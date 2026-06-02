# 📁 docs/ — Mapa único del proyecto Marcas-CardioMetabolismo

Esta carpeta es el **mapa que conecta todo**: cómo se relacionan las fuentes, los
scripts, los datos y los tableros; cómo actualizar cada mes; y cómo verificar que
los datos están bien.

> **Regla de oro:** esta carpeta **solo documenta**. No cambia el comportamiento
> del proyecto. Ningún archivo de `docs/` es leído por los tableros ni por los
> scripts — es para humanos.

---

## Por dónde empezar

| Si querés… | Abrí |
|---|---|
| **Ver todo de un vistazo (visual, clickeable)** | **`00-MAPA.html`** ← doble-click, abre en el browser |
| Entender cómo se conecta todo | `01-arquitectura.md` |
| Actualizar un mes nuevo (paso a paso) | `02-actualizar.md` |
| Chequear que un número está bien | `03-verificar.md` |
| Saber qué es una variable / clave de datos | `04-diccionario.md` |
| Encontrar el script que hace X (los 97) | `05-scripts.md` |
| Prolijear el proyecto a futuro (opcional) | `06-reorganizacion.md` |
| **Errores que ya pasaron y NO repetir (+ guardrails)** | **`07-lecciones-y-errores.md`** |

---

## Las 3 cosas que más se preguntan

1. **"¿De dónde sale este número?"** → `01-arquitectura.md` (la cadena
   fuente→script→dato→tablero) + `04-diccionario.md` (qué clave lo guarda).

2. **"Llegó el IQVIA del mes, ¿qué corro?"** → `02-actualizar.md` (el TL;DR de arriba).

3. **"¿Está bien lo que cargué?"** → `03-verificar.md` → `py shared/audit-full.py`
   (debe dar `FAIL: 0`).

---

## Recordatorios clave (también en `../CLAUDE.md`)

- Los `data.js` / `const D` y los `kpis*.json` son **derivados**: se regeneran con
  scripts, no se editan a mano.
- Las fuentes Excel viven en OneDrive: `…\Documentos\Hub-Marcas-Inputs\`, **no** en el repo.
- "Estimado de Ventas" (no "Presupuesto"). "Venta Interna" ≠ "Mercado IQVIA" ≠ "Recetas".
- **IE** = crecimiento relativo al mercado: `(SIE_curr/SIE_prev)/(Mkt_curr/Mkt_prev)×100`.
- El pre-commit hook corre syntax + history + audit. Nunca `--no-verify`.

---

_Generado como documentación de referencia. Si algo del proyecto cambia y este doc
queda viejo, actualizá el `.md` correspondiente — son archivos comunes de texto._
