#!/usr/bin/env python3
"""
publish_notion.py — POST briefing.md to a Notion database as a new page.

Reads credentials from environment:
  NOTION_TOKEN        — secret_xxx integration token
  NOTION_DATABASE_ID  — UUID of target database (or pass via --output)

Database properties expected (rename via --property-map if your DB uses different names):
  Name      (Title)
  Date      (Date)
  Window    (Number)
  Threats   (Number)
  News      (Number)
  Advice    (Number)
  Sources   (Rich text)

Stdlib only.

Usage:
  python publish_notion.py --input briefing.md --output <database_id>
  python publish_notion.py --input briefing.md   # picks $NOTION_DATABASE_ID
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def log(msg: str) -> None:
    print(f"[publish_notion] {msg}", file=sys.stderr)


# ---------- Briefing parsing ----------

H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
META_RE = re.compile(r"^_Window:\s+last\s+(\d+)\s+hours\s+.\s+(\d+)\s+sources\s+polled\s+.\s+(\d+)\s+items\s+reviewed\s+.\s+(\d+)\s+kept_", re.MULTILINE)
ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
DATE_FROM_TITLE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def split_inline(text: str) -> list[dict]:
    """Convert a line with Markdown bold + links into a list of Notion rich_text objects."""
    out: list[dict] = []
    i = 0
    while i < len(text):
        # try link
        m_link = LINK_RE.match(text, i)
        if m_link:
            out.append({
                "type": "text",
                "text": {"content": m_link.group(1), "link": {"url": m_link.group(2)}},
            })
            i = m_link.end()
            continue
        # try bold
        m_bold = BOLD_RE.match(text, i)
        if m_bold:
            out.append({
                "type": "text",
                "text": {"content": m_bold.group(1)},
                "annotations": {"bold": True},
            })
            i = m_bold.end()
            continue
        # find next special character
        next_special = len(text)
        for token in ("[", "**"):
            j = text.find(token, i)
            if j != -1 and j < next_special:
                next_special = j
        chunk = text[i:next_special]
        if chunk:
            # Notion has a 2000-char limit per text fragment
            while chunk:
                piece, chunk = chunk[:2000], chunk[2000:]
                out.append({"type": "text", "text": {"content": piece}})
        i = next_special if next_special > i else i + 1
    return out


def parse_briefing(text: str) -> dict:
    parsed = {
        "title": "Cybersec Briefing",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "window_hours": 24,
        "sources_polled": "?",
        "items_kept": 0,
        "sections": {"Threats": [], "News": [], "Advice": []},
        "items_per_section": {"Threats": 0, "News": 0, "Advice": 0},
    }
    h1 = H1_RE.search(text)
    if h1:
        parsed["title"] = h1.group(1).strip()
        d = DATE_FROM_TITLE_RE.search(parsed["title"])
        if d:
            parsed["date"] = d.group(1)
    m = META_RE.search(text)
    if m:
        parsed["window_hours"] = int(m.group(1))
        parsed["sources_polled"] = m.group(2)
        parsed["items_kept"] = int(m.group(4))

    # Sections
    current = None
    for line in text.splitlines():
        h = H2_RE.match(line)
        if h:
            current = h.group(1).strip()
            if current not in parsed["sections"]:
                parsed["sections"][current] = []
            continue
        if current is None:
            continue
        im = ITEM_RE.match(line.strip())
        if im:
            parsed["sections"][current].append(im.group(1).strip())

    for k in parsed["items_per_section"]:
        parsed["items_per_section"][k] = len(parsed["sections"].get(k, []))

    return parsed


def briefing_to_blocks(parsed: dict) -> list[dict]:
    blocks: list[dict] = []
    for sec in ("Threats", "News", "Advice"):
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": sec}}]},
        })
        items = parsed["sections"].get(sec, [])
        if not items:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": "No material items in the window."}, "annotations": {"italic": True}}]},
            })
            continue
        for item in items:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": split_inline(item)},
            })
    return blocks


def make_request(url: str, method: str, headers: dict, body: bytes | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return e.code, parsed


def main() -> int:
    p = argparse.ArgumentParser(description="Publish briefing.md to a Notion database.")
    p.add_argument("--input", required=True)
    p.add_argument("--output", help="Database ID (overrides $NOTION_DATABASE_ID)")
    p.add_argument("--property-map", help="JSON file remapping property names")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        log(f"ERROR: input not found: {in_path}")
        return 2

    token = os.environ.get("NOTION_TOKEN", "").strip()
    db_id = args.output or os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not (token and db_id):
        log("ERROR: missing NOTION_TOKEN or NOTION_DATABASE_ID")
        return 2

    prop_map = {
        "Name": "Name",
        "Date": "Date",
        "Window": "Window",
        "Threats": "Threats",
        "News": "News",
        "Advice": "Advice",
        "Sources": "Sources",
    }
    if args.property_map:
        m_path = Path(args.property_map)
        if not m_path.exists():
            log(f"ERROR: property-map not found: {m_path}")
            return 2
        prop_map.update(json.loads(m_path.read_text(encoding="utf-8")))

    text = in_path.read_text(encoding="utf-8")
    parsed = parse_briefing(text)

    properties = {
        prop_map["Name"]: {"title": [{"text": {"content": parsed["title"]}}]},
        prop_map["Date"]: {"date": {"start": parsed["date"]}},
        prop_map["Window"]: {"number": parsed["window_hours"]},
        prop_map["Threats"]: {"number": parsed["items_per_section"]["Threats"]},
        prop_map["News"]: {"number": parsed["items_per_section"]["News"]},
        prop_map["Advice"]: {"number": parsed["items_per_section"]["Advice"]},
        prop_map["Sources"]: {"rich_text": [{"text": {"content": parsed["sources_polled"]}}]},
    }

    payload = {
        "parent": {"database_id": db_id},
        "properties": properties,
        "children": briefing_to_blocks(parsed),
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    code, resp = make_request(f"{NOTION_API}/pages", "POST", {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "ClaudeSkillFetcher/1.0",
    }, body_bytes)

    if code in (200, 201):
        page_id = resp.get("id", "<no id>")
        page_url = resp.get("url", "")
        log(f"OK — page created ({page_id})")
        log(f"     {page_url}")
        return 0

    log(f"FAIL — HTTP {code}: {json.dumps(resp)[:500]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
