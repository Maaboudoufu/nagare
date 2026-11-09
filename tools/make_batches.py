"""Write ready-to-run Chrome scripts for scraping boot.dev, from the templates in this folder.

Usage:  python3 tools/make_batches.py scrape OUT_DIR [--all]     (live courses in tools/raw/catalog.json not yet
                                                                  scraped; --all re-scrapes every one)
        python3 tools/make_batches.py capture OUT_DIR [--new]    (diagram lessons; --new skips ones already captured)

Full re-scrape (from the project root, with the Chrome DevTools MCP and a tab logged in to boot.dev):
  1. navigate_page to any boot.dev lesson with this initScript, so scraper scripts can reuse your login:
       (() => { const f = window.fetch; window.fetch = function (i, o) { try { const a = new Headers((o && o.headers) || (i instanceof Request ? i.headers : undefined)).get('authorization'); if (a) window.__auth = a; } catch (e) {} return f.apply(this, arguments); }; })();
  2. Refresh tools/raw/catalog.json (all courses + paths): in the same tab, evaluate
       async () => { const H = {headers: {authorization: window.__auth}};
         const all = await (await fetch("https://api.boot.dev/v1/courses", H)).json();
         const paths = await (await fetch("https://api.boot.dev/v1/static/paths")).json();
         return [{paths: paths.map(p => ({slug: p.slug, title: p.title, description: p.shortDescription, courses: p.courseUUIDs})),
                  courses: all.map(c => ({uuid: c.uuid, slug: c.slug, title: c.title, status: c.status, language: c.language,
                                          description: c.shortDescription, numLessons: c.numLessons}))}]; }
     with filePath = tools/raw/catalog.json.
  3. make_batches.py scrape OUT_DIR, then run each OUT_DIR/scrape{N}.js with evaluate_script
     (sourcePath = the script, filePath = a new tools/raw/courses{N}.json, waitForStableDom = false).
  4. make_batches.py capture OUT_DIR --new, then run each OUT_DIR/capture{N}.js the same way
     (filePath = a new tools/raw/diagrams{N}.json). Run batches one at a time: they drive the same tab.
  5. python3 tools/build.py .
  6. docker compose up -d --build   (rebuilds the image with the new data)
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    s = open(p).read()
    return json.loads(s[s.index('['):s.rindex(']') + 1])


def write(out, name, placeholder, batches):
    tpl = open(os.path.join(HERE, f'{name}.js')).read()
    assert placeholder in tpl, f'{placeholder} missing from {name}.js'
    os.makedirs(out, exist_ok=True)
    for i, b in enumerate(batches):
        open(os.path.join(out, f'{name}{i}.js'), 'w').write(tpl.replace(placeholder, json.dumps(b)))
    print(f'wrote {len(batches)} {name} scripts to {out}, batch sizes {[len(b) for b in batches]}')


def raw_course_files():
    return sorted(glob.glob(os.path.join(HERE, 'raw', 'devops*.json')) + glob.glob(os.path.join(HERE, 'raw', 'courses*.json')))


def capture_list():
    """Lessons with Excalidraw diagrams, with what capture.js needs to recognise them on the page."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    todo = []
    have = {(l['uuid'], x['ref']) for p in glob.glob(os.path.join(HERE, 'raw', 'diagrams*.json'))
            for l in load(p) for x in l['svgs'] if x['svg']} if '--new' in sys.argv else set()
    for p in raw_course_files():
        for c in load(p):
            for ch in c['chapters']:
                for l in ch['lessons']:
                    diags = l.get('diagrams') or {}
                    if not diags:
                        continue
                    readme = next(v for k, v in l.items() if k.startswith('lessonData'))['readme']
                    h1 = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', re.search(r'^#\s+(.+)$', readme, re.M).group(1))
                    # refs may carry a #fragment (highlighted elements) on top of the diagram's name
                    refs = [{'ref': s, 'alt': a} for a, s in re.findall(r'!\[([^\]]*)\]\(<?([^)\s>]+)', readme)
                            if s.split('#')[0] in diags and (l['uuid'], s) not in have]
                    if not refs:
                        continue
                    todo.append({'uuid': l['uuid'], 'title': l['title'], 'h1': norm(h1), 'refs': refs})
    assert todo, 'no diagrams found: scrape the courses into tools/raw/ first'
    return todo


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('scrape', 'capture'):
        sys.exit(__doc__)
    mode, out = sys.argv[1], sys.argv[2]
    if mode == 'scrape':
        catalog = load(os.path.join(HERE, 'raw', 'catalog.json'))[0]
        have = set() if '--all' in sys.argv else {c['uuid'] for p in raw_course_files() for c in load(p)}
        todo = [c['uuid'] for c in catalog['courses'] if c['status'] == 'live' and c['uuid'] not in have]
        assert todo, 'every live course is already in tools/raw/ (pass --all to re-scrape)'
        write(out, 'scrape', '__BATCH__', [todo[i:i + 5] for i in range(0, len(todo), 5)])
    else:
        todo = capture_list()
        write(out, 'capture', '__LESSONS__', [todo[i::3] for i in range(3)])
