# Static HTML Recipe

The credential-free, default publisher. Renders the briefing to a standalone HTML file that opens in any browser.

## What it does

Reads `briefing.md`, parses the three sections (Threats / News / Advice), and renders to `assets/templates/news_page.html`. The HTML:

- Embeds all CSS inline — no external stylesheet, no CDN dependency
- Embeds JavaScript for the dark/light mode toggle inline
- Is mobile-responsive (single-column on phones, multi-column on desktop)
- Has zero external network dependencies — works on a flight

## Usage

```bash
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_static_html.py \
  --input /tmp/briefing.md \
  --output /tmp/cybersec_briefing.html
```

That is it. Open the resulting HTML in a browser:

- macOS: `open /tmp/cybersec_briefing.html`
- Linux: `xdg-open /tmp/cybersec_briefing.html`
- Windows: `start /tmp/cybersec_briefing.html` (or double-click in Explorer)

## Where to put it

### Option A — local file (simplest)

Open the file in your browser daily. Bookmark `file:///path/to/cybersec_briefing.html`. Done.

### Option B — local web server

If you already run a Caddy / nginx / Apache locally:

```bash
# Caddy example — serve a folder
caddy file-server --listen :8080 --root ~/cybersec_briefings
```

Open `http://localhost:8080/cybersec_briefing.html` daily. The orchestrator can write directly into `~/cybersec_briefings/` and you visit the URL.

### Option C — S3 + CloudFront

```bash
aws s3 cp /tmp/cybersec_briefing.html s3://my-bucket/cybersec.html --acl public-read
# CloudFront invalidation if needed:
aws cloudfront create-invalidation --distribution-id E123 --paths /cybersec.html
```

### Option D — Netlify drag-and-drop

1. Go to https://app.netlify.com/drop
2. Drag the `cybersec_briefing.html` onto the page
3. Get a permanent URL like `https://cybersec-briefing-12345.netlify.app`

The Skill does NOT automate this — it's a manual upload — but it's the simplest path to a real URL without any account/credential work.

### Option E — Cloudflare Pages

If you have a `wrangler` CLI authenticated:

```bash
wrangler pages publish /tmp/ --project-name cybersec-briefing
```

### Option F — Vercel

```bash
vercel deploy /tmp/cybersec_briefing.html
```

### Option G — GitHub Pages (manual)

Drop the HTML into a `gh-pages` branch or `docs/` folder of any repo with Pages enabled. (For automated git-based publishing, use the GitHub Pages publisher instead — separate Skill.)

## The HTML template

Lives at `assets/templates/news_page.html`. Variables:

- `{TITLE}` — page title (defaults to "Cybersec Briefing — YYYY-MM-DD")
- `{GENERATED_AT}` — ISO timestamp
- `{WINDOW_HOURS}` — fetch window
- `{SOURCES_POLLED}` — count
- `{ITEMS_KEPT}` — total items after categorization
- `{THREATS_HTML}` — rendered Threats section
- `{NEWS_HTML}` — rendered News section
- `{ADVICE_HTML}` — rendered Advice section
- `{FOOTER_NOTE}` — failed sources note (or empty)

To customize the template:

1. Copy `assets/templates/news_page.html` to your own location
2. Edit the CSS / structure / branding
3. Pass `--template /path/to/your_template.html` to the publisher

## Customization examples

### Brand it with your company colors

Open `news_page.html`, find the `:root` CSS variables block, change:

```css
--accent-cyan: #5adcf0;   /* change to your brand color */
--accent-yellow: #ffd54f;
--bg-dark: #0c0c0e;
```

### Add a logo

Insert into the `<header>` block:

```html
<img src="data:image/png;base64,iVBOR..." alt="Logo" class="logo">
```

Base64-embed the logo to keep the page self-contained.

### Add an archive link

If you accumulate `cybersec_briefing_2026-05-27.html` files in a folder, add to the footer:

```html
<a href="../index.html">← Briefing archive</a>
```

Then generate an index.html separately (e.g., with `python scripts/build_archive_index.py`).

## When this recipe is NOT the right pick

- You want comment threads on each briefing → use WordPress
- You want full-text search across 6 months of briefings → use Notion
- You want every briefing in a git history → use GitHub Pages publisher
- You want the briefing emailed daily → wire a separate email-sending Skill in your chain

## Troubleshooting

### "HTML looks broken on mobile"

Open the file on desktop, view source, and confirm the `<meta name="viewport">` tag is intact. Some text editors strip it during edits.

### "Dark mode toggle doesn't work"

The JavaScript is inline. If you customized the template and broke the `<script>` block, the toggle stops working. Restore from the original.

### "Source links don't render as links"

The Markdown → HTML conversion in `publish_static_html.py` handles `[text](url)` properly. If your briefing uses raw URLs without Markdown link syntax, they get rendered as plain text. Fix at the categorizer step.
