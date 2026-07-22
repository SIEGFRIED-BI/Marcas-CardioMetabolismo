# -*- coding: utf-8 -*-
"""Redefine el MERCADO de TETRALGIN y TETRALGIN NOVO (antimigranosos, N02C + algunos
N02B) en OTC/data.js mol_perf, desde un export IQVIA curado por MKT
('mercado tetralgin*.xlsx' en hubRoot).

Por que: el mercado auto-derivado de Tetralgin por molecula era angosto/erroneo
(Tetralgin = CAFFEINE_CHLORPHENAMINE, molecula casi unica) e incluia FLOCUR RAPID
pero no triptanes, TAFIROL MIGRA ni los splits de MIGRAL. Este archivo es la
definicion autoritativa del mercado antimigranoso: se usa para redefinir SOLO los
COMPETIDORES (todo lo NO-Siegfried del archivo).

IMPORTANTE - consistencia de fuente (LEMA): las unidades SIE (TETRALGIN / TETRALGIN
NOVO) NO se tocan: se conservan las del mol_perf actual (cierre oficial AR_PM), de
las que dependen venta, recetas, Total y brandKpis. El archivo trae los SIE con un
rounding levemente distinto (drift de pocas unidades) -> si se usaran, audit-full
falla. Por eso: SIE = mol_perf actual (oficial); competidores = archivo. TETRALGIN
APC del archivo se descarta (SIE discontinuado, 0 en 2026, ademas seria SIE
file-sourced). Solo cambia el DENOMINADOR (competidores).

TETRALGIN y TETRALGIN NOVO COMPARTEN el mismo mercado -> ambas familias reciben la
MISMA lista de productos. La atribucion de unidades SIE por familia la hace el
render via D.budIqviaMap (TETRALGIN->['TETRALGIN (SIE)'], NOVO->['TETRALGIN NOVO
(SIE)']), asi que NO hay que tocar los flags: alcanza con conservar los nombres
'BRAND (COD)' exactos.

Columnas por HEADER (IQVIA cambia el orden entre entregas): Manufacturer, Product,
y las mensuales 'M/D/YYYY\\nUnits'. Ventana = la del mol_perf actual de TETRALGIN
(los meses del producto SIE), para que Tetralgin quede alineado con el resto de OTC.

Luego correr la cascada estandar: recompute-mol-perf-aggregates + build-kpis +
sync-kpistrip + fix-brandkpis-market-total + fix-brandkpis-ie-vs-market +
fix-brandkpis-rec. Idempotente. Skip si falta openpyxl/archivo.

Uso: py shared/rebuild-otc-tetralgin-from-iqvia.py
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path
from collections import defaultdict

SHARED = Path(__file__).resolve().parent
REPO = SHARED.parent
sys.path.insert(0, str(SHARED))

SRC_GLOB = 'mercado tetralgin*.xlsx'
FAMS = ['TETRALGIN', 'TETRALGIN NOVO']  # ambas comparten el mercado
MES_NUM = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
           7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
MES_SET = {v.lower(): k for k, v in MES_NUM.items()}


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


def parse_month(h):
    """'7/1/2021\\nUnits' -> 'Jul 2021'; 'Units\\nJul 2021' -> 'Jul 2021'. None si no es mes."""
    s = str(h or '').replace('Units', '').replace('\n', ' ').strip()
    s = re.sub(r'\s+', ' ', s)
    # formato M/D/YYYY o M-D-YYYY
    m = re.match(r'^(\d{1,2})[/-]\d{1,2}[/-](\d{4})$', s)
    if m:
        mo = int(m.group(1))
        if 1 <= mo <= 12:
            return f'{MES_NUM[mo]} {m.group(2)}'
    # formato 'Mon YYYY'
    m = re.match(r'^([A-Za-z]{3}) (\d{4})$', s)
    if m and m.group(1).lower() in MES_SET:
        return f'{MES_NUM[MES_SET[m.group(1).lower()]]} {m.group(2)}'
    return None


def detect_cols(hdr):
    manuf_col = prod_col = None
    month_cols = {}  # 'Mon YYYY' -> idx
    for i, h in enumerate(hdr):
        low = str(h or '').strip().lower()
        if low == 'manufacturer':
            manuf_col = i
        elif low == 'product':          # NO 'Product Type'
            prod_col = i
        mk = parse_month(h)
        if mk:
            month_cols[mk] = i
    return manuf_col, prod_col, month_cols


def read_market(path, window):
    """Devuelve [product_dict,...] con monthly_vals limitado a `window` (todo el archivo = mercado)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = rows[0]
    manuf_col, prod_col, month_cols = detect_cols(hdr)
    if manuf_col is None or prod_col is None:
        raise ValueError(f'no encontre columnas Manufacturer/Product en el header: {hdr[:9]}')
    win = [m for m in window if m in month_cols]
    if not win:
        raise ValueError('la ventana no interseca con los meses del archivo')

    agg = defaultdict(lambda: defaultdict(float))  # prod -> mes -> units
    manuf_of = {}
    for r in rows[1:]:
        prod = str(r[prod_col] or '').strip()
        if not prod:
            continue
        manuf_of[prod] = str(r[manuf_col] or '').strip()
        for mes in win:
            v = r[month_cols[mes]]
            try:
                agg[prod][mes] += float(v or 0)
            except (TypeError, ValueError):
                pass

    prods = []
    for prod, series in agg.items():
        monthly = {m: int(round(series.get(m, 0))) for m in win}
        if sum(monthly.values()) == 0:      # descartar productos sin datos en la ventana
            continue
        manuf = manuf_of[prod]
        prods.append({
            'prod': prod, 'manuf': manuf, 'is_sie': 'SIEG' in manuf.upper(),
            'monthly_vals': monthly,
            'ytd': {}, 'mat': {}, 'quarterly_vals': {},
            'ms_monthly': {}, 'ms_ytd': {}, 'ms_mat': {}, 'ms_quarterly': {},
        })
    last = win[-1]
    prods.sort(key=lambda p: (0 if p['is_sie'] else 1, -(p['monthly_vals'].get(last, 0))))
    return prods, win


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

    # ventana = monthly_vals del producto SIE de TETRALGIN (Feb 2024..Jun 2026)
    sie_prod = next((pp for pp in mol.get('TETRALGIN', {}).get('products', []) if pp.get('is_sie')), None)
    window = list((sie_prod or {}).get('monthly_vals', {}).keys())
    if not window:
        print('  (skip) no pude determinar la ventana de meses'); return 0

    file_prods, win = read_market(src, window)
    if not file_prods:
        print('  (skip) 0 productos leidos del archivo'); return 0

    # SIE = mol_perf actual (cierre oficial AR_PM), NO el del archivo (evita drift).
    # Se toma de TETRALGIN (la familia canonica con ambos productos SIE marcados).
    existing_sie = [pp for pp in mol.get('TETRALGIN', {}).get('products', []) if pp.get('is_sie')]
    if not existing_sie:
        print('  (skip) no encontre productos SIE en mol_perf TETRALGIN'); return 0
    # Competidores = todo lo NO-Siegfried del archivo (redefine el denominador).
    competitors = [p for p in file_prods if not p['is_sie']]
    dropped_sie = [p['prod'] for p in file_prods if p['is_sie']]

    last = win[-1]
    def newlist():
        # deep-copy para que cada familia tenga objetos independientes
        return json.loads(json.dumps(existing_sie)) + json.loads(json.dumps(competitors))
    sie_names = [pp['prod'] for pp in existing_sie]
    mkt_last = (sum(pp['monthly_vals'].get(last, 0) for pp in existing_sie)
                + sum(pp['monthly_vals'].get(last, 0) for pp in competitors))
    for fam in FAMS:
        if fam not in mol:
            print(f'  (warn) {fam} no esta en mol_perf; skip'); continue
        mol[fam]['products'] = newlist()
        print(f'  {fam}: {len(existing_sie)} SIE (oficial) + {len(competitors)} competidores, '
              f'ventana {win[0]}..{win[-1]}, mkt {last}={mkt_last}')
    print(f'  SIE conservados del cierre: {", ".join(sie_names)}')
    if dropped_sie:
        print(f'  SIE del archivo descartados (se usa el oficial): {", ".join(dropped_sie)}')

    p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                 encoding='utf-8', newline='')
    print('  OTC/data.js: mercado TETRALGIN / TETRALGIN NOVO redefinido desde', src.name)
    print('  -> correr recompute-mol-perf-aggregates + build-kpis + sync-kpistrip + fix-brandkpis-*')
    return 0


if __name__ == '__main__':
    sys.exit(main())
