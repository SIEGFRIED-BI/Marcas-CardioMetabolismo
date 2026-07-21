# -*- coding: utf-8 -*-
"""Gate de consistencia de 'Total Siegfried' (total/data.js), modelo DEDUPLICADO.

El Total cuenta cada producto SIE y cada mercado IQVIA UNA sola vez (cifra real de
compania). Verifica 4 cadenas, con un recompute dedup INDEPENDIENTE (no reusa
build-total.py):
  A. IQVIA: units.{sie,mkt,ie,ms} del Total == recompute dedup desde mol_perf
     (union de productos SIE unicos por nombre + mercados unicos por serie).
  B. Recetas: aditivo -> Total == suma de las 7 lineas (recetas no duplica).
  C. kpis.json (lo que consume el Total) == kpiStrip que MUESTRA cada linea.
  D. IE/MS del Total salen de las sumas (no promedio) + venta budget ~ venta kpis.

Uso: py shared/check-total-consistency.py    (exit!=0 si hay inconsistencia)
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KPIS = REPO / 'kpis.json'
LINE_FILES = {'cardio':'cardio/data.js','antibio':'ATB/data.js','otx':'OTC/data.js',
              'resp':'respiratorio/data.js','mujer':'mujer/data.js','snc':'SNC/data.js',
              'derma':'dermatologia/data.js'}
KEYMAP = {'cardio':'cardio','antibio':'ATB','otx':'OTC','resp':'respiratorio',
          'mujer':'mujer','snc':'SNC','derma':'dermatologia'}
_M6 = ['Jan','Feb','Mar','Apr','May','Jun']
WIN = {  # periodo -> (meses curr, meses prev)  IQVIA cierre Jun 2026
    'mensual':(['Jun 2026'],['Jun 2025']),
    'ytd':([f'{m} 2026' for m in _M6],[f'{m} 2025' for m in _M6]),
    'semestre':([f'{m} 2026' for m in _M6],[f'{m} 2025' for m in _M6]),
    'trimestre':(['Apr 2026','May 2026','Jun 2026'],['Apr 2025','May 2025','Jun 2025']),
    'mat':([f'{m} 2025' for m in ['Jul','Aug','Sep','Oct','Nov','Dec']]+[f'{m} 2026' for m in _M6],
           [f'{m} 2024' for m in ['Jul','Aug','Sep','Oct','Nov','Dec']]+[f'{m} 2025' for m in _M6]),
}

def load_js(path):
    t = (REPO / path).read_text(encoding='utf-8-sig', errors='replace')
    for pat in (r'window\.OTC_DASHBOARD\s*=\s*', r'window\.TOTAL_SIEGFRIED\s*=\s*'):
        m = re.search(pat, t)
        if m:
            ob = t.index('{', m.end())
            return json.JSONDecoder().raw_decode(t[ob:])[0]
    raise ValueError(f'no anchor en {path}')

def close(a, b, tol):
    if a is None or b is None: return a == b
    return abs(a - b) <= tol

def dedup_iqvia():
    """Recompute INDEPENDIENTE: union de SIE unicos (por nombre) + mercados unicos (por serie)."""
    sie, mkt = {}, {}
    for path in LINE_FILES.values():
        D = load_js(path)
        for fam, fo in (D.get('mol_perf') or {}).items():
            mon = fo.get('monthly') or {}
            if mon:
                skey = tuple((m, round(v or 0)) for m, v in sorted(mon.items()))
                mkt.setdefault(skey, mon)
            for p in fo.get('products', []):
                if p.get('is_resto'): continue
                if p.get('is_sie') or '(SIE)' in (p.get('prod') or ''):
                    sie.setdefault(p['prod'], p.get('monthly_vals') or {})
    def wsum(ds, ms): return sum((d.get(m) or 0) for d in ds for m in ms)
    out = {}
    for per, (cw, pw) in WIN.items():
        sc, sp = wsum(sie.values(), cw), wsum(sie.values(), pw)
        mc, mp = wsum(mkt.values(), cw), wsum(mkt.values(), pw)
        out[per] = {'sie': round(sc), 'mkt': round(mc),
                    'ms': round(sc/mc*100, 2) if mc else None,
                    'ie': round((sc/sp)/(mc/mp)*100, 1) if (sp and mp and sc/sp <= 4) else None}
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    kp = json.loads(KPIS.read_text(encoding='utf-8'))
    lines = kp['lines']; lmap = {L['key']: L for L in lines}
    total = load_js('total/data.js'); comp = total['company']
    errs = []; checks = 0
    ded = dedup_iqvia()

    for p in total['periods']:
        # A: IQVIA units == recompute dedup independiente
        u = comp[p]['units']; d = ded.get(p, {})
        checks += 4
        if not close(u['sie_curr'], d.get('sie'), 2): errs.append(f'A {p}/units.sie: {u["sie_curr"]} != dedup {d.get("sie")}')
        if not close(u['mkt_curr'], d.get('mkt'), 2): errs.append(f'A {p}/units.mkt: {u["mkt_curr"]} != dedup {d.get("mkt")}')
        if not close(u.get('ms'), d.get('ms'), 0.1):  errs.append(f'A {p}/units.ms: {u.get("ms")} != dedup {d.get("ms")}')
        if not close(u.get('ie'), d.get('ie'), 0.2):  errs.append(f'A {p}/units.ie: {u.get("ie")} != dedup {d.get("ie")}')
        # D: IE/MS del Total salen de SUS sumas (no promedio)
        checks += 1
        exp_ms = round(u['sie_curr']/u['mkt_curr']*100, 2) if u['mkt_curr'] else None
        if not close(exp_ms, u.get('ms'), 0.1): errs.append(f'D {p}/units.ms no sale de sus sumas')
        # B: recetas aditivo == suma lineas
        r = comp[p]['recetas']; checks += 1
        man = sum((((L.get('kpis') or {}).get(p) or {}).get('recetas_sie') or {}).get('curr') or 0 for L in lines)
        if not close(r['sie_curr'], round(man), 1): errs.append(f'B {p}/recetas.sie: {r["sie_curr"]} != sum {round(man)}')
        # venta budget ~ kpis
        ve = comp[p].get('venta_est', {}).get('real'); vi = comp[p]['venta']['curr']; checks += 1
        if ve is not None and vi and abs(ve-vi)/max(vi,1) > 0.02: errs.append(f'D {p}/venta {ve} vs kpis {vi}')

    # C: kpis.json == kpiStrip (display) por linea
    FIELDS = [('ytd','units_sie.curr','units_ytd',2),('ytd','mercado_units.curr','mkt_ytd26',2),
              ('ytd','ms_units.curr','ms_ytd',0.1),('ytd','units_sie.ie','ie_ytd',0.2),
              ('mat','units_sie.curr','units_mat',2),('mat','ms_units.curr','ms_mat',0.1),
              ('ytd','recetas_sie.curr','sie_rec',2),('ytd','ms_recetas.curr','ms_rec',0.1)]
    for lkey, ldir in KEYMAP.items():
        L = lmap.get(lkey); ks = (load_js(LINE_FILES[lkey]).get('kpiStrip') or {})
        if not L: continue
        for per, path, ksf, tol in FIELDS:
            node = (L.get('kpis') or {}).get(per, {})
            for part in path.split('.'): node = (node or {}).get(part) if isinstance(node, dict) else None
            disp = ks.get(ksf); checks += 1
            if node is None or disp is None: continue
            if not close(round(node,2) if isinstance(node,float) else node,
                         round(disp,2) if isinstance(disp,float) else disp, tol):
                errs.append(f'C {lkey}.{ksf}: kpis={node} != display={disp}')

    print(f"check-total-consistency (modelo DEDUP): {checks} chequeos")
    if errs:
        print(f"\nFAIL ({len(errs)}):"); [print("  ", e) for e in errs[:40]]; return 1
    print("OK: IQVIA dedup == recompute independiente; recetas aditivas; IE/MS desde sumas; kpis==display.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
