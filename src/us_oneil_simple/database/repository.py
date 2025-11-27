"""데이터베이스 Repository"""
import json
from datetime import datetime, date
from typing import List

from .connection import DatabaseConnection
from .models import Position, Alert


class PositionRepository:
    """포지션 데이터베이스 Repository"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def add(
        self,
        ticker: str,
        market: str,
        entry_price: float,
        pattern: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        signal_data: dict | None = None,
    ) -> Position | None:
        """포지션 추가 (이미 open 상태인 포지션이 있으면 None 반환)"""
        # 먼저 open 포지션이 있는지 확인
        if self.has_position(ticker):
            return None

        query = """
            INSERT INTO positions (ticker, market, entry_price, pattern, stop_loss, take_profit, signal_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
            RETURNING *
        """
        result = self.db.execute_one(
            query,
            (ticker, market, entry_price, pattern, stop_loss, take_profit, json.dumps(signal_data) if signal_data else None)
        )
        if result:
            return Position.from_dict(dict(result))
        return None

    def get_by_ticker(self, ticker: str, status: str = "open") -> Position | None:
        """티커로 포지션 조회"""
        query = "SELECT * FROM positions WHERE ticker = %s AND status = %s"
        result = self.db.execute_one(query, (ticker, status))
        if result:
            return Position.from_dict(dict(result))
        return None

    def get_all_open(self) -> List[Position]:
        """모든 열린 포지션 조회"""
        query = "SELECT * FROM positions WHERE status = 'open' ORDER BY entry_date DESC"
        results = self.db.execute(query)
        return [Position.from_dict(dict(r)) for r in results]

    def get_all(self, status: str | None = None) -> List[Position]:
        """모든 포지션 조회"""
        if status:
            query = "SELECT * FROM positions WHERE status = %s ORDER BY entry_date DESC"
            results = self.db.execute(query, (status,))
        else:
            query = "SELECT * FROM positions ORDER BY entry_date DESC"
            results = self.db.execute(query)
        return [Position.from_dict(dict(r)) for r in results]

    def has_position(self, ticker: str) -> bool:
        """포지션 보유 여부 확인"""
        query = "SELECT 1 FROM positions WHERE ticker = %s AND status = 'open' LIMIT 1"
        result = self.db.execute_one(query, (ticker,))
        return result is not None

    def count_open(self) -> int:
        """열린 포지션 개수"""
        query = "SELECT COUNT(*) as cnt FROM positions WHERE status = 'open'"
        result = self.db.execute_one(query)
        return result['cnt'] if result else 0

    def close(
        self,
        ticker: str,
        exit_price: float,
        exit_reason: str,
        profit_pct: float,
    ) -> bool:
        """포지션 청산"""
        query = """
            UPDATE positions
            SET status = 'closed',
                exit_price = %s,
                exit_date = CURRENT_TIMESTAMP,
                exit_reason = %s,
                profit_pct = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticker = %s AND status = 'open'
        """
        self.db.execute(query, (exit_price, exit_reason, profit_pct, ticker))
        return True

    def remove(self, ticker: str) -> bool:
        """포지션 삭제 (청산 처리)"""
        return self.close(ticker, 0, '수동 삭제', 0)


class AlertRepository:
    """알림 기록 Repository (중복 알림 방지)"""

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def add(
        self,
        ticker: str,
        market: str,
        pattern: str,
        alert_price: float,
        signal_data: dict | None = None,
    ) -> Alert | None:
        """알림 기록 추가"""
        query = """
            INSERT INTO alerts (ticker, market, pattern, alert_date, alert_price, signal_data)
            VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)
            ON CONFLICT (ticker, pattern, alert_date) DO NOTHING
            RETURNING *
        """
        result = self.db.execute_one(
            query,
            (ticker, market, pattern, alert_price, json.dumps(signal_data) if signal_data else None)
        )
        if result:
            return Alert.from_dict(dict(result))
        return None

    def has_alert_today(self, ticker: str, pattern: str) -> bool:
        """오늘 동일 알림이 있는지 확인"""
        query = """
            SELECT 1 FROM alerts
            WHERE ticker = %s AND pattern = %s AND alert_date = CURRENT_DATE
            LIMIT 1
        """
        result = self.db.execute_one(query, (ticker, pattern))
        return result is not None

    def get_today_alerts(self) -> List[Alert]:
        """오늘 발송된 모든 알림 조회"""
        query = "SELECT * FROM alerts WHERE alert_date = CURRENT_DATE ORDER BY sent_at DESC"
        results = self.db.execute(query)
        return [Alert.from_dict(dict(r)) for r in results]

    def get_alerts_by_ticker(self, ticker: str, days: int = 7) -> List[Alert]:
        """특정 종목의 최근 알림 조회"""
        query = """
            SELECT * FROM alerts
            WHERE ticker = %s AND alert_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY sent_at DESC
        """
        results = self.db.execute(query, (ticker, days))
        return [Alert.from_dict(dict(r)) for r in results]

    def cleanup_old_alerts(self, days: int = 30) -> int:
        """오래된 알림 삭제"""
        query = "DELETE FROM alerts WHERE alert_date < CURRENT_DATE - INTERVAL '%s days'"
        self.db.execute(query, (days,))
        return 0