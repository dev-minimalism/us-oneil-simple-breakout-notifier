"""포지션 관리자 (PostgreSQL 지원)"""
import json
import os
from datetime import datetime
from typing import Dict, List, Callable

from ..database import DatabaseConnection, PositionRepository, AlertRepository, get_db_connection


class PositionManager:
    """포지션 관리 클래스 (PostgreSQL 백엔드)"""

    def __init__(
        self,
        positions_file: str = "positions.json",  # fallback용 (더 이상 사용 안함)
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30,
        db: DatabaseConnection | None = None,
    ):
        """
        Args:
            positions_file: (레거시) 포지션 저장 파일 경로
            stop_loss_pct: 손절 기준 (%)
            take_profit_pct: 익절 기준 (%)
            max_holding_days: 최대 보유 기간 (일)
            db: 데이터베이스 연결 (None이면 자동 생성)
        """
        self.positions_file = positions_file
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_days = max_holding_days

        # 데이터베이스 연결
        self.db = db or get_db_connection()
        self.db.init_tables()  # 테이블 초기화

        # Repository
        self.position_repo = PositionRepository(self.db)
        self.alert_repo = AlertRepository(self.db)

        print(f"  PostgreSQL 포지션 관리자 초기화 완료")

    def add(
        self,
        ticker: str,
        market: str,
        entry_price: float,
        pattern: str,
        signal: Dict
    ) -> Dict | None:
        """
        포지션 추가

        Args:
            ticker: 종목 코드
            market: 시장 ('US' 또는 'KR')
            entry_price: 진입가
            pattern: 패턴명
            signal: 신호 딕셔너리

        Returns:
            추가된 포지션 딕셔너리 또는 None (이미 존재 시)
        """
        stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
        take_profit = entry_price * (1 + self.take_profit_pct / 100)

        position = self.position_repo.add(
            ticker=ticker,
            market=market,
            entry_price=entry_price,
            pattern=pattern,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_data=signal,
        )

        if position:
            print(f"  📝 포지션 추가: {ticker} @ {entry_price}")
            return position.to_dict()
        else:
            print(f"  ⚠️ 포지션 추가 실패 (이미 존재): {ticker}")
            return None

    def remove(self, ticker: str) -> bool:
        """
        포지션 제거

        Args:
            ticker: 종목 코드

        Returns:
            제거 성공 여부
        """
        return self.position_repo.remove(ticker)

    def close_position(
        self,
        ticker: str,
        exit_price: float,
        exit_reason: str,
        profit_pct: float
    ) -> bool:
        """
        포지션 청산

        Args:
            ticker: 종목 코드
            exit_price: 청산가
            exit_reason: 청산 사유
            profit_pct: 수익률

        Returns:
            청산 성공 여부
        """
        return self.position_repo.close(ticker, exit_price, exit_reason, profit_pct)

    def get(self, ticker: str) -> Dict | None:
        """
        특정 종목 포지션 조회

        Args:
            ticker: 종목 코드

        Returns:
            포지션 딕셔너리 또는 None
        """
        position = self.position_repo.get_by_ticker(ticker)
        if position:
            return position.to_dict()
        return None

    def has_position(self, ticker: str) -> bool:
        """
        특정 종목 포지션 보유 여부

        Args:
            ticker: 종목 코드

        Returns:
            보유 여부
        """
        return self.position_repo.has_position(ticker)

    def get_all(self) -> List[Dict]:
        """모든 열린 포지션 조회"""
        positions = self.position_repo.get_all_open()
        return [p.to_dict() for p in positions]

    def count(self) -> int:
        """포지션 개수"""
        return self.position_repo.count_open()

    def check_exit_conditions(
        self,
        position: Dict,
        current_price: float
    ) -> tuple[bool, float, str]:
        """
        청산 조건 확인

        Args:
            position: 포지션 딕셔너리
            current_price: 현재가

        Returns:
            (청산여부, 청산가, 청산사유)
        """
        entry_date_str = position.get('entry_date')
        if isinstance(entry_date_str, str):
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d %H:%M:%S')
        else:
            entry_date = entry_date_str

        holding_days = (datetime.now() - entry_date).days

        stop_loss = position.get('stop_loss', 0)
        take_profit = position.get('take_profit', float('inf'))

        # 손절 확인
        if stop_loss and current_price <= stop_loss:
            return True, stop_loss, f'손절 ({self.stop_loss_pct}%)'

        # 익절 확인
        if take_profit and current_price >= take_profit:
            return True, current_price, f'익절 (+{self.take_profit_pct}%)'

        # 보유기간 만료 확인
        if holding_days >= self.max_holding_days:
            return True, current_price, f'보유기간 만료 ({holding_days}일)'

        return False, current_price, ''

    def calculate_profit(self, position: Dict, current_price: float) -> tuple[float, int]:
        """
        수익률 계산

        Args:
            position: 포지션 딕셔너리
            current_price: 현재가

        Returns:
            (수익률, 보유일수)
        """
        entry_price = position['entry_price']
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        entry_date_str = position.get('entry_date')
        if isinstance(entry_date_str, str):
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d %H:%M:%S')
        else:
            entry_date = entry_date_str

        holding_days = (datetime.now() - entry_date).days
        return profit_pct, holding_days

    # ========================================
    # 중복 알림 방지
    # ========================================

    def can_send_alert(self, ticker: str, pattern: str) -> bool:
        """
        알림 발송 가능 여부 (오늘 동일 알림이 없으면 True)

        Args:
            ticker: 종목 코드
            pattern: 패턴명

        Returns:
            알림 발송 가능 여부
        """
        return not self.alert_repo.has_alert_today(ticker, pattern)

    def record_alert(
        self,
        ticker: str,
        market: str,
        pattern: str,
        alert_price: float,
        signal_data: Dict | None = None
    ) -> bool:
        """
        알림 기록 저장 (중복 방지용)

        Args:
            ticker: 종목 코드
            market: 시장
            pattern: 패턴명
            alert_price: 알림 가격
            signal_data: 신호 데이터

        Returns:
            저장 성공 여부
        """
        alert = self.alert_repo.add(
            ticker=ticker,
            market=market,
            pattern=pattern,
            alert_price=alert_price,
            signal_data=signal_data,
        )
        return alert is not None

    def get_today_alerts(self) -> List[Dict]:
        """오늘 발송된 모든 알림 조회"""
        alerts = self.alert_repo.get_today_alerts()
        return [a.to_dict() for a in alerts]

    # ========================================
    # 포맷팅
    # ========================================

    def format_list_message(
        self,
        get_current_price: Callable[[str, str], float | None]
    ) -> str:
        """
        포지션 목록 메시지 포맷팅

        Args:
            get_current_price: 현재가 조회 함수 (ticker, market) -> price

        Returns:
            포맷된 HTML 메시지
        """
        positions = self.get_all()

        if not positions:
            return "📊 <b>현재 포지션</b>\n\n보유 중인 포지션이 없습니다."

        msg = f"📊 <b>현재 포지션</b> ({len(positions)}개)\n\n"

        for i, pos in enumerate(positions, 1):
            ticker = pos['ticker']
            market_emoji = "🇺🇸" if pos['market'] == 'US' else "🇰🇷"

            entry_date_str = pos.get('entry_date')
            if isinstance(entry_date_str, str):
                entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d %H:%M:%S')
            else:
                entry_date = entry_date_str

            holding_days = (datetime.now() - entry_date).days

            # 현재가 조회 시도
            try:
                current_price = get_current_price(ticker, pos['market'])
                if current_price:
                    profit_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                    profit_icon = "📈" if profit_pct > 0 else "📉"
                    current_info = f"{current_price:,.2f} ({profit_icon}{profit_pct:+.2f}%)"
                else:
                    current_info = "조회 실패"
            except:
                current_info = "조회 실패"

            stop_loss = pos.get('stop_loss', 0)
            take_profit = pos.get('take_profit', 0)

            msg += f"""
{i}. {market_emoji} <b>{ticker}</b>
   진입: {pos['entry_price']:,.2f}
   현재: {current_info}
   패턴: {pos['pattern']}
   보유: {holding_days}일
   손절: {stop_loss:,.2f}
   익절: {take_profit:,.2f}
"""

        return msg