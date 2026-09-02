// shared/qlik/rofina-inspect-obj.mjs
// Definiciones EXACTAS del objeto 'Convenios vs mostrador' + estado de selecciones +
// valores posibles de los campos de filtro. Necesario antes de extraer: hay que saber
// que hace 'MesesRollBack' y con que selecciones esta armado el numero publicado.
// Uso: node shared/qlik/rofina-inspect-obj.mjs [objectId]
import { loadSession, openEngine } from "./rofina-session.mjs";

const OBJ = process.argv[2] || "ThZZvT";
const s = loadSession();
const { session, app } = await openEngine(s.appId, s);

const o = await app.getObject(OBJ);
const props = await o.getProperties();
const hc = props.qHyperCubeDef || {};

console.log(`=== objeto ${OBJ}: "${props.qMetaDef?.title || props.title || ""}" (${props.qInfo?.qType})`);
console.log(`\nDIMENSIONES (${(hc.qDimensions || []).length}):`);
for (const d of hc.qDimensions || []) {
  const def = d.qDef || {};
  console.log(`   fieldDefs=${JSON.stringify(def.qFieldDefs)}  labels=${JSON.stringify(def.qFieldLabels)}`);
}
console.log(`\nMEDIDAS (${(hc.qMeasures || []).length}):`);
for (const m of hc.qMeasures || []) {
  const def = m.qDef || {};
  console.log(`   "${def.qLabel || ""}"`);
  console.log(`        ${def.qDef}`);
  if (def.qNumFormat?.qFmt) console.log(`        fmt: ${def.qNumFormat.qFmt}  type:${def.qNumFormat.qType}`);
}
console.log(`\nqMode=${hc.qMode}  qSuppressZero=${hc.qSuppressZero}  qSuppressMissing=${hc.qSuppressMissing}`);
if (hc.qInterColumnSortOrder) console.log(`sortOrder=${JSON.stringify(hc.qInterColumnSortOrder)}`);

// selecciones actuales
const lay = await app.getAppLayout();
console.log(`\n=== SELECCIONES ACTUALES`);
const selObj = await app.createSessionObject({
  qInfo: { qType: "selections" },
  qSelectionObjectDef: {},
});
const selLay = await selObj.getLayout();
for (const sel of selLay.qSelectionObject?.qSelections || []) {
  console.log(`   ${sel.qField}: ${sel.qSelectedCount}/${sel.qTotal}  -> ${sel.qSelected}`);
}
if (!(selLay.qSelectionObject?.qSelections || []).length) console.log("   (ninguna)");

// valores posibles de los campos de filtro
console.log(`\n=== VALORES de los campos de filtro`);
for (const campo of ["Año", "Mes", "MesesRollBack", "AñoMesVisible", "AñoSeleccion", "MesSeleccion"]) {
  try {
    const lb = await app.createSessionObject({
      qInfo: { qType: "lb" },
      qListObjectDef: {
        qDef: { qFieldDefs: [campo] },
        qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 60, qWidth: 1 }],
      },
    });
    const l = await lb.getLayout();
    const items = (l.qListObject?.qDataPages?.[0]?.qMatrix || []).map(
      (r) => `${r[0].qText}${r[0].qState === "S" ? "*" : ""}`
    );
    console.log(`   ${campo.padEnd(16)} total=${l.qListObject?.qSize?.qcy}  ${items.join(", ")}`);
  } catch (e) {
    console.log(`   ${campo.padEnd(16)} (error: ${e.message})`);
  }
}
console.log("\n(* = seleccionado)");

await session.close();
process.exit(0);
