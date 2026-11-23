
import pygame
import survival_system as survival
from config import *
import world
import hud
import player as player_module
import messages
import interactions
import harvest
import time_system
import renderer
import game_over as game_over_screen
import wolves
import weather
import menu
import ai_agent
import os
import game_clock
import difficulty
import audio
import pack_learning

pygame.init()

game_over = False
running = True
is_night = False

clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 17)

#SCALED: THE GAME IS ALWAYS DRAWN AT 800 x 600 AND STRETCHED (KEEPING ITS SHAPE) TO FILL
#THE WINDOW, SO IT CAN BE RESIZED OR MADE FULL SCREEN (F11) WITHOUT CHANGING ANY GAME CODE
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("Wilderness Survival AI Simulator")

#LOAD GAME ASSETS
audio.init()
renderer.load_assets()
world.load_world_assets()
player_module.load_player_frames()
hud.load_assets()
wolves.load_wolf_frames()
pack_learning.load()        #WHAT THE WOLVES REMEMBER ABOUT YOU FROM EARLIER GAMES

#IN-GAME TIME (GAME CLOCK, SO AI MODE CAN FAST-FORWARD)
start_time = game_clock.now()
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
player_speed = 3.5              #PIXELS PER FRAME (WAS 5)
move_carry = [0.0, 0.0]         #LEFTOVER FRACTIONS OF A PIXEL, SO SPEEDS LIKE 3.5 WORK

#ARROW KEYS OR WASD
KEYS_LEFT = (pygame.K_LEFT, pygame.K_a)
KEYS_RIGHT = (pygame.K_RIGHT, pygame.K_d)
KEYS_UP = (pygame.K_UP, pygame.K_w)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)


def toggle_fullscreen():
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        pass

#HOW THE RUN ENDED: "rescued" / "escaped" (VICTORY) OR WHAT KILLED YOU ("wolf", "cold", ...)
ending = None
endless = False             #AFTER A VICTORY YOU CAN KEEP GOING (C) FOR A HIGH SCORE
end_background = None       #THE LAST FRAME, SHOWN DIMMED BEHIND THE ENDING

#GAME MODE: False = YOU PLAY, True = THE AI PLAYS
ai_mode = False
ai = None
run_logged = False

#AI MODE FAST-FORWARD: HOW MANY GAME STEPS TO RUN FOR EACH FRAME DRAWN (KEYS 1-4)
SPEEDS = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 4, pygame.K_4: 8}
sim_speed = 1

def whole_pixels(fx, fy):
    #THE PLAYER'S RECT ONLY MOVES IN WHOLE PIXELS: KEEP THE LEFTOVER FRACTION FOR NEXT FRAME
    if fx == 0:
        move_carry[0] = 0.0
    if fy == 0:
        move_carry[1] = 0.0
    move_carry[0] += fx
    move_carry[1] += fy
    dx, dy = int(move_carry[0]), int(move_carry[1])
    move_carry[0] -= dx
    move_carry[1] -= dy
    return dx, dy


#RESTART GAME
def restart_game(mode=None):
    global player, day, days_survived
    global game_over, is_night
    global start_time, previous_elapsed_time
    global wolf_list
    global ai_mode, ai, run_logged
    global ending, endless, end_background

    #"play" = YOU PLAY, "ai" = WATCH THE AI SURVIVE, None = KEEP THE SAME MODE
    if mode is not None:
        ai_mode = mode == "ai"
        hud.show_hmm = ai_mode      #THE FORECAST PANEL STARTS OPEN WHEN WATCHING THE AI (H TOGGLES IT)
        hud.show_pack = ai_mode     #SO DOES THE WOLF PACK PANEL (G TOGGLES IT)
    #THE PACK LEARNS YOUR HABITS AND THE AI'S HABITS SEPARATELY
    wolves.LEARNING_MODE = "ai" if ai_mode else "play"
    pack_learning.save()
    if ai_mode:
        if ai is None:
            ai = ai_agent.Agent()
        ai.reset()
    run_logged = False
    ending = None
    endless = False
    end_background = None

    #RESET SURVIVAL STATS
    survival.reset_survival()

    #RESET WORLD
    world.reset_world()
    harvest.clear()

    #RESET PLAYER
    player = player_module.create_player(*world.PLAYER_START)

    #RESET DAY COUNTER
    day = 1
    days_survived = 0

    #RESET GAME STATE
    game_over = False
    is_night = False

    #RESET DAY/NIGHT TIMER
    start_time = game_clock.now()
    previous_elapsed_time = 0

    #RESET WOLVES
    wolf_list = wolves.create_wolves()

    #RESET WEATHER
    weather.reset()

    #DAY 1 DIFFICULTY
    difficulty.apply(1)

def log_ai_run():
    #SAVE EACH AI RUN (USEFUL FOR COMPARING VERSIONS OF THE AI, AND FOR MACHINE LEARNING LATER)
    header = "days_survived,wolves_defeated,decisions,outcome\n"
    try:
        rows = []
        if os.path.exists("ai_runs.csv"):
            with open("ai_runs.csv") as f:
                rows = f.read().splitlines()
        if not rows or rows[0].strip() != header.strip():
            #OLDER FILE WITHOUT THE OUTCOME COLUMN: ADD IT
            old = rows[1:] if rows else []
            with open("ai_runs.csv", "w") as f:
                f.write(header)
                for row in old:
                    f.write(row + ",\n")
        with open("ai_runs.csv", "a") as f:
            f.write(f"{days_survived},{wolves.wolves_defeated},{ai.decisions},{ending}\n")
    except OSError:
        pass


def open_menu():
    #SHOW THE MAIN MENU; RETURNS FALSE IF THE PLAYER CHOSE QUIT
    choice = menu.run(screen, clock)
    if choice == "quit":
        return False
    restart_game(choice)
    return True


#SHOW THE MAIN MENU FIRST
if not open_menu():
    running = False

def update_game(dt):
    #ONE STEP OF THE GAME (EVERYTHING EXCEPT DRAWING). IN AI MODE THIS CAN RUN SEVERAL
    #TIMES PER FRAME TO FAST-FORWARD.
    global day, days_survived, game_over, is_night, previous_elapsed_time
    global player, player_direction, player_is_moving, ending

    game_clock.advance(dt)
    was_night = is_night

    #UPDATE DAY/NIGHT CYCLE
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

    #HANDLE NEW DAY: THE WILDERNESS GETS HARSHER
    if day_changed:
        days_survived = day - 1
        if day == GOAL_DAYS + 1 and not endless:
            #VICTORY: YOU LASTED GOAL_DAYS FULL DAYS. A CAMPFIRE'S SMOKE BRINGS THE RESCUERS;
            #WITHOUT ONE YOU FIND YOUR OWN WAY OUT
            ending = "rescued" if world.lit_campfires() else "escaped"
            game_over = True
            audio.play("victory")
            pack_learning.save()
            return
        audio.play("birds")
        difficulty.apply(day)
        left = GOAL_DAYS + 1 - day
        if 0 < left <= 3 and not endless:
            messages.show_message(f"Day {day}: hold on, rescue may come in {left} day{'s' if left > 1 else ''}!", 3500)
        else:
            messages.show_message(f"Day {day}: it gets harsher ({difficulty.describe(day)})", 3500)

    #A WOLF HOWLS AS NIGHT FALLS
    if is_night and not was_night:
        audio.play("howl")
        wolves.start_howl(wolf_list)

    #INPUT: FROM THE AI, OR FROM THE KEYBOARD
    dx = 0
    dy = 0
    if ai_mode:
        #THE AI DECIDES WHAT TO "PRESS" THIS STEP
        controls = ai.update(player, player_direction, wolf_list)
        dx, dy = controls.dx, controls.dy
        for action in controls.actions:
            if action == "interact":
                interactions.interact_with_world(player)
            elif action == "campfire":
                interactions.craft_campfire(player)
            elif action == "tent":
                interactions.craft_tent(player)
            elif action == "attack":
                if wolves.player_attack(wolf_list, player, player_direction, survival):
                    player_module.start_attack()
    else:
        keys = pygame.key.get_pressed()

        if any(keys[k] for k in KEYS_LEFT):
            dx = -player_speed

        if any(keys[k] for k in KEYS_RIGHT):
            dx = player_speed

        if any(keys[k] for k in KEYS_UP):
            dy = -player_speed

        if any(keys[k] for k in KEYS_DOWN):
            dy = player_speed

    #SLOW DOWN ON MUD AND TALL GRASS, IN THE RAIN, AND WHEN EXHAUSTED (BOTH MODES)
    speed_factor = world.speed_multiplier(player) * weather.player_speed_factor()
    dx, dy = whole_pixels(dx * speed_factor, dy * speed_factor)

    if dx < 0:
        player_direction = "left"
    elif dx > 0:
        player_direction = "right"
    elif dy < 0:
        player_direction = "up"
    elif dy > 0:
        player_direction = "down"

    #MOVE THE PLAYER
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

    #FOOTSTEPS (SKIPPED WHILE THE AI FAST-FORWARDS, OR IT WOULD BE A RATTLE)
    if player_is_moving and not (ai_mode and sim_speed > 2):
        audio.footstep(abs(player.x - previous_x) + abs(player.y - previous_y),
                       world.terrain_at(player.centerx, player.bottom - 4))

    #MOVE THE WOLVES
    #HOLD E TO CHOP / MINE (THE AI "HOLDS" TOO). LETTING GO OR WALKING AWAY LOSES THE PROGRESS
    if ai_mode:
        holding = controls.hold
    else:
        holding = survival.is_alive and pygame.key.get_pressed()[pygame.K_e]
    facing = harvest.update(dt, holding, player)
    if facing:
        player_direction = facing       #FACE THE TREE / ROCK WHILE WORKING ON IT

    wolves.move_wolves(wolf_list, WORLD_WIDTH, WORLD_HEIGHT, player, world.obstacles)

    #WOLF ATTACK
    wolves.attack_player(wolf_list, player, survival, messages)

    #NIGHTFALL, RAIN AND COLD
    weather.update(dt, elapsed_time, is_night, player)

    #HUNGER AND THIRST RISE STEADILY; HEALTH SLOWLY COMES BACK WHEN FED, HYDRATED AND RESTED
    survival.drain_needs(dt, CYCLE_DURATION)
    survival.regenerate(dt, weather.player_near_fire or weather.player_sheltered)

    #TREES, ROCKS AND BUSHES GROW BACK, DEFEATED WOLVES ARE REPLACED
    world.update(game_clock.now())
    wolves.update_respawns(wolf_list, player)

    survival.check_death()
    if not survival.is_alive:
        game_over = True
        days_survived = day - 1
        ending = survival.last_cause
        audio.play("game_over")
        pack_learning.save()


#GAME LOOP
while running:

    #EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            #FULL SCREEN ON / OFF (THE GAME IS SCALED UP, KEEPING ITS SHAPE)
            toggle_fullscreen()
        elif event.type == pygame.KEYDOWN:
            if game_over:
                if event.key == pygame.K_c and ending in ("rescued", "escaped") and not endless:
                    #KEEP SURVIVING AFTER THE RESCUE, FOR A HIGHER SCORE
                    endless = True
                    game_over = False
                    end_background = None
                    difficulty.apply(day)
                    messages.show_message("Endless mode: how long can you last?", 3000)
                elif event.key == pygame.K_r:
                    restart_game()
                elif event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_m:
                    #BACK TO THE MAIN MENU
                    if not open_menu():
                        running = False
            elif event.key == pygame.K_g:
                #SHOW / HIDE THE WOLF PACK PANEL (GAME THEORY + MACHINE LEARNING)
                hud.show_pack = not hud.show_pack
            elif event.key == pygame.K_h:
                #SHOW / HIDE THE WEATHER FORECAST (HMM) PANEL
                hud.show_hmm = not hud.show_hmm
            elif event.key == pygame.K_v:
                #SOUND ON / OFF
                audio.toggle_mute()
            elif event.key == pygame.K_ESCAPE:
                #BACK TO THE MAIN MENU DURING A GAME
                if not open_menu():
                    running = False
            elif ai_mode:
                #THE AI IS IN CONTROL. KEYS 1-4 CHANGE THE SPEED (1x, 2x, 4x, 8x)
                if event.key in SPEEDS:
                    sim_speed = SPEEDS[event.key]
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

    dt = min(clock.tick(60), 50)     #CAP dt SO A SLOW FRAME DOESN'T JUMP TOO FAR

    #RUN THE GAME (SEVERAL STEPS PER FRAME WHEN THE AI IS FAST-FORWARDING)
    steps = sim_speed if ai_mode else 1
    for _ in range(steps):
        if game_over or not running:
            break
        update_game(dt)

    if game_over:
        player_is_moving = False

    #MUSIC FOR THE TIME OF DAY, AND RAIN / WIND / CAMPFIRE SOUNDS
    audio.update_world(weather, world, player, game_over and ending not in ("rescued", "escaped"))

    #UPDATE PLAYER ANIMATION
    player_module.update_player_animation(player_is_moving, player_direction, dt * steps)

    #RENDER GAME
    if game_over:
        if ai_mode and not run_logged:
            log_ai_run()
            run_logged = True
        if end_background is None:
            end_background = screen.copy()      #THE LAST FRAME OF THE RUN
        game_over_screen.draw_ending(screen, end_background, ending, days_survived, wolves.wolves_defeated,
                                     ai_mode, ending in ("rescued", "escaped") and not endless,
                                     pygame.time.get_ticks())
        pygame.display.flip()
    else:
        if ai_mode:
            ai.sim_speed = sim_speed
        renderer.draw_frame(
            screen,
            font,
            day,
            player,
            player_direction,
            is_night,
            night_overlay,
            wolf_list,
            ai if ai_mode else None
        )

pack_learning.save()
pygame.quit()
