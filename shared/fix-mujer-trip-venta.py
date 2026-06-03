# -*- coding: utf-8 -*-
"""Corrige la VENTA INTERNA de los productos TRIP en linea mujer.

PROBLEMA: en la Planilla de Ventas SAP, TODOS los TRIP comparten
Gran Familia = Familia = Producto = 'TRIP'; la variante (+45, D3, D3 Plus,
Magnesio) SOLO aparece en la columna 'Presentacion'. El merge general
(merge-ventas-internas.py) agrupa por Familia (col1), asi que NO puede
separarlos: 'D3' se tragaba TODO TRIP (~41k) y '45'/'D3 PLUS'/'MAGNESIO'
quedaban en 0 (bug reportado: "TRIP 45 esta mal, si tiene datos de venta").

SOLUCION: este corrector lee la planilla, clasifica las filas de TRIP por
PRESENTACION (col3) y setea budget['45'|'D3'|'D3 PLUS'|'MAGNESIO'].real en
mujer/index.html. Solo toca esas 4 keys; preserva el estimado (budget[]) y
todo el resto de const D (reemplazo DIRIGIDO del objeto budget, sin
reformatear el archivo).

Mapeo Presentacion -> budget key:
  'TRIP +45 ...'          -> 45
  'TRIP Magnesio ...'     -> MAGNESIO
  'TRIP D3 Plus ...'      -> D3 PLUS
  'TRIP D3 ...' (resto)   -> D3   (incluye filas '/TRIP D3 ... - CR' = creditos, netos)
CALCITOL D3 / CALCITRIOL (Gran Familia 'Otros') NO se incluyen: el segmento
'D3' del tablero es TRIP D3.

IMPORTANTE: el merge tiene esas 4 keys con mapeo VACIO (no toca TRIP), asi que
los valores de este corrector PERSISTEN entre merges. Re-correr SOLO cuando
llegue una planilla nueva:
  py shared/fix-mujer-trip-venta.py "<planilla.xlsx>" [--cutoff 2026-05]
"""
from __future__ import annotations
import sys, re, json, argparse
from collections import defaultdict
from pathlib import Path
import openpyxl

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'mujer' / 'index.html'
DEFAULT_FILE = r'C:\Users\camarinaro\OneDrive - Portalcorp\Documentos\Hub-Marcas-Inputs\Planilla de Ventas - 2 de junio de 2026.xlsx'
TRIP_KEYS = ['45', 'D3', 'D3 PLUS', 'MAGNESIO']
MESES = {'ENE': 0, 'FEB': 1, 'MAR': 2, 'ABR': 3, 'MAY': 4, 'JUN': 5,
         'JUL': 6, 'AGO': 7, 'SEP': 8, 'OCT': 9, 'NOV': 10, 'DIC': 11}
MES_ABBR = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def classify(pres):
    pu = (pres or '').upper()
    if 'TRIP' not in pu:
        return None
    if '+45' in pu or re.search(r'\b45\b', pu):
        return '45'
    if 'MAGNESIO' in pu:
        return 'MAGNESIO'
    if 'D3 PLUS' in pu:
        return 'D3 PLUS'
    if 'D3' in pu:
        return 'D3'
    return None


def parse_planilla(path, cutoff):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        rows.append(list(row))
        if i > 6000:
            break
    wb.close()
    hdr = rows[0]
    # col -> (year, month_idx) para columnas tipo 'Mes-YYYY'
    colmap = {}
    for c, h in enumerate(hdr):
        m = re.match(r'([A-Za-z]{3})[\-\s/](\d{4})', str(h or '').strip())
        if m:
            mon = MESES.get(m.group(1)[:3].upper())
            if mon is not None:
                colmap[c] = (int(m.group(2)), mon)
    data = {k: defaultdict(int) for k in TRIP_KEYS}
    seen_pres = defaultdict(set)
    for r in rows[1:]:
        if str(r[0] if len(r) else '').strip().upper() != 'TRIP':
            continue
        pres = r[3] if len(r) > 3 else ''
        key = classify(pres)
        if not key:
            continue
        seen_pres[key].add(str(pres).strip())
        for c, ym in colmap.items():
            if cutoff and ym > cutoff:
                continue
            v = r[c] if c < len(r) else None
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                data[key][ym] += v
    return data, seen_pres


def load_D(text):
    m = re.search(r'const D\s*=\s*\{', text)
    ob = m.end() - 1
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return D, ob, ob + end


def apply(D, data):
    bud = D['budget']
    changes = []
    for key in TRIP_KEYS:
        if key not in bud:
            print('  [aviso] budget no tiene key %r, se omite' % key)
            continue
        for (yr, idx), v in sorted(data[key].items()):
            yk = str(yr)
            yo = bud.setdefault(key, {}).setdefault(yk, {})
            real = list(yo.get('real') or [])
            real = (real + [0] * 12)[:12]
            old = real[idx]
            real[idx] = int(round(v))
            yo['real'] = real
            yo.setdefault('budget', [0] * 12)
            if old != real[idx]:
                changes.append((key, yk, MES_ABBR[idx], old, real[idx]))
    return changes


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?', default=DEFAULT_FILE)
    ap.add_argument('--cutoff', default='2026-05', help="Ultimo mes cerrado YYYY-MM (default 2026-05)")
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not Path(args.file).is_file():
        print('ERROR: no existe la planilla:', args.file)
        return 1
    cutoff = None
    if args.cutoff:
        mm = re.match(r'(\d{4})-(\d{2})', args.cutoff)
        cutoff = (int(mm.group(1)), int(mm.group(2)) - 1)

    data, seen = parse_planilla(args.file, cutoff)
    print('Presentaciones TRIP encontradas por key:')
    for k in TRIP_KEYS:
        print('  %-9s <- %s' % (k, sorted(seen.get(k, []))))

    text = open(HTML, 'r', encoding='utf-8', newline='').read()
    D, ob, oend = load_D(text)
    bud = D['budget']

    # localizar el substring EXACTO del objeto budget (formato del archivo) para
    # reemplazo dirigido (no reformatea el resto de const D, incl. prec_comp).
    old_default = json.dumps(bud, ensure_ascii=False)
    old_compact = json.dumps(bud, ensure_ascii=False, separators=(',', ':'))
    if old_default in text:
        oldstr, seps = old_default, None
    elif old_compact in text:
        oldstr, seps = old_compact, (',', ':')
    else:
        oldstr, seps = None, None

    changes = apply(D, data)
    print('\nCambios en budget.real (%d celdas):' % len(changes))
    for key, yr, mes, old, new in changes:
        print('  %-9s %s %s: %s -> %s' % (key, yr, mes, old, new))

    if args.dry_run:
        print('\n(dry-run, no se escribe)')
        return 0

    if oldstr is not None:
        newstr = json.dumps(bud, ensure_ascii=False) if seps is None else json.dumps(bud, ensure_ascii=False, separators=seps)
        text2 = text.replace(oldstr, newstr, 1)
        mode = 'dirigido (solo objeto budget)'
    else:
        # fallback: re-serializa todo D (default). Solo si no se pudo ubicar budget.
        text2 = text[:ob] + json.dumps(D, ensure_ascii=False) + text[oend:]
        mode = 'FALLBACK: re-serializo todo const D'

    if text2 == text:
        print('\nSin cambios.')
    else:
        open(HTML, 'w', encoding='utf-8', newline='').write(text2)
    print('\nEscrito (%s). Keys TRIP corregidas: %s' % (mode, TRIP_KEYS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
