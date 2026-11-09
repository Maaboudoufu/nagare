"""Download every image and video the lessons link to, so nothing loads from the internet at runtime.

Usage (from the project root):  python3 tools/fetch_media.py [--images-only]
  - Files land in media/<host>/<path> (about 11 GB, mostly lesson videos; git-ignored, mounted into the app).
  - media.lock.json records each file's SHA-256 and size; a later run verifies against it, so the media
    set is the same every time. Commit that file.
  - The lessons in courses/*.json are rewritten to /media/... links (tools/build.py does the same on a rebuild).
Safe to re-run: it skips files already downloaded and verified, and retries rate-limited hosts.
"""
import concurrent.futures, glob, hashlib, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, 'media')
LOCK = os.path.join(ROOT, 'media.lock.json')
EMBED = re.compile(r'(!\[[^\]]*\]\(\s*<?)(https?://[^)\s>]+)')


def local_path(url):
    """https://host/a/b.png -> host/a/b.png (URL-decoded, no query, never outside media/)."""
    u = urllib.parse.urlsplit(url)
    parts = [p for p in urllib.parse.unquote(u.path).split('/') if p not in ('', '.', '..')]
    return '/'.join([u.netloc.lower()] + parts)


def lesson_texts(lesson):
    yield lesson, 'readme'
    for q in lesson.get('questions') or []:
        yield q, 'question'


def course_files():
    return [p for p in sorted(glob.glob(os.path.join(ROOT, 'courses', '*.json'))) if not p.endswith('index.json')]


def remote_urls():
    urls = set()
    for p in course_files():
        for ch in json.load(open(p))['chapters']:
            for l in ch['lessons']:
                for obj, key in lesson_texts(l):
                    urls.update(m.group(2) for m in EMBED.finditer(obj.get(key) or ''))
    return urls


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def fetch(url, lock):
    rel = local_path(url)
    dest = os.path.join(MEDIA, rel)
    want = lock.get(url)
    if want and os.path.exists(dest) and os.path.getsize(dest) == want['size'] and sha256(dest) == want['sha256']:
        return url, want, 'ok'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'nagare-media-fetch/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest + '.part', 'wb') as f:
                while block := r.read(1 << 20):
                    f.write(block)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 5:
                return url, None, f'HTTP {e.code}'
        except OSError as e:
            if attempt == 5:
                return url, None, str(e)[:60]
        time.sleep(2 ** attempt)  # rate limits (imgur) and flaky connections
    got = {'path': rel, 'sha256': sha256(dest + '.part'), 'size': os.path.getsize(dest + '.part')}
    if want and (got['sha256'], got['size']) != (want['sha256'], want['size']):
        os.remove(dest + '.part')
        return url, None, 'checksum differs from media.lock.json (the file changed upstream)'
    os.replace(dest + '.part', dest)
    return url, got, 'downloaded'


def rewrite(lock):
    """Point the lessons' media links at /media/... for every file we have."""
    changed = 0
    for p in course_files():
        c = json.load(open(p))
        before = json.dumps(c)
        for ch in c['chapters']:
            for l in ch['lessons']:
                for obj, key in lesson_texts(l):
                    if obj.get(key):
                        obj[key] = EMBED.sub(lambda m: m.group(1) + ('/media/' + lock[m.group(2)]['path'] if m.group(2) in lock else m.group(2)), obj[key])
        if json.dumps(c) != before:
            json.dump(c, open(p, 'w'))
            changed += 1
    return changed


def main():
    lock = json.load(open(LOCK)) if os.path.exists(LOCK) else {}
    urls = sorted(remote_urls() | set(lock))
    if '--images-only' in sys.argv:
        urls = [u for u in urls if not u.lower().endswith(('.mp4', '.webm', '.mov'))]
    print(f'{len(urls)} files')
    failed, done = [], 0
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for url, entry, status in ex.map(lambda u: fetch(u, lock), urls):
            done += 1
            if entry:
                lock[url] = entry
            else:
                failed.append((status, url))
            if done % 25 == 0 or done == len(urls):
                print(f'  {done}/{len(urls)}', flush=True)
                json.dump(dict(sorted(lock.items())), open(LOCK, 'w'), indent=1)  # progress survives an interruption
    json.dump(dict(sorted(lock.items())), open(LOCK, 'w'), indent=1)
    print(f'lessons rewritten: {rewrite(lock)} course files')
    for status, url in failed:
        print(f'  failed ({status}): {url}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
