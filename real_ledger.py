"""
real_ledger.py (con comisiones)
Igual lógica que la versión anterior probada (reservar completo, escalar
si falta capital, liberar al cerrar) -- ahora con la comisión real de
Binance (0.1% por operación) aplicada tanto al comprar como al vender,
para que los números se parezcan lo más posible a lo que pasaría con
plata real de verdad.
"""

import json
import os
import time


def load_ledger(path, capital_inicial):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    ledger = {
        "capital_total_inicial": capital_inicial,
        "capital_disponible": capital_inicial,
        "posiciones_reservadas": {},
        "historial_eventos": [],
        "comisiones_pagadas_total": 0.0,
        "updated_at": int(time.time()),
    }
    save_ledger(path, ledger)
    return ledger


def save_ledger(path, ledger):
    ledger["updated_at"] = int(time.time())
    with open(path, "w") as f:
        json.dump(ledger, f, indent=2)


def try_reserve(ledger, ticker, system, unit_shares_deseado, price, min_notional_usd, commission_pct):
    """
    Intenta reservar el capital para comprar, incluyendo la comisión de
    ENTRADA (se paga sobre el monto bruto de la compra).

    Devuelve (shares_aprobados, monto_bruto, comision, motivo).
    El monto TOTAL que sale de la caja es (monto_bruto + comision).
    """
    monto_bruto_deseado = unit_shares_deseado * price
    comision_deseada = monto_bruto_deseado * commission_pct
    costo_total_deseado = monto_bruto_deseado + comision_deseada

    disponible = ledger["capital_disponible"]

    if disponible >= costo_total_deseado:
        return unit_shares_deseado, round(monto_bruto_deseado, 2), round(comision_deseada, 2), "completo"

    monto_bruto_maximo = disponible / (1 + commission_pct)
    if monto_bruto_maximo >= min_notional_usd:
        shares_escalados = monto_bruto_maximo / price
        comision_escalada = monto_bruto_maximo * commission_pct
        return (round(shares_escalados, 8), round(monto_bruto_maximo, 2),
                round(comision_escalada, 2), "escalado")

    return 0.0, 0.0, 0.0, "sin_capital"


def confirm_reserve(ledger, ticker, system, shares, monto_bruto, comision):
    key = f"{ticker}_{system}"
    costo_total = monto_bruto + comision
    ledger["capital_disponible"] = round(ledger["capital_disponible"] - costo_total, 2)
    ledger["comisiones_pagadas_total"] = round(ledger["comisiones_pagadas_total"] + comision, 2)
    ledger["posiciones_reservadas"][key] = {
        "shares": shares, "monto_bruto": monto_bruto, "comision_entrada": comision,
        "costo_total": costo_total, "reservado_at": int(time.time()),
    }
    ledger["historial_eventos"].append({
        "evento": "reserva", "ticker": ticker, "system": system,
        "shares": shares, "monto_bruto": monto_bruto, "comision": comision,
        "capital_disponible_despues": ledger["capital_disponible"],
        "timestamp": int(time.time()),
    })


def release(ledger, ticker, system, precio_venta, commission_pct):
    key = f"{ticker}_{system}"
    pos = ledger["posiciones_reservadas"].pop(key, None)
    if pos is None:
        return None

    monto_bruto_venta = pos["shares"] * precio_venta
    comision_salida = monto_bruto_venta * commission_pct
    monto_neto_venta = monto_bruto_venta - comision_salida

    pnl_neto = monto_neto_venta - pos["costo_total"]

    ledger["capital_disponible"] = round(ledger["capital_disponible"] + monto_neto_venta, 2)
    ledger["comisiones_pagadas_total"] = round(ledger["comisiones_pagadas_total"] + comision_salida, 2)
    ledger["historial_eventos"].append({
        "evento": "liberacion", "ticker": ticker, "system": system,
        "monto_bruto_venta": round(monto_bruto_venta, 2),
        "comision_salida": round(comision_salida, 2),
        "costo_total_original": pos["costo_total"],
        "pnl_neto": round(pnl_neto, 2),
        "capital_disponible_despues": ledger["capital_disponible"],
        "timestamp": int(time.time()),
    })
    return round(pnl_neto, 2)


def get_summary(ledger):
    total_reservado = sum(p["costo_total"] for p in ledger["posiciones_reservadas"].values())
    return {
        "capital_total_inicial": ledger["capital_total_inicial"],
        "capital_disponible": ledger["capital_disponible"],
        "capital_reservado_en_posiciones": round(total_reservado, 2),
        "capital_total_actual": round(ledger["capital_disponible"] + total_reservado, 2),
        "comisiones_pagadas_total": ledger["comisiones_pagadas_total"],
        "cantidad_posiciones_abiertas": len(ledger["posiciones_reservadas"]),
        "posiciones": ledger["posiciones_reservadas"],
    }
