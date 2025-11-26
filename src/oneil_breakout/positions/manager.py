"""포지션 관리자"""
import json
import os
from datetime import datetime
from typing import Dict, List, Callable


class PositionManager:
    """포지션 관리 클래스"""

    def __init__(
        self,
        positions_file: str = "positions.json",
        stop_loss_pct: float = -8.0,
        take_profit_pct: float = 20.0,
        max_holding_days: int = 30
    ):
        """
        Args:
            positions_file: 포지션 저장 파일 경로
            stop_loss_pct: 손절 기준 (%)
            take_profit_pct: 익절 기준 (%)
            max_holding_days: 최대 보유 기간 (일)
        """
        self.positions_file = positions_file
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_holding_days = max_holding_days
        self.positions: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        """포지션 파일에서 로드"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('positions', [])
            except Exception as e:
                print(f"⚠️  포지션 로드 실패: {e}")
        return []

    def _save(self) -> bool:
        """포지션 파일에 저장"""
        try:
            data = {
                'positions': self.positions,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 포지션 저장 실패: {e}")
            return False

    def add(
        self,
        ticker: str,
        market: str,
        entry_price: float,
        pattern: str,
        signal: Dict
    ) -> Dict:
        """
        포지션 추가

        Args:
            ticker: 종목 코드
            market: 시장 ('US' 또는 'KR')
            entry_price: 진입가
            pattern: 패턴명
            signal: 신호 딕셔너리

        Returns:
            추가된 포지션 딕셔너리
        """
        position = {
            'ticker': ticker,
            'market': market,
            'entry_price': entry_price,
            'entry_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pattern': pattern,
            'stop_loss': entry_price * (1 + self.stop_loss_pct / 100),
            'take_profit': entry_price * (1 + self.take_profit_pct / 100),
            'signal': signal
        }
        self.positions.append(position)
        self._save()
        print(f"  📝 포지션 추가: {ticker} @ {entry_price}")
        return position

    def remove(self, ticker: str) -> bool:
        """
        포지션 제거

        Args:
            ticker: 종목 코드

        Returns:
            제거 성공 여부
        """
        for pos in self.positions:
            if pos['ticker'] == ticker:
                self.positions.remove(pos)
                self._save()
                return True
        return False

    def get(self, ticker: str) -> Dict | None:
        """
        특정 종목 포지션 조회

        Args:
            ticker: 종목 코드

        Returns:
            포지션 딕셔너리 또는 None
        """
        return next((p for p in self.positions if p['ticker'] == ticker), None)

    def has_position(self, ticker: str) -> bool:
        """
        특정 종목 포지션 보유 여부

        Args:
            ticker: 종목 코드

        Returns:
            보유 여부
        """
        return any(p['ticker'] == ticker for p in self.positions)

    def get_all(self) -> List[Dict]:
        """모든 포지션 조회"""
        return self.positions.copy()

    def count(self) -> int:
        """포지션 개수"""
        return len(self.positions)

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
        entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d %H:%M:%S')
        holding_days = (datetime.now() - entry_date).days

        # 손절 확인
        if current_price <= position['stop_loss']:
            return True, position['stop_loss'], f'손절 ({self.stop_loss_pct}%)'

        # 익절 확인
        if current_price >= position['take_profit']:
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
        entry_date = datetime.strptime(position['entry_date'], '%Y-%m-%d %H:%M:%S')
        holding_days = (datetime.now() - entry_date).days
        return profit_pct, holding_days

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
        if not self.positions:
            return "📊 <b>현재 포지션</b>\n\n보유 중인 포지션이 없습니다."

        msg = f"📊 <b>현재 포지션</b> ({len(self.positions)}개)\n\n"

        for i, pos in enumerate(self.positions, 1):
            ticker = pos['ticker']
            market_emoji = "🇺🇸" if pos['market'] == 'US' else "🇰🇷"
            entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d %H:%M:%S')
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

            msg += f"""
{i}. {market_emoji} <b>{ticker}</b>
   진입: {pos['entry_price']:,.2f}
   현재: {current_info}
   패턴: {pos['pattern']}
   보유: {holding_days}일
   손절: {pos['stop_loss']:,.2f}
   익절: {pos['take_profit']:,.2f}
"""

        return msg