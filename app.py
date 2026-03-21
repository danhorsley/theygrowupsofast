# They Grow Up So Fast — prototype with sandwich (stacked) cells
# Agent walks a colored path. Each cell consumed on contact.
# SANDWICH cells: multiple colors stacked at one position.
#   Each agent pops the top layer. Remaining layers stay until next agent.
#   Drawn as horizontal color stripes — read top to bottom.
# Goal: consume all layers AND end with zero agents.

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

FIXED_VERB = {
    FIXED_PASS:       VERB_PASS,
    FIXED_REPLICATE:  VERB_REPLICATE,
    FIXED_DISSOLVE:   VERB_DISSOLVE,
    FIXED_TURN_LEFT:  VERB_TURN_LEFT,
    FIXED_TURN_RIGHT: VERB_TURN_RIGHT,
}

FIXED_LABEL = {
    FIXED_REPLICATE: "Replicate", FIXED_DISSOLVE: "Dissolve",
    FIXED_TURN_RIGHT: "Turn Right", FIXED_TURN_LEFT: "Turn Left",
    FIXED_PASS: "Pass",
}

# ── tuning ──

MAX_POP     = 100
MAX_STEPS   = 500
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

# ── cell helpers ──
# Grid cells are either:
#   EMPTY (0), AGENT (4), a wall type int (1-9), or a tuple of ints (sandwich stack)
# Sandwich: (B, R) means Blue on top, Red below. First agent pops Blue, second pops Red.

def is_wall(cell):
    if isinstance(cell, tuple):
        return len(cell) > 0
    return cell in ALL_WALL_TYPES

def pop_top(cell):
    """Pop top layer from a cell. Returns (top_color, remaining_cell_value)."""
    if isinstance(cell, tuple):
        top = cell[0]
        rest = cell[1:]
        if len(rest) == 0:
            return top, EMPTY
        if len(rest) == 1:
            return top, rest[0]
        return top, rest
    return cell, EMPTY

def get_verb(color, verbs):
    if color in FIXED_VERB:
        return FIXED_VERB[color]
    return verbs.get(color, VERB_PASS)

def count_walls(grid, underneath):
    """Count total consumable layers (grid + hidden under agents)."""
    n = 0
    for row in grid:
        for c in row:
            if isinstance(c, tuple):
                n += len(c)
            elif c in ALL_WALL_TYPES:
                n += 1
    for layers in underneath.values():
        n += len(layers)
    return n

def fixed_types_in_level(level):
    found = set()
    for _, _, c in level["cells"]:
        colors = c if isinstance(c, tuple) else (c,)
        for color in colors:
            if color in FIXED_TYPES:
                found.add(color)
    return sorted(found)


# ── level shorthand ──

R, Y, B = WALL_RED, WALL_YELLOW, WALL_BLUE
G, P = FIXED_REPLICATE, FIXED_DISSOLVE
O, C = FIXED_TURN_RIGHT, FIXED_TURN_LEFT
W = FIXED_PASS

def tape_level(colors):
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "start": (-1, 0),
        "dir": RIGHT,
    }


# ── levels ──

LEVELS = [
    # ── Phase 1: pure assignable, learn basics ──
    tape_level([R, Y, B]),
    tape_level([R, Y, B, B]),
    tape_level([R, Y, B, Y]),

    # ── Phase 2: introduce fixed squares ──
    tape_level([G, R, R]),
    tape_level([R, G, R, P, P]),
    tape_level([R, G, Y, P]),

    # ── Phase 3: harder assignable ──
    tape_level([R, R, Y, B, Y]),
    tape_level([R, Y, Y, B, B]),
    tape_level([R, Y, B, R, B]),
    tape_level([R, R, Y, B, B, B]),

    # ── Phase 4: 2D shapes with turns ──

    # 11: L-shape
    {
        "cells": [(0,0,R), (1,0,R), (2,0,B),
                                     (2,1,R), (2,2,R), (2,3,Y)],
        "start": (-1, 0), "dir": RIGHT,
    },
    # 12: Reverse L
    {
        "cells": [(2,0,Y), (2,1,R), (2,2,R), (0,3,R), (1,3,R), (2,3,B)],
        "start": (-1, 3), "dir": RIGHT,
    },
    # 13: U-shape
    {
        "cells": [(0,0,R), (1,0,R), (2,0,B), (2,1,R), (0,2,Y), (1,2,R), (2,2,B)],
        "start": (-1, 0), "dir": RIGHT,
    },
    # 14: Big U
    {
        "cells": [(0,0,R), (1,0,R), (2,0,R), (3,0,B),
                  (3,1,R), (3,2,R),
                  (0,3,Y), (1,3,R), (2,3,R), (3,3,B)],
        "start": (-1, 0), "dir": RIGHT,
    },
]

# ── Phase 5: fractal levels ──

from fractal import build_spiral_fractal, build_multi_fractal

LEVELS += [
    build_spiral_fractal(2, seg_len=2, seg_color=R, branch_color=Y, turn_color=B),
    build_spiral_fractal(3, seg_len=2, seg_color=B, branch_color=R, turn_color=Y),
    build_spiral_fractal(3, seg_len=3, seg_color=Y, branch_color=B, turn_color=R),
    build_multi_fractal(3, sub_depth=2, seg_len=2, trunk_seg=6,
                        seg_color=R, branch_color=Y, turn_color=B),
]

# ── Phase 6: sandwich (stacked cell) levels ──

LEVELS += [
    # 19: T-junction intro — sandwich corner splits two agents
    # R=Pass, Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,R), (1,0,G), (2,0,(B,R)), (3,0,R), (4,0,Y),
                               (2,1,R), (2,2,R), (2,3,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },

    # 20: Longer T-junction — same concept, more to consume
    # R=Pass, Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,R), (1,0,R), (2,0,G), (3,0,(B,R)), (4,0,R), (5,0,R), (6,0,Y),
                                         (3,1,R), (3,2,R), (3,3,R), (3,4,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },

    # 21: Cross junction — 3-layer sandwich, 3-way split
    # Sandwich (B, C, R): first agent turns right (B), second turns left (C=fixed),
    # third passes through (R). Three branches cleared simultaneously.
    # R=Pass, Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,R), (1,0,G), (2,0,R), (3,0,G), (4,0,(B,C,R)), (5,0,R), (6,0,Y),
                                                   (4,1,R), (4,2,R), (4,3,Y),
                                                   (4,-1,R), (4,-2,R), (4,-3,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },
]

NUM_LEVELS = len(LEVELS)


# ── world setup ──

def make_grid(level):
    grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
    cells = level["cells"]

    # flatten all positions for bounding box (handle sandwich tuples)
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
        grid[y + oy][x + ox] = c  # c can be int or tuple

    ax, ay = sx + ox, sy + oy
    grid[ay][ax] = AGENT
    agent = {"x": ax, "y": ay, "dx": level["dir"][0], "dy": level["dir"][1], "alive": True}

    underneath = {}  # (x, y) -> [remaining colors] for sandwich layers under agents

    return grid, [agent], underneath


# ── sim helpers ──

def vacate(x, y, grid, underneath):
    """Agent leaves position: restore any sandwich layers hidden underneath."""
    if (x, y) in underneath:
        r = underneath.pop((x, y))
        grid[y][x] = r[0] if len(r) == 1 else tuple(r)
    else:
        grid[y][x] = EMPTY

def occupy(nx, ny, grid, underneath, remaining):
    """Agent moves to position, hiding any remaining sandwich layers."""
    grid[ny][nx] = AGENT
    if remaining:
        underneath[(nx, ny)] = list(remaining) if isinstance(remaining, tuple) else [remaining]


# ── sim step ──

def sim_step(agents, grid, verbs, underneath):
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
            vacate(x, y, grid, underneath)
            a["x"], a["y"] = nx, ny
            grid[ny][nx] = AGENT

        elif is_wall(target):
            top, remaining = pop_top(target)
            verb = get_verb(top, verbs)

            # remaining is EMPTY (int 0), a single color (int), or a tuple
            has_remaining = remaining != EMPTY

            if verb == VERB_PASS:
                vacate(x, y, grid, underneath)
                a["x"], a["y"] = nx, ny
                if has_remaining:
                    occupy(nx, ny, grid, underneath, remaining)
                else:
                    grid[ny][nx] = AGENT

            elif verb == VERB_REPLICATE:
                child = {"x": nx, "y": ny, "dx": dx, "dy": dy, "alive": True}
                new_agents.append(child)
                if has_remaining:
                    occupy(nx, ny, grid, underneath, remaining)
                else:
                    grid[ny][nx] = AGENT

            elif verb == VERB_DISSOLVE:
                a["alive"] = False
                vacate(x, y, grid, underneath)
                if has_remaining:
                    grid[ny][nx] = remaining if not isinstance(remaining, list) else tuple(remaining)
                else:
                    grid[ny][nx] = EMPTY

            elif verb == VERB_TURN_LEFT:
                vacate(x, y, grid, underneath)
                a["x"], a["y"] = nx, ny
                a["dx"], a["dy"] = turn_left(dx, dy)
                if has_remaining:
                    occupy(nx, ny, grid, underneath, remaining)
                else:
                    grid[ny][nx] = AGENT

            elif verb == VERB_TURN_RIGHT:
                vacate(x, y, grid, underneath)
                a["x"], a["y"] = nx, ny
                a["dx"], a["dy"] = turn_right(dx, dy)
                if has_remaining:
                    occupy(nx, ny, grid, underneath, remaining)
                else:
                    grid[ny][nx] = AGENT

        elif target == AGENT:
            pass  # blocked

    # add newborns
    spawned = 0
    for na in new_agents:
        if len(agents) + spawned >= MAX_POP:
            break
        agents.append(na)
        spawned += 1

    alive = [a for a in agents if a["alive"]]
    return alive, spawned


def in_bounds(x, y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H


# ── drawing ──

def draw_cell(screen, rx, ry, cell):
    """Draw a single cell or sandwich at pixel position (rx, ry)."""
    if isinstance(cell, tuple):
        # sandwich: horizontal stripes, top color at top
        n = len(cell)
        inner_h = CELL - 2
        for i, color in enumerate(cell):
            sy = ry + 1 + (inner_h * i) // n
            sh = (inner_h * (i + 1)) // n - (inner_h * i) // n
            pygame.draw.rect(screen, WCOLOR[color], (rx + 1, sy, CELL - 2, sh))
            if color in FIXED_TYPES:
                pygame.draw.rect(screen, (255,255,255), (rx+3, sy+1, CELL-6, max(sh-2, 1)), 1)
    elif cell in WCOLOR:
        pygame.draw.rect(screen, WCOLOR[cell], (rx+1, ry+1, CELL-2, CELL-2))
        if cell in FIXED_TYPES:
            pygame.draw.rect(screen, (255,255,255), (rx+4, ry+4, CELL-8, CELL-8), 1)


def draw_grid(screen, grid, agents, underneath):
    for y in range(GRID_H):
        for x in range(GRID_W):
            c = grid[y][x]
            if is_wall(c):
                draw_cell(screen, x * CELL, y * CELL, c)

    for a in agents:
        if not a["alive"]:
            continue
        rx, ry = a["x"] * CELL, a["y"] * CELL
        cx, cy = rx + CELL // 2, ry + CELL // 2

        # if sitting on a sandwich, draw remaining layers underneath (dimmed)
        key = (a["x"], a["y"])
        if key in underneath:
            layers = underneath[key]
            cell_val = layers[0] if len(layers) == 1 else tuple(layers)
            # draw dimmed
            draw_cell(screen, rx, ry, cell_val)
            # dim overlay
            dim = pygame.Surface((CELL-2, CELL-2))
            dim.set_alpha(140)
            dim.fill(BG)
            screen.blit(dim, (rx+1, ry+1))

        pygame.draw.circle(screen, AGENT_COLOR, (cx, cy), CELL // 2 - 2)
        tip_x = cx + a["dx"] * (CELL // 4)
        tip_y = cy + a["dy"] * (CELL // 4)
        pygame.draw.circle(screen, AGENT_DOT, (tip_x, tip_y), 3)


def draw_preview_cell(screen, rx, ry, cell, pc):
    """Draw a mini cell/sandwich in the preview panel."""
    if isinstance(cell, tuple):
        n = len(cell)
        for i, color in enumerate(cell):
            sy = ry + (pc * i) // n
            sh = (pc * (i + 1)) // n - (pc * i) // n
            pygame.draw.rect(screen, WCOLOR[color], (rx, sy, pc, sh))
    elif cell in WCOLOR:
        pygame.draw.rect(screen, WCOLOR[cell], (rx, ry, pc, pc))
        if cell in FIXED_TYPES:
            pygame.draw.rect(screen, (255,255,255), (rx+2, ry+2, pc-4, pc-4), 1)


def draw_shape_preview(screen, font_sm, level, px, y):
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
        draw_preview_cell(screen, rx, ry, color, pc)

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

    screen.blit(font_sm.render("SPACE run/pause   R reset", True, TEXT_DIM), (px + 12, y))
    screen.blit(font_sm.render("N next   P prev   ESC quit", True, TEXT_DIM), (px + 12, y + 15))
    y += 36

    level = LEVELS[level_idx % NUM_LEVELS]
    screen.blit(font_sm.render("SHAPE:", True, TEXT_COLOR), (px + 12, y))
    y += 18
    y = draw_shape_preview(screen, font_sm, level, px + 12, y)

    fixed_in_level = fixed_types_in_level(level)
    if fixed_in_level:
        y += 4
        screen.blit(font_sm.render("FIXED (automatic):", True, TEXT_DIM), (px + 12, y))
        y += 16
        for ft in fixed_in_level:
            pygame.draw.rect(screen, WCOLOR[ft], (px + 14, y, 14, 14))
            pygame.draw.rect(screen, (255,255,255), (px + 16, y + 2, 10, 10), 1)
            screen.blit(font_sm.render(FIXED_LABEL[ft], True, TEXT_DIM), (px + 34, y))
            y += 17
    y += 8

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

    grid, agents, underneath = make_grid(LEVELS[level_idx])
    walls_start = count_walls(grid, underneath)
    paused = True
    step = 0
    total_spawned = 1
    peak_pop = 1
    last_sim_tick = 0
    btn_hit_rects = []

    def reset_level():
        nonlocal grid, agents, underneath, walls_start, paused, step, total_spawned, peak_pop
        grid, agents, underneath = make_grid(LEVELS[level_idx])
        walls_start = count_walls(grid, underneath)
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

        walls_left = count_walls(grid, underneath)
        game_over = (walls_left == 0) or (len(agents) == 0 and step > 0) or (step >= MAX_STEPS)
        if not paused and not game_over and now - last_sim_tick >= SIM_TICK_MS:
            last_sim_tick = now
            agents, spawned = sim_step(agents, grid, verbs, underneath)
            step += 1
            total_spawned += spawned
            if len(agents) > peak_pop:
                peak_pop = len(agents)

        walls_left = count_walls(grid, underneath)
        screen.fill(BG)
        draw_grid(screen, grid, agents, underneath)
        btn_hit_rects = draw_panel(screen, font, font_sm, verbs, step, agents,
                                   total_spawned, peak_pop, walls_left, walls_start,
                                   paused, mouse_pos, level_idx)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


main()
