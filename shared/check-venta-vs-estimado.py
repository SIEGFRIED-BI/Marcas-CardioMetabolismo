"""Chequea %Cumplimiento (venta interna / estimado) por producto en las 7 lineas.
Un %Cumpl absurdo (muy alto o muy bajo) casi siempre indica un error de
GRANULARIDAD/MAPEO en la Venta Interna — p.ej. sumar una Gran Familia entera a
una sub-marca (el bug de ALTA DOSIS = 705%, jun-2026).

Umbrales (sobre el total del año con datos):
  - FAIL  : %Cumpl > 500%   -> casi seguro LUMPING (venta inflada por sumar la
            Gran Familia entera a una sub-marca, el bug ALTA DOSIS=705%). exit 1.
  - WARN  : %Cumpl > 300%  o  < 30%   -> revisar (puede ser bajo cumplimiento real,
            venta sin mapear, o producto discontinuado; NO bloquea).

Se bloquea solo en el lado ALTO porque el bug de granularidad SIEMPRE infla la
venta. El lado bajo es ambiguo (no se bloquea).

Solo evalua productos que tengan estimado (budget) cargado.

Uso: py shared/check-venta-vs-estimado.py
Exit 0 si todo OK/solo-warn; exit 1 si hay algun FAIL (cumpl >500%).
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('cardio', 'cardio/data.js', False), ('ATB', 'ATB/data.js', False),
    ('OTC', 'OTC/data.js', False), ('respi', 'respiratorio/data.js', False),
    ('mujer', 'mujer/index.html', True), ('SNC', 'SNC/index.html', True),
    ('derma', 'dermatologia/data.js', False),
]
WARN_HI, FAIL_HI = 300, 500
WARN_LO = 30  # < WARN_LO -> warning (no bloquea; cumpl bajo es ambiguo)


def load(path, inline):
    enc = 'utf-8' if inline else 'utf-8-sig'
    t = (REPO / path).read_text(encoding=enc, errors='replace')
    if inline:
        m = re.search(r'const D\s*=\s*\{', t); ob = m.end() - 1
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t); ob = t.index('{', m.end())
    return json.JSONDecoder().raw_decode(t[ob:])[0]


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    warns, fails = [], []
    for name, path, inline in LINES:
        D = load(path, inline)
        for prod, years in (D.get('budget') or {}).items():
            for yr, yo in (years or {}).items():
                real = yo.get('real') or []
                bud = yo.get('budget') or []
                # solo meses donde AMBOS tienen dato > 0
                sr = sb = 0
                for i in range(min(len(real), len(bud), 12)):
                    rv, bv = real[i], bud[i]
                    if rv is not None and bv is not None and bv > 0:
                        sr += rv or 0; sb += bv or 0
                if sb <= 0:
                    continue
                pct = sr / sb * 100
                if pct > FAIL_HI:
                    fails.append((name, prod, yr, round(pct)))
                elif pct > WARN_HI or pct < WARN_LO:
                    warns.append((name, prod, yr, round(pct)))
    if warns:
        print('WARN (%Cumpl sospechoso, revisar):')
        for n, p, y, pc in warns: print(f'  [{n}] {p} {y}: {pc}%')
    if fails:
        print('FAIL (%Cumpl >500%, casi seguro LUMPING: venta inflada por granularidad):')
        for n, p, y, pc in fails: print(f'  [{n}] {p} {y}: {pc}%')
        print('\n-> Revisar el matcheo en merge-ventas-internas.py (Familia vs Gran Familia).')
        return 1
    if not warns:
        print('OK: %Cumpl razonable en todos los productos con estimado.')
    else:
        print('\n(solo warnings, no bloquea)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
