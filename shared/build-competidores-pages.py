#!/usr/bin/env python3
"""
shared/build-competidores-pages.py

Crea una pagina dedicada "Competidores DDD" por linea con heatmap
geografico (Provincia + Region CUP), filtros, busqueda y selectores
de periodo (M/Q/S/YTD/MAT) y metrica (MS% / dMS% pp / dUnits %).

Para cada linea genera:
  <line>/DDD/competidores.html   - pagina standalone
  <line>/DDD/competidores-data.js - SOLO para Shape A (cardio/SNC/dermato);
                                    extrae el `const D = {...}` del main DDD
                                    y lo expone como window.SFG_COMP_DATA

Para Shape B (ATB/OTC/respi/mujer) la pagina carga `../data.js` (window.OTC_DATA)
ya existente.

Tambien agrega un nav-tab "Competidores" en la pagina principal del DDD
que abre competidores.html.
"""
from __future__ import annotations
import re, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Per-line config
LINES = [
    # (name, shape, ddd_main_path, line_color)
    ('cardio',       'A', 'cardio/DDD/index.html',           '#7A1518'),
    ('SNC',          'A', 'SNC/DDD/psq_ddd.html',            '#7A1518'),
    ('dermatologia', 'A', 'dermatologia/dermato_ddd.html',   '#7A1518'),
    ('ATB',          'B', 'ATB/DDD/index.html',              '#7A1518'),
    ('OTC',          'B', 'OTC/DDD/index.html',              '#7A1518'),
    ('respiratorio', 'B', 'respiratorio/DDD/index.html',     '#7A1518'),
    ('mujer',        'B', 'mujer/DDD/index.html',            '#7A1518'),
]

LINE_TITLES = {
    'cardio':       'Cardio-Metabolismo',
    'SNC':          'Psiquiatría',
    'dermatologia': 'Dermatología',
    'ATB':          'Antibióticos',
    'OTC':          'OTC',
    'respiratorio': 'Respiratorio',
    'mujer':        'Línea Mujer',
}


def extract_shape_a_data(html_path: Path) -> str:
    """Find the 'const D = {...};' block in the main DDD HTML and return the
       JSON string of D (best effort — uses bracket matching)."""
    text = html_path.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'\bconst\s+D\s*=\s*\{', text)
    if not m:
        m = re.search(r'__SFG_DDD_EXPORT__\s*=\s*\{', text)
        if not m: raise RuntimeError(f'no D found in {html_path}')
    # Find matching brace
    start = text.index('{', m.end()-1)
    depth = 0
    in_str = False
    str_ch = ''
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if esc:
            esc = False; continue
        if c == '\\':
            esc = True; continue
        if in_str:
            if c == str_ch: in_str = False
            continue
        if c == '"' or c == "'":
            in_str = True; str_ch = c; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise RuntimeError(f'unbalanced braces in {html_path}')


# ── HTML template (data shape is selected at load time) ──────────────
PAGE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Siegfried · Competidores DDD · __TITLE__</title>
<style>
:root{--sie:#7A1518;--ink:#1a1a1a;--mut:#737373;--bg:#fafafa;--card:#fff;--bord:#e5e5e5;}
*{box-sizing:border-box;}
body{margin:0;font-family:'Inter','IBM Plex Sans',-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--ink);font-size:13px;}
/* Unified nav (same as main dashboard) */
.nav{position:sticky;top:0;z-index:200;height:50px;background:#ffffff;border-bottom:2px solid var(--sie);box-shadow:0 1px 8px rgba(0,0,0,.08);display:flex;align-items:center;padding:0 24px;}
.nav-back{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;color:var(--sie);letter-spacing:.12em;text-transform:uppercase;text-decoration:none;border:1px solid rgba(122,21,24,.3);border-radius:6px;padding:6px 12px;margin-right:14px;white-space:nowrap;transition:all .15s;display:inline-flex;align-items:center;gap:6px;}
.nav-back:hover{background:var(--sie);color:#fff;border-color:var(--sie);}
.nav-logo{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:700;color:var(--sie);letter-spacing:.18em;margin-right:18px;white-space:nowrap;text-decoration:none;display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:6px;transition:background .15s;}
.nav-logo:hover{background:rgba(122,21,24,.08);}
.nav-items{display:flex;overflow-x:auto;flex:1;}
.nav-item{height:50px;padding:0 14px;display:flex;align-items:center;font-size:11px;font-weight:500;color:#4b5563;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:all .2s;text-decoration:none;}
.nav-item:hover{color:var(--ink);}
.nav-item.on{color:var(--sie);border-bottom-color:var(--sie);font-weight:600;}
.nav-tab-ddd{height:34px;align-self:center;padding:0 12px;background:#b01e1e;color:#fff;border-radius:5px;margin:0 6px;font-size:11px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;letter-spacing:.02em;}
.nav-tab-bonos{height:34px;align-self:center;padding:0 12px;background:#86EFAC;color:#166534;border-radius:5px;margin:0 6px 0 0;font-size:11px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;}

.wrap{padding:20px;max-width:1800px;margin:0 auto;}
h1{margin:0 0 6px;font-size:22px;font-weight:700;}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--mut);letter-spacing:.15em;text-transform:uppercase;font-weight:700;}
.subtitle{color:var(--mut);font-size:12px;margin-bottom:18px;}

.card{background:var(--card);border:1px solid var(--bord);border-radius:8px;padding:16px 18px;margin-bottom:16px;}
.card h2{margin:0 0 10px;font-size:13px;font-weight:700;color:var(--ink);text-transform:uppercase;letter-spacing:.1em;}

/* Market selector */
.mkt-grid{display:flex;flex-wrap:wrap;gap:6px;}
.mkt-pill{padding:6px 12px;border:1px solid var(--bord);border-radius:14px;font-size:11px;font-weight:600;cursor:pointer;background:#fff;color:var(--mut);}
.mkt-pill:hover{border-color:var(--mut);color:var(--ink);}
.mkt-pill.on{background:var(--sie);color:#fff;border-color:var(--sie);}

/* Controls */
.ctrl{display:flex;flex-wrap:wrap;gap:14px;align-items:center;padding:12px 14px;background:#fafafa;border-radius:6px;margin-bottom:12px;}
.ctrl .lbl{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em;font-weight:600;}
.ctrl .seg{display:inline-flex;border:1px solid #d4d4d4;border-radius:5px;overflow:hidden;background:#fff;}
.ctrl .seg button{padding:6px 12px;border:0;background:transparent;cursor:pointer;font-size:11px;font-weight:600;color:#525252;border-right:1px solid #e5e5e5;}
.ctrl .seg button:last-child{border-right:0;}
.ctrl .seg button.on{background:var(--sie);color:#fff;}
.ctrl .seg button:hover:not(.on){background:#f5f5f5;}
.ctrl .meta{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#1f2937;font-weight:600;margin-left:auto;padding:4px 12px;background:#fff;border:1px solid var(--bord);border-radius:5px;}

/* Competitor filter */
.flt-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;padding:12px 14px;background:#fafafa;border-radius:6px;margin-bottom:14px;}
.flt-bar .preset{display:inline-flex;border:1px solid #d4d4d4;border-radius:5px;overflow:hidden;background:#fff;}
.flt-bar .preset button{padding:5px 11px;border:0;background:transparent;cursor:pointer;font-size:11px;font-weight:600;color:#525252;border-right:1px solid #e5e5e5;}
.flt-bar .preset button:last-child{border-right:0;}
.flt-bar .preset button.on{background:#1f2937;color:#fff;}
.flt-bar .search{padding:5px 11px;border:1px solid #d4d4d4;border-radius:4px;font-size:11px;width:200px;}
.flt-bar .search:focus{outline:none;border-color:var(--sie);}
.flt-bar .meta{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--mut);margin-left:auto;align-self:center;}
.pills{display:flex;flex-wrap:wrap;gap:5px;flex:1;min-width:300px;max-height:140px;overflow-y:auto;padding:4px;border:1px solid #e5e5e5;border-radius:5px;background:#fff;}
.pill-c{padding:3px 10px;border:1px solid #d4d4d4;border-radius:12px;font-size:10px;font-weight:600;cursor:pointer;background:#fff;color:#525252;white-space:nowrap;transition:all .15s;user-select:none;}
.pill-c.on{background:#1f2937;color:#fff;border-color:#1f2937;}
.pill-c.on.sie{background:var(--sie);border-color:var(--sie);}
.pill-c:not(.on){opacity:.5;}
.pill-c:not(.on):hover{opacity:1;border-color:var(--mut);}

/* Heatmap tables */
.tbl-title{font-size:11px;font-weight:700;color:var(--ink);text-transform:uppercase;letter-spacing:.08em;margin:14px 0 6px;display:flex;align-items:center;justify-content:space-between;}
.tbl-title .meta{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--mut);font-weight:500;letter-spacing:.02em;text-transform:none;}
.hm-wrap{overflow:auto;border:1px solid var(--bord);border-radius:6px;max-height:560px;background:#fff;}
table.hm{border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:10px;width:max-content;}
table.hm th,table.hm td{border:1px solid #f0f0f0;padding:4px 6px;text-align:center;min-width:42px;}
table.hm thead th{background:#1f2937;color:#fff;font-weight:700;font-size:9px;letter-spacing:.04em;white-space:nowrap;padding:6px 8px;}
/* Two-row sticky header: first row pinned at top:0, second row pinned at top:30px */
table.hm thead tr:first-child th{position:sticky;top:0;z-index:5;box-shadow:0 1px 0 rgba(0,0,0,.1);}
table.hm thead tr:nth-child(2) th{position:sticky;top:30px;z-index:4;}
table.hm thead th:first-child{position:sticky;left:0;z-index:6;}
/* Make sure the rowspan=2 first header column sticks at top AND left */
table.hm thead tr:first-child th[rowspan="2"]{position:sticky;left:0;top:0;z-index:6;}
table.hm tbody th{position:sticky;left:0;background:#fafafa;color:var(--ink);font-weight:600;text-align:left;font-size:10px;white-space:nowrap;z-index:1;border-right:1px solid #d4d4d4;max-width:200px;overflow:hidden;text-overflow:ellipsis;padding:5px 10px;}
table.hm tbody th.sie{color:var(--sie);font-weight:700;}
table.hm tbody th.sie::before{content:'★ ';}
table.hm tbody tr:hover th,table.hm tbody tr:hover td{filter:brightness(0.95);}
/* SIE column highlight (column == competitor de Siegfried) */
table.hm thead th.sie-col{background:#7A1518 !important;color:#fff !important;border-left:2px solid #7A1518;border-right:2px solid #7A1518;font-weight:800;letter-spacing:.04em;}
table.hm td.sie-col{box-shadow:inset 2px 0 0 #7A1518, inset -2px 0 0 #7A1518;font-weight:700;}
/* Zebra rows */
table.hm tbody tr:nth-child(even) th{background:#f3f4f6;}
table.hm tbody tr:nth-child(even) td:not(.sie-col){opacity:.96;}
table.hm tbody th{padding-right:14px;font-size:11px;}
/* Sticky SIE column shadow on horizontal scroll */
table.hm thead th.sie-col,table.hm td.sie-col{position:relative;}
/* Sub-columns: visual separator between competitor groups */
table.hm td.sub-units{border-right:1px solid #d4d4d4 !important;font-size:9px;}
table.hm td.sub-metric{font-weight:700;}
table.hm thead th.sub{padding:3px 6px !important;background:#1f2937;color:#9ca3af;}
table.hm thead th.sub.sie{background:#7A1518 !important;color:#fff !important;}
/* Subtle divider between competitor pairs */
table.hm thead th[colspan="2"]{border-right:2px solid #d4d4d4;}
table.hm td.sub-units:not(:last-child){border-right:2px solid #d4d4d4 !important;}
.empty{padding:20px;text-align:center;color:var(--mut);font-size:12px;}
.note{font-size:10px;color:var(--mut);margin-top:8px;font-style:italic;}
</style>
</head>
<body>
<nav class="nav">
  <a class="nav-back" href="__HUB__" title="Volver al hub">← Hub</a>
  <a class="nav-logo" href="__HUB__">⬡ SIEGFRIED</a>
  <div class="nav-items">__NAV_ITEMS__</div>
  <span style="font-size:10px;color:var(--mut);font-family:'IBM Plex Mono',monospace;margin-left:12px;white-space:nowrap;" id="cutoff"></span>
</nav>

<div class="wrap">
  <div class="card">
    <h2>Mercado / Molécula</h2>
    <div class="mkt-grid" id="mkt-grid"></div>
  </div>

  <div class="card">
    <div class="ctrl">
      <span class="lbl">Período</span>
      <div class="seg" id="ctl-period">
        <button data-p="m">Mensual</button>
        <button data-p="q" class="on">Trimestral</button>
        <button data-p="s">Semestral</button>
        <button data-p="ytd">YTD</button>
        <button data-p="mat">MAT</button>
      </div>
      <span class="lbl">Métrica</span>
      <div class="seg" id="ctl-metric">
        <button data-m="ms" class="on">MS%</button>
        <button data-m="dms">VAR MS%</button>
        <button data-m="du">VAR UNIDADES%</button>
      </div>
      <span class="meta" id="period-label"></span>
      <button id="btn-export" style="padding:7px 14px;background:#16a34a;color:#fff;border:0;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer;letter-spacing:.04em;margin-left:8px;">📥 Exportar Excel</button>
    </div>

    <div class="flt-bar">
      <span class="lbl">Competidores</span>
      <div class="preset" id="ctl-preset">
        <button data-preset="all">Todos</button>
        <button data-preset="sie">Solo SIE</button>
        <button data-preset="top5">Top 5</button>
        <button data-preset="top10" class="on">Top 10</button>
      </div>
      <input type="text" class="search" id="ctl-search" placeholder="Buscar competidor..." />
      <div class="pills" id="comp-pills"></div>
      <span class="meta" id="comp-meta"></span>
    </div>

    <div class="tbl-title"><span>Por Provincia</span><span class="meta" id="prov-meta"></span></div>
    <div class="hm-wrap"><table class="hm" id="hm-prov"><thead></thead><tbody></tbody></table></div>

    <div class="tbl-title" style="margin-top:18px;"><span>Por Región CUP (zonas IQVIA detalladas)</span><span class="meta" id="cup-meta"></span></div>
    <div class="hm-wrap"><table class="hm" id="hm-cup"><thead></thead><tbody></tbody></table></div>

    <p class="note" id="note"></p>
  </div>
</div>

__DATA_LOADER__
<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>

<script>
/* === Competidores DDD — heatmap por provincia + region CUP ========= */
(function(){
  // Resolve data based on shape detected at runtime.
  // Shape A (cardio/SNC/dermato): window.SFG_COMP_DATA = D (markets/brand_monthly/regions/months)
  // Shape B (ATB/OTC/respi):     window.OTC_DATA.ddd  (markets/regionsByMonth/months)
  // Shape B mujer:               window.OTC_DATA.dddGineco (families/molecule.all.regionsByMonth)
  function detectShape(){
    if (window.SFG_COMP_DATA && window.SFG_COMP_DATA.markets && window.SFG_COMP_DATA.brand_monthly !== undefined) {
      // older shape: brand_monthly is on each market
      return {shape:'A', D: window.SFG_COMP_DATA};
    }
    if (window.SFG_COMP_DATA && window.SFG_COMP_DATA.markets) {
      // Check if markets have brand_monthly
      const m0 = Object.values(window.SFG_COMP_DATA.markets)[0] || {};
      if (m0.brand_monthly) return {shape:'A', D: window.SFG_COMP_DATA};
    }
    if (window.OTC_DATA && window.OTC_DATA.ddd && Object.keys(window.OTC_DATA.ddd.markets||{}).length){
      return {shape:'B', D: window.OTC_DATA.ddd, kind:'ddd'};
    }
    if (window.OTC_DATA && window.OTC_DATA.dddGineco){
      return {shape:'B', D: window.OTC_DATA.dddGineco, kind:'gineco'};
    }
    if (window.OTC_DATA && window.OTC_DATA.respDdd){
      return {shape:'B', D: window.OTC_DATA.respDdd, kind:'resp'};
    }
    return null;
  }

  const ctx = detectShape();
  if (!ctx){
    document.getElementById('mkt-grid').innerHTML = '<span class="empty">No se encontró data DDD para esta línea.</span>';
    return;
  }
  const SHAPE = ctx.shape;
  const D = ctx.D;
  const KIND = ctx.kind || '';
  const MONTHS = (D.months && Array.isArray(D.months)) ? D.months : (Array.isArray(D.months) ? D.months : []);
  const MKTS = D.markets || D.families || {};

  let HEAT_PERIOD = 'q';
  let HEAT_METRIC = 'ms';
  let HEAT_PRESET = 'top10';
  let HEAT_SEARCH = '';
  let HEAT_MARKET = null;
  const VIS_BY_MKT = {};  // market -> Set<brand> when in custom mode

  // === CUP zone → Provincia mapping ===================================
  // IQVIA RegionCUP field mixes provincias y zonas CUP (subdivisiones).
  // Esta tabla mapea cada zona CUP a su provincia real. Las que NO estan
  // listadas se asumen como nombre de provincia directo.
  const CUP_TO_PROV = {
    '_CAPITAL FEDERAL': 'CABA',
    '_SUBURBANO NORTE': 'Buenos Aires',
    '_SUBURBANO OESTE': 'Buenos Aires',
    '_SUBURBANO SUR':   'Buenos Aires',
    'AZUL-OLAVARRIA-TANDIL':                  'Buenos Aires',
    'BAHIA BLANCA':                           'Buenos Aires',
    'BARADERO-SAN PEDRO-RAMALLO-SAN NICOLAS': 'Buenos Aires',
    'JUNIN-CHIVILCOY-PERGAMINO':              'Buenos Aires',
    'LA PLATA':                               'Buenos Aires',
    'LUJAN Y ALREDEDORES':                    'Buenos Aires',
    'M.DEL PLATA':                            'Buenos Aires',
    'PILAR - ESCOBAR':                        'Buenos Aires',
    'ZARATE - CAMPANA':                       'Buenos Aires',
    'CATAMARCA':                              'Catamarca',
    'COMODORO RIVADAVIA':                     'Chubut',
    'TRELEW':                                 'Chubut',
    'RESISTENCIA':                            'Chaco',
    'CORDOBA':                                'Córdoba',
    'RIO IV Y ALREDEDORES':                   'Córdoba',
    'SAN FCO-ESTE Y NORTE':                   'Córdoba',
    'CORRIENTES':                             'Corrientes',
    'CONCORDIA':                              'Entre Ríos',
    'PARANA':                                 'Entre Ríos',
    'FORMOSA':                                'Formosa',
    'JUJUY':                                  'Jujuy',
    'SANTA ROSA':                             'La Pampa',
    'LA RIOJA':                               'La Rioja',
    'MENDOZA':                                'Mendoza',
    'SAN RAFAEL':                             'Mendoza',
    'POSADAS':                                'Misiones',
    'NEUQUEN':                                'Neuquén',
    'RIO NEGRO':                              'Río Negro',
    'SALTA':                                  'Salta',
    'SAN JUAN':                               'San Juan',
    'SAN LUIS':                               'San Luis',
    'SANTA CRUZ':                             'Santa Cruz',
    'RAFAELA-NTE SANTA FE':                   'Santa Fe',
    'ROSARIO':                                'Santa Fe',
    'SANTA FE':                               'Santa Fe',
    'SANTIAGO DEL ESTERO':                    'Santiago del Estero',
    'TIERRA DEL FUEGO':                       'Tierra del Fuego',
    'TUCUMAN':                                'Tucumán',
  };
  function regionToProvince(r){
    if (!r) return null;
    return CUP_TO_PROV[r] || r;
  }

  // === Period helpers ===
  function periodIdxs(){
    const N = MONTHS.length; if (!N) return null;
    const last = N - 1;
    const lastM = MONTHS[last];
    const mkLabel = (a,b) => MONTHS[a] + (b>a ? '..'+MONTHS[b] : '');
    if (HEAT_PERIOD==='m'){
      const prev = last>=1 ? [last-1] : null;
      return {curr:[last], prev, label: lastM, prevLabel: prev ? MONTHS[prev[0]] : null};
    }
    if (HEAT_PERIOD==='q'){
      const curr = [last-2, last-1, last].filter(i=>i>=0);
      const prev = last-5>=0 ? [last-5, last-4, last-3] : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[2]) : null};
    }
    if (HEAT_PERIOD==='s'){
      const curr = Array.from({length:6}, (_,k)=>last-5+k).filter(i=>i>=0);
      const prev = last-11>=0 ? Array.from({length:6}, (_,k)=>last-11+k) : null;
      return {curr, prev, label: mkLabel(curr[0], curr[curr.length-1]), prevLabel: prev ? mkLabel(prev[0], prev[5]) : null};
    }
    if (HEAT_PERIOD==='ytd'){
      const yr = lastM.split('-').pop();
      const curr = MONTHS.map((m,i)=>m.endsWith('-'+yr) ? i : -1).filter(i=>i>=0 && i<=last);
      const prevYr = String(parseInt(yr,10)-1);
      const prevAll = MONTHS.map((m,i)=>m.endsWith('-'+prevYr) ? i : -1).filter(i=>i>=0);
      const prev = prevAll.length >= curr.length ? prevAll.slice(0, curr.length) : null;
      return {curr, prev, label:'YTD '+yr, prevLabel: prev ? 'YTD '+prevYr : null};
    }
    if (HEAT_PERIOD==='mat'){
      const curr = Array.from({length:12}, (_,k)=>last-11+k).filter(i=>i>=0);
      const prev = last-23>=0 ? Array.from({length:12}, (_,k)=>last-23+k) : null;
      return {curr, prev, label: 'MAT '+lastM, prevLabel: prev ? 'MAT '+MONTHS[last-12] : null};
    }
    return null;
  }
  function sumMonths(arr, idxs){
    if (!arr || !idxs) return 0;
    let s=0; for (const i of idxs){ if (i>=0 && i<arr.length){ const v=arr[i]; if (typeof v==='number') s+=v; } } return s;
  }

  // === Shape-A helpers: rank competitors + grid ===
  function rankedBrandsA(market, regions, period){
    const mk = MKTS[market]; if (!mk) return [];
    const bm = mk.brand_monthly || {};
    const brands = Object.keys(bm);
    const sieList = (mk.brands || []).map(s=>String(s).toUpperCase());
    const bt = {};
    for (const b of brands){
      let t=0;
      for (const r of regions){ const arr=(bm[b]||{})[r]; if (arr) t += sumMonths(arr, period.curr); }
      bt[b] = t;
    }
    return brands.filter(b=>bt[b]>0).sort((a,b)=>bt[b]-bt[a])
                 .map(b=>({brand:b, units:bt[b], isSie: sieList.includes(String(b).toUpperCase())}));
  }
  function computeGridA(market, regions, period, visibleSet){
    const mk = MKTS[market]; if (!mk) return null;
    const bm = mk.brand_monthly || {};
    const tm = mk.total_monthly || {};
    const sieList = (mk.brands || []).map(s=>String(s).toUpperCase());
    const allBrands = Object.keys(bm);
    // Per-brand total in period (national across regions)
    const bt = {};
    for (const b of allBrands){
      let t=0;
      for (const r of regions){ const arr=(bm[b]||{})[r]; if (arr) t += sumMonths(arr, period.curr); }
      bt[b]=t;
    }
    const rows = allBrands.filter(b=>bt[b]>0 && (!visibleSet || visibleSet.has(b)))
                          .sort((a,b)=>bt[b]-bt[a])
                          .map(b=>({brand:b, isSie: sieList.includes(String(b).toUpperCase())}));
    // Total market per region in period
    const regTotal = {};
    for (const r of regions){
      let t = sumMonths(tm[r], period.curr);
      if (!t){ for (const b of allBrands) t += sumMonths((bm[b]||{})[r], period.curr); }
      regTotal[r] = t;
    }
    const cols = regions.filter(r=>regTotal[r]>0).sort((a,b)=>regTotal[b]-regTotal[a]);
    const cells = {};
    let max_ms=0, max_abs_dms=0, max_abs_du=0;
    for (const row of rows){
      const b = row.brand;
      cells[b] = {};
      for (const r of cols){
        const arr = (bm[b]||{})[r] || null;
        const tot = tm[r] || null;
        const u_a = sumMonths(arr, period.curr);
        let mkt_a = sumMonths(tot, period.curr);
        if (!mkt_a){ for (const bb of allBrands) mkt_a += sumMonths((bm[bb]||{})[r], period.curr); }
        const ms_a = mkt_a>0 ? u_a/mkt_a*100 : null;
        let u_p=null, mkt_p=null, ms_p=null, dms=null, du=null;
        if (period.prev){
          u_p = sumMonths(arr, period.prev);
          mkt_p = sumMonths(tot, period.prev);
          if (!mkt_p){ for (const bb of allBrands) mkt_p += sumMonths((bm[bb]||{})[r], period.prev); }
          ms_p = mkt_p>0 ? u_p/mkt_p*100 : null;
          if (ms_a!==null && ms_p!==null) dms = ms_a-ms_p;
          if (u_p>0) du = (u_a-u_p)/u_p*100;
        }
        cells[b][r] = {u_act:u_a, u_prev:u_p, mkt_act:mkt_a, mkt_prev:mkt_p, ms_act:ms_a, ms_prev:ms_p, dms, du};
        if (ms_a!==null && ms_a>max_ms) max_ms = ms_a;
        if (dms!==null && Math.abs(dms)>max_abs_dms) max_abs_dms = Math.abs(dms);
        if (du!==null && Math.abs(du)>max_abs_du) max_abs_du = Math.abs(du);
      }
    }
    return {rows, cols, cells, max_ms, max_abs_dms, max_abs_du};
  }

  // === Shape-B helpers ===
  function aggregateB(market, idxs){
    const mk = MKTS[market]; if (!mk) return {};
    const rbm = mk.regionsByMonth || (mk.molecule && mk.molecule.all && mk.molecule.all.regionsByMonth) || {};
    const agg = {};
    for (const i of idxs){
      const mn = MONTHS[i]; if (!mn) continue;
      const list = rbm[mn] || [];
      for (const r of list){
        if (!agg[r.name]) agg[r.name] = {sie:0,total:0};
        agg[r.name].sie += Number(r.sie||0);
        agg[r.name].total += Number(r.total||0);
      }
    }
    for (const k of Object.keys(agg)){
      const a = agg[k]; a.ms = a.total>0 ? a.sie/a.total*100 : null;
    }
    return agg;
  }

  // === Visible set logic (shared) ===
  function getVisibleSet(market, allRanked){
    if (!VIS_BY_MKT[market]) VIS_BY_MKT[market] = new Set();
    const cache = VIS_BY_MKT[market];
    if (HEAT_PRESET==='all') return new Set(allRanked.map(r=>r.brand));
    if (HEAT_PRESET==='sie') return new Set(allRanked.filter(r=>r.isSie).map(r=>r.brand));
    if (HEAT_PRESET==='top5') return new Set(allRanked.slice(0,5).map(r=>r.brand));
    if (HEAT_PRESET==='top10') return new Set(allRanked.slice(0,10).map(r=>r.brand));
    // custom
    if (cache.size===0) allRanked.slice(0,10).forEach(r=>cache.add(r.brand));
    return cache;
  }

  // === Color helpers ===
  function colorMS(v, max){
    if (v==null || max<=0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.min(v/max, 1);
    const r = Math.round(243+(30-243)*t);
    const g = Math.round(244+(64-244)*t);
    const b = Math.round(246+(175-246)*t);
    return {bg:`rgb(${r},${g},${b})`, fg: t>0.55?'#fff':'#1f2937'};
  }
  function colorDiv(v, max){
    if (v==null || max<=0) return {bg:'#fff', fg:'#9ca3af'};
    const t = Math.max(-1, Math.min(1, v/max));
    if (t>=0){
      const r = Math.round(255+(22-255)*t);
      const g = Math.round(255+(163-255)*t);
      const b = Math.round(255+(74-255)*t);
      return {bg:`rgb(${r},${g},${b})`, fg: t>0.55?'#fff':'#0f5132'};
    } else {
      const tt = -t;
      const r = Math.round(255+(220-255)*tt);
      const g = Math.round(255+(38-255)*tt);
      const b = Math.round(255+(38-255)*tt);
      return {bg:`rgb(${r},${g},${b})`, fg: tt>0.55?'#fff':'#7f1d1d'};
    }
  }
  function fmtCellMetric(cell, max){
    if (HEAT_METRIC==='ms'){
      if (cell.ms_act==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const c = colorMS(cell.ms_act, max.ms);
      return {txt: cell.ms_act.toFixed(1)+'%', bg:c.bg, fg:c.fg};
    }
    if (HEAT_METRIC==='dms'){
      if (cell.dms==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const c = colorDiv(cell.dms, max.dms);
      return {txt:(cell.dms>=0?'+':'')+cell.dms.toFixed(1), bg:c.bg, fg:c.fg};
    }
    if (HEAT_METRIC==='du'){
      if (cell.du==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
      const c = colorDiv(cell.du, max.du);
      return {txt:(cell.du>=0?'+':'')+cell.du.toFixed(0)+'%', bg:c.bg, fg:c.fg};
    }
    return {txt:'—', bg:'#fff', fg:'#9ca3af'};
  }

  // === Render Shape A table (TRANSPOSED: regions=rows, competitors=cols) ===
  function renderTableA(tableId, regions, market, period, visibleSet){
    const tbl = document.getElementById(tableId);
    const thead = tbl.querySelector('thead'); const tbody = tbl.querySelector('tbody');
    if (!regions.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class="empty">Sin regiones.</td></tr>'; return; }
    const grid = computeGridA(market, regions, period, visibleSet);
    if (!grid || !grid.rows.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class="empty">Sin datos visibles. Activá competidores en el filtro.</td></tr>'; return; }
    const max = {ms: Math.max(grid.max_ms,1), dms: Math.max(grid.max_abs_dms, 0.1), du: Math.max(grid.max_abs_du, 1)};
    const cleanReg = r => r.startsWith('_') ? r.slice(1) : r;
    // Header con DOS filas: competidor (colspan=2) y abajo sub-headers metric | Unidades
    // Las sub-headers incluyen el periodo activo y, si es Δ, el comparador
    const pLab = period.label || '';
    const ppLab = period.prevLabel || '';
    let metricLabel;
    if (HEAT_METRIC==='ms')       metricLabel = `MS% · ${pLab}`;
    else if (HEAT_METRIC==='dms') metricLabel = ppLab ? `VAR MS% · ${pLab} vs ${ppLab}` : `VAR MS% · sin comparador`;
    else                          metricLabel = ppLab ? `VAR UNIDADES% · ${pLab} vs ${ppLab}` : `VAR UNIDADES% · sin comparador`;
    const unitsLabel = `Unidades · ${pLab}`;
    let h = '<tr><th rowspan="2">Región / Provincia</th>';
    for (const row of grid.rows){
      const cls = row.isSie ? 'sie sie-col' : '';
      h += `<th class="${cls}" colspan="2" title="${row.brand}" style="border-bottom:1px solid rgba(255,255,255,.15)">${row.isSie?'★ ':''}${row.brand}</th>`;
    }
    h += '</tr><tr>';
    for (const row of grid.rows){
      const cls = row.isSie ? 'sie sie-col sub' : 'sub';
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${metricLabel}">${metricLabel}</th>`;
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${unitsLabel}">${unitsLabel}</th>`;
    }
    h += '</tr>';
    thead.innerHTML = h;
    // Body: una fila por región, dos celdas por competidor (MS% colored + Units plain)
    function fmtUnits(u){
      if (u==null) return '—';
      if (u >= 1e6) return (u/1e6).toFixed(1)+'M';
      if (u >= 1e3) return (u/1e3).toFixed(1)+'k';
      return u.toLocaleString('es-AR');
    }
    let b = '';
    for (const r of grid.cols){
      b += `<tr><th title="${r}">${cleanReg(r)}</th>`;
      for (const row of grid.rows){
        const cell = grid.cells[row.brand][r];
        const f = fmtCellMetric(cell, max);
        const tt = [`${row.brand} · ${r}`];
        tt.push(`Período: ${period.label}`);
        if (cell.ms_act!=null) tt.push(`MS%: ${cell.ms_act.toFixed(2)}%`);
        if (cell.dms!=null) tt.push(`Δ MS%: ${(cell.dms>=0?'+':'')+cell.dms.toFixed(2)} pp (vs ${period.prevLabel||'—'})`);
        if (cell.du!=null) tt.push(`Δ U: ${(cell.du>=0?'+':'')+cell.du.toFixed(1)}% (vs ${period.prevLabel||'—'})`);
        tt.push(`Unidades: ${cell.u_act.toLocaleString('es-AR')}`);
        if (cell.mkt_act > 0){
          const perPct = cell.mkt_act / 100;
          tt.push(`1% MS% = ${Math.round(perPct).toLocaleString('es-AR')} u. (mercado total: ${cell.mkt_act.toLocaleString('es-AR')})`);
        }
        const tdCls = row.isSie ? 'sie-col' : '';
        const ttStr = tt.join('\\n');
        // Sub-col 1: metric (con heat color)
        b += `<td class="${tdCls} sub-metric" style="background:${f.bg};color:${f.fg}" title="${ttStr}">${f.txt}</td>`;
        // Sub-col 2: unidades (neutro)
        const uStr = fmtUnits(cell.u_act);
        b += `<td class="${tdCls} sub-units" style="color:#525252;background:#fafafa;font-weight:500;" title="${ttStr}">${uStr}</td>`;
      }
      b += '</tr>';
    }
    tbody.innerHTML = b;
  }

  // === Render Shape B table (TRANSPOSED: regiones=filas, series=cols) ===
  function renderTableB(tableId, regionFilter, market, period){
    const tbl = document.getElementById(tableId);
    const thead = tbl.querySelector('thead'); const tbody = tbl.querySelector('tbody');
    const aggC = aggregateB(market, period.curr);
    const aggP = period.prev ? aggregateB(market, period.prev) : null;
    const regs = Object.keys(aggC).filter(regionFilter).filter(r=>aggC[r].total>0)
                       .sort((a,b)=>aggC[b].total-aggC[a].total);
    if (!regs.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class="empty">Sin datos para esta vista.</td></tr>'; return; }
    let max_ms=0, max_abs_dms=0, max_abs_du=0;
    for (const r of regs){
      const a = aggC[r];
      if (a.ms!=null && a.ms>max_ms) max_ms = a.ms;
      if (aggP && aggP[r]){
        const p = aggP[r];
        if (p.ms!=null && a.ms!=null) max_abs_dms = Math.max(max_abs_dms, Math.abs(a.ms-p.ms));
        if (p.sie>0) max_abs_du = Math.max(max_abs_du, Math.abs((a.sie-p.sie)/p.sie*100));
        if (p.total>0) max_abs_du = Math.max(max_abs_du, Math.abs((a.total-p.total)/p.total*100));
      }
    }
    const max = {ms: Math.max(max_ms,1), dms: Math.max(max_abs_dms, 0.1), du: Math.max(max_abs_du, 1)};
    const cleanReg = r => r.startsWith('_') ? r.slice(1) : r;
    function cell(serie, region){
      const a = aggC[region]; const p = aggP ? aggP[region] : null;
      const v_a = serie==='SIE' ? a.sie : a.total;
      const v_p = p ? (serie==='SIE' ? p.sie : p.total) : null;
      const ms_a = serie==='SIE' ? a.ms : 100;
      const ms_p = (p && serie==='SIE') ? p.ms : null;
      let dms=null, du=null;
      if (ms_a!=null && ms_p!=null) dms = ms_a-ms_p;
      if (v_p && v_p>0) du = (v_a-v_p)/v_p*100;
      if (HEAT_METRIC==='ms'){
        if (serie==='Mercado total') return {txt: v_a.toLocaleString('es-AR'), bg:'#fafafa', fg:'#525252'};
        if (ms_a==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorMS(ms_a, max.ms);
        return {txt: ms_a.toFixed(1)+'%', bg:c.bg, fg:c.fg};
      }
      if (HEAT_METRIC==='dms'){
        if (serie==='Mercado total') return {txt:'—', bg:'#fafafa', fg:'#9ca3af'};
        if (dms==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(dms, max.dms);
        return {txt:(dms>=0?'+':'')+dms.toFixed(1), bg:c.bg, fg:c.fg};
      }
      if (HEAT_METRIC==='du'){
        if (du==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(du, max.du);
        return {txt:(du>=0?'+':'')+du.toFixed(0)+'%', bg:c.bg, fg:c.fg};
      }
      return {txt:'—', bg:'#fff', fg:'#9ca3af'};
    }
    // Header con DOS filas: serie (colspan=2) y abajo metric | Unidades
    const series = ['SIE','Mercado total'];
    const pLab = period.label || '';
    const ppLab = period.prevLabel || '';
    let metricLabel;
    if (HEAT_METRIC==='ms')       metricLabel = `MS% · ${pLab}`;
    else if (HEAT_METRIC==='dms') metricLabel = ppLab ? `VAR MS% · ${pLab} vs ${ppLab}` : `VAR MS% · sin comparador`;
    else                          metricLabel = ppLab ? `VAR UNIDADES% · ${pLab} vs ${ppLab}` : `VAR UNIDADES% · sin comparador`;
    const unitsLabel = `Unidades · ${pLab}`;
    let h = '<tr><th rowspan="2">Región / Provincia</th>';
    for (const s of series){
      const cls = s==='SIE' ? 'sie sie-col' : '';
      h += `<th class="${cls}" colspan="2" style="border-bottom:1px solid rgba(255,255,255,.15)">${s==='SIE'?'★ ':''}${s}</th>`;
    }
    h += '</tr><tr>';
    for (const s of series){
      const cls = s==='SIE' ? 'sie sie-col sub' : 'sub';
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${metricLabel}">${metricLabel}</th>`;
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${unitsLabel}">${unitsLabel}</th>`;
    }
    h += '</tr>';
    thead.innerHTML = h;
    function fmtUnits(u){
      if (u==null) return '—';
      if (u >= 1e6) return (u/1e6).toFixed(1)+'M';
      if (u >= 1e3) return (u/1e3).toFixed(1)+'k';
      return u.toLocaleString('es-AR');
    }
    let b = '';
    for (const r of regs){
      b += `<tr><th title="${r}">${cleanReg(r)}</th>`;
      for (const s of series){
        const f = cell(s, r);
        const tdCls = s==='SIE' ? 'sie-col' : '';
        const a = aggC[r];
        const units = s==='SIE' ? a.sie : a.total;
        const tt = [`${s} · ${r}`, `Período: ${period.label}`,
                    `Unidades: ${units.toLocaleString('es-AR')}`];
        if (a.total > 0){
          const perPct = a.total / 100;
          tt.push(`1% MS% = ${Math.round(perPct).toLocaleString('es-AR')} u. (mercado total: ${a.total.toLocaleString('es-AR')})`);
        }
        const ttStr = tt.join('\\n');
        b += `<td class="${tdCls} sub-metric" style="background:${f.bg};color:${f.fg}" title="${ttStr}">${f.txt}</td>`;
        b += `<td class="${tdCls} sub-units" style="color:#525252;background:#fafafa;font-weight:500;" title="${ttStr}">${fmtUnits(units)}</td>`;
      }
      b += '</tr>';
    }
    tbody.innerHTML = b;
  }

  // === Shape B: aggregate regions by province ===
  function aggregateBByProvince(market, idxs){
    const raw = aggregateB(market, idxs);
    const out = {};
    for (const region of Object.keys(raw)){
      const prov = regionToProvince(region);
      if (!prov) continue;
      if (!out[prov]) out[prov] = {sie:0,total:0};
      out[prov].sie   += raw[region].sie;
      out[prov].total += raw[region].total;
    }
    for (const k of Object.keys(out)){
      const a = out[k]; a.ms = a.total>0 ? a.sie/a.total*100 : null;
    }
    return out;
  }

  function renderTableBProv(tableId, market, period){
    const tbl = document.getElementById(tableId);
    const thead = tbl.querySelector('thead'); const tbody = tbl.querySelector('tbody');
    const aggC = aggregateBByProvince(market, period.curr);
    const aggP = period.prev ? aggregateBByProvince(market, period.prev) : null;
    const provs = Object.keys(aggC).filter(p=>aggC[p].total>0).sort((a,b)=>aggC[b].total-aggC[a].total);
    if (!provs.length){ thead.innerHTML=''; tbody.innerHTML='<tr><td class="empty">Sin datos para esta vista.</td></tr>'; return; }
    let max_ms=0, max_abs_dms=0, max_abs_du=0;
    for (const p of provs){
      const a = aggC[p];
      if (a.ms!=null && a.ms>max_ms) max_ms = a.ms;
      if (aggP && aggP[p]){
        const pp = aggP[p];
        if (pp.ms!=null && a.ms!=null) max_abs_dms = Math.max(max_abs_dms, Math.abs(a.ms-pp.ms));
        if (pp.sie>0) max_abs_du = Math.max(max_abs_du, Math.abs((a.sie-pp.sie)/pp.sie*100));
        if (pp.total>0) max_abs_du = Math.max(max_abs_du, Math.abs((a.total-pp.total)/pp.total*100));
      }
    }
    const max = {ms: Math.max(max_ms,1), dms: Math.max(max_abs_dms, 0.1), du: Math.max(max_abs_du, 1)};
    function cell(serie, prov){
      const a = aggC[prov]; const p = aggP ? aggP[prov] : null;
      const v_a = serie==='SIE' ? a.sie : a.total;
      const v_p = p ? (serie==='SIE' ? p.sie : p.total) : null;
      const ms_a = serie==='SIE' ? a.ms : 100;
      const ms_p = (p && serie==='SIE') ? p.ms : null;
      let dms=null, du=null;
      if (ms_a!=null && ms_p!=null) dms = ms_a-ms_p;
      if (v_p && v_p>0) du = (v_a-v_p)/v_p*100;
      if (HEAT_METRIC==='ms'){
        if (serie==='Mercado total') return {txt: v_a.toLocaleString('es-AR'), bg:'#fafafa', fg:'#525252'};
        if (ms_a==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorMS(ms_a, max.ms);
        return {txt: ms_a.toFixed(1)+'%', bg:c.bg, fg:c.fg};
      }
      if (HEAT_METRIC==='dms'){
        if (serie==='Mercado total') return {txt:'—', bg:'#fafafa', fg:'#9ca3af'};
        if (dms==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(dms, max.dms);
        return {txt:(dms>=0?'+':'')+dms.toFixed(1), bg:c.bg, fg:c.fg};
      }
      if (HEAT_METRIC==='du'){
        if (du==null) return {txt:'—', bg:'#fff', fg:'#9ca3af'};
        const c = colorDiv(du, max.du);
        return {txt:(du>=0?'+':'')+du.toFixed(0)+'%', bg:c.bg, fg:c.fg};
      }
      return {txt:'—', bg:'#fff', fg:'#9ca3af'};
    }
    // TRANSPOSED + sub-cols: Provincia | SIE (metric | Unidades) | Mercado total (metric | Unidades)
    const series = ['SIE','Mercado total'];
    const pLab = period.label || '';
    const ppLab = period.prevLabel || '';
    let metricLabel;
    if (HEAT_METRIC==='ms')       metricLabel = `MS% · ${pLab}`;
    else if (HEAT_METRIC==='dms') metricLabel = ppLab ? `VAR MS% · ${pLab} vs ${ppLab}` : `VAR MS% · sin comparador`;
    else                          metricLabel = ppLab ? `VAR UNIDADES% · ${pLab} vs ${ppLab}` : `VAR UNIDADES% · sin comparador`;
    const unitsLabel = `Unidades · ${pLab}`;
    let h = '<tr><th rowspan="2">Provincia</th>';
    for (const s of series){
      const cls = s==='SIE' ? 'sie sie-col' : '';
      h += `<th class="${cls}" colspan="2" style="border-bottom:1px solid rgba(255,255,255,.15)">${s==='SIE'?'★ ':''}${s}</th>`;
    }
    h += '</tr><tr>';
    for (const s of series){
      const cls = s==='SIE' ? 'sie sie-col sub' : 'sub';
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${metricLabel}">${metricLabel}</th>`;
      h += `<th class="${cls}" style="font-size:8px;font-weight:600;opacity:.9;letter-spacing:.02em;white-space:nowrap;" title="${unitsLabel}">${unitsLabel}</th>`;
    }
    h += '</tr>';
    thead.innerHTML = h;
    function fmtUnits(u){
      if (u==null) return '—';
      if (u >= 1e6) return (u/1e6).toFixed(1)+'M';
      if (u >= 1e3) return (u/1e3).toFixed(1)+'k';
      return u.toLocaleString('es-AR');
    }
    let b = '';
    for (const p of provs){
      b += `<tr><th title="${p}">${p}</th>`;
      for (const s of series){
        const f = cell(s, p);
        const tdCls = s==='SIE' ? 'sie-col' : '';
        const a = aggC[p];
        const units = s==='SIE' ? a.sie : a.total;
        const tt = [`${s} · ${p}`, `Período: ${period.label}`,
                    `Unidades: ${units.toLocaleString('es-AR')}`];
        if (a.total > 0){
          const perPct = a.total / 100;
          tt.push(`1% MS% = ${Math.round(perPct).toLocaleString('es-AR')} u. (mercado total: ${a.total.toLocaleString('es-AR')})`);
        }
        const ttStr = tt.join('\\n');
        b += `<td class="${tdCls} sub-metric" style="background:${f.bg};color:${f.fg}" title="${ttStr}">${f.txt}</td>`;
        b += `<td class="${tdCls} sub-units" style="color:#525252;background:#fafafa;font-weight:500;" title="${ttStr}">${fmtUnits(units)}</td>`;
      }
      b += '</tr>';
    }
    tbody.innerHTML = b;
  }

  // === Comp pills (Shape A only) ===
  function renderPills(market, allRanked, visibleSet){
    const el = document.getElementById('comp-pills');
    const search = (HEAT_SEARCH||'').toUpperCase();
    const filtered = search ? allRanked.filter(r=>r.brand.toUpperCase().includes(search)) : allRanked;
    el.innerHTML = filtered.map(r=>{
      const on = visibleSet.has(r.brand);
      const cls = 'pill-c' + (on?' on':'') + (r.isSie?' sie':'');
      return `<button class="${cls}" data-b="${r.brand.replace(/"/g,'&quot;')}" title="${r.brand} · ${r.units.toLocaleString('es-AR')} u.">${r.isSie?'★ ':''}${r.brand}</button>`;
    }).join('');
    document.getElementById('comp-meta').textContent = `${visibleSet.size}/${allRanked.length} visibles` + (search?` · "${HEAT_SEARCH}"`:'');
  }

  // === Aggregate brand_monthly per province (Shape A) ===
  // Returns a "virtual" market view where regions are provinces (aggregated
  // sum of constituent CUP zones).
  function buildProvinceView(market){
    if (SHAPE !== 'A') return null;
    const mk = MKTS[market]; if (!mk) return null;
    const bm = mk.brand_monthly || {};
    const tm = mk.total_monthly || {};
    const NMonths = MONTHS.length;
    const provBM = {}; // brand → province → [N months]
    const provTM = {}; // province → [N months]
    const addToArr = (target, src) => {
      if (!src) return target;
      for (let i = 0; i < NMonths; i++){
        target[i] = (target[i]||0) + (Number(src[i])||0);
      }
      return target;
    };
    for (const brand of Object.keys(bm)){
      provBM[brand] = {};
      for (const region of Object.keys(bm[brand])){
        const prov = regionToProvince(region);
        if (!prov) continue;
        if (!provBM[brand][prov]) provBM[brand][prov] = new Array(NMonths).fill(0);
        addToArr(provBM[brand][prov], bm[brand][region]);
      }
    }
    for (const region of Object.keys(tm)){
      const prov = regionToProvince(region);
      if (!prov) continue;
      if (!provTM[prov]) provTM[prov] = new Array(NMonths).fill(0);
      addToArr(provTM[prov], tm[region]);
    }
    return { brands: mk.brands || [], brand_monthly: provBM, total_monthly: provTM };
  }

  // For Shape A province table we need a way to feed `computeGridA` with the
  // province-aggregated view. We achieve this by temporarily injecting a
  // synthetic market into MKTS and pointing computeGridA at it.
  const PROV_MKT_KEY = '__PROV_AGG__';
  function withProvinceView(market, fn){
    const view = buildProvinceView(market);
    if (!view) return fn();
    const savedOrig = MKTS[PROV_MKT_KEY];
    MKTS[PROV_MKT_KEY] = view;
    try { return fn(); } finally {
      if (savedOrig === undefined) delete MKTS[PROV_MKT_KEY]; else MKTS[PROV_MKT_KEY] = savedOrig;
    }
  }

  // === Render entry point ===
  function getRawRegions(){
    if (SHAPE==='A'){
      return (D.regions||[]).filter(r=>r && r!=='-');
    }
    const mk = MKTS[HEAT_MARKET]; if (!mk) return [];
    const rbm = mk.regionsByMonth || (mk.molecule && mk.molecule.all && mk.molecule.all.regionsByMonth) || {};
    const set = new Set();
    for (const list of Object.values(rbm)){ for (const r of (list||[])){ set.add(r.name); } }
    return Array.from(set);
  }

  function render(){
    if (!HEAT_MARKET) HEAT_MARKET = Object.keys(MKTS)[0];
    if (!HEAT_MARKET){ document.getElementById('mkt-grid').innerHTML='<span class="empty">Sin mercados.</span>'; return; }
    const period = periodIdxs(); if (!period) return;
    const allRegs = getRawRegions();
    const cupRegs = allRegs;  // CUP table shows ALL raw zones (provinces + BAIRES + sub-zones)

    if (SHAPE==='A'){
      // Pills + ranking use the raw (full) data for accuracy
      const allRanked = rankedBrandsA(HEAT_MARKET, allRegs, period);
      const visibleSet = getVisibleSet(HEAT_MARKET, allRanked);
      renderPills(HEAT_MARKET, allRanked, visibleSet);
      // Province table: aggregated view
      withProvinceView(HEAT_MARKET, () => {
        const provView = MKTS[PROV_MKT_KEY];
        const provNames = Object.keys(provView.total_monthly);
        renderTableA('hm-prov', provNames, PROV_MKT_KEY, period, visibleSet);
      });
      // CUP/Region table: raw zones
      renderTableA('hm-cup', cupRegs, HEAT_MARKET, period, visibleSet);
    } else {
      document.getElementById('comp-pills').innerHTML = '<span class="empty">Data DDD de esta línea no expone competidores individuales — mostrando SIE vs Mercado Total.</span>';
      document.getElementById('comp-meta').textContent = '';
      // For Shape B we still aggregate to province via the regionsByMonth filter.
      const provFilter = r => {
        const p = regionToProvince(r);
        return p && p !== '-';
      };
      renderTableBProv('hm-prov', HEAT_MARKET, period);
      renderTableB('hm-cup',  r=>r,                  HEAT_MARKET, period);
    }

    document.getElementById('period-label').textContent =
      `${HEAT_MARKET} · ${period.label}` + (HEAT_METRIC==='ms' ? '' : (period.prevLabel ? ` (vs ${period.prevLabel})` : ' · sin comparador'));

    const noteEl = document.getElementById('note');
    if (SHAPE==='A'){
      noteEl.textContent = (HEAT_METRIC!=='ms' && !period.prev)
        ? 'Sin período comparador disponible: la serie no es lo suficientemente larga para esta agregación.'
        : 'Filas = competidores ordenados por unidades; columnas = regiones ordenadas por volumen del mercado. Hover para detalle.';
    } else {
      noteEl.textContent = 'La data DDD de esta línea agrega SIE vs Mercado Total por región/mes. No expone competidores individuales — el granular requiere rebuild de data.js desde el xlsx fuente.';
    }
    if (SHAPE==='A'){
      const provCount = (function(){ const view = buildProvinceView(HEAT_MARKET); return view ? Object.keys(view.total_monthly).length : 0; })();
      document.getElementById('prov-meta').textContent = `${provCount} provincias`;
    } else {
      const aggC = aggregateBByProvince(HEAT_MARKET, period.curr);
      document.getElementById('prov-meta').textContent = `${Object.keys(aggC).filter(p=>aggC[p].total>0).length} provincias`;
    }
    document.getElementById('cup-meta').textContent = `${cupRegs.length} zonas CUP`;
  }

  function renderMktGrid(){
    const el = document.getElementById('mkt-grid');
    const keys = Object.keys(MKTS);
    if (!HEAT_MARKET && keys.length) HEAT_MARKET = keys[0];
    el.innerHTML = keys.map(k=>`<button class="mkt-pill ${k===HEAT_MARKET?'on':''}" data-mkt="${k.replace(/"/g,'&quot;')}">${k}</button>`).join('');
  }

  // === Wire up controls (event delegation for pills) ===
  document.addEventListener('click', (e)=>{
    const t = e.target;
    if (t.matches && t.matches('.mkt-pill')){
      HEAT_MARKET = t.dataset.mkt;
      document.querySelectorAll('.mkt-pill').forEach(b=>b.classList.toggle('on', b===t));
      render();
    } else if (t.closest && t.closest('#ctl-period')){
      const btn = t.closest('button'); if (!btn || !btn.dataset.p) return;
      HEAT_PERIOD = btn.dataset.p;
      document.querySelectorAll('#ctl-period button').forEach(b=>b.classList.toggle('on', b===btn));
      render();
    } else if (t.closest && t.closest('#ctl-metric')){
      const btn = t.closest('button'); if (!btn || !btn.dataset.m) return;
      HEAT_METRIC = btn.dataset.m;
      document.querySelectorAll('#ctl-metric button').forEach(b=>b.classList.toggle('on', b===btn));
      render();
    } else if (t.closest && t.closest('#ctl-preset')){
      const btn = t.closest('button'); if (!btn || !btn.dataset.preset) return;
      HEAT_PRESET = btn.dataset.preset;
      document.querySelectorAll('#ctl-preset button').forEach(b=>b.classList.toggle('on', b===btn));
      if (HEAT_MARKET) VIS_BY_MKT[HEAT_MARKET] = new Set();
      render();
    } else if (t.matches && t.matches('.pill-c')){
      const b = t.dataset.b;
      // Switch to custom
      if (HEAT_PRESET !== 'custom'){
        HEAT_PRESET = 'custom';
        document.querySelectorAll('#ctl-preset button').forEach(x=>x.classList.remove('on'));
        // seed VIS_BY_MKT from current visibility (parse from DOM state)
        const visible = new Set();
        document.querySelectorAll('.pill-c.on').forEach(p => visible.add(p.dataset.b));
        VIS_BY_MKT[HEAT_MARKET] = visible;
      }
      const set = VIS_BY_MKT[HEAT_MARKET];
      if (set.has(b)) set.delete(b); else set.add(b);
      render();
    }
  });

  document.getElementById('ctl-search').addEventListener('input', (e)=>{
    HEAT_SEARCH = e.target.value || '';
    if (!HEAT_MARKET) return;
    const period = periodIdxs();
    if (SHAPE==='A' && period){
      const allRegs = getRegions();
      const allRanked = rankedBrandsA(HEAT_MARKET, allRegs, period);
      const visibleSet = getVisibleSet(HEAT_MARKET, allRanked);
      renderPills(HEAT_MARKET, allRanked, visibleSet);
    }
  });

  // === Export to Excel =================================================
  function tableToAoA(tableId){
    const tbl = document.getElementById(tableId);
    if (!tbl) return [];
    const rows = [];
    tbl.querySelectorAll('thead tr').forEach(tr => {
      const r = [];
      tr.querySelectorAll('th').forEach(th => {
        const cs = parseInt(th.getAttribute('colspan')||'1', 10);
        const txt = (th.textContent || '').trim();
        r.push(txt);
        for (let i=1;i<cs;i++) r.push('');
      });
      rows.push(r);
    });
    tbl.querySelectorAll('tbody tr').forEach(tr => {
      const r = [];
      tr.querySelectorAll('th, td').forEach(c => r.push((c.textContent||'').trim()));
      rows.push(r);
    });
    return rows;
  }

  function exportExcel(){
    if (typeof XLSX === 'undefined'){
      alert('Librería XLSX no cargó — revisá tu conexión.'); return;
    }
    const market = HEAT_MARKET || 'mercado';
    const periodLabel = (document.getElementById('period-label').textContent || '').replace(/[\\/?*\\[\\]:]/g, '-').slice(0, 60);
    const metricNice = HEAT_METRIC==='ms' ? 'MS%' : (HEAT_METRIC==='dms' ? 'VAR_MS%' : 'VAR_UNIDADES%');
    const wb = XLSX.utils.book_new();
    const provAoA = tableToAoA('hm-prov');
    const cupAoA  = tableToAoA('hm-cup');
    if (provAoA.length){
      const ws = XLSX.utils.aoa_to_sheet(provAoA);
      XLSX.utils.book_append_sheet(wb, ws, 'Por Provincia');
    }
    if (cupAoA.length){
      const ws = XLSX.utils.aoa_to_sheet(cupAoA);
      XLSX.utils.book_append_sheet(wb, ws, 'Por Region CUP');
    }
    // Filename: Competidores_<linea>_<mercado>_<metrica>_<periodo>.xlsx
    const safe = s => String(s||'').replace(/[\\/?*\\[\\]:]/g, '-').replace(/\\s+/g, '_').slice(0, 50);
    const fname = `Competidores_${safe(market)}_${safe(metricNice)}_${safe(periodLabel)}.xlsx`;
    XLSX.writeFile(wb, fname);
  }
  document.getElementById('btn-export').addEventListener('click', exportExcel);

  // Init
  renderMktGrid();
  render();
  document.getElementById('cutoff').textContent = MONTHS.length ? `Hasta ${MONTHS[MONTHS.length-1]}` : '';
})();
</script>
<script src="__HUB__shared/sortable-heatmap.js"></script>
</body>
</html>
"""


def build_nav_items(line: str, main_url: str, ddd_url: str) -> str:
    """Construye los <a class='nav-item'> del nav unificado para competidores.html."""
    sections = [
        ('Resumen',             f'{main_url}'),
        ('Venta Interna',       f'{main_url}#s-bud'),
        ('Mercado IQVIA',       f'{main_url}#s-perf'),
        ('Recetas',             f'{main_url}#s-rec'),
        ('Stock',               f'{main_url}#s-stock'),
        ('Cobertura',           f'{main_url}#s-cover'),
        ('Mostrador vs Convenios', f'{main_url}#s-can'),
        ('Convenios',           f'{main_url}#s-conv'),
        ('Precios',             f'{main_url}#s-prec'),
    ]
    items = [f'<a class="nav-item" href="{href}">{label}</a>' for label, href in sections]
    # DDD (red pill)
    items.append(f'<a class="nav-tab-ddd" href="{ddd_url}">DDD</a>')
    # Competidores (active)
    items.append('<a class="nav-item on" href="./competidores.html">Competidores</a>')
    # Bonos PAP (only cardio + SNC)
    if line in ('cardio', 'SNC'):
        items.append('<a class="nav-tab-bonos" href="https://bonos-pap.pages.dev/" target="_blank" rel="noopener">Bonos PAP ↗</a>')
    return '\n    '.join(items)


def build_page(line: str, shape: str, main_path: str) -> str:
    main_p = REPO / main_path
    base_dir = main_p.parent
    out_path = base_dir / 'competidores.html'
    main_filename = main_p.name

    if shape == 'A':
        # Extract data from main DDD
        d_json = extract_shape_a_data(main_p)
        data_file = base_dir / 'competidores-data.js'
        data_file.write_text(f'window.SFG_COMP_DATA = {d_json};\n', encoding='utf-8', newline='')
        data_loader = '<script src="./competidores-data.js"></script>'
        loader_note = f'extracted to {data_file.name}'
    elif line == 'mujer':
        comp_data = base_dir / 'competidores-data.js'
        if comp_data.is_file():
            data_loader = '<script src="./competidores-data.js"></script>'
            loader_note = f'reuses {comp_data.name} (Shape A pre-built)'
        else:
            data_loader = '<script src="./data.js"></script>'
            loader_note = 'reuses ./data.js (Shape B fallback)'
    else:
        data_loader = '<script src="../data.js"></script>'
        loader_note = 'reuses ../data.js'

    # Per-line URL paths (relative from competidores.html location)
    # dermato: competidores.html en `dermatologia/`. Main = `dermato_dashboard.html`.
    # Otros: competidores.html en `<line>/DDD/`. Main = `../index.html` or `../psq_dashboard.html`.
    if line == 'dermatologia':
        main_url = 'dermato_dashboard.html'
        ddd_url  = 'dermato_ddd.html'
        hub_url  = '../'
    else:
        main_url = f'../{main_filename.replace("psq_ddd.html","psq_dashboard.html").replace("index.html","index.html")}'
        # Actually for cardio/ATB/OTC/respi/mujer, main = '../index.html'; SNC = '../psq_dashboard.html'
        if line == 'SNC':
            main_url = '../psq_dashboard.html'
        else:
            main_url = '../index.html'
        ddd_url  = './'
        hub_url  = '../../'

    nav_items_html = build_nav_items(line, main_url, ddd_url)

    html = (PAGE_HTML
            .replace('__TITLE__', LINE_TITLES.get(line, line))
            .replace('__LINE__', LINE_TITLES.get(line, line).upper())
            .replace('__MAIN__', main_filename)
            .replace('__HUB__', hub_url)
            .replace('__NAV_ITEMS__', nav_items_html)
            .replace('__DATA_LOADER__', data_loader))

    out_path.write_text(html, encoding='utf-8', newline='')
    return f'  [{line}] OK ({loader_note}, page={out_path.stat().st_size:,} bytes)'


def patch_main_ddd_nav(line: str, main_path: str):
    """Add a 'Competidores' tab to the nav of the main DDD page."""
    p = REPO / main_path
    text = p.read_text(encoding='utf-8', errors='replace')
    if 'href="./competidores.html"' in text or 'competidores.html' in text:
        return f'  [{line}/nav] SKIP (ya tiene tab)'

    # Find DDD tab and inject Competidores after it.
    # Common pattern: <a class="nav-tab hl" href="./">DDD</a> in cardio/ATB/OTC/respi
    # SNC/dermato use psq_ddd.html / dermato_ddd.html so URL is "./psq_ddd.html" probably
    # Strategy: find href="./" or class with hl and inject right after.
    patterns = [
        r'(<a[^>]*class="[^"]*\bhl\b[^"]*"[^>]*href="\./"[^>]*>DDD</a>)',
        r'(<a[^>]*class="[^"]*\bhl\b[^"]*"[^>]*href="\./[^"]*"[^>]*>DDD[^<]*</a>)',
        r'(<a[^>]*href="\./"[^>]*>DDD</a>)',
    ]
    new_tab = '<a class="nav-tab" href="./competidores.html">Competidores</a>'
    inserted = False
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            text = text[:m.end()] + new_tab + text[m.end():]
            inserted = True
            break

    if not inserted:
        return f'  [{line}/nav] WARN no insertion point found'

    p.write_text(text, encoding='utf-8', newline='')
    return f'  [{line}/nav] OK tab inserted'


def main():
    print('Build paginas competidores DDD...\n')
    for line, shape, main_path, _ in LINES:
        try:
            print(build_page(line, shape, main_path))
        except Exception as e:
            print(f'  [{line}] ERROR: {e}')
    print()
    print('Patch nav del DDD principal...\n')
    for line, _, main_path, _ in LINES:
        print(patch_main_ddd_nav(line, main_path))
    print('\nListo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
