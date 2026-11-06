import pygame
import world
import messages
import survival_system as survival

def craft_campfire(player_rect):
    if world.wood >= 3 and world.stone >= 2:
        world.wood -= 3
        world.stone -= 2

        campfire = pygame.Rect(player_rect.centerx - 15, player_rect.centery - 15, 30, 30)
        world.campfires.append(campfire)

        messages.show_message("Campfire crafted!")
    else:
        messages.show_message("Need 3 wood and 2 stone!")

def rest_at_campfire():
    if survival.energy < 100:
        survival.energy = min(survival.energy + 30, 100)
        messages.show_message("You rested by the campfire! 30 energy restored.")
    else:
        messages.show_message("You are already fully rested!")


def interact_with_world(player_rect):

    # CHECK WATER
    if player_rect.colliderect(world.water.inflate(40, 40)):
        survival.drink_water()
        messages.show_message("You drank fresh water! Thirst decreased.")
        return

    # CHECK BERRY BUSHES
    for bush in world.berry_bushes:
        if player_rect.colliderect(bush.inflate(40, 40)):
            survival.eat_berries()
            messages.show_message("You ate wild berries! Hunger decreased.")
            return

    # CHECK TREES
    for i, tree in enumerate(world.trees):
        if player_rect.colliderect(tree.inflate(40, 40)):
            if i not in world.collected_trees:
                world.wood += 1
                world.collected_trees.append(i)
                messages.show_message("You collected 1 wood!")
            else:
                messages.show_message("This tree has no wood left.")
            return

    # CHECK ROCKS
    for i, rock in enumerate(world.rocks):
        if player_rect.colliderect(rock.inflate(40, 40)):
            if i not in world.collected_rocks:
                world.stone += 1
                world.collected_rocks.append(i)
                messages.show_message("You collected 1 stone!")
            else:
                messages.show_message("This rock has no stone left.")
            return

    # CHECK CAMPFIRES
    for campfire in world.campfires:
        if player_rect.colliderect(campfire.inflate(50, 50)):
            rest_at_campfire()
            return

    # NOTHING FOUND
    messages.show_message("Nothing to collect nearby!")
