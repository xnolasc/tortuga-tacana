#!/bin/bash
SYSTEM_DIR="$HOME/Desktop/Tortuga Crypto Ledger"
cd "$SYSTEM_DIR" || exit 1
python3 crypto_report.py >> crypto_daily_recalc.log 2>&1
