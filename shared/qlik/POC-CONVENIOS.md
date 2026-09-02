# Convenios vs Mostrador desde el Qlik de rofina.us

Cómo se trae el trimestre de *Convenios vs mostrador* sin depender del export manual.
Validado el **2026-09-02** contra el export del 27-jun-2026.

## Por qué es distinto a los otros extractores

Los de ventas/recetas/DDD van al tenant **`tableros.us`**, que tiene API key
(`shared/qlik/.qlik-key.txt`). Éste va a **`rofina.us`**, que **no tiene API key**: se
autentica con la **cookie de sesión del navegador**, que vence sola (~1 h). Por eso
**no se puede meter en el cierre desatendido** (`update-all.ps1`): es un paso manual,
que se corre cuando cierra el trimestre.

## Renovar la sesión (lo único que hay que hacer a mano)

1. Entrar a Qlik en `rofina.us.qlikcloud.com` y abrir la app **Convenios**.
2. Abrir en otra pestaña `https://rofina.us.qlikcloud.com/api/v1/users/me`.
3. F12 → **Network** → F5 → clic derecho sobre la request `me` → **Copy as cURL (bash)**.
4. De ese bloque, copiar el valor de `-b '...'` a `cookie` y el `_csrfToken=...` a
   `csrfToken` en `shared/qlik/.rofina-session` (gitignored por `*session*`).

Si la sesión venció, cualquier script corta con *"SESION VENCIDA"*; no publica nada.

## Coordenadas

| | |
|---|---|
| tenant | `rofina.us.qlikcloud.com` |
| app | `e0521314-d5f9-4289-b170-43089e07bdd6` ("Convenios") |
| hoja | `0f01abe6-7747-45fb-afc6-0575a2e3d90f` ("Convenios vs mostrador") |
| objeto | `ThZZvT` (pivot-table, 4 dims + 12 medidas = las 16 columnas del xlsx) |

## Cómo se arma un trimestre

Los campos `Año` y `Mes` del modelo **están vacíos**: los filtros reales son
`AñoSeleccion`, `MesSeleccion` y `MesesRollBack` (valores 0/3/6/12/18/24).

`MesesRollBack = N` es *"ventana de N meses terminando en el mes seleccionado"*.
Las dos formas de pedir un trimestre son **equivalentes** (verificado celda a celda):

    Mar + rollback 3     ==     Jan,Feb,Mar + rollback 0

Los extractores corren las dos y **abortan si no coinciden**.

> **Ojo:** `field.selectValues()` **falla EN SILENCIO** en este tenant — deja 0
> selecciones sin tirar error, incluso en campos sin `ñ` como `MesesRollBack`. Hay que
> seleccionar por `qElemNumber` vía listbox (`selectListObjectValues`), que es lo que
> hace `rofina-extract-convenios.mjs`. Y **verificar la selección después de aplicarla**:
> el script lee el selection object y aborta si no quedó como se pidió.

## Uso

```bash
# 1. extraer el trimestre por las dos rutas
node shared/qlik/rofina-extract-convenios.mjs --year 2026 --months Jun --rollback 3 --out q2.json
node shared/qlik/rofina-extract-convenios.mjs --year 2026 --months Apr,May,Jun --rollback 0 --out q2_alt.json

# 2. armar el xlsx (exige que las dos rutas coincidan)
py shared/qlik/rofina-json-to-convenios-xlsx.py q2.json \
   "<hub>/convenios NUEVO/Convenios vs mostrador - <fecha> 2do trimestre 2026.xlsx" \
   --verificar-con q2_alt.json

# 3. publicar
py shared/build-canales-quarterly.py
py shared/bump-cache-busters.py
```

El nombre del xlsx **tiene que** contener `(1er|2do|3er|4to) trimestre <AAAA>` y la
frase `Convenios vs mostrador` (eso le da prioridad sobre el formato viejo `<N> trm`).

## Control de validación (2026-09-02)

Extracción de **Q1-2026** vs el export manual del 27-jun, a nivel familia:

| | |
|---|---|
| familias | **184/184** |
| medidas de SAP (facturado, convenios, $ neto, % dto) | **100 % idénticas** |
| `% convenio UNI` — la única que consume el Hub | mediana **0,084 pp**, máx **0,91 pp**, todas hacia arriba |

La diferencia residual es **maduración de CloseUp**: entre junio y hoy el consumo bruto
creció 0,12 % (llegaron reportes tarde). Los rollbacks 6/12/24 quedan descartados sin
ambigüedad (bajan a 4 %, 2 % y 1,5 % de coincidencia).

## Dos cosas del modelo que hay que tener presentes

**1. El `%` y la columna `Consumo uni` NO usan la misma cifra.**

    Consumo uni     = sum(if(Tipo_Cabecera='ND', -Consumo_Unidades_Inf, Consumo_Unidades_Inf))
    % convenio UNI  = sum(Consumo_Unidades_Inf) / sum(unidades_total)      <-- SIN restar ND

O sea, el porcentaje se calcula con el consumo **bruto** y la columna de al lado muestra
el **neto de notas de débito**. Entre el 27-jun y el 02-sep se cargaron ND en masa para
Q1-2026: `Consumo uni` cayó 15 % (3.660.374 → 3.113.053) mientras el `%` casi no se
movió. Con el consumo neto, el convenio de Q1-2026 sería **59,9 %** en vez del **70,4 %**
que se publica: **10,5 pp de diferencia**. Es una definición del tablero de rofina, no
nuestra — pero conviene saberlo antes de discutir un número de convenio.

**2. `% mostrador` es un residuo**, no una medición: `(facturado − consumo) / facturado`.
Por eso `build-canales-quarterly.py` no lo publica cuando no es interpretable
(consumo > facturado, o facturado ≤ 0). Ver el docstring de ese script.
