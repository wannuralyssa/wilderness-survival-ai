
#MAIN MENU: SHOWN BEFORE THE GAME STARTS (AND AFTER GAME OVER IF THE PLAYER PRESSES M)
import math
import pygame
from config import *
import world

OPTIONS = ["Start Game", "How to Play", "Quit"]

CONTROLS = [
    ("Arrow keys", "Move"),
    ("E", "Collect, drink, eat, rest, relight a fire"),
    ("Space", "Attack a wolf in front of you"),
    ("C", "Build a campfire (3 wood, 2 stone)"),
    ("T", "Build a tent (4 wood)")
]

TIPS = [
    "Survive as many days as you can.",
    "Keep Food and Water above half and your health slowly heals.",
    "Rain puts out campfires: shelter in a tent.",
    "Cold drains energy: stand by a campfire to warm up.",
    "Wolves hunt from further away at night."
]

GOLD = (250, 204, 96)
TEXT = (240, 240, 235)
TEXT_DIM = (190, 195, 200)

fonts = {}


def _fonts():
    if not fonts:
        fonts["title"] = pygame.font.SysFont("Arial", 54, bold=True)
        fonts["subtitle"] = pygame.font.SysFont("Arial", 20, bold=True)
        fonts["button"] = pygame.font.SysFont("Arial", 22, bold=True)
        fonts["text"] = pygame.font.SysFont("Arial", 16)
        fonts["bold"] = pygame.font.SysFont("Arial", 16, bold=True)
    return fonts


def _panel(screen, rect, color, border, radius=12):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, color, panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, border, panel.get_rect(), width=2, border_radius=radius)
    screen.blit(panel, rect.topleft)


def _centered_text(screen, text, font, color, center, shadow=True):
    if shadow:
        s = fonts[font].render(text, True, (20, 24, 20))
        screen.blit(s, s.get_rect(center=(center[0] + 3, center[1] + 3)))
    s = fonts[font].render(text, True, color)
    screen.blit(s, s.get_rect(center=center))


def _button_rects():
    rects = []
    for i in range(len(OPTIONS)):
        rect = pygame.Rect(0, 0, 280, 50)
        rect.center = (WIDTH // 2, 320 + i * 66)
        rects.append(rect)
    return rects


def _draw_background(screen, now):
    #SLOWLY PAN ACROSS THE REAL GAME MAP
    camera = pygame.Rect(0, 0, WIDTH, HEIGHT)
    camera.centerx = WORLD_WIDTH // 2 + int((WORLD_WIDTH - WIDTH) / 2 * 0.9 * math.sin(now / 9000))
    camera.centery = WORLD_HEIGHT // 2 + int((WORLD_HEIGHT - HEIGHT) / 2 * 0.9 * math.sin(now / 13000))
    camera.clamp_ip(pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT))

    world.draw_ground(screen, camera)
    for _, image, position in sorted(world.get_sprites(camera), key=lambda s: s[0]):
        screen.blit(image, position)

    #DARKEN IT SO THE MENU STANDS OUT
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((10, 16, 20, 120))
    screen.blit(shade, (0, 0))


def _draw_main(screen, selected, now):
    #TITLE, GENTLY FLOATING UP AND DOWN
    bob = int(4 * math.sin(now / 600))
    _centered_text(screen, "Wilderness Survival", "title", GOLD, (WIDTH // 2, 150 + bob))
    _centered_text(screen, "A I   S I M U L A T O R", "subtitle", TEXT, (WIDTH // 2, 205 + bob))

    for i, (option, rect) in enumerate(zip(OPTIONS, _button_rects())):
        if i == selected:
            _panel(screen, rect.inflate(8, 4), (250, 204, 96, 235), (255, 240, 200, 255))
            _centered_text(screen, option, "button", (40, 30, 20), rect.center, shadow=False)
        else:
            _panel(screen, rect, (18, 22, 28, 190), (255, 255, 255, 60))
            _centered_text(screen, option, "button", TEXT, rect.center, shadow=False)

    hint = fonts["text"].render("Up / Down to choose   -   Enter to select   -   or use the mouse", True, TEXT_DIM)
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 30)))


def _draw_help(screen):
    panel = pygame.Rect(0, 0, 600, 430)
    panel.center = (WIDTH // 2, HEIGHT // 2)
    _panel(screen, panel, (18, 22, 28, 225), (250, 204, 96, 160))

    _centered_text(screen, "How to Play", "button", GOLD, (WIDTH // 2, panel.y + 34), shadow=False)

    y = panel.y + 70
    for key, action in CONTROLS:
        key_surface = fonts["bold"].render(key, True, (40, 30, 20))
        key_rect = pygame.Rect(panel.x + 40, y, max(70, key_surface.get_width() + 16), 24)
        pygame.draw.rect(screen, GOLD, key_rect, border_radius=6)
        screen.blit(key_surface, key_surface.get_rect(center=key_rect.center))
        screen.blit(fonts["text"].render(action, True, TEXT), (panel.x + 180, y + 3))
        y += 34

    y += 10
    for tip in TIPS:
        screen.blit(fonts["text"].render("-  " + tip, True, TEXT_DIM), (panel.x + 40, y))
        y += 24

    back = fonts["text"].render("Press Enter or Esc (or click) to go back", True, TEXT_DIM)
    screen.blit(back, back.get_rect(center=(WIDTH // 2, panel.bottom - 22)))


def run(screen, clock):
    #SHOW THE MENU UNTIL THE PLAYER CHOOSES. RETURNS "start" OR "quit"
    _fonts()
    selected = 0
    showing_help = False

    while True:
        clock.tick(60)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if showing_help:
                if event.type == pygame.MOUSEBUTTONDOWN or (
                        event.type == pygame.KEYDOWN and event.key in (
                            pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_BACKSPACE)):
                    showing_help = False
                continue

            choice = None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(OPTIONS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(OPTIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    choice = selected
            elif event.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(_button_rects()):
                    if rect.collidepoint(event.pos):
                        selected = i
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(_button_rects()):
                    if rect.collidepoint(event.pos):
                        choice = i

            if choice is not None:
                if OPTIONS[choice] == "Start Game":
                    return "start"
                if OPTIONS[choice] == "How to Play":
                    showing_help = True
                if OPTIONS[choice] == "Quit":
                    return "quit"

        _draw_background(screen, now)
        if showing_help:
            _draw_help(screen)
        else:
            _draw_main(screen, selected, now)
        pygame.display.flip()
