#!/usr/bin/env python3
"""PostgreSQL 데이터베이스 생성 스크립트

사용법:
    python scripts/create_database.py
"""
import os
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent

# .env 파일 로드
load_dotenv(project_root / ".env")

# 환경 변수에서 설정 로드
SSH_HOST = os.environ.get('SSH_HOST', '')
SSH_PORT = int(os.environ.get('SSH_PORT', '22'))
SSH_USER = os.environ.get('SSH_USER', '')
SSH_KEY_PATH = Path(os.environ.get('SSH_KEY_PATH', '~/.ssh/id_rsa')).expanduser()

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', '')
DB_USER = os.environ.get('DB_USER', '')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')


def create_database():
    """데이터베이스 생성"""
    print("=" * 60)
    print("PostgreSQL 데이터베이스 생성")
    print("=" * 60)

    tunnel = None
    conn = None

    try:
        # SSH 터널 시작
        print("\n1. SSH 터널 연결...")
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, SSH_PORT),
            ssh_username=SSH_USER,
            ssh_pkey=str(SSH_KEY_PATH),
            remote_bind_address=(DB_HOST, DB_PORT),
            local_bind_address=('127.0.0.1', 0),
        )
        tunnel.start()
        print(f"  연결됨: localhost:{tunnel.local_bind_port}")

        # postgres DB에 연결
        print("\n2. postgres DB 연결...")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            database='postgres',  # 기본 DB
            user=DB_USER,
            password=DB_PASSWORD,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # DB 존재 여부 확인
        print(f"\n3. '{DB_NAME}' 데이터베이스 확인...")
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()

        if exists:
            print(f"  데이터베이스 '{DB_NAME}'이(가) 이미 존재합니다.")
        else:
            # DB 생성
            print(f"\n4. '{DB_NAME}' 데이터베이스 생성...")
            cursor.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"  데이터베이스 '{DB_NAME}' 생성 완료!")

        cursor.close()
        conn.close()

        # 새 DB에 연결하여 테이블 생성
        print(f"\n5. '{DB_NAME}' 연결 및 테이블 생성...")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        cursor = conn.cursor()

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
        """)

        # UNIQUE 제약 추가 (이미 있으면 무시)
        try:
            cursor.execute("""
                ALTER TABLE positions
                ADD CONSTRAINT positions_ticker_status_unique UNIQUE (ticker, status)
            """)
        except psycopg2.errors.DuplicateTable:
            conn.rollback()

        conn.commit()

        # alerts 테이블
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
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON alerts(ticker);
            CREATE INDEX IF NOT EXISTS idx_alerts_alert_date ON alerts(alert_date);
        """)

        # UNIQUE 제약 추가
        try:
            cursor.execute("""
                ALTER TABLE alerts
                ADD CONSTRAINT alerts_ticker_pattern_date_unique UNIQUE (ticker, pattern, alert_date)
            """)
        except psycopg2.errors.DuplicateTable:
            conn.rollback()

        conn.commit()
        print("  테이블 생성 완료!")

        print("\n" + "=" * 60)
        print("데이터베이스 및 테이블 생성 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()
        if tunnel:
            tunnel.stop()
        print("\n연결 종료")

    return True


if __name__ == "__main__":
    create_database()