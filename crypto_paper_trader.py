"""
crypto_paper_trader.py (branch: experimento-5-mejoras)
Agrega 2 chequeos ANTES de comprar o agregar unidad de piramide:
  - OPCION 3: limite de unidades por familia correlacionada
  - OPCION 4: limite de portfolio heat (riesgo total abierto)
"""

import json
import os
import time

from crypto_common import (
    TICKERS, symbol_for, SKIP_AFTER_WINNER, PYRAMID_ADD_INTERVAL_N, MAX_UNITS,
    TICKER_CAPITAL_USD, COMMISSION_PCT, MIN_NOTIONAL_USD,
    LEVELS_CACHE_PATH, STATE_PATH, TRADES_LOG_PATH, TRADER_LOG,
    ledger_path_for, MAX_UNITS_PER_FAMILY, PORTFOLIO_HEAT_LIMIT_PCT,
    get_dynamic_capital,
)
from crypto_price_feed import get_precise_price
import yfinance as yf
import pool_ledger as rl

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
    line = "[" + time.strftime('%Y-%m-%d %H:%M:%S') + "] " + msg
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


def build_family_map(familias):
    m = {}
    for i, fam in enumerate(familias):
        for t in fam:
            m[t] = i
    return m


def count_units_in_family(state, family_map, ticker):
    fam_id = family_map.get(ticker)
    if fam_id is None:
        return 0
    total_unidades = 0
    for t, fid in family_map.items():
        if fid != fam_id:
            continue
        for system in SYSTEMS:
            pos = state.get(t, {}).get(system, {})
            if pos.get("status") == "EN_POSICION":
                total_unidades += len(pos.get("units", []))
    return total_unidades


def compute_portfolio_heat(state, levels):
    total_risk = 0.0
    for ticker, systems in state.items():
        lvl = levels.get(ticker, {})
        ref_price = lvl.get("ref_price")
        for system in SYSTEMS:
            pos = systems.get(system, {})
            if pos.get("status") == "EN_POSICION":
                shares = sum(u["shares"] for u in pos.get("units", []))
                stop = pos.get("stop")
                if ref_price is not None and stop is not None:
                    total_risk += shares * max(ref_price - stop, 0)
    return round(total_risk, 2)


def total_system_capital():
    return round(sum(get_dynamic_capital(t) for t in TICKERS), 2)


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
    log(ticker + "/" + system + ": " + reason.upper() + " -> vende " + str(round(total_shares,6)) + " @ " + str(price) + " (P&L neto: $" + str(pnl_neto) + ")")
    return empty_position()


def main():
    cache = load_json(LEVELS_CACHE_PATH, None)
    if not cache:
        log("No existe crypto_levels_cache.json -- corre crypto_report.py primero.")
        return

    familias = cache.get("familias", [])
    family_map = build_family_map(familias)

    default_state = {}
    for t in TICKERS:
        default_state[t] = {}
        for s in SYSTEMS:
            default_state[t][s] = empty_position()
    state = load_json(STATE_PATH, default_state)
    trades = load_json(TRADES_LOG_PATH, [])

    heat_actual = compute_portfolio_heat(state, cache["levels"])
    heat_limite = round(total_system_capital() * PORTFOLIO_HEAT_LIMIT_PCT, 2)
    log("Portfolio heat actual: $" + str(heat_actual) + " / limite: $" + str(heat_limite))

    for ticker in TICKERS:
        levels = cache["levels"].get(ticker)
        if not levels or not levels.get("ok"):
            continue

        n_atr = levels["n_atr"]
        stop_distance = levels["stop_distance"]

        symbol = symbol_for(ticker)
        price_info = get_precise_price(symbol)
        if not price_info["ok"]:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                if len(hist) > 0:
                    price_info = {"last_price": float(hist["Close"].iloc[-1]), "ok": True}
            except Exception:
                pass
        if not price_info["ok"]:
            continue
        price = price_info["last_price"]

        ledger = rl.load_pool()

        if ticker not in state:
            state[ticker] = {}
            for s in SYSTEMS:
                state[ticker][s] = empty_position()

        ledger_changed = False

        for system in SYSTEMS:
            sys_levels = levels[system]
            if not sys_levels.get("available", True):
                continue
            pos = state[ticker].get(system, empty_position())

            if pos["status"] in ("ESPERANDO", "SIN_CAPITAL", "FAMILIA_LLENA", "HEAT_LIMITE"):
                if system == "system1":
                    last_result = get_last_trade_result(trades, ticker, system)
                    if SKIP_AFTER_WINNER and last_result == "GANANCIA":
                        continue

                if price >= sys_levels["entry"]:
                    unit_shares_deseado = sys_levels["unit_shares"]
                    if unit_shares_deseado <= 0:
                        continue

                    unidades_familia = count_units_in_family(state, family_map, ticker)
                    if unidades_familia >= MAX_UNITS_PER_FAMILY:
                        log(ticker + "/" + system + ": FAMILIA LLENA, se salta.")
                        state[ticker][system] = {"status": "FAMILIA_LLENA"}
                        continue

                    riesgo_nueva = unit_shares_deseado * stop_distance
                    if heat_actual + riesgo_nueva > heat_limite:
                        log(ticker + "/" + system + ": PORTFOLIO HEAT se pasaria, se salta.")
                        state[ticker][system] = {"status": "HEAT_LIMITE"}
                        continue

                    shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                        ledger, ticker, system, unit_shares_deseado, price,
                        MIN_NOTIONAL_USD, COMMISSION_PCT)

                    if motivo == "sin_capital":
                        state[ticker][system] = {"status": "SIN_CAPITAL"}
                        continue

                    rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                    ledger_changed = True
                    heat_actual += shares_ok * stop_distance

                    entry_time = int(time.time())
                    state[ticker][system] = {
                        "status": "EN_POSICION",
                        "units": [{"entry_price": price, "shares": shares_ok, "entry_time": entry_time}],
                        "stop": round(price - stop_distance, 6),
                    }
                    nota = "" if motivo == "completo" else " (ESCALADO)"
                    log(ticker + "/" + system + ": COMPRA unidad 1 de " + str(shares_ok) + " @ " + str(price) + nota)

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
                        unidades_familia = count_units_in_family(state, family_map, ticker)
                        if unidades_familia >= MAX_UNITS_PER_FAMILY:
                            continue
                        riesgo_nueva = unit_shares_deseado * stop_distance
                        if heat_actual + riesgo_nueva > heat_limite:
                            continue

                        shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                            ledger, ticker, system, unit_shares_deseado, price,
                            MIN_NOTIONAL_USD, COMMISSION_PCT)
                        if motivo == "sin_capital":
                            continue
                        rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                        ledger_changed = True
                        heat_actual += shares_ok * stop_distance

                        units.append({"entry_price": price, "shares": shares_ok,
                                      "entry_time": int(time.time())})
                        new_stop = round(price - stop_distance, 6)
                        state[ticker][system] = {"status": "EN_POSICION", "units": units, "stop": new_stop}
                        log(ticker + "/" + system + ": AGREGA unidad " + str(len(units)) + "/" + str(MAX_UNITS))

        if ledger_changed:
            rl.save_pool(ledger)

    save_json(STATE_PATH, state)
    save_json(TRADES_LOG_PATH, trades)


if __name__ == "__main__":
    main()
