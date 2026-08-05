import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
const HERE = dirname(fileURLToPath(import.meta.url));
function apiKey(){ if(process.env.QLIK_API_KEY) return process.env.QLIK_API_KEY.trim();
  const f=join(HERE,".qlik-key.txt"); if(existsSync(f)) return readFileSync(f,"utf8").trim();
  throw new Error("no key"); }
const H = { Authorization: "Bearer " + apiKey(), "Content-Type": "application/json" };
const BASE = "https://tableros.us.qlikcloud.com/api/v1";
const APP = "a3a4907d-9340-46d0-93c4-f2ce7f004ff0";
async function get(p){ const r = await fetch(BASE+p, { headers: H });
  if(!r.ok) return { _status: r.status, _txt: (await r.text()).slice(0,200) };
  return r.json(); }
const app = await get(`/apps/${APP}`);
const a = app.attributes || app;
console.log("app: " + (a.name || "?"));
console.log("  lastReloadTime : " + (a.lastReloadTime || "?"));
console.log("  modifiedDate   : " + (a.modifiedDate || "?"));
console.log("  publishTime    : " + (a.publishTime || "-"));
const rl = await get(`/reloads?appId=${APP}&limit=6`);
const items = rl.data || [];
console.log("\nultimos reloads (" + items.length + "):");
for (const r of items) {
  console.log("  " + String(r.status).padEnd(10) + " inicio " + (r.startTime||"-") + "  fin " + (r.endTime||"EN CURSO") + "  tipo " + (r.type||"-"));
}
const enCurso = items.filter(r => ["QUEUED","RELOADING","IN_PROGRESS"].includes(String(r.status).toUpperCase()));
console.log("\nRELOAD EN CURSO: " + (enCurso.length ? "SI -> " + enCurso.map(r=>r.status).join(",") : "no"));
console.log("hora local ahora: " + new Date().toISOString());
process.exit(0);
