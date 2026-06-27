# -*- coding: utf-8 -*-
"""Crea/actualiza brandKpis['MAGNUS 36'] en OTC (no existia -> al seleccionar la marca
en el tablero la tarjeta KPI quedaba vacia). MAGNUS 36 ya es seleccionable (esta en
prodMap) y ya tiene mercado propio en mol_perf (sildenafil/tadalafil rebuild), budget
(estimado) y rec_ms; solo faltaba el brandKpis.

Arma la entrada igual que las demas marcas desde mol_perf[MAGNUS 36] (producto SIE +
mercado), budget (ultimo mes con real) y rec_ms (ultimo mes). market_total/ms/ie los
re-afinan despues fix-brandkpis-market-total.py y fix-brandkpis-ie-vs-market.py.
Tambien agrega 'MAGNUS 36' a sieProds (consistencia con brandKpis). Idempotente.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
FAM = 'MAGNUS 36'


def msort(k):
    p = k.split(); return int(p[1]) * 100 + MES.index(p[0])


def period_kpi(mol, sie, per):
    d = mol.get(per, {})
    if not d:
        return None
    keys = sorted(d, key=msort)
    if len(keys) < 2:
        return None
    cur, prev = keys[-1], keys[-2]
    units = sie.get(per, {}).get(cur)
    units_prev = sie.get(per, {}).get(prev)
    mkt = d.get(cur)
    if units is None or not mkt:
        return None
    ms = round(units / mkt * 100, 1) if mkt else None
    growth = round((units / units_prev - 1) * 100, 1) if units_prev else None
    ie = None
    mkt_prev = d.get(prev)
    if units_prev and mkt and mkt_prev:
        bg = units / units_prev; mg = mkt / mkt_prev
        if bg < 5 and 0.2 < mg < 5:
            ie = round(bg / mg * 100, 1)
    return {'ie': ie, 'ms': ms, 'units': int(round(units)),
            'units_prev': int(round(units_prev)) if units_prev else None,
            'market_total': int(round(mkt)), 'growth': growth}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    p = REPO / 'OTC' / 'data.js'
    t = p.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])

    mol = (D.get('mol_perf') or {}).get(FAM)
    if not mol:
        print(f'  (skip) mol_perf[{FAM}] no existe'); return 0
    sie = next((pp for pp in mol.get('products', []) if pp.get('is_sie')), None)
    if not sie:
        print(f'  (skip) {FAM} sin producto SIE'); return 0

    ytd = period_kpi(mol, sie, 'ytd')
    mat = period_kpi(mol, sie, 'mat')
    if not ytd or not mat:
        print(f'  (skip) no pude computar ytd/mat de {FAM}'); return 0

    # budget: ultimo mes con real en D.budget[MAGNUS 36][2026]
    budget = {'pct': None, 'real': None, 'target': None}
    by = (D.get('budget') or {}).get(FAM, {}).get('2026', {})
    real = by.get('real') or []; tgt = by.get('budget') or []
    last_i = max((i for i, v in enumerate(real) if v not in (None, 0)), default=-1)
    if last_i >= 0:
        rv = real[last_i]; tv = tgt[last_i] if last_i < len(tgt) else None
        budget = {'pct': round(rv / tv * 100, 1) if tv else None,
                  'real': int(round(rv)), 'target': int(round(tv)) if tv else None}

    # rec: ultimo mes de rec_ms[MAGNUS 36].ms
    rec = {'ms': 0, 'label': None}
    rm = (D.get('rec_ms') or {}).get(FAM, {}).get('ms') or {}
    if rm:
        lk = max(rm, key=msort)
        rec = {'ms': round(rm[lk], 1) if isinstance(rm[lk], float) else rm[lk], 'label': lk}

    D.setdefault('brandKpis', {})[FAM] = {'ytd': ytd, 'mat': mat, 'budget': budget, 'rec': rec}

    # sieProds: mantener consistencia (mismo set que brandKpis)
    sp = D.get('sieProds')
    if isinstance(sp, list) and FAM not in sp:
        D['sieProds'] = sorted(set(sp) | {FAM})

    p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                 encoding='utf-8', newline='')
    print(f'  brandKpis[{FAM}]: ytd ms={ytd["ms"]} ie={ytd["ie"]} | mat ms={mat["ms"]} '
          f'| budget {budget["pct"]}% | rec {rec["ms"]}% ({rec["label"]})')
    print('  + agregado a sieProds. Correr fix-brandkpis-market/ie/rec para afinar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
