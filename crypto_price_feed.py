"""crypto_price_feed.py -- igual al resto del sistema, batch + respaldo individual."""

import json
import requests
import yfinance as yf
from crypto_common import BINANCE_BASE, TICKER_PRICE_ENDPOINT, BOOK_TICKER_ENDPOINT

TIMEOUT = 8
MAX_RETRIES = 2


def _empty_result(symbol):
    return {"symbol": symbol, "last_price": None, "bid": None, "ask": None,
            "mid": None, "spread_pct": None, "ok": False, "error": None}


def _try_yahoo_fallback(symbol):
    ticker_original = symbol.replace("BUSDT", "").replace("USDT", "")
    try:
        stock = yf.Ticker(ticker_original)
        hist = stock.history(period="1d")
        if len(hist) > 0:
            precio = float(hist["Close"].iloc[-1])
            result = _empty_result(symbol)
            result.update({"last_price": precio, "mid": precio, "ok": True})
            return result
    except Exception:
        pass
    return None


def get_precise_price(symbol: str) -> dict:
    result = _empty_result(symbol)
    last_error = None
    for _ in range(MAX_RETRIES + 1):
        try:
            r1 = requests.get(f"{BINANCE_BASE}{TICKER_PRICE_ENDPOINT}",
                               params={"symbol": symbol}, timeout=TIMEOUT)
            r1.raise_for_status()
            last_price = float(r1.json()["price"])
            r2 = requests.get(f"{BINANCE_BASE}{BOOK_TICKER_ENDPOINT}",
                               params={"symbol": symbol}, timeout=TIMEOUT)
            r2.raise_for_status()
            book = r2.json()
            bid, ask = float(book["bidPrice"]), float(book["askPrice"])
            mid = (bid + ask) / 2 if (bid and ask) else last_price
            spread_pct = ((ask - bid) / mid * 100) if mid else None
            result.update({"last_price": last_price, "bid": bid, "ask": ask,
                            "mid": mid, "spread_pct": spread_pct, "ok": True})
            return result
        except Exception as e:
            last_error = str(e)
    yahoo_result = _try_yahoo_fallback(symbol)
    if yahoo_result:
        return yahoo_result
    result["error"] = last_error
    return result


def get_precise_prices(symbols: list) -> dict:
    results = {s: _empty_result(s) for s in symbols}
    if not symbols:
        return results
    symbols_param = json.dumps(symbols)
    try:
        r1 = requests.get(f"{BINANCE_BASE}{TICKER_PRICE_ENDPOINT}",
                           params={"symbols": symbols_param}, timeout=TIMEOUT)
        r1.raise_for_status()
        prices = {item["symbol"]: float(item["price"]) for item in r1.json()}
        r2 = requests.get(f"{BINANCE_BASE}{BOOK_TICKER_ENDPOINT}",
                           params={"symbols": symbols_param}, timeout=TIMEOUT)
        r2.raise_for_status()
        books = {item["symbol"]: item for item in r2.json()}
        for s in symbols:
            if s not in prices:
                continue
            last_price = prices[s]
            bid = ask = mid = spread_pct = None
            if s in books:
                bid, ask = float(books[s]["bidPrice"]), float(books[s]["askPrice"])
                mid = (bid + ask) / 2 if (bid and ask) else last_price
                spread_pct = ((ask - bid) / mid * 100) if mid else None
            results[s].update({"last_price": last_price, "bid": bid, "ask": ask,
                                "mid": mid, "spread_pct": spread_pct, "ok": True})
        return results
    except Exception:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(symbols), 10)) as ex:
            individual = list(ex.map(get_precise_price, symbols))
        return {r["symbol"]: r for r in individual}
    finally:
        # Asegurar que cualquier simbolo que quedo sin 'ok=True' (ej. FN
        # que Binance no tiene) tambien intente el fallback de Yahoo
        for s in symbols:
            if not results.get(s, {}).get("ok"):
                yahoo_result = _try_yahoo_fallback(s)
                if yahoo_result:
                    results[s] = yahoo_result
