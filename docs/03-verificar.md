# 03 · Verificar — cómo saber que los datos están bien

> El objetivo de este doc: que chequear un número sea **un comando**, y que
> entiendas qué significa cada check si algo falla.

---

## El comando único

```
py shared/audit-full.py
```
Revisa TODAS las marcas de TODAS las líneas en TODAS las métricas (IE, MS%,
unidades, crecimiento, recetas, stock) en TODOS los períodos. Termina con:

```
TOTAL CHECKS: 22642  PASS: 22642  FAIL: 0
```

**`FAIL: 0` = todo consistente.** Cualquier número distinto de 0 lista exactamente
qué marca × métrica × período no cierra.

---

## Los 8 checks que corre `audit-full.py`

| # | Check | Qué valida |
|---|---|---|
| 1 | **LINE-LEVEL** | hub `kpis.json` == `kpiStrip` de cada tablero (los números del hub y del strip coinciden) |
| 2 | **BRAND-LEVEL** | `brandKpis` == lo que se recomputa desde `mol_perf` (IE/MS/unidades por marca) |
| 3 | **RECETAS** | 5 chequeos internos de coherencia de recetas |
| 4 | **MOL_PERF** | `monthly_vals` → `ytd` / `mat` / `quarterly` cierran (los agregados = suma de los meses) |
| 5 | **STOCK** | shape correcto + valores no-negativos |
| 6 | **CONVENIOS** | los % suman 100 por OS |
| 7 | **KPI STRIP MARKET** | `mkt_ytd26`/`mkt_mat26` == suma de `mol_perf` YTD/MAT |
| 8 | **BUDGET** | estructura correcta (12 meses por año) |

Tolerancia: 0.5pp para porcentajes, 0.1% para conteos.

---

## Los otros 2 verificadores (los corre el pre-commit hook)

```
py shared/check-syntax-and-consistency.py
```
Sintaxis + antipatrones en los HTML/JS de las 7 líneas. Detecta: `const`/`window`
duplicados, JSON inline imparseables, índices hardcodeados (`Array(12).fill`,
`tm[11]`, `'DIC 2025'`), y nav desbalanceado. Termina `OK: 21 HTML + 6 JS … sin issues`.

```
py shared/verify-history-preserved.py --baseline HEAD --strict
```
Compara contra un commit de referencia y **bloquea si se perdieron meses** de
`mol_perf`. Esto evita el error clásico de "reemplacé el time-series en vez de
agregar el mes nuevo".

---

## El pre-commit hook (red de seguridad automática)

Está en `.git/hooks/pre-commit`. En cada commit que toque `*.html`/`*.js`/`data.js`
corre, en orden:

1. `check-syntax-and-consistency.py` → bloquea si hay error de sintaxis/antipatrón.
2. `verify-history-preserved.py --baseline HEAD --strict` → bloquea si se pierde historia.
3. `audit-full.py` → bloquea si hay inconsistencia de datos.

> **Nunca** uses `git commit --no-verify`. Si el hook bloquea, hay un problema real.

---

## Verificación manual (spot-check de un número puntual)

Ejemplo: querés confirmar el **MS% MAT** de un mercado en cardio.

1. Abrí `cardio/data.js`, buscá `"mol_perf"` → la familia (ej. `"DAURAN"`).
2. La familia tiene `mat: { "Apr 2026": <mercado_total> }` = suma de los `mat`
   de todos sus `products[]`.
3. Cada producto SIE tiene `ms_mat: { "Apr 2026": <share%> }` =
   `producto.mat["Apr 2026"] / familia.mat["Apr 2026"] × 100`.
4. Cruzá contra `kpis.json` → `lines[<cardio>].kpis.mat.ms_units.curr`.
5. Cruzá contra la pestaña Mercado IQVIA del tablero (tabla multi-período, col MS% MAT).

Si los 3 lugares coinciden → el dato está bien. (El check #1, #2 y #7 del audit
hacen exactamente este cruce automáticamente para todas las marcas.)

**Fórmula del IE para verificar a mano:**
```
IE = (SIE_curr / SIE_prev) / (Mercado_curr / Mercado_prev) × 100
```
IE > 100 = SIE ganó share (creció más que el mercado). IE < 100 = perdió share.

---

## Qué hacer si el audit falla

La causa más común es que `brandKpis` / `kpiStrip` quedaron desfasados de `mol_perf`
después de un merge. La cadena de fix:

```
py shared/fix-brandkpis-from-molperf.py    # recomputa brandKpis desde mol_perf (fuente única)
py shared/build-kpis.py                     # regenera kpis.json
py shared/sync-kpistrip-with-kpis-json.py   # alinea el strip de cada tablero
py shared/audit-full.py                     # re-verificar → debe dar 0 FAIL
```

Si el problema es de agregados internos de `mol_perf` (check #4):
```
py shared/recompute-mol-perf-aggregates.py  # rehace quarterly/ytd/mat/ms_* desde monthly_vals
```

---

## Chequeo del propio entregable `docs/`

Esta carpeta es **solo documentación**: no cambia el comportamiento. Para confirmar
que no rompió nada:
```
git status                              # debe mostrar SOLO archivos nuevos bajo docs/
py shared/check-syntax-and-consistency.py   # idéntico a antes
py shared/audit-full.py                     # idéntico a antes (0 FAIL)
```
