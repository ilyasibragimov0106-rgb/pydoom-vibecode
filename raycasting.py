"""Vectorized DDA raycaster writing into a numpy RGB framebuffer.

One ray per framebuffer column: walls via a batched grid DDA (all rays
advance together with boolean masks), textured slices written column by
column from precomputed shade LUTs.  Floor/ceiling use the horizontal
scanline method, grouped by brightness level so each group is a single
fancy-index gather.
"""
import math

import numpy as np

from settings import (RENDER_W, RENDER_H, PLANE_LEN, FOG_K, SHADE_LEVELS)
from textures import WALL_LUTS, FLOOR_LUT, CEIL_LUT, TEX


class Raycaster:
    def __init__(self, game):
        self.game = game
        self.frame = np.zeros((RENDER_H, RENDER_W, 3), np.uint8)
        self.zbuffer = np.full(RENDER_W, 1e9, np.float32)
        self.cam_x = (2.0 * np.arange(RENDER_W, dtype=np.float32) / RENDER_W) - 1.0
        self._rows = {}
        # padded grid (walls beyond the border) for vectorized cell lookups
        m = game.map
        pad = np.ones((m.h + 2, m.w + 2), np.int32)
        pad[1:-1, 1:-1] = np.array(m.grid, np.int32)
        self._grid_pad = pad

    def render(self):
        p = self.game.player
        self._draw_floor_ceiling(p)
        self._cast_walls(p)

    # ------------------------------------------------------------ shading --
    @staticmethod
    def _light_vec(d):
        return np.clip(1.25 / (1.0 + d * FOG_K), 0.0, 1.0)

    # ------------------------------------------------------- floor / ceil --
    def _draw_floor_ceiling(self, p):
        ang = p.angle
        dir_x, dir_y = math.cos(ang), math.sin(ang)
        plane_x, plane_y = -math.sin(ang) * PLANE_LEN, math.cos(ang) * PLANE_LEN
        rdx = dir_x + plane_x * self.cam_x
        rdy = dir_y + plane_y * self.cam_x
        half = RENDER_H // 2
        ys = np.arange(half, RENDER_H, dtype=np.float32)
        pdist = np.maximum(ys - half, 0.5)
        row_dist = (0.5 * RENDER_H) / pdist
        fx = p.x + row_dist[:, None] * rdx[None, :]
        fy = p.y + row_dist[:, None] * rdy[None, :]
        tx = (fx * TEX).astype(np.int32) & (TEX - 1)
        ty = (fy * TEX).astype(np.int32) & (TEX - 1)
        lev = (self._light_vec(row_dist) * (SHADE_LEVELS - 1)).astype(np.int32)
        frame = self.frame
        for l in np.unique(lev):
            sel = lev == l
            yr = ys[sel].astype(np.int32)
            frame[yr] = FLOOR_LUT[l][ty[sel], tx[sel]]
            yc = (RENDER_H - 1) - yr
            frame[yc] = CEIL_LUT[max(0, int(l) - 4)][ty[sel], tx[sel]]

    # --------------------------------------------------------------- walls --
    def _cast_walls(self, p):
        ang = p.angle
        dir_x, dir_y = math.cos(ang), math.sin(ang)
        plane_x, plane_y = -math.sin(ang) * PLANE_LEN, math.cos(ang) * PLANE_LEN
        px, py = p.x, p.y
        W = RENDER_W

        rdx = dir_x + plane_x * self.cam_x
        rdy = dir_y + plane_y * self.cam_x
        rdx = np.where(rdx >= 0, np.maximum(rdx, 1e-9), np.minimum(rdx, -1e-9))
        rdy = np.where(rdy >= 0, np.maximum(rdy, 1e-9), np.minimum(rdy, -1e-9))

        map_x = np.full(W, int(px), np.int32)
        map_y = np.full(W, int(py), np.int32)
        delta_x = np.abs(1.0 / rdx)
        delta_y = np.abs(1.0 / rdy)
        step_x = np.where(rdx < 0, -1, 1)
        step_y = np.where(rdy < 0, -1, 1)
        side_x = np.where(rdx < 0, (px - map_x) * delta_x, (map_x + 1.0 - px) * delta_x)
        side_y = np.where(rdy < 0, (py - map_y) * delta_y, (map_y + 1.0 - py) * delta_y)

        active = np.ones(W, dtype=bool)
        side = np.zeros(W, np.int8)
        hit = np.zeros(W, np.int32)
        gp = self._grid_pad
        for _ in range(96):              # >= diagonal crossings of a 30x30 map
            if not active.any():
                break
            go_x = active & (side_x < side_y)
            go_y = active & ~go_x
            side_x[go_x] += delta_x[go_x]
            map_x[go_x] += step_x[go_x]
            side[go_x] = 0
            side_y[go_y] += delta_y[go_y]
            map_y[go_y] += step_y[go_y]
            side[go_y] = 1
            vals = gp[map_y + 1, map_x + 1]
            newly = active & (vals > 0)
            hit[newly] = vals[newly]
            active &= vals == 0

        perp = np.where(side == 0, side_x - delta_x, side_y - delta_y)
        perp = np.maximum(perp, 1e-4)
        wall_x = np.where(side == 0, py + perp * rdy, px + perp * rdx)
        wall_x -= np.floor(wall_x)
        tex_x = (wall_x * TEX).astype(np.int32)
        flip = ((side == 0) & (rdx > 0)) | ((side == 1) & (rdy < 0))
        tex_x = np.where(flip, TEX - 1 - tex_x, tex_x)
        lev = (self._light_vec(perp) * (SHADE_LEVELS - 1)).astype(np.int32)
        lev = np.where(side == 1, np.maximum(lev - 5, 0), lev)
        line_h = np.clip((RENDER_H / perp).astype(np.int32), 1, 1400)

        frame = self.frame
        zb = self.zbuffer
        for x in range(W):
            h_i = int(hit[x])
            zb[x] = float(perp[x])
            if h_i == 0:
                zb[x] = 1e9
                continue
            y0, y1, rows = self._rows_for(int(line_h[x]))
            if rows.size == 0:
                continue
            lut = WALL_LUTS[h_i - 1][int(lev[x])]
            frame[y0:y1, x] = lut[rows, int(tex_x[x])]

    def _rows_for(self, line_h):
        """Cached texture-row indices + screen clip range for a wall height."""
        c = self._rows.get(line_h)
        if c is None:
            half_h = RENDER_H // 2
            top = half_h - (line_h >> 1)
            y0 = max(0, top)
            y1 = min(RENDER_H, top + line_h)
            if y1 <= y0:
                rows = np.zeros(0, np.int32)
            else:
                rows = (((np.arange(y0, y1) - top) * (TEX / line_h))
                        .astype(np.int32)) & (TEX - 1)
            c = (y0, y1, rows)
            self._rows[line_h] = c
        return c
