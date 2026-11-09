"""Checks a course translation against the English course: nothing a lesson needs to work may change.
Code blocks, inline code, links/image URLs and callout markers ([!tip] etc.) must be identical; quizzes keep the same
number of answers; every lesson of the checked chapters is present and non-empty.

Usage: python3 tools/check_course_translation.py SLUG TRANSLATION.json [--chapters 0,1,2]
TRANSLATION.json: {"chapters": {"<index>": "title"}, "lessons": {"<uuid>": {"title", "readme", "prompt"?, "questions"?:
[{"question", "answers": [...]}]}}, "title"?, "description"?}"""
import json, os, re, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENCE = re.compile(r'```.*?```', re.S)
INLINE = re.compile(r'`[^`\n]+`')
URL = re.compile(r'\]\(\s*<?([^)\s>]+)')
CALLOUT = re.compile(r'\[![\w]+\]')


def parts(md):
    md = md or ''
    rest = FENCE.sub('', md)
    return {'code blocks': FENCE.findall(md), 'inline code': sorted(INLINE.findall(rest)),
            'links': sorted(URL.findall(rest)), 'callouts': CALLOUT.findall(rest)}


def check(slug, tr, chapters=None):
    course = json.load(open(os.path.join(ROOT, 'courses', f'{slug}.json')))
    problems = []
    for ci, ch in enumerate(course['chapters']):
        if chapters is not None and ci not in chapters:
            continue
        if not (tr.get('chapters') or {}).get(str(ci), '').strip():
            problems.append(f'chapter {ci}: missing title')
        for l in ch['lessons']:
            t = (tr.get('lessons') or {}).get(l['uuid'])
            where = f'{l["uuid"]} ({l["title"]})'
            if not t or not t.get('title', '').strip() or not t.get('readme', '').strip():
                problems.append(f'{where}: missing title or readme')
                continue
            for name, want in parts(l['readme']).items():
                if parts(t['readme'])[name] != want:
                    problems.append(f'{where}: {name} differ')
            if l.get('prompt') and not (t.get('prompt') or '').strip():
                problems.append(f'{where}: missing prompt')
            for qi, q in enumerate(l.get('questions') or []):
                tq = (t.get('questions') or [None] * (qi + 1))[qi] if qi < len(t.get('questions') or []) else None
                if not tq or len(tq.get('answers') or []) != len(q['answers']) or not tq.get('question', '').strip():
                    problems.append(f'{where}: question {qi} missing or wrong answer count')
                    continue
                for name, want in parts(q['question']).items():
                    if parts(tq['question'])[name] != want:
                        problems.append(f'{where}: question {qi} {name} differ')
                for ai, a in enumerate(q['answers']):
                    if Counter(INLINE.findall(a)) != Counter(INLINE.findall(tq['answers'][ai])):
                        problems.append(f'{where}: question {qi} answer {ai} inline code differs')
    return problems


if __name__ == '__main__':
    slug, path = sys.argv[1], sys.argv[2]
    chapters = None
    if '--chapters' in sys.argv:
        chapters = {int(x) for x in sys.argv[sys.argv.index('--chapters') + 1].split(',')}
    problems = check(slug, json.load(open(path)), chapters)
    for p in problems:
        print(p)
    print(f'{len(problems)} problems')
    sys.exit(1 if problems else 0)
