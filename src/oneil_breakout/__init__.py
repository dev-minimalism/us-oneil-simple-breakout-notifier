"""
윌리엄 오닐 돌파매매(CAN SLIM) 통합 알림 시스템
- 시간대별 자동 시장 선택 (한국 장중/미국 장중)
- 텔레그램 명령어로 종목 관리
- 미국 주식 + 한국 주식 통합 지원
- 컵앤핸들, 피벗 포인트, 베이스 돌파 패턴 감지
"""

__version__ = "3.0.0"
__author__ = "Yungoo Park"
__email__ = "ygpark@lendingmachine.co.kr"

# 주요 클래스 노출
from .bot import BreakoutDetector
from .backtest import BacktestEngine
from .config import Settings, load_settings
from .positions import PositionManager
from .watchlist import WatchlistManager

__all__ = [
    'BreakoutDetector',
    'BacktestEngine',
    'Settings',
    'load_settings',
    'PositionManager',
    'WatchlistManager',
]
