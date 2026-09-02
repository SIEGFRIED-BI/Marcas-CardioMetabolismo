// shared/qlik/ddd-meses-disponibles.mjs
// Lista los valores de AñoMes que sirve HOY la app "Siegfried DDD". La ventana de Qlik
// es MOVIL, asi que antes de anexar un mes hay que ver que hay (y que no se haya caido
// la punta vieja). Barato: solo un listbox, no toca el cubo grande.
// Uso: node shared/qlik/ddd-meses-disponibles.mjs
import { readFileSync, existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import { auth, qix } from "@qlik/api";

const HERE = dirname(fileURLToPath(import.meta.url));
const TENANT = "tableros.us.qlikcloud.com";
const APP = "a3a4907d-9340-46d0-93c4-f2ce7f004ff0";   // Siegfried DDD

function apiKey() {
  if (process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f = join(HERE, ".qlik-key.txt");
  if (existsSync(f)) return readFileSync(f, "utf8").trim();
  throw new Error("falta la API key (QLIK_API_KEY o shared/qlik/.qlik-key.txt)");
}

const MES = { Ene: 1, Feb: 2, Mar: 3, Abr: 4, May: 5, Jun: 6, Jul: 7, Ago: 8, Sep: 9, Oct: 10, Nov: 11, Dic: 12 };
const k = (s) => { const [m, y] = String(s).split("-"); return (+y || 0) * 100 + (MES[m] || 0); };

auth.setDefaultHostConfig({ authType: "apikey", host: TENANT, apiKey: apiKey() });
const session = qix.openAppSession({ appId: APP });
const app = await session.getDoc();

for (const campo of ["AñoMes", "Periodo"]) {
  try {
    const lb = await app.createSessionObject({
      qInfo: { qType: "lb" },
      qListObjectDef: {
        qDef: { qFieldDefs: [campo] },
        qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 200, qWidth: 1 }],
      },
    });
    const l = await lb.getLayout();
    const vals = (l.qListObject?.qDataPages?.[0]?.qMatrix || []).map((r) => r[0].qText);
    const ord = vals.filter((v) => k(v)).sort((a, b) => k(a) - k(b));
    console.log(`\n${campo}: ${l.qListObject?.qSize?.qcy} valores`);
    if (ord.length) console.log(`  ventana: ${ord[0]} .. ${ord[ord.length - 1]}  (${ord.length} meses)`);
    console.log(`  ultimos 6: ${ord.slice(-6).join(", ") || vals.slice(0, 12).join(", ")}`);
  } catch (e) {
    console.log(`\n${campo}: no se pudo leer (${e.message})`);
  }
}
await session.close?.();
process.exit(0);
