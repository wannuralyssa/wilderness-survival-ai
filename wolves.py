
import pygame
import random
import math
import survival_system
import messages
import search
import world
import weather

#WOLF SPRITES
WOLF_ANIMATION_SPEED = 8      #FRAMES BETWEEN WALK FRAMES
WOLF_DIRECTIONS = ["down", "left", "right", "up"]
WOLF_WALK_FRAMES = [1, 2, 3, 2]
WOLF_SPEED = 2                #PIXELS PER FRAME ON NORMAL GRASS

#COMBAT
WOLF_MAX_HEALTH = 3           #HITS NEEDED TO DEFEAT A WOLF
WOLF_STUN_FRAMES = 40         #A HIT WOLF CAN'T MOVE OR BITE FOR THIS LONG
WOLF_RESPAWN_TIME = 30000     #A DEFEATED WOLF IS REPLACED AFTER 30 SECONDS
RESPAWN_MIN_DISTANCE = 600    #NEW WOLVES APPEAR FAR AWAY FROM THE PLAYER
PLAYER_ATTACK_COOLDOWN = 400  #MILLISECONDS BETWEEN SWINGS
PLAYER_ATTACK_ENERGY = 1      #EACH SWING COSTS THIS MUCH ENERGY

wolf_frames = {
    "down": [],
    "left": [],
    "right": [],
    "up": []
}

#RED-TINTED FRAMES SHOWN FOR A MOMENT WHEN A WOLF IS HIT
wolf_hit_frames = {
    "down": [],
    "left": [],
    "right": [],
    "up": []
}

respawn_times = []            #WHEN EACH DEFEATED WOLF WILL BE REPLACED
last_player_attack = -10000
wolves_defeated = 0


def load_wolf_frames():
    #CALL THIS AFTER pygame.display.set_mode()
    for direction in WOLF_DIRECTIONS:
        wolf_frames[direction] = []
        for i in range(4):
            image = pygame.image.load(
                f"assets/wolf/frames/wolf_{direction}_{i}.png"
            ).convert_alpha()
            wolf_frames[direction].append(image)

            hit_image = image.copy()
            hit_image.fill((110, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            wolf_hit_frames[direction].append(hit_image)


#WHERE WOLVES START (SET IN map_layout.py)
WOLF_SPAWNS = world.layout.WOLF_SPAWNS


def make_wolf(x, y):
    return {
        "rect": pygame.Rect(x, y, 40, 30),
        "direction": (0, 0),
        "move_timer": 0,
        "attack_timer": 0,
        "path": [],
        "path_index": 0,
        "path_timer": 0,
        "facing": "right",
        "is_moving": False,
        "anim_timer": 0,
        "walk_index": 0,
        "fx": float(x),
        "fy": float(y),
        "health": WOLF_MAX_HEALTH,
        "stun_timer": 0,
        "flash_timer": 0,
        "knock_vx": 0.0,
        "knock_vy": 0.0
    }


def create_wolves():
    global last_player_attack, wolves_defeated
    respawn_times.clear()
    last_player_attack = -10000
    wolves_defeated = 0
    return [make_wolf(x, y) for x, y in WOLF_SPAWNS]


def move_wolves(wolves, width, height, player, obstacles):
    for wolf_data in wolves:

        wolf = wolf_data["rect"]
        old_x, old_y = wolf.x, wolf.y

        #A HIT WOLF IS KNOCKED BACK AND STUNNED FOR A MOMENT
        if wolf_data["stun_timer"] > 0:
            wolf_data["stun_timer"] -= 1
            wolf_data["flash_timer"] = max(0, wolf_data["flash_timer"] - 1)
            knock_back(wolf_data, obstacles)
            wolf.clamp_ip(pygame.Rect(0, 0, width, height))
            update_wolf_animation(wolf_data, 0, 0)
            continue

        #CHECK IF WOLF DETECTS THE PLAYER
        distance_to_player = math.hypot(wolf.centerx - player.centerx, wolf.centery - player.centery)
        if distance_to_player < 60:
            #CLOSE ENOUGH TO LUNGE STRAIGHT AT THE PLAYER
            speed = WOLF_SPEED * world.speed_multiplier(wolf)
            dx = player.centerx - wolf.centerx
            dy = player.centery - wolf.centery
            saved = (wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"])
            step_wolf(wolf_data, dx / max(1, distance_to_player) * speed,
                      dy / max(1, distance_to_player) * speed)
            if wolf.collidelist(obstacles) != -1:
                wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"] = saved
        elif detect_player(wolf, player, weather.wolf_detection_range()):
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
                    #SLOWER IN MUD AND TALL GRASS
                    speed = WOLF_SPEED * world.speed_multiplier(wolf)
                    step_wolf(wolf_data, dx / distance * speed, dy / distance * speed)
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
            speed = WOLF_SPEED * world.speed_multiplier(wolf)

            was_blocked = wolf.collidelist(obstacles) != -1
            saved = (wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"])
            step_wolf(wolf_data, dx * speed, dy * speed)

            #DON'T WANDER INTO TREES, ROCKS, LOGS OR WATER: TURN AROUND INSTEAD
            if not was_blocked and wolf.collidelist(obstacles) != -1:
                wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"] = saved
                wolf_data["move_timer"] = 0

        #KEEP WOLF INSIDE SCREEN
        wolf.clamp_ip(pygame.Rect(0, 0, width, height))

        #UPDATE FACING DIRECTION AND WALK ANIMATION
        update_wolf_animation(wolf_data, wolf.x - old_x, wolf.y - old_y)


def knock_back(wolf_data, obstacles):
    #SLIDE THE WOLF AWAY FROM THE PLAYER, SLOWING DOWN EACH FRAME, WITHOUT GOING THROUGH OBSTACLES
    wolf = wolf_data["rect"]
    saved = (wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"])
    step_wolf(wolf_data, wolf_data["knock_vx"], wolf_data["knock_vy"])
    if wolf.collidelist(obstacles) != -1:
        wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"] = saved
        wolf_data["knock_vx"] = wolf_data["knock_vy"] = 0.0
    wolf_data["knock_vx"] *= 0.8
    wolf_data["knock_vy"] *= 0.8


def attack_area(player_rect, direction):
    #THE AREA IN FRONT OF THE PLAYER THAT A SWING HITS
    area = pygame.Rect(0, 0, 60, 60)
    if direction == "left":
        area.midright = (player_rect.centerx, player_rect.centery)
    elif direction == "right":
        area.midleft = (player_rect.centerx, player_rect.centery)
    elif direction == "up":
        area.midbottom = (player_rect.centerx, player_rect.centery)
    else:
        area.midtop = (player_rect.centerx, player_rect.centery)
    return area


def player_attack(wolves, player_rect, direction, survival):
    #THE PLAYER SWINGS AT WHATEVER IS IN FRONT OF THEM. RETURNS TRUE IF THE SWING HAPPENED
    global last_player_attack, wolves_defeated

    now = pygame.time.get_ticks()
    if now - last_player_attack < PLAYER_ATTACK_COOLDOWN:
        return False
    if survival.energy < PLAYER_ATTACK_ENERGY:
        messages.show_message("Too exhausted to fight!", 1200)
        return False

    last_player_attack = now
    survival.energy -= PLAYER_ATTACK_ENERGY
    area = attack_area(player_rect, direction)

    for wolf_data in list(wolves):
        wolf = wolf_data["rect"]
        if not area.colliderect(wolf):
            continue

        wolf_data["health"] -= 1
        if wolf_data["health"] <= 0:
            wolves.remove(wolf_data)
            respawn_times.append(now + WOLF_RESPAWN_TIME)
            wolves_defeated += 1
            messages.show_message("You defeated a wolf!", 1500)
            continue

        #KNOCK THE WOLF BACK, AWAY FROM THE PLAYER
        dx = wolf.centerx - player_rect.centerx
        dy = wolf.centery - player_rect.centery
        distance = max(1, math.hypot(dx, dy))
        wolf_data["knock_vx"] = dx / distance * 7
        wolf_data["knock_vy"] = dy / distance * 7
        wolf_data["stun_timer"] = WOLF_STUN_FRAMES
        wolf_data["flash_timer"] = 10
        wolf_data["attack_timer"] = max(wolf_data["attack_timer"], 60)

    return True


def update_respawns(wolves, player_rect):
    #REPLACE DEFEATED WOLVES SO THE FOREST NEVER RUNS OUT OF THEM
    now = pygame.time.get_ticks()
    for due in [t for t in respawn_times if now >= t]:
        #PICK THE SPAWN POINT FARTHEST FROM THE PLAYER (MUST BE FAR ENOUGH AWAY)
        spawns = sorted(
            WOLF_SPAWNS,
            key=lambda p: -math.hypot(p[0] - player_rect.centerx, p[1] - player_rect.centery)
        )
        x, y = spawns[0]
        if math.hypot(x - player_rect.centerx, y - player_rect.centery) < RESPAWN_MIN_DISTANCE:
            continue    #TRY AGAIN NEXT FRAME, WHEN THE PLAYER HAS MOVED AWAY
        respawn_times.remove(due)
        wolves.append(make_wolf(x, y))


def step_wolf(wolf_data, vx, vy):
    #MOVE WITH SUB-PIXEL PRECISION SO SLOW SPEEDS (BELOW 1 PX PER FRAME) STILL WORK
    wolf = wolf_data["rect"]

    #RESYNC IF THE RECT WAS MOVED ELSEWHERE (E.G. CLAMPED TO THE SCREEN)
    if abs(wolf_data["fx"] - wolf.x) > 1 or abs(wolf_data["fy"] - wolf.y) > 1:
        wolf_data["fx"] = float(wolf.x)
        wolf_data["fy"] = float(wolf.y)

    wolf_data["fx"] += vx
    wolf_data["fy"] += vy
    wolf.x = round(wolf_data["fx"])
    wolf.y = round(wolf_data["fy"])


def update_wolf_animation(wolf_data, moved_x, moved_y):
    wolf_data["is_moving"] = moved_x != 0 or moved_y != 0

    if wolf_data["is_moving"]:
        if abs(moved_x) >= abs(moved_y):
            wolf_data["facing"] = "right" if moved_x > 0 else "left"
        else:
            wolf_data["facing"] = "down" if moved_y > 0 else "up"

        wolf_data["anim_timer"] += 1
        if wolf_data["anim_timer"] >= WOLF_ANIMATION_SPEED:
            wolf_data["anim_timer"] = 0
            wolf_data["walk_index"] = (wolf_data["walk_index"] + 1) % len(WOLF_WALK_FRAMES)
    else:
        wolf_data["anim_timer"] = 0
        wolf_data["walk_index"] = 0

def attack_player(wolves, player, survival, messages):
    for wolf_data in wolves:
        wolf = wolf_data["rect"]

        #REDUCE ATTACK COOLDOWN
        if wolf_data["attack_timer"] > 0:
            wolf_data["attack_timer"] -= 1

        #A STUNNED WOLF CAN'T BITE
        if wolf_data["stun_timer"] > 0:
            continue

        #CHECK IF WOLF IS CLOSE ENOUGH TO ATTACK
        if wolf.colliderect(player):
            #ATTACK ONLY WHEN COOLDOWN REACHES ZERO
            if wolf_data["attack_timer"] <= 0:
                survival.wolf_attack()
                messages.show_message(f"A wolf attacked you! -{survival.WOLF_DAMAGE} Health")
                survival.check_death()
                #WAIT 2 SECONDS BEFORE ATTACKING AGAIN
                wolf_data["attack_timer"] = 120

def detect_player(wolf, player, detection_range = 180):
    distance = math.hypot(
        wolf.centerx - player.centerx,
        wolf.centery - player.centery
    )
    return distance <= detection_range

def find_wolf_path(wolf, player, obstacles):
    #A* SEARCH: FINDS THE CHEAPEST ROUTE, AVOIDING MUD AND TALL GRASS WHEN A DETOUR IS CHEAPER
    cell_size = world.CELL_SIZE
    grid = world.get_cost_grid()
    start = (wolf.centery // cell_size, wolf.centerx // cell_size)
    goal = (player.centery // cell_size, player.centerx // cell_size)
    return search.a_star(grid, start, goal)

def draw_wolf(screen, wolf_data, offset=(0, 0)):
    #offset = CAMERA POSITION (WORLD COORDINATES -> SCREEN COORDINATES)
    wolf = wolf_data["rect"].move(-offset[0], -offset[1])

    if wolf_data["is_moving"]:
        frame = WOLF_WALK_FRAMES[wolf_data["walk_index"]]
    else:
        frame = 0

    if wolf_data["flash_timer"] > 0:
        image = wolf_hit_frames[wolf_data["facing"]][frame]
    else:
        image = wolf_frames[wolf_data["facing"]][frame]

    #SHADOW
    pygame.draw.ellipse(
        screen,
        (35, 45, 30),
        (wolf.centerx - 20, wolf.bottom - 5, 40, 8)
    )

    #SPRITE: FEET ON THE BOTTOM OF THE COLLISION BOX
    sprite_rect = image.get_rect(midbottom=(wolf.centerx, wolf.bottom + 3))
    screen.blit(image, sprite_rect)

    #HEALTH BAR ONCE THE WOLF HAS BEEN HIT
    if wolf_data["health"] < WOLF_MAX_HEALTH:
        bar = pygame.Rect(0, 0, 36, 5)
        bar.midbottom = (wolf.centerx, sprite_rect.top + 4)
        pygame.draw.rect(screen, (40, 20, 20), bar)
        filled = bar.copy()
        filled.width = int(bar.width * wolf_data["health"] / WOLF_MAX_HEALTH)
        pygame.draw.rect(screen, (220, 60, 60), filled)


#WHERE THE EYES ARE IN EACH 64 x 48 SPRITE (USED FOR GLOWING EYES AT NIGHT)
EYE_POSITIONS = {
    "right": [(52, 13)],
    "left": [(11, 13)],
    "down": [(27, 11), (37, 11)],
    "up": []
}


def eye_positions(wolf_data):
    #EYE POSITIONS IN WORLD COORDINATES
    wolf = wolf_data["rect"]
    left = wolf.centerx - 32
    top = wolf.bottom + 3 - 48
    return [(left + x, top + y) for x, y in EYE_POSITIONS[wolf_data["facing"]]]


def draw_wolves(screen, wolves, offset=(0, 0)):
    for wolf_data in wolves:
        draw_wolf(screen, wolf_data, offset)
