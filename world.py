
import pygame
from config import *

#IMAGES
pine_tree_image = None
oak_tree_image = None
tree_images = []
rock_image = None
berry_bush_image = None
water_image = None

def load_world_assets():
    global pine_tree_image, oak_tree_image, tree_images
    global rock_image, berry_bush_image, water_image

    pine_tree_image = pygame.image.load(
        "assets/environment/pine_tree.png"
    ).convert_alpha()

    oak_tree_image = pygame.image.load(
        "assets/environment/oak_tree.png"
    ).convert_alpha()

    tree_images = [
    oak_tree_image,
    pine_tree_image,
    oak_tree_image,
    pine_tree_image
    ]

    rock_image = pygame.image.load(
        "assets/environment/rock.png"
    ).convert_alpha()

    berry_bush_image = pygame.image.load(
        "assets/environment/berry_bush.png"
    ).convert_alpha()

    water_image = pygame.image.load(
        "assets/environment/pond.png"
    )

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
    scaled_water = pygame.transform.scale(
    water_image, (130, 95)
    )

    screen.blit(
        scaled_water, (water.centerx - 65, water.centery - 47)
    )

    # DRAW TREES
    for i, tree in enumerate(trees):
        tree_image = pygame.transform.scale(
            tree_images[i],
            (80, 90)
        )

        screen.blit(
            tree_image,
            (tree.centerx - 40, tree.bottom - 90)
        )

    # DRAW ROCKS
    for rock in rocks:
        scaled_rock = pygame.transform.scale(
            rock_image, (55, 45)
        )

        screen.blit(
            scaled_rock, (rock.centerx - 27, rock.bottom - 45)
        )

    # DRAW BERRY BUSHES
    for bush in berry_bushes:
        scaled_bush = pygame.transform.scale(
            berry_bush_image, (65, 55)
        )

        screen.blit(
            scaled_bush, (bush.centerx - 32, bush.bottom - 55)
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

