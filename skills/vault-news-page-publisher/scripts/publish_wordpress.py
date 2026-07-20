#!/usr/bin/env python3
"""
publish_wordpress.py — POST briefing.md to WordPress as a new post via REST API.

Reads credentials from environment:
  WP_URL          — https://yourdomain.com
  WP_USER         — WordPress username
  WP_APP_PASSWORD — Application Password (NOT login password)

Usage:
  python publish_wordpress.py --input briefing.md --status draft
  python publish_wordpress.py --input briefing.md --status publish --category "Cybersec Briefings"
  python publish_wordpress.py --input briefing.md --output https://myblog.com  # override env WP_URL

Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[publish_wordpress] {msg}", file=sys.stderr)


# Reuse the MD→HTML logic from the static publisher
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from publish_static_html import parse_briefing, render_items_html, html_escape  # noqa: E402


def briefing_to_wp_html(briefing_text: str) -> tuple[str, str]:
    """Return (rendered_html, excerpt)."""
    parsed = parse_briefing(briefing_text)
    parts = []
    parts.append(f'<p><em>Window: last {html_escape(parsed["window_hours"])} hours &middot; {html_escape(parsed["sources_polled"])} sources polled &middot; {html_escape(parsed["items_kept"])} items kept</em></p>')
    for sec_name, css_class in [("Threats", "threats"), ("News", "news"), ("Advice", "advice")]:
        items = parsed["sections"].get(sec_name, [])
        parts.append(f'<h2 class="{css_class}">{sec_name}</h2>')
        parts.append(render_items_html(items))

    # Excerpt: first Threat item, plain text, 160 chars
    threats = parsed["sections"].get("Threats", [])
    if threats:
        raw = threats[0]
        plain = re.sub(r"\[[^\]]+\]\([^)]+\)", "", raw)
        plain = re.sub(r"\*+", "", plain).strip()
        excerpt = plain[:160].rsplit(" ", 1)[0] + "..."
    else:
        excerpt = "Daily cybersec briefing."

    return "\n".join(parts), excerpt


def make_request(url: str, method: str, headers: dict, body: bytes | None = None) -> tuple[int, dict]:
    """Returns (status_code, parsed_json_body)."""
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


def find_or_create_category(wp_url: str, auth_header: str, category_name: str) -> int | None:
    """Find an existing category by slug-ish match; create if missing. Returns numeric ID."""
    slug = category_name.lower().replace(" ", "-")
    list_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories?search={urllib.request.quote(category_name)}"
    code, body = make_request(list_url, "GET", {"Authorization": auth_header})
    if code != 200:
        log(f"category search failed ({code}): {body}")
        return None
    for cat in body if isinstance(body, list) else []:
        if cat.get("slug") == slug or cat.get("name") == category_name:
            return cat["id"]
    # Create
    create_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/categories"
    payload = json.dumps({"name": category_name, "slug": slug}).encode("utf-8")
    code, body = make_request(create_url, "POST", {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }, payload)
    if code in (200, 201):
        return body.get("id")
    log(f"category create failed ({code}): {body}")
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Publish briefing.md to WordPress via REST API.")
    p.add_argument("--input", required=True)
    p.add_argument("--output", help="WordPress URL (overrides $WP_URL)")
    p.add_argument("--status", choices=["draft", "publish"], default="draft")
    p.add_argument("--category", help="Category name (e.g. 'Cybersec Briefings')")
    p.add_argument("--tags", help="Comma-separated tags")
    p.add_argument("--allow-http", action="store_true", help="Allow non-HTTPS WP_URL (NOT recommended)")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        log(f"ERROR: input not found: {in_path}")
        return 2

    wp_url = args.output or os.environ.get("WP_URL", "").strip().rstrip("/")
    wp_user = os.environ.get("WP_USER", "").strip()
    wp_pw = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not (wp_url and wp_user and wp_pw):
        log("ERROR: missing WP_URL / WP_USER / WP_APP_PASSWORD env vars")
        return 2
    if not wp_url.startswith("https://") and not args.allow_http:
        log("ERROR: WP_URL must be https:// (use --allow-http to override)")
        return 2

    briefing_text = in_path.read_text(encoding="utf-8")
    title_m = re.search(r"#\s+(Cybersec\s+Briefing\s+.\s+\d{4}-\d{2}-\d{2})", briefing_text)
    title = title_m.group(1) if title_m else f"Cybersec Briefing — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"

    content_html, excerpt = briefing_to_wp_html(briefing_text)

    auth_bytes = f"{wp_user}:{wp_pw}".encode("utf-8")
    auth_header = "Basic " + base64.b64encode(auth_bytes).decode("ascii")

    payload = {
        "title": title,
        "content": content_html,
        "status": args.status,
        "excerpt": excerpt,
    }

    if args.category:
        cat_id = find_or_create_category(wp_url, auth_header, args.category)
        if cat_id is not None:
            payload["categories"] = [cat_id]

    if args.tags:
        payload["tags_input"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    post_url = f"{wp_url}/wp-json/wp/v2/posts"
    body_bytes = json.dumps(payload).encode("utf-8")
    code, body = make_request(post_url, "POST", {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": "ClaudeSkillFetcher/1.0",
    }, body_bytes)

    if code in (200, 201):
        log(f"OK — post created (id={body.get('id')}, status={body.get('status')})")
        log(f"     {body.get('link')}")
        return 0
    log(f"FAIL — HTTP {code}: {body}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
