import json
import os
import time

from crypto_common import symbol_for, COMMISSION_PCT, STATE_PATH, TRADES_LOG_PATH
from crypto_price_feed import get_precise_price

LEGACY_TICKERS = ["BNB", "UNI", "NEAR", "LTC", "INJ", "FET"]
SYSTEMS = ["system1", "system2"]
REASON = "cierre_legacy_branch_anterior"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def calcular_costo_entrada(units):
    costo_total = 0.0
    for u in units:
        monto_bruto = u["entry_price"] * u["shares"]
        comision = monto_bruto * COMMISSION_PCT
        costo_total += monto_bruto + comision
    return round(costo_total, 4)


def main():
    state = load_json(STATE_PATH, {})
    trades = load_json(TRADES_LOG_PATH, [])

    cerrados = []

    for ticker in LEGACY_TICKERS:
        symbol = symbol_for(ticker)
        price_data = get_precise_price(symbol)

        if not price_data.get("ok"):
            print("[SALTADO] " + ticker + ": no se pudo obtener precio (" + str(price_data.get("error")) + ")")
            continue

        price = price_data.get("mid") or price_data.get("last_price")
        if not price:
            print("[SALTADO] " + ticker + ": precio vacio en la respuesta")
            continue

        for system in SYSTEMS:
            pos = state.get(ticker, {}).get(system)
            if not pos or pos.get("status") != "EN_POSICION":
                print("[SALTADO] " + ticker + "/" + system + ": no esta EN_POSICION")
                continue

            units = pos["units"]
            total_shares = sum(u["shares"] for u in units)
            costo_total_original = calcular_costo_entrada(units)
            avg_entry = sum(u["entry_price"] * u["shares"] for u in units) / total_shares

            monto_bruto_venta = total_shares * price
            comision_salida = monto_bruto_venta * COMMISSION_PCT
            monto_neto_venta = monto_bruto_venta - comision_salida
            pnl_neto = round(monto_neto_venta - costo_total_original, 2)

            trades.append({
                "ticker": ticker, "system": system,
                "entry_price": round(avg_entry, 6), "exit_price": round(price, 6),
                "shares": round(total_shares, 8), "units": len(units),
                "pnl_usd": pnl_neto,
                "result": "GANANCIA" if pnl_neto > 0 else "PERDIDA",
                "reason": REASON,
                "entry_time": units[0]["entry_time"], "exit_time": int(time.time()),
            })

            state[ticker][system] = {"status": "ESPERANDO"}
            cerrados.append((ticker, system, pnl_neto))
            print("[CERRADO] " + ticker + "/" + system + ": vende " + str(round(total_shares,6)) + " @ " + str(round(price,6)) + " (P&L neto: $" + str(pnl_neto) + ")")

    if cerrados:
        save_json(STATE_PATH, state)
        save_json(TRADES_LOG_PATH, trades)
        print("")
        print("Total cerrados: " + str(len(cerrados)) + " (de " + str(len(LEGACY_TICKERS) * len(SYSTEMS)) + " posibles)")
        print("crypto_state.json y crypto_trades.json actualizados.")
        print("pool_ledger.json NO fue tocado.")
    else:
        print("")
        print("Nada que cerrar -- ningun ticker estaba EN_POSICION.")


if __name__ == "__main__":
    main()
