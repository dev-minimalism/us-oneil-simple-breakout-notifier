#!/usr/bin/env python3
"""PostgreSQL 데이터베이스 연결 테스트 스크립트

사용법:
    python scripts/test_db_connection.py
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from us_oneil_simple.database import get_db_connection, PositionRepository, AlertRepository


def test_connection():
    """DB 연결 테스트"""
    print("=" * 60)
    print("PostgreSQL 데이터베이스 연결 테스트")
    print("=" * 60)

    try:
        # 연결
        print("\n1. SSH 터널 및 DB 연결 시도...")
        db = get_db_connection()
        db.connect()
        print("  연결 성공!")

        # 테이블 초기화
        print("\n2. 테이블 초기화...")
        db.init_tables()
        print("  테이블 초기화 완료!")

        # 테스트 데이터 삽입
        print("\n3. 테스트 포지션 추가...")
        pos_repo = PositionRepository(db)
        test_position = pos_repo.add(
            ticker="TEST",
            market="US",
            entry_price=100.0,
            pattern="테스트패턴",
            stop_loss=92.0,
            take_profit=120.0,
            signal_data={"test": True}
        )
        if test_position:
            print(f"  포지션 추가 성공: {test_position.ticker}")
        else:
            print("  포지션 이미 존재 (중복 방지)")

        # 포지션 조회
        print("\n4. 포지션 조회...")
        positions = pos_repo.get_all_open()
        print(f"  열린 포지션 수: {len(positions)}개")
        for pos in positions:
            print(f"    - {pos.ticker}: ${pos.entry_price} ({pos.pattern})")

        # 알림 테스트
        print("\n5. 알림 기록 테스트...")
        alert_repo = AlertRepository(db)
        alert = alert_repo.add(
            ticker="TEST",
            market="US",
            pattern="테스트패턴",
            alert_price=100.0,
            signal_data={"test": True}
        )
        if alert:
            print(f"  알림 기록 성공: {alert.ticker}")
        else:
            print("  알림 이미 존재 (오늘 중복 방지)")

        # 중복 체크
        print("\n6. 중복 알림 체크...")
        has_alert = alert_repo.has_alert_today("TEST", "테스트패턴")
        print(f"  오늘 TEST/테스트패턴 알림 존재: {has_alert}")

        # 테스트 데이터 정리
        print("\n7. 테스트 데이터 정리...")
        pos_repo.close("TEST", 100.0, "테스트 완료", 0.0)
        print("  테스트 포지션 청산 완료!")

        print("\n" + "=" * 60)
        print("모든 테스트 통과!")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if 'db' in locals():
            db.close()
            print("\n연결 종료")

    return True


if __name__ == "__main__":
    test_connection()