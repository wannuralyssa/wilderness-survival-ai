#MACHINE LEARNING: THE WOLF PACK LEARNS YOUR HABITS
#==================================================
#EVERY ENCOUNTER ROUND (SEE game_theory.py) THE PACK WRITES DOWN TWO THINGS:
#   * THE SITUATION AT THE START OF THE ROUND (FEATURES):
#       - is the player's health low?   - is the player by a campfire?   - was the player moving?
#   * WHAT THE PLAYER ACTUALLY DID (THE LABEL): ATTACK (swung) OR EVADE (backed away)
#
#FROM THESE EXAMPLES IT TRAINS A NAIVE BAYES CLASSIFIER:
#   P(tactic | features)  ~  P(tactic) * P(feature 1 | tactic) * P(feature 2 | tactic) * ...
#(WITH LAPLACE SMOOTHING SO AN UNSEEN COMBINATION IS NEVER IMPOSSIBLE).
#
#AT THE START OF EACH ROUND A WOLF PREDICTS WHAT YOU WILL DO AND BLENDS TWO STRATEGIES:
#   * THE NASH EQUILIBRIUM (SAFE: CAN'T BE EXPLOITED)
#   * THE BEST RESPONSE TO THE PREDICTION (EXPLOITS YOUR HABITS)
#THE MORE EXAMPLES IT HAS SEEN, THE MORE IT TRUSTS THE PREDICTION. IF YOU ARE PREDICTABLE
#(E.G. YOU ALWAYS SWING), THE WOLVES START CIRCLING AND PUNISHING YOUR SWINGS. MIX IT UP!
#
#THE PACK REMEMBERS BETWEEN GAMES (pack_memory.json), SEPARATELY FOR YOU AND FOR THE AI.
import json
import os

import game_theory as gt

FEATURE_NAMES = ["low health", "by a fire", "was moving"]
CLASSES = gt.PLAYER_TACTICS          #ATTACK, EVADE
TRUST_HALF = 25                      #AFTER THIS MANY EXAMPLES THE PACK TRUSTS ITS MODEL 50%
MEMORY_FILE = "pack_memory.json"


class PackModel:
    def __init__(self, data=None):
        data = data or {}
        n_f = len(FEATURE_NAMES)
        self.class_counts = data.get("class_counts", [0, 0])
        #feature_counts[c][f] = HOW OFTEN FEATURE f WAS TRUE WHEN THE PLAYER PLAYED c
        self.feature_counts = data.get("feature_counts", [[0] * n_f for _ in CLASSES])
        self.correct = data.get("correct", 0)
        self.predicted = data.get("predicted", 0)
        #MEASURED PAYOFF OF EACH (PLAYER, WOLF) PAIR: [SUM, COUNT] (COMPARE WITH THE DESIGNED MATRIX)
        self.outcomes = data.get("outcomes", [[[0.0, 0] for _ in gt.WOLF_TACTICS] for _ in CLASSES])

    def to_dict(self):
        return {"class_counts": self.class_counts, "feature_counts": self.feature_counts,
                "correct": self.correct, "predicted": self.predicted, "outcomes": self.outcomes}

    @property
    def examples(self):
        return sum(self.class_counts)

    def predict(self, features):
        #NAIVE BAYES WITH LAPLACE SMOOTHING. RETURNS [P(ATTACK), P(EVADE)]
        total = self.examples
        scores = []
        for c in range(len(CLASSES)):
            score = (self.class_counts[c] + 1) / (total + len(CLASSES))
            for f, value in enumerate(features):
                p_true = (self.feature_counts[c][f] + 1) / (self.class_counts[c] + 2)
                score *= p_true if value else 1 - p_true
            scores.append(score)
        s = sum(scores)
        return [x / s for x in scores]

    def confidence(self):
        n = self.examples
        return n / (n + TRUST_HALF)

    def update(self, features, label):
        #SCORE THE PREDICTION FIRST (SO THE ACCURACY IS HONEST), THEN LEARN FROM THE EXAMPLE
        if self.examples >= 5:
            guess = max(range(len(CLASSES)), key=lambda c: self.predict(features)[c])
            self.correct += guess == label
            self.predicted += 1
        self.class_counts[label] += 1
        for f, value in enumerate(features):
            self.feature_counts[label][f] += int(bool(value))

    def record_outcome(self, player_tactic, wolf_tactic, payoff):
        cell = self.outcomes[player_tactic][wolf_tactic]
        cell[0] += payoff
        cell[1] += 1

    def accuracy(self):
        return self.correct / self.predicted if self.predicted else None


def wolf_mix(A, nash_mix, model, features):
    #BLEND THE NASH EQUILIBRIUM WITH THE BEST RESPONSE TO WHAT THE MODEL PREDICTS
    if model.examples < 5:
        return list(nash_mix)
    prediction = model.predict(features)
    best = gt.wolf_best_response(A, prediction)
    trust = model.confidence()
    return [(1 - trust) * q + (trust if j == best else 0.0) for j, q in enumerate(nash_mix)]


#----------------------------------------------------------------
# MEMORY BETWEEN GAMES
#----------------------------------------------------------------
models = {"play": PackModel(), "ai": PackModel()}


def load():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE) as f:
                data = json.load(f)
            for key in models:
                models[key] = PackModel(data.get(key))
    except (OSError, ValueError):
        pass


def save():
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump({key: model.to_dict() for key, model in models.items()}, f)
    except OSError:
        pass


def forget(mode):
    #START THE PACK'S MEMORY OF THIS PLAYER AGAIN
    models[mode] = PackModel()
    save()
