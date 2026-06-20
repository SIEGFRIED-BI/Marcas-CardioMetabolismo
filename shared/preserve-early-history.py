# -*- coding: utf-8 -*-
"""Re-inyecta los meses pre-ventana de mol_perf que los sync borran (SNC/derma/mujer).

El master IQVIA trae una ventana movil (~60 meses). Al re-sincronizar mol_perf, los
meses mas viejos que el master ya no incluye (p.ej. Abr/May 2021 en SNC/derma,
Mar/Abr/May 2021 en mujer) se pierden -> verify-history-preserved FALLA (regla #7:
los merges AGREGAN meses, nunca reemplazan). Esto los recupera desde git HEAD (el
commit anterior que SI los tiene) y los vuelve a poner en monthly_vals de cada
producto + monthly de la familia.

Idempotente: si los meses ya estan, no toca nada (0 re-inyectados). Correr DESPUES de
los syncs/rebuilds y ANTES de recompute-mol-perf-aggregates (que recomputa ytd/mat/ms
incluyendo los meses re-inyectados).

Uso: py shared/preserve-early-history.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Solo las inline (const D): son las de historia larga que el sync recorta.
# Las data.js (cardio/ATB/OTC/respi) tienen ventana Feb-2024+ -> no sufren esto.
FILES = ['SNC/data.js', 'dermatologia/data.js', 'mujer/data.js']


def load_D(text):
    m = re.search(r'(?:const\s+D|window\.OTC_DASHBOARD)\s*=\s*', text)
    if not m:
        return None, None, None
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    return D, ob, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    total = 0
    for rel in FILES:
        p = REPO / rel
        if not p.is_file():
            print(f'  (skip) {rel}: no existe'); continue
        text = p.read_text(encoding='utf-8', errors='replace')
        D, ob, end = load_D(text)
        if D is None:
            print(f'  (skip) {rel}: sin const D'); continue
        old_raw = subprocess.run(['git', 'show', f'HEAD:{rel}'],
                                 capture_output=True, cwd=str(REPO)).stdout.decode('utf-8', 'replace')
        if not old_raw:
            print(f'  (skip) {rel}: sin version en HEAD'); continue
        OD, _, _ = load_D(old_raw)
        if OD is None:
            print(f'  (skip) {rel}: HEAD sin const D'); continue
        omp = OD.get('mol_perf', {}) or {}
        added = 0
        for fam, f in (D.get('mol_perf', {}) or {}).items():
            of = omp.get(fam)
            if not isinstance(of, dict):
                continue
            # nivel familia
            for mth, v in (of.get('monthly') or {}).items():
                if mth not in (f.get('monthly') or {}):
                    f.setdefault('monthly', {})[mth] = v; added += 1
            # nivel producto (match por nombre)
            oprods = {pp.get('prod'): pp for pp in (of.get('products') or [])}
            for pr in (f.get('products') or []):
                op = oprods.get(pr.get('prod'))
                if not op:
                    continue
                for mth, v in (op.get('monthly_vals') or {}).items():
                    if mth not in (pr.get('monthly_vals') or {}):
                        pr.setdefault('monthly_vals', {})[mth] = v; added += 1
        total += added
        print(f'  {rel}: {added} valores re-inyectados' + (' (dry-run)' if a.dry_run else ''))
        if added and not a.dry_run:
            p.write_text(text[:ob] + json.dumps(D, ensure_ascii=False) + text[ob + end:],
                         encoding='utf-8', newline='')
    print(f'TOTAL: {total} valores' + (' (nada que hacer, historia OK)' if total == 0 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
