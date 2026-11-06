
import pygame
import world
import hud
import messages
import survival_system as survival
from config import *

def draw_frame(screen, font, day, player_rect, is_night, night_overlay):
    #DRAW BACKGROUND
    screen.fill(GRASS)

    #DRAW WORLD OBJECTS
    world.draw_world(screen)

    #DRAW NIGHT EFFECT
    if is_night:
        screen.blit(night_overlay, (0, 0))

    #DRAW PLAYER
    pygame.draw.rect(screen, PLAYER_COLOR, player_rect)

    #DRAW HUD
    hud.draw_hud(
        screen,
        font,
        day,
        world.wood,
        world.stone,
        survival
    )

    #DRAW NOTIFICATION
    messages.draw_message(screen, font)

    #DISPLAY COMPLETED FRAME
    pygame.display.flip()