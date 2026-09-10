PATH = "crypto_common.py"

with open(PATH) as f:
    content = f.read()

old = 'DASHBOARD_TITLE = "Tortuga Tacana Pool Dennis - 31 tickers (22 cripto + 9 bStocks tokenizados), 1 pool unico"'
new = 'DASHBOARD_TITLE = "Tortuga Tacana Pool Dennis - 35 tickers (26 cripto + 9 bStocks tokenizados), 1 pool unico"'

count = content.count(old)
assert count == 1, "[FALLO] encontrado " + str(count) + " veces (se esperaba 1)."
content = content.replace(old, new)

with open(PATH, "w") as f:
    f.write(content)

print("[OK] titulo actualizado a 35 tickers")
