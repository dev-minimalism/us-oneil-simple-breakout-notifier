"""설정 관리 (미국 주식 전용)"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass
class TelegramSettings:
    """텔레그램 설정"""
    token: str = ""
    chat_id: str = ""


@dataclass
class PatternSettings:
    """패턴 감지 설정"""
    # 피벗 돌파
    volume_surge_min: float = 50.0
    breakout_max: float = 5.0

    # 컵앤핸들
    cup_depth_min: float = 12.0
    cup_depth_max: float = 40.0
    handle_depth_max: float = 12.0

    # 베이스 돌파
    base_volatility_max: float = 15.0
    base_volume_surge_min: float = 40.0
    base_breakout_max: float = 7.0


@dataclass
class TradingSettings:
    """거래 설정"""
    stop_loss_pct: float = -8.0
    take_profit_pct: float = 20.0
    max_holding_days: int = 30
    max_positions: int = 5
    position_size_pct: float = 20.0  # 각 포지션 크기 (자본 대비 %)


@dataclass
class ScanSettings:
    """스캔 설정"""
    interval_seconds: int = 1800  # 30분
    request_delay: float = 1.0


@dataclass
class DataSettings:
    """데이터 설정"""
    analysis_period: str = "6mo"  # 분석 기간


@dataclass
class WatchlistSettings:
    """워치리스트 기본값"""
    us_stocks: List[str] = field(default_factory=lambda: [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META",
        "NVDA", "AMD", "AVGO",
        "TSLA", "NFLX", "CRM", "ADBE",
        "PLTR", "SNOW", "CRWD", "NET", "DDOG", "ZS",
        "COIN", "SQ", "PYPL",
        "SHOP"
    ])


@dataclass
class DatabaseSettings:
    """PostgreSQL 데이터베이스 설정 (SSH 터널 지원)"""
    # SSH 터널 설정
    ssh_host: str = ""
    ssh_port: int = 22
    ssh_user: str = ""
    ssh_key_path: str = "~/.ssh/id_rsa"

    # PostgreSQL 설정
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""


@dataclass
class Settings:
    """전체 설정"""
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pattern: PatternSettings = field(default_factory=PatternSettings)
    trading: TradingSettings = field(default_factory=TradingSettings)
    scan: ScanSettings = field(default_factory=ScanSettings)
    data: DataSettings = field(default_factory=DataSettings)
    watchlist: WatchlistSettings = field(default_factory=WatchlistSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)

    # 파일 경로
    watchlist_file: str = "watchlist.json"
    positions_file: str = "positions.json"


def _find_env_file() -> Path | None:
    """프로젝트 루트에서 .env 파일 찾기"""
    # 현재 파일 기준으로 프로젝트 루트 탐색
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        env_path = parent / ".env"
        if env_path.exists():
            return env_path
    return None


def load_settings() -> Settings:
    """
    설정 로드 (.env 파일 우선, 환경 변수 지원)

    우선순위:
        1. .env 파일 (프로젝트 루트)
        2. 시스템 환경 변수

    환경변수:
        TELEGRAM_TOKEN: 텔레그램 봇 토큰
        TELEGRAM_CHAT_ID: 텔레그램 채팅 ID
        SCAN_INTERVAL: 스캔 주기 (초)
        STOP_LOSS_PCT: 손절 비율 (%)
        TAKE_PROFIT_PCT: 익절 비율 (%)
        MAX_HOLDING_DAYS: 최대 보유 기간 (일)
        VOLUME_SURGE_MIN: 거래량 급증 최소 비율 (%)
        BREAKOUT_MAX: 돌파 최대 비율 (%)

    Returns:
        Settings 인스턴스
    """
    # .env 파일 로드
    env_path = _find_env_file()
    if env_path:
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드: {env_path}")
    else:
        # 현재 작업 디렉토리에서도 시도
        load_dotenv()

    settings = Settings()

    # 환경 변수에서 로드
    # 텔레그램 설정
    if os.environ.get('TELEGRAM_TOKEN'):
        settings.telegram.token = os.environ['TELEGRAM_TOKEN']
    if os.environ.get('TELEGRAM_CHAT_ID'):
        settings.telegram.chat_id = os.environ['TELEGRAM_CHAT_ID']

    # 스캔 설정
    if os.environ.get('SCAN_INTERVAL'):
        settings.scan.interval_seconds = int(os.environ['SCAN_INTERVAL'])
    if os.environ.get('REQUEST_DELAY'):
        settings.scan.request_delay = float(os.environ['REQUEST_DELAY'])

    # 거래 설정
    if os.environ.get('STOP_LOSS_PCT'):
        settings.trading.stop_loss_pct = float(os.environ['STOP_LOSS_PCT'])
    if os.environ.get('TAKE_PROFIT_PCT'):
        settings.trading.take_profit_pct = float(os.environ['TAKE_PROFIT_PCT'])
    if os.environ.get('MAX_HOLDING_DAYS'):
        settings.trading.max_holding_days = int(os.environ['MAX_HOLDING_DAYS'])
    if os.environ.get('MAX_POSITIONS'):
        settings.trading.max_positions = int(os.environ['MAX_POSITIONS'])
    if os.environ.get('POSITION_SIZE_PCT'):
        settings.trading.position_size_pct = float(os.environ['POSITION_SIZE_PCT'])

    # 패턴 설정 - 피벗 돌파
    if os.environ.get('VOLUME_SURGE_MIN'):
        settings.pattern.volume_surge_min = float(os.environ['VOLUME_SURGE_MIN'])
    if os.environ.get('BREAKOUT_MAX'):
        settings.pattern.breakout_max = float(os.environ['BREAKOUT_MAX'])

    # 패턴 설정 - 컵앤핸들
    if os.environ.get('CUP_DEPTH_MIN'):
        settings.pattern.cup_depth_min = float(os.environ['CUP_DEPTH_MIN'])
    if os.environ.get('CUP_DEPTH_MAX'):
        settings.pattern.cup_depth_max = float(os.environ['CUP_DEPTH_MAX'])
    if os.environ.get('HANDLE_DEPTH_MAX'):
        settings.pattern.handle_depth_max = float(os.environ['HANDLE_DEPTH_MAX'])

    # 패턴 설정 - 베이스 돌파
    if os.environ.get('BASE_VOLATILITY_MAX'):
        settings.pattern.base_volatility_max = float(os.environ['BASE_VOLATILITY_MAX'])
    if os.environ.get('BASE_VOLUME_SURGE_MIN'):
        settings.pattern.base_volume_surge_min = float(os.environ['BASE_VOLUME_SURGE_MIN'])
    if os.environ.get('BASE_BREAKOUT_MAX'):
        settings.pattern.base_breakout_max = float(os.environ['BASE_BREAKOUT_MAX'])

    # 데이터 설정
    if os.environ.get('ANALYSIS_PERIOD'):
        settings.data.analysis_period = os.environ['ANALYSIS_PERIOD']

    # 워치리스트 설정 (콤마로 구분된 문자열)
    if os.environ.get('US_STOCKS'):
        stocks = [s.strip() for s in os.environ['US_STOCKS'].split(',') if s.strip()]
        if stocks:
            settings.watchlist.us_stocks = stocks

    # 파일 경로 설정
    if os.environ.get('WATCHLIST_FILE'):
        settings.watchlist_file = os.environ['WATCHLIST_FILE']
    if os.environ.get('POSITIONS_FILE'):
        settings.positions_file = os.environ['POSITIONS_FILE']

    # 데이터베이스 설정
    if os.environ.get('SSH_HOST'):
        settings.database.ssh_host = os.environ['SSH_HOST']
    if os.environ.get('SSH_PORT'):
        settings.database.ssh_port = int(os.environ['SSH_PORT'])
    if os.environ.get('SSH_USER'):
        settings.database.ssh_user = os.environ['SSH_USER']
    if os.environ.get('SSH_KEY_PATH'):
        settings.database.ssh_key_path = os.environ['SSH_KEY_PATH']
    if os.environ.get('DB_HOST'):
        settings.database.db_host = os.environ['DB_HOST']
    if os.environ.get('DB_PORT'):
        settings.database.db_port = int(os.environ['DB_PORT'])
    if os.environ.get('DB_NAME'):
        settings.database.db_name = os.environ['DB_NAME']
    if os.environ.get('DB_USER'):
        settings.database.db_user = os.environ['DB_USER']
    if os.environ.get('DB_PASSWORD'):
        settings.database.db_password = os.environ['DB_PASSWORD']

    return settings