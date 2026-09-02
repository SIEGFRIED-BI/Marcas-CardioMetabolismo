// shared/qlik/rofina-extract-convenios.mjs
// Extrae 'Convenios vs mostrador' a nivel FAMILIA del tenant rofina.us, replicando el
// layout del export manual (Laboratorio | Familia | Producto | Producto_key | 12 medidas).
//
// El trimestre se arma seleccionando AñoSeleccion + MesSeleccion (los campos 'Año'/'Mes'
// del modelo estan vacios). 'MesesRollBack' es un parametro aparte del modelo.
// IMPORTANTE: la seleccion se VERIFICA despues de aplicarla (leyendo el selection object)
// -- selectValues sobre campos con 'ñ' fallo en silencio en el otro tenant.
//
// Uso:
//   node shared/qlik/rofina-extract-convenios.mjs --year 2026 --months Jan,Feb,Mar \
//        [--rollback 0] [--out salida.json]
import { writeFileSync } from "fs";
import { loadSession, openEngine } from "./rofina-session.mjs";

const argv = process.argv.slice(2);
const arg = (n, d) => {
  const i = argv.indexOf(`--${n}`);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : d;
};
const YEAR = arg("year", "2026");
const MONTHS = arg("months", "Jan,Feb,Mar").split(",").map((x) => x.trim());
const ROLLBACK = arg("rollback", "0");
const OUT = arg("out", null);

const MEASURES = [
  ["Unidades facturadas", "Sum(unidades_total)"],
  ["Convenios", "Sum(convenios)"],
  ["$ neto facturado", "Sum(neto)"],
  ["Consumo uni", "sum(if(Tipo_Cabecera='ND', -Consumo_Unidades_Inf,Consumo_Unidades_Inf))"],
  ["Consumo PVP", "sum(if(Tipo_Cabecera='ND', -Consumo_Pesos_Inf,Consumo_Pesos_Inf))"],
  ["Aporte neto", "sum(if(Tipo_Cabecera='ND', -Aporte_Neto,Aporte_Neto))"],
  ["$ netos", "sum(if(Tipo_Cabecera='ND', -impneto,impneto))"],
  ["% convenio UNI", "sum(Consumo_Unidades_Inf)/sum(unidades_total)"],
  ["% mostrador UNI", "(sum(unidades_total)-sum(Consumo_Unidades_Inf))/sum(unidades_total)"],
  ["% dto com", "(sum(neto)-sum(convenios))/sum(bruto_hipotetico)-1"],
  ["% dto conv", "sum(convenios)/sum(bruto_hipotetico)"],
  ["% dto total", "-(sum(bruto_hipotetico)-sum(neto))/sum(bruto_hipotetico)"],
];

const s = loadSession();
const { session, app } = await openEngine(s.appId, s);

async function selecciones() {
  const so = await app.createSessionObject({
    qInfo: { qType: "selections" },
    qSelectionObjectDef: {},
  });
  const l = await so.getLayout();
  const out = {};
  for (const sel of l.qSelectionObject?.qSelections || []) out[sel.qField] = sel.qSelected;
  return out;
}

// Seleccion por qElemNumber via listbox, NO por field.selectValues(): este ultimo
// falla EN SILENCIO en estos tenants (ni siquiera con campos sin 'ñ' como
// MesesRollBack -- probado: dejaba 0 selecciones sin tirar error). El listbox resuelve
// bien los campos con 'ñ' y selecciona por indice, asi que es inmune al tipo del valor
// (numerico vs texto) y al encoding.
async function seleccionar(campo, valores) {
  const lb = await app.createSessionObject({
    qInfo: { qType: "lb-sel" },
    qListObjectDef: {
      qDef: { qFieldDefs: [campo] },
      qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 200, qWidth: 1 }],
    },
  });
  const l = await lb.getLayout();
  const matrix = l.qListObject?.qDataPages?.[0]?.qMatrix || [];
  const quiero = valores.map((v) => String(v).trim().toLowerCase());
  const elems = matrix
    .filter((r) => quiero.includes(String(r[0].qText).trim().toLowerCase()))
    .map((r) => r[0].qElemNumber);
  if (elems.length !== valores.length) {
    const hay = matrix.map((r) => r[0].qText);
    throw new Error(
      `${campo}: pedi ${valores.length} valor(es) [${valores}] y encontre ${elems.length}. ` +
      `Valores disponibles: ${hay.slice(0, 30).join(", ")}`
    );
  }
  await lb.selectListObjectValues("/qListObjectDef", elems, false, false);
}

await app.clearAll();
await seleccionar("AñoSeleccion", [YEAR]);
await seleccionar("MesSeleccion", MONTHS);
await seleccionar("MesesRollBack", [ROLLBACK]);

// VERIFICAR que la seleccion quedo aplicada (no asumir)
const sel = await selecciones();
const esperado = {
  "AñoSeleccion": String(YEAR),
  "MesSeleccion": MONTHS.join(", "),
  "MesesRollBack": String(ROLLBACK),
};
// Comparar como CONJUNTO: Qlik devuelve los valores en su orden interno
// ('Mar, Feb, Jan'), no en el que se pidieron.
const comoSet = (x) =>
  String(x ?? "")
    .split(",")
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean)
    .sort()
    .join(",");
let ok = true;
for (const [k, v] of Object.entries(esperado)) {
  const got = sel[k];
  const match = comoSet(got) === comoSet(v);
  if (!match) ok = false;
  console.error(`   sel ${k.padEnd(14)} esperado=${v.padEnd(18)} real=${got ?? "(ninguna)"} ${match ? "OK" : "<<< NO COINCIDE"}`);
}
if (!ok) {
  console.error("ABORTADO: la seleccion no quedo aplicada como se pidio. No extraigo datos que no se que universo tienen.");
  await session.close();
  process.exit(2);
}

// Hypercube PLANO (qMode 'S') a nivel Laboratorio+Familia, igual que las filas de
// familia del export manual.
const obj = await app.createSessionObject({
  qInfo: { qType: "sessiontable" },
  qHyperCubeDef: {
    qDimensions: [["Laboratorio"], ["Familia"]].map((f) => ({ qDef: { qFieldDefs: f } })),
    qMeasures: MEASURES.map(([label, def]) => ({ qDef: { qLabel: label, qDef: def } })),
    qInitialDataFetch: [],
    qSuppressZero: false,
    qSuppressMissing: true,
  },
});
const lay = await obj.getLayout();
const total = lay.qHyperCube.qSize.qcy;
const W = 2 + MEASURES.length;
console.error(`   hypercube: ${total} filas x ${W} cols`);

const rows = [];
const H = 500;
for (let top = 0; top < total; top += H) {
  const pages = await obj.getHyperCubeData({
    qPath: "/qHyperCubeDef",
    qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: W }],
  });
  for (const r of pages[0].qMatrix) {
    rows.push({
      Laboratorio: r[0].qText,
      Familia: r[1].qText,
      valores: MEASURES.map(([label], i) => ({
        label,
        num: r[2 + i].qIsNull ? null : r[2 + i].qNum,
        text: r[2 + i].qText,
      })),
    });
  }
}

const payload = {
  tenant: s.tenant,
  appId: s.appId,
  objetoOriginal: "ThZZvT",
  extraidoEl: new Date().toISOString(),
  seleccion: { year: YEAR, months: MONTHS, rollback: ROLLBACK },
  seleccionVerificada: sel,
  measures: MEASURES.map(([l, d]) => ({ label: l, def: d })),
  rows,
};
const out = OUT || `rofina_convenios_${YEAR}_${MONTHS.join("-")}_rb${ROLLBACK}.json`;
writeFileSync(out, JSON.stringify(payload, null, 1));
console.error(`OK: ${rows.length} filas -> ${out}`);

await session.close();
process.exit(0);
