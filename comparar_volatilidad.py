"""Compara el N (ATR) de hoy contra el de hace unos dias, usando el
historial de Git, para confirmar si el mercado esta mas tranquilo o
no (en vez de asumirlo de memoria)."""
import json
import subprocess
import sys

def obtener_niveles_de_commit(commit_hash):
    try:
        resultado = subprocess.run(
            ["git", "show", commit_hash + ":crypto_levels_cache.json"],
            capture_output=True, text=True, check=True
        )
        return json.loads(resultado.stdout)
    except Exception as e:
        print(f"No se pudo leer el commit {commit_hash}: {e}")
        return None

# Buscar commits que tocaron crypto_levels_cache.json, con fecha
log = subprocess.run(
    ["git", "log", "--format=%h|%ad", "--date=short", "--", "crypto_levels_cache.json"],
    capture_output=True, text=True
).stdout.strip().split("\n")

if not log or log == ['']:
    print("No hay historial de crypto_levels_cache.json en este branch.")
    sys.exit(1)

print("=== Commits disponibles con niveles guardados ===")
for line in log[:15]:
    print(" ", line)

# Elegir automaticamente uno de hace ~3-5 dias (o el mas viejo disponible si no hay tantos)
import datetime
hoy = datetime.date.today()
elegido = None
for line in log:
    h, fecha_str = line.split("|")
    fecha = datetime.date.fromisoformat(fecha_str)
    dias_atras = (hoy - fecha).days
    if dias_atras >= 2:
        elegido = (h, fecha_str)
        break

if not elegido:
    elegido_h, elegido_fecha = log[-1].split("|")
    print(f"\nNo hay commits de 2+ dias atras -- usando el mas viejo disponible: {elegido_fecha}")
else:
    elegido_h, elegido_fecha = elegido
    print(f"\nUsando commit de {elegido_fecha} ({elegido_h}) para comparar")

datos_viejos = obtener_niveles_de_commit(elegido_h)
datos_hoy = json.load(open("crypto_levels_cache.json"))

if not datos_viejos:
    sys.exit(1)

print(f"\n=== Comparacion de N (ATR): {elegido_fecha} vs HOY ===\n")
print(f"{'Ticker':<8} {'N viejo':>12} {'N hoy':>12} {'Cambio %':>10}")
print("-" * 46)

for ticker in sorted(datos_hoy["levels"].keys()):
    d_hoy = datos_hoy["levels"].get(ticker, {})
    d_viejo = datos_viejos["levels"].get(ticker, {})
    if not d_hoy.get("ok") or not d_viejo.get("ok"):
        continue
    n_hoy = d_hoy["n_atr"]
    n_viejo = d_viejo["n_atr"]
    cambio_pct = ((n_hoy - n_viejo) / n_viejo * 100) if n_viejo else 0
    flecha = "↓ mas tranquilo" if cambio_pct < -10 else ("↑ mas volatil" if cambio_pct > 10 else "= parecido")
    print(f"{ticker:<8} {n_viejo:>12.6f} {n_hoy:>12.6f} {cambio_pct:>9.1f}% {flecha}")

print("\n=== Si la mayoria dice 'mas tranquilo', el mercado SI esta mas calmo hoy ===")
print("=== Si la mayoria dice 'parecido', es solo percepcion / falta de rupturas ===")
