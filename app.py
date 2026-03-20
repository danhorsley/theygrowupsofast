# They Grow Up So Fast – minimal Pygame prototype
# One replicator, three rules, clear the obstacle with as few children as possible
# 2025/2026 style – clarity first, no magic

import pygame
import sys
import time
from collections import deque

# ────────────────────────────────────────────────
#   CONFIG / CONSTANTS
# ────────────────────────────────────────────────

WIDTH, HEIGHT = 640, 480
GRID_W, GRID_H = 40, 30               # logical cells
CELL_SIZE = min(WIDTH // GRID_W, HEIGHT // GRID_H)

FPS = 30
SIM_STEPS_PER_FRAME = 1               # how aggressive the sim is per draw

BLACK   = (0, 0, 0)
GRAY    = (40, 40, 40)
WHITE   = (220, 220, 220)
RED     = (220, 60, 60)
GREEN   = (60, 220, 60)
BLUE    = (60, 60, 220)
YELLOW  = (220, 220, 60)

FONT_SIZE = 16

# ────────────────────────────────────────────────
#   RULE DEFINITIONS
#   Each rule is just a string name + a function that gets called on every agent
# ────────────────────────────────────────────────

def rule_replicate_toward_obstacle_if_empty(agent, grid, new_agents):
    x, y = agent
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < GRID_W and 0 <= ny < GRID_H): continue
        if grid[ny][nx] == '.':                                 # empty
            # look a bit further – is obstacle in that direction?
            for k in range(1, 5):
                mx, my = x + dx*k, y + dy*k
                if not (0 <= mx < GRID_W and 0 <= my < GRID_H): break
                if grid[my][mx] == '#':
                    new_agents.append((nx, ny))
                    return True
    return False

def rule_consume_obstacle_if_adjacent(agent, grid, _):
    x, y = agent
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx] == '#':
            grid[ny][nx] = '.'
            return True
    return False

def rule_die_if_isolated(agent, grid, _):
    x, y = agent
    neighbors = 0
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx] == '@':
            neighbors += 1
    if neighbors == 0:
        grid[y][x] = '.'
        return True  # died
    return False

def rule_always_replicate_random_empty(agent, grid, new_agents):
    x, y = agent
    dirs = [(-1,0),(1,0),(0,-1),(0,1)]
    random.shuffle(dirs)  # for visual variety
    for dx, dy in dirs:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_W and 0 <= ny < GRID_H and grid[ny][nx] == '.':
            new_agents.append((nx, ny))
            return True
    return False

def rule_die_after_age(agent, grid, _):
    # we'll add simple age tracking later if needed
    return False

# Map from display name → actual function
RULE_FUNCTIONS = {
    "Replicate toward obstacle (if empty ahead)" : rule_replicate_toward_obstacle_if_empty,
    "Consume obstacle if adjacent"               : rule_consume_obstacle_if_adjacent,
    "Die if isolated (no neighbors)"             : rule_die_if_isolated,
    "Always replicate to random empty neighbor"  : rule_always_replicate_random_empty,
    # Add more here – keep names short & clear
    # "Die after 8 generations",
    # "Replicate only if < 3 neighbors",
    # "Avoid crowding (die if 4+ neighbors)",
}

RULE_NAMES = list(RULE_FUNCTIONS.keys())

# ────────────────────────────────────────────────
#   GAME STATE
# ────────────────────────────────────────────────

def reset_world():
    grid = [['.' for _ in range(GRID_W)] for _ in range(GRID_H)]

    # obstacle – simple wall with a gap to make it solvable
    for x in range(GRID_W//4, GRID_W - GRID_W//4):
        grid[GRID_H//2][x] = '#'

    # starting agent (child)
    start_x = GRID_W // 2
    start_y = GRID_H // 4
    grid[start_y][start_x] = '@'

    agents = deque([(start_x, start_y)])
    return grid, agents

grid, agents = reset_world()

selected_rules = [0, 1, 2]   # indices into RULE_NAMES – start with 3 safe-ish choices

running = True
sim_paused = True
step_count = 0
max_population = 1
total_spawned = 1

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("They Grow Up So Fast – prototype")
font = pygame.font.SysFont("consolas", FONT_SIZE)
clock = pygame.time.Clock()

def count_obstacle_cells():
    return sum(row.count('#') for row in grid)

initial_obstacles = count_obstacle_cells()

# ────────────────────────────────────────────────
#   UI HELPERS
# ────────────────────────────────────────────────

def draw_text(s, x, y, color=WHITE):
    img = font.render(s, True, color)
    screen.blit(img, (x, y))

def draw_button(text, x, y, w, h, hovered):
    color = (70,70,80) if not hovered else (100,100,120)
    pygame.draw.rect(screen, color, (x,y,w,h))
    pygame.draw.rect(screen, WHITE, (x,y,w,h), 1)
    draw_text(text, x+8, y+4)

# ────────────────────────────────────────────────
#   MAIN LOOP
# ────────────────────────────────────────────────

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                sim_paused = not sim_paused
            elif event.key == pygame.K_r:
                grid, agents = reset_world()
                step_count = 0
                max_population = 1
                total_spawned = 1
                sim_paused = True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = pygame.mouse.get_pos()
            # rule buttons – bottom area
            if my > HEIGHT - 140:
                slot_w = WIDTH // len(RULE_NAMES)
                for i, name in enumerate(RULE_NAMES):
                    bx = i * slot_w + 4
                    by = HEIGHT - 130
                    if bx <= mx < bx + slot_w - 8 and by <= my < by + 30:
                        # cycle through selection for this slot
                        for slot in range(3):
                            if selected_rules[slot] == i:
                                selected_rules[slot] = (selected_rules[slot] + 1) % len(RULE_NAMES)
                                break
                        else:
                            # no one had it → assign to first empty-looking slot
                            for slot in range(3):
                                if selected_rules[slot] == selected_rules[slot]:  # silly always-true
                                    selected_rules[slot] = i
                                    break

    # ─── Simulation step ──────────────────────────────────────
    if not sim_paused:
        for _ in range(SIM_STEPS_PER_FRAME):
            step_count += 1
            new_agents = []

            # Process every agent (copy because we mutate)
            current_agents = list(agents)
            for ax, ay in current_agents:
                if grid[ay][ax] != '@': continue  # already died

                died = False
                for idx in selected_rules:
                    rule_name = RULE_NAMES[idx]
                    func = RULE_FUNCTIONS[rule_name]
                    if func((ax, ay), grid, new_agents):
                        if "die" in rule_name.lower():
                            died = True

                if died:
                    grid[ay][ax] = '.'
                    agents.remove((ax, ay))

            # Births
            for nx, ny in new_agents:
                if grid[ny][nx] == '.':
                    grid[ny][nx] = '@'
                    agents.append((nx, ny))
                    total_spawned += 1
                    max_population = max(max_population, len(agents))

    # ─── Drawing ──────────────────────────────────────────────
    screen.fill(BLACK)

    # Grid
    for y in range(GRID_H):
        for x in range(GRID_W):
            r = pygame.Rect(x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            cell = grid[y][x]
            if cell == '#':
                pygame.draw.rect(screen, RED, r)
            elif cell == '@':
                age_color = min(255, 80 + step_count * 2 % 176)  # pulse a bit
                pygame.draw.circle(screen, (age_color, 180, 100), r.center, CELL_SIZE//2 - 2)
            else:
                pygame.draw.rect(screen, GRAY, r, 1)

    # UI overlay
    draw_text(f"Step: {step_count:4d}   Agents: {len(agents):3d} / max {max_population:3d}   Spawned: {total_spawned}", 10, 8)
    draw_text(f"Obstacles left: {count_obstacle_cells()}/{initial_obstacles}", 10, 26)

    status = "PAUSED – SPACE to run" if sim_paused else "Running – SPACE to pause"
    if len(agents) == 0 and count_obstacle_cells() > 0:
        status = "All children died – R to restart"
    elif count_obstacle_cells() == 0:
        status = "PATH CLEARED!   R to try again"
    draw_text(status, 10, HEIGHT - 60, GREEN if "CLEARED" in status else YELLOW)

    # Rule selectors (very crude dropdown style)
    draw_text("Selected rules (click to cycle):", 10, HEIGHT - 110)
    slot_w = WIDTH // 3
    for i in range(3):
        idx = selected_rules[i]
        name = RULE_NAMES[idx]
        hovered = False  # could add mouse check but skipping for now
        draw_button(name, 10 + i*slot_w, HEIGHT - 80, slot_w-20, 36, hovered)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()