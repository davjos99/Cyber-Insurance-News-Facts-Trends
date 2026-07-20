#!/usr/bin/env python3
"""
validate_briefing.py — sanity-check a generated briefing.md against the rules.

Exit 0 = pass, exit 1 = fail.

Checks:
  1. Three section headers exist: "## Threats", "## News", "## Advice"
  2. Each section has 3-5 items OR an explicit "No material items today" line
  3. Every item has a source URL: [Source: ...](http...)
  4. No hard-banned adjectives: critical, concerning, groundbreaking, etc.
  5. Word count <= 800 (one screen)

Usage:
  python validate_briefing.py briefing.md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ["Threats", "News", "Advice"]

BANNED_PHRASES = [
    "critical",  # CVSS 9.x → use the number; "critical infrastructure" gets a pass below
    "concerning",
    "groundbreaking",
    "game-changing",
    "alarming",
    "shocking",
    "unprecedented",
    "devastating",
    "catastrophic",
    "staggering",
]

# These narrow contexts let "critical" pass — it's a noun phrase, not an editorializing adjective
ALLOWED_CRITICAL_CONTEXTS = [
    "critical infrastructure",
    "mission-critical",
    "business-critical",
    "critical vulnerabilities and exposures",  # CVE expansion
]

SOFT_WARNINGS = ["significant", "major", "important", "huge"]

# Source URL pattern: [Source: anything](http... or https...)
SOURCE_URL_RE = re.compile(r"\[Source:[^\]]+\]\(https?://[^)]+\)", re.IGNORECASE)
ITEM_LINE_RE = re.compile(r"^\s*[-*]\s+")
SECTION_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$")


def log(level: str, msg: str) -> None:
    print(f"[{level}] {msg}", file=sys.stderr)


def parse_sections(text: str) -> dict[str, list[str]]:
    """Returns {section_name: [item_line, ...]}."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = SECTION_HEADER_RE.match(line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is None:
            continue
        if ITEM_LINE_RE.match(line):
            sections[current].append(line.strip())
    return sections


def check_banned(text: str) -> list[str]:
    """Return list of banned-phrase errors."""
    errors = []
    lower = text.lower()
    for phrase in BANNED_PHRASES:
        # locate every occurrence
        for m in re.finditer(rf"\b{re.escape(phrase)}\b", lower):
            start = max(0, m.start() - 30)
            end = min(len(lower), m.end() + 30)
            context = lower[start:end]
            # Allow narrow "critical" contexts
            if phrase == "critical" and any(allowed in context for allowed in ALLOWED_CRITICAL_CONTEXTS):
                continue
            snippet = text[start:end].replace("\n", " ")
            errors.append(f"banned phrase '{phrase}' near: ...{snippet}...")
    return errors


def check_warnings(text: str) -> list[str]:
    """Return list of soft warnings (not errors)."""
    warnings = []
    lower = text.lower()
    for phrase in SOFT_WARNINGS:
        if re.search(rf"\b{re.escape(phrase)}\b", lower):
            warnings.append(f"soft warning: '{phrase}' detected — verify it earns its slot")
    return warnings


def validate(path: Path) -> int:
    if not path.exists():
        log("ERROR", f"file not found: {path}")
        return 2

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Required sections
    sections = parse_sections(text)
    for sec in REQUIRED_SECTIONS:
        if sec not in sections:
            errors.append(f"missing required section: ## {sec}")

    # 2. Each section: 3-5 items OR explicit "no material items"
    no_material_re = re.compile(r"no\s+(material|additional|threat-grade|news-grade|advice-grade)\s+items?", re.IGNORECASE)
    for sec in REQUIRED_SECTIONS:
        if sec not in sections:
            continue
        items = sections[sec]
        # Allow explicit "no material items today" as a single statement
        if len(items) == 0:
            # Look for a no_material line in the section body
            section_body = _extract_section_body(text, sec)
            if no_material_re.search(section_body):
                continue
            errors.append(f"section '{sec}' has 0 items and no 'no material items' note")
        elif len(items) > 7:
            warnings.append(f"section '{sec}' has {len(items)} items (target 3-5); consider tightening")
        elif len(items) < 3 and not no_material_re.search(_extract_section_body(text, sec)):
            warnings.append(f"section '{sec}' has only {len(items)} items (target 3-5)")

    # 3. Every item has a source URL
    all_items = [it for items in sections.values() for it in items]
    for item in all_items:
        if not SOURCE_URL_RE.search(item):
            errors.append(f"item missing [Source: ...](url): {item[:80]}...")

    # 4. Banned phrases
    errors.extend(check_banned(text))

    # 5. Word count
    word_count = len(text.split())
    if word_count > 800:
        warnings.append(f"word count {word_count} exceeds 800 target")

    # 6. Soft warnings
    warnings.extend(check_warnings(text))

    # Report
    print(f"Briefing validation: {path}")
    print(f"  Sections found: {list(sections.keys())}")
    print(f"  Items per section: { {k: len(v) for k, v in sections.items()} }")
    print(f"  Word count: {word_count}")
    print()
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ! {w}")
        print()
    if errors:
        print(f"FAIL — {len(errors)} error(s):")
        for e in errors:
            print(f"  X {e}")
        return 1
    print("PASS")
    return 0


def _extract_section_body(text: str, section_name: str) -> str:
    """Return the text between '## section_name' and the next '##' header."""
    pattern = rf"##\s+{re.escape(section_name)}\b(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_briefing.py <briefing.md>", file=sys.stderr)
        return 2
    return validate(Path(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
