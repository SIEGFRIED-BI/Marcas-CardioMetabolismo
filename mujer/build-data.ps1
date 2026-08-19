param(
  [string]$SourceDir = 'C:\Users\camarinaro\Downloads\Hub-Marcas-Inputs\linea-mujer\2026-04\fuentes-originales',
  [string]$OutputPath = (Join-Path $PSScriptRoot 'data.js'),
  # Override opcional para leer el PM IQVIA desde una carpeta centralizada
  # (ej. Hub-Marcas-Inputs/_iqvia-master/2026-04/). Si no se pasa, usa el
  # lookup legacy en $SourceDir con el patron 'IQUVIA_VENTAS.xlsx'.
  # NOTA: solo afecta el lookup de PM, NO el de DDD ni el del MAESTRO_COM_CARLITOS,
  # que siguen leyendose desde $SourceDir.
  [string]$IqviaDir = $null,
  [string]$IqviaPattern = $null
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$monthIndex = @{
  'ene' = 1; 'feb' = 2; 'mar' = 3; 'abr' = 4; 'may' = 5; 'jun' = 6
  'jul' = 7; 'ago' = 8; 'sep' = 9; 'sept' = 9; 'oct' = 10; 'nov' = 11; 'dic' = 12
}

$monthLabel = @{
  1 = 'Ene'; 2 = 'Feb'; 3 = 'Mar'; 4 = 'Abr'; 5 = 'May'; 6 = 'Jun'
  7 = 'Jul'; 8 = 'Ago'; 9 = 'Sep'; 10 = 'Oct'; 11 = 'Nov'; 12 = 'Dic'
}

$monthLabelEn = @{
  1 = 'Jan'; 2 = 'Feb'; 3 = 'Mar'; 4 = 'Apr'; 5 = 'May'; 6 = 'Jun'
  7 = 'Jul'; 8 = 'Aug'; 9 = 'Sep'; 10 = 'Oct'; 11 = 'Nov'; 12 = 'Dec'
}

$monthIndexEn = @{
  'jan' = 1; 'feb' = 2; 'mar' = 3; 'apr' = 4; 'may' = 5; 'jun' = 6
  'jul' = 7; 'aug' = 8; 'sep' = 9; 'oct' = 10; 'nov' = 11; 'dec' = 12
}

$dashboardFamilyOrder = @(
  'ISIS FREE',
  'ISIS',
  'ISIS MINI',
  'ISIS MINI 24',
  'SIDERBLUT COMPLEX',
  'SIDERBLUT',
  'SIDERBLUT POLI',
  'SIDERBLUT FOLICO',
  'TRIP D3',
  'TRIP +45',
  'TRIP D3 PLUS',
  'TRIP MAGNESIO',
  'DELTROX NF',
  'CALCIO BASE DUPOMAR',
  'CALCIO BASE DUPOMAR D',
  'CALCIO CITRATO DUPOMAR D3 200',
  'CALCIO CITRATO DUPOMAR D3 400',
  'CLIMATIX'
)

$dashboardColors = [ordered]@{
  'ISIS FREE' = '#b01e1e'
  'ISIS' = '#dc2626'
  'ISIS MINI' = '#ef4444'
  'ISIS MINI 24' = '#f97316'
  'SIDERBLUT COMPLEX' = '#16a34a'
  'SIDERBLUT' = '#059669'
  'SIDERBLUT POLI' = '#0d9488'
  'SIDERBLUT FOLICO' = '#0284c7'
  'TRIP D3' = '#7c3aed'
  'TRIP +45' = '#4f46e5'
  'TRIP D3 PLUS' = '#14b8a6'
  'TRIP MAGNESIO' = '#6366f1'
  'DELTROX NF' = '#92400e'
  'CALCIO BASE DUPOMAR' = '#d97706'
  'CALCIO BASE DUPOMAR D' = '#ea580c'
  'CALCIO CITRATO DUPOMAR D3 200' = '#2563eb'
  'CALCIO CITRATO DUPOMAR D3 400' = '#1d4ed8'
  'CLIMATIX' = '#db2777'
}

$dashboardMarketConfig = [ordered]@{
  'ISIS FREE' = @{ label = 'Sin estrógeno'; group = 'ISIS FREE'; filters = @(@{ productsLike = @('ISIS FREE') }); sieProducts = @('ISIS FREE (SIE)') }
  'ISIS' = @{ label = 'Alta dosis'; group = 'ISIS'; filters = @(@{ productsLike = @('ISIS') }); sieProducts = @('ISIS (SIE)') }
  'ISIS MINI' = @{ label = 'Baja dosis 21+7'; group = 'ISIS MINI'; filters = @(@{ productsLike = @('ISIS MINI') }); sieProducts = @('ISIS MINI (SIE)') }
  'ISIS MINI 24' = @{ label = 'Baja dosis 24'; group = 'ISIS MINI 24'; filters = @(@{ productsLike = @('ISIS MINI 24') }); sieProducts = @('ISIS MINI 24 (SIE)') }
  'SIDERBLUT COMPLEX' = @{ label = 'Hierro complejo'; group = 'SIDERBLUT COMPLEX'; filters = @(@{ productsLike = @('SIDERBLUT COMPLEX') }); sieProducts = @('SIDERBLUT COMPLEX (SIE)') }
  'SIDERBLUT' = @{ label = 'Hierro solo'; group = 'SIDERBLUT'; filters = @(@{ productsLike = @('SIDERBLUT') }); sieProducts = @('SIDERBLUT (SIE)') }
  'SIDERBLUT POLI' = @{ label = 'Hierro poli'; group = 'SIDERBLUT POLI'; filters = @(@{ productsLike = @('SIDERBLUT POLI') }); sieProducts = @('SIDERBLUT POLI (SIE)') }
  'SIDERBLUT FOLICO' = @{ label = 'Hierro folico'; group = 'SIDERBLUT FOLICO'; filters = @(@{ productsLike = @('SIDERBLUT FOLICO') }); sieProducts = @('SIDERBLUT FOLICO (SIE)') }
  'TRIP D3' = @{ label = 'Colecalciferol'; group = 'TRIP D3'; filters = @(@{ productsLike = @('TRIP D3') }); sieProducts = @('TRIP D3 (SIE)') }
  'TRIP +45' = @{ label = 'Meno care'; group = 'TRIP +45'; filters = @(@{ productsLike = @('TRIP +45') }); sieProducts = @('TRIP +45 (SIE)') }
  'TRIP D3 PLUS' = @{ label = 'D3 + K2'; group = 'TRIP D3 PLUS'; filters = @(@{ productsLike = @('TRIP D3 PLUS') }); sieProducts = @('TRIP D3 PLUS (SIE)') }
  'TRIP MAGNESIO' = @{ label = 'Magnesio'; group = 'TRIP MAGNESIO'; filters = @(@{ productsLike = @('TRIP MAGNESIO') }); sieProducts = @('TRIP MAGNESIO (SIE)') }
  'DELTROX NF' = @{ label = 'Ibandronico'; group = 'DELTROX NF'; filters = @(@{ productsLike = @('DELTROX NF', 'DELTROX') }); sieProducts = @('DELTROX NF (SIE)') }
  'CALCIO BASE DUPOMAR' = @{ label = 'Calcio base'; group = 'CALCIO BASE DUPOMAR'; filters = @(@{ productsLike = @('CALCIO BASE DUPOMAR') }); sieProducts = @('CALCIO BASE DUPOMAR (SIE)') }
  'CALCIO BASE DUPOMAR D' = @{ label = 'Calcio + D'; group = 'CALCIO BASE DUPOMAR D'; filters = @(@{ productsLike = @('CALCIO BASE DUPOMAR D') }); sieProducts = @('CALCIO BASE DUPOMAR D (SIE)') }
  'CALCIO CITRATO DUPOMAR D3 200' = @{ label = 'Calcio citrato D3 200'; group = 'CALCIO CITRATO DUPOMAR D3 200'; filters = @(@{ productsLike = @('CALCIO CITRATO DUPOMAR D3 200') }); sieProducts = @('CALCIO CITRATO DUPOMAR D3 200 (SIE)') }
  'CALCIO CITRATO DUPOMAR D3 400' = @{ label = 'Calcio citrato D3 400'; group = 'CALCIO CITRATO DUPOMAR D3 400'; filters = @(@{ productsLike = @('CALCIO CITRATO DUPOMAR D3 400') }); sieProducts = @('CALCIO CITRATO DUPOMAR D3 400 (SIE)') }
  'CLIMATIX' = @{ label = 'Tibolona'; group = 'CLIMATIX'; filters = @(@{ productsLike = @('CLIMATIX') }); sieProducts = @('CLIMATIX (SIE)') }
}

$familyOrder = @(
  'Totales',
  'ISIS FREE',
  'ISIS',
  'ISIS MINI',
  'ISIS MINI 24',
  'SIDERBLUT COMPLEX',
  'SIDERBLUT',
  'SIDERBLUT POLI',
  'SIDERBLUT FOLICO',
  'TRIP D3',
  'TRIP +45',
  'TRIP D3 PLUS',
  'TRIP MAGNESIO',
  'DELTROX NF',
  'CALCIO BASE DUPOMAR',
  'CALCIO BASE DUPOMAR D',
  'CALCIO CITRATO DUPOMAR D3 200',
  'CALCIO CITRATO DUPOMAR D3 400',
  'CLIMATIX'
)

$dddMarketConfig = [ordered]@{
  'ISIS FREE' = @{ family = 'ISIS FREE'; keywords = @('ISIS FREE') }
  'ISIS' = @{ family = 'ISIS'; keywords = @('ISIS') }
  'ISIS MINI' = @{ family = 'ISIS MINI'; keywords = @('ISIS MINI') }
  'ISIS MINI 24' = @{ family = 'ISIS MINI 24'; keywords = @('ISIS MINI 24') }
  'SIDERBLUT COMPLEX' = @{ family = 'SIDERBLUT COMPLEX'; keywords = @('SIDERBLUT COMPLEX') }
  'SIDERBLUT' = @{ family = 'SIDERBLUT'; keywords = @('SIDERBLUT') }
  'SIDERBLUT POLI' = @{ family = 'SIDERBLUT POLI'; keywords = @('SIDERBLUT POLI') }
  'SIDERBLUT FOLICO' = @{ family = 'SIDERBLUT FOLICO'; keywords = @('SIDERBLUT FOLICO') }
  'TRIP D3' = @{ family = 'TRIP D3'; keywords = @('TRIP D3') }
  'TRIP +45' = @{ family = 'TRIP +45'; keywords = @('TRIP +45') }
  'TRIP D3 PLUS' = @{ family = 'TRIP D3 PLUS'; keywords = @('TRIP D3 PLUS') }
  'TRIP MAGNESIO' = @{ family = 'TRIP MAGNESIO'; keywords = @('TRIP MAGNESIO') }
  'DELTROX NF' = @{ family = 'DELTROX NF'; keywords = @('DELTROX NF', 'DELTROX') }
  'CALCIO BASE DUPOMAR' = @{ family = 'CALCIO BASE DUPOMAR'; keywords = @('CALCIO BASE DUPOMAR') }
  'CALCIO BASE DUPOMAR D' = @{ family = 'CALCIO BASE DUPOMAR D'; keywords = @('CALCIO BASE DUPOMAR D') }
  'CALCIO CITRATO DUPOMAR D3 200' = @{ family = 'CALCIO CITRATO DUPOMAR D3 200'; keywords = @('CALCIO CITRATO DUPOMAR D3 200') }
  'CALCIO CITRATO DUPOMAR D3 400' = @{ family = 'CALCIO CITRATO DUPOMAR D3 400'; keywords = @('CALCIO CITRATO DUPOMAR D3 400') }
  'CLIMATIX' = @{ family = 'CLIMATIX'; keywords = @('CLIMATIX') }
}

function Get-MatchingPath {
  param(
    [string]$Dir,
    [string]$Include,
    [string]$Exclude = ''
  )

  $items = Get-ChildItem -LiteralPath $Dir | Where-Object { $_.Name -like $Include }
  if ($Exclude) {
    $items = $items | Where-Object { $_.Name -notlike $Exclude }
  }

  $match = $items | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $match) {
    throw "No se encontro un archivo que coincida con '$Include' en '$Dir'."
  }

  return $match.FullName
}

function Normalize-Text {
  param([object]$Value)

  if ($null -eq $Value) {
    return ''
  }

  return ([string]$Value).Trim()
}

function To-Number {
  param([object]$Value)

  if ($null -eq $Value) {
    return 0.0
  }

  if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal] -or
      $Value -is [int] -or $Value -is [long]) {
    return [double]$Value
  }

  $text = ([string]$Value).Trim()
  if (-not $text -or $text -eq '-') {
    return 0.0
  }

  $parsed = 0.0
  if ([double]::TryParse($text, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
    return $parsed
  }

  $text = $text.Replace('.', '').Replace('%', '').Replace(',', '.')
  if ([double]::TryParse($text, [System.Globalization.NumberStyles]::Any, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
    return $parsed
  }

  return 0.0
}

function Normalize-MonthLabel {
  param([object]$Value)

  if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal] -or
      $Value -is [int] -or $Value -is [long]) {
    try {
      $date = [datetime]::FromOADate([double]$Value)
      return '{0}-{1}' -f $monthLabel[$date.Month], $date.Year
    }
    catch {
    }
  }

  $raw = Normalize-Text $Value
  if (-not $raw) {
    return ''
  }

  if ($raw -match '^([A-Za-z]+)-(\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndex.ContainsKey($mon)) {
      return '{0}-{1}' -f $monthLabel[$monthIndex[$mon]], $year
    }
  }

  return $raw
}

function Get-MonthSortValue {
  param([string]$Label)

  if ($Label -match '^([A-Za-z]+)-(\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndex.ContainsKey($mon)) {
      return ($year * 100) + $monthIndex[$mon]
    }
  }

  return 0
}

function Sort-Months {
  param([string[]]$Months)

  return $Months | Sort-Object { Get-MonthSortValue $_ }
}

function Normalize-MonthLabelEn {
  param([object]$Value)

  if ($Value -is [double] -or $Value -is [single] -or $Value -is [decimal] -or
      $Value -is [int] -or $Value -is [long]) {
    try {
      $date = [datetime]::FromOADate([double]$Value)
      return '{0} {1}' -f $monthLabelEn[$date.Month], $date.Year
    }
    catch {
    }
  }

  $raw = Normalize-Text $Value
  if (-not $raw) {
    return ''
  }

  $raw = $raw -replace '\s+', ' '
  $rawLower = $raw.ToLower()

  if ($rawLower -match '^([a-z]{3,4})-(\d{4})$') {
    $mon = $matches[1]
    $year = [int]$matches[2]
    if ($monthIndex.ContainsKey($mon)) {
      return '{0} {1}' -f $monthLabelEn[$monthIndex[$mon]], $year
    }
  }

  if ($rawLower -match '^(\d{1,2})/(\d{1,2})/(\d{4})$') {
    $month = [int]$matches[1]
    $year = [int]$matches[3]
    if ($monthLabelEn.ContainsKey($month)) {
      return '{0} {1}' -f $monthLabelEn[$month], $year
    }
  }

  if ($rawLower -match '^([a-z]{3}) (\d{4})$') {
    $mon = $matches[1]
    $year = [int]$matches[2]
    if ($monthIndexEn.ContainsKey($mon)) {
      return '{0} {1}' -f $monthLabelEn[$monthIndexEn[$mon]], $year
    }
  }

  return $raw
}

function Get-MonthSortValueEn {
  param([string]$Label)

  if ($Label -match '^([A-Za-z]{3}) (\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndexEn.ContainsKey($mon)) {
      return ($year * 100) + $monthIndexEn[$mon]
    }
  }

  return 0
}

function Sort-MonthsEn {
  param([string[]]$Months)

  return $Months | Sort-Object { Get-MonthSortValueEn $_ }
}

function Get-YtdSumEn {
  param(
    [hashtable]$MonthlyMap,
    [string]$MonthKey
  )

  if (-not $MonthlyMap -or -not $MonthKey -or $MonthKey -notmatch '^([A-Za-z]{3}) (\d{4})$') {
    return 0.0
  }

  $targetMonth = $monthIndexEn[$matches[1].ToLower()]
  $targetYear = [int]$matches[2]
  $sum = 0.0
  foreach ($key in $MonthlyMap.Keys) {
    if ($key -match '^([A-Za-z]{3}) (\d{4})$') {
      $month = $monthIndexEn[$matches[1].ToLower()]
      $year = [int]$matches[2]
      if ($year -eq $targetYear -and $month -le $targetMonth) {
        $sum += [double]$MonthlyMap[$key]
      }
    }
  }
  return $sum
}

function Get-MatSumEn {
  param(
    [hashtable]$MonthlyMap,
    [string[]]$OrderedKeys,
    [string]$MonthKey
  )

  if (-not $MonthlyMap -or -not $OrderedKeys -or -not $MonthKey) {
    return 0.0
  }

  $idx = [array]::IndexOf($OrderedKeys, $MonthKey)
  if ($idx -lt 0) {
    return 0.0
  }

  $start = [Math]::Max(0, $idx - 11)
  $sum = 0.0
  for ($i = $start; $i -le $idx; $i++) {
    $monthValue = 0.0
    if ($MonthlyMap.ContainsKey($OrderedKeys[$i])) {
      $monthValue = [double]$MonthlyMap[$OrderedKeys[$i]]
    }
    $sum += $monthValue
  }
  return $sum
}

function Get-QuarterSortValue {
  param([string]$Label)

  if ($Label -match '^(Q[1-4]) (\d{4})$') {
    $quarter = @('Q1', 'Q2', 'Q3', 'Q4').IndexOf($matches[1])
    $year = [int]$matches[2]
    return ($year * 10) + $quarter
  }

  return 0
}

function Sort-QuarterLabels {
  param([string[]]$Labels)

  return $Labels | Sort-Object { Get-QuarterSortValue $_ }
}

function Convert-QuarterLabelFromHeader {
  param([string]$Header)

  $text = (Normalize-Text $Header) -replace '\s+', ' '
  if (-not $text) {
    return ''
  }

  $text = $text -replace '\n', ' '
  $text = $text -replace '\r', ' '
  $endMonthRaw = ''
  $year = 0
  if ($text -match '([A-Za-z]{3,4})\s+\d{4}\s+to\s+([A-Za-z]{3,4})\s+(\d{4})') {
    $endMonthRaw = $matches[2].Substring(0, 3).ToLower()
    $year = [int]$matches[3]
  }
  elseif ($text -match '([A-Za-z]{3,4})\s+to\s+([A-Za-z]{3,4})\s+(\d{4})') {
    $endMonthRaw = $matches[2].Substring(0, 3).ToLower()
    $year = [int]$matches[3]
  }

  if ($endMonthRaw) {
    $month = 0
    if ($monthIndex.ContainsKey($endMonthRaw)) {
      $month = $monthIndex[$endMonthRaw]
    }
    elseif ($monthIndexEn.ContainsKey($endMonthRaw)) {
      $month = $monthIndexEn[$endMonthRaw]
    }
    if ($month -gt 0) {
      $quarter = switch ($month) {
        2 { 'Q1' }
        5 { 'Q2' }
        8 { 'Q3' }
        11 { 'Q4' }
        default { '' }
      }
      if ($quarter) {
        return "$quarter $year"
      }
    }
  }

  return ''
}

function Normalize-ProductKey {
  param([object]$Value)

  $text = (Normalize-Text $Value).ToUpper()
  if (-not $text) {
    return ''
  }

  $text = $text -replace '\([^)]*\)', ''
  $text = $text -replace '[%./,+-]', ' '
  $text = $text -replace '\s+', ' '
  return $text.Trim()
}

function Resolve-MujerFamily {
  param(
    [string]$Candidate,
    [hashtable]$MasterMap
  )

  $lookup = Normalize-ProductKey $Candidate
  if ($lookup -and $MasterMap.ContainsKey($lookup)) {
    return $MasterMap[$lookup]
  }

  $probe = (Normalize-Text $Candidate).ToUpper()
  if (-not $probe) { return '' }
  if ($probe.Contains('ISIS FREE') -or $probe -eq 'DROSPIRENONA') { return 'ISIS FREE' }
  if ($probe.Contains('ISIS MINI 24')) { return 'ISIS MINI 24' }
  if ($probe.Contains('ISIS MINI')) { return 'ISIS MINI' }
  if ($probe.Contains('ISIS') -or $probe.Contains('ETINILESTRADIOL')) { return 'ISIS' }
  if ($probe.Contains('SIDERBLUT FOLIC')) { return 'SIDERBLUT FOLICO' }
  if ($probe.Contains('SIDERBLUT POLI')) { return 'SIDERBLUT POLI' }
  if ($probe.Contains('SIDERBLUT COMPLEX')) { return 'SIDERBLUT COMPLEX' }
  if ($probe.Contains('SIDERBLUT')) { return 'SIDERBLUT' }
  if ($probe.Contains('TRIP MAGNESIO')) { return 'TRIP MAGNESIO' }
  if ($probe.Contains('TRIP +45')) { return 'TRIP +45' }
  if ($probe.Contains('TRIP D3 PLUS')) { return 'TRIP D3 PLUS' }
  if ($probe.Contains('TRIP D3') -or $probe.Contains('TRIP')) { return 'TRIP D3' }
  if ($probe.Contains('DELTROX')) { return 'DELTROX NF' }
  if ($probe.Contains('CALCIO CITRATO') -and $probe.Contains('400')) { return 'CALCIO CITRATO DUPOMAR D3 400' }
  if ($probe.Contains('CALCIO CITRATO')) { return 'CALCIO CITRATO DUPOMAR D3 200' }
  if ($probe.Contains('CALCIO BASE') -and ($probe.Contains(' D ') -or $probe.EndsWith(' D') -or $probe.Contains(' D3'))) {
    if ($probe.Contains('400')) { return 'CALCIO CITRATO DUPOMAR D3 400' }
    if ($probe.Contains('200')) { return 'CALCIO CITRATO DUPOMAR D3 200' }
    return 'CALCIO BASE DUPOMAR D'
  }
  if ($probe.Contains('CALCIO BASE')) { return 'CALCIO BASE DUPOMAR' }
  if ($probe.Contains('CLIMATIX')) { return 'CLIMATIX' }
  return ''
}

function Test-NormalizedProductMatch {
  param(
    [string]$Left,
    [string]$Right
  )

  if (-not $Left -or -not $Right) {
    return $false
  }

  return $Left -eq $Right -or $Left.StartsWith($Right) -or $Right.StartsWith($Left)
}

function Classify-StockStatus {
  param([nullable[double]]$Days)

  if ($null -eq $Days) { return 'nd' }
  if ($Days -le 0) { return 'quiebre' }
  if ($Days -lt 7) { return 'critico' }
  if ($Days -lt 14) { return 'bajo' }
  if ($Days -lt 20) { return 'alerta' }
  return 'ok'
}

function Get-WorstStockStatus {
  param([string[]]$Statuses)

  $priority = @('quiebre', 'critico', 'bajo', 'alerta', 'ok', 'nd')
  foreach ($status in $priority) {
    if ($Statuses -contains $status) {
      return $status
    }
  }

  return 'nd'
}

function Get-CoverageLabel {
  param([string]$MonthKey)

  if ($MonthKey -match '^([A-Za-z]{3}) (\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = $matches[2]
    if ($monthIndexEn.ContainsKey($mon)) {
      return '{0} {1}' -f $monthLabel[$monthIndexEn[$mon]], $year.Substring(2)
    }
  }

  return $MonthKey
}

function Test-PMMarketMatch {
  param(
    [hashtable]$Config,
    [string]$Product,
    [string]$Molecule,
    [string]$Atc
  )

  $productUpper = (Normalize-Text $Product).ToUpper()
  $moleculeUpper = (Normalize-Text $Molecule).ToUpper()
  $atcUpper = (Normalize-Text $Atc).ToUpper()

  foreach ($filter in $Config.filters) {
    $moleculeMatch = $true
    $atcMatch = $true
    $productMatch = $true

    if ($filter.ContainsKey('molecules') -and $filter.molecules.Count -gt 0) {
      $moleculeMatch = $false
      foreach ($candidate in $filter.molecules) {
        $candidateUpper = $candidate.ToUpper()
        if ($moleculeUpper -eq $candidateUpper -or $moleculeUpper.Contains($candidateUpper)) {
          $moleculeMatch = $true
          break
        }
      }
    }

    if ($filter.ContainsKey('atcStarts') -and $filter.atcStarts.Count -gt 0) {
      $atcMatch = $false
      foreach ($candidate in $filter.atcStarts) {
        if ($atcUpper.StartsWith($candidate.ToUpper())) {
          $atcMatch = $true
          break
        }
      }
    }

    if ($filter.ContainsKey('productsLike') -and $filter.productsLike.Count -gt 0) {
      $productMatch = $false
      foreach ($candidate in $filter.productsLike) {
        if ($productUpper.Contains($candidate.ToUpper())) {
          $productMatch = $true
          break
        }
      }
    }

    if ($moleculeMatch -and $atcMatch -and $productMatch) {
      return $true
    }
  }

  return $false
}

function Round-Number {
  param(
    [double]$Value,
    [int]$Digits = 1
  )

  return [math]::Round($Value, $Digits)
}

function Ensure-Map {
  param(
    [hashtable]$Map,
    [string]$Key
  )

  if (-not $Map.ContainsKey($Key)) {
    $Map[$Key] = @{}
  }
}

function Ensure-OrderedMap {
  param(
    [System.Collections.Specialized.OrderedDictionary]$Map,
    [string]$Key,
    [object]$Value
  )

  if (-not $Map.Contains($Key)) {
    $Map.Add($Key, $Value)
  }
}

function Ensure-NestedMetric {
  param(
    [hashtable]$Map,
    [string]$Key
  )

  if (-not $Map.ContainsKey($Key)) {
    $Map[$Key] = @{
      total = 0.0
      sie = 0.0
    }
  }
}

function Get-LastNonZeroMonth {
  param(
    [string[]]$Months,
    [double[]]$Values
  )

  for ($i = $Values.Count - 1; $i -ge 0; $i--) {
    if ($Values[$i] -gt 0) {
      return $Months[$i]
    }
  }

  return ''
}

function Get-YtdSum {
  param(
    [string[]]$Months,
    [double[]]$Values,
    [int]$Year,
    [string]$CutMonth
  )

  $cutValue = Get-MonthSortValue $CutMonth
  $sum = 0.0
  for ($i = 0; $i -lt $Months.Count; $i++) {
    if ($Months[$i] -match "-$Year$" -and (Get-MonthSortValue $Months[$i]) -le $cutValue) {
      $sum += $Values[$i]
    }
  }

  return [math]::Round($sum, 0)
}

function Convert-MetricMap {
  param([hashtable]$Map)

  $rows = foreach ($key in ($Map.Keys | Sort-Object)) {
    $item = $Map[$key]
    $share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    [pscustomobject][ordered]@{
      name = $key
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = $share
    }
  }

  return @($rows)
}

if (-not (Test-Path -LiteralPath $SourceDir)) {
  throw "La carpeta de fuentes no existe: $SourceDir"
}

$rxOverridePath = 'C:\Users\camarinaro\Downloads\RECETAS LINEA MUJER MARCAS.xlsx'
$stockOverridePath = 'C:\Users\camarinaro\Downloads\STOCK Y VENTAS LINEA MUJER.xlsx'
$convCurrentOverridePath = 'C:\Users\camarinaro\Downloads\CONVENIOS POR OS.xlsx'
$convPrevOverridePath = 'C:\Users\camarinaro\Downloads\Detalle consumos y aportes por convenio - 10 de abril de 2026.xlsx'
$dddOverridePath = 'C:\Users\camarinaro\Downloads\DDD LINEA MUJER.xlsx'
$priceOverridePath = 'C:\Users\camarinaro\Downloads\PRECIO LINEA MUJER 10-04-26.xlsx'

$budgetPath = Get-MatchingPath -Dir $SourceDir -Include 'ESTIMADOS VIGENTES_CARLITOS.xlsx'
$ventaInternaPath = Get-MatchingPath -Dir $SourceDir -Include 'VENTA INTERNA_CARLITOS.xlsx'
$rxPath = if (Test-Path -LiteralPath $rxOverridePath) { $rxOverridePath } else { 'C:\Users\camarinaro\Downloads\RECETAS_CARLITOS 1.xlsx' }
if (-not (Test-Path -LiteralPath $rxPath)) { $rxPath = Get-MatchingPath -Dir $SourceDir -Include 'RECETAS_CARLITOS.xlsx' }
$stockPath = if (Test-Path -LiteralPath $stockOverridePath) { $stockOverridePath } else { Get-MatchingPath -Dir $SourceDir -Include 'STOCK Y VENTAS_ CARLITOS.xlsx' }
$channelPath = Get-MatchingPath -Dir $SourceDir -Include 'Convenios vs mostrador*'
$conv2024Path = if (Test-Path -LiteralPath $convPrevOverridePath) { $convPrevOverridePath } else { Get-MatchingPath -Dir $SourceDir -Include 'CONVENIOS VS MOSTRADOS 2024_CARLITOS.xlsx' }
$conv2025Path = if (Test-Path -LiteralPath $convCurrentOverridePath) { $convCurrentOverridePath } else { Get-MatchingPath -Dir $SourceDir -Include 'Convenios vs mostrador _CARLITOS.xlsx' }
$maestroPath = Get-MatchingPath -Dir $SourceDir -Include 'MAESTRO_COM_CARLITOS.xlsx'
$dddPath = if (Test-Path -LiteralPath $dddOverridePath) { $dddOverridePath } else { Get-MatchingPath -Dir $SourceDir -Include 'IQUVIA_VENTAS.xlsx' }
$pmPath = Get-MatchingPath -Dir $(if ($IqviaDir) { $IqviaDir } else { $SourceDir }) -Include $(if ($IqviaPattern) { $IqviaPattern } else { 'IQUVIA_VENTAS.xlsx' })
$pricePath = if (Test-Path -LiteralPath $priceOverridePath) { $priceOverridePath } else { Get-MatchingPath -Dir $SourceDir -Include 'PRECIOS_CARLITOS.xlsx' }

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

function Open-Matrix {
  param(
    [object]$Excel,
    [string]$Path
  )

  $ws = $null
  $usedRange = $null
  $wb = $Excel.Workbooks.Open($Path)
  try {
    $ws = $wb.Worksheets.Item(1)
    $usedRange = $ws.UsedRange
    $value = $usedRange.Value2
    return ,$value
  }
  finally {
    if ($null -ne $usedRange) {
      [System.Runtime.InteropServices.Marshal]::ReleaseComObject($usedRange) | Out-Null
    }
    if ($null -ne $ws) {
      [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws) | Out-Null
    }
    $wb.Close($false)
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
  }
}

try {
  $budgetMatrix = Open-Matrix -Excel $excel -Path $budgetPath
  $ventaInternaMatrix = Open-Matrix -Excel $excel -Path $ventaInternaPath
  try {
    $rxMatrix = Open-Matrix -Excel $excel -Path $rxPath
  }
  catch {
    $rxMatrix = $null
  }
  $stockMatrix = Open-Matrix -Excel $excel -Path $stockPath
  $channelMatrix = Open-Matrix -Excel $excel -Path $channelPath
  $conv2024Matrix = Open-Matrix -Excel $excel -Path $conv2024Path
  $conv2025Matrix = Open-Matrix -Excel $excel -Path $conv2025Path
  $maestroMatrix = Open-Matrix -Excel $excel -Path $maestroPath
  $dddMatrix = Open-Matrix -Excel $excel -Path $dddPath
  $pmMatrix = Open-Matrix -Excel $excel -Path $pmPath
  $priceMatrix = Open-Matrix -Excel $excel -Path $pricePath
}
finally {
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}

# --- Columnas del PM por NOMBRE de header (NO por posicion) ------------------
# El export de IQVIA reordeno sus columnas: el AR_PM viejo (317 cols) traia
# Manufacturer/Product/Pack en 1/2/3, y el de Ago-2026 (329 cols) trae
# Pack/Manufacturer/ATC IV/Ph.Forms III/Product. Leerlas por posicion escribia
# el laboratorio en 'prod' y el pack en 'manuf' -> is_sie caia a false en TODOS
# los productos y NINGUNA marca SIE quedaba en mol_perf, sin mover una sola
# suma (el audit daba 16.626/16.634 con las 4 lineas vacias de SIE).
$pmColProduct = $null; $pmColManuf = $null; $pmColPack = $null
for ($_pc = 1; $_pc -le [Math]::Min(12, $pmMatrix.GetLength(1)); $_pc++) {
  $_ph = ((Normalize-Text $pmMatrix[1, $_pc]) -replace '\s+', ' ').Trim().ToUpper()
  if (-not $_ph) { continue }
  if ($_ph -eq 'PRODUCT' -and $null -eq $pmColProduct) { $pmColProduct = $_pc }
  elseif ($_ph -eq 'MANUFACTURER' -and $null -eq $pmColManuf) { $pmColManuf = $_pc }
  elseif ($_ph -eq 'PACK' -and $null -eq $pmColPack) { $pmColPack = $_pc }
}
if ($null -eq $pmColProduct -or $null -eq $pmColManuf) {
  # Sin headers canonicos (ej. slices legacy) volvemos a las posiciones viejas,
  # pero RUIDOSAMENTE: si el layout cambio otra vez esto tiene que verse.
  Write-Warning "PM: no encontre los headers Product/Manufacturer en la fila 1; caigo a las posiciones legacy 1/2/3. Verificar que 'prod' no quede con el laboratorio."
  if ($null -eq $pmColManuf)   { $pmColManuf = 1 }
  if ($null -eq $pmColProduct) { $pmColProduct = 2 }
  if ($null -eq $pmColPack)    { $pmColPack = 3 }
}
if ($null -eq $pmColPack) { $pmColPack = 3 }
Write-Host ("   PM cols por header: Product={0} Manufacturer={1} Pack={2}" -f $pmColProduct, $pmColManuf, $pmColPack) -ForegroundColor DarkGray
# ----------------------------------------------------------------------------

$rxMasterMap = @{}
$budgetMasterMap = @{}
for ($r = 3; $r -le $maestroMatrix.GetLength(0); $r++) {
  $familySap = Normalize-Text $maestroMatrix[$r, 5]
  $nameIqvia = Normalize-Text $maestroMatrix[$r, 4]
  $presSap = Normalize-Text $maestroMatrix[$r, 9]
  $familyCanonical = ''
  if ($familySap) {
    $familyCanonical = Resolve-MujerFamily -Candidate $familySap -MasterMap @{}
    if (-not $familyCanonical) { $familyCanonical = Resolve-MujerFamily -Candidate $nameIqvia -MasterMap @{} }
    if (-not $familyCanonical) { $familyCanonical = Resolve-MujerFamily -Candidate $presSap -MasterMap @{} }
    if (-not $familyCanonical) { $familyCanonical = $familySap.ToUpper() }
    if ($nameIqvia) { $rxMasterMap[(Normalize-ProductKey $nameIqvia)] = $familyCanonical }
    if ($presSap) { $rxMasterMap[(Normalize-ProductKey $presSap)] = $familyCanonical }
    if ($presSap) { $budgetMasterMap[(Normalize-ProductKey $presSap)] = $familyCanonical }
  }
}

function Convert-MujerRecetasMatrix {
  param(
    [object[,]]$Matrix,
    [hashtable]$MasterMap
  )

  if (-not $Matrix -or $Matrix.GetLength(0) -lt 3 -or (Normalize-Text $Matrix[2, 4]) -ne 'Cant. Recetas') {
    return ,$Matrix
  }

  $months = New-Object 'System.Collections.Generic.List[string]'
  for ($c = 4; $c -le $Matrix.GetLength(1); $c += 2) {
    $month = Normalize-MonthLabel $Matrix[1, $c]
    if ($month) {
      $months.Add($month)
    }
  }

  $familyTotals = @{}
  $brandRows = @{}
  for ($r = 3; $r -le $Matrix.GetLength(0); $r++) {
    $market = Normalize-Text $Matrix[$r, 1]
    $molecule = Normalize-Text $Matrix[$r, 2]
    $brand = Normalize-Text $Matrix[$r, 3]
    if (-not $brand) {
      continue
    }

    $family = Resolve-MujerFamily -Candidate $brand -MasterMap $MasterMap
    if (-not $family) { $family = Resolve-MujerFamily -Candidate $market -MasterMap $MasterMap }
    if (-not $family) { $family = Resolve-MujerFamily -Candidate $molecule -MasterMap $MasterMap }
    if (-not $family -or -not ($dashboardFamilyOrder -contains $family)) {
      continue
    }

    if (-not $familyTotals.ContainsKey($family)) {
      $familyTotals[$family] = @{
        prescriptions = @(for ($i = 0; $i -lt $months.Count; $i++) { 0.0 })
        doctors = @(for ($i = 0; $i -lt $months.Count; $i++) { 0.0 })
      }
    }

    $brandName = if ($brand -eq 'Totales') { '' } else { $brand }
    if ($brandName) {
      if (-not $brandRows.ContainsKey($family)) {
        $brandRows[$family] = @{}
      }
      if (-not $brandRows[$family].ContainsKey($brandName)) {
        $brandRows[$family][$brandName] = @{
          prescriptions = @(for ($i = 0; $i -lt $months.Count; $i++) { 0.0 })
          doctors = @(for ($i = 0; $i -lt $months.Count; $i++) { 0.0 })
        }
      }
    }

    $idx = 0
    for ($c = 4; $c -le $Matrix.GetLength(1) -and $idx -lt $months.Count; $c += 2) {
      $rxValue = To-Number $Matrix[$r, $c]
      $docValue = if (($c + 1) -le $Matrix.GetLength(1)) { To-Number $Matrix[$r, ($c + 1)] } else { 0.0 }
      $familyTotals[$family].prescriptions[$idx] += $rxValue
      $familyTotals[$family].doctors[$idx] += $docValue
      if ($brandName) {
        $brandRows[$family][$brandName].prescriptions[$idx] += $rxValue
        $brandRows[$family][$brandName].doctors[$idx] += $docValue
      }
      $idx++
    }
  }

  $outputRows = New-Object System.Collections.Generic.List[object]
  foreach ($family in $dashboardFamilyOrder) {
    if (-not $familyTotals.ContainsKey($family)) {
      continue
    }
    $outputRows.Add([pscustomobject]@{
      family = $family
      brand = 'Totales'
      prescriptions = $familyTotals[$family].prescriptions
      doctors = $familyTotals[$family].doctors
    }) | Out-Null

    if ($brandRows.ContainsKey($family)) {
      foreach ($brandName in ($brandRows[$family].Keys | Sort-Object)) {
        $outputRows.Add([pscustomobject]@{
          family = $family
          brand = $brandName
          prescriptions = $brandRows[$family][$brandName].prescriptions
          doctors = $brandRows[$family][$brandName].doctors
        }) | Out-Null
      }
    }
  }

  $out = [Array]::CreateInstance([object], @([int](2 + $outputRows.Count), [int](3 + ($months.Count * 2))), @(1, 1))
  for ($i = 0; $i -lt $months.Count; $i++) {
    $out[1, (4 + ($i * 2))] = $months[$i]
    $out[1, (5 + ($i * 2))] = $months[$i]
  }
  $row = 3
  foreach ($item in $outputRows) {
    $out[$row, 2] = $item.family
    $out[$row, 3] = $item.brand
    for ($i = 0; $i -lt $months.Count; $i++) {
      $out[$row, (4 + ($i * 2))] = [math]::Round([double]$item.prescriptions[$i], 0)
      $out[$row, (5 + ($i * 2))] = [math]::Round([double]$item.doctors[$i], 0)
    }
    $row++
  }

  return ,$out
}

function Convert-MujerConveniosMatrix {
  param([object[,]]$Matrix)

  if (-not $Matrix -or $Matrix.GetLength(0) -lt 2 -or (Normalize-Text $Matrix[1, 4]) -ne 'ObraSocial1') {
    return ,$Matrix
  }

  $rows = New-Object System.Collections.Generic.List[object]
  for ($r = 2; $r -le $Matrix.GetLength(0); $r++) {
    $family = Normalize-Text $Matrix[$r, 3]
    $os1 = Normalize-Text $Matrix[$r, 4]
    $os2 = Normalize-Text $Matrix[$r, 5]
    $product = Normalize-Text $Matrix[$r, 6]
    $units = To-Number $Matrix[$r, 7]
    if (-not $family -or -not $os1 -or $units -le 0) {
      continue
    }
    if ($os2 -and $os2 -ne 'Totales') {
      continue
    }
    if ($product -and $product -ne 'Totales') {
      continue
    }
    $resolvedFamily = Resolve-MujerFamily -Candidate $family -MasterMap $budgetMasterMap
    if (-not $resolvedFamily) {
      $resolvedFamily = $family.ToUpper()
    }
    if (-not ($familyOrder -contains $resolvedFamily)) {
      continue
    }

    $rows.Add([pscustomobject]@{
      family = $resolvedFamily
      os = $os1
      units = [math]::Round($units, 0)
    }) | Out-Null
  }

  $out = [Array]::CreateInstance([object], @([int](1 + $rows.Count), [int]5), @(1, 1))
  $out[1, 3] = 'Familia'
  $out[1, 4] = 'OS'
  $out[1, 5] = 'Units'
  $row = 2
  foreach ($item in $rows) {
    $out[$row, 3] = $item.family
    $out[$row, 4] = $item.os
    $out[$row, 5] = $item.units
    $row++
  }
  return ,$out
}

$rxMatrix = Convert-MujerRecetasMatrix -Matrix $rxMatrix -MasterMap $rxMasterMap
$conv2024Matrix = Convert-MujerConveniosMatrix -Matrix $conv2024Matrix
$conv2025Matrix = Convert-MujerConveniosMatrix -Matrix $conv2025Matrix

if (-not $rxMatrix) {
  $rxMonthsFallback = @(
    'Ene-2025','Feb-2025','Mar-2025','Abr-2025','May-2025','Jun-2025',
    'Jul-2025','Ago-2025','Sep-2025','Oct-2025','Nov-2025','Dic-2025',
    'Ene-2026','Feb-2026','Mar-2026','Abr-2026','May-2026','Jun-2026',
    'Jul-2026','Ago-2026','Sep-2026','Oct-2026','Nov-2026','Dic-2026'
  )
  $rows = 3 + $dashboardFamilyOrder.Count
  $cols = 4 + ($rxMonthsFallback.Count * 2)
  $rxMatrix = New-Object 'object[,]' $rows, $cols
  $rxMatrix[1,1] = ''
  $rxMatrix[1,2] = ''
  $rxMatrix[1,3] = ''
  for ($i = 0; $i -lt $rxMonthsFallback.Count; $i++) {
    $rxMatrix[1, (4 + ($i * 2))] = $rxMonthsFallback[$i]
    $rxMatrix[1, (5 + ($i * 2))] = $rxMonthsFallback[$i]
  }
  $rxMatrix[2,1] = 'Totales'
  $rxMatrix[2,2] = 'Totales'
  $rxMatrix[2,3] = 'Totales'
  for ($i = 0; $i -lt $rxMonthsFallback.Count; $i++) {
    $rxMatrix[2, (4 + ($i * 2))] = 0
    $rxMatrix[2, (5 + ($i * 2))] = 0
  }
  for ($r = 0; $r -lt $dashboardFamilyOrder.Count; $r++) {
    $row = 3 + $r
    $market = $dashboardFamilyOrder[$r]
    $rxMatrix[$row,1] = $market
    $rxMatrix[$row,2] = $market
    $rxMatrix[$row,3] = $market
    for ($i = 0; $i -lt $rxMonthsFallback.Count; $i++) {
      $rxMatrix[$row, (4 + ($i * 2))] = 0
      $rxMatrix[$row, (5 + ($i * 2))] = 0
    }
  }
}

$budgetMonths = @()
for ($c = 5; $c -le $budgetMatrix.GetLength(1); $c++) {
  $budgetMonths += Normalize-MonthLabel $budgetMatrix[1, $c]
}

$budgetFamilies = [ordered]@{}
$budgetProducts = [ordered]@{}
$budgetTotalsActual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
$budgetTotalsBudget = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })

for ($r = 2; $r -le $budgetMatrix.GetLength(0); $r++) {
  $line = Normalize-Text $budgetMatrix[$r, 2]
  if ($line -and $line.ToUpper() -ne 'MUJER') {
    continue
  }
  $product = Normalize-Text $budgetMatrix[$r, 4]
  $family = Resolve-MujerFamily -Candidate $product -MasterMap $budgetMasterMap
  if (-not $family) {
    continue
  }

  if (-not $budgetFamilies.Contains($family)) {
    $budgetFamilies[$family] = [ordered]@{
      actual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
      budget = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
      compliance = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 100.0 })
    }
  }

  $rowActual = New-Object System.Collections.Generic.List[double]
  for ($c = 5; $c -le $budgetMatrix.GetLength(1); $c++) {
    $value = To-Number $budgetMatrix[$r, $c]
    $idx = $c - 5
    $budgetFamilies[$family].actual[$idx] += $value
    $budgetFamilies[$family].budget[$idx] += $value
    $budgetTotalsActual[$idx] += $value
    $budgetTotalsBudget[$idx] += $value
    $rowActual.Add($value)
  }

  if (-not $product -or $product -eq 'Totales') {
    continue
  }

  if (-not $budgetProducts.Contains($family)) {
    $budgetProducts.Add($family, @())
  }

  $latestIndex = $rowActual.Count - 1
  while ($latestIndex -ge 0 -and $rowActual[$latestIndex] -le 0) {
    $latestIndex--
  }

  $budgetProducts[$family] += [pscustomobject][ordered]@{
    name = $product
    totalActual = [math]::Round(($rowActual | Measure-Object -Sum).Sum, 0)
    ytd2026 = Get-YtdSum -Months $budgetMonths -Values @($rowActual) -Year 2026 -CutMonth (Get-LastNonZeroMonth -Months $budgetMonths -Values @($rowActual))
    latestActual = if ($latestIndex -ge 0) { [math]::Round($rowActual[$latestIndex], 0) } else { 0 }
  }
}

$ventaInternaMonths = @()
for ($c = 7; $c -le $ventaInternaMatrix.GetLength(1); $c++) {
  $ventaInternaMonths += Normalize-MonthLabel $ventaInternaMatrix[2, $c]
}

$ventaInternaFamilies = @{}
for ($r = 3; $r -le $ventaInternaMatrix.GetLength(0); $r++) {
  $granFamilia = Normalize-Text $ventaInternaMatrix[$r, 2]
  $familia = Normalize-Text $ventaInternaMatrix[$r, 3]
  $producto = Normalize-Text $ventaInternaMatrix[$r, 4]
  $presentacion = Normalize-Text $ventaInternaMatrix[$r, 5]
  $resolvedFamily = Resolve-MujerFamily -Candidate $presentacion -MasterMap $budgetMasterMap
  if (-not $resolvedFamily) { $resolvedFamily = Resolve-MujerFamily -Candidate $producto -MasterMap $budgetMasterMap }
  if (-not $resolvedFamily) { $resolvedFamily = Resolve-MujerFamily -Candidate $familia -MasterMap $budgetMasterMap }
  if (-not $resolvedFamily) { $resolvedFamily = Resolve-MujerFamily -Candidate $granFamilia -MasterMap $budgetMasterMap }
  if (-not $resolvedFamily) { continue }

  if (-not $ventaInternaFamilies.ContainsKey($resolvedFamily)) {
    $ventaInternaFamilies[$resolvedFamily] = @(for ($i = 0; $i -lt $ventaInternaMonths.Count; $i++) { 0.0 })
  }

  for ($c = 7; $c -le $ventaInternaMatrix.GetLength(1); $c++) {
    $idx = $c - 7
    $ventaInternaFamilies[$resolvedFamily][$idx] += To-Number $ventaInternaMatrix[$r, $c]
  }
}

foreach ($family in $ventaInternaFamilies.Keys) {
  if (-not $budgetFamilies.Contains($family)) { continue }
  for ($i = 0; $i -lt $ventaInternaMonths.Count; $i++) {
    $monthKey = $ventaInternaMonths[$i]
    $budgetIdx = $budgetMonths.IndexOf($monthKey)
    if ($budgetIdx -ge 0) {
      $budgetFamilies[$family].actual[$budgetIdx] = [math]::Round($ventaInternaFamilies[$family][$i], 0)
    }
  }
}

$ventaInternaMonthSet = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($monthKey in $ventaInternaMonths) {
  $ventaInternaMonthSet.Add($monthKey) | Out-Null
}
for ($i = 0; $i -lt $budgetMonths.Count; $i++) {
  $monthKey = $budgetMonths[$i]
  if ($monthKey -match '-2026$' -and -not $ventaInternaMonthSet.Contains($monthKey)) {
    foreach ($family in $budgetFamilies.Keys) {
      if ($family -eq 'Totales') { continue }
      $budgetFamilies[$family].actual[$i] = 0.0
    }
  }
  if ($monthKey -like 'Total *') {
    foreach ($family in $budgetFamilies.Keys) {
      if ($family -eq 'Totales') { continue }
      $budgetFamilies[$family].actual[$i] = 0.0
    }
  }
}

$budgetTotalsActual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
foreach ($family in $budgetFamilies.Keys) {
  if ($family -eq 'Totales') { continue }
  for ($i = 0; $i -lt $budgetMonths.Count; $i++) {
    $budgetTotalsActual[$i] += [double]$budgetFamilies[$family].actual[$i]
  }
}

$budgetFamilies['Totales'] = [ordered]@{
  actual = @($budgetTotalsActual | ForEach-Object { [math]::Round($_, 0) })
  budget = @($budgetTotalsBudget | ForEach-Object { [math]::Round($_, 0) })
  compliance = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 100.0 })
}

$budgetCut = Get-LastNonZeroMonth -Months $budgetMonths -Values $budgetFamilies['Totales'].actual
foreach ($family in @($budgetProducts.Keys)) {
  $budgetProducts[$family] = @(
    $budgetProducts[$family] |
      Sort-Object -Property @{ Expression = 'ytd2026'; Descending = $true }, @{ Expression = 'totalActual'; Descending = $true } |
      Select-Object -First 8
  )
}

$stockMonths = @()
for ($c = 8; $c -le $stockMatrix.GetLength(1); $c += 4) {
  $stockMonths += Normalize-MonthLabel $stockMatrix[1, $c]
}

$stockFamilies = [ordered]@{}
$stockProducts = [ordered]@{}
$stockProductSeries = [ordered]@{}
for ($r = 3; $r -le $stockMatrix.GetLength(0); $r++) {
  $familyRaw = Normalize-Text $stockMatrix[$r, 2]
  $product = Normalize-Text $stockMatrix[$r, 3]
  $family = $familyRaw
  if ($familyRaw -and $familyRaw -ne 'Totales') {
    $family = Resolve-MujerFamily -Candidate $familyRaw -MasterMap $budgetMasterMap
    if (-not $family) { $family = Resolve-MujerFamily -Candidate $product -MasterMap $budgetMasterMap }
  }
  if (-not $family) {
    continue
  }

  $stockSeries = New-Object System.Collections.Generic.List[double]
  $salesSeries = New-Object System.Collections.Generic.List[double]
  $billingSeries = New-Object System.Collections.Generic.List[double]
  $daysSeries = New-Object System.Collections.Generic.List[double]

  for ($c = 8; $c -le $stockMatrix.GetLength(1); $c += 4) {
    $stockSeries.Add((To-Number $stockMatrix[$r, $c]))
    $salesSeries.Add((To-Number $stockMatrix[$r, ($c + 1)]))
    $billingSeries.Add((To-Number $stockMatrix[$r, ($c + 2)]))
    $daysSeries.Add((To-Number $stockMatrix[$r, ($c + 3)]))
  }

  if ($family -eq 'Totales' -or $product -eq 'Totales' -or -not $product) {
    Ensure-OrderedMap -Map $stockFamilies -Key $family -Value ([ordered]@{
      stock = @($stockSeries)
      sales = @($salesSeries)
      billing = @($billingSeries)
      days = @($daysSeries)
    })
    continue
  }

  if (-not ($familyOrder -contains $family)) {
    continue
  }

  if (-not $stockProducts.Contains($family)) {
    $stockProducts.Add($family, @())
  }

  $stockProductSeries[$product] = [ordered]@{
    family = $family
    stock = @($stockSeries)
    sales = @($salesSeries)
    billing = @($billingSeries)
    days = @($daysSeries)
  }

  $stockProducts[$family] += [pscustomobject][ordered]@{
    name = $product
    totalStock = [math]::Round((To-Number $stockMatrix[$r, 4]), 0)
    totalSales = [math]::Round((To-Number $stockMatrix[$r, 5]), 0)
    totalBilling = [math]::Round((To-Number $stockMatrix[$r, 6]), 0)
    totalDays = [math]::Round((To-Number $stockMatrix[$r, 7]), 0)
  }
}

$stockCut = Get-LastNonZeroMonth -Months $stockMonths -Values $stockFamilies['Totales'].sales
foreach ($family in @($stockProducts.Keys)) {
  $stockProducts[$family] = @(
    $stockProducts[$family] |
      Sort-Object -Property @{ Expression = 'totalSales'; Descending = $true }, @{ Expression = 'totalBilling'; Descending = $true } |
      Select-Object -First 8
  )
}

foreach ($family in $stockFamilies.Keys) {
  if (-not $budgetFamilies.Contains($family)) {
    continue
  }
  for ($i = 0; $i -lt $stockMonths.Count; $i++) {
    $monthKey = $stockMonths[$i]
    $budgetIdx = $budgetMonths.IndexOf($monthKey)
    if ($budgetIdx -ge 0) {
      $budgetFamilies[$family].actual[$budgetIdx] = [math]::Round([double]$stockFamilies[$family].sales[$i], 0)
    }
  }
}

$budgetTotalsActual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
foreach ($family in $budgetFamilies.Keys) {
  if ($family -eq 'Totales') { continue }
  for ($i = 0; $i -lt $budgetMonths.Count; $i++) {
    $budgetTotalsActual[$i] += [double]$budgetFamilies[$family].actual[$i]
  }
}

$budgetFamilies['Totales'] = [ordered]@{
  actual = @($budgetTotalsActual | ForEach-Object { [math]::Round($_, 0) })
  budget = @($budgetTotalsBudget | ForEach-Object { [math]::Round($_, 0) })
  compliance = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 100.0 })
}

$budgetCut = Get-LastNonZeroMonth -Months $budgetMonths -Values $budgetFamilies['Totales'].actual

$channelFamilies = [ordered]@{}
for ($r = 2; $r -le $channelMatrix.GetLength(0); $r++) {
  $family = Normalize-Text $channelMatrix[$r, 2]
  if (-not $family) {
    continue
  }

  $units = To-Number $channelMatrix[$r, 3]
  $convenioUnits = $units * (To-Number $channelMatrix[$r, 10])
  $mostradorUnits = $units - $convenioUnits

  Ensure-OrderedMap -Map $channelFamilies -Key $family -Value ([ordered]@{
    facturedUnits = [math]::Round($units, 0)
    convenioUnits = [math]::Round($convenioUnits, 0)
    mostradorUnits = [math]::Round($mostradorUnits, 0)
    convenioPct = Round-Number ((To-Number $channelMatrix[$r, 10]) * 100)
    mostradorPct = Round-Number ((To-Number $channelMatrix[$r, 11]) * 100)
    discountCommonPct = Round-Number ((To-Number $channelMatrix[$r, 12]) * 100)
    discountConvenioPct = Round-Number ((To-Number $channelMatrix[$r, 13]) * 100)
    discountTotalPct = Round-Number ((To-Number $channelMatrix[$r, 14]) * 100)
  })
}

$osAggregate = @{}
foreach ($family in $familyOrder) {
  $osAggregate[$family] = @{}
}
$osAggregate['Totales'] = @{}

foreach ($rowSet in @(
  @{ year = 2024; matrix = $conv2024Matrix },
  @{ year = 2025; matrix = $conv2025Matrix }
)) {
  $year = $rowSet.year
  $matrix = $rowSet.matrix

  for ($r = 2; $r -le $matrix.GetLength(0); $r++) {
    $family = Normalize-Text $matrix[$r, 3]
    $os = Normalize-Text $matrix[$r, 4]
    if (-not $family -or -not $os) {
      continue
    }

    $units = To-Number $matrix[$r, 5]
    foreach ($bucket in @($family, 'Totales')) {
      if (-not $osAggregate.ContainsKey($bucket)) {
        $osAggregate[$bucket] = @{}
      }
      if (-not $osAggregate[$bucket].ContainsKey($os)) {
        $osAggregate[$bucket][$os] = @{ units2024 = 0.0; units2025 = 0.0 }
      }
      if ($year -eq 2024) {
        $osAggregate[$bucket][$os].units2024 += $units
      }
      else {
        $osAggregate[$bucket][$os].units2025 += $units
      }
    }
  }
}

$osFamilies = [ordered]@{}
foreach ($family in ($osAggregate.Keys | Sort-Object { $familyOrder.IndexOf($_) })) {
  $rows = foreach ($os in $osAggregate[$family].Keys) {
    $item = $osAggregate[$family][$os]
    $deltaUnits = $item.units2025 - $item.units2024
    [pscustomobject][ordered]@{
      os = $os
      units2024 = [math]::Round($item.units2024, 0)
      units2025 = [math]::Round($item.units2025, 0)
      deltaUnits = [math]::Round($deltaUnits, 0)
    }
  }

  $total2025 = (($rows | ForEach-Object { [double]$_.units2025 } | Measure-Object -Sum).Sum)
  $prepared = @(
    $rows |
      Sort-Object -Property @{ Expression = 'units2025'; Descending = $true } |
      Select-Object -First 10 |
      ForEach-Object {
        $share = if ($total2025 -gt 0) { Round-Number (($_.units2025 / $total2025) * 100) } else { 0.0 }
        $deltaPct = if ($_.units2024 -gt 0) { Round-Number (((($_.units2025 - $_.units2024) / $_.units2024) * 100)) } else { 0.0 }
        [pscustomobject][ordered]@{
          os = $_.os
          units2024 = $_.units2024
          units2025 = $_.units2025
          share2025 = $share
          deltaUnits = $_.deltaUnits
          deltaPct = $deltaPct
        }
      }
  )

  Ensure-OrderedMap -Map $osFamilies -Key $family -Value ([ordered]@{
    total2025 = [math]::Round($total2025, 0)
    rows = $prepared
  })
}

$rxMonths = @()
for ($c = 4; $c -le $rxMatrix.GetLength(1); $c += 2) {
  $rxMonths += Normalize-MonthLabel $rxMatrix[1, $c]
}

$rxFamilies = @{}
$rxBrands = @{}
$rxBrandMonthly = @{}
for ($r = 3; $r -le $rxMatrix.GetLength(0); $r++) {
  $familyRaw = Normalize-Text $rxMatrix[$r, 2]
  $brand = Normalize-Text $rxMatrix[$r, 3]
  if (-not $familyRaw) {
    continue
  }

  $family = ''
  $familyLookupKey = Normalize-ProductKey $brand
  if ($familyLookupKey -and $rxMasterMap.ContainsKey($familyLookupKey)) {
    $family = $rxMasterMap[$familyLookupKey]
  }
  if ($familyRaw -match '\(([^)]+)\)') {
    $family = $matches[1].Trim().ToUpper()
  }
  else {
    if (-not $family) {
      $family = $familyRaw.ToUpper()
    }
    if ($family -like 'FLEXINA*') { $family = 'FLEXINA' }
    if ($family -like 'MAGNUS*') { $family = 'MAGNUS' }
  }

  if (-not ($dashboardFamilyOrder -contains $family)) {
    $familyProbe = $familyRaw.ToUpper()
    if ($familyProbe.Contains('DROSPIRENONA')) {
      $family = 'ISIS'
    }
    elseif ($familyProbe.Contains('SIDERBLUT')) {
      if ($familyProbe.Contains('FOLIC')) { $family = 'SIDERBLUT FOLICO' }
      elseif ($familyProbe.Contains('POLI')) { $family = 'SIDERBLUT POLI' }
      elseif ($familyProbe.Contains('COMPLEX')) { $family = 'SIDERBLUT COMPLEX' }
      else { $family = 'SIDERBLUT' }
    }
    elseif ($familyProbe.Contains('TRIP')) {
      if ($familyProbe.Contains('PLUS')) { $family = 'TRIP D3 PLUS' }
      elseif ($familyProbe.Contains('+45')) { $family = 'TRIP +45' }
      elseif ($familyProbe.Contains('MAGNESIO')) { $family = 'TRIP MAGNESIO' }
      else { $family = 'TRIP D3' }
    }
    elseif ($familyProbe.Contains('CALCIO')) {
      if ($familyProbe.Contains('CITRATO') -and $familyProbe.Contains('400')) { $family = 'CALCIO CITRATO DUPOMAR D3 400' }
      elseif ($familyProbe.Contains('CITRATO')) { $family = 'CALCIO CITRATO DUPOMAR D3 200' }
      elseif ($familyProbe.Contains('BASE') -and $familyProbe.Contains('D ')) { $family = 'CALCIO BASE DUPOMAR D' }
      else { $family = 'CALCIO BASE DUPOMAR' }
    }
    elseif ($familyProbe.Contains('CLIMATIX')) {
      $family = 'CLIMATIX'
    }
  }

  if (-not $rxFamilies.ContainsKey($family)) {
    $rxFamilies[$family] = @{
      prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
      doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
    }
  }

  if ($brand -eq 'Totales') {
    $index = 0
    for ($c = 4; $c -le $rxMatrix.GetLength(1); $c += 2) {
      $rxFamilies[$family].prescriptions[$index] += (To-Number $rxMatrix[$r, $c])
      $rxFamilies[$family].doctors[$index] += (To-Number $rxMatrix[$r, ($c + 1)])
      $index++
    }
    continue
  }

  if ($brand -and $brand -ne 'Totales') {
    if (-not $rxBrands.ContainsKey($family)) {
      $rxBrands[$family] = @{}
    }
    if (-not $rxBrandMonthly.ContainsKey($family)) {
      $rxBrandMonthly[$family] = @{}
    }
    if (-not $rxBrands[$family].ContainsKey($brand)) {
      $rxBrands[$family][$brand] = @{ prescriptions = 0.0; doctors = 0.0 }
    }
    if (-not $rxBrandMonthly[$family].ContainsKey($brand)) {
      $rxBrandMonthly[$family][$brand] = @{
        prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
        doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
      }
    }
    $index = 0
    for ($c = 4; $c -le $rxMatrix.GetLength(1); $c += 2) {
      $rxBrandMonthly[$family][$brand].prescriptions[$index] += To-Number $rxMatrix[$r, $c]
      $rxBrandMonthly[$family][$brand].doctors[$index] += To-Number $rxMatrix[$r, ($c + 1)]
      $index++
    }
    $rxBrands[$family][$brand].prescriptions += To-Number $rxMatrix[$r, ($rxMatrix.GetLength(1) - 1)]
    $rxBrands[$family][$brand].doctors += To-Number $rxMatrix[$r, $rxMatrix.GetLength(1)]
  }
}

$rxFamiliesOut = [ordered]@{}
foreach ($family in ($rxFamilies.Keys | Sort-Object { $familyOrder.IndexOf($_) })) {
  $series = $rxFamilies[$family]
  $latestMonth = Get-LastNonZeroMonth -Months $rxMonths -Values $series.prescriptions
  $brands = @()
  if ($rxBrands.ContainsKey($family)) {
    $brands = @(
      $rxBrands[$family].Keys |
        ForEach-Object {
          [pscustomobject][ordered]@{
            brand = $_
            prescriptions = [math]::Round($rxBrands[$family][$_].prescriptions, 0)
            doctors = [math]::Round($rxBrands[$family][$_].doctors, 0)
          }
        } |
        Sort-Object -Property @{ Expression = 'prescriptions'; Descending = $true } |
        Select-Object -First 8
    )
  }

  Ensure-OrderedMap -Map $rxFamiliesOut -Key $family -Value ([ordered]@{
    prescriptions = @($series.prescriptions | ForEach-Object { [math]::Round($_, 0) })
    doctors = @($series.doctors | ForEach-Object { [math]::Round($_, 0) })
    latestMonth = $latestMonth
    topBrands = $brands
  })
}

$rxTotalsPresent = $rxFamiliesOut.Contains('Totales')
if (-not $rxTotalsPresent) {
  $rxTotalPres = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
  $rxTotalDocs = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
  foreach ($family in $rxFamiliesOut.Keys) {
    for ($i = 0; $i -lt $rxMonths.Count; $i++) {
      $rxTotalPres[$i] += $rxFamiliesOut[$family].prescriptions[$i]
      $rxTotalDocs[$i] += $rxFamiliesOut[$family].doctors[$i]
    }
  }
  $rxFamiliesOut['Totales'] = [ordered]@{
    prescriptions = @($rxTotalPres | ForEach-Object { [math]::Round($_, 0) })
    doctors = @($rxTotalDocs | ForEach-Object { [math]::Round($_, 0) })
    latestMonth = Get-LastNonZeroMonth -Months $rxMonths -Values $rxTotalPres
    topBrands = @()
  }
}

$rxTotals = @{
  prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
  doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
}
foreach ($family in $rxFamiliesOut.Keys) {
  if ($family -eq 'Totales') {
    continue
  }
  for ($i = 0; $i -lt $rxMonths.Count; $i++) {
    $rxTotals.prescriptions[$i] += $rxFamiliesOut[$family].prescriptions[$i]
    $rxTotals.doctors[$i] += $rxFamiliesOut[$family].doctors[$i]
  }
}
$rxFamiliesOut['Totales'] = [ordered]@{
  prescriptions = @($rxTotals.prescriptions | ForEach-Object { [math]::Round($_, 0) })
  doctors = @($rxTotals.doctors | ForEach-Object { [math]::Round($_, 0) })
  latestMonth = Get-LastNonZeroMonth -Months $rxMonths -Values $rxTotals.prescriptions
  topBrands = @()
}

$dddMonthsSet = New-Object 'System.Collections.Generic.HashSet[string]'
$dddMonthly = @{}
$dddRegions = @{}
$dddProducts = @{}
$dddSourceIsNew = (Normalize-Text $dddMatrix[1, 2]) -eq 'Mercado'

for ($r = 2; $r -le $dddMatrix.GetLength(0); $r++) {
  $market = if ($dddSourceIsNew) {
    Resolve-MujerFamily -Candidate (Normalize-Text $dddMatrix[$r, 2]) -MasterMap $budgetMasterMap
  } else {
    Normalize-Text $dddMatrix[$r, 2]
  }
  if (-not $market -or -not $dddMarketConfig.Contains($market)) {
    continue
  }

  $month = if ($dddSourceIsNew) { Normalize-MonthLabelEn $dddMatrix[$r, 5] } else { Normalize-MonthLabel $dddMatrix[$r, 5] }
  $region = Normalize-Text $dddMatrix[$r, 1]
  $product = if ($dddSourceIsNew) { Normalize-Text $dddMatrix[$r, 8] } else { Normalize-Text $dddMatrix[$r, 8] }
  $units = To-Number $dddMatrix[$r, 9]
  if (-not $month -or -not $region -or -not $product -or $units -le 0) {
    continue
  }

  $dddMonthsSet.Add($month) | Out-Null
  $isSie = $false
  foreach ($keyword in $dddMarketConfig[$market].keywords) {
    if ($product.ToUpper().Contains($keyword)) {
      $isSie = $true
      break
    }
  }

  if (-not $dddMonthly.ContainsKey($market)) {
    $dddMonthly[$market] = @{}
  }
  if (-not $dddRegions.ContainsKey($market)) {
    $dddRegions[$market] = @{}
  }
  if (-not $dddProducts.ContainsKey($market)) {
    $dddProducts[$market] = @{}
  }

  Ensure-NestedMetric -Map $dddMonthly[$market] -Key $month
  $dddMonthly[$market][$month].total += $units
  if ($isSie) {
    $dddMonthly[$market][$month].sie += $units
  }

  if (-not $dddRegions[$market].ContainsKey($month)) {
    $dddRegions[$market][$month] = @{}
  }
  Ensure-NestedMetric -Map $dddRegions[$market][$month] -Key $region
  $dddRegions[$market][$month][$region].total += $units
  if ($isSie) {
    $dddRegions[$market][$month][$region].sie += $units
  }

  if (-not $dddProducts[$market].ContainsKey($month)) {
    $dddProducts[$market][$month] = @{}
  }
  if (-not $dddProducts[$market][$month].ContainsKey($product)) {
    $dddProducts[$market][$month][$product] = @{
      units = 0.0
      isSie = $isSie
    }
  }
  $dddProducts[$market][$month][$product].units += $units
}

$dddMonths = Sort-Months @($dddMonthsSet)
$dddMarketsOut = [ordered]@{}

foreach ($market in $dddMarketConfig.Keys) {
  if (-not $dddMonthly.ContainsKey($market)) {
    continue
  }

  $monthlyRows = foreach ($month in $dddMonths) {
    $item = if ($dddMonthly[$market].ContainsKey($month)) { $dddMonthly[$market][$month] } else { @{ total = 0.0; sie = 0.0 } }
    $share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    [ordered]@{
      month = $month
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = $share
    }
  }

  $latestMonth = $dddMonths[-1]
  $regionsByMonth = [ordered]@{}
  $productsByMonth = [ordered]@{}

  foreach ($month in $dddMonths) {
    $regionRows = @()
    if ($dddRegions[$market].ContainsKey($month)) {
      $regionRows = Convert-MetricMap $dddRegions[$market][$month]
    }
    $regionsByMonth.Add($month, @(
      $regionRows | Sort-Object -Property @{ Expression = 'share'; Descending = $true }, @{ Expression = 'total'; Descending = $true }
    ))

    $productRows = @()
    if ($dddProducts[$market].ContainsKey($month)) {
      $totalUnits = 0.0
      foreach ($name in $dddProducts[$market][$month].Keys) {
        $totalUnits += $dddProducts[$market][$month][$name].units
      }

      $productRows = @(
        $dddProducts[$market][$month].Keys |
          ForEach-Object {
            $item = $dddProducts[$market][$month][$_]
            [pscustomobject][ordered]@{
              product = $_
              units = [math]::Round($item.units, 0)
              share = if ($totalUnits -gt 0) { Round-Number (($item.units / $totalUnits) * 100) } else { 0.0 }
              isSie = [bool]$item.isSie
            }
          } |
          Sort-Object -Property @{ Expression = 'units'; Descending = $true } |
          Select-Object -First 12
      )
    }
    $productsByMonth.Add($month, $productRows)
  }

  $dddMarketsOut.Add($market, [ordered]@{
    family = $dddMarketConfig[$market].family
    latestMonth = $latestMonth
    monthly = $monthlyRows
    regionsByMonth = $regionsByMonth
    productsByMonth = $productsByMonth
  })
}

$dashboardShare = @{}
foreach ($family in $familyOrder) {
  $dashboardShare[$family] = @{}
}

foreach ($market in $dddMarketsOut.Keys) {
  $family = $dddMarketsOut[$market].family
  foreach ($row in $dddMarketsOut[$market].monthly) {
    if (-not $dashboardShare[$family].ContainsKey($row.month)) {
      $dashboardShare[$family][$row.month] = @{
        total = 0.0
        sie = 0.0
      }
    }
    $dashboardShare[$family][$row.month].total += $row.total
    $dashboardShare[$family][$row.month].sie += $row.sie
  }
}

$dashboardShareOut = [ordered]@{}
foreach ($family in $familyOrder) {
  if (-not $dashboardShare.ContainsKey($family)) {
    continue
  }
  $rows = foreach ($month in $dddMonths) {
    $item = if ($dashboardShare[$family].ContainsKey($month)) { $dashboardShare[$family][$month] } else { @{ total = 0.0; sie = 0.0 } }
    [ordered]@{
      month = $month
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    }
  }
  $dashboardShareOut.Add($family, $rows)
}

$dashboardShareOut['Totales'] = @(
  foreach ($month in $dddMonths) {
    $total = 0.0
    $sie = 0.0
    foreach ($family in $dashboardShareOut.Keys) {
      if ($family -eq 'Totales') {
        continue
      }
      $row = $dashboardShareOut[$family] | Where-Object { $_.month -eq $month } | Select-Object -First 1
      if ($row) {
        $total += $row.total
        $sie += $row.sie
      }
    }
    [ordered]@{
      month = $month
      total = [math]::Round($total, 0)
      sie = [math]::Round($sie, 0)
      share = if ($total -gt 0) { Round-Number (($sie / $total) * 100) } else { 0.0 }
    }
  }
)

$familyToMarkets = [ordered]@{}
foreach ($family in $familyOrder) {
  $familyToMarkets.Add($family, @())
}
foreach ($market in $dddMarketConfig.Keys) {
  $family = $dddMarketConfig[$market].family
  $familyToMarkets[$family] = @($familyToMarkets[$family] + $market)
}
$familyToMarkets['Totales'] = @($dddMarketConfig.Keys)

$summary = [ordered]@{}
foreach ($family in $familyOrder) {
  $budgetFamily = if ($budgetFamilies.Contains($family)) { $budgetFamilies[$family] } else { $null }
  $stockFamily = if ($stockFamilies.Contains($family)) { $stockFamilies[$family] } else { $null }
  $channelFamily = if ($channelFamilies.Contains($family)) { $channelFamilies[$family] } else { $null }
  $rxFamily = if ($rxFamiliesOut.Contains($family)) { $rxFamiliesOut[$family] } else { $null }
  $shareFamily = if ($dashboardShareOut.Contains($family)) { $dashboardShareOut[$family] } else { $null }

  $latestBudgetActual = 0
  $latestBudgetTarget = 0
  $ytdActual2026 = 0
  $ytdBudget2026 = 0
  if ($budgetFamily) {
    $latestBudgetActual = [math]::Round(($budgetFamily.actual[$budgetMonths.IndexOf($budgetCut)]), 0)
    $latestBudgetTarget = [math]::Round(($budgetFamily.budget[$budgetMonths.IndexOf($budgetCut)]), 0)
    $ytdActual2026 = Get-YtdSum -Months $budgetMonths -Values $budgetFamily.actual -Year 2026 -CutMonth $budgetCut
    $ytdBudget2026 = Get-YtdSum -Months $budgetMonths -Values $budgetFamily.budget -Year 2026 -CutMonth $budgetCut
  }

  $latestStockDays = 0
  if ($stockFamily) {
    $latestStockDays = [math]::Round(($stockFamily.days[$stockMonths.IndexOf($stockCut)]), 0)
  }

  $latestRx = 0
  if ($rxFamily -and $rxFamily.latestMonth) {
    $latestRx = [math]::Round(($rxFamily.prescriptions[$rxMonths.IndexOf($rxFamily.latestMonth)]), 0)
  }

  $latestShare = 0.0
  if ($shareFamily -and $shareFamily.Count -gt 0) {
    $latestShare = $shareFamily[-1].share
  }

  $summary.Add($family, [ordered]@{
    ytdActual2026 = $ytdActual2026
    ytdBudget2026 = $ytdBudget2026
    compliance2026 = if ($ytdBudget2026 -gt 0) { Round-Number (($ytdActual2026 / $ytdBudget2026) * 100) } else { 0.0 }
    latestMonth = $budgetCut
    latestActual = $latestBudgetActual
    latestBudget = $latestBudgetTarget
    latestStockDays = $latestStockDays
    convenioPct = if ($channelFamily) { $channelFamily.convenioPct } else { 0.0 }
    latestRx = $latestRx
    latestShare = $latestShare
    hasDdd = ($familyToMarkets[$family].Count -gt 0)
  })
}

# Dashboard layer compatible with the dermatologia executive view
$pmHeaderInfo = [ordered]@{
  monthly = @()
  ytd = @()
  mat = @()
  quarterly = @()
}
for ($c = 8; $c -le $pmMatrix.GetLength(1); $c++) {
  $header = ((Normalize-Text $pmMatrix[1, $c]) -replace '\s+', ' ').Trim()
  if (-not $header -or $header -notlike '*Units') {
    continue
  }

  if ($header -match '^MAT ([A-Za-z]{3}) (\d{4}) Units$') {
    $key = '{0} {1}' -f $matches[1], $matches[2]
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.mat += [pscustomobject]@{ col = $c; key = $key }
    }
    continue
  }

  if ($header -match '^YTD ([A-Za-z]{3}) (\d{4}) Units$') {
    $key = '{0} {1}' -f $matches[1], $matches[2]
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.ytd += [pscustomobject]@{ col = $c; key = $key }
    }
    continue
  }

  if ($header -match '^([A-Za-z]{3}) (\d{4}) Units$') {
    $key = '{0} {1}' -f $matches[1], $matches[2]
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.monthly += [pscustomobject]@{ col = $c; key = $key }
    }
    continue
  }

  if ($header -match '^\d{1,2}/\d{1,2}/\d{4} Units$') {
    $monthKey = Normalize-MonthLabelEn (($header -replace ' Units$', '').Trim())
    if ((Get-MonthSortValueEn $monthKey) -ge 202402) {
      $pmHeaderInfo.monthly += [pscustomobject]@{ col = $c; key = $monthKey }
    }
    continue
  }

  if ($header -like '* to *Units') {
    $quarterKey = Convert-QuarterLabelFromHeader ($header -replace ' Units$', '')
    if ($quarterKey -and (Get-QuarterSortValue $quarterKey) -ge 20240) {
      $pmHeaderInfo.quarterly += [pscustomobject]@{ col = $c; key = $quarterKey }
    }
  }
}

$pmMatKeys = @($pmHeaderInfo.mat | ForEach-Object { $_.key })
$pmYtdKeys = @($pmHeaderInfo.ytd | ForEach-Object { $_.key })
$pmMonthlyKeys = @($pmHeaderInfo.monthly | ForEach-Object { $_.key })
$pmQuarterKeys = @($pmHeaderInfo.quarterly | ForEach-Object { $_.key })

if ($pmMatKeys.Count -eq 0 -and $pmMonthlyKeys.Count -gt 0) {
  $pmMatKeys = @($pmMonthlyKeys)
}
if ($pmYtdKeys.Count -eq 0 -and $pmMonthlyKeys.Count -gt 0) {
  $pmYtdKeys = @($pmMonthlyKeys)
}

$pmCurrentMatKey = $pmMatKeys[-1]
$pmPrevMatKey = $pmMatKeys[-2]
$pmCurrentYtdKey = $pmYtdKeys[-1]
$pmPrevYtdKey = $pmYtdKeys[-2]

$pmPerf = [ordered]@{}
$pmProductMatLookup = @{}
$brandKpis = [ordered]@{}
$molLabels = [ordered]@{}
$prodMap = [ordered]@{}
$budIqviaMap = [ordered]@{}
$marketTotalsByGroup = @{}
$marketSieByGroup = @{}

foreach ($family in $dashboardFamilyOrder) {
  $cfg = $dashboardMarketConfig[$family]
  $molLabels[$family] = $family
  $prodMap[$family] = [ordered]@{
    mol = $family
    canal = $family
    conv = $family
    rec = $family
    prec = $family
    bud = $family
  }
  $budIqviaMap[$family] = @($cfg.sieProducts)

  $aggregatedProducts = @{}
  $marketMonthly = @{}
  $marketYtd = @{}
  $marketMat = @{}
  $marketQuarterly = @{}
  foreach ($key in $pmMonthlyKeys) { $marketMonthly[$key] = 0.0 }
  foreach ($key in $pmYtdKeys) { $marketYtd[$key] = 0.0 }
  foreach ($key in $pmMatKeys) { $marketMat[$key] = 0.0 }
  foreach ($key in $pmQuarterKeys) { $marketQuarterly[$key] = 0.0 }

  for ($r = 2; $r -le $pmMatrix.GetLength(0); $r++) {
    $product = Normalize-Text $pmMatrix[$r, $pmColProduct]
    $manufacturer = Normalize-Text $pmMatrix[$r, $pmColManuf]
    # PENDIENTE: molecula y ATC siguen leyendose por POSICION. Son las dos ultimas
    # lecturas posicionales del PM que quedan en los 5 builders (ver CLAUDE.md regla 8:
    # el reorden de columnas de Jul-2026 borro las 49 marcas SIE sin mover una suma).
    # No se convirtieron a header porque mujer lee un PM SLICEADO (useSlicedIqvia en
    # close-manifest) cuyo layout no se pudo verificar, y porque update-all.ps1 NO
    # reconstruye mujer: se sincroniza con sync-mujer-pm.py, que si resuelve por header.
    # Antes de volver a correr mujer/build-data.ps1: confirmar el layout del slice.
    $molecule = Normalize-Text $pmMatrix[$r, 4]
    $atc = Normalize-Text $pmMatrix[$r, 5]
    if (-not $product) {
      continue
    }
    if (-not (Test-PMMarketMatch -Config $cfg -Product $product -Molecule $molecule -Atc $atc)) {
      continue
    }

    if (-not $aggregatedProducts.ContainsKey($product)) {
      $aggregatedProducts[$product] = @{
        manuf = $manufacturer
        is_sie = ($product -like '*(SIE)*' -or $manufacturer.ToUpper().Contains('SIEGFRIED'))
        monthly = @{}
        ytd = @{}
        mat = @{}
        quarterly = @{}
      }
      foreach ($key in $pmMonthlyKeys) { $aggregatedProducts[$product].monthly[$key] = 0.0 }
      foreach ($key in $pmYtdKeys) { $aggregatedProducts[$product].ytd[$key] = 0.0 }
      foreach ($key in $pmMatKeys) { $aggregatedProducts[$product].mat[$key] = 0.0 }
      foreach ($key in $pmQuarterKeys) { $aggregatedProducts[$product].quarterly[$key] = 0.0 }
    }

    foreach ($colInfo in $pmHeaderInfo.monthly) {
      $value = To-Number $pmMatrix[$r, $colInfo.col]
      $aggregatedProducts[$product].monthly[$colInfo.key] += $value
      $marketMonthly[$colInfo.key] += $value
    }
    foreach ($colInfo in $pmHeaderInfo.ytd) {
      $value = To-Number $pmMatrix[$r, $colInfo.col]
      $aggregatedProducts[$product].ytd[$colInfo.key] += $value
      $marketYtd[$colInfo.key] += $value
    }
    foreach ($colInfo in $pmHeaderInfo.mat) {
      $value = To-Number $pmMatrix[$r, $colInfo.col]
      $aggregatedProducts[$product].mat[$colInfo.key] += $value
      $marketMat[$colInfo.key] += $value
    }
    foreach ($colInfo in $pmHeaderInfo.quarterly) {
      $value = To-Number $pmMatrix[$r, $colInfo.col]
      $aggregatedProducts[$product].quarterly[$colInfo.key] += $value
      $marketQuarterly[$colInfo.key] += $value
    }
  }

  if (($pmHeaderInfo.ytd.Count -eq 0 -or $pmHeaderInfo.mat.Count -eq 0) -and $pmMonthlyKeys.Count -gt 0) {
    foreach ($productName in $aggregatedProducts.Keys) {
      $item = $aggregatedProducts[$productName]
      foreach ($key in $pmMonthlyKeys) {
        $item.ytd[$key] = Get-YtdSumEn -MonthlyMap $item.monthly -MonthKey $key
        $item.mat[$key] = Get-MatSumEn -MonthlyMap $item.monthly -OrderedKeys $pmMonthlyKeys -MonthKey $key
      }
    }
    foreach ($key in $pmMonthlyKeys) {
      $marketYtd[$key] = 0.0
      $marketMat[$key] = 0.0
      foreach ($productName in $aggregatedProducts.Keys) {
        $marketYtd[$key] += [double]$aggregatedProducts[$productName].ytd[$key]
        $marketMat[$key] += [double]$aggregatedProducts[$productName].mat[$key]
      }
    }
  }

  $productRows = @(
    $aggregatedProducts.Keys |
      ForEach-Object {
        $item = $aggregatedProducts[$_]
        [pscustomobject]@{
          name = $_
          manuf = $item.manuf
          is_sie = [bool]$item.is_sie
          currentMat = [math]::Round(($item.mat[$pmCurrentMatKey]), 0)
          currentYtd = [math]::Round(($item.ytd[$pmCurrentYtdKey]), 0)
        }
      } |
      Sort-Object -Property @{ Expression = 'currentMat'; Descending = $true }, @{ Expression = 'currentYtd'; Descending = $true }
  )

  $selectedProductNames = New-Object 'System.Collections.Generic.List[string]'
  foreach ($prodName in $cfg.sieProducts) {
    if ($aggregatedProducts.ContainsKey($prodName) -and -not $selectedProductNames.Contains($prodName)) {
      $selectedProductNames.Add($prodName)
    }
  }
  foreach ($row in $productRows) {
    if ($selectedProductNames.Count -ge 8) {
      break
    }
    if (-not $selectedProductNames.Contains($row.name)) {
      $selectedProductNames.Add($row.name)
    }
  }

  $pmProductMatLookup[$family] = @{}
  $productsOut = @(
    foreach ($prodName in $selectedProductNames) {
      $item = $aggregatedProducts[$prodName]
      $baseKey = Normalize-ProductKey $prodName
      if (-not $pmProductMatLookup[$family].ContainsKey($baseKey)) {
        $pmProductMatLookup[$family][$baseKey] = [math]::Round(($item.mat[$pmCurrentMatKey]), 0)
      }

      $monthlyVals = [ordered]@{}
      $ytdVals = [ordered]@{}
      $matVals = [ordered]@{}
      $quarterlyVals = [ordered]@{}
      $msMonthly = [ordered]@{}
      $msQuarterly = [ordered]@{}
      $msYtd = [ordered]@{}
      $msMat = [ordered]@{}

      foreach ($key in $pmMonthlyKeys) {
        $units = [math]::Round(($item.monthly[$key]), 0)
        $monthlyVals[$key] = $units
        $msMonthly[$key] = if ($marketMonthly[$key] -gt 0) { Round-Number (($item.monthly[$key] / $marketMonthly[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $pmYtdKeys) {
        $units = [math]::Round(($item.ytd[$key]), 0)
        $ytdVals[$key] = $units
        $msYtd[$key] = if ($marketYtd[$key] -gt 0) { Round-Number (($item.ytd[$key] / $marketYtd[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $pmMatKeys) {
        $units = [math]::Round(($item.mat[$key]), 0)
        $matVals[$key] = $units
        $msMat[$key] = if ($marketMat[$key] -gt 0) { Round-Number (($item.mat[$key] / $marketMat[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $pmQuarterKeys) {
        $units = [math]::Round(($item.quarterly[$key]), 0)
        $quarterlyVals[$key] = $units
        $msQuarterly[$key] = if ($marketQuarterly[$key] -gt 0) { Round-Number (($item.quarterly[$key] / $marketQuarterly[$key]) * 100) } else { 0.0 }
      }

      [ordered]@{
        prod = $prodName
        manuf = $item.manuf
        is_sie = [bool]$item.is_sie
        monthly_vals = $monthlyVals
        ytd = $ytdVals
        mat = $matVals
        ms_ytd = $msYtd
        ms_mat = $msMat
        quarterly_vals = $quarterlyVals
        ms_monthly = $msMonthly
        ms_quarterly = $msQuarterly
      }
    }
  )

  $marketMonthlyOut = [ordered]@{}
  $marketYtdOut = [ordered]@{}
  $marketMatOut = [ordered]@{}
  $marketQuarterlyOut = [ordered]@{}
  foreach ($key in $pmMonthlyKeys) { $marketMonthlyOut[$key] = [math]::Round($marketMonthly[$key], 0) }
  foreach ($key in $pmYtdKeys) { $marketYtdOut[$key] = [math]::Round($marketYtd[$key], 0) }
  foreach ($key in $pmMatKeys) { $marketMatOut[$key] = [math]::Round($marketMat[$key], 0) }
  foreach ($key in $pmQuarterKeys) { $marketQuarterlyOut[$key] = [math]::Round($marketQuarterly[$key], 0) }

  $pmPerf[$family] = [ordered]@{
    products = $productsOut
    ytd = $marketYtdOut
    mat = $marketMatOut
    monthly = $marketMonthlyOut
    quarterly = $marketQuarterlyOut
  }

  $currentYtdUnits = 0.0
  $prevYtdUnits = 0.0
  $currentMatUnits = 0.0
  $prevMatUnits = 0.0
  foreach ($prodName in $cfg.sieProducts) {
    if ($aggregatedProducts.ContainsKey($prodName)) {
      $currentYtdUnits += $aggregatedProducts[$prodName].ytd[$pmCurrentYtdKey]
      $prevYtdUnits += $aggregatedProducts[$prodName].ytd[$pmPrevYtdKey]
      $currentMatUnits += $aggregatedProducts[$prodName].mat[$pmCurrentMatKey]
      $prevMatUnits += $aggregatedProducts[$prodName].mat[$pmPrevMatKey]
    }
  }

  if (-not $marketTotalsByGroup.ContainsKey($cfg.group)) {
    $marketTotalsByGroup[$cfg.group] = @{
      ytd = $marketYtd[$pmCurrentYtdKey]
      mat = $marketMat[$pmCurrentMatKey]
    }
  }
  if (-not $marketSieByGroup.ContainsKey($cfg.group)) {
    $marketSieByGroup[$cfg.group] = @{
      currentYtd = 0.0
      prevYtd = 0.0
      currentMat = 0.0
      prevMat = 0.0
    }
  }
  $marketSieByGroup[$cfg.group].currentYtd += $currentYtdUnits
  $marketSieByGroup[$cfg.group].prevYtd += $prevYtdUnits
  $marketSieByGroup[$cfg.group].currentMat += $currentMatUnits
  $marketSieByGroup[$cfg.group].prevMat += $prevMatUnits

  $budgetPct = $null
  $budgetReal = $null
  $budgetTarget = $null
  if ($summary.Contains($family)) {
    $budgetPct = $summary[$family].compliance2026
    $budgetReal = $summary[$family].latestActual
    $budgetTarget = $summary[$family].latestBudget
  }

  $brandKpis[$family] = [ordered]@{
    ytd = [ordered]@{
      ie = if ($prevYtdUnits -gt 0) { Round-Number (($currentYtdUnits / $prevYtdUnits) * 100) } else { $null }
      ms = if ($marketYtd[$pmCurrentYtdKey] -gt 0) { Round-Number (($currentYtdUnits / $marketYtd[$pmCurrentYtdKey]) * 100) } else { $null }
      units = [math]::Round($currentYtdUnits, 0)
      units_prev = [math]::Round($prevYtdUnits, 0)
      market_total = [math]::Round($marketYtd[$pmCurrentYtdKey], 0)
      growth = if ($prevYtdUnits -gt 0) { Round-Number ((($currentYtdUnits - $prevYtdUnits) / $prevYtdUnits) * 100) } else { $null }
    }
    mat = [ordered]@{
      ie = if ($prevMatUnits -gt 0) { Round-Number (($currentMatUnits / $prevMatUnits) * 100) } else { $null }
      ms = if ($marketMat[$pmCurrentMatKey] -gt 0) { Round-Number (($currentMatUnits / $marketMat[$pmCurrentMatKey]) * 100) } else { $null }
      units = [math]::Round($currentMatUnits, 0)
      units_prev = [math]::Round($prevMatUnits, 0)
      market_total = [math]::Round($marketMat[$pmCurrentMatKey], 0)
      growth = if ($prevMatUnits -gt 0) { Round-Number ((($currentMatUnits - $prevMatUnits) / $prevMatUnits) * 100) } else { $null }
    }
    budget = [ordered]@{
      pct = $budgetPct
      real = $budgetReal
      target = $budgetTarget
    }
    rec = [ordered]@{
      ms = $null
      label = $null
    }
  }
}

$dashboardBudget = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  if (-not $budgetFamilies.Contains($family)) {
    continue
  }

  $entry = $budgetFamilies[$family]
  $familyBudget = [ordered]@{}
  foreach ($year in @('2025', '2026')) {
    $actual = @()
    $budget = @()
    for ($month = 1; $month -le 12; $month++) {
      $monthKey = '{0}-{1}' -f $monthLabel[$month], $year
      $idx = $budgetMonths.IndexOf($monthKey)
      $actualValue = $null
      $budgetValue = $null
      if ($idx -ge 0) {
        $budgetValue = [math]::Round(($entry.budget[$idx]), 0)
        if ($year -eq '2026' -and $idx -gt $budgetMonths.IndexOf($budgetCut)) {
          $actualValue = $null
        }
        else {
          $actualValue = [math]::Round(($entry.actual[$idx]), 0)
        }
      }
      $actual += $actualValue
      $budget += $budgetValue
    }
    $familyBudget[$year] = [ordered]@{
      budget = $budget
      real = $actual
    }
  }
  $dashboardBudget[$family] = $familyBudget
}

$dashboardStock = [ordered]@{}
$stockMonthsEn = @($stockMonths | ForEach-Object { Normalize-MonthLabelEn $_ })
foreach ($family in $dashboardFamilyOrder) {
  if (-not $stockFamilies.Contains($family)) {
    continue
  }

  $entry = $stockFamilies[$family]
  $rows = [ordered]@{}
  for ($i = 0; $i -lt $stockMonthsEn.Count; $i++) {
    $rows[$stockMonthsEn[$i]] = [ordered]@{
      stock = [math]::Round(($entry.stock[$i]), 0)
      ventas = [math]::Round(($entry.sales[$i]), 0)
      facturacion = [math]::Round(($entry.billing[$i]), 0)
      dias = if ($entry.days[$i] -gt 0) { [math]::Round(($entry.days[$i]), 0) } else { $null }
    }
  }
  $dashboardStock[$family] = $rows
}

$covCutIndex = $stockMonths.IndexOf($stockCut)
if ($covCutIndex -lt 0) { $covCutIndex = $stockMonths.Count - 1 }
$covStartIndex = [Math]::Max(0, $covCutIndex - 11)
$covIndices = @()
for ($i = $covStartIndex; $i -le $covCutIndex; $i++) {
  $covIndices += $i
}
$coverageLabels = @(
  foreach ($idx in $covIndices) {
    Get-CoverageLabel (Normalize-MonthLabelEn $stockMonths[$idx])
  }
)

$stockAlerts = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  if (-not $stockFamilies.Contains($family)) {
    continue
  }

  $entry = $stockFamilies[$family]
  $ventas = @()
  $dias = @()
  $statuses = @()
  $alertIndices = @()
  foreach ($idx in $covIndices) {
    $saleValue = [math]::Round(($entry.sales[$idx]), 0)
    $dayValue = if ($entry.days[$idx] -gt 0) { [math]::Round(($entry.days[$idx]), 0) } else { $null }
    $status = Classify-StockStatus $dayValue
    if ($status -ne 'ok' -and $status -ne 'nd') {
      $alertIndices += $ventas.Count
    }
    $ventas += $saleValue
    $dias += $dayValue
    $statuses += $status
  }

  $stockAlerts[$family] = [ordered]@{
    ventas = $ventas
    dias = $dias
    statuses = $statuses
    alert_indices = $alertIndices
    worst_status = Get-WorstStockStatus $statuses
    n_alerts = $alertIndices.Count
    familia = $family
  }
}

$stockPresByFamily = @{}
foreach ($productName in $stockProductSeries.Keys) {
  $entry = $stockProductSeries[$productName]
  $family = $entry.family
  if ($family -eq 'Totales' -or -not ($dashboardFamilyOrder -contains $family)) {
    continue
  }
  if (-not $stockPresByFamily.ContainsKey($family)) {
    $stockPresByFamily[$family] = @()
  }

  $ventas = @()
  $dias = @()
  $statuses = @()
  $alertIndices = @()
  foreach ($idx in $covIndices) {
    $saleValue = [math]::Round(($entry.sales[$idx]), 0)
    $dayValue = if ($entry.days[$idx] -gt 0) { [math]::Round(($entry.days[$idx]), 0) } else { $null }
    $status = Classify-StockStatus $dayValue
    if ($status -ne 'ok' -and $status -ne 'nd') {
      $alertIndices += $ventas.Count
    }
    $ventas += $saleValue
    $dias += $dayValue
    $statuses += $status
  }

  $stockPresByFamily[$family] += [pscustomobject][ordered]@{
    product = $productName
    totalSales = [math]::Round((($entry.sales | Measure-Object -Sum).Sum), 0)
    ventas = $ventas
    dias = $dias
    statuses = $statuses
    alert_indices = $alertIndices
    worst_status = Get-WorstStockStatus $statuses
    n_alerts = $alertIndices.Count
    familia = $family
  }
}

$stockPres = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  if (-not $stockPresByFamily.ContainsKey($family)) {
    continue
  }

  $selected = @(
    $stockPresByFamily[$family] |
      Sort-Object -Property @{ Expression = 'totalSales'; Descending = $true } |
      Select-Object -First 6
  )
  foreach ($row in $selected) {
    $stockPres[$row.product] = [ordered]@{
      ventas = $row.ventas
      dias = $row.dias
      statuses = $row.statuses
      alert_indices = $row.alert_indices
      worst_status = $row.worst_status
      n_alerts = $row.n_alerts
      familia = $row.familia
    }
  }
}

$dashboardCanales = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  if (-not $channelFamilies.Contains($family)) {
    continue
  }
  $entry = $channelFamilies[$family]
  $dashboardCanales[$family] = [ordered]@{
    unid = $entry.facturedUnits
    conv = $entry.convenioPct
    most = $entry.mostradorPct
    conv_units = $entry.convenioUnits
    most_units = $entry.mostradorUnits
    dto_total = $entry.discountTotalPct
    dto_conv = $entry.discountConvenioPct
    dto_most = $entry.discountCommonPct
    unid_prev = $null
    conv_prev = $null
    most_prev = $null
    conv_units_prev = $null
    most_units_prev = $null
    dto_total_prev = $null
    dto_conv_prev = $null
    dto_most_prev = $null
    conv_pp = $null
    most_pp = $null
  }
}

$dashboardConvenios = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  if (-not $osFamilies.Contains($family)) {
    continue
  }
  $dashboardConvenios[$family] = @(
    $osFamilies[$family].rows |
      ForEach-Object {
        [ordered]@{
          os = $_.os
          unid24 = $_.units2024
          unid = $_.units2025
          delta = $_.deltaPct
        }
      }
  )
}

$dashboardRecetas = [ordered]@{}
$dashboardRecMs = [ordered]@{}
$dashboardRecComp = [ordered]@{}
$rxMonthsEn = @($rxMonths | ForEach-Object { Normalize-MonthLabelEn $_ })

foreach ($family in $dashboardFamilyOrder) {
  if (-not $rxFamilies.ContainsKey($family)) {
    continue
  }

  $familyMonthly = [ordered]@{}
  for ($i = 0; $i -lt $rxMonths.Count; $i++) {
    $familyMonthly[$rxMonthsEn[$i]] = [ordered]@{
      recetas = [math]::Round(($rxFamilies[$family].prescriptions[$i]), 0)
      medicos = [math]::Round(($rxFamilies[$family].doctors[$i]), 0)
    }
  }
  $dashboardRecetas[$family] = $familyMonthly

  $sieMonthly = @{}
  foreach ($key in $rxMonthsEn) { $sieMonthly[$key] = 0.0 }
  if ($rxBrandMonthly.ContainsKey($family)) {
    foreach ($brand in $rxBrandMonthly[$family].Keys) {
      if (-not $brand.ToUpper().Contains('SIE')) {
        continue
      }
      for ($i = 0; $i -lt $rxMonths.Count; $i++) {
        $sieMonthly[$rxMonthsEn[$i]] += $rxBrandMonthly[$family][$brand].prescriptions[$i]
      }
    }
  }

  $sieMonthlyOut = [ordered]@{}
  $msMonthlyOut = [ordered]@{}
  foreach ($key in $rxMonthsEn) {
    $total = $dashboardRecetas[$family][$key].recetas
    $sieValue = [math]::Round($sieMonthly[$key], 0)
    $sieMonthlyOut[$key] = $sieValue
    $msMonthlyOut[$key] = if ($total -gt 0) { Round-Number (($sieMonthly[$key] / $total) * 100) } else { 0.0 }
  }

  $quarterOrder = [ordered]@{}
  foreach ($key in $rxMonthsEn) {
    $monthToken = $key.Split(' ')[0]
    $yearToken = $key.Split(' ')[1]
    $quarter = switch ($monthToken) {
      'Jan' { 'Q1' }
      'Feb' { 'Q1' }
      'Mar' { 'Q1' }
      'Apr' { 'Q2' }
      'May' { 'Q2' }
      'Jun' { 'Q2' }
      'Jul' { 'Q3' }
      'Aug' { 'Q3' }
      'Sep' { 'Q3' }
      'Oct' { 'Q4' }
      'Nov' { 'Q4' }
      'Dec' { 'Q4' }
      default { '' }
    }
    if (-not $quarter) { continue }
    $qKey = "$quarter $yearToken"
    if (-not $quarterOrder.Contains($qKey)) {
      $quarterOrder[$qKey] = @{ sie = 0.0; total = 0.0 }
    }
    $quarterOrder[$qKey].sie += $sieMonthly[$key]
    $quarterOrder[$qKey].total += $dashboardRecetas[$family][$key].recetas
  }

  $quarterlyOut = [ordered]@{}
  $quarterlyMsOut = [ordered]@{}
  foreach ($qKey in (Sort-QuarterLabels @($quarterOrder.Keys))) {
    $quarterlyOut[$qKey] = [math]::Round(($quarterOrder[$qKey].sie), 0)
    $quarterlyMsOut[$qKey] = if ($quarterOrder[$qKey].total -gt 0) { Round-Number (($quarterOrder[$qKey].sie / $quarterOrder[$qKey].total) * 100) } else { 0.0 }
  }

  $dashboardRecMs[$family] = [ordered]@{
    sie = $sieMonthlyOut
    ms = $msMonthlyOut
    quarterly = $quarterlyOut
    ms_quarterly = $quarterlyMsOut
  }

  $compRows = [ordered]@{}
  if ($rxBrandMonthly.ContainsKey($family)) {
    foreach ($brand in $rxBrandMonthly[$family].Keys) {
      $brandMonthly = [ordered]@{}
      $brandQuarterlyTemp = @{}
      $brandTotal = 0.0
      for ($i = 0; $i -lt $rxMonths.Count; $i++) {
        $value = [math]::Round(($rxBrandMonthly[$family][$brand].prescriptions[$i]), 0)
        $monthKey = $rxMonthsEn[$i]
        $brandMonthly[$monthKey] = $value
        $brandTotal += $value
        $monthToken = $monthKey.Split(' ')[0]
        $yearToken = $monthKey.Split(' ')[1]
        $quarter = switch ($monthToken) {
          'Jan' { 'Q1' }
          'Feb' { 'Q1' }
          'Mar' { 'Q1' }
          'Apr' { 'Q2' }
          'May' { 'Q2' }
          'Jun' { 'Q2' }
          'Jul' { 'Q3' }
          'Aug' { 'Q3' }
          'Sep' { 'Q3' }
          'Oct' { 'Q4' }
          'Nov' { 'Q4' }
          'Dec' { 'Q4' }
          default { '' }
        }
        if (-not $quarter) { continue }
        $qKey = "$quarter $yearToken"
        if (-not $brandQuarterlyTemp.ContainsKey($qKey)) {
          $brandQuarterlyTemp[$qKey] = 0.0
        }
        $brandQuarterlyTemp[$qKey] += $value
      }
      $brandQuarterly = [ordered]@{}
      foreach ($qKey in (Sort-QuarterLabels @($brandQuarterlyTemp.Keys))) {
        $brandQuarterly[$qKey] = [math]::Round(($brandQuarterlyTemp[$qKey]), 0)
      }

      $compRows[$brand] = [ordered]@{
        monthly = $brandMonthly
        quarterly = $brandQuarterly
        total = [math]::Round($brandTotal, 0)
      }
    }
  }
  $dashboardRecComp[$family] = $compRows

  if ($brandKpis.Contains($family)) {
    $latestRecMonth = $rxMonthsEn[-1]
    $brandKpis[$family].rec.ms = $dashboardRecMs[$family].ms[$latestRecMonth]
    $brandKpis[$family].rec.label = $latestRecMonth
  }
}

$pricePrevLabel = Normalize-Text $priceMatrix[1, 13]
$priceCurrLabel = Normalize-Text $priceMatrix[1, 14]
$dashboardPrices = [ordered]@{}
$precIqvia = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  $dashboardPrices[$family] = [ordered]@{}
  $precIqvia[$family] = [ordered]@{}
  if (-not $pmProductMatLookup.ContainsKey($family)) {
    continue
  }

  $allowedProducts = $pmProductMatLookup[$family]
  for ($r = 2; $r -le $priceMatrix.GetLength(0); $r++) {
    $productName = Normalize-Text $priceMatrix[$r, 3]
    $presentation = Normalize-Text $priceMatrix[$r, 4]
    $lab = Normalize-Text $priceMatrix[$r, 7]
    if (-not $productName -or -not $presentation) {
      continue
    }

    $normPriceKey = Normalize-ProductKey $productName
    $matchedKey = ''
    foreach ($candidate in $allowedProducts.Keys) {
      if (Test-NormalizedProductMatch -Left $candidate -Right $normPriceKey) {
        $matchedKey = $candidate
        break
      }
    }
    if (-not $matchedKey) {
      continue
    }

    if (-not $dashboardPrices[$family].Contains($presentation)) {
      $dashboardPrices[$family].Add($presentation, @())
    }

    if (-not $precIqvia[$family].Contains($productName.ToUpper())) {
      $precIqvia[$family].Add($productName.ToUpper(), $allowedProducts[$matchedKey])
    }

    $dashboardPrices[$family][$presentation] += [ordered]@{
      lab = $lab
      prod = $productName
      is_sie = $lab.ToUpper().Contains('SIEGFRIED')
      pvp_dic25 = Round-Number (To-Number $priceMatrix[$r, 13]) 2
      pvp_feb26 = Round-Number (To-Number $priceMatrix[$r, 14]) 2
      var = if ((To-Number $priceMatrix[$r, 15]) -ne 0) { (To-Number $priceMatrix[$r, 15]) / 100 } else { 0.0 }
    }
  }
}

$totalCurrentYtd = 0.0
$totalPrevYtd = 0.0
$totalCurrentMat = 0.0
$totalPrevMat = 0.0
$totalMarketYtd = 0.0
$totalMarketMat = 0.0
foreach ($group in $marketTotalsByGroup.Keys) {
  $totalMarketYtd += $marketTotalsByGroup[$group].ytd
  $totalMarketMat += $marketTotalsByGroup[$group].mat
  $totalCurrentYtd += $marketSieByGroup[$group].currentYtd
  $totalPrevYtd += $marketSieByGroup[$group].prevYtd
  $totalCurrentMat += $marketSieByGroup[$group].currentMat
  $totalPrevMat += $marketSieByGroup[$group].prevMat
}

$latestRecMonthOverall = if ($rxMonthsEn.Count -gt 0) { $rxMonthsEn[-1] } else { $pmCurrentYtdKey }
$recSieOverall = 0.0
$recTotalOverall = 0.0
foreach ($family in $dashboardRecMs.Keys) {
  if ($dashboardRecMs[$family].sie.Contains($latestRecMonthOverall)) {
    $recSieOverall += $dashboardRecMs[$family].sie[$latestRecMonthOverall]
  }
  if ($dashboardRecetas.Contains($family) -and $dashboardRecetas[$family].Contains($latestRecMonthOverall)) {
    $recTotalOverall += $dashboardRecetas[$family][$latestRecMonthOverall].recetas
  }
}

$dashboardKpiStrip = [ordered]@{
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
  ms_rec = if ($recTotalOverall -gt 0) { Round-Number (($recSieOverall / $recTotalOverall) * 100) } else { $null }
  sie_rec_dic25 = [math]::Round($recSieOverall, 0)
  tot_rec_dic25 = [math]::Round($recTotalOverall, 0)
  bud_pct = if ($summary['Totales'].ytdBudget2026 -gt 0) { Round-Number (($summary['Totales'].ytdActual2026 / $summary['Totales'].ytdBudget2026) * 100) } else { $null }
  bud_total = $summary['Totales'].ytdBudget2026
  real_total = $summary['Totales'].ytdActual2026
}

$dashboardMeta = [ordered]@{
  latest_month = $pmCurrentMatKey
  ytd_keys = $pmYtdKeys
  mat_keys = $pmMatKeys
  current_ytd_key = $pmCurrentYtdKey
  prev_ytd_key = $pmPrevYtdKey
  current_mat_key = $pmCurrentMatKey
  prev_mat_key = $pmPrevMatKey
  kpi_ytd_label = ('YTD {0}' -f $pmCurrentYtdKey.Replace(' ', ''''))
  kpi_ytd_prev_label = ('YTD {0}' -f $pmPrevYtdKey.Replace(' ', ''''))
  kpi_mat_label = ('MAT {0}' -f $pmCurrentMatKey.Replace(' ', ''''))
  kpi_mat_prev_label = ('MAT {0}' -f $pmPrevMatKey.Replace(' ', ''''))
  budget_label = if ($budgetCut -match '^([A-Za-z]+)-(\d{4})$') { '{0}''{1}' -f $monthLabel[$monthIndex[$matches[1].ToLower()]], $matches[2].Substring(2) } else { $budgetCut }
  rec_label = if ($latestRecMonthOverall -match '^([A-Za-z]{3}) (\d{4})$') { '{0}''{1}' -f $monthLabel[$monthIndexEn[$matches[1].ToLower()]], $matches[2].Substring(2) } else { $latestRecMonthOverall }
  conv_prev_year = 2024
  conv_current_year = 2025
  canales_prev_year = 2024
  canales_current_year = 2025
  canales_year = 2025
  canales_label = '2025 vs 2024'
  price_prev_label = $pricePrevLabel
  price_curr_label = $priceCurrLabel
  footer_date = '01/04/2026'
}

$dashboardDefaults = [ordered]@{
  brand = 'ISIS'
  market = 'ISIS'
  rec = 'ISIS'
}

$rxCut = ''
if ($null -ne $rxFamiliesOut['Totales'] -and $null -ne $rxFamiliesOut['Totales'].prescriptions) {
  $rxCut = Get-LastNonZeroMonth -Months $rxMonths -Values $rxFamiliesOut['Totales'].prescriptions
}

$dashboardData = [ordered]@{
  meses = @('Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic')
  sieProds = $dashboardFamilyOrder
  colors = $dashboardColors
  compColors = @('#374151', '#6b7280', '#9ca3af', '#d1d5db', '#4b5563', '#1f2937')
  budget = $dashboardBudget
  mol_perf = $pmPerf
  recetas = $dashboardRecetas
  rec_ms = $dashboardRecMs
  rec_comp = $dashboardRecComp
  canales = $dashboardCanales
  convenios = $dashboardConvenios
  stock = $dashboardStock
  stock_alerts = $stockAlerts
  stock_pres = $stockPres
  coverage_labels = $coverageLabels
  precios = $dashboardPrices
  prec_iqvia = $precIqvia
  kpiStrip = $dashboardKpiStrip
  brandKpis = $brandKpis
  sieMolMap = [ordered]@{
    'ACERPES' = 'ACERPES'
    'ACI-TIP' = 'ACI-TIP'
    'ALUMPAK' = 'ALUMPAK'
    'ARTRO RED' = 'ARTRO RED'
    'FLEXINA' = 'FLEXINA'
    'MAGNUS' = 'MAGNUS'
    'TETRALGIN' = 'TETRALGIN'
    'TETRALGIN NOVO' = 'TETRALGIN NOVO'
  }
  molLabels = $molLabels
  prodMap = $prodMap
  budIqviaMap = $budIqviaMap
  meta = $dashboardMeta
  defaults = $dashboardDefaults
}

$data = [ordered]@{
  meta = [ordered]@{
    generatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm')
    sourceDir = $SourceDir
    budgetCut = $budgetCut
    stockCut = $stockCut
    rxCut = $rxCut
    dddCut = if ($dddMonths -and $dddMonths.Count -gt 0) { $dddMonths[-1] } else { '' }
  }
  families = $familyOrder
  familyToMarkets = $familyToMarkets
  summary = $summary
  budget = [ordered]@{
    months = $budgetMonths
    families = $budgetFamilies
    topProducts = $budgetProducts
  }
  stock = [ordered]@{
    months = $stockMonths
    families = $stockFamilies
    topProducts = $stockProducts
  }
  channel = [ordered]@{
    families = $channelFamilies
  }
  osComparison = [ordered]@{
    families = $osFamilies
  }
  prescriptions = [ordered]@{
    months = $rxMonths
    families = $rxFamiliesOut
  }
  marketShare = [ordered]@{
    months = $dddMonths
    families = $dashboardShareOut
  }
  ddd = [ordered]@{
    months = $dddMonths
    markets = $dddMarketsOut
  }
}

$json = $data | ConvertTo-Json -Depth 40 -Compress
$dashboardJson = $dashboardData | ConvertTo-Json -Depth 50 -Compress
$content = "window.MUJER_DATA = $json;`r`nwindow.OTC_DASHBOARD = $dashboardJson;"
Set-Content -LiteralPath $OutputPath -Value $content -Encoding UTF8
Write-Output "Mujer data generated: $OutputPath"
