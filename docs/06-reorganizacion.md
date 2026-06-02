# 06 · Reorganización futura (blueprint OPCIONAL)

> ⚠️ **Nada de esto está aplicado ni se aplica ahora.** Es un plano para cuando
> tengas tiempo y ganas de prolijear. El proyecto HOY funciona; estos cambios son
> mejoras de orden, no arreglos. Cada uno tiene su riesgo anotado.

---

## 1. Unificar la arquitectura de datos (data.js vs inline)

**Hoy:** 4 líneas usan `data.js` externo (`window.OTC_DASHBOARD`), 3 lo tienen
inline (`const D`) dentro del HTML. El mismo schema, dos lugares.

**Propuesta:** mover mujer/SNC/dermatologia a `data.js` externo también
(`<linea>/data.js` + `<script src>` en el HTML).

**Pros:** un solo patrón; HTML chico y diffeable; `git blame` útil; los scripts
`sync-*` y los patchers dejan de hacer cirugía de regex dentro del HTML.

**Contras / riesgo:** ALTO. Hay que reescribir los `sync-mujer/snc/dermato-pm.py`,
los `merge-recetas-*` inline, el `_restore-snc-budget-chart.py`, y todos los
patchers que buscan `const D = {` por regex. Si se hace, hacerlo **una línea a la
vez**, con `audit-full.py` verde antes y después de cada una.

**Veredicto:** alto valor de orden, alto costo. Solo si vas a tocar mucho esas líneas.

---

## 2. Subcarpetas en `shared/` por categoría

**Hoy:** 97 archivos planos en `shared/`. Difícil de escanear (lo resuelve `05-scripts.md`).

**Propuesta de layout:**
```
shared/
├── build/      (build-*.py, build-*.ps1)
├── sync/       (sync-*.py, slice-iqvia-master.py)
├── merge/      (merge-*.py)
├── rebuild/    (rebuild-*.py, recompute-*.py)
├── patch/      (patch-*.py)
├── fix/        (fix-*.py)
├── audit/      (audit-*.py, check-*.py, verify-*.py)
├── inject/     (inject-*.py, apply-*.py, add-*.py)
├── cleanup/    (consolidate/dedup/trim/remove/rename/redesign/unify/_restore)
├── ddd/        (update-ddd-*.py, build-competidores-*.py)
└── lib/        (multi-period-table.js/.css, design-tokens.css, ux-shared.js, export-*.js, *.json)
```

**⚠️ Por qué NO conviene hoy:** mover los archivos **rompe**:
- El **pre-commit hook** (`.git/hooks/pre-commit`) llama `py shared/check-…`,
  `py shared/verify-…`, `py shared/audit-full.py` por path fijo.
- Las páginas cargan `../shared/multi-period-table.js`, `../shared/design-tokens.css`,
  etc. por path relativo fijo. Mover los `.js`/`.css` rompe las 21 páginas.
- `build-all.ps1` y `sync-mujer-pm.py` invocan otros scripts por path
  (`shared/<x>.py`).

**Si igual se hace:** mover, y en el mismo commit actualizar (a) el pre-commit hook,
(b) todos los `<link>`/`<script src>` de las 21 páginas (con un patcher), (c) los
paths internos de `build-all.ps1` y el `LOCKED_REBUILDS` de `sync-mujer-pm.py`.
Es factible pero es un commit grande y delicado. Dejarlo documentado, no urgente.

**Alternativa de bajo riesgo (recomendada):** NO mover nada; usar `05-scripts.md`
como índice. Ya resuelve el 90% del dolor sin riesgo cero.

---

## 3. Alinear `Hub-Marcas-Inputs/` con su propio README

El `README.txt` de inputs define una estructura ideal por línea/mes
(`dashboard / ddd / fuentes-originales / notas-corte`) que hoy está solo
parcialmente realizada ("OTC ya tiene generador… el resto todavía necesita
proceso"). Propuesta: completar esa estructura para las 7 líneas, así cada mes
se sabe exactamente dónde va cada Excel. **Riesgo: cero** (es OneDrive, no toca
el repo). **Valor: alto** para que dejen de aparecer "carpetas vacías".

---

## 4. Manifest `data-sources.json` (semilla para automatizar el mapa)

Hoy la relación fuente↔script↔output está en la cabeza + en estos docs. Un
archivo declarativo la haría verificable por código:
```jsonc
// docs/data-sources.json (futuro)
{
  "mol_perf": {
    "source": "_iqvia-master/YYYY-MM/AR_PM_FV_Standard_*.xlsx",
    "scripts": ["sync-mujer-pm.py","sync-snc-pm.py","sync-dermato-pm.py","build-data.ps1"],
    "outputs": ["<linea>/data.js#mol_perf","<linea>/index.html#const D.mol_perf"],
    "verify": "audit-full.py#4"
  },
  "budget.real": { "source":"Planilla de Ventas - *.xlsx", "scripts":["merge-ventas-internas.py"], … }
}
```
Con eso, `00-MAPA.html` podría leerlo y dibujarse solo (en vez de tener el mapa
hardcodeado), y un script podría chequear que cada output declarado existe.
**Riesgo: cero** (archivo nuevo en docs/). **Valor: alto** a largo plazo.

---

## 5. Limpieza de archivos legacy (a confirmar antes de borrar)

Candidatos a revisar (NO borrar sin verificar que no se usan):
- `mujer/data.js` (¿legacy? mujer usa inline `const D`).
- `mujer/market-overrides.js`, `mujer/price-ddd-overrides.js`, `mujer/runtime-market-overrides.js`.
- `<linea>/runtime-overrides.js`.
- `dermatologia/index.html` (473 bytes — ¿stub/redirect?).
- `SNC/psq_dashboard.html` (305 bytes — ¿stub?).

**Método seguro:** `grep` del nombre en todo el repo; si nadie lo referencia,
moverlo a un `_legacy/` (no borrar) y verificar que el tablero sigue OK + `audit-full.py` verde.

---

## Orden sugerido (de menos a más riesgo)

| # | Mejora | Riesgo | Valor | Cuándo |
|---|---|:-:|:-:|---|
| 3 | Completar estructura de `Hub-Marcas-Inputs/` | cero | alto | ya |
| 4 | `data-sources.json` declarativo | cero | alto | cuando puedas |
| 5 | Auditar/mover legacy a `_legacy/` | bajo | medio | cuando puedas |
| 2 | Subcarpetas en `shared/` | alto | medio | solo con tiempo |
| 1 | Unificar arquitectura de datos | alto | alto | solo si tocás mucho mujer/SNC/derma |

**Regla:** una mejora por commit, con `audit-full.py` verde antes y después.
