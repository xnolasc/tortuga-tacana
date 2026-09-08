"""
pool_ledger.py (branch: pool-real-dennis)
UN SOLO pool de capital compartido entre TODOS los tickers cripto --
igual diseño original de Dennis: una sola cuenta, el 1% de riesgo se
calcula sobre el capital TOTAL real (o simulado), y cualquier ticker
que rompa su nivel compite por la MISMA plata.
"""
import json
import os
import time

from binance_account import get_capital_disponible_real

POOL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pool_ledger.json")


def load_pool():
    capital_actual, es_real = get_capital_disponible_real()

    if os.path.exists(POOL_PATH):
        with open(POOL_PATH) as f:
            pool = json.load(f)
    else:
        pool = {"posiciones_reservadas": {}, "historial_eventos": [],
                "comisiones_pagadas_total": 0.0}

    reservado = sum(p["costo_total"] for p in pool["posiciones_reservadas"].values())
    pool["capital_total_real_o_simulado"] = capital_actual
    pool["es_balance_real"] = es_real
    pool["capital_disponible"] = round(capital_actual - reservado, 2)
    pool["updated_at"] = int(time.time())
    return pool


def save_pool(pool):
    with open(POOL_PATH, "w") as f:
        json.dump(pool, f, indent=2)


def try_reserve(pool, ticker, system, unit_shares_deseado, price, min_notional_usd, commission_pct):
    monto_bruto_deseado = unit_shares_deseado * price
    comision_deseada = monto_bruto_deseado * commission_pct
    costo_total_deseado = monto_bruto_deseado + comision_deseada
    disponible = pool["capital_disponible"]

    if disponible >= costo_total_deseado:
        return unit_shares_deseado, round(monto_bruto_deseado, 2), round(comision_deseada, 2), "completo"

    monto_bruto_maximo = disponible / (1 + commission_pct)
    if monto_bruto_maximo >= min_notional_usd:
        shares_escalados = monto_bruto_maximo / price
        comision_escalada = monto_bruto_maximo * commission_pct
        return (round(shares_escalados, 8), round(monto_bruto_maximo, 2),
                round(comision_escalada, 2), "escalado")

    return 0.0, 0.0, 0.0, "sin_capital"


def confirm_reserve(pool, ticker, system, shares, monto_bruto, comision):
    key = f"{ticker}_{system}"
    costo_total_nuevo = monto_bruto + comision
    pool["capital_disponible"] = round(pool["capital_disponible"] - costo_total_nuevo, 2)
    pool["comisiones_pagadas_total"] = round(pool["comisiones_pagadas_total"] + comision, 2)

    if key in pool["posiciones_reservadas"]:
        existing = pool["posiciones_reservadas"][key]
        existing["shares"] = round(existing["shares"] + shares, 8)
        existing["monto_bruto"] = round(existing["monto_bruto"] + monto_bruto, 2)
        existing["comision_entrada"] = round(existing["comision_entrada"] + comision, 2)
        existing["costo_total"] = round(existing["costo_total"] + costo_total_nuevo, 2)
        existing["unidades"] = existing.get("unidades", 1) + 1
    else:
        pool["posiciones_reservadas"][key] = {
            "shares": shares, "monto_bruto": monto_bruto, "comision_entrada": comision,
            "costo_total": costo_total_nuevo, "unidades": 1, "reservado_at": int(time.time()),
        }

    pool["historial_eventos"].append({
        "evento": "reserva", "ticker": ticker, "system": system,
        "shares": shares, "monto_bruto": monto_bruto, "comision": comision,
        "capital_disponible_despues": pool["capital_disponible"],
        "timestamp": int(time.time()),
    })


def release(pool, ticker, system, precio_venta, commission_pct):
    key = f"{ticker}_{system}"
    pos = pool["posiciones_reservadas"].pop(key, None)
    if pos is None:
        return None

    monto_bruto_venta = pos["shares"] * precio_venta
    comision_salida = monto_bruto_venta * commission_pct
    monto_neto_venta = monto_bruto_venta - comision_salida
    pnl_neto = monto_neto_venta - pos["costo_total"]

    pool["capital_disponible"] = round(pool["capital_disponible"] + monto_neto_venta, 2)
    pool["comisiones_pagadas_total"] = round(pool["comisiones_pagadas_total"] + comision_salida, 2)
    pool["historial_eventos"].append({
        "evento": "liberacion", "ticker": ticker, "system": system,
        "monto_bruto_venta": round(monto_bruto_venta, 2),
        "comision_salida": round(comision_salida, 2),
        "costo_total_original": pos["costo_total"],
        "pnl_neto": round(pnl_neto, 2),
        "capital_disponible_despues": pool["capital_disponible"],
        "timestamp": int(time.time()),
    })
    return round(pnl_neto, 2)


def get_summary(pool):
    total_reservado = sum(p["costo_total"] for p in pool["posiciones_reservadas"].values())
    return {
        "capital_total": pool["capital_total_real_o_simulado"],
        "es_balance_real": pool["es_balance_real"],
        "capital_disponible": pool["capital_disponible"],
        "capital_reservado_en_posiciones": round(total_reservado, 2),
        "comisiones_pagadas_total": pool["comisiones_pagadas_total"],
        "cantidad_posiciones_abiertas": len(pool["posiciones_reservadas"]),
        "posiciones": pool["posiciones_reservadas"],
    }
