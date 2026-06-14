from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class StockMove:
    code: str
    name: str
    market: str
    close: int
    change_percent: float
    volume: int
    trading_value: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class NewsItem:
    title: str
    link: str
    originallink: str
    description: str
    pub_date: datetime | None = None


@dataclass
class StockReportItem:
    stock: StockMove
    news: list[NewsItem] = field(default_factory=list)
    cause: str = ""
    summary: str = ""


@dataclass(frozen=True)
class DailyReport:
    report_date: date
    items: tuple[StockReportItem, ...]

