#THE CAMPFIRE, DRAWN WITH CODE: A SMOOTH 16-FRAME FLAME LOOP WITH RISING EMBERS,
#AND A PUT-OUT FIRE WITH CHARRED LOGS AND A CURL OF SMOKE
import math
import random
import pygame

SIZE = (48, 64)             #EACH FRAME (THE STONES SIT AT THE BOTTOM)
FRAMES = 16
FRAME_TIME = 70             #MILLISECONDS PER FRAME (THE LOOP TAKES ~1.1 SECONDS)
BASE_Y = 52                 #WHERE THE FLAMES START (TOP OF THE LOGS)

STONE = (122, 122, 128)
STONE_LIGHT = (160, 160, 166)
STONE_DARK = (70, 70, 78)
LOG = (120, 74, 40)
LOG_DARK = (76, 46, 26)
LOG_BURNT = (46, 36, 32)

lit_frames = []
out_frames = []


def _stones(surface, front):
    #A RING OF STONES, SEEN FROM SLIGHTLY ABOVE (BACK ROW SMALLER AND HIGHER).
    #THE BACK HALF IS DRAWN BEHIND THE FLAMES, THE FRONT HALF IN FRONT OF THEM
    cx = SIZE[0] // 2
    for i in range(10):
        a = math.pi * 2 * i / 10
        if (math.sin(a) > 0.01) != front:
            continue
        x = cx + math.cos(a) * 17
        y = 54 + math.sin(a) * 6
        w = 9 if math.sin(a) > 0 else 7
        rect = pygame.Rect(0, 0, w, 6)
        rect.center = (round(x), round(y))
        pygame.draw.ellipse(surface, STONE_DARK, rect.inflate(2, 2))
        pygame.draw.ellipse(surface, STONE, rect)
        pygame.draw.line(surface, STONE_LIGHT, (rect.x + 2, rect.y + 1), (rect.right - 3, rect.y + 1))


def _logs(surface, colour, dark):
    #TWO CROSSED LOGS
    for (x1, y1, x2, y2) in ((12, 57, 34, 49), (14, 49, 36, 57)):
        pygame.draw.line(surface, dark, (x1, y1 + 1), (x2, y2 + 1), 5)
        pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 4)
        pygame.draw.circle(surface, (196, 150, 96) if colour == LOG else (80, 64, 56), (x2, y2), 2)


def _flame(surface, cx, height, width, lean, colour):
    #A TEARDROP: WIDE AT THE BOTTOM, POINTED AT THE TOP, LEANING A LITTLE
    points = []
    steps = 10
    for k in range(steps + 1):
        t = k / steps                       #0 = BOTTOM, 1 = TIP
        half = width / 2 * math.sin(math.pi * (0.5 + 0.5 * t)) * (1 - t * 0.15)
        y = BASE_Y - height * t
        x_shift = lean * t * t
        points.append((cx - half + x_shift, y))
    for k in range(steps, -1, -1):
        t = k / steps
        half = width / 2 * math.sin(math.pi * (0.5 + 0.5 * t)) * (1 - t * 0.15)
        y = BASE_Y - height * t
        x_shift = lean * t * t
        points.append((cx + half + x_shift, y))
    pygame.draw.polygon(surface, colour, [(round(x), round(y)) for x, y in points])


def build():
    #CALL THIS AFTER pygame.display.set_mode()
    lit_frames.clear()
    out_frames.clear()
    cx = SIZE[0] // 2
    rng = random.Random(7)
    #EMBERS: (START X, SPEED, START PHASE). EACH ONE LOOPS SMOOTHLY OVER THE 16 FRAMES
    embers = [(cx + rng.uniform(-8, 8), rng.choice([1, 2]), rng.random()) for _ in range(5)]
    #TONGUES OF FLAME: (X OFFSET, BASE HEIGHT, WIDTH, PHASE)
    tongues = [(-7, 15, 10, 0.0), (6, 17, 10, 0.37), (0, 24, 13, 0.7)]

    for f in range(FRAMES):
        t = f / FRAMES
        frame = pygame.Surface(SIZE, pygame.SRCALPHA)

        #GLOW ON THE GROUND
        glow = pygame.Surface(SIZE, pygame.SRCALPHA)
        pulse = 0.85 + 0.15 * math.sin(2 * math.pi * t * 2)
        pygame.draw.ellipse(glow, (255, 170, 70, int(70 * pulse)), (2, 44, 44, 18))
        frame.blit(glow, (0, 0))

        _stones(frame, False)
        _logs(frame, LOG, LOG_DARK)

        #FLAMES: THREE LAYERS (RED OUTSIDE, ORANGE, YELLOW CORE). HEIGHT AND SWAY USE TWO
        #SINE WAVES THAT BOTH FIT THE LOOP, SO THE ANIMATION NEVER "JUMPS"
        for layer, colour in enumerate(((226, 74, 30), (248, 146, 38), (255, 226, 112))):
            s = 1.0 - layer * 0.28
            for dx, base, width, phase in tongues:
                wave = math.sin(2 * math.pi * (t + phase)) * 0.6 + math.sin(4 * math.pi * (t + phase * 1.7)) * 0.4
                height = (base + 5 * wave) * s
                lean = 3 * math.sin(2 * math.pi * (t + phase + 0.25))
                _flame(frame, cx + dx * (1 - layer * 0.25), height, width * s, lean, colour)

        _stones(frame, True)

        #EMBERS RISING AND FADING
        for x, speed, phase in embers:
            life = (t * speed + phase) % 1.0
            ey = BASE_Y - 10 - life * 44
            ex = x + math.sin(life * 6 + phase * 6) * 3
            colour = (255, 220, 120) if life < 0.5 else (240, 120, 50)
            if life < 0.9:
                frame.set_at((round(ex), round(ey)), colour)
        lit_frames.append(frame)

        #PUT-OUT FIRE: CHARRED LOGS, A FEW DYING EMBERS, SMOKE CURLING UP
        out = pygame.Surface(SIZE, pygame.SRCALPHA)
        _stones(out, False)
        _logs(out, LOG_BURNT, (30, 24, 22))
        _stones(out, True)
        pygame.draw.ellipse(out, (90, 86, 84), (16, 50, 16, 5))         #ASH
        if f % 8 < 4:
            out.set_at((22, 51), (220, 90, 40))
        for k in range(3):
            life = (t + k / 3) % 1.0
            sy = 46 - life * 36
            sx = cx + math.sin(life * 5 + k) * 4
            radius = 2 + life * 4
            puff = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(puff, (200, 200, 205, int(110 * (1 - life))), (7, 7), round(radius))
            out.blit(puff, (round(sx) - 7, round(sy) - 7))
        out_frames.append(out)


def frame_index(now):
    return (now // FRAME_TIME) % FRAMES
