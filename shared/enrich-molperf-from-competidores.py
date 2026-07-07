"""Enriquece D.mol_perf[<market>].products con TODAS las brands de competidores-data.js.

Formato CORRECTO de keys (alineado con meta.ytd_keys / mat_keys):
  - monthly_vals: 'Mar 2024', 'Apr 2024', ...
  - quarterly_vals: 'Q1 2024', 'Q2 2024', ...
  - ytd / mat: 'Mar 2024', 'Mar 2025', 'Mar 2026'  (END month del cumulative)
  - ms_*: mismas keys que el numerador
"""
from __future__ import annotations
import re, json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('cardio',       'cardio/data.js',                'cardio/DDD/competidores-data.js'),
    ('ATB',          'ATB/data.js',                   'ATB/DDD/competidores-data.js'),
    ('OTC',          'OTC/data.js',                   'OTC/DDD/competidores-data.js'),
    ('respiratorio', 'respiratorio/data.js',          'respiratorio/DDD/competidores-data.js'),
]
MES_EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
MES_ES_TO_EN = {'Ene':'Jan','Feb':'Feb','Mar':'Mar','Abr':'Apr','May':'May','Jun':'Jun',
                'Jul':'Jul','Ago':'Aug','Sep':'Sep','Oct':'Oct','Nov':'Nov','Dic':'Dec'}


def parse_es_month(mk_es):
    parts = mk_es.split('-')
    if len(parts) != 2: return None
    en = MES_ES_TO_EN.get(parts[0])
    if not en: return None
    return f'{en} {parts[1]}'


def load_competidores(path):
    s = path.read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n')
    return json.loads(s)


def load_D(path_rel):
    p = REPO / path_rel
    text = p.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return text[:ob], D, text[ob+end:], p


def save_D(prefix, D, suffix, p):
    p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                 encoding='utf-8', newline='')


def match_market(comp_mkt_name, mol_keys):
    target = comp_mkt_name.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
    for k in mol_keys:
        norm = k.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
        if norm == target: return k
    for k in mol_keys:
        norm = k.upper().replace('-', ' ').replace(' ', '').replace('.', '').strip()
        if target.startswith(norm) or norm.startswith(target): return k
    return None


def aggregate_brand_monthly(brand_monthly_obj, months_es):
    out = {}
    for region, arr in brand_monthly_obj.items():
        if not isinstance(arr, list): continue
        for i, val in enumerate(arr):
            if i >= len(months_es): break
            mk_en = parse_es_month(months_es[i])
            if not mk_en: continue
            out[mk_en] = out.get(mk_en, 0) + (val or 0)
    return out


def compute_aggregates_proper(monthly, ytd_keys, mat_keys):
    """Use ytd_keys (e.g. ['Mar 2024','Mar 2025','Mar 2026']) to compute YTD per year.
    For each ytd_key 'MES YEAR':
      ytd[key] = sum(monthly[m YEAR] for m in Jan..MES)
    For each mat_key:
      mat[key] = sum(monthly[<last 12 months ending at key>])"""
    ytd = {}
    mat = {}
    quarterly = {}

    for yk in ytd_keys:
        try:
            mes_name, year = yk.split()
            year = int(year)
            end_m = MES_EN.index(mes_name) + 1
        except: continue
        total = sum((monthly.get(f'{MES_EN[i]} {year}') or 0) for i in range(end_m))
        ytd[yk] = total

    for yk in mat_keys:
        try:
            mes_name, year = yk.split()
            year = int(year)
            end_m = MES_EN.index(mes_name) + 1
        except: continue
        total = 0
        y, m = year, end_m
        for _ in range(12):
            total += monthly.get(f'{MES_EN[m-1]} {y}') or 0
            m -= 1
            if m == 0: m = 12; y -= 1
        mat[yk] = total

    # Quarterly: sum 3 months per quarter, all years available
    years = set()
    for mk in monthly:
        try: years.add(int(mk.split()[1]))
        except: pass
    for yr in years:
        for q in range(1, 5):
            mses = [(q-1)*3, (q-1)*3+1, (q-1)*3+2]
            tot = sum((monthly.get(f'{MES_EN[i]} {yr}') or 0) for i in mses)
            if tot > 0:
                quarterly[f'Q{q} {yr}'] = tot

    return ytd, mat, quarterly


def enrich_line(line_key, data_rel, comp_rel):
    data_p = REPO / data_rel
    comp_p = REPO / comp_rel
    if not data_p.is_file() or not comp_p.is_file():
        return 'no file'
    prefix, D, suffix, file_p = load_D(data_rel)
    comp = load_competidores(comp_p)
    months_es = comp['months']
    meta = D.get('meta', {})
    ytd_keys = meta.get('ytd_keys') or []
    mat_keys = meta.get('mat_keys') or []
    mol = D.get('mol_perf', {})
    mol_keys = list(mol.keys())

    stats = {'matched': 0, 'skipped': 0, 'added': 0, 'updated': 0}

    for comp_mkt_name, mkt_obj in comp['markets'].items():
        mol_key = match_market(comp_mkt_name, mol_keys)
        if not mol_key:
            stats['skipped'] += 1; continue
        stats['matched'] += 1

        mol_obj = mol[mol_key]
        # RESTO sintetico (build-data) y enrich (competidores reales) son MUTUAMENTE
        # EXCLUYENTES: ambos des-truncan el mercado. Si coexisten, el total se cuenta
        # doble (resto + competidores). Al enriquecer con marcas reales descartamos el
        # 'Otros (resto del mercado)'; el recompute posterior deja sum(products)=mercado.
        if any(p.get('is_resto') for p in mol_obj.get('products', [])):
            mol_obj['products'] = [p for p in mol_obj['products'] if not p.get('is_resto')]
        existing_prods = mol_obj.get('products', [])
        existing_bases = {}
        for p in existing_prods:
            name = p.get('prod', '')
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip().upper()
            existing_bases[base] = p

        for brand, brand_monthly_obj in mkt_obj.get('brand_monthly', {}).items():
            monthly = aggregate_brand_monthly(brand_monthly_obj, months_es)
            if not monthly: continue
            ytd, mat, q = compute_aggregates_proper(monthly, ytd_keys, mat_keys)
            brand_upper = brand.upper().strip()
            existing = existing_bases.get(brand_upper)
            if existing:
                # Merge monthly_vals: KEEP existing months, OVERRIDE solo si comp tiene valor
                merged_monthly = {**(existing.get('monthly_vals') or {}), **monthly}
                existing['monthly_vals'] = merged_monthly
                # Recompute aggregates from MERGED monthly
                e_ytd, e_mat, e_q = compute_aggregates_proper(merged_monthly, ytd_keys, mat_keys)
                existing['ytd'] = e_ytd
                existing['mat'] = e_mat
                existing['quarterly_vals'] = e_q
                stats['updated'] += 1
            else:
                new_p = {
                    'prod': brand,
                    'manuf': '',
                    'is_sie': False,
                    'monthly_vals': monthly,
                    'ytd': ytd,
                    'mat': mat,
                    'quarterly_vals': q,
                    'ms_monthly': {},
                    'ms_ytd': {},
                    'ms_mat': {},
                    'ms_quarterly': {},
                }
                mol_obj['products'].append(new_p)
                stats['added'] += 1

        # Recompute MS% per period for ALL products
        all_prods = mol_obj['products']
        for period_field, ms_field in [('monthly_vals','ms_monthly'),
                                         ('ytd','ms_ytd'),
                                         ('mat','ms_mat'),
                                         ('quarterly_vals','ms_quarterly')]:
            totals = defaultdict(int)
            for p in all_prods:
                for k, v in (p.get(period_field) or {}).items():
                    totals[k] += (v or 0)
            for p in all_prods:
                ms_dict = {}
                for k, v in (p.get(period_field) or {}).items():
                    tot = totals[k]
                    if tot > 0:
                        ms_dict[k] = round((v or 0)/tot*100, 2)
                p[ms_field] = ms_dict

    save_D(prefix, D, suffix, file_p)
    return f"matched={stats['matched']}, skip={stats['skipped']}, added={stats['added']}, updated={stats['updated']}"


def main():
    for key, data_rel, comp_rel in LINES:
        try:
            print(f'  {key}: {enrich_line(key, data_rel, comp_rel)}')
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f'  {key}: ERROR {e}')


if __name__ == '__main__':
    main()
