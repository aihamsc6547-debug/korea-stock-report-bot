from __future__ import annotations

from .models import StockMove


EXCLUDED_NAME_KEYWORDS = (
    "ETF",
    "ETN",
    "KODEX",
    "TIGER",
    "ACE ",
    "RISE ",
    "SOL ",
    "KBSTAR",
    "ARIRANG",
    "HANARO",
    "KOSEF",
    "TIMEFOLIO",
    "KIWOOM ",
    "PLUS ",
    "1Q ",
    "레버리지",
    "인버스",
    "선물",
    "단일종목",
    "스팩",
    "SPAC",
)


def dedupe_moves(moves: list[StockMove]) -> list[StockMove]:
    seen: set[str] = set()
    deduped: list[StockMove] = []

    for move in moves:
        if is_excluded_product(move.name):
            continue
        if move.code in seen:
            continue
        seen.add(move.code)
        deduped.append(move)

    return deduped


def is_excluded_product(name: str) -> bool:
    upper_name = name.upper()
    return any(keyword.upper() in upper_name for keyword in EXCLUDED_NAME_KEYWORDS)
