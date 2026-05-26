"""Remueve la tabla 'SIE · Evolución mensual / SIE vs Mercado · Total Anual'
del lado derecho de la seccion Recetas en las 7 lineas.

Cambios por linea:
  1. HTML: <div class="card-sm" id="rec-detail"></div> -> oculto display:none
     (asi el JS sigue pudiendo setear .innerHTML sin errores)
  2. HTML: <div class="g2">...recChart + rec-detail</div> -> sin grid 2-col,
     el chart usa todo el ancho.

Idempotente: si rec-detail ya esta hidden, no hace nada.

NO modifica el JS que renderiza la tabla — simplemente la oculta. Si en
el futuro se quiere volver a mostrar, sacar el display:none.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FILES = [
    'cardio/index.html',
    'ATB/index.html',
    'OTC/index.html',
    'respiratorio/index.html',
    'mujer/index.html',
    # SNC EXCLUIDO a pedido del usuario: en SNC se mantiene el grafico/tabla
    # 'SIE · Evolucion mensual / SIE vs Mercado · Total Anual' visible.
    'dermatologia/dermato_dashboard.html',
]


def patch_file(path: Path):
    t = path.read_text(encoding='utf-8', errors='replace')
    orig = t
    changes = []

    # 1. Buscar el div con id="rec-detail" y ponerle display:none
    #    Si ya tiene display:none, skip.
    pat_rd = re.compile(r'<div class="card-sm" id="rec-detail"([^>]*)></div>')
    m = pat_rd.search(t)
    if m:
        attrs = m.group(1)
        if 'display:none' in attrs:
            changes.append('rec-detail: already hidden')
        else:
            new_div = '<div class="card-sm" id="rec-detail" style="display:none;"></div>'
            t = t.replace(m.group(0), new_div)
            changes.append('rec-detail: hidden')
    else:
        changes.append('rec-detail: NOT FOUND')

    # 2. Buscar el g2 que contiene el recChart + rec-detail y hacer que el
    #    chart use todo el ancho. Patron tipico:
    #    <div class="g2">
    #      <div><div class="chart-h280"><canvas id="recChart"></canvas></div></div>
    #      <div class="card-sm" id="rec-detail" ...></div>
    #    </div>
    #
    # En vez de tocar el grid (que afecta layout), simplemente seteamos
    # grid-template-columns:1fr inline en ese g2 especifico via wrapper id.
    # Pero mas simple: agregamos un style attribute al g2 que rodea al recChart.
    pat_g2 = re.compile(
        r'(<div class="g2">\s*<div><div class="chart-h280"><canvas id="recChart">)',
        re.MULTILINE
    )
    m2 = pat_g2.search(t)
    if m2:
        # Verificar que no esta ya tocado
        before = t[:m2.start()]
        # check if any g2 directly preceding has the override style
        if 'data-rec-fullwidth' in t[max(0,m2.start()-100):m2.start()+50]:
            changes.append('g2: already full-width')
        else:
            replacement = '<div class="g2" data-rec-fullwidth style="grid-template-columns:1fr !important;"><div><div class="chart-h280"><canvas id="recChart">'
            t = t.replace(m2.group(0), replacement)
            changes.append('g2: full-width')
    else:
        changes.append('g2: NOT FOUND or different shape')

    if t == orig:
        return f'{path.name}: no changes ({"; ".join(changes)})'
    path.write_text(t, encoding='utf-8', newline='')
    return f'{path.name}: {"; ".join(changes)}'


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  MISS: {f}'); continue
        print(f'  {patch_file(p)}')


if __name__ == '__main__':
    main()
