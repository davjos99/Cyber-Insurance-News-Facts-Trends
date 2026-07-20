# Cybersec Insurance News-Facts-Trends Fetcher

The first Skill in the morning cybersecurity briefing chain. Pulls RSS feeds from 10-15 trusted cybersec sources, normalizes everything to one JSON shape, dedupes across sources, and hands the output to the categorizer.

Python stdlib only. No `pip install`. Drop into `~/.claude/skills/` and run.

## What this Skill replaces

A $9-29/month RSS.app subscription, or roughly 20 minutes of every morning spent skimming HackerNews + KrebsOnSecurity + Bleeping Computer + SANS ISC manually.

## Installation

```bash
# from the repo
cp -r data/sample_skills/vault-cybersec-news-fetcher/ ~/.claude/skills/cybersec-news-fetcher/

# verify
ls ~/.claude/skills/cybersec-news-fetcher/
# expected: SKILL.md, references/, scripts/, assets/, README.md, LICENSE.txt
```

That is the whole install. No virtualenv, no requirements.txt, no Docker.

## Usage

### From Claude Code (natural language)

Type in chat: **fetch cyber news** or **pull infosec headlines last 24h**

Claude Code loads `SKILL.md`, runs `scripts/fetch_feeds.py` with the default source list, then `scripts/dedupe.py`, and writes the result to `~/Desktop/raw_news.json` (or wherever you ask).

### From the command line (direct)

```bash
# 24-hour window, default 10 sources
python ~/.claude/skills/cybersec-news-fetcher/scripts/fetch_feeds.py \
  --sources ~/.claude/skills/cybersec-news-fetcher/assets/templates/cybersec_sources.json \
  --since 24 \
  --output /tmp/raw_news.json

# Dedupe across sources
python ~/.claude/skills/cybersec-news-fetcher/scripts/dedupe.py \
  --input /tmp/raw_news.json \
  --output /tmp/deduped.json

# Weekly digest (7 days)
python ~/.claude/skills/cybersec-news-fetcher/scripts/fetch_feeds.py \
  --sources ~/.claude/skills/cybersec-news-fetcher/assets/templates/cybersec_sources.json \
  --since 168 \
  --output /tmp/weekly_raw.json

# Dev loop — 3 fixture sources, fast
python ~/.claude/skills/cybersec-news-fetcher/scripts/fetch_feeds.py \
  --test \
  --output /tmp/test_raw.json
```

## Customization

### Adding a source

Edit `assets/templates/cybersec_sources.json` and add an entry:

```json
{
  "name": "Recorded Future Blog",
  "url": "https://www.recordedfuture.com/feed",
  "category": "threat-intel",
  "authority_tier": 2
}
```

Authority tier (1-5, 1 highest) determines who wins the tiebreaker when the same story appears in multiple feeds.

### Dropping a source

Same file, delete the entry. The fetcher silently skips missing sources.

### Changing the time window

Pass `--since <hours>`. Defaults to 24. Common values:

- `--since 24`: daily morning briefing
- `--since 168`: weekly digest
- `--since 720`: monthly retrospective

### Adding private/paid feeds

Edit `references/private_sources.md` (create the file if missing). The fetcher does not read this file by default — it's a placeholder for member-maintained credentials. To wire it in, add the source URL and credentials to `cybersec_sources.json` like any public source. If the feed needs auth headers, fork `fetch_feeds.py` and add a `headers` field to the source schema.

## Output shape

```json
{
  "generated_at": "2026-05-27T08:00:00+00:00",
  "window_hours": 24,
  "sources_polled": 10,
  "sources_succeeded": 9,
  "sources_failed": [
    {"name": "ThreatPost", "reason": "HTTP 503"}
  ],
  "items_raw": 142,
  "items_after_time_filter": 38,
  "items_after_dedupe": 31,
  "items": [
    {
      "title": "...",
      "summary": "...",
      "url": "https://...",
      "published_date": "2026-05-27T04:30:00+00:00",
      "source_name": "The Hacker News",
      "raw_age_hours": 3.5
    }
  ]
}
```

The categorizer (Skill 2 in the chain) reads `items[]` plus the metadata above it.

## Troubleshooting

### "No items returned"
- Check `sources_failed` in the output JSON. If all 10 sources failed, you have a network issue, not a Skill issue.
- Try `--test` mode to bypass the source list and hit 3 known-good feeds.

### "KrebsOnSecurity returns HTTP 403"
- Brian's Cloudflare config sometimes blocks default Python user agents. The fetcher already uses a Mozilla UA, but if Cloudflare hardens further, manually swap to the browser UA in `scripts/fetch_feeds.py` (`FALLBACK_UA` constant).

### "Output has duplicates"
- Run `scripts/dedupe.py` on the fetcher output. The fetcher does NOT dedupe by default — that's a separate step.

### "Parse error on Source X"
- The source changed its RSS dialect. Pull the raw XML manually (`curl <url>`) and inspect. If it's malformed, file an issue with the source. If it's a new dialect (e.g., RSS 1.0/RDF), patch `parse_feed_bytes` in `fetch_feeds.py`.

## When this skill matters

Run as Step 1 of the morning briefing chain. The orchestrator (`morning-cybersec-briefing`) calls this Skill, then the categorizer, then the publisher. End result: a clean cybersec briefing page lands on your news page or static HTML file by 8 AM, with zero clicks.

## When this skill does not help

- You're a CISO with a SIEM + paid threat intel platform — those tools already do this better.
- You need OT/ICS-specific signal — extend the source list with Dragos, Nozomi, Claroty feeds.
- You need real-time alerting on a specific CVE — RSS polling once a day is too slow; use a CVE-API tool instead.

## Chain map

```
[ cybersec-news-fetcher ]  ← you are here
        |
        v   raw_news.json (normalized + deduped)
[ cybersec-news-categorizer ]
        |
        v   briefing.md
[ cybersec-news-page-publisher ]
        |
        v   news_page.html (or WordPress post, Notion page, GH Pages)
```

The orchestrator `morning-cybersec-briefing` chains all three.

## See also

- Vault Module G.6 lesson (Capstone — Content-Curation Chain)
- Companion Skills: `cybersec-news-categorizer`, `cybersec-news-page-publisher`, `morning-cybersec-briefing`
- The same architecture (pull → normalize → dedupe → hand off) ports to any RSS domain: finance news, AI research, real estate listings, etc.
