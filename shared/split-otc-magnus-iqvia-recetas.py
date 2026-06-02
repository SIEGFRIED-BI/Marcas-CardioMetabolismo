"""Aperturra MAGNUS (sildenafil) y MAGNUS 36 (tadalafil) en OTC para
MERCADO IQVIA (mol_perf) y RECETAS (rec_ms/rec_comp/recetas).

La Venta Interna ya se separa con apply-otc-magnus-split.py. Este script hace
las otras dos capas.

Clasificacion sildenafil/tadalafil: tomada del OTC/DDD/competidores-data.js
(mercados 'Magnus' y 'Magnus 36' con sus marcas). Verificada marca por marca
(100% de cobertura sobre mol_perf y rec_comp).

Preserva TODA la historia (reparticion de productos existentes, no re-deriva).
Luego correr: recompute-mol-perf-aggregates, fix-brandkpis-from-molperf,
build-kpis, build-families-perf, sync-kpistrip, audit-full.

Idempotente: si mol_perf['MAGNUS 36'] ya existe, no hace nada.
"""
from __future__ import annotations
import json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / 'OTC' / 'data.js'

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
TADA_KW = ['CIALIS','DROTAQ','EQUITONE','INVICTUS','JAST','LEVAL','MOMENTUM','PERDURAL',
           'PLACET','QUARTIER','TADALAFILO','TADAL','TALIS','ROSPOWER','H36']


def norm(b):
    s = re.sub(r'\([^)]*\)', '', str(b)).upper()
    return re.sub(r'\s+', ' ', s).strip()


def is_tada(brand):
    """True = tadalafil (MAGNUS 36); False = sildenafil (MAGNUS)."""
    s = norm(brand)
    if '36' in s: return True
    if 'VIRIPOTENS MAX' in s or 'VIRILON' in s: return True
    toks = ' ' + s + ' '
    for kw in TADA_KW:
        if s.startswith(kw) or (' ' + kw + ' ') in toks or s == kw:
            return True
    return False


def qkey(mk):
    p = mk.split()
    if len(p) != 2: return None
    m = MES_INV.get(p[0])
    if not m: return None
    return f'Q{(m-1)//3+1} {p[1]}'


def main():
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    t = DATA.read_text(encoding='utf-8-sig', errors='replace')
    m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
    ob = t.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(t[ob:])

    if 'MAGNUS 36' in D.get('mol_perf', {}):
        print('mol_perf["MAGNUS 36"] ya existe — nada que hacer (idempotente).')
        return 0

    # ---------- PART B: mol_perf ----------
    src = D['mol_perf']['MAGNUS']
    sild_p, tada_p = [], []
    for p in src['products']:
        (tada_p if is_tada(p['prod']) else sild_p).append(p)
    D['mol_perf']['MAGNUS'] = {'family': 'MAGNUS', 'products': sild_p,
                               'monthly': {}, 'quarterly': {}, 'ytd': {}, 'mat': {}}
    D['mol_perf']['MAGNUS 36'] = {'family': 'MAGNUS 36', 'products': tada_p,
                                  'monthly': {}, 'quarterly': {}, 'ytd': {}, 'mat': {}}
    print(f'mol_perf: MAGNUS {len(sild_p)} prods (sild) | MAGNUS 36 {len(tada_p)} prods (tada)')

    # Estructuras dependientes
    for dct, val in [('sieMolMap', 'MAGNUS 36'), ('molLabels', 'MAGNUS 36')]:
        if dct in D and isinstance(D[dct], dict):
            D[dct]['MAGNUS 36'] = val
    if 'colors' in D:
        D['colors'].setdefault('MAGNUS 36', '#c026d3')  # magenta, distinto del MAGNUS (#7c3aed)
    if 'prodMap' in D and 'MAGNUS' in D['prodMap']:
        D['prodMap']['MAGNUS 36'] = {'mol': 'MAGNUS 36', 'canal': 'MAGNUS', 'conv': 'MAGNUS',
                                     'rec': 'MAGNUS 36', 'prec': 'MAGNUS', 'bud': 'MAGNUS 36'}
    if 'budIqviaMap' in D and isinstance(D['budIqviaMap'], dict):
        D['budIqviaMap']['MAGNUS'] = ['MAGNUS (SIE)']
        D['budIqviaMap']['MAGNUS 36'] = ['MAGNUS 36 (SIE)']

    # ---------- PART C: recetas ----------
    rc = D['rec_comp']['MAGNUS']
    rc_sild, rc_tada = {}, {}
    for brand, bd in rc.items():
        (rc_tada if is_tada(brand) else rc_sild)[brand] = bd
    D['rec_comp']['MAGNUS'] = rc_sild
    D['rec_comp']['MAGNUS 36'] = rc_tada
    print(f'rec_comp: MAGNUS {len(rc_sild)} marcas | MAGNUS 36 {len(rc_tada)} marcas')

    def build_recms(comp, sie_brand):
        mkt = defaultdict(int)
        for brand, bd in comp.items():
            for mk, v in (bd.get('monthly') or {}).items():
                mkt[mk] += int(v or 0)
        sie = {mk: int(v or 0) for mk, v in ((comp.get(sie_brand) or {}).get('monthly') or {}).items()}
        ms = {mk: round(sie.get(mk, 0) / mkt[mk] * 100, 2) for mk in mkt if mkt[mk]}
        q_sie, q_mkt = defaultdict(int), defaultdict(int)
        for mk, v in sie.items():
            qk = qkey(mk);  q_sie[qk] += v if qk else 0
        for mk, v in mkt.items():
            qk = qkey(mk);  q_mkt[qk] += v if qk else 0
        msq = {qk: round(q_sie[qk] / q_mkt[qk] * 100, 2) for qk in q_mkt if q_mkt[qk]}
        return {'sie': sie, 'ms': ms, 'quarterly': dict(q_sie), 'ms_quarterly': msq, 'mkt': dict(mkt)}, dict(mkt)

    rms_sild, mkt_sild = build_recms(rc_sild, 'MAGNUS SIE')
    rms_tada, mkt_tada = build_recms(rc_tada, 'MAGNUS 36 SIE')
    D['rec_ms']['MAGNUS'] = rms_sild
    D['rec_ms']['MAGNUS 36'] = rms_tada

    # recetas (serie del mercado total): recetas = mkt molecula; medicos = proporcional
    orig = D['recetas'].get('MAGNUS', {})
    rec_sild, rec_tada = {}, {}
    for mk, obj in orig.items():
        tot = mkt_sild.get(mk, 0) + mkt_tada.get(mk, 0)
        med = (obj or {}).get('medicos', 0) or 0
        s, ta = mkt_sild.get(mk, 0), mkt_tada.get(mk, 0)
        rec_sild[mk] = {'recetas': s, 'medicos': int(round(med * s / tot)) if tot else 0}
        rec_tada[mk] = {'recetas': ta, 'medicos': int(round(med * ta / tot)) if tot else 0}
    D['recetas']['MAGNUS'] = rec_sild
    D['recetas']['MAGNUS 36'] = rec_tada

    new_t = t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:]
    DATA.write_text(new_t, encoding='utf-8', newline='')
    print('OTC/data.js actualizado: MAGNUS / MAGNUS 36 separados en IQVIA + Recetas.')
    print('AHORA correr: recompute-mol-perf-aggregates, fix-brandkpis-from-molperf, build-kpis, build-families-perf, sync-kpistrip, audit-full')
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
