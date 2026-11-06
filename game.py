
import pygame
import survival_system as survival
from config import *
import world
import hud
import player as player_module
import messages
import interactions
import time_system
import renderer

pygame.init()

game_over = False
running = True
is_night = False

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 17)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wilderness Survival AI Simulator")

#IN-GAME TIME
start_time = pygame.time.get_ticks()
day = 1
previous_elapsed_time = 0

night_overlay = pygame.Surface((WIDTH, HEIGHT))
night_overlay.fill((10, 15, 50))
night_overlay.set_alpha(120)

#CREATE PLAYER
player = player_module.create_player(380, 280)
player_speed = 5

#GAME LOOP
while running:

    #EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if survival.is_alive:
                if event.key == pygame.K_e:
                     interactions. interact_with_world(player)
                elif event.key == pygame.K_c:
                    interactions.craft_campfire(player)

    #UPDATE DAY/NIGHT CYCLE
    if not game_over:
        (
            elapsed_time,
            is_night,
            day,
            previous_elapsed_time,
            day_changed
        ) = time_system.update_day_cycle(
            start_time,
            previous_elapsed_time,
            day
        )

        #HANDLE NEW DAY
        if day_changed:
            survival.end_day()

            if not survival.is_alive:
                game_over = True
                is_night = False
                messages.show_message("GAME OVER! Your survivor has died.")
            else:
                messages.show_message(f"Day {day} begins!")

                                
    #CHECK KEYBOARD INPUT
    dx = 0
    dy = 0

    if not game_over:
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            dx = -player_speed

        if keys[pygame.K_RIGHT]:
            dx = player_speed

        if keys[pygame.K_UP]:
            dy = -player_speed

        if keys[pygame.K_DOWN]:
            dy = player_speed

    #MOVE THE PLAYER
    if not game_over:
        player = player_module.move_player(
            player,
            dx,
            dy,
            world.obstacles,
            WIDTH,
            HEIGHT
        )
       
    #RENDER GAME
    renderer.draw_frame(
        screen,
        font,
        day,
        player,
        is_night,
        night_overlay
    )

    #LIMIT THE GAME TO 60FPS
    clock.tick(60)

pygame.quit()
