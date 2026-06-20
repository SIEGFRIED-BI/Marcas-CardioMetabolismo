# -*- coding: utf-8 -*-
"""Audita que TODAS las etiquetas de fecha de meta coincidan con su dato real.

Cada etiqueta tiene su PROPIA fuente/corte (no todas siguen a IQVIA):
  - kpi_ytd/ytd_prev/mat/mat_prev -> ultimo mes de mol_perf (corte IQVIA PM)
  - budget_label                  -> ultimo mes real (no-0) de budget[*]['2026'].real
  - rec_label                     -> ultimo mes de recetas / rec_ms (corte CloseUp)
Que una etiqueta este "atras" de IQVIA NO es bug si refleja su propia fuente.
El bug es cuando NO coincide con su fuente (p.ej. rec_label mostrando el mes IQVIA).

Uso: py shared/audit-labels.py   (exit 1 si hay mismatches)
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EN = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
ES = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
ANCHORS = [r'window\.OTC_DASHBOARD\s*=\s*', r'const\s+D\s*=\s*']
FILES = {
    'cardio': 'cardio/data.js', 'ATB': 'ATB/data.js', 'OTC': 'OTC/data.js',
    'respiratorio': 'respiratorio/data.js', 'SNC': 'SNC/data.js',
    'derma': 'dermatologia/data.js', 'mujer': 'mujer/index.html',
}


def msort(mk):
    p = str(mk).split(); return int(p[1])*100 + EN.get(p[0],0) if len(p)==2 and p[0] in EN else 0


def find_live(text):
    for anc in ANCHORS:
        for m in re.finditer(anc, text):
            try:
                ob = text.index('{', m.end()); obj,_ = json.JSONDecoder().raw_decode(text[ob:])
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(obj, dict) and obj.get('mol_perf'):
                return obj
    return None


def last_iqvia(obj):
    mm = set()
    for fam in (obj.get('mol_perf') or {}).values():
        mm |= set((fam.get('monthly') or {}).keys())
        for p in (fam.get('products') or []): mm |= set((p.get('monthly_vals') or {}).keys())
    if not mm: return None
    k = max(mm, key=msort); p = k.split(); return EN[p[0]], int(p[1])


def last_budget(obj):
    mx = -1
    for yrs in (obj.get('budget') or {}).values():
        real = (yrs.get('2026') or {}).get('real') or [] if isinstance(yrs, dict) else []
        for i, v in enumerate(real):
            if v not in (None, 0): mx = max(mx, i)
    return (mx+1, 2026) if 0 <= mx < 12 else None


def last_recetas(obj):
    mm = set()
    for d in (obj.get('recetas') or {}).values():
        if isinstance(d, dict): mm |= {k for k in d if msort(k)}
    for d in (obj.get('rec_ms') or {}).values():
        if isinstance(d, dict):
            sie = d.get('sie') if isinstance(d.get('sie'), dict) else d
            mm |= {k for k in sie if msort(k)}
    if not mm: return None
    k = max(mm, key=msort); p = k.split(); return EN[p[0]], int(p[1])


def expected(obj):
    e = {}
    iq = last_iqvia(obj)
    if iq:
        mm, yy = iq
        e['kpi_ytd_label'] = f"YTD {ES[mm]}'{yy}"; e['kpi_ytd_prev_label'] = f"YTD {ES[mm]}'{yy-1}"
        e['kpi_mat_label'] = f"MAT {ES[mm]}'{yy}"; e['kpi_mat_prev_label'] = f"MAT {ES[mm]}'{yy-1}"
    bu = last_budget(obj)
    if bu: e['budget_label'] = f"{ES[bu[0]]}'{str(bu[1])[2:]}"
    rc = last_recetas(obj)
    if rc: e['rec_label'] = f"{ES[rc[0]]}'{str(rc[1])[2:]}"
    return e


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    bad = 0
    for ln, rel in FILES.items():
        p = REPO / rel
        obj = find_live(p.read_text(encoding='utf-8', errors='replace'))
        if not obj: print(f'[{ln}] no live obj'); bad += 1; continue
        meta = obj.get('meta', {}) or {}
        exp = expected(obj)
        for key, want in exp.items():
            got = meta.get(key)
            status = 'OK' if got == want else ('MISSING' if got is None else 'MISMATCH')
            if status != 'OK':
                bad += 1
                print(f'[{ln:12}] {key:20} {status:9} got={got!r:24} expected={want!r}')
    if bad == 0:
        print('OK: todas las etiquetas coinciden con su dato real (7 lineas).')
        return 0
    print(f'\n{bad} etiqueta(s) desfasada(s).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
