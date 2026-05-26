/* shared/multi-period-table.js
 * Renderiza una tabla multi-período (MAT / YTD / MES / TRIM × 6 métricas)
 * para una línea (per-line), reutilizable en secciones:
 *   - Mercado IQVIA  (datos: D.mol_perf)
 *   - Recetas        (datos: D.rec_ms con .sie y .mkt monthly dicts)
 *
 * Columnas por período:
 *   U Ant     - Unidades/Recetas mercado período anterior
 *   U Act     - Unidades/Recetas mercado período actual (con flecha ▲/▼)
 *   MS% Ant   - Market share SIE período anterior
 *   MS% Act   - Market share SIE período actual (con flecha)
 *   IE        - (SIE growth / Market growth × 100)
 *   Var pp    - MS% Act - MS% Ant
 *
 * Coloreado:
 *   IE: verde ≥105 · gris 95-105 · ámbar 85-94 · rojo <85
 *   Var pp: verde >+0.05 · gris ±0.05 · rojo <-0.05
 *
 * Uso (en cada línea, dentro de DOMContentLoaded):
 *   renderMultiPeriodTable('mp-iqvia-wrap', { source: 'iqvia' });
 *   renderMultiPeriodTable('mp-rec-wrap',   { source: 'recetas' });
 *
 * Toma D directamente del scope global (window.OTC_DASHBOARD o const D).
 */
(function(global){
  'use strict';

  var MES_INV = {Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,
                 Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12};
  var NUM_TO_MES = {};
  for (var k in MES_INV) NUM_TO_MES[MES_INV[k]] = k;
  var MES_SHORT = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                   7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'};

  function fmtInt(n) {
    if (n == null) return '—';
    var x = Math.abs(+n||0);
    if (x === 0) return '0';
    if (x >= 1e6) return (n/1e6).toFixed(x>=1e7?1:2).replace(/\.?0+$/,'')+'M';
    if (x >= 1e3) return (n/1e3).toFixed(x>=1e4?0:1).replace(/\.0$/,'')+'k';
    return Math.round(n).toString();
  }
  function fmtPct(n, d) {
    if (n == null) return '—';
    return Number(n).toFixed(d!=null?d:1)+'%';
  }
  function ieClass(ie) {
    if (ie == null) return 'mp-ie-flat';
    if (ie >= 105) return 'mp-ie-good';
    if (ie >= 95)  return 'mp-ie-flat';
    if (ie >= 85)  return 'mp-ie-warn';
    return 'mp-ie-bad';
  }
  function varppClass(v) {
    if (v == null) return 'mp-varpp-flat';
    if (v > 0.05) return 'mp-varpp-good';
    if (v < -0.05) return 'mp-varpp-bad';
    return 'mp-varpp-flat';
  }
  function arrow(curr, prev) {
    if (curr == null || prev == null) return '';
    if (curr > prev * 1.001) return '<span class="mp-arrow up">▲</span>';
    if (curr < prev * 0.999) return '<span class="mp-arrow down">▼</span>';
    return '';
  }
  function monthRange(endY, endM, n) {
    var out = [], y = endY, m = endM;
    for (var i = 0; i < n; i++) {
      out.push(NUM_TO_MES[m] + ' ' + y);
      m--; if (m === 0) { m = 12; y--; }
    }
    return out;
  }
  function windowsFor(endY, endM) {
    return {
      mes:       { curr: [NUM_TO_MES[endM]+' '+endY],     prev: [NUM_TO_MES[endM]+' '+(endY-1)] },
      ytd:       { curr: (function(){var a=[];for(var m=1;m<=endM;m++)a.push(NUM_TO_MES[m]+' '+endY);return a;})(),
                   prev: (function(){var a=[];for(var m=1;m<=endM;m++)a.push(NUM_TO_MES[m]+' '+(endY-1));return a;})() },
      trimestre: { curr: monthRange(endY, endM, 3),       prev: monthRange(endY-1, endM, 3) },
      mat:       { curr: monthRange(endY, endM, 12),      prev: monthRange(endY-1, endM, 12) },
    };
  }
  function sumWindow(dict, keys) {
    if (!dict) return 0;
    var s = 0;
    for (var i = 0; i < keys.length; i++) {
      var v = dict[keys[i]];
      if (v != null) s += +v || 0;
    }
    return s;
  }
  function detectLatest(monthlyDicts) {
    // monthlyDicts: array of monthly_vals-like objects
    var latest = null;
    for (var i = 0; i < monthlyDicts.length; i++) {
      var md = monthlyDicts[i] || {};
      for (var mk in md) {
        var parts = mk.split(' ');
        if (parts.length !== 2 || !(parts[0] in MES_INV)) continue;
        var y = parseInt(parts[1]);
        if (isNaN(y)) continue;
        var key = y * 100 + MES_INV[parts[0]];
        if (latest == null || key > latest) latest = key;
      }
    }
    if (latest == null) return null;
    return { y: Math.floor(latest/100), m: latest%100 };
  }

  function computeFamily(marketMonthly, sieMonthly, windowKeys) {
    var market_curr = sumWindow(marketMonthly, windowKeys.curr);
    var market_prev = sumWindow(marketMonthly, windowKeys.prev);
    var sie_curr    = sumWindow(sieMonthly, windowKeys.curr);
    var sie_prev    = sumWindow(sieMonthly, windowKeys.prev);
    var ms_curr = (market_curr > 0) ? +(sie_curr / market_curr * 100).toFixed(1) : null;
    var ms_prev = (market_prev > 0) ? +(sie_prev / market_prev * 100).toFixed(1) : null;
    var ie = null;
    if (sie_prev > 0 && market_prev > 0 && market_curr > 0) {
      var sg = sie_curr / sie_prev;
      var mg = market_curr / market_prev;
      if (mg > 0) ie = Math.round(sg / mg * 100);
    }
    var var_pp = null;
    if (ms_curr != null && ms_prev != null) var_pp = +(ms_curr - ms_prev).toFixed(2);
    return {
      market_curr: Math.round(market_curr),
      market_prev: Math.round(market_prev),
      sie_curr:    Math.round(sie_curr),
      sie_prev:    Math.round(sie_prev),
      ms_curr:     ms_curr,
      ms_prev:     ms_prev,
      ie:          ie,
      var_pp:      var_pp,
    };
  }

  // Build family list for IQVIA from D.mol_perf
  function buildIqviaFamilies(D) {
    var mp = D && D.mol_perf;
    if (!mp) return null;
    // Detect latest month across all families
    var allMonthly = [];
    for (var fam in mp) {
      var prods = (mp[fam] && mp[fam].products) || [];
      for (var p = 0; p < prods.length; p++) {
        if (prods[p].monthly_vals) allMonthly.push(prods[p].monthly_vals);
      }
    }
    var latest = detectLatest(allMonthly);
    if (!latest) return null;
    var windows = windowsFor(latest.y, latest.m);

    var families = [];
    for (var fam in mp) {
      var prods2 = (mp[fam] && mp[fam].products) || [];
      var hasSie = false;
      // Build aggregated monthly_vals for market (all products) and sie (is_sie products)
      var mktMonthly = {}, sieMonthly = {};
      for (var pp = 0; pp < prods2.length; pp++) {
        var pr = prods2[pp];
        var mv = pr.monthly_vals || {};
        for (var mk in mv) {
          mktMonthly[mk] = (mktMonthly[mk] || 0) + (+mv[mk] || 0);
          if (pr.is_sie) sieMonthly[mk] = (sieMonthly[mk] || 0) + (+mv[mk] || 0);
        }
        if (pr.is_sie) hasSie = true;
      }
      if (!hasSie) continue;
      var periods = {};
      for (var pk in windows) periods[pk] = computeFamily(mktMonthly, sieMonthly, windows[pk]);
      families.push({ family: fam, periods: periods });
    }
    families.sort(function(a,b){ return (b.periods.mat.market_curr||0) - (a.periods.mat.market_curr||0); });
    var ml = MES_SHORT[latest.m];
    return {
      latest: { y: latest.y, m: latest.m, label: ml + ' ' + latest.y },
      period_labels: {
        mes:       ml + ' ' + latest.y + ' vs ' + ml + ' ' + (latest.y-1),
        ytd:       'YTD Ene-' + ml + ' ' + latest.y + ' vs ' + (latest.y-1),
        trimestre: 'Trim. ' + MES_SHORT[((latest.m-3+11)%12)+1] + '-' + ml + ' ' + latest.y + ' vs ' + (latest.y-1),
        mat:       'MAT ' + ml + ' ' + latest.y + ' vs ' + ml + ' ' + (latest.y-1),
      },
      families: families,
    };
  }

  // Build family list for Recetas from D.rec_ms
  function buildRecetasFamilies(D) {
    var rm = D && D.rec_ms;
    if (!rm) return null;
    // Detect latest month
    var allMonthly = [];
    for (var fam in rm) {
      if (rm[fam] && rm[fam].sie) allMonthly.push(rm[fam].sie);
      if (rm[fam] && rm[fam].mkt) allMonthly.push(rm[fam].mkt);
    }
    var latest = detectLatest(allMonthly);
    if (!latest) return null;
    var windows = windowsFor(latest.y, latest.m);

    var families = [];
    for (var fam in rm) {
      var sieMonthly = (rm[fam] && rm[fam].sie) || {};
      var mktMonthly = (rm[fam] && rm[fam].mkt) || {};
      // Skip if no SIE data at all
      var hasAnySie = false;
      for (var mk in sieMonthly) { if (+sieMonthly[mk] > 0) { hasAnySie = true; break; } }
      if (!hasAnySie) continue;
      var periods = {};
      for (var pk in windows) periods[pk] = computeFamily(mktMonthly, sieMonthly, windows[pk]);
      families.push({ family: fam, periods: periods });
    }
    families.sort(function(a,b){ return (b.periods.mat.market_curr||0) - (a.periods.mat.market_curr||0); });
    var ml = MES_SHORT[latest.m];
    return {
      latest: { y: latest.y, m: latest.m, label: ml + ' ' + latest.y },
      period_labels: {
        mes:       ml + ' ' + latest.y + ' vs ' + ml + ' ' + (latest.y-1),
        ytd:       'YTD Ene-' + ml + ' ' + latest.y + ' vs ' + (latest.y-1),
        trimestre: 'Trim. ' + MES_SHORT[((latest.m-3+11)%12)+1] + '-' + ml + ' ' + latest.y + ' vs ' + (latest.y-1),
        mat:       'MAT ' + ml + ' ' + latest.y + ' vs ' + ml + ' ' + (latest.y-1),
      },
      families: families,
    };
  }

  function renderTable(container, data, opts) {
    if (!data || !data.families || !data.families.length) {
      container.innerHTML = '<div style="padding:24px;text-align:center;color:#9ca3af;font-size:11px;">Sin datos disponibles</div>';
      return;
    }
    var lbls = data.period_labels;
    var sourceLabel = (opts && opts.source === 'recetas') ? 'Recetas' : 'Unidades IQVIA';

    function periodCells(p, isLast) {
      var sep = isLast ? '' : ' mp-sep';
      return ''
        + '<td class="mp-num">' + fmtInt(p.market_prev) + '</td>'
        + '<td class="mp-num">' + arrow(p.market_curr, p.market_prev) + fmtInt(p.market_curr) + '</td>'
        + '<td class="mp-num">' + fmtPct(p.ms_prev) + '</td>'
        + '<td class="mp-num">' + arrow(p.ms_curr, p.ms_prev) + fmtPct(p.ms_curr) + '</td>'
        + '<td class="mp-ie ' + ieClass(p.ie) + '">' + (p.ie == null ? '—' : p.ie) + '</td>'
        + '<td class="' + varppClass(p.var_pp) + sep + '">' + (p.var_pp == null ? '—' : (p.var_pp > 0 ? '+' : '') + p.var_pp.toFixed(2) + ' pp') + '</td>';
    }

    var rows = data.families.map(function(f){
      return '<tr>'
        + '<td class="mp-fam">' + f.family + '</td>'
        + periodCells(f.periods.mat,       false)
        + periodCells(f.periods.ytd,       false)
        + periodCells(f.periods.mes,       false)
        + periodCells(f.periods.trimestre, true)
        + '</tr>';
    }).join('');

    container.innerHTML = ''
      + '<div class="mp-wrap">'
      + '<table class="mp-table">'
      + '<colgroup>'
      + '<col style="width:9%">'
      + '<col span="6" style="width:3.8%">'   // MAT 6 cols
      + '<col span="6" style="width:3.8%">'   // YTD 6 cols
      + '<col span="6" style="width:3.8%">'   // MES 6 cols
      + '<col span="6" style="width:3.8%">'   // TRIM 6 cols
      + '</colgroup>'
      + '<thead>'
      + '<tr class="mp-group-row">'
      +   '<th rowspan="2" class="mp-fam-th">Marca</th>'
      +   '<th colspan="6" class="mp-g mp-g-mat">MAT <span class="mp-lbl">' + lbls.mat + '</span></th>'
      +   '<th colspan="6" class="mp-g mp-g-ytd">YTD <span class="mp-lbl">' + lbls.ytd + '</span></th>'
      +   '<th colspan="6" class="mp-g mp-g-mes">MES <span class="mp-lbl">' + lbls.mes + '</span></th>'
      +   '<th colspan="6" class="mp-g mp-g-trim">TRIM <span class="mp-lbl">' + lbls.trimestre + '</span></th>'
      + '</tr>'
      + '<tr class="mp-sub-row">'
      +   ['mat','ytd','mes','trim'].map(function(grp){
            return ['<th class="mp-sh mp-sh-'+grp+'">U Ant</th>',
                    '<th class="mp-sh mp-sh-'+grp+'">U Act</th>',
                    '<th class="mp-sh mp-sh-'+grp+'">MS% Ant</th>',
                    '<th class="mp-sh mp-sh-'+grp+'">MS% Act</th>',
                    '<th class="mp-sh mp-sh-'+grp+'">IE</th>',
                    '<th class="mp-sh mp-sh-'+grp+' mp-sep">Var pp</th>'].join('');
          }).join('')
      + '</tr>'
      + '</thead>'
      + '<tbody>' + rows + '</tbody>'
      + '</table>'
      + '</div>';
  }

  function renderMultiPeriodTable(containerId, opts) {
    var el = document.getElementById(containerId);
    if (!el) return;
    opts = opts || {};
    // Data source priority: opts.data > window.OTC_DASHBOARD > window.D
    var D = opts.data
         || (typeof global.OTC_DASHBOARD !== 'undefined' ? global.OTC_DASHBOARD : null)
         || (typeof global.D !== 'undefined' ? global.D : null);
    if (!D) { el.innerHTML = '<div style="padding:12px;color:#9ca3af;font-size:11px;">Sin datos disponibles</div>'; return; }
    var data = null;
    if (opts.source === 'recetas') data = buildRecetasFamilies(D);
    else                            data = buildIqviaFamilies(D);
    renderTable(el, data, opts);
  }

  global.renderMultiPeriodTable = renderMultiPeriodTable;
})(window);
