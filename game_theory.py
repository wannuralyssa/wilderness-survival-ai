#GAME THEORY: WOLF ENCOUNTERS AS A ZERO-SUM GAME
#===============================================
#WHEN A WOLF GETS CLOSE, EACH "ROUND" (ABOUT 1.4 SECONDS) BOTH SIDES PICK A TACTIC AT THE
#SAME TIME, WITHOUT KNOWING WHAT THE OTHER WILL DO:
#
#   PLAYER: ATTACK  stand your ground and swing
#           EVADE   back away and keep your distance
#
#   WOLF:   LUNGE   charge straight in and bite
#           CIRCLE  circle just out of reach, and dart in when you swing (you're open)
#           STALK   hang back and follow you, waiting
#
#THE PAYOFF (TO THE PLAYER, IN "HEALTH POINTS") OF EACH PAIR COMES FROM THE GAME'S OWN
#NUMBERS: HOW HARD WOLVES BITE TODAY, HOW HURT THE WOLF IS, AND WHETHER YOU ARE BY A FIRE.
#THE WOLF GETS THE NEGATIVE (ZERO-SUM). NO PURE TACTIC IS SAFE (ATTACK LOSES TO CIRCLE,
#EVADE LOSES TO LUNGE), SO THE SOLUTION IS A MIXED NASH EQUILIBRIUM: PLAY EACH TACTIC WITH
#A CERTAIN PROBABILITY, SO THE OTHER SIDE CAN'T EXPLOIT YOU.
from itertools import combinations

PLAYER_TACTICS = ["attack", "evade"]
WOLF_TACTICS = ["lunge", "circle", "stalk"]
ATTACK, EVADE = 0, 1
LUNGE, CIRCLE, STALK = 0, 1, 2

KILL_VALUE = 18         #DEFEATING A WOLF IS WORTH ABOUT THIS MUCH HEALTH (ONE FEWER THREAT)
HIT_VALUE = 6           #A HIT THAT STUNS AND HURTS A WOLF
FIRE_VALUE = 6          #A WOLF THAT CHARGES INTO FIRELIGHT GETS SCARED OFF


def payoff_matrix(bite_damage=10, wolf_health=3, near_fire=False):
    #A[i][j] = PAYOFF TO THE PLAYER WHEN THE PLAYER PLAYS i AND THE WOLF PLAYS j
    D = bite_damage
    hit = HIT_VALUE + (KILL_VALUE - HIT_VALUE if wolf_health <= 1 else 0)
    fire = FIRE_VALUE if near_fire else 0
    return [
        #   lunge                circle      stalk
        [hit - 0.3 * D + fire,   -D - 1,     -1.0],      #attack: a swing meets the lunge, misses the circler
        [-0.5 * D + fire,        0.0,        -0.5],      #evade: a lunge often catches you; circling can't
    ]


#----------------------------------------------------------------
# SOLVING THE GAME (SUPPORT ENUMERATION, EXACT FOR SMALL GAMES)
#----------------------------------------------------------------
def _solve_linear(M, b):
    #GAUSSIAN ELIMINATION; RETURNS None IF THE SYSTEM HAS NO UNIQUE SOLUTION
    n = len(M)
    A = [row[:] + [b[i]] for i, row in enumerate(M)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[pivot][col]) < 1e-12:
            return None
        A[col], A[pivot] = A[pivot], A[col]
        for r in range(n):
            if r != col:
                f = A[r][col] / A[col][col]
                for c in range(col, n + 1):
                    A[r][c] -= f * A[col][c]
    return [A[i][n] / A[i][i] for i in range(n)]


def _mix_for(A, rows, cols, row_player):
    #THE MIX OVER `rows` THAT MAKES THE OTHER PLAYER INDIFFERENT BETWEEN ALL `cols`
    #UNKNOWNS: ONE PROBABILITY PER ROW + THE VALUE v
    k = len(rows)
    M, b = [], []
    for c in cols:
        if row_player:
            M.append([A[r][c] for r in rows] + [-1.0])
        else:
            M.append([A[c][r] for r in rows] + [-1.0])
        b.append(0.0)
    M.append([1.0] * k + [0.0])
    b.append(1.0)
    sol = _solve_linear(M, b)
    if sol is None or any(p < -1e-9 for p in sol[:k]):
        return None
    return [max(0.0, p) for p in sol[:k]], sol[k]


def solve_zero_sum(A):
    #NASH EQUILIBRIUM OF A ZERO-SUM GAME. RETURNS (PLAYER MIX, WOLF MIX, VALUE TO THE PLAYER)
    m, n = len(A), len(A[0])
    best = None
    for k in range(1, min(m, n) + 1):
        for rows in combinations(range(m), k):
            for cols in combinations(range(n), k):
                found_p = _mix_for(A, rows, cols, True)
                found_q = _mix_for(A, cols, rows, False)
                if found_p is None or found_q is None:
                    continue
                p_sub, v = found_p
                q_sub, _ = found_q
                p = [0.0] * m
                q = [0.0] * n
                for r, value in zip(rows, p_sub):
                    p[r] = value
                for c, value in zip(cols, q_sub):
                    q[c] = value
                #CHECK: NO TACTIC OUTSIDE THE SUPPORTS DOES BETTER FOR EITHER SIDE
                player_payoffs = [sum(A[i][j] * q[j] for j in range(n)) for i in range(m)]
                wolf_payoffs = [sum(A[i][j] * p[i] for i in range(m)) for j in range(n)]
                if max(player_payoffs) <= v + 1e-7 and min(wolf_payoffs) >= v - 1e-7:
                    if best is None or k < best[0]:
                        best = (k, p, q, v)
        if best is not None:
            break
    _, p, q, v = best
    return p, q, v


_cache = {}


def equilibrium(bite_damage, wolf_health, near_fire):
    key = (round(bite_damage), min(wolf_health, 2), bool(near_fire))
    if key not in _cache:
        _cache[key] = solve_zero_sum(payoff_matrix(*key))
    return _cache[key]


def wolf_best_response(A, player_mix):
    #THE WOLF TACTIC THAT HURTS A PLAYER WHO PLAYS player_mix THE MOST
    n = len(A[0])
    expected = [sum(A[i][j] * player_mix[i] for i in range(len(A))) for j in range(n)]
    return min(range(n), key=lambda j: expected[j])


#----------------------------------------------------------------
# python game_theory.py : THE EQUILIBRIA, AND WHY LEARNING WOLVES PUNISH PREDICTABLE PLAYERS
#----------------------------------------------------------------
if __name__ == "__main__":
    import random

    def show(title, A):
        p, q, v = solve_zero_sum(A)
        print(title)
        for i, row in enumerate(A):
            print(f"   {PLAYER_TACTICS[i]:>6}: " + "  ".join(f"{x:7.1f}" for x in row))
        print("   player : " + ", ".join(f"{t} {x:.0%}" for t, x in zip(PLAYER_TACTICS, p)))
        print("   wolf   : " + ", ".join(f"{t} {x:.0%}" for t, x in zip(WOLF_TACTICS, q)))
        print(f"   value  : {v:.2f} health per round for the player\n")

    show("Day 1 (bite 10), healthy wolf:", payoff_matrix(10, 3, False))
    show("Day 1, wolf on its last hit point:", payoff_matrix(10, 1, False))
    show("Day 1, player standing by a campfire:", payoff_matrix(10, 3, True))
    show("Day 10 (bite 18), healthy wolf:", payoff_matrix(18, 3, False))

    #SIMULATE 400 ROUNDS AGAINST DIFFERENT PLAYERS: WOLVES THAT ONLY PLAY NASH VS WOLVES
    #THAT LEARN THE PLAYER'S HABITS (pack_learning.py) AND EXPLOIT THEM
    import pack_learning
    A = payoff_matrix(10, 3, False)
    p_star, q_star, value = solve_zero_sum(A)
    players = {"always attacks (90%)": 0.9, "always evades (90%)": 0.1, "plays Nash": p_star[ATTACK]}
    print("Average health per round for the player (400 rounds):")
    for name, attack_rate in players.items():
        results = []
        for learning in (False, True):
            rng = random.Random(3)
            model = pack_learning.PackModel()
            total = 0.0
            for _ in range(400):
                features = (0, 0, 0)
                mix = pack_learning.wolf_mix(A, q_star, model, features) if learning else q_star
                wolf = rng.choices(range(3), weights=mix)[0]
                player = ATTACK if rng.random() < attack_rate else EVADE
                total += A[player][wolf]
                model.update(features, player)
            results.append(total / 400)
        print(f"   {name:<22} Nash wolves {results[0]:6.2f}   learning wolves {results[1]:6.2f}")
    print(f"   (the game's value is {value:.2f}: a Nash player gets this whatever the wolves do)")
