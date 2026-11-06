# academic-assertiveness

An agent skill that makes academic prose direct without making it overconfident. It removes defensive
metadiscourse, redundant hedges, self-labelled caution and weak framing of a contribution, while keeping every
limitation, null result, number, citation and association/causation distinction that the evidence requires.

It ships as one portable skill folder in the `SKILL.md` format, so the same files run in three harnesses:

| Harness | Skill location | Activation | Hooks |
| --- | --- | --- | --- |
| **Claude Code** (Anthropic) | `~/.claude/skills/academic-assertiveness/` | `/academic-assertiveness`, or automatic from the description | optional `UserPromptSubmit` + `PreToolUse` reminder |
| **OpenAI Codex** | `~/.codex/skills/academic-assertiveness/` | `$academic-assertiveness`, or implicit (`agents/openai.yaml`) | optional, same hooks in `~/.codex/hooks.json` |
| **MiniMax Mini-Agent** | the `skills_dir` in Mini-Agent's `config.yaml` | selected from the description (Claude-skills loader) | none (Mini-Agent has no hook system) |

MiniMax models used through Claude Code or Codex (via their Anthropic- or OpenAI-compatible endpoints) pick the skill
up through those harnesses as well.

## Install

```bash
git clone https://github.com/JFWaskin/academic-assertiveness.git
cd academic-assertiveness
./install.sh all --hooks          # or: ./install.sh claude | codex | minimax  [--hooks] [--dest DIR]
```

`install.sh` copies the `academic-assertiveness/` folder into each harness's skills directory and, with `--hooks`,
merges two reminder hooks into Claude Code's `settings.json` and Codex's `hooks.json`. It keeps existing hooks,
writes a timestamped backup first, and is safe to re-run. `./install.sh claude --uninstall` removes the skill and
its hooks.

For Mini-Agent, point its config at the installed folder:

```yaml
# ~/.mini-agent/config/config.yaml
tools:
  enable_skills: true
  skills_dir: "~/.mini-agent/skills"   # the folder that contains academic-assertiveness/
```

Requirements: Python 3.10+ (standard library only), `bash`, and optionally `rsync`.

## Use

Ask for academic editing as usual, for example *"tighten this discussion section and remove defensive phrasing"*,
or invoke the skill explicitly (`/academic-assertiveness` in Claude Code, `$academic-assertiveness` in Codex). The
skill edits for:

* defensive scope and apologetic metadiscourse ("this study does not attempt to…")
* redundant or stacked hedges ("may possibly suggest")
* caution self-labels ("a cautious reading", "the defensible inference", "intentionally weaker")
* weak framing of the work's own contribution, vague quantifiers, overclaims, and unsupported novelty or gap claims

and it preserves claim polarity, negation scope, population and sample, all statistics, citations, warranted
uncertainty and the line between association and cause. See `academic-assertiveness/SKILL.md` and
`references/examples.md` for the full rules.

## The advisory scanner

`scripts/audit.py` is a read-only triage tool. It never edits a file. It reads `.md`, `.txt`, `.tex` and `.docx`
(the accepted view: tracked deletions skipped, insertions kept, reference list skipped).

```bash
python3 academic-assertiveness/scripts/audit.py thesis.docx --summary      # counts and paragraph hotspots
python3 academic-assertiveness/scripts/audit.py chapter.md --format json   # every candidate with paragraph numbers
python3 academic-assertiveness/scripts/audit.py paper.tex --only D,S,R --min-severity 2
```

| Code | Detects |
| --- | --- |
| D | defensive scope ("is not an admission", "does not overstate", "rather than answering it") |
| M | throat-clearing ("it is worth noting", "it should be stressed") |
| S | the text labelling its own caution ("a cautious account", "warrants a careful reading") |
| H | stacked hedges ("may possibly", "suggests that … might") |
| W | weak framing of a contribution ("one useful example", "suggests a direction rather than…") |
| V | vague quantifiers ("a number of", "somewhat") |
| O | overclaim ("conclusively proves", "it is clear that") |
| G | novelty or research-gap claims ("to our knowledge", "for the first time") |
| Z | Chinese rules (本文并不试图, 值得注意的是, 可能或许, 首次, 填补空白) |
| R | a paragraph stacking three or more disclaimers |
| L | a paragraph opening with what the work is not |
| K | three or more hedges in one sentence |
| C | causal wording in a sentence that reports an association |
| N | broad capability negation (`--include-negation`, off by default) |

The summary ranks paragraphs by severity-weighted flags and lists disclaimer wordings repeated across the document,
which is usually where a revision pays off most.

**Every flag is a review candidate, not a verdict.** Many R and L flags mark limitations that should stay; the
editorial decision is to keep the disclaimer that changes interpretation and cut the repetition around it. A
zero-flag result certifies nothing.

## Tests

```bash
python3 academic-assertiveness/scripts/test_audit.py
```

The regression set holds defensive passages that must be flagged and warranted limitations, null results and neutral
reports that must not be, plus checks of `.docx` reading and reference-list skipping. CI runs it on every push.

On the master's thesis the rules were tuned on (about 900 paragraphs), the scanner flagged all 25 passages an editor
revised for assertiveness, with 49 flags in total. That is a single-document, single-discipline result; precision and
recall on other fields are untested. Please add misses and false positives from your own texts to `test_audit.py`.

## Layout

```
academic-assertiveness/          the skill (copy this folder into any SKILL.md-compatible harness)
  SKILL.md                       instructions, read by Claude Code, Codex and Mini-Agent
  agents/openai.yaml             Codex display name, default prompt, implicit-invocation policy
  references/                    rules.json, calibration examples, review protocol
  scripts/audit.py               advisory scanner
  scripts/activate.py            hook: reminds the agent to apply the skill on academic-writing prompts and edits
  scripts/test_audit.py          regression tests
install.sh                       installer for claude | codex | minimax | all
tools/install_hooks.py           idempotent hook merge/removal for Claude Code and Codex
```

## License

MIT. See `LICENSE`.
