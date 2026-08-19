#!/bin/sh
# Pre-commit hook: run syntax check + audit before allowing commit.
# Si alguna falla, bloquea el commit.

# Check 0: cache-busters. Si se tocaron data.js / assets compartidos / paginas,
# re-genera el ?v=<hash> y re-stagea las paginas afectadas. Asi NUNCA se sirve
# una version vieja cacheada por olvidarse de bumpear ?v.
#
# OJO: aca habia una lista HARDCODEADA de paginas a re-stagear que NO incluia las 7
# */DDD/competidores.html (ni dermatologia/competidores.html). Resultado: al actualizar el
# DDD, el bump les cambiaba el ?v= pero el cambio quedaba SIN STAGEAR, y el commit subia el
# competidores-data.js nuevo con el HTML apuntando al hash viejo. El navegador servia el
# cacheado: dato nuevo publicado, mes viejo en pantalla, y ningun gate lo veia porque no
# mueve ninguna suma. Detectado el 2026-08-05 al actualizar a Jun-2026.
# Por eso ya no hay lista: se re-stagea CUALQUIER html cuyo unico cambio sea el ?v=, que es
# exactamente lo que bump-cache-busters puede tocar. Si un html tiene ademas cambios de
# contenido sin stagear, se lo deja como esta (no es de este hook decidir por el usuario).
if git diff --cached --name-only | grep -qE '(data\.js|shared/.*\.(js|css)|index\.html|dermato_dashboard\.html|kpis\.html)$'; then
    echo "Bumping cache-busters (?v=hash)..."
    py shared/bump-cache-busters.py
    for f in $(git diff --name-only -- '*.html'); do
        # lineas de cambio real (sin cabeceras del diff) que NO son un ?v=<hash>
        otras=$(git diff -U0 -- "$f" | grep -E '^[-+][^-+]' | grep -cv '?v=[0-9a-f]\{6,\}')
        if [ "$otras" -eq 0 ]; then
            git add "$f"
            echo "  re-stageado: $f"
        else
            echo "  OJO: $f tiene cambios ademas del ?v=, se deja sin stagear"
        fi
    done
fi

# Check 1: syntax y antipatrones (siempre que haya cambios en HTML/JS)
if git diff --cached --name-only | grep -qE '\.(html|js)$'; then
    echo "Running syntax & antipattern check..."
    py shared/check-syntax-and-consistency.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "SYNTAX CHECK FAILED -- commit bloqueado"
        echo "Revisa los issues arriba y corregilos antes de comitear."
        exit 1
    fi
fi

# Check 2: history preservation (bloquea si se pierden meses de historia)
if git diff --cached --name-only | grep -qE '(data\.js|index\.html|dermato_dashboard\.html|psq_dashboard\.html)$'; then
    echo "Running history-preservation check..."
    py shared/verify-history-preserved.py --baseline HEAD --strict
    if [ $? -ne 0 ]; then
        echo ""
        echo "HISTORY CHECK FAILED -- commit bloqueado"
        echo "Se detecto perdida de meses de historia en mol_perf."
        echo "El nuevo IQVIA solo debe AGREGAR meses, no reemplazar el time-series."
        echo "Usar shared/merge-april-2026-only.py (o equivalente) que preserva historia."
        exit 1
    fi
fi

# Check 3: consistency audit (solo si hay cambios en data)
if git diff --cached --name-only | grep -qE '(data\.js|kpis\.json|index\.html|dermato_dashboard\.html|psq_dashboard\.html)$'; then
    echo "Running consistency audit..."
    py shared/audit-full.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "AUDIT FAILED -- commit bloqueado"
        echo "Ejecutar: py shared/fix-brandkpis-from-molperf.py && py shared/build-kpis.py && py shared/sync-kpistrip-with-kpis-json.py"
        exit 1
    fi
    echo "Audit OK"
fi

# Check 4: venta interna vs estimado (bloquea %Cumpl >500% = lumping col0/col1,
# el bug ALTA DOSIS=705%). Solo si cambio algun data.js / pagina con budget.
if git diff --cached --name-only | grep -qE '(data\.js|index\.html|dermato_dashboard\.html)$'; then
    echo "Running venta-vs-estimado check..."
    py shared/check-venta-vs-estimado.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "VENTA/ESTIMADO CHECK FAILED -- commit bloqueado"
        echo "Hay %Cumpl >500%: la venta interna esta sumando una Gran Familia"
        echo "entera a una sub-marca. Revisar merge-ventas-internas.py (Familia col1)."
        exit 1
    fi
fi

# Check 5: paridad entre lineas (mismo nucleo de keys/labels en las 7).
if git diff --cached --name-only | grep -qE '(data\.js|index\.html|dermato_dashboard\.html)$'; then
    echo "Running cross-line parity check..."
    py shared/check-cross-line-parity.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "CROSS-LINE PARITY FAILED -- commit bloqueado"
        echo "Alguna linea perdio una key/label del nucleo comun. Revisar arriba."
        exit 1
    fi
fi

# Check 5b: mujer conserva su segmentacion por CLASE IQVIA (ALTA DOSIS, SIN
# ESTROGENO, ...). Bloquea la regresion de reconstruir mujer por MARCA (ISIS,
# SIDERBLUT, TRIP D3) = sintoma de haber metido 'mujer' en build-all. mujer debe
# quedar FUERA de build-all (como SNC/derma): se preserva de prod + sync time-series.
if git diff --cached --name-only | grep -qE 'mujer/data\.js$'; then
    echo "Running mujer-segmentation check..."
    py shared/check-mujer-segmentation.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "MUJER-SEGMENTATION FAILED -- commit bloqueado"
        echo "mujer/data.js perdio la segmentacion por CLASE IQVIA (mercados por marca)."
        echo "mujer debe quedar FUERA de build-all (como SNC/derma): se preserva + sync."
        exit 1
    fi
fi

# Check 6: etiquetas vs dato real (cada label = su fuente; atrapa rec_label/iqviaMeta stale).
if git diff --cached --name-only | grep -qE '(data\.js|index\.html|dermato_dashboard\.html)$'; then
    echo "Running labels-vs-data check..."
    py shared/audit-labels.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "LABELS CHECK FAILED -- commit bloqueado"
        echo "Una etiqueta de fecha no coincide con su fuente. Correr: py shared/finalize-labels.py"
        exit 1
    fi
fi

# Check 7: render-parity (F3). Bloquea que una funcion del bundle shared/render/
# se vuelva a copiar inline en una pagina (regresion del fix-7-veces).
if git diff --cached --name-only | grep -qE '(index\.html|dermato_dashboard\.html|shared/render/.*\.js)$'; then
    echo "Running render-parity check..."
    py shared/check-render-parity.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "RENDER-PARITY FAILED -- commit bloqueado"
        echo "Una funcion de render compartida quedo definida inline en una pagina."
        echo "Debe venir SOLO del bundle shared/render/ (borrar la copia inline)."
        exit 1
    fi
fi

# Check 8: salud de las paginas DDD (mercados-molecula). Bloquea include roto
# (app.js faltante) y mercados con region_data vacio (tabla regional en blanco).
if git diff --cached --name-only | grep -qE '(DDD/.*\.(html|js)|dermato_ddd\.html|psq_ddd\.html|data\.js)$'; then
    echo "Running DDD-health check..."
    py shared/check-ddd-health.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "DDD-HEALTH FAILED -- commit bloqueado"
        echo "Una pagina DDD tiene un include roto (app.js faltante) o un mercado con"
        echo "region_data vacio (tabla regional en blanco). Revisar arriba."
        exit 1
    fi
fi

# Check 9: IE relativo al mercado. Bloquea que brandKpis[marca].ie quede como
# crecimiento propio (units/units_prev) en vez de IE vs-mercado (base 100).
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    echo "Running IE-vs-market check..."
    py shared/fix-brandkpis-ie-vs-market.py --check
    if [ $? -ne 0 ]; then
        echo ""
        echo "IE-RELATIVE FAILED -- commit bloqueado"
        echo "Algun brandKpis.ie quedo como crecimiento propio en vez de IE vs-mercado."
        echo "Correr: py shared/fix-brandkpis-ie-vs-market.py"
        exit 1
    fi
fi

# Check 10: brandKpis market_total/ms vs mol_perf (agregado autoritativo). Bloquea
# market_total de un mercado más amplio o units del mes (no MAT).
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    echo "Running brandKpis-market-total check..."
    py shared/fix-brandkpis-market-total.py --check
    if [ $? -ne 0 ]; then
        echo ""
        echo "BRANDKPIS-MARKET FAILED -- commit bloqueado"
        echo "Algun brandKpis.market_total/ms no coincide con mol_perf[fam].ytd/mat."
        echo "Correr: py shared/fix-brandkpis-market-total.py"
        exit 1
    fi
fi

# Check 11: convenios sin filas duplicadas exactas (misma OS + mismas unidades con
# código distinto) que el render suma -> doble conteo.
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    echo "Running convenios-dedup check..."
    py shared/dedup-convenios-exact.py --check
    if [ $? -ne 0 ]; then
        echo ""
        echo "CONVENIOS-DEDUP FAILED -- commit bloqueado"
        echo "Hay filas de convenios duplicadas exactas (doble conteo en el render)."
        echo "Correr: py shared/dedup-convenios-exact.py"
        exit 1
    fi
fi

# Check 12: brandKpis.rec.ms sin ceros espurios (0 con dato en rec_ms).
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    echo "Running brandKpis-rec check..."
    py shared/fix-brandkpis-rec.py --check
    if [ $? -ne 0 ]; then
        echo ""
        echo "BRANDKPIS-REC FAILED -- commit bloqueado"
        echo "Algun brandKpis.rec.ms quedo en 0 teniendo dato en rec_ms."
        echo "Correr: py shared/fix-brandkpis-rec.py"
        exit 1
    fi
fi

# Check 13: suma(mol_perf[fam].products) == mol_perf[fam] total, exacto.
# Es la invariante de la que recompute-mol-perf-aggregates.py deriva el total del
# mercado: si no cierra, el proximo recompute mueve el total publicado y arrastra el
# tablero Total y los KPIs. Ningun otro gate la verificaba por familia.
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    echo "Running molperf-suma-productos check..."
    py shared/check-molperf-suma-productos.py
    if [ $? -ne 0 ]; then
        echo ""
        echo "MOLPERF-SUMA FAILED -- commit bloqueado"
        echo "La suma de mol_perf[fam].products no da el total de la familia."
        echo "Si se agregaron competidores, el residuo 'Otros (resto del mercado)' tiene"
        echo "que recalcularse: py shared/itemize-molperf-otros.py"
        exit 1
    fi
fi

# Check 14: los agregados POR PRODUCTO (mat/ytd) suman el total de su familia.
# Es distinto del Check 13: aquel valida las VENTANAS sumando monthly_vals, y por eso no
# veia que 78 productos tuvieran mat={}. Ese hueco no movia ninguna suma -- solo rompia el
# grafico anual, que renormaliza sobre p.mat (REXULTI salia 100% en vez de 84,13% y los 4
# competidores de BREXPIPRAZOLE no se dibujaban).
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    py shared/check-molperf-agregados-por-producto.py
    if [ $? -ne 0 ]; then
        echo "BLOQUEADO: agregados por producto inconsistentes con su familia."
        exit 1
    fi
fi


# Check 15: la ficha por marca (brandKpis/kpiByBrand) al dia con mol_perf. Es lo que
# export-dashboard.js usa para exportar MS%/IE/Mercado por marca, y no la valida ningun
# otro gate: en SNC quedo congelada en enero (units_ytd = 1 mes en vez de 6) mientras el
# tablero mostraba junio, y nadie se entero porque no rompe ninguna suma.
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    py shared/check-brandkpis-al-dia.py
    if [ $? -ne 0 ]; then
        echo "BLOQUEADO: la ficha por marca no coincide con mol_perf."
        exit 1
    fi
fi

# Check 16: las marcas SIEGFRIED siguen en mol_perf con is_sie=true. Es el UNICO gate
# que mira ETIQUETAS y no sumas. En Jul-2026 el export de IQVIA reordeno sus columnas
# (317 -> 329) y los build-data.ps1 leian producto/laboratorio por POSICION: 'prod'
# quedo con el laboratorio ("GADOR"), 'manuf' con la presentacion ("SINLIP CAPS 20mg
# x 30"), is_sie cayo a false en los 384 productos y las 49 marcas SIE desaparecieron
# de cardio/ATB/OTC/respiratorio. No se movio UNA sola suma: audit-full daba
# 16.626/16.634 y verify-history-preserved daba OK.
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    py shared/check-molperf-sie-presente.py
    if [ $? -ne 0 ]; then
        echo "BLOQUEADO: faltan marcas SIE en mol_perf (o 'manuf' trae presentaciones)."
        echo "Casi siempre es el master con las columnas reordenadas: verificar que"
        echo "build-data.ps1 resuelva Product/Manufacturer por HEADER y re-correr el build."
        exit 1
    fi
fi

# Check 17: FORMA vs baseline (claves de primer nivel, productos y familias de
# mol_perf). El otro gate que no mira sumas. En Jul-2026 el mismo cierre borro la
# clave 'mercadosAteneo' de las 4 lineas (el literal $dashboardData conoce 27 claves
# y reescribe data.js entero) y dejo mol_perf con la mitad de los productos (cardio
# 364 -> 182: itemize-molperf-otros.py fallo sin frenar el pipeline). Las dos cosas
# pasaron todos los gates de aritmetica.
if git diff --cached --name-only | grep -qE 'data\.js$'; then
    py shared/check-forma-vs-baseline.py
    if [ $? -ne 0 ]; then
        echo "BLOQUEADO: la forma de algun data.js se degrado vs HEAD."
        echo "Si falta una clave top-level, la borro el rebuild y hay que regenerarla"
        echo "(mercadosAteneo -> py shared/build-mercados-ateneo.py --master <AR_PM>)."
        echo "Si se derrumbaron los productos: py shared/itemize-molperf-otros.py --master <AR_PM>"
        exit 1
    fi
fi

exit 0
