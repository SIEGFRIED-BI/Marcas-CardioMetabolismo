"""Recomputa brandKpis[brand].ytd.ie y brandKpis[brand].mat.ie usando la
fórmula vs-market (base 100):

  ie = (brand_units_curr / brand_units_prev) / (market_curr / market_prev) * 100

Antes: ie = (units_curr / units_prev) * 100  (crecimiento brand puro)
       -> 78 para ACEMUK que esta cayendo de 535k a 421k (= -21%, IE 79)

Ahora: ie vs-market. Si el mercado tambien cae al mismo ritmo, IE = 100
       (la marca crece igual que el mercado). Si la marca cae menos que el
       mercado, IE > 100 (le esta ganando al mercado).

Aplica a las 7 lineas. Idempotente."""
from __future__ import annotations
import re, json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
FILES = [
    ('cardio/data.js', False),
    ('ATB/data.js', False),
    ('OTC/data.js', False),
    ('respiratorio/data.js', False),
    ('mujer/data.js', False),
    ('SNC/data.js', False),
    ('dermatologia/data.js', False),
]


def find_obj(text, is_inline):
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        return text.index('{', m.start() + 8)
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    return text.index('{', m.end())


def build_brand_to_mol(D):
    """Map brand_name -> mol_perf key (molecule market the brand belongs to)."""
    out = {}
    for m_key, obj in (D.get('mol_perf') or {}).items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = p.get('prod', '')
            if not name: continue
            # Brand = prod without (SIE) suffix
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
            # Some brandKpis keys use the base, some use exact prod
            for k in (name, base, base.upper()):
                if k and k not in out:
                    out[k] = m_key
    return out


def compute_market_units(mol_obj, month_keys):
    """Sum units across all products in the molecule for the given months."""
    if not isinstance(mol_obj, dict): return 0
    total = 0
    for p in mol_obj.get('products', []):
        mv = p.get('monthly_vals', {})
        for mk in month_keys:
            v = mv.get(mk, 0)
            if v: total += v
    return total


def get_ytd_months(D, year):
    """YTD months of given year present in mol_perf."""
    mol = D.get('mol_perf', {})
    months = set()
    for o in mol.values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            for mk in (p.get('monthly_vals') or {}).keys():
                if mk.endswith(f' {year}'):
                    months.add(mk)
    return sorted(months, key=lambda k: ('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split().index(k.split()[0])))


def get_mat_months(D, end_year, end_month):
    """Last 12 months ending at end_year-end_month."""
    MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    out = []
    y, m = end_year, end_month
    for _ in range(12):
        out.append(f'{MES[m-1]} {y}')
        m -= 1
        if m == 0: m = 12; y -= 1
    return list(reversed(out))


def patch_line(path_rel, is_inline):
    file_p = REPO / path_rel
    if not file_p.is_file():
        return f'MISS'
    text = file_p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    ob = find_obj(text, is_inline)
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    prefix = text[:ob]; suffix = text[ob+end:]

    bk = D.get('brandKpis', {})
    mol = D.get('mol_perf', {})
    if not bk or not mol:
        return f'no brandKpis or mol_perf'

    brand_to_mol = build_brand_to_mol(D)

    # Detect end of data (latest YTD year). Use any product's monthly_vals.
    all_months = set()
    for o in mol.values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            all_months.update((p.get('monthly_vals') or {}).keys())
    MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
    def msort(k):
        parts = k.split()
        return int(parts[1])*100 + MES.index(parts[0])+1
    sorted_months = sorted(all_months, key=msort)
    if not sorted_months:
        return 'no months'
    last = sorted_months[-1]
    last_m_name, last_y = last.split()
    last_y = int(last_y)
    last_m = MES.index(last_m_name) + 1
    ytd_curr_months = [k for k in sorted_months if k.endswith(f' {last_y}') and MES.index(k.split()[0])+1 <= last_m]
    ytd_prev_months = [f'{MES[MES.index(k.split()[0])]} {last_y-1}' for k in ytd_curr_months]
    mat_curr_months = get_mat_months(D, last_y, last_m)
    mat_prev_months = get_mat_months(D, last_y-1, last_m)

    changed = 0
    for brand, kobj in bk.items():
        if not isinstance(kobj, dict): continue
        mol_key = brand_to_mol.get(brand) or brand_to_mol.get(brand.upper())
        if not mol_key:
            # Fallback: search the brand name in any mol_perf
            for k, o in mol.items():
                if not isinstance(o, dict): continue
                for prod in o.get('products', []):
                    if prod.get('is_sie') and brand.upper() in str(prod.get('prod','')).upper():
                        mol_key = k; break
                if mol_key: break
        if not mol_key:
            continue
        mol_obj = mol.get(mol_key)
        # YTD
        ytd = kobj.get('ytd', {})
        if isinstance(ytd, dict) and ytd.get('units') and ytd.get('units_prev'):
            mkt_curr = compute_market_units(mol_obj, ytd_curr_months)
            mkt_prev = compute_market_units(mol_obj, ytd_prev_months)
            if mkt_prev > 0 and ytd['units_prev'] > 0:
                brand_ratio = ytd['units'] / ytd['units_prev']
                mkt_ratio = mkt_curr / mkt_prev
                if mkt_ratio > 0:
                    new_ie = round(brand_ratio / mkt_ratio * 100, 1)
                    if ytd.get('ie') != new_ie:
                        ytd['ie'] = new_ie
                        changed += 1
        # MAT
        mat = kobj.get('mat', {})
        if isinstance(mat, dict) and mat.get('units') and mat.get('units_prev'):
            mkt_curr = compute_market_units(mol_obj, mat_curr_months)
            mkt_prev = compute_market_units(mol_obj, mat_prev_months)
            if mkt_prev > 0 and mat['units_prev'] > 0:
                brand_ratio = mat['units'] / mat['units_prev']
                mkt_ratio = mkt_curr / mkt_prev
                if mkt_ratio > 0:
                    new_ie = round(brand_ratio / mkt_ratio * 100, 1)
                    if mat.get('ie') != new_ie:
                        mat['ie'] = new_ie
                        changed += 1

    file_p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                      encoding='utf-8', newline='')
    return f'{changed} IEs recomputados'


def main():
    for path_rel, is_inline in FILES:
        print(f'  {path_rel}: {patch_line(path_rel, is_inline)}')


if __name__ == '__main__':
    main()
