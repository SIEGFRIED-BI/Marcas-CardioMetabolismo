#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruye SNC/data.js -> kpiByBrand desde mol_perf + budget.

POR QUE
-------
Las 11 fichas de SNC estaban CONGELADAS EN UN CORTE VIEJO, y nadie lo veia porque la
ficha no la valida ningun gate:
    EMERAL  units_ytd = 1.812     <- es Jan 2026 solo (Jan 2026 = 1.813)
            mkt_ytd26 = 547.116   <- idem (Jan 2026 = 547.438)
            YTD real Ene-Jun 2026 = 10.949
    real_total = suma Ene+Feb 2026  (11 de 11 marcas, exacto)
O sea: la parte IQVIA quedo en enero, la venta interna en febrero, y el budget de un plan
que despues se reemplazo (por eso bud_total ya no matchea ninguna ventana del budget
actual). Mientras tanto el tablero muestra Jun 2026.
Y ademas faltaba BREXIL entero: 11 fichas para 12 marcas SIE. kpiByBrand es lo que
shared/export-dashboard.js usa para exportar MS%/IE/Mercado por marca, asi que BREXIL no
salia en la exportacion y las otras 11 salian con numeros de enero.

DE DONDE SALE CADA CAMPO (convencion tomada de dermatologia, que es la linea sana)
---------------------------------------------------------------------------------
  units/mkt/ms/ie   mol_perf: YTD = Ene..mes de cierre del año en curso vs mismo tramo del
                    año anterior; MAT = los 12 meses hasta el cierre vs los 12 previos.
                    ie = (marca_curr/marca_prev) / (mercado_curr/mercado_prev) * 100,
                    None si no hay base previa o si la marca crecio mas de 4x (lanzamiento).
  bud_total/real_total/bud_pct
                    budget[marca][año] en el ULTIMO MES CON VENTA REAL de la linea (no es
                    un YTD: en dermato el bloque budget es Jul..Jul y da 12/12 exacto en
                    target y en real).
  ms_rec            se preserva el valor que ya tenia la ficha (en SNC las 11 son null;
                    recetas es otro subsistema y no se recalcula aca).
  mol               la familia de mol_perf donde vive el producto SIE.

VALIDACION
----------
--check corre las MISMAS formulas contra dermatologia/brandKpis, que esta al dia, y exige
reproducirla campo por campo. Dio 120/120 en los campos IQVIA y 12/12 en el bloque budget.
Si eso no cierra, las fichas de SNC que salgan de aca serian inventadas: no se escribe.

Uso: py shared/rebuild-kpibybrand-snc.py [--check] [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent.parent
MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def cargar(rel):
    t = (REPO / rel).read_text(encoding='utf-8', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    s = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[s:])
    return {'text': t, 'ini': s, 'fin': s + end, 'D': D}


def msort(mk):
    p = mk.split()
    return (int(p[1]), MES.index(p[0])) if len(p) == 2 and p[0] in MES else (0, 0)


def sin_lab(x):
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(x)).strip()


def ventanas(D):
    todos = sorted({k for f in D['mol_perf'].values() for p in (f.get('products') or [])
                    for k in (p.get('monthly_vals') or {})}, key=msort)
    mes, anio = todos[-1].split()[0], int(todos[-1].split()[1])
    ci = MES.index(mes) + 1

    def mat(a):
        fin = a * 12 + MES.index(mes)
        return ['{} {}'.format(MES[(fin - b) % 12], (fin - b) // 12) for b in range(11, -1, -1)]
    return ([f'{MES[i]} {anio}' for i in range(ci)], [f'{MES[i]} {anio-1}' for i in range(ci)],
            mat(anio), mat(anio - 1), anio, todos[-1])


def ultimo_mes_real(D, anio):
    """Indice del ultimo mes con venta real > 0 en toda la linea. Es el mes al que se
    refiere el bloque budget de la ficha (no es un acumulado)."""
    ult = -1
    for b in (D.get('budget') or {}).values():
        arr = ((b or {}).get(str(anio)) or {}).get('real') or []
        for i, v in enumerate(arr):
            if v is not None and v > 0:
                ult = max(ult, i)
    return ult


def suma(mv, keys):
    return sum(int(round(float(mv.get(k) or 0))) for k in keys)


def calcular(D, marca, fam, ventana, i_bud, anio):
    ytd_c, ytd_p, mat_c, mat_p = ventana
    f = D['mol_perf'][fam]
    prod = next((p for p in f['products'] if sin_lab(p['prod']).upper() == marca.upper()), None)
    if prod is None:
        return None
    mv = prod.get('monthly_vals') or {}
    fam_mv = {}
    for p in f['products']:
        for k, v in (p.get('monthly_vals') or {}).items():
            fam_mv[k] = fam_mv.get(k, 0) + int(round(float(v or 0)))
    u_yc, u_yp = suma(mv, ytd_c), suma(mv, ytd_p)
    u_mc, u_mp = suma(mv, mat_c), suma(mv, mat_p)
    k_yc, k_yp = suma(fam_mv, ytd_c), suma(fam_mv, ytd_p)
    k_mc, k_mp = suma(fam_mv, mat_c), suma(fam_mv, mat_p)

    def ie(bc, bp, mc, mp):
        if not bp or not mp or not mc:
            return None
        g = bc / bp
        if g > 4.0:                      # lanzamiento: sin comparable
            return None
        return round(g / (mc / mp) * 100, 1)

    b = ((D.get('budget') or {}).get(marca) or {}).get(str(anio)) or {}
    bud = (b.get('budget') or [])
    real = (b.get('real') or [])
    tgt = bud[i_bud] if 0 <= i_bud < len(bud) else None
    rl = real[i_bud] if 0 <= i_bud < len(real) else None
    pct = round((rl or 0) / tgt * 100, 1) if tgt else None
    return {'ie_ytd': ie(u_yc, u_yp, k_yc, k_yp), 'ie_mat': ie(u_mc, u_mp, k_mc, k_mp),
            'ms_ytd': round(u_yc / k_yc * 100, 2) if k_yc else None,
            'ms_mat': round(u_mc / k_mc * 100, 2) if k_mc else None,
            'units_ytd': u_yc, 'units_mat': u_mc, 'units_ytd25': u_yp, 'units_mat25': u_mp,
            'mkt_ytd26': k_yc, 'mkt_mat26': k_mc,
            'bud_pct': pct, 'bud_total': tgt, 'real_total': rl, 'mol': fam}


def familia_de(D, marca):
    for fam, f in D['mol_perf'].items():
        for p in (f.get('products') or []):
            if p.get('is_sie') and sin_lab(p['prod']).upper() == marca.upper():
                return fam
    return None


def marcas_sie(D):
    return sorted({sin_lab(p['prod']) for f in D['mol_perf'].values()
                   for p in (f.get('products') or []) if p.get('is_sie')})


def check_dermato():
    """Las mismas formulas tienen que reproducir dermatologia/brandKpis, que esta al dia."""
    info = cargar('dermatologia/data.js')
    D = info['D']
    yc, yp, mc, mp, anio, corte = ventanas(D)
    i_bud = ultimo_mes_real(D, anio)
    print('validacion contra dermatologia (corte {}, budget en {} {})'
          .format(corte, MES[i_bud], anio))
    ok = mal = 0
    for marca, v in sorted(D['brandKpis'].items()):
        fam = familia_de(D, marca)
        c = calcular(D, marca, fam, (yc, yp, mc, mp), i_bud, anio)
        esperado = {
            'units_ytd': v['ytd']['units'], 'units_ytd25': v['ytd']['units_prev'],
            'mkt_ytd26': v['ytd']['market_total'], 'ms_ytd': v['ytd']['ms'], 'ie_ytd': v['ytd']['ie'],
            'units_mat': v['mat']['units'], 'units_mat25': v['mat']['units_prev'],
            'mkt_mat26': v['mat']['market_total'], 'ms_mat': v['mat']['ms'], 'ie_mat': v['mat']['ie'],
            'bud_total': v['budget']['target'], 'real_total': v['budget']['real'],
            'bud_pct': v['budget']['pct']}
        malos = []
        for k, a in esperado.items():
            b = c.get(k)
            igual = (abs(a - b) <= 0.15) if isinstance(a, float) and isinstance(b, (int, float)) else a == b
            ok += igual; mal += (not igual)
            if not igual:
                malos.append('{}: {} vs {}'.format(k, a, b))
        print('  {:<14} {}'.format(marca, 'OK' if not malos else 'FAIL -> ' + '; '.join(malos[:3])))
    print('  {} de {} campos reproducidos'.format(ok, ok + mal))
    return mal == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='solo valida contra dermatologia')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if not check_dermato():
        print('\nABORTADO: las formulas no reproducen dermatologia. Las fichas de SNC que '
              'salgan de aca serian inventadas.', file=sys.stderr)
        return 1
    if a.check:
        return 0

    info = cargar('SNC/data.js')
    D = info['D']
    yc, yp, mc, mp, anio, corte = ventanas(D)
    i_bud = ultimo_mes_real(D, anio)
    viejo = D.get('kpiByBrand') or {}
    print()
    print('SNC: corte IQVIA {}, budget en {} {}'.format(corte, MES[i_bud], anio))
    print('{:<14} {:>10} {:>10} {:>10} {:>10} {:>8} {:>8}'.format(
        'marca', 'units_ytd', '(antes)', 'mkt_ytd', '(antes)', 'ms_ytd', '(antes)'))
    print('-' * 76)
    nuevo = {}
    for marca in marcas_sie(D):
        fam = familia_de(D, marca)
        c = calcular(D, marca, fam, (yc, yp, mc, mp), i_bud, anio)
        if c is None:
            continue
        # recetas: es otro subsistema, se preserva lo que ya habia
        c['ms_rec'] = (viejo.get(marca) or {}).get('ms_rec')
        c = {k: c[k] for k in ('ie_ytd', 'ie_mat', 'ms_ytd', 'ms_mat', 'units_ytd', 'units_mat',
                               'units_ytd25', 'units_mat25', 'mkt_ytd26', 'mkt_mat26',
                               'ms_rec', 'bud_pct', 'bud_total', 'real_total', 'mol')}
        nuevo[marca] = c
        v = viejo.get(marca) or {}
        print('{:<14} {:>10,} {:>10} {:>10,} {:>10} {:>8} {:>8}'.format(
            marca + (' NUEVA' if marca not in viejo else ''), c['units_ytd'],
            '{:,}'.format(v['units_ytd']) if v else '-', c['mkt_ytd26'],
            '{:,}'.format(v['mkt_ytd26']) if v else '-', c['ms_ytd'], v.get('ms_ytd', '-')))
    print()
    print('  fichas: {} -> {}   (agregadas: {})'.format(
        len(viejo), len(nuevo), ', '.join(sorted(set(nuevo) - set(viejo))) or 'ninguna'))
    if a.dry_run:
        print('DRY RUN: no se escribio nada.')
        return 0
    D['kpiByBrand'] = nuevo
    p = REPO / 'SNC/data.js'
    antes = p.stat().st_size
    p.write_text(info['text'][:info['ini']] + json.dumps(D, ensure_ascii=False)
                 + info['text'][info['fin']:], encoding='utf-8', newline='')
    print('  SNC/data.js {:,} -> {:,} bytes'.format(antes, p.stat().st_size))
    return 0


if __name__ == '__main__':
    sys.exit(main())
