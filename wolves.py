
import pygame
import random
import math


def create_wolves():
    wolf_list = [
        {
            "rect": pygame.Rect(150, 150, 40, 30),
            "direction": (0, 0),
            "move_timer": 0
        }
    ]

    return wolf_list


def move_wolves(wolves, width, height, player):
    for wolf_data in wolves:

        wolf = wolf_data["rect"]

        #CHECK IF WOLF DETECTS THE PLAYER
        if detect_player(wolf, player):
            dx = player.centerx - wolf.centerx
            dy = player.centery - wolf.centery
            distance = math.hypot(dx, dy)

            #MOVE TOWARDS THE PLAYER
            if distance > 0:
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

def detect_player(wolf, player, detection_range = 180):
    distance = math.hypot(
        wolf.centerx - player.centerx,
        wolf.centery - player.centery
    )
    return distance <= detection_range


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
