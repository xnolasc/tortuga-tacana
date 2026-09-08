"""Chequeo de salud del pool unico -- reemplaza check_bugs.py (que
asumia 8 ledgers separados por ticker, ya no aplica en este branch)."""
import json
from pool_ledger import load_pool, get_summary

pool = load_pool()
resumen = get_summary(pool)

capital_total = resumen["capital_total"]
disponible = resumen["capital_disponible"]
reservado = resumen["capital_reservado_en_posiciones"]
total_calculado = round(disponible + reservado, 2)

print("=== Chequeo de consistencia del POOL UNICO ===\n")
print(f"Capital total: \${capital_total}")
print(f"Disponible: \${disponible}")
print(f"Reservado: \${reservado}")
print(f"Total (disponible+reservado): \${total_calculado}")
print(f"Balance real de Binance: {resumen['es_balance_real']}")
print(f"Posiciones abiertas: {resumen['cantidad_posiciones_abiertas']}")

if abs(total_calculado - capital_total) > 0.05:
    print(f"\n❌ INCONSISTENCIA: total calculado (\${total_calculado}) no coincide con capital total (\${capital_total})")
else:
    print(f"\n✅ TODO OK -- el pool cierra correctamente")
