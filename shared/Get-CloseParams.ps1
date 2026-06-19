#requires -Version 5.1
<#
  Get-CloseParams.ps1 — Puente manifiesto -> PowerShell.

  Lee shared/close-manifest.json (via shared/manifest.py --emit-ps) y devuelve un
  hashtable con los parametros resueltos del cierre, para que update-all.ps1 /
  build-all.ps1 no hardcodeen rutas/mes. Fuente unica = close-manifest.json.

  Uso (dot-source):
    . (Join-Path $PSScriptRoot 'Get-CloseParams.ps1')
    $cp = Get-CloseParams
    $cp.CloseMonth   # 2026-05  (corte real -> --cutoff / --cierre)
    $cp.CycleFolder  # 2026-04  (carpeta legacy -> -Month de build-all / resolucion)
    $cp.src_iqvia_master   # path resuelto del AR_PM
    $cp.src_venta_interna  # path resuelto de la Planilla
#>

function Get-CloseParams {
    [CmdletBinding()]
    param()
    $py = if (Get-Command 'py' -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
    $manifest = Join-Path $PSScriptRoot 'manifest.py'
    if (-not (Test-Path -LiteralPath $manifest)) {
        throw "No encuentro manifest.py en $PSScriptRoot"
    }
    $lines = & $py $manifest --emit-ps
    if ($LASTEXITCODE -ne 0) {
        throw "manifest.py --emit-ps fallo (exit $LASTEXITCODE)"
    }
    $h = @{}
    foreach ($ln in $lines) {
        if (-not $ln) { continue }
        $i = $ln.IndexOf('=')
        if ($i -lt 0) { continue }
        $h[$ln.Substring(0, $i)] = $ln.Substring($i + 1)
    }
    return $h
}
