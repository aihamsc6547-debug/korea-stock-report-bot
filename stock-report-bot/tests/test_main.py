from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.main import generate_report
from app.render_obsidian import report_file_path


class GenerateReportTest(unittest.TestCase):
    def test_skip_existing_requested_date_avoids_market_lookup(self) -> None:
        report_date = date(2026, 6, 18)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            existing_path = report_file_path(report_date, output_dir)
            existing_path.parent.mkdir(parents=True)
            existing_path.write_text("existing report", encoding="utf-8")
            settings = SimpleNamespace(report_output_dir=output_dir)

            with patch("app.main.find_available_market_date") as find_market_date:
                result = generate_report(
                    requested_date=report_date,
                    settings=settings,
                    skip_existing=True,
                )

            self.assertEqual(result, existing_path)
            find_market_date.assert_not_called()

    def test_skip_existing_uses_resolved_market_date(self) -> None:
        report_date = date(2026, 6, 18)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            existing_path = report_file_path(report_date, output_dir)
            existing_path.parent.mkdir(parents=True)
            existing_path.write_text("existing report", encoding="utf-8")
            settings = SimpleNamespace(report_output_dir=output_dir)

            with (
                patch("app.main.find_available_market_date", return_value=(report_date, [])),
                patch("app.main.fetch_feature_news") as fetch_feature_news,
            ):
                result = generate_report(
                    requested_date=date(2026, 6, 19),
                    settings=settings,
                    skip_existing=True,
                )

            self.assertEqual(result, existing_path)
            fetch_feature_news.assert_not_called()


if __name__ == "__main__":
    unittest.main()
