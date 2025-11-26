"""워치리스트 관리자 (미국 주식 전용)"""
import json
import os
from datetime import datetime
from typing import List


class WatchlistManager:
    """감시 종목 관리 클래스 (미국 주식 전용)"""

    def __init__(
        self,
        watchlist_file: str = "watchlist.json",
        default_stocks: List[str] | None = None
    ):
        """
        Args:
            watchlist_file: 감시 종목 저장 파일 경로
            default_stocks: 기본 종목 리스트
        """
        self.watchlist_file = watchlist_file
        self.default_stocks = default_stocks or [
            "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA",
            "AMZN", "META", "AMD", "AVGO", "NFLX"
        ]
        self.watchlist = self._load()

    def _load(self) -> List[str]:
        """감시 종목 파일에서 로드"""
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 기존 형식 호환 (us 키가 있으면 사용)
                    if 'us' in data:
                        return data['us']
                    elif 'stocks' in data:
                        return data['stocks']
                    elif isinstance(data, list):
                        return data
            except Exception as e:
                print(f"⚠️  감시 종목 로드 실패: {e}")

        return self.default_stocks.copy()

    def _save(self) -> bool:
        """감시 종목 파일에 저장"""
        try:
            data = {
                'stocks': self.watchlist,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.watchlist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 감시 종목 저장 실패: {e}")
            return False

    def add(self, ticker: str) -> str:
        """
        종목 추가

        Args:
            ticker: 종목 코드

        Returns:
            결과 메시지
        """
        ticker = ticker.upper().strip()
        if ticker in self.watchlist:
            return f"⚠️  {ticker}는 이미 감시 중입니다."

        self.watchlist.append(ticker)
        if self._save():
            return f"✅ {ticker} 추가 완료!\n현재 감시 종목: {len(self.watchlist)}개"
        else:
            self.watchlist.remove(ticker)
            return "❌ 저장 실패"

    def remove(self, ticker: str) -> str:
        """
        종목 삭제

        Args:
            ticker: 종목 코드

        Returns:
            결과 메시지
        """
        ticker = ticker.upper().strip()
        if ticker not in self.watchlist:
            return f"⚠️  {ticker}는 감시 목록에 없습니다."

        self.watchlist.remove(ticker)
        if self._save():
            return f"✅ {ticker} 삭제 완료!\n현재 감시 종목: {len(self.watchlist)}개"
        else:
            self.watchlist.append(ticker)
            return "❌ 저장 실패"

    def get_all(self) -> List[str]:
        """감시 종목 조회"""
        return self.watchlist.copy()

    def count(self) -> int:
        """종목 개수"""
        return len(self.watchlist)

    def format_list_message(self) -> str:
        """
        감시 종목 목록 메시지 포맷팅

        Returns:
            포맷된 HTML 메시지
        """
        msg = f"📊 <b>감시 종목</b> ({len(self.watchlist)}개)\n\n"

        if self.watchlist:
            msg += ", ".join(self.watchlist)
        else:
            msg += "없음"

        return msg