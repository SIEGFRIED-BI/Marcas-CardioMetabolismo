// shared/qlik/extract-recetas.mjs
// Extrae RECETAS (Cant. Recetas + Cant. Médicos) de la app "Tablero Recetas Siegfried (CUP)"
// de Qlik Cloud (tenant tableros.us) → JSON con [Mercado(sin Mix), Droga, Marca, AñoMes, recetas, medicos].
//
// Filtros CLAVE (descubiertos y validados 2026-07 contra el export manual):
//   1) Fichado = 'SI'                         -> solo recetas fichadas/auditadas (análogo a "Rofina" de Venta).
//   2) Flag_Rollback = {0}                    -> excluye datos preliminares/rollback.
//   3) Mercado (sin Mix) = if(not wildmatch(Mercado,'*MIX*'), Mercado, NULL())  -> excluye pseudo-mercados MIX.
//   Validación: ACEMUK SIE Abr-2026 = 21.325 (archivo 21.319); resto ±2-5% = revisión CloseUp (dato más fresco).
//
// Medidas: Cant. Recetas = sum(Cantidad) ; Cant. Médicos = count(distinct CodigoMedicoUnico)
//   (el médicos es distinct POR celda (mercado,droga,marca,mes) — el hypercube lo calcula correcto por fila).
//
// NOTA: el archivo del tablero está acotado a los ~72 mercados que trackea el negocio; este extractor trae
// TODOS los mercados sin-Mix y el consumidor/manifest decide cuáles usar (o filtrar). El médicos NO se puede
// sumar entre mercados (es distinct) — respetar el grano.
//
// Auth: env QLIK_API_KEY o shared/qlik/.qlik-key.txt (gitignored). Requiere: npm i (ver package.json).
// Uso: node shared/qlik/extract-recetas.mjs [salida.json]   (default: ./recetas_qlik.json)

import { auth, qix } from "@qlik/api";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "11a25fee-9c18-4028-9698-c03b29d91725"; // Tablero Recetas Siegfried (CUP)
const OUT = process.argv[2] || join(process.cwd(), "recetas_qlik.json");
const SET = "{<Flag_Rollback={0}, Fichado={'SI'}>}";
const MERCADO_SINMIX = "=if(not wildmatch(Mercado,'*MIX*'),Mercado,NULL())";

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
  // el app abre con una selección por defecto (último mes) -> limpiarla para traer todos los meses.
  // Los filtros de la receta viven en el set-analysis de las medidas (Fichado, Flag_Rollback), no en selección.
  await app.clearAll();

  const def = { qInfo: { qType: "sessiontable" }, qHyperCubeDef: {
    qDimensions: [
      { qDef: { qFieldDefs: [MERCADO_SINMIX] } },
      { qDef: { qFieldDefs: ["Droga"] } },
      { qDef: { qFieldDefs: ["Marca"] } },
      { qDef: { qFieldDefs: ["AñoMes"] } },
    ],
    qMeasures: [
      { qDef: { qDef: `sum(${SET} Cantidad)` } },
      { qDef: { qDef: `count(distinct ${SET} CodigoMedicoUnico)` } },
    ],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } };
  const obj = await app.createSessionObject(def);
  const total = (await obj.getLayout()).qHyperCube.qSize.qcy;

  const W = 6, H = 1600, out = [];
  for (let top = 0; top < total; top += H) {
    const pages = await obj.getHyperCubeData({ qPath: "/qHyperCubeDef", qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: W }] });
    for (const r of pages[0].qMatrix)
      out.push([r[0].qText, r[1].qText, r[2].qText, r[3].qText, r[4].qNum, r[5].qNum]);
    process.stderr.write(`${Math.min(top + H, total)}/${total} `);
  }
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`\nOK: ${out.length} filas -> ${OUT}\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
