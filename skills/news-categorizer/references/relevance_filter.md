# Relevance Filter — What Gets Dropped Before Categorization

A 30-item raw feed should filter down to 9-15 brief-worthy items. Most of what RSS surfaces is noise. This file lists the patterns that get dropped.

## Drop categories

### 1. Vendor PR
Patterns:
- "X announces partnership with Y"
- "X named leader in [Gartner Magic Quadrant | Forrester Wave | IDC MarketScape]"
- "X integrates with Y" (when not security-relevant)
- "X launches new [platform | suite | product]" (without a specific new defensive capability)
- "X receives funding round" (unless > $100M Series C+ and the brief audience cares about market signals)

Why drop: The vendor's marketing team wrote it. It's not news, it's promotion.

### 2. Broad opinion
Patterns:
- "5 things every CISO should know"
- "Why zero trust matters"
- "The future of cybersecurity is..."
- "Cybersecurity is the most important..."
- Any title that starts with "Why" or "The truth about" and ends with no specific technical content

Why drop: Opinion without recipe is filler.

### 3. Conference / event promos
Patterns:
- "Join us at RSA / Black Hat / DEFCON / BSides..."
- "Register for our webinar"
- "Live demo at booth #..."
- "Speaking session announcement"

Why drop: Calendar items, not security signals.

### 4. Sponsored / "presented by"
Patterns:
- "Sponsored by X"
- "Presented by X"
- "In partnership with X"
- "Brought to you by X"

Why drop: Editorial integrity. Paid placements skew the brief.

### 5. Listicle filler
Patterns:
- "Top 10 [tools | trends | predictions] for 2026"
- "Best [SIEM | EDR | XDR] solutions of 2026"
- "Cybersec wins / fails of the week"

Why drop: SEO bait. Rarely contains a specific technical fact or recommendation.

### 6. Industry-survey results without a specific finding
Patterns:
- "X% of organizations now use cloud security tools"
- "Cybersec spending up Y% YoY"
- "M% of CISOs report stress"

Why drop: Headline stat without an actionable insight. Most surveys are vendor-sponsored anyway.

### 7. Already-covered angle
If an earlier item in your draft already covered the same incident from a higher-authority source, drop the lower-authority repeat. (The fetcher's deduper handles most of this; you catch the strays.)

### 8. Speculation without disclosure
Patterns:
- "Researchers say AI could be used to..."
- "Experts warn that quantum computers might..."
- "It's possible that..."

Why drop: Theoretical risk without a specific finding, PoC, or recommendation.

### 9. Geopolitics without technical content
Patterns:
- "Russia accused of..."
- "China cyber operations target..."
- "North Korea hackers steal..."

These CAN qualify if there's a specific technical IoC, malware family, or vulnerability — but pure attribution headlines without technical substance get dropped. The reader can't act on "Country X bad."

### 10. Recycled patch announcements
If Microsoft Patch Tuesday already shipped and was covered last week, a follow-up "Microsoft Patch Tuesday details" article from a different source 5 days later gets dropped unless it adds new exploitation data.

## What does NOT get dropped

- Specific CVEs with version ranges
- Named breaches with record counts
- Ransomware leak-site listings (always include, even if 50/week)
- Government action (regulations, takedowns)
- Open-source tool releases with usage docs
- Post-mortems of specific incidents
- Hardening guides with concrete configs
- New detection rules / Sigma rules / Yara rules
- Vulnerability research with PoC code

## Edge cases

### "Acme Corp announces new XDR product with novel detection technique"

Mostly vendor PR, but if there's a genuinely new technique (described, not just named), it can squeeze into Advice. Test: would a SOC engineer adopt this if they read the source? If yes, keep. If no, drop.

### "Cybercrime cost economy $X trillion in 2025"

Drop. Industry stat without action. The number is too aggregated to matter to one operator.

### "Reuters reports phishing campaign targeting US elections"

Keep IF the campaign has named threat actors, IoCs, or target sectors. Drop IF it's just "phishing is happening, again."

### "Acme Corp CISO resigns"

News-bucket. Only worth including if Acme is a major vendor (AWS, Microsoft, Cisco) or if the resignation followed a public incident. Otherwise drop.

## How to calibrate

If you're consistently keeping > 20 items per run, your filter is too loose — re-read this file. If you're keeping < 5 items per run, your filter is too tight — relax on the "Advice" category, which is naturally lower-volume.

Target: 9-15 items total across all three buckets after filtering.
