"""
crypto_paper_trader.py (versión LEDGER)
Igual máquina de estados (System 1 + System 2, pirámide, stop dinámico)
que el resto del sistema -- pero ahora, en vez de comprar el tamaño
"ideal" sin restricción, consulta el ledger REAL de cada ticker antes
de comprar: si el capital de ese ticker (compartido entre S1 y S2)
alcanza, compra completo; si alcanza parcial, ESCALA hacia abajo; si no
alcanza ni el mínimo, se salta la señal. Al cerrar, libera el capital
de vuelta al ledger de ese ticker, con la comisión de salida aplicada.

100% simulado -- ningún precio real de Binance se toca para comprar/
vender de verdad, solo se CONSULTA el precio público (igual que el
resto del sistema).
"""

import json
import os
import time

from crypto_common import (
    TICKERS, symbol_for, SKIP_AFTER_WINNER, PYRAMID_ADD_INTERVAL_N, MAX_UNITS,
    TICKER_CAPITAL_USD, COMMISSION_PCT, MIN_NOTIONAL_USD,
    LEVELS_CACHE_PATH, STATE_PATH, TRADES_LOG_PATH, TRADER_LOG,
    ledger_path_for,
)
from crypto_price_feed import get_precise_price
import real_ledger as rl

SYSTEMS = ["system1", "system2"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(TRADER_LOG, "a") as f:
        f.write(line + "\n")


def get_last_trade_result(trades, ticker, system):
    for t in reversed(trades):
        if t["ticker"] == ticker and t["system"] == system:
            return t["result"]
    return None


def empty_position():
    return {"status": "ESPERANDO"}


def close_position_with_ledger(ledger, ticker, system, pos, price, reason, trades):
    units = pos["units"]
    total_shares = sum(u["shares"] for u in units)
    cost_basis_bruto = sum(u["entry_price"] * u["shares"] for u in units)
    avg_entry = cost_basis_bruto / total_shares if total_shares > 0 else 0

    pnl_neto = rl.release(ledger, ticker, system, price, COMMISSION_PCT)

    trades.append({
        "ticker": ticker, "system": system,
        "entry_price": round(avg_entry, 6), "exit_price": price,
        "shares": round(total_shares, 8), "units": len(units),
        "pnl_usd": pnl_neto if pnl_neto is not None else 0.0,
        "result": "GANANCIA" if (pnl_neto or 0) > 0 else "PERDIDA",
        "reason": reason,
        "entry_time": units[0]["entry_time"], "exit_time": int(time.time()),
    })
    log(f"{ticker}/{system}: {reason.upper()} -> vende {round(total_shares,6)} unidades "
        f"@ {price} (P&L neto con comisiones: ${pnl_neto})")
    return empty_position()


def main():
    cache = load_json(LEVELS_CACHE_PATH, None)
    if not cache:
        log("No existe crypto_levels_cache.json -- corré crypto_report.py primero.")
        return

    default_state = {t: {s: empty_position() for s in SYSTEMS} for t in TICKERS}
    state = load_json(STATE_PATH, default_state)
    trades = load_json(TRADES_LOG_PATH, [])

    for ticker in TICKERS:
        levels = cache["levels"].get(ticker)
        if not levels or not levels.get("ok"):
            log(f"{ticker}: sin niveles válidos, se salta.")
            continue

        n_atr = levels["n_atr"]
        stop_distance = levels["stop_distance"]

        symbol = symbol_for(ticker)
        price_info = get_precise_price(symbol)
        if not price_info["ok"]:
            log(f"{ticker}: no se pudo obtener precio ({price_info['error']}), se salta.")
            continue
        price = price_info["last_price"]

        ledger_path = ledger_path_for(ticker)
        ledger = rl.load_ledger(ledger_path, TICKER_CAPITAL_USD[ticker])

        if ticker not in state:
            state[ticker] = {s: empty_position() for s in SYSTEMS}

        ledger_changed = False

        for system in SYSTEMS:
            sys_levels = levels[system]
            if not sys_levels.get("available", True):
                continue
            pos = state[ticker].get(system, empty_position())

            if pos["status"] == "ESPERANDO":
                if system == "system1":
                    last_result = get_last_trade_result(trades, ticker, system)
                    if SKIP_AFTER_WINNER and last_result == "GANANCIA":
                        continue

                if price >= sys_levels["entry"]:
                    unit_shares_deseado = sys_levels["unit_shares"]
                    if unit_shares_deseado <= 0:
                        log(f"{ticker}/{system}: señal pero unit_shares=0 "
                            f"({sys_levels['limiting_factor']}), se salta.")
                        continue

                    shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                        ledger, ticker, system, unit_shares_deseado, price,
                        MIN_NOTIONAL_USD, COMMISSION_PCT)

                    if motivo == "sin_capital":
                        log(f"{ticker}/{system}: señal de entrada pero SIN CAPITAL "
                            f"disponible en el ledger de {ticker} (disponible: "
                            f"${ledger['capital_disponible']}), se salta.")
                        continue

                    rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                    ledger_changed = True

                    entry_time = int(time.time())
                    state[ticker][system] = {
                        "status": "EN_POSICION",
                        "units": [{"entry_price": price, "shares": shares_ok, "entry_time": entry_time}],
                        "stop": round(price - stop_distance, 6),
                    }
                    nota = "" if motivo == "completo" else " (ESCALADO por falta de capital)"
                    log(f"{ticker}/{system}: COMPRA unidad 1 de {shares_ok} @ {price}{nota} "
                        f"(stop={round(price - stop_distance, 6)}, capital disponible después: "
                        f"${ledger['capital_disponible']})")

            elif pos["status"] == "EN_POSICION":
                units = pos["units"]
                stop = pos["stop"]

                if price <= stop:
                    state[ticker][system] = close_position_with_ledger(
                        ledger, ticker, system, pos, price, "stop_loss", trades)
                    ledger_changed = True
                    continue

                if price <= sys_levels["exit"]:
                    state[ticker][system] = close_position_with_ledger(
                        ledger, ticker, system, pos, price, "exit_breakout", trades)
                    ledger_changed = True
                    continue

                if len(units) < MAX_UNITS:
                    last_unit_price = units[-1]["entry_price"]
                    add_trigger = last_unit_price + PYRAMID_ADD_INTERVAL_N * n_atr
                    unit_shares_deseado = sys_levels["unit_shares"]
                    if price >= add_trigger and unit_shares_deseado > 0:
                        shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                            ledger, ticker, system, unit_shares_deseado, price,
                            MIN_NOTIONAL_USD, COMMISSION_PCT)
                        if motivo == "sin_capital":
                            log(f"{ticker}/{system}: pirámide quiere agregar pero SIN CAPITAL, se salta el add.")
                            continue
                        rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                        ledger_changed = True

                        units.append({"entry_price": price, "shares": shares_ok,
                                      "entry_time": int(time.time())})
                        new_stop = round(price - stop_distance, 6)
                        state[ticker][system] = {"status": "EN_POSICION", "units": units, "stop": new_stop}
                        nota = "" if motivo == "completo" else " (ESCALADO)"
                        log(f"{ticker}/{system}: AGREGA unidad {len(units)}/{MAX_UNITS} de "
                            f"{shares_ok}{nota} @ {price} (nuevo stop={new_stop})")

        if ledger_changed:
            rl.save_ledger(ledger_path, ledger)

    save_json(STATE_PATH, state)
    save_json(TRADES_LOG_PATH, trades)


if __name__ == "__main__":
    main()
