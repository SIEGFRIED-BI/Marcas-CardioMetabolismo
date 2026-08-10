#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La ficha por marca (brandKpis / kpiByBrand) tiene que estar AL DIA con mol_perf.

QUE VALIDA
----------
Recalcula cada ficha desde mol_perf + budget y la compara campo por campo con lo
publicado. Una ficha no la valida ningun otro gate: no rompe ninguna suma, no la mira
audit-full, y la tabla multi-periodo la ignora (calcula lo suyo desde monthly_vals). Se
puede quedar quieta meses sin que nada avise.

POR QUE EXISTE
--------------
Detectado 2026-08-06 en SNC: las 11 fichas estaban CONGELADAS en un corte viejo --
units_ytd = Jan 2026 solo (EMERAL 1.812 contra un YTD real Ene-Jun de 10.949, 6x),
real_total = Ene+Feb 2026 en 11 de 11 marcas, y bud_total de un plan ya reemplazado --
mientras el tablero mostraba Jun 2026. Ademas faltaba BREXIL entero.
kpiByBrand/brandKpis es lo que shared/export-dashboard.js usa para exportar MS%/IE/Mercado
por marca, asi que la exportacion salia con numeros de enero.

CONVENCION (verificada contra dermatologia, 156/156 campos)
-----------------------------------------------------------
  units/mkt/ms/ie   YTD = Ene..mes de cierre del año en curso vs mismo tramo del anterior.
                    MAT = los 12 meses hasta el cierre vs los 12 previos.
                    ie  = (marca_curr/marca_prev)/(mkt_curr/mkt_prev)*100; None si no hay
                    base previa o si la marca crecio mas de 4x (lanzamiento).
  bud_total/real_total/bud_pct
                    el ULTIMO MES CON VENTA REAL de la linea. NO es un acumulado.

Un desvio puede ser tres cosas distintas y el reporte NO las mezcla:
  FALTA     la marca SIE no tiene ficha
  STALE     la ficha existe pero sus numeros no son los de mol_perf hoy
  SIN-DATO  la marca no tiene budget (bud_* en null es correcto, no se cuenta como falla)

Uso: py shared/check-brandkpis-al-dia.py [--verbose] [--linea X]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent.parent
MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
LINEAS = ['cardio', 'ATB', 'OTC', 'respiratorio', 'mujer', 'SNC', 'dermatologia']
# lineas sin ficha por marca que ya estan declaradas como pendiente (ver main())
SIN_FICHA_CONOCIDAS = {'mujer'}


def cargar(ln):
    p = REPO / ln / 'data.js'
    if not p.is_file():
        return None
    t = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m:
        return None
    return json.JSONDecoder().raw_decode(t[t.index('{', m.end()):])[0]


def msort(mk):
    p = mk.split()
    return (int(p[1]), MES.index(p[0])) if len(p) == 2 and p[0] in MES else (0, 0)


def sin_lab(x):
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(x)).strip()


def ventanas(D):
    todos = sorted({k for f in D['mol_perf'].values() for p in (f.get('products') or [])
                    for k in (p.get('monthly_vals') or {})}, key=msort)
    if not todos:
        return None
    mes, anio = todos[-1].split()[0], int(todos[-1].split()[1])
    ci = MES.index(mes) + 1

    def mat(a):
        fin = a * 12 + MES.index(mes)
        return ['{} {}'.format(MES[(fin - b) % 12], (fin - b) // 12) for b in range(11, -1, -1)]
    return ([f'{MES[i]} {anio}' for i in range(ci)], [f'{MES[i]} {anio-1}' for i in range(ci)],
            mat(anio), mat(anio - 1), anio, todos[-1])


def ultimo_mes_real(D, anio):
    ult = -1
    for b in (D.get('budget') or {}).values():
        arr = ((b or {}).get(str(anio)) or {}).get('real') or []
        for i, v in enumerate(arr):
            if v is not None and v > 0:
                ult = max(ult, i)
    return ult


def suma(mv, keys):
    return sum(int(round(float(mv.get(k) or 0))) for k in keys)


def calcular(D, marca, fam, vent, i_bud, anio):
    yc, yp, mc, mp = vent
    f = D['mol_perf'][fam]
    prod = next((p for p in f['products'] if sin_lab(p['prod']).upper() == marca.upper()), None)
    if prod is None:
        return None
    mv = prod.get('monthly_vals') or {}
    fam_mv = {}
    for p in f['products']:
        for k, v in (p.get('monthly_vals') or {}).items():
            fam_mv[k] = fam_mv.get(k, 0) + int(round(float(v or 0)))
    u_yc, u_yp = suma(mv, yc), suma(mv, yp)
    u_mc, u_mp = suma(mv, mc), suma(mv, mp)
    k_yc, k_yp = suma(fam_mv, yc), suma(fam_mv, yp)
    k_mc, k_mp = suma(fam_mv, mc), suma(fam_mv, mp)

    def ie(bc, bp, mcc, mpp):
        if not bp or not mpp or not mcc:
            return None
        g = bc / bp
        return None if g > 4.0 else round(g / (mcc / mpp) * 100, 1)

    b = ((D.get('budget') or {}).get(marca) or {}).get(str(anio)) or {}
    bud, real = (b.get('budget') or []), (b.get('real') or [])
    tgt = (bud[i_bud] or None) if 0 <= i_bud < len(bud) else None
    rl = real[i_bud] if 0 <= i_bud < len(real) else None
    return {'units_ytd': u_yc, 'units_ytd25': u_yp, 'mkt_ytd26': k_yc,
            'ms_ytd': round(u_yc / k_yc * 100, 2) if k_yc else None,
            'ie_ytd': ie(u_yc, u_yp, k_yc, k_yp),
            'units_mat': u_mc, 'units_mat25': u_mp, 'mkt_mat26': k_mc,
            'ms_mat': round(u_mc / k_mc * 100, 2) if k_mc else None,
            'ie_mat': ie(u_mc, u_mp, k_mc, k_mp),
            'bud_total': tgt, 'real_total': rl,
            'bud_pct': round((rl or 0) / tgt * 100, 1) if tgt else None}


def aplanar(v):
    """brandKpis (anidada) -> las mismas claves que kpiByBrand (plana)."""
    if 'ytd' in v and isinstance(v.get('ytd'), dict):
        b = v.get('budget') or {}
        return {'units_ytd': v['ytd'].get('units'), 'units_ytd25': v['ytd'].get('units_prev'),
                'mkt_ytd26': v['ytd'].get('market_total'), 'ms_ytd': v['ytd'].get('ms'),
                'ie_ytd': v['ytd'].get('ie'),
                'units_mat': v['mat'].get('units'), 'units_mat25': v['mat'].get('units_prev'),
                'mkt_mat26': v['mat'].get('market_total'), 'ms_mat': v['mat'].get('ms'),
                'ie_mat': v['mat'].get('ie'),
                'bud_total': b.get('target'), 'real_total': b.get('real'), 'bud_pct': b.get('pct')}
    return v


CAMPOS = ['units_ytd', 'units_ytd25', 'mkt_ytd26', 'ms_ytd', 'ie_ytd',
          'units_mat', 'units_mat25', 'mkt_mat26', 'ms_mat', 'ie_mat',
          'bud_total', 'real_total', 'bud_pct']
IQVIA = CAMPOS[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--linea')
    a = ap.parse_args()

    print('[brandkpis-al-dia] la ficha por marca vs mol_perf, campo por campo')
    print('{:<14} {:>7} {:>7} {:>8} {:>7} {:>9} {:>8}  {}'.format(
        'linea', 'clave', 'fichas', 'campos', 'ok', 'STALE', 'FALTA', 'corte'))
    print('-' * 84)
    fails, detalle, notas = [], [], []
    for ln in (LINEAS if not a.linea else [a.linea]):
        D = cargar(ln)
        if not D:
            continue
        clave = 'brandKpis' if D.get('brandKpis') is not None else (
            'kpiByBrand' if D.get('kpiByBrand') is not None else None)
        if clave is None:
            # mujer es un hueco CONOCIDO y no se puede cerrar sin una decision humana: no
            # tiene budIqviaMap, que es el mapa canonico de que productos son "propios" de
            # cada familia. Sin el no se sabe la atribucion -- en cardio SYNCROCOR excluye
            # a NEBILET (co-marketing) aunque los dos son SIE, y DIOVAN incluye a DIOVAN IC.
            # Familias como 'SOLO' tienen 5 marcas propias y hay que decidir cuales cuentan.
            # Se reporta como pendiente declarado, no como falla, para que el gate siga
            # sirviendo; si OTRA linea pierde su ficha, eso si falla.
            (notas if ln in SIN_FICHA_CONOCIDAS else fails).append(
                '{}: NO TIENE ficha por marca (ni brandKpis ni kpiByBrand). La exportacion '
                'no lleva ninguna fila de MS% por marca de esta linea.{}'
                .format(ln, ' PENDIENTE DECLARADO: falta budIqviaMap para saber la '
                        'atribucion por familia.' if ln in SIN_FICHA_CONOCIDAS else ''))
            print('{:<14} {:>7} {:>7} {:>8} {:>7} {:>9} {:>8}  {}'.format(
                ln, '-', 0, 0, 0, '-', 'TODA', '-'))
            continue
        fichas = D[clave]
        v = ventanas(D)
        if not v:
            continue
        yc, yp, mc, mp, anio, corte = v
        i_bud = ultimo_mes_real(D, anio)
        sie = sorted({sin_lab(p['prod']) for f in D['mol_perf'].values()
                      for p in (f.get('products') or []) if p.get('is_sie')})
        fam_de = {}
        for fam, f in D['mol_perf'].items():
            for p in (f.get('products') or []):
                if p.get('is_sie'):
                    fam_de.setdefault(sin_lab(p['prod']).upper(), fam)
        # que marcas SIE no tienen ficha (solo cuenta si la linea keyea por marca)
        keys_up = {k.upper() for k in fichas}
        def cubierta(m):
            if m.upper() in keys_up:
                return True
            fam = fam_de_tmp.get(m.upper())
            return bool(fam) and fam.upper() in keys_up
        fam_de_tmp = {}
        for _f, _v in D['mol_perf'].items():
            for _p in (_v.get('products') or []):
                if _p.get('is_sie'):
                    fam_de_tmp.setdefault(sin_lab(_p['prod']).upper(), _f)
        falta = [m for m in sie if not cubierta(m)
                 and (D.get('budget') or {}).get(m) is not None]
        n_ok = n_mal = n_camp = 0
        for marca in sorted(fichas):
            fam = fam_de.get(marca.upper())
            if not fam:
                continue          # la ficha keyea por familia, no por marca: se salta
            c = calcular(D, marca, fam, (yc, yp, mc, mp), i_bud, anio)
            if c is None:
                continue
            pub = aplanar(fichas[marca])
            malos = []
            for k in CAMPOS:
                x, y = pub.get(k), c.get(k)
                if x is None and y is None:
                    continue
                n_camp += 1
                igual = (abs(x - y) <= 0.15) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else x == y
                if not igual and k.startswith('ie_') and (x is None) != (y is None):
                    notas.append('{} {}: {}={} vs {} (umbral de marca nueva)'.format(ln, marca, k, x, y))
                    continue
                n_ok += igual; n_mal += (not igual)
                if not igual:
                    malos.append('{}={} (deberia {})'.format(k, x, y))
            if malos:
                detalle.append((ln, marca, malos))
        estado_stale = n_mal if n_mal else 'OK'
        print('{:<14} {:>7} {:>7} {:>8} {:>7} {:>9} {:>8}  {}'.format(
            ln, clave[:7], len(fichas), n_camp, n_ok, estado_stale,
            len(falta) or 'OK', corte))
        if n_mal:
            fails.append('{}: {} campo(s) de la ficha no coinciden con mol_perf'.format(ln, n_mal))
        if falta:
            fails.append('{}: marcas SIE sin ficha: {}'.format(ln, ', '.join(falta)))

    print()
    if detalle:
        print('  desvios (marca -> campo publicado vs recalculado):')
        for ln, marca, malos in detalle[:20]:
            print('    {:<13} {:<16} {}'.format(ln, marca[:16], '; '.join(malos[:4])))
        if len(detalle) > 20:
            print('    ... y {} marca(s) mas'.format(len(detalle) - 20))
    if notas:
        print('  notas (no cuentan como falla):')
        for x in notas[:8]:
            print('    ', x)
    print('  FAILS: {}'.format(len(fails)))
    for x in fails:
        print('    ', x)
    if fails:
        print('  Para SNC: py shared/rebuild-kpibybrand-snc.py')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
