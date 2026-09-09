# Bugfix: status "ESPERANDO" invisible cuando el bloqueo real era otro

**Fecha:** 2026-09-08
**Repos afectados:** `tortuga-crypto` (`crypto_paper_trader.py`) y
`tortuga-acciones` (`turtle_paper_trader_ledger.py`), ambos en el diseno de
pool unico (`pool_ledger.py`, estilo Dennis 1983, branch `pool-real-dennis`).

## Sintoma

En el dashboard, SPCX (S1 y S2) rompio su nivel de entrada ($153.57 >=
$152.20) y el estado siguio mostrando "ESPERANDO" indefinidamente, sin
ninguna explicacion visible.

## Causa raiz

El trader SI detecta la ruptura correctamente, intenta reservar capital con
`rl.try_reserve()`, pero el pool compartido estaba en `capital_disponible =
0.0` (agotado por otros tickers que entraron antes). El codigo hacia:

```python
if motivo == "sin_capital":
    continue
```

Este `continue` no deja ningun rastro: no llama a `log()`, y no cambia
`state[ticker][system]["status"]`, que se queda en `"ESPERANDO"` para
siempre aunque el motivo real ya no sea "todavia no rompio nivel" sino "no
hay plata". En cripto, el mismo patron aparecia ademas en dos chequeos mas:
limite de familia correlacionada y limite de portfolio heat -- ambos
loguean el motivo en el log de texto, pero no actualizan el status visible
en el dashboard.

## Fix

Se agregaron estados nuevos, visibles en el dashboard sin tocar el codigo
del dashboard (que ya muestra `status` tal cual y solo distingue
`EN_POSICION` con un color distinto):

- `SIN_CAPITAL` -- rompio nivel, pero el pool no tiene fondos disponibles.
- `FAMILIA_LLENA` -- rompio nivel, familia correlacionada al maximo. Solo cripto.
- `HEAT_LIMITE` -- rompio nivel, excederia el limite de riesgo abierto. Solo cripto.

La condicion que decide si un ticker vuelve a intentar comprar se amplio de
`if pos["status"] == "ESPERANDO":` a incluir los nuevos estados, preservando
el comportamiento funcional exacto -- el unico cambio es que el motivo del
bloqueo queda visible.

## Nota

El caso de "sin_capital" durante el agregado de unidades de piramide
(dentro de `EN_POSICION`, via `add_trigger`) no se toco: ahi el ticker ya
se muestra como `EN_POSICION`, no hay problema de visibilidad.
