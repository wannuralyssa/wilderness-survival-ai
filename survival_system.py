import random 

health = 100
hunger = 40
thirst = 50
energy = 60
is_alive = True

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
    global health
    health = max(health - 20, 0)
    print("A wolf attacks you! You lost 20 health.")

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

    health = 100
    hunger = 40
    thirst = 50
    energy = 60
    is_alive = True





