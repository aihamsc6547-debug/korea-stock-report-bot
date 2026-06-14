from __future__ import annotations

import json
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Settings
from .fetch_market import MarketFetchResult
from .models import StockMove


NAVER_MARKET_ENDPOINT = "https://m.stock.naver.com/api/stocks/marketValue/{market}"
PAGE_SIZE = 100


def fetch_latest_naver_market_moves(settings: Settings) -> tuple[date | None, MarketFetchResult]:
    rows: list[StockMove] = []
    traded_dates: list[date] = []

    for market in ("KOSPI", "KOSDAQ"):
        page = 1
        total_count = None

        while total_count is None or (page - 1) * PAGE_SIZE < total_count:
            payload = _fetch_page(market, page)
            stocks = payload.get("stocks", [])
            total_count = int(payload.get("totalCount", len(stocks)))

            if not stocks:
                break

            for raw in stocks:
                move = _parse_stock(raw, settings)
                if move:
                    rows.append(move)

                traded_at = _parse_traded_date(raw.get("localTradedAt", ""))
                if traded_at:
                    traded_dates.append(traded_at)

            page += 1

    actual_date = max(traded_dates) if traded_dates else None
    return actual_date, MarketFetchResult(
        moves=sorted(rows, key=lambda item: (item.change_percent, item.trading_value), reverse=True),
        has_market_data=bool(traded_dates),
    )


def _fetch_page(market: str, page: int) -> dict:
    params = urlencode({"page": page, "pageSize": PAGE_SIZE})
    request = Request(
        f"{NAVER_MARKET_ENDPOINT.format(market=market)}?{params}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_stock(raw: dict, settings: Settings) -> StockMove | None:
    change_percent = _to_float(raw.get("fluctuationsRatio"))
    volume = _to_int(raw.get("accumulatedTradingVolumeRaw") or raw.get("accumulatedTradingVolume"))
    trading_value = _to_int(raw.get("accumulatedTradingValueRaw"))
    reasons = _match_reasons(change_percent, volume, trading_value, settings)

    if not reasons:
        return None

    exchange = raw.get("stockExchangeType", {})
    market = exchange.get("nameEng") or ("KOSDAQ" if raw.get("sosok") == "1" else "KOSPI")

    return StockMove(
        code=str(raw.get("itemCode", "")),
        name=str(raw.get("stockName", "")),
        market=str(market),
        close=_to_int(raw.get("closePriceRaw") or raw.get("closePrice")),
        change_percent=change_percent,
        volume=volume,
        trading_value=trading_value,
        reasons=tuple(reasons),
    )


def _match_reasons(change_percent: float, volume: int, trading_value: int, settings: Settings) -> list[str]:
    if trading_value < settings.min_trading_value:
        return []

    reasons: list[str] = []

    if change_percent >= settings.limit_up_percent:
        reasons.append("상한가")
    if change_percent >= settings.min_gain_percent:
        reasons.append(f"{settings.min_gain_percent:g}% 이상 상승")
    if volume >= settings.min_volume:
        reasons.append("거래량 1,000만 주 이상")

    if reasons:
        reasons.append("거래대금 50억 이상")

    return reasons


def _parse_traded_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _to_int(value) -> int:
    if value in (None, "", "N/A"):
        return 0
    return int(str(value).replace(",", ""))


def _to_float(value) -> float:
    if value in (None, "", "N/A"):
        return 0.0
    return float(str(value).replace(",", ""))
