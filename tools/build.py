"""Turn scraped boot.dev JSON (tools/raw/) into the app's data: courses/*.json, courses/diagrams/, progress.json.
Usage (from the project root):  python3 tools/build.py .
Reads tools/raw/catalog.json (courses + paths), devops*.json / courses*.json (scraped courses), diagrams*.json.
Progress you made in the local app is kept; boot.dev progress from the scrape is merged under it.
To re-scrape boot.dev first, see make_batches.py."""
import glob, hashlib, json, os, re, sys

out = sys.argv[1]
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw')
_lock = f'{out}/media.lock.json'
MEDIA_LOCK = json.load(open(_lock)) if os.path.exists(_lock) else {}
MEDIA_EMBED = re.compile(r'(!\[[^\]]*\]\(\s*<?)(https?://[^)\s>]+)')
srcs = sorted(glob.glob(f'{RAW}/devops*.json') + glob.glob(f'{RAW}/courses*.json'))
diagram_srcs = sorted(glob.glob(f'{RAW}/diagrams*.json'))


def load(p):
    s = open(p).read()
    return json.loads(s[s.index('['):s.rindex(']') + 1])


# Excalidraw diagrams as boot.dev rendered them: {(lesson uuid, readme ref): svg text}
SVGS = {(l['uuid'], x['ref']): x['svg'] for p in diagram_srcs for l in load(p) for x in l['svgs'] if x['svg']}
embedded = 0


def embed_diagrams(l, readme):
    """Save each captured diagram as a file and point the readme's relative ref at it."""
    global embedded
    for (uuid, ref), svg in SVGS.items():
        if uuid != l['uuid']:
            continue
        base, _, frag = ref.partition('#')  # a #fragment highlights part of the drawing: keep it a separate file
        name = re.sub(r'[^A-Za-z0-9_-]', '_', os.path.basename(base).removesuffix('.excalidraw'))
        if frag:
            name += '-' + hashlib.sha1(frag.encode()).hexdigest()[:8]
        rel = f"courses/diagrams/{l['uuid']}/{name}.svg"
        os.makedirs(os.path.dirname(f'{out}/{rel}'), exist_ok=True)
        open(f'{out}/{rel}', 'w').write(svg)
        new = readme.replace(f']({ref})', f']({rel})').replace(f'](<{ref}>)', f']({rel})')
        embedded += new != readme
        readme = new
    return readme


# Learn Linux sandbox files from /v1/lessons/<uuid>/shell-state. Paid lessons a free account can't fetch (402) get
# every captured file instead: the closest thing to their worldbanc tree.
SHELL_STATES = load(f'{RAW}/shell_state.json')[0] if os.path.exists(f'{RAW}/shell_state.json') else {}
SHELL_FALLBACK = {'starterDirs': sorted({d for s in SHELL_STATES.values() for d in s.get('starterDirs') or []}),
                  'starterFiles': list({f['name']: f for s in SHELL_STATES.values() for f in s.get('starterFiles') or []}.values())}


def nonnull(d):
    return {k: v for k, v in (d or {}).items() if v not in (None, [], {}, '')}


def cli_step(st, base):
    if st.get('cliCommand'):
        c = st['cliCommand']
        cmd, expects = c['command'], []
        for t in c.get('tests') or []:
            t = nonnull(t)
            if 'exitCode' in t: expects.append(f"exit code {t['exitCode']}")
            if 'stdoutContainsAll' in t: expects.append('output contains: ' + ', '.join(map(repr, t['stdoutContainsAll'])))
            if 'stdoutContainsNone' in t: expects.append("output doesn't contain: " + ', '.join(map(repr, t['stdoutContainsNone'])))
            if 'stdoutLinesGT' in t: expects.append(f"more than {t['stdoutLinesGT']} lines of output")
            if 'stdoutJq' in t: expects.append('jq check: ' + json.dumps(t['stdoutJq']))
    else:
        h = st['httpRequest']
        r = h['request']
        url = r['fullURL'].replace('${baseURL}', base) if base and base != 'override' else r['fullURL']
        cmd = f"{r['method']} {url}"
        body = r.get('bodyJSON') or r.get('bodyForm')
        if body: cmd += '\n' + json.dumps(body, indent=2)
        expects = []
        for t in h.get('tests') or []:
            t = nonnull(t)
            if 'statusCode' in t: expects.append(f"status {t['statusCode']}")
            expects += [f"{k}: {json.dumps(v)}" for k, v in t.items() if k != 'statusCode']
    return {'description': st.get('description', ''), 'command': cmd, 'expects': expects}


def lesson(l):
    data = next(v for k, v in l.items() if k.startswith('lessonData'))
    x = {'uuid': l['uuid'], 'title': l['title'], 'type': l['type'], 'readme': embed_diagrams(l, data['readme'])}
    if data.get('starterFiles'):
        x['lang'] = data.get('progLang')
        x['files'] = [f for f in data['starterFiles'] if not f['name'].endswith('_js_test.go')]
        if data.get('codeExpectedOutput') is not None: x['expected'] = data['codeExpectedOutput']
    if data.get('questions'): x['questions'] = data['questions']
    if data.get('cliData'):
        base = data['cliData'].get('baseURLDefault')
        x['steps'] = [cli_step(st, base) for st in data['cliData'].get('steps') or []]
        x['cli'] = data['cliData'].get('steps') or []  # raw checks, graded by server/grader.py
        x['baseURL'] = base
    if data.get('shellData'):
        sh = data['shellData']
        checks = []
        for c in sh.get('checks') or []:
            if (c.get('matchCommand') or {}).get('lastContains'):
                checks.append('Your last command should contain: ' + ', '.join(c['matchCommand']['lastContains']))
            if c.get('runCommand'):
                checks.append(f"Checked by running: {c['runCommand']}")
        x['steps'] = [{'description': f"The shell starts in {sh.get('cwd')}", 'command': None, 'expects': checks}]
        # The sandbox's starter files (up to MBs) go in their own file that only the server reads.
        state = SHELL_STATES.get(l['uuid'], SHELL_FALLBACK)
        x['sandbox'] = 'exact' if l['uuid'] in SHELL_STATES else 'approximate'
        os.makedirs(f'{out}/courses/shell', exist_ok=True)
        json.dump({'cwd': sh.get('cwd') or '/home/user', 'root': sh.get('starterFilesRoot') or '/home/user',
                   'dirs': (state.get('starterDirs') or []) + (sh.get('starterDirs') or []),
                   'files': state.get('starterFiles') or [] if state is not SHELL_FALLBACK else '_fallback',  # stored once
                   'init': sh.get('initCommands') or [],
                   'checks': sh.get('checks') or []}, open(f"{out}/courses/shell/{l['uuid']}.json", 'w'))
    if data.get('gitHubChecks'):
        x['steps'] = [{'description': st['stepType'].replace('_', ' '), 'command': None,
                       'expects': [json.dumps(v) for k, v in nonnull(st).items() if k != 'stepType']}
                      for st in data['gitHubChecks'].get('steps') or []]
    if 'studentPrompt' in data: x['prompt'] = data['studentPrompt']
    return x


os.makedirs(f'{out}/courses', exist_ok=True)
prog_path = f'{out}/progress.json'
local = json.load(open(prog_path)) if os.path.exists(prog_path) else {}
progress, index = {}, []
catalog = load(f'{RAW}/catalog.json')[0]
scraped = {c['uuid']: c for p in srcs for c in load(p)}  # later files win if a course was re-scraped
live = [c['uuid'] for c in catalog['courses'] if c['status'] == 'live']
missing = [u for u in live if u not in scraped]
assert not missing, f'{len(missing)} live courses not scraped yet: run make_batches.py scrape'
# "All" order: every path's courses in path order, then courses no path uses.
order = list(dict.fromkeys([u for p in catalog['paths'] for u in p['courses']] + live))
courses = [scraped[u] for u in order if u in live]
for c in courses:
    chapters = [{'title': ch['title'], 'lessons': [lesson(l) for l in ch['lessons']]} for ch in c['chapters']]
    if MEDIA_LOCK:  # lesson media that tools/fetch_media.py downloaded: link the local copies
        for ch in chapters:
            for l in ch['lessons']:
                for obj, key in [(l, 'readme')] + [(q, 'question') for q in l.get('questions') or []]:
                    if obj.get(key):
                        obj[key] = MEDIA_EMBED.sub(lambda m: m.group(1) + ('/media/' + MEDIA_LOCK[m.group(2)]['path'] if m.group(2) in MEDIA_LOCK else m.group(2)), obj[key])
    json.dump({'slug': c['slug'], 'title': c['title'], 'chapters': chapters}, open(f"{out}/courses/{c['slug']}.json", 'w'))
    index.append({'slug': c['slug'], 'title': c['title'], 'language': c['language'], 'description': c['description'],
                  'lessons': [l['uuid'] for ch in chapters for l in ch['lessons']]})
    for ch in c['chapters']:
        for l in ch['lessons']:
            u, p = l.get('user') or {}, {}
            if l.get('isComplete'): p['done'] = True
            files = (u.get('previousSubmissionCode') or {}).get('files')
            if files: p['code'] = {f['name']: f['content'] for f in files}
            if u.get('multipleChoiceAnswers'): p['answers'] = u['multipleChoiceAnswers']
            if p: progress[l['uuid']] = p
for uuid, p in local.items():  # work done in the local app wins over boot.dev's copy
    progress.setdefault(uuid, {}).update(p)

if os.path.isdir(f'{out}/courses/shell'):
    json.dump(SHELL_FALLBACK['starterFiles'], open(f'{out}/courses/shell/_fallback.json', 'w'))
slugs = {c['uuid']: c['slug'] for c in courses}
paths = [{'slug': p['slug'], 'title': p['title'], 'description': p['description'],
          'courses': [slugs[u] for u in p['courses']]} for p in catalog['paths']]
json.dump({'courses': index, 'paths': paths}, open(f'{out}/courses/index.json', 'w'))
json.dump(progress, open(prog_path, 'w'), indent=1)
n = sum(len(c['lessons']) for c in index)
assert n == sum(len(ch['lessons']) for c in courses for ch in c['chapters'])
assert embedded == len(SVGS), f'only {embedded} of {len(SVGS)} diagrams were linked into lesson text'
print(f'{len(index)} courses, {n} lessons, {len(paths)} paths, {len(progress)} with progress, {embedded} diagrams')
