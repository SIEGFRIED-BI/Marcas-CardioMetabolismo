// shared/qlik/rofina-discover.mjs
// Descubre en la app de Convenios el objeto que tiene la tabla 'Convenios vs mostrador'
// y los campos de filtro (Año / Mes / MesesRollBack). NO extrae datos todavia.
// Uso: node shared/qlik/rofina-discover.mjs
import { loadSession, rest, openEngine } from "./rofina-session.mjs";

const s = loadSession();
console.log(`tenant : ${s.tenant}`);
console.log(`appId  : ${s.appId}`);

// 1) la sesion vive?
const me = await rest("/api/v1/users/me", s);
console.log(`sesion : OK -> ${me.name} <${me.email || "sin email"}>  (subject ${me.subject?.slice(0, 12)}...)`);

// 2) abrir la app por Engine
const { session, app } = await openEngine(s.appId, s);
const layout = await app.getAppLayout();
console.log(`app    : ${layout.qTitle}  (lastReload ${layout.qLastReloadTime})`);

// 3) campos del modelo
const tablesModel = await app.getTablesAndKeys({}, {}, 0, true, false);
const campos = new Set();
for (const t of tablesModel.qtr || []) for (const f of t.qFields || []) campos.add(f.qName);
const interes = [...campos].filter((c) =>
  /a.o|mes|rollback|familia|producto|laboratorio|obrasocial|convenio|mostrador|unidad|consumo/i.test(c)
);
console.log(`\ncampos relevantes (${interes.length} de ${campos.size}):`);
for (const c of interes.sort()) console.log(`   ${c}`);

// 4) objetos de la hoja
const sheets = await app.getObjects({ qTypes: ["sheet"], qIncludeSessionObjects: false, qData: {} });
console.log(`\nhojas: ${sheets.length}`);
for (const sh of sheets) {
  const o = await app.getObject(sh.qInfo.qId);
  const lay = await o.getLayout();
  const titulo = lay.qMeta?.title || "(sin titulo)";
  const marca = sh.qInfo.qId === s.sheetId ? "  <<< la del link" : "";
  console.log(`\n  hoja ${sh.qInfo.qId}  "${titulo}"${marca}`);
  for (const cell of lay.cells || []) {
    try {
      const child = await app.getObject(cell.name);
      const cl = await child.getLayout();
      const hc = cl.qHyperCube;
      const dims = (hc?.qDimensionInfo || []).map((d) => d.qFallbackTitle);
      const meas = (hc?.qMeasureInfo || []).map((m) => m.qFallbackTitle);
      const t = cl.qMeta?.title || cl.title || "";
      console.log(`     ${cell.type.padEnd(14)} ${cell.name}  "${t}"`);
      if (dims.length || meas.length) {
        console.log(`        dims  (${dims.length}): ${dims.join(" | ")}`);
        console.log(`        meds  (${meas.length}): ${meas.join(" | ")}`);
        if (hc?.qSize) console.log(`        size  : ${hc.qSize.qcx} x ${hc.qSize.qcy}`);
      }
    } catch (e) {
      console.log(`     ${cell.type.padEnd(14)} ${cell.name}  (no pude leer: ${e.message})`);
    }
  }
}

await session.close();
process.exit(0);
