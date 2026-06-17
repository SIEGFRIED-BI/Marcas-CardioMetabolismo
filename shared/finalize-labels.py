# -*- coding: utf-8 -*-
"""Normaliza TODAS las etiquetas de fecha de los 7 tableros desde el dato real.

Reemplaza a stamp-update-date.py. Para cada tablero detecta el objeto de datos
VIVO (el que tiene mol_perf: window.OTC_DASHBOARD / inline const D /
window.MUJER_DATA), computa desde el dato real y reescribe por regex:
  - kpi_ytd_label / kpi_ytd_prev_label / kpi_mat_label / kpi_mat_prev_label
    (ultimo mes de mol_perf; prev = interanual)        -> "YTD Abr'2026", "MAT Abr'2025"
  - budget_label  (ultimo mes real de budget[fam]['2026'].real)   -> "May'26"
  - rec_label     (ultimo mes de recetas / rec_ms)                -> "Abr'26"
  - footer_date   = HOY (ultima modificacion del tablero)          -> "16/06/2026"
    + el texto hardcodeado "Datos al DD/MM/YYYY" del footer inline.

Idempotente. Correr al final del pipeline (update-all.ps1). Uso:
  py shared/finalize-labels.py [--date DD/MM/YYYY]
"""
from __future__ import annotations
import argparse, json, re, sys, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# (archivo, ¿buscar footer hardcodeado "Datos al"?)
FILES = [
    ('cardio/data.js', False), ('ATB/data.js', False), ('OTC/data.js', False),
    ('respiratorio/data.js', False), ('mujer/data.js', False),
    ('SNC/index.html', True), ('dermatologia/dermato_dashboard.html', True),
    ('mujer/index.html', True),
]
MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
ES = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
ANCHORS = [r'window\.OTC_DASHBOARD\s*=\s*', r'window\.MUJER_DATA\s*=\s*', r'const\s+D\s*=\s*']


def msort(mk):
    p = str(mk).split(); return int(p[1])*100 + MES_INV.get(p[0],0) if len(p)==2 and p[0] in MES_INV else 0


def find_live_obj(text):
    """Devuelve el primer objeto parseable que tenga mol_perf no vacio."""
    for anc in ANCHORS:
        for m in re.finditer(anc, text):
            try:
                ob = text.index('{', m.end())
                obj, _ = json.JSONDecoder().raw_decode(text[ob:])
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(obj, dict) and obj.get('mol_perf'):
                return obj
    return None


def last_iqvia(obj):
    months = set()
    for fam in (obj.get('mol_perf') or {}).values():
        months |= set((fam.get('monthly') or {}).keys())
        for p in (fam.get('products') or []):
            months |= set((p.get('monthly_vals') or {}).keys())
    if not months: return None
    mk = max(months, key=msort); p = mk.split(); return MES_INV[p[0]], int(p[1])


def last_budget(obj):
    mx = -1
    for fam, yrs in (obj.get('budget') or {}).items():
        real = (yrs.get('2026') or {}).get('real') or [] if isinstance(yrs, dict) else []
        for i, v in enumerate(real):
            if v is not None and v != 0: mx = max(mx, i)
    return (mx + 1, 2026) if 0 <= mx < 12 else None


def last_recetas(obj):
    months = set()
    for fam, d in (obj.get('recetas') or {}).items():
        if isinstance(d, dict): months |= {k for k in d.keys() if msort(k)}
    for fam, d in (obj.get('rec_ms') or {}).items():
        if isinstance(d, dict):
            sie = d.get('sie') if isinstance(d.get('sie'), dict) else d
            months |= {k for k in sie.keys() if msort(k)}
    if not months: return None
    mk = max(months, key=msort); p = mk.split(); return MES_INV[p[0]], int(p[1])


def set_label(text, key, value):
    """Setea "key": "value" en TODAS sus apariciones, ya sea que el valor actual
    sea string ("...") o null. value sin comillas."""
    pat = re.compile(r'("' + re.escape(key) + r'":\s*)(?:"[^"]*"|null)')
    return pat.subn(lambda m: m.group(1) + '"' + value + '"', text)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--date'); a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    today = a.date or datetime.date.today().strftime('%d/%m/%Y')
    if not re.fullmatch(r'\d{2}/\d{2}/\d{4}', today): print('fecha invalida:', today); return 2
    print('finalize-labels | footer "Datos al" =', today, '\n')

    for rel, has_footer in FILES:
        p = REPO / rel
        if not p.is_file(): print('  (skip)', rel); continue
        text = p.read_text(encoding='utf-8', errors='replace'); orig = text
        obj = find_live_obj(text)
        labels = {'footer_date': today}
        if obj:
            iq = last_iqvia(obj)
            if iq:
                mm, yy = iq
                labels['kpi_ytd_label'] = f"YTD {ES[mm]}'{yy}"
                labels['kpi_ytd_prev_label'] = f"YTD {ES[mm]}'{yy-1}"
                labels['kpi_mat_label'] = f"MAT {ES[mm]}'{yy}"
                labels['kpi_mat_prev_label'] = f"MAT {ES[mm]}'{yy-1}"
            bu = last_budget(obj)
            if bu: labels['budget_label'] = f"{ES[bu[0]]}'{str(bu[1])[2:]}"
            rc = last_recetas(obj)
            if rc: labels['rec_label'] = f"{ES[rc[0]]}'{str(rc[1])[2:]}"
        changed = []
        for key, val in labels.items():
            text, n = set_label(text, key, val)
            if n: changed.append(f'{key}={val}({n})')
        if has_footer:
            text, n = re.subn(r'(Datos al )\d{2}/\d{2}/\d{4}', r'\g<1>' + today, text)
            if n: changed.append(f'footer-text({n})')
        # sanity: si toco un inline const D, debe seguir parseando
        if text != orig and 'const D' in text[:max(1, text.find('=', 0))+0] or True:
            for anc in ANCHORS:
                m = re.search(anc, text)
                if m:
                    try:
                        ob = text.index('{', m.end()); json.JSONDecoder().raw_decode(text[ob:])
                    except Exception as e:
                        print('  ERROR parse tras editar', rel, '->', e, '(NO escribo)'); changed = None; break
        if changed is None: continue
        if text != orig:
            p.write_text(text, encoding='utf-8', newline=''); print(f'  OK {rel:42} {", ".join(changed)}')
        else:
            print(f'  (sin cambios) {rel}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
