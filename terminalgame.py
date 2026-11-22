
import survival_system as survival

running = True
day = 1

player_name = input("What is your survivor's name?\n")
print(f"Welcome to the wilderness, {player_name}!")
print(f"\nDay {day} begins.")


def choose_action():
    global running, day

    choice = input("\nWhat would you like to do?\n"
                   "1. Eat berries\n" 
                   "2. Drink water\n"
                   "3. Sleep\n"
                   "4. Explore\n"
                   "5. Quit game\n"
                   "Enter your choice (1-5): ")

    if choice == "1":
        survival.eat_berries()
        survival.print_status()
    elif choice == "2":
        survival.drink_water()
        survival.print_status()
    elif choice == "3":
        survival.sleep()
        survival.print_status()
    elif choice == "4":
        survival.explore()
        survival.end_day()
        print(f"\nDay {day} has ended.\n")
        if survival.is_alive:
            day += 1
            print(f"\nDay {day} begins.")
    elif choice == "5":
     print("You quit the game.")
     running = False
    else:
        print("Invalid choice. Please try again.")

def continue_game():
    global running

    survival.print_status()

    while running and survival.is_alive:
        choose_action()

    if survival.is_alive:
        print("Thanks for playing!")
    else:
        print("Your survival journey has come to an end.")

continue_game()