"""
crypto_report.py (branch: experimento-5-mejoras)
Ahora usa capital DINAMICO por ticker (Opcion 1) y calcula FAMILIAS
por correlacion (Opcion 3), guardandolas en el mismo cache de niveles.
"""

import json
import time
import requests
from pool_ledger import load_pool

from crypto_common import (
    TICKERS, symbol_for, MIN_NOTIONAL_USD, ENTRY_BREAKOUT_DAYS, EXIT_BREAKOUT_DAYS,
    SYSTEM2_ENTRY_BREAKOUT_DAYS, SYSTEM2_EXIT_BREAKOUT_DAYS, ATR_LOOKBACK_DAYS,
    RISK_PCT_PER_SYSTEM, BINANCE_BASE, KLINES_ENDPOINT, LEVELS_CACHE_PATH,
    CORRELATION_LOOKBACK_DAYS, CORRELATION_THRESHOLD, get_dynamic_capital,
)

KLINES_NEEDED = max(SYSTEM2_ENTRY_BREAKOUT_DAYS, ATR_LOOKBACK_DAYS, CORRELATION_LOOKBACK_DAYS) + 2


def fetch_daily_klines(symbol, limit=KLINES_NEEDED):
    r = requests.get(
        BINANCE_BASE + KLINES_ENDPOINT,
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


def compute_levels_for_ticker(ticker, candles_cache):
    symbol = symbol_for(ticker)
    try:
        candles = fetch_daily_klines(symbol)
    except Exception as e:
        return {"ticker": ticker, "symbol": symbol, "ok": False, "error": str(e)}
    candles_cache[ticker] = candles

    min_needed = max(ENTRY_BREAKOUT_DAYS, ATR_LOOKBACK_DAYS + 1) + 1
    if len(candles) < min_needed:
        return {"ticker": ticker, "symbol": symbol, "ok": False,
                "error": "Solo " + str(len(candles)) + " velas, se necesitan " + str(min_needed)}

    closed = candles[:-1]
    n = len(closed)
    ref_price = closed[-1]["close"]

    tr_list = compute_true_range(closed[-(ATR_LOOKBACK_DAYS + 1):])
    n_atr = sum(tr_list) / len(tr_list) if tr_list else None
    if n_atr is None or n_atr <= 0:
        return {"ticker": ticker, "symbol": symbol, "ok": False, "error": "N invalido"}
    stop_distance = 2.0 * n_atr

    ticker_capital = capital_total  # POOL compartido, no caja por ticker

    system1 = None
    if n >= ENTRY_BREAKOUT_DAYS:
        s1_entry = max(c["high"] for c in closed[-ENTRY_BREAKOUT_DAYS:])
        s1_exit = min(c["low"] for c in closed[-EXIT_BREAKOUT_DAYS:])
        shares, limit, risk_usd = compute_unit_sizing(stop_distance, ref_price, ticker_capital)
        system1 = {"available": True, "entry": round(s1_entry, 6), "exit": round(s1_exit, 6),
                   "unit_shares": shares, "limiting_factor": limit, "risk_usd_per_unit": risk_usd}
    else:
        system1 = {"available": False, "reason": "Faltan velas"}

    system2 = None
    if n >= SYSTEM2_ENTRY_BREAKOUT_DAYS:
        s2_entry = max(c["high"] for c in closed[-SYSTEM2_ENTRY_BREAKOUT_DAYS:])
        s2_exit = min(c["low"] for c in closed[-SYSTEM2_EXIT_BREAKOUT_DAYS:])
        shares, limit, risk_usd = compute_unit_sizing(stop_distance, ref_price, ticker_capital)
        system2 = {"available": True, "entry": round(s2_entry, 6), "exit": round(s2_exit, 6),
                   "unit_shares": shares, "limiting_factor": limit, "risk_usd_per_unit": risk_usd}
    else:
        system2 = {"available": False, "reason": "Faltan velas"}

    return {
        "ticker": ticker, "symbol": symbol, "ok": True,
        "n_atr": round(n_atr, 12), "stop_distance": round(stop_distance, 12),
        "ref_price": round(ref_price, 6), "ticker_capital_dinamico": ticker_capital,
        "system1": system1, "system2": system2, "computed_at": int(time.time()),
    }


def _correlation(a, b):
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    a, b = a[-n:], b[-n:]
    mean_a, mean_b = sum(a) / n, sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((x - mean_b) ** 2 for x in b)
    if var_a == 0 or var_b == 0:
        return 0.0
    return cov / ((var_a ** 0.5) * (var_b ** 0.5))


def compute_correlation_groups(candles_cache, threshold):
    returns = {}
    for ticker, candles in candles_cache.items():
        closes = [c["close"] for c in candles]
        if len(closes) < 6:
            continue
        returns[ticker] = [(closes[i] - closes[i - 1]) / closes[i - 1]
                            for i in range(1, len(closes)) if closes[i - 1] != 0]

    tickers_list = list(returns.keys())
    assigned = {}
    groups = []
    for t in tickers_list:
        if t in assigned:
            continue
        group = [t]
        assigned[t] = True
        for t2 in tickers_list:
            if t2 in assigned:
                continue
            c = _correlation(returns[t], returns[t2])
            if c >= threshold:
                group.append(t2)
                assigned[t2] = True
        groups.append(group)
    return groups


def main():
    pool = load_pool()
    capital_total = pool["capital_total_real_o_simulado"]
    es_real = pool["es_balance_real"]
    print(f"Capital total del pool: ${capital_total:.2f} ({"REAL de Binance" if es_real else "SIMULADO"})")
    candles_cache = {}
    levels = {}
    for ticker in TICKERS:
        try:
            levels[ticker] = compute_levels_for_ticker(ticker, candles_cache, capital_total)
        except Exception as e:
            levels[ticker] = {"ticker": ticker, "ok": False, "error": str(e)}
        print(ticker + ": " + str(levels[ticker]))

    print("")
    print("Calculando familias por correlacion...")
    familias = compute_correlation_groups(candles_cache, CORRELATION_THRESHOLD)
    for i, fam in enumerate(familias):
        print("  Familia " + str(i+1) + ": " + str(fam))

    with open(LEVELS_CACHE_PATH, "w") as f:
        json.dump({
            "generated_at": int(time.time()),
            "levels": levels,
            "familias": familias,
        }, f, indent=2)
    print("")
    print("Guardado en " + LEVELS_CACHE_PATH)


if __name__ == "__main__":
    main()
