
import pygame


def draw_bar(screen, font, label, value, x, y, color):
    #DRAW THE LABEL
    text = font.render(f"{label}: {value}", True, (255, 255, 255))
    screen.blit(text, (x, y))

    #DRAW THE BACKGROUND BAR
    pygame.draw.rect(screen, (80, 80, 80), (x, y + 22, 120, 8))

    #CALCULATE THE FILLED PORTION
    bar_width = int(value * 1.2)

    #DRAW THE FILLED BAR
    pygame.draw.rect(screen, color, (x, y + 22, bar_width, 8))


def draw_hud(screen, font, day, wood, stone, survival):
    #DISPLAY CURRENT DAY AND RESOURCES
    day_text = font.render(f"Day {day}", True, (255, 255, 255))
    wood_text = font.render(f"Wood: {wood}", True, (255, 255, 255))
    stone_text = font.render(f"Stone: {stone}", True, (255, 255, 255))

    screen.blit(day_text, (20, 12))
    screen.blit(wood_text, (650, 20))
    screen.blit(stone_text, (650, 45))

    #DISPLAY SURVIVAL STATUS BARS
    draw_bar(screen, font, "Health", survival.health, 20, 42, (220, 60, 60))
    draw_bar(screen, font, "Hunger", survival.hunger, 20, 82, (230, 160, 40))
    draw_bar(screen, font, "Thirst", survival.thirst, 20, 122, (50, 150, 230))
    draw_bar(screen, font, "Energy", survival.energy, 20, 162, (60, 200, 100))
