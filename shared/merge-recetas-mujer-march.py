"""Merge mujer recetas Mar 2026 desde el pivot CloseUp.

Para cada familia mujer, busca el droga al que pertenece su SIE brand y
agrega/agrega los meses al rec_ms[fam] y rec_comp[fam][brand].monthly."""
from __future__ import annotations
import re, json
from pathlib import Path
from collections import defaultdict
import openpyxl

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'mujer' / 'index.html'
PIVOT = Path(r'C:\Users\camarinaro\OneDrive - Portalcorp\Documentos\Hub-Marcas-Inputs\linea-mujer\2026-04\fuentes-originales\Sin título - Tabla dinámica - 14 de mayo de 2026.xlsx')
TARGET_MONTH = 'Mar 2026'

# Familia mujer -> SIE brand keyword (debe matchear el nombre del brand SIE
# en el pivot dentro del market correcto). Buscaremos esa fila, identificamos
# la droga, y agregaremos a nivel DROGA.
FAM_SIE_BRAND = {
    'SIN ESTROGENO':    'ISIS FREE SIN EST SIE',
    'ALTA DOSIS':       'ISIS SIE',
    'BAJA DOSIS 21+7':  'ISIS MINI SIE',
    'BAJA DOSIS 24':    'ISIS MINI 24 SIE',
    'COMPLEX':          'SIDERBLUT COMPLEX SIE',
    'D3':               'TRIP D3 SIE',
    'DELTROX':          'DELTROX SIE',
    'BASE':             'CALCIO BASE SIE',
    'BASE D':           'CALCIO BASE D SIE',
}


def read_pivot(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        if not row: continue
        market = (str(row[0]) if row[0] else '').strip()
        droga = (str(row[1]) if row[1] else '').strip()
        marca = (str(row[2]) if row[2] else '').strip()
        rec = row[3] if len(row) > 3 else None
        try: rec = int(rec or 0)
        except (TypeError, ValueError): rec = 0
        rows.append((market, droga, marca, rec))
    wb.close()
    return rows


def find_droga_for_brand(rows, brand_kw):
    """Find the (market, droga) for an EXACT match of brand_kw, preferring
    rows with non-'-' market (specific market) and the largest droga total."""
    bu = brand_kw.upper().strip()
    candidates = []
    for m, d, marca, rec in rows:
        if not marca or d.upper() == 'TOTALES': continue
        if marca.upper() == bu:  # exact match
            candidates.append((m, d, rec))
    if not candidates: return None
    # Prefer market != '-', then largest droga rec
    candidates.sort(key=lambda x: (0 if x[0] == '-' else 1, x[2]), reverse=True)
    return (candidates[0][0], candidates[0][1])


def droga_total(rows, market, droga):
    """Sum of recetas across all brands in (market, droga). Use the row where
    droga is set and marca='Totales' if exists, else sum across brands."""
    mu = market.upper(); du = droga.upper()
    # Look for the Totales row first
    for m, d, marca, rec in rows:
        if m.upper() == mu and d.upper() == du and (not marca or marca.upper() == 'TOTALES'):
            return rec
    # Sum across brands
    total = 0
    for m, d, marca, rec in rows:
        if m.upper() == mu and d.upper() == du and marca and marca.upper() != 'TOTALES':
            total += rec
    return total


def brand_recetas(rows, market, droga, brand_kw):
    """Recetas of the brand matching brand_kw in (market, droga)."""
    bu = brand_kw.upper().strip()
    mu = market.upper(); du = droga.upper()
    for m, d, marca, rec in rows:
        if m.upper() == mu and d.upper() == du and bu in marca.upper():
            return rec
    return 0


def droga_competitors(rows, market, droga):
    """List all brands and their recetas in (market, droga)."""
    mu = market.upper(); du = droga.upper()
    out = []
    for m, d, marca, rec in rows:
        if m.upper() == mu and d.upper() == du and marca and marca.upper() != 'TOTALES':
            out.append((marca, rec))
    return out


def main():
    global PIVOT, TARGET_MONTH
    import argparse, datetime
    ap = argparse.ArgumentParser()
    ap.add_argument('--pivot', default=str(PIVOT))
    ap.add_argument('--month', default=None, help="e.g. 'Apr 2026'; si falta se deriva del header del pivot")
    args = ap.parse_args()
    PIVOT = Path(args.pivot)
    if not PIVOT.is_file():
        print(f'ERROR: pivot no existe: {PIVOT}'); return 1
    if args.month:
        TARGET_MONTH = args.month
    else:
        _MES = {1:'Jan',2:'Feb',3:'Mar',4:'Apr',5:'May',6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct',11:'Nov',12:'Dec'}
        _wb = openpyxl.load_workbook(PIVOT, read_only=True, data_only=True); _r1 = list(next(_wb.active.iter_rows(min_row=1, max_row=1, values_only=True))); _wb.close()
        for _v in _r1:
            if isinstance(_v, (datetime.datetime, datetime.date)):
                TARGET_MONTH = f'{_MES[_v.month]} {_v.year}'; break
    print(f'Mes objetivo: {TARGET_MONTH} | pivot: {PIVOT.name}')
    rows = read_pivot(PIVOT)
    print(f'Pivot rows: {len(rows)}')

    text = HTML.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D = (\{)', text)
    ob = text.index('{', m.start()+8)
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    prefix = text[:ob]; suffix = text[ob+end:]

    rec_ms = D.setdefault('rec_ms', {})
    rec_comp = D.setdefault('rec_comp', {})
    recetas_top = D.setdefault('recetas', {})

    for fam, sie_kw in FAM_SIE_BRAND.items():
        loc = find_droga_for_brand(rows, sie_kw)
        if not loc:
            print(f'  {fam}: NO SE ENCUENTRA brand SIE "{sie_kw}"')
            continue
        market, droga = loc
        sie_rec = brand_recetas(rows, market, droga, sie_kw)

        rms = rec_ms.setdefault(fam, {})
        rms.setdefault('sie', {})[TARGET_MONTH] = sie_rec
        # Limpiar mkt[Mar 2026] si existía de runs previos
        if 'mkt' in rms and TARGET_MONTH in rms['mkt']:
            del rms['mkt'][TARGET_MONTH]
        # Approximación de mkt: mantener la relación Feb 2026 (sie/ms*100).
        # Si no hay Feb ms, usar droga_total como mejor estimación.
        feb_sie = rms.get('sie', {}).get('Feb 2026')
        feb_ms = rms.get('ms', {}).get('Feb 2026')
        # ms: usar el MS% de Feb 2026 como referencia (asume MS% estable mes-a-mes).
        # NO setear rec_ms.mkt[Mar 2026] (igual que Feb 2026 que tenía None) para
        # mantener la consistencia con la estructura existente.
        if feb_sie and feb_ms:
            rms.setdefault('ms', {})[TARGET_MONTH] = feb_ms
            print(f'  {fam}: sie={sie_rec}, ms={feb_ms}% (carry from Feb)')
        else:
            mkt_total = droga_total(rows, market, droga)
            ms_pct = round(sie_rec/mkt_total*100, 1) if mkt_total > 0 else 0
            rms.setdefault('ms', {})[TARGET_MONTH] = ms_pct
            print(f'  {fam}: sie={sie_rec}, ms={ms_pct}% (computed from droga)')

        # Update D.recetas[fam][Mar 2026] (este es el que usa el CHART de Recetas)
        rec_fam = recetas_top.setdefault(fam, {})
        rec_fam[TARGET_MONTH] = {'recetas': sie_rec, 'medicos': 0}

        # rec_comp: update existing brands for this fam (match by primer token)
        fam_comp = rec_comp.setdefault(fam, {})
        comp_brands = droga_competitors(rows, market, droga)

        def first_word(s):
            # Strip SIE / paren suffix and take the first token
            cleaned = re.sub(r'\s*\([^)]+\)\s*$', '', s).strip()
            cleaned = re.sub(r'\s+SIE\s*$', '', cleaned, flags=re.I).strip()
            return cleaned.split()[0].upper() if cleaned else ''

        comp_updated = 0
        for brand_name, rec in comp_brands:
            bn_first = first_word(brand_name)
            if not bn_first: continue
            # Find existing rec_comp key whose first word matches
            matched = None
            for ek in fam_comp.keys():
                if first_word(ek) == bn_first:
                    matched = ek; break
            if matched:
                b_obj = fam_comp[matched]
                if isinstance(b_obj, dict):
                    b_obj.setdefault('monthly', {})[TARGET_MONTH] = rec
                    comp_updated += 1
        if comp_updated > 0:
            print(f'    rec_comp: {comp_updated} brands updated')

    HTML.write_text(prefix + json.dumps(D, ensure_ascii=False) + suffix,
                    encoding='utf-8', newline='')
    print(f'\nMujer rec_ms / rec_comp actualizado para {TARGET_MONTH}')
    return 0


if __name__ == '__main__':
    main()
