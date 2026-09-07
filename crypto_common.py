"""
crypto_common.py (branch: experimento-5-mejoras)
Agrega sobre la version base:
1. Capital dinamico por ticker (get_dynamic_capital)
2. Riesgo configurable (ya existia, ahora aplicado sobre capital dinamico)
3. Familias por correlacion (constantes de umbral y limite)
4. Portfolio heat (limite global de riesgo abierto)
5. (el polling mas rapido se ajusta en el cron, no en este archivo)

Tickers nuevos: LTC, ZEC, DASH (se agregan a la lista; si alguno no
existe en Binance, el pipeline ya maneja eso marcando 'ok': False sin
romper nada, igual que paso antes con MATIC/otros).
"""

import os
import json

TICKERS = ["BNB", "UNI", "BTC", "ETH", "SOL", "SUI", "NEAR",
           "TRX", "XRP", "LTC", "ZEC", "DASH",
           "INJ", "DOGE", "DOT", "FET", "LINK",
           "RNDR", "TAO", "GRT",
           "AKT", "IO", "ATH"]

def symbol_for(ticker: str) -> str:
    return f"{ticker}USDT"

TICKER_CAPITAL_USD = {
    "BNB": 200.0, "UNI": 200.0, "BTC": 200.0, "ETH": 200.0,
    "SOL": 200.0, "SUI": 200.0, "NEAR": 200.0, "TRX": 200.0, "XRP": 200.0,
    "LTC": 200.0, "ZEC": 200.0, "DASH": 200.0,
    "INJ": 200.0, "DOGE": 200.0, "DOT": 200.0, "FET": 200.0, "LINK": 200.0,
    "RNDR": 200.0, "TAO": 200.0, "GRT": 200.0,
    "AKT": 200.0, "IO": 200.0, "ATH": 200.0,
}

RISK_PCT_PER_UNIT = 0.03
RISK_PCT_PER_SYSTEM = RISK_PCT_PER_UNIT / 2

COMMISSION_PCT = 0.001
MIN_NOTIONAL_USD = 10.0

ENTRY_BREAKOUT_DAYS = 20
EXIT_BREAKOUT_DAYS = 10
ATR_LOOKBACK_DAYS = 20
STOP_N_MULTIPLE = 2.0
SKIP_AFTER_WINNER = True

SYSTEM2_ENTRY_BREAKOUT_DAYS = 55
SYSTEM2_EXIT_BREAKOUT_DAYS = 20

PYRAMID_ADD_INTERVAL_N = 0.5
MAX_UNITS = 4

CORRELATION_LOOKBACK_DAYS = 60
CORRELATION_THRESHOLD = 0.75
MAX_UNITS_PER_FAMILY = 6

PORTFOLIO_HEAT_LIMIT_PCT = 0.20

BINANCE_BASE = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
TICKER_PRICE_ENDPOINT = "/api/v3/ticker/price"
BOOK_TICKER_ENDPOINT = "/api/v3/ticker/bookTicker"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_CACHE_PATH = os.path.join(BASE_DIR, "crypto_levels_cache.json")
STATE_PATH = os.path.join(BASE_DIR, "crypto_state.json")
TRADES_LOG_PATH = os.path.join(BASE_DIR, "crypto_trades.json")
DAILY_RECALC_LOG = os.path.join(BASE_DIR, "crypto_daily_recalc.log")
TRADER_LOG = os.path.join(BASE_DIR, "crypto_trader.log")

def ledger_path_for(ticker: str) -> str:
    return os.path.join(BASE_DIR, f"real_ledger_{ticker}.json")

DASHBOARD_PORT = 8897
DASHBOARD_TITLE = "Tortuga Tacana V2 - 23 tickers - Capital dinamico + Familias + Heat"


def get_dynamic_capital(ticker: str) -> float:
    inicial = TICKER_CAPITAL_USD.get(ticker, 200.0)
    if not os.path.exists(TRADES_LOG_PATH):
        return round(inicial, 2)
    try:
        with open(TRADES_LOG_PATH) as f:
            trades = json.load(f)
    except Exception:
        return round(inicial, 2)
    pnl = sum(t["pnl_usd"] for t in trades if t.get("ticker") == ticker)
    return round(inicial + pnl, 2)
