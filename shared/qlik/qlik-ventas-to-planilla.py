# -*- coding: utf-8 -*-
"""shared/qlik/qlik-ventas-to-planilla.py

Convierte el JSON de extract-ventas.mjs en un xlsx con el layout que espera
merge-ventas-internas.py:

    Gran Familia | Familia | Producto | Cód. Presentación | <Mes-YYYY> ...

Una fila por SKU (gran_familia, familia, producto, CodigoProducto); una columna por mes.
Los meses salen ordenados cronológicamente. El cutoff (mes cerrado) NO se aplica acá:
lo aplica merge-ventas-internas.py con --cutoff.

Uso:
    py shared/qlik/qlik-ventas-to-planilla.py <input.json> <output.xlsx>
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
import openpyxl

MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MES_IDX = {m: i for i, m in enumerate(MES)}


def ym_key(label):
    """'Jun-2025' -> (2025, 5) para ordenar cronológicamente."""
    m, y = label.split('-')
    return (int(y), MES_IDX.get(m, 0))


def main():
    if len(sys.argv) < 3:
        print('uso: qlik-ventas-to-planilla.py <input.json> <output.xlsx>', file=sys.stderr)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    rows = json.load(open(src, encoding='utf-8'))

    months = sorted({r[4] for r in rows}, key=ym_key)
    # ventana: quedarse con los ultimos ~3 anios (el filtro por Año del engine no aplica
    # por la ñ; los labels "Jun-2025" son ASCII asi que ventaneamos aca, robusto).
    if months:
        maxy = max(ym_key(m)[0] for m in months)
        months = [m for m in months if ym_key(m)[0] >= maxy - 2]
    grid = defaultdict(lambda: defaultdict(float))  # (g,f,prod,cod) -> mes -> val
    for g, f, prod, cod, ym, val in rows:
        grid[(g, f, prod, cod)][ym] += val

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append(['Gran Familia', 'Familia', 'Producto', 'Cód. Presentación'] + months)
    for (g, f, prod, cod), mv in sorted(grid.items()):
        ws.append([g, f, prod, cod] + [round(mv.get(m, 0)) for m in months])
    wb.save(out)
    print(f'OK: {ws.max_row - 1} filas x {len(months)} meses ({months[0]}..{months[-1]}) -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
