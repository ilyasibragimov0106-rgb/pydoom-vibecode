"""Procedural generation of every graphic in the game - no external assets.

* Wall / floor / ceiling textures are (64, 64, 3) uint8 numpy arrays.  Each one
  also gets a precomputed brightness LUT of shape (SHADE_LEVELS, 64, 64, 3) so
  the raycaster can fetch an already shaded pixel with a single fancy index.
* Sprites are (64, 64, 4) RGBA uint8 numpy arrays painted with tiny numpy
  helpers (ellipse / rect / line / pixel) - creatures, items, projectiles.
"""
import numpy as np

from settings import SHADE_LEVELS

TEX = 64
_RNG = np.random.default_rng(1993)

# --------------------------------------------------------------- helpers ----


def _u8(a):
    return np.clip(a, 0, 255).astype(np.uint8)


def _hash01(v):
    """Deterministic pseudo random in [0, 1) from an integer/float array."""
    h = np.sin(v.astype(np.float32) * 12.9898) * 43758.5453
    return h - np.floor(h)


def _shade_lut(rgb):
    lut = np.empty((SHADE_LEVELS,) + rgb.shape, np.uint8)
    for i in range(SHADE_LEVELS):
        lut[i] = _u8(rgb.astype(np.float32) * (i / (SHADE_LEVELS - 1)))
    return lut


# ----------------------------------------------------------- wall textures --
def _brick_tex():
    r, c = np.mgrid[0:TEX, 0:TEX].astype(np.float32)
    bh, bw = 16, 16
    row = (r // bh).astype(np.int32)
    off = (row & 1) * (bw // 2)
    mortar = (((c + off) % bw) < 2) | ((r % bh) < 2)
    brick_id = row * 31 + ((c + off) // bw).astype(np.int32)
    shade = 0.78 + 0.4 * _hash01(brick_id)
    base = np.array([128, 64, 48], np.float32)
    img = base[None, None, :] * shade[..., None]
    img = np.where(mortar[..., None], np.array([54, 46, 42], np.float32), img)
    bevel = (r % bh) == 2
    img = np.where(bevel[..., None], img * 0.72, img)
    img += _RNG.normal(0, 8, (TEX, TEX, 1))
    return _u8(img)


def _tech_tex():
    r, c = np.mgrid[0:TEX, 0:TEX].astype(np.float32)
    img = np.full((TEX, TEX, 3), 92.0, np.float32)
    seam = ((c % 16) < 2) | ((r % 16) < 2)
    img = np.where(seam[..., None], 58.0, img)
    rivet = ((c % 16 == 4) | (c % 16 == 12)) & ((r % 16 == 4) | (r % 16 == 12))
    img = np.where(rivet[..., None], 40.0, img)
    rivet_light = (c % 16 == 5) & ((r % 16 == 4) | (r % 16 == 12))
    img = np.where(rivet_light[..., None], 112.0, img)
    stripe = (r >= 28) & (r < 34)
    stripe_img = np.where((r == 29)[..., None],
                          np.array([110, 140, 190], np.float32),
                          np.array([46, 66, 100], np.float32))
    img = np.where(stripe[..., None], stripe_img, img)
    vent = (r >= 42) & (r < 50) & ((c % 4) < 2)
    img = np.where(vent[..., None], 66.0, img)
    img += _RNG.normal(0, 7, (TEX, TEX, 1))
    return _u8(img)


def _stone_tex():
    r, c = np.mgrid[0:TEX, 0:TEX].astype(np.float32)
    bs = 32
    row = (r // bs).astype(np.int32)
    off = (row & 1) * (bs // 2)
    mortar = (((c + off) % bs) < 3) | ((r % bs) < 3)
    block_id = row * 17 + ((c + off) // bs).astype(np.int32)
    shade = 0.8 + 0.3 * _hash01(block_id)
    base = np.array([108, 106, 100], np.float32)
    img = base[None, None, :] * shade[..., None]
    img = np.where(mortar[..., None], np.array([44, 44, 42], np.float32), img)
    crack = _hash01(block_id * 7 + (r + c).astype(np.int32)) < 0.045
    img = np.where(crack[..., None], img * 0.55, img)
    img += _RNG.normal(0, 9, (TEX, TEX, 1))
    return _u8(img)


def _switch_tex():
    """Tech wall with an exit switch panel (red button + green sign)."""
    img = _tech_tex().astype(np.float32)
    img[16:48, 20:44] = np.array([66, 66, 74], np.float32)
    img[16:48, 20:23] = 100          # left bevel (light)
    img[16:48, 41:44] = 34           # right bevel (dark)
    img[16:19, 20:44] = 105
    img[45:48, 20:44] = 36
    img[20:27, 25:39] = np.array([20, 120, 40], np.float32)   # EXIT sign
    for dx in (27, 31, 35):                                   # letter dots
        img[22:25, dx:dx + 2] = 235
    yy, xx = np.mgrid[0:TEX, 0:TEX]
    d2 = (yy - 35.0) ** 2 + (xx - 32.0) ** 2
    img[d2 <= 25] = np.array([190, 30, 26], np.float32)       # button
    img[d2 <= 9] = np.array([240, 90, 70], np.float32)
    img += _RNG.normal(0, 4, (TEX, TEX, 1))
    return _u8(img)


def _floor_tex():
    r, c = np.mgrid[0:TEX, 0:TEX].astype(np.float32)
    tile_id = (r // 32).astype(np.int32) * 7 + (c // 32).astype(np.int32)
    shade = 0.85 + 0.25 * _hash01(tile_id)
    base = np.array([78, 74, 68], np.float32)
    img = base[None, None, :] * shade[..., None]
    mortar = ((r % 32) < 2) | ((c % 32) < 2)
    img = np.where(mortar[..., None], np.array([40, 38, 36], np.float32), img)
    stain = _hash01(tile_id * 13 + (r * 3 + c).astype(np.int32)) < 0.05
    img = np.where(stain[..., None], img * 0.7, img)
    img += _RNG.normal(0, 7, (TEX, TEX, 1))
    return _u8(img)


def _ceil_tex():
    r, c = np.mgrid[0:TEX, 0:TEX].astype(np.float32)
    img = np.full((TEX, TEX, 3), 58.0, np.float32)
    seam = ((c % 16) < 2) | ((r % 16) < 2)
    img = np.where(seam[..., None], 44.0, img)
    vent = ((r >= 24) & (r < 30)) & ((c % 6) < 3)
    img = np.where(vent[..., None], 36.0, img)
    img += _RNG.normal(0, 5, (TEX, TEX, 1))
    return _u8(img)


# ------------------------------------------------------------ sprite paint --
def _canvas():
    return np.zeros((TEX, TEX, 4), np.uint8)


def _set(cv, mask, color):
    cv[mask, 0] = color[0]
    cv[mask, 1] = color[1]
    cv[mask, 2] = color[2]
    cv[mask, 3] = 255


def _ellipse(cv, cx, cy, rx, ry, color):
    yy, xx = np.mgrid[0:TEX, 0:TEX]
    m = (((xx - cx) / max(rx, 1e-3)) ** 2 + ((yy - cy) / max(ry, 1e-3)) ** 2) <= 1.0
    _set(cv, m, color)


def _rect(cv, x0, y0, x1, y1, color):
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(TEX - 1, int(x1)), min(TEX - 1, int(y1))
    if x1 < x0 or y1 < y0:
        return
    cv[y0:y1 + 1, x0:x1 + 1, 0] = color[0]
    cv[y0:y1 + 1, x0:x1 + 1, 1] = color[1]
    cv[y0:y1 + 1, x0:x1 + 1, 2] = color[2]
    cv[y0:y1 + 1, x0:x1 + 1, 3] = 255


def _px(cv, x, y, color):
    if 0 <= x < TEX and 0 <= y < TEX:
        cv[y, x, 0] = color[0]
        cv[y, x, 1] = color[1]
        cv[y, x, 2] = color[2]
        cv[y, x, 3] = 255


def _line(cv, x0, y0, x1, y1, color, w=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    if n == 0:
        _px(cv, int(round(x0)), int(round(y0)), color)
        return
    for i in range(n + 1):
        t = i / n
        x = int(round(x0 + (x1 - x0) * t))
        y = int(round(y0 + (y1 - y0) * t))
        _px(cv, x, y, color)
        if w >= 2:
            _px(cv, x + 1, y, color)
            _px(cv, x, y + 1, color)
            _px(cv, x + 1, y + 1, color)


def _pain_tint(cv):
    m = cv[:, :, 3] > 0
    cv[m, 0] = _u8(cv[m, 0].astype(np.float32) * 0.55 + 120)
    cv[m, 1] = _u8(cv[m, 1].astype(np.float32) * 0.5)
    cv[m, 2] = _u8(cv[m, 2].astype(np.float32) * 0.5)


# ------------------------------------------------------------------- imp ----
C_IMP = (150, 62, 40)
C_IMP_D = (104, 42, 28)
C_IMP_B = (186, 102, 64)
C_HORN = (226, 212, 186)
C_EYE = (255, 224, 64)
C_BLOOD = (150, 12, 10)
C_TEETH = (240, 238, 225)


def _paint_imp(swing=0, arms='down', glow=False, squash=0.0, lie=False,
               blood=False, pain=False):
    cv = _canvas()
    if lie:
        _ellipse(cv, 30, 58, 16, 6, C_IMP)
        _ellipse(cv, 24, 57, 7, 4, C_IMP_B)
        _ellipse(cv, 46, 56, 7, 5, C_IMP)
        _rect(cv, 47, 54, 49, 55, (30, 10, 8))          # closed eye
        _line(cv, 40, 52, 52, 51, C_HORN, 1)            # horn on the ground
        if blood:
            _ellipse(cv, 32, 62, 20, 3, C_BLOOD)
        return cv
    sq = squash
    bcy = 42 + 11 * sq
    brx = 11 + 2 * sq
    bry = max(3.0, 12 * (1 - 0.6 * sq))
    hcy = 26 + 15 * sq
    lry = max(2.0, 7 * (1 - 0.5 * sq))
    ih = int(round(hcy))
    ib = int(round(bcy))
    # legs (behind the body)
    _ellipse(cv, 27 + swing, 55 + 2 * sq, 3.2, lry, C_IMP_D)
    _ellipse(cv, 37 - swing, 55 + 2 * sq, 3.2, lry, C_IMP_D)
    if arms == 'down':
        _ellipse(cv, 19, bcy + 3 + swing, 3.2, 8 * (1 - 0.5 * sq), C_IMP_D)
        _ellipse(cv, 45, bcy + 3 - swing, 3.2, 8 * (1 - 0.5 * sq), C_IMP_D)
    # body
    _ellipse(cv, 32, bcy, brx, bry, C_IMP)
    _ellipse(cv, 32, bcy + bry * 0.25, brx * 0.55, bry * 0.62, C_IMP_B)
    # shoulder spikes
    _px(cv, 20, ib - int(bry) + 1, C_HORN)
    _px(cv, 21, ib - int(bry) + 2, C_HORN)
    _px(cv, 44, ib - int(bry) + 1, C_HORN)
    _px(cv, 43, ib - int(bry) + 2, C_HORN)
    # head
    _ellipse(cv, 32, hcy, 9, 8, C_IMP)
    _line(cv, 26, hcy - 6, 21, hcy - 14, C_HORN, 1)
    _line(cv, 38, hcy - 6, 43, hcy - 14, C_HORN, 1)
    if pain or sq > 0.4:
        _rect(cv, 27, ih - 2, 28, ih - 1, (40, 12, 8))
        _rect(cv, 35, ih - 2, 36, ih - 1, (40, 12, 8))
    else:
        _rect(cv, 27, ih - 3, 28, ih - 2, C_EYE)
        _rect(cv, 35, ih - 3, 36, ih - 2, C_EYE)
        _px(cv, 28, ih - 3, (200, 30, 20))
        _px(cv, 36, ih - 3, (200, 30, 20))
    _rect(cv, 28, ih + 3, 36, ih + 4, (44, 14, 10))
    _px(cv, 29, ih + 3, C_TEETH)
    _px(cv, 32, ih + 3, C_TEETH)
    _px(cv, 35, ih + 3, C_TEETH)
    if arms == 'raise':
        _ellipse(cv, 19, bcy - 7, 3.2, 8, C_IMP)
        _ellipse(cv, 45, bcy - 7, 3.2, 8, C_IMP)
        _px(cv, 18, ib - 15, C_TEETH)
        _px(cv, 20, ib - 15, C_TEETH)
        _px(cv, 44, ib - 15, C_TEETH)
        _px(cv, 46, ib - 15, C_TEETH)
        if glow:
            _ellipse(cv, 45, bcy - 17, 5, 5, (255, 120, 20))
            _ellipse(cv, 45, bcy - 17, 3, 3, (255, 224, 110))
    if pain:
        _pain_tint(cv)
    return cv


IMP_WALK = [_paint_imp(swing=s) for s in (-2, 0, 2, 0)]
IMP_ATTACK = [_paint_imp(arms='raise'),
              _paint_imp(arms='raise', glow=True),
              _paint_imp(arms='raise', glow=True, squash=0.06)]
IMP_PAIN = [_paint_imp(pain=True, squash=0.12)]
IMP_DIE = [_paint_imp(squash=0.3, pain=True),
           _paint_imp(squash=0.6, pain=True),
           _paint_imp(squash=0.85, pain=True),
           _paint_imp(lie=True),
           _paint_imp(lie=True, blood=True)]


# ---------------------------------------------------------------- soldier ---
C_S_PANT = (56, 68, 46)
C_S_TOP = (110, 114, 76)
C_S_D = (72, 78, 50)
C_SKIN = (214, 170, 132)
C_HELM = (74, 88, 54)
C_RIFLE = (52, 52, 58)
C_WOOD = (112, 78, 44)
C_BOOT = (40, 40, 38)


def _paint_soldier(swing=0, aim=False, flash=False, squash=0.0, lie=False,
                   blood=False, pain=False):
    cv = _canvas()
    if lie:
        _ellipse(cv, 32, 59, 17, 6, C_S_TOP)
        _ellipse(cv, 24, 58, 7, 4, C_S_PANT)
        _ellipse(cv, 47, 57, 6, 5, C_SKIN)
        _rect(cv, 47, 55, 49, 56, (30, 20, 15))
        _ellipse(cv, 43, 53, 4, 3, C_HELM)              # helmet fell off
        _line(cv, 14, 54, 40, 60, C_RIFLE, 1)
        if blood:
            _ellipse(cv, 32, 62, 20, 3, C_BLOOD)
        return cv
    sq = squash
    bcy = 42 + 11 * sq
    bry = max(3.0, 11 * (1 - 0.55 * sq))
    hcy = 27 + 15 * sq
    lry = max(2.0, 7 * (1 - 0.5 * sq))
    ih = int(round(hcy))
    ib = int(round(bcy))
    _ellipse(cv, 28 + swing, 55 + 2 * sq, 3.0, lry, C_S_PANT)
    _ellipse(cv, 36 - swing, 55 + 2 * sq, 3.0, lry, C_S_PANT)
    _ellipse(cv, 28 + swing, 61 + 2 * sq, 3.4, 2.2, C_BOOT)
    _ellipse(cv, 36 - swing, 61 + 2 * sq, 3.4, 2.2, C_BOOT)
    _ellipse(cv, 32, bcy, 9, bry, C_S_TOP)
    _rect(cv, 26, ib + int(bry * 0.5), 38, ib + int(bry * 0.5) + 1, C_S_D)
    if aim:
        _rect(cv, 30, ih + 2, 34, ib + 6, C_RIFLE)
        _rect(cv, 31, ib + 4, 33, ib + 9, C_WOOD)
        _ellipse(cv, 30, ib + 7, 2.5, 2.5, C_SKIN)
    else:
        _line(cv, 20, bcy + 1, 45, bcy - 3, C_RIFLE, 1)
        _rect(cv, 40, ib - 5, 46, ib - 1, C_WOOD)
        _ellipse(cv, 22, bcy + 2, 2.5, 2.5, C_SKIN)
    # head + helmet
    _ellipse(cv, 32, hcy, 6, 6, C_SKIN)
    _ellipse(cv, 32, hcy - 4, 7, 4, C_HELM)
    if pain or sq > 0.4:
        _rect(cv, 29, ih, 30, ih, (40, 25, 15))
        _rect(cv, 34, ih, 35, ih, (40, 25, 15))
    else:
        _px(cv, 29, ih + 1, (35, 30, 25))
        _px(cv, 35, ih + 1, (35, 30, 25))
    _rect(cv, 30, ih + 4, 34, ih + 4, (90, 55, 40))
    if aim and flash:
        _ellipse(cv, 32, ih - 1, 7, 7, (255, 190, 60))
        _ellipse(cv, 32, ih - 1, 4, 4, (255, 245, 200))
    if pain:
        _pain_tint(cv)
    return cv


SOLDIER_WALK = [_paint_soldier(swing=s) for s in (-2, 0, 2, 0)]
SOLDIER_ATTACK = [_paint_soldier(aim=True),
                  _paint_soldier(aim=True, flash=True),
                  _paint_soldier(aim=True, flash=True)]
SOLDIER_PAIN = [_paint_soldier(pain=True, squash=0.12)]
SOLDIER_DIE = [_paint_soldier(squash=0.3, pain=True),
               _paint_soldier(squash=0.6, pain=True),
               _paint_soldier(squash=0.85, pain=True),
               _paint_soldier(lie=True),
               _paint_soldier(lie=True, blood=True)]


# ------------------------------------------------------------------ items ---
def _paint_medkit():
    cv = _canvas()
    _rect(cv, 20, 44, 44, 62, (222, 220, 214))
    _rect(cv, 20, 44, 44, 46, (246, 246, 240))
    _rect(cv, 20, 60, 44, 62, (178, 176, 170))
    _rect(cv, 30, 48, 34, 60, (196, 32, 28))
    _rect(cv, 26, 51, 38, 55, (196, 32, 28))
    return cv


def _paint_bullets():
    cv = _canvas()
    _rect(cv, 22, 46, 42, 62, (96, 92, 86))
    _rect(cv, 22, 46, 42, 48, (122, 118, 110))
    for i in range(4):
        _rect(cv, 25 + i * 4, 40, 27 + i * 4, 46, (226, 182, 54))
        _px(cv, 26 + i * 4, 40, (250, 220, 120))
    _rect(cv, 25, 52, 39, 54, (58, 56, 52))
    return cv


def _paint_shells():
    cv = _canvas()
    _rect(cv, 22, 46, 42, 62, (172, 44, 34))
    _rect(cv, 22, 46, 42, 48, (202, 68, 52))
    for i in range(4):
        _rect(cv, 25 + i * 4, 42, 26 + i * 4, 48, (222, 180, 64))
        _px(cv, 25 + i * 4, 42, (255, 230, 140))
    _rect(cv, 25, 54, 39, 56, (118, 28, 22))
    return cv


def _paint_torch(phase=0):
    cv = _canvas()
    _rect(cv, 30, 40, 33, 62, (112, 76, 42))
    _rect(cv, 33, 40, 34, 62, (78, 52, 30))
    _rect(cv, 28, 38, 35, 41, (60, 58, 56))
    fy = 34 - phase * 2
    _ellipse(cv, 31, fy, 5.5, 8 - phase, (255, 120, 24))
    _ellipse(cv, 31, fy - 2, 3.5, 5 - phase * 0.5, (255, 214, 88))
    _px(cv, 31, fy - 6 + phase, (255, 250, 200))
    return cv


def _paint_fireball(r):
    cv = _canvas()
    _ellipse(cv, 32, 32, r + 3, r + 3, (255, 96, 18))
    _ellipse(cv, 32, 32, r, r, (255, 176, 48))
    _ellipse(cv, 32, 32, max(1, r - 3), max(1, r - 3), (255, 242, 170))
    return cv


def _paint_explosion(i):
    cv = _canvas()
    if i == 0:
        _ellipse(cv, 32, 32, 9, 9, (255, 200, 70))
        _ellipse(cv, 32, 32, 5, 5, (255, 250, 210))
    elif i == 1:
        _ellipse(cv, 32, 32, 14, 14, (255, 120, 28))
        _ellipse(cv, 32, 32, 9, 9, (255, 200, 70))
        _ellipse(cv, 32, 32, 4, 4, (255, 250, 210))
    else:
        _ellipse(cv, 32, 32, 16, 16, (120, 70, 50))
        _ellipse(cv, 32, 32, 11, 11, (70, 60, 55))
        for sx, sy in ((20, 24), (45, 28), (24, 44), (42, 42)):
            _px(cv, sx, sy, (90, 80, 72))
    return cv


# -------------------------------------------------------------- assembly ----
WALL_TEXTURES = [_brick_tex(), _tech_tex(), _stone_tex(), _switch_tex()]
WALL_LUTS = [_shade_lut(w) for w in WALL_TEXTURES]

FLOOR_TEX = _u8(_floor_tex().astype(np.float32) * 0.92)
FLOOR_LUT = _shade_lut(FLOOR_TEX)
CEIL_TEX = _u8(_ceil_tex().astype(np.float32) * 0.8)
CEIL_LUT = _shade_lut(CEIL_TEX)

SPRITES = {
    'imp_walk': IMP_WALK,
    'imp_attack': IMP_ATTACK,
    'imp_pain': IMP_PAIN,
    'imp_die': IMP_DIE,
    'soldier_walk': SOLDIER_WALK,
    'soldier_attack': SOLDIER_ATTACK,
    'soldier_pain': SOLDIER_PAIN,
    'soldier_die': SOLDIER_DIE,
    'medkit': [_paint_medkit()],
    'bullets': [_paint_bullets()],
    'shells': [_paint_shells()],
    'torch': [_paint_torch(0), _paint_torch(1)],
    'fireball': [_paint_fireball(6), _paint_fireball(8)],
    'explosion': [_paint_explosion(0), _paint_explosion(1), _paint_explosion(2)],
}
