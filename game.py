
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
import game_over as game_over_screen
import wolves

pygame.init()

game_over = False
running = True
is_night = False

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 17)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wilderness Survival AI Simulator")

#LOAD GAME ASSETS
renderer.load_assets()
world.load_world_assets()

#IN-GAME TIME
start_time = pygame.time.get_ticks()
day = 1
days_survived = 0
previous_elapsed_time = 0

night_overlay = pygame.Surface((WIDTH, HEIGHT))
night_overlay.fill((10, 15, 50))
night_overlay.set_alpha(120)

#CREATE PLAYER
player = player_module.create_player(380, 280)
wolf_list = wolves.create_wolves()
player_direction = "down"
player_speed = 5

#RESTART GAME
def restart_game():
    global player, day, days_survived
    global game_over, is_night
    global start_time, previous_elapsed_time
    global wolf_list

    #RESET SURVIVAL STATS
    survival.reset_survival()

    #RESET WORLD
    world.reset_world()

    #RESET PLAYER
    player = player_module.create_player(380, 280)

    #RESET DAY COUNTER
    day = 1
    days_survived = 0

    #RESET GAME STATE
    game_over = False
    is_night = False

    #RESET DAY/NIGHT TIMER
    start_time = pygame.time.get_ticks()
    previous_elapsed_time = 0

    #RESET WOLVES
    wolf_list = wolves.create_wolves()

#GAME LOOP
while running:

    #EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if game_over:
                if event.key == pygame.K_r:
                    restart_game()
                elif event.key == pygame.K_q:
                    running = False
            elif survival.is_alive:
                if event.key == pygame.K_e:
                     interactions.interact_with_world(player)
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
            days_survived = day - 1

            if not survival.is_alive:
                game_over = True
                is_night = False
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

        if dx < 0:
            player_direction = "left"
        elif dx > 0:
            player_direction = "right"
        elif dy < 0:
            player_direction = "up"
        elif dy > 0: 
            player_direction = "down"

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

        #MOVE THE WOLVES
        wolves.move_wolves(wolf_list, WIDTH, HEIGHT, player)

        #WOLF ATTACK
        wolves.attack_player(wolf_list, player, survival, messages)

        if not survival.is_alive:
            game_over = True
            dyas_survived = day - 1

               
    #RENDER GAME
    if game_over:
        screen.fill((20, 20, 20))
        game_over_screen.gameover(screen, font, days_survived)
        pygame.display.flip()
    else:
        renderer.draw_frame(
            screen,
            font,
            day,
            player,
            player_direction,
            is_night,
            night_overlay,
            wolf_list
        )

    #LIMIT THE GAME TO 60FPS
    clock.tick(60)

pygame.quit()
