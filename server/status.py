"""Uptime for the status page (the profile menu's Status). Every CHECK_S the worker checks what learners depend on and
keeps the outages, 90 days of them, in data/status.json:
  App         this app. Down for any gap between checks: the worker wasn't running, so nobody could use it.
  Workspaces  Docker, which runs every code check, terminal and sandbox.
  Codex       OpenAI's Codex service, for Ask Codex. Any answer counts; only no answer (or a 5xx) is down.
Self-check: python3 server/status.py
"""
import json, os, subprocess, threading, time, urllib.error, urllib.request

CHECK_S = 120
KEEP_S = 90 * 86400
NAMES = ('App', 'Workspaces', 'Codex')
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
lock = threading.Lock()


def path():
    return os.path.join(DATA_DIR, 'status.json')


def load():
    try:
        with open(path()) as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        data = {}
    data.setdefault('outages', {})
    for name in NAMES:
        data['outages'].setdefault(name, [])
    return data


def save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path() + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, path())


def record(data, up, now):
    """Fold one round of checks ({name: bool}) into data: open an outage on the first failure, close it on recovery.
    A gap since the last round longer than three rounds is an App outage."""
    data.setdefault('since', now)
    last = data.get('last')
    if last and now - last > 3 * CHECK_S:
        data['outages']['App'].append([last, now])
    for name, ok in up.items():
        runs = data['outages'][name]
        ongoing = runs and runs[-1][1] is None
        if not ok and not ongoing:
            runs.append([now, None])
        elif ok and ongoing:
            runs[-1][1] = now
    for name in NAMES:
        data['outages'][name] = [r for r in data['outages'][name] if r[1] is None or r[1] > now - KEEP_S]
    data['since'] = max(data['since'], now - KEEP_S)
    data['last'] = now
    return data


def checks():
    def docker():
        try:
            return subprocess.run(['docker', 'info', '--format', '{{.ServerVersion}}'], capture_output=True, timeout=15).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def codex():
        import codex as cx  # noqa: PLC0415 (here so this file's self-check doesn't need it)
        try:
            urllib.request.urlopen(urllib.request.Request(cx.BASE + '/models', headers=cx.UA), timeout=15).close()
            return True
        except urllib.error.HTTPError as e:  # 401 without a token: it answered
            return e.code < 500
        except OSError:
            return False
    return {'Workspaces': docker(), 'Codex': codex()}


def report():
    """What the page shows: when tracking began, now, and each service's outages (an ongoing one ends now)."""
    with lock:
        data = load()
    now = time.time()
    return {'since': data.get('since', now), 'now': now,
            'services': [{'name': n, 'outages': [[s, e or now, e is None] for s, e in data['outages'][n]]} for n in NAMES]}


def _loop():
    while True:
        up = checks()
        try:
            with lock:
                save(record(load(), up, time.time()))
        except OSError as e:
            print(f'status: {e}', flush=True)
        time.sleep(CHECK_S)


def start():
    threading.Thread(target=_loop, daemon=True).start()


if __name__ == '__main__':
    d = record({'outages': {n: [] for n in NAMES}}, {'Workspaces': True, 'Codex': True}, 1000)
    assert d['since'] == 1000 and all(not r for r in d['outages'].values())
    record(d, {'Workspaces': False, 'Codex': True}, 1120)
    record(d, {'Workspaces': False, 'Codex': True}, 1240)  # still down: one outage, not two
    assert d['outages']['Workspaces'] == [[1120, None]]
    record(d, {'Workspaces': True, 'Codex': True}, 1360)
    assert d['outages']['Workspaces'] == [[1120, 1360]]
    record(d, {'Workspaces': True, 'Codex': True}, 1360 + 3600)  # the worker was off for an hour
    assert d['outages']['App'] == [[1360, 4960]]
    later = 4960 + KEEP_S + 1
    record(d, {'Workspaces': True, 'Codex': True}, later)  # 90 days on: old outages go (the gap itself is a new one)
    assert d['outages']['App'] == [[4960, later]] and d['outages']['Workspaces'] == [] and d['since'] == 4961
    print('ok: status outages')
