# Cybersec News Categorizer

The second Skill in the morning cybersec briefing chain. Reads the deduped JSON from `cybersec-news-fetcher`, sorts items into Threats / News / Advice, drops vendor PR and broad opinion pieces, and emits a one-page Markdown briefing.

Python stdlib only. No `pip install`.

## What this Skill does

Turns 30 raw RSS items into a 9-15 item three-bucket briefing in 200ms. The buckets:

- **Threats** — "Patch / hunt / contain today" (active CVEs, breaches, ransomware, supply-chain compromise)
- **News** — "Update mental model, not firewall" (takedowns, regulations, M&A, vendor announcements)
- **Advice** — "Read later this week" (hardening guides, detection rules, configuration recipes)

## Installation

```bash
cp -r data/sample_skills/vault-news-categorizer/ ~/.claude/skills/cybersec-news-categorizer/
ls ~/.claude/skills/cybersec-news-categorizer/
# expected: SKILL.md, references/, scripts/, assets/, README.md, LICENSE.txt
```

## Usage

### From Claude Code (LLM-driven)

After the fetcher has written `deduped.json`, type in chat: **categorize the cyber news** or **build the briefing**.

Claude Code reads SKILL.md, loads the deduped items, applies the three-bucket taxonomy from `references/categorization_rules.md`, writes summaries per `references/bullet_style_guide.md`, and renders to the template.

### From the command line (deterministic fallback)

Use this when running headless (cron, GitHub Actions):

```bash
# Run the heuristic categorizer
python ~/.claude/skills/cybersec-news-categorizer/scripts/categorize.py \
  --input /tmp/deduped.json \
  --output /tmp/briefing.md

# Validate
python ~/.claude/skills/cybersec-news-categorizer/scripts/validate_briefing.py /tmp/briefing.md
```

The heuristic categorizer pattern-matches on the same signals the LLM uses (CVE numbers, "patched", "ransomware", "released", "guide", "how to") and is conservative — items without a strong signal default to News rather than being dropped.

The LLM-driven path produces better summaries (it can paraphrase, not just truncate). Use the heuristic path when no LLM is in the loop.

## Customization

### Tighten the relevance filter

Edit `references/relevance_filter.md` to add patterns the briefer should drop. For the heuristic categorizer (`scripts/categorize.py`), edit `DROP_PATTERNS` at the top of the file.

### Loosen the banned phrases

Edit `references/banned_phrases.md` and the `BANNED_PHRASES` list in `scripts/validate_briefing.py`. Keep them in sync.

### Change the template

Edit `assets/templates/briefing_template.md`. The variables are wrapped in `{CURLY_BRACES}` — see the file for the full list.

### Add a fourth bucket

If you want a separate "Research" bucket for academic disclosures:

1. Add a section header in `assets/templates/briefing_template.md`
2. Add the bucket to `REQUIRED_SECTIONS` in `scripts/validate_briefing.py`
3. Add a `RESEARCH_PATTERNS` list to `scripts/categorize.py` and update `categorize_item()`

## Output shape

```markdown
# Cybersec Briefing — 2026-05-27

_Window: last 24 hours · 10 sources polled · 31 items reviewed · 11 kept_

## Threats
- **CVE-2026-1234 in Apache HTTP Server** — ... [Source: The Hacker News](https://...)
- ...

## News
- **FBI seizes StealC info-stealer infrastructure** — ... [Source: KrebsOnSecurity](https://...)
- ...

## Advice
- **Hardening Kubernetes against supply-chain attacks** — ... [Source: SANS ISC](https://...)
- ...

---
_Generated 2026-05-27T08:00:00 UTC · 10/10 sources succeeded_
```

## Troubleshooting

### "Validation fails on the briefing"
Run `python scripts/validate_briefing.py /tmp/briefing.md` and read the X-marked errors. Common fixes:
- Missing section header → ensure the template has all three (Threats/News/Advice)
- Item missing source URL → check the rendering step kept the `[Source:](url)` format
- Banned phrase → strip "critical", "concerning", etc., or pair with a number

### "Heuristic categorizer puts everything in News"
That's the safe default. If items deserve Threats, they need a CVE / breach / ransomware signal in the title or summary. Tighten the fetcher's summary capture if summaries are coming back empty.

### "Briefing too long"
Tighten the cap from 5 to 3 in `scripts/categorize.py`:`rank_within_bucket(...)[:3]`. Or sharpen the relevance filter.

### "Schneier items look weird in News"
Schneier on Security publishes short link-roundups. They survive the filter but contain mostly the linked article's headline. If you find this noisy, drop authority_tier 1 sources from News (keep them for Threats/Advice) by adding a filter in `categorize.py`.

## When this skill matters

Step 2 of the morning briefing chain. Without categorization, the reader gets a wall of 100 RSS items and gives up. With categorization, they get a 9-15 item scannable brief and read every word.

## When this skill does not help

- You already have a categorized feed (Mandiant Advantage, Recorded Future) — those are richer and you don't need this layer
- You want to publish raw RSS without editorial — skip this Skill and pipe the fetcher output straight to the publisher

## Chain map

```
[ cybersec-news-fetcher ]
        |
        v   raw_news.json
[ cybersec-news-categorizer ]  ← you are here
        |
        v   briefing.md
[ cybersec-news-page-publisher ]
        |
        v   news_page.html (or WordPress, Notion, GH Pages)
```
