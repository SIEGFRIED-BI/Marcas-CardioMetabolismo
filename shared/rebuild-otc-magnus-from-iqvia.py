# -*- coding: utf-8 -*-
"""Reconstruye el MERCADO completo de MAGNUS (sildenafil) y MAGNUS 36 (tadalafil)
en OTC/data.js mol_perf, desde un export IQVIA AR_PM filtrado a esos 2 mercados
('Mercado-MAGNUS-sildenafil-tadalafil.xlsx' en hubRoot).

Por que: el master AR_PM general solo traia 3 marcas de sildenafil (MAGNUS+VIMAX+
ALMAXIMO) -> mercado MAGNUS incompleto, MS% sobreestimado. Este export trae las 26
marcas de sildenafil y 27 de tadalafil (mismo panel nacional, a May-2026, nivel marca,
nombres 'BRAND (CODIGO)' con SIEGFRIED como 'MAGNUS (SIE)'/'MAGNUS 36 (SIE)').

Reemplaza mol_perf['MAGNUS'].products y ['MAGNUS 36'].products con monthly_vals de
todas las marcas (ventana = la que ya usa el mol_perf de OTC). Luego hay que correr
recompute-mol-perf-aggregates + build-kpis + sync-kpistrip + fix-brandkpis-* para
propagar (cascada estandar). Idempotente. Skip si falta openpyxl/archivo.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path
from collections import defaultdict

SHARED = Path(__file__).resolve().parent
REPO = SHARED.parent
sys.path.insert(0, str(SHARED))

SRC_GLOB = 'Mercado-MAGNUS-sildenafil*.xlsx'
MOL_TO_FAM = {'SILDENAFIL': 'MAGNUS', 'TADALAFIL': 'MAGNUS 36'}
COL_MANUF, COL_PROD, COL_MOL = 0, 1, 4


def find_src():
    try:
        import manifest
        hub = manifest.hub_root()
    except Exception:
        hub = None
    for base in ([hub] if hub else []) + [REPO.parent,
            Path.home() / 'OneDrive - Portalcorp' / 'Documentos' / 'Hub-Marcas-Inputs']:
        if base and base.is_dir():
            c = sorted(base.glob(SRC_GLOB))
            if c:
                return c[0]
    return None


def read_markets(path, window):
    """Devuelve {fam: [product_dict,...]} con monthly_vals limitado a `window`."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = rows[0]
    # columnas mensuales puras: 'Units\n<Mon> <YYYY>' (sin MAT/YTD/to)
    month_cols = {}
    for i, h in enumerate(hdr):
        clean = re.sub(r'\s+', ' ', str(h or '').replace('Units', '').replace('\n', ' ')).strip()
        if re.fullmatch(r'[A-Z][a-z]{2} \d{4}', clean):
            month_cols[clean] = i
    win = [m for m in window if m in month_cols]

    # agregar packs -> marca (Product). Guardar manuf + molecula.
    agg = defaultdict(lambda: defaultdict(float))  # prod -> mes -> units
    meta = {}  # prod -> (manuf, molecule)
    for r in rows[1:]:
        prod = str(r[COL_PROD] or '').strip()
        mol = str(r[COL_MOL] or '').strip().upper()
        if not prod or mol not in MOL_TO_FAM:
            continue
        meta[prod] = (str(r[COL_MANUF] or '').strip(), mol)
        for mes in win:
            v = r[month_cols[mes]]
            try:
                agg[prod][mes] += float(v or 0)
            except (TypeError, ValueError):
                pass

    fams = {f: [] for f in MOL_TO_FAM.values()}
    for prod, series in agg.items():
        manuf, mol = meta[prod]
        fam = MOL_TO_FAM[mol]
        is_sie = 'SIEG' in manuf.upper()
        monthly = {m: int(round(series.get(m, 0))) for m in win}
        fams[fam].append({
            'prod': prod, 'manuf': manuf, 'is_sie': is_sie,
            'monthly_vals': monthly,
            'ytd': {}, 'mat': {}, 'quarterly_vals': {},
            'ms_monthly': {}, 'ms_ytd': {}, 'ms_mat': {}, 'ms_quarterly': {},
        })
    # orden: SIE primero, luego por unidades del ultimo mes desc
    last = win[-1] if win else None
    for fam in fams:
        fams[fam].sort(key=lambda p: (0 if p['is_sie'] else 1,
                                      -(p['monthly_vals'].get(last, 0) if last else 0)))
    return fams, win


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    src = find_src()
    if src is None:
        print('  (skip) no se encontro', SRC_GLOB, 'en hubRoot'); return 0
    try:
        import openpyxl  # noqa
    except ImportError:
        print('  (skip) openpyxl no disponible'); return 0

    p = REPO / 'OTC' / 'data.js'
    t = p.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    mol = D.get('mol_perf', {})

    # ventana = monthly_vals del producto SIE de MAGNUS (Feb 2024..May 2026)
    sie_prod = next((pp for pp in mol.get('MAGNUS', {}).get('products', []) if pp.get('is_sie')), None)
    window = list((sie_prod or {}).get('monthly_vals', {}).keys())
    if not window:
        print('  (skip) no pude determinar la ventana de meses'); return 0

    fams, win = read_markets(src, window)

    # El archivo curado de MKT define el mercado y abajo se REEMPLAZAN los products
    # enteros. Si ese archivo esta mas atrasado que lo ya publicado, el reemplazo BORRA
    # meses -- y ningun gate lo ve: verify-history-preserved mira el rango de la LINEA
    # (OTC conserva su ultimo mes por las otras familias) y las sumas internas cierran
    # perfecto sobre el dato truncado. Paso en Jul-2026: el xlsx llegaba a May-2026 y
    # MAGNUS / MAGNUS 36 quedaron un mes ATRAS de produccion (sin Jun-2026).
    # No decidimos por el operador: paramos y que elija.
    perdidos = [m for m in window if m not in win]
    if perdidos:
        print()
        print(f'  [!] "{Path(src).name}" no cubre {len(perdidos)} mes(es) que el build SI tiene:')
        print(f'      {", ".join(perdidos)}')
        print('      HIBRIDO: se aplica la curacion de MKT en los meses que cubre y se')
        print('      PRESERVAN esos meses tal como vinieron del master. Antes se')
        print('      reemplazaban los products enteros y esos meses se BORRABAN en')
        print('      silencio (Jul-2026: MAGNUS quedo un mes atras de produccion).')
        print('      Medido: el master reproduce la curacion con -0,33% (MAGNUS) /')
        print('      -1,91% (MAGNUS 36); el mes de empalme quedo a -0,02% del publicado.')

    for fam, prods in fams.items():
        if fam not in mol or not prods:
            print(f'  (warn) {fam}: {len(prods)} prods, fam_en_molperf={fam in mol}'); continue
        # Preservar los meses que el archivo curado no cubre (por producto).
        # OJO: no usar `p` como variable de loop, que es el Path del data.js.
        previos = {str(pp.get('prod')): (pp.get('monthly_vals') or {})
                   for pp in mol[fam].get('products', [])}
        if perdidos:
            for pp in prods:
                antes = previos.get(str(pp.get('prod')), {})
                for mk in perdidos:
                    if mk in antes:
                        pp.setdefault('monthly_vals', {})[mk] = antes[mk]
        mol[fam]['products'] = prods
        extra = f' + {len(perdidos)} mes(es) preservados del master' if perdidos else ''
        print(f'  {fam}: {len(prods)} marcas (SIE incl.), ventana {win[0]}..{win[-1]}{extra}')

    p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                 encoding='utf-8', newline='')
    print('  OTC/data.js: mol_perf MAGNUS / MAGNUS 36 reconstruidos. '
          'Correr recompute-mol-perf-aggregates + build-kpis + sync-kpistrip + fix-brandkpis-*.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
