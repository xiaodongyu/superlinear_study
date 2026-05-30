#!/usr/bin/env python3
"""Build a standalone HTML dashboard for CVPR 2024 paper metadata."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from collections import Counter
from pathlib import Path

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into", "is", "it", "its",
    "of", "on", "or", "the", "to", "towards", "via", "with", "without", "using", "based", "toward",
    "learning", "image", "images", "video", "vision", "cvpr", "2024", "via", "new", "toward", "towards",
}


def parse_authors(raw: str) -> list[str]:
    return [a.strip() for a in raw.split(",") if a.strip()]


def tokenize_title(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{1,}", title.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def bucket_team_size(n: int) -> str:
    if n <= 2:
        return "1-2"
    if n <= 4:
        return "3-4"
    if n <= 6:
        return "5-6"
    if n <= 8:
        return "7-8"
    return "9+"


def bucket_title_len(n: int) -> str:
    if n <= 8:
        return "<=8"
    if n <= 12:
        return "9-12"
    if n <= 16:
        return "13-16"
    if n <= 20:
        return "17-20"
    return "21+"


def svg_bar_chart(title: str, data: list[tuple[str, int]], width: int = 620, height: int = 280) -> str:
    if not data:
        return ""
    margin = 48
    inner_w = width - margin * 2
    inner_h = height - margin * 2
    max_v = max(v for _, v in data) or 1
    bar_w = inner_w / len(data)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">']
    parts.append(f'<text x="{width/2}" y="26" text-anchor="middle" class="chart-title">{html.escape(title)}</text>')
    parts.append(f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" class="axis"/>')

    for i, (label, value) in enumerate(data):
        h = 0 if max_v == 0 else (value / max_v) * (inner_h - 8)
        x = margin + i * bar_w + 8
        y = height - margin - h
        bw = max(16, bar_w - 16)
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" class="bar"/>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{height-margin+16}" text-anchor="middle" class="xlab">{html.escape(label)}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{max(40, y-6):.1f}" text-anchor="middle" class="val">{value}</text>')

    parts.append("</svg>")
    return "".join(parts)


def build_dashboard(records: list[dict]) -> str:
    paper_count = len(records)
    all_authors = []
    team_sizes = []
    title_lens = []
    colon_titles = 0
    code_count = 0

    keyword_counter: Counter[str] = Counter()
    for r in records:
        authors = parse_authors(r.get("authors", ""))
        all_authors.extend(authors)
        team_sizes.append(len(authors))

        title = r.get("title", "")
        if ":" in title:
            colon_titles += 1
        title_lens.append(len(re.findall(r"\w+", title)))

        if (r.get("code_url") or "").strip():
            code_count += 1

        keyword_counter.update(tokenize_title(title))

    unique_author_count = len(set(all_authors))
    avg_authors = (sum(team_sizes) / paper_count) if paper_count else 0.0
    pct_code = (code_count / paper_count * 100) if paper_count else 0.0
    pct_colon = (colon_titles / paper_count * 100) if paper_count else 0.0

    team_bucket_counts = Counter(bucket_team_size(n) for n in team_sizes)
    title_bucket_counts = Counter(bucket_title_len(n) for n in title_lens)

    team_data = [(k, team_bucket_counts.get(k, 0)) for k in ["1-2", "3-4", "5-6", "7-8", "9+"]]
    title_data = [(k, title_bucket_counts.get(k, 0)) for k in ["<=8", "9-12", "13-16", "17-20", "21+"]]
    hot_topics = keyword_counter.most_common(14)

    topic_lines = "".join(
        f"<li><span>{html.escape(k)}</span><b>{v}</b></li>" for k, v in hot_topics
    )

    surprise_1 = f"{team_bucket_counts.get('3-4', 0)} papers have 3-4 authors, the largest team-size bucket."
    surprise_2 = f"{pct_colon:.1f}% of titles include a colon, showing a strong two-part naming style."
    surprise_3 = f"{pct_code:.1f}% include an explicit code link in the paper page metadata."

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>CVPR 2024 Paper Dashboard</title>
<style>
:root {{ --bg:#f4f1ea; --ink:#1d2b2a; --card:#fffaf2; --accent:#0f766e; --accent2:#dc6b2f; --muted:#5f6b6a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: 'Trebuchet MS', 'Avenir Next', sans-serif; color:var(--ink); background:radial-gradient(circle at 10% 10%, #fff7dd, transparent 40%), radial-gradient(circle at 90% 20%, #d8f2ef, transparent 38%), var(--bg); }}
.container {{ max-width:1100px; margin:0 auto; padding:28px 16px 40px; }}
h1 {{ margin:0 0 8px; font-size:2rem; letter-spacing:0.3px; }}
.sub {{ color:var(--muted); margin:0 0 18px; }}
.grid {{ display:grid; gap:12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
.card {{ background:var(--card); border:1px solid #e6dcc8; border-radius:14px; padding:14px; box-shadow:0 4px 18px rgba(20,30,28,0.06); }}
.kpi-label {{ font-size:0.84rem; color:var(--muted); }}
.kpi-val {{ font-size:1.7rem; font-weight:700; margin-top:4px; }}
.section {{ margin-top:18px; }}
.section h2 {{ margin:0 0 10px; font-size:1.15rem; }}
.two-col {{ display:grid; gap:12px; grid-template-columns: 1fr 1fr; }}
.chart-title {{ font-size:14px; font-weight:600; fill:var(--ink); }}
.axis {{ stroke:#546261; stroke-width:1; }}
.bar {{ fill:var(--accent); }}
.xlab {{ font-size:11px; fill:var(--muted); }}
.val {{ font-size:11px; fill:var(--accent2); font-weight:700; }}
.topic-list {{ list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px; }}
.topic-list li {{ display:flex; justify-content:space-between; padding:8px 10px; border:1px dashed #d7cab1; border-radius:10px; background:#fffdf8; }}
.surprise li {{ margin-bottom:6px; }}
@media (max-width:900px) {{ .two-col {{ grid-template-columns:1fr; }} h1 {{ font-size:1.6rem; }} }}
</style>
</head>
<body>
  <main class=\"container\">
    <h1>CVPR 2024 Paper Dashboard</h1>
    <p class=\"sub\">Generated from scraped metadata in <code>cvpr2024_papers.json</code>.</p>

    <section class=\"grid\">
      <article class=\"card\"><div class=\"kpi-label\">Count of Papers</div><div class=\"kpi-val\">{paper_count}</div></article>
      <article class=\"card\"><div class=\"kpi-label\">Unique Authors</div><div class=\"kpi-val\">{unique_author_count}</div></article>
      <article class=\"card\"><div class=\"kpi-label\">Avg Authors / Paper</div><div class=\"kpi-val\">{avg_authors:.2f}</div></article>
      <article class=\"card\"><div class=\"kpi-label\">Papers with Open Source Code</div><div class=\"kpi-val\">{pct_code:.1f}%</div></article>
      <article class=\"card\"><div class=\"kpi-label\">Titles Containing ':'</div><div class=\"kpi-val\">{pct_colon:.1f}%</div></article>
    </section>

    <section class=\"section card\">
      <h2>Hot Topics (From Title Keywords)</h2>
      <ul class=\"topic-list\">{topic_lines}</ul>
    </section>

    <section class=\"section card\">
      <h2>Surprises</h2>
      <ul class=\"surprise\">
        <li>{html.escape(surprise_1)}</li>
        <li>{html.escape(surprise_2)}</li>
        <li>{html.escape(surprise_3)}</li>
      </ul>
    </section>

    <section class=\"section two-col\">
      <article class=\"card\">{svg_bar_chart('Team Size Distribution', team_data)}</article>
      <article class=\"card\">{svg_bar_chart('Title Length Distribution (Words)', title_data)}</article>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CVPR 2024 dashboard HTML")
    parser.add_argument("--input", type=Path, default=Path("3.1_cvpr_conf_extract/results/cvpr2024_papers.json"))
    parser.add_argument("--output", type=Path, default=Path("3.1_cvpr_conf_extract/results/cvpr2024_dashboard.html"))
    args = parser.parse_args()

    records = json.loads(args.input.read_text(encoding="utf-8"))
    html_doc = build_dashboard(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_doc, encoding="utf-8")
    print(f"Saved dashboard to {args.output}")


if __name__ == "__main__":
    main()
