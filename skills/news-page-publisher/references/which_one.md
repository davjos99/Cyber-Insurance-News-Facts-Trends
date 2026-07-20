# Which Publisher to Pick

Decision tree. Read top to bottom. Stop at the first match.

## Branch 1 — Do you have any credentials set up?

**No:** Use **static HTML**. Zero auth, zero config, works in 30 seconds.

→ Open the resulting `news_page.html` in your browser, or upload it to:
- Netlify drag-and-drop
- GitHub Pages (manual drag)
- Any web host with FTP
- S3 / Cloudflare Pages / Vercel
- Your local filesystem (just open in browser)

## Branch 2 — Are you OK with the brief being PUBLIC?

**No:** Use **Notion** (private workspace) or **static HTML** kept on a private machine.

**Yes:** Continue to Branch 3.

## Branch 3 — Do you already use one of these tools daily?

| Tool you use | Recommended publisher |
|---|---|
| WordPress (any hosting) | **WordPress** |
| Notion (personal or team) | **Notion** |
| Jekyll / Hugo / GitHub Pages site | **GitHub Pages** |
| Obsidian / Logseq | **static HTML** (then sync the .html file into your vault folder) |
| ConvertKit / Beehiiv newsletter | **static HTML** (then paste the rendered content into your newsletter editor) |
| Custom internal wiki | **static HTML** + manual upload |
| Nothing yet | **static HTML** |

## Branch 4 — Multiple destinations?

Run the orchestrator with multiple `publishers` in `chain_config.json`:

```json
{
  "publishers": [
    {"type": "static_html", "destination": "/var/www/html/cybersec.html"},
    {"type": "wordpress", "destination": "https://mysite.com"},
    {"type": "notion", "destination": "abc123def-database-id"}
  ]
}
```

The orchestrator calls each publisher in sequence. If one fails, the others still run — failure of one publisher does not block the others.

## Why static HTML is the default

- **Zero setup:** Works on any computer. No tokens, no API keys, no integrations.
- **No vendor lock-in:** The .html file is yours. Move it anywhere.
- **Searchable archive:** Drop yesterday's .html into a `cybersec_briefings/` folder. Use grep.
- **Offline-friendly:** Read on the train, in a SCIF, on a plane.
- **Portable:** Same .html opens identically on Mac / Windows / Linux / iPhone.

The fancier publishers add nice-to-haves (RSS feed of your archive, comment threads, full-text search) but they cost credentials and ongoing maintenance. Start static. Graduate when you have a real reason.

## Edge cases

### "I want a public RSS feed of my briefings"

Use **WordPress** (auto-generates `/feed/`) or **GitHub Pages with Jekyll** (jekyll-feed plugin).

### "I want my briefings searchable across 6 months"

Use **Notion** (built-in search across the database) or **GitHub Pages with Algolia** (free tier).

### "I want a daily email of the brief"

Out of scope for this Skill. Wire the static HTML publisher to an email-sending Skill (e.g., add a `scripts/email_briefing.py` that takes the rendered HTML and ships it via Mailgun / Postmark / Resend).

### "I want all four publishers in parallel"

Configure the orchestrator's `chain_config.json` with all four. Run time goes from ~2s (static only) to ~8-15s (all four with API calls). Still well under the daily cron budget.

### "I'm scared of credentials"

Stay on static HTML. The chain works just as well. The other publishers are optional, not required.
