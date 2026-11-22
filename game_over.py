import pygame
from config import *


def _centered(screen, font, text, color, y):
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=(WIDTH // 2, y)))


def gameover(screen, font, days_survived, wolves_defeated=0):
    #GAME OVER TITLE
    title_font = pygame.font.SysFont("Arial", 50, bold=True)
    _centered(screen, title_font, "GAME OVER", (220, 20, 60), 190)

    #DAYS SURVIVED AND WOLVES DEFEATED
    _centered(screen, font, f"You survived {days_survived} day(s)!", (255, 255, 255), 265)
    _centered(screen, font, f"Wolves defeated: {wolves_defeated}", (200, 200, 200), 295)

    #OPTIONS
    _centered(screen, font, "Press R to Restart", (255, 255, 255), 360)
    _centered(screen, font, "Press M for the Main Menu", (255, 255, 255), 395)
    _centered(screen, font, "Press Q to Quit", (255, 255, 255), 430)
