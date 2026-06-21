# -*- coding: utf-8 -*-
"""Recompone brandKpis[marca].{ytd,mat}.market_total y .ms desde el agregado
AUTORITATIVO de mol_perf[fam].ytd/.mat[ultimo_mes] (lo produce
recompute-mol-perf-aggregates.py), en vez de lo que dejó build-data.ps1.

Arregla (prioridad C de la auditoría):
  - cardio DIOVAN D  : market_total ~26% alto (incluía un mercado más amplio) -> ms 6.0->7.6
  - ATB CEFALEXINA   : market_total ~3% alto (ARG y ARG DUO) -> ms 58.4->60.2
  - OTC FLEXINA .mat : market_total y units eran del MES (no MAT) -> ms 19.3->12.3

market_total = mol_perf[fam][per][ultimo_mes].  units se conserva (build-data lo
calcula bien por producto), SALVO la anomalía MAT<YTD (imposible para acumulado):
ahí se recomputa units/units_prev/growth desde el producto SIE de la marca,
anclando en el YTD (que sí es correcto). ms = units/market_total.

No toca .ie (eso lo hace fix-brandkpis-ie-vs-market.py). Idempotente, modo --check.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
FILES = ['cardio/data.js','ATB/data.js','OTC/data.js','respiratorio/data.js',
         'mujer/data.js','SNC/data.js','dermatologia/data.js']


def msort(k):
    p = k.split(); return int(p[1]) * 100 + MES.index(p[0])


def load_D(path):
    t = (REPO / path).read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    return t[:ob], D, t[ob + end:], REPO / path


def last_agg(mol, per):
    d = mol.get(per, {})
    if not isinstance(d, dict) or not d:
        return None
    return d[max(d, key=msort)]


def all_months(mol):
    s = set()
    for p in mol.get('products', []):
        s.update((p.get('monthly_vals') or {}).keys())
    return sorted(s, key=msort)


def windows(mol):
    am = all_months(mol)
    if not am:
        return None
    last = am[-1]; yr = last.split()[1]
    ytd_c = [m for m in am if m.split()[1] == yr and msort(m) <= msort(last)]
    ytd_p = [f'{m.split()[0]} {int(yr)-1}' for m in ytd_c]
    i = am.index(last)
    mat_c = am[max(0, i-11):i+1]
    # mat prev = 12 meses anteriores a mat_c
    j = max(0, i-11)
    mat_p = am[max(0, j-12):j]
    return {'ytd': (ytd_c, ytd_p), 'mat': (mat_c, mat_p)}


def psum(prod, months):
    mv = prod.get('monthly_vals', {})
    return sum(mv.get(m, 0) or 0 for m in months)


def find_brand_product(mol, ytd_curr, target_units):
    """Producto SIE cuya suma YTD == units almacenado (la marca)."""
    if not target_units:
        return None
    for p in mol.get('products', []):
        if p.get('is_sie') and abs(psum(p, ytd_curr) - target_units) <= max(2, 0.01 * target_units):
            return p
    return None


def patch_line(path, check_only=False):
    prefix, D, suffix, fp = load_D(path)
    bk = D.get('brandKpis', {}); mp = D.get('mol_perf', {})
    if not bk or not mp:
        return 0, 'sin brandKpis/mol_perf'
    changed = 0
    for fam, kp in bk.items():
        mol = mp.get(fam)
        if not isinstance(mol, dict):
            continue
        win = windows(mol)
        if not win:
            continue
        for per in ('ytd', 'mat'):
            st = kp.get(per)
            if not isinstance(st, dict):
                continue
            curr_months, prev_months = win[per]
            # 1) market_total autoritativo
            mkt = last_agg(mol, per)
            if mkt is None:
                continue
            new_mkt = int(round(mkt))
            # 2) units: conservar, salvo anomalía MAT<YTD (units del mes, no MAT)
            new_units = st.get('units')
            new_uprev = st.get('units_prev')
            new_growth = st.get('growth')
            if per == 'mat':
                yu = kp.get('ytd', {}).get('units')
                if st.get('units') is not None and yu is not None and st['units'] < yu:
                    prod = find_brand_product(mol, win['ytd'][0], yu)
                    if prod is not None:
                        new_units = int(round(psum(prod, curr_months)))
                        up = psum(prod, prev_months)
                        new_uprev = int(round(up)) if up else new_uprev
                        if new_uprev:
                            new_growth = round((new_units / new_uprev - 1) * 100, 1)
            # 3) ms
            new_ms = round(new_units / new_mkt * 100, 1) if (new_units and new_mkt) else st.get('ms')
            for key, val in (('market_total', new_mkt), ('units', new_units),
                             ('units_prev', new_uprev), ('growth', new_growth), ('ms', new_ms)):
                if val is not None and st.get(key) != val:
                    if not check_only:
                        st[key] = val
                    changed += 1
    if changed and not check_only:
        fp.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                      encoding='utf-8', newline='')
    return changed, f'{changed} campo(s) ' + ('a corregir' if check_only else 'corregidos')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_only = '--check' in sys.argv
    total = 0
    for f in FILES:
        try:
            n, msg = patch_line(f, check_only)
            total += n
            print(f'  {f}: {msg}')
        except Exception as e:
            print(f'  {f}: ERROR {e}')
            return 1
    if check_only and total > 0:
        print(f'BRANDKPIS-MARKET FAIL: {total} campos market_total/ms desalineados '
              f'(correr: py shared/fix-brandkpis-market-total.py)')
        return 1
    print('OK: brandKpis market_total/ms alineados con mol_perf.' if check_only else 'Listo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
