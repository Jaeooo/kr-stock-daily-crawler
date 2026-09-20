#!/bin/bash
cd "$(dirname "$0")/.."
python3 src/main.py
echo
read -n 1 -s -r -p "완료. 아무 키나 누르면 창을 닫습니다..."
echo
