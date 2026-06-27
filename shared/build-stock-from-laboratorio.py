# -*- coding: utf-8 -*-
"""Actualiza Stock + Cobertura (D.stock, D.stock_alerts, D.stock_pres,
D.coverage_labels) desde la planilla 'Laboratorio - Familia - Producto*.xlsx'
del hub (la fuente que ya usa build-data para stock).

Estructura de la planilla: col0=Laboratorio, col1=Familia, col2=Producto,
col3-6=Totales(Stock/Ventas/Fact/Dias), luego grupos de 4 por mes
(Stock final, Ventas, Facturacion, Dias de Stock) con el mes en la fila 0.

  D.stock[familia]       = {mes_EN: {stock,ventas,facturacion,dias}}  (todos los meses)
  D.stock_alerts[familia]= ultimos 12m: {ventas[12],dias[12],statuses[12],
                            alert_indices,worst_status,n_alerts,familia}
  D.stock_pres[producto] = igual, por presentacion
  D.coverage_labels      = etiquetas ES cortas de los ultimos 12 meses

SOLO familias/presentaciones que hoy estan en cada tablero (no agrega extra).
Status (igual a build-data.Classify-StockStatus): <=0 quiebre, <7 critico, <14 bajo,
<20 alerta, else ok; None -> nd. Idempotente, --check. Skip si falta openpyxl/archivo.
"""
from __future__ import annotations
import re, json, sys, datetime
from pathlib import Path

SHARED = Path(__file__).resolve().parent
REPO = SHARED.parent
sys.path.insert(0, str(SHARED))

LINES = ['cardio/data.js','ATB/data.js','OTC/data.js','respiratorio/data.js',
         'mujer/data.js','SNC/data.js','dermatologia/data.js']
EN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
ALERT_LEVELS = ('quiebre', 'critico', 'bajo', 'alerta')
WORST_ORDER = ('quiebre', 'critico', 'bajo', 'alerta', 'ok', 'nd')


def classify(days):
    if days is None: return 'nd'
    if days <= 0: return 'quiebre'
    if days < 7: return 'critico'
    if days < 14: return 'bajo'
    if days < 20: return 'alerta'
    return 'ok'


def worst(statuses):
    for s in WORST_ORDER:
        if s in statuses: return s
    return 'nd'


def find_source():
    try:
        import manifest
        hub = manifest.hub_root()
    except Exception:
        hub = None
    cands = []
    for base in ([hub] if hub else []) + [REPO.parent,
            Path.home() / 'OneDrive - Portalcorp' / 'Documentos' / 'Hub-Marcas-Inputs']:
        if base and base.is_dir():
            cands += list(base.glob('Laboratorio - Familia - Producto*.xlsx'))
    # mas reciente por fecha de modificacion
    cands = [c for c in cands if c.is_file()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def read_laboratorio(path):
    """Devuelve (months_en[], fam_data{fam:{mes:{...}}}, pres_data{prod:{mes:{...}}})."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    row0, row1 = rows[0], rows[1]
    # grupos de 4 desde la col donde row1=='Stock final' por 2da vez (la 1a es Totales)
    month_cols = []  # (idx_stock, mes_en)
    for i, h in enumerate(row0):
        if isinstance(h, datetime.datetime):
            mes_en = f'{EN[h.month-1]} {h.year}'
            month_cols.append((i, mes_en))
    # dedup por mes conservando primer idx de cada grupo (cada mes ocupa 4 cols)
    seen = set(); groups = []
    for idx, mes in month_cols:
        if mes in seen: continue
        seen.add(mes); groups.append((idx, mes))
    months_en = [m for _, m in groups]

    def num(v):
        try: return int(round(float(v)))
        except (TypeError, ValueError): return None

    fam_data, pres_data = {}, {}
    for r in rows[2:]:
        fam = str(r[1] or '').strip()
        prod = str(r[2] or '').strip()
        if not fam or fam.lower() in ('totales', 'total'):
            continue
        series = {}
        for idx, mes in groups:
            stock = num(r[idx]); ventas = num(r[idx+1]); fact = num(r[idx+2]); dias = num(r[idx+3])
            # stock/ventas/fact a >=0 (SAP a veces deja stock negativo por ajustes;
            # el quiebre se refleja igual via 'dias' -> status). dias se conserva.
            series[mes] = {'stock': max(0, stock or 0), 'ventas': max(0, ventas or 0),
                           'facturacion': max(0, fact or 0), 'dias': dias if dias is not None else 0}
        if prod.lower() == 'totales':
            fam_data[fam] = series          # fila familia
        elif prod:
            pres_data[prod] = series        # fila presentacion
    return months_en, fam_data, pres_data


def alerts_from_series(series, months12, label):
    ventas = [series.get(m, {}).get('ventas', 0) for m in months12]
    dias = [series.get(m, {}).get('dias', 0) for m in months12]
    statuses = [classify(d) for d in dias]
    ai = [i for i, s in enumerate(statuses) if s in ALERT_LEVELS]
    out = {'ventas': ventas, 'dias': dias, 'statuses': statuses,
           'alert_indices': ai, 'worst_status': worst(statuses), 'n_alerts': len(ai)}
    return out


def patch(check_only=False):
    src = find_source()
    if src is None:
        print('  (skip) no se encontro Laboratorio - Familia - Producto*.xlsx'); return 0
    try:
        months_en, fam_data, pres_data = read_laboratorio(src)
    except ImportError:
        print('  (skip) openpyxl no disponible'); return 0
    if not fam_data:
        print('  (skip) sin filas de familia en la planilla'); return 0
    months12 = months_en[-12:]
    cov_labels = [f'{ES[EN.index(m.split()[0])]} {m.split()[1][2:]}' for m in months12]
    print(f'  fuente: {src.name}  meses={len(months_en)} (..{months_en[-1]})')

    total_changed = 0
    for rel in LINES:
        p = REPO / rel
        t = p.read_text(encoding='utf-8-sig')
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
        if not m: continue
        ob = t.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(t[ob:])
        cur_fams = set(D.get('stock', {}))
        cur_pres = set(D.get('stock_pres', {}))
        if not cur_fams and not cur_pres:
            continue
        new_stock, new_alerts, new_pres = {}, {}, {}
        for fam in cur_fams:
            if fam in fam_data:
                new_stock[fam] = fam_data[fam]
                a = alerts_from_series(fam_data[fam], months12, fam); a['familia'] = fam
                new_alerts[fam] = a
            else:  # conservar lo que habia si la planilla no lo trae
                new_stock[fam] = D['stock'][fam]
                new_alerts[fam] = D.get('stock_alerts', {}).get(fam, {})
        for pr in cur_pres:
            if pr in pres_data:
                a = alerts_from_series(pres_data[pr], months12, pr); a['familia'] = D['stock_pres'][pr].get('familia', '')
                new_pres[pr] = a
            else:
                new_pres[pr] = D['stock_pres'][pr]
        changed = (D.get('stock') != new_stock or D.get('stock_alerts') != new_alerts
                   or D.get('stock_pres') != new_pres or D.get('coverage_labels') != cov_labels)
        if changed:
            total_changed += 1
            if not check_only:
                D['stock'] = new_stock; D['stock_alerts'] = new_alerts
                D['stock_pres'] = new_pres; D['coverage_labels'] = cov_labels
                p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob+end:],
                             encoding='utf-8', newline='')
        print(f'  {rel}: fams={len(new_stock)} pres={len(new_pres)} '
              f'({"cambia" if changed else "ok"})')
    if check_only and total_changed:
        print(f'STOCK: {total_changed} data.js desactualizados. Correr: py shared/build-stock-from-laboratorio.py')
        return 1
    return 0


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    return patch('--check' in sys.argv)


if __name__ == '__main__':
    sys.exit(main())
