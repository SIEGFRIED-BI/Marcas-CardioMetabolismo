# 04 · Diccionario de datos (exhaustivo)

> Cada clave de los objetos de datos: qué es, en qué líneas existe, su shape, un
> ejemplo **real** del repo, y qué script la actualiza.
>
> El objeto se llama `window.OTC_DASHBOARD` en cardio/ATB/OTC/respiratorio (archivo
> `data.js`) y `const D` en mujer/SNC/dermatologia (inline en el HTML). **Mismo
> schema** en ambos. En este doc lo llamamos `D`.

---

## Mapa de claves por línea

| Clave | cardio | ATB | OTC | respi | mujer | SNC | derma |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `meses` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `sieProds` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `colors` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `compColors` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `budget` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `mol_perf` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `respPerf` | ✓ | ✓ | — | ✓ | — | — | — |
| `recetas` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `rec_ms` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `rec_comp` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `canales` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `canales_quarterly` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `convenios` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stock` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stock_alerts` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stock_pres` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `stock_pres_months` | — | — | — | — | — | ✓ | ✓ |
| `precios` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `prec_iqvia` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `kpiStrip` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `brandKpis` | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| `kpiByBrand` | — | — | — | — | — | ✓ | — |
| `sieMolMap` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `molLabels` | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `prodMap` | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `budIqviaMap` | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `familyMap` | — | — | — | — | — | — | ✓ |
| `defaults` | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |
| `coverage_labels` | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| `iqviaMeta` | — | — | — | — | ✓ | — | — |
| `meta` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 🔑 Estructuras núcleo

### `mol_perf` — Mercado IQVIA (la más importante)
Diccionario `familia → { products[], agregados }`. Una "familia" es un mercado IQVIA
(molécula o segmento). Fuente: IQVIA master vía `sync-*-pm.py` / `build-data.ps1`.

```jsonc
"mol_perf": {
  "DAURAN": {                          // familia / mercado
    "family": "DAURAN",
    "products": [
      {
        "prod": "DAURAN (SIE)",        // nombre del producto (con sufijo manuf)
        "manuf": "SIEGFRIED",
        "is_sie": true,                // ← true = producto Siegfried
        "monthly_vals": { "...": 1063, "Mar 2026": 1312, "Apr 2026": 1226 },
        "quarterly_vals": { "Q1 2026": 3438, ... },
        "ytd":  { "Apr 2025": 1893,  "Apr 2026": 4702 },   // YTD por año (key = mes de cierre)
        "mat":  { "Apr 2025": 3358,  "Apr 2026": 12609 },  // MAT por año
        "ms_monthly":   { "Apr 2026": 0.97 },              // share% del producto vs familia
        "ms_quarterly": { "Q1 2026": 0.95 },
        "ms_ytd":       { "Apr 2026": 1.06 },
        "ms_mat":       { "Apr 2025": 0.32, "Apr 2026": 0.99 }
      }
      // … resto de productos del mercado (competidores, is_sie:false)
    ],
    "monthly":   { "Apr 2026": <suma de todos los products> },
    "quarterly": { "Q1 2026": ... },
    "ytd":       { "Apr 2025": ..., "Apr 2026": ... },     // = mercado total
    "mat":       { "Apr 2025": 1056509, "Apr 2026": 1271751 }
  }
}
```
- **`ms_*` del producto** = `producto.<periodo> / familia.<periodo> × 100`.
- **Keys de `ytd`/`mat`**: el mes de cierre (`"Apr 2026"`), NO `"Dec"`. (Bug histórico
  arreglado por `fix-mol-perf-aggregates.py`.)
- Actualiza: `sync-mujer-pm.py`, `sync-snc-pm.py`, `sync-dermato-pm.py`,
  `build-data.ps1` (cardio/ATB/OTC/respi), `merge-april-2026-only.py`,
  `recompute-mol-perf-aggregates.py` (rehace los agregados).

---

### `rec_ms` — Recetas: SIE vs mercado (CloseUp)
`familia → { sie, mkt, ms, quarterly?, ms_quarterly? }`. Cada uno es un dict mensual.

```jsonc
"rec_ms": {
  "DAURAN": {
    "sie": { "Jan 2026": 350, "Feb 2026": 342, "Mar 2026": 376 },  // recetas SIE
    "mkt": { "Jan 2026": 5800, ... },                              // recetas mercado total
    "ms":  { "Mar 2026": 6.25 },                                   // share% recetas
    "ms_quarterly": { "Q1 2026": 6.1 }
  }
}
```
> ⚠️ **En mujer, `mkt` está vacío `{}`** en todas las familias. La tabla multi-período
> lo resuelve sumando `sie + competidores de rec_comp` en runtime (ver `multi-period-table.js`).
- Actualiza: `merge-recetas-*.py`.

### `rec_comp` — Recetas: competidores por marca
`familia → marca → { monthly, quarterly, total, *_medicos }`. **Shape nested** (no
es un dict de meses directo — los meses están bajo `.monthly`).

```jsonc
"rec_comp": {
  "DAURAN": {
    "ACUS RMM": {
      "monthly":   { "Mar 2026": 222, ... },
      "quarterly": { "Q1 2026": 600 },
      "total": 4609,
      "monthly_medicos": { ... }, "quarterly_medicos": { ... }, "total_medicos": ...
    }
  }
}
```
- En mujer cada marca trae además `is_sie` (bool).
- Actualiza: `merge-recetas-*.py`, `fix-rec-comp-colors.py`, `fix-mujer-d3-comp.py`.

### `recetas` — serie de recetas por marca (para el chart de evolución)
`marca → { "MMM YYYY": { recetas, medicos } }`. Lo que dibuja el gráfico de Recetas.
Actualiza: `merge-recetas-*.py`, `make-recetas-evolution-dynamic.py`.

---

### `budget` — Venta Interna vs Estimado de Ventas
`producto → año → { budget[12], real[12] }`. Arrays de 12 meses (Ene→Dic);
`null` = mes futuro sin dato.

```jsonc
"budget": {
  "DAURAN": {
    "2025": { "budget": [0,0,…], "real": [399,400,520,600,1000,739,…] },
    "2026": { "budget": [0,0,0,0,…], "real": [1574,1753,2119,1552,null,null,…] }
  }
}
```
- **`real`** = Venta Interna (SAP). **`budget`** = Estimado de Ventas (label NUNCA
  "Presupuesto"). `budget` puede ser todo 0 si esa línea no tiene estimado cargado.
- Actualiza: `real` ← `merge-ventas-internas.py`; `budget` ← `build-budget-overrides.ps1`
  (que escribe `shared/budget-overrides.js`, aplicado en runtime).

---

### `kpiStrip` — tira de KPIs arriba del tablero
Dict plano de valores ya calculados (línea-nivel). Lo que muestra la franja de
tarjetas. Debe coincidir con `kpis.json`.

```jsonc
"kpiStrip": {
  "ie_ytd": 98.3, "ie_mat": 95.3,
  "ms_ytd": 6.17, "ms_mat": 6.21,
  "units_ytd": 1298618, "units_ytd25": 1321698,   // SIE actual / año-1
  "units_mat": 4058592, "units_mat25": 4259255,
  "mkt_ytd26": 21045994, "mkt_mat26": 65369505,    // mercado total
  "ms_rec": 6.24, "sie_rec_dic25": 33939, "tot_rec_dic25": 546352,
  "bud_pct": null, "bud_total": 0, "real_total": ...
}
```
- Actualiza: `sync-kpistrip-with-kpis-json.py` (lo alinea con `kpis.json`).

### `brandKpis` — KPIs por marca (cardio/ATB/OTC/respi/derma)
`marca → { ytd{}, mat{}, budget{}, rec{} }` con IE, MS, units, growth.

```jsonc
"brandKpis": {
  "DAURAN": {
    "ytd": { "ie":218.9, "ms":1.1, "units":4702, "units_prev":1893, "market_total":442950, "growth":148.4 },
    "mat": { "ie":311.9, "ms":1.0, "units":12609, "units_prev":3358, "market_total":1271751, "growth":275.5 },
    "budget": { "pct":0, "real":2119, "target":0 },
    "rec": { "ms":1.5, "label":"…" }
  }
}
```
- **Fuente única = `mol_perf`.** Recalcular con `fix-brandkpis-from-molperf.py`.
- `kpiByBrand` (solo SNC) cumple un rol equivalente.

---

### `respPerf` — performance alternativa por molécula/ATC (cardio/ATB/respi)
`familia → { molecule, atc }`, cada uno con segmentación `all/etico/popular`. Usado
por charts específicos. Se reconstruye con `rebuild-acemuk-atc-r05c0.py` (ej. ACEMUK
= todo el ATC R05C0).

---

## 📦 Stock / Cobertura

### `stock` — inventario y días por familia
`familia → { "MMM YYYY": { stock, ventas, facturacion, dias } }`.
```jsonc
"stock": { "DAURAN": { "Mar 2025": { "stock":802, "ventas":494, "facturacion":520, "dias":49 } } }
```
Actualiza: `merge-stock.py`, `merge-stock-april.py`, fixes puntuales (`fix-atb-stock-2026.py`, `fix-otc-stock-empty.py`).

### `stock_pres` — stock por presentación (SKU)
Lo que usa la sección **Cobertura** (días por SKU, marcado de quiebre/bajo/alerta).
Cada entry trae al menos `{ familia, dias, … }`.

### `stock_alerts` — alertas de faltante
Lista de SKUs en quiebre/bajo. `stock_pres_months` (SNC/derma) = meses cubiertos.

---

## 🏪 Canales y Convenios

### `canales` — Mostrador vs Convenios
`familia → año → mes → { mostrador, convenio }` (unidades por canal).

### `canales_quarterly` — versión trimestral (texto %)
`familia → { año: { trimestre: "c% / m%" } }`. Arma `patch-canales-quarterly.py`.
También existe `shared/canales_quarterly.json` como cache.

### `convenios` — desglose por Obra Social
`familia → año → mes → { "<OS>": unidades }`. Los % suman 100 por OS (check #6 del audit).
`dedup-convenios.py` saca OS duplicadas.

---

## 💲 Precios

### `precios` — precio de lista por SKU
- cardio/ATB/OTC/respi: `precios[FAM].molecule[presentacion] = [entries]`.
- dermato: **shape flat** `precios[FAM][presentacion] = [entries]` (por eso usa
  `update-dermato-precios.py`, no `merge-precios.py`).

### `prec_iqvia` — precios de referencia IQVIA
Mismo espíritu, fuente IQVIA.

---

## 🗂️ Mapeos y metadatos

| Clave | Qué es |
|---|---|
| `meses` | `["Ene","Feb",…,"Dic"]` — labels de meses (es). |
| `sieProds` | lista de familias/marcas SIE de la línea (orden del selector). |
| `colors` | `marca → "#hex"` color por marca/familia. |
| `compColors` | paleta de grises para competidores. |
| `coverage_labels` | labels de la grilla de cobertura. |
| `sieMolMap` | `productoSIE → mercado/molécula` (qué mercado le corresponde a cada SIE). |
| `molLabels` | `mercado → label lindo` (cardio/ATB/OTC/respi). |
| `prodMap` | `marca → producto` (cardio/ATB/OTC/respi). |
| `budIqviaMap` | mapea marca de budget ↔ mercado IQVIA (para derivar real desde IQVIA). |
| `familyMap` | mapeo de familias (solo derma). |
| `defaults` | `{ brand, market, rec }` selección inicial del tablero. |
| `meta` | corte y labels. Ver abajo. |
| `iqviaMeta` | (solo mujer) `{ latestYear, latestMonth, latestKey, prevKey, latestShort, prevShort }` usado por `renderKpis`/`renderBrandKpis`. |

### `meta` (ejemplo real cardio)
```jsonc
"meta": {
  "latest_month": "Apr 2026",
  "ytd_keys": ["Apr 2024","Apr 2025","Apr 2026"],
  "mat_keys": ["Apr 2024","Apr 2025","Apr 2026"],
  "current_ytd_key": "Apr 2026", "prev_ytd_key": "Apr 2025",
  "current_mat_key": "Apr 2026", "prev_mat_key": "Mar 2025",
  "kpi_ytd_label": "YTD Abr'2026", "kpi_mat_label": "MAT Abr'2026",
  "budget_label": "...", "footer_date": "..."
}
```
> ⚠️ En mujer hay **dos** metadatos paralelos: `meta` (usado por la mayoría) e
> `iqviaMeta` (usado por el strip). Mantenerlos sincronizados — un desfasaje hace
> que los labels muestren el mes equivocado.

---

## 🌎 `window.SFG_COMP_DATA` — Competidores DDD (heatmap regional)
Vive en `<linea>/DDD/competidores-data.js`. Independiente de `D`.
```jsonc
{
  "months":  ["Abr-2024", …, "Mar-2026"],   // 24 meses
  "regions": ["AZUL-OLAVARRIA-TANDIL", …],   // ~42 regiones CUP
  "markets": {
    "Apixaban (Pixaban)": {
      "brands": ["PIXABAN", …],              // marcas SIE del mercado
      "brand_monthly": { "<marca>": { "<region>": [12+ valores] } },
      "total_monthly": { "<region>": [valores] }
    }
  }
}
```
Actualiza: `build-competidores-shape-a.py`, `build-mujer-competidores-data.py`,
`update-ddd-*-from-competidores.py`.

---

## 📊 Derivados del hub

### `kpis.json` (lo lee `kpis.html` → Por Línea / Por Producto)
```jsonc
{
  "generated_at": "...", "as_of_month": "Apr 2026",
  "periods": ["mensual","ytd","trimestre","semestre","mat"],
  "period_labels": { "ytd": "YTD 2026 (Ene–Apr) vs 2025", … },
  "lines": [
    {
      "key":"cardio","name":"CardioMetabólica","icon":"❤️","color":"#B01E1E",
      "href":"cardio/","owner":"…",
      "recetas_through":"Mar 2026","iqvia_through":"Apr 2026","venta_through":"Apr 2026",
      "has_recetas":true,
      "sparkline_units_sie":[…12…],"sparkline_months":[…12…],
      "kpis": {
        "ytd": {
          "recetas_sie":   {"curr":…,"prev":…,"ie":…},
          "ms_recetas":    {"curr":…,"prev":…},
          "mercado_recetas":{"curr":…,"prev":…,"ie":…},
          "units_sie":     {"curr":1298618,"prev":1321698,"ie":98.3},
          "ms_units":      {"curr":…,"prev":…},
          "mercado_units": {"curr":…,"prev":…,"ie":…},
          "venta_interna": {"curr":…,"prev":…,"ie":…}
        },
        "mensual": {…}, "trimestre": {…}, "semestre": {…}, "mat": {…}
      }
    }
    // × 7 líneas
  ],
  "products": [ … 64 productos con periods.{mensual,ytd,…} … ]
}
```
Genera: `shared/build-kpis.py`.

### `kpis-families.json` (lo lee `kpis.html` → Por Marca)
```jsonc
{
  "as_of_short":"Abr 2026",
  "period_labels": { "mat":"MAT Abr 2026 vs Abr 2025", … },
  "families": [
    {
      "family":"ACEMUK","display":"ACEMUK","line":"resp","lineName":"Respiratoria",
      "sie_brands":["ACEMUK (SIE)", …],
      "periods": {
        "mat": {"market_curr":38917473,"market_prev":49162714,
                "sie_curr":3079734,"sie_prev":3437819,
                "ms_curr":7.9,"ms_prev":7.0,"ie":113.0,"var_pp":0.9},
        "ytd": {…}, "mes": {…}, "trimestre": {…}
      }
    }
    // × 86 familias
  ]
}
```
Genera: `shared/build-families-perf.py`.

---

## Fórmulas (idénticas en build-kpis.py, build-families-perf.py y multi-period-table.js)

```
MS%  = SIE_units / Mercado_units × 100
IE   = (SIE_curr / SIE_prev) / (Mercado_curr / Mercado_prev) × 100
Var pp = MS%_curr − MS%_prev
```
Casos borde: si `prev == 0` o crecimiento > ~300% → `ie = null` (no comparable).
