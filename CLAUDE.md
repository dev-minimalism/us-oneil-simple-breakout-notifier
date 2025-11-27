# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil Breakout Trading Bot (윌리엄 오닐 돌파매매 봇) - An automated trading signal detection system that identifies chart breakout patterns (Cup-and-Handle, Pivot Point Breakout, Base Breakout) in US stock markets using the CAN SLIM strategy framework.

**Stack:** Python 3.12+, yfinance (US stocks), PostgreSQL (SSH tunnel), Telegram Bot API

## Common Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e .                    # Install as editable package

# Run the main trading bot
python -m us_oneil_simple            # Full bot with Telegram listener

# Run a single scan (no loop)
python -m us_oneil_simple scan

# Run backtests
python -m us_oneil_simple backtest --capital 100000
python -m us_oneil_simple backtest --start 2024-01-01 --end 2024-12-31

# Database scripts
python scripts/create_database.py   # Create PostgreSQL database and tables
python scripts/test_db_connection.py # Test database connection

# Development tools
ruff check src/                     # Lint
black src/                          # Format
mypy src/                           # Type check
pytest                              # Run tests
```

## Architecture

### Package Structure (`src/us_oneil_simple/`)

The codebase follows a modular architecture:

```
src/us_oneil_simple/
├── __main__.py          # CLI entry point (run/scan/backtest commands)
├── bot/detector.py      # BreakoutDetector - main orchestrator class
├── backtest/engine.py   # BacktestEngine - historical testing
├── config/settings.py   # Settings dataclasses + load_settings()
├── database/            # PostgreSQL database (SSH tunnel support)
│   ├── connection.py    # DatabaseConnection - SSH tunnel + DB connection
│   ├── models.py        # Position, Alert dataclasses
│   └── repository.py    # PositionRepository, AlertRepository
├── data/us_stock.py     # yfinance data fetching
├── patterns/            # Pattern detection algorithms
│   ├── pivot.py         # detect_pivot_breakout()
│   ├── cup_handle.py    # detect_cup_and_handle()
│   └── base.py          # detect_base_breakout()
├── positions/manager.py # PositionManager - entry/exit tracking (PostgreSQL backend)
├── watchlist/manager.py # WatchlistManager - dynamic stock list
├── telegram/
│   ├── client.py        # TelegramClient - API wrapper
│   └── formatter.py     # Message formatting functions
└── market/status.py     # Market hours detection (US: 22:00-07:00 KST)
```

### Core Classes

- **`BreakoutDetector`** (`bot/detector.py`): Main orchestrator that ties everything together. Handles Telegram commands, runs scans, manages positions.
- **`BacktestEngine`** (`backtest/engine.py`): Simulates historical trading with stop-loss/take-profit logic.
- **`Settings`** (`config/settings.py`): Dataclass hierarchy for all configuration. Loads from `.env` file.
- **`PositionManager`** (`positions/manager.py`): Tracks open positions in PostgreSQL with automatic stop-loss (-8%), take-profit (+20%), and 30-day expiry.
- **`DatabaseConnection`** (`database/connection.py`): Manages SSH tunnel and PostgreSQL connection.
- **`AlertRepository`** (`database/repository.py`): Tracks sent alerts to prevent duplicates (same ticker/pattern/day).

### Data Flow

```
Telegram Commands → BreakoutDetector.process_command()
                         ↓
              Data: get_us_stock_data() (yfinance)
                         ↓
              Pattern: detect_pivot_breakout() → Signal?
                    ↓                              ↓
                  YES                             NO
                   ↓                              ↓
           Check: can_send_alert()?          Skip
                   ↓
           AlertRepository.add() (prevent duplicates)
           TelegramClient.send_message()
           PositionManager.add()
                   ↓
         Periodic check_positions() (every 30 min)
                   ↓
         Exit on: stop-loss / take-profit / 30-day expiry
```

### Configuration

All settings are loaded from `.env` file via `load_settings()`.

Key environment variables (see `.env.example` for full list):
- `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` - Required for Telegram integration
- `SSH_HOST`, `SSH_USER`, `SSH_KEY_PATH` - SSH tunnel for PostgreSQL
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL credentials
- `SCAN_INTERVAL` - Scan period in seconds (default: 1800)
- `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT`, `MAX_HOLDING_DAYS` - Risk management
- `VOLUME_SURGE_MIN`, `BREAKOUT_MAX` - Pattern detection thresholds
- `US_STOCKS` - Watchlist (comma-separated)

### Telegram Commands

```
/scan          - Trigger immediate market scan
/positions     - Show current holdings with P&L
/close TICKER  - Manually close a position
/add TICKER    - Add stock to watchlist
/remove TICKER - Remove from watchlist
/list          - Show watchlist
/status        - Show market hours status
/help          - Show all commands
```

## Threading Model

- **Main thread**: 30-minute scan loop (`run()` → `run_smart_scan()`)
- **Daemon thread**: Telegram polling every 2 seconds (`start_command_listener()`)
- **On-demand threads**: `/scan` command spawns daemon thread for manual scans
- **`scan_lock`**: Mutex prevents overlapping scans

## Adding New Features

- **New Telegram command**: Add case in `BreakoutDetector.process_command()`
- **New pattern detector**: Add function in `patterns/`, call from `analyze_stock()`
- **New config option**: Add field to appropriate dataclass in `config/settings.py`, handle in `load_settings()`
- **New database table**: Add model in `database/models.py`, repository in `database/repository.py`, update `connection.py` init_tables()
- **Backtest pattern**: Add detection method in `BacktestEngine`, call from `run_backtest()`
