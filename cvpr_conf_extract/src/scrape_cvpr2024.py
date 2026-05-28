#!/usr/bin/env python3
"""Scrape CVPR 2024 OpenAccess paper metadata to CSV/JSON without third-party deps."""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://openaccess.thecvf.com/CVPR2024?day=all"
SITE_ROOT = "https://openaccess.thecvf.com/"
USER_AGENT = "Mozilla/5.0 (compatible; CVPRScraper/1.0)"


@dataclass
class Paper:
    title: str
    authors: str
    abstract: str
    paper_url: str
    pdf_url: str
    supplemental_url: str


def fetch_html(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def clean_text(text: str) -> str:
    text = unescape(strip_tags(text))
    return re.sub(r"\s+", " ", text).strip()


def parse_listing(listing_html: str) -> List[dict]:
    pattern = re.compile(
        r'<dt class="ptitle">\s*<a href="(?P<href>[^"]+)">(?P<title>.*?)</a>\s*</dt>\s*<dd>(?P<authors>.*?)</dd>',
        re.DOTALL,
    )
    entries = []
    for m in pattern.finditer(listing_html):
        entries.append(
            {
                "title": clean_text(m.group("title")),
                "detail_url": urljoin(SITE_ROOT, m.group("href")),
                "authors": clean_text(m.group("authors")),
            }
        )
    return entries


def parse_detail(detail_html: str, detail_url: str) -> dict:
    abstract = ""
    m_abs = re.search(r"<div id=\"abstract\">\s*<b>Abstract</b>\s*(.*?)</div>", detail_html, re.DOTALL)
    if m_abs:
        abstract = clean_text(m_abs.group(1))

    pdf_url = ""
    supplemental_url = ""
    for href, label in re.findall(r'<a href="([^"]+)">([^<]+)</a>', detail_html, re.DOTALL):
        l = clean_text(label).lower()
        full = urljoin(SITE_ROOT, href)
        if "pdf" in l and not pdf_url:
            pdf_url = full
        if ("supp" in l or "supplement" in l) and not supplemental_url:
            supplemental_url = full

    return {"abstract": abstract, "pdf_url": pdf_url, "supplemental_url": supplemental_url, "paper_url": detail_url}


def scrape(limit: Optional[int], delay: float = 0.0) -> List[Paper]:
    listing_html = fetch_html(BASE_URL)
    entries = parse_listing(listing_html)
    if limit is not None:
        entries = entries[:limit]

    papers: List[Paper] = []
    for idx, entry in enumerate(entries, start=1):
        detail_html = fetch_html(entry["detail_url"])
        detail = parse_detail(detail_html, entry["detail_url"])
        papers.append(
            Paper(
                title=entry["title"],
                authors=entry["authors"],
                abstract=detail["abstract"],
                paper_url=detail["paper_url"],
                pdf_url=detail["pdf_url"],
                supplemental_url=detail["supplemental_url"],
            )
        )
        if delay > 0 and idx < len(entries):
            time.sleep(delay)
    return papers


def write_json(papers: List[Paper], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asdict(p) for p in papers], ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(papers: List[Paper], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "authors", "abstract", "paper_url", "pdf_url", "supplemental_url"],
        )
        writer.writeheader()
        for p in papers:
            writer.writerow(asdict(p))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape CVPR 2024 metadata")
    parser.add_argument("--limit", type=int, default=None, help="Only scrape first N papers")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=Path, default=Path("cvpr_conf_extract/results/cvpr2024_papers.json"))
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    papers = scrape(limit=args.limit, delay=args.delay)
    if args.format == "json":
        write_json(papers, args.output)
    else:
        write_csv(papers, args.output)

    print(f"Saved {len(papers)} papers to {args.output}")


if __name__ == "__main__":
    main()
