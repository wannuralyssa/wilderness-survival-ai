#HOLD E TO CHOP A TREE OR MINE A ROCK (LIKE MINECRAFT)
#=====================================================
#PRESSING E NEXT TO A TREE OR ROCK NO LONGER GIVES WOOD / STONE STRAIGHT AWAY: YOU HOLD E
#WHILE THE PLAYER SWINGS, THE TREE OR ROCK SHAKES, CHIPS FLY AND A RING FILLS UP. LET GO
#OR WALK AWAY AND THE PROGRESS IS LOST. DRINKING, EATING AND RESTING ARE STILL ONE PRESS.
import math
import random
import pygame

import audio
import game_clock
import messages
import player as player_module
import world

HOLD_TIME = {"tree": 1600, "rock": 2200}        #MILLISECONDS OF HOLDING E
HIT_EVERY = 400                                 #A SWING (AND A CHOP / CLINK SOUND) THIS OFTEN
CHIP_COLOURS = {"tree": [(150, 100, 56), (196, 150, 96), (110, 150, 60)],
                "rock": [(150, 150, 156), (110, 110, 118), (190, 190, 196)]}

target = None           #("tree" OR "rock", INDEX) BEING WORKED ON, OR None
progress = 0            #MILLISECONDS HELD SO FAR
next_hit = 0
chips = []              #FLYING CHIPS: [X, Y, VX, VY, LIFE, COLOUR] IN WORLD COORDINATES


def harvest_target(player_rect):
    #THE TREE OR ROCK E WOULD WORK ON (THE SAME ORDER AS interactions.py), IF IT CAN BE HARVESTED
    for i, fire in enumerate(world.campfires):
        if player_rect.colliderect(fire.inflate(50, 50)):
            return None
    if world.near_water(player_rect):
        return None
    for bush in world.berry_bushes:
        if player_rect.colliderect(bush.inflate(40, 40)):
            return None
    for i, tree in enumerate(world.trees):
        if player_rect.colliderect(tree.inflate(40, 40)):
            return ("tree", i) if i not in world.collected_trees else None
    for i, rock in enumerate(world.rocks):
        if player_rect.colliderect(rock.inflate(40, 40)):
            return ("rock", i) if i not in world.collected_rocks else None
    return None


def target_rect(t):
    kind, i = t
    return world.trees[i] if kind == "tree" else world.rocks[i]


def reset():
    global target, progress
    target = None
    progress = 0
    world.harvest_shake = None


def clear():
    reset()
    chips.clear()


def update(dt, holding, player_rect):
    #CALL EVERY GAME STEP. holding = IS E (OR THE AI'S "HOLD") DOWN?
    #RETURNS THE DIRECTION THE PLAYER SHOULD FACE (TOWARDS THE TREE / ROCK), OR None
    global target, progress, next_hit
    _update_chips(dt)

    current = harvest_target(player_rect) if holding else None
    if current is None:
        reset()
        return None
    if current != target:
        #STARTED ON SOMETHING NEW: PROGRESS STARTS AGAIN
        target = current
        progress = 0
        next_hit = 0

    progress += dt
    kind, index = target
    rect = target_rect(target)

    #SWING, SOUND AND CHIPS EVERY HIT
    if progress >= next_hit:
        next_hit += HIT_EVERY
        player_module.start_attack()
        audio.play("chop" if kind == "tree" else "mine", 0.55)
        _spawn_chips(kind, rect, player_rect)

    #THE TREE / ROCK WOBBLES WHILE YOU WORK ON IT
    world.harvest_shake = (kind, index, round(math.sin(game_clock.now() / 25) * 1.5))

    dx, dy = rect.centerx - player_rect.centerx, rect.centery - player_rect.centery
    facing = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")

    if progress >= HOLD_TIME[kind]:
        _finish(kind, index, rect, player_rect)
    return facing


def _finish(kind, index, rect, player_rect):
    if kind == "tree":
        world.wood += 1
        world.collect_tree(index)
        audio.play("chop")
        messages.show_message("You collected 1 wood!")
    else:
        world.stone += 1
        world.collect_rock(index)
        audio.play("mine")
        messages.show_message("You collected 1 stone!")
    for _ in range(2):
        _spawn_chips(kind, rect, player_rect)
    reset()


def _spawn_chips(kind, rect, player_rect):
    #CHIPS FLY OUT FROM THE SIDE OF THE TREE / ROCK THAT FACES THE PLAYER
    side = 1 if player_rect.centerx > rect.centerx else -1
    x = rect.centerx + side * rect.width * 0.4
    y = rect.bottom - (30 if kind == "tree" else 12)
    for _ in range(5):
        chips.append([x, y, side * random.uniform(0.04, 0.12), random.uniform(-0.18, -0.08),
                      random.uniform(350, 600), random.choice(CHIP_COLOURS[kind])])


def _update_chips(dt):
    for chip in chips:
        chip[0] += chip[2] * dt
        chip[1] += chip[3] * dt
        chip[3] += 0.0006 * dt          #GRAVITY
        chip[4] -= dt
    chips[:] = [c for c in chips if c[4] > 0]


def draw(screen, camera):
    #CHIPS, AND A RING ABOVE THE TREE / ROCK THAT FILLS UP AS YOU HOLD E
    for x, y, vx, vy, life, colour in chips:
        pygame.draw.rect(screen, colour, (int(x - camera.x), int(y - camera.y), 3, 2))

    if target is None:
        return
    kind, _ = target
    rect = target_rect(target)
    fraction = min(1.0, progress / HOLD_TIME[kind])
    top = rect.bottom - (100 if kind == "tree" else 54)
    centre = (rect.centerx - camera.x, top - camera.y)

    radius = 11
    pygame.draw.circle(screen, (20, 24, 30), centre, radius + 3)
    pygame.draw.circle(screen, (70, 76, 84), centre, radius, 3)
    if fraction > 0:
        box = pygame.Rect(0, 0, radius * 2, radius * 2)
        box.center = centre
        colour = (196, 150, 96) if kind == "tree" else (190, 196, 206)
        start = math.pi / 2 - fraction * 2 * math.pi
        pygame.draw.arc(screen, colour, box, start, math.pi / 2, 4)
    #A LITTLE AXE / PICK MARK IN THE MIDDLE
    pygame.draw.line(screen, (230, 230, 230), (centre[0] - 3, centre[1] + 3), (centre[0] + 3, centre[1] - 3), 2)
