"""Player: WASD movement with wall sliding, mouse look, health/ammo."""
import math

import pygame

from map import move_with_collision
from settings import (PLAYER_SPEED, PLAYER_STRAFE_SPEED, MOUSE_SENS,
                      PLAYER_RADIUS, PLAYER_MAX_HEALTH, START_BULLETS,
                      START_SHELLS, MAX_BULLETS, MAX_SHELLS)


class Player:
    def __init__(self, game, x, y, angle):
        self.game = game
        self.x = x
        self.y = y
        self.angle = angle
        self.health = PLAYER_MAX_HEALTH
        self.bullets = START_BULLETS
        self.shells = START_SHELLS
        self.alive = True
        self.pain_t = 0.0          # pain face timer
        self.hurt_flash = 0.0      # red screen flash
        self.pickup_flash = 0.0    # gold screen flash
        self.bob_t = 0.0           # weapon bob phase
        self.step_acc = 0.0
        self.step_alt = False

    def update(self, dt):
        self.pain_t = max(0.0, self.pain_t - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.pickup_flash = max(0.0, self.pickup_flash - dt)
        if not self.alive:
            return
        keys = pygame.key.get_pressed()
        fwd = (keys[pygame.K_w] or keys[pygame.K_UP]) - (keys[pygame.K_s] or keys[pygame.K_DOWN])
        strafe = keys[pygame.K_d] - keys[pygame.K_a]
        sp_f = fwd * PLAYER_SPEED
        sp_s = strafe * PLAYER_STRAFE_SPEED
        if fwd and strafe:
            sp_f *= 0.7071
            sp_s *= 0.7071
        ca = math.cos(self.angle)
        sa = math.sin(self.angle)
        vx = ca * sp_f - sa * sp_s
        vy = sa * sp_f + ca * sp_s
        self.move(vx * dt, vy * dt)

        moved = math.hypot(vx, vy) * dt
        if moved > 1e-4:
            self.bob_t += dt * 7.5
            self.step_acc += moved
            if self.step_acc >= 0.62:
                self.step_acc = 0.0
                self.step_alt = not self.step_alt
                self.game.sound_mgr.play('step1' if self.step_alt else 'step2', 0.8)

    def turn(self, dx):
        """Mouse look: dx is the horizontal mouse delta in pixels."""
        self.angle += dx * MOUSE_SENS

    def move(self, dx, dy):
        m = self.game.map
        self.x, self.y = move_with_collision(m, self.x, self.y, dx, dy, PLAYER_RADIUS)

    def damage(self, dmg):
        if not self.alive:
            return
        self.health -= dmg
        self.pain_t = 0.45
        self.hurt_flash = 0.4
        self.game.sound_mgr.play('player_pain')
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.game.sound_mgr.play('player_die')
            self.game.on_player_death()

    def add_health(self, n):
        self.health = min(PLAYER_MAX_HEALTH, self.health + n)

    def add_bullets(self, n):
        self.bullets = min(MAX_BULLETS, self.bullets + n)

    def add_shells(self, n):
        self.shells = min(MAX_SHELLS, self.shells + n)
