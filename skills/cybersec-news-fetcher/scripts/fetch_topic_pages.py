#!/usr/bin/env python3
"""
fetch_topic_pages.py — fetch HTML cyber insurance topic pages, extract article links,
verify candidate article pages, and write JSON.

Stdlib only: urllib, re, json, html, datetime.

Usage:
  py skills\\vault-cybersec-news-fetcher\\scripts\\fetch_topic_pages.py ^
    --sources skills\\vault-cybersec-news-fetcher\\assets\\templates\\cyber_insurance_topic_pages.json ^
    --output output\\topic_items.json
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


USER_AGENT = "Mozilla/5.0 (compatible; CyberInsuranceTopicFetcher/2.0; +https://example.com)"
FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT_S = 15
SLEEP_BETWEEN = 1.0


def log(msg: str) -> None:
    print(f"[fetch_topic_pages] {msg}", file=sys.stderr)


@dataclass
class TopicSource:
    name: str
    url: str
    category: str
    authority_tier: int
    allow_paths: list[str]


def fetch_url(url: str, ua: str = USER_AGENT) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()


def fetch_with_retry(url: str) -> bytes:
    last_err = None
    for attempt, ua in enumerate([USER_AGENT, USER_AGENT, FALLBACK_UA]):
        try:
            if attempt > 0:
                time.sleep(2)
            return fetch_url(url, ua=ua)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 401) and ua != FALLBACK_UA:
                continue
            if 500 <= e.code < 600 and attempt < 2:
                continue
            raise
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
            last_err = e
            if attempt < 2:
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("unreachable")


def text_from_html(fragment: str) -> str:
    fragment = re.sub(r"<script[\s\S]*?</script>", "", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"<style[\s\S]*?</style>", "", fragment, flags=re.IGNORECASE)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html_mod.unescape(fragment)
    fragment = re.sub(r"\s+", " ", fragment).strip()
    return fragment


def is_cyber_insurance_text(text: str) -> bool:
    t = text.lower()

    cyber_terms = [
        "cyber", "cybersecurity", "ransomware", "data breach", "privacy",
        "incident response", "cyber risk", "cyber liability", "cyber insurance",
        "cyber-insurance", "coverage", "exclusion", "endorsement", "underwriting",
        "claims", "premium", "capacity", "broker", "policy", "reinsurance",
        "sme", "small business", "ai", "fourth-party", "vendor", "war exclusion"
    ]
    if not any(term in t for term in cyber_terms):
        return False

    insurance_terms = [
        "insurance", "insurer", "underwriting", "policy", "claims",
        "coverage", "premium", "premiums", "broker", "carrier",
        "capacity", "exclusion", "endorsement", "reinsurance", "loss"
    ]
    return any(term in t for term in insurance_terms)


def page_title(html_text: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    return text_from_html(m.group(1))


def extract_links_generic(html_text: str, base_url: str, allow_paths: list[str]) -> list[dict]:
    html_text = re.sub(r"<script[\s\S]*?</script>", "", html_text, flags=re.IGNORECASE)
    html_text = re.sub(r"<style[\s\S]*?</style>", "", html_text, flags=re.IGNORECASE)

    anchors = re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    items: list[dict] = []
    for href, inner in anchors:
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue

        href_abs = urllib.parse.urljoin(base_url, href)
        parsed = urllib.parse.urlparse(href_abs)

        if allow_paths:
            if not any(path in parsed.path for path in allow_paths):
                continue

        text = text_from_html(inner)
        if len(text) < 12:
            continue

        # candidate link text should at least smell like insurance/cyber
        if not is_cyber_insurance_text(text):
            continue

        items.append({"title": text, "url": href_abs})

    return items


def verify_candidate(url: str) -> tuple[str, bool]:
    try:
        raw = fetch_with_retry(url)
        html_text = raw.decode("utf-8", errors="replace")
        title = page_title(html_text)
        if not title:
            title = url
        return title, is_cyber_insurance_text(title + " " + url)
    except Exception:
        # if article page fetch fails, fall back to URL/title guess
        return url, is_cyber_insurance_text(url)


def normalize_items(raw_items: list[dict], source: TopicSource, now: datetime) -> list[dict]:
    out: list[dict] = []
    for it in raw_items:
        title = (it.get("title") or "").strip()
        url = (it.get("url") or "").strip()
        if not title or not url:
            continue

        verified_title, ok = verify_candidate(url)
        if not ok and not is_cyber_insurance_text(title):
            continue

        item = {
            "title": verified_title if verified_title else title,
            "summary": "",
            "url": url,
            "published_date": now.isoformat(),
            "source_name": source.name,
            "raw_age_hours": 0.0,
            "scraped_from_topic_page": True,
            "category": source.category,
            "authority_tier": source.authority_tier,
        }
        out.append(item)
    return out


def load_sources(path: Path) -> list[TopicSource]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    raw = cfg.get("topic_pages", [])
    if not isinstance(raw, list):
        raise ValueError("topic_pages must be a list")

    sources: list[TopicSource] = []
    for s in raw:
        allow_paths = s.get("allow_paths", [])
        if isinstance(allow_paths, str):
            allow_paths = [allow_paths]
        sources.append(
            TopicSource(
                name=s["name"],
                url=s["url"],
                category=s.get("category", "market"),
                authority_tier=int(s.get("authority_tier", 2)),
                allow_paths=list(allow_paths),
            )
        )
    return sources


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch cyber insurance topic pages.")
    p.add_argument("--sources", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    sources_path = Path(args.sources)
    if not sources_path.exists():
        log(f"ERROR: sources file not found: {sources_path}")
        return 2

    try:
        sources = load_sources(sources_path)
    except Exception as e:
        log(f"ERROR: unable to load sources: {e}")
        return 2

    now = datetime.now(timezone.utc)
    all_items: list[dict] = []
    failed: list[dict] = []

    for src in sources:
        log(f"Fetching topic page: {src.name} ({src.url})")
        try:
            raw = fetch_with_retry(src.url)
            html_text = raw.decode("utf-8", errors="replace")
            log(f"  page title: {page_title(html_text)[:120]}")
            candidates = extract_links_generic(html_text, src.url, src.allow_paths)
            log(f"  extracted {len(candidates)} candidate links")
            items = normalize_items(candidates, src, now)
            log(f"  normalized {len(items)} items")
            all_items.extend(items)
            time.sleep(SLEEP_BETWEEN)
        except urllib.error.HTTPError as e:
            log(f"  HTTP error {e.code}")
            failed.append({"name": src.name, "reason": f"HTTP {e.code}"})
        except urllib.error.URLError as e:
            log(f"  URLError: {e.reason}")
            failed.append({"name": src.name, "reason": f"URLError: {e.reason}"})
        except Exception as e:
            log(f"  Error: {type(e).__name__}: {e}")
            failed.append({"name": src.name, "reason": f"{type(e).__name__}: {e}"})

    out = {
        "generated_at": now.isoformat(),
        "sources_polled": len(sources),
        "sources_failed": failed,
        "items_raw": len(all_items),
        "items": all_items,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Wrote topic items: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
