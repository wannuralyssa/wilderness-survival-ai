

import pygame


def create_player(x, y):
    return pygame.Rect(x, y, 40, 40)


def move_player(player, dx, dy, obstacles, width, height):
    #CALCULATE THE PLAYER'S POSSIBLE NEW POSITION
    moved_player = player.move(dx, dy)

    #KEEP THE PLAYER INSIDE THE WINDOW
    if moved_player.left < 0:
        moved_player.left = 0

    if moved_player.right > width:
        moved_player.right = width

    if moved_player.top < 0:
        moved_player.top = 0

    if moved_player.bottom > height:
        moved_player.bottom = height

    #CHECK FOR COLLISIONS
    for obstacle in obstacles:
        if moved_player.colliderect(obstacle):
            return player

    #UPDATE THE PLAYER'S POSITION
    return moved_player

def draw_player(screen, player_rect, direction = "down"):
    #PLAYER SHADOW
    pygame.draw.ellipse(
        screen, 
        (35, 45, 30),
        (player_rect.x + 5, player_rect.y + 31, 32, 9)
    )

    #BACKPACK
    if direction == "down":
        #Mostly hidden behind the body
        pygame.draw.rect(
            screen,
            (75, 105, 55),
            (player_rect.x + 10, player_rect.y + 14, 21, 17),
            border_radius = 4
        )
    elif direction == "up":
        #Fully visible from behind
        pygame.draw.rect(
            screen,
            (75, 105, 55),
            (player_rect.x + 8, player_rect.y + 13, 24, 19),
            border_radius = 4
        )
    elif direction == "left":
        pygame.draw.rect(
            screen,
            (75, 105, 55),
            (player_rect.x + 23, player_rect.y + 15, 10, 17),
            border_radius = 3
        )   
    elif direction == "right":
        pygame.draw.rect(
            screen,
            (75, 105, 55),
            (player_rect.x + 7, player_rect.y + 15, 10, 17),
            border_radius = 3
        )   

    #BODY/JACKET
    pygame.draw.rect(
        screen,
        (120, 75, 45),
        (player_rect.x + 10, player_rect.y + 16, 21, 17),
        border_radius = 4
    )

    #HEAD
    if direction == "down":
        pygame.draw.circle(
                screen,
                (220, 175, 135),
                (player_rect.centerx, player_rect.y + 10),
                9
            )
    elif direction == "up":
        pygame.draw.circle(
                screen,
                (65, 40, 30),
                (player_rect.centerx, player_rect.y + 10),
                9
            )    
    elif direction == "left":
        pygame.draw.circle(
                screen,
                (220, 175, 135),
                (player_rect.centerx - 3, player_rect.y + 10),
                9
            )
    elif direction == "right":
        pygame.draw.circle(
                screen,
                (220, 175, 135),
                (player_rect.centerx + 3, player_rect.y + 10),
                9
            )

    #HAIR
    if direction == "down":
         pygame.draw.arc(
                screen,
                (65, 40, 30),
                (player_rect.centerx - 9, player_rect.y, 18, 17),
                0, 3.14, 4
            )
    elif direction == "up":
          pygame.draw.circle(
                 screen,
                 (65, 40, 30),
                 (player_rect.centerx, player_rect.y + 10),
                 9
             )
    elif direction == "left":
          pygame.draw.arc(
                 screen,
                 (65, 40, 30),
                 (player_rect.centerx - 9, player_rect.y + 1, 18, 17),
                 -1.57, 1.57, 4
             )
    elif direction == "right":
         pygame.draw.arc(
                screen,
                (65, 40, 30),
                (player_rect.centerx - 9, player_rect.y + 1, 18, 17),
                1.57, 4.71, 4
            )

    #BOOTS
    pygame.draw.rect(
        screen,
        (45, 35, 30),
        (player_rect.x + 10, player_rect.y + 30, 8, 7),
        border_radius = 2
    )

    pygame.draw.rect(
        screen,
        (45, 35, 30),
        (player_rect.x + 23, player_rect.y + 30, 8, 7),
        border_radius = 2
    )
    
