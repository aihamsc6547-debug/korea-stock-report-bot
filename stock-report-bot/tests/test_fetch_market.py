from __future__ import annotations

import sys
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from requests import ConnectionError

from app.fetch_market import fetch_market_moves_with_status


class FetchMarketTest(unittest.TestCase):
    def test_request_error_returns_no_market_data_for_fallback(self) -> None:
        stock_api = SimpleNamespace(
            get_market_ohlcv_by_ticker=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ConnectionError("temporary KRX outage")
            )
        )
        pykrx_module = SimpleNamespace(stock=stock_api)
        settings = SimpleNamespace()

        with patch.dict(sys.modules, {"pykrx": pykrx_module}):
            result = fetch_market_moves_with_status(date(2026, 6, 18), settings)

        self.assertFalse(result.has_market_data)
        self.assertEqual(result.moves, [])


if __name__ == "__main__":
    unittest.main()
