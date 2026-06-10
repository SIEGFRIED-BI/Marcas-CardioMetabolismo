# -*- coding: utf-8 -*-
"""Remapea el mercado IQVIA de BREXIL: ARIPIPRAZOLE -> BREXPIPRAZOLE.

Pedido (Juan/Carlos): "que para BREXIL el mercado sea su molecula".
BREXIL es brexpiprazol. Hoy se compara contra el mercado ARIPIPRAZOLE (IRAZEM,
LEMIDAL, ARIZIC, ARISDAR, SIBLIX, etc.) que es OTRA molecula. Correcto: que
compita solo en BREXPIPRAZOLE.

En el master AR_PM la molecula BREXPIPRAZOLE = solo REXULTI (B7I). BREXIL (SIE)
es lanzamiento sin unidades IQVIA todavia (0). Mercado = REXULTI + BREXIL (SIE).

Reconstruye mol_perf['BREXPIPRAZOLE'] (2 productos) desde los monthly_vals que
ya estan en la familia ARIPIPRAZOLE actual (REXULTI + BREXIL), recomputa
agregados/ms_*, y ELIMINA mol_perf['ARIPIPRAZOLE'] (queda huerfana: ninguna
marca SIE la usa). El cambio de mapping de marca (mol:ARIPIPRAZOLE->BREXPIPRAZOLE)
se hace aparte con un Edit en el config de SNC/index.html.

Pack-level => llega a Mar-2026 (igual que antes; renderBrandKpis lee el ultimo
mes por familia). Recalcular kpis aparte. Uso: py shared/remap-brexil-brexpiprazole-snc.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'SNC' / 'index.html'
SRC_FAM = 'ARIPIPRAZOLE'
DST_FAM = 'BREXPIPRAZOLE'
DST_LABEL = 'Brexpiprazol'
KEEP_PRODS = {'REXULTI', 'BREXIL'}          # primer-token(Product) que quedan

MES_INV = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
           'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
NUM2 = {v:k for k,v in MES_INV.items()}


def msort(mk):
    p = mk.split(); return int(p[1])*100 + MES_INV.get(p[0],0) if len(p)==2 else 0
def quarter_key(mk):
    p = mk.split()
    if len(p)!=2: return ''
    m = MES_INV.get(p[0]); return f'Q{(m-1)//3+1} {p[1]}' if m else ''
def agg_quarterly(monthly):
    o = defaultdict(int)
    for mk,v in monthly.items():
        q = quarter_key(mk)
        if q: o[q]+=v
    return dict(o)
def agg_ytd(monthly, cierre):
    by = defaultdict(int)
    for mk,v in monthly.items():
        p = mk.split()
        if len(p)!=2: continue
        mn = MES_INV.get(p[0])
        if mn and mn<=cierre: by[p[1]]+=v
    return {f'{NUM2[cierre]} {y}': v for y,v in by.items()}
def agg_mat(monthly, cierre):
    years = {int(mk.split()[1]) for mk in monthly if len(mk.split())==2 and mk.split()[0] in MES_INV}
    out = {}
    for y in sorted(years):
        tot = 0
        for back in range(11,-1,-1):
            idx = (y*12 + (cierre-1)) - back
            yy, mm = divmod(idx, 12)
            tot += int(monthly.get(f'{NUM2[mm+1]} {yy}', 0) or 0)
        out[f'{NUM2[cierre]} {y}'] = tot
    return out


def build_family(products):
    fam_monthly = defaultdict(int)
    for p in products:
        for mk,v in p['monthly_vals'].items(): fam_monthly[mk]+=v
    fam_monthly = {k:v for k,v in fam_monthly.items()}
    cierre = MES_INV.get(max(fam_monthly,key=msort).split()[0],12) if fam_monthly else 12
    fam_q=agg_quarterly(fam_monthly); fam_y=agg_ytd(fam_monthly,cierre); fam_m=agg_mat(fam_monthly,cierre)
    out=[]
    for src in products:
        mv=src['monthly_vals']
        p={'prod':src['prod'],'manuf':src.get('manuf',''),'is_sie':src.get('is_sie',False),'monthly_vals':mv}
        p['quarterly_vals']=agg_quarterly(mv); p['ytd']=agg_ytd(mv,cierre); p['mat']=agg_mat(mv,cierre)
        p['ms_monthly']  ={mk: round(mv.get(mk,0)/fv*100,2) if fv>0 else 0 for mk,fv in fam_monthly.items()}
        p['ms_quarterly']={qk: round(p['quarterly_vals'].get(qk,0)/fv*100,2) if fv>0 else 0 for qk,fv in fam_q.items()}
        p['ms_ytd']      ={y: round(p['ytd'].get(y,0)/fv*100,2) if fv>0 else 0 for y,fv in fam_y.items()}
        p['ms_mat']      ={y: round(p['mat'].get(y,0)/fv*100,2) if fv>0 else 0 for y,fv in fam_m.items()}
        out.append(p)
    out.sort(key=lambda p: (not p['is_sie'], -(p['monthly_vals'].get(max(p['monthly_vals'],key=msort,default=''),0) if p['monthly_vals'] else 0)))
    return {'family':DST_LABEL,'products':out,'monthly':fam_monthly,'quarterly':fam_q,'ytd':fam_y,'mat':fam_m}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dry-run',action='store_true'); a=ap.parse_args()
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    text=HTML.read_text(encoding='utf-8',errors='replace')
    import re
    m=re.search(r'const\s+D\s*=\s*',text); ob=text.index('{',m.end())
    D,end=json.JSONDecoder().raw_decode(text[ob:])
    src=D['mol_perf'].get(SRC_FAM)
    if not src: print('ERROR: no existe familia',SRC_FAM); return 2
    keep=[p for p in src['products'] if str(p['prod']).split(' ')[0].upper() in KEEP_PRODS]
    print(f'Productos que quedan en {DST_FAM}:')
    for p in keep: print(f'  {"SIE " if p.get("is_sie") else "    "}{p["prod"]}')
    fam=build_family(keep)
    last=max(fam['monthly'],key=msort)
    print(f'\nMercado {DST_FAM} {last} = {fam["monthly"][last]:,} u  ({len(keep)} productos)')
    for p in fam['products']:
        print(f'  {"SIE " if p["is_sie"] else "    "}{p["prod"]:18} {last}={p["monthly_vals"].get(last,0):>6}  MS%={p["ms_ytd"].get(max(p["ms_ytd"],key=msort,default=""),0)}')

    del D['mol_perf'][SRC_FAM]
    D['mol_perf'][DST_FAM]=fam
    print(f'\nmol_perf: -{SRC_FAM}  +{DST_FAM}')
    print('mol_perf keys:', list(D['mol_perf'].keys()))
    if a.dry_run:
        print('\nDRY RUN: nada escrito.'); return 0
    HTML.write_text(text[:ob]+json.dumps(D,ensure_ascii=False)+text[ob+end:], encoding='utf-8', newline='')
    print(f'\nEscrito SNC/index.html ({HTML.stat().st_size:,} bytes)')
    print('FALTA: cambiar mapping de marca BREXIL mol:ARIPIPRAZOLE -> BREXPIPRAZOLE (Edit)')
    return 0


if __name__=='__main__':
    sys.exit(main())
