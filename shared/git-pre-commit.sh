#!/bin/sh
# Pre-commit hook: run syntax check + audit before allowing commit.
# Si alguna falla, bloquea el commit.

# Check 0: cache-busters. Si se tocaron data.js / assets compartidos / paginas,
# re-genera el ?v=<hash> y re-stagea las paginas afectadas. Asi NUNCA se sirve
# una version vieja cacheada por olvidarse de bumpear ?v.
if git diff --cached --name-only | grep -qE '(data\.js|shared/.*\.(js|css)|index\.html|dermato_dashboard\.html|kpis\.html)$'; then
    echo "Bumping cache-busters (?v=hash)..."
    py shared/bump-cache-busters.py
    git add cardio/index.html ATB/index.html OTC/index.html respiratorio/index.html \
            mujer/index.html SNC/index.html dermatologia/dermato_dashboard.html \
            kpis.html index.html 2>/dev/null
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
exit 0
