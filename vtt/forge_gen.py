"""Map Forge data: terrain grid, objects, chunks (prefabs) and procedural generators. No Qt, so it is easy to test."""
import random
from collections import deque

VOID, FLOOR, CAVE, WATER, LAVA, GRASS, DIRT, WOOD, PIT, SAND = range(10)
TERRAIN = {FLOOR: "Stone floor", WOOD: "Wooden floor", CAVE: "Cave floor", GRASS: "Grass", DIRT: "Dirt path", SAND: "Sand",
           WATER: "Water", LAVA: "Lava", PIT: "Chasm", VOID: "Rock / wall"}
LIQUID = {WATER, LAVA, PIT}
OBJECTS = {"door": "Door", "chest": "Chest", "pillar": "Pillar", "statue": "Statue", "altar": "Altar", "throne": "Throne",
           "barrel": "Barrel", "crate": "Crate", "table": "Table", "bed": "Bed", "bookshelf": "Bookshelf",
           "stairs_up": "Stairs up", "stairs_down": "Stairs down", "torch": "Torch", "trap": "Trap (DM only)",
           "bones": "Bones", "rubble": "Rubble", "grave": "Gravestone", "well": "Well", "campfire": "Campfire",
           "tree": "Tree", "bush": "Bush", "rock": "Boulder", "mushrooms": "Mushrooms"}
N4 = ((0, -1), (1, 0), (0, 1), (-1, 0))
N8 = N4 + ((1, -1), (1, 1), (-1, 1), (-1, -1))

# chunk legend: ' ' leaves the map untouched, '#' carves rock/wall
TCHAR = {"#": VOID, ".": FLOOR, ",": CAVE, "~": WATER, "^": LAVA, '"': GRASS, ":": DIRT, "_": WOOD, "o": PIT, "s": SAND}
OCHAR = {"D": ("door", FLOOR), "C": ("chest", FLOOR), "P": ("pillar", FLOOR), "S": ("statue", FLOOR), "A": ("altar", FLOOR),
         "H": ("throne", FLOOR), "B": ("barrel", FLOOR), "X": ("crate", FLOOR), "T": ("table", FLOOR), "Y": ("table", WOOD),
         "Z": ("bed", WOOD), "L": ("bookshelf", WOOD), "<": ("stairs_up", FLOOR), ">": ("stairs_down", FLOOR),
         "f": ("torch", FLOOR), "!": ("trap", FLOOR), "x": ("bones", FLOOR), "r": ("rubble", FLOOR), "G": ("grave", GRASS),
         "W": ("well", FLOOR), "F": ("campfire", DIRT), "t": ("tree", GRASS), "b": ("bush", GRASS), "R": ("rock", GRASS),
         "m": ("mushrooms", CAVE), "K": ("rock", CAVE)}


def parse(rows):
    w = max(len(r) for r in rows)
    out = []
    for row in rows:
        line = []
        for ch in row.ljust(w):
            if ch == " ":
                line.append(None)
            elif ch in OCHAR:
                o, t = OCHAR[ch]
                line.append((t, o))
            else:
                line.append((TCHAR[ch], ""))
        out.append(line)
    return out


def chunk(cat, name, rows):
    g = parse(rows)
    return dict(cat=cat, name=name, g=g, builtin=True)


BUILTIN = [
    chunk("Rooms", "Pillared hall", [".........", ".P..P..P.", ".........", ".........", ".........", ".P..P..P.", "........."]),
    chunk("Rooms", "Round chamber", ["  .....  ", " ....... ", ".........", ".........", "....S....", ".........", ".........",
                                     " ....... ", "  .....  "]),
    chunk("Rooms", "Shrine", [".......", ".S.A.S.", ".......", ".......", ".f...f.", ".......", "......."]),
    chunk("Rooms", "Throne room", ["....H....", ".S.....S.", ".........", ".P.....P.", ".........", ".P.....P.", ".........",
                                   ".P.....P.", ".........", ".f.....f.", "........."]),
    chunk("Rooms", "Treasure vault", ["C.C.C", ".....", "C...C", ".....", "..!.."]),
    chunk("Rooms", "Storeroom", ["BBX.XB", "B.....", "......", "X....X", "XB..BB"]),
    chunk("Rooms", "Prison cells", ["x#.#x#.#x", ".#.#.#.#.", "D#D#D#D#D", ".........", "f.......f"]),
    chunk("Rooms", "Library", ["LLLL_LLLL", "_________", "_LL___LL_", "_________", "_LL_Y_LL_", "_________", "_________"]),
    chunk("Rooms", "Barracks", ["Z_Z_Z_Z_", "________", "________", "________", "Z_Z_Z_Z_", "_Y____Y_"]),
    chunk("Rooms", "Flooded room", [".......", "..~~~..", ".~~~~~.", ".~~~~~.", ".~~~~~.", "..~~~..", "......."]),
    chunk("Rooms", "Crypt", ["x.....x", ".S...S.", ".......", "...A...", ".......", ".S...S.", "x.....x"]),
    chunk("Hazards", "Lava bridge", ["^^^^^^^^^", "^^^^^^^^^", ".........", "^^^^^^^^^", "^^^^^^^^^"]),
    chunk("Hazards", "Chasm crossing", ["ooooooooo", "ooooooooo", "_________", "ooooooooo", "ooooooooo"]),
    chunk("Corridors", "Cross junction", ["  .  ", "  .  ", ".....", "  .  ", "  .  "]),
    chunk("Corridors", "Corridor bend", ["...", "  .", "  ."]),
    chunk("Corridors", "T junction", [".....", "  .  ", "  .  "]),
    chunk("Corridors", "Stairwell", ["...", ".>.", "..."]),
    chunk("Caves", "Cave pocket", ["  ,,,  ", " ,,,,,,", ",,,m,,,", ",,,,,,K", " ,,,,, ", "  ,,   "]),
    chunk("Caves", "Underground lake", ["  ,,,,,  ", " ,,~~~,, ", ",,~~~~~,,", ",,~~~~~,,", " ,,~~~,m ", "  ,,,,,  "]),
    chunk("Outdoors", "Forest clearing", ["tt\"\"\"\"\"tt", "t\"\"\"\"\"\"\"t", "\"\"\"\"\"\"\"\"\"", "\"\"\":F:\"\"\"",
                                         "\"\"\"::b\"\"\"", "\"\"\"\"\"\"\"\"\"", "t\"\"\"\"\"\"\"t", "tt\"\"\"\"\"tt"]),
    chunk("Outdoors", "Ruined tower", [" ##### ", "##...##", "#..r..#", "#.....:", "#..x..#", "##...##", " ##### "]),
    chunk("Outdoors", "Graveyard", ["\"G\"G\"G\"", "\"\"\"\"\"\"\"", "\"G\"G\"G\"", "\"\"\"S\"\"\"", "\"G\"G\"G\""]),
    chunk("Outdoors", "Village well", ["\":::::\"", ":.....:", ":..W..:", ":.....:", "\":::::\""]),
]


def rotate(g):
    h, w = len(g), len(g[0])
    return [[g[h - 1 - j][i] for j in range(h)] for i in range(w)]


def flip(g):
    return [row[::-1] for row in g]


class MapData:
    def __init__(self, w=40, h=30, fill=VOID, seed=None):
        self.w, self.h = w, h
        self.t = [[fill] * w for _ in range(h)]
        self.o = [[""] * w for _ in range(h)]
        self.seed = random.randrange(1 << 30) if seed is None else seed

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x, y):
        return self.t[y][x] if self.inside(x, y) else VOID

    def obj(self, x, y):
        return self.o[y][x] if self.inside(x, y) else ""

    def copy(self):
        m = MapData(self.w, self.h, seed=self.seed)
        m.t, m.o = [r[:] for r in self.t], [r[:] for r in self.o]
        return m

    def to_dict(self):
        return dict(w=self.w, h=self.h, seed=self.seed, t=self.t, o=self.o)

    @staticmethod
    def from_dict(d):
        m = MapData(d["w"], d["h"], seed=d.get("seed", 1))
        m.t, m.o = d["t"], d["o"]
        return m

    def stamp(self, g, x0, y0):
        for dy, row in enumerate(g):
            for dx, cell in enumerate(row):
                if cell is not None and self.inside(x0 + dx, y0 + dy):
                    self.t[y0 + dy][x0 + dx], self.o[y0 + dy][x0 + dx] = cell

    def grab(self, x0, y0, x1, y1):
        return [[(self.t[y][x], self.o[y][x]) for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]

    def paste(self, other, x0, y0):
        self.stamp(other.grab(0, 0, other.w - 1, other.h - 1), x0, y0)

    def flood(self, x, y, passable):
        """Cells reachable from (x, y) through cells where passable(x, y) is true, with distances."""
        dist = {(x, y): 0}
        q = deque([(x, y)])
        while q:
            cx, cy = q.popleft()
            for dx, dy in N4:
                n = (cx + dx, cy + dy)
                if n not in dist and self.inside(*n) and passable(*n):
                    dist[n] = dist[(cx, cy)] + 1
                    q.append(n)
        return dist


def value_noise(w, h, rng, scale):
    gw, gh = w // scale + 2, h // scale + 2
    g = [[rng.random() for _ in range(gw)] for _ in range(gh)]
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            fx, fy = x / scale, y / scale
            x0, y0 = int(fx), int(fy)
            sx, sy = (fx - x0) ** 2 * (3 - 2 * (fx - x0)), (fy - y0) ** 2 * (3 - 2 * (fy - y0))
            a = g[y0][x0] + (g[y0][x0 + 1] - g[y0][x0]) * sx
            b = g[y0 + 1][x0] + (g[y0 + 1][x0 + 1] - g[y0 + 1][x0]) * sx
            row.append(a + (b - a) * sy)
        out.append(row)
    return out


def free_spot(m, x, y):
    """Nearest open, object-free floor cell to (x, y)."""
    best = None
    for yy in range(m.h):
        for xx in range(m.w):
            if m.t[yy][xx] not in LIQUID | {VOID} and not m.o[yy][xx]:
                d = abs(xx - x) + abs(yy - y)
                if best is None or d < best[0]:
                    best = (d, xx, yy)
    return best[1:] if best else (x, y)


def doorway(m, x, y):
    wall = lambda a, b: m.get(a, b) == VOID
    return (wall(x - 1, y) and wall(x + 1, y) and not wall(x, y - 1) and not wall(x, y + 1)) or \
           (wall(x, y - 1) and wall(x, y + 1) and not wall(x - 1, y) and not wall(x + 1, y))


def add_stairs(m, rng):
    walk = lambda x, y: m.t[y][x] not in (VOID, LAVA, PIT)
    open_cells = [(x, y) for y in range(m.h) for x in range(m.w) if walk(x, y) and m.t[y][x] != WATER]
    if not open_cells:
        return
    sx, sy = free_spot(m, *rng.choice(open_cells))
    dist = m.flood(sx, sy, walk)
    far = max((c for c in dist if not m.o[c[1]][c[0]] and m.t[c[1]][c[0]] != WATER), key=dist.get, default=None)
    m.o[sy][sx] = "stairs_up"
    if far and far != (sx, sy):
        m.o[far[1]][far[0]] = "stairs_down"


def gen_dungeon(w=40, h=30, seed=None, rooms=9, min_room=4, max_room=9, loops=0.25, wide=1, deco=0.5, prefabs=0.35):
    rng = random.Random(seed)
    m = MapData(w, h, seed=seed)
    placed = []
    max_room = max(min_room, max_room)
    pool = [c["g"] for c in BUILTIN if c["cat"] == "Rooms"]
    for _ in range(rooms * 50):
        if len(placed) >= rooms:
            break
        g = None
        if rng.random() < prefabs:
            g = rng.choice(pool)
            for _ in range(rng.randrange(4)):
                g = rotate(g)
            rw, rh = len(g[0]), len(g)
        else:
            rw, rh = rng.randint(min_room, max_room), rng.randint(min_room, max_room)
        if rw > w - 2 or rh > h - 2:
            continue
        x, y = rng.randint(1, w - rw - 1), rng.randint(1, h - rh - 1)
        if any(x < px + pw + 2 and px < x + rw + 2 and y < py + ph + 2 and py < y + rh + 2 for px, py, pw, ph, _ in placed):
            continue
        placed.append((x, y, rw, rh, g))
    for x, y, rw, rh, g in placed:
        if g:
            m.stamp(g, x, y)
        else:
            for yy in range(y, y + rh):
                for xx in range(x, x + rw):
                    m.t[yy][xx] = FLOOR
    centers = [(x + rw // 2, y + rh // 2) for x, y, rw, rh, _ in placed]
    n = len(centers)
    dist = lambda i, j: abs(centers[i][0] - centers[j][0]) + abs(centers[i][1] - centers[j][1])
    edges, linked = set(), {0} if n else set()
    while len(linked) < n:  # minimum spanning tree: every room reachable
        i, j = min(((i, j) for i in linked for j in range(n) if j not in linked), key=lambda e: dist(*e))
        edges.add((i, j))
        linked.add(j)
    for i in range(n):  # a few extra loops so the dungeon isn't a pure tree
        near = sorted((j for j in range(n) if j != i), key=lambda j: dist(i, j))[:3]
        if near and rng.random() < loops:
            edges.add((i, rng.choice(near)))
    in_room = lambda xx, yy: any(x <= xx < x + rw and y <= yy < y + rh for x, y, rw, rh, _ in placed)
    for i, j in edges:
        (x1, y1), (x2, y2) = centers[i], centers[j]
        path = []
        if rng.random() < 0.5:
            path += [(x, y1) for x in range(min(x1, x2), max(x1, x2) + 1)] + [(x2, y) for y in range(min(y1, y2), max(y1, y2) + 1)]
        else:
            path += [(x1, y) for y in range(min(y1, y2), max(y1, y2) + 1)] + [(x, y2) for x in range(min(x1, x2), max(x1, x2) + 1)]
        for cx, cy in path:
            for k in range(wide):
                for xx, yy in ((cx + k, cy), (cx, cy + k)):
                    if 0 < xx < w - 1 and 0 < yy < h - 1 and m.t[yy][xx] == VOID:
                        m.t[yy][xx] = FLOOR
    for x, y, rw, rh, g in placed:  # doors where corridors enter plain rooms
        if g:
            continue
        ring = [(xx, y - 1) for xx in range(x, x + rw)] + [(xx, y + rh) for xx in range(x, x + rw)] + \
               [(x - 1, yy) for yy in range(y, y + rh)] + [(x + rw, yy) for yy in range(y, y + rh)]
        for xx, yy in ring:
            if m.get(xx, yy) == FLOOR and doorway(m, xx, yy) and rng.random() < 0.75:
                m.o[yy][xx] = "door"
        decorate(m, x, y, rw, rh, rng, deco)
    for yy in range(h):
        for xx in range(w):
            if m.t[yy][xx] == FLOOR and not m.o[yy][xx] and not in_room(xx, yy) and not doorway(m, xx, yy):
                r = rng.random()
                if r < 0.03 * deco:
                    m.o[yy][xx] = "trap"
                elif r < 0.05 * deco:
                    m.o[yy][xx] = rng.choice(["rubble", "bones"])
    add_stairs(m, rng)
    return m


def decorate(m, x, y, rw, rh, rng, deco):
    """Gives a plain room a theme without blocking its entrances."""
    def ok(xx, yy):
        if m.o[yy][xx] or m.t[yy][xx] != FLOOR:
            return False
        return not any((nx < x or nx >= x + rw or ny < y or ny >= y + rh) and m.get(nx, ny) != VOID
                       for nx, ny in ((xx + dx, yy + dy) for dx, dy in N4))  # next to an entrance

    cells = [(xx, yy) for yy in range(y, y + rh) for xx in range(x, x + rw)]
    edge = [(xx, yy) for xx, yy in cells if xx in (x, x + rw - 1) or yy in (y, y + rh - 1)]
    theme = rng.choices(["empty", "storage", "pillars", "crypt", "treasure", "camp", "library"], [3, 2, 2, 1, 1, 1, 1])[0]
    put = lambda c, o: ok(*c) and m.o[c[1]].__setitem__(c[0], o)
    if theme == "storage":
        for c in edge:
            if rng.random() < 0.35 * (deco + 0.5):
                put(c, rng.choice(["barrel", "crate"]))
    elif theme == "pillars" and rw >= 6 and rh >= 6:
        for xx in range(x + 1, x + rw - 1, 3):
            for yy in (y + 1, y + rh - 2):
                put((xx, yy), "pillar")
    elif theme == "crypt":
        put((x + rw // 2, y + rh // 2), "statue")
        for c in cells:
            if rng.random() < 0.08:
                put(c, "bones")
    elif theme == "treasure":
        c = rng.choice(edge)
        put(c, "chest")
    elif theme == "camp":
        put((x + rw // 2, y + rh // 2), "campfire")
        for c in edge:
            if rng.random() < 0.15:
                put(c, "bed")
    elif theme == "library":
        for xx in range(x, x + rw):
            put((xx, y), "bookshelf")
        put((x + rw // 2, y + rh // 2), "table")
    for c in edge:  # torches along the walls
        if rng.random() < 0.06 * (deco + 0.5) and any(m.get(c[0] + dx, c[1] + dy) == VOID for dx, dy in N4):
            put(c, "torch")
    for c in cells:
        if rng.random() < 0.02 * deco:
            put(c, rng.choice(["rubble", "bones"]))


def gen_caves(w=40, h=30, seed=None, fill=0.46, smooth=5, lakes=0.3, lava=False, deco=0.5):
    rng = random.Random(seed)
    wall = [[x in (0, w - 1) or y in (0, h - 1) or rng.random() < fill for x in range(w)] for y in range(h)]
    for _ in range(smooth):  # cellular automaton: rock grows where rock is common
        wall = [[x in (0, w - 1) or y in (0, h - 1) or
                 sum(not (0 <= x + dx < w and 0 <= y + dy < h) or wall[y + dy][x + dx]
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1)) >= 5 for x in range(w)] for y in range(h)]
    m = MapData(w, h, seed=seed)
    seen, best = set(), set()
    for y in range(h):
        for x in range(w):
            if not wall[y][x] and (x, y) not in seen:
                region = set(m.flood(x, y, lambda a, b: not wall[b][a]))
                seen |= region
                if len(region) > len(best):
                    best = region
    for x, y in best:  # keep only the biggest connected cave
        m.t[y][x] = CAVE
    noise = value_noise(w, h, rng, 6)
    for x, y in best:
        if noise[y][x] > 1 - lakes * 0.45 and all(m.get(x + dx, y + dy) != VOID for dx, dy in N8):
            m.t[y][x] = LAVA if lava else WATER
    for x, y in best:
        if m.t[y][x] == CAVE:
            r = rng.random()
            m.o[y][x] = "mushrooms" if r < 0.025 * deco else "rock" if r < 0.05 * deco else "bones" if r < 0.06 * deco else ""
    add_stairs(m, rng)
    return m


def gen_wilds(w=40, h=30, seed=None, forest=0.5, river=True, road=True, deco=0.5):
    rng = random.Random(seed)
    m = MapData(w, h, fill=GRASS, seed=seed)
    big, small = value_noise(w, h, rng, 7), value_noise(w, h, rng, 3)
    for y in range(h):
        for x in range(w):
            if big[y][x] > 1 - forest * 0.8 and small[y][x] > 0.3 and rng.random() < 0.75:
                m.o[y][x] = "tree"
            elif rng.random() < 0.03 * deco:
                m.o[y][x] = "bush"
            elif rng.random() < 0.012 * deco:
                m.o[y][x] = "rock"
    if river:
        x, width = rng.randint(w // 4, 3 * w // 4), rng.choice([2, 3])
        for y in range(h):
            for k in range(-1, width + 1):
                xx = x + k
                if 0 <= xx < w:
                    if 0 <= k < width:
                        m.t[y][xx], m.o[y][xx] = WATER, ""
                    elif rng.random() < 0.6:
                        m.t[y][xx], m.o[y][xx] = SAND, ""
            x = max(1, min(w - width - 1, x + rng.choice([-1, 0, 0, 1])))
    if road:
        y = rng.randint(h // 4, 3 * h // 4)
        for x in range(w):
            for yy in (y, y + 1):
                if 0 <= yy < h:
                    m.t[yy][x] = WOOD if m.t[yy][x] == WATER else DIRT  # a wooden bridge where the road meets the river
                    m.o[yy][x] = ""
            y = max(1, min(h - 3, y + rng.choice([-1, 0, 0, 0, 1])))
    camp = next(c["g"] for c in BUILTIN if c["name"] == "Forest clearing")
    for _ in range(30):
        x, y = rng.randint(0, w - len(camp[0])), rng.randint(0, h - len(camp))
        if all(m.t[yy][xx] == GRASS for yy in range(y, y + len(camp)) for xx in range(x, x + len(camp[0]))):
            m.stamp(camp, x, y)
            break
    return m


GENERATORS = {"Dungeon": gen_dungeon, "Caves": gen_caves, "Wilderness": gen_wilds}
