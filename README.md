# 🐢 Tortuga Tacana

> Sistema de paper trading algorítmico basado en las reglas originales de los
> **Turtle Traders** de Richard Dennis (1983), aplicado a un pool único de
> **35 mercados**: 26 criptomonedas + 9 acciones tokenizadas, operando en
> tiempo real sobre datos de Binance.

---

## 🇪🇸 Español

### ¿Qué es esto?

Tortuga Tacana es una implementación fiel al diseño original del sistema
Turtle: **un solo pool de capital compartido** entre todos los mercados,
donde el que primero rompe su nivel de entrada se sirve del capital
disponible — exactamente como jugaba el grupo original de Dennis en 1983.
La mayoría de las implementaciones modernas simplifican esto con "cajas"
de capital separadas por ticker; acá se optó deliberadamente por el diseño
más fiel, con todas las consecuencias que eso trae (competencia real por
capital, saturación cuando pocos mercados absorben todo el pool, etc.).

### Cómo funciona

- **System 1**: entrada en ruptura de máximo de 20 días, salida en ruptura
  de mínimo de 10 días.
- **System 2**: entrada en ruptura de máximo de 55 días, salida en ruptura
  de mínimo de 20 días.
- **N (ATR)**: mide volatilidad; determina el stop (`entrada − 2×N`) y el
  tamaño de cada unidad de posición.
- **Pirámide**: hasta 4 unidades por posición, agregando cada 0.5×N de
  avance a favor.
- **Pool único**: todo el capital simulado (actualmente $4,200) es
  compartido entre los 35 mercados — no hay cajas separadas por ticker.
- **Familias de correlación**: los mercados se agrupan automáticamente por
  correlación estadística real (no por categoría de sector), para evitar
  que activos que se mueven igual se coman todo el riesgo del portfolio al
  mismo tiempo.
- **Portfolio heat**: límite global de riesgo abierto en simultáneo.

### Stack técnico

- Python + Binance API (spot + bStocks tokenizados)
- Cron jobs para recálculo diario de niveles y trading cada 3 minutos
- Dashboards HTML servidos localmente (LaunchAgents en macOS)
- 100% paper trading — capital simulado, sin dinero real todavía

### Estado actual

Proyecto activo en desarrollo, actualmente en pausa temporal mientras se
evalúan ajustes de diseño (tamaño de capital vs. cantidad de mercados,
posible sistema alternativo de Dual Moving Average para comparar
resultados con capital limitado).

### 🔧 Instalación

**Requisitos previos:**
- Python 3.9 o superior
- macOS, Linux o Windows (probado en macOS 12 Monterey)
- Una cuenta de Binance (no hace falta API Key para correr en modo
  simulado — el sistema funciona con datos públicos de precio)

**1. Cloná el repositorio:**
```bash
git clone https://github.com/xnolasc/tortuga-tacana.git
cd tortuga-tacana
git checkout pool-real-dennis
```

**2. Creá y activá un entorno virtual:**
```bash
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

**3. Instalá las dependencias:**
```bash
pip install python-binance python-dotenv requests yfinance
```

**4. (Opcional) Configurá tu API Key de Binance** — solo necesario si
querés que el sistema lea tu balance real en modo lectura, en vez del
capital simulado por defecto:
```bash
cp .env.example .env
# editá .env y agregá BINANCE_API_KEY / BINANCE_SECRET_KEY
# (permisos "Enable Reading" únicamente — nunca "Enable Withdrawals")
```

**5. Corré el recálculo de niveles (una vez, antes del primer trade):**
```bash
python3 crypto_report.py
```

**6. Corré el trader (modo prueba manual):**
```bash
python3 crypto_paper_trader.py
```

**7. Levantá el dashboard local:**
```bash
python3 crypto_dashboard.py
# abrí http://localhost:8895 en el navegador
```

Para que el trader corra solo cada cierto tiempo (en vez de ejecutarlo a
mano), se puede automatizar con `cron` (Linux/macOS) o el Programador de
Tareas (Windows) — ver `crontab -e` como referencia.

**Todo corre en modo simulado (paper trading) por defecto.** No se
ejecuta ninguna orden real en Binance a menos que se configure
explícitamente la API Key con permisos de trading — algo que este
proyecto todavía no implementa.

---

## 🇬🇧 English

### What is this?

Tortuga Tacana is a faithful implementation of the original Turtle Trading
system design: **a single shared capital pool** across all markets, where
whichever ticker breaks its entry level first draws from the available
capital — exactly how Dennis's original group traded in 1983. Most modern
implementations simplify this with per-ticker capital boxes; this project
deliberately chose the more faithful design, with all the consequences
that brings (real competition for capital, saturation when a few markets
absorb the whole pool, etc.).

### How it works

- **System 1**: entry on a 20-day high breakout, exit on a 10-day low
  breakout.
- **System 2**: entry on a 55-day high breakout, exit on a 20-day low
  breakout.
- **N (ATR)**: measures volatility; determines the stop (`entry − 2×N`)
  and each position unit's size.
- **Pyramiding**: up to 4 units per position, adding every 0.5×N of
  favorable movement.
- **Single pool**: all simulated capital (currently $4,200) is shared
  across the 35 markets — no per-ticker capital boxes.
- **Correlation families**: markets are grouped automatically by real
  statistical correlation (not by sector label), to prevent assets that
  move together from eating the whole portfolio's risk budget at once.
- **Portfolio heat**: a global cap on simultaneous open risk.

### Tech stack

- Python + Binance API (spot + tokenized bStocks)
- Cron jobs for daily level recalculation and trading every 3 minutes
- HTML dashboards served locally (macOS LaunchAgents)
- 100% paper trading — simulated capital, no real money yet

### Current status

Active project, currently paused temporarily while design adjustments are
evaluated (capital size vs. number of markets, possible alternative Dual
Moving Average system to compare results under limited capital).

### 🔧 Installation

**Prerequisites:**
- Python 3.9 or higher
- macOS, Linux, or Windows (tested on macOS 12 Monterey)
- A Binance account (no API Key required to run in simulated mode — the
  system works with public price data)

**1. Clone the repository:**
```bash
git clone https://github.com/xnolasc/tortuga-tacana.git
cd tortuga-tacana
git checkout pool-real-dennis
```

**2. Create and activate a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

**3. Install dependencies:**
```bash
pip install python-binance python-dotenv requests yfinance
```

**4. (Optional) Configure your Binance API Key** — only needed if you
want the system to read your real balance in read-only mode, instead of
the default simulated capital:
```bash
cp .env.example .env
# edit .env and add BINANCE_API_KEY / BINANCE_SECRET_KEY
# ("Enable Reading" permission only — never "Enable Withdrawals")
```

**5. Run the level recalculation (once, before the first trade):**
```bash
python3 crypto_report.py
```

**6. Run the trader (manual test run):**
```bash
python3 crypto_paper_trader.py
```

**7. Start the local dashboard:**
```bash
python3 crypto_dashboard.py
# open http://localhost:8895 in your browser
```

To have the trader run automatically on a schedule (instead of running it
manually), it can be automated with `cron` (Linux/macOS) or Task
Scheduler (Windows) — see `crontab -e` for reference.

**Everything runs in simulated mode (paper trading) by default.** No real
order is ever placed on Binance unless the API Key is explicitly
configured with trading permissions — something this project does not
implement yet.

---

*Basado en / Based on: Curtis Faith, "Way of the Turtle" — reglas
originales de Richard Dennis y William Eckhardt, 1983.*
