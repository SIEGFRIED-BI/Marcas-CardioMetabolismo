# -*- coding: utf-8 -*-
"""Reconstruye D.convenios (obras sociales) de dermato desde los exports CloseUp
"Detalle consumos y aportes por convenio" (metrica 'Consumo uni', por ObraSocial1).

La seccion Convenios NO venia del pipeline (era carga manual/legacy). Este script la
productiza: toma el export del anio corriente (current) y el del previo (prev), mapea
Producto->familia con los alias del build (convenios.dermato en close-manifest.json,
mismo criterio que build-budget-overrides), y arma por familia la lista
[{os, unid (current), unid24 (prev), delta}] ordenada por unid desc (el render toma
top-10 sin re-ordenar). delta=null ("nuevo") si la base previa es < minBaseForDelta.

RESOLUCION de archivos (si no se pasan --current/--prev):
  busca en hubRoot (y _inbox/<closeMonth>) archivos "Convenios dermato <AÑO>.xlsx"
  con AÑO = closeYear (current) y closeYear-1 (prev). Los exports crudos de CloseUp se
  llaman igual entre si (sin anio en el nombre) -> hay que renombrarlos con el anio.

Uso:
  py shared/merge-convenios-dermato.py                         # auto-resuelve del hub
  py shared/merge-convenios-dermato.py --current A.xlsx --prev B.xlsx
  py shared/merge-convenios-dermato.py --check                 # gate: exit 1 si drift
  py shared/merge-convenios-dermato.py --dry-run
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import openpyxl

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / 'shared' / 'close-manifest.json'

# Fallback si el manifest no trae convenios.dermato (red de seguridad).
_ALIAS_FALLBACK = [['ACNECLIN AP', 'ACNECLIN 100 AP'], ['ACNECLIN PBA', 'ACNECLIN PBA'],
                   ['MICOMAZOL B', 'MICOMAZOL B'], ['MICROSONA C', 'MICROSONA C'],
                   ['PALDAR H', 'PALDAR H'], ['ACNECLIN', 'ACNECLIN'], ['CLOBESOL', 'CLOBESOL'],
                   ['MICOMAZOL', 'MICOMAZOL'], ['MICROSONA', 'MICROSONA'], ['PALDAR', 'PALDAR'],
                   ['ROACCUTAN', 'ROACCUTAN'], ['MOMETAX', 'MOMETAX']]
_MIN_BASE_FALLBACK = 5
_LINE_FILE = 'dermatologia/data.js'


def load_manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding='utf-8'))
    except Exception:
        return {}


def cfg(mani):
    conv = ((mani.get('convenios') or {}).get('dermato') or {})
    alias = conv.get('productAliases') or _ALIAS_FALLBACK
    minbase = conv.get('minBaseForDelta', _MIN_BASE_FALLBACK)
    return [(a[0], a[1]) for a in alias], minbase


def hub_root(mani):
    import os
    hr = ((mani.get('global') or {}).get('hubRoot') or '')
    od = os.environ.get('OneDrive', '')
    return Path(hr.replace('${OneDrive}', od).replace('\\', '/')) if hr else None


def resolve_files(mani, cur_arg, prev_arg):
    if cur_arg and prev_arg:
        return Path(cur_arg), Path(prev_arg)
    g = mani.get('global') or {}
    year = int(g.get('closeYear') or 0)
    hr = hub_root(mani)
    close = g.get('closeMonth') or ''
    dirs = [hr] if hr else []
    if hr and close:
        dirs.append(hr / (g.get('inboxSubfolder') or '_inbox') / close)

    def find(y):
        for d in dirs:
            if not d or not d.is_dir():
                continue
            for pat in (f'Convenios dermato {y}.xlsx', f'convenios-dermato-{y}.xlsx'):
                hit = list(d.glob(pat))
                if hit:
                    return hit[0]
        return None
    return (find(year) if not cur_arg else Path(cur_arg),
            find(year - 1) if not prev_arg else Path(prev_arg))


def oskey(s):
    m = re.search(r'\((\d{3,6})\)', str(s))
    return m.group(1) if m else re.sub(r'\s+', ' ', str(s).strip().upper())


def fam_of(prod, alias):
    u = prod.upper()
    for fam, al in alias:
        if al in u:
            return fam
    return None


def parse(path, alias):
    """-> ({familia: {oskey: units}}, {(familia,oskey): display})"""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    out = defaultdict(lambda: defaultdict(float))
    disp = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        prod = str(r[3] or '').strip() if len(r) > 3 else ''
        os1 = str(r[0] or '').strip() if len(r) > 0 else ''
        os2 = str(r[1] or '').strip() if len(r) > 1 else ''
        if not prod or prod == 'Totales' or os2 == 'Totales' or os1 == 'Totales':
            continue
        f = fam_of(prod, alias)
        if not f:
            continue
        u = r[4] if len(r) > 4 and isinstance(r[4], (int, float)) else 0
        k = oskey(os1)
        out[f][k] += u
        disp[(f, k)] = os1
    wb.close()
    return out, disp


def build(d_cur, d_prev, disp_cur, disp_prev, alias, minbase):
    fams = [a[0] for a in alias]
    conv = {}
    for fam in fams:
        cur = d_cur.get(fam, {})
        prev = d_prev.get(fam, {})
        rows = []
        for k in set(cur) | set(prev):
            u = round(cur.get(k, 0))
            u25 = round(prev.get(k, 0))
            dl = round((u - u25) / u25 * 100, 1) if u25 >= minbase else None
            rows.append({'os': disp_cur.get((fam, k)) or disp_prev.get((fam, k)),
                         'unid': u, 'unid24': u25, 'delta': dl})
        # desempate por nombre de OS -> orden DETERMINISTICO (set() itera distinto por
        # hash randomization; sin esto el re-run cambia el orden de empates -> churn/gate falso).
        rows.sort(key=lambda x: (-(x['unid'] or 0), -(x['unid24'] or 0), str(x['os'])))
        if rows:
            conv[fam] = rows
    return conv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--current')
    ap.add_argument('--prev')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    mani = load_manifest()
    alias, minbase = cfg(mani)
    cur_f, prev_f = resolve_files(mani, args.current, args.prev)

    if not (cur_f and cur_f.is_file() and prev_f and prev_f.is_file()):
        msg = (f"convenios dermato: sin exports ("
               f"current={cur_f if cur_f else '-'}, prev={prev_f if prev_f else '-'}) "
               f"-> skip (se conserva lo que ya esta).")
        print(msg)
        return 0  # no es error: la fuente es manual/opcional

    d_cur, disp_cur = parse(cur_f, alias)
    d_prev, disp_prev = parse(prev_f, alias)
    newconv = build(d_cur, d_prev, disp_cur, disp_prev, alias, minbase)

    p = REPO / _LINE_FILE
    text = p.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])
    old = D.get('convenios') or {}

    # drift/summary
    drift = []
    for fam, rows in newconv.items():
        if old.get(fam) != rows:
            s26 = sum(x['unid'] for x in rows)
            s25 = sum(x['unid24'] for x in rows)
            drift.append(f"{fam}: 2026={s26:,} 2025={s25:,} ({len(rows)} OS)")

    print(f"convenios dermato desde:\n  current={cur_f.name}\n  prev   ={prev_f.name}")
    for d in drift:
        print('  ' + d)

    if args.check:
        if drift:
            print(f"\nCONVENIOS-DERMATO DRIFT: {len(drift)} familia(s) != stored. "
                  f"Corre: py shared/merge-convenios-dermato.py")
            return 1
        print("\nOK: convenios dermato == fuente.")
        return 0
    if args.dry_run:
        print("\n[DRY-RUN] no escribí.")
        return 0

    D['convenios'] = newconv
    p.write_text(text[:ob] + json.dumps(D, ensure_ascii=False) + text[ob + end:],
                 encoding='utf-8', newline='')
    print(f"\ndermatologia/data.js: convenios de {len(newconv)} familias actualizados.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
