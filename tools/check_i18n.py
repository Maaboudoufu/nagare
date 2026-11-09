"""Every UI string has a Japanese translation: compares the t('…') / N_('…') keys in web/src (plus the English the
server sends, listed below) with web/src/lib/ja.json. Prints what's missing or unused; exit 1 if anything is missing.
Usage: python3 tools/check_i18n.py"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = re.compile(r"\b(?:t|N_)\('((?:[^'\\]|\\.)*)'")
sys.path.insert(0, os.path.join(ROOT, 'server'))
import gamify  # noqa: E402

SERVER = {a[i] for a in gamify.ACHIEVEMENTS for i in (1, 2)} | {
    # gateway/admin.go errors, shown in the admin page's notices
    "That isn't an email address", "Admins are set in .env and can't be signed out, banned or removed here",
    "That email is in ALLOWED_EMAILS in .env; remove it there", 'Bad mode', 'Unknown action', 'Bad request', 'JSON only'}


def keys():
    found = set(SERVER)
    for p in glob.glob(os.path.join(ROOT, 'web', 'src', '**', '*.js*'), recursive=True):
        found |= {re.sub(r"\\(.)", r'\1', k) for k in KEY.findall(open(p).read())}
    return found


if __name__ == '__main__':
    ja = json.load(open(os.path.join(ROOT, 'web', 'src', 'lib', 'ja.json')))
    want = keys()
    missing, unused = sorted(want - set(ja)), sorted(set(ja) - want)
    for k in missing:
        print('missing:', k)
    for k in unused:
        print('unused: ', k)
    bad = [k for k in want & set(ja) if set(re.findall(r'\{(\w+)\}', k)) != set(re.findall(r'\{(\w+)\}', ja[k]))]
    for k in bad:
        print('placeholders differ:', k)
    print(f'{len(want)} keys, {len(missing)} missing, {len(unused)} unused, {len(bad)} placeholder mismatches')
    sys.exit(1 if missing or bad else 0)
