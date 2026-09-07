# Bug corregido: pirámide sobreescribía el ledger en vez de acumular

**Fecha:** 2026-09-06

## Qué pasaba

Cuando una posición agregaba una 2da, 3ra o 4ta unidad de la pirámide,
`confirm_reserve()` en `real_ledger.py` SOBREESCRIBÍA el registro de
`posiciones_reservadas[ticker_system]` en vez de sumarle la unidad
nueva. El `capital_disponible` se descontaba bien en cada compra, pero
el campo "reservado" (usado para mostrar en el dashboard y para
calcular el P&L al cerrar la posición) solo guardaba los datos de la
ÚLTIMA unidad comprada, perdiendo el registro de las anteriores.

## Cómo se detectó

ARB agregó 4 unidades de pirámide en System 1 y System 2. El dashboard
mostraba "Ledger ARB: $0.00 disponible, $42.14 reservado" quedando un
total de $42.14 sobre $200 inicial -- parecía que $157.86 habían
desaparecido. Al revisar `historial_eventos`, la suma de las 8 compras
reales (4+4) daba exactamente $200.00 -- el dinero nunca se perdió,
solo el número "reservado" mostrado estaba mal.

## El fix

`confirm_reserve()` ahora verifica si ya existe una posición reservada
para esa key (ticker_system) y, si existe, SUMA la unidad nueva sobre
lo existente (shares, monto_bruto, comisión, costo_total) en vez de
sobreescribir. Se agregó también un contador `unidades` para poder ver
cuántos agregados de pirámide tiene cada posición abierta.

## Reparación de datos existentes

Se corrió `repair_ledgers.py`, que reconstruye `posiciones_reservadas`
desde `historial_eventos` (que siempre tuvo el registro completo y
correcto de cada evento individual) -- así se recuperó el número real
de "reservado" para ARB sin necesidad de inventar ni estimar nada.

## Impacto real

Ninguna plata se perdió en ningún momento -- `capital_disponible`
siempre estuvo bien calculado. El bug era puramente de visualización
y de cálculo de P&L al momento del cierre (que hubiera dado un número
equivocado si ARB se hubiera cerrado antes de este fix).

---

# Registro de cambios

**2026-09-06**
- Agregados TRX (Tron) y XRP (Ripple) a Tortuga Tacaña, $200 cada uno.
- Título del dashboard actualizado a: BNB/UNI/ARB/BTC/ETH/SOL/SUI/NEAR/TRX/XRP
- Chequeo de bugs corrido después del alta: 10/10 tickers OK, sin inconsistencias.
- Capital total simulado del sistema: $2,000 (10 tickers x $200 c/u).
