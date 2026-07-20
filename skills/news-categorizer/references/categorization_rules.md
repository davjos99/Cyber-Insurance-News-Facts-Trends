# Categorization Rules — Threats / News / Advice

Three buckets. Mutually exclusive. If an item fits two, pick the one the reader needs to act on first.

## Threats — "Patch / hunt / contain TODAY"

An attacker is doing something **right now** or **this week**. The reader's response is operational: apply a patch, hunt for IoCs, isolate a system, change a credential.

### What qualifies

- **Active exploitation**: CVE with confirmed in-the-wild use, especially with public PoC
- **Named breach**: a real company confirmed a real data theft this week
- **Ransomware leak-site listing**: a victim was named on a leak site (LockBit, BlackSuit, ALPHV, etc.)
- **Supply-chain compromise**: npm/PyPI/Maven malicious package, compromised vendor build pipeline, signed-driver abuse
- **Zero-day disclosure**: vendor patches a vulnerability marked "exploitation detected"
- **Botnet / C2 takedown**: not technically a threat, but reader needs to hunt for prior infection IoCs
- **Phishing / vishing campaign**: targeted, named, with technical IoCs (not just "phishing is up 12% this quarter")

### Examples (real shape)

- "CVE-2026-1234 in Apache HTTP Server 2.4.50-2.4.59 allows unauthenticated RCE. Active exploitation confirmed by Talos. Patch in 2.4.60." ← **Threat**
- "Acme Corp breach exposes 4.2M customer records, BlackSuit claims responsibility on leak site." ← **Threat**
- "Malicious npm package 'colors-rainbow' steals .env files; 12K weekly downloads before takedown." ← **Threat**

### Watch out for

- "Cybercrime cost the global economy $X trillion in 2025" → that's an industry stat, not a threat → **News**
- "Phishing attacks targeting healthcare increased 23%" → trend, not specific → **News**
- "Researchers find theoretical weakness in TLS 1.3 KEM" → no PoC, not exploitable yet → **News** (or drop)

## News — "Update mental model, not firewall"

The cybersec **world** changed. Companies move, policies shift, governments act, vendors announce. The reader's response is intellectual: adjust their understanding of the landscape.

### What qualifies

- **Government action**: new regulation (SEC cybersec disclosure rule, NIS2, EU AI Act security clauses), sanctions, indictments
- **Law enforcement**: FBI / Europol takedowns (operation names: OpEndgame, OpDuckHunt, OpCronos), arrests
- **Company M&A**: cybersec vendor acquisitions, CISO appointments at major firms
- **Vendor announcements**: new security products, EOL announcements, certificate-authority changes
- **Industry stats**: ransomware payment volumes, breach counts, cyber-insurance market shifts
- **Standards / frameworks**: new NIST publications, CISA KEV catalog additions, OWASP Top 10 updates
- **Research disclosures**: academic papers on novel attack classes (without immediate exploitation)

### Examples (real shape)

- "FBI seizes infrastructure of StealC info-stealer operation; 3 operators arrested in Romania." ← **News**
- "SEC adopts final rule requiring 4-day breach disclosure for public companies." ← **News**
- "Microsoft announces Defender for Cloud will integrate with Sentinel by Q3 2026." ← **News**

### Watch out for

- "Acme Corp announces new threat-intel platform" → vendor PR → **Drop**
- "Acme Corp acquires Beta Co for $400M to expand SOAR portfolio" → real M&A → **News**

## Advice — "Read this later this week"

Someone published **how to do something better**. The reader's response is to bookmark + adapt when time permits.

### What qualifies

- **Hardening guides**: "How to lock down a Windows DC against Kerberoasting"
- **Post-mortems with lessons**: "What we learned from the 2026-03 Acme breach" (third-party analysis with takeaways)
- **Defensive technique**: new detection idea, novel honeypot design, EDR rule pack
- **Configuration recipes**: terraform / ansible modules for specific security controls
- **Methodology**: red-team playbook, threat-modeling framework
- **Tool releases**: open-source security tooling (with usage docs, not just GitHub link)

### Examples (real shape)

- "Hardening Kubernetes against supply-chain attacks: image signing, admission control, runtime monitoring (with example manifests)." ← **Advice**
- "SOC engineers: 3 Splunk queries to catch DCSync attempts." ← **Advice**
- "OWASP releases LLM Top 10 v2 — prompt injection, training data poisoning, output handling." ← **Advice**

### Watch out for

- "5 things every CISO should know about AI" with no specific framework/recipe → **Drop** (opinion filler)
- "Why zero trust matters" → opinion, not advice → **Drop**
- "Splunk query: index=main ..." with specific detection logic → **Advice** ✓

## Edge cases

### Item fits Threats AND Advice

Example: "CVE-2026-5678 in Windows Kernel actively exploited. Microsoft published hardening guide with detection queries."

Resolution: **Threats** wins. The exploitation is the urgent ask; the hardening is a side benefit.

### Item fits News AND Threats

Example: "FBI takes down BlackBasta infrastructure; victims should hunt for these IoCs."

Resolution: **Threats** wins (because of the hunt-for-IoCs action). The takedown news is secondary.

### Item fits News AND Advice

Example: "NIST publishes SP 800-218 SSDF guidance for secure software development."

Resolution: **Advice** wins (it's a framework the reader adopts). The publication is the delivery mechanism, the framework is the substance.

### Item is broad opinion

Example: "Why cybersec is the most important skill of the decade"

Resolution: **Drop**. No action, no specific stat, no specific framework.

## When in doubt

Default to **News**. It's the safest holding pen. Threats has the highest action-stakes (don't put non-urgent items there); Advice requires concrete recipes (don't put opinions there). News is for "the world changed, no immediate action required."
