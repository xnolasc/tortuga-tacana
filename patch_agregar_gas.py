PATH = "crypto_common.py"

with open(PATH) as f:
    content = f.read()

old = '''TICKERS = ["BNB", "UNI", "BTC", "ETH", "SOL", "NEAR",
           "XRP", "LTC", "ZEC", "DASH",
           "INJ", "DOT", "FET", "LINK",
           "RNDR", "TAO", "GRT",
           "IO", "FF", "ATOM", "VET", "ETC",
           "COHR", "MRVL", "AXTI", "LITE", "PLTR", "AAOI", "NVDA", "FN", "SPCX"]'''

new = '''TICKERS = ["BNB", "UNI", "BTC", "ETH", "SOL", "NEAR",
           "XRP", "LTC", "ZEC", "DASH",
           "INJ", "DOT", "FET", "LINK",
           "RNDR", "TAO", "GRT",
           "IO", "FF", "ATOM", "VET", "ETC",
           "AVAX", "POL", "TRX", "ADA",
           "COHR", "MRVL", "AXTI", "LITE", "PLTR", "AAOI", "NVDA", "FN", "SPCX"]'''

count = content.count(old)
assert count == 1, "[FALLO] encontrado " + str(count) + " veces (se esperaba 1)."
content = content.replace(old, new)

with open(PATH, "w") as f:
    f.write(content)

print("[OK] AVAX, POL, TRX, ADA agregados a TICKERS")
