/* shared/render/sections.js
 * F3 - render compartido. Contiene las funciones de render que son IDENTICAS
 * (mismo token-stream) en las 7 lineas (verificado jun-2026): se movieron aca
 * para tener UNA sola copia (antes copiadas en las 7 paginas).
 *
 * Resuelven el dato y el estado por scope global lexico (cada pagina declara
 * `const D`, mas covBrand/covView/covFilter/covCharts/COV_LABELS/covClassify/
 * cqProd/Chart): este archivo es un <script> clasico que comparte el mismo
 * entorno global, asi que las referencias se resuelven en tiempo de LLAMADA
 * (DOMContentLoaded / despues de que la pagina definio esos globals).
 *
 * IMPORTANTE: incluir ANTES del <script> principal de la pagina, porque
 * renderCanQuartTable se llama inline en el top-level de ese script.
 *
 * Equivalencia A===B verificada en preview en las 7 antes de borrar las copias
 * inline. NO agregar aca funciones que difieran entre lineas (ver F3).
 */

function renderCobertura(){
  const grid = document.getElementById('cov-grid');
  if(!grid) return;

  // Rango de fechas del sec-sub: derivado del dato (coverage_labels), no literal.
  const __cr = document.getElementById('cov-range');
  if(__cr && Array.isArray(D.coverage_labels) && D.coverage_labels.length){
    __cr.textContent = D.coverage_labels[0] + ' – ' + D.coverage_labels[D.coverage_labels.length-1];
  }

  // If brand filter active, force presentacion view
  const isPresView = covBrand ? true : (covView === 'presentacion');
  const SA_all = isPresView ? (D.stock_pres||{}) : (D.stock_alerts||{});
  // Apply brand filter
  const SA = covBrand
    ? Object.fromEntries(Object.entries(SA_all).filter(([,v])=>v && v.familia===covBrand))
    : SA_all;
  // Guard: ignorar entries malformados/vacios (p.ej. familias sin dato de stock que
  // el builder emite como {}), asi un entry incompleto no rompe toda la seccion.
  const prods = Object.keys(SA).filter(p => SA[p] && Array.isArray(SA[p].alert_indices));

  // Summary counts
  let q=0,b=0,a=0,ok=0;
  prods.forEach(p=>{
    const ws = SA[p].worst_status;
    if(ws==='quiebre'||ws==='critico') q++;
    else if(ws==='bajo') b++;
    else if(ws==='alerta') a++;
    else ok++;
  });
  const qEl=document.getElementById('cov-q'); if(qEl) qEl.textContent=q||'0';
  const bEl=document.getElementById('cov-b'); if(bEl) bEl.textContent=b||'0';
  const aEl=document.getElementById('cov-a'); if(aEl) aEl.textContent=a||'0';
  const okEl=document.getElementById('cov-ok'); if(okEl) okEl.textContent=ok||'0';

  // Filter
  let filtered = prods.filter(p=>{
    const ws = SA[p].worst_status;
    if(covFilter==='all') return true;
    if(covFilter==='quiebre') return ws==='quiebre'||ws==='critico';
    if(covFilter==='bajo') return ws==='bajo';
    if(covFilter==='alerta') return ws==='alerta';
    if(covFilter==='ok') return ws==='ok';
    return true;
  });

  // Destroy old charts
  Object.values(covCharts).forEach(c=>{try{c.destroy();}catch(e){}});
  covCharts={};
  grid.innerHTML='';

  const STATUS_COLORS = {quiebre:'#b91c1c',critico:'#c2410c',bajo:'#d97706',alerta:'#2563eb',ok:'#16a34a',nd:'#9ca3af'};

  filtered.forEach(prod=>{
    const pd = SA[prod];
    const {ventas,dias,statuses,alert_indices,worst_status,n_alerts} = pd;

    const card = document.createElement('div');
    card.className = `cov-mini-card worst-${worst_status}`;

    // Build alert badges text
    const alertBadges = alert_indices.map(i=>{
      const s = statuses[i];
      const d = dias[i];
      return `<span class="cov-badge ${s==='critico'?'quiebre':s}">${COV_LABELS[i]}${d!==null?' '+d+'d':''}</span>`;
    }).join('');

    const lastDias = [...dias].reverse().find(x=>x!==null);
    const lastStatus = covClassify(lastDias);
    const diasColor = STATUS_COLORS[lastStatus]||'#9ca3af';
    const diasPct = lastDias!=null ? Math.min(Math.round(lastDias/30*100),100) : 0;

    card.innerHTML=`
      <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <span style="font-size:12px;font-weight:700;color:#111827;line-height:1.3;">${prod}</span>
          <span style="font-size:9px;font-family:'IBM Plex Mono',monospace;color:${diasColor};font-weight:700;flex-shrink:0;margin-left:8px;">
            ${lastDias!=null ? lastDias+'d' : '—'}
          </span>
        </div>
        ${isPresView&&SA[prod]?.familia ? `<span style="font-size:9px;color:#9ca3af;font-weight:600;text-transform:uppercase;letter-spacing:.08em;">${SA[prod].familia}</span>` : ''}
      </div>
      <div style="position:relative;height:110px;margin-bottom:8px;"><canvas id="cov-c-${prod.replace(/[^a-zA-Z0-9]/g,'_')}"></canvas></div>
      <div style="height:3px;background:#f3f4f6;border-radius:2px;margin-bottom:6px;overflow:hidden;">
        <div style="height:100%;width:${diasPct}%;background:${diasColor};border-radius:2px;transition:width .4s;"></div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:2px;min-height:18px;">
        ${alertBadges || '<span style="font-size:9px;color:#16a34a;font-weight:600;">✓ Sin alertas</span>'}
      </div>`;
    grid.appendChild(card);

    // Mini sparkline chart
    const canvasId = `cov-c-${prod.replace(/[^a-zA-Z0-9]/g,'_')}`;
    const ctx = card.querySelector(`#${canvasId}`).getContext('2d');

    const pointColors = statuses.map(s=>STATUS_COLORS[s]||'#b01e1e');
    const pointRadius = statuses.map(s=>s!=='ok'&&s!=='nd' ? 5 : 2);
    const pointStyle = statuses.map(s=>s!=='ok'&&s!=='nd' ? 'triangle' : 'circle');

    // Vertical alert plugin
    const vLines = {
      id:'vl_'+prod,
      beforeDraw(chart){
        const {ctx:c,chartArea:{top,bottom},scales:{x}}=chart;
        alert_indices.forEach(i=>{
          const s=statuses[i]; if(s==='nd') return;
          const xPos=x.getPixelForValue(i);
          c.save();
          c.beginPath();
          c.strokeStyle=(STATUS_COLORS[s]||'#888')+'60';
          c.lineWidth=s==='quiebre'?2:1;
          c.setLineDash(s==='quiebre'?[]:[3,2]);
          c.moveTo(xPos,top); c.lineTo(xPos,bottom);
          c.stroke(); c.restore();
        });
      }
    };

    const ch = new Chart(ctx,{
      type:'line',
      plugins:[vLines],
      data:{
        labels:COV_LABELS,
        datasets:[{
          data:ventas,
          borderColor:'#b01e1e',
          backgroundColor:'rgba(176,30,30,.06)',
          fill:true, tension:.35, borderWidth:1.5,
          pointBackgroundColor:pointColors,
          pointBorderColor:pointColors,
          pointRadius:pointRadius,
          pointStyle:pointStyle,
          pointHoverRadius:6,
        }]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{
          legend:{display:false},
          tooltip:{
            backgroundColor:'#1f2937',
            callbacks:{
              title:c=>`${COV_LABELS[c[0].dataIndex]} · ${prod}`,
              label:c=>{
                const i=c.dataIndex; const d=dias[i]; const s=statuses[i];
                const icons={quiebre:'🔴',critico:'🟠',bajo:'🟡',alerta:'🔵',ok:'✅',nd:'⚪'};
                const vStr=c.parsed.y!=null?(c.parsed.y>=1e6?(c.parsed.y/1e6).toFixed(2)+'M':c.parsed.y>=1e3?(c.parsed.y/1e3).toFixed(0)+'k':c.parsed.y):'—';
                return [`Ventas: ${vStr} u.`, d!=null?`${icons[s]||'⚪'} ${d}d stock`:'Sin datos stock'];
              }
            }
          }
        },
        scales:{
          x:{display:true,ticks:{color:'#9ca3af',font:{size:8,family:'IBM Plex Mono'},maxRotation:45,minRotation:45,autoSkip:true,autoSkipPadding:6},grid:{display:false},border:{display:false}},
          y:{display:false,beginAtZero:false}
        }
      }
    });
    covCharts[prod]=ch;
  });
}

function renderCanQuartTable(){
  const el = document.getElementById('can-quart-table'); if(!el) return;
  const data = (D.canales_quarterly||{})[cqProd];
  if(!data){ el.innerHTML='<p style="color:#4b5563;font-size:11px;padding:8px;">Sin datos para esta marca.</p>'; return; }
  const years = Object.keys(data).sort();
  const quarters = ['Q1','Q2','Q3','Q4'];
  // v.x marca el trimestre donde el % no es interpretable, con el motivo:
  //   'desfasaje' -> consumo por convenio del trimestre > unidades facturadas. El
  //                  %convenio es real (se muestra, NO se clampea: es la senal), pero
  //                  el mostrador, que sale por resta, seria negativo -> '—'.
  //   'base'      -> unidades facturadas <= 0 (devoluciones netas >= facturacion). No
  //                  hay universo contra el que medir: los dos van '—'.
  const TIP = {
    desfasaje: 'El consumo por convenio del trimestre supera las unidades facturadas',
    base: 'Unidades facturadas ≤ 0 en el trimestre (devoluciones netas ≥ facturación)'
  };
  const motivos = new Set();
  Object.values(data).forEach(y => Object.values(y||{}).forEach(v => { if(v && v.x) motivos.add(v.x); }));
  const valCell = (v, key) => {
    if(!v || v[key]==null){
      const t = (v && v.x) ? ` title="${TIP[v.x]||'Sin dato'}"` : '';
      return `<span style="color:#6b7280;"${t}>—</span>`;
    }
    const col = key==='c' ? '#2563eb' : '#d97706';
    const star = (v.x && key==='c')
      ? `<sup style="color:#dc2626;font-weight:700;" title="${TIP[v.x]||''}">*</sup>`
      : '';
    return `<span style="color:${col};font-weight:700;">${v[key].toFixed(0)}%</span>${star}`;
  };
  let html = '<div style="overflow-x:auto;border-radius:6px;border:1px solid rgba(0,0,0,.08);"><table style="width:100%;border-collapse:collapse;font-size:12px;">';
  // First header row: Año + 4 colspan=2 quarters
  html += '<thead>';
  html += '<tr style="background:#1f2937;color:#fff;">';
  html += '<th rowspan="2" style="text-align:left;padding:10px 14px;font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;border-right:1px solid rgba(255,255,255,.08);">Año</th>';
  for(const q of quarters){
    html += `<th colspan="2" style="text-align:center;padding:10px 8px;font-size:11px;font-weight:700;letter-spacing:.05em;border-right:1px solid rgba(255,255,255,.08);border-bottom:1px solid rgba(255,255,255,.12);">${q}</th>`;
  }
  html += '</tr>';
  // Sub-header row: Conv | Most repeated
  html += '<tr style="background:#1f2937;color:#9ca3af;">';
  for(let i=0;i<4;i++){
    html += '<th style="text-align:center;padding:6px 8px;font-size:9px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;color:#60a5fa;border-right:1px solid rgba(255,255,255,.05);">Convenio</th>';
    html += '<th style="text-align:center;padding:6px 8px;font-size:9px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;color:#fbbf24;border-right:1px solid rgba(255,255,255,.08);">Mostrador</th>';
  }
  html += '</tr></thead>';
  html += '<tbody>';
  for(let i=0;i<years.length;i++){
    const y = years[i];
    const bg = i%2===0 ? '#ffffff' : '#f9fafb';
    html += `<tr style="background:${bg};border-bottom:1px solid rgba(0,0,0,.05);">`;
    html += `<td style="padding:11px 14px;font-weight:700;color:#111827;border-right:1px solid rgba(0,0,0,.06);">${y}</td>`;
    for(const q of quarters){
      const v = (data[y]||{})[q];
      html += `<td style="padding:11px 8px;text-align:center;background:rgba(37,99,235,.04);">${valCell(v,'c')}</td>`;
      html += `<td style="padding:11px 8px;text-align:center;background:rgba(217,119,6,.04);border-right:1px solid rgba(0,0,0,.06);">${valCell(v,'m')}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table></div>';
  html += '<p style="margin-top:12px;font-size:10px;color:#6b7280;letter-spacing:.04em;"><span style="color:#2563eb;font-weight:700">■</span> Convenio OS &nbsp;·&nbsp; <span style="color:#d97706;font-weight:700">■</span> Mostrador</p>';
  if(motivos.size){
    html += '<p style="margin-top:4px;font-size:10px;color:#6b7280;line-height:1.5;">';
    if(motivos.has('desfasaje')){
      html += '<span style="color:#dc2626;font-weight:700">*</span> El consumo por convenio del trimestre (CloseUp) '
           +  'supera las unidades facturadas (SAP) — desfasaje entre facturación y dispensa. '
           +  'El % de convenio es el real; el de mostrador, que sale por resta, no es medible y va como «—».';
    }
    if(motivos.has('base')){
      if(motivos.has('desfasaje')) html += '<br>';
      html += '«—» en ambas columnas: las unidades facturadas del trimestre fueron ≤ 0 '
           +  '(devoluciones netas ≥ facturación), así que no hay base contra la cual medir el reparto.';
    }
    html += '</p>';
  }
  el.innerHTML = html;
}
