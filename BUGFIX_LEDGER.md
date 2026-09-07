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

**2026-09-07 (branch experimento-5-mejoras)**
- Agregados 6 tickers nuevos: INJ, DOGE, PEPE, DOT, FET, LINK, $200 cada uno.
- Total de tickers en este branch: 19 (13 anteriores + estos 6).
- Capital total simulado del experimento: $3,800 (19 x $200).
- Titulo del dashboard actualizado para reflejar 19 tickers.

**2026-09-07 (branch experimento-5-mejoras) -- parte 2**
- Removido ARB de la lista activa (TICKERS y TICKER_CAPITAL_USD). Su
  ledger (real_ledger_ARB.json) se conserva como registro historico del
  trade cerrado (-$12.39), pero ya no participa en recalculos ni compras
  nuevas.
- Agregados 3 tokens de IA: RNDR (Render, GPU para IA), TAO (Bittensor,
  red de machine learning descentralizada), GRT (The Graph, indexado de
  datos on-chain usado por agentes de IA), $200 cada uno.
- Total de tickers activos en este branch: 21 (18 anteriores - ARB + 3 nuevos).
- Capital total simulado activo: $4,200 (21 x $200), mas el historico de ARB.
- Titulo del dashboard actualizado a "21 tickers".
- Nota: ya tenia FET, LINK y NEAR relacionados con IA/agentes desde antes;
  con RNDR/TAO/GRT el tema queda mejor representado (compute, ML, datos).

**2026-09-07 (branch experimento-5-mejoras) -- parte 3**
- Removido PEPE de la lista activa (tenia bug de precision numerica
  irresoluble en la practica: N tan chico que las unidades quedaban en
  millones de tokens, aunque el fix de precision evito el crash).
  Su ledger (real_ledger_PEPE.json) se conserva como historico.
- Agregados 3 tokens de computo GPU descentralizado (Capa 2 del modelo
  de capas de IA): AKT (Akash Network), IO (io.net), ATH (Aethir),
  $200 cada uno.
- Total de tickers activos: 23 (21 anteriores - PEPE + estos 3).
- Capital total simulado activo: $4,600 (23 x $200).
- Titulo del dashboard actualizado a "23 tickers".
- Con este cambio, el tema IA queda representado en 4 capas del modelo
  de capas propuesto: Computo (RNDR, AKT, IO, ATH), Datos (GRT, LINK),
  Entrenamiento/Inferencia (TAO), Agentes (FET, NEAR).

**2026-09-07 (branch experimento-5-mejoras) -- parte 4**
- AKT (Akash Network) y ATH (Aethir) confirmados como NO disponibles
  en Binance (400 Bad Request en /api/v3/klines, y ausentes en el
  listado completo de exchangeInfo). Removidos de la lista.
- Queda IO (io.net) como el unico de los 3 tokens de computo GPU
  adicionales que si existe y funciona en Binance.
- Total de tickers activos: 21 (BNB/UNI/BTC/ETH/SOL/SUI/NEAR/TRX/XRP/
  LTC/ZEC/DASH/INJ/DOGE/DOT/FET/LINK/RNDR/TAO/GRT/IO).
