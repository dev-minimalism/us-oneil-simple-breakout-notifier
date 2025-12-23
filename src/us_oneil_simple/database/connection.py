"""PostgreSQL 데이터베이스 연결 (SSH 터널 지원)"""
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor
from sshtunnel import SSHTunnelForwarder


class DatabaseConnection:
    """SSH 터널을 통한 PostgreSQL 연결 관리"""

    def __init__(
        self,
        # SSH 설정
        ssh_host: str = "",
        ssh_port: int = 22,
        ssh_user: str = "",
        ssh_key_path: str = "~/.ssh/id_rsa",
        # DB 설정
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "",
        db_user: str = "",
        db_password: str = "",
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_key_path = Path(ssh_key_path).expanduser()

        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password

        self._tunnel: SSHTunnelForwarder | None = None
        self._connection: psycopg2.extensions.connection | None = None

    def _start_tunnel(self) -> SSHTunnelForwarder:
        """SSH 터널 시작"""
        if self._tunnel is not None and self._tunnel.is_active:
            return self._tunnel

        self._tunnel = SSHTunnelForwarder(
            (self.ssh_host, self.ssh_port),
            ssh_username=self.ssh_user,
            ssh_pkey=str(self.ssh_key_path),
            remote_bind_address=(self.db_host, self.db_port),
            local_bind_address=('127.0.0.1', 0),  # 자동 포트 할당
        )
        self._tunnel.start()
        print(f"  SSH 터널 연결: {self.ssh_host}:{self.ssh_port} -> localhost:{self._tunnel.local_bind_port}")
        return self._tunnel

    def _stop_tunnel(self):
        """SSH 터널 종료"""
        if self._tunnel is not None:
            self._tunnel.stop()
            self._tunnel = None

    def _is_connection_alive(self) -> bool:
        """연결이 살아있는지 확인"""
        if self._connection is None or self._connection.closed:
            return False

        try:
            # 간단한 쿼리로 연결 상태 확인
            with self._connection.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _is_tunnel_alive(self) -> bool:
        """SSH 터널이 살아있는지 확인"""
        return self._tunnel is not None and self._tunnel.is_active

    def _reconnect(self):
        """연결 재시도"""
        print("  🔄 DB 연결 재시도 중...")

        # 기존 연결 정리
        try:
            if self._connection is not None:
                self._connection.close()
        except Exception:
            pass
        self._connection = None

        # 기존 터널 정리
        try:
            if self._tunnel is not None:
                self._tunnel.stop()
        except Exception:
            pass
        self._tunnel = None

        # 새로 연결
        return self._connect_internal()

    def _connect_internal(self) -> psycopg2.extensions.connection:
        """실제 연결 수행"""
        tunnel = self._start_tunnel()

        self._connection = psycopg2.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password,
        )
        print(f"  PostgreSQL 연결: {self.db_name}")
        return self._connection

    def connect(self) -> psycopg2.extensions.connection:
        """데이터베이스 연결 (자동 재연결 지원)"""
        # 터널과 연결이 모두 살아있으면 기존 연결 반환
        if self._is_tunnel_alive() and self._is_connection_alive():
            return self._connection

        # 터널이 죽었거나 연결이 끊어진 경우 재연결
        if self._tunnel is not None or self._connection is not None:
            print("  ⚠️ DB 연결 끊김 감지, 재연결 시도...")
            return self._reconnect()

        # 최초 연결
        return self._connect_internal()

    def close(self):
        """연결 종료"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._stop_tunnel()

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True) -> Generator:
        """커서 컨텍스트 매니저"""
        conn = self.connect()
        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def _execute_with_retry(self, query: str, params: tuple = None, fetch_one: bool = False, max_retries: int = 2):
        """쿼리 실행 (연결 끊김 시 재시도)"""
        last_error = None

        for attempt in range(max_retries):
            try:
                with self.get_cursor() as cursor:
                    cursor.execute(query, params)
                    if cursor.description:
                        return cursor.fetchone() if fetch_one else cursor.fetchall()
                    return None if fetch_one else []
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                print(f"  ❌ DB 쿼리 오류 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self._reconnect()
            except Exception as e:
                # 연결 오류가 아닌 경우 바로 raise
                raise e

        # 모든 재시도 실패
        raise last_error

    def execute(self, query: str, params: tuple = None) -> list:
        """쿼리 실행 및 결과 반환 (자동 재연결)"""
        result = self._execute_with_retry(query, params, fetch_one=False)
        return result if result else []

    def execute_one(self, query: str, params: tuple = None) -> dict | None:
        """단일 결과 반환 (자동 재연결)"""
        return self._execute_with_retry(query, params, fetch_one=True)

    def init_tables(self):
        """테이블 초기화"""
        with self.get_cursor() as cursor:
            # positions 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'US',
                    entry_price DECIMAL(15, 4) NOT NULL,
                    entry_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    pattern VARCHAR(50) NOT NULL,
                    stop_loss DECIMAL(15, 4),
                    take_profit DECIMAL(15, 4),
                    signal_data JSONB,
                    status VARCHAR(20) NOT NULL DEFAULT 'open',
                    exit_price DECIMAL(15, 4),
                    exit_date TIMESTAMP,
                    exit_reason VARCHAR(100),
                    profit_pct DECIMAL(10, 4),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
                CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
                CREATE INDEX IF NOT EXISTS idx_positions_entry_date ON positions(entry_date);

                -- open 상태일 때만 중복 방지 (partial unique index)
                CREATE UNIQUE INDEX IF NOT EXISTS idx_positions_ticker_open
                ON positions(ticker) WHERE status = 'open';
            """)

            # alerts 테이블 (중복 알림 방지용)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'US',
                    pattern VARCHAR(50) NOT NULL,
                    alert_date DATE NOT NULL DEFAULT CURRENT_DATE,
                    alert_price DECIMAL(15, 4) NOT NULL,
                    signal_data JSONB,
                    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, pattern, alert_date) -- 같은 날 동일 종목/패턴 중복 알림 방지
                );

                CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON alerts(ticker);
                CREATE INDEX IF NOT EXISTS idx_alerts_alert_date ON alerts(alert_date);
            """)

            print("  테이블 초기화 완료")


# 전역 연결 인스턴스 (싱글톤)
_db_instance: DatabaseConnection | None = None


def get_db_connection(
    ssh_host: str | None = None,
    ssh_port: int | None = None,
    ssh_user: str | None = None,
    ssh_key_path: str | None = None,
    db_host: str | None = None,
    db_port: int | None = None,
    db_name: str | None = None,
    db_user: str | None = None,
    db_password: str | None = None,
) -> DatabaseConnection:
    """데이터베이스 연결 인스턴스 반환 (싱글톤)"""
    global _db_instance

    if _db_instance is None:
        # 환경 변수에서 로드
        _db_instance = DatabaseConnection(
            ssh_host=ssh_host or os.environ.get('SSH_HOST', ''),
            ssh_port=ssh_port or int(os.environ.get('SSH_PORT', '22')),
            ssh_user=ssh_user or os.environ.get('SSH_USER', ''),
            ssh_key_path=ssh_key_path or os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa'),
            db_host=db_host or os.environ.get('DB_HOST', 'localhost'),
            db_port=db_port or int(os.environ.get('DB_PORT', '5432')),
            db_name=db_name or os.environ.get('DB_NAME', ''),
            db_user=db_user or os.environ.get('DB_USER', ''),
            db_password=db_password or os.environ.get('DB_PASSWORD', ''),
        )

    return _db_instance