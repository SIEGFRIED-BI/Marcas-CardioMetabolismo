# -*- coding: utf-8 -*-
"""Reconstruye COMPLETO el `const D = {...}` inline de las 3 DDD viejas
(cardio/SNC/dermato) desde su competidores-data.js (Shape A, 24 meses,
mercados-molécula). A diferencia de update-ddd-from-competidores.py (que
preservaba los mercados viejos y solo refrescaba series), esto regenera los
mercados con NOMBRES MOLÉCULA (consistente con las otras 4 DDD) y GENERA
region_data / top_brands / brand_meta / clase desde el competidores.

Arregla de raíz: eje de 24 meses alineado con los datos, MS% por marca con la
key correcta (p.ej. ENTRESTO TA REV en vez de ENTRESTO), y deja el const D
internamente consistente (region_data == getRT por región, 24 meses).

El render (getSieMS/getRT/rKPI/rTbl/rComp/rC1-3) NO se toca: solo el objeto D.
Idempotente. Windows PowerShell-agnóstico (python puro).
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (DDD html inline, competidores-data.js) — solo las 3 VIEJAS (const D inline)
LINES = [
    ('cardio/DDD/index.html',        'cardio/DDD/competidores-data.js'),
    ('SNC/DDD/psq_ddd.html',         'SNC/DDD/competidores-data.js'),
    ('dermatologia/dermato_ddd.html','dermatologia/competidores-data.js'),
]

MES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']


def load_comp(path):
    s = (REPO / path).read_text(encoding='utf-8').replace('window.SFG_COMP_DATA = ', '').rstrip(';\n \t\r')
    return json.loads(s)


def load_inline_D(path):
    p = REPO / path
    t = p.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const\s+D\s*=\s*\{', t)
    if not m:
        return None
    ob = t.index('{', m.start())
    D, end = json.JSONDecoder().raw_decode(t[ob:])
    return p, t[:ob], D, t[ob + end:]


def quarters_from_months(months):
    out = []
    for mk in months:
        try:
            mes, yr = mk.split('-')
            q = MES.index(mes) // 3 + 1
            qk = f'Q{q}-{yr}'
            if qk not in out:
                out.append(qk)
        except Exception:
            continue
    return out


def build_market(comp_mkt, months_count, regions):
    brands_sie = list(comp_mkt.get('brands', []))
    sie_set = set(brands_sie)

    # total_monthly por región + __NAC__
    total_monthly = {}
    nac_total = [0] * months_count
    for reg in regions:
        arr = comp_mkt.get('total_monthly', {}).get(reg)
        if not isinstance(arr, list):
            continue
        padded = (list(arr) + [0] * months_count)[:months_count]
        total_monthly[reg] = padded
        for i in range(months_count):
            nac_total[i] += padded[i] or 0
    total_monthly['__NAC__'] = nac_total

    # brand_monthly por marca: región + __NAC__
    brand_monthly = {}
    for brand, regdict in comp_mkt.get('brand_monthly', {}).items():
        if not isinstance(regdict, dict):
            continue
        entry = {}
        nac = [0] * months_count
        for reg in regions:
            arr = regdict.get(reg)
            if not isinstance(arr, list):
                continue
            padded = (list(arr) + [0] * months_count)[:months_count]
            entry[reg] = padded
            for i in range(months_count):
                nac[i] += padded[i] or 0
        entry['__NAC__'] = nac
        brand_monthly[brand] = entry

    # brand_meta + top_brands (ranked por unidades nacionales desc)
    brand_meta = {b: {'sie': b in sie_set} for b in brand_monthly}
    top_brands = sorted(brand_monthly.keys(),
                        key=lambda b: sum(brand_monthly[b].get('__NAC__', [])),
                        reverse=True)

    # region_data = suma 24 meses por región (== getRT por región, así rTbl y
    # los KPIs coinciden). __NAC__ NO va acá (es solo la tabla de regiones reales).
    region_data = {}
    for reg in regions:
        tm = total_monthly.get(reg)
        if not tm:
            continue
        total = sum(tm)
        sie = 0
        for b in top_brands:
            if brand_meta[b]['sie']:
                bm = brand_monthly[b].get(reg)
                if bm:
                    sie += sum(bm)
        region_data[reg] = {
            'total': total,
            'sie': sie,
            'ms': round(sie / total * 100, 1) if total > 0 else 0,
        }

    total_units = sum(nac_total)
    sie_units = 0
    for b in top_brands:
        if brand_meta[b]['sie']:
            sie_units += sum(brand_monthly[b].get('__NAC__', []))
    global_ms = round(sie_units / total_units * 100, 1) if total_units > 0 else 0

    molecules = comp_mkt.get('molecules', []) or []
    atc = comp_mkt.get('atc', []) or []
    clase = ' + '.join(molecules) if molecules else (atc[0] if atc else '')

    return {
        'brands': brands_sie,
        'clase': clase,
        'total_units': total_units,
        'sie_units': sie_units,
        'global_ms': global_ms,
        'brand_monthly': brand_monthly,
        'total_monthly': total_monthly,
        'brand_meta': brand_meta,
        'top_brands': top_brands,
        'region_data': region_data,
    }


def rebuild(ddd_path, comp_path, check_only=False):
    comp = load_comp(comp_path)
    loaded = load_inline_D(ddd_path)
    if loaded is None:
        return 0, 'NO inline const D'
    p, prefix, oldD, suffix = loaded

    months = list(comp.get('months', []))
    regions = list(comp.get('regions', []))
    mc = len(months)

    newD = {
        'months': months,
        'quarters': quarters_from_months(months),
        'regions': regions,
        'markets': {},
    }
    empty_regions = 0
    for mk_name, comp_mkt in comp.get('markets', {}).items():
        mkt = build_market(comp_mkt, mc, regions)
        if not mkt['region_data']:
            empty_regions += 1
        newD['markets'][mk_name] = mkt

    changed = (json.dumps(oldD, ensure_ascii=False, sort_keys=True)
               != json.dumps(newD, ensure_ascii=False, sort_keys=True))
    if changed and not check_only:
        p.write_text(prefix + json.dumps(newD, ensure_ascii=False) + suffix,
                     encoding='utf-8', newline='')
    msg = (f'{"CAMBIA" if changed else "sin cambios"} '
           f'[markets={len(newD["markets"])}, months={mc}, '
           f'mkts_sin_region_data={empty_regions}]')
    return (1 if changed else 0), msg


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_only = '--check' in sys.argv
    for ddd, comp in LINES:
        try:
            _, msg = rebuild(ddd, comp, check_only)
            print(f'  {ddd}: {msg}')
        except Exception as e:
            print(f'  {ddd}: ERROR {e}')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
