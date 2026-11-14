"""Billboard sprite projection into the raycaster framebuffer, weapon overlay,
minimap, crosshair, pickup messages and screen flashes."""
import math

import numpy as np
import pygame

from settings import (WIDTH, HEIGHT, RENDER_W, RENDER_H, HUD_H, PLANE_LEN,
                      DRAW_DIST, light_by_dist)


class ObjectRenderer:
    def __init__(self, game):
        self.game = game
        self.minimap_walls = self._build_minimap_walls()
        self.dmg_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.dmg_overlay.fill((190, 0, 0))
        self.gold_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.gold_overlay.fill((200, 160, 40))

    # ---------------------------------------------------------- pipeline ---
    def draw(self):
        """World frame + sprites + weapon + overlays (HUD drawn separately)."""
        self._render_sprites()
        self._blit_world()
        self._draw_weapon()
        self._draw_crosshair()
        if self.game.show_minimap:
            self._draw_minimap()
        self._draw_message()

    def _blit_world(self):
        frame = self.game.raycasting.frame
        surf = pygame.image.frombuffer(frame.tobytes(), (RENDER_W, RENDER_H), "RGB")
        surf = pygame.transform.scale(surf, (WIDTH, HEIGHT))
        self.game.screen.blit(surf, (0, 0))

    # ------------------------------------------------------------ sprites --
    def _render_sprites(self):
        g = self.game
        frame = g.raycasting.frame
        zb = g.raycasting.zbuffer
        p = g.player
        ang = p.angle
        dir_x, dir_y = math.cos(ang), math.sin(ang)
        plane_x, plane_y = -math.sin(ang) * PLANE_LEN, math.cos(ang) * PLANE_LEN
        inv_det = 1.0 / (plane_x * dir_y - dir_x * plane_y)

        things = []
        for s in g.get_renderables():
            if s.dead:
                continue
            dx = s.x - p.x
            dy = s.y - p.y
            d2 = dx * dx + dy * dy
            if d2 > DRAW_DIST * DRAW_DIST:
                continue
            ty = inv_det * (-plane_y * dx + plane_x * dy)
            if ty <= 0.12:
                continue
            things.append((-d2, id(s), s, dx, dy, ty))
        things.sort(key=lambda t: (t[0], t[1]))       # far to near

        for _, _, s, dx, dy, ty in things:
            tx = inv_det * (dir_y * dx - dir_x * dy)
            full_h = RENDER_H / ty
            tex = s.current_frame()
            th, tw = tex.shape[:2]
            spr_h = full_h * s.scale
            spr_w = spr_h * tw / th
            cx = RENDER_W * 0.5 * (1.0 + tx / ty)
            x0 = int(round(cx - spr_w * 0.5))
            x1 = int(round(cx + spr_w * 0.5))
            bottom = RENDER_H * 0.5 + full_h * 0.5 - full_h * s.z
            y0 = int(round(bottom - spr_h))
            y1 = int(round(bottom))
            sx0, sx1 = max(0, x0), min(RENDER_W, x1)
            sy0, sy1 = max(0, y0), min(RENDER_H, y1)
            if sx1 <= sx0 or sy1 <= sy0:
                continue
            shade = 1.0 if s.emissive else light_by_dist(ty)
            tex_rows = ((np.arange(sy0, sy1) - y0)
                        * (th / max(1, y1 - y0))).astype(np.int32)
            np.clip(tex_rows, 0, th - 1, out=tex_rows)
            alpha_any = (tex[:, :, 3] > 110).any(axis=0)
            span = max(1, x1 - x0)
            for sx in range(sx0, sx1):
                if zb[sx] <= ty:
                    continue
                tc = int((sx - x0) * tw / span)
                if tc < 0 or tc >= tw or not alpha_any[tc]:
                    continue
                col = tex[tex_rows, tc]
                mask = col[:, 3] > 110
                if not mask.any():
                    continue
                reg = frame[sy0:sy1, sx]
                reg[mask] = (col[mask, :3].astype(np.float32)
                             * shade).astype(np.uint8)

    # ------------------------------------------------------------- weapon --
    def _draw_weapon(self):
        g = self.game
        wm = g.weapons
        w = wm.current
        p = g.player
        t = wm.anim_t
        nf = len(w.frames)
        if nf == 3:
            idx = 0 if t >= w.anim_time else (1 if t < w.anim_time * 0.45 else 2)
        else:
            idx = 0 if t >= w.anim_time else min(1 + int(t / w.anim_time * (nf - 1)), nf - 1)
        img = w.frames[idx]
        big = pygame.transform.scale(img,
                                     (img.get_width() * w.scale,
                                      img.get_height() * w.scale))
        bob_x = int(math.sin(p.bob_t) * 9)
        bob_y = int(abs(math.cos(p.bob_t)) * 7)
        recoil = 10 if wm.anim_t < 0.09 else 0
        x = WIDTH // 2 - big.get_width() // 2 + bob_x
        y = HEIGHT - HUD_H - big.get_height() + 10 + bob_y + recoil
        g.screen.blit(big, (x, y))

    def _draw_crosshair(self):
        s = self.game.screen
        cx, cy = WIDTH // 2, (HEIGHT - HUD_H) // 2
        c = (220, 60, 50)
        pygame.draw.line(s, c, (cx - 8, cy), (cx - 4, cy), 1)
        pygame.draw.line(s, c, (cx + 4, cy), (cx + 8, cy), 1)
        pygame.draw.line(s, c, (cx, cy - 8), (cx, cy - 4), 1)
        pygame.draw.line(s, c, (cx, cy + 4), (cx, cy + 8), 1)
        pygame.draw.circle(s, (255, 90, 70), (cx, cy), 1)

    # ------------------------------------------------------------ minimap --
    def _build_minimap_walls(self):
        m = self.game.map
        cs = 7
        surf = pygame.Surface((m.w * cs, m.h * cs), pygame.SRCALPHA)
        colors = {1: (150, 70, 60), 2: (120, 130, 150),
                  3: (130, 130, 120), 4: (70, 160, 90), 5: (150, 45, 40)}
        for y in range(m.h):
            for x in range(m.w):
                v = m.grid[y][x]
                if v:
                    pygame.draw.rect(surf, colors.get(v, (200, 200, 200)),
                                     (x * cs, y * cs, cs, cs))
        surf.set_alpha(205)
        return surf

    def _draw_minimap(self):
        g = self.game
        cs = 7
        surf = self.minimap_walls.copy()
        for it in g.items:
            if not it.dead:
                pygame.draw.circle(surf, (80, 200, 255),
                                   (int(it.x * cs), int(it.y * cs)), 2)
        for n in g.npcs:
            if n.alive:
                is_boss = getattr(n, 'is_boss', False)
                pygame.draw.circle(surf, (170, 80, 255) if is_boss else (255, 60, 40),
                                   (int(n.x * cs), int(n.y * cs)),
                                   3 if is_boss else 2)
        for ex in g.map.exit_cells:
            col = (60, 255, 90) if not g.map.exit_locked else (220, 60, 40)
            pygame.draw.circle(surf, col, (int(ex[0] * cs), int(ex[1] * cs)), 3)
        p = g.player
        a = p.angle
        px, py = p.x * cs, p.y * cs
        pts = [(px + math.cos(a) * 5, py + math.sin(a) * 5),
               (px + math.cos(a + 2.5) * 4, py + math.sin(a + 2.5) * 4),
               (px + math.cos(a - 2.5) * 4, py + math.sin(a - 2.5) * 4)]
        pygame.draw.polygon(surf, (255, 230, 80), pts)
        g.screen.blit(surf, (10, 10))

    # ------------------------------------------------------------ message --
    def _draw_message(self):
        g = self.game
        if g.message_t <= 0:
            return
        font = pygame.font.Font(None, 28)
        surf = font.render(g.message, True, (230, 200, 80))
        x = WIDTH // 2 - surf.get_width() // 2
        g.screen.blit(surf, (x, 10))

    # ------------------------------------------------------------ flashes --
    def draw_flashes(self):
        p = self.game.player
        if p.hurt_flash > 0:
            self.dmg_overlay.set_alpha(int(120 * min(1.0, p.hurt_flash / 0.4)))
            self.game.screen.blit(self.dmg_overlay, (0, 0))
        if p.pickup_flash > 0:
            self.gold_overlay.set_alpha(int(60 * min(1.0, p.pickup_flash / 0.22)))
            self.game.screen.blit(self.gold_overlay, (0, 0))
