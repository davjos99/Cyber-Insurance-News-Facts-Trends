#!/usr/bin/env python3
"""
publish_static_html.py — render briefing.md to a self-contained HTML file.

Zero auth. Zero network calls. Just file I/O.

Usage:
  python publish_static_html.py --input briefing.md --output news_page.html
  python publish_static_html.py --input briefing.md --output news_page.html --template /path/to/custom.html
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[publish_static_html] {msg}", file=sys.stderr)


# ---------- Markdown -> HTML (very narrow scope: only what the brief uses) ----------

INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def md_inline_to_html(text: str) -> str:
    """Convert inline Markdown to HTML — bold, italic, links."""
    # Escape first, then re-introduce the link/bold tags
    # Strategy: find spans first, replace with placeholders, escape, then sub back.
    placeholders: list[tuple[str, str]] = []

    def stash(m: re.Match, kind: str) -> str:
        key = f"\x00{kind}{len(placeholders)}\x00"
        placeholders.append((key, m.group(0)))
        return key

    # Links
    text = INLINE_LINK_RE.sub(lambda m: stash(m, "L"), text)
    # Bold
    text = BOLD_RE.sub(lambda m: stash(m, "B"), text)
    # Italic
    text = ITALIC_RE.sub(lambda m: stash(m, "I"), text)
    # Escape literal HTML
    text = html_escape(text)
    # Restore spans as real HTML
    for key, original in placeholders:
        if key.startswith("\x00L"):
            m = INLINE_LINK_RE.match(original)
            label = html_escape(m.group(1))
            url = html_escape(m.group(2))
            text = text.replace(key, f'<a href="{url}" rel="noopener noreferrer" target="_blank">{label}</a>')
        elif key.startswith("\x00B"):
            m = BOLD_RE.match(original)
            inner = html_escape(m.group(1))
            text = text.replace(key, f"<strong>{inner}</strong>")
        elif key.startswith("\x00I"):
            m = ITALIC_RE.match(original)
            inner = html_escape(m.group(1))
            text = text.replace(key, f"<em>{inner}</em>")
    return text


# ---------- Briefing parsing ----------

SECTION_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
TITLE_HEADER_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
META_LINE_RE = re.compile(r"^_Window:\s+last\s+(\d+)\s+hours\s+.\s+(\d+)\s+sources\s+polled\s+.\s+(\d+)\s+items\s+reviewed\s+.\s+(\d+)\s+kept_", re.MULTILINE)
ITEM_LINE_RE = re.compile(r"^[-*]\s+(.+)$")


def parse_briefing(text: str) -> dict:
    """Extract title, meta, sections from briefing.md."""
    out = {
        "title": "Cybersec Insurance News-Facts-Trends Briefing",
        "window_hours": "24",
        "sources_polled": "?",
        "items_reviewed": "?",
        "items_kept": "?",
        "sections": {"Threats": [], "News": [], "Advice": []},
        "footer_note": "",
    }

    title_m = TITLE_HEADER_RE.search(text)
    if title_m:
        out["title"] = title_m.group(1).strip()

    meta_m = META_LINE_RE.search(text)
    if meta_m:
        out["window_hours"] = meta_m.group(1)
        out["sources_polled"] = meta_m.group(2)
        out["items_reviewed"] = meta_m.group(3)
        out["items_kept"] = meta_m.group(4)

    # Parse sections
    lines = text.splitlines()
    current_section = None
    for line in lines:
        sec_m = SECTION_HEADER_RE.match(line)
        if sec_m:
            current_section = sec_m.group(1).strip()
            if current_section not in out["sections"]:
                out["sections"][current_section] = []
            continue
        if current_section is None:
            continue
        item_m = ITEM_LINE_RE.match(line.strip())
        if item_m:
            out["sections"][current_section].append(item_m.group(1).strip())

    # Footer: lines starting with _Sources that failed (in italics) at the bottom
    failed_m = re.search(r"_Sources that failed[^_]*_", text)
    if failed_m:
        out["footer_note"] = f"<br><em>{html_escape(failed_m.group(0).strip('_'))}</em>"

    return out


def render_items_html(items: list[str]) -> str:
    if not items:
        return '<div class="no-items">No material items in the window.</div>'
    # An item may start with "**Title** — body"
    rendered_items = []
    for raw in items:
        if " — " in raw:
            head, _, tail = raw.partition(" — ")
            head_html = md_inline_to_html(head)
            tail_html = md_inline_to_html(tail)
            rendered_items.append(f"<li>{head_html}<p>{tail_html}</p></li>")
        else:
            rendered_items.append(f"<li>{md_inline_to_html(raw)}</li>")
    return f"<ul>{''.join(rendered_items)}</ul>"


# ---------- Main ----------

def main() -> int:
    p = argparse.ArgumentParser(description="Render briefing.md to static HTML.")
    p.add_argument("--input", required=True, help="briefing.md")
    p.add_argument("--output", required=True, help="output HTML path")
    p.add_argument("--template", help="HTML template path (defaults to ../assets/templates/news_page.html)")
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        log(f"ERROR: input not found: {in_path}")
        return 2

    if args.template:
        tmpl_path = Path(args.template)
    else:
        tmpl_path = Path(__file__).parent.parent / "assets" / "templates" / "news_page.html"
    if not tmpl_path.exists():
        log(f"ERROR: template not found: {tmpl_path}")
        return 2

    text = in_path.read_text(encoding="utf-8")
    parsed = parse_briefing(text)
    template = tmpl_path.read_text(encoding="utf-8")

    now = datetime.now(timezone.utc)

    replacements = {
        "{TITLE}": "Cybersec Insurance News-Facts-Trends",
        "{WINDOW_HOURS}": html_escape(parsed["window_hours"]),
        "{SOURCES_POLLED}": html_escape(parsed["sources_polled"]),
        "{ITEMS_KEPT}": html_escape(parsed["items_kept"]),
        "{ITEMS_REVIEWED}": html_escape(parsed["items_reviewed"]),
        "{GENERATED_AT}": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "{THREATS_HTML}": render_items_html(parsed["sections"].get("Threats", [])),
        "{NEWS_HTML}": render_items_html(parsed["sections"].get("News", [])),
        "{ADVICE_HTML}": render_items_html(parsed["sections"].get("Advice", [])),
        "{FOOTER_NOTE}": parsed["footer_note"],
    }
    for k, v in replacements.items():
        template = template.replace(k, v)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(template, encoding="utf-8")
    log(f"Wrote: {out_path}  ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
