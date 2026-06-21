# -*- coding: utf-8 -*-
"""Rellena brandKpis[marca].rec.ms (+ label) desde D.rec_ms[marca] cuando quedó
en 0/None pero el rec_ms SÍ tiene dato (bug puntual: dermato MOMETAX mostraba
'MS% Recetas 0.0%' cuando el real es ~67%).

Solo toca el caso roto (rec.ms in {0, None} y rec_ms con valor) -> no cambia las
marcas que ya muestran un mes válido. Usa el último mes de rec_ms[marca].ms.
Aplica a las 7. Idempotente, modo --check.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
FILES = ['cardio/data.js','ATB/data.js','OTC/data.js','respiratorio/data.js',
         'mujer/data.js','SNC/data.js','dermatologia/data.js']


def msort(k):
    p = k.split(); return int(p[1]) * 100 + MES.index(p[0])


def patch_line(path, check_only=False):
    t = (REPO / path).read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m:
        return 0, 'no OTC_DASHBOARD'
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    bk = D.get('brandKpis', {}); rm = D.get('rec_ms', {})
    if not bk or not rm:
        return 0, 'sin brandKpis/rec_ms'
    fixed = 0
    for fam, kp in bk.items():
        rec = kp.get('rec')
        if not isinstance(rec, dict):
            continue
        if rec.get('ms') not in (0, None):
            continue
        src = (rm.get(fam) or {}).get('ms') or {}
        if not src:
            continue
        last = max(src, key=msort)
        val = src[last]
        if not val:
            continue
        if not check_only:
            rec['ms'] = round(val, 1) if isinstance(val, float) else val
            rec['label'] = last
        fixed += 1
    if fixed and not check_only:
        (REPO / path).write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                                 encoding='utf-8', newline='')
    return fixed, f'{fixed} rec.ms ' + ('a rellenar' if check_only else 'rellenados')


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_only = '--check' in sys.argv
    total = 0
    for f in FILES:
        try:
            n, msg = patch_line(f, check_only)
            total += n
            print(f'  {f}: {msg}')
        except Exception as e:
            print(f'  {f}: ERROR {e}')
            return 1
    if check_only and total > 0:
        print(f'BRANDKPIS-REC FAIL: {total} rec.ms en 0 con dato en rec_ms. '
              f'Correr: py shared/fix-brandkpis-rec.py')
        return 1
    print('OK: brandKpis.rec.ms sin ceros espurios.' if check_only else 'Listo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
