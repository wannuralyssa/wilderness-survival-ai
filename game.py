
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
import weather
import menu

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
player_module.load_player_frames()
hud.load_assets()
wolves.load_wolf_frames()

#IN-GAME TIME
start_time = pygame.time.get_ticks()
day = 1
days_survived = 0
previous_elapsed_time = 0

night_overlay = pygame.Surface((WIDTH, HEIGHT))
night_overlay.fill((10, 15, 50))
night_overlay.set_alpha(120)

#CREATE PLAYER
player = player_module.create_player(*world.PLAYER_START)
wolf_list = wolves.create_wolves()
player_direction = "down"
player_is_moving = False
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
    player = player_module.create_player(*world.PLAYER_START)

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

    #RESET WEATHER
    weather.reset()

#SHOW THE MAIN MENU FIRST
if menu.run(screen, clock) == "quit":
    running = False
else:
    restart_game()

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
                elif event.key == pygame.K_m:
                    #BACK TO THE MAIN MENU
                    if menu.run(screen, clock) == "quit":
                        running = False
                    else:
                        restart_game()
            elif survival.is_alive:
                if event.key == pygame.K_e:
                     interactions.interact_with_world(player)
                elif event.key == pygame.K_c:
                    interactions.craft_campfire(player)
                elif event.key == pygame.K_t:
                    interactions.craft_tent(player)
                elif event.key == pygame.K_SPACE:
                    #SWING AT WHATEVER IS IN FRONT OF THE PLAYER
                    if wolves.player_attack(wolf_list, player, player_direction, survival):
                        player_module.start_attack()
            

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
    dt = clock.tick(60)
    

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

        #SLOW DOWN ON MUD AND TALL GRASS, IN THE RAIN, AND WHEN EXHAUSTED
        speed_factor = world.speed_multiplier(player) * weather.player_speed_factor()
        dx = round(dx * speed_factor)
        dy = round(dy * speed_factor)

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
        #REMEMBER THE PLAYER'S PREVIOUS POSITION
        previous_x = player.x
        previous_y = player.y

        player = player_module.move_player(
            player,
            dx,
            dy, 
            world.obstacles,
            WORLD_WIDTH,
            WORLD_HEIGHT
        )

        #CHECK WHETHER THE PLAYER ACTUALLY MOVED
        player_is_moving = (
            player.x != previous_x or
            player.y != previous_y
        )

        #MOVE THE WOLVES
        wolves.move_wolves(wolf_list, WORLD_WIDTH, WORLD_HEIGHT, player, world.obstacles)

        #WOLF ATTACK
        wolves.attack_player(wolf_list, player, survival, messages)

        #NIGHTFALL, RAIN AND COLD
        weather.update(dt, elapsed_time, is_night, player)

        #HEALTH SLOWLY COMES BACK WHEN FED, HYDRATED AND RESTED
        survival.regenerate(dt, weather.player_near_fire or weather.player_sheltered)

        #TREES AND ROCKS GROW BACK, DEFEATED WOLVES ARE REPLACED
        world.update(pygame.time.get_ticks())
        wolves.update_respawns(wolf_list, player)

        if not survival.is_alive:
            game_over = True
            days_survived = day - 1
    else:
        player_is_moving = False

    #UPDATE PLAYER ANIMATION
    player_module.update_player_animation(player_is_moving, player_direction, dt)


               
    #RENDER GAME
    if game_over:
        screen.fill((20, 20, 20))
        game_over_screen.gameover(screen, font, days_survived, wolves.wolves_defeated)
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

pygame.quit()
