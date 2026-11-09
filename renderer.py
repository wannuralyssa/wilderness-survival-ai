
import pygame
import world
import hud
import messages
import survival_system as survival
from config import *
import player as player_module

grass_texture = None

def load_assets():
    global grass_texture
    grass_texture = pygame.image.load(
        "assets/environment/grass.png"
    ).convert()

def draw_frame(screen, font, day, player_rect, is_night, night_overlay):
    #DRAW BACKGROUND
    tile_size = 128

    small_grass = pygame.transform.scale(
        grass_texture,
        (tile_size, tile_size)
    )

    for x in range(0, WIDTH, tile_size):
        for y in range(0, HEIGHT, tile_size):
            screen.blit(small_grass, (x, y))

    #DRAW WORLD OBJECTS
    world.draw_world(screen)

    #DRAW NIGHT EFFECT
    if is_night:
        screen.blit(night_overlay, (0, 0))

    #DRAW PLAYER
    player_module.draw_player(screen, player_rect)

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