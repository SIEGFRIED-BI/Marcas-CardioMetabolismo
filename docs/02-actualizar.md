# 02 · Actualizar — runbook mensual

> Qué correr cada mes, en qué orden, qué archivo toca cada paso y cómo confirmar
> que salió bien. Todos los comandos se corren desde la raíz del repo
> (`C:\Users\camarinaro\Marcas-CardioMetabolismo`).
>
> **Antes de empezar:** las fuentes Excel van en OneDrive →
> `…\Documentos\Hub-Marcas-Inputs\`. El repo solo guarda los resultados.

---

## TL;DR — el flujo feliz de un mes nuevo

```
1. Dejar el IQVIA master del mes en   Hub-Marcas-Inputs/_iqvia-master/YYYY-MM/
2. (mujer) py shared/slice-iqvia-master.py        # recorta el master de 18MB
3. Generar/sincronizar mol_perf por línea:
      - cardio/ATB/OTC/respi:  pwsh shared/build-all.ps1 -Month YYYY-MM -Lines cardio,ATB,OTC,respiratorio
      - mujer:   py shared/sync-mujer-pm.py        # (corre solo sus rebuilds fijos)
      - SNC:     py shared/sync-snc-pm.py
      - derma:   py shared/sync-dermato-pm.py
4. Venta Interna (SAP):    py shared/merge-ventas-internas.py <planilla.xlsx>
5. Estimado de Ventas:     pwsh shared/build-budget-overrides.ps1   (si cambió)
6. Recetas (CloseUp):      py shared/merge-recetas-*.py <pivot.xlsx>
7. Stock:                  py shared/merge-stock.py <pivot SAP.xlsx>
8. Recalcular agregados:   py shared/recompute-mol-perf-aggregates.py
9. Reconstruir KPIs:       py shared/build-kpis.py && py shared/build-families-perf.py
10. Sincronizar strip:     py shared/sync-kpistrip-with-kpis-json.py
11. VERIFICAR:             py shared/audit-full.py        (debe dar 0 FAIL)
12. Commit + push:         git add -A && git commit && git push   (Cloudflare redeploya)
```

> El pre-commit hook corre **syntax + history + audit** automáticamente en el
> paso 12. Si falla, NO uses `--no-verify` — arreglá la causa (ver `03-verificar.md`).

---

## Dato MANUAL aparte · Comparativa de Precios (línea mujer)

La sección **"Precios mercado" / Comparativa de Precios** de mujer **no** viene de
IQVIA: es un **snapshot manual** del Excel `Comparativa de PRECIOS_DD.MM.AAAA.xlsx`
(precio público y por unidad de cada presentación SIE vs sus competidores, con el
% de diferencia).

Hay **dos formas** de refrescarlo según qué Excel tengas:

**(a) Solo actualizar precios** (lo más común). Llega el catálogo plano del Manual
(una hoja: `Producto | Presentación | Droga | Laboratorio | Troquel | Q Pres | PVP
al DD/MM | …`, p.ej. `Sin título - Tabla - <fecha>.xlsx`). Mantiene la MISMA
estructura curada (mismos competidores) y solo refresca los precios, matcheando por
**Troquel**, y recalcula $/unidad y % gap:
```
py shared/parse-comparativa-precios.py "<comparativa curada por marca.xlsx>" \
    --prices "<catalogo plano con PVP.xlsx>" --fecha DD/MM/AAAA
```
(Toma la columna `PVP al ...` más a la derecha = la más reciente.)

**(b) Reconstruir la estructura** desde una comparativa nueva ya organizada por
marca (`Comparativa de PRECIOS_DD.MM.AAAA.xlsx`, una hoja por marca con bloques):
```
py shared/parse-comparativa-precios.py "<comparativa.xlsx>"
```

Después, siempre:
```
py shared/audit-full.py        # debe dar 0 FAIL
git add -A && git commit && git push
```

- Solo procesa las hojas/marcas de mujer (Isis, Trip, Gynoderm, Siderblut, Climatix,
  Deltox, Calcio Base); el resto del Excel se ignora.
- Inyecta `prec_comp` + `prec_comp_meta` en `mujer/index.html` (idempotente:
  reemplaza la inyección anterior, no duplica). Cada fila guarda su `troq` (Troquel)
  para poder rematchear precios en el futuro.
- La **fecha del snapshot** sale de `--fecha` (o del nombre del archivo, DD.MM.AAAA)
  y se muestra en la sección ("al DD/MM/AAAA").

> Es el **único** dato del tablero que no se actualiza solo. Si nadie corre el
> parser, la comparativa queda con la fecha vieja — por eso la fecha va siempre
> visible. Detalle de claves en `04-diccionario.md` (`prec_comp`).

---

## Paso a paso por tipo de dato

### A) IQVIA (Mercado) — el corazón, define `mol_perf`

**Fuente:** `Hub-Marcas-Inputs/_iqvia-master/YYYY-MM/AR_PM_FV_Standard_*.xlsx`
**Columnas del Excel:** col 0 `Manufacturer` · col 1 `Product` · col 2 `ATC IV` ·
col 3 `Molecules Long` · luego ~155 columnas mensuales con header `Units\nMMM YYYY`
(de May 2021 al último mes). El alterno es `Ateneo Total - MAT Movil_*.xlsx`.

**Líneas con archivo separado (cardio/ATB/OTC/respiratorio):**
```
pwsh shared/build-all.ps1 -Month 2026-05 -Lines cardio,ATB,OTC,respiratorio
```
Parámetros útiles: `-IqviaSubfolder _iqvia-master` (default), `-IqviaPattern` (glob),
`-DryRun` (no escribe), `-CommitPush` (hace add+commit+push de los `data.js`).
Regenera cada `<linea>/data.js`.

**Líneas inline (mujer/SNC/dermatologia):** se sincronizan con su `sync-*-pm.py`,
que **respeta la segmentación existente** y solo reemplaza el time-series:
```
py shared/slice-iqvia-master.py     # solo mujer necesita el recorte previo
py shared/sync-mujer-pm.py          # familias: SIN ESTROGENO, ALTA DOSIS, …, CLIMATIX
py shared/sync-snc-pm.py            # segmentado por molécula
py shared/sync-dermato-pm.py        # segmentado por molécula
```

> **Mercados con composición fija (locked):** `sync-mujer-pm.py` al final corre
> automáticamente los rebuilds de mercados definidos a mano (lista
> `LOCKED_REBUILDS`). Hoy: **mujer `45`** (`rebuild-mujer-45-market.py`: TRIP +45
> vs solo VIASEK MENOCARE CAPS oral). En respiratorio, **ACEMUK** usa
> `rebuild-acemuk-atc-r05c0.py` (todos los R05C0). Si agregás un mercado fijo
> nuevo: creá `rebuild-<linea>-<mercado>-market.py` y agregalo a `LOCKED_REBUILDS`.

**Confirmar:** abrí el tablero → Mercado IQVIA → el último mes debe ser el nuevo;
o `py shared/recompute-mol-perf-aggregates.py --dry-run` muestra el cierre detectado.

---

### B) Venta Interna (SAP) — define `budget[fam][año].real`

**Fuente:** `Planilla de Ventas - <fecha>.xlsx` (formato: `Familia | Ene-YYYY | … | Dic-YYYY+1`).
```
py shared/merge-ventas-internas.py <ruta a la planilla.xlsx>
```
Actualiza `budget[fam].YYYY.real[]` en todas las líneas. Preserva el resto.

> **mujer · TRIP — paso obligatorio aparte.** Los productos TRIP (D3, D3 PLUS,
> +45, MAGNESIO) comparten Gran Familia=Familia='TRIP' en la planilla; solo se
> distinguen por **Presentación**, así que el merge NO puede separarlos (van con
> mapeo vacío). Después del merge, correr:
> ```
> py shared/fix-mujer-trip-venta.py "<ruta a la planilla.xlsx>" --cutoff YYYY-MM
> ```
> Clasifica por Presentación y setea la venta de esas 4 keys. (Mismo patrón que
> los splits: se re-aplica tras cada merge. Como el merge las saltea, en la
> práctica solo hace falta re-correrlo cuando llega una planilla nueva.)

---

### C) Estimado de Ventas — define `budget[fam][año].budget` (vía overrides)

**Fuente:** `Hub-Marcas-Inputs/Estimados VENTA vigentes MKT sidus.xlsx`.
```
pwsh shared/build-budget-overrides.ps1
```
Regenera `shared/budget-overrides.js` (objeto `OVERRIDES[linea][producto] = [12 meses]`),
que las líneas aplican en runtime sobre la barra de Venta Interna.
Solo hay que correrlo **cuando cambia el estimado**, no todos los meses.

---

### D) Recetas (CloseUp) — define `recetas`, `rec_ms`, `rec_comp`

**Fuente:** pivot CloseUp (`Sin titulo - Tabla dinamica - <fecha>.xlsx`), columnas
`[Mercado, Droga, Marca, AñoMes, Cant. Recetas, Cant. Medicos]`. **Lag ~1 mes** vs IQVIA.

Hay un merge por familia de líneas (difieren por shape):
```
py shared/merge-recetas-march.py <pivot.xlsx>        # cardio/ATB/OTC/respi (data.js)
py shared/merge-recetas-respi.py <pivot.xlsx>        # respiratorio (10 mercados)
py shared/merge-recetas-snc.py <pivot.xlsx>          # SNC (inline const D)
py shared/merge-recetas-mujer-march.py <pivot.xlsx>  # mujer (inline)
```
**Confirmar:** tablero → Recetas → la tabla multi-período debe traer el mes nuevo
con MS%/IE/Var pp calculados.

---

### E) Stock / Cobertura — define `stock`, `stock_pres`, `stock_alerts`

**Fuente:** pivot SAP `Laboratorio - Familia - Producto - <fecha>.xlsx` (Laboratorio,
Familia, Producto + por mes: Stock final, Ventas, Facturación, Días de Stock).

**Recomendado — actualización mensual COMPLETA (todas las líneas):**
```
py shared/merge-stock-month.py --pivot "<pivot.xlsx>" [--dry-run]
```
Deriva el mes nuevo del pivot y, por línea, actualiza:
- **chart** `stock[fam][mes]` y **cobertura** (`coverage_labels` + `stock_alerts` +
  `stock_pres`) en cardio/ATB/OTC/respiratorio.
- **mujer:** solo cobertura. Su chart está keyeado por SEGMENTOS (lo alimenta venta
  interna, no el pivot) → `CHART_SKIP_LINES`.
- **SNC / dermatologia:** solo chart. Su cobertura usa labels hardcodeados (SNC) o un
  array decoy `stock_pres_months` que NO es el que renderiza (dermato usa
  `coverage_labels`) → `COBERTURA_SKIP_LINES`. (Si hay que actualizar esa cobertura,
  es a mano; ojo de no desalinear largos de arrays.)

Correr siempre `--dry-run` primero. `merge-stock.py` (incremental, solo chart de las
4 data.js) queda como alternativa mínima.

> **Por qué tanto skip:** el stock tiene DOS representaciones por línea (chart por
> familia vs cobertura por presentación) con claves distintas; mezclarlas rompe la
> alineación de los arrays de cobertura. Ver `07-lecciones` (Bug 9).

---

### F) Precios — define `precios`, `prec_iqvia`

**Fuente:** dump del Manual Farmacéutico (`Producto, Presentacion, Droga, PVP …`).
```
py shared/merge-precios.py <dump.xlsx>          # cardio/ATB/OTC/respi (precios[FAM].molecule[pres])
py shared/update-dermato-precios.py <dump.xlsx> # dermato (precios[FAM][pres], shape flat)
```

---

### G) Convenios — define `convenios`, `canales`, `canales_quarterly`

**Fuente:** `Hub-Marcas-Inputs/convenios NUEVO/<trimestre>.xlsx`.
Se ingieren con el `build-data.ps1` de cada línea; `dedup-convenios.py` limpia OS duplicadas
y `patch-canales-quarterly.py` arma la tabla trimestral.

---

### H) Competidores DDD (heatmap regional) — define `competidores-data.js`

**Fuente:** `Producto-Molécula-ATC-provincia - <fecha>.xlsx`
(`RegionCUP, Mercado, Producto, AñoMes, Unidades, Codigo Clase Terapeutica`).
```
py shared/build-competidores-shape-a.py <xlsx>        # genérico por línea
py shared/build-mujer-competidores-data.py            # mujer
py shared/update-ddd-from-competidores.py             # vuelca a DDD/index.html
py shared/update-ddd-otcdata-from-competidores.py     # ATB/OTC/respiratorio
py shared/update-ddd-mujer-from-competidores.py       # mujer/DDD/data.js
```

---

## Cierre: reconstruir derivados + publicar

```
py shared/recompute-mol-perf-aggregates.py     # quarterly/ytd/mat/ms_* desde monthly_vals
py shared/build-kpis.py                         # → kpis.json (hub, Por Línea/Producto)
py shared/build-families-perf.py                # → kpis-families.json (hub, Por Marca)
py shared/sync-kpistrip-with-kpis-json.py       # alinea el strip de cada tablero con kpis.json
py shared/bump-cache-busters.py                 # ?v=<hash> en data.js/assets (anti-cache viejo)
py shared/audit-full.py                         # DEBE dar 0 FAIL (ver 03-verificar.md)
git add -A && git commit -m "Actualización corte YYYY-MM" && git push origin main
```
Cloudflare Pages redeploya solo al pushear a `main` (~1-2 min).

> **Cache-buster (importante):** cada `<linea>/index.html` carga `data.js?v=<hash>`
> y los assets `shared/*.js|css?v=<hash>`. El `?v` se deriva del **hash del
> contenido** vía `bump-cache-busters.py`. Si cambia data.js pero NO se bumpea el
> `?v`, el navegador/CDN sirve la **versión vieja cacheada** (bug real que pasó en
> jun-2026). Por eso:
> - `build-all.ps1` ya corre `bump-cache-busters.py` al final (automático).
> - El **pre-commit hook** también lo corre y re-stagea (red de seguridad).
> - El hook vive en `.git/hooks/pre-commit` (no se versiona). Copia de respaldo:
>   `shared/git-pre-commit.sh`. Si reclonás el repo, reinstalalo:
>   `cp shared/git-pre-commit.sh .git/hooks/pre-commit`
> - Verificar a mano: `py shared/bump-cache-busters.py --check` (0 = al día).

---

## Si el audit falla en el cierre

Cadena de corrección estándar:
```
py shared/fix-brandkpis-from-molperf.py   # recomputa brandKpis IE/MS desde mol_perf (fuente única)
py shared/build-kpis.py
py shared/sync-kpistrip-with-kpis-json.py
py shared/audit-full.py                    # re-verificar
```
Más detalle de cada check → `03-verificar.md`.

---

## Notas importantes

- **Nunca** edites un número a mano en `data.js` / `const D`. Corré el script.
- **Nunca** reemplaces todo el time-series: los merges **agregan** meses. Para
  agregar un único mes preservando historia está `merge-april-2026-only.py` como
  patrón de referencia. El hook `verify-history-preserved.py` bloquea si se pierde historia.
- `pwsh` = PowerShell 7. Los `.ps1` corren ahí; los `.py` con `py` (Python).
- El estado de qué línea tiene generador automático vs sync manual está en
  `Hub-Marcas-Inputs/README.txt`.
