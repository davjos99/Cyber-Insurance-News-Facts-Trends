# Morning Cybersec Briefing (Orchestrator)

The fourth Skill in the chain — the glue that chains the other three. Runs `fetch → dedupe → categorize → validate → publish` in sequence.

Replaces a $9-29/month RSS.app subscription.

## What this chain produces

Every morning at 7:30 AM (or whenever you cron it), a clean cybersec briefing lands in your browser / WordPress / Notion / GitHub Pages. Three sections (Threats / News / Advice), 9-15 items total, every item with a source URL.

## Installation

```bash
# Install all four Skills
cp -r data/sample_skills/vault-cybersec-news-fetcher/    ~/.claude/skills/cybersec-news-fetcher/
cp -r data/sample_skills/vault-news-categorizer/         ~/.claude/skills/cybersec-news-categorizer/
cp -r data/sample_skills/vault-news-page-publisher/      ~/.claude/skills/cybersec-news-page-publisher/
cp -r data/sample_skills/vault-morning-cybersec-briefing/ ~/.claude/skills/morning-cybersec-briefing/

# Verify
ls ~/.claude/skills/
# expected: cybersec-news-fetcher, cybersec-news-categorizer, cybersec-news-page-publisher, morning-cybersec-briefing
```

## First run (default config)

```bash
mkdir -p ~/.cybersec-briefing/runs

# Use the bundled default config
bash ~/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh \
  ~/.claude/skills/morning-cybersec-briefing/assets/templates/chain_config.json
```

The brief lands at `~/.cybersec-briefing/latest.html`. Open it:

```bash
open ~/.cybersec-briefing/latest.html       # macOS
xdg-open ~/.cybersec-briefing/latest.html   # Linux
start ~/.cybersec-briefing/latest.html      # Windows
```

That's the whole chain. ~5-30 seconds depending on feed responsiveness.

## Per-user config

Copy the default to a user-editable location:

```bash
mkdir -p ~/.cybersec-briefing
cp ~/.claude/skills/morning-cybersec-briefing/assets/templates/chain_config.json \
   ~/.cybersec-briefing/chain_config.json
```

Edit `~/.cybersec-briefing/chain_config.json`:

- Change `window_hours` to 168 for a weekly digest
- Add WordPress / Notion / GitHub Pages entries to `publishers[]`
- Tweak `retain_runs_days` if you want a longer archive

Then run:

```bash
bash ~/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh
```

The shell wrapper defaults to `~/.cybersec-briefing/chain_config.json`.

## Automating daily

See `references/cron_setup_local.md` for Mac / Linux / Windows instructions.

Quick version (Mac/Linux cron):

```bash
crontab -e
# Add:
30 7 * * * /usr/bin/env bash ~/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh ~/.cybersec-briefing/chain_config.json >> ~/.cybersec-briefing/cron.log 2>&1
```

Quick version (Windows PowerShell):

```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument '"C:\Users\YOU\.claude\skills\morning-cybersec-briefing\scripts\orchestrate.py" "C:\Users\YOU\.cybersec-briefing\chain_config.json"'
$Trigger = New-ScheduledTaskTrigger -Daily -At 7:30AM
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "CybersecBriefing"
```

## Cloud schedule (GitHub Actions)

See `references/github_actions_workflow.md` for the full `.github/workflows/morning-briefing.yml`.

## What replaces what

| Tool / service | Cost | Replaced by |
|---|---|---|
| RSS.app | $9-29/mo | This Skill chain |
| Inoreader Pro | $7.50/mo | This Skill chain |
| Feedly Pro | $7/mo | This Skill chain |
| Hand-curating a daily Slack post | 20 min/day | This Skill chain |

The chain is free (no API costs, all sources are public RSS) and runs on your own machine or GitHub Actions (also free for public repos).

## Customization

### Change the source list

Edit `~/.claude/skills/cybersec-news-fetcher/assets/templates/cybersec_sources.json`. Add/drop sources, change authority tiers.

### Change the categorization rules

Edit `~/.claude/skills/cybersec-news-categorizer/references/categorization_rules.md` (for LLM-driven categorization) and `~/.claude/skills/cybersec-news-categorizer/scripts/categorize.py` (for headless cron-mode categorization).

### Change the HTML template

Edit `~/.claude/skills/cybersec-news-page-publisher/assets/templates/news_page.html`. Modify CSS variables for colors, add a logo, etc.

### Add a fourth publisher

Drop a `publish_<NAME>.py` script in `~/.claude/skills/cybersec-news-page-publisher/scripts/`. Add an entry to `publishers[]` in your config with `type: "<NAME>"`.

## Output structure

```
~/.cybersec-briefing/
├── chain_config.json
├── latest.html                    ← always overwritten with the freshest briefing
├── runs.log                       ← one-line summary per run
├── runs/
│   ├── 2026-05-27T073012Z/
│   │   ├── raw_news.json
│   │   ├── deduped.json
│   │   └── briefing.md
│   ├── 2026-05-26T073011Z/
│   │   └── ...
│   └── ... (auto-cleaned after retain_runs_days)
```

## Troubleshooting

### "All sources failed"
Check `~/.cybersec-briefing/runs/<latest>/raw_news.json`. The `sources_failed` array names the culprits. If all 10 failed, you have a network issue, not a Skill issue.

### "Brief looks short / empty"
Check `items_after_time_filter` in raw_news.json. If it's < 10, the window is too tight — increase `window_hours` to 48 or 168.

### "Cron job doesn't run on Mac"
Cron on macOS is unreliable (laptop sleep). Use launchd instead. See `references/cron_setup_local.md`.

### "Validation always warns about banned phrases"
The cybersec press loves "critical" and "concerning." The heuristic categorizer strips these automatically. If you're seeing warnings, your custom categorizer is letting them through — re-read `references/banned_phrases.md` in the categorizer skill.

### "WordPress publish fails 401"
Application Password (NOT login password). See `cybersec-news-page-publisher/references/wordpress_recipe.md`.

### "Notion publish fails 404"
Integration not connected to the database. Open the database in Notion → `...` → Add connections → pick the integration.

## When this skill matters

Every morning. The whole chain exists to make the first 30 minutes of your day NOT spent skimming RSS feeds.

## When this skill does not help

- You already have a SIEM + paid threat intel platform → those are richer and more real-time
- You need < 1 hour latency on a specific CVE → RSS polling once a day is too slow
- You want OT/ICS-specific signal → extend the source list with Dragos, Nozomi, Claroty

## See also

- The Adobe Stock chain in Module G.2 — same orchestrator pattern, different domain
- The Newsletter chain in Module G.1 — same architecture, content-creation instead of content-curation
- Vault Module G.6 lesson — full walkthrough of building YOUR version of a content-curation chain
