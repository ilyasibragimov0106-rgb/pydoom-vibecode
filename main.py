"""PYDOOM - entry point: game states (menu / play / game over / win),
the classic DOOM menu fire effect, input handling and the main loop.
Run:  python main.py
"""
import math
import os
import random

import numpy as np
import pygame

from settings import (WIDTH, HEIGHT, FPS, TITLE, HUD_H, PICKUP_RANGE,
                      EXIT_TRIGGER_DIST)
from map import GameMap
from levelgen import generate_level
from player import Player
from raycasting import Raycaster
from object_renderer import ObjectRenderer
from hud import Hud
from sound import SoundManager
from sprite_object import Pickup, Torch
from npc import Imp, Soldier, Cyberdemon, Explosion
from weapon import WeaponManager

FIRE_W, FIRE_H = 320, 90
_FIRE_STOPS = ((0.0, (7, 7, 7)), (0.18, (66, 14, 10)), (0.42, (168, 52, 18)),
               (0.68, (236, 124, 26)), (0.86, (252, 206, 74)), (1.0, (255, 244, 190)))


def _fire_palette():
    cols = np.zeros((37, 3), np.float32)
    xs = np.linspace(0, 1, 37)
    for (a, ca), (b, cb) in zip(_FIRE_STOPS[:-1], _FIRE_STOPS[1:]):
        m = (xs >= a) & (xs <= b)
        t = (xs[m] - a) / max(b - a, 1e-6)
        cols[m] = np.array(ca, np.float32) * (1 - t[:, None]) + np.array(cb, np.float32) * t[:, None]
    return cols.astype(np.uint8)


class DoomFire:
    """The famous PSX DOOM fire propagation effect, vectorized with numpy."""

    def __init__(self):
        self.heat = np.zeros((FIRE_H, FIRE_W), np.int32)
        self.heat[-1] = 36
        self.pal = _fire_palette()

    def update(self):
        h = self.heat
        idx = np.arange(FIRE_W)
        for y in range(FIRE_H - 2, -1, -1):
            rnd = np.random.randint(0, 3, FIRE_W)
            src = h[y + 1][(idx - rnd) % FIRE_W]
            h[y] = np.maximum(src - (rnd & 1) - 1, 0)

    def draw(self, screen, y):
        img = np.ascontiguousarray(self.pal[self.heat])
        surf = pygame.image.frombuffer(img.tobytes(), (FIRE_W, FIRE_H), "RGB")
        big = pygame.transform.scale(surf, (WIDTH, FIRE_H * WIDTH // FIRE_W))
        screen.blit(big, (0, y))


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font_mid = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 26)
        self.sound_mgr = SoundManager()
        self.fire = DoomFire()
        self.state = 'menu'
        self.show_minimap = True
        self.paused = False
        self.message = ''
        self.message_t = 0.0
        self.running = True
        self._frame = 0
        self._text_cache = {}
        self.level = 1
        self.level_seed = None
        self.map = None
        self.player = None
        self.npcs = []
        self.items = []
        self.torches = []
        self.projectiles = []
        self.effects = []
        self.weapons = None
        self.raycasting = None
        self.renderer = None
        self.hud = None
        self.kills = 0
        self.total_npcs = 0
        self.sound_mgr.start_music()

    # ------------------------------------------------------------ setup ----
    def new_game(self, fresh=False, next_level=False):
        """Start a run.  fresh: back to level 1 (from the menu).
        next_level: descend deeper - generate the next procedural level.
        Level 1 is the handcrafted map; levels 2..inf are generated.
        R in-game retries the same level with the same layout (same seed)."""
        if fresh:
            self.level = 1
            self.level_seed = None
        if next_level:
            self.level += 1
            self.level_seed = None
        if self.level > 1 and self.level_seed is None:
            self.level_seed = random.getrandbits(32)
        if self.level == 1:
            self.map = GameMap()
        else:
            self.map = GameMap(generate_level(self.level, seed=self.level_seed))
        sx, sy, sa = self.map.player_start
        self.player = Player(self, sx, sy, sa)
        self.npcs = []
        self.boss = None
        for kind, x, y in self.map.npc_spawns:
            if kind == 'imp':
                self.npcs.append(Imp(self, x, y))
            elif kind == 'soldier':
                self.npcs.append(Soldier(self, x, y))
            else:
                self.boss = Cyberdemon(self, x, y)
                self.npcs.append(self.boss)
        if self.boss is not None:
            self.map.lock_exit()
        self.items = [Pickup(self, k, x, y) for k, x, y in self.map.item_spawns]
        self.torches = [Torch(self, x, y) for x, y in self.map.torch_spawns]
        self.projectiles = []
        self.effects = []
        self.weapons = WeaponManager(self)
        self.raycasting = Raycaster(self)
        self.renderer = ObjectRenderer(self)
        self.hud = Hud(self)
        self.kills = 0
        self.total_npcs = len(self.npcs)
        self.message = ''
        self.message_t = 0.0
        self.paused = False
        self._set_state('play')
        self.sound_mgr.start_music()
        if self.boss is not None:
            self.show_message(f"LEVEL {self.level} - THE CYBERDEMON GUARDS THE EXIT")
        else:
            self.show_message(f"ENTERING LEVEL {self.level} - FIND THE GREEN EXIT SWITCH")

    def _set_state(self, st):
        self.state = st
        if st == 'play':
            pygame.event.set_grab(True)
            pygame.mouse.set_visible(False)
            pygame.event.clear(pygame.MOUSEMOTION)   # drop the grab spike
        else:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)

    # ------------------------------------------------------------- world ---
    def get_renderables(self):
        return self.npcs + self.projectiles + self.effects + self.items + self.torches

    def show_message(self, text):
        self.message = text
        self.message_t = 2.6

    def register_noise(self, x, y, radius):
        for n in self.npcs:
            if n.alive:
                n.hear(x, y, radius)

    def on_npc_killed(self, npc):
        self.kills += 1
        if getattr(npc, 'is_boss', False):
            self.map.unlock_exit()
            self.sound_mgr.play('exit')
            self.show_message("THE EXIT SWITCH HAS POWERED ON")
            self.effects.append(Explosion(self, npc.x, npc.y, scale=1.1))

    def on_player_death(self):
        self._set_state('gameover')
        self.sound_mgr.stop_music()

    def win_level(self):
        self._set_state('win')
        self.sound_mgr.stop_music()
        self.sound_mgr.play('exit')

    # ------------------------------------------------------------ update ---
    def update(self, dt):
        if self.state != 'play':
            return
        if self.paused:
            return
        self.player.update(dt)
        keys = pygame.key.get_pressed()
        fire_pressed = (pygame.mouse.get_pressed()[0]
                        or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL])
        self.weapons.update(dt, fire_pressed and self.player.alive)
        for n in self.npcs:
            n.update(dt)
        for pr in self.projectiles:
            pr.update(dt)
        self.projectiles = [x for x in self.projectiles if not x.dead]
        for e in self.effects:
            e.update(dt)
        self.effects = [x for x in self.effects if not x.dead]
        for t in self.torches:
            t.update(dt)
        p = self.player
        if p.alive:
            for it in self.items:
                if it.dead:
                    continue
                if (math.hypot(it.x - p.x, it.y - p.y) < PICKUP_RANGE
                        and it.try_pickup(p)):
                    it.dead = True
                    self.sound_mgr.play('pickup')
                    p.pickup_flash = 0.22
                    self.show_message(it.message)
            for ex in self.map.exit_cells:
                if math.hypot(ex[0] - p.x, ex[1] - p.y) < EXIT_TRIGGER_DIST:
                    if self.map.exit_locked:
                        self.show_message("SEALED! SLAY THE CYBERDEMON FIRST")
                    else:
                        self.win_level()
                    break
        self.message_t -= dt

    # ------------------------------------------------------------ render ---
    def _big_text(self, text, size, color, shadow):
        key = (text, size, color)
        if key not in self._text_cache:
            f = pygame.font.Font(None, size)
            surf = f.render(text, True, color)
            sh = f.render(text, True, shadow)
            combo = pygame.Surface((surf.get_width() + 6, surf.get_height() + 6),
                                   pygame.SRCALPHA)
            combo.blit(sh, (6, 6))
            combo.blit(surf, (0, 0))
            self._text_cache[key] = combo
        return self._text_cache[key]

    def _render_menu(self):
        scr = self.screen
        scr.fill((10, 8, 10))
        self.fire.update()
        self.fire.draw(scr, HEIGHT - 380)
        title = self._big_text("PYDOOM", 130, (190, 26, 20), (60, 8, 6))
        scr.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
        sub = self.font_small.render("A PYTHON 2.5D SHOOTER IN THE SPIRIT OF DOOM (1993)",
                                     True, (170, 150, 120))
        scr.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 210))
        lines = ("WASD - MOVE      MOUSE - LOOK      LMB / CTRL - FIRE",
                 "1 / 2 - WEAPONS  TAB - MINIMAP     M - MUSIC   P - PAUSE",
                 "R - RESTART LEVEL   ESC - MENU")
        for i, ln in enumerate(lines):
            srf = self.font_small.render(ln, True, (160, 160, 170))
            scr.blit(srf, (WIDTH // 2 - srf.get_width() // 2, 265 + i * 30))
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            pr = self.font_mid.render("PRESS ENTER TO START", True, (230, 190, 60))
            scr.blit(pr, (WIDTH // 2 - pr.get_width() // 2, 405))
        ft = self.font_small.render("ALL TEXTURES, SPRITES AND SOUNDS ARE GENERATED PROCEDURALLY",
                                    True, (110, 110, 120))
        scr.blit(ft, (WIDTH // 2 - ft.get_width() // 2, HEIGHT - 40))

    def _render_end(self, text, color, fire_on, prompt):
        scr = self.screen
        scr.fill((12, 6, 6) if fire_on else (8, 10, 8))
        if fire_on:
            self.fire.update()
            self.fire.draw(scr, HEIGHT - 380)
        big = self._big_text(text, 120, color, (30, 6, 4))
        scr.blit(big, (WIDTH // 2 - big.get_width() // 2, 150))
        stats = self.font_mid.render(f"LEVEL {self.level}   -   KILLS: {self.kills} / {self.total_npcs}",
                                     True, (200, 200, 210))
        scr.blit(stats, (WIDTH // 2 - stats.get_width() // 2, 310))
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            pr = self.font_mid.render(prompt, True, (230, 190, 60))
            scr.blit(pr, (WIDTH // 2 - pr.get_width() // 2, 390))

    def render(self):
        if self.state == 'play':
            self.raycasting.render()
            self.renderer.draw()
            self.hud.draw()
            self.renderer.draw_flashes()
            if self.paused:
                dim = pygame.Surface((WIDTH, HEIGHT))
                dim.set_alpha(130)
                dim.fill((0, 0, 0))
                self.screen.blit(dim, (0, 0))
                pr = self.font_mid.render("PAUSED - P TO RESUME", True, (230, 190, 60))
                self.screen.blit(pr, (WIDTH // 2 - pr.get_width() // 2,
                                      HEIGHT // 2 - pr.get_height() // 2))
        elif self.state == 'menu':
            self._render_menu()
        elif self.state == 'gameover':
            self._render_end("YOU DIED", (200, 30, 20), True,
                             "R / ENTER - RETRY LEVEL      ESC - MENU")
        elif self.state == 'win':
            self._render_end(f"LEVEL {self.level} CLEARED", (80, 200, 90), False,
                             "ENTER / R - GO DEEPER      ESC - MENU")
        pygame.display.flip()

    # ------------------------------------------------------------- input ---
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
            return
        if e.type == pygame.KEYDOWN:
            if self.state == 'menu':
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.sound_mgr.play('menu_blip')
                    self.new_game(fresh=True)
                elif e.key == pygame.K_ESCAPE:
                    self.running = False
                elif e.key == pygame.K_m:
                    self.sound_mgr.toggle_music()
            elif self.state == 'play':
                if e.key == pygame.K_ESCAPE:
                    self._set_state('menu')
                elif e.key == pygame.K_r:
                    self.sound_mgr.play('menu_blip')
                    self.new_game()
                elif e.key == pygame.K_p:
                    self.paused = not self.paused
                elif e.key == pygame.K_TAB:
                    self.show_minimap = not self.show_minimap
                elif e.key == pygame.K_m:
                    self.sound_mgr.toggle_music()
                elif e.key == pygame.K_1:
                    self.weapons.select(0)
                elif e.key == pygame.K_2:
                    self.weapons.select(1)
                elif e.key == pygame.K_3:
                    self.weapons.select(2)
                elif e.key == pygame.K_4:
                    self.weapons.select(3)
            else:                                    # gameover / win
                if e.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                    self.new_game(next_level=(self.state == 'win'))
                elif e.key == pygame.K_ESCAPE:
                    self._set_state('menu')
        elif e.type == pygame.MOUSEMOTION:
            # mouse look: applied only while actually playing
            if (self.state == 'play' and not self.paused
                    and self.player is not None and self.player.alive):
                self.player.turn(e.rel[0])
        elif e.type == pygame.MOUSEBUTTONDOWN and self.state == 'menu':
            self.new_game(fresh=True)

    # --------------------------------------------------------------- run ---
    def run(self):
        smoke = os.environ.get("PYDOOM_SMOKE") == "1"
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                self.handle_event(e)
            self.update(dt)
            self.render()
            self._frame += 1
            if smoke and self._frame > 140:
                self.running = False
        pygame.quit()


if __name__ == "__main__":
    Game().run()
