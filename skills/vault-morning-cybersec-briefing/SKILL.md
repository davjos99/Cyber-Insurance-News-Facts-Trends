---
name: morning-cybersec-briefing
description: Orchestrator for the three-Skill cybersecurity briefing chain. Runs fetcher → categorizer → publisher in sequence, with error handling between steps. Replaces a $9-29/mo RSS.app subscription. Default publisher is static HTML (zero credentials). Designed to be triggered by cron (Mac/Linux), Task Scheduler (Windows), or GitHub Actions. Trigger when the user says "run the morning cybersec briefing", "build today's cybersec brief", "do the full briefing chain", or "publish the morning brief".
allowed-tools: Read, Bash, Write
---

# Morning Cybersec Briefing (Orchestrator)

The wrapper that chains the three sub-skills into one command. Run this once per day (via cron or a click) and the morning brief lands on your reading surface.

> **Operating principle:** The orchestrator is dumb glue. It calls each Skill in sequence, halts on hard failure, and continues on soft failure (e.g., one of multiple publishers fails — the others still run). All logic lives in the three sub-skills.

## The chain

```
fetcher → dedupe → categorize → validate → publish(es)
```

1. **`scripts/fetch_feeds.py`** (from `cybersec-news-fetcher`) pulls 10 RSS feeds, normalizes, writes `raw_news.json`
2. **`scripts/dedupe.py`** (from `cybersec-news-fetcher`) collapses cross-source duplicates, writes `deduped.json`
3. **`scripts/categorize.py`** (from `cybersec-news-categorizer`) applies the Threats/News/Advice taxonomy, writes `briefing.md`
4. **`scripts/validate_briefing.py`** (from `cybersec-news-categorizer`) sanity-checks the brief
5. **`scripts/publish_<TYPE>.py`** (from `cybersec-news-page-publisher`) renders to the destination(s)

## When to run

- **Daily, automated** — via cron at 7:30 AM your local time, so the brief is ready when you sit down with coffee
- **On-demand** — when you want a fresh brief mid-day (e.g., a major incident just broke)
- **Weekly digest** — set `window_hours: 168` in `chain_config.json` for a Sunday weekly recap

## Inputs

| File | Status | Source | What it provides |
|---|---|---|---|
| `assets/templates/chain_config.json` | required (default ships) | Bundled in this skill | Paths to sub-skills + publisher choice + window |
| Three sub-skills installed | required | `~/.claude/skills/cybersec-news-*` | The actual work |

## Workflow

### Step 1 — Read chain_config.json

```json
{
  "version": "1.0",
  "window_hours": 24,
  "skill_paths": {
    "fetcher": "~/.claude/skills/cybersec-news-fetcher",
    "categorizer": "~/.claude/skills/cybersec-news-categorizer",
    "publisher": "~/.claude/skills/cybersec-news-page-publisher"
  },
  "work_dir": "~/.cybersec-briefing/runs",
  "publishers": [
    {"type": "static_html", "destination": "~/.cybersec-briefing/latest.html"}
  ],
  "halt_on_categorize_validation_fail": false,
  "halt_on_publish_fail": false
}
```

Member edits this to:
- Change the time window (24h daily, 168h weekly)
- Add WordPress / Notion / GitHub Pages publishers
- Change where outputs land

### Step 2 — Create the per-run work directory

`{work_dir}/{YYYY-MM-DD_HHMMSS}/` — every run gets a fresh subfolder. Keep the last 30 days; older runs auto-deleted by a cleanup pass at the end. Members can re-run a publisher against an old briefing.md if they want.

### Step 3 — Run the fetcher

```bash
python {fetcher}/scripts/fetch_feeds.py \
  --sources {fetcher}/assets/templates/cybersec_sources.json \
  --since {window_hours} \
  --output {work_dir}/raw_news.json
```

Hard failure: zero sources succeeded → halt the chain.
Soft failure: some sources failed → continue. Log to the run log.

### Step 4 — Run the dedupe

```bash
python {fetcher}/scripts/dedupe.py \
  --input {work_dir}/raw_news.json \
  --output {work_dir}/deduped.json
```

### Step 5 — Run the categorizer

```bash
python {categorizer}/scripts/categorize.py \
  --input {work_dir}/deduped.json \
  --output {work_dir}/briefing.md
```

### Step 6 — Validate

```bash
python {categorizer}/scripts/validate_briefing.py {work_dir}/briefing.md
```

If validation fails AND `halt_on_categorize_validation_fail: true` → halt.
Otherwise log + continue.

### Step 7 — Run each publisher

For each entry in `publishers[]`:

```bash
python {publisher}/scripts/publish_{type}.py --input {work_dir}/briefing.md --output {destination}
```

Failures: log + continue (unless `halt_on_publish_fail: true`).

### Step 8 — Cleanup

Delete run folders older than 30 days. Write a single-line summary to `{work_dir}/../runs.log`:

```
2026-05-27T08:00:12  OK  fetched=200 deduped=117 kept=15 publishers=[static_html:ok]
```

## What not to do

- Do not chain unrelated work into the orchestrator. The orchestrator's job is to call the 3 sub-skills. If you want email delivery, that's a separate Skill — don't bolt it onto this one.
- Do not bypass the validator silently. If validation fails, surface it. Better to ship a failing brief with a warning than a silent corruption.
- Do not run the chain inside a HTTP request handler. It takes 5-30 seconds depending on feed responsiveness. Use cron / scheduled tasks.
- Do not hardcode paths in the orchestrator. Read everything from `chain_config.json` so the member can move things around.

## Reference files

- `references/cron_setup_local.md` — Mac/Linux cron + Windows Task Scheduler walkthroughs
- `references/github_actions_workflow.md` — `.github/workflows/morning-briefing.yml` for cloud scheduling
- `references/chain_config.md` — full chain_config.json schema with every field documented

## Scripts

- `scripts/orchestrate.sh` — Bash wrapper for Mac/Linux. Reads chain_config.json, runs the chain. Used by cron.
- `scripts/orchestrate.py` — Python alternative, cross-platform. Used by Windows Task Scheduler and GitHub Actions.

Both scripts have the same behavior; pick by platform.

## Assets

- `assets/templates/chain_config.json` — default config. Members copy this to `~/.cybersec-briefing/chain_config.json` and edit.

## License + attribution

Apache 2.0. See `LICENSE.txt`. Original work for Agent Skills Academy Vault Module G.6. The orchestrator pattern (dumb glue chains atomic Skills) is the canonical Vault chain architecture — see also Module G.1 (newsletter chain), G.2 (Adobe Stock chain), G.5 (LinkedIn carousel chain).
