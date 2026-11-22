"""
AI SURVIVOR
===========
Plays the game with the same controls as a human (move, E, C, T, Space), in three layers:

  1. OBSERVE  : turn the real game into the small abstract state used by the MDP (mdp.observe)
  2. DECIDE   : look up the best action for that state in the policy solved by value iteration.
                If that action is impossible right now (e.g. no shelter to rest at), take the
                action with the next-highest Q-value.
  3. ACT      : carry the action out: plan a route with A* search, walk it, then press the
                right key (E to collect/drink/eat/rest, C campfire, T tent, Space attack).
"""
import math
import random
import pygame
import game_clock
import mdp
import search
import world
import weather
import survival_system as survival
import wolves as wolves_module

CELL = world.CELL_SIZE
PLAYER_SPEED = 3.5            #SAME AS player_speed IN game.py
DECISION_INTERVAL = 3000        #RE-CHECK THE DECISION EVERY 3 SECONDS
STUCK_FRAMES = 45               #NO PROGRESS FOR THIS MANY FRAMES = STUCK, PLAN AGAIN
TASK_TIMEOUT = 15000            #GIVE UP ON A TASK AFTER 15 SECONDS
TIE_MARGIN = 0.03               #Q-VALUES THIS CLOSE COUNT AS A TIE
PREFERENCE = ["build_fire", "build_tent", "drink", "eat", "gather_stone", "gather_wood",
              "rest", "flee", "fight"]

ACTION_LABELS = {
    "gather_wood": "Gather wood",
    "gather_stone": "Gather stone",
    "eat": "Eat berries",
    "drink": "Drink water",
    "build_fire": "Build a campfire",
    "build_tent": "Build a tent",
    "rest": "Rest at shelter",
    "fight": "Fight the wolf",
    "flee": "Flee from the wolf"
}


class Controls:
    #WHAT THE AI "PRESSES" THIS FRAME
    def __init__(self):
        self.dx = 0
        self.dy = 0
        self.actions = []       #ANY OF: "interact", "campfire", "tent", "attack"


#----------------------------------------------------------------
# HELPERS
#----------------------------------------------------------------
def cell_of(rect):
    return rect.centery // CELL, rect.centerx // CELL


def cell_rect(cell):
    r, c = cell
    return pygame.Rect(c * CELL, r * CELL, 40, 40)


def cell_center(cell):
    r, c = cell
    return c * CELL + 20, r * CELL + 20


def free(cell):
    grid = world.get_cost_grid()
    r, c = cell
    return 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] is not None


def first_interaction(rect):
    #WHAT PRESSING E WOULD DO WITH THE PLAYER AT rect (SAME ORDER AS interactions.py)
    for i, fire in enumerate(world.campfires):
        if rect.colliderect(fire.inflate(50, 50)):
            return "campfire", i
    if world.near_water(rect):
        return "water", None
    for i, bush in enumerate(world.berry_bushes):
        if rect.colliderect(bush.inflate(40, 40)):
            return "bush", i
    for i, tree in enumerate(world.trees):
        if rect.colliderect(tree.inflate(40, 40)):
            return "tree", i
    for i, rock in enumerate(world.rocks):
        if rect.colliderect(rock.inflate(40, 40)):
            return "rock", i
    return None, None


def nearest_wolf(player_rect, wolf_list):
    best, best_d = None, 1e9
    for wolf_data in wolf_list:
        d = math.hypot(wolf_data["rect"].centerx - player_rect.centerx,
                       wolf_data["rect"].centery - player_rect.centery)
        if d < best_d:
            best, best_d = wolf_data, d
    return best, best_d


#----------------------------------------------------------------
# THE AGENT
#----------------------------------------------------------------
class Agent:
    def __init__(self):
        self.policy = mdp.load_policy()
        self.water_cells = None
        self.reset()

    def reset(self):
        self.task = None
        self.state = None
        self.decision_time = -99999
        self.excluded = {}          #TARGETS TO AVOID FOR A WHILE: {key: until_time}
        self.last_reason = ""
        self.decisions = 0
        self.failed_until = {}      #ACTIONS THAT JUST FAILED: DON'T RETRY THEM FOR A FEW SECONDS

    #------------------------------------------------------------
    # DECIDE
    #------------------------------------------------------------
    def ranked_actions(self, state):
        #ACTIONS FROM BEST TO WORST Q-VALUE. WHEN SEVERAL ARE PRACTICALLY EQUAL (WITHIN TIE_MARGIN),
        #PREFER THE MORE PRODUCTIVE ONE (E.G. GATHER INSTEAD OF RESTING ON A SAFE, SUNNY DAY)
        q = self.policy["q"][mdp.state_index(state)]
        best = max(q)
        def key(item):
            action, value = item
            tied = value >= best - TIE_MARGIN
            return (0 if tied else 1, PREFERENCE.index(action) if tied else 0, -value)
        return sorted(zip(self.policy["actions"], q), key=key)

    def feasible(self, action, player_rect, wolf_list):
        if self.failed_until.get(action, 0) > game_clock.now():
            return False
        if action == "build_fire":
            return world.wood >= 3 and world.stone >= 2 and weather.current != weather.RAIN
        if action == "build_tent":
            return world.wood >= 4
        if action == "rest":
            return self.state[8] > 0
        if action in ("fight", "flee"):
            return self.state[7] == 1
        #DON'T DO THINGS THAT ARE POINTLESS RIGHT NOW (THE ABSTRACT MODEL CAN'T SEE THE EXACT NUMBERS)
        if action == "gather_wood":
            return world.wood < 8 and len(world.collected_trees) < len(world.trees)
        if action == "gather_stone":
            return world.stone < 4 and len(world.collected_rocks) < len(world.rocks)
        if action == "eat":
            return survival.hunger > 10 and len(world.collected_bushes) < len(world.berry_bushes)
        if action == "drink":
            return survival.thirst > 10
        return True

    def decide(self, now, player_rect, wolf_list):
        self.decision_time = now
        self.decisions += 1
        ranked = self.ranked_actions(self.state)
        for rank, (action, q) in enumerate(ranked):
            if not self.feasible(action, player_rect, wolf_list):
                continue
            if self.task and self.task["action"] == action and not self.task["failed"]:
                return          #ALREADY DOING IT
            self.task = new_task(action, now)
            self.last_reason = ("best action (MDP policy)" if rank == 0
                                else f"best possible ({rank} higher not possible now)")
            if weather.current == weather.CLEAR and self.state[6] in (mdp.RAIN, mdp.COLD):
                self.last_reason += " - HMM forecast"
            self.task["q"] = q
            return

    #------------------------------------------------------------
    # EACH FRAME
    #------------------------------------------------------------
    def update(self, player_rect, player_direction, wolf_list):
        now = game_clock.now()
        controls = Controls()
        old_state = self.state
        self.state = mdp.observe(survival, world, weather, player_rect, wolf_list)

        #DECIDE AGAIN WHEN THE TASK ENDS, EVERY FEW SECONDS, OR WHEN THE SITUATION CHANGES A LOT
        threat_changed = old_state is not None and old_state[7] != self.state[7]
        context_changed = old_state is not None and old_state[6] != self.state[6]
        if (self.task is None or self.task["done"] or self.task["failed"] or threat_changed
                or context_changed or now - self.decision_time > DECISION_INTERVAL):
            if self.task and (self.task["done"] or self.task["failed"]):
                if self.task["failed"]:
                    self.failed_until[self.task["action"]] = now + 5000
                self.task = None
            self.decide(now, player_rect, wolf_list)

        if self.task:
            if now - self.task["start"] > TASK_TIMEOUT:
                self.task["failed"] = True
            else:
                run_task(self, self.task, player_rect, player_direction, wolf_list, controls, now)
        return controls

    #------------------------------------------------------------
    # TARGET SELECTION
    #------------------------------------------------------------
    def is_excluded(self, key, now):
        return self.excluded.get(key, 0) > now

    def stand_cells(self, kind, index, target_rect):
        #FREE GRID CELLS FROM WHICH PRESSING E WOULD USE EXACTLY THIS TARGET
        cells = []
        r0, c0 = target_rect.centery // CELL, target_rect.centerx // CELL
        for r in range(r0 - 2, r0 + 3):
            for c in range(c0 - 2, c0 + 3):
                if free((r, c)) and first_interaction(cell_rect((r, c))) == (kind, index):
                    cells.append((r, c))
        return cells

    def plan_to_object(self, kind, candidates, player_rect, now, max_targets=6):
        #candidates: [(index, rect)]. PICK THE CLOSEST ONE WE CAN ACTUALLY REACH
        start = cell_of(player_rect)
        options = sorted(candidates, key=lambda item: math.hypot(item[1].centerx - player_rect.centerx,
                                                                 item[1].centery - player_rect.centery))
        best = None
        for index, rect in options[:max_targets]:
            if self.is_excluded((kind, index), now):
                continue
            for goal in sorted(self.stand_cells(kind, index, rect),
                               key=lambda cl: math.hypot(cell_center(cl)[0] - player_rect.centerx,
                                                         cell_center(cl)[1] - player_rect.centery))[:2]:
                path = search.a_star(world.get_cost_grid(), start, goal)
                if path and (best is None or len(path) < len(best[1])):
                    best = ((kind, index), path)
            if best and len(best[1]) < 6:
                break
        return best

    def water_targets(self):
        if self.water_cells is None:
            grid = world.get_cost_grid()
            self.water_cells = [(r, c) for r in range(len(grid)) for c in range(len(grid[0]))
                                if grid[r][c] is not None and world.near_water(cell_rect((r, c)))]
        return self.water_cells


#----------------------------------------------------------------
# TASKS (ONE PER MACRO-ACTION)
#----------------------------------------------------------------
def new_task(action, now):
    return {"action": action, "start": now, "phase": "plan", "path": [], "target": None,
            "done": False, "failed": False, "attempts": 0, "last_pos": None, "still": 0,
            "wait_until": 0, "presses": 0, "q": 0.0}


def follow_path(task, player_rect, controls):
    #WALK TOWARDS THE NEXT CELL ON THE PATH. RETURNS TRUE WHEN THE PATH IS FINISHED
    while task["path"]:
        tx, ty = cell_center(task["path"][0])
        dx, dy = tx - player_rect.centerx, ty - player_rect.centery
        if abs(dx) <= 3 and abs(dy) <= 3:
            task["path"].pop(0)
            continue
        controls.dx = max(-PLAYER_SPEED, min(PLAYER_SPEED, dx))
        controls.dy = max(-PLAYER_SPEED, min(PLAYER_SPEED, dy))
        return False
    return True


def steer_to(point, player_rect, controls, tolerance=3):
    dx, dy = point[0] - player_rect.centerx, point[1] - player_rect.centery
    if abs(dx) <= tolerance and abs(dy) <= tolerance:
        return True
    controls.dx = max(-PLAYER_SPEED, min(PLAYER_SPEED, dx))
    controls.dy = max(-PLAYER_SPEED, min(PLAYER_SPEED, dy))
    return False


def check_stuck(agent, task, player_rect, now):
    pos = player_rect.topleft
    if task["last_pos"] == pos:
        task["still"] += 1
    else:
        task["still"] = 0
    task["last_pos"] = pos
    if task["still"] > STUCK_FRAMES:
        task["still"] = 0
        task["attempts"] += 1
        if task["target"] is not None:
            agent.excluded[task["target"]] = now + 20000
        task["phase"] = "plan"
        if task["attempts"] > 3:
            task["failed"] = True


def run_task(agent, task, player_rect, player_direction, wolf_list, controls, now):
    action = task["action"]
    if action in ("gather_wood", "gather_stone", "eat", "drink"):
        gather_task(agent, task, player_rect, controls, now)
    elif action in ("build_fire", "build_tent"):
        build_task(agent, task, player_rect, controls, now)
    elif action == "rest":
        rest_task(agent, task, player_rect, controls, now)
    elif action == "fight":
        fight_task(agent, task, player_rect, player_direction, wolf_list, controls, now)
    elif action == "flee":
        flee_task(agent, task, player_rect, wolf_list, controls, now)


def gather_task(agent, task, player_rect, controls, now):
    action = task["action"]
    if task["phase"] == "plan":
        if action == "gather_wood":
            candidates = [(i, t) for i, t in enumerate(world.trees) if i not in world.collected_trees]
            plan = agent.plan_to_object("tree", candidates, player_rect, now)
        elif action == "gather_stone":
            candidates = [(i, r) for i, r in enumerate(world.rocks) if i not in world.collected_rocks]
            plan = agent.plan_to_object("rock", candidates, player_rect, now)
        elif action == "eat":
            candidates = [(i, b) for i, b in enumerate(world.berry_bushes) if i not in world.collected_bushes]
            plan = agent.plan_to_object("bush", candidates, player_rect, now)
        else:
            start = cell_of(player_rect)
            cells = sorted(agent.water_targets(),
                           key=lambda cl: math.hypot(cell_center(cl)[0] - player_rect.centerx,
                                                     cell_center(cl)[1] - player_rect.centery))
            plan = None
            tried = 0
            for cl in cells:
                if agent.is_excluded(("water", cl), now) or first_interaction(cell_rect(cl))[0] != "water":
                    continue
                path = search.a_star(world.get_cost_grid(), start, cl)
                tried += 1
                if path and (plan is None or len(path) < len(plan[1])):
                    plan = (("water", cl), path)
                if (plan and tried >= 4) or tried >= 12:
                    break
        if plan is None:
            task["failed"] = True
            return
        task["target"], task["path"] = plan
        task["phase"] = "travel"
        task["before"] = (world.wood, world.stone, survival.hunger, survival.thirst)

    if task["phase"] == "travel":
        check_stuck(agent, task, player_rect, now)
        if follow_path(task, player_rect, controls):
            task["phase"] = "act"

    if task["phase"] == "act":
        if now < task["wait_until"]:
            return
        wood, stone, hunger, thirst = task["before"]
        finished = (
            (action == "gather_wood" and world.wood > wood) or
            (action == "gather_stone" and world.stone > stone) or
            (action == "eat" and (survival.hunger <= 15 or task["presses"] >= 3)) or
            (action == "drink" and (survival.thirst <= 10 or task["presses"] >= 3))
        )
        if finished:
            task["done"] = True
        elif task["presses"] >= 4:
            agent.excluded[task["target"]] = now + 20000
            task["failed"] = True
        else:
            controls.actions.append("interact")
            task["presses"] += 1
            task["wait_until"] = now + 350


def build_task(agent, task, player_rect, controls, now):
    building_fire = task["action"] == "build_fire"
    count = len(world.campfires) if building_fire else len(world.tents)
    if task["phase"] == "plan":
        task["count_before"] = count
        task["phase"] = "act"
    if task["phase"] == "act":
        if count > task["count_before"]:
            task["done"] = True
            return
        if now < task["wait_until"]:
            return
        if task["presses"] >= 1:
            #NOT ENOUGH SPACE HERE: WALK A FEW CELLS AWAY AND TRY AGAIN
            task["attempts"] += 1
            if task["attempts"] > 4:
                task["failed"] = True
                return
            start = cell_of(player_rect)
            options = [(start[0] + dr, start[1] + dc) for dr in range(-3, 4) for dc in range(-3, 4)
                       if (dr or dc) and free((start[0] + dr, start[1] + dc))
                       and free((start[0] + dr + 1, start[1] + dc))]
            random.shuffle(options)
            for goal in options[:5]:
                path = search.a_star(world.get_cost_grid(), start, goal)
                if path:
                    task["path"] = path
                    task["phase"] = "move"
                    break
            task["presses"] = 0
            return
        controls.actions.append("campfire" if building_fire else "tent")
        task["presses"] += 1
        task["wait_until"] = now + 300
    if task["phase"] == "move":
        check_stuck(agent, task, player_rect, now)
        if follow_path(task, player_rect, controls):
            task["phase"] = "act"


def rest_task(agent, task, player_rect, controls, now):
    px, py = player_rect.center
    if task["phase"] == "plan":
        tents = sorted(world.tents, key=lambda t: math.hypot(t.centerx - px, t.centery - py))
        lit = [(i, f) for i, f in enumerate(world.campfires) if world.campfire_lit[i]]
        if tents and math.hypot(tents[0].centerx - px, tents[0].centery - py) < 450:
            tent = tents[0]
            task["tent"] = tent
            goal = min(((r, c) for r in range(tent.centery // CELL - 2, tent.centery // CELL + 3)
                        for c in range(tent.centerx // CELL - 2, tent.centerx // CELL + 3) if free((r, c))),
                       key=lambda cl: math.hypot(cell_center(cl)[0] - tent.centerx, cell_center(cl)[1] - tent.centery),
                       default=None)
            path = search.a_star(world.get_cost_grid(), cell_of(player_rect), goal) if goal else None
            task["path"] = path or []
            task["phase"] = "travel"
        elif lit:
            plan = agent.plan_to_object("campfire", lit, player_rect, now)
            if plan is None:
                task["failed"] = True
                return
            task["target"], task["path"] = plan
            task["tent"] = None
            task["phase"] = "travel"
        else:
            task["failed"] = True
            return

    if task["phase"] == "travel":
        check_stuck(agent, task, player_rect, now)
        if follow_path(task, player_rect, controls):
            task["phase"] = "settle"

    if task["phase"] == "settle":
        tent = task.get("tent")
        if tent is not None:
            #STEP INSIDE THE TENT (IT IS NOT AN OBSTACLE)
            if tent.collidepoint(player_rect.center) or steer_to(tent.center, player_rect, controls, 6):
                task["phase"] = "rest"
        else:
            controls.actions.append("interact")       #REST BY THE FIRE: +30 ENERGY
            task["phase"] = "rest"

    if task["phase"] == "rest":
        #STAY PUT; THE AGENT DECIDES AGAIN EVERY FEW SECONDS WHETHER TO KEEP RESTING
        if survival.energy >= 95 and survival.health >= 95 and weather.current == weather.CLEAR \
                and weather.night_amount < 0.5 and mdp.forecast_context(weather) is None:
            task["done"] = True


def fight_task(agent, task, player_rect, player_direction, wolf_list, controls, now):
    wolf_data, distance = nearest_wolf(player_rect, wolf_list)
    if wolf_data is None or distance > 320:
        task["done"] = True
        return
    wolf = wolf_data["rect"]
    dx, dy = wolf.centerx - player_rect.centerx, wolf.centery - player_rect.centery
    wanted = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")

    if distance > 70:
        #GET CLOSER (A* IF FAR, OTHERWISE STRAIGHT AT IT)
        if distance > 160:
            if not task["path"] or now - task.get("planned", 0) > 800:
                task["path"] = search.a_star(world.get_cost_grid(), cell_of(player_rect), cell_of(wolf)) or []
                task["planned"] = now
            follow_path(task, player_rect, controls)
        else:
            steer_to(wolf.center, player_rect, controls)
        return

    #CLOSE: FACE THE WOLF, THEN SWING WHEN IT IS INSIDE THE ATTACK AREA
    if player_direction != wanted:
        controls.dx = (2 if dx > 0 else -2) if wanted in ("left", "right") else 0
        controls.dy = (2 if dy > 0 else -2) if wanted in ("up", "down") else 0
        return
    if wolves_module.attack_area(player_rect, player_direction).colliderect(wolf):
        controls.actions.append("attack")
    else:
        steer_to(wolf.center, player_rect, controls)


def flee_task(agent, task, player_rect, wolf_list, controls, now):
    wolf_data, distance = nearest_wolf(player_rect, wolf_list)
    if wolf_data is None or distance > 360:
        task["done"] = True
        return
    if task["phase"] == "plan" or not task["path"]:
        #PICK A REACHABLE SPOT FAR FROM THE WOLF
        start = cell_of(player_rect)
        wolf = wolf_data["rect"]
        options = []
        for _ in range(40):
            r = start[0] + random.randint(-9, 9)
            c = start[1] + random.randint(-9, 9)
            if free((r, c)):
                wx, wy = cell_center((r, c))
                score = math.hypot(wx - wolf.centerx, wy - wolf.centery) - 0.4 * math.hypot(wx - player_rect.centerx, wy - player_rect.centery)
                options.append((score, (r, c)))
        options.sort(reverse=True)
        task["path"] = []
        for _, goal in options[:4]:
            path = search.a_star(world.get_cost_grid(), start, goal)
            if path:
                task["path"] = path
                break
        task["phase"] = "travel"
        if not task["path"]:
            task["failed"] = True
            return
    check_stuck(agent, task, player_rect, now)
    follow_path(task, player_rect, controls)


#----------------------------------------------------------------
# DRAWING: THE AI'S PATH AND A PANEL EXPLAINING ITS DECISION
#----------------------------------------------------------------
_fonts = {}


def draw_overlay(screen, agent, camera, player_rect):
    if not _fonts:
        _fonts["bold"] = pygame.font.SysFont("Arial", 15, bold=True)
        _fonts["small"] = pygame.font.SysFont("Arial", 13)
    task = agent.task

    #PLANNED PATH AS A LINE OF DOTS
    if task and task["path"]:
        for r, c in task["path"]:
            x, y = c * CELL + 20 - camera.x, r * CELL + 20 - camera.y
            pygame.draw.circle(screen, (255, 230, 120), (x, y), 3)
        r, c = task["path"][-1]
        pygame.draw.circle(screen, (255, 230, 120), (c * CELL + 20 - camera.x, r * CELL + 20 - camera.y), 9, 2)

    #PANEL
    panel = pygame.Rect(10, 200, 262, 176)
    surface = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(surface, (18, 22, 28, 190), surface.get_rect(), border_radius=10)
    pygame.draw.rect(surface, (250, 204, 96, 140), surface.get_rect(), width=1, border_radius=10)
    screen.blit(surface, panel.topleft)

    x, y = panel.x + 10, panel.y + 8
    tag = _fonts["bold"].render("AI MODE", True, (40, 30, 20))
    tag_rect = pygame.Rect(x, y, tag.get_width() + 12, 20)
    pygame.draw.rect(screen, (250, 204, 96), tag_rect, border_radius=5)
    screen.blit(tag, (x + 6, y + 1))
    speed = getattr(agent, "sim_speed", 1)
    screen.blit(_fonts["small"].render(f"Speed x{speed} (keys 1-4)", True, (190, 195, 200)),
                (tag_rect.right + 8, y + 3))

    y += 28
    doing = ACTION_LABELS.get(task["action"], "-") if task else "Thinking..."
    screen.blit(_fonts["bold"].render(f"Doing: {doing}", True, (240, 240, 235)), (x, y))
    y += 19
    screen.blit(_fonts["small"].render(f"Why: {agent.last_reason}", True, (190, 195, 200)), (x, y))

    if agent.state is not None:
        s = agent.state
        y += 22
        line1 = f"health {mdp.HEALTH_LEVELS[s[0]]}, food {mdp.FOOD_LEVELS[s[1]]}, water {mdp.WATER_LEVELS[s[2]]}"
        line2 = f"energy {mdp.ENERGY_LEVELS[s[3]]}, wood {mdp.WOOD_LEVELS[s[4]]}, stone {mdp.STONE_LEVELS[s[5]]}"
        context = mdp.CONTEXTS[s[6]]
        if weather.current == weather.CLEAR and s[6] in (mdp.RAIN, mdp.COLD):
            context += " soon"      #THE HMM FORECAST, NOT THE WEATHER YET
        line3 = (f"{context}, wolf: {'yes' if s[7] else 'no'}, "
                 f"shelter: {mdp.SHELTER_LEVELS[s[8]]}")
        for line in (line1, line2, line3):
            screen.blit(_fonts["small"].render(line, True, (170, 210, 255)), (x, y))
            y += 16

        #TOP 3 ACTIONS BY Q-VALUE
        y += 4
        ranked = [(act, q) for act, q in agent.ranked_actions(s)
                  if agent.feasible(act, player_rect, [])][:3]
        best_q = ranked[0][1] if ranked else 0
        for action, q in ranked:
            label = ACTION_LABELS[action]
            screen.blit(_fonts["small"].render(f"{label}", True, (240, 240, 235)), (x, y))
            screen.blit(_fonts["small"].render(f"Q = {q:.1f}", True, (250, 204, 96) if q == best_q else (190, 195, 200)),
                        (panel.right - 72, y))
            y += 15
