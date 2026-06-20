"""Recomputa quarterly_vals, ytd, mat, ms_* en mol_perf de las 7 lineas
desde el monthly_vals actual. Asegura consistencia interna despues de
cualquier merge o edicion manual de monthly_vals.

Uso: py shared/recompute-mol-perf-aggregates.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
NUM_TO_MES = {v:k for k,v in MES_INV.items()}


def msort(mk):
    p = mk.split()
    if len(p) != 2: return 0
    try: return int(p[1]) * 100 + MES_INV.get(p[0], 0)
    except (ValueError, IndexError): return 0


def quarter_key(mk):
    parts = mk.split()
    if len(parts) != 2: return ''
    m = MES_INV.get(parts[0])
    if not m: return ''
    q = (m - 1) // 3 + 1
    return f'Q{q} {parts[1]}'


def detect_cierre_month(monthly):
    """The cierre month is the most recent month in the data."""
    keys = sorted(monthly.keys(), key=msort)
    if not keys: return None
    last = keys[-1].split()
    return MES_INV.get(last[0])


def aggregate_quarterly(monthly):
    out = defaultdict(int)
    for mk, v in monthly.items():
        qk = quarter_key(mk)
        if qk:
            try: out[qk] += int(round(float(v or 0)))
            except (TypeError, ValueError): pass
    return dict(out)


def aggregate_ytd(monthly, cierre_month):
    """YTD per year ending in cierre_month."""
    if not monthly: return {}
    cierre_lbl = NUM_TO_MES.get(cierre_month, 'Dec')
    by_year = defaultdict(int)
    for mk, v in monthly.items():
        parts = mk.split()
        if len(parts) != 2: continue
        m_num = MES_INV.get(parts[0])
        if not m_num: continue
        if m_num <= cierre_month:
            try: by_year[parts[1]] += int(round(float(v or 0)))
            except (TypeError, ValueError): pass
    return {f'{cierre_lbl} {y}': v for y, v in by_year.items()}


def aggregate_mat(monthly, cierre_month):
    """MAT per year = rolling 12 months ending in cierre_month."""
    if not monthly: return {}
    cierre_lbl = NUM_TO_MES.get(cierre_month, 'Dec')
    years_with = set()
    for mk in monthly:
        parts = mk.split()
        if len(parts) == 2 and parts[0] in MES_INV:
            try: years_with.add(int(parts[1]))
            except ValueError: pass
    out = {}
    for y in sorted(years_with):
        total = 0
        for back in range(11, -1, -1):
            total_idx = (y * 12 + (cierre_month - 1)) - back
            yy, mm = divmod(total_idx, 12)
            mk = f'{NUM_TO_MES[mm + 1]} {yy}'
            v = monthly.get(mk)
            if v is not None:
                try: total += int(round(float(v or 0)))
                except (TypeError, ValueError): pass
        out[f'{cierre_lbl} {y}'] = total
    return out


def safe_share(num, den, round_to=2):
    if not den or den == 0: return 0
    return round((num or 0) / den * 100, round_to)


def recompute_family(fam_obj, cierre_month):
    """Recompute fam_obj.products[*].quarterly_vals/ytd/mat/ms_* and
    fam_obj.monthly/quarterly/ytd/mat from current monthly_vals."""
    if not isinstance(fam_obj, dict): return 0
    prods = fam_obj.get('products', [])
    if not prods: return 0

    # Family-level monthly = sum of products monthly_vals
    fam_monthly = defaultdict(int)
    for p in prods:
        if not isinstance(p, dict): continue
        mv = p.get('monthly_vals') or {}
        for mk, v in mv.items():
            if v is not None:
                try: fam_monthly[mk] += int(round(float(v or 0)))
                except (TypeError, ValueError): pass
    fam_monthly = dict(fam_monthly)
    fam_quarterly = aggregate_quarterly(fam_monthly)
    fam_ytd = aggregate_ytd(fam_monthly, cierre_month)
    fam_mat = aggregate_mat(fam_monthly, cierre_month)

    # Set family aggregates if they exist as keys
    if 'monthly' in fam_obj and isinstance(fam_obj['monthly'], dict):
        fam_obj['monthly'] = fam_monthly
    if 'quarterly' in fam_obj and isinstance(fam_obj['quarterly'], dict):
        fam_obj['quarterly'] = fam_quarterly
    if 'ytd' in fam_obj and isinstance(fam_obj['ytd'], dict):
        fam_obj['ytd'] = fam_ytd
    if 'mat' in fam_obj and isinstance(fam_obj['mat'], dict):
        fam_obj['mat'] = fam_mat

    # Per-product aggregates + ms_*
    n_updated = 0
    for p in prods:
        if not isinstance(p, dict): continue
        mv = p.get('monthly_vals') or {}
        if not mv: continue
        p_quarterly = aggregate_quarterly(mv)
        p_ytd = aggregate_ytd(mv, cierre_month)
        p_mat = aggregate_mat(mv, cierre_month)
        p['quarterly_vals'] = p_quarterly
        p['ytd'] = p_ytd
        p['mat'] = p_mat
        # ms_*: product / family
        p['ms_monthly']   = {mk: safe_share(mv.get(mk,0),       fam_monthly.get(mk,0))   for mk in fam_monthly}
        p['ms_quarterly'] = {qk: safe_share(p_quarterly.get(qk,0), fam_quarterly.get(qk,0)) for qk in fam_quarterly}
        p['ms_ytd']       = {yk: safe_share(p_ytd.get(yk,0),    fam_ytd.get(yk,0))    for yk in fam_ytd}
        p['ms_mat']       = {mk: safe_share(p_mat.get(mk,0),    fam_mat.get(mk,0))    for mk in fam_mat}
        n_updated += 1
    return n_updated


LINES = [
    ('cardio',  'cardio/data.js',                     'window.OTC_DASHBOARD'),
    ('ATB',     'ATB/data.js',                        'window.OTC_DASHBOARD'),
    ('OTC',     'OTC/data.js',                        'window.OTC_DASHBOARD'),
    ('respi',   'respiratorio/data.js',               'window.OTC_DASHBOARD'),
    ('mujer',   'mujer/index.html',                   'const D'),
    ('SNC',     'SNC/data.js',                     'window.OTC_DASHBOARD'),
    ('derma',   'dermatologia/data.js','window.OTC_DASHBOARD'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--cierre', help="Mes de cierre FIJO 'YYYY-MM' o num 1-12. Si se omite, se "
                    "autodetecta del ultimo mes presente (comportamiento historico). Pinearlo "
                    "evita que un mes parcial colado achique MAT/YTD.")
    args = ap.parse_args()
    cierre_override = None
    if args.cierre:
        cierre_override = int(args.cierre.split('-')[1]) if '-' in args.cierre else int(args.cierre)

    for line, path, var in LINES:
        p = REPO / path
        is_inline = var == 'const D'
        enc = 'utf-8' if is_inline else 'utf-8-sig'
        t = p.read_text(encoding=enc, errors='replace')
        if is_inline:
            m = re.search(r'const D\s*=\s*\{', t)
            if not m: print(f'{line}: no const D'); continue
            ob = m.end() - 1
        else:
            m = re.search(re.escape(var) + r'\s*=\s*', t)
            if not m: print(f'{line}: no {var}'); continue
            ob = t.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(t[ob:])
        mol = D.get('mol_perf', {})

        # Detect cierre month from the last monthly entry across all products
        all_months = set()
        for v in mol.values():
            if not isinstance(v, dict): continue
            for pp in v.get('products', []):
                if isinstance(pp, dict):
                    all_months.update((pp.get('monthly_vals') or {}).keys())
        cierre = cierre_override or detect_cierre_month({m: 0 for m in all_months}) or 12

        total_updated = 0
        for fam_key, fam_obj in mol.items():
            n = recompute_family(fam_obj, cierre_month=cierre)
            total_updated += n

        # Regenerar meta.ytd_keys / mat_keys (el eje anual que consume el chart de
        # Mercado IQVIA) desde los agregados recomputados. Bug que arregla: el sync
        # movia la data a un mes nuevo (p.ej. Abr->May) pero estas listas quedaban
        # viejas -> el chart buscaba ms_ytd/ms_mat con keys inexistentes ("Sin datos
        # para este filtro" en MAT/YTD). Asi el eje SIEMPRE matchea la data.
        meta = D.get('meta')
        meta_changed = ''
        if isinstance(meta, dict):
            yk, mk = set(), set()
            for fam_obj in mol.values():
                if isinstance(fam_obj, dict):
                    yk |= set((fam_obj.get('ytd') or {}).keys())
                    mk |= set((fam_obj.get('mat') or {}).keys())
            if yk and 'ytd_keys' in meta:
                meta['ytd_keys'] = sorted(yk, key=msort)
            if mk and 'mat_keys' in meta:
                meta['mat_keys'] = sorted(mk, key=msort)
            if yk or mk:
                meta_changed = f" | ytd_keys={len(meta.get('ytd_keys',[]))} mat_keys={len(meta.get('mat_keys',[]))}"

        print(f'{line:8s}: cierre_month={cierre}, products updated={total_updated}{meta_changed}')

        if not args.dry_run:
            new_t = t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:]
            p.write_text(new_t, encoding=enc.replace('-sig',''), newline='')


if __name__ == '__main__':
    main()
