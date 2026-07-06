"""Detecta familias de mol_perf que FUSIONAN >=2 mercados distintos de la fuente
(el bug ROXOLAN = rosuvastatina + rosuvastatina+ezetimibe, jun-2026).

Para cada linea con <linea>/DDD/competidores-data.js (window.SFG_COMP_DATA):
  - Mapea cada marca SIE -> su mercado de la fuente (campo 'brands' por mercado).
  - Por cada familia de mol_perf, junta los mercados-fuente de sus productos SIE.
  - Si una familia tiene SIE de >=2 mercados-fuente distintos -> FLAG (posible fusion).

Esto NO es prueba definitiva (algunos splits finos son intencionales), pero
señala dónde mirar. Correr tras cualquier sync/rebuild de IQVIA.

Uso: py shared/check-mercados-fuente.py
Exit 0 siempre (es un reporte; revisar manualmente los flags).
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('cardio', 'cardio/data.js', False, 'cardio/DDD/competidores-data.js'),
    ('ATB', 'ATB/data.js', False, 'ATB/DDD/competidores-data.js'),
    ('OTC', 'OTC/data.js', False, 'OTC/DDD/competidores-data.js'),
    ('respi', 'respiratorio/data.js', False, 'respiratorio/DDD/competidores-data.js'),
    ('mujer', 'mujer/data.js', False, 'mujer/DDD/competidores-data.js'),
    ('SNC', 'SNC/data.js', False, 'SNC/DDD/competidores-data.js'),
    ('derma', 'dermatologia/data.js', False, 'dermatologia/competidores-data.js'),
]


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'\([^)]*\)', '', str(s)).upper()).strip()


def loadD(path, inline):
    # Robusto: acepta data.js (window.OTC_DASHBOARD = {...}) o inline legacy
    # (const D = {...}). Post-migracion F4 las 7 lineas viven en data.js. Falla
    # RUIDOSAMENTE (ValueError) si no encuentra el objeto, para no saltear lineas
    # en silencio ni crashear con un traceback cripptico.
    t = (REPO / path).read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*\{', t) or re.search(r'const\s+D\s*=\s*\{', t)
    if not m:
        raise ValueError(f'no encontre window.OTC_DASHBOARD ni "const D = {{...}}" en {path}')
    ob = t.index('{', m.start())
    return json.JSONDecoder().raw_decode(t[ob:])[0]


def loadC(path):
    p = REPO / path
    if not p.is_file():
        return None
    t = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'window\.SFG_COMP_DATA\s*=\s*', t)
    if not m:
        return None
    return json.JSONDecoder().raw_decode(t[t.index('{', m.end()):])[0]


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    any_flag = False
    load_errors = []
    for name, dp, inline, cp in LINES:
        C = loadC(cp)
        if not C:
            print(f'[{name}] sin competidores-data.js — no se puede chequear')
            continue
        try:
            D = loadD(dp, inline)
        except Exception as e:
            load_errors.append(name)
            print(f'[{name}] ERROR cargando {dp}: {e}')
            continue
        b2m = {}  # marca SIE normalizada -> mercado fuente
        for mk, mo in C.get('markets', {}).items():
            for b in mo.get('brands', []):
                b2m[norm(b)] = mk
        flags = []
        for fam, fo in (D.get('mol_perf') or {}).items():
            mkts = set()
            for p in fo.get('products', []):
                if not p.get('is_sie'):
                    continue
                sm = b2m.get(norm(p.get('prod', '')))
                if sm:
                    mkts.add(sm)
            if len(mkts) > 1:
                flags.append((fam, sorted(mkts)))
        if flags:
            any_flag = True
            print(f'[{name}] FAMILIAS que fusionan >=2 mercados-fuente (REVISAR):')
            for fam, mk in flags:
                print(f'    {fam}: {mk}')
        else:
            print(f'[{name}] OK — ninguna familia fusiona mercados distintos')
    if any_flag:
        print('\nNota: revisar manualmente. Si son moleculas distintas (ej. mono vs combo,')
        print('sildenafil vs tadalafil) -> separar la familia (ver split-cardio-roxolan.py).')
        print('Si es un split fino intencional o adulto/ped no separable -> dejar.')
    if load_errors:
        print(f'\nERROR: no se pudieron cargar {len(load_errors)} linea(s): {load_errors}. '
              'El chequeo NO cubrio esas lineas — revisar.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
