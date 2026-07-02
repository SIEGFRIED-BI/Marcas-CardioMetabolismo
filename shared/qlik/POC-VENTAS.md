# PoC Venta interna — receta validada (F1)

_2026-07-02 · fuente: app **Siegfried Ventas** (`aa911794-e7fc-4002-8a3a-1a57a5751a2c`), tenant `tableros.us`._

## Resultado
Al nivel de **budget keys del tablero** (las familias que terminan en `data.js`):
**77/77 familias × 12 meses cerrados (Jun-2025..May-2026) = 924/924 celdas idénticas** al archivo manual
`Planilla de Ventas - 2 de junio de 2026.xlsx`. Jun-2026 difiere solo porque el manual era parcial
(exportado el día 2) y Qlik ya tiene el mes completo → lo resuelve el `--cutoff` del merge.

## Receta de extracción
- **Filtro CLAVE (selección oculta del export manual):** `Descripcion_Organizacion_Venta = 'Rofina'`.
  Excluye Roemmers y exportaciones ("Exp", "MM", "VL"). Verificado: ACEMUK Jun-2025 Rofina = 567.976 =
  valor exacto del manual (sin filtro daba 1.336.303 = 2,3×).
- **Grano:** `gran_familia` + `familia` (para réplica fiel del archivo agregar `producto` + `CodigoProducto`).
- **Medida:** `sum(venta_un)` (idéntica a `venta_un_conv` y `venta_un_conv2` en este dato).
- **Tiempo:** dimensión `AñoMes` (formato `"Jun-2025"`). El calendario llega a Dic-2031 con meses
  futuros vacíos → **eso explica los labels "Año 2030/2031"** vistos en otras apps (no es error de datos).

## Cómo se extrae (session-hypercube, @qlik/api)
1. `selectValues` en `Año` = {2024,2025,2026} y en `Descripcion_Organizacion_Venta` = {Rofina}.
2. `createSessionObject` con `qHyperCubeDef`: dims [gran_familia, familia, producto, CodigoProducto,
   AñoMes] + measure `sum(venta_un)`, `qSuppressZero:true`.
3. `getHyperCubeData` paginado (10k celdas/pág; ~114k filas → ~72 págs de 1600).
4. Pivotar a ancho (una fila por SKU, una columna por mes) → xlsx con el layout de la Planilla
   (`Gran Familia | Familia | Producto | Presentación | Cód | Jun-2025 | … `).

Script PoC: `scratchpad/qlik-node/extract-ventas.mjs` (extrae a JSON) + comparación en Python.

## Lección general (aplica a TODA fuente)
Cada export manual lleva **selecciones ocultas** que no están en ninguna medida del app y hay que
descubrir por fuente (acá: `Rofina`). El método: extraer sin filtro, comparar contra el archivo real,
y desglosar por campos candidatos (CondicionVenta, Organización de Venta, línea de negocio) hasta que
un subconjunto dé el valor exacto. Sin esto, los números salen inflados (exportaciones/otros canales).

## Uso (producción) — scripts en este directorio
```
# 1) instalar dependencia (una vez):  npm install --prefix shared/qlik
# 2) key: definir env QLIK_API_KEY  (o crear shared/qlik/.qlik-key.txt, gitignored)
node shared/qlik/extract-ventas.mjs  <ruta>/ventas_qlik.json      # extrae Rofina (todo el historial)
py   shared/qlik/qlik-ventas-to-planilla.py  <ruta>/ventas_qlik.json  "<_inbox>/Planilla de Ventas (Qlik).xlsx"
py   shared/merge-ventas-internas.py --file "<...>/Planilla de Ventas (Qlik).xlsx" --cutoff <closeMonth>
```
- **Ventana temporal:** el filtro por año NO se aplica en el engine (el `selectValues` sobre `Año`/`AñoMes`
  no matchea por la ñ; el filtro Rofina —ASCII— sí). Se ventanea en el pivot (últimos ~3 años; los labels
  `Jun-2025` son ASCII). Extrae todo Rofina (~114k filas, ~90s) — OK para 2×/mes. TODO opcional: filtrar
  año en el engine por código de campo para achicar la transferencia.

## Verificación drop-in (2026-07-02)
Generada la planilla desde Qlik (Rofina, Jun-2025..Jun-2026) y corrido `merge-ventas-internas.py --cutoff
2026-05`: **cardio / ATB / respiratorio quedaron byte-idénticos** al `data.js` actual (git diff vacío);
**OTC** difirió solo en 7 celdas de MAGNUS = porque el test no corrió `apply-otc-magnus-split.py` (paso
posterior del cascade que separa MAGNUS 36). Total Rofina Jun-2025 = 2.156.607 = "Totales" del manual exacto.

## Pendiente (pre-existente, NO de Qlik) — verificar aparte
`merge-ventas-internas.py` **falla en SNC/mujer/dermatologia** con "OTC_DATA not found" (esas 3 líneas ya
no emiten `window.OTC_DATA` tras la limpieza F5). El error es al LEER su data.js, independiente del archivo
de entrada → **la venta interna de esas 3 líneas puede no estar actualizándose por esta vía**. Revisar si
tienen otro camino o quedó un bug latente.

## Para F3 (scheduling 2×/mes)
Agregar a `update-all.ps1` un paso previo que corra extract+pivot → `_inbox/<closeMonth>/`, y mover la key a
env/Windows Credential Manager (no scratchpad). El resto del pipeline no cambia.
