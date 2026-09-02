#!/usr/bin/env python3
"""Gate: las marcas SIEGFRIED tienen que seguir estando en mol_perf.

Por que existe (2026-08-18): el export de IQVIA reordeno sus columnas
(AR_PM 317 cols: Manufacturer/Product/Pack -> 329 cols: Pack/Manufacturer/
ATC IV/Ph.Forms III/Product) y los build-data.ps1 leian producto y laboratorio
por POSICION. Resultado: 'prod' quedo con el laboratorio ("GADOR") y 'manuf'
con la presentacion ("SINLIP CAPS 20mg x 30"); is_sie cayo a false en los 384
productos y NINGUNA de las 49 marcas SIE quedo en mol_perf de cardio/ATB/OTC/
respiratorio. Ninguna suma se movio, asi que audit-full daba 16.626/16.634 y
verify-history-preserved daba OK: es un cambio de ETIQUETA, no de aritmetica.

Tres chequeos, ninguno basado en sumas:
  A. cada linea que declara sieProds tiene >=1 producto con is_sie=true
  B. el set de marcas SIE presentes en mol_perf no se achica vs el baseline git
  C. los valores de 'manuf' no parecen presentaciones (firma del swap)

Uso:  python shared/check-molperf-sie-presente.py [--baseline HEAD]
Exit != 0 si hay algun FAIL o SKIP.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gitcmd import GIT as _GIT  # noqa: E402  (git no esta en el PATH fuera del hook)

LINES = [
    ('cardio', 'cardio/data.js'), ('antibio', 'ATB/data.js'),
    ('mujer', 'mujer/data.js'), ('snc', 'SNC/data.js'),
    ('resp', 'respiratorio/data.js'), ('otx', 'OTC/data.js'),
    ('derma', 'dermatologia/data.js'),
]

# Marcadores de presentacion/pack. Si aparecen en 'manuf' es que esa columna
# trae el Pack y no el laboratorio.
PACK_RE = re.compile(
    r"(\bx\s*\d+\b|\d+\s*(MG|ML|G|MCG|UI)\b|\bTABL?\b|\bCAPS?\b|\bCOMP\b|"
    r"\bJBE\b|\bSUSP\b|\bAMP\b|\bCREMA?\b|\bGOTAS\b|\bSOL\b|\bINY\b)", re.I)

results = []  # (status, nombre, detalle)


def add(status, nombre, detalle):
    results.append((status, nombre, detalle))
    print(f'{status:4s} {nombre:38s} {detalle}')


def parse_data_js(text):
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    if not m:
        return None
    ob = text.index('{', m.end())
    return json.JSONDecoder().raw_decode(text[ob:])[0]


def load_now(rel):
    p = REPO / rel
    if not p.is_file():
        return None
    return parse_data_js(p.read_text(encoding='utf-8-sig', errors='replace'))


def load_baseline(rel, baseline):
    r = subprocess.run([_GIT, '--no-pager', 'show', f'{baseline}:{rel}'],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return parse_data_js(r.stdout)


def base_name(prod):
    """'ROXOLAN (SIE)' -> 'ROXOLAN'."""
    return re.sub(r'\s*\(.*?\)\s*$', '', str(prod or '')).strip().upper()


def sie_brands_in_molperf(D):
    """Marcas declaradas en sieProds que efectivamente aparecen en mol_perf."""
    declared = {str(s).strip().upper() for s in D.get('sieProds', []) if s}
    seen = set()
    for obj in D.get('mol_perf', {}).values():
        if not isinstance(obj, dict):
            continue
        for p in obj.get('products', []):
            n = base_name(p.get('prod'))
            if n in declared:
                seen.add(n)
    return seen


def molperf_products(D):
    for obj in D.get('mol_perf', {}).values():
        if isinstance(obj, dict):
            for p in obj.get('products', []):
                yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default='HEAD',
                    help='ref git contra la que comparar el set SIE (default HEAD)')
    args = ap.parse_args()

    for key, rel in LINES:
        D = load_now(rel)
        if D is None:
            add('SKIP', f'{key}: cargar {rel}', 'no existe o no parsea')
            continue

        declared = {str(s).strip().upper() for s in D.get('sieProds', []) if s}
        prods = list(molperf_products(D))
        n_sie = sum(1 for p in prods if p.get('is_sie'))

        # --- A. hay al menos un is_sie ------------------------------------
        if not declared:
            add('SKIP', f'{key}: A is_sie presente', 'la linea no declara sieProds')
        elif not prods:
            add('SKIP', f'{key}: A is_sie presente', 'mol_perf vacio')
        elif n_sie == 0:
            add('FAIL', f'{key}: A is_sie presente',
                f'0 de {len(prods)} productos con is_sie=true '
                f'({len(declared)} marcas SIE declaradas) -> ratio 0,00')
        else:
            add('PASS', f'{key}: A is_sie presente',
                f'{n_sie} de {len(prods)} productos con is_sie=true '
                f'(ratio {n_sie / len(prods):.3f})')

        # --- B. el set SIE no se achica vs baseline -----------------------
        now_set = sie_brands_in_molperf(D)
        B = load_baseline(rel, args.baseline)
        if B is None:
            add('SKIP', f'{key}: B set SIE vs {args.baseline}',
                'no hay baseline legible')
        else:
            old_set = sie_brands_in_molperf(B)
            perdidas = sorted(old_set - now_set)
            if perdidas:
                muestra = ', '.join(perdidas[:8]) + (' ...' if len(perdidas) > 8 else '')
                add('FAIL', f'{key}: B set SIE vs {args.baseline}',
                    f'{len(now_set)} ahora vs {len(old_set)} en baseline; '
                    f'faltan {len(perdidas)}: {muestra}')
            else:
                add('PASS', f'{key}: B set SIE vs {args.baseline}',
                    f'{len(now_set)} ahora vs {len(old_set)} en baseline; 0 perdidas')

        # --- C. 'manuf' no parece una presentacion ------------------------
        manufs = [str(p.get('manuf') or '') for p in prods]
        manufs = [m for m in manufs if m.strip()]
        if not manufs:
            add('SKIP', f'{key}: C manuf no es pack', 'sin valores de manuf')
        else:
            packish = sum(1 for m in manufs if PACK_RE.search(m))
            frac = packish / len(manufs)
            if frac > 0.20:
                add('FAIL', f'{key}: C manuf no es pack',
                    f'{packish} de {len(manufs)} manuf parecen presentacion '
                    f'(ratio {frac:.3f} > 0,200) -> columnas corridas?')
            else:
                add('PASS', f'{key}: C manuf no es pack',
                    f'{packish} de {len(manufs)} manuf parecen presentacion '
                    f'(ratio {frac:.3f})')

    n_fail = sum(1 for s, _, _ in results if s == 'FAIL')
    n_skip = sum(1 for s, _, _ in results if s == 'SKIP')
    n_pass = sum(1 for s, _, _ in results if s == 'PASS')
    print('\n' + '=' * 70)
    print(f'check-molperf-sie-presente: {n_pass} PASS  {n_fail} FAIL  {n_skip} SKIP')
    print('=' * 70)
    if n_fail or n_skip:
        print('\nDETALLE:')
        for s, n, d in results:
            if s != 'PASS':
                print(f'  {s} {n}: {d}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
