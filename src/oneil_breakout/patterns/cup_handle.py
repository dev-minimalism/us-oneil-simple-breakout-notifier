"""컵앤핸들 패턴 감지"""
import numpy as np
import pandas as pd


def detect_cup_and_handle(
    df: pd.DataFrame,
    idx: int,
    cup_depth_min: float = 12,
    cup_depth_max: float = 40,
    handle_depth_max: float = 12
) -> tuple[bool, float]:
    """
    컵앤핸들 패턴 감지

    Args:
        df: OHLCV 데이터프레임
        idx: 감지할 인덱스
        cup_depth_min: 컵 최소 깊이 (%)
        cup_depth_max: 컵 최대 깊이 (%)
        handle_depth_max: 핸들 최대 깊이 (%)

    Returns:
        (신호발생여부, 저항선)
    """
    if idx < 60:
        return False, 0

    try:
        window = df.iloc[idx - 60:idx + 1]
        close = window['Close'].values

        # 컵 형성
        mid_idx = len(close) // 2
        left_peak = np.max(close[:mid_idx])
        right_peak = np.max(close[mid_idx:])
        bottom = np.min(close[mid_idx - 10:mid_idx + 10])
        cup_depth = ((left_peak - bottom) / left_peak) * 100

        # 핸들 형성
        handle = close[-10:]
        handle_depth = ((np.max(handle) - np.min(handle)) / np.max(handle)) * 100

        # 돌파 확인
        current_price = close[-1]
        resistance = np.max(close[-20:])
        breakout = current_price >= resistance * 0.99

        if cup_depth_min <= cup_depth <= cup_depth_max and handle_depth < handle_depth_max and breakout:
            return True, resistance

    except Exception:
        pass

    return False, 0
