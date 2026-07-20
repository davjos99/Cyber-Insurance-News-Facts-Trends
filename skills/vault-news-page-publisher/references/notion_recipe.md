# Notion Recipe

Publish the daily cybersec briefing as a Notion page in a database.

## Prerequisites

1. A Notion workspace (personal or team)
2. A Notion **integration** (one-time setup, takes 2 minutes)
3. A Notion **database** to receive the briefings (one-time setup)

## Setup (one-time)

### Create a Notion integration

1. Go to https://www.notion.so/my-integrations
2. Click **+ New integration**
3. Name it "Cybersec Briefing"
4. Workspace: pick your workspace
5. Capabilities: Read content, Update content, Insert content (default)
6. Submit
7. Copy the **Internal Integration Token** (starts with `secret_`)

### Create the database

1. In your Notion workspace, create a new page
2. Type `/database` and pick "Database — Full page"
3. Name it "Cybersec Briefings"
4. Add these properties (rename / type as listed):
   - **Name** (Title) — auto-generated
   - **Date** (Date)
   - **Window** (Number) — fetch window in hours
   - **Threats** (Number)
   - **News** (Number)
   - **Advice** (Number)
   - **Sources** (Text) — e.g. "10/10"
5. Click the `...` menu → **Add connections** → pick "Cybersec Briefing" integration

### Get the database ID

In the URL of your database page: `https://www.notion.so/{workspace}/{database_id}?v={view_id}`

The `{database_id}` is the 32-char hex (with dashes). Copy it.

### Store credentials

Create `~/.cybersec-briefing/notion-creds.env`:

```bash
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=12345678-1234-1234-1234-123456789012
```

Chmod 600:

```bash
chmod 600 ~/.cybersec-briefing/notion-creds.env
```

## Usage

```bash
set -a; source ~/.cybersec-briefing/notion-creds.env; set +a

python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_notion.py \
  --input /tmp/briefing.md \
  --output "$NOTION_DATABASE_ID"
```

## What gets posted

A new page in the database with:

- **Name:** "Cybersec Briefing — 2026-05-27"
- **Date:** 2026-05-27
- **Window:** 24
- **Threats:** 5
- **News:** 5
- **Advice:** 5
- **Sources:** "10/10"
- **Page body:** the briefing content, rendered as Notion blocks (heading + bulleted lists + paragraph)

## API endpoint

```
POST https://api.notion.com/v1/pages
Authorization: Bearer {NOTION_TOKEN}
Notion-Version: 2022-06-28
Content-Type: application/json

{
  "parent": { "database_id": "{NOTION_DATABASE_ID}" },
  "properties": {
    "Name": { "title": [{"text": {"content": "Cybersec Briefing — 2026-05-27"}}] },
    "Date": { "date": {"start": "2026-05-27"} },
    "Threats": { "number": 5 },
    "News": { "number": 5 },
    "Advice": { "number": 5 },
    "Sources": { "rich_text": [{"text": {"content": "10/10"}}] }
  },
  "children": [ <list of block objects> ]
}
```

## Block conversion

The Skill converts Markdown to Notion blocks:

| Markdown | Notion block |
|---|---|
| `# Heading 1` | heading_1 |
| `## Heading 2` | heading_2 |
| `### Heading 3` | heading_3 |
| `- item` | bulleted_list_item |
| `1. item` | numbered_list_item |
| paragraph | paragraph |
| `[text](url)` | text with link annotation |
| `**bold**` | text with bold annotation |
| `_italic_` | text with italic annotation |
| `---` | divider |

## Common errors

### `401 Unauthorized`
- Token wrong or expired. Regenerate at https://www.notion.so/my-integrations.

### `404 Not Found — Could not find database`
- The integration is NOT connected to the database. Open the database page → `...` menu → Add connections → pick the integration.

### `400 — body failed validation`
- Most often: property name mismatch. The Skill expects properties named exactly **Name**, **Date**, **Window**, **Threats**, **News**, **Advice**, **Sources**. Rename in Notion to match, OR pass `--property-map /path/to/map.json` to remap.

### `400 — text blocks exceed 2000 chars`
- Notion limits text content per block to 2000 chars. The Skill splits longer paragraphs automatically; if you customize the template to add bigger blocks, you may hit this.

## Customization

### Different property names

If your existing database has different property names, create `~/.cybersec-briefing/notion-property-map.json`:

```json
{
  "Name": "Title",
  "Date": "Briefing Date",
  "Threats": "Threat Count",
  "News": "News Count",
  "Advice": "Advice Count",
  "Sources": "Source Coverage"
}
```

Then pass `--property-map ~/.cybersec-briefing/notion-property-map.json`.

### Tags / categories

If you want to tag briefings, add a `Tags` (Multi-select) property to your database and pass `--tags cybersec,daily-brief`.

## Security notes

- Notion integration tokens have access to whatever pages you connect them to. Connect only the briefing database, NOT your entire workspace.
- Rotate tokens every 90 days at https://www.notion.so/my-integrations.
- Tokens are NOT scoped per-page — they apply to all pages you've connected the integration to.

## When this recipe is NOT the right pick

- You want a public archive → use WordPress or GitHub Pages
- You don't use Notion → don't start using Notion just for this; use static HTML
- You need real-time editing or comments on briefings → Notion is fine for that, this is the right pick
