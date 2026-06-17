from __future__ import annotations

import unittest
from datetime import date

from app.filter_stocks import dedupe_moves
from app.models import DailyReport, NewsItem, StockMove, StockReportItem
from app.render_obsidian import render_report
from app.summarize import infer_cause, prioritize_news_for_cause


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
    def test_high_confidence_theme_memory_beats_generic_news_keyword(self) -> None:
        stock = StockMove(
            code="005930",
            name="삼성전자",
            market="KOSPI",
            close=0,
            change_percent=7.86,
            volume=1,
            trading_value=10_000_000_000,
            reasons=("거래대금 50억 이상",),
        )
        news = [
            NewsItem(
                title="삼성전자, AI 서버 투자 확대 기대",
                link="https://example.com",
                originallink="",
                description="AI 인프라 수요 증가가 반도체 업황 개선으로 이어진다는 분석이다.",
            )
        ]

        self.assertEqual(infer_cause(stock, news), "삼성 / 반디플")

    def test_theme_memory_groups_north_korea_related_stocks(self) -> None:
        news = [
            NewsItem(
                title="남북 경협주, 트럼프가 올린 김정은 사진에 급등",
                link="https://example.com",
                originallink="",
                description="좋은사람들과 코데즈컴바인 등 남북 경제 협력 관련 종목이 상승했다.",
            )
        ]
        stocks = [
            StockMove(
                code="033340",
                name="좋은사람들",
                market="KOSDAQ",
                close=0,
                change_percent=20.53,
                volume=1,
                trading_value=10_000_000_000,
                reasons=("12% 이상 상승", "거래대금 50억 이상"),
            ),
            StockMove(
                code="047770",
                name="코데즈컴바인",
                market="KOSDAQ",
                close=0,
                change_percent=29.89,
                volume=1,
                trading_value=10_000_000_000,
                reasons=("상한가", "12% 이상 상승", "거래대금 50억 이상"),
            ),
        ]

        self.assertEqual([infer_cause(stock, news) for stock in stocks], ["남북경협/대북 테마", "남북경협/대북 테마"])

    def test_prioritize_news_for_cause_moves_matching_article_first(self) -> None:
        news = [
            NewsItem(
                title="건강보험 적용 기대에 탈모주 무더기 상한가",
                link="https://example.com/health",
                originallink="",
                description="코데즈컴바인 등 상한가 종목이 함께 언급됐다.",
            ),
            NewsItem(
                title="남북 경협주, 김정은 사진에 급등",
                link="https://example.com/north",
                originallink="",
                description="좋은사람들과 코데즈컴바인 등 남북 경제 협력 관련주가 강세다.",
            ),
        ]

        ranked = prioritize_news_for_cause(news, "남북경협/대북 테마")

        self.assertEqual(ranked[0].link, "https://example.com/north")

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

    def test_mixed_theme_memory_does_not_override_current_news_keyword(self) -> None:
        stock = StockMove(
            code="023160",
            name="태광",
            market="KOSDAQ",
            close=0,
            change_percent=13.41,
            volume=1,
            trading_value=10_000_000_000,
            reasons=("12% 이상 상승", "거래대금 50억 이상"),
        )
        news = [
            NewsItem(
                title="태광, 조선 기자재 수주 기대감에 상승",
                link="https://example.com",
                originallink="",
                description="조선 업황 개선과 기자재 수요가 부각됐다.",
            )
        ]

        self.assertEqual(infer_cause(stock, news), "조선/기자재 테마")

    def test_stock_theme_profile_wins_over_generic_ai_news_keyword(self) -> None:
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
                title="AI 인프라 투자 확대로 통신장비 수요 기대",
                link="https://example.com",
                originallink="",
                description="5G와 6G 통신장비 관련 종목이 부각됐다.",
            )
        ]

        self.assertEqual(infer_cause(stock, news), "IT / 통신")

    def test_stock_theme_profile_fallback_when_news_is_unhelpful(self) -> None:
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

        self.assertEqual(infer_cause(stock, []), "IT / 통신")

    def test_stock_theme_profile_uses_current_keyword_inside_multi_theme_stock(self) -> None:
        stock = StockMove(
            code="049630",
            name="재영솔루텍",
            market="KOSDAQ",
            close=0,
            change_percent=12.0,
            volume=1,
            trading_value=10_000_000_000,
            reasons=("12% 이상 상승", "거래대금 50억 이상"),
        )
        news = [
            NewsItem(
                title="재영솔루텍, 마켓컬리 지분 가치 부각",
                link="https://example.com",
                originallink="",
                description="보유 지분과 유통 플랫폼 성장 기대가 투자심리를 자극했다.",
            )
        ]

        self.assertEqual(infer_cause(stock, news), "유통 / 물류")


if __name__ == "__main__":
    unittest.main()
