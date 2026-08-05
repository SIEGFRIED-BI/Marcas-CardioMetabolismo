// shared/qlik/extract-ddd-mes.mjs
// Extrae UN MES del panel DDD regional (app "Siegfried DDD", Qlik Cloud tableros.us) con las
// 9 columnas del archivo manual, para poder AGREGARLO al DDD ya publicado:
//   [RegionCUP, Mercado, Droga, ClaseTerapeutica, AñoMes, CodClaseTerap, CodProducto, Producto, Unidades]
//
// Uso: node shared/qlik/extract-ddd-mes.mjs --mes "Jun-2026" --out <salida.json>
//      [--markets <markets.json>]   (opcional; por defecto TODOS los mercados)
//
// POR QUE UN MES: el panel completo son 9.508.682 filas / 695.227.298 u en 24 meses (medido).
// Para agregar un mes al DDD publicado alcanza su tajada (~406.727 filas), es una sola corrida
// y es estrictamente ADITIVO: los meses anteriores no se re-extraen, asi que no pueden
// moverse. Ademas la ventana de Qlik es movil (hoy Jul-2024..Jun-2026 mientras los tableros
// tienen Jun-2024..May-2026), asi que re-extraer PERDERIA Jun-2024.
//
// ── LAS CUATRO COSAS QUE HAY QUE SABER DE ESTE ENGINE (todas medidas) ────────────────────
//
// 1. TOPE DURO DE 10.000 FILAS POR CUBO.
//    Paginando el cubo completo, la ventana qTop=10000 vuelve VACIA: se extraen 10.000 filas
//    (7.503.040 u de 31.926.027, el 23,5%) y despues nada. Por eso trocear NO es una
//    optimizacion, es obligatorio: cada trozo tiene que quedar debajo de 10.000 filas.
//
// 2. NO HAY QUE HACER POLLING DE qHyperCube.qSize.qcy. Viene a medio calcular: para el mismo
//    objeto de 7 dimensiones se leyo 406.727, 1.089, 2.900, 1.251 y 4.173 en corridas
//    distintas. Y peor: el polling (decenas de getLayout por objeto) es lo que hace que el
//    engine cancele las familias de requests con 'BeginExclusive canceled family requests'.
//    Crear el objeto cuesta 0,2 s -- lo lento nunca fue crear objetos, era el polling.
//    Solucion: pedir los datos en la MISMA llamada de creacion (qInitialDataFetch) y paginar
//    hasta que la suma llegue al total conocido del trozo, sin mirar qcy nunca.
//
// 3. getField(...).selectValues(...) ES INERTE EN ESTA APP.
//    Devuelve true, las selecciones activas quedan en [] y el total sigue siendo el panel
//    completo (695.227.298 u) en vez del mes (31.926.027 u). Pasa con AñoMes y con Periodo, o
//    sea no es el acento: es la app (republicada el 2026-08-05 16:46 UTC). TODO filtro va por
//    expresion de conjunto. Por eso shared/extract-ddd.mjs, que filtra por linea con
//    selectValues sobre DescripcionMercado, HOY NO ESTA FILTRANDO.
//
// 4. exportData() devuelve "Access denied" para CSV_C, CSV_T y OOXML.
//    Seria la via limpia (el server arma el archivo, sin paginar); necesita que le habiliten
//    el permiso de export a la identidad de la API key. Mientras no este, se pagina.
//
// ── COMO SE VALIDA (G1, dentro de la propia extraccion) ─────────────────────────────────
// Primero se piden los totales del mes POR MERCADO con un cubo de 1 dimension, que el engine
// resuelve de una y es confiable. Cada mercado se extrae despues por separado y su suma tiene
// que dar EXACTAMENTE ese total; si no, se reintenta, y si igual no cierra se ABORTA sin
// escribir. Un mercado que no entra en 10.000 filas se sub-trocea por region.
// OJO: la suma de los mercados SUPERA el total del mes y eso es CORRECTO -- los mercados se
// solapan a proposito (jerarquia contenedor/sub-segmento), 1.819 de 6.621 productos estan en
// mas de uno. La invariante es por mercado, nunca global.

import { auth, qix } from "@qlik/api";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "a3a4907d-9340-46d0-93c4-f2ce7f004ff0"; // Siegfried DDD
const TOPE_CUBO = 10000;   // tope duro del engine (medido)
const MAX_CELDAS = 9000;   // Qlik corta la pagina en ~10.000 CELDAS (error 6001), no en filas

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}
const MES = arg("--mes");
const OUT = arg("--out", join(process.cwd(), "ddd_mes.json"));
const MARKETS_FILE = arg("--markets");

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta la API key: definí QLIK_API_KEY o creá shared/qlik/.qlik-key.txt");
}
const esc = x => String(x).replace(/'/g, "''");
const R = v => Math.round(v || 0);

const DIMS = ["RegionCUP", "DescripcionDrogaIMS", "DescripcionClaseTerapeutica4IMS",
              "CodigoClaseTerapeutica4IMS", "CodigoProductoIMS", "DescripcionProductoIMS"];
const W = DIMS.length + 1;
const H = Math.max(1, Math.floor(MAX_CELDAS / W));

let app;

/** Crea el cubo Y pide la primera pagina en la misma llamada (sin getLayout ni polling). */
async function cubo(medida, dims) {
  const o = await app.createSessionObject({ qInfo: { qType: "x" }, qHyperCubeDef: {
    qDimensions: (dims || DIMS).map(d => ({ qDef: { qFieldDefs: [d] } })),
    qMeasures: [{ qDef: { qDef: medida } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: H, qWidth: (dims || DIMS).length + 1 }],
    qSuppressZero: true, qSuppressMissing: true } });
  const l = await o.getLayout();
  return { o, primera: (l.qHyperCube.qDataPages[0] || {}).qMatrix || [] };
}

/** Pagina un cubo hasta que la suma llegue a `esperado` o se agote. Nunca mira qcy. */
async function paginar(medida, esperado, dims) {
  const anchoM = (dims || DIMS).length;      // indice de la medida
  const { o, primera } = await cubo(medida, dims);
  const filas = [...primera];
  let suma = filas.reduce((s, r) => s + (r[anchoM].qNum || 0), 0);
  let top = filas.length;
  while (top < TOPE_CUBO && Math.abs(R(suma) - R(esperado)) > 1) {
    const p = await o.getHyperCubeData({ qPath: "/qHyperCubeDef",
      qPages: [{ qTop: top, qLeft: 0, qHeight: Math.min(H, TOPE_CUBO - top), qWidth: anchoM + 1 }] });
    const m = (p[0] || {}).qMatrix || [];
    if (!m.length) break;
    for (const r of m) suma += (r[anchoM].qNum || 0);
    filas.push(...m);
    top += m.length;
  }
  return { filas, suma, tope: top >= TOPE_CUBO };
}

async function main() {
  if (!MES) throw new Error('Falta --mes "Jun-2026"');
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  app = await qix.openAppSession({ appId: APP_ID }).getDoc();
  await app.clearAll();
  const setMes = `AñoMes={'${esc(MES)}'}`;

  // ── total del mes y totales por mercado: cubos chicos, resueltos de una ──
  const ctl = await app.createSessionObject({ qInfo: { qType: "c" }, qHyperCubeDef: {
    qDimensions: [], qMeasures: [{ qDef: { qDef: `sum({<${setMes}>} MensualUnidades)` } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 1, qWidth: 1 }] } });
  const totalMes = (await ctl.getLayout()).qHyperCube.qDataPages[0].qMatrix[0][0].qNum;
  process.stderr.write(`total ${MES}: ${R(totalMes).toLocaleString("es-AR")} u\n`);
  if (!totalMes) throw new Error(`el mes ${MES} no tiene unidades; revisar la etiqueta`);

  const om = await app.createSessionObject({ qInfo: { qType: "m" }, qHyperCubeDef: {
    qDimensions: [{ qDef: { qFieldDefs: ["DescripcionMercado"] } }],
    qMeasures: [{ qDef: { qDef: `sum({<${setMes}>} MensualUnidades)` } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 500, qWidth: 2 }],
    qSuppressZero: true, qSuppressMissing: true } });
  const mercados = ((await om.getLayout()).qHyperCube.qDataPages[0].qMatrix || [])
    .map(r => [r[0].qText, r[1].qNum]).filter(([m, u]) => m && m !== "-" && u > 0);
  mercados.sort((a, b) => b[1] - a[1]);
  process.stderr.write(`mercados con datos: ${mercados.length}\n`);

  let filtro = null;
  if (MARKETS_FILE && existsSync(MARKETS_FILE)) {
    filtro = new Set(JSON.parse(readFileSync(MARKETS_FILE, "utf8")).map(String));
    process.stderr.write(`filtrando a ${filtro.size} mercados del archivo\n`);
  }

  const out = [];
  let suma = 0, hechos = 0, subtroceados = 0;
  const t0 = Date.now();
  for (const [mkt, esperadoMkt] of mercados) {
    if (filtro && !filtro.has(mkt)) continue;
    const medMkt = `sum({<${setMes},DescripcionMercado={'${esc(mkt)}'}>} MensualUnidades)`;
    let r = await paginar(medMkt, esperadoMkt);

    // ── el mercado no entro en el tope: se sub-trocea por region ──
    if (Math.abs(R(r.suma) - R(esperadoMkt)) > 1) {
      const or = await app.createSessionObject({ qInfo: { qType: "r" }, qHyperCubeDef: {
        qDimensions: [{ qDef: { qFieldDefs: ["RegionCUP"] } }],
        qMeasures: [{ qDef: { qDef: medMkt } }],
        qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 200, qWidth: 2 }],
        qSuppressZero: true, qSuppressMissing: true } });
      const regs = ((await or.getLayout()).qHyperCube.qDataPages[0].qMatrix || [])
        .map(x => [x[0].qText, x[1].qNum]).filter(([g, u]) => g && u > 0);
      const dimsR = DIMS.filter(d => d !== "RegionCUP");
      const acc = [];
      let sumR = 0;
      for (const [reg, espReg] of regs) {
        const medR = `sum({<${setMes},DescripcionMercado={'${esc(mkt)}'},RegionCUP={'${esc(reg)}'}>} MensualUnidades)`;
        const rr = await paginar(medR, espReg, dimsR);
        if (Math.abs(R(rr.suma) - R(espReg)) > 1) {
          throw new Error(`G1 NO CIERRA en "${mkt}" / region "${reg}": ${R(rr.suma)} u contra ` +
                          `${R(espReg)} u esperadas${rr.tope ? " (llego al tope de 10.000 filas)" : ""}. No se escribe nada.`);
        }
        // se re-inserta la region, que salio de las dimensiones de este sub-cubo
        for (const x of rr.filas) acc.push({ reg, cols: x });
        sumR += rr.suma;
      }
      if (Math.abs(R(sumR) - R(esperadoMkt)) > 1) {
        throw new Error(`G1 NO CIERRA en "${mkt}" tras sub-trocear por region: ${R(sumR)} contra ${R(esperadoMkt)}.`);
      }
      for (const { reg, cols } of acc) {
        out.push([reg, mkt, cols[0].qText, cols[1].qText, MES, cols[2].qText, cols[3].qText, cols[4].qText, cols[5].qNum]);
      }
      suma += sumR;
      subtroceados++;
    } else {
      for (const x of r.filas) {
        out.push([x[0].qText, mkt, x[1].qText, x[2].qText, MES, x[3].qText, x[4].qText, x[5].qText, x[6].qNum]);
      }
      suma += r.suma;
    }
    hechos++;
    if (hechos % 20 === 0) {
      process.stderr.write(`  ${hechos} mercados | ${out.length.toLocaleString("es-AR")} filas | ` +
                           `${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
    }
  }

  process.stderr.write(`G1 OK por mercado en los ${hechos} mercados (${subtroceados} sub-troceados por region): ` +
                       `${out.length.toLocaleString("es-AR")} filas, ${R(suma).toLocaleString("es-AR")} u ` +
                       `(el total del mes es ${R(totalMes).toLocaleString("es-AR")} u; la suma es mayor ` +
                       `porque los mercados se solapan)\n`);
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`OK DDD ${MES}: ${out.length} filas -> ${OUT} (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
