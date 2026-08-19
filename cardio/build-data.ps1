param(
  [string]$SourceDir = 'C:\Users\camarinaro\Downloads\Hub-Marcas-Inputs\cardio\2026-04\fuentes-originales',
  [string]$OutputPath = (Join-Path $PSScriptRoot 'data.js'),
  # Override opcional para leer el PM IQVIA desde una carpeta centralizada
  # (ej. Hub-Marcas-Inputs/_iqvia-master/2026-04/). Si no se pasa, usa el
  # lookup legacy en $dashboardDir con el patron 'PM ARGENTINA Premium*'.
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
  'DAURAN',
  'DILATREND',
  'DILATREND AP',
  'DILATREND D',
  'DIOVAN',
  'DIOVAN D',
  'EMPAX',
  'EMPAX MET',
  'ENTRESTO',
  'EXFORGE',
  'EXFORGE D',
  'METGLUCON AP',
  'METGLUCON DUO',
  'PIXABAN',
  'ROXOLAN',
  'ROXOLAN PLUS',
  'SILTRAN',
  'SILTRAN MET',
  'SINTROM',
  'SYNCROCOR',
  'SYNCROCOR D',
  'TELPRES',
  'TERLOC'
)

$dashboardColors = [ordered]@{
  'DAURAN' = '#b01e1e'
  'DILATREND' = '#8f1515'
  'DILATREND AP' = '#d97706'
  'DILATREND D' = '#ea580c'
  'DIOVAN' = '#1d4ed8'
  'DIOVAN D' = '#2563eb'
  'EMPAX' = '#059669'
  'EMPAX MET' = '#0d9488'
  'ENTRESTO' = '#7c3aed'
  'EXFORGE' = '#6d28d9'
  'EXFORGE D' = '#db2777'
  'METGLUCON AP' = '#0284c7'
  'METGLUCON DUO' = '#0369a1'
  'PIXABAN' = '#16a34a'
  'ROXOLAN' = '#65a30d'
  'ROXOLAN PLUS' = '#4d7c0f'
  'SILTRAN' = '#0891b2'
  'SILTRAN MET' = '#0f766e'
  'SINTROM' = '#92400e'
  'SYNCROCOR' = '#be123c'
  'SYNCROCOR D' = '#9f1239'
  'TELPRES' = '#7c2d12'
  'TERLOC' = '#4f46e5'
}

$dashboardMarketConfig = [ordered]@{
  'DAURAN' = @{ label = 'Dapagliflozina'; group = 'DAURAN'; filters = @(@{ molecules = @('DAPAGLIFLOZIN'); atcStarts = @('A10P1'); productsLike = @('DAURAN') }); sieProducts = @('DAURAN (SIE)') }
  'DILATREND' = @{ label = 'Carvedilol'; group = 'DILATREND'; filters = @(@{ molecules = @('CARVEDILOL'); atcStarts = @('C07A'); productsLike = @('DILATREND') }); sieProducts = @('DILATREND (SIE)') }
  'DILATREND AP' = @{ label = 'Carvedilol AP'; group = 'DILATREND AP'; filters = @(@{ molecules = @('CARVEDILOL'); atcStarts = @('C07A'); productsLike = @('DILATREND AP') }); sieProducts = @('DILATREND AP (SIE)') }
  'DILATREND D' = @{ label = 'Carvedilol + Diuretico'; group = 'DILATREND D'; filters = @(@{ molecules = @('CARVEDILOL_HYDROCHLOROTHIAZIDE'); atcStarts = @('C07B'); productsLike = @('DILATREND D') }); sieProducts = @('DILATREND D (SIE)') }
  'DIOVAN' = @{ label = 'Valsartan'; group = 'DIOVAN'; filters = @(@{ molecules = @('VALSARTAN'); atcStarts = @('C09C'); productsLike = @('DIOVAN') }); sieProducts = @('DIOVAN (SIE)', 'DIOVAN IC (SIE)') }
  'DIOVAN D' = @{ label = 'Valsartan + Hidroclorotiazida'; group = 'DIOVAN D'; filters = @(@{ molecules = @('HYDROCHLOROTHIAZIDE_VALSARTAN'); atcStarts = @('C09D'); productsLike = @('DIOVAN-D', 'DIOVAN D') }); sieProducts = @('DIOVAN-D (SIE)') }
  'EMPAX' = @{ label = 'Empagliflozina'; group = 'EMPAX'; filters = @(@{ molecules = @('EMPAGLIFLOZIN'); atcStarts = @('A10P1'); productsLike = @('EMPAX') }); sieProducts = @('EMPAX (SIE)') }
  'EMPAX MET' = @{ label = 'Empagliflozina + Metformina'; group = 'EMPAX MET'; filters = @(@{ molecules = @('EMPAGLIFLOZIN_METFORMIN'); atcStarts = @('A10M'); productsLike = @('EMPAX MET') }); sieProducts = @('EMPAX MET (SIE)') }
  'ENTRESTO' = @{ label = 'Sacubitril + Valsartan'; group = 'ENTRESTO'; filters = @(@{ molecules = @('SACUBITRIL_VALSARTAN'); atcStarts = @('C09D'); productsLike = @('ENTRESTO') }); sieProducts = @('ENTRESTO (SIE)') }
  'EXFORGE' = @{ label = 'Amlodipina + Valsartan'; group = 'EXFORGE'; filters = @(@{ molecules = @('AMLODIPINE_VALSARTAN'); atcStarts = @('C09D'); productsLike = @('EXFORGE') }); sieProducts = @('EXFORGE (SIE)') }
  'EXFORGE D' = @{ label = 'Amlodipina + HCT + Valsartan'; group = 'EXFORGE D'; filters = @(@{ molecules = @('AMLODIPINE_HYDROCHLOROTHIAZIDE_VALSARTAN'); atcStarts = @('C09D'); productsLike = @('EXFORGE D') }); sieProducts = @('EXFORGE D (SIE)') }
  'METGLUCON AP' = @{ label = 'Metformina'; group = 'METGLUCON AP'; filters = @(@{ molecules = @('METFORMIN'); atcStarts = @('A10J'); productsLike = @('METGLUCON AP', 'METGLUCON') }); sieProducts = @('METGLUCON AP (SIE)', 'METGLUCON (SIE)') }
  'METGLUCON DUO' = @{ label = 'Glibenclamida + Metformina'; group = 'METGLUCON DUO'; filters = @(@{ molecules = @('GLIBENCLAMIDE_METFORMIN'); atcStarts = @('A10M'); productsLike = @('METGLUCON DUO') }); sieProducts = @('METGLUCON DUO (SIE)') }
  'PIXABAN' = @{ label = 'Apixaban'; group = 'PIXABAN'; filters = @(@{ molecules = @('APIXABAN'); atcStarts = @('B01F'); productsLike = @('PIXABAN') }); sieProducts = @('PIXABAN (SIE)') }
  'ROXOLAN' = @{ label = 'Rosuvastatina'; group = 'ROXOLAN'; filters = @(@{ molecules = @('ROSUVASTATIN'); atcStarts = @('C10A','C10B'); productsLike = @('ROXOLAN') }); sieProducts = @('ROXOLAN (SIE)') }
  'ROXOLAN PLUS' = @{ label = 'Rosuvastatina + Ezetimibe'; group = 'ROXOLAN PLUS'; filters = @(@{ molecules = @('EZETIMIBE_ROSUVASTATIN'); atcStarts = @('C10C') }); sieProducts = @('ROXOLAN PLUS (SIE)') }
  'SILTRAN' = @{ label = 'Sitagliptina'; group = 'SILTRAN'; filters = @(@{ molecules = @('SITAGLIPTIN'); atcStarts = @('A10H'); productsLike = @('SILTRAN') }); sieProducts = @('SILTRAN (SIE)') }
  'SILTRAN MET' = @{ label = 'Sitagliptina + Metformina'; group = 'SILTRAN MET'; filters = @(@{ molecules = @('METFORMIN_SITAGLIPTIN'); atcStarts = @('A10M'); productsLike = @('SILTRAN MET') }); sieProducts = @('SILTRAN MET (SIE)') }
  'SINTROM' = @{ label = 'Acenocumarol'; group = 'SINTROM'; filters = @(@{ molecules = @('ACENOCOUMAROL'); atcStarts = @('B01A'); productsLike = @('SINTROM') }); sieProducts = @('SINTROM (SIE)') }
  # SYNCROCOR / SYNCROCOR D: el matcheo de molecula es por Contains, y
  # 'HYDROCHLOROTHIAZIDE_NEBIVOLOL'.Contains('NEBIVOLOL') -> el mercado del mono se
  # tragaria el combo (regla #2 de CLAUDE.md). El mercado REAL (molecula exacta), la
  # venta y el stock (las 5 presentaciones comparten Familia SAP 'SYNCROCOR') y las
  # recetas (mercado 'NEBIVOLOL (NEBILET)') los re-aplica SIEMPRE
  # shared/onboard-cardio-syncrocor.py, que corre despues del build en update-all.ps1.
  'SYNCROCOR' = @{ label = 'Nebivolol'; group = 'SYNCROCOR'; filters = @(@{ molecules = @('NEBIVOLOL'); atcStarts = @('C07A'); productsLike = @('SYNCROCOR') }); sieProducts = @('SYNCROCOR (SIE)') }
  'SYNCROCOR D' = @{ label = 'Nebivolol + Hidroclorotiazida'; group = 'SYNCROCOR D'; filters = @(@{ molecules = @('HYDROCHLOROTHIAZIDE_NEBIVOLOL'); atcStarts = @('C07B'); productsLike = @('SYNCROCOR D') }); sieProducts = @('SYNCROCOR D (SIE)') }
  'TELPRES' = @{ label = 'Telmisartan'; group = 'TELPRES'; filters = @(@{ molecules = @('TELMISARTAN'); atcStarts = @('C09C'); productsLike = @('TELPRES') }); sieProducts = @('TELPRES (SIE)') }
  'TERLOC' = @{ label = 'Amlodipina'; group = 'TERLOC'; filters = @(@{ molecules = @('AMLODIPINE'); atcStarts = @('C08C'); productsLike = @('TERLOC') }); sieProducts = @('TERLOC (SIE)') }
}

$familyOrder = @(
  'Totales',
  'DAURAN','DILATREND','DILATREND AP','DILATREND D','DIOVAN','DIOVAN D','EMPAX','EMPAX MET','ENTRESTO','EXFORGE','EXFORGE D','METGLUCON AP','METGLUCON DUO','PIXABAN','ROXOLAN','ROXOLAN PLUS','SILTRAN','SILTRAN MET','SINTROM','SYNCROCOR','SYNCROCOR D','TELPRES','TERLOC'
)

$dddMarketConfig = [ordered]@{
  'Terloc' = @{ family = 'TERLOC'; keywords = @('TERLOC') }
  'Dauran' = @{ family = 'DAURAN'; keywords = @('DAURAN') }
  'Siltran Flia' = @{ family = 'SILTRAN'; keywords = @('SILTRAN') }
  'Siltran Met' = @{ family = 'SILTRAN MET'; keywords = @('SILTRAN MET') }
  'Siltran' = @{ family = 'SILTRAN'; keywords = @('SILTRAN') }
  'Diovan' = @{ family = 'DIOVAN'; keywords = @('DIOVAN') }
  'Dilatrend (Carvedilol)' = @{ family = 'DILATREND'; keywords = @('DILATREND') }
  'Apixaban (Pixaban)' = @{ family = 'PIXABAN'; keywords = @('PIXABAN') }
  'Roxolan (Rosuvastatina)' = @{ family = 'ROXOLAN'; keywords = @('ROXOLAN') }
  'Roxolan Plus' = @{ family = 'ROXOLAN PLUS'; keywords = @('ROXOLAN') }
  'Metglucon' = @{ family = 'METGLUCON AP'; keywords = @('METGLUCON') }
  'Telpres' = @{ family = 'TELPRES'; keywords = @('TELPRES') }
  'Exforge' = @{ family = 'EXFORGE'; keywords = @('EXFORGE') }
  'Empax' = @{ family = 'EMPAX'; keywords = @('EMPAX') }
  'Entresto' = @{ family = 'ENTRESTO'; keywords = @('ENTRESTO') }
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

function Get-FirstExistingPath {
  param(
    [string[]]$Paths
  )

  foreach ($path in $Paths) {
    if ($path -and (Test-Path -LiteralPath $path)) {
      return $path
    }
  }

  return $null
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

function Get-QuarterKeyFromMonthLabelEn {
  param([string]$MonthLabel)

  if ($MonthLabel -match '^([A-Za-z]{3}) (\d{4})$') {
    $monthToken = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndexEn.ContainsKey($monthToken)) {
      $month = $monthIndexEn[$monthToken]
      $quarter = switch ($month) {
        { $_ -in 1, 2, 3 } { 'Q1' }
        { $_ -in 4, 5, 6 } { 'Q2' }
        { $_ -in 7, 8, 9 } { 'Q3' }
        { $_ -in 10, 11, 12 } { 'Q4' }
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

function Resolve-InternalSalesFamily {
  param(
    [string]$GranFamily,
    [string]$Family,
    [string]$Product
  )

  $gran = (Normalize-Text $GranFamily).ToUpper()
  $family = (Normalize-Text $Family).ToUpper()
  $product = (Normalize-Text $Product).ToUpper()

  foreach ($candidate in @($family, $gran)) {
    switch ($candidate) {
      'TOTALES' { return 'Totales' }
      'DAURAN' { return 'DAURAN' }
      'DILATREND' { return 'DILATREND' }
      'DILATREND AP' { return 'DILATREND AP' }
      'DILATREND D' { return 'DILATREND D' }
      'DIOVAN' { return 'DIOVAN' }
      'DIOVAN D' { return 'DIOVAN D' }
      'EMPAX' { return 'EMPAX' }
      'EMPAX MET' { return 'EMPAX MET' }
      'ENTRESTO' { return 'ENTRESTO' }
      'EXFORGE' { return 'EXFORGE' }
      'EXFORGE D' { return 'EXFORGE D' }
      'METGLUCON AP' { return 'METGLUCON AP' }
      'METGLUCON DUO' { return 'METGLUCON DUO' }
      'PIXABAN' { return 'PIXABAN' }
      'ROXOLAN' { return 'ROXOLAN' }
      'ROXOLAN PLUS' { return 'ROXOLAN PLUS' }
      'SILTRAN' { return 'SILTRAN' }
      'SILTRAN MET' { return 'SILTRAN MET' }
      'SINTROM' { return 'SINTROM' }
      # OJO: en SAP las 5 presentaciones (incluida la del combo) comparten
      # Familia = 'SYNCROCOR' -> esto le da TODO al mono. El reparto real por
      # presentacion lo re-aplica shared/onboard-cardio-syncrocor.py.
      'SYNCROCOR' { return 'SYNCROCOR' }
      'SYNCROCOR D' { return 'SYNCROCOR D' }
      'TELPRES' { return 'TELPRES' }
      'TERLOC' { return 'TERLOC' }
    }
  }

  if ($product -eq 'TOTALES') {
    switch ($family) {
      'DILATREND AP' { return 'DILATREND AP' }
      'DILATREND D' { return 'DILATREND D' }
      'DIOVAN D' { return 'DIOVAN D' }
      'EMPAX MET' { return 'EMPAX MET' }
      'EXFORGE D' { return 'EXFORGE D' }
      'METGLUCON AP' { return 'METGLUCON AP' }
      'METGLUCON DUO' { return 'METGLUCON DUO' }
      'SILTRAN MET' { return 'SILTRAN MET' }
    }
  }

  return ''
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
    $hasMoleculeRule = ($filter.ContainsKey('molecules') -and $filter.molecules.Count -gt 0)
    $hasAtcRule = ($filter.ContainsKey('atcStarts') -and $filter.atcStarts.Count -gt 0)

    if ($hasMoleculeRule) {
      $moleculeMatch = $false
      foreach ($candidate in $filter.molecules) {
        $candidateUpper = $candidate.ToUpper()
        if ($moleculeUpper -eq $candidateUpper -or $moleculeUpper.Contains($candidateUpper)) {
          $moleculeMatch = $true
          break
        }
      }
    }

    if ($hasAtcRule) {
      $atcMatch = $false
      foreach ($candidate in $filter.atcStarts) {
        if ($atcUpper.StartsWith($candidate.ToUpper())) {
          $atcMatch = $true
          break
        }
      }
    }

    if (-not ($hasMoleculeRule -or $hasAtcRule) -and $filter.ContainsKey('productsLike') -and $filter.productsLike.Count -gt 0) {
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

function Get-SegmentKey {
  param([object]$Value)

  $text = (Normalize-Text $Value).ToUpper()
  if (-not $text) { return 'unknown' }
  if ($text.Contains('POPULAR') -or $text.Contains('OTC')) { return 'popular' }
  if ($text.Contains('ETICO') -or $text.Contains('ETHICAL')) { return 'etico' }
  return 'unknown'
}

function Get-ConfigMoleculeRules {
  param([hashtable]$Config)

  $rules = New-Object 'System.Collections.Generic.List[string]'
  foreach ($filter in $Config.filters) {
    if ($filter.ContainsKey('molecules')) {
      foreach ($candidate in $filter.molecules) {
        $value = (Normalize-Text $candidate).ToUpper()
        if ($value -and -not $rules.Contains($value)) {
          $rules.Add($value)
        }
      }
    }
  }
  return @($rules)
}

function Get-ConfigAtcRules {
  param([hashtable]$Config)

  $rules = New-Object 'System.Collections.Generic.List[string]'
  foreach ($filter in $Config.filters) {
    if ($filter.ContainsKey('atcStarts')) {
      foreach ($candidate in $filter.atcStarts) {
        $value = (Normalize-Text $candidate).ToUpper()
        if ($value -and -not $rules.Contains($value)) {
          $rules.Add($value)
        }
      }
    }
  }
  return @($rules)
}

function Test-TextEqualsAny {
  param(
    [string]$Text,
    [string[]]$Candidates
  )

  # Igualdad EXACTA, no substring. El filtro `molecules` del config nombra LA molecula
  # del mercado ('VALSARTAN'), y matchear con .Contains() metia los COMBOS en el mercado
  # mono: 'HYDROCHLOROTHIAZIDE_VALSARTAN'.Contains('VALSARTAN') = $true.
  # En Jul-2026 eso inflo 11 familias de cardio -- DIOVAN x1,90 (el mercado de valsartan
  # mono pasaba de 731.273 a 1.389.281 sumando los combos, que YA tienen su propia
  # familia DIOVAN D), TERLOC x1,98, SILTRAN x1,84, ROXOLAN x1,16. Es exactamente la
  # regla critica #2 de CLAUDE.md (una familia = UN mercado de la fuente) y el bug
  # historico de ROXOLAN (rosuvastatina vs rosuvastatina/ezetimibe).
  # Ningun gate lo veia: sum(productos) == total de familia cerraba sobre el universo
  # equivocado. Se verifico contra el master que con igualdad ninguna familia queda en
  # cero y todas caen a <=0,25% del valor publicado.
  if (-not $Text -or -not $Candidates -or $Candidates.Count -eq 0) { return $false }
  foreach ($candidate in $Candidates) {
    if ($candidate -and $Text -eq $candidate) {
      return $true
    }
  }
  return $false
}

function Test-TextContainsAny {
  param(
    [string]$Text,
    [string[]]$Candidates
  )

  if (-not $Text -or -not $Candidates -or $Candidates.Count -eq 0) { return $false }
  foreach ($candidate in $Candidates) {
    if ($candidate -and ($Text -eq $candidate -or $Text.Contains($candidate))) {
      return $true
    }
  }
  return $false
}

function Test-AtcStartsAny {
  param(
    [string]$Text,
    [string[]]$Candidates
  )

  if (-not $Text -or -not $Candidates -or $Candidates.Count -eq 0) { return $false }
  foreach ($candidate in $Candidates) {
    if ($candidate -and $Text.StartsWith($candidate)) {
      return $true
    }
  }
  return $false
}

function New-SeriesMap {
  param([string[]]$Keys)

  $map = @{}
  foreach ($key in $Keys) {
    $map[$key] = 0.0
  }
  return $map
}

function New-PerfBucket {
  param(
    [string[]]$MonthlyKeys,
    [string[]]$YtdKeys,
    [string[]]$MatKeys,
    [string[]]$QuarterKeys
  )

  return @{
    products = @{}
    marketMonthly = (New-SeriesMap $MonthlyKeys)
    marketYtd = (New-SeriesMap $YtdKeys)
    marketMat = (New-SeriesMap $MatKeys)
    marketQuarterly = (New-SeriesMap $QuarterKeys)
  }
}

function Ensure-PerfBucketProduct {
  param(
    [hashtable]$Bucket,
    [string]$Product,
    [string]$Manufacturer,
    [bool]$IsSie,
    [string[]]$MonthlyKeys,
    [string[]]$YtdKeys,
    [string[]]$MatKeys,
    [string[]]$QuarterKeys
  )

  if (-not $Bucket.products.ContainsKey($Product)) {
    $Bucket.products[$Product] = @{
      manuf = $Manufacturer
      is_sie = $IsSie
      monthly = (New-SeriesMap $MonthlyKeys)
      ytd = (New-SeriesMap $YtdKeys)
      mat = (New-SeriesMap $MatKeys)
      quarterly = (New-SeriesMap $QuarterKeys)
    }
  }
  elseif ($IsSie) {
    $Bucket.products[$Product].is_sie = $true
  }
}

function Convert-PerfBucket {
  param(
    [hashtable]$Bucket,
    [string[]]$SieProducts,
    [string]$Family,
    [string[]]$MonthlyKeys,
    [string[]]$YtdKeys,
    [string[]]$MatKeys,
    [string[]]$QuarterKeys,
    [string]$CurrentMatKey,
    [string]$CurrentYtdKey,
    [hashtable]$ProductMatLookup
  )

  $productRows = @(
    $Bucket.products.Keys |
      ForEach-Object {
        $item = $Bucket.products[$_]
        [pscustomobject]@{
          name = $_
          manuf = $item.manuf
          is_sie = [bool]$item.is_sie
          currentMat = [math]::Round(($item.mat[$CurrentMatKey]), 0)
          currentYtd = [math]::Round(($item.ytd[$CurrentYtdKey]), 0)
        }
      } |
      Sort-Object -Property @{ Expression = 'currentMat'; Descending = $true }, @{ Expression = 'currentYtd'; Descending = $true }
  )

  $selectedProductNames = New-Object 'System.Collections.Generic.List[string]'
  foreach ($prodName in $SieProducts) {
    if ($Bucket.products.ContainsKey($prodName) -and -not $selectedProductNames.Contains($prodName)) {
      $selectedProductNames.Add($prodName)
    }
  }
  foreach ($row in $productRows) {
    if ($selectedProductNames.Count -ge 8) { break }
    if (-not $selectedProductNames.Contains($row.name)) {
      $selectedProductNames.Add($row.name)
    }
  }

  if ($null -ne $ProductMatLookup) {
    $ProductMatLookup.Clear()
  }

  $productsOut = @(
    foreach ($prodName in $selectedProductNames) {
      $item = $Bucket.products[$prodName]
      if ($null -ne $ProductMatLookup) {
        $baseKey = Normalize-ProductKey $prodName
        if ($baseKey -and -not $ProductMatLookup.ContainsKey($baseKey)) {
          $ProductMatLookup[$baseKey] = [math]::Round(($item.mat[$CurrentMatKey]), 0)
        }
      }

      $monthlyVals = [ordered]@{}
      $ytdVals = [ordered]@{}
      $matVals = [ordered]@{}
      $quarterlyVals = [ordered]@{}
      $msMonthly = [ordered]@{}
      $msQuarterly = [ordered]@{}
      $msYtd = [ordered]@{}
      $msMat = [ordered]@{}

      foreach ($key in $MonthlyKeys) {
        $units = [math]::Round(($item.monthly[$key]), 0)
        $monthlyVals[$key] = $units
        $msMonthly[$key] = if ($Bucket.marketMonthly[$key] -gt 0) { Round-Number (($item.monthly[$key] / $Bucket.marketMonthly[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $YtdKeys) {
        $units = [math]::Round(($item.ytd[$key]), 0)
        $ytdVals[$key] = $units
        $msYtd[$key] = if ($Bucket.marketYtd[$key] -gt 0) { Round-Number (($item.ytd[$key] / $Bucket.marketYtd[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $MatKeys) {
        $units = [math]::Round(($item.mat[$key]), 0)
        $matVals[$key] = $units
        $msMat[$key] = if ($Bucket.marketMat[$key] -gt 0) { Round-Number (($item.mat[$key] / $Bucket.marketMat[$key]) * 100) } else { 0.0 }
      }
      foreach ($key in $QuarterKeys) {
        $units = [math]::Round(($item.quarterly[$key]), 0)
        $quarterlyVals[$key] = $units
        $msQuarterly[$key] = if ($Bucket.marketQuarterly[$key] -gt 0) { Round-Number (($item.quarterly[$key] / $Bucket.marketQuarterly[$key]) * 100) } else { 0.0 }
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

  # RESTO DEL MERCADO (cola larga): mercado_completo - suma(productos emitidos top-8).
  # Restaura el invariante sum(products)=mercado completo para que MS%/IE de TODOS los
  # consumidores que suman products[] (build-kpis, build-families, fix-brandkpis,
  # recompute) queden correctos SIN tocarlos. is_sie=false e is_resto=true: nunca entra
  # al numerador SIE; el render lo muestra como 'Otros' gris, ultimo. Solo si hay cola.
  $restoMonthly = [ordered]@{}; $restoYtd = [ordered]@{}; $restoMat = [ordered]@{}; $restoQuarterly = [ordered]@{}
  $restoMsMonthly = [ordered]@{}; $restoMsYtd = [ordered]@{}; $restoMsMat = [ordered]@{}; $restoMsQuarterly = [ordered]@{}
  $restoHasTail = $false
  foreach ($key in $MonthlyKeys) {
    $sel = 0.0; foreach ($n in $selectedProductNames) { $sel += $Bucket.products[$n].monthly[$key] }
    $val = $Bucket.marketMonthly[$key] - $sel; if ($val -lt 0) { $val = 0.0 }
    if ($val -gt 0.5) { $restoHasTail = $true }
    $restoMonthly[$key] = [math]::Round($val, 0)
    $restoMsMonthly[$key] = if ($Bucket.marketMonthly[$key] -gt 0) { Round-Number (($val / $Bucket.marketMonthly[$key]) * 100) } else { 0.0 }
  }
  foreach ($key in $YtdKeys) {
    $sel = 0.0; foreach ($n in $selectedProductNames) { $sel += $Bucket.products[$n].ytd[$key] }
    $val = $Bucket.marketYtd[$key] - $sel; if ($val -lt 0) { $val = 0.0 }
    $restoYtd[$key] = [math]::Round($val, 0)
    $restoMsYtd[$key] = if ($Bucket.marketYtd[$key] -gt 0) { Round-Number (($val / $Bucket.marketYtd[$key]) * 100) } else { 0.0 }
  }
  foreach ($key in $MatKeys) {
    $sel = 0.0; foreach ($n in $selectedProductNames) { $sel += $Bucket.products[$n].mat[$key] }
    $val = $Bucket.marketMat[$key] - $sel; if ($val -lt 0) { $val = 0.0 }
    $restoMat[$key] = [math]::Round($val, 0)
    $restoMsMat[$key] = if ($Bucket.marketMat[$key] -gt 0) { Round-Number (($val / $Bucket.marketMat[$key]) * 100) } else { 0.0 }
  }
  foreach ($key in $QuarterKeys) {
    $sel = 0.0; foreach ($n in $selectedProductNames) { $sel += $Bucket.products[$n].quarterly[$key] }
    $val = $Bucket.marketQuarterly[$key] - $sel; if ($val -lt 0) { $val = 0.0 }
    $restoQuarterly[$key] = [math]::Round($val, 0)
    $restoMsQuarterly[$key] = if ($Bucket.marketQuarterly[$key] -gt 0) { Round-Number (($val / $Bucket.marketQuarterly[$key]) * 100) } else { 0.0 }
  }
  if ($restoHasTail) {
    $productsOut = @($productsOut) + @([ordered]@{
      prod = 'Otros (resto del mercado)'
      manuf = 'OTROS'
      is_sie = $false
      is_resto = $true
      monthly_vals = $restoMonthly
      ytd = $restoYtd
      mat = $restoMat
      ms_ytd = $restoMsYtd
      ms_mat = $restoMsMat
      quarterly_vals = $restoQuarterly
      ms_monthly = $restoMsMonthly
      ms_quarterly = $restoMsQuarterly
    })
  }

  $marketMonthlyOut = [ordered]@{}
  $marketYtdOut = [ordered]@{}
  $marketMatOut = [ordered]@{}
  $marketQuarterlyOut = [ordered]@{}
  foreach ($key in $MonthlyKeys) { $marketMonthlyOut[$key] = [math]::Round($Bucket.marketMonthly[$key], 0) }
  foreach ($key in $YtdKeys) { $marketYtdOut[$key] = [math]::Round($Bucket.marketYtd[$key], 0) }
  foreach ($key in $MatKeys) { $marketMatOut[$key] = [math]::Round($Bucket.marketMat[$key], 0) }
  foreach ($key in $QuarterKeys) { $marketQuarterlyOut[$key] = [math]::Round($Bucket.marketQuarterly[$key], 0) }

  return [ordered]@{
    family = $Family
    products = $productsOut
    ytd = $marketYtdOut
    mat = $marketMatOut
    monthly = $marketMonthlyOut
    quarterly = $marketQuarterlyOut
  }
}

function New-DddBucket {
  return @{
    monthly = @{}
    regions = @{}
    products = @{}
  }
}

function Add-DddBucketRow {
  param(
    [hashtable]$Bucket,
    [string]$Month,
    [string]$Region,
    [string]$Product,
    [double]$Units,
    [bool]$IsSie
  )

  Ensure-NestedMetric -Map $Bucket.monthly -Key $Month
  $Bucket.monthly[$Month].total += $Units
  if ($IsSie) { $Bucket.monthly[$Month].sie += $Units }

  if (-not $Bucket.regions.ContainsKey($Month)) { $Bucket.regions[$Month] = @{} }
  Ensure-NestedMetric -Map $Bucket.regions[$Month] -Key $Region
  $Bucket.regions[$Month][$Region].total += $Units
  if ($IsSie) { $Bucket.regions[$Month][$Region].sie += $Units }

  if (-not $Bucket.products.ContainsKey($Month)) { $Bucket.products[$Month] = @{} }
  if (-not $Bucket.products[$Month].ContainsKey($Product)) {
    $Bucket.products[$Month][$Product] = @{ units = 0.0; isSie = $IsSie }
  }
  $Bucket.products[$Month][$Product].units += $Units
  if ($IsSie) { $Bucket.products[$Month][$Product].isSie = $true }
}

function Convert-DddBucket {
  param(
    [hashtable]$Bucket,
    [string[]]$Months,
    [string]$Family
  )

  $monthlyRows = foreach ($month in $Months) {
    $item = if ($Bucket.monthly.ContainsKey($month)) { $Bucket.monthly[$month] } else { @{ total = 0.0; sie = 0.0 } }
    [ordered]@{
      month = $month
      total = [math]::Round($item.total, 0)
      sie = [math]::Round($item.sie, 0)
      share = if ($item.total -gt 0) { Round-Number (($item.sie / $item.total) * 100) } else { 0.0 }
    }
  }

  $regionsByMonth = [ordered]@{}
  $productsByMonth = [ordered]@{}
  foreach ($month in $Months) {
    $regionRows = @()
    if ($Bucket.regions.ContainsKey($month)) {
      $regionRows = Convert-MetricMap $Bucket.regions[$month]
    }
    $regionsByMonth.Add($month, @(
      $regionRows | Sort-Object -Property @{ Expression = 'share'; Descending = $true }, @{ Expression = 'total'; Descending = $true }
    ))

    $productRows = @()
    if ($Bucket.products.ContainsKey($month)) {
      $totalUnits = 0.0
      foreach ($name in $Bucket.products[$month].Keys) {
        $totalUnits += $Bucket.products[$month][$name].units
      }

      $productRows = @(
        $Bucket.products[$month].Keys |
          ForEach-Object {
            $item = $Bucket.products[$month][$_]
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

  $monthList = @($Months)
  $monthCount = ($monthList | Measure-Object).Count
  $latestMonth = if ($monthCount -gt 0) { $monthList[-1] } else { '' }
  return [ordered]@{
    family = $Family
    latestMonth = $latestMonth
    monthly = $monthlyRows
    regionsByMonth = $regionsByMonth
    productsByMonth = $productsByMonth
  }
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

$dashboardDir = if (Test-Path -LiteralPath (Join-Path $SourceDir 'dashboard')) { Join-Path $SourceDir 'dashboard' } else { $SourceDir }
$dddDir = if (Test-Path -LiteralPath (Join-Path $SourceDir 'ddd')) { Join-Path $SourceDir 'ddd' } else { $SourceDir }

if (-not (Test-Path -LiteralPath $dashboardDir)) {
  throw "La carpeta de dashboard no existe: $dashboardDir"
}
if (-not (Test-Path -LiteralPath $dddDir)) {
  throw "La carpeta de DDD no existe: $dddDir"
}

$budgetPath = $null
$internalSalesPath = try { Get-MatchingPath -Dir $dashboardDir -Include 'VENTA*' } catch { $null }
$rxPath = Get-MatchingPath -Dir $dashboardDir -Include 'RECETAS*'
$stockPath = Get-MatchingPath -Dir $dashboardDir -Include 'STOCK Y VENTAS*'
$channel2024DashboardPath = try { Get-MatchingPath -Dir $dashboardDir -Include 'Convenios vs mostrador*.xlsx' -Exclude '*(*' } catch { $null }
$channel2025DashboardPath = try { Get-MatchingPath -Dir $dashboardDir -Include 'Convenios vs mostrador*(*).xlsx' } catch { $null }
$channel2024Path = Get-FirstExistingPath @(
  'C:\Users\camarinaro\Downloads\Convenios vs mostrador - 10 de abril de 2026.xlsx',
  $channel2024DashboardPath
)
$channel2025Path = Get-FirstExistingPath @(
  'C:\Users\camarinaro\Downloads\Convenios vs mostrador - 10 de abril de 2026 (1).xlsx',
  $channel2025DashboardPath
)
$conv2024Path = Get-MatchingPath -Dir $dashboardDir -Include 'CONVENIOS 2024*'
$conv2025Path = Get-MatchingPath -Dir $dashboardDir -Include 'CONVENIOS 2025*'
$dddPath = Get-MatchingPath -Dir $dddDir -Include '*.xlsx'
$pmPath = Get-MatchingPath -Dir $(if ($IqviaDir) { $IqviaDir } else { $dashboardDir }) -Include $(if ($IqviaPattern) { $IqviaPattern } else { 'PM ARGENTINA Premium*' })
$pricePath = Get-MatchingPath -Dir $dashboardDir -Include 'PRECIOS*'

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

Write-Host "[Cardio] Leyendo fuentes..."

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
  $budgetMatrix = if ($budgetPath) { Open-Matrix -Excel $excel -Path $budgetPath } else { $null }
  $internalSalesMatrix = if ($internalSalesPath) { Open-Matrix -Excel $excel -Path $internalSalesPath } else { $null }
  $rxMatrix = Open-Matrix -Excel $excel -Path $rxPath
  $stockMatrix = Open-Matrix -Excel $excel -Path $stockPath
  $channel2024Matrix = if ($channel2024Path) { Open-Matrix -Excel $excel -Path $channel2024Path } else { $null }
  $channel2025Matrix = if ($channel2025Path) { Open-Matrix -Excel $excel -Path $channel2025Path } else { $null }
  $conv2024Matrix = Open-Matrix -Excel $excel -Path $conv2024Path
  $conv2025Matrix = Open-Matrix -Excel $excel -Path $conv2025Path
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

Write-Host "[Respiratorio] Fuentes cargadas."

$budgetMonths = @()
$budgetFamilies = [ordered]@{}
$budgetProducts = [ordered]@{}
if ($budgetMatrix) {
  for ($c = 3; $c -le $budgetMatrix.GetLength(1); $c += 3) {
    $budgetMonths += Normalize-MonthLabel $budgetMatrix[1, $c]
  }

  for ($r = 3; $r -le $budgetMatrix.GetLength(0); $r++) {
    $family = Normalize-Text $budgetMatrix[$r, 1]
    $product = Normalize-Text $budgetMatrix[$r, 2]
    if (-not $family) {
      continue
    }

    $actual = New-Object System.Collections.Generic.List[double]
    $budget = New-Object System.Collections.Generic.List[double]
    $compliance = New-Object System.Collections.Generic.List[double]

    for ($c = 3; $c -le $budgetMatrix.GetLength(1); $c += 3) {
      $actual.Add((To-Number $budgetMatrix[$r, $c]))
      $budget.Add((To-Number $budgetMatrix[$r, ($c + 1)]))
      $compliance.Add((Round-Number ((To-Number $budgetMatrix[$r, ($c + 2)]) * 100)))
    }

    if ($family -eq 'Totales' -or $product -eq 'Totales' -or -not $product) {
      Ensure-OrderedMap -Map $budgetFamilies -Key $family -Value ([ordered]@{
        actual = @($actual)
        budget = @($budget)
        compliance = @($compliance)
      })
      continue
    }

    if (-not $budgetProducts.Contains($family)) {
      $budgetProducts.Add($family, @())
    }

    $latestIndex = $actual.Count - 1
    while ($latestIndex -ge 0 -and $actual[$latestIndex] -le 0) {
      $latestIndex--
    }

    $budgetProducts[$family] += [pscustomobject][ordered]@{
      name = $product
      totalActual = [math]::Round(($actual | Measure-Object -Sum).Sum, 0)
      ytd2026 = Get-YtdSum -Months $budgetMonths -Values @($actual) -Year 2026 -CutMonth (Get-LastNonZeroMonth -Months $budgetMonths -Values @($actual))
      latestActual = if ($latestIndex -ge 0) { [math]::Round($actual[$latestIndex], 0) } else { 0 }
    }
  }

  $budgetCut = Get-LastNonZeroMonth -Months $budgetMonths -Values $budgetFamilies['Totales'].actual
  foreach ($family in @($budgetProducts.Keys)) {
    $budgetProducts[$family] = @(
      $budgetProducts[$family] |
        Sort-Object -Property @{ Expression = 'ytd2026'; Descending = $true }, @{ Expression = 'totalActual'; Descending = $true } |
        Select-Object -First 8
    )
  }
}
else {
  $budgetMonths = @(
    'Ene-2025','Feb-2025','Mar-2025','Abr-2025','May-2025','Jun-2025','Jul-2025','Ago-2025','Sep-2025','Oct-2025','Nov-2025','Dic-2025',
    'Ene-2026','Feb-2026','Mar-2026','Abr-2026','May-2026','Jun-2026','Jul-2026','Ago-2026','Sep-2026','Oct-2026','Nov-2026','Dic-2026'
  )
  foreach ($family in $familyOrder) {
    $budgetFamilies[$family] = [ordered]@{
      actual = @(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
      budget = @(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
      compliance = @(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)
    }
  }
  $budgetCut = 'Abr-2026'
}

if (-not $budgetPath -and $internalSalesMatrix) {
  foreach ($family in $familyOrder) {
    if (-not $budgetFamilies.Contains($family)) {
      $budgetFamilies[$family] = [ordered]@{
        actual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
        budget = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
        compliance = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
      }
    }
  }

  for ($r = 3; $r -le $internalSalesMatrix.GetLength(0); $r++) {
    $granFamily = Normalize-Text $internalSalesMatrix[$r, 2]
    $familyLabel = Normalize-Text $internalSalesMatrix[$r, 3]
    $product = Normalize-Text $internalSalesMatrix[$r, 4]
    $family = Resolve-InternalSalesFamily -GranFamily $granFamily -Family $familyLabel -Product $product
    if (-not $family -or ($product -and $product -ne 'Totales')) {
      continue
    }
    if (-not $budgetFamilies.Contains($family)) {
      continue
    }

    $actualSeries = @($budgetFamilies[$family].actual)
    for ($c = 7; $c -le $internalSalesMatrix.GetLength(1); $c++) {
      $monthKey = Normalize-MonthLabel $internalSalesMatrix[2, $c]
      $budgetIdx = $budgetMonths.IndexOf($monthKey)
      if ($budgetIdx -lt 0) {
        continue
      }
      $actualSeries[$budgetIdx] = To-Number $internalSalesMatrix[$r, $c]
    }
    $budgetFamilies[$family].actual = @($actualSeries)
  }

  $totalActual = @(for ($i = 0; $i -lt $budgetMonths.Count; $i++) { 0.0 })
  foreach ($family in $dashboardFamilyOrder) {
    if (-not $budgetFamilies.Contains($family)) {
      continue
    }
    for ($i = 0; $i -lt $budgetMonths.Count; $i++) {
      $totalActual[$i] += To-Number $budgetFamilies[$family].actual[$i]
    }
  }
  $budgetFamilies['Totales'].actual = @($totalActual)

  $internalCut = Get-LastNonZeroMonth -Months $budgetMonths -Values $budgetFamilies['Totales'].actual
  if ($internalCut) {
    $budgetCut = $internalCut
  }
}

$stockMonths = @()
for ($c = 8; $c -le $stockMatrix.GetLength(1); $c += 4) {
  $stockMonths += Normalize-MonthLabel $stockMatrix[1, $c]
}

$stockFamilies = [ordered]@{}
$stockProducts = [ordered]@{}
$stockProductSeries = [ordered]@{}
for ($r = 3; $r -le $stockMatrix.GetLength(0); $r++) {
  $family = Normalize-Text $stockMatrix[$r, 2]
  $product = Normalize-Text $stockMatrix[$r, 3]
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

$channelFamilies = [ordered]@{}
function Get-ChannelFamilyEntry {
  return [ordered]@{
    prev = [ordered]@{
      facturedUnits = 0
      convenioUnits = 0
      mostradorUnits = 0
      convenioPct = 0.0
      mostradorPct = 0.0
      discountCommonPct = 0.0
      discountConvenioPct = 0.0
      discountTotalPct = 0.0
    }
    current = [ordered]@{
      facturedUnits = 0
      convenioUnits = 0
      mostradorUnits = 0
      convenioPct = 0.0
      mostradorPct = 0.0
      discountCommonPct = 0.0
      discountConvenioPct = 0.0
      discountTotalPct = 0.0
    }
  }
}

function Set-ChannelYearData {
  param(
    $Map,
    [object[,]]$Matrix,
    [string]$YearKey
  )

  if (-not $Matrix) {
    return
  }

  for ($r = 2; $r -le $Matrix.GetLength(0); $r++) {
    $family = Normalize-Text $Matrix[$r, 2]
    if (-not $family) {
      continue
    }

    if (-not $Map.Contains($family)) {
      $Map[$family] = Get-ChannelFamilyEntry
    }

    $units = To-Number $Matrix[$r, 5]
    $convenioUnits = To-Number $Matrix[$r, 8]
    $mostradorUnits = [math]::Max(0, $units - $convenioUnits)

    $Map[$family][$YearKey] = [ordered]@{
      facturedUnits = [math]::Round($units, 0)
      convenioUnits = [math]::Round($convenioUnits, 0)
      mostradorUnits = [math]::Round($mostradorUnits, 0)
      convenioPct = Round-Number ((To-Number $Matrix[$r, 12]) * 100)
      mostradorPct = Round-Number ((To-Number $Matrix[$r, 13]) * 100)
      discountCommonPct = Round-Number ((To-Number $Matrix[$r, 14]) * 100)
      discountConvenioPct = Round-Number ((To-Number $Matrix[$r, 15]) * 100)
      discountTotalPct = Round-Number ((To-Number $Matrix[$r, 16]) * 100)
    }
  }
}

Set-ChannelYearData -Map $channelFamilies -Matrix $channel2024Matrix -YearKey 'prev'
Set-ChannelYearData -Map $channelFamilies -Matrix $channel2025Matrix -YearKey 'current'

foreach ($family in $familyOrder) {
  if (-not $channelFamilies.Contains($family)) {
    $channelFamilies[$family] = Get-ChannelFamilyEntry
  }
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
    $osPrimary = Normalize-Text $matrix[$r, 4]
    $osSecondary = Normalize-Text $matrix[$r, 5]
    $product = Normalize-Text $matrix[$r, 6]
    if (-not $family) {
      continue
    }

    # The convenios base has one rollup row per OS and then product detail rows.
    # We only want the OS-level rollup, otherwise totals get duplicated.
    if ($product -and $product -ne 'Totales') {
      continue
    }

    $os = ''
    if ($osSecondary -and $osSecondary -ne 'Totales') {
      $os = $osSecondary
    }
    elseif ($osPrimary -and $osPrimary -ne 'Totales') {
      $os = $osPrimary
    }

    if (-not $os) {
      continue
    }

    $units = To-Number $matrix[$r, 7]
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
  $market = Normalize-Text $rxMatrix[$r, 1]
  $drug = Normalize-Text $rxMatrix[$r, 2]
  $brand = Normalize-Text $rxMatrix[$r, 3]
  if (-not $market) {
    continue
  }

  $family = ''
  if ($market -match '\(([^)]+)\)') {
    $family = $matches[1].Trim().ToUpper()
  }
  else {
    $family = $market.ToUpper()
    if ($family -like 'FLEXINA*') { $family = 'FLEXINA' }
    if ($family -like 'MAGNUS*') { $family = 'MAGNUS' }
  }

  if (-not $rxFamilies.ContainsKey($family)) {
    $rxFamilies[$family] = @{
      prescriptions = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
      doctors = @(for ($i = 0; $i -lt $rxMonths.Count; $i++) { 0.0 })
    }
  }

  if ($drug -eq 'Totales' -and -not $brand) {
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

Write-Host "[Cardio] Recetas procesadas."

$pmMetaByPack = @{}
$pmMetaByProduct = @{}
$familySiePatterns = @{}
foreach ($family in $dashboardFamilyOrder) {
  $patterns = New-Object 'System.Collections.Generic.List[string]'
  foreach ($prodName in $dashboardMarketConfig[$family].sieProducts) {
    $base = Normalize-ProductKey (($prodName -replace '\(SIE\)', '').Trim())
    if ($base -and -not $patterns.Contains($base)) {
      $patterns.Add($base)
    }
  }
  foreach ($marketName in $dddMarketConfig.Keys) {
    if ($dddMarketConfig[$marketName].family -ne $family) { continue }
    foreach ($keyword in $dddMarketConfig[$marketName].keywords) {
      $base = Normalize-ProductKey $keyword
      if ($base -and -not $patterns.Contains($base)) {
        $patterns.Add($base)
      }
    }
  }
  $familySiePatterns[$family] = @($patterns | Sort-Object { $_.Length } -Descending)
}

for ($r = 2; $r -le $pmMatrix.GetLength(0); $r++) {
  $manufacturer = Normalize-Text $pmMatrix[$r, $pmColManuf]
  $product = Normalize-Text $pmMatrix[$r, $pmColProduct]
  $pack = Normalize-Text $pmMatrix[$r, $pmColPack]
  $segment = if ((Get-Variable pmColMap -ErrorAction Ignore) -and $pmColMap.segment) { Get-SegmentKey $pmMatrix[$r, $pmColMap.segment] } else { 'all' }
  $meta = @{
    segment = $segment
    manufacturer = $manufacturer
    product = $product
    pack = $pack
  }

  $packKey = Normalize-ProductKey $pack
  if ($packKey -and -not $pmMetaByPack.ContainsKey($packKey)) {
    $pmMetaByPack[$packKey] = $meta
  }
  $productKey = Normalize-ProductKey $product
  if ($productKey -and -not $pmMetaByProduct.ContainsKey($productKey)) {
    $pmMetaByProduct[$productKey] = $meta
  }
}

$dddMonthsSet = New-Object 'System.Collections.Generic.HashSet[string]'
$respDddAgg = @{}
$compareModes = @('molecule', 'atc')
$segmentModes = @('all', 'etico', 'popular')
$familyAtcRules = @{}

foreach ($family in $dashboardFamilyOrder) {
  $respDddAgg[$family] = @{}
  $familyAtcRules[$family] = @(Get-ConfigAtcRules $dashboardMarketConfig[$family])
  foreach ($compareMode in $compareModes) {
    $respDddAgg[$family][$compareMode] = @{}
    foreach ($segmentMode in $segmentModes) {
      $respDddAgg[$family][$compareMode][$segmentMode] = New-DddBucket
    }
  }
}

if ($null -eq $dddMatrix) {
  $excelReload = New-Object -ComObject Excel.Application
  $excelReload.Visible = $false
  $excelReload.DisplayAlerts = $false
  try {
    $dddMatrix = Open-Matrix -Excel $excelReload -Path $dddPath
  }
  finally {
    $excelReload.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excelReload) | Out-Null
  }
}

for ($r = 2; $r -le $dddMatrix.GetLength(0); $r++) {
  if ($r % 100000 -eq 0) {
    Write-Host ("[Cardio] DDD procesadas: {0}/{1}" -f $r, $dddMatrix.GetLength(0))
  }

  $market = Normalize-Text $dddMatrix[$r, 2]
  if (-not $dddMarketConfig.Contains($market)) { continue }

  $month = Normalize-MonthLabel $dddMatrix[$r, 5]
  $region = Normalize-Text $dddMatrix[$r, 1]
  $product = Normalize-Text $dddMatrix[$r, 8]
  $productKey = Normalize-ProductKey $product
  $atcCode = (Normalize-Text $dddMatrix[$r, 6]).ToUpper()
  $units = To-Number $dddMatrix[$r, 9]
  if (-not $month -or -not $region -or -not $product -or $units -le 0) { continue }

  $dddMonthsSet.Add($month) | Out-Null

  $segmentKey = 'unknown'
  if ($productKey -and $pmMetaByPack.ContainsKey($productKey)) {
    $segmentKey = $pmMetaByPack[$productKey].segment
  }
  elseif ($productKey -and $pmMetaByProduct.ContainsKey($productKey)) {
    $segmentKey = $pmMetaByProduct[$productKey].segment
  }

  $sieOwner = ''
  $bestLen = -1
  foreach ($family in $dashboardFamilyOrder) {
    foreach ($pattern in $familySiePatterns[$family]) {
      if (-not $pattern) { continue }
      if (($productKey -eq $pattern -or $productKey.StartsWith($pattern) -or $productKey.Contains($pattern)) -and $pattern.Length -gt $bestLen) {
        $sieOwner = $family
        $bestLen = $pattern.Length
        break
      }
    }
  }

  $family = $dddMarketConfig[$market].family
  Add-DddBucketRow -Bucket $respDddAgg[$family].molecule.all -Month $month -Region $region -Product $product -Units $units -IsSie ($sieOwner -eq $family)
  if ($segmentModes -contains $segmentKey) {
    Add-DddBucketRow -Bucket $respDddAgg[$family].molecule[$segmentKey] -Month $month -Region $region -Product $product -Units $units -IsSie ($sieOwner -eq $family)
  }

  foreach ($familyAtc in $dashboardFamilyOrder) {
    if (-not (Test-AtcStartsAny -Text $atcCode -Candidates $familyAtcRules[$familyAtc])) {
      continue
    }
    Add-DddBucketRow -Bucket $respDddAgg[$familyAtc].atc.all -Month $month -Region $region -Product $product -Units $units -IsSie ($sieOwner -eq $familyAtc)
    if ($segmentModes -contains $segmentKey) {
      Add-DddBucketRow -Bucket $respDddAgg[$familyAtc].atc[$segmentKey] -Month $month -Region $region -Product $product -Units $units -IsSie ($sieOwner -eq $familyAtc)
    }
  }
}

$dddMonths = Sort-Months @($dddMonthsSet)
$respDddOut = [ordered]@{}
$dddMarketsOut = [ordered]@{}
foreach ($family in $dashboardFamilyOrder) {
  $respDddOut[$family] = [ordered]@{}
  foreach ($compareMode in $compareModes) {
    $respDddOut[$family].Add($compareMode, [ordered]@{})
    foreach ($segmentMode in $segmentModes) {
      $respDddOut[$family][$compareMode].Add($segmentMode, (Convert-DddBucket -Bucket $respDddAgg[$family][$compareMode][$segmentMode] -Months $dddMonths -Family $family))
    }
  }
  $dddMarketsOut[$family] = Convert-DddBucket -Bucket $respDddAgg[$family].molecule.all -Months $dddMonths -Family $family
}

Write-Host "[Cardio] DDD procesadas."

$dashboardShare = @{}
foreach ($family in $familyOrder) {
  $dashboardShare[$family] = @{}
}

foreach ($family in $dddMarketsOut.Keys) {
  foreach ($row in $dddMarketsOut[$family].monthly) {
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
    convenioPct = if ($channelFamily) { $channelFamily.current.convenioPct } else { 0.0 }
    latestRx = $latestRx
    latestShare = $latestShare
    hasDdd = ($familyToMarkets[$family].Count -gt 0)
  })
}

# Dashboard layer compatible with the dermatologia executive view
function Get-PmMonthMeta {
  param([string]$Key)
  if ($Key -match '^([A-Za-z]{3}) (\d{4})$') {
    $mon = $matches[1].ToLower()
    $year = [int]$matches[2]
    if ($monthIndexEn.ContainsKey($mon)) {
      return @{ month = $monthIndexEn[$mon]; year = $year }
    }
  }
  return $null
}

function Get-PmYtdValue {
  param([hashtable]$Series, [string[]]$Months, [string]$CutKey)
  $meta = Get-PmMonthMeta $CutKey
  if ($null -eq $meta) { return 0.0 }
  $sum = 0.0
  foreach ($monthKey in $Months) {
    $monthMeta = Get-PmMonthMeta $monthKey
    if ($null -eq $monthMeta) { continue }
    if ($monthMeta.year -eq $meta.year -and $monthMeta.month -le $meta.month) {
      $sum += [double]$Series[$monthKey]
    }
  }
  return $sum
}

function Get-PmMatValue {
  param([hashtable]$Series, [string[]]$Months, [string]$CutKey)
  $cutSort = Get-MonthSortValueEn $CutKey
  $window = @($Months | Where-Object { (Get-MonthSortValueEn $_) -le $cutSort } | Select-Object -Last 12)
  $sum = 0.0
  foreach ($monthKey in $window) { $sum += [double]$Series[$monthKey] }
  return $sum
}

function Get-PmQuarterValue {
  param([hashtable]$Series, [string[]]$Months, [string]$QuarterKey)
  $sum = 0.0
  foreach ($monthKey in $Months) {
    if ((Get-QuarterKeyFromMonthLabelEn $monthKey) -eq $QuarterKey) {
      $sum += [double]$Series[$monthKey]
    }
  }
  return $sum
}

$pmColMap = [ordered]@{
  molecule = 3
  atc = 4
  segment = $null
  firstMetric = $null
}

# Deteccion dinamica de columnas: el "PM ARGENTINA Premium" legacy tenia
# molecule en col 3 y ATC en col 4. El "AR_PM_FV_Standard" (Premium central
# de IQVIA) tiene Pack en col 3, ATC IV en col 4, Ph. Forms III en col 5 y
# Molecules Long en col 6. Escaneamos los primeros 8 headers de row 1 y
# pisamos los defaults si encontramos los nombres canonicos.
for ($_c = 1; $_c -le [Math]::Min(8, $pmMatrix.GetLength(1)); $_c++) {
  $_h = ((Normalize-Text $pmMatrix[1, $_c]) -replace '\s+', ' ').Trim().ToUpper()
  if (-not $_h) { continue }
  if ($_h -match '^MOLECULES?(\s+LONG)?$') { $pmColMap.molecule = $_c }
  elseif ($_h -match '^ATC([\s-]?(IV|4))?$') { $pmColMap.atc = $_c }
  elseif ($_h -eq 'MARKET TYPE') { $pmColMap.segment = $_c }
}

$pmHeaderInfo = [ordered]@{
  monthly = @()
  ytd = @()
  mat = @()
  quarterly = @()
}

for ($c = 1; $c -le $pmMatrix.GetLength(1); $c++) {
  $header = ((Normalize-Text $pmMatrix[1, $c]) -replace '\s+', ' ').Trim()
  if (-not $header) { continue }

  if ($header -match '^(\d{1,2})/(\d{4}) Units$') {
    $key = ('{0} {1}' -f $monthLabelEn[[int]$matches[1]], $matches[2])
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.monthly += [pscustomobject]@{ col = $c; key = $key }
      if ($null -eq $pmColMap.firstMetric) { $pmColMap.firstMetric = $c }
    }
    continue
  }

  if ($header -match '^([A-Za-z]{3}) (\d{4}) Units$') {
    $key = ('{0} {1}' -f $matches[1].Substring(0,3), $matches[2])
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.monthly += [pscustomobject]@{ col = $c; key = $key }
      if ($null -eq $pmColMap.firstMetric) { $pmColMap.firstMetric = $c }
    }
    continue
  }

  if ($header -match '^Units ([A-Za-z]{3,9}) (\d{4})$') {
    $monthToken = $matches[1].Substring(0, 3)
    $key = ('{0} {1}' -f $monthToken, $matches[2])
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.monthly += [pscustomobject]@{ col = $c; key = $key }
      if ($null -eq $pmColMap.firstMetric) { $pmColMap.firstMetric = $c }
    }
    continue
  }

  if ($header -match '^(?:Units )?MAT M (\d{4}) ([A-Za-z]{3,9})(?: \*)?$') {
    $monthToken = $matches[2].Substring(0, 3)
    $key = ('{0} {1}' -f $monthToken, $matches[1])
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.mat += [pscustomobject]@{ col = $c; key = $key }
    }
    continue
  }

  if ($header -match '^(?:Units )?YTD ([A-Za-z]{3,9}) (\d{4})$') {
    $monthToken = $matches[1].Substring(0, 3)
    $key = ('{0} {1}' -f $monthToken, $matches[2])
    if ((Get-MonthSortValueEn $key) -ge 202402) {
      $pmHeaderInfo.ytd += [pscustomobject]@{ col = $c; key = $key }
    }
    continue
  }
}

if ($pmColMap.firstMetric -eq 6) { $pmColMap.segment = 5 }
elseif ((Normalize-Text $pmMatrix[1,5]).ToUpper().Contains('MARKET TYPE')) { $pmColMap.segment = 5 }

$pmHeaderInfo.monthly = @($pmHeaderInfo.monthly | Sort-Object { Get-MonthSortValueEn $_.key })
$pmMonthlyKeys = @($pmHeaderInfo.monthly | ForEach-Object { $_.key } | Select-Object -Unique)
if ($pmMonthlyKeys.Count -gt 0 -and ((($pmHeaderInfo.ytd | Measure-Object).Count -eq 0) -or (($pmHeaderInfo.mat | Measure-Object).Count -eq 0))) {
  $latestMonthlyKey = $pmMonthlyKeys[-1]
  $latestMeta = Get-PmMonthMeta $latestMonthlyKey
  $years = @($pmMonthlyKeys | ForEach-Object { if ($_ -match '^[A-Za-z]{3} (\d{4})$') { [int]$matches[1] } } | Select-Object -Unique | Sort-Object)
  foreach ($year in $years) {
    $candidate = ('{0} {1}' -f $monthLabelEn[$latestMeta.month], $year)
    if ($pmMonthlyKeys -contains $candidate) {
      if ((($pmHeaderInfo.ytd | Where-Object { $_.key -eq $candidate } | Measure-Object).Count) -eq 0) {
        $pmHeaderInfo.ytd += [pscustomobject]@{ col = $null; key = $candidate }
      }
      if ((($pmHeaderInfo.mat | Where-Object { $_.key -eq $candidate } | Measure-Object).Count) -eq 0) {
        $pmHeaderInfo.mat += [pscustomobject]@{ col = $null; key = $candidate }
      }
    }
  }
}
$pmHeaderInfo.ytd = @($pmHeaderInfo.ytd | Sort-Object { Get-MonthSortValueEn $_.key })
$pmHeaderInfo.mat = @($pmHeaderInfo.mat | Sort-Object { Get-MonthSortValueEn $_.key })
$pmMatKeys = @($pmHeaderInfo.mat | ForEach-Object { $_.key } | Select-Object -Unique)
$pmYtdKeys = @($pmHeaderInfo.ytd | ForEach-Object { $_.key } | Select-Object -Unique)
$derivedQuarterKeys = @(
  $pmMonthlyKeys |
    ForEach-Object { Get-QuarterKeyFromMonthLabelEn $_ } |
    Where-Object { $_ } |
    Select-Object -Unique
)
$pmQuarterFromMonthly = $true
$pmQuarterKeys = Sort-QuarterLabels $derivedQuarterKeys

if ($pmMatKeys.Count -lt 2 -or $pmYtdKeys.Count -lt 2 -or $pmMonthlyKeys.Count -lt 1) {
  throw "No se pudieron detectar correctamente las series PM. Mensual=$($pmMonthlyKeys.Count) YTD=$($pmYtdKeys.Count) MAT=$($pmMatKeys.Count)"
}

Write-Host ("[PM] Detectado. Mensual={0} YTD={1} MAT={2} Quarter={3}" -f $pmMonthlyKeys.Count, $pmYtdKeys.Count, $pmMatKeys.Count, $pmQuarterKeys.Count)

$pmCurrentMatKey = $pmMatKeys[-1]
$pmPrevMatKey = $pmMatKeys[-2]
$pmCurrentYtdKey = $pmYtdKeys[-1]
$pmPrevYtdKey = $pmYtdKeys[-2]

$pmPerf = [ordered]@{}

$respPerf = [ordered]@{}
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

  $moleculeRules = @(Get-ConfigMoleculeRules $cfg)
  $atcRules = @(Get-ConfigAtcRules $cfg)
  $perfBuckets = [ordered]@{
    molecule = [ordered]@{
      all = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
      etico = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
      popular = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
    }
    atc = [ordered]@{
      all = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
      etico = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
      popular = (New-PerfBucket -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys)
    }
  }

  for ($r = 2; $r -le $pmMatrix.GetLength(0); $r++) {
    $product = Normalize-Text $pmMatrix[$r, $pmColProduct]
    $manufacturer = Normalize-Text $pmMatrix[$r, $pmColManuf]
    $segment = if ((Get-Variable pmColMap -ErrorAction Ignore) -and $pmColMap.segment) { Get-SegmentKey $pmMatrix[$r, $pmColMap.segment] } else { 'all' }
    $atc = Normalize-Text $pmMatrix[$r, $pmColMap.atc]
    $molecule = Normalize-Text $pmMatrix[$r, $pmColMap.molecule]
    if (-not $product) {
      continue
    }

    $productUpper = $product.ToUpper()
    $atcUpper = $atc.ToUpper()
    $moleculeUpper = $molecule.ToUpper()
    $moleculeMatch = Test-TextEqualsAny -Text $moleculeUpper -Candidates $moleculeRules
    $atcMatch = Test-AtcStartsAny -Text $atcUpper -Candidates $atcRules
    if (-not $moleculeMatch -and -not $atcMatch) {
      continue
    }

    $isSieProduct = ($cfg.sieProducts -contains $product) -or $productUpper.Contains('(SIE)') -or $manufacturer.ToUpper().Contains('SIEGFRIED')

    foreach ($viewKey in @('molecule', 'atc')) {
      $matchesView = if ($viewKey -eq 'molecule') { $moleculeMatch } else { $atcMatch }
      if (-not $matchesView) { continue }

      $targets = @($perfBuckets[$viewKey].all)
      if (@('etico', 'popular') -contains $segment) {
        $targets += $perfBuckets[$viewKey][$segment]
      }

      foreach ($bucket in $targets) {
        Ensure-PerfBucketProduct -Bucket $bucket -Product $product -Manufacturer $manufacturer -IsSie $isSieProduct -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys

        foreach ($colInfo in $pmHeaderInfo.monthly) {
          $value = To-Number $pmMatrix[$r, $colInfo.col]
          $bucket.products[$product].monthly[$colInfo.key] += $value
          $bucket.marketMonthly[$colInfo.key] += $value
          if ($pmQuarterFromMonthly -and $pmQuarterKeys.Count -gt 0) {
            $quarterKey = Get-QuarterKeyFromMonthLabelEn $colInfo.key
            if ($quarterKey -and $bucket.products[$product].quarterly.ContainsKey($quarterKey)) {
              $bucket.products[$product].quarterly[$quarterKey] += $value
              $bucket.marketQuarterly[$quarterKey] += $value
            }
          }
        }
        foreach ($colInfo in $pmHeaderInfo.ytd) {
          if ($null -eq $colInfo.col) { continue }
          $value = To-Number $pmMatrix[$r, $colInfo.col]
          $bucket.products[$product].ytd[$colInfo.key] += $value
          $bucket.marketYtd[$colInfo.key] += $value
        }
        foreach ($colInfo in $pmHeaderInfo.mat) {
          if ($null -eq $colInfo.col) { continue }
          $value = To-Number $pmMatrix[$r, $colInfo.col]
          $bucket.products[$product].mat[$colInfo.key] += $value
          $bucket.marketMat[$colInfo.key] += $value
        }
        foreach ($colInfo in $pmHeaderInfo.quarterly) {
          if ($null -eq $colInfo.col) { continue }
          $value = To-Number $pmMatrix[$r, $colInfo.col]
          $bucket.products[$product].quarterly[$colInfo.key] += $value
          $bucket.marketQuarterly[$colInfo.key] += $value
        }
      }
    }
  }

  foreach ($viewKey in @('molecule', 'atc')) {
    foreach ($segmentKey in @('all', 'etico', 'popular')) {
      $bucket = $perfBuckets[$viewKey][$segmentKey]
      foreach ($yKey in $pmYtdKeys) {
        $bucket.marketYtd[$yKey] = Get-PmYtdValue -Series $bucket.marketMonthly -Months $pmMonthlyKeys -CutKey $yKey
      }
      foreach ($mKey in $pmMatKeys) {
        $bucket.marketMat[$mKey] = Get-PmMatValue -Series $bucket.marketMonthly -Months $pmMonthlyKeys -CutKey $mKey
      }
      foreach ($qKey in $pmQuarterKeys) {
        $bucket.marketQuarterly[$qKey] = Get-PmQuarterValue -Series $bucket.marketMonthly -Months $pmMonthlyKeys -QuarterKey $qKey
      }
      foreach ($prodName in @($bucket.products.Keys)) {
        foreach ($yKey in $pmYtdKeys) {
          $bucket.products[$prodName].ytd[$yKey] = Get-PmYtdValue -Series $bucket.products[$prodName].monthly -Months $pmMonthlyKeys -CutKey $yKey
        }
        foreach ($mKey in $pmMatKeys) {
          $bucket.products[$prodName].mat[$mKey] = Get-PmMatValue -Series $bucket.products[$prodName].monthly -Months $pmMonthlyKeys -CutKey $mKey
        }
        foreach ($qKey in $pmQuarterKeys) {
          $bucket.products[$prodName].quarterly[$qKey] = Get-PmQuarterValue -Series $bucket.products[$prodName].monthly -Months $pmMonthlyKeys -QuarterKey $qKey
        }
      }
    }
  }

  $pmProductMatLookup[$family] = @{
    molecule = @{}
    atc = @{}
  }
  $molAll = Convert-PerfBucket -Bucket $perfBuckets.molecule.all -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $pmProductMatLookup[$family].molecule
  $atcAll = Convert-PerfBucket -Bucket $perfBuckets.atc.all -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $pmProductMatLookup[$family].atc
  $respPerf[$family] = [ordered]@{
    molecule = [ordered]@{
      all = $molAll
      etico = (Convert-PerfBucket -Bucket $perfBuckets.molecule.etico -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $null)
      popular = (Convert-PerfBucket -Bucket $perfBuckets.molecule.popular -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $null)
    }
    atc = [ordered]@{
      all = $atcAll
      etico = (Convert-PerfBucket -Bucket $perfBuckets.atc.etico -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $null)
      popular = (Convert-PerfBucket -Bucket $perfBuckets.atc.popular -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $null)
    }
  }
  $pmPerf[$family] = Convert-PerfBucket -Bucket $perfBuckets.molecule.all -SieProducts $cfg.sieProducts -Family $family -MonthlyKeys $pmMonthlyKeys -YtdKeys $pmYtdKeys -MatKeys $pmMatKeys -QuarterKeys $pmQuarterKeys -CurrentMatKey $pmCurrentMatKey -CurrentYtdKey $pmCurrentYtdKey -ProductMatLookup $null

  $currentYtdUnits = 0.0
  $prevYtdUnits = 0.0
  $currentMatUnits = 0.0
  $prevMatUnits = 0.0
  foreach ($prodName in $cfg.sieProducts) {
    if ($perfBuckets.molecule.all.products.ContainsKey($prodName)) {
      $currentYtdUnits += $perfBuckets.molecule.all.products[$prodName].ytd[$pmCurrentYtdKey]
      $prevYtdUnits += $perfBuckets.molecule.all.products[$prodName].ytd[$pmPrevYtdKey]
      $currentMatUnits += $perfBuckets.molecule.all.products[$prodName].mat[$pmCurrentMatKey]
      $prevMatUnits += $perfBuckets.molecule.all.products[$prodName].mat[$pmPrevMatKey]
    }
  }

  if (-not $marketTotalsByGroup.ContainsKey($cfg.group)) {
    $marketTotalsByGroup[$cfg.group] = @{
      ytd = $perfBuckets.molecule.all.marketYtd[$pmCurrentYtdKey]
      mat = $perfBuckets.molecule.all.marketMat[$pmCurrentMatKey]
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
      ms = if ($perfBuckets.molecule.all.marketYtd[$pmCurrentYtdKey] -gt 0) { Round-Number (($currentYtdUnits / $perfBuckets.molecule.all.marketYtd[$pmCurrentYtdKey]) * 100) } else { $null }
      units = [math]::Round($currentYtdUnits, 0)
      units_prev = [math]::Round($prevYtdUnits, 0)
      market_total = [math]::Round($perfBuckets.molecule.all.marketYtd[$pmCurrentYtdKey], 0)
      growth = if ($prevYtdUnits -gt 0) { Round-Number ((($currentYtdUnits - $prevYtdUnits) / $prevYtdUnits) * 100) } else { $null }
    }
    mat = [ordered]@{
      ie = if ($prevMatUnits -gt 0) { Round-Number (($currentMatUnits / $prevMatUnits) * 100) } else { $null }
      ms = if ($perfBuckets.molecule.all.marketMat[$pmCurrentMatKey] -gt 0) { Round-Number (($currentMatUnits / $perfBuckets.molecule.all.marketMat[$pmCurrentMatKey]) * 100) } else { $null }
      units = [math]::Round($currentMatUnits, 0)
      units_prev = [math]::Round($prevMatUnits, 0)
      market_total = [math]::Round($perfBuckets.molecule.all.marketMat[$pmCurrentMatKey], 0)
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
  $prevEntry = $entry.prev
  $currentEntry = $entry.current
  $dashboardCanales[$family] = [ordered]@{
    unid = $currentEntry.facturedUnits
    conv = $currentEntry.convenioPct
    most = $currentEntry.mostradorPct
    conv_units = $currentEntry.convenioUnits
    most_units = $currentEntry.mostradorUnits
    dto_total = $currentEntry.discountTotalPct
    dto_conv = $currentEntry.discountConvenioPct
    dto_most = $currentEntry.discountCommonPct
    unid_prev = $prevEntry.facturedUnits
    conv_prev = $prevEntry.convenioPct
    most_prev = $prevEntry.mostradorPct
    conv_units_prev = $prevEntry.convenioUnits
    most_units_prev = $prevEntry.mostradorUnits
    dto_total_prev = $prevEntry.discountTotalPct
    dto_conv_prev = $prevEntry.discountConvenioPct
    dto_most_prev = $prevEntry.discountCommonPct
    conv_pp = Round-Number ($currentEntry.convenioPct - $prevEntry.convenioPct)
    most_pp = Round-Number ($currentEntry.mostradorPct - $prevEntry.mostradorPct)
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
  $dashboardPrices[$family] = [ordered]@{
    molecule = [ordered]@{}
    atc = [ordered]@{}
  }
  $precIqvia[$family] = [ordered]@{
    molecule = [ordered]@{}
    atc = [ordered]@{}
  }
  if (-not $pmProductMatLookup.ContainsKey($family)) {
    continue
  }

  $allowedByMode = @{
    molecule = if ($pmProductMatLookup[$family].ContainsKey('molecule')) { $pmProductMatLookup[$family].molecule } else { @{} }
    atc = if ($pmProductMatLookup[$family].ContainsKey('atc')) { $pmProductMatLookup[$family].atc } else { @{} }
  }
  for ($r = 2; $r -le $priceMatrix.GetLength(0); $r++) {
    $productName = Normalize-Text $priceMatrix[$r, 3]
    $presentation = Normalize-Text $priceMatrix[$r, 4]
    $lab = Normalize-Text $priceMatrix[$r, 7]
    if (-not $productName -or -not $presentation) {
      continue
    }

    $normPriceKey = Normalize-ProductKey $productName

    foreach ($compareMode in @('molecule', 'atc')) {
      $allowedProducts = $allowedByMode[$compareMode]
      if (-not $allowedProducts -or $allowedProducts.Keys.Count -eq 0) {
        continue
      }

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

      if (-not $dashboardPrices[$family][$compareMode].Contains($presentation)) {
        $dashboardPrices[$family][$compareMode].Add($presentation, @())
      }

      if (-not $precIqvia[$family][$compareMode].Contains($productName.ToUpper())) {
        $precIqvia[$family][$compareMode].Add($productName.ToUpper(), $allowedProducts[$matchedKey])
      }

      $dashboardPrices[$family][$compareMode][$presentation] += [ordered]@{
        lab = $lab
        prod = $productName
        is_sie = $lab.ToUpper().Contains('SIEGFRIED')
        pvp_dic25 = Round-Number (To-Number $priceMatrix[$r, 13]) 2
        pvp_feb26 = Round-Number (To-Number $priceMatrix[$r, 14]) 2
        var = if ((To-Number $priceMatrix[$r, 15]) -ne 0) { (To-Number $priceMatrix[$r, 15]) / 100 } else { 0.0 }
      }
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
  has_budget = [bool]$budgetPath
  footer_date = '06/04/2026'
}

$dashboardDefaults = [ordered]@{
  brand = 'DAURAN'
  market = 'Dapagliflozina'
  rec = 'DAURAN'
}

$dashboardData = [ordered]@{
  meses = @('Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic')
  sieProds = $dashboardFamilyOrder
  colors = $dashboardColors
  compColors = @('#374151', '#6b7280', '#9ca3af', '#d1d5db', '#4b5563', '#1f2937')
  budget = $dashboardBudget
  mol_perf = $pmPerf
  respPerf = $respPerf
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
  sieMolMap = $molLabels
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
    rxCut = ''
    dddCut = if (($dddMonths | Measure-Object).Count -gt 0) { $dddMonths[-1] } else { '' }
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
  respDdd = [ordered]@{
    order = $dashboardFamilyOrder
    months = $dddMonths
    families = $respDddOut
  }
}

Add-Type -AssemblyName System.Web.Extensions
$serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$serializer.MaxJsonLength = [int]::MaxValue
$serializer.RecursionLimit = 256
try {
  $json = $serializer.Serialize($data)
  $dashboardJson = $serializer.Serialize($dashboardData)
}
catch {
  Write-Host "[Cardio] Serializer web fallo, uso ConvertTo-Json."
  $json = $data | ConvertTo-Json -Depth 100 -Compress
  $dashboardJson = $dashboardData | ConvertTo-Json -Depth 100 -Compress
}
$content = "window.OTC_DATA = $json;`r`nwindow.OTC_DASHBOARD = $dashboardJson;"
Set-Content -LiteralPath $OutputPath -Value $content -Encoding UTF8
Write-Output "Cardio data generated: $OutputPath"
