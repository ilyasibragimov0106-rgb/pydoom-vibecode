"""Weapons: pistol, shotgun, chainsaw and plasma gun - all procedurally drawn.

kind: 'hitscan' (instant ray with pellets), 'melee' (chainsaw damage ticks),
'projectile' (plasma bolts flying as sprites).
"""
import math
import random

import pygame

from npc import PlasmaBolt
from settings import (PISTOL_DMG, PISTOL_COOLDOWN, PISTOL_SPREAD, PISTOL_ANIM,
                      SHOTGUN_PELLETS, SHOTGUN_DMG, SHOTGUN_COOLDOWN,
                      SHOTGUN_SPREAD, SHOTGUN_ANIM, WAKE_NOISE_RADIUS,
                      DRAW_DIST, CHAINSAW_DMG, CHAINSAW_TICK, CHAINSAW_RANGE,
                      PLASMA_DMG, PLASMA_COOLDOWN, PLASMA_SPREAD, PLASMA_ANIM)


def _star(cx, cy, r_out, r_in, n=8):
    pts = []
    for i in range(n * 2):
        ang = math.pi * i / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    return pts


def _hand(s, x, y, w, h):
    pygame.draw.ellipse(s, (206, 158, 116), (x, y, w, h))
    pygame.draw.ellipse(s, (172, 124, 88), (x, y + h * 0.4, w, h * 0.7))


def build_pistol_frames():
    frames = []
    for mode in ('idle', 'fire0', 'fire1'):
        s = pygame.Surface((46, 44), pygame.SRCALPHA)
        dy = 0 if mode == 'idle' else (3 if mode == 'fire0' else 2)
        _hand(s, 12, 30 + dy, 24, 13)
        pygame.draw.rect(s, (44, 44, 50), (18, 22 + dy, 13, 12))    # grip
        pygame.draw.rect(s, (80, 80, 88), (16, 10 + dy, 18, 14))    # slide
        pygame.draw.rect(s, (104, 104, 114), (16, 10 + dy, 18, 5))  # slide top
        pygame.draw.rect(s, (36, 36, 42), (19, 13 + dy, 12, 3))     # ejection
        pygame.draw.rect(s, (56, 56, 63), (20, 6 + dy, 10, 5))      # muzzle
        pygame.draw.rect(s, (14, 14, 16), (22, 7 + dy, 6, 3))
        if mode != 'idle':
            ro, ri = (11, 5) if mode == 'fire0' else (7, 3)
            pygame.draw.polygon(s, (255, 206, 64), _star(25, 4, ro, ri))
            pygame.draw.circle(s, (255, 252, 214), (25, 4), ri - 2)
        frames.append(s)
    return frames


def build_shotgun_frames():
    frames = []
    for mode in ('idle', 'fire0', 'fire1', 'pump'):
        s = pygame.Surface((58, 50), pygame.SRCALPHA)
        py_ = 6 if mode == 'pump' else 0
        _hand(s, 6, 34 + py_, 16, 12)
        _hand(s, 36, 34 + py_, 16, 12)
        pygame.draw.rect(s, (58, 58, 66), (25, 2, 9, 34))      # barrel
        pygame.draw.rect(s, (76, 76, 84), (25, 2, 4, 34))      # highlight
        pygame.draw.rect(s, (40, 40, 46), (32, 2, 2, 34))
        pygame.draw.rect(s, (34, 34, 38), (26, 0, 7, 3))       # muzzle
        pygame.draw.rect(s, (48, 48, 54), (24, 30 + py_, 12, 8))   # receiver
        pygame.draw.rect(s, (124, 86, 46), (21, 36 + py_, 17, 9))  # pump wood
        pygame.draw.rect(s, (96, 64, 34), (21, 40 + py_, 17, 2))
        pygame.draw.rect(s, (70, 70, 78), (26, 44, 9, 5))      # stock tip
        if mode in ('fire0', 'fire1'):
            ro, ri = (14, 6) if mode == 'fire0' else (9, 4)
            pygame.draw.polygon(s, (255, 206, 64), _star(29, 2, ro, ri))
            pygame.draw.circle(s, (255, 252, 214), (29, 2), ri - 2)
        frames.append(s)
    return frames


def build_chainsaw_frames():
    frames = []
    for mode in ('idle', 'saw0', 'saw1'):
        s = pygame.Surface((52, 46), pygame.SRCALPHA)
        bd = 0 if mode == 'idle' else (-1 if mode == 'saw0' else 1)
        _hand(s, 8, 32, 16, 12)
        _hand(s, 30, 34, 16, 10)
        pygame.draw.rect(s, (60, 60, 66), (22, 14, 10, 10))     # top handle
        pygame.draw.rect(s, (110, 112, 70), (16, 22, 22, 16))   # motor body
        pygame.draw.rect(s, (140, 142, 92), (16, 22, 22, 5))
        pygame.draw.rect(s, (70, 70, 44), (18, 30, 8, 3))       # vents
        pygame.draw.rect(s, (70, 70, 44), (28, 30, 8, 3))
        pygame.draw.rect(s, (46, 46, 40), (38, 24, 5, 7))       # exhaust
        pygame.draw.rect(s, (178, 178, 190), (25, 2 + bd, 6, 20))  # blade
        for ty in range(2, 20, 2):                              # teeth
            pygame.draw.rect(s, (150, 150, 162), (23, ty + bd, 2, 2))
            pygame.draw.rect(s, (150, 150, 162), (31, ty + 1 + bd, 2, 2))
        if mode != 'idle':
            pygame.draw.circle(s, (255, 230, 90), (28, 3 + bd), 2)  # spark
            pygame.draw.circle(s, (255, 160, 40), (26, 5 + bd), 1)
        frames.append(s)
    return frames


def build_plasma_frames():
    frames = []
    for mode in ('idle', 'fire0', 'fire1'):
        s = pygame.Surface((56, 44), pygame.SRCALPHA)
        _hand(s, 8, 32, 16, 10)
        _hand(s, 34, 32, 14, 10)
        pygame.draw.rect(s, (40, 45, 60), (18, 32, 10, 8))      # grip
        pygame.draw.rect(s, (70, 80, 110), (22, 16, 14, 18))    # body
        pygame.draw.rect(s, (90, 100, 130), (22, 16, 14, 4))    # rail
        pygame.draw.rect(s, (50, 55, 75), (25, 6, 8, 10))       # barrel
        pygame.draw.rect(s, (30, 34, 48), (27, 7, 4, 8))        # bore
        cell = (160, 240, 255) if mode != 'idle' else (60, 140, 200)
        pygame.draw.rect(s, cell, (24, 20, 10, 5))              # energy cell
        if mode != 'idle':
            ro, ri = (12, 5) if mode == 'fire0' else (8, 3)
            pygame.draw.polygon(s, (120, 200, 255), _star(29, 4, ro, ri))
            pygame.draw.circle(s, (230, 250, 255), (29, 4), ri - 2)
        frames.append(s)
    return frames


class Weapon:
    def __init__(self, name, frames, ammo_attr, damage, pellets, spread,
                 cooldown, anim_time, sound, scale=4, kind='hitscan'):
        self.name = name
        self.frames = frames
        self.ammo_attr = ammo_attr
        self.damage = damage
        self.pellets = pellets
        self.spread = spread
        self.cooldown = cooldown
        self.anim_time = anim_time
        self.sound = sound
        self.scale = scale
        self.kind = kind


class WeaponManager:
    def __init__(self, game):
        self.game = game
        self.weapons = [
            Weapon("PISTOL", build_pistol_frames(), 'bullets', PISTOL_DMG, 1,
                   PISTOL_SPREAD, PISTOL_COOLDOWN, PISTOL_ANIM, 'pistol'),
            Weapon("SHOTGUN", build_shotgun_frames(), 'shells', SHOTGUN_DMG,
                   SHOTGUN_PELLETS, SHOTGUN_SPREAD, SHOTGUN_COOLDOWN,
                   SHOTGUN_ANIM, 'shotgun'),
            Weapon("CHAINSAW", build_chainsaw_frames(), None, CHAINSAW_DMG, 1,
                   0.0, CHAINSAW_TICK, CHAINSAW_TICK, 'saw', kind='melee'),
            Weapon("PLASMA GUN", build_plasma_frames(), 'cells', PLASMA_DMG, 1,
                   PLASMA_SPREAD, PLASMA_COOLDOWN, PLASMA_ANIM, 'plasma',
                   kind='projectile'),
        ]
        self.index = 0
        self.cooldown = 0.0
        self.anim_t = 99.0

    @property
    def current(self):
        return self.weapons[self.index]

    def select(self, i):
        if 0 <= i < len(self.weapons) and i != self.index:
            self.index = i
            self.cooldown = max(self.cooldown, 0.18)
            self.anim_t = 99.0
            self.game.sound_mgr.play('switch_w', 0.7)

    def update(self, dt, fire_pressed):
        self.cooldown -= dt
        self.anim_t += dt
        if fire_pressed and self.cooldown <= 0 and self.game.player.alive:
            if self.current.kind == 'melee':
                self.saw()
            else:
                self.fire()

    def saw(self):
        """Chainsaw: continuous motor ticks, damage on contact in front."""
        g = self.game
        p = g.player
        w = self.current
        self.cooldown = w.cooldown
        self.anim_t = 0.0
        g.register_noise(p.x, p.y, 4.0)
        ang = p.angle
        best = None
        best_d = 1e9
        for npc in g.npcs:
            if not npc.alive:
                continue
            ndx = npc.x - p.x
            ndy = npc.y - p.y
            nd = math.hypot(ndx, ndy)
            if nd > CHAINSAW_RANGE:
                continue
            na = math.atan2(ndy, ndx)
            diff = abs((ang - na + math.pi) % (2 * math.pi) - math.pi)
            if diff <= math.atan2(npc.hit_w + 0.12, nd) and nd < best_d:
                if g.map.line_of_sight(p.x, p.y, npc.x, npc.y):
                    best, best_d = npc, nd
        if best is not None:
            g.sound_mgr.play('saw_hit', 0.9)
            best.take_damage(int(w.damage * random.uniform(0.85, 1.15)),
                             (p.x, p.y))
        else:
            g.sound_mgr.play('saw', 0.55)

    def fire(self):
        g = self.game
        p = g.player
        w = self.current
        if getattr(p, w.ammo_attr) <= 0:
            g.sound_mgr.play('empty', 0.7)
            self.cooldown = 0.3
            return
        setattr(p, w.ammo_attr, getattr(p, w.ammo_attr) - 1)
        g.sound_mgr.play(w.sound)
        self.cooldown = w.cooldown
        self.anim_t = 0.0
        g.register_noise(p.x, p.y, WAKE_NOISE_RADIUS)
        if w.kind == 'projectile':
            ang = p.angle + random.gauss(0, w.spread)
            bx = p.x + math.cos(ang) * 0.4
            by = p.y + math.sin(ang) * 0.4
            g.projectiles.append(PlasmaBolt(g, bx, by, ang))
            return
        for _ in range(w.pellets):
            ang = p.angle + random.gauss(0, w.spread)
            wall_d = g.map.cast_ray(p.x, p.y, math.cos(ang), math.sin(ang), DRAW_DIST)
            best = None
            best_d = 1e9
            for npc in g.npcs:
                if not npc.alive:
                    continue
                ndx = npc.x - p.x
                ndy = npc.y - p.y
                nd = math.hypot(ndx, ndy)
                if nd < 1e-4 or nd > wall_d + 0.2:
                    continue
                na = math.atan2(ndy, ndx)
                diff = abs((ang - na + math.pi) % (2 * math.pi) - math.pi)
                if diff <= math.atan2(npc.hit_w, nd) and nd < best_d:
                    best, best_d = npc, nd
            if best is not None:
                falloff = 1.0 if w.pellets == 1 else max(0.35, min(1.0, 1.15 - best_d * 0.09))
                dmg = w.damage * falloff * random.uniform(0.85, 1.15)
                best.take_damage(int(dmg), (p.x, p.y))
