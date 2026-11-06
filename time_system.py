
import pygame
from config import *


def update_day_cycle(start_time, previous_elapsed_time, day):
    #CALCULATE ELAPSED TIME IN THE CURRENT DAY/NIGHT CYCLE
    elapsed_time = (
        pygame.time.get_ticks() - start_time
    ) % CYCLE_DURATION

    #DETERMINE WHETHER IT IS IGHTTIME
    is_night = elapsed_time >= DAY_DURATION

    #CHECK WHETHER A NEW DAY HAS STARTED
    day_changed = elapsed_time < previous_elapsed_time

    if day_changed:
        day += 1

    #STORE THE CURRENT ELAPSED TIME FOR THE NEXT UPDATE
    previous_elapsed_time = elapsed_time

    return elapsed_time, is_night, day, previous_elapsed_time, day_changed
