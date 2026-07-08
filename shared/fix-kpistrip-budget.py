# -*- coding: utf-8 -*-
"""Persiste en data.js lo que shared/budget-overrides.js computa en runtime, para que
el dato ALMACENADO == lo que la card muestra == lo que exporta el Excel.

Contexto: la card "Estimado · <Mes>'26" NO usa el kpiStrip almacenado: en runtime
budget-overrides.js (estimados vigentes MKT sidus) pisa budget[fam].2026.budget,
kpiStrip.bud_* y brandKpis[fam].budget con la semantica MES CORRIENTE (ultimo mes
con venta real != 0). Pero lo ALMACENADO quedaba congelado al corte del full build
(OTC decia 100%/425k de Mar-2026) y eso es lo que leen la hoja "Resumen" del export
(OTC_DATA.summary), el tooltip del badge (OTC_DATA.meta) y cualquier consumidor
server-side. Este fixer replica EXACTO la logica del override y la persiste:

  A) budget[fam].2026.budget <- OVERRIDES[line][fam] (estimados vigentes; las
     familias sin override conservan su budget de data.js, igual que en runtime).
  B) kpiStrip.{bud_total, real_total, bud_pct} = MES corriente (sumBudgetAtIndex).
  C) brandKpis[fam].budget = {pct, real, target} del MES corriente (syncBrandKpis).
  D) OTC_DATA.summary[fam]: ytdActual2026/ytdBudget2026/compliance2026 (YTD hasta el
     mes corriente, con estimados vigentes) + latestMonth/latestActual/latestBudget
     (mes corriente). Totales = suma de todas las familias del budget.
  E) OTC_DATA.meta.{budgetCut, rxCut, dddCut, stockCut} desde el dato vivo.

mujer no esta en OVERRIDES -> usa los estimados de su data.js con la MISMA semantica
mensual (consistencia entre lineas). Idempotente (el override en runtime recomputa lo
mismo y queda no-op). Uso:
  py shared/fix-kpistrip-budget.py            # aplica
  py shared/fix-kpistrip-budget.py --check    # gate: exit 1 si hay drift
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OVR_FILE = REPO / 'shared' / 'budget-overrides.js'
# key de OVERRIDES -> (nombre linea, data.js)
LINES = [
    ('cardio',       'cardio',       'cardio/data.js'),
    ('atb',          'ATB',          'ATB/data.js'),
    ('otc',          'OTC',          'OTC/data.js'),
    ('respiratorio', 'respiratorio', 'respiratorio/data.js'),
    ('snc',          'SNC',          'SNC/data.js'),
    ('dermatologia', 'dermato',      'dermatologia/data.js'),
    (None,           'mujer',        'mujer/data.js'),
]
MES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MES_EN_I = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def load_overrides():
    t = OVR_FILE.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const OVERRIDES = (\{.*?\});', t, re.S)
    return json.loads(m.group(1)) if m else {}


def find_obj(text, key):
    m = re.search(r'window\.' + key + r'\s*=\s*', text)
    if not m:
        return None
    ob = text.index('{', m.end())
    obj, end = json.JSONDecoder().raw_decode(text[ob:])
    return ob, obj, ob + end


def r0(v):
    return None if v is None else round(v)


def r1(v):
    return None if v is None else round(v * 10) / 10


def latest_actual_index(bud):
    """Réplica de latestActualIndex: último idx con algún real finito != 0."""
    latest = -1
    for o in bud.values():
        arr = (o.get('2026') or {}).get('real')
        if not isinstance(arr, list):
            continue
        for i, v in enumerate(arr):
            if isinstance(v, (int, float)) and v != 0:
                latest = max(latest, i)
    return latest


def sum_at(bud, kind, idx):
    """Réplica de sumBudgetAtIndex: suma finitos en idx; None si ninguno."""
    total, found = 0, False
    for o in bud.values():
        arr = (o.get('2026') or {}).get(kind)
        if not isinstance(arr, list) or idx >= len(arr):
            continue
        v = arr[idx]
        if isinstance(v, (int, float)):
            total += v
            found = True
    return r0(total) if found else None


def sum_ytd(bud, kind, lastm):
    tot = 0
    for o in bud.values():
        arr = (o.get('2026') or {}).get(kind) or []
        tot += sum(v for v in arr[:lastm] if isinstance(v, (int, float)))
    return round(tot)


def rx_cut_from_label(D):
    lbl = (D.get('meta') or {}).get('rec_label') or ''
    m = re.match(r"^([A-Za-z]{3})'(\d{2})$", lbl.strip())
    return f'{m.group(1)}-20{m.group(2)}' if m else None


def stock_cut(D):
    st = D.get('stock') or {}
    best = None
    for months in st.values():
        if not isinstance(months, dict):
            continue
        for mk, v in months.items():
            p = mk.split()
            if len(p) != 2 or p[0] not in MES_EN_I:
                continue
            val = (v or {}).get('stock') if isinstance(v, dict) else v
            if not val:
                continue
            key = (int(p[1]), MES_EN_I[p[0]])
            if best is None or key > best:
                best = key
    return f'{MES_ES[best[1]]}-{best[0]}' if best else None


def process(ovr_key, line, rel, overrides, check):
    p = REPO / rel
    text = p.read_text(encoding='utf-8', errors='replace')
    dash = find_obj(text, 'OTC_DASHBOARD')
    if not dash:
        return f'  [{line}] sin OTC_DASHBOARD -> skip', False
    _, D, _ = dash
    bud = D.setdefault('budget', {})
    drifts = []

    # A) estimados vigentes (OVERRIDES) -> budget[fam].2026.budget
    for fam, est in (overrides.get(ovr_key) or {}).items():
        entry = bud.setdefault(fam, {})
        y = entry.setdefault('2026', {})
        if not isinstance(y.get('real'), list):
            y['real'] = [None] * 12
        newb = [r0(v) if isinstance(v, (int, float)) else None for v in (est or [])[:12]]
        newb += [None] * (12 - len(newb))
        if y.get('budget') != newb:
            drifts.append(f'budget[{fam}].2026.budget: estimados vigentes (override)')
            y['budget'] = newb

    idx = latest_actual_index(bud)
    if idx < 0:
        return f'  [{line}] sin venta real 2026 -> skip', False
    lastm = idx + 1
    month_lbl = f'{MES_ES[idx]}-2026'

    # B) kpiStrip = mes corriente
    bt, rt = sum_at(bud, 'budget', idx), sum_at(bud, 'real', idx)
    pct = r1(rt / bt * 100) if (bt and rt is not None) else None
    ks = D.get('kpiStrip')
    if isinstance(ks, dict):
        for k, v in (('bud_total', bt), ('real_total', rt), ('bud_pct', pct)):
            if k in ks and ks[k] != v:
                drifts.append(f'kpiStrip.{k}: {ks[k]} -> {v}')
                ks[k] = v

    # C) brandKpis[fam].budget = mes corriente (solo familias con serie)
    bk = D.get('brandKpis')
    if isinstance(bk, dict):
        for fam, payload in bk.items():
            if not isinstance(payload, dict) or fam not in bud:
                continue
            y = bud[fam].get('2026') or {}
            t = (y.get('budget') or [None] * 12)[idx] if len(y.get('budget') or []) > idx else None
            r = (y.get('real') or [None] * 12)[idx] if len(y.get('real') or []) > idx else None
            has_t = isinstance(t, (int, float)) and t != 0
            has_r = isinstance(r, (int, float))
            newb = {'pct': r1(r / t * 100) if (has_t and has_r) else None,
                    'real': r0(r) if has_r else None,
                    'target': r0(t) if has_t else None}
            if payload.get('budget') != newb:
                drifts.append(f'brandKpis[{fam}].budget: {payload.get("budget")} -> {newb}')
                payload['budget'] = newb

    # D/E) objeto legacy OTC_DATA
    leg = find_obj(text, 'OTC_DATA')
    L = leg[1] if leg else None
    if L is not None:
        summ = L.get('summary')
        if isinstance(summ, dict):
            for fam, s in summ.items():
                if not isinstance(s, dict):
                    continue
                if fam == 'Totales':
                    fr, fb = sum_ytd(bud, 'real', lastm), sum_ytd(bud, 'budget', lastm)
                    la, lb = sum_at(bud, 'real', idx) or 0, sum_at(bud, 'budget', idx) or 0
                elif fam in bud:
                    y = bud[fam].get('2026') or {}
                    fr = round(sum(v for v in (y.get('real') or [])[:lastm] if isinstance(v, (int, float))))
                    fb = round(sum(v for v in (y.get('budget') or [])[:lastm] if isinstance(v, (int, float))))
                    la = r0((y.get('real') or [None] * 12)[idx] or 0)
                    lb = r0((y.get('budget') or [None] * 12)[idx] or 0)
                else:
                    continue
                comp = r1(fr / fb * 100) if fb else 0
                for k, v in (('ytdActual2026', fr), ('ytdBudget2026', fb), ('compliance2026', comp),
                             ('latestMonth', month_lbl), ('latestActual', la), ('latestBudget', lb)):
                    if k in s and s[k] != v:
                        drifts.append(f'summary[{fam}].{k}: {s[k]} -> {v}')
                        s[k] = v
        meta_l = L.get('meta')
        if isinstance(meta_l, dict):
            newcuts = {'budgetCut': month_lbl, 'rxCut': rx_cut_from_label(D), 'stockCut': stock_cut(D)}
            ddd_months = ((L.get('ddd') or {}).get('months') or [])
            if ddd_months:
                newcuts['dddCut'] = ddd_months[-1]
            for k, v in newcuts.items():
                if v and k in meta_l and meta_l[k] != v:
                    drifts.append(f'meta.{k}: {meta_l[k]!r} -> {v!r}')
                    meta_l[k] = v

    if drifts and not check:
        for key, obj in (('OTC_DASHBOARD', D), ('OTC_DATA', L)):
            if obj is None:
                continue
            pos = find_obj(text, key)
            text = text[:pos[0]] + json.dumps(obj, ensure_ascii=False) + text[pos[2]:]
        p.write_text(text, encoding='utf-8', newline='')
    tag = 'DRIFT' if drifts else 'ok'
    detail = ('\n      ' + '\n      '.join(drifts[:5]) + (f'\n      ... +{len(drifts)-5} mas' if len(drifts) > 5 else '')) if drifts else ''
    return (f'  [{line}] mes={MES_ES[idx]}-2026 real_mes={rt:,} est_mes={bt if bt is not None else 0:,} '
            f'pct={pct} [{tag}]{detail}'), bool(drifts)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check = '--check' in sys.argv
    overrides = load_overrides()
    any_drift = False
    for ovr_key, line, rel in LINES:
        msg, drifted = process(ovr_key, line, rel, overrides, check)
        print(msg)
        any_drift = any_drift or drifted
    if check and any_drift:
        print('\nKPISTRIP-BUDGET FAIL: dato almacenado != lo que muestra la card '
              '(budget-overrides). Corre: py shared/fix-kpistrip-budget.py')
        return 1
    print('\nOK: venta-vs-estimado almacenado == display (mes corriente).' if not any_drift
          else '\nListo (drift corregido).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
