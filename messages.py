import pygame
import game_clock
import hud
from config import WIDTH, HEIGHT

#MESSAGE SETTINGS
message_text = ""
message_start_time = 0
MESSAGE_DURATION = 1000
message_duration = MESSAGE_DURATION
message_style = None

SLIDE_TIME = 180        #MILLISECONDS TO SLIDE IN
FADE_TIME = 250         #MILLISECONDS TO FADE OUT AT THE END
BOTTOM_GAP = 14         #SPACE BETWEEN THE NOTIFICATION AND THE BOTTOM OF THE SCREEN

#ACCENT COLOURS FOR EACH KIND OF MESSAGE
GOOD = (110, 205, 120)
BAD = (232, 84, 84)
WARN = (240, 182, 70)
INFO = (110, 170, 240)

#(WORDS IN THE MESSAGE, ICON, ACCENT). THE FIRST MATCH WINS
STYLES = [
    (("not enough space",), None, BAD),
    (("exhausted and freezing",), "cold", BAD),
    (("tent built",), None, GOOD),
    (("rest in your tent",), "energy", GOOD),
    (("wolf attacked",), "wolf", BAD),
    (("defeated a wolf",), "wolf", GOOD),
    (("too exhausted to fight",), "energy", BAD),
    (("wood and", "need "), "wood", BAD),
    (("wood!",), "wood", GOOD),
    (("tree",), "wood", WARN),
    (("stone",), "stone", GOOD),
    (("rock",), "stone", WARN),
    (("drank", "water"), "water", GOOD),
    (("berries",), "food", GOOD),
    (("put out your campfire",), "rain", BAD),
    (("rain", "clouds", "wet", "tent"), "rain", WARN),
    (("icy", "cold", "freezing"), "cold", WARN),
    (("clears up",), "clear", GOOD),
    (("sun is setting", "wolves hunt"), "moon", WARN),
    (("day ",), "sun", WARN),
    (("rested", "rest "), "energy", GOOD),
    (("campfire", "relit"), "energy", GOOD),
]
BAD_WORDS = ("need ", "not enough", "too ", "no ", "nothing", "exhausted", "already")

fonts = {}


def show_message(text, duration=MESSAGE_DURATION):
    #duration = HOW LONG THE MESSAGE STAYS ON SCREEN (MILLISECONDS)
    global message_text, message_start_time, message_duration, message_style

    now = game_clock.now()
    still_showing = message_text and now - message_start_time < message_duration
    message_text = text
    #A MESSAGE THAT REPLACES ANOTHER ONE DOESN'T SLIDE IN AGAIN
    message_start_time = now - (SLIDE_TIME if still_showing else 0)
    message_duration = duration + (SLIDE_TIME if still_showing else 0)
    message_style = style_for(text)


def style_for(text):
    #PICK AN ICON AND A COLOUR FROM WHAT THE MESSAGE IS ABOUT
    lower = text.lower()
    icon, accent = None, INFO
    for words, style_icon, style_accent in STYLES:
        if any(word in lower for word in words):
            icon, accent = style_icon, style_accent
            break
    if accent == GOOD and any(lower.startswith(word) or f" {word}" in lower for word in BAD_WORDS):
        accent = BAD
    if lower.startswith(BAD_WORDS):
        accent = BAD
    return icon, accent


def draw_message(screen, font):
    if not message_text:
        return
    elapsed = game_clock.now() - message_start_time
    if elapsed >= message_duration:
        return

    if not fonts:
        fonts["text"] = pygame.font.SysFont("Arial", 13, bold=True)
    icon_name, accent = message_style or (None, INFO)
    icon = hud.small_icons.get(icon_name) if icon_name else None

    #SLIDE UP AT THE START, FADE OUT AT THE END
    slide = min(1.0, elapsed / SLIDE_TIME)
    slide = 1 - (1 - slide) ** 3
    alpha = min(1.0, (message_duration - elapsed) / FADE_TIME, 0.25 + 0.75 * slide)

    text = fonts["text"].render(message_text, True, (245, 242, 232))
    shadow = fonts["text"].render(message_text, True, (0, 0, 0))
    icon_space = 30 if icon else 14
    width = min(WIDTH - 40, text.get_width() + icon_space + 22)
    height = 30

    card = pygame.Surface((width, height + 4), pygame.SRCALPHA)
    body = pygame.Rect(0, 0, width, height)

    #DROP SHADOW, DARK BODY, COLOURED STRIPE ON THE LEFT, THIN BORDER
    pygame.draw.rect(card, (0, 0, 0, 90), body.move(0, 3), border_radius=9)
    pygame.draw.rect(card, (20, 24, 30, 215), body, border_radius=9)
    pygame.draw.rect(card, (*accent, 255), (0, 0, 5, height),
                     border_top_left_radius=9, border_bottom_left_radius=9)
    pygame.draw.rect(card, (255, 255, 255, 40), body, width=1, border_radius=9)

    #ICON IN A SOFT COLOURED CIRCLE (OR A SMALL DOT WHEN THERE IS NO ICON)
    x = 12
    if icon:
        pygame.draw.circle(card, (*accent, 60), (x + 9, height // 2), 11)
        card.blit(icon, icon.get_rect(center=(x + 9, height // 2)))
        x += 25
    else:
        pygame.draw.circle(card, (*accent, 255), (x + 2, height // 2), 3)
        x += 10

    text_y = (height - text.get_height()) // 2
    card.blit(shadow, (x + 1, text_y + 1))
    card.blit(text, (x, text_y))

    #A THIN LINE ALONG THE BOTTOM SHOWS HOW LONG THE MESSAGE WILL STAY
    left = 1 - elapsed / message_duration
    timer_width = int((width - 24) * left)
    if timer_width > 0:
        pygame.draw.rect(card, (*accent, 150), (12, height - 3, timer_width, 1))

    card.set_alpha(int(255 * max(0.0, alpha)))
    y = HEIGHT - BOTTOM_GAP - height + int((1 - slide) * 18)
    screen.blit(card, ((WIDTH - width) // 2, y))
