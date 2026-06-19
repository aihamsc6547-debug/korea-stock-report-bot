from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.assign_news import assign_feature_news_to_stocks, merge_news_lists
from app.fetch_news import _is_report_date, filter_feature_news_items
from app.models import NewsItem, StockMove


KST = ZoneInfo("Asia/Seoul")


class FeatureNewsFilterTest(unittest.TestCase):
    def test_filters_feature_news_after_market_open(self) -> None:
        items = [
            NewsItem(
                title="(특징주) 장전 기대감 기사",
                link="https://example.com/before",
                originallink="",
                description="장 시작 전 기사다.",
                pub_date=datetime(2026, 6, 17, 8, 59, tzinfo=KST),
            ),
            NewsItem(
                title="(특징주) 전선주 강세",
                link="https://example.com/after",
                originallink="",
                description="장 시작 후 기사다.",
                pub_date=datetime(2026, 6, 17, 9, 1, tzinfo=KST),
            ),
            NewsItem(
                title="전선주 강세",
                link="https://example.com/no-feature",
                originallink="",
                description="특징주 제목이 아니다.",
                pub_date=datetime(2026, 6, 17, 9, 2, tzinfo=KST),
            ),
        ]

        filtered = filter_feature_news_items(items, date(2026, 6, 17))

        self.assertEqual([item.link for item in filtered], ["https://example.com/after"])

    def test_stock_news_date_filter_rejects_old_articles(self) -> None:
        report_date = date(2026, 6, 19)

        self.assertTrue(_is_report_date(datetime(2026, 6, 19, 10, 0, tzinfo=KST), report_date))
        self.assertFalse(_is_report_date(datetime(2025, 12, 22, 14, 0, tzinfo=KST), report_date))
        self.assertFalse(_is_report_date(None, report_date))


class NewsAssignmentTest(unittest.TestCase):
    def test_assigns_only_direct_stock_feature_article(self) -> None:
        stocks = [
            StockMove(
                code="006340",
                name="대원전선",
                market="KOSPI",
                close=0,
                change_percent=10.58,
                volume=1,
                trading_value=10_000_000_000,
                reasons=("거래대금 50억 이상",),
            ),
            StockMove(
                code="153460",
                name="네이블",
                market="KOSDAQ",
                close=0,
                change_percent=12.0,
                volume=1,
                trading_value=10_000_000_000,
                reasons=("12% 이상 상승", "거래대금 50억 이상"),
            ),
        ]
        news = [
            NewsItem(
                title="(특징주) 대원전선, 해저케이블 기대에 강세",
                link="https://example.com/direct",
                originallink="",
                description="전선과 구리 관련 종목에 매수세가 유입됐다.",
                pub_date=datetime(2026, 6, 17, 10, 0, tzinfo=KST),
            ),
            NewsItem(
                title="(특징주) 전선주, 해저케이블 기대에 강세",
                link="https://example.com/theme",
                originallink="",
                description="전선 관련 종목에 매수세가 유입됐다.",
                pub_date=datetime(2026, 6, 17, 10, 5, tzinfo=KST),
            )
        ]

        assigned = assign_feature_news_to_stocks(stocks, news)

        self.assertEqual([item.link for item in assigned["006340"]], ["https://example.com/direct"])
        self.assertNotIn("153460", assigned)

    def test_merge_news_lists_dedupes_by_original_link(self) -> None:
        first = NewsItem(
            title="(특징주) 네이블 강세",
            link="https://naver.example.com/a",
            originallink="https://example.com/a",
            description="통신장비 수요가 부각됐다.",
        )
        duplicate = NewsItem(
            title="네이블 강세",
            link="https://naver.example.com/other",
            originallink="https://example.com/a",
            description="같은 원문 기사다.",
        )

        merged = merge_news_lists([first], [duplicate])

        self.assertEqual(merged, [first])

    def test_does_not_assign_theme_article_by_profile_keyword(self) -> None:
        stock = StockMove(
            code="153460",
            name="네이블",
            market="KOSDAQ",
            close=0,
            change_percent=12.0,
            volume=1,
            trading_value=10_000_000_000,
            reasons=("12% 이상 상승", "거래대금 50억 이상"),
        )
        news = [
            NewsItem(
                title="(특징주) 통신장비주, 6G 투자 기대에 강세",
                link="https://example.com/telecom",
                originallink="",
                description="통신 인프라 투자가 확대될 것이란 전망이다.",
                pub_date=datetime(2026, 6, 17, 10, 0, tzinfo=KST),
            )
        ]

        assigned = assign_feature_news_to_stocks([stock], news)

        self.assertNotIn("153460", assigned)


if __name__ == "__main__":
    unittest.main()
