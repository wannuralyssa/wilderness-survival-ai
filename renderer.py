
import pygame
import world
import hud
import messages
import survival_system as survival
from config import *
import player as player_module
import wolves
import weather
import ai_agent

#THE CAMERA IS THE PART OF THE WORLD SHOWN ON SCREEN
camera = pygame.Rect(0, 0, WIDTH, HEIGHT)


def load_assets():
    #THE GRASS AND OTHER GROUND TEXTURES ARE NOW LOADED IN world.load_world_assets()
    pass


def update_camera(target_rect):
    #FOLLOW THE PLAYER, BUT NEVER SHOW ANYTHING OUTSIDE THE WORLD
    camera.center = target_rect.center
    camera.clamp_ip(pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT))


def draw_frame(screen, font, day, player_rect, player_direction, is_night, night_overlay, wolf_list, ai=None):
    update_camera(player_rect)
    offset = camera.topleft

    #DRAW FLAT GROUND (GRASS, PLATEAUS, WATER, CAMPFIRES)
    world.draw_ground(screen, camera)

    #COLLECT EVERYTHING THAT STANDS UP: TREES, ROCKS, BUSHES, LOGS, WOLVES, PLAYER
    #EACH ENTRY IS (Y OF ITS FEET, FUNCTION THAT DRAWS IT)
    drawables = []

    for sort_y, image, position in world.get_sprites(camera):
        drawables.append((sort_y, lambda image=image, position=position: screen.blit(image, position)))

    for wolf_data in wolf_list:
        drawables.append((
            wolf_data["rect"].bottom,
            lambda wolf_data=wolf_data: wolves.draw_wolf(screen, wolf_data, offset)
        ))

    drawables.append((
        player_rect.bottom,
        lambda: player_module.draw_player(screen, player_rect, player_direction, offset)
    ))

    #DRAW FROM TOP OF THE WORLD TO BOTTOM, SO WHATEVER IS IN FRONT COVERS WHAT IS BEHIND
    drawables.sort(key=lambda item: item[0])
    for _, draw in drawables:
        draw()

    #DRAW NIGHT, RAIN AND COLD (night_overlay IS NO LONGER USED: weather.py HANDLES DARKNESS)
    weather.draw(
        screen,
        camera,
        player_rect,
        wolf_list,
        [wolves.eye_positions(wolf_data) for wolf_data in wolf_list]
    )

    #AI MODE: SHOW THE AI'S PLAN AND WHAT IT IS THINKING
    if ai is not None:
        ai_agent.draw_overlay(screen, ai, camera, player_rect)

    #DRAW HUD (STATS, DAY, WEATHER AND RESOURCES)
    hud.draw_hud(
        screen,
        day,
        world.wood,
        world.stone,
        survival,
        weather,
        wolves.wolves_defeated
    )

    #DRAW NOTIFICATION
    messages.draw_message(screen, font)

    #DISPLAY COMPLETED FRAME
    pygame.display.flip()
