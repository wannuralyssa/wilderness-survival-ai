

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

    #UODATE THE PLAYER'S POSITION
    return moved_player
