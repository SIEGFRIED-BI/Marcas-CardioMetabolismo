#requires -Version 5.1
<#
.SYNOPSIS
  Cierre mensual COMPLETO e IDEMPOTENTE en un comando, manifest-driven.
  Actualiza las 7 lineas (IQVIA + venta + competidores + KPIs + etiquetas) desde
  shared/close-manifest.json. FRENA antes de pushear.

.DESCRIPTION
  Toda la config sale del manifiesto (shared/close-manifest.json via Get-CloseParams.ps1):
    closeMonth (corte real, ej 2026-05) -> --cutoff / --cierre
    cycleFolder (carpeta legacy, ej 2026-04) -> -Month de build-all / paneles
    master / ateneo / venta -> rutas resueltas (de _inbox/<closeMonth> o legacy)

  Orden (con las cadenas de reversion bakeadas y los flags de idempotencia):
    1. build-all (5 data.js)
    2. sync SNC -> 3. re-aplicar PGB multidosis -> 4. re-aplicar BREXPIPRAZOLE
    5. sync derma -> 6. sync mujer
    7. preservar meses pre-ventana que los syncs borran (regla #7)
    8. venta --cutoff -> 9. re-split MAGNUS venta -> 10. re-aplicar mujer TRIP
    11. split MAGNUS iqvia/recetas
    12. competidores Shape-A
    13. recompute --cierre (ventana FIJA, evita que un mes parcial achique MAT)
    14. build-kpis + build-families + sync-kpistrip
    15. finalize-labels -> 16. cache-busters
    17. gates (syntax / audit / history --strict)
  Re-correrlo da el mismo resultado (idempotente). NO commitea ni pushea.

  Recetas (CloseUp) tienen su propia cadencia/corte: se mergean aparte cuando llega
  el pivot, NO en este cierre.

  IMPORTANTE: Windows PowerShell 5.1 (powershell.exe), NO pwsh 7 (corrompe data.js).

.PARAMETER Month
  Override del cycleFolder (carpeta de inputs). Default = manifest.cycleFolder.
.PARAMETER SkipBuildAll
  Saltea el build-all pesado (util para re-sincronizar el resto sin reconstruir data.js).
.EXAMPLE
  powershell.exe -File shared\update-all.ps1
#>
[CmdletBinding()]
param(
  [string]$Month,
  [switch]$SkipBuildAll,
  [switch]$Competidores
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }

if ($PSVersionTable.PSVersion.Major -ge 6) {
  Write-Warning "Estas en PowerShell $($PSVersionTable.PSVersion) (pwsh). El build necesita Windows PowerShell 5.1 o corrompe los data.js. Reabri con 'powershell.exe -File shared\update-all.ps1 ...'."
  exit 1
}

# ── Parametros del cierre desde el manifiesto (fuente unica) ──
. (Join-Path $PSScriptRoot 'Get-CloseParams.ps1')
$cp = Get-CloseParams
$closeMonth  = $cp.CloseMonth
$cycleFolder = if ($Month) { $Month } else { $cp.CycleFolder }
$master = $cp.src_iqvia_master
$ateneo = $cp.src_ateneo_mat
$venta  = $cp.src_venta_interna
if (-not (Test-Path -LiteralPath $master)) { throw "Master IQVIA no resuelto: '$master' (revisar close-manifest.json / _inbox)" }

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " update-all  close:$closeMonth  cycle:$cycleFolder" -ForegroundColor Cyan
Write-Host "   master: $(Split-Path $master -Leaf)" -ForegroundColor Cyan
Write-Host "   venta : $(if($venta){Split-Path $venta -Leaf}else{'(no resuelta)'})" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

function Step($name, $block) {
  Write-Host "`n>>> $name" -ForegroundColor Cyan
  & $block
  if ($LASTEXITCODE -ne 0) { Write-Warning "$name termino con exit $LASTEXITCODE" }
}

# 1. build data.js (5 lineas). build-all mergea venta SIN cutoff; el paso 8 la re-mergea con cutoff.
if (-not $SkipBuildAll) {
  Step 'build-all (5 lineas)' { & (Join-Path $PSScriptRoot 'build-all.ps1') -Month $cycleFolder -IqviaPattern 'AR_PM*' -SkipKpis }
}

# 2-6. mol_perf IQVIA: syncs + re-aplicar lo que el sync de SNC revierte
Step 'sync SNC'            { & $py (Join-Path $PSScriptRoot 'sync-snc-pm.py') --master $master }
Step 'SNC PGB multidosis'  { & $py (Join-Path $PSScriptRoot 'rebuild-pgb-multidosis-snc.py') --master $master }
Step 'SNC BREXPIPRAZOLE'   { & $py (Join-Path $PSScriptRoot 'rebuild-brexpiprazole-ateneo-snc.py') --source $ateneo }
Step 'sync derma'          { & $py (Join-Path $PSScriptRoot 'sync-dermato-pm.py') --master $master }
Step 'sync mujer'          { & $py (Join-Path $PSScriptRoot 'sync-mujer-pm.py') --master $master }

# 7. Preservar meses pre-ventana que los syncs borran (regla #7)
Step 'preservar historia'  { & $py (Join-Path $PSScriptRoot 'preserve-early-history.py') }

# 8-11. Venta (cutoff = mes cerrado) + re-aplicar los splits que venta/build revierten
if ($venta -and (Test-Path -LiteralPath $venta)) {
  Step 'venta interna (cutoff)' { & $py (Join-Path $PSScriptRoot 'merge-ventas-internas.py') --file $venta --cutoff $closeMonth }
  Step 'OTC MAGNUS venta'       { & $py (Join-Path $PSScriptRoot 'apply-otc-magnus-split.py') --file $venta --cutoff $closeMonth }
  Step 'mujer TRIP venta'       { & $py (Join-Path $PSScriptRoot 'fix-mujer-trip-venta.py') $venta --cutoff $closeMonth }
} else {
  Write-Warning "Venta no resuelta -> se saltea merge/splits de venta."
}
Step 'OTC MAGNUS iqvia/rec'  { & $py (Join-Path $PSScriptRoot 'split-otc-magnus-iqvia-recetas.py') }
# Estimado de MAGNUS / MAGNUS 36 desde la planilla por-SKU 'MKT sidus' (el panel de
# budget agrupa MAGNUS combinado -> MAGNUS 36 quedaba en 0). Skipea si falta el xlsx.
Step 'OTC MAGNUS estimado'   { & $py (Join-Path $PSScriptRoot 'fix-otc-magnus-estimado.py') }

# 12. Competidores (panel regional; su carpeta = cycleFolder).
# OPT-IN (-Competidores): el generador de paginas (build-competidores-pages /
# update-ddd-*) produce HOY un template distinto al committeado (titulo/fuente/
# layout) -> regenerar cambiaria la APARIENCIA de las paginas de competidores sin
# validar. Hasta definir cual template es el canonico, queda fuera del cierre por
# defecto (la data IQVIA/venta/KPIs SI se actualiza). Correr aparte: -Competidores.
if ($Competidores) {
  Step 'competidores data' { & $py (Join-Path $PSScriptRoot 'build-competidores-shape-a.py') --month $cycleFolder }
  foreach ($s in 'build-competidores-pages.py','rebuild-ddd-inline-from-competidores.py','update-ddd-mujer-from-competidores.py','update-ddd-otcdata-from-competidores.py') {
    $p = Join-Path $PSScriptRoot $s
    if (Test-Path -LiteralPath $p) { Step $s { & $py $p } }
  }
} else {
  Write-Host "`n>>> competidores: OMITIDO (template del generador difiere del committeado; usar -Competidores tras validar)" -ForegroundColor DarkYellow
}

# 13. Recompute aggregates con cierre FIJO (mata el bug del MAT que se achica)
Step 'recompute aggregates' { & $py (Join-Path $PSScriptRoot 'recompute-mol-perf-aggregates.py') --cierre $closeMonth }

# 14. KPIs consolidados + strip en las 7
Step 'build-kpis'     { & $py (Join-Path $PSScriptRoot 'build-kpis.py') --repo $repo }
Step 'build-families' { & $py (Join-Path $PSScriptRoot 'build-families-perf.py') }
Step 'sync-kpistrip'  { & $py (Join-Path $PSScriptRoot 'sync-kpistrip-with-kpis-json.py') }
# brandKpis[marca].market_total/ms/units = agregado autoritativo de mol_perf[fam].ytd/mat
# (build-data a veces deja un mercado más amplio o valores del mes). Va PRIMERO porque
# corrige units, de las que depende el IE. Idempotente.
Step 'brandKpis market_total' { & $py (Join-Path $PSScriptRoot 'fix-brandkpis-market-total.py') }
# brandKpis[marca].ie = IE relativo al mercado (no crecimiento propio), con las units
# ya corregidas por el paso anterior. Idempotente.
Step 'brandKpis IE vs mercado' { & $py (Join-Path $PSScriptRoot 'fix-brandkpis-ie-vs-market.py') }
# convenios: quita filas duplicadas exactas (misma OS con código distinto y mismas
# unidades) que el render suma -> doble conteo (PAMI/IOMA/SWISS). Idempotente.
Step 'convenios dedup' { & $py (Join-Path $PSScriptRoot 'dedup-convenios-exact.py') }
# brandKpis[marca].rec.ms: rellena desde rec_ms si quedó en 0 con dato (MOMETAX). Idempotente.
Step 'brandKpis rec.ms' { & $py (Join-Path $PSScriptRoot 'fix-brandkpis-rec.py') }

# 15-16. Etiquetas + cache-busters
Step 'finalize-labels' { & $py (Join-Path $PSScriptRoot 'finalize-labels.py') }
Step 'cache-busters'   { & $py (Join-Path $PSScriptRoot 'bump-cache-busters.py') }

# 17. Gates
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " GATES" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
$gateFail = $false
foreach ($g in @(
    @{n='syntax';  s='check-syntax-and-consistency.py'; a=@()},
    @{n='parity';  s='check-cross-line-parity.py';      a=@()},
    @{n='render';  s='check-render-parity.py';          a=@()},
    @{n='ddd';     s='check-ddd-health.py';             a=@()},
    @{n='labels';  s='audit-labels.py';                 a=@()},
    @{n='ie-rel';  s='fix-brandkpis-ie-vs-market.py';   a=@('--check')},
    @{n='bk-mkt';  s='fix-brandkpis-market-total.py';   a=@('--check')},
    @{n='conv-dup';s='dedup-convenios-exact.py';        a=@('--check')},
    @{n='bk-rec';  s='fix-brandkpis-rec.py';            a=@('--check')},
    @{n='audit';   s='audit-full.py';                   a=@()},
    @{n='history'; s='verify-history-preserved.py';     a=@('--baseline','HEAD','--strict')}
)) {
  $gp = Join-Path $PSScriptRoot $g.s
  if (-not (Test-Path -LiteralPath $gp)) { continue }
  Write-Host "`n>>> gate: $($g.n)" -ForegroundColor Cyan
  & $py $gp @($g.a)
  if ($LASTEXITCODE -ne 0) { Write-Warning "GATE $($g.n) FALLO (exit $LASTEXITCODE)"; $gateFail = $true }
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Push-Location $repo
git status -s
Pop-Location
if ($gateFail) {
  Write-Host "`n[!] Algun gate fallo. Revisar antes de commitear." -ForegroundColor Red
} else {
  Write-Host "`n[OK] Listo. Revisa el git diff y, si esta bien, commit + push (Cloudflare redeploya)." -ForegroundColor Green
}
Write-Host " (Este script NO commitea ni pushea.)" -ForegroundColor DarkGray
