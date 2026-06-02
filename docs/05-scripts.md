# 05 · Catálogo de scripts (`shared/`)

> Los 97 archivos de `shared/`, agrupados por categoría. Propósito tomado del
> docstring/header real de cada script. Cómo correr: `.py` → `py shared/<x>.py`;
> `.ps1` → `pwsh shared/<x>.ps1`; `.js`/`.css` → se inyectan/cargan en las páginas.

**Buscá por categoría:** [BUILD](#build) · [SYNC](#sync) · [MERGE](#merge) ·
[REBUILD](#rebuild) · [PATCH](#patch) · [FIX](#fix) · [AUDIT/VERIFY](#auditverify) ·
[INJECT/UX](#injectux) · [CLEANUP](#cleanup) · [COMPETIDORES-DDD](#competidores-ddd) ·
[LIBRERÍAS JS](#librerías-js) · [CSS](#css) · [JSON cache](#json-cache) · [REFERENCIA](#referencia)

---

## BUILD
Generan archivos derivados desde fuentes.

| Script | Propósito | Output |
|---|---|---|
| `build-all.ps1` | Orquestador mensual. `-Month YYYY-MM -Lines … [-CommitPush]`. Regenera los `data.js` desde el IQVIA master + fuentes por línea. | `<linea>/data.js`, opcional commit/push |
| `build-kpis.py` | KPIs SIE-only por línea y período (YTD/MAT/Trim/Sem/Mensual) para el hub. | `kpis.json` |
| `build-families-perf.py` | Data multi-período por familia para la vista "Por Marca". | `kpis-families.json` |
| `build-summary.py` | Mini-tabla cross-línea con los KPIs principales del hub. | `shared/cross-line-summary.json` |
| `build-budget-overrides.ps1` | Lee el Excel de Estimado de Ventas y arma el objeto de overrides. | `shared/budget-overrides.js` |
| `build-competidores-shape-a.py` | Builder genérico DDD (Shape A) desde xlsx `Producto-Mol-ATC-provincia`. | `<linea>/DDD/competidores-data.js` |
| `build-competidores-pages.py` | Página "Competidores DDD" por línea (heatmap geográfico + filtros). | `<linea>/DDD/competidores.html` |
| `build-mujer-competidores-data.py` | Versión mujer del builder DDD (segmentado por familia). | `mujer/DDD/competidores-data.js` |

---

## SYNC
Sincronizan desde el IQVIA master respetando la segmentación existente.

| Script | Propósito | Toca |
|---|---|---|
| `sync-mujer-pm.py` | Sincroniza `mol_perf` de mujer (familias SIN ESTROGENO…CLIMATIX). Al final corre los rebuilds fijos (`LOCKED_REBUILDS`). | `mujer/index.html` |
| `sync-snc-pm.py` | Sincroniza `mol_perf` de SNC segmentado por molécula. | `SNC/index.html` |
| `sync-dermato-pm.py` | Sincroniza `mol_perf` de dermato segmentado por molécula. | `dermatologia/dermato_dashboard.html` |
| `sync-kpistrip-with-kpis-json.py` | Alinea el `kpiStrip` de cada tablero con `kpis.json`. | los 7 tableros |
| `sync-recetas-ui-with-mujer.py` | Sincroniza la UI de Recetas de las otras líneas con la de mujer (línea fuente). | 6 tableros |
| `slice-iqvia-master.py` | Recorta el AR_PM de 18 MB en cuts por línea (KB) para parsear rápido. Hoy: mujer. | `_iqvia-master/YYYY-MM/sliced/` |

---

## MERGE
Incorporan datos nuevos preservando lo previo (agregan meses, no reemplazan).

| Script | Propósito |
|---|---|
| `merge-april-2026-only.py` | Agrega SOLO Abr 2026 a `mol_perf` preservando TODO el histórico. **Patrón de referencia anti-pérdida de historia.** |
| `merge-ventas-internas.py` | Actualiza `budget[fam].YYYY.real` (Venta Interna) desde la Planilla de Ventas. |
| `merge-recetas-march.py` | Merge ad-hoc de un mes de recetas (cardio/ATB/OTC/respi) desde pivot CloseUp. |
| `merge-recetas-respi.py` | Recetas de respiratorio (10 mercados, pivot completo). |
| `merge-recetas-snc.py` | Recetas de SNC (inline `const D`). |
| `merge-recetas-mujer-march.py` | Recetas Mar 2026 de mujer. |
| `merge-stock.py` | Stock+ventas+facturación+días desde pivot SAP `Laboratorio-Familia-Producto`. |
| `merge-stock-april.py` | Stock/Cobertura de todas las líneas, corte abril. |
| `merge-precios.py` | Precios desde dump Manual Farmacéutico (cardio/ATB/OTC/respi). |
| `merge-carbidopa-into-benserazide.py` | Mergea CARBIDOPA_LEVODOPA dentro de BENSERAZIDE_LEVODOPA en SNC. |

---

## REBUILD
Reconstruyen un mercado/agregado específico.

| Script | Propósito |
|---|---|
| `rebuild-mujer-45-market.py` | `mol_perf['45']` de mujer = TRIP +45 vs solo VIASEK MENOCARE CAPS (oral). Excluye GEL/BARRA. **Locked en `sync-mujer-pm.py`.** |
| `rebuild-acemuk-atc-r05c0.py` | `respPerf.ACEMUK.atc.all` = TODOS los productos ATC R05C0 (Expectorantes). |
| `recompute-mol-perf-aggregates.py` | Rehace `quarterly_vals/ytd/mat/ms_*` desde `monthly_vals` en las 7 líneas. Correr tras cualquier merge/edición. |

---

## PATCH
Modifican la **estructura** HTML/JS (no los datos).

| Script | Propósito |
|---|---|
| `patch-venta-interna-table.py` | Tabla unificada de Venta Interna (1 fila/producto, V/Estim/%Cumpl) en 6 líneas (NO SNC). |
| `patch-multi-period-sections.py` | Inyecta las tablas multi-período (MAT/YTD/MES/TRIM) en Mercado IQVIA y Recetas. |
| `patch-aggregate-by-brand.py` | `renderPerf` agregado por marca. |
| `patch-canales-quarterly.py` | Reemplaza Mostrador vs Convenios por tabla trimestre×año. |
| `patch-budget-tri-redistribute.py` | Redistribución del shortfall solo en los próximos 3 meses. |
| `patch-precios-external.py` | Saca Precios del body y lo manda como pill externo en el nav. |

---

## FIX
Correcciones puntuales de datos o bugs.

| Script | Propósito |
|---|---|
| `fix-brandkpis-from-molperf.py` | Recomputa `brandKpis` IE/MS desde `mol_perf` (**fuente única**). |
| `fix-brandkpis-ie-vs-market.py` | Recomputa solo el IE de `brandKpis` con fórmula vs-market. |
| `fix-mol-perf-aggregates.py` | Arregla `ytd`/`mat` que usaban key `'Dec'` en vez del mes de cierre. |
| `fix-mol-perf-mat-monthly.py` | Arregla `mat` simplificado a solo entries anuales (rompía chart SNC). |
| `fix-kpi-order.py` | Ordena los KPIs (IE, MS%, Unidades, Crecimiento, Estimado, MS% Recetas) igual en LÍNEA y MARCA. |
| `fix-kpi-source-position.py` | Badge de fuente inline (no absolute) para no romper labels largos. |
| `fix-acneclin-split.py` | Separa ACNECLIN y ACNECLIN AP en `mol_perf.MINOCYCLINE` (derma). |
| `fix-atb-stock-2026.py` | Re-carga stock Ene-Abr 2026 de ATB (estaba 14-17× abajo). |
| `fix-otc-stock-empty.py` | Quita entries de stock placeholder (0/0) en OTC. |
| `fix-rec-comp-colors.py` | Colores visibles para competidores en el chart de Recetas. |
| `fix-ddd-quarterly-hardcoded.py` | Quita índices hardcodeados (12 meses/4 quarters) en DDD. |
| `fix-dermato-mar2026.py` | Extiende `mol_perf` derma a Mar 2026 + remueve productos. |
| `fix-dermato-mometax.py` | Restaura recetas de MOMETAX (estaban en 0 desde Oct 2025). |
| `fix-medicos-jan-feb-mar-2026.py` | Corrige `medicos` (count único, no suma) Ene-Mar 2026. |
| `fix-mujer-d3-comp.py` | Pobla `rec_comp.D3` de mujer (estaba vacío). |
| `fix-mujer-solo-ms.py` | Saca la familia SOLO del MS% Recetas (OTC, sin pivot CloseUp). |
| `fix-comp-export-format.py` | Export Excel de competidores con números/formatos reales. |

---

## AUDIT/VERIFY
Validación (los 3 primeros los corre el pre-commit hook).

| Script | Propósito |
|---|---|
| `audit-full.py` | 8 checks cross-línea/cross-métrica. **El verificador principal.** |
| `audit-consistency.py` | Compara IE/MS/units/recetas entre los distintos lugares del tablero. |
| `check-syntax-and-consistency.py` | Sintaxis + antipatrones en HTML/JS. |
| `verify-history-preserved.py` | Bloquea si `mol_perf` pierde meses vs un commit base. |

---

## INJECT/UX
Agregan features o capa visual a las páginas.

| Script | Propósito |
|---|---|
| `inject-ux-shared.py` | Inyecta `microinteractions.css`/`design-tokens.css`/`ux-shared.js` en las 21 páginas. |
| `inject-budget-total-option.py` | Opción "TOTAL LÍNEA" en el selector de Venta Interna. |
| `inject-budget-redistribute.py` | Strip de totales del año + redistribución del shortfall. |
| `inject-budget-redistribute-chart.py` | Segmento ámbar "Redistribuido" apilado en el chart. |
| `inject-perf-brand-filter.py` | Filtro de competidores en Mercado IQVIA. |
| `inject-rec-brand-filter.py` | Filtro de competidores en el panel de Recetas. |
| `add-kpi-source-badges.py` | Badge de fuente (IQVIA/Recetas/Vta Int) en cada KPI tile. |
| `make-recetas-evolution-dynamic.py` | Hace dinámica la tabla "SIE · Evolución mensual" de Recetas. |
| `apply-sidebar-layout.py` | Filtro de marca como sidebar fixed + bloque KPIs con borde rojo. |
| `apply-comp-ie-total-pais.py` | Propaga el template de competidores OTC a las otras 6 páginas. |

---

## CLEANUP
Consolidación, dedup, renombres, rediseños.

| Script | Propósito |
|---|---|
| `consolidate-isis-alta-dosis.py` | Junta los 3 SKUs ISIS en `mol_perf['ALTA DOSIS']` (mujer) como un brand. |
| `dedup-convenios.py` | Saca Obras Sociales duplicadas en convenios. |
| `trim-mujer-stock.py` | Limita el stock de mujer a 2025+2026. |
| `enrich-molperf-from-competidores.py` | Agrega todas las brands de competidores a `mol_perf[mercado].products`. |
| `apply-product-exclusions.py` | Saca de TODOS los análisis los productos de `excluded-products.py`. |
| `remove-medicos-and-table-comparativo.py` | Saca Médicos + convierte Comparativo en tabla. |
| `remove-rec-detail.py` | Oculta la tabla "SIE · Evolución mensual / SIE vs Mercado" en Recetas (NO SNC). |
| `rename-presupuesto-to-estimado.py` | Renombra "Presupuesto" → "Estimado de Ventas" en labels. |
| `unify-fonts-and-colors.py` | Unifica fuente (IBM Plex) y colores en DDD/competidores. |
| `redesign-nav-compact.py` | Navbar compacto de una fila en las 7 líneas. |
| `redesign-nav-ddd-comp.py` | Mismo navbar compacto en DDD/Competidores. |
| `_restore-snc-budget-chart.py` | Restaura el chart original de Venta Interna en SNC (deshace la tabla). |

---

## COMPETIDORES-DDD
Vuelcan los datos de competidores a las vistas DDD.

| Script | Propósito |
|---|---|
| `update-ddd-from-competidores.py` | Actualiza `DDD/index.html` desde `competidores-data.js`. |
| `update-ddd-otcdata-from-competidores.py` | `OTC_DATA.ddd` de ATB/OTC/respiratorio. |
| `update-ddd-mujer-from-competidores.py` | `mujer/DDD/data.js` (`OTC_DATA.dddGineco`). |
| `update-dermato-precios.py` | Precios de dermato (shape flat) desde Manual Farmacéutico. |

---

## Librerías JS
Se cargan/inyectan en las páginas (no se "corren").

| Archivo | Rol |
|---|---|
| `multi-period-table.js` | Render de la tabla multi-período (MAT/YTD/MES/TRIM × 6 métricas) en IQVIA y Recetas. |
| `budget-overrides.js` | `OVERRIDES[linea][producto] = [12 meses]` del Estimado de Ventas (generado). |
| `data-status.js` | Badge "Datos al DD/MM/YYYY" + grisado de familias sin SIE. |
| `export-common.js` | Helpers comunes de export (Excel/PDF). |
| `export-dashboard.js` | Botón "Exportar Excel" del tablero. |
| `export-ddd.js` | Export de la vista DDD. |
| `export-pdf.js` | Botón "Exportar PDF" (print stylesheet A4 landscape). |
| `ux-shared.js` | Toasts, empty states, feedback de filtros. Idempotente. |
| `resize-cols.js` | Columnas redimensionables (heatmaps DDD). |

## CSS
| Archivo | Rol |
|---|---|
| `design-tokens.css` | Tokens canónicos (colores, fuentes, spacing). Se inyecta primero. |
| `microinteractions.css` | Animaciones/hover/transiciones. |
| `responsive.css` | Overrides mobile-first para las 21 páginas (incluye la regla de "Venta Interna sin scroll horizontal"). |
| `multi-period-table.css` | Estilos de la tabla multi-período (colores por período/IE/Var pp). |

## JSON cache
| Archivo | Rol |
|---|---|
| `canales_quarterly.json` | Cache de la tabla trimestral de canales. |
| `cross-line-summary.json` | Salida de `build-summary.py` (mini-tabla del hub). |

## Referencia
| Archivo | Rol |
|---|---|
| `excluded-products.py` | Lista canónica de productos a excluir de todos los análisis. |

---

> Si un script no tiene docstring claro, su nombre + esta tabla alcanzan para ubicarlo.
> Al tocar uno, leé su header completo primero — varios son **idempotentes** (se
> pueden re-correr sin daño) y otros son **one-off** (un mes puntual).
