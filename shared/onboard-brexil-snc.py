# -*- coding: utf-8 -*-
"""Onboarding de BREXIL (brexpiprazol, lanzamiento abr-2026) a SNC.

BREXIL es lanzamiento nuevo: SOLO tiene datos en Venta Interna y Stock.
- Recetas: el mercado existe pero BREXIL aun no figura como marca (0 recetas).
- IQVIA: el corte llega a mar-2026 y BREXIL lanzo en abril -> 0 unidades aun.
- Precios/canales/convenios: sin dato.
Por eso se agrega SOLO a budget (venta interna + estimado 0) y stock. Cuando los
proximos cortes de IQVIA/CloseUp incluyan BREXIL, se agrega a mol_perf/recetas.

Datos (fuentes jun-2026):
  Venta interna 2026 (Planilla de Ventas): Abr 558, May 682 u. (Jun no cerrado)
  Stock (Laboratorio-Familia-Producto, may-2026): stock 624, ventas 466, fact 682
    dias = round(624/466*30) = 40   (convencion del tablero: dias = stock/ventas*30)
  Estimado: "Lanzamiento" = 0.

Idempotente. Uso: py shared/onboard-brexil-snc.py
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / 'SNC' / 'index.html'

BREXIL_REAL_2026 = [0, 0, 0, 558, 682, 0, 0, 0, 0, 0, 0, 0]   # Ene..Dic; venta interna Abr/May
# Estimado de ventas (curva de lanzamiento, suma de las 4 presentaciones 1/2/3/4 mg)
BREXIL_BUDGET_2026 = [0, 0, 0, 300, 350, 380, 390, 400, 410, 420, 430, 456]
BREXIL_STOCK = {'May 2026': {'stock': 624, 'ventas': 466, 'facturacion': 682, 'dias': round(624 / 466 * 30)}}
BREXIL_COLOR = '#be123c'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    text = HTML.read_text(encoding='utf-8', errors='replace')
    m = re.search(r'const\s+D\s*=\s*', text)
    ob = text.index('{', m.end())
    D, end = json.JSONDecoder().raw_decode(text[ob:])

    D.setdefault('budget', {})['BREXIL'] = {
        '2026': {'budget': list(BREXIL_BUDGET_2026), 'real': list(BREXIL_REAL_2026)},
    }
    D.setdefault('stock', {})['BREXIL'] = dict(BREXIL_STOCK)
    D.setdefault('colors', {})['BREXIL'] = BREXIL_COLOR

    print('BREXIL agregado a SNC:')
    print('  budget[BREXIL].2026.real =', BREXIL_REAL_2026)
    print('  stock[BREXIL] =', BREXIL_STOCK)
    print('  colors[BREXIL] =', BREXIL_COLOR)

    new = text[:ob] + json.dumps(D, ensure_ascii=False) + text[ob + end:]
    HTML.write_text(new, encoding='utf-8', newline='')
    print('\nEscrito SNC/index.html.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
