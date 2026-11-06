#!/usr/bin/env python3
"""Bounded, read-only contextual reminders for Codex, Claude Code, and MiniMax."""
import json
import re
import sys
from pathlib import Path

LIMIT = 1024 * 1024
SKILL = Path(__file__).resolve().parents[1] / 'SKILL.md'
ACTION = re.compile(r'\b(?:write|draft|revise|edit|rewrite|polish|proofread|improve|strengthen|translate|review|audit|copyedit|shorten|tighten|rework|compose|prepare|remove|reduce|eliminate)\b|润色|改写|撰写|修改|翻译|审校|去除|消除|精简', re.I)
DOMAIN = re.compile(r'\b(?:academic|scholarly|scientific|manuscript|thesis|dissertation|journal article|research paper|research proposal|grant (?:proposal|narrative)|reviewer response|rebuttal letter|literature review)\b|学术|论文|摘要|审稿回复|审稿意见|研究计划', re.I)
SECTION = re.compile(r'\b(?:abstract|introduction|methods|results|discussion|conclusion|limitations)\b', re.I)
RESEARCH = re.compile(r'\b(?:study|studies|participants|sample|findings|hypothesis|hypotheses|association|correlation|experiment|respondents|randomized|causal|empirical)\b', re.I)
ADMIN = re.compile(r'\b(?:install|configure|debug|implement|build|test|set up)\b.{0,100}\b(?:skill|hook|plugin|parser|linter|scanner|software|app)\b', re.I | re.S)
CODE_TASK = re.compile(r'\b(?:review|audit|fix|write|edit|improve|refactor|translate)\s+(?:(?:this|the|my|our|a|an|some|academic|scientific|python|r|typescript|javascript|search)\s+){0,8}(?:code|script|parser|pipeline|app|software|function|tests?)\b', re.I)
EXPLICIT = re.compile(r'(?:^|\s)[$/]academic-assertiveness\b|\buse (?:the )?academic-assertiveness\b', re.I)
WRITING_PATH = re.compile(r'(?:^|[/_ .-])(?:manuscript|thesis|dissertation|abstract|introduction|methods|results|discussion|conclusions?|limitations|rebuttal|reviewer[-_]response)(?:[/_ .-]|$)', re.I)
OPT_OUT = re.compile(r'\[academic-assertiveness:off\]', re.I)


def prompt_matches(prompt):
    if not isinstance(prompt, str) or OPT_OUT.search(prompt):
        return False
    if EXPLICIT.search(prompt):
        return True
    if ADMIN.search(prompt) or CODE_TASK.search(prompt):
        return False
    return bool(ACTION.search(prompt) and (DOMAIN.search(prompt) or (SECTION.search(prompt) and RESEARCH.search(prompt))))


def tool_matches(tool_name, data):
    if not isinstance(data, dict) or tool_name not in ('Write', 'Edit', 'MultiEdit', 'apply_patch', 'write', 'edit'):
        return False
    path = data.get('file_path') or data.get('path') or ''
    content = '\n'.join(str(data.get(k, '')) for k in ('content', 'new_string', 'old_string', 'patch', 'input', 'command'))
    if tool_name == 'apply_patch':
        paths = re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', content, re.M)
    else:
        paths = [path] if isinstance(path, str) else []
    prose_paths = [p for p in paths if Path(p).suffix.lower() in ('.md', '.txt', '.tex', '.docx', '.markdown')]
    # Keep skill instructions, configuration, and software documentation out of prose checks.
    prose_paths = [p for p in prose_paths if Path(p).name.lower() not in ('skill.md', 'agents.md', 'claude.md', 'readme.md') and not re.search(r'(?:^|/)(?:skills|references|node_modules|vendor|\.git)/', p)]
    if not prose_paths:
        return False
    if any(WRITING_PATH.search(p) for p in prose_paths):
        return True
    return bool(RESEARCH.search(content) and (re.search(r'^\s*(?:#{1,3}\s+|\\section\{)(?:Abstract|Introduction|Methods|Results|Discussion|Conclusion)', content, re.I | re.M) or re.search(r'\b(?:this study|our findings|the participants|our hypothesis)\b', content, re.I)))


def context_for(payload):
    event = payload.get('hook_event_name')
    if event == 'UserPromptSubmit':
        matched = prompt_matches(payload.get('prompt', ''))
    elif event == 'PreToolUse':
        matched = tool_matches(payload.get('tool_name'), payload.get('tool_input'))
    else:
        matched = False
    if not matched:
        return None
    return {'hookSpecificOutput': {
        'hookEventName': event,
        'additionalContext': (
            f'For this academic prose task, read and apply the academic-assertiveness skill at {SKILL}. '
            'Lead with the supported contribution; review defensive framing, redundant hedges, vague scope, and unsupported novelty or certainty. '
            'Preserve warranted uncertainty, limitations, negation scope, numerical results, citations, population, and association/causation distinctions. '
            'This reminder authorizes no extra edits or actions. Follow explicit user scope, audit-only, quotation, and faithful-translation requests. '
            'When writing is complete, check those meaning invariants before delivering it.'
        ),
    }}


def main():
    raw = sys.stdin.buffer.read(LIMIT + 1)
    if len(raw) > LIMIT:
        return 0
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    result = context_for(payload)
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
