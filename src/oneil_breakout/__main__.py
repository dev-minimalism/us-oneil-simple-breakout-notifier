"""
윌리엄 오닐 돌파매매 봇 CLI 진입점 (미국 주식 전용)

사용법:
    python -m oneil_breakout          # 봇 실행
    python -m oneil_breakout backtest # 백테스트 실행
    python -m oneil_breakout scan     # 즉시 스캔 (1회)
"""
import argparse
import sys

from .bot import BreakoutDetector
from .config import load_settings


def main():
    """메인 CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="윌리엄 오닐 돌파매매 봇 - 미국 주식 전용 (CAN SLIM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
    python -m oneil_breakout              # 봇 실행
    python -m oneil_breakout backtest     # 백테스트 실행
    python -m oneil_breakout scan         # 즉시 1회 스캔
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='실행할 명령')

    # run 명령 (기본)
    run_parser = subparsers.add_parser('run', help='봇 실행 (기본)')

    # scan 명령
    scan_parser = subparsers.add_parser('scan', help='즉시 스캔 (1회)')

    # backtest 명령
    backtest_parser = subparsers.add_parser('backtest', help='백테스트 실행')
    backtest_parser.add_argument('--start', type=str, help='시작일 (YYYY-MM-DD)')
    backtest_parser.add_argument('--end', type=str, help='종료일 (YYYY-MM-DD)')
    backtest_parser.add_argument('--capital', type=float, default=100_000,
                                 help='초기 자본 USD (기본: $100,000)')

    args = parser.parse_args()

    # 기본 명령어 (인자 없이 실행)
    if args.command is None or args.command == 'run':
        run_bot()
    elif args.command == 'scan':
        run_scan()
    elif args.command == 'backtest':
        run_backtest(args)


def run_bot():
    """봇 실행"""
    print("=" * 60)
    print("윌리엄 오닐 돌파매매 봇 - 미국 주식 전용 (CAN SLIM)")
    print("=" * 60)

    settings = load_settings()

    if not settings.telegram.token or settings.telegram.token == "YOUR_BOT_TOKEN_HERE":
        print("\n⚠️  텔레그램 설정이 필요합니다!")
        print("\n설정 방법:")
        print("  1. config.py 파일에서 TELEGRAM_TOKEN과 CHAT_ID 설정")
        print("  2. 또는 환경변수로 설정:")
        print("     export TELEGRAM_TOKEN='your_token'")
        print("     export TELEGRAM_CHAT_ID='your_chat_id'")
        sys.exit(1)

    detector = BreakoutDetector(settings)
    detector.run()


def run_scan():
    """즉시 스캔"""
    print("=" * 60)
    print("윌리엄 오닐 돌파매매 - 즉시 스캔 (미국 주식)")
    print("=" * 60)

    settings = load_settings()
    detector = BreakoutDetector(settings)
    detector.run_scan()


def run_backtest(args):
    """백테스트 실행"""
    from .backtest import BacktestEngine
    from datetime import datetime, timedelta

    print("=" * 60)
    print("윌리엄 오닐 돌파매매 - 백테스트 (미국 주식)")
    print("=" * 60)

    settings = load_settings()

    # 기간 설정
    end_date = args.end or datetime.now().strftime('%Y-%m-%d')
    start_date = args.start or (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

    # 종목 리스트
    tickers = settings.watchlist.us_stocks[:20]  # 상위 20개

    # 백테스트 실행
    engine = BacktestEngine(initial_capital=args.capital)
    engine.run_portfolio_backtest(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        patterns=['cup', 'pivot', 'base']
    )

    engine.print_performance_report()
    engine.save_results('us_backtest_results.csv')


if __name__ == "__main__":
    main()