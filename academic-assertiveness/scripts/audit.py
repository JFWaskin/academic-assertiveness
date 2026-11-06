#!/usr/bin/env python3
"""Read-only academic-prose triage (English, with a small Chinese rule set). Flags are review candidates, never
replacements: every candidate needs a contextual decision, and a zero-flag result certifies nothing.

Two kinds of detector run:
  lexical      phrase patterns from references/rules.json (defensive scope, metadiscourse, caution self-labels,
               stacked hedges, weak framing, vague quantifiers, overclaim, research-gap, Chinese rules)
  structural   R  a paragraph that stacks several disclaimers
               L  a paragraph that opens by saying what the work is not
               K  a sentence that clusters three or more hedges
               C  causal wording inside a sentence that reports an association
A document summary ranks paragraph hotspots and lists disclaimer wordings repeated across the document.

Inputs: .md .markdown .txt .tex, and .docx (accepted view: deleted text skipped, inserted text kept).
"""
import argparse
import bisect
import collections
import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / 'references/rules.json').read_text(encoding='utf-8'))
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# ---------------------------------------------------------------- structural detectors
DISCLAIM = re.compile(
    r"\b(?:does|do|did|can|could|would|will)\s*n[o']t\s+(?:\w+\s+)?(?:establish|identify|demonstrate|prove|show|imply|"
    r"justify|authori[sz]e|license|licence|diagnose|reveal|constitute|confirm|measure|label|separate|substitute|"
    r"reconstruct|determine|support\s+(?:a|an|the)\s+causal)\b"
    r"|\bcannot\s+(?:\w+\s+)?(?:establish|identify|demonstrate|prove|show|separate|justify|label|determine|reveal|"
    r"be\s+(?:read|treated|taken|interpreted))\b"
    r"|\b(?:is|are|was|were)\s+not\s+(?:\w+\s+)?(?:evidence|proof|causal|a\s+claim|a\s+substitute|a\s+demonstration|"
    r"a\s+direct|a\s+measure(?:ment)?|a\s+verified|a\s+validated)\b"
    r"|\brather\s+than\s+(?:as\s+)?(?:a\s+|an\s+)?(?:causal|direct|established|proof|demonstration|evidence|"
    r"confirm\w*|verified|validated)\b"
    r"|\b(?:only|merely|treated\s+only)\s+as\s+(?:\w+\s+)?(?:hypothesis-generating|descriptive|exploratory|"
    r"illustrat\w+|candidates?)\b"
    r"|\bhypothesis-generating\b|\bremains?\s+a\s+hypothesis\b"
    r"|\bshould\s+not\s+be\s+(?:read|taken|interpreted|treated)\b"
    r"|\bnot\s+(?:a|an)\s+(?:causal|direct|verified|validated)\b"
    r"|\bwithout\s+(?:treating|implying|claiming|turning|converting)\b"
    r"|\bnot\s+(?:yet\s+)?(?:established|demonstrated|proven|validated)\b", re.I)
HEDGE = re.compile(
    r"\b(?:may|might|could|possibly|perhaps|potentially|plausibly|presumably|probably|likely|apparently|arguably|"
    r"seems?|appears?|suggests?|tentative(?:ly)?|somewhat|conceivably)\b", re.I)
ASSOC = re.compile(r"\b(?:correlat\w*|associat\w*|co-?var\w*|linked\s+(?:to|with)|relationship\s+between)\b", re.I)
CAUSAL = re.compile(r"\b(?:causes?|caused|causing|leads?\s+to|led\s+to|drives?|drove|results?\s+in|determines?|"
                    r"produces?|brings?\s+about|is\s+responsible\s+for|because\s+of)\b", re.I)
NEG_NEAR = re.compile(r"\b(?:not|no|never|cannot|without|neither|nor)\b", re.I)
NEG_LEAD = re.compile(
    r"^(?:\W*)(?:(?:this|these|the|that|such|it|they|neither|none)\b(?:(?!\b(?:that|which|who|whom|whose)\b)[^.;:]){0,80}?"
    r"\b(?:is|are|was|were|does|do|did)\s+"
    r"(?:not|neither)\b|no\s+(?:claim|attempt|inference)\b|rather\s+than\b|it\s+is\s+not\b)", re.I)
STAT_RESULT = re.compile(r"\b(?:surviv\w*|significan\w*|correction|differ\w*|reach\w*|p\s*[=<>]|q\s*[=<>]|"
                         r"detectab\w*|effect\s+size|interval|confidence)\b", re.I)
SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+(?=[A-Z“\"(\u4e00-\u9fff])")

STRUCTURAL = {
    'R_REPEATED_DISCLAIMER': (2, "Several disclaimers in one paragraph. Keep the one that changes interpretation, merge "
                                 "or delete the rest, and lead with the finding."),
    'L_NEGATIVE_LEAD': (1, "Paragraph opens by saying what the work is not. Lead with what it does or shows; move the "
                           "limit after the claim if it is needed."),
    'K_HEDGE_CLUSTER': (2, "Three or more hedges in one sentence. Keep the hedge the evidence warrants and drop the "
                           "rest."),
    'C_CAUSAL_IN_ASSOCIATION': (3, "Causal wording in a sentence that reports an association. Check the design supports "
                                   "a causal reading."),
}


# ---------------------------------------------------------------- input
def read_docx(path):
    """Accepted-view paragraph texts of a .docx (w:del skipped, w:ins kept, tabs and breaks as spaces)."""
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    paras = []
    for p in root.iter(W + 'p'):
        ppr = p.find(W + 'pPr')
        mark = ppr.find(W + 'rPr') if ppr is not None else None
        if mark is not None and mark.find(W + 'del') is not None and not ''.join(
                t.text or '' for t in p.iter(W + 't')).strip():
            continue
        out = []
        parent = {c: q for q in p.iter() for c in q}

        def deleted(el):
            while el is not None and el is not p:
                if el.tag in (W + 'del', W + 'moveFrom'):
                    return True
                el = parent.get(el)
            return False
        for el in p.iter():
            if el.tag == W + 't' and not deleted(el):
                out.append(el.text or '')
            elif el.tag in (W + 'tab', W + 'br') and not deleted(el):
                out.append(' ')
        paras.append(''.join(out))
    return paras


def prose_view(text, suffix='.md', include_quotes=False, mask_inline_quotes=False):
    """Mask common non-prose while preserving every source offset and newline."""
    view = list(text)

    def hide(start, end):
        for i in range(start, end):
            if text[i] != '\n':
                view[i] = '\0'

    suffix = suffix.lower()
    if suffix in ('.md', '.markdown'):
        front = re.match(r'\A\ufeff?---[^\S\n]*\n.*?\n(?:---|\.\.\.)[^\S\n]*(?:\n|$)', text, re.S)
        if front:
            hide(*front.span())
        fence = None
        offset = 0
        for line in text.splitlines(keepends=True):
            marker = re.match(r' {0,3}(`{3,}|~{3,})(.*)', line)
            if fence:
                hide(offset, offset + len(line))
                if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                    fence = None
            elif marker:
                fence = (marker[1][0], len(marker[1]))
                hide(offset, offset + len(line))
            elif not include_quotes and re.match(r'\s*>', line):
                hide(offset, offset + len(line))
            elif line.startswith(('    ', '\t')):
                hide(offset, offset + len(line))
            offset += len(line)
        for m in re.finditer(r'<!--.*?(?:-->|\Z)', text, re.S):
            hide(*m.span())
        for m in re.finditer(r'(`+)[^\n]*?\1', text):
            hide(*m.span())
    if suffix == '.tex':
        for m in re.finditer(r'\\begin\{(verbatim\*?|lstlisting|minted|equation\*?|align\*?)\}.*?\\end\{\1\}', text, re.S):
            hide(*m.span())
        for m in re.finditer(r'(?<!\\)%[^\n]*', text):
            hide(*m.span())
        for m in re.finditer(r'\\verb(.).*?\1|(?<!\\)\$\$.*?(?<!\\)\$\$|(?<!\\)\$[^\n]*?(?<!\\)\$|\\\[.*?\\\]|\\\(.*?\\\)', text, re.S):
            hide(*m.span())
    if mask_inline_quotes:
        for m in re.finditer(r'“[^”\n]{1,400}”|"[^"\n]{1,400}"', text):
            hide(*m.span())
    return ''.join(view)


def skip_references(paras):
    """Index of the reference-list heading in the last 70% of the document, or len(paras)."""
    start = int(len(paras) * 0.3)
    for i in range(start, len(paras)):
        if paras[i].strip().lower() in ('references', 'bibliography', 'works cited', 'reference list', '参考文献'):
            return i
    return len(paras)


# ---------------------------------------------------------------- scanning
def _record(filename, text, starts, para_of, s, e, cat, instruction, severity):
    line_index = bisect.bisect_right(starts, s) - 1
    begin = text.rfind('\n', 0, s) + 1
    end = text.find('\n', e)
    end = len(text) if end == -1 else end
    return {'_span': (s, e), 'file': str(filename), 'line': line_index + 1, 'column': s - starts[line_index] + 1,
            'paragraph': para_of(s), 'category': cat, 'severity': severity, 'match': text[s:e][:240],
            'context': ' '.join(text[begin:end].split())[:500], 'instruction': instruction}


def scan_text(text, filename='<text>', include_negation=False, include_quotes=False, structural=True,
              mask_inline_quotes=False, disclaim_threshold=3, hedge_threshold=3):
    view = prose_view(text, Path(filename).suffix, include_quotes, mask_inline_quotes)
    starts = [0] + [m.end() for m in re.finditer('\n', text)]
    pstarts = [0] + [m.end() for m in re.finditer(r'\n[ \t]*\n', text)]

    def para_of(offset):
        return bisect.bisect_right(pstarts, offset)

    records = []
    for rule in RULES:
        if not rule.get('default', True) and not include_negation:
            continue
        seen = set()
        flags = 0 if rule['id'].startswith('Z_') else re.I
        for pattern in rule['patterns']:
            for m in re.finditer(pattern, view, flags):
                if m.span() in seen or m.start() == m.end():
                    continue
                seen.add(m.span())
                records.append(_record(filename, text, starts, para_of, m.start(), m.end(), rule['id'],
                                       rule['message'], rule.get('severity', 1)))
    if structural:
        records += structural_scan(text, view, filename, starts, pstarts, para_of, disclaim_threshold, hedge_threshold)
    return dedupe(records)


def dedupe(records):
    """Drop a lexical match nested inside a longer match of the same category in the same paragraph."""
    keep = []
    for r in records:
        s, e = r['_span'] if '_span' in r else (None, None)
        nested = s is not None and any(o is not r and o['category'] == r['category'] and o.get('_span')
                                       and o['_span'][0] <= s and e <= o['_span'][1]
                                       and (o['_span'][1] - o['_span'][0]) > (e - s) for o in records)
        if not nested:
            keep.append(r)
    for r in keep:
        r.pop('_span', None)
    return sorted(keep, key=lambda r: (r['file'], r['line'], r['column'], r['category']))


def structural_scan(text, view, filename, starts, pstarts, para_of, disclaim_threshold, hedge_threshold):
    out = []
    bounds = pstarts + [len(text)]
    for k in range(len(pstarts)):
        s, e = bounds[k], bounds[k + 1]
        para = view[s:e]
        if len(para.strip().replace('\0', '')) < 60:
            continue
        hits = list(DISCLAIM.finditer(para))
        if len(hits) >= disclaim_threshold:
            sev, msg = STRUCTURAL['R_REPEATED_DISCLAIMER']
            words = '; '.join(' '.join(h.group(0).split()) for h in hits)
            rec = _record(filename, text, starts, para_of, s + hits[0].start(), s + hits[0].end(),
                          'R_REPEATED_DISCLAIMER', f"{len(hits)} disclaimers ({words}). {msg}", sev)
            out.append(rec)
        lead = re.match(r'\s*', para).end()
        first = SENT_SPLIT.split(para[lead:], maxsplit=1)[0]
        m = NEG_LEAD.match(first)
        if m and not STAT_RESULT.search(first):     # a null result stated first is a finding, not a defensive lead
            sev, msg = STRUCTURAL['L_NEGATIVE_LEAD']
            out.append(_record(filename, text, starts, para_of, s + lead, s + lead + len(first),
                               'L_NEGATIVE_LEAD', msg, sev))
        offset = 0
        for sent in SENT_SPLIT.split(para):
            i = para.find(sent, offset)
            offset = i + len(sent)
            hedges = HEDGE.findall(sent)
            if len(hedges) >= hedge_threshold:
                sev, msg = STRUCTURAL['K_HEDGE_CLUSTER']
                out.append(_record(filename, text, starts, para_of, s + i, s + i + len(sent), 'K_HEDGE_CLUSTER',
                                   f"{len(hedges)} hedges ({', '.join(h.lower() for h in hedges)}). {msg}", sev))
            if ASSOC.search(sent):
                for c in CAUSAL.finditer(sent):
                    before = sent[max(0, c.start() - 40):c.start()]
                    if NEG_NEAR.search(before) or re.search(r'\bcausal|\bcaus(?:e|ation)\b', before, re.I):
                        continue
                    after = sent[c.end():c.end() + 6]
                    if re.match(r'(?:cause|causes)$', c.group(0), re.I) and (
                            re.search(r'\b(?:the|a|an|its|their|any|one|no)\s+(?:[\w-]+\s+){0,2}$', before, re.I)
                            or re.match(r'\s*(?:of\b|[.,;:)])', after)):
                        continue                    # noun use ("a psychological cause of"), not a causal claim
                    sev, msg = STRUCTURAL['C_CAUSAL_IN_ASSOCIATION']
                    out.append(_record(filename, text, starts, para_of, s + i + c.start(), s + i + c.end(),
                                       'C_CAUSAL_IN_ASSOCIATION', msg, sev))
                    break
    return out


# ---------------------------------------------------------------- reporting
def summary(rows, top=10):
    lines = []
    cats = collections.Counter(r['category'] for r in rows)
    lines.append('Flags by category: ' + ', '.join(f'{k} {v}' for k, v in cats.most_common()))
    weight = collections.Counter()
    ctx = {}
    for r in rows:
        key = (r['file'], r['paragraph'])
        weight[key] += r['severity']
        ctx.setdefault(key, r['context'][:110])
    lines.append(f'Paragraph hotspots (severity-weighted, top {top}):')
    for (f, p), w in weight.most_common(top):
        lines.append(f'  {Path(f).name} ¶{p}  weight {w}  {ctx[(f, p)]}…')
    stems = collections.Counter()
    for r in rows:
        if r['category'] == 'R_REPEATED_DISCLAIMER':
            for w in re.findall(r'\(([^)]*)\)', r['instruction'])[:1]:
                for d in w.split('; '):
                    stems[re.sub(r'\b(?:does|do|did)\b', 'do', d.lower())] += 1
    rep = [(s, n) for s, n in stems.most_common() if n >= 3]
    if rep:
        lines.append('Disclaimer wordings repeated across flagged paragraphs: ' +
                     ', '.join(f'"{s}" ×{n}' for s, n in rep[:12]))
    return '\n'.join(lines)


def load(path, mask_refs=True):
    """Return (text, suffix) for scanning. A .docx becomes blank-line-separated accepted paragraphs."""
    suffix = path.suffix.lower()
    if suffix == '.docx':
        paras = read_docx(path)
        if mask_refs:
            paras = paras[:skip_references(paras)]
        return '\n\n'.join(p.strip() for p in paras if p.strip()), '.txt'
    return path.read_text(encoding='utf-8-sig'), suffix


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text')
    parser.add_argument('--csv', type=Path, help='Write CSV report (legacy starter-kit option)')
    parser.add_argument('--include-negation', action='store_true', help='Add the broad N capability-negation rule')
    parser.add_argument('--include-quotes', action='store_true', help='Include Markdown block quotations')
    parser.add_argument('--mask-inline-quotes', action='store_true', help='Skip text inside inline quotation marks')
    parser.add_argument('--no-structural', action='store_true', help='Lexical rules only')
    parser.add_argument('--keep-references', action='store_true', help='.docx: also scan the reference list')
    parser.add_argument('--min-severity', type=int, default=1, choices=[1, 2, 3])
    parser.add_argument('--only', help='Comma-separated category prefixes to keep, e.g. D,S,R')
    parser.add_argument('--disclaimer-threshold', type=int, default=3)
    parser.add_argument('--hedge-threshold', type=int, default=3)
    parser.add_argument('--summary', action='store_true', help='Text format: print only the summary')
    parser.add_argument('--top', type=int, default=10, help='Number of paragraph hotspots in the summary')
    args = parser.parse_args()
    if args.csv and any(args.csv.resolve() == p.resolve() for p in args.files):
        parser.error('Report destination must not overwrite an input manuscript')
    rows = []
    for path in args.files:
        if path.suffix.lower() not in ('.md', '.txt', '.tex', '.markdown', '.docx'):
            parser.error(f'Extract document text first; unsupported extension: {path.suffix}')
        try:
            text, suffix = load(path, not args.keep_references)
        except (OSError, UnicodeError, zipfile.BadZipFile, KeyError, ET.ParseError):
            parser.error(f'Cannot read manuscript: {path}')
        name = str(path) if suffix == path.suffix.lower() else str(path) + suffix
        found = scan_text(text, name, args.include_negation, args.include_quotes, not args.no_structural,
                          args.mask_inline_quotes, args.disclaimer_threshold, args.hedge_threshold)
        for r in found:
            r['file'] = str(path)
        rows.extend(found)
    rows = [r for r in rows if r['severity'] >= args.min_severity]
    if args.only:
        keep = tuple(x.strip().upper() for x in args.only.split(','))
        rows = [r for r in rows if r['category'].startswith(keep)]
    rows.sort(key=lambda r: (r['file'], r['line'], r['column'], r['category']))
    fields = ['file', 'line', 'column', 'paragraph', 'category', 'severity', 'match', 'context', 'instruction']
    if args.csv or args.format == 'csv':
        output = args.csv.open('w', encoding='utf-8', newline='') if args.csv else sys.stdout
        try:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        finally:
            if args.csv:
                output.close()
    elif args.format == 'json':
        print(json.dumps({'advisory_only': True, 'findings': rows,
                          'summary': summary(rows, args.top).split('\n')}, ensure_ascii=False, indent=2))
    else:
        if not args.summary:
            for row in rows:
                print(f"{row['file']}:¶{row['paragraph']}:{row['line']}:{row['column']} [{row['category']}] "
                      f"{row['match'][:90]!r}: {row['instruction']}")
        print(summary(rows, args.top))
        print(f'Total advisory flags: {len(rows)}; overlapping categories count separately. No text changed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
