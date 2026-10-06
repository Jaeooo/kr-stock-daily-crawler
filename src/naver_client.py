"""네이버 증권(m.stock.naver.com) 개별 종목 API 클라이언트."""

from __future__ import annotations

import time

import requests

INTEGRATION_URL = "https://m.stock.naver.com/api/stock/{code}/integration"
LONG_CHART_URL = "https://api.stock.naver.com/chart/domestic/item/{code}"
HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
RETRY_BACKOFF_SEC = 1.5


def fetch_integration(code: str) -> dict:
    """종목코드에 대한 네이버 integration API 원본 응답을 반환한다. 실패 시 빈 dict."""
    url = INTEGRATION_URL.format(code=code)
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 - 네트워크 예외를 폭넓게 잡아 재시도
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
    print(f"[naver_client] {code} 조회 실패: {last_error}")
    return {}


def fetch_deal_trend(code: str) -> list[dict]:
    """종목코드에 대한 최근 거래일별 종가/기관/외국인/외국인보유율/거래량 목록을 반환한다.

    반환 형식은 네이버 integration API의 dealTrendInfos 원본 리스트 그대로이며,
    각 항목은 최소한 bizdate, closePrice, organPureBuyQuant, foreignerPureBuyQuant,
    foreignerHoldRatio, accumulatedTradingVolume 키를 가진다.
    실패 시 빈 리스트를 반환한다.

    주의: foreignerHoldRatio는 "외국인 보유율"(발행주식 대비)이지, 투자한도가 있는
    종목에서 네이버가 "외인소진율"이라고 부르는 한도 대비 비율과는 다르다.
    진짜 소진율이 필요하면 true_exhaustion_ratio()를 함께 써야 한다.
    """
    return fetch_integration(code).get("dealTrendInfos", [])


def fetch_long_foreign_history(code: str) -> list[dict]:
    """종목코드에 대한 장기(~110거래일) 종가/거래량/외국인보유율 이력을 반환한다.

    이 엔드포인트(api.stock.naver.com)는 m.stock.naver.com의 integration API와
    달리 기관/외국인 순매매량은 제공하지 않는다 — 종가/거래량/외국인보유율만 있다.
    각 항목은 localDate(YYYYMMDD), closePrice, accumulatedTradingVolume,
    foreignRetentionRate(숫자, % 기호 없음) 키를 가진다. 실패 시 빈 리스트.
    """
    url = LONG_CHART_URL.format(code=code)
    params = {"periodType": "dayCandle", "additionalIndicatorType": "foreign"}
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return data.get("priceInfos", [])
        except Exception as e:  # noqa: BLE001
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
    print(f"[naver_client] {code} 장기 이력 조회 실패: {last_error}")
    return []


def find_row_for_date(deal_trend_infos: list[dict], bizdate: str) -> dict | None:
    """bizdate(YYYYMMDD)에 해당하는 행을 찾는다."""
    for row in deal_trend_infos:
        if row.get("bizdate") == bizdate:
            return row
    return None


def _parse_percent(value: str) -> float | None:
    try:
        return float(value.rstrip("%").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def get_today_exhaustion_ratio(integration_data: dict) -> float | None:
    """integration 응답의 totalInfos에서 '오늘 기준' 진짜 외국인소진율(한도 대비, %)을 찾는다."""
    for info in integration_data.get("totalInfos", []):
        if info.get("code") == "foreignRate":
            return _parse_percent(info.get("value", ""))
    return None


def true_exhaustion_ratio(integration_data: dict, target_hold_ratio: str) -> str | None:
    """특정 날짜의 외국인 보유율(target_hold_ratio, %)을, 오늘자 보유율/소진율 비로
    역산한 투자한도를 이용해 '그 날짜의 진짜 소진율'로 환산한다.

    외국인 투자한도가 100%인 종목(대부분)은 보유율=소진율이라 값이 그대로 나오고,
    한도가 더 낮은 종목(KT 등)은 한도 대비 비율로 환산된 값이 나온다.
    역산에 필요한 정보가 없으면 None을 반환한다 (호출 쪽에서 보유율로 대체 처리).
    """
    deal_trend = integration_data.get("dealTrendInfos", [])
    if not deal_trend:
        return None

    today_exhaustion = get_today_exhaustion_ratio(integration_data)
    today_hold = _parse_percent(deal_trend[0].get("foreignerHoldRatio", ""))
    target_hold = _parse_percent(target_hold_ratio)

    if today_exhaustion is None or today_hold is None or target_hold is None:
        return None
    if today_exhaustion == 0:
        return None

    implied_limit = today_hold / today_exhaustion * 100  # 외국인 투자한도(%)
    if implied_limit == 0:
        return None

    return f"{target_hold / implied_limit * 100:.2f}"
