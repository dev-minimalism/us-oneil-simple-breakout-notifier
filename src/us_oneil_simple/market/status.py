"""시장 상태 확인 (미국 주식 전용)"""
from datetime import datetime, time as dt_time
from typing import Dict


def get_market_status() -> Dict[str, bool | str | int]:
    """
    현재 시간에 따른 미국 시장 상태 확인 (한국 시간 기준)

    Returns:
        {
            'is_open': bool - 미국 장중 여부,
            'time': str - 현재 시간,
            'weekday': int - 요일 (0=월요일, 6=일요일)
        }
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()

    # 주말 체크
    is_weekend = weekday >= 5

    # 미국 장중 (한국 시간): 22:30 - 05:00 다음날 (서머타임)
    # 겨울: 23:30 - 06:00
    # 여유있게 22:00 - 07:00으로 설정
    us_open_night = dt_time(22, 0)
    us_close_morning = dt_time(7, 0)

    is_open = False

    if not is_weekend:
        # 22:00 이후 (당일 밤)
        if current_time >= us_open_night:
            is_open = True
        # 07:00 이전 (다음날 새벽)
        elif current_time <= us_close_morning:
            is_open = True

    return {
        'is_open': is_open,
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def format_market_status_message(market_status: Dict, stock_count: int, is_scanning: bool = False) -> str:
    """
    시장 상태 메시지 포맷팅

    Args:
        market_status: get_market_status() 결과
        stock_count: 감시 종목 수
        is_scanning: 스캔 진행 중 여부

    Returns:
        포맷된 메시지
    """
    msg = "📊 <b>시장 상태</b>\n\n"
    msg += f"⏰ 현재 시간 (KST): {market_status['time']}\n\n"

    if market_status['is_open']:
        msg += "🇺🇸 미국 장중 (22:00-07:00 KST)\n"
        msg += f"   감시 중: {stock_count}개 종목\n"
    else:
        msg += "🇺🇸 미국 장 마감\n"
        msg += "\n⏸️  휴장 시간입니다"

    if is_scanning:
        msg += "\n\n🔄 현재 스캔 진행 중..."

    return msg