# Wilderness AI Survival Simulator 🌲

A 2D survival game built with Python and Pygame as an individual Artificial Intelligence course project.

The player must survive in a wilderness environment by collecting resources, managing survival needs, and crafting useful items.

**Goal:** survive **10 days** until rescue comes. If you get there, you win: a search party spots your campfire smoke (**Rescued**), or, with no fire burning, you find your own way out of the forest (**Escaped**). Then you can keep going in endless mode. If your health reaches zero, the run ends with what killed you: the wolves, hunger, thirst, or the cold.

## 🎮 Current Features

- **Player movement:** Explore the environment using the arrow keys or WASD, with a walk cycle that alternates the legs.
- **Resource collection:** Gather wood, stone, wild berries, and water. Like in Minecraft, you hold E to chop a tree or mine a rock: the player swings, the tree or rock shakes, chips fly and a ring fills up; let go or walk away and the progress is lost. Harvested trees and rocks grow back after a while; each berry bush can be eaten from 3 times, then needs to grow back.
- **Music and sound:** Original music (menu, day and night themes that crossfade), ambient rain, wind and campfire sounds, footsteps that change with the ground, and effects for every action. All synthesized from code by `make_audio.py`: no samples or downloads.
- **Growing difficulty:** Every day the wilderness gets harsher (`difficulty.py`): more and tougher wolves, faster hunger and thirst, slower healing and regrowth, and more frequent, harsher bad weather. Every run eventually ends, so days survived is a real score.
- **Main menu:** Play yourself, watch the AI survive, read how to play, or quit (keyboard or mouse). Esc returns to the menu.
- **Survival system:** Manage health, hunger, thirst, and energy.
- **Healing:** Health slowly comes back (+1 every 3 s) while Food and Water are above half, energy isn't empty, and you haven't been bitten for 5 s. Twice as fast by a campfire or in a tent.
- **Crafting:** Collect resources to craft a campfire. Campfires are animated (flickering flames, rising embers, smoke when put out) and solid: you walk around them, not through them.
- **Resting:** Use campfires to restore energy.
- **Large scrolling world:** A 1600 x 1200 map with a camera that follows the player.
- **Height levels:** Plateaus (including a two-level lookout) with stepped cliffs that can only be climbed using stairs.
- **Rivers and paths:** A winding river with sandy banks and three bridges; dirt paths connect the areas and are faster to walk on.
- **Terrain:** Mud and tall grass slow movement; the river and ponds block the way.
- **Wolves:** Wolves wander, detect the player, and chase using A* search over a terrain-cost grid.
- **Combat:** Wolf bites take 10 health. Swing at wolves (3 hits to defeat one). Defeated wolves are replaced after 30 seconds, far from the player.
- **Smart wolves:** Up close, wolves lunge, circle (and dart in when you swing), or stalk. They choose using game theory, and the pack learns your habits and starts exploiting them.
- **Endings:** A victory story when you are rescued or escape after 10 days, and a defeat story that depends on what killed you.
- **Nightfall:** Darkness limits vision to a small light radius; wolves are harder to see but hunt from further away.
- **Heavy rain:** Reduces visibility, slows movement, drains energy and puts out campfires; build a tent for shelter.
- **Cold snaps:** Drain energy over time; stand near a campfire to warm up.
- **Readable skies (HMM weather):** Rain and cold snaps come from a Hidden Markov Model. Before bad weather the sky shows signs (drifting cloud shadows, wind with tumbling leaves), but the signs are noisy: clouds don't always mean rain. The HUD shows a forecast worked out from the signs only (e.g. "Rain 63% soon"), and H opens a panel with the full HMM reasoning. The game still warns you before nightfall.
- **Tent shelter:** Resting inside a tent closes it up: the canvas glows with a lantern, your shadow breathes on the canvas, rain drums on the roof, and "Zzz" floats up while you recover.
- **Full screen:** F11 switches to full screen (the window can also be resized); the game scales up and keeps its shape.
- **Survival progression:** Hunger and thirst rise steadily; at 100 the player starts losing health.
- **Game over system:** The game ends when the player's health reaches zero.

## 🕹️ Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Move the player |
| E (hold) | Chop a tree / mine a rock: hold E until the ring fills (about 1.6 s for wood, 2.2 s for stone) |
| E (press) | Drink, eat berries, rest at a campfire, relight a campfire (1 wood) |
| Space | Attack in the direction you are facing (costs 1 energy) |
| C | Craft a campfire (3 wood, 2 stone) |
| T | Build a tent (4 wood) |
| R / M / Q | Restart / main menu / quit on the game over screen |
| 1 / 2 / 3 / 4 | AI mode only: speed x1 / x2 / x4 / x8 |
| H | Show / hide the weather forecast panel (HMM) |
| G | Show / hide the wolf pack panel (game theory + machine learning) |
| C | After a victory: keep surviving (endless mode) |
| F11 | Full screen on / off |
| V | Sound on / off |

## 🛠️ Technologies

- Python 3.11
- Pygame 2.6.1
- Git and GitHub

## 🚀 How to Run

1. Clone this repository:

   ```bash
   git clone (https://github.com/wannuralyssa/wilderness-survival-ai.git)
   ```

2. Navigate into the project folder:

   ```bash
   cd wilderness-survival-ai
   ```

3. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   ```

   On Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

4. Install Pygame:

   ```bash
   pip install pygame
   ```

5. Run the game:

   ```bash
   python game.py
   ```

## 🧠 AI Concepts

| Concept | Status | Where |
|---|---|---|
| **Search Algorithms** | ✅ Implemented | Wolves chase with **A\*** (Manhattan heuristic) over a terrain-cost grid (`search.py`); BFS kept for comparison. The AI survivor also uses A\* to walk to its targets. |
| **Markov Decision Process (MDP)** | ✅ Implemented | `mdp.py`: the AI survivor's brain. Abstract states (health, food, water, energy, wood, stone, time/weather, wolf nearby, shelter), 9 macro-actions, a probabilistic transition model calibrated from the game's numbers, rewards for surviving, and **value iteration** to find the best policy. |
| **Hidden Markov Models (HMM)** | ✅ Implemented | `hmm.py`: the weather is generated by an HMM with a hidden sky state (clear, storm front, rain, cold front, cold snap) and noisy visible signs (sunny, clouds, wind, raining, snowing). The forecast uses the **forward algorithm** (filtering), **prediction** of rain / cold in the next 30 s, and **Viterbi** decoding (shown in the H panel). The AI feeds the forecast into its MDP so it prepares shelter before the weather turns. |
| **Game Theory** | ✅ Implemented | `game_theory.py`: every wolf encounter is a **zero-sum game** (you: attack / evade; wolf: lunge / circle / stalk) with payoffs from the game's numbers. A **support-enumeration solver** finds the **mixed Nash equilibrium**. Wolves start from it, and the AI survivor plays its equilibrium mix so it can't be exploited. |
| **Machine Learning** | ✅ Implemented | `pack_learning.py`: the wolf pack trains a **Naive Bayes classifier** (with Laplace smoothing) on every encounter round to predict whether you will attack or evade. The more it has seen, the more it blends the Nash strategy with the **best response** to its prediction. It remembers you between games (`pack_memory.json`), separately from the AI. |

### 🤖 AI mode ("Watch AI Survive")

Choose **Watch AI Survive** in the main menu to let the AI play. Every frame it:

1. **Observes** the game and converts it into an abstract MDP state.
2. **Decides** using the policy solved by value iteration (if the best action isn't possible right now, it takes the next-best by Q-value).
3. **Acts** with the same controls as a human: it plans a route with A\* and presses E / C / T / Space.

A panel shows what the AI is doing, why, the state it sees, and its top choices with their Q-values. Press 1-4 to fast-forward (x1, x2, x4, x8). Each AI run is logged to `ai_runs.csv`.

With the growing difficulty and the 10-day goal, the AI's results are logged in `ai_runs.csv` (days survived, wolves defeated, decisions and how the run ended). In 4 test runs with the smarter wolves, the AI was rescued once (day 11) and died on days 8, 8 and 5 (hunger and thirst twice, cold once).

### 🌦️ HMM weather forecasting

The true state of the sky is **hidden**. Every 5 seconds of game time it changes according to a transition model, and the sky shows one sign drawn from an emission model:

| Hidden state | Usually shows | Then becomes |
|---|---|---|
| Clear | Sunny (sometimes clouds or wind) | a storm front or a cold front, now and then |
| Storm front | Clouds | Rain (or it blows over) |
| Cold front | Wind | Cold snap (or it blows over) |
| Rain / Cold snap | Raining / Snowing | Clear |

Only the signs are visible, so the game keeps a **belief** (a probability for each hidden state) and updates it with the forward algorithm after every sign. From the belief it **predicts** the chance of rain or cold in the next 30 seconds. That forecast is shown on the HUD, and from 45% the game warns you. In AI mode, the agent treats "bad weather is likely soon" as bad weather in its MDP state, so it builds a tent or fire and gets inside *before* the rain or cold arrives.

Run `python hmm.py` to evaluate the model on 20,000 simulated ticks (filtering accuracy, Viterbi accuracy, how often and how early rain is forecast, false alarms). Set `USE_FORECAST = False` in `mdp.py` to compare the AI with and without the forecast.

### ⚔️ Wolf encounters: game theory + machine learning

When a wolf gets within reach, the fight is played in rounds of about 1.4 seconds. In each round both sides pick a tactic at the same time:

| You \ Wolf | Lunge (charge in) | Circle (dart in when you swing) | Stalk (hang back) |
|---|---|---|---|
| **Attack** (swing) | the lunge runs into your swing | you're bitten while open | you waste energy |
| **Evade** (back off) | the lunge often catches you | it can't reach you | it follows you |

No single tactic is safe for either side, so `game_theory.py` computes the **mixed Nash equilibrium** for the current situation. The payoffs change with today's bite damage, how hurt the wolf is, and whether you are by a campfire. Near a fire, lunging is too risky, so wolves stalk instead.

On top of that, the pack **learns** (`pack_learning.py`): after every round it records the situation (low health? by a fire? moving?) and what you did, and a Naive Bayes classifier predicts your next move. A predictable player gets exploited: if you always swing, the wolves circle more. A player who mixes like the Nash equilibrium can't be exploited, which is exactly what the AI survivor does. The **G** panel shows the current equilibrium, the pack's prediction, its accuracy and how much it is exploiting you.

Run `python game_theory.py` to see the equilibria and a simulation of learning wolves against an always-attacking player, an always-evading player, and a Nash player.

To change the MDP (e.g. rewards or probabilities), edit `mdp.py` and run `python mdp.py` to solve it again; the policy is saved to `mdp_policy.json`.

## 📌 Project Status

Currently under development. The basic survival mechanics and playable Pygame prototype are implemented. More gameplay features, visual improvements, and AI components will be added progressively.

---

Created as an individual Artificial Intelligence course project.

## Copyright

Copyright (c) 2026 Wan Alyssa. All rights reserved.

This project, including its original source code, documentation,
and original creative assets, is my own work.

No permission is granted to copy, redistribute, modify, or
commercially use this work without prior written permission,
except where applicable law or third-party licences permit otherwise.

Third-party libraries and assets remain subject to their
respective licences.

