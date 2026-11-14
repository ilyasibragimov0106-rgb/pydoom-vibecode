"""Global tuning constants for PYDOOM - a 2.5D shooter in the spirit of DOOM (1993)."""
import math

# ---------------------------------------------------------------- window ----
WIDTH, HEIGHT = 1280, 800          # window size, the 3D view fills the window
RENDER_W, RENDER_H = 640, 400      # internal raycasting framebuffer resolution
FPS = 60
TITLE = "PYDOOM - python 2.5D shooter"
HUD_H = 110                        # bottom status bar height in screen pixels

# --------------------------------------------------------------- camera -----
FOV = math.radians(72)
PLANE_LEN = math.tan(FOV * 0.5)    # camera plane half-length
DRAW_DIST = 26.0                   # tiles
FOG_K = 0.22                       # distance fog strength
SHADE_LEVELS = 32                  # precomputed brightness levels per texture


def light_by_dist(d):
    """Classic distance based light diminishing (1.0 near, dark far)."""
    l = 1.25 / (1.0 + d * FOG_K)
    return l if l < 1.0 else 1.0


# --------------------------------------------------------------- player -----
PLAYER_SPEED = 3.6
PLAYER_STRAFE_SPEED = 3.0
MOUSE_SENS = 0.0023                # radians per mouse pixel
PLAYER_RADIUS = 0.28
PLAYER_MAX_HEALTH = 100
START_BULLETS = 60
START_SHELLS = 8
START_CELLS = 40
MAX_BULLETS = 250
MAX_SHELLS = 50
MAX_CELLS = 300
PICKUP_RANGE = 0.62

# -------------------------------------------------------------- weapons -----
PISTOL_DMG = 16
PISTOL_COOLDOWN = 0.36
PISTOL_SPREAD = 0.014
PISTOL_ANIM = 0.16

SHOTGUN_PELLETS = 7
SHOTGUN_DMG = 9
SHOTGUN_COOLDOWN = 0.95
SHOTGUN_SPREAD = 0.085
SHOTGUN_ANIM = 0.42

CHAINSAW_DMG = 13            # per damage tick while the motor runs
CHAINSAW_TICK = 0.12
CHAINSAW_RANGE = 1.4

PLASMA_DMG = 15
PLASMA_COOLDOWN = 0.11
PLASMA_SPREAD = 0.022
PLASMA_SPEED = 9.5
PLASMA_ANIM = 0.12

WAKE_NOISE_RADIUS = 9.0            # gunfire wakes npcs within this radius

# ----------------------------------------------------- cyberdemon boss ------
BOSS_EVERY = 5                     # a cyberdemon guards every Nth level
CYBER_HEALTH = 850
CYBER_SPEED = 1.85
CYBER_MELEE_DMG = 25
CYBER_MELEE_RANGE = 1.9
CYBER_ROCKET_DMG = 26
CYBER_ROCKET_SPEED = 5.5
CYBER_ATTACK_RANGE = 13.0
CYBER_CD = (1.4, 2.3)

# ----------------------------------------------------------------- npc ------
NPC_RADIUS = 0.30
NPC_SEPARATION = 0.72
SIGHT_RANGE = 15.0

IMP_HEALTH = 60
IMP_SPEED = 1.75
IMP_MELEE_DMG = 11
IMP_MELEE_RANGE = 1.25
IMP_FIREBALL_DMG = 14
IMP_FIREBALL_SPEED = 4.6
IMP_ATTACK_RANGE = 9.0
IMP_CD = (1.0, 2.1)

SOLDIER_HEALTH = 40
SOLDIER_SPEED = 1.55
SOLDIER_DMG = 6
SOLDIER_ACCURACY = 0.72
SOLDIER_HOLD_DIST = 3.0            # stop closing in when the player is this near
SOLDIER_ATTACK_RANGE = 14.0
SOLDIER_CD = (0.8, 1.8)

# --------------------------------------------------------------- items ------
MEDKIT_HEALTH = 25
BULLETS_PICKUP = 20
SHELLS_PICKUP = 6
CELLS_PICKUP = 25

EXIT_TRIGGER_DIST = 1.45
