# 01 · Arquitectura — cómo se conecta todo

> Mapa mental del proyecto **Marcas-CardioMetabolismo**. Empezá por acá si nunca
> tocaste el repo. Para el paso a paso de actualización → `02-actualizar.md`.

---

## La cadena completa en una línea

```
Excel externos (IQVIA / SAP / CloseUp / Manual Farmacéutico)
        │   ← viven en OneDrive: Hub-Marcas-Inputs/
        ▼
shared/ scripts  (sync- / merge- / build- / rebuild-)
        │
        ▼
DATOS por línea
   ├─ cardio/ATB/OTC/respiratorio → data.js   (window.OTC_DASHBOARD = {...})
   └─ mujer/SNC/dermatologia      → inline en el HTML (const D = {...})
        │
        ▼
shared/build-kpis.py  +  shared/build-families-perf.py
        │
        ▼
DERIVADOS (raíz del repo)
   ├─ kpis.json           → lo lee kpis.html (pestaña "Por Línea" / "Por Producto")
   └─ kpis-families.json  → lo lee kpis.html (pestaña "Por Marca")
        │
        ▼
PRESENTACIÓN
   ├─ index.html  (hub: tarjetas de las 7 líneas)
   ├─ kpis.html   (indicadores cross-línea)
   └─ <linea>/index.html + <linea>/DDD/* (tableros y competidores)
        │
        ▼
git push → Cloudflare Pages redeploya automático
```

**Regla de oro:** los `data.js` / `const D` y los `kpis*.json` son **DERIVADOS** —
se regeneran con scripts. La fuente de verdad son los **Excel** en OneDrive.
Nunca editás un número a mano en `data.js`; corrés el script que lo regenera.

---

## Dónde vive cada cosa

### Repo de código — `C:\Users\camarinaro\Marcas-CardioMetabolismo`
| Qué | Path |
|---|---|
| Hub (landing) | `index.html` |
| Indicadores cross-línea | `kpis.html` + `kpis.json` + `kpis-families.json` |
| Notas de naming para Claude | `CLAUDE.md` |
| Scripts (97 archivos) | `shared/` |
| Esta documentación | `docs/` |

### Inputs (fuentes) — `C:\Users\camarinaro\OneDrive - Portalcorp\Documentos\Hub-Marcas-Inputs`
| Qué | Path |
|---|---|
| IQVIA Premium master | `_iqvia-master/YYYY-MM/AR_PM_FV_Standard_*.xlsx` (18 MB) |
| IQVIA MAT móvil (alterno) | `_iqvia-master/YYYY-MM/Ateneo Total - MAT Movil_*.xlsx` |
| Cuts ya recortados por línea | `_iqvia-master/YYYY-MM/sliced/` |
| Estimado de Ventas | `Estimados VENTA vigentes MKT sidus.xlsx` |
| Fuentes por línea/mes | `cardio/2026-04/`, `ATB/…`, `OTC/…`, `respiratorio/…`, `dermato/…`, `linea-mujer/…`, `PSQ/…` |
| Convenios | `convenios NUEVO/` |
| Guía de la carpeta | `README.txt` |

> **Por esto se sentía "vacío":** las fuentes Excel **no están en el repo** —
> están en OneDrive, en una estructura paralela. El repo solo guarda los
> resultados ya procesados (los `data.js`).

---

## Las dos arquitecturas (y por qué conviven)

| Patrón | Líneas | Cómo se cargan los datos |
|---|---|---|
| **Archivo separado** | cardio, ATB, OTC, respiratorio | `<linea>/index.html` hace `<script src="data.js">`; ese `data.js` define `window.OTC_DASHBOARD = {...}` |
| **Inline** | mujer, SNC, dermatologia | El objeto `const D = {...}` está **adentro** del HTML (`mujer/index.html`, `SNC/index.html`, `dermatologia/dermato_dashboard.html`) |

Ambos objetos tienen **el mismo schema** (mismas claves). La diferencia es solo
*dónde* vive el objeto. Históricamente las primeras 4 líneas se armaron con un
generador (`build-data.ps1`) que escupe `data.js`; las otras 3 se editan/
sincronizan inline con los `sync-*-pm.py`.

---

## Las 7 líneas de un vistazo

| Línea | Archivo principal | Variable | Datos | Particularidades |
|---|---|---|---|---|
| **cardio** | `cardio/index.html` + `cardio/data.js` | `window.OTC_DASHBOARD` | separado | + `respPerf`, `brandKpis` |
| **ATB** | `ATB/index.html` + `ATB/data.js` | `window.OTC_DASHBOARD` | separado | + `respPerf`, `brandKpis` |
| **OTC** | `OTC/index.html` + `OTC/data.js` | `window.OTC_DASHBOARD` | separado | sin `respPerf` |
| **respiratorio** | `respiratorio/index.html` + `respiratorio/data.js` | `window.OTC_DASHBOARD` | separado | `data.js` más grande (5.4 MB) |
| **mujer** | `mujer/index.html` (inline) | `const D` | inline | + `iqviaMeta`; mercados con composición fija (`45`) |
| **SNC** | `SNC/index.html` (inline) | `const D` | inline | + `kpiByBrand`; chart Venta Interna propio (no tabla) |
| **dermatologia** | `dermatologia/dermato_dashboard.html` (inline) | `const D` | inline | + `familyMap`; `precios` flat distinto |

Detalle de claves por línea → `04-diccionario.md`.

---

## Secciones de cada tablero (nav tabs) y qué dato leen

| Sección | Dato que usa | Render |
|---|---|---|
| Resumen / KPIs | `kpiStrip`, `brandKpis` | `renderKpis`, `renderBrandKpis` |
| **Venta Interna** | `budget` | `renderBudget` |
| **Mercado IQVIA** | `mol_perf` (+ `respPerf` en cardio/ATB/respi) | `renderPerf`, `renderMultiPeriodTable('iqvia')` |
| **Recetas** | `rec_ms`, `rec_comp`, `recetas` | `renderRec`, `renderMultiPeriodTable('recetas')` |
| **Stock** | `stock`, `stock_pres`, `stock_alerts` | `renderStock` |
| **Cobertura** | `stock_pres`, `coverage_labels` | `renderCobertura` |
| **Mostrador vs Convenios** | `canales`, `canales_quarterly` | `renderCanales` |
| **Convenios** | `convenios` | `renderConv` |
| **Precios** | `precios`, `prec_iqvia` | `renderPrec` |

Las tablas **multi-período** (MAT/YTD/MES/TRIM × Units/MS%/IE/Var pp) que se ven
en Mercado IQVIA y Recetas las dibuja `shared/multi-period-table.js` (mismo
componente en las 7 líneas).

---

## Conceptos clave (glosario corto)

- **SIE** = Siegfried (productos propios). En `mol_perf` se marcan con `is_sie: true`.
- **Venta Interna** = venta SAP de Siegfried (campo `budget[...].real`).
- **Estimado de Ventas** = el plan comercial SAP (campo `budget[...].budget`). El
  campo JS se llama `budget` por historia, pero el label SIEMPRE dice "Estimado
  de Ventas" (ver `CLAUDE.md`). NO decir "Presupuesto".
- **Mercado IQVIA** = unidades del mercado total (IQVIA Premium). Fuente de `mol_perf`.
- **Recetas** = recetadas (CloseUp). Lag de ~1 mes vs IQVIA. Fuente de `rec_*`.
- **MS%** (market share) = `unidades_SIE / unidades_mercado × 100`.
- **IE** (Índice de Evolución / iEvol) = crecimiento **relativo al mercado**:
  `(SIE_curr/SIE_prev) / (Mercado_curr/Mercado_prev) × 100`. IE > 100 = SIE
  crece más que el mercado (gana share). **No** es el crecimiento propio.
- **Ventanas de período** (cierre = último mes con dato, hoy Abr 2026):
  - **Mensual**: último mes vs mismo mes año-1.
  - **YTD**: Ene..cierre vs mismo rango año-1.
  - **Trimestre**: últimos 3 meses vs mismos 3 año-1.
  - **Semestre**: últimos 6 meses vs mismos 6 año-1.
  - **MAT**: últimos 12 meses vs los 12 previos.

---

## Archivos auxiliares por línea (no confundir con los datos)

- `<linea>/build-data.ps1` — generador histórico del `data.js` (cardio/ATB/OTC/respi/mujer).
- `<linea>/export.js` — exportación de esa línea.
- `mujer/market-overrides.js`, `mujer/price-ddd-overrides.js`, `mujer/data.js` — overrides legacy de mujer.
- `<linea>/DDD/competidores-data.js` — `window.SFG_COMP_DATA` (heatmap regional de competidores).
- `<linea>/DDD/competidores.html`, `<linea>/DDD/index.html` — vistas DDD.

---

Siguiente: **`02-actualizar.md`** (cómo meter un mes nuevo) ·
**`03-verificar.md`** (cómo chequear que está bien) ·
**`04-diccionario.md`** (qué es cada variable) ·
**`05-scripts.md`** (los 97 scripts).
