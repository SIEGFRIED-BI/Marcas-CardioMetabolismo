# ============================================================================
# DEPRECADO / SOLO-REFERENCIA (jul-2026). NO forma parte del pipeline de cierre.
# Genero UNA VEZ (10-abr-2026) la segmentacion por CLASE IQVIA de mujer
# (ALTA DOSIS, SIN ESTROGENO, BAJA DOSIS 21+7, ...) mapeando familias por-MARCA
# -> CLASE (ver $segmentToFamilies mas abajo) y la horneo en mujer/data.js. Desde
# entonces esa segmentacion se PRESERVA y solo se le actualiza el time-series via
# shared/sync-mujer-pm.py (mujer se trata como SNC/derma; la protege el gate
# shared/check-mujer-segmentation.py; ver shared/update-all.ps1).
# Se conserva SOLO como REFERENCIA del mapeo marca<->clase. Su salida
# (mujer/market-overrides.js) era codigo muerto -ninguna pagina la cargaba- y fue
# eliminada. Requiere el Excel manual 'TABLERO ULTIMA VISTA 2.xlsx'.
# ============================================================================
param(
  [string]$WorkbookPath = 'C:\Users\camarinaro\Downloads\TABLERO ULTIMA VISTA 2.xlsx',
  [string]$OutputPath = (Join-Path $PSScriptRoot 'market-overrides.js')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$monthLabelEn = @{
  1 = 'Jan'; 2 = 'Feb'; 3 = 'Mar'; 4 = 'Apr'; 5 = 'May'; 6 = 'Jun'
  7 = 'Jul'; 8 = 'Aug'; 9 = 'Sep'; 10 = 'Oct'; 11 = 'Nov'; 12 = 'Dec'
}
$monthIndexEn = @{
  'jan' = 1; 'feb' = 2; 'mar' = 3; 'apr' = 4; 'may' = 5; 'jun' = 6
  'jul' = 7; 'aug' = 8; 'sep' = 9; 'oct' = 10; 'nov' = 11; 'dec' = 12
}
$dashboardFamilyOrder = @(
  'ISIS FREE','ISIS','ISIS MINI','ISIS MINI 24','SIDERBLUT COMPLEX','SIDERBLUT','SIDERBLUT POLI','SIDERBLUT FOLICO',
  'TRIP D3','TRIP +45','TRIP D3 PLUS','TRIP MAGNESIO','DELTROX NF','CALCIO BASE DUPOMAR','CALCIO BASE DUPOMAR D',
  'CALCIO CITRATO DUPOMAR D3 200','CALCIO CITRATO DUPOMAR D3 400','CLIMATIX'
)
$segmentToFamilies = [ordered]@{
  'SIN ESTROGENO' = @('ISIS FREE')
  'ALTA DOSIS' = @('ISIS')
  'BAJA DOSIS 21+7' = @('ISIS MINI')
  'BAJA DOSIS 24' = @('ISIS MINI 24')
  'COMPLEX' = @('SIDERBLUT COMPLEX', 'SIDERBLUT FOLICO')
  'PROD COMB DE HIERRO' = @('SIDERBLUT COMPLEX', 'SIDERBLUT FOLICO')
  'SOLO' = @('SIDERBLUT', 'SIDERBLUT POLI')
  'HIERRO SOLO' = @('SIDERBLUT', 'SIDERBLUT POLI')
  'D3' = @('TRIP D3')
  '45' = @('TRIP +45')
  'D3 PLUS' = @('TRIP D3 PLUS')
  'MAGNESIO' = @('TRIP MAGNESIO')
  'DELTROX' = @('DELTROX NF')
  'BASE' = @('CALCIO BASE DUPOMAR')
  'BASE D' = @('CALCIO BASE DUPOMAR D', 'CALCIO CITRATO DUPOMAR D3 200', 'CALCIO CITRATO DUPOMAR D3 400')
  'CLIMATIX' = @('CLIMATIX')
}

function Normalize-Text([object]$Value) {
  if ($null -eq $Value) { return '' }
  return ([string]$Value).Trim()
}

function To-Number([object]$Value) {
  if ($null -eq $Value) { return 0.0 }
  if ($Value -is [double] -or $Value -is [int] -or $Value -is [decimal] -or $Value -is [long]) { return [double]$Value }
  $text = ([string]$Value).Trim()
  if (-not $text -or $text -eq '-') { return 0.0 }
  $text = $text.Replace('.', '').Replace('%', '').Replace(',', '.')
  $parsed = 0.0
  if ([double]::TryParse($text, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) { return $parsed }
  return 0.0
}

function Normalize-ProductKey([string]$Value) {
  $text = (Normalize-Text $Value).ToUpperInvariant()
  $text = [regex]::Replace($text, '[^A-Z0-9]+', ' ')
  return ($text.Trim() -replace '\s+', ' ')
}

function Resolve-MujerFamily([string]$Candidate) {
  $probe = (Normalize-Text $Candidate).ToUpper()
  if (-not $probe) { return '' }
  if ($probe.Contains('ISIS FREE') -or $probe.Contains('S/ESTROG')) { return 'ISIS FREE' }
  if ($probe.Contains('ISIS MINI 24')) { return 'ISIS MINI 24' }
  if ($probe.Contains('ISIS MINI')) { return 'ISIS MINI' }
  if ($probe -match '(^| )ISIS( |$)') { return 'ISIS' }
  if ($probe.Contains('SIDERBLUT FOLIC')) { return 'SIDERBLUT FOLICO' }
  if ($probe.Contains('SIDERBLUT POLI')) { return 'SIDERBLUT POLI' }
  if ($probe.Contains('SIDERBLUT COMPLEX')) { return 'SIDERBLUT COMPLEX' }
  if ($probe.Contains('SIDERBLUT')) { return 'SIDERBLUT' }
  if ($probe.Contains('TRIP MAGNESIO')) { return 'TRIP MAGNESIO' }
  if ($probe.Contains('TRIP +45')) { return 'TRIP +45' }
  if ($probe.Contains('TRIP D3 PLUS')) { return 'TRIP D3 PLUS' }
  if ($probe.Contains('TRIP D3') -or $probe -match '(^| )TRIP( |$)') { return 'TRIP D3' }
  if ($probe.Contains('DELTROX')) { return 'DELTROX NF' }
  if ($probe.Contains('CLIMATIX')) { return 'CLIMATIX' }
  if ($probe.Contains('CALCIO') -and $probe.Contains('400')) { return 'CALCIO CITRATO DUPOMAR D3 400' }
  if ($probe.Contains('CALCIO') -and $probe.Contains('200')) { return 'CALCIO CITRATO DUPOMAR D3 200' }
  if ($probe.Contains('BASE D3') -or ($probe.Contains('BASE D') -and $probe.Contains('CALCIO'))) { return 'CALCIO BASE DUPOMAR D' }
  if ($probe.Contains('CALCIO BASE')) { return 'CALCIO BASE DUPOMAR' }
  return ''
}

function Normalize-MonthKey([string]$Header) {
  $raw = (Normalize-Text $Header).ToLower()
  $raw = $raw -replace '\s+', ' '
  $raw = $raw -replace '\.', ''
  if ($raw -match '^([a-z]{3})[ -](\d{2,4})$') {
    $mon = $matches[1]
    $year = [int]$matches[2]
    if ($year -lt 100) { $year += 2000 }
    if ($monthIndexEn.ContainsKey($mon)) { return '{0} {1}' -f $monthLabelEn[$monthIndexEn[$mon]], $year }
  }
  if ($raw -match '^([a-z]{3}) (\d{4})$') {
    $mon = $matches[1]
    if ($monthIndexEn.ContainsKey($mon)) { return '{0} {1}' -f $monthLabelEn[$monthIndexEn[$mon]], $matches[2] }
  }
  return ''
}

function Get-MonthSortValueEn([string]$MonthKey) {
  if ($MonthKey -match '^([A-Za-z]{3}) (\d{4})$') {
    return ([int]$matches[2] * 100) + $monthIndexEn[$matches[1].ToLower()]
  }
  return 0
}

function Round-Number([double]$Value, [int]$Digits = 1) { return [math]::Round($Value, $Digits) }

function Read-WorksheetMatrixByCells([object]$Worksheet) {
  $usedRange = $Worksheet.UsedRange
  try {
    $rows = $usedRange.Rows.Count
    $cols = $usedRange.Columns.Count
    $matrix = New-Object 'object[,]' ($rows + 1), ($cols + 1)
    for ($r = 1; $r -le $rows; $r++) {
      for ($c = 1; $c -le $cols; $c++) {
        $cell = $Worksheet.Cells.Item($r, $c)
        if ($r -le 2) {
          $matrix[$r, $c] = $cell.Text
        }
        else {
          $matrix[$r, $c] = $cell.Value2
        }
      }
    }
    return ,$matrix
  } finally {
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($usedRange) | Out-Null
  }
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $excel.Workbooks.Open($WorkbookPath, 0, $true)
try {
  $pmSheet = $wb.Worksheets.Item('IQVIA_MENSUAL')
  $pmMatrix = Read-WorksheetMatrixByCells -Worksheet $pmSheet
} finally {
  $wb.Close($false)
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}

$monthCols = @()
for ($c = 9; $c -lt $pmMatrix.GetLength(1); $c++) {
  $key = Normalize-MonthKey (Normalize-Text $pmMatrix[2, $c])
  if ($key -and (Get-MonthSortValueEn $key) -ge 202402) {
    $monthCols += [pscustomobject]@{ col = $c; key = $key }
  }
}
$monthlyKeys = @($monthCols | ForEach-Object { $_.key })
$currentKey = $monthlyKeys[-1]
$prevYearKey = if ($currentKey -match '^([A-Za-z]{3}) (\d{4})$') { '{0} {1}' -f $matches[1], ([int]$matches[2] - 1) } else { $null }

$brandConfig = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  $brandConfig[$family] = [ordered]@{ group = ''; sieProducts = @() }
}
for ($r = 3; $r -lt $pmMatrix.GetLength(0); $r++) {
  $isSIE = (Normalize-Text $pmMatrix[$r, 6]).ToUpper()
  if ($isSIE -notin @('SI','SÍ','YES')) { continue }
  $segment = Normalize-Text $pmMatrix[$r, 4]
  $product = Normalize-Text $pmMatrix[$r, 3]
  $presentation = Normalize-Text $pmMatrix[$r, 2]
  $brandLabel = Normalize-Text $pmMatrix[$r, 7]
  $family = Resolve-MujerFamily $brandLabel
  if (-not $family) { $family = Resolve-MujerFamily $product }
  if (-not $family) { $family = Resolve-MujerFamily $presentation }
  if (-not $family) { continue }
  if (-not $brandConfig.Contains($family)) { continue }
  if ($segment) { $brandConfig[$family].group = $segment }
  if ($product -and -not ($brandConfig[$family].sieProducts -contains $product)) { $brandConfig[$family].sieProducts += $product }
}
foreach ($segment in $segmentToFamilies.Keys) {
  foreach ($family in $segmentToFamilies[$segment]) {
    if (-not $brandConfig[$family].group) { $brandConfig[$family].group = $segment }
  }
}

$byGroup = @{}
for ($r = 3; $r -lt $pmMatrix.GetLength(0); $r++) {
  $group = Normalize-Text $pmMatrix[$r, 4]
  if (-not $group) { continue }
  if (-not $byGroup.ContainsKey($group)) { $byGroup[$group] = @{} }
  $product = Normalize-Text $pmMatrix[$r, 3]
  if (-not $product) { continue }
  if (-not $byGroup[$group].ContainsKey($product)) {
    $byGroup[$group][$product] = [ordered]@{
      manuf = Normalize-Text $pmMatrix[$r, 5]
      is_sie = ((Normalize-Text $pmMatrix[$r, 6]).ToUpper() -in @('SI','SÍ','YES'))
      monthly = @{}
    }
    foreach ($k in $monthlyKeys) { $byGroup[$group][$product].monthly[$k] = 0.0 }
  }
  foreach ($m in $monthCols) {
    $byGroup[$group][$product].monthly[$m.key] += To-Number $pmMatrix[$r, $m.col]
  }
}

function Get-YtdMap($monthlyMap) {
  $out = [ordered]@{}
  foreach ($k in $monthlyKeys) {
    $sum = 0.0
    if ($k -match '^([A-Za-z]{3}) (\d{4})$') {
      $year = [int]$matches[2]
      $limit = $monthIndexEn[$matches[1].ToLower()]
      foreach ($mk in $monthlyKeys) {
        if ($mk -match '^([A-Za-z]{3}) (\d{4})$' -and [int]$matches[2] -eq $year -and $monthIndexEn[$matches[1].ToLower()] -le $limit) {
          $sum += [double]$monthlyMap[$mk]
        }
      }
    }
    $out[$k] = [math]::Round($sum, 0)
  }
  return $out
}

function Get-MatMap($monthlyMap) {
  $out = [ordered]@{}
  foreach ($k in $monthlyKeys) {
    $idx = $monthlyKeys.IndexOf($k)
    $sum = 0.0
    $start = [Math]::Max(0, $idx - 11)
    for ($i = $start; $i -le $idx; $i++) { $sum += [double]$monthlyMap[$monthlyKeys[$i]] }
    $out[$k] = [math]::Round($sum, 0)
  }
  return $out
}

$molPerf = [ordered]@{}
$brandKpis = [ordered]@{}
$marketTotalsByGroup = @{}
$marketSieByGroup = @{}

foreach ($family in $dashboardFamilyOrder) {
  $group = $brandConfig[$family].group
  if (-not $group -or -not $byGroup.ContainsKey($group)) { continue }
  $marketMonthly = [ordered]@{}
  foreach ($k in $monthlyKeys) { $marketMonthly[$k] = 0.0 }
  foreach ($prod in $byGroup[$group].Keys) {
    foreach ($k in $monthlyKeys) { $marketMonthly[$k] += [double]$byGroup[$group][$prod].monthly[$k] }
  }
  $marketYtd = Get-YtdMap $marketMonthly
  $marketMat = Get-MatMap $marketMonthly

  $productRows = @()
  foreach ($prod in $byGroup[$group].Keys) {
    $item = $byGroup[$group][$prod]
    $ytdMap = Get-YtdMap $item.monthly
    $matMap = Get-MatMap $item.monthly
    $productRows += [pscustomobject]@{
      prod = $prod
      manuf = $item.manuf
      is_sie = [bool]$item.is_sie
      monthly = $item.monthly
      ytd = $ytdMap
      mat = $matMap
      currentMat = $matMap[$currentKey]
    }
  }
  $selected = New-Object 'System.Collections.Generic.List[string]'
  foreach ($sie in $brandConfig[$family].sieProducts) {
    if (($productRows | Where-Object { $_.prod -eq $sie })) { $selected.Add($sie) | Out-Null }
  }
  foreach ($row in ($productRows | Sort-Object -Property @{ Expression='currentMat'; Descending=$true })) {
    if ($selected.Count -ge 8) { break }
    if (-not $selected.Contains($row.prod)) { $selected.Add($row.prod) | Out-Null }
  }

  $productsOut = @()
  $currentYtdUnits = 0.0
  $prevYtdUnits = 0.0
  $currentMatUnits = 0.0
  $prevMatUnits = 0.0
  foreach ($row in $productRows) {
    if ($brandConfig[$family].sieProducts -contains $row.prod) {
      $currentYtdUnits += [double]$row.ytd[$currentKey]
      if ($prevYearKey -and $row.ytd.Contains($prevYearKey)) { $prevYtdUnits += [double]$row.ytd[$prevYearKey] }
      $currentMatUnits += [double]$row.mat[$currentKey]
      if ($prevYearKey -and $row.mat.Contains($prevYearKey)) { $prevMatUnits += [double]$row.mat[$prevYearKey] }
    }
    if (-not $selected.Contains($row.prod)) { continue }
    $msYtd = [ordered]@{}
    $msMat = [ordered]@{}
    foreach ($k in $monthlyKeys) {
      $msYtd[$k] = if ($marketYtd[$k] -gt 0) { Round-Number (($row.ytd[$k] / $marketYtd[$k]) * 100) } else { 0.0 }
      $msMat[$k] = if ($marketMat[$k] -gt 0) { Round-Number (($row.mat[$k] / $marketMat[$k]) * 100) } else { 0.0 }
    }
    $productsOut += [ordered]@{
      prod = $row.prod
      manuf = $row.manuf
      is_sie = [bool]$row.is_sie
      monthly_vals = $row.monthly
      ytd = $row.ytd
      mat = $row.mat
      ms_ytd = $msYtd
      ms_mat = $msMat
      quarterly_vals = [ordered]@{}
      ms_monthly = [ordered]@{}
      ms_quarterly = [ordered]@{}
    }
  }
  $molPerf[$family] = [ordered]@{
    products = $productsOut
    monthly = $marketMonthly
    ytd = $marketYtd
    mat = $marketMat
    quarterly = [ordered]@{}
  }
  $brandKpis[$family] = [ordered]@{
    ytd = [ordered]@{
      ie = if ($prevYtdUnits -gt 0) { Round-Number (($currentYtdUnits / $prevYtdUnits) * 100) } else { $null }
      ms = if ($marketYtd[$currentKey] -gt 0) { Round-Number (($currentYtdUnits / $marketYtd[$currentKey]) * 100) } else { $null }
      units = [math]::Round($currentYtdUnits, 0)
      units_prev = [math]::Round($prevYtdUnits, 0)
      market_total = [math]::Round($marketYtd[$currentKey], 0)
      growth = if ($prevYtdUnits -gt 0) { Round-Number ((($currentYtdUnits - $prevYtdUnits) / $prevYtdUnits) * 100) } else { $null }
    }
    mat = [ordered]@{
      ie = if ($prevMatUnits -gt 0) { Round-Number (($currentMatUnits / $prevMatUnits) * 100) } else { $null }
      ms = if ($marketMat[$currentKey] -gt 0) { Round-Number (($currentMatUnits / $marketMat[$currentKey]) * 100) } else { $null }
      units = [math]::Round($currentMatUnits, 0)
      units_prev = [math]::Round($prevMatUnits, 0)
      market_total = [math]::Round($marketMat[$currentKey], 0)
      growth = if ($prevMatUnits -gt 0) { Round-Number ((($currentMatUnits - $prevMatUnits) / $prevMatUnits) * 100) } else { $null }
    }
  }
  if (-not $marketTotalsByGroup.ContainsKey($group)) {
    $marketTotalsByGroup[$group] = @{ ytd = [double]$marketYtd[$currentKey]; mat = [double]$marketMat[$currentKey] }
    $marketSieByGroup[$group] = @{ currentYtd = 0.0; prevYtd = 0.0; currentMat = 0.0; prevMat = 0.0 }
  }
  $marketSieByGroup[$group].currentYtd += $currentYtdUnits
  $marketSieByGroup[$group].prevYtd += $prevYtdUnits
  $marketSieByGroup[$group].currentMat += $currentMatUnits
  $marketSieByGroup[$group].prevMat += $prevMatUnits
}

$totalMarketYtd = 0.0
$totalMarketMat = 0.0
$totalCurrentYtd = 0.0
$totalPrevYtd = 0.0
$totalCurrentMat = 0.0
$totalPrevMat = 0.0
foreach ($g in $marketTotalsByGroup.Keys) {
  $totalMarketYtd += $marketTotalsByGroup[$g].ytd
  $totalMarketMat += $marketTotalsByGroup[$g].mat
  $totalCurrentYtd += $marketSieByGroup[$g].currentYtd
  $totalPrevYtd += $marketSieByGroup[$g].prevYtd
  $totalCurrentMat += $marketSieByGroup[$g].currentMat
  $totalPrevMat += $marketSieByGroup[$g].prevMat
}

$molLabels = [ordered]@{}
$sieMolMap = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  $molLabels[$family] = $family
  $sieMolMap[$family] = $family
}

$override = [ordered]@{
  mol_perf = $molPerf
  brandKpis = $brandKpis
  kpiStrip = [ordered]@{
    ie_ytd = if ($totalPrevYtd -gt 0) { Round-Number (($totalCurrentYtd / $totalPrevYtd) * 100) } else { $null }
    ie_mat = if ($totalPrevMat -gt 0) { Round-Number (($totalCurrentMat / $totalPrevMat) * 100) } else { $null }
    ms_ytd = if ($totalMarketYtd -gt 0) { Round-Number (($totalCurrentYtd / $totalMarketYtd) * 100) } else { $null }
    ms_mat = if ($totalMarketMat -gt 0) { Round-Number (($totalCurrentMat / $totalMarketMat) * 100) } else { $null }
    units_ytd = [math]::Round($totalCurrentYtd, 0)
    units_ytd25 = [math]::Round($totalPrevYtd, 0)
    units_mat = [math]::Round($totalCurrentMat, 0)
    units_mat25 = [math]::Round($totalPrevMat, 0)
    mkt_ytd26 = [math]::Round($totalMarketYtd, 0)
    mkt_mat26 = [math]::Round($totalMarketMat, 0)
  }
  molLabels = $molLabels
  sieMolMap = $sieMolMap
}

$json = $override | ConvertTo-Json -Depth 8 -Compress
$js = "window.MUJER_MARKET_OVERRIDE = $json;"
[System.IO.File]::WriteAllText($OutputPath, $js, [System.Text.UTF8Encoding]::new($false))
Write-Output "Generated: $OutputPath"
