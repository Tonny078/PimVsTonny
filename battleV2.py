#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   PIM  vs  TONNY  —  Dragon Ball Z Pixel Art Battle  ║
║   Animated: Pillow + Tkinter  (NOT a GIF)            ║
║   Pixel art, DBZ beams, power-ups, full auto-battle  ║
╚══════════════════════════════════════════════════════╝
"""

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import random, math

# ════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════
SCALE  = 4          # pixel-art zoom (each logical px → 4×4 screen px)
LW, LH = 320, 180   # logical canvas
SW, SH = LW * SCALE, LH * SCALE
FPS    = 24
MS     = max(1, 1000 // FPS)
GY     = 148        # ground Y (logical)
MAX_HP = 100
MOVE_SPEED = 4.8
RUSH_SPEED = 7.2
JUMP_VY = -7.4
KICK_VY = -8.1
HIT_STUN = 7
DOWN_STUN = 14
STAND_STUN = 8
REACTIVE_BLOCK_CHANCE = 0.35
REACTIVE_BLOCK_CHANCE_BEAM = 0.45
BURST_TIME = 84
SHIELD_TIME = 90
RAGE_TIME = 96
MODE_COOLDOWN = 88
FLIGHT_DRAIN = 0.70
FLIGHT_MIN_EN = 16.0
FLIGHT_HOLD_MIN = 42
FLIGHT_HOLD_MAX = 66
OFFENSE_CHAIN_FRAMES = 24
SCARY_TRIGGER_CHANCE = 0.004
HIT_FLASH_FRAMES = 4
DAMAGE_FLOAT_LIFE = 22
PIM_AURA_COL = (100, 255, 100)
TONNY_AURA_COL = (180, 100, 255)

# Pre-bake star field
random.seed(13)
STARS = [(random.randint(0, LW-1),
          random.randint(0, GY - 14),
          random.randint(80, 255)) for _ in range(90)]
random.seed()

# ════════════════════════════════════════════════════════
#  SPRITE ENGINE
# ════════════════════════════════════════════════════════
def build_sprite(rows, pal):
    """Parse ASCII art + palette into {w, h, px} dict.  '.' = transparent."""
    w = max(len(r) for r in rows)
    h = len(rows)
    px = []
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c != '.' and c in pal:
                px.append((x, y, pal[c]))
    return {'w': w, 'h': h, 'px': px}


def make_down_sprite(spr):
    """Create a flattened side-lying variant for downed/back-fall states."""
    flat_px = []
    for x, y, col in spr['px']:
        rx = y
        ry = spr['w'] - 1 - x
        ry = int(ry * 0.72)
        flat_px.append((rx, ry, col))

    minx = min(x for x, _, _ in flat_px)
    miny = min(y for _, y, _ in flat_px)
    px = [(x - minx, y - miny, col) for x, y, col in flat_px]
    w = max(x for x, _, _ in px) + 1
    h = max(y for _, y, _ in px) + 1
    return {'w': w, 'h': h, 'px': px}


def blit(draw, spr, ox, oy, flip=False, gray=False):
    W = spr['w']
    for (x, y, col) in spr['px']:
        lx = ox + (W - 1 - x if flip else x)
        ly = oy + y
        if 0 <= lx < LW and 0 <= ly < LH:
            if gray:
                g = int(col[0] * 0.30 + col[1] * 0.59 + col[2] * 0.11)
                col = (g, g, g)
            draw.point((lx, ly), fill=col)


# ════════════════════════════════════════════════════════
#  SPRITE: PIM  — bald head, over-ear headphones, blue shirt
# ════════════════════════════════════════════════════════
_PP = {
    'H': (12, 10, 10),      # headphone band
    'C': (70, 70, 82),      # ear-cup dark
    'L': (128, 126, 138),   # ear-cup highlight
    'S': (232, 178, 128),   # skin
    'D': (188, 136, 86),    # skin shadow
    'e': (26, 16, 6),       # eye
    'n': (208, 154, 102),   # nose
    'm': (170, 90, 68),     # mouth / lips
    'B': (50, 82, 175),     # blue shirt
    'b': (36, 60, 132),     # shirt shadow
    'T': (40, 50, 100),     # trousers
    't': (25, 32, 68),      # trousers dark
    'K': (18, 14, 10),      # boots
    'A': (232, 178, 128),   # arm / hand skin
    'W': (255, 255, 255),   # shirt collar white
}

PIM_SPR = build_sprite([
    # 0         1
    # 0123456789012345
    "....HHHHHHHH....",  # 0  headphone band arcs over head
    "...CLlHHHHlLC...",  # 1  ear cups
    "..LSSSSSSSSSSL..",  # 2  bald head (cups still on side)
    "..LSSSSSSSSSSL..",  # 3
    "...SeeSSSeeSSS..",  # 4  eyes
    "...SSSnnSSSSS...",  # 5  nose bridge
    "...SDmmmmDSSS...",  # 6  mouth
    "...SSSSSSSSSSS..",  # 7  chin
    "..WWWWWWWWWWWW..",  # 8  shirt collar
    "..BBBBBBBBBBBb..",  # 9  shirt
    "..BbBBBBBBBBBb..",  # 10 shirt
    ".A.bBBBBBBBBb.A.",  # 11 arms extended
    ".A..BBBBBBBB..A.",  # 12 lower arms
    "....TTTTTTTTTT..",  # 13 trousers
    "....TTttttttTT..",  # 14
    "....TTT....TTT..",  # 15 legs
    "...KKKKK..KKKKK.",  # 16 boots
], _PP)

# ════════════════════════════════════════════════════════
#  SPRITE: TONNY — cap + brim, glasses, dark hoodie, blue fire
# ════════════════════════════════════════════════════════
_TP = {
    'V': (22, 18, 10),      # cap body dark
    'v': (36, 30, 18),      # cap mid-tone
    'W': (8,  6,  2),       # visor / brim
    'w': (14, 11,  5),      # visor highlight edge
    'S': (196, 150, 100),   # skin
    'D': (158, 114, 64),    # skin shadow
    'G': (36, 140, 228),    # glasses frame (blue)
    'g': (160, 212, 252),   # glasses lens tint
    'e': (18, 12,  4),      # eye behind lens
    'm': (154, 78, 58),     # mouth
    'H': (26, 22, 18),      # hoodie dark
    'h': (44, 40, 34),      # hoodie mid
    'P': (28, 28, 34),      # trousers dark
    'p': (18, 18, 24),      # trousers darker
    'K': (14, 10,  8),      # boots
    'A': (196, 150, 100),   # arm skin
    'f': (24, 114, 252),    # blue flame core
    'F': (90, 170, 252),    # blue flame bright
}

TONNY_SPR = build_sprite([
    # 0         1
    # 0123456789012345
    ".....VVVVVVVV...",  # 0  cap top
    "....VvVVVVVVvV..",  # 1
    "...WWwWWWWWwWW..",  # 2  brim (wider than cap)
    "..SSSSSSSSSSSSS.",  # 3  forehead
    "..SGGgSSSSGGgS..",  # 4  glasses frames + lenses
    "..SSeSSSSSeSS...",  # 5  eyes visible through lens
    "...SSSSDdSSSSS..",  # 6  nose
    "...SSSmmmSSSSS..",  # 7  mouth
    "...SSSSSSSSSSS..",  # 8  chin
    "..HHHHHHHHHHH...",  # 9  hoodie neck
    "..HhHHhHHhHHHH..",  # 10 hoodie
    ".A.hHHHHHHHHh.A.",  # 11 arms
    ".A..HHHHHHHH..A.",  # 12 lower arms
    "....PPPPPPPPPP..",  # 13 trousers
    "....PPppppppPP..",  # 14
    "....PPP....PPP..",  # 15 legs
    "...KKKKK..KKKK..",  # 16 boots
], _TP)

PIM_DOWN_SPR = make_down_sprite(PIM_SPR)
TONNY_DOWN_SPR = make_down_sprite(TONNY_SPR)

# ════════════════════════════════════════════════════════
#  PARTICLES
# ════════════════════════════════════════════════════════
class Particle:
    __slots__ = ('x','y','vx','vy','col','life','maxl','sz')

    def __init__(self, x, y, vx, vy, col, life, sz=1):
        self.x  = float(x);   self.y  = float(y)
        self.vx = float(vx);  self.vy = float(vy)
        self.col = col;       self.life = life
        self.maxl = life;     self.sz = sz

    def step(self):
        self.x  += self.vx;  self.y  += self.vy
        self.vy += 0.20;     self.vx *= 0.93
        self.life -= 1
        return self.life > 0

    def draw(self, draw):
        a  = self.life / self.maxl
        col = tuple(int(c * a) for c in self.col)
        ix, iy = int(self.x), int(self.y)
        if self.sz == 1:
            if 0 <= ix < LW and 0 <= iy < LH:
                draw.point((ix, iy), fill=col)
        else:
            s = self.sz
            x0 = max(0, ix - s)
            y0 = max(0, iy - s)
            x1 = min(LW - 1, ix + s)
            y1 = min(LH - 1, iy + s)
            if x0 <= x1 and y0 <= y1:
                draw.rectangle([x0, y0, x1, y1], fill=col)


PARTS = []
DAMAGE_FLOATS = []


def _damage_color_for_fighter(f):
    return PIM_AURA_COL if f['name'] == 'Pim' else TONNY_AURA_COL


def spawn_damage_float(target, dmg, source):
    DAMAGE_FLOATS.append({
        'x': float(target['cx'] + random.randint(-5, 5)),
        'y': float(target['cy'] - 10 + random.randint(-3, 2)),
        'vy': -0.95,
        'life': DAMAGE_FLOAT_LIFE,
        'maxl': DAMAGE_FLOAT_LIFE,
        'txt': str(dmg),
        'col': _damage_color_for_fighter(source),
    })

def emit(x, y, col, n=8, speed=2.0, sz=1, vy_bias=-0.4):
    for _ in range(n):
        a = random.uniform(0, math.tau)
        s = random.uniform(0.3, speed)
        PARTS.append(Particle(x, y,
            math.cos(a)*s, math.sin(a)*s + vy_bias,
            col, random.randint(8, 22), sz))

def emit_aura(f, n=3):
    for _ in range(n):
        x = f['cx'] + random.randint(-7, 7)
        y = f['y']  + random.randint(2, 14)
        PARTS.append(Particle(x, y,
            random.uniform(-0.5, 0.5),
            random.uniform(-2.4, -0.5),
            f['aura_col'],
            random.randint(10, 28)))

def emit_spark(x, y, col, n=8):
    """Hitting spark — star burst."""
    for i in range(n):
        a = i / n * math.tau
        s = random.uniform(1.0, 3.5)
        PARTS.append(Particle(x, y,
            math.cos(a)*s, math.sin(a)*s,
            col, random.randint(5, 14), 1))

# ════════════════════════════════════════════════════════
#  FIGHTER
# ════════════════════════════════════════════════════════
def new_fighter(name, x, spr, facing, aura_col):
    down_spr = PIM_DOWN_SPR if name == "Pim" else TONNY_DOWN_SPR
    f = {
        'name':     name,
        'x':        float(x),
        'y':        float(GY - spr['h']),
        'spr':      spr,
        'spr_down': down_spr,
        'facing':   facing,     # 1=right, -1=left
        'hp':       MAX_HP,
        'en':       60.0,
        'state':    'idle',     # idle|walk|flight|chase|punch|kick|charge|beam|block|hurt|down|stand|ko|victory
        'st':       0,          # frames in state
        'base_aura_col': aura_col,
        'aura_col': aura_col,
        'aura':     False,
        'aura_lvl': 0.0,
        'mode':     'none',     # none|burst|shield|rage
        'mode_t':   0,
        'mode_cd':  0,
        'beam_end': None,
        'beam_target': None,
        'beam_missed': False,
        'pursuing': 0,
        'flight_hold': 0,
        'hover_y': float(GY - spr['h']),
        'offense_t': 0,
        'vx':       0.0,
        'vy':       0.0,
        'grounded': True,
        'invuln':   0,
        'power':    random.randint(9000, 12000),
        'combo':    0,
        'cx':       0,
        'cy':       0,
        'hit_flash': 0,
        'special_name': '',
        'special_t': 0,
    }
    _refresh_center(f)
    return f

def _refresh_center(f):
    spr = f['spr_down'] if f['state'] == 'down' else f['spr']
    if f['state'] == 'down':
        top_y = float(GY - spr['h'])
    else:
        top_y = f['y']
    f['cx'] = int(f['x'] + spr['w'] // 2)
    f['cy'] = int(top_y + spr['h'] // 2)

def tick_fighter(f):
    f['st'] += 1
    en_regen = 0.32
    if f['mode'] == 'burst':
        en_regen += 0.22
    elif f['mode'] == 'rage':
        en_regen += 0.12
    f['en'] = min(100.0, f['en'] + en_regen)
    if f['invuln'] > 0:
        f['invuln'] -= 1
    if f['hit_flash'] > 0:
        f['hit_flash'] -= 1
    if f['offense_t'] > 0:
        f['offense_t'] -= 1
    if f['special_t'] > 0:
        f['special_t'] -= 1
    if f['mode_cd'] > 0:
        f['mode_cd'] -= 1
    if f['mode_t'] > 0:
        f['mode_t'] -= 1
        if f['mode'] == 'burst':
            f['aura_lvl'] = max(f['aura_lvl'], 0.62)
        elif f['mode'] == 'shield':
            f['aura_lvl'] = max(f['aura_lvl'], 0.68)
        elif f['mode'] == 'rage':
            f['aura_lvl'] = max(f['aura_lvl'], 0.78)
        if f['mode_t'] == 0:
            f['mode'] = 'none'
            f['aura_col'] = f['base_aura_col']
            f['mode_cd'] = MODE_COOLDOWN
            emit(f['cx'], f['cy'] - 5, (200, 180, 255), n=10, speed=2.6)
            f['aura_lvl'] = max(0.25, f['aura_lvl'] * 0.45)
    if f['state'] != 'chase' and f['pursuing'] > 0:
        f['pursuing'] -= 1
    if f['state'] in ('hurt', 'down', 'stand', 'ko'):
        f['pursuing'] = 0
        f['offense_t'] = 0
    # Gravity / flight lift
    if not f['grounded']:
        grav = 0.58
        if f['state'] in ('flight', 'chase'):
            grav = 0.01
            f['en'] = max(0.0, f['en'] - FLIGHT_DRAIN)
            if f['state'] == 'flight':
                if f['flight_hold'] > 0:
                    f['flight_hold'] -= 1
                    grav = 0.00
                    f['vy'] *= 0.72
                    hover_delta = f['hover_y'] - f['y']
                    f['vy'] += max(-0.24, min(0.24, hover_delta * 0.075))
                else:
                    f['vy'] *= 0.95
        f['vy'] += grav
        f['y']  += f['vy']
        gnd = float(GY - f['spr']['h'])
        if f['y'] >= gnd and f['state'] not in ('flight', 'chase'):
            f['y'] = gnd; f['vy'] = 0; f['grounded'] = True
            # landing dust
            emit(f['cx'], GY - 1, (100, 80, 120), n=6, speed=1.4, vy_bias=0)
        elif f['state'] == 'flight':
            if f['flight_hold'] > 0:
                f['vy'] = max(-1.0, min(1.0, f['vy']))
                if f['st'] < 18 and f['vy'] > -0.4:
                    f['vy'] -= 0.06
            else:
                if f['st'] < 24 and f['vy'] > -0.6:
                    f['vy'] -= 0.08
            f['y'] = max(10.0, min(gnd - 44.0, f['y']))
            f['grounded'] = False
    f['x'] += f['vx']
    g_damp = 0.92 if f['mode'] == 'burst' else 0.88
    a_damp = 0.98 if f['mode'] == 'burst' else 0.97
    f['vx'] *= g_damp if f['grounded'] else a_damp
    f['x'] = max(4.0, min(float(LW - f['spr']['w'] - 4), f['x']))

    if f['state'] == 'flight' and f['en'] < FLIGHT_MIN_EN:
        f['state'] = 'idle'
        f['st'] = 0

    if f['state'] != 'beam' and f['beam_end'] is not None:
        f['beam_end'] = None
        f['beam_target'] = None
        f['beam_missed'] = False

    if f['mode'] == 'none' and f['mode_cd'] == 0 and f['hp'] < 58 and random.random() < SCARY_TRIGGER_CHANCE:
        mode = 'rage' if f['hp'] < 36 else ('shield' if random.random() < 0.48 else 'burst')
        _activate_mode(f, mode)
        BATTLE_MSG[0] = f"{f['name']}: SCARY ENERGY!"
        BATTLE_MSG[1] = 54
        FLASH[0] = max(FLASH[0], 10)
        SHAKE[0] = max(SHAKE[0], 6)
    # Aura decay when idle
    if not f['aura'] and f['mode'] == 'none':
        f['aura_lvl'] = max(0.0, f['aura_lvl'] - 0.04)
    _refresh_center(f)

# ════════════════════════════════════════════════════════
#  BATTLE AI
# ════════════════════════════════════════════════════════
FLASH = [0]
SHAKE = [0]
BATTLE_MSG = ['', 0]  # [text, frames_left]

SPECIAL_NAMES_PIM   = ["BALD BLAST!", "HEADPHONE BEAM!", "GOLDEN STRIKE!", "MEGA PUNCH!"]
SPECIAL_NAMES_TONNY = ["BLUE INFERNO!", "TONNY WAVE!", "CAP CANNON!", "AZURE BURST!"]
SPECIAL_NAME_BANK = {
    'beam': ["GALAXY RAY!", "ZERO BURST!", "CORE CANNON!"],
    'dash': ["FLASH DASH!", "SKY CUT!", "BLAZE RUSH!"],
    'uppercut': ["STAR UPPERCUT!", "NOVA LIFT!", "DRAGON RISE!"],
    'slam': ["THUNDER SLAM!", "METEOR DROP!", "GROUND BREAK!"],
    'rapid': ["RAPID FURY!", "STORM JAB!", "BLADE RAIN!"],
}

def _dist(a, b):
    return abs(a['cx'] - b['cx'])


def _can_connect(atk, dfn, reach, ypad=12):
    if dfn['state'] == 'down':
        reach += 8
        ypad += 20
    dx = dfn['cx'] - atk['cx']
    if abs(dx) > reach:
        return False
    if dx * atk['facing'] < -6:
        return False
    return abs(dfn['cy'] - atk['cy']) <= ypad


def _announce_move(f, kind):
    base = SPECIAL_NAMES_PIM if f['name'] == 'Pim' else SPECIAL_NAMES_TONNY
    pool = SPECIAL_NAME_BANK.get(kind, [])
    options = pool + base[:2]
    if not options:
        options = ["POWER MOVE!"]
    f['special_name'] = random.choice(options)
    BATTLE_MSG[0] = f"{f['name']}: {f['special_name']}"
    BATTLE_MSG[1] = 48


def _activate_mode(f, mode):
    f['mode'] = mode
    if mode == 'burst':
        f['mode_t'] = BURST_TIME
        f['aura_col'] = (255, 180, 70)
    elif mode == 'shield':
        f['mode_t'] = SHIELD_TIME
        f['aura_col'] = (80, 220, 255)
    else:
        f['mode_t'] = RAGE_TIME
        f['aura_col'] = (255, 90, 90)
    f['mode_cd'] = MODE_COOLDOWN
    f['aura'] = True
    f['aura_lvl'] = max(0.70, f['aura_lvl'])
    emit(f['cx'], f['cy'] - 8, f['aura_col'], n=18, speed=3.8, sz=2)

def ai_decide(me, opp):
    if me['state'] not in ('idle', 'walk', 'flight'): return
    if me['hp'] <= 0: return
    if me['state'] == 'flight' and me['en'] < FLIGHT_MIN_EN:
        me['state'] = 'idle'; me['st'] = 0
    if me['state'] == 'chase':
        return

    d = _dist(me, opp)
    hp_ratio = me['hp'] / MAX_HP

    options = []
    weights = []

    def add(action, weight):
        if weight > 0:
            options.append(action)
            weights.append(weight)

    add('rush', 7 if d > 88 else 4 if d > 48 else 2)
    add('jump', 2 if d > 60 else 1 if d > 28 else 0)
    add('punch', 2 if d > 58 else 5 if d > 28 else 6)
    add('kick', 1 if d > 70 else 5 if d > 34 else 8)
    add('block', 1 if d > 55 else 4 if d > 20 else 6)
    add('charge', 3 if me['en'] < 30 else 1)
    add('beam', 0 if me['en'] < 60 else (2 if d > 46 else 1))
    add('dash', 0 if me['en'] < 20 else (5 if d > 24 else 2))
    add('uppercut', 0 if me['en'] < 26 else (5 if d < 42 and me['grounded'] else 2 if d < 58 else 0))
    add('slam', 0 if me['en'] < 34 else (4 if d < 48 and me['grounded'] else 1))
    add('rapid', 0 if me['en'] < 30 else (4 if d < 56 else 1))
    add('powerup', 0 if me['mode'] != 'none' or me['mode_cd'] > 0 else (4 if me['en'] > 36 else 2))
    add('flight', 0 if me['en'] < 30 else (16 if d > 54 else 8))

    if hp_ratio < 0.35:
        if 'block' in options:
            weights[options.index('block')] += 2
        if 'kick' in options:
            weights[options.index('kick')] += 1
        if 'beam' in options:
            weights[options.index('beam')] += 1
        if 'powerup' in options:
            weights[options.index('powerup')] += 2

    if me['mode'] == 'burst':
        if 'dash' in options:
            weights[options.index('dash')] += 2
        if 'rapid' in options:
            weights[options.index('rapid')] += 2
    elif me['mode'] == 'rage':
        if 'uppercut' in options:
            weights[options.index('uppercut')] += 2
        if 'slam' in options:
            weights[options.index('slam')] += 2

    if me['offense_t'] > 0:
        if 'punch' in options:
            weights[options.index('punch')] += 3
        if 'kick' in options:
            weights[options.index('kick')] += 4
        if 'dash' in options:
            weights[options.index('dash')] += 2
        if 'rapid' in options:
            weights[options.index('rapid')] += 2
        if 'flight' in options:
            weights[options.index('flight')] = max(0, weights[options.index('flight')] - 4)
        if 'block' in options:
            weights[options.index('block')] = max(0, weights[options.index('block')] - 2)

    if opp['state'] == 'down':
        if 'kick' in options:
            weights[options.index('kick')] += 4
        if 'slam' in options:
            weights[options.index('slam')] += 4
        if 'rapid' in options:
            weights[options.index('rapid')] += 2
        if 'dash' in options:
            weights[options.index('dash')] += 2
        if 'beam' in options:
            weights[options.index('beam')] += 1
        if 'flight' in options:
            weights[options.index('flight')] = max(0, weights[options.index('flight')] - 6)

    elif opp['state'] in ('flight', 'chase'):
        if 'beam' in options:
            weights[options.index('beam')] += 4
        if 'uppercut' in options:
            weights[options.index('uppercut')] += 4
        if 'dash' in options:
            weights[options.index('dash')] += 2
        if 'jump' in options:
            weights[options.index('jump')] += 1

    elif opp['state'] == 'charge':
        if 'punch' in options:
            weights[options.index('punch')] += 4
        if 'dash' in options:
            weights[options.index('dash')] += 3
        if 'beam' in options:
            weights[options.index('beam')] += 2
        if 'kick' in options:
            weights[options.index('kick')] += 1

    elif opp['state'] == 'block':
        if 'rapid' in options:
            weights[options.index('rapid')] += 3
        if 'dash' in options:
            weights[options.index('dash')] += 2
        if 'kick' in options:
            weights[options.index('kick')] += 2

    if me['combo'] >= 2:
        if 'punch' in options:
            weights[options.index('punch')] += 2
        if 'kick' in options:
            weights[options.index('kick')] += 3
        if 'rapid' in options:
            weights[options.index('rapid')] += 2
        if 'dash' in options:
            weights[options.index('dash')] += 1

    choice = random.choices(options, weights=weights, k=1)[0]

    if choice == 'rush':
        me['state'] = 'walk'; me['st'] = 0
        s_mul = 1.35 if me['mode'] == 'burst' else 1.0
        me['vx'] += me['facing'] * random.uniform(MOVE_SPEED, RUSH_SPEED) * s_mul
        if random.random() < 0.35:
            me['grounded'] = False
            me['vy'] = random.uniform(-2.2, -0.7)

    elif choice == 'jump':
        me['state'] = 'jump'; me['st'] = 0
        me['grounded'] = False
        j_boost = 0.8 if me['mode'] == 'burst' else 0.0
        me['vy'] = random.uniform(JUMP_VY - j_boost, JUMP_VY + 1.0)
        me['vx'] += me['facing'] * random.uniform(1.6, 3.4 + j_boost)

    elif choice == 'punch':
        me['state'] = 'punch'; me['st'] = 0
        me['vx'] += me['facing'] * 1.1

    elif choice == 'kick':
        me['state'] = 'kick'; me['st'] = 0
        me['grounded'] = False
        me['vy'] = random.uniform(KICK_VY, KICK_VY + 1.1)
        me['vx'] += me['facing'] * random.uniform(2.0, 4.6)

    elif choice == 'block':
        me['state'] = 'block'; me['st'] = 0
        me['vx'] *= 0.35

    elif choice == 'charge':
        me['state'] = 'charge'; me['st'] = 0; me['aura'] = True

    elif choice == 'beam':
        me['state'] = 'beam'; me['st'] = 0; me['en'] -= 52
        _announce_move(me, 'beam')

    elif choice == 'dash':
        me['state'] = 'dash'; me['st'] = 0; me['en'] -= 20
        me['vx'] += me['facing'] * random.uniform(6.8, 9.2)
        _announce_move(me, 'dash')

    elif choice == 'uppercut':
        me['state'] = 'uppercut'; me['st'] = 0; me['en'] -= 26
        me['grounded'] = False
        me['vy'] = random.uniform(-7.8, -6.8)
        me['vx'] += me['facing'] * random.uniform(2.8, 4.2)
        _announce_move(me, 'uppercut')

    elif choice == 'slam':
        me['state'] = 'slam'; me['st'] = 0; me['en'] -= 34
        me['grounded'] = False
        me['vy'] = random.uniform(-6.8, -5.8)
        me['vx'] += me['facing'] * random.uniform(1.8, 3.0)
        _announce_move(me, 'slam')

    elif choice == 'rapid':
        me['state'] = 'rapid'; me['st'] = 0; me['en'] -= 30
        me['vx'] += me['facing'] * random.uniform(2.8, 4.8)
        _announce_move(me, 'rapid')

    elif choice == 'powerup':
        me['state'] = 'powerup'; me['st'] = 0
        me['vx'] *= 0.25

    elif choice == 'flight':
        me['state'] = 'flight'; me['st'] = 0
        me['grounded'] = False
        me['vy'] = random.uniform(-2.8, -1.6)
        me['vx'] += me['facing'] * random.uniform(1.4, 3.0)
        gnd = float(GY - me['spr']['h'])
        me['hover_y'] = max(12.0, min(gnd - 42.0, me['y'] - random.uniform(18.0, 30.0)))
        me['flight_hold'] = random.randint(FLIGHT_HOLD_MIN, FLIGHT_HOLD_MAX)


def _roll_block_outcome(atk, dfn, kind):
    if dfn['state'] in ('ko', 'down', 'stand', 'hurt'):
        return None

    if dfn['state'] == 'block':
        chance = 1.0
    else:
        chance = REACTIVE_BLOCK_CHANCE_BEAM if kind == 'beam' else REACTIVE_BLOCK_CHANCE
        if dfn['state'] in ('punch', 'kick', 'beam', 'charge', 'dash', 'uppercut', 'slam', 'rapid', 'powerup'):
            chance -= 0.10
        if not dfn['grounded']:
            chance -= 0.08
        if dfn['mode'] == 'shield':
            chance += 0.16
        elif dfn['mode'] == 'burst':
            chance -= 0.06
        chance = max(0.08, min(0.90, chance))
        if random.random() >= chance:
            return None
        dfn['state'] = 'block'
        dfn['st'] = 0

    roll = random.random()
    if not dfn['grounded'] and roll < 0.18:
        return 'air_counter'
    if roll < 0.45:
        return 'full'
    if roll < 0.82:
        return 'chip'
    return 'counter'


def _apply_block_result(atk, dfn, dmg, kb, kind):
    outcome = _roll_block_outcome(atk, dfn, kind)
    if outcome is None:
        return False

    dir_ = 1 if dfn['x'] > atk['x'] else -1

    if outcome == 'air_counter':
        reflected = max(3, dmg // (2 if kind == 'beam' else 2))
        atk['hp'] = max(0, atk['hp'] - reflected)
        atk['state'] = 'hurt' if atk['hp'] > 0 else 'ko'
        atk['st'] = 0
        atk['vx'] = -kb * 0.62 * dir_
        atk['vy'] = -4.1
        atk['grounded'] = False
        atk['invuln'] = max(atk['invuln'], 7)

        dfn['state'] = 'flight' if dfn['en'] > FLIGHT_MIN_EN else dfn['state']
        dfn['vx'] = kb * 0.16 * dir_
        dfn['vy'] = -2.8
        dfn['grounded'] = False
        dfn['invuln'] = max(dfn['invuln'], 6)
        if kind == 'beam':
            atk['beam_end'] = None
            atk['beam_target'] = None
            atk['beam_missed'] = False
        emit_spark(dfn['cx'], dfn['cy'] - 10, (150, 230, 255), n=12)
        emit_spark(atk['cx'], atk['cy'] - 8, (255, 160, 80), n=10)
        SHAKE[0] = max(SHAKE[0], 10)
        return True

    if outcome == 'full':
        dfn['vx'] = kb * 0.10 * dir_
        dfn['invuln'] = max(dfn['invuln'], 4)
        atk['combo'] = 0
        emit(dfn['cx'], dfn['cy'] - 2, (180, 220, 255), n=8, speed=1.8)
        return True

    if outcome == 'chip':
        chip = max(1, dmg // 6)
        dfn['hp'] = max(0, dfn['hp'] - chip)
        dfn['vx'] = kb * 0.18 * dir_
        dfn['invuln'] = max(dfn['invuln'], 4)
        atk['combo'] = 0
        emit(dfn['cx'], dfn['cy'] - 2, (160, 205, 255), n=7, speed=1.6)
        return True

    # Counter / reflect
    reflected = max(2, dmg // (3 if kind == 'beam' else 2))
    atk['hp'] = max(0, atk['hp'] - reflected)
    atk['state'] = 'hurt' if atk['hp'] > 0 else 'ko'
    atk['st'] = 0
    atk['vx'] = -kb * 0.55 * dir_
    atk['vy'] = -3.0
    atk['grounded'] = False
    atk['invuln'] = max(atk['invuln'], 6)

    dfn['vx'] = kb * 0.12 * dir_
    dfn['invuln'] = max(dfn['invuln'], 5)
    atk['combo'] = 0
    if kind == 'beam':
        atk['beam_end'] = None
        atk['beam_target'] = None
        atk['beam_missed'] = False

    emit_spark(dfn['cx'], dfn['cy'] - 6, (170, 220, 255), n=10)
    emit_spark(atk['cx'], atk['cy'] - 8, (255, 180, 90), n=9)
    SHAKE[0] = max(SHAKE[0], 9)
    return True


def _hit(atk, dfn, dmg, kb, kind='punch'):
    if dfn['invuln'] > 0: return

    if atk['mode'] == 'rage':
        dmg += 4
        kb *= 1.18
    elif atk['mode'] == 'burst':
        dmg += 2
        kb *= 1.08

    if dfn['mode'] == 'shield':
        dmg = max(1, int(dmg * 0.66))
        kb *= 0.72

    if _apply_block_result(atk, dfn, dmg, kb, kind):
        return

    atk['combo'] += 1
    if kind in ('punch', 'kick', 'dash', 'rapid', 'telekick'):
        dmg += min(4, atk['combo'] // 2)
    atk['offense_t'] = max(atk['offense_t'], OFFENSE_CHAIN_FRAMES)
    dfn['hp'] = max(0, dfn['hp'] - dmg)
    dfn['hit_flash'] = HIT_FLASH_FRAMES
    spawn_damage_float(dfn, dmg, atk)
    dfn['state'] = 'down' if kind in ('kick', 'beam', 'uppercut', 'slam') or dmg >= 13 else 'hurt'
    dfn['st'] = 0
    dir_ = 1 if dfn['x'] > atk['x'] else -1
    dfn['vx'] = kb * dir_
    if kind == 'beam':
        dfn['vy'] = -7.0
        dfn['invuln'] = 8
    elif kind in ('kick', 'uppercut'):
        dfn['vy'] = -8.2
        dfn['invuln'] = 7
    elif kind == 'slam':
        dfn['vy'] = -6.4
        dfn['invuln'] = 7
    else:
        dfn['vy'] = -3.2 if not dfn['grounded'] else -1.6
        dfn['invuln'] = 6
    dfn['grounded'] = False
    emit(dfn['cx'], dfn['cy'] - 4, (255, 70, 50), n=12, speed=3.2, sz=1)
    emit_spark(dfn['cx'], dfn['cy'] - 8, (255, 200, 60), n=10)
    SHAKE[0] = max(SHAKE[0], 7)

    if dfn['state'] == 'down' and dfn['grounded']:
        dfn['vx'] *= 0.55

    if dfn['state'] == 'down':
        dfn['invuln'] = min(dfn['invuln'], 3)

    if atk['en'] > 8 and atk['hp'] > 0:
        pursue_chance = 0.0
        if dfn['state'] == 'down':
            pursue_chance = 0.96
        elif kind in ('kick', 'uppercut', 'slam'):
            pursue_chance = 0.62
        elif kind in ('dash', 'rapid', 'telekick', 'punch'):
            pursue_chance = 0.28
        if random.random() < pursue_chance:
            atk['pursuing'] = min(5, max(atk['pursuing'] + 1, 2))
            atk['state'] = 'chase'
            atk['st'] = 0
            atk['grounded'] = False
            atk['en'] = max(0.0, atk['en'] - 7.0)


def advance(me, opp):
    s, t = me['state'], me['st']

    if s == 'punch':
        if t == 4 and _can_connect(me, opp, 28, 10):
            _hit(me, opp, random.randint(6, 14), 4.3, 'punch')
            me['power'] += 130
        if t > 11: me['state'] = 'idle'; me['st'] = 0

    elif s == 'kick':
        if t == 6 and _can_connect(me, opp, 38, 12):
            _hit(me, opp, random.randint(10, 22), 7.0, 'kick')
            emit_spark(me['cx'] + 14*me['facing'], me['cy'], (255, 150, 20), n=12)
            me['power'] += 280
        if t > 16 or (me['grounded'] and t > 8):
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'jump':
        if t > 13 and me['grounded']:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'flight':
        me['grounded'] = False
        tx = opp['cx'] + opp['vx'] * 5
        ty = me['hover_y'] if me['flight_hold'] > 0 else (opp['cy'] - random.randint(4, 36))
        dx = max(-1.0, min(1.0, (tx - me['cx']) / 20.0))
        dy = max(-1.0, min(1.0, (ty - me['cy']) / 18.0))
        me['vx'] += dx * (0.88 if me['mode'] == 'burst' else 0.62)
        me['vy'] += dy * (0.20 if me['flight_hold'] > 0 else 0.48)
        me['vy'] = max(-5.2, min(4.1, me['vy']))
        if t % 2 == 0:
            emit_aura(me, n=4)
        if me['flight_hold'] == 0 and t > 34 and _can_connect(me, opp, 36, 16) and me['en'] > 16 and random.random() < 0.42:
            me['state'] = 'kick'; me['st'] = 0
            me['vy'] = random.uniform(-7.4, -6.0)
            me['vx'] += me['facing'] * random.uniform(3.0, 5.2)
        elif t > 68 or me['en'] < FLIGHT_MIN_EN:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'chase':
        me['grounded'] = False
        if t == 1:
            lead_x = int(opp['x'] + opp['vx'] * 2)
            lead_y = int(opp['y'] + opp['vy'] * 3)
            tx = lead_x - opp['facing'] * random.randint(12, 18)
            ty = max(8, min(GY - me['spr']['h'] - 4, lead_y - random.randint(4, 10)))
            me['x'] = float(max(4, min(LW - me['spr']['w'] - 4, tx)))
            me['y'] = float(ty)
            me['vx'] = me['facing'] * random.uniform(3.8, 5.4)
            me['vy'] = random.uniform(-1.2, 0.8)
            emit(me['cx'], me['cy'] - 6, (180, 220, 255), n=14, speed=3.6, sz=2)
            SHAKE[0] = max(SHAKE[0], 5)
        if t == 3 and _can_connect(me, opp, 34, 14):
            _hit(me, opp, random.randint(10, 21), 7.8, 'telekick')
            me['power'] += 340
        if t > 8:
            me['pursuing'] = max(0, me['pursuing'] - 1)
            chain_chance = 0.90 if opp['state'] == 'down' else 0.55
            if me['pursuing'] > 0 and opp['hp'] > 0 and _dist(me, opp) < 130 and random.random() < chain_chance and me['en'] > 9:
                me['state'] = 'chase'; me['st'] = 0
                me['en'] = max(0.0, me['en'] - 6.0)
            else:
                me['pursuing'] = 0
                me['state'] = 'flight' if me['en'] > FLIGHT_MIN_EN and random.random() < 0.45 else 'idle'
                me['st'] = 0

    elif s == 'charge':
        me['en'] = min(100.0, me['en'] + 2.5)
        me['aura_lvl'] = min(1.0, me['aura_lvl'] + 0.07)
        me['power'] += random.randint(0, 400)
        emit_aura(me, n=5)
        # Shockwave ripple particles
        if t % 8 == 0:
            for ang in range(0, 360, 30):
                a = math.radians(ang)
                PARTS.append(Particle(
                    me['cx'], GY - 2,
                    math.cos(a) * 2.5, -0.5,
                    me['aura_col'], 14, 1))
        if t > 48 or me['en'] >= 98:
            me['state'] = 'idle'; me['aura'] = False
            FLASH[0] = max(FLASH[0], 6)
            emit(me['cx'], me['cy'], me['aura_col'], n=18, speed=4, sz=2)

    elif s == 'beam':
        me['aura_lvl'] = 1.0
        emit_aura(me, n=7)
        if t == 1:
            pred_x = int(opp['cx'] + opp['vx'] * 12)
            pred_y = int(opp['cy'] + opp['vy'] * 4)
            me['beam_target'] = (max(0, min(LW - 1, pred_x)), max(0, min(LH - 1, pred_y)))
            miss_bias = 0.22 + min(0.40, abs(opp['vx']) * 0.035 + (0.18 if opp['state'] in ('flight', 'dash', 'chase') else 0.0))
            me['beam_missed'] = random.random() < miss_bias
            me['beam_end'] = me['beam_target']
        if t == 24:
            FLASH[0] = 12; SHAKE[0] = max(SHAKE[0], 15)
            tx, ty = me['beam_target'] if me['beam_target'] is not None else (opp['cx'], opp['cy'] - 4)
            target_close = abs(opp['cx'] - tx) + abs(opp['cy'] - ty) < 28
            if not me['beam_missed'] and target_close:
                _hit(me, opp, random.randint(22, 38), 10.0, 'beam')
                emit(opp['cx'], opp['cy'], me['aura_col'], n=25, speed=5.5, sz=2)
            else:
                emit(tx, ty, me['aura_col'], n=22, speed=4.6, sz=2)
                emit_spark(tx, ty, (255, 255, 255), n=12)
            me['power'] += 2000
        if t > 30:
            me['beam_end'] = None; me['beam_target'] = None; me['beam_missed'] = False; me['aura'] = False
            me['aura_lvl'] = 0.55; me['state'] = 'idle'; me['st'] = 0

    elif s == 'dash':
        me['vx'] += me['facing'] * (1.2 if t < 6 else 0.2)
        if t == 4 and _can_connect(me, opp, 36, 12):
            _hit(me, opp, random.randint(11, 20), 8.0, 'dash')
            me['power'] += 360
            SHAKE[0] = max(SHAKE[0], 8)
        if t > 11:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'uppercut':
        if t == 5 and _can_connect(me, opp, 34, 14):
            _hit(me, opp, random.randint(13, 25), 8.8, 'uppercut')
            me['power'] += 430
            emit_spark(me['cx'] + 8 * me['facing'], me['cy'] - 12, (255, 210, 90), n=13)
        if t > 16 and me['grounded']:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'slam':
        if t < 7:
            me['vy'] += 0.16
        if t == 8 and _can_connect(me, opp, 40, 16):
            _hit(me, opp, random.randint(15, 28), 9.2, 'slam')
            me['power'] += 520
            emit(me['cx'], GY - 1, (220, 170, 90), n=18, speed=3.6)
            SHAKE[0] = max(SHAKE[0], 12)
        if t > 18 and me['grounded']:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'rapid':
        me['vx'] += me['facing'] * 0.5
        if t in (4, 6, 8) and _can_connect(me, opp, 42, 12):
            _hit(me, opp, random.randint(6, 12), 4.1, 'rapid')
            me['power'] += 180
        if t > 13:
            me['state'] = 'idle'; me['st'] = 0

    elif s == 'powerup':
        me['aura_lvl'] = min(1.0, me['aura_lvl'] + 0.09)
        if t == 1:
            if me['hp'] < 36 and me['en'] > 24:
                mode = 'rage'
            elif random.random() < 0.50:
                mode = 'burst'
            else:
                mode = 'shield'
            _activate_mode(me, mode)
            BATTLE_MSG[0] = f"{me['name']}: {mode.upper()} MODE!"
            BATTLE_MSG[1] = 42
        if t % 3 == 0:
            emit_aura(me, n=5)
        if t > 12:
            me['state'] = 'idle'; me['st'] = 0; me['aura'] = False

    elif s == 'block':
        if t > 16: me['state'] = 'idle'; me['st'] = 0

    elif s == 'hurt':
        if t > 10:
            me['state'] = 'down' if me['hp'] > 0 else 'ko'
            me['st'] = 0

    elif s == 'down':
        me['vx'] *= 0.72
        if me['grounded'] and t > DOWN_STUN:
            me['state'] = 'stand'; me['st'] = 0

    elif s == 'stand':
        me['vx'] *= 0.5
        if t > STAND_STUN:
            me['state'] = 'idle' if me['hp'] > 0 else 'ko'
            me['st'] = 0

    elif s == 'victory':
        me['aura_lvl'] = min(1.0, me['aura_lvl'] + 0.02)
        emit_aura(me, n=3)

# ════════════════════════════════════════════════════════
#  RENDERING
# ════════════════════════════════════════════════════════
def draw_bg(draw, frame):
    # Gradient sky — manual bands
    for i in range(9):
        y0 = i * (GY // 9)
        y1 = (i+1) * (GY // 9)
        t  = i / 8.0
        r = int(5  + (18 - 5)  * t)
        g = int(2  + (7  - 2)  * t)
        b = int(18 + (44 - 18) * t)
        draw.rectangle([0, y0, LW, y1], fill=(r, g, b))

    # Twinkling stars
    for (sx, sy, br) in STARS:
        on = ((frame // 5 + sx * 7) % 12) < 7
        bv = br if on else br // 4
        draw.point((sx, sy), fill=(bv, bv, int(bv * 0.88)))

    # Distant pixel-art mountains
    for mx in range(0, LW, 20):
        mh = 10 + (mx * 11 + 3) % 22
        mc = (24, 16, 38)
        draw.polygon([
            (mx, GY - mh),
            (mx + 10, GY - mh - 8),
            (mx + 20, GY - mh)
        ], fill=mc)

    # Ground
    draw.rectangle([0, GY, LW, LH], fill=(36, 24, 52))
    draw.line([0, GY, LW, GY], fill=(72, 50, 92))
    # Ground detail cracks
    for crx in (45, 105, 165, 225, 280):
        draw.line([crx, GY, crx - 10, GY + 8], fill=(52, 36, 68))
        draw.line([crx, GY, crx +  8, GY + 7], fill=(52, 36, 68))


def draw_aura(draw, f, frame):
    lvl = f['aura_lvl']
    if lvl < 0.04: return
    r, g, b = f['aura_col']
    if f['mode'] == 'shield':
        r, g, b = (80, 220, 255)
    elif f['mode'] == 'burst':
        r, g, b = (255, 180, 70)
    elif f['mode'] == 'rage':
        r, g, b = (255, 90, 90)
    if f['mode_t'] > 0 and f['mode_t'] > (RAGE_TIME // 2):
        lvl = min(1.0, lvl + 0.18)
    fcx = f['cx']
    body_h = f['spr_down']['h'] if f['state'] == 'down' else f['spr']['h']
    base_y = (GY - f['spr_down']['h']) if f['state'] == 'down' else f['y']
    fcy = int(base_y + body_h * 0.48)
    pulse = 0.5 + 0.5 * math.sin(frame * (0.62 if f['mode_t'] > 0 else 0.48))

    for ring in range(5):
        rad = int((5 + ring * 7) * lvl + pulse * 3)
        alpha = lvl * (1.0 - ring * 0.18)
        col = (int(r * alpha), int(g * alpha), int(b * alpha))
        step = max(8, int(20 / (lvl + 0.1)))
        for deg in range(0, 360, step):
            a = math.radians(deg)
            px = fcx + int(math.cos(a) * rad)
            py = fcy + int(math.sin(a) * rad * 0.52)
            if 0 <= px < LW and 0 <= py < LH:
                draw.point((px, py), fill=col)


def draw_beam(draw, f, frame):
    if f['beam_end'] is None: return
    r, g, b = f['aura_col']
    x1 = f['cx'] + 9 * f['facing']
    y1 = int(f['y'] + f['spr']['h'] * 0.28)
    x2, y2 = f['beam_end']

    # Multi-layer beam (fat centre → thin outer glow)
    for layer in range(6, -1, -1):
        brightness = 1.0 - layer * 0.14
        col = (
            int(r * brightness + (1 - brightness) * 255),
            int(g * brightness + (1 - brightness) * 255),
            int(b * brightness + (1 - brightness) * 255),
        )
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for i in range(0, steps, 2):
            tt = i / steps
            bx = int(x1 + (x2 - x1) * tt)
            by = int(y1 + (y2 - y1) * tt) + random.randint(-layer, layer)
            if 0 <= bx < LW and 0 <= by < LH:
                draw.point((bx, by), fill=col)

    # Impact bloom
    for _ in range(4):
        ox = x2 + random.randint(-5, 5)
        oy = y2 + random.randint(-5, 5)
        if 0 <= ox < LW and 0 <= oy < LH:
            draw.point((ox, oy), fill=(255, 255, 255))


def draw_hud(draw, pim, ton, frame):
    bar_w = 98

    for i, f in enumerate([pim, ton]):
        bx = 5 if i == 0 else LW - 5 - bar_w
        by = 6

        # HP bar
        draw.rectangle([bx, by, bx + bar_w, by + 5], fill=(32, 14, 24))
        hp = max(0.0, f['hp'] / MAX_HP)
        hcol = (45, 200, 45) if hp > 0.6 else ((225, 175, 10) if hp > 0.3 else (215, 30, 30))
        if hp > 0:
            draw.rectangle([bx, by, bx + int(bar_w * hp), by + 5], fill=hcol)
        draw.rectangle([bx, by, bx + bar_w, by + 5], outline=(185, 162, 210))

        # Energy bar
        ey = by + 7
        draw.rectangle([bx, ey, bx + bar_w, ey + 3], fill=(14, 6, 32))
        if f['en'] > 0:
            draw.rectangle([bx, ey, bx + int(bar_w * f['en'] / 100), ey + 3], fill=(60, 140, 255))

        # Name
        draw.text((bx, by - 9), f['name'], fill=(240, 235, 255))

        # Power level (with comma formatting)
        pl_col = (255, 215, 70)
        # Pulse if charging
        if f['state'] == 'charge':
            pulse = abs(math.sin(frame * 0.25))
            pl_col = (
                int(255 * pulse + 180 * (1 - pulse)),
                int(215 * pulse + 100 * (1 - pulse)),
                int(70  * pulse),
            )
        draw.text((bx, ey + 5), f"PL:{f['power']:,}", fill=pl_col)

        if f['mode'] != 'none':
            mcol = (255, 170, 70) if f['mode'] == 'burst' else ((85, 220, 255) if f['mode'] == 'shield' else (255, 90, 95))
            draw.text((bx, ey + 23), f"{f['mode'].upper()} {f['mode_t']//24 + 1}s", fill=mcol)

        # Combo counter
        if f['combo'] >= 2:
            draw.text((bx, ey + 14), f"{f['combo']}x COMBO!", fill=(255, 120, 20))


def draw_special_msg(draw, frame):
    if BATTLE_MSG[1] <= 0: return
    alpha = min(1.0, BATTLE_MSG[1] / 30.0)
    col = (int(255 * alpha), int(220 * alpha), int(60 * alpha))
    txt = BATTLE_MSG[0]
    tx = LW // 2 - len(txt) * 3
    draw.text((tx, LH // 2 - 30), txt, fill=col)
    BATTLE_MSG[1] -= 1


def draw_ko_screen(draw, winner):
    cx_ = LW // 2
    cy_ = LH // 2 - 18
    # Shadow box
    draw.rectangle([cx_ - 46, cy_ - 8, cx_ + 46, cy_ + 10], fill=(16, 4, 10))
    draw.rectangle([cx_ - 46, cy_ - 8, cx_ + 46, cy_ + 10], outline=(220, 35, 35))
    draw.text((cx_ - 42, cy_ - 6), "  K . O . !", fill=(255, 55, 55))
    wname = winner['name'].upper()
    draw.text((cx_ - 44, cy_ + 11), f"{wname} WINS!", fill=(255, 210, 45))


def draw_intro_banner(draw, frame):
    """VS screen for first 55 frames."""
    if frame > 55: return
    alpha = min(1.0, (55 - frame) / 20.0)
    col   = (int(255 * alpha), int(210 * alpha), int(50 * alpha))
    draw.text((LW // 2 - 34, LH // 2 - 6), "FIGHT!", fill=col)
    draw.text((8,  LH // 2 + 6), "Pim",   fill=(int(255 * alpha), int(200 * alpha), int(40 * alpha)))
    draw.text((LW - 26, LH // 2 + 6), "Tonny", fill=(int(40 * alpha), int(150 * alpha), int(255 * alpha)))


# ════════════════════════════════════════════════════════
#  MAIN APP
# ════════════════════════════════════════════════════════
class Battle:
    def __init__(self, root):
        self.root  = root
        self.frame = 0
        self.phase = 'intro'   # intro → fight → ko
        self.ko_t  = 0

        self.pim   = new_fighter("Pim",   18,  PIM_SPR,   1,  PIM_AURA_COL)
        self.ton   = new_fighter("Tonny", 270, TONNY_SPR, -1, TONNY_AURA_COL)

        self.canvas  = tk.Canvas(root, width=SW, height=SH,
                                 bg='#050212', highlightthickness=0)
        self.canvas.pack()
        self.img_ref = None

        root.title("PIM vs TONNY — DBZ Pixel Art Battle")
        root.resizable(False, False)
        self._loop()

    # ── render one frame ──────────────────────────────────
    def _render(self):
        f   = self.frame
        pim = self.pim
        ton = self.ton

        # Camera shake
        sx = sy = 0
        if SHAKE[0] > 0:
            sx = random.randint(-2, 2)
            sy = random.randint(-1, 1)
            SHAKE[0] -= 1

        img  = Image.new('RGB', (LW, LH))
        draw = ImageDraw.Draw(img)

        draw_bg(draw, f)
        draw_aura(draw, pim, f)
        draw_aura(draw, ton, f)
        draw_beam(draw, pim, f)
        draw_beam(draw, ton, f)

        # Advance + draw particles
        PARTS[:] = [p for p in PARTS if p.step()]
        for p in PARTS:
            p.draw(draw)

        # Floating damage numbers
        next_floats = []
        for dmgf in DAMAGE_FLOATS:
            dmgf['x'] += random.uniform(-0.12, 0.12)
            dmgf['y'] += dmgf['vy']
            dmgf['vy'] *= 0.93
            dmgf['life'] -= 1
            if dmgf['life'] <= 0:
                continue
            alpha = dmgf['life'] / dmgf['maxl']
            col = tuple(int(c * alpha) for c in dmgf['col'])
            x = int(dmgf['x'])
            y = int(dmgf['y'])
            draw.text((x + 1, y + 1), dmgf['txt'], fill=(10, 8, 16))
            draw.text((x, y), dmgf['txt'], fill=col)
            next_floats.append(dmgf)
        DAMAGE_FLOATS[:] = next_floats

        # Sprites — animation offsets
        bob_p   = int(math.sin(f * 0.18) * 1.0)       if pim['state'] == 'idle' else 0
        bob_t   = int(math.sin(f * 0.18 + 1.3) * 1.0) if ton['state'] == 'idle' else 0
        walk_p  = int(math.sin(f * 0.55) * 2.0)       if pim['state'] == 'walk' else 0
        walk_t  = int(math.sin(f * 0.55) * 2.0)       if ton['state'] == 'walk' else 0
        flight_p = int(math.sin(f * 0.80) * 3.0) if pim['state'] in ('flight', 'chase') else 0
        flight_t = int(math.sin(f * 0.80 + 1.1) * 3.0) if ton['state'] in ('flight', 'chase') else 0
        hurt_p  = random.randint(-1, 1)               if pim['state'] == 'hurt' else 0
        hurt_t  = random.randint(-1, 1)               if ton['state'] == 'hurt' else 0
        block_p = -2 if pim['state'] == 'block' else 0
        block_t = -2 if ton['state'] == 'block' else 0
        stand_p = -2 if pim['state'] == 'stand' else 0
        stand_t = -2 if ton['state'] == 'stand' else 0
        punch_p = 4 if (pim['state'] == 'punch' and 5 <= pim['st'] <= 11) else 0
        punch_t = 4 if (ton['state'] == 'punch' and 5 <= ton['st'] <= 11) else 0
        charge_shake_p = random.randint(-1, 1) if pim['state'] == 'charge' else 0
        charge_shake_t = random.randint(-1, 1) if ton['state'] == 'charge' else 0

        dash_p = 6 if pim['state'] == 'dash' and 3 <= pim['st'] <= 7 else 0
        dash_t = 6 if ton['state'] == 'dash' and 3 <= ton['st'] <= 7 else 0
        up_p = -5 if pim['state'] == 'uppercut' and 3 <= pim['st'] <= 8 else 0
        up_t = -5 if ton['state'] == 'uppercut' and 3 <= ton['st'] <= 8 else 0
        rapid_jit_p = random.randint(-1, 1) if pim['state'] == 'rapid' else 0
        rapid_jit_t = random.randint(-1, 1) if ton['state'] == 'rapid' else 0
        chase_jit_p = random.randint(-2, 2) if pim['state'] == 'chase' else 0
        chase_jit_t = random.randint(-2, 2) if ton['state'] == 'chase' else 0
        power_p = int(math.sin(f * 0.45) * 2.0) if pim['state'] == 'powerup' else 0
        power_t = int(math.sin(f * 0.45 + 1.2) * 2.0) if ton['state'] == 'powerup' else 0

        pim_spr = pim['spr_down'] if pim['state'] == 'down' else pim['spr']
        ton_spr = ton['spr_down'] if ton['state'] == 'down' else ton['spr']

        pim_x = int(pim['x']) + (pim['spr']['w'] - pim_spr['w']) // 2
        ton_x = int(ton['x']) + (ton['spr']['w'] - ton_spr['w']) // 2
        pim_y = (GY - pim_spr['h']) if pim['state'] == 'down' else int(pim['y'])
        ton_y = (GY - ton_spr['h']) if ton['state'] == 'down' else int(ton['y'])

        blit(
            draw,
            pim_spr,
            pim_x + sx + (punch_p + dash_p) * pim['facing'] + charge_shake_p + rapid_jit_p + chase_jit_p - block_p * pim['facing'],
            pim_y + bob_p + walk_p + flight_p + hurt_p + stand_p + up_p + power_p + block_p + sy,
            flip=(pim['facing'] > 0),
            gray=(pim['hit_flash'] > 0),
        )

        blit(
            draw,
            ton_spr,
            ton_x + sx - (punch_t + dash_t) * ton['facing'] + charge_shake_t + rapid_jit_t + chase_jit_t - block_t * ton['facing'],
            ton_y + bob_t + walk_t + flight_t + hurt_t + stand_t + up_t + power_t + block_t + sy,
            flip=(ton['facing'] > 0),
            gray=(ton['hit_flash'] > 0),
        )

        draw_hud(draw, pim, ton, f)
        draw_special_msg(draw, f)

        if self.phase == 'ko':
            winner = pim if ton['hp'] <= 0 else ton
            draw_ko_screen(draw, winner)

        if self.phase == 'intro':
            draw_intro_banner(draw, f)

        # Screen flash overlay
        if FLASH[0] > 0:
            t = min(0.80, FLASH[0] / 14.0)
            overlay = Image.new('RGB', (LW, LH), (255, 255, 255))
            img = Image.blend(img, overlay, t)
            FLASH[0] -= 1

        # Scale up with nearest-neighbour (keeps pixel art crisp)
        img = img.resize((SW, SH), Image.NEAREST)
        return ImageTk.PhotoImage(img)

    # ── logic + render tick ───────────────────────────────
    def _loop(self):
        pim, ton = self.pim, self.ton

        if self.phase == 'intro':
            if self.frame >= 55:
                self.phase = 'fight'

        elif self.phase == 'fight':
            tick_fighter(pim)
            tick_fighter(ton)

            # Always face each other
            if pim['cx'] < ton['cx']:
                pim['facing'], ton['facing'] = 1, -1
            else:
                pim['facing'], ton['facing'] = -1, 1

            # Staggered AI decisions
            if self.frame % 4 == 0: ai_decide(pim, ton)
            if self.frame % 4 == 2: ai_decide(ton, pim)

            advance(pim, ton)
            advance(ton, pim)

            if pim['hp'] <= 0 or ton['hp'] <= 0:
                self.phase = 'ko'
                w = pim if ton['hp'] <= 0 else ton
                l = ton if ton['hp'] <= 0 else pim
                w['state'] = 'victory'
                l['state'] = 'ko'
                FLASH[0] = 18

        elif self.phase == 'ko':
            self.ko_t += 1
            w = pim if ton['hp'] <= 0 else ton
            emit_aura(w, n=3)
            # Restart after ~7 s
            if self.ko_t > 168:
                PARTS.clear(); DAMAGE_FLOATS.clear(); FLASH[0] = 0; SHAKE[0] = 0
                BATTLE_MSG[0] = ''; BATTLE_MSG[1] = 0
                self.frame = 0; self.ko_t = 0; self.phase = 'intro'
                self.pim = new_fighter("Pim",   18,  PIM_SPR,   1,  PIM_AURA_COL)
                self.ton = new_fighter("Tonny", 270, TONNY_SPR, -1, TONNY_AURA_COL)

        self.frame += 1
        self.img_ref = self._render()
        self.canvas.create_image(0, 0, anchor='nw', image=self.img_ref)
        self.root.after(MS, self._loop)


if __name__ == '__main__':
    root = tk.Tk()
    Battle(root)
    root.mainloop()
