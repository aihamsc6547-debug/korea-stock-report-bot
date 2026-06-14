from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.build_site import build_site, discover_reports, markdown_to_html


SAMPLE_REPORT = """---
tags:
  - stock
date: 2026-06-12
---

# 2026-06-12 한국 주식 장마감 리포트

## 요약

선별 2개 | 상한가 1개 | 거래대금 50억 이상 2개

## 테마/섹터별 보기

### 반도체 업황/테마 부각 (1개)

| 종목명 | 등락률 | 거래대금 |
|:---:|:---:|---:|
| HPSP | +30.00% | 1,122억 원 |

## 종목별 메모

#### HPSP (403870) +30.00%
- 핵심: 반도체 기대감으로 급등했다.
- [관련 기사](https://example.com/news)
"""


class BuildSiteTest(unittest.TestCase):
    def test_markdown_to_html_converts_report_table_and_links(self) -> None:
        rendered = markdown_to_html(SAMPLE_REPORT)

        self.assertIn("<h1", rendered)
        self.assertIn("<table>", rendered)
        self.assertIn('<th class="center">종목명</th>', rendered)
        self.assertIn('<th class="numeric">거래대금</th>', rendered)
        self.assertIn('<td class="center">HPSP</td>', rendered)
        self.assertIn('<td class="center">+30.00%</td>', rendered)
        self.assertIn('<td class="numeric">1,122억 원</td>', rendered)
        self.assertIn('<a href="https://example.com/news"', rendered)

    def test_build_site_creates_index_and_report_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "published-reports" / "2026" / "06"
            output_dir = root / "public"
            source_dir.mkdir(parents=True)
            (source_dir / "2026-06-12-korea-market-report.md").write_text(SAMPLE_REPORT, encoding="utf-8")

            pages = build_site(root / "published-reports", output_dir)

            self.assertEqual(len(pages), 1)
            self.assertTrue((output_dir / "index.html").exists())
            self.assertTrue((output_dir / "reports" / "2026-06-12.html").exists())
            self.assertTrue((output_dir / "reports" / "latest.html").exists())
            self.assertIn("선별 2개", (output_dir / "index.html").read_text(encoding="utf-8"))

    def test_discover_reports_uses_latest_copy_for_duplicate_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "2026" / "06"
            newer = root / "copy"
            older.mkdir(parents=True)
            newer.mkdir()
            (older / "2026-06-12-korea-market-report.md").write_text(SAMPLE_REPORT, encoding="utf-8")
            (newer / "2026-06-12-korea-market-report.md").write_text(
                SAMPLE_REPORT.replace("선별 2개", "선별 3개"), encoding="utf-8"
            )

            pages = discover_reports(root)

            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0].summary, "선별 3개 | 상한가 1개 | 거래대금 50억 이상 2개")


if __name__ == "__main__":
    unittest.main()
