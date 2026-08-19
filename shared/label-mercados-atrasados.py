#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rotula en molLabels los mercados que van ATRASADOS respecto del cierre de su linea.

Casi todos los mercados salen del master AR_PM y avanzan juntos, pero algunos los define
un export CURADO por Marketing que puede llegar mas tarde. En el cierre de Jul-2026 el
archivo de MAGNUS ('Mercado-MAGNUS-sildenafil-tadalafil.xlsx') llegaba solo hasta
May-2026: MAGNUS y MAGNUS 36 quedaron congelados en Jun-2026 (el ultimo mes publicado)
mientras el resto de OTC pasaba a Jul-2026.

Un mercado un mes atras no esta mal, pero si no se dice, el lector compara MS% de
periodos distintos sin saberlo. Este script lo dice EN EL TABLERO: el selector de mercado
pasa a mostrar 'MAGNUS (mercado al Jun-2026)'.

Es derivado del dato y auto-corrige: cuando la fuente se pone al dia y la familia alcanza
el cierre, el sufijo se borra solo. Idempotente.

Uso:  python shared/label-mercados-atrasados.py [--check]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = ['cardio/data.js', 'ATB/data.js', 'OTC/data.js', 'respiratorio/data.js',
         'mujer/data.js', 'SNC/data.js', 'dermatologia/data.js']
EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
      'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

SUFIJO = re.compile(r'\s*\(mercado al [A-Za-z]{3}-\d{4}\)\s*$')


def msort(k):
    p = k.split()
    return int(p[1]) * 12 + EN.index(p[0])


def fmt(k):
    p = k.split()
    return f'{ES[EN.index(p[0])]}-{p[1]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    total_rot, total_limp = 0, 0
    for rel in FILES:
        p = REPO / rel
        if not p.is_file():
            continue
        t = p.read_text(encoding='utf-8-sig', errors='replace')
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
        if not m:
            continue
        ob = t.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(t[ob:])
        mp = D.get('mol_perf') or {}
        ml = D.get('molLabels')
        if not mp or not isinstance(ml, dict):
            continue

        ult = {}
        for fam, o in mp.items():
            if not isinstance(o, dict):
                continue
            ms = set()
            for pr in o.get('products', []):
                ms.update((pr.get('monthly_vals') or {}).keys())
            ms = [x for x in ms if len(x.split()) == 2 and x.split()[0] in EN]
            if ms:
                ult[fam] = max(ms, key=msort)
        if not ult:
            continue
        cierre = max(ult.values(), key=msort)

        cambios = []
        for fam, last in sorted(ult.items()):
            if fam not in ml:
                continue
            base = SUFIJO.sub('', str(ml[fam])).strip()
            if msort(last) < msort(cierre):
                nuevo = f'{base} (mercado al {fmt(last)})'
            else:
                nuevo = base
            if ml[fam] != nuevo:
                cambios.append((fam, ml[fam], nuevo))
                if not args.check:
                    ml[fam] = nuevo

        for fam, viejo, nuevo in cambios:
            if '(mercado al' in nuevo:
                total_rot += 1
                print(f'  {rel:24s} {fam:18s} -> "{nuevo}"  (cierre de la linea: {fmt(cierre)})')
            else:
                total_limp += 1
                print(f'  {rel:24s} {fam:18s} al dia, saco el sufijo')

        if cambios and not args.check:
            p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                         encoding='utf-8', newline='')

    print(f'\nlabel-mercados-atrasados: {total_rot} rotulado(s), {total_limp} limpiado(s)')
    if args.check and (total_rot or total_limp):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
