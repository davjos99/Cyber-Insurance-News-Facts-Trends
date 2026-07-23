#!/usr/bin/env python3
"""
fetch_feeds.py — pull RSS/Atom from cybersec sources, normalize, write JSON.

Python stdlib ONLY. No feedparser, no requests, no pip installs.

Usage:
  python fetch_feeds.py --sources cybersec_sources.json --since 24 --output raw_news.json
  python fetch_feeds.py --test --output raw_news.json    # 3-source fixture mode

Output JSON shape:
  {
    "generated_at": "...",
    "window_hours": 24,
    "sources_polled": 10,
    "sources_succeeded": 9,
    "sources_failed": [{"name": "...", "reason": "..."}],
    "items_raw": 142,
    "items_after_time_filter": 38,
    "items": [
      {"title": "...", "summary": "...", "url": "...",
       "published_date": "...", "source_name": "...",
       "raw_age_hours": 4.2}
    ]
  }
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

USER_AGENT = "Mozilla/5.0 (compatible; ClaudeSkillFetcher/1.0; +https://anthropic.com)"
FALLBACK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT_S = 15
SUMMARY_MAX_CHARS = 500

def is_cyber_insurance(item: dict) -> bool:
    """Return True if this normalized item looks like cyber insurance news."""
    title = (item.get("title") or "").lower()
    desc = (item.get("summary") or "").lower()

    text = " ".join([title, desc])

    must_have_any = [
        "cyber insurance",
        "cyber-insurance",
        "cybersecurity insurance",
        "cyber risk",
        "cyber coverage",
        "cyber liability",
        "ransomware coverage",
        "cyber policy",
        "cyber premiums",
        "cyber underwriting",
    ]

    insurance_terms = [
        "insurance",
        "insurer",
        "underwriting",
        "policy",
        "premiums",
        "broker",
        "carrier",
    ]

    if not any(term in text for term in must_have_any):
        return False

    if not any(term in text for term in insurance_terms):
        return False

    return True

# Atom namespace map
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

TEST_SOURCES = [
    {"name": "The Hacker News",  "url": "https://feeds.feedburner.com/TheHackersNews", "authority_tier": 2},
    {"name": "KrebsOnSecurity",  "url": "https://krebsonsecurity.com/feed/",            "authority_tier": 1},
    {"name": "Bleeping Computer","url": "https://www.bleepingcomputer.com/feed/",        "authority_tier": 2},
]


def log(msg: str) -> None:
    print(f"[fetch_feeds] {msg}", file=sys.stderr)


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", "", s)
    # Decode common HTML entities (stdlib html.unescape handles numeric + named)
    import html as _html
    s = _html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def truncate(s: str, n: int = SUMMARY_MAX_CHARS) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "..."


def parse_date(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    # Try RFC 822 (RSS) first
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (TypeError, ValueError):
        pass
    # Try ISO 8601 (Atom)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ):
        try:
            iso = s.replace("Z", "+00:00") if fmt.endswith("Z") else s
            dt = datetime.strptime(iso, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Final attempt — fromisoformat is forgiving
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def fetch_url(url: str, ua: str = USER_AGENT) -> bytes:
    """One attempt with a polite UA. Raises on failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": ua,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()


def fetch_with_retry(url: str) -> bytes:
    """Polite UA, retry once on transient errors, fall back to browser UA on 403."""
    last_err = None
    for attempt, ua in enumerate([USER_AGENT, USER_AGENT, FALLBACK_UA]):
        try:
            if attempt > 0:
                time.sleep(2)
            return fetch_url(url, ua=ua)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 401) and ua != FALLBACK_UA:
                # Try fallback UA next iteration
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


def parse_feed_bytes(raw: bytes, source_name: str) -> list[dict]:
    """Auto-detect RSS vs Atom and return a list of normalized items."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise ValueError(f"XML parse error: {e}") from e

    items: list[dict] = []
    tag = root.tag.lower()
    # When the root uses xmlns="http://www.w3.org/2005/Atom" without a prefix,
    # ElementTree gives every child a {ns}name tag. Detect that case.
    is_atom_default_ns = root.tag.endswith("}feed") and "Atom" in root.tag

    if not is_atom_default_ns and ("rss" in tag or root.find("channel") is not None):
        # RSS 2.0
        channel = root.find("channel") or root
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = item.findtext("description") or ""
            content_encoded = item.find("content:encoded", NS)
            if content_encoded is not None and content_encoded.text:
                desc = content_encoded.text
            pub_date = item.findtext("pubDate") or item.findtext("dc:date", default="", namespaces=NS)
            items.append({
                "title": title,
                "summary": truncate(strip_html(desc)),
                "url": link,
                "published_date_raw": pub_date.strip() if pub_date else "",
            })
    else:
        # Atom 1.0 — try BOTH explicit atom: namespace AND default-namespace path
        def afind(parent, name):
            # Try unprefixed first (works when parser handles ns transparently)
            el = parent.find(name)
            if el is not None:
                return el
            return parent.find(f"atom:{name}", NS)

        def afindall(parent, name):
            els = parent.findall(name)
            if els:
                return els
            return parent.findall(f"atom:{name}", NS)

        entries = afindall(root, "entry")
        for entry in entries:
            t = afind(entry, "title")
            title = (t.text or "").strip() if t is not None and t.text else ""
            # link with rel="alternate" preferred
            link_el = None
            for cand in afindall(entry, "link"):
                if cand.get("rel", "alternate") == "alternate":
                    link_el = cand
                    break
            link = link_el.get("href", "").strip() if link_el is not None else ""
            sm = afind(entry, "summary")
            ct = afind(entry, "content")
            desc = ""
            if ct is not None and ct.text:
                desc = ct.text
            elif sm is not None and sm.text:
                desc = sm.text
            pub = afind(entry, "published") or afind(entry, "updated")
            pub_date = (pub.text or "").strip() if pub is not None and pub.text else ""
            if title and link:
                items.append({
                    "title": title,
                    "summary": truncate(strip_html(desc)),
                    "url": link,
                    "published_date_raw": pub_date,
                })

    return items


def normalize_items(items: list[dict], source_name: str, now: datetime) -> list[dict]:
    """Coerce parsed items to the canonical shape with raw_age_hours computed."""
    out: list[dict] = []
    for it in items:
        if not it.get("title") or not it.get("url"):
            continue  # skip empty entries
        dt = parse_date(it.get("published_date_raw", ""))
        fallback = dt is None
        if dt is None:
            dt = now  # treat as just-published
        age_hours = (now - dt).total_seconds() / 3600.0
        if age_hours < 0:
            age_hours = 0.0  # future-dated items get clamped
        item = {
            "title": it["title"],
            "summary": it.get("summary", ""),
            "url": it["url"],
            "published_date": dt.isoformat(),
            "source_name": source_name,
            "raw_age_hours": round(age_hours, 2),
        }
        if fallback:
            item["published_date_fallback"] = True
        out.append(item)
    return out


def fetch_one_source(source: dict, now: datetime) -> tuple[list[dict], str | None]:
    """Returns (items, error_reason). error_reason is None on success."""
    name = source["name"]
    url = source["url"]
    log(f"Fetching: {name}  ({url})")
    try:
        raw = fetch_with_retry(url)
    except urllib.error.HTTPError as e:
        return [], f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return [], f"URLError: {e.reason}"
    except (socket.timeout, TimeoutError):
        return [], "timeout"
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"

    try:
        parsed = parse_feed_bytes(raw, name)
    except ValueError as e:
        return [], f"parse error: {e}"

 # NEW: optional cyber-insurance filter for this source
    requires_filter = source.get("requires_filter", False)
    if requires_filter:
        before = len(parsed)
        parsed = [it for it in parsed if is_cyber_insurance(it)]
        after = len(parsed)
        log(f"  -> filtered cyber-insurance items: {after}/{before}")
  
    items = normalize_items(parsed, name, now)
    log(f"  -> {len(items)} items")
    return items, None


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch cybersec RSS feeds.")
    p.add_argument("--sources", help="Path to sources JSON.")
    p.add_argument("--since", type=float, default=24.0, help="Time window in hours (default 24).")
    p.add_argument("--output", required=True, help="Output JSON path.")
    p.add_argument("--test", action="store_true", help="Use 3-source fixture set.")
    args = p.parse_args()

    if args.test:
        sources = TEST_SOURCES
        log(f"TEST MODE — using {len(sources)} fixture sources")
    else:
        if not args.sources:
            print("ERROR: --sources required (or use --test)", file=sys.stderr)
            return 2
        sources_path = Path(args.sources)
        if not sources_path.exists():
            print(f"ERROR: sources file not found: {sources_path}", file=sys.stderr)
            return 2
        with sources_path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        sources = cfg.get("sources", [])

    now = datetime.now(timezone.utc)
    all_items: list[dict] = []
    failed: list[dict] = []
    succeeded = 0

    for src in sources:
        items, err = fetch_one_source(src, now)
        if err:
            failed.append({"name": src["name"], "reason": err})
            continue
        succeeded += 1
        all_items.extend(items)

    items_raw = len(all_items)
    log(f"Total items pre-filter: {items_raw}")

    # Time window filter
    filtered = [it for it in all_items if it["raw_age_hours"] <= args.since]
    log(f"After time filter (<={args.since}h): {len(filtered)}")

    out = {
        "generated_at": now.isoformat(),
        "window_hours": args.since,
        "sources_polled": len(sources),
        "sources_succeeded": succeeded,
        "sources_failed": failed,
        "items_raw": items_raw,
        "items_after_time_filter": len(filtered),
        "items": filtered,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    log(f"Wrote: {out_path}")
    if failed:
        log(f"Failed sources: {[f['name'] for f in failed]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
