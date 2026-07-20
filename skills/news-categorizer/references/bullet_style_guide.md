# Bullet Style Guide

Every item in the briefing gets a 1-2 sentence summary. The summary is the difference between a useful brief and a noise reel.

## The rule

**Names + dates + numbers lead. Adjectives never.**

This is Pragati's universal voice rule ported from the Monday Brief skill: "Numbers lead, words follow. Never write 'revenue is healthy' — write '$43k this month, ▲ 8% MoM'." Same in cybersec.

## Good vs bad

### BAD
- "A critical vulnerability was discovered in Apache." ← no CVE number, no version range, no exploitation status, no patch, just an adjective
- "Acme Corp suffered a major breach." ← no record count, no threat actor, no leak-site evidence
- "Concerning rise in supply-chain attacks." ← no specific incident, no number, just vibes

### GOOD
- "CVE-2026-1234 in Apache HTTP Server 2.4.50-2.4.59 allows unauthenticated RCE; active exploitation confirmed; patched in 2.4.60."
- "Acme Corp confirmed breach affecting 4.2M customers; BlackSuit ransomware group claimed responsibility on leak site."
- "FBI seized 23 servers belonging to StealC info-stealer operation; operation stole credentials from 1.5M victims across 89 countries."

## Structure

Each summary has up to 3 facts in this order:

1. **What** (CVE / product / company / technique)
2. **Scope** (version range / record count / victim count / industries affected)
3. **Action** (patch / hunt / read / nothing)

If you can't fill at least two of these slots from the source, the item is too shallow — drop it.

## Length

1-2 sentences. Max 40 words per item. If you're past 40 words, you're editorializing — cut.

The brief is a scanning tool, not a long-read. The reader skims; if a row catches their eye, they click the URL for depth.

## Source citation

Every item ends with: `[Source: {source_name}]({url})`

Markdown link, source name visible, URL behind the link. The publisher renders this as a clickable link in HTML / WordPress / Notion.

Never strip the URL "for cleanliness." The whole point of the brief is to let the reader drill in.

## Banned phrases (validator-enforced)

These get flagged by `scripts/validate_briefing.py`:

- "critical" (use the CVSS score instead, or "actively exploited")
- "concerning" (state the number)
- "groundbreaking" (almost always wrong; security research is iterative)
- "game-changing" (marketing language)
- "alarming" (let the reader judge)
- "shocking" (same)
- "unprecedented" (rarely true)

## Voice — anti-doom

The cybersec press defaults to apocalypse mode. The Pragati brief defaults to operator mode. The difference:

### Apocalypse voice
> "A SHOCKING new vulnerability threatens MILLIONS of users globally. Experts say this could be the BIGGEST cyber threat of the decade."

### Operator voice
> "CVE-2026-1234, CVSS 9.8, affects Apache 2.4.50-2.4.59. 12M servers exposed per Shodan. Patch shipped 2026-05-26. Hunt for /admin/exec.cgi in your access logs."

The operator voice respects the reader's time and competence. That is the moat. Newsroom voice does the opposite.

## Examples by bucket

### Threats — good summaries

- "CVE-2026-1234 in Apache HTTP Server 2.4.50-2.4.59 allows unauthenticated RCE. Active exploitation confirmed by Talos; patch in 2.4.60."
- "Acme Corp confirmed 4.2M-record breach; BlackSuit listed on leak site; passwords were bcrypt-hashed."
- "Malicious npm package 'colors-rainbow' exfiltrated .env files via Discord webhook; 12K weekly downloads pre-takedown; check package.json for the dep."

### News — good summaries

- "FBI seized 23 servers of StealC info-stealer operation; 3 operators arrested in Romania, Netherlands."
- "SEC final rule requires public companies to disclose material breaches within 4 business days starting 2026-12-01."
- "Microsoft acquired CloudKnox for $1.2B; identity-and-access governance for multi-cloud."

### Advice — good summaries

- "Hardening Kubernetes against supply-chain attacks: image signing with Sigstore, admission controllers, runtime monitoring; example YAML manifests provided."
- "OWASP LLM Top 10 v2 released: prompt injection #1, training data poisoning #2, insecure output handling #3."
- "SANS publishes 3 Splunk queries to detect DCSync attempts; covers replication GUID patterns + NTDSUtil indicators."
