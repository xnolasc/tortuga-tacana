PATH = "crypto_paper_trader.py"

with open(PATH) as f:
    content = f.read()

patches = []

old1 = '''            if pos["status"] == "ESPERANDO":
                if system == "system1":
                    last_result = get_last_trade_result(trades, ticker, system)
                    if SKIP_AFTER_WINNER and last_result == "GANANCIA":
                        continue'''
new1 = '''            if pos["status"] in ("ESPERANDO", "SIN_CAPITAL", "FAMILIA_LLENA", "HEAT_LIMITE"):
                if system == "system1":
                    last_result = get_last_trade_result(trades, ticker, system)
                    if SKIP_AFTER_WINNER and last_result == "GANANCIA":
                        continue'''
patches.append(("condicion de entrada", old1, new1))

old2 = '''                    unidades_familia = count_units_in_family(state, family_map, ticker)
                    if unidades_familia >= MAX_UNITS_PER_FAMILY:
                        log(ticker + "/" + system + ": FAMILIA LLENA, se salta.")
                        continue'''
new2 = '''                    unidades_familia = count_units_in_family(state, family_map, ticker)
                    if unidades_familia >= MAX_UNITS_PER_FAMILY:
                        log(ticker + "/" + system + ": FAMILIA LLENA, se salta.")
                        state[ticker][system] = {"status": "FAMILIA_LLENA"}
                        continue'''
patches.append(("familia llena", old2, new2))

old3 = '''                    riesgo_nueva = unit_shares_deseado * stop_distance
                    if heat_actual + riesgo_nueva > heat_limite:
                        log(ticker + "/" + system + ": PORTFOLIO HEAT se pasaria, se salta.")
                        continue'''
new3 = '''                    riesgo_nueva = unit_shares_deseado * stop_distance
                    if heat_actual + riesgo_nueva > heat_limite:
                        log(ticker + "/" + system + ": PORTFOLIO HEAT se pasaria, se salta.")
                        state[ticker][system] = {"status": "HEAT_LIMITE"}
                        continue'''
patches.append(("portfolio heat", old3, new3))

old4 = '''                    shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                        ledger, ticker, system, unit_shares_deseado, price,
                        MIN_NOTIONAL_USD, COMMISSION_PCT)

                    if motivo == "sin_capital":
                        continue

                    rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                    ledger_changed = True
                    heat_actual += shares_ok * stop_distance'''
new4 = '''                    shares_ok, monto_ok, comision_ok, motivo = rl.try_reserve(
                        ledger, ticker, system, unit_shares_deseado, price,
                        MIN_NOTIONAL_USD, COMMISSION_PCT)

                    if motivo == "sin_capital":
                        state[ticker][system] = {"status": "SIN_CAPITAL"}
                        continue

                    rl.confirm_reserve(ledger, ticker, system, shares_ok, monto_ok, comision_ok)
                    ledger_changed = True
                    heat_actual += shares_ok * stop_distance'''
patches.append(("sin capital (entrada)", old4, new4))

for nombre, old, new in patches:
    count = content.count(old)
    assert count == 1, "[FALLO] '" + nombre + "': encontrado " + str(count) + " veces (se esperaba 1)."
    content = content.replace(old, new)
    print("[OK] parche '" + nombre + "' aplicado")

with open(PATH, "w") as f:
    f.write(content)
print("crypto_paper_trader.py actualizado.")
