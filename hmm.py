#HIDDEN MARKOV MODEL: READING THE SKY TO FORECAST THE WEATHER
#=============================================================
#THE WEATHER IS MADE BY A HIDDEN MARKOV MODEL:
#
#   HIDDEN STATES (WHAT THE ATMOSPHERE IS REALLY DOING, NEVER SHOWN DIRECTLY)
#       clear        calm weather
#       storm_front  a storm is building up (rain is on its way)
#       rain         heavy rain
#       cold_front   cold air is moving in (a cold snap is on its way)
#       cold         cold snap
#
#   OBSERVATIONS (WHAT YOU CAN SEE EVERY TICK)
#       sunny, clouds, wind, raining, snowing
#
#EVERY TICK (5 SECONDS OF GAME TIME) THE HIDDEN STATE MOVES ACCORDING TO THE TRANSITION
#MODEL T, AND THE SKY SHOWS ONE SIGN, DRAWN FROM THE EMISSION MODEL E. THE SIGNS ARE
#NOISY: A CALM SKY IS SOMETIMES CLOUDY, AND A STORM FRONT IS SOMETIMES SUNNY.
#
#THE AI (AND THE HUD FORECAST) ONLY SEES THE SIGNS. IT USES:
#   * FILTERING  (THE FORWARD ALGORITHM)   P(STATE NOW | ALL SIGNS SO FAR)
#   * PREDICTION                           P(RAIN / COLD STARTS WITHIN THE NEXT FEW TICKS)
#   * VITERBI                              THE MOST LIKELY SEQUENCE OF STATES (H PANEL)
import random

STATES = ["clear", "storm_front", "rain", "cold_front", "cold"]
OBSERVATIONS = ["sunny", "clouds", "wind", "raining", "snowing"]
CLEAR, STORM_FRONT, RAIN, COLD_FRONT, COLD = range(5)
SUNNY, CLOUDS, WIND, RAINING, SNOWING = range(5)

STATE_NAMES = ["Clear", "Storm building", "Rain", "Cold front", "Cold snap"]
OBSERVATION_NAMES = ["Sunny", "Clouds", "Wind", "Raining", "Snowing"]

TICK = 5000                 #MILLISECONDS OF GAME TIME BETWEEN TWO SIGNS
FORECAST_TICKS = 6          #"SOON" = WITHIN THE NEXT 6 TICKS (30 SECONDS)
WARNING_LEVEL = 0.45        #FROM THIS CHANCE ON, THE GAME WARNS YOU (AND THE AI PREPARES)

#CHANCE PER TICK THAT A CALM SKY STARTS TO TURN (difficulty.py RAISES THIS ON LATER DAYS)
FRONT_CHANCE = 0.06


def transition_model(front_chance=None):
    #T[i][j] = P(NEXT STATE = j | STATE NOW = i)
    f = FRONT_CHANCE if front_chance is None else front_chance
    return [
        #  clear     storm    rain   cold_f   cold
        [1 - f,     f / 2,   0.0,   f / 2,   0.0],     #clear: ~80 s on day 1
        [0.04,      0.78,    0.18,  0.0,     0.0],     #storm front: ~23 s, then rain (or it blows over)
        [0.15,      0.0,     0.85,  0.0,     0.0],     #rain: ~33 s
        [0.04,      0.0,     0.0,   0.78,    0.18],    #cold front: ~23 s, then cold
        [0.13,      0.0,     0.0,   0.0,     0.87],    #cold snap: ~38 s
    ]


#E[i][o] = P(SIGN = o | STATE = i)
EMISSION = [
    #  sunny  clouds  wind   raining  snowing
    [0.72,   0.16,   0.12,  0.0,     0.0],      #clear
    [0.08,   0.74,   0.18,  0.0,     0.0],      #storm front
    [0.0,    0.02,   0.0,   0.98,    0.0],      #rain
    [0.08,   0.16,   0.76,  0.0,     0.0],      #cold front
    [0.0,    0.02,   0.0,   0.0,     0.98],     #cold snap
]

PRIOR = [1.0, 0.0, 0.0, 0.0, 0.0]               #EVERY GAME STARTS ON A CALM DAY


def _normalise(values):
    total = sum(values)
    if total <= 0:
        return [1.0 / len(values)] * len(values)
    return [v / total for v in values]


def predict(belief, T):
    #ONE STEP OF THE MARKOV CHAIN: P(X_t+1) = SUM_i P(X_t = i) T[i][j]
    n = len(belief)
    return [sum(belief[i] * T[i][j] for i in range(n)) for j in range(n)]


def forward_step(belief, observation, T):
    #FILTERING (FORWARD ALGORITHM): PREDICT, THEN WEIGHT BY HOW WELL EACH STATE EXPLAINS THE SIGN
    predicted = predict(belief, T)
    return _normalise([predicted[j] * EMISSION[j][observation] for j in range(len(predicted))])


def chance_soon(belief, T, target, ticks=FORECAST_TICKS):
    #P(THE WEATHER BECOMES target AT SOME POINT IN THE NEXT `ticks` TICKS).
    #TRICK: MAKE target "STICKY" (ABSORBING), RUN THE CHAIN FORWARD, AND READ HOW MUCH
    #PROBABILITY HAS ENDED UP THERE
    sticky = [row[:] for row in T]
    sticky[target] = [1.0 if j == target else 0.0 for j in range(len(T))]
    b = belief[:]
    for _ in range(ticks):
        b = predict(b, sticky)
    return b[target]


def viterbi(observations, T, prior=PRIOR):
    #THE SINGLE MOST LIKELY SEQUENCE OF HIDDEN STATES THAT EXPLAINS THE SIGNS
    n = len(STATES)
    if not observations:
        return []
    tiny = 1e-300
    score = [prior[s] * EMISSION[s][observations[0]] for s in range(n)]
    back = []
    for o in observations[1:]:
        new_score, pointers = [], []
        for j in range(n):
            best_i = max(range(n), key=lambda i: score[i] * T[i][j])
            pointers.append(best_i)
            new_score.append(score[best_i] * T[best_i][j] * EMISSION[j][o])
        total = sum(new_score) or tiny
        score = [s / total for s in new_score]     #RESCALE SO THE NUMBERS DON'T UNDERFLOW
        back.append(pointers)
    state = max(range(n), key=lambda s: score[s])
    path = [state]
    for pointers in reversed(back):
        state = pointers[state]
        path.append(state)
    return path[::-1]


class WeatherFilter:
    #WHAT THE PLAYER / AI BELIEVES ABOUT THE HIDDEN WEATHER, UPDATED FROM THE SIGNS ONLY
    HISTORY = 12

    def __init__(self):
        self.reset()

    def reset(self):
        self.belief = PRIOR[:]
        self.signs = []
        self.rain_soon = 0.0
        self.cold_soon = 0.0

    def observe(self, observation, front_chance=None):
        T = transition_model(front_chance)
        self.belief = forward_step(self.belief, observation, T)
        self.signs = (self.signs + [observation])[-self.HISTORY:]
        self.rain_soon = chance_soon(self.belief, T, RAIN)
        self.cold_soon = chance_soon(self.belief, T, COLD)

    def most_likely(self):
        return max(range(len(self.belief)), key=lambda s: self.belief[s])

    def viterbi_path(self, front_chance=None):
        #VITERBI OVER THE RECENT SIGNS (STARTING FROM WHAT WE BELIEVED BEFORE THEM IS CLOSE
        #ENOUGH FOR A DISPLAY; THE FULL HISTORY WOULD GIVE THE SAME RECENT STATES)
        return viterbi(self.signs, transition_model(front_chance), prior=[0.6, 0.1, 0.1, 0.1, 0.1])


#----------------------------------------------------------------
# SAMPLING (USED BY weather.py TO MAKE THE ACTUAL WEATHER)
#----------------------------------------------------------------
def next_state(state, front_chance=None, rng=random):
    return rng.choices(range(len(STATES)), weights=transition_model(front_chance)[state], k=1)[0]


def emit(state, rng=random):
    return rng.choices(range(len(OBSERVATIONS)), weights=EMISSION[state], k=1)[0]


#----------------------------------------------------------------
# EVALUATION: python hmm.py
#----------------------------------------------------------------
if __name__ == "__main__":
    rng = random.Random(1)
    T = transition_model()
    filt = WeatherFilter()
    state = CLEAR
    states, signs = [], []
    correct = naive_correct = 0
    warned = hits = false_alarms = 0
    starts = 0
    steps = 20000
    beliefs_rain_soon = []
    for t in range(steps):
        state = next_state(state, rng=rng)
        sign = emit(state, rng)
        filt.observe(sign)
        states.append(state)
        signs.append(sign)
        beliefs_rain_soon.append(filt.rain_soon)
        correct += filt.most_likely() == state
        #NAIVE RULE: CLOUDS = STORM FRONT, WIND = COLD FRONT, SUNNY = CLEAR
        naive = {SUNNY: CLEAR, CLOUDS: STORM_FRONT, WIND: COLD_FRONT, RAINING: RAIN, SNOWING: COLD}[sign]
        naive_correct += naive == state

    #HOW EARLY DOES THE FORECAST WARN BEFORE RAIN STARTS?
    lead_times = []
    for t in range(1, steps):
        if states[t] == RAIN and states[t - 1] != RAIN:
            starts += 1
            lead = 0
            k = t - 1
            while k >= 0 and states[k] != RAIN and beliefs_rain_soon[k] >= WARNING_LEVEL:
                lead += 1
                k -= 1
            if lead > 0:
                hits += 1
                lead_times.append(lead)
    alarms = sum(1 for t in range(1, steps)
                 if beliefs_rain_soon[t] >= WARNING_LEVEL > beliefs_rain_soon[t - 1] and states[t] == CLEAR)
    vit = viterbi(signs[:2000], T)
    vit_acc = sum(a == b for a, b in zip(vit, states[:2000])) / 2000

    print(f"Filtering accuracy (most likely state)     : {correct / steps:.1%}")
    print(f"Naive 'trust the sign' accuracy            : {naive_correct / steps:.1%}")
    print(f"Viterbi accuracy (whole sequence, 2000)    : {vit_acc:.1%}")
    print(f"Rain spells warned in advance (>= {WARNING_LEVEL:.0%})     : {hits}/{starts} = {hits / max(1, starts):.1%}")
    if lead_times:
        print(f"Average warning time                       : {5 * sum(lead_times) / len(lead_times):.1f} s")
    print(f"False alarms (warning while really clear)  : {alarms}")
