param(
  [string]$WorkbookPath = 'C:\Users\camarinaro\Downloads\Estimados vigentes MKT.xlsx',
  [string]$OutputPath = 'C:\Users\camarinaro\Documents\marcas\Marcas-CardioMetabolismo\shared\budget-overrides.js'
)

$ErrorActionPreference = 'Stop'

function Normalize-Text {
  param([object]$Value)
  $text = [string]$Value
  if([string]::IsNullOrWhiteSpace($text)){ return '' }
  $normalized = $text.Normalize([Text.NormalizationForm]::FormD)
  $sb = New-Object System.Text.StringBuilder
  foreach($ch in $normalized.ToCharArray()){
    $cat = [Globalization.CharUnicodeInfo]::GetUnicodeCategory($ch)
    if($cat -ne [Globalization.UnicodeCategory]::NonSpacingMark){
      [void]$sb.Append($ch)
    }
  }
  return ($sb.ToString().ToUpperInvariant() -replace '[^A-Z0-9]+',' ').Trim()
}

function New-NullBudget {
  return @(for($i=0; $i -lt 12; $i++){ $null })
}

function New-ZeroBudget {
  return [double[]]@(0,0,0,0,0,0,0,0,0,0,0,0)
}

function Match-BudgetKey {
  param(
    [string]$Product,
    [array]$Matchers
  )
  $norm = Normalize-Text $Product
  foreach($entry in $Matchers){
    foreach($alias in $entry.aliases){
      $aliasNorm = Normalize-Text $alias
      if($aliasNorm -and ($norm -eq $aliasNorm -or $norm.StartsWith($aliasNorm + ' '))){
        return $entry.key
      }
    }
  }
  return $null
}

$monthHeaders = @('ene-26','feb-26','mar-26','abr-26','may-26','jun-26','jul-26','ago-26','sept-26','oct-26','nov-26','dic-26')

$lineConfigs = @{
  cardio = @{
    workbookLine = 'Cardio met'
    matchers = @(
      @{ key = 'DAURAN'; aliases = @('DAURAN ') }
      @{ key = 'DILATREND AP'; aliases = @('DILATREND AP') }
      @{ key = 'DILATREND D'; aliases = @('DILATREND D') }
      @{ key = 'EMPAX MET'; aliases = @('EMPAX MET') }
      @{ key = 'METGLUCON DUO'; aliases = @('METGLUCON DUO') }
      @{ key = 'SILTRAN MET'; aliases = @('SILTRAN MET') }
      @{ key = 'ENTRESTO'; aliases = @('ENTRESTO') }
      @{ key = 'EXFORGE D'; aliases = @('EXFORGE D') }
      @{ key = 'EXFORGE'; aliases = @('EXFORGE') }
      @{ key = 'ROXOLAN'; aliases = @('ROXOLAN') }
      @{ key = 'DIOVAN D'; aliases = @('DIOVAN D') }
      @{ key = 'DIOVAN'; aliases = @('DIOVAN') }
      @{ key = 'PIXABAN'; aliases = @('PIXABAN') }
      @{ key = 'SINTROM'; aliases = @('SINTROM') }
      @{ key = 'TERLOC'; aliases = @('TERLOC') }
      @{ key = 'DILATREND'; aliases = @('DILATREND') }
      @{ key = 'TELPRES'; aliases = @('TELPRES') }
      @{ key = 'EMPAX'; aliases = @('EMPAX ') }
      @{ key = 'METGLUCON AP'; aliases = @('METGLUCON ') }
      @{ key = 'SILTRAN'; aliases = @('SILTRAN ') }
    )
  }
  snc = @{
    workbookLine = 'Neuro'
    matchers = @(
      @{ key = 'MADOPAR DISP'; aliases = @('MADOPAR 125 MG DISP', 'MADOPAR DISP') }
      @{ key = 'MADOPAR HBS'; aliases = @('MADOPAR HBS') }
      @{ key = 'APLACASSE'; aliases = @('APLACASSE') }
      @{ key = 'DORMICUM'; aliases = @('DORMICUM') }
      @{ key = 'EMERAL'; aliases = @('EMERAL') }
      @{ key = 'LEVITAL'; aliases = @('LEVITAL') }
      @{ key = 'LURAP'; aliases = @('LURAP') }
      @{ key = 'MADOPAR'; aliases = @('MADOPAR') }
      @{ key = 'MELERIL'; aliases = @('MELERIL') }
      @{ key = 'PGB'; aliases = @('PGB') }
      @{ key = 'QTP'; aliases = @('QTP') }
      @{ key = 'VALIUM'; aliases = @('VALIUM') }
      @{ key = 'VALQUIR'; aliases = @('VALQUIR') }
      @{ key = 'VISDON'; aliases = @('VISDON') }
    )
  }
  dermatologia = @{
    workbookLine = 'Dermato'
    matchers = @(
      @{ key = 'ACNECLIN AP'; aliases = @('ACNECLIN 100 AP') }
      @{ key = 'ACNECLIN PBA'; aliases = @('ACNECLIN PBA') }
      @{ key = 'MICOMAZOL B'; aliases = @('MICOMAZOL B') }
      @{ key = 'MICROSONA BB'; aliases = @('MICROSONA BB') }
      @{ key = 'MICROSONA C'; aliases = @('MICROSONA C') }
      @{ key = 'PALDAR H'; aliases = @('PALDAR H') }
      @{ key = 'ACNECLIN'; aliases = @('ACNECLIN') }
      @{ key = 'CLOBESOL'; aliases = @('CLOBESOL') }
      @{ key = 'MICOMAZOL'; aliases = @('MICOMAZOL') }
      @{ key = 'MICROSONA'; aliases = @('MICROSONA') }
      @{ key = 'PALDAR'; aliases = @('PALDAR') }
      @{ key = 'ROACCUTAN'; aliases = @('ROACCUTAN') }
      @{ key = 'MOMETAX'; aliases = @('MOMETAX') }
    )
  }
  otc = @{
    workbookLine = 'OTC'
    matchers = @(
      @{ key = 'TETRALGIN NOVO'; aliases = @('TETRALGIN NOVO') }
      @{ key = 'ACERPES'; aliases = @('ACERPES') }
      @{ key = 'ACI-TIP'; aliases = @('ACI-TIP') }
      @{ key = 'ALUMPAK'; aliases = @('ALUMPAK') }
      @{ key = 'ARTRO RED'; aliases = @('ARTRO RED') }
      @{ key = 'FLEXINA'; aliases = @('FLEXINA') }
      @{ key = 'MAGNUS'; aliases = @('MAGNUS') }
      @{ key = 'TETRALGIN'; aliases = @('TETRALGIN') }
    )
  }
  atb = @{
    workbookLine = 'ATB'
    matchers = @(
      @{ key = 'CEFALEXINA ARG DUO'; aliases = @('CEFALEXINA ARG DUO') }
      @{ key = 'BACTRIM FORTE'; aliases = @('BACTRIM FORTE') }
      @{ key = 'ACANTEX'; aliases = @('ACANTEX') }
      @{ key = 'BACTRIM'; aliases = @('BACTRIM ') }
      @{ key = 'CEFALEXINA ARG'; aliases = @('CEFALEXINA ARG ') }
      @{ key = 'MACROMAX'; aliases = @('MACROMAX') }
    )
  }
  respiratorio = @{
    workbookLine = 'Respi'
    matchers = @(
      @{ key = 'ACEMUK BIOTIC DUO'; aliases = @('ACEMUK BIOTIC DUO') }
      @{ key = 'ACEMUK DIA Y NOCHE'; aliases = @('ACEMUK DIA Y NOCHE') }
      @{ key = 'ACEMUK GRIP'; aliases = @('ACEMUK GRIP') }
      @{ key = 'AIREAL PLUS'; aliases = @('AIREAL PLUS') }
      @{ key = 'DUO-DECADRON'; aliases = @('DUODECADRON') }
      @{ key = 'HEXALER BRONQUIAL DU'; aliases = @('HEXALER BRONQUIAL DUO') }
      @{ key = 'HEXALER BRONQUIAL'; aliases = @('HEXALER BRONQUIAL') }
      @{ key = 'HEXALER CORT'; aliases = @('HEXALER CORT') }
      @{ key = 'HEXALER NASAL'; aliases = @('HEXALER NASAL') }
      @{ key = 'HEXALER PLUS'; aliases = @('HEXALER PLUS') }
      @{ key = 'ACEMUK L'; aliases = @('ACEMUK L') }
      @{ key = 'ACEMUK'; aliases = @('ACEMUK') }
      @{ key = 'AIREAL'; aliases = @('AIREAL') }
      @{ key = 'ALIDIAL'; aliases = @('ALIDIAL') }
      @{ key = 'DECADRON'; aliases = @('DECADRON') }
      @{ key = 'HEXALER'; aliases = @('HEXALER') }
    )
  }
}

$lineByWorkbook = @{}
$initialBudgets = @{}
foreach($lineKey in $lineConfigs.Keys){
  $config = $lineConfigs[$lineKey]
  $lineByWorkbook[$config.workbookLine] = $lineKey
  $initialBudgets[$lineKey] = @{}
  foreach($matcher in $config.matchers){
    if(-not $initialBudgets[$lineKey].ContainsKey($matcher.key)){
      $initialBudgets[$lineKey][$matcher.key] = New-NullBudget
    }
  }
}

if(-not (Test-Path $WorkbookPath)){
  throw "No encontré el workbook presupuestado: $WorkbookPath"
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false

try {
  $wb = $excel.Workbooks.Open($WorkbookPath)
  $ws = $wb.Worksheets.Item('Estimados 2026')
  $used = $ws.UsedRange
  $values = $used.Value2
  $rowCount = $used.Rows.Count
  $colCount = $used.Columns.Count

  $headers = @{}
  for($c=1; $c -le $colCount; $c++){
    $headers[(Normalize-Text $ws.Cells.Item(1, $c).Text)] = $c
  }

  $lineaCol = $headers[(Normalize-Text 'Linea')]
  $prodCol = $headers[(Normalize-Text 'Producto')]
  $monthCols = @()
  foreach($month in $monthHeaders){
    $monthCols += $headers[(Normalize-Text $month)]
  }

  $budgets = @{}
  foreach($lineKey in $lineConfigs.Keys){
    $budgets[$lineKey] = @{}
    foreach($matcher in $lineConfigs[$lineKey].matchers){
      if(-not $budgets[$lineKey].ContainsKey($matcher.key)){
        $budgets[$lineKey][$matcher.key] = New-ZeroBudget
      }
    }
  }

  $matchCounters = @{}
  foreach($lineKey in $lineConfigs.Keys){
    $matchCounters[$lineKey] = @{}
    foreach($matcher in $lineConfigs[$lineKey].matchers){
      if(-not $matchCounters[$lineKey].ContainsKey($matcher.key)){
        $matchCounters[$lineKey][$matcher.key] = 0
      }
    }
  }

  for($r=2; $r -le $rowCount; $r++){
    $workbookLine = [string]$values[$r, $lineaCol]
    if(-not $lineByWorkbook.ContainsKey($workbookLine)){ continue }

    $lineKey = $lineByWorkbook[$workbookLine]
    $product = [string]$values[$r, $prodCol]
    $budgetKey = Match-BudgetKey -Product $product -Matchers $lineConfigs[$lineKey].matchers
    if(-not $budgetKey){ continue }

    for($idx=0; $idx -lt $monthCols.Count; $idx++){
      $cellValue = $values[$r, $monthCols[$idx]]
      if($null -eq $cellValue -or $cellValue -eq ''){ continue }
      $num = [double]$cellValue
      $budgets[$lineKey][$budgetKey][$idx] = [double]$budgets[$lineKey][$budgetKey][$idx] + $num
    }

    $matchCounters[$lineKey][$budgetKey]++
  }

  foreach($lineKey in $budgets.Keys){
    foreach($budgetKey in @($budgets[$lineKey].Keys)){
      if($matchCounters[$lineKey][$budgetKey] -eq 0){
        $budgets[$lineKey][$budgetKey] = New-NullBudget
        continue
      }
      $budgets[$lineKey][$budgetKey] = @(
        foreach($value in $budgets[$lineKey][$budgetKey]){
          [int][Math]::Round([double]$value, 0)
        }
      )
    }
  }

  $overridesJson = ConvertTo-Json $budgets -Depth 6 -Compress
  $generatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  $sourceLabel = $WorkbookPath.Replace('\','\\')

  $jsTemplate = @'
// Generated by shared/build-budget-overrides.ps1
// Source: __SOURCE__
// Generated at: __GENERATED_AT__
(function(){
  const MONTHS_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  const OVERRIDES = __OVERRIDES__;

  function round0(value){
    return value == null ? null : Math.round(value);
  }

  function round1(value){
    return value == null ? null : Math.round(value * 10) / 10;
  }

  function ensureSeriesShape(entry){
    if(!entry['2026']) entry['2026'] = {};
    const bucket = entry['2026'];
    if(!Array.isArray(bucket.budget)) bucket.budget = Array(12).fill(null);
    if(!Array.isArray(bucket.real)) bucket.real = Array(12).fill(null);
    if(bucket.budget.length < 12) bucket.budget = bucket.budget.concat(Array(12 - bucket.budget.length).fill(null));
    if(bucket.real.length < 12) bucket.real = bucket.real.concat(Array(12 - bucket.real.length).fill(null));
    return bucket;
  }

  function latestActualIndex(data){
    let latest = -1;
    Object.values(data?.budget || {}).forEach(entry => {
      const real = entry?.['2026']?.real;
      if(!Array.isArray(real)) return;
      real.forEach((value, idx) => {
        const num = Number(value);
        if(Number.isFinite(num) && num !== 0){
          latest = Math.max(latest, idx);
        }
      });
    });
    return latest;
  }

  function sumBudgetAtIndex(data, kind, idx){
    let total = 0;
    let found = false;
    Object.values(data?.budget || {}).forEach(entry => {
      const arr = entry?.['2026']?.[kind];
      if(!Array.isArray(arr)) return;
      const num = Number(arr[idx]);
      if(!Number.isFinite(num)) return;
      total += num;
      found = true;
    });
    return found ? round0(total) : null;
  }

  function syncBrandKpis(data, idx){
    if(!data?.brandKpis) return;
    Object.entries(data.brandKpis).forEach(([brand, payload]) => {
      const series = data?.budget?.[brand]?.['2026'];
      if(!series) return;
      const targetNum = Number(series.budget?.[idx]);
      const realNum = Number(series.real?.[idx]);
      const hasTarget = Number.isFinite(targetNum) && targetNum !== 0;
      const hasReal = Number.isFinite(realNum);
      payload.budget = {
        pct: hasTarget && hasReal ? round1((realNum / targetNum) * 100) : null,
        real: hasReal ? round0(realNum) : null,
        target: hasTarget ? round0(targetNum) : null,
      };
    });
  }

  function syncBudgetCopy(label){
    if(typeof document === 'undefined') return;
    const el = document.getElementById('bud-copy');
    if(!el) return;
    const suffix = label && label !== '2026' ? ` · seguimiento a ${label}` : '';
    el.textContent = `Unidades mensuales: venta interna Siegfried vs presupuesto planificado · 2025 cierre · 2026 vigente${suffix}`;
  }

  function applyBudget2026Overrides(opts){
    const line = opts?.line;
    const data = opts?.data;
    if(!line || !data || !OVERRIDES[line]) return data;

    const lineOverrides = OVERRIDES[line];
    data.budget = data.budget || {};

    Object.entries(lineOverrides).forEach(([brand, budget]) => {
      data.budget[brand] = data.budget[brand] || {};
      const bucket = ensureSeriesShape(data.budget[brand]);
      bucket.budget = budget.slice(0, 12).map(value => value == null ? null : round0(Number(value)));
    });

    data.meta = data.meta || {};
    const latestIdx = latestActualIndex(data);
    const budgetIdx = latestIdx >= 0 ? latestIdx : 0;
    const budgetLabel = latestIdx >= 0 ? `${MONTHS_ES[budgetIdx]}'26` : '2026';
    data.meta.budget_index = budgetIdx;
    data.meta.budget_label = budgetLabel;
    data.meta.has_budget = Object.keys(lineOverrides).length > 0;

    if(data.kpiStrip){
      const budTotal = sumBudgetAtIndex(data, 'budget', budgetIdx);
      const realTotal = sumBudgetAtIndex(data, 'real', budgetIdx);
      data.kpiStrip.bud_total = budTotal;
      data.kpiStrip.real_total = realTotal;
      data.kpiStrip.bud_pct = budTotal && realTotal != null ? round1((realTotal / budTotal) * 100) : null;
    }

    syncBrandKpis(data, budgetIdx);
    syncBudgetCopy(budgetLabel);
    return data;
  }

  window.BUDGET_2026_OVERRIDES = OVERRIDES;
  window.applyBudget2026Overrides = applyBudget2026Overrides;
})();
'@

  $js = $jsTemplate.Replace('__SOURCE__', $sourceLabel).Replace('__GENERATED_AT__', $generatedAt).Replace('__OVERRIDES__', $overridesJson)

  $folder = Split-Path -Parent $OutputPath
  if(-not (Test-Path $folder)){
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
  }
  Set-Content -Path $OutputPath -Value $js -Encoding UTF8

  foreach($lineKey in ($matchCounters.Keys | Sort-Object)){
    $missing = @(
      foreach($kv in $matchCounters[$lineKey].GetEnumerator()){
        if($kv.Value -eq 0){ $kv.Key }
      }
    )
    if($missing.Count){
      Write-Output ("[{0}] sin match presupuestado: {1}" -f $lineKey, ($missing -join ', '))
    } else {
      Write-Output ("[{0}] todos los budget keys quedaron mapeados" -f $lineKey)
    }
  }
  Write-Output ("Archivo generado: {0}" -f $OutputPath)
}
finally {
  if($used){ [void][System.Runtime.Interopservices.Marshal]::ReleaseComObject($used) }
  if($ws){ [void][System.Runtime.Interopservices.Marshal]::ReleaseComObject($ws) }
  if($wb){ $wb.Close($false); [void][System.Runtime.Interopservices.Marshal]::ReleaseComObject($wb) }
  if($excel){ $excel.Quit(); [void][System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
