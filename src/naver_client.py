"""네이버 증권(m.stock.naver.com) 개별 종목 API 클라이언트."""

from __future__ import annotations

import time

import requests

INTEGRATION_URL = "https://m.stock.naver.com/api/stock/{code}/integration"
HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_BACKOFF_SEC = 1.5


def fetch_deal_trend(code: str) -> list[dict]:
    """종목코드에 대한 최근 거래일별 종가/기관/외국인/외국인소진율/거래량 목록을 반환한다.

    반환 형식은 네이버 integration API의 dealTrendInfos 원본 리스트 그대로이며,
    각 항목은 최소한 bizdate, closePrice, organPureBuyQuant, foreignerPureBuyQuant,
    foreignerHoldRatio, accumulatedTradingVolume 키를 가진다.
    실패 시 빈 리스트를 반환한다.
    """
    url = INTEGRATION_URL.format(code=code)
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data.get("dealTrendInfos", [])
        except Exception as e:  # noqa: BLE001 - 네트워크 예외를 폭넓게 잡아 재시도
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
    print(f"[naver_client] {code} 조회 실패: {last_error}")
    return []


def find_row_for_date(deal_trend_infos: list[dict], bizdate: str) -> dict | None:
    """bizdate(YYYYMMDD)에 해당하는 행을 찾는다."""
    for row in deal_trend_infos:
        if row.get("bizdate") == bizdate:
            return row
    return None
