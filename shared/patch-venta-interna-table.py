"""Patch Venta Interna en las 6 lineas (cardio, ATB, respi, mujer, SNC, derma)
para usar el mismo template tabla que OTC: 1 fila por producto, monthly Venta +
columnas Venta total / Presup total / %Cumplimiento.

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
    <div class="sec-hd"><span class="sec-num">Venta Interna</span><h2 class="sec-title">Venta Interna vs Presupuesto</h2></div>
    <p class="sec-sub" id="bud-copy">Unidades mensuales: venta interna Siegfried vs presupuesto · % cumplimiento por producto</p>
    <div class="card">
      <div class="ctrl-row">
        <div class="pill-group" id="bud-pills" style="display:none;"></div>
        <div style="margin-left:auto;"><div class="yr-ctrl" id="bud-yr"></div></div>
      </div>
      <div id="bud-table-wrap" style="overflow-x:auto;margin-top:8px;">
        <table id="bud-table" style="width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:11px;">
          <thead id="bud-table-head"></thead>
          <tbody id="bud-table-body"></tbody>
          <tfoot id="bud-table-foot"></tfoot>
        </table>
      </div>
    </div>
  </div>'''

# --- renderBudget function template ---
# Layout: 3 sub-filas por producto (Venta / Presup / %Cumpl) con comparacion
# mes a mes en las 12 columnas + columna TOTAL al final.
NEW_RENDER_BUDGET = '''function renderBudget(){
  var BUD_PRODS_LOCAL = Object.keys(D.budget||{});
  var MESES_L = (typeof MESES!=='undefined' && MESES.length===12) ? MESES : ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  var fmtU = function(n){ return Number(n||0).toLocaleString('es-AR'); };
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
  // Header (1 fila): PRODUCTO | METRICA | Ene .. Dic | TOTAL
  var head = document.getElementById('bud-table-head');
  if(head){
    var hh = '<tr style="border-bottom:1px solid #e5e7eb;">';
    hh += '<th style="text-align:left;padding:8px 10px;font-size:10px;font-weight:700;color:#374151;letter-spacing:.08em;text-transform:uppercase;">Producto</th>';
    hh += '<th style="text-align:left;padding:8px 8px;font-size:9px;font-weight:600;color:#6b7280;letter-spacing:.05em;text-transform:uppercase;"></th>';
    MESES_L.forEach(function(m){
      hh += '<th style="text-align:right;padding:8px 8px;font-size:10px;font-weight:700;color:#374151;letter-spacing:.06em;text-transform:uppercase;">'+m+'</th>';
    });
    hh += '<th style="text-align:right;padding:8px 10px;font-size:10px;font-weight:700;color:#b01e1e;letter-spacing:.06em;text-transform:uppercase;border-left:2px solid #fde2e2;">Total</th>';
    hh += '</tr>';
    head.innerHTML = hh;
  }
  // Body: 3 filas por producto
  var body = document.getElementById('bud-table-body');
  if(body){
    var html = '';
    rows.forEach(function(r, idx){
      var rowBorderTop = idx===0 ? '' : 'border-top:1px solid #e5e7eb;';
      // Row 1: Venta
      html += '<tr style="'+rowBorderTop+'">';
      html += '<td rowspan="3" style="padding:8px 10px;font-weight:700;color:#111827;font-family:\\'IBM Plex Sans\\',sans-serif;vertical-align:top;background:#fafbfc;border-right:1px solid #e5e7eb;">'+r.prod+'</td>';
      html += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#b01e1e;letter-spacing:.04em;text-transform:uppercase;">Venta</td>';
      r.real.forEach(function(v){
        html += '<td style="padding:4px 8px;text-align:right;color:#111827;">'+(v==null?'—':fmtU(Math.round(v)))+'</td>';
      });
      html += '<td style="padding:4px 10px;text-align:right;font-weight:700;color:#b01e1e;border-left:2px solid #fde2e2;">'+fmtU(Math.round(r.totR))+'</td>';
      html += '</tr>';
      // Row 2: Presup
      html += '<tr>';
      html += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#1f4ba6;letter-spacing:.04em;text-transform:uppercase;">Presup</td>';
      r.bud.forEach(function(v){
        var disp = (v==null || +v<=0) ? '—' : fmtU(Math.round(v));
        html += '<td style="padding:4px 8px;text-align:right;color:#1f4ba6;">'+disp+'</td>';
      });
      var totBStr = r.totB>0 ? fmtU(Math.round(r.totB)) : '—';
      html += '<td style="padding:4px 10px;text-align:right;color:#1f4ba6;font-weight:700;border-left:2px solid #fde2e2;">'+totBStr+'</td>';
      html += '</tr>';
      // Row 3: % Cumpl (mes a mes)
      html += '<tr style="border-bottom:1px solid #f3f4f6;">';
      html += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.04em;text-transform:uppercase;">% Cumpl</td>';
      for(var i=0;i<12;i++){
        var rv = r.real[i], bv = r.bud[i];
        var pct = (bv && +bv>0 && rv!=null) ? (+rv / +bv * 100) : null;
        var pctStr = pct==null ? '—' : pct.toFixed(0)+'%';
        html += '<td style="padding:4px 8px;text-align:right;font-weight:700;color:'+pctColor(pct)+';background:'+pctBg(pct)+';">'+pctStr+'</td>';
      }
      var totPct = (r.totB>0 && r.totR>0) ? (r.totR/r.totB*100) : null;
      var totPctStr = totPct==null ? '—' : totPct.toFixed(1)+'%';
      html += '<td style="padding:4px 10px;text-align:right;font-weight:800;color:'+pctColor(totPct)+';background:'+pctBg(totPct)+';border-left:2px solid #fde2e2;">'+totPctStr+'</td>';
      html += '</tr>';
    });
    body.innerHTML = html;
  }
  // Footer: TOTAL LINEA (3 filas)
  var foot = document.getElementById('bud-table-foot');
  if(foot){
    var grandReal = totalsReal.reduce(function(a,b){return a+b;},0);
    var grandBud  = totalsBud.reduce(function(a,b){return a+b;},0);
    var grandPct  = (grandBud > 0 && grandReal > 0) ? (grandReal/grandBud*100) : null;
    var fhtml = '';
    // Row 1: TOTAL LINEA - Venta
    fhtml += '<tr style="border-top:2px solid #b01e1e;background:#fef2f2;font-weight:700;">';
    fhtml += '<td rowspan="3" style="padding:8px 10px;color:#111827;text-transform:uppercase;letter-spacing:.04em;font-size:11px;font-weight:800;vertical-align:top;border-right:1px solid #fecaca;">TOTAL LÍNEA</td>';
    fhtml += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#b01e1e;letter-spacing:.04em;text-transform:uppercase;">Venta</td>';
    for(var j=0;j<12;j++){
      var tv = hasReal[j] ? fmtU(Math.round(totalsReal[j])) : '—';
      fhtml += '<td style="padding:4px 8px;text-align:right;color:#111827;">'+tv+'</td>';
    }
    fhtml += '<td style="padding:4px 10px;text-align:right;color:#b01e1e;font-weight:800;border-left:2px solid #fde2e2;">'+fmtU(Math.round(grandReal))+'</td>';
    fhtml += '</tr>';
    // Row 2: TOTAL LINEA - Presup
    fhtml += '<tr style="background:#fef2f2;font-weight:700;">';
    fhtml += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#1f4ba6;letter-spacing:.04em;text-transform:uppercase;">Presup</td>';
    for(var k=0;k<12;k++){
      var tb = hasBud[k] ? fmtU(Math.round(totalsBud[k])) : '—';
      fhtml += '<td style="padding:4px 8px;text-align:right;color:#1f4ba6;">'+tb+'</td>';
    }
    var gbStr = grandBud>0 ? fmtU(Math.round(grandBud)) : '—';
    fhtml += '<td style="padding:4px 10px;text-align:right;color:#1f4ba6;font-weight:800;border-left:2px solid #fde2e2;">'+gbStr+'</td>';
    fhtml += '</tr>';
    // Row 3: TOTAL LINEA - % Cumpl
    fhtml += '<tr style="background:#fef2f2;font-weight:700;">';
    fhtml += '<td style="padding:4px 8px;font-size:9px;font-weight:700;color:#6b7280;letter-spacing:.04em;text-transform:uppercase;">% Cumpl</td>';
    for(var n=0;n<12;n++){
      var rr = totalsReal[n], bb = totalsBud[n];
      var mpct = (bb>0 && rr>0) ? (rr/bb*100) : null;
      var mpctStr = mpct==null ? '—' : mpct.toFixed(0)+'%';
      fhtml += '<td style="padding:4px 8px;text-align:right;font-weight:800;color:'+pctColor(mpct)+';background:'+pctBg(mpct)+';">'+mpctStr+'</td>';
    }
    var gpctStr = grandPct == null ? '—' : grandPct.toFixed(1)+'%';
    fhtml += '<td style="padding:4px 10px;text-align:right;font-weight:800;color:'+pctColor(grandPct)+';background:'+pctBg(grandPct)+';border-left:2px solid #fde2e2;">'+gpctStr+'</td>';
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
