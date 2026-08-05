#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shared/check-molperf-suma-productos.py

GATE: por cada familia de mol_perf, la suma de los productos tiene que dar el total
de la familia, EXACTO, en los 4 campos (monthly / quarterly / ytd / mat).

POR QUE ES CRITICO (y por que no lo cubria ningun otro gate)
------------------------------------------------------------
shared/recompute-mol-perf-aggregates.py REDEFINE el total del mercado como la suma de
los productos:
    # Family-level monthly = sum of products monthly_vals
    fam_monthly[mk] += ...            (lineas ~142-158)
y de ese campo sale el mercado del tablero Total (shared/build-total.py) y los KPIs.
O sea: si la suma de productos NO cierra con el total de la familia, el total publicado
se mueve solo en la proxima corrida del recompute, y arrastra el tablero Total, el MS%
de compania y los KPIs. Es un error silencioso y diferido.

Lo mas cerca que habia era audit-full.py:392-415, que compara la suma de monthly_vals
de TODAS las familias de la linea contra kpiStrip con tolerancia max(10, 0,5%): es un
agregado de linea contra otra fuente, asi que un residuo mal calculado en una familia
(o una fila 'Otros' borrada con residuo != 0) pasaba sin ser detectado mientras la
desviacion quedara debajo del 0,5% del mercado de la linea entera.

La fila 'Otros (resto del mercado)' es parte de la suma: es el residuo del cap de 8
productos del build. Puede quedar levemente NEGATIVA por el redondeo por-producto del
build (la suma de valores redondeados se pasa del total redondeado por unas unidades);
eso se tolera hasta NEG_TOL del total del periodo y se reporta, pero la SUMA tiene que
cerrar exacta igual.

QUE SE COMPARA Y POR QUE NO SE SUMAN LOS AGREGADOS DE LOS PRODUCTOS
-------------------------------------------------------------------
Los agregados quarterly/ytd/mat de un producto se emiten SOLO si la ventana completa
existe (ver recompute-mol-perf-aggregates.py: aggregate_quarterly/ytd/mat exigen la
ventana entera). Entonces un producto que arranco despues del inicio de la serie no
tiene agregado para las keys viejas, mientras la familia si lo tiene. Sumar los campos
de agregado de los productos da de menos por diseño: en mujer/SNC/dermatologia eso son
343 diferencias legitimas, no un error.

Por eso los agregados se validan sumando los monthly_vals de los productos SOBRE LA
VENTANA del periodo, que es la invariante real y cierra en las 7 lineas. Y aparte se
verifica, producto por producto, que su agregado coincida con la suma de sus propios
meses cuando la ventana esta completa.

Uso:  py shared/check-molperf-suma-productos.py [--verbose]
Exit: 0 todo cierra | 1 hay diferencias
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = {
    'cardio': 'cardio/data.js',
    'ATB': 'ATB/data.js',
    'OTC': 'OTC/data.js',
    'respiratorio': 'respiratorio/data.js',
    'mujer': 'mujer/data.js',
    'SNC': 'SNC/data.js',
    'dermatologia': 'dermatologia/data.js',
}
CAMPOS = (('monthly_vals', 'monthly'), ('quarterly_vals', 'quarterly'),
          ('ytd', 'ytd'), ('mat', 'mat'))
RESTO = 'Otros (resto del mercado)'
MES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MI = {m: i + 1 for i, m in enumerate(MES)}


def ventana(kind, key):
    """Meses que abarca una key de quarterly ('Q2 2026') / ytd / mat ('Jun 2026')."""
    p = str(key).split()
    if len(p) != 2 or not p[1].isdigit():
        return None
    y = int(p[1])
    if kind == 'quarterly':
        if not (p[0].startswith('Q') and p[0][1:].isdigit()):
            return None
        q = int(p[0][1:])
        return ['{} {}'.format(MES[m - 1], y) for m in range((q - 1) * 3 + 1, q * 3 + 1)]
    if p[0] not in MI:
        return None
    cm = MI[p[0]]
    if kind == 'ytd':
        return ['{} {}'.format(MES[m - 1], y) for m in range(1, cm + 1)]
    out = []
    for b in range(11, -1, -1):
        idx = (y * 12 + (cm - 1)) - b
        yy, mm = divmod(idx, 12)
        out.append('{} {}'.format(MES[mm], yy))
    return out
# Cuanto puede quedar negativa la fila 'Otros' por redondeo, como fraccion del total
# del periodo. Medido en las 4 lineas con el universo completo itemizado: maximo
# 5 unidades sobre mercados de 15k-2,2M. 0,5% es una cota holgada que igual atrapa
# un residuo mal calculado (un universo mal inferido da 36-59%).
NEG_TOL = 0.005


def load(path):
    t = (REPO / path).read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m:
        return None
    return json.JSONDecoder().raw_decode(t[t.index('{', m.end()):])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    errs, negs, checks, fams = [], [], 0, 0
    for linea, rel in LINES.items():
        if not (REPO / rel).is_file():
            continue
        D = load(rel)
        if not D:
            continue
        mp = D.get('mol_perf') or {}
        for fam, fo in mp.items():
            prods = fo.get('products') or []
            if not prods:
                continue
            fams += 1
            # (A) monthly: la suma de los productos == el monthly de la familia, exacto.
            #     Es el campo del que recompute-mol-perf-aggregates.py deriva el total.
            acc_m = defaultdict(int)
            for p in prods:
                for k, v in (p.get('monthly_vals') or {}).items():
                    acc_m[k] += int(v or 0)
            for k, v in (fo.get('monthly') or {}).items():
                checks += 1
                if acc_m.get(k, 0) != int(v or 0):
                    errs.append('{} / {} / monthly[{}]: suma de productos = {:,} != familia = {:,} '
                                '(dif {:+,})'.format(linea, fam, k, acc_m.get(k, 0), int(v or 0),
                                                     acc_m.get(k, 0) - int(v or 0)))
            # (B) agregados: se suman los monthly de los productos SOBRE LA VENTANA del
            #     periodo (no los campos de agregado, que se emiten solo con ventana
            #     completa y darian de menos por diseño).
            for kind in ('quarterly', 'ytd', 'mat'):
                for k, v in (fo.get(kind) or {}).items():
                    w = ventana(kind, k)
                    if not w or not all(x in acc_m for x in w):
                        continue
                    checks += 1
                    real = sum(acc_m[x] for x in w)
                    if real != int(v or 0):
                        errs.append('{} / {} / {}[{}]: suma de productos en la ventana = {:,} != '
                                    'familia = {:,} (dif {:+,})'.format(linea, fam, kind, k, real,
                                                                        int(v or 0), real - int(v or 0)))
            # (C) cada producto: su agregado == la suma de sus propios meses, cuando la
            #     ventana esta completa en su monthly_vals.
            for p in prods:
                mv = {k: int(x or 0) for k, x in (p.get('monthly_vals') or {}).items()}
                for kind, campo in (('quarterly', 'quarterly_vals'), ('ytd', 'ytd'), ('mat', 'mat')):
                    for k, v in (p.get(campo) or {}).items():
                        w = ventana(kind, k)
                        if not w or not all(x in mv for x in w):
                            continue
                        checks += 1
                        if sum(mv[x] for x in w) != int(v or 0):
                            errs.append('{} / {} / {}: {}[{}] = {:,} != suma de sus meses {:,}'.format(
                                linea, fam, str(p.get('prod'))[:26], campo, k, int(v or 0),
                                sum(mv[x] for x in w)))
            # la fila 'Otros' puede quedar levemente negativa por redondeo
            resto = next((p for p in prods if str(p.get('prod')) == RESTO or p.get('is_resto')), None)
            if resto:
                for campo, famcampo in CAMPOS:
                    base = fo.get(famcampo) or {}
                    for k, v in (resto.get(campo) or {}).items():
                        val = int(v or 0)
                        if val >= 0:
                            continue
                        tot = int(base.get(k) or 0)
                        checks += 1
                        if tot > 0 and abs(val) / tot > NEG_TOL:
                            errs.append('{} / {} / Otros.{}[{}] = {:,} es {:.2f}% del total {:,} '
                                        '-> excede la cota de redondeo ({:.1f}%)'.format(
                                            linea, fam, campo, k, val, abs(val) / tot * 100,
                                            tot, NEG_TOL * 100))
                        else:
                            negs.append('{} / {} / Otros.{}[{}] = {}'.format(linea, fam, campo, k, val))

    print('[molperf-suma] {:,} comparaciones sobre {} familias'.format(checks, fams))
    if negs:
        print('  {} valores negativos en la fila Otros, todos dentro de la cota de '
              'redondeo ({:.1f}% del total):'.format(len(negs), NEG_TOL * 100))
        for x in (negs if a.verbose else negs[:6]):
            print('     {}'.format(x))
        if not a.verbose and len(negs) > 6:
            print('     ... y {} mas (--verbose para verlos)'.format(len(negs) - 6))
    if errs:
        print('  FAIL: {} diferencias'.format(len(errs)))
        for x in errs[:25]:
            print('     {}'.format(x))
        if len(errs) > 25:
            print('     ... y {} mas'.format(len(errs) - 25))
        return 1
    print('  OK: la suma de products cierra con el total de la familia en los 4 campos.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
