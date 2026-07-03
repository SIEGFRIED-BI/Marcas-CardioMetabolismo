# -*- coding: utf-8 -*-
"""GATE: mujer/data.js mol_perf debe usar segmentacion por CLASE IQVIA
(ALTA DOSIS, SIN ESTROGENO, BAJA DOSIS 21+7, ...), NUNCA por MARCA
(ISIS, SIDERBLUT, TRIP D3, CALCIO BASE DUPOMAR, ...).

POR QUE EXISTE: mujer es una linea IQVIA-preservada (igual que SNC/derma). Su
mol_perf NO se reconstruye desde cero en build-all; se PRESERVA de prod y solo se
le actualiza el time-series (shared/sync-mujer-pm.py) + preserve-early-history.
La segmentacion por CLASE es un artefacto estable creado one-off (2026-04) y
preservado incrementalmente. Si alguien vuelve a meter 'mujer' en la lista de
build-all, mujer/build-data.ps1 la reconstruiria por MARCA (array
$dashboardFamilyOrder) y clobbearia la estructura de prod -> el tablero de mujer
mostraria mercados completamente distintos. ESTE GATE detecta esa regresion y
bloquea el commit/cierre antes de que llegue a prod.

Ver: shared/update-all.ps1 (mujer excluida de build-all), memoria rearquitectura-cierre.

Exit 0 si OK; 1 si detecta segmentacion por marca o faltan clases esperadas.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / 'mujer' / 'data.js'

# Marcadores DISTINTIVOS de la segmentacion por CLASE (deben estar TODOS).
# Son nombres que SOLO existen en la vista por clase, nunca en la por marca.
REQUIRED_CLASS = ['ALTA DOSIS', 'SIN ESTROGENO', 'BAJA DOSIS 21+7']

# Marcadores DISTINTIVOS de la segmentacion por MARCA (build-data.ps1
# $dashboardFamilyOrder). Si CUALQUIERA aparece como key de mol_perf, mujer fue
# reconstruida por build-data -> REGRESION.
FORBIDDEN_BRAND = ['ISIS', 'ISIS FREE', 'ISIS MINI', 'SIDERBLUT',
                   'TRIP D3', 'CALCIO BASE DUPOMAR', 'DELTROX NF']

MIN_FAMILIES = 12  # prod tiene 14; margen por si alguna clase queda sin data un mes


def load_mol_perf():
    t = DATA.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'(?:const D|window\.OTC_DASHBOARD)\s*=\s*', t)
    if not m:
        raise RuntimeError('mujer/data.js: no se encontro window.OTC_DASHBOARD')
    ob = t.index('{', m.end())
    D, _ = json.JSONDecoder().raw_decode(t[ob:])
    return D.get('mol_perf', {}) or {}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        mol = load_mol_perf()
    except Exception as e:
        print(f'MUJER-SEG FAIL: no se pudo leer mujer/data.js ({e})')
        return 1
    fams = set(mol.keys())

    problems = []
    brand_leaked = sorted(f for f in FORBIDDEN_BRAND if f in fams)
    if brand_leaked:
        problems.append(f'segmentacion por MARCA detectada (mujer reconstruida por '
                        f'build-data en vez de preservada+synced): {brand_leaked}')
    missing_class = sorted(f for f in REQUIRED_CLASS if f not in fams)
    if missing_class:
        problems.append(f'faltan clases IQVIA esperadas: {missing_class}')
    if len(fams) < MIN_FAMILIES:
        problems.append(f'solo {len(fams)} familias (esperadas >= {MIN_FAMILIES})')

    if problems:
        print('MUJER-SEG FAIL: mujer/data.js mol_perf NO tiene la segmentacion por CLASE.')
        for p in problems:
            print(f'  - {p}')
        print('  Causa tipica: se metio "mujer" en la lista de build-all. mujer debe '
              'quedar FUERA de build-all (como SNC/derma): se preserva de prod y solo '
              'se le actualiza el time-series (sync-mujer-pm.py).')
        return 1

    print(f'OK: mujer segmentada por CLASE IQVIA ({len(fams)} familias; '
          f'clases clave presentes; sin fugas por marca).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
