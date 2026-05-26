"""Patch Venta Interna en las 6 lineas (cardio, ATB, respi, mujer, SNC, derma)
para usar el mismo template tabla que OTC: 1 fila por producto, monthly Venta +
columnas Venta total / Estim. total / %Cumplimiento.

Reemplaza:
  - HTML section <div class="sec" id="s-bud">..</div>
  - function renderBudget() {...}
  - function renderBudPills() {...} (no-op)
  - function setBP(p) {...} (no-op + renderBudget)

Mantiene:
  - renderBudYr() + setBY() (year switcher)
  - bYear / bProd state
  - Cualquier helper auxiliar como getIQVIAReal2026() si existe.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FILES = [
    'cardio/index.html',
    'ATB/index.html',
    'OTC/index.html',
    'respiratorio/index.html',
    'mujer/index.html',
    'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# --- HTML section template ---
NEW_HTML_SECTION = '''<div class="sec" id="s-bud">
    <div class="sec-hd"><span class="sec-num">Venta Interna</span><h2 class="sec-title">Venta Interna vs Estimado de Ventas</h2></div>
    <p class="sec-sub" id="bud-copy">Unidades mensuales: venta interna Siegfried vs estimado de ventas · % cumplimiento por producto</p>
    <div class="card">
      <div class="ctrl-row">
        <div class="pill-group" id="bud-pills" style="display:none;"></div>
        <div style="margin-left:auto;"><div class="yr-ctrl" id="bud-yr"></div></div>
      </div>
      <div id="bud-table-wrap" style="overflow-x:hidden;margin-top:8px;width:100%;">
        <table id="bud-table" style="width:100%;table-layout:fixed;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:10.5px;">
          <colgroup id="bud-table-cols"></colgroup>
          <thead id="bud-table-head"></thead>
          <tbody id="bud-table-body"></tbody>
          <tfoot id="bud-table-foot"></tfoot>
        </table>
      </div>
    </div>
  </div>'''

# --- renderBudget function template ---
# Layout: 1 fila por producto. Cada mes tiene 3 SUB-COLUMNAS (V/E/%).
# Total cols: 1 (Producto) + 12 meses × 3 sub-cols + 3 sub-cols Total = 40 cols.
NEW_RENDER_BUDGET = '''function renderBudget(){
  var BUD_PRODS_LOCAL = Object.keys(D.budget||{});
  var MESES_L = (typeof MESES!=='undefined' && MESES.length===12) ? MESES : ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  // Compact format: 1234 -> 1.2k, 1234567 -> 1.2M. Default to '—' for null.
  var fmtU = function(n){
    if(n==null) return '—';
    var x = Math.abs(+n||0);
    if(x===0) return '0';
    if(x>=1e6) return (n/1e6).toFixed(x>=1e7?1:2).replace(/\\.?0+$/,'')+'M';
    if(x>=1e3) return (n/1e3).toFixed(x>=1e4?0:1).replace(/\\.0$/,'')+'k';
    return Math.round(n).toString();
  };
  var pctColor = function(p){
    if(p == null) return '#9ca3af';
    if(p >= 100) return '#16a34a';
    if(p >= 85)  return '#d97706';
    return '#b01e1e';
  };
  var pctBg = function(p){
    if(p == null) return 'transparent';
    if(p >= 100) return 'rgba(22,163,74,.08)';
    if(p >= 85)  return 'rgba(217,119,6,.08)';
    return 'rgba(176,30,30,.08)';
  };
  var rows = [];
  var totalsReal = new Array(12).fill(0);
  var totalsBud  = new Array(12).fill(0);
  var hasReal = new Array(12).fill(false);
  var hasBud  = new Array(12).fill(false);
  BUD_PRODS_LOCAL.forEach(function(prod){
    var yo = (D.budget[prod]||{})[bYear] || {};
    var real = (yo.real || []).slice();
    var bud  = (yo.budget || []).slice();
    if(bYear==='2026' && (typeof getIQVIAReal2026==='function') && !real.some(function(v){return v!=null;})){
      var iqv = getIQVIAReal2026(prod);
      if(iqv) real = iqv;
    }
    while(real.length < 12) real.push(null);
    while(bud.length  < 12) bud.push(null);
    var totR = 0, totB = 0;
    for(var i=0;i<12;i++){
      var rv = real[i], bv = bud[i];
      if(rv != null){ totR += +rv || 0; totalsReal[i] += +rv || 0; hasReal[i] = true; }
      if(bv != null && +bv > 0){ totB += +bv || 0; totalsBud[i] += +bv || 0; hasBud[i] = true; }
    }
    rows.push({prod: prod, real: real, bud: bud, totR: totR, totB: totB});
  });
  // Colgroup: 1 col Producto + 36 sub-cols (12 meses × 3) + 3 sub-cols Total
  var cg = document.getElementById('bud-table-cols');
  if(cg){
    var cgh = '<col style="width:9%">';                 // Producto
    for(var ci=0;ci<12;ci++){
      cgh += '<col style="width:2.4%">';                // V del mes
      cgh += '<col style="width:2.4%">';                // E del mes
      cgh += '<col style="width:2.4%">';                // % del mes
    }
    cgh += '<col style="width:2.5%">';                  // V Total
    cgh += '<col style="width:2.5%">';                  // E Total
    cgh += '<col style="width:2.5%">';                  // % Total
    cg.innerHTML = cgh;
  }
  // Header (2 filas): row 1 = MESES con colspan=3, row 2 = sub-labels V/E/%
  var head = document.getElementById('bud-table-head');
  if(head){
    var hh = '<tr style="border-bottom:1px solid #e5e7eb;">';
    hh += '<th rowspan="2" style="text-align:left;padding:6px 6px;font-size:9px;font-weight:700;color:#374151;letter-spacing:.06em;text-transform:uppercase;vertical-align:bottom;border-right:1px solid #e5e7eb;">Producto</th>';
    MESES_L.forEach(function(m, mi){
      var sep = (mi%2===0) ? 'background:#fafbfc;' : '';
      hh += '<th colspan="3" style="text-align:center;padding:4px 2px;font-size:9px;font-weight:700;color:#374151;letter-spacing:.04em;text-transform:uppercase;border-bottom:1px solid #f3f4f6;'+sep+'">'+m+'</th>';
    });
    hh += '<th colspan="3" style="text-align:center;padding:4px 2px;font-size:9px;font-weight:700;color:#b01e1e;letter-spacing:.04em;text-transform:uppercase;border-left:2px solid #fde2e2;background:#fef2f2;">Total</th>';
    hh += '</tr>';
    // Row 2: V / E / % sub-headers (12 meses + Total)
    hh += '<tr style="border-bottom:1px solid #e5e7eb;">';
    for(var ji=0;ji<12;ji++){
      var sep = (ji%2===0) ? 'background:#fafbfc;' : '';
      hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#b01e1e;letter-spacing:.02em;text-transform:uppercase;'+sep+'">V</th>';
      hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#1f4ba6;letter-spacing:.02em;text-transform:uppercase;'+sep+'">E</th>';
      hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#6b7280;letter-spacing:.02em;text-transform:uppercase;'+sep+'">%</th>';
    }
    hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#b01e1e;letter-spacing:.02em;text-transform:uppercase;border-left:2px solid #fde2e2;background:#fef2f2;">V</th>';
    hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#1f4ba6;letter-spacing:.02em;text-transform:uppercase;background:#fef2f2;">E</th>';
    hh += '<th style="text-align:right;padding:3px 2px;font-size:7.5px;font-weight:700;color:#6b7280;letter-spacing:.02em;text-transform:uppercase;background:#fef2f2;">%</th>';
    hh += '</tr>';
    head.innerHTML = hh;
  }
  // Body: 1 fila por producto, cada mes = 3 celdas (V/E/%)
  var body = document.getElementById('bud-table-body');
  if(body){
    var html = '';
    rows.forEach(function(r){
      html += '<tr style="border-bottom:1px solid #f3f4f6;">';
      html += '<td title="'+r.prod+'" style="padding:4px 6px;font-weight:700;font-size:10px;color:#111827;font-family:\\'IBM Plex Sans\\',sans-serif;background:#fafbfc;border-right:1px solid #e5e7eb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+r.prod+'</td>';
      for(var i=0;i<12;i++){
        var rv = r.real[i], bv = r.bud[i];
        var pct = (bv && +bv>0 && rv!=null) ? (+rv / +bv * 100) : null;
        var pctStr = pct==null ? '—' : pct.toFixed(0)+'%';
        var monthBg = (i%2===0) ? 'background:#fafbfc;' : '';
        var pctCellBg = pctBg(pct);
        var bgFinal = pctCellBg !== 'transparent' ? pctCellBg : monthBg.replace('background:','') || 'transparent';
        html += '<td style="padding:3px 2px;text-align:right;color:#111827;font-size:9.5px;'+monthBg+'">'+(rv==null?'—':fmtU(rv))+'</td>';
        html += '<td style="padding:3px 2px;text-align:right;color:#1f4ba6;font-size:9.5px;'+monthBg+'">'+(bv==null||+bv<=0?'—':fmtU(bv))+'</td>';
        html += '<td style="padding:3px 2px;text-align:right;font-weight:700;font-size:9.5px;color:'+pctColor(pct)+';background:'+(pctCellBg!=='transparent'?pctCellBg:(i%2===0?'#fafbfc':'transparent'))+';">'+pctStr+'</td>';
      }
      // Total: 3 sub-cols
      var totPct = (r.totB>0 && r.totR>0) ? (r.totR/r.totB*100) : null;
      var totPctStr = totPct==null ? '—' : totPct.toFixed(0)+'%';
      var totBStr = r.totB>0 ? fmtU(r.totB) : '—';
      html += '<td style="padding:3px 2px;text-align:right;font-weight:700;color:#b01e1e;font-size:9.5px;border-left:2px solid #fde2e2;background:#fef2f2;">'+fmtU(r.totR)+'</td>';
      html += '<td style="padding:3px 2px;text-align:right;color:#1f4ba6;font-weight:700;font-size:9.5px;background:#fef2f2;">'+totBStr+'</td>';
      html += '<td style="padding:3px 2px;text-align:right;font-weight:800;font-size:9.5px;color:'+pctColor(totPct)+';background:'+(pctBg(totPct)!=='transparent'?pctBg(totPct):'#fef2f2')+';">'+totPctStr+'</td>';
      html += '</tr>';
    });
    body.innerHTML = html;
  }
  // Footer: TOTAL LINEA (1 fila, mismo formato que producto)
  var foot = document.getElementById('bud-table-foot');
  if(foot){
    var grandReal = totalsReal.reduce(function(a,b){return a+b;},0);
    var grandBud  = totalsBud.reduce(function(a,b){return a+b;},0);
    var grandPct  = (grandBud > 0 && grandReal > 0) ? (grandReal/grandBud*100) : null;
    var fhtml = '<tr style="border-top:2px solid #b01e1e;background:#fef2f2;font-weight:700;">';
    fhtml += '<td style="padding:5px 6px;color:#111827;text-transform:uppercase;letter-spacing:.04em;font-size:9px;font-weight:800;border-right:1px solid #fecaca;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">TOTAL LÍNEA</td>';
    for(var fj=0;fj<12;fj++){
      var rr = totalsReal[fj], bb = totalsBud[fj];
      var mpct = (bb>0 && rr>0) ? (rr/bb*100) : null;
      var mpctStr = mpct==null ? '—' : mpct.toFixed(0)+'%';
      var tv = hasReal[fj] ? fmtU(rr) : '—';
      var tb = hasBud[fj]  ? fmtU(bb) : '—';
      fhtml += '<td style="padding:4px 2px;text-align:right;color:#111827;font-size:9.5px;font-weight:700;">'+tv+'</td>';
      fhtml += '<td style="padding:4px 2px;text-align:right;color:#1f4ba6;font-size:9.5px;font-weight:700;">'+tb+'</td>';
      fhtml += '<td style="padding:4px 2px;text-align:right;font-weight:800;font-size:9.5px;color:'+pctColor(mpct)+';background:'+pctBg(mpct)+';">'+mpctStr+'</td>';
    }
    var gpctStr = grandPct == null ? '—' : grandPct.toFixed(0)+'%';
    var gbStr   = grandBud>0 ? fmtU(grandBud) : '—';
    fhtml += '<td style="padding:4px 2px;text-align:right;color:#b01e1e;font-weight:800;font-size:9.5px;border-left:2px solid #fde2e2;">'+fmtU(grandReal)+'</td>';
    fhtml += '<td style="padding:4px 2px;text-align:right;color:#1f4ba6;font-weight:800;font-size:9.5px;">'+gbStr+'</td>';
    fhtml += '<td style="padding:4px 2px;text-align:right;font-weight:800;font-size:9.5px;color:'+pctColor(grandPct)+';background:'+pctBg(grandPct)+';">'+gpctStr+'</td>';
    fhtml += '</tr>';
    foot.innerHTML = fhtml;
  }
}'''

NEW_BUD_PILLS = '''function renderBudPills(){
  var el = document.getElementById('bud-pills');
  if(el) el.innerHTML = '';
}'''

NEW_SET_BP = '''function setBP(p){ /* deprecated: tabla muestra todos los productos */ renderBudget(); }'''


def find_matching_brace(text, start):
    """Find the position of the matching closing brace starting from an opening brace at start."""
    depth = 0
    i = start
    in_str = False
    str_quote = None
    in_re = False
    in_line_comment = False
    in_block_comment = False
    in_template = False
    while i < len(text):
        c = text[i]
        nxt = text[i+1] if i+1 < len(text) else ''
        if in_line_comment:
            if c == '\n': in_line_comment = False
            i += 1; continue
        if in_block_comment:
            if c == '*' and nxt == '/':
                in_block_comment = False; i += 2; continue
            i += 1; continue
        if in_str:
            if c == '\\': i += 2; continue
            if c == str_quote:
                in_str = False; str_quote = None
            i += 1; continue
        if in_template:
            if c == '\\': i += 2; continue
            if c == '`':
                in_template = False
            i += 1; continue
        if c == '/' and nxt == '/':
            in_line_comment = True; i += 2; continue
        if c == '/' and nxt == '*':
            in_block_comment = True; i += 2; continue
        if c in ('"', "'"):
            in_str = True; str_quote = c
            i += 1; continue
        if c == '`':
            in_template = True; i += 1; continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def find_matching_div(text, start):
    """Find the closing </div> for the <div> that contains 'start' position.
    Returns position right after the closing </div>."""
    depth = 0
    i = start
    while i < len(text):
        # Look ahead for either <div or </div
        nxt_open = text.find('<div', i)
        nxt_close = text.find('</div>', i)
        if nxt_close < 0:
            return -1
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            if depth == 0:
                return nxt_close + len('</div>')
            i = nxt_close + len('</div>')
    return -1


def replace_html_section(text):
    """Replace <div class="sec" id="s-bud">...</div> with new template."""
    m = re.search(r'<div class="sec" id="s-bud">', text)
    if not m: return text, 'NO s-bud section'
    start = m.start()
    # find the </div> after the opening
    inner_start = m.end()
    # First <div is at start; we need to balance starting from depth=1
    depth = 1
    i = inner_start
    while i < len(text) and depth > 0:
        nxt_open = text.find('<div', i)
        nxt_close = text.find('</div>', i)
        if nxt_close < 0: return text, 'unmatched div'
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            i = nxt_close + len('</div>')
    end = i  # position right after the final </div>
    return text[:start] + NEW_HTML_SECTION + text[end:], 'OK'


def replace_function(text, fn_name, new_def):
    """Replace function fn_name(){...} with new_def. Returns (new_text, status)."""
    pat = re.compile(r'function\s+' + re.escape(fn_name) + r'\s*\([^)]*\)\s*\{')
    m = pat.search(text)
    if not m: return text, f'NO {fn_name}()'
    open_brace = m.end() - 1
    close = find_matching_brace(text, open_brace)
    if close < 0: return text, f'unmatched brace for {fn_name}'
    return text[:m.start()] + new_def + text[close+1:], 'OK'


def patch_file(path: Path):
    is_inline = path.suffix == '.html'
    enc = 'utf-8'
    t = path.read_text(encoding=enc, errors='replace')
    orig = t
    # Replace HTML section
    t, status_html = replace_html_section(t)
    # Replace renderBudget
    t, status_fn = replace_function(t, 'renderBudget', NEW_RENDER_BUDGET)
    # Replace renderBudPills (no-op)
    t, status_pills = replace_function(t, 'renderBudPills', NEW_BUD_PILLS)
    # Replace setBP (no-op + renderBudget)
    t, status_setbp = replace_function(t, 'setBP', NEW_SET_BP)
    if t == orig:
        return f'{path.name}: no changes (html={status_html}, fn={status_fn}, pills={status_pills}, setbp={status_setbp})'
    path.write_text(t, encoding=enc, newline='')
    return f'{path.name}: html={status_html}, fn={status_fn}, pills={status_pills}, setbp={status_setbp}'


def main():
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  MISS: {f}'); continue
        result = patch_file(p)
        print(f'  {result}')


if __name__ == '__main__':
    main()
