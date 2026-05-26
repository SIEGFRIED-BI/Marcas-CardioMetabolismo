"""Renombra 'Presupuesto'/'presupuesto' -> 'Estimado de Ventas'/'estimado de ventas'
en los user-facing labels de las 7 lineas.

Solo toca TEXTO en strings (labels JS, comentarios HTML, page subtitles, copys).
NO toca nombres de campos JS como D.budget, bud_total, var budget, etc.
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
    'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]

# Solo reemplazos en TEXTO (no en identificadores). Usamos delimitadores claros
# para asegurar que solo cambiamos strings.
REPLACEMENTS = [
    # Page subtitle "IE · MS% · ... · Presupuesto · ..."
    ('· Presupuesto ·', '· Estimado Vtas ·'),
    # KPI label "Presupuesto · 2026" (template literals + string literals)
    ("'Presupuesto · ", "'Estimado · "),
    ('"Presupuesto · ', '"Estimado · '),
    ('`Presupuesto · ', '`Estimado · '),
    # JS check label.indexOf('Presupuesto')
    ("indexOf('Presupuesto')", "indexOf('Estimado')"),
    # Bud copy "...vs presupuesto planificado..."
    ('vs presupuesto planificado', 'vs estimado de ventas planificado'),
    # Sin datos budget
    ("'Sin datos budget'", "'Sin datos de estimado'"),
]


def patch_file(path: Path):
    t = path.read_text(encoding='utf-8', errors='replace')
    orig = t
    changes = []
    for old, new in REPLACEMENTS:
        n = t.count(old)
        if n > 0:
            t = t.replace(old, new)
            changes.append(f'{old!r}->{new!r} ({n})')
    if t == orig:
        return f'{path.name}: no changes'
    path.write_text(t, encoding='utf-8', newline='')
    return f'{path.name}: ' + '; '.join(changes)


def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    for f in FILES:
        p = REPO / f
        if not p.is_file():
            print(f'  MISS: {f}'); continue
        print(f'  {patch_file(p)}')


if __name__ == '__main__':
    main()
