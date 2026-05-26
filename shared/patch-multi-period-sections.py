"""Agrega la tabla multi-período (MAT/YTD/MES/TRIM × 6 cols) al final de las
secciones Mercado IQVIA (#s-perf) y Recetas (#s-rec) en las 7 líneas.

Cambios por línea:
  1. <link rel="stylesheet" href="../shared/multi-period-table.css"> en <head>
  2. <script src="../shared/multi-period-table.js"></script> antes de </body>
  3. <div class="card mp-summary-card"><div id="mp-iqvia-wrap"></div></div>
     insertado dentro de <div class="sec" id="s-perf"> antes de su </div> de cierre
  4. Idem para Recetas (<div id="mp-rec-wrap">) dentro de #s-rec
  5. <script> inline al final del body para invocar renderMultiPeriodTable
     en DOMContentLoaded

Idempotente: si ya estan los markers (mp-iqvia-wrap / mp-rec-wrap), no agrega
nada de nuevo.

NO modifica el contenido existente de las secciones, solo agrega cards al final.
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

CSS_LINK = '<link rel="stylesheet" href="../shared/multi-period-table.css">'
JS_TAG   = '<script src="../shared/multi-period-table.js"></script>'

IQVIA_CARD = '''<div class="card mp-summary-card" style="margin-top:14px;">
      <p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">Comparativa multi-periodo &middot; Mercado IQVIA</p>
      <div id="mp-iqvia-wrap"></div>
    </div>'''

REC_CARD = '''<div class="card mp-summary-card" style="margin-top:14px;">
      <p style="font-size:9px;font-weight:700;color:#4b5563;letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;">Comparativa multi-periodo &middot; Recetas (CloseUp)</p>
      <div id="mp-rec-wrap"></div>
    </div>'''

INIT_SCRIPT = '''<script>
// Multi-period summary tables (added by patch-multi-period-sections.py).
// Pasa D directamente para soportar tanto window.OTC_DASHBOARD como const D inline.
(function(){
  function getData(){
    try { if (typeof OTC_DASHBOARD !== 'undefined') return OTC_DASHBOARD; } catch(e){}
    try { if (typeof D !== 'undefined') return D; } catch(e){}
    return null;
  }
  function init(){
    if (typeof window.renderMultiPeriodTable !== 'function') return;
    var data = getData();
    if (!data) return;
    try { window.renderMultiPeriodTable('mp-iqvia-wrap', { source: 'iqvia', data: data }); } catch(e){ console.error('[mp-iqvia]', e); }
    try { window.renderMultiPeriodTable('mp-rec-wrap',   { source: 'recetas', data: data }); } catch(e){ console.error('[mp-rec]', e); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else setTimeout(init, 50);
})();
</script>'''


def find_section_close(text, start):
    """Given a position 'start' inside a <div class='sec'>, find the closing
    </div> at the same nesting level (depth=1 when entering).
    Returns the position of that closing </div>."""
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        nxt_open  = text.find('<div', i)
        nxt_close = text.find('</div>', i)
        if nxt_close < 0: return -1
        if nxt_open >= 0 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            if depth == 0: return nxt_close
            i = nxt_close + len('</div>')
    return -1


def inject_card(text, section_id, card_html, marker_id):
    """Inserta card_html antes del </div> de cierre de la seccion section_id."""
    if marker_id in text:
        return text, 'already present'
    m = re.search(r'<div class="sec" id="' + re.escape(section_id) + r'">', text)
    if not m: return text, f'NO section #{section_id}'
    close_pos = find_section_close(text, m.end())
    if close_pos < 0: return text, f'unmatched </div> for #{section_id}'
    # Insert card_html before the closing </div>, with proper indentation
    return text[:close_pos] + '    ' + card_html + '\n  ' + text[close_pos:], 'OK'


def inject_css_link(text):
    if 'multi-period-table.css' in text:
        return text, 'already'
    # Insert before </head>
    idx = text.find('</head>')
    if idx < 0: return text, 'no </head>'
    return text[:idx] + '  ' + CSS_LINK + '\n' + text[idx:], 'OK'


def inject_js_tag(text):
    if 'multi-period-table.js' in text:
        return text, 'already'
    # Insert before </body>
    idx = text.rfind('</body>')
    if idx < 0:
        # No </body>? insert before </html>
        idx = text.rfind('</html>')
        if idx < 0: return text, 'no </body> or </html>'
    return text[:idx] + JS_TAG + '\n' + INIT_SCRIPT + '\n' + text[idx:], 'OK'


def patch_file(path: Path):
    t = path.read_text(encoding='utf-8', errors='replace')
    orig = t
    statuses = []
    t, s = inject_css_link(t);                             statuses.append(f'css={s}')
    t, s = inject_card(t, 's-perf', IQVIA_CARD, 'mp-iqvia-wrap'); statuses.append(f'iqvia={s}')
    t, s = inject_card(t, 's-rec',  REC_CARD,   'mp-rec-wrap');   statuses.append(f'rec={s}')
    t, s = inject_js_tag(t);                               statuses.append(f'js={s}')
    if t == orig:
        return f'{path.name}: no changes ({"; ".join(statuses)})'
    path.write_text(t, encoding='utf-8', newline='')
    return f'{path.name}: {"; ".join(statuses)}'


def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  MISS: {f}'); continue
        print(f'  {patch_file(p)}')


if __name__ == '__main__':
    main()
