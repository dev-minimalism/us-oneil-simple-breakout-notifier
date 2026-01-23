"""데이터베이스 Repository"""
import json
from datetime import datetime, date
from typing import List, Any

import numpy as np

from .connection import DatabaseConnection
from .models import Position, Alert


def _convert_numpy_types(obj: Any) -> Any:
    """numpy 타입을 Python 기본 타입으로 변환 (JSON 직렬화용)"""
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(v) for v in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    return obj


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

        # numpy 타입 → Python 기본 타입 변환
        entry_price = float(entry_price) if entry_price is not None else None
        stop_loss = float(stop_loss) if stop_loss is not None else None
        take_profit = float(take_profit) if take_profit is not None else None
        signal_json = json.dumps(_convert_numpy_types(signal_data)) if signal_data else None

        query = """
            INSERT INTO positions (ticker, market, entry_price, pattern, stop_loss, take_profit, signal_data, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
            RETURNING *
        """
        result = self.db.execute_one(
            query,
            (ticker, market, entry_price, pattern, stop_loss, take_profit, signal_json)
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
        """포지션 청산

        Returns:
            청산 성공 여부 (실제 업데이트된 행이 있으면 True)
        """
        query = """
            UPDATE positions
            SET status = 'closed',
                exit_price = %s,
                exit_date = CURRENT_TIMESTAMP,
                exit_reason = %s,
                profit_pct = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticker = %s AND status = 'open'
            RETURNING id
        """
        result = self.db.execute_one(query, (exit_price, exit_reason, profit_pct, ticker))
        success = result is not None
        if success:
            print(f"  ✅ 포지션 DB 청산 성공: {ticker}")
        else:
            print(f"  ❌ 포지션 DB 청산 실패 (open 포지션 없음): {ticker}")
        return success

    def remove(self, ticker: str) -> bool:
        """포지션 삭제 (청산 처리)"""
        return self.close(ticker, 0, '수동 삭제', 0)

    def get_closed(self, limit: int = 20) -> List[Position]:
        """청산된 포지션 조회 (최근 거래 내역)"""
        query = """
            SELECT * FROM positions
            WHERE status = 'closed'
            ORDER BY exit_date DESC
            LIMIT %s
        """
        results = self.db.execute(query, (limit,))
        return [Position.from_dict(dict(r)) for r in results]

    def get_stats(self) -> dict:
        """거래 통계 조회"""
        query = """
            SELECT
                COUNT(*) as total_trades,
                COUNT(CASE WHEN profit_pct > 0 THEN 1 END) as win_count,
                COUNT(CASE WHEN profit_pct <= 0 THEN 1 END) as loss_count,
                COALESCE(AVG(profit_pct), 0) as avg_profit,
                COALESCE(MAX(profit_pct), 0) as max_profit,
                COALESCE(MIN(profit_pct), 0) as max_loss,
                COALESCE(SUM(profit_pct), 0) as total_profit
            FROM positions
            WHERE status = 'closed'
        """
        result = self.db.execute_one(query)
        if result:
            total = result['total_trades'] or 0
            wins = result['win_count'] or 0
            return {
                'total_trades': total,
                'win_count': wins,
                'loss_count': result['loss_count'] or 0,
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'avg_profit': float(result['avg_profit'] or 0),
                'max_profit': float(result['max_profit'] or 0),
                'max_loss': float(result['max_loss'] or 0),
                'total_profit': float(result['total_profit'] or 0),
            }
        return {
            'total_trades': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'max_profit': 0,
            'max_loss': 0,
            'total_profit': 0,
        }


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
        try:
            # numpy 타입 → Python 기본 타입 변환
            alert_price = float(alert_price) if alert_price is not None else 0.0
            signal_json = json.dumps(_convert_numpy_types(signal_data)) if signal_data else None

            query = """
                INSERT INTO alerts (ticker, market, pattern, alert_date, alert_price, signal_data)
                VALUES (%s, %s, %s, CURRENT_DATE, %s, %s)
                ON CONFLICT (ticker, pattern, alert_date) DO NOTHING
                RETURNING *
            """
            result = self.db.execute_one(
                query,
                (ticker, market, pattern, alert_price, signal_json)
            )
            if result:
                print(f"  ✅ Alert DB 저장 성공: {ticker} ({pattern})")
                return Alert.from_dict(dict(result))
            else:
                # ON CONFLICT로 인해 INSERT가 스킵된 경우 (이미 존재)
                print(f"  ⚠️ Alert DB 저장 스킵 (이미 존재): {ticker} ({pattern})")
                return None
        except Exception as e:
            print(f"  ❌ Alert DB 저장 예외: {ticker} ({pattern}) - {type(e).__name__}: {e}")
            raise

    def has_alert_today(self, ticker: str, pattern: str) -> bool:
        """오늘 동일 알림이 있는지 확인"""
        try:
            query = """
                SELECT 1 FROM alerts
                WHERE ticker = %s AND pattern = %s AND alert_date = CURRENT_DATE
                LIMIT 1
            """
            result = self.db.execute_one(query, (ticker, pattern))
            has_alert = result is not None
            if has_alert:
                print(f"  ℹ️ 오늘 이미 알림 있음: {ticker} ({pattern})")
            return has_alert
        except Exception as e:
            print(f"  ❌ Alert 조회 예외: {ticker} ({pattern}) - {type(e).__name__}: {e}")
            raise

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