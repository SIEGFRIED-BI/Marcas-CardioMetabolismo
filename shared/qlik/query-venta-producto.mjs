// Diagnóstico: venta_un (Rofina) por producto y AñoMes para productos que matchean un patrón.
// Uso: node shared/qlik/query-venta-producto.mjs <PATRON> [AÑO]   ej: MICOMAZOL 2026
import { auth, qix } from "@qlik/api";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "aa911794-e7fc-4002-8a3a-1a57a5751a2c";
const PAT = (process.argv[2] || "MICOMAZOL").toUpperCase();
const YEAR = process.argv[3] || "2026";
function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt"); if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta QLIK_API_KEY");
}
async function main() {
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  const app = await qix.openAppSession({ appId: APP_ID }).getDoc();
  await app.clearAll();
  const def = { qInfo: { qType: "sessiontable" }, qHyperCubeDef: {
    qDimensions: [["producto"], ["AñoMes"]].map(f => ({ qDef: { qFieldDefs: f } })),
    qMeasures: [{ qDef: { qDef: "sum({<Descripcion_Organizacion_Venta={'Rofina'}>} venta_un)" } }],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } };
  const obj = await app.createSessionObject(def);
  const total = (await obj.getLayout()).qHyperCube.qSize.qcy;
  const MES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  const byProd = {};
  for (let top = 0; top < total; top += 3000) {
    const p = await obj.getHyperCubeData({ qPath: "/qHyperCubeDef", qPages: [{ qTop: top, qLeft: 0, qHeight: 3000, qWidth: 3 }] });
    for (const r of p[0].qMatrix) {
      const prod = (r[0].qText || "").toUpperCase(), ym = r[1].qText || "", v = r[2].qNum || 0;
      if (!prod.includes(PAT) || !ym.endsWith(YEAR)) continue;
      byProd[prod] = byProd[prod] || {}; byProd[prod][ym] = (byProd[prod][ym] || 0) + v;
    }
  }
  console.log(`\n=== venta_un Rofina ${YEAR} · productos ~ "${PAT}" (por mes) ===`);
  for (const prod of Object.keys(byProd).sort()) {
    const row = MES.map(m => { const v = byProd[prod][`${m}-${YEAR}`]; return v ? `${m}:${Math.round(v)}` : null; }).filter(Boolean);
    console.log(`  ${prod}\n     ${row.join("  ")}`);
  }
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
