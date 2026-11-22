#THE TENT, DRAWN WITH CODE: AN OPEN TENT, AND A CLOSED, LANTERN-LIT TENT WITH THE PLAYER INSIDE
import math
import random
import pygame

SIZE = (104, 80)              #THE TENT IMAGE (ITS BOTTOM CENTRE STANDS ON THE TENT'S BOTTOM EDGE)

#SHAPE (POINTS INSIDE THE 104 x 80 IMAGE)
APEX = (46, 10)               #FRONT TOP OF THE TENT
BACK_APEX = (64, 4)           #BACK TOP (THE RIDGE GOES FROM APEX TO HERE)
FRONT_LEFT = (8, 76)
FRONT_RIGHT = (82, 76)
BACK_RIGHT = (100, 60)
DOOR_TOP = (45, 30)
DOOR_LEFT = (26, 76)
DOOR_RIGHT = (64, 76)

#COLOURS
CANVAS = (198, 124, 66)
CANVAS_SIDE = (150, 88, 48)
CANVAS_LIGHT = (226, 158, 96)
OUTLINE = (62, 36, 22)
INSIDE = (44, 28, 22)
ROPE = (222, 208, 172)
WOOD = (112, 76, 44)

images = {}


def _base(surface):
    #SHADOW, ROPES, PEGS, SIDE PANEL, FRONT FACE AND RIDGE: EVERYTHING EXCEPT THE DOOR
    shadow = pygame.Surface(SIZE, pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (25, 35, 20, 90), (4, 64, 100, 16))
    surface.blit(shadow, (0, 0))

    #GUY ROPES AND PEGS
    pygame.draw.line(surface, ROPE, APEX, (1, 72), 1)
    pygame.draw.line(surface, ROPE, BACK_APEX, (103, 50), 1)
    for x, y in ((1, 72), (102, 50)):
        pygame.draw.rect(surface, WOOD, (x - 1, y - 2, 3, 5))

    #SIDE PANEL (IN SHADE)
    side = [APEX, BACK_APEX, BACK_RIGHT, FRONT_RIGHT]
    pygame.draw.polygon(surface, CANVAS_SIDE, side)
    #FOLDS IN THE SIDE PANEL
    for t in (0.33, 0.66):
        top = (APEX[0] + (BACK_APEX[0] - APEX[0]) * t, APEX[1] + (BACK_APEX[1] - APEX[1]) * t)
        bottom = (FRONT_RIGHT[0] + (BACK_RIGHT[0] - FRONT_RIGHT[0]) * t,
                  FRONT_RIGHT[1] + (BACK_RIGHT[1] - FRONT_RIGHT[1]) * t)
        pygame.draw.line(surface, (134, 76, 40), top, bottom, 1)

    #FRONT FACE
    front = [APEX, FRONT_LEFT, FRONT_RIGHT]
    pygame.draw.polygon(surface, CANVAS, front)
    #A LIGHTER STRIP ALONG THE LEFT EDGE (THE SUN COMES FROM THE TOP LEFT)
    pygame.draw.polygon(surface, CANVAS_LIGHT, [APEX, FRONT_LEFT, (FRONT_LEFT[0] + 7, FRONT_LEFT[1]), (APEX[0] + 1, APEX[1] + 4)])

    #OUTLINES
    pygame.draw.polygon(surface, OUTLINE, side, 2)
    pygame.draw.polygon(surface, OUTLINE, front, 2)
    pygame.draw.line(surface, (240, 182, 120), (APEX[0] + 1, APEX[1]), (BACK_APEX[0] - 1, BACK_APEX[1] + 1), 1)

    #POLE TIPS STICKING OUT OF THE TOP
    pygame.draw.line(surface, WOOD, APEX, (APEX[0], APEX[1] - 7), 2)
    pygame.draw.line(surface, WOOD, BACK_APEX, (BACK_APEX[0], BACK_APEX[1] - 5), 2)


def _door_mask():
    mask = pygame.Surface(SIZE, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), [DOOR_TOP, DOOR_LEFT, DOOR_RIGHT])
    return mask


def _front_mask():
    mask = pygame.Surface(SIZE, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), [APEX, FRONT_LEFT, FRONT_RIGHT])
    return mask


def build():
    #CALL THIS AFTER pygame.display.set_mode()

    #OPEN TENT: DARK DOORWAY WITH THE FLAPS ROLLED BACK
    open_tent = pygame.Surface(SIZE, pygame.SRCALPHA)
    _base(open_tent)
    pygame.draw.polygon(open_tent, INSIDE, [DOOR_TOP, DOOR_LEFT, DOOR_RIGHT])
    pygame.draw.polygon(open_tent, (64, 42, 30), [DOOR_TOP, (DOOR_LEFT[0] + 8, DOOR_LEFT[1]), (DOOR_RIGHT[0] - 8, DOOR_RIGHT[1])])
    #ROLLED-BACK FLAPS
    pygame.draw.polygon(open_tent, CANVAS_LIGHT, [DOOR_TOP, DOOR_LEFT, (DOOR_LEFT[0] - 6, DOOR_LEFT[1])])
    pygame.draw.polygon(open_tent, CANVAS_SIDE, [DOOR_TOP, DOOR_RIGHT, (DOOR_RIGHT[0] + 6, DOOR_RIGHT[1])])
    pygame.draw.line(open_tent, OUTLINE, DOOR_TOP, (DOOR_LEFT[0] - 6, DOOR_LEFT[1]), 1)
    pygame.draw.line(open_tent, OUTLINE, DOOR_TOP, (DOOR_RIGHT[0] + 6, DOOR_RIGHT[1]), 1)
    images["open"] = open_tent

    #CLOSED TENT: FLAPS TIED SHUT, CANVAS GLOWING FROM A LANTERN INSIDE
    closed = pygame.Surface(SIZE, pygame.SRCALPHA)
    _base(closed)
    glow = pygame.Surface(SIZE, pygame.SRCALPHA)
    centre = (DOOR_TOP[0], 52)
    for radius, alpha in ((52, 70), (40, 80), (28, 100), (16, 120)):
        pygame.draw.circle(glow, (255, 210, 130, alpha), centre, radius)
    glow.blit(_front_mask(), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    closed.blit(glow, (0, 0))
    #THE TWO FLAPS MEET IN THE MIDDLE; LIGHT LEAKS THROUGH THE GAP
    pygame.draw.line(closed, (255, 232, 160), (DOOR_TOP[0], DOOR_TOP[1] + 2), (DOOR_TOP[0], 75), 2)
    pygame.draw.line(closed, OUTLINE, (DOOR_TOP[0] - 2, DOOR_TOP[1] + 2), (DOOR_TOP[0] - 2, 75), 1)
    pygame.draw.line(closed, OUTLINE, DOOR_TOP, DOOR_LEFT, 1)
    pygame.draw.line(closed, OUTLINE, DOOR_TOP, DOOR_RIGHT, 1)
    #TOGGLES HOLDING THE FLAPS SHUT
    for y in (44, 56, 68):
        pygame.draw.rect(closed, WOOD, (DOOR_TOP[0] - 3, y, 6, 2))
    pygame.draw.polygon(closed, OUTLINE, [APEX, FRONT_LEFT, FRONT_RIGHT], 2)
    images["closed"] = closed
    images["front_mask"] = _front_mask()

    fonts["z"] = pygame.font.SysFont("Arial", 13, bold=True)


fonts = {}
_silhouettes = {}


def _silhouette():
    #THE PLAYER'S HEAD AND SHOULDERS AS A SHADOW, CAST ON THE CANVAS BY THE LANTERN
    if "shadow" not in _silhouettes:
        shadow = pygame.Surface((40, 34), pygame.SRCALPHA)
        colour = (88, 42, 18, 150)
        pygame.draw.ellipse(shadow, colour, (4, 20, 32, 22))      #SHOULDERS
        pygame.draw.rect(shadow, colour, (16, 14, 8, 10))         #NECK
        pygame.draw.circle(shadow, colour, (20, 11), 9)           #HEAD
        pygame.draw.circle(shadow, colour, (29, 6), 4)            #PONYTAIL
        pygame.draw.circle(shadow, colour, (32, 11), 3)
        _silhouettes["shadow"] = shadow
    return _silhouettes["shadow"]


def draw_occupied(screen, topleft, player_image, now, resting, raining):
    #THE TENT WITH THE PLAYER INSIDE: CLOSED, LANTERN-LIT, A SHADOW MOVING ON THE CANVAS
    tent = images["closed"].copy()

    #THE PLAYER'S SHADOW BREATHES SLOWLY UP AND DOWN
    shadow = _silhouette()
    breathe = round(math.sin(now / 700) * 1.2)
    layer = pygame.Surface(SIZE, pygame.SRCALPHA)
    layer.blit(shadow, (DOOR_TOP[0] - shadow.get_width() // 2 - 6, 42 + breathe))
    layer.blit(images["front_mask"], (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    tent.blit(layer, (0, 0))
    screen.blit(tent, topleft)

    x, y = topleft

    #RAIN DRUMMING ON THE ROOF
    if raining:
        rng = random.Random(now // 90)
        for _ in range(7):
            t = rng.random()
            px = APEX[0] + (BACK_RIGHT[0] - APEX[0]) * t * rng.random()
            py = APEX[1] + (BACK_RIGHT[1] - APEX[1]) * t
            px, py = x + int(px) + rng.randint(-3, 3), y + int(py) - 2
            pygame.draw.line(screen, (200, 220, 255), (px - 2, py - 1), (px, py), 1)
            pygame.draw.line(screen, (200, 220, 255), (px + 2, py - 1), (px, py), 1)

    #Zzz WHILE RESTING
    if resting:
        for i in range(3):
            phase = ((now / 1800) + i / 3) % 1.0
            zx = x + BACK_APEX[0] + 4 + int(phase * 14) + i * 2
            zy = y + BACK_APEX[1] - int(phase * 26)
            letter = fonts["z"].render("z", True, (240, 240, 255))
            letter.set_alpha(int(255 * min(1.0, (1 - phase) * 2)))
            screen.blit(letter, (zx, zy))
