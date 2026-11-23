#THE END OF A RUN: VICTORY (RESCUED / FOUND THE WAY OUT) OR DEFEAT (WITH WHAT KILLED YOU)
import math
import pygame
from config import *

GOLD = (250, 204, 96)
TEXT = (240, 238, 230)
TEXT_DIM = (180, 184, 190)

STORIES = {
    "rescued": ("RESCUED!",
                (120, 220, 140),
                "On the morning of day {next_day}, a search party spotted the smoke of your campfire "
                "rising above the pines. After {days} days alone in the wilderness, you walk out of "
                "the forest with the rangers, tired, hungry, and alive."),
    "escaped": ("YOU MADE IT OUT!",
                (120, 220, 140),
                "On the morning of day {next_day}, you followed the river downstream past the last "
                "ridge and saw the lights of a ranger station. After {days} days in the wild, "
                "you have found your way out of the forest."),
    "wolf": ("GAME OVER",
             (230, 70, 70),
             "The wolves closed in one last time. You fought hard for {days} day{s}, "
             "but the pack was too much for you."),
    "hunger": ("GAME OVER",
               (230, 70, 70),
               "Without enough food your strength slowly faded. You held on for {days} day{s} "
               "before the wilderness won."),
    "thirst": ("GAME OVER",
               (230, 70, 70),
               "With no water left, you couldn't go on. You survived {days} day{s} in the wild."),
    "hunger and thirst": ("GAME OVER",
                          (230, 70, 70),
                          "Starving and parched, you couldn't go any further. You survived {days} day{s}."),
    "cold": ("GAME OVER",
             (230, 70, 70),
             "Exhausted and frozen, you lay down by the trees and didn't get up again. "
             "You survived {days} day{s}."),
    None: ("GAME OVER",
           (230, 70, 70),
           "Your survivor has died after {days} day{s} in the wilderness."),
}

_fonts = {}


def _fonts_ready():
    if not _fonts:
        _fonts["title"] = pygame.font.SysFont("Arial", 40, bold=True)
        _fonts["text"] = pygame.font.SysFont("Arial", 16)
        _fonts["bold"] = pygame.font.SysFont("Arial", 15, bold=True)
        _fonts["key"] = pygame.font.SysFont("Arial", 13, bold=True)


def _wrap(text, font, width):
    words, lines, line = text.split(), [], ""
    for word in words:
        test = f"{line} {word}".strip()
        if font.size(test)[0] <= width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _centered(screen, surface, y):
    screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))


def draw_ending(screen, background, story, days, wolves_defeated, ai_mode, can_continue, now):
    #background = THE LAST FRAME OF THE GAME, SHOWN DIMMED BEHIND THE STORY
    _fonts_ready()
    if background is not None:
        screen.blit(background, (0, 0))
    else:
        screen.fill((20, 20, 20))
    victory = story in ("rescued", "escaped")
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((10, 20, 18, 170) if victory else (25, 8, 10, 185))
    screen.blit(shade, (0, 0))

    title, colour, text = STORIES.get(story, STORIES[None])
    who = "The AI" if ai_mode else "You"
    text = text.format(days=days, next_day=days + 1, s="" if days == 1 else "s")

    #PANEL
    panel = pygame.Rect(0, 0, 600, 330)
    panel.center = (WIDTH // 2, HEIGHT // 2)
    card = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(card, (16, 20, 26, 225), card.get_rect(), border_radius=14)
    pygame.draw.rect(card, (*colour, 170), card.get_rect(), width=2, border_radius=14)
    screen.blit(card, panel.topleft)

    #TITLE (GENTLY PULSING ON A VICTORY)
    scale = 1.0 + (0.03 * math.sin(now / 300) if victory else 0)
    title_surface = _fonts["title"].render(title, True, colour)
    if scale != 1.0:
        size = (int(title_surface.get_width() * scale), int(title_surface.get_height() * scale))
        title_surface = pygame.transform.smoothscale(title_surface, size)
    _centered(screen, title_surface, panel.y + 42)
    subtitle = f"{who} survived {days} day{'s' if days != 1 else ''}"
    if not victory:
        subtitle += " (rescue goal reached!)" if days >= GOAL_DAYS else f" (goal: {GOAL_DAYS})"
    _centered(screen, _fonts["bold"].render(subtitle, True, GOLD), panel.y + 78)

    #THE STORY
    y = panel.y + 104
    for line in _wrap(text, _fonts["text"], panel.width - 70):
        _centered(screen, _fonts["text"].render(line, True, TEXT), y)
        y += 22

    #STATS
    y = panel.bottom - 92
    stats = f"Days survived: {days}     Wolves defeated: {wolves_defeated}"
    _centered(screen, _fonts["bold"].render(stats, True, TEXT_DIM), y)

    #KEYS
    keys = []
    if can_continue:
        keys.append(("C", "keep going"))
    keys += [("R", "play again"), ("M", "menu"), ("Q", "quit")]
    surfaces = []
    for key, label in keys:
        k = _fonts["key"].render(key, True, (40, 30, 20))
        t = _fonts["text"].render(label, True, TEXT)
        surfaces.append((k, t))
    total = sum(k.get_width() + 14 + 6 + t.get_width() + 18 for k, t in surfaces) - 18
    x = WIDTH // 2 - total // 2
    y = panel.bottom - 50
    for k, t in surfaces:
        box = pygame.Rect(x, y, k.get_width() + 14, 22)
        pygame.draw.rect(screen, GOLD, box, border_radius=5)
        screen.blit(k, k.get_rect(center=box.center))
        screen.blit(t, (box.right + 6, y + 2))
        x = box.right + 6 + t.get_width() + 18


#KEPT FOR OLD CODE
def gameover(screen, font, days_survived, wolves_defeated=0):
    draw_ending(screen, None, None, days_survived, wolves_defeated, False, False, 0)
