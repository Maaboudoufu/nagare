"""Lesson help from Codex, on the learner's own ChatGPT account. Linking uses OpenAI's Codex OAuth device-code flow,
the one the Codex CLI and Hermes use: we show a code, the learner enters it at auth.openai.com, we get their tokens.

Hermetic: the worker calls OpenAI itself, never from a user's container. Codex gets the lesson text and the learner's
saved code as a prompt, with no tools: it can't run commands, read files or reach anything else. Tokens are kept in
data/codex/<user>.json (0600) and never sent to the browser. Requests are store:false.
Learners pick a model and reasoning effort in Settings, from the models their account offers.
Settings (environment): CODEX_MODEL (gpt-5.5), the default model
Self-check: python3 server/codex.py
"""
import base64, json, os, threading, time, urllib.error, urllib.parse, urllib.request

ISSUER = 'https://auth.openai.com'
CLIENT_ID = 'app_EMoamEEZ73f0CkXaXp7hrann'  # the Codex CLI's public OAuth client
DEVICE_URL = ISSUER + '/codex/device'  # where the learner enters the code
BASE = 'https://chatgpt.com/backend-api/codex'
MODEL = os.environ.get('CODEX_MODEL') or 'gpt-5.5'  # empty in .env means the default
UA = {'User-Agent': 'codex_cli_rs/0.0.0 (nagare)'}  # OpenAI's Cloudflare turns away Python's default (error 530)
EFFORTS = ('low', 'medium', 'high')  # when the account's model list doesn't say
DIR = os.path.join(os.environ.get('DATA_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')), 'codex')
MAX_LESSON, MAX_CODE, MAX_TURNS = 24000, 24000, 12  # characters, characters, earlier messages kept
# The answer style follows the i-have-adhd rules (github.com/ayghri/i-have-adhd): many learners here have ADHD.
INSTRUCTIONS = """You are a tutor inside Nagare, a site where people learn to code. Many learners have ADHD: small \
working memory, hard to start, easily lost in long text. Help them get unstuck on the lesson below.

Be super concise and easy to understand:
- First line: the one thing to do or look at, e.g. "Look at line 3: should health go up or down?" No intro.
- Plain words, short sentences. Explain any term the lesson hasn't taught yet in a few words.
- More than one step: a numbered list, one small action per step, at most 5 steps.
- One issue at a time. Mention a second problem only as a one-line question at the end.
- Errors: say the cause and the fix, matter-of-fact. Never "Oh no" or "Uh oh".
- No greetings, no recap, no "hope this helps" or "let me know".
- If something is still open, end with one small next step they can do in under two minutes.

Hints first: point at the line and the idea. Don't write the whole solution unless they clearly ask for it. Code: only \
the few lines that matter. Answer in Markdown, in the language the learner writes in. You can't run code or see \
anything beyond what's here."""

pending = {}  # user -> device login in progress: {device_auth_id, user_code, interval, expires}
lock = threading.Lock()  # ponytail: one lock for every user's token file; refreshes are rare
model_cache = {}  # user -> (when, models)


class NotLinked(Exception):
    pass


def _post(url, body, form=False, timeout=30):
    """(status, JSON answer) of a POST to OpenAI."""
    data = urllib.parse.urlencode(body).encode() if form else json.dumps(body).encode()
    req = urllib.request.Request(url, data, {**UA, 'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'{}')
        except ValueError:
            return e.code, {}


def _claims(jwt):
    """A JWT's payload. Not verified: it came straight from OpenAI over TLS, and is only read for display and expiry."""
    try:
        part = jwt.split('.')[1]
        return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))
    except (IndexError, ValueError, AttributeError):
        return {}


def _path(user):
    return os.path.join(DIR, f'{user}.json')


def _load(user):
    try:
        with open(_path(user)) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return None


def _save(user, tokens):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    tmp = _path(user) + '.tmp'
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as f:
        json.dump(tokens, f)
    os.replace(tmp, _path(user))


def _keep(tokens, got):
    """Tokens from an OpenAI answer merged over what we had (a refresh may leave some out)."""
    tokens = {**(tokens or {}), **{k: got[k] for k in ('id_token', 'access_token', 'refresh_token') if got.get(k)}}
    auth = _claims(tokens.get('id_token')).get('https://api.openai.com/auth', {})
    tokens['account_id'] = auth.get('chatgpt_account_id') or tokens.get('account_id', '')
    return tokens


# ---- linking ----

def status(user):
    tokens = _load(user)
    if tokens:
        return {'linked': True, 'email': _claims(tokens.get('id_token')).get('email', '')}
    p = pending.get(user)
    if p and p['expires'] > time.time():
        return {'linked': False, 'code': p['user_code'], 'url': DEVICE_URL, 'interval': p['interval']}
    return {'linked': False}


def start(user):
    """Ask OpenAI for a device code for this user to enter at DEVICE_URL."""
    code, got = _post(ISSUER + '/api/accounts/deviceauth/usercode', {'client_id': CLIENT_ID})
    if code != 200 or not got.get('device_auth_id'):
        return {'error': 'OpenAI did not give a sign-in code. Try again in a minute.'}
    pending[user] = {'device_auth_id': got['device_auth_id'], 'user_code': got.get('user_code') or got.get('usercode'),
                     'interval': max(int(got.get('interval') or 5), 3), 'expires': time.time() + 15 * 60}
    return status(user)


def poll(user):
    """Called by the browser every few seconds while the code is shown: links the account once it's been entered."""
    p = pending.get(user)
    if not p or p['expires'] < time.time():
        pending.pop(user, None)
        return {**status(user), 'expired': not _load(user)}
    code, got = _post(ISSUER + '/api/accounts/deviceauth/token', {'device_auth_id': p['device_auth_id'], 'user_code': p['user_code']})
    if code in (403, 404):  # not entered yet
        return status(user)
    pending.pop(user, None)
    if code != 200 or not got.get('authorization_code'):
        return {'linked': False, 'error': 'Linking failed. Try again.'}
    code, got = _post(ISSUER + '/oauth/token', {'grant_type': 'authorization_code', 'code': got['authorization_code'],
                                                 'redirect_uri': ISSUER + '/deviceauth/callback', 'client_id': CLIENT_ID,
                                                 'code_verifier': got.get('code_verifier', '')}, form=True)
    if code != 200 or not got.get('access_token'):
        return {'linked': False, 'error': 'Linking failed. Try again.'}
    with lock:
        _save(user, _keep(None, got))
    return status(user)


def unlink(user):
    pending.pop(user, None)
    model_cache.pop(user, None)
    with lock:
        try:
            os.remove(_path(user))
        except FileNotFoundError:
            pass
    return status(user)


def _access(user):
    """The user's access token and account id, refreshed first if it expires within a minute."""
    with lock:
        tokens = _load(user)
        if not tokens:
            raise NotLinked
        if _claims(tokens.get('access_token')).get('exp', 0) < time.time() + 60:
            code, got = _post(ISSUER + '/oauth/token', {'grant_type': 'refresh_token', 'refresh_token': tokens.get('refresh_token', ''),
                                                         'client_id': CLIENT_ID}, form=True)
            if code != 200 or not got.get('access_token'):
                if code in (400, 401):  # refresh token revoked or used up: they need to link again
                    os.remove(_path(user))
                    raise NotLinked
                raise RuntimeError('Could not reach OpenAI. Try again.')
            tokens = _keep(tokens, got)
            _save(user, tokens)
        return tokens['access_token'], tokens.get('account_id', '')


def _headers(user):
    token, account = _access(user)
    return {**UA, 'Authorization': f'Bearer {token}', 'chatgpt-account-id': account, 'originator': 'codex_cli_rs'}


def _model(m):
    """One entry of the account's model list, as the browser gets it."""
    efforts = [e.get('effort') if isinstance(e, dict) else e for e in m.get('supported_reasoning_levels') or []]
    return {'slug': m['slug'], 'name': m.get('display_name') or m['slug'], 'description': m.get('description') or '',
            'efforts': [e for e in efforts if isinstance(e, str)] or list(EFFORTS),
            'effort': m.get('default_reasoning_level') or 'medium'}


def models(user):
    """The models this account may use with Codex (asked of OpenAI, kept 10 minutes). Just the default if it won't say."""
    when, got = model_cache.get(user, (0, None))
    if time.time() - when < 600:
        return got
    got = []
    try:
        req = urllib.request.Request(BASE + '/models?client_version=1.0.0', headers=_headers(user))
        with urllib.request.urlopen(req, timeout=15) as r:
            got = [_model(m) for m in json.loads(r.read()).get('models', [])
                   if isinstance(m, dict) and isinstance(m.get('slug'), str) and m.get('visibility', 'list') == 'list']
    except (OSError, ValueError, AttributeError):
        pass
    got = got or [_model({'slug': MODEL})]
    model_cache[user] = (time.time(), got)
    return got


def choose(user, settings):
    """(model, effort) from the learner's settings, if their account offers them; the defaults otherwise."""
    offered = models(user)
    m = next((m for m in offered if m['slug'] == settings.get('codexModel')), None) \
        or next((m for m in offered if m['slug'] == MODEL), offered[0])
    effort = settings.get('codexEffort')
    return m['slug'], effort if effort in m['efforts'] else m['effort']


# ---- asking ----

def prompt(lesson, saved, question):
    """The learner's message: the lesson, their saved work on it, and their question."""
    parts = [f"# Lesson: {lesson.get('title', '')}\n\n{(lesson.get('readme') or '')[:MAX_LESSON]}"]
    code = saved.get('code') if isinstance(saved.get('code'), dict) else {}
    files = ''.join(f"\n## {name}\n```\n{text}\n```\n" for name, text in code.items() if isinstance(text, str))
    if files:
        parts.append('# My code' + files[:MAX_CODE])
    parts.append(f'# My question\n\n{question}')
    return '\n\n'.join(parts)


def body(lesson, saved, question, history, model=MODEL, effort=None):
    turns = [{'role': 'assistant' if m.get('role') == 'assistant' else 'user',
              'content': [{'type': 'output_text' if m.get('role') == 'assistant' else 'input_text', 'text': m['text'][:MAX_CODE]}]}
             for m in [m for m in history if isinstance(m, dict) and isinstance(m.get('text'), str)][-MAX_TURNS:]]
    # The lesson and code go with the newest question, so they're current even if the learner edited since.
    turns.append({'role': 'user', 'content': [{'type': 'input_text', 'text': prompt(lesson, saved, question)}]})
    out = {'model': model, 'instructions': INSTRUCTIONS, 'input': turns, 'store': False, 'stream': True}
    if effort:
        out['reasoning'] = {'effort': effort}
    return out


def ask(user, lesson, saved, question, history, settings=None):
    """Yields Codex's answer as it's written. Raises NotLinked, or RuntimeError with a message for the learner.
    settings: the learner's app settings, for their model and effort."""
    headers = _headers(user)
    model, effort = choose(user, settings or {})
    req = urllib.request.Request(BASE + '/responses', json.dumps(body(lesson, saved, question, history, model, effort)).encode(),
                                 {**headers, 'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
    try:
        r = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise NotLinked
        detail = e.read(500).decode(errors='replace')
        raise RuntimeError('Usage limit reached on your ChatGPT plan.' if e.code == 429 else f'Codex said no ({e.code}): {detail}')
    except OSError as e:
        raise RuntimeError(f'Could not reach Codex: {e}')
    with r:
        yield from events(r)


def events(lines):
    """Text deltas from a Responses API event stream (SSE lines as bytes)."""
    for line in lines:
        if not line.startswith(b'data:'):
            continue
        try:
            ev = json.loads(line[5:])
        except ValueError:
            continue
        kind = ev.get('type')
        if kind == 'response.output_text.delta':
            yield ev.get('delta', '')
        elif kind in ('response.failed', 'error'):
            err = ev.get('error') or (ev.get('response') or {}).get('error') or {}
            raise RuntimeError(err.get('message') or 'Codex stopped with an error.')
        elif kind == 'response.completed':
            return


if __name__ == '__main__':
    import tempfile
    sse = [b'event: x\n', b'data: {"type":"response.output_text.delta","delta":"Hel"}\n', b'\n', b'data: not json\n',
           b'data: {"type":"response.output_text.delta","delta":"lo"}\n', b'data: {"type":"response.completed"}\n',
           b'data: {"type":"response.output_text.delta","delta":"!"}\n']
    assert ''.join(events(sse)) == 'Hello'
    try:
        list(events([b'data: {"type":"response.failed","response":{"error":{"message":"nope"}}}\n']))
        raise AssertionError('a failed response passed')
    except RuntimeError as e:
        assert str(e) == 'nope'
    jwt = lambda c: 'h.' + base64.urlsafe_b64encode(json.dumps(c).encode()).decode().rstrip('=') + '.s'
    tok = _keep(None, {'id_token': jwt({'email': 'a@b.c', 'https://api.openai.com/auth': {'chatgpt_account_id': 'acc'}}),
                       'access_token': jwt({'exp': time.time() + 3600}), 'refresh_token': 'r1'})
    assert tok['account_id'] == 'acc' and _keep(tok, {'access_token': 'new'})['refresh_token'] == 'r1'
    b = body({'title': 'T', 'readme': 'R' * 99999}, {'code': {'main.py': 'print(1)', 'bad': 5}}, 'why?',
             [{'role': 'user', 'text': 'hi'}, {'role': 'assistant', 'text': 'yo'}, {'role': 'x'}, 'junk'] * 10)
    assert b['store'] is False and 'tools' not in b and len(b['input']) == MAX_TURNS + 1
    last = b['input'][-1]['content'][0]['text']
    assert 'print(1)' in last and 'why?' in last and len(last) < MAX_LESSON + 200
    with tempfile.TemporaryDirectory() as d:
        DIR = os.path.join(d, 'codex')
        assert status('u1') == {'linked': False}
        _save('u1', tok)
        assert oct(os.stat(_path('u1')).st_mode & 0o777) == '0o600'
        assert status('u1') == {'linked': True, 'email': 'a@b.c'} and _access('u1')[1] == 'acc'
        model_cache['u1'] = (time.time(), [_model({'slug': 'big', 'supported_reasoning_levels': [{'effort': 'high'}], 'default_reasoning_level': 'high'}),
                                           _model({'slug': 'small', 'supported_reasoning_levels': [{'effort': 'low'}, {'effort': 'medium'}]})])
        assert choose('u1', {'codexModel': 'small', 'codexEffort': 'low'}) == ('small', 'low')
        assert choose('u1', {'codexModel': 'small', 'codexEffort': 'high'}) == ('small', 'medium')  # not offered: its default
        assert choose('u1', {'codexModel': 'made-up'}) == ('big', 'high')  # not offered: the first one
        assert body({}, {}, 'q', [], 'small', 'low')['reasoning'] == {'effort': 'low'} and 'reasoning' not in body({}, {}, 'q', [])
        assert unlink('u1') == {'linked': False} and 'u1' not in model_cache
        try:
            _access('u1')
            raise AssertionError('unlinked user got a token')
        except NotLinked:
            pass
    print('ok: codex events, prompts and token storage')
