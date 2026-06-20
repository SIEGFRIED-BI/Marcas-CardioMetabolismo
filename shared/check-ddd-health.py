# -*- coding: utf-8 -*-
"""Gate de salud de las páginas DDD (las de mercados-molécula con tabla regional).
Previene las 2 clases de bug que rompieron el DDD (jun-2026):

  1) MERCADO VACÍO: en las páginas con `const D = {markets:...}` inline, un mercado
     con region_data vacío -> al seleccionarlo, tabla de regiones en blanco (y si es
     el default, la página abre rota). [pasó en SNC/cardio/dermato]

  2) app.js FALTANTE: una página DDD que incluye <script src=".../app.js"> cuyo
     archivo no existe -> 404 -> la lógica no carga -> página en blanco. [pasó en ATB]

Uso: py shared/check-ddd-health.py   (exit 1 si hay algo roto)
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DDD_PAGES = [
    'cardio/DDD/index.html', 'ATB/DDD/index.html', 'OTC/DDD/index.html',
    'respiratorio/DDD/index.html', 'mujer/DDD/index.html',
    'SNC/DDD/psq_ddd.html', 'dermatologia/dermato_ddd.html',
]


def inline_D(text):
    """Devuelve el objeto del primer `const D = {` con 'markets', o None."""
    for m in re.finditer(r'const\s+D\s*=\s*\{', text):
        ob = text.index('{', m.start())
        try:
            D, _ = json.JSONDecoder().raw_decode(text[ob:])
        except Exception:
            continue
        if isinstance(D, dict) and 'markets' in D:
            return D
    return None


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    issues = []
    for rel in DDD_PAGES:
        p = REPO / rel
        if not p.is_file():
            issues.append(f'[{rel}] no existe'); continue
        t = p.read_text(encoding='utf-8', errors='replace')

        # 1) app.js (y data.js) referenciados deben existir
        for mt in re.finditer(r'src="([^"]*\.js)(?:\?[^"]*)?"', t):
            ref = mt.group(1)
            if ref.startswith(('http://', 'https://', '//')):
                continue
            target = (p.parent / ref).resolve()
            if not target.is_file():
                issues.append(f'[{rel}] include roto: {ref!r} (archivo no existe -> 404)')

        # 2) mercados con region_data vacío (solo páginas con const D inline)
        D = inline_D(t)
        if D:
            empty = [m for m in D['markets']
                     if len((D['markets'][m].get('region_data') or {})) == 0]
            if empty:
                issues.append(f'[{rel}] {len(empty)} mercado(s) con region_data VACÍO '
                              f'(tabla regional en blanco): {", ".join(empty[:8])}')

    if issues:
        print(f'DDD-HEALTH FAIL ({len(issues)}):')
        for i in issues:
            print('  -', i)
        return 1
    print(f'OK: {len(DDD_PAGES)} páginas DDD sanas (includes resuelven; sin mercados vacíos).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
