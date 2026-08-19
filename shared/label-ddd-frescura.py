#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rotula el GAP DE FRESCURA entre el panel DDD y el Mercado IQVIA de la linea.

Los dos hechos conviven en el mismo tablero pero se actualizan por caminos
distintos: Mercado IQVIA sale del master AR_PM (mensual, al dia) y el DDD sale
del panel regional de Qlik, que puede ir uno o mas meses atras. En el cierre de
Jul-2026 el master trajo julio y el panel de Qlik seguia en junio.

El problema es que la pagina DDD no dice a que mes corresponde: su subtitulo es
un texto fijo ('... IQVIA 2025' en cardio, con el dato en Jun-2026). Un lector
que salta del Mercado IQVIA al DDD no tiene forma de ver que esta mirando un mes
distinto. Este script deriva las DOS fechas del dato real y las escribe en el
subtitulo, en vez de dejarlas implicitas.

Es idempotente: si ya hay un <span class="frescura-ddd"> lo reemplaza.
No inventa nada: si no puede derivar alguna de las dos fechas, reporta SKIP.

Uso:  python shared/label-ddd-frescura.py [--check]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (pagina DDD, data.js de la linea)
PAGES = [
    ('cardio/DDD/index.html', 'cardio/data.js'),
    ('ATB/DDD/index.html', 'ATB/data.js'),
    ('OTC/DDD/index.html', 'OTC/data.js'),
    ('respiratorio/DDD/index.html', 'respiratorio/data.js'),
    ('mujer/DDD/index.html', 'mujer/data.js'),
    ('SNC/DDD/index.html', 'SNC/data.js'),
    ('dermatologia/DDD/index.html', 'dermatologia/data.js'),
]

EN = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
      'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
ES = {'Ene': 1, 'Feb': 2, 'Mar': 3, 'Abr': 4, 'May': 5, 'Jun': 6,
      'Jul': 7, 'Ago': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dic': 12}
ES_OUT = {v: k for k, v in ES.items()}

SPAN_RE = re.compile(r'\s*<span class="frescura-ddd">.*?</span>', re.S)
HERO_RE = re.compile(r'(<div class="hero-sub">)(.*?)(</div>)', re.S)

results = []


def add(status, nombre, detalle):
    results.append((status, nombre, detalle))
    print(f'{status:4s} {nombre:34s} {detalle}')


def parse_month(s):
    """'Jun-2026' | 'Jun 2026' -> (2026, 6)."""
    p = re.split(r'[ -]', str(s).strip())
    if len(p) != 2:
        return None
    mm = EN.get(p[0]) or ES.get(p[0])
    if not mm:
        return None
    try:
        return (int(p[1]), mm)
    except ValueError:
        return None


def fmt(ym):
    return f'{ES_OUT[ym[1]]}-{ym[0]}'


def months_from_text(text):
    """Ultimo mes de un array `months` (cardio lo trae inline; las demas lineas
    lo tienen en el competidores-data.js que la pagina carga aparte)."""
    best = None
    for m in re.finditer(r'"months"\s*:\s*\[(.*?)\]', text, re.S):
        for x in re.findall(r'"([^"]+)"', m.group(1)):
            ym = parse_month(x)
            if ym and (best is None or ym > best):
                best = ym
    return best


def ddd_last_month(html, page_path):
    """Inline primero; si no, el competidores-data.js hermano."""
    ym = months_from_text(html)
    if ym:
        return ym
    sib = page_path.parent / 'competidores-data.js'
    if sib.is_file():
        txt = sib.read_text(encoding='utf-8-sig', errors='replace')
        ym = months_from_text(txt)
        if ym:
            return ym
        # ultimo recurso: cualquier month key suelto del archivo
        cand = [parse_month(x) for x in
                re.findall(r'"((?:Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic|'
                           r'Jan|Apr|Aug|Dec)[ -]20\d\d)"', txt)]
        cand = [c for c in cand if c]
        if cand:
            return max(cand)
    return None


def iqvia_last_month(data_js):
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', data_js)
    if not m:
        return None
    ob = data_js.index('{', m.end())
    D, _ = json.JSONDecoder().raw_decode(data_js[ob:])
    months = set()
    for o in D.get('mol_perf', {}).values():
        if isinstance(o, dict):
            for p in o.get('products', []):
                months.update(p.get('monthly_vals', {}).keys())
    parsed = [x for x in (parse_month(k) for k in months) if x]
    return max(parsed) if parsed else None


def gap_months(a, b):
    return (b[0] * 12 + b[1]) - (a[0] * 12 + a[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='no escribe; falla si alguna etiqueta esta ausente o desactualizada')
    args = ap.parse_args()

    changed = 0
    for page_rel, data_rel in PAGES:
        page = REPO / page_rel
        data = REPO / data_rel
        if not page.is_file() or not data.is_file():
            add('SKIP', page_rel, 'falta la pagina o el data.js')
            continue
        html = page.read_text(encoding='utf-8', errors='replace')
        ddd = ddd_last_month(html, page)
        iq = iqvia_last_month(data.read_text(encoding='utf-8-sig', errors='replace'))
        if not ddd or not iq:
            add('SKIP', page_rel,
                f'no derivo fechas (ddd={ddd and fmt(ddd)}, iqvia={iq and fmt(iq)})')
            continue

        g = gap_months(ddd, iq)
        if g > 0:
            txt = (f'DDD al {fmt(ddd)} · Mercado IQVIA al {fmt(iq)} '
                   f'({g} mes{"es" if g > 1 else ""} de diferencia)')
        else:
            txt = f'DDD al {fmt(ddd)} · al día con Mercado IQVIA'
        span = f'<span class="frescura-ddd"> · {txt}</span>'

        if not HERO_RE.search(html):
            add('SKIP', page_rel, 'la pagina no tiene <div class="hero-sub">')
            continue

        def repl(m):
            body = SPAN_RE.sub('', m.group(2))
            return m.group(1) + body + span + m.group(3)

        new = HERO_RE.sub(repl, html, count=1)
        if new == html:
            add('PASS', page_rel, f'ya rotulada: {txt}')
        elif args.check:
            add('FAIL', page_rel, f'etiqueta ausente o desactualizada; deberia decir: {txt}')
        else:
            page.write_text(new, encoding='utf-8', newline='')
            changed += 1
            add('PASS', page_rel, f'rotulada: {txt}')

    n_fail = sum(1 for s, _, _ in results if s == 'FAIL')
    n_skip = sum(1 for s, _, _ in results if s == 'SKIP')
    n_pass = sum(1 for s, _, _ in results if s == 'PASS')
    print('\n' + '=' * 70)
    print(f'label-ddd-frescura: {n_pass} PASS  {n_fail} FAIL  {n_skip} SKIP  '
          f'({changed} paginas escritas)')
    print('=' * 70)
    if n_skip:
        print('\nSIN ROTULAR (declarado, no silencioso):')
        for s, n, d in results:
            if s == 'SKIP':
                print(f'  SKIP {n}: {d}')
    return 1 if n_fail else 0


if __name__ == '__main__':
    sys.exit(main())
