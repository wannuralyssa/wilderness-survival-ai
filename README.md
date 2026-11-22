# Wilderness AI Survival Simulator 🌲

A 2D survival game built with Python and Pygame as an individual Artificial Intelligence course project.

The player must survive in a wilderness environment by collecting resources, managing survival needs, and crafting useful items.

## 🎮 Current Features

- **Player movement:** Explore the environment using keyboard controls.
- **Resource collection:** Gather wood, stone, wild berries, and water. Harvested trees and rocks grow back after a while.
- **Main menu:** Start the game, read how to play, or quit (keyboard or mouse).
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
- **Survival progression:** Hunger and thirst increase as each day passes.
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

## 🧠 AI Concepts (Planned)

The project aims to incorporate concepts from the Artificial Intelligence course:

- **Search Algorithms:** Wolves use A* search (Manhattan heuristic) over a terrain-cost grid; BFS is kept for comparison. *(Implemented)*
- **Game Theory:** Decision-making in dangerous situations.
- **Hidden Markov Models (HMM):** Reasoning about hidden environmental conditions.
- **Markov Decision Processes (MDP):** Choosing actions to maximize survival.
- **Machine Learning Basics:** Exploring simple learning-based decision-making.

These AI components are planned for future development.

## 📌 Project Status

Currently under development. The basic survival mechanics and playable Pygame prototype are implemented. More gameplay features, visual improvements, and AI components will be added progressively.

---

Created as an individual Artificial Intelligence course project.