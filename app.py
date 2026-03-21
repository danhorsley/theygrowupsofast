# They Grow Up So Fast — prototype with fixed-outcome squares
# Agent walks a colored path. Each cell consumed on contact.
# ASSIGNABLE colors (Red, Yellow, Blue): player picks a verb.
# FIXED colors (Green, Purple, Orange, Cyan): always do one thing.
# Goal: consume all cells AND end with zero agents.

import pygame
import sys

# ── layout ──

CELL     = 20
GRID_W   = 38
GRID_H   = 26
GRID_PX_W = GRID_W * CELL
GRID_PX_H = GRID_H * CELL
PANEL_W  = 280
WIN_W    = GRID_PX_W + PANEL_W
WIN_H    = max(GRID_PX_H, 580)

# ── cell types ──

EMPTY       = 0
WALL_RED    = 1
WALL_YELLOW = 2
WALL_BLUE   = 3
AGENT       = 4

# fixed-outcome cells — verb is baked in, player can't change it
FIXED_REPLICATE  = 5   # green
FIXED_DISSOLVE   = 6   # purple
FIXED_TURN_RIGHT = 7   # orange
FIXED_TURN_LEFT  = 8   # cyan
FIXED_PASS       = 9   # grey

ASSIGNABLE_TYPES = (WALL_RED, WALL_YELLOW, WALL_BLUE)
FIXED_TYPES = (FIXED_REPLICATE, FIXED_DISSOLVE, FIXED_TURN_RIGHT, FIXED_TURN_LEFT, FIXED_PASS)
ALL_WALL_TYPES = ASSIGNABLE_TYPES + FIXED_TYPES

COLOR_NAMES = {
    WALL_RED: "Red", WALL_YELLOW: "Yellow", WALL_BLUE: "Blue",
    FIXED_REPLICATE: "Green", FIXED_DISSOLVE: "Purple",
    FIXED_TURN_RIGHT: "Orange", FIXED_TURN_LEFT: "Cyan",
    FIXED_PASS: "Grey",
}

# ── verbs ──

VERB_PASS       = 0
VERB_REPLICATE  = 1
VERB_DISSOLVE   = 2
VERB_TURN_LEFT  = 3
VERB_TURN_RIGHT = 4
VERB_COUNT      = 5

VERB_NAMES = {
    VERB_PASS:       "Pass",
    VERB_REPLICATE:  "Replicate",
    VERB_DISSOLVE:   "Dissolve",
    VERB_TURN_LEFT:  "Turn Left",
    VERB_TURN_RIGHT: "Turn Right",
}

# fixed cells always map to this verb
FIXED_VERB = {
    FIXED_PASS:       VERB_PASS,
    FIXED_REPLICATE:  VERB_REPLICATE,
    FIXED_DISSOLVE:   VERB_DISSOLVE,
    FIXED_TURN_LEFT:  VERB_TURN_LEFT,
    FIXED_TURN_RIGHT: VERB_TURN_RIGHT,
}

# short names for legend
FIXED_LABEL = {
    FIXED_REPLICATE:  "Replicate",
    FIXED_DISSOLVE:   "Dissolve",
    FIXED_TURN_RIGHT: "Turn Right",
    FIXED_TURN_LEFT:  "Turn Left",
    FIXED_PASS:       "Pass",
}

# ── tuning ──

MAX_POP     = 100
MAX_STEPS   = 300
SIM_TICK_MS = 200
FPS         = 30

# ── palette ──

BG            = (18, 18, 24)
PANEL_BG      = (24, 24, 32)
TEXT_COLOR     = (195, 195, 205)
TEXT_DIM       = (100, 100, 115)
STATUS_GREEN   = (80, 220, 120)
STATUS_YELLOW  = (220, 210, 70)
STATUS_RED     = (220, 70, 70)
AGENT_COLOR    = (70, 210, 120)
AGENT_DOT      = (200, 255, 200)

WCOLOR = {
    WALL_RED:        (200, 60, 60),
    WALL_YELLOW:     (210, 195, 50),
    WALL_BLUE:       (55, 100, 200),
    FIXED_REPLICATE: (50, 180, 80),
    FIXED_DISSOLVE:  (150, 60, 190),
    FIXED_TURN_RIGHT:(220, 130, 40),
    FIXED_TURN_LEFT: (50, 180, 200),
    FIXED_PASS:      (90, 90, 100),
}

VERB_COLOR = {
    VERB_PASS:       (120, 120, 130),
    VERB_REPLICATE:  (80, 220, 120),
    VERB_DISSOLVE:   (220, 160, 50),
    VERB_TURN_LEFT:  (70, 180, 220),
    VERB_TURN_RIGHT: (180, 100, 220),
}

# ── direction ──

RIGHT = (1, 0)
DOWN  = (0, 1)
LEFT  = (-1, 0)
UP    = (0, -1)

def turn_left(dx, dy):
    return (dy, -dx)

def turn_right(dx, dy):
    return (-dy, dx)

# ── level shorthand ──

R, Y, B = WALL_RED, WALL_YELLOW, WALL_BLUE
G, P = FIXED_REPLICATE, FIXED_DISSOLVE
O, C = FIXED_TURN_RIGHT, FIXED_TURN_LEFT
W = FIXED_PASS

def tape_level(colors):
    """1D horizontal tape. Agent starts one cell left, facing right."""
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "start": (-1, 0),
        "dir": RIGHT,
    }


# ── levels ──

LEVELS = [
    # ── Phase 1: pure assignable, learn basics ──

    tape_level([R, Y, B]),         # 1: RYB (2 solutions, tutorial)
    tape_level([R, Y, B, B]),      # 2: RYBB (2 solutions)
    tape_level([R, Y, B, Y]),      # 3: RYBY (1 sol: R=Rep Y=Dissolve B=Pass)

    # ── Phase 2: introduce fixed squares ──

    # 4: green replicates! figure out R. (R=Dissolve)
    tape_level([G, R, R]),

    # 5: green replicates, purple dissolves. figure out R. (R=Pass)
    tape_level([R, G, R, P, P]),

    # 6: mixed fixed + assignable. (R=Pass, Y=Dissolve)
    tape_level([R, G, Y, P]),

    # ── Phase 3: harder assignable ──

    tape_level([R, R, Y, B, Y]),       # 7: RRYBY
    tape_level([R, Y, Y, B, B]),       # 8: RYYBB
    tape_level([R, Y, B, R, B]),       # 9: RYBRB
    tape_level([R, R, Y, B, B, B]),    # 10: RRYBBB

    # ── Phase 4: 2D shapes with turns ──

    # 11: L-shape — R=Pass, B=TurnRight, Y=Dissolve
    {
        "cells": [(0,0,R), (1,0,R), (2,0,B),
                                     (2,1,R),
                                     (2,2,R),
                                     (2,3,Y)],
        "start": (-1, 0),
        "dir": RIGHT,
    },

    # 12: Reverse L — R=Pass, B=TurnLeft, Y=Dissolve
    {
        "cells": [                   (2,0,Y),
                                     (2,1,R),
                                     (2,2,R),
                  (0,3,R), (1,3,R), (2,3,B)],
        "start": (-1, 3),
        "dir": RIGHT,
    },

    # 13: U-shape — R=Pass, B=TurnRight, Y=Dissolve
    {
        "cells": [(0,0,R), (1,0,R), (2,0,B),
                                     (2,1,R),
                  (0,2,Y), (1,2,R), (2,2,B)],
        "start": (-1, 0),
        "dir": RIGHT,
    },

    # 14: Big U — R=Pass, B=TurnRight, Y=Dissolve
    {
        "cells": [(0,0,R), (1,0,R), (2,0,R), (3,0,B),
                                               (3,1,R),
                                               (3,2,R),
                  (0,3,Y), (1,3,R), (2,3,R), (3,3,B)],
        "start": (-1, 0),
        "dir": RIGHT,
    },
]

# ── Phase 5: fractal levels (generated) ──

from fractal import build_spiral_fractal, build_multi_fractal

LEVELS += [
    # 15: Depth-2 spiral — R=Pass, Y=Replicate, B=TurnRight (24 cells, peak 4)
    build_spiral_fractal(2, seg_len=2, seg_color=R, branch_color=Y, turn_color=B),

    # 16: Depth-3 spiral — B=Pass, R=Replicate, Y=TurnRight (52 cells, peak 8)
    build_spiral_fractal(3, seg_len=2, seg_color=B, branch_color=R, turn_color=Y),

    # 17: Depth-3 spiral bigger — Y=Pass, B=Replicate, R=TurnRight (67 cells, peak 8)
    build_spiral_fractal(3, seg_len=3, seg_color=Y, branch_color=B, turn_color=R),

    # 18: Multi-branch party — R=Pass, Y=Replicate, B=TurnRight (peak 12)
    build_multi_fractal(3, sub_depth=2, seg_len=2, trunk_seg=6,
                        seg_color=R, branch_color=Y, turn_color=B),
]

NUM_LEVELS = len(LEVELS)

# ── helpers ──

def in_bounds(x, y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H

def is_wall(cell):
    return cell in ALL_WALL_TYPES

def get_verb(cell, verbs):
    """Get the verb for a cell: fixed cells have hardcoded verbs, assignable use player's choice."""
    if cell in FIXED_VERB:
        return FIXED_VERB[cell]
    return verbs.get(cell, VERB_PASS)

def count_walls(grid):
    n = 0
    for row in grid:
        for c in row:
            if is_wall(c):
                n += 1
    return n

def fixed_types_in_level(level):
    """Which fixed cell types appear in this level?"""
    return sorted(set(c for _, _, c in level["cells"] if c in FIXED_TYPES))


# ── world setup ──

def make_grid(level):
    grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
    cells = level["cells"]

    xs = [x for x, y, c in cells]
    ys = [y for x, y, c in cells]
    sx, sy = level["start"]
    min_x = min(min(xs), sx)
    max_x = max(max(xs), sx)
    min_y = min(min(ys), sy)
    max_y = max(max(ys), sy)

    shape_w = max_x - min_x + 1
    shape_h = max_y - min_y + 1

    ox = (GRID_W - shape_w) // 2 - min_x
    oy = (GRID_H - shape_h) // 2 - min_y

    for x, y, c in cells:
        grid[y + oy][x + ox] = c

    ax, ay = sx + ox, sy + oy
    grid[ay][ax] = AGENT
    dx, dy = level["dir"]
    agent = {"x": ax, "y": ay, "dx": dx, "dy": dy, "alive": True}

    return grid, [agent]


# ── sim step ──

def sim_step(agents, grid, verbs):
    new_agents = []

    for a in agents:
        if not a["alive"]:
            continue

        x, y = a["x"], a["y"]
        dx, dy = a["dx"], a["dy"]
        nx, ny = x + dx, y + dy

        if not in_bounds(nx, ny):
            continue

        target = grid[ny][nx]

        if target == EMPTY:
            grid[y][x] = EMPTY
            a["x"], a["y"] = nx, ny
            grid[ny][nx] = AGENT

        elif is_wall(target):
            verb = get_verb(target, verbs)
            grid[ny][nx] = EMPTY  # always consumed

            if verb == VERB_PASS:
                grid[y][x] = EMPTY
                a["x"], a["y"] = nx, ny
                grid[ny][nx] = AGENT

            elif verb == VERB_REPLICATE:
                child = {"x": nx, "y": ny, "dx": dx, "dy": dy, "alive": True}
                new_agents.append(child)
                grid[ny][nx] = AGENT

            elif verb == VERB_DISSOLVE:
                a["alive"] = False
                grid[y][x] = EMPTY

            elif verb == VERB_TURN_LEFT:
                grid[y][x] = EMPTY
                a["x"], a["y"] = nx, ny
                a["dx"], a["dy"] = turn_left(dx, dy)
                grid[ny][nx] = AGENT

            elif verb == VERB_TURN_RIGHT:
                grid[y][x] = EMPTY
                a["x"], a["y"] = nx, ny
                a["dx"], a["dy"] = turn_right(dx, dy)
                grid[ny][nx] = AGENT

        elif target == AGENT:
            pass  # blocked, wait

    # add newborns
    spawned = 0
    for na in new_agents:
        if len(agents) + spawned >= MAX_POP:
            break
        agents.append(na)
        spawned += 1

    # prune dead
    alive = [a for a in agents if a["alive"]]
    return alive, spawned


# ── drawing ──

def draw_grid(screen, grid, agents):
    for y in range(GRID_H):
        for x in range(GRID_W):
            c = grid[y][x]
            if c in WCOLOR:
                rx, ry = x * CELL, y * CELL
                pygame.draw.rect(screen, WCOLOR[c], (rx+1, ry+1, CELL-2, CELL-2))
                # fixed cells get a small white inner border to show "locked"
                if c in FIXED_TYPES:
                    pygame.draw.rect(screen, (255, 255, 255), (rx+4, ry+4, CELL-8, CELL-8), 1)

    for a in agents:
        if not a["alive"]:
            continue
        rx, ry = a["x"] * CELL, a["y"] * CELL
        cx, cy = rx + CELL // 2, ry + CELL // 2
        pygame.draw.circle(screen, AGENT_COLOR, (cx, cy), CELL // 2 - 2)
        tip_x = cx + a["dx"] * (CELL // 4)
        tip_y = cy + a["dy"] * (CELL // 4)
        pygame.draw.circle(screen, AGENT_DOT, (tip_x, tip_y), 3)


def draw_shape_preview(screen, font_sm, level, px, y):
    """Draw a mini version of the level shape in the panel."""
    cells = level["cells"]
    sx, sy = level["start"]

    all_x = [x for x, _, _ in cells] + [sx]
    all_y = [y_ for _, y_, _ in cells] + [sy]
    min_x, min_y = min(all_x), min(all_y)

    pc = 12
    gap = 2

    for cx, cy, color in cells:
        rx = px + (cx - min_x) * (pc + gap)
        ry = y + (cy - min_y) * (pc + gap)
        pygame.draw.rect(screen, WCOLOR[color], (rx, ry, pc, pc))
        if color in FIXED_TYPES:
            pygame.draw.rect(screen, (255, 255, 255), (rx+2, ry+2, pc-4, pc-4), 1)

    # agent start triangle
    adx, ady = level["dir"]
    ax = px + (sx - min_x) * (pc + gap) + pc // 2
    ay = y + (sy - min_y) * (pc + gap) + pc // 2
    r = pc // 2
    tip = (ax + adx * r, ay + ady * r)
    p1 = (ax + ady * r * 0.6, ay - adx * r * 0.6)
    p2 = (ax - ady * r * 0.6, ay + adx * r * 0.6)
    pygame.draw.polygon(screen, AGENT_COLOR, [tip, p1, p2])

    max_y_cell = max(all_y)
    shape_h = (max_y_cell - min_y + 1) * (pc + gap)
    return y + shape_h + 4


def draw_panel(screen, font, font_sm, verbs, step, agents, total_spawned, peak_pop,
               walls_left, walls_start, paused, mouse_pos, level_idx):
    px = GRID_PX_W
    pygame.draw.rect(screen, PANEL_BG, (px, 0, PANEL_W, WIN_H))

    y = 10
    screen.blit(font.render("THEY GROW UP SO FAST", True, TEXT_COLOR), (px + 10, y))
    y += 24

    screen.blit(font_sm.render(f"Level {level_idx + 1} / {NUM_LEVELS}", True, TEXT_DIM), (px + 12, y))
    y += 22

    for s in [
        f"Step:   {step}",
        f"Agents: {len(agents)}  (peak {peak_pop})",
        f"Spawned: {total_spawned}",
        f"Cells:  {walls_left}/{walls_start} remaining",
    ]:
        screen.blit(font_sm.render(s, True, TEXT_DIM), (px + 12, y))
        y += 16

    # status
    y += 4
    sub_msg = None
    if walls_left == 0 and len(agents) == 0:
        msg, color = "PERFECT!", STATUS_GREEN
        sub_msg = "Press N for next level."
    elif walls_left == 0:
        msg, color = "PATH CLEARED", STATUS_GREEN
        sub_msg = f"{len(agents)} still alive. Not perfect."
    elif len(agents) == 0 and step > 0:
        msg, color = "ALL DISSOLVED", STATUS_RED
        sub_msg = "Path not cleared. Try again (R)."
    elif paused and step == 0:
        msg, color = "SET RULES, THEN SPACE", STATUS_YELLOW
    elif paused:
        msg, color = "PAUSED", STATUS_YELLOW
    elif step >= MAX_STEPS:
        msg, color = "TIME'S UP", STATUS_RED
    else:
        msg, color = "RUNNING...", STATUS_GREEN

    screen.blit(font.render(msg, True, color), (px + 12, y))
    if sub_msg:
        screen.blit(font_sm.render(sub_msg, True, color), (px + 12, y + 17))
    y += 38

    # controls
    screen.blit(font_sm.render("SPACE run/pause   R reset", True, TEXT_DIM), (px + 12, y))
    screen.blit(font_sm.render("N next   P prev   ESC quit", True, TEXT_DIM), (px + 12, y + 15))
    y += 36

    # shape preview
    level = LEVELS[level_idx % NUM_LEVELS]
    screen.blit(font_sm.render("SHAPE:", True, TEXT_COLOR), (px + 12, y))
    y += 18
    y = draw_shape_preview(screen, font_sm, level, px + 12, y)

    # fixed square legend (only if this level has fixed cells)
    fixed_in_level = fixed_types_in_level(level)
    if fixed_in_level:
        y += 4
        screen.blit(font_sm.render("FIXED (automatic):", True, TEXT_DIM), (px + 12, y))
        y += 16
        for ft in fixed_in_level:
            # swatch + label
            pygame.draw.rect(screen, WCOLOR[ft], (px + 14, y, 14, 14))
            pygame.draw.rect(screen, (255, 255, 255), (px + 16, y + 2, 10, 10), 1)
            screen.blit(font_sm.render(FIXED_LABEL[ft], True, TEXT_DIM), (px + 34, y))
            y += 17
    y += 8

    # assignable verb buttons
    screen.blit(font_sm.render("RULES (click to cycle):", True, TEXT_COLOR), (px + 12, y))
    y += 20

    btn_rects = []
    for wall_type in ASSIGNABLE_TYPES:
        cname = COLOR_NAMES[wall_type]
        verb = verbs.get(wall_type, VERB_PASS)
        vname = VERB_NAMES[verb]

        bx, by = px + 8, y
        bw, bh = PANEL_W - 16, 34

        hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
        bg = (50, 50, 65) if hovered else (38, 38, 52)
        pygame.draw.rect(screen, bg, (bx, by, bw, bh))

        # color swatch
        pygame.draw.rect(screen, WCOLOR[wall_type], (bx + 4, by + 4, 26, bh - 8))

        arrow_text = f"{cname}  \u2192  "
        screen.blit(font_sm.render(arrow_text, True, TEXT_COLOR), (bx + 36, by + 8))
        verb_x = bx + 36 + font_sm.size(arrow_text)[0]
        screen.blit(font_sm.render(vname, True, VERB_COLOR[verb]), (verb_x, by + 8))

        btn_rects.append((bx, by, bw, bh, wall_type))
        y += bh + 5

    return btn_rects


# ── main ──

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("They Grow Up So Fast")
    clock = pygame.time.Clock()
    font    = pygame.font.SysFont("consolas", 15)
    font_sm = pygame.font.SysFont("consolas", 13)

    level_idx = 0
    verbs = {WALL_RED: VERB_PASS, WALL_YELLOW: VERB_PASS, WALL_BLUE: VERB_PASS}

    grid, agents = make_grid(LEVELS[level_idx])
    walls_start = count_walls(grid)
    paused = True
    step = 0
    total_spawned = 1
    peak_pop = 1
    last_sim_tick = 0
    btn_hit_rects = []

    def reset_level():
        nonlocal grid, agents, walls_start, paused, step, total_spawned, peak_pop
        grid, agents = make_grid(LEVELS[level_idx])
        walls_start = count_walls(grid)
        paused = True
        step = 0
        total_spawned = 1
        peak_pop = 1

    def change_level(new_idx):
        nonlocal level_idx, verbs
        level_idx = new_idx % NUM_LEVELS
        verbs = {WALL_RED: VERB_PASS, WALL_YELLOW: VERB_PASS, WALL_BLUE: VERB_PASS}
        reset_level()

    running = True
    while running:
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    reset_level()
                elif event.key == pygame.K_n:
                    change_level(level_idx + 1)
                elif event.key == pygame.K_p:
                    change_level(level_idx - 1)
                elif event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for bx, by, bw, bh, wall_type in btn_hit_rects:
                    if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                        verbs[wall_type] = (verbs[wall_type] + 1) % VERB_COUNT
                        break

        # sim
        walls_left = count_walls(grid)
        game_over = (walls_left == 0) or (len(agents) == 0 and step > 0) or (step >= MAX_STEPS)
        if not paused and not game_over and now - last_sim_tick >= SIM_TICK_MS:
            last_sim_tick = now
            agents, spawned = sim_step(agents, grid, verbs)
            step += 1
            total_spawned += spawned
            if len(agents) > peak_pop:
                peak_pop = len(agents)

        # draw
        walls_left = count_walls(grid)
        screen.fill(BG)
        draw_grid(screen, grid, agents)
        btn_hit_rects = draw_panel(screen, font, font_sm, verbs, step, agents,
                                   total_spawned, peak_pop, walls_left, walls_start,
                                   paused, mouse_pos, level_idx)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


main()
