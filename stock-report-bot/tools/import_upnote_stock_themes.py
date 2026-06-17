from __future__ import annotations

import argparse
import csv
import io
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "config" / "stock_theme_keywords.csv"
CSV_HEADER = '"종목명","종목코드"'

THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("남북경협/대북 테마", ("남북경협", "개성공단", "대북", "북한", "금강산")),
    ("로봇 테마 부각", ("휴머노이드", "로봇", "액추에이터", "감속기", "스마트팩토리", "의료로봇", "보스턴다이내믹스")),
    ("전력기기/전력망 테마", ("전력기기", "전력망", "전선", "해저케이블", "스마트그리드", "전력")),
    ("전력 / 에너지", ("에너지", "ESS", "전력저장", "원전", "풍력", "태양광", "대왕고래", "셰일가스")),
    ("반도체 업황/테마 부각", ("반도체", "HBM", "SOCAMM", "유리기판", "MLCC", "전력반도체", "PCB", "FPCB")),
    ("BIO / 의료AI", ("바이오", "의료AI", "의료기기", "의료로봇", "비만치료제", "유전자치료")),
    ("이차전지", ("이차전지", "2차전지", "배터리", "전고체", "LFP", "폐배터리", "원통형")),
    ("조선/기자재 테마", ("조선", "해운")),
    ("방산", ("방산", "지뢰", "미사일")),
    ("우주 / 항공", ("우주", "항공", "UAM", "드론", "스타링크", "스페이스X", "저궤도위성")),
    ("IT / 통신", ("통신", "5G", "6G", "유심", "USIM", "알뜰폰")),
    ("자율주행/모빌리티 테마", ("자율주행", "자동차", "전기차", "수소차", "차량")),
    ("원자재 테마", ("원자재", "희토류", "알루미늄", "니켈", "구리", "철강", "강관")),
    ("정책 수혜 기대감", ("정부정책", "정책", "밸류업", "저PBR", "고령화", "교육")),
    ("정치 테마", ("정치", "한동훈", "김경수", "윤석열", "우원식", "김동연")),
    ("코인 / 가상자산", ("가상화폐", "가상현실", "코인", "메타버스")),
    ("IP / 엔터", ("IP", "엔터", "게임", "콘텐츠", "웹툰")),
    ("금융", ("금융", "증권", "은행", "보험")),
    ("화장품 / 중국", ("화장품", "미용", "중국")),
    ("음식료", ("음식료", "식품", "수산")),
    ("건설/인프라 테마", ("건설", "인프라", "재건")),
    ("유통 / 물류", ("유통", "물류", "쿠팡", "마켓컬리")),
)


def main() -> None:
    args = parse_args()
    rows = parse_upnote_export(Path(args.input).expanduser())
    write_stock_theme_keywords(rows, Path(args.output).expanduser())
    print(f"Wrote {len(rows)} stock theme rows: {Path(args.output).expanduser()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import UpNote stock theme CSV text into project config.")
    parser.add_argument("--input", required=True, help="Pasted UpNote text file containing CSV rows.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="CSV path for normalized stock theme keywords.")
    return parser.parse_args()


def parse_upnote_export(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    csv_start = text.find(CSV_HEADER)
    if csv_start < 0:
        raise ValueError(f"Could not find CSV header in {path}")

    rows: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    reader = csv.DictReader(io.StringIO(text[csv_start:]))
    for row in reader:
        stock_name = _clean_cell(row.get("종목명", ""))
        stock_code = _clean_stock_code(row.get("종목코드", ""))
        if not stock_name or not stock_code or stock_code in seen_codes:
            continue

        categories = _clean_theme_list(row.get("대분류", ""))
        subthemes = _clean_theme_list(row.get("중분류", ""))
        keywords = _clean_theme_list(row.get("키워드", ""))
        rows.append(
            {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "preferred_theme": infer_preferred_theme(categories, subthemes, keywords),
                "categories": categories,
                "subthemes": subthemes,
                "keywords": keywords,
            }
        )
        seen_codes.add(stock_code)

    return sorted(rows, key=lambda item: (item["stock_name"], item["stock_code"]))


def infer_preferred_theme(categories: str, subthemes: str, keywords: str) -> str:
    compact_categories = _compact(categories)
    compact_details = _compact(" | ".join((subthemes, keywords)))
    scored_themes: list[tuple[int, str]] = []

    for theme, hints in THEME_RULES:
        score = 0
        for hint in hints:
            compact_hint = _compact(hint)
            if compact_hint in compact_details:
                score += 3
            if compact_hint in compact_categories:
                score += 1
        if score:
            scored_themes.append((score, theme))

    if scored_themes:
        business_themes = [item for item in scored_themes if item[1] != "정치 테마"]
        if business_themes:
            return max(business_themes, key=lambda item: item[0])[1]
        return max(scored_themes, key=lambda item: item[0])[1]
    return "개별주"


def write_stock_theme_keywords(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["stock_name", "stock_code", "preferred_theme", "categories", "subthemes", "keywords"]
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _clean_cell(value: str | None) -> str:
    return " ".join((value or "").split())


def _clean_stock_code(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits.zfill(6) if digits else ""


def _clean_theme_list(value: str | None) -> str:
    parts = []
    for raw_part in (value or "").split("|"):
        part = raw_part.strip().lstrip("#").strip()
        if part and part not in parts:
            parts.append(part)
    return " | ".join(parts)


def _compact(value: str) -> str:
    return re.sub(r"[\s#/()·,._-]+", "", value).lower()


if __name__ == "__main__":
    main()
