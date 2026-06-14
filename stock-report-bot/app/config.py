from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency guidance is handled at runtime
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = PROJECT_ROOT.parent / "Obsidian-Archive" / "Market-Reports"


@dataclass(frozen=True)
class Settings:
    naver_client_id: str
    naver_client_secret: str
    report_output_dir: Path
    min_gain_percent: float = 12.0
    min_volume: int = 10_000_000
    min_trading_value: int = 5_000_000_000
    limit_up_percent: float = 29.5
    news_display: int = 5


def load_settings() -> Settings:
    if load_dotenv:
        load_dotenv(PROJECT_ROOT / ".env")

    output_dir = os.getenv("REPORT_OUTPUT_DIR")

    return Settings(
        naver_client_id=os.getenv("NAVER_CLIENT_ID", ""),
        naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", ""),
        report_output_dir=Path(output_dir).expanduser() if output_dir else DEFAULT_REPORT_DIR,
    )
