import pygame
import heapq
from collections import deque

def bfs(grid, start, goal):
    queue = deque([[start]])
    visited = {start}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == goal:
            return path

        row, col = current

        neighbors = [
            (row - 1, col), #Up
            (row + 1, col), #Down
            (row, col - 1), #Left
            (row, col + 1) #Right
        ]

        for next_cell in neighbors:
             r, c = next_cell

             if (
                 0 <= r < len(grid)
                 and 0 <= c < len(grid[0])
                 and grid[r][c] == 0
                 and next_cell not in visited
             ):
                 visited.add(next_cell)
                 queue.append(path + [next_cell])
    return None

def create_grid(width, height, cell_size, obstacles):
    rows = height // cell_size
    cols = width // cell_size

    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    for obstacle in obstacles:
        for row in range(rows):
            for col in range(cols):
                cell_rect = pygame.Rect(
                    col * cell_size,
                    row * cell_size,
                    cell_size,
                    cell_size
                )

                if cell_rect.colliderect(obstacle):
                    grid[row][col] = 1
    return grid


def a_star(grid, start, goal):
    #A* SEARCH ON A COST GRID
    #grid[row][col] IS THE COST OF ENTERING THAT CELL, OR None IF IT IS BLOCKED
    rows = len(grid)
    cols = len(grid[0])

    def heuristic(cell):
        #MANHATTAN DISTANCE: NEVER OVERESTIMATES, BECAUSE EVERY STEP COSTS AT LEAST 1
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_list = [(heuristic(start), 0, start)]
    came_from = {start: None}
    cost_so_far = {start: 0}

    while open_list:
        _, current_cost, current = heapq.heappop(open_list)

        if current == goal:
            #REBUILD THE PATH BY WALKING BACKWARDS FROM THE GOAL
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            return path[::-1]

        #SKIP OUTDATED ENTRIES IN THE PRIORITY QUEUE
        if current_cost > cost_so_far[current]:
            continue

        row, col = current
        neighbors = [
            (row - 1, col), #Up
            (row + 1, col), #Down
            (row, col - 1), #Left
            (row, col + 1) #Right
        ]

        for next_cell in neighbors:
            r, c = next_cell
            if not (0 <= r < rows and 0 <= c < cols):
                continue

            step_cost = grid[r][c]
            if step_cost is None:
                #THE GOAL MAY TOUCH AN OBSTACLE (PLAYER STANDING NEXT TO A TREE)
                if next_cell != goal:
                    continue
                step_cost = 1

            new_cost = current_cost + step_cost
            if new_cost < cost_so_far.get(next_cell, float("inf")):
                cost_so_far[next_cell] = new_cost
                came_from[next_cell] = current
                heapq.heappush(open_list, (new_cost + heuristic(next_cell), new_cost, next_cell))

    return None


def create_cost_grid(width, height, cell_size, obstacles, cost_function):
    #None = BLOCKED CELL, OTHERWISE THE COST OF WALKING THROUGH THE CELL
    rows = height // cell_size
    cols = width // cell_size
    grid = []

    for row in range(rows):
        grid_row = []
        for col in range(cols):
            cell_rect = pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)

            if cell_rect.collidelist(obstacles) != -1:
                grid_row.append(None)
            else:
                grid_row.append(cost_function(cell_rect.centerx, cell_rect.centery))
        grid.append(grid_row)

    return grid


if __name__ == "__main__":
    #QUICK TESTS (ONLY RUN WHEN YOU RUN search.py DIRECTLY)
    test_grid = [
        [0, 0, 0, 1, 0],
        [0, 1, 0, 1, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 1, 0]
    ]

    start = (0, 0)
    goal = (3, 4)

    path = bfs(test_grid, start, goal)

    print("Found path:", path)

    test_obstacles = [
        pygame.Rect(100, 100, 40, 50),
        pygame.Rect(250, 180, 40, 50)
    ]

    game_grid = create_grid(800, 600, 40, test_obstacles)

    for row in game_grid:
        print(row)
    cost_test = [
        [1, 1, 1, 1, 1],
        [1, None, 4, None, 1],
        [1, None, 4, 1, 1],
        [1, 1, 1, None, 1]
    ]
    print("A* path:", a_star(cost_test, (0, 0), (3, 4)))
