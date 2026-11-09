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
        cid = _check(_docker('create', '-it', '--label', 'nagare=sandbox', '--label', f'nagare.user={user}', '--name', name,
                             '--network', 'none', '--memory', '256m', '--pids-limit', '128', '--cpus', '0.5',
                             *RUNTIME,
                             '--hostname', 'worldbanc', '--user', 'user', '-w', spec['cwd'], '-e', 'TERM=xterm-256color',
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


def check_sandbox(user, uuid):
    """Grade a Learn Linux lesson: 'last command contains' exactly, 'run this' by showing the output."""
    box = boxes.get(_sandbox_name(user, uuid))
    if not box:
        return {'error': 'Open the terminal and run your commands first.'}
    box.touch()
    spec = shell_spec(uuid)
    last = _docker('exec', box.name, 'sh', '-c', 'tail -n 1 /tmp/.shell_history 2>/dev/null').stdout.decode().strip()
    results = []
    for c in spec['checks']:
        want = (c.get('matchCommand') or {}).get('lastContains')
        if want:
            missing = [w for w in want if w not in last]
            results.append({'kind': 'match', 'ok': not missing, 'want': want, 'last': last,
                            'message': f"Your last command should contain: {', '.join(want)}"})
        if c.get('runCommand'):
            r = _docker('exec', '-u', 'user', '-w', spec['cwd'], box.name, 'bash', '-c', c['runCommand'], timeout=20)
            results.append({'kind': 'run', 'ok': None, 'command': c['runCommand'],
                            'output': (r.stdout + r.stderr).decode(errors='replace')[:4000]})
    graded = [r for r in results if r['ok'] is not None]
    return {'results': results, 'passed': all(r['ok'] for r in graded) and len(graded) == len(results),
            'review': any(r['ok'] is None for r in results) and all(r['ok'] for r in graded)}


# ---- lifecycle ----

def remove_all():
    """Remove every workspace and sandbox container (volumes, i.e. users' files, stay)."""
    ids = _docker('ps', '-aq', '--filter', 'label=nagare').stdout.split()
    if ids:
        _docker('rm', '-f', *[i.decode() for i in ids])
    with boxes_lock:
        boxes.clear()


def _reaper():
    while True:
        time.sleep(30)
        now = time.monotonic()
        with boxes_lock:
            idle = [b for b in boxes.values() if now - b.used > IDLE_S]
        for b in idle:
            _stop(b)


def start():
    """Call once at worker startup: clear leftovers from a previous run, then reap idle containers."""
    remove_all()
    _ensure_network()
    threading.Thread(target=_reaper, daemon=True).start()
