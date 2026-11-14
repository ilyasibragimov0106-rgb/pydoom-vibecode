"""Endless procedural level generation: rooms + corridors, same map legend
as map.MAP_DATA (1/2/3 walls, X exit switch, P player, I/S enemies,
M/A/G items, T torches).

generate_level(level, seed) flood-fill-validates every candidate layout and
retries with a derived seed until one passes, so GameMap never sees a broken
level.  Difficulty scales with `level`: bigger dungeon, more enemies and a
growing share of soldiers.
"""
import random

WALL, FLOOR, PILLAR, EXIT = '1', '.', '2', 'X'
SIZE = 30


def _center(room):
    x, y, w, h = room
    return x + w // 2, y + h // 2


def _dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _overlap(a, b):
    """Rooms must keep at least one wall cell between them."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax - 1 <= bx + bw and bx - 1 <= ax + aw
            and ay - 1 <= by + bh and by - 1 <= ay + ah)


def _carve_corridor(g, a, b, rng):
    (x0, y0), (x1, y1) = a, b
    if rng.random() < 0.5:
        for x in range(min(x0, x1), max(x0, x1) + 1):
            g[y0][x] = FLOOR
        for y in range(min(y0, y1), max(y0, y1) + 1):
            g[y][x1] = FLOOR
    else:
        for y in range(min(y0, y1), max(y0, y1) + 1):
            g[y][x0] = FLOOR
        for x in range(min(x0, x1), max(x0, x1) + 1):
            g[y1][x] = FLOOR


def _bfs(g, start):
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in seen and g[ny][nx] != WALL:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def _build(rng, level):
    W = H = SIZE
    g = [[WALL] * W for _ in range(H)]

    # ------------------------------------------------------------- rooms --
    rooms = []
    target = 9 + min(level - 1, 4)
    for _ in range(160):
        if len(rooms) >= target:
            break
        rw, rh = rng.randint(4, 9), rng.randint(4, 8)
        rx = rng.randint(1, W - rw - 2)
        ry = rng.randint(1, H - rh - 2)
        rect = (rx, ry, rw, rh)
        if any(_overlap(rect, other) for other in rooms):
            continue
        rooms.append(rect)
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                g[y][x] = FLOOR
    if len(rooms) < 3:
        return None

    # --------------------------------------------------------- corridors --
    order = rooms[:]
    rng.shuffle(order)
    connected = [order[0]]
    for room in order[1:]:
        base = min(connected, key=lambda c: _dist2(_center(c), _center(room)))
        _carve_corridor(g, _center(base), _center(room), rng)
        connected.append(room)
    for _ in range(rng.randint(2, 4)):            # extra loops, no dead ends
        a, b = rng.sample(rooms, 2)
        _carve_corridor(g, _center(a), _center(b), rng)

    # ----------------------------------------------------------- pillars --
    start_room = rooms[0]
    exit_room = max(rooms[1:],
                    key=lambda r: _dist2(_center(start_room), _center(r)))
    for room in rooms:
        if room is start_room or room is exit_room:
            continue
        x, y, w, h = room
        for _ in range(rng.randint(0, 2)):
            px = rng.randint(x + 1, x + w - 2)
            py = rng.randint(y + 1, y + h - 2)
            if g[py][px] == FLOOR:
                g[py][px] = PILLAR

    # ------------------------------------------------------ start / exit --
    sx, sy = _center(start_room)
    g[sy][sx] = 'P'
    cands = []
    ex, ey, ew, eh = exit_room
    for y in range(ey, ey + eh):
        for x in range(ex, ex + ew):
            if g[y][x] != FLOOR:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < H and g[ny][nx] == WALL:
                    border = nx in (0, W - 1) or ny in (0, H - 1)
                    cands.append((2 if border else 1, nx, ny))
    if not cands:
        return None
    cands.sort(reverse=True)
    best = cands[0][0]
    _, xc, yc = rng.choice([c for c in cands if c[0] == best])
    g[yc][xc] = EXIT

    # --------------------------------------------- reachability validation --
    reach = _bfs(g, (sx, sy))
    for y in range(H):
        for x in range(W):
            if g[y][x] != WALL and (x, y) not in reach:
                return None
    if not any(0 <= xc + dx < W and 0 <= yc + dy < H
               and g[yc + dy][xc + dx] == FLOOR
               and (xc + dx, yc + dy) in reach
               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
        return None

    # ------------------------------------------------------------ spawns --
    free = [c for c in sorted(reach) if g[c[1]][c[0]] == FLOOR]
    used = {(sx, sy)}

    def pick(count, min_dist):
        picked = []
        for md in (min_dist, max(2, min_dist // 2), 0):
            pool = [c for c in free
                    if c not in used
                    and (c[0] - sx) ** 2 + (c[1] - sy) ** 2 >= md * md]
            rng.shuffle(pool)
            for c in pool:
                if len(picked) >= count:
                    break
                picked.append(c)
                used.add(c)
            if len(picked) >= count:
                break
        return picked

    total_npcs = min(6 + 2 * (level - 1), 16)
    boss = (level % 5 == 0)
    if boss:
        # the cyberdemon guards the exit room; fewer regular adds
        bx, by = _center(exit_room)
        g[by][bx] = 'B'
        used.add((bx, by))
        total_npcs = 4 + min(level // 5, 3)
        n_sold = total_npcs // 3
    else:
        n_sold = int(round(total_npcs * min(0.2 + 0.08 * (level - 1), 0.55)))
    for x, y in pick(total_npcs - n_sold, 8):
        g[y][x] = 'I'
    for x, y in pick(n_sold, 9):
        g[y][x] = 'S'
    for x, y in pick(3, 4):
        g[y][x] = 'M'
    for x, y in pick(3, 4):
        g[y][x] = 'A'
    for x, y in pick(2 + min(level - 1, 3) + (2 if boss else 0), 5):
        g[y][x] = 'G'
    for x, y in pick(2 + min(level - 1, 2) + (2 if boss else 0), 4):
        g[y][x] = 'C'
    for x, y in pick(5 + rng.randint(0, 3), 0):
        g[y][x] = 'T'

    return [''.join(row) for row in g]


def generate_level(level=1, seed=None):
    """Return map rows for `level`.  Deterministic for a given (level, seed)."""
    base = seed if seed is not None else random.getrandbits(32)
    for attempt in range(60):
        rows = _build(random.Random(f"{base}:{attempt}"), level)
        if rows is not None:
            return rows
    raise RuntimeError("failed to generate a valid level")
