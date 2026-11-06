
import pygame
import survival_system as survival

game_over = False
running = True
is_night = False
clock = pygame.time.Clock()

pygame.init()
font = pygame.font.SysFont("Arial", 17)

#SET UP THE GAME WINDOW
WIDTH = 800
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wilderness Survival AI Simulator")

#IN-GAME TIME
DAY_DURATION = 10000
NIGHT_DURATION = 10000
CYCLE_DURATION = DAY_DURATION + NIGHT_DURATION
start_time = pygame.time.get_ticks()
day = 1
previous_elapsed_time = 0

night_overlay = pygame.Surface((WIDTH, HEIGHT))
night_overlay.fill((10, 15, 50))
night_overlay.set_alpha(120)

#DEFINE COLORS
GRASS = (80, 160, 80)
PLAYER_COLOR = (220, 190, 140)
TREE_COLOR = (25, 100, 45)
TRUNK_COLOR = (110, 70, 35)
ROCK_COLOR = (120, 120, 120)
WATER_COLOR = (40, 130, 220)

#CREATE PLAYER
player = pygame.Rect(380, 280, 40, 40)
player_speed = 5

#CREATE TREES
trees = [
    pygame.Rect(100, 100, 40, 50),
    pygame.Rect(250, 180, 40, 50),
    pygame.Rect(600, 100, 40, 50),
    pygame.Rect(680, 400, 40, 50)
] 

collected_trees = []
wood = 0

#CREATE ROCKS
rocks = [
    pygame.Rect(200, 400, 35, 30),
    pygame.Rect(500, 200, 35, 30),
    pygame.Rect(350, 450, 35, 30)
    ]

collected_rocks = []
stone = 0

campfires = []

obstacles = trees + rocks

#CREATE BERRY BUSHES
berry_bushes = [
    pygame.Rect(150, 300, 35, 30),
    pygame.Rect(400, 150, 35, 30),
    pygame.Rect(700, 250, 35, 30)
]

#CREATE A WATER SOURCE
water = pygame.Rect(550, 350, 100, 70)

#IN-GAME MESSAGE VARIABLES
message_text = ""
message_start_time = 0
MESSAGE_DURATION = 1000

#FUNCTIONS
def craft_campfire():
    global wood, stone

    if wood >= 3 and stone >= 2:
        wood -= 3
        stone -= 2

        campfire = pygame.Rect(player.centerx - 15, player.centery - 15, 30, 30)
        campfires.append(campfire)

        show_message("Campfire crafted!")
    else:
        show_message("Need 3 wood and 2 stone!")

def rest_at_campfire():
    if survival.energy < 100:
        survival.energy = min(survival.energy + 30, 100)
        show_message("You rested by the campfire! 30 energy restored.")
    else:
        show_message("You are already fully rested!")


def show_message(text):
    global message_text, message_start_time

    message_text = text 
    message_start_time = pygame.time.get_ticks()

def draw_message():
    current_time = pygame.time.get_ticks()
    if current_time - message_start_time < MESSAGE_DURATION:
        text = font.render(message_text, True, (255, 255, 255))
        message_box = pygame.Rect(150, 520, 500, 45)
        pygame.draw.rect(screen, (40, 40, 40), message_box)
        screen.blit(text, (message_box.x + 15, message_box.y + 12))

def draw_bar(label, value, x, y, color):
    #draw the label
    text = font.render(f"{label}: {value}", True, (255, 255, 255))
    screen.blit(text, (x, y))

    #draw the background bar
    pygame.draw.rect(screen, (80, 80,80), (x, y + 22, 120, 8))

    #calculate the filled portion
    bar_width = int(value * 1.2)

    #draw the filled bar
    pygame.draw.rect(screen, color, (x, y + 22, bar_width, 8))

def draw_hud():
    #display current day
    day_text = font.render(f"Day {day}", True, (255, 255, 255))
    wood_text = font.render(f"Wood: {wood}", True, (255, 255, 255))
    stone_text = font.render(f"Stone: {stone}", True, (255, 255, 255))
    screen.blit(day_text, (20, 12))
    screen.blit(wood_text, (650, 20))
    screen.blit(stone_text, (650, 45))

    #display survival instinct
    draw_bar("Health", survival.health, 20, 42, (220, 60, 60))
    draw_bar("Hunger", survival.hunger, 20, 82, (230, 160, 40))
    draw_bar("Thirst", survival.thirst, 20, 122, (50, 150, 230))
    draw_bar("Energy", survival.energy, 20, 162, (60, 200, 100))

#GAME LOOP
while running:

    #EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if survival.is_alive:
                if event.key == pygame.K_e:
                    #CHECK WATER
                    if player.colliderect(water.inflate(40, 40)):
                        survival.drink_water()
                        show_message("You drank fresh water! Thirst decreased.")
                    else:
                        found_resource = False

                        #CHECK BERRY BUSHES
                        for bush in berry_bushes:
                            if player.colliderect(bush.inflate(40, 40)):
                                survival.eat_berries()
                                show_message("You ate wild berries! Hunger decreased.")
                                found_resource = True
                                break

                        #CHECK TREES
                        if not found_resource:
                            for i, tree in enumerate(trees):
                                if player.colliderect(tree.inflate(40,40)):
                                    found_resource = True
                                    if i not in collected_trees:
                                        wood += 1
                                        collected_trees.append(i)
                                        show_message("You collected 1 wood!")
                                    else:
                                        show_message("This tree has no wood left.")
                                    break

                        #CHECK ROCKS
                        if not found_resource:
                            for i, rock in enumerate(rocks):
                                if player.colliderect(rock.inflate(40, 40)):
                                    found_resource = True
                                    if i not in collected_rocks:
                                        stone += 1
                                        collected_rocks.append(i)
                                        show_message("You collected 1 stone!")
                                    else:
                                        show_message("This rock has no stone left.")
                                    break

                        #CHECK CAMPFIRES
                        if not found_resource:
                            for campfire in campfires:
                                if player.colliderect(campfire.inflate(50, 50)):
                                    rest_at_campfire()
                                    found_resource = True
                                    break

                        if not found_resource:
                            show_message("Nothing to collect nearby!")
    
                elif event.key == pygame.K_c:
                    craft_campfire()

    #CALCULATE WHETHER DAYTIME/NIGHTTIME
    if not game_over:
        elapsed_time = (pygame.time.get_ticks() - start_time) % CYCLE_DURATION
        is_night = elapsed_time >= DAY_DURATION

    if not game_over:
        if elapsed_time < previous_elapsed_time:
            day += 1
            survival.end_day()

            if not survival.is_alive:
                game_over = True
                is_night = False
                show_message("GAME OVER! Your survivor has died.")
            else:
                show_message(f"Day {day} begins!")

    previous_elapsed_time = elapsed_time
                                
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

    #CALCULATE THE PLAYER'S NEW POSSIBLE POSITION
    if not game_over:
        moved_player = player.move(dx, dy)

    #KEEP THE PLAYER INSIDE THE WINDOW
    if player.left < 0:
        moved_player.left = 0

    if player.right > WIDTH:
        moved_player.right = WIDTH

    if player.top < 0:
        moved_player.top = 0

    if player.bottom > HEIGHT:
        moved_player.bottom = HEIGHT

    #CHECK FOR COLLISIONS
    can_move = True

    for obstacle in obstacles:
        if moved_player.colliderect(obstacle):
            can_move = False
            break

    #UPDATE POSITION ONLY IF THERE IS NO COLLISION
    if can_move:
        player = moved_player

    #DRAW THE BACKGROUND
    screen.fill(GRASS)

    #DRAW WATER
    pygame.draw.rect(screen, WATER_COLOR, water)

    #DRAW TREES
    for tree in trees:
        pygame.draw.rect(screen, TRUNK_COLOR, tree)
        pygame.draw.circle(screen, TREE_COLOR, (tree.centerx, tree.y), 25)

    #DRAW ROCKS
    for rock in rocks:
        pygame.draw.ellipse(screen, ROCK_COLOR,rock)

    #DRAW BERRY BUSHES
    for bush in berry_bushes:
        pygame.draw.rect(screen, (30, 110, 40), bush)
        pygame.draw.circle(screen, (200, 30, 50), (bush.centerx - 8, bush.centery), 5)
        pygame.draw.circle(screen, (200, 30, 50), (bush.centerx + 8, bush.centery), 5)
        pygame.draw.circle(screen, (200, 30, 50), (bush.centerx, bush.centery - 8), 5)

    #DRAW CAMPFIRE
    for campfire in campfires:
        pygame.draw.circle(screen, (100, 100, 100), campfire.center, 16)
        pygame.draw.circle(screen, (255, 120, 20), campfire.center, 10)
        pygame.draw.circle(screen, (255, 220, 50), campfire.center, 5)

    #DRAW NIGHT EFFECT
    if is_night:
        screen.blit(night_overlay, (0, 0))

    #DRAW THE PLAYER
    pygame.draw.rect(screen, PLAYER_COLOR, player)

    #DRAW HUD
    draw_hud()

    #DRAW MESSAGE
    draw_message()

    #DISPLAY THE COMPLETED FRAME
    pygame.display.flip()

    #LIMIT THE GAME TO 60FPS
    clock.tick(60)

pygame.quit()





