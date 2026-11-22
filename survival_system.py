import random 

health = 100
hunger = 40
thirst = 50
energy = 60
is_alive = True

#WOLF BITES
WOLF_DAMAGE = 10

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

    health = 100
    hunger = 40
    thirst = 50
    energy = 60
    is_alive = True
