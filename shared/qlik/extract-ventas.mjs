// shared/qlik/extract-ventas.mjs
// Extrae VENTA INTERNA (unidades) de la app "Siegfried Ventas" de Qlik Cloud (tenant tableros.us)
// y escribe un JSON con filas [gran_familia, familia, producto, CodigoProducto, AñoMes, venta_un].
//
// Filtro CLAVE (selección oculta del export manual, descubierta y verificada 2026-07):
//   Descripcion_Organizacion_Venta = 'Rofina'  -> canal doméstico; excluye Roemmers + exportaciones.
//   Con este filtro reproduce la Planilla de Ventas manual EXACTO (924/924 celdas de meses cerrados).
//
// Medida: sum(venta_un) (idéntica a venta_un_conv / venta_un_conv2 en este dato).
// Grano: gran_familia + familia + producto(SKU) + CodigoProducto, por AñoMes (formato "Jun-2025").
//
// Auth: API key (read) en env QLIK_API_KEY, o en shared/qlik/.qlik-key.txt (gitignored).
// Requiere: npm i @qlik/api  (node 22+ trae WebSocket nativo).
// Uso: node shared/qlik/extract-ventas.mjs [salida.json]   (default: ./ventas_qlik.json)
//
// Paso siguiente: qlik-ventas-to-planilla.py convierte este JSON en el xlsx que consume
// merge-ventas-internas.py. Ver shared/qlik/POC-VENTAS.md.

import { auth, qix } from "@qlik/api";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "aa911794-e7fc-4002-8a3a-1a57a5751a2c"; // Siegfried Ventas
const ORG_FILTER = "Rofina";                            // Descripcion_Organizacion_Venta
const OUT = process.argv[2] || join(process.cwd(), "ventas_qlik.json");

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta la API key: definí QLIK_API_KEY o creá shared/qlik/.qlik-key.txt");
}

async function main() {
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  const session = qix.openAppSession({ appId: APP_ID });
  const app = await session.getDoc();

  // selección: organización doméstica (Rofina). El filtro por año NO se hace acá (el
  // selectValues sobre el campo "Año" no matchea por la ñ); la ventana temporal la aplica
  // qlik-ventas-to-planilla.py (los labels de AñoMes son ASCII). Extraemos todo Rofina.
  const of = await app.getField("Descripcion_Organizacion_Venta");
  await of.selectValues({ qFieldValues: [{ qText: ORG_FILTER }], qToggleMode: false, qSoftLock: false });

  const def = { qInfo: { qType: "sessiontable" }, qHyperCubeDef: {
    qDimensions: [["gran_familia"], ["familia"], ["producto"], ["CodigoProducto"], ["AñoMes"]]
      .map(f => ({ qDef: { qFieldDefs: f } })),
    qMeasures: [{ qDef: { qDef: "sum(venta_un)" } }],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } };
  const obj = await app.createSessionObject(def);
  const total = (await obj.getLayout()).qHyperCube.qSize.qcy;

  const W = 6, H = 1600, out = [];
  for (let top = 0; top < total; top += H) {
    const pages = await obj.getHyperCubeData({ qPath: "/qHyperCubeDef", qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: W }] });
    for (const r of pages[0].qMatrix)
      out.push([r[0].qText, r[1].qText, r[2].qText, r[3].qText, r[4].qText, r[5].qNum]);
    process.stderr.write(`${Math.min(top + H, total)}/${total} `);
  }
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`\nOK: ${out.length} filas -> ${OUT}\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
