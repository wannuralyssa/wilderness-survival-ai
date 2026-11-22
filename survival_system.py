import random 

health = 100
hunger = 40
thirst = 50
energy = 60
is_alive = True

#WOLF BITES (difficulty.py RAISES THIS AS THE DAYS GO BY)
WOLF_DAMAGE = 10

#HUNGER AND THIRST RISE STEADILY DURING THE DAY (POINTS PER FULL DAY + NIGHT)
HUNGER_PER_DAY = 15
THIRST_PER_DAY = 20
_need_buffer = [0.0, 0.0]
_starve_timer = 0

#HEALTH REGENERATION: +1 HEALTH EVERY REGEN_INTERVAL MILLISECONDS, BUT ONLY WHEN
#FED, HYDRATED, NOT EXHAUSTED, AND NOT BITTEN RECENTLY
REGEN_INTERVAL = 3000
REGEN_MIN_FOOD = 50          #FOOD BAR (100 - HUNGER) MUST BE AT LEAST THIS
REGEN_MIN_WATER = 50         #WATER BAR (100 - THIRST) MUST BE AT LEAST THIS
REGEN_DELAY_AFTER_HIT = 5000
regenerating = False
_regen_timer = 0
_time_since_hit = 999999

def print_status():
    print("\n========== Survivor status ==========")
    print(f"Health: {health}")
    print(f"Hunger: {hunger}")
    print(f"Thirst: {thirst}")
    print(f"Energy: {energy}")
    print("=====================================")

def eat_berries():
    global hunger
    hunger = max(hunger - 15, 0)
    print("You eat berries! Your hunger decreases by 15.")

def drink_water():
    global thirst
    thirst = max(thirst - 20, 0)
    print("You drink water! Your thirst decreases by 20.")

def wolf_attack():
    global health, _time_since_hit
    health = max(health - WOLF_DAMAGE, 0)
    _time_since_hit = 0
    print(f"A wolf attacks you! You lost {WOLF_DAMAGE} health.")

def regenerate(dt, resting=False):
    #CALL EVERY FRAME. dt = MILLISECONDS SINCE LAST FRAME.
    #resting = BY A CAMPFIRE OR IN A TENT (HEALS TWICE AS FAST)
    global health, regenerating, _regen_timer, _time_since_hit
    _time_since_hit += dt

    regenerating = (
        is_alive
        and health < 100
        and 100 - hunger >= REGEN_MIN_FOOD
        and 100 - thirst >= REGEN_MIN_WATER
        and energy > 0
        and _time_since_hit >= REGEN_DELAY_AFTER_HIT
    )
    if not regenerating:
        _regen_timer = 0
        return

    _regen_timer += dt * (2 if resting else 1)
    while _regen_timer >= REGEN_INTERVAL:
        health = min(100, health + 1)
        _regen_timer -= REGEN_INTERVAL

def drain_needs(dt, day_length):
    #CALL EVERY FRAME. HUNGER AND THIRST GO UP A LITTLE ALL THE TIME;
    #AT 100 THE PLAYER STARTS LOSING HEALTH (STARVING / DEHYDRATED)
    global hunger, thirst, health, _starve_timer
    _need_buffer[0] += HUNGER_PER_DAY * dt / day_length
    _need_buffer[1] += THIRST_PER_DAY * dt / day_length
    if _need_buffer[0] >= 1:
        hunger = min(100, hunger + int(_need_buffer[0]))
        _need_buffer[0] -= int(_need_buffer[0])
    if _need_buffer[1] >= 1:
        thirst = min(100, thirst + int(_need_buffer[1]))
        _need_buffer[1] -= int(_need_buffer[1])

    if hunger >= 100 or thirst >= 100:
        _starve_timer += dt
        while _starve_timer >= 1500:
            health = max(0, health - 1)
            _starve_timer -= 1500
        check_death()
    else:
        _starve_timer = 0

def sleep():
    global energy
    energy = min(energy + 30, 100)
    print("You sleep and regain energy!")

def check_hunger():
    global health
    if hunger >= 100:
        health = max(health - 10, 0)
        print("You are starving! You lost 10 health.")

def check_thirst():
    global health
    if thirst >= 100:
        health = max(health - 15, 0)
        print("You are dehydrated! You lost 15 health.")

def check_death():
    global is_alive
    if health <= 0:
        is_alive = False
        print("GAME OVER! Your survivor has died.")

def end_day():
    global hunger, thirst
    hunger = min(hunger + 5, 100)
    thirst = min(thirst + 10, 100)
    check_hunger()
    check_thirst()
    check_death()
    print_status()

def explore():
    events = ["berries", "water", "wolf", "nothing"]
    event = random.choices(events, weights=[0.35, 0.30, 0.15, 0.20], k=1)[0]

    if event == "berries":
        print("You found some wild berries!")
        eat_berries()
    elif event == "water":
        print("You discovered a freshwater source!")
        drink_water()
    elif event == "wolf":
        print("You encountered a dangerous wolf!")
        wolf_attack()
    else:
        print("You found nothing interesting.")

def reset_survival():
    global health, hunger, thirst, energy, is_alive
    global regenerating, _regen_timer, _time_since_hit
    regenerating = False
    _regen_timer = 0
    _time_since_hit = 999999
    global _starve_timer
    _need_buffer[0] = _need_buffer[1] = 0.0
    _starve_timer = 0

    health = 100
    hunger = 40
    thirst = 50
    energy = 60
    is_alive = True
