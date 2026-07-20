# WordPress Recipe

Publish the daily cybersec briefing as a WordPress post via REST API.

## Prerequisites

1. **WordPress 5.6+** (any host: WP.com Business+, WP Engine, self-hosted, Bluehost, etc.)
2. **REST API enabled** — true by default on all modern WP; if you disabled it via a plugin, re-enable
3. **An application password** — NOT your login password. See "Setup" below.

## Setup (one-time)

### Create an application password

1. Log into your WordPress admin
2. Navigate to **Users → Profile**
3. Scroll to **Application Passwords**
4. Enter a name (e.g., "Cybersec Briefing Skill")
5. Click **Add New Application Password**
6. WordPress generates a 24-character password like `xxxx xxxx xxxx xxxx xxxx xxxx` — **copy it now**, you cannot see it again
7. Note your WordPress username

### Store credentials safely

Add to `~/.cybersec-briefing/wp-creds.env` (the Skill reads this file, NOT committed to git):

```bash
WP_URL=https://yourdomain.com
WP_USER=your_username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

Chmod the file to 600:

```bash
chmod 600 ~/.cybersec-briefing/wp-creds.env
```

## Usage

```bash
# Load creds (or set them in your shell rc)
set -a; source ~/.cybersec-briefing/wp-creds.env; set +a

python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_wordpress.py \
  --input /tmp/briefing.md \
  --output "$WP_URL" \
  --status draft
```

Flags:

- `--status draft` — saved as draft for review
- `--status publish` — published immediately (use after you trust the categorizer)
- `--category "Cybersec Briefings"` — category slug (must exist in WP)
- `--tags "cybersec,daily-brief"` — comma-separated tags

## What gets posted

- **Title:** "Cybersec Briefing — 2026-05-27"
- **Content:** Briefing converted from Markdown to HTML
- **Excerpt:** First 160 chars of the Threats section
- **Format:** Standard post (not aside / link / quote)
- **Status:** draft or publish per --status flag

## API endpoint

```
POST {WP_URL}/wp-json/wp/v2/posts
Authorization: Basic <base64(user:app_password)>
Content-Type: application/json

{
  "title": "Cybersec Briefing — 2026-05-27",
  "content": "<rendered HTML>",
  "status": "draft",
  "excerpt": "<first 160 chars of Threats>",
  "categories": [<numeric_id_of_Cybersec_Briefings_category>]
}
```

If the category doesn't exist, the Skill creates it via the `/wp-json/wp/v2/categories` endpoint (one-time).

## Common errors

### `401 Unauthorized`
- App password typed wrong or expired
- Username is the WordPress LOGIN name, not the display name
- Application Passwords feature disabled in WP (check via Users → Profile)

### `403 Forbidden`
- The user doesn't have post-create permission. Check their role — needs Author or higher.
- A security plugin (Wordfence, Sucuri) is blocking REST API for non-admin endpoints. Whitelist the user agent `ClaudeSkillFetcher/1.0`.

### `404 Not Found`
- WP_URL has a trailing slash that's confusing the router. Try with and without.
- REST API disabled at the plugin level. Re-enable.

### `400 Bad Request — invalid post status`
- Category slug doesn't exist. Either create it manually in WP first, or let the Skill create it via the API.

## Security notes

- Application passwords have FULL site permission. Treat them like login passwords. Don't commit `wp-creds.env` to git. Don't paste it into chat. Rotate every 90 days.
- The Skill uses HTTPS only. It will refuse `http://` URLs unless `--allow-http` is passed.
- Basic Auth over HTTPS is the standard WP REST API auth method. JWT auth requires a plugin (e.g., JWT Authentication) — out of scope for this Skill.

## Editing/deleting old briefings

The Skill creates new posts. It does NOT update or delete existing ones. If yesterday's briefing has a typo, fix it directly in WordPress admin.

## Self-hosted gotchas

If you self-host:
- Ensure your `wp-config.php` doesn't have `define('WP_DEBUG', true)` enabled — debug output breaks JSON responses
- If you use a CDN (Cloudflare), allow the POST request through (Cloudflare's default WAF sometimes flags REST API calls)
- Set `WORDPRESS_DB_COLLATE` to `utf8mb4_unicode_ci` for the post content to handle non-ASCII characters (CVE-XXXX is fine, but emoji or unusual quotes can corrupt)
