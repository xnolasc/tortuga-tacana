"""
crypto_dashboard.py (versión LEDGER)
Muestra, además de la tabla normal de Estado/Resultados, el estado del
LEDGER de cada ticker (capital disponible, reservado, comisiones
pagadas) -- para ver en vivo cómo se comporta la restricción de
capital real que estamos probando.
"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from crypto_common import (
    TICKERS, symbol_for, TICKER_CAPITAL_USD, MAX_UNITS,
    DASHBOARD_PORT, DASHBOARD_TITLE,
    LEVELS_CACHE_PATH, STATE_PATH, TRADES_LOG_PATH, ledger_path_for,
)
from crypto_price_feed import get_precise_prices
import pool_ledger as rl

REFRESH_SECONDS = 10
SYSTEMS = ["system1", "system2"]
SYSTEM_LABEL = {"system1": "S1 (20d/10d)", "system2": "S2 (55d/20d)"}

_cache_lock = threading.Lock()
_cache = {"status_rows": [], "results": {}, "pool_summary": {}, "updated_at": None}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def recompute():
    levels_doc = load_json(LEVELS_CACHE_PATH, {"levels": {}})
    levels = levels_doc.get("levels", {})
    state = load_json(STATE_PATH, {})
    trades = load_json(TRADES_LOG_PATH, [])

    symbols = [symbol_for(t) for t in TICKERS]
    prices = get_precise_prices(symbols)

    pool = rl.load_pool()
    pool_summary = rl.get_summary(pool)

    status_rows = []
    for ticker in TICKERS:
        lvl = levels.get(ticker, {})
        pinfo = prices.get(symbol_for(ticker), {})
        price = pinfo.get("last_price")

        for system in SYSTEMS:
            sys_lvl = lvl.get(system, {}) if lvl.get("ok") else {}
            pos = state.get(ticker, {}).get(system, {"status": "ESPERANDO"})
            units = pos.get("units", [])
            total_shares = sum(u["shares"] for u in units) if units else None

            floating_pnl = None
            floating_pnl_pct = None
            if units and price is not None:
                cost_basis = sum(u["entry_price"] * u["shares"] for u in units)
                floating_pnl = round((price * total_shares) - cost_basis, 2)
                avg_entry = cost_basis / total_shares if total_shares else None
                floating_pnl_pct = round((price / avg_entry - 1) * 100, 2) if avg_entry else None

            status_rows.append({
                "ticker": ticker, "system": system,
                "price": price, "spread_pct": pinfo.get("spread_pct"), "price_ok": pinfo.get("ok", False),
                "available": sys_lvl.get("available", True),
                "entry": sys_lvl.get("entry"), "exit": sys_lvl.get("exit"),
                "n_atr": lvl.get("n_atr"),
                "unit_shares_planned": sys_lvl.get("unit_shares"),
                "status": pos.get("status", "ESPERANDO"),
                "units_held": len(units) if units else 0,
                "total_shares": total_shares,
                "avg_entry": (sum(u["entry_price"] * u["shares"] for u in units) / total_shares) if units and total_shares else None,
                "stop": pos.get("stop"),
                "floating_pnl": floating_pnl, "floating_pnl_pct": floating_pnl_pct,
            })

    closed_pnl = sum(t["pnl_usd"] for t in trades)
    wins = [t for t in trades if t["result"] == "GANANCIA"]
    losses = [t for t in trades if t["result"] == "PERDIDA"]
    win_rate = round(len(wins) / len(trades) * 100, 1) if trades else None

    results = {
        "total_trades": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate": win_rate, "closed_pnl_usd": round(closed_pnl, 2),
        "trades": list(reversed(trades)),
    }

    with _cache_lock:
        _cache["status_rows"] = status_rows
        _cache["results"] = results
        _cache["pool_summary"] = pool_summary
        _cache["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def background_updater():
    while True:
        try:
            recompute()
        except Exception as e:
            print(f"Error recalculando dashboard: {e}")
        time.sleep(REFRESH_SECONDS)


def fmt(v, decimals=2, prefix="", suffix=""):
    if v is None:
        return "—"
    return f"{prefix}{v:,.{decimals}f}{suffix}"


def render_html():
    with _cache_lock:
        rows = _cache["status_rows"]
        results = _cache["results"]
        pool_summary = _cache["pool_summary"]
        updated_at = _cache["updated_at"]

    fuente_txt = "REAL de Binance" if pool_summary.get("es_balance_real") else "SIMULADO -- falta API Key"
    fuente_color = "green" if pool_summary.get("es_balance_real") else "red"
    ledger_cards = [f"""
    <div class="card" style="min-width:100%;">
      <div class="label">Pool unico compartido (21 tickers, diseño Dennis)</div>
      <div class="value">${fmt(pool_summary.get('capital_disponible'), 2)}</div>
      <div class="dim">de ${fmt(pool_summary.get('capital_total'), 0)} total (<span class="{fuente_color}">{fuente_txt}</span>) · reservado: ${fmt(pool_summary.get('capital_reservado_en_posiciones'), 2)} · comisiones pagadas: ${fmt(pool_summary.get('comisiones_pagadas_total'), 2)} · posiciones abiertas: {pool_summary.get('cantidad_posiciones_abiertas', 0)}</div>
    </div>"""]

    status_trs = []
    for r in rows:
        status_class = "pos-en" if r["status"] == "EN_POSICION" else "pos-esp"
        status_display = r["status"] if r.get("available", True) else "SIN HISTORIAL"
        price_txt = fmt(r["price"], 4, "$") if r["price_ok"] else '<span class="red">sin datos</span>'
        spread_txt = fmt(r["spread_pct"], 3, "", "%")

        if r["units_held"] > 0:
            shares_display = f'{fmt(r["total_shares"], 6)} ({r["units_held"]}/{MAX_UNITS} unid.)'
        else:
            shares_display = f'{fmt(r["unit_shares_planned"], 6)}/unid. deseado'

        floating_class = ""
        floating_txt = "—"
        if r["floating_pnl"] is not None:
            floating_class = "green" if r["floating_pnl"] >= 0 else "red"
            floating_txt = f'{fmt(r["floating_pnl"], 2, "$")} ({fmt(r["floating_pnl_pct"], 2, "", "%")})'

        status_trs.append(f"""
        <tr>
          <td class="ticker">{r['ticker']}</td>
          <td class="dim">{SYSTEM_LABEL[r['system']]}</td>
          <td>{price_txt}</td>
          <td class="dim">spread {spread_txt}</td>
          <td>{fmt(r['entry'], 4, "$")}</td>
          <td>{fmt(r['exit'], 4, "$")}</td>
          <td>{fmt(r['n_atr'], 4)}</td>
          <td><span class="badge {status_class}">{status_display}</span></td>
          <td>{shares_display}</td>
          <td>{fmt(r['avg_entry'], 6, "$")}</td>
          <td>{fmt(r['stop'], 6, "$")}</td>
          <td class="{floating_class}">{floating_txt}</td>
        </tr>""")

    trade_trs = []
    for t in results.get("trades", []):
        cls = "green" if t["result"] == "GANANCIA" else "red"
        ts_entry = time.strftime("%Y-%m-%d %H:%M", time.localtime(t["entry_time"]))
        ts_exit = time.strftime("%Y-%m-%d %H:%M", time.localtime(t["exit_time"]))
        trade_trs.append(f"""
        <tr>
          <td class="ticker">{t['ticker']}</td>
          <td class="dim">{SYSTEM_LABEL.get(t.get('system'), '—')}</td>
          <td>{fmt(t['entry_price'], 6, "$")}</td>
          <td>{fmt(t['exit_price'], 6, "$")}</td>
          <td>{fmt(t['shares'], 6)} ({t.get('units','?')} unid.)</td>
          <td class="{cls}">{fmt(t['pnl_usd'], 2, "$")}</td>
          <td class="dim">{t['reason']}</td>
          <td class="dim">{ts_entry} → {ts_exit}</td>
        </tr>""")

    total_pnl_class = "green" if (results.get("closed_pnl_usd") or 0) >= 0 else "red"
    win_rate_txt = fmt(results.get("win_rate"), 1, "", "%")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="{REFRESH_SECONDS}">
<title>{DASHBOARD_TITLE}</title>
<style>
  body {{ background:#0e1117; color:#e6e6e6; font-family: -apple-system, Arial, sans-serif; margin:0; padding:24px; }}
  h1 {{ margin:0 0 4px 0; font-size:22px; }}
  .updated {{ color:#888; font-size:13px; margin-bottom:20px; }}
  .tabs {{ display:flex; gap:8px; margin-bottom:16px; }}
  .tab-btn {{ background:#1b1f27; border:1px solid #2a2f3a; color:#ccc; padding:8px 18px;
              border-radius:8px 8px 0 0; cursor:pointer; font-size:14px; }}
  .tab-btn.active {{ background:#232838; color:#fff; border-bottom:2px solid #f0b90b; }}
  .tab-content {{ display:none; }}
  .tab-content.active {{ display:block; }}
  table {{ border-collapse:collapse; width:100%; background:#161a22; border-radius:8px; overflow:hidden; }}
  th, td {{ padding:9px 12px; text-align:left; font-size:13px; border-bottom:1px solid #232838; }}
  th {{ background:#1b1f27; color:#9aa4b2; font-weight:600; text-transform:uppercase; font-size:11px; }}
  .ticker {{ font-weight:700; }}
  .dim {{ color:#7a8494; font-size:12px; }}
  .green {{ color:#3ddc84; font-weight:600; }}
  .red {{ color:#ff5c5c; font-weight:600; }}
  .badge {{ padding:3px 9px; border-radius:12px; font-size:11px; font-weight:600; }}
  .pos-esp {{ background:#232838; color:#9aa4b2; }}
  .pos-en {{ background:#233a2b; color:#3ddc84; }}
  .summary {{ display:flex; gap:16px; margin-bottom:18px; flex-wrap:wrap; }}
  .card {{ background:#161a22; border-radius:10px; padding:16px 22px; min-width:220px; }}
  .card .label {{ color:#7a8494; font-size:12px; text-transform:uppercase; margin-bottom:6px; }}
  .card .value {{ font-size:22px; font-weight:700; }}
</style>
<script>
  function showTab(name) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    document.getElementById('btn-' + name).classList.add('active');
    localStorage.setItem('ledger_tab', name);
  }}
  window.onload = function() {{
    var saved = localStorage.getItem('ledger_tab') || 'ledgers';
    showTab(saved);
  }}
</script>
</head>
<body>
  <h1>{DASHBOARD_TITLE}</h1>
  <div class="updated">Última actualización: {updated_at or '—'} · auto-refresh cada {REFRESH_SECONDS}s · comisión aplicada: 0.1% por operación</div>

  <div class="tabs">
    <div class="tab-btn" id="btn-ledgers" onclick="showTab('ledgers')">Ledgers</div>
    <div class="tab-btn" id="btn-estado" onclick="showTab('estado')">Estado</div>
    <div class="tab-btn" id="btn-resultados" onclick="showTab('resultados')">Resultados</div>
  </div>

  <div class="tab-content" id="tab-ledgers">
    <div class="summary">
      {"".join(ledger_cards)}
    </div>
  </div>

  <div class="tab-content" id="tab-estado">
    <table>
      <tr>
        <th>Ticker</th><th>Sistema</th><th>Precio</th><th></th><th>Entrada</th><th>Salida</th>
        <th>N (ATR)</th><th>Estado</th><th>Shares</th><th>Precio prom. entrada</th><th>Stop</th><th>P&amp;L flotante</th>
      </tr>
      {"".join(status_trs)}
    </table>
  </div>

  <div class="tab-content" id="tab-resultados">
    <div class="summary">
      <div class="card"><div class="label">P&amp;L neto total (con comisiones)</div><div class="value {total_pnl_class}">{fmt(results.get('closed_pnl_usd'), 2, "$")}</div></div>
      <div class="card"><div class="label">Win rate</div><div class="value">{win_rate_txt}</div></div>
      <div class="card"><div class="label">Trades</div><div class="value">{results.get('total_trades', 0)}</div></div>
    </div>
    <table>
      <tr>
        <th>Ticker</th><th>Sistema</th><th>Entrada prom.</th><th>Salida</th><th>Shares</th><th>P&amp;L neto $</th><th>Motivo</th><th>Cuándo</th>
      </tr>
      {"".join(trade_trs) if trade_trs else '<tr><td colspan="8" class="dim">Todavía no hay trades cerrados.</td></tr>'}
    </table>
  </div>
</body>
</html>"""
    return html


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(render_html().encode("utf-8"))

    def log_message(self, *args):
        pass


def main():
    threading.Thread(target=background_updater, daemon=True).start()
    server = HTTPServer(("0.0.0.0", DASHBOARD_PORT), Handler)
    print(f"{DASHBOARD_TITLE} corriendo en http://localhost:{DASHBOARD_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
