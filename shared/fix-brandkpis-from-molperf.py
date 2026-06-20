"""Recomputa brandKpis[brand].ytd.ie y .mat.ie usando mol_perf como FUENTE
ÚNICA (consistente con la 'Tabla comparativa' del Mercado IQVIA).

Para cada brand SIE:
  brand_curr = sum( products[brand].monthly_vals[YTD months curr year] )
  brand_prev = sum( products[brand].monthly_vals[YTD months prev year] )
  mkt_curr   = sum( all products in same mol_perf market, curr year )
  mkt_prev   = sum( all products in same mol_perf market, prev year )
  ie = (brand_curr/brand_prev) / (mkt_curr/mkt_prev) * 100

Si brand_prev==0 o mkt_prev==0 -> ie = None (sin comparable).
Si la marca tiene >300% growth (caso brand nueva) -> ie = None.

Tambien actualiza units, units_prev, ms para alinear con la base de datos."""
from __future__ import annotations
import re, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    ('cardio/data.js', False),
    ('ATB/data.js', False),
    ('OTC/data.js', False),
    ('respiratorio/data.js', False),
    ('dermatologia/data.js', False),
]
MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def find_obj(text, is_inline):
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        return text.index('{', m.start() + 8)
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    return text.index('{', m.end())


def latest_in_molperf(D):
    mol = D.get('mol_perf', {})
    all_m = set()
    for o in mol.values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            all_m.update((p.get('monthly_vals') or {}).keys())
    def msort(k):
        ps = k.split()
        return int(ps[1])*100 + MES.index(ps[0])+1
    sm = sorted(all_m, key=msort)
    return sm[-1] if sm else None


def ytd_months(year, end_m):
    return [f'{MES[i]} {year}' for i in range(end_m)]


def mat_months(end_y, end_m):
    """Last 12 months ending at end_y/end_m, ASC."""
    out = []
    y, m = end_y, end_m
    for _ in range(12):
        out.append(f'{MES[m-1]} {y}')
        m -= 1
        if m == 0: m = 12; y -= 1
    return list(reversed(out))


def sum_window(monthly, window):
    return sum(monthly.get(mk, 0) or 0 for mk in window)


def find_primary_mol(D, brand_key):
    """Find the mol_perf market where brand is a SIE leader (primary)."""
    mol = D.get('mol_perf', {})
    brand_u = brand_key.upper()
    candidates = []
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = str(p.get('prod', '')).upper()
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
            # Exact match: brand_key == base (without SIE)
            if base == brand_u:
                # Check if this is the "primary" molecule for the brand
                # (brand_key matches the molecule key or is the strongest)
                priority = 0
                if brand_u == m_key.upper(): priority = 2
                elif brand_u in m_key.upper(): priority = 1
                candidates.append((priority, m_key, obj, p))
    if not candidates: return None, None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1], candidates[0][2]


def find_brand_products(mol_obj, brand_key):
    """Get all SIE products in this molecule matching the brand."""
    out = []
    brand_u = brand_key.upper()
    for p in mol_obj.get('products', []):
        if not p.get('is_sie'): continue
        name = str(p.get('prod', '')).upper()
        base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        if base == brand_u:
            out.append(p)
    return out


def patch_line(path_rel, is_inline):
    file_p = REPO / path_rel
    if not file_p.is_file(): return 'MISS'
    text = file_p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    ob = find_obj(text, is_inline)
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    prefix = text[:ob]; suffix = text[ob+end:]

    bk = D.get('brandKpis', {})
    mol = D.get('mol_perf', {})
    if not bk or not mol: return 'no bk or mol_perf'

    latest = latest_in_molperf(D)
    if not latest: return 'no months'
    last_m_name, last_y = latest.split()
    last_y = int(last_y); last_m = MES.index(last_m_name) + 1

    win_ytd_c = ytd_months(last_y, last_m)
    win_ytd_p = ytd_months(last_y-1, last_m)
    win_mat_c = mat_months(last_y, last_m)
    win_mat_p = mat_months(last_y-1, last_m)

    changed = 0
    new_null = 0
    for brand, kobj in bk.items():
        if not isinstance(kobj, dict): continue
        mol_key, mol_obj = find_primary_mol(D, brand)
        if not mol_obj: continue

        # Brand units in primary molecule (sum SIE presentations matching brand)
        brand_prods = find_brand_products(mol_obj, brand)
        if not brand_prods: continue

        def sum_brand(window):
            return sum(sum_window(p.get('monthly_vals', {}), window) for p in brand_prods)

        def sum_market(window):
            return sum(sum_window(p.get('monthly_vals', {}), window)
                       for p in mol_obj.get('products', []))

        for period, win_c, win_p in [('ytd', win_ytd_c, win_ytd_p),
                                       ('mat', win_mat_c, win_mat_p)]:
            target = kobj.get(period, {})
            if not isinstance(target, dict): continue
            b_c = sum_brand(win_c)
            b_p = sum_brand(win_p)
            m_c = sum_market(win_c)
            m_p = sum_market(win_p)

            # Update units (consistente con mol_perf)
            old_units = target.get('units')
            if old_units != b_c:
                target['units'] = b_c
                changed += 1
            old_units_prev = target.get('units_prev')
            if old_units_prev != b_p:
                target['units_prev'] = b_p
                changed += 1

            # Update ms (consistente)
            new_ms = round(b_c/m_c*100, 1) if m_c > 0 else None
            if target.get('ms') != new_ms:
                target['ms'] = new_ms
                changed += 1

            # Update market_total
            if target.get('market_total') != m_c:
                target['market_total'] = m_c
                changed += 1

            # IE vs-market: only if both prev sums are non-zero AND reasonable
            new_ie = None
            if b_p > 0 and m_p > 0 and m_c > 0:
                brand_ratio = b_c / b_p
                mkt_ratio = m_c / m_p
                if mkt_ratio > 0 and brand_ratio < 5:  # cap unrealistic growth
                    new_ie = round(brand_ratio / mkt_ratio * 100, 1)
            if target.get('ie') != new_ie:
                if new_ie is None: new_null += 1
                target['ie'] = new_ie
                changed += 1

            # growth = (b_c/b_p - 1)*100
            new_growth = round((b_c/b_p - 1)*100, 1) if b_p > 0 else None
            if target.get('growth') != new_growth:
                target['growth'] = new_growth
                changed += 1

    file_p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                      encoding='utf-8', newline='')
    return f'{changed} updates, {new_null} IEs nullified (sin prev data)'


def main():
    for path_rel, is_inline in FILES:
        print(f'  {path_rel}: {patch_line(path_rel, is_inline)}')


if __name__ == '__main__':
    main()
