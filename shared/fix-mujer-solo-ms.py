#!/usr/bin/env python3
# DEPRECADO (jul-2026): NINGUN orquestador lo invoca. Lee mujer/index.html PRE-F4
# (const D inline), que ya no existe (mujer migro a mujer/data.js /
# window.OTC_DASHBOARD en commit ebf0c2f) -> hoy fallaria. Se conserva como
# referencia; si se reactiva, migrar a data.js/OTC_DASHBOARD primero.
"""
shared/fix-mujer-solo-ms.py

La familia SOLO (SIDERBLUT, FER-IN-SOL, etc.) son productos OTC y
no estan en pivots de recetas CloseUp. Para que el grafico de MS%
Recetas no muestre SOLO con datos vacios, simplemente removemos
SOLO de:
  - rec_ms (asi no aparece como pill en el selector)
  - rec_comp (datos basura asociados)
  - recetas (todo en 0)

SOLO sigue presente en:
  - sieProds (sigue siendo SIE family)
  - mol_perf (IQVIA Units intactos)
  - budget (presupuesto y venta interna intactos)
  - stock, precios, etc.

NO mezcla data IQVIA con recetas.
NO modifica nada mas.

Uso:
    py shared/fix-mujer-solo-ms.py [--dry-run]
"""

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'mujer' / 'index.html'
FAMILY = 'SOLO'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    text = HTML.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    if not m:
        print('ERROR: const D no encontrado', file=sys.stderr); return 2
    abs_start = m.start() + len('const D = ')
    abs_start = text.index('{', abs_start)
    D, end = json.JSONDecoder().raw_decode(text[abs_start:])
    abs_end = abs_start + end

    removed = []
    for section in ('rec_ms', 'rec_comp', 'recetas'):
        sec = D.get(section)
        if isinstance(sec, dict) and FAMILY in sec:
            del sec[FAMILY]
            removed.append(section)
    print(f'Removido {FAMILY} de: {removed}')

    # Verificar que SOLO sigue presente en otras secciones
    keep_in = []
    for section in ('mol_perf', 'budget', 'stock', 'precios'):
        if FAMILY in D.get(section, {}):
            keep_in.append(section)
    print(f'{FAMILY} se mantiene en: {keep_in}')

    if args.dry_run:
        print('\nDRY RUN: no se escribio.')
        return 0

    new_text = text[:abs_start] + json.dumps(D, ensure_ascii=False) + text[abs_end:]
    HTML.write_text(new_text, encoding='utf-8', newline='')
    print(f'\n-> {HTML} reescrito ({HTML.stat().st_size:,} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
