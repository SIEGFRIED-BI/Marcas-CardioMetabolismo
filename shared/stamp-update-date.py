# -*- coding: utf-8 -*-
"""Estampa la fecha de ULTIMA MODIFICACION del tablero en el badge "Datos al ...".

El badge "Datos al DD/MM/YYYY" debe reflejar el ultimo dia que se modifico el
tablero (no el corte IQVIA). Este script pone la fecha de hoy (o --date) en:
  - el texto hardcodeado "Datos al DD/MM/YYYY" del footer (SNC/derma/mujer inline)
  - el campo meta "footer_date":"DD/MM/YYYY" (todas; las lineas data.js lo
    renderizan al span #footer-date via JS)

Re-ejecutar en cada deploy para mantenerlo al dia.
Uso: py shared/stamp-update-date.py [--date DD/MM/YYYY]
"""
from __future__ import annotations
import argparse, re, sys, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = [
    'SNC/index.html', 'dermatologia/dermato_dashboard.html', 'mujer/index.html',
    'cardio/data.js', 'ATB/data.js', 'OTC/data.js', 'respiratorio/data.js', 'mujer/data.js',
]
DATE_RE = re.compile(r'\d{2}/\d{2}/\d{4}')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--date'); a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    today = a.date or datetime.date.today().strftime('%d/%m/%Y')
    if not DATE_RE.fullmatch(today): print('fecha invalida:', today); return 2
    print('Estampando "Datos al" =', today)
    for rel in FILES:
        p = REPO / rel
        if not p.is_file(): print('  (skip, no existe)', rel); continue
        t = p.read_text(encoding='utf-8', errors='replace'); orig = t
        # 1) texto hardcodeado "Datos al DD/MM/YYYY"
        t = re.sub(r'(Datos al )\d{2}/\d{2}/\d{4}', r'\g<1>' + today, t)
        # 2) meta "footer_date": "DD/MM/YYYY"
        t = re.sub(r'("footer_date":\s*")\d{2}/\d{2}/\d{4}(")', r'\g<1>' + today + r'\g<2>', t)
        if t == orig: print('  (sin cambios)', rel); continue
        p.write_text(t, encoding='utf-8', newline=''); print('  OK', rel)
    return 0


if __name__ == '__main__':
    sys.exit(main())
