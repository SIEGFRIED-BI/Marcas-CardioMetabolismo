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
5. `shared/check-molperf-suma-productos.py` — `suma(mol_perf[fam].products)` ==
   total de la familia, EXACTO. Es la invariante de la que
   `recompute-mol-perf-aggregates.py` deriva el total del mercado: si no cierra, el
   próximo recompute mueve el total publicado y arrastra el tablero Total y los KPIs
   (error silencioso y diferido). La fila `Otros (resto del mercado)` es parte de la
   suma y puede quedar levemente negativa por el redondeo por-producto del build;
   se tolera hasta 0,5% del período.

Si algo falla, NO usar `--no-verify`. Investigar y arreglar.
(El hook vive en `.git/hooks/pre-commit`; copia versionada: `shared/git-pre-commit.sh`.)
Chequeos manuales extra: `shared/check-mercados-fuente.py` (familias que mezclan
mercados DENTRO de una linea), `shared/check-mercados-cross-linea.py` (una marca
SIE de OTRA linea colada en el mol_perf de esta — bug MOMETASONE 2026-07-30, el
anterior no lo ve porque compara contra el competidores-data.js de la propia
linea) y `shared/bump-cache-busters.py --check`.

**Mercados-copia del DDD regional (doble conteo).** Los mercados de la columna `Mercado`
del panel DDD son una **jerarquía deliberada**: un contenedor y sus sub-segmentos
(`Macromax` ⊃ `Macromax pediátr.`; `Antipsicóticos` ⊃ `Quetiapinas`; `Micomazol Total` ⊃
`Micomazol Crema`). El dato está bien — el problema es que `build-competidores-shape-a.py`
re-indexa por molécula/ATC (`units[brand][region][mes] += u`) y la columna `Mercado` **no**
forma parte de la clave, así que si el archivo trae el contenedor Y el contenido esas
unidades se suman **dos veces**. Medido en ATB, May-2026: el mercado de azitromicina
publicaba 259.658 u contra 213.664 u reales en Qlik (+21,5%).
La lista vive en **`shared/ddd-mercados-copia.json`** y el builder saltea esas filas. Se
regenera con `shared/qlik/detectar-mercados-copia-xlsx.py`, que compara **celda por celda**
`(región, producto, mes)` sobre el propio xlsx y solo marca copias EXACTAS. Conviene
re-correrlo cuando aparezcan mercados nuevos en el panel.
**mujer NO se lista a propósito**: `build-mujer-competidores-data.py` indexa por mercado
(`data[market][brand][region][mes]`), o sea cada mercado del Ateneo es su propio bucket con
su total correcto y ahí no hay doble conteo — descartar le borraría 22 mercados (los
segmentos de marketing que esa página muestra).
NO usar la API de Qlik para detectar esto: devuelve agregados a medio calcular y el mismo
test dio resultados distintos entre corridas, con la dirección contenedor/contenido
invertida (marcaba `Hexaler ⊆ Alergical` con Hexaler en 18,0M y Alergical en 9,5M).

**Vista alternativa del mercado por clase terapéutica (`mercadosATC`).** En Mercado IQVIA
hay un selector *Universo: Molécula / Clase terapéutica*. La segunda mide cada marca
contra su clase ATC III del Ateneo (ROXOLAN: 2,0% en ROSUVASTATIN vs 1,05% en
`C10A - PRD REGULADORES LIPIDOS`, y de #10 pasa a #24 de 135). La genera
`shared/build-mercados-atc.py` — clasificación del Ateneo, unidades del master AR_PM,
porque el Ateneo viene en MAT móvil y la tabla necesita mensual. Valida el cruce AR_PM vs
Ateneo por clase (265/265 cierran) y aborta si alguna se pasa de `--tol`.
Vive en una clave **aparte** de `mol_perf` a propósito: `build-total.py:260` y
`check-total-consistency.py:54` recorren `mol_perf` para armar el mercado de compañía, y
el universo ATC ancho bajaría el MS% publicado. **Ese paso tiene que correr después de
`build-all`**: el literal `$dashboardData` de cada `build-data.ps1` (27 claves) reescribe
`data.js` entero y borra cualquier clave que no conozca. Ya está encadenado en
`update-all.ps1`, igual que `itemize-molperf-otros.py`.
Ojo con `respPerf` (cardio/ATB/respiratorio): es un intento previo de lo mismo
(`{molecule,atc} × {all,etico,popular}`) pero está **truncado a 8 productos sin fila de
residuo** (cardio ROXOLAN `atc.all` suma 9.530.488 contra su `family.mat` 20.671.610),
los 6 nodos `etico`/`popular` están vacíos y va un mes atrasado. Solo respiratorio lo
consume, en el gráfico (`respiratorio/index.html:643`), así que ahí conviven dos vistas
ATC con números distintos.

**Ranking completo en la apertura del mercado.** Los `build-data.ps1` de
cardio/ATB/OTC/respiratorio cortan en 8 productos por mercado y meten el resto en
`Otros (resto del mercado)`, así que la apertura de la tabla multi-período mostraba un
ranking truncado (el render no tiene tope: es el dato). Lo destapa
`shared/itemize-molperf-otros.py` (`--mode full`, default), que itemiza el universo del
mercado desde el master AR_PM. **La regla es asimétrica** y conviene no tocarla:
*sub-contar* (los candidatos no llegan a explicar el bucket, ej. respiratorio DECADRON)
es seguro y se itemiza igual dejando el remanente en `Otros`; *sobre-contar* (los
candidatos exceden el bucket) significa que la molécula abarca más que el mercado y se
**rechaza** — es el caso de los mercados splitteados por dosis, ATB CEFALEXINA ARG
(+1953%) y ARG DUO (+5038%), cuyas dos familias particionan la molécula CEFALEXIN.
Los candidatos que son marcas SIEGFRIED se excluyen siempre: `check-total-consistency.py`
y `build-total.py` arman el universo SIE de compañía con `sie.setdefault(p['prod'], ...)`,
o sea dedupean por NOMBRE y se quedan con la primera copia, así que una copia agregada
puede tapar a la publicada según el orden de iteración y mover el MAT SIE de compañía.

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
