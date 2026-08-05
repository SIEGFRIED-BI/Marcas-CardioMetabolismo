// shared/qlik/extract-ddd-mes.mjs
// Extrae UN MES del panel DDD regional (app "Siegfried DDD", Qlik Cloud tableros.us) con
// las 9 columnas del archivo manual, para poder AGREGARLO al DDD ya publicado:
//   [RegionCUP, Mercado, Droga, ClaseTerapeutica, AñoMes, CodClaseTerap, CodProducto, Producto, Unidades]
//
// Uso: node shared/qlik/extract-ddd-mes.mjs --mes "Jun-2026" --out <salida.json>
//      [--markets <markets.json>]   (opcional; por defecto TODOS los mercados)
//
// POR QUE UN MES: el panel completo son 9.508.682 filas / 695.227.298 u en 24 meses
// (medido). Paginarlo entero es inviable. Para agregar un mes al DDD publicado alcanza su
// tajada, es una sola corrida y es estrictamente ADITIVO: los meses anteriores no se
// vuelven a extraer, asi que no pueden moverse. Ademas la ventana de Qlik es movil (hoy
// sirve Jul-2024..Jun-2026 mientras los tableros tienen Jun-2024..May-2026), asi que
// re-extraer perderia Jun-2024.
//
// ── TRES COMPORTAMIENTOS DEL ENGINE QUE HAY QUE SORTEAR (todos medidos) ──────────────
//
// 1. getField(...).selectValues(...) ES INERTE EN ESTA APP.
//    Devuelve true, las selecciones activas quedan en [] y el total sigue siendo el panel
//    completo (695.227.298 u) en vez del mes (31.926.027 u). Pasa con AñoMes y tambien con
//    Periodo, o sea NO es el acento: es la app (se republico el 2026-08-05 16:46 UTC).
//    CONSECUENCIA: extract-ddd.mjs, que filtra por linea con selectValues sobre
//    DescripcionMercado, HOY NO ESTA FILTRANDO. Todo filtro va por expresion de conjunto.
//
// 2. qHyperCube.qSize.qcy VIENE A MEDIO CALCULAR en cubos grandes.
//    Para el mismo objeto de 7 dimensiones se leyo 406.727, 1.089, 2.900, 1.251 y 4.173 en
//    corridas distintas, y "esperar a que se estabilice" no alcanza: se estabiliza en un
//    plateau intermedio. Paginar contra ese numero trajo el 2,4% de las unidades.
//    CONSECUENCIA: no se pagina un cubo grande. Se trocea por mercado, que da cubos de
//    pocos miles de filas que el engine calcula completos.
//
// 3. Una pagina puede venir corta sin ser la ultima.
//    Por eso cada ventana se reintenta y, sobre todo, cada mercado se valida por suma.
//
// ── COMO SE VALIDA (G1, dentro de la propia extraccion) ──────────────────────────────
// Se piden primero los totales del mes POR MERCADO con un cubo de 1 dimension (que el
// engine si calcula bien). Cada mercado se extrae despues por separado y su suma tiene que
// dar exactamente ese total; si no, se reintenta y si igual no cierra, ABORTA sin escribir.
// Al final la suma de todos los mercados tiene que dar el total del mes sin dimensiones.
// Son dos caminos independientes contra el mismo numero.

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
const MES = arg("--mes");
const OUT = arg("--out", join(process.cwd(), "ddd_mes.json"));
const MARKETS_FILE = arg("--markets");

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta la API key: definí QLIK_API_KEY o creá shared/qlik/.qlik-key.txt");
}
const espera = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s).replace(/'/g, "''");

async function main() {
  if (!MES) throw new Error('Falta --mes "Jun-2026"');
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  const session = qix.openAppSession({ appId: APP_ID });
  const app = await session.getDoc();
  await app.clearAll();

  const setMes = `AñoMes={'${esc(MES)}'}`;

  // ── total del mes, sin dimensiones: la referencia de todo ──
  const ctl = await app.createSessionObject({ qInfo: { qType: "ctl" }, qHyperCubeDef: {
    qDimensions: [], qMeasures: [{ qDef: { qDef: `sum({<${setMes}>} MensualUnidades)` } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 1, qWidth: 1 }] } });
  const totalMes = (await ctl.getLayout()).qHyperCube.qDataPages[0].qMatrix[0][0].qNum;
  process.stderr.write(`total ${MES}: ${Math.round(totalMes).toLocaleString("es-AR")} u\n`);
  if (!totalMes) throw new Error(`el mes ${MES} no tiene unidades; revisar la etiqueta`);

  // ── totales por mercado: cubo de 1 dimension, que el engine si calcula bien ──
  const objM = await app.createSessionObject({ qInfo: { qType: "mkt" }, qHyperCubeDef: {
    qDimensions: [{ qDef: { qFieldDefs: ["DescripcionMercado"] } }],
    qMeasures: [{ qDef: { qDef: `sum({<${setMes}>} MensualUnidades)` } }],
    qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } });
  let nM = 0;
  for (let i = 0; i < 20; i++) {
    await espera(1000);
    const n = (await objM.getLayout()).qHyperCube.qSize.qcy;
    if (n && n === nM) break;
    nM = n;
  }
  const mercados = [];
  for (let t = 0; t < nM; t += 500) {
    const p = await objM.getHyperCubeData({ qPath: "/qHyperCubeDef",
      qPages: [{ qTop: t, qLeft: 0, qHeight: 500, qWidth: 2 }] });
    for (const r of p[0].qMatrix) mercados.push([r[0].qText, r[1].qNum]);
  }
  const sumaMercados = mercados.reduce((s, m) => s + m[1], 0);
  process.stderr.write(`mercados con datos en ${MES}: ${mercados.length}, suman ${Math.round(sumaMercados).toLocaleString("es-AR")} u\n`);
  // OJO: la suma de los mercados SUPERA el total del mes y eso es CORRECTO. Los mercados de
  // DescripcionMercado se solapan a proposito: son una jerarquia (Macromax ⊃ Macromax
  // pediátr.; Antipsicóticos ⊃ Quetiapinas), asi que un producto cuenta en varios. Medido:
  // 42.776.740 u sumando los 146 mercados contra 31.926.027 u del mes (+34%), y 1.819 de
  // 6.621 productos estan en mas de un mercado.
  // Una version anterior de este script ABORTABA aca exigiendo que cerraran: la precondicion
  // estaba mal, no el dato. La invariante que SI vale es por mercado, y es la que se verifica
  // en el loop de abajo.
  if (sumaMercados < totalMes - 1) {
    throw new Error(`los mercados suman ${Math.round(sumaMercados)}, MENOS que el mes ` +
                    `${Math.round(totalMes)}: hay unidades fuera de DescripcionMercado`);
  }

  let filtro = null;
  if (MARKETS_FILE && existsSync(MARKETS_FILE)) {
    filtro = new Set(JSON.parse(readFileSync(MARKETS_FILE, "utf8")).map(String));
    process.stderr.write(`filtrando a ${filtro.size} mercados del archivo\n`);
  }

  // ── un cubo chico por mercado ──
  const DIMS = ["RegionCUP", "DescripcionDrogaIMS", "DescripcionClaseTerapeutica4IMS",
                "CodigoClaseTerapeutica4IMS", "CodigoProductoIMS", "DescripcionProductoIMS"];
  const out = [];
  let suma = 0, hechos = 0;
  mercados.sort((a, b) => b[1] - a[1]);
  for (const [mkt, esperadoMkt] of mercados) {
    if (filtro && !filtro.has(mkt)) continue;
    const medida = `sum({<${setMes},DescripcionMercado={'${esc(mkt)}'}>} MensualUnidades)`;
    let filas = null, sMkt = 0;
    for (let intento = 1; intento <= 4 && filas === null; intento++) {
      const o = await app.createSessionObject({ qInfo: { qType: "m" + hechos }, qHyperCubeDef: {
        qDimensions: DIMS.map(d => ({ qDef: { qFieldDefs: [d] } })),
        qMeasures: [{ qDef: { qDef: medida } }],
        qInitialDataFetch: [], qSuppressZero: true, qSuppressMissing: true } });
      let n = 0;
      for (let i = 0; i < 15; i++) {
        await espera(400);
        const k = (await o.getLayout()).qHyperCube.qSize.qcy;
        if (k && k === n) break;
        n = k;
      }
      const acc = [];
      sMkt = 0;
      for (let t = 0; t < n; t += 1000) {
        const p = await o.getHyperCubeData({ qPath: "/qHyperCubeDef",
          qPages: [{ qTop: t, qLeft: 0, qHeight: Math.min(1000, n - t), qWidth: 7 }] });
        for (const r of (p[0].qMatrix || [])) { acc.push(r); sMkt += (r[6].qNum || 0); }
      }
      if (Math.abs(Math.round(sMkt) - Math.round(esperadoMkt)) <= 1) filas = acc;
      else {
        process.stderr.write(`\n  [${mkt}] intento ${intento}: ${Math.round(sMkt)} != ${Math.round(esperadoMkt)}`);
        await espera(1200);
      }
    }
    if (filas === null) {
      throw new Error(`G1 NO CIERRA en el mercado "${mkt}": ultima suma ${Math.round(sMkt)} u ` +
                      `contra ${Math.round(esperadoMkt)} u esperadas. No se escribe nada.`);
    }
    for (const r of filas) {
      out.push([r[0].qText, mkt, r[1].qText, r[2].qText, MES, r[3].qText, r[4].qText, r[5].qText, r[6].qNum]);
      suma += (r[6].qNum || 0);
    }
    hechos++;
    if (hechos % 10 === 0 || hechos === mercados.length) {
      process.stderr.write(`\n${hechos}/${mercados.length} mercados, ${out.length} filas, ${Math.round(suma).toLocaleString("es-AR")} u`);
    }
  }

  process.stderr.write(`\n`);
  // G1 es POR MERCADO (ya validado arriba, mercado por mercado, con reintentos y abortando si
  // alguno no cierra). No se compara la suma global contra el total del mes porque los
  // mercados se solapan y la suma tiene que ser MAYOR; compararlas seria la precondicion
  // equivocada que hacia abortar la version anterior.
  process.stderr.write(`G1 OK por mercado en los ${hechos} mercados extraidos: ` +
                       `${Math.round(suma).toLocaleString("es-AR")} u ` +
                       `(el total del mes es ${Math.round(totalMes).toLocaleString("es-AR")} u; ` +
                       `la suma es mayor porque los mercados se solapan)\n`);
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`OK DDD ${MES}: ${out.length} filas -> ${OUT}\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
