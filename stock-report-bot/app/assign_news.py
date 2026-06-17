from __future__ import annotations

from .models import NewsItem, StockMove


MARKET_NEWS_TITLE_KEYWORDS = ("특징주", "상한가", "급등", "강세", "신고가")


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
    title_has_market_keyword = any(keyword in title for keyword in MARKET_NEWS_TITLE_KEYWORDS)
    direct_score = 0

    if stock.name in title:
        direct_score += 120
    if stock.code and stock.code in title:
        direct_score += 30

    if not direct_score:
        return 0

    if stock.name in description:
        direct_score += 20
    if stock.code and stock.code in description:
        direct_score += 10

    score = direct_score
    if title_has_market_keyword:
        score += 10
    return score


def _news_timestamp(news: NewsItem) -> float:
    return news.pub_date.timestamp() if news.pub_date else 0.0
