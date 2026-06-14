from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import Settings
from .models import StockMove


@dataclass(frozen=True)
class MarketFetchResult:
    moves: list[StockMove]
    has_market_data: bool


def fetch_market_moves(target_date: date, settings: Settings) -> list[StockMove]:
    return fetch_market_moves_with_status(target_date, settings).moves


def fetch_market_moves_with_status(target_date: date, settings: Settings) -> MarketFetchResult:
    try:
        from pykrx import stock
    except ImportError as exc:
        raise RuntimeError(
            "pykrx가 설치되어 있지 않습니다. `pip install -r requirements.txt`를 먼저 실행하세요."
        ) from exc

    yyyymmdd = target_date.strftime("%Y%m%d")
    rows: list[StockMove] = []
    has_market_data = False

    for market in ("KOSPI", "KOSDAQ"):
        try:
            frame = stock.get_market_ohlcv_by_ticker(yyyymmdd, market=market)
        except KeyError:
            # pykrx may raise KeyError for holidays or dates with no KRX table.
            continue

        if frame.empty:
            continue

        frame = _normalize_ohlcv_frame(frame)
        if not _has_price_data(frame):
            continue

        has_market_data = True
        tickers = stock.get_market_ticker_list(yyyymmdd, market=market)
        names = {ticker: stock.get_market_ticker_name(ticker) for ticker in tickers}

        for code, row in frame.iterrows():
            change_percent = float(row.get("change_percent", 0.0))
            volume = int(row.get("volume", 0))
            trading_value = int(row.get("trading_value", 0))
            reasons = _match_reasons(change_percent, volume, trading_value, settings)

            if not reasons:
                continue

            rows.append(
                StockMove(
                    code=str(code),
                    name=names.get(str(code), str(code)),
                    market=market,
                    close=int(row.get("close", 0)),
                    change_percent=change_percent,
                    volume=volume,
                    trading_value=trading_value,
                    reasons=tuple(reasons),
                )
            )

    return MarketFetchResult(
        moves=sorted(rows, key=lambda item: (item.change_percent, item.trading_value), reverse=True),
        has_market_data=has_market_data,
    )


def _normalize_ohlcv_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "종가": "close",
        "등락률": "change_percent",
        "거래량": "volume",
        "거래대금": "trading_value",
    }
    normalized = frame.rename(columns=rename_map).copy()

    for column in ("close", "change_percent", "volume", "trading_value"):
        if column not in normalized.columns:
            normalized[column] = 0

    return normalized


def _has_price_data(frame: pd.DataFrame) -> bool:
    return bool((frame["close"] > 0).any())


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
