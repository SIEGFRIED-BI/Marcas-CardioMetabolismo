#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shared/itemize-molperf-otros.py

Arregla el RANKING de las tablas de Mercado IQVIA: desglosa del bucket
'Otros (resto del mercado)' las marcas que SUPERAN a la marca SIE, para que el
puesto que muestra el tablero sea el puesto real de IQVIA.

EL BUG
------
Los build-data.ps1 de cardio/ATB/OTC/respiratorio cortan en 8 productos por
mercado (`if ($selectedProductNames.Count -ge 8) { break }`) y meten todo el
resto en un unico 'Otros (resto del mercado)'. Cuando dentro de ese bucket hay
marcas MAS GRANDES que la marca propia, el tablero la muestra en un puesto que
no existe. Caso reportado: ROXOLAN se veia #7 y en IQVIA es #10, porque ROSUFEN,
ROSUSTATIN y ROSUFEC (los tres > ROXOLAN) estaban dentro de 'Otros'.
Los agregados (total de mercado y MS% propio) SIEMPRE estuvieron bien: lo unico
falso era el ranking y la lista de competidores.

POR QUE NO SE USA enrich-molperf-from-competidores.py
----------------------------------------------------
Ese script trae las marcas de competidores-data.js, que es el panel REGIONAL
(DDD, Qlik) -- otro universo que el AR_PM nacional del que sale mol_perf. Mezclar
las dos fuentes rompe la invariante sum(products) == family total. Aca se lee el
MISMO master AR_PM.

POR QUE NO SE RE-CORRE build-data.ps1 CON EL CAP MAS ALTO
---------------------------------------------------------
Regenerar esas 4 lineas desde cero revierte la venta interna del mes y todos los
splits (MAGNUS/36, ROXOLAN/PLUS, SYNCROCOR/D, TRIP). Este script es quirurgico:
solo toca mol_perf[mercado].products.

COMO PRESERVA LA CONSISTENCIA (esto es lo importante)
----------------------------------------------------
NO se elimina el bucket: se lo RECALCULA. 'Otros' sigue siendo el residuo
    Otros = total_del_mercado - suma(productos listados)
solo que ahora hay mas productos listados, asi que el residuo es mas chico. Por
construccion sum(products) == family total EXACTO, mes a mes, sin tocar ni un
valor del total del mercado. (Si se itemizara reemplazando el bucket por la suma
cruda de las marcas, el total se movaria unas decenas de unidades por el
redondeo por-producto que hace el build -- eso NO se hace.)

Se ABORTA por mercado si el residuo recalculado quedaria NEGATIVO en algun mes:
significa que el universo inferido no es el del mercado (p.ej. mercados
splitteados por dosis como CEFALEXINA ARG / ARG DUO, donde la molecula sola
sobre-cuenta). Esos mercados quedan intactos y se reportan.

Uso:
    py shared/itemize-molperf-otros.py [--master <xlsx>] [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import openpyxl

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MASTER = Path(r'C:\Users\camarinaro\OneDrive - Portalcorp\Documentos\Hub-Marcas-Inputs'
                      r'\_iqvia-master\2026-06\AR_PM_FV_Standard_Jul-2026.xlsx')
RESTO = 'Otros (resto del mercado)'
LINES = ['cardio/data.js', 'ATB/data.js', 'OTC/data.js', 'respiratorio/data.js']
MES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MI = {m: i + 1 for i, m in enumerate(MES)}


def msort(mk):
    p = str(mk).split()
    return (int(p[1]), MI.get(p[0], 0)) if len(p) == 2 and p[1].isdigit() else (0, 0)


def qkey(mk):
    p = mk.split()
    m = MI.get(p[0])
    return 'Q{} {}'.format((m - 1) // 3 + 1, p[1]) if m else None


def read_master(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    r1 = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
    ci, mcols = {}, []
    for i, h in enumerate(r1):
        if not h:
            continue
        s = str(h).strip()
        sn = s.replace('\n', ' ').strip().lower()
        if sn.startswith('manufacturer'):
            ci['manuf'] = i
        elif sn.startswith('product'):
            ci['prod'] = i
        elif sn.startswith('molecules'):
            ci['mol'] = i
        if s.startswith('Units'):
            a = (s.split('\n', 1)[-1] if '\n' in s else s[len('Units'):]).strip()
            if a.upper().startswith(('MAT', 'YTD')):
                continue
            m = re.match(r'(\w+)\s+(\d{4})$', a)
            if m and m.group(1) in MI:
                mcols.append((i, '{} {}'.format(m.group(1), m.group(2))))
    prods = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        p = row[ci['prod']] if ci['prod'] < len(row) else None
        if not p:
            continue
        name = str(p).strip()
        d = prods.setdefault(name, {'manuf': '', 'mol': '', 'monthly': defaultdict(float)})
        if ci.get('manuf') is not None and ci['manuf'] < len(row) and row[ci['manuf']]:
            d['manuf'] = str(row[ci['manuf']]).strip()
        if ci.get('mol') is not None and ci['mol'] < len(row) and row[ci['mol']]:
            d['mol'] = str(row[ci['mol']]).strip()
        for c, mk in mcols:
            if c < len(row) and isinstance(row[c], (int, float)):
                d['monthly'][mk] += row[c]
    wb.close()
    for d in prods.values():
        d['monthly'] = {k: int(round(v)) for k, v in d['monthly'].items()}
    return prods, [mk for _, mk in mcols]


def strip_suffix(p):
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(p)).strip().upper()


def agg_from_monthly(monthly, keys_ref, kind, cierre):
    """Agrega monthly a quarterly/ytd/mat usando SOLO las keys que ya existen en el
    mercado (keys_ref), para no inventar columnas nuevas."""
    out = {}
    if kind == 'quarterly':
        tmp = defaultdict(int)
        for mk, v in monthly.items():
            q = qkey(mk)
            if q:
                tmp[q] += int(v or 0)
        return {k: tmp.get(k, 0) for k in keys_ref}
    for key in keys_ref:
        p = str(key).split()
        if len(p) != 2 or not p[1].isdigit():
            continue
        cm, y = MI.get(p[0], cierre), int(p[1])
        if kind == 'ytd':
            win = ['{} {}'.format(MES[m - 1], y) for m in range(1, cm + 1)]
        else:
            win = []
            for back in range(11, -1, -1):
                idx = (y * 12 + (cm - 1)) - back
                yy, mm = divmod(idx, 12)
                win.append('{} {}'.format(MES[mm], yy))
        out[key] = sum(int(monthly.get(mk, 0) or 0) for mk in win)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', default=str(DEFAULT_MASTER))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    mp_path = Path(a.master)
    if not mp_path.is_file():
        print('ERROR: master no existe: {}'.format(mp_path), file=sys.stderr)
        return 2
    print('Master: {}'.format(mp_path))
    MPROD, MMONTHS = read_master(mp_path)
    print('  {} productos en el master, {} meses ({}..{})'.format(
        len(MPROD), len(MMONTHS), MMONTHS[0], MMONTHS[-1]))
    by_exact = set(MPROD)
    by_base = defaultdict(list)
    for n in MPROD:
        by_base[strip_suffix(n)].append(n)

    print()
    print('{:<12} {:<24} {:>9} {:>9} {:>6} {:>13} {}'.format(
        'linea', 'mercado', 'rank_ant', 'rank_new', 'items', 'Otros nuevo', 'estado'))
    print('-' * 108)

    planned = []
    tocados = saltados = 0
    for rel in LINES:
        p = REPO / rel
        text = p.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
        s = text.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(text[s:])
        e = s + end
        cambios_linea = 0

        for fam, f in (D.get('mol_perf') or {}).items():
            prods = f.get('products') or []
            resto = next((x for x in prods if str(x.get('prod')) == RESTO), None)
            if not resto:
                continue
            fam_monthly = {k: int(v or 0) for k, v in (f.get('monthly') or {}).items()}
            if not fam_monthly:
                continue
            last = max(fam_monthly, key=msort)
            cierre = MI[last.split()[0]]
            listados = [x for x in prods if x is not resto]
            sie = [x for x in listados if x.get('is_sie')]
            if not sie:
                continue
            principal = max(sie, key=lambda x: (x.get('mat') or {}).get(last, 0) or 0)
            sie_mat = (principal.get('mat') or {}).get(last, 0) or 0

            # universo del mercado inferido de los listados
            mols, encontrados = set(), set()
            for x in listados:
                nm = str(x.get('prod'))
                cand = nm if nm in by_exact else (by_base.get(strip_suffix(nm)) or [None])[0]
                if cand:
                    encontrados.add(cand)
                    if MPROD[cand]['mol']:
                        mols.add(MPROD[cand]['mol'])
            if not mols:
                continue
            ocultos = [n for n, d in MPROD.items() if d['mol'] in mols and n not in encontrados]
            if not ocultos:
                continue

            # MAT de cada oculto, para saber quien supera a la marca SIE
            idx = MMONTHS.index(last) if last in MMONTHS else len(MMONTHS) - 1
            w = MMONTHS[max(0, idx - 11):idx + 1]
            mat_of = {n: sum(MPROD[n]['monthly'].get(mk, 0) for mk in w) for n in ocultos}
            superan = sorted([n for n in ocultos if mat_of[n] > sie_mat],
                             key=lambda n: -mat_of[n])

            orden_ant = sorted(prods, key=lambda x: -((x.get('mat') or {}).get(last, 0) or 0))
            rank_ant = [i for i, x in enumerate(orden_ant, 1) if x is principal][0]

            if not superan:
                continue    # el rank ya era correcto

            # --- construir los productos nuevos, restringidos a los meses del mercado ---
            meses_mkt = sorted(fam_monthly, key=msort)
            q_ref = list((f.get('quarterly') or {}).keys())
            y_ref = list((f.get('ytd') or {}).keys())
            m_ref = list((f.get('mat') or {}).keys())
            nuevos = []
            for n in superan:
                monthly = {mk: int(MPROD[n]['monthly'].get(mk, 0) or 0) for mk in meses_mkt}
                if not any(monthly.values()):
                    continue
                nuevos.append({
                    'prod': n,
                    'manuf': MPROD[n]['manuf'],
                    'is_sie': False,
                    'monthly_vals': monthly,
                    'quarterly_vals': agg_from_monthly(monthly, q_ref, 'quarterly', cierre),
                    'ytd': agg_from_monthly(monthly, y_ref, 'ytd', cierre),
                    'mat': agg_from_monthly(monthly, m_ref, 'mat', cierre),
                    'ms_monthly': {}, 'ms_quarterly': {}, 'ms_ytd': {}, 'ms_mat': {},
                })
            if not nuevos:
                continue

            # --- recalcular el residuo: total - suma(listados + nuevos) ---
            def suma(campo, keys):
                acc = defaultdict(int)
                for x in listados + nuevos:
                    d = x.get(campo) or {}
                    for k in keys:
                        acc[k] += int(d.get(k, 0) or 0)
                return acc

            s_m = suma('monthly_vals', meses_mkt)
            s_q = suma('quarterly_vals', q_ref)
            s_y = suma('ytd', y_ref)
            s_t = suma('mat', m_ref)
            neg = [mk for mk in meses_mkt if fam_monthly[mk] - s_m[mk] < 0]
            if neg:
                saltados += 1
                print('{:<12} {:<24} {:>9} {:>9} {:>6} {:>13} {}'.format(
                    rel.split('/')[0][:12], fam[:24], '#' + str(rank_ant), '-', len(nuevos), '-',
                    'SALTADO: residuo negativo en {} mes(es) -> el universo inferido no es el del mercado'.format(len(neg))))
                continue

            nuevo_resto_m = {mk: fam_monthly[mk] - s_m[mk] for mk in meses_mkt}
            nuevo_resto_q = {k: int((f.get('quarterly') or {}).get(k, 0) or 0) - s_q[k] for k in q_ref}
            nuevo_resto_y = {k: int((f.get('ytd') or {}).get(k, 0) or 0) - s_y[k] for k in y_ref}
            nuevo_resto_t = {k: int((f.get('mat') or {}).get(k, 0) or 0) - s_t[k] for k in m_ref}
            if any(v < 0 for v in list(nuevo_resto_q.values()) + list(nuevo_resto_y.values()) + list(nuevo_resto_t.values())):
                saltados += 1
                print('{:<12} {:<24} {:>9} {:>9} {:>6} {:>13} {}'.format(
                    rel.split('/')[0][:12], fam[:24], '#' + str(rank_ant), '-', len(nuevos), '-',
                    'SALTADO: residuo negativo en un agregado'))
                continue

            resto['monthly_vals'] = nuevo_resto_m
            resto['quarterly_vals'] = nuevo_resto_q
            resto['ytd'] = nuevo_resto_y
            resto['mat'] = nuevo_resto_t

            finales = listados + nuevos + [resto]
            # ms_* de TODOS contra el total de familia (que no cambio)
            for x in finales:
                mv = x.get('monthly_vals') or {}
                x['ms_monthly'] = {mk: (round(int(mv.get(mk, 0) or 0) / fam_monthly[mk] * 100, 2)
                                        if fam_monthly.get(mk) else 0) for mk in meses_mkt}
                for campo, ref, dst in (('quarterly_vals', q_ref, 'ms_quarterly'),
                                        ('ytd', y_ref, 'ms_ytd'), ('mat', m_ref, 'ms_mat')):
                    src = x.get(campo) or {}
                    base = f.get('quarterly' if campo == 'quarterly_vals' else campo) or {}
                    x[dst] = {k: (round(int(src.get(k, 0) or 0) / int(base.get(k) or 0) * 100, 2)
                                  if int(base.get(k) or 0) else 0) for k in ref}
            finales.sort(key=lambda x: (not x.get('is_sie'), -((x.get('mat') or {}).get(last, 0) or 0)))
            f['products'] = finales

            orden_new = sorted(finales, key=lambda x: -((x.get('mat') or {}).get(last, 0) or 0))
            rank_new = [i for i, x in enumerate(orden_new, 1) if x is principal][0]
            tocados += 1
            cambios_linea += 1
            print('{:<12} {:<24} {:>9} {:>9} {:>6} {:>13,} {}'.format(
                rel.split('/')[0][:12], fam[:24], '#' + str(rank_ant), '#' + str(rank_new),
                len(nuevos), nuevo_resto_t.get(last, 0),
                'OK  ' + ', '.join(x['prod'] for x in nuevos[:3]) + ('...' if len(nuevos) > 3 else '')))

        if cambios_linea:
            planned.append((p, text, s, e, D))

    print()
    print('mercados corregidos: {} | saltados por no reconciliar: {}'.format(tocados, saltados))
    if a.dry_run:
        print('\nDRY RUN: no se escribio nada.')
        return 0
    print()
    for p, text, s, e, D in planned:
        p.write_text(text[:s] + json.dumps(D, ensure_ascii=False) + text[e:],
                     encoding='utf-8', newline='')
        print('-> {} ({:,} bytes)'.format(p.relative_to(REPO), p.stat().st_size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
