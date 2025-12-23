"""로깅 설정 (한국 시간 기준 일별 롤링)"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo


# 한국 시간대
KST = ZoneInfo("Asia/Seoul")


class KSTTimedRotatingFileHandler(TimedRotatingFileHandler):
    """한국 시간 기준으로 롤링하는 파일 핸들러"""

    def computeRollover(self, currentTime):
        """한국 시간 기준 자정에 롤링"""
        # 현재 시간을 KST로 변환
        kst_now = datetime.fromtimestamp(currentTime, tz=KST)

        # 다음 날 자정 계산
        kst_midnight = kst_now.replace(hour=0, minute=0, second=0, microsecond=0)
        if kst_now >= kst_midnight:
            # 이미 자정을 지났으면 다음 날 자정
            from datetime import timedelta
            kst_midnight += timedelta(days=1)

        return int(kst_midnight.timestamp())

    def doRollover(self):
        """롤링 시 한국 시간 기준 날짜로 파일명 생성"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # 한국 시간 기준 날짜
        kst_now = datetime.now(KST)

        # 현재 파일을 날짜 붙은 이름으로 변경
        dfn = self.rotation_filename(
            self.baseFilename + "." + kst_now.strftime("%Y%m%d")
        )

        if os.path.exists(dfn):
            os.remove(dfn)

        self.rotate(self.baseFilename, dfn)

        # 새 파일 스트림 열기
        self.stream = self._open()

        # 다음 롤링 시간 계산
        currentTime = int(datetime.now().timestamp())
        self.rolloverAt = self.computeRollover(currentTime)


class KSTFormatter(logging.Formatter):
    """한국 시간으로 타임스탬프를 표시하는 포매터"""

    def formatTime(self, record, datefmt=None):
        kst_time = datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return kst_time.strftime(datefmt)
        return kst_time.strftime("%Y-%m-%d %H:%M:%S")


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """
    로깅 설정

    Args:
        log_dir: 로그 파일 디렉토리
        log_level: 로그 레벨

    Returns:
        설정된 루트 로거
    """
    # 로그 디렉토리 생성
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 포맷 설정
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    formatter = KSTFormatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (한국 시간 기준 일별 롤링)
    log_file = log_path / "bot.log"
    file_handler = KSTTimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,  # 30일치 보관
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # print를 로거로 리다이렉트
    sys.stdout = LoggerWriter(root_logger, logging.INFO)
    sys.stderr = LoggerWriter(root_logger, logging.ERROR)

    return root_logger


class LoggerWriter:
    """print 출력을 로거로 리다이렉트"""

    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self.buffer = ""

    def write(self, message: str):
        if message and message.strip():
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        pass

    def isatty(self):
        return False
