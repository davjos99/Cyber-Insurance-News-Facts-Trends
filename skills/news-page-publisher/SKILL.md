---
name: cybersec-news-page-publisher
description: Render a categorized briefing.md to a publishable news page on the member's chosen stack — static HTML (default, no credentials needed), WordPress REST API, Notion API, or GitHub Pages. Picks the publisher based on the member's environment using a decision tree in references/which_one.md. Trigger when the user says "publish the briefing", "put the brief on the news page", "render the cybersec brief", "ship the briefing to WordPress / Notion / GitHub Pages".
allowed-tools: Read, Write, Bash
---

# Cybersec News Page Publisher

The third link in the morning cybersec briefing chain. Reads a categorized `briefing.md` from `cybersec-news-categorizer` and publishes it to the member's chosen stack.

> **Operating principle:** The credential-free path is the default. Static HTML works on any computer with zero setup. WordPress / Notion / GitHub Pages are advanced paths that require the member to set up auth — those Skills exist for members who already use those stacks, not as the first step.

## When to run

Run this as Step 3 of the morning briefing chain. Also run standalone when:

- The briefing has already been written and the member wants to re-render with a different publisher
- Testing a new publisher recipe (WordPress → Notion migration, e.g.)
- Rendering an archive — taking a 30-day folder of briefing.md files and producing a static HTML index

## Inputs

| File | Status | Source | What it provides |
|---|---|---|---|
| `<briefing.md>` | required | Output of `cybersec-news-categorizer` | The categorized brief |
| Publisher choice | required | CLI flag or member preference in chain_config.json | Which stack to publish to |
| Auth credentials | conditional | Env vars or member config | Only needed for WordPress / Notion / GitHub Pages |

## The four publishers

The Skill ships four publishers. Pick by member stack — see `references/which_one.md` for the decision tree.

### 1. Static HTML (default, no credentials)

**Use when:** Member has any computer and any way to serve a static file (local Apache, Caddy, GitHub Pages without git automation, scp to a server, S3, Cloudflare Pages, Netlify drag-and-drop, or even just opening the HTML in a browser).

**Script:** `scripts/publish_static_html.py`

**Output:** A standalone HTML file with embedded CSS — no external dependencies, opens cleanly in any browser. Uses the template at `assets/templates/news_page.html`.

**Auth:** None.

### 2. GitHub Pages

**Use when:** Member already has a GitHub Pages site (jekyll or plain HTML), wants git history of every briefing, and is OK with the brief being public.

**Script:** `scripts/publish_github_pages.py`

**Output:** Writes the HTML (or Markdown for jekyll-style sites) to a configured local repo path, runs `git add / commit / push`.

**Auth:** SSH key configured for the GitHub remote, OR a personal access token in `~/.gitconfig`. The Skill does NOT handle auth setup — assumes git already works.

### 3. WordPress (self-hosted or .com Business+)

**Use when:** Member runs a WordPress site and wants the briefing as a daily post.

**Script:** `scripts/publish_wordpress.py`

**Output:** POST to the WP REST API, creates a new post in 'draft' or 'publish' status per member preference.

**Auth:** WordPress URL + username + application password (NOT the WP login password). See `references/wordpress_recipe.md` for setup.

### 4. Notion

**Use when:** Member uses Notion as a personal knowledge base / team workspace and wants the briefing in a Notion database.

**Script:** `scripts/publish_notion.py`

**Output:** Notion API call creating a new page in a configured database, with the brief as the page body and metadata (date, sources count, items count) as database properties.

**Auth:** Notion integration token + database ID. See `references/notion_recipe.md` for setup.

## Workflow

### Step 1 — Read the briefing

Load `briefing.md`. Parse the metadata line (`_Window: last N hours · M sources polled · K items kept_`) and the three section headers.

### Step 2 — Choose a publisher

If invoked through Claude Code, ask the member once (and cache the answer in `~/.cybersec-briefing/publisher.txt`):

> "Where should I publish the brief? Options: (1) static HTML local file, (2) WordPress, (3) Notion, (4) GitHub Pages. Type 1-4."

If invoked through the orchestrator with a `chain_config.json`, read the `publisher` field there.

If no preference exists, default to **static HTML** — the credential-free path.

### Step 3 — Run the chosen publisher

Each publisher script has the same interface:

```bash
python scripts/publish_<NAME>.py --input briefing.md --output <destination>
```

The output destination format varies:
- static_html: `--output /path/to/news_page.html`
- github_pages: `--output <local_repo_path>` (the script handles the post filename)
- wordpress: `--output <wp_url>` (the post is created via API, the URL is just for logging)
- notion: `--output <database_id>` (page is created via API in that DB)

### Step 4 — Verify the publish

After each publisher runs, check:

- **static_html:** file exists, is > 1 KB, opens cleanly in `xdg-open` / `open` / `start`
- **github_pages:** `git log -1` shows the new commit, `git push` reported no errors
- **wordpress:** REST API response is 200/201 with a post ID returned
- **notion:** API response is 200 with a page object returned

If verification fails, log it and exit non-zero. The orchestrator catches this and emails / logs the failure.

## What not to do

- Do not default to WordPress / Notion / GitHub Pages. The credential-free static HTML path is the default. Members who want fancier publishers opt in explicitly.
- Do not hardcode credentials in the Skill. All auth comes from env vars or a member-maintained config file.
- Do not retry forever on API failures. One retry, then exit non-zero. The orchestrator logs the failure.
- Do not modify the briefing.md content. The publisher's job is to RENDER, not to edit. If the brief has issues, that's the categorizer's job.
- Do not publish to multiple destinations in one call. If the member wants static HTML + WordPress, the orchestrator runs the publisher twice.

## Reference files

- `references/which_one.md` — decision tree for picking a publisher
- `references/wordpress_recipe.md` — WordPress REST API setup (app passwords, post format, draft vs publish)
- `references/github_pages_recipe.md` — GitHub Pages flow (jekyll vs plain HTML, git automation)
- `references/notion_recipe.md` — Notion API setup (integration token, database schema)
- `references/static_html_recipe.md` — static HTML deployment options (S3, Netlify, local file)

## Scripts

- `scripts/publish_static_html.py` — Python stdlib only. Renders briefing.md → HTML using the embedded template. NO auth.
- `scripts/publish_github_pages.py` — Python stdlib only. Writes HTML/MD to a local repo, runs git via subprocess.
- `scripts/publish_wordpress.py` — Python stdlib only. POST to WP REST API with Basic Auth (application password).
- `scripts/publish_notion.py` — Python stdlib only. POST to Notion API with Bearer token.

All four use `urllib.request` for HTTP — no `requests` dependency. Same constraint as the rest of the chain.

## Assets

- `assets/templates/news_page.html` — clean HTML template with embedded CSS, dark+light mode toggle, mobile responsive

## License + attribution

Apache 2.0. See `LICENSE.txt`. Original work for Agent Skills Academy Vault Module G.6. The multi-publisher pattern (one Skill, multiple backends) is a common Vault architecture — see also `vault-monday-brief` (which has WordPress + Notion + email backends in its planned roadmap).
