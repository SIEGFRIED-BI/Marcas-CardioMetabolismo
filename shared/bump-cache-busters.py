"""Pone/actualiza el cache-buster ?v=<hash> en las referencias a data.js y a los
assets compartidos (shared/*.js, shared/*.css) de todas las paginas.

El ?v se deriva del HASH DEL CONTENIDO de cada archivo:
  - Si el archivo cambia -> el hash cambia -> el navegador/CDN baja la version nueva.
  - Si no cambia -> el hash es igual -> sin diff espurio.

Esto evita el bug clasico: editar data.js y olvidarse de bumpear ?v, dejando que
el navegador sirva la version vieja cacheada.

Correr al final de cualquier actualizacion (build-all.ps1 ya lo invoca; el
pre-commit hook tambien lo corre y re-stagea). Idempotente.

Uso: py shared/bump-cache-busters.py [--check]
  --check: no escribe; sale con codigo !=0 si algun ?v esta desactualizado
           (lo usa el pre-commit hook como red de seguridad).
"""
from __future__ import annotations
import hashlib, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Paginas que referencian data.js propio y/o assets compartidos.
PAGES = [
    'cardio/index.html', 'ATB/index.html', 'OTC/index.html',
    'respiratorio/index.html', 'mujer/index.html', 'SNC/index.html',
    'dermatologia/dermato_dashboard.html', 'kpis.html', 'index.html',
]

# Assets compartidos a cache-bustear (los que existan).
SHARED_ASSETS = [
    'multi-period-table.js', 'multi-period-table.css',
    'budget-overrides.js', 'ux-shared.js', 'data-status.js',
    'export-pdf.js', 'export-common.js', 'export-dashboard.js', 'export-ddd.js',
    'resize-cols.js', 'design-tokens.css', 'microinteractions.css', 'responsive.css',
]


def fhash(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:10]


def process(text: str, page_path: Path) -> str:
    page_dir = page_path.parent
    # 1) data.js propio de la pagina (lineas con archivo separado)
    dj = page_dir / 'data.js'
    if dj.is_file():
        v = fhash(dj)
        # match ./data.js  o  data.js  con o sin ?v= previo
        text = re.sub(r'(\.?/?data\.js)(\?v=[0-9A-Za-z]+)?',
                      lambda m: m.group(1) + '?v=' + v, text)
    # 2) assets compartidos
    for a in SHARED_ASSETS:
        ap = REPO / 'shared' / a
        if not ap.is_file():
            continue
        v = fhash(ap)
        text = re.sub(r'(shared/' + re.escape(a) + r')(\?v=[0-9A-Za-z]+)?',
                      lambda m, vv=v: m.group(1) + '?v=' + vv, text)
    return text


def main():
    check = '--check' in sys.argv
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    changed, stale = [], []
    for rel in PAGES:
        p = REPO / rel
        if not p.is_file():
            continue
        orig = p.read_text(encoding='utf-8', errors='replace')
        new = process(orig, p)
        if new != orig:
            if check:
                stale.append(rel)
            else:
                p.write_text(new, encoding='utf-8', newline='')
                changed.append(rel)
    if check:
        if stale:
            print('CACHE-BUSTER DESACTUALIZADO en:', ', '.join(stale))
            print('Corre: py shared/bump-cache-busters.py')
            return 1
        print('cache-busters OK')
        return 0
    print(f'cache-busters actualizados en {len(changed)} pagina(s): {changed}' if changed
          else 'cache-busters ya estaban al dia (sin cambios)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
