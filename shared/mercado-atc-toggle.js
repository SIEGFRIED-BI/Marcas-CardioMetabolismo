/* shared/mercado-atc-toggle.js
 * Agrega a la seccion "Mercado IQVIA" un selector para ver la comparativa
 * multi-periodo contra DOS universos distintos:
 *
 *   Molecula          -> D.mol_perf         (lo de siempre, es el default)
 *   Clase terapeutica -> D.mercadosATC      (vista amplia por ATC III del Ateneo)
 *
 * Pedido del usuario: "mantene los que estan pero agrega por ejemplo para roxolan el
 * mercado de hipolipemeantes" / "no quiero agregar productos y demas, son formas
 * extras de analizar el mercado".
 * Ejemplo: ROXOLAN mide 2,0% contra el mercado de ROSUVASTATIN (10,1M MAT) y 1,05%
 * contra C10A - PRD REGULADORES LIPIDOS (135 marcas, 19,6M MAT).
 *
 * POR QUE NO HAY QUE TOCAR multi-period-table.js
 * ----------------------------------------------
 * renderMultiPeriodTable(containerId, opts) ya acepta opts.data y lo usa como si fuera
 * el dashboard entero. Y buildIqviaFamilies() solo lee, de cada producto,
 * monthly_vals + is_sie: el mercado lo arma sumando los monthly_vals y el MS%/IE/Var pp
 * los calcula por su cuenta (computeFamily / computeBrand). Asi que basta con pasarle un
 * objeto sintetico { mol_perf: ..., budIqviaMap: ... } armado desde D.mercadosATC.
 * Cero cambios en el bundle compartido -> no se toca la logica de render ni se corre el
 * riesgo de duplicarla inline (shared/check-render-parity.py).
 *
 * ATRIBUCION DEL MS% PROPIO
 * -------------------------
 * Una clase ATC contiene VARIAS marcas Siegfried (en C10A estan ROXOLAN y ROXOLAN PLUS;
 * en C09D estan DIOVAN D, ENTRESTO, EXFORGE y EXFORGE D). buildIqviaFamilies calcula
 * own = is_sie && ownList.indexOf(prod) !== -1, con ownList = budIqviaMap[familia]. Por
 * eso se pasa D.mercadosATC.propios como budIqviaMap: cada fila mide SOLO su propia
 * marca contra la clase, no todo lo Siegfried que haya adentro. Sin esto, DILATREND y
 * DILATREND AP mostrarian las dos el mismo 4,00% en vez de 4,00% y 0,33%.
 */
(function (global) {
  'use strict';

  var WRAP_ID = 'mp-iqvia-wrap';
  var BAR_ID = 'mp-atc-bar';

  function getData() {
    try { if (typeof global.OTC_DASHBOARD !== 'undefined' && global.OTC_DASHBOARD) return global.OTC_DASHBOARD; } catch (e) {}
    try { if (typeof global.D !== 'undefined' && global.D) return global.D; } catch (e) {}
    return null;
  }

  function famLabel(fam) {
    return (global.FAM_LABEL && global.FAM_LABEL[fam]) || fam;
  }

  /* Arma el objeto sintetico que espera renderMultiPeriodTable. Las claves de familia
   * llevan la clase pegada ("ROXOLAN · C10A - PRD REGULADORES LIPIDOS") porque la fila
   * es la marca pero el universo es la clase, y sin eso la tabla diria solo "ROXOLAN"
   * con numeros que no son los de su mercado de molecula. */
  function buildAtcData(D) {
    var mA = D && D.mercadosATC;
    if (!mA || !mA.clases || !mA.porFamilia) return null;
    var mp = {}, bim = {}, n = 0;
    Object.keys(mA.porFamilia).forEach(function (fam) {
      var clase = mA.porFamilia[fam];
      var c = mA.clases[clase];
      if (!c || !c.products || !c.products.length) return;
      var key = famLabel(fam) + ' · ' + clase;
      mp[key] = { products: c.products };
      bim[key] = (mA.propios && mA.propios[fam]) || [];
      n++;
    });
    if (!n) return null;
    return { mol_perf: mp, budIqviaMap: bim };
  }

  function render(modo) {
    var D = getData();
    if (!D || typeof global.renderMultiPeriodTable !== 'function') return;
    var opts = { source: 'iqvia', data: D };
    if (modo === 'atc') {
      var alt = buildAtcData(D);
      if (alt) opts.data = alt;
    }
    try {
      global.renderMultiPeriodTable(WRAP_ID, opts);
    } catch (e) {
      if (global.console) console.error('[mp-atc]', e);
    }
  }

  function build() {
    var wrap = document.getElementById(WRAP_ID);
    if (!wrap || document.getElementById(BAR_ID)) return;      // idempotente
    var D = getData();
    if (!buildAtcData(D)) return;   // la linea no tiene la vista -> no se muestra nada
    var mA = D.mercadosATC;
    var nClases = Object.keys(mA.clases).length;

    var bar = document.createElement('div');
    bar.id = BAR_ID;
    bar.style.cssText = 'display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 8px;';
    bar.innerHTML =
      '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;font-weight:700;'
      + 'letter-spacing:.1em;text-transform:uppercase;color:#6b7280;">Universo</span>'
      + '<div style="display:inline-flex;background:#fff;border:1px solid #e5e7eb;'
      + 'border-radius:6px;overflow:hidden;">'
      + '<button type="button" data-modo="mol" style="padding:4px 10px;border:0;'
      + 'border-right:1px solid #f3f4f6;background:#b01e1e;color:#fff;cursor:pointer;'
      + 'font:600 10px/1.4 inherit;">Molécula</button>'
      + '<button type="button" data-modo="atc" style="padding:4px 10px;border:0;'
      + 'background:transparent;color:#525252;cursor:pointer;font:600 10px/1.4 inherit;">'
      + 'Clase terapéutica</button>'
      + '</div>'
      + '<span id="' + BAR_ID + '-hint" style="font-size:9.5px;color:#6b7280;">'
      + 'Mercado de la molécula exacta.</span>';
    wrap.parentNode.insertBefore(bar, wrap);

    var hint = bar.querySelector('#' + BAR_ID + '-hint');
    var botones = bar.querySelectorAll('button[data-modo]');
    function setModo(modo) {
      for (var i = 0; i < botones.length; i++) {
        var on = botones[i].getAttribute('data-modo') === modo;
        botones[i].style.background = on ? '#b01e1e' : 'transparent';
        botones[i].style.color = on ? '#fff' : '#525252';
      }
      hint.textContent = modo === 'atc'
        ? 'Clase terapéutica ATC del Ateneo — ' + nClases + ' clases, universo más amplio '
          + 'que la molécula. El MS% de cada marca se recalcula contra la clase.'
        : 'Mercado de la molécula exacta.';
      render(modo);
    }
    for (var j = 0; j < botones.length; j++) {
      botones[j].addEventListener('click', function () {
        setModo(this.getAttribute('data-modo'));
      });
    }
    // No se re-renderiza al iniciar: la pagina ya dibujo la vista de molecula.
  }

  function init() {
    // Corre despues del init de la pagina, que es el que dibuja la tabla por primera vez.
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { setTimeout(build, 120); });
    } else {
      setTimeout(build, 120);
    }
  }
  init();
  global.__sfMercadoAtc = { build: build, render: render, buildAtcData: buildAtcData };
})(window);
