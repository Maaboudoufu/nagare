"""Per-user containers. Nothing a user runs touches the server itself:

  workspace  one container per user (nagare-ws-<user>): code runs, CLI checks and the project terminal.
             Their files live in a volume (nagare-home-<user>), so they survive restarts.
  sandbox    one container per user and Learn Linux lesson (nagare-sb-<user>-<lesson>), seeded with that
             lesson's files, no network.

Both start on first use and are stopped after WORKSPACE_IDLE_MINUTES without activity (runs, checks, keystrokes).
A stopped workspace comes back in well under a second with the same files. Settings (environment):
  WORKSPACE_IDLE_MINUTES (15)  MAX_WORKSPACES (50)  WORKSPACE_CPUS (1)  WORKSPACE_MEMORY (1g)
  WORKSPACE_RUNTIME (e.g. runsc for gVisor; default: Docker's runc)
"""
import io, json, os, posixpath, re, subprocess, tarfile, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHELL_DIR = os.path.join(os.path.dirname(HERE), 'courses', 'shell')
IMAGE = os.environ.get('SANDBOX_IMAGE', 'nagare')
NETWORK = 'nagare-users'
HOME = '/home/user'
IDLE_S = float(os.environ.get('WORKSPACE_IDLE_MINUTES', 15)) * 60
MAX_WORKSPACES = int(os.environ.get('MAX_WORKSPACES', 50))
SANDBOXES_PER_USER = 3
RUNTIME = ['--runtime', os.environ['WORKSPACE_RUNTIME']] if os.environ.get('WORKSPACE_RUNTIME') else []
LIMITS = ['--cpus', os.environ.get('WORKSPACE_CPUS', '1'), '--memory', os.environ.get('WORKSPACE_MEMORY', '1g'),
          '--pids-limit', '512', *RUNTIME]
USER_ID = re.compile(r'^[a-z0-9]{1,32}$')
# The AWS course talks to Floci, a local AWS emulator inside the workspace, never to real AWS.
AWS_ENV = ['-e', 'AWS_ENDPOINT_URL=http://localhost:4566', '-e', 'AWS_DEFAULT_REGION=us-east-1']
AWS_CREDENTIALS = '[default]\naws_access_key_id = test\naws_secret_access_key = test\n'


class Busy(Exception):
    """Too many workspaces running; try again in a bit."""


def _docker(*args, data=None, timeout=60):
    return subprocess.run(['docker', *args], input=data, capture_output=True, timeout=timeout)


def _check(r, what):
    if r.returncode:
        raise RuntimeError(r.stderr.decode().strip() or f'docker {what} failed')
    return r.stdout.decode().strip()


class Box:
    """A running container plus when it was last used."""

    def __init__(self, name, kind, user):
        self.name, self.kind, self.user = name, kind, user
        self.used = time.monotonic()
        self.lock = threading.Lock()  # one grading request at a time per workspace
        self.agent = None
        self.aws = False

    def touch(self):
        self.used = time.monotonic()

    def call(self, req):
        """Send one request to the workspace's grading agent (agent.py) and wait for the answer."""
        self.touch()
        with self.lock:
            for attempt in (1, 2):  # a dead agent (e.g. it crashed) is restarted once
                if not self.agent or self.agent.poll() is not None:
                    self.agent = subprocess.Popen(['docker', 'exec', '-i', self.name, 'python3', '-u', '/app/server/agent.py'],
                                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                try:
                    self.agent.stdin.write((json.dumps(req) + '\n').encode())
                    self.agent.stdin.flush()
                    line = self.agent.stdout.readline()
                except OSError:
                    line = b''
                if line:
                    self.touch()
                    return json.loads(line)
                self.agent.kill()
                self.agent = None
        try:
            if not _running(self.name):  # the container itself is gone: forget it, so the next request starts a new one
                _stop(self)
        except (RuntimeError, subprocess.TimeoutExpired):
            pass  # Docker didn't answer: the reaper sorts it out
        return {'error': 'Your workspace stopped while running that. Try again.'}

    def start_aws(self):
        """Start Floci in this workspace (once). About 60 ms; ~140 MB, so only for people doing the AWS course."""
        if self.aws:
            return
        _docker('exec', '-d', '-w', HOME, self.name, 'sh', '-c',
                'mkdir -p .floci && cd .floci && exec floci -Dquarkus.http.host=127.0.0.1 >>log 2>&1')
        _docker('exec', self.name, 'sh', '-c', 'for i in $(seq 100); do curl -s -o /dev/null localhost:4566 && exit; sleep 0.05; done')
        self.aws = True


boxes = {}  # container name -> Box
boxes_lock = threading.Lock()
user_locks = {}  # name -> lock, so two requests don't both create the same container


def _name_lock(name):
    with boxes_lock:
        return user_locks.setdefault(name, threading.Lock())


def _running(*names):
    """Which of our containers are running right now (all of them if no names are given)."""
    out = _check(_docker('ps', '--filter', 'label=nagare', '--format', '{{.Names}}'), 'ps').split()
    return set(out) & set(names) if names else set(out)


def _stop(box):
    with boxes_lock:
        boxes.pop(box.name, None)
    if box.agent:
        box.agent.kill()
    _docker('rm', '-f', box.name)  # workspaces' files stay in their volume


def _ensure_network():
    if _docker('network', 'inspect', NETWORK).returncode:
        # Internet access (git, AWS lessons, HTTP clients) but no traffic between users' containers.
        _docker('network', 'create', '-o', 'com.docker.network.bridge.enable_icc=false', NETWORK)


def workspace(user):
    """The user's running workspace, starting it if needed."""
    if not USER_ID.match(user):
        raise ValueError('bad user id')
    name = f'nagare-ws-{user}'
    with _name_lock(name):
        box = boxes.get(name)
        if box:
            box.touch()
            return box
        with boxes_lock:
            running = sorted((b for b in boxes.values() if b.kind == 'workspace'), key=lambda b: b.used)
        if len(running) >= MAX_WORKSPACES:  # make room: stop the longest-idle one, if it's been idle a while
            if time.monotonic() - running[0].used < 60:
                raise Busy('The server is busy. Try again in a minute.')
            _stop(running[0])
        _check(_docker('run', '-d', '--rm', '--name', name, '--label', 'nagare=workspace', '--label', f'nagare.user={user}',
                       '--hostname', 'workspace', '--network', NETWORK, '--init', '--user', '1000:1000',
                       '--security-opt', 'no-new-privileges',  # no sudo/setuid to root (sandboxes keep sudo: no network)
                       '-e', f'HOME={HOME}', '-e', 'TERM=xterm-256color', *AWS_ENV, '-w', HOME,
                       '-v', f'nagare-home-{user}:{HOME}', *LIMITS, IMAGE, 'sleep', 'infinity'), 'run')
        # Starter AWS credentials for the emulator, unless the user already configured their own.
        _docker('exec', name, 'sh', '-c', '[ -f .aws/credentials ] || { umask 077 && mkdir -p .aws && printf "%s" "$0" > .aws/credentials; }',
                AWS_CREDENTIALS)
        box = Box(name, 'workspace', user)
        with boxes_lock:
            boxes[name] = box
        return box


def warm(user):
    """Start the workspace in the background (on page load), so the first Run doesn't wait for it."""
    try:
        workspace(user)
    except Exception:
        pass


def user_path(d):
    """A folder the user typed ('~', '~/proj', 'proj', '/home/user/proj') as a path inside their workspace."""
    d = (d or '').strip()
    if d.startswith(HOME):
        d = d[len(HOME):]
    rel = posixpath.normpath('/' + d.lstrip('~').lstrip('/')).lstrip('/')
    return posixpath.join(HOME, rel) if rel not in ('', '.') else HOME


def terminal_argv(box, folder):
    """A login shell in the user's workspace, in folder (created if missing)."""
    return ['docker', 'exec', '-it', '-w', HOME, box.name, 'bash', '-c',
            'mkdir -p -- "$1" && cd -- "$1" && exec bash --rcfile /app/server/support/project.bashrc -i', 'bash', folder]


# ---- Learn Linux sandboxes ----

def shell_spec(uuid):
    spec = json.load(open(os.path.join(SHELL_DIR, f'{uuid}.json')))
    if spec['files'] == '_fallback':
        spec['files'] = json.load(open(os.path.join(SHELL_DIR, '_fallback.json')))
    return spec


def _match_count(spec):
    """Match checks in this lesson. More than one turns on command recording."""
    return sum(1 for c in spec['checks'] if (c.get('matchCommand') or {}).get('lastContains'))


def _seed_tar(spec):
    """Starter files as a tar owned by the sandbox user (uid 1000), with every parent folder so it's writable."""
    root = spec['root'].strip('/')
    dirs = set()
    for path in [d.strip('/') for d in spec['dirs']] + [os.path.dirname(f['name']) for f in spec['files']]:
        while path:
            dirs.add(path)
            path = os.path.dirname(path)
    buf, now = io.BytesIO(), time.time()
    with tarfile.open(fileobj=buf, mode='w') as tar:
        def add(name, data=None, mode=0o644):
            info = tarfile.TarInfo(name)
            info.uid = info.gid = 1000
            info.mtime = now  # otherwise files show a 1970 date in ls -l
            info.uname = info.gname = 'user'
            if data is None:
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            else:
                info.size, info.mode = len(data), mode
                tar.addfile(info, io.BytesIO(data))
        for d in sorted(dirs):
            add(f'{root}/{d}')
        for f in spec['files']:
            add(f"{root}/{f['name']}", f['content'].encode())
        if spec['init']:
            add('tmp/.lesson_init.sh', ('\n'.join(spec['init']) + '\n').encode(), 0o755)
    return buf.getvalue()


def _sandbox_name(user, uuid):
    return f'nagare-sb-{user}-{uuid.replace("-", "")[:12]}'


def sandbox(user, uuid):
    """The user's sandbox for this lesson, creating, seeding and starting it if needed."""
    if not USER_ID.match(user):
        raise ValueError('bad user id')
    name = _sandbox_name(user, uuid)
    with _name_lock(name):
        box = boxes.get(name)
        if box:
            box.touch()
            return box
        with boxes_lock:
            mine = sorted((b for b in boxes.values() if b.kind == 'sandbox' and b.user == user), key=lambda b: b.used)
        for old in mine[:max(0, len(mine) - SANDBOXES_PER_USER + 1)]:  # keep the few most recent
            _stop(old)
        spec = shell_spec(uuid)
        # One check still reads the last history line, so those shells keep the original prompt.
        record = ['-e', 'NAGARE_RECORD_COMMANDS=1'] if _match_count(spec) > 1 else []
        cid = _check(_docker('create', '-it', '--label', 'nagare=sandbox', '--label', f'nagare.user={user}', '--name', name,
                             '--network', 'none', '--memory', '256m', '--pids-limit', '128', '--cpus', '0.5',
                             *RUNTIME,
                             '--hostname', 'worldbanc', '--user', 'user', '-w', spec['cwd'], '-e', 'TERM=xterm-256color',
                             *record,
                             IMAGE, 'bash', '--rcfile', '/etc/sandbox.bashrc', '-i'), 'create')
        try:
            _check(_docker('cp', '-a', '-', f'{cid}:/', data=_seed_tar(spec)), 'cp')
            _check(_docker('start', cid), 'start')
        except RuntimeError:
            _docker('rm', '-f', cid)
            raise
        box = Box(name, 'sandbox', user)
        with boxes_lock:
            boxes[name] = box
        return box


def reset_sandbox(user, uuid):
    name = _sandbox_name(user, uuid)
    box = boxes.get(name)
    if box:
        _stop(box)
    else:
        _docker('rm', '-f', name)


# Bound grading memory even if an interactive loop produces a large command log.
SHELL_LOG_LIMIT = 1 << 20


def _nul_records(raw):
    """Read only completed records; a concurrent append may leave an unfinished tail."""
    return [part.decode(errors='replace') for part in raw.split(b'\0')[:-1]]


def _claim_command(commands, start, want):
    """Earliest command at or after start that contains every token, and the index after it.

    A miss leaves start unchanged, so a later check can still match a command this one did not take.
    One command satisfies only one check: the next check begins after it.
    """
    for i in range(start, len(commands)):
        if all(token in commands[i] for token in want):
            return commands[i], i + 1
    return '', start


def _read_commands(box):
    """The DEBUG log, or None when history exists and this log does not.

    None means this sandbox is not recording (an older image, or it was created without the
    recording env). An empty list means the learner has not run a recorded command.
    """
    r = _docker('exec', box.name, 'sh', '-c',
                f'if [ -f /tmp/.shell_commands ]; then head -c {SHELL_LOG_LIMIT + 1} /tmp/.shell_commands; '
                'elif [ -s /tmp/.shell_history ]; then exit 3; fi')
    if r.returncode == 3:
        return None
    if r.returncode:
        raise RuntimeError('Could not read your commands. Try submitting again.')
    if len(r.stdout) > SHELL_LOG_LIMIT:
        raise RuntimeError('The command log is full. Reset the sandbox and run the assignment again.')
    return _nul_records(r.stdout)


_STALE_SANDBOX = 'This sandbox needs an update. Reset it and run the assignment again.'


def check_sandbox(user, uuid):
    """One match check uses the last history line; several claim recorded commands in order.

    Each command can satisfy one check. A miss leaves the cursor unchanged. `after` means
    a failed check searched after an earlier matched step. Matching tests text, not success.
    Only a multi-check sandbox sets a DEBUG trap, for direct interactive commands. Function,
    script, and subshell bodies and skipped conditional branches stay out of that log.
    Run checks keep their manual-review behavior.

    Rebuild SANDBOX_IMAGE when sandbox.bashrc changes, then reset existing sandboxes.
    An older image with history but no command log returns an update error.
    """
    box = boxes.get(_sandbox_name(user, uuid))
    if not box:
        return {'error': 'Open the terminal and run your commands first.'}
    box.touch()
    spec = shell_spec(uuid)
    nmatch = _match_count(spec)
    commands, last_line = None, ''
    if nmatch > 1:
        try:
            commands = _read_commands(box)
        except subprocess.TimeoutExpired:
            return {'error': 'Reading your commands timed out. Try submitting again.'}
        except RuntimeError as e:
            return {'error': str(e)}
        if commands is None:
            return {'error': _STALE_SANDBOX}
    elif nmatch == 1:
        last_line = _docker('exec', box.name, 'sh', '-c', 'tail -n 1 /tmp/.shell_history 2>/dev/null').stdout.decode().strip()
    cursor, claimed = 0, False
    results = []
    for c in spec['checks']:
        want = (c.get('matchCommand') or {}).get('lastContains')
        if want:
            if nmatch > 1:
                command, cursor = _claim_command(commands, cursor, want)
                ok = bool(command)
                after = (not ok) and claimed
                if ok:
                    claimed = True
                scope = 'ordered'
            else:
                command, ok, after, scope = last_line, all(token in last_line for token in want), False, 'last'
            lead = 'Your last command should contain' if scope == 'last' else 'A command should contain'
            results.append({'kind': 'match', 'ok': ok, 'want': want, 'last': command, 'scope': scope,
                            'after': after, 'message': f"{lead}: {', '.join(want)}"})
        if c.get('runCommand'):
            try:
                r = _docker('exec', '-u', 'user', '-w', spec['cwd'], box.name, 'bash', '-c', c['runCommand'], timeout=20)
                output = (r.stdout + r.stderr).decode(errors='replace')[:4000]
            except subprocess.TimeoutExpired:
                output = 'Timed out after 20s'
            results.append({'kind': 'run', 'ok': None, 'command': c['runCommand'], 'output': output})
    graded = [r for r in results if r['ok'] is not None]
    return {'results': results, 'passed': all(r['ok'] for r in graded) and len(graded) == len(results),
            'review': any(r['ok'] is None for r in results) and all(r['ok'] for r in graded)}


# ---- lifecycle ----

def remove_user(user):
    """Stop one user's workspace and sandboxes (an admin signed them out). Their files stay."""
    with boxes_lock:
        mine = [b for b in boxes.values() if b.user == user]
    for b in mine:
        _stop(b)


def remove_all():
    """Remove every workspace and sandbox container (volumes, i.e. users' files, stay)."""
    ids = _docker('ps', '-aq', '--filter', 'label=nagare').stdout.split()
    if ids:
        _docker('rm', '-f', *[i.decode() for i in ids])
    with boxes_lock:
        boxes.clear()


def _reap():
    """Stop idle containers, and forget ones that died on their own (out of memory, removed by hand)."""
    now = time.monotonic()
    with boxes_lock:
        known = list(boxes.values())  # before asking Docker: a container started meanwhile isn't mistaken for dead
    running = _running()
    for b in known:
        if now - b.used > IDLE_S or b.name not in running:
            _stop(b)


def _reaper():
    while True:
        time.sleep(30)
        try:
            _reap()
        except Exception as e:  # Docker hiccup: try again next round rather than never reaping again
            print(f'workspace reaper: {e}', flush=True)


def start():
    """Call once at worker startup: clear leftovers from a previous run, then reap idle containers."""
    remove_all()
    _ensure_network()
    threading.Thread(target=_reaper, daemon=True).start()


if __name__ == '__main__':
    # Real lesson ids. Records below are the commands those assignments ask for.
    EXPR = 'f9d0dadb-59f8-489b-af77-f6693000d569'          # expr 123456, then expr 420
    ECHO_HIST = '498e7b52-9044-4c03-996f-6452eeeb4730'    # echo, then history
    ECHO_CLEAR = '317def47-df3a-4fb3-b3df-f01c1b180b6d'   # echo, then clear
    HEAD_TAIL = '96b5e0ce-37f8-44c2-b219-ebdae3655f23'    # head 2023.csv, then tail 2023.csv
    PWD_LS = 'f5f6762e-9736-4d2f-aaff-423088dbbf47'       # pwd, then ls worldbanc
    PATH_GEN = '25411224-2384-4c13-93d2-0eeb5ad30eb1'     # echo PATH, then genids.sh
    STDERR = '1c360eb8-4b1c-46ae-a123-2b92e67f0ac9'       # process_transactions.sh ... 2>, then cat the log
    PWD = 'aa6b8b23-8be0-41a8-930f-5375f2026699'          # one check: pwd
    # Separate commands, including steps the assignment runs between the two checks.
    SEPARATE = {
        EXPR: ['expr 123456 + 7890', 'expr 420 - 69'],
        ECHO_HIST: ['echo Investigating WorldBanc', 'whoami', 'history'],
        ECHO_CLEAR: ['echo Case file: WorldBanc', 'echo Case file: WorldBanc', 'clear'],
        HEAD_TAIL: ['cd worldbanc/private/transactions', 'cat 2023.csv', 'head -n 6 2023.csv', 'tail -n 5 2023.csv'],
        PWD_LS: ['pwd', 'ls', 'ls worldbanc'],
        PATH_GEN: ['export PATH="$PATH:$HOME/worldbanc/private/bin"', 'echo "$PATH"', 'cd ~', 'genids.sh'],
        STDERR: ['worldbanc/private/bin/process_transactions.sh worldbanc/private/transactions/2020.csv 2> /tmp/worldbanc.log',
                 'cat /tmp/worldbanc.log'],
    }

    def grade(uuid, *, last='', records=None, output=b'ok\n', stale=False, raw=None, read_code=0, read_timeout=False):
        user = 't3test'
        name = _sandbox_name(user, uuid)
        boxes[name] = Box(name, 'sandbox', user)
        calls = []
        packed = b'' if not records else ('\0'.join(records) + '\0').encode()

        def fake(*args, **kwargs):
            calls.append(args)
            script = args[args.index('-c') + 1] if '-c' in args else ''
            if script.startswith('if [ -f /tmp/.shell_commands ]'):
                if read_timeout:
                    raise subprocess.TimeoutExpired(args, 60)
                code = 3 if stale else read_code
                return subprocess.CompletedProcess(args, code, b'' if stale else packed if raw is None else raw, b'')
            if script.startswith('tail -n 1 /tmp/.shell_history'):
                return subprocess.CompletedProcess(args, 0, (last + '\n').encode() if last else b'', b'')
            return subprocess.CompletedProcess(args, 0, output, b'')

        global _docker
        old = _docker
        _docker = fake
        try:
            return check_sandbox(user, uuid), calls, name
        finally:
            _docker = old
            boxes.pop(name, None)

    def rows(uuid, records):
        res, calls, name = grade(uuid, records=records)
        got = [(r['ok'], r['after'], r['scope']) for r in res['results']]
        assert len(calls) == 1 and calls[0][1] == name and '/tmp/.shell_commands' in calls[0][-1], calls
        assert 'tail -n 1' not in calls[0][-1]
        assert res['review'] is False and res['passed'] is all(ok for ok, _, _ in got) and 'error' not in res
        return got, res

    def expect(uuid, records, want):
        got, res = rows(uuid, records)
        assert got == [(ok, after, 'ordered') for ok, after in want], (records, got, res)
        return res

    assert check_sandbox('t3test', EXPR) == {'error': 'Open the terminal and run your commands first.'}
    bare, empty = rows(EXPR, [])
    assert bare == [(False, False, 'ordered'), (False, False, 'ordered')]
    assert [r['want'] for r in empty['results']] == [['expr', '123456'], ['expr', '420']]
    assert empty['results'][0]['message'] == 'A command should contain: expr, 123456'

    both, one, none = [(True, False), (True, False)], [(True, False), (False, True)], [(False, False), (False, False)]
    # The multi-check lessons, each command recorded on its own.
    seen = set()
    for uuid, records in SEPARATE.items():
        expect(uuid, records, both)
        seen.add(uuid)
    # Two recorded commands (what `;` and `&&` produce). One string cannot satisfy both checks.
    expect(EXPR, ['expr 123456 + 7890', 'expr 420 - 69'], both)
    expect(EXPR, ['echo "expr 123456 + 7890; expr 420 - 69"'], one)
    expect(EXPR, ["echo 'expr 123456 + 7890 && expr 420 - 69'"], one)
    expect(EXPR, ['expr 123456 + 7890\\; expr 420 - 69'], one)
    expect(EXPR, ['expr 123456 + 420'], one)
    expect(ECHO_HIST, ['echo history'], one)
    expect(EXPR, ['expr 123456 + 7890', 'ls', 'expr 420 - 69'], both)             # unrelated command in between
    expect(EXPR, ['expr 420 - 69', 'expr 123456 + 7890', 'expr 420 - 69'], both)  # retry after a reversed pair
    expect(EXPR, ['expr 420 - 69', 'expr 123456 + 7890'], [(True, False), (False, True)])
    expect(ECHO_HIST, ['history', 'echo Investigating WorldBanc'], [(True, False), (False, True)])
    expect(EXPR, ['expr 123456 + 7890'], [(True, False), (False, True)])          # second is missing
    expect(EXPR, ['expr 420 - 69'], [(False, False), (True, False)])              # first is missing, second still matches
    expect(ECHO_HIST, ['history'], [(False, False), (True, False)])
    expect(EXPR, [], none)
    stale, stale_calls, _ = grade(EXPR, last='expr 123456 + 7890', stale=True)
    assert stale == {'error': _STALE_SANDBOX}, stale
    assert len(stale_calls) == 1 and stale_calls[0][-1].startswith('if [ -f /tmp/.shell_commands ]')

    assert _nul_records(b'echo hello\0unfinished') == ['echo hello']
    assert _nul_records(b'echo \xff\0') == ['echo \ufffd']
    failed, _, _ = grade(EXPR, read_code=1)
    timed_out, _, _ = grade(EXPR, read_timeout=True)
    full, calls, _ = grade(EXPR, raw=b'x' * (SHELL_LOG_LIMIT + 1))
    assert failed == {'error': 'Could not read your commands. Try submitting again.'}
    assert timed_out == {'error': 'Reading your commands timed out. Try submitting again.'}
    assert full == {'error': 'The command log is full. Reset the sandbox and run the assignment again.'}
    assert f'head -c {SHELL_LOG_LIMIT + 1}' in calls[0][-1]

    # Every one-check lesson grades only the last history line. An earlier match is not read.
    sentinel, single, run_lessons, discovered = '___nope___', 0, 0, set()
    run_uuid = None
    for name in sorted(os.listdir(SHELL_DIR)):
        if not name.endswith('.json') or name == '_fallback.json':
            continue
        uuid = name[:-5]
        spec = shell_spec(uuid)
        match = [w for w in ((c.get('matchCommand') or {}).get('lastContains') for c in spec['checks']) if w]
        runs = [c['runCommand'] for c in spec['checks'] if c.get('runCommand')]
        assert not (match and runs), uuid
        if len(match) > 1:
            discovered.add(uuid)
        elif len(match) == 1:
            single += 1
            want = match[0]
            assert all(token not in sentinel for token in want), want
            line = ' '.join(want)
            for last, ok in ((sentinel, False), (line, True)):
                res, calls, name_box = grade(uuid, last=last)
                assert [(r['ok'], r['after'], r['scope'], r['last']) for r in res['results']] == [(ok, False, 'last', last)]
                assert res['results'][0]['message'] == f"Your last command should contain: {', '.join(want)}"
                assert res['passed'] is ok and res['review'] is False and 'error' not in res
                assert [c[-1] for c in calls] == ['tail -n 1 /tmp/.shell_history 2>/dev/null']
                assert name_box == calls[0][1]
        else:
            run_lessons += 1
            if run_uuid is None:
                run_uuid = uuid
            res, calls, name_box = grade(uuid, last='echo leftover', records=['echo leftover'])
            assert res['passed'] is False and res['review'] is True and 'error' not in res, uuid
            assert [r['ok'] for r in res['results']] == [None] * len(runs)
            assert [r['command'] for r in res['results']] == runs
            assert [r['output'] for r in res['results']] == ['ok\n'] * len(runs)
            assert [c[c.index('-c') + 1] for c in calls] == runs, (uuid, calls)
            assert all(c[c.index('-u') + 1] == 'user' and c[c.index('-w') + 1] == spec['cwd'] for c in calls)
            assert all(name_box in c for c in calls)
            assert not any('/tmp/.shell_' in str(c) for c in calls)
    assert seen == discovered, sorted(discovered ^ seen)  # every multi-check lesson has a command fixture
    assert single > 0 and run_lessons > 0  # both other check shapes are still exercised

    def create_args(uuid):
        calls = []

        def fake(*args, **kwargs):
            calls.append(args)
            out = b'cid\n' if args and args[0] == 'create' else b''
            return subprocess.CompletedProcess(args, 0, out, b'')

        global _docker
        old, _docker = _docker, fake
        name = _sandbox_name('t3test', uuid)
        try:
            sandbox('t3test', uuid)
        finally:
            _docker = old
            boxes.pop(name, None)
        return next(c for c in calls if c and c[0] == 'create')

    # Recording is a create-time env var. Single-check and run-only shells do not get it.
    assert 'NAGARE_RECORD_COMMANDS=1' in create_args(EXPR)
    assert 'NAGARE_RECORD_COMMANDS=1' not in create_args(PWD)
    assert 'NAGARE_RECORD_COMMANDS=1' not in create_args(run_uuid)
    # The whole last line, not a split of it.
    for last, ok in (('pwd; ls', True), ('ls; pwd', True), ('ls', False)):
        res, calls, _ = grade(PWD, last=last)
        assert res['results'][0]['ok'] is ok and res['results'][0]['last'] == last and res['results'][0]['scope'] == 'last'
        assert calls[0][-1] == 'tail -n 1 /tmp/.shell_history 2>/dev/null'

    def bash_records(typed, record=True):
        """Source the real rcfile with temp paths. Do not read the user's profile.

        record=True sets NAGARE_RECORD_COMMANDS, as a multi-check sandbox does. False leaves the original shell.
        """
        import shutil, tempfile
        bash = shutil.which('bash')
        assert bash, 'bash is required'
        rc_text = open(os.path.join(HERE, 'support', 'sandbox.bashrc')).read()
        init_text = 'echo INIT_MARKER_SHOULD_NOT_APPEAR\nexpr 999999 + 1\n'
        with tempfile.TemporaryDirectory() as d:
            hist, log, init = (os.path.join(d, n) for n in ('history', 'commands', 'init.sh'))
            rc_path = os.path.join(d, 'bashrc')
            patched = (rc_text.replace('/tmp/.shell_history', hist)
                       .replace('/tmp/.shell_commands', log)
                       .replace('/tmp/.lesson_init.sh', init))
            for token in ('/tmp/.shell_history', '/tmp/.shell_commands', '/tmp/.lesson_init.sh'):
                assert token not in patched, token
            open(init, 'w').write(init_text)
            os.chmod(init, 0o755)
            open(rc_path, 'w').write(patched)
            env = {'PATH': '/usr/bin:/bin:/usr/local/bin', 'TERM': 'dumb', 'HOME': d, 'LANG': 'C'}
            if record:
                env['NAGARE_RECORD_COMMANDS'] = '1'
            proc = subprocess.run([bash, '--noprofile', '--rcfile', rc_path, '-i'],
                                  input=typed.encode(), capture_output=True, env=env, timeout=15)
            assert proc.returncode == 0, proc.stderr.decode(errors='replace')
            assert not os.path.exists(init), 'lesson init did not run'
            transcript = proc.stdout.decode(errors='replace')
            logged = os.path.exists(log)
            assert logged is record, (record, logged)
            raw = open(log, 'rb').read() if logged else b''
            history = open(hist).read() if os.path.exists(hist) else ''
            return _nul_records(raw), history, transcript

    typed = """\
expr 123456 + 7890
expr 420 - 69
expr 123456 + 7890; expr 420 - 69
expr 123456 + 7890 && expr 420 - 69
false && echo SKIPPED
echo "expr 123456 + 7890; expr 420 - 69"
echo 'expr 123456 + 7890 && expr 420 - 69'
expr 123456 + 7890\\; expr 420 - 69
false
echo STATUS:$?
exit
"""

    records, history, transcript = bash_records(typed)
    assert records == [
        'expr 123456 + 7890',
        'expr 420 - 69',
        'expr 123456 + 7890',
        'expr 420 - 69',
        'expr 123456 + 7890',
        'expr 420 - 69',
        'false',
        'echo "expr 123456 + 7890; expr 420 - 69"',
        "echo 'expr 123456 + 7890 && expr 420 - 69'",
        'expr 123456 + 7890\\; expr 420 - 69',
        'false',
        'echo STATUS:$?',
        'exit',
    ], records
    assert 'echo SKIPPED' not in records
    assert not any(r == '_nagare_prompt' or 'history -a' in r or 'INIT_MARKER' in r or '999999' in r for r in records)
    assert history.splitlines() == [
        'expr 123456 + 7890',
        'expr 420 - 69',
        'expr 123456 + 7890; expr 420 - 69',
        'expr 123456 + 7890 && expr 420 - 69',
        'false && echo SKIPPED',
        'echo "expr 123456 + 7890; expr 420 - 69"',
        "echo 'expr 123456 + 7890 && expr 420 - 69'",
        'expr 123456 + 7890\\; expr 420 - 69',
        'false',
        'echo STATUS:$?',
        'exit',
    ], history.splitlines()
    assert 'STATUS:1' in transcript and 'STATUS:0' not in transcript, transcript
    assert 'INIT_MARKER_SHOULD_NOT_APPEAR' not in transcript
    # Native `;` and `&&` become two records; a quoted or escaped separator stays one, and grading uses those records.
    expect(EXPR, records[0:2], both)
    expect(EXPR, records[2:4], both)
    expect(EXPR, records[4:6], both)
    expect(EXPR, [records[7]], one)
    expect(EXPR, [records[8]], one)
    expect(EXPR, [records[9]], one)
    records, _, transcript = bash_records("""\
echo Investigating WorldBanc
history
true || echo SKIPPED_OR
cat <<< "hello"
cat <<'EOF.txt'
echo BODY_ONLY
EOF.txt
expr 123456 + 7890; expr 420 - 69
f() { echo FUNCTION_BODY; }
f
(echo SUBSHELL_BODY)
exit
""")
    expect(ECHO_HIST, records[:2], both)
    assert records[:4] == ['echo Investigating WorldBanc', 'history', 'true', 'cat <<< "hello"'], records
    # Bash versions format the here-document text differently; its body stays in one record.
    assert records[4].startswith('cat ') and 'BODY_ONLY' in records[4], records
    assert records[5:] == ['expr 123456 + 7890', 'expr 420 - 69', 'f', 'exit'], records
    expect(EXPR, records[5:7], both)
    assert 'FUNCTION_BODY' in transcript and 'SUBSHELL_BODY' in transcript
    # Single-check and run-only shells keep history -a and do not write a command log.
    off, off_hist, off_out = bash_records('pwd; ls\nfalse\necho STATUS:$?\nexit\n', record=False)
    assert off == []
    assert off_hist.splitlines() == ['pwd; ls', 'false', 'echo STATUS:$?', 'exit'], off_hist.splitlines()
    assert 'STATUS:1' in off_out and 'STATUS:0' not in off_out and 'INIT_MARKER_SHOULD_NOT_APPEAR' not in off_out, off_out
    print('ok: sandbox checks')
