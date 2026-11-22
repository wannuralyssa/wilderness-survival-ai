# Wilderness AI Survival Simulator 🌲

A 2D survival game built with Python and Pygame as an individual Artificial Intelligence course project.

The player must survive in a wilderness environment by collecting resources, managing survival needs, and crafting useful items.

## 🎮 Current Features

- **Player movement:** Explore the environment using keyboard controls.
- **Resource collection:** Gather wood, stone, wild berries, and water. Harvested trees and rocks grow back after a while; each berry bush can be eaten from 3 times, then needs to grow back.
- **Growing difficulty:** Every day the wilderness gets harsher (`difficulty.py`): more and tougher wolves, faster hunger and thirst, slower healing and regrowth, and more frequent, harsher bad weather. Every run eventually ends, so days survived is a real score.
- **Main menu:** Play yourself, watch the AI survive, read how to play, or quit (keyboard or mouse). Esc returns to the menu.
- **Survival system:** Manage health, hunger, thirst, and energy.
- **Healing:** Health slowly comes back (+1 every 3 s) while Food and Water are above half, energy isn't empty, and you haven't been bitten for 5 s. Twice as fast by a campfire or in a tent.
- **Crafting:** Collect resources to craft a campfire.
- **Resting:** Use campfires to restore energy.
- **Large scrolling world:** A 1600 x 1200 map with a camera that follows the player.
- **Height levels:** Plateaus (including a two-level lookout) with stepped cliffs that can only be climbed using stairs.
- **Rivers and paths:** A winding river with sandy banks and three bridges; dirt paths connect the areas and are faster to walk on.
- **Terrain:** Mud and tall grass slow movement; the river and ponds block the way.
- **Wolves:** Wolves wander, detect the player, and chase using A* search over a terrain-cost grid.
- **Combat:** Wolf bites take 10 health. Swing at wolves (3 hits to defeat one). Defeated wolves are replaced after 30 seconds, far from the player.
- **Nightfall:** Darkness limits vision to a small light radius; wolves are harder to see but hunt from further away.
- **Heavy rain:** Reduces visibility, slows movement, drains energy and puts out campfires; build a tent for shelter.
- **Cold snaps:** Drain energy over time; stand near a campfire to warm up.
- **Weather warnings:** The game warns the player before night, rain or cold arrives.
- **Survival progression:** Hunger and thirst rise steadily; at 100 the player starts losing health.
- **Game over system:** The game ends when the player's health reaches zero.

## 🕹️ Controls

| Key | Action |
|---|---|
| Arrow keys | Move the player |
| E | Interact: collect, drink, eat, rest at a campfire, relight a campfire (1 wood) |
| Space | Attack in the direction you are facing (costs 1 energy) |
| C | Craft a campfire (3 wood, 2 stone) |
| T | Build a tent (4 wood) |
| R / M / Q | Restart / main menu / quit on the game over screen |
| 1 / 2 / 3 / 4 | AI mode only: speed x1 / x2 / x4 / x8 |

## 🛠️ Technologies

- Python 3.11
- Pygame 2.6.1
- Git and GitHub

## 🚀 How to Run

1. Clone this repository:

   ```bash
   git clone YOUR_GITHUB_REPOSITORY_URL
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
| **Hidden Markov Models (HMM)** | Planned | Reasoning about things the AI can't see directly. |
| **Game Theory** | Planned | Decision-making in wolf encounters. |
| **Machine Learning** | Planned | Learning from past AI runs (`ai_runs.csv`). |

### 🤖 AI mode ("Watch AI Survive")

Choose **Watch AI Survive** in the main menu to let the AI play. Every frame it:

1. **Observes** the game and converts it into an abstract MDP state.
2. **Decides** using the policy solved by value iteration (if the best action isn't possible right now, it takes the next-best by Q-value).
3. **Acts** with the same controls as a human: it plans a route with A\* and presses E / C / T / Space.

A panel shows what the AI is doing, why, the state it sees, and its top choices with their Q-values. Press 1-4 to fast-forward (x1, x2, x4, x8). Each AI run is logged to `ai_runs.csv`.

With the growing difficulty, the MDP agent currently survives around **9-11 days** in testing.

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
