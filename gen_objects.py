"""Places trees, rocks, bushes and logs, then writes map_objects.py.

Run it from the project folder after changing map_layout.py:  python gen_objects.py
"""
import random

#START FROM AN EMPTY OBJECT LIST, SO OLD OBJECTS DON'T BLOCK THE NEW ONES
open("map_objects.py", "w").write("TREES = []\nROCKS = []\nLOGS = []\nBUSHES = []\n")

import world
import map_layout as L
from pygame import Rect
rng = random.Random(2026)
T = world.TILE

def tiles_of(rect, margin=0):
    r = rect.inflate(margin * 2, margin * 2)
    for row in range(max(0, r.top // T), min(world.ROWS, (r.bottom - 1) // T + 1)):
        for col in range(max(0, r.left // T), min(world.COLS, (r.right - 1) // T + 1)):
            yield row, col

def level_near(row, col, radius=1):
    vals = set()
    for rr in range(row - radius, row + radius + 1):
        for cc in range(col - radius, col + radius + 1):
            if 0 <= rr < world.ROWS and 0 <= cc < world.COLS:
                vals.add(world.height[rr][cc])
                if (rr, cc) in world.face_row:
                    vals.add(-1)
    return vals

reserved = [Rect(L.PLAYER_START[0] - 60, L.PLAYER_START[1] - 60, 160, 160)]
reserved += [Rect(x - 50, y - 50, 140, 130) for x, y in L.WOLF_SPAWNS]
reserved += [b.inflate(60, 40) for b in world.bridges]
reserved += [s.inflate(40, 0).move(0, 30).inflate(0, 60) for s in world.stairs]   # in front of stairs
reserved += [s.move(0, -40).inflate(40, 0) for s in world.stairs]                   # top of stairs
reserved += [p.inflate(60, 50) for p in world.ponds]

placed = []
def ok(rect, margin=10, allow_edge=False):
    if rect.inflate(margin * 2, margin * 2).collidelist(placed) != -1:
        return False
    if rect.collidelist(reserved) != -1:
        return False
    lv = None
    for row, col in tiles_of(rect, 10):
        t = world.terrain[row][col]
        if t not in ("grass",):
            return False
        near = level_near(row, col)
        if len(near) > 1:
            return False
        if lv is None:
            lv = next(iter(near))
    if not allow_edge and (rect.left < 0 or rect.top < 0 or rect.right > 1600 or rect.bottom > 1200):
        return False
    return True

def place(rect, **kw):
    if ok(rect, **kw):
        placed.append(rect); return True
    return False

trees = []
# 1) DENSE FOREST BORDER
for x in range(-20, 1620, 46):
    for y in (-28, 22):
        r = Rect(x + rng.randint(-6, 6) + (23 if y > 0 else 0), y + rng.randint(-4, 4), 40, 50)
        if place(r, margin=2, allow_edge=True): trees.append(r)
    for y in (1112, 1158):
        r = Rect(x + rng.randint(-6, 6) + (23 if y > 1130 else 0), y + rng.randint(-4, 4), 40, 50)
        if place(r, margin=2, allow_edge=True): trees.append(r)
for y in range(60, 1120, 50):
    for x in (-18, 30):
        r = Rect(x + rng.randint(-4, 4), y + rng.randint(-6, 6) + (25 if x > 0 else 0), 40, 50)
        if place(r, margin=2, allow_edge=True): trees.append(r)
    for x in (1532, 1578):
        r = Rect(x + rng.randint(-4, 4), y + rng.randint(-6, 6) + (25 if x < 1560 else 0), 40, 50)
        if place(r, margin=2, allow_edge=True): trees.append(r)
border_count = len(trees)
# 2) WOODLAND CLUSTERS
clusters = [(820, 120, 70), (700, 880, 80), (1160, 720, 60), (420, 1000, 0), (100, 700, 70),
            (1300, 1100, 60), (560, 300, 40), (1340, 300, 60), (860, 400, 50), (200, 200, 60)]
for cx, cy, spread in clusters:
    if spread == 0:
        continue
    for _ in range(150):
        x = int(rng.gauss(cx, spread)); y = int(rng.gauss(cy, spread))
        if place(Rect(x, y, 40, 50), margin=23): trees.append(placed[-1])
        if sum(1 for t in trees if abs(t.x - cx) < 2.5 * spread and abs(t.y - cy) < 2.5 * spread) > 12:
            break
def scatter(n, w, h, margin, tries=8000, region=None):
    out = []
    for _ in range(tries):
        if len(out) >= n: break
        if region:
            x0, y0, x1, y1 = region; r = Rect(rng.randrange(x0, x1), rng.randrange(y0, y1), w, h)
        else:
            r = Rect(rng.randrange(80, 1500), rng.randrange(80, 1080), w, h)
        if place(r, margin=margin): out.append(r)
    return out

# objects on high ground (rewards for climbing)
bushes = scatter(1, 35, 30, 30, region=(500, 200, 660, 280))          # lookout
rocks = scatter(2, 35, 30, 30, region=(1220, 200, 1460, 420))         # eastern cliffs
rocks += scatter(1, 35, 30, 30, region=(180, 830, 440, 980))          # south-west ridge
bushes += scatter(1, 35, 30, 30, region=(1240, 780, 1440, 900))       # mesa
rocks += scatter(15, 35, 30, 30)
bushes += scatter(13, 35, 30, 30)
logs = scatter(6, 80, 22, 20)

# 3) A FEW SCATTERED TREES
for _ in range(4000):
    if len(trees) > border_count + 95:
        break
    r = Rect(rng.randrange(60, 1500), rng.randrange(60, 1080), 40, 50)
    if place(r, margin=23): trees.append(r)

def out(name, rects):
    lines = [f"    ({r.x}, {r.y})," for r in rects]
    return f"{name} = [\n" + "\n".join(lines) + "\n]\n"
open('map_objects.py', 'w').write(
    "\n#GENERATED BY gen_objects.py: POSITIONS (TOP-LEFT x, y) OF EVERY TREE, ROCK, BUSH AND LOG.\n"
    "#YOU CAN EDIT, ADD OR REMOVE LINES BY HAND.\n\n"
    + out("TREES", trees) + "\n" + out("ROCKS", rocks) + "\n" + out("BUSHES", bushes) + "\n" + out("LOGS", logs))
print("trees", len(trees), "(border", border_count, ") rocks", len(rocks), "bushes", len(bushes), "logs", len(logs))
