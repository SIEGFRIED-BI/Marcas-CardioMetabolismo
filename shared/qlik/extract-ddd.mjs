// shared/qlik/extract-ddd.mjs
// Extrae DDD regional (Producto-Molécula-ATC-provincia) de la app "Siegfried DDD"
// (Qlik Cloud, tenant tableros.us) -> JSON con las 9 columnas del archivo manual:
//   [RegionCUP, Mercado, Droga, ClaseTerapeutica, AñoMes, CodClaseTerap, CodProducto, Producto, Unidades]
//
// Volumen: el panel completo es ~7-8M filas (paginar todo es inviable). Por eso se
// FILTRA por linea: se seleccionan los mercados de la linea (DescripcionMercado) y se
// pagina solo esa tajada (~774k/linea, ~850 paginas, ~5 min).
//
// Mapeo de campos (validado POC-DDD.md 2026-07-02):
//   RegionCUP, DescripcionMercado, DescripcionDrogaIMS, DescripcionClaseTerapeutica4IMS,
//   AñoMes, CodigoClaseTerapeutica4IMS, CodigoProductoIMS, DescripcionProductoIMS,
//   medida = sum(MensualUnidades). clearAll() antes (el app abre con mes por defecto).
//   Sin filtro oculto (el build filtra a mercados SIE por molecula/ATC despues).
//
// Auth: env QLIK_API_KEY o shared/qlik/.qlik-key.txt (gitignored).
// Uso: node shared/qlik/extract-ddd.mjs --markets <markets.json> --out <salida.json>
//      (markets.json = array de DescripcionMercado de la linea)

import { auth, qix } from "@qlik/api";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "a3a4907d-9340-46d0-93c4-f2ce7f004ff0"; // Siegfried DDD

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}
const MARKETS_FILE = arg("--markets");
const OUT = arg("--out", join(process.cwd(), "ddd_qlik.json"));

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta la API key: definí QLIK_API_KEY o creá shared/qlik/.qlik-key.txt");
}

async function main() {
  if (!MARKETS_FILE || !existsSync(MARKETS_FILE)) throw new Error("Falta --markets <markets.json>");
  const markets = JSON.parse(readFileSync(MARKETS_FILE, "utf8"));
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  const session = qix.openAppSession({ appId: APP_ID });
  const app = await session.getDoc();
  await app.clearAll();

  // Seleccionar los mercados de la linea (filtra el modelo -> el cubo baja de ~8M a ~774k).
  const fld = await app.getField("DescripcionMercado");
  await fld.selectValues(markets.map(m => ({ qText: String(m) })), false, false);
  process.stderr.write(`mercados seleccionados: ${markets.length}\n`);

  const def = { qInfo: { qType: "sessiontable" }, qHyperCubeDef: {
    qDimensions: [
      { qDef: { qFieldDefs: ["RegionCUP"] } },
      { qDef: { qFieldDefs: ["DescripcionMercado"] } },
      { qDef: { qFieldDefs: ["DescripcionDrogaIMS"] } },
      { qDef: { qFieldDefs: ["DescripcionClaseTerapeutica4IMS"] } },
      { qDef: { qFieldDefs: ["AñoMes"] } },
      { qDef: { qFieldDefs: ["CodigoClaseTerapeutica4IMS"] } },
      { qDef: { qFieldDefs: ["CodigoProductoIMS"] } },
      { qDef: { qFieldDefs: ["DescripcionProductoIMS"] } },
    ],
    qMeasures: [ { qDef: { qDef: "sum(MensualUnidades)" } } ],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } };
  const obj = await app.createSessionObject(def);
  const total = (await obj.getLayout()).qHyperCube.qSize.qcy;
  process.stderr.write(`filas del cubo (linea): ${total}\n`);

  const W = 9, H = 1000, out = [];
  for (let top = 0; top < total; top += H) {
    const pages = await obj.getHyperCubeData({ qPath: "/qHyperCubeDef", qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: W }] });
    for (const r of pages[0].qMatrix)
      out.push([r[0].qText, r[1].qText, r[2].qText, r[3].qText, r[4].qText, r[5].qText, r[6].qText, r[7].qText, r[8].qNum]);
    if (top % 50000 === 0 || top + H >= total) process.stderr.write(`${Math.min(top + H, total)}/${total} `);
  }
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`\nOK DDD: ${out.length} filas -> ${OUT}\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
