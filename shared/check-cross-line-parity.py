# -*- coding: utf-8 -*-
"""Gate de paridad entre lineas: las 7 deben compartir el mismo set de keys CORE
en su objeto vivo + las mismas keys de etiquetas en meta. Atrapa la clase de bug
'a una linea le falta rec_label / kpiStrip / etc.' que desincroniza el render.

NO exige igualdad total (las 4 data.js y las 3 inline difieren legitimamente en
estructura); exige que el NUCLEO comun este presente en todas.

Uso: py shared/check-cross-line-parity.py   (exit 1 si falta algo)
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FILES = {
    'cardio': 'cardio/data.js', 'ATB': 'ATB/data.js', 'OTC': 'OTC/data.js',
    'respiratorio': 'respiratorio/data.js', 'SNC': 'SNC/index.html',
    'derma': 'dermatologia/dermato_dashboard.html', 'mujer': 'mujer/index.html',
}
ANCHORS = [r'window\.OTC_DASHBOARD\s*=\s*', r'const\s+D\s*=\s*']

# Nucleo comun que TODAS las lineas deben tener (verificado jun-2026).
CORE_TOP = ['mol_perf', 'budget', 'meta', 'kpiStrip']
CORE_META = ['kpi_ytd_label', 'kpi_ytd_prev_label', 'kpi_mat_label',
             'kpi_mat_prev_label', 'budget_label', 'rec_label', 'footer_date']


def load_live(text):
    for anc in ANCHORS:
        for m in re.finditer(anc, text):
            try:
                ob = text.index('{', m.end())
                obj, _ = json.JSONDecoder().raw_decode(text[ob:])
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(obj, dict) and obj.get('mol_perf'):
                return obj
    return None


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    issues = []
    for line, rel in FILES.items():
        p = REPO / rel
        if not p.is_file():
            issues.append(f'[{line}] no existe {rel}'); continue
        D = load_live(p.read_text(encoding='utf-8', errors='replace'))
        if not D:
            issues.append(f'[{line}] no se pudo parsear el objeto vivo'); continue
        for k in CORE_TOP:
            if k not in D:
                issues.append(f'[{line}] falta key top-level CORE: {k!r}')
        meta = D.get('meta', {}) or {}
        for k in CORE_META:
            if k not in meta:
                issues.append(f'[{line}] meta sin label CORE: {k!r}')
    if issues:
        print(f'CROSS-LINE PARITY FAIL ({len(issues)}):')
        for i in issues:
            print('  -', i)
        return 1
    print(f'OK: las {len(FILES)} lineas comparten el nucleo comun '
          f'(top={CORE_TOP}, meta labels={len(CORE_META)}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
