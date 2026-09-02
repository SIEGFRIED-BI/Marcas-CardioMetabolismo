#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G3-forma: diffea la ESTRUCTURA de cada data.js contra el baseline git.

Todos los gates existentes comparan SUMAS. Una degradacion que no mueve ninguna
suma los pasa a todos. En el cierre de Jul-2026 pasaron tres a la vez:

  - se borro la clave de primer nivel `mercadosAteneo` en las 4 lineas
    (el literal $dashboardData de build-data.ps1 conoce 27 claves y reescribe
    data.js entero; el paso que la regenera llamaba a un script supersedido)
  - mol_perf paso de 364 a 182 productos en cardio (itemize-molperf-otros.py
    fallo sin frenar el pipeline) -> ranking truncado otra vez
  - desaparecieron las 49 marcas SIE (master con columnas reordenadas)

Ninguna de las tres rompe una suma. Este gate mira FORMA:
  D. no se perdio ninguna clave de primer nivel vs baseline
  E. la cantidad de productos de mol_perf no se derrumba (> --drop)
  F. la cantidad de familias de mol_perf no baja

Uso:  python shared/check-forma-vs-baseline.py [--baseline HEAD] [--drop 0.15]
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

results = []


def add(status, nombre, detalle):
    results.append((status, nombre, detalle))
    print(f'{status:4s} {nombre:34s} {detalle}')


def parse_data_js(text):
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    if not m:
        return None
    ob = text.index('{', m.end())
    return json.JSONDecoder().raw_decode(text[ob:])[0]


def shape(D):
    mol = D.get('mol_perf', {})
    nprod = 0
    months = set()
    for o in mol.values():
        if isinstance(o, dict):
            for p in o.get('products', []):
                nprod += 1
                months.update(p.get('monthly_vals', {}).keys())
    # Mercado por familia (suma de monthly_vals de TODOS sus productos, incluida la
    # fila de residuo 'Otros'). Sirve para separar dos cosas que el conteo de
    # productos mezcla: perder NOMBRES de competidores vs perder MERCADO.
    mkt = {}
    for fam, o in mol.items():
        if isinstance(o, dict):
            s = 0.0
            for p in o.get('products', []):
                for v in (p.get('monthly_vals') or {}).values():
                    s += float(v or 0)
            mkt[fam] = s
    return {'keys': set(D.keys()), 'fams': len(mol), 'prods': nprod,
            'months': len(months), 'mkt': mkt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default='HEAD')
    ap.add_argument('--drop', type=float, default=0.15,
                    help='caida relativa de productos tolerada (default 15%%)')
    args = ap.parse_args()

    for key, rel in LINES:
        p = REPO / rel
        if not p.is_file():
            add('SKIP', f'{key}: cargar', f'no existe {rel}')
            continue
        N = parse_data_js(p.read_text(encoding='utf-8-sig', errors='replace'))
        r = subprocess.run([_GIT, '--no-pager', 'show', f'{args.baseline}:{rel}'],
                           cwd=REPO, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        if r.returncode != 0 or not r.stdout.strip():
            add('SKIP', f'{key}: baseline', f'no hay {args.baseline}:{rel}')
            continue
        B = parse_data_js(r.stdout)
        if N is None or B is None:
            add('SKIP', f'{key}: parsear', 'data.js no parsea')
            continue
        sn, sb = shape(N), shape(B)

        # --- D. claves de primer nivel -----------------------------------
        perdidas = sorted(sb['keys'] - sn['keys'])
        nuevas = sorted(sn['keys'] - sb['keys'])
        if perdidas:
            add('FAIL', f'{key}: D claves top-level',
                f'{len(sn["keys"])} ahora vs {len(sb["keys"])} en baseline; '
                f'PERDIDAS: {", ".join(perdidas)}')
        else:
            extra = f'; nuevas: {", ".join(nuevas)}' if nuevas else ''
            add('PASS', f'{key}: D claves top-level',
                f'{len(sn["keys"])} ahora vs {len(sb["keys"])} en baseline; '
                f'0 perdidas{extra}')

        # --- E. productos de mol_perf ------------------------------------
        if sb['prods'] == 0:
            add('SKIP', f'{key}: E productos mol_perf', 'baseline sin productos')
        else:
            ratio = sn['prods'] / sb['prods']
            if ratio < (1 - args.drop):
                # Bajar el conteo de productos NO es lo mismo que perder mercado. El
                # itemizador (itemize-molperf-otros.py) expande la fila 'Otros' en
                # competidores con nombre, pero RECHAZA la expansion si sobre-contaria
                # el bucket; en ese caso las unidades siguen ahi, agrupadas en 'Otros',
                # y el total del mercado no se mueve. Caso real (2026-09-02):
                # ATB/MACROMAX paso de 30 a 9 productos con nombre porque expandir la
                # molecula AZITHROMYCIN sobre-contaba el bucket un 3%, y su MAT quedo
                # en -0,13%. Perder NOMBRES no mueve ningun MS%; perder MERCADO si.
                afectadas, mkt_ok = [], True
                for fam, m_b in (sb.get('mkt') or {}).items():
                    m_n = (sn.get('mkt') or {}).get(fam)
                    if m_n is None:
                        afectadas.append(fam + ': FAMILIA PERDIDA'); mkt_ok = False
                    elif m_b > 0 and abs(m_n / m_b - 1) > 0.02:
                        afectadas.append('{}: mercado {:,.0f} -> {:,.0f} ({:+.1%})'
                                         .format(fam, m_b, m_n, m_n / m_b - 1))
                        mkt_ok = False
                det = ('{} ahora vs {} en baseline (ratio {:.3f} < {:.3f})'
                       .format(sn['prods'], sb['prods'], ratio, 1 - args.drop))
                if mkt_ok:
                    add('WARN', key + ': E productos mol_perf',
                        det + ' -- pero el MERCADO de cada familia se preserva (<=2%): '
                        'es menos desglose por nombre, no menos dato')
                else:
                    add('FAIL', key + ': E productos mol_perf',
                        det + ' Y el mercado se movio en: ' + '; '.join(afectadas[:4]))
            else:
                add('PASS', f'{key}: E productos mol_perf',
                    f'{sn["prods"]} ahora vs {sb["prods"]} en baseline '
                    f'(ratio {ratio:.3f})')

        # --- F. familias de mol_perf --------------------------------------
        if sn['fams'] < sb['fams']:
            add('FAIL', f'{key}: F familias mol_perf',
                f'{sn["fams"]} ahora vs {sb["fams"]} en baseline (bajaron)')
        else:
            add('PASS', f'{key}: F familias mol_perf',
                f'{sn["fams"]} ahora vs {sb["fams"]} en baseline; '
                f'{sn["months"]} meses (baseline {sb["months"]})')

    n_fail = sum(1 for s, _, _ in results if s == 'FAIL')
    n_skip = sum(1 for s, _, _ in results if s == 'SKIP')
    n_pass = sum(1 for s, _, _ in results if s == 'PASS')
    print('\n' + '=' * 70)
    print(f'check-forma-vs-baseline: {n_pass} PASS  {n_fail} FAIL  {n_skip} SKIP')
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
