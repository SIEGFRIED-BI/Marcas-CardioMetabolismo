// shared/qlik/extract-ddd-mes.mjs
// Extrae UN MES del panel DDD regional (app "Siegfried DDD", Qlik Cloud tableros.us) con las
// 9 columnas del archivo manual, para AGREGARLO al DDD ya publicado:
//   [RegionCUP, Mercado, Droga, ClaseTerapeutica, AñoMes, CodClaseTerap, CodProducto, Producto, Unidades]
//
// Uso: node shared/qlik/extract-ddd-mes.mjs --mes "Jun-2026" --out <salida.json>
//
// POR QUE UN MES: el panel son 9.508.682 filas / 695.227.298 u en 24 meses. Para agregar un
// mes al DDD publicado alcanza su tajada (406.727 filas) y es estrictamente ADITIVO: los
// meses anteriores no se re-extraen, asi que no pueden moverse. Ademas la ventana de Qlik es
// movil (hoy Jul-2024..Jun-2026 contra Jun-2024..May-2026 de los tableros), asi que
// re-extraer todo PERDERIA Jun-2024.
//
// ── LO QUE HAY QUE SABER DE ESTE ENGINE (todo medido) ───────────────────────────────────
//
// 1. SE FILTRA CON toggleSelect, NO CON selectValues NI CON EXPRESIONES DE CONJUNTO.
//    - selectValues() quedo INERTE en esta app (republicada 2026-08-05 16:46 UTC): devuelve
//      true, las selecciones activas quedan en [] y el total sigue siendo el panel completo
//      (695.227.298 u). Pasa con AñoMes, con DescripcionMercado y con Periodo.
//    - toggleSelect() SI funciona: con AñoMes='Jun-2026' el total da 31.926.027 u exactos.
//    - Las expresiones de conjunto filtran, pero SOBRE-CUENTAN: el cubo se evalua sobre el
//      modelo completo y los productos combo, que estan asociados a varias Drogas, devuelven
//      el valor entero en cada fila de Droga. Medido en "Acemuk Día y Noche" (4 moleculas):
//      total real 1.870.797 u contra 6.792.581 u del cubo, 3,6x. Con SELECCION no pasa.
//    Por eso TODO filtro es por seleccion, y se VERIFICA contra un numero: una seleccion que
//    reporta exito no prueba nada.
//
// 2. HAY QUE TROCEAR. Con el mes seleccionado el cubo de 8 dimensiones reporta qcy=406.727
//    (correcto), pero paginarlo entero se agota a las 27.031 filas en 108 s: es demasiado
//    caro. Se trocea POR REGION (43 trozos de ~9.500 filas), que ademas da una invariante
//    natural: la suma de cada region tiene que dar su propio total.
//
// 3. LAS SELECCIONES TOMAN LOCK EXCLUSIVO y cancelan calculos pendientes
//    ('BeginExclusive canceled family requests' / 'Exclusive request aborted family
//    requests'). Por eso se serializa: seleccionar -> crear el cubo -> paginar -> soltar la
//    seleccion, sin nada en vuelo, y con reintentos y backoff ante un abort.
//
// 4. NO HAY QUE HACER POLLING DE qcy sin seleccion (viene a medio calcular: 406.727 / 1.089 /
//    2.900 / 1.251 / 4.173 para el mismo objeto). CON seleccion es confiable. Y crear un
//    session object cuesta 0,2 s: lo lento nunca fue crear objetos, era el polling.
//
// 5. exportData() da "Access denied" (CSV_C, CSV_T, OOXML). Seria mas simple -- el server arma
//    el archivo -- y solo necesita el permiso de export en la identidad de la API key.
//
// ── VALIDACION (G1, dentro de la extraccion) ────────────────────────────────────────────
// El total del mes y el total de cada region salen de cubos chicos que el engine resuelve de
// una. Cada region se pagina por separado y su suma tiene que dar EXACTAMENTE su total; si no,
// se reintenta, y si igual no cierra se ABORTA sin escribir. Al final la suma de las regiones
// tiene que dar el total del mes.

import { auth, qix } from "@qlik/api";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP_ID = "a3a4907d-9340-46d0-93c4-f2ce7f004ff0"; // Siegfried DDD
const MAX_CELDAS = 9000;   // Qlik corta la pagina en ~10.000 CELDAS (error 6001), no en filas

function arg(name, def) {
  const i = process.argv.indexOf(name);
  return i >= 0 && i + 1 < process.argv.length ? process.argv[i + 1] : def;
}
const MES = arg("--mes");
const OUT = arg("--out", join(process.cwd(), "ddd_mes.json"));
// Archivo de avance: la extraccion es REANUDABLE. El estado de seleccion de esta app es no
// deterministico -- la misma secuencia da resultados distintos entre corridas -- y una pasada
// completa son 42 regiones y ~20 min, asi que caerse a mitad es lo normal. En vez de pelear
// por una corrida perfecta, cada region que cierra se guarda y la corrida siguiente arranca
// donde quedo. Con dos o tres pasadas se completa el mes.
const PARCIAL = OUT.replace(/\.json$/, "") + ".parcial.json";

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("Falta la API key: definí QLIK_API_KEY o creá shared/qlik/.qlik-key.txt");
}
const espera = ms => new Promise(r => setTimeout(r, ms));
const R = v => Math.round(v || 0);

// Las 7 dimensiones que quedan al fijar la region por seleccion.
const DIMS = ["DescripcionMercado", "DescripcionDrogaIMS", "DescripcionClaseTerapeutica4IMS",
              "CodigoClaseTerapeutica4IMS", "CodigoProductoIMS", "DescripcionProductoIMS"];
const W = DIMS.length + 1;
const H = Math.max(1, Math.floor(MAX_CELDAS / W));

let app;
let seleccionada = null;   // region vigente; a nivel modulo porque conReintento la resetea al reconectar

/** Referencia INDEPENDIENTE DEL ESTADO. El identificador de conjunto `1` ignora TODAS las
 *  selecciones vigentes; sin el, la referencia hereda lo que haya quedado seleccionado de una
 *  corrida anterior (medido: la referencia del mes dio 2.598 u en vez de 31.926.027 porque
 *  seguia viva una seleccion de region de una corrida abortada). En esta app las selecciones
 *  PERSISTEN entre sesiones y clearAll() no las limpia. */
async function refEscalar(setExtra) {
  const o = await app.createSessionObject({ qInfo: { qType: "ref" }, qHyperCubeDef: {
    qDimensions: [], qMeasures: [{ qDef: { qDef: `sum({1<${setExtra}>} MensualUnidades)` } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 1, qWidth: 1 }] } });
  return (await o.getLayout()).qHyperCube.qDataPages[0].qMatrix[0][0].qNum;
}

/** Abre (o reabre) la sesion con la app. La sesion websocket de Qlik SE SUSPENDE SOLA a los
 *  pocos minutos ("Session suspended") y una extraccion de 43 regiones tarda ~20 min: medido,
 *  se corto a los 294 s con 10 regiones y 105.828 filas ya extraidas. Hay que poder reconectar
 *  sin perder lo hecho, por eso la sesion se abre por funcion y no una sola vez. */
async function abrirSesion() {
  app = await qix.openAppSession({ appId: APP_ID }).getDoc();
}

/** Reintenta ante los aborts por lock exclusivo del engine Y ante la suspension de la sesion.
 *  Si la sesion se cayo, la reabre: los objetos de sesion se pierden, pero como cada region se
 *  arma con objetos nuevos alcanza con volver a fijar la seleccion (lo hace fijarRegion). */
async function conReintento(fn, etiqueta, intentos = 6) {
  let ultimo;
  for (let i = 1; i <= intentos; i++) {
    try { return await fn(); }
    catch (e) {
      ultimo = e;
      const msg = e.message || "";
      const caida = /suspend|closed|socket|disconnect|not connected/i.test(msg);
      if (!caida && !/abort|exclusive|cancel/i.test(msg)) throw e;
      process.stderr.write(`\n   [${etiqueta}: ${msg.slice(0, 42)}, reintento ${i}]`);
      await espera(1500 * i);
      if (caida) { await abrirSesion(); seleccionada = null; }
    }
  }
  throw ultimo;
}

async function totalEscalar() {
  const o = await app.createSessionObject({ qInfo: { qType: "t" }, qHyperCubeDef: {
    qDimensions: [], qMeasures: [{ qDef: { qDef: "sum(MensualUnidades)" } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 1, qWidth: 1 }] } });
  return (await o.getLayout()).qHyperCube.qDataPages[0].qMatrix[0][0].qNum;
}

/** Un cubo de 1 dimension + total. El engine los resuelve de una y son confiables. */
async function porDimension(campo, alto = 500, setExtra = null) {
  // Con setExtra se usa {1<...>}: independiente de las selecciones vigentes (ver refEscalar).
  const medida = setExtra ? `sum({1<${setExtra}>} MensualUnidades)` : "sum(MensualUnidades)";
  const o = await app.createSessionObject({ qInfo: { qType: "d" }, qHyperCubeDef: {
    qDimensions: [{ qDef: { qFieldDefs: [campo] } }],
    qMeasures: [{ qDef: { qDef: medida } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: alto, qWidth: 2 }],
    qSuppressZero: true, qSuppressMissing: true } });
  const l = await o.getLayout();
  return ((l.qHyperCube.qDataPages[0] || {}).qMatrix || [])
    .map(r => [r[0].qText, r[1].qNum]).filter(([v, u]) => v && u > 0);
}

/** Pagina el cubo de la seleccion vigente hasta llegar a `esperado`. Reintenta las paginas
 *  vacias en vez de tomarlas como fin: una pagina puede venir vacia sin serlo. */
async function paginar(esperado) {
  const o = await app.createSessionObject({ qInfo: { qType: "p" }, qHyperCubeDef: {
    qDimensions: DIMS.map(d => ({ qDef: { qFieldDefs: [d] } })),
    qMeasures: [{ qDef: { qDef: "sum(MensualUnidades)" } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: H, qWidth: W }],
    qSuppressZero: true, qSuppressMissing: true } });
  const l = await o.getLayout();
  const filas = [...((l.qHyperCube.qDataPages[0] || {}).qMatrix || [])];
  let suma = filas.reduce((s, r) => s + (r[DIMS.length].qNum || 0), 0);
  let top = filas.length;
  const qcy = l.qHyperCube.qSize.qcy;
  while (Math.abs(R(suma) - R(esperado)) > 1) {
    let m = [];
    for (let i = 1; i <= 6 && !m.length; i++) {
      m = await conReintento(async () => {
        const p = await o.getHyperCubeData({ qPath: "/qHyperCubeDef",
          qPages: [{ qTop: top, qLeft: 0, qHeight: H, qWidth: W }] });
        return (p[0] || {}).qMatrix || [];
      }, "pagina");
      if (!m.length) await espera(1200 * i);
    }
    if (!m.length) break;                       // no hay mas, aunque no cierre
    for (const r of m) suma += (r[DIMS.length].qNum || 0);
    filas.push(...m);
    top += m.length;
  }
  return { filas, suma, qcy };
}

async function main() {
  if (!MES) throw new Error('Falta --mes "Jun-2026"');
  auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
  await abrirSesion();

  // ── cuanto TIENE que dar el mes, sin depender de ninguna seleccion ──
  // Un cubo SIN dimensiones con expresion de conjunto si filtra bien y es exacto (la
  // sobre-cuenta de las expresiones de conjunto aparece recien cuando hay dimensiones en
  // relacion muchos-a-muchos, como DescripcionDrogaIMS). Sirve de referencia independiente.
  const oEsp = await app.createSessionObject({ qInfo: { qType: "e" }, qHyperCubeDef: {
    qDimensions: [], qMeasures: [{ qDef: { qDef: `sum({1<AñoMes={'${String(MES).replace(/'/g, "''")}'}>} MensualUnidades)` } }],
    qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 1, qWidth: 1 }] } });
  const esperadoMes = (await oEsp.getLayout()).qHyperCube.qDataPages[0].qMatrix[0][0].qNum;
  if (!esperadoMes) throw new Error(`el mes ${MES} no tiene unidades; revisar la etiqueta`);
  process.stderr.write(`${MES} deberia dar ${R(esperadoMes).toLocaleString("es-AR")} u\n`);

  // ── dejar el mes SELECCIONADO, sea cual sea el estado con el que arranco la sesion ──
  // OJO: clearAll() TAMPOCO es confiable en esta app -- una corrida anterior dejo AñoMes
  // seleccionado y la sesion nueva lo heredo (el total ya venia en 31.926.027 antes de tocar
  // nada). Y toggleSelect ALTERNA: si el mes ya estaba seleccionado, togglearlo lo
  // DESELECCIONA. Por eso no se asume el estado: se mide, y solo se toca si hace falta.
  const fMes = await app.getField("AñoMes");
  let totalMes = await totalEscalar();
  if (Math.abs(R(totalMes) - R(esperadoMes)) > 1) {
    await conReintento(() => app.clearAll(true), "clearAll");
    await conReintento(() => fMes.toggleSelect(String(MES), false, 0), "seleccion mes");
    for (let i = 1; i <= 8; i++) {
      totalMes = await totalEscalar();
      if (Math.abs(R(totalMes) - R(esperadoMes)) <= 1) break;
      await espera(800 * i);
    }
  } else {
    process.stderr.write(`  (el mes ya venia seleccionado de una corrida anterior)\n`);
  }
  process.stderr.write(`seleccion ${MES}: total ${R(totalMes).toLocaleString("es-AR")} u\n`);
  if (Math.abs(R(totalMes) - R(esperadoMes)) > 1) {
    throw new Error(`LA SELECCION DEL MES NO QUEDO APLICADA: el total da ${R(totalMes)} u y ` +
                    `deberia dar ${R(esperadoMes)}. No se extrae nada.`);
  }

  // ── totales por region: la invariante de cada trozo ──
  const SETMES = `AñoMes={'${String(MES).replace(/'/g, "''")}'}`;
  // Se excluyen las regiones que el builder descarta igual (build-competidores-shape-a.py:
  // `if region in ('Totales', '-'): continue`). Ademas "-" es el bucket NULO y toggleSelect no
  // puede seleccionar un valor vacio: la corrida se corto ahi con 40 de 43 regiones ya hechas.
  const REG_FUERA = new Set(["-", "Totales"]);
  const SETSINREG = `${SETMES},RegionCUP-={'-','Totales'}`;
  const regiones = (await porDimension("RegionCUP", 200, SETMES)).filter(([r]) => !REG_FUERA.has(r));
  const sumaReg = regiones.reduce((s, r) => s + r[1], 0);
  process.stderr.write(`regiones con datos: ${regiones.length}, suman ` +
                       `${R(sumaReg).toLocaleString("es-AR")} u\n`);
  const refSinReg = await refEscalar(SETSINREG);
  if (Math.abs(R(sumaReg) - R(refSinReg)) > 1) {
    throw new Error(`las regiones suman ${R(sumaReg)} y la referencia sin el bucket nulo da ` +
                    `${R(refSinReg)}: hay unidades fuera de RegionCUP.`);
  }
  process.stderr.write(`  (se excluye el bucket nulo de region: ${R(totalMes - refSinReg).toLocaleString("es-AR")} u, ` +
                       `que el builder descarta igual)
`);

  // let, no const: el objeto de campo pertenece a la sesion; al reconectar hay que pedirlo de nuevo
  let fReg = await app.getField("RegionCUP");
  const out = [];
  // ── avance previo: se retoma lo ya extraido en corridas anteriores ──
  const yaHechas = new Map();          // region -> filas
  if (existsSync(PARCIAL)) {
    const prev = JSON.parse(readFileSync(PARCIAL, "utf8"));
    if (prev.mes === MES) {
      for (const [reg, filas] of Object.entries(prev.regiones || {})) yaHechas.set(reg, filas);
      process.stderr.write(`  retomando: ${yaHechas.size} regiones ya extraidas en corridas anteriores
`);
    }
  }
  let suma = 0, hechas = 0;
  const t0 = Date.now();

  /** Espera a que el total escalar converja a `objetivo`. Es la unica forma de saber que una
   *  seleccion quedo aplicada: en esta app ni el valor de retorno ni las selecciones activas
   *  son confiables. */
  async function esperarTotal(objetivo, etiqueta) {
    for (let i = 1; i <= 8; i++) {
      const t = await conReintento(() => totalEscalar(), `total ${etiqueta}`);
      if (Math.abs(R(t) - R(objetivo)) <= 1) return true;
      await espera(800 * i);
    }
    return false;
  }

  /** Deja seleccionada SOLO `reg`. clear() del campo NO funciona en esta app (igual que
   *  clearAll): si no se deselecciona la anterior, toggleSelect SUMA la nueva a la vigente y
   *  el total da la suma de las dos. Por eso se togglea explicitamente la anterior para
   *  sacarla, y se verifica cada transicion contra un numero. */
  /** Vuelve al estado base -- solo el mes seleccionado -- cuando la transicion de regiones se
   *  descoloca. En vez de seguir parcheando cada modo de falla del estado (toggle que no
   *  aplica, deseleccion que no vuelve, sesion suspendida) hay UNA salida generica: sesion
   *  nueva y el mes re-fijado, verificado contra el numero. Es idempotente. */
  async function resetDuro() {
    process.stderr.write(`\n   [reset: sesion nueva, clearAll y mes re-fijado]`);
    await abrirSesion();
    fReg = await app.getField("RegionCUP");
    seleccionada = null;
    for (let i = 1; i <= 6; i++) {
      // clearAll() SI funciona (verificado: deja el panel en 695.227.298 u). Una version
      // anterior de este reset solo re-toggleaba el mes, asi que si lo que estaba trabado era
      // una seleccion de REGION nunca volvia al estado base. Se limpia todo y se re-fija.
      await app.clearAll(true);
      await espera(600 * i);
      const fM = await app.getField("AñoMes");
      await fM.toggleSelect(String(MES), false, 0);
      await espera(600 * i);
      const t = await totalEscalar();
      if (Math.abs(R(t) - R(totalMes)) <= 1) return;
    }
    throw new Error(`no se pudo volver al estado base (solo ${MES} seleccionado). No se escribe nada.`);
  }

  async function fijarRegion(reg, esperado) {
    if (seleccionada && seleccionada !== reg) {
      await conReintento(() => fReg.toggleSelect(String(seleccionada), false, 0), `sacar ${seleccionada}`);
      if (!await esperarTotal(totalMes, `sin region`)) await resetDuro();
      seleccionada = null;
    }
    if (seleccionada !== reg) {
      await conReintento(() => fReg.toggleSelect(String(reg), false, 0), `sel ${reg}`);
      if (!await esperarTotal(esperado, reg)) {
        // segundo intento: estado base y volver a seleccionar
        await resetDuro();
        await conReintento(() => fReg.toggleSelect(String(reg), false, 0), `sel2 ${reg}`);
        if (!await esperarTotal(esperado, reg)) {
          throw new Error(`la seleccion de la region "${reg}" no llego a aplicarse ni tras un ` +
                          `reset (el total no converge a ${R(esperado)} u). No se escribe nada.`);
        }
      }
      seleccionada = reg;
    }
  }
  for (const [reg, esperadoReg] of regiones) {
    // Se selecciona la region y se ESPERA A QUE LA SELECCION ESTE APLICADA antes de crear el
    // cubo. Sin esto el cubo se arma mientras la seleccion todavia tiene el lock exclusivo y
    // sale calculado contra un estado a medias: medido, _CAPITAL FEDERAL daba qcy=20 filas y
    // 34.688 u en vez de 4.158.092. La unica forma de saberlo es pedir el total escalar y
    // compararlo contra el total conocido de la region.
    if (yaHechas.has(reg)) {
      for (const f of yaHechas.get(reg)) { out.push(f); suma += (f[8] || 0); }
      hechas++;
      continue;
    }
    await fijarRegion(reg, esperadoReg);
    // La suma del cubo SUPERA el total de la region, y esta BIEN: DescripcionMercado es una
    // dimension y los mercados SE SOLAPAN a proposito (jerarquia contenedor/sub-segmento;
    // 1.819 de 6.621 productos estan en mas de un mercado), asi que un producto aparece en
    // varias filas con su valor entero. Medido en _CAPITAL FEDERAL: 8.873.274 u de cubo
    // contra 4.158.092 u de la region, 2,13x. Es exactamente la estructura que ya tienen los
    // xlsx publicados -- por eso existe shared/ddd-mercados-copia.json aguas abajo.
    // Entonces la region NO se valida por suma; se pagina hasta agotar y la validacion real
    // es POR MERCADO, al final, contra los totales del censo de mercados.
    const r = await paginar(Infinity);
    for (const x of r.filas) {
      out.push([reg, x[0].qText, x[1].qText, x[2].qText, MES, x[3].qText, x[4].qText, x[5].qText, x[6].qNum]);
    }
    suma += r.suma;
    hechas++;
    // se persiste la region apenas cierra: si la app se descoloca en la siguiente, esto no se
    // pierde y la proxima corrida arranca desde aca
    const filasReg = [];
    for (const x of r.filas) {
      filasReg.push([reg, x[0].qText, x[1].qText, x[2].qText, MES, x[3].qText, x[4].qText, x[5].qText, x[6].qNum]);
    }
    yaHechas.set(reg, filasReg);
    writeFileSync(PARCIAL, JSON.stringify({ mes: MES, regiones: Object.fromEntries(yaHechas) }));
    if (hechas % 5 === 0 || hechas === regiones.length) {
      process.stderr.write(`  ${hechas}/${regiones.length} regiones | ${out.length.toLocaleString("es-AR")} filas | ` +
                           `${(suma / totalMes * 100).toFixed(1)}% | ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
    }
  }

  // ── G1: POR MERCADO, que es la invariante que vale ──
  // Se compara lo extraido contra el censo de mercados (cubo de 1 dimension, confiable). No
  // se compara la suma global contra el total del mes: los mercados se solapan y la suma
  // TIENE que ser mayor.
  // sacar la ultima region para que el censo de mercados vea el mes completo
  if (seleccionada) {
    await conReintento(() => fReg.toggleSelect(String(seleccionada), false, 0), "sacar ultima region");
    await esperarTotal(totalMes, "sin region");
    seleccionada = null;
  }
  const censoMkt = await porDimension("DescripcionMercado", 500, SETSINREG);
  // Se DEDUPLICA por (region, mercado, producto) antes de comparar. DescripcionDrogaIMS es
  // muchos-a-muchos: un combo esta asociado a cada molecula componente y el cubo devuelve el
  // valor ENTERO del producto en cada fila de droga. Medido: Grinsil, _CAPITAL FEDERAL,
  // producto 52305 -> dos filas (CLAVULANIC ACID y AMOXICILLIN) con 21.067 u IDENTICAS cada
  // una. Sumando todo daba 1.364.801 u contra 916.833 del censo; tomando una fila por
  // (region, producto) da 916.833 EXACTO.
  // Las filas duplicadas NO se sacan del archivo: el xlsx publicado tiene exactamente la misma
  // estructura (medido en ATB: 323 celdas con varias drogas, el 100% con unidades identicas,
  // p.ej. Bactrim cod 32499 con TRIMETHOPRIM y SULFAMETHOXAZOLE en 12.197 u cada una), asi que
  // reproducirla es lo que mantiene el mes nuevo consistente con los 24 anteriores.
  // OJO: eso significa que el builder DOBLE-CUENTA los combos, igual que hacia con los
  // mercados-copia. Es un defecto aparte, ya presente en lo publicado, y se reporta.
  const unicos = new Map();
  for (const f of out) unicos.set(`${f[0]} ${f[1]} ${f[6]}`, f);
  const extraido = new Map();
  for (const f of unicos.values()) extraido.set(f[1], (extraido.get(f[1]) || 0) + (f[8] || 0));
  const malos = [];
  for (const [mkt, esp] of censoMkt) {
    const got = extraido.get(mkt) || 0;
    if (Math.abs(R(got) - R(esp)) > 1) malos.push(`${mkt}: ${R(got)} != ${R(esp)}`);
  }
  const faltantes = censoMkt.filter(([m]) => !extraido.has(m)).map(([m]) => m);
  if (malos.length) {
    throw new Error(`G1 NO CIERRA en ${malos.length} de ${censoMkt.length} mercados. ` +
                    `Primeros: ${malos.slice(0, 3).join(" | ")}. No se escribe nada.`);
  }
  process.stderr.write(`G1 OK por mercado: los ${censoMkt.length} mercados cierran exacto ` +
                       `(${out.length.toLocaleString("es-AR")} filas, ${R(suma).toLocaleString("es-AR")} u; ` +
                       `la suma supera los ${R(totalMes).toLocaleString("es-AR")} u del mes porque los ` +
                       `mercados se solapan)${faltantes.length ? " | sin filas: " + faltantes.length : ""}\n`);
  writeFileSync(OUT, JSON.stringify(out));
  process.stderr.write(`OK DDD ${MES}: -> ${OUT} (${((Date.now() - t0) / 1000).toFixed(0)}s)\n`);
  process.exit(0);
}
main().catch(e => { console.error("ERROR:", e.message); process.exit(1); });
