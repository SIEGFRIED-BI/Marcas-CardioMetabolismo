# -*- coding: utf-8 -*-
"""shared/qlik/qlik-recetas-to-file.py

Convierte los JSON de extract-recetas.mjs en el xlsx que espera build-data.ps1
(parser $rxMatrix): 2 filas de header + datos.

Layout (Excel, 1-indexed):
  fila1: [_, _, 'Mes-Año', <mes>, <mes>, <mes>, <mes>, ...]   (mes en cols 4,6,8...)
  fila2: [Mercado (sin Mix), Droga, Marca, 'Cant. Recetas', 'Cant. Médicos', ...]
  fila3+: datos
     - por MERCADO: (mercado, 'Totales', '', recetas_mkt, medicos_mkt, ...)  <- familia total
       (medicos a nivel mercado = DISTINCT, del grano-mercado; NO la suma de marcas)
     - por (mercado, droga, marca): (mercado, droga, marca, recetas, medicos, ...)  <- detalle marca

El build deriva la familia del parentesis del mercado ("...(ISIS)" -> ISIS) y se
auto-filtra a las familias del tablero, asi que UN archivo (todos los mercados) sirve
para todas las lineas. Ver shared/qlik/POC-RECETAS.md.

Uso:
    py shared/qlik/qlik-recetas-to-file.py <brand.json> <output.xlsx>
    (el grano-mercado se lee de <brand>.mkt.json, que emite extract-recetas.mjs)
"""
from __future__ import annotations
import json, sys, os
from collections import defaultdict
import openpyxl

MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MI = {m: i for i, m in enumerate(MES)}

CORR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recetas-corrections.json')


def ymk(label):
    m, y = label.split('-'); return (int(y), MI.get(m, 0))


def load_corrections():
    """Lee recetas-corrections.json (mercados a mergear + labs a forzar). Si no
    existe o falla, devuelve reglas vacias (comportamiento identico al de antes)."""
    try:
        c = json.load(open(CORR_FILE, encoding='utf-8'))
        merges = {k: v for k, v in (c.get('marketMerges') or {}).items() if not k.startswith('_')}
        labs = {k: v for k, v in (c.get('labOverrides') or {}).items() if not k.startswith('_')}
        return merges, labs
    except Exception as e:
        print(f'WARN: correcciones no aplicadas ({e})', file=sys.stderr)
        return {}, {}


def apply_corrections(brand_rows, mkt_rows, merges, labs):
    """Aplica marketMerges (renombra el mercado -> se fusionan al agregar) y
    labOverrides (fuerza el token de lab de una marca). Devuelve (brand, mkt, n)."""
    n = 0
    if labs:
        for r in brand_rows:                       # [merc, dro, mar, ym, rec, med]
            mar = str(r[2] or '')
            toks = mar.split()
            if len(toks) >= 2:
                base = ' '.join(toks[:-1])
                if base in labs and toks[-1] != labs[base]:
                    r[2] = base + ' ' + labs[base]; n += 1
    if merges:
        for r in brand_rows:
            if r[0] in merges: r[0] = merges[r[0]]; n += 1
        for r in mkt_rows:                          # [merc, ym, rec, med]
            if r[0] in merges: r[0] = merges[r[0]]; n += 1
    return brand_rows, mkt_rows, n


def main():
    if len(sys.argv) < 3:
        print('uso: qlik-recetas-to-file.py <brand.json> <output.xlsx>', file=sys.stderr); return 2
    src, out = sys.argv[1], sys.argv[2]
    mkt_src = src[:-5] + '.mkt.json' if src.endswith('.json') else src + '.mkt.json'
    brand_rows = json.load(open(src, encoding='utf-8'))          # [merc, droga, marca, ym, rec, med]
    mkt_rows = json.load(open(mkt_src, encoding='utf-8'))        # [merc, ym, rec, med]

    merges, labs = load_corrections()
    brand_rows, mkt_rows, ncorr = apply_corrections(brand_rows, mkt_rows, merges, labs)
    if ncorr:
        print(f'correcciones aplicadas: {ncorr} filas ({len(merges)} merges, {len(labs)} labs)')

    months = sorted({r[3] for r in brand_rows} | {r[1] for r in mkt_rows}, key=ymk)

    # Mercado (sin Mix) devuelve NULL ("-"/"") para los pseudo-mercados MIX. Esas
    # recetas YA estan contadas en su mercado real (con nombre) -> el bucket "-" es
    # DUPLICADO y duplicaria la marca al agregar. Se EXCLUYE (validado ATB 2026-07:
    # sin esto ACANTEX/BACTRIM/etc daban 2x). Un mercado sin nombre no es trackeable
    # igual (el build filtra por el parentesis del mercado).
    def _mix_null(merc):
        return (not merc) or str(merc).strip() in ('-', '')
    # grano marca: (merc,droga,marca) -> mes -> (rec, med)
    brand = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for merc, dro, mar, ym, rec, med in brand_rows:
        if _mix_null(merc): continue
        c = brand[(merc, dro, mar)][ym]; c[0] += rec; c[1] += med
    # grano mercado (Totales): merc -> mes -> (rec, med DISTINCT)
    mkt = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for merc, ym, rec, med in mkt_rows:
        if _mix_null(merc): continue
        c = mkt[merc][ym]; c[0] += rec; c[1] += med

    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Sheet1'
    # fila1: fechas en cols 4,6,8...
    row1 = [None, None, 'Mes-Año']
    for m in months: row1 += [m, m]
    ws.append(row1)
    # fila2: nombres de columna
    row2 = ['Mercado (sin Mix)', 'Droga', 'Marca']
    for _ in months: row2 += ['Cant. Recetas', 'Cant. Médicos']
    ws.append(row2)
    # datos: por mercado -> Totales + marcas
    markets = sorted(set(mkt) | {k[0] for k in brand})
    for merc in markets:
        tot = mkt.get(merc, {})
        r = [merc, 'Totales', '']
        for m in months:
            v = tot.get(m, [0, 0]); r += [round(v[0]), round(v[1])]
        ws.append(r)
        bkeys = sorted(k for k in brand if k[0] == merc)
        for (mc, dro, mar) in bkeys:
            r = [mc, dro, mar]
            for m in months:
                v = brand[(mc, dro, mar)].get(m, [0, 0]); r += [round(v[0]), round(v[1])]
            ws.append(r)
    wb.save(out)
    print(f'OK: {ws.max_row - 2} filas datos, {len(months)} meses ({months[0]}..{months[-1]}), '
          f'{len(markets)} mercados -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
