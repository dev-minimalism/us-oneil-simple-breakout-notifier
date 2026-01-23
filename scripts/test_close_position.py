#!/usr/bin/env python3
"""포지션 청산 로직 테스트 스크립트"""
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from us_oneil_simple.database import DatabaseConnection, get_db_connection


def test_close_logic():
    """청산 로직 테스트"""
    print("=" * 60)
    print("포지션 청산 로직 테스트")
    print("=" * 60)

    db = get_db_connection()
    db.init_tables()

    # 1. 현재 open 포지션 확인
    print("\n[1] 현재 open 포지션 확인")
    open_positions = db.execute("SELECT id, ticker, status, entry_price FROM positions WHERE status = 'open'")
    print(f"  Open 포지션 수: {len(open_positions)}")
    for pos in open_positions:
        print(f"    - ID: {pos['id']}, Ticker: {pos['ticker']}, Price: {pos['entry_price']}")

    # 2. UPDATE ... RETURNING 테스트 (존재하지 않는 티커)
    print("\n[2] UPDATE RETURNING 테스트 (존재하지 않는 티커: FAKE_TICKER_XYZ)")
    query = """
        UPDATE positions
        SET status = 'closed',
            exit_price = 100.0,
            exit_date = CURRENT_TIMESTAMP,
            exit_reason = '테스트',
            profit_pct = 5.0,
            updated_at = CURRENT_TIMESTAMP
        WHERE ticker = %s AND status = 'open'
        RETURNING id
    """
    result = db.execute_one(query, ('FAKE_TICKER_XYZ',))
    print(f"  Result: {result}")
    print(f"  Success (result is not None): {result is not None}")

    # 3. 실제 open 포지션이 있다면 테스트 (dry-run)
    if open_positions:
        test_ticker = open_positions[0]['ticker']
        test_id = open_positions[0]['id']
        print(f"\n[3] 실제 포지션으로 SELECT 테스트 (ticker: {test_ticker})")

        # 실제 업데이트하지 않고 SELECT로 확인
        check_query = "SELECT id, ticker, status FROM positions WHERE ticker = %s AND status = 'open'"
        check_result = db.execute_one(check_query, (test_ticker,))
        print(f"  SELECT 결과: {check_result}")

        # 트랜잭션 롤백 테스트 (실제 청산하지 않음)
        print(f"\n[4] RETURNING 절 동작 확인 (롤백 예정)")
        try:
            with db.get_cursor() as cursor:
                cursor.execute(query, (test_ticker,))
                result = cursor.fetchone()
                print(f"  RETURNING 결과: {result}")
                print(f"  cursor.description: {cursor.description}")
                print(f"  cursor.rowcount: {cursor.rowcount}")
                # 의도적으로 예외 발생 → 롤백
                raise Exception("테스트 롤백")
        except Exception as e:
            print(f"  롤백됨: {e}")

        # 롤백 확인
        after_check = db.execute_one(check_query, (test_ticker,))
        print(f"  롤백 후 SELECT 결과: {after_check}")
        print(f"  포지션 유지됨: {after_check is not None}")
    else:
        print("\n[3] open 포지션이 없어서 실제 테스트 스킵")

    # 5. closed 포지션 확인
    print("\n[5] 최근 closed 포지션 확인")
    closed_positions = db.execute(
        "SELECT id, ticker, status, exit_reason, exit_date FROM positions WHERE status = 'closed' ORDER BY exit_date DESC LIMIT 5"
    )
    print(f"  Closed 포지션 수 (최근 5개): {len(closed_positions)}")
    for pos in closed_positions:
        print(f"    - ID: {pos['id']}, Ticker: {pos['ticker']}, Reason: {pos['exit_reason']}, Date: {pos['exit_date']}")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    test_close_logic()
