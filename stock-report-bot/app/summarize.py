from __future__ import annotations

import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .models import NewsItem, StockMove


PROJECT_ROOT = Path(__file__).resolve().parents[1]
THEME_MEMORY_PATH = PROJECT_ROOT / "config" / "theme_memory.csv"
HIGH_CONFIDENCE_MEMORY_COUNT = 5
HIGH_CONFIDENCE_MEMORY_SCORE = 0.80
FALLBACK_MEMORY_COUNT = 5
FALLBACK_MEMORY_SCORE = 0.55
NON_OVERRIDING_MEMORY_THEMES = {"개별주"}

KEYWORD_CAUSES: tuple[tuple[str, str], ...] = (
    ("액면병합", "액면병합/거래재개 이슈"),
    ("주식병합", "액면병합/거래재개 이슈"),
    ("거래재개", "액면병합/거래재개 이슈"),
    ("거래 재개", "액면병합/거래재개 이슈"),
    ("자율주행", "자율주행/모빌리티 테마"),
    ("전력기기", "전력기기/전력망 테마"),
    ("변압기", "전력기기/전력망 테마"),
    ("전선", "전력기기/전력망 테마"),
    ("전력망", "전력기기/전력망 테마"),
    ("조선", "조선/기자재 테마"),
    ("공급계약", "공급계약/수주 기대감"),
    ("수주", "공급계약/수주 기대감"),
    ("실적", "실적 개선 기대감"),
    ("흑자", "실적 개선 기대감"),
    ("정책", "정책 수혜 기대감"),
    ("정부", "정책 수혜 기대감"),
    ("인수", "인수합병/지분 이슈"),
    ("합병", "인수합병/지분 이슈"),
    ("임상", "바이오 임상/허가 이슈"),
    ("허가", "바이오 임상/허가 이슈"),
    ("AI", "AI 테마 부각"),
    ("반도체", "반도체 업황/테마 부각"),
    ("배터리", "2차전지 테마 부각"),
    ("원전", "원전 테마 부각"),
    ("방산", "방산 테마 부각"),
)

STOCK_NAME_CAUSES: tuple[tuple[str, str], ...] = (
    ("로보", "로봇 테마 부각"),
    ("로봇", "로봇 테마 부각"),
    ("보틱스", "로봇 테마 부각"),
    ("오토메이션", "로봇 테마 부각"),
)


def infer_cause(stock: StockMove, news: list[NewsItem]) -> str:
    stock_name_cause = _infer_from_stock_name(stock.name)
    if stock_name_cause:
        return stock_name_cause

    news_text = _join_news_text(news)
    high_confidence_memory = _infer_from_theme_memory(
        stock.name,
        min_count=HIGH_CONFIDENCE_MEMORY_COUNT,
        min_confidence=HIGH_CONFIDENCE_MEMORY_SCORE,
    )
    if high_confidence_memory:
        return high_confidence_memory

    if news:
        lead_causes = _extract_causes(news[0].title + " " + news[0].description)
        if lead_causes:
            return Counter(lead_causes).most_common(1)[0][0]

    causes = _extract_causes(news_text)

    if causes:
        return Counter(causes).most_common(1)[0][0]

    fallback_memory = _infer_from_theme_memory(
        stock.name,
        min_count=FALLBACK_MEMORY_COUNT,
        min_confidence=FALLBACK_MEMORY_SCORE,
    )
    if fallback_memory:
        return fallback_memory

    if "상한가" in stock.reasons:
        return "상한가 기록, 구체적 재료는 추가 확인 필요"
    if stock.change_percent >= 12:
        return "급등세 부각, 구체적 재료는 추가 확인 필요"
    if stock.volume >= 10_000_000:
        return "거래량 급증, 수급성 이슈 추가 확인 필요"

    return "관련 뉴스 기반 원인 확인 필요"


def _infer_from_stock_name(name: str) -> str:
    for keyword, cause in STOCK_NAME_CAUSES:
        if keyword in name:
            return cause
    return ""


def _extract_causes(text: str) -> list[str]:
    lowered = text.lower()
    causes = []

    for keyword, cause in KEYWORD_CAUSES:
        if keyword.lower() in lowered:
            causes.append(cause)

    return causes


def _join_news_text(news: list[NewsItem]) -> str:
    return " ".join([item.title + " " + item.description for item in news])


def _infer_from_theme_memory(name: str, min_count: int, min_confidence: float) -> str:
    entry = _load_theme_memory().get(name)
    if not entry:
        return ""

    theme = entry["preferred_theme"]
    if theme in NON_OVERRIDING_MEMORY_THEMES:
        return ""

    if int(entry["preferred_count"]) < min_count:
        return ""
    if float(entry["confidence"]) < min_confidence:
        return ""

    return theme


@lru_cache(maxsize=1)
def _load_theme_memory() -> dict[str, dict[str, str]]:
    if not THEME_MEMORY_PATH.exists():
        return {}

    with THEME_MEMORY_PATH.open(encoding="utf-8", newline="") as file:
        return {row["stock_name"]: row for row in csv.DictReader(file)}


def summarize_news(news: list[NewsItem]) -> str:
    if not news:
        return "관련 뉴스 검색 결과가 없습니다. 종목 공시와 장중 특징주 기사를 별도로 확인하세요."

    lead = news[0]
    summary = lead.description or lead.title
    return summary.strip() or "기사 요약문이 제공되지 않았습니다."
