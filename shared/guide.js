/* shared/guide.js — Guía de uso compartida para los tableros de marcas.
   Inyecta un botón "❓ Guía" en .nav-actions y un drawer lateral que explica
   dónde encontrar cada dato + glosario de métricas. Data-agnóstico: solo usa
   la nav común (#s-kpi, #s-bud, ...). No toca el render de cada línea. */
(function () {
  'use strict';

  // ¿Dónde veo...? (atajos)
  var SHORTCUTS = [
    ['Mi MS% vs el mercado', 'Mercado IQVIA'],
    ['Si gané o perdí share (IE)', 'Resumen'],
    ['Cómo voy vs el presupuesto', 'Venta Interna'],
    ['Mis recetas vs la competencia', 'Recetas'],
    ['Quiebres / cobertura de stock', 'Cobertura'],
    ['Precios vs competidores', 'Precios'],
    ['Detalle por región / competidores', 'DDD · Competidores'],
  ];

  // Secciones (match por href #id de la nav)
  var SECTIONS = [
    ['#s-kpi', 'Resumen', 'KPIs principales de la línea: IE, MS%, unidades IQVIA, crecimiento, estimado de venta y recetas. Toggle YTD / MAT.'],
    ['#s-bud', 'Venta Interna', 'Venta real vs presupuesto por producto, mes a mes. Cumplimiento %.'],
    ['#s-perf', 'Mercado IQVIA', 'Tu participación (MS%) vs el mercado, evolución (IE), unidades y ranking de competidores. Acá ves "mi MS% vs el mercado".'],
    ['#s-rec', 'Recetas', 'Recetas y médicos prescriptores (CloseUp): tu share de recetas vs la competencia.'],
    ['#s-stock', 'Stock', 'Días de stock y venta por producto.'],
    ['#s-cover', 'Cobertura', 'Estado de cobertura (quiebre / bajo / alerta / OK), por marca o presentación.'],
    ['#s-can', 'Mostrador vs Convenios', 'Mix de venta por mostrador vs convenios y descuentos.'],
    ['#s-conv', 'Convenios', 'Convenios por obra social, comparado año contra año.'],
    ['#s-pcomp', 'Precios mercado', 'Comparativa de precios vs la competencia por presentación.'],
  ];

  var GLOSSARY = [
    ['IE — Índice de Evolución', 'Tu crecimiento RELATIVO al del mercado. >100 = creciste más que el mercado (ganaste share); <100 = menos. No es tu crecimiento propio.'],
    ['MS% — Market Share', 'Tu participación: tus unidades ÷ unidades del mercado × 100.'],
    ['YTD', 'Acumulado del año (Ene → mes de cierre) vs el mismo período del año anterior.'],
    ['MAT', '12 meses móviles vs los 12 anteriores.'],
    ['Trimestre / Semestre', 'Últimos 3 / 6 meses vs el mismo período del año anterior.'],
    ['"Datos al…"', 'Fecha de última actualización del tablero. Cada fuente tiene su propio corte (IQVIA, venta, recetas), indicado en cada sección.'],
  ];

  var CSS = '.guide-btn{font:600 12px/1 "IBM Plex Sans",system-ui,sans-serif;color:#b01e1e;background:#fff;border:1px solid #e3c4c4;border-radius:8px;padding:7px 11px;cursor:pointer;white-space:nowrap;transition:background .15s,border-color .15s}'
    + '.guide-btn:hover{background:#fdf2f2;border-color:#b01e1e}'
    + '.guide-overlay{position:fixed;inset:0;background:rgba(17,24,39,.38);opacity:0;visibility:hidden;transition:opacity .25s;z-index:999}'
    + '.guide-overlay.on{opacity:1;visibility:visible}'
    + '.guide-drawer{position:fixed;top:0;right:0;height:100vh;width:380px;max-width:92vw;background:#fff;box-shadow:-8px 0 28px rgba(0,0,0,.16);transform:translateX(100%);transition:transform .28s cubic-bezier(.4,0,.2,1);z-index:1000;display:flex;flex-direction:column;font-family:"IBM Plex Sans",system-ui,sans-serif}'
    + '.guide-drawer.on{transform:translateX(0)}'
    + '.guide-head{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;border-bottom:1px solid #eee;flex-shrink:0}'
    + '.guide-head h2{font-size:16px;font-weight:700;color:#111827;margin:0}'
    + '.guide-close{background:none;border:none;font-size:22px;line-height:1;color:#9ca3af;cursor:pointer;padding:0 4px}'
    + '.guide-close:hover{color:#374151}'
    + '.guide-body{overflow-y:auto;padding:18px 20px;flex:1}'
    + '.guide-sec{margin-bottom:22px}'
    + '.guide-sec h3{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#b01e1e;margin:0 0 10px}'
    + '.guide-q{display:flex;gap:8px;padding:7px 0;border-bottom:1px solid #f3f4f6;font-size:12.5px;color:#374151}'
    + '.guide-q:last-child{border-bottom:none}.guide-q .q{flex:1}.guide-q .a{font-weight:600;color:#b01e1e;white-space:nowrap}'
    + '.guide-item{margin-bottom:12px}.guide-item b{display:block;font-size:13px;color:#111827;margin-bottom:2px}.guide-item p{margin:0;font-size:12px;color:#6b7280;line-height:1.5}'
    + '.guide-gloss{font-size:12px;color:#374151;line-height:1.55}.guide-gloss b{color:#111827}'
    + '.guide-foot{padding:12px 20px;border-top:1px solid #eee;font-size:11px;color:#9ca3af;flex-shrink:0}';

  function injectCss() {
    if (document.getElementById('guide-css')) return;
    var s = document.createElement('style'); s.id = 'guide-css'; s.textContent = CSS;
    document.head.appendChild(s);
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  function build() {
    injectCss();
    // Solo secciones presentes en esta línea
    var present = SECTIONS.filter(function (s) { return document.querySelector('a.nav-item[href="' + s[0] + '"]') || document.querySelector(s[0]); });

    var overlay = el('div', 'guide-overlay');
    var drawer = el('div', 'guide-drawer');
    drawer.setAttribute('role', 'dialog');
    drawer.setAttribute('aria-label', 'Guía de uso del tablero');

    var head = el('div', 'guide-head');
    head.appendChild(el('h2', null, 'Guía de uso'));
    var closeBtn = el('button', 'guide-close', '&times;');
    closeBtn.setAttribute('aria-label', 'Cerrar');
    head.appendChild(closeBtn);

    var body = el('div', 'guide-body');

    // Atajos
    var qSec = el('div', 'guide-sec');
    qSec.appendChild(el('h3', null, '¿Dónde veo…?'));
    SHORTCUTS.forEach(function (q) {
      var row = el('div', 'guide-q');
      row.appendChild(el('span', 'q', esc(q[0])));
      row.appendChild(el('span', 'a', esc(q[1])));
      qSec.appendChild(row);
    });
    body.appendChild(qSec);

    // Secciones del tablero
    var sSec = el('div', 'guide-sec');
    sSec.appendChild(el('h3', null, 'Secciones de este tablero'));
    present.forEach(function (s) {
      var it = el('div', 'guide-item');
      it.innerHTML = '<b>' + esc(s[1]) + '</b><p>' + esc(s[2]) + '</p>';
      sSec.appendChild(it);
    });
    body.appendChild(sSec);

    // Glosario
    var gSec = el('div', 'guide-sec');
    gSec.appendChild(el('h3', null, 'Glosario'));
    var gl = el('div', 'guide-gloss');
    gl.innerHTML = GLOSSARY.map(function (g) { return '<p style="margin:0 0 9px"><b>' + esc(g[0]) + ':</b> ' + esc(g[1]) + '</p>'; }).join('');
    gSec.appendChild(gl);
    body.appendChild(gSec);

    var foot = el('div', 'guide-foot', 'Actualización: el tablero se regenera cada mes desde una base IQVIA única (un solo proceso para todas las líneas). "Datos al…" = última actualización; cada sección muestra su propio corte (IQVIA, venta y recetas pueden diferir).');

    drawer.appendChild(head); drawer.appendChild(body); drawer.appendChild(foot);
    document.body.appendChild(overlay); document.body.appendChild(drawer);

    function open() { overlay.classList.add('on'); drawer.classList.add('on'); }
    function close() { overlay.classList.remove('on'); drawer.classList.remove('on'); }
    overlay.addEventListener('click', close);
    closeBtn.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

    // Botón en la nav
    var host = document.querySelector('.nav-actions') || document.querySelector('nav');
    var btn = el('button', 'guide-btn nav-tab', '❓ Guía');
    btn.type = 'button';
    btn.addEventListener('click', open);
    if (host) host.appendChild(btn); else { btn.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:998'; document.body.appendChild(btn); }

    // Tooltips livianos: title en los nav-items (hover) — no toca el render
    present.forEach(function (s) {
      var a = document.querySelector('a.nav-item[href="' + s[0] + '"]');
      if (a && !a.title) a.title = s[2];
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
