"""The app worker: the /api behind the Go gateway (gateway/main.go), which signs people in and passes the user
as X-User. Code runs, CLI checks and terminals happen in that user's own container (workspace.py); progress is
saved per user in data/progress/<user>.json. python3 server/serve.py also runs it alone at http://localhost:8000.
Without Docker, build the UI first: cd web && bun install && bun run build   (UI dev with hot reload: bun run dev -> :5173)
Self-check: python3 server/serve.py --check  (re-submits your saved code, tests the CLI grader)
Without Docker, Python lessons need pytest: python3 -m venv .venv && .venv/bin/python -m pip install pytest"""
import email.utils, glob, gzip, json, os, signal, sys, tempfile, threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import grader, terminal, workspace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # repo root
WEB = os.path.join(ROOT, 'web', 'dist')
COURSES = os.path.join(ROOT, 'courses')  # served at /courses/, except shell/ (sandbox files)
PROGRESS_DIR = os.path.join(os.environ.get('DATA_DIR', os.path.join(ROOT, 'data')), 'progress')
LESSONS = {l['uuid']: l
           for p in glob.glob(os.path.join(COURSES, '*.json')) if not p.endswith('index.json')
           for ch in json.load(open(p))['chapters'] for l in ch['lessons']}
lock = threading.Lock()  # ponytail: one lock for every user's progress file; per-user locks if saves ever queue up


def progress_path(user):
    return os.path.join(PROGRESS_DIR, f'{user}.json')


def load_progress(user):
    try:
        return json.load(open(progress_path(user)))
    except FileNotFoundError:
        return {}


def save_progress(user, key, data):
    with lock:
        prog = load_progress(user)
        prog.setdefault(key, {}).update(data)
        os.makedirs(PROGRESS_DIR, exist_ok=True)
        tmp = progress_path(user) + '.tmp'
        json.dump(prog, open(tmp, 'w'), indent=1)
        os.replace(tmp, progress_path(user))  # never leave a half-written file


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def translate_path(self, path):
        p = super().translate_path(path)  # normalised, inside WEB
        rel = os.path.relpath(p, WEB)
        return os.path.join(ROOT, rel) if rel.split(os.sep)[0] == 'courses' else p

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')  # revalidate, so updated pages and icons show up
        super().end_headers()

    def user(self):
        """Set by the gateway from the signed-in account; 'local' when there's no sign-in."""
        u = self.headers.get('X-User', 'local')
        return u if workspace.USER_ID.match(u) else None

    def send_json(self, res, status=200):
        data = json.dumps(res).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def trusted(self):
        """Only this app's own pages may use it: blocks other websites (CSRF) and DNS rebinding."""
        port = self.server.server_address[1]
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        return host in (f'localhost:{port}', f'127.0.0.1:{port}') and origin in (None, f'http://{host}')

    GZIP = {'.json': 'application/json', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml',
            '.html': 'text/html; charset=utf-8'}
    gz_cache = {}  # path -> (mtime, gzipped bytes): course JSON shrinks ~5x, compressed once per file version

    def do_GET(self):
        if not self.trusted():
            return self.send_error(403)
        url = urllib.parse.urlsplit(self.path)
        user = self.user()
        if url.path.startswith('/api/') and not user:
            return self.send_error(400)
        if url.path == '/api/term':
            return terminal.serve(self, urllib.parse.parse_qs(url.query), user)
        if url.path == '/api/progress':  # the app's first call: start their workspace meanwhile
            threading.Thread(target=workspace.warm, args=(user,), daemon=True).start()
            return self.send_json(load_progress(user))
        if url.path.startswith('/courses/shell/'):  # sandbox files are for the server only
            return self.send_error(404)
        full = self.translate_path(self.path)
        if os.path.isdir(full):
            full = os.path.join(full, 'index.html')
        ctype = self.GZIP.get(os.path.splitext(full)[1])
        if not (ctype and 'gzip' in self.headers.get('Accept-Encoding', '') and os.path.isfile(full)):
            return super().do_GET()
        mtime = os.stat(full).st_mtime
        modified = email.utils.formatdate(mtime, usegmt=True)
        if self.headers.get('If-Modified-Since') == modified:
            self.send_response(304)
            return self.end_headers()
        cached = self.gz_cache.get(full)
        if not cached or cached[0] != mtime:
            cached = self.gz_cache[full] = (mtime, gzip.compress(open(full, 'rb').read(), 6))
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(cached[1])))
        self.send_header('Last-Modified', modified)
        self.end_headers()
        self.wfile.write(cached[1])

    def do_POST(self):
        if not self.trusted():
            return self.send_error(403)
        user = self.user()
        if not user:
            return self.send_error(400)
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        lesson = LESSONS.get(body.get('uuid'))
        try:
            if self.path == '/api/run' and lesson and 'files' in lesson:
                res = workspace.workspace(user).call({'op': 'run', 'lesson': lesson, 'code': body.get('code') or {},
                                                      'submit': bool(body.get('submit'))})
            elif self.path == '/api/cli' and lesson and 'cli' in lesson:
                box = workspace.workspace(user)
                if body.get('aws'):
                    box.start_aws()
                res = box.call({'op': 'cli', 'steps': lesson['cli'], 'dir': workspace.user_path(body.get('dir')),
                                'baseURL': body.get('baseURL') or lesson.get('baseURL') or ''})
            elif self.path == '/api/sandbox/check' and lesson and lesson.get('sandbox'):
                res = workspace.check_sandbox(user, body['uuid'])
            elif self.path == '/api/sandbox/reset' and lesson and lesson.get('sandbox'):
                workspace.reset_sandbox(user, body['uuid'])
                res = {'ok': True}
            elif self.path == '/api/progress' and isinstance(body.get('uuid'), str) and isinstance(body.get('data'), dict):
                save_progress(user, body['uuid'], body['data'])
                res = {'ok': True}
            else:
                return self.send_error(404)
        except workspace.Busy as e:
            return self.send_json({'error': str(e), 'output': str(e), 'passed': False}, 503)
        self.send_json(res)


def check_cli():
    """Grade a made-up CLI lesson against this app's own server, plus one step that must fail."""
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    first = json.load(open(os.path.join(COURSES, 'index.json')))['courses'][0]['slug']
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
        {'httpRequest': {'request': {'method': 'GET', 'fullURL': '${baseURL}/courses/index.json'},
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
        port = int(os.environ.get('PORT', 8000))  # gateway/main.go sets PORT
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)  # localhost only: the API runs code and shells
        if 'PORT' not in os.environ:
            print(f'Courses running at http://localhost:{port}')
        try:
            server.serve_forever()
        finally:
            workspace.remove_all()
