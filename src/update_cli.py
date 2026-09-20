"""GUI 없이 콘솔에서 바로 업데이트를 확인/적용하는 진입점.

run_gui.bat이 안 뜨거나 GUI 자체가 고장났을 때를 대비한 예비 경로.
"""

from __future__ import annotations

import sys

import updater


def main() -> None:
    try:
        message = updater.check_and_update()
    except Exception as e:  # noqa: BLE001
        print(f"업데이트 확인 중 오류가 발생했어: {e}")
        sys.exit(1)
    print(message)


if __name__ == "__main__":
    main()
