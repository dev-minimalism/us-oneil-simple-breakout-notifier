"""베이스 돌파 패턴 감지"""
import numpy as np
import pandas as pd


def detect_base_breakout(
    df: pd.DataFrame,
    idx: int,
    volatility_max: float = 15,
    volume_surge_min: float = 40,
    breakout_max: float = 7
) -> tuple[bool, float]:
    """
    베이스 돌파 감지

    Args:
        df: OHLCV 데이터프레임
        idx: 감지할 인덱스
        volatility_max: 베이스 최대 변동성 (%)
        volume_surge_min: 최소 거래량 증가율 (%)
        breakout_max: 최대 돌파율 (%)

    Returns:
        (신호발생여부, 저항선)
    """
    if idx < 40:
        return False, 0

    try:
        window = df.iloc[idx - 40:idx + 1]
        close = window['Close'].values

        # 횡보 구간 확인
        base_period = close[-30:-5]
        base_high = np.max(base_period)
        base_low = np.min(base_period)
        base_volatility = ((base_high - base_low) / base_low) * 100

        current_price = close[-1]
        breakout = current_price > base_high
        breakout_pct = ((current_price - base_high) / base_high) * 100

        # 거래량 확인
        avg_volume = window['Volume'].iloc[-30:-5].mean()
        current_volume = window['Volume'].iloc[-1]
        volume_surge = (current_volume / avg_volume - 1) * 100

        if base_volatility < volatility_max and breakout and volume_surge >= volume_surge_min and 0 < breakout_pct <= breakout_max:
            return True, base_high

    except Exception:
        pass

    return False, 0
