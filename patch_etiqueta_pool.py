PATH = "crypto_dashboard.py"

with open(PATH) as f:
    content = f.read()

old = '<div class="label">Pool unico compartido (21 tickers, diseño Dennis)</div>'
new = '<div class="label">Pool unico compartido (35 tickers, diseño Dennis)</div>'

count = content.count(old)
assert count == 1, "[FALLO] encontrado " + str(count) + " veces (se esperaba 1)."
content = content.replace(old, new)

with open(PATH, "w") as f:
    f.write(content)

print("[OK] etiqueta actualizada a 35 tickers")
