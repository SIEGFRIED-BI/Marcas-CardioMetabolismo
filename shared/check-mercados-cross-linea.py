"""Detecta el patron MOMETASONE: un producto is_sie=true en el mol_perf de una
linea que en realidad es una marca de OTRA linea (segun su propio sieProds).

POR QUE HACE FALTA (y por que check-mercados-fuente.py no lo vio):
check-mercados-fuente.py mapea marca-SIE -> mercado-fuente usando el
competidores-data.js DE LA PROPIA LINEA. Si el SIE ajeno ni siquiera aparece
ahi (porque es una marca de OTRA linea, con su PROPIO competidores-data.js
separado), el lookup devuelve None y la marca se saltea en silencio -> nunca
suma a "esta familia tiene SIE de >=2 mercados" y el check da OK.
Exactamente lo que paso: HEXALER NASAL / HEXALER BRONQUIAL (marcas de
RESPIRATORIO) aparecian is_sie=true dentro de mol_perf.MOMETASONE de DERMATO;
check-mercados-fuente.py no las via porque no estan en el competidores-data.js
de dermato. audit-full.py tampoco (no compara sieProds entre lineas). El bug
paso 17.856 checks sin que nada lo marcara.

METODO: sieProds de cada linea es la lista curada de marcas que esa linea
posee (fuente de verdad de "de quien es esta marca"). Para cada producto
is_sie=true en mol_perf de la linea X: si su nombre base (sin sufijo
"(SIE)"/"(SIEGFRIED)") aparece en el sieProds de OTRA linea Y, Y NO en el de
la propia X -> FLAG. Es deterministico y no necesita leer el master IQVIA.

ESTO ES UN REPORTE, NO UN FIX. Un hallazgo puede ser:
  (a) el bug real (una molecula que IQVIA junta pero que corresponde a
      formas farmaceuticas/mercados distintos -> split por ATC, ver
      shared/split-mometasone-atc.py como plantilla), o
  (b) dos lineas legitimamente compitiendo en el MISMO mercado real (menos
      probable dado como esta organizado el negocio, pero no se descarta a
      priori) -> no tocar.
Cada hallazgo se verifica a mano contra el master ANTES de decidir un split.

Uso: py shared/check-mercados-cross-linea.py
Exit 0 siempre (reporte). Correr tras cualquier sync/rebuild/onboarding de
mol_perf o cambio de sieProds.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINES = [
    ('cardio', 'cardio/data.js'),
    ('ATB', 'ATB/data.js'),
    ('OTC', 'OTC/data.js'),
    ('respi', 'respiratorio/data.js'),
    ('mujer', 'mujer/data.js'),
    ('SNC', 'SNC/data.js'),
    ('derma', 'dermatologia/data.js'),
]


def base_name(prod):
    """'HEXALER NASAL (SIE)' -> 'HEXALER NASAL'. Igual normalizacion que el
    resto del repo (sufijo entre parentesis del manufacturer)."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(prod)).strip().upper()


def load_D(path):
    t = (REPO / path).read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*\{', t) or re.search(r'const\s+D\s*=\s*\{', t)
    if not m:
        raise ValueError(f'no encontre window.OTC_DASHBOARD ni "const D = {{...}}" en {path}')
    ob = t.index('{', m.start())
    return json.JSONDecoder().raw_decode(t[ob:])[0]


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    loaded, load_errors = {}, []
    for name, path in LINES:
        try:
            loaded[name] = load_D(path)
        except Exception as e:
            load_errors.append(name)
            print(f'[{name}] ERROR cargando {path}: {e}')

    # sieProds de cada linea (base_name normalizado) -> set
    sieprods = {name: {base_name(b) for b in (D.get('sieProds') or [])}
               for name, D in loaded.items()}

    # marca(base_name) -> lista de lineas dueñas (segun sieProds)
    owner = {}
    for name, brands in sieprods.items():
        for b in brands:
            owner.setdefault(b, []).append(name)

    dupes = {b: ls for b, ls in owner.items() if len(ls) > 1}
    if dupes:
        print('AVISO: marcas que aparecen en el sieProds de MAS DE UNA linea (revisar si es intencional):')
        for b, ls in sorted(dupes.items()):
            print(f'    {b}: {ls}')
        print()

    any_flag = False
    for name, D in loaded.items():
        flags = []
        own = sieprods.get(name, set())
        for fam, fo in (D.get('mol_perf') or {}).items():
            if not isinstance(fo, dict):
                continue
            for p in fo.get('products', []):
                if not p.get('is_sie'):
                    continue
                b = base_name(p.get('prod', ''))
                if b in own:
                    continue
                otras = [ln for ln, brands in sieprods.items() if ln != name and b in brands]
                if otras:
                    flags.append((fam, p.get('prod'), otras))
        if flags:
            any_flag = True
            print(f'[{name}] marcas SIE de OTRA linea dentro de su mol_perf (REVISAR):')
            for fam, prod, otras in flags:
                print(f'    mol_perf[{fam}] tiene {prod!r} is_sie=true, pero pertenece a: {otras}')
        else:
            print(f'[{name}] OK — ningun SIE ajeno en su mol_perf')

    if any_flag:
        print('\nNota: verificar el ATC real de cada producto contra el master IQVIA antes de')
        print('decidir un split (puede ser el bug real -> split por ATC, ver split-mometasone-atc.py;')
        print('o una molecula que 2 lineas legitimamente comparten -> no tocar sin confirmar).')
    if load_errors:
        print(f'\nERROR: no se pudieron cargar {len(load_errors)} linea(s): {load_errors}. '
              'El chequeo NO cubrio esas lineas — revisar.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
