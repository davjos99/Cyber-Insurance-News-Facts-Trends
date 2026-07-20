# Cybersec News Page Publisher

The third Skill in the morning cybersec briefing chain. Reads a categorized `briefing.md` and publishes it to one of four destinations:

1. **Static HTML** (default, zero credentials)
2. **WordPress** (REST API + Application Password)
3. **Notion** (API + integration token)
4. **GitHub Pages** (git commit + push)

Python stdlib only.

## What this Skill replaces

The "now I have to copy this brief somewhere I can read it" friction. With this Skill, the brief lands wherever you read things — your browser, your blog, your Notion workspace, your team's Pages site.

## Installation

```bash
cp -r data/sample_skills/vault-news-page-publisher/ ~/.claude/skills/cybersec-news-page-publisher/
ls ~/.claude/skills/cybersec-news-page-publisher/
# expected: SKILL.md, references/, scripts/, assets/, README.md, LICENSE.txt
```

## Usage

### Static HTML (start here)

```bash
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_static_html.py \
  --input /tmp/briefing.md \
  --output /tmp/cybersec_briefing.html

# Open the result
open /tmp/cybersec_briefing.html   # macOS
xdg-open /tmp/cybersec_briefing.html   # Linux
start /tmp/cybersec_briefing.html   # Windows
```

Zero auth. Zero network calls. The HTML file is self-contained — bring it on a flight, drop it on S3, drag it onto Netlify. See `references/static_html_recipe.md`.

### WordPress

```bash
# One-time: configure credentials (see references/wordpress_recipe.md)
cat > ~/.cybersec-briefing/wp-creds.env <<EOF
WP_URL=https://yoursite.com
WP_USER=yourusername
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
EOF
chmod 600 ~/.cybersec-briefing/wp-creds.env

# Each run
set -a; source ~/.cybersec-briefing/wp-creds.env; set +a
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_wordpress.py \
  --input /tmp/briefing.md \
  --status draft \
  --category "Cybersec Briefings"
```

### Notion

```bash
# One-time: configure credentials (see references/notion_recipe.md)
cat > ~/.cybersec-briefing/notion-creds.env <<EOF
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=12345678-1234-1234-1234-123456789012
EOF
chmod 600 ~/.cybersec-briefing/notion-creds.env

# Each run
set -a; source ~/.cybersec-briefing/notion-creds.env; set +a
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_notion.py \
  --input /tmp/briefing.md
```

### GitHub Pages

```bash
# One-time: configure (see references/github_pages_recipe.md)
cat > ~/.cybersec-briefing/gh-pages-config.json <<EOF
{
  "repo_path": "/Users/you/my-blog",
  "flavor": "jekyll",
  "post_dir": "_posts",
  "front_matter": {"layout": "post", "categories": ["cybersec"]},
  "commit_message_template": "Cybersec briefing for {DATE}",
  "auto_push": true
}
EOF

# Each run
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_github_pages.py \
  --input /tmp/briefing.md \
  --config ~/.cybersec-briefing/gh-pages-config.json
```

## Customization

### Pick a publisher

Read `references/which_one.md`. The decision tree leads to one of:

- **No credentials available / not sure** → static HTML
- **Already use WordPress** → WordPress
- **Already use Notion** → Notion
- **Already have a Jekyll/Hugo Pages site** → GitHub Pages

### Customize the HTML template

Edit `assets/templates/news_page.html`. Change colors via the `:root` CSS variables block. Add a logo by base64-embedding it in the `<header>`. See `references/static_html_recipe.md` for examples.

### Publish to multiple destinations in one run

The orchestrator (Skill 4 in the chain) supports multi-publisher chains via `chain_config.json`. Each publisher is called in sequence; failure of one does not block others.

## Troubleshooting

### Static HTML

- **"Looks broken on mobile"** → ensure the `<meta name="viewport">` tag is intact
- **"Links don't render"** → check that the briefing has `[Source: name](url)` Markdown syntax, not raw URLs

### WordPress

- **401 Unauthorized** → wrong application password; regenerate at Users → Profile
- **403 Forbidden** → security plugin blocking REST API; whitelist user agent
- **Category creation fails** → ensure the user has `manage_categories` permission

### Notion

- **404 "Could not find database"** → integration isn't connected to the database; open the DB → `...` menu → Add connections
- **400 validation error** → property name mismatch; use `--property-map`

### GitHub Pages

- **`Permission denied (publickey)`** → SSH key not configured for the remote
- **`! [rejected]`** → someone else pushed; `git pull --rebase` manually

## When this skill matters

Step 3 of the morning briefing chain. The categorizer produces a Markdown brief; this Skill renders it to wherever the member actually reads things. Without this step, the brief lives in `/tmp/` and the member never sees it.

## When this skill does not help

- You read briefings as raw Markdown in your terminal — skip this Skill, the categorizer's output is already final for you
- You want email delivery — wire a separate email-sending Skill into the chain after this one
- You want push notifications — wire a Pushover / ntfy.sh Skill into the chain

## Chain map

```
[ cybersec-news-fetcher ]
        |
        v   raw_news.json
[ cybersec-news-categorizer ]
        |
        v   briefing.md
[ cybersec-news-page-publisher ]  ← you are here
        |
        v   news_page.html (or WordPress post, Notion page, GH Pages commit)
```

## Vendor-API compatibility notes

- **WordPress REST API:** stable since WP 4.7 (2016). Application Passwords ship in WP 5.6+ (2020). Older WP installations need the JWT Authentication plugin instead — out of scope for this Skill.
- **Notion API:** version pinned to `2022-06-28`. Notion releases new versions roughly twice a year; older versions are deprecated after ~2 years. Update `NOTION_VERSION` in `publish_notion.py` if Notion deprecates 2022-06-28.
- **GitHub:** uses `git` CLI directly, so whatever version of git you have works. No HTTPS API dependency.
