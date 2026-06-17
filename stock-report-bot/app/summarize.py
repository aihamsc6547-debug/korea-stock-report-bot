from __future__ import annotations

import csv
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from .models import NewsItem, StockMove


PROJECT_ROOT = Path(__file__).resolve().parents[1]
THEME_MEMORY_PATH = PROJECT_ROOT / "config" / "theme_memory.csv"
STOCK_THEME_KEYWORDS_PATH = PROJECT_ROOT / "config" / "stock_theme_keywords.csv"
HIGH_CONFIDENCE_MEMORY_COUNT = 5
HIGH_CONFIDENCE_MEMORY_SCORE = 0.80
FALLBACK_MEMORY_COUNT = 5
FALLBACK_MEMORY_SCORE = 0.55
NON_OVERRIDING_MEMORY_THEMES = {"개별주"}
CAUSE_NEWS_HINTS: dict[str, tuple[str, ...]] = {
    "남북경협/대북 테마": ("남북", "경협", "대북", "북한", "김정은", "개성공단", "금강산"),
    "로봇 테마 부각": ("로봇", "휴머노이드", "액추에이터", "감속기", "스마트팩토리", "의료로봇"),
    "전력기기/전력망 테마": ("전력기기", "전력망", "전선", "해저케이블", "스마트그리드"),
    "IT / 통신": ("통신", "통신장비", "5G", "6G", "유심", "USIM"),
}

STOCK_PROFILE_CAUSES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("남북경협/대북 테마", ("남북경협", "남북", "개성공단", "대북", "북한", "금강산")),
    ("로봇 테마 부각", ("휴머노이드", "로봇", "액추에이터", "감속기", "스마트팩토리", "의료로봇", "보스턴다이내믹스")),
    ("AI 테마 부각", ("AI", "인공지능", "데이터센터", "클라우드", "온디바이스AI")),
    ("전력기기/전력망 테마", ("전력기기", "전력망", "전선", "해저케이블", "스마트그리드")),
    ("전력 / 에너지", ("에너지", "ESS", "전력저장", "원전", "풍력", "태양광", "대왕고래", "셰일가스")),
    ("반도체 업황/테마 부각", ("반도체", "HBM", "SOCAMM", "유리기판", "MLCC", "전력반도체", "PCB", "FPCB")),
    ("BIO / 의료AI", ("바이오", "의료AI", "의료기기", "의료로봇", "비만치료제", "유전자치료")),
    ("이차전지", ("이차전지", "2차전지", "배터리", "전고체", "LFP", "폐배터리", "원통형")),
    ("조선/기자재 테마", ("조선", "해운")),
    ("방산", ("방산", "지뢰", "미사일")),
    ("우주 / 항공", ("우주", "항공", "UAM", "드론", "스타링크", "스페이스X", "저궤도위성")),
    ("IT / 통신", ("통신", "통신장비", "5G", "6G", "유심", "USIM", "알뜰폰")),
    ("자율주행/모빌리티 테마", ("자율주행", "자동차", "전기차", "수소차", "차량")),
    ("원자재 테마", ("원자재", "희토류", "알루미늄", "니켈", "구리", "철강", "강관")),
    ("정책 수혜 기대감", ("정부정책", "정책", "밸류업", "저PBR", "고령화", "교육")),
    ("정치 테마", ("정치", "한동훈", "김경수", "윤석열", "우원식", "김동연")),
    ("코인 / 가상자산", ("가상화폐", "가상현실", "코인", "메타버스")),
    ("IP / 엔터", ("IP", "엔터", "게임", "콘텐츠", "웹툰")),
    ("금융", ("금융", "증권", "은행", "보험")),
    ("화장품 / 중국", ("화장품", "미용", "중국")),
    ("음식료", ("음식료", "식품", "수산")),
    ("건설/인프라 테마", ("건설", "인프라", "재건")),
    ("유통 / 물류", ("유통", "물류", "쿠팡", "마켓컬리")),
)

KEYWORD_CAUSES: tuple[tuple[str, str], ...] = (
    ("액면병합", "액면병합/거래재개 이슈"),
    ("주식병합", "액면병합/거래재개 이슈"),
    ("거래재개", "액면병합/거래재개 이슈"),
    ("거래 재개", "액면병합/거래재개 이슈"),
    ("남북 경협", "남북경협/대북 테마"),
    ("남북경협", "남북경협/대북 테마"),
    ("남북 경제 협력", "남북경협/대북 테마"),
    ("경협주", "남북경협/대북 테마"),
    ("대북", "남북경협/대북 테마"),
    ("북한", "남북경협/대북 테마"),
    ("김정은", "남북경협/대북 테마"),
    ("개성공단", "남북경협/대북 테마"),
    ("금강산", "남북경협/대북 테마"),
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

    stock_profile_cause = _infer_from_stock_theme_profile(stock, news_text)
    if stock_profile_cause:
        return stock_profile_cause

    if news:
        lead_causes = _extract_causes(news[0].title + " " + news[0].description)
        if lead_causes:
            return Counter(lead_causes).most_common(1)[0][0]

    causes = _extract_causes(news_text)

    if causes:
        return Counter(causes).most_common(1)[0][0]

    stock_profile_fallback = _infer_from_stock_theme_profile(stock, news_text, allow_fallback=True)
    if stock_profile_fallback:
        return stock_profile_fallback

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


def _infer_from_stock_theme_profile(stock: StockMove, news_text: str, allow_fallback: bool = False) -> str:
    entry = _find_stock_theme_profile(stock)
    if not entry:
        return ""

    matched_theme = _match_stock_profile_to_news(entry, news_text)
    if matched_theme:
        return matched_theme

    if allow_fallback:
        preferred_theme = entry["preferred_theme"]
        if preferred_theme not in NON_OVERRIDING_MEMORY_THEMES:
            return preferred_theme

    return ""


def _find_stock_theme_profile(stock: StockMove) -> dict[str, str] | None:
    profiles = _load_stock_theme_profiles()
    code = _normalize_stock_code(stock.code)
    return profiles["by_code"].get(code) or profiles["by_name"].get(stock.name)


def _match_stock_profile_to_news(entry: dict[str, str], news_text: str) -> str:
    if not news_text:
        return ""

    compact_profile = _compact_profile_text(
        " ".join([entry["categories"], entry["subthemes"], entry["keywords"]])
    )
    compact_news = _compact_profile_text(news_text)
    scores: list[tuple[int, int, str]] = []

    for index, (theme, hints) in enumerate(STOCK_PROFILE_CAUSES):
        matched_count = sum(
            1
            for hint in hints
            if _compact_profile_text(hint) in compact_profile and _compact_profile_text(hint) in compact_news
        )
        if matched_count:
            scores.append((matched_count, -index, theme))

    if not scores:
        return ""

    return max(scores)[2]


@lru_cache(maxsize=1)
def _load_theme_memory() -> dict[str, dict[str, str]]:
    if not THEME_MEMORY_PATH.exists():
        return {}

    with THEME_MEMORY_PATH.open(encoding="utf-8", newline="") as file:
        return {row["stock_name"]: row for row in csv.DictReader(file)}


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


def _compact_profile_text(value: str) -> str:
    return re.sub(r"[\s#/()·,._-]+", "", value).lower()


def summarize_news(news: list[NewsItem]) -> str:
    if not news:
        return "관련 뉴스 검색 결과가 없습니다. 종목 공시와 장중 특징주 기사를 별도로 확인하세요."

    lead = news[0]
    summary = lead.description or lead.title
    return summary.strip() or "기사 요약문이 제공되지 않았습니다."


def prioritize_news_for_cause(news: list[NewsItem], cause: str) -> list[NewsItem]:
    hints = CAUSE_NEWS_HINTS.get(cause)
    if not hints:
        return news

    indexed = list(enumerate(news))
    return [
        item
        for _, item in sorted(
            indexed,
            key=lambda pair: (_cause_news_score(pair[1], hints), -pair[0]),
            reverse=True,
        )
    ]


def _cause_news_score(news: NewsItem, hints: tuple[str, ...]) -> int:
    text = news.title + " " + news.description
    return sum(1 for hint in hints if hint in text)
