
import pygame
import random
import math
import survival_system
import messages
import search
import world


def create_wolves():
    wolf_list = [
        {
            "rect": pygame.Rect(150, 150, 40, 30),
            "direction": (0, 0),
            "move_timer": 0,
            "attack_timer": 0,
            "path": [],
            "path_index": 0,
            "path_timer": 0
        }
    ]

    return wolf_list


def move_wolves(wolves, width, height, player, obstacles):
    for wolf_data in wolves:

        wolf = wolf_data["rect"]

        #CHECK IF WOLF DETECTS THE PLAYER
        if detect_player(wolf, player):
            #RECALCULATE THE PATH EVERY 30 FRAMES
            if wolf_data["path_timer"] <= 0:
                wolf_data["path"] = find_wolf_path(
                    wolf, player, obstacles
                )
                wolf_data["path_index"] = 1
                wolf_data["path_timer"] = 30
            wolf_data["path_timer"] -= 1
            path = wolf_data["path"]

            if path and wolf_data["path_index"] < len(path):
                row, col = path[wolf_data["path_index"]]
                target_x = col * 40 + 20
                target_y = row * 40 + 20
                dx = target_x - wolf.centerx
                dy = target_y - wolf.centery
                distance = math.hypot(dx, dy)

                if distance <= 3:
                    wolf_data["path_index"] += 1
                elif distance > 0:
                    wolf.x += round((dx / distance) * 2)
                    wolf.y += round((dy / distance) * 2)
        else:
            #RANDOM WANDERING
            if wolf_data["move_timer"] <= 0:
                wolf_data["direction"] = random.choice([
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1),
                ])

                wolf_data["move_timer"] = random.randint(30, 90)

            wolf_data["move_timer"] -= 1
            dx, dy = wolf_data["direction"]
            wolf.x += dx * 2
            wolf.y += dy * 2

        #KEEP WOLF INSIDE SCREEN
        wolf.clamp_ip(pygame.Rect(0, 0, width, height))

def attack_player(wolves, player, survival, messages):
    for wolf_data in wolves:
        wolf = wolf_data["rect"]

        #CHECK IF WOLF IS CLOSE ENOUGH TO ATTACK
        if wolf.colliderect(player):
            #ATTACK ONLY WHEN COOLDOWN REACHES ZERO
            if wolf_data["attack_timer"] <= 0:
                survival.wolf_attack()
                messages.show_message(" A wolf attacked you! -20 Health")
                survival.check_death()
                #WAIT 2 SECONDS BEFORE ATTACKING AGAIN
                wolf_data ["attack_timer"] = 120
            #REDUCE ATTACK COOLDOWN
            if wolf_data["attack_timer"] > 0:
                wolf_data["attack_timer"] -= 1



def detect_player(wolf, player, detection_range = 180):
    distance = math.hypot(
        wolf.centerx - player.centerx,
        wolf.centery - player.centery
    )
    return distance <= detection_range

def find_wolf_path(wolf, player, obstacles):
    cell_size = 40
    grid = search.create_grid(800, 600, cell_size, obstacles)
    start = (wolf.centery // cell_size, wolf.centerx // cell_size)
    goal = (player.centery // cell_size, player.centerx // cell_size)
    return search.bfs(grid, start, goal)

def draw_wolves(screen, wolves):
    for wolf_data in wolves:

        wolf = wolf_data["rect"]

        #BODY
        pygame.draw.ellipse(
            screen,
            (100, 100, 100),
            (wolf.x, wolf.y + 8, 30, 18)
        )

        #HEAD
        pygame.draw.circle(
            screen,
            (120, 120, 120),
            (wolf.x + 30, wolf.y + 10),
            10
        )

        #EARS
        pygame.draw.polygon(
            screen,
            (80, 80, 80),
            [
                (wolf.x + 23, wolf.y + 3),
                (wolf.x + 25, wolf.y - 7),
                (wolf.x + 30, wolf.y + 3)
            ]
        )

        pygame.draw.polygon(
            screen,
            (80, 80, 80),
            [
                (wolf.x + 32, wolf.y + 3),
                (wolf.x + 38, wolf.y - 7),
                (wolf.x + 39, wolf.y + 7)
            ]
        )

        #EYE
        pygame.draw.circle(
            screen,
            (255, 220, 50),
            (wolf.x + 33, wolf.y + 8),
            2
        )
