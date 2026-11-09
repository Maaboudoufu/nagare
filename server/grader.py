"""Lesson grading: run code lessons and CLI checks. No server state here: it runs inside each user's workspace
container (agent.py), and directly for the self-check (serve.py --check)."""
import base64, json, operator, os, re, sqlite3, subprocess, sys, tempfile, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPORT = os.path.join(HERE, 'support')
PY = sys.executable


def run_sql(d, files):
    """Run .sql files in name order on a fresh in-memory SQLite db; print every result set."""
    db, out = sqlite3.connect(':memory:'), []
    for name in sorted(files):
        buf = ''
        for line in open(os.path.join(d, name)):
            buf += line
            if not sqlite3.complete_statement(buf):
                continue
            try:
                cur = db.execute(buf)
            except sqlite3.Error as e:
                return False, '\n'.join(out + [f'{name}: Error: {e}', buf.strip()])
            if cur.description:
                rows = cur.fetchall()
                cols = [c[0] for c in cur.description]
                table = [cols] + [['NULL' if v is None else str(v) for v in r] for r in rows]
                w = [max(len(r[i]) for r in table) for i in range(len(cols))]
                fmt = lambda r: ' | '.join(v.ljust(w[i]) for i, v in enumerate(r))
                out += [f'-- {name}', fmt(cols), '-+-'.join('-' * x for x in w), *map(fmt, table[1:]), '']
            buf = ''
        db.commit()
    return True, '\n'.join(out) or '(no rows returned)'


C_WRAP = '-Wl,' + ','.join(f'--wrap={f}' for f in ('malloc', 'calloc', 'realloc', 'free', 'strdup'))


def commands(lesson, d, submit):
    """The commands that run a lesson in folder d, plus extra environment variables."""
    lang, is_test = lesson.get('lang'), lesson['type'] == 'type_code_tests'
    names = [f['name'] for f in lesson['files']]
    if lang == 'go':
        open(os.path.join(d, 'go.mod'), 'w').write('module lesson\n\ngo 1.22\n')
        if is_test and not submit:
            open(os.path.join(d, 'zz_run_test.go'), 'w').write('package main\n\nfunc init() { withSubmit = false }\n')
        return [['go', 'test', '-count=1', '-v', '.'] if is_test else ['go', 'run', '.']], {}
    if lang == 'py':
        env = {'PYTHONPATH': os.path.join(SUPPORT, 'python')}  # pyodide stand-in
        if not is_test:
            return [[PY, os.path.join(SUPPORT, 'python', 'run_main.py'), 'main.py']], env
        return [[PY, '-m', 'pytest', '-s', '-v', '-p', 'no:cacheprovider', '-o', 'markers=submit']
                + ([] if submit else ['-m', 'not submit'])], env
    if lang in ('js', 'ts'):
        for n in names:  # the hidden test helper decides run vs submit cases
            if n.startswith('unit_test.'):
                p = os.path.join(d, n)
                src = open(p).read()  # read before reopening for write, which truncates
                open(p, 'w').write(src.replace('let withSubmit = false', f'let withSubmit = {str(submit).lower()}'))
        return [['bun', f'main_test.{lang}' if is_test else f'main.{lang}']], {}
    if lang == 'c':
        sources = [n for n in names if n.endswith('.c')]
        tracks = any('bootlib.h' in open(os.path.join(d, n)).read() for n in names)
        build = ['gcc', '-std=gnu17', '-g', '-O0', '-Wall', '-I', os.path.join(SUPPORT, 'c'), '-o', 'lesson', *sources, '-lm']
        return [build + ([C_WRAP] if tracks else []), ['./lesson']], ({'BOOT_SUBMIT': '1'} if submit else {})
    raise ValueError(f'no runner for {lang} lessons')


def run(lesson, code, submit):
    """Run a lesson's code. code: {filename: content} for the editable files."""
    lang, is_test = lesson.get('lang'), lesson['type'] == 'type_code_tests'
    out = ''
    with tempfile.TemporaryDirectory() as d:
        for f in lesson['files']:
            content = f['content'] if f['isReadonly'] else code.get(f['name'], f['content'])
            open(os.path.join(d, f['name']), 'w').write(content)
        if lang == 'sql':
            out = run_sql(d, [f['name'] for f in lesson['files']])[1]
            return {'output': out, 'passed': None}  # no stored solution to grade against
        try:
            cmds, env = commands(lesson, d, submit)
        except ValueError as e:
            return {'output': str(e), 'passed': False}
        for cmd in cmds:  # e.g. compile, then run; stop at the first failure
            try:
                p = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
                                   env={**os.environ, **env})
            except subprocess.TimeoutExpired:
                return {'output': out + 'Timed out after 30s', 'passed': False}
            except FileNotFoundError:
                return {'output': out + f'{cmd[0]} is not installed. Run the app with docker compose; its image has every toolchain.', 'passed': False}
            out += p.stdout + p.stderr
            if p.returncode:
                break
    ok = p.returncode == 0 and '✘ Fail' not in out  # JS/TS test helpers print failures but exit 0
    passed = ok if is_test else p.returncode == 0 and p.stdout.strip() == (lesson.get('expected') or '').strip()
    return {'output': out, 'passed': passed if submit else None, 'ok': ok}


# ---- CLI lessons ----

VAR = re.compile(r'\$\{(\w+)\}')
OPS = {'==': operator.eq, 'eq': operator.eq, '>': operator.gt, 'gt': operator.gt, '>=': operator.ge,
       '<': operator.lt, '<=': operator.le, 'contains': lambda a, b: b in a, 'not_contains': lambda a, b: b not in a}


def interp(v, vars):
    """Replace ${name} with known variables, recursively; unknown ${...} is left for the shell."""
    if isinstance(v, str):
        return VAR.sub(lambda m: str(vars[m.group(1)]) if m.group(1) in vars else m.group(0), v)
    if isinstance(v, list):
        return [interp(x, vars) for x in v]
    if isinstance(v, dict):
        return {k: interp(x, vars) for k, x in v.items()}
    return v


def jq(query, value):
    """First result of a jq query on a JSON value."""
    p = subprocess.run(['jq', '-c', query], input=json.dumps(value), capture_output=True, text=True, timeout=10)
    if p.returncode:
        raise ValueError(f'jq error: {p.stderr.strip()}')
    if not p.stdout.strip():
        raise ValueError(f'jq `{query}` returned nothing')
    return json.loads(p.stdout.split('\n', 1)[0])


def strip_jsonc(s):
    """Drop // and /* */ comments outside strings, then trailing commas."""
    out, i, in_str = [], 0, False
    while i < len(s):
        c = s[i]
        if in_str:
            out.append(c)
            if c == '\\':
                out.append(s[i + 1:i + 2]); i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif s.startswith('//', i):
            i = s.find('\n', i) if '\n' in s[i:] else len(s); continue
        elif s.startswith('/*', i):
            i = s.find('*/', i + 2) + 2 if '*/' in s[i + 2:] else len(s); continue
        else:
            out.append(c)
        i += 1
    # ponytail: regex misses ",}" inside strings; fine for config files
    return re.sub(r',(\s*[}\]])', r'\1', ''.join(out))


def parse_json(text, mode):
    if mode == 'jsonl':
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(strip_jsonc(text) if mode == 'jsonc' else text)


def compare(actual, op, expected):
    if isinstance(actual, bool) != isinstance(expected, bool):
        return False
    try:
        return OPS[op](actual, expected)
    except (TypeError, KeyError):
        return False


def cli_command(c, cwd, vars):
    cmd = interp(c['command'], vars)
    try:
        # No stdin and no terminal: prompts (docker login, ssh passwords) fail fast instead of hanging.
        p = subprocess.run(['bash', '-c', cmd], cwd=cwd, capture_output=True, text=True, timeout=180,
                           stdin=subprocess.DEVNULL, start_new_session=True)
    except subprocess.TimeoutExpired:
        return {'output': f'$ {cmd}\nTimed out after 180s', 'failures': ['command timed out']}
    stdout, both = p.stdout, p.stdout + p.stderr
    if c.get('stdoutFilterTmdl'):
        stdout = next((l for l in reversed(stdout.splitlines()) if c['stdoutFilterTmdl'] in l), stdout)
    fails = []
    for v in c.get('stdoutVariables') or []:
        m = re.search(v['regex'], p.stdout)
        if m:
            vars[v['name']] = m.group(1) if m.groups() else m.group(0)
        else:
            fails.append(f"couldn't find {v['regex']!r} in the output")
    for t in c.get('tests') or []:
        if t.get('exitCode') is not None and p.returncode != t['exitCode']:
            fails.append(f"expected exit code {t['exitCode']}, got {p.returncode}")
        for s in interp(t.get('stdoutContainsAll') or [], vars):
            if s not in both:
                fails.append(f'output should contain {s!r}')
        for s in interp(t.get('stdoutContainsNone') or [], vars):
            if s in both:
                fails.append(f'output should not contain {s!r}')
        if t.get('stdoutLinesGT') is not None and len(p.stdout.splitlines()) <= t['stdoutLinesGT']:
            fails.append(f"expected more than {t['stdoutLinesGT']} lines of output")
        if t.get('stdoutJq'):
            q = t['stdoutJq']
            try:
                val = jq(q['query'], parse_json(stdout, q.get('inputMode')))
                for e in q.get('expectedResults') or []:
                    if not compare(val, e['operator'], e['value']):
                        fails.append(f"jq `{q['query']}` gave {json.dumps(val)}, expected {e['operator']} {json.dumps(e['value'])}")
            except (ValueError, subprocess.TimeoutExpired) as e:
                fails.append(f"couldn't check output with jq: {e}")
    return {'output': f'$ {cmd}\n{both}', 'failures': fails}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None  # urllib then raises HTTPError carrying the 3xx response


def http_request(h, vars):
    r = interp(h['request'], vars)
    headers, data = dict(r.get('headers') or {}), None
    if r.get('bodyJSON') is not None:
        data = json.dumps(r['bodyJSON']).encode()
        headers.setdefault('Content-Type', 'application/json')
    elif r.get('bodyForm') is not None:
        data = urllib.parse.urlencode(r['bodyForm']).encode()
        headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    if r.get('basicAuth'):
        a = r['basicAuth']
        headers['Authorization'] = 'Basic ' + base64.b64encode(f"{a['username']}:{a['password']}".encode()).decode()
    req = urllib.request.Request(r['fullURL'], data=data, headers=headers, method=r['method'])
    opener = urllib.request.build_opener(*([NoRedirect] if r.get('followRedirects') is False else []))
    try:
        resp = opener.open(req, timeout=30)
        status, body, hdrs = resp.status, resp.read(), resp.headers
    except urllib.error.HTTPError as e:
        status, body, hdrs = e.code, e.read(), e.headers
    except (urllib.error.URLError, OSError) as e:
        return {'output': f"{r['method']} {r['fullURL']}\n{e}",
                'failures': [f"couldn't reach {r['fullURL']}: is your server running?"]}
    text = body.decode('utf-8', 'replace')
    fails, notes = [], []
    for v in h.get('responseVariables') or []:
        try:
            if v.get('bodyRegex'):
                vars[v['name']] = re.search(v['bodyRegex'], text).group(1)
            else:
                val = jq(v['path'], json.loads(text))
                vars[v['name']] = val if isinstance(val, str) else json.dumps(val)
        except (AttributeError, ValueError) as e:
            fails.append(f"couldn't read {v['name']} from the response: {e}")
    for v in h.get('responseHeaderVariables') or []:
        values = hdrs.get_all(v['header']) or []
        matches = [re.search(v['regex'], x) for x in values] if v.get('regex') else []
        found = next((m.group(1) for m in matches if m), None) if v.get('regex') else (values[0] if values else None)
        if found is None:
            fails.append(f"couldn't read {v['name']} from the {v['header']} header")
        else:
            vars[v['name']] = found
    for t in interp(h.get('tests') or [], vars):
        if t.get('statusCode') is not None and status != t['statusCode']:
            fails.append(f"expected status {t['statusCode']}, got {status}")
        if t.get('bodyContains') is not None and t['bodyContains'] not in text:
            fails.append(f"body should contain {t['bodyContains']!r}")
        if t.get('bodyContainsNone') is not None and t['bodyContainsNone'] in text:
            fails.append(f"body should not contain {t['bodyContainsNone']!r}")
        for key, check in (('headersContain', lambda a, b: b in a), ('headersEqual', operator.eq)):
            if t.get(key):
                k, want = t[key]['key'], t[key]['value']
                if not any(check(x, want) for x in hdrs.get_all(k) or []):
                    fails.append(f"header {k} should {'contain' if key == 'headersContain' else 'equal'} {want!r}")
        if t.get('jsonValue'):
            jv = t['jsonValue']
            want = next(jv[k] for k in ('intValue', 'stringValue', 'boolValue') if jv.get(k) is not None)
            try:
                val = jq(jv['path'], json.loads(text))
                if not compare(val, jv['operator'], want):
                    fails.append(f"{jv['path']} is {json.dumps(val)}, expected {jv['operator']} {json.dumps(want)}")
            except ValueError as e:
                fails.append(f"couldn't read {jv['path']} from the JSON body: {e}")
        if t.get('trailersEqual'):
            notes.append(f"Not checked locally: HTTP trailer {t['trailersEqual']}")
    shown = '\n'.join(f'{k}: {v}' for k, v in hdrs.items())
    return {'output': '\n'.join(notes + [f"{r['method']} {r['fullURL']}\n→ {status}\n{shown}\n\n{text[:3000]}"]), 'failures': fails}


def run_cli(steps, cwd, base_url):
    """Run a CLI lesson's steps in order, stopping at the first failing one."""
    vars, results, failed = {'baseURL': base_url}, [], False
    for st in steps:
        if failed:
            results.append(None)  # skipped
            continue
        try:
            res = cli_command(st['cliCommand'], cwd, vars) if st.get('cliCommand') else http_request(st['httpRequest'], vars)
        except Exception as e:  # a malformed step shouldn't kill the whole run
            res = {'output': '', 'failures': [f'{type(e).__name__}: {e}']}
        results.append(res)
        failed = bool(res['failures'])
        ms = (st.get('cliCommand') or st.get('httpRequest')).get('sleepAfterMs')
        if ms:
            time.sleep(ms / 1000)
    return {'results': results, 'passed': all(r and not r['failures'] for r in results)}
