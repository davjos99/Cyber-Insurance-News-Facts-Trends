#!/usr/bin/env bash
# orchestrate.sh — Bash wrapper for the cybersec briefing chain.
#
# Used by cron / launchd / systemd. Delegates the actual work to orchestrate.py
# so we get one source of truth — bash is just the trigger.
#
# Usage:
#   orchestrate.sh [<config_path>]
#
# Defaults config to ~/.cybersec-briefing/chain_config.json.

set -u
# NOTE: we intentionally do NOT use 'set -e' — failures in individual sub-skills
# are handled by orchestrate.py (which has the halt_on_* logic). Bash should
# never short-circuit before orchestrate.py decides.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="${1:-${HOME}/.cybersec-briefing/chain_config.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Resolve python3 — fall back to python on systems that only have python in PATH
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "ERROR: no python3 or python in PATH" >&2
        exit 2
    fi
fi

echo "[orchestrate.sh] $(date -u +%Y-%m-%dT%H:%M:%SZ) starting chain"
echo "[orchestrate.sh] python: $(command -v ${PYTHON_BIN})"
echo "[orchestrate.sh] config: ${CONFIG}"

"${PYTHON_BIN}" "${SCRIPT_DIR}/orchestrate.py" "${CONFIG}"
RC=$?

echo "[orchestrate.sh] $(date -u +%Y-%m-%dT%H:%M:%SZ) chain finished with exit ${RC}"
exit "${RC}"
