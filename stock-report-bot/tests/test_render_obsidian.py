from __future__ import annotations

import unittest
from datetime import date

from app.filter_stocks import dedupe_moves
from app.models import DailyReport, NewsItem, StockMove, StockReportItem
from app.render_obsidian import render_report
from app.summarize import infer_cause


class RenderObsidianTest(unittest.TestCase):
    def test_render_report_contains_stock_table_and_news_link(self) -> None:
        item = StockReportItem(
            stock=StockMove(
                code="000000",
                name="예시종목",
                market="KOSDAQ",
                close=1234,
                change_percent=18.42,
                volume=23_100_000,
                trading_value=124_000_000_000,
                reasons=("12% 이상 상승", "거래량 1,000만 주 이상", "거래대금 50억 이상"),
            ),
            news=[
                NewsItem(
                    title="예시종목 급등",
                    link="https://example.com/news",
                    originallink="",
                    description="신규 공급계약 기대감으로 상승했다.",
                )
            ],
            cause="공급계약/수주 기대감",
            summary="신규 공급계약 기대감으로 상승했다.",
        )

        rendered = render_report(DailyReport(report_date=date(2026, 5, 1), items=(item,)))

        self.assertIn("# 2026-05-01 한국 주식 장마감 리포트", rendered)
        self.assertIn("선별 1개 | 상한가 0개 | 12% 이상 1개 | 거래량 1,000만 주 이상 1개 | 거래대금 50억 이상 1개", rendered)
        self.assertIn("### 공급계약/수주 기대감 (1개)", rendered)
        self.assertIn("| 종목명 | 등락률 | 거래대금 |", rendered)
        self.assertIn("|:---:|:---:|---:|", rendered)
        self.assertIn("| 예시종목 | +18.42% | 1,240억 원 |", rendered)
        self.assertIn("#### 예시종목 (000000) +18.42%", rendered)
        self.assertIn("[예시종목 급등](https://example.com/news)", rendered)

class FilterStocksTest(unittest.TestCase):
    def test_dedupe_moves_excludes_etf_etn_and_spac_products(self) -> None:
        stock = StockMove("000000", "예시종목", "KOSDAQ", 1000, 12.3, 100, 100000, ("12% 이상 상승",))
        etn = StockMove("111111", "삼성 레버리지 WTI원유 선물 ETN", "KOSPI", 1000, 30.0, 100, 100000, ("상한가",))
        spac = StockMove("222222", "신한제18호스팩", "KOSDAQ", 1000, 17.0, 100, 100000, ("12% 이상 상승",))
        leverage = StockMove("333333", "KIWOOM 삼성전자선물단일종목레버리지", "KOSPI", 1000, 17.0, 100, 100000, ("12% 이상 상승",))

        self.assertEqual(dedupe_moves([etn, stock, spac, leverage]), [stock])


class SummarizeTest(unittest.TestCase):
    def test_robot_stock_name_wins_over_shipyard_context(self) -> None:
        stock = StockMove(
            code="108490",
            name="로보티즈",
            market="KOSDAQ",
            close=0,
            change_percent=15.18,
            volume=1,
            trading_value=10_000_000_000,
            reasons=("12% 이상 상승", "거래대금 50억 이상"),
        )
        news = [
            NewsItem(
                title="로보티즈, 조선소 용접 자동화 적용 기대",
                link="https://example.com",
                originallink="",
                description="조선소 현장에 로봇 솔루션을 적용한다는 소식이다.",
            )
        ]

        self.assertEqual(infer_cause(stock, news), "로봇 테마 부각")


if __name__ == "__main__":
    unittest.main()
