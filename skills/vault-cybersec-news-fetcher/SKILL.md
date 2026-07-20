---
name: cybersec-news-fetcher
description: Fetch the last 24-168 hours of cybersecurity news from 10-15 trusted RSS sources (The Hacker News, KrebsOnSecurity, Bleeping Computer, SANS ISC, US-CERT, Schneier, Cisco Talos, Dark Reading, ThreatPost, CSO Online), dedupe across sources, and write a normalized raw_news.json the categorizer can consume. Python stdlib only — no feedparser, no requests, no pip installs. Trigger when the user says "fetch cyber news", "pull infosec headlines", "what cybersec news today", "cybersecurity briefing", or "run the news fetcher".
allowed-tools: Read, Bash, Write
---

# Cybersec News Fetcher

The first link in the morning cybersec briefing chain. Pulls raw RSS items from 10-15 trusted sources, normalizes them into one JSON shape, dedupes across feeds, and hands the output to the categorizer. Uses Python stdlib only — drop into `~/.claude/skills/` and run, no `pip install` step.

> **Operating principle:** A briefing is only as good as its sources. Better to skip a flaky source than poison the briefing with low-signal noise. Better to dedupe aggressively than ship a brief that says the same breach three times in three voices.

## When to run

Run this as Step 1 of the morning briefing chain. Also run it standalone when:

- A member asks "what cybersec news today" (last 24h)
- A weekly cybersec digest is being assembled (last 168h)
- A research dossier needs the last 30 days of CVE / breach news on a vendor
- The orchestrator is calling fetch → categorize → publish in sequence

Default window is the last 24 hours. Pass `--since 168` for weekly digests.

## Inputs

| File | Status | Source | What it provides |
|---|---|---|---|
| `assets/templates/cybersec_sources.json` | required (default ships) | Pre-populated 10-source list | The RSS feed URLs to poll |
| `--since <hours>` | required (default 24) | CLI flag | Time window — drops items older than this |
| `--output <path>` | required | CLI flag | Where to write the normalized raw_news.json |
| `--test` | optional | CLI flag | Use 3-source fixture mode (Hacker News + Krebs + Bleeping) for fast dev loop |

## Workflow

### Step 1 — Load source list

Read `assets/templates/cybersec_sources.json`. Each entry has a `name`, `url`, and optional `category` tag. If a member wants to swap sources (drop ThreatPost, add Recorded Future), they edit this file — not the script.

### Step 2 — Fetch each feed, parse RSS

For each source, run `scripts/fetch_feeds.py`. The script:

- Uses `urllib.request` with a polite User-Agent (`Mozilla/5.0 (compatible; ClaudeSkillFetcher/1.0)`)
- Times out at 15 seconds per feed (some cybersec sources hang under load)
- Retries once on transient errors (5xx, timeout)
- Parses RSS 2.0 + Atom 1.0 with `xml.etree.ElementTree`
- Logs which sources blocked, 4xx'd, or returned empty

> **Voice rule:** Fail loud, continue gracefully. If KrebsOnSecurity blocks the User-Agent today, log it, skip it, and finish the briefing with 9 sources instead of 10. Never HALT the chain over a single dead feed.

### Step 3 — Normalize every item to one shape

Every feed returns its own quirky RSS dialect. The fetcher coerces them all into:

```json
{
  "title": "string (required)",
  "summary": "string (the <description> or <content:encoded>, HTML-stripped, truncated to 500 chars)",
  "url": "string (canonical https://)",
  "published_date": "ISO 8601 string",
  "source_name": "string (which feed it came from)",
  "raw_age_hours": "float (computed at fetch time)"
}
```

### Step 4 — Time-window filter

Drop items where `raw_age_hours > --since`. This is the cheap pre-dedupe filter — no point deduping 200 items when 180 are too old.

### Step 5 — Dedupe across sources

Run `scripts/dedupe.py` on the time-filtered output. Two-pass dedup:

1. **URL canonicalization** — strip tracking params (`?utm_*`, `?ref=`, `#anchor`), lowercase host, drop trailing `/`. Identical canonical URLs → dedupe.
2. **Title fuzzy match** — if two items from different sources have title similarity ≥0.85 (Jaccard on lowercased word sets, stripped of stopwords), keep the one from the higher-authority source. Authority order: KrebsOnSecurity > SANS ISC > Schneier > Cisco Talos > The Hacker News > everyone else.

### Step 6 — Write raw_news.json

Output schema:

```json
{
  "generated_at": "ISO 8601 timestamp",
  "window_hours": 24,
  "sources_polled": 10,
  "sources_succeeded": 9,
  "sources_failed": [{"name": "ThreatPost", "reason": "HTTP 403"}],
  "items_raw": 142,
  "items_after_time_filter": 38,
  "items_after_dedupe": 31,
  "items": [ { ... normalized item ... } ]
}
```

The categorizer (Skill 2) reads `items[]` and the metadata block above it.

## What not to do

- Do not invent items if a source is down. Just log the failure and continue with fewer sources.
- Do not bypass the time-window filter. A "weekly briefing" that includes 6-month-old items is junk.
- Do not skip the User-Agent. Several cybersec sources block default Python user agents — set the explicit Mozilla string.
- Do not install `feedparser` or `requests`. Stdlib only. The whole point is members can drop the bundle in and run without a virtualenv.
- Do not write the briefing — that is Skill 2's job. This skill stops at normalized JSON.

## Reference files

- `references/cybersec_feed_sources.md` — the 15 trusted sources with URLs, what each covers, who runs them, why they earn a slot
- `references/fetch_patterns.md` — User-Agent rotation, retry strategy, timeout handling, RSS-vs-Atom parsing gotchas
- (optional, member can add) `references/private_sources.md` — paid feeds the member has access to (Recorded Future, Mandiant, etc.)

## Scripts

- `scripts/fetch_feeds.py` — Python 3.10+, stdlib only. Hits each feed, parses RSS/Atom, normalizes, writes JSON. Supports `--test` mode for fast dev loops (3 fixture sources).
- `scripts/dedupe.py` — Cross-source dedup. Two-pass (URL canonicalization + title Jaccard). Reads raw_news.json, writes deduped.json.

## Assets

- `assets/templates/cybersec_sources.json` — Pre-populated 10-source list. Edit to add/drop sources.
- `assets/fixtures/sample_raw_news.json` — 5-item fixture for testing downstream Skills without hitting the network.

## License + attribution

Apache 2.0. See `LICENSE.txt`. Built fresh for Agent Skills Academy Vault Module G.6 — chains with `cybersec-news-categorizer` + `cybersec-news-page-publisher` under the `morning-cybersec-briefing` orchestrator. No upstream Anthropic plugin to attribute — the architecture mirrors Anthropic's `small-business` plugin pattern (pull → normalize → degrade → hand off) but the cybersec domain and source list are original.
