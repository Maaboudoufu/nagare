"""Draws the achievement medals: one 24x24 pixel-art scene per achievement (server/gamify.py), each with the same dog
doing what the achievement is about, in a frame of the tier's metal. Writes web/src/assets/medals.svg, a sprite of
one <symbol> per achievement id; Badge in web/src/components/Achievements.jsx shows them.

Usage: python3 tools/make_medals.py            write the sprite
       python3 tools/make_medals.py sheet.png  also save a contact sheet to look at (needs Pillow)

A scene is a list of steps, painted in order on a 24x24 grid (the frame takes the outer ring, so scenes use 1..22):
  ('#', color, x, y, w, h)   a filled rectangle
  (sprite, x, y)             a sprite from SPRITES, its top-left corner at x, y; add 'f' to mirror it
Colors are one letter each (PALETTE, the DawnBringer 32 palette plus the dog's cream); '.' or a space is see-through."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
import gamify  # noqa: E402

N = 24
PALETTE = {
    'K': '#222034', 'D': '#45283C', 'M': '#663931', 'B': '#8F563B', 'O': '#DF7126', 'T': '#D9A066', 'E': '#EEC39A',
    'Y': '#FBF236', 'L': '#99E550', 'G': '#6ABE30', 'A': '#37946E', 'F': '#4B692F', 'N': '#3F3F74', 'U': '#306082',
    'I': '#5B6EE1', 'S': '#639BFF', 'C': '#5FCDE4', 'Q': '#CBDBFC', 'W': '#FFFFFF', 'H': '#9BADB7', 'J': '#847E87',
    'Z': '#595652', 'V': '#76428A', 'X': '#AC3232', 'R': '#D95763', 'P': '#D77BBA', 'w': '#F2E2C4',
}
TIER = {'bronze': '#C08A62', 'silver': '#A3ABB8', 'gold': '#C9A64E'}  # the contact sheet's; the app uses its own --tier

SPRITES = {k: v.strip('\n').split('\n') for k, v in {
    # The dog: tan, cream muzzle and belly, brown floppy ears, red collar. HEAD is 9x7; BODY (sitting) goes under it.
    'HEAD': """
..TTTTT..
.TTTTTTT.
BBTTTTTBB
BBTKTKTBB
BBTwwwTBB
.BwwKwwB.
..wwPww..""",
    'BODY': """
..RRRRR..
.TTTwTTT.
.TTwwwTT.
.TTwwwTT.
.wwTTTww.""",
    'TAIL': """
.T
TT
T.""",
    'STAND': """
.........TTTT.
........BTTTTT
T.......BBTKTw
TT......BBTTwwK
.TTTTTTTTBTwwP
.TTTTTTTTRR...
.TTTTTTTTTT...
.TTwwwwwwTT...
.TT.TT.TT.TT..
.ww.ww.ww.ww..""",
    'RUN': """
..........TTTT.
.........BTTTTT
TT.......BBTKTw
.TT......BBTTwwK
..TTTTTTTTBTwwP
..TTTTTTTTRR...
.TTTwwwwwTTT...
TTT.......TTT..
ww.........ww..""",
    'LIEBODY': """
..TTTTTT...
.TTTTTTTT.T
TTTTTTTTTTT
TTTTTTTTww.""",
    'PAWS': """
ww.....ww""",
    # What the dog wears. Each is placed relative to HEAD (see the scenes).
    'GRADCAP': """
...KKKKK...
KKKKKKKKKKK
..KKKKKKK.Y
..........Y""",
    'HARDHAT': """
..YYYYY..
.YYYOYYY.
YYYYYYYYY""",
    'ARMYHAT': """
..FFFFF..
.FFAFFFF.
FFFFFFFFF""",
    'CAPTAIN': """
..WWWWW..
.WWWYWWW.
.KKKKKKK.""",
    'PIRATE': """
....KKK....
..KKKWKKK..
.KKKKKKKKK.
KKKKKKKKKKK""",
    'AVIATOR': """
..MMMMM..
.MMMMMMM.
BKCCKCCKB""",
    'SHADES': """
.KKKKKKK.
..KK.KK..""",
    'EYEPATCH': """
..KKKKK..
..KK.....
...K.....""",
    'DIVEMASK': """
.YYYYYYY.
.YCKCKCY.""",
    'HELMET': """
...WWWWWWW...
..WNNNNNNNW..
.WNQNNNNNNNW.
.WQNNNNNNNNW.
.WNNNNNNNNNW.
.WNNNNNNNNNW.
.WNNNNNNNNNW.
.WNNNNNNNNNW.
..WNNNNNNNW..
...WWWWWWW...""",
    'HEADSET': """
..KKKKKKK..
.K.......K.
.K.......K.
RR.......RR
RR.......RR
.K.........
..KR.......""",
    'BIRD': """
.II..
IIKIO
.III.""",
    'SCARF': """
.RRRRRRR.
.....RXR.
.....RR..""",
    'BOWTIE': """
.XX...XX.
.XXXKXXX.
.XX...XX.""",
    # Things around the dog.
    'SUN': """
..YYY..
.YYYYY.
YYYYYYY
YYYYYYY
YYYYYYY
.YYYYY.
..YYY..""",
    'SUNRISE': """
....YYY....
..YYYYYYY..
.YYYYYYYYY.
.YYYYYYYYY.
YYYYYYYYYYY
YYYYYYYYYYY""",
    'MOON': """
..WWW.
.WW...
WW....
WW....
.WW...
..WWW.""",
    'STAR': """
.Y.
YYY
.Y.""",
    'FIRE': """
...O...
..OO...
..OYO..
.OOYOO.
.OYYYO.
.OYWYO.
MMBMMBM""",
    'CLOUD': """
..WWW..
.WWWWW.
WWWWWWW""",
    'TUBE': """
.RRWWRRRWWRR.
RRRWWRRRWWRRR
.RRWWRRRWWRR.""",
    'CANOE': """
B................B
MBBBBBBBBBBBBBBBBM
.MMMMMMMMMMMMMMMM.""",
    'PADDLE': """
....E
....E
...E.
...E.
..E..
..E..
.BB..
BBB..
BB...""",
    'BOARD': """
.WWWWWRRWWWWW.
..WWWWRRWWWW..""",
    'WAVE': """
...........WWWWWWW....
.........WWQQQQQQQWW..
........WQQ.....IIQQW.
........WQ.......IIIQW
.........W.......IIIIQ
................IIIIIQ
...............IIIIIII
..............IIIIIIII
.............QIIIIIIII
...........QQIIIIIIIII
.........QQIIIIIIIIIII
......QQQIIIIIIIIIIIII
...QQQIIIIIIIIIIIIIIII
QQQIIIIIIIIIIIIIIIIIII""",
    'FLAG': """
ZRRRR
ZRRRR
ZRRR.
Z....
Z....
Z....
Z....""",
    'SCROLL': """
WWRRWW
WWRRWW""",
    'HAMMER': """
JJJJJ
JJJJJ
..E..
..E..
..E..
..E..""",
    'TERMINAL': """
HHHHHHHHHH
HKKKKKKKKH
HKGKKKKKKH
HKKGKKKKKH
HKGKKGGKKH
HKKKKKKKKH
HHHHHHHHHH
...ZZZZ...""",
    'LAPTOP': """
.HHHHHHHHH.
.HHHHHHHHH.
.HHHHWHHHH.
.HHHHHHHHH.
.HHHHHHHHH.
JJJJJJJJJJJ""",
    'PLANE': """
RR..................
RRR...............K.
RRRRRRRRRRRRRRRRR.K.
RRRRRRRRRRRRRRRRRRK.
.RRRRWWWWWWWWRRRR.K.
...RRRRRRRRRRRR...K.
.....Z.....Z........""",
    'DB': """
.CCCCC.
CQQQQQC
CCCCCCC
IIIIIII
CCCCCCC
IIIIIII
CCCCCCC
IIIIIII
.IIIII.""",
    'BONE': """
W.....W
WWWWWWW
W.....W""",
    'BIGBONE': """
WW.........WW
WWWWWWWWWWWWW
WW.........WW""",
    'NOTE': """
.KK
.K.
.K.
KK.""",
    'BUBBLE': """
.WWWWWWWWW.
WWWWWWWWWWW
WWWWWWWWWWW
WWWWWWWWWWW
WWWWWWWWWWW
WWWWWWWWWWW
.WWWWWWWWW.
..WW.......
.W.........""",
    'SBUB': """
.WWW.
WWWWW
WWWWW
.WWW.
.W...""",
    'H': """
K.K
K.K
KKK
K.K
K.K""",
    'I': """
KKK
.K.
.K.
.K.
KKK""",
    '?': """
KK.
..K
.K.
...
.K.""",
    'FISH': """
O.OOO.
OOOOKO
O.OOO.""",
    'BALLOON': """
.RRR.
RRWRR
RRRRR
RRRRR
.RRR.
..R..""",
    'FOUNTAIN': """
..Q.Q.Q.Q..
.Q.CQQQC.Q.
Q..CQCQC..Q
...CCQCC...
...CQCQC...
...CCQCC...
...CQCQC...
...CCQCC...
.HHHHHHHHH.
HHHHHHHHHHH""",
    'HULL': """
MBBBBBBBBBBBBBBBBM
.MBBBBBBBBBBBBBBM.
..MMMMMMMMMMMMMM..""",
    'SAIL': """
W......
WW.....
WWW....
WWWW...
WWWWW..
WWWWW..
WWWWWW.
WWWWWW.
WWWWWWW
WWWWWWW""",
    'FLOWER': """
.PPP.
PPYPP
PYYYP
PPYPP
.PPP.
..G..
.GG..
..G..
..GG.
..G..""",
    'PAPER': """
WWWWWWWWW
WWWWWWWWW
WWRWRWRWW
WWRWRWRWW
WWWWWWWWW
WWWRRRWWW
WWRRRRRWW
WWRRRRRWW
WWWRRRWWW
WWWWWWWWW""",
    'RIBS': """
B..............B
BB............BB
.BBEBEBEBEBEBBB.
..BBBBBBBBBBBB..
...Z........Z...
...Z........Z...""",
    'WHEEL': """
....B....
.B.BBB.B.
..BEEEB..
.BE.B.EB.
BBEBBBEBB
.BE.B.EB.
..BEEEB..
.B.BBB.B.
....B....""",
    'ROCKET': """
..R..
.RRR.
.WWW.
.WCW.
.WWW.
.WWW.
RWWWR
R.O.R
..Y..""",
    'SNAKE': """
....IIII..
...IKIIII.
.RRIIIIII.
.....YII..
.....YII..
..IIIIIII.
.IIYYYYYII
.IIIIIIIII
..IIIIIII.""",
    'GOPHER': """
..BBB..
.BKBKB.
.BBwBB.
.BwWwB.
MMBBBMM
MMMMMMM""",
    'SAFE': """
JJJJJJJJJJ
JHHHHHHHHJ
JHHKKKHHHJ
JHKWWWKHYJ
JHKWKWKHYJ
JHKWWWKHYJ
JHHKKKHHHJ
JHHHHHHHHJ
JJJJJJJJJJ
K........K""",
    'CHIP': """
.H.H.H.H.
KKKKKKKKK
KZKKKKKKK
KKKKKKKKK
KKKKKKKKK
.H.H.H.H.""",
    'STICK': """
.G.........G.
MMMMMMMMMMMMM""",
    'CHEST': """
.MMMMMMM.
MBBBBBBBM
MYYYYYYYM
MBBBYBBBM
MBBBBBBBM
MMMMMMMMM""",
    'COINS': """
..Y.Y..
.YYYYY.""",
    'UMBRELLA': """
....RRR....
..RRWWWRR..
.RRWWRWWRR.
RRWWRRRWWRR""",
    'BOLT': """
...YY
..YY.
.YY..
YYYY.
..YY.
.YY..
YY...
Y....""",
    'SHOVEL': """
BBB
.E.
.E.
.E.
.E.
.E.
HHH
HHH
.H.""",
    'DIRT': """
..MMM..
.MBMMM.
MMMMBMM""",
    'RIPPLES': """
..QQQQQQ..
.Q......Q.
.Q..QQ..Q.
..QQQQQQ..""",
    'LENS': """
.HHHHH.
HQQQQQH
HQKKWQH
HQKKQQH
HQQQQQH
.HHHHH.
.....MM.
......MM""",
    'BOOK': """
XXXXXXXXXXXXXX
XXXXXXXXXWWWWX""",
}.items()}
SPRITES['BALLOON2'] = [r.replace('R', 'Y') for r in SPRITES['BALLOON']]
for name, color in [('BOOK2', 'I'), ('BOOK3', 'G'), ('BOOK4', 'V'), ('BOOK5', 'O')]:
    SPRITES[name] = [SPRITES['BOOK'][0].replace('X', color), 'X' + SPRITES['BOOK'][1][1:].replace('X', color)]
SPRITES['MOUNT'] = ['.' * (9 - j) + 'H' * (j + 2) + 'J' * (j + 2) + '.' * (9 - j) for j in range(10)]
SPRITES['BRICKS'] = ['E' * 12 if j % 3 == 2 else ''.join('E' if (i + j // 3 * 3) % 6 == 5 else 'R' for i in range(12)) for j in range(9)]


def box(c, x, y, w, h):
    return ('#', c, x, y, w, h)


def dots(c, *at):
    return [('#', c, x, y, 1, 1) for x, y in at]


def sky(c='S', ground=None, y=18):
    return [box(c, 1, 1, 22, 22)] + ([box(ground, 1, y, 22, 23 - y)] if ground else [])


def water(y, c='U', crest='C'):
    """Water from row y down, with a broken line of crests on top."""
    return [box(c, 1, y, 22, 23 - y)] + dots(crest, *[(x, y) for x in range(1, 23) if x % 4 < 2])


def sit(x, y, tail=True):
    """The dog sitting, facing you: 9 wide, 12 tall."""
    return [('TAIL', x + 8, y + 8)] * tail + [('HEAD', x, y), ('BODY', x, y + 7)]


STARS = dots('W', (3, 3), (9, 2), (15, 5), (20, 9), (5, 8), (18, 2))
SCENES = {
    # Lessons done
    'first-light': [box('N', 1, 1, 22, 6), box('V', 1, 7, 22, 5), box('P', 1, 12, 22, 6), box('F', 1, 18, 22, 5),
                    ('SUNRISE', 11, 12), *dots('Y', (10, 10), (16, 9), (21, 11)), *sit(2, 6)],
    'getting-warm': [*sky('N', 'F'), *STARS, ('FIRE', 2, 11), *sit(12, 6)],
    'in-the-flow': [*sky(), ('CLOUD', 14, 2), *water(13), ('HEAD', 7, 5), ('TUBE', 5, 12), *dots('Q', (3, 17), (4, 17), (17, 19), (18, 19), (9, 21), (10, 21))],
    'riverbed': [*sky('S', 'B'), box('M', 1, 20, 22, 3), box('C', 12, 20, 11, 2), ('DIRT', 15, 15), ('SHOVEL', 12, 9), *sit(2, 6), ('HARDHAT', 2, 4)],
    'deep-water': [box('U', 1, 1, 22, 22), box('N', 1, 14, 22, 9), box('Y', 2, 6, 20, 12), *dots('U', (2, 6), (21, 6)), *dots('N', (2, 17), (21, 17)),
                   box('Z', 11, 3, 2, 3), box('Z', 11, 3, 4, 1), box('H', 6, 7, 11, 9), box('C', 7, 8, 9, 7), ('HEAD', 7, 8),
                   box('O', 1, 10, 1, 4), *dots('Q', (18, 3), (19, 5), (4, 20), (3, 3))],
    'open-sea': [*sky(), ('SUN', 15, 2), *water(18), box('Z', 12, 3, 1, 13), ('SAIL', 13, 4), ('HEAD', 2, 8), ('CAPTAIN', 2, 6), ('HULL', 2, 15)],
    # Streaks and days
    'ripple': [*sky('S', 'G'), box('U', 11, 18, 12, 5), ('RIPPLES', 12, 18), *sit(1, 6), *dots('J', (16, 15))],
    'steady-current': [*sky(), *water(15), ('HEAD', 4, 6), box('R', 6, 13, 5, 1), ('CANOE', 2, 13), ('PADDLE', 14, 8), *dots('Q', (4, 19), (5, 19), (15, 20), (16, 20))],
    'tidal-force': [*sky(), ('WAVE', 1, 3), *water(17, 'I', 'Q'), ('STAND', 2, 6), ('BOARD', 2, 16)],
    'perennial': [*sky('S', 'G'), box('C', 1, 21, 22, 1), ('FLOWER', 15, 8), *sit(2, 6), *dots('P', (13, 19), (20, 20)), *dots('Y', (12, 20), (21, 19))],
    'watermark': [*sky('A', 'F', 19), ('PAPER', 12, 6), *sit(2, 7)],
    'four-seasons': [box('L', 1, 1, 11, 11), box('C', 12, 1, 11, 11), box('O', 1, 12, 11, 11), box('Q', 12, 12, 11, 11),
                     *dots('P', (3, 3), (5, 6), (2, 9)), box('Y', 18, 2, 3, 3), *dots('X', (2, 14), (4, 18), (3, 21)), *dots('W', (19, 14), (21, 18), (18, 21), (20, 16)),
                     *sit(7, 5, tail=False), ('SCARF', 7, 12)],
    # Courses
    'headwaters': [*sky(), ('CLOUD', 2, 3), ('MOUNT', 1, 13), box('W', 9, 13, 6, 1), box('C', 12, 14, 1, 3), box('C', 13, 17, 1, 3), box('C', 12, 20, 1, 3),
                   ('FLAG', 17, 7), *sit(7, 1, tail=False)],
    'confluence': [box('V', 1, 1, 22, 22), box('D', 1, 20, 22, 3), ('STAR', 2, 2), ('STAR', 18, 2), ('STAR', 19, 10), *sit(6, 8), ('GRADCAP', 5, 6), ('SCROLL', 15, 16)],
    'delta': [box('U', 1, 1, 22, 22), ('BOOK', 4, 13), ('BOOK2', 5, 15), ('BOOK3', 4, 17), ('BOOK4', 5, 19), ('BOOK5', 4, 21), *sit(7, 1)],
    'builder': [*sky('S', 'Z', 20), ('BRICKS', 11, 11), ('HAMMER', 15, 4), *sit(2, 8), ('HARDHAT', 2, 6)],
    'shipwright': [*sky('S', 'E', 19), ('HEAD', 7, 6), ('HARDHAT', 7, 4), ('RIBS', 3, 13), ('HAMMER', 17, 5)],
    # Kinds of lesson
    'shell-shocked': [box('D', 1, 1, 22, 22), box('Z', 1, 20, 22, 3), ('TERMINAL', 12, 12), *sit(2, 8), ('ARMYHAT', 2, 6)],
    'helmsman': [*sky(), *water(19), ('HEAD', 7, 4), ('CAPTAIN', 7, 2), box('R', 9, 11, 5, 1), box('T', 8, 12, 7, 3), ('WHEEL', 7, 12)],
    'sharp-eye': [box('A', 1, 1, 22, 22), box('F', 1, 20, 22, 3), *sit(5, 8), ('LENS', 9, 9)],
    'clear-water': [*sky(), box('G', 1, 8, 22, 2), box('C', 1, 10, 22, 13), *dots('Q', (3, 12), (4, 12), (17, 14), (18, 14), (8, 19), (9, 19)),
                    ('HEAD', 7, 1), ('PAWS', 7, 8), ('FISH', 3, 15), ('FISH', 14, 17, 'f'), ('BONE', 8, 20), *dots('H', (2, 22), (19, 22), (20, 22))],
    'test-pilot': [*sky(), ('CLOUD', 2, 16), ('CLOUD', 14, 18), ('PLANE', 1, 11), ('HEAD', 7, 5), ('AVIATOR', 7, 5), box('R', 6, 12, 11, 1)],
    'flight-hours': [box('K', 1, 1, 22, 22), *STARS, ('HELMET', 4, 3), ('HEAD', 6, 5), box('W', 7, 13, 7, 5), box('H', 8, 14, 5, 1), box('R', 9, 15, 3, 2),
                     box('W', 6, 18, 3, 2), box('W', 12, 18, 3, 2), ('ROCKET', 17, 11)],
    'query-crafter': [box('N', 1, 1, 22, 22), box('K', 1, 20, 22, 3), ('DB', 15, 11), *sit(3, 8), ('BIGBONE', 1, 13)],
    'hello-world': [*sky('S', 'G', 20), ('BUBBLE', 11, 1), ('H', 13, 2), ('I', 17, 2), *sit(2, 8)],
    'sounding-board': [box('V', 1, 1, 22, 22), box('D', 1, 20, 22, 3), ('BUBBLE', 11, 1), ('?', 15, 2), *sit(2, 9), ('HEADSET', 1, 8)],
    # Languages
    'polyglot': [box('A', 1, 1, 22, 22), box('F', 1, 20, 22, 3), ('SBUB', 12, 1), ('SBUB', 17, 6), ('SBUB', 12, 11),
                 box('R', 13, 2, 3, 2), box('I', 18, 7, 3, 2), box('G', 13, 12, 3, 2), *sit(2, 8)],
    'seven-seas': [*sky('S', 'E', 19), box('U', 1, 15, 22, 4), ('CHEST', 12, 14), ('COINS', 13, 12), *sit(2, 8), ('PIRATE', 1, 5), ('EYEPATCH', 2, 10)],
    'pythonista': [box('D', 1, 1, 22, 22), box('M', 1, 20, 22, 3), ('SNAKE', 12, 11), *sit(2, 8)],
    'gopher': [*sky('S', 'G', 19), ('CLOUD', 13, 3), ('GOPHER', 14, 14), *sit(2, 7)],
    'type-safe': [box('U', 1, 1, 22, 22), box('N', 1, 20, 22, 3), ('SAFE', 12, 10), *sit(2, 8)],
    'low-level': [box('F', 1, 1, 22, 22), box('A', 1, 5, 22, 1), box('A', 4, 5, 1, 18), box('A', 17, 1, 1, 12), *dots('Y', (4, 5), (17, 5), (20, 20)),
                  ('CHIP', 12, 16), ('LIEBODY', 9, 11), ('HEAD', 2, 8), ('PAWS', 2, 15)],
    'version-controlled': [box('K', 1, 1, 22, 22), box('Z', 15, 3, 1, 17), box('Z', 16, 8, 3, 1), box('Z', 19, 8, 1, 8),
                           box('O', 14, 3, 3, 2), box('O', 14, 11, 3, 2), box('O', 14, 18, 3, 2), box('C', 18, 14, 3, 2), *sit(2, 8), ('STICK', 0, 13)],
    # Times of day, big days, the rest
    'night-owl': [box('N', 1, 1, 22, 22), ('MOON', 15, 2), *dots('W', (3, 3), (9, 2), (5, 7), (20, 10)), box('M', 1, 19, 22, 4), ('HEAD', 6, 7), box('T', 7, 14, 7, 1), ('LAPTOP', 5, 13)],
    'early-bird': [box('C', 1, 1, 22, 9), box('E', 1, 10, 22, 8), box('G', 1, 18, 22, 5), ('SUNRISE', 11, 12), *sit(2, 6), ('BIRD', 4, 3), ('NOTE', 11, 2)],
    'deep-dive': [box('I', 1, 1, 22, 5), box('U', 1, 6, 22, 17), box('E', 1, 21, 22, 2), ('FISH', 15, 15), box('G', 3, 17, 1, 4), box('G', 5, 19, 1, 2),
                  *sit(6, 6), ('DIVEMASK', 6, 8), box('R', 15, 3, 1, 7), *dots('O', (15, 2)), *dots('Q', (17, 5), (18, 3), (17, 1), (3, 9), (4, 6))],
    'flash-flood': [box('N', 1, 1, 22, 22), ('BOLT', 16, 1), *dots('Q', (3, 2), (2, 3), (9, 3), (8, 4), (13, 7), (12, 8), (5, 6), (4, 7)), *water(18, 'I', 'Q'),
                    ('RUN', 3, 9), *dots('W', (2, 17), (4, 16), (17, 17), (19, 16))],
    'weekend-tide': [*sky(), ('SUN', 2, 2), box('U', 1, 12, 22, 3), box('E', 1, 15, 22, 8), ('UMBRELLA', 11, 4), box('M', 16, 8, 1, 12),
                     box('R', 1, 19, 13, 2), ('LIEBODY', 9, 15), ('HEAD', 2, 12), ('SHADES', 2, 14), ('PAWS', 2, 19)],
    'make-it-yours': [box('D', 1, 1, 22, 22), box('Y', 4, 2, 16, 17), box('O', 5, 3, 14, 15), box('C', 6, 4, 12, 13), ('HEAD', 7, 6), ('BODY', 7, 13), box('C', 7, 17, 9, 1),
                      ('BOWTIE', 7, 12), box('Y', 9, 20, 6, 2)],
    'rising': [*sky(), ('CLOUD', 1, 18), ('CLOUD', 15, 20), ('BALLOON', 4, 1), ('BALLOON2', 13, 2), box('Z', 6, 7, 1, 3), box('Z', 15, 8, 1, 2), box('Z', 7, 10, 8, 1), *sit(7, 10)],
    'wellspring': [*sky(), ('FOUNTAIN', 6, 13), *sit(7, 1, tail=False)],
}


def paint(steps):
    grid = [['.'] * N for _ in range(N)]
    for step in steps:
        if step[0] == '#':
            _, c, x, y, w, h = step
            for j in range(y, y + h):
                for i in range(x, x + w):
                    grid[j][i] = c
            continue
        name, x, y, *flip = step
        for j, row in enumerate(SPRITES[name]):
            for i, c in enumerate(row[::-1] if flip else row):
                if c not in '. ' and 0 <= y + j < N and 0 <= x + i < N:
                    grid[y + j][x + i] = c
    inside = lambda i, j: 1 <= i <= 22 and 1 <= j <= 22 and (i, j) not in {(1, 1), (22, 1), (1, 22), (22, 22)}
    return [[c if inside(i, j) else '.' for i, c in enumerate(row)] for j, row in enumerate(grid)]


def frame():
    """The ring around every scene: one pixel thick, corners cut."""
    return ([(i, j) for i in range(2, 22) for j in (0, 23)] + [(i, j) for j in range(2, 22) for i in (0, 23)]
            + [(1, 1), (22, 1), (1, 22), (22, 22)])


def pips(tier):
    """Studs on the frame's bottom edge: one for bronze, two for silver, three for gold, so the tier isn't color alone."""
    return [(i, 23) for x in {'bronze': [11], 'silver': [8, 14], 'gold': [5, 11, 17]}[tier] for i in (x, x + 1)]


def runs(cells):
    """Pixels as an SVG path, one rectangle per horizontal run."""
    d, cells = [], sorted(set(cells), key=lambda p: (p[1], p[0]))
    while cells:
        x, y = cells.pop(0)
        w = 1
        while cells and cells[0] == (x + w, y):
            cells.pop(0)
            w += 1
        d.append(f'M{x} {y}h{w}v1h-{w}z')
    return ''.join(d)


def symbol(a):
    grid = paint(SCENES[a.id])
    by_color = {}
    for j, row in enumerate(grid):
        for i, c in enumerate(row):
            if c != '.':
                by_color.setdefault(c, []).append((i, j))
    paths = ''.join(f'<path fill="{PALETTE[c]}" d="{runs(cells)}"/>' for c, cells in sorted(by_color.items()))
    return (f'<symbol id="{a.id}" viewBox="0 0 {N} {N}">{paths}<path fill="currentColor" d="{runs(frame())}"/>'
            f'<path fill="#fff" fill-opacity=".8" d="{runs(pips(a.tier))}"/></symbol>')


def sheet(path, scale=6, cols=7, gap=4):
    from PIL import Image
    todo = [a for a in gamify.ACHIEVEMENTS if a.id in SCENES]
    cell = N * scale + gap * scale
    img = Image.new('RGB', (cols * cell, -(-len(todo) // cols) * cell), '#151920')
    rgb = lambda h: tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
    for n, a in enumerate(todo):
        tile = Image.new('RGBA', (N, N), (0, 0, 0, 0))
        for j, row in enumerate(paint(SCENES[a.id])):
            for i, c in enumerate(row):
                if c != '.':
                    tile.putpixel((i, j), rgb(PALETTE[c]) + (255,))
        for p in frame():
            tile.putpixel(p, rgb(TIER[a.tier]) + (255,))
        for p in pips(a.tier):
            tile.putpixel(p, (255, 255, 255, 255))
        tile = tile.resize((N * scale, N * scale), Image.NEAREST)
        img.paste(tile, (n % cols * cell + gap * scale // 2, n // cols * cell + gap * scale // 2), tile)
    img.save(path)


if __name__ == '__main__':
    missing = [a.id for a in gamify.ACHIEVEMENTS if a.id not in SCENES]
    if len(sys.argv) > 1:
        sheet(sys.argv[1])
    if missing:
        sys.exit('no scene yet for: ' + ', '.join(missing))
    out = os.path.join(ROOT, 'web', 'src', 'assets', 'medals.svg')
    with open(out, 'w') as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg">\n<!-- Made by tools/make_medals.py: edit the scenes there, not here. -->\n'
                + '\n'.join(symbol(a) for a in gamify.ACHIEVEMENTS) + '\n</svg>\n')
    print(f'{len(gamify.ACHIEVEMENTS)} medals written to {os.path.relpath(out, ROOT)}')
