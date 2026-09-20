#!/bin/bash
cd "$(dirname "$0")"

# macOS 시스템/Xcode Python에 딸려오는 Tk(8.5)는 다크모드/렌더링 버그가 있어서
# Tk 8.6 이상을 쓰는 python이 있으면 그걸 우선적으로 사용한다.
PYTHON_BIN="python3"
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import tkinter, sys; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if ! "$PYTHON_BIN" -c "import tkinter, sys; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)" >/dev/null 2>&1; then
  echo "경고: Tk 8.6 이상을 쓰는 python을 못 찾아서 화면이 깨질 수 있어."
  echo "  brew install python-tk@3.11  (또는 python.org에서 최신 Python 설치) 후 다시 실행해줘."
fi

"$PYTHON_BIN" src/gui.py
