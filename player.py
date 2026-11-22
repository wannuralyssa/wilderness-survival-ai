import math
import pygame
import game_clock

ANIMATION_SPEED = 150          #MILLISECONDS PER WALK FRAME
SPRITE_SIZE = (48, 64)         #ON-SCREEN SIZE OF THE CHARACTER
DIRECTIONS = ["down", "left", "right", "up"]
IDLE_FRAME = 0
WALK_FRAMES = [1, 2, 3]

player_frames = {
    "down": [],
    "left": [],
    "right": [],
    "up": []
}

current_frame = IDLE_FRAME
walk_index = 0
animation_timer = 0

#ATTACK SWING EFFECT
ATTACK_EFFECT_TIME = 160      #MILLISECONDS THE SWING IS VISIBLE
attack_start_time = -10000

#ANGLE (RADIANS) THE SWING IS CENTRED ON FOR EACH DIRECTION
SWING_ANGLES = {
    "right": 0.0,
    "up": math.pi / 2,
    "left": math.pi,
    "down": -math.pi / 2
}


def start_attack():
    global attack_start_time
    attack_start_time = game_clock.now()


def load_player_frames():
    #CALL THIS AFTER pygame.display.set_mode()
    for direction in DIRECTIONS:
        player_frames[direction] = []
        for i in range(4):
            image = pygame.image.load(
                f"assets/player/frames/player_{direction}_{i}.png"
            ).convert_alpha()
            image = pygame.transform.smoothscale(image, SPRITE_SIZE)
            player_frames[direction].append(image)


def create_player(x, y):
    return pygame.Rect(x, y, 40, 40)


def feet_rect(player_rect):
    #ONLY THE FEET COLLIDE WITH OBSTACLES, SO THE PLAYER CAN WALK "BEHIND" TREES
    #AND SQUEEZE THROUGH GAPS (LIKE MOST TOP-DOWN RPGS)
    return pygame.Rect(player_rect.x + 8, player_rect.bottom - 14, 24, 14)


def move_player(player, dx, dy, obstacles, width, height):
    #TRY THE FULL MOVE FIRST; IF BLOCKED, SLIDE ALONG THE OBSTACLE ON ONE AXIS
    for step_x, step_y in ((dx, dy), (dx, 0), (0, dy)):
        if step_x == 0 and step_y == 0:
            continue
        moved = _try_move(player, step_x, step_y, obstacles, width, height)
        if moved is not None:
            return moved
    return player


def _try_move(player, dx, dy, obstacles, width, height):
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

    #CHECK FOR COLLISIONS (FEET ONLY)
    if feet_rect(moved_player).collidelist(obstacles) != -1:
        return None

    #UPDATE THE PLAYER'S POSITION
    return moved_player


def update_player_animation(is_moving, direction, dt):
    global current_frame, walk_index, animation_timer

    if is_moving:
        animation_timer += dt

        if animation_timer >= ANIMATION_SPEED:
            animation_timer -= ANIMATION_SPEED
            walk_index = (walk_index + 1) % len(WALK_FRAMES)

        current_frame = WALK_FRAMES[walk_index]
    else:
        current_frame = IDLE_FRAME
        walk_index = 0
        animation_timer = 0


def draw_player(screen, player_rect, direction="down", offset=(0, 0)):
    #offset = CAMERA POSITION (WORLD COORDINATES -> SCREEN COORDINATES)
    player_rect = player_rect.move(-offset[0], -offset[1])

    #PLAYER SHADOW
    pygame.draw.ellipse(
        screen,
        (35, 45, 30),
        (player_rect.centerx - 14, player_rect.bottom - 7, 28, 9)
    )

    #SPRITE: FEET ON THE BOTTOM OF THE COLLISION BOX
    image = player_frames[direction][current_frame]
    sprite_rect = image.get_rect(midbottom=(player_rect.centerx, player_rect.bottom + 2))
    screen.blit(image, sprite_rect)

    #SWING EFFECT: A WHITE ARC SWEEPING ACROSS THE FRONT OF THE PLAYER
    elapsed = game_clock.now() - attack_start_time
    if 0 <= elapsed < ATTACK_EFFECT_TIME:
        progress = elapsed / ATTACK_EFFECT_TIME
        middle = SWING_ANGLES[direction]
        start = middle - 1.1
        stop = start + 2.2 * (0.35 + 0.65 * progress)
        arc_rect = pygame.Rect(0, 0, 76, 76)
        arc_rect.center = (player_rect.centerx, player_rect.centery - 4)
        pygame.draw.arc(screen, (255, 255, 255), arc_rect, start, stop, 4)
        pygame.draw.arc(screen, (200, 220, 255), arc_rect.inflate(-10, -10), start, stop, 2)
