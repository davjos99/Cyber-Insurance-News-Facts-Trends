#!/usr/bin/env python3
"""
orchestrate.py — run the three-Skill cybersec briefing chain.

Cross-platform. Used by Windows Task Scheduler and GitHub Actions.

Usage:
  python orchestrate.py [<config_path>]

Defaults config to ~/.cybersec-briefing/chain_config.json. If that doesn't
exist, falls back to the bundled assets/templates/chain_config.json.

Exit codes:
  0 — chain ran (regardless of soft failures)
  1 — hard failure (zero sources, halt_on_* tripped, etc.)
  2 — config / setup error
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[orchestrate] {msg}", file=sys.stderr)


def expand(p: str | None) -> Path | None:
    if p is None:
        return None
    return Path(os.path.expandvars(os.path.expanduser(p)))


def load_env_file(env_path: Path) -> None:
    """Source a .env file into os.environ — KEY=VALUE per line."""
    if not env_path.exists():
        log(f"WARN: env file not found, skipping: {env_path}")
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    log(f"Loaded env from {env_path}")


def run_step(name: str, cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    log(f"--- {name} ---")
    log(f"$ {' '.join(str(c) for c in cmd)}")
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    if p.stdout:
        for line in p.stdout.splitlines():
            log(f"    stdout: {line}")
    if p.stderr:
        for line in p.stderr.splitlines():
            log(f"    {line}")
    log(f"    [{name}] exit code: {p.returncode}")
    return p.returncode, p.stdout, p.stderr


def cleanup_old_runs(work_dir: Path, retain_days: int) -> None:
    if retain_days <= 0:
        return
    cutoff = time.time() - retain_days * 86400
    if not work_dir.exists():
        return
    for child in work_dir.iterdir():
        if not child.is_dir():
            continue
        if child.stat().st_mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            log(f"Cleaned old run: {child.name}")


def append_log_line(log_file: Path, line: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def main() -> int:
    # Load config
    if len(sys.argv) >= 2 and sys.argv[1]:
        cfg_path = expand(sys.argv[1])
    else:
        cfg_path = expand("~/.cybersec-briefing/chain_config.json")
        if not cfg_path.exists():
            # Fall back to bundled default
            cfg_path = Path(__file__).parent.parent / "assets" / "templates" / "chain_config.json"

    if not cfg_path.exists():
        log(f"ERROR: config not found: {cfg_path}")
        return 2

    log(f"Config: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    if cfg.get("version") != "1.0":
        log(f"ERROR: unsupported config version: {cfg.get('version')}")
        return 2

    # Resolve paths — robust for BOTH personal (~/.claude/skills) and project
    # (<folder>/.claude/skills) scope. The 3 sub-skills are siblings of this
    # orchestrator, so if the configured path is missing we resolve them relative
    # to this script's own skills dir. That makes "open the folder and run" work
    # with zero config edits, and tolerates folder-name drift in the config.
    sp = cfg["skill_paths"]
    SKILLS_HOME = Path(__file__).resolve().parents[2]  # .../.claude/skills
    SIBLINGS = {
        "fetcher": "vault-cybersec-news-fetcher",
        "categorizer": "vault-news-categorizer",
        "publisher": "vault-news-page-publisher",
    }

    def resolve_skill(role: str, configured) -> Path | None:
        d = expand(configured)
        if d and d.exists():
            return d
        sib = SKILLS_HOME / SIBLINGS[role]
        if sib.exists():
            log(f"{role}: resolved sibling skill at {sib}")
            return sib
        return d

    fetcher_dir = resolve_skill("fetcher", sp.get("fetcher"))
    categorizer_dir = resolve_skill("categorizer", sp.get("categorizer"))
    publisher_dir = resolve_skill("publisher", sp.get("publisher"))

    for name, d in [("fetcher", fetcher_dir), ("categorizer", categorizer_dir), ("publisher", publisher_dir)]:
        if not d or not d.exists():
            log(f"ERROR: {name} skill path missing: {d}")
            return 2

    work_root = expand(cfg["work_dir"])
    work_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    work_dir = work_root / run_id
    work_dir.mkdir(parents=True, exist_ok=True)
    log(f"Run dir: {work_dir}")

    raw_path = work_dir / "raw_news.json"
    deduped_path = work_dir / "deduped.json"
    briefing_path = work_dir / "briefing.md"

    sources_file = expand(cfg.get("fetcher", {}).get("sources_file")) or (fetcher_dir / "assets" / "templates" / "cybersec_sources.json")
    template_file = expand(cfg.get("categorizer", {}).get("template")) or (categorizer_dir / "assets" / "templates" / "briefing_template.md")
    window_hours = cfg.get("window_hours", 24)

    overall_ok = True
    publisher_results: list[str] = []

    # 1. Fetch
    rc, _, _ = run_step("FETCH", [
        sys.executable, fetcher_dir / "scripts" / "fetch_feeds.py",
        "--sources", sources_file,
        "--since", str(window_hours),
        "--output", raw_path,
    ])
    if rc != 0:
        log("Fetcher exited non-zero — halting chain")
        overall_ok = False
        return _finish(cfg, work_dir, work_root, run_id, "FAIL_FETCH", overall_ok, publisher_results)

    # Check for zero sources
    with raw_path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)
    if cfg.get("halt_on_zero_sources", True) and raw_data.get("sources_succeeded", 0) == 0:
        log("ZERO sources succeeded — halting (halt_on_zero_sources=true)")
        return _finish(cfg, work_dir, work_root, run_id, "FAIL_ZERO_SOURCES", False, publisher_results)

    # 2. Dedupe
    rc, _, _ = run_step("DEDUPE", [
        sys.executable, fetcher_dir / "scripts" / "dedupe.py",
        "--input", raw_path,
        "--output", deduped_path,
    ])
    if rc != 0:
        log("Dedupe exited non-zero — halting chain")
        return _finish(cfg, work_dir, work_root, run_id, "FAIL_DEDUPE", False, publisher_results)

    # 3. Categorize
    rc, _, _ = run_step("CATEGORIZE", [
        sys.executable, categorizer_dir / "scripts" / "categorize.py",
        "--input", deduped_path,
        "--output", briefing_path,
        "--template", template_file,
    ])
    if rc != 0:
        log("Categorizer exited non-zero — halting chain")
        return _finish(cfg, work_dir, work_root, run_id, "FAIL_CATEGORIZE", False, publisher_results)

    # 4. Validate
    rc, _, _ = run_step("VALIDATE", [
        sys.executable, categorizer_dir / "scripts" / "validate_briefing.py",
        briefing_path,
    ])
    if rc != 0 and cfg.get("halt_on_categorize_validation_fail", False):
        log("Validator failed AND halt_on_categorize_validation_fail=true — halting")
        return _finish(cfg, work_dir, work_root, run_id, "FAIL_VALIDATE", False, publisher_results)

    # 5. Publish (sequence)
    for pub_cfg in cfg.get("publishers", []):
        pub_type = pub_cfg["type"]
        pub_dest = pub_cfg.get("destination", "")
        # Expand env vars and ~
        pub_dest = os.path.expandvars(os.path.expanduser(pub_dest))
        env_file = pub_cfg.get("env_file")
        if env_file:
            load_env_file(expand(env_file))
        extra = pub_cfg.get("extra_args", [])
        script = publisher_dir / "scripts" / f"publish_{pub_type}.py"
        if not script.exists():
            log(f"ERROR: no such publisher script: {script}")
            publisher_results.append(f"{pub_type}:no_script")
            overall_ok = False
            if cfg.get("halt_on_publish_fail", False):
                return _finish(cfg, work_dir, work_root, run_id, "FAIL_PUBLISH", False, publisher_results)
            continue
        # GH Pages uses --config, not --output
        if pub_type == "github_pages":
            cmd = [sys.executable, script, "--input", briefing_path, "--config", pub_dest] + list(extra)
        else:
            cmd = [sys.executable, script, "--input", briefing_path, "--output", pub_dest] + list(extra)
        rc, _, _ = run_step(f"PUBLISH:{pub_type}", cmd)
        if rc == 0:
            publisher_results.append(f"{pub_type}:ok")
        else:
            publisher_results.append(f"{pub_type}:fail")
            overall_ok = False
            if cfg.get("halt_on_publish_fail", False):
                return _finish(cfg, work_dir, work_root, run_id, "FAIL_PUBLISH", False, publisher_results)

    return _finish(cfg, work_dir, work_root, run_id, "OK" if overall_ok else "PARTIAL", overall_ok, publisher_results)


def _finish(cfg, work_dir, work_root, run_id, status, ok, publisher_results) -> int:
    # Read counts from raw_news.json + deduped.json + briefing.md if they exist
    fetched = deduped = kept = 0
    raw_p = work_dir / "raw_news.json"
    if raw_p.exists():
        try:
            with raw_p.open("r", encoding="utf-8") as f:
                d = json.load(f)
            fetched = d.get("items_raw", 0)
        except Exception:
            pass
    ded_p = work_dir / "deduped.json"
    if ded_p.exists():
        try:
            with ded_p.open("r", encoding="utf-8") as f:
                d = json.load(f)
            deduped = d.get("items_after_dedupe", 0)
        except Exception:
            pass
    br_p = work_dir / "briefing.md"
    if br_p.exists():
        kept_line = next((line for line in br_p.read_text(encoding="utf-8").splitlines() if "kept" in line), "")
        import re as _re
        m = _re.search(r"(\d+)\s+kept", kept_line)
        if m:
            kept = int(m.group(1))

    log_file = expand(cfg.get("log_file", "~/.cybersec-briefing/runs.log"))
    if log_file:
        publishers_str = "[" + ",".join(publisher_results) + "]" if publisher_results else "[]"
        append_log_line(log_file, f"{run_id}  {status}  fetched={fetched} deduped={deduped} kept={kept} publishers={publishers_str}")

    # Cleanup old runs
    cleanup_old_runs(work_root, cfg.get("retain_runs_days", 30))

    log(f"=== {status} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
