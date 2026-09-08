"""
binance_account.py (branch: pool-real-dennis)
Consulta el balance REAL de tu cuenta de Binance (USDT disponible).
Si no hay API Key configurada, cae en un fallback simulado.
"""
import hmac
import hashlib
import time
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

API_KEY = os.environ.get("BINANCE_API_KEY")
SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")
BASE = "https://api.binance.com"

SIMULATED_CAPITAL_FALLBACK = 4200.0  # 21 tickers x $200 = $4200, el total que ya tenias


def _firmar(params):
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    firma = hmac.new(SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return query_string + f"&signature={firma}"


def get_balance_real():
    if not API_KEY or not SECRET_KEY:
        raise RuntimeError("BINANCE_API_KEY / BINANCE_SECRET_KEY no configuradas (.env)")
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp}
    query = _firmar(params)
    headers = {"X-MBX-APIKEY": API_KEY}
    r = requests.get(f"{BASE}/api/v3/account?{query}", headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()
    return {b["asset"]: float(b["free"]) for b in data["balances"] if float(b["free"]) > 0}


def get_capital_disponible_real():
    try:
        balances = get_balance_real()
        return balances.get("USDT", 0.0), True
    except Exception:
        return SIMULATED_CAPITAL_FALLBACK, False
