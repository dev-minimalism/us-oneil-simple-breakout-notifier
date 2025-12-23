"""시장 상태 확인 (미국 주식 - 확장 시간 지원)"""
from datetime import datetime, time as dt_time, timedelta
from typing import Dict


# 시장 세션 정의 (한국 시간 기준)
MARKET_SESSIONS = {
    'day_market': {
        'name': '데이마켓',
        'emoji': '🌅',
        'start': dt_time(10, 0),
        'end': dt_time(17, 50),
    },
    'pre_market': {
        'name': '프리마켓',
        'emoji': '🌆',
        'start': dt_time(18, 0),
        'end': dt_time(23, 30),
    },
    'regular': {
        'name': '정규장',
        'emoji': '🏛️',
        'start': dt_time(23, 30),
        'end': dt_time(6, 0),  # 다음날
    },
    'after_market': {
        'name': '애프터마켓',
        'emoji': '🌙',
        'start': dt_time(6, 0),
        'end': dt_time(9, 50),
    },
}


def get_current_session(current_time: dt_time) -> str | None:
    """
    현재 시간에 해당하는 시장 세션 반환

    Args:
        current_time: 현재 시간

    Returns:
        세션 키 ('day_market', 'pre_market', 'regular', 'after_market') 또는 None (휴장)
    """
    # 데이마켓: 10:00~17:50
    if dt_time(10, 0) <= current_time < dt_time(17, 50):
        return 'day_market'

    # 프리마켓: 18:00~23:30
    if dt_time(18, 0) <= current_time < dt_time(23, 30):
        return 'pre_market'

    # 정규장: 23:30~06:00 (자정 넘어감)
    if current_time >= dt_time(23, 30) or current_time < dt_time(6, 0):
        return 'regular'

    # 애프터마켓: 06:00~09:50
    if dt_time(6, 0) <= current_time < dt_time(9, 50):
        return 'after_market'

    # 휴장: 09:50~10:00, 17:50~18:00
    return None


def get_market_status() -> Dict:
    """
    현재 시간에 따른 미국 시장 상태 확인 (한국 시간 기준)

    Returns:
        {
            'is_open': bool - 시장 열림 여부,
            'session': str | None - 현재 세션 키,
            'session_name': str - 현재 세션 이름,
            'session_emoji': str - 현재 세션 이모지,
            'time': str - 현재 시간,
            'weekday': int - 요일 (0=월요일, 6=일요일)
        }
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()

    # 주말 체크 (토요일 09:50 이후 ~ 일요일 전체 ~ 월요일 10:00 이전)
    is_weekend = False
    if weekday == 5 and current_time >= dt_time(9, 50):  # 토요일 애프터마켓 종료 후
        is_weekend = True
    elif weekday == 6:  # 일요일 전체
        is_weekend = True

    session = None
    session_name = "휴장"
    session_emoji = "⏸️"

    if not is_weekend:
        session = get_current_session(current_time)
        if session:
            session_info = MARKET_SESSIONS[session]
            session_name = session_info['name']
            session_emoji = session_info['emoji']

    return {
        'is_open': session is not None,
        'session': session,
        'session_name': session_name,
        'session_emoji': session_emoji,
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def get_next_scan_time() -> datetime:
    """
    다음 스캔 시간 계산 (매시간 :02, :32)

    Returns:
        다음 스캔 시간 (datetime)
    """
    now = datetime.now()
    minute = now.minute

    if minute < 2:
        # 현재 시간의 :02
        next_scan = now.replace(minute=2, second=0, microsecond=0)
    elif minute < 32:
        # 현재 시간의 :32
        next_scan = now.replace(minute=32, second=0, microsecond=0)
    else:
        # 다음 시간의 :02
        next_scan = (now + timedelta(hours=1)).replace(minute=2, second=0, microsecond=0)

    return next_scan


def get_seconds_until_next_scan() -> int:
    """
    다음 스캔까지 남은 초 계산

    Returns:
        남은 초
    """
    next_scan = get_next_scan_time()
    delta = next_scan - datetime.now()
    return max(0, int(delta.total_seconds()))


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

    session_emoji = market_status['session_emoji']
    session_name = market_status['session_name']

    if market_status['is_open']:
        msg += f"{session_emoji} <b>{session_name}</b> 진행 중\n"
        msg += f"   감시 중: {stock_count}개 종목\n\n"

        # 세션별 시간 표시
        session = market_status['session']
        if session:
            session_info = MARKET_SESSIONS[session]
            start = session_info['start'].strftime('%H:%M')
            end = session_info['end'].strftime('%H:%M')
            msg += f"   ⏱️ {start} ~ {end} KST\n"

        # 다음 스캔 시간
        next_scan = get_next_scan_time()
        msg += f"\n   ⏭️ 다음 스캔: {next_scan.strftime('%H:%M')}"
    else:
        msg += f"{session_emoji} {session_name}\n"

        # 주말 여부 확인
        if market_status['weekday'] >= 5:
            msg += "\n📅 주말 휴장"
        else:
            msg += "\n⏸️ 휴장 시간입니다"

    if is_scanning:
        msg += "\n\n🔄 현재 스캔 진행 중..."

    return msg
