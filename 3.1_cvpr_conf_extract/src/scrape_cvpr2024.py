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
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_LISTING_URLS = [
    "https://openaccess.thecvf.com/CVPR2024?day=2024-06-19",
    "https://openaccess.thecvf.com/CVPR2024?day=2024-06-20",
    "https://openaccess.thecvf.com/CVPR2024?day=2024-06-21",
]
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
    code_url: str


def fetch_html(url: str, timeout: int = 10) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_html_with_retry(url: str, timeout: int = 10, retries: int = 4, backoff: float = 1.2) -> str:
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            return fetch_html(url, timeout=timeout)
        except Exception as exc:
            last_exc = exc
            if attempt == retries:
                break
            sleep_s = backoff * (2 ** (attempt - 1))
            print(f"[retry] {url} attempt {attempt}/{retries} failed: {exc}. sleeping {sleep_s:.1f}s")
            time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def clean_text(text: str) -> str:
    text = unescape(strip_tags(text))
    return re.sub(r"\s+", " ", text).strip()


def parse_listing(listing_html: str) -> List[dict]:
    pattern = re.compile(
        r'<dt class="ptitle">.*?<a href="(?P<href>[^"]+)">(?P<title>.*?)</a>\s*</dt>\s*<dd>(?P<authors>.*?)</dd>',
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
    m_abs = re.search(r"<div id=\"abstract\">\s*(.*?)\s*</div>", detail_html, re.DOTALL)
    if m_abs:
        abstract = clean_text(m_abs.group(1))

    pdf_url = ""
    supplemental_url = ""
    code_url = ""
    for href, label in re.findall(r'<a href="([^"]+)">([^<]+)</a>', detail_html, re.DOTALL):
        l = clean_text(label).lower()
        full = urljoin(SITE_ROOT, href)
        if "pdf" in l and not pdf_url:
            pdf_url = full
        if ("supp" in l or "supplement" in l) and not supplemental_url:
            supplemental_url = full
        if ("github.com" in full.lower() or "code" in l) and not code_url:
            code_url = full

    return {
        "abstract": abstract,
        "pdf_url": pdf_url,
        "supplemental_url": supplemental_url,
        "code_url": code_url,
        "paper_url": detail_url,
    }


def unique_entries(entries: Iterable[dict]) -> List[dict]:
    seen = set()
    unique = []
    for entry in entries:
        detail_url = entry["detail_url"]
        if detail_url in seen:
            continue
        seen.add(detail_url)
        unique.append(entry)
    return unique


def load_resume_state(path: Path) -> Dict[str, dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    by_url: Dict[str, dict] = {}
    for item in data:
        if isinstance(item, dict) and item.get("paper_url"):
            by_url[item["paper_url"]] = item
    return by_url


def save_checkpoint(records: Dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records.values(), key=lambda x: x.get("paper_url", ""))
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def scrape(
    limit: Optional[int],
    delay: float = 0.0,
    listing_urls: Optional[List[str]] = None,
    timeout: int = 10,
    retries: int = 4,
    checkpoint_every: int = 50,
    resume_file: Optional[Path] = None,
) -> List[Paper]:
    urls = listing_urls or DEFAULT_LISTING_URLS
    all_entries = []
    for listing_url in urls:
        listing_html = fetch_html_with_retry(listing_url, timeout=timeout, retries=retries)
        all_entries.extend(parse_listing(listing_html))

    entries = unique_entries(all_entries)
    if limit is not None:
        entries = entries[:limit]

    resume_by_url: Dict[str, dict] = {}
    if resume_file is not None:
        resume_by_url = load_resume_state(resume_file)
        if resume_by_url:
            print(f"[resume] loaded {len(resume_by_url)} records from {resume_file}")

    records_by_url: Dict[str, dict] = dict(resume_by_url)
    papers: List[Paper] = []
    updated_since_checkpoint = 0
    for idx, entry in enumerate(entries, start=1):
        existing = records_by_url.get(entry["detail_url"])
        if existing and existing.get("abstract"):
            papers.append(Paper(**existing))
            continue
        try:
            detail_html = fetch_html_with_retry(entry["detail_url"], timeout=timeout, retries=retries)
            detail = parse_detail(detail_html, entry["detail_url"])
        except Exception as exc:
            print(f"[warn] failed detail fetch for {entry['detail_url']}: {exc}")
            detail = {
                "abstract": "",
                "pdf_url": "",
                "supplemental_url": "",
                "code_url": "",
                "paper_url": entry["detail_url"],
            }
        papers.append(
            Paper(
                title=entry["title"],
                authors=entry["authors"],
                abstract=detail["abstract"],
                paper_url=detail["paper_url"],
                pdf_url=detail["pdf_url"],
                supplemental_url=detail["supplemental_url"],
                code_url=detail["code_url"],
            )
        )
        records_by_url[entry["detail_url"]] = asdict(papers[-1])
        updated_since_checkpoint += 1

        if resume_file is not None and checkpoint_every > 0 and updated_since_checkpoint >= checkpoint_every:
            save_checkpoint(records_by_url, resume_file)
            print(f"[checkpoint] {len(records_by_url)}/{len(entries)} saved to {resume_file}")
            updated_since_checkpoint = 0

        if delay > 0 and idx < len(entries):
            time.sleep(delay)

    if resume_file is not None:
        save_checkpoint(records_by_url, resume_file)
        print(f"[checkpoint] final save {len(records_by_url)} records to {resume_file}")
    return papers


def write_json(papers: List[Paper], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asdict(p) for p in papers], ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(papers: List[Paper], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "authors", "abstract", "paper_url", "pdf_url", "supplemental_url", "code_url"],
        )
        writer.writeheader()
        for p in papers:
            writer.writerow(asdict(p))


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape CVPR 2024 metadata")
    parser.add_argument("--limit", type=int, default=None, help="Only scrape first N papers")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=Path, default=Path("3.1_cvpr_conf_extract/results/cvpr2024_papers.json"))
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between requests (seconds)")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds per request")
    parser.add_argument("--retries", type=int, default=4, help="Retry attempts per request")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=50,
        help="Write resume checkpoint every N processed papers (0 to disable)",
    )
    parser.add_argument(
        "--resume-file",
        type=Path,
        default=Path("3.1_cvpr_conf_extract/results/cvpr2024_papers_resume.json"),
        help="Checkpoint file for resumable runs",
    )
    parser.add_argument(
        "--listing-url",
        action="append",
        dest="listing_urls",
        help="Listing page URL to scrape; repeat to scrape multiple listing pages",
    )
    args = parser.parse_args()

    papers = scrape(
        limit=args.limit,
        delay=args.delay,
        listing_urls=args.listing_urls,
        timeout=args.timeout,
        retries=args.retries,
        checkpoint_every=args.checkpoint_every,
        resume_file=args.resume_file,
    )
    if args.format == "json":
        write_json(papers, args.output)
    else:
        write_csv(papers, args.output)

    print(f"Saved {len(papers)} papers to {args.output}")


if __name__ == "__main__":
    main()
