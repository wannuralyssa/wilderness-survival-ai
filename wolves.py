
import pygame
import random
import math
import survival_system
import messages
import search
import world
import weather
import game_clock
import audio
import json

#WOLF SPRITES (FROM THE WOLF SPRITESHEET, SLICED INTO assets/wolf/anim/)
WOLF_SPRITE_SCALE = 0.9       #THE SHEET IS 84 x 56 PER FRAME
WOLF_SPEED = 2                #PIXELS PER FRAME ON NORMAL GRASS

#FRAMES PER SECOND OF EACH ANIMATION, AND WHETHER IT LOOPS
WOLF_ANIMS = {
    "idle":   (6, True),
    "walk":   (9, True),
    "run":    (12, True),
    "chase":  (14, True),
    "search": (6, True),
    "attack": (12, False),
    "hurt":   (8, False),
    "death":  (8, False),
    "howl":   (5, False),
}
DEATH_LINGER = 2200           #HOW LONG A DEFEATED WOLF'S BODY STAYS (MILLISECONDS)
BITE_ANIM_TIME = 420          #HOW LONG THE BITE ANIMATION PLAYS
HOWL_TIME = 1600              #HOW LONG A HOWL LASTS
CLOSE_CHASE = 130             #CLOSER THAN THIS, A RUNNING WOLF SWITCHES TO ITS CHASE POSE

#COMBAT
WOLF_MAX_HEALTH = 3           #HITS NEEDED TO DEFEAT A WOLF
TARGET_WOLVES = 4             #HOW MANY WOLVES ROAM THE MAP (difficulty.py RAISES IT)
DETECTION_BONUS = 0           #EXTRA SMELL RANGE ON LATER DAYS
WOLF_STUN_FRAMES = 40         #A HIT WOLF CAN'T MOVE OR BITE FOR THIS LONG
WOLF_RESPAWN_TIME = 30000     #A DEFEATED WOLF IS REPLACED AFTER 30 SECONDS
RESPAWN_MIN_DISTANCE = 600    #NEW WOLVES APPEAR FAR AWAY FROM THE PLAYER
PLAYER_ATTACK_COOLDOWN = 400  #MILLISECONDS BETWEEN SWINGS
PLAYER_ATTACK_ENERGY = 1      #EACH SWING COSTS THIS MUCH ENERGY

#wolf_frames["walk"][True][2] = THIRD WALK FRAME FACING RIGHT (False = FACING LEFT)
wolf_frames = {}
wolf_hit_frames = {}          #RED-TINTED FRAMES SHOWN FOR A MOMENT WHEN A WOLF IS HIT
wolf_eyes = {}                #wolf_eyes["walk"][True][2] = (x, y) OF THE EYE IN THAT FRAME
wolf_frame_size = (76, 50)

respawn_times = []            #WHEN EACH DEFEATED WOLF WILL BE REPLACED
dying_wolves = []             #DEFEATED WOLVES PLAYING THEIR DEATH ANIMATION (NOT A THREAT ANY MORE)
last_player_attack = -10000
wolves_defeated = 0


def load_wolf_frames():
    #CALL THIS AFTER pygame.display.set_mode()
    global wolf_frame_size
    with open("assets/wolf/anim/wolf_anim.json") as f:
        info = json.load(f)

    sheet_w, sheet_h = info["size"]
    size = (round(sheet_w * WOLF_SPRITE_SCALE), round(sheet_h * WOLF_SPRITE_SCALE))
    wolf_frame_size = size

    for anim, count in info["counts"].items():
        right, left, right_hit, left_hit = [], [], [], []
        eyes_right, eyes_left = [], []
        for i in range(count):
            image = pygame.image.load(f"assets/wolf/anim/{anim}_{i}.png").convert_alpha()
            image = pygame.transform.smoothscale(image, size)
            flipped = pygame.transform.flip(image, True, False)
            right.append(image)
            left.append(flipped)
            for frame, hit_list in ((image, right_hit), (flipped, left_hit)):
                hit_image = frame.copy()
                hit_image.fill((120, 10, 10), special_flags=pygame.BLEND_RGB_ADD)
                hit_list.append(hit_image)

            ex, ey = info["eyes"][f"{anim}_{i}"]
            ex, ey = ex * WOLF_SPRITE_SCALE, ey * WOLF_SPRITE_SCALE
            eyes_right.append((round(ex), round(ey)))
            eyes_left.append((round(size[0] - 1 - ex), round(ey)))

        wolf_frames[anim] = {True: right, False: left}
        wolf_hit_frames[anim] = {True: right_hit, False: left_hit}
        wolf_eyes[anim] = {True: eyes_right, False: eyes_left}


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
        "face_right": random.random() < 0.5,
        "is_moving": False,
        "chasing": False,
        "chase_distance": 9999,
        "pause_anim": "idle",
        "anim": "idle",
        "anim_start": game_clock.now() - random.randint(0, 2000),
        "bite_time": -10000,
        "howl_until": 0,
        "fx": float(x),
        "fy": float(y),
        "health": WOLF_MAX_HEALTH,
        "max_health": WOLF_MAX_HEALTH,
        "stun_timer": 0,
        "flash_timer": 0,
        "knock_vx": 0.0,
        "knock_vy": 0.0
    }


def create_wolves():
    global last_player_attack, wolves_defeated
    respawn_times.clear()
    dying_wolves.clear()
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
        wolf_data["chase_distance"] = distance_to_player
        wolf_data["chasing"] = False

        #A HOWLING WOLF STANDS STILL UNTIL IT FINISHES (OR THE PLAYER GETS TOO CLOSE)
        if wolf_data["howl_until"] > game_clock.now() and distance_to_player > 150:
            update_wolf_animation(wolf_data, 0, 0)
            continue
        wolf_data["howl_until"] = 0

        if distance_to_player < 60:
            wolf_data["chasing"] = True
            #CLOSE ENOUGH TO LUNGE STRAIGHT AT THE PLAYER
            speed = WOLF_SPEED * world.speed_multiplier(wolf)
            dx = player.centerx - wolf.centerx
            dy = player.centery - wolf.centery
            saved = (wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"])
            step_wolf(wolf_data, dx / max(1, distance_to_player) * speed,
                      dy / max(1, distance_to_player) * speed)
            if wolf.collidelist(obstacles) != -1:
                wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"] = saved
        elif detect_player(wolf, player, weather.wolf_detection_range() + DETECTION_BONUS):
            wolf_data["chasing"] = True
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
                if random.random() < 0.3:
                    #STOP FOR A MOMENT: STAND IDLE OR SNIFF THE GROUND
                    wolf_data["direction"] = (0, 0)
                    wolf_data["pause_anim"] = random.choice(["idle", "search", "search"])
                    wolf_data["move_timer"] = random.randint(60, 150)
                else:
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

        #A CHASING WOLF ALWAYS LOOKS AT THE PLAYER
        if wolf_data["chasing"] and abs(player.centerx - wolf.centerx) > 6:
            wolf_data["face_right"] = player.centerx > wolf.centerx

        #UPDATE FACING DIRECTION AND ANIMATION
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

    now = game_clock.now()
    if now - last_player_attack < PLAYER_ATTACK_COOLDOWN:
        return False
    if survival.energy < PLAYER_ATTACK_ENERGY:
        messages.show_message("Too exhausted to fight!", 1200)
        return False

    last_player_attack = now
    survival.energy -= PLAYER_ATTACK_ENERGY
    audio.play("swing")
    area = attack_area(player_rect, direction)

    for wolf_data in list(wolves):
        wolf = wolf_data["rect"]
        if not area.colliderect(wolf):
            continue

        wolf_data["health"] -= 1
        audio.play("hit")
        if wolf_data["health"] <= 0:
            audio.play("wolf_die")
            wolves.remove(wolf_data)
            #KEEP THE BODY AROUND FOR ITS DEATH ANIMATION (IT CAN'T BITE OR BE HIT ANY MORE)
            wolf_data["face_right"] = wolf.centerx < player_rect.centerx
            wolf_data["death_time"] = now
            wolf_data["flash_timer"] = 8
            set_anim(wolf_data, "death")
            dying_wolves.append(wolf_data)
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
        wolf_data["face_right"] = wolf.centerx < player_rect.centerx
        wolf_data["howl_until"] = 0
        set_anim(wolf_data, "hurt")
        audio.play("wolf_yelp")
        wolf_data["flash_timer"] = 10
        wolf_data["attack_timer"] = max(wolf_data["attack_timer"], 60)

    return True


def update_respawns(wolves, player_rect):
    #REPLACE DEFEATED WOLVES SO THE FOREST NEVER RUNS OUT OF THEM
    now = game_clock.now()

    #CLEAR AWAY BODIES WHOSE DEATH ANIMATION HAS FINISHED
    dying_wolves[:] = [w for w in dying_wolves if now - w["death_time"] < DEATH_LINGER]
    for wolf_data in dying_wolves:
        wolf_data["flash_timer"] = max(0, wolf_data["flash_timer"] - 1)

    #ON LATER DAYS MORE WOLVES ARRIVE (THEY APPEAR FAR AWAY, LIKE RESPAWNS)
    while len(wolves) + len(respawn_times) < TARGET_WOLVES:
        respawn_times.append(now)
    for due in [t for t in respawn_times if now >= t]:
        #PICK THE SPAWN POINT FARTHEST FROM THE PLAYER (MUST BE FAR ENOUGH AWAY)
        spawns = sorted(
            WOLF_SPAWNS,
            key=lambda p: -math.hypot(p[0] - player_rect.centerx, p[1] - player_rect.centery)
        )
        x, y = random.choice(spawns[:2])
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


def set_anim(wolf_data, anim):
    #SWITCH TO A NEW ANIMATION, STARTING AT ITS FIRST FRAME
    if wolf_data["anim"] != anim:
        wolf_data["anim"] = anim
        wolf_data["anim_start"] = game_clock.now()


def update_wolf_animation(wolf_data, moved_x, moved_y):
    #PICK THE ANIMATION THAT MATCHES WHAT THE WOLF IS DOING
    now = game_clock.now()
    wolf_data["is_moving"] = moved_x != 0 or moved_y != 0
    if moved_x != 0 and not wolf_data["chasing"]:
        wolf_data["face_right"] = moved_x > 0

    if wolf_data["stun_timer"] > 0:
        anim = "hurt"
    elif now - wolf_data["bite_time"] < BITE_ANIM_TIME:
        anim = "attack"
    elif wolf_data["howl_until"] > now:
        anim = "howl"
    elif wolf_data["is_moving"] and wolf_data["chasing"]:
        anim = "chase" if wolf_data["chase_distance"] < CLOSE_CHASE else "run"
    elif wolf_data["is_moving"]:
        anim = "walk"
    elif wolf_data["chasing"]:
        anim = "idle"
    else:
        anim = wolf_data["pause_anim"]
    set_anim(wolf_data, anim)


def current_frame(wolf_data):
    #WHICH FRAME OF ITS ANIMATION THE WOLF IS SHOWING RIGHT NOW
    anim = wolf_data["anim"]
    fps, loops = WOLF_ANIMS[anim]
    count = len(wolf_frames[anim][True])
    index = int((game_clock.now() - wolf_data["anim_start"]) * fps / 1000)
    return index % count if loops else min(index, count - 1)


def start_howl(wolves):
    #CALLED WHEN NIGHT FALLS: WOLVES THAT AREN'T HUNTING STOP AND HOWL AT THE MOON
    now = game_clock.now()
    for wolf_data in wolves:
        if not wolf_data["chasing"] and wolf_data["stun_timer"] <= 0:
            wolf_data["howl_until"] = now + HOWL_TIME + random.randint(0, 500)
            set_anim(wolf_data, "howl")


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
                wolf_data["bite_time"] = game_clock.now()
                if abs(player.centerx - wolf.centerx) > 4:
                    wolf_data["face_right"] = player.centerx > wolf.centerx
                audio.play("wolf_bite")
                audio.play("hurt")
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

def sprite_rect(wolf_data, offset=(0, 0)):
    #THE SPRITE STANDS WITH ITS FEET ON THE BOTTOM OF THE COLLISION BOX
    wolf = wolf_data["rect"]
    w, h = wolf_frame_size
    return pygame.Rect(wolf.centerx - w // 2 - offset[0], wolf.bottom + 3 - h - offset[1], w, h)


def draw_wolf(screen, wolf_data, offset=(0, 0)):
    #offset = CAMERA POSITION (WORLD COORDINATES -> SCREEN COORDINATES)
    wolf = wolf_data["rect"].move(-offset[0], -offset[1])
    frame = current_frame(wolf_data)
    frames = wolf_hit_frames if wolf_data["flash_timer"] > 0 else wolf_frames
    image = frames[wolf_data["anim"]][wolf_data["face_right"]][frame]

    #A DEFEATED WOLF FADES AWAY AT THE END
    if "death_time" in wolf_data:
        left = DEATH_LINGER - (game_clock.now() - wolf_data["death_time"])
        if left < 700:
            image = image.copy()
            image.set_alpha(max(0, int(255 * left / 700)))

    #SHADOW
    pygame.draw.ellipse(
        screen,
        (35, 45, 30),
        (wolf.centerx - 24, wolf.bottom - 5, 48, 9)
    )

    rect = sprite_rect(wolf_data, offset)
    screen.blit(image, rect)

    #HEALTH BAR ONCE THE WOLF HAS BEEN HIT
    if 0 < wolf_data["health"] < wolf_data["max_health"]:
        bar = pygame.Rect(0, 0, 36, 5)
        bar.midbottom = (wolf.centerx, rect.top + 10)
        pygame.draw.rect(screen, (40, 20, 20), bar.inflate(2, 2))
        filled = bar.copy()
        filled.width = int(bar.width * wolf_data["health"] / wolf_data["max_health"])
        pygame.draw.rect(screen, (220, 60, 60), filled)


def eye_positions(wolf_data):
    #EYE POSITION IN WORLD COORDINATES (USED FOR GLOWING EYES AT NIGHT)
    rect = sprite_rect(wolf_data)
    x, y = wolf_eyes[wolf_data["anim"]][wolf_data["face_right"]][current_frame(wolf_data)]
    return [(rect.x + x, rect.y + y)]


def draw_wolves(screen, wolves, offset=(0, 0)):
    for wolf_data in dying_wolves + wolves:
        draw_wolf(screen, wolf_data, offset)
