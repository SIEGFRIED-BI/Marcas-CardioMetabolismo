# -*- coding: utf-8 -*-
"""Reconstruye mol_perf['PREGABALIN'] de SNC como el MERCADO MULTIDOSIS.

Pedido (Juan): en el mercado de PGB ver SOLO multidosis. IQVIA clasifica dos
mercados de pregabalina: "PGB Capsulas" y "PGB Multidosis". El multidosis son
las presentaciones en tableta divisible (no capsulas) de 13 marcas:
  PGB, PLENICA, NEURISTAN, KABIAN, LINPREL, GAVIN, LUNEL, PREBIEN, PRINCIPIA,
  AXUAL, PREBICTAL, DOLONEUTIN, SERIPRAN
Excluye LYRICA, MYSTIKA, PREGABALINA RICHET, GAVANEURAL, etc. (capsulas/no md).

Filtro desde el master nacional AR_PM (misma fuente/escala que el resto de SNC):
  Molecules Long == PREGABALIN  AND  pack SIN 'CAPS'  AND
  primer-token(Product) en MULTI_BRANDS.
Validado: total Mar2026 nacional=116006 ~ regional "PGB Multidosis"=108153
(la dif es panel PM vs CUP; se usa el nacional por consistencia de escala).

Historico hasta Mar-2026 (ultimo corte pack-level disponible). Las otras 10
moleculas siguen en Abr-2026; el check de history es a nivel LINEA (union de
meses), asi que no se pierde Abr. renderBrandKpis ya lee el ultimo mes POR
familia, asi que PGB muestra "Mar 2026".

NO toca otras familias. kpis se recomputan aparte (build-kpis + build-families
+ sync-kpistrip). Uso: py shared/rebuild-pgb-multidosis-snc.py [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import openpyxl

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'SNC' / 'index.html'
MASTER = Path(r'C:\Users\camarinaro\OneDrive - Portalcorp\Documentos\Hub-Marcas-Inputs\_iqvia-master\2026-04\AR_PM_FV_Standard_Apr-27-2026.xlsx')

FAM_KEY = 'PREGABALIN'
FAM_LABEL = 'Pregabalina Multidosis'
MULTI_BRANDS = {'AXUAL', 'DOLONEUTIN', 'GAVIN', 'KABIAN', 'LINPREL', 'LUNEL',
                'NEURISTAN', 'PGB', 'PLENICA', 'PREBICTAL', 'PREBIEN',
                'PRINCIPIA', 'SERIPRAN'}

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


def load_multidosis(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    row1 = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
    col_manuf=col_prod=col_pack=col_mol=None; month_cols=[]
    for i,h in enumerate(row1):
        if not h: continue
        s=str(h).strip(); sn=s.replace('\n',' ').strip().lower()
        if sn.startswith('manufacturer'): col_manuf=i
        elif sn.startswith('product'): col_prod=i
        elif sn.startswith('pack'): col_pack=i
        elif sn.startswith('molecules'): col_mol=i
        if s.startswith('Units') and '\n' in s:
            after=s.split('\n',1)[-1].strip()
            if after.upper().startswith(('MAT','YTD')): continue
            m=re.match(r'(\w+)\s+(\d{4})$', after)
            if m and m.group(1) in MES_INV: month_cols.append((i, f'{m.group(1)} {m.group(2)}'))
    if col_manuf is None: col_manuf=0
    if col_prod is None: col_prod=1
    if col_pack is None: col_pack=2
    if col_mol is None: col_mol=5
    prods = defaultdict(lambda: {'manuf':None,'monthly':defaultdict(float)})
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row)<=col_mol: continue
        if str(row[col_mol] or '').strip().upper()!='PREGABALIN': continue
        prod = row[col_prod] if col_prod<len(row) else None
        pack = str(row[col_pack] or '') if col_pack<len(row) else ''
        if not prod: continue
        if 'CAPS' in pack.upper(): continue                       # excluir capsulas
        if str(prod).split(' ')[0].upper() not in MULTI_BRANDS: continue  # solo marcas multidosis
        b = prods[prod]; b['manuf'] = row[col_manuf] if col_manuf<len(row) else None
        for ci,mk in month_cols:
            if ci>=len(row): continue
            v = row[ci]
            if v is None: continue
            try: b['monthly'][mk]+=float(v)
            except (ValueError,TypeError): pass
    wb.close()
    months = [mk for _,mk in sorted(month_cols, key=lambda x: msort(x[1]))]
    return months, {p:{'manuf':i['manuf'],'monthly':{mk:int(round(v)) for mk,v in i['monthly'].items()}}
                    for p,i in prods.items()}


def build_family(prods):
    fam_monthly = defaultdict(int); plist=[]
    for name,info in prods.items():
        mv = info['monthly']
        for mk,v in mv.items(): fam_monthly[mk]+=v
        is_sie = str(name).split(' ')[0].upper()=='PGB'
        plist.append({'prod':name,'manuf':info.get('manuf') or '','is_sie':is_sie,'monthly_vals':mv})
    fam_monthly = dict(fam_monthly)
    cierre = MES_INV.get(max(fam_monthly,key=msort).split()[0],12) if fam_monthly else 12
    fam_q=agg_quarterly(fam_monthly); fam_y=agg_ytd(fam_monthly,cierre); fam_m=agg_mat(fam_monthly,cierre)
    for p in plist:
        mv=p['monthly_vals']
        p['quarterly_vals']=agg_quarterly(mv); p['ytd']=agg_ytd(mv,cierre); p['mat']=agg_mat(mv,cierre)
        p['ms_monthly']  ={mk: round(mv.get(mk,0)/fv*100,2) if fv>0 else 0 for mk,fv in fam_monthly.items()}
        p['ms_quarterly']={qk: round(p['quarterly_vals'].get(qk,0)/fv*100,2) if fv>0 else 0 for qk,fv in fam_q.items()}
        p['ms_ytd']      ={y: round(p['ytd'].get(y,0)/fv*100,2) if fv>0 else 0 for y,fv in fam_y.items()}
        p['ms_mat']      ={y: round(p['mat'].get(y,0)/fv*100,2) if fv>0 else 0 for y,fv in fam_m.items()}
    plist.sort(key=lambda p: (not p['is_sie'], -(p['monthly_vals'].get(max(p['monthly_vals'],key=msort,default=''),0) if p['monthly_vals'] else 0)))
    return {'family':FAM_LABEL,'products':plist,'monthly':fam_monthly,'quarterly':fam_q,'ytd':fam_y,'mat':fam_m}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dry-run',action='store_true'); a=ap.parse_args()
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    if not MASTER.is_file(): print('ERROR master no existe:',MASTER); return 2
    months,prods=load_multidosis(MASTER)
    fam=build_family(prods)
    last=max(fam['monthly'],key=msort)
    print(f'Multidosis: {len(months)} meses ({months[0]}..{months[-1]}), {len(fam["products"])} productos')
    print(f'  mercado {last} = {fam["monthly"][last]:,} u')
    for p in fam['products']:
        print(f'    {"SIE " if p["is_sie"] else "    "}{p["monthly_vals"].get(last,0):>7} {p["prod"]}')

    text=HTML.read_text(encoding='utf-8',errors='replace')
    m=re.search(r'const\s+D\s*=\s*',text); ob=text.index('{',m.end())
    D,end=json.JSONDecoder().raw_decode(text[ob:])
    old=D['mol_perf'].get(FAM_KEY,{})
    print(f'\nPREGABALIN actual: {len(old.get("products",[]))} productos, ultimo mes {max(old.get("monthly",{}),key=msort,default="?")}')
    D['mol_perf'][FAM_KEY]=fam
    print(f'PREGABALIN nuevo (multidosis): {len(fam["products"])} productos, ultimo mes {last}')

    if a.dry_run:
        print('\nDRY RUN: nada escrito.'); return 0
    HTML.write_text(text[:ob]+json.dumps(D,ensure_ascii=False)+text[ob+end:], encoding='utf-8', newline='')
    print(f'\nEscrito SNC/index.html ({HTML.stat().st_size:,} bytes)')
    return 0


if __name__=='__main__':
    sys.exit(main())
