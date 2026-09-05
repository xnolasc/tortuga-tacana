"""
crypto_report.py (versión LEDGER)
Igual lógica de System 1 + System 2 que el resto del sistema. La única
diferencia real: el tamaño "deseado" de cada unidad se calcula sobre el
capital PROPIO de cada ticker (TICKER_CAPITAL_USD), no sobre un capital
global compartido -- ese tamaño "deseado" es lo que después el ledger
va a aprobar completo, escalar, o rechazar según el capital disponible
real en ese momento.
"""

import json
import time
import requests

from crypto_common import (
    TICKERS, symbol_for, TICKER_CAPITAL_USD, RISK_PCT_PER_SYSTEM,
    MIN_NOTIONAL_USD, ENTRY_BREAKOUT_DAYS, EXIT_BREAKOUT_DAYS,
    SYSTEM2_ENTRY_BREAKOUT_DAYS, SYSTEM2_EXIT_BREAKOUT_DAYS,
    ATR_LOOKBACK_DAYS, BINANCE_BASE, KLINES_ENDPOINT, LEVELS_CACHE_PATH,
)

KLINES_NEEDED = max(SYSTEM2_ENTRY_BREAKOUT_DAYS, ATR_LOOKBACK_DAYS) + 2


def fetch_daily_klines(symbol: str, limit: int = KLINES_NEEDED):
    r = requests.get(
        f"{BINANCE_BASE}{KLINES_ENDPOINT}",
        params={"symbol": symbol, "interval": "1d", "limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    raw = r.json()
    return [{
        "open": float(k[1]), "high": float(k[2]),
        "low": float(k[3]), "close": float(k[4]),
    } for k in raw]


def compute_true_range(candles):
    tr_list = []
    for i in range(1, len(candles)):
        prev_close = candles[i - 1]["close"]
        h, l = candles[i]["high"], candles[i]["low"]
        tr_list.append(max(h - l, abs(h - prev_close), abs(l - prev_close)))
    return tr_list


def compute_unit_sizing(stop_distance, ref_price, ticker_capital):
    risk_usd = ticker_capital * RISK_PCT_PER_SYSTEM
    unit_shares = (risk_usd / stop_distance) if stop_distance > 0 else 0.0
    unit_cost = unit_shares * ref_price
    limiting_factor = "riesgo"
    if unit_cost < MIN_NOTIONAL_USD:
        unit_shares = 0.0
        limiting_factor = "minNotional"
    return round(unit_shares, 8), limiting_factor, round(risk_usd, 2)


def compute_levels_for_ticker(ticker: str):
    symbol = symbol_for(ticker)
    candles = fetch_daily_klines(symbol)

    min_needed = max(ENTRY_BREAKOUT_DAYS, ATR_LOOKBACK_DAYS + 1) + 1
    if len(candles) < min_needed:
        return {"ticker": ticker, "symbol": symbol, "ok": False,
                "error": f"Solo {len(candles)} velas, se necesitan {min_needed}"}

    closed = candles[:-1]
    n = len(closed)
    ref_price = closed[-1]["close"]

    tr_list = compute_true_range(closed[-(ATR_LOOKBACK_DAYS + 1):])
    n_atr = sum(tr_list) / len(tr_list) if tr_list else None
    if not n_atr or n_atr <= 0:
        return {"ticker": ticker, "symbol": symbol, "ok": False, "error": "N inválido"}
    stop_distance = 2.0 * n_atr

    ticker_capital = TICKER_CAPITAL_USD[ticker]

    system1 = None
    if n >= ENTRY_BREAKOUT_DAYS:
        s1_entry = max(c["high"] for c in closed[-ENTRY_BREAKOUT_DAYS:])
        s1_exit = min(c["low"] for c in closed[-EXIT_BREAKOUT_DAYS:])
        shares, limit, risk_usd = compute_unit_sizing(stop_distance, ref_price, ticker_capital)
        system1 = {"available": True, "entry": round(s1_entry, 6), "exit": round(s1_exit, 6),
                   "unit_shares": shares, "limiting_factor": limit, "risk_usd_per_unit": risk_usd}
    else:
        system1 = {"available": False, "reason": f"Faltan velas: {n}/{ENTRY_BREAKOUT_DAYS}"}

    system2 = None
    if n >= SYSTEM2_ENTRY_BREAKOUT_DAYS:
        s2_entry = max(c["high"] for c in closed[-SYSTEM2_ENTRY_BREAKOUT_DAYS:])
        s2_exit = min(c["low"] for c in closed[-SYSTEM2_EXIT_BREAKOUT_DAYS:])
        shares, limit, risk_usd = compute_unit_sizing(stop_distance, ref_price, ticker_capital)
        system2 = {"available": True, "entry": round(s2_entry, 6), "exit": round(s2_exit, 6),
                   "unit_shares": shares, "limiting_factor": limit, "risk_usd_per_unit": risk_usd}
    else:
        system2 = {"available": False, "reason": f"Faltan velas: {n}/{SYSTEM2_ENTRY_BREAKOUT_DAYS}"}

    return {
        "ticker": ticker, "symbol": symbol, "ok": True,
        "n_atr": round(n_atr, 6), "stop_distance": round(stop_distance, 6),
        "ref_price": round(ref_price, 6), "ticker_capital": ticker_capital,
        "system1": system1, "system2": system2, "computed_at": int(time.time()),
    }


def main():
    levels = {}
    for ticker in TICKERS:
        try:
            levels[ticker] = compute_levels_for_ticker(ticker)
        except Exception as e:
            levels[ticker] = {"ticker": ticker, "ok": False, "error": str(e)}
        print(f"{ticker}: {levels[ticker]}")

    with open(LEVELS_CACHE_PATH, "w") as f:
        json.dump({"generated_at": int(time.time()), "levels": levels}, f, indent=2)
    print(f"\nGuardado en {LEVELS_CACHE_PATH}")


if __name__ == "__main__":
    main()
