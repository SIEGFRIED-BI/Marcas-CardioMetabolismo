# PoC Recetas — receta validada (F2)

_2026-07-02 · fuente: app **Tablero Recetas Siegfried (CUP)** (`11a25fee-9c18-4028-9698-c03b29d91725`), tenant `tableros.us`._

## Receta de extracción (validada)
- **Filtro 1 — `Fichado = 'SI'`** (recetas fichadas/auditadas). Es el "filtro oculto" del export manual,
  análogo a "Rofina" en Venta. Validado: ACEMUK SIE Abr-2026 con Fichado=SI = **21.325** vs archivo **21.319**.
- **Filtro 2 — `Flag_Rollback = {0}`** (excluye datos preliminares/rollback).
- **Dim de mercado — `Mercado (sin Mix)`** = dimensión maestra calculada:
  `=if(not wildmatch(Mercado,'*MIX*'), Mercado, NULL())` (excluye pseudo-mercados MIX que duplican recetas).
- **Grano:** Mercado(sin Mix) · Droga · Marca (+ AñoMes, formato "Abr-2026").
- **Medidas:** Cant. Recetas = `sum(Cantidad)` ; Cant. Médicos = `count(distinct CodigoMedicoUnico)`.

## Verificación (2026-07-02)
Extraído Abr-2026 con la receta y comparado contra `Sin título - Tabla dinámica - 3 de junio de 2026 (1).xlsx`:
**58,7% de las hojas exactas (±2); el resto difiere solo ±2-5% en AMBAS direcciones** = revisión de datos de
CloseUp entre el archivo (3-jun) y el reload del app (2-jul). Un error de receta daría diffs sistemáticos en
una sola dirección; acá son bidireccionales y chicos → la receta es correcta, es dato más fresco.

## Ojos / nuances (importantes)
- **Médicos es un DISTINCT count** → NO se puede sumar entre mercados/meses. Respetar el grano; si se agrega,
  recomputar el distinct (o extraer al grano requerido).
- **Lag ~2 meses:** el último mes de recetas es ~2 meses atrás (un archivo de junio trae Abr-2026).
- **Mercados trackeados:** el archivo del tablero está acotado a los ~72 mercados de CloseUp que definís por
  marca ("ARA II (DIOV-ENTR-EXFO)", "ANTICONCEPTIVOS ORALES (ISIS)", ...). Es **config de negocio**: el
  extractor trae todos los mercados sin-Mix; el consumidor/manifest decide cuáles usar (mantener la lista).
- Calendario del app llega a 2031 con meses vacíos (igual que Ventas) — no es bug.

## Validación a fondo (multi-mes, 2026-07-02)
- **Fix necesario:** el app abre con una **selección por defecto al último mes** → hay que `app.clearAll()`
  antes de armar el cubo (ya está en extract-recetas.mjs), si no trae 1 solo mes. Con clearAll: 24 meses, 33.716 filas.
- Comparado vs `ATB/recetas.xlsx` (24 meses, Mar-2024..Feb-2026): **82-97% de las celdas dentro de ±3% por mes**
  (avg ~88%), incluso meses de 2 años atrás. El residuo es **revisión de CloseUp** (el dato se corrige con el
  tiempo). **Recetas NO se reproduce byte-a-byte contra archivos viejos** (a diferencia de Venta, que dio 924/924
  exacto) — es propio del dato, no de la receta. Ancla de correctitud: ACEMUK Abr-2026 = 21.325 vs 21.319.

## Script + pendiente
- `shared/qlik/extract-recetas.mjs` (extrae a JSON; query idéntica a la validada).
- **Pendiente para cerrar end-to-end:** un pivot al shape exacto que espera el build (analizar cómo
  `build-data.ps1` parsea recetas/rec_ms/rec_comp — el archivo trae Mercado|Droga|Marca|Cant.Recetas|Cant.Médicos
  por mes) y wiring en update-all → _inbox. Mecánico, análogo a `qlik-ventas-to-planilla.py`.
