# -*- coding: utf-8 -*-
"""Construye D.canales_quarterly[familia][anio][Qn] = {c: %convenio, m: %mostrador}
desde las planillas trimestrales 'Convenios vs mostrador' (hubRoot/convenios NUEVO).

La seccion 'Mostrador vs Convenios (trimestral)' del tablero ya espera ese campo
(renderCanQuartTable lee D.canales_quarterly) pero estaba vacio. Esto lo puebla por
trimestre/anio, SOLO para las familias que hoy estan en cada tablero (no agrega extra).

Fuente: filas a nivel FAMILIA (col 'Producto' == 'Totales'), columnas '% convenio UNI'
y '% mostrador UNI' (se detectan por header, robusto a ambos formatos de planilla).
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
    """Devuelve {familia: {'c':pct, 'm':pct}} a nivel familia."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return {}
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
    if None in (c_fam, c_prod, c_conv, c_most):
        return {}
    out = {}
    for r in rows[1:]:
        fam = str(r[c_fam] or '').strip()
        prod = str(r[c_prod] or '').strip()
        if not fam or fam.lower() in ('totales', 'total') or prod.lower() != 'totales':
            continue
        try:
            conv = float(r[c_conv]); most = float(r[c_most])
        except (TypeError, ValueError):
            continue
        # los % vienen como fraccion (0..1)
        out[fam] = {'c': round(conv * 100, 1), 'm': round(most * 100, 1)}
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

    # accum[familia][anio][Q] = {c,m}. Si hay 2 archivos para el mismo (anio,Q),
    # gana el de nombre 'Convenios vs mostrador' (mas nuevo) sobre 'Ner trm'.
    files = sorted(d.glob('*.xlsx'))
    accum = {}
    seen = {}  # (anio,Q) -> prioridad usada
    for f in files:
        yq = parse_yq2(f.name)
        if not yq:
            continue
        year, q = yq
        prio = 2 if 'convenios vs mostrador' in f.name.lower() else 1
        if seen.get((year, q), 0) >= prio:
            continue
        fam_data = read_file_familia(f)
        if not fam_data:
            continue
        seen[(year, q)] = prio
        for fam, cm in fam_data.items():
            accum.setdefault(fam, {}).setdefault(year, {})[q] = cm

    if not accum:
        print('  (skip) sin datos en las planillas')
        return 0
    print(f'  planillas: {len(seen)} (anio,Q); familias en fuente: {len(accum)}')

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
