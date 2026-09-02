# -*- coding: utf-8 -*-
"""Convierte el JSON de rofina-extract-convenios.mjs en el xlsx que ya consume
shared/build-canales-quarterly.py.

Replica el layout del export manual de Qlik ('Convenios vs mostrador - <fecha> <N>
trimestre <AAAA>.xlsx'): 4 columnas de etiqueta + las 12 medidas, y las filas de
familia marcadas con Producto == 'Totales' (que es como el builder las reconoce en el
formato nuevo).

Si se pasan dos JSON, exige que coincidan antes de escribir: la extraccion se hace por
dos rutas (mes final + rollback, y los 3 meses sueltos) y si no dan igual, algo del
universo no es lo que creemos y no se publica.

Uso:
  py shared/qlik/rofina-json-to-convenios-xlsx.py <in.json> <salida.xlsx> [--verificar-con <otro.json>]
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import openpyxl

COLS = ['Laboratorio', 'Familia', 'Producto', 'Producto_key',
        'Unidades facturadas', 'Convenios', '$ neto facturado', 'Consumo uni',
        'Consumo PVP', 'Aporte neto', '$ netos', '% convenio UNI', '% mostrador UNI',
        '% dto com', '% dto conv', '% dto total']
MEDIDAS = COLS[4:]


def cargar(p):
    d = json.load(open(p, encoding='utf-8'))
    filas = {}
    for row in d['rows']:
        fam = (row.get('Familia') or '').strip()
        if not fam or fam == '-':
            continue
        filas[(row.get('Laboratorio') or '').strip(), fam] = {
            v['label']: v['num'] for v in row['valores']
        }
    return d, filas


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    otro = None
    if '--verificar-con' in sys.argv:
        otro = Path(sys.argv[sys.argv.index('--verificar-con') + 1])
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    meta, filas = cargar(src)
    print(f'fuente : {src.name}')
    print(f'         seleccion={meta["seleccion"]}  extraido={meta["extraidoEl"][:19]}')
    print(f'         {len(filas)} filas (Laboratorio, Familia)')

    if otro:
        meta2, filas2 = cargar(otro)
        print(f'control: {otro.name}  seleccion={meta2["seleccion"]}')
        if set(filas) != set(filas2):
            solo1 = sorted(set(filas) - set(filas2))[:5]
            solo2 = sorted(set(filas2) - set(filas))[:5]
            print(f'ABORTADO: las dos rutas no traen las mismas filas. '
                  f'solo en A: {solo1} | solo en B: {solo2}')
            return 2
        difs = []
        for k in filas:
            for m in MEDIDAS:
                a, b = filas[k].get(m), filas2[k].get(m)
                if a is None and b is None:
                    continue
                if a is None or b is None or abs(a - b) > max(abs(a) * 1e-9, 1e-9):
                    difs.append(f'{k[1]}/{m}: {a} vs {b}')
        if difs:
            print(f'ABORTADO: {len(difs)} celda(s) difieren entre las dos rutas. '
                  f'Primeras: {difs[:4]}')
            return 2
        print(f'control: OK, las dos rutas coinciden en {len(filas) * len(MEDIDAS)} celdas')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sheet1'
    ws.append(COLS)
    n_fam = 0
    for (lab, fam) in sorted(filas):
        v = filas[(lab, fam)]
        # 'Totales' en Producto = fila de nivel familia (asi la lee el builder)
        ws.append([lab, fam, 'Totales', ''] + [v.get(m) for m in MEDIDAS])
        n_fam += 1
    wb.save(out)
    print(f'OK: {n_fam} filas de familia -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
