"""Enemies (imp, former soldier), their AI, fireball projectiles, explosions.

AI: idle -> chase when the player is seen (grid line of sight) or heard
(gunshot noise); chases the last known position with wall sliding and a
perpendicular unstick probe (simple pathing), attacks on cooldown.
"""
import math
import random

from map import move_with_collision
from settings import (NPC_RADIUS, NPC_SEPARATION, SIGHT_RANGE,
                      IMP_HEALTH, IMP_SPEED, IMP_MELEE_DMG, IMP_MELEE_RANGE,
                      IMP_FIREBALL_DMG, IMP_FIREBALL_SPEED, IMP_ATTACK_RANGE,
                      IMP_CD,
                      SOLDIER_HEALTH, SOLDIER_SPEED, SOLDIER_DMG,
                      SOLDIER_ACCURACY, SOLDIER_HOLD_DIST,
                      SOLDIER_ATTACK_RANGE, SOLDIER_CD)
from sprite_object import SpriteObject
from textures import SPRITES


class NPC(SpriteObject):
    walk_key = None
    attack_key = None
    pain_key = None
    die_key = None
    sight_sound = ''
    pain_sound = ''
    death_sound = ''
    death_frame_t = 0.16

    def __init__(self, game, x, y):
        super().__init__(game, x, y, scale=0.92, z=0.0)
        self.health = 100
        self.speed = 1.5
        self.state = 'idle'
        self.anim_t = random.random()        # desync walk animations
        self.attack_cd = 0.0
        self.pain_t = 0.0
        self.moving = False
        self.attack_time = 0.45
        self.attack_hit_t = 0.22
        self.attack_done = False
        self.cd_range = (1.0, 2.0)
        self.attack_range = 9.0
        self.last_known = (x, y)
        self.radius = NPC_RADIUS

    @property
    def alive(self):
        return self.health > 0

    # ------------------------------------------------------------- events --
    def hear(self, x, y, radius):
        if not self.alive:
            return
        if math.hypot(x - self.x, y - self.y) <= radius:
            if self.state == 'idle':
                self.wake()
            else:
                self.last_known = (x, y)

    def wake(self):
        if self.state != 'idle' or not self.alive:
            return
        self.state = 'chase'
        self.attack_cd = random.uniform(0.4, 1.0)
        if self.sight_sound:
            self.game.sound_mgr.play(self.sight_sound, 0.9)

    def take_damage(self, dmg, from_pos):
        if not self.alive:
            return
        self.health -= dmg
        self.last_known = from_pos
        if self.health <= 0:
            self.health = 0
            self.state = 'die'
            self.anim_t = 0.0
            self.game.sound_mgr.play(self.death_sound, 0.9)
            self.game.on_npc_killed()
        else:
            self.pain_t = 0.3
            self.game.sound_mgr.play(self.pain_sound, 0.8)
            if self.state == 'idle':
                self.wake()

    # ------------------------------------------------------------ visuals --
    def current_frame(self):
        if self.state == 'die':
            fr = SPRITES[self.die_key]
            return fr[min(int(self.anim_t / self.death_frame_t), len(fr) - 1)]
        if self.pain_t > 0:
            return SPRITES[self.pain_key][0]
        if self.state == 'attack':
            fr = SPRITES[self.attack_key]
            return fr[min(int(self.anim_t / (self.attack_time / len(fr))), len(fr) - 1)]
        fr = SPRITES[self.walk_key]
        if self.moving:
            return fr[int(self.anim_t * 7) % len(fr)]
        return fr[0]

    # -------------------------------------------------------------- logic --
    def update(self, dt):
        if self.state == 'die':
            self.anim_t += dt
            return
        if not self.game.player.alive:
            self.moving = False
            return
        self.anim_t += dt
        self.pain_t = max(0.0, self.pain_t - dt)
        self.attack_cd -= dt
        if self.pain_t > 0:
            self.moving = False
            return
        p = self.game.player
        dx = p.x - self.x
        dy = p.y - self.y
        dist = math.hypot(dx, dy)
        see = dist < SIGHT_RANGE and self.game.map.line_of_sight(self.x, self.y, p.x, p.y)
        if see:
            self.last_known = (p.x, p.y)
        if self.state == 'idle':
            self.moving = False
            if see:
                self.wake()
            return
        if self.state == 'attack':
            self.moving = False
            if not self.attack_done and self.anim_t >= self.attack_hit_t:
                self.attack_done = True
                self.do_attack(dist, see)
            if self.anim_t >= self.attack_time:
                self.state = 'chase'
                self.attack_cd = random.uniform(*self.cd_range)
            return
        # chase
        if self.attack_cd <= 0 and see and dist <= self.attack_range:
            self.state = 'attack'
            self.anim_t = 0.0
            self.attack_done = False
            self.moving = False
            return
        self._move_toward(dt, dist, see)

    def _move_toward(self, dt, dist, see):
        tx, ty = self.last_known
        gx = tx - self.x
        gy = ty - self.y
        gd = math.hypot(gx, gy)
        if gd < 0.25 and not see:
            # reached the last known position - probe sideways (searching)
            a = math.atan2(gy, gx) + random.choice((-1, 1)) * math.pi / 2
            self.last_known = (self.x + math.cos(a) * 2.5, self.y + math.sin(a) * 2.5)
            return
        if gd < 1e-4:
            return
        if self._hold_position(dist, see):
            self.moving = False
            return
        sp = self.speed * dt
        mx = gx / gd * sp
        my = gy / gd * sp
        nx, ny = self._try_move(mx, my)
        moved = math.hypot(nx - self.x, ny - self.y)
        if moved < sp * 0.25 and not see:
            # blocked: probe a perpendicular direction
            side = random.choice((-1, 1))
            if sp > 0:
                ax, ay = -my / sp, mx / sp
            else:
                ax, ay = 0.0, 0.0
            nx2, ny2 = self._try_move(ax * sp * 1.5 * side, ay * sp * 1.5 * side)
            if math.hypot(nx2 - self.x, ny2 - self.y) > moved:
                nx, ny = nx2, ny2
        self.moving = moved > 1e-5
        self.x, self.y = nx, ny

    def _hold_position(self, dist, see):
        return False

    def _try_move(self, mx, my):
        m = self.game.map
        p = self.game.player

        def blocked_by(x, y):
            if p.alive and math.hypot(p.x - x, p.y - y) < 0.72:
                return True
            for o in self.game.npcs:
                if o is not self and o.alive and math.hypot(o.x - x, o.y - y) < NPC_SEPARATION:
                    return True
            return False

        nx, ny = move_with_collision(m, self.x, self.y, mx, my, self.radius)
        if blocked_by(nx, ny):
            nx1, ny1 = move_with_collision(m, self.x, self.y, mx, 0.0, self.radius)
            if not blocked_by(nx1, ny1):
                return nx1, ny1
            nx2, ny2 = move_with_collision(m, self.x, self.y, 0.0, my, self.radius)
            if not blocked_by(nx2, ny2):
                return nx2, ny2
            return self.x, self.y
        return nx, ny

    def do_attack(self, dist, see):
        raise NotImplementedError


class Imp(NPC):
    walk_key = 'imp_walk'
    attack_key = 'imp_attack'
    pain_key = 'imp_pain'
    die_key = 'imp_die'
    sight_sound = 'imp_sight'
    pain_sound = 'imp_pain'
    death_sound = 'imp_die'

    def __init__(self, game, x, y):
        super().__init__(game, x, y)
        self.health = IMP_HEALTH
        self.speed = IMP_SPEED
        self.attack_range = IMP_ATTACK_RANGE
        self.cd_range = IMP_CD
        self.attack_time = 0.5
        self.attack_hit_t = 0.25

    def do_attack(self, dist, see):
        p = self.game.player
        if dist <= IMP_MELEE_RANGE + 0.2:
            self.game.sound_mgr.play('scratch')
            if see and dist < IMP_MELEE_RANGE + 0.5:
                p.damage(int(IMP_MELEE_DMG * random.uniform(0.8, 1.2)))
        else:
            self.game.sound_mgr.play('fireball', 0.8)
            ang = math.atan2(p.y - self.y, p.x - self.x)
            fx = self.x + math.cos(ang) * 0.5
            fy = self.y + math.sin(ang) * 0.5
            self.game.projectiles.append(Fireball(self.game, fx, fy, ang))


class Soldier(NPC):
    walk_key = 'soldier_walk'
    attack_key = 'soldier_attack'
    pain_key = 'soldier_pain'
    die_key = 'soldier_die'
    sight_sound = 'sold_sight'
    pain_sound = 'sold_pain'
    death_sound = 'sold_die'

    def __init__(self, game, x, y):
        super().__init__(game, x, y)
        self.health = SOLDIER_HEALTH
        self.speed = SOLDIER_SPEED
        self.attack_range = SOLDIER_ATTACK_RANGE
        self.cd_range = SOLDIER_CD
        self.attack_time = 0.4
        self.attack_hit_t = 0.18

    def _hold_position(self, dist, see):
        return see and dist < SOLDIER_HOLD_DIST

    def do_attack(self, dist, see):
        self.game.sound_mgr.play('enemy_shot', 0.55)
        if not see:
            return
        chance = SOLDIER_ACCURACY * max(0.25, min(1.0, 1.3 - dist * 0.07))
        if random.random() < chance:
            self.game.player.damage(int(SOLDIER_DMG * random.uniform(0.7, 1.3)))


class Fireball(SpriteObject):
    def __init__(self, game, x, y, ang):
        super().__init__(game, x, y, scale=0.3, z=0.45, emissive=True)
        self.vx = math.cos(ang) * IMP_FIREBALL_SPEED
        self.vy = math.sin(ang) * IMP_FIREBALL_SPEED
        self.anim_t = 0.0
        self.life = 0.0

    def current_frame(self):
        return SPRITES['fireball'][int(self.anim_t * 10) % 2]

    def update(self, dt):
        self.anim_t += dt
        self.life += dt
        if self.life > 5.0:
            self.dead = True
            return
        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt
        if self.game.map.is_wall(nx, ny):
            self.explode()
            return
        self.x, self.y = nx, ny
        p = self.game.player
        if p.alive and math.hypot(p.x - self.x, p.y - self.y) < 0.5:
            p.damage(int(IMP_FIREBALL_DMG * random.uniform(0.8, 1.2)))
            self.explode()

    def explode(self):
        self.dead = True
        self.game.effects.append(Explosion(self.game, self.x, self.y))
        self.game.sound_mgr.play('explosion', 0.8)


class Explosion(SpriteObject):
    def __init__(self, game, x, y):
        super().__init__(game, x, y, scale=0.5, z=0.42, emissive=True)
        self.life = 0.0

    def current_frame(self):
        return SPRITES['explosion'][min(int(self.life / 0.1), 2)]

    def update(self, dt):
        self.life += dt
        if self.life > 0.3:
            self.dead = True
