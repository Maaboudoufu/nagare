"""XP, levels, streaks and achievements. Kept in each user's progress under 'app:stats', which only the server writes."""
import collections, datetime, json, os, zoneinfo
from typing import Callable, NamedTuple

COURSES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'courses')
CATALOG = json.load(open(os.path.join(COURSES, 'index.json')))['courses']
COURSE_OF = {uuid: c for c in CATALOG for uuid in c['lessons']}

LOGIN_XP, COURSE_XP, DEFAULT_XP = 10, 250, 25
LESSON_XP = {'type_choice': 10, 'type_text_input': 15, 'type_interview_chat': 15}
TIER_XP = {'bronze': 25, 'silver': 50, 'gold': 100}
GROUPS = {'type_cli': 'terminal', 'type_shell': 'terminal', 'type_choice': 'quiz', 'type_code_tests': 'tests',
          'type_code': 'code', 'type_code_sql': 'sql', 'type_interview_chat': 'interview'}


def level(xp):
    """Level n starts at 50·n·(n-1) XP: 0, 100, 300, 600, 1000, ..."""
    n = 1
    while xp >= 50 * (n + 1) * n:
        n += 1
    return n


def done_lessons(prog, lessons):
    """{uuid: saved progress} for every lesson the user finished."""
    return {u: p for u, p in prog.items() if u in lessons and isinstance(p, dict) and p.get('done')}


def tally(prog, lessons):
    done = done_lessons(prog, lessons)
    t = {'lessons': len(done), 'terminal': 0, 'quiz': 0, 'tests': 0, 'code': 0, 'sql': 0, 'interview': 0}
    for u in done:
        g = GROUPS.get(lessons[u].get('type'))
        if g:
            t[g] += 1
    langs = collections.Counter(COURSE_OF[u]['language'] for u in done if u in COURSE_OF)
    t['languages'] = len(set(langs) - {'any'})
    t['lang'] = langs  # lessons per language: t['lang']['python']
    # Most lessons finished on one day. Date-only stamps are lessons from before XP existed (_stats): not counted.
    per_day = collections.Counter(p['doneAt'][:10] for p in done.values() if len(p.get('doneAt') or '') > 10)
    t['best_day'] = max(per_day.values(), default=0)
    finished = [c for c in CATALOG if c['lessons'] and all(u in done for u in c['lessons'])]
    t['courses'] = len(finished)
    t['projects'] = sum(c['slug'].startswith('build-') for c in finished)
    return t


class Achievement(NamedTuple):
    id: str
    name: str
    description: str
    tier: str
    value: Callable  # (tally, stats) -> how far along
    goal: int


ACHIEVEMENTS = [Achievement(*a) for a in [
    ('first-light', 'First Light', 'Complete your first lesson', 'bronze', lambda t, s: t['lessons'], 1),
    ('getting-warm', 'Getting Warm', 'Complete 10 lessons', 'bronze', lambda t, s: t['lessons'], 10),
    ('in-the-flow', 'In the Flow', 'Complete 50 lessons', 'silver', lambda t, s: t['lessons'], 50),
    ('riverbed', 'Carving the Riverbed', 'Complete 200 lessons', 'gold', lambda t, s: t['lessons'], 200),
    ('ripple', 'Ripple', 'Show up 3 days in a row', 'bronze', lambda t, s: s['best'], 3),
    ('steady-current', 'Steady Current', 'Show up 7 days in a row', 'silver', lambda t, s: s['best'], 7),
    ('tidal-force', 'Tidal Force', 'Show up 30 days in a row', 'gold', lambda t, s: s['best'], 30),
    ('headwaters', 'Headwaters', 'Finish a course', 'silver', lambda t, s: t['courses'], 1),
    ('confluence', 'Confluence', 'Finish 3 courses', 'gold', lambda t, s: t['courses'], 3),
    ('builder', 'Builder', 'Finish a project course', 'silver', lambda t, s: t['projects'], 1),
    ('shell-shocked', 'Shell Shocked', 'Complete 25 terminal lessons', 'silver', lambda t, s: t['terminal'], 25),
    ('sharp-eye', 'Sharp Eye', 'Answer 50 quizzes', 'silver', lambda t, s: t['quiz'], 50),
    ('test-pilot', 'Test Pilot', 'Pass 25 test-graded coding lessons', 'silver', lambda t, s: t['tests'], 25),
    ('query-crafter', 'Query Crafter', 'Complete 10 SQL lessons', 'bronze', lambda t, s: t['sql'], 10),
    ('polyglot', 'Polyglot', 'Complete lessons in 3 different languages', 'silver', lambda t, s: t['languages'], 3),
    ('night-owl', 'Night Owl', 'Complete a lesson between midnight and 4 a.m.', 'bronze', lambda t, s: s['flags'].get('night', 0), 1),
    ('early-bird', 'Early Bird', 'Complete a lesson between 4 and 7 a.m.', 'bronze', lambda t, s: s['flags'].get('early', 0), 1),
    ('deep-dive', 'Deep Dive', 'Earn 300 XP in one day', 'silver', lambda t, s: max(s['days'].values(), default=0), 300),
    ('make-it-yours', 'Make It Yours', 'Fill in your profile', 'bronze', lambda t, s: s['flags'].get('profile', 0), 1),
    ('rising', 'Rising', 'Reach level 5', 'silver', lambda t, s: level(s['xp']), 5),
    ('wellspring', 'Wellspring', 'Reach level 10', 'gold', lambda t, s: level(s['xp']), 10),
    ('deep-water', 'Deep Water', 'Complete 500 lessons', 'gold', lambda t, s: t['lessons'], 500),
    ('open-sea', 'Open Sea', 'Complete 1,000 lessons', 'gold', lambda t, s: t['lessons'], 1000),
    ('perennial', 'Perennial Stream', 'Show up 100 days in a row', 'gold', lambda t, s: s['best'], 100),
    ('watermark', 'Watermark', 'Be active on 30 different days', 'silver', lambda t, s: len(s['days']), 30),
    ('four-seasons', 'Four Seasons', 'Be active on 100 different days', 'gold', lambda t, s: len(s['days']), 100),
    ('delta', 'Delta', 'Finish 10 courses', 'gold', lambda t, s: t['courses'], 10),
    ('shipwright', 'Shipwright', 'Finish 3 project courses', 'gold', lambda t, s: t['projects'], 3),
    ('helmsman', 'Helmsman', 'Complete 100 terminal lessons', 'gold', lambda t, s: t['terminal'], 100),
    ('clear-water', 'Clear Water', 'Answer 200 quizzes', 'gold', lambda t, s: t['quiz'], 200),
    ('flight-hours', 'Flight Hours', 'Pass 100 test-graded coding lessons', 'gold', lambda t, s: t['tests'], 100),
    ('hello-world', 'Hello, World', 'Complete 10 output-checked coding lessons', 'bronze', lambda t, s: t['code'], 10),
    ('sounding-board', 'Sounding Board', 'Answer 10 interview questions', 'bronze', lambda t, s: t['interview'], 10),
    ('pythonista', 'Pythonista', 'Complete 100 Python lessons', 'silver', lambda t, s: t['lang']['python'], 100),
    ('gopher', 'Gopher', 'Complete 100 Go lessons', 'silver', lambda t, s: t['lang']['go'], 100),
    ('type-safe', 'Type Safe', 'Complete 100 TypeScript lessons', 'silver', lambda t, s: t['lang']['typescript'], 100),
    ('low-level', 'Low Level', 'Complete 25 C lessons', 'silver', lambda t, s: t['lang']['c'], 25),
    ('version-controlled', 'Version Controlled', 'Complete 25 Git lessons', 'bronze', lambda t, s: t['lang']['git'], 25),
    ('seven-seas', 'Seven Seas', 'Complete lessons in 7 different languages', 'gold', lambda t, s: t['languages'], 7),
    ('weekend-tide', 'Weekend Tide', 'Complete a lesson on a Saturday or Sunday', 'bronze', lambda t, s: s['flags'].get('weekend', 0), 1),
    ('flash-flood', 'Flash Flood', 'Complete 20 lessons in one day', 'silver', lambda t, s: t['best_day'], 20),
]]


def now_in(tz):
    try:
        return datetime.datetime.now(zoneinfo.ZoneInfo(tz or 'UTC'))
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return datetime.datetime.now(datetime.timezone.utc)


def _add_xp(s, n, why, today, events):
    """why: {'key': 'login' | 'lesson' | 'course' | 'achievement', ...params}; the UI words it in its language."""
    before = level(s['xp'])
    s['xp'] += n
    s['days'][today] = s['days'].get(today, 0) + n
    events.append({'kind': 'xp', 'xp': n, **why})
    if level(s['xp']) > before:
        events.append({'kind': 'level', 'level': level(s['xp'])})


def _unlock(prog, s, lessons, now, events):
    t = tally(prog, lessons)
    for _ in range(3):  # an unlock's XP can unlock a level achievement
        new = [a for a in ACHIEVEMENTS if a.id not in s['achievements'] and a.value(t, s) >= a.goal]
        for a in new:
            s['achievements'][a.id] = now.isoformat(timespec='seconds')
            events.append({'kind': 'achievement', 'id': a.id, 'name': a.name, 'tier': a.tier})
            _add_xp(s, TIER_XP[a.tier], {'key': 'achievement', 'name': a.name}, now.date().isoformat(), events)
        if not new:
            break


def lesson_xp(lesson):
    return LESSON_XP.get(lesson.get('type'), DEFAULT_XP)


def _stats(prog, lessons, now):
    """The user's stats, created on first use. Lessons finished before XP existed count, but not on the activity graph."""
    if 'app:stats' not in prog:
        today = now.date().isoformat()
        s = {'joined': today, 'xp': 0, 'days': {}, 'streak': 0, 'best': 0, 'last': None, 'achievements': {}, 'flags': {}}
        for u, p in done_lessons(prog, lessons).items():
            s['xp'] += lesson_xp(lessons[u])
            p['doneAt'] = today
        s['xp'] += COURSE_XP * tally(prog, lessons)['courses']
        prog['app:stats'] = s
    return prog['app:stats']


def tz_of(prog, fallback=None):
    return (prog.get('app:settings') or {}).get('tz') or fallback


def live_streak(prog):
    """The stored streak only counts while it's unbroken: last seen today or yesterday, in their time zone."""
    s, today = prog.get('app:stats') or {}, now_in(tz_of(prog)).date()
    return s.get('streak', 0) if s.get('last') in (today.isoformat(), (today - datetime.timedelta(days=1)).isoformat()) else 0


def login(prog, lessons, tz=None):
    """First visit of the day: login XP and the streak."""
    now = now_in(tz_of(prog, tz))
    events = []
    s = _stats(prog, lessons, now)
    today, yesterday = now.date().isoformat(), (now.date() - datetime.timedelta(days=1)).isoformat()
    if s['last'] != today:
        s['streak'] = s['streak'] + 1 if s['last'] == yesterday else 1
        s['best'] = max(s['best'], s['streak'])
        s['last'] = today
        _add_xp(s, LOGIN_XP, {'key': 'login', 'streak': s['streak']}, today, events)
    _unlock(prog, s, lessons, now, events)
    return events


def saved(prog, lessons, key, data):
    """After a progress save: XP for a newly finished lesson (and its course), then achievements."""
    now = now_in(tz_of(prog))
    events = []
    s = _stats(prog, lessons, now)
    today = now.date().isoformat()
    p = prog.get(key)
    if key in lessons and data.get('done') and not p.get('doneAt'):
        p['doneAt'] = now.isoformat(timespec='seconds')
        _add_xp(s, lesson_xp(lessons[key]), {'key': 'lesson'}, today, events)
        if now.hour < 4:
            s['flags']['night'] = 1
        elif now.hour < 7:
            s['flags']['early'] = 1
        if now.weekday() >= 5:
            s['flags']['weekend'] = 1
        course = COURSE_OF.get(key)
        if course and all((prog.get(u) or {}).get('done') for u in course['lessons']):
            _add_xp(s, COURSE_XP, {'key': 'course', 'title': course['title']}, today, events)
    if key == 'app:profile' and sum(bool(str(v).strip()) for v in p.values()) >= 3:
        s['flags']['profile'] = 1
    _unlock(prog, s, lessons, now, events)
    return events


def achievements(prog, lessons):
    s = _stats(prog, lessons, now_in(tz_of(prog)))
    t = tally(prog, lessons)
    return [{'id': a.id, 'name': a.name, 'description': a.description, 'tier': a.tier, 'goal': a.goal,
             'value': min(a.value(t, s), a.goal), 'unlocked': s['achievements'].get(a.id)} for a in ACHIEVEMENTS]


if __name__ == '__main__':
    lessons = {'a': {'type': 'type_code'}, 'b': {'type': 'type_choice'}}
    assert [level(x) for x in (0, 99, 100, 299, 300, 1000)] == [1, 1, 2, 2, 3, 5]
    prog = {'a': {'done': True}}
    ev = login(prog, lessons, 'America/Los_Angeles')
    s = prog['app:stats']
    assert s['streak'] == 1 and prog['a']['doneAt'] and 'first-light' in s['achievements'], s
    assert login(prog, lessons, 'America/Los_Angeles') == [] and s['streak'] == 1  # same day: nothing new
    prog['app:settings'] = {'tz': 'America/Los_Angeles'}
    prog['b'] = {'done': True}
    ev = saved(prog, lessons, 'b', {'done': True})
    assert ev[0] == {'kind': 'xp', 'xp': 10, 'key': 'lesson'}, ev
    assert saved(prog, lessons, 'b', {'done': True}) == []  # no XP twice for one lesson
    prog['app:profile'] = {'name': 'A', 'bio': 'b', 'location': 'c'}
    assert any(e.get('id') == 'make-it-yours' for e in saved(prog, lessons, 'app:profile', prog['app:profile']))
    s['last'] = (now_in(tz_of(prog, 'America/Los_Angeles')).date() - datetime.timedelta(days=1)).isoformat()
    login(prog, lessons, 'America/Los_Angeles')
    assert s['streak'] == 2 and live_streak(prog) == 2, s
    s['last'] = '2000-01-01'
    assert live_streak(prog) == 0  # broken streaks don't show
    t = tally({'a': {'done': True, 'doneAt': '2026-01-01T10:00:00'}, 'b': {'done': True, 'doneAt': '2026-01-01'}}, lessons)
    assert t['best_day'] == 1 and t['lang']['python'] == 0, t  # date-only stamps don't count toward a day
    medals = open(os.path.join(os.path.dirname(COURSES), 'web', 'src', 'assets', 'medals.svg')).read()
    assert not [a.id for a in ACHIEVEMENTS if f'<symbol id="{a.id}"' not in medals]  # every achievement has its glyph
    assert len({a.id for a in ACHIEVEMENTS}) == len(ACHIEVEMENTS)
    print('ok: gamify')
