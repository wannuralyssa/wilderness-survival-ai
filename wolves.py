
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
import survival_system
import game_theory as gt
import pack_learning

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
    track_player(player)
    pick_active_attacker(wolves, player)
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

        detected = detect_player(wolf, player, weather.wolf_detection_range() + DETECTION_BONUS)
        ignoring = wolf_data.get("ignore_until", 0) > game_clock.now()
        if ignoring:
            #THIS WOLF HAS GIVEN UP FOR NOW AND WANDERS OFF
            detected = False
            wolf_data["enc"] = None
        if not ignoring and distance_to_player < ENGAGE_RANGE and (detected or distance_to_player < 100):
            #CLOSE: AN ENCOUNTER. EACH ROUND THE WOLF PICKS A TACTIC (GAME THEORY + WHAT THE PACK
            #HAS LEARNED ABOUT THIS PLAYER)
            encounter_step(wolf_data, player, obstacles, distance_to_player)
        elif wolf_data.get("enc") is not None and distance_to_player >= ENGAGE_RANGE + 40:
            finish_round(wolf_data, player)
            wolf_data["enc"] = None
            continue
        elif detected:
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


#----------------------------------------------------------------
# ENCOUNTERS (GAME THEORY + MACHINE LEARNING)
#----------------------------------------------------------------
ENGAGE_RANGE = 170          #CLOSER THAN THIS, THE WOLF STOPS CHASING AND STARTS AN ENCOUNTER
ROUND_TIME = 1400           #MILLISECONDS PER ROUND (BOTH SIDES PICK A TACTIC EACH ROUND)
CIRCLE_RADIUS = 85          #JUST OUT OF REACH OF A SWING
STALK_DISTANCE = 150
LUNGE_TIME = 900            #MILLISECONDS A LUNGE LASTS
LEARNING_MODE = "play"      #WHOSE HABITS THE PACK IS LEARNING: "play" (YOU) OR "ai"
_player_last = None
player_was_moving = False


def track_player(player):
    #IS THE PLAYER MOVING? (A FEATURE FOR THE PACK'S PREDICTIONS)
    global _player_last, player_was_moving
    centre = player.center
    player_was_moving = _player_last is not None and centre != _player_last
    _player_last = centre


active_attacker = None       #ONLY ONE WOLF ATTACKS AT A TIME; THE OTHERS STALK AND WAIT THEIR TURN


def pick_active_attacker(wolves, player):
    global active_attacker
    now = game_clock.now()
    engaged = [w for w in wolves
               if w.get("ignore_until", 0) <= now and math.hypot(
                   w["rect"].centerx - player.centerx, w["rect"].centery - player.centery) < ENGAGE_RANGE]
    if active_attacker in engaged:
        return
    active_attacker = min(engaged, key=lambda w: math.hypot(
        w["rect"].centerx - player.centerx, w["rect"].centery - player.centery), default=None)


def is_threat(wolf_data):
    #FALSE WHILE A WOLF HAS GIVEN UP AND IS WANDERING AWAY
    return wolf_data.get("ignore_until", 0) <= game_clock.now()


def give_up(wolf_data, player, seconds=8):
    #THE WOLF LOSES INTEREST AND WANDERS AWAY FOR A WHILE
    wolf = wolf_data["rect"]
    wolf_data["ignore_until"] = game_clock.now() + seconds * 1000
    wolf_data["enc"] = None
    dx, dy = wolf.centerx - player.centerx, wolf.centery - player.centery
    wolf_data["direction"] = ((1 if dx > 0 else -1), 0) if abs(dx) >= abs(dy) else (0, (1 if dy > 0 else -1))
    wolf_data["move_timer"] = 90
    wolf_data["stalk_rounds"] = 0


def round_context(wolf_data):
    #THE GAME BEING PLAYED RIGHT NOW: HOW HARD WOLVES BITE, HOW HURT THIS WOLF IS, FIRE NEARBY?
    return survival_system.WOLF_DAMAGE, wolf_data["health"], weather.player_near_fire


def start_round(wolf_data, player, now):
    bite, health, fire = round_context(wolf_data)
    A = gt.payoff_matrix(bite, health, fire)
    _, nash, _ = gt.equilibrium(bite, health, fire)
    features = (int(survival_system.health < 40), int(fire), int(player_was_moving))
    model = pack_learning.models[LEARNING_MODE]
    mix = pack_learning.wolf_mix(A, nash, model, features)
    tactic = random.choices(range(len(gt.WOLF_TACTICS)), weights=mix)[0]
    wolf_data["enc"] = {
        "tactic": tactic, "start": now, "until": now + ROUND_TIME, "features": features,
        "matrix": A, "spin": random.choice((-1, 1)), "dart": False, "recorded": False,
        "player_start": player.center, "start_distance": math.hypot(
            wolf_data["rect"].centerx - player.centerx, wolf_data["rect"].centery - player.centery),
        "health_start": survival_system.health, "wolf_health_start": wolf_data["health"]
    }


def finish_round(wolf_data, player, killed=False):
    #WHAT DID THE PLAYER DO THIS ROUND? THE PACK LEARNS FROM IT
    enc = wolf_data.get("enc")
    if enc is None or enc["recorded"] or enc.get("forced"):
        return
    enc["recorded"] = True
    swung = last_player_attack >= enc["start"]
    wolf = wolf_data["rect"]
    distance = math.hypot(wolf.centerx - player.centerx, wolf.centery - player.centery)
    backed_off = distance - enc["start_distance"] >= 15 or math.hypot(
        player.centerx - enc["player_start"][0], player.centery - enc["player_start"][1]) >= 40
    if swung:
        label = gt.ATTACK
    elif backed_off:
        label = gt.EVADE
    else:
        return          #THE PLAYER DID NEITHER: NOTHING TO LEARN FROM
    model = pack_learning.models[LEARNING_MODE]
    model.update(enc["features"], label)
    #WHAT ACTUALLY HAPPENED, IN THE SAME UNITS AS THE PAYOFF MATRIX
    payoff = (survival_system.health - enc["health_start"]) \
        + gt.HIT_VALUE * (enc["wolf_health_start"] - max(0, wolf_data["health"])) \
        + (gt.KILL_VALUE - gt.HIT_VALUE if killed else 0)
    model.record_outcome(label, enc["tactic"], payoff)


def move_with_obstacles(wolf_data, vx, vy, obstacles):
    #MOVE, SLIDING ALONG OBSTACLES INSTEAD OF STOPPING DEAD
    wolf = wolf_data["rect"]
    for step_x, step_y in ((vx, vy), (vx, 0), (0, vy)):
        saved = (wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"])
        step_wolf(wolf_data, step_x, step_y)
        if wolf.collidelist(obstacles) == -1:
            return True
        wolf.x, wolf.y, wolf_data["fx"], wolf_data["fy"] = saved
    return False


def encounter_step(wolf_data, player, obstacles, distance):
    now = game_clock.now()
    enc = wolf_data.get("enc")
    if enc is None or now >= enc["until"]:
        finish_round(wolf_data, player)
        if wolf_data is not active_attacker:
            #NOT THIS WOLF'S TURN: IT STALKS AND WAITS
            wolf_data["enc"] = {"tactic": gt.STALK, "start": now, "until": now + 700, "forced": True,
                                "recorded": True, "dart": False, "spin": 1}
        else:
            start_round(wolf_data, player, now)
            #A WOLF THAT KEEPS HANGING BACK (OR FACES A FIRE) EVENTUALLY GIVES UP
            if wolf_data["enc"]["tactic"] == gt.STALK:
                wolf_data["stalk_rounds"] = wolf_data.get("stalk_rounds", 0) + 1
                if wolf_data["stalk_rounds"] >= 3 or (weather.player_near_fire and random.random() < 0.5):
                    give_up(wolf_data, player)
                    return
            else:
                wolf_data["stalk_rounds"] = 0
        enc = wolf_data["enc"]

    wolf = wolf_data["rect"]
    dx, dy = player.centerx - wolf.centerx, player.centery - wolf.centery
    d = max(1.0, distance)
    ux, uy = dx / d, dy / d                         #UNIT VECTOR TOWARDS THE PLAYER
    speed = WOLF_SPEED * world.speed_multiplier(wolf)
    tactic = enc["tactic"]

    #A CIRCLING WOLF DARTS IN THE MOMENT YOU SWING (YOU ARE OPEN FOR A SPLIT SECOND)
    if tactic == gt.CIRCLE and last_player_attack >= enc["start"] and wolf_data["attack_timer"] <= 0:
        enc["dart"] = True

    #A LUNGE IS ONE CHARGE (UNDER A SECOND); AFTER THAT THE WOLF FALLS BACK
    if tactic == gt.LUNGE and not enc["dart"] and now - enc["start"] > LUNGE_TIME:
        tactic = gt.STALK

    if tactic == gt.LUNGE or enc["dart"]:
        wolf_data["chasing"] = True
        boost = 2.2 if enc["dart"] else 1.7
        move_with_obstacles(wolf_data, ux * speed * boost, uy * speed * boost, obstacles)
        #CHARGING INTO FIRELIGHT SCARES A WOLF OFF
        for fire in world.lit_campfires():
            if math.hypot(fire.centerx - wolf.centerx, fire.centery - wolf.centery) < 60:
                scare_off(wolf_data, fire)
                break
    elif tactic == gt.CIRCLE:
        #MOVE SIDEWAYS AROUND THE PLAYER, KEEPING JUST OUT OF REACH
        tx, ty = -uy * enc["spin"], ux * enc["spin"]
        pull = max(-1.0, min(1.0, (distance - CIRCLE_RADIUS) / 25))
        vx, vy = tx + ux * pull, ty + uy * pull
        length = max(0.01, math.hypot(vx, vy))
        if not move_with_obstacles(wolf_data, vx / length * speed * 1.2, vy / length * speed * 1.2, obstacles):
            enc["spin"] *= -1
    else:
        #STALK: HANG BACK, KEEP WATCHING, FOLLOW IF THE PLAYER MOVES AWAY
        gap = distance - STALK_DISTANCE
        if abs(gap) > 20:
            direction = 1 if gap > 0 else -1
            move_with_obstacles(wolf_data, ux * speed * 0.7 * direction, uy * speed * 0.7 * direction, obstacles)
        if abs(dx) > 6:
            wolf_data["face_right"] = dx > 0


def scare_off(wolf_data, fire):
    wolf = wolf_data["rect"]
    dx, dy = wolf.centerx - fire.centerx, wolf.centery - fire.centery
    d = max(1.0, math.hypot(dx, dy))
    wolf_data["knock_vx"], wolf_data["knock_vy"] = dx / d * 6, dy / d * 6
    wolf_data["stun_timer"] = WOLF_STUN_FRAMES
    wolf_data["face_right"] = dx < 0
    set_anim(wolf_data, "hurt")
    audio.play("wolf_yelp")
    enc = wolf_data.get("enc")
    if enc is not None:
        enc["until"] = game_clock.now()       #THE ROUND IS OVER


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
            finish_round(wolf_data, player_rect, killed=True)
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
                #AFTER A BITE THE WOLF BACKS OFF FOR A MOMENT, THEN A NEW ROUND STARTS
                if wolf_data.get("enc") is not None:
                    finish_round(wolf_data, player)
                    now = game_clock.now()
                    wolf_data["enc"] = {"tactic": gt.STALK, "start": now, "until": now + 900,
                                        "forced": True, "recorded": True, "dart": False, "spin": 1}
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
