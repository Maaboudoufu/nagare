"""Restyle the generated CMPE 126 diagrams (courses/diagrams, panel bg #151920) to the app's tokens.

Rewrites colors, fonts, strokes and radii in place; layout is untouched.
Usage: python3 tools/restyle_diagrams.py FILE...
"""
import re, sys

SANS = 'IBM Plex Sans,system-ui,-apple-system,Segoe UI,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = '#0F1216'

# old palette -> muted app hues, same hue per state so legends and lesson text that name colors stay true:
# amber=current, blue=compared, green=done, red=removed.
COLORS = {
    '#151920': BG,
    '#d4d8de': '#E9EBEE', '#858d98': '#9BA3AF', '#9aa1ab': '#9BA3AF',
    '#1b2028': '#161A21', '#353c47': '#2E3540', '#3a414b': '#4A5360', '#5a626d': '#626B78',
    '#a08654': '#C4A26A', '#8f7a58': '#C4A26A', '#b89c6c': '#C4A26A', '#3a3226': '#241F16', '#3a3128': '#241F16',
    '#6382a8': '#7E9AC4', '#8aa3c2': '#7E9AC4', '#212b38': '#18202E',
    '#6a9480': '#6EA586', '#86a894': '#6EA586', '#1f2d27': '#142019',
    '#966a71': '#C47B75', '#b48b91': '#C47B75', '#2e2328': '#221718',
}
# Text never carries state color: the shape beside it already does. Colored text -> light neutral.
STATE_TEXT = {'#b89c6c', '#8aa3c2', '#86a894', '#b48b91'}
STATE = {'#C4A26A', '#7E9AC4', '#6EA586', '#C47B75'}
CODE = re.compile(r'^[-+]?[\d.,]+%?$|^[∞øØ∅—–-]$|[()\[\]{}=<>*&;|_#^~]|::|->|0x')

def attr(tag, name):
    m = re.search(rf"\b{name}='([^']*)'", tag)
    return m and m.group(1)

def setattr_(tag, name, val):
    if re.search(rf"\b{name}='[^']*'", tag):
        return re.sub(rf"\b{name}='[^']*'", f"{name}='{val}'", tag)
    return tag.replace('<' + tag[1:].split()[0], '<' + tag[1:].split()[0] + f" {name}='{val}'", 1)

def recolor(s):
    return re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: COLORS.get(m.group(0).lower(), m.group(0)), s)

def text(m):
    tag, body = m.group(1), m.group(2)
    if (attr(tag, 'fill') or '').lower() in STATE_TEXT:
        tag = setattr_(tag, 'fill', '#C2C8D0')
    tag = recolor(tag).replace("font-weight='bold'", "font-weight='600'")
    size = float(attr(tag, 'font-size') or 12)
    words = body.strip()
    if CODE.search(words) or not re.search(r'[A-Za-z]', words):
        tag = setattr_(tag, 'font-family', MONO)
        if size < 11: tag = setattr_(tag, 'font-size', '11')
    else:
        y = float(attr(tag, 'y') or 99)
        if size >= 13 and y <= 44 and attr(tag, 'text-anchor') == 'middle':  # panel title
            tag = setattr_(setattr_(tag, 'font-weight', '600'), 'fill', '#E9EBEE')
            tag = setattr_(tag, 'font-size', '14')
            body = body.replace(words, words[:1].upper() + words[1:], 1)
        elif size < 11.5:
            tag = setattr_(tag, 'font-size', '11.5')
    return tag + body + '</text>'

def shape(m):
    tag = recolor(m.group(0))
    if "width='100%'" in tag and "height='100%'" in tag:   # panel card -> flat page
        return setattr_(tag, 'rx', '0')
    stroke, sw = attr(tag, 'stroke'), attr(tag, 'stroke-width')
    if stroke and sw and float(sw) < 2:
        tag = setattr_(tag, 'stroke-width', '1.5' if stroke in STATE else '1')
    rx = attr(tag, 'rx')
    if rx and tag.startswith('<rect') and 4 <= float(rx) <= 8:
        tag = setattr_(tag, 'rx', '3')
    return tag

def restyle(src):
    src = src.replace(f"font-family='{MONO}'", f"font-family='{SANS}'")
    root = src[:src.index('>')]
    if 'font-family' not in root:
        src = src.replace(root, root + f" font-family='{SANS}'", 1)
    src = re.sub(r"(<text\b[^>]*>)(.*?)</text>", text, src, flags=re.S)
    src = re.sub(r"<(?:rect|line|circle|path|polygon|polyline)\b[^>]*>", shape, src)
    return recolor(src)

if __name__ == '__main__':
    for f in sys.argv[1:]:
        s = open(f).read()
        assert '#151920' in s, f'{f}: not a generated diagram (or already restyled)'
        open(f, 'w').write(restyle(s))
