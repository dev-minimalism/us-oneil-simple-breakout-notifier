"""텔레그램 클라이언트"""
import requests


class TelegramClient:
    """텔레그램 API 클라이언트"""

    def __init__(self, token: str, chat_id: str):
        """
        Args:
            token: 텔레그램 봇 토큰
            chat_id: 텔레그램 채팅 ID
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0

    def send_message(self, message: str) -> bool:
        """
        텔레그램으로 메시지 전송

        Args:
            message: 전송할 메시지 (HTML 지원)

        Returns:
            전송 성공 여부
        """
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(f"{self.base_url}/sendMessage", data=payload)
            if response.status_code == 200:
                print(f"✅ 텔레그램 전송 성공")
                return True
            else:
                print(f"❌ 텔레그램 전송 실패: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 텔레그램 전송 오류: {e}")
            return False

    def get_updates(self, timeout: int = 10) -> list:
        """
        텔레그램 업데이트 확인

        Args:
            timeout: 롱 폴링 타임아웃 (초)

        Returns:
            업데이트 리스트
        """
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.last_update_id + 1,
                'timeout': timeout
            }
            response = requests.get(url, params=params, timeout=timeout + 5)

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
        except Exception as e:
            print(f"⚠️  텔레그램 업데이트 확인 오류: {e}")
            return []
