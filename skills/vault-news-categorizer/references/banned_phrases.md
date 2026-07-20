# Banned Phrases — Validator-Enforced

The validator (`scripts/validate_briefing.py`) rejects any briefing that contains these phrases. The rationale comes from the bullet-style guide: numbers lead, words follow. Adjectives editorialize without informing.

## Hard-banned adjectives

- critical
- concerning
- groundbreaking
- game-changing
- alarming
- shocking
- unprecedented
- devastating
- catastrophic
- staggering
- massive (used as descriptor; "massive 4.2M records" is OK because the number does the work)

## Hard-banned framings

- "could be the biggest..."
- "experts say..." (use the expert's name + claim)
- "shockingly..."
- "alarmingly..."
- "in a stunning development..."
- "this could be a game-changer for..."

## Soft warnings (validator flags, doesn't reject)

These get a warning the briefer should review:

- "significant" (often meaningless — replace with the number)
- "major" (replace with scope)
- "important" (let the reader judge)
- "huge" (replace with the metric)

## Allowed when paired with a number

These adjectives become OK when they're describing a real measurement:

- "actively exploited" — paired with the CVE and exploitation source
- "in-the-wild" — paired with the threat actor or campaign name
- "publicly disclosed" — paired with the disclosure date
- "unpatched" — paired with the timeline

Example:
- BAD: "A critical vulnerability was disclosed."
- GOOD: "CVE-2026-1234 (CVSS 9.8), unpatched for 11 days, actively exploited by FIN12."

## Editor's note

The point is not to write robotic copy. The point is to respect the reader's time. Adjectives without numbers are filler. Numbers without adjectives are signal.

When in doubt, write the number first and see if you still need the adjective.
