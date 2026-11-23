
import math
import pygame
import hmm
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
show_hmm = False        #H SHOWS / HIDES THE WEATHER FORECAST PANEL
show_pack = False       #G SHOWS / HIDES THE WOLF PACK PANEL (GAME THEORY + MACHINE LEARNING)

#COLOUR OF EACH HIDDEN STATE AND EACH SIGN IN THE HMM PANEL
STATE_COLOURS = [(250, 210, 90), (120, 140, 200), (70, 120, 235), (170, 220, 240), (235, 245, 255)]
PANEL_NAMES = ["Clear", "Storm front", "Rain", "Cold front", "Cold snap"]
SIGN_COLOURS = [(250, 210, 90), (150, 155, 170), (150, 220, 170), (70, 120, 235), (235, 245, 255)]


def load_assets():
    #CALL THIS AFTER pygame.display.set_mode()
    for name in ("health", "food", "water", "energy", "wood", "stone", "wolf",
                 "sun", "moon", "rain", "cold", "clear"):
        icons[name] = pygame.image.load(f"assets/ui/icon_{name}.png").convert_alpha()
        small_icons[name] = pygame.transform.smoothscale(icons[name], (16, 16))
    fonts["tiny"] = pygame.font.SysFont("Arial", 11)
    fonts["small"] = pygame.font.SysFont("Arial", 12)
    fonts["bold"] = pygame.font.SysFont("Arial", 12, bold=True)
    fonts["big"] = pygame.font.SysFont("Arial", 14, bold=True)


small_icons = {}
next_panel_y = 0        #WHERE THE NEXT PANEL ON THE RIGHT CAN GO (SET BY draw_hud)
left_panel_y = 0        #WHERE A PANEL ON THE LEFT CAN GO (UNDER THE STATS)


def _panel(screen, rect, radius=8):
    #SEE-THROUGH ROUNDED PANEL
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, PANEL_COLOR, panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, PANEL_BORDER, panel.get_rect(), width=1, border_radius=radius)
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
    radius = rect.height // 2
    pygame.draw.rect(screen, BAR_BACK, rect, border_radius=radius)
    if fraction > 0:
        filled = rect.copy()
        filled.width = max(rect.height, int(rect.width * fraction))
        pygame.draw.rect(screen, color, filled, border_radius=radius)
        #A LIGHTER STRIP ALONG THE TOP MAKES THE BAR LOOK ROUNDED
        if rect.height >= 7 and filled.width > 6:
            shine = pygame.Rect(filled.x + 2, filled.y + 1, filled.width - 4, 1)
            light = tuple(min(255, c + 60) for c in color)
            pygame.draw.rect(screen, light, shine)


PANEL_WIDTH = 150           #THE PANELS ON THE RIGHT


def draw_hmm_panel(screen, weather, rect):
    #WHAT THE HMM BELIEVES ABOUT THE HIDDEN WEATHER, FROM THE SIGNS IT HAS SEEN
    _panel(screen, rect)
    fc = weather.forecast
    x, y = rect.x + 8, rect.y + 5
    _text(screen, "Sky reading (HMM)", (x, y), "bold", (255, 214, 120))
    y += 17

    #FILTERED BELIEF: P(HIDDEN STATE NOW | ALL SIGNS SO FAR)
    for i, name in enumerate(PANEL_NAMES):
        p = fc.belief[i]
        _text(screen, name, (x, y), "tiny", TEXT if p >= 0.5 else TEXT_DIM)
        _text(screen, f"{p:.0%}", (rect.right - 8, y), "tiny", TEXT_DIM, align="right")
        _bar(screen, pygame.Rect(x + 62, y + 4, rect.width - 108, 5), p, STATE_COLOURS[i])
        y += 13

    #THE LAST SIGNS SEEN, AND THE MOST LIKELY HIDDEN STATES BEHIND THEM (VITERBI)
    y += 3
    path = fc.viterbi_path()
    cell = 7
    start = rect.right - 8 - cell * fc.HISTORY
    _text(screen, "Signs", (x, y), "tiny", TEXT_DIM)
    for k, sign in enumerate(fc.signs):
        pygame.draw.rect(screen, SIGN_COLOURS[sign], (start + k * cell, y + 3, cell - 1, 7), border_radius=1)
    y += 12
    _text(screen, "Viterbi", (x, y), "tiny", TEXT_DIM)
    for k, state in enumerate(path):
        pygame.draw.rect(screen, STATE_COLOURS[state], (start + k * cell, y + 3, cell - 1, 7), border_radius=1)
    y += 14

    #PREDICTION: CHANCE OF RAIN / COLD IN THE NEXT 30 SECONDS
    seconds = hmm.FORECAST_TICKS * hmm.TICK // 1000
    _text(screen, f"{seconds}s:", (x, y), "tiny", TEXT_DIM)
    _text(screen, f"rain {fc.rain_soon:.0%}  cold {fc.cold_soon:.0%}", (rect.right - 8, y), "bold",
          TEXT, align="right")


def draw_pack_panel(screen, weather, survival, rect):
    #THE ENCOUNTER GAME'S NASH EQUILIBRIUM RIGHT NOW, AND WHAT THE PACK HAS LEARNED ABOUT YOU
    import game_theory as gt
    import pack_learning
    import wolves
    _panel(screen, rect)
    x, y = rect.x + 8, rect.y + 5
    _text(screen, "Wolf pack (GT + ML)", (x, y), "bold", (255, 214, 120))
    y += 17

    fire = weather.player_near_fire
    you, wolf_mix, value = gt.equilibrium(survival.WOLF_DAMAGE, wolves.WOLF_MAX_HEALTH, fire)
    #NASH EQUILIBRIUM: ATTACK / EVADE FOR YOU, LUNGE / CIRCLE / STALK FOR THE WOLVES
    _text(screen, "Nash equilibrium" + ("  (by fire)" if fire else ""), (x, y), "tiny", TEXT_DIM)
    y += 13
    _text(screen, "You", (x + 6, y), "tiny", TEXT_DIM)
    _text(screen, f"A{you[0]:.0%} E{you[1]:.0%}", (rect.right - 8, y), "tiny", TEXT, align="right")
    y += 13
    _text(screen, "Wolf", (x + 6, y), "tiny", TEXT_DIM)
    _text(screen, f"L{wolf_mix[0]:.0%} C{wolf_mix[1]:.0%} S{wolf_mix[2]:.0%}", (rect.right - 8, y), "tiny",
          TEXT, align="right")
    y += 16

    model = pack_learning.models[wolves.LEARNING_MODE]
    features = (int(survival.health < 40), int(fire), int(wolves.player_was_moving))
    attack = model.predict(features)[0]
    _text(screen, "You'll attack", (x, y), "tiny", TEXT_DIM)
    _text(screen, f"{attack:.0%}", (rect.right - 8, y), "bold", (255, 170, 120), align="right")
    y += 13
    accuracy = model.accuracy()
    acc_text = f"{accuracy:.0%}" if accuracy is not None else "-"
    _text(screen, f"{model.examples} rounds, right {acc_text}", (x, y), "tiny", TEXT_DIM)
    y += 13
    trust = model.confidence() if model.examples >= 5 else 0.0
    _text(screen, "Exploit", (x, y), "tiny", TEXT_DIM)
    _bar(screen, pygame.Rect(x + 44, y + 4, rect.width - 86, 5), trust, (230, 110, 90))
    _text(screen, f"{trust:.0%}", (rect.right - 8, y), "tiny", TEXT_DIM, align="right")


def draw_hud(screen, day, wood, stone, survival, weather, wolves_defeated):
    global next_panel_y, left_panel_y
    now = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(now / 150)

    #------------------------------------------------------------
    # SURVIVAL STATS (TOP LEFT): ICON, BAR AND NUMBER ON ONE SMALL ROW EACH
    #------------------------------------------------------------
    values = {
        "Health": survival.health,
        "Food": 100 - survival.hunger,
        "Water": 100 - survival.thirst,
        "Energy": survival.energy
    }

    panel = pygame.Rect(8, 8, 150, 10 + 17 * len(STAT_ROWS))
    _panel(screen, panel)

    y = panel.y + 6
    for label, icon, color in STAT_ROWS:
        value = values[label]
        low = value <= LOW_STAT

        screen.blit(small_icons[icon], (panel.x + 6, y))
        value_rect = _text(screen, str(int(value)), (panel.right - 7, y + 1), "bold",
                           (255, 120, 110) if low else TEXT_DIM, align="right")
        if label == "Health" and survival.regenerating:
            #GREEN "+" WHILE HEALTH IS COMING BACK
            _text(screen, "+", (value_rect.left - 2, y), "bold", (120, 230, 120), align="right")

        bar_color = color
        if low:
            #FLASH WHEN LOW
            bar_color = tuple(int(c + (255 - c) * 0.5 * pulse) for c in color)
        _bar(screen, pygame.Rect(panel.x + 27, y + 5, panel.width - 64, 7), value / 100, bar_color)
        y += 17

    #WHAT THE WEATHER IS DOING TO YOU (SMALL LINE UNDER THE PANEL)
    left_panel_y = panel.bottom + 5
    status = weather.status_text()
    if status:
        text, color = status
        tag = fonts["bold"].render(text, True, color)
        tag_rect = pygame.Rect(panel.x, panel.bottom + 4, tag.get_width() + 14, 18)
        _panel(screen, tag_rect, 6)
        screen.blit(tag, (tag_rect.x + 7, tag_rect.y + 2))
        left_panel_y = tag_rect.bottom + 5

    #------------------------------------------------------------
    # DAY, TIME, WEATHER AND RESOURCES (TOP RIGHT)
    #------------------------------------------------------------
    right = pygame.Rect(WIDTH - PANEL_WIDTH - 8, 8, PANEL_WIDTH, 68)
    _panel(screen, right)
    x = right.x + 6

    #DAY NUMBER (OUT OF THE GOAL) WITH SUN OR MOON, AND HOW MUCH OF THE DAY / NIGHT IS LEFT
    screen.blit(small_icons["moon" if weather.is_night_now else "sun"], (x, right.y + 4))
    goal = f" / {GOAL_DAYS}" if day <= GOAL_DAYS else ""
    _text(screen, f"Day {day}{goal}", (x + 21, right.y + 4), "big")
    elapsed = weather.elapsed_time
    if elapsed < DAY_DURATION:
        fraction, color = elapsed / DAY_DURATION, (250, 200, 80)
    else:
        fraction, color = (elapsed - DAY_DURATION) / NIGHT_DURATION, (150, 160, 230)
    _bar(screen, pygame.Rect(x, right.y + 23, right.width - 12, 4), fraction, color)

    #WEATHER, PLUS THE HMM FORECAST (A CHANCE, WORKED OUT ONLY FROM THE SIGNS IN THE SKY)
    icon = {"rain": "rain", "cold": "cold"}.get(weather.current, "clear")
    y = right.y + 30
    screen.blit(small_icons[icon], (x, y))
    _text(screen, weather.WEATHER_NAMES[weather.current], (x + 21, y + 1), "bold")
    fc = weather.forecast
    if weather.current == weather.CLEAR:
        name, chance = max((("Rain", fc.rain_soon), ("Cold", fc.cold_soon)), key=lambda item: item[1])
        if chance >= 0.2:
            warm = min(1.0, chance / 0.7)
            colour = (255, int(230 - 60 * warm), int(150 - 70 * warm))
            _text(screen, f"{name} {chance:.0%}", (right.right - 7, y + 2), "tiny", colour, align="right")
        else:
            _text(screen, hmm.OBSERVATION_NAMES[weather.sky_sign], (right.right - 7, y + 2), "tiny",
                  TEXT_DIM, align="right")

    #RESOURCES
    y = right.y + 49
    for icon, amount in (("wood", wood), ("stone", stone), ("wolf", wolves_defeated)):
        screen.blit(small_icons[icon], (x, y))
        _text(screen, str(amount), (x + 19, y + 1), "bold")
        x += 48

    next_panel_y = right.bottom + 6
    if show_hmm:
        rect = pygame.Rect(right.x, next_panel_y, PANEL_WIDTH, 128)
        draw_hmm_panel(screen, weather, rect)
        next_panel_y = rect.bottom + 6
    if show_pack:
        rect = pygame.Rect(right.x, next_panel_y, PANEL_WIDTH, 109)
        draw_pack_panel(screen, weather, survival, rect)
        next_panel_y = rect.bottom + 6
