"""피벗 포인트 돌파 패턴 감지"""
from typing import Dict

import numpy as np
import pandas as pd


def detect_pivot_breakout(
    df: pd.DataFrame,
    ticker: str,
    market: str,
    stock_name: str | None = None,
    volume_surge_min: float = 50,
    breakout_max: float = 5
) -> Dict | None:
    """
    피벗 포인트 돌파 감지

    Args:
        df: OHLCV 데이터프레임
        ticker: 종목 코드
        market: 시장 ('US' 또는 'KR')
        stock_name: 종목명 (한국 주식용)
        volume_surge_min: 최소 거래량 증가율 (%)
        breakout_max: 최대 돌파율 (%)

    Returns:
        신호 딕셔너리 또는 None
    """
    if df is None or len(df) < 30:
        return None

    try:
        recent = df.tail(30).copy()
        avg_volume = recent['Volume'].iloc[:-1].mean()
        current_volume = recent['Volume'].iloc[-1]
        volume_surge = (current_volume / avg_volume - 1) * 100

        close = recent['Close'].values
        current_price = close[-1]
        resistance = np.max(close[-20:-1])

        breakout = current_price > resistance
        breakout_pct = ((current_price - resistance) / resistance) * 100

        if breakout and volume_surge >= volume_surge_min and 0 < breakout_pct <= breakout_max:
            signal = {
                'ticker': ticker,
                'pattern': '피벗돌파',
                'market': market,
                'resistance': resistance,
                'current_price': current_price,
                'breakout_pct': round(breakout_pct, 2),
                'volume_surge': round(volume_surge, 2)
            }

            if market == 'KR' and stock_name:
                signal['name'] = stock_name

            return signal
    except Exception:
        pass

    return None


def detect_pivot_breakout_at_index(df: pd.DataFrame, idx: int) -> tuple[bool, float]:
    """
    특정 인덱스에서 피벗 포인트 돌파 감지 (백테스트용)

    Args:
        df: OHLCV 데이터프레임
        idx: 감지할 인덱스

    Returns:
        (신호발생여부, 저항선)
    """
    if idx < 30:
        return False, 0

    try:
        window = df.iloc[idx - 30:idx + 1]

        avg_volume = window['Volume'].iloc[:-1].mean()
        current_volume = window['Volume'].iloc[-1]
        volume_surge = (current_volume / avg_volume - 1) * 100

        close = window['Close'].values
        current_price = close[-1]
        resistance = np.max(close[-20:-1])
        breakout = current_price > resistance
        breakout_pct = ((current_price - resistance) / resistance) * 100

        if breakout and volume_surge >= 50 and 0 < breakout_pct <= 5:
            return True, resistance

    except Exception:
        pass

    return False, 0
