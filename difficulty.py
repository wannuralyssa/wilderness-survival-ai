
#DIFFICULTY THAT GROWS EVERY DAY
#===============================
#WITHOUT THIS, DAY 20 IS EXACTLY AS EASY AS DAY 1 AND A GOOD PLAYER (OR AI) NEVER DIES.
#EACH NEW DAY THE WILDERNESS GETS HARSHER, SO EVERY RUN EVENTUALLY ENDS AND
#"DAYS SURVIVED" BECOMES A REAL SCORE. apply(day) IS CALLED AT THE START OF EVERY DAY.
import survival_system as survival
import wolves
import weather
import world


def settings(day):
    #ALL THE NUMBERS FOR A GIVEN DAY. d = 0 ON DAY 1, 1 ON DAY 2, ...
    d = max(0, day - 1)
    return {
        #WOLVES: MORE OF THEM, TOUGHER, FASTER, BETTER NOSES
        "wolf_count": min(4 + d // 2, 10),
        "wolf_health": min(3 + d // 4, 6),
        "wolf_damage": min(10 + 2 * (d // 2), 24),
        "wolf_speed": min(2.0 + 0.12 * d, 3.4),
        "wolf_detection_bonus": min(10 * d, 120),

        #HUNGER AND THIRST RISE FASTER EACH DAY (POINTS PER FULL DAY + NIGHT)
        "hunger_per_day": min(15 + 5 * d, 70),
        "thirst_per_day": min(20 + 6 * d, 90),

        #HEALING GETS SLOWER (MILLISECONDS PER +1 HEALTH)
        "regen_interval": int(3000 * (1 + 0.15 * d)),

        #BAD WEATHER: MORE OFTEN, AND IT DRAINS MORE ENERGY
        "clear_chance": max(0.4 - 0.03 * d, 0.1),
        "weather_drain": 1 + 0.1 * d,

        #TREES, ROCKS AND BERRY BUSHES TAKE LONGER TO GROW BACK
        "regrow_multiplier": 1 + 0.15 * d,
    }


def apply(day):
    s = settings(day)

    wolves.TARGET_WOLVES = s["wolf_count"]
    wolves.WOLF_MAX_HEALTH = s["wolf_health"]
    wolves.WOLF_SPEED = s["wolf_speed"]
    wolves.DETECTION_BONUS = s["wolf_detection_bonus"]
    survival.WOLF_DAMAGE = s["wolf_damage"]

    survival.HUNGER_PER_DAY = s["hunger_per_day"]
    survival.THIRST_PER_DAY = s["thirst_per_day"]
    survival.REGEN_INTERVAL = s["regen_interval"]

    bad = 1 - s["clear_chance"]
    weather.NEXT_WEATHER_CHANCE = {weather.CLEAR: s["clear_chance"], weather.RAIN: bad / 2, weather.COLD: bad / 2}
    weather.DIFFICULTY_DRAIN = s["weather_drain"]

    world.REGROW_MULTIPLIER = s["regrow_multiplier"]
    return s


def describe(day):
    s = settings(day)
    return f"{s['wolf_count']} wolves, bite -{s['wolf_damage']}"
