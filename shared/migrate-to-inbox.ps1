#requires -Version 5.1
<#
.SYNOPSIS
  F5 - Cutover al _inbox unico. COPIA (no mueve) las fuentes resueltas del cierre
  a _inbox/<closeMonth>/, para que el resolver (manifest.resolve_source) las tome
  de ahi en vez del legacy. COPIA = el legacy queda intacto -> reversible.

.DESCRIPTION
  El resolver prioriza _inbox/<closeMonth>/<glob> y si no, cae al legacyDir. Este
  script lleva las fuentes actuales (legacy) al _inbox, de a una o todas. Idempotente
  (si el archivo ya esta en _inbox, lo saltea). NO borra nada del legacy: la
  depreciacion de carpetas viejas se hace aparte, despues de 1-2 cierres OK.

  Recomendado: migrar de a UNA fuente (-Only), correr update-all, validar, y recien
  la siguiente. Default = DRY-RUN (solo muestra el plan); usar -Execute para copiar.

.PARAMETER Only
  Migrar solo esta fuente: iqvia_master | venta_interna | ateneo_mat. Default: todas.
.PARAMETER Execute
  Ejecuta la copia. Sin este flag = dry-run (no toca archivos).
.EXAMPLE
  powershell.exe -File shared\migrate-to-inbox.ps1                 # dry-run, todas
  powershell.exe -File shared\migrate-to-inbox.ps1 -Only iqvia_master -Execute
#>
[CmdletBinding()]
param(
  [ValidateSet('iqvia_master','venta_interna','ateneo_mat')]
  [string]$Only,
  [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$py = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
. (Join-Path $PSScriptRoot 'Get-CloseParams.ps1')
$cp = Get-CloseParams
$inbox = $cp.InboxDir
$close = $cp.CloseMonth
if (-not $inbox) { throw "El manifest no expone InboxDir (revisar shared/manifest.py emit-ps)." }

$sources = if ($Only) { @($Only) } else { @('iqvia_master','venta_interna','ateneo_mat') }

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " migrate-to-inbox  close:$close" -ForegroundColor Cyan
Write-Host "   inbox: $inbox" -ForegroundColor Cyan
Write-Host "   modo : $(if($Execute){'EXECUTE (copia real)'}else{'DRY-RUN (no toca archivos)'})" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

if ($Execute -and -not (Test-Path -LiteralPath $inbox)) {
  New-Item -ItemType Directory -Force -Path $inbox | Out-Null
}

$seen = @{}
foreach ($s in $sources) {
  $src = $cp.("src_$s")
  if (-not $src -or -not (Test-Path -LiteralPath $src)) {
    Write-Warning "[$s] no resuelto o inexistente: '$src' -> se saltea"
    continue
  }
  if ($seen.ContainsKey($src)) {
    Write-Host "[$s] mismo archivo que otra fuente ya planificada ($(Split-Path $src -Leaf)) -> skip" -ForegroundColor DarkGray
    continue
  }
  $seen[$src] = $true
  $leaf = Split-Path $src -Leaf
  $dest = Join-Path $inbox $leaf
  $srcInInbox = ($src -like "$inbox*")
  if ($srcInInbox) {
    Write-Host "[$s] ya resuelve desde _inbox ($leaf) -> nada que hacer" -ForegroundColor Green
    continue
  }
  if (Test-Path -LiteralPath $dest) {
    Write-Host "[$s] ya existe en _inbox: $leaf -> skip" -ForegroundColor DarkGray
    continue
  }
  Write-Host "[$s] COPY" -ForegroundColor Yellow
  Write-Host "    de : $src"
  Write-Host "    a  : $dest"
  if ($Execute) {
    Copy-Item -LiteralPath $src -Destination $dest
    Write-Host "    -> copiado." -ForegroundColor Green
  }
}

Write-Host "`n-- verificacion (resolver despues) --" -ForegroundColor Cyan
foreach ($s in $sources) {
  $r = & $py (Join-Path $PSScriptRoot 'manifest.py') --resolve $s
  Write-Host ("  {0,-14} -> {1}" -f $s, $r)
}
if (-not $Execute) {
  Write-Host "`n[DRY-RUN] nada copiado. Re-correr con -Execute para aplicar." -ForegroundColor DarkYellow
} else {
  Write-Host "`n[OK] Copiado a _inbox. Verifica arriba que el resolver apunte a _inbox," -ForegroundColor Green
  Write-Host "     corre el cierre (update-all.ps1) y valida. El legacy sigue intacto." -ForegroundColor Green
}
