# -*- coding: utf-8 -*-
"""Convierte el JSON de extract-ddd.mjs en el xlsx 'Producto-Molécula-ATC-provincia'
que espera build-competidores-shape-a.py (9 columnas, 1 fila header + datos).
El orden del JSON ya coincide con las columnas del archivo manual.

Uso: py shared/qlik/ddd-json-to-xlsx.py <in.json> <out.xlsx>
"""
import json, sys
import openpyxl

HEADER = ['RegionCUP', 'Mercado', 'Droga', 'Clase Terapeutica', 'AñoMes',
          'Codigo Clase Terapeutica', 'Codigo Producto', 'Producto', 'Unidades']


def main():
    if len(sys.argv) < 3:
        print('uso: ddd-json-to-xlsx.py <in.json> <out.xlsx>', file=sys.stderr); return 2
    src, out = sys.argv[1], sys.argv[2]
    rows = json.load(open(src, encoding='utf-8'))
    wb = openpyxl.Workbook(write_only=True)   # write_only = rápido/liviano para ~800k filas
    ws = wb.create_sheet('Sheet1')
    ws.append(HEADER)
    for r in rows:
        # r = [Region, Mercado, Droga, Clase, AñoMes, CodClase, CodProd, Producto, Unidades]
        u = r[8]
        ws.append([r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], int(u) if u is not None else 0])
    wb.save(out)
    print(f'OK: {len(rows)} filas -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
