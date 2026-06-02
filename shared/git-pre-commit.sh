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
exit 0
