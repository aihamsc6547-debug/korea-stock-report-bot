from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from .models import NewsItem, StockMove


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STOCK_THEME_KEYWORDS_PATH = PROJECT_ROOT / "config" / "stock_theme_keywords.csv"
MARKET_NEWS_TITLE_KEYWORDS = ("특징주", "상한가", "급등", "강세", "신고가")
IGNORED_PROFILE_TOKENS = {"기타", "신규상장"}
COMPACT_IGNORED_PROFILE_TOKENS = {re.sub(r"[\s#/()·,._-]+", "", value).lower() for value in IGNORED_PROFILE_TOKENS}


def assign_feature_news_to_stocks(
    stocks: list[StockMove],
    news_pool: list[NewsItem],
    per_stock_limit: int = 3,
) -> dict[str, list[NewsItem]]:
    assigned: dict[str, list[NewsItem]] = {}

    for stock in stocks:
        scored = [
            (news, _assignment_score(stock, news))
            for news in news_pool
        ]
        matches = [(news, score) for news, score in scored if score > 0]
        if not matches:
            continue

        ranked = sorted(
            matches,
            key=lambda pair: (pair[1], _news_timestamp(pair[0])),
            reverse=True,
        )
        assigned[stock.code] = [news for news, _ in ranked[:per_stock_limit]]

    return assigned


def merge_news_lists(*news_lists: list[NewsItem], limit: int | None = None) -> list[NewsItem]:
    merged: list[NewsItem] = []
    seen: set[str] = set()

    for news_list in news_lists:
        for item in news_list:
            key = item.originallink or item.link or item.title
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if limit is not None and len(merged) >= limit:
                return merged

    return merged


def _assignment_score(stock: StockMove, news: NewsItem) -> int:
    title = news.title
    description = news.description
    text = title + " " + description
    title_has_market_keyword = any(keyword in title for keyword in MARKET_NEWS_TITLE_KEYWORDS)
    direct_score = 0

    if stock.name in title:
        direct_score += 120
    if stock.name in description:
        direct_score += 50
    if stock.code and stock.code in text:
        direct_score += 30

    profile_score = _profile_match_score(stock, news)
    if not direct_score and not title_has_market_keyword:
        return 0
    if not direct_score and profile_score < 22:
        return 0

    score = direct_score + profile_score
    if title_has_market_keyword:
        score += 10
    return score


def _profile_match_score(stock: StockMove, news: NewsItem) -> int:
    profile = _find_stock_theme_profile(stock)
    if not profile:
        return 0

    compact_title = _compact(news.title)
    compact_description = _compact(news.description)
    score = 0

    for token in _profile_tokens(profile):
        compact_token = _compact(token)
        if compact_token in compact_title:
            score += 22
        elif compact_token in compact_description:
            score += 8

    return score


def _find_stock_theme_profile(stock: StockMove) -> dict[str, str] | None:
    profiles = _load_stock_theme_profiles()
    return profiles["by_code"].get(_normalize_stock_code(stock.code)) or profiles["by_name"].get(stock.name)


def _profile_tokens(profile: dict[str, str]) -> list[str]:
    tokens: list[str] = []
    for column in ("subthemes", "keywords"):
        for raw_token in re.split(r"\s*\|\s*|/", profile[column]):
            token = raw_token.strip().lstrip("#").strip()
            if _is_usable_profile_token(token) and token not in tokens:
                tokens.append(token)
    return tokens


def _is_usable_profile_token(token: str) -> bool:
    compact = _compact(token)
    if len(compact) < 2:
        return False
    if compact in COMPACT_IGNORED_PROFILE_TOKENS:
        return False
    if re.search(r"20\d{2}년\d분기신규상장", compact):
        return False
    return True


@lru_cache(maxsize=1)
def _load_stock_theme_profiles() -> dict[str, dict[str, dict[str, str]]]:
    profiles = {"by_name": {}, "by_code": {}}
    if not STOCK_THEME_KEYWORDS_PATH.exists():
        return profiles

    with STOCK_THEME_KEYWORDS_PATH.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            profiles["by_name"][row["stock_name"]] = row
            profiles["by_code"][_normalize_stock_code(row["stock_code"])] = row

    return profiles


def _normalize_stock_code(code: str) -> str:
    digits = re.sub(r"\D", "", code)
    return digits.zfill(6) if digits else ""


def _compact(value: str) -> str:
    return re.sub(r"[\s#/()·,._-]+", "", value).lower()


def _news_timestamp(news: NewsItem) -> float:
    return news.pub_date.timestamp() if news.pub_date else 0.0
