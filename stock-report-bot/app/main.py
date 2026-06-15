from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

from .config import load_settings
from .fetch_market import fetch_market_moves_with_status
from .fetch_naver_market import fetch_latest_naver_market_moves
from .fetch_news import fetch_stock_news
from .filter_stocks import dedupe_moves
from .models import DailyReport, StockReportItem
from .render_obsidian import write_report
from .summarize import infer_cause, prioritize_news_for_cause, summarize_news


def main() -> None:
    args = parse_args()
    requested_date = parse_date(args.date)
    settings = load_settings()

    report_date, moves = find_available_market_date(requested_date, settings)
    if report_date != requested_date:
        print(f"No market data for {requested_date.isoformat()}; using {report_date.isoformat()} instead.")

    items: list[StockReportItem] = []

    for move in moves:
        news = fetch_stock_news(move, settings)
        cause = infer_cause(move, news)
        news = prioritize_news_for_cause(news, cause)
        items.append(
            StockReportItem(
                stock=move,
                news=news,
                cause=cause,
                summary=summarize_news(news),
            )
        )

    output_path = write_report(DailyReport(report_date=report_date, items=tuple(items)), settings.report_output_dir)
    print(f"Created report: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Korean market close report for Obsidian.")
    parser.add_argument("--date", help="Report date in YYYYMMDD or YYYY-MM-DD format. Defaults to today.")
    return parser.parse_args()


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    raise SystemExit("--date는 YYYYMMDD 또는 YYYY-MM-DD 형식이어야 합니다.")


def find_available_market_date(target_date: date, settings, lookback_days: int = 10) -> tuple[date, list]:
    current = target_date

    for _ in range(lookback_days + 1):
        result = fetch_market_moves_with_status(current, settings)
        if result.has_market_data:
            return current, dedupe_moves(result.moves)
        current -= timedelta(days=1)

    latest_date, result = fetch_latest_naver_market_moves(settings)
    if latest_date and result.has_market_data:
        print("pykrx/KRX data unavailable; using Naver mobile market data fallback.")
        return latest_date, dedupe_moves(result.moves)

    raise SystemExit(f"{target_date.isoformat()} 기준 {lookback_days}일 이내 거래일 데이터를 찾지 못했습니다.")


if __name__ == "__main__":
    main()
