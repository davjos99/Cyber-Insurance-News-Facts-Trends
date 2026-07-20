---
name: cybersec-news-categorizer
description: Turn a deduped raw_news.json into a one-page Markdown briefing organized into three sections — Threats (active CVEs, breaches, ransomware, exploitation in the wild), News (company moves, policy shifts, takedowns, M&A), and Advice (best-practice guides, how-tos, hardening playbooks). Each section gets 3-5 items, each item gets a 1-2 sentence summary with the source URL cited. Drops vendor PR and broad opinion pieces. Trigger when the user says "categorize cyber news", "build the briefing", "make the cybersec brief", or "summarize the news".
allowed-tools: Read, Write
---

# Cybersec News Categorizer

The second link in the morning cybersec briefing chain. Reads the deduped JSON from `cybersec-news-fetcher`, applies a three-bucket taxonomy (Threats / News / Advice), drops low-signal noise, and emits a one-page Markdown briefing the publisher can render to HTML, WordPress, Notion, or GitHub Pages.

> **Operating principle:** A briefing is a *decision aid*, not a feed. Every item earns its slot by helping the reader decide what to do today. If an item doesn't answer "should I patch / read / change behavior?", it does not belong in the brief.

## When to run

Run this as Step 2 of the morning briefing chain. Also run standalone when:

- The fetcher has already pulled fresh data and you want to re-categorize with different filters
- You're testing the briefing template
- You want to bulk-generate weekly digests from a 168h raw_news.json

## Inputs

| File | Status | Source | What it provides |
|---|---|---|---|
| `<deduped.json>` | required | Output of `cybersec-news-fetcher` | The normalized + deduped news items |
| `assets/templates/briefing_template.md` | required (ships in bundle) | This Skill's assets | The Markdown skeleton |
| `assets/fixtures/sample_briefing.md` | optional | Bundled fixture | Example output to seed the LLM's voice |

## Workflow

### Step 1 — Read the deduped JSON

Load `items[]` from the fetcher's output. The metadata block (`generated_at`, `window_hours`, `sources_polled`) gets quoted into the briefing's footer.

### Step 2 — Filter low-signal items

Drop items that match any of these patterns (see `references/relevance_filter.md` for the full list):

- Vendor PR: "X announces partnership with Y", "X named leader in Gartner Magic Quadrant"
- Broad opinion: "5 things every CISO should know about AI" (when not tied to a specific incident)
- Conference promos: "Join us at RSA", "Register for Black Hat"
- Sponsored / "presented by"
- Listicle filler: "Top 10 cybersec tools of 2026"
- Duplicate angle of an item already kept

Be ruthless. A 30-item raw feed should usually filter down to 9-15 brief-worthy items.

### Step 3 — Categorize each surviving item

Three buckets. See `references/categorization_rules.md` for the full ruleset. Quick guide:

- **Threats** = an attacker is doing something *right now* or *this week*. Active exploitation, fresh CVE with PoC, named breach, ransomware leak-site listing, supply-chain compromise. The reader's next action is patch / hunt / contain.
- **News** = the cybersec *world* changed. Company acquisition, policy shift, government takedown, vendor announcement of a security product / feature, executive move. The reader's next action is update their mental model, not their firewall.
- **Advice** = someone published *how to do something better*. Hardening guide, post-mortem with lessons, new defensive technique, configuration recipe. The reader's next action is read + adapt later this week.

If an item doesn't cleanly fit one bucket, default to **News** — the safest holding pen.

### Step 4 — Rank within each bucket

Within Threats: rank by exploitation severity (active > PoC > theoretical) then by reach (number of affected systems).

Within News: rank by impact on the reader's stack (vendor they use > general industry > adjacent industry).

Within Advice: rank by actionability (concrete recipe > principle > opinion).

Keep the top 3-5 per bucket. Drop the rest.

### Step 5 — Summarize each surviving item

Each item gets a 1-2 sentence summary that:

- Names the thing (CVE number, company, vendor, technique)
- States what happened or what's recommended
- Cites the source URL
- Does NOT use adjectives like "critical" or "concerning" — let the numbers speak

See `references/bullet_style_guide.md` for examples.

### Step 6 — Render to the template

Fill `assets/templates/briefing_template.md`. The template is locked — keep the structure stable so the publisher's HTML/WordPress/Notion render is predictable.

```markdown
# Cybersec Briefing — {YYYY-MM-DD}

_Window: last {N} hours · {M} sources polled · {K} items reviewed_

## Threats
- **{Item title}** — {1-2 sentence summary}. [Source: {source_name}]({url})

## News
- **{Item title}** — {1-2 sentence summary}. [Source: {source_name}]({url})

## Advice
- **{Item title}** — {1-2 sentence summary}. [Source: {source_name}]({url})

---
_Generated {timestamp} · {sources_succeeded}/{sources_polled} sources succeeded_
```

### Step 7 — Validate

Run `scripts/validate_briefing.py <output.md>`. The validator checks:

- Three section headers exist (Threats / News / Advice)
- Each section has 3-5 items (or explicit "No material items today")
- Every item has a source URL
- No banned phrases ("critical", "concerning", "groundbreaking", "game-changing")
- Word count fits one screen (≤ 800 words)

If the validator fails, regenerate the briefing with the specific failures fed back as constraints.

## What not to do

- Do not inflate item count to hit the 3-5 minimum. If Threats only has 2 items today, write "No additional threat-grade items in the window" — never pad.
- Do not editorialize. Pragati's voice is "numbers lead, words follow." That ports to cybersec — names + dates + CVE numbers lead, adjectives never.
- Do not include items without a URL. The brief is only useful if the reader can drill in.
- Do not categorize vendor announcements as Advice. A vendor saying "our new product is great" is News at best, dropped at worst.
- Do not run the Skill on un-deduped raw_news.json. Two versions of the same story make the brief look sloppy.

## Reference files

- `references/categorization_rules.md` — the Threats / News / Advice taxonomy with examples and edge cases
- `references/bullet_style_guide.md` — how to write the 1-2 sentence summaries (anti-fluff)
- `references/relevance_filter.md` — what gets dropped before categorization
- `references/banned_phrases.md` — adjectives the validator rejects

## Scripts

- `scripts/validate_briefing.py` — Python 3.10+, stdlib only. Validates a generated briefing.md against the structural and voice rules. Exit 0 = pass, exit 1 = fail (with line-by-line errors).

## Assets

- `assets/templates/briefing_template.md` — the Markdown skeleton
- `assets/fixtures/sample_briefing.md` — a complete example briefing, hand-curated, for testing the publisher and seeding voice

## License + attribution

Apache 2.0. See `LICENSE.txt`. Original work for Agent Skills Academy Vault Module G.6. The Threats/News/Advice taxonomy is a cybersec-specific adaptation of the universal "act now / update mental model / file for later" triage pattern used in editorial newsroom workflows.
