from __future__ import annotations

import argparse
import csv
import html
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT.parent / "reference" / "enex"
DEFAULT_OUTPUT = PROJECT_ROOT / "config" / "theme_memory.csv"

CDATA_START = "<![CDATA["
CDATA_END = "]]>"
STOCK_LINE_RE = re.compile(r"^●(.+)")
STOCK_NAME_RE = re.compile(r"([^()/,●]+?)\s*\([+-]?\d+(?:\.\d+)?%\)")
TITLE_DATE_RE = re.compile(r"(?P<year>20\d{2})[.\-](?P<month>\d{2})[.\-](?P<day>\d{2})")
THEME_RE = re.compile(r"^<\s*(?P<theme>[^<>]{1,70})\s*>$")


@dataclass(frozen=True)
class ThemeExample:
    note_date: str
    stock_name: str
    theme: str


def main() -> None:
    args = parse_args()
    input_paths = sorted(Path(args.input_dir).expanduser().glob("*.enex"))
    examples: list[ThemeExample] = []

    for path in input_paths:
        examples.extend(extract_examples(path))

    rows = summarize_examples(examples, args.min_count)
    write_theme_memory(rows, Path(args.output).expanduser())
    print(f"Extracted {len(examples)} examples from {len(input_paths)} ENEX file(s).")
    print(f"Wrote {len(rows)} stock-theme rows: {Path(args.output).expanduser()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract stock-theme examples from Signal Evening ENEX files.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="Directory containing .enex files.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="CSV path for extracted theme memory.")
    parser.add_argument("--min-count", type=int, default=1, help="Minimum examples required for a stock to be written.")
    return parser.parse_args()


def extract_examples(path: Path) -> list[ThemeExample]:
    examples: list[ThemeExample] = []
    note_title = ""

    with path.open("r", encoding="utf-8", errors="replace") as file:
        for line in file:
            title = _extract_xml_value(line, "title")
            if title:
                note_title = title
                continue

            if CDATA_START not in line:
                continue

            content_lines = [_extract_cdata_start(line)]
            if CDATA_END not in line:
                for content_line in file:
                    content_lines.append(content_line)
                    if CDATA_END in content_line:
                        break

            content = _strip_cdata_end("".join(content_lines))
            examples.extend(_extract_examples_from_note(note_title, content))

    return examples


def summarize_examples(examples: list[ThemeExample], min_count: int) -> list[dict[str, str]]:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    last_seen: dict[tuple[str, str], str] = {}

    for example in examples:
        grouped[example.stock_name][example.theme] += 1
        key = (example.stock_name, example.theme)
        if example.note_date > last_seen.get(key, ""):
            last_seen[key] = example.note_date

    rows: list[dict[str, str]] = []
    for stock_name, theme_counts in grouped.items():
        total_count = sum(theme_counts.values())
        if total_count < min_count:
            continue

        top_theme, top_count = theme_counts.most_common(1)[0]
        rows.append(
            {
                "stock_name": stock_name,
                "preferred_theme": top_theme,
                "example_count": str(total_count),
                "preferred_count": str(top_count),
                "confidence": f"{top_count / total_count:.3f}",
                "last_seen": max(last_seen[(stock_name, theme)] for theme in theme_counts),
                "theme_counts": "; ".join(f"{theme}:{count}" for theme, count in theme_counts.most_common()),
            }
        )

    return sorted(rows, key=lambda row: (-int(row["preferred_count"]), row["stock_name"]))


def write_theme_memory(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "stock_name",
        "preferred_theme",
        "example_count",
        "preferred_count",
        "confidence",
        "last_seen",
        "theme_counts",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _extract_examples_from_note(note_title: str, content: str) -> list[ThemeExample]:
    note_date = _extract_note_date(note_title)
    current_theme = ""
    examples: list[ThemeExample] = []

    for line in _enml_to_text_lines(content):
        theme = _extract_theme(line)
        if theme:
            current_theme = theme
            continue

        if not current_theme or not line.startswith("●"):
            continue

        for stock_name in _extract_stock_names(line):
            examples.append(ThemeExample(note_date=note_date, stock_name=stock_name, theme=current_theme))

    return examples


def _enml_to_text_lines(content: str) -> list[str]:
    text = re.sub(r'<div[^>]*display:none[^>]*>.*?</div>', "\n", content)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</(?:div|p|li|h[1-6])>", "\n", text)
    text = re.sub(r"<en-media\b[^>]*/>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    lines = []
    for line in text.splitlines():
        compact = " ".join(line.split())
        if compact:
            lines.append(compact)
    return lines


def _extract_stock_names(line: str) -> list[str]:
    names = []
    for raw_name in STOCK_NAME_RE.findall(line):
        name = _clean_stock_name(raw_name)
        if name:
            names.append(name)
    return names


def _extract_theme(line: str) -> str:
    match = THEME_RE.match(line)
    if not match:
        return ""

    theme = " ".join(match.group("theme").split())
    if any(skip in theme for skip in ("시장 주도", "to the DEEP")):
        return ""
    return _normalize_theme(theme)


def _normalize_theme(theme: str) -> str:
    compact = re.sub(r"\s+", "", theme)

    if "반디플" in compact or "반/디플" in compact or "반도체" in compact:
        return "삼성 / 반디플"
    if "로봇" in compact:
        return "로봇"
    if "전력" in compact or "전선" in compact or "에너지" in compact or "원전" in compact:
        return "전력 / 에너지"
    if "BIO" in compact or "바이오" in compact or "의료" in compact or "미용" in compact:
        return "BIO / 의료AI"
    if "이차전지" in compact or "2차전지" in compact or "배터리" in compact or "ESS" in compact:
        return "이차전지"
    if "조선" in compact:
        return "조선"
    if "방산" in compact:
        return "방산"
    if "우주" in compact or "항공" in compact:
        return "우주 / 항공"
    if "통신" in compact or "보안" in compact or compact == "IT":
        return "IT / 통신"
    if "코인" in compact or "가상자산" in compact:
        return "코인 / 가상자산"
    if "실적" in compact or "공시" in compact:
        return "실적 / 공시"
    if "정부" in compact or "정책" in compact:
        return "정부 정책"

    return theme


def _clean_stock_name(value: str) -> str:
    name = value.strip(" /,\t")
    name = re.sub(r"^(?:및|과|와)\s+", "", name)
    return name.strip()


def _extract_note_date(title: str) -> str:
    match = TITLE_DATE_RE.search(title)
    if not match:
        return ""
    return f"{match.group('year')}-{match.group('month')}-{match.group('day')}"


def _extract_xml_value(line: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", line)
    return html.unescape(match.group(1).strip()) if match else ""


def _extract_cdata_start(line: str) -> str:
    return line.split(CDATA_START, 1)[1]


def _strip_cdata_end(text: str) -> str:
    return text.split(CDATA_END, 1)[0]


if __name__ == "__main__":
    main()
