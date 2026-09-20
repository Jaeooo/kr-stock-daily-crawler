"""종가 크롤러 진입점.

인자 없이 실행하면 오늘 날짜 기준으로 티커리스트.xlsx를 읽어
종가{M}-{D}.xlsx를 생성한다.

    python main.py

개발/테스트용으로 --date 옵션을 남겨뒀지만 (예: --date 2026-09-11),
일반 사용 시에는 쓸 필요 없다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import build_report


class _Tee:
    """print() 출력을 콘솔과 로그 파일에 동시에 남기기 위한 헬퍼."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)

    def flush(self):
        for s in self._streams:
            s.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="네이버 증권에서 당일 종가/기관/외국인 데이터를 받아 엑셀로 만든다.")
    parser.add_argument("--date", help=argparse.SUPPRESS, default=None)
    parser.add_argument("--ticker-list", help=argparse.SUPPRESS, default=str(build_report.DEFAULT_TICKER_LIST))
    parser.add_argument("--out-dir", help=argparse.SUPPRESS, default=str(build_report.DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    log_path = out_dir / f"run_log_{today_str}.txt"
    with log_path.open("a", encoding="utf-8") as log_file:
        original_stdout = sys.stdout
        sys.stdout = _Tee(original_stdout, log_file)
        try:
            build_report.run(
                ticker_list_path=Path(args.ticker_list),
                output_dir=out_dir,
                target=target,
            )
        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    main()
