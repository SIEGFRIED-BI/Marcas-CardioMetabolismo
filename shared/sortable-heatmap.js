/* shared/sortable-heatmap.js
 * Orden por columna (click en el header) para las tablas heatmap `table.hm` de las
 * paginas de competidores / DDD de las 7 lineas ("Por Provincia" y "Por Region").
 *
 * Por que un modulo aparte y no un patch en cada pagina:
 *   Las 7 competidores.html tienen 4 variantes distintas del bloque <script> inline y
 *   el generador (shared/build-competidores-pages.py) ya divergio de lo committeado.
 *   Este modulo trabaja SOLO contra el DOM ya renderizado, asi que no toca ninguna de
 *   las funciones de render (renderTableA / renderTableB / renderTableBProv) y sirve
 *   igual para las 4 variantes y para las dos tablas de cada pagina.
 *
 * Que hace:
 *   - Click en un sub-header (MS% / Unidades / IE / VAR ...) ordena las filas por esa
 *     columna mayor->menor; segundo click invierte; tercer click vuelve al orden original.
 *   - Click en el header de la primera columna (Region / Provincia) ordena A->Z / Z->A.
 *   - La fila TOTAL PAIS (tr.row-total-pais) queda SIEMPRE fija arriba: es un agregado,
 *     no una fila comparable.
 *   - Las celdas sin dato ("—") van SIEMPRE al final, en las dos direcciones.
 *
 * Invariantes que respeta (por eso no rompe nada de lo que ya andaba):
 *   - Mueve los <tr> existentes; NO los re-crea. Sobreviven los estilos inline (heat
 *     colors / escala de intensidad), los title (tooltips), data-prov y los anchos que
 *     haya seteado shared/resize-cols.js.
 *   - El click de fila de la pagina esta DELEGADO en document contra
 *     '#hm-prov tbody tr[data-prov]', asi que mover nodos no lo desengancha.
 *   - La flecha se dibuja con CSS ::after sobre [data-sfsort], NO como nodo de texto:
 *     (a) el export a Excel lee th.textContent y no queda contaminado con "▼";
 *     (b) shared/resize-cols.js observa el thead con {childList:true} y una mutacion
 *         de atributo no le dispara re-attach.
 *   - Al re-renderizar (cambio de periodo / metrica / competidores / top5-top10) el
 *     orden se re-aplica buscando la MISMA columna por (marca, metrica), no por indice:
 *     si esa columna ya no existe, el orden se descarta en vez de ordenar por otra marca.
 *
 * Se auto-inicializa. No requiere ningun cambio en las paginas mas que incluirlo.
 */
(function () {
  'use strict';

  var STYLE_ID = 'sfsort-styles';
  var HINT = ' · click para ordenar mayor→menor';
  // estado por tabla: id -> {group, metric, dir} | null
  var state = Object.create(null);
  var busy = false;

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var st = document.createElement('style');
    st.id = STYLE_ID;
    st.textContent = [
      'table.hm thead th[data-sfsortable]{cursor:pointer;-webkit-user-select:none;user-select:none;}',
      'table.hm thead th[data-sfsortable]:hover{filter:brightness(1.25);}',
      'table.hm thead th[data-sfsort]::after{',
      '  content:"\\00a0▼";font-size:8px;opacity:.95;font-weight:700;',
      '}',
      'table.hm thead th[data-sfsort="asc"]::after{content:"\\00a0▲";}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(st);
  }

  /* Parsea el texto de una celda a numero comparable.
   * Formatos que producen las paginas (renderTableA / renderTableB / renderTableBProv):
   *   MS%            -> "56.6%"            (toFixed(1) + '%')
   *   VAR MS%        -> "+1.2" / "-0.8"    (signo + toFixed(1))
   *   VAR UNIDADES%  -> "+10%" / "-5%"     (signo + toFixed(0) + '%')
   *   Unidades       -> "986" | "77.8k" | "1.2M"   (fmtUnits)
   *   IE             -> "98"               (Math.round)
   *   Mercado total  -> "215.594"          (toLocaleString('es-AR') => punto de miles)
   *   sin dato       -> "—"
   * OJO el orden de las ramas: los miles se evaluan ANTES del decimal pelado, si no
   * "215.594" se leeria como 215,594 (mil veces menos).
   */
  function parseNum(txt) {
    if (txt == null) return null;
    var s = String(txt).trim();
    if (!s || s === '—' || s === '–' || s === '-' || s === 'n/d') return null;
    var m;
    // miles con separador: 1.234 / 1,234 / 1.234.567 (grupos de EXACTAMENTE 3)
    m = s.match(/^([+\-]?)(\d{1,3}(?:[.,]\d{3})+)$/);
    if (m) return (m[1] === '-' ? -1 : 1) * parseInt(m[2].replace(/[.,]/g, ''), 10);
    // sufijo k / M
    m = s.match(/^([+\-]?\d+(?:[.,]\d+)?)\s*([kKmM])$/);
    if (m) {
      return parseFloat(m[1].replace(',', '.')) * (m[2].toLowerCase() === 'k' ? 1e3 : 1e6);
    }
    // porcentaje, pp, o numero pelado (con o sin signo)
    m = s.match(/^([+\-]?\d+(?:[.,]\d+)?)\s*(%|pp)?$/i);
    if (m) return parseFloat(m[1].replace(',', '.'));
    return null;
  }

  function headRows(tbl) {
    var thead = tbl.querySelector('thead');
    return thead ? thead.querySelectorAll('tr') : [];
  }

  /* Devuelve la lista de sub-headers (2da fila del thead) o [] si la tabla no tiene
   * el layout de dos filas. */
  function subHeaders(tbl) {
    var rows = headRows(tbl);
    if (rows.length < 2) return [];
    return Array.prototype.slice.call(rows[1].querySelectorAll('th'));
  }

  function labelHeader(tbl) {
    var rows = headRows(tbl);
    if (!rows.length) return null;
    return rows[0].querySelector('th[rowspan="2"]');
  }

  /* La etiqueta del grupo (marca / serie) al que pertenece el sub-header i.
   * La 1ra fila del thead es: [th rowspan=2 (region)] + un th colspan=N por grupo. */
  function groupLabelFor(tbl, idx) {
    var rows = headRows(tbl);
    if (rows.length < 2) return '';
    var ths = Array.prototype.slice.call(rows[0].querySelectorAll('th'));
    var col = 0;
    for (var i = 0; i < ths.length; i++) {
      var th = ths[i];
      if (th.getAttribute('rowspan')) continue;  // la columna de etiqueta, no es un grupo
      var span = parseInt(th.getAttribute('colspan') || '1', 10);
      if (idx >= col && idx < col + span) return (th.textContent || '').trim();
      col += span;
    }
    return '';
  }

  function dataRows(tbl) {
    var tbody = tbl.querySelector('tbody');
    if (!tbody) return { pinned: [], rows: [], tbody: null };
    var all = Array.prototype.slice.call(tbody.children);
    var pinned = [], rows = [];
    for (var i = 0; i < all.length; i++) {
      var tr = all[i];
      if (tr.tagName !== 'TR') continue;
      // fila vacia ("Sin datos visibles") -> no se ordena nada
      if (tr.querySelector('td.empty')) return { pinned: [], rows: [], tbody: tbody };
      if (tr.classList && tr.classList.contains('row-total-pais')) pinned.push(tr);
      else rows.push(tr);
    }
    return { pinned: pinned, rows: rows, tbody: tbody };
  }

  function markSortable(tbl) {
    var subs = subHeaders(tbl);
    for (var i = 0; i < subs.length; i++) {
      var th = subs[i];
      th.setAttribute('data-sfsortable', String(i));
      var t = th.getAttribute('title') || '';
      if (t.indexOf(HINT) === -1) th.setAttribute('title', t + HINT);
    }
    var lh = labelHeader(tbl);
    if (lh && subs.length) {
      lh.setAttribute('data-sfsortable', 'label');
      var lt = lh.getAttribute('title') || '';
      if (lt.indexOf('ordenar') === -1) lh.setAttribute('title', lt + ' · click para ordenar A→Z');
    }
  }

  function clearArrows(tbl) {
    var ths = tbl.querySelectorAll('thead th[data-sfsort]');
    for (var i = 0; i < ths.length; i++) ths[i].removeAttribute('data-sfsort');
  }

  /* Aplica el estado de orden guardado para esta tabla. Si la columna guardada ya no
   * existe (cambio de metrica / de set de competidores), descarta el orden. */
  function apply(tbl) {
    var id = tbl.id;
    var st = id ? state[id] : null;
    clearArrows(tbl);
    if (!st) return;

    var d = dataRows(tbl);
    if (!d.tbody || d.rows.length < 2) return;

    var th = null, idx = -1;
    if (st.metric === '__label__') {
      th = labelHeader(tbl);
      idx = -1;
    } else {
      var subs = subHeaders(tbl);
      for (var i = 0; i < subs.length; i++) {
        var lbl = (subs[i].textContent || '').trim();
        if (lbl === st.metric && groupLabelFor(tbl, i) === st.group) { th = subs[i]; idx = i; break; }
      }
    }
    if (!th) { state[id] = null; return; }   // la columna ya no esta -> no ordenamos por otra

    var rows = d.rows.slice();
    var keyed = rows.map(function (tr, pos) {
      var v;
      if (idx === -1) {
        var cell = tr.querySelector('th');
        v = cell ? (cell.textContent || '').trim() : '';
      } else {
        var tds = tr.querySelectorAll('td');
        v = idx < tds.length ? parseNum(tds[idx].textContent) : null;
      }
      return { tr: tr, v: v, pos: pos };
    });

    var asc = st.dir === 'asc';
    keyed.sort(function (a, b) {
      var av = a.v, bv = b.v;
      // sin dato siempre al final, en las dos direcciones
      var aNull = (av === null || av === undefined || av === '');
      var bNull = (bv === null || bv === undefined || bv === '');
      if (aNull && bNull) return a.pos - b.pos;
      if (aNull) return 1;
      if (bNull) return -1;
      var cmp;
      if (typeof av === 'string' || typeof bv === 'string') {
        cmp = String(av).localeCompare(String(bv), 'es');
      } else {
        cmp = av - bv;
      }
      if (cmp === 0) return a.pos - b.pos;   // estable
      return asc ? cmp : -cmp;
    });

    busy = true;
    try {
      var frag = document.createDocumentFragment();
      for (var p = 0; p < d.pinned.length; p++) frag.appendChild(d.pinned[p]);
      for (var k = 0; k < keyed.length; k++) frag.appendChild(keyed[k].tr);
      d.tbody.appendChild(frag);
    } finally {
      // Descartamos las mutaciones que generamos nosotros: el callback de
      // MutationObserver es ASINCRONICO, asi que un flag no alcanza (cuando corre,
      // busy ya volvio a false -> se re-aplicaria en loop infinito).
      if (tbl.__sfsortObs) tbl.__sfsortObs.takeRecords();
      busy = false;
    }
    th.setAttribute('data-sfsort', asc ? 'asc' : 'desc');
  }

  function onHeaderClick(ev) {
    var th = ev.target && ev.target.closest ? ev.target.closest('th[data-sfsortable]') : null;
    if (!th) return;
    var tbl = th.closest('table.hm');
    if (!tbl || !tbl.id) return;
    var kind = th.getAttribute('data-sfsortable');

    var group, metric;
    if (kind === 'label') {
      group = '';
      metric = '__label__';
    } else {
      var idx = parseInt(kind, 10);
      metric = (th.textContent || '').trim();
      group = groupLabelFor(tbl, idx);
    }

    var cur = state[tbl.id];
    if (cur && cur.group === group && cur.metric === metric) {
      // desc -> asc -> sin orden
      if (cur.dir === 'desc') state[tbl.id] = { group: group, metric: metric, dir: 'asc' };
      else state[tbl.id] = null;
    } else {
      state[tbl.id] = { group: group, metric: metric, dir: 'desc' };
    }

    if (state[tbl.id]) {
      apply(tbl);
    } else {
      clearArrows(tbl);
      // sin orden: forzamos un re-render de la pagina si expone uno; si no, dejamos
      // las filas donde estan (el proximo re-render natural restaura el orden base).
      if (typeof window.renderAll === 'function') { try { window.renderAll(); } catch (e) {} }
    }
  }

  function hook(tbl) {
    if (tbl.__sfsortHooked) return;
    tbl.__sfsortHooked = true;
    markSortable(tbl);
    var thead = tbl.querySelector('thead');
    if (!thead || typeof MutationObserver === 'undefined') return;
    // Observamos SOLO el thead, nunca el tbody: las funciones de render reasignan
    // thead.innerHTML en TODOS sus caminos (incluidos los estados vacios), asi que
    // alcanza para detectar un re-render; y como nuestro propio sort solo mueve
    // filas del tbody y setea atributos en el thead, no nos auto-disparamos.
    var obs = new MutationObserver(function () {
      if (busy) return;
      busy = true;
      try { markSortable(tbl); } finally { busy = false; }
      apply(tbl);
    });
    tbl.__sfsortObs = obs;
    obs.observe(thead, { childList: true });
  }

  function init() {
    injectStyles();
    var tables = document.querySelectorAll('table.hm');
    for (var i = 0; i < tables.length; i++) hook(tables[i]);
    document.addEventListener('click', onHeaderClick);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
