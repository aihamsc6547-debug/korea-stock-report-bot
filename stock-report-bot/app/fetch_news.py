from __future__ import annotations

import html
import json
import re
import time
from datetime import date, datetime, time as datetime_time, timedelta
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .config import Settings
from .models import NewsItem, StockMove


NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
MIN_REQUEST_INTERVAL_SECONDS = 0.35
MAX_RETRIES = 4
FEATURE_NEWS_QUERIES = ("특징주", "상한가 특징주", "급등 특징주")
FEATURE_NEWS_DISPLAY = 100
FEATURE_NEWS_MAX_PAGES = 3
KST = ZoneInfo("Asia/Seoul")
_LAST_REQUEST_AT = 0.0


def fetch_stock_news(stock: StockMove, settings: Settings, display: int | None = None) -> list[NewsItem]:
    if not settings.naver_client_id or not settings.naver_client_secret:
        return []

    for query in _build_news_queries(stock):
        items = _fetch_news_query(query, settings, display=display or settings.news_display)
        ranked = _rank_news_items(stock, items)
        if ranked:
            return ranked

    return []


def fetch_feature_news(report_date: date, settings: Settings) -> list[NewsItem]:
    if not settings.naver_client_id or not settings.naver_client_secret:
        return []

    collected: list[NewsItem] = []
    for query in FEATURE_NEWS_QUERIES:
        for page in range(FEATURE_NEWS_MAX_PAGES):
            start = page * FEATURE_NEWS_DISPLAY + 1
            items = _fetch_news_query(query, settings, display=FEATURE_NEWS_DISPLAY, start=start)
            if not items:
                break
            collected.extend(filter_feature_news_items(items, report_date))

    return _dedupe_news_items(collected)


def filter_feature_news_items(items: list[NewsItem], report_date: date) -> list[NewsItem]:
    return [
        item
        for item in items
        if "특징주" in item.title and _is_after_market_open(item.pub_date, report_date)
    ]


def _fetch_news_query(query: str, settings: Settings, display: int, start: int = 1) -> list[NewsItem]:
    params = urlencode(
        {
            "query": query,
            "display": display,
            "start": start,
            "sort": "date",
        }
    )
    request = Request(
        f"{NAVER_NEWS_ENDPOINT}?{params}",
        headers={
            "X-Naver-Client-Id": settings.naver_client_id,
            "X-Naver-Client-Secret": settings.naver_client_secret,
        },
    )

    payload = _request_news_payload(request)
    return [_parse_news_item(item) for item in payload.get("items", [])]


def _build_news_queries(stock: StockMove) -> list[str]:
    queries = [f"{stock.name} 특징주"]

    if "상한가" in stock.reasons:
        queries.append(f"{stock.name} 상한가")
    elif stock.change_percent >= 12:
        queries.append(f"{stock.name} 급등")

    if stock.volume >= 10_000_000:
        queries.append(f"{stock.name} 거래량")

    queries.append(stock.name)

    deduped: list[str] = []
    for query in queries:
        if query not in deduped:
            deduped.append(query)
    return deduped[:3]


def _dedupe_news_items(items: list[NewsItem]) -> list[NewsItem]:
    deduped: list[NewsItem] = []
    seen: set[str] = set()
    for item in items:
        key = item.originallink or item.link or item.title
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _is_after_market_open(pub_date: datetime | None, report_date: date) -> bool:
    if not pub_date:
        return False

    local_pub_date = pub_date.astimezone(KST) if pub_date.tzinfo else pub_date.replace(tzinfo=KST)
    market_open = datetime.combine(report_date, datetime_time(9, 0), tzinfo=KST)
    next_day = datetime.combine(report_date + timedelta(days=1), datetime_time(0, 0), tzinfo=KST)
    return market_open <= local_pub_date < next_day


def _request_news_payload(request: Request) -> dict:
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        _respect_rate_limit()
        try:
            with urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code in (401, 403):
                raise RuntimeError(
                    "네이버 뉴스 API 인증 또는 권한 오류입니다. Client ID/Secret과 검색 API 사용 설정을 확인하세요."
                ) from exc
            if exc.code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            return {}
        except (TimeoutError, URLError) as exc:
            last_error = exc
            time.sleep(1.0 * (attempt + 1))

    if isinstance(last_error, HTTPError) and last_error.code == 429:
        return {}

    return {}


def _respect_rate_limit() -> None:
    global _LAST_REQUEST_AT

    elapsed = time.monotonic() - _LAST_REQUEST_AT
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)
    _LAST_REQUEST_AT = time.monotonic()


def _parse_news_item(item: dict) -> NewsItem:
    pub_date = None
    if item.get("pubDate"):
        try:
            pub_date = parsedate_to_datetime(item["pubDate"])
        except (TypeError, ValueError):
            pub_date = None

    return NewsItem(
        title=_clean_html(item.get("title", "")),
        link=item.get("link", ""),
        originallink=item.get("originallink", ""),
        description=_clean_html(item.get("description", "")),
        pub_date=pub_date if isinstance(pub_date, datetime) else None,
    )


def _clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(without_tags).strip()


def _rank_news_items(stock: StockMove, items: list[NewsItem]) -> list[NewsItem]:
    scored = [(item, _relevance_score(stock, item)) for item in items]
    positive = [pair for pair in scored if pair[1] > 0]
    return [item for item, _ in sorted(positive, key=lambda pair: pair[1], reverse=True)]


def _relevance_score(stock: StockMove, item: NewsItem) -> int:
    title = item.title
    description = item.description
    score = 0

    if stock.name in title:
        score += 100
    if stock.code in title:
        score += 20

    if not score:
        return 0

    if stock.name in description:
        score += 20
    if stock.code in description:
        score += 10
    if any(keyword in title for keyword in ("특징주", "상한가", "급등", "거래량")):
        score += 10

    return score
