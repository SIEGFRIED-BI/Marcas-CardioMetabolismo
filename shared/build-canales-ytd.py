# -*- coding: utf-8 -*-
"""Construye D.canales (panel "Mostrador vs Convenios") en YTD vs YTD, desde las
planillas trimestrales de hubRoot/'convenios NUEVO'.

QUE ARREGLA (estado previo, verificado 2026-09-02):
  - cardio tenia las 23 familias con TODOS los campos en 0 -> la seccion mostraba
    "Sin datos disponibles". Causa: cardio/build-data.ps1 busca 'Convenios vs
    mostrador*.xlsx' en <linea>/<mes>/fuentes-originales, donde no estan (viven en
    'convenios NUEVO'), y el try/catch se comia el error.
  - Los *_prev y conv_pp/most_pp eran null en TODAS las lineas -> el delta del render
    decia "s/d" siempre. El comparativo interanual que la seccion promete no existia.
  - respiratorio tenia conv_units/most_units con valores en PESOS y negativos
    (ACEMUK: conv_units = -3.945.903.480), aunque conv% estaba bien.
  - meta.canales_label estaba HARDCODEADO como '2025 vs 2024' en los 5 build-data.ps1,
    con el resto del tablero en Ago-2026. Aca se deriva del dato.

VENTANA: YTD = los trimestres disponibles del anio mas reciente, contra LOS MISMOS
trimestres del anio anterior (apples-to-apples). Hoy: 2026 Q1+Q2 vs 2025 Q1+Q2. No se
compara medio anio contra un anio entero.

CONSUMO: se usa el consumo BRUTO (= % convenio UNI x unidades facturadas), que es el que
usa la fuente para el %, NO la columna 'Consumo uni' (que viene neta de notas de debito).
Las dos difieren mucho y cada vez mas -- ver shared/qlik/POC-CONVENIOS.md. Asi el panel
anual y el trimestral cuentan lo mismo.

NO MEDIBLE: si las unidades facturadas del periodo son <= 0, no hay base contra la cual
medir -> conv=null y el render descarta esa familia (filtra por v.conv!=null). Si el
consumo supera lo facturado, se conserva el %convenio real y most queda null.

Idempotente. --check para ver si hay que correrlo. Skipea si falta openpyxl o la carpeta.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent
REPO = SHARED.parent
sys.path.insert(0, str(SHARED))

LINES = ['cardio/data.js', 'ATB/data.js', 'OTC/data.js', 'respiratorio/data.js',
         'mujer/data.js', 'SNC/data.js', 'dermatologia/data.js']
SUBDIR = 'convenios NUEVO'
QN = {'1er': 'Q1', '2do': 'Q2', '3er': 'Q3', '4to': 'Q4'}
QMESES = {'Q1': ('Ene', 'Mar'), 'Q2': ('Abr', 'Jun'), 'Q3': ('Jul', 'Sep'), 'Q4': ('Oct', 'Dic')}

# mujer keyea por SEGMENTO de marketing (ALTA DOSIS, SIN ESTROGENO...) y la fuente trae
# FAMILIAS de producto (ISIS, ISIS FREE...). Sin este mapa el match por nombre pierde 8
# segmentos con dato real (ALTA DOSIS 189.836 u, SIN ESTROGENO 579.534 u...). Es el mismo
# mapa que usa merge-ventas-internas.py; la fuente real es close-manifest.json.
_MUJER_FALLBACK = {
    'SIN ESTROGENO': ['ISIS FREE'], 'ALTA DOSIS': ['ISIS'],
    'BAJA DOSIS 21+7': ['ISIS MINI'], 'BAJA DOSIS 24': ['ISIS MINI 24'],
    'COMPLEX': ['SIDERBLUT COMPLEX', 'SIDERBLUT FOLIC'],
    'SOLO': ['SIDERBLUT', 'SIDERBLUT POLI', 'FERINSOL'],
    'DELTROX': ['DELTROX'], 'BASE': ['CALCIO BASE DUPOMAR'],
    'BASE D': ['CALCIO BASE DUPOMAR D', 'CALCIO BASE DUPOMAR D3',
               'CALCIO CITRATO DUPOMAR D3'],
    'CLIMATIX': ['CLIMATIX'],
    # D3 / D3 PLUS / 45 / MAGNESIO comparten la familia 'TRIP' en la fuente: no se
    # pueden separar aca (mismo limite que en venta). Quedan sin dato, no mal asignadas.
    'D3': [], 'D3 PLUS': [], '45': [], 'MAGNESIO': [],
}
try:
    import manifest as _mf
    MUJER_SEG = _mf.seg_get('mujer_venta_segments', 'segmentToFams', _MUJER_FALLBACK)
except Exception:
    MUJER_SEG = _MUJER_FALLBACK


def hub_dir():
    try:
        import manifest
        d = manifest.hub_root() / SUBDIR
        if d.is_dir():
            return d
    except Exception:
        pass
    for base in (REPO.parent, Path.home() / 'OneDrive - Portalcorp' / 'Documentos' / 'Hub-Marcas-Inputs'):
        d = base / SUBDIR
        if d.is_dir():
            return d
    return None


def parse_yq(fname):
    m = re.search(r'(1er|2do|3er|4to)\s*(?:trm|trim(?:estre)?)\s*(\d{4})', fname, re.I)
    if not m:
        return None
    return (m.group(2), QN[m.group(1).lower()])


def leer(path):
    """{familia: dict con las bases absolutas del trimestre}. Acepta los dos formatos
    (fila de familia con Producto=='Totales' o con Producto VACIO)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.worksheets[0].iter_rows(values_only=True))
    wb.close()
    if not rows:
        return {}
    hdr = [str(c or '').strip().lower() for c in rows[0]]

    def col(*names):
        for i, h in enumerate(hdr):
            if any(n in h for n in names):
                return i
        return None
    c_fam, c_prod = col('familia'), col('producto')
    c_uni = col('unidades facturadas')
    c_pconv = col('% convenio', 'convenio uni')
    c_conv = col('convenios')
    c_neto = col('$ neto facturado')
    c_dtot = col('% dto total')
    if None in (c_fam, c_prod, c_uni, c_pconv):
        return {}

    def f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    out = {}
    for r in rows[1:]:
        fam = str(r[c_fam] or '').strip()
        prod = str(r[c_prod] or '').strip()
        if not fam or fam.lower() in ('totales', 'total'):
            continue
        if prod.lower() not in ('', 'totales'):
            continue
        uni, pconv = f(r[c_uni]), f(r[c_pconv])
        if uni is None or pconv is None:
            continue
        conv = f(r[c_conv]) if c_conv is not None else None
        neto = f(r[c_neto]) if c_neto is not None else None
        dtot = f(r[c_dtot]) if c_dtot is not None else None
        # bruto_hipotetico no viene en el export; se despeja de neto/(1+%dto total).
        # Validado contra Convenios/(%dto conv): 169 familias coinciden, 0 difieren.
        bruto = (neto / (1 + dtot)) if (neto is not None and dtot is not None and (1 + dtot)) else None
        out[fam] = {
            'uni': uni,
            'consumo': pconv * uni,      # consumo BRUTO, el que usa la fuente para el %
            'conv_pesos': conv,
            'neto': neto,
            'bruto': bruto,
        }
    return out


def acumular(trimestres):
    """Suma una lista de {familia: bases} en un solo periodo."""
    acc = {}
    for t in trimestres:
        for fam, v in t.items():
            a = acc.setdefault(fam, {'uni': 0.0, 'consumo': 0.0, 'conv_pesos': 0.0,
                                     'neto': 0.0, 'bruto': 0.0, 'bruto_ok': True})
            a['uni'] += v['uni']
            a['consumo'] += v['consumo']
            for k in ('conv_pesos', 'neto', 'bruto'):
                if v[k] is None:
                    a['bruto_ok'] = a['bruto_ok'] and k != 'bruto'
                else:
                    a[k] += v[k]
    return acc


def pct(num, den):
    return round(num / den * 100, 1) if den else None


def armar(cur, prev):
    """Los 18 campos de D.canales[familia] para un periodo y su comparable."""
    u = cur['uni']
    if u <= 0:                       # sin base: nada medible, el render la descarta
        return None
    c = pct(cur['consumo'], u)
    # consumo > facturado: el mostrador sale por RESTA, asi que ni el % ni las unidades
    # son medibles (darian negativas). Se conserva el convenio real y el resto va None.
    excede = c is None or c > 100
    m = None if excede else round(100 - c, 1)
    most_u = None if excede else int(round(u - cur['consumo']))

    out = {
        'unid': int(round(u)),
        'conv': c,
        'most': m,
        'conv_units': int(round(cur['consumo'])),
        'most_units': most_u,
        'dto_total': None, 'dto_conv': None, 'dto_most': None,
        'unid_prev': None, 'conv_prev': None, 'most_prev': None,
        'conv_units_prev': None, 'most_units_prev': None,
        'dto_total_prev': None, 'dto_conv_prev': None, 'dto_most_prev': None,
        'conv_pp': None, 'most_pp': None,
    }
    if cur.get('bruto'):
        b = cur['bruto']
        out['dto_conv'] = round(cur['conv_pesos'] / b * 100, 1)
        out['dto_total'] = round((cur['neto'] / b - 1) * 100, 1)
        out['dto_most'] = round(out['dto_total'] - out['dto_conv'], 1)

    if prev and prev['uni'] > 0:
        up = prev['uni']
        cp = pct(prev['consumo'], up)
        excede_p = cp is None or cp > 100
        out['unid_prev'] = int(round(up))
        out['conv_prev'] = cp
        out['most_prev'] = None if excede_p else round(100 - cp, 1)
        out['conv_units_prev'] = int(round(prev['consumo']))
        out['most_units_prev'] = None if excede_p else int(round(up - prev['consumo']))
        if prev.get('bruto'):
            b = prev['bruto']
            out['dto_conv_prev'] = round(prev['conv_pesos'] / b * 100, 1)
            out['dto_total_prev'] = round((prev['neto'] / b - 1) * 100, 1)
            out['dto_most_prev'] = round(out['dto_total_prev'] - out['dto_conv_prev'], 1)
        if c is not None and cp is not None:
            out['conv_pp'] = round(c - cp, 1)
            if out['most'] is not None and out['most_prev'] is not None:
                out['most_pp'] = round(out['most'] - out['most_prev'], 1)
    return out


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    check_only = '--check' in sys.argv
    d = hub_dir()
    if d is None:
        print('  (skip) no se encontro la carpeta convenios NUEVO en hubRoot')
        return 0
    try:
        import openpyxl  # noqa
    except ImportError:
        print('  (skip) openpyxl no disponible')
        return 0

    # un archivo por (anio,Q); gana 'Convenios vs mostrador' sobre el formato viejo
    mejor = {}
    for f in sorted(d.glob('*.xlsx')):
        yq = parse_yq(f.name)
        if not yq:
            continue
        prio = 2 if 'convenios vs mostrador' in f.name.lower() else 1
        if mejor.get(yq, (0, None))[0] < prio:
            mejor[yq] = (prio, f)
    if not mejor:
        print('  (skip) sin planillas trimestrales')
        return 0

    datos = {}
    for (y, q), (_, f) in mejor.items():
        fam = leer(f)
        if fam:
            datos[(y, q)] = fam
    if not datos:
        print('  (skip) las planillas no traen filas de familia')
        return 0

    anio = max(y for y, _ in datos)
    qs = sorted(q for y, q in datos if y == anio)
    anio_prev = str(int(anio) - 1)
    qs_prev = [q for q in qs if (anio_prev, q) in datos]
    if qs_prev != qs:
        print(f'  (aviso) {anio_prev} no tiene {sorted(set(qs) - set(qs_prev))}: '
              f'el comparable YTD usa {qs_prev or "nada"}')

    cur = acumular([datos[(anio, q)] for q in qs])
    prev = acumular([datos[(anio_prev, q)] for q in qs_prev]) if qs_prev else {}

    desde, hasta = QMESES[qs[0]][0], QMESES[qs[-1]][1]
    label = f'YTD {anio} ({desde}–{hasta}) vs {anio_prev}'
    print(f'  ventana: {anio} {"+".join(qs)} vs {anio_prev} {"+".join(qs_prev) or "(sin comparable)"}')
    print(f'  label  : {label}')
    print(f'  familias en fuente: {len(cur)}')

    total_changed = 0
    for rel in LINES:
        p = REPO / rel
        t = p.read_text(encoding='utf-8-sig')
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
        if not m:
            continue
        ob = t.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(t[ob:])
        fams = set(D.get('mol_perf', {})) | set(D.get('budget', {})) | set(D.get('canales', {}))

        es_mujer = rel.startswith('mujer/')

        def bases(fam, periodo):
            """Bases de la familia en el periodo. En mujer, la suma de las familias de
            producto que componen el segmento."""
            if not es_mujer:
                return periodo.get(fam)
            fuentes = MUJER_SEG.get(fam)
            if fuentes is None:                       # segmento sin mapa: intenta por nombre
                return periodo.get(fam)
            if not fuentes:                           # mapeado a [] a proposito
                return None
            partes = [periodo[f] for f in fuentes if f in periodo]
            if not partes:
                return None
            tot = {'uni': 0.0, 'consumo': 0.0, 'conv_pesos': 0.0, 'neto': 0.0, 'bruto': 0.0}
            for p_ in partes:
                for k in tot:
                    tot[k] += p_.get(k) or 0.0
            return tot

        nuevo, sin_base, sin_prev = {}, 0, 0
        for fam in sorted(fams):
            b_cur = bases(fam, cur)
            if not b_cur:
                continue
            e = armar(b_cur, bases(fam, prev))
            if e is None:
                sin_base += 1
                continue
            nuevo[fam] = e
            if e['conv_pp'] is None:
                sin_prev += 1

        meta = D.get('meta')
        meta_nueva = dict(meta) if isinstance(meta, dict) else None
        if meta_nueva is not None:
            meta_nueva['canales_label'] = label
            meta_nueva['canales_current_year'] = int(anio)
            meta_nueva['canales_prev_year'] = int(anio_prev)
            meta_nueva['canales_year'] = int(anio)

        cambia = D.get('canales') != nuevo or (meta_nueva is not None and meta != meta_nueva)
        if cambia:
            total_changed += 1
            if not check_only:
                D['canales'] = nuevo
                if meta_nueva is not None:
                    D['meta'] = meta_nueva
                p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                             encoding='utf-8', newline='')
        con_delta = len(nuevo) - sin_prev
        print(f'  {rel:<24} {len(nuevo):>3} familias  ({con_delta} con delta interanual'
              f'{f", {sin_base} sin base" if sin_base else ""})'
              f' {"(a actualizar)" if check_only and cambia else ""}')
        # mujer: avisar que familias de la fuente no caen en ningun segmento, para que
        # el volumen sin asignar no quede en silencio (los nombres de CloseUp vienen
        # truncados a 20 chars y no siempre son los mismos que en SAP).
        if es_mujer:
            usadas = {f for seg in MUJER_SEG.values() for f in seg}
            libres = [(f, cur[f]['uni']) for f in cur
                      if f not in usadas and cur[f]['uni'] > 1000
                      and any(k in f.upper() for k in ('CALCIO', 'CITRATO', 'ISIS',
                                                       'SIDERBLUT', 'TRIP', 'DUPOMAR'))]
            for f, u in sorted(libres, key=lambda x: -x[1]):
                print(f'      (sin asignar a ningun segmento) {f}: {u:,.0f} u YTD')

    if check_only and total_changed:
        print(f'CANALES-YTD: {total_changed} data.js desactualizados. '
              f'Correr: py shared/build-canales-ytd.py')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
