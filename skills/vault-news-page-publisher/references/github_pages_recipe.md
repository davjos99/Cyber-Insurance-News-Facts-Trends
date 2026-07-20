# GitHub Pages Recipe

Publish the daily cybersec briefing to a GitHub Pages site via git commits.

## Prerequisites

1. A GitHub Pages site already configured (any of: Jekyll, plain HTML, mkdocs, hugo, etc.)
2. A local clone of the repo with git already working (SSH key or PAT configured)
3. The Skill assumes you can run `git push` from the local repo without password prompts

## Setup (one-time)

### Pick your structure

The Skill supports two flavors:

**Flavor A — Jekyll-style** (recommended)

Briefings go in `_posts/` with filenames like `2026-05-27-cybersec-briefing.md`. Jekyll auto-renders them. Front-matter is added by the Skill.

**Flavor B — plain HTML**

The Skill writes `cybersec_briefing_2026-05-27.html` to a configured folder. You manage your own index page.

### Configure the Skill

Create `~/.cybersec-briefing/gh-pages-config.json`:

```json
{
  "repo_path": "/Users/you/code/my-blog",
  "flavor": "jekyll",
  "post_dir": "_posts",
  "front_matter": {
    "layout": "post",
    "categories": ["cybersec", "daily-brief"],
    "tags": ["security", "rss"]
  },
  "commit_message_template": "Cybersec briefing for {DATE}",
  "auto_push": true
}
```

For Flavor B (plain HTML), use:

```json
{
  "repo_path": "/Users/you/code/my-blog",
  "flavor": "html",
  "post_dir": "briefings",
  "commit_message_template": "Cybersec briefing for {DATE}",
  "auto_push": true
}
```

## Usage

```bash
python ~/.claude/skills/cybersec-news-page-publisher/scripts/publish_github_pages.py \
  --input /tmp/briefing.md \
  --config ~/.cybersec-briefing/gh-pages-config.json
```

The script:

1. Reads the config
2. Determines the destination path: `{repo_path}/{post_dir}/{date}-cybersec-briefing.md` (or `.html`)
3. Prepends front-matter (Jekyll) or wraps in HTML template
4. Writes the file
5. Runs `git -C {repo_path} add {destination}`
6. Runs `git -C {repo_path} commit -m "Cybersec briefing for 2026-05-27"`
7. Runs `git -C {repo_path} push origin <branch>` (if `auto_push: true`)

## Front-matter (Jekyll flavor)

```yaml
---
layout: post
title: "Cybersec Briefing — 2026-05-27"
date: 2026-05-27 08:00:00 +0000
categories: cybersec daily-brief
tags: security rss
excerpt: "Last 24h cybersec briefing — 3 threats, 4 news items, 4 advice."
---
```

## Common errors

### `fatal: not a git repository`
- `repo_path` in config is wrong, or the folder isn't actually a git repo

### `Permission denied (publickey)` on push
- SSH key isn't configured for the remote. Run `ssh -T git@github.com` to verify.
- Solution: configure SSH keys at https://github.com/settings/keys, then `git remote set-url origin git@github.com:USER/REPO.git`

### `! [rejected] main -> main (fetch first)`
- Someone else pushed to the branch between your last pull and now. The Skill does NOT auto-pull (to avoid clobbering local changes). Run `git pull --rebase` manually and re-run the Skill.

### `Push succeeded but Pages didn't rebuild`
- GitHub Pages can take 30-60 seconds to rebuild. Check the Actions tab for the build status.
- If Pages is configured to deploy from `/docs` instead of root, ensure `post_dir` is inside `/docs`.

## Branching strategy

The Skill commits to whichever branch is currently checked out. For Jekyll sites:

- Source branch (`main`): the Skill commits here, GitHub Actions builds + deploys to `gh-pages`
- Old-style sites: GitHub serves directly from `gh-pages` or `main` `/docs`

The Skill does NOT switch branches. If you're on a feature branch, the commit goes there. Switch to your publish branch before running.

## Security notes

- Briefings on GitHub Pages are PUBLIC. Anyone who finds your Pages URL can read them.
- If you need private briefings, use Notion or static HTML on a private machine. NOT GitHub Pages.
- The Skill does NOT redact source URLs. Anything the categorizer kept will be public.
- If you accidentally pushed a sensitive briefing, `git revert` + force-push is your friend (but anyone who already pulled has it; consider it leaked).

## When this recipe is NOT the right pick

- You want private briefings → use Notion
- You don't already have a Pages site → set up Netlify drag-and-drop with static HTML instead (zero git/setup)
- You don't want to learn git → use static HTML

## Custom build steps

If your Jekyll site has a custom plugin / theme that needs a build before deploy, the Skill doesn't trigger it. Rely on GitHub Actions to build on push, OR use a `post-commit` hook in the repo to run `jekyll build` locally.
