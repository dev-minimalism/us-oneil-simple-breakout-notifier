"""미국 주식 돌파매매 감지 봇"""
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List

from ..config import Settings, load_settings
from ..data.us_stock import get_us_stock_data
from ..patterns.pivot import detect_pivot_breakout
from ..market.status import (
    get_market_status,
    format_market_status_message,
    get_next_scan_time,
    get_seconds_until_next_scan,
)
from ..positions import PositionManager
from ..watchlist import WatchlistManager
from ..telegram.client import TelegramClient
from ..telegram.formatter import (
    format_signal_message,
    format_close_position_message,
    format_no_signal_message
)


class BreakoutDetector:
    """미국 주식 돌파매매 패턴 감지 봇"""

    def __init__(self, settings: Settings | None = None):
        """
        Args:
            settings: 설정 객체 (None이면 자동 로드)
        """
        self.settings = settings or load_settings()

        # 텔레그램 클라이언트
        self.telegram = TelegramClient(
            self.settings.telegram.token,
            self.settings.telegram.chat_id
        )

        # 워치리스트 관리자
        self.watchlist = WatchlistManager(
            self.settings.watchlist_file,
            self.settings.watchlist.us_stocks
        )

        # 포지션 관리자
        self.positions = PositionManager(
            self.settings.positions_file,
            self.settings.trading.stop_loss_pct,
            self.settings.trading.take_profit_pct,
            self.settings.trading.max_holding_days
        )

        # 스캔 락
        self.scan_lock = threading.Lock()
        self.is_scanning = False

        print(f"✅ 감시 종목 로드 완료: {self.watchlist.count()}개")
        print(f"✅ 포지션 로드 완료: {self.positions.count()}개")

    # ========================================
    # 텔레그램 명령어 처리
    # ========================================

    def process_command(self, message: str) -> str | None:
        """텔레그램 명령어 처리"""
        parts = message.strip().split()
        if not parts:
            return None

        command = parts[0].lower()

        if command in ('/help', '/start'):
            return self._get_help_message()

        elif command == '/add':
            if len(parts) < 2:
                return "❌ 사용법: /add [티커]\n예: /add AAPL"
            return self.watchlist.add(parts[1])

        elif command == '/remove':
            if len(parts) < 2:
                return "❌ 사용법: /remove [티커]\n예: /remove AAPL"
            return self.watchlist.remove(parts[1])

        elif command == '/list':
            return self.watchlist.format_list_message()

        elif command == '/status':
            market_status = get_market_status()
            return format_market_status_message(
                market_status,
                self.watchlist.count(),
                self.is_scanning
            )

        elif command == '/scan':
            return 'SCAN'

        elif command == '/positions':
            return self.positions.format_list_message(self._get_current_price)

        elif command == '/close':
            if len(parts) < 2:
                return "❌ 사용법: /close [티커]\n예: /close AAPL"
            return self._close_position_command(parts[1].upper())

        elif command == '/trades':
            return self.positions.format_trades_message()

        elif command == '/stats':
            return self.positions.format_stats_message()

        return None

    def _get_help_message(self) -> str:
        """도움말 메시지"""
        return """
🤖 <b>윌리엄 오닐 돌파매매 봇</b>

<b>스캔:</b>
/scan - 즉시 스캔
/status - 시장 상태 확인

<b>포지션 관리:</b>
/positions - 현재 보유 포지션 보기
/close [티커] - 포지션 수동 청산

<b>거래 내역:</b>
/trades - 최근 거래 내역
/stats - 거래 통계

<b>종목 관리:</b>
/add [티커] - 종목 추가
/remove [티커] - 종목 삭제
/list - 현재 감시 종목 보기

<b>시장 시간 (KST):</b>
🌅 데이마켓: 10:00~17:50
🌆 프리마켓: 18:00~23:30
🏛️ 정규장: 23:30~06:00
🌙 애프터마켓: 06:00~09:50

<b>스캔 스케줄:</b>
• 매시간 :02, :32 자동 스캔
"""

    def _close_position_command(self, ticker: str) -> str:
        """포지션 청산 명령 처리"""
        pos = self.positions.get(ticker)
        if not pos:
            return f"❌ {ticker} 포지션을 찾을 수 없습니다."

        try:
            current_price = self._get_current_price(ticker, 'US')
            if current_price:
                success = self._close_position(pos, current_price, "수동 청산")
                if success:
                    return f"✅ {ticker} 포지션이 청산되었습니다."
                else:
                    return f"❌ {ticker} 포지션 청산 실패 (DB 업데이트 오류)"
            else:
                return f"❌ {ticker} 현재가 조회 실패"
        except Exception as e:
            return f"❌ 청산 중 오류: {e}"

    def _get_current_price(self, ticker: str, market: str = 'US') -> float | None:
        """현재가 조회"""
        df = get_us_stock_data(ticker, period="5d")
        if df is not None and len(df) > 0:
            return df['Close'].iloc[-1]
        return None

    # ========================================
    # 포지션 관리
    # ========================================

    def _close_position(self, position: Dict, exit_price: float, reason: str) -> bool:
        """포지션 청산 처리

        Returns:
            청산 성공 여부
        """
        ticker = position['ticker']
        profit_pct, holding_days = self.positions.calculate_profit(position, exit_price)

        # DB에서 포지션 청산 먼저 시도 (성공해야 텔레그램 발송)
        success = self.positions.close_position(
            ticker,
            exit_price,
            reason,
            profit_pct
        )

        if not success:
            print(f"  ⚠️ 포지션 청산 실패 (DB 업데이트 안됨): {ticker}")
            return False

        # DB 청산 성공 후 텔레그램 발송
        msg = format_close_position_message(
            ticker,
            'US',
            position['pattern'],
            position['entry_price'],
            exit_price,
            profit_pct,
            holding_days,
            reason
        )
        self.telegram.send_message(msg)
        print(f"  ❌ 포지션 청산 완료: {ticker} ({reason}) {profit_pct:+.2f}%")
        return True

    def check_positions(self):
        """포지션 추적 및 청산 조건 확인"""
        if self.positions.count() == 0:
            return

        print(f"\n📊 포지션 추적 중... ({self.positions.count()}개)")

        for pos in self.positions.get_all():
            ticker = pos['ticker']
            try:
                current_price = self._get_current_price(ticker)
                if current_price is None:
                    continue

                profit_pct, holding_days = self.positions.calculate_profit(pos, current_price)
                print(f"  🔍 {ticker}: ${current_price:,.2f} ({profit_pct:+.2f}%)", end="")

                should_exit, exit_price, reason = self.positions.check_exit_conditions(pos, current_price)
                if should_exit:
                    print(f" ⚠️ {reason}!")
                    self._close_position(pos, exit_price, reason)
                else:
                    print(f" ⚪")

                time.sleep(1)

            except Exception as e:
                print(f" ❌ 오류: {e}")

    # ========================================
    # 종목 분석
    # ========================================

    def analyze_stock(self, ticker: str) -> List[Dict]:
        """주식 분석"""
        df = get_us_stock_data(ticker, self.settings.data.analysis_period)
        if df is None:
            return []

        signals = []
        pivot_signal = detect_pivot_breakout(
            df, ticker, 'US',
            volume_surge_min=self.settings.pattern.volume_surge_min,
            breakout_max=self.settings.pattern.breakout_max
        )
        if pivot_signal:
            signals.append(pivot_signal)

        return signals

    # ========================================
    # 스캔 실행
    # ========================================

    def run_scan(self, is_manual: bool = False) -> List[Dict]:
        """스캔 실행

        Args:
            is_manual: 수동 스캔 여부 (/scan 명령어로 실행된 경우 True)
        """
        print(f"\n{'=' * 60}")
        print(f"🔍 스캔 시작")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 감시 종목: {self.watchlist.count()}개")
        print(f"{'=' * 60}\n")

        signals = []
        tickers = self.watchlist.get_all()

        if not tickers:
            print("⚠️  감시 종목이 없습니다.")
            return signals

        for ticker in tickers:
            try:
                print(f"  🔍 {ticker}...", end=" ")
                stock_signals = self.analyze_stock(ticker)

                if stock_signals:
                    for signal in stock_signals:
                        pattern = signal['pattern']

                        # 중복 알림 방지 1: 이미 포지션 보유 중이면 스킵
                        if self.positions.has_position(ticker):
                            print(f"⏭️ 스킵 (이미 포지션 보유 중)")
                            continue

                        # 중복 알림 방지 2: 오늘 이미 동일 신호를 보냈는지 확인
                        if not self.positions.can_send_alert(ticker, pattern):
                            print(f"⏭️ 중복 (오늘 이미 알림 발송)")
                            continue

                        signals.append(signal)

                        # 알림 기록 저장 먼저 (중복 방지용) - 실패하면 텔레그램 발송 안함
                        alert_saved = self.positions.record_alert(
                            ticker=ticker,
                            market='US',
                            pattern=pattern,
                            alert_price=signal['current_price'],
                            signal_data=signal
                        )

                        if not alert_saved:
                            print(f"⚠️ 알림 저장 실패 - 텔레그램 발송 건너뜀")
                            continue

                        # 알림 저장 성공 시에만 텔레그램 발송
                        msg = format_signal_message(signal)
                        self.telegram.send_message(msg)

                        # 포지션 자동 추가
                        if not self.positions.has_position(ticker):
                            self.positions.add(
                                ticker=ticker,
                                market='US',
                                entry_price=signal['current_price'],
                                pattern=signal['pattern'],
                                signal=signal
                            )

                        print(f"✅ 신호!")
                        time.sleep(1)
                else:
                    print("⚪")
            except Exception as e:
                print(f"❌ 오류: {e}")

        self._print_scan_summary(signals, is_manual)

        return signals

    def run_smart_scan(self) -> List[Dict]:
        """시간대에 따라 자동 스캔"""
        if self.is_scanning:
            print("\n⏸️  수동 스캔이 진행 중입니다. 이번 주기는 건너뜁니다...\n")
            return []

        market_status = get_market_status()

        print(f"\n{'=' * 60}")
        print(f"🔍 윌리엄 오닐 스마트 스캔")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not market_status['is_open']:
            print(f"{market_status['session_emoji']} {market_status['session_name']}")
            print(f"{'=' * 60}\n")
            return []

        session_emoji = market_status['session_emoji']
        session_name = market_status['session_name']
        print(f"{session_emoji} {session_name} - 스캔 시작 ({self.watchlist.count()}개)")
        print(f"{'=' * 60}\n")

        # 먼저 포지션 추적
        self.check_positions()

        return self.run_scan()

    def _print_scan_summary(self, signals: List[Dict], is_manual: bool = False):
        """스캔 결과 요약 출력

        Args:
            signals: 발견된 신호 목록
            is_manual: 수동 스캔 여부 (수동 스캔일 때만 "신호 없음" 텔레그램 알림 전송)
        """
        if signals:
            print(f"\n📊 {len(signals)}개 신호 발견")
        else:
            print("\n⚪ 신호 없음")

            # 수동 스캔(/scan)일 때만 "신호 없음" 알림 전송
            if is_manual:
                msg = format_no_signal_message(
                    "스캔",
                    self.watchlist.count(),
                    0,
                    True,
                    False
                )
                self.telegram.send_message(msg)

        print(f"\n{'=' * 60}\n")

    # ========================================
    # 스캔 스레드 관리
    # ========================================

    def _execute_scan_in_thread(self):
        """별도 스레드에서 스캔 실행"""
        if self.is_scanning:
            self.telegram.send_message("⚠️  이미 스캔이 진행 중입니다. 완료 후 다시 시도해주세요.")
            return

        if not self.scan_lock.acquire(blocking=False):
            self.telegram.send_message("⚠️  다른 스캔이 진행 중입니다. 잠시 후 다시 시도해주세요.")
            return

        try:
            self.is_scanning = True
            print(f"\n🔔 수동 스캔 명령어 수신 - 스캔 시작")
            self.run_scan(is_manual=True)
            self.telegram.send_message(f"✅ 스캔 완료!")
        except Exception as e:
            print(f"❌ 스캔 중 오류: {e}")
            self.telegram.send_message(f"❌ 스캔 중 오류가 발생했습니다: {str(e)}")
        finally:
            self.is_scanning = False
            self.scan_lock.release()

    def check_telegram_updates(self):
        """텔레그램 메시지 확인 (명령어 처리)"""
        updates = self.telegram.get_updates()

        for update in updates:
            message_text = update['text']
            reply = self.process_command(message_text)

            if reply == 'SCAN':
                self.telegram.send_message("🔍 스캔을 시작합니다...")
                scan_thread = threading.Thread(
                    target=self._execute_scan_in_thread,
                    daemon=True
                )
                scan_thread.start()

            elif reply:
                self.telegram.send_message(reply)

    def start_command_listener(self):
        """백그라운드에서 텔레그램 명령어 리스너 시작"""

        def listener_loop():
            while True:
                try:
                    self.check_telegram_updates()
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️  리스너 오류: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=listener_loop, daemon=True)
        thread.start()
        print("✅ 텔레그램 명령어 리스너 시작")

    # ========================================
    # 메인 실행
    # ========================================

    def get_start_message(self) -> str:
        """시작 메시지 생성"""
        market_status = get_market_status()
        session_emoji = market_status['session_emoji']
        session_name = market_status['session_name']

        next_scan = get_next_scan_time()
        next_scan_str = next_scan.strftime('%H:%M')

        return f"""
🤖 <b>윌리엄 오닐 돌파매매 봇 시작</b>

📊 감시 종목: {self.watchlist.count()}개
📍 현재 포지션: {self.positions.count()}개

🕐 현재 상태: {session_emoji} {session_name}
⏭️ 다음 스캔: {next_scan_str}

📈 <b>시장 시간 (KST)</b>
   🌅 데이마켓: 10:00~17:50
   🌆 프리마켓: 18:00~23:30
   🏛️ 정규장: 23:30~06:00
   🌙 애프터마켓: 06:00~09:50

⏰ 스캔 스케줄: 매시간 :02, :32

🎯 자동 포지션 추적:
   • 손절({self.settings.trading.stop_loss_pct}%), 익절(+{self.settings.trading.take_profit_pct}%)
   • {self.settings.trading.max_holding_days}일 만료 알림

시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    def run(self):
        """메인 실행 루프 (매시간 :02, :32에 스캔)"""
        # 텔레그램 명령어 리스너 시작
        self.start_command_listener()

        # 시작 메시지 (키보드 버튼 포함)
        start_msg = self.get_start_message()
        self.telegram.send_message(start_msg, with_keyboard=True)
        print(start_msg)

        try:
            while True:
                # 다음 스캔 시간까지 대기
                wait_seconds = get_seconds_until_next_scan()
                next_scan = get_next_scan_time()

                if wait_seconds > 0:
                    print(f"⏰ 다음 스캔: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"💤 {wait_seconds // 60}분 {wait_seconds % 60}초 대기 중...\n")
                    time.sleep(wait_seconds)

                # 스캔 실행
                self.run_smart_scan()

                # 스캔 직후 1초 대기 (다음 스캔 시간 계산을 위해)
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n⛔ 프로그램 종료")
            self.telegram.send_message("⛔ 윌리엄 오닐 돌파매매 봇 종료")