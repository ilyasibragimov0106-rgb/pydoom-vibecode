"""Level data, grid queries, DDA ray helpers and shared collision movement.

Map legend:  1 brick wall, 2 tech wall, 3 stone wall, X exit switch (tex 4),
             P player start, I imp, S soldier, M medkit, A bullets, G shells,
             T torch, . empty floor.
"""
import math

MAP_DATA = [
    "111111111111111111111111",
    "1......1........1......1",
    "1.P.T..1..I..A..1..T...1",
    "1......1...............1",
    "1...I.....2222..1.G....1",
    "1......1..2M.2..1......1",
    "1......1........1...I..1",
    "1111.1111111.111111.1111",
    "1........T......T......1",
    "1............S.........1",
    "1..2..A.............2..1",
    "1........333333........1",
    "1.T......3.I..3...I....1",
    "1..G.....3..M.3........1",
    "1........333.33........1",
    "1...............2......1",
    "1....S....I..........T.1",
    "1.......2..............1",
    "1......................1",
    "1..................11111",
    "1.............M.......X1",
    "1.M...............S11111",
    "1...........G....A.....1",
    "111111111111111111111111",
]

WALL_TEX = {'1': 1, '2': 2, '3': 3, '4': 4, 'X': 4}


class GameMap:
    """Parses MAP_DATA once, validates it and answers grid queries."""

    def __init__(self):
        rows = [r for r in MAP_DATA if r.strip()]
        self.h = len(rows)
        self.w = len(rows[0])
        for i, r in enumerate(rows):
            if len(r) != self.w:
                raise ValueError(f"map row {i} has {len(r)} cols, expected {self.w}")
        self.grid = [[WALL_TEX.get(ch, 0) for ch in row] for row in rows]
        for i in range(self.w):
            if self.grid[0][i] == 0 or self.grid[self.h - 1][i] == 0:
                raise ValueError("map border is not closed")
        for j in range(self.h):
            if self.grid[j][0] == 0 or self.grid[j][self.w - 1] == 0:
                raise ValueError("map border is not closed")

        self.player_start = None
        self.npc_spawns = []
        self.item_spawns = []
        self.torch_spawns = []
        self.exit_cells = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                cx, cy = x + 0.5, y + 0.5
                if ch == 'P':
                    self.player_start = (cx, cy, 0.0)
                elif ch == 'I':
                    self.npc_spawns.append(('imp', cx, cy))
                elif ch == 'S':
                    self.npc_spawns.append(('soldier', cx, cy))
                elif ch == 'M':
                    self.item_spawns.append(('medkit', cx, cy))
                elif ch == 'A':
                    self.item_spawns.append(('bullets', cx, cy))
                elif ch == 'G':
                    self.item_spawns.append(('shells', cx, cy))
                elif ch == 'T':
                    self.torch_spawns.append((cx, cy))
                elif ch == 'X':
                    self.exit_cells.append((cx, cy))
        if self.player_start is None:
            raise ValueError("map has no player start 'P'")
        self._validate_reachable()

    # ------------------------------------------------------------ queries --
    def cell(self, ix, iy):
        if 0 <= ix < self.w and 0 <= iy < self.h:
            return self.grid[iy][ix]
        return 1

    def is_wall_idx(self, ix, iy):
        return self.cell(ix, iy) > 0

    def is_wall(self, x, y):
        return self.is_wall_idx(int(math.floor(x)), int(math.floor(y)))

    # -------------------------------------------------------------- rays ---
    def cast_ray(self, x0, y0, dx, dy, max_dist):
        """Distance (grid DDA) to the first wall along the ray, <= max_dist."""
        d = math.hypot(dx, dy)
        if d < 1e-9:
            return max_dist
        dx /= d
        dy /= d
        ix, iy = int(x0), int(y0)
        if self.is_wall_idx(ix, iy):
            return 0.0
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        tdx = abs(1.0 / dx) if dx != 0 else 1e30
        tdy = abs(1.0 / dy) if dy != 0 else 1e30
        if dx > 0:
            tmx = (ix + 1 - x0) / dx
        elif dx < 0:
            tmx = (ix - x0) / dx
        else:
            tmx = 1e30
        if dy > 0:
            tmy = (iy + 1 - y0) / dy
        elif dy < 0:
            tmy = (iy - y0) / dy
        else:
            tmy = 1e30
        t = 0.0
        while t <= max_dist:
            if tmx < tmy:
                t = tmx
                tmx += tdx
                ix += step_x
            else:
                t = tmy
                tmy += tdy
                iy += step_y
            if self.is_wall_idx(ix, iy):
                return min(t, max_dist)
        return max_dist

    def line_of_sight(self, x0, y0, x1, y1):
        dist = math.hypot(x1 - x0, y1 - y0)
        t = self.cast_ray(x0, y0, x1 - x0, y1 - y0, dist + 1.0)
        return t >= dist - 1e-4

    # -------------------------------------------------------- validation ---
    def _validate_reachable(self):
        start = (int(self.player_start[0]), int(self.player_start[1]))
        seen = {start}
        queue = [start]
        while queue:
            x, y = queue.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen and not self.is_wall_idx(nx, ny):
                    seen.add((nx, ny))
                    queue.append((nx, ny))

        def need(cx, cy):
            if not self.is_wall_idx(int(cx), int(cy)) and (int(cx), int(cy)) not in seen:
                raise ValueError(f"unreachable spawn near ({cx}, {cy})")

        for _, cx, cy in self.npc_spawns:
            need(cx, cy)
        for _, cx, cy in self.item_spawns:
            need(cx, cy)
        for cx, cy in self.torch_spawns:
            need(cx, cy)
        for cx, cy in self.exit_cells:      # some adjacent floor cell must exist
            ok = any((int(cx) + dx, int(cy) + dy) in seen
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if not ok:
                raise ValueError("exit switch is unreachable")


def _blocked(m, x, y, r):
    return (m.is_wall(x - r, y - r) or m.is_wall(x + r, y - r)
            or m.is_wall(x - r, y + r) or m.is_wall(x + r, y + r))


def move_with_collision(m, x, y, dx, dy, r):
    """Move with sliding along walls: x and y axes are resolved separately."""
    nx = x + dx
    if not _blocked(m, nx, y, r):
        x = nx
    ny = y + dy
    if not _blocked(m, x, ny, r):
        y = ny
    return x, y
