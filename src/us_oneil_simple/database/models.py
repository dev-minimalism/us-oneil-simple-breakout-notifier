"""데이터베이스 모델"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, Any


@dataclass
class Position:
    """포지션 모델"""
    id: int | None = None
    ticker: str = ""
    market: str = "US"
    entry_price: float = 0.0
    entry_date: datetime = field(default_factory=datetime.now)
    pattern: str = ""
    stop_loss: float | None = None
    take_profit: float | None = None
    signal_data: Dict[str, Any] | None = None
    status: str = "open"  # open, closed
    exit_price: float | None = None
    exit_date: datetime | None = None
    exit_reason: str | None = None
    profit_pct: float | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """딕셔너리에서 Position 객체 생성"""
        return cls(
            id=data.get('id'),
            ticker=data.get('ticker', ''),
            market=data.get('market', 'US'),
            entry_price=float(data.get('entry_price', 0)),
            entry_date=data.get('entry_date', datetime.now()),
            pattern=data.get('pattern', ''),
            stop_loss=float(data['stop_loss']) if data.get('stop_loss') else None,
            take_profit=float(data['take_profit']) if data.get('take_profit') else None,
            signal_data=data.get('signal_data'),
            status=data.get('status', 'open'),
            exit_price=float(data['exit_price']) if data.get('exit_price') else None,
            exit_date=data.get('exit_date'),
            exit_reason=data.get('exit_reason'),
            profit_pct=float(data['profit_pct']) if data.get('profit_pct') else None,
            created_at=data.get('created_at', datetime.now()),
            updated_at=data.get('updated_at', datetime.now()),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'market': self.market,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date.strftime('%Y-%m-%d %H:%M:%S') if isinstance(self.entry_date, datetime) else str(self.entry_date),
            'pattern': self.pattern,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'signal_data': self.signal_data,
            'status': self.status,
            'exit_price': self.exit_price,
            'exit_date': self.exit_date.strftime('%Y-%m-%d %H:%M:%S') if self.exit_date else None,
            'exit_reason': self.exit_reason,
            'profit_pct': self.profit_pct,
        }


@dataclass
class Alert:
    """알림 기록 모델 (중복 방지용)"""
    id: int | None = None
    ticker: str = ""
    market: str = "US"
    pattern: str = ""
    alert_date: date = field(default_factory=date.today)
    alert_price: float = 0.0
    signal_data: Dict[str, Any] | None = None
    sent_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict) -> "Alert":
        """딕셔너리에서 Alert 객체 생성"""
        alert_date = data.get('alert_date')
        if isinstance(alert_date, str):
            alert_date = datetime.strptime(alert_date, '%Y-%m-%d').date()
        elif isinstance(alert_date, datetime):
            alert_date = alert_date.date()

        return cls(
            id=data.get('id'),
            ticker=data.get('ticker', ''),
            market=data.get('market', 'US'),
            pattern=data.get('pattern', ''),
            alert_date=alert_date or date.today(),
            alert_price=float(data.get('alert_price', 0)),
            signal_data=data.get('signal_data'),
            sent_at=data.get('sent_at', datetime.now()),
            created_at=data.get('created_at', datetime.now()),
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'ticker': self.ticker,
            'market': self.market,
            'pattern': self.pattern,
            'alert_date': self.alert_date.strftime('%Y-%m-%d') if isinstance(self.alert_date, date) else str(self.alert_date),
            'alert_price': self.alert_price,
            'signal_data': self.signal_data,
            'sent_at': self.sent_at.strftime('%Y-%m-%d %H:%M:%S') if isinstance(self.sent_at, datetime) else str(self.sent_at),
        }