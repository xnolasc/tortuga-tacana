"""
crypto_common.py (versión LEDGER)
Variante del sistema Tortuga Crypto pensada como el paso previo más
cercano a Binance real: cada ticker tiene su PROPIA caja de capital
limitado (no infinito como en el paper trading normal), compartida
entre System 1 y System 2 (pool compartido dentro del mismo ticker).

Universo reducido a propósito: solo BNB y UNI, cada uno con su propio
monto de capital -- para poder observar bien el comportamiento del
ledger (escalado, capital agotado, liberación al cerrar) sin el ruido
de 18+ tickers a la vez.
"""

import os

# --- Universo de tickers para esta prueba ---
TICKERS = ["BNB", "UNI", "ARB", "BTC", "ETH", "SOL"]

def symbol_for(ticker: str) -> str:
    return f"{ticker}USDT"

# --- Capital REAL (simulado) por ticker -- cada uno con su propia caja ---
TICKER_CAPITAL_USD = {
    "BNB": 500.0,
    "UNI": 200.0,
    "ARB": 200.0,
    "BTC": 200.0,
    "ETH": 200.0,
    "SOL": 200.0,
}

# --- Riesgo por unidad, como % del capital de ESE ticker (no dinámico
# todavía en esta versión -- se recalcula sobre el capital ORIGINAL de
# cada ticker, para simplificar el experimento) ---
RISK_PCT_PER_UNIT = 0.03          # 1% del capital del ticker, por unidad
RISK_PCT_PER_SYSTEM = RISK_PCT_PER_UNIT / 2   # dividido entre S1 y S2

# --- Comisión real de Binance spot (0.1% por operación, sin BNB para fees) ---
COMMISSION_PCT = 0.001

# --- Restricción real de Binance: mínimo de orden ---
MIN_NOTIONAL_USD = 10.0

# --- Parámetros Turtle System 1 y System 2 (idénticos al resto del sistema) ---
ENTRY_BREAKOUT_DAYS = 20
EXIT_BREAKOUT_DAYS = 10
ATR_LOOKBACK_DAYS = 20
STOP_N_MULTIPLE = 2.0
SKIP_AFTER_WINNER = True

SYSTEM2_ENTRY_BREAKOUT_DAYS = 55
SYSTEM2_EXIT_BREAKOUT_DAYS = 20

PYRAMID_ADD_INTERVAL_N = 0.5
MAX_UNITS = 4

# --- Binance API (pública, sin API key) ---
BINANCE_BASE = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
TICKER_PRICE_ENDPOINT = "/api/v3/ticker/price"
BOOK_TICKER_ENDPOINT = "/api/v3/ticker/bookTicker"

# --- Rutas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_CACHE_PATH = os.path.join(BASE_DIR, "crypto_levels_cache.json")
STATE_PATH = os.path.join(BASE_DIR, "crypto_state.json")
TRADES_LOG_PATH = os.path.join(BASE_DIR, "crypto_trades.json")
DAILY_RECALC_LOG = os.path.join(BASE_DIR, "crypto_daily_recalc.log")
TRADER_LOG = os.path.join(BASE_DIR, "crypto_trader.log")

def ledger_path_for(ticker: str) -> str:
    """Cada ticker tiene su propio archivo de ledger -- pools separados
    entre tickers, pero compartido entre System 1 y System 2 dentro de
    cada uno."""
    return os.path.join(BASE_DIR, f"real_ledger_{ticker}.json")

DASHBOARD_PORT = 8897   # distinto a 8898 (paper normal) y 8899 (acciones)
DASHBOARD_TITLE = "🐢 Tortuga Tacaña — Ledger Real (BNB/UNI/ARB)"
