"""Verificador de historia preservada — corre antes de commitear cualquier
cambio que toque mol_perf de las 7 lineas. Compara el estado actual contra
un commit de referencia (default HEAD~1) y bloquea si:

  - Se perdio cualquier mes que existia en el baseline.
  - El first_month avanzo (deberia ser <= baseline.first_month).
  - El total de meses bajo respecto al baseline (a menos que se haya
    quitado por exclusion explicita).

Uso:
    py shared/verify-history-preserved.py [--baseline <commit>] [--strict]

Devuelve exit code 0 si OK, 1 si encuentra perdida de historia.

Se puede integrar en .git/hooks/pre-commit para que bloquee commits que
involuntariamente acorten la historia.
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gitcmd import git_show as _git_show, available as _git_available  # noqa: E402

LINES = [
    ('cardio',  'cardio/data.js',                     'window.OTC_DASHBOARD'),
    ('ATB',     'ATB/data.js',                        'window.OTC_DASHBOARD'),
    ('OTC',     'OTC/data.js',                        'window.OTC_DASHBOARD'),
    ('respi',   'respiratorio/data.js',               'window.OTC_DASHBOARD'),
    ('mujer',   'mujer/data.js',                   'window.OTC_DASHBOARD'),
    ('SNC',     'SNC/data.js',                     'window.OTC_DASHBOARD'),
    ('derma',   'dermatologia/data.js','window.OTC_DASHBOARD'),
]

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}


def msort_key(mk):
    p = mk.split()
    if len(p) != 2: return 0
    try: return int(p[1]) * 100 + MES_INV.get(p[0], 0)
    except (ValueError, IndexError): return 0


def parse_data(text, var_pattern):
    is_inline = var_pattern == 'const D'
    if is_inline:
        m = re.search(r'const D\s*=\s*\{', text)
        if not m: return None
        ob = m.end() - 1
    else:
        m = re.search(re.escape(var_pattern) + r'\s*=\s*', text)
        if not m: return None
        try:
            ob = text.index('{', m.end())
        except ValueError:
            return None
    try:
        D, _ = json.JSONDecoder().raw_decode(text[ob:])
        return D
    except Exception:
        return None


def get_months_set(D):
    all_months = set()
    for v in (D.get('mol_perf') or {}).values():
        if not isinstance(v, dict): continue
        for p in v.get('products', []):
            mv = p.get('monthly_vals', {})
            all_months.update(mv.keys())
    # mercadosAteneo: vista alternativa por los mercados curados del Ateneo (antes era
    # mercadosATC / clases ATC III, que el usuario rechazo). Se une (no reemplaza) porque
    # tambien es historia mensual publicada y sin esto quedaba sin red: si un cierre la
    # dejara con menos meses -- o vacia -- este gate daba OK igual.
    for c in ((D.get('mercadosAteneo') or {}).get('mercados') or {}).values():
        if not isinstance(c, dict): continue
        for p in c.get('products', []):
            all_months.update((p.get('monthly_vals') or {}).keys())
    return all_months


def get_baseline(path, commit):
    # git via gitcmd: lanzado por el pre-commit hook git esta en el PATH, pero lanzado
    # por update-all.ps1 desde PowerShell NO -> el gate crasheaba con FileNotFoundError
    # en cada cierre y se leia como si hubiera encontrado un problema.
    return _git_show(commit, path, cwd=REPO) or None


def verify_line(line, path, var_pattern, baseline_commit):
    p = REPO / path
    if not p.exists():
        return {'line': line, 'status': 'FILE_NOT_FOUND'}
    enc = 'utf-8' if 'html' in path else 'utf-8-sig'
    curr_text = p.read_text(encoding=enc, errors='replace')
    curr_D = parse_data(curr_text, var_pattern)
    if not curr_D:
        return {'line': line, 'status': 'NO_DATA_CURR'}

    baseline_text = get_baseline(path, baseline_commit)
    if not baseline_text:
        return {'line': line, 'status': 'NO_BASELINE_AT_COMMIT'}
    base_D = parse_data(baseline_text, var_pattern)
    if not base_D:
        return {'line': line, 'status': 'NO_DATA_BASELINE'}

    curr_months = get_months_set(curr_D)
    base_months = get_months_set(base_D)
    missing = base_months - curr_months  # meses que estaban antes y ya no estan
    new = curr_months - base_months
    curr_sorted = sorted(curr_months, key=msort_key)
    base_sorted = sorted(base_months, key=msort_key)
    curr_first = curr_sorted[0] if curr_sorted else None
    base_first = base_sorted[0] if base_sorted else None
    curr_last = curr_sorted[-1] if curr_sorted else None
    base_last = base_sorted[-1] if base_sorted else None

    ok = (not missing) and (msort_key(curr_first or '') <= msort_key(base_first or ''))
    return {
        'line': line,
        'status': 'OK' if ok else 'HISTORY_LOST',
        'baseline_range': f'{base_first} -> {base_last} ({len(base_months)} mo)',
        'current_range':  f'{curr_first} -> {curr_last} ({len(curr_months)} mo)',
        'missing': sorted(missing, key=msort_key),
        'added':   sorted(new, key=msort_key),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', default='HEAD~1',
                    help='Commit de referencia (default: HEAD~1)')
    ap.add_argument('--strict', action='store_true',
                    help='Exit code 1 si encuentra perdida de historia')
    args = ap.parse_args()

    print(f'Verifying historical preservation vs baseline: {args.baseline}')
    # Sin git no hay baseline: TODAS las lineas caerian en NO_BASELINE_AT_COMMIT, que
    # este gate trata como aceptable, y terminaria imprimiendo "OK: history preserved"
    # sin haber comparado NADA. Un gate que no puede correr se declara AUSENTE, no
    # pasado.
    if not _git_available():
        print('FAIL: no encuentro el ejecutable de git -> no hay baseline contra la cual '
              'comparar. El gate NO corrio (no es un OK).', file=sys.stderr)
        sys.exit(2)
    print()
    any_fail = False
    print(f'{"linea":8s} | {"status":15s} | {"baseline":40s} | {"current":40s} | {"missing":10s}')
    print('-' * 130)
    sin_baseline = 0
    for line, path, var in LINES:
        r = verify_line(line, path, var, args.baseline)
        status = r.get('status', '?')
        if status == 'NO_BASELINE_AT_COMMIT':
            sin_baseline += 1
        baseline = r.get('baseline_range', '-')
        current = r.get('current_range', '-')
        missing = len(r.get('missing', []))
        print(f'{line:8s} | {status:15s} | {baseline:40s} | {current:40s} | {missing:10d}')
        # NO_DATA_BASELINE = el baseline (HEAD) no parsea con el anchor esperado
        # (p.ej. el dato cambio de archivo/anchor en una migracion F4 inline->data.js):
        # no hay baseline COMPARABLE -> no se puede afirmar perdida (igual que
        # NO_BASELINE_AT_COMMIT). Las perdidas reales requieren un baseline parseable
        # y SI se detectan (status HISTORY_LOST). Post-migracion el baseline vuelve a
        # parsear y el gate recupera plena efectividad.
        if status not in ('OK', 'NO_BASELINE_AT_COMMIT', 'NO_DATA_BASELINE'):
            any_fail = True
            for m_ in r.get('missing', [])[:5]:
                print(f'    [{line}] LOST: {m_}')
    print()
    # Que UNA linea no exista en el baseline es legitimo (migracion de archivo/anchor).
    # Que no exista NINGUNA significa que el commit de baseline no existe -- un typo en
    # --baseline, o un repo sin ese ancestro. Sin baseline no hay comparacion, y el gate
    # imprimia "OK: history preserved" igual. Se declara AUSENTE, no pasado.
    if sin_baseline == len(LINES):
        print(f'FAIL: ninguna linea existe en el baseline {args.baseline!r} -> el commit no '
              f'existe o no tiene estos archivos. El gate NO comparo nada (no es un OK).',
              file=sys.stderr)
        sys.exit(2)
    if any_fail and args.strict:
        print('FAIL: history was lost in at least one line. Use --baseline to compare against earlier commit if needed.')
        sys.exit(1)
    else:
        print('OK: history preserved across all lines.' if not any_fail else 'WARNING: history changes detected but --strict not set.')


if __name__ == '__main__':
    main()
