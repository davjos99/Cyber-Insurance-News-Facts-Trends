# GitHub Actions Workflow

Run the cybersec briefing chain on GitHub's infrastructure. No need for your laptop to be on.

## When this is the right pick

- You don't want a laptop / VPS dedicated to running the chain
- You want the briefings committed to a repo as a side effect
- You want the chain to survive your machine being off / asleep / lost
- You're already on GitHub for other reasons

## When this is NOT the right pick

- You want the briefing on a private Notion workspace and don't want secrets in GitHub
- You don't have a GitHub account / don't want one
- You need < 1 minute latency between cron trigger and brief delivery (GH Actions has minutes of queue time on free tier)

## Setup

### 1. Create a new repo (or reuse an existing one)

```bash
mkdir cybersec-briefing-runner
cd cybersec-briefing-runner
git init
git remote add origin git@github.com:YOU/cybersec-briefing-runner.git
```

### 2. Copy the three sub-skills into the repo

```bash
mkdir -p skills
cp -r ~/.claude/skills/cybersec-news-fetcher skills/
cp -r ~/.claude/skills/cybersec-news-categorizer skills/
cp -r ~/.claude/skills/cybersec-news-page-publisher skills/
```

### 3. Create the workflow file

Create `.github/workflows/morning-briefing.yml`:

```yaml
name: Morning Cybersec Briefing

on:
  schedule:
    # 7:30 AM UTC daily — adjust for your timezone
    - cron: "30 7 * * *"
  workflow_dispatch:  # allow manual trigger

permissions:
  contents: write  # for committing the briefing back to the repo

jobs:
  build-briefing:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run the chain
        env:
          # Optional — only set if you're using Notion publisher
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
          # Optional — only set if you're using WordPress publisher
          WP_URL: ${{ secrets.WP_URL }}
          WP_USER: ${{ secrets.WP_USER }}
          WP_APP_PASSWORD: ${{ secrets.WP_APP_PASSWORD }}
        run: |
          mkdir -p output
          python skills/cybersec-news-fetcher/scripts/fetch_feeds.py \
            --sources skills/cybersec-news-fetcher/assets/templates/cybersec_sources.json \
            --since 24 \
            --output output/raw_news.json
          python skills/cybersec-news-fetcher/scripts/dedupe.py \
            --input output/raw_news.json \
            --output output/deduped.json
          python skills/cybersec-news-categorizer/scripts/categorize.py \
            --input output/deduped.json \
            --output output/briefing.md
          python skills/cybersec-news-categorizer/scripts/validate_briefing.py output/briefing.md || true
          python skills/cybersec-news-page-publisher/scripts/publish_static_html.py \
            --input output/briefing.md \
            --output output/index.html

      - name: Commit briefing
        run: |
          git config user.name "Cybersec Briefing Bot"
          git config user.email "bot@users.noreply.github.com"
          DATE=$(date +%Y-%m-%d)
          mkdir -p briefings
          cp output/briefing.md briefings/${DATE}.md
          cp output/index.html briefings/${DATE}.html
          cp output/index.html index.html  # latest at repo root
          git add briefings/ index.html
          git commit -m "Cybersec briefing for ${DATE}" || echo "Nothing to commit"
          git push

      - name: Upload artifact (for download)
        uses: actions/upload-artifact@v4
        with:
          name: briefing-${{ github.run_number }}
          path: output/
```

### 4. Configure secrets (only if using non-static publishers)

Repo settings → Secrets and variables → Actions → **New repository secret**

Set the secrets your `publishers` array references. For Notion:

- `NOTION_TOKEN` = `secret_xxxxxxxx`
- `NOTION_DATABASE_ID` = `12345678-1234-1234-1234-...`

For WordPress:

- `WP_URL` = `https://yoursite.com`
- `WP_USER` = `username`
- `WP_APP_PASSWORD` = `xxxx xxxx xxxx xxxx xxxx xxxx`

### 5. Enable GitHub Pages

Repo settings → Pages → Source: **Deploy from a branch** → Branch: `main`, folder: `/ (root)` → Save.

Your latest briefing now lives at: `https://YOU.github.io/cybersec-briefing-runner/`

### 6. Trigger the first run manually

Repo → Actions tab → "Morning Cybersec Briefing" → **Run workflow**. Verify it completes successfully before relying on the schedule.

## Cost

- **Public repo:** FREE — GitHub Actions is unlimited for public repos
- **Private repo:** 2,000 minutes/month free; the chain takes ~30 seconds per run = 60 runs per minute of quota → effectively free

## Timezone

GitHub Actions cron uses **UTC**. Adjust:

| Your TZ | UTC cron for 7:30 AM your TZ |
|---|---|
| US East (EDT, UTC-4) | `30 11 * * *` |
| US East (EST, UTC-5) | `30 12 * * *` |
| US Pacific (PDT, UTC-7) | `30 14 * * *` |
| US Pacific (PST, UTC-8) | `30 15 * * *` |
| London (BST, UTC+1) | `30 6 * * *` |
| Berlin (CEST, UTC+2) | `30 5 * * *` |
| Mumbai (IST, UTC+5:30) | `0 2 * * *` |
| Sydney (AEST, UTC+10) | `30 21 * * *` (previous day) |

Note: GitHub Actions does NOT honor DST. Your cron drifts by an hour twice a year. The Skill schedules a daily run; the exact minute doesn't matter much.

## Latency caveat

GitHub Actions free tier queues jobs. A `30 7 * * *` cron may actually start anywhere between 7:30 and 8:15 AM UTC. If you need < 5 min latency, run the chain on your own machine.

## Security

- Repository secrets are encrypted at rest. They appear as `***` in logs.
- The workflow has `contents: write` to commit briefings. It does NOT have any other permissions.
- The bundled publishers all use HTTPS. No credentials traverse plaintext.

## Customizing

### Multiple publishers

Add more publisher steps to the `Run the chain` block:

```yaml
python skills/cybersec-news-page-publisher/scripts/publish_notion.py \
  --input output/briefing.md
python skills/cybersec-news-page-publisher/scripts/publish_wordpress.py \
  --input output/briefing.md \
  --output $WP_URL \
  --status publish
```

### Different window

For a weekly digest (run Sundays at 8 AM UTC):

```yaml
on:
  schedule:
    - cron: "0 8 * * 0"
```

And pass `--since 168`.

### Notify on failure

Add a failure-notification step:

```yaml
      - name: Notify Slack on failure
        if: failure()
        uses: slackapi/slack-github-action@v1.25.0
        with:
          payload: '{"text":"Cybersec briefing chain failed: ${{ github.run_id }}"}'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## Troubleshooting

### "Workflow runs but no briefing committed"

- Check the run log in the Actions tab. Look for the `Commit briefing` step output.
- If you see "Nothing to commit," the brief is identical to a previous one (possible if cron fires twice within the same day) — that's harmless.

### "All sources failed"

- GitHub's egress IPs are sometimes blocked by Cloudflare-protected sources. Add to the workflow:
  ```yaml
  - name: Wait randomly before fetch
    run: sleep $((RANDOM % 60))
  ```
  This spreads concurrent jobs across the global Actions fleet.

### "I want to test the workflow before committing"

- Run it locally first (per the cron setup guide).
- Then push to a feature branch with `workflow_dispatch` only (no schedule) to test on GitHub.
- Then merge to main with the schedule enabled.
