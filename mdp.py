"""
MARKOV DECISION PROCESS (MDP) FOR THE AI SURVIVOR
=================================================

The real game has far too many details (exact positions, every number) to plan over directly,
so the AI plans over a SMALL, ABSTRACT version of the game:

  STATE  s = (health, food, water, energy, wood, stone, context, threat, shelter)
             each one put into a few "bins" (e.g. health = critical / hurt / healthy)
  ACTION a = a "macro-action" that takes a few seconds in the real game
             (gather wood, gather stone, eat, drink, build fire, build tent, rest, fight, flee)
  T(s'|s,a) = PROBABILITY of ending up in state s' after doing a in s (the transition model below)
  R(s,a,s') = REWARD: +1 for every step survived, penalties for low stats, a big penalty for dying
  gamma    = DISCOUNT FACTOR: how much the future matters compared with now

VALUE ITERATION finds V*(s), the best long-term reward from each state, by repeating the
Bellman update until it stops changing:

      V(s) <- max_a  sum_s'  T(s'|s,a) * [ R(s,a,s') + gamma * V(s') ]

The POLICY is then  pi(s) = argmax_a Q(s,a).  It is saved to mdp_policy.json so the game loads
instantly. Run  python mdp.py  to solve the MDP again after changing the model.
"""
import itertools
import json
import os

#----------------------------------------------------------------
# STATES
#----------------------------------------------------------------
HEALTH_LEVELS = ["critical", "hurt", "healthy"]     # <30, 30-69, 70+
FOOD_LEVELS = ["low", "ok"]                          # food bar (100 - hunger) <50, 50+
WATER_LEVELS = ["low", "ok"]                         # water bar (100 - thirst) <50, 50+
ENERGY_LEVELS = ["low", "mid", "high"]               # <30, 30-69, 70+
WOOD_LEVELS = ["0-2", "3", "4+"]                     # 3 wood = campfire, 4 wood = tent
STONE_LEVELS = ["0-1", "2+"]                         # 2 stone = campfire
CONTEXTS = ["day", "night", "rain", "cold"]
THREAT_LEVELS = ["none", "wolf"]                     # a wolf close by?
SHELTER_LEVELS = ["none", "fire", "tent"]            # is there a lit campfire or a tent to go back to?

DAY, NIGHT, RAIN, COLD = range(4)

VARIABLES = [HEALTH_LEVELS, FOOD_LEVELS, WATER_LEVELS, ENERGY_LEVELS, WOOD_LEVELS,
             STONE_LEVELS, CONTEXTS, THREAT_LEVELS, SHELTER_LEVELS]
SIZES = [len(v) for v in VARIABLES]
ALL_STATES = list(itertools.product(*[range(n) for n in SIZES]))
DEAD = "dead"
SHELTER_RANGE = 700          #A SHELTER COUNTS IF IT IS WITHIN THIS MANY PIXELS

#----------------------------------------------------------------
# ACTIONS
#----------------------------------------------------------------
ACTIONS = ["gather_wood", "gather_stone", "eat", "drink", "build_fire",
           "build_tent", "rest", "fight", "flee"]

#----------------------------------------------------------------
# MODEL PARAMETERS (ONE STEP IS ROUGHLY 8 SECONDS OF GAME TIME)
#----------------------------------------------------------------
GAMMA = 0.95

#CALIBRATED FROM THE GAME: HUNGER RISES ABOUT 25 AND THIRST ABOUT 32 PER DAY IN THE MIDDLE OF A
#RUN (difficulty.py), I.E. 2-3 POINTS PER 8-SECOND STEP, SO FALLING INTO "low" HAPPENS QUICKLY
FOOD_DROP = 0.06
WATER_DROP = 0.08
#CALIBRATED FROM THE GAME: EXPOSED ENERGY LOSS IS 0.3/s AT NIGHT, 0.6/s IN RAIN, 1.0/s IN COLD,
#SO OVER ONE 8-SECOND STEP THE CHANCE OF DROPPING A WHOLE ENERGY LEVEL (ABOUT 35 POINTS) IS:
ENERGY_DROP = {DAY: 0.02, NIGHT: 0.07, RAIN: 0.14, COLD: 0.23}

#RESTING: A CAMPFIRE GIVES +30 ENERGY AT ONCE PLUS 1.5/s, EVEN IN THE COLD.
#A TENT GIVES ONLY 0.4/s, AND IN A COLD SNAP YOU STILL LOSE 0.4/s INSIDE IT.
REST_ENERGY_GAIN = {1: 0.60, 2: 0.12}
TENT_COLD_DROP = 0.09

#HEALING: +1 HEALTH EVERY 3 s (TWICE AS FAST WHEN RESTING) -> CHANCE OF GOING UP A HEALTH LEVEL
HEAL_CHANCE = 0.08
HEAL_CHANCE_RESTING = 0.15

WOLF_APPEARS = {DAY: 0.10, NIGHT: 0.25, RAIN: 0.08, COLD: 0.12}
WOLF_STAYS = 0.75

#CALIBRATED FROM THE GAME: EACH HIT STUNS THE WOLF FOR 0.67 s AND YOUR SWING RECHARGES IN 0.4 s,
#SO A HEALTHY PLAYER USUALLY BEATS ONE WOLF (3 HITS) BEFORE IT CAN BITE MUCH.
#RUNNING AWAY OFTEN FAILS AT NIGHT, WHEN WOLVES CAN SMELL YOU FROM FURTHER AWAY.
FIGHT_HURT = 0.15
FIGHT_WINS = 0.85
FIGHT_ENERGY_DROP = 0.05
FLEE_HURT = 0.30
FLEE_ESCAPES = 0.50

CONTEXT_CHANGE = {
    DAY: {NIGHT: 0.12, RAIN: 0.06, COLD: 0.06},
    NIGHT: {DAY: 0.20},
    RAIN: {DAY: 0.30},
    COLD: {DAY: 0.25}
}

REWARD_ALIVE = 1.0
PENALTY_PER_LOW_STAT = 0.3
PENALTY_CRITICAL_HEALTH = 1.0
PENALTY_DEATH = -50.0

#BEING OUT IN THE OPEN AT NIGHT, IN RAIN OR IN THE COLD IS UNCOMFORTABLE AND DRAINS ENERGY.
#THIS PENALTY IS AVOIDED BY RESTING AT A SHELTER (LIT CAMPFIRE OR TENT)
EXPOSURE_PENALTY = {DAY: 0.0, NIGHT: 0.4, RAIN: 0.6, COLD: 0.8}


def _context_outcomes(ctx):
    changes = CONTEXT_CHANGE[ctx]
    outcomes = [(ctx, 1.0 - sum(changes.values()))]
    outcomes += list(changes.items())
    return outcomes


def transitions(state, action):
    """Returns a list of (probability, next_state, reward). next_state may be DEAD."""
    h, f, w, e, wood, stone, ctx, threat, shelter = state

    #--- WHAT THE ACTION ITSELF DOES ---------------------------------
    resting = action == "rest" and shelter > 0
    food_fixed = water_fixed = None
    energy_gain = 0.0
    wood_gain = stone_gain = 0.0
    built = 0                 #0 = NOTHING BUILT, 1 = CAMPFIRE, 2 = TENT
    new_wood, new_stone = wood, stone

    if action == "gather_wood":
        wood_gain = 0.6
    elif action == "gather_stone":
        stone_gain = 0.6
    elif action == "eat":
        food_fixed = 0.9          # PROBABILITY THE FOOD BAR ENDS UP "ok"
    elif action == "drink":
        water_fixed = 0.95
    elif action == "build_fire" and wood >= 1 and stone == 1 and ctx != RAIN:
        built, new_wood, new_stone = 1, 0, 0
    elif action == "build_tent" and wood == 2:
        built, new_wood = 2, 0
    elif resting:
        energy_gain = REST_ENERGY_GAIN[shelter]

    #--- HEALTH: CHANCE OF GETTING HURT, AND OF HEALING ----------------
    hurt_chances = []
    if threat == 1:
        hurt_chances.append({"fight": FIGHT_HURT, "flee": FLEE_HURT}.get(action, 0.60))
    if f == 0:
        hurt_chances.append(0.25)       # STARVING
    if w == 0:
        hurt_chances.append(0.30)       # DEHYDRATED
    if e == 0:
        hurt_chances.append(0.30)       # EXHAUSTED AND FREEZING
    p_not_hurt = 1.0
    for p in hurt_chances:
        p_not_hurt *= 1 - p
    p_hurt = 1 - p_not_hurt
    p_heal = 0.0
    if f == 1 and w == 1 and e >= 1 and threat == 0:
        p_heal = HEAL_CHANCE_RESTING if resting else HEAL_CHANCE
    health_outcomes = [(h - 1, p_hurt), (min(2, h + 1), (1 - p_hurt) * p_heal),
                       (h, (1 - p_hurt) * (1 - p_heal))]

    #--- FOOD, WATER, ENERGY --------------------------------------------
    if resting and shelter == 2 and ctx == COLD:
        energy_gain = 0.0         #A TENT DOESN'T WARM YOU UP IN A COLD SNAP
    p_food_ok = food_fixed if food_fixed is not None else (0.0 if f == 0 else 1 - FOOD_DROP)
    p_water_ok = water_fixed if water_fixed is not None else (0.0 if w == 0 else 1 - WATER_DROP)
    energy_drop = 0.0 if resting else ENERGY_DROP[ctx]
    if resting and shelter == 2 and ctx == COLD:
        energy_drop = TENT_COLD_DROP
    if action == "fight" and threat == 1:
        energy_drop = max(energy_drop, FIGHT_ENERGY_DROP)  # SWINGING COSTS ENERGY
    if energy_gain:
        energy_outcomes = [(min(2, e + 1), energy_gain), (e, 1 - energy_gain)]
    elif e == 0:
        energy_outcomes = [(0, 1.0)]
    else:
        energy_outcomes = [(e - 1, energy_drop), (e, 1 - energy_drop)]

    #--- RESOURCES -------------------------------------------------------
    wood_outcomes = [(min(2, new_wood + 1), wood_gain), (new_wood, 1 - wood_gain)] if wood_gain else [(new_wood, 1.0)]
    stone_outcomes = [(1, stone_gain), (new_stone, 1 - stone_gain)] if stone_gain else [(new_stone, 1.0)]

    #--- WOLVES ------------------------------------------------------------
    if threat == 1:
        p_gone = {"fight": FIGHT_WINS, "flee": FLEE_ESCAPES}.get(action, 1 - WOLF_STAYS)
        threat_outcomes = [(0, p_gone), (1, 1 - p_gone)]
    else:
        threat_outcomes = [(1, WOLF_APPEARS[ctx]), (0, 1 - WOLF_APPEARS[ctx])]

    #--- PUT EVERYTHING TOGETHER (ALL PARTS ARE INDEPENDENT) -----------
    results = {}
    for ctx2, p_ctx in _context_outcomes(ctx):
        #SHELTER: BUILDING ONE GIVES SHELTER; WALKING AWAY OR RAIN (PUTS OUT FIRES) CAN LOSE IT
        if built and not (built == 1 and ctx2 == RAIN):
            shelter_outcomes = [(built, 1.0)]
        elif shelter > 0:
            #TENTS STAY FOREVER; RAIN PUTS OUT CAMPFIRES
            p_keep = 0.0 if (shelter == 1 and ctx2 == RAIN and ctx != RAIN) else 1.0
            shelter_outcomes = [(shelter, p_keep), (0, 1 - p_keep)]
        else:
            shelter_outcomes = [(0, 1.0)]

        for (h2, p_h), (f2, p_f), (w2, p_w), (e2, p_e), (wd2, p_wd), (st2, p_st), (t2, p_t), (s2, p_s) in itertools.product(
                health_outcomes, [(1, p_food_ok), (0, 1 - p_food_ok)], [(1, p_water_ok), (0, 1 - p_water_ok)],
                energy_outcomes, wood_outcomes, stone_outcomes, threat_outcomes,
                shelter_outcomes):
            p = p_ctx * p_h * p_f * p_w * p_e * p_wd * p_st * p_t * p_s
            if p < 1e-6:
                continue
            if h2 < 0:
                key, reward = DEAD, PENALTY_DEATH
            else:
                key = (h2, f2, w2, e2, wd2, st2, ctx2, t2, s2)
                low = (f2 == 0) + (w2 == 0) + (e2 == 0)
                reward = REWARD_ALIVE - PENALTY_PER_LOW_STAT * low - PENALTY_CRITICAL_HEALTH * (h2 == 0)
                if not resting:
                    reward -= EXPOSURE_PENALTY[ctx]
                elif shelter == 2 and ctx == COLD:
                    reward -= EXPOSURE_PENALTY[ctx] / 2      #A TENT ONLY HALF-PROTECTS FROM COLD
            old = results.get(key)
            if old:
                results[key] = (old[0] + p, old[1])
            else:
                results[key] = (p, reward)
    return [(p, s2, r) for s2, (p, r) in results.items()]


#----------------------------------------------------------------
# VALUE ITERATION
#----------------------------------------------------------------
def value_iteration(tolerance=0.01, max_sweeps=500, verbose=True):
    index = {s: i for i, s in enumerate(ALL_STATES)}
    #PRE-COMPUTE THE MODEL ONCE: model[i][a] = [(prob, next_index or -1 for dead, reward), ...]
    model = []
    for s in ALL_STATES:
        model.append([[(p, index[s2] if s2 != DEAD else -1, r) for p, s2, r in transitions(s, a)]
                      for a in ACTIONS])

    V = [0.0] * len(ALL_STATES)
    for sweep in range(max_sweeps):
        biggest_change = 0.0
        for i in range(len(ALL_STATES)):
            best = max(sum(p * (r + (GAMMA * V[j] if j >= 0 else 0.0)) for p, j, r in outcomes)
                       for outcomes in model[i])
            biggest_change = max(biggest_change, abs(best - V[i]))
            V[i] = best
        if verbose:
            print(f"sweep {sweep + 1}: biggest change in V = {biggest_change:.4f}")
        if biggest_change < tolerance:
            break

    policy, q_values = [], []
    for i in range(len(ALL_STATES)):
        q = [sum(p * (r + (GAMMA * V[j] if j >= 0 else 0.0)) for p, j, r in outcomes)
             for outcomes in model[i]]
        q_values.append([round(x, 2) for x in q])
        policy.append(ACTIONS[q.index(max(q))])
    return V, policy, q_values


POLICY_FILE = "mdp_policy.json"


def solve_and_save(path=POLICY_FILE):
    V, policy, q_values = value_iteration()
    with open(path, "w") as f:
        json.dump({"actions": ACTIONS, "values": [round(v, 2) for v in V],
                   "policy": policy, "q": q_values}, f)
    return V, policy, q_values


_loaded = None


def load_policy(path=POLICY_FILE):
    #LOAD THE SOLVED POLICY (SOLVE IT FIRST IF THE FILE IS MISSING)
    global _loaded
    if _loaded is None:
        if not os.path.exists(path):
            print("Solving the MDP with value iteration (first run only)...")
            solve_and_save(path)
        with open(path) as f:
            _loaded = json.load(f)
    return _loaded


def state_index(state):
    i = 0
    for value, size in zip(state, SIZES):
        i = i * size + value
    return i


def describe(state):
    return ", ".join(f"{VARIABLES[k][v]}" for k, v in enumerate(state))


#----------------------------------------------------------------
# TURNING THE REAL GAME INTO AN ABSTRACT STATE
#----------------------------------------------------------------
#HMM + MDP: IF TRUE, THE AI TREATS "BAD WEATHER IS LIKELY SOON" (FROM THE HMM FORECAST)
#AS BAD WEATHER, SO IT PREPARES IN ADVANCE. SET TO FALSE TO COMPARE WITHOUT THE FORECAST.
USE_FORECAST = True


def forecast_context(weather_module):
    #RAIN OR COLD IF THE HMM SAYS IT IS LIKELY IN THE NEXT 30 SECONDS, ELSE None
    import hmm
    fc = weather_module.forecast
    if max(fc.rain_soon, fc.cold_soon) < hmm.WARNING_LEVEL:
        return None
    return RAIN if fc.rain_soon >= fc.cold_soon else COLD


def observe(survival, world_module, weather_module, player_rect, wolf_list):
    import math
    health = survival.health
    h = 0 if health < 30 else 1 if health < 70 else 2
    f = 0 if 100 - survival.hunger < 50 else 1
    w = 0 if 100 - survival.thirst < 50 else 1
    e = 0 if survival.energy < 30 else 1 if survival.energy < 70 else 2
    wood = world_module.wood
    wd = 0 if wood < 3 else 1 if wood == 3 else 2
    st = 1 if world_module.stone >= 2 else 0
    if weather_module.current == weather_module.RAIN:
        ctx = RAIN
    elif weather_module.current == weather_module.COLD:
        ctx = COLD
    elif USE_FORECAST and forecast_context(weather_module) is not None:
        #HMM: THE SKY SAYS BAD WEATHER IS LIKELY SOON, SO PLAN AS IF IT IS ALREADY HERE
        #(BUILD THE TENT / FIRE AND GET INSIDE BEFORE THE RAIN OR COLD ARRIVES)
        ctx = forecast_context(weather_module)
    elif weather_module.night_amount > 0.5:
        ctx = NIGHT
    else:
        ctx = DAY
    px, py = player_rect.center
    threat = int(any(math.hypot(wd_["rect"].centerx - px, wd_["rect"].centery - py) < 230 for wd_ in wolf_list))
    def near(things):
        return any(math.hypot(s.centerx - px, s.centery - py) < SHELTER_RANGE for s in things)
    shelter = 2 if near(world_module.tents) else 1 if near(world_module.lit_campfires()) else 0
    return (h, f, w, e, wd, st, ctx, threat, shelter)


if __name__ == "__main__":
    import time
    start = time.time()
    V, policy, _ = solve_and_save()
    print(f"Solved {len(ALL_STATES)} states x {len(ACTIONS)} actions in {time.time() - start:.1f} s")
    examples = [
        (2, 1, 1, 1, 0, 0, DAY, 0, 0),
        (2, 1, 0, 1, 0, 0, DAY, 0, 0),
        (2, 1, 1, 1, 2, 0, NIGHT, 0, 0),
        (2, 1, 1, 1, 1, 1, NIGHT, 0, 0),
        (2, 1, 1, 1, 1, 1, NIGHT, 0, 1),
        (2, 1, 1, 1, 0, 0, RAIN, 0, 2),
        (2, 1, 1, 1, 0, 0, NIGHT, 0, 2),
        (2, 1, 1, 0, 0, 0, COLD, 0, 1),
        (2, 1, 1, 2, 2, 1, RAIN, 0, 0),
        (2, 1, 1, 1, 0, 0, RAIN, 0, 0),
        (2, 1, 1, 2, 0, 0, DAY, 1, 0),
        (2, 1, 1, 2, 0, 0, DAY, 0, 2),
        (2, 1, 1, 1, 0, 0, DAY, 0, 2),
        (2, 1, 1, 0, 0, 0, NIGHT, 0, 0),
        (2, 1, 1, 1, 0, 0, COLD, 0, 0),
        (2, 1, 1, 1, 1, 1, COLD, 0, 0),
        (2, 1, 1, 0, 0, 0, DAY, 1, 0),
        (0, 1, 1, 1, 0, 0, DAY, 1, 0),
        (1, 1, 1, 1, 0, 0, DAY, 0, 0),
        (2, 1, 1, 2, 1, 1, DAY, 0, 0),
    ]
    for s in examples:
        print(f"{describe(s):70s} -> {policy[state_index(s)]}")
