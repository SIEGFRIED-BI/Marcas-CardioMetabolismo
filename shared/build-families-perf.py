"""Build kpis-families.json: family-level multi-period market/SIE data
for the new 'Por Marca' view in kpis.html.

Periods:
  mes        - latest_month curr_yr vs latest_month prev_yr
  ytd        - Ene..latest_month curr_yr vs same range prev_yr
  trimestre  - ultimos 3 meses vs mismos 3 meses prev_yr
  mat        - ultimos 12 meses vs prev 12 (= same window prev_yr)

For each family in each line's mol_perf:
  market_curr   = sum of all products' units in family for the window
  market_prev   = same for prev_yr window
  sie_curr      = sum of SIE products' units in family for the window
  sie_prev      = same for prev_yr window
  ms_curr       = sie_curr / market_curr * 100
  ms_prev       = sie_prev / market_prev * 100
  ie            = (sie_curr/sie_prev) / (market_curr/market_prev) * 100
                  (relative growth of SIE vs market)
  var_pp        = ms_curr - ms_prev

Output: kpis-families.json at repo root.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from datetime import date

REPO = Path(__file__).resolve().parent.parent

LINES = [
    ('cardio', 'Cardiometabolismo', 'cardio/data.js', False),
    ('antibio', 'Antibióticos',     'ATB/data.js', False),
    ('otx',    'OTX',               'OTC/data.js', False),
    ('resp',   'Respiratoria',      'respiratorio/data.js', False),
    ('mujer',  'Mujer',             'mujer/data.js', False),
    ('snc',    'SNC',               'SNC/data.js', False),
    ('derma',  'Dermatología',      'dermatologia/data.js', False),
]

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
NUM_TO_MES = {v:k for k,v in MES_INV.items()}
MES_SHORT = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
             7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}


def load_data(path: Path, is_inline: bool):
    enc = 'utf-8' if is_inline else 'utf-8-sig'
    t = path.read_text(encoding=enc, errors='replace')
    if is_inline:
        m = re.search(r'const D\s*=\s*\{', t)
        if not m: return None
        ob = m.end() - 1
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
        if not m: return None
        ob = t.index('{', m.end())
    D, _ = json.JSONDecoder().raw_decode(t[ob:])
    return D


def add_months(y, m, delta):
    idx = y * 12 + (m - 1) + delta
    return divmod(idx, 12)[0], divmod(idx, 12)[1] + 1


def month_range(end_y, end_m, n):
    """Returns list of n month_keys ending in (end_y, end_m)."""
    out = []
    y, m = end_y, end_m
    for _ in range(n):
        out.append(f'{NUM_TO_MES[m]} {y}')
        m -= 1
        if m == 0:
            m = 12; y -= 1
    return list(reversed(out))


def windows_for(end_y, end_m):
    """Define curr/prev windows for each period."""
    men_curr = [f'{NUM_TO_MES[end_m]} {end_y}']
    men_prev = [f'{NUM_TO_MES[end_m]} {end_y - 1}']
    tri_curr = month_range(end_y, end_m, 3)
    tri_prev = month_range(end_y - 1, end_m, 3)
    ytd_curr = [f'{NUM_TO_MES[m]} {end_y}' for m in range(1, end_m + 1)]
    ytd_prev = [f'{NUM_TO_MES[m]} {end_y - 1}' for m in range(1, end_m + 1)]
    mat_curr = month_range(end_y, end_m, 12)
    mat_prev = month_range(end_y - 1, end_m, 12)
    return {
        'mes':       (men_curr, men_prev),
        'ytd':       (ytd_curr, ytd_prev),
        'trimestre': (tri_curr, tri_prev),
        'mat':       (mat_curr, mat_prev),
    }


def sum_window(monthly_dict, window_keys):
    return sum(float(monthly_dict.get(mk, 0) or 0) for mk in window_keys)


def safe_div(a, b):
    if not b or b == 0: return None
    return a / b


def safe_round(x, n=2):
    if x is None: return None
    return round(x, n)


def detect_latest(mol_perf):
    """Find the latest (year, month) with data across all families' monthly_vals."""
    latest = None
    for fam, fd in (mol_perf or {}).items():
        if not isinstance(fd, dict): continue
        for p in (fd.get('products') or []):
            for mk in (p.get('monthly_vals') or {}):
                parts = mk.split()
                if len(parts) != 2 or parts[0] not in MES_INV: continue
                try:
                    y = int(parts[1]); m = MES_INV[parts[0]]
                    key = (y, m)
                    if latest is None or key > latest:
                        latest = key
                except (ValueError, IndexError):
                    pass
    return latest


def compute_family_period(fam_data, window_curr, window_prev):
    """Returns dict with market_curr, market_prev, sie_curr, sie_prev,
    ms_curr, ms_prev, ie, var_pp for a single family and period window."""
    products = fam_data.get('products') or []
    # Market = sum of ALL products' monthly_vals in the window
    market_curr = 0
    market_prev = 0
    sie_curr = 0
    sie_prev = 0
    for p in products:
        mv = p.get('monthly_vals') or {}
        pc = sum_window(mv, window_curr)
        pp = sum_window(mv, window_prev)
        market_curr += pc
        market_prev += pp
        if p.get('is_sie'):
            sie_curr += pc
            sie_prev += pp
    ms_curr = safe_round((sie_curr / market_curr * 100) if market_curr > 0 else None, 1)
    ms_prev = safe_round((sie_prev / market_prev * 100) if market_prev > 0 else None, 1)
    # IE relative = (sie growth) / (market growth) * 100
    sie_growth = safe_div(sie_curr, sie_prev)
    mkt_growth = safe_div(market_curr, market_prev)
    # Cap volatilidad (igual que fix-brandkpis-ie-vs-market.py y multi-period-table.computeBrand):
    # base insignificante (crecimiento propio >=5x) o mercado volatil/incompleto -> IE no comparable.
    if (sie_growth is not None and mkt_growth is not None
            and sie_growth < 5 and 0.2 < mkt_growth < 5):
        ie = round(sie_growth / mkt_growth * 100, 0)
    else:
        ie = None
    var_pp = None
    if ms_curr is not None and ms_prev is not None:
        var_pp = round(ms_curr - ms_prev, 2)
    return {
        'market_curr': int(round(market_curr)),
        'market_prev': int(round(market_prev)),
        'sie_curr':    int(round(sie_curr)),
        'sie_prev':    int(round(sie_prev)),
        'ms_curr':     ms_curr,
        'ms_prev':     ms_prev,
        'ie':          ie,
        'var_pp':      var_pp,
    }


def main():
    families = []
    latest_overall = None

    for line_key, line_name, path_rel, is_inline in LINES:
        path = REPO / path_rel
        if not path.is_file():
            print(f'  MISS: {path_rel}', file=sys.stderr); continue
        D = load_data(path, is_inline)
        if D is None:
            print(f'  no D in {path_rel}', file=sys.stderr); continue
        mol_perf = D.get('mol_perf') or {}
        latest = detect_latest(mol_perf)
        if latest is None:
            print(f'  no latest month in {line_key}', file=sys.stderr); continue
        if latest_overall is None or latest > latest_overall:
            latest_overall = latest

        end_y, end_m = latest
        windows = windows_for(end_y, end_m)

        for fam_name, fam_data in mol_perf.items():
            if not isinstance(fam_data, dict): continue
            products = fam_data.get('products') or []
            # Only include families with at least 1 SIE product
            sie_products = [p for p in products if p.get('is_sie')]
            if not sie_products: continue
            # Pick a "display name": the most representative SIE brand
            sie_names = [p.get('prod', '') for p in sie_products]
            display_name = fam_name  # default to family name
            periods_data = {}
            for pkey, (wcurr, wprev) in windows.items():
                periods_data[pkey] = compute_family_period(fam_data, wcurr, wprev)
            families.append({
                'family':     fam_name,
                'display':    display_name,
                'line':       line_key,
                'lineName':   line_name,
                'sie_brands': sie_names,
                'periods':    periods_data,
            })

    # Sort by current units descending (MAT period)
    families.sort(key=lambda f: -(f['periods']['mat']['market_curr'] or 0))

    end_y, end_m = latest_overall
    mes_short = MES_SHORT[end_m]
    period_labels = {
        'mes':       f"{mes_short} {end_y} vs {mes_short} {end_y-1}",
        'ytd':       f"YTD Ene-{mes_short} {end_y} vs {end_y-1}",
        'trimestre': f"Trim. {MES_SHORT[(end_m-2-1)%12+1]}-{mes_short} {end_y} vs {end_y-1}",
        'mat':       f"MAT {mes_short} {end_y} vs {mes_short} {end_y-1}",
    }

    out = {
        'generated_at': date.today().isoformat(),
        'as_of_month':  f'{NUM_TO_MES[end_m]} {end_y}',
        'as_of_short':  f'{mes_short} {end_y}',
        'period_labels': period_labels,
        'families':     families,
    }
    out_path = REPO / 'kpis-families.json'
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8', newline='')
    print(f'OK: {out_path} ({len(families)} families, as_of={mes_short} {end_y})')


if __name__ == '__main__':
    main()
