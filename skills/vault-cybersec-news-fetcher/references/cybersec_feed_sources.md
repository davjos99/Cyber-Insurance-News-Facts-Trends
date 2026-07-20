# Cybersec Feed Sources — The 15 Trusted Wells

These 15 sources are the ones we trust for daily cybersec signal. The Skill ships with 10 enabled by default; the other 5 are listed here for members who want to extend the source list.

## Authority order (used by the deduper)

When the same story appears in multiple feeds, the deduper keeps the version from the higher-authority source:

1. KrebsOnSecurity (Brian Krebs, original investigative reporting, breaks stories first)
2. SANS Internet Storm Center (handler-written diary, technical depth)
3. Schneier on Security (Bruce Schneier, policy + cryptography depth)
4. Cisco Talos (vendor-run but research-heavy, deep CVE work)
5. The Hacker News (high volume, fast turnaround, sometimes shallow)
6. Bleeping Computer (good breach + ransomware coverage, lots of remediation guides)
7. Dark Reading (enterprise-focused, opinion-heavy)
8. CSO Online (executive-audience, policy + budget angles)
9. ThreatPost (rebooted under Kaspersky — note the bias)
10. US-CERT / CISA Alerts (official advisories, slow but authoritative)
11. (Extension slot) Recorded Future Blog
12. (Extension slot) Mandiant Blog
13. (Extension slot) Microsoft Security Response Center
14. (Extension slot) Project Zero (Google)
15. (Extension slot) Bug Bounty Reports Explained

## The 10 default sources

### 1. The Hacker News
- **URL:** https://feeds.feedburner.com/TheHackersNews
- **Covers:** Daily roundup of CVEs, breaches, APT activity, security tools
- **Cadence:** 3-8 posts/day
- **Watch out for:** Sometimes light on technical depth — good for breadth, not always depth
- **Earns its slot:** Highest-volume reliable feed in the space

### 2. KrebsOnSecurity
- **URL:** https://krebsonsecurity.com/feed/
- **Covers:** Investigative breach reporting, financial cybercrime, identity theft
- **Cadence:** 1-3 posts/week (low volume, high signal)
- **Watch out for:** Long-form, sometimes paywall-adjacent (newsletter-style)
- **Earns its slot:** Brian Krebs breaks stories. The deduper gives Krebs the authority tiebreaker for a reason.

### 3. Bleeping Computer
- **URL:** https://www.bleepingcomputer.com/feed/
- **Covers:** Ransomware, malware analysis, breach disclosures, Windows-specific issues
- **Cadence:** 5-15 posts/day
- **Watch out for:** Volume — set the time window tight or you drown
- **Earns its slot:** Best ransomware coverage on the internet

### 4. SANS Internet Storm Center
- **URL:** https://isc.sans.edu/rssfeed.xml
- **Covers:** Handler diary entries, technical write-ups, packet captures, real attacks observed
- **Cadence:** 1-3 posts/day
- **Watch out for:** Highly technical — diaries assume packet-level fluency
- **Earns its slot:** Practitioner-written, deepest technical depth in any free feed

### 5. US-CERT / CISA Alerts
- **URL:** https://www.cisa.gov/uscert/ncas/alerts.xml
- **Covers:** Official US government cybersec advisories, ICS-CERT advisories
- **Cadence:** 2-5 posts/week
- **Watch out for:** Government tone (dry), but authoritative
- **Earns its slot:** Official source of record for US infrastructure threats

### 6. Cisco Talos
- **URL:** https://blog.talosintelligence.com/rss/
- **Covers:** Vulnerability research, malware reversing, threat actor profiling
- **Cadence:** 2-4 posts/week
- **Watch out for:** Vendor-run — be aware of the Cisco product subtext
- **Earns its slot:** Among the top corporate threat research teams; deep, original work

### 7. Schneier on Security
- **URL:** https://www.schneier.com/feed/atom/
- **Covers:** Policy, cryptography, surveillance, broader security thinking
- **Cadence:** 1-2 posts/day (mostly link aggregation + commentary)
- **Watch out for:** Aggregator-style (lots of "link to article + 1 paragraph comment")
- **Earns its slot:** Bruce Schneier's framing is the missing layer — policy + culture, not just CVEs

### 8. Dark Reading
- **URL:** https://www.darkreading.com/rss.xml
- **Covers:** Enterprise security, CISO-level commentary, industry analysis
- **Cadence:** 5-10 posts/day
- **Watch out for:** Marketing-leaning headlines, vendor sponsorships
- **Earns its slot:** Best enterprise-audience signal for CISO-style framings

### 9. ThreatPost
- **URL:** https://threatpost.com/feed/
- **Covers:** Vulnerability disclosures, threat actor news, security tooling
- **Cadence:** 3-6 posts/day
- **Watch out for:** Owned by Kaspersky — bias possible on Russia/sanctions-related news
- **Earns its slot:** Solid breadth, good for the second-opinion check

### 10. CSO Online
- **URL:** https://www.csoonline.com/feed/
- **Covers:** Executive-audience security news, policy, budget, hiring
- **Cadence:** 4-8 posts/day
- **Watch out for:** Some "thought leadership" pieces are sponsored
- **Earns its slot:** Translates security news to business language — useful for the briefing's "advice" section

## Known failure modes per source

- **The Hacker News:** Feedburner can return 410 if their cache is being rebuilt — usually clears in 30 minutes
- **KrebsOnSecurity:** Aggressive Cloudflare — sometimes 403s default Python user agents (Skill sets explicit Mozilla UA)
- **Bleeping Computer:** Rare 429 if you hammer the feed; the Skill rate-limits to 1 request per source
- **SANS ISC:** Reliable. Almost never fails.
- **US-CERT/CISA:** Reliable. Government-grade uptime.
- **Cisco Talos:** Reliable but Blogger-hosted, so RSS dates can be ambiguous on the published vs. updated field
- **Schneier:** Atom feed (not RSS 2.0) — Skill parser handles both
- **Dark Reading:** Sometimes returns chunked response without Content-Length — handled by urllib
- **ThreatPost:** Occasional 503 during their CDN switches
- **CSO Online:** Aggressive paywall — feed returns headlines only, not full content (which is fine for briefing)

## How to extend

Edit `assets/templates/cybersec_sources.json` and add an entry:

```json
{
  "name": "Recorded Future Blog",
  "url": "https://www.recordedfuture.com/feed",
  "category": "threat-intel",
  "authority_tier": 2
}
```

Authority tiers (1 = highest, 5 = lowest) feed into the deduper's tiebreaker logic. Keep paid/subscription feeds in `references/private_sources.md` (gitignored if you're committing the bundle to GitHub) so credentials never leak.
