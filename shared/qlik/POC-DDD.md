# PoC DDD + Competidores — receta validada (F2)

_2026-07-02 · fuente: app **Siegfried DDD** (`a3a4907d-9340-46d0-93c4-f2ce7f004ff0`), tenant `tableros.us`._

## Un solo extracto alimenta DDD **y** Competidores
La fuente única es el archivo **`Producto-Molécula-ATC-provincia`** (IQVIA/IMS por región). De ahí:
- `shared/build-competidores-shape-a.py` → `<linea>/DDD/competidores-data.js` (window.SFG_COMP_DATA),
  agrupando HÍBRIDO por molécula/ATC y quedándose con mercados que tienen marca SIE.
- Los scripts `rebuild-ddd-inline-from-competidores.py` / `update-ddd-*from-competidores.py` reconstruyen
  las páginas DDD desde ese competidores-data.js. **Actualizar el extracto actualiza las DOS pestañas.**

## Shape objetivo (columnas del archivo)
`RegionCUP · Mercado · Droga · Clase Terapeutica · AñoMes · Codigo Clase Terapeutica · Codigo Producto · Producto · Unidades`

## Mapeo de campos (validado) — app Siegfried DDD
| Columna archivo | Campo/medida Qlik |
|---|---|
| RegionCUP | `RegionCUP` |
| Mercado | `DescripcionMercado` |
| Droga | `DescripcionDrogaIMS` |
| Clase Terapeutica | `DescripcionClaseTerapeutica4IMS` |
| Codigo Clase Terapeutica | `CodigoClaseTerapeutica4IMS` |
| Codigo Producto | `CodigoProductoIMS` |
| Producto | `DescripcionProductoIMS` |
| AñoMes | `AñoMes` (formato "Dic-2025") |
| Unidades | `sum(MensualUnidades)` |

- **`clearAll()` obligatorio** antes del cubo (el app abre con selección default de mes, como Recetas).
- **Sin filtro oculto tipo Rofina/Fichado**: el archivo trae todos los productos de los mercados de la línea;
  build-competidores-shape-a.py filtra a mercados SIE por molécula/ATC (patrones SIE_PATTERNS_BY_LINE).

## Validación (2026-07-02)
Celda ancla exacta: `RegionCUP='_CAPITAL FEDERAL', DescripcionProductoIMS='ABLOOM TABL 10mg x 30',
AñoMes='Dic-2025'` → `sum(MensualUnidades) = 27` = archivo cardio (fila 1) **exacto**.

## OJO — volumen (define el método de extracción)
- El archivo por línea ya es **~774.882 filas** (cardio). El panel completo (145 mercados × 43 regiones ×
  productos × 24 meses) es **~7-8M filas** → **paginar hypercube ingenuamente es inviable** (~7000 páginas).
- **Opciones (elegir en la implementación):**
  1. **Export-to-file por API** (Qlik data-export / Reporting: exportar una straight-table a xlsx/csv) — lo
     más eficiente para este volumen. Requiere ubicar/crear el objeto tabla en el app.
  2. **Por-línea filtrado** (`DescripcionMercado` ∈ {mercados de la línea}) → ~774k/línea (~700 págs, ~5 min/línea).
     Necesita el mapa mercado→línea (que hoy vive implícito en los archivos por-línea; los 145 mercados de
     DescripcionMercado se reparten por línea).
- Recomendado: empezar con **(2) por-línea** para una línea (cardio) y validar el competidores-data.js completo
  contra el actual; si el volumen molesta, migrar a **(1) export-to-file**.

## Pendiente para cerrar DDD end-to-end
1. Elegir método de extracción (export-to-file vs por-línea) + mapa mercado→línea.
2. Extraer → xlsx `Producto-Mol-ATC-provincia` por línea → correr `build-competidores-shape-a.py` +
   los `rebuild/update-ddd-*` → comparar `competidores-data.js` y las páginas DDD contra las actuales.
3. Wire en update-all → _inbox.
