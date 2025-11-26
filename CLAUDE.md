# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil Breakout Trading Bot (윌리엄 오닐 돌파매매 봇) - An automated trading signal detection system that identifies chart breakout patterns (Cup-and-Handle, Pivot Point Breakout, Base Breakout) in both US and Korean stock markets using the CAN SLIM strategy framework.

**Stack:** Python 3.12+, yfinance (US stocks), pykrx (Korean stocks), Telegram Bot API

## Common Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the main trading bot
python oneil_breakout_bot_smart_with_positions.py

# Run backtests
python oneil_backtest.py
python oneil_backtest_2.py

# Test utilities
python test_telegram.py    # Validate Telegram bot setup
python test_kr_stock.py    # Validate Korean stock data fetching
```

## Architecture

### Main Application: `oneil_breakout_bot_smart_with_positions.py`

The `SmartUnifiedBreakoutDetector` class is the core component:

- **Watchlist Management:** Dynamic stock lists loaded from `watchlist.json`, modified via Telegram commands (`/add_us`, `/add_kr`, `/remove_us`, `/remove_kr`)
- **Position Tracking:** Entry/exit tracking with P&L stored in `positions.json`
- **Pattern Detection:** `detect_pivot_breakout()` identifies resistance breakouts with volume surge
- **Market Intelligence:** `get_market_status()` returns Korean (09:00-15:30) and US (22:30-06:00 KST) market hours
- **Threading:** Background Telegram command listener + scan mutex to prevent concurrent scans

### Data Flow

```
Telegram Commands → SmartUnifiedBreakoutDetector
                         ↓
              Data Retrieval (yfinance/pykrx)
                         ↓
              Pattern Detection → Signal Found?
                    ↓                    ↓
                  YES                   NO
                   ↓                    ↓
           Add Position          Log & Skip
           Send Alert
                   ↓
         Periodic Position Check (every 30 min)
                   ↓
         Stop-Loss (-8%) / Take-Profit (+20%) / 30-day Expiry
```

### Key Files

| File | Purpose |
|------|---------|
| `oneil_breakout_bot_smart_with_positions.py` | Main live trading bot |
| `oneil_backtest.py` | Backtesting engine |
| `config.py` | Configuration (Telegram credentials, thresholds, watchlists) |
| `watchlist.json` | Runtime dynamic stock list |
| `positions.json` | Open position tracking (generated at runtime) |

### Configuration (`config.py`)

Critical settings to modify:
- `TELEGRAM_TOKEN` / `CHAT_ID` - Bot credentials
- `US_WATCH_LIST` / `KR_WATCH_LIST` - Default watchlists
- `VOLUME_SURGE_MIN` (50%) - Pivot breakout volume threshold
- `STOP_LOSS_PERCENT` (-7.5%) - Risk management

### Telegram Commands

```
/scan, /scan_kr, /scan_us     - Trigger market scans
/add_us TICKER, /add_kr CODE  - Add to watchlist
/remove_us, /remove_kr        - Remove from watchlist
/list                         - Show watchlist
/positions                    - Show holdings with P&L
/close TICKER                 - Close position
/status                       - Market hours status
```

## Threading Notes

- Main thread: 30-minute scan loop + position checks
- Background daemon: Telegram polling (2-sec interval)
- Manual `/scan` commands spawn daemon threads
- `scan_lock` mutex prevents overlapping scans

## Adding New Features

- **Telegram command:** Add case to `process_command()` method
- **New pattern:** Add `detect_*()` method, integrate into `analyze_us_stock()` / `analyze_kr_stock()`
- **Config option:** Add to `config.py`, read in `main()`
- **Backtest support:** Implement in `BacktestEngine` class in `oneil_backtest.py`