"""종목명 -> 종목코드 매핑을 네이버 증권 API로 구축하고 로컬에 캐싱한다."""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import requests

SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_FILE = OUTPUT_DIR / "stock_master_cache.csv"
CACHE_MAX_AGE_DAYS = 7

MARKET_VALUE_URL = "https://m.stock.naver.com/api/stocks/marketValue/{category}"
CATEGORIES = ["KOSPI", "KOSDAQ"]
PAGE_SIZE = 100
REQUEST_TIMEOUT = 10
REQUEST_DELAY_SEC = 0.2
HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass
class StockRecord:
    code: str
    name: str
    market: str


def _fetch_category(session: requests.Session, category: str) -> list[StockRecord]:
    records: list[StockRecord] = []
    page = 1
    while True:
        resp = session.get(
            MARKET_VALUE_URL.format(category=category),
            params={"page": page, "pageSize": PAGE_SIZE},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        stocks = data.get("stocks", [])
        if not stocks:
            break
        for s in stocks:
            records.append(StockRecord(code=s["itemCode"], name=s["stockName"], market=category))
        total = data.get("totalCount", 0)
        if page * PAGE_SIZE >= total:
            break
        page += 1
        time.sleep(REQUEST_DELAY_SEC)
    return records


def build_master() -> list[StockRecord]:
    """네이버에서 코스피+코스닥 전종목 코드/이름을 받아온다."""
    session = requests.Session()
    all_records: list[StockRecord] = []
    for category in CATEGORIES:
        all_records.extend(_fetch_category(session, category))
    return all_records


def save_cache(records: list[StockRecord]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "name", "market"])
        for r in records:
            writer.writerow([r.code, r.name, r.market])


def load_cache() -> list[StockRecord]:
    with CACHE_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [StockRecord(code=row["code"], name=row["name"], market=row["market"]) for row in reader]


def _cache_is_fresh() -> bool:
    if not CACHE_FILE.exists():
        return False
    mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
    return datetime.now() - mtime < timedelta(days=CACHE_MAX_AGE_DAYS)


def get_name_to_code_map(force_refresh: bool = False) -> dict[str, str]:
    """종목명 -> 종목코드 dict을 반환한다. 캐시가 오래됐거나 없으면 새로 받아온다."""
    if force_refresh or not _cache_is_fresh():
        records = build_master()
        save_cache(records)
    else:
        records = load_cache()

    name_to_code: dict[str, str] = {}
    duplicate_names: set[str] = set()
    for r in records:
        if r.name in name_to_code and name_to_code[r.name] != r.code:
            duplicate_names.add(r.name)
        name_to_code[r.name] = r.code

    if duplicate_names:
        print(f"[stock_master] 경고: 이름이 겹치는 종목 {len(duplicate_names)}개 발견 (마지막 값으로 덮어씀): "
              f"{sorted(duplicate_names)[:10]}{' ...' if len(duplicate_names) > 10 else ''}")

    return name_to_code
