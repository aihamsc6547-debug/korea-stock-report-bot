from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
OBSIDIAN_REPORT_DIR = REPO_ROOT / "Obsidian-Archive" / "Market-Reports"
PUBLISHED_REPORT_DIR = REPO_ROOT / "published-reports"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "public"
REPORT_NAME_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})-korea-market-report\.md$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class ReportPage:
    report_date: datetime
    title: str
    summary: str
    source_path: Path
    output_name: str


def main() -> None:
    args = parse_args()
    source_dir = resolve_source_dir(Path(args.source_dir).expanduser() if args.source_dir else None)
    output_dir = Path(args.output_dir).expanduser()
    pages = build_site(source_dir, output_dir, args.site_title)
    print(f"Built web site: {output_dir} ({len(pages)} report(s), source: {source_dir})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static web site from generated market reports.")
    parser.add_argument("--source-dir", help="Directory containing generated report Markdown files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to write static HTML files.")
    parser.add_argument("--site-title", default="한국 주식 장마감 리포트", help="Title shown on the web site.")
    return parser.parse_args()


def resolve_source_dir(source_dir: Path | None = None) -> Path:
    if source_dir:
        return source_dir

    if _find_report_paths(PUBLISHED_REPORT_DIR):
        return PUBLISHED_REPORT_DIR

    return OBSIDIAN_REPORT_DIR


def build_site(source_dir: Path, output_dir: Path, site_title: str = "한국 주식 장마감 리포트") -> list[ReportPage]:
    pages = discover_reports(source_dir)
    reports_dir = output_dir / "reports"
    assets_dir = output_dir / "assets"

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    (assets_dir / "site.css").write_text(WEB_CSS, encoding="utf-8")
    (output_dir / "index.html").write_text(render_index(pages, site_title), encoding="utf-8")

    for page in pages:
        report_markdown = page.source_path.read_text(encoding="utf-8")
        (reports_dir / page.output_name).write_text(render_report_page(page, report_markdown, site_title), encoding="utf-8")

    if pages:
        latest_href = f"{pages[0].output_name}"
        (reports_dir / "latest.html").write_text(render_redirect(latest_href, site_title), encoding="utf-8")

    return pages


def discover_reports(source_dir: Path) -> list[ReportPage]:
    reports: dict[str, ReportPage] = {}

    for path in _find_report_paths(source_dir):
        match = REPORT_NAME_RE.search(path.name)
        if not match:
            continue

        report_date = datetime.strptime(match.group("date"), "%Y-%m-%d")
        text = path.read_text(encoding="utf-8")
        reports[match.group("date")] = ReportPage(
            report_date=report_date,
            title=_extract_title(text, report_date),
            summary=_extract_summary(text),
            source_path=path,
            output_name=f"{match.group('date')}.html",
        )

    return sorted(reports.values(), key=lambda page: page.report_date, reverse=True)


def render_index(pages: list[ReportPage], site_title: str) -> str:
    latest = pages[0] if pages else None
    rows = "\n".join(
        f"""
        <tr>
          <td><a href="reports/{page.output_name}">{page.report_date:%Y-%m-%d}</a></td>
          <td>{html.escape(page.summary or page.title)}</td>
        </tr>"""
        for page in pages
    )

    if not rows:
        rows = """
        <tr>
          <td colspan="2">아직 발행된 리포트가 없습니다.</td>
        </tr>"""

    latest_link = (
        f'<a class="button" href="reports/{latest.output_name}">최신 리포트 보기</a>' if latest else ""
    )
    latest_text = latest.report_date.strftime("%Y-%m-%d") if latest else "대기 중"

    body = f"""
    <main class="shell">
      <section class="masthead">
        <div>
          <p class="eyebrow">Daily Market Close</p>
          <h1>{html.escape(site_title)}</h1>
          <p class="lede">최근 발행일: {latest_text}</p>
        </div>
        {latest_link}
      </section>

      <section class="section">
        <div class="section-heading">
          <h2>리포트 목록</h2>
          <span>{len(pages)}개</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>날짜</th>
                <th>요약</th>
              </tr>
            </thead>
            <tbody>{rows}
            </tbody>
          </table>
        </div>
      </section>
    </main>
    """
    return render_layout(site_title, body, "")


def render_report_page(page: ReportPage, markdown_text: str, site_title: str) -> str:
    report_html = markdown_to_html(markdown_text)
    body = f"""
    <main class="shell">
      <nav class="top-nav">
        <a href="../index.html">리포트 목록</a>
        <a href="latest.html">최신</a>
      </nav>
      <article class="report-body">
        {report_html}
      </article>
    </main>
    """
    return render_layout(f"{page.report_date:%Y-%m-%d} | {site_title}", body, "../")


def render_redirect(href: str, site_title: str) -> str:
    escaped_href = html.escape(href, quote=True)
    body = f"""
    <main class="shell">
      <p>최신 리포트로 이동합니다. <a href="{escaped_href}">바로 열기</a></p>
    </main>
    """
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url={escaped_href}">
  <title>{html.escape(site_title)}</title>
  <link rel="stylesheet" href="../assets/site.css">
</head>
<body>{body}</body>
</html>
"""


def render_layout(title: str, body: str, asset_prefix: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{asset_prefix}assets/site.css">
</head>
<body>
  {body}
</body>
</html>
"""


def markdown_to_html(markdown_text: str) -> str:
    lines = _strip_frontmatter(markdown_text).splitlines()
    html_lines: list[str] = []
    slug_counts: dict[str, int] = {}
    index = 0
    in_list = False

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            index += 1
            continue

        if _is_table_line(line):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            table_lines: list[str] = []
            while index < len(lines) and _is_table_line(lines[index]):
                table_lines.append(lines[index])
                index += 1
            html_lines.append(_render_table(table_lines))
            continue

        heading = _parse_heading(stripped)
        if heading:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            level, text = heading
            html_lines.append(f'<h{level} id="{_slugify(text, slug_counts)}">{_convert_inline(text)}</h{level}>')
            index += 1
            continue

        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_convert_inline(stripped[2:])}</li>")
            index += 1
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{_convert_inline(stripped)}</p>")
        index += 1

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _find_report_paths(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(source_dir.rglob("*-korea-market-report.md"))


def _extract_title(text: str, report_date: datetime) -> str:
    for line in _strip_frontmatter(text).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return f"{report_date:%Y-%m-%d} 한국 주식 장마감 리포트"


def _extract_summary(text: str) -> str:
    lines = _strip_frontmatter(text).splitlines()
    in_summary = False

    for line in lines:
        stripped = line.strip()
        if stripped == "## 요약":
            in_summary = True
            continue
        if in_summary and stripped.startswith("## "):
            break
        if in_summary and stripped:
            return stripped

    return ""


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :])

    return text


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _render_table(table_lines: list[str]) -> str:
    rows = [_parse_table_row(line) for line in table_lines]
    if not rows:
        return ""

    header = rows[0]
    body_rows = rows[1:]
    aligns: list[str] = []

    if body_rows and _is_alignment_row(body_rows[0]):
        aligns = [_alignment_class(cell) for cell in body_rows[0]]
        body_rows = body_rows[1:]

    header_html = "".join(f"<th>{_convert_inline(cell)}</th>" for cell in header)
    body_html = "\n".join(
        "<tr>"
        + "".join(
            f'<td{_class_attr(aligns[index] if index < len(aligns) else "")}>{_convert_inline(cell)}</td>'
            for index, cell in enumerate(row)
        )
        + "</tr>"
        for row in body_rows
    )

    return f"""<div class="table-wrap">
<table>
  <thead><tr>{header_html}</tr></thead>
  <tbody>
{body_html}
  </tbody>
</table>
</div>"""


def _parse_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_alignment_row(row: list[str]) -> bool:
    return bool(row) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)


def _alignment_class(cell: str) -> str:
    if cell.endswith(":") and not cell.startswith(":"):
        return "numeric"
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    return ""


def _class_attr(value: str) -> str:
    return f' class="{value}"' if value else ""


def _convert_inline(text: str) -> str:
    parts: list[str] = []
    cursor = 0

    for match in LINK_RE.finditer(text):
        parts.append(html.escape(text[cursor : match.start()]))
        label = html.escape(match.group(1))
        url = html.escape(match.group(2), quote=True)
        parts.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>')
        cursor = match.end()

    parts.append(html.escape(text[cursor:]))
    return "".join(parts)


def _slugify(text: str, counts: dict[str, int]) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in text)
    slug = re.sub(r"-+", "-", slug).strip("-") or "section"
    count = counts.get(slug, 0)
    counts[slug] = count + 1
    return slug if count == 0 else f"{slug}-{count + 1}"


WEB_CSS = """
:root {
  color-scheme: light;
  --bg: #f5f7f7;
  --paper: #ffffff;
  --text: #182026;
  --muted: #64717a;
  --line: #dbe2e4;
  --accent: #006d77;
  --accent-strong: #0a4b52;
  --warm: #b42318;
  --soft: #edf6f7;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
  line-height: 1.65;
}

a {
  color: var(--accent-strong);
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}

.shell {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 64px;
}

.masthead {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 0;
  border-bottom: 1px solid var(--line);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
h3,
h4 {
  line-height: 1.25;
  letter-spacing: 0;
}

h1 {
  margin: 0;
  font-size: clamp(28px, 5vw, 44px);
}

h2 {
  margin: 38px 0 14px;
  font-size: 24px;
}

h3 {
  margin: 30px 0 10px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  font-size: 20px;
}

h4 {
  margin: 22px 0 8px;
  font-size: 17px;
}

.lede {
  margin: 8px 0 0;
  color: var(--muted);
}

.button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: #ffffff;
  font-weight: 700;
  text-decoration: none;
  white-space: nowrap;
}

.section {
  padding-top: 20px;
}

.section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.section-heading span {
  color: var(--muted);
  font-size: 14px;
}

.top-nav {
  display: flex;
  gap: 14px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}

.report-body {
  padding: 20px 0 0;
}

.report-body > h1:first-child {
  margin-top: 0;
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  margin: 10px 0 22px;
  border: 1px solid var(--line);
  background: var(--paper);
}

table {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  vertical-align: top;
}

th {
  background: var(--soft);
  color: var(--accent-strong);
  font-size: 13px;
  font-weight: 800;
}

td.numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

td.center {
  text-align: center;
}

tr:last-child td {
  border-bottom: 0;
}

p,
ul {
  max-width: 900px;
}

ul {
  padding-left: 20px;
}

li + li {
  margin-top: 3px;
}

.report-body > p:first-of-type {
  display: inline-block;
  margin: 0 0 12px;
  padding: 6px 10px;
  border-left: 4px solid var(--warm);
  background: #fff7f5;
  font-weight: 700;
}

@media (max-width: 720px) {
  .shell {
    width: min(100% - 22px, 1120px);
    padding-top: 14px;
  }

  .masthead {
    align-items: start;
    flex-direction: column;
    padding: 20px 0;
  }

  h1 {
    font-size: 28px;
  }

  h2 {
    font-size: 21px;
  }

  th,
  td {
    padding: 9px 10px;
  }
}
"""


if __name__ == "__main__":
    main()
