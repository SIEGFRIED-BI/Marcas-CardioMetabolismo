// Diagnostico: ¿bajo que Organizacion_Venta esta la venta de ATB que Qlik-Rofina no cuenta?
// Selecciona un mes (default Abr-2025) SIN filtro de organizacion y agrupa venta_un por
// [Descripcion_Organizacion_Venta, producto]; imprime el desglose por org para las marcas ATB.
// Uso: node shared/qlik/query-venta-org.mjs [AñoMes]   (default 'Abr-2025')
import { auth, qix } from "@qlik/api";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "aa911794-e7fc-4002-8a3a-1a57a5751a2c";
const MONTH = process.argv[2] || "Abr-2025";
const BRANDS = ["MACROMAX", "BACTRIM", "CEFALEXINA", "ACANTEX"];

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta QLIK_API_KEY");
}

async function main() {
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  const session = qix.openAppSession({ appId: APP_ID });
  const app = await session.getDoc();
  await app.clearAll();

  // Filtro de mes via SET ANALYSIS en la medida (mas robusto que selectValues con la ñ).
  const def = { qInfo: { qType: "sessiontable" }, qHyperCubeDef: {
    qDimensions: [["Descripcion_Organizacion_Venta"], ["producto"]].map(f => ({ qDef: { qFieldDefs: f } })),
    qMeasures: [{ qDef: { qDef: `sum({<AñoMes={'${MONTH}'}>} venta_un)` } }],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } };
  const obj = await app.createSessionObject(def);
  const total = (await obj.getLayout()).qHyperCube.qSize.qcy;

  const byOrgBrand = {}; // org -> brand -> sum
  const orgTotals = {};
  const H = 2000;
  for (let top = 0; top < total; top += H) {
    const pages = await obj.getHyperCubeData({ qPath: "/qHyperCubeDef", qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: 3 }] });
    for (const r of pages[0].qMatrix) {
      const org = r[0].qText, prod = (r[1].qText || "").toUpperCase(), v = r[2].qNum || 0;
      for (const b of BRANDS) {
        if (prod.includes(b) && !(b === "BACTRIM" && prod.includes("FORTE"))) {
          byOrgBrand[org] = byOrgBrand[org] || {};
          byOrgBrand[org][b] = (byOrgBrand[org][b] || 0) + v;
          orgTotals[org] = (orgTotals[org] || 0) + v;
        }
      }
    }
  }
  console.log(`\n=== venta_un ${MONTH} por Organizacion (marcas ATB: ${BRANDS.join(", ")}) ===`);
  for (const org of Object.keys(orgTotals).sort((a, b) => orgTotals[b] - orgTotals[a])) {
    console.log(`\nORG: ${org}  (total ATB = ${Math.round(orgTotals[org]).toLocaleString()})`);
    for (const b of BRANDS) if (byOrgBrand[org][b]) console.log(`    ${b}: ${Math.round(byOrgBrand[org][b]).toLocaleString()}`);
  }
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
