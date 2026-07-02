#requires -Version 5.1
<#
.SYNOPSIS
  Orquestador para regenerar los data.js de todos los dashboards del repo.

.DESCRIPTION
  Corre los build-data.ps1 de cardio, ATB, OTC, mujer y respiratorio para
  un mes dado, leyendo los Excels desde Hub-Marcas-Inputs (en OneDrive) y
  escribiendo el data.js de cada linea en su carpeta del repo.

  Lineas sin Excels en su carpeta del mes se saltean con warning.

.PARAMETER Month
  Mes a procesar en formato YYYY-MM, ej: '2026-04'.

.PARAMETER BaseDir
  Raiz de Hub-Marcas-Inputs. Por default usa
  $env:OneDrive\Documentos\Hub-Marcas-Inputs.

.PARAMETER Lines
  Lineas a procesar. Por default 'all' (cardio, ATB, OTC, mujer, respiratorio).
  Pueden pasarse varias separadas por coma: -Lines cardio,ATB

.PARAMETER CommitPush
  Si esta presente, hace git add */data.js + commit + push a origin/main.

.PARAMETER CommitMessage
  Mensaje de commit. Default: "Update dashboard data for <Month> cut".

.PARAMETER DryRun
  No corre ningun build, solo imprime que harian.

.PARAMETER IqviaSubfolder
  Subcarpeta dentro de BaseDir donde esta el Excel maestro de IQVIA.
  Default: '_iqvia-master'. Path final: <BaseDir>/<IqviaSubfolder>/<Month>/.
  Si la carpeta no existe, cada linea cae al lookup legacy en sus propias fuentes.

.PARAMETER IqviaPattern
  Glob para encontrar el Excel maestro de IQVIA dentro de la carpeta IqviaSubfolder.
  Default: 'AR_PM*' (matchea 'AR_PM_FV_Standard_<fecha>.xlsx', el formato
  estandar de IQVIA). Solo se usa si la carpeta IqviaSubfolder existe.

.PARAMETER VentasFile
  Path al xlsx de Planilla de Ventas (venta interna mensual por familia).
  Si se omite, busca en <BaseDir>/<VentasSubfolder>/<Month>/Planilla*.xlsx.
  Si no encuentra, skip silently la actualizacion de venta interna.

.PARAMETER VentasSubfolder
  Subcarpeta dentro de BaseDir donde esta la Planilla de Ventas.
  Default: '_ventas'.

.PARAMETER SkipKpis
  Si esta presente, NO regenera kpis.json al final. Por default
  build-all corre shared/build-kpis.py y trackea kpis.json en el commit.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04'
  Regenera data.js de las 5 lineas para el corte 2026-04. No hace commit.
  Lee el PM IQVIA desde Hub-Marcas-Inputs/_iqvia-master/2026-04/AR_PM*.xlsx
  si existe, sino cada linea cae al lookup legacy.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -Lines cardio,ATB
  Solo regenera cardio y ATB.

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -CommitPush
  Regenera todo y pushea a origin/main (Cloudflare Pages re-deploya solo).

.EXAMPLE
  .\shared\build-all.ps1 -Month '2026-04' -DryRun
  Muestra que builds correrian sin ejecutar nada.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^\d{4}-\d{2}$')]
    [string]$Month,

    [string]$BaseDir = (Join-Path $env:OneDrive 'Documentos\Hub-Marcas-Inputs'),

    [ValidateSet('cardio','ATB','OTC','mujer','respiratorio','all')]
    [string[]]$Lines = @('all'),

    [switch]$CommitPush,

    [string]$CommitMessage,

    [switch]$DryRun,

    [string]$IqviaSubfolder = '_iqvia-master',

    [string]$IqviaPattern = 'AR_PM*',

    [string]$VentasFile,

    [string]$VentasSubfolder = '_ventas',

    [switch]$SkipKpis
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

# Mapeo: linea repo -> carpeta hub + subcarpeta de fuentes + flag central IQVIA
# La subcarpeta '' significa que el script lee de la raiz del mes (caso respiratorio).
# OverrideBaseDir: si esta setteada, esa linea ignora el -BaseDir general y
#   busca sus fuentes en otro lado (caso OTC: sus inputs viven en
#   Actualizaciones-Marcas y no en Hub-Marcas-Inputs).
# UseCentralIqvia=$false: la linea NO usa el AR_PM centralizado y cae a su lookup legacy.
# UseSlicedIqvia=$true: la linea consume un AR_PM pre-sliceado (filtrado y reformateado
#   con shared/slice-iqvia-master.py) en lugar del master crudo. Necesario para mujer
#   porque su parser espera el layout de IQUVIA_VENTAS (col 4 = ATC-4, col 5 = mol)
#   y no el de AR_PM Premium (col 4 = ATC IV, col 6 = Molecules Long); el slicer hace
#   el reshape ademas del filtro por ATC-4 codes que mujer compite.
$lineConfig = [ordered]@{
    'cardio'       = @{ HubFolder = 'cardio';       FuentesSub = 'fuentes-originales'; UseCentralIqvia = $true;  UseSlicedIqvia = $false; OverrideBaseDir = $null }
    'ATB'          = @{ HubFolder = 'ATB';          FuentesSub = 'fuentes-originales'; UseCentralIqvia = $true;  UseSlicedIqvia = $false; OverrideBaseDir = $null }
    'OTC'          = @{ HubFolder = 'OTC';          FuentesSub = 'fuentes-originales'; UseCentralIqvia = $true;  UseSlicedIqvia = $false; OverrideBaseDir = (Join-Path $env:OneDrive 'Documentos\Actualizaciones-Marcas') }
    'mujer'        = @{ HubFolder = 'linea-mujer';  FuentesSub = 'fuentes-originales'; UseCentralIqvia = $true;  UseSlicedIqvia = $true;  OverrideBaseDir = $null }
    'respiratorio' = @{ HubFolder = 'respiratorio'; FuentesSub = '';                   UseCentralIqvia = $true;  UseSlicedIqvia = $false; OverrideBaseDir = $null }
}

if ($Lines -contains 'all') {
    $Lines = @($lineConfig.Keys)
}

if (-not $CommitMessage) {
    $CommitMessage = "Update dashboard data for $Month cut"
}

# Validacion del BaseDir
if (-not (Test-Path -LiteralPath $BaseDir)) {
    throw "BaseDir not found: $BaseDir`nUsa -BaseDir <path> si tu Hub-Marcas-Inputs esta en otro lugar."
}

# IQVIA centralizada (opcional). Si la carpeta no existe, cada linea
# cae al lookup legacy en su propia carpeta de fuentes.
$iqviaMasterDir = Join-Path $BaseDir (Join-Path $IqviaSubfolder $Month)
$iqviaSlicedDir = Join-Path $iqviaMasterDir 'sliced'
$iqviaCentralized = Test-Path -LiteralPath $iqviaMasterDir
$iqviaMasterFile = $null
if ($iqviaCentralized) {
    $iqviaMasterFile = Get-ChildItem -LiteralPath $iqviaMasterDir -Filter $IqviaPattern -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $iqviaMasterFile) {
        Write-Warning "Carpeta IQVIA centralizada existe pero no hay match para '$IqviaPattern' en $iqviaMasterDir. Cae a legacy."
        $iqviaCentralized = $false
    }
}

# Si alguna linea pidio slice y existe master, generamos los slices con
# shared/slice-iqvia-master.py antes de empezar a procesar.
$linesNeedingSlice = @($Lines | Where-Object {
    $lineConfig.Contains($_) -and $lineConfig[$_].UseSlicedIqvia
})
if ($iqviaCentralized -and $linesNeedingSlice.Count -gt 0 -and -not $DryRun) {
    Write-Host ""
    Write-Host "Generando slices de IQVIA master para: $($linesNeedingSlice -join ', ')..." -ForegroundColor Cyan
    $slicerPath = Join-Path $PSScriptRoot 'slice-iqvia-master.py'
    $pyExe = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
    & $pyExe $slicerPath --master $iqviaMasterFile.FullName --out-dir $iqviaSlicedDir --lines @($linesNeedingSlice)
    if ($LASTEXITCODE -ne 0) {
        throw "El slicer ($slicerPath) fallo con exit code $LASTEXITCODE."
    }
}

Write-Host ""
Write-Host "================================================================"
Write-Host " build-all  -  Mes: $Month  -  Lineas: $($Lines -join ', ')"
Write-Host " Hub:  $BaseDir"
Write-Host " Repo: $repoRoot"
if ($iqviaCentralized) {
    Write-Host " IQVIA: $iqviaMasterDir  (pattern '$IqviaPattern')" -ForegroundColor Green
} else {
    Write-Host " IQVIA: legacy (cada linea lee de su carpeta de fuentes)" -ForegroundColor DarkGray
}
if ($DryRun) { Write-Host " ** DRY RUN ** (no se ejecuta nada)" }
Write-Host "================================================================"

$results = [ordered]@{}

foreach ($line in $Lines) {
    if (-not $lineConfig.Contains($line)) {
        Write-Warning "Linea desconocida: $line  -  saltando"
        $results[$line] = 'unknown'
        continue
    }
    $cfg = $lineConfig[$line]
    # Algunas lineas tienen sus inputs en otra carpeta-raiz (ej. OTC vive
    # en Actualizaciones-Marcas en vez de Hub-Marcas-Inputs).
    $effectiveBase = if ($cfg.OverrideBaseDir) { $cfg.OverrideBaseDir } else { $BaseDir }
    $monthDir = Join-Path $effectiveBase (Join-Path $cfg.HubFolder $Month)
    if ($cfg.FuentesSub) {
        $sourceDir = Join-Path $monthDir $cfg.FuentesSub
    } else {
        $sourceDir = $monthDir
    }
    $scriptPath = Join-Path $repoRoot (Join-Path $line 'build-data.ps1')

    Write-Host ""
    Write-Host "[$line] -----------------------------------------------------" -ForegroundColor Cyan
    Write-Host "  Source:  $sourceDir"
    Write-Host "  Script:  $scriptPath"

    if (-not (Test-Path -LiteralPath $sourceDir)) {
        Write-Warning "  Carpeta de fuentes inexistente. Saltando."
        $results[$line] = 'skipped (no source folder)'
        continue
    }
    # Algunas lineas (ej. respiratorio) splitean inputs en subcarpetas
    # 'dashboard/' y 'ddd/'. Buscamos xlsx/csv en la raiz Y en esas subcarpetas.
    $checkDirs = @($sourceDir)
    foreach ($sub in 'dashboard','ddd') {
        $subPath = Join-Path $sourceDir $sub
        if (Test-Path -LiteralPath $subPath) { $checkDirs += $subPath }
    }
    $excelCount = 0
    foreach ($d in $checkDirs) {
        $excelCount += (Get-ChildItem -LiteralPath $d -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in '.xlsx','.xlsm','.xls','.csv' }).Count
    }
    if ($excelCount -eq 0) {
        Write-Warning "  No hay Excels/CSV en la carpeta (ni en subcarpetas dashboard/ ddd/). Saltando."
        $results[$line] = 'skipped (empty)'
        continue
    }
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        Write-Warning "  Script de build inexistente: $scriptPath"
        $results[$line] = 'skipped (no script)'
        continue
    }

    # Build args para la invocacion
    $invokeArgs = @{ SourceDir = $sourceDir }
    if ($iqviaCentralized -and $cfg.UseCentralIqvia) {
        if ($cfg.UseSlicedIqvia) {
            # Esta linea consume un slice pre-procesado de AR_PM (re-shaped al
            # layout que su parser espera). Apuntamos -IqviaDir al sliced/ dir
            # y -IqviaPattern al archivo concreto del slice.
            $invokeArgs.IqviaDir = $iqviaSlicedDir
            $invokeArgs.IqviaPattern = "AR_PM_$line.xlsx"
            Write-Host "  IQVIA: sliced ($($invokeArgs.IqviaDir)\$($invokeArgs.IqviaPattern))" -ForegroundColor Green
        } else {
            $invokeArgs.IqviaDir = $iqviaMasterDir
            $invokeArgs.IqviaPattern = $IqviaPattern
        }
    } elseif ($iqviaCentralized -and -not $cfg.UseCentralIqvia) {
        Write-Host "  IQVIA: legacy (esta linea no soporta AR_PM centralizado)" -ForegroundColor DarkGray
    }

    if ($DryRun) {
        $argsPreview = $invokeArgs.GetEnumerator() | ForEach-Object { "-$($_.Key) `"$($_.Value)`"" }
        Write-Host "  [DRY RUN] $scriptPath $($argsPreview -join ' ')" -ForegroundColor Yellow
        $results[$line] = 'dry-run'
        continue
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $scriptPath @invokeArgs
        $sw.Stop()
        $results[$line] = "ok ($([int]$sw.Elapsed.TotalSeconds)s)"
        Write-Host "  OK ($([int]$sw.Elapsed.TotalSeconds)s)" -ForegroundColor Green
    } catch {
        $sw.Stop()
        $msg = $_.Exception.Message
        if ($msg.Length -gt 200) { $msg = $msg.Substring(0,200) + '...' }
        $results[$line] = "FAILED: $msg"
        Write-Host "  FAILED: $msg" -ForegroundColor Red
    }
}

# Resumen
Write-Host ""
Write-Host "================================================================"
Write-Host " RESUMEN"
Write-Host "================================================================"
foreach ($k in $results.Keys) {
    $status = $results[$k]
    $color = switch -Wildcard ($status) {
        'ok*'        { 'Green' }
        'skipped*'   { 'Yellow' }
        'unknown'    { 'Yellow' }
        'dry-run'    { 'DarkGray' }
        'FAILED*'    { 'Red' }
        default      { 'Gray' }
    }
    Write-Host ("  {0,-14} : {1}" -f $k, $status) -ForegroundColor $color
}

# Regenerar el cross-line-summary.json del hub si al menos una linea termino bien.
if (-not $DryRun) {
    $anyOk = $results.Values | Where-Object { $_ -like 'ok*' }
    if ($anyOk) {
        $summaryScript = Join-Path $PSScriptRoot 'build-summary.py'
        if (Test-Path -LiteralPath $summaryScript) {
            $pyExe = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
            Write-Host ""
            Write-Host "Regenerando shared/cross-line-summary.json..." -ForegroundColor Cyan
            & $pyExe $summaryScript --repo $repoRoot
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "El build-summary.py fallo (exit $LASTEXITCODE), pero los data.js si se generaron."
            }
        }
    }
}

# ─── Venta interna: actualizar budget.real desde Planilla de Ventas ───
# Resuelve VentasFile en este orden:
#   1) Param explicito -VentasFile
#   2) <BaseDir>/<VentasSubfolder>/<Month>/Planilla*.xlsx (mas reciente)
$pyExe = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
if (-not $DryRun) {
    $resolvedVentas = $null
    if ($VentasFile) {
        if (Test-Path -LiteralPath $VentasFile) {
            $resolvedVentas = $VentasFile
        } else {
            Write-Warning "VentasFile especificado no existe: $VentasFile"
        }
    } else {
        $ventasDir = Join-Path $BaseDir (Join-Path $VentasSubfolder $Month)
        if (Test-Path -LiteralPath $ventasDir) {
            $candidates = Get-ChildItem -LiteralPath $ventasDir -Filter 'Planilla*.xlsx' -File -ErrorAction SilentlyContinue |
                Sort-Object -Property LastWriteTime -Descending
            if ($candidates) { $resolvedVentas = $candidates[0].FullName }
        }
    }
    if ($resolvedVentas) {
        $ventasScript = Join-Path $PSScriptRoot 'merge-ventas-internas.py'
        if (Test-Path -LiteralPath $ventasScript) {
            Write-Host ""
            Write-Host "Actualizando venta interna desde: $resolvedVentas" -ForegroundColor Cyan
            & $pyExe $ventasScript --file $resolvedVentas
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "merge-ventas-internas.py fallo (exit $LASTEXITCODE)."
            }
        }
    } else {
        Write-Host ""
        Write-Host "Venta interna: no hay Planilla de Ventas (skip)." -ForegroundColor DarkGray
    }
}

# ─── KPIs: regenerar kpis.json (consume rec_ms / mol_perf / budget) ───
if (-not $DryRun -and -not $SkipKpis) {
    $kpisScript = Join-Path $PSScriptRoot 'build-kpis.py'
    if (Test-Path -LiteralPath $kpisScript) {
        Write-Host ""
        Write-Host "Regenerando kpis.json..." -ForegroundColor Cyan
        & $pyExe $kpisScript --repo $repoRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "build-kpis.py fallo (exit $LASTEXITCODE)."
        }
    }
}

# ─── Cache-busters: bump ?v=<hash> tras regenerar data.js / kpis.json ───
# Evita que el navegador/CDN sirva una version vieja cacheada de data.js.
if (-not $DryRun) {
    $cbScript = Join-Path $PSScriptRoot 'bump-cache-busters.py'
    if (Test-Path -LiteralPath $cbScript) {
        Write-Host ""
        Write-Host "Actualizando cache-busters (?v=hash)..." -ForegroundColor Cyan
        & $pyExe $cbScript
    }
}

# Commit & push
if ($CommitPush -and -not $DryRun) {
    $hadFailure = $results.Values | Where-Object { $_ -like 'FAILED*' }
    if ($hadFailure) {
        Write-Host ""
        Write-Warning "Hubo errores en algun build, NO se hace commit/push."
        exit 1
    }
    Write-Host ""
    Write-Host "================================================================"
    Write-Host " Git commit + push"
    Write-Host "================================================================"
    Push-Location $repoRoot
    try {
        # data.js de las lineas + shared/cross-line-summary.json + kpis.json
        # + inline D de mujer/SNC (si merge-ventas o sync los toco)
        git add '*/data.js' 'shared/cross-line-summary.json' 'kpis.json' 'kpis-families.json' `
                'cardio/index.html' 'ATB/index.html' 'OTC/index.html' 'respiratorio/index.html' `
                'mujer/index.html' 'SNC/index.html' 'dermatologia/dermato_dashboard.html' `
                'kpis.html' 'index.html' 2>&1 | Out-Null
        $staged = git diff --cached --name-only
        if (-not $staged) {
            Write-Host "  Sin cambios para commitear." -ForegroundColor Yellow
        } else {
            Write-Host "  Archivos staged:"
            $staged | ForEach-Object { Write-Host "    $_" }
            git commit -m $CommitMessage
            if ($LASTEXITCODE -ne 0) { throw "git commit fallo (exit $LASTEXITCODE)" }
            git push origin main
            if ($LASTEXITCODE -ne 0) { throw "git push fallo (exit $LASTEXITCODE)" }
            Write-Host "  Pusheado a origin/main." -ForegroundColor Green
            Write-Host "  Cloudflare Pages re-deploya en ~1-2 min." -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
