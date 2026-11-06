#!/usr/bin/env python3
"""Add (or remove) the academic-assertiveness activation hooks in a Claude Code or Codex hooks file.

Usage: install_hooks.py SETTINGS_JSON ACTIVATE_PY [--remove]

Claude Code keeps hooks in ~/.claude/settings.json; Codex keeps them in ~/.codex/hooks.json. Both use the same
shape: {"hooks": {"UserPromptSubmit": [{"hooks": [...]}], "PreToolUse": [{"matcher": ..., "hooks": [...]}]}}.
Existing entries are preserved; entries already pointing at an activate.py of this skill are replaced, so the
script is idempotent. A timestamped backup is written before any change.
"""
import json
import shutil
import sys
import time
from pathlib import Path

MARK = 'academic-assertiveness/scripts/activate.py'


def ours(group):
    return any(MARK in (h.get('command') or '') for h in group.get('hooks', []))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    settings, activate = Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser().resolve()
    remove = '--remove' in sys.argv[3:]
    data = json.loads(settings.read_text(encoding='utf-8')) if settings.exists() and settings.read_text().strip() else {}
    if settings.exists():
        shutil.copy2(settings, settings.with_name(settings.name + f'.bak-{time.strftime("%Y%m%d%H%M%S")}'))
    hooks = data.setdefault('hooks', {})
    command = f'"{sys.executable}" "{activate}"' if ' ' in sys.executable + str(activate) else f'{sys.executable} {activate}'
    entry = {'type': 'command', 'command': command, 'timeout': 5}
    wanted = {'UserPromptSubmit': {'hooks': [entry]},
              'PreToolUse': {'matcher': 'Write|Edit|MultiEdit|apply_patch', 'hooks': [entry]}}
    for event, group in wanted.items():
        kept = [g for g in hooks.get(event, []) if not ours(g)]
        hooks[event] = kept if remove else kept + [group]
        if not hooks[event]:
            del hooks[event]
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(('removed from ' if remove else 'hooks installed in ') + str(settings))


if __name__ == '__main__':
    main()
