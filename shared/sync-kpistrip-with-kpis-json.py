"""Sincroniza D.kpiStrip de cada data.js con los valores canonicos de
kpis.json. Para que el strip arriba del dashboard muestre exactamente los
mismos numeros que el hub /kpis.html y la tabla 'Apertura por familia'.

Mapeo kpis.json -> data.js kpiStrip:
  units_sie.ie       -> ie_ytd / ie_mat   (IE vs-market base 100)
  ms_units.curr      -> ms_ytd / ms_mat   (MS% del periodo)
  units_sie.curr     -> units_ytd / units_mat
  units_sie.prev     -> units_ytd25 / units_mat25
  mercado_units.curr -> mkt_ytd26 / mkt_mat26
  ms_recetas.curr    -> ms_rec
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KJ = json.loads((REPO / 'kpis.json').read_text(encoding='utf-8'))
LINES = {l['key']: l for l in KJ['lines']}

MAP = {
    'cardio':  ('cardio', 'cardio/data.js', False),
    'antibio': ('antibio', 'ATB/data.js', False),
    'otx':     ('otx', 'OTC/data.js', False),
    'resp':    ('resp', 'respiratorio/data.js', False),
    'mujer':   ('mujer', 'mujer/data.js', False),
    'snc':     ('snc', 'SNC/data.js', False),
    'derma':   ('derma', 'dermatologia/data.js', False),
}


def find_obj(text, is_inline):
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        ob = text.index('{', m.start() + 8)
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
        ob = text.index('{', m.end())
    return ob


def patch_line(key, path_rel, is_inline):
    line = LINES.get(key)
    if not line:
        return f'NO kpis.json entry for {key}'
    k_ytd = line['kpis']['ytd']
    k_mat = line['kpis']['mat']
    p = REPO / path_rel
    if not p.is_file():
        return f'MISS {path_rel}'
    text = p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    ob = find_obj(text, is_inline)
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    prefix = text[:ob]; suffix = text[ob+end:]

    ks = D.setdefault('kpiStrip', {})
    before = json.dumps(ks)
    ks['ie_ytd'] = k_ytd['units_sie']['ie']
    ks['ie_mat'] = k_mat['units_sie']['ie']
    ks['ms_ytd'] = k_ytd['ms_units']['curr']
    ks['ms_mat'] = k_mat['ms_units']['curr']
    ks['units_ytd'] = k_ytd['units_sie']['curr']
    ks['units_ytd25'] = k_ytd['units_sie']['prev']
    ks['units_mat'] = k_mat['units_sie']['curr']
    ks['units_mat25'] = k_mat['units_sie']['prev']
    ks['mkt_ytd26'] = k_ytd['mercado_units']['curr']
    ks['mkt_mat26'] = k_mat['mercado_units']['curr']
    if k_ytd.get('ms_recetas', {}).get('curr') is not None:
        ks['ms_rec'] = k_ytd['ms_recetas']['curr']
        ks['sie_rec'] = k_ytd.get('recetas_sie', {}).get('curr')
        ks['tot_rec'] = k_ytd.get('mercado_recetas', {}).get('curr')
    after = json.dumps(ks)
    if before == after:
        return 'no changes'
    p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                 encoding='utf-8', newline='')
    return 'OK'


def main():
    for key, (k, path, inline) in MAP.items():
        print(f'  {key:8s}: {patch_line(key, path, inline)}')


if __name__ == '__main__':
    main()
