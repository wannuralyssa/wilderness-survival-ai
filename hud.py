
import math
import pygame
from config import *

#COLOURS
PANEL_COLOR = (18, 22, 28, 175)
PANEL_BORDER = (255, 255, 255, 45)
TEXT = (240, 240, 235)
TEXT_DIM = (175, 180, 185)
BAR_BACK = (55, 58, 64)

#EACH STAT: (LABEL, ICON, COLOUR). FOOD AND WATER ARE SHOWN AS "HOW FULL YOU ARE",
#SO EVERY BAR MEANS THE SAME THING: FULL = GOOD, EMPTY = DANGER
STAT_ROWS = [
    ("Health", "health", (225, 64, 72)),
    ("Food", "food", (236, 150, 52)),
    ("Water", "water", (64, 156, 236)),
    ("Energy", "energy", (240, 206, 64))
]
LOW_STAT = 25           #BARS BELOW THIS FLASH AS A WARNING

icons = {}
fonts = {}


def load_assets():
    #CALL THIS AFTER pygame.display.set_mode()
    for name in ("health", "food", "water", "energy", "wood", "stone", "wolf",
                 "sun", "moon", "rain", "cold", "clear"):
        icons[name] = pygame.image.load(f"assets/ui/icon_{name}.png").convert_alpha()
    fonts["small"] = pygame.font.SysFont("Arial", 14)
    fonts["bold"] = pygame.font.SysFont("Arial", 15, bold=True)
    fonts["big"] = pygame.font.SysFont("Arial", 20, bold=True)


def _panel(screen, rect):
    #SEE-THROUGH ROUNDED PANEL
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, PANEL_COLOR, panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), width=1, border_radius=10)
    screen.blit(panel, rect.topleft)


def _text(screen, text, pos, font="small", color=TEXT, align="left"):
    surface = fonts[font].render(text, True, color)
    rect = surface.get_rect()
    if align == "right":
        rect.topright = pos
    else:
        rect.topleft = pos
    screen.blit(surface, rect)
    return rect


def _bar(screen, rect, fraction, color):
    fraction = max(0.0, min(1.0, fraction))
    pygame.draw.rect(screen, BAR_BACK, rect, border_radius=5)
    if fraction > 0:
        filled = rect.copy()
        filled.width = max(rect.height, int(rect.width * fraction))
        pygame.draw.rect(screen, color, filled, border_radius=5)
        #A LIGHTER STRIP ALONG THE TOP MAKES THE BAR LOOK ROUNDED
        if rect.height >= 8 and filled.width > 8:
            shine = pygame.Rect(filled.x + 3, filled.y + 2, filled.width - 6, 2)
            light = tuple(min(255, c + 60) for c in color)
            pygame.draw.rect(screen, light, shine, border_radius=1)


def draw_hud(screen, day, wood, stone, survival, weather, wolves_defeated):
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now / 150)

    #------------------------------------------------------------
    # SURVIVAL STATS (TOP LEFT)
    #------------------------------------------------------------
    values = {
        "Health": survival.health,
        "Food": 100 - survival.hunger,
        "Water": 100 - survival.thirst,
        "Energy": survival.energy
    }

    panel = pygame.Rect(10, 10, 236, 26 + 30 * len(STAT_ROWS))
    _panel(screen, panel)

    y = panel.y + 12
    for label, icon, color in STAT_ROWS:
        value = values[label]
        low = value <= LOW_STAT

        screen.blit(icons[icon], (panel.x + 10, y))
        _text(screen, label, (panel.x + 42, y - 2), "bold", (255, 120, 110) if low else TEXT)
        value_rect = _text(screen, str(int(value)), (panel.right - 12, y - 2), "bold",
                           (255, 120, 110) if low else TEXT_DIM, align="right")
        if label == "Health" and survival.regenerating:
            #GREEN "+" WHILE HEALTH IS COMING BACK
            _text(screen, "+", (value_rect.left - 4, y - 3), "bold", (120, 230, 120), align="right")

        bar_color = color
        if low:
            #FLASH WHEN LOW
            bar_color = tuple(int(c + (255 - c) * 0.5 * pulse) for c in color)
        _bar(screen, pygame.Rect(panel.x + 42, y + 16, panel.width - 54, 9), value / 100, bar_color)
        y += 30

    #WHAT THE WEATHER IS DOING TO YOU (SMALL LINE UNDER THE PANEL)
    status = weather.status_text()
    if status:
        text, color = status
        tag = fonts["bold"].render(text, True, color)
        tag_rect = pygame.Rect(panel.x, panel.bottom + 6, tag.get_width() + 20, 24)
        _panel(screen, tag_rect)
        screen.blit(tag, (tag_rect.x + 10, tag_rect.y + 3))

    #------------------------------------------------------------
    # DAY, TIME AND WEATHER (TOP RIGHT)
    #------------------------------------------------------------
    right = pygame.Rect(WIDTH - 196, 10, 186, 120)
    _panel(screen, right)

    #DAY NUMBER WITH SUN OR MOON
    screen.blit(icons["moon" if weather.is_night_now else "sun"], (right.x + 10, right.y + 10))
    _text(screen, f"Day {day}", (right.x + 42, right.y + 10), "big")
    _text(screen, "Night" if weather.is_night_now else "Day", (right.right - 12, right.y + 14),
          "small", TEXT_DIM, align="right")

    #TIME BAR: HOW MUCH OF THE DAY (OR NIGHT) IS LEFT
    elapsed = weather.elapsed_time
    if elapsed < DAY_DURATION:
        fraction, color = elapsed / DAY_DURATION, (250, 200, 80)
    else:
        fraction, color = (elapsed - DAY_DURATION) / NIGHT_DURATION, (150, 160, 230)
    _bar(screen, pygame.Rect(right.x + 12, right.y + 40, right.width - 24, 6), fraction, color)

    #WEATHER, PLUS A FORECAST WHEN IT IS ABOUT TO CHANGE
    icon = {"rain": "rain", "cold": "cold"}.get(weather.current, "clear")
    screen.blit(icons[icon], (right.x + 10, right.y + 54))
    _text(screen, weather.WEATHER_NAMES[weather.current], (right.x + 42, right.y + 52), "bold")
    if weather.upcoming and weather.upcoming != weather.current:
        _text(screen, f"{weather.WEATHER_NAMES[weather.upcoming]} soon", (right.x + 42, right.y + 68),
              "small", (255, 210, 120))

    #RESOURCES
    x = right.x + 10
    for icon, amount in (("wood", wood), ("stone", stone), ("wolf", wolves_defeated)):
        screen.blit(icons[icon], (x, right.y + 88))
        _text(screen, str(amount), (x + 27, right.y + 91), "bold")
        x += 58
