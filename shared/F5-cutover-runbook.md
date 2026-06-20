# F5 — Cutover al `_inbox` único (runbook)

**Objetivo:** que todas las fuentes del cierre se lean de **una sola carpeta**
`Hub-Marcas-Inputs/_inbox/<closeMonth>/` en vez de las carpetas legacy dispersas.

**Estado:** la fundación está PROBADA end-to-end — el resolver
(`manifest.resolve_source`) prioriza `_inbox/<closeMonth>/<glob>` y, si no está,
cae al legacy (aditivo: con `_inbox` vacío resuelve EXACTO como hoy). Verificado:
un archivo puesto en `_inbox` gana al legacy; al sacarlo, vuelve al legacy.

**Por qué se hace en el cierre real (no antes):** si copiás los inputs al `_inbox`
mid-cycle y después llega un archivo más nuevo, el resolver tomaría la copia vieja
del `_inbox`. Por eso el cutover va **con los archivos finales del mes**.

## Procedimiento (de a UNA fuente, reversible)

Las fuentes hoy: `iqvia_master` (AR_PM*.xlsx), `venta_interna` (Planilla de
Ventas*.xlsx), `ateneo_mat` (= mismo AR_PM que iqvia_master).

1. **Ver el plan (dry-run, no toca nada):**
   ```
   powershell.exe -File shared\migrate-to-inbox.ps1
   ```
   Muestra qué copiaría a `_inbox/<closeMonth>/` y a dónde resuelve cada fuente.

2. **Migrar una fuente y validar:**
   ```
   powershell.exe -File shared\migrate-to-inbox.ps1 -Only iqvia_master -Execute
   ```
   COPIA (no mueve) → el legacy queda intacto. Confirmá en la salida que el
   resolver ahora apunte a `_inbox`.

3. **Correr el cierre normal y revisar:**
   ```
   powershell.exe -File shared\update-all.ps1
   ```
   `git diff` debe ser equivalente a un cierre normal (gates verdes). Si algo
   sale mal, borrá el archivo del `_inbox` → vuelve a resolver del legacy (rollback
   instantáneo).

4. Repetir 2-3 para `venta_interna` (ateneo_mat se cubre solo: mismo archivo que
   iqvia_master).

5. **Depreciar legacy:** recién tras 1-2 cierres OK leyendo del `_inbox`, archivar
   las carpetas legacy (`_iqvia-master/<cycleFolder>/`, planilla suelta en el hub).
   No hace falta tocar el manifest: el `legacyDir` queda como fallback histórico.

## Notas
- `closeMonth` (corte real) y `cycleFolder` (carpeta legacy) viven en
  `close-manifest.json`; el `_inbox` usa `closeMonth`.
- Para ver la resolución actual de cualquier fuente:
  `py shared\manifest.py --resolve iqvia_master`
- El cutover NO cambia nada del render ni del dato: solo de DÓNDE se leen los inputs.
