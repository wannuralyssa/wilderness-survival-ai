health = 100
hunger = 100
thirst = 100
energy = 60

def print_status():
    print("\nSurvivor status")
    print(f"Health: {health}")
    print(f"Hunger: {hunger}")
    print(f"Thirst: {thirst}")
    print(f"Energy: {energy}\n")

def drink_water():
    global thirst
    thirst = max(thirst - 25, 0)
    print("You drink water.")

def eat_berries():
    global hunger
    hunger = max(hunger - 20, 0)
    print("You eat berries.")

def wolf_attack():
    global health
    health = max(health - 25, 0)
    print("A wolf attacks you!")

def sleep():
    global energy
    energy = min(energy + 30, 100)
    print("You sleep and regain energy.")

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

check_hunger()
check_thirst()
print_status()


