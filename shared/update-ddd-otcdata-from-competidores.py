"""Actualiza OTC_DATA.ddd en data.js de ATB/OTC/respiratorio desde
competidores-data.js. Construye regionsByMonth y productsByMonth.

Shape destino:
  OTC_DATA.ddd.months = [<24 months es>]
  OTC_DATA.ddd.markets[mk] = {
    family: <mk>,
    latestMonth: <last>,
    monthly: {},  # se preserva si existe
    regionsByMonth: {[m]: [{name, total, sie, share}]},
    productsByMonth: {[m]: [{product, units, share, isSie}]}
  }
"""
from __future__ import annotations
import re, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('ATB',          'ATB/data.js',          'ATB/DDD/competidores-data.js'),
    ('OTC',          'OTC/data.js',          'OTC/DDD/competidores-data.js'),
    ('respiratorio', 'respiratorio/data.js', 'respiratorio/DDD/competidores-data.js'),
]


def load_comp(rel):
    s = (REPO / rel).read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n')
    return json.loads(s)


def build_ddd_from_comp(comp_data):
    """Transform Shape A competidores -> OTC_DATA.ddd structure."""
    months = comp_data.get('months', [])
    regions = comp_data.get('regions', [])
    new_markets = {}

    for mk_name, mk_obj in comp_data.get('markets', {}).items():
        bm = mk_obj.get('brand_monthly', {})
        tm = mk_obj.get('total_monthly', {})
        sie_set = set(s.upper() for s in mk_obj.get('brands', []))

        regions_by_month = {}
        products_by_month = {}

        for mi, mk in enumerate(months):
            # regionsByMonth: por region, total y sie
            rrows = []
            for reg in regions:
                if reg == '-' or reg.startswith('_'): continue
                tot_arr = tm.get(reg, [])
                total = (tot_arr[mi] if mi < len(tot_arr) else 0) or 0
                sie = 0
                for brand, regs in bm.items():
                    if brand.upper() not in sie_set: continue
                    arr = regs.get(reg, [])
                    sie += (arr[mi] if mi < len(arr) else 0) or 0
                if total > 0:
                    share = round(sie/total*100, 1)
                    rrows.append({'name': reg, 'total': total, 'sie': sie, 'share': share})
            rrows.sort(key=lambda x: -x['total'])
            regions_by_month[mk] = rrows

            # productsByMonth: por brand, units nacional (suma regiones)
            prows = []
            total_market_month = 0
            brand_units = {}
            for brand, regs in bm.items():
                u = 0
                for arr in regs.values():
                    u += (arr[mi] if mi < len(arr) else 0) or 0
                brand_units[brand] = u
                total_market_month += u
            for brand, u in brand_units.items():
                if u <= 0: continue
                share = round(u/total_market_month*100, 1) if total_market_month > 0 else 0
                prows.append({
                    'product': brand,
                    'units': u,
                    'share': share,
                    'isSie': brand.upper() in sie_set,
                })
            prows.sort(key=lambda x: -x['units'])
            products_by_month[mk] = prows

        new_markets[mk_name] = {
            'family': mk_name,
            'latestMonth': months[-1] if months else '',
            'monthly': {},
            'regionsByMonth': regions_by_month,
            'productsByMonth': products_by_month,
        }

    # familyToMarkets: el render (app.js) arma ORDERED_MARKETS = familyToMarkets.Totales
    # .filter(m => markets[m]). Si las keys de markets cambiaron (nombres molecula) y
    # Totales quedo con los nombres viejos, el filtro da VACIO -> pagina en blanco.
    # Por eso se REGENERA aca, consistente con las keys nuevas de markets.
    fam2mk = {'Totales': list(new_markets.keys())}
    for mk_name, mk_obj in comp_data.get('markets', {}).items():
        for b in mk_obj.get('brands', []):
            bu = str(b).upper()
            fam2mk.setdefault(bu, [])
            if mk_name not in fam2mk[bu]:
                fam2mk[bu].append(mk_name)

    return {'months': months, 'markets': new_markets, 'familyToMarkets': fam2mk}


def patch_line(line_key, data_rel, comp_rel):
    comp = load_comp(comp_rel)
    new_ddd = build_ddd_from_comp(comp)

    p = REPO / data_rel
    t = p.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DATA\s*=\s*', t)
    if not m: return 'no OTC_DATA'
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    prefix = t[:ob]; suffix = t[ob+end:]

    fam2mk = new_ddd.pop('familyToMarkets')
    D['ddd'] = new_ddd
    D['familyToMarkets'] = fam2mk   # regenerado para que matchee las keys nuevas de markets

    n_markets = len(new_ddd['markets'])
    n_months = len(new_ddd['months'])
    ordered = [m for m in fam2mk['Totales'] if m in new_ddd['markets']]
    p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                 encoding='utf-8', newline='')
    return f'OK [months={n_months}, markets={n_markets}, familyToMarkets.Totales={len(fam2mk["Totales"])}, ORDERED={len(ordered)}]'


def main():
    for line, data_rel, comp_rel in LINES:
        try:
            print(f'  {line}: {patch_line(line, data_rel, comp_rel)}')
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f'  {line}: ERROR {e}')


if __name__ == '__main__':
    main()
