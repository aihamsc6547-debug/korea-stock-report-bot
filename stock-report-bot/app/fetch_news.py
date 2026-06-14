from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Settings
from .models import NewsItem, StockMove


NAVER_NEWS_ENDPOINT = "https://openapi.naver.com/v1/search/news.json"
MIN_REQUEST_INTERVAL_SECONDS = 0.35
MAX_RETRIES = 4
_LAST_REQUEST_AT = 0.0


def fetch_stock_news(stock: StockMove, settings: Settings, display: int | None = None) -> list[NewsItem]:
    if not settings.naver_client_id or not settings.naver_client_secret:
        return []

    for query in _build_news_queries(stock):
        params = urlencode(
            {
                "query": query,
                "display": display or settings.news_display,
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
        items = payload.get("items", [])
        if items:
            return _rank_news_items(stock, [_parse_news_item(item) for item in items])

    return []


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
    ranked = positive if positive else scored
    return [item for item, _ in sorted(ranked, key=lambda pair: pair[1], reverse=True)]


def _relevance_score(stock: StockMove, item: NewsItem) -> int:
    title = item.title
    description = item.description
    score = 0

    if stock.name in title:
        score += 100
    if stock.name in description:
        score += 40
    if stock.code in title or stock.code in description:
        score += 20
    if any(keyword in title for keyword in ("특징주", "상한가", "급등", "거래량")):
        score += 10

    return score
