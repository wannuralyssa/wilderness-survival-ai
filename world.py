
import pygame
from config import *

# CREATE TREES
trees = [
    pygame.Rect(100, 100, 40, 50),
    pygame.Rect(250, 180, 40, 50),
    pygame.Rect(600, 100, 40, 50),
    pygame.Rect(680, 400, 40, 50)
]

collected_trees = []
wood = 0

# CREATE ROCKS
rocks = [
    pygame.Rect(200, 400, 35, 30),
    pygame.Rect(500, 200, 35, 30),
    pygame.Rect(350, 450, 35, 30)
]

collected_rocks = []
stone = 0

# CREATE CAMPFIRES
campfires = []

# CREATE OBSTACLES
obstacles = trees + rocks

# CREATE BERRY BUSHES
berry_bushes = [
    pygame.Rect(150, 300, 35, 30),
    pygame.Rect(400, 150, 35, 30),
    pygame.Rect(700, 250, 35, 30)
]

# CREATE WATER SOURCE
water = pygame.Rect(550, 350, 100, 70)

# DRAW WORLD OBJECTS
def draw_world(screen):
    # DRAW WATER
    pygame.draw.rect(screen, WATER_COLOR, water)

    # DRAW TREES
    for tree in trees:
        pygame.draw.rect(screen, TRUNK_COLOR, tree)
        pygame.draw.circle(
            screen, TREE_COLOR, (tree.centerx, tree.y), 25
        )

    # DRAW ROCKS
    for rock in rocks:
        pygame.draw.ellipse(screen, ROCK_COLOR, rock)

    # DRAW BERRY BUSHES
    for bush in berry_bushes:
        pygame.draw.rect(screen, (30, 110, 40), bush)
        pygame.draw.circle(
            screen, (200, 30, 50), (bush.centerx - 8, bush.centery), 5
        )
        pygame.draw.circle(
            screen, (200, 30, 50), (bush.centerx + 8, bush.centery), 5
        )
        pygame.draw.circle(
            screen, (200, 30, 50), (bush.centerx, bush.centery - 8), 5
        )

    #DRAW CAMPFIRE
    for campfire in campfires:
        pygame.draw.circle(screen, (100, 100, 100), campfire.center, 16)
        pygame.draw.circle(screen, (255, 120, 20), campfire.center, 10)
        pygame.draw.circle(screen, (255, 220, 50), campfire.center, 5)

#RESET WORLD
def reset_world():
    global wood, stone

    collected_trees.clear()
    collected_rocks.clear()
    campfires.clear()
    wood = 0
    stone = 0

