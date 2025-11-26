"""미국 주식 데이터 수집"""
import pandas as pd
import yfinance as yf


def get_us_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame | None:
    """
    미국 주식 데이터 가져오기

    Args:
        ticker: 종목 코드 (예: "AAPL")
        period: 조회 기간 (예: "6mo", "1y")

    Returns:
        OHLCV 데이터프레임 또는 None
    """
    try:
        stock_obj = yf.Ticker(ticker)
        df = stock_obj.history(period=period)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"❌ {ticker} 데이터 조회 실패: {e}")
        return None


def get_us_stock_data_by_date(ticker: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """
    미국 주식 데이터 기간별 조회

    Args:
        ticker: 종목 코드
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)

    Returns:
        OHLCV 데이터프레임 또는 None
    """
    try:
        stock_obj = yf.Ticker(ticker)
        df = stock_obj.history(start=start_date, end=end_date)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"❌ {ticker} 데이터 조회 실패: {e}")
        return None
