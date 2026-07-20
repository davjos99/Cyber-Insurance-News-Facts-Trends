#!/usr/bin/env python3
"""
publish_github_pages.py — write briefing to a GitHub Pages repo, commit, push.

Two flavors:
  jekyll  → writes _posts/YYYY-MM-DD-cybersec-briefing.md with front-matter
  html    → writes <post_dir>/cybersec_briefing_YYYY-MM-DD.html via the static publisher

Config file (JSON):
  {
    "repo_path": "/Users/you/my-blog",
    "flavor": "jekyll",
    "post_dir": "_posts",
    "front_matter": {"layout":"post","categories":["cybersec"],"tags":["security"]},
    "commit_message_template": "Cybersec briefing for {DATE}",
    "auto_push": true
  }

Usage:
  python publish_github_pages.py --input briefing.md --config gh-pages-config.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[publish_github_pages] {msg}", file=sys.stderr)


def run_git(repo_path: Path, args: list[str], check: bool = True) -> tuple[int, str, str]:
    """Run a git command in the repo, return (rc, stdout, stderr)."""
    cmd = ["git", "-C", str(repo_path)] + args
    log(f"$ {' '.join(cmd)}")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        log(f"git stderr: {p.stderr.strip()}")
    return p.returncode, p.stdout, p.stderr


def extract_date_from_briefing(text: str) -> str:
    """Pull the date from the H1: 'Cybersec Briefing — 2026-05-27'."""
    m = re.search(r"#\s+Cybersec\s+Briefing\s+.\s+(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_jekyll_post(briefing_text: str, front_matter: dict, date_str: str) -> str:
    """Wrap briefing.md in Jekyll front-matter."""
    fm = dict(front_matter)
    fm["title"] = f"Cybersec Briefing — {date_str}"
    fm["date"] = f"{date_str} 08:00:00 +0000"

    fm_lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}: [{', '.join(repr(x) for x in v)}]")
        else:
            fm_lines.append(f'{k}: "{v}"')
    fm_lines.append("---")
    fm_lines.append("")

    # Strip the H1 from the briefing — Jekyll renders the title from front-matter
    body_lines = briefing_text.splitlines()
    stripped: list[str] = []
    h1_skipped = False
    for line in body_lines:
        if not h1_skipped and line.startswith("# "):
            h1_skipped = True
            continue
        stripped.append(line)

    return "\n".join(fm_lines) + "\n".join(stripped)


def main() -> int:
    p = argparse.ArgumentParser(description="Publish briefing to GitHub Pages via git.")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--no-push", action="store_true", help="Override config.auto_push (commit only)")
    args = p.parse_args()

    in_path = Path(args.input)
    cfg_path = Path(args.config)
    if not in_path.exists():
        log(f"ERROR: input not found: {in_path}")
        return 2
    if not cfg_path.exists():
        log(f"ERROR: config not found: {cfg_path}")
        return 2

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    repo_path = Path(cfg["repo_path"]).expanduser()
    flavor = cfg.get("flavor", "jekyll").lower()
    post_dir = repo_path / cfg.get("post_dir", "_posts")

    if not repo_path.exists() or not (repo_path / ".git").exists():
        log(f"ERROR: not a git repo: {repo_path}")
        return 2

    briefing_text = in_path.read_text(encoding="utf-8")
    date_str = extract_date_from_briefing(briefing_text)

    post_dir.mkdir(parents=True, exist_ok=True)

    if flavor == "jekyll":
        dest = post_dir / f"{date_str}-cybersec-briefing.md"
        content = build_jekyll_post(briefing_text, cfg.get("front_matter", {}), date_str)
        dest.write_text(content, encoding="utf-8")
    elif flavor == "html":
        # Lazily import the static publisher
        sys.path.insert(0, str(Path(__file__).parent))
        from publish_static_html import parse_briefing, render_items_html, html_escape
        dest = post_dir / f"cybersec_briefing_{date_str}.html"
        tmpl_path = Path(__file__).parent.parent / "assets" / "templates" / "news_page.html"
        tmpl = tmpl_path.read_text(encoding="utf-8")
        parsed = parse_briefing(briefing_text)
        now = datetime.now(timezone.utc)
        replacements = {
            "{TITLE}": html_escape(parsed["title"]),
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
            tmpl = tmpl.replace(k, v)
        dest.write_text(tmpl, encoding="utf-8")
    else:
        log(f"ERROR: unknown flavor: {flavor}")
        return 2

    log(f"Wrote: {dest}")

    # git add + commit
    rc, _, _ = run_git(repo_path, ["add", str(dest.relative_to(repo_path))])
    if rc != 0:
        return 1
    commit_msg = cfg.get("commit_message_template", "Cybersec briefing for {DATE}").replace("{DATE}", date_str)
    rc, _, _ = run_git(repo_path, ["commit", "-m", commit_msg])
    if rc != 0:
        log("WARNING: nothing to commit (possibly already committed for today)")
        return 0

    auto_push = cfg.get("auto_push", True) and not args.no_push
    if auto_push:
        rc, _, stderr = run_git(repo_path, ["push"])
        if rc != 0:
            log(f"ERROR: git push failed: {stderr}")
            return 1
        log("Pushed.")
    else:
        log("Committed locally, push skipped (auto_push=false or --no-push)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
