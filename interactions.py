import pygame
import world
import messages
import survival_system as survival
import weather

CAMPFIRE_WOOD_COST = 3
CAMPFIRE_STONE_COST = 2
RELIGHT_WOOD_COST = 1
TENT_WOOD_COST = 4


def craft_campfire(player_rect):
    #YOU CAN'T START A FIRE IN THE POURING RAIN
    if weather.current == weather.RAIN:
        messages.show_message("It's too wet to light a fire!", 1500)
        return

    if world.wood >= CAMPFIRE_WOOD_COST and world.stone >= CAMPFIRE_STONE_COST:
        #BUILD IT JUST IN FRONT OF THE PLAYER'S FEET, SO IT ISN'T HIDDEN UNDER THEM
        campfire = pygame.Rect(0, 0, 30, 30)
        campfire.midtop = (player_rect.centerx, player_rect.bottom + 6)
        if campfire.collidelist(world.obstacles) != -1:
            messages.show_message("Not enough space here for a campfire!", 1500)
            return

        world.wood -= CAMPFIRE_WOOD_COST
        world.stone -= CAMPFIRE_STONE_COST
        world.add_campfire(campfire)

        messages.show_message("Campfire crafted!")
    else:
        messages.show_message(f"Need {CAMPFIRE_WOOD_COST} wood and {CAMPFIRE_STONE_COST} stone!")


def craft_tent(player_rect):
    #A TENT IS SHELTER FROM RAIN AND COLD: STAND INSIDE IT
    if world.wood < TENT_WOOD_COST:
        messages.show_message(f"Need {TENT_WOOD_COST} wood to build a tent!", 1500)
        return

    tent = pygame.Rect(0, 0, 64, 40)
    tent.midbottom = (player_rect.centerx, player_rect.bottom + 4)

    if tent.collidelist(world.obstacles) != -1:
        messages.show_message("Not enough space here for a tent!", 1500)
        return

    world.wood -= TENT_WOOD_COST
    world.tents.append(tent)
    messages.show_message("Tent built! Stand inside it to shelter.", 2500)


def rest_at_campfire():
    if survival.energy < 100:
        survival.energy = min(survival.energy + 30, 100)
        messages.show_message("You rested by the campfire! 30 energy restored.")
    else:
        messages.show_message("You are already fully rested!")


def relight_campfire(index):
    if weather.current == weather.RAIN:
        messages.show_message("Too wet to relight! Wait for the rain to stop.", 2000)
    elif world.wood >= RELIGHT_WOOD_COST:
        world.wood -= RELIGHT_WOOD_COST
        world.campfire_lit[index] = True
        messages.show_message(f"You relit the campfire! (-{RELIGHT_WOOD_COST} wood)", 1500)
    else:
        messages.show_message(f"Need {RELIGHT_WOOD_COST} wood to relight the campfire!", 1500)


def interact_with_world(player_rect):

    # CHECK CAMPFIRES (REST AT A BURNING ONE, RELIGHT A PUT-OUT ONE)
    for i, campfire in enumerate(world.campfires):
        if player_rect.colliderect(campfire.inflate(50, 50)):
            if world.campfire_lit[i]:
                rest_at_campfire()
            else:
                relight_campfire(i)
            return

    # CHECK WATER (PONDS AND THE RIVER)
    if world.near_water(player_rect):
        survival.drink_water()
        messages.show_message("You drank fresh water! Thirst decreased.")
        return

    # CHECK BERRY BUSHES
    for bush in world.berry_bushes:
        if player_rect.colliderect(bush.inflate(40, 40)):
            survival.eat_berries()
            messages.show_message("You ate wild berries! Hunger decreased.")
            return

    # CHECK TREES (HARVESTED TREES GROW BACK AFTER A WHILE)
    for i, tree in enumerate(world.trees):
        if player_rect.colliderect(tree.inflate(40, 40)):
            if i not in world.collected_trees:
                world.wood += 1
                world.collect_tree(i)
                messages.show_message("You collected 1 wood!")
            else:
                messages.show_message("This tree needs time to grow back.")
            return

    # CHECK ROCKS (MINED ROCKS COME BACK AFTER A WHILE)
    for i, rock in enumerate(world.rocks):
        if player_rect.colliderect(rock.inflate(40, 40)):
            if i not in world.collected_rocks:
                world.stone += 1
                world.collect_rock(i)
                messages.show_message("You collected 1 stone!")
            else:
                messages.show_message("This rock is mined out for now.")
            return

    # CHECK TENTS
    for tent in world.tents:
        if tent.collidepoint(player_rect.center):
            messages.show_message("You rest in your tent, safe from the weather.", 2000)
            return

    # NOTHING FOUND
    messages.show_message("Nothing to collect nearby!")
