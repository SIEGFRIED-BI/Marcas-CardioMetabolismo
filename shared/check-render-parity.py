# -*- coding: utf-8 -*-
"""Gate anti-regresion del render compartido (F3).

Las funciones de render que se movieron a shared/render/*.js deben existir en
UN SOLO lugar: el bundle compartido. Este gate bloquea la regresion clasica
"alguien vuelve a copiar la funcion inline en una pagina" (que es justo lo que
F3 elimina: el fix-7-veces).

Para cada archivo shared/render/*.js:
  1) descubre las funciones top-level que define (function NOMBRE(...)).
Para cada una de las 7 paginas:
  2) NINGUNA de esas funciones puede estar definida inline (function NOMBRE().
  3) la pagina DEBE incluir el bundle (<script src=".../render/<archivo>").

Uso: py shared/check-render-parity.py   (exit 1 si hay regresion)
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RENDER_DIR = REPO / 'shared' / 'render'
PAGES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html',
]


def shared_bundles():
    """{archivo.js: [funciones top-level que define]}."""
    out = {}
    if not RENDER_DIR.is_dir():
        return out
    for p in sorted(RENDER_DIR.glob('*.js')):
        t = p.read_text(encoding='utf-8', errors='replace')
        fns = re.findall(r'(?m)^function\s+([A-Za-z_$][\w$]*)\s*\(', t)
        if fns:
            out[p.name] = fns
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    bundles = shared_bundles()
    if not bundles:
        print('OK: no hay shared/render/*.js con funciones (nada que custodiar).')
        return 0
    all_fns = {fn for fns in bundles.values() for fn in fns}
    issues = []
    for rel in PAGES:
        p = REPO / rel
        if not p.is_file():
            issues.append(f'[{rel}] no existe'); continue
        t = p.read_text(encoding='utf-8', errors='replace')
        # 2) no redefinir inline. Match 'function NOMBRE(' en cualquier posicion:
        # las LLAMADAS (renderCobertura();) no llevan 'function' antes -> sin falso
        # positivo; solo una DEFINICION re-pegada dispara.
        for fn in sorted(all_fns):
            if re.search(r'function\s+' + re.escape(fn) + r'\s*\(', t):
                issues.append(f'[{rel}] redefine inline {fn!r} (debe venir solo del bundle shared/render/)')
        # 3) incluir cada bundle
        for js in bundles:
            if f'render/{js}' not in t:
                issues.append(f'[{rel}] no incluye el bundle shared/render/{js}')
    if issues:
        print(f'RENDER-PARITY FAIL ({len(issues)}):')
        for i in issues:
            print('  -', i)
        return 1
    nfn = sum(len(v) for v in bundles.values())
    print(f'OK: {nfn} funcion(es) de render en {len(bundles)} bundle(s) shared/render/; '
          f'ninguna redefinida inline; las {len(PAGES)} paginas incluyen el/los bundle(s).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
