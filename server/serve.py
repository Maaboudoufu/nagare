"""The app worker: the /api behind the Go gateway (gateway/main.go), which signs people in and passes the user
as X-User. Code runs, CLI checks and terminals happen in that user's own container (workspace.py); progress is
saved per user in data/progress/<user>.json. The gateway serves the pages, course data and media itself.
Self-check: python3 server/serve.py --check  (re-submits your saved code, tests the CLI grader)"""
import datetime, functools, glob, hmac, json, os, signal, sys, tempfile, threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
import gamify, grader, terminal, workspace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
COURSES = os.path.join(ROOT, 'courses')
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(ROOT, 'data'))
PROGRESS_DIR = os.path.join(DATA_DIR, 'progress')
INTERNAL_TOKEN = os.environ.get('INTERNAL_TOKEN', '')  # from the gateway, for /internal/ calls only it makes
MAX_BODY = 1 << 20  # bytes; a save is one lesson's code or answers
lock = threading.Lock()  # ponytail: one lock for every user's progress file; per-user locks if saves ever queue up


def read_json(path):
    with open(path) as f:
        return json.load(f)


LESSONS = {l['uuid']: l
           for p in glob.glob(os.path.join(COURSES, '*.json')) if not p.endswith('index.json')
           for ch in read_json(p)['chapters'] for l in ch['lessons']}

# Lesson titles in other languages (courses/<lang>/<slug>.json), for activity lists in the reader's language.
TITLES = {}
for p in glob.glob(os.path.join(COURSES, '*', '*.json')):
    lang, name = os.path.basename(os.path.dirname(p)), os.path.basename(p)
    if name != 'index.json' and lang.isalpha() and len(lang) <= 3:
        TITLES.setdefault(lang, {}).update(
            {u: l['title'] for u, l in read_json(p).get('lessons', {}).items() if l.get('title')})


def progress_path(user):
    return os.path.join(PROGRESS_DIR, f'{user}.json')


def load_progress(user):
    try:
        return read_json(progress_path(user))
    except FileNotFoundError:
        return {}


def update_progress(user, fn):
    """Load, change with fn(prog), save; returns the progress and fn's result."""
    with lock:
        prog = load_progress(user)
        out = fn(prog)
        os.makedirs(PROGRESS_DIR, exist_ok=True)
        tmp = progress_path(user) + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(prog, f, indent=1)
        os.replace(tmp, progress_path(user))  # never leave a half-written file
        return prog, out


def save_progress(user, key, data):
    data = {k: v for k, v in data.items() if k != 'doneAt'}  # set by the server only
    def apply(prog):
        prog.setdefault(key, {}).update(data)
        return gamify.saved(prog, LESSONS, key, data)
    return update_progress(user, apply)


def members():
    """Everyone who has signed in (data/users.json, written by the gateway): {id: {name, picture, banned, ...}}."""
    try:
        return read_json(os.path.join(DATA_DIR, 'users.json'))
    except (FileNotFoundError, ValueError):
        return {}


def parts(prog):
    """A progress file's stats, settings and profile."""
    return prog.get('app:stats') or {}, prog.get('app:settings') or {}, prog.get('app:profile') or {}


def public_fields(prog, member):
    """What any signed-in member may see of another in a list. Never their email or code."""
    stats, settings, profile = parts(prog)
    return {'name': profile.get('name') or member.get('name') or '', 'handle': profile.get('handle', ''),
            'picture': member.get('picture', '') if settings.get('photo', True) else '',
            'level': gamify.level(stats.get('xp', 0)), 'streak': gamify.live_streak(prog),
            'lessons': len(gamify.done_lessons(prog, LESSONS))}


def public_profile(me, uid, lang='en'):
    """A member's profile page: the public fields plus XP, activity, course progress and achievements.
    None (404) for unknown or banned members, or ones who hid their profile (Settings)."""
    if uid == 'me':
        uid = me
    if not workspace.USER_ID.match(uid or ''):
        return None
    member, prog = members().get(uid, {}), load_progress(uid)
    stats, settings, profile = parts(prog)
    if not stats or member.get('banned') or (uid != me and settings.get('publicProfile') is False):
        return None
    done = gamify.done_lessons(prog, LESSONS)
    languages = {}
    for u in done:
        code = gamify.COURSE_OF.get(u, {}).get('language')
        if code and code != 'any':
            languages[code] = languages.get(code, 0) + 1
    recent = sorted(((p['doneAt'], u) for u, p in done.items() if p.get('doneAt')), reverse=True)[:6]
    titles = TITLES.get(lang, {})
    return {**public_fields(prog, member), 'id': uid, 'self': uid == me,
            **{k: profile.get(k, '') for k in ('bio', 'location', 'website', 'github')},
            'xp': stats.get('xp', 0), 'best': stats.get('best', 0), 'joined': stats.get('joined'),
            'days': stats.get('days', {}), 'languages': languages,
            'courses': [{'slug': c['slug'], 'done': n, 'total': len(c['lessons'])}
                        for c in gamify.CATALOG if (n := sum(u in done for u in c['lessons']))],
            'recent': [{'uuid': u, 'slug': gamify.COURSE_OF.get(u, {}).get('slug'), 'at': at,
                        'title': titles.get(u) or LESSONS[u]['title']} for at, u in recent],
            'achievements': gamify.achievements(prog, LESSONS)}


# ponytail: reads every progress file per request; cache it if there are ever thousands of users
def leaderboard(me, period):
    """Everyone who hasn't opted out (Settings) or been banned, ranked by XP: all time, or the last 7 or 30 days."""
    known = members()
    days = {'week': 7, 'month': 30}.get(period)
    rows = []
    for path in glob.glob(os.path.join(PROGRESS_DIR, '*.json')):
        uid = os.path.basename(path)[:-len('.json')]
        member = known.get(uid, {})
        try:
            prog = read_json(path)
        except ValueError:
            continue
        stats, settings, _ = parts(prog)
        hidden = settings.get('leaderboard') is False
        if not stats or member.get('banned') or (hidden and uid != me):
            continue
        xp = stats.get('xp', 0)
        if days:  # counted in their days, like their activity graph
            since = (gamify.now_in(gamify.tz_of(prog)).date() - datetime.timedelta(days=days - 1)).isoformat()
            xp = sum(v for day, v in stats.get('days', {}).items() if day >= since)
        rows.append({**public_fields(prog, member), 'xp': xp, 'you': uid == me, 'hidden': hidden,
                     # links to their profile, unless they hid it
                     'id': uid if uid == me or settings.get('publicProfile') is not False else None})
    rows.sort(key=lambda r: (-r['xp'], -r['lessons'], r['name'].lower()))  # the UI names nameless rows
    for i, r in enumerate(rows):
        r['rank'] = i + 1
    return [r for r in rows if r['rank'] <= 50 or r['you']]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def user(self):
        """Set by the gateway from the signed-in account; 'local' when there's no sign-in."""
        u = self.headers.get('X-User', 'local')
        return u if workspace.USER_ID.match(u) else None

    def send_json(self, res, status=200):
        data = json.dumps(res).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def trusted(self):
        """Only this app's own pages may use it: blocks other websites (CSRF) and DNS rebinding."""
        port = self.server.server_address[1]
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        return host in (f'localhost:{port}', f'127.0.0.1:{port}') and origin in (None, f'http://{host}')

    def do_GET(self):
        if not self.trusted():
            return self.send_error(403)
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        arg = lambda name, default=None: query.get(name, [default])[0]
        user = self.user()
        if not user:
            return self.send_error(400)
        if url.path == '/api/term':
            return terminal.serve(self, query, user)
        if url.path == '/api/progress':  # the app's first call: start their workspace meanwhile
            threading.Thread(target=workspace.warm, args=(user,), daemon=True).start()
            prog, events = update_progress(user, lambda p: gamify.login(p, LESSONS, arg('tz')))
            return self.send_json({**prog, 'app:events': events})  # app:events isn't saved
        if url.path == '/api/leaderboard':
            return self.send_json(leaderboard(user, arg('period', 'all')))
        if url.path.startswith('/api/profile/'):
            profile = public_profile(user, url.path[len('/api/profile/'):], arg('lang', 'en'))
            return self.send_json(profile) if profile else self.send_error(404)
        if url.path == '/api/achievements':
            return self.send_json(gamify.achievements(load_progress(user), LESSONS))
        self.send_error(404)

    def read_body(self):
        """The request's JSON object, or None if it's too big or isn't one."""
        size = int(self.headers.get('Content-Length') or 0)
        if size > MAX_BODY:
            return None
        try:
            body = json.loads(self.rfile.read(size) or b'{}')
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    def do_POST(self):
        if not self.trusted():
            return self.send_error(403)
        user, body = self.user(), self.read_body()
        if not user or body is None:
            return self.send_error(400)
        if self.path == '/internal/kick':  # never reachable through the gateway's /api/ proxy
            if not INTERNAL_TOKEN or not hmac.compare_digest(self.headers.get('X-Internal-Token', ''), INTERNAL_TOKEN):
                return self.send_error(403)
            if workspace.USER_ID.match(str(body.get('user'))):
                threading.Thread(target=workspace.remove_user, args=(body['user'],), daemon=True).start()
            return self.send_json({'ok': True})
        uuid, lesson = body.get('uuid'), None
        if isinstance(uuid, str):
            lesson = LESSONS.get(uuid)
        try:
            if self.path == '/api/run' and lesson and 'files' in lesson:
                code = body.get('code') if isinstance(body.get('code'), dict) else {}
                res = workspace.workspace(user).call({'op': 'run', 'lesson': lesson, 'code': code,
                                                      'submit': bool(body.get('submit'))})
            elif self.path == '/api/cli' and lesson and 'cli' in lesson:
                box = workspace.workspace(user)
                if body.get('aws'):
                    box.start_aws()
                res = box.call({'op': 'cli', 'steps': lesson['cli'], 'dir': workspace.user_path(body.get('dir')),
                                'baseURL': body.get('baseURL') or lesson.get('baseURL') or ''})
            elif self.path == '/api/sandbox/check' and lesson and lesson.get('sandbox'):
                res = workspace.check_sandbox(user, uuid)
            elif self.path == '/api/sandbox/reset' and lesson and lesson.get('sandbox'):
                workspace.reset_sandbox(user, uuid)
                res = {'ok': True}
            elif (self.path == '/api/progress' and isinstance(uuid, str) and isinstance(body.get('data'), dict)
                  and uuid not in ('app:stats', 'app:events')):  # stats are the server's
                prog, events = save_progress(user, uuid, body['data'])
                res = {'ok': True, 'events': events, 'stats': prog['app:stats']}
            else:
                return self.send_error(404)
        except workspace.Busy as e:
            return self.send_json({'error': str(e), 'output': str(e), 'passed': False}, 503)
        self.send_json(res)


class QuietFiles(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def check_cli():
    """Grade a made-up CLI lesson against a local file server, plus one step that must fail."""
    srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietFiles, directory=COURSES))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    first = gamify.CATALOG[0]['slug']
    ok = lambda **t: [{'exitCode': None, 'stdoutContainsAll': None, 'stdoutContainsNone': None,
                       'stdoutLinesGT': None, 'stdoutJq': None, **t}]
    steps = [
        {'cliCommand': {'command': 'echo id=abc123', 'tests': ok(exitCode=0, stdoutContainsAll=['id=']),
                        'stdoutVariables': [{'name': 'myid', 'regex': r'id=(\w+)'}]}},
        {'cliCommand': {'command': 'printf \'{"n":[1,2,3],"id":"${myid}"}\'', 'tests': ok(
            stdoutContainsAll=['abc123'],
            stdoutJq={'inputMode': '', 'query': '.n | length', 'expectedResults': [{'type': 'int', 'operator': '>=', 'value': 3}]})}},
        {'cliCommand': {'command': 'printf \'// c\\n{"a": "http://x", /* c */ "b": [1,],}\'', 'tests': ok(
            stdoutJq={'inputMode': 'jsonc', 'query': '.a + (.b|tostring)', 'expectedResults': [{'type': 'string', 'operator': '==', 'value': 'http://x[1]'}]})}},
        {'httpRequest': {'request': {'method': 'GET', 'fullURL': '${baseURL}/index.json'},
                         'responseVariables': [{'name': 'slug', 'path': '.courses[0].slug'}],
                         'tests': [{'statusCode': 200, 'headersContain': {'key': 'Content-Type', 'value': 'json'},
                                    'jsonValue': {'path': '.courses | length', 'operator': 'gt', 'intValue': 0}}]}},
        {'cliCommand': {'command': 'echo ${slug}', 'tests': ok(stdoutContainsAll=[first])}},
    ]
    with tempfile.TemporaryDirectory() as d:
        res = grader.run_cli(steps, d, f'http://127.0.0.1:{srv.server_address[1]}')
        assert res['passed'], json.dumps(res, indent=1)
        bad = grader.run_cli([{'cliCommand': {'command': 'exit 3', 'tests': ok(exitCode=0)}}] + steps, d, '')
        assert not bad['passed'] and bad['results'][1] is None, bad
    srv.shutdown()
    print(f'ok: CLI grader passes {len(steps)} sample checks and catches a failing one')


def check():
    prog = load_progress('local')
    passed = 0
    for uuid, p in prog.items():
        l = LESSONS.get(uuid)
        if l and p.get('done') and p.get('code') and l.get('files') and l.get('lang') != 'sql':
            if grader.run(l, p['code'], submit=True)['passed']:
                passed += 1
            else:  # the lesson may have changed since you solved it
                print('mismatch:', l['title'])
    assert passed, 'no saved code passed locally'
    print(f'ok: {passed} completed lessons pass locally')
    check_cli()


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        workspace.start()
        signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
        port = int(os.environ.get('PORT', 8002))  # gateway/main.go sets PORT
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)  # localhost only: the API runs code and shells
        try:
            server.serve_forever()
        finally:
            workspace.remove_all()
