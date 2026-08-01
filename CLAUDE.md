# Marcas-CardioMetabolismo · Notas para Claude

## ⚠️ REGLAS CRÍTICAS — errores que ya pasaron, NO repetir
> Detalle completo + causa/fix de cada uno en `docs/07-lecciones-y-errores.md`.

1. **Planilla SAP = Gran Familia (col0) + Familia (col1).** Matchear venta interna
   por **Familia (col1)**, NUNCA sumar la Gran Familia entera a una sub-marca.
   (Bug: ALTA DOSIS se tragó todas las ISIS → %Cumpl 705%.)
2. **Una familia de `mol_perf` = UN mercado de la fuente (una molécula).** Si la
   fuente separa moléculas (mono vs combo, sildenafil vs tadalafil), el dashboard
   también. (Bug: ROXOLAN mezclaba rosuvastatina + rosuvastatina/ezetimibe.)
3. **Mercado de Recetas = suma de `rec_comp` (historia completa)**, no `rec_ms.mkt`
   (suele venir con pocos meses → mata IE/Var pp).
4. **`?v=<hash>` del cache-buster siempre fresco** — automático (build-all +
   pre-commit). Nunca editar data.js sin que el `?v` cambie, o el deployado
   sirve la versión vieja cacheada.
5. **Los splits de Venta Interna (MAGNUS/36, ROXOLAN/PLUS) NO son parte del merge.**
   Re-correr `merge-ventas-internas.py` completo los REVIERTE. Re-aplicarlos
   después, o correr la corrección de la línea puntual.
6. **IE solo con base previa significativa** (crecimiento <5×); si no, "—".
7. **Los merges AGREGAN meses, nunca reemplazan** (lo bloquea verify-history).

## Convenciones de naming (importantes — no equivocarse)

- **"Estimado de Ventas"** — NO "Presupuesto". Es la métrica que viene de
  SAP / planificación comercial (campo `D.budget[prod].YYYY.budget`). El
  campo JS se llama `budget` por compatibilidad histórica pero el label
  user-facing es siempre "Estimado de Ventas" o "Estimado".
  - Section title: "Venta Interna vs Estimado de Ventas"
  - Row label / KPI card: "Estimado"
  - Page subtitle: "...· Estimado Vtas ·..."
  - Copy: "...vs estimado de ventas planificado..."

- **"Venta Interna"** — venta SAP de Siegfried. NO confundir con "Mercado".

- **"Mercado IQVIA"** — datos de IQVIA Premium Market (units). NO confundir
  con venta interna.

- **"Recetas"** — datos de CloseUp (recetadas). Lag de ~1 mes vs IQVIA.

- **SIE** = Siegfried (productos propios). `is_sie: true` en mol_perf.

## Antes de cualquier commit

El pre-commit hook ejecuta:
0. `shared/bump-cache-busters.py` — `?v=<hash>` fresco + re-stagea páginas
1. `shared/check-syntax-and-consistency.py` — sintaxis HTML/JS
2. `shared/verify-history-preserved.py --baseline HEAD --strict` — protege
   contra pérdida de meses históricos en mol_perf
3. `shared/audit-full.py` — consistencia kpis.json ↔ data.js ↔ mol_perf
4. `shared/check-venta-vs-estimado.py` — bloquea %Cumpl >500% (lumping col0/col1)

Si algo falla, NO usar `--no-verify`. Investigar y arreglar.
(El hook vive en `.git/hooks/pre-commit`; copia versionada: `shared/git-pre-commit.sh`.)
Chequeos manuales extra: `shared/check-mercados-fuente.py` (familias que mezclan
mercados DENTRO de una linea), `shared/check-mercados-cross-linea.py` (una marca
SIE de OTRA linea colada en el mol_perf de esta — bug MOMETASONE 2026-07-30, el
anterior no lo ve porque compara contra el competidores-data.js de la propia
linea) y `shared/bump-cache-busters.py --check`.

## Cierre mensual — 1 comando

Dejar las bases nuevas y correr **un** comando (Windows PowerShell **5.1**, NO pwsh 7):

```
powershell.exe -File shared\update-all.ps1 -Month AAAA-MM
```

Qué hace (en orden) y **frena antes de pushear** (revisás el `git diff` y pusheás vos):
1. `build-all.ps1` → cardio/ATB/OTC/mujer/respiratorio (PM + DDD + venta).
2. `sync-snc-pm.py` / `sync-dermato-pm.py --master` → SNC y derma. **Re-aplica
   SIEMPRE** `rebuild-pgb-multidosis-snc.py` y `rebuild-brexpiprazole-ateneo-snc.py`
   (el sync de SNC los pisaría: deja PREGABALIN completo y borra BREXPIPRAZOLE).
3. `build-competidores-shape-a.py --month` (regional, glob por mes).
4. `build-kpis.py` + `build-families-perf.py` + `sync-kpistrip-with-kpis-json.py`.
5. `finalize-labels.py` → **todas** las etiquetas desde el dato real + "Datos al"
   = fecha de hoy (última modificación). NO editar etiquetas a mano.
6. `bump-cache-busters.py` + gates (audit/sintaxis/history).

**Bases que se dejan:** PM IQVIA en `_iqvia-master/AAAA-MM/AR_PM*.xlsx`; recetas/
venta/regionales en `fuentes-originales` de cada línea. `-SkipBuildAll` saltea el
rebuild de las 5 (útil si solo cambió SNC/derma/recetas).

**No tocar:** `window.OTC_DATA` (lo usan las páginas de competidores Shape B).

## Líneas y archivos

| Línea | Path | Estructura datos |
|---|---|---|
| Cardio | `cardio/index.html` + `cardio/data.js` | `window.OTC_DASHBOARD` |
| ATB | `ATB/index.html` + `ATB/data.js` | `window.OTC_DASHBOARD` |
| OTC | `OTC/index.html` + `OTC/data.js` | `window.OTC_DASHBOARD` |
| Respi | `respiratorio/index.html` + `respiratorio/data.js` | `window.OTC_DASHBOARD` |
| Mujer | `mujer/index.html` (inline) | `const D` |
| SNC | `SNC/index.html` (inline) | `const D` |
| Derma | `dermatologia/dermato_dashboard.html` (inline) | `const D` |

## Estado actual del Estimado de Ventas (a 2026-04)

| Línea | Tiene estimado 2026 | Total estimado 2026 |
|---|---|---|
| OTC | ✓ | 1.697.979 u. |
| Mujer | ✓ | 3.059.129 u. |
| SNC | ✓ | 1.211.510 u. |
| Derma | ✓ | 1.266.009 u. |
| Cardio | ✗ | — |
| ATB | ✗ | — |
| Respi | ✗ | — |

Las 3 líneas sin estimado muestran "—" en las columnas Estim./%Cumpl pero
mantienen la fila Venta mes a mes.
