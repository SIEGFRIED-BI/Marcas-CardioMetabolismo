#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresca SOLO el bloque budget de la ficha por marca (brandKpis / kpiByBrand).

POR QUE HACE FALTA UN SCRIPT APARTE
-----------------------------------
Los fix-brandkpis-* recalculan la parte IQVIA (units/mkt/ms/ie) pero NO tocan el bloque
budget (target/real/pct). Cuando entra un mes nuevo de VENTA INTERNA -- que puede ir
adelante de IQVIA, porque SAP esta al dia y IQVIA reporta con ~2 meses de atraso -- la
ficha se queda con el mes anterior y el Check 15
(shared/check-brandkpis-al-dia.py) bloquea el commit.
Paso 2026-09-02 al subir la venta de Jul a Ago-2026: 201 campos de 6 lineas quedaron
desfasados, todos bud_total / real_total / bud_pct.

CONVENCION (la misma que valida el Check 15)
--------------------------------------------
El bloque budget NO es un acumulado: es el ULTIMO MES CON VENTA REAL de la linea.
Un target de 0 se guarda como None -- un target de cero no es un target y el % de
cumplimiento seria indefinido (SYNCROCOR / SYNCROCOR D / TELPRES tienen budget 0 en
meses con venta > 0).

Uso: py shared/refresh-brandkpis-budget.py [--dry-run]
"""
from __future__ import annotations
import argparse, importlib.util, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location('chk', REPO / 'shared' / 'check-brandkpis-al-dia.py')
chk = importlib.util.module_from_spec(_s)
_s.loader.exec_module(chk)


def cargar(ln):
    p = REPO / ln / 'data.js'
    t = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m:
        return None
    s = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[s:])
    return {'p': p, 'text': t, 'ini': s, 'fin': s + end, 'D': D}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    tot = 0
    for ln in chk.LINEAS:
        info = cargar(ln)
        if not info:
            continue
        D = info['D']
        clave = 'brandKpis' if D.get('brandKpis') is not None else (
            'kpiByBrand' if D.get('kpiByBrand') is not None else None)
        if clave is None:
            continue
        v = chk.ventanas(D)
        if not v:
            continue
        anio = v[4]
        i_bud = chk.ultimo_mes_real(D, anio)
        if i_bud < 0:
            print('  {:<14} sin venta real en {}'.format(ln, anio)); continue
        n = 0
        for marca, ficha in D[clave].items():
            b = ((D.get('budget') or {}).get(marca) or {}).get(str(anio)) or {}
            bud, real = (b.get('budget') or []), (b.get('real') or [])
            tgt = (bud[i_bud] or None) if 0 <= i_bud < len(bud) else None
            rl = real[i_bud] if 0 <= i_bud < len(real) else None
            pct = round((rl or 0) / tgt * 100, 1) if tgt else None
            if 'ytd' in ficha and isinstance(ficha.get('ytd'), dict):
                antes = ficha.get('budget') or {}
                nuevo = {'pct': pct, 'real': rl, 'target': tgt}
                if antes != nuevo:
                    ficha['budget'] = nuevo; n += 1
            else:
                if (ficha.get('bud_total'), ficha.get('real_total'), ficha.get('bud_pct')) != (tgt, rl, pct):
                    ficha['bud_total'], ficha['real_total'], ficha['bud_pct'] = tgt, rl, pct
                    n += 1
        tot += n
        print('  {:<14} {:<11} mes de venta: {} {}  ->  {} ficha(s) actualizada(s)'
              .format(ln, clave, chk.MES[i_bud], anio, n))
        if n and not a.dry_run:
            info['p'].write_text(
                info['text'][:info['ini']] + json.dumps(D, ensure_ascii=False) + info['text'][info['fin']:],
                encoding='utf-8', newline='')
    print('  total: {} ficha(s){}'.format(tot, ' (DRY RUN, no se escribio)' if a.dry_run else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
