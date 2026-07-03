# DEPRECADO (jul-2026): NINGUN orquestador lo invoca. Lee mujer/index.html PRE-F4
# (const D inline), que ya no existe (mujer migro a mujer/data.js /
# window.OTC_DASHBOARD en commit ebf0c2f) -> hoy fallaria. La consolidacion ya
# esta horneada en mujer/data.js y se preserva via sync-mujer-pm.py. Se conserva
# como referencia; si se reactiva, migrar a data.js/OTC_DASHBOARD primero.
"""Consolida los 3 SKUs de ISIS en mol_perf['ALTA DOSIS'] de mujer en un solo
producto brand-level 'ISIS (SIE)', para mantener consistencia con el resto:

Antes (3 entries, SKU level):
  'ISIS TABL RECUBIE 3.00MG x 28 /.03'
  'ISIS TABL RECUBIE 3.00MG x 84 /.03'
  'ISIS TABL RECUBIE 3.00MG x 56 /.03'

Despues (1 entry, brand level — consistente con ISIS MINI / ISIS MINI 24 / etc):
  'ISIS (SIE)'

Logica:
- Suma monthly_vals, quarterly_vals, ytd, mat (unidades aditivas).
- Suma ms_monthly, ms_quarterly, ms_ytd, ms_mat (share aditivo dentro del
  mismo mercado).
- Mantiene manuf, is_sie del primer producto.

Idempotente. Re-build de kpis.json y sync a kpiStrip se debe correr despues.
"""
from __future__ import annotations
import re, json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
FILE = REPO / 'mujer' / 'index.html'


def merge_dicts_sum(*dicts):
    """Sum values across multiple dicts. Keys union."""
    out = defaultdict(float)
    for d in dicts:
        if not isinstance(d, dict): continue
        for k, v in d.items():
            try:
                out[k] += float(v) if v is not None else 0
            except (TypeError, ValueError):
                pass
    # Round to int if all dicts had integer-typed values
    out2 = {}
    for k, v in out.items():
        if v == int(v):
            out2[k] = int(v)
        else:
            out2[k] = round(v, 2)
    return out2


def main():
    t = FILE.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const D\s*=\s*\{', t)
    if not m:
        print('  ERROR: no const D found in mujer/index.html')
        return
    ob = m.end() - 1
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    prefix = t[:ob]
    suffix = t[ob + end:]

    mol = D.get('mol_perf', {})
    alta = mol.get('ALTA DOSIS')
    if not alta or not isinstance(alta, dict):
        print('  ERROR: ALTA DOSIS not found in mol_perf')
        return

    prods = alta.get('products', [])
    isis_skus = []
    other_prods = []
    isis_consolidated_existing = None
    for p in prods:
        nm = p.get('prod', '')
        if p.get('is_sie') and re.match(r'^ISIS TABL RECUBIE', nm):
            isis_skus.append(p)
        elif nm == 'ISIS (SIE)':
            isis_consolidated_existing = p
        else:
            other_prods.append(p)

    if not isis_skus:
        print('  no SKU-level ISIS found — already consolidated or no data')
        return

    # Build consolidated product
    consolidated = {
        'prod': 'ISIS (SIE)',
        'manuf': isis_skus[0].get('manuf', 'SIEGFRIED'),
        'is_sie': True,
        'monthly_vals': merge_dicts_sum(*(p.get('monthly_vals', {}) for p in isis_skus)),
        'quarterly_vals': merge_dicts_sum(*(p.get('quarterly_vals', {}) for p in isis_skus)),
        'ytd': merge_dicts_sum(*(p.get('ytd', {}) for p in isis_skus)),
        'mat': merge_dicts_sum(*(p.get('mat', {}) for p in isis_skus)),
        'ms_ytd': merge_dicts_sum(*(p.get('ms_ytd', {}) for p in isis_skus)),
        'ms_mat': merge_dicts_sum(*(p.get('ms_mat', {}) for p in isis_skus)),
        'ms_monthly': merge_dicts_sum(*(p.get('ms_monthly', {}) for p in isis_skus)),
        'ms_quarterly': merge_dicts_sum(*(p.get('ms_quarterly', {}) for p in isis_skus)),
    }

    # Replace products array: keep non-ISIS, add consolidated at top
    new_products = [consolidated] + other_prods
    alta['products'] = new_products

    # Write back
    new_t = prefix + json.dumps(D, ensure_ascii=False) + suffix
    FILE.write_text(new_t, encoding='utf-8', newline='')

    print(f'  OK: consolidated {len(isis_skus)} ISIS SKUs into 1 brand-level entry')
    print(f'      monthly_vals: {len(consolidated["monthly_vals"])} months')
    print(f'      ms_ytd sample: {list(consolidated["ms_ytd"].items())[-3:]}')
    print(f'      ms_mat sample: {list(consolidated["ms_mat"].items())[-3:]}')


if __name__ == '__main__':
    main()
