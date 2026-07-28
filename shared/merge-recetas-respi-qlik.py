# -*- coding: utf-8 -*-
"""Agrega familias faltantes a recetas/rec_ms/rec_comp de respiratorio/data.js desde el
export de recetas de Qlik ('RECETAS_qlik_*.xlsx' del source de respi).

POR QUE FALTABAN: respiratorio/build-data.ps1 deriva la clave de familia del PARENTESIS del
nombre de mercado (linea ~1508: if ($market -match '\\(([^)]+)\\)') { $family = $matches[1] }).
Cuando el mercado usa una ABREVIATURA que no es la clave de familia, el nombre derivado no
matchea $dashboardFamilyOrder y la linea ~2410 hace 'continue' -> la familia queda SIN recetas,
en silencio:
    'CORTICOST ASOC (H CORT)'  -> 'H CORT'     != 'HEXALER CORT'         -> se perdia
    'CORTICO. NASAL (H NASAL)' -> 'H NASAL'    != 'HEXALER NASAL'        -> se perdia
    'ANTIGRIPALES (ACEMUK DN)' -> 'ACEMUK DN'  != 'ACEMUK DIA Y NOCHE'   -> se perdia
    'ANTIHISTA SIST (HEXALER)' -> 'HEXALER'    == 'HEXALER'              -> OK
Este script mapea el mercado a la familia EXPLICITAMENTE (MARKET_TO_FAMILY) y escribe con la
MISMA forma/semantica que las familias que ya funcionan (verificado contra 'HEXALER' como
control: si el re-derivado de HEXALER no coincide con el data.js actual, aborta).

SEMANTICA (verificada contra el dato en produccion, no inventada):
  recetas[fam][mes]        = {recetas, medicos} de la fila 'Totales' del mercado
  rec_ms[fam].sie[mes]     = suma de TODAS las marcas SIE del mercado (no solo la de la familia)
  rec_ms[fam].ms[mes]      = round(sie/mercado*100, 1)
  rec_ms[fam].quarterly    = sie por trimestre;  ms_quarterly = round(sie_q/mkt_q*100, 1)
  rec_comp[fam][marca]     = {monthly, quarterly, total}  (TODAS las marcas del mercado)
  brandKpis[fam].rec       = {ms, label} del ultimo mes (si la familia existe en brandKpis)

Header del export: meses en ESPANOL como texto ('Jun-2024', 'Ago-2024', 'Dic-2025') en la fila 1
y metrica ('Cant. Recetas' / 'Cant. Medicos') en la fila 2; datos desde la fila 3. Tambien
soporta datetime (formato del pivot viejo).

Idempotente. Uso:
  py shared/merge-recetas-respi-qlik.py [--families "HEXALER CORT,HEXALER NASAL"] [--dry-run]
  py shared/merge-recetas-respi-qlik.py --list        (que familias faltan y cuanto dato hay)
"""
from __future__ import annotations
import argparse, importlib.util, json, re, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_JS = REPO / 'respiratorio' / 'data.js'

# Productos vetados (shared/excluded-products.py): no van a rec_comp ni al sie.
# Sin esto el gate 'EXCLUDED PRODUCT detected' bloquea el commit (paso VIXIDONE LB SIE).
_spec = importlib.util.spec_from_file_location('excluded', REPO / 'shared' / 'excluded-products.py')
_exc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_exc)
is_excluded = _exc.is_excluded
SRC_GLOBS = ['respiratorio/*/dashboard/RECETAS_qlik_*.xlsx', 'respiratorio/*/RECETAS_qlik_*.xlsx']
HUB = Path.home() / 'OneDrive - Portalcorp' / 'Documentos' / 'Hub-Marcas-Inputs'

MARKET_TO_FAMILY = {
    'CORTICOST ASOC (H CORT)':  'HEXALER CORT',
    'CORTICO. NASAL (H NASAL)': 'HEXALER NASAL',
    'ANTIGRIPALES (ACEMUK DN)': 'ACEMUK DIA Y NOCHE',
}
CONTROL = ('ANTIHISTA SIST (HEXALER)', 'HEXALER')  # familia que YA funciona: valida el metodo

MES_ES = {'ENE':'Jan','FEB':'Feb','MAR':'Mar','ABR':'Apr','MAY':'May','JUN':'Jun','JUL':'Jul',
          'AGO':'Aug','SEP':'Sep','SET':'Sep','OCT':'Oct','NOV':'Nov','DIC':'Dec'}
MES_NUM = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}


def msort(mk):
    p = str(mk).split()
    return int(p[1])*100 + MES_NUM.get(p[0], 0) if len(p) == 2 and p[0] in MES_NUM else 0


def qkey(mk):
    p = mk.split()
    if len(p) != 2 or p[0] not in MES_NUM: return ''
    return f'Q{(MES_NUM[p[0]]-1)//3+1} {p[1]}'


def qsort(qk):
    p = str(qk).split()
    return int(p[1])*10 + int(p[0][1]) if len(p) == 2 and p[0].startswith('Q') else 0


def to_int(v):
    if v is None or v == '' or v == '-': return 0
    try: return int(round(float(v)))
    except (TypeError, ValueError): return 0


def parse_month(h):
    """'Jun-2024' | 'Ago-2024' | datetime -> 'Jun 2024'. None si no es mes."""
    if isinstance(h, datetime):
        inv = {v: k for k, v in MES_NUM.items()}
        return f'{inv[h.month]} {h.year}'
    s = str(h or '').strip()
    m = re.match(r'^([A-Za-z]{3})[-/ ](\d{4})$', s)
    if not m: return None
    en = MES_ES.get(m.group(1).upper())
    return f'{en} {m.group(2)}' if en else None


def resolve_src(explicit=None):
    if explicit: return Path(explicit)
    cands = []
    for base in (HUB, REPO.parent):
        if not base.is_dir(): continue
        for g in SRC_GLOBS:
            cands += sorted(base.glob(g))
    if not cands: return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def read_source(path):
    """-> (months, markets) con markets[mercado] = {'tot':{mes:{rec,med}}, 'brands':{marca:{rec:{},med:{}}}}"""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    r1 = list(next(it)); r2 = list(next(it))
    col = {}; months = []
    for i, h in enumerate(r1):
        mk = parse_month(h)
        if not mk: continue
        if mk not in months: months.append(mk)
        h2 = str(r2[i] if i < len(r2) else '').lower()
        metric = 'rec' if 'receta' in h2 else ('med' if 'dico' in h2 else None)
        if metric: col[i] = (mk, metric)
    months.sort(key=msort)

    markets = {}
    for row in it:
        if not row or len(row) < 3: continue
        merc = str(row[0] or '').strip()
        if not merc: continue
        droga = str(row[1] or '').strip(); marca = str(row[2] or '').strip()
        md = markets.setdefault(merc, {'tot': {}, 'brands': {}})
        if droga == 'Totales' and not marca:
            for i, (mk, metric) in col.items():
                if i < len(row): md['tot'].setdefault(mk, {})[metric] = to_int(row[i])
            continue
        if marca == 'Totales' or not marca: continue
        bd = md['brands'].setdefault(marca, {'rec': {}, 'med': {}})
        for i, (mk, metric) in col.items():
            if i < len(row): bd[metric][mk] = bd[metric].get(mk, 0) + to_int(row[i])
    wb.close()
    return months, markets


def build_family(md, months):
    """Devuelve (recetas, rec_ms, rec_comp) para un mercado, con la semantica de produccion."""
    recetas = {}
    for mk in months:
        t = md['tot'].get(mk) or {}
        recetas[mk] = {'recetas': t.get('rec', 0), 'medicos': t.get('med', 0)}

    sie = {}
    for mk in months:
        sie[mk] = sum(b['rec'].get(mk, 0) for name, b in md['brands'].items()
                      if 'SIE' in name.upper() and not is_excluded(name))
    ms = {mk: (round(sie[mk] / recetas[mk]['recetas'] * 100, 1) if recetas[mk]['recetas'] else 0) for mk in months}

    sq = defaultdict(int); mq = defaultdict(int)
    for mk in months:
        q = qkey(mk)
        if not q: continue
        sq[q] += sie[mk]; mq[q] += recetas[mk]['recetas']
    quarterly = {q: sq[q] for q in sorted(sq, key=qsort)}
    ms_quarterly = {q: (round(sq[q] / mq[q] * 100, 1) if mq[q] else 0) for q in sorted(sq, key=qsort)}
    rec_ms = {'sie': sie, 'ms': ms, 'quarterly': quarterly, 'ms_quarterly': ms_quarterly}

    rec_comp = {}
    for name, b in md['brands'].items():
        if is_excluded(name): continue
        monthly = {mk: b['rec'].get(mk, 0) for mk in months}
        bq = defaultdict(int)
        for mk in months:
            q = qkey(mk)
            if q: bq[q] += monthly[mk]
        rec_comp[name] = {'monthly': monthly,
                          'quarterly': {q: bq[q] for q in sorted(bq, key=qsort)},
                          'total': sum(monthly.values())}
    return recetas, rec_ms, rec_comp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--families', default='HEXALER CORT',
                    help="familias a agregar, coma-separadas, o 'all'")
    ap.add_argument('--source')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

    src = resolve_src(a.source)
    if src is None or not src.is_file():
        print('  (skip) no encontre RECETAS_qlik_*.xlsx'); return 0
    print(f'source: {src.name}')
    months, markets = read_source(src)
    print(f'meses: {len(months)}  {months[0]}..{months[-1]}')

    text = DATA_JS.read_text(encoding='utf-8-sig')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])

    if a.list:
        print('\nfamilias del mapeo:')
        for mkt, fam in MARKET_TO_FAMILY.items():
            has = fam in (D.get('rec_ms') or {})
            n = len((markets.get(mkt) or {}).get('brands') or {})
            last = (markets.get(mkt, {}).get('tot', {}).get(months[-1], {}) or {}).get('rec')
            print(f'  {fam:22} en data.js={has}  |  source: {mkt!r} {n} marcas, {months[-1]}={last}')
        return 0

    # --- control: re-derivar una familia que YA funciona y exigir igualdad ---
    cmkt, cfam = CONTROL
    if cmkt in markets and cfam in (D.get('rec_ms') or {}):
        c_rec, c_ms, c_comp = build_family(markets[cmkt], months)
        cur_ms = D['rec_ms'][cfam]; cur_rec = D['recetas'][cfam]
        bad = []
        for mk in months:
            if cur_ms['sie'].get(mk) != c_ms['sie'][mk]: bad.append(f'sie[{mk}] {cur_ms["sie"].get(mk)} != {c_ms["sie"][mk]}')
            if abs((cur_ms['ms'].get(mk) or 0) - c_ms['ms'][mk]) > 0.05: bad.append(f'ms[{mk}] {cur_ms["ms"].get(mk)} != {c_ms["ms"][mk]}')
            if (cur_rec.get(mk) or {}).get('recetas') != c_rec[mk]['recetas']: bad.append(f'recetas[{mk}]')
        if bad:
            print(f'ABORTADO: el control {cfam} no reproduce el dato actual ({len(bad)} difs). '
                  f'Primeras: {bad[:4]}. No escribo para no meter dato inconsistente.')
            return 2
        print(f'control OK: {cfam} re-derivado == data.js actual ({len(months)} meses)')
    else:
        print(f'  (warn) no pude correr el control con {cfam}')

    want = ([f for f in MARKET_TO_FAMILY.values()] if a.families.strip().lower() == 'all'
            else [x.strip() for x in a.families.split(',') if x.strip()])
    fam_to_mkt = {v: k for k, v in MARKET_TO_FAMILY.items()}
    changed = []
    for fam in want:
        mkt = fam_to_mkt.get(fam)
        if not mkt:
            print(f'  (skip) {fam}: no esta en MARKET_TO_FAMILY'); continue
        if mkt not in markets:
            print(f'  (skip) {fam}: el mercado {mkt!r} no esta en el source'); continue
        if fam not in (D.get('mol_perf') or {}):
            print(f'  (warn) {fam}: no existe en mol_perf de respi (revisar el nombre)')
        recetas, rec_ms, rec_comp = build_family(markets[mkt], months)
        last = months[-1]
        D.setdefault('recetas', {})[fam] = recetas
        D.setdefault('rec_ms', {})[fam] = rec_ms
        D.setdefault('rec_comp', {})[fam] = rec_comp
        bk = (D.get('brandKpis') or {}).get(fam)
        if isinstance(bk, dict):
            bk.setdefault('rec', {})
            bk['rec']['ms'] = rec_ms['ms'][last]
            bk['rec']['label'] = last
        sie_names = [n for n in rec_comp if 'SIE' in n.upper()]
        print(f'  + {fam:22} mercado {last}={recetas[last]["recetas"]}  SIE={rec_ms["sie"][last]}  '
              f'MS%={rec_ms["ms"][last]}  ({len(rec_comp)} marcas, SIE: {sie_names})')
        changed.append(fam)

    if not changed:
        print('nada para cambiar.'); return 0
    if a.dry_run:
        print('DRY-RUN: nada escrito.'); return 0
    DATA_JS.write_text(text[:ob] + json.dumps(D, ensure_ascii=False) + text[ob+end:],
                       encoding='utf-8', newline='')
    print(f'Escrito {DATA_JS}  ({len(changed)} familia(s): {changed})')
    print('  -> correr build-kpis + sync-kpistrip + fix-brandkpis-rec + bump-cache-busters')
    return 0


if __name__ == '__main__':
    sys.exit(main())
