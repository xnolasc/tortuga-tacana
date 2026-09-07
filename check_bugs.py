"""Chequeo de salud (branch experimento-5-mejoras): ahora compara el
total del ledger contra el capital DINAMICO esperado (inicial + P&L de
trades ya cerrados de ese ticker), no contra un $200 fijo."""
import json
import glob

from crypto_common import get_dynamic_capital

print("=== Chequeo de consistencia de ledgers (capital dinamico) ===\n")
todo_bien = True

for path in sorted(glob.glob('real_ledger_*.json')):
    with open(path) as f:
        l = json.load(f)
    ticker = path.replace('real_ledger_', '').replace('.json', '')
    reservado = sum(p['costo_total'] for p in l['posiciones_reservadas'].values())
    total = round(l['capital_disponible'] + reservado, 2)
    esperado = get_dynamic_capital(ticker)

    if abs(total - esperado) > 0.02:
        print(f"❌ {ticker}: total=${total} != esperado (dinamico)=${esperado} -- REVISAR")
        todo_bien = False
    else:
        print(f"✅ {ticker}: total=${total} (coincide con capital dinamico esperado)")

print("\n" + ("=== TODO OK ===" if todo_bien else "=== HAY PROBLEMAS, REVISAR ARRIBA ==="))
