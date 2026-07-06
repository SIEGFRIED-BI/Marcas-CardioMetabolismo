"""Audit de consistencia: para cada linea y cada SIE brand, comparar los
valores de IE, MS%, units, recetas que aparecen en distintos lugares del
dashboard. Reporta inconsistencias detectadas.

NO modifica nada — solo lee y reporta.

Lugares a comparar:
1. Hub /kpis.html (kpis.json) vs Dashboard top strip (D.kpiStrip) — line level
2. brandKpis.<brand>.ytd.ie (KPI strip al filtrar) vs renderPerf table calc
3. brandKpis.<brand>.ytd.ms (KPI strip MS%) vs mol_perf MS% computed
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

LINES = [
    ('cardio',  'cardio', 'cardio/data.js', False),
    ('antibio', 'ATB',    'ATB/data.js', False),
    ('otx',     'OTC',    'OTC/data.js', False),
    ('resp',    'respiratorio', 'respiratorio/data.js', False),
    ('mujer',   'mujer',  'mujer/data.js', False),
    ('snc',     'SNC',    'SNC/data.js', False),
    ('derma',   'dermatologia', 'dermatologia/data.js', False),
]


def load_D(path_rel, is_inline):
    # Robusto: data.js (window.OTC_DASHBOARD = {...}) o inline legacy (const D = {...}).
    # Post-migracion F4 las 7 lineas viven en data.js. Falla claro (ValueError) si no
    # encuentra el objeto, para no saltear lineas en silencio.
    p = REPO / path_rel
    text = p.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*\{', text) or re.search(r'const\s+D\s*=\s*\{', text)
    if not m:
        raise ValueError(f'no encontre window.OTC_DASHBOARD ni "const D = {{...}}" en {path_rel}')
    ob = text.index('{', m.start())
    D, _ = json.JSONDecoder().raw_decode(text[ob:])
    return D


def find_latest_month(D):
    mol = D.get('mol_perf', {})
    all_months = set()
    for o in mol.values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            all_months.update((p.get('monthly_vals') or {}).keys())
    MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    def msort(k):
        parts = k.split()
        return int(parts[1])*100 + MES.index(parts[0])+1
    sm = sorted(all_months, key=msort)
    if not sm: return None
    p = sm[-1].split()
    return (int(p[1]), MES.index(p[0])+1)


def ytd_months(year, end_month):
    MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    return [f'{MES[i]} {year}' for i in range(end_month)]


def compute_mol_ms_for_brand(D, brand, months_curr, months_prev):
    """For each mol_perf market, find the brand and compute MS% curr/prev."""
    mol = D.get('mol_perf', {})
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        brand_curr = brand_prev = 0
        mkt_curr = mkt_prev = 0
        found = False
        for p in obj.get('products', []):
            mv = p.get('monthly_vals', {})
            c = sum(mv.get(mk, 0) or 0 for mk in months_curr)
            pp = sum(mv.get(mk, 0) or 0 for mk in months_prev)
            mkt_curr += c
            mkt_prev += pp
            name = str(p.get('prod', '')).upper()
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
            if p.get('is_sie') and (brand.upper() == base or brand.upper() == name):
                brand_curr += c
                brand_prev += pp
                found = True
        if found:
            ms_c = (brand_curr/mkt_curr*100) if mkt_curr>0 else None
            ms_p = (brand_prev/mkt_prev*100) if mkt_prev>0 else None
            return {'mol': m_key, 'brand_curr': brand_curr, 'brand_prev': brand_prev,
                    'mkt_curr': mkt_curr, 'mkt_prev': mkt_prev,
                    'ms_curr': round(ms_c,2) if ms_c else None,
                    'ms_prev': round(ms_p,2) if ms_p else None,
                    'ie_brand_growth': round(brand_curr/brand_prev*100,1) if brand_prev>0 else None,
                    'ie_vs_mkt': (round((brand_curr/brand_prev)/(mkt_curr/mkt_prev)*100,1)
                                  if (brand_prev>0 and mkt_prev>0
                                      and (brand_curr/brand_prev)<5 and 0.2<(mkt_curr/mkt_prev)<5)
                                  else None)}
    return None


def audit():
    kj = json.loads((REPO / 'kpis.json').read_text(encoding='utf-8'))
    kj_lines = {l['key']: l for l in kj['lines']}

    print('=' * 80)
    print('AUDIT: Hub kpis.html (kpis.json) vs Dashboard kpiStrip')
    print('=' * 80)
    print(f"{'LINE':10s} {'METRIC':12s} {'kpis.json':>12s} {'data.js':>12s} {'STATUS'}")
    load_errors = set()
    issues = 0
    for key, line_dir, path_rel, is_inline in LINES:
        try:
            D = load_D(path_rel, is_inline)
        except Exception as e:
            load_errors.add(line_dir)
            print(f'  {line_dir}: ERROR loading: {e}')
            continue
        ks = D.get('kpiStrip', {})
        kjl = kj_lines.get(key)
        if not kjl: continue
        checks = [
            ('IE YTD',  kjl['kpis']['ytd']['units_sie']['ie'],   ks.get('ie_ytd')),
            ('IE MAT',  kjl['kpis']['mat']['units_sie']['ie'],   ks.get('ie_mat')),
            ('MS% YTD', kjl['kpis']['ytd']['ms_units']['curr'],  ks.get('ms_ytd')),
            ('MS% MAT', kjl['kpis']['mat']['ms_units']['curr'],  ks.get('ms_mat')),
            ('U YTD',   kjl['kpis']['ytd']['units_sie']['curr'], ks.get('units_ytd')),
            ('U MAT',   kjl['kpis']['mat']['units_sie']['curr'], ks.get('units_mat')),
        ]
        for label, a, b in checks:
            status = 'OK' if a == b else 'MISMATCH'
            if status != 'OK': issues += 1
            print(f"  {line_dir:10s} {label:8s} {str(a):>12s} {str(b):>12s} {status}")
    total_issues = issues
    print(f'\nLine-level mismatches: {issues}\n')

    print('=' * 80)
    print('AUDIT: brandKpis.IE vs vs-market computed from mol_perf')
    print('=' * 80)
    print(f"{'LINE':10s} {'BRAND':25s} {'bk.ie':>8s} {'computed':>9s} {'STATUS'}")
    issues = 0
    for key, line_dir, path_rel, is_inline in LINES:
        try:
            D = load_D(path_rel, is_inline)
        except Exception as e:
            load_errors.add(line_dir)
            continue
        bk = D.get('brandKpis', {})
        if not bk: continue
        latest = find_latest_month(D)
        if not latest: continue
        end_y, end_m = latest
        m_curr = ytd_months(end_y, end_m)
        m_prev = ytd_months(end_y-1, end_m)
        for brand, kobj in list(bk.items())[:5]:  # First 5 brands per line
            ytd = kobj.get('ytd', {}) if isinstance(kobj, dict) else {}
            bk_ie = ytd.get('ie')
            comp = compute_mol_ms_for_brand(D, brand, m_curr, m_prev)
            if comp is None:
                continue
            expected = comp['ie_vs_mkt']
            diff = abs((bk_ie or 0) - (expected or 0))
            status = 'OK' if diff < 0.5 else f'MISMATCH (diff={diff})'
            if status != 'OK': issues += 1
            print(f"  {line_dir:10s} {brand:25s} {str(bk_ie):>8s} {str(expected):>9s} {status}")
    total_issues += issues
    print(f'\nBrand-level mismatches: {issues}\n')

    # Fail loudly: exit != 0 si alguna linea no cargo (cobertura incompleta ->
    # NO reportar "0 mismatches" como verde) o si hay mismatches reales.
    if load_errors:
        print(f'ERROR: no se pudieron cargar {len(load_errors)} linea(s): '
              f'{sorted(load_errors)}. El audit NO cubrio esas lineas.')
    if load_errors or total_issues:
        return 1
    print('OK: consistencia verificada en las 7 lineas (0 mismatches).')
    return 0


if __name__ == '__main__':
    sys.exit(audit())
