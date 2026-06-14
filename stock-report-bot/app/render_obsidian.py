from __future__ import annotations

from pathlib import Path

from .models import DailyReport, NewsItem, StockReportItem


SUMMARY_MAX_CHARS = 90
NEWS_LINK_LIMIT = 2


def render_report(report: DailyReport) -> str:
    date_text = report.report_date.isoformat()
    limit_up_count = sum(1 for item in report.items if "상한가" in item.stock.reasons)
    gain_count = sum(1 for item in report.items if item.stock.change_percent >= 12)
    volume_count = sum(1 for item in report.items if item.stock.volume >= 10_000_000)
    trading_value_count = sum(1 for item in report.items if item.stock.trading_value >= 5_000_000_000)

    lines: list[str] = [
        "---",
        "tags:",
        "  - stock",
        "  - korea-market",
        "  - daily-report",
        f"date: {date_text}",
        "---",
        "",
        f"# {date_text} 한국 주식 장마감 리포트",
        "",
        "## 요약",
        "",
        f"선별 {len(report.items)}개 | 상한가 {limit_up_count}개 | 12% 이상 {gain_count}개 | 거래량 1,000만 주 이상 {volume_count}개 | 거래대금 50억 이상 {trading_value_count}개",
        "",
        "## 테마/섹터별 보기",
        "",
    ]

    grouped_items = _group_by_cause(report.items)
    for cause, items in grouped_items.items():
        lines.extend(_render_group_table(cause, items))

    lines.extend(["", "## 종목별 메모", ""])

    for cause, items in grouped_items.items():
        lines.extend([f"### {cause} ({len(items)}개)", ""])
        for item in items:
            lines.extend(_render_item(item))

    return "\n".join(lines).rstrip() + "\n"


def write_report(report: DailyReport, output_dir: Path) -> Path:
    month_dir = output_dir / f"{report.report_date:%Y}" / f"{report.report_date:%m}"
    month_dir.mkdir(parents=True, exist_ok=True)
    path = month_dir / f"{report.report_date.isoformat()}-korea-market-report.md"
    path.write_text(render_report(report), encoding="utf-8")
    return path


def _render_item(item: StockReportItem) -> list[str]:
    stock = item.stock
    lines = [
        f"#### {stock.name} ({stock.code}) {stock.change_percent:+.2f}%",
        f"- 거래대금: {_format_trading_value(stock.trading_value)} / 거래량: {_format_volume(stock.volume)}",
        f"- 기준: {', '.join(stock.reasons)}",
        f"- 핵심: {_shorten(item.summary)}",
    ]

    if item.news:
        for news in item.news[:NEWS_LINK_LIMIT]:
            lines.append(f"- [{_escape_link_text(news.title)}]({_preferred_link(news)})")
    else:
        lines.append("- 관련 기사 없음")

    lines.append("")
    return lines


def _render_group_table(cause: str, items: list[StockReportItem]) -> list[str]:
    lines = [
        f"### {cause} ({len(items)}개)",
        "",
        "| 종목명 | 등락률 | 거래대금 |",
        "|:---:|:---:|---:|",
    ]

    for item in items:
        stock = item.stock
        lines.append(
            "| "
            f"{stock.name} | "
            f"{stock.change_percent:+.2f}% | "
            f"{_format_trading_value(stock.trading_value)} |"
        )

    lines.append("")
    return lines


def _group_by_cause(items: tuple[StockReportItem, ...]) -> dict[str, list[StockReportItem]]:
    grouped: dict[str, list[StockReportItem]] = {}

    for item in items:
        grouped.setdefault(item.cause or "원인 확인 필요", []).append(item)

    return grouped


def _preferred_link(news: NewsItem) -> str:
    return news.originallink or news.link


def _escape_link_text(text: str) -> str:
    return text.replace("[", "(").replace("]", ")")


def _format_number(value: int) -> str:
    return f"{value:,}"


def _format_reasons(reasons: tuple[str, ...]) -> str:
    labels = []

    for reason in reasons:
        if reason == "상한가":
            labels.append("상한가")
        elif "12%" in reason:
            labels.append("12%+")
        elif "거래량" in reason:
            labels.append("거래량")
        elif "거래대금" in reason:
            labels.append("대금50억+")
        else:
            labels.append(reason)

    return ", ".join(labels)


def _format_volume(value: int) -> str:
    if value >= 100_000_000:
        return f"{value / 100_000_000:.1f}억주"
    if value >= 10_000:
        return f"{value / 10_000:.0f}만주"
    return f"{value:,}주"


def _format_trading_value(value: int) -> str:
    eok = value / 100_000_000
    if eok >= 1:
        return f"{eok:,.0f}억 원"
    return f"{value:,}원"


def _shorten(text: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"
