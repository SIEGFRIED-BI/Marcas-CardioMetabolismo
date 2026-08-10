#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Los agregados POR PRODUCTO de mol_perf tienen que sumar el total de su familia.

    sum(products[*].mat[k]) == family.mat[k]     para toda key k
    sum(products[*].ytd[k]) == family.ytd[k]

POR QUE EXISTE ESTE CHEQUEO
---------------------------
Detectado 2026-08-06: 78 productos de mujer/SNC/derma (171.397 u) tenian mat={} y ytd={}
porque recompute-mol-perf-aggregates.py exigia que los 12 meses de la ventana estuvieran
presentes en el propio producto. Para un LANZAMIENTO NUEVO los meses previos no son dato
faltante, son CEROS, asi que el MAT era genuino y se estaba descartando.

Nada de eso rompia una suma de familia, y por eso ningun gate lo veia:
  - la tabla multi-periodo suma monthly_vals, no lee mat -> mostraba bien
  - check-molperf-suma-productos.py valida las ventanas sumando monthly -> pasaba
  - audit-full valida la familia contra si misma -> pasaba
Lo que si lo leia era el GRAFICO anual, que renormaliza sobre p.mat. En SNC/BREXPIPRAZOLE,
con 4 de 5 productos en mat={}, REXULTI salia 100% cuando su MS% real era 84,13%, y los
cuatro competidores -- incluida la marca propia BREXIL -- no se dibujaban. El usuario lo
reporto como "no veo los competidores".

O sea: un defecto que solo se ve en UNA superficie y no mueve ninguna suma. Este chequeo lo
convierte en una igualdad que falla ruidosa.

Salida: una linea PASS/FAIL por linea con las dos cifras, y exit != 0 si hay FAIL.
Uso: py shared/check-molperf-agregados-por-producto.py [--verbose]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent.parent
LINES = ['cardio', 'ATB', 'OTC', 'respiratorio', 'mujer', 'SNC', 'dermatologia']


MES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']


def ventana_mat(key):
    """'Jun 2022' -> los 12 meses Jul 2021..Jun 2022."""
    p = str(key).split()
    if len(p) != 2 or p[0] not in MES:
        return []
    try: y = int(p[1])
    except ValueError: return []
    fin = y * 12 + MES.index(p[0])
    out = []
    for back in range(11, -1, -1):
        yy, mm = divmod(fin - back, 12)
        out.append('{} {}'.format(MES[mm], yy))
    return out


def parse(path):
    t = path.read_text(encoding='utf-8', errors='replace')
    i = t.index('window.OTC_DASHBOARD')
    m = re.compile(r'=\s*').search(t, i)
    return json.JSONDecoder().raw_decode(t[t.index('{', m.end()):])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()

    fails, n_chk, n_vacios = [], 0, []
    print('[molperf-agregados] sum(products.<campo>) == family.<campo>, key por key')
    for ln in LINES:
        p = REPO / ln / 'data.js'
        if not p.is_file():
            continue
        D = parse(p)
        mp = D.get('mol_perf') or {}
        n = mal = 0
        for fam, f in mp.items():
            prods = [x for x in (f.get('products') or []) if isinstance(x, dict)]
            # cobertura de la familia: si la familia tiene la key, cada producto con
            # datos mensuales en esa ventana tiene que aportar su parte
            for campo in ('mat', 'ytd'):
                for k, v in (f.get(campo) or {}).items():
                    s = sum((x.get(campo) or {}).get(k, 0) for x in prods)
                    n += 1; n_chk += 1
                    if round(s) != round(v or 0):
                        mal += 1
                        if len(fails) < 25:
                            fails.append('{}/{} {}[{}]: productos {:,} vs familia {:,} ({:+,})'
                                         .format(ln, fam, campo, k, round(s), round(v or 0),
                                                 round(s) - round(v or 0)))
            # Sintoma original: un producto con ventas DENTRO de una ventana MAT que la
            # familia si publica, pero sin su propia key para esa ventana.
            # No alcanza con "tiene ventas y mat esta vacio": hay productos cuyas ventas
            # caen enteras ANTES del primer MAT completo de la linea (mujer/CLIMATIX/
            # TIBOFEM vendio 1 u en Jun 2021, derma/CICLOPIROX/LOPROX 2 u en Jun 2021, y
            # el primer MAT es Jul 2021-Jun 2022). Ahi no hay MAT que calcular y la
            # familia tampoco los cuenta -- marcarlos seria un falso positivo, y un gate
            # que grita en falso se termina ignorando.
            for k in (f.get('mat') or {}):
                win = ventana_mat(k)
                if not win:
                    continue
                for x in prods:
                    if str(x.get('prod', '')).lower() == 'otros':
                        continue
                    mv = x.get('monthly_vals') or {}
                    dentro = any(mv.get(mk) for mk in win)
                    n_chk += 1
                    if dentro and k not in (x.get('mat') or {}):
                        n_vacios.append('{}/{}/{} [{}]'.format(ln, fam, x.get('prod'), k))
        print('  {:<14} {:>6,} comparaciones  {}'.format(ln, n, 'PASS' if not mal else 'FAIL {}'.format(mal)))

    if n_vacios:
        fails.append('{} producto(s) con ventas DENTRO de una ventana MAT que la familia '
                     'publica, pero sin su propia key (el grafico anual los pone en 0): {}'
                     .format(len(n_vacios), ', '.join(n_vacios[:6])))
    print('  total: {:,} comparaciones, {} FAIL'.format(n_chk, len(fails)))
    for x in fails[:25]:
        print('    ', x)
    if fails:
        print('  Correr: py shared/recompute-mol-perf-aggregates.py')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
