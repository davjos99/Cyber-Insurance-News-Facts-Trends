#!/usr/bin/env python3
"""
dedupe.py — two-pass dedup across cybersec sources.

Pass 1: URL canonicalization (strip tracking params, lowercase host)
Pass 2: Title Jaccard similarity >= 0.85 across sources, keep higher-authority

Authority order (lower number = higher authority):
  1 = KrebsOnSecurity, SANS ISC, Schneier, US-CERT
  2 = The Hacker News, Bleeping Computer, Cisco Talos
  3 = Dark Reading, ThreatPost, CSO Online
  4 = anything else

Usage:
  python dedupe.py --input raw_news.json --output deduped.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

AUTHORITY = {
    "KrebsOnSecurity": 1,
    "SANS Internet Storm Center": 1,
    "Schneier on Security": 1,
    "US-CERT CISA Alerts": 1,
    "The Hacker News": 2,
    "Bleeping Computer": 2,
    "Cisco Talos": 2,
    "Dark Reading": 3,
    "ThreatPost": 3,
    "CSO Online": 3,
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "this", "that", "these", "those",
    "it", "its", "their", "them", "they", "we", "our", "us", "you", "your",
    "new", "now", "more", "than", "after", "before", "into", "over", "under",
}


def log(msg: str) -> None:
    print(f"[dedupe] {msg}", file=sys.stderr)


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url
    host = parts.netloc.lower()
    # Strip www. for canonical comparison
    if host.startswith("www."):
        host = host[4:]
    # Drop tracking params
    if parts.query:
        kept = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(("utm_", "ref", "src", "fbclid", "gclid", "mc_"))]
        query = urlencode(kept)
    else:
        query = ""
    # Drop fragment
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", host, path, query, ""))


def title_tokens(title: str) -> set[str]:
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    words = [w for w in t.split() if w and w not in STOPWORDS and len(w) > 2]
    return set(words)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def authority_rank(source_name: str) -> int:
    return AUTHORITY.get(source_name, 4)


def dedupe_items(items: list[dict]) -> tuple[list[dict], dict]:
    stats = {"input_count": len(items), "url_collapsed": 0, "title_collapsed": 0}

    # Pass 1: URL canonicalization
    by_canon: dict[str, dict] = {}
    for it in items:
        canon = canonicalize_url(it.get("url", ""))
        if not canon:
            # No URL — keep with synthetic key so we still emit it
            by_canon[f"__no_url__{id(it)}"] = it
            continue
        if canon in by_canon:
            stats["url_collapsed"] += 1
            existing = by_canon[canon]
            if authority_rank(it["source_name"]) < authority_rank(existing["source_name"]):
                by_canon[canon] = it
        else:
            by_canon[canon] = it

    pass1 = list(by_canon.values())
    log(f"Pass 1 (URL canon): {len(items)} -> {len(pass1)}  (collapsed {stats['url_collapsed']})")

    # Pass 2: title Jaccard. Compare each item to those kept so far.
    kept: list[dict] = []
    kept_tokens: list[set[str]] = []
    for it in pass1:
        toks = title_tokens(it.get("title", ""))
        merged = False
        for idx, existing_toks in enumerate(kept_tokens):
            sim = jaccard(toks, existing_toks)
            if sim >= 0.85:
                stats["title_collapsed"] += 1
                # Replace the kept one if this one is higher authority
                existing = kept[idx]
                if authority_rank(it["source_name"]) < authority_rank(existing["source_name"]):
                    kept[idx] = it
                    kept_tokens[idx] = toks
                merged = True
                break
        if not merged:
            kept.append(it)
            kept_tokens.append(toks)

    log(f"Pass 2 (title Jaccard >=0.85): {len(pass1)} -> {len(kept)}  (collapsed {stats['title_collapsed']})")
    stats["output_count"] = len(kept)
    return kept, stats


def main() -> int:
    p = argparse.ArgumentParser(description="Dedupe cybersec news items.")
    p.add_argument("--input", required=True, help="Input JSON (from fetch_feeds.py)")
    p.add_argument("--output", required=True, help="Output JSON")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        return 2

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    deduped, stats = dedupe_items(items)

    data["items"] = deduped
    data["items_after_dedupe"] = len(deduped)
    data["dedupe_stats"] = stats

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Wrote: {out_path}  ({len(deduped)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
