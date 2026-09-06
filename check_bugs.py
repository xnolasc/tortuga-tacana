"""Chequeo de salud: corre esto cuando quieras para confirmar que
no hay inconsistencias contables en ningun ledger."""
import json
import glob

print("=== Chequeo de consistencia de ledgers ===\n")
todo_bien = True

for path in sorted(glob.glob('real_ledger_*.json')):
    with open(path) as f:
        l = json.load(f)
    ticker = path.replace('real_ledger_', '').replace('.json', '')
    reservado = sum(p['costo_total'] for p in l['posiciones_reservadas'].values())
    total = round(l['capital_disponible'] + reservado, 2)
    inicial = l['capital_total_inicial']

    if total != inicial:
        print(f"❌ {ticker}: total=${total} != inicial=${inicial} -- REVISAR")
        todo_bien = False
    else:
        print(f"✅ {ticker}: total=${total} (correcto)")

    # Chequeo extra: que las shares en posiciones_reservadas coincidan
    # con las shares reales guardadas en crypto_state.json
    with open('crypto_state.json') as f:
        state = json.load(f)
    for key, pos in l['posiciones_reservadas'].items():
        t, sistema = key.rsplit('_', 1)
        if t == ticker:
            estado_pos = state.get(t, {}).get(sistema, {})
            if estado_pos.get('status') == 'EN_POSICION':
                shares_reales = sum(u['shares'] for u in estado_pos.get('units', []))
                if abs(shares_reales - pos['shares']) > 0.00001:
                    print(f"   ⚠️  {key}: ledger dice {pos['shares']} shares, pero state.json dice {shares_reales} -- DESINCRONIZADO")
                    todo_bien = False

print("\n" + ("=== TODO OK ===" if todo_bien else "=== HAY PROBLEMAS, REVISAR ARRIBA ==="))
