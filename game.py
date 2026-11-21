import pygame
import random

CELL = 8
COLS = 100
ROWS = 75
BRUSH = 2  # how many cells out from the mouse to paint

EMPTY = 0
SAND = 1
WATER = 2
STONE = 3

colors = {
    EMPTY: (30, 30, 60),
    SAND: (220, 190, 100),
    WATER: (50, 120, 230),
    STONE: (120, 120, 120),
}
names = {SAND: "sand", WATER: "water", STONE: "stone"}

# grid[row][col] holds what is in each cell
grid = [[EMPTY] * COLS for _ in range(ROWS)]
moved = set()  # cells that already moved this frame


def in_bounds(col, row):
    return 0 <= col < COLS and 0 <= row < ROWS


def try_move(col, row, new_col, new_row, can_swap_with):
    # Swap this cell with the target if the target is something we can move into
    if in_bounds(new_col, new_row) and grid[new_row][new_col] in can_swap_with:
        grid[row][col], grid[new_row][new_col] = grid[new_row][new_col], grid[row][col]
        moved.add((new_col, new_row))
        return True
    return False


def update_sand(col, row):
    # Sand falls through empty space and sinks through water
    side = random.choice([-1, 1])
    falls_into = (EMPTY, WATER)
    if try_move(col, row, col, row + 1, falls_into):
        return
    if try_move(col, row, col + side, row + 1, falls_into):
        return
    try_move(col, row, col - side, row + 1, falls_into)


def update_water(col, row):
    # Water falls like sand, but if it can't fall it spreads sideways
    side = random.choice([-1, 1])
    if try_move(col, row, col, row + 1, (EMPTY,)):
        return
    if try_move(col, row, col + side, row + 1, (EMPTY,)):
        return
    if try_move(col, row, col - side, row + 1, (EMPTY,)):
        return
    if try_move(col, row, col + side, row, (EMPTY,)):
        return
    try_move(col, row, col - side, row, (EMPTY,))


def update_world():
    moved.clear()
    # Go bottom to top so a falling cell doesn't get moved twice in one frame
    for row in range(ROWS - 1, -1, -1):
        for col in range(COLS):
            if (col, row) in moved:
                continue
            cell = grid[row][col]
            if cell == SAND:
                update_sand(col, row)
            elif cell == WATER:
                update_water(col, row)


def paint(mx, my, material):
    center_col = mx // CELL
    center_row = my // CELL
    for row in range(center_row - BRUSH, center_row + BRUSH + 1):
        for col in range(center_col - BRUSH, center_col + BRUSH + 1):
            if in_bounds(col, row):
                grid[row][col] = material


def draw_world():
    for row in range(ROWS):
        for col in range(COLS):
            cell = grid[row][col]
            if cell != EMPTY:
                pygame.draw.rect(screen, colors[cell], (col * CELL, row * CELL, CELL, CELL))


pygame.init()
screen = pygame.display.set_mode((COLS * CELL, ROWS * CELL))
pygame.display.set_caption("Sand Game")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 28)

material = SAND
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                material = SAND
            if event.key == pygame.K_2:
                material = WATER
            if event.key == pygame.K_3:
                material = STONE
            if event.key == pygame.K_c:
                grid = [[EMPTY] * COLS for _ in range(ROWS)]

    # Holding the mouse keeps painting, so use get_pressed instead of events
    buttons = pygame.mouse.get_pressed()
    mx, my = pygame.mouse.get_pos()
    if buttons[0]:
        paint(mx, my, material)
    if buttons[2]:
        paint(mx, my, EMPTY)

    update_world()

    screen.fill(colors[EMPTY])
    draw_world()
    text = font.render(f"1 sand  2 water  3 stone  right-click erase  C clear   |   {names[material]}", True, (255, 255, 255))
    screen.blit(text, (10, 10))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
