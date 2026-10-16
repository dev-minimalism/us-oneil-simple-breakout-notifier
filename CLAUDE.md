# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

William O'Neil Breakout Trading Bot (윌리엄 오닐 돌파매매 봇) - a Telegram signal bot that scans a US stock watchlist for breakout patterns (CAN SLIM) and tracks paper positions in PostgreSQL. It never places orders.

Everything user-facing is Korean: Telegram messages, log output, docstrings, comments, and commit messages (`fix:`, `feat:`, `docs:`, `chore:` prefixes). Keep that convention.

**Stack:** Python 3.12+, yfinance, PostgreSQL over an SSH tunnel (`sshtunnel` + `psycopg2`), Telegram Bot API called directly with `requests` (no bot framework).

## Common Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .                      # pyproject.toml is canonical; requirements.txt is stale
pip install -e ".[dev]"               # ruff / black / mypy / pytest (not installed by default)

python -m us_oneil_simple             # Full bot: Telegram listener + scheduled scans
python -m us_oneil_simple scan        # One scan, then exit
python -m us_oneil_simple backtest --capital 100000 --start 2024-01-01 --end 2024-12-31

python scripts/create_database.py     # Create DB + tables through the SSH tunnel
python scripts/test_db_connection.py  # Verify tunnel + DB
python scripts/test_close_position.py # Exercises close logic against the REAL DB (rolls back)

ruff check src/ && black src/ && mypy src/
pytest                                # Configured (testpaths=tests) but no tests/ directory exists yet
```

**What each command needs:** `run` and `scan` both construct `PositionManager`, which opens the SSH tunnel and calls `init_tables()` immediately. Neither can start without a `.env` and reachable PostgreSQL. `run` additionally exits if `TELEGRAM_TOKEN` is unset. `backtest` needs neither DB nor Telegram, only yfinance.

The `scripts/test_*.py` files are manual DB checks, not pytest tests.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`: it SSHes to the server, `pkill`s the running bot, does `git reset --hard origin/main` and checks out `main`, runs `pip install -e .`, and restarts with `setsid nohup .venv/bin/python3 -u -m us_oneil_simple`. **`main` is the only branch and it is production.** Every push to it, including docs-only commits, restarts the bot and sends a "bot started" Telegram message.

## Architecture

### Package map (`src/us_oneil_simple/`)

```
__main__.py            CLI; calls setup_logging() first, then dispatches run / scan / backtest
bot/detector.py        BreakoutDetector: Telegram commands, scan loop, position exit checks
backtest/engine.py     BacktestEngine: standalone, no DB or Telegram
config/settings.py     Settings dataclasses + load_settings() (.env -> os.environ -> dataclass)
config/logging.py      KST daily-rolling file log; redirects sys.stdout/stderr into logging
database/              DatabaseConnection (tunnel + RLock + retry), Position/Alert models, repositories
data/us_stock.py       yfinance fetchers (by period, by date range)
patterns/              pivot.py (live + backtest); cup_handle.py, base.py (backtest-style only)
positions/manager.py   PositionManager: PostgreSQL-backed positions + alert dedupe
watchlist/manager.py   WatchlistManager: file-backed (watchlist.json in the working directory)
market/status.py       Session detection + fixed :02/:32 scan schedule
telegram/              TelegramClient (requests + retry/backoff), message formatters
```

### Scan loop and scheduling

- `run()` sleeps until the next `:02` or `:32` minute mark (`market/status.get_next_scan_time`) and then calls `run_smart_scan()`. `SCAN_INTERVAL` and `REQUEST_DELAY` are parsed into `settings.scan` but **nothing reads them**.
- `run_smart_scan()`: skip if a manual scan is running -> skip if market closed -> `check_positions()` (exit checks) -> `run_scan()`.
- "Market open" means any of four KST sessions: 데이마켓 10:00-17:50, 프리마켓 18:00-23:30, 정규장 23:30-06:00, 애프터마켓 06:00-09:50. Scans therefore run almost around the clock on weekdays. Closed from Saturday 09:50 through Sunday. Times are fixed KST clock times from local `datetime.now()`; there is no US DST adjustment and the host is assumed to be in KST.
- `/scan` from Telegram spawns a daemon thread guarded by `scan_lock` and the `is_scanning` flag. The scheduled loop only checks `is_scanning`; it does not take the lock. Manual scans skip `check_positions()` and are the only scans that send a "no signal" message.

### Which patterns actually run

- **The live bot detects only pivot breakout.** `analyze_stock()` calls `detect_pivot_breakout` alone, and `format_signal_message` is hardcoded for it.
- `patterns/cup_handle.py` and `patterns/base.py` use the backtest signature `(df, idx, ...) -> (bool, resistance)`, not the live signature `(df, ticker, market, **thresholds) -> signal dict | None`. They are not wired into the live scan.
- `BacktestEngine` carries its **own inline copies** of cup-and-handle and base detection with hardcoded thresholds and imports only `detect_pivot_breakout_at_index` (also hardcoded at 50% volume / 5% breakout). `PatternSettings` from `.env` affect the live pivot scan only; the backtest ignores them.
- To add a live pattern: write a live-signature function in `patterns/`, append it in `analyze_stock()`, and make `format_signal_message` branch on `signal['pattern']`.

### Signal dict and pattern names

`detect_pivot_breakout` returns `{'ticker','pattern','market','resistance','current_price','breakout_pct','volume_surge'}` with values cast to Python `float`. numpy scalars break JSON and psycopg2; `repository._convert_numpy_types` is the safety net for the `signal_data` JSONB column. Pattern names are Korean strings (`'피벗돌파'`, `'컵앤핸들'`, `'베이스돌파'`), stored in the `pattern` column, and form part of the alert dedupe key `(ticker, pattern, alert_date)`.

### Persistence

- Positions and alerts live in PostgreSQL. The watchlist lives in `watchlist.json` next to the process (gitignored). `positions.json` / `POSITIONS_FILE` are legacy and unused.
- `get_db_connection()` is a module-level singleton that reads `os.environ` directly, **not** `settings.database`. It works because `load_settings()` has already called `load_dotenv()`; standalone scripts must call `load_dotenv()` themselves (see `scripts/`).
- Schema is created by `DatabaseConnection.init_tables()` on every `PositionManager` start (idempotent `CREATE ... IF NOT EXISTS`). Treat that as canonical. `scripts/create_database.py` adds an older `UNIQUE (ticker, status)` constraint that would block a second closed position for the same ticker; `init_tables()` instead uses a partial unique index on `ticker WHERE status = 'open'`.
- `DatabaseConnection` serializes every query behind an `RLock`, pings with `SELECT 1`, and rebuilds tunnel + connection on `OperationalError` / `InterfaceError` (3 attempts). Non-connection exceptions are re-raised immediately.

### Write-before-notify rule

Every Telegram message that reflects a state change is sent only **after** the DB write succeeds:

- Signal: `has_position` -> `can_send_alert` (returns False on any DB error) -> `record_alert` (`INSERT ... ON CONFLICT DO NOTHING`) -> send message -> `positions.add`.
- Close: `positions.close_position` (`UPDATE ... RETURNING id`) -> send message. A no-op UPDATE returns False and nothing is sent.

Keep this order when touching alert or position code; it is what prevents duplicate and phantom alerts.

### Exit logic

`PositionManager.check_exit_conditions` checks stop-loss, take-profit, then holding-day expiry. Stop-loss exits at the stored `stop_loss` price rather than the current price; the other two exit at current price. Defaults come from `TradingSettings` (-8% / +20% / 30 days). `check_positions()` fetches a fresh 5-day history per open position, one second apart.

### Logging

`setup_logging()` replaces `sys.stdout` and `sys.stderr` with a `LoggerWriter`, so the whole codebase uses `print()` and output lands in `logs/bot.log` with KST-midnight rotation and 30 days retained. `print()` is the convention; don't introduce `logging.getLogger` calls just for consistency's sake.

### Telegram

`TelegramClient.get_updates` advances `last_update_id` for every update but only returns messages from the configured `TELEGRAM_CHAT_ID`, so messages from other chats are consumed and ignored. `process_command` returns the sentinel string `'SCAN'` to make the listener spawn a scan thread; any other string is sent back as the reply. All messages use HTML `parse_mode`. The persistent reply keyboard is defined in `DEFAULT_KEYBOARD`.

## Configuration

`load_settings()` locates `.env` by walking up from `config/settings.py`, loads it, then overrides dataclass defaults from `os.environ`. `.env.example` lists every key. `US_STOCKS` only seeds the watchlist when `watchlist.json` is absent; once the file exists it wins. The backtest CLI uses the first 20 tickers of `US_STOCKS` from settings, not `watchlist.json`, and writes `us_backtest_results.csv`.

## Gotchas

- `paramiko` is pinned `>=3.0,<4.0` because 4.0 removed `DSSKey`, which `sshtunnel` still imports.
- `pykrx` and the `market='KR'` branches are leftovers from an earlier Korea-market version. The bot is US-only.
- ruff and black use line length 100; ruff ignores E501.
