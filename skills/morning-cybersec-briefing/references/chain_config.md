# chain_config.json — Full Schema

The single configuration file for the orchestrator. Members copy `assets/templates/chain_config.json` to `~/.cybersec-briefing/chain_config.json` and edit.

## Full example with every field

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
  "fetcher": {
    "sources_file": "~/.claude/skills/cybersec-news-fetcher/assets/templates/cybersec_sources.json"
  },
  "categorizer": {
    "template": "~/.claude/skills/cybersec-news-categorizer/assets/templates/briefing_template.md"
  },
  "publishers": [
    {
      "type": "static_html",
      "destination": "~/.cybersec-briefing/latest.html",
      "extra_args": []
    },
    {
      "type": "wordpress",
      "destination": "$WP_URL",
      "extra_args": ["--status", "draft", "--category", "Cybersec Briefings"],
      "env_file": "~/.cybersec-briefing/wp-creds.env"
    },
    {
      "type": "notion",
      "destination": "$NOTION_DATABASE_ID",
      "extra_args": [],
      "env_file": "~/.cybersec-briefing/notion-creds.env"
    },
    {
      "type": "github_pages",
      "destination": "~/.cybersec-briefing/gh-pages-config.json",
      "extra_args": []
    }
  ],
  "halt_on_zero_sources": true,
  "halt_on_categorize_validation_fail": false,
  "halt_on_publish_fail": false,
  "retain_runs_days": 30,
  "log_file": "~/.cybersec-briefing/runs.log"
}
```

## Field reference

### `version`
Schema version. Currently `"1.0"`. The orchestrator reads this and refuses to run on unknown versions.

### `window_hours`
The time window for the fetcher. Defaults to 24 (daily briefing). Common values:
- `24` — daily morning briefing
- `168` — weekly Sunday digest
- `720` — monthly retrospective

### `skill_paths`
Paths to the three sub-skill installations. Defaults assume `~/.claude/skills/` — change if your skills live elsewhere. Tilde expansion is honored.

### `work_dir`
Where per-run output folders are created. Each run gets `{work_dir}/{YYYY-MM-DD_HHMMSS}/`. The orchestrator auto-cleans folders older than `retain_runs_days`.

### `fetcher.sources_file`
Path to the sources JSON. Defaults to the bundled 10-source list inside the fetcher skill. Override to point at a member-maintained extended source list.

### `categorizer.template`
Path to the briefing template. Defaults to the bundled template. Override to ship custom branding (different sections, different header, etc.).

### `publishers`
An **array** — multiple publishers can run per chain invocation. Each entry has:

- `type` — one of `static_html`, `wordpress`, `notion`, `github_pages`
- `destination` — the publisher-specific destination (file path / WP URL / DB ID / config path). Env-var substitution (`$VAR`) is supported.
- `extra_args` — additional CLI args passed to the publisher script
- `env_file` — optional path to a `.env` file the orchestrator sources before running this publisher

If multiple publishers are listed, they run in sequence. If one fails, the others continue (unless `halt_on_publish_fail: true`).

### `halt_on_zero_sources` (default: `true`)
If the fetcher reports zero successful sources, halt the chain. Set to `false` for environments where occasional network outages are expected.

### `halt_on_categorize_validation_fail` (default: `false`)
If `validate_briefing.py` exits non-zero, halt the chain. Default is `false` because validation warnings shouldn't block publishing — better to ship a flagged brief than nothing.

### `halt_on_publish_fail` (default: `false`)
If a publisher fails, halt subsequent publishers. Default is `false` — failure of WordPress shouldn't block Notion.

### `retain_runs_days` (default: `30`)
How long to keep run folders before auto-cleaning. Set higher (90, 365) if you want a longer archive of briefings. Set to `0` to keep forever.

### `log_file`
Single-line summary log. One line per run with timestamp + outcome.

## Minimal config (just static HTML)

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
  ]
}
```

## Common patterns

### Daily + weekly

Run the chain twice with different configs:

```bash
# Daily, 7:30 AM
python orchestrate.py --config ~/.cybersec-briefing/daily-config.json

# Weekly, Sunday 8 AM
python orchestrate.py --config ~/.cybersec-briefing/weekly-config.json
```

`weekly-config.json` has `window_hours: 168` and a different `destination` (e.g., a separate Notion DB for weekly digests).

### Test mode (no real publish)

```json
{
  "version": "1.0",
  "window_hours": 24,
  "skill_paths": {...},
  "work_dir": "/tmp/cybersec-test",
  "publishers": [
    {"type": "static_html", "destination": "/tmp/cybersec-test/test.html"}
  ]
}
```

Point everything at `/tmp/`. Run the chain, inspect outputs, delete the folder. Useful when debugging a feed parser change.

### Multi-tenant (multiple readers)

Each reader has their own config + work_dir. The orchestrator is invoked per reader:

```bash
for reader in alice bob carol; do
  python orchestrate.py --config ~/cybersec-tenants/${reader}/chain_config.json
done
```

Each gets their own briefing with their own publishers configured.
