import pygame

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