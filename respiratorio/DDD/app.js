const ROOT = window.OTC_DATA || {};
const DD = ROOT.ddd || {};
const RESP_DDD = ROOT.respDdd || {};
const RESP_FAMILIES = RESP_DDD.families || {};
const MKT_MAP = Object.keys(RESP_FAMILIES).length ? RESP_FAMILIES : (DD.markets || {});
const MONTHS = RESP_DDD.months || DD.months || [];
const FAMILY_MAP = ROOT.familyToMarkets || {};
// Cubo nacional por producto para los filtros de la pagina Competidores
// (forma farmaceutica / condicion etico-popular / molecula). Certificado 0-diff
// contra respDdd.molecule.all (sum por producto == total del mercado por familia/mes).
// Solo respiratorio lo trae; si falta, los filtros quedan inertes y la pagina
// se comporta identico a antes.
const RESP_DETAIL = RESP_DDD.detail || {};
function hasMeaningfulDddMarket(market){
  const views = MKT_MAP[market];
  if (!views) return false;
  const bucket = views?.molecule?.all || views;
  const monthly = bucket?.monthly || [];
  return monthly.some(row => Number(row?.total || 0) > 0 || Number(row?.sie || 0) > 0);
}
const ORDERED_MARKETS = (RESP_DDD.order || FAMILY_MAP.Totales || Object.keys(MKT_MAP)).filter(m => MKT_MAP[m] && hasMeaningfulDddMarket(m));
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
  if (qFamily && MKT_MAP[qFamily]) return qFamily;
  if (!Object.keys(RESP_FAMILIES).length && qFamily && FAMILY_MAP[qFamily] && FAMILY_MAP[qFamily][0]) return FAMILY_MAP[qFamily][0];
  const rootDefault = ROOT.defaults?.market || ROOT.defaults?.brand;
  if (rootDefault && MKT_MAP[rootDefault]) return rootDefault;
  if (!Object.keys(RESP_FAMILIES).length && rootDefault && FAMILY_MAP[rootDefault] && FAMILY_MAP[rootDefault][0]) return FAMILY_MAP[rootDefault][0];
  return ORDERED_MARKETS[0];
}

let cur = defaultMarket();
let cmp = PARAMS.get('compare') || 'molecule';
let seg = PARAMS.get('segment') || 'all';
if (!['molecule','atc'].includes(cmp)) cmp = 'molecule';
if (!['all','etico','popular'].includes(seg)) seg = 'all';
let selRegs = (PARAMS.get('regions') || '').split('|').filter(Boolean);
let selB = PARAMS.get('product') || null;
let chs = {};
let sC = 'total';
let sD = 'desc';
let ddOpen = false;
let ztSort = { col:'ms', dir:-1 };
// Sort para la tabla de productos nacionales (rComp). 'default' = SIE primero
// + units desc; otras opciones: 'ms' | 'units' | 'var' con dir asc/desc.
let pSort = { col:'default', dir:'desc' };
// Filtros del panel de competidores (operan sobre RESP_DETAIL, mercado nacional).
// filForma/filMol vacios = sin filtro (todas). filCond: 'all'|'etico'|'popular'.
let filForma = new Set((PARAMS.get('forma') || '').split('|').filter(Boolean));
let filMol = new Set((PARAMS.get('mol') || '').split('|').filter(Boolean));
let filCond = PARAMS.get('cond') || 'all';
if (!['all','etico','popular'].includes(filCond)) filCond = 'all';

function fmt(n){ return Number(n || 0).toLocaleString('es-AR'); }
function fms(n){ return Number(n || 0).toFixed(1) + '%'; }
function fk(n){ const v = Number(n || 0); return v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1) + 'k' : fmt(v); }
function mParts(key){ const [m, y] = String(key || '').split('-'); return { m, y:Number(y || 0) }; }
function monthShort(key){ const p = mParts(key); return p.y ? `${p.m}'${String(p.y).slice(-2)}` : key; }
function monthLabel(key){ const p = mParts(key); return p.y ? `${p.m} ${p.y}` : key; }
function quarterKey(key){ const p = mParts(key); const q = Math.floor((MONTH_INDEX[p.m] || 0) / 3) + 1; return `Q${q}-${p.y}`; }
function qParts(key){ const [q, y] = String(key || '').split('-'); return { q, y:Number(y || 0) }; }
function validRegion(name){ return !!name && name !== '-'; }
function familyViewMap(){ return MKT_MAP[cur] || {}; }
function marketObj(){
  const familyViews = familyViewMap();
  if (familyViews?.molecule || familyViews?.atc) {
    return familyViews?.[cmp]?.[seg] || familyViews?.[cmp]?.all || familyViews?.molecule?.all || null;
  }
  return familyViews;
}
// ---- Filtros de competidores (cubo nacional RESP_DETAIL) ----
function detailFor(family){ return (RESP_DETAIL[family] && RESP_DETAIL[family].products) || []; }
function familyHasDetail(family){ return detailFor(family).length > 0; }
function familyFormas(family){ return [...new Set(detailFor(family).map(p => p.forma || '(s.d.)'))].sort((a,b)=>a.localeCompare(b,'es')); }
function familyMolecules(family){ return [...new Set(detailFor(family).map(p => p.mol).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es')); }
function passFilters(p){
  if (filForma.size && !filForma.has(p.forma || '(s.d.)')) return false;
  if (filMol.size && !filMol.has(p.mol)) return false;
  if (filCond !== 'all' && p.seg !== filCond) return false;
  return true;
}
function filterActive(){ return familyHasDetail(cur) && (filForma.size > 0 || filMol.size > 0 || filCond !== 'all'); }
function filteredProducts(family){ return detailFor(family).filter(passFilters); }
// Sintetiza un objeto con forma de bucket (monthly/regionsByMonth/productsByMonth)
// a partir del cubo nacional filtrado, para que rC2/rComp/rBF (y sus helpers)
// funcionen sin cambios. regionsByMonth trae una unica fila 'Nacional' -> natRow
// devuelve el total nacional del universo filtrado.
function synthNatView(family){
  const base = MKT_MAP[family] && MKT_MAP[family].molecule && MKT_MAP[family].molecule.all;
  const axis = base ? MONTHS.filter(m => base.regionsByMonth && base.regionsByMonth[m]) : MONTHS.slice();
  const prods = filteredProducts(family);
  const monthly = [], regionsByMonth = {}, productsByMonth = {};
  axis.forEach(m => {
    let total = 0, sie = 0;
    const pr = [];
    prods.forEach(p => {
      const u = Number(p.u[m] || 0);
      if (u > 0) { total += u; if (p.sie) sie += u; pr.push({ product:p.p, units:u, isSie:!!p.sie }); }
    });
    const share = total > 0 ? +(sie / total * 100).toFixed(1) : 0;
    monthly.push({ month:m, total:Math.round(total), sie:Math.round(sie), share });
    regionsByMonth[m] = [{ name:'Nacional', total:Math.round(total), sie:Math.round(sie), share }];
    pr.forEach(x => { x.share = total > 0 ? +(x.units / total * 100).toFixed(1) : 0; });
    pr.sort((a,b) => b.units - a.units);
    // total/sie ya se sumaron sobre TODOS los productos filtrados; la lista visible
    // se acota a top-20/mes para que la tabla y el chart no se vuelvan gigantes.
    productsByMonth[m] = pr.slice(0, 20);
  });
  return { family, latestMonth: axis[axis.length - 1] || '', monthly, regionsByMonth, productsByMonth, _synth:true };
}
// Vista nacional para los paneles de competidores: bucket normal si no hay filtro,
// o la vista sintetizada filtrada si hay. Los paneles regionales siguen usando marketObj().
function natViewObj(){ return filterActive() ? synthNatView(cur) : marketObj(); }
// Poda selecciones de filtro que no existen en el market actual (al cambiar de mercado).
function pruneFilters(){
  if (!familyHasDetail(cur)) { filForma.clear(); filMol.clear(); filCond = 'all'; return; }
  const forms = new Set(familyFormas(cur));
  const mols = new Set(familyMolecules(cur));
  filForma = new Set([...filForma].filter(f => forms.has(f)));
  filMol = new Set([...filMol].filter(m => mols.has(m)));
}
function marketMonths(mk){ return MONTHS.filter(m => mk?.regionsByMonth?.[m]); }
function latestMonth(mk){ return mk?.latestMonth || marketMonths(mk).slice(-1)[0] || MONTHS.slice(-1)[0] || ''; }
function regionRows(mk, month){ return ((mk?.regionsByMonth || {})[month] || []).filter(r => validRegion(r.name)); }
function productRows(mk, month){ return ((mk?.productsByMonth || {})[month] || []).filter(r => r && r.product); }
// Devuelve los productos vistos en los ultimos N meses del market.
// Util para que productos como TUKOL (que dejaron de reportar a IQVIA pero
// son competidores historicos relevantes) aparezcan en la lista aunque
// tengan 0 unidades en el mes actual.
function recentProductRows(mk, monthsBack = 6){
  const months = marketMonths(mk);
  if (!months.length) return [];
  const recent = months.slice(-monthsBack);
  const latest = months[months.length - 1];
  const latestRows = new Map(productRows(mk, latest).map(r => [r.product, r]));
  // Empezamos desde el mes mas viejo y avanzamos: el dato mas reciente gana
  const newest = new Map();
  recent.forEach(m => {
    productRows(mk, m).forEach(r => {
      newest.set(r.product, { row:r, month:m });
    });
  });
  const out = [];
  newest.forEach((entry, prod) => {
    if (latestRows.has(prod)) {
      out.push(latestRows.get(prod));
    } else {
      // Producto sin datos en el mes actual; lo mostramos con 0/0 y la
      // ultima fecha en que reporto, para no confundir.
      out.push({ ...entry.row, units:0, share:0, _historic:true, _lastSeen:entry.month });
    }
  });
  return out;
}
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
function competitorRows(mk){
  // Antes: solo productos del ultimo mes. Ahora: ultimos 6 meses para que
  // historicos como TUKOL (que dejaron de reportar) sigan apareciendo.
  return recentProductRows(mk, 6).filter(row => !row.isSie);
}
function allProductRows(mk){ return productRows(mk, latestMonth(mk)); }
function ensureSelection(){
  const mk = marketObj();
  const nv = natViewObj();
  const regionNames = regionRows(mk, latestMonth(mk)).map(row => row.name);
  const productNames = competitorRows(nv).map(row => row.product);
  selRegs = selRegs.filter(reg => regionNames.includes(reg));
  if (selB && !productNames.includes(selB)) selB = null;
}
function syncUrl(){
  const url = new URL(location.href);
  url.searchParams.set('market', cur);
  url.searchParams.set('family', marketObj()?.family || '');
  url.searchParams.set('compare', cmp);
  url.searchParams.set('segment', seg);
  if (selB) url.searchParams.set('product', selB); else url.searchParams.delete('product');
  if (selRegs.length) url.searchParams.set('regions', selRegs.join('|')); else url.searchParams.delete('regions');
  if (filForma.size) url.searchParams.set('forma', [...filForma].join('|')); else url.searchParams.delete('forma');
  if (filMol.size) url.searchParams.set('mol', [...filMol].join('|')); else url.searchParams.delete('mol');
  if (filCond !== 'all') url.searchParams.set('cond', filCond); else url.searchParams.delete('cond');
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
  const cmpLabel = cmp === 'atc' ? 'ATC' : 'misma molécula';
  const segLabel = seg === 'all' ? 'todos' : (seg === 'etico' ? 'ético' : 'popular');
  document.querySelector('.hero-sub').textContent = `Market Share por Región · ${cur} · ${cmpLabel} · ${segLabel} · corte ${monthLabel(latest)} · vista ${active}`;
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
  // Con filtro activo, las tarjetas nacionales reflejan el mercado filtrado
  // (vista nacional sintetizada). El filtro es nacional, asi que se ignora la
  // seleccion de region para las KPI y la tarjeta 4 pasa a "peso del filtro".
  const useFilt = filterActive();
  const kmk = useFilt ? natViewObj() : mk;
  const ar = useFilt ? '__NAC__' : activeReg();
  const latest = latestMonth(kmk);
  const first = marketMonths(kmk)[0];
  const latestRow = ar === '__NAC__' ? natRow(kmk, latest) : regionRow(kmk, ar, latest);
  const firstRow = ar === '__NAC__' ? natRow(kmk, first) : regionRow(kmk, ar, first);
  const latestMs = Number(ar === '__NAC__' ? latestRow.ms : latestRow.share || 0);
  const firstMs = Number(ar === '__NAC__' ? firstRow.ms : firstRow.share || 0);
  const diff = +(latestMs - firstMs).toFixed(1);
  const label = useFilt ? 'Nacional' : activeLabel();
  let k4 = '';
  if (useFilt) {
    const full = natRow(mk, latest).total;
    const peso = full > 0 ? +(latestRow.total / full * 100).toFixed(1) : 0;
    k4 = `<div class="kc c4"><div class="kh">PESO DEL FILTRO</div><div class="kv purple">${peso}%</div><div class="kd">${fmt(latestRow.total)} de ${fmt(full)} u.<br>del mercado ${cur}</div></div>`;
  } else if (ar === '__NAC__') {
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
    <div class="kc c2"><div class="kh">UNIDADES SIE · ${monthLabel(latest).toUpperCase()}</div><div class="kv blue">${fk(latestRow.sie)}</div><div class="kd">${kmk.family}<br>de ${fk(latestRow.total)} u.</div></div>
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
      sie:false,
      historic:!!row._historic,
      lastSeen:row._lastSeen
    });
  });
  // Sort: por defecto SIE primero + units desc; si el user clickeo un header,
  // ordenamos por esa columna (manteniendo SIE arriba para no perderlo).
  if (pSort.col === 'default') {
    rows.sort((a, b) => (b.sie - a.sie) || (Number(b.units || 0) - Number(a.units || 0)));
  } else {
    const dir = pSort.dir === 'asc' ? 1 : -1;
    const key = pSort.col;
    rows.sort((a, b) => {
      if (a.sie !== b.sie) return b.sie - a.sie;
      return (Number(a[key] || 0) - Number(b[key] || 0)) * dir;
    });
  }
  // Indicadores ↑ ↓ ↕ en headers
  ['ms','units','var'].forEach(col => {
    const el = document.getElementById('ps-' + col);
    if (!el) return;
    if (pSort.col === col) {
      el.textContent = pSort.dir === 'asc' ? '↑' : '↓';
      el.style.color = '#b01e1e';
    } else {
      el.textContent = '↕';
      el.style.color = '#a3a3a3';
    }
  });
  const maxMs = Math.max(...rows.map(row => row.ms), 1);
  const periodTxt = (prev && prev !== latest)
    ? `PRODUCTOS NACIONALES · ${monthLabel(latest).toUpperCase()} vs ${monthLabel(prev).toUpperCase()}`
    : `PRODUCTOS NACIONALES · ${monthLabel(latest).toUpperCase()}`;
  document.getElementById('cpe').textContent = periodTxt;
  document.getElementById('cbo').innerHTML = rows.map((row, index) => {
    const hl = selB === row.name;
    const vc = row.var > 0 ? 'p' : row.var < 0 ? 'n' : 'z';
    const vs = row.var > 0 ? '+' : '';
    const bw = Math.max(row.ms / maxMs * 100, 1);
    const histTag = row.historic ? ` <span style="font-size:9px;color:#94a3b8;font-weight:400;font-style:italic;" title="Sin datos IQVIA en el mes actual; ultima vez visto en ${row.lastSeen || 'mes previo'}">sin datos en periodo</span>` : '';
    const opacity = row.historic ? 'opacity:0.55;' : '';
    return `<tr style="${opacity}${hl ? 'background:#EFF6FF;font-weight:600' : row.sie ? 'background:#FEF2F2' : ''}"><td class="rk">${index + 1}</td>
      <td><div class="cbb"><div class="cl ${row.sie ? 's' : 'o'}"></div>${row.name}${row.sie ? ' <span class="st">SIE</span>' : ''}${histTag}</div></td>
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
// Sort handler para la tabla de productos nacionales (rComp).
// Click en el mismo header alterna asc/desc. Click en uno nuevo arranca desc
// (asumimos que el user quiere ver el mas alto primero). Click en la
// columna actual cuando ya esta desc -> asc; click otra vez -> default.
function pSortBy(col){
  if (pSort.col === col) {
    if (pSort.dir === 'desc') { pSort.dir = 'asc'; }
    else { pSort.col = 'default'; pSort.dir = 'desc'; }
  } else {
    pSort.col = col;
    pSort.dir = 'desc';
  }
  const mk = marketObj();
  if (mk) rComp(mk);
}
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
  const cmpBar = document.getElementById('cmpBar');
  const segBar = document.getElementById('segBar');
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

  [
    { key:'molecule', label:'Molécula' },
    { key:'atc', label:'ATC' }
  ].forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'mc' + (item.key === cmp ? ' a' : '');
    chip.textContent = item.label;
    chip.dataset.c = item.key;
    chip.onclick = () => {
      cmp = item.key;
      ensureSelection();
      document.querySelectorAll('#cmpBar .mc').forEach(node => node.classList.toggle('a', node.dataset.c === item.key));
      render();
    };
    cmpBar.appendChild(chip);
  });

  [
    { key:'all', label:'Todos' }
  ].forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'mc' + (item.key === seg ? ' a' : '');
    chip.textContent = item.label;
    chip.dataset.s = item.key;
    chip.onclick = () => {
      seg = item.key;
      ensureSelection();
      document.querySelectorAll('#segBar .mc').forEach(node => node.classList.toggle('a', node.dataset.s === item.key));
      render();
    };
    segBar.appendChild(chip);
  });

  ensureSelection();
  buildRegList();
  updBtnText();
  updTags();
  render();
}

// Detecta si los segmentos etico/popular tienen data para el market actual.
// Cuando el master IQVIA no trae Market Type, los buckets quedan vacios y
// hay que deshabilitar el chip para no enganhar al usuario.
function refreshSegChipsAvailability(){
  const views = MKT_MAP[cur] || {};
  const cmpView = views[cmp] || {};
  ['all', 'etico', 'popular'].forEach(seg => {
    const bucket = cmpView[seg];
    let hasData = false;
    if (bucket && bucket.productsByMonth) {
      hasData = Object.values(bucket.productsByMonth).some(arr => Array.isArray(arr) && arr.length > 0);
    }
    const chip = document.querySelector(`#segBar .mc[data-s="${seg}"]`);
    if (!chip) return;
    if (hasData) {
      chip.style.opacity = '';
      chip.style.pointerEvents = '';
      chip.style.cursor = '';
      chip.title = '';
    } else {
      chip.style.opacity = '0.35';
      chip.style.pointerEvents = 'none';
      chip.style.cursor = 'not-allowed';
      chip.title = 'Sin data de segmento (IQVIA Premium master no trae Market Type)';
    }
  });
  // Si la seleccion actual quedo en un seg sin datos, caemos a 'all'
  const curChip = document.querySelector(`#segBar .mc[data-s="${seg}"]`);
  if (curChip && curChip.style.pointerEvents === 'none') {
    seg = 'all';
    document.querySelectorAll('#segBar .mc').forEach(n => n.classList.toggle('a', n.dataset.s === 'all'));
  }
}

// ---- UI de filtros de competidores ----
function filtChip(label, active, onClick, title){
  const c = document.createElement('div');
  c.className = 'mc' + (active ? ' a' : '');
  c.textContent = label;
  if (title) c.title = title;
  c.onclick = onClick;
  return c;
}
function buildFilterBars(){
  const wrap = document.getElementById('filtGroups');
  const has = familyHasDetail(cur);
  if (wrap) wrap.style.display = has ? 'flex' : 'none';
  if (!has) return;
  const fb = document.getElementById('formaBar');
  if (fb){
    fb.innerHTML = '';
    fb.appendChild(filtChip('Todas', filForma.size === 0, () => { filForma.clear(); render(); }));
    familyFormas(cur).forEach(f => fb.appendChild(
      filtChip(f, filForma.has(f), () => { filForma.has(f) ? filForma.delete(f) : filForma.add(f); render(); })));
  }
  const cb = document.getElementById('condBar');
  if (cb){
    cb.innerHTML = '';
    [['all','Todas'],['etico','Bajo receta · ético'],['popular','Venta libre · popular']].forEach(([k,l]) =>
      cb.appendChild(filtChip(l, filCond === k, () => { filCond = k; render(); })));
  }
  const mb = document.getElementById('molBar');
  if (mb){
    mb.innerHTML = '';
    mb.appendChild(filtChip('Todas', filMol.size === 0, () => { filMol.clear(); render(); }));
    familyMolecules(cur).forEach(m => mb.appendChild(
      filtChip(m, filMol.has(m), () => { filMol.has(m) ? filMol.delete(m) : filMol.add(m); render(); })));
  }
}
function updFilterNote(){
  const el = document.getElementById('filtNote');
  if (!el) return;
  if (!filterActive()){ el.style.display = 'none'; el.innerHTML = ''; return; }
  const parts = [];
  if (filCond !== 'all') parts.push(filCond === 'etico' ? 'bajo receta (ético)' : 'venta libre (popular)');
  if (filForma.size) parts.push('forma: ' + [...filForma].join(', '));
  if (filMol.size) parts.push('molécula: ' + [...filMol].join(', '));
  const nv = natViewObj();
  const latest = latestMonth(nv);
  const nat = natRow(nv, latest);
  const n = filteredProducts(cur).length;
  el.style.display = 'block';
  el.innerHTML = `<b>Filtro activo</b> · ${parts.join(' · ')} — ${n} producto${n === 1 ? '' : 's'} · mercado ${fmt(nat.total)} u. (${monthLabel(latest)}). ` +
    `<span style="opacity:.75">Aplica a los paneles de competidores (02 · MS% Mensual y 04 · tabla); el mapa y las tablas por región muestran el mercado completo.</span> ` +
    `<a href="#" onclick="clrFilters();return false;" style="color:var(--sie);font-weight:700">Limpiar filtros</a>`;
}
function clrFilters(){ filForma.clear(); filMol.clear(); filCond = 'all'; render(); }

function render(){
  const mk = marketObj();
  if (!mk) return;
  pruneFilters();
  ensureSelection();
  syncUrl();
  refreshSegChipsAvailability();
  const nv = natViewObj();
  renderHero(mk);
  rKPI(mk);
  rBF(nv);
  rC1(mk);
  rC2(nv);
  rC3(mk);
  rComp(nv);
  rTbl(mk);
  rMapa(mk);
  buildFilterBars();
  updFilterNote();
  buildRegList();
  updBtnText();
  updTags();
}

init();
