"""텔레그램 클라이언트"""
import time
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


class TelegramClient:
    """텔레그램 API 클라이언트"""

    def __init__(self, token: str, chat_id: str, max_retries: int = 3):
        """
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 텔레그램 채팅 ID
            max_retries: 최대 재시도 횟수
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.max_retries = max_retries

    def _retry_request(self, method: str, url: str, retries: int = None, **kwargs) -> requests.Response | None:
        """
        재시도 로직이 포함된 HTTP 요청

        Args:
            method: HTTP 메소드 ('get' 또는 'post')
            url: 요청 URL
            retries: 재시도 횟수 (기본값: self.max_retries)
            **kwargs: requests에 전달할 추가 인자

        Returns:
            Response 객체 또는 None (모든 재시도 실패 시)
        """
        if retries is None:
            retries = self.max_retries

        request_func = requests.get if method == 'get' else requests.post

        for attempt in range(retries):
            try:
                response = request_func(url, **kwargs)
                return response
            except (Timeout, ConnectionError) as e:
                wait_time = 2 ** attempt  # 1, 2, 4초 대기
                if attempt < retries - 1:
                    print(f"⚠️  네트워크 오류 (재시도 {attempt + 1}/{retries}): {e}")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 네트워크 오류 (최대 재시도 초과): {e}")
            except RequestException as e:
                print(f"❌ 요청 오류: {e}")
                break

        return None

    def send_message(self, message: str) -> bool:
        """
        텔레그램으로 메시지 전송

        Args:
            message: 전송할 메시지 (HTML 지원)

        Returns:
            전송 성공 여부
        """
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = self._retry_request(
            'post',
            f"{self.base_url}/sendMessage",
            data=payload,
            timeout=30
        )

        if response is None:
            return False

        if response.status_code == 200:
            print(f"✅ 텔레그램 전송 성공")
            return True
        else:
            print(f"❌ 텔레그램 전송 실패: {response.status_code}")
            return False

    def get_updates(self, timeout: int = 10) -> list:
        """
        텔레그램 업데이트 확인

        Args:
            timeout: 롱 폴링 타임아웃 (초)

        Returns:
            업데이트 리스트
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': timeout
        }
        # 롱 폴링은 재시도 1회로 제한 (타임아웃이 정상 동작일 수 있음)
        response = self._retry_request(
            'get',
            url,
            retries=1,
            params=params,
            timeout=timeout + 10
        )

        if response is None:
            return []

        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and data.get('result'):
                updates = []
                for update in data['result']:
                    self.last_update_id = update['update_id']

                    if 'message' in update and 'text' in update['message']:
                        chat_id = str(update['message']['chat']['id'])
                        if chat_id == str(self.chat_id):
                            updates.append({
                                'text': update['message']['text'],
                                'chat_id': chat_id
                            })
                return updates
        return []
