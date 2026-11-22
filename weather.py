
#ENVIRONMENTAL THREATS: NIGHTFALL, HEAVY RAIN AND COLD SNAPS
import math
import random
import pygame
from config import *
import survival_system as survival
import messages
import world
import audio
import hmm

#WEATHER TYPES
CLEAR = "clear"
RAIN = "rain"
COLD = "cold"

WEATHER_NAMES = {
    CLEAR: "Clear",
    RAIN: "Heavy Rain",
    COLD: "Cold Snap"
}

#THE WEATHER COMES FROM A HIDDEN MARKOV MODEL (SEE hmm.py): A HIDDEN "SKY STATE" CHANGES EVERY
#TICK, AND THE SKY SHOWS A NOISY SIGN (SUNNY, CLOUDS, WIND). YOU ONLY SEE THE SIGNS.
STATE_TO_WEATHER = {
    hmm.CLEAR: CLEAR, hmm.STORM_FRONT: CLEAR, hmm.COLD_FRONT: CLEAR,
    hmm.RAIN: RAIN, hmm.COLD: COLD
}
CALM_START = 45000          #THE FIRST 45 SECONDS OF A GAME ARE ALWAYS CALM
NIGHT_WARNING_TIME = 8000   #WARN THE PLAYER THIS LONG BEFORE NIGHT
FADE_TIME = 5000            #DUSK AND DAWN TAKE THIS LONG

#ENERGY CHANGE PER SECOND
ENERGY_DRAIN_NIGHT = 0.3        #NIGHTS ARE CHILLY
ENERGY_DRAIN_RAIN = 0.6         #GETTING SOAKED
ENERGY_DRAIN_COLD = 1.0         #COLD SNAP, OUT IN THE OPEN
ENERGY_DRAIN_COLD_TENT = 0.4    #COLD SNAP, INSIDE A TENT
ENERGY_GAIN_FIRE = 1.5          #WARMING UP NEXT TO A CAMPFIRE
ENERGY_GAIN_TENT = 0.4          #RESTING IN A TENT
HEALTH_DRAIN_EXHAUSTED = 0.5    #HEALTH LOST PER SECOND WHEN ENERGY IS 0

CAMPFIRE_WARMTH_RADIUS = 100
DIFFICULTY_DRAIN = 1.0          #difficulty.py MAKES BAD WEATHER DRAIN MORE ON LATER DAYS

#WOLF DETECTION RANGE (PIXELS)
WOLF_RANGE_DAY = 180
WOLF_RANGE_NIGHT = 260          #WOLVES HUNT BETTER IN THE DARK
WOLF_RANGE_RAIN_PENALTY = 60    #RAIN HIDES YOUR SCENT A LITTLE

#LIGHT RADIUS (HOW FAR YOU CAN SEE)
VISION_DAY = 320
VISION_NIGHT = 150
CAMPFIRE_LIGHT = 170

DARK_COLOR = (8, 12, 35)


#STATE
current = CLEAR
upcoming = None             #NO LONGER USED: NOBODY KNOWS THE FUTURE NOW (KEPT FOR OLD CODE)
sky_state = hmm.CLEAR       #HIDDEN: THE TRUE STATE OF THE ATMOSPHERE
sky_sign = hmm.SUNNY        #VISIBLE: WHAT THE SKY LOOKS LIKE RIGHT NOW
tick_timer = 0
calm_timer = 0
forecast = hmm.WeatherFilter()   #THE HMM FILTER: WHAT YOU CAN WORK OUT FROM THE SIGNS
rain_warned = False
cold_warned = False
night_warned = False

cloud_amount = 0.0      #0..1, CLOUD SHADOWS DRIFTING OVER THE MAP
wind_amount = 0.0       #0..1, LEAVES AND GUSTS BLOWING ACROSS

night_amount = 0.0      #0 = FULL DAY, 1 = FULL NIGHT (SMOOTH)
rain_amount = 0.0       #0..1, FADES IN AND OUT
cold_amount = 0.0       #0..1, FADES IN AND OUT
is_night_now = False
elapsed_time = 0         #MILLISECONDS INTO THE CURRENT DAY + NIGHT (FOR THE HUD CLOCK)

player_sheltered = False
player_near_fire = False

_energy_buffer = 0.0
_health_buffer = 0.0
_freeze_message_timer = 0

_light_cache = {}
_layers = {}
rain_drops = []
snow_flakes = []
leaves = []
cloud_drift = 0.0

#CLOUD SHADOWS: (X, Y IN THE WORLD, SIZE). THEY DRIFT SLOWLY TO THE RIGHT
CLOUDS = [(100, 150, 1.0), (700, 520, 1.3), (1250, 200, 0.9), (400, 950, 1.2), (1100, 820, 1.0),
          (1500, 1050, 0.8)]
LEAF_COLOURS = [(126, 168, 64), (170, 150, 60), (196, 120, 52), (100, 140, 60)]


def reset():
    global current, upcoming, night_warned
    global sky_state, sky_sign, tick_timer, calm_timer, rain_warned, cold_warned
    global night_amount, rain_amount, cold_amount, is_night_now, cloud_amount, wind_amount
    global player_sheltered, player_near_fire
    global _energy_buffer, _health_buffer, _freeze_message_timer

    current = CLEAR
    upcoming = None
    sky_state = hmm.CLEAR
    sky_sign = hmm.SUNNY
    tick_timer = hmm.TICK
    calm_timer = CALM_START
    forecast.reset()
    rain_warned = False
    cold_warned = False
    cloud_amount = 0.0
    wind_amount = 0.0
    night_warned = False
    night_amount = 0.0
    rain_amount = 0.0
    cold_amount = 0.0
    is_night_now = False
    player_sheltered = False
    player_near_fire = False
    _energy_buffer = 0.0
    _health_buffer = 0.0
    _freeze_message_timer = 0
    rain_drops.clear()
    snow_flakes.clear()
    leaves.clear()


reset()


#----------------------------------------------------------------
# UPDATE
#----------------------------------------------------------------
def _approach(value, target, step):
    #MOVE value TOWARDS target BY AT MOST step
    if value < target:
        return min(value + step, target)
    return max(value - step, target)


def _night_target(elapsed_time):
    #SMOOTH DUSK AT THE END OF THE DAY AND DAWN AT THE END OF THE NIGHT
    if elapsed_time < DAY_DURATION - FADE_TIME:
        return 0.0
    if elapsed_time < DAY_DURATION:
        return (elapsed_time - (DAY_DURATION - FADE_TIME)) / FADE_TIME
    if elapsed_time < CYCLE_DURATION - FADE_TIME:
        return 1.0
    return (CYCLE_DURATION - elapsed_time) / FADE_TIME


def _start_weather(previous):
    #WHAT HAPPENS WHEN THE WEATHER YOU CAN FEEL ACTUALLY CHANGES
    if current == RAIN:
        #THE RAIN PUTS OUT EVERY CAMPFIRE
        audio.play("thunder")
        if world.extinguish_campfires() > 0:
            messages.show_message("Heavy rain! It put out your campfire.", 3000)
            audio.play("extinguish")
        else:
            messages.show_message("Heavy rain! Find shelter.", 3000)
    elif current == COLD:
        messages.show_message("A cold snap! Stay near a campfire.", 3000)
        audio.play("wind_gust")
    elif previous != CLEAR:
        messages.show_message("The weather clears up.", 2500)


def _update_weather_state(dt):
    global current, sky_state, sky_sign, tick_timer, calm_timer, rain_warned, cold_warned

    calm_timer -= dt
    tick_timer -= dt
    if tick_timer > 0:
        return
    tick_timer += hmm.TICK

    #1) THE HIDDEN SKY STATE MOVES ON (MARKOV CHAIN). NOTHING CHANGES DURING THE CALM START
    if calm_timer <= 0:
        sky_state = hmm.next_state(sky_state)

    #2) THE SKY SHOWS A NOISY SIGN OF THE HIDDEN STATE
    sky_sign = hmm.emit(sky_state)
    if sky_sign == hmm.WIND and current == CLEAR:
        audio.play("wind_gust", 0.5)

    #3) THE FORECAST (HMM FILTER) LEARNS FROM THE SIGN, NOT FROM THE HIDDEN STATE
    forecast.observe(sky_sign)

    #4) THE WEATHER YOU FEEL
    previous = current
    current = STATE_TO_WEATHER[sky_state]
    if current != previous:
        _start_weather(previous)

    #WARN WHEN THE FORECAST SAYS BAD WEATHER IS LIKELY (IT CAN BE WRONG!)
    if current == CLEAR:
        if forecast.rain_soon >= hmm.WARNING_LEVEL and not rain_warned:
            messages.show_message(f"Dark clouds... {forecast.rain_soon:.0%} chance of rain soon (T = tent)", 4000)
            rain_warned = True
        if forecast.cold_soon >= hmm.WARNING_LEVEL and not cold_warned:
            messages.show_message(f"An icy wind... {forecast.cold_soon:.0%} chance of a cold snap soon", 4000)
            cold_warned = True
    if forecast.rain_soon < 0.25 or current != CLEAR:
        rain_warned = False
    if forecast.cold_soon < 0.25 or current != CLEAR:
        cold_warned = False


def _update_survival(dt, player_rect):
    global player_sheltered, player_near_fire
    global _energy_buffer, _health_buffer, _freeze_message_timer

    player_sheltered = any(tent.collidepoint(player_rect.center) for tent in world.tents)
    player_near_fire = any(
        math.hypot(fire.centerx - player_rect.centerx, fire.centery - player_rect.centery)
        <= CAMPFIRE_WARMTH_RADIUS
        for fire in world.lit_campfires()
    )

    seconds = dt / 1000

    #WORK OUT HOW FAST ENERGY CHANGES RIGHT NOW
    if player_near_fire:
        energy_rate = ENERGY_GAIN_FIRE
    elif player_sheltered:
        energy_rate = -ENERGY_DRAIN_COLD_TENT * DIFFICULTY_DRAIN if current == COLD else ENERGY_GAIN_TENT
    else:
        energy_rate = 0.0
        energy_rate -= ENERGY_DRAIN_NIGHT * night_amount
        energy_rate -= ENERGY_DRAIN_RAIN * rain_amount
        energy_rate -= ENERGY_DRAIN_COLD * cold_amount
        energy_rate *= DIFFICULTY_DRAIN

    #STATS ARE WHOLE NUMBERS, SO COLLECT SMALL CHANGES UNTIL THEY ADD UP TO 1
    _energy_buffer += energy_rate * seconds
    whole = int(_energy_buffer)
    if whole != 0:
        survival.energy = max(0, min(100, survival.energy + whole))
        _energy_buffer -= whole

    #NO ENERGY LEFT: THE PLAYER STARTS FREEZING
    if survival.energy <= 0:
        _health_buffer += HEALTH_DRAIN_EXHAUSTED * seconds
        whole = int(_health_buffer)
        if whole > 0:
            survival.health = max(0, survival.health - whole)
            _health_buffer -= whole
            survival.check_death()

        _freeze_message_timer -= dt
        if _freeze_message_timer <= 0:
            messages.show_message("You're exhausted and freezing! Find warmth!", 2000)
            _freeze_message_timer = 5000
    else:
        _health_buffer = 0.0


def _store_elapsed(value):
    global elapsed_time
    elapsed_time = value


def update(dt, elapsed_time, is_night, player_rect):
    #CALL ONCE PER FRAME WHILE THE GAME IS RUNNING
    global night_amount, rain_amount, cold_amount, is_night_now, night_warned
    global cloud_amount, wind_amount

    is_night_now = is_night
    _store_elapsed(elapsed_time)
    night_amount = _night_target(elapsed_time)

    #WARN BEFORE NIGHT
    time_to_night = DAY_DURATION - elapsed_time
    if 0 < time_to_night <= NIGHT_WARNING_TIME and not night_warned:
        messages.show_message("The sun is setting... Wolves hunt at night!", 3500)
        night_warned = True
    if elapsed_time < DAY_DURATION - NIGHT_WARNING_TIME:
        night_warned = False

    _update_weather_state(dt)

    #FADE RAIN AND COLD IN AND OUT OVER ABOUT 3 SECONDS
    step = dt / 3000
    rain_amount = _approach(rain_amount, 1.0 if current == RAIN else 0.0, step)
    cold_amount = _approach(cold_amount, 1.0 if current == COLD else 0.0, step)
    cloudy = sky_sign in (hmm.CLOUDS, hmm.RAINING)
    cloud_amount = _approach(cloud_amount, 1.0 if cloudy else 0.0, dt / 4000)
    wind_amount = _approach(wind_amount, 1.0 if sky_sign in (hmm.WIND, hmm.SNOWING) else 0.0, dt / 2500)

    _update_survival(dt, player_rect)
    _update_particles(dt)


#----------------------------------------------------------------
# EFFECTS USED BY OTHER MODULES
#----------------------------------------------------------------
def player_speed_factor():
    factor = 1.0
    if not player_sheltered:
        factor *= 1.0 - 0.2 * rain_amount     #RAIN MAKES THE GROUND SLIPPERY
    if survival.energy <= 0:
        factor *= 0.6                          #EXHAUSTED
    return factor


def wolf_detection_range():
    detection = WOLF_RANGE_DAY + (WOLF_RANGE_NIGHT - WOLF_RANGE_DAY) * night_amount
    detection -= WOLF_RANGE_RAIN_PENALTY * rain_amount
    return detection


def vision_radius():
    radius = VISION_DAY + (VISION_NIGHT - VISION_DAY) * night_amount
    radius *= 1.0 - 0.3 * rain_amount
    return radius


def darkness_alpha():
    #HOW DARK THE SCREEN IS (0 = NO DARKNESS, 255 = BLACK)
    alpha = 215 * night_amount
    alpha += rain_amount * (120 * (1 - night_amount) + 25 * night_amount)
    return int(min(235, alpha))


#----------------------------------------------------------------
# DRAWING
#----------------------------------------------------------------
def _light_circle(radius):
    #A CIRCLE THAT IS SEE-THROUGH IN THE MIDDLE AND FADES TO DARK AT THE EDGE.
    #CACHED, BECAUSE DRAWING IT IS SLOW
    radius = max(20, int(radius) // 8 * 8)
    if radius not in _light_cache:
        surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        surface.fill((*DARK_COLOR, 255))
        for r in range(radius, 0, -2):
            alpha = int(255 * (r / radius) ** 2)
            pygame.draw.circle(surface, (*DARK_COLOR, alpha), (radius, radius), r)
        _light_cache[radius] = surface
    return _light_cache[radius]


def _layer(name):
    #FULL-SCREEN SEE-THROUGH SURFACES, CREATED ONCE AND REUSED EVERY FRAME
    if name not in _layers:
        _layers[name] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    return _layers[name]


def _update_particles(dt):
    #RAIN: FAST DIAGONAL STREAKS
    wanted_drops = int(220 * rain_amount)
    while len(rain_drops) < wanted_drops:
        rain_drops.append([random.uniform(0, WIDTH + 100), random.uniform(-HEIGHT, 0),
                           random.uniform(0.9, 1.3)])
    del rain_drops[wanted_drops:]
    for drop in rain_drops:
        drop[0] -= 0.25 * dt * drop[2]
        drop[1] += 1.1 * dt * drop[2]
        if drop[1] > HEIGHT:
            drop[0] = random.uniform(0, WIDTH + 100)
            drop[1] = random.uniform(-60, 0)

    #CLOUD SHADOWS DRIFT WITH THE WIND
    global cloud_drift
    cloud_drift += dt * (0.012 + 0.03 * wind_amount)

    #WIND: LEAVES TUMBLING ACROSS THE SCREEN
    wanted_leaves = int(34 * wind_amount)
    while len(leaves) < wanted_leaves:
        leaves.append([random.uniform(-WIDTH, 0), random.uniform(0, HEIGHT), random.uniform(0.7, 1.3),
                       random.uniform(0, 6.28), random.choice(LEAF_COLOURS)])
    del leaves[wanted_leaves:]
    for leaf in leaves:
        leaf[3] += dt * 0.008
        leaf[0] += 0.32 * dt * leaf[2]
        leaf[1] += math.sin(leaf[3]) * 0.06 * dt
        if leaf[0] > WIDTH + 10:
            leaf[0] = random.uniform(-80, -10)
            leaf[1] = random.uniform(0, HEIGHT)

    #SNOW: SLOW, DRIFTING FLAKES
    wanted_flakes = int(110 * cold_amount)
    while len(snow_flakes) < wanted_flakes:
        snow_flakes.append([random.uniform(0, WIDTH), random.uniform(-HEIGHT, 0),
                            random.uniform(0.5, 1.0), random.uniform(0, 6.28)])
    del snow_flakes[wanted_flakes:]
    for flake in snow_flakes:
        flake[3] += dt * 0.002
        flake[0] += math.sin(flake[3]) * 0.03 * dt
        flake[1] += 0.06 * dt * flake[2]
        if flake[1] > HEIGHT:
            flake[0] = random.uniform(0, WIDTH)
            flake[1] = random.uniform(-20, 0)


def _cloud_shadow(scale):
    #A SOFT, LUMPY SHADOW (CACHED)
    key = ("cloud", scale)
    if key not in _light_cache:
        w, h = int(300 * scale), int(170 * scale)
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        rng = random.Random(int(scale * 100))
        for _ in range(9):
            bw, bh = rng.uniform(0.35, 0.6) * w, rng.uniform(0.4, 0.7) * h
            bx, by = rng.uniform(0, w - bw), rng.uniform(0, h - bh)
            pygame.draw.ellipse(surface, (20, 30, 50, 46), (bx, by, bw, bh))
        _light_cache[key] = surface
    return _light_cache[key]


def draw(screen, camera, player_rect, wolf_list, wolf_eye_positions):
    #DRAW EVERYTHING WEATHER-RELATED ON TOP OF THE WORLD (BUT UNDER THE HUD)

    #CLOUDS: THEIR SHADOWS SLIDE OVER THE GROUND (A SIGN THAT RAIN MAY BE COMING)
    if cloud_amount > 0.02:
        span = WORLD_WIDTH + 600
        for x, y, scale in CLOUDS:
            shadow = _cloud_shadow(scale)
            sx = (x + cloud_drift) % span - 300 - camera.x
            sy = y - camera.y
            if -shadow.get_width() < sx < WIDTH and -shadow.get_height() < sy < HEIGHT:
                shadow.set_alpha(int(255 * cloud_amount))
                screen.blit(shadow, (sx, sy))

    #COLD: A FROSTY BLUE HAZE
    if cold_amount > 0:
        frost = _layer("frost")
        frost.fill((190, 220, 255, int(45 * cold_amount)))
        screen.blit(frost, (0, 0))

    #DARKNESS WITH HOLES OF LIGHT AROUND THE PLAYER AND CAMPFIRES
    alpha = darkness_alpha()
    if alpha > 0:
        darkness = _layer("darkness")
        darkness.fill((*DARK_COLOR, alpha))

        lights = [(player_rect.centerx, player_rect.centery, vision_radius())]
        flicker = random.uniform(-6, 6)
        for fire in world.lit_campfires():
            lights.append((fire.centerx, fire.centery,
                           (CAMPFIRE_LIGHT + flicker) * (1.0 - 0.2 * rain_amount)))

        #A LANTERN GLOWS IN THE TENT WHEN THE PLAYER IS INSIDE
        if world.occupied_tent is not None:
            lights.append((world.occupied_tent.centerx, world.occupied_tent.bottom - 30, 120))

        for x, y, radius in lights:
            circle = _light_circle(radius)
            r = circle.get_width() // 2
            darkness.blit(circle, (x - camera.x - r, y - camera.y - r),
                          special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(darkness, (0, 0))

        #WARM GLOW AROUND CAMPFIRES
        for fire in world.lit_campfires():
            glow = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 150, 60, int(40 * alpha / 235)), (60, 60), 60)
            pygame.draw.circle(glow, (255, 180, 80, int(40 * alpha / 235)), (60, 60), 35)
            screen.blit(glow, (fire.centerx - camera.x - 60, fire.centery - camera.y - 60))

        if world.occupied_tent is not None:
            tent = world.occupied_tent
            glow = pygame.Surface((160, 120), pygame.SRCALPHA)
            strength = alpha / 235
            pygame.draw.ellipse(glow, (255, 170, 80, int(45 * strength)), (0, 20, 160, 100))
            pygame.draw.ellipse(glow, (255, 200, 120, int(55 * strength)), (40, 40, 80, 60))
            screen.blit(glow, (tent.centerx - camera.x - 80, tent.bottom - camera.y - 90))

        #GLOWING WOLF EYES IN THE DARK: YOU CAN'T SEE THE WOLF, BUT YOU CAN SEE IT WATCHING YOU
        if night_amount > 0.5:
            vision = vision_radius()
            for wolf_data, eyes in zip(wolf_list, wolf_eye_positions):
                wolf = wolf_data["rect"]
                distance = math.hypot(wolf.centerx - player_rect.centerx,
                                      wolf.centery - player_rect.centery)
                if vision * 0.8 < distance < 420:
                    for ex, ey in eyes:
                        sx, sy = ex - camera.x, ey - camera.y
                        pygame.draw.circle(screen, (255, 200, 40), (sx, sy), 2)
                        pygame.draw.circle(screen, (255, 255, 180), (sx, sy), 1)

    #RAIN STREAKS
    if rain_drops:
        rain_layer = _layer("rain")
        rain_layer.fill((0, 0, 0, 0))
        for x, y, speed in rain_drops:
            pygame.draw.line(rain_layer, (170, 190, 230, 150), (x, y), (x - 4, y + 14), 1)
        screen.blit(rain_layer, (0, 0))

    #WIND: TUMBLING LEAVES AND FAINT GUST LINES
    for x, y, speed, phase, colour in leaves:
        w = 2 + int(abs(math.sin(phase)) * 3)
        pygame.draw.rect(screen, colour, (int(x), int(y), w, 2))
    if wind_amount > 0.3:
        gust = _layer("gust")
        gust.fill((0, 0, 0, 0))
        for i, (x, y, speed, phase, colour) in enumerate(leaves[:8]):
            length = 40 + 20 * speed
            pygame.draw.line(gust, (255, 255, 255, int(60 * wind_amount)),
                             (int(x) - 60 - length, int(y) + 12 * (i % 3)), (int(x) - 60, int(y) + 12 * (i % 3)), 1)
        screen.blit(gust, (0, 0))

    #SNOWFLAKES
    for x, y, size, _ in snow_flakes:
        pygame.draw.circle(screen, (240, 245, 255), (int(x), int(y)), 2 if size > 0.75 else 1)


def status_text():
    #WHAT THE WEATHER IS DOING TO THE PLAYER, AS (TEXT, COLOUR), OR None
    if player_near_fire:
        return "Warm by the fire", (255, 190, 90)
    if player_sheltered:
        return "Sheltered in your tent", (170, 220, 255)
    if survival.energy <= 0:
        return "Freezing!", (255, 90, 90)
    if current in (RAIN, COLD) or night_amount > 0.5:
        return "Exposed: losing energy", (200, 210, 255)
    return None
