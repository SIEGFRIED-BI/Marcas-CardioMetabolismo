# -*- coding: utf-8 -*-
"""Construye D.canales_quarterly[familia][anio][Qn] = {c: %convenio, m: %mostrador}
desde las planillas trimestrales 'Convenios vs mostrador' (hubRoot/convenios NUEVO).

La seccion 'Mostrador vs Convenios (trimestral)' del tablero ya espera ese campo
(renderCanQuartTable lee D.canales_quarterly) pero estaba vacio. Esto lo puebla por
trimestre/anio, SOLO para las familias que hoy estan en cada tablero (no agrega extra).

Fuente: filas a nivel FAMILIA, columnas '% convenio UNI' y '% mostrador UNI' (se
detectan por header). Los % vienen como fraccion (0..1) y en la fuente se cumple
SIEMPRE %mostrador == 1 - %convenio (verificado: 0 de 1264 filas lo violan), o sea
mostrador es un RESIDUO, no una medicion propia.

DOS FORMATOS de planilla, y la fila de familia se marca distinto en cada uno:
    'Convenios vs mostrador - <fecha> <N> trimestre <AAAA>.xlsx'  -> Producto == 'Totales'
    '<N> trm <AAAA>.xlsx'  (formato viejo)                        -> Producto VACIO
Antes solo se aceptaba 'Totales', asi que los 13 archivos viejos se leian y se
descartaban EN SILENCIO -> 2023 y 2024 enteros (8 trimestres) nunca llegaban al
tablero. Ahora se aceptan los dos. Son mutuamente excluyentes (0 familias aparecen
con las dos marcas en un mismo archivo), asi que no hay doble conteo.
Control que habilita mezclarlos: en 2025 Q1/Q2/Q3, donde existen ambos archivos, los
dos formatos dan el MISMO % en las 70 familias comunes (0 difieren >0.15pp).
Donde hay dos archivos para el mismo (anio,Q) gana el 'Convenios vs mostrador': en
2026 Q1 factura lo mismo pero trae mas consumo (CloseUp madura: llegan reportes tarde).

ANOMALIA %convenio > 100: pasa cuando el consumo por convenio del trimestre (CloseUp)
supera las unidades facturadas del trimestre (SAP) -- desfasaje entre facturacion y
dispensa, no un error de cuenta. El residuo 'mostrador' se vuelve NEGATIVO y el tablero
llegaba a mostrar '-156% mostrador' (DELTROX 2026Q1). Se conserva el %convenio REAL (no
se clampea: es la senal) y se marca la celda con x=True + m=None -> el render ya pinta
None como '—' y agrega la nota al pie.
Idempotente. Skipea si falta openpyxl o la carpeta.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent
REPO = SHARED.parent
sys.path.insert(0, str(SHARED))

LINES = ['cardio/data.js','ATB/data.js','OTC/data.js','respiratorio/data.js',
         'mujer/data.js','SNC/data.js','dermatologia/data.js']
SUBDIR = 'convenios NUEVO'
QMAP = {'1er':'Q1','1ER':'Q1','2do':'Q2','2DO':'Q2','3er':'Q3','3ER':'Q3','4to':'Q4','4TO':'Q4'}

# mujer: segmento de marketing -> familias de producto de la fuente. Fuente real:
# close-manifest.json (seg mujer_venta_segments), igual que merge-ventas-internas.py.
_MUJER_FALLBACK = {
    'SIN ESTROGENO': ['ISIS FREE'], 'ALTA DOSIS': ['ISIS'],
    'BAJA DOSIS 21+7': ['ISIS MINI'], 'BAJA DOSIS 24': ['ISIS MINI 24'],
    'COMPLEX': ['SIDERBLUT COMPLEX', 'SIDERBLUT FOLIC'],
    'SOLO': ['SIDERBLUT', 'SIDERBLUT POLI', 'FERINSOL'],
    'DELTROX': ['DELTROX'], 'BASE': ['CALCIO BASE DUPOMAR'],
    'BASE D': ['CALCIO BASE DUPOMAR D', 'CALCIO BASE DUPOMAR D3', 'CALCIO CITRATO DUPOMAR D3'],
    'CLIMATIX': ['CLIMATIX'], 'D3': [], 'D3 PLUS': [], '45': [], 'MAGNESIO': [],
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


def parse_yq2(fname):
    # 'Ner trm 2023' (viejo) y 'Ner trimestre 2025' (nuevo)
    m = re.search(r'(1er|2do|3er|4to)\s*(?:trm|trim(?:estre)?)\s*(\d{4})', fname, re.I)
    if not m:
        return None
    q = {'1er':'Q1','2do':'Q2','3er':'Q3','4to':'Q4'}.get(m.group(1).lower())
    return (m.group(2), q) if q else None


def read_file_familia(path):
    """Devuelve ({familia: {'c':pct, 'm':pct[, 'x':True]}}, motivo_si_vacio)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return {}, 'archivo vacio'
    hdr = [str(c or '').strip().lower() for c in rows[0]]
    def col(*names):
        for i, h in enumerate(hdr):
            if any(n in h for n in names):
                return i
        return None
    c_fam = col('familia')
    c_prod = col('producto')
    c_conv = col('% convenio', 'convenio uni', '%convenio')
    c_most = col('% mostrador', 'mostrador uni', '%mostrador')
    c_fact = col('unidades facturadas')
    if None in (c_fam, c_prod, c_conv, c_most):
        falta = [n for n, c in (('familia', c_fam), ('producto', c_prod),
                                ('% convenio', c_conv), ('% mostrador', c_most)) if c is None]
        return {}, f'faltan columnas: {", ".join(falta)}'
    out = {}
    for r in rows[1:]:
        fam = str(r[c_fam] or '').strip()
        prod = str(r[c_prod] or '').strip()
        if not fam or fam.lower() in ('totales', 'total'):
            continue
        # nivel FAMILIA: 'Totales' en el formato nuevo, VACIO en el viejo
        if prod.lower() not in ('', 'totales'):
            continue
        try:
            conv = float(r[c_conv]); most = float(r[c_most])
        except (TypeError, ValueError):
            continue
        fact = r[c_fact] if c_fact is not None else None
        # los % vienen como fraccion (0..1)
        c = round(conv * 100, 1)
        m = round(most * 100, 1)

        # Los tres casos, explicitos. El % de convenio es consumo/facturado del
        # trimestre, y el de mostrador sale por RESTA -- asi que el resultado solo es
        # interpretable si el denominador es positivo y el consumo no lo supera.
        if isinstance(fact, (int, float)) and fact <= 0:
            # base <= 0: las devoluciones netas del trimestre igualan o superan lo
            # facturado. No hay universo contra el que medir: ni convenio ni mostrador
            # significan nada (se vieron ratios de -1160% y +255%).
            out[fam] = {'c': None, 'm': None, 'x': 'base'}
        elif c > 100 or m < 0 or c < 0 or m > 100:
            # consumo del trimestre > facturado del trimestre: el residuo 'mostrador'
            # no es medible. Se conserva el %convenio real y se declara el limite.
            out[fam] = {'c': c, 'm': None, 'x': 'desfasaje'}
        else:
            out[fam] = {'c': c, 'm': m}
    if not out:
        return {}, f'0 filas a nivel familia (se miraron {len(rows) - 1} filas)'
    return out, ''


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

    # accum[familia][anio][Q] = {c,m}. Si hay 2 archivos para el mismo (anio,Q),
    # gana el de nombre 'Convenios vs mostrador' (mas nuevo) sobre 'Ner trm'.
    # Se leen TODAS y se ordena por prioridad DESPUES, para poder reportar los archivos
    # que no aportan nada (antes se descartaban en silencio: 13 planillas, 8 trimestres).
    files = sorted(d.glob('*.xlsx'))
    leidos = {}   # (anio,Q) -> [(prio, nombre, fam_data)]
    vacios = []
    ignorados = []
    for f in files:
        yq = parse_yq2(f.name)
        if not yq:
            ignorados.append(f.name)
            continue
        year, q = yq
        prio = 2 if 'convenios vs mostrador' in f.name.lower() else 1
        fam_data, motivo = read_file_familia(f)
        if not fam_data:
            vacios.append((f.name, motivo))
            continue
        leidos.setdefault((year, q), []).append((prio, f.name, fam_data))

    if not leidos:
        print('  (skip) sin datos en las planillas')
        return 0

    accum = {}
    anomalias = []
    for (year, q), cands in sorted(leidos.items()):
        cands.sort(key=lambda x: -x[0])
        prio, name, fam_data = cands[0]
        # control: si hay dos fuentes para el mismo trimestre, cuanto difieren
        if len(cands) > 1:
            otro = cands[1][2]
            comunes = set(fam_data) & set(otro)
            difs = [k for k in comunes
                    if abs((fam_data[k]['c'] or 0) - (otro[k]['c'] or 0)) > 0.15]
            if difs:
                print(f'    {year} {q}: 2 fuentes, gana {name[:44]!r} '
                      f'({len(difs)}/{len(comunes)} familias difieren >0.15pp)')
        for fam, cm in fam_data.items():
            accum.setdefault(fam, {}).setdefault(year, {})[q] = cm
            if cm.get('x'):
                anomalias.append((cm['x'], fam, year, q, cm.get('c')))

    print(f'  planillas: {len(leidos)} (anio,Q) de {len(files)} archivos; '
          f'familias en fuente: {len(accum)}')
    print(f'  trimestres: {", ".join(f"{y}{q}" for y, q in sorted(leidos))}')
    if vacios:
        print(f'  ATENCION: {len(vacios)} planilla(s) sin filas utilizables '
              f'(antes se descartaban en silencio):')
        for name, motivo in vacios:
            print(f'      {name[:60]:<60} {motivo}')
    desf = [a for a in anomalias if a[0] == 'desfasaje']
    base = [a for a in anomalias if a[0] == 'base']
    if desf:
        print(f'  {len(desf)} celda(s) con consumo del trimestre > facturado: se publica el '
              f'%convenio real y el mostrador (residuo) queda "—".')
        for _, fam, y, q, c in desf[:5]:
            print(f'      {fam} {y}{q} convenio={c}%')
        if len(desf) > 5:
            print(f'      ... y {len(desf) - 5} mas')
    if base:
        print(f'  {len(base)} celda(s) con Unidades facturadas <= 0 (devoluciones netas '
              f'>= facturacion): NADA medible, van "—"/"—".')
        for _, fam, y, q, c in base[:5]:
            print(f'      {fam} {y}{q}')
        if len(base) > 5:
            print(f'      ... y {len(base) - 5} mas')

    total_changed = 0
    for rel in LINES:
        p = REPO / rel
        t = p.read_text(encoding='utf-8-sig')
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', t)
        if not m:
            continue
        ob = t.index('{', m.end())
        D, end = json.JSONDecoder().raw_decode(t[ob:])
        # familias del tablero (las que hoy existen): mol_perf + budget + canales
        fams = set(D.get('mol_perf', {})) | set(D.get('budget', {})) | set(D.get('canales', {}))
        cq = {fam: accum[fam] for fam in accum if fam in fams}
        # mujer keyea por SEGMENTO (ALTA DOSIS, SIN ESTROGENO...) y la fuente trae
        # FAMILIAS de producto (ISIS, ISIS FREE...): sin el mapa quedaban 2 de 12
        # segmentos. Mismo mapa que build-canales-ytd y merge-ventas-internas.
        if rel.startswith('mujer/'):
            for seg, fuentes in MUJER_SEG.items():
                if seg not in fams or seg in cq or not fuentes:
                    continue
                por_anio = {}
                for f in fuentes:
                    for y, to in (accum.get(f) or {}).items():
                        for q, cm in to.items():
                            por_anio.setdefault(y, {}).setdefault(q, []).append(cm)
                # el % de un segmento no es el promedio de sus familias: se pondera por
                # las unidades, que no estan en accum -> solo se toma cuando el segmento
                # se compone de UNA sola familia (el resto queda sin dato, no mal sumado).
                if len(fuentes) == 1:
                    unico = accum.get(fuentes[0])
                    if unico:
                        cq[seg] = unico
        new = {k: cq[k] for k in sorted(cq)}
        if D.get('canales_quarterly') != new:
            total_changed += 1
            if not check_only:
                D['canales_quarterly'] = new
                p.write_text(t[:ob] + json.dumps(D, ensure_ascii=False) + t[ob + end:],
                             encoding='utf-8', newline='')
        print(f'  {rel}: {len(new)} familias con trimestral '
              f'({"a actualizar" if check_only else "ok"})')
    if check_only and total_changed:
        print(f'CANALES-QUARTERLY: {total_changed} data.js desactualizados. '
              f'Correr: py shared/build-canales-quarterly.py')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
