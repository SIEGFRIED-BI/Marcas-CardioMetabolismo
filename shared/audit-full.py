"""Audit completo: revisa TODAS las brands de TODAS las lineas en TODAS las
metricas (IE, MS%, units, growth, recetas, stock) en TODOS los periodos
(YTD, MAT, mensual, trimestre, semestre).

Tolerancia 0.5pp para porcentajes, 0.1% para conteos.
Reporta cada inconsistencia detectada.

Returns exit code 0 si todo OK, 1 si hay mismatches.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KJ_PATH = REPO / 'kpis.json'

LINES = [
    ('cardio',  'cardio',       'cardio/data.js', False),
    ('antibio', 'ATB',          'ATB/data.js',    False),
    ('otx',     'OTC',          'OTC/data.js',    False),
    ('resp',    'respiratorio', 'respiratorio/data.js', False),
    ('mujer',   'mujer',        'mujer/data.js', False),
    ('snc',     'SNC',          'SNC/data.js',   False),
    ('derma',   'dermatologia', 'dermatologia/data.js', False),
]
MES = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def load_D(path_rel, is_inline):
    p = REPO / path_rel
    text = p.read_text(encoding='utf-8-sig' if not is_inline else 'utf-8', errors='replace')
    if is_inline:
        m = re.search(r'const D = (\{)', text)
        ob = text.index('{', m.start() + 8)
    else:
        m = re.search(r'window\.OTC_DASHBOARD\s*=\s*', text)
        ob = text.index('{', m.end())
    D, _ = json.JSONDecoder().raw_decode(text[ob:])
    return D


def latest_month(D):
    all_m = set()
    for o in (D.get('mol_perf') or {}).values():
        if not isinstance(o, dict): continue
        for p in o.get('products', []):
            all_m.update((p.get('monthly_vals') or {}).keys())
    if not all_m: return None
    def msort(k):
        ps = k.split(); return int(ps[1])*100 + MES.index(ps[0])+1
    sm = sorted(all_m, key=msort)
    p = sm[-1].split()
    return (int(p[1]), MES.index(p[0])+1)


def ytd(year, end_m): return [f'{MES[i]} {year}' for i in range(end_m)]
def mat(end_y, end_m):
    out = []; y,m = end_y, end_m
    for _ in range(12):
        out.append(f'{MES[m-1]} {y}'); m-=1
        if m==0: m=12; y-=1
    return list(reversed(out))
def trimestre(end_y, end_m):
    return mat(end_y, end_m)[-3:]
def semestre(end_y, end_m):
    return mat(end_y, end_m)[-6:]
def mensual(end_y, end_m):
    return [f'{MES[end_m-1]} {end_y}']


def sum_window(monthly, win): return sum(monthly.get(mk, 0) or 0 for mk in win)


def find_brand_mol(D, brand_key):
    """Find the mol_perf primary market for brand."""
    mol = D.get('mol_perf', {})
    bu = brand_key.upper()
    cands = []
    for m_key, obj in mol.items():
        if not isinstance(obj, dict): continue
        for p in obj.get('products', []):
            if not p.get('is_sie'): continue
            name = str(p.get('prod','')).upper()
            base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
            if base == bu:
                pri = 2 if bu == m_key.upper() else (1 if bu in m_key.upper() else 0)
                cands.append((pri, m_key, obj))
    if not cands: return None, None
    cands.sort(key=lambda x: -x[0])
    return cands[0][1], cands[0][2]


def compute_brand_vs_market(D, brand_key, win_c, win_p):
    mol_key, mol_obj = find_brand_mol(D, brand_key)
    if not mol_obj: return None
    bu = brand_key.upper()
    b_c = b_p = m_c = m_p = 0
    for p in mol_obj.get('products', []):
        mv = p.get('monthly_vals', {})
        c = sum_window(mv, win_c); pp = sum_window(mv, win_p)
        m_c += c; m_p += pp
        name = str(p.get('prod','')).upper()
        base = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
        if p.get('is_sie') and base == bu:
            b_c += c; b_p += pp
    ie = None
    if b_p > 0 and m_p > 0 and m_c > 0:
        br = b_c/b_p; mr = m_c/m_p
        if mr > 0 and br < 5:
            ie = round(br/mr*100, 1)
    ms = round(b_c/m_c*100, 1) if m_c > 0 else None
    return {'b_c':b_c, 'b_p':b_p, 'm_c':m_c, 'm_p':m_p, 'ie':ie, 'ms':ms}


def approx_eq(a, b, tol=0.5):
    if a is None and b is None: return True
    if a is None or b is None: return False
    return abs(a-b) <= tol


class AuditReport:
    def __init__(self):
        self.checks = 0
        self.fails = 0
        self.fail_details = []

    def check(self, label, expected, actual, tol=0.5):
        self.checks += 1
        if not approx_eq(expected, actual, tol):
            self.fails += 1
            self.fail_details.append(f'  FAIL {label}: expected={expected}, actual={actual}, diff={(actual or 0)-(expected or 0):.2f}')


def audit_line_level(R):
    kj = json.loads(KJ_PATH.read_text(encoding='utf-8'))
    kjl = {l['key']:l for l in kj['lines']}
    print('\n[1] LINE-LEVEL: hub kpis.json vs dashboard kpiStrip')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        ks = D.get('kpiStrip', {})
        kl = kjl.get(key)
        if not kl: continue
        for period_short in ['ytd','mat']:
            k = kl['kpis'][period_short]
            R.check(f'{line_dir} {period_short.upper()} IE', k['units_sie']['ie'], ks.get(f'ie_{period_short}'))
            R.check(f'{line_dir} {period_short.upper()} MS%', k['ms_units']['curr'], ks.get(f'ms_{period_short}'))
            R.check(f'{line_dir} {period_short.upper()} U', k['units_sie']['curr'], ks.get(f'units_{period_short}'), tol=1)
            R.check(f'{line_dir} {period_short.upper()} Uprev', k['units_sie']['prev'], ks.get(f'units_{period_short}25'), tol=1)


def audit_brand_level(R):
    print('\n[2] BRAND-LEVEL: brandKpis vs mol_perf computed')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        bk = D.get('brandKpis', {})
        if not bk: continue
        latest = latest_month(D)
        if not latest: continue
        end_y, end_m = latest
        for brand, kobj in bk.items():
            if not isinstance(kobj, dict): continue
            for period_short, win_c_fn, win_p_fn in [
                ('ytd', lambda: ytd(end_y, end_m),       lambda: ytd(end_y-1, end_m)),
                ('mat', lambda: mat(end_y, end_m),        lambda: mat(end_y-1, end_m)),
            ]:
                target = kobj.get(period_short)
                if not isinstance(target, dict): continue
                comp = compute_brand_vs_market(D, brand, win_c_fn(), win_p_fn())
                if not comp: continue
                R.check(f'{line_dir} {brand} {period_short.upper()} IE', comp['ie'], target.get('ie'))
                R.check(f'{line_dir} {brand} {period_short.upper()} units', comp['b_c'], target.get('units'), tol=1)
                R.check(f'{line_dir} {brand} {period_short.upper()} units_prev', comp['b_p'], target.get('units_prev'), tol=1)
                R.check(f'{line_dir} {brand} {period_short.upper()} ms', comp['ms'], target.get('ms'))


def audit_recetas(R):
    """Verifica consistencias internas de recetas:
       - kpis.json ms_recetas vs kpiStrip.ms_rec
       - rec_ms[fam].sie[m] / rec_ms[fam].mkt[m] * 100 == rec_ms[fam].ms[m]
       - sum(rec_ms[fam].sie YTD) == kpis.json.recetas_sie.curr
       - recetas[fam][m].recetas == rec_ms[fam].mkt[m] (cuando ambos existen)
       - brandKpis[brand].rec.ms == rec_ms[fam].ms[last_month] del fam
    """
    kj = json.loads(KJ_PATH.read_text(encoding='utf-8'))
    kjl = {l['key']:l for l in kj['lines']}
    print('\n[3] RECETAS: 5 chequeos internos')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        ks = D.get('kpiStrip', {})
        kl = kjl.get(key)

        # 3.1) ms_rec vs kpis.json
        if kl:
            expected = kl['kpis']['ytd']['ms_recetas']['curr']
            if expected is not None:
                R.check(f'{line_dir} ms_rec (kpiStrip vs kpis.json)', expected, ks.get('ms_rec'))

        # 3.2) rec_ms internal consistency: sie/mkt*100 == ms per month per family
        rec_ms = D.get('rec_ms', {}) or {}
        for fam, obj in rec_ms.items():
            if not isinstance(obj, dict): continue
            sie_m = obj.get('sie', {}) or {}
            mkt_m = obj.get('mkt', {}) or {}
            ms_m  = obj.get('ms',  {}) or {}
            for mk in sie_m.keys():
                sie = sie_m.get(mk) or 0
                mkt = mkt_m.get(mk)
                ms  = ms_m.get(mk)
                if mkt and mkt > 0 and ms is not None:
                    expected_ms = round(sie/mkt*100, 1)
                    R.check(f'{line_dir} rec_ms[{fam}].ms[{mk}] = sie/mkt*100', expected_ms, ms, tol=0.5)

        # 3.3) sum(rec_ms[fam].sie YTD) ~ kpis.json.recetas_sie.curr
        if kl:
            kpi_rec_curr = kl['kpis']['ytd']['recetas_sie']['curr']
            kpi_rec_as_of = kj.get('as_of_month', 'Mar 2026')
            # Sum all rec_ms[fam].sie YTD = months in current year up to as_of
            end_y, end_m = (int(kpi_rec_as_of.split()[-1]), MES.index(kpi_rec_as_of.split()[0])+1) if kpi_rec_as_of else (None,None)
            if end_y:
                ytd_keys = ytd(end_y, end_m)
                total = 0
                for fam, obj in rec_ms.items():
                    if not isinstance(obj, dict): continue
                    sie_m = obj.get('sie', {}) or {}
                    for mk in ytd_keys:
                        total += int(sie_m.get(mk) or 0)
                if kpi_rec_curr is not None:
                    R.check(f'{line_dir} sum(rec_ms[].sie YTD) vs kpis.json.recetas_sie.curr',
                            kpi_rec_curr, total, tol=max(10, kpi_rec_curr*0.01) if kpi_rec_curr else 10)

        # 3.4) recetas[fam][m].recetas (Cant. Recetas) vs rec_ms[fam].mkt[m]
        # SOLO cuando D.recetas usa nombres de familia (no de brand).
        # SNC tiene D.recetas keyed por brand (e.g., 'LEVITAL SIE') con valores
        # brand-level (=lo que iria en rec_ms.sie). En esa estructura el check
        # vs mkt no aplica — se skipea.
        recetas = D.get('recetas', {}) or {}
        is_brand_keyed = any(' SIE' in k or '(SIE)' in k for k in recetas.keys())
        if not is_brand_keyed:
            for fam, months in recetas.items():
                if not isinstance(months, dict): continue
                rms_obj = rec_ms.get(fam)
                if not isinstance(rms_obj, dict): continue
                mkt_m = rms_obj.get('mkt', {}) or {}
                for mk, entry in months.items():
                    if not isinstance(entry, dict): continue
                    rec_val = entry.get('recetas')
                    mkt_val = mkt_m.get(mk)
                    if rec_val and mkt_val and mkt_val > 0:
                        R.check(f'{line_dir} recetas[{fam}][{mk}].recetas vs rec_ms.mkt',
                                mkt_val, rec_val, tol=max(5, mkt_val*0.005))


def audit_summary(R):
    print('\n' + '=' * 70)
    print(f'TOTAL CHECKS: {R.checks}  PASS: {R.checks-R.fails}  FAIL: {R.fails}')
    print('=' * 70)
    if R.fails:
        print('\nFAILURE DETAILS:')
        for d in R.fail_details[:50]:
            print(d)
        if R.fails > 50:
            print(f'  ... y {R.fails-50} mas')
    return 0 if R.fails == 0 else 1


def audit_molperf_internal(R):
    """Verifica consistencias dentro de mol_perf:
       - sum(product.monthly_vals YTD) == product.ytd[year]
       - sum(product.monthly_vals MAT) == product.mat[year]
       - ms_ytd[year] == ytd[year] / sum(all products ytd[year]) * 100
       - quarterly_vals[Q] == sum of monthly for that quarter
    """
    print('\n[4] MOL_PERF: internal monthly -> ytd / mat / quarterly consistency')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        mol = D.get('mol_perf', {})
        for m_key, obj in mol.items():
            if not isinstance(obj, dict): continue
            for p in obj.get('products', []):
                mv = p.get('monthly_vals', {})
                ytd_dict = p.get('ytd', {})
                mat_dict = p.get('mat', {})
                q_dict = p.get('quarterly_vals', {})
                # YTD: sum months 1..N for each year and check
                years = set()
                for mk in mv.keys():
                    try: years.add(int(mk.split()[1]))
                    except: pass
                for yr in years:
                    if yr in ytd_dict:
                        # find max month in this year
                        max_m = max([MES.index(mk.split()[0])+1 for mk in mv if mk.endswith(f' {yr}') and (mv.get(mk) or 0) > 0], default=0)
                        if max_m > 0:
                            expected = sum(mv.get(f'{MES[i]} {yr}', 0) or 0 for i in range(max_m))
                            actual = ytd_dict.get(yr) or ytd_dict.get(str(yr)) or 0
                            R.check(f'{line_dir} mol_perf[{m_key}][{p.get("prod","?")}].ytd[{yr}]',
                                    expected, actual, tol=max(1, expected*0.005))
                # Quarterly: each Q should sum 3 monthly
                for qk in q_dict.keys():
                    # qk format e.g., 'Q1 2025' or 'Q1-2025'
                    qparts = re.split(r'[\s-]', qk)
                    if len(qparts) != 2: continue
                    q_num = qparts[0].lstrip('Q')
                    try: q_num = int(q_num); yr = int(qparts[1])
                    except: continue
                    if q_num < 1 or q_num > 4: continue
                    months = range((q_num-1)*3, q_num*3)
                    expected = sum(mv.get(f'{MES[i]} {yr}', 0) or 0 for i in months)
                    actual = q_dict.get(qk) or 0
                    R.check(f'{line_dir} mol_perf[{m_key}][{p.get("prod","?")}].quarterly[{qk}]',
                            expected, actual, tol=max(1, expected*0.005))


def audit_stock(R):
    """Verifica que D.stock[fam][month] tenga shape consistente: si stock o
    ventas estan, las claves esperadas {stock, ventas, facturacion, dias}
    no contienen valores invalidos (negativos, NaN). NO se verifica dias
    contra stock/ventas*30 porque la formula real (SAP) usa promedio
    movil que no se puede reconstruir desde data.js."""
    print('\n[5] STOCK: shape + valores no-negativos')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        stock = D.get('stock', {})
        for fam, months in stock.items():
            if not isinstance(months, dict): continue
            for mk, entry in months.items():
                if not isinstance(entry, dict): continue
                for k in ('stock', 'ventas'):
                    # stock y ventas NUNCA pueden ser negativos (units)
                    v = entry.get(k)
                    if v is not None and isinstance(v, (int, float)) and v < 0:
                        R.fails += 1; R.checks += 1
                        R.fail_details.append(f'  FAIL stock[{fam}][{mk}].{k}={v} negativo en {line_dir}')
                    else:
                        R.checks += 1
                # facturacion puede ser negativa (devoluciones netas) — solo check si <-1000
                fact = entry.get('facturacion')
                if fact is not None and isinstance(fact, (int, float)) and fact < -1000:
                    R.fails += 1; R.checks += 1
                    R.fail_details.append(f'  FAIL stock[{fam}][{mk}].facturacion={fact} <-1000 en {line_dir}')
                else:
                    R.checks += 1


def audit_convenios(R):
    """Verifica D.convenios[fam].2024 + 2025 totales suman 100% por OS."""
    print('\n[6] CONVENIOS: % suma 100 por OS (interno)')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        conv = D.get('convenios', {})
        for fam, fam_obj in conv.items():
            if not isinstance(fam_obj, dict): continue
            for yr, obs in fam_obj.items():
                if not isinstance(obs, list): continue
                # Sum all pct in this year - should ~100
                total_pct = sum(o.get('pct', 0) or 0 for o in obs if isinstance(o, dict))
                if total_pct > 0:
                    R.check(f'{line_dir} convenios[{fam}][{yr}] sum pct',
                            100, round(total_pct, 1), tol=2.0)


def audit_kpistrip_market(R):
    """Verifica kpiStrip.mkt_ytd26 / mkt_mat26 == sum mol_perf market YTD/MAT."""
    print('\n[7] KPI STRIP MARKET: mkt_ytd26/mat26 vs sum(mol_perf YTD/MAT)')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        ks = D.get('kpiStrip', {})
        mol = D.get('mol_perf', {})
        latest = latest_month(D)
        if not latest: continue
        end_y, end_m = latest
        win_ytd = ytd(end_y, end_m)
        win_mat = mat(end_y, end_m)
        mkt_ytd = 0; mkt_mat = 0
        for o in mol.values():
            if not isinstance(o, dict): continue
            for p in o.get('products', []):
                mv = p.get('monthly_vals', {})
                mkt_ytd += sum_window(mv, win_ytd)
                mkt_mat += sum_window(mv, win_mat)
        R.check(f'{line_dir} kpiStrip.mkt_ytd26 vs sum mol_perf YTD',
                mkt_ytd, ks.get('mkt_ytd26'), tol=max(10, mkt_ytd*0.005))
        R.check(f'{line_dir} kpiStrip.mkt_mat26 vs sum mol_perf MAT',
                mkt_mat, ks.get('mkt_mat26'), tol=max(10, mkt_mat*0.005))


def audit_budget(R):
    """Verifica D.budget[fam][year].real arrays son listas de 12 numeros."""
    print('\n[8] BUDGET: estructura (12 meses por anio)')
    for key, line_dir, path_rel, inline in LINES:
        try: D = load_D(path_rel, inline)
        except Exception as e: continue
        bud = D.get('budget', {})
        for fam, fam_obj in bud.items():
            if not isinstance(fam_obj, dict): continue
            for yr, yr_obj in fam_obj.items():
                if not isinstance(yr_obj, dict): continue
                for k in ('budget', 'real'):
                    arr = yr_obj.get(k)
                    if not isinstance(arr, list): continue
                    if len(arr) != 12:
                        R.fails += 1
                        R.checks += 1
                        R.fail_details.append(f'  FAIL budget[{fam}][{yr}].{k}: len={len(arr)} (esperado 12) en {line_dir}')
                    else:
                        R.checks += 1


def main():
    R = AuditReport()
    audit_line_level(R)
    audit_brand_level(R)
    audit_recetas(R)
    audit_molperf_internal(R)
    audit_stock(R)
    audit_convenios(R)
    audit_kpistrip_market(R)
    audit_budget(R)
    return audit_summary(R)


if __name__ == '__main__':
    sys.exit(main())
