#!/usr/bin/env bash
# Install the academic-assertiveness skill for Claude Code, OpenAI Codex and/or MiniMax Mini-Agent.
#
#   ./install.sh claude            # ~/.claude/skills/academic-assertiveness
#   ./install.sh codex             # ${CODEX_HOME:-~/.codex}/skills/academic-assertiveness
#   ./install.sh minimax           # ${MINI_AGENT_SKILLS:-~/.mini-agent/skills}/academic-assertiveness
#   ./install.sh all --hooks       # all three, plus activation hooks for Claude Code and Codex
#   ./install.sh claude --uninstall
#
# Options
#   --hooks       also register the prompt/edit reminder hooks (Claude Code and Codex; Mini-Agent has no hooks)
#   --dest DIR    install the skill folder into DIR instead of the harness default (single target only)
#   --uninstall   remove the skill folder and its hooks
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/academic-assertiveness"
NAME=academic-assertiveness
PY="${PYTHON:-python3}"
HOOKS=0; UNINSTALL=0; DEST=""; TARGETS=()

while [ $# -gt 0 ]; do
  case "$1" in
    claude|codex|minimax) TARGETS+=("$1") ;;
    all) TARGETS+=(claude codex minimax) ;;
    --hooks) HOOKS=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --dest) DEST="$2"; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
[ ${#TARGETS[@]} -gt 0 ] || { sed -n '2,15p' "$0"; exit 2; }
[ -z "$DEST" ] || [ ${#TARGETS[@]} -eq 1 ] || { echo "--dest needs exactly one target" >&2; exit 2; }
command -v "$PY" >/dev/null || { echo "python3 is required (set PYTHON=...)" >&2; exit 1; }

skills_dir() {
  case "$1" in
    claude)  echo "${CLAUDE_HOME:-$HOME/.claude}/skills" ;;
    codex)   echo "${CODEX_HOME:-$HOME/.codex}/skills" ;;
    minimax) echo "${MINI_AGENT_SKILLS:-$HOME/.mini-agent/skills}" ;;
  esac
}
hooks_file() {
  case "$1" in
    claude) echo "${CLAUDE_HOME:-$HOME/.claude}/settings.json" ;;
    codex)  echo "${CODEX_HOME:-$HOME/.codex}/hooks.json" ;;
    *)      echo "" ;;
  esac
}

for t in "${TARGETS[@]}"; do
  dir="${DEST:-$(skills_dir "$t")}/$NAME"
  hf="$(hooks_file "$t")"
  if [ "$UNINSTALL" = 1 ]; then
    [ -n "$hf" ] && [ -f "$hf" ] && "$PY" "$SRC/../tools/install_hooks.py" "$hf" "$dir/scripts/activate.py" --remove
    rm -rf "$dir" && echo "[$t] removed $dir"
    continue
  fi
  mkdir -p "$dir"
  if command -v rsync >/dev/null; then
    rsync -a --delete --exclude __pycache__ --exclude .DS_Store "$SRC/" "$dir/"
  else
    rm -rf "$dir" && cp -R "$SRC" "$dir"
  fi
  echo "[$t] skill installed in $dir"
  if [ "$HOOKS" = 1 ]; then
    if [ -n "$hf" ]; then
      "$PY" "$SRC/../tools/install_hooks.py" "$hf" "$dir/scripts/activate.py"
    else
      echo "[$t] Mini-Agent has no hook system; the skill is selected from its description."
    fi
  fi
  if [ "$t" = minimax ]; then
    cat <<EOF
[$t] In Mini-Agent's config.yaml (e.g. ~/.mini-agent/config/config.yaml) set:
        tools:
          enable_skills: true
          skills_dir: "$(dirname "$dir")"
EOF
  fi
done
"$PY" "$SRC/scripts/test_audit.py" >/dev/null 2>&1 && echo "self-test passed" || echo "self-test FAILED: run $PY $SRC/scripts/test_audit.py"
