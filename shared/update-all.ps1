#requires -Version 5.1
<#
.SYNOPSIS
  Cierre mensual COMPLETO en un comando: actualiza las 7 lineas + DDD/competidores
  + KPIs + etiquetas + cache-busters desde las mismas bases. FRENA antes de pushear.

.DESCRIPTION
  Corre, en orden:
    1. build-all.ps1 -Month <M>            (cardio/ATB/OTC/mujer/respiratorio + DDD principal + venta + kpis)
    2. sync-snc-pm.py / sync-dermato-pm.py --master <AR_PM>   (SNC y derma)
    3. build-competidores-shape-a.py --month <M>             (competidores-data.js + pages)
       (+ build-competidores-pages.py / update-ddd-from-competidores.py si existen)
    4. build-kpis.py + build-families-perf.py + sync-kpistrip-with-kpis-json.py
    5. finalize-labels.py                  (etiquetas consistentes + "Datos al"=hoy)
    6. bump-cache-busters.py
    7. Gates: check-syntax-and-consistency.py, audit-full.py, verify-history-preserved.py
  NO hace commit ni push: imprime git status para que revises y pushees vos.

  IMPORTANTE: correr con Windows PowerShell 5.1 (powershell.exe), NO pwsh 7
  (pwsh corrompe los data.js por el serializer). Este script lo verifica.

.PARAMETER Month
  Mes a procesar, YYYY-MM. Default '2026-04'.
.PARAMETER IqviaPattern
  Glob del master AR_PM en _iqvia-master/<Month>/. Default 'AR_PM*'.
.PARAMETER SkipBuildAll
  Saltea el build-all pesado (util si los data.js ya estan al dia y solo
  queres re-sincronizar SNC/derma/competidores/kpis/etiquetas).
.EXAMPLE
  powershell.exe -File shared\update-all.ps1 -Month 2026-04
#>
[CmdletBinding()]
param(
  [ValidatePattern('^\d{4}-\d{2}$')][string]$Month = '2026-04',
  [string]$BaseDir = (Join-Path $env:OneDrive 'Documentos\Hub-Marcas-Inputs'),
  [string]$IqviaPattern = 'AR_PM*',
  [switch]$SkipBuildAll
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }

if ($PSVersionTable.PSVersion.Major -ge 6) {
  Write-Warning "Estas en PowerShell $($PSVersionTable.PSVersion) (pwsh). El build necesita Windows PowerShell 5.1 o corrompe los data.js. Reabrí con 'powershell.exe -File shared\update-all.ps1 ...'."
  exit 1
}

$masterDir = Join-Path $BaseDir (Join-Path '_iqvia-master' $Month)
$master = Get-ChildItem -LiteralPath $masterDir -Filter $IqviaPattern -File -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -notmatch '^~\$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $master) { throw "No encontre master '$IqviaPattern' en $masterDir" }

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " update-all  Mes:$Month  Master:$($master.Name)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

function Step($name, $script) {
  Write-Host "`n>>> $name" -ForegroundColor Cyan
  & $script
  if ($LASTEXITCODE -ne 0) { Write-Warning "$name termino con exit $LASTEXITCODE" }
}

# 1. build-all (5 lineas + DDD principal + venta + kpis + cache-busters intermedios)
if (-not $SkipBuildAll) {
  Step 'build-all (5 lineas)' { & (Join-Path $PSScriptRoot 'build-all.ps1') -Month $Month -IqviaPattern $IqviaPattern -SkipKpis }
}

# 2. SNC + derma (aceptan --master)
Step 'sync SNC'   { & $py (Join-Path $PSScriptRoot 'sync-snc-pm.py')     --master $master.FullName }
# SNC tiene customizaciones que sync-snc NO conoce y debe re-aplicar SIEMPRE despues:
#   - PGB multidosis (PREGABALIN = solo tabletas multidosis, no el mercado completo)
#   - BREXIL = mercado BREXPIPRAZOLE (sync-snc no genera esa familia)
# Si no se re-aplican, sync-snc deja PREGABALIN completo y borra BREXPIPRAZOLE.
Step 'SNC: PGB multidosis'  { & $py (Join-Path $PSScriptRoot 'rebuild-pgb-multidosis-snc.py') }
Step 'SNC: BREXPIPRAZOLE'   { & $py (Join-Path $PSScriptRoot 'rebuild-brexpiprazole-ateneo-snc.py') }
Step 'sync derma' { & $py (Join-Path $PSScriptRoot 'sync-dermato-pm.py') --master $master.FullName }

# 3. Competidores (data + pages) y DDD subpaginas
Step 'competidores data' { & $py (Join-Path $PSScriptRoot 'build-competidores-shape-a.py') --month $Month }
foreach ($s in 'build-competidores-pages.py','update-ddd-from-competidores.py','update-ddd-mujer-from-competidores.py','update-ddd-otcdata-from-competidores.py') {
  $p = Join-Path $PSScriptRoot $s
  if (Test-Path -LiteralPath $p) { Step $s { & $py $p } }
}

# 4. KPIs consolidados + sync del strip en las 7
Step 'build-kpis'        { & $py (Join-Path $PSScriptRoot 'build-kpis.py') --repo $repo }
Step 'build-families'    { & $py (Join-Path $PSScriptRoot 'build-families-perf.py') }
Step 'sync-kpistrip'     { & $py (Join-Path $PSScriptRoot 'sync-kpistrip-with-kpis-json.py') }

# 5. Etiquetas consistentes + "Datos al" = hoy
Step 'finalize-labels'   { & $py (Join-Path $PSScriptRoot 'finalize-labels.py') }

# 6. Cache-busters
Step 'cache-busters'     { & $py (Join-Path $PSScriptRoot 'bump-cache-busters.py') }

# 7. Gates
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " GATES" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
$gateFail = $false
foreach ($g in @(
    @{n='syntax';  s='check-syntax-and-consistency.py'; a=@()},
    @{n='audit';   s='audit-full.py';                   a=@()},
    @{n='history'; s='verify-history-preserved.py';     a=@('--baseline','HEAD')}
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
