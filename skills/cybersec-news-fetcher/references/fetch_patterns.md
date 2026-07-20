# HTTP Fetch Patterns — Cybersec Feed Edition

The cybersec corner of the web is more hostile to scrapers than the average RSS source. KrebsOnSecurity sits behind Cloudflare. ThreatPost goes down for hours at a time. Bleeping Computer rate-limits aggressively. This file documents the patterns the fetcher uses to survive that.

## User-Agent

**Never use Python's default User-Agent.** Default is `Python-urllib/3.x` and Cloudflare blocks it on sight.

The Skill uses:

```
Mozilla/5.0 (compatible; ClaudeSkillFetcher/1.0; +https://anthropic.com)
```

Why:
- `Mozilla/5.0` prefix is the universal compatibility tax — looks browser-like enough to skip the lazy blocker tier
- `compatible; ClaudeSkillFetcher/1.0` is honest — identifies the bot for sources that log user agents
- `+https://anthropic.com` is the reverse-lookup hint — well-behaved bots include a URL where the source can complain or block politely

If a source still blocks (KrebsOnSecurity has done this), switch to a pure-browser UA:

```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

That's less honest but unblockable. Use it as the fallback only.

## Timeout

15 seconds per feed. Tuning:

- 5s is too tight — SANS ISC occasionally takes 6-8s on first hit
- 30s is too loose — a hanging Bleeping Computer request blocks the whole chain
- 15s is the sweet spot — covers slow-but-alive sources, kills truly hung ones

The Skill uses `urllib.request.urlopen(req, timeout=15)`.

## Retry strategy

One retry on transient errors. NOT on 4xx (the source is telling you "don't"). The transient codes:

- `5xx` — server's fault
- `socket.timeout` — network's fault, often clears on retry
- `urllib.error.URLError` with DNS failure — also often clears

The Skill:

1. First attempt
2. If transient → sleep 2s → retry once
3. If still failing → log, skip, continue

NO exponential backoff. NO retry-after parsing. NO retry storm. The whole chain has a ~60s budget; retries don't get to eat all of it.

## Rate limiting

The Skill polls each feed **exactly once per run**. There's no need for sophisticated rate limiting because:

- A morning briefing runs once per day per member
- Even 10 members all running the chain at 8 AM hits each feed 10 times total — well under any reasonable RSS limit

If you're running the chain in a multi-tenant SaaS, that math changes. Add a `--delay <seconds>` flag and sleep between feeds. Default is no delay.

## RSS vs Atom

Cybersec feeds split roughly 60/40 between RSS 2.0 and Atom 1.0. The Skill parser handles both via `xml.etree.ElementTree`:

- **RSS 2.0:** `<channel>` → `<item>` with `<title>`, `<link>`, `<description>`, `<pubDate>`
- **Atom 1.0:** `<feed>` → `<entry>` with `<title>`, `<link href="...">`, `<summary>` or `<content>`, `<published>` or `<updated>`

Schneier on Security is Atom. The Hacker News (Feedburner) is RSS 2.0. The parser auto-detects from the root element name.

## Date parsing

RSS dates are a nightmare. The Skill handles four formats:

1. RFC 822 (`Tue, 27 May 2026 14:32:00 +0000`) — most RSS 2.0 feeds
2. ISO 8601 (`2026-05-27T14:32:00Z`) — most Atom feeds
3. RFC 822 with named timezone (`Tue, 27 May 2026 14:32:00 GMT`) — older feeds
4. ISO 8601 with offset (`2026-05-27T14:32:00+00:00`) — newer Atom

If parsing fails, the Skill uses the fetch time as the published_date and tags `published_date_fallback: true` in the JSON so the categorizer can be skeptical.

## HTML-stripping the summary

RSS summaries are full HTML. The Skill strips with a simple regex:

```python
re.sub(r'<[^>]+>', '', summary)
```

That's not robust against malformed HTML but it's good enough for headline-grade summaries. Truncate to 500 chars and move on — the categorizer doesn't need more.

## What NOT to do

- Do NOT add `feedparser`. It's the de-facto Python RSS library but it's an external dep, and members run this Skill without `pip install`.
- Do NOT add `requests`. Same reason — `urllib` works fine for one request per source.
- Do NOT bypass the time-window filter at fetch time. The fetcher's job is to PULL; filtering is a separate step. (Yes, it's wasteful to pull a 200-item feed when 180 are too old, but the alternative is per-source pagination logic that breaks every time a source tweaks its feed. Stay simple.)
- Do NOT cache between runs. Each run is fresh. Members who want caching can wrap the Skill in their own script.

## Debug mode

`--test` flag uses 3 fixture sources (Hacker News + Krebs + Bleeping) and writes verbose logs to stderr. Use this when:

- Adding a new source — verify the parser handles its feed shape
- Debugging "why did the chain return 0 items today"
- Recording demo footage for the Vault module
