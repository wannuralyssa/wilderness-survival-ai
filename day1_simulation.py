health = 100
hunger = 90
thirst = 80
energy = 60
is_alive = True
day = 1

def print_status():
    print(f"\nDay {day}")
    print("Survivor status")
    print(f"Health: {health}")
    print(f"Hunger: {hunger}")
    print(f"Thirst: {thirst}")
    print(f"Energy: {energy}\n")

def drink_water():
    global thirst
    thirst = max(thirst - 25, 0)

def eat_berries():
    global hunger
    hunger = max(hunger - 20, 0)

def wolf_attack():
    global health
    health = max(health - 25, 0)

def sleep():
    global energy
    energy = min(energy + 30, 100)

def check_hunger():
    if hunger >= 100:
        global health
        health = max(health - 10, 0)

def check_thirst():
    if thirst >= 100:
        global health
        health = max(health - 15, 0)

def check_death():
    global is_alive
    if health <= 0:
        is_alive = False

def end_day():
    global hunger, thirst
    hunger = min(hunger + 5, 100)
    thirst = min(thirst + 10, 100)
    check_hunger()
    check_thirst()
    check_death()
    print_status()


#print_status()
#drink_water()
#eat_berries()
#wolf_attack()
#sleep()
#end_day()

for day in range(1, 4):

    if not is_alive:
        break

    end_day()



        
    


##theoretically survivor can still continue action after dying so add if is_alive 
#check to prevent further actions after death 