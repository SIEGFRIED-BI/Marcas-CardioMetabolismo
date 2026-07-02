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
    # Ventana = año actual + el anterior (los años que tiene el budget del tablero).
    # Incluir años más viejos hace que el merge CREE un año espurio en budget[fam]
    # (que solo tiene 2025-2026) -> columnas basura. El filtro por Año del engine no
    # aplica (ñ); ventaneamos acá (labels "Jun-2025" son ASCII). maxy-1 = 2 años.
    if months:
        maxy = max(ym_key(m)[0] for m in months)
        months = [m for m in months if ym_key(m)[0] >= maxy - 1]
    grid = defaultdict(lambda: defaultdict(float))  # (g,f,prod,cod) -> mes -> val
    for g, f, prod, cod, ym, val in rows:
        grid[(g, f, prod, cod)][ym] += val

    # Layout EXACTO del manual (5 cols de etiqueta): el merge usa col0/col1 (Gran
    # Familia/Familia); apply-otc-magnus-split.py y fix-mujer-trip-venta.py clasifican
    # por col3 = Presentación (SKU). col2 (Producto) no lo consume nadie -> familia como proxy.
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append(['Gran Familia', 'Familia', 'Producto', 'Presentación', 'Cód. Presentación'] + months)
    for (g, f, prod, cod), mv in sorted(grid.items()):
        ws.append([g, f, f, prod, cod] + [round(mv.get(m, 0)) for m in months])
    wb.save(out)
    print(f'OK: {ws.max_row - 1} filas x {len(months)} meses ({months[0]}..{months[-1]}) -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
