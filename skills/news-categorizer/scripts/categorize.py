#!/usr/bin/env python3
"""
categorize.py — deterministic heuristic categorizer for the cybersec briefing chain.

When this Skill is invoked through Claude Code, the LLM does the categorization
using SKILL.md guidance. When the orchestrator runs the chain headlessly (cron,
GitHub Actions), it calls THIS script as a fallback so the chain produces a
briefing without needing an LLM in the loop.

The heuristics are tuned conservatively — they pattern-match on the same signals
SKILL.md describes (CVE numbers, "patched", "breach", "ransomware", "released",
"acquired", "guide", "how to", etc.). Items that don't match a strong signal
default to News.

Python stdlib only.

Usage:
  python categorize.py --input deduped.json --output briefing.md
  python categorize.py --input deduped.json --output briefing.md --template /path/to/briefing_template.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# === Patterns ============================================================

THREAT_PATTERNS = [
    r"\bCVE-\d{4}-\d{4,7}\b",
    r"\bactive(ly)?\s+exploit",
    r"\bin[-\s]the[-\s]wild\b",
    r"\bzero[-\s]day\b",
    r"\b0[-\s]day\b",
    r"\bbreach(ed|es)?\b",
    r"\bransomware\b",
    r"\bdata\s+(theft|leak|stolen|exposed)\b",
    r"\b(records?|customers?)\s+(exposed|stolen|leaked)\b",
    r"\bmalicious\s+(npm|pypi|package|extension)\b",
    r"\bbackdoor(ed)?\b",
    r"\bsupply[-\s]chain\s+(attack|compromise)\b",
    r"\bphishing\s+campaign\b",
    r"\bRCE\b",
    r"\bremote\s+code\s+execution\b",
    r"\bprivilege\s+escalation\b",
    r"\bvulnerab(ility|ilities)\s+(in|affect)",
    r"\bexploit(ed|ation)\b",
    r"\bpatch\s+now\b",
    r"\bemergency\s+patch\b",
    r"\bleak\s+site\b",
]

NEWS_PATTERNS = [
    r"\bFBI\s+(seize|arrest|takedown)",
    r"\b(Europol|Interpol|NCA|DOJ)\s+(seize|arrest|operation)",
    r"\bacqui(re|sition|sitions)\b",
    r"\b(announces|launches|releases)\s+",  # vendor announcement — needs guarding below
    r"\bSEC\s+(rule|regulation|filing)",
    r"\bNIS2\b",
    r"\bGDPR\b",
    r"\bsanction(s|ed)\b",
    r"\bindict(ed|ment)\b",
    r"\bappointed\s+(CISO|CSO|CTO)",
    r"\b(takedown|disrupt|seize|seized)\b.{0,40}\b(operation|infrastructure|botnet|server)",
    r"\bnew\s+regulation\b",
    r"\bend[-\s]of[-\s]life\b",
]

ADVICE_PATTERNS = [
    r"\bhow\s+to\s+",
    r"\bharden(ing)?\s+",
    r"\bbest\s+practices?\b",
    r"\bguide\s+to\b",
    r"\b(playbook|recipe|tutorial|walkthrough)\b",
    r"\bdetect(ion|ing)\s+",
    r"\b(Splunk|Sigma|Yara|Snort)\s+(rule|query|signature)",
    r"\bopen[-\s]source(d)?\s+(tool|toolkit|library)",
    r"\bconfigur(e|ation)\s+",
    r"\bpost[-\s]mortem\b",
    r"\bdefend(ing)?\s+against\b",
    r"\bOWASP\b",
    r"\bNIST\s+(SP|publication|framework)",
    r"\bMITRE\s+ATT&CK\b",
]

DROP_PATTERNS = [
    r"\bsponsor(ed|ship)\b",
    r"\bpresented\s+by\b",
    r"\bbrought\s+to\s+you\s+by\b",
    r"\bin\s+partnership\s+with\b",
    r"\bjoin\s+us\s+at\b",
    r"\bregister\s+for\s+(our|the)\s+webinar\b",
    r"\bspeaking\s+session\b",
    r"\bMagic\s+Quadrant\b",
    r"\bForrester\s+Wave\b",
    r"\b(\d+\s+things\s+every|\d+\s+(best|top)\s+\w+\s+(of|for)\s+202)",
    r"\b(why|the\s+truth\s+about)\b.{0,80}\b(matters|important|cybersec|security)\b",
    r"\bthought\s+leader",
    # Vendor PR + promo formats
    r"\bTHN\s+Webinar\b",
    r"\[\s*Webinar\s*\]",
    r"\bLearn\s+How\s+to\s+Fight\s+Back\b",
    r"\bpodcastdetail\b",  # SANS daily stormcast filler entries
    r"\bStormcast\s+For\b",
]

# Banned phrases the validator enforces — drop or rewrite at summary time
BANNED_RE = re.compile(
    r"\b(critical|concerning|groundbreaking|game-changing|alarming|shocking|unprecedented|devastating|catastrophic|staggering)\b",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    print(f"[categorize] {msg}", file=sys.stderr)


def matches_any(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def count_matches(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


def categorize_item(item: dict) -> str | None:
    """Return 'Threats' / 'News' / 'Advice' / None (drop)."""
    text = f"{item.get('title','')} {item.get('summary','')}"

    if matches_any(text, DROP_PATTERNS):
        return None

    threat_score = count_matches(text, THREAT_PATTERNS)
    advice_score = count_matches(text, ADVICE_PATTERNS)
    news_score = count_matches(text, NEWS_PATTERNS)

    # Strong signals win
    if threat_score >= 1 and threat_score >= advice_score:
        return "Threats"
    if advice_score >= 2:
        return "Advice"
    if advice_score >= 1 and threat_score == 0:
        return "Advice"
    if news_score >= 1:
        return "News"

    # Default to News for items with no strong signal but no drop signal either
    return "News"


def authority_rank(source_name: str) -> int:
    table = {
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
    return table.get(source_name, 4)


def rank_within_bucket(items: list[dict], bucket: str) -> list[dict]:
    """Sort by (authority asc, recency asc) — best items first."""
    return sorted(items, key=lambda it: (authority_rank(it["source_name"]), it.get("raw_age_hours", 999)))


def clean_summary(text: str) -> str:
    """Strip banned phrases out of the auto-generated summary."""
    return BANNED_RE.sub("", text).replace("  ", " ").strip()


def render_item(item: dict) -> str:
    title = item["title"].strip().rstrip(".")
    summary = clean_summary(item.get("summary", ""))
    if not summary:
        summary = "(no summary available from source)"
    elif len(summary) > 280:
        # Trim to last full sentence within 280 chars
        cut = summary[:280].rsplit(".", 1)[0]
        summary = cut + "." if cut else summary[:280] + "..."
    source_name = item["source_name"]
    url = item["url"]
    return f"- **{title}** — {summary} [Source: {source_name}]({url})"


def build_briefing(data: dict, template_text: str) -> str:
    items = data.get("items", [])
    buckets: dict[str, list[dict]] = {"Threats": [], "News": [], "Advice": []}
    dropped = 0
    for it in items:
        cat = categorize_item(it)
        if cat is None:
            dropped += 1
            continue
        buckets[cat].append(it)

    # Rank + cap at 5
    for bucket in buckets:
        buckets[bucket] = rank_within_bucket(buckets[bucket], bucket)[:5]

    log(f"Categorized: Threats={len(buckets['Threats'])} News={len(buckets['News'])} Advice={len(buckets['Advice'])} Dropped={dropped}")

    items_kept = sum(len(v) for v in buckets.values())

    def render_bucket(items: list[dict], bucket_name: str) -> str:
        if not items:
            return f"_No material {bucket_name.lower()}-grade items in the window._"
        return "\n".join(render_item(it) for it in items)

    now = datetime.now(timezone.utc)
    failed = data.get("sources_failed", [])
    failed_note = ""
    if failed:
        names = ", ".join(f["name"] for f in failed)
        failed_note = f"\n_Sources that failed this run: {names}_"

    # Parse generated_at to a date string
    gen_at_raw = data.get("generated_at", now.isoformat())
    try:
        gen_at = datetime.fromisoformat(gen_at_raw.replace("Z", "+00:00"))
    except ValueError:
        gen_at = now

    rendered = template_text
    replacements = {
        "{DATE}": gen_at.strftime("%Y-%m-%d"),
        "{WINDOW_HOURS}": str(int(data.get("window_hours", 24))),
        "{SOURCES_POLLED}": str(data.get("sources_polled", 0)),
        "{ITEMS_REVIEWED}": str(data.get("items_after_dedupe", data.get("items_after_time_filter", len(items)))),
        "{ITEMS_KEPT}": str(items_kept),
        "{THREATS_ITEMS}": render_bucket(buckets["Threats"], "Threats"),
        "{NEWS_ITEMS}": render_bucket(buckets["News"], "News"),
        "{ADVICE_ITEMS}": render_bucket(buckets["Advice"], "Advice"),
        "{TIMESTAMP}": gen_at.strftime("%Y-%m-%dT%H:%M:%S"),
        "{SOURCES_SUCCEEDED}": str(data.get("sources_succeeded", 0)),
        "{FAILED_SOURCES_NOTE}": failed_note,
    }
    for k, v in replacements.items():
        rendered = rendered.replace(k, v)
    return rendered


def main() -> int:
    p = argparse.ArgumentParser(description="Categorize cybersec news into a briefing.")
    p.add_argument("--input", required=True, help="Deduped news JSON (from dedupe.py)")
    p.add_argument("--output", required=True, help="Output briefing.md")
    p.add_argument("--template", help="Custom briefing template (defaults to ../assets/templates/briefing_template.md)")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        log(f"ERROR: input not found: {in_path}")
        return 2

    if args.template:
        tmpl_path = Path(args.template)
    else:
        tmpl_path = Path(__file__).parent.parent / "assets" / "templates" / "briefing_template.md"

    if not tmpl_path.exists():
        log(f"ERROR: template not found: {tmpl_path}")
        return 2

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    template_text = tmpl_path.read_text(encoding="utf-8")

    briefing = build_briefing(data, template_text)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(briefing, encoding="utf-8")
    log(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
