const ROOT = window.OTC_DATA || {};
const DD = ROOT.ddd || {};
const MKT_MAP = DD.markets || {};
const MONTHS = DD.months || [];
const FAMILY_MAP = ROOT.familyToMarkets || {};
const ORDERED_MARKETS = (FAMILY_MAP.Totales || Object.keys(MKT_MAP)).filter(m => MKT_MAP[m]);
const PARAMS = new URLSearchParams(location.search);
const MONTH_INDEX = {Ene:0,Feb:1,Mar:2,Abr:3,May:4,Jun:5,Jul:6,Ago:7,Sep:8,Oct:9,Nov:10,Dic:11};
const SIE = '#7A1518';
const SEL = '#2563EB';
const RC = ['#7A1518','#2563EB','#7C3AED','#D97706','#16A34A','#DB2777','#0891B2','#EA580C','#6D28D9','#0D9488','#F59E0B','#4F46E5'];
const BC = ['#2563EB','#7C3AED','#D97706','#16A34A','#DB2777','#0891B2','#EA580C','#6D28D9','#0D9488','#4F46E5','#CA8A04','#0369A1','#059669','#B91C1C','#F59E0B'];

function defaultMarket(){
  const qMarket = PARAMS.get('market');
  if (qMarket && MKT_MAP[qMarket]) return qMarket;
  const qFamily = PARAMS.get('family');
  if (qFamily && FAMILY_MAP[qFamily] && FAMILY_MAP[qFamily][0]) return FAMILY_MAP[qFamily][0];
  const rootDefault = ROOT.defaults?.market || ROOT.defaults?.brand;
  if (rootDefault && MKT_MAP[rootDefault]) return rootDefault;
  if (rootDefault && FAMILY_MAP[rootDefault] && FAMILY_MAP[rootDefault][0]) return FAMILY_MAP[rootDefault][0];
  return ORDERED_MARKETS[0];
}

let cur = defaultMarket();
let selRegs = (PARAMS.get('regions') || '').split('|').filter(Boolean);
let selB = PARAMS.get('product') || null;
let chs = {};
let sC = 'total';
let sD = 'desc';
let ddOpen = false;
let ztSort = { col:'ms', dir:-1 };

function fmt(n){ return Number(n || 0).toLocaleString('es-AR'); }
function fms(n){ return Number(n || 0).toFixed(1) + '%'; }
function fk(n){ const v = Number(n || 0); return v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1) + 'k' : fmt(v); }
function mParts(key){ const [m, y] = String(key || '').split('-'); return { m, y:Number(y || 0) }; }
function monthShort(key){ const p = mParts(key); return p.y ? `${p.m}'${String(p.y).slice(-2)}` : key; }
function monthLabel(key){ const p = mParts(key); return p.y ? `${p.m} ${p.y}` : key; }
function quarterKey(key){ const p = mParts(key); const q = Math.floor((MONTH_INDEX[p.m] || 0) / 3) + 1; return `Q${q}-${p.y}`; }
function qParts(key){ const [q, y] = String(key || '').split('-'); return { q, y:Number(y || 0) }; }
function validRegion(name){ return !!name && name !== '-'; }
function marketObj(){ return MKT_MAP[cur]; }
function marketMonths(mk){ return MONTHS.filter(m => mk?.regionsByMonth?.[m]); }
function latestMonth(mk){ return mk?.latestMonth || marketMonths(mk).slice(-1)[0]; }
function regionRows(mk, month){ return ((mk?.regionsByMonth || {})[month] || []).filter(r => validRegion(r.name)); }
function productRows(mk, month){ return ((mk?.productsByMonth || {})[month] || []).filter(r => r && r.product); }
function regionRow(mk, reg, month){ return regionRows(mk, month).find(r => r.name === reg) || { name:reg, total:0, sie:0, share:0 }; }
function natRow(mk, month){
  const rows = regionRows(mk, month);
  const total = rows.reduce((sum, row) => sum + Number(row.total || 0), 0);
  const sie = rows.reduce((sum, row) => sum + Number(row.sie || 0), 0);
  return { total, sie, ms: total > 0 ? +(sie / total * 100).toFixed(1) : 0 };
}
function activeReg(){ return selRegs.length === 1 ? selRegs[0] : '__NAC__'; }
function activeLabel(){ return selRegs.length === 1 ? selRegs[0].replace(/^_/, '') : 'Nacional'; }
function getSieMS(mk, reg){
  return marketMonths(mk).map(month => reg === '__NAC__' ? natRow(mk, month).ms : Number(regionRow(mk, reg, month).share || 0));
}
function getProdMonthlyData(mk, product){
  return marketMonths(mk).map(month => {
    const row = productRows(mk, month).find(item => item.product === product);
    return { month, units:Number(row?.units || 0), ms:Number(row?.share || 0) };
  });
}
function getQuarterlySieMS(mk, reg){
  const grouped = {};
  marketMonths(mk).forEach(month => {
    const q = quarterKey(month);
    const row = reg === '__NAC__' ? natRow(mk, month) : regionRow(mk, reg, month);
    if (!grouped[q]) grouped[q] = { total:0, sie:0 };
    grouped[q].total += Number(row.total || 0);
    grouped[q].sie += Number(row.sie || 0);
  });
  return Object.keys(grouped).sort((a, b) => {
    const pa = qParts(a), pb = qParts(b);
    return pa.y * 10 + Number(pa.q.slice(1)) - (pb.y * 10 + Number(pb.q.slice(1)));
  }).map(q => ({ key:q, ms: grouped[q].total > 0 ? +(grouped[q].sie / grouped[q].total * 100).toFixed(1) : 0 }));
}
function getQuarterlyProdMS(mk, product){
  const grouped = {};
  marketMonths(mk).forEach(month => {
    const q = quarterKey(month);
    const row = productRows(mk, month).find(item => item.product === product);
    if (!grouped[q]) grouped[q] = { units:0, total:0 };
    grouped[q].units += Number(row?.units || 0);
    grouped[q].total += natRow(mk, month).total;
  });
  return Object.keys(grouped).sort((a, b) => {
    const pa = qParts(a), pb = qParts(b);
    return pa.y * 10 + Number(pa.q.slice(1)) - (pb.y * 10 + Number(pb.q.slice(1)));
  }).map(q => ({ key:q, ms: grouped[q].total > 0 ? +(grouped[q].units / grouped[q].total * 100).toFixed(1) : 0 }));
}
function topRegionsByLatest(mk, count){
  return [...regionRows(mk, latestMonth(mk))].sort((a, b) => Number(b.total || 0) - Number(a.total || 0)).slice(0, count).map(row => row.name);
}
function competitorRows(mk){ return productRows(mk, latestMonth(mk)).filter(row => !row.isSie); }
function allProductRows(mk){ return productRows(mk, latestMonth(mk)); }
function ensureSelection(){
  const mk = marketObj();
  const regionNames = regionRows(mk, latestMonth(mk)).map(row => row.name);
  const productNames = competitorRows(mk).map(row => row.product);
  selRegs = selRegs.filter(reg => regionNames.includes(reg));
  if (selB && !productNames.includes(selB)) selB = null;
}
function syncUrl(){
  const url = new URL(location.href);
  url.searchParams.set('market', cur);
  url.searchParams.set('family', marketObj()?.family || '');
  if (selB) url.searchParams.set('product', selB); else url.searchParams.delete('product');
  if (selRegs.length) url.searchParams.set('regions', selRegs.join('|')); else url.searchParams.delete('regions');
  history.replaceState({}, '', url);
}
function lineColor(index){ return BC[index % BC.length]; }
function destroyChart(key){ if (chs[key]) { chs[key].destroy(); chs[key] = null; } }

function toggleDD(){
  ddOpen = !ddOpen;
  document.getElementById('regDD').classList.toggle('open', ddOpen);
  if (ddOpen) {
    document.getElementById('regQ').value = '';
    buildRegList();
    document.getElementById('regQ').focus();
  }
}
function closeDD(){
  ddOpen = false;
  document.getElementById('regDD').classList.remove('open');
}
document.addEventListener('click', event => {
  const wrap = document.getElementById('regWrap');
  if (ddOpen && wrap && !wrap.contains(event.target)) closeDD();
});
function buildRegList(){
  const mk = marketObj();
  const latest = latestMonth(mk);
  const query = (document.getElementById('regQ')?.value || '').toLowerCase();
  const rows = [...regionRows(mk, latest)]
    .filter(row => row.name.replace(/^_/, '').toLowerCase().includes(query))
    .sort((a, b) => Number(b.total || 0) - Number(a.total || 0));
  const list = document.getElementById('regList');
  list.innerHTML = '';
  rows.forEach(row => {
    const div = document.createElement('div');
    const isSel = selRegs.includes(row.name);
    div.className = 'reg-opt' + (isSel ? ' sel' : '');
    div.innerHTML = `<div class="reg-chk">${isSel ? '✓' : ''}</div><span>${row.name.replace(/^_/, '')}</span>`;
    div.onclick = event => { event.stopPropagation(); toggleReg(row.name); };
    list.appendChild(div);
  });
}
function filterRegs(){ buildRegList(); }
function toggleReg(reg){
  const index = selRegs.indexOf(reg);
  if (index >= 0) selRegs.splice(index, 1); else selRegs.push(reg);
  onRegsChanged();
}
function clrRegs(){ selRegs = []; onRegsChanged(); closeDD(); }
function selTop7(){ selRegs = topRegionsByLatest(marketObj(), 7); onRegsChanged(); }
function onRegsChanged(){ buildRegList(); updBtnText(); updTags(); render(); }
function updBtnText(){
  const button = document.getElementById('regBtnText');
  if (!button) return;
  if (selRegs.length === 0) button.textContent = 'Nacional (todas)';
  else if (selRegs.length === 1) button.textContent = selRegs[0].replace(/^_/, '');
  else button.textContent = selRegs.length + ' regiones seleccionadas';
}
function updTags(){
  const el = document.getElementById('rtags');
  if (!el) return;
  if (selRegs.length === 0) { el.innerHTML = ''; return; }
  el.innerHTML = selRegs.map(reg => `<div class="rtag">${reg.replace(/^_/, '')}<span class="x" onclick="rmReg('${reg}')">✕</span></div>`).join('');
}
function rmReg(reg){ selRegs = selRegs.filter(item => item !== reg); onRegsChanged(); }

function renderHero(mk){
  const latest = latestMonth(mk);
  const active = activeLabel();
  document.querySelector('.hero-sub').textContent = `Market Share por Región · ${cur} · ${mk.family} · corte ${monthLabel(latest)} · vista ${active}`;
}

function lineOptions(legendFont){
  return {
    responsive:true,
    maintainAspectRatio:false,
    interaction:{mode:'index', intersect:false},
    plugins:{
      legend:{position:'bottom', labels:{usePointStyle:true, pointStyle:'circle', padding:10, font:{size:legendFont, weight:'500'}}},
      tooltip:{backgroundColor:'#1A1A1A', padding:10, cornerRadius:6, mode:'index', intersect:false, callbacks:{label:c => c.dataset.label + ': ' + c.parsed.y.toFixed(1) + '%'}}
    },
    scales:{
      y:{ticks:{callback:v => v.toFixed(1) + '%', font:{size:10.5}, color:'#737373'}, grid:{color:'#E5E5E522'}, border:{display:false}},
      x:{ticks:{font:{size:10.5, weight:'500'}, color:'#737373'}, grid:{display:false}, border:{display:false}}
    }
  };
}

function rKPI(mk){
  const ar = activeReg();
  const latest = latestMonth(mk);
  const first = marketMonths(mk)[0];
  const latestRow = ar === '__NAC__' ? natRow(mk, latest) : regionRow(mk, ar, latest);
  const firstRow = ar === '__NAC__' ? natRow(mk, first) : regionRow(mk, ar, first);
  const latestMs = Number(ar === '__NAC__' ? latestRow.ms : latestRow.share || 0);
  const firstMs = Number(ar === '__NAC__' ? firstRow.ms : firstRow.share || 0);
  const diff = +(latestMs - firstMs).toFixed(1);
  const label = activeLabel();
  let k4 = '';
  if (ar === '__NAC__') {
    const rows = regionRows(mk, latest);
    const above = rows.filter(row => Number(row.share || 0) > latestMs).length;
    k4 = `<div class="kc c4"><div class="kh">REGIONES SOBRE PROMEDIO</div><div class="kv purple">${above}<span style="font-size:15px;color:var(--t4)">/${rows.length}</span></div><div class="kd">MS% > ${fms(latestMs)} nacional</div></div>`;
  } else {
    const nat = natRow(mk, latest).ms;
    const gap = +(latestMs - nat).toFixed(1);
    k4 = `<div class="kc c4"><div class="kh">VS NACIONAL</div><div class="kv purple">${gap >= 0 ? '+' : ''}${gap}pp</div><div class="kd">Nacional: ${fms(nat)} · Región: ${fms(latestMs)}</div></div>`;
  }
  document.getElementById('kr').innerHTML = `
    <div class="kc c1"><div class="kh">MS% · ${label.toUpperCase()}</div><div class="kv red">${fms(latestMs)}</div><div class="kd">${cur}<br>${fmt(latestRow.total)} u. mercado</div></div>
    <div class="kc c2"><div class="kh">UNIDADES SIE · ${monthLabel(latest).toUpperCase()}</div><div class="kv blue">${fk(latestRow.sie)}</div><div class="kd">${mk.family}<br>de ${fk(latestRow.total)} u.</div></div>
    <div class="kc c3"><div class="kh">MS% ÚLTIMO CORTE · ${label.toUpperCase()}</div><div class="kv green">${fms(latestMs)}</div><div class="kd">${monthLabel(latest)} · <span style="color:${diff >= 0 ? 'var(--green)' : 'var(--red)'}">${diff >= 0 ? '+' : ''}${diff}pp</span> vs ${monthLabel(first)}</div></div>${k4}`;
}

function rBF(mk){
  const ch = document.getElementById('fcs');
  ch.innerHTML = '';
  competitorRows(mk).sort((a, b) => Number(b.units || 0) - Number(a.units || 0)).forEach((row, index) => {
    const d = document.createElement('div');
    d.className = 'bc' + (selB === row.product ? ' a' : '');
    d.innerHTML = `<span class="d" style="background:${lineColor(index)}"></span>${row.product}`;
    d.onclick = () => { selB = selB === row.product ? null : row.product; render(); };
    ch.appendChild(d);
  });
  document.getElementById('fcl').style.display = selB ? 'block' : 'none';
}
function clrB(){ selB = null; render(); }
function rC1(mk){
  destroyChart('c1');
  const ar = activeReg();
  const rl = activeLabel();
  const labels = marketMonths(mk).map(monthShort);
  const ds = [{
    label:'Siegfried',
    data:getSieMS(mk, ar),
    borderColor:SIE,
    backgroundColor:SIE + '15',
    fill:true,
    tension:.35,
    pointRadius:4,
    pointBackgroundColor:'#fff',
    pointBorderColor:SIE,
    pointBorderWidth:2,
    pointHoverRadius:6,
    borderWidth:2.5,
    order:0
  }];
  if (selB) {
    const prod = getProdMonthlyData(mk, selB);
    ds.push({
      label: ar === '__NAC__' ? selB : `${selB} (nac.)`,
      data:prod.map(item => item.ms),
      borderColor:SEL,
      backgroundColor:SEL + '10',
      fill:false,
      tension:.35,
      pointRadius:4,
      pointBackgroundColor:'#fff',
      pointBorderColor:SEL,
      pointBorderWidth:2,
      pointHoverRadius:6,
      borderDash: ar === '__NAC__' ? [] : [7,4],
      borderWidth:2.5,
      order:1
    });
  }
  document.getElementById('s1').textContent = selB ? `Siegfried vs ${selB} · ${rl}` : `Siegfried · ${rl}`;
  chs.c1 = new Chart(document.getElementById('c1').getContext('2d'), { type:'line', data:{ labels, datasets:ds }, options:lineOptions(10.5) });
}

function rC2(mk){
  destroyChart('c2');
  const labels = marketMonths(mk).map(monthShort);
  document.getElementById('s2').textContent = 'Top competidores · Nacional';
  const top = competitorRows(mk).sort((a, b) => Number(b.units || 0) - Number(a.units || 0)).slice(0, 8).map(row => row.product);
  if (selB && !top.includes(selB)) top[top.length - 1] = selB;
  const ds = [{
    label:'Siegfried',
    data:getSieMS(mk, '__NAC__'),
    borderColor:SIE,
    backgroundColor:'transparent',
    tension:.3,
    pointRadius:5,
    pointBackgroundColor:'#fff',
    pointBorderColor:SIE,
    pointBorderWidth:2.5,
    borderWidth:3,
    pointHoverRadius:5,
    order:0
  }];
  top.forEach((product, index) => {
    ds.push({
      label:product,
      data:getProdMonthlyData(mk, product).map(item => item.ms),
      borderColor:product === selB ? SEL : lineColor(index),
      backgroundColor:'transparent',
      tension:.3,
      pointRadius:product === selB ? 5 : 2.5,
      pointBackgroundColor:product === selB ? '#fff' : (product === selB ? SEL : lineColor(index)),
      pointBorderColor:product === selB ? SEL : lineColor(index),
      pointBorderWidth:product === selB ? 2.5 : 1,
      borderWidth:product === selB ? 3 : 1.2,
      pointHoverRadius:5,
      order:1
    });
  });
  chs.c2 = new Chart(document.getElementById('c2').getContext('2d'), { type:'line', data:{ labels, datasets:ds }, options:lineOptions(9.5) });
}

function rC3(mk){
  destroyChart('c3');
  const regsToShow = selRegs.length ? [...selRegs] : topRegionsByLatest(mk, 7);
  const qBase = getQuarterlySieMS(mk, '__NAC__');
  const ds = regsToShow.map((reg, index) => ({
    label:reg.replace(/^_/, ''),
    data:getQuarterlySieMS(mk, reg).map(item => item.ms),
    borderColor:RC[index % RC.length],
    backgroundColor:'transparent',
    tension:.3,
    pointRadius:5,
    pointBackgroundColor:'#fff',
    pointBorderColor:RC[index % RC.length],
    pointBorderWidth:2.5,
    borderWidth:2.5,
    pointHoverRadius:7
  }));
  ds.push({
    label:'Nacional',
    data:qBase.map(item => item.ms),
    borderColor:'#1A1A1A',
    borderDash:[5,3],
    backgroundColor:'transparent',
    tension:.3,
    pointRadius:3,
    pointBackgroundColor:'#1A1A1A',
    pointBorderColor:'#1A1A1A',
    borderWidth:1.5,
    pointHoverRadius:5
  });
  if (selB) {
    ds.push({
      label:`${selB} (producto)`,
      data:getQuarterlyProdMS(mk, selB).map(item => item.ms),
      borderColor:SEL,
      borderDash:[8,4],
      backgroundColor:'transparent',
      tension:.3,
      pointRadius:5,
      pointBackgroundColor:'#fff',
      pointBorderColor:SEL,
      pointBorderWidth:2.5,
      borderWidth:2.5,
      pointHoverRadius:7
    });
  }
  document.getElementById('s3').textContent = selRegs.length ? (selRegs.length === 1 ? selRegs[0].replace(/^_/, '') : selRegs.length + ' regiones seleccionadas') : 'Top 7 regiones por volumen';
  chs.c3 = new Chart(document.getElementById('c3').getContext('2d'), {
    type:'line',
    data:{ labels:qBase.map(item => item.key), datasets:ds },
    options:{
      ...lineOptions(10.5),
      scales:{
        y:{ticks:{callback:v => v.toFixed(1) + '%', font:{size:10.5}, color:'#737373'}, grid:{color:'#E5E5E522'}, border:{display:false}},
        x:{ticks:{font:{size:11, weight:'600'}, color:'#525252'}, grid:{display:false}, border:{display:false}}
      }
    }
  });
}

function rComp(mk){
  const months = marketMonths(mk);
  const latest = months[months.length - 1];
  const prev = months[months.length - 2] || latest;
  const latestNat = natRow(mk, latest);
  const prevNat = natRow(mk, prev);
  const rows = [{ name:'Siegfried', ms:latestNat.ms, units:latestNat.sie, var:+(latestNat.ms - prevNat.ms).toFixed(2), sie:true }];
  competitorRows(mk).forEach(row => {
    const prevRow = productRows(mk, prev).find(item => item.product === row.product);
    rows.push({
      name:row.product,
      ms:Number(row.share || 0),
      units:Number(row.units || 0),
      var:+(Number(row.share || 0) - Number(prevRow?.share || 0)).toFixed(2),
      sie:false
    });
  });
  rows.sort((a, b) => (b.sie - a.sie) || (Number(b.units || 0) - Number(a.units || 0)));
  const maxMs = Math.max(...rows.map(row => row.ms), 1);
  document.getElementById('cpe').textContent = `PRODUCTOS NACIONALES · ${monthLabel(latest).toUpperCase()}`;
  document.getElementById('cbo').innerHTML = rows.map((row, index) => {
    const hl = selB === row.name;
    const vc = row.var > 0 ? 'p' : row.var < 0 ? 'n' : 'z';
    const vs = row.var > 0 ? '+' : '';
    const bw = Math.max(row.ms / maxMs * 100, 1);
    return `<tr style="${hl ? 'background:#EFF6FF;font-weight:600' : row.sie ? 'background:#FEF2F2' : ''}"><td class="rk">${index + 1}</td>
      <td><div class="cbb"><div class="cl ${row.sie ? 's' : 'o'}"></div>${row.name}${row.sie ? ' <span class="st">SIE</span>' : ''}</div></td>
      <td class="r mn">${row.ms.toFixed(1)}%</td><td class="shs"><div class="sb"><div class="sf ${row.sie ? 's' : 'o'}" style="width:${bw}%"></div></div></td>
      <td class="r un">${fmt(row.units)}</td><td class="r"><span class="vb ${vc}">${vs}${row.var.toFixed(2)}pp</span></td></tr>`;
  }).join('');
}

function rTbl(mk){
  const latest = latestMonth(mk);
  let rows = regionRows(mk, latest).map(row => ({ region:row.name.replace(/^_/, ''), rr:row.name, total:Number(row.total || 0), sie:Number(row.sie || 0), ms:Number(row.share || 0) }));
  rows.sort((a, b) => {
    if (sC === 'region') return sD === 'asc' ? a.region.localeCompare(b.region, 'es') : b.region.localeCompare(a.region, 'es');
    return sD === 'asc' ? a[sC] - b[sC] : b[sC] - a[sC];
  });
  const maxMs = Math.max(...rows.map(row => row.ms), 1);
  const natMs = natRow(mk, latest).ms;
  let html = `<table class="rt2"><thead><tr><th onclick="doS('region')">#</th><th onclick="doS('region')">Región ↕</th><th onclick="doS('ms')">MS% ↕</th><th onclick="doS('sie')">U. Siegfried ↕</th><th onclick="doS('total')">U. Mercado ↕</th><th>vs Nac.</th></tr></thead><tbody>`;
  rows.forEach((row, index) => {
    const diff = +(row.ms - natMs).toFixed(1);
    const bw = Math.max(row.ms / maxMs * 100, 2);
    const act = selRegs.includes(row.rr);
    html += `<tr style="${act ? 'background:#FEF2F2;font-weight:700;' : ''}" onclick="tglRegFromTbl('${row.rr}')"><td class="rk">${index + 1}</td><td style="font-weight:600">${row.region}</td><td><div class="mbc"><div class="mmb ${row.ms >= natMs ? 'hi' : 'lo'}" style="width:${bw}%"></div><span class="mv">${row.ms.toFixed(1)}%</span></div></td><td class="uv">${fmt(row.sie)}</td><td class="uv">${fmt(row.total)}</td><td><span class="badge ${diff >= 0 ? 'up' : 'down'}">${diff >= 0 ? '+' : ''}${diff}pp</span></td></tr>`;
  });
  html += '</tbody></table>';
  document.getElementById('tw').innerHTML = html;
}
function tglRegFromTbl(reg){ toggleReg(reg); }
function doS(col){ if (sC === col) sD = sD === 'asc' ? 'desc' : 'asc'; else { sC = col; sD = col === 'region' ? 'asc' : 'desc'; } rTbl(marketObj()); }
const PROVS = [
  {id:'jujuy', pts:'97,6 131,6 125,44 97,38', zones:['JUJUY']},
  {id:'salta', pts:'97,6 161,6 169,34 153,70 97,38', zones:['SALTA']},
  {id:'formosa', pts:'161,6 223,6 216,58 161,58', zones:['FORMOSA']},
  {id:'misiones', pts:'223,6 281,16 279,72 252,96 221,70', zones:['POSADAS']},
  {id:'chaco', pts:'161,58 216,58 207,102 188,114 161,108', zones:['RESISTENCIA']},
  {id:'tucuman', pts:'97,68 130,68 121,100 94,94', zones:['TUCUMAN']},
  {id:'corrientes', pts:'161,58 207,102 252,96 240,128 218,134 200,112 161,108', zones:['CORRIENTES']},
  {id:'catamarca', pts:'80,70 97,68 94,94 78,116 58,114 56,86', zones:['CATAMARCA']},
  {id:'santiago', pts:'130,68 161,68 157,130 139,134 121,100', zones:['SANTIAGO DEL ESTERO']},
  {id:'entre_r', pts:'200,112 218,134 240,128 242,160 236,196 206,196 194,150', zones:['PARANA','CONCORDIA']},
  {id:'larioja', pts:'56,86 78,116 74,160 50,158 46,120', zones:['LA RIOJA']},
  {id:'sanjuan', pts:'36,104 80,104 78,168 48,170 34,150', zones:['SAN JUAN']},
  {id:'cordoba', pts:'78,108 157,108 157,198 78,200', zones:['CORDOBA','RIO IV Y ALREDEDORES','SAN FCO-ESTE Y NORTE']},
  {id:'santafe', pts:'157,94 196,94 200,196 157,196', zones:['ROSARIO','SANTA FE','RAFAELA-NTE SANTA FE']},
  {id:'mendoza', pts:'32,150 78,150 76,196 56,220 30,210 30,184', zones:['MENDOZA','SAN RAFAEL']},
  {id:'sanluis', pts:'78,154 120,154 118,200 78,204', zones:['SAN LUIS']},
  {id:'bsas', pts:'138,196 236,196 256,254 240,304 203,312 144,312 124,284 120,228', zones:['AZUL-OLAVARRIA-TANDIL','BAHIA BLANCA','JUNIN-CHIVILCOY-PERGAMINO','M.DEL PLATA','BARADERO-SAN PEDRO-RAMALLO-SAN NICOLAS','LUJAN Y ALREDEDORES','LA PLATA','ZARATE - CAMPANA','PILAR - ESCOBAR']},
  {id:'gba', pts:'202,192 240,192 238,208 202,208', zones:['_CAPITAL FEDERAL','_SUBURBANO NORTE','_SUBURBANO OESTE','_SUBURBANO SUR']},
  {id:'lapampa', pts:'60,196 120,196 124,284 88,296 58,268 56,222', zones:['SANTA ROSA']},
  {id:'neuquen', pts:'28,238 78,238 76,310 28,312', zones:['NEUQUEN']},
  {id:'rionegro', pts:'28,312 158,312 148,358 28,360', zones:['RIO NEGRO']},
  {id:'chubut', pts:'26,360 130,360 126,452 26,454', zones:['TRELEW','COMODORO RIVADAVIA']},
  {id:'santacruz', pts:'24,430 106,430 104,500 24,502', zones:['SANTA CRUZ']},
  {id:'tdf', pts:'42,478 104,478 102,506 42,506', zones:['TIERRA DEL FUEGO']}
];

const ZPOS = {
  '_CAPITAL FEDERAL':{x:224,y:200}, '_SUBURBANO NORTE':{x:216,y:194},
  '_SUBURBANO OESTE':{x:210,y:200}, '_SUBURBANO SUR':{x:218,y:206},
  'LA PLATA':{x:230,y:208}, 'ZARATE - CAMPANA':{x:216,y:190}, 'PILAR - ESCOBAR':{x:212,y:194}, 'LUJAN Y ALREDEDORES':{x:206,y:198},
  'BARADERO-SAN PEDRO-RAMALLO-SAN NICOLAS':{x:198,y:182}, 'JUNIN-CHIVILCOY-PERGAMINO':{x:180,y:196}, 'M.DEL PLATA':{x:238,y:250},
  'AZUL-OLAVARRIA-TANDIL':{x:194,y:240}, 'BAHIA BLANCA':{x:158,y:264}, 'ROSARIO':{x:182,y:168}, 'SANTA FE':{x:184,y:146},
  'RAFAELA-NTE SANTA FE':{x:168,y:142}, 'SAN FCO-ESTE Y NORTE':{x:162,y:144}, 'CORDOBA':{x:134,y:146}, 'RIO IV Y ALREDEDORES':{x:124,y:168},
  'PARANA':{x:190,y:148}, 'CONCORDIA':{x:228,y:146}, 'POSADAS':{x:262,y:84}, 'CORRIENTES':{x:212,y:88}, 'RESISTENCIA':{x:204,y:86},
  'FORMOSA':{x:222,y:64}, 'SALTA':{x:110,y:44}, 'JUJUY':{x:113,y:30}, 'TUCUMAN':{x:110,y:72}, 'SANTIAGO DEL ESTERO':{x:134,y:90},
  'CATAMARCA':{x:108,y:98}, 'LA RIOJA':{x:92,y:114}, 'SAN JUAN':{x:66,y:140}, 'MENDOZA':{x:62,y:170}, 'SAN RAFAEL':{x:70,y:192},
  'SAN LUIS':{x:96,y:176}, 'SANTA ROSA':{x:128,y:228}, 'NEUQUEN':{x:50,y:270}, 'RIO NEGRO':{x:144,y:296}, 'TRELEW':{x:110,y:332},
  'COMODORO RIVADAVIA':{x:76,y:372}, 'SANTA CRUZ':{x:60,y:434}, 'TIERRA DEL FUEGO':{x:68,y:480}
};

function zoneColor(pct){
  const p = Math.min(Math.max(pct, 0), 1);
  if (p < 0.5) {
    const t = p * 2;
    return `rgb(${Math.round(203 + (30 - 203) * t)},${Math.round(213 + (58 - 213) * t)},${Math.round(225 + (95 - 225) * t)})`;
  }
  const t = (p - 0.5) * 2;
  return `rgb(${Math.round(30 + (122 - 30) * t)},${Math.round(58 + (21 - 58) * t)},${Math.round(95 + (24 - 95) * t)})`;
}
function highlightZone(reg){
  document.querySelectorAll('[data-zone]').forEach(el => {
    const match = el.dataset.zone === reg;
    el.setAttribute('fill-opacity', match ? '1' : '0.25');
    el.setAttribute('stroke-width', match ? '1.8' : '0.5');
    el.setAttribute('stroke-opacity', match ? '0.9' : '0.2');
  });
}
function clearHighlight(){
  document.querySelectorAll('[data-zone]').forEach(el => {
    el.setAttribute('fill-opacity', '0.82');
    el.setAttribute('stroke-width', '0.8');
    el.setAttribute('stroke-opacity', '0.4');
  });
}
function showTip(tipId, bgId, t1, t2, t3, t4, name, ms, total, sie, natMs, tx, ty, svgW, svgH){
  const tip = document.getElementById(tipId);
  if (!tip) return;
  const diff = (ms - natMs).toFixed(1);
  document.getElementById(t1).textContent = name.replace(/^_/, '');
  document.getElementById(t2).textContent = `MS%: ${ms.toFixed(1)}%`;
  document.getElementById(t3).textContent = total > 0 ? `SIE: ${sie.toLocaleString('es-AR')} · Mkt: ${total.toLocaleString('es-AR')}` : '';
  document.getElementById(t4).textContent = `vs Nac: ${diff >= 0 ? '+' : ''}${diff} pp`;
  const W = 158, H = 52;
  document.getElementById(bgId).setAttribute('width', W);
  document.getElementById(bgId).setAttribute('height', H);
  let x = tx + 8, y = ty - 28;
  if (x + W > svgW - 4) x = tx - W - 8;
  if (y < 4) y = 4;
  if (y + H > svgH - 4) y = svgH - H - 4;
  tip.setAttribute('transform', `translate(${x},${y})`);
  tip.setAttribute('visibility', 'visible');
}

function rMapa(mk){
  if (!document.getElementById('prov-layer')) return;
  const NS = 'http://www.w3.org/2000/svg';
  const latest = latestMonth(mk);
  const zData = {};
  regionRows(mk, latest).forEach(row => { zData[row.name] = { ms:Number(row.share || 0), sie:Number(row.sie || 0), total:Number(row.total || 0) }; });
  const allMs = Object.values(zData).map(item => item.ms);
  const allTot = Object.values(zData).map(item => item.total).filter(item => item > 0);
  const maxMs = Math.max(...allMs, 0.1);
  const maxTotal = Math.max(...allTot, 1);
  const natMs = natRow(mk, latest).ms;
  document.getElementById('map-leg-max').textContent = maxMs.toFixed(1) + '%';
  document.getElementById('s6').textContent = `MS%: ${cur} · ${monthLabel(latest)}`;
  const pLayer = document.getElementById('prov-layer');
  pLayer.innerHTML = '';
  PROVS.forEach(prov => {
    const poly = document.createElementNS(NS, 'polygon');
    poly.setAttribute('points', prov.pts);
    poly.setAttribute('fill', '#f1f5f9');
    poly.setAttribute('stroke', '#cbd5e1');
    poly.setAttribute('stroke-width', '0.7');
    pLayer.appendChild(poly);
  });
  const bLayer = document.getElementById('bub-layer');
  const mapTip = document.getElementById('map-tip');
  bLayer.innerHTML = '';
  const entries = Object.entries(ZPOS).filter(([reg]) => zData[reg]).sort((a, b) => zData[b[0]].total - zData[a[0]].total);
  const rMax = 22, rMin = 4;
  entries.forEach(([reg, pos]) => {
    const data = zData[reg];
    const pct = maxMs > 0 ? data.ms / maxMs : 0;
    const r = rMin + (rMax - rMin) * Math.sqrt(data.total / maxTotal);
    const fill = zoneColor(pct);
    const circ = document.createElementNS(NS, 'circle');
    circ.setAttribute('cx', pos.x);
    circ.setAttribute('cy', pos.y);
    circ.setAttribute('r', r.toFixed(1));
    circ.setAttribute('fill', fill);
    circ.setAttribute('fill-opacity', '0.82');
    circ.setAttribute('stroke', 'white');
    circ.setAttribute('stroke-opacity', '0.4');
    circ.setAttribute('stroke-width', '0.8');
    circ.setAttribute('data-zone', reg);
    if (data.ms > maxMs * 0.4) circ.setAttribute('filter', 'url(#fglow)');
    circ.style.cursor = 'pointer';
    circ.addEventListener('mouseenter', () => {
      highlightZone(reg);
      showTip('map-tip', 'mt-bg', 'mt-t1', 'mt-t2', 'mt-t3', 'mt-t4', reg, data.ms, data.total, data.sie, natMs, pos.x, pos.y, 300, 560);
      bLayer.parentNode.appendChild(mapTip);
    });
    circ.addEventListener('mouseleave', () => { clearHighlight(); mapTip.setAttribute('visibility', 'hidden'); });
    circ.addEventListener('click', () => toggleReg(reg));
    bLayer.appendChild(circ);
  });
  rScatter(zData, maxMs, natMs);
  renderZT(zData, maxMs, natMs);
}
function rScatter(zData, maxMs, natMs){
  const NS = 'http://www.w3.org/2000/svg';
  const gEl = document.getElementById('scatter-g');
  if (!gEl) return;
  const W = 400, H = 320, ML = 50, MR = 14, MT = 28, MB = 46;
  const PW = W - ML - MR, PH = H - MT - MB;
  const scTip = document.getElementById('sc-tip');
  gEl.innerHTML = '';
  const allTotals = Object.values(zData).map(item => item.total).filter(item => item > 0);
  const minTotal = Math.min(...allTotals);
  const maxTotal = Math.max(...allTotals);
  const logMin = Math.log10(Math.max(minTotal, 1));
  const logMax = Math.log10(Math.max(maxTotal, 1));
  const xSc = total => ML + (Math.log10(Math.max(total, 1)) - logMin) / Math.max(logMax - logMin, 1) * PW;
  const ySc = ms => MT + PH - (ms / (maxMs * 1.18)) * PH;
  const rSc = total => 4 + 14 * Math.sqrt(total / maxTotal);
  const yStep = maxMs > 30 ? 10 : maxMs > 12 ? 5 : 2;
  for (let value = 0; value <= maxMs * 1.2; value += yStep) {
    const y = ySc(value);
    if (y < MT || y > MT + PH) continue;
    const gl = document.createElementNS(NS, 'line');
    gl.setAttribute('x1', ML); gl.setAttribute('x2', ML + PW); gl.setAttribute('y1', y); gl.setAttribute('y2', y);
    gl.setAttribute('stroke', '#f0f0f0'); gl.setAttribute('stroke-width', '1');
    gEl.appendChild(gl);
    const gt = document.createElementNS(NS, 'text');
    gt.setAttribute('x', ML - 5); gt.setAttribute('y', y + 3.5); gt.setAttribute('text-anchor', 'end'); gt.setAttribute('fill', '#9ca3af'); gt.setAttribute('font-size', '9'); gt.textContent = value + '%';
    gEl.appendChild(gt);
  }
  [500,1000,2000,5000,10000,20000,50000,100000,200000,500000,1000000,2000000].filter(value => value >= minTotal * 0.3 && value <= maxTotal * 3).forEach(value => {
    const x = xSc(value);
    if (x < ML || x > ML + PW) return;
    const gl = document.createElementNS(NS, 'line');
    gl.setAttribute('x1', x); gl.setAttribute('x2', x); gl.setAttribute('y1', MT); gl.setAttribute('y2', MT + PH); gl.setAttribute('stroke', '#f0f0f0'); gl.setAttribute('stroke-width', '1');
    gEl.appendChild(gl);
    const lbl = value >= 1e6 ? (value / 1e6).toFixed(1) + 'M' : value >= 1e3 ? (value / 1e3).toFixed(0) + 'k' : value;
    const gt = document.createElementNS(NS, 'text');
    gt.setAttribute('x', x); gt.setAttribute('y', MT + PH + 16); gt.setAttribute('text-anchor', 'middle'); gt.setAttribute('fill', '#9ca3af'); gt.setAttribute('font-size', '8.5'); gt.textContent = lbl;
    gEl.appendChild(gt);
  });
  const natY = ySc(natMs);
  const refL = document.createElementNS(NS, 'line');
  refL.setAttribute('x1', ML); refL.setAttribute('x2', ML + PW); refL.setAttribute('y1', natY); refL.setAttribute('y2', natY); refL.setAttribute('stroke', '#7A1518'); refL.setAttribute('stroke-width', '1.2'); refL.setAttribute('stroke-dasharray', '5 3'); refL.setAttribute('opacity', '0.75');
  gEl.appendChild(refL);
  const refT = document.createElementNS(NS, 'text');
  refT.setAttribute('x', ML + PW - 4); refT.setAttribute('y', natY - 5); refT.setAttribute('text-anchor', 'end'); refT.setAttribute('fill', '#f87171'); refT.setAttribute('font-size', '8.5'); refT.setAttribute('font-weight', '600'); refT.textContent = `Nac. ${natMs.toFixed(1)}%`;
  gEl.appendChild(refT);
  const ax = document.createElementNS(NS, 'polyline');
  ax.setAttribute('points', `${ML},${MT} ${ML},${MT + PH} ${ML + PW},${MT + PH}`); ax.setAttribute('fill', 'none'); ax.setAttribute('stroke', '#d1d5db'); ax.setAttribute('stroke-width', '1.2');
  gEl.appendChild(ax);
  const yLbl = document.createElementNS(NS, 'text');
  yLbl.setAttribute('transform', `rotate(-90,14,${MT + PH / 2})`); yLbl.setAttribute('x', 14); yLbl.setAttribute('y', MT + PH / 2); yLbl.setAttribute('text-anchor', 'middle'); yLbl.setAttribute('fill', '#9ca3af'); yLbl.setAttribute('font-size', '9'); yLbl.textContent = 'Market Share %';
  gEl.appendChild(yLbl);
  const xLbl = document.createElementNS(NS, 'text');
  xLbl.setAttribute('x', ML + PW / 2); xLbl.setAttribute('y', H - 10); xLbl.setAttribute('text-anchor', 'middle'); xLbl.setAttribute('fill', '#9ca3af'); xLbl.setAttribute('font-size', '9'); xLbl.textContent = 'Unidades de mercado (log)';
  gEl.appendChild(xLbl);
  const title = document.createElementNS(NS, 'text');
  title.setAttribute('x', ML + PW / 2); title.setAttribute('y', MT - 12); title.setAttribute('text-anchor', 'middle'); title.setAttribute('fill', '#6b7280'); title.setAttribute('font-size', '10'); title.setAttribute('font-weight', '600'); title.textContent = 'Volumen vs MS% · por zona CUP';
  gEl.appendChild(title);
  [{x:ML+4,y:MT+12,txt:'Baja vol · Alta MS',anchor:'start'},{x:ML+PW-4,y:MT+12,txt:'Alta vol · Alta MS',anchor:'end'},{x:ML+4,y:MT+PH-5,txt:'Baja vol · Baja MS',anchor:'start'},{x:ML+PW-4,y:MT+PH-5,txt:'Alta vol · Baja MS',anchor:'end'}].forEach(item => {
    const qt = document.createElementNS(NS, 'text');
    qt.setAttribute('x', item.x); qt.setAttribute('y', item.y); qt.setAttribute('text-anchor', item.anchor); qt.setAttribute('fill', '#e5e7eb'); qt.setAttribute('font-size', '7.5'); qt.textContent = item.txt;
    gEl.appendChild(qt);
  });
  Object.entries(zData).filter(([, item]) => item.total > 0).sort((a, b) => b[1].total - a[1].total).forEach(([reg, item]) => {
    const x = xSc(item.total), y = ySc(item.ms), r = rSc(item.total), pct = maxMs > 0 ? item.ms / maxMs : 0, fill = zoneColor(pct);
    const circ = document.createElementNS(NS, 'circle');
    circ.setAttribute('cx', x.toFixed(1)); circ.setAttribute('cy', y.toFixed(1)); circ.setAttribute('r', r.toFixed(1)); circ.setAttribute('fill', fill); circ.setAttribute('fill-opacity', '0.82'); circ.setAttribute('stroke', 'white'); circ.setAttribute('stroke-opacity', '0.4'); circ.setAttribute('stroke-width', '0.8'); circ.setAttribute('data-zone', reg); circ.style.cursor = 'pointer';
    if (item.total > maxTotal * 0.08 || item.ms > maxMs * 0.6) {
      const lbl = document.createElementNS(NS, 'text');
      lbl.setAttribute('x', x + r + 3); lbl.setAttribute('y', y + 3.5); lbl.setAttribute('fill', '#9ca3af'); lbl.setAttribute('font-size', '7.5'); lbl.setAttribute('pointer-events', 'none'); lbl.textContent = reg.replace(/^_/, '').split('-')[0].trim();
      gEl.appendChild(lbl);
    }
    circ.addEventListener('mouseenter', () => { highlightZone(reg); showTip('sc-tip', 'st-bg', 'st-t1', 'st-t2', 'st-t3', 'st-t4', reg, item.ms, item.total, item.sie, natMs, x, y, W, H); gEl.appendChild(scTip); });
    circ.addEventListener('mouseleave', () => { clearHighlight(); scTip.setAttribute('visibility', 'hidden'); });
    circ.addEventListener('click', () => toggleReg(reg));
    gEl.appendChild(circ);
  });
  gEl.appendChild(scTip);
}

function renderZT(zData, maxMs, natMs){
  const tbody = document.getElementById('zona-tbl-mapa');
  if (!tbody) return;
  let rows = Object.entries(zData).map(([reg, data]) => ({ zone:reg.replace(/^_/, ''), reg, ms:data.ms, sie:data.sie, total:data.total, diff:+(data.ms - natMs).toFixed(2) }));
  rows.sort((a, b) => {
    const va = ztSort.col === 'zone' ? a.zone.toLowerCase() : a[ztSort.col];
    const vb = ztSort.col === 'zone' ? b.zone.toLowerCase() : b[ztSort.col];
    if (va === vb) return 0;
    return ztSort.dir === -1 ? (va > vb ? -1 : 1) : (va > vb ? 1 : -1);
  });
  tbody.innerHTML = rows.map((row, index) => {
    const pct = maxMs > 0 ? row.ms / maxMs : 0;
    const col = zoneColor(pct);
    const dCol = row.diff >= 0 ? '#16a34a' : '#dc2626';
    const barW = Math.max(pct * 100, 1).toFixed(1);
    const isSel = selRegs.includes(row.reg);
    return `<tr class="${isSel ? 'act' : ''}" onclick="toggleReg('${row.reg}')"><td class="zt-num">${index + 1}</td><td class="zt-zone"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${col};margin-right:5px;vertical-align:middle"></span>${row.zone}</td><td class="zt-ms"><div class="ms-bar-wrap"><span style="min-width:36px;text-align:right">${row.ms.toFixed(1)}%</span><div class="ms-bar-bg"><div class="ms-bar-fill" style="width:${barW}%"></div></div></div></td><td class="zt-diff" style="color:${dCol}">${row.diff >= 0 ? '+' : ''}${row.diff}pp</td><td class="zt-units">${row.sie.toLocaleString('es-AR')}</td><td class="zt-units" style="color:#a3a3a3">${row.total.toLocaleString('es-AR')}</td></tr>`;
  }).join('');
}
function sortZT(th){
  const col = th.dataset.col;
  if (ztSort.col === col) ztSort.dir *= -1; else { ztSort.col = col; ztSort.dir = col === 'zone' ? 1 : -1; }
  document.querySelectorAll('.zt thead th').forEach(header => { header.className = header.dataset.col === col ? (ztSort.dir === -1 ? 'sort-desc' : 'sort-asc') : 'sort-none'; });
  render();
}

function init(){
  const bar = document.getElementById('mbar');
  ORDERED_MARKETS.forEach(market => {
    const chip = document.createElement('div');
    chip.className = 'mc' + (market === cur ? ' a' : '');
    chip.textContent = market;
    chip.dataset.m = market;
    chip.onclick = () => {
      cur = market;
      ensureSelection();
      document.querySelectorAll('.mc').forEach(node => node.classList.toggle('a', node.dataset.m === market));
      render();
    };
    bar.appendChild(chip);
  });
  ensureSelection();
  buildRegList();
  updBtnText();
  updTags();
  render();
}

function render(){
  const mk = marketObj();
  if (!mk) return;
  ensureSelection();
  syncUrl();
  renderHero(mk);
  rKPI(mk);
  rBF(mk);
  rC1(mk);
  rC2(mk);
  rC3(mk);
  rComp(mk);
  rTbl(mk);
  rMapa(mk);
  buildRegList();
  updBtnText();
  updTags();
}

init();
