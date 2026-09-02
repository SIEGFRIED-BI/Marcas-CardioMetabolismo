#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restaura en MAGNUS / MAGNUS 36 los meses que el archivo curado de MKT no cubre.

POR QUE. El mercado de MAGNUS no sale del AR_PM: lo define un export curado por
Marketing ('Mercado-MAGNUS-sildenafil-tadalafil.xlsx' en hubRoot) que separa
sildenafil de tadalafil. `rebuild-otc-magnus-from-iqvia.py` lo aplica DESPUES del
split desde el master, asi que reescribe las dos familias enteras con lo que traiga
ese archivo. En el cierre de Jul-2026 el archivo estaba 2 meses atrasado (llega a
May-2026), y las dos familias quedaron SIN junio -- un mes ATRAS de lo publicado.

Ningun gate lo veia: verify-history-preserved compara el rango de la LINEA (OTC
seguia teniendo Jul-2026 por sus otras familias), y las sumas internas cerraban
perfecto sobre el dato truncado. Lo caza check-molperf-vs-master.py (MAGNUS
publicado=0 contra 80.078 del master).

QUE HACE. Copia los monthly_vals de los meses pedidos desde una referencia git
(por defecto HEAD, o sea lo que hoy esta publicado) a las familias MAGNUS y
MAGNUS 36 del working tree. No inventa ni escala nada: son exactamente los valores
que ya estan en produccion. NO agrega meses que la referencia no tenga.

Es aditivo y idempotente: solo escribe meses ausentes o distintos, y reporta cada
producto tocado.

Uso:
  python shared/restore-magnus-mes-publicado.py --mes "Jun 2026" [--ref HEAD] [--check]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gitcmd import GIT as _GIT  # noqa: E402  (git no esta en el PATH fuera del hook)
TARGET = 'OTC/data.js'
FAMILIAS = ('MAGNUS', 'MAGNUS 36')


def parse_data_js(text):
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    if not m:
        return None, None, None
    ob = text.index('{', m.end())
    obj, end = json.JSONDecoder().raw_decode(text[ob:])
    return obj, text[:ob], text[ob + end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mes', action='append', required=True,
                    help='month key a restaurar, ej "Jun 2026" (repetible)')
    ap.add_argument('--ref', default='HEAD', help='ref git de referencia (default HEAD)')
    ap.add_argument('--check', action='store_true', help='no escribe; exit 1 si falta algo')
    args = ap.parse_args()

    p = REPO / TARGET
    cur_txt = p.read_text(encoding='utf-8-sig', errors='replace')
    D, prefix, suffix = parse_data_js(cur_txt)
    if D is None:
        print(f'FATAL: no parseo {TARGET}', file=sys.stderr)
        return 2

    r = subprocess.run([_GIT, '--no-pager', 'show', f'{args.ref}:{TARGET}'],
                       cwd=REPO, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0 or not r.stdout.strip():
        print(f'FATAL: no puedo leer {args.ref}:{TARGET}', file=sys.stderr)
        return 2
    REFD, _, _ = parse_data_js(r.stdout)

    tocados, faltantes, sin_ref = 0, 0, []
    for fam in FAMILIAS:
        cur_fam = D.get('mol_perf', {}).get(fam)
        ref_fam = REFD.get('mol_perf', {}).get(fam)
        if not cur_fam or not ref_fam:
            print(f'  SKIP {fam}: no existe en working tree o en {args.ref}')
            continue
        ref_by_name = {str(x.get('prod')): x for x in ref_fam.get('products', [])}
        for prod in cur_fam.get('products', []):
            name = str(prod.get('prod'))
            ref = ref_by_name.get(name)
            if ref is None:
                sin_ref.append(f'{fam}/{name}')
                continue
            mv = prod.setdefault('monthly_vals', {})
            rmv = ref.get('monthly_vals', {})
            for mk in args.mes:
                if mk not in rmv:
                    continue
                if mv.get(mk) != rmv[mk]:
                    if args.check:
                        faltantes += 1
                    else:
                        mv[mk] = rmv[mk]
                        tocados += 1

    for fam in FAMILIAS:
        o = D.get('mol_perf', {}).get(fam)
        if not o:
            continue
        for mk in args.mes:
            tot = sum(float(x.get('monthly_vals', {}).get(mk, 0) or 0)
                      for x in o.get('products', []))
            sie = sum(float(x.get('monthly_vals', {}).get(mk, 0) or 0)
                      for x in o.get('products', []) if x.get('is_sie'))
            print(f'  {fam:11s} {mk}: mercado={tot:12,.0f}  SIE={sie:10,.0f}')

    if sin_ref:
        print(f'  productos sin contraparte en {args.ref}: {len(sin_ref)}')
        for s in sin_ref[:10]:
            print(f'     {s}')

    if args.check:
        print(f'\n--check: {faltantes} valores difieren de {args.ref}')
        return 1 if faltantes else 0

    if tocados:
        p.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                     encoding='utf-8', newline='')
        print(f'\n-> {TARGET} reescrito: {tocados} valores restaurados desde {args.ref}')
    else:
        print('\n(sin cambios)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
