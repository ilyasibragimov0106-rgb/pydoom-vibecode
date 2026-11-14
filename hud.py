"""Classic DOOM style status bar: bitmap red numbers, marine face, ARMS panel."""
import pygame

from settings import WIDTH, HEIGHT, HUD_H

_GLYPHS = {
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
}

_bmp_cache = {}


def bitmap(text, scale=6, color=(210, 40, 30)):
    key = (text, scale, color)
    if key not in _bmp_cache:
        w = (6 * len(text) - 1) * scale
        s = pygame.Surface((max(1, w), 7 * scale), pygame.SRCALPHA)
        for i, ch in enumerate(text):
            g = _GLYPHS.get(ch)
            if not g:
                continue
            for ry in range(7):
                row = g[ry]
                for rx in range(5):
                    if row[rx] == '1':
                        pygame.draw.rect(s, color,
                                         ((6 * i + rx) * scale, ry * scale, scale, scale))
        _bmp_cache[key] = s
    return _bmp_cache[key]


class Hud:
    def __init__(self, game):
        self.game = game
        self.panel = self._build_panel()
        self.small = pygame.font.Font(None, 22)
        self.faces = self._build_faces()

    # ------------------------------------------------------------- panel ---
    def _build_panel(self):
        s = pygame.Surface((WIDTH, HUD_H))
        s.fill((52, 52, 58))
        pygame.draw.line(s, (96, 96, 104), (0, 0), (WIDTH, 0), 2)
        pygame.draw.line(s, (24, 24, 28), (0, HUD_H - 2), (WIDTH, HUD_H - 2), 2)
        for x in (160, 400, 560, 790, 990, 1140):
            pygame.draw.line(s, (30, 30, 34), (x, 6), (x, HUD_H - 6), 2)
            pygame.draw.line(s, (86, 86, 94), (x + 2, 6), (x + 2, HUD_H - 6), 1)
        for rx, ry in ((8, 8), (WIDTH - 12, 8), (8, HUD_H - 12), (WIDTH - 12, HUD_H - 12)):
            pygame.draw.circle(s, (90, 90, 98), (rx, ry), 3)
            pygame.draw.circle(s, (28, 28, 32), (rx, ry), 1)
        for bx, bw in ((16, 130), (176, 210), (416, 130), (576, 200), (806, 170), (1006, 130)):
            pygame.draw.rect(s, (38, 38, 44), (bx, 10, bw, HUD_H - 20))
            pygame.draw.rect(s, (70, 70, 78), (bx, 10, bw, HUD_H - 20), 1)
        return s

    # -------------------------------------------------------------- face ---
    def _paint_face(self, tier, look, mood):
        s = pygame.Surface((26, 26), pygame.SRCALPHA)
        skin = (198, 152, 112) if mood != 'dead' else (150, 120, 96)
        pygame.draw.ellipse(s, skin, (3, 3, 20, 22))
        pygame.draw.rect(s, (92, 62, 36), (3, 2, 20, 6))
        pygame.draw.rect(s, (92, 62, 36), (3, 6, 3, 8))
        pygame.draw.rect(s, (92, 62, 36), (20, 6, 3, 8))
        if mood == 'dead':
            pygame.draw.line(s, (60, 30, 20), (7, 11), (11, 15), 2)
            pygame.draw.line(s, (60, 30, 20), (11, 11), (7, 15), 2)
            pygame.draw.line(s, (60, 30, 20), (15, 11), (19, 15), 2)
            pygame.draw.line(s, (60, 30, 20), (19, 11), (15, 15), 2)
            pygame.draw.rect(s, (70, 30, 24), (9, 19, 8, 3))
        elif mood == 'pain':
            pygame.draw.line(s, (60, 36, 24), (7, 10), (11, 12), 2)
            pygame.draw.line(s, (60, 36, 24), (15, 12), (19, 10), 2)
            pygame.draw.ellipse(s, (60, 20, 16), (9, 16, 7, 6))
        elif mood == 'grin':
            pygame.draw.rect(s, (240, 240, 235), (7, 11, 4, 3))
            pygame.draw.rect(s, (240, 240, 235), (15, 11, 4, 3))
            pygame.draw.rect(s, (40, 60, 140), (8, 11, 2, 2))
            pygame.draw.rect(s, (40, 60, 140), (16, 11, 2, 2))
            pygame.draw.rect(s, (70, 40, 26), (8, 17, 10, 4))
            pygame.draw.rect(s, (240, 240, 235), (9, 18, 8, 2))
        else:
            ex = 7 + look
            pygame.draw.rect(s, (240, 240, 235), (ex, 11, 4, 3))
            pygame.draw.rect(s, (240, 240, 235), (ex + 8, 11, 4, 3))
            pygame.draw.rect(s, (40, 60, 140), (ex + 1, 11, 2, 2))
            pygame.draw.rect(s, (40, 60, 140), (ex + 9, 11, 2, 2))
            mw = 8 + tier
            pygame.draw.line(s, (70, 40, 26), (13 - mw // 2, 19), (13 + mw // 2, 19), 2)
        blobs = ((6, 7), (18, 8), (8, 13), (17, 14), (11, 6),
                 (6, 17), (18, 18), (13, 9), (9, 20), (16, 20))
        for i in range(min(tier * 2, len(blobs))):
            bx, by = blobs[i]
            pygame.draw.rect(s, (170, 20, 16), (bx, by, 2, 2))
        if mood == 'dead':
            pygame.draw.rect(s, (150, 16, 12), (4, 20, 18, 5))
        return pygame.transform.scale(s, (78, 78))

    def _build_faces(self):
        faces = {}
        for tier in range(5):
            for look in (-1, 0, 1):
                faces[(tier, look)] = self._paint_face(tier, look, 'ok')
        faces['pain'] = self._paint_face(2, 0, 'pain')
        faces['grin'] = self._paint_face(2, 0, 'grin')
        faces['dead'] = self._paint_face(4, 0, 'dead')
        return faces

    def _current_face(self):
        p = self.game.player
        wm = self.game.weapons
        if not p.alive:
            return self.faces['dead']
        if p.pain_t > 0.2:
            return self.faces['pain']
        if wm.anim_t < 0.22:
            return self.faces['grin']
        h = p.health
        tier = 0 if h > 80 else 1 if h > 60 else 2 if h > 40 else 3 if h > 20 else 4
        look = ((pygame.time.get_ticks() // 800) % 3) - 1
        return self.faces[(tier, look)]

    # --------------------------------------------------------------- draw --
    def draw(self):
        g = self.game
        p = g.player
        scr = g.screen
        y0 = HEIGHT - HUD_H
        scr.blit(self.panel, (0, y0))
        wm = g.weapons

        cur = wm.current
        ammo_txt = str(getattr(p, cur.ammo_attr)) if cur.ammo_attr else "-"
        ammo_col = (230, 190, 60) if g.cheat_ammo else (210, 40, 30)
        scr.blit(bitmap(ammo_txt, 6, ammo_col), (28, y0 + 28))
        scr.blit(self.small.render("AMMO", True, (150, 150, 158)), (30, y0 + 12))
        scr.blit(self.small.render(cur.name, True, (200, 170, 80)), (28, y0 + 78))

        hp_col = (230, 190, 60) if g.cheat_health else (210, 40, 30)
        scr.blit(bitmap(f"{int(p.health)}%", 6, hp_col), (196, y0 + 28))
        scr.blit(self.small.render("HEALTH", True, (150, 150, 158)), (198, y0 + 12))

        face = self._current_face()
        scr.blit(face, (442, y0 + 16))

        scr.blit(self.small.render("ARMS", True, (150, 150, 158)), (596, y0 + 12))
        for i in range(4):
            bx = 588 + i * 46
            active = (wm.index == i)
            col = (200, 170, 60) if active else (90, 90, 98)
            pygame.draw.rect(scr, (30, 30, 36), (bx, y0 + 34, 40, 46))
            pygame.draw.rect(scr, col, (bx, y0 + 34, 40, 46), 2)
            scr.blit(bitmap(str(i + 1), 3, (210, 190, 120) if active else (130, 130, 140)),
                     (bx + 13, y0 + 48))

        for label, val, yy in (("BULL", p.bullets, 12), ("SHEL", p.shells, 38),
                               ("CELL", p.cells, 64)):
            scr.blit(self.small.render(label, True, (150, 150, 158)), (826, y0 + yy + 2))
            scr.blit(bitmap(str(val), 2), (884, y0 + yy))

        scr.blit(self.small.render("KILLS", True, (150, 150, 158)), (1026, y0 + 16))
        scr.blit(bitmap(f"{g.kills}/{g.total_npcs}", 3), (1026, y0 + 40))
        scr.blit(self.small.render(f"LVL {g.level}", True, (200, 170, 80)), (1096, y0 + 44))

        scr.blit(self.small.render("R-RESTART", True, (130, 130, 140)), (1156, y0 + 22))
        scr.blit(self.small.render("TAB-MAP", True, (130, 130, 140)), (1156, y0 + 44))
        scr.blit(self.small.render("M-MUSIC", True, (130, 130, 140)), (1156, y0 + 66))

        # boss health bar
        boss = g.boss
        if boss is not None and boss.alive and boss.state != 'idle':
            frac = max(0.0, boss.health / boss.max_health)
            bw = 420
            bx0 = WIDTH // 2 - bw // 2
            pygame.draw.rect(scr, (30, 4, 4), (bx0, 24, bw, 18))
            pygame.draw.rect(scr, (200, 30, 20), (bx0 + 2, 26, int((bw - 4) * frac), 14))
            lbl = self.small.render("CYBERDEMON", True, (255, 120, 90))
            scr.blit(lbl, (WIDTH // 2 - lbl.get_width() // 2, 46))
