# 07 · Lecciones y errores (NO repetir)

> Registro de bugs reales que pasaron, su causa raíz, el fix, y el **guardrail**
> que evita que vuelvan. Leer antes de tocar datos. Las reglas están al final.

---

## ❌ Bug 1 — El deployado mostraba datos viejos (cache-buster)

**Síntoma:** editaba `data.js`, pusheaba, pero la web seguía mostrando lo viejo
(ROXOLAN/MAGNUS sin los cambios).
**Causa:** el HTML cargaba `data.js?v=202605051436` (fecha fija) y ese `?v` no se
bumpeaba al cambiar `data.js`. El navegador/CDN servía la versión cacheada bajo
esa misma URL. (Además el sitio está detrás de Cloudflare Access, así que no se
puede verificar el deployado con curl externo — da la pantalla de login.)
**Fix:** `?v=<hash-del-contenido>` vía `shared/bump-cache-busters.py`.
**Guardrail (automático):**
- `build-all.ps1` corre `bump-cache-busters.py` al final.
- El **pre-commit hook** lo corre y re-stagea en cada commit que toque
  data.js / shared assets / páginas.
- Verificar a mano: `py shared/bump-cache-busters.py --check`.

---

## ❌ Bug 2 — Familias de Mercado IQVIA que mezclaban 2 mercados

**Síntoma:** ROXOLAN mostraba un mercado/MS% que no coincidía con la fuente.
**Causa:** la familia `mol_perf['ROXOLAN']` fusionaba DOS mercados que la fuente
separa: `Roxolan (Rosuvastatina)` (mono) + `Roxolan Plus` (rosuvastatina+ezetimibe).
También `HEXALER BRONQUIAL` estaba contaminada con productos **nasales**
(HEXALER NASAL, MOMETAX) que ya estaban en `HEXALER NASAL`.
**Fix:** split ROXOLAN→ROXOLAN+ROXOLAN PLUS; limpieza de HEXALER BRONQUIAL.
Clasificación tomada del `<linea>/DDD/competidores-data.js` (verificada marca por
marca contra la fuente, 0 mismatches).
**Regla:** **una familia de `mol_perf` = UN mercado de la fuente (una molécula).**
Si la fuente (PM nacional `Molecules Long`, o el competidores-data.js) separa dos
moléculas/mercados, el dashboard también.
**Guardrail:** `py shared/check-mercados-fuente.py` (detector de familias que
mezclan ≥2 mercados-fuente con SIE). Correr tras cualquier sync/rebuild de IQVIA.

---

## ❌ Bug 3 — Venta Interna: %Cumpl absurdo (705%) por col0 vs col1

**Síntoma:** mujer ALTA DOSIS mostraba %Cumpl 705% (venta 118k vs estimado 17k).
**Causa:** la **planilla SAP** tiene `Gran Familia (col0)` y `Familia (col1)`.
La Gran Familia `ISIS` agrupa TODAS las variantes (ISIS alta dosis, ISIS FREE,
ISIS MINI, ISIS MINI 24). El merge de mujer matcheaba por **col0**, así que
ALTA DOSIS (target Familia `ISIS`) se tragaba las 4 variantes (~118k) y
SIN ESTROGENO / BAJA DOSIS / COMPLEX quedaban en 0. El estimado (17k) sí estaba
a nivel Familia → de ahí el 705%.
**Fix:** `merge-ventas-internas.py` matchea por **Familia (col1)**, no Gran Familia.
**Regla:** **la planilla SAP agrupa por Gran Familia; siempre resolver a la
granularidad del budget key (Familia / presentación), nunca sumar la Gran Familia
entera a una sub-marca.** Esto vale para TODAS las líneas (TETRALGIN/NOVO,
BACTRIM/FORTE, DILATREND/AP/D, EMPAX/MET, ROXOLAN/PLUS, MAGNUS/36, ISIS/variantes).
**Guardrail:** `py shared/check-venta-vs-estimado.py` (flaggea %Cumpl absurdos,
> 300% o < 30%, que casi siempre son un error de granularidad/mapeo).

---

## ❌ Bug 4 — Recetas: IE / Var pp faltaban en casi todos los mercados

**Síntoma:** en la tabla multi-período de Recetas, solo unos pocos mercados
tenían IE y Var pp; el resto mostraba "—".
**Causa:** `rec_ms[fam].mkt` (mercado total) venía casi vacío — 3 meses o menos.
Sin año anterior no se puede calcular IE/Var pp. Pero `rec_comp[fam]`
(competidores) sí tiene la historia completa.
**Fix:** el renderer (`multi-period-table.js`) computa el mercado de recetas desde
`rec_comp` (suma de marcas, historia completa), usando el origen con más cobertura.
**Regla:** **el mercado de recetas se arma de `rec_comp` (la fuente completa de
competidores), no de `rec_ms.mkt` (que suele venir parcial).**

---

## ❌ Bug 5 — IE absurdo (76.188) por base del año anterior ~0

**Síntoma:** EMPAX mostraba IE = 76.188.
**Causa:** productos nuevos con base del año anterior ≈0 → el ratio de crecimiento
explota.
**Fix:** cap igual que `brandKpis`: si el SIE creció >5×, IE = "—" (no comparable).
La Var pp (cambio de share) sí se muestra.
**Regla:** **IE solo es válido con base previa significativa. Si el crecimiento
es >5×, mostrar "—", no un número.**

**Extensión (jun-2026) — Recetas, período MES con mercado incompleto:** en la tabla
multi-período de Recetas, el **último mes** suele venir con lag (faltan competidores)
→ el mercado del mes queda MENOR que el propio SIE → MS% > 100% (se vieron 8600%),
IE disparado (22.144) y Var pp imposible (+8.561 pp). **Fix:** en `multi-period-table.js`
(`computeFamily`/`computeBrand`) el período solo computa MS%/IE/Var pp si el mercado
es **completo** (`SIE ≤ mercado × 1.02`); además el IE exige mercado no-volátil
(`0.2 < mg < 5`). Si no, "—". **Regla:** **MS% nunca puede superar 100%: si pasa, el
mercado del período está incompleto → mostrar "—", no un número.**

---

## ❌ Bug 6 — Re-correr el merge revierte los splits

**Síntoma latente:** los splits MAGNUS 36 / ROXOLAN PLUS / etc. NO son parte de
`merge-ventas-internas.py`. Re-correr el merge completo los **revierte** (vuelve a
matchear la Gran Familia y pisa el split).
**Regla:** los splits de Venta Interna (MAGNUS/36, ROXOLAN/PLUS) viven en scripts
aparte (`apply-otc-magnus-split.py`, `split-cardio-roxolan.py`). **Después de
cualquier `merge-ventas-internas.py`, RE-APLICAR esos splits** (o no re-correr el
merge completo; correr la corrección de la línea puntual). Mismo patrón que los
`LOCKED_REBUILDS` de mujer.

---

## ❌ Bug 7 (histórico) — Pérdida de historia al actualizar IQVIA

**Causa:** reemplazar el time-series de `mol_perf` en vez de AGREGAR el mes nuevo.
**Regla:** los merges AGREGAN meses, nunca reemplazan. **Guardrail:**
`verify-history-preserved.py` (en el pre-commit, bloquea si se pierden meses).

---

## ❌ Bug 8 — Venta TRIP (mujer): variante solo en Presentación (col3)

**Síntoma:** "TRIP 45 está mal, sí tiene datos de venta" — TRIP 45, TRIP D3 PLUS y
TRIP MAGNESIO mostraban venta 0 en Abr/May 2026, mientras TRIP D3 estaba inflado.
**Causa:** es el bug de granularidad (col0/col1, ver Bug 3) llevado un paso más:
en la planilla SAP, **las 4 variantes de TRIP comparten Gran Familia = Familia =
Producto = 'TRIP'**; lo único que las distingue es la **Presentación (col3)**
(`TRIP +45`, `TRIP D3`, `TRIP D3 Plus`, `TRIP Magnesio`). El merge agrupa por
Familia (col1) → no puede separarlas. El mapeo tenía `'D3'→['TRIP']` (se tragaba
TODO TRIP) y `'45'/'D3 PLUS'/'MAGNESIO'→[]` (0).
**Fix:** `shared/fix-mujer-trip-venta.py` clasifica las filas de TRIP por
Presentación y setea la venta de las 4 keys. En el merge esas 4 keys quedan con
mapeo **vacío** (las saltea, no las pisa → los valores del corrector persisten).
**Regla:** cuando una Gran Familia agrupa varias marcas y **la planilla NO las
separa en col1 (Familia) sino solo en col3 (Presentación)**, hay que clasificar
por Presentación. No alcanza con matchear por Familia.
**Guardrail:** `check-venta-vs-estimado.py` ya flaggeaba los 3 TRIP con %Cumpl
bajísimo (6-15%) — esa señal (varios productos de una misma marca con cumpl muy
bajo) es pista de venta sin mapear por granularidad.

---

## ❌ Bug 9 — Stock: dos representaciones por línea, claves distintas

**Síntoma (potencial):** al agregar un mes de stock, la cobertura de algunas líneas
quedaba desalineada (arrays de `stock_alerts`/`stock_pres` más largos que los labels).
**Causa:** el stock tiene DOS vistas por línea con claves distintas:
- **chart** `stock[fam][mes]`: en data.js/SNC/dermato por familia SAP; en **mujer por
  SEGMENTO** (SIN ESTROGENO, D3…), alimentado por venta interna, NO por el pivot.
- **cobertura** (`coverage_labels` + `stock_alerts` + `stock_pres`): por nombre
  comercial. Pero el label array que se RENDERIZA varía: data.js/mujer/dermato usan
  `coverage_labels`; **SNC lo tiene HARDCODEADO** en el HTML; **dermato además tiene un
  `stock_pres_months` DECOY** que no se renderiza.
**Fix:** `merge-stock-month.py` solo toca lo que cada línea puede recibir del pivot:
`CHART_SKIP_LINES={'mujer'}` (chart segment-keyed) y
`COBERTURA_SKIP_LINES={'SNC','dermatologia'}` (labels hardcodeados/decoy).
**Regla:** **antes de escribir stock, confirmar qué clave usa el chart y qué array de
labels renderiza la cobertura de esa línea** (`const COV_LABELS = D.<algo>`). No asumir
que `stock_pres_months` es el que se muestra. Correr `--dry-run` y chequear largos.

---

## ❌ Bug 10 — Stock ATB: días corrupto (pivot) + escala histórica inflada

**Síntoma:** los "días de stock" de ATB no cuadraban — Abr 2026 mostraba **6 días** en las 6
familias con stock alto (debía ser ~25).
**Causa 1 (días):** la columna "Días de Stock" del pivot SAP vino **corrupta** para Abr 2026.
El tablero define **días = stock/ventas×30** (todos los demás meses lo cumplen exacto).
**Fix 1:** recomputado Abr 2026 en `D.stock`; y `merge-stock-month.py` ahora **SIEMPRE
recomputa** `días = round(stock/ventas×30)` en `parse_pivot` (ignora la columna del pivot) →
guardrail para que no se repita.
**Causa 2 (escala, PRE-EXISTENTE):** el histórico de stock ATB tiene stock y ventas **~10x
inflados** vs la realidad — venta interna ACANTEX ≈ 24k/mes, el pivot histórico decía ≈ 234k.
El pivot de mayo (≈ 22k, correcto) coincide con venta interna → el chart mostraba un
"acantilado" falso en may-2026. **Los días NO se afectan** (son un ratio).
**Fix 2 (jun-2026):** el factor NO era constante (ratio 2.8x→9.7x: el "ventas" histórico
era otra métrica, no ventas mensuales). Como **días es invariante a la métrica**
(`stock/ventas` del mismo origen = ratio real de cobertura), se reconstruyó con
`shared/rescale-atb-stock.py`: `ventas = D.budget[fam][YYYY].real` (venta interna real) y
`stock = round(días/30 × ventas)`, preservando los días EXACTOS. Resultado: serie suave en
unidades reales, sin acantilado; `ventas == venta interna` y `días == stock/ventas×30` (0
inconsistencias). Se escalaron también las `ventas` de `stock_alerts`/`stock_pres`.
**Regla:** si el stock viene en una métrica inconsistente, **NO escalar por un factor a ojo**;
reconstruir `stock = días/30 × venta_interna` (días es invariante; venta interna es la fuente
real de ventas que el tablero ya tiene en `budget.real`).
**Regla:** **días = stock/ventas×30 SIEMPRE** (no confiar en la columna del pivot). Al
agregar un mes de stock, **cruzar el stock/ventas absoluto contra la venta interna** para
detectar saltos de unidad/escala.

---

## ✅ Reglas de oro (resumen)

1. **`?v=<hash>` siempre fresco** — automático (build-all + pre-commit). Nunca
   editar data.js sin que el `?v` se actualice. Verificar: `bump-cache-busters.py --check`.
2. **Una familia mol_perf = un mercado de la fuente (una molécula).** No fusionar.
3. **Planilla SAP: matchear por Familia (col1), no por Gran Familia (col0).**
4. **Mercado de recetas = suma de `rec_comp` (historia completa), no `rec_ms.mkt`.**
5. **IE con base previa <20% del actual o crecimiento >5× → "—" (no comparable).**
6. **Splits de Venta Interna se RE-APLICAN después de cada merge.**
7. **Los merges AGREGAN meses, nunca reemplazan** (lo bloquea el guardian).
8. **El estimado ("Estimado de Ventas") nunca se llama "Presupuesto"** (ver CLAUDE.md).

## Antes de pushear un corte, correr SIEMPRE:
```
py shared/recompute-mol-perf-aggregates.py
py shared/build-kpis.py && py shared/build-families-perf.py
py shared/sync-kpistrip-with-kpis-json.py
py shared/bump-cache-busters.py
py shared/check-mercados-fuente.py        # familias que mezclan mercados
py shared/check-venta-vs-estimado.py      # %Cumpl absurdos
py shared/audit-full.py                   # DEBE dar 0 FAIL
```
(El pre-commit hook corre syntax + history + audit + cache-buster automáticamente.)
