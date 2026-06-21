# -*- coding: utf-8 -*-
"""Quita filas DUPLICADAS EXACTAS de D.convenios que el render
(normalizeConvName + suma) cuenta doble.

El render agrupa por normalizeConvName(os) y SUMA unid/unid24. La fuente trae la
misma OS dos veces con un código distinto pero MISMAS unidades, p.ej.:
  'INSSJYP - PAMI'         unid=665642
  'INSSJYP - PAMI (9153)'  unid=665642   <- (9153) se borra al normalizar -> se suman -> PAMI x2

Esto borra SOLO la fila repetida: misma normalizeConvName(os) Y mismas (unid, unid24).
NO toca variantes reales (OSDE (9124) vs OSDE NACIONAL | FMLK -> normalizan distinto,
o tienen unidades distintas -> el render las muestra/ suma a propósito). Es decir, está
alineado con normalizeConvName del render, a diferencia de dedup-convenios.py (que
agrupa por prefijo canónico y es más agresivo).

Aplica a las 7 (data.js). Idempotente, modo --check.
"""
from __future__ import annotations
import re, json, sys, unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = ['cardio/data.js','ATB/data.js','OTC/data.js','respiratorio/data.js',
         'mujer/data.js','SNC/data.js','dermatologia/data.js']


def normalize_conv(name):
    """Puerto EXACTO de normalizeConvName() del render."""
    s = str(name or '')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\s*\([^)]*\)', ' ', s)
    s = re.sub(r'\s*\|\s*FMLK\b', ' ', s, flags=re.I)
    s = re.sub(r'\s*\|\s*[A-Z]{1,5}\b', ' ', s, flags=re.I)
    s = re.sub(r'\bGROUP\b', ' ', s, flags=re.I)
    s = re.sub(r'\s*-\s*CT\b', ' ', s, flags=re.I)
    s = re.sub(r'\s*-\s*LACTEOS?\b', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip().upper()
    return s


def dedup_product(rows):
    seen = set(); out = []; removed = 0
    for r in rows:
        key = (normalize_conv(r.get('os')), r.get('unid'), r.get('unid24'))
        if key in seen:
            removed += 1
            continue
        seen.add(key); out.append(r)
    return out, removed


def patch_line(path, check_only=False):
    t = (REPO / path).read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    if not m:
        return 0, 'no OTC_DASHBOARD'
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    conv = D.get('convenios', {})
    total_removed = 0
    for prod, rows in conv.items():
        if not isinstance(rows, list):
            continue
        new_rows, removed = dedup_product(rows)
        if removed and not check_only:
            conv[prod] = new_rows
        total_removed += removed
    if total_removed and not check_only:
        (REPO / path).write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                                 encoding='utf-8', newline='')
    return total_removed, f'{total_removed} fila(s) duplicadas ' + ('a quitar' if check_only else 'quitadas')


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
        print(f'CONVENIOS-DEDUP FAIL: {total} filas duplicadas exactas (doble conteo). '
              f'Correr: py shared/dedup-convenios-exact.py')
        return 1
    print('OK: convenios sin duplicados exactos.' if check_only else 'Listo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
