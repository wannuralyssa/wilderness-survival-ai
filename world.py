
import math
import random
import pygame
import tent_art
import fire_art
from config import *
import map_layout as layout
import map_objects as objects
import game_clock

CELL_SIZE = 40          #GRID SIZE USED BY A* PATHFINDING
TILE = 20               #FINER GRID USED FOR CLIFF SHAPES, RIVER AND TERRAIN
COLS = WORLD_WIDTH // TILE
ROWS = WORLD_HEIGHT // TILE

PLAYER_START = layout.PLAYER_START

#HOW LONG UNTIL A HARVESTED TREE OR ROCK CAN BE HARVESTED AGAIN (MILLISECONDS)
TREE_REGROW_TIME = 90000
ROCK_REGROW_TIME = 120000
BUSH_REGROW_TIME = 60000
BUSH_SERVINGS = 3           #A BUSH CAN BE EATEN FROM 3 TIMES, THEN IT NEEDS TO GROW BACK
REGROW_MULTIPLIER = 1.0     #difficulty.py MAKES REGROWING SLOWER ON LATER DAYS


#================================================================
# OBJECTS
#================================================================
trees = [pygame.Rect(x, y, 40, 50) for x, y in objects.TREES]
rocks = [pygame.Rect(x, y, 35, 30) for x, y in objects.ROCKS]
logs = [pygame.Rect(x, y, 80, 22) for x, y in objects.LOGS]
berry_bushes = [pygame.Rect(x, y, 35, 30) for x, y in objects.BUSHES]
ponds = [pygame.Rect(*p) for p in layout.PONDS]

#HARVESTED TREES AND ROCKS: {INDEX: TIME WHEN IT GROWS BACK}
collected_trees = {}
collected_rocks = {}
collected_bushes = {}       #EMPTY BUSHES: {INDEX: TIME WHEN BERRIES GROW BACK}
bush_servings = {}          #BERRIES LEFT ON A BUSH (MISSING = FULL)
wood = 0
stone = 0

#BUILT BY THE PLAYER
campfires = []
campfire_lit = []       #TRUE/FALSE FOR EACH CAMPFIRE (RAIN PUTS THEM OUT)
campfire_blockers = []  #THE PART OF EACH CAMPFIRE YOU CAN'T WALK THROUGH
tents = []


#================================================================
# HEIGHT GRID (WHICH LEVEL EACH 20 x 20 TILE IS ON)
#================================================================
def _inside_polygon(x, y, polygon):
    #RAY CASTING: COUNT HOW MANY EDGES A LINE TO THE RIGHT CROSSES
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            cross_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < cross_x:
                inside = not inside
    return inside


height = [[0] * COLS for _ in range(ROWS)]
for _plateau in layout.PLATEAUS:
    for _r in range(ROWS):
        for _c in range(COLS):
            if _inside_polygon(_c * TILE + TILE / 2, _r * TILE + TILE / 2, _plateau["polygon"]):
                height[_r][_c] = max(height[_r][_c], _plateau["level"])

STAIRS_WIDTH = 80
CLIFF_HEIGHT = 40       #CLIFF FACES ARE 2 TILES TALL
EDGE_THICKNESS = 6      #INVISIBLE WALL ALONG THE NORTH, WEST AND EAST EDGES

stairs = [pygame.Rect(x, y, STAIRS_WIDTH, CLIFF_HEIGHT)
          for _plateau in layout.PLATEAUS for x, y in _plateau["stairs"]]


def _in_stairs(r, c):
    return any(s.collidepoint(c * TILE + 1, r * TILE + 1) for s in stairs)


#CLIFF FACE TILES: THE 2 TILES BELOW ANY PLACE WHERE THE GROUND DROPS
#face_row[(r, c)] = 0 FOR THE UPPER HALF OF THE CLIFF, 1 FOR THE LOWER HALF
face_row = {}
for _r in range(1, ROWS):
    for _c in range(COLS):
        if height[_r - 1][_c] > height[_r][_c]:
            for _k in range(2):
                if _r + _k < ROWS and not _in_stairs(_r + _k, _c):
                    face_row[(_r + _k, _c)] = _k


def _merge_cells(cells):
    #JOIN NEIGHBOURING TILES IN A ROW INTO ONE RECT (FEWER RECTS = FASTER COLLISIONS)
    rects = []
    by_row = {}
    for r, c in cells:
        by_row.setdefault(r, []).append(c)
    for r, cols in by_row.items():
        cols.sort()
        start = prev = cols[0]
        for c in cols[1:] + [None]:
            if c is not None and c == prev + 1:
                prev = c
                continue
            rects.append(pygame.Rect(start * TILE, r * TILE, (prev - start + 1) * TILE, TILE))
            if c is not None:
                start = prev = c
    return rects


cliff_faces = _merge_cells(face_row.keys())

#THIN WALLS ON TOP TILES WHERE THE NEIGHBOUR TO THE NORTH, WEST OR EAST IS LOWER
plateau_walls = []
for _r in range(ROWS):
    for _c in range(COLS):
        _h = height[_r][_c]
        if _h == 0:
            continue
        _x, _y = _c * TILE, _r * TILE
        if _r > 0 and height[_r - 1][_c] < _h:
            plateau_walls.append(pygame.Rect(_x, _y, TILE, EDGE_THICKNESS))
        if _c > 0 and height[_r][_c - 1] < _h:
            plateau_walls.append(pygame.Rect(_x, _y, EDGE_THICKNESS, TILE))
        if _c < COLS - 1 and height[_r][_c + 1] < _h:
            plateau_walls.append(pygame.Rect(_x + TILE - EDGE_THICKNESS, _y, EDGE_THICKNESS, TILE))


def height_at(x, y):
    #HOW HIGH THE GROUND IS AT A POINT (0 = LOWEST)
    r, c = int(y) // TILE, int(x) // TILE
    if 0 <= r < ROWS and 0 <= c < COLS:
        return height[r][c]
    return 0


#================================================================
# RIVER, BRIDGES AND PATHS
#================================================================
def _smooth_curve(points, step=6):
    #CATMULL-ROM SPLINE: A SMOOTH CURVE THROUGH ALL THE POINTS
    result = []
    pts = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        n = max(1, int(length / step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            result.append((x, y))
    result.append(points[-1])
    return result


river_curve = _smooth_curve(layout.RIVER_POINTS)
RIVER_HALF = layout.RIVER_WIDTH / 2
SAND_WIDTH = 16


def river_x_at(y):
    #X POSITION OF THE MIDDLE OF THE RIVER AT HEIGHT y
    for (x1, y1), (x2, y2) in zip(river_curve, river_curve[1:]):
        if y1 <= y <= y2 and y2 != y1:
            return x1 + (x2 - x1) * (y - y1) / (y2 - y1)
    return river_curve[-1][0]


def _distance_to_curve(x, y, curve, near=None):
    best = 1e9
    for (x1, y1), (x2, y2) in zip(curve, curve[1:]):
        if near is not None and (min(abs(y1 - y), abs(y2 - y)) > near or min(abs(x1 - x), abs(x2 - x)) > near):
            continue
        dx, dy = x2 - x1, y2 - y1
        length2 = dx * dx + dy * dy
        t = 0 if length2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / length2))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


bridges = []
for _y in layout.BRIDGES_Y:
    _cx = river_x_at(_y)
    _left = int(round((_cx - 70) / TILE)) * TILE
    bridges.append(pygame.Rect(_left, _y - 40, 140, 80))

path_curves = [_smooth_curve(p, step=8) for p in layout.PATHS]
PATH_HALF = layout.PATH_WIDTH / 2

#TERRAIN OF EACH TILE: "grass", "path", "sand", "mud", "tall_grass", "stairs" OR "water"
terrain = [["grass"] * COLS for _ in range(ROWS)]


def _in_blob(x, y, rect):
    #MUD AND TALL GRASS ARE OVALS THAT FIT INSIDE THEIR RECT
    rx, ry, rw, rh = rect
    if rw <= 0 or rh <= 0:
        return False
    nx = (x - (rx + rw / 2)) / (rw / 2)
    ny = (y - (ry + rh / 2)) / (rh / 2)
    return nx * nx + ny * ny <= 1


for _r in range(ROWS):
    for _c in range(COLS):
        _x, _y = _c * TILE + TILE / 2, _r * TILE + TILE / 2
        _t = "grass"
        if height[_r][_c] == 0 and (_r, _c) not in face_row:
            if any(_distance_to_curve(_x, _y, curve, 60) <= PATH_HALF for curve in path_curves):
                _t = "path"
            _d = _distance_to_curve(_x, _y, river_curve, 120)
            if _d <= RIVER_HALF - 4:
                _t = "water"
            elif _d <= RIVER_HALF + SAND_WIDTH:
                _t = "sand"
        if any(_in_blob(_x, _y, m) for m in layout.MUD):
            _t = "mud"
        elif any(_in_blob(_x, _y, g) for g in layout.TALL_GRASS):
            _t = "tall_grass"
        if _in_stairs(_r, _c):
            _t = "stairs"
        if _t == "water" and any(b.collidepoint(_x, _y) for b in bridges):
            _t = "bridge"
        terrain[_r][_c] = _t

water_tiles = [(_r, _c) for _r in range(ROWS) for _c in range(COLS) if terrain[_r][_c] == "water"]
river_blocks = _merge_cells(water_tiles)

#MOVEMENT COST (USED BY A* SEARCH) AND SPEED MULTIPLIER FOR EACH TERRAIN
TERRAIN_COST = {
    "grass": 1,
    "path": 1,
    "sand": 1,
    "bridge": 1,
    "tall_grass": 2,
    "stairs": 3,
    "mud": 4,
    "water": 1
}

TERRAIN_SPEED = {
    "grass": 1.0,
    "path": 1.15,       #PATHS ARE A LITTLE FASTER
    "sand": 0.9,
    "bridge": 1.0,
    "tall_grass": 0.7,
    "stairs": 0.6,
    "mud": 0.45,
    "water": 1.0
}

#EVERYTHING THAT BLOCKS MOVEMENT
#TREES, ROCKS AND LOGS ONLY BLOCK AT THEIR BASE (TRUNK / BOTTOM OF THE STONE),
#SO IT IS EASY TO WALK BETWEEN THEM. THE FULL RECTS ARE STILL USED FOR DRAWING AND "E".
tree_blockers = [pygame.Rect(t.x + 10, t.bottom - 16, 20, 14) for t in trees]
rock_blockers = [pygame.Rect(r.x + 3, r.bottom - 16, 29, 14) for r in rocks]
log_blockers = [pygame.Rect(l.x + 4, l.bottom - 14, 72, 12) for l in logs]

obstacles = (
    tree_blockers + rock_blockers + log_blockers + ponds + river_blocks
    + plateau_walls + cliff_faces
)


def terrain_at(x, y):
    r, c = int(y) // TILE, int(x) // TILE
    if 0 <= r < ROWS and 0 <= c < COLS:
        return terrain[r][c]
    return "grass"


def speed_multiplier(rect):
    #CHECK THE GROUND UNDER THE CHARACTER'S FEET
    return TERRAIN_SPEED[terrain_at(rect.centerx, rect.bottom - 4)]


def cell_cost(x, y):
    return TERRAIN_COST[terrain_at(x, y)]


def near_water(rect):
    #CAN THE PLAYER DRINK HERE? (NEXT TO A POND OR THE RIVER)
    if any(rect.colliderect(p.inflate(40, 40)) for p in ponds):
        return True
    area = rect.inflate(30, 30)
    for r in range(area.top // TILE, area.bottom // TILE + 1):
        for c in range(area.left // TILE, area.right // TILE + 1):
            if 0 <= r < ROWS and 0 <= c < COLS and terrain[r][c] == "water":
                return True
    return False


_cost_grid = None


def get_cost_grid():
    #BUILD THE A* COST GRID ONCE (THE MAP DOES NOT CHANGE)
    global _cost_grid
    if _cost_grid is None:
        import search
        _cost_grid = search.create_cost_grid(
            WORLD_WIDTH, WORLD_HEIGHT, CELL_SIZE, obstacles, cell_cost
        )
    return _cost_grid


#================================================================
# RESOURCES AND CAMPFIRES
#================================================================
def collect_tree(index):
    collected_trees[index] = game_clock.now() + TREE_REGROW_TIME * REGROW_MULTIPLIER


def collect_rock(index):
    collected_rocks[index] = game_clock.now() + ROCK_REGROW_TIME * REGROW_MULTIPLIER


def eat_from_bush(index):
    #RETURNS TRUE IF THE BUSH HAD BERRIES
    if index in collected_bushes:
        return False
    bush_servings[index] = bush_servings.get(index, BUSH_SERVINGS) - 1
    if bush_servings[index] <= 0:
        del bush_servings[index]
        collected_bushes[index] = game_clock.now() + BUSH_REGROW_TIME * REGROW_MULTIPLIER
    return True


def update(now):
    #REGROW TREES, ROCKS AND BERRY BUSHES WHOSE TIME HAS COME
    for collected in (collected_trees, collected_rocks, collected_bushes):
        for index in [i for i, t in collected.items() if now >= t]:
            del collected[index]


def campfire_blocker(rect):
    #THE STONE RING BLOCKS WALKING (NOBODY WALKS THROUGH A FIRE)
    return pygame.Rect(rect.x + 1, rect.bottom - 14, rect.width - 2, 12)


def add_campfire(rect):
    campfires.append(rect)
    campfire_lit.append(True)
    blocker = campfire_blocker(rect)
    campfire_blockers.append(blocker)
    obstacles.append(blocker)
    #A* (WOLVES AND THE AI) GOES AROUND THE FIRE TOO
    grid = get_cost_grid()
    r, c = blocker.centery // CELL_SIZE, blocker.centerx // CELL_SIZE
    if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
        grid[r][c] = None


def lit_campfires():
    return [fire for fire, lit in zip(campfires, campfire_lit) if lit]


def extinguish_campfires():
    #RAIN PUTS OUT EVERY BURNING CAMPFIRE. RETURNS HOW MANY WENT OUT
    count = sum(campfire_lit)
    for i in range(len(campfire_lit)):
        campfire_lit[i] = False
    return count


#================================================================
# IMAGES
#================================================================
scaled_water = None
scaled_trees = []
depleted_trees = []
scaled_rock = None
depleted_rock = None
scaled_bush = None
empty_bush = None
log_image = None
tent_image = None
occupied_tent = None        #THE TENT THE PLAYER IS RESTING IN (DRAWN BY renderer.py INSTEAD)
harvest_shake = None        #("tree" OR "rock", INDEX, X OFFSET) WHILE IT IS BEING CHOPPED / MINED
campfire_frames = []
campfire_out_image = None
ground_surface = None


def _darker(image, color):
    darker = image.copy()
    darker.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return darker


def load_world_assets():
    global scaled_water, scaled_trees, depleted_trees, scaled_rock, depleted_rock
    global scaled_bush, empty_bush, log_image, tent_image, campfire_frames, campfire_out_image

    def load(name):
        return pygame.image.load(f"assets/environment/{name}").convert_alpha()

    scaled_water = pygame.transform.smoothscale(load("pond.png"), (130, 95))
    scaled_trees = [
        pygame.transform.smoothscale(load("oak_tree.png"), (80, 90)),
        pygame.transform.smoothscale(load("pine_tree.png"), (80, 90))
    ]
    #HARVESTED TREES LOOK DULL UNTIL THEY GROW BACK
    depleted_trees = [_darker(tree, (150, 140, 120)) for tree in scaled_trees]
    scaled_rock = pygame.transform.smoothscale(load("rock.png"), (55, 45))
    #MINED ROCKS SHRINK TO A SMALL PILE
    depleted_rock = _darker(pygame.transform.smoothscale(load("rock.png"), (34, 28)), (170, 165, 160))
    scaled_bush = pygame.transform.smoothscale(load("berry_bush.png"), (65, 55))
    #A BUSH WITH NO BERRIES LEFT LOOKS DULL UNTIL IT GROWS BACK
    empty_bush = _darker(scaled_bush, (130, 150, 120))
    log_image = load("log.png")
    tent_art.build()
    tent_image = tent_art.images["open"]
    fire_art.build()
    campfire_frames = fire_art.lit_frames
    campfire_out_image = fire_art.out_frames

    build_ground_surface()


#================================================================
# DRAWING THE GROUND (DONE ONCE WHEN THE GAME LOADS)
#================================================================
GROUND_LEVEL_TINT = 24      #EACH LEVEL OF HIGH GROUND IS DRAWN THIS MUCH BRIGHTER

PATH_EDGE = (150, 104, 58)
PATH_DIRT = (214, 162, 90)
PATH_SPECK = (186, 136, 72)
SAND = (226, 184, 112)
WET_SAND = (190, 150, 92)
WATER_EDGE = (34, 96, 178)
WATER = (46, 126, 214)
WATER_LIGHT = (110, 176, 236)


def _blob_outline(rect, seed, points=36, wobble=0.14):
    #A WOBBLY OVAL: LOOKS NATURAL INSTEAD OF PERFECTLY ROUND
    rng = random.Random(seed)
    rx, ry, rw, rh = rect
    cx, cy = rw / 2, rh / 2
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
    outline = []
    for i in range(points):
        a = 2 * math.pi * i / points
        r = 1 + wobble * (math.sin(2 * a + phases[0]) + 0.6 * math.sin(3 * a + phases[1])
                          + 0.4 * math.sin(5 * a + phases[2])) / 2
        outline.append((cx + math.cos(a) * rw / 2 * r, cy + math.sin(a) * rh / 2 * r))
    return outline


def _shrink(points, center, factor):
    cx, cy = center
    return [(cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points]


GRASS_DARK = (52, 112, 42)
GRASS_MID = (78, 146, 50)
GRASS_LIGHT = (112, 178, 60)
GRASS_TIP = (150, 204, 80)


def _grass_blade(surface, x, y, height, lean, color, tip):
    pygame.draw.line(surface, color, (x, y), (x + lean, y - height), 2)
    surface.fill(tip, (x + lean - 1, y - height, 2, 2))


def _draw_mud(surface, rect, seed):
    rng = random.Random(seed)
    margin = 10
    rx, ry, rw, rh = rect
    patch = pygame.Surface((rw + margin * 2, rh + margin * 2), pygame.SRCALPHA)
    outline = [(x + margin, y + margin) for x, y in _blob_outline(rect, seed)]
    center = (rw / 2 + margin, rh / 2 + margin)

    #LAYERS: DARK EDGE, DRY MUD, WET MUD, WETTEST CENTRE
    pygame.draw.polygon(patch, (78, 56, 36), _shrink(outline, center, 1.05))
    pygame.draw.polygon(patch, (128, 94, 58), outline)
    pygame.draw.polygon(patch, (110, 78, 46), _shrink(outline, center, 0.74))
    pygame.draw.polygon(patch, (94, 66, 40), _shrink(outline, center, 0.42))

    def random_point(spread):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.random()) * spread
        return int(center[0] + math.cos(a) * rw / 2 * d), int(center[1] + math.sin(a) * rh / 2 * d)

    #SPECKLES AND SMALL STONES
    for _ in range(rw * rh // 120):
        x, y = random_point(0.85)
        patch.fill(rng.choice([(146, 110, 70), (84, 60, 36), (138, 102, 64)]), (x, y, 2, 2))
    for _ in range(3):
        x, y = random_point(0.7)
        patch.fill((150, 146, 136), (x, y, 3, 2))

    #PUDDLES WITH A BIT OF SKY REFLECTED IN THEM
    for _ in range(rng.randint(1, 3)):
        x, y = random_point(0.5)
        w, h = rng.randint(12, 22), rng.randint(6, 9)
        pygame.draw.ellipse(patch, (70, 58, 44), (x - w // 2 - 1, y - h // 2 + 1, w + 2, h + 1))
        pygame.draw.ellipse(patch, (88, 104, 118), (x - w // 2, y - h // 2, w, h))
        patch.fill((178, 200, 214), (x - w // 4, y - h // 4, max(2, w // 3), 2))

    #GRASS TUFTS ALONG THE EDGE, SO THE MUD BLENDS INTO THE GRASS
    for i in range(len(outline)):
        x1, y1 = outline[i]
        x2, y2 = outline[(i + 1) % len(outline)]
        for k in range(3):
            t = rng.random()
            x = int(x1 + (x2 - x1) * t + rng.uniform(-3, 3))
            y = int(y1 + (y2 - y1) * t + rng.uniform(-2, 4))
            _grass_blade(patch, x, y, rng.randint(4, 7), rng.choice((-1, 0, 1)),
                         rng.choice((GRASS_DARK, GRASS_MID)), GRASS_LIGHT)

    surface.blit(patch, (rx - margin, ry - margin))


def _draw_tall_grass(surface, rect, seed):
    rng = random.Random(seed)
    margin = 16
    rx, ry, rw, rh = rect
    patch = pygame.Surface((rw + margin * 2, rh + margin * 2), pygame.SRCALPHA)
    outline = [(x + margin, y + margin) for x, y in _blob_outline(rect, seed)]
    center = (rw / 2 + margin, rh / 2 + margin)

    #DARK GROUND UNDER THE TALL GRASS
    pygame.draw.polygon(patch, (56, 118, 44), outline)
    pygame.draw.polygon(patch, (48, 104, 40), _shrink(outline, center, 0.7))

    #LOTS OF BLADES, DRAWN FROM BACK TO FRONT SO LOWER ONES OVERLAP HIGHER ONES
    blades = []
    for _ in range(rw * rh // 26):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.random()) * 1.02
        x = center[0] + math.cos(a) * rw / 2 * d
        y = center[1] + math.sin(a) * rh / 2 * d + 6
        blades.append((y, x))
    blades.sort()
    for y, x in blades:
        color = rng.choice((GRASS_DARK, GRASS_MID, GRASS_MID, GRASS_LIGHT))
        tip = GRASS_TIP if color != GRASS_DARK else GRASS_MID
        _grass_blade(patch, int(x), int(y), rng.randint(8, 14), rng.choice((-2, -1, 0, 1, 2)), color, tip)

    surface.blit(patch, (rx - margin, ry - margin))


def _draw_paths(surface):
    rng = random.Random(4)
    for curve in path_curves:
        for x, y in curve:
            pygame.draw.circle(surface, PATH_EDGE, (int(x), int(y)), int(PATH_HALF + 3 + rng.uniform(-2, 2)))
    for curve in path_curves:
        for x, y in curve:
            pygame.draw.circle(surface, PATH_DIRT, (int(x), int(y)), int(PATH_HALF + rng.uniform(-2, 1)))
    for curve in path_curves:
        for x, y in curve[::2]:
            for _ in range(2):
                sx = int(x + rng.uniform(-PATH_HALF + 4, PATH_HALF - 4))
                sy = int(y + rng.uniform(-PATH_HALF + 4, PATH_HALF - 4))
                surface.fill(PATH_SPECK, (sx, sy, 2, 2))


def _draw_river(surface):
    rng = random.Random(9)
    for x, y in river_curve:
        pygame.draw.circle(surface, SAND, (int(x), int(y)), int(RIVER_HALF + SAND_WIDTH + rng.uniform(-3, 3)))
    for x, y in river_curve:
        pygame.draw.circle(surface, WET_SAND, (int(x), int(y)), int(RIVER_HALF + 3))
    for x, y in river_curve:
        pygame.draw.circle(surface, WATER_EDGE, (int(x), int(y)), int(RIVER_HALF))
    for x, y in river_curve:
        pygame.draw.circle(surface, WATER, (int(x), int(y)), int(RIVER_HALF - 6))
    #RIPPLES
    for x, y in river_curve[::2]:
        rx = int(x + rng.uniform(-RIVER_HALF + 10, RIVER_HALF - 14))
        ry = int(y + rng.uniform(-6, 6))
        pygame.draw.line(surface, WATER_LIGHT, (rx, ry), (rx + rng.randint(4, 9), ry), 2)
    #PEBBLES ON THE SAND
    for x, y in river_curve[::3]:
        side = rng.choice((-1, 1))
        px = int(x + side * (RIVER_HALF + rng.uniform(5, SAND_WIDTH)))
        surface.fill((160, 150, 140), (px, int(y + rng.uniform(-5, 5)), 3, 2))


def _draw_plateaus(surface, face_tile, side_tile, stairs_image):
    #BRIGHTER GRASS ON HIGH GROUND
    for r in range(ROWS):
        for c in range(COLS):
            level = height[r][c]
            if level > 0:
                tint = GROUND_LEVEL_TINT * level
                surface.fill((tint, tint, tint // 2), (c * TILE, r * TILE, TILE, TILE),
                             special_flags=pygame.BLEND_RGB_ADD)

    #ROCKY RIMS ON THE NORTH, WEST AND EAST EDGES
    t = EDGE_THICKNESS
    for r in range(ROWS):
        for c in range(COLS):
            h = height[r][c]
            if h == 0:
                continue
            x, y = c * TILE, r * TILE
            if c > 0 and height[r][c - 1] < h:
                surface.blit(side_tile, (x, y), (0, (r % 2) * 4, t, TILE))
                pygame.draw.line(surface, (34, 28, 26), (x, y), (x, y + TILE - 1))
            if c < COLS - 1 and height[r][c + 1] < h:
                surface.blit(side_tile, (x + TILE - t, y), (0, (r % 2) * 4, t, TILE))
                pygame.draw.line(surface, (34, 28, 26), (x + TILE - 1, y), (x + TILE - 1, y + TILE - 1))
            if r > 0 and height[r - 1][c] < h:
                pygame.draw.line(surface, (34, 28, 26), (x, y), (x + TILE - 1, y), 2)
                pygame.draw.line(surface, (112, 106, 98), (x, y + 2), (x + TILE - 1, y + 2), 2)
                pygame.draw.line(surface, (170, 215, 110), (x, y + 4), (x + TILE - 1, y + 4))

    #CLIFF FACES
    for (r, c), half in face_row.items():
        x, y = c * TILE, r * TILE
        surface.blit(face_tile, (x, y), ((x % 40), half * TILE, TILE, TILE))
        #DARK OUTLINE WHERE A CLIFF FACE ENDS
        if (r, c - 1) not in face_row and not _in_stairs(r, c - 1):
            pygame.draw.line(surface, (34, 28, 26), (x, y), (x, y + TILE - 1), 2)
        if (r, c + 1) not in face_row and not _in_stairs(r, c + 1):
            pygame.draw.line(surface, (34, 28, 26), (x + TILE - 2, y), (x + TILE - 2, y + TILE - 1), 2)

    #SHADOW ON THE GROUND JUST BELOW EACH CLIFF
    shadow = pygame.Surface((TILE, 12), pygame.SRCALPHA)
    for i, alpha in enumerate((80, 50, 25)):
        shadow.fill((0, 0, 0, alpha), (0, i * 4, TILE, 4))
    for (r, c), half in face_row.items():
        if half == 1 and (r + 1, c) not in face_row:
            surface.blit(shadow, (c * TILE, (r + 1) * TILE))

    #STAIRS
    for stair in stairs:
        surface.blit(stairs_image, stair.topleft)


def build_ground_surface():
    global ground_surface

    def load(name):
        return pygame.image.load(f"assets/environment/{name}").convert_alpha()

    #ONE BIG NON-REPEATING GRASS TEXTURE (REPEATED IF THE WORLD IS BIGGER THAN IT)
    grass = pygame.image.load("assets/environment/grass_ground.png").convert()
    ground_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
    for x in range(0, WORLD_WIDTH, grass.get_width()):
        for y in range(0, WORLD_HEIGHT, grass.get_height()):
            ground_surface.blit(grass, (x, y))

    for i, patch in enumerate(layout.TALL_GRASS):
        _draw_tall_grass(ground_surface, patch, seed=100 + i)
    _draw_paths(ground_surface)
    for i, patch in enumerate(layout.MUD):
        _draw_mud(ground_surface, patch, seed=200 + i)
    _draw_river(ground_surface)
    _draw_plateaus(ground_surface, load("cliff_face.png"), load("cliff_side.png"), load("stairs.png"))

    bridge_image = load("bridge_wide.png")
    for bridge in bridges:
        ground_surface.blit(bridge_image, bridge_image.get_rect(center=bridge.center))

    ground_surface = ground_surface.convert()


#================================================================
# DRAWING EACH FRAME
#================================================================
def draw_ground(screen, camera):
    #FLAT THINGS: GROUND AND PONDS
    screen.blit(ground_surface, (0, 0), camera)

    for pond in ponds:
        screen.blit(
            scaled_water, (pond.centerx - 65 - camera.x, pond.centery - 47 - camera.y)
        )


def get_sprites(camera):
    #TALL THINGS, AS (SORT_Y, IMAGE, SCREEN_POSITION).
    #THE RENDERER DRAWS THEM FROM TOP TO BOTTOM SO THINGS IN FRONT COVER THINGS BEHIND.
    view = camera.inflate(160, 200)
    sprites = []

    for log in logs:
        if view.colliderect(log):
            pos = log_image.get_rect(midbottom=(log.centerx, log.bottom + 4)).topleft
            sprites.append((log.bottom, log_image, (pos[0] - camera.x, pos[1] - camera.y)))

    for i, tree in enumerate(trees):
        if view.colliderect(tree):
            image = depleted_trees[i % 2] if i in collected_trees else scaled_trees[i % 2]
            shake = harvest_shake[2] if harvest_shake and harvest_shake[:2] == ("tree", i) else 0
            sprites.append((tree.bottom, image,
                            (tree.centerx - 40 + shake - camera.x, tree.bottom - 90 - camera.y)))

    for i, rock in enumerate(rocks):
        if view.colliderect(rock):
            if i in collected_rocks:
                sprites.append((rock.bottom, depleted_rock,
                                (rock.centerx - 17 - camera.x, rock.bottom - 28 - camera.y)))
            else:
                shake = harvest_shake[2] if harvest_shake and harvest_shake[:2] == ("rock", i) else 0
                sprites.append((rock.bottom, scaled_rock,
                                (rock.centerx - 27 + shake - camera.x, rock.bottom - 45 - camera.y)))

    for i, bush in enumerate(berry_bushes):
        if view.colliderect(bush):
            sprites.append((bush.bottom, empty_bush if i in collected_bushes else scaled_bush,
                            (bush.centerx - 32 - camera.x, bush.bottom - 55 - camera.y)))

    #TENTS ARE SORTED BY THEIR BACK EDGE, SO THE PLAYER IS DRAWN IN FRONT WHEN INSIDE
    for tent in tents:
        if view.colliderect(tent) and tent is not occupied_tent:
            pos = tent_image.get_rect(midbottom=(tent.centerx, tent.bottom)).topleft
            sprites.append((tent.top, tent_image, (pos[0] - camera.x, pos[1] - camera.y)))

    #CAMPFIRES FLICKER BETWEEN 3 FRAMES; PUT-OUT CAMPFIRES SHOW ASHES
    now = game_clock.now()
    for i, (campfire, lit) in enumerate(zip(campfires, campfire_lit)):
        if view.colliderect(campfire):
            #EACH FIRE STARTS AT A DIFFERENT POINT IN THE LOOP SO THEY DON'T FLICKER IN SYNC
            frame = fire_art.frame_index(now + i * 370)
            image = campfire_frames[frame] if lit else campfire_out_image[frame]
            pos = image.get_rect(midbottom=(campfire.centerx, campfire.bottom + 2)).topleft
            sprites.append((campfire.bottom, image, (pos[0] - camera.x, pos[1] - camera.y)))

    return sprites


#RESET WORLD
def reset_world():
    global wood, stone

    collected_trees.clear()
    collected_rocks.clear()
    collected_bushes.clear()
    bush_servings.clear()
    global _cost_grid
    if campfire_blockers:
        for blocker in campfire_blockers:
            if blocker in obstacles:
                obstacles.remove(blocker)
        campfire_blockers.clear()
        _cost_grid = None           #REBUILT WITHOUT THE OLD FIRES
    campfires.clear()
    campfire_lit.clear()
    tents.clear()
    wood = 0
    stone = 0
