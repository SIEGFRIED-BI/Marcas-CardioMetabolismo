# Qlik Cloud — Discovery (F0)

_Fecha: 2026-07-02 · read-only, vía API key personal + `@qlik/api` (Engine/QIX sobre WebSocket)._

## Conexión
- **Tenant con API:** `https://tableros.us.qlikcloud.com` (región `us`).
- **Auth:** API key (Bearer JWT ES384). Funciona; usuario = Carlos Marinaro (Professional, lee tablas).
- **Gotcha:** `/api/v1/users/me` responde **301** a `/users/{id}` y en el redirect se pierde el header
  `Authorization` → usar `--location-trusted` (curl) o llamar endpoints que no redirigen.
- **Método de extracción probado:** `createSessionObject` con `qHyperCubeDef` (dims + medidas con
  set-analysis) → `getLayout`/`GetHyperCubeData` paginado. Verificado en vivo contra la app Convenios.
- **Sin acceso:** `/api/v1/automations` → **403** (la key no tiene scope de automations).

## Apps del tenant (9)
| App | Space | appId | Rol para el tablero |
|---|---|---|---|
| Siegfried Ventas | Siegfried | aa911794-e7fc-4002-8a3a-1a57a5751a2c | venta interna (Facturacion_FACT, SAP) |
| Tablero Recetas Siegfried (CUP) | Siegfried | 11a25fee-9c18-4028-9698-c03b29d91725 | recetas (Prescripciones, CloseUp) |
| Siegfried DDD | Siegfried | a3a4907d-9340-46d0-93c4-f2ce7f004ff0 | DDD por región (IMS_FACT CPC/CPA) |
| Siegfried Convenios | Siegfried | afed3174-8603-4e5c-9bad-8b77706a53bc | convenios (pero NO es la fuente real, ver abajo) |
| Dashboard Siegfried Farmacias | Siegfried QA | 029ba94f-8940-4bd5-9b53-597b25484862 | sell-out + APMs (no stock) |
| Siegfried Elvis | Siegfried | 64fa12f6-87aa-439c-aacc-01b8d1db1a14 | CRM/visitas APMs (no está en el tablero) |
| Tablero Corporativo Siegfried | Siegfried QA | aa15881f-f60c-4710-bf81-90edeceeb1a5 | agregado (Fact + DDD + IQVIA presc.) |
| Cupones Siegfried | Siegfried | 7c58708c-c477-489a-8f8f-46dec17a8f6c | cupones (no está en el tablero) |
| Primero pasos | Inicio | eca994c5-... | intro Qlik (ignorar) |

## Alcance real (clave)
El usuario exporta desde (al menos) **DOS Qliks**; solo `tableros.us` tiene API hoy.

| Fuente del tablero | Origen | ¿Automatizable ahora? |
|---|---|---|
| Venta interna | **tableros.us** (Siegfried Ventas) | ✅ SÍ |
| Recetas | **tableros.us** (Tablero Recetas CUP) | ✅ SÍ |
| DDD | **tableros.us** (Siegfried DDD) | ✅ SÍ |
| Convenios / canales | **OTRO Qlik** (sin API todavía) | 🔒 bloqueado |
| Presupuesto / Estimados | otro Qlik / marketing | 🔒 bloqueado |
| IQVIA AR_PM (mol_perf/IE/MS) | IQVIA directo | ✋ manual |
| Stock / cobertura | no está en Qlik | ✋ manual |

> **Decisión (usuario, 2026-07-02):** IQVIA AR_PM y Stock/cobertura quedan **fuera del alcance de Qlik** —
> el usuario adjunta esas "bajadas planas" a mano (como hoy). No hay app de inventario en el tenant. El
> build ya las lee del hub sin cambios.

## Hallazgo Convenios (por qué NO era buen PoC)
- Los archivos `Convenios vs mostrador` (carpeta `convenios NUEVO/`, todos 27-jun) se exportan **a mano
  desde OTRO Qlik** — la app Convenios de tableros.us **no es la fuente**.
- Sus columnas (`Unidades facturadas`, `% convenio UNI`, `% mostrador UNI`, `% dto com`) **no existen
  como medida** en ningún objeto de la app de tableros.us.
- Al extraer de tableros.us: `Consumo_Unidades_Inf` ≈ "Consumo uni" (1.995.745 vs 1.996.605, <0,05%),
  pero `Facturacion_Unidades` NO asocia a Familia (cae en fila nula "-") → no reproduce "Unidades facturadas".
- **Flag de dato:** varias pivots de Convenios rotulan `Año 2030/2031` y meses hasta Dic-2031 (etiquetas
  dinámicas o error de fechas del propio app — a verificar si algún día se usa esa app).

## Próximo (F1 · PoC)
PoC end-to-end sobre UNA de las 3 disponibles (Venta / Recetas / DDD): extraer de tableros.us →
xlsx en `_inbox/<mes>/` con la forma del archivo actual → `update-all.ps1` → `data.js` **idéntico**
(git diff vacío) al de la corrida manual + 13 gates verdes.

## Scripts de discovery (en scratchpad, no en el repo)
`qlik-node/`: `infos.mjs` (histograma de objetos), `enumall.mjs`/`inspect.mjs` (firmas de tablas),
`getprops.mjs` (definición de pivots), `masters.mjs` (medidas/dimensiones maestras),
`extract-test.mjs` (session-hypercube + GetHyperCubeData). API key en `scratchpad/qlik-key.txt` (fuera del repo).
