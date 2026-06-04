# -*- coding: utf-8 -*-
"""Re-escala el STOCK de ATB a unidades reales (venta interna).

PROBLEMA: el stock pivot historico de ATB trae 'Stock final'/'Ventas' en una metrica
distinta (no ventas mensuales reales): el ratio vs la venta interna real va de ~2.8x
(Jun25) a ~9.7x (Mar26), y el pivot de mayo ya viene en la metrica nueva (~1x). Eso
genera un "acantilado" falso en el grafico de stock (de ~180k a ~14k en may-2026).

SOLUCION: 'dias' es invariante a la metrica (stock/ventas del mismo origen = ratio real
de cobertura). Reconstruimos por (familia, mes):
    ventas_real = D.budget[fam][YYYY].real[mes]    (venta interna; el tablero ya la usa)
    dias        = D.stock[fam][mes].dias           (se preserva, ratio correcto)
    stock_real  = round(dias/30 * ventas_real)
y escalamos las 'ventas' de stock_alerts / stock_pres por el mismo ratio por (fam, mes).
NO toca 'dias', 'facturacion' (no se muestra), ni otras lineas/secciones.

Solo ATB. Idempotente solo si se corre 1 vez (re-correr re-escalaria de nuevo) ->
correr una sola vez. Uso: py shared/rescale-atb-stock.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / 'ATB' / 'data.js'
MES_EN = {'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
          'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11}
MES_ES = {'Ene': 0, 'Feb': 1, 'Mar': 2, 'Abr': 3, 'May': 4, 'Jun': 5,
          'Jul': 6, 'Ago': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dic': 11}


def parse_en(k):
    p = str(k).split()
    return (int(p[1]), MES_EN[p[0]]) if len(p) == 2 and p[0] in MES_EN else (None, None)


def parse_es(k):
    p = str(k).split()
    return (2000 + int(p[1]), MES_ES[p[0]]) if len(p) == 2 and p[0] in MES_ES else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    text = DATA.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])

    stock = D['stock']
    budget = D['budget']
    FAMS = list(stock.keys())
    ratio = {}  # (fam, year, idx) -> ventas_real / ventas_old

    def real_v(fam, yr, idx):
        r = ((budget.get(fam) or {}).get(str(yr)) or {}).get('real') or []
        return r[idx] if idx is not None and idx < len(r) and isinstance(r[idx], (int, float)) else None

    # 1) D.stock: ventas=real, stock=dias/30*real (preserva dias)
    n_stock = 0
    sample = {}
    for fam in FAMS:
        for mk, d in stock[fam].items():
            yr, idx = parse_en(mk)
            vr = real_v(fam, yr, idx)
            ov = d.get('ventas'); di = d.get('dias')
            if vr and vr > 0 and ov and di is not None:
                ratio[(fam, yr, idx)] = vr / ov
                if fam == 'ACANTEX' and mk in ('Mar 2026', 'Apr 2026', 'May 2026'):
                    sample[mk] = (d.get('stock'), ov, di)
                d['ventas'] = int(round(vr))
                d['stock'] = int(round(di / 30 * vr))
                n_stock += 1

    # 2) stock_alerts[fam].ventas y 3) stock_pres[prod].ventas: escalar por ratio(fam,mes)
    cov = D.get('coverage_labels') or []
    n_al = n_pr = 0
    for fam in FAMS:
        e = (D.get('stock_alerts') or {}).get(fam)
        if e and isinstance(e.get('ventas'), list):
            for i, lbl in enumerate(cov):
                yr, idx = parse_es(lbl)
                r = ratio.get((fam, yr, idx))
                if r is not None and i < len(e['ventas']) and isinstance(e['ventas'][i], (int, float)):
                    e['ventas'][i] = int(round(e['ventas'][i] * r)); n_al += 1
    for prod, e in (D.get('stock_pres') or {}).items():
        fam = e.get('familia')
        if fam in FAMS and isinstance(e.get('ventas'), list):
            for i, lbl in enumerate(cov):
                yr, idx = parse_es(lbl)
                r = ratio.get((fam, yr, idx))
                if r is not None and i < len(e['ventas']) and isinstance(e['ventas'][i], (int, float)):
                    e['ventas'][i] = int(round(e['ventas'][i] * r)); n_pr += 1

    print('ACANTEX sample (stock, ventas, dias) ANTES -> DESPUES:')
    for mk in ('Mar 2026', 'Apr 2026', 'May 2026'):
        if mk in sample:
            d = stock['ACANTEX'][mk]
            print('  %-9s %s -> stock=%s ventas=%s dias=%s'
                  % (mk, sample[mk], d['stock'], d['ventas'], d['dias']))
    print('\nD.stock celdas=%d, stock_alerts ventas=%d, stock_pres ventas=%d' % (n_stock, n_al, n_pr))

    if args.dry_run:
        print('\nDRY RUN: nada se escribio.')
        return 0
    DATA.write_text(text[:ob] + json.dumps(D, ensure_ascii=False) + text[ob + end:],
                    encoding='utf-8', newline='')
    print('\nEscrito ATB/data.js.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
