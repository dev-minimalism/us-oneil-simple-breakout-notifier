# William O'Neil Breakout Trading Bot (US Stocks)

**윌리엄 오닐 돌파매매 봇 - 미국 주식 전용 (CAN SLIM)**

미국 주식 시장에서 차트 돌파 패턴(컵앤핸들, 피벗 포인트 돌파, 베이스 돌파)을 자동 감지하고 텔레그램으로 알림을 보내는 자동화 트레이딩 신호 시스템입니다.

## Features

- **패턴 감지**: 컵앤핸들, 피벗 포인트 돌파, 베이스 돌파
- **데이터 소스**: yfinance (미국 주식)
- **스마트 스캔**: 미국 장중 자동 스캔 (22:00-07:00 KST)
- **텔레그램 통합**: 명령어로 종목 관리, 실시간 알림
- **포지션 추적**: 자동 손절(-8%), 익절(+20%), 만료(30일) 알림
- **PostgreSQL 저장**: SSH 터널을 통한 원격 DB 연결, 중복 알림 방지, 스레드 안전
- **자동 로그 롤링**: 한국 시간 자정 기준 일별 로그 파일 생성 (30일 보관)
- **백테스트**: 과거 데이터로 전략 성과 검증

## Installation

```bash
# 가상환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -e .
```

## Quick Start

### 1. 설정

`.env.example`을 복사하여 `.env` 파일을 생성하고 설정을 입력합니다:

```bash
cp .env.example .env
```

`.env` 파일 주요 설정:

```bash
# 텔레그램 (필수)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# PostgreSQL (SSH 터널)
SSH_HOST=your_ssh_host
SSH_USER=your_ssh_user
SSH_KEY_PATH=~/.ssh/your_key
DB_NAME=us_oneil_simple_notifier_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

### 2. 데이터베이스 설정

```bash
python scripts/create_database.py   # DB 및 테이블 생성
python scripts/test_db_connection.py # 연결 테스트
```

### 3. 봇 실행

```bash
python -m us_oneil_simple
```

### 4. 즉시 스캔

```bash
python -m us_oneil_simple scan
```

### 5. 백테스트

```bash
python -m us_oneil_simple backtest --capital 100000
```

---

## Telegram Commands

| 명령어 | 설명 |
|--------|------|
| `/scan` | 즉시 스캔 |
| `/positions` | 현재 포지션 보기 |
| `/close TICKER` | 포지션 수동 청산 |
| `/trades` | 최근 거래 내역 |
| `/stats` | 거래 통계 |
| `/add TICKER` | 종목 추가 |
| `/remove TICKER` | 종목 삭제 |
| `/list` | 감시 종목 목록 |
| `/status` | 시장 상태 확인 |
| `/help` | 도움말 |

### 사용 예시

```
/add NVDA          → 종목 추가
/remove AAPL       → 종목 삭제
/list              → 감시 종목 확인
/status            → 시장 상태 확인
```

---

## Background Execution (nohup)

서버에서 봇을 백그라운드로 실행하는 방법입니다.

### 기본 실행

```bash
# 백그라운드 실행 (권장 - 자동 로그 롤링)
nohup python -m us_oneil_simple > /dev/null 2>&1 &
```

로그 파일은 자동으로 `logs/` 디렉토리에 생성됩니다:
- `logs/bot.log` - 현재 로그
- `logs/bot.log.20241224` - 이전 날짜 로그 (한국 시간 자정 기준 롤링)
- 최대 30일치 자동 보관

### 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/bot.log

# 최근 100줄 확인
tail -100 logs/bot.log

# 에러만 확인
grep -i error logs/bot.log

# 특정 날짜 로그 확인
cat logs/bot.log.20241224

# 최신 로그 파일 목록
ls -lt logs/ | head -5
```

### 프로세스 관리

```bash
# 실행 중인 봇 확인
ps aux | grep us_oneil_simple

# 프로세스 ID 확인
pgrep -f us_oneil_simple

# 봇 종료
pkill -f us_oneil_simple

# 또는 PID로 종료
kill <PID>
```

### 재시작 스크립트

`restart.sh` 파일 생성:

```bash
#!/bin/bash
pkill -f us_oneil_simple
sleep 2
cd /path/to/us-oneil-simple-breakout-notifier
source .venv/bin/activate
nohup python -m us_oneil_simple > /dev/null 2>&1 &
echo "Bot restarted. PID: $!"
```

```bash
chmod +x restart.sh
./restart.sh
```

### systemd 서비스 (권장)

`/etc/systemd/system/us-oneil-bot.service` 파일 생성:

```ini
[Unit]
Description=US O'Neil Breakout Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/us-oneil-simple-breakout-notifier
Environment=PATH=/path/to/us-oneil-simple-breakout-notifier/.venv/bin
ExecStart=/path/to/us-oneil-simple-breakout-notifier/.venv/bin/python -m us_oneil_simple
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable us-oneil-bot
sudo systemctl start us-oneil-bot

# 상태 확인
sudo systemctl status us-oneil-bot

# 로그 확인
sudo journalctl -u us-oneil-bot -f

# 재시작
sudo systemctl restart us-oneil-bot
```

---

## Market Hours (KST)

| 시간대 | 동작 |
|--------|------|
| 22:00 - 07:00 (평일) | 미국 주식 스캔 |
| 그 외 | 대기 (스캔 안함) |

---

## Pattern Detection

### 1. 피벗 포인트 돌파
- 20일 저항선 돌파
- 50% 이상 거래량 증가
- 돌파율 0~5%

### 2. 컵앤핸들
- 12-40% 깊이의 컵 형성
- 12% 미만의 핸들
- 저항선 돌파

### 3. 베이스 돌파
- 횡보 구간(변동성 15% 미만) 후 돌파
- 40% 이상 거래량 증가
- 돌파율 0~7%

---

## Backtest

### CLI로 실행

```bash
python -m us_oneil_simple backtest --capital 100000
python -m us_oneil_simple backtest --start 2024-01-01 --end 2024-12-31
```

### Python API로 실행

```python
from us_oneil_simple import BacktestEngine

engine = BacktestEngine(initial_capital=100_000)  # USD
engine.run_portfolio_backtest(
    tickers=['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA'],
    start_date='2024-01-01',
    end_date='2024-12-31',
    patterns=['pivot', 'base']
)
engine.print_performance_report()
engine.save_results('backtest_results.csv')
```

### 성과 보고서 예시

```
📊 백테스트 성과 보고서
============================================================

💰 자본
   초기 자본:              $100,000
   최종 자본:              $112,500
   총 수익:                 $12,500
   수익률:                   12.50%
   연간 수익률:              12.50%

📈 거래 통계
   총 거래:                     25건
   수익 거래:                   16건
   손실 거래:                    9건
   승률:                       64.00%

📊 패턴별 성과
패턴          거래수     평균수익      승률
----------------------------------------
컵앤핸들          10건      7.20%    70.0%
피벗돌파           8건      9.50%    62.5%
베이스돌파         7건      6.80%    57.1%
```

### 리스크 관리

| 항목 | 기본값 |
|------|--------|
| 손절 | -8% |
| 익절 | +20% |
| 최대 보유 기간 | 30일 |
| 포지션 크기 | 자본의 20% |
| 최대 포지션 | 5개 |

---

## Configuration

`.env` 파일 주요 설정 (전체 목록은 `.env.example` 참조):

```bash
# 텔레그램 (필수)
TELEGRAM_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# PostgreSQL (SSH 터널)
SSH_HOST=your_ssh_host
SSH_USER=your_ssh_user
SSH_KEY_PATH=~/.ssh/your_key
DB_NAME=us_oneil_simple_notifier_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# 스캔 설정
SCAN_INTERVAL=1800        # 30분 (초)

# 패턴 감지 설정
VOLUME_SURGE_MIN=50       # 최소 거래량 증가율 (%)
BREAKOUT_MAX=5            # 최대 돌파율 (%)
CUP_DEPTH_MIN=12          # 컵 최소 깊이 (%)
CUP_DEPTH_MAX=40          # 컵 최대 깊이 (%)

# 거래 설정
STOP_LOSS_PCT=-8.0        # 손절 기준 (%)
TAKE_PROFIT_PCT=20.0      # 익절 기준 (%)
MAX_HOLDING_DAYS=30       # 최대 보유 기간 (일)

# 워치리스트 (콤마로 구분)
US_STOCKS=AAPL,MSFT,NVDA,GOOGL,TSLA
```

---

## Project Structure

```
us-oneil-simple-breakout-notifier/
├── src/us_oneil_simple/
│   ├── __init__.py          # 패키지 진입점
│   ├── __main__.py          # CLI
│   ├── bot/detector.py      # 메인 봇 클래스
│   ├── backtest/engine.py   # 백테스트 엔진
│   ├── config/settings.py   # 설정 관리
│   ├── database/            # PostgreSQL 데이터베이스
│   │   ├── connection.py    # SSH 터널 + DB 연결
│   │   ├── models.py        # Position, Alert 모델
│   │   └── repository.py    # Repository 패턴
│   ├── data/
│   │   └── us_stock.py      # 미국 주식 데이터
│   ├── patterns/
│   │   ├── pivot.py         # 피벗 돌파
│   │   ├── cup_handle.py    # 컵앤핸들
│   │   └── base.py          # 베이스 돌파
│   ├── positions/manager.py # 포지션 관리 (PostgreSQL)
│   ├── watchlist/manager.py # 워치리스트 관리
│   └── telegram/
│       ├── client.py        # 텔레그램 API
│       └── formatter.py     # 메시지 포맷
├── scripts/
│   ├── create_database.py   # DB 생성 스크립트
│   └── test_db_connection.py # DB 연결 테스트
├── .env.example             # 설정 예제
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Python API

```python
from us_oneil_simple import (
    BreakoutDetector,
    BacktestEngine,
    Settings,
    load_settings,
    PositionManager,
    WatchlistManager
)

# 설정 로드
settings = load_settings()

# 봇 실행
detector = BreakoutDetector(settings)
detector.run()

# 또는 1회 스캔만
detector.run_scan()
```

---

## Troubleshooting

### ModuleNotFoundError: No module named 'pkg_resources'

```bash
pip install setuptools
```

### 텔레그램 메시지가 안 옴

1. 봇 토큰 확인
2. Chat ID 확인 (`@userinfobot`에서 확인)
3. 봇에게 먼저 `/start` 메시지 보내기

### SSL 인증서 오류 (macOS)

```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### 너무 많은/잘못된 신호

`.env`에서 조건 강화:

```bash
VOLUME_SURGE_MIN=70   # 50 → 70으로 상향
BREAKOUT_MAX=3        # 5 → 3으로 하향
```

### SSH 터널 연결 실패

1. SSH 키 경로 확인 (`SSH_KEY_PATH`)
2. SSH 서버 접속 가능 여부 확인
3. paramiko 버전 확인: `pip install "paramiko<3.5.0"`

### 데이터베이스 연결 실패

```bash
python scripts/test_db_connection.py  # 연결 테스트
python scripts/create_database.py     # DB 재생성
```

---

## Disclaimer

- 과거 성과는 미래를 보장하지 않습니다
- 백테스트 결과는 슬리피지, 수수료 미포함
- 실제 투자 전 충분한 검토 필요
- 본 소프트웨어 사용으로 인한 손실에 대해 책임지지 않습니다

---

## License

MIT License

## Author

Yungoo Park (developer.ygpark@gmail.com)

## References

- 윌리엄 오닐 저서: "How to Make Money in Stocks"
- CAN SLIM 투자 전략
