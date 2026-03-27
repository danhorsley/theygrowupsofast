# They Grow Up So Fast — prototype with sandwich (stacked) cells
# Agent walks a colored path. Each cell consumed on contact.
# SANDWICH cells: multiple colors stacked at one position.
#   Each agent pops the top layer. Remaining layers stay until next agent.
#   Drawn as horizontal color stripes — read top to bottom.
# Goal: consume all layers AND end with zero agents.

import pygame
import sys
import os
import asyncio

# ensure our own directory is on the path for sibling imports (sound.py, fractal.py)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

try:
    from sound import GameSounds
    _HAS_SOUND = True
except (ImportError, Exception):
    _HAS_SOUND = False

# ── layout ──

CELL     = 20
GRID_W   = 38
GRID_H   = 26
GRID_PX_W = GRID_W * CELL
GRID_PX_H = GRID_H * CELL
PANEL_W  = 280
WIN_W    = GRID_PX_W + PANEL_W
WIN_H    = max(GRID_PX_H, 680)

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

# editor-only cell types (not used in campaign, available for community levels)
FIXED_REVERSE    = 10  # pink — agent reverses direction (180 turn)
FIXED_SKIP       = 11  # lime — agent consumes but jumps over next cell
FIXED_ONE_WAY_R  = 12  # white-right — passable going right, blocks other dirs
FIXED_ONE_WAY_D  = 13  # white-down
FIXED_ONE_WAY_L  = 14  # white-left
FIXED_ONE_WAY_U  = 15  # white-up
FIXED_TELEPORT_A = 16  # teleport pair 1 entrance (legacy, kept for compat)
FIXED_TELEPORT_B = 17  # teleport pair 1 exit (legacy)

# multi-pair teleports: 4 pairs, In/Out each
TELE_IN_1  = 16  # same as FIXED_TELEPORT_A (pair 1 in)
TELE_OUT_1 = 17  # same as FIXED_TELEPORT_B (pair 1 out)
TELE_IN_2  = 20
TELE_OUT_2 = 21
TELE_IN_3  = 22
TELE_OUT_3 = 23
TELE_IN_4  = 24
TELE_OUT_4 = 25

TELE_PAIRS = {
    TELE_IN_1: TELE_OUT_1, TELE_OUT_1: TELE_IN_1,
    TELE_IN_2: TELE_OUT_2, TELE_OUT_2: TELE_IN_2,
    TELE_IN_3: TELE_OUT_3, TELE_OUT_3: TELE_IN_3,
    TELE_IN_4: TELE_OUT_4, TELE_OUT_4: TELE_IN_4,
}
ALL_TELE_TYPES = tuple(TELE_PAIRS.keys())

# editor-only assignable colors (not used in campaign)
WALL_PINK  = 18
WALL_TEAL  = 19

ASSIGNABLE_TYPES = (WALL_RED, WALL_YELLOW, WALL_BLUE, WALL_PINK)
EDITOR_ASSIGNABLE = (WALL_TEAL,)  # teal remains editor-only
ALL_ASSIGNABLE = ASSIGNABLE_TYPES + EDITOR_ASSIGNABLE
FIXED_TYPES = (FIXED_REPLICATE, FIXED_DISSOLVE, FIXED_TURN_RIGHT, FIXED_TURN_LEFT, FIXED_PASS)
EDITOR_EXTRA_TYPES = (FIXED_REVERSE, FIXED_SKIP,
                      FIXED_ONE_WAY_R, FIXED_ONE_WAY_D, FIXED_ONE_WAY_L, FIXED_ONE_WAY_U,
                      TELE_IN_1, TELE_OUT_1, TELE_IN_2, TELE_OUT_2,
                      TELE_IN_3, TELE_OUT_3, TELE_IN_4, TELE_OUT_4)
ALL_WALL_TYPES = ALL_ASSIGNABLE + FIXED_TYPES + EDITOR_EXTRA_TYPES
# ensure all teleport types are recognized as walls
assert all(t in ALL_WALL_TYPES for t in ALL_TELE_TYPES), "Missing teleport types in ALL_WALL_TYPES"

ONE_WAY_TYPES = (FIXED_ONE_WAY_R, FIXED_ONE_WAY_D, FIXED_ONE_WAY_L, FIXED_ONE_WAY_U)
ONE_WAY_DIR = {
    FIXED_ONE_WAY_R: (1, 0), FIXED_ONE_WAY_D: (0, 1),
    FIXED_ONE_WAY_L: (-1, 0), FIXED_ONE_WAY_U: (0, -1),
}
TELEPORT_TYPES = ALL_TELE_TYPES

COLOR_NAMES = {
    WALL_RED: "Red", WALL_YELLOW: "Yellow", WALL_BLUE: "Blue",
    FIXED_REPLICATE: "Green", FIXED_DISSOLVE: "Purple",
    FIXED_TURN_RIGHT: "Orange", FIXED_TURN_LEFT: "Cyan",
    FIXED_PASS: "Grey",
    FIXED_REVERSE: "Reverse", FIXED_SKIP: "Skip",
    FIXED_ONE_WAY_R: "Gate R", FIXED_ONE_WAY_D: "Gate D",
    FIXED_ONE_WAY_L: "Gate L", FIXED_ONE_WAY_U: "Gate U",
    TELE_IN_1: "Tel1→", TELE_OUT_1: "→Tel1",
    TELE_IN_2: "Tel2→", TELE_OUT_2: "→Tel2",
    TELE_IN_3: "Tel3→", TELE_OUT_3: "→Tel3",
    TELE_IN_4: "Tel4→", TELE_OUT_4: "→Tel4",
    WALL_PINK: "Pink", WALL_TEAL: "Teal",
}

# ── verbs ──

VERB_PASS       = 0
VERB_REPLICATE  = 1
VERB_DISSOLVE   = 2
VERB_TURN_LEFT  = 3
VERB_TURN_RIGHT = 4
VERB_REVERSE    = 5
VERB_SKIP       = 6
VERB_WAIT       = 7
VERB_COUNT      = 5  # campaign uses 5 verbs; editor uses all 8

VERB_NAMES = {
    VERB_PASS:       "Pass",
    VERB_REPLICATE:  "Replicate",
    VERB_DISSOLVE:   "Dissolve",
    VERB_TURN_LEFT:  "Turn Left",
    VERB_TURN_RIGHT: "Turn Right",
    VERB_REVERSE:    "Reverse",
    VERB_SKIP:       "Skip",
    VERB_WAIT:       "Wait",
}

FIXED_VERB = {
    FIXED_PASS:       VERB_PASS,
    FIXED_REPLICATE:  VERB_REPLICATE,
    FIXED_DISSOLVE:   VERB_DISSOLVE,
    FIXED_TURN_LEFT:  VERB_TURN_LEFT,
    FIXED_TURN_RIGHT: VERB_TURN_RIGHT,
    FIXED_REVERSE:    VERB_REVERSE,
    FIXED_SKIP:       VERB_SKIP,
}

FIXED_LABEL = {
    FIXED_REPLICATE: "Replicate", FIXED_DISSOLVE: "Dissolve",
    FIXED_TURN_RIGHT: "Turn Right", FIXED_TURN_LEFT: "Turn Left",
    FIXED_PASS: "Pass", FIXED_REVERSE: "Reverse", FIXED_SKIP: "Skip",
    FIXED_ONE_WAY_R: "Gate Right", FIXED_ONE_WAY_D: "Gate Down",
    FIXED_ONE_WAY_L: "Gate Left", FIXED_ONE_WAY_U: "Gate Up",
    TELE_IN_1: "Teleport 1 In", TELE_OUT_1: "Teleport 1 Out",
    TELE_IN_2: "Teleport 2 In", TELE_OUT_2: "Teleport 2 Out",
    TELE_IN_3: "Teleport 3 In", TELE_OUT_3: "Teleport 3 Out",
    TELE_IN_4: "Teleport 4 In", TELE_OUT_4: "Teleport 4 Out",
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

# per-agent team colors (for multi-rule levels)
TEAM_COLORS = [
    (70, 210, 120),   # team 0: green (same as default)
    (100, 160, 255),  # team 1: blue
    (255, 160, 80),   # team 2: orange
    (220, 120, 200),  # team 3: pink
]
TEAM_NAMES = ["A", "B", "C", "D"]
EVIL_COLOR = (220, 50, 50)  # red for evil agents in intercept mode

WCOLOR = {
    WALL_RED:        (200, 60, 60),
    WALL_YELLOW:     (210, 195, 50),
    WALL_BLUE:       (55, 100, 200),
    FIXED_REPLICATE: (50, 180, 80),
    FIXED_DISSOLVE:  (150, 60, 190),
    FIXED_TURN_RIGHT:(220, 130, 40),
    FIXED_TURN_LEFT: (50, 180, 200),
    FIXED_PASS:      (90, 90, 100),
    FIXED_REVERSE:   (220, 100, 160),
    FIXED_SKIP:      (160, 220, 60),
    FIXED_ONE_WAY_R: (180, 180, 190),
    FIXED_ONE_WAY_D: (180, 180, 190),
    FIXED_ONE_WAY_L: (180, 180, 190),
    FIXED_ONE_WAY_U: (180, 180, 190),
    TELE_IN_1: (160, 40, 130),     # pair 1: dark magenta IN
    TELE_OUT_1:(230, 120, 200),   # pair 1: light magenta OUT
    TELE_IN_2: (30, 120, 140),    # pair 2: dark cyan IN
    TELE_OUT_2:(100, 210, 230),   # pair 2: light cyan OUT
    TELE_IN_3: (160, 120, 30),    # pair 3: dark amber IN
    TELE_OUT_3:(230, 200, 100),   # pair 3: light amber OUT
    TELE_IN_4: (50, 130, 40),     # pair 4: dark lime IN
    TELE_OUT_4:(140, 220, 120),   # pair 4: light lime OUT
    WALL_PINK:       (230, 100, 180),   # vibrant pink — 4th assignable
    WALL_TEAL:       (60, 180, 170),
}

VERB_COLOR = {
    VERB_PASS:       (120, 120, 130),
    VERB_REPLICATE:  (80, 220, 120),
    VERB_DISSOLVE:   (220, 160, 50),
    VERB_TURN_LEFT:  (70, 180, 220),
    VERB_TURN_RIGHT: (180, 100, 220),
    VERB_REVERSE:    (220, 100, 160),
    VERB_SKIP:       (160, 220, 60),
    VERB_WAIT:       (200, 180, 100),
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

def get_disabled_verbs(level):
    """Return dict of {color: [disabled verb ints]} from level definition."""
    return level.get("disabled_verbs", {})

def cycle_verb(current, disabled_list):
    """Cycle to next allowed verb, skipping disabled ones."""
    for _ in range(VERB_COUNT):
        current = (current + 1) % VERB_COUNT
        if current not in disabled_list:
            return current
    return current  # fallback

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

    # ── Phase 3: harder assignable (mix in grey filler) ──
    tape_level([W, R, Y, B, Y]),
    tape_level([R, W, Y, B, B]),
    tape_level([W, Y, B, R, B]),
    tape_level([R, R, Y, W, B, B]),

    # ── Phase 4: 2D shapes with turns ──

    # 11: L-shape
    {
        "cells": [(0,0,W), (1,0,W), (2,0,B),
                                     (2,1,W), (2,2,W), (2,3,Y)],
        "start": (-1, 0), "dir": RIGHT,
    },
    # 12: Reverse L
    {
        "cells": [(2,0,Y), (2,1,W), (2,2,W), (0,3,W), (1,3,W), (2,3,B)],
        "start": (-1, 3), "dir": RIGHT,
    },
    # 13: U-shape
    {
        "cells": [(0,0,W), (1,0,W), (2,0,B), (2,1,W), (0,2,Y), (1,2,W), (2,2,B)],
        "start": (-1, 0), "dir": RIGHT,
    },
    # 14: Big U
    {
        "cells": [(0,0,W), (1,0,W), (2,0,W), (3,0,B),
                  (3,1,W), (3,2,W),
                  (0,3,Y), (1,3,W), (2,3,W), (3,3,B)],
        "start": (-1, 0), "dir": RIGHT,
    },
]

# ── Phase 5: fractal levels ──

from fractal import build_spiral_fractal, build_multi_fractal, build_key_fractal, build_gap_key_fractal

LEVELS += [
    build_spiral_fractal(2, seg_len=2, seg_color=W, branch_color=Y, turn_color=B),
    build_spiral_fractal(3, seg_len=2, seg_color=W, branch_color=R, turn_color=Y),
    build_spiral_fractal(3, seg_len=3, seg_color=W, branch_color=B, turn_color=R),
    build_multi_fractal(3, sub_depth=2, seg_len=2, trunk_seg=6,
                        seg_color=W, branch_color=Y, turn_color=B),
]

# ── Phase 6: sandwich (stacked cell) levels ──

LEVELS += [
    # 19: T-junction intro — sandwich corner splits two agents
    # R=Pass, Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,W), (1,0,G), (2,0,(B,W)), (3,0,W), (4,0,Y),
                               (2,1,W), (2,2,W), (2,3,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },

    # 20: Longer T-junction — same concept, more to consume
    # R=Pass, Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,W), (1,0,W), (2,0,G), (3,0,(B,W)), (4,0,W), (5,0,W), (6,0,Y),
                                         (3,1,W), (3,2,W), (3,3,W), (3,4,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },

    # 21: Cross junction — 3-layer sandwich, 3-way split
    # Sandwich (B, C, W): first agent turns right (B), second turns left (C=fixed),
    # third passes through (W=grey). Three branches cleared simultaneously.
    # Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,W), (1,0,G), (2,0,W), (3,0,G), (4,0,(B,C,W)), (5,0,W), (6,0,Y),
                                                   (4,1,W), (4,2,W), (4,3,Y),
                                                   (4,-1,W), (4,-2,W), (4,-3,Y),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },
]

# ── Phase 7: key puzzle + fractal reward ──

LEVELS += [
    # 22: Key puzzle + depth-2 fractal tail (44 layers, peak ~4)
    build_key_fractal(fractal_depth=2),

    # 23: Key puzzle + depth-3 fractal tail (72 layers, peak ~7)
    build_key_fractal(fractal_depth=3),
]

# ── Phase 8: gap-based levels (air gaps for timing) ──

LEVELS += [
    # 24: Gap fork — standalone timing puzzle with air gaps
    # Fewer cells, cleaner visuals, same timing mechanic
    # Y=Dissolve, B=TurnRight
    {
        "cells": [
            (0,0,W), (1,0,G), (2,0,(B,W)),
            (6,0,(W,Y)),
            (8,0,P),
            (2,1,W), (2,3,W), (2,4,C),
            (3,4,W), (6,4,C),
            (6,3,W), (6,1,W),
        ],
        "start": (-1, 0), "dir": RIGHT,
    },

    # 25: Gap key + depth-2 fractal (39 layers, peak 4)
    build_gap_key_fractal(fractal_depth=2),

    # 26: Gap key + depth-3 fractal (69 layers, peak 7) — the big finale
    build_gap_key_fractal(fractal_depth=3),
]

# ── Phase 9: generated puzzles (brute-force + heuristic scored) ──

LEVELS += [
    # 27: R=Pass Y=Dissolve B=Replicate — B replicates, Y kills
    {"cells": [(0,0,B), (1,0,Y), (2,0,R), (3,0,Y)],
     "start": (-1, 0), "dir": RIGHT},

    # 28: R=Pass Y=Dissolve B=Replicate — longer, same idea
    {"cells": [(0,0,B), (1,0,R), (2,0,Y), (3,0,B), (4,0,Y), (5,0,R), (6,0,Y)],
     "start": (-1, 0), "dir": RIGHT},

    # 29: R=Replicate Y=Pass B=Dissolve — fixed G+P mixed in, peak 4
    {"cells": [(0,0,R), (1,0,G), (2,0,Y), (3,0,R), (4,0,B), (5,0,P), (6,0,P), (7,0,B)],
     "start": (-1, 0), "dir": RIGHT},

    # 30: R=Replicate Y=Pass B=Dissolve — tight
    {"cells": [(0,0,R), (1,0,Y), (2,0,B), (3,0,Y), (4,0,B)],
     "start": (-1, 0), "dir": RIGHT},

    # 31: R=Dissolve Y=Dissolve B=Replicate — two colors dissolve!
    {"cells": [(0,0,B), (1,0,B), (2,0,R), (3,0,B), (4,0,Y), (5,0,R), (6,0,R)],
     "start": (-1, 0), "dir": RIGHT},

    # 32: R=Replicate Y=Replicate B=Dissolve — two colors replicate!
    {"cells": [(0,0,R), (1,0,B), (2,0,Y), (3,0,B), (4,0,B)],
     "start": (-1, 0), "dir": RIGHT},

    # 33: R=Replicate Y=Replicate B=Dissolve — longer, peak 3
    {"cells": [(0,0,R), (1,0,B), (2,0,Y), (3,0,Y), (4,0,B), (5,0,B), (6,0,B)],
     "start": (-1, 0), "dir": RIGHT},
]

# ── Phase 10: two-agent facing levels ──

def facing_level(colors):
    """Two agents approach a tape from opposite ends."""
    n = len(colors)
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0},
            {"x": n, "y": 0, "dx": -1, "dy": 0},
        ],
    }

LEVELS += [
    # 34: Intro facing — R=Replicate Y=Dissolve B=Pass (peak 4)
    facing_level([R, Y, Y, Y, Y, B, R]),

    # 35: R=Replicate Y=Dissolve B=Pass — different shape
    facing_level([R, Y, B, Y, Y, Y, R]),

    # 36: R=Replicate Y=Pass B=Dissolve (peak 4)
    facing_level([R, Y, B, B, B, B, R]),

    # 37: R=Pass Y=Dissolve B=Replicate — 3 colors, trickier (peak 3)
    facing_level([R, Y, Y, R, Y, B]),

    # 38: R=Dissolve Y=Replicate B=Pass — reversed expectations (peak 3)
    facing_level([R, R, R, R, Y, B, Y]),

    # 39: R=Replicate Y=Dissolve B=Replicate — two colors replicate! (peak 4)
    facing_level([R, Y, B, Y, Y]),

    # 40: R=Pass Y=Dissolve B=Replicate — longer, 1 solution
    facing_level([R, Y, Y, R, Y, B]),

    # 41: R=Replicate Y=Pass B=Dissolve — 1 solution
    facing_level([R, Y, B, Y, B, B, Y]),
]

# ── Phase 11: hard facing — longest, peak 4, 1 solution ──
LEVELS += [
    # 42: R=Replicate Y=Dissolve B=Pass — 8 cells, asymmetric, 2 agents swarm
    facing_level([R, Y, B, Y, Y, Y, B, R]),
]

# ── Phase 12: per-agent rules — each agent has its own verb assignment ──

def per_agent_facing(colors):
    """Two agents with separate rule sets approach from opposite ends."""
    n = len(colors)
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": n, "y": 0, "dx": -1, "dy": 0, "team": 1},
        ],
        "per_agent_rules": True,
    }

def per_agent_staggered(colors, gap=3):
    """Two agents with separate rules, both go right, staggered start."""
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": -1 - gap, "y": 0, "dx": 1, "dy": 0, "team": 1},
        ],
        "per_agent_rules": True,
    }

LEVELS += [
    # 43: Per-agent intro — 2 solutions, gentle
    # A: R=Replicate Y=Dissolve  B: R=Dissolve Y=Pass
    per_agent_facing([R, Y, B, Y, R, B, Y]),

    # 44: Asymmetric — one replicates, other dissolves on same color
    # A: R=Replicate Y=Dissolve B=Pass  B: R=Pass Y=Pass B=Dissolve
    per_agent_facing([R, Y, Y, B, Y, R, Y]),

    # 45: All 3 verbs split across agents
    # A: R=Replicate Y=Pass B=Dissolve  B: R=Pass Y=Dissolve B=Pass
    per_agent_facing([R, Y, Y, B, Y, Y, B]),

    # 46: Tricky — B must replicate for agent B
    # A: R=Pass Y=Pass B=Dissolve  B: R=Dissolve Y=Pass B=Replicate
    per_agent_facing([R, R, Y, R, Y, R, B]),

    # 47: Hardest — unique-ish solution, all 3 colors meaningful
    per_agent_facing([R, Y, B, R, Y, B]),
]


# ── fractal builder ──

def build_fractal_branch(depth, seg_len, ox, oy, dx, dy, seg_color):
    """Generate fractal branch cells. seg_color for path segments, fixed G/O/P for structure."""
    cells = []
    def branch(x, y, ddx, ddy, d):
        for i in range(seg_len):
            cells.append((x + ddx * i, y + ddy * i, seg_color))
        ex, ey = x + ddx * seg_len, y + ddy * seg_len
        if d == 0:
            cells.append((ex, ey, FIXED_DISSOLVE))
            return
        cells.append((ex, ey, FIXED_REPLICATE))
        bx, by = ex + ddx, ey + ddy
        cells.append((bx, by, FIXED_TURN_RIGHT))
        cdx, cdy = turn_right(ddx, ddy)
        branch(bx + ddx, by + ddy, ddx, ddy, d - 1)
        branch(bx + cdx, by + cdy, cdx, cdy, d - 1)
    branch(ox, oy, dx, dy, depth)
    return cells

# ── Phase 13: dual-corner fractal — the spectacle levels ──
# Two agents start at opposite corners. Each solves a key puzzle,
# then their agent enters a fractal quadrant. At peak, many agents
# swarm simultaneously, then everything dissolves to zero.
# A uses R segments (R=Pass, Y=Dissolve, B=TurnRight)
# B uses Y segments (Y=Pass, B=Dissolve, R=TurnLeft)

def build_dual_fractal(depth, frac_start, bx_off, by_off):
    """Build a dual-corner key+fractal level.
    Grey (FIXED_PASS) for all path segments. Assignable colors only at decision points."""
    W = FIXED_PASS  # grey road
    key_a = [
        (0,0,W), (1,0,FIXED_REPLICATE), (2,0,(WALL_BLUE, W)),   # split sandwich: B=TurnRight
        (6,0,(W, WALL_YELLOW)),                                    # timing sandwich: Y=Dissolve
        (2,1,W), (2,3,W), (2,4,FIXED_TURN_LEFT),                 # detour
        (3,4,W), (6,4,FIXED_TURN_LEFT),
        (6,3,W), (6,1,W),
    ] + [(i, 0, W) for i in range(8, frac_start)]

    frac_a = build_fractal_branch(depth, 2, frac_start, 0, 1, 0, W)

    key_b = [
        (bx_off, by_off, W),
        (bx_off-1, by_off, FIXED_REPLICATE),
        (bx_off-2, by_off, (WALL_RED, W)),                        # split sandwich: R=TurnLeft
        (bx_off-6, by_off, (W, WALL_BLUE)),                       # timing sandwich: B=Dissolve
        (bx_off-8, by_off, W),
        (bx_off-9, by_off, W),
        (bx_off-2, by_off+1, W),
        (bx_off-2, by_off+3, W),
        (bx_off-2, by_off+4, FIXED_TURN_RIGHT),
        (bx_off-3, by_off+4, W),
        (bx_off-6, by_off+4, FIXED_TURN_RIGHT),
        (bx_off-6, by_off+3, W),
        (bx_off-6, by_off+1, W),
    ] + [(bx_off-i, by_off, W) for i in range(10, frac_start)]

    frac_b = build_fractal_branch(depth, 2, bx_off-frac_start, by_off, -1, 0, W)

    return {
        "cells": key_a + frac_a + key_b + frac_b,
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": bx_off+1, "y": by_off, "dx": -1, "dy": 0, "team": 1},
        ],
        "per_agent_rules": True,
    }

# ── Phase 14: generated 2D puzzles — unique solutions, turns required ──

LEVELS += [
    # 48: L-shape, 1 sol — R=Pass Y=Dissolve B=TurnLeft
    {"cells": [(0,-1,B),(0,0,R),(0,1,B),(1,0,Y),(1,1,B)], "start": (1,-1), "dir": (-1,0)},

    # 49: Corner, 1 sol — R=TurnRight Y=Dissolve B=TurnLeft
    {"cells": [(-1,1,R),(0,0,R),(0,1,B),(1,0,Y)], "start": (-1,2), "dir": (0,-1)},

    # 50: Zigzag, 1 sol — R=Dissolve Y=Pass B=TurnLeft
    {"cells": [(0,-1,B),(0,0,R),(1,-1,B),(1,0,Y),(1,1,Y)], "start": (1,2), "dir": (0,-1)},

    # 51: Hook, 1 sol — R=TurnRight Y=TurnLeft B=Dissolve
    {"cells": [(-2,1,B),(-1,0,Y),(-1,1,R),(0,0,Y),(0,1,R)], "start": (1,1), "dir": (-1,0)},

    # 52: Grey road + turns, 1 sol — R=TurnLeft Y=TurnLeft B=Dissolve
    {"cells": [(-1,-1,B),(0,-1,W),(0,0,W),(0,1,R),(1,-1,Y),(1,0,W),(1,1,R)], "start": (0,-2), "dir": (0,1)},

    # 53: Replicate + turns, 5 sol — R=Dissolve Y=TurnLeft B=Pass
    {"cells": [(-1,-2,Y),(-1,0,R),(0,-2,Y),(0,-1,R),(0,0,G)], "start": (0,1), "dir": (0,-1)},

    # 54: Fixed turn + assignable, 5 sol — R=Pass Y=Dissolve B=TurnLeft
    {"cells": [(-1,-1,Y),(-1,0,O),(0,0,B),(0,1,B)], "start": (-1,1), "dir": (1,0)},
]

# ── Phase 15: dual-corner fractal — the spectacle levels ──

LEVELS += [
    # 55: Dual fractal depth 2 — peak 8, the "aha" moment
    build_dual_fractal(depth=2, frac_start=10, bx_off=30, by_off=16),

    # 56: Dual fractal depth 3 — peak 14, the grand finale
    build_dual_fractal(depth=3, frac_start=12, bx_off=32, by_off=18),
]

# ── Phase 14: swarm shape levels ──
# Vertical cascade of R=Replicate + B=TurnLeft spawns N agents
# who attack recognizable shapes in parallel. Visual payoff levels.
# Solution: R=Replicate, Y=Dissolve, B=TurnLeft (unique for all)

def make_swarm_shape(n_rows, row_fn, row_width):
    """Vertical replication cascade feeding N rows of a shape."""
    cells = []
    for i in range(n_rows):
        cells.append((0, i*2, R))
        cells.append((0, i*2+1, B))
    cells.append((0, n_rows*2, Y))
    for i in range(n_rows):
        ry = i*2+1
        row = row_fn(i, n_rows, row_width)
        for x, c in row:
            cells.append((x+1, ry, c))
        cells.append((row_width+1, ry, Y))
    return {"cells": cells, "start": (0, -1), "dir": (0, 1)}

def _row_plain(i, n, w):
    return [(x, W) for x in range(w)]

def _row_pyramid(i, n, w):
    rw = max(1, w - i)
    return [(x, W) for x in range(rw)]

def _row_diamond(i, n, w):
    mid = n // 2
    rw = min(w, i + 2) if i <= mid else min(w, n - i + 1)
    return [(x, W) for x in range(rw)]

def _row_steps(i, n, w):
    return [(x, W) for x in range(min(w, i + 1))]

def _row_triangle(i, n, w):
    return [(x, W) for x in range(min(w, n - i))]

LEVELS += [
    # 57: Rectangle 4x6 — intro to swarm (peak 3)
    make_swarm_shape(4, _row_plain, 6),

    # 58: Steps 6 — staircase swarm (peak 3)
    make_swarm_shape(6, _row_steps, 6),

    # 59: Pyramid 6 — pyramid dissolve (peak 4)
    make_swarm_shape(6, _row_pyramid, 8),

    # 60: Diamond 6 — diamond dissolve (peak 4)
    make_swarm_shape(6, _row_diamond, 8),

    # 61: Triangle 6 — inverted triangle (peak 4)
    make_swarm_shape(6, _row_triangle, 8),

    # 62: Rectangle 8x10 — the big payoff (peak 4, 105 cells)
    make_swarm_shape(8, _row_plain, 10),
]

# ── Phase 15: bounce levels ──
# Two agents face each other. They walk in, bounce on collision, reverse,
# and each clears their half. The player figures out the shared rules.

def bounce_gap(left_colors, right_colors):
    """Two agents face symmetric tape with gap in middle."""
    cells = []
    for i, c in enumerate(left_colors):
        cells.append((i, 0, c))
    gap_x = len(left_colors)
    for i, c in enumerate(right_colors):
        cells.append((gap_x + 1 + i, 0, c))
    return {
        "cells": cells,
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": gap_x + 1 + len(right_colors), "y": 0, "dx": -1, "dy": 0, "team": 0},
        ],
    }

def bounce_headon(colors):
    """Two agents face each other on a tape, no gap."""
    n = len(colors)
    return {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "agents": [
            {"x": -1, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": n, "y": 0, "dx": -1, "dy": 0, "team": 0},
        ],
    }

LEVELS += [
    # 63: Bounce intro — simple symmetric, gap (5 solutions, gentle)
    bounce_gap([R, Y], [Y, R]),

    # 64: Bounce 3-color gap (2 solutions, tighter)
    bounce_gap([R, Y, B], [B, Y, R]),

    # 65: Bounce unique — 8 cells, only 1 solution
    bounce_gap([R, R, Y, B], [B, Y, R, R]),

    # 66: Head-on 3-color (2 solutions, no gap)
    bounce_headon([R, Y, B, Y, R]),

    # 67: Head-on symmetric 6-cell (2 solutions incl. replicate variant)
    bounce_headon([R, Y, B, B, Y, R]),

    # 68: Longer bounce — asymmetric arms, unique solution
    bounce_gap([R, R, R, Y, B], [B, Y, R, R, R]),
]

# ── Phase 16: intercept mode — route evil agents to dissolve ──
# Evil agents (red) have fixed rules visible to the player.
# Hero agent (green) uses player-assigned rules.
# Win: all evil agents dissolved.

def intercept_level(cells, hero_def, evil_defs, evil_rules):
    """Build an intercept level."""
    agents = [dict(hero_def, team=0, evil=False)]
    for ed in evil_defs:
        agents.append(dict(ed, team=1, evil=True))
    return {
        "cells": cells,
        "agents": agents,
        "mode": "intercept",
        "evil_rules": evil_rules,
    }

LEVELS += [
    # 69: Intercept intro — evil walks right, hero comes from above
    # P is behind where evil started — evil bounces back into it
    # Evil: R=Pass. Hero: R=Pass, bounce evil backward.
    intercept_level(
        cells=[
            (-1, 0, P),  # dissolve BEHIND evil's start
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, R), (4, 0, R), (5, 0, R),
            (3, -1, R), (3, -2, R),  # hero's approach path from above
        ],
        hero_def={"x": 3, "y": -3, "dx": 0, "dy": 1},  # hero enters from above
        evil_defs=[{"x": -2, "y": 0, "dx": 1, "dy": 0}],  # evil from far left
        evil_rules={R: VERB_PASS, Y: VERB_PASS, B: VERB_PASS},
    ),

    # 70: Evil turns right at Y, hero intercepts on the vertical path
    # Evil goes right, turns down at Y, walks into P at bottom
    # Hero enters from the side to bounce evil into the P
    intercept_level(
        cells=[
            (0, 0, R), (1, 0, R), (2, 0, Y),
            (2, 1, R), (2, 2, R), (2, 3, R), (2, 4, P),  # evil's turn-down path
            (4, 2, R), (3, 2, R),  # hero's approach from right
        ],
        hero_def={"x": 5, "y": 2, "dx": -1, "dy": 0},  # hero from right
        evil_defs=[{"x": -1, "y": 0, "dx": 1, "dy": 0}],
        evil_rules={R: VERB_PASS, Y: VERB_TURN_RIGHT, B: VERB_PASS},
    ),

    # 71: Two evil agents approach from opposite ends, hero drops from above
    # P cells at far ends — evil bounces off hero and walks back into P
    intercept_level(
        cells=[
            (-1, 0, P),  # left dissolve
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, R),
            (4, 0, R), (5, 0, R), (6, 0, R), (7, 0, R),
            (8, 0, P),  # right dissolve
            (3, -1, R), (3, -2, R), (4, -1, R), (4, -2, R),  # hero path from above
        ],
        hero_def={"x": 3, "y": -3, "dx": 0, "dy": 1},
        evil_defs=[
            {"x": -2, "y": 0, "dx": 1, "dy": 0},
            {"x": 9, "y": 0, "dx": -1, "dy": 0},
        ],
        evil_rules={R: VERB_PASS, Y: VERB_PASS, B: VERB_PASS},
    ),
]

# ── Phase 17: place agent mode — find the right starting position ──

def place_agent_level(cells, fixed_rules, max_agents=1):
    return {
        "cells": cells,
        "agents": [],  # player places agents
        "mode": "place_agent",
        "fixed_rules": fixed_rules,
        "max_agents": max_agents,
    }

LEVELS += [
    # 72: Simple L-shape — only one entry point clears it
    # R=Pass, Y=TurnRight, B=Dissolve. Enter from top-left going right.
    place_agent_level(
        cells=[
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, Y),
            (3, 1, R), (3, 2, R), (3, 3, B),
        ],
        fixed_rules={R: VERB_PASS, Y: VERB_TURN_RIGHT, B: VERB_DISSOLVE},
    ),

    # 73: T-shape — must enter from the right arm to clear everything
    # R=Pass, Y=TurnLeft, B=Dissolve
    place_agent_level(
        cells=[
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, R), (4, 0, R),
            (2, 1, Y), (2, 2, R), (2, 3, B),
        ],
        fixed_rules={R: VERB_PASS, Y: VERB_TURN_LEFT, B: VERB_DISSOLVE},
    ),

    # 74: Spiral — only one entry point navigates the whole spiral
    # R=Pass, Y=TurnRight, B=Dissolve
    place_agent_level(
        cells=[
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, Y),
            (3, 1, R), (3, 2, R), (3, 3, Y),
            (2, 3, R), (1, 3, R), (0, 3, Y),
            (0, 2, R), (0, 1, B),
        ],
        fixed_rules={R: VERB_PASS, Y: VERB_TURN_RIGHT, B: VERB_DISSOLVE},
    ),

    # 75: Place 2 agents — both needed to clear a forked path
    place_agent_level(
        cells=[
            (0, 0, R), (1, 0, R), (2, 0, R), (3, 0, B),
            (0, 2, R), (1, 2, R), (2, 2, R), (3, 2, B),
        ],
        fixed_rules={R: VERB_PASS, B: VERB_DISSOLVE, Y: VERB_PASS},
        max_agents=2,
    ),
]

# ── Phase 18: binary tree levels ──

LEVELS += [
    # 77: Tree intro — symmetric depth 1 (easy, Y=Dissolve, rest don't matter)
    {"cells": [(0,0,W),(0,1,W),(0,2,W),(0,3,W),(0,4,G),(0,5,(C,O)),
               (1,5,W),(2,5,W),(3,5,W),(4,5,Y),
               (-1,5,W),(-2,5,W),(-3,5,W),(-4,5,Y)],
     "start": (0,-1), "dir": (0,1)},

    # 78: Asymmetric tree — right arm has a turn (R=TR), left is straight (B=Pass). 1 solution.
    {"cells": [(0,0,W),(0,1,W),(0,2,G),(0,3,(C,O)),
               (1,3,W),(2,3,W),(3,3,R),(3,4,W),(3,5,Y),
               (-1,3,W),(-2,3,B),(-3,3,W),(-4,3,Y)],
     "start": (0,-1), "dir": (0,1)},

    # 79: Expire tree — one child dissolves immediately, parent navigates L-path. 1 solution.
    {"cells": [(0,0,W),(0,1,W),(0,2,G),(0,3,(C,O)),
               (1,3,Y),
               (-1,3,W),(-2,3,R),(-2,2,W),(-2,1,B),(-2,0,Y)],
     "start": (0,-1), "dir": (0,1)},

    # 80: Symmetric depth 2 — 4 branches, the spectacle level (pk=4)
    {"cells": [(0,0,W),(0,1,W),(0,2,W),(0,3,G),(0,4,(C,O)),
               (1,4,W),(2,4,W),(3,4,G),(4,4,(C,O)),
               (4,3,W),(4,2,W),(4,1,Y),(4,5,W),(4,6,W),(4,7,Y),
               (-1,4,W),(-2,4,W),(-3,4,G),(-4,4,(C,O)),
               (-4,5,W),(-4,6,W),(-4,7,Y),(-4,3,W),(-4,2,W),(-4,1,Y)],
     "start": (0,-1), "dir": (0,1)},
]

# ── Phase 18: devilish levels — unique solutions, non-obvious answers ──

def tape_level_d(colors, disabled=None):
    """1D tape with optional disabled verbs."""
    level = {
        "cells": [(i, 0, c) for i, c in enumerate(colors)],
        "start": (-1, 0),
        "dir": (1, 0),
    }
    if disabled:
        level["disabled_verbs"] = disabled
    return level

LEVELS += [
    # Devilish 1: "The Trap" — looks like pass-through but needs replicate + turn
    # R=Replicate, Y=Dissolve, B=TurnRight (1 solution)
    {"cells": [(0,0,W),(1,0,R),(2,0,(B,W)),(3,0,W),(4,0,Y),
               (2,1,W),(2,2,Y)],
     "start": (-1,0), "dir": (1,0)},

    # Devilish 2: "T-Junction" — same mechanic, different shape
    {"cells": [(0,0,R),(1,0,(B,W)),(2,0,W),(3,0,Y),
               (1,1,W),(1,2,Y)],
     "start": (-1,0), "dir": (1,0)},

    # Devilish 3: "Spiral" — clockwise spiral, R=Pass B=TurnRight Y=Dissolve
    {"cells": [(0,0,R),(1,0,R),(2,0,R),(3,0,B),
               (3,1,R),(3,2,R),(3,3,B),
               (2,3,R),(1,3,R),(0,3,B),
               (0,2,R),(0,1,Y)],
     "start": (-1,0), "dir": (1,0)},

    # Devilish 4: "Counter-Replicate" — must replicate AND dissolve extras
    # R=Replicate, Y=Dissolve, B=Dissolve (1 solution, pk=3)
    tape_level_d([R, R, Y, R, R, Y, B]),
]

# ── Phase 19: No-Pass levels — Pass verb disabled, every color does something ──

LEVELS += [
    # No-Pass intro — short tape, R=Replicate Y=Dissolve B=Dissolve
    tape_level_d([R, R, Y, Y, B],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS], B: [VERB_PASS]}),

    # No-Pass with double replicate — R=Rep Y=Rep B=Dissolve (pk=4)
    tape_level_d([R, Y, B, B, B, B],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS], B: [VERB_PASS]}),

    # No-Pass longer — R=Rep Y=Dissolve B=Dissolve (pk=4)
    tape_level_d([R, R, R, Y, Y, Y, B],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS], B: [VERB_PASS]}),

    # No-Pass spectacle — big replicate chain (pk=4)
    tape_level_d([R, R, R, Y, B, Y, B],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS], B: [VERB_PASS]}),

    # Mixed restriction — R,Y no pass, B free. R=Rep Y=Dissolve B=Pass
    tape_level_d([R, Y, B, B, Y],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS]}),

    # Mixed restriction longer
    tape_level_d([R, R, Y, Y, B, Y],
                 disabled={R: [VERB_PASS], Y: [VERB_PASS]}),
]

# ── campaign order: curated selection from all levels ──
# The full LEVELS list is the "songbook." CAMPAIGN is the album.
# Level select shows campaign order. Editor still accesses all levels.

# Phase 20: 4-color levels (Pink as 4th assignable)
K = WALL_PINK
LEVELS += [
    # 4-color intro: R=Replicate Y=Dissolve B=Pass K=Dissolve (1 solution)
    {"cells": [(i,0,c) for i,c in enumerate([R,Y,B,R,K,Y])],
     "start": (-1,0), "dir": (1,0)},

    # 4-color with double rep: R=Replicate Y=Dissolve B=Replicate K=Pass (1 sol, pk=3)
    {"cells": [(i,0,c) for i,c in enumerate([R,Y,B,B,K,B])],
     "start": (-1,0), "dir": (1,0)},

    # 4-color longer: R=Replicate Y=Replicate B=Dissolve K=Pass (1 sol, pk=3)
    {"cells": [(i,0,c) for i,c in enumerate([R,Y,B,K,R,B])],
     "start": (-1,0), "dir": (1,0)},

    # 4-color hard: R=Pass Y=Replicate B=Dissolve K=Pass (1 sol)
    {"cells": [(i,0,c) for i,c in enumerate([R,Y,B,K,Y,B])],
     "start": (-1,0), "dir": (1,0)},
]

# Phase 21: Teleport levels
TA, TB = FIXED_TELEPORT_A, FIXED_TELEPORT_B
LEVELS += [
    # Teleport intro: walk through R, teleport, walk through B, dissolve at Y
    {"cells": [(0,0,R),(1,0,R),(2,0,TA),
               (6,0,TB),(7,0,B),(8,0,B),(9,0,Y)],
     "start": (-1,0), "dir": (1,0)},

    # Teleport + branch: replicate, child teleports, parent continues locally
    {"cells": [(0,0,W),(1,0,G),(2,0,(TA,W)),
               (3,0,W),(4,0,Y),
               (8,2,TB),(9,2,W),(10,2,Y)],
     "start": (-1,0), "dir": (1,0)},

    # Teleport + 4 colors: R path → teleport → K path → dissolve
    {"cells": [(0,0,R),(1,0,B),(2,0,TA),
               (6,0,TB),(7,0,K),(8,0,B),(9,0,Y)],
     "start": (-1,0), "dir": (1,0)},
]

# ── Phase 22: Mandala — showcase level, 4 agents from center ──

LEVELS += [
    # 4-ring cross mandala: RBRY pattern. Unique solution. 4 agents march outward.
    {"cells": [(1,0,R),(-1,0,R),(0,1,R),(0,-1,R),
               (2,0,B),(-2,0,B),(0,2,B),(0,-2,B),
               (3,0,R),(-3,0,R),(0,3,R),(0,-3,R),
               (4,0,Y),(-4,0,Y),(0,4,Y),(0,-4,Y)],
     "agents": [{"x":0,"y":0,"dx":1,"dy":0,"team":0},
                {"x":0,"y":0,"dx":-1,"dy":0,"team":1},
                {"x":0,"y":0,"dx":0,"dy":1,"team":2},
                {"x":0,"y":0,"dx":0,"dy":-1,"team":3}]},

    # 5-ring cross mandala: RBRBY. 2 solutions incl replicate variant (pk=8!)
    {"cells": [(1,0,R),(-1,0,R),(0,1,R),(0,-1,R),
               (2,0,B),(-2,0,B),(0,2,B),(0,-2,B),
               (3,0,R),(-3,0,R),(0,3,R),(0,-3,R),
               (4,0,B),(-4,0,B),(0,4,B),(0,-4,B),
               (5,0,Y),(-5,0,Y),(0,5,Y),(0,-5,Y)],
     "agents": [{"x":0,"y":0,"dx":1,"dy":0,"team":0},
                {"x":0,"y":0,"dx":-1,"dy":0,"team":1},
                {"x":0,"y":0,"dx":0,"dy":1,"team":2},
                {"x":0,"y":0,"dx":0,"dy":-1,"team":3}]},
]

# ── Phase 23: The Replic8 — signature level shaped like an 8 ──

LEVELS.append(
    {"cells": [(1,0,Y),(2,0,W),(3,0,W),(4,0,W),(5,0,W),(6,0,Y),
               (0,1,Y),(1,1,B),(6,1,B),(7,1,Y),
               (0,2,W),(7,2,W),
               (0,3,W),(7,3,W),
               (0,4,Y),(1,4,B),(6,4,B),(7,4,Y),
               (1,5,Y),(2,5,B),(5,5,B),(6,5,Y),
               (2,6,Y),(3,6,B),(4,6,P),(5,6,Y),
               (3,7,(R,Y)),(4,7,Y),
               (2,8,P),(4,8,B),(5,8,Y),
               (1,9,Y),(2,9,B),(5,9,B),(6,9,Y),
               (0,10,Y),(1,10,B),(6,10,B),(7,10,Y),
               (0,11,W),(7,11,W),
               (0,12,W),(7,12,W),
               (0,13,Y),(1,13,B),(6,13,B),(7,13,Y),
               (1,14,Y),(2,14,W),(3,14,W),(4,14,W),(5,14,W),(6,14,Y)],
     "start": (3,8), "dir": (0,-1)},
)

# ── Phase: Cross-junction levels ──
# Hand-designed 4-color cross with R=Pass, Y=TurnLeft, B=TurnRight, T=Replicate

# User's hand-designed cross-junction (48 cells, 1 solution, pk=3)
# R=Pass, Y=TurnLeft, B=TurnRight, T=Replicate
LEVELS += (
    {"cells": [(3,0,B),(4,0,R),(5,0,R),(6,0,B),(3,1,R),(6,1,R),(3,2,R),(6,2,P),
               (0,3,Y),(1,3,R),(2,3,R),(3,3,(WALL_TEAL,B)),(4,3,(Y,B)),(5,3,R),(6,3,R),(7,3,R),(8,3,R),(9,3,B),
               (0,4,R),(3,4,P),(4,4,WALL_TEAL),(5,4,P),(6,4,P),(9,4,R),
               (0,5,R),(3,5,R),(5,5,R),(6,5,R),(9,5,R),
               (0,6,Y),(1,6,R),(2,6,R),(3,6,Y),(4,6,B),(5,6,Y),(6,6,(Y,B)),(7,6,WALL_TEAL),(8,6,R),(9,6,B),
               (3,7,B),(4,7,Y),(6,7,R),(3,8,R),(6,8,R),(3,9,B),(4,9,R),(5,9,R),(6,9,B)],
     "agents": [{"x": 4, "y": 5, "dx": 0, "dy": -1, "team": 0}]},
)

# Expanded cross-junction reward level (64 cells, 4 agents, pk=8, 2 solutions)
# arm=4, depth=1: 4 agents from center, each splits into 2 sub-arms
def _build_cross_reward():
    cells = {}
    def add(x, y, c):
        if (x, y) not in cells: cells[(x, y)] = c
    def branching_arm(ox, oy, dx, dy, arm_len, depth):
        x, y = ox, oy
        for i in range(arm_len):
            add(x, y, R); x += dx; y += dy
        if depth <= 0:
            add(x, y, P); return
        add(x, y, WALL_TEAL)
        fx, fy = x + dx, y + dy
        add(fx, fy, (Y, B))
        ldx, ldy = dy, -dx   # turn left
        rdx, rdy = -dy, dx   # turn right
        branching_arm(fx + ldx, fy + ldy, ldx, ldy, arm_len, depth - 1)
        branching_arm(fx + rdx, fy + rdy, rdx, rdy, arm_len, depth - 1)
    for sx, sy, dx, dy in [(0,-1,0,-1),(0,1,0,1),(1,0,1,0),(-1,0,-1,0)]:
        branching_arm(sx, sy, dx, dy, 4, 1)
    return {
        "cells": [(x, y, c) for (x, y), c in cells.items()],
        "agents": [
            {"x": 0, "y": 0, "dx": 0, "dy": -1, "team": 0},
            {"x": 0, "y": 0, "dx": 0, "dy": 1, "team": 0},
            {"x": 0, "y": 0, "dx": 1, "dy": 0, "team": 0},
            {"x": 0, "y": 0, "dx": -1, "dy": 0, "team": 0},
        ],
    }

LEVELS += (_build_cross_reward(),)

# ── Phase: Dense swap levels ──
# Single agent walks top row, replicates at sandwich, child drops to bottom row.
# R=Pass, Y=TurnLeft, B=TurnRight, T=Replicate. All unique solutions.

# ── Phase: Ping-Pong — introduces reverse (bounce) cells ──
# Agent bounces up/down columns of T(pass)/Rev(reverse), replicates to side columns.
# R=Replicate, Y=TurnLeft, B=TurnRight, T=Pass. 1 unique solution.
_RV = FIXED_REVERSE
LEVELS += (
    {"cells": [(0,0,P),(7,0,P),(14,0,P),
               (0,1,WALL_TEAL),(7,1,WALL_TEAL),(14,1,WALL_TEAL),
               (0,2,_RV),(7,2,_RV),(14,2,_RV),
               (0,3,WALL_TEAL),(7,3,WALL_TEAL),(14,3,WALL_TEAL),
               (0,4,_RV),(7,4,_RV),(14,4,_RV),
               (0,5,WALL_TEAL),(7,5,WALL_TEAL),(14,5,WALL_TEAL),
               (0,6,_RV),(7,6,_RV),(14,6,_RV),
               (0,7,Y),(7,7,(B,Y)),(14,7,B),
               (0,8,_RV),(7,8,WALL_TEAL),(14,8,_RV),
               (0,9,WALL_TEAL),(7,9,R),(14,9,WALL_TEAL),
               (0,10,_RV),(7,10,WALL_TEAL),(14,10,_RV),
               (0,11,WALL_TEAL),(7,11,R),(14,11,WALL_TEAL),
               (0,12,_RV),(14,12,_RV),
               (0,13,WALL_TEAL),(7,13,_RV),(14,13,WALL_TEAL),
               (0,14,_RV),(7,14,WALL_TEAL),(14,14,_RV),
               (7,15,_RV),(7,16,WALL_TEAL),(7,17,_RV)],
     "agents": [{"x": 7, "y": 12, "dx": 0, "dy": -1, "team": 0}]},
)

def _dense_swap(top_pre, top_post, bot_len, gap):
    cells = []; seen = set()
    def add(x,y,c):
        if (x,y) not in seen: cells.append((x,y,c)); seen.add((x,y))
    for i in range(top_pre): add(i, 0, R)
    sx = top_pre
    add(sx, 0, WALL_TEAL); add(sx+1, 0, (B, R))
    for i in range(top_post): add(sx+2+i, 0, R)
    add(sx+2+top_post, 0, FIXED_DISSOLVE)
    bot_y = gap + 1
    add(sx+1, bot_y, Y)
    for i in range(bot_len): add(sx+2+i, bot_y, R)
    add(sx+2+bot_len, bot_y, FIXED_DISSOLVE)
    return {"cells": cells, "start": (-1, 0), "dir": (1, 0)}

LEVELS += (
    # Compact swap: gap=1, tight
    _dense_swap(top_pre=2, top_post=3, bot_len=4, gap=1),
    # Wider swap: gap=2, more dramatic drop
    _dense_swap(top_pre=3, top_post=4, bot_len=5, gap=2),
    # Big swap: gap=3, longer paths
    _dense_swap(top_pre=4, top_post=4, bot_len=6, gap=3),
)

# ── Phase: "Surrounded" — 5-color aha moment ──
# R=Pass, Y=TurnLeft, B=TurnLeft(!), Pk=Replicate, T=Dissolve
# The misdirection: Y and B are BOTH TurnLeft. Teal dissolves instead of replicates.
# Pink (appears once as sandwich) is the actual Replicate.
LEVELS += (
    {"cells": [(0,0,WALL_TEAL),(1,0,R),(2,0,R),(3,0,R),(4,0,R),(5,0,R),(6,0,R),(7,0,B),
               (0,1,B),(1,1,(WALL_PINK,Y)),(2,1,R),(3,1,R),(4,1,R),(5,1,R),(6,1,B),(7,1,R),
               (0,2,R),(1,2,R),(2,2,B),(3,2,R),(4,2,Y),(5,2,WALL_TEAL),(6,2,R),(7,2,R),
               (0,3,R),(1,3,R),(2,3,R),(5,3,R),(6,3,R),(7,3,R),
               (0,4,R),(1,4,B),(2,4,R),(3,4,R),(4,4,R),(5,4,Y),(6,4,R),(7,4,R),
               (0,5,R),(2,5,B),(3,5,R),(4,5,R),(5,5,R),(6,5,Y),(7,5,R),
               (0,6,Y),(1,6,R),(2,6,R),(3,6,R),(4,6,R),(5,6,R),(6,6,R),(7,6,Y)],
     "agents": [{"x": 4, "y": 3, "dx": 0, "dy": -1, "team": 0}]},
)

# ── Phase: Dual-constraint — two separate shapes, shared rules ──
# Each shape alone has multiple solutions. Together: 1 unique solution.
# The player must find rules that work for BOTH paths simultaneously.

# Hand-designed dual-constraint (from user): R=Rp Y=TL B=TR T=D pk=5
LEVELS += (
    {"cells": [(3,0,R),(4,0,B),(4,1,Y),(9,1,R),(10,1,B),(10,2,Y),(16,0,WALL_TEAL),(17,0,B),(18,0,B),(16,1,WALL_TEAL),(17,2,Y),(18,2,Y),(21,2,P),
               (0,11,B),(3,11,R),(4,11,B),(9,11,B),(10,11,B),(16,11,WALL_TEAL),(21,11,P),
               (0,12,B),(4,12,B),(9,12,Y),(10,12,Y)],
     "agents": [{"x":2,"y":0,"dx":1,"dy":0,"team":0},
                {"x":2,"y":11,"dx":1,"dy":0,"team":0}]},
)

# Diagonal scatter (from user): R=TL Y=D B=TR pk=5
# Agent enters, hits triple-green sandwich, spawns 5 agents that fan out diagonally
LEVELS += (
    {"cells": [(3,0,B),(5,0,Y),(2,3,B),(4,3,Y),(2,6,B),(4,6,Y),
               (0,9,(G,G,G)),(1,9,(G,G,G)),(2,9,(R,B,R)),(3,9,(B,R,B)),(7,9,Y),
               (2,12,R),(4,12,Y),(3,15,R),(5,15,Y),(3,18,R),(5,18,Y)],
     "agents": [{"x":-1,"y":9,"dx":1,"dy":0,"team":0}]},
)

# Spiral reverse (from user): R=TL Y=Rp B=TR T=P pk=2
LEVELS += (
    {"cells": [(0,0,P),(1,0,P),(2,0,WALL_TEAL),(3,0,WALL_TEAL),(4,0,WALL_TEAL),(5,0,WALL_TEAL),(6,0,WALL_TEAL),(7,0,R),
               (0,1,B),(1,1,WALL_TEAL),(7,1,R),
               (0,2,B),(1,2,WALL_TEAL),(7,2,R),
               (0,3,B),(1,3,WALL_TEAL),(7,3,R),
               (0,4,B),(1,4,B),(3,4,WALL_TEAL),(4,4,WALL_TEAL),(5,4,WALL_TEAL),(6,4,FIXED_REVERSE),(7,4,R),
               (0,5,B),(1,5,WALL_TEAL),(3,5,WALL_TEAL),(4,5,R),
               (0,6,B),(1,6,WALL_TEAL),(4,6,R),
               (0,7,B),(1,7,WALL_TEAL),(5,7,WALL_TEAL),(6,7,R),
               (0,8,B),(1,8,WALL_TEAL),(6,8,R),
               (0,9,B),(1,9,(Y,B))],
     "agents": [{"x":1,"y":10,"dx":0,"dy":-1,"team":0}]},
)

# New dual-path (from user): R=TL Y=D B=TL Pk=Rp pk=9
# Horizontal sandwich row + vertical alternating column, Y dissolve triangle
LEVELS += (
    {"cells": [(5,0,2),(6,0,2),(7,1,2),(10,1,2),(8,2,2),(9,2,2),(10,2,2),
               (0,5,2),(5,5,(18,1)),(6,5,(18,1)),(7,5,(18,1)),(8,5,(18,1)),(9,5,(18,1)),(10,5,(1,3)),
               (10,6,18),(0,7,2),(10,7,3),(10,8,18),(0,9,2),(10,9,3),(10,10,18),
               (0,11,2),(10,11,3),(10,12,18),(0,13,2),(10,13,3),(10,14,18)],
     "agents": [{"x":4,"y":5,"dx":1,"dy":0,"team":0},
                {"x":10,"y":15,"dx":0,"dy":-1,"team":1}]},
)
_DUAL_PATH_NEW = len(LEVELS) - 1

# Spiral generator (from user): R=TR Y=TR B=TR Pk=Rp pk=10 t=78
# Consecutive replicates fan out into diagonal staircase pattern
LEVELS += (
    {"cells": [(9,0,6),(9,1,6),(9,2,6),(9,3,6),(9,4,6),(9,5,6),(9,6,6),(9,7,6),(9,8,6),(9,9,6),
               (0,10,18),(1,10,18),(2,10,18),(3,10,18),(4,10,18),(5,10,18),(6,10,18),(7,10,18),(8,10,18),
               (10,10,1),(11,10,3),(12,10,2),(13,10,1),(14,10,3),(15,10,2),(16,10,1),(17,10,3),(18,10,2),(19,10,1),
               (9,11,1),(10,11,1),(9,12,3),(11,12,3),(9,13,2),(12,13,2),(9,14,1),(13,14,1),
               (9,15,3),(14,15,3),(9,16,2),(15,16,2),(9,17,1),(16,17,1),(9,18,3),(17,18,3),(9,19,2),(18,19,2),(9,20,1),(19,20,1)],
     "agents": [{"x":-1,"y":10,"dx":1,"dy":0,"team":0}]},
)
_SPIRAL_GEN = len(LEVELS) - 1

# Layered factory (from user): R=TR Y=D B=Rp T=TL pk=12 t=46
# Sandwich row produces agents that drop through B columns into Y dissolve field
LEVELS += (
    {"cells": [(0,0,1),(5,0,(3,1)),(7,0,(3,1)),(9,0,(3,1)),(11,0,(3,1)),(13,0,(3,1)),(15,0,(3,1)),(17,0,1),
               (5,1,3),(7,1,3),(9,1,3),(11,1,3),(13,1,3),(15,1,3),(17,1,3),
               (5,2,3),(7,2,3),(9,2,3),(11,2,3),(13,2,3),(15,2,3),
               (0,4,8),(5,4,2),(6,4,2),(7,4,2),(8,4,2),(9,4,2),(10,4,2),(11,4,2),(12,4,2),(13,4,2),(14,4,2),(15,4,2),(16,4,2),(17,4,2),
               (5,5,2),(6,5,2),(7,5,2),(8,5,2),(9,5,2),(10,5,2),(11,5,2),(12,5,2),(13,5,2),(14,5,2),(15,5,2),(16,5,2),(17,5,2),
               (6,8,3),(8,8,3),(10,8,3),(12,8,3),(14,8,3),(16,8,3),
               (5,9,19),(6,9,19),(7,9,19),(8,9,19),(9,9,19),(10,9,19),(11,9,19),(12,9,19),(13,9,19),(14,9,19),(15,9,19),(16,9,19)],
     "agents": [{"x":-4,"y":4,"dx":1,"dy":0,"team":0}]},
)
_LAYERED_FACTORY = len(LEVELS) - 1

# 3-agent frame (from user): R=TL Y=TR B=Rp pk=16 — room escape / trust the timeline
LEVELS += (
    {"cells": [(1,0,6),(2,0,6),(3,0,6),(4,0,6),(5,0,6),(6,0,6),(7,0,6),(8,0,6),(9,0,6),
               (1,1,(3,2)),(2,1,(3,1)),(3,1,(3,1)),(4,1,(3,1)),(5,1,(3,1)),(6,1,(3,1)),(7,1,(3,1)),(8,1,(3,1)),(9,1,(3,1)),(10,1,(3,2)),(11,1,6),
               (10,2,(3,1)),(11,2,6),(10,3,1),(11,3,6),
               (0,4,6),(1,4,2),(4,4,3),(5,4,1),(9,4,3),(10,4,2),(11,4,6),
               (0,5,6),(1,5,1),(10,5,(3,1)),(11,5,6),
               (0,6,6),(1,6,(3,1)),(10,6,(3,1)),(11,6,6),
               (0,7,6),(1,7,(3,1)),(10,7,(3,1)),(11,7,6),
               (0,8,6),(1,8,(3,1)),(10,8,(3,1)),(11,8,6),
               (0,9,6),(1,9,(3,1)),(10,9,(3,1)),(11,9,6),
               (0,10,6),(1,10,(3,1)),(10,10,(3,1)),(11,10,6),
               (0,11,6),(1,11,(3,2)),(2,11,(3,1)),(3,11,(3,1)),(4,11,(3,1)),(5,11,(3,1)),(6,11,(3,1)),(7,11,(3,1)),(8,11,(3,1)),(10,11,(3,1)),(11,11,6),
               (2,12,6),(3,12,6),(4,12,6),(5,12,6),(6,12,6),(7,12,6),(8,12,6),(10,12,6)],
     "agents": [{"x":5,"y":5,"dx":0,"dy":-1,"team":0},
                {"x":-12,"y":4,"dx":1,"dy":0,"team":1},
                {"x":9,"y":11,"dx":-1,"dy":0,"team":2}]},
)
_3AGENT_FRAME = len(LEVELS) - 1

# ── Pingpong.txt levels L12-L27 ──

# L12: Triple sandwich intro (39c, 1sol, R=P Y=TL B=TR Pk=D T=TL)
LEVELS += ({"cells": [(0,0,1),(8,0,1),(0,1,3),(1,1,1),(2,1,3),(6,1,3),(7,1,1),(8,1,3),(0,2,3),(1,2,3),(7,2,3),(8,2,3),(0,3,1),(1,3,3),(2,3,(3,1,19)),(6,3,1),(7,3,3),(8,3,3),(0,6,1),(1,6,(2,1)),(2,6,2),(0,7,3),(1,7,3),(2,7,1),(6,7,1),(7,7,3),(8,7,3),(0,8,3),(1,8,3),(7,8,3),(8,8,3),(0,9,3),(1,9,1),(2,9,3),(6,9,3),(7,9,1),(8,9,3),(0,10,1),(8,10,1)], "agents": [{"x":3,"y":3,"dx":-1,"dy":0,"team":0}]},)
_PP_L12 = len(LEVELS) - 1

# L13: Large level (81c, 1sol)
LEVELS += ({"cells": [(10,0,19),(11,0,19),(12,0,19),(13,0,19),(14,0,19),(15,0,19),(16,0,19),(17,0,19),(0,2,3),(1,2,3),(2,2,3),(3,2,3),(5,2,18),(6,2,18),(7,2,18),(8,2,18),(10,2,1),(11,2,1),(12,2,1),(13,2,1),(14,2,1),(15,2,1),(16,2,1),(17,2,1),(0,5,3),(1,5,3),(2,5,3),(3,5,3),(5,5,1),(9,5,1),(13,5,1),(17,5,1),(4,6,18),(5,6,1),(6,6,18),(7,6,3),(8,6,18),(9,6,1),(10,6,18),(11,6,3),(12,6,18),(13,6,1),(14,6,18),(15,6,3),(16,6,18),(17,6,1),(18,6,18),(19,6,3),(21,6,6),(0,7,1),(1,7,1),(2,7,1),(3,7,1),(7,7,3),(11,7,3),(15,7,3),(19,7,3),(0,10,1),(1,10,1),(2,10,1),(3,10,1),(5,10,18),(6,10,18),(7,10,18),(8,10,18),(10,10,3),(11,10,3),(12,10,3),(13,10,3),(14,10,3),(15,10,3),(16,10,3),(17,10,3),(10,12,19),(11,12,19),(12,12,19),(13,12,19),(14,12,19),(15,12,19),(16,12,19),(17,12,19)], "agents": [{"x":2,"y":6,"dx":1,"dy":0,"team":0}]},)
_PP_L13 = len(LEVELS) - 1

# L14: Dual-agent (24c, 2ag)
LEVELS += ({"cells": [(0,0,6),(3,0,(18,19)),(6,0,6),(11,0,6),(14,0,(18,19)),(17,0,6),(3,1,1),(14,1,1),(9,3,19),(10,3,2),(9,4,18),(13,4,1),(14,4,(18,19)),(3,5,(18,19)),(9,5,1),(10,5,2),(3,8,1),(14,8,1),(0,9,6),(3,9,(18,19)),(6,9,6),(11,9,6),(14,9,(18,19)),(17,9,6)], "agents": [{"x":8,"y":4,"dx":1,"dy":0,"team":0},{"x":7,"y":4,"dx":1,"dy":0,"team":1}]},)
_PP_L14 = len(LEVELS) - 1

# L15: Compact dual-agent (15c, 2ag)
LEVELS += ({"cells": [(4,0,19),(5,0,(1,18)),(6,0,19),(5,1,2),(0,3,19),(2,3,2),(5,3,(18,1)),(8,3,2),(10,3,19),(5,5,2),(4,6,18),(5,6,(1,18)),(6,6,1),(4,7,19),(6,7,19)], "agents": [{"x":1,"y":3,"dx":1,"dy":0,"team":0},{"x":9,"y":3,"dx":-1,"dy":0,"team":1}]},)
_PP_L15 = len(LEVELS) - 1

# L16: 4-agent (19c, 4ag)
LEVELS += ({"cells": [(5,0,2),(10,0,2),(0,1,6),(2,1,1),(3,1,2),(4,1,3),(5,1,3),(6,1,1),(10,1,3),(11,1,1),(4,2,1),(0,3,6),(3,3,2),(4,3,3),(4,4,1),(0,5,6),(3,5,2),(4,5,3),(4,6,6)], "agents": [{"x":1,"y":1,"dx":1,"dy":0,"team":0},{"x":12,"y":1,"dx":-1,"dy":0,"team":1},{"x":18,"y":3,"dx":-1,"dy":0,"team":2},{"x":18,"y":5,"dx":-1,"dy":0,"team":3}]},)
_PP_L16 = len(LEVELS) - 1

# L17: Large scenic (55c, 1ag, uses teleport)
LEVELS += ({"cells": [(9,0,6),(10,0,1),(16,0,1),(14,1,1),(15,1,1),(11,2,2),(14,2,2),(8,3,19),(9,3,16),(12,3,1),(13,3,1),(14,3,2),(12,4,2),(13,4,2),(11,5,2),(14,5,2),(21,5,6),(28,5,2),(10,6,1),(15,6,1),(22,6,2),(27,6,2),(9,7,1),(16,7,1),(23,7,2),(26,7,2),(24,8,2),(25,8,2),(20,9,17),(21,9,19),(22,9,20),(25,9,2),(24,10,2),(26,10,2),(0,11,6),(1,11,3),(7,11,3),(23,11,2),(27,11,2),(2,12,3),(6,12,3),(22,12,2),(28,12,2),(3,13,3),(5,13,3),(0,14,21),(4,14,3),(3,15,3),(4,15,3),(2,16,3),(5,16,3),(1,17,3),(6,17,3),(0,18,3),(7,18,3)], "agents": [{"x":4,"y":3,"dx":1,"dy":0,"team":0}]},)
_PP_L17 = len(LEVELS) - 1

# L18: Dual-agent complex (41c, 2ag, 1sol)
LEVELS += ({"cells": [(0,0,3),(12,0,19),(1,1,3),(12,1,19),(2,2,1),(3,2,1),(4,2,1),(8,2,1),(10,2,1),(11,2,1),(4,3,1),(8,3,1),(6,4,3),(7,4,3),(8,4,18),(4,5,19),(7,5,1),(8,5,1),(2,6,19),(3,6,19),(4,6,19),(6,6,1),(6,7,1),(7,7,1),(3,8,1),(4,8,1),(5,8,18),(6,8,3),(7,8,3),(8,8,1),(9,8,18),(3,9,1),(4,9,1),(8,9,(18,1)),(9,9,3),(10,9,1),(11,9,1),(1,10,3),(8,10,3),(0,11,3),(9,11,3)], "agents": [{"x":5,"y":6,"dx":1,"dy":0,"team":0},{"x":10,"y":8,"dx":-1,"dy":0,"team":1}]},)
_PP_L18 = len(LEVELS) - 1

# L19: Dual-agent with one-way gates (34c, 2ag)
LEVELS += ({"cells": [(0,0,19),(1,0,2),(2,0,18),(3,0,2),(4,0,18),(5,0,2),(6,0,18),(7,0,2),(1,1,1),(3,1,1),(5,1,1),(7,1,1),(1,2,1),(2,2,11),(3,2,1),(4,2,11),(5,2,1),(6,2,11),(7,2,3),(9,2,3),(1,3,19),(2,3,19),(3,3,19),(4,3,19),(5,3,19),(6,3,19),(1,4,19),(2,4,3),(3,4,18),(4,4,3),(5,4,18),(6,4,3),(7,4,18),(9,4,3)], "agents": [{"x":0,"y":2,"dx":1,"dy":0,"team":0},{"x":8,"y":2,"dx":-1,"dy":0,"team":1}]},)
_PP_L19 = len(LEVELS) - 1

# L20: Single agent diamond (28c, 1sol)
LEVELS += ({"cells": [(0,0,18),(8,0,18),(9,0,19),(1,1,1),(7,1,1),(1,2,19),(2,2,19),(4,2,18),(6,2,18),(2,3,19),(3,3,1),(4,3,(2,1)),(5,3,1),(1,4,1),(3,4,(2,18)),(5,4,(2,18)),(9,4,1),(3,5,1),(4,5,(2,18)),(5,5,1),(2,6,18),(6,6,18),(1,7,1),(7,7,1),(0,8,18),(4,8,18),(7,8,19),(8,8,18)], "agents": [{"x":4,"y":4,"dx":0,"dy":-1,"team":0}]},)
_PP_L20 = len(LEVELS) - 1

# L21: 3-agent complex (57c, 3ag, 1sol, R=P Y=TL B=TR Pk=D)
LEVELS += ({"cells": [(1,0,2),(2,0,3),(3,0,18),(1,1,2),(2,1,3),(3,1,3),(4,1,2),(1,2,1),(4,2,1),(6,2,3),(7,2,1),(8,2,1),(9,2,3),(1,3,1),(4,3,1),(5,3,3),(6,3,2),(9,3,1),(1,4,1),(4,4,1),(5,4,1),(9,4,1),(1,5,2),(2,5,(1,3)),(3,5,3),(4,5,2),(5,5,1),(9,5,1),(2,6,(3,2)),(3,6,(3,2)),(5,6,1),(9,6,18),(1,7,3),(2,7,(1,2)),(3,7,2),(4,7,3),(5,7,3),(9,7,2),(1,8,1),(4,8,1),(9,8,1),(0,9,3),(1,9,2),(4,9,1),(9,9,1),(0,10,1),(4,10,1),(9,10,1),(0,11,3),(1,11,2),(3,11,18),(4,11,3),(9,11,1),(1,12,3),(2,12,1),(3,12,1),(9,12,1)], "agents": [{"x":1,"y":-1,"dx":0,"dy":1,"team":0},{"x":12,"y":12,"dx":-1,"dy":0,"team":1},{"x":9,"y":13,"dx":0,"dy":-1,"team":2}]},)
_PP_L21 = len(LEVELS) - 1

# L22: Sandwich grid (46c, 1ag, 1sol, R=TR B=Rp T=TL pk=10)
LEVELS += ({"cells": [(8,0,3),(1,1,19),(4,1,19),(5,1,3),(6,1,19),(7,1,3),(8,1,(1,19)),(9,1,3),(10,1,1),(11,1,3),(12,1,1),(15,1,1),(1,2,3),(4,2,3),(6,2,3),(10,2,3),(12,2,3),(15,2,3),(0,3,19),(1,3,(1,19)),(2,3,1),(3,3,19),(4,3,(1,19)),(5,3,(19,1)),(6,3,(1,19)),(7,3,1),(9,3,19),(10,3,(1,19)),(11,3,(1,19)),(12,3,(1,19)),(13,3,1),(14,3,19),(15,3,(1,19)),(16,3,1),(0,14,6),(2,14,6),(3,14,6),(5,14,6),(7,14,6),(9,14,6),(11,14,6),(13,14,6),(14,14,6),(16,14,6),(5,15,6),(11,15,6)], "agents": [{"x":8,"y":-1,"dx":0,"dy":1,"team":0}]},)
_PP_L22 = len(LEVELS) - 1

# L23: 5-color spiral frame (134c, 1ag, 1sol, R=Rp Y=TR B=P Pk=D T=TL)
LEVELS += ({"cells": [(0,0,19),(1,0,3),(2,0,3),(3,0,3),(4,0,3),(5,0,3),(6,0,3),(7,0,3),(8,0,3),(9,0,3),(10,0,3),(11,0,3),(12,0,3),(13,0,3),(14,0,3),(15,0,19),(0,1,3),(15,1,3),(0,2,3),(2,2,2),(3,2,(1,19,18)),(4,2,3),(5,2,3),(6,2,3),(7,2,3),(8,2,3),(9,2,3),(10,2,3),(11,2,3),(12,2,3),(13,2,(1,2)),(15,2,19),(0,3,3),(2,3,3),(3,3,3),(4,3,19),(11,3,3),(12,3,19),(13,3,3),(15,3,18),(0,4,3),(2,4,3),(4,4,3),(5,4,19),(10,4,3),(11,4,19),(13,4,3),(15,4,3),(0,5,3),(2,5,3),(5,5,3),(6,5,19),(9,5,3),(10,5,19),(13,5,3),(15,5,3),(0,6,3),(2,6,3),(6,6,3),(7,6,19),(8,6,3),(9,6,19),(13,6,3),(15,6,3),(0,7,3),(2,7,3),(7,7,19),(8,7,18),(13,7,3),(15,7,3),(0,8,3),(2,8,3),(6,8,19),(7,8,3),(8,8,3),(9,8,19),(13,8,3),(15,8,3),(0,9,3),(2,9,3),(5,9,19),(6,9,3),(9,9,3),(10,9,19),(13,9,3),(15,9,3),(0,10,3),(2,10,3),(4,10,19),(5,10,3),(10,10,3),(11,10,19),(13,10,3),(15,10,3),(0,11,3),(2,11,3),(3,11,19),(4,11,3),(11,11,3),(12,11,19),(13,11,3),(15,11,3),(0,12,3),(2,12,2),(3,12,3),(4,12,3),(5,12,3),(6,12,3),(7,12,3),(8,12,3),(9,12,3),(10,12,3),(11,12,3),(12,12,3),(13,12,2),(15,12,3),(0,13,3),(15,13,3),(0,14,19),(1,14,3),(2,14,3),(3,14,3),(4,14,3),(5,14,3),(6,14,3),(7,14,3),(8,14,3),(9,14,3),(10,14,3),(11,14,3),(12,14,3),(13,14,3),(14,14,3),(15,14,19)], "agents": [{"x":3,"y":1,"dx":0,"dy":1,"team":0}]},)
_PP_L23 = len(LEVELS) - 1

# L24: Dual-agent checkerboard (25c, 2ag, 1sol, R=P Y=TL B=TR Pk=D T=D)
LEVELS += ({"cells": [(0,0,1),(2,0,3),(4,0,3),(6,0,1),(8,0,19),(0,2,2),(2,2,3),(4,2,3),(6,2,1),(8,2,2),(0,4,2),(2,4,1),(4,4,3),(6,4,3),(8,4,2),(0,6,2),(2,6,1),(4,6,3),(6,6,3),(8,6,2),(0,8,2),(2,8,1),(4,8,1),(6,8,18),(8,8,3)], "agents": [{"x":-2,"y":0,"dx":1,"dy":0,"team":0},{"x":10,"y":8,"dx":-1,"dy":0,"team":1}]},)
_PP_L24 = len(LEVELS) - 1

# L25: Minimal dual-agent (14c, 2ag, 1sol, R=TL Y=P B=TR)
LEVELS += ({"cells": [(0,0,3),(1,0,3),(2,0,1),(3,0,1),(0,1,(2,6)),(1,1,3),(3,1,1),(2,7,(2,6)),(3,7,1),(1,8,3),(2,8,1),(3,8,1),(0,9,3),(1,9,3)], "agents": [{"x":2,"y":1,"dx":1,"dy":0,"team":0},{"x":0,"y":8,"dx":1,"dy":0,"team":1}]},)
_PP_L25 = len(LEVELS) - 1

# L26: Diagonal scatter (31c, 1ag, 1sol, Y=TR B=Rp Pk=D T=P)
LEVELS += ({"cells": [(0,0,2),(6,0,2),(9,0,2),(11,0,2),(1,1,2),(6,1,(3,2)),(7,1,19),(8,1,2),(12,1,2),(2,2,2),(6,2,2),(7,2,2),(13,2,2),(3,3,2),(14,3,2),(6,5,2),(7,5,2),(0,6,2),(1,6,2),(5,6,3),(6,6,19),(7,6,19),(8,6,2),(2,7,2),(3,7,2),(5,7,3),(9,7,2),(11,7,18),(12,7,18),(13,7,18),(14,7,18)], "agents": [{"x":6,"y":4,"dx":0,"dy":-1,"team":0}]},)
_PP_L26 = len(LEVELS) - 1

# L27: Dual-agent frame (41c, 2ag, 1sol, R=TR B=TL Pk=Rp pk=7)
LEVELS += ({"cells": [(4,0,6),(5,0,6),(4,3,1),(5,3,1),(3,4,(18,3)),(4,4,3),(5,4,(18,3)),(6,4,1),(1,5,(18,1)),(2,5,6),(3,5,6),(4,5,6),(5,5,6),(6,5,(18,1)),(0,6,3),(1,6,1),(5,6,6),(6,6,(18,1)),(0,7,3),(1,7,(18,1)),(2,7,6),(5,7,6),(6,7,(18,1)),(0,8,3),(1,8,1),(2,8,6),(3,8,6),(4,8,6),(5,8,6),(6,8,(18,1)),(0,9,3),(2,9,(18,3)),(3,9,1),(4,9,(18,1)),(5,9,3),(3,10,3),(4,10,3),(3,12,1),(4,12,1),(5,12,18),(6,12,1)], "agents": [{"x":-3,"y":5,"dx":1,"dy":0,"team":0},{"x":3,"y":0,"dx":0,"dy":1,"team":1}]},)
_PP_L27 = len(LEVELS) - 1

# ── campaign order: curated selection from all levels ──
# Indices into the full LEVELS list above. The "album" from the "songbook."

# Count levels just added
_N = len(LEVELS)
_SPIRAL_REV = _N - 1           # spiral reverse
_DIAG_SCATTER = _N - 2         # diagonal scatter
_DUAL_HAND = _N - 3            # hand-designed dual-constraint
_R8 = _DUAL_HAND - 1           # the Replic8 level (figure-8)
_SURROUNDED = _R8 - 1          # "Surrounded" 5-color aha
_SWAP_START = _SURROUNDED - 3  # 3 dense swap levels
_PINGPONG = _SWAP_START - 1    # ping-pong (introduces reverse)
_CROSS_REWARD = _PINGPONG - 1  # expanded cross-junction reward
_CROSS_HAND = _CROSS_REWARD - 1  # hand-designed cross-junction
_MAND_START = _CROSS_HAND - 2  # 2 mandala levels
_TP_START = _MAND_START - 3    # 3 teleport levels
_4C_START = _TP_START - 4      # 4 four-color levels

# Triple sandwich intro (from user): R=TR Y=TL B=P T=D pk=1 t=85
# Mirrored L-frames with B/R/T triple sandwich at junction
LEVELS += (
    {"cells": [(0,0,1),(8,0,1),(0,1,3),(1,1,1),(2,1,3),(6,1,3),(7,1,1),(8,1,3),
               (0,2,3),(1,2,3),(7,2,3),(8,2,3),(0,3,1),(1,3,3),(2,3,(3,1,19)),(6,3,1),(7,3,3),(8,3,3),
               (0,6,1),(1,6,(2,1)),(2,6,2),(0,7,3),(1,7,3),(2,7,1),(6,7,1),(7,7,3),(8,7,3),
               (0,8,3),(1,8,3),(7,8,3),(8,8,3),(0,9,3),(1,9,1),(2,9,3),(6,9,3),(7,9,1),(8,9,3),(0,10,1),(8,10,1)],
     "agents": [{"x":3,"y":3,"dx":-1,"dy":0,"team":0}]},
)
_TRIPLE_SANDWICH = len(LEVELS) - 1

# Symmetric factory (from user): R=TL B=TR Pk=Rp T=D pk=13 t=73
# Pink replicate rows feed into repeating R/Pk/B grid, teal dissolve rows at edges
LEVELS += (
    {"cells": [(10,0,19),(11,0,19),(12,0,19),(13,0,19),(14,0,19),(15,0,19),(16,0,19),(17,0,19),
               (0,2,3),(1,2,3),(2,2,3),(3,2,3),(5,2,18),(6,2,18),(7,2,18),(8,2,18),(10,2,1),(11,2,1),(12,2,1),(13,2,1),(14,2,1),(15,2,1),(16,2,1),(17,2,1),
               (0,5,3),(1,5,3),(2,5,3),(3,5,3),(5,5,1),(9,5,1),(13,5,1),(17,5,1),
               (4,6,18),(5,6,1),(6,6,18),(7,6,3),(8,6,18),(9,6,1),(10,6,18),(11,6,3),(12,6,18),(13,6,1),(14,6,18),(15,6,3),(16,6,18),(17,6,1),(18,6,18),(19,6,3),(21,6,6),
               (0,7,1),(1,7,1),(2,7,1),(3,7,1),(7,7,3),(11,7,3),(15,7,3),(19,7,3),
               (0,10,1),(1,10,1),(2,10,1),(3,10,1),(5,10,18),(6,10,18),(7,10,18),(8,10,18),(10,10,3),(11,10,3),(12,10,3),(13,10,3),(14,10,3),(15,10,3),(16,10,3),(17,10,3),
               (10,12,19),(11,12,19),(12,12,19),(13,12,19),(14,12,19),(15,12,19),(16,12,19),(17,12,19)],
     "agents": [{"x":2,"y":6,"dx":1,"dy":0,"team":0}]},
)
_SYM_FACTORY = len(LEVELS) - 1

# L35: "The Gauntlet" — 5-color, 2-agent facing, 70c, all 5 verbs used, 1 unique solution
# R=TR Y=D B=Rp Pk=TL T=P pk=6 t=26 — the ultimate boss level
LEVELS += (
    {"cells": [(2,0,(18,18)),(3,0,(18,18)),(7,0,(1,1)),(8,0,(1,1)),
               (1,1,(18,18)),(2,1,(1,1)),(3,1,(1,1)),(4,1,(18,18)),(6,1,(1,1)),(7,1,(18,18)),(8,1,(18,18)),(9,1,(1,1)),
               (0,2,2),(1,2,(18,1)),(2,2,19),(3,2,2),(4,2,3),(5,2,19),(6,2,3),(7,2,2),(8,2,19),(9,2,(1,18)),(10,2,2),
               (0,3,1),(1,3,19),(2,3,19),(3,3,19),(4,3,18),(5,3,3),(6,3,1),(7,3,19),(8,3,19),(9,3,19),(10,3,18),
               (0,4,1),(1,4,19),(2,4,19),(3,4,19),(4,4,19),(5,4,(1,18)),(6,4,19),(7,4,19),(8,4,19),(9,4,19),(10,4,18),
               (1,5,2),(2,5,(18,19)),(3,5,19),(4,5,3),(5,5,(18,1)),(6,5,3),(7,5,19),(8,5,(1,19)),(9,5,2),
               (2,6,18),(3,6,19),(4,6,1),(5,6,19),(6,6,18),(7,6,19),(8,6,1),
               (3,7,2),(4,7,(3,1)),(5,7,19),(6,7,(3,18)),(7,7,2),
               (4,8,2),(5,8,3),(6,8,2),
               (5,9,19)],
     "agents": [{"x":5,"y":10,"dx":0,"dy":-1,"team":0},
                {"x":5,"y":1,"dx":0,"dy":1,"team":1}]},
)
_GAUNTLET = len(LEVELS) - 1

# ── Pingpong L28-L34 ──

# L28: Dual-agent diagonal (34c, 2ag)
LEVELS += ({"cells": [(4,0,3),(8,0,19),(3,1,3),(8,1,19),(2,2,3),(8,2,19),(1,3,3),(8,3,19),(5,4,2),(7,4,2),(9,4,2),(11,4,2),(13,4,3),(14,4,3),(15,4,3),(16,4,3),(17,4,19),(0,5,19),(1,5,3),(2,5,3),(3,5,3),(4,5,3),(6,5,2),(8,5,2),(10,5,2),(12,5,2),(8,6,19),(16,6,3),(8,7,19),(15,7,3),(8,8,19),(14,8,3),(8,9,19),(13,9,3)], "agents": [{"x":4,"y":4,"dx":1,"dy":0,"team":0},{"x":13,"y":5,"dx":-1,"dy":0,"team":1}]},)
_PP_L28 = len(LEVELS) - 1

# L29: Compact dual-agent (19c, 2ag)
LEVELS += ({"cells": [(1,0,1),(6,0,6),(3,1,1),(4,1,18),(5,1,1),(7,1,1),(0,3,1),(1,3,2),(1,5,6),(3,5,2),(4,5,2),(5,5,2),(6,5,6),(4,6,1),(5,6,1),(6,6,1),(7,6,1),(0,7,1),(6,7,1)], "agents": [{"x":2,"y":5,"dx":1,"dy":0,"team":0},{"x":5,"y":7,"dx":0,"dy":-1,"team":1}]},)
_PP_L29 = len(LEVELS) - 1

# L30: Dual-agent rooms (42c, 2ag)
LEVELS += ({"cells": [(5,0,1),(6,0,3),(7,0,3),(8,0,3),(9,0,1),(5,1,3),(6,1,1),(9,1,3),(1,2,2),(5,2,3),(6,2,1),(9,2,3),(1,3,2),(5,3,3),(6,3,1),(9,3,3),(0,4,1),(1,4,2),(5,4,3),(6,4,1),(7,4,19),(9,4,3),(1,5,2),(5,5,3),(6,5,1),(7,5,1),(8,5,1),(9,5,3),(0,6,1),(5,6,3),(6,6,1),(7,6,1),(8,6,1),(9,6,3),(5,7,3),(6,7,1),(7,7,3),(8,7,3),(9,7,1),(7,8,19),(6,10,2),(7,10,2)], "agents": [{"x":5,"y":8,"dx":0,"dy":-1,"team":0},{"x":-5,"y":1,"dx":1,"dy":0,"team":1}]},)
_PP_L30 = len(LEVELS) - 1

# L31: 4-agent staircase (52c, 4ag)
LEVELS += ({"cells": [(16,0,2),(18,0,1),(15,1,2),(18,1,1),(14,2,2),(18,2,1),(13,3,2),(18,3,1),(3,4,3),(4,4,2),(9,4,3),(10,4,2),(15,4,3),(16,4,19),(18,4,1),(2,5,3),(3,5,2),(8,5,3),(9,5,2),(14,5,3),(15,5,19),(18,5,1),(1,6,3),(2,6,2),(7,6,3),(8,6,2),(13,6,3),(14,6,19),(18,6,1),(0,7,3),(1,7,2),(6,7,3),(7,7,2),(12,7,3),(13,7,19),(18,7,1),(4,8,19),(18,8,1),(3,9,19),(18,9,1),(2,10,19),(18,10,1),(1,11,19),(18,11,1),(10,12,19),(18,12,1),(9,13,19),(18,13,1),(8,14,19),(18,14,1),(7,15,19),(18,15,1)], "agents": [{"x":-2,"y":4,"dx":1,"dy":0,"team":0},{"x":-2,"y":5,"dx":1,"dy":0,"team":1},{"x":-2,"y":6,"dx":1,"dy":0,"team":2},{"x":-2,"y":7,"dx":1,"dy":0,"team":3}]},)
_PP_L31 = len(LEVELS) - 1

# L32: 4-agent grid sweep (63c, 4ag, 5 colors)
LEVELS += ({"cells": [(3,0,18),(4,0,1),(5,0,18),(6,0,18),(7,0,18),(8,0,2),(2,1,18),(3,1,19),(5,1,1),(6,1,1),(7,1,1),(8,1,1),(1,2,18),(2,2,19),(5,2,1),(6,2,1),(7,2,1),(8,2,1),(0,3,18),(1,3,19),(5,3,1),(6,3,1),(7,3,1),(8,3,1),(0,4,1),(5,4,1),(6,4,1),(7,4,1),(8,4,1),(0,5,(3,18)),(1,5,1),(2,5,1),(3,5,1),(4,5,1),(5,5,1),(6,5,1),(7,5,1),(8,5,1),(9,5,1),(10,5,2),(0,6,18),(1,6,1),(2,6,1),(3,6,1),(4,6,1),(5,6,1),(6,6,1),(7,6,1),(8,6,1),(9,6,1),(10,6,2),(5,7,1),(6,7,1),(7,7,1),(8,7,1),(5,8,1),(6,8,2),(7,8,1),(8,8,1),(5,9,1),(6,9,2),(7,9,1),(8,9,1)], "agents": [{"x":5,"y":10,"dx":0,"dy":-1,"team":0},{"x":6,"y":10,"dx":0,"dy":-1,"team":1},{"x":7,"y":10,"dx":0,"dy":-1,"team":2},{"x":8,"y":10,"dx":0,"dy":-1,"team":3}]},)
_PP_L32 = len(LEVELS) - 1

# L33: Dual-agent scenic (69c, 2ag)
LEVELS += ({"cells": [(0,0,3),(1,0,3),(2,0,3),(3,0,3),(4,0,3),(5,0,3),(6,0,3),(7,0,3),(8,0,3),(9,0,3),(10,0,3),(11,0,18),(11,1,1),(12,1,18),(10,2,1),(11,2,1),(12,2,1),(13,2,18),(10,3,2),(11,3,3),(0,4,6),(10,4,18),(11,4,3),(15,4,6),(17,4,6),(19,4,6),(21,4,6),(23,4,6),(25,4,6),(10,5,2),(11,5,3),(0,6,6),(10,6,18),(11,6,3),(10,7,2),(11,7,3),(0,8,6),(10,8,18),(11,8,3),(10,9,2),(11,9,3),(0,10,6),(10,10,18),(11,10,3),(10,11,2),(11,11,3),(0,12,6),(10,12,18),(11,12,3),(10,13,2),(11,13,3),(0,14,6),(10,14,18),(11,14,3),(13,14,1),(14,14,2),(15,14,1),(16,14,2),(17,14,1),(18,14,2),(19,14,1),(20,14,2),(21,14,1),(22,14,2),(23,14,1),(24,14,2),(25,14,1),(26,14,6),(10,15,6)], "agents": [{"x":-1,"y":0,"dx":1,"dy":0,"team":0},{"x":11,"y":15,"dx":0,"dy":-1,"team":1}]},)
_PP_L33 = len(LEVELS) - 1

# L34: 5-color sandwich puzzle (27c, 1ag)
LEVELS += ({"cells": [(0,0,3),(1,0,1),(2,0,1),(5,0,1),(6,0,1),(7,0,2),(2,2,(18,19)),(6,2,18),(7,2,(19,2)),(1,3,2),(2,3,19),(6,3,2),(7,3,19),(0,6,3),(0,7,19),(1,7,(1,2)),(8,7,3),(1,8,(2,19)),(2,8,19),(6,8,(2,2)),(7,8,1),(8,8,2),(2,9,2),(3,9,1),(4,9,1),(5,9,1),(6,9,2)], "agents": [{"x":1,"y":2,"dx":1,"dy":0,"team":0}]},)
_PP_L34 = len(LEVELS) - 1

# ── External levels loader ──
# Load additional levels from levels.txt (one TGUSF1-... code per line)
# This allows hot-swapping community levels without editing app.py
_COMMUNITY_LEVELS_START = len(LEVELS)
_levels_txt = os.path.join(os.path.dirname(__file__), "levels.txt")
if os.path.exists(_levels_txt):
    with open(_levels_txt) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and _line.startswith("TGUSF1-"):
                _lev = deserialize_level(_line)
                if _lev:
                    LEVELS += (_lev,)
_COMMUNITY_LEVELS_END = len(LEVELS)
_N_COMMUNITY = _COMMUNITY_LEVELS_END - _COMMUNITY_LEVELS_START

_seen_order = set()
def _dedup(indices):
    """Remove duplicate indices, keeping first occurrence."""
    result = []
    for idx in indices:
        if idx not in _seen_order:
            _seen_order.add(idx)
            result.append(idx)
    return result

CAMPAIGN_ORDER = _dedup([
    # Act 1: Tutorial (4) — learn pass, dissolve, turns on simple tapes
    0, 1, 2, 5,
    # Act 2: 2D + Grey + Triple sandwich (4) — turns in 2D, sandwich intro
    8, 10, _TRIPLE_SANDWICH, 14,
    # Act 3: Advanced (4) — fractals, sandwiches, key puzzles
    15, 18, 20, 23,
    # Act 4: Multi-agent intro (4) — two agents, shared + per-agent rules
    _PP_L25, _PP_L15, 47, 48,
    # Act 5: Devilish (2) — traps, forced replicate
    81, 85,
    # Act 6: 4-color + Reverse (5) — new mechanics, ping-pong intro
    _4C_START, _4C_START+1, _4C_START+3,
    _PINGPONG, _PP_L20,
    # Act 7: Teleport + Mandala (4)
    _TP_START, _TP_START+1,
    _MAND_START, _MAND_START+1,
    # Act 8: Cross-junction + Swap (4) — solve locally, watch it scale
    _CROSS_HAND, _CROSS_REWARD,
    _SWAP_START, _SWAP_START+1,
    # Act 9: Dual-constraint (8) — two shapes, shared rules
    _DUAL_HAND, _PP_L24, _PP_L25, _DUAL_PATH_NEW, _PP_L14, _PP_L28, _PP_L30, _PP_L27,
    # Act 10: Spectacle (5) — consecutive replicate, layered factory, big grids
    _SPIRAL_GEN, _LAYERED_FACTORY, _PP_L22, _PP_L13, _SYM_FACTORY,
    # Act 11: Multi-agent advanced (6) — 3-4 agents, room escape
    _PP_L29, _PP_L21, _PP_L16, _PP_L31, _3AGENT_FRAME, _PP_L18,
    # Act 12: 5-color endgame (5) — surrounded, spiral frame, scatter, 4-agent sweep
    _SURROUNDED, _PP_L23, _PP_L26, _PP_L32, _PP_L34,
    # Act 13: Boss levels (4) — scenic + hardest puzzles
    _PP_L33, _PP_L17, _SPIRAL_REV,
    # The Gauntlet: 5-color, 2-agent, all verbs, 1 solution — penultimate challenge
    _GAUNTLET,
    # Finale: The Replic8
    _R8,
])

CAMPAIGN = [LEVELS[i] for i in CAMPAIGN_ORDER if i < len(LEVELS)]

# ── load external levels from levels.txt ──
_LEVELS_TXT = os.path.join(os.path.dirname(__file__), "levels.txt")

def _load_external_levels():
    """Load level codes from levels.txt, return list of level dicts."""
    # import deserialize here to avoid circular dependency — it's defined below
    # so we call this lazily from main()
    ext = []
    if os.path.exists(_LEVELS_TXT):
        with open(_LEVELS_TXT) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("TGUSF1-"):
                    ext.append(line)
    return ext

NUM_LEVELS = len(CAMPAIGN)

_ALL_LEVELS = LEVELS  # keep full list for editor
LEVELS = CAMPAIGN


# ── level serialization ──

import json, zlib, base64

def serialize_level(level):
    """Encode a level dict to a compact shareable string."""
    cells = level["cells"]
    if not cells:
        return None

    # normalize coordinates to start at (0,0)
    min_x = min(x for x, y, c in cells)
    min_y = min(y for x, y, c in cells)

    def encode_cell(c):
        if isinstance(c, tuple):
            return list(c)
        return c

    data = {
        "c": [[x - min_x, y - min_y, encode_cell(c)] for x, y, c in cells],
    }

    if "agents" in level:
        data["a"] = [[a["x"] - min_x, a["y"] - min_y, a["dx"], a["dy"], a.get("team", 0)]
                      for a in level["agents"]]
    else:
        data["a"] = [[level["start"][0] - min_x, level["start"][1] - min_y,
                       level["dir"][0], level["dir"][1], 0]]

    if level.get("per_agent_rules"):
        data["p"] = 1

    payload = json.dumps(data, separators=(',', ':'))
    compressed = zlib.compress(payload.encode(), 9)
    code = "TGUSF1-" + base64.urlsafe_b64encode(compressed).decode().rstrip('=')
    return code


def deserialize_level(code):
    """Decode a level string back to a level dict."""
    if not code.startswith("TGUSF1-"):
        return None
    b64 = code[7:]
    # restore padding
    b64 += '=' * (-len(b64) % 4)
    try:
        compressed = base64.urlsafe_b64decode(b64)
        payload = zlib.decompress(compressed).decode()
        data = json.loads(payload)
    except Exception:
        return None

    def decode_cell(c):
        if isinstance(c, list):
            return tuple(c)
        return c

    cells = [(x, y, decode_cell(c)) for x, y, c in data["c"]]
    agents = [{"x": a[0], "y": a[1], "dx": a[2], "dy": a[3], "team": a[4]}
              for a in data["a"]]

    level = {"cells": cells, "agents": agents}
    if data.get("p"):
        level["per_agent_rules"] = True
    return level


# ── pack serialization (collections of levels) ──

def serialize_pack(name, levels):
    """Encode a named collection of levels to a shareable string."""
    if not levels:
        return None
    # serialize each level to its compact dict form
    pack_levels = []
    for level in levels:
        cells = level.get("cells", [])
        if not cells:
            continue
        min_x = min(x for x, y, c in cells)
        min_y = min(y for x, y, c in cells)
        def encode_cell(c):
            if isinstance(c, tuple):
                return list(c)
            return c
        ld = {"c": [[x - min_x, y - min_y, encode_cell(c)] for x, y, c in cells]}
        if "agents" in level:
            ld["a"] = [[a["x"] - min_x, a["y"] - min_y, a["dx"], a["dy"], a.get("team", 0)]
                        for a in level["agents"]]
        else:
            ld["a"] = [[level["start"][0] - min_x, level["start"][1] - min_y,
                         level["dir"][0], level["dir"][1], 0]]
        if level.get("per_agent_rules"):
            ld["p"] = 1
        if level.get("mode"):
            ld["m"] = level["mode"]
        pack_levels.append(ld)

    data = {"n": name, "l": pack_levels}
    payload = json.dumps(data, separators=(',', ':'))
    compressed = zlib.compress(payload.encode(), 9)
    code = "TGUSFP1-" + base64.urlsafe_b64encode(compressed).decode().rstrip('=')
    return code


def deserialize_pack(code):
    """Decode a pack string back to a name + list of level dicts."""
    if not code.startswith("TGUSFP1-"):
        return None, None
    b64 = code[8:]
    b64 += '=' * (-len(b64) % 4)
    try:
        compressed = base64.urlsafe_b64decode(b64)
        payload = zlib.decompress(compressed).decode()
        data = json.loads(payload)
    except Exception:
        return None, None

    def decode_cell(c):
        if isinstance(c, list):
            return tuple(c)
        return c

    name = data.get("n", "Unnamed Pack")
    levels = []
    for ld in data.get("l", []):
        cells = [(x, y, decode_cell(c)) for x, y, c in ld["c"]]
        agents = [{"x": a[0], "y": a[1], "dx": a[2], "dy": a[3], "team": a[4]}
                  for a in ld["a"]]
        level = {"cells": cells, "agents": agents}
        if ld.get("p"):
            level["per_agent_rules"] = True
        if ld.get("m"):
            level["mode"] = ld["m"]
        levels.append(level)

    return name, levels


def grid_to_level(grid, agents, underneath):
    """Extract a level dict from the current grid state (for editor)."""
    cells = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            c = grid[y][x]
            if is_wall(c):
                cells.append((x, y, c))
            # also check if agent is sitting on sandwich layers
    for (ax, ay), layers in underneath.items():
        cell_val = layers[0] if len(layers) == 1 else tuple(layers)
        cells.append((ax, ay, cell_val))

    agent_defs = [{"x": a["x"], "y": a["y"], "dx": a["dx"], "dy": a["dy"],
                   "team": a.get("team", 0)} for a in agents if a["alive"]]

    if not cells:
        return None
    return {"cells": cells, "agents": agent_defs}


def check_solvable(level, max_teams=1):
    """Brute-force check: does any verb assignment give a perfect solution?"""
    from itertools import product as iprod
    verbs_range = [VERB_PASS, VERB_REPLICATE, VERB_DISSOLVE, VERB_TURN_LEFT, VERB_TURN_RIGHT,
                   VERB_REVERSE, VERB_SKIP, VERB_WAIT]

    if max_teams == 1:
        combos = iprod(verbs_range, repeat=3)
    else:
        combos = iprod(verbs_range, repeat=3 * max_teams)

    solutions = 0
    for combo in combos:
        if max_teams == 1:
            vl = [{WALL_RED: combo[0], WALL_YELLOW: combo[1], WALL_BLUE: combo[2]}]
        else:
            vl = []
            for t in range(max_teams):
                off = t * 3
                vl.append({WALL_RED: combo[off], WALL_YELLOW: combo[off+1], WALL_BLUE: combo[off+2]})

        g, ag, und = make_grid(level)
        for _ in range(MAX_STEPS):
            if not ag or count_walls(g, und) == 0:
                break
            ag, _, _ = sim_step(ag, g, vl, und)

        if count_walls(g, und) == 0 and len(ag) == 0:
            solutions += 1
            if solutions >= 1:
                return solutions  # early exit: at least 1 solution found
    return solutions


# ── editor ──

EDITOR_PALETTE = [
    # assignable colors (player sets the verb)
    (WALL_RED,         "Red"),
    (WALL_YELLOW,      "Yellow"),
    (WALL_BLUE,        "Blue"),
    (WALL_PINK,        "Pink"),
    (WALL_TEAL,        "Teal"),
    # fixed cells (always do one thing)
    (FIXED_PASS,       "Grey (pass)"),
    (FIXED_REPLICATE,  "Green (replicate)"),
    (FIXED_DISSOLVE,   "Purple (dissolve)"),
    (FIXED_TURN_RIGHT, "Turn R"),
    (FIXED_TURN_LEFT,  "Turn L"),
    (FIXED_REVERSE,    "Reverse"),
    (FIXED_SKIP,       "Skip"),
    # teleport pairs (same hue, dark=in light=out)
    (TELE_IN_1, "Tele 1 In"),
    (TELE_OUT_1, "Tele 1 Out"),
    (TELE_IN_2, "Tele 2 In"),
    (TELE_OUT_2, "Tele 2 Out"),
    (TELE_IN_3, "Tele 3 In"),
    (TELE_OUT_3, "Tele 3 Out"),
    (TELE_IN_4, "Tele 4 In"),
    (TELE_OUT_4, "Tele 4 Out"),
]

EDITOR_BG = (30, 30, 42)


def draw_editor_panel(screen, font, font_sm, editor_state, mouse_pos):
    """Draw the editor palette and controls. Compact 2-column grid layout."""
    px = GRID_PX_W
    pygame.draw.rect(screen, EDITOR_BG, (px, 0, PANEL_W, WIN_H))

    y = 8
    screen.blit(font.render("LEVEL EDITOR", True, (255, 200, 80)), (px + 10, y))
    y += 24

    # one-line hint (H key toggles help overlay)
    show_help = editor_state.get("show_help", False)
    help_btn = None  # no separate button needed, H key handles it
    screen.blit(font_sm.render("H=help  T=test  C=copy  V=paste", True, TEXT_DIM), (px + 8, y))
    y += 20

    # agent placement: dedicated button + agent mode toggle
    na = editor_state["num_agents"]
    agent_mode = editor_state.get("agent_place_mode", False)

    # agent place toggle button
    abx, aby = px + 8, y
    abw, abh = PANEL_W - 16, 24
    a_hov = abx <= mouse_pos[0] < abx + abw and aby <= mouse_pos[1] < aby + abh
    a_bg = (80, 180, 100) if agent_mode else (55, 55, 70) if a_hov else (40, 40, 52)
    pygame.draw.rect(screen, a_bg, (abx, aby, abw, abh), border_radius=3)
    a_label = f"PLACE AGENT ({na} max)  {'[ON]' if agent_mode else '[OFF]'}"
    a_fg = (0, 0, 0) if agent_mode else TEXT_COLOR
    screen.blit(font_sm.render(a_label, True, a_fg), (abx + 6, aby + 4))
    agent_btn = (abx, aby, abw, abh, "agent_toggle")
    y += abh + 4

    # agent count + per-agent buttons (compact row)
    screen.blit(font_sm.render("Agents:", True, TEXT_DIM), (px + 10, y + 2))
    count_rects = []
    for i in range(1, 5):
        cbx = px + 70 + (i - 1) * 28
        cbw, cbh = 24, 20
        active = na == i
        c_hov = cbx <= mouse_pos[0] < cbx + cbw and y <= mouse_pos[1] < y + cbh
        bg = (80, 180, 100) if active else (50, 50, 65) if c_hov else (38, 38, 52)
        pygame.draw.rect(screen, bg, (cbx, y, cbw, cbh), border_radius=2)
        fg = (0, 0, 0) if active else TEXT_COLOR
        screen.blit(font_sm.render(str(i), True, fg), (cbx + 8, y + 2))
        count_rects.append((cbx, y, cbw, cbh, ("agent_count", i)))

    # per-agent toggle
    pa = editor_state["per_agent"]
    pbx = px + 195
    pbw = 75
    p_hov = pbx <= mouse_pos[0] < pbx + pbw and y <= mouse_pos[1] < y + 20
    bg = (80, 180, 100) if pa else (50, 50, 65) if p_hov else (38, 38, 52)
    pygame.draw.rect(screen, bg, (pbx, y, pbw, 20), border_radius=2)
    fg = (0, 0, 0) if pa else TEXT_COLOR
    screen.blit(font_sm.render("PerAgent" if pa else "Shared", True, fg), (pbx + 4, y + 2))
    per_agent_btn = (pbx, y, pbw, 20, "per_agent_toggle")
    y += 26

    # cell palette header
    screen.blit(font_sm.render("CELLS:", True, TEXT_COLOR), (px + 10, y))
    y += 16

    # 2-column grid of color swatches — compact
    btn_rects = []
    sel = editor_state["selected"]
    cols = 2
    swatch_w = (PANEL_W - 20) // cols - 4
    swatch_h = 22
    for i, (cell_type, label) in enumerate(EDITOR_PALETTE):
        col = i % cols
        row = i // cols
        bx = px + 8 + col * (swatch_w + 6)
        by = y + row * (swatch_h + 3)
        is_sel = cell_type == sel
        hovered = bx <= mouse_pos[0] < bx + swatch_w and by <= mouse_pos[1] < by + swatch_h
        bg = (70, 70, 90) if is_sel else (50, 50, 65) if hovered else (38, 38, 52)
        pygame.draw.rect(screen, bg, (bx, by, swatch_w, swatch_h), border_radius=2)
        # color swatch
        pygame.draw.rect(screen, WCOLOR[cell_type], (bx + 2, by + 2, 18, swatch_h - 4))
        if cell_type in FIXED_TYPES:
            pygame.draw.rect(screen, (255, 255, 255), (bx + 4, by + 4, 14, swatch_h - 8), 1)
        # short label
        short = label.split("(")[0].strip()[:10]
        screen.blit(font_sm.render(short, True, TEXT_COLOR), (bx + 23, by + 3))
        if is_sel:
            pygame.draw.rect(screen, (255, 200, 80), (bx, by, swatch_w, swatch_h), 2, border_radius=2)
        btn_rects.append((bx, by, swatch_w, swatch_h, cell_type))

    n_rows = (len(EDITOR_PALETTE) + cols - 1) // cols
    y += n_rows * (swatch_h + 3) + 8

    # current brush indicator
    brush = editor_state.get("brush", editor_state["selected"])
    screen.blit(font_sm.render("Brush:", True, TEXT_DIM), (px + 10, y))
    bx_start = px + 55
    if isinstance(brush, tuple):
        # sandwich brush — draw stacked stripes
        sw_w, sw_h = 30, 18
        n = len(brush)
        for i, sc in enumerate(brush):
            sy = y + (sw_h * i) // n
            sh = (sw_h * (i + 1)) // n - (sw_h * i) // n
            pygame.draw.rect(screen, WCOLOR[sc], (bx_start, sy, sw_w, sh))
        pygame.draw.rect(screen, TEXT_DIM, (bx_start, y, sw_w, sw_h), 1)
        screen.blit(font_sm.render("sandwich", True, TEXT_DIM), (bx_start + 34, y + 2))
    else:
        pygame.draw.rect(screen, WCOLOR.get(brush, (80,80,80)), (bx_start, y, 18, 14))
        if brush in FIXED_TYPES:
            pygame.draw.rect(screen, (255,255,255), (bx_start + 2, y + 2, 14, 10), 1)
        cname = ""
        for ct, lb in EDITOR_PALETTE:
            if ct == brush: cname = lb; break
        screen.blit(font_sm.render(cname, True, TEXT_DIM), (bx_start + 22, y))
    y += 20

    # sandwich stack builder
    stack = editor_state["sandwich_stack"]
    if stack:
        screen.blit(font_sm.render("Building:", True, TEXT_DIM), (px + 10, y))
        for i, sc in enumerate(stack):
            pygame.draw.rect(screen, WCOLOR[sc], (px + 70 + i * 22, y, 18, 14))
        screen.blit(font_sm.render("S=add D=clear", True, TEXT_DIM), (px + 70 + len(stack) * 22 + 4, y))
        y += 18
    else:
        y += 2

    # action buttons — compact horizontal pairs
    action_rects = []
    action_btns = [("Test", "test"), ("Copy", "copy"), ("Paste", "paste"), ("Clear", "clear")]
    abw2 = (PANEL_W - 24) // 2
    for i, (label, key) in enumerate(action_btns):
        col = i % 2
        row = i // 2
        bx = px + 8 + col * (abw2 + 6)
        by = y + row * 28
        bw, bh = abw2, 24
        hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
        bg = (60, 60, 80) if hovered else (45, 45, 60)
        pygame.draw.rect(screen, bg, (bx, by, bw, bh), border_radius=3)
        screen.blit(font_sm.render(label, True, TEXT_COLOR), (bx + bw // 2 - font_sm.size(label)[0] // 2, by + 4))
        action_rects.append((bx, by, bw, bh, key))
    y += 2 * 28 + 8

    # status message
    msg = editor_state.get("status_msg", "")
    if msg:
        mc = STATUS_GREEN if "OK" in msg or "Copied" in msg or "placed" in msg.lower() else STATUS_YELLOW
        screen.blit(font_sm.render(msg, True, mc), (px + 10, y))
        y += 16

    # level code (full, wrapped)
    code = editor_state.get("level_code", "")
    if code:
        cw = PANEL_W - 20
        chars = cw // 7
        max_lines = 6
        for i in range(0, len(code), chars):
            if i // chars >= max_lines:
                screen.blit(font_sm.render("...", True, (100, 120, 150)), (px + 10, y))
                y += 13
                break
            screen.blit(font_sm.render(code[i:i+chars], True, (150, 180, 220)), (px + 10, y))
            y += 13

    # return all clickable rects: btn_rects (cells) + action_rects + special buttons
    all_special = [agent_btn, per_agent_btn] + count_rects
    return btn_rects, action_rects + all_special


def draw_editor_grid(screen, grid, editor_agents, underneath):
    """Draw grid with editor overlay (grid lines, cursor highlight)."""
    # draw faint grid lines
    for x in range(GRID_W + 1):
        pygame.draw.line(screen, (35, 35, 48), (x * CELL, 0), (x * CELL, GRID_PX_H))
    for y in range(GRID_H + 1):
        pygame.draw.line(screen, (35, 35, 48), (0, y * CELL), (GRID_PX_W, y * CELL))

    # draw cells
    for y in range(GRID_H):
        for x in range(GRID_W):
            c = grid[y][x]
            if is_wall(c):
                draw_cell(screen, x * CELL, y * CELL, c)

    # draw editor agents (as colored arrows)
    for a in editor_agents:
        rx, ry = a["x"] * CELL, a["y"] * CELL
        cx, cy = rx + CELL // 2, ry + CELL // 2
        team = a.get("team", 0)
        color = TEAM_COLORS[team % len(TEAM_COLORS)]
        pygame.draw.circle(screen, color, (cx, cy), CELL // 2 - 2)
        tip_x = cx + a["dx"] * (CELL // 4)
        tip_y = cy + a["dy"] * (CELL // 4)
        pygame.draw.circle(screen, (255, 255, 255), (tip_x, tip_y), 3)


# ── world setup ──

def make_grid(level):
    grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
    cells = level["cells"]

    # gather all positions for bounding box: cells + agent starts
    xs = [x for x, y, c in cells]
    ys = [y for x, y, c in cells]

    if "agents" in level:
        agent_defs = level["agents"]
    else:
        agent_defs = [{"x": level["start"][0], "y": level["start"][1],
                       "dx": level["dir"][0], "dy": level["dir"][1]}]

    for ad in agent_defs:
        xs.append(ad["x"]); ys.append(ad["y"])

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    shape_w = max_x - min_x + 1
    shape_h = max_y - min_y + 1

    ox = (GRID_W - shape_w) // 2 - min_x
    oy = (GRID_H - shape_h) // 2 - min_y

    for x, y, c in cells:
        grid[y + oy][x + ox] = c

    agents = []
    for i, ad in enumerate(agent_defs):
        ax, ay = ad["x"] + ox, ad["y"] + oy
        grid[ay][ax] = AGENT
        team = ad.get("team", i)
        evil = ad.get("evil", False)
        agents.append({"x": ax, "y": ay, "dx": ad["dx"], "dy": ad["dy"], "alive": True, "team": team, "evil": evil})

    underneath = {}

    return grid, agents, underneath


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

def _resolve_wall(a, nx, ny, grid, verbs_list, underneath, evil_rules=None):
    """Resolve an agent hitting a wall cell. Returns action dict or None."""
    x, y = a["x"], a["y"]
    dx, dy = a["dx"], a["dy"]
    target = grid[ny][nx]
    top, remaining = pop_top(target)

    # one-way gates: block agents coming from wrong direction
    if top in ONE_WAY_TYPES:
        if (dx, dy) != ONE_WAY_DIR[top]:
            return None

    # evil agents use fixed evil_rules, hero agents use verbs_list
    if evil_rules and a.get("evil"):
        team_verbs = evil_rules
    else:
        team_verbs = verbs_list[min(a.get("team", 0), len(verbs_list) - 1)]
    verb = get_verb(top, team_verbs)
    has_remaining = remaining != EMPTY

    return {"verb": verb, "top": top, "remaining": remaining, "has_remaining": has_remaining}


def sim_step(agents, grid, verbs_list, underneath, evil_rules=None):
    """Two-phase sim: compute intended moves, resolve collisions, then execute.
    Collision rule: agent moving into occupied cell bounces (reverses).
    Two agents moving into same empty cell: both bounce."""
    new_agents = []
    consumed_count = 0
    dissolved_count = 0
    turned_count = 0
    reversed_count = 0
    teleported_count = 0

    # ── phase 1: compute intended destinations ──
    intents = []  # (agent, action_type, dest_x, dest_y, wall_info)
    for a in agents:
        if not a["alive"]:
            intents.append((a, "dead", -1, -1, None))
            continue

        x, y = a["x"], a["y"]
        dx, dy = a["dx"], a["dy"]
        nx, ny = x + dx, y + dy

        if not in_bounds(nx, ny):
            intents.append((a, "stuck", x, y, None))
            continue

        target = grid[ny][nx]

        if target == EMPTY:
            intents.append((a, "move", nx, ny, None))
        elif is_wall(target):
            info = _resolve_wall(a, nx, ny, grid, verbs_list, underneath, evil_rules)
            if info is None:
                intents.append((a, "stuck", x, y, None))
            elif info["verb"] == VERB_DISSOLVE:
                intents.append((a, "dissolve", nx, ny, info))
            elif info["verb"] == VERB_REPLICATE:
                intents.append((a, "replicate", nx, ny, info))
            elif info["verb"] == VERB_SKIP:
                skip_x, skip_y = nx + dx, ny + dy
                if in_bounds(skip_x, skip_y) and grid[skip_y][skip_x] == EMPTY:
                    intents.append((a, "skip", skip_x, skip_y, info))
                else:
                    intents.append((a, "skip_short", nx, ny, info))
            else:
                # pass, turn_left, turn_right, reverse, wait — all move to nx,ny
                intents.append((a, "wall_move", nx, ny, info))
        elif target == AGENT:
            # always block — agents form stacks, pop one at a time
            intents.append((a, "stuck", x, y, None))
        else:
            intents.append((a, "stuck", x, y, None))

    # ── phase 2: agents pass through each other, no collision detection needed ──

    # ── phase 3: execute ──
    for a, action, dest_x, dest_y, info in intents:
        if not a["alive"]:
            continue

        x, y = a["x"], a["y"]
        dx, dy = a["dx"], a["dy"]
        nx, ny = x + dx, y + dy

        if action == "move":
            vacate(x, y, grid, underneath)
            a["x"], a["y"] = dest_x, dest_y
            grid[dest_y][dest_x] = AGENT

        elif action == "bounce":
            pass

        elif action == "dissolve":
            dissolved_count += 1
            a["alive"] = False
            a["rev_count"] = 0
            vacate(x, y, grid, underneath)
            if info["has_remaining"]:
                rem = info["remaining"]
                grid[ny][nx] = rem if not isinstance(rem, list) else tuple(rem)
            else:
                grid[ny][nx] = EMPTY

        elif action == "replicate":
            consumed_count += 1
            child = {"x": nx, "y": ny, "dx": dx, "dy": dy, "alive": True,
                     "team": a.get("team", 0), "evil": a.get("evil", False)}
            new_agents.append(child)
            if info["has_remaining"]:
                occupy(nx, ny, grid, underneath, info["remaining"])
            else:
                grid[ny][nx] = AGENT

        elif action in ("wall_move", "skip_short"):
            consumed_count += 1
            verb = info["verb"]
            vacate(x, y, grid, underneath)
            a["x"], a["y"] = nx, ny

            if verb == VERB_TURN_LEFT:
                a["dx"], a["dy"] = turn_left(dx, dy)
                a["rev_count"] = 0
                turned_count += 1
            elif verb == VERB_TURN_RIGHT:
                a["dx"], a["dy"] = turn_right(dx, dy)
                a["rev_count"] = 0
                turned_count += 1
            elif verb == VERB_REVERSE:
                # cap consecutive reverses: if reversed 2+ times in a row, pass through instead
                rev_count = a.get("rev_count", 0) + 1
                if rev_count >= 3:
                    # treat as pass — don't reverse, just walk through
                    a["rev_count"] = 0
                else:
                    a["dx"], a["dy"] = -dx, -dy
                    a["rev_count"] = rev_count
                    reversed_count += 1
            elif verb == VERB_WAIT:
                # stay in place, consume cell, don't move
                a["x"], a["y"] = x, y
                # but cell at nx,ny was consumed — handle remaining
                if info["has_remaining"]:
                    grid[ny][nx] = info["remaining"] if not isinstance(info["remaining"], tuple) else info["remaining"]
                else:
                    grid[ny][nx] = EMPTY
                # re-place agent at original position
                grid[y][x] = AGENT
                continue  # skip the occupy logic below

            if info["has_remaining"]:
                occupy(nx, ny, grid, underneath, info["remaining"])
            else:
                grid[ny][nx] = AGENT

        elif action == "skip":
            vacate(x, y, grid, underneath)
            a["x"], a["y"] = dest_x, dest_y
            grid[dest_y][dest_x] = AGENT
            # handle consumed cell at nx,ny
            if info["has_remaining"]:
                rem = info["remaining"]
                grid[ny][nx] = rem if not isinstance(rem, tuple) else rem
            else:
                grid[ny][nx] = EMPTY

        # teleport handling (after wall actions)
        if action in ("wall_move", "replicate", "dissolve", "skip", "skip_short") and info and info.get("top") in TELE_PAIRS:
            pair = TELE_PAIRS[info["top"]]
            for ty in range(GRID_H):
                for tx in range(GRID_W):
                    tc = grid[ty][tx]
                    found_pair = False
                    if tc == pair: found_pair = True
                    elif isinstance(tc, tuple) and pair in tc: found_pair = True
                    elif (tx, ty) in underneath and pair in underneath[(tx, ty)]: found_pair = True
                    if found_pair:
                        teleported_count += 1
                        vacate(a["x"], a["y"], grid, underneath)
                        if info["has_remaining"]:
                            grid[ny][nx] = info["remaining"] if not isinstance(info["remaining"], tuple) else info["remaining"]
                        else:
                            grid[ny][nx] = EMPTY
                        exit_top, exit_rem = pop_top(tc)
                        exit_has_rem = exit_rem != EMPTY
                        a["x"], a["y"] = tx, ty
                        if exit_has_rem:
                            occupy(tx, ty, grid, underneath, exit_rem)
                        else:
                            grid[ty][tx] = AGENT
                        break
                else:
                    continue
                break

    # add newborns
    spawned = 0
    for na in new_agents:
        if len(agents) + spawned >= MAX_POP:
            break
        agents.append(na)
        spawned += 1

    alive = [a for a in agents if a["alive"]]
    events = {"consumed": consumed_count, "dissolved": dissolved_count,
              "replicated": spawned, "turned": turned_count,
              "reversed": reversed_count, "teleported": teleported_count}
    return alive, spawned, events


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
            if color in FIXED_TYPES or color in EDITOR_EXTRA_TYPES:
                pygame.draw.rect(screen, (255,255,255), (rx+3, sy+1, CELL-6, max(sh-2, 1)), 1)
            # dividing line between same-color adjacent layers
            if i > 0 and cell[i] == cell[i-1]:
                div_y = ry + 1 + (inner_h * i) // n
                pygame.draw.line(screen, (0, 0, 0), (rx + 1, div_y), (rx + CELL - 2, div_y))
                pygame.draw.line(screen, (255, 255, 255, 80), (rx + 2, div_y), (rx + CELL - 3, div_y))
    elif cell in WCOLOR:
        pygame.draw.rect(screen, WCOLOR[cell], (rx+1, ry+1, CELL-2, CELL-2))
        if cell in FIXED_TYPES:
            pygame.draw.rect(screen, (255,255,255), (rx+4, ry+4, CELL-8, CELL-8), 1)
        # fixed turn: draw "L" or "R" centered
        if cell == FIXED_TURN_LEFT:
            lbl_font = pygame.font.SysFont("consolas", 12, bold=True)
            lbl = lbl_font.render("L", True, (255, 255, 255))
            screen.blit(lbl, (rx + (CELL - lbl.get_width()) // 2, ry + (CELL - lbl.get_height()) // 2))
        elif cell == FIXED_TURN_RIGHT:
            lbl_font = pygame.font.SysFont("consolas", 12, bold=True)
            lbl = lbl_font.render("R", True, (255, 255, 255))
            screen.blit(lbl, (rx + (CELL - lbl.get_width()) // 2, ry + (CELL - lbl.get_height()) // 2))
        # one-way gate: draw direction arrow
        if cell in ONE_WAY_TYPES:
            cx, cy = rx + CELL // 2, ry + CELL // 2
            d = ONE_WAY_DIR[cell]
            tip = (cx + d[0] * 5, cy + d[1] * 5)
            base1 = (cx - d[0] * 3 + d[1] * 3, cy - d[1] * 3 + d[0] * 3)
            base2 = (cx - d[0] * 3 - d[1] * 3, cy - d[1] * 3 - d[0] * 3)
            pygame.draw.polygon(screen, (40, 40, 50), [tip, base1, base2])
        # teleport: big centered pair number, dark=in light=out (same hue)
        elif cell in ALL_TELE_TYPES:
            tele_ins = [TELE_IN_1, TELE_IN_2, TELE_IN_3, TELE_IN_4]
            tele_outs = [TELE_OUT_1, TELE_OUT_2, TELE_OUT_3, TELE_OUT_4]
            if cell in tele_ins:
                pair_num = tele_ins.index(cell) + 1
            else:
                pair_num = tele_outs.index(cell) + 1
            # big centered number
            num_font = pygame.font.SysFont("consolas", 14, bold=True)
            num_surf = num_font.render(str(pair_num), True, (255, 255, 255))
            nx = rx + (CELL - num_surf.get_width()) // 2
            ny = ry + (CELL - num_surf.get_height()) // 2
            screen.blit(num_surf, (nx, ny))
        # reverse: draw double-headed arrow
        elif cell == FIXED_REVERSE:
            cx, cy = rx + CELL // 2, ry + CELL // 2
            pygame.draw.line(screen, (255,255,255), (cx-4, cy), (cx+4, cy), 1)
            pygame.draw.line(screen, (255,255,255), (cx-4, cy), (cx-2, cy-2), 1)
            pygame.draw.line(screen, (255,255,255), (cx+4, cy), (cx+2, cy+2), 1)
        # skip: draw double chevron
        elif cell == FIXED_SKIP:
            cx, cy = rx + CELL // 2, ry + CELL // 2
            pygame.draw.line(screen, (40,40,50), (cx-3, cy-3), (cx, cy), 1)
            pygame.draw.line(screen, (40,40,50), (cx, cy), (cx-3, cy+3), 1)
            pygame.draw.line(screen, (40,40,50), (cx, cy-3), (cx+3, cy), 1)
            pygame.draw.line(screen, (40,40,50), (cx+3, cy), (cx, cy+3), 1)


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

        if a.get("evil"):
            color = EVIL_COLOR
        else:
            team = a.get("team", 0)
            color = TEAM_COLORS[team % len(TEAM_COLORS)]
        pygame.draw.circle(screen, color, (cx, cy), CELL // 2 - 2)
        tip_x = cx + a["dx"] * (CELL // 4)
        tip_y = cy + a["dy"] * (CELL // 4)
        pygame.draw.circle(screen, (255, 255, 255), (tip_x, tip_y), 3)

    # draw stack badges (×N) for positions with multiple agents
    pos_counts = {}
    for a in agents:
        if not a["alive"]:
            continue
        key = (a["x"], a["y"])
        pos_counts[key] = pos_counts.get(key, 0) + 1
    badge_font = pygame.font.SysFont("consolas", 10, bold=True)
    for (px, py), count in pos_counts.items():
        if count > 1:
            bx = px * CELL + CELL - 8
            by = py * CELL
            badge = badge_font.render(f"×{count}", True, (255, 255, 255))
            # dark background for readability
            pygame.draw.rect(screen, (30, 30, 40), (bx - 1, by, badge.get_width() + 2, badge.get_height()))
            screen.blit(badge, (bx, by))


def draw_preview_cell(screen, rx, ry, cell, pc):
    """Draw a mini cell/sandwich in the preview panel."""
    if isinstance(cell, tuple):
        n = len(cell)
        for i, color in enumerate(cell):
            sy = ry + (pc * i) // n
            sh = (pc * (i + 1)) // n - (pc * i) // n
            pygame.draw.rect(screen, WCOLOR[color], (rx, sy, pc, sh))
            if i > 0 and cell[i] == cell[i-1]:
                div_y = ry + (pc * i) // n
                pygame.draw.line(screen, (30, 30, 40), (rx + 1, div_y), (rx + pc - 2, div_y))
    elif cell in WCOLOR:
        pygame.draw.rect(screen, WCOLOR[cell], (rx, ry, pc, pc))
        if cell in FIXED_TYPES:
            pygame.draw.rect(screen, (255,255,255), (rx+2, ry+2, pc-4, pc-4), 1)


def draw_shape_preview(screen, font_sm, level, px, y):
    cells = level["cells"]

    if "agents" in level:
        agent_defs = level["agents"]
    else:
        agent_defs = [{"x": level["start"][0], "y": level["start"][1],
                       "dx": level["dir"][0], "dy": level["dir"][1]}]

    all_x = [x for x, _, _ in cells] + [a["x"] for a in agent_defs]
    all_y = [y_ for _, y_, _ in cells] + [a["y"] for a in agent_defs]
    min_x, min_y = min(all_x), min(all_y)
    max_x_cell = max(all_x)
    max_y_cell = max(all_y)
    shape_w = max_x_cell - min_x + 1
    shape_h = max_y_cell - min_y + 1

    # scale preview to fit panel width and a max height
    max_pw = PANEL_W - 28
    max_ph = 160
    gap = 1
    pc = min(12, (max_pw - gap * (shape_w - 1)) // shape_w,
                 (max_ph - gap * (shape_h - 1)) // shape_h)
    pc = max(pc, 3)  # minimum visible size

    for cx, cy, color in cells:
        rx = px + (cx - min_x) * (pc + gap)
        ry = y + (cy - min_y) * (pc + gap)
        draw_preview_cell(screen, rx, ry, color, pc)

    for ad in agent_defs:
        adx, ady = ad["dx"], ad["dy"]
        ax = px + (ad["x"] - min_x) * (pc + gap) + pc // 2
        ay = y + (ad["y"] - min_y) * (pc + gap) + pc // 2
        r = pc // 2
        tip = (ax + adx * r, ay + ady * r)
        p1 = (ax + ady * r * 0.6, ay - adx * r * 0.6)
        p2 = (ax - ady * r * 0.6, ay + adx * r * 0.6)
        pygame.draw.polygon(screen, AGENT_COLOR, [tip, p1, p2])

    preview_h = shape_h * (pc + gap)
    return y + preview_h + 4


def draw_panel(screen, font, font_sm, verbs_list, active_team, n_teams, step, agents,
               total_spawned, peak_pop, walls_left, walls_start, paused, mouse_pos, level_idx,
               evil_rules=None, is_testing=False):
    px = GRID_PX_W
    pygame.draw.rect(screen, PANEL_BG, (px, 0, PANEL_W, WIN_H))
    level = LEVELS[level_idx % NUM_LEVELS]
    is_intercept = level.get("mode") == "intercept"

    y = 10
    screen.blit(font.render("REPLIC8", True, TEXT_COLOR), (px + 10, y))
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
    evil_alive = sum(1 for a in agents if a.get("evil") and a.get("alive", True))
    hero_alive = sum(1 for a in agents if not a.get("evil") and a.get("alive", True))

    if is_intercept:
        if evil_alive == 0 and step > 0:
            msg, color = "INTERCEPTED!", STATUS_GREEN
            sub_msg = "All threats neutralized. Press N."
        elif hero_alive == 0 and step > 0:
            msg, color = "HERO DISSOLVED", STATUS_RED
            sub_msg = "Your agent dissolved. Try again (R)."
        elif step >= MAX_STEPS:
            msg, color = "TIME'S UP", STATUS_RED
        elif paused and step == 0:
            msg, color = "INTERCEPT MODE", STATUS_YELLOW
            sub_msg = "Route the evil agents to dissolve."
        elif paused:
            msg, color = "PAUSED", STATUS_YELLOW
        else:
            msg, color = f"EVIL: {evil_alive} remaining", STATUS_RED
    elif level.get("mode") == "place_agent" and paused and step == 0:
        max_a = level.get("max_agents", 1)
        placed = len([a for a in agents if a.get("alive", True)])
        msg, color = "PLACE AGENT MODE", STATUS_YELLOW
        if placed == 0:
            sub_msg = f"Click grid to place agent ({max_a} max)"
        else:
            sub_msg = f"{placed}/{max_a} placed. Click=rotate. SPACE=go."
    elif walls_left == 0 and len(agents) == 0:
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
    if is_testing:
        screen.blit(font_sm.render("E=back to editor  ESC=editor", True, (255, 200, 80)), (px + 12, y + 15))
    else:
        screen.blit(font_sm.render("N next   P prev   ESC quit", True, TEXT_DIM), (px + 12, y + 15))
    if paused and step > 0:
        screen.blit(font_sm.render("<< >>  step frame by frame", True, (150, 180, 220)), (px + 12, y + 30))
        y += 48
    else:
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

    # team tabs (only for per-agent-rule levels, not place_agent)
    tab_rects = []
    is_place = level.get("mode") == "place_agent"
    if is_place:
        # no clickable rules — fixed rules shown below
        pass
    elif n_teams > 1:
        screen.blit(font_sm.render("AGENT RULES (TAB to switch):", True, TEXT_COLOR), (px + 12, y))
        y += 18
        tab_w = (PANEL_W - 24) // n_teams
        for ti in range(n_teams):
            tx = px + 8 + ti * (tab_w + 4)
            active = ti == active_team
            tc = TEAM_COLORS[ti % len(TEAM_COLORS)]
            bg = tc if active else (40, 40, 55)
            fg = (0, 0, 0) if active else tc
            pygame.draw.rect(screen, bg, (tx, y, tab_w, 22))
            label = f" {TEAM_NAMES[ti % len(TEAM_NAMES)]}"
            screen.blit(font_sm.render(label, True, fg), (tx + 4, y + 3))
            tab_rects.append((tx, y, tab_w, 22, ti))
        y += 28
    else:
        screen.blit(font_sm.render("RULES (click to cycle):", True, TEXT_COLOR), (px + 12, y))
        y += 20

    verbs = verbs_list[active_team] if verbs_list else default_verbs()
    btn_rects = []

    # show buttons only for assignable colors actually used in this level
    level = LEVELS[level_idx % len(LEVELS)]
    level_colors = set()
    for _, _, c in level["cells"]:
        if isinstance(c, tuple):
            level_colors.update(c)
        else:
            level_colors.add(c)
    active_assignable = [c for c in ASSIGNABLE_TYPES if c in level_colors]
    for ec in EDITOR_ASSIGNABLE:
        if ec in level_colors:
            active_assignable.append(ec)

    for wall_type in ([] if is_place else active_assignable):
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

        # show disabled verbs indicator
        disabled = get_disabled_verbs(level).get(wall_type, [])
        if disabled:
            disabled_names = [VERB_NAMES[v] for v in disabled]
            dim_text = "\u2718 " + " ".join(disabled_names)
            screen.blit(font_sm.render(dim_text, True, (80, 50, 50)), (bx + 36, by + 21))

        btn_rects.append((bx, by, bw, bh, wall_type))
        y += bh + 5

    # fixed rules display (read-only) for intercept or place_agent
    is_place = level.get("mode") == "place_agent"
    if (is_intercept or is_place) and evil_rules:
        y += 8
        rules_label = "ENEMY RULES (fixed):" if is_intercept else "RULES (fixed):"
        rules_color = EVIL_COLOR if is_intercept else STATUS_YELLOW
        screen.blit(font_sm.render(rules_label, True, rules_color), (px + 12, y))
        y += 18
        for wall_type in active_assignable:
            cname = COLOR_NAMES[wall_type]
            verb = evil_rules.get(wall_type, VERB_PASS)
            vname = VERB_NAMES[verb]
            bx, by_r = px + 8, y
            bw, bh = PANEL_W - 16, 28
            pygame.draw.rect(screen, (35, 25, 25), (bx, by_r, bw, bh))
            pygame.draw.rect(screen, WCOLOR[wall_type], (bx + 4, by_r + 4, 20, bh - 8))
            arrow_text = f"{cname}  \u2192  "
            screen.blit(font_sm.render(arrow_text, True, (140, 100, 100)), (bx + 30, by_r + 6))
            vx = bx + 30 + font_sm.size(arrow_text)[0]
            screen.blit(font_sm.render(vname, True, EVIL_COLOR), (vx, by_r + 6))
            y += bh + 3

    return btn_rects, tab_rects


# ── save / load ──

SAVE_PATH = os.path.expanduser("~/.tgusf_save.json")

def save_progress(stars, sim_speed, show_gridlines, packs=None):
    data = {"stars": stars, "speed": sim_speed, "gridlines": show_gridlines}
    if packs:
        # store packs as serialized codes to keep save file clean
        data["packs"] = [{"name": p["name"], "code": p["code"]} for p in packs]
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_progress():
    try:
        with open(SAVE_PATH) as f:
            return json.load(f)
    except Exception:
        return None


# ── screen draw functions ──

SPEED_LABELS = ["Slow", "Normal", "Fast"]
SPEED_MS     = [400, 200, 80]

STAR_CHARS = ["☆☆☆", "★☆☆", "★★☆", "★★★"]
STAR_COLORS = [
    (60, 60, 70),     # 0: unplayed grey
    (100, 180, 100),  # 1: cleared green
    (220, 200, 60),   # 2: perfect gold
    (255, 220, 80),   # 3: efficient bright gold
]


def draw_title_screen(screen, font, font_sm, font_lg, mouse_pos, tick):
    screen.fill(BG)
    cx = WIN_W // 2

    # title
    title = font_lg.render("REPLIC8", True, (220, 210, 70))
    screen.blit(title, (cx - title.get_width() // 2, 140))

    sub = font_sm.render("Set the rules. Watch them propagate.", True, TEXT_DIM)
    screen.blit(sub, (cx - sub.get_width() // 2, 200))

    # animated replicator dots
    y_line = 260
    n_dots = 5
    for i in range(n_dots):
        dx = ((tick * 2 + i * 60) % (WIN_W + 40)) - 20
        color = TEAM_COLORS[i % len(TEAM_COLORS)]
        pygame.draw.circle(screen, color, (dx, y_line), 6)
        pygame.draw.circle(screen, (255, 255, 255), (dx + 4, y_line), 2)

    # menu buttons
    btn_rects = []
    btns = [("PLAY", "play"), ("EDITOR", "editor"), ("SETTINGS", "settings")]
    for i, (label, action) in enumerate(btns):
        bw, bh = 200, 40
        bx = cx - bw // 2
        by = 310 + i * 55
        hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
        bg = (60, 60, 80) if hovered else (40, 40, 55)
        pygame.draw.rect(screen, bg, (bx, by, bw, bh), border_radius=6)
        pygame.draw.rect(screen, (100, 100, 120), (bx, by, bw, bh), 1, border_radius=6)
        txt = font.render(label, True, TEXT_COLOR)
        screen.blit(txt, (cx - txt.get_width() // 2, by + 10))
        btn_rects.append((bx, by, bw, bh, action))

    # community call to action
    cta_lines = [
        "Design levels in the editor (E) and share codes on Discord!",
        "Best community levels get included — designers get free Steam copy.",
    ]
    cta_y = WIN_H - 70
    for cta_line in cta_lines:
        cta = font_sm.render(cta_line, True, (70, 90, 110))
        screen.blit(cta, (cx - cta.get_width() // 2, cta_y))
        cta_y += 16

    # version
    ver = font_sm.render("v1.0 — Press E for editor anytime", True, (60, 60, 70))
    screen.blit(ver, (cx - ver.get_width() // 2, WIN_H - 30))

    return btn_rects


def draw_level_select(screen, font, font_sm, stars, mouse_pos, scroll_y,
                      active_tab="campaign", packs=None, pack_idx=0):
    """Draw level select with Campaign / Community Packs tabs."""
    screen.fill(BG)
    cx = WIN_W // 2
    if packs is None:
        packs = []

    # tabs: Campaign | Community Packs
    tab_rects = []
    tabs = [("Campaign", "campaign"), ("Community Packs", "packs")]
    tab_w = 160
    tab_y = 10
    for i, (label, key) in enumerate(tabs):
        tx = cx - tab_w + i * (tab_w + 4)
        active = key == active_tab
        bg = (60, 60, 80) if active else (35, 35, 48)
        fg = TEXT_COLOR if active else TEXT_DIM
        pygame.draw.rect(screen, bg, (tx, tab_y, tab_w, 24), border_radius=4)
        if active:
            pygame.draw.rect(screen, (100, 160, 220), (tx, tab_y, tab_w, 24), 1, border_radius=4)
        txt = font_sm.render(label, True, fg)
        screen.blit(txt, (tx + tab_w // 2 - txt.get_width() // 2, tab_y + 4))
        tab_rects.append((tx, tab_y, tab_w, 24, key))

    btn_rects = []
    action_rects = []

    if active_tab == "campaign":
        hint = font_sm.render("Click to play — ESC back to menu", True, TEXT_DIM)
        screen.blit(hint, (cx - hint.get_width() // 2, 42))

        cols = 8
        tile_w, tile_h = 80, 65
        gap = 10
        grid_w = cols * (tile_w + gap) - gap
        ox = (WIN_W - grid_w) // 2
        oy = 70 - scroll_y

        for i in range(NUM_LEVELS):
            col = i % cols
            row = i // cols
            tx = ox + col * (tile_w + gap)
            ty = oy + row * (tile_h + gap)

            if ty + tile_h < 60 or ty > WIN_H:
                continue

            star = stars[i] if i < len(stars) else 0
            hovered = tx <= mouse_pos[0] < tx + tile_w and ty <= mouse_pos[1] < ty + tile_h

            if hovered:
                bg = (55, 55, 75)
            elif star >= 3:
                bg = (40, 45, 30)
            elif star >= 1:
                bg = (35, 40, 35)
            else:
                bg = (30, 30, 40)

            pygame.draw.rect(screen, bg, (tx, ty, tile_w, tile_h), border_radius=4)
            pygame.draw.rect(screen, (70, 70, 85), (tx, ty, tile_w, tile_h), 1, border_radius=4)

            num = font.render(str(i + 1), True, TEXT_COLOR)
            screen.blit(num, (tx + tile_w // 2 - num.get_width() // 2, ty + 6))

            star_text = STAR_CHARS[min(star, 3)]
            star_color = STAR_COLORS[min(star, 3)]
            st = font_sm.render(star_text, True, star_color)
            screen.blit(st, (tx + tile_w // 2 - st.get_width() // 2, ty + 38))

            btn_rects.append((tx, ty, tile_w, tile_h, ("level", i)))

    elif active_tab == "packs":
        # load pack button
        by = 46
        for label, action in [("Load Pack (V)", "load_pack"), ("Share Pack (C)", "share_pack")]:
            bw, bh = 150, 26
            bx = cx - bw - 5 if action == "load_pack" else cx + 5
            hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
            bg = (55, 55, 70) if hovered else (40, 40, 52)
            pygame.draw.rect(screen, bg, (bx, by, bw, bh), border_radius=4)
            txt = font_sm.render(label, True, TEXT_COLOR)
            screen.blit(txt, (bx + bw // 2 - txt.get_width() // 2, by + 5))
            action_rects.append((bx, by, bw, bh, action))

        oy = 82

        if not packs:
            msg = font_sm.render("No packs loaded yet. Press V to paste a pack code.", True, TEXT_DIM)
            screen.blit(msg, (cx - msg.get_width() // 2, oy + 40))
        else:
            for pi, pack in enumerate(packs):
                # pack header
                py = oy + pi * 200 - scroll_y
                if py > WIN_H or py + 200 < 80:
                    continue

                is_active = pi == pack_idx
                # pack name bar
                bar_bg = (50, 60, 80) if is_active else (35, 35, 48)
                pygame.draw.rect(screen, bar_bg, (40, py, WIN_W - 80, 28), border_radius=4)
                name_txt = font.render(pack["name"], True, TEXT_COLOR if is_active else TEXT_DIM)
                screen.blit(name_txt, (50, py + 5))
                n_levels = len(pack.get("levels", []))
                count_txt = font_sm.render(f"{n_levels} levels", True, TEXT_DIM)
                screen.blit(count_txt, (WIN_W - 130, py + 7))

                # delete button
                dbx = WIN_W - 75
                dby = py + 2
                dbw, dbh = 30, 22
                d_hov = dbx <= mouse_pos[0] < dbx + dbw and dby <= mouse_pos[1] < dby + dbh
                d_bg = (180, 50, 50) if d_hov else (80, 40, 40)
                pygame.draw.rect(screen, d_bg, (dbx, dby, dbw, dbh), border_radius=3)
                screen.blit(font_sm.render("X", True, TEXT_COLOR), (dbx + 10, dby + 3))
                action_rects.append((dbx, dby, dbw, dbh, ("delete_pack", pi)))

                # pack level tiles
                levels = pack.get("levels", [])
                for li, level in enumerate(levels):
                    col = li % 8
                    row = li // 8
                    tx = 50 + col * 70
                    ty = py + 34 + row * 50

                    if ty + 45 < 80 or ty > WIN_H:
                        continue

                    hovered = tx <= mouse_pos[0] < tx + 60 and ty <= mouse_pos[1] < ty + 42
                    bg = (55, 55, 75) if hovered else (35, 35, 48)
                    pygame.draw.rect(screen, bg, (tx, ty, 60, 42), border_radius=3)
                    pygame.draw.rect(screen, (70, 70, 85), (tx, ty, 60, 42), 1, border_radius=3)

                    num = font_sm.render(f"P{pi+1}.{li+1}", True, TEXT_COLOR)
                    screen.blit(num, (tx + 30 - num.get_width() // 2, ty + 4))

                    nc = len(level.get("cells", []))
                    info = font_sm.render(f"{nc}c", True, TEXT_DIM)
                    screen.blit(info, (tx + 30 - info.get_width() // 2, ty + 22))

                    btn_rects.append((tx, ty, 60, 42, ("pack_level", pi, li)))

    return btn_rects, tab_rects, action_rects


def draw_settings_screen(screen, font, font_sm, sim_speed, show_gridlines, mouse_pos, sound_on=True):
    screen.fill(BG)
    cx = WIN_W // 2

    title = font.render("SETTINGS", True, TEXT_COLOR)
    screen.blit(title, (cx - title.get_width() // 2, 80))

    btn_rects = []
    y = 160

    # sim speed
    screen.blit(font_sm.render("Sim Speed:", True, TEXT_DIM), (cx - 140, y))
    for i, label in enumerate(SPEED_LABELS):
        bw, bh = 80, 30
        bx = cx - 140 + 100 + i * (bw + 10)
        hovered = bx <= mouse_pos[0] < bx + bw and y <= mouse_pos[1] < y + bh
        active = i == sim_speed
        bg = (80, 180, 100) if active else (55, 55, 70) if hovered else (40, 40, 52)
        pygame.draw.rect(screen, bg, (bx, y, bw, bh), border_radius=4)
        txt = font_sm.render(label, True, (0, 0, 0) if active else TEXT_COLOR)
        screen.blit(txt, (bx + bw // 2 - txt.get_width() // 2, y + 7))
        btn_rects.append((bx, y, bw, bh, ("speed", i)))
    y += 55

    # grid lines
    screen.blit(font_sm.render("Grid Lines:", True, TEXT_DIM), (cx - 140, y))
    for i, label in enumerate(["Off", "On"]):
        bw, bh = 80, 30
        bx = cx - 140 + 100 + i * (bw + 10)
        hovered = bx <= mouse_pos[0] < bx + bw and y <= mouse_pos[1] < y + bh
        active = (i == 1) == show_gridlines
        bg = (80, 180, 100) if active else (55, 55, 70) if hovered else (40, 40, 52)
        pygame.draw.rect(screen, bg, (bx, y, bw, bh), border_radius=4)
        txt = font_sm.render(label, True, (0, 0, 0) if active else TEXT_COLOR)
        screen.blit(txt, (bx + bw // 2 - txt.get_width() // 2, y + 7))
        btn_rects.append((bx, y, bw, bh, ("gridlines", i == 1)))
    y += 55

    # sound
    screen.blit(font_sm.render("Sound:", True, TEXT_DIM), (cx - 140, y))
    for i, label in enumerate(["Off", "On"]):
        bw2, bh2 = 80, 30
        bx2 = cx - 140 + 100 + i * (bw2 + 10)
        hovered = bx2 <= mouse_pos[0] < bx2 + bw2 and y <= mouse_pos[1] < y + bh2
        active = (i == 1) == sound_on
        bg = (80, 180, 100) if active else (55, 55, 70) if hovered else (40, 40, 52)
        pygame.draw.rect(screen, bg, (bx2, y, bw2, bh2), border_radius=4)
        txt = font_sm.render(label, True, (0, 0, 0) if active else TEXT_COLOR)
        screen.blit(txt, (bx2 + bw2 // 2 - txt.get_width() // 2, y + 7))
        btn_rects.append((bx2, y, bw2, bh2, ("sound", i == 1)))
    y += 55

    # reset progress
    bw, bh = 180, 34
    bx = cx - bw // 2
    hovered = bx <= mouse_pos[0] < bx + bw and y <= mouse_pos[1] < y + bh
    bg = (180, 60, 60) if hovered else (80, 40, 40)
    pygame.draw.rect(screen, bg, (bx, y, bw, bh), border_radius=4)
    txt = font_sm.render("Reset Progress", True, TEXT_COLOR)
    screen.blit(txt, (cx - txt.get_width() // 2, y + 8))
    btn_rects.append((bx, y, bw, bh, ("reset", True)))
    y += 55

    # back
    bw, bh = 120, 34
    bx = cx - bw // 2
    by = y + 20
    hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
    bg = (55, 55, 70) if hovered else (40, 40, 52)
    pygame.draw.rect(screen, bg, (bx, by, bw, bh), border_radius=4)
    txt = font_sm.render("Back", True, TEXT_COLOR)
    screen.blit(txt, (cx - txt.get_width() // 2, by + 8))
    btn_rects.append((bx, by, bw, bh, ("back", True)))

    return btn_rects


def draw_pause_overlay(screen, font, font_sm, mouse_pos):
    # semi-transparent overlay
    overlay = pygame.Surface((WIN_W, WIN_H))
    overlay.set_alpha(160)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    cx = WIN_W // 2
    cy = WIN_H // 2

    title = font.render("PAUSED", True, STATUS_YELLOW)
    screen.blit(title, (cx - title.get_width() // 2, cy - 80))

    btn_rects = []
    btns = [("Resume (SPACE)", "resume"), ("Restart (R)", "restart"),
            ("Level Select (L)", "levels"), ("Quit (ESC)", "quit")]
    for i, (label, action) in enumerate(btns):
        bw, bh = 220, 32
        bx = cx - bw // 2
        by = cy - 30 + i * 42
        hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
        bg = (55, 55, 75) if hovered else (35, 35, 50)
        pygame.draw.rect(screen, bg, (bx, by, bw, bh), border_radius=4)
        txt = font_sm.render(label, True, TEXT_COLOR)
        screen.blit(txt, (cx - txt.get_width() // 2, by + 7))
        btn_rects.append((bx, by, bw, bh, action))

    return btn_rects


def calc_stars(walls_left, agents_alive, step, level):
    """Calculate star rating: 0=fail, 1=cleared, 2=perfect, 3=efficient."""
    if walls_left > 0:
        return 0
    if agents_alive > 0:
        return 1
    # perfect — check efficiency
    par = level.get("par", len(level.get("cells", [])) * 3)
    if step <= par:
        return 3
    return 2


# ── main ──

async def main():
    global LEVELS, NUM_LEVELS

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Replic8")
    clock = pygame.time.Clock()
    font    = pygame.font.SysFont("consolas", 15)
    font_sm = pygame.font.SysFont("consolas", 13)
    font_lg = pygame.font.SysFont("consolas", 26, bold=True)

    # ── sound ──
    sounds = None
    if _HAS_SOUND:
        try:
            sounds = GameSounds()
        except Exception:
            sounds = None

    # ── load external levels from levels.txt ──
    ext_codes = _load_external_levels()
    ext_levels = []
    for code in ext_codes:
        lev = deserialize_level(code)
        if lev:
            ext_levels.append(lev)
    if ext_levels:
        LEVELS = list(LEVELS) + ext_levels
        NUM_LEVELS = len(LEVELS)

    # ── sound ──
    sounds = None
    if _HAS_SOUND:
        try:
            sounds = GameSounds()
        except Exception as e:
            print(f"Sound init failed: {e}")
            sounds = None

    # ── screen state ──
    screen_mode = "title"  # "title" | "play" | "level_select" | "settings"
    stars = [0] * NUM_LEVELS
    sim_speed = 1
    show_gridlines = False
    show_pause_menu = False
    level_select_scroll = 0
    level_select_tab = "campaign"  # "campaign" | "packs"
    community_packs = []  # list of {"name": str, "code": str, "levels": [level_dicts]}
    pack_idx = 0
    level_select_tab_rects = []
    level_select_action_rects = []

    title_tick = 0

    # load saved progress
    saved = load_progress()
    if saved:
        for i, s in enumerate(saved.get("stars", [])):
            if i < len(stars):
                stars[i] = s
        sim_speed = saved.get("speed", 1)
        show_gridlines = saved.get("gridlines", False)
        # load saved packs
        for p in saved.get("packs", []):
            name, levels = deserialize_pack(p.get("code", ""))
            if levels:
                community_packs.append({"name": name, "code": p["code"], "levels": levels})

    level_idx = 0
    active_team = 0

    def default_verbs():
        v = {}
        for c in ASSIGNABLE_TYPES:
            v[c] = VERB_PASS
        for ec in EDITOR_ASSIGNABLE:
            v[ec] = VERB_PASS
        return v

    def num_teams():
        level = LEVELS[level_idx]
        if level.get("per_agent_rules"):
            if "agents" in level:
                return len(level["agents"])
            return 1
        return 1

    verbs_list = [default_verbs()]

    grid, agents, underneath = make_grid(LEVELS[level_idx])
    walls_start = count_walls(grid, underneath)
    paused = True
    step = 0
    total_spawned = len(agents)
    peak_pop = len(agents)
    last_sim_tick = 0
    btn_hit_rects = []
    tab_hit_rects = []

    history = {}  # dict: step_number -> (grid_copy, agents_copy, underneath_copy)
    MAX_HISTORY = 200

    def save_snapshot():
        """Save current state for rewind, keyed by step number."""
        import copy
        history[step] = (copy.deepcopy(grid), copy.deepcopy(agents), copy.deepcopy(underneath))
        # trim old entries if too many
        if len(history) > MAX_HISTORY:
            oldest = min(history.keys())
            del history[oldest]

    def restore_snapshot(target_step):
        """Restore state from history by step number."""
        nonlocal grid, agents, underneath, step, total_spawned, peak_pop
        if target_step not in history:
            return False
        import copy
        g, ag, und = history[target_step]
        grid[:] = copy.deepcopy(g)
        agents.clear()
        agents.extend(copy.deepcopy(ag))
        underneath.clear()
        underneath.update(copy.deepcopy(und))
        step = target_step
        total_spawned = max(len(agents), 1)
        peak_pop = max(len(agents), 1)
        return True

    def reset_level():
        nonlocal grid, agents, underneath, walls_start, paused, step, total_spawned, peak_pop, place_agent_pos
        level = LEVELS[level_idx % NUM_LEVELS]

        if level.get("mode") == "place_agent":
            # load grid but no agents — player places them
            grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
            cells = level["cells"]
            xs = [x for x, y, c in cells]; ys = [y for x, y, c in cells]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            shape_w = max_x - min_x + 1; shape_h = max_y - min_y + 1
            ox = (GRID_W - shape_w) // 2 - min_x
            oy = (GRID_H - shape_h) // 2 - min_y
            for x, y, c in cells:
                grid[y + oy][x + ox] = c
            agents = []
            place_agent_pos = []
            underneath = {}
        else:
            grid, agents, underneath = make_grid(level)
            place_agent_pos = []

        walls_start = count_walls(grid, underneath)
        paused = True
        step = 0
        total_spawned = max(len(agents), 1)
        peak_pop = max(len(agents), 1)
        history.clear()
        step = 0
        save_snapshot()  # save initial state as step 0

    def change_level(new_idx):
        nonlocal level_idx, verbs_list, active_team, screen_mode
        level_idx = new_idx % NUM_LEVELS
        nt = num_teams()
        verbs_list = [default_verbs() for _ in range(nt)]
        active_team = 0
        screen_mode = "play"
        reset_level()

    # place_agent mode state
    place_agent_pos = []  # list of {"x","y","dx","dy"} for player-placed agents

    def is_place_agent():
        return LEVELS[level_idx % NUM_LEVELS].get("mode") == "place_agent"

    def start_level(idx):
        nonlocal level_idx, verbs_list, active_team, screen_mode, show_pause_menu, place_agent_pos
        level_idx = idx % NUM_LEVELS
        level = LEVELS[level_idx]
        screen_mode = "play"
        show_pause_menu = False
        place_agent_pos = []

        if level.get("mode") == "place_agent":
            # fixed rules — load from level
            fr = level.get("fixed_rules", {})
            verbs_list = [fr]
            active_team = 0
        else:
            nt = num_teams()
            dv = get_disabled_verbs(level)
            vl = []
            for _ in range(nt):
                v = default_verbs()
                # if Pass is disabled for a color, start at first allowed verb
                for color, disabled in dv.items():
                    if VERB_PASS in disabled:
                        v[color] = cycle_verb(VERB_PASS, disabled)
                vl.append(v)
            verbs_list = vl
            active_team = 0
        reset_level()

    # ── editor state ──
    editor_mode = False
    editor_state = {
        "selected": WALL_RED,
        "sandwich_stack": [],
        "num_agents": 1,
        "per_agent": False,
        "agent_place_mode": False,
        "status_msg": "",
        "level_code": "",
        "undo": [],
        "clear_pending": False,
        "clear_tick": 0,
    }
    editor_agents = []  # agent start positions in editor
    editor_palette_rects = []
    editor_action_rects = []

    def editor_save_undo():
        import copy
        snap = (copy.deepcopy(grid), copy.deepcopy(editor_agents))
        editor_state["undo"].append(snap)
        if len(editor_state["undo"]) > 50:
            editor_state["undo"].pop(0)

    def editor_undo():
        nonlocal grid, editor_agents
        if editor_state["undo"]:
            grid, editor_agents = editor_state["undo"].pop()

    def enter_editor():
        nonlocal editor_mode, screen_mode, grid, editor_agents, underneath
        editor_mode = True
        screen_mode = "play"
        grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
        editor_agents = []
        underneath = {}
        editor_state["undo"] = []
        editor_state["status_msg"] = "Editor mode. Place cells, then T to test."
        editor_state["level_code"] = ""
        editor_state["sandwich_stack"] = []

    def exit_editor():
        nonlocal editor_mode, screen_mode
        editor_mode = False
        screen_mode = "play"
        reset_level()

    testing_editor_level = False
    saved_editor_grid = None
    saved_editor_agents = None
    saved_editor_test_level = None

    def editor_test():
        """Build a level from grid, switch to play mode. Preserves editor state."""
        nonlocal editor_mode, screen_mode, grid, agents, underneath, walls_start
        nonlocal paused, step, total_spawned, peak_pop
        nonlocal level_idx, verbs_list, active_team
        nonlocal testing_editor_level, saved_editor_grid, saved_editor_agents, saved_editor_test_level
        import copy

        if not editor_agents:
            editor_state["status_msg"] = "Place at least 1 agent (Shift+click)"
            return
        if count_walls(grid, {}) == 0:
            editor_state["status_msg"] = "Place some cells first!"
            return

        # save editor state for returning
        saved_editor_grid = copy.deepcopy(grid)
        saved_editor_agents = copy.deepcopy(editor_agents)

        # build level from current grid
        level = grid_to_level(grid, [], {})
        if not level:
            editor_state["status_msg"] = "No cells to test"
            return
        level["agents"] = [{"x": a["x"], "y": a["y"], "dx": a["dx"], "dy": a["dy"],
                            "team": a.get("team", 0)} for a in editor_agents]
        if editor_state["per_agent"]:
            level["per_agent_rules"] = True

        saved_editor_test_level = level

        # add as temp level and switch to it
        if len(LEVELS) > NUM_LEVELS:
            LEVELS.pop()
        LEVELS.append(level)
        level_idx = len(LEVELS) - 1
        nt = len(set(a.get("team", 0) for a in editor_agents)) if editor_state["per_agent"] else 1
        verbs_list = [default_verbs() for _ in range(nt)]
        active_team = 0

        grid, agents, underneath = make_grid(level)
        walls_start = count_walls(grid, underneath)
        paused = True
        step = 0
        total_spawned = len(agents)
        peak_pop = len(agents)
        editor_mode = False
        screen_mode = "play"
        testing_editor_level = True
        editor_state["status_msg"] = ""

    def return_to_editor():
        """Return from testing to the editor with grid preserved."""
        nonlocal editor_mode, screen_mode, grid, editor_agents, underneath
        nonlocal testing_editor_level
        import copy
        editor_mode = True
        screen_mode = "play"
        testing_editor_level = False
        if saved_editor_grid:
            grid = copy.deepcopy(saved_editor_grid)
            editor_agents[:] = copy.deepcopy(saved_editor_agents) if saved_editor_agents else []
        underneath = {}
        editor_state["status_msg"] = "Back in editor. E=exit, T=test again"

    def reset_test_level():
        """Reset the test level (re-run from start, keep verbs)."""
        nonlocal grid, agents, underneath, walls_start, paused, step, total_spawned, peak_pop
        if saved_editor_test_level:
            grid, agents, underneath = make_grid(saved_editor_test_level)
            walls_start = count_walls(grid, underneath)
            paused = True
            step = 0
            total_spawned = len(agents)
            peak_pop = len(agents)

    def editor_copy():
        level = grid_to_level(grid, [], {})
        if not level:
            editor_state["status_msg"] = "No cells to copy!"
            return
        if not editor_agents:
            editor_state["status_msg"] = "Place agent first! (click PLACE AGENT)"
            return
        level["agents"] = [{"x": a["x"], "y": a["y"], "dx": a["dx"], "dy": a["dy"],
                            "team": a.get("team", 0)} for a in editor_agents]
        if editor_state["per_agent"]:
            level["per_agent_rules"] = True
        code = serialize_level(level)
        if code:
            copied = False
            try:
                pygame.scrap.put(pygame.SCRAP_TEXT, code.encode())
                copied = True
            except Exception:
                pass
            # also try pyperclip-style subprocess fallback on macOS
            if not copied:
                try:
                    import subprocess
                    subprocess.run(["pbcopy"], input=code.encode(), check=True)
                    copied = True
                except Exception:
                    pass
            editor_state["level_code"] = code
            if copied:
                editor_state["status_msg"] = f"Copied! ({len(code)} chars)"
            else:
                editor_state["status_msg"] = f"Code shown below (copy manually)"

    def editor_paste():
        nonlocal grid, editor_agents, underneath
        code = None
        # try pygame scrap first
        try:
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if raw:
                code = raw.decode().strip().rstrip('\x00')
        except Exception:
            pass
        # fallback: macOS pbpaste
        if not code:
            try:
                import subprocess
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    code = result.stdout.strip()
            except Exception:
                pass
        if not code:
            editor_state["status_msg"] = "Clipboard empty"
            return

        level = deserialize_level(code)
        if not level:
            editor_state["status_msg"] = "Invalid level code"
            return

        editor_save_undo()
        grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
        underneath = {}

        # center the level
        cells = level["cells"]
        xs = [x for x, y, c in cells]; ys = [y for x, y, c in cells]
        ox = (GRID_W - (max(xs) - min(xs) + 1)) // 2 - min(xs)
        oy = (GRID_H - (max(ys) - min(ys) + 1)) // 2 - min(ys)

        for x, y, c in cells:
            gx, gy = x + ox, y + oy
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                grid[gy][gx] = c

        editor_agents = []
        for a in level.get("agents", []):
            editor_agents.append({"x": a["x"] + ox, "y": a["y"] + oy,
                                  "dx": a["dx"], "dy": a["dy"], "team": a.get("team", 0)})

        editor_state["per_agent"] = level.get("per_agent_rules", False)
        editor_state["num_agents"] = len(editor_agents)
        editor_state["level_code"] = code
        editor_state["status_msg"] = "Level loaded OK"

    # init scrap for clipboard
    try:
        pygame.scrap.init()
    except Exception:
        pass

    # hit rect storage
    title_btn_rects = []
    level_select_rects = []
    settings_rects = []
    pause_btn_rects = []

    running = True
    while running:
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        title_tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_progress(stars, sim_speed, show_gridlines, community_packs)
                running = False

            elif event.type == pygame.KEYDOWN:

                # ── title screen ──
                if screen_mode == "title":
                    if event.key == pygame.K_ESCAPE:
                        save_progress(stars, sim_speed, show_gridlines, community_packs)
                        running = False
                    elif event.key == pygame.K_e:
                        enter_editor()
                    elif event.key == pygame.K_RETURN:
                        screen_mode = "level_select"

                # ── level select ──
                elif screen_mode == "level_select":
                    if event.key == pygame.K_ESCAPE:
                        screen_mode = "title"
                    elif event.key == pygame.K_v:
                        # paste pack code
                        try:
                            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                            if raw:
                                code = raw.decode().strip().rstrip('\x00')
                                name, levels = deserialize_pack(code)
                                if levels:
                                    community_packs.append({"name": name, "code": code, "levels": levels})
                                    level_select_tab = "packs"
                                    save_progress(stars, sim_speed, show_gridlines, community_packs)
                        except Exception:
                            pass
                    elif event.key == pygame.K_TAB:
                        level_select_tab = "packs" if level_select_tab == "campaign" else "campaign"
                        level_select_scroll = 0

                # ── settings ──
                elif screen_mode == "settings":
                    if event.key == pygame.K_ESCAPE:
                        save_progress(stars, sim_speed, show_gridlines, community_packs)
                        screen_mode = "title"

                # ── play mode ──
                elif screen_mode == "play":
                    if event.key == pygame.K_ESCAPE:
                        if editor_mode:
                            exit_editor()
                            screen_mode = "level_select"
                        elif testing_editor_level:
                            return_to_editor()
                        elif show_pause_menu:
                            save_progress(stars, sim_speed, show_gridlines, community_packs)
                            screen_mode = "level_select"
                        elif step > 0 and not editor_mode:
                            show_pause_menu = True
                            paused = True
                        else:
                            screen_mode = "level_select"

                    elif event.key == pygame.K_e:
                        if editor_mode:
                            exit_editor()
                            screen_mode = "level_select"
                        elif testing_editor_level:
                            return_to_editor()
                        else:
                            enter_editor()

                    elif editor_mode:
                        if event.key == pygame.K_h:
                            editor_state["show_help"] = not editor_state.get("show_help", False)
                        elif event.key == pygame.K_t:
                            editor_test()
                        elif event.key == pygame.K_c:
                            editor_copy()
                        elif event.key == pygame.K_v:
                            editor_paste()
                        elif event.key == pygame.K_z:
                            editor_undo()
                        elif event.key == pygame.K_x:
                            if editor_state["clear_pending"] and (now - editor_state["clear_tick"]) < 1500:
                                editor_save_undo()
                                grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
                                editor_agents = []
                                editor_state["status_msg"] = "Cleared!"
                                editor_state["clear_pending"] = False
                            else:
                                editor_state["clear_pending"] = True
                                editor_state["clear_tick"] = now
                                editor_state["status_msg"] = "Press X again to confirm clear"
                        elif event.key == pygame.K_s:
                            sel = editor_state["selected"]
                            stack = editor_state["sandwich_stack"]
                            if len(stack) < 3:
                                stack.append(sel)
                                # update brush to current sandwich
                                if len(stack) > 1:
                                    editor_state["brush"] = tuple(stack)
                                else:
                                    editor_state["brush"] = stack[0]
                                editor_state["status_msg"] = f"Stack: {len(stack)} layers. S=add more or click to place"
                            else:
                                editor_state["status_msg"] = "Max 3 layers"
                        elif event.key == pygame.K_d:
                            editor_state["sandwich_stack"] = []
                            editor_state["brush"] = editor_state["selected"]
                            editor_state["status_msg"] = "Stack cleared, brush reset"
                        elif event.key == pygame.K_1:
                            editor_state["num_agents"] = 1
                            editor_state["per_agent"] = False
                        elif event.key == pygame.K_2:
                            editor_state["num_agents"] = 2
                        elif event.key == pygame.K_3:
                            editor_state["num_agents"] = 3
                        elif event.key == pygame.K_4:
                            editor_state["num_agents"] = 4
                        elif event.key == pygame.K_a:
                            editor_state["per_agent"] = not editor_state["per_agent"]
                            editor_state["status_msg"] = f"Per-agent rules: {'ON' if editor_state['per_agent'] else 'OFF'}"

                    elif show_pause_menu:
                        if event.key == pygame.K_SPACE:
                            show_pause_menu = False
                            paused = False
                        elif event.key == pygame.K_r:
                            show_pause_menu = False
                            reset_level()
                        elif event.key == pygame.K_l:
                            show_pause_menu = False
                            screen_mode = "level_select"

                    else:
                        if event.key == pygame.K_SPACE:
                            paused = not paused
                            if sounds and not paused:
                                sounds.play_start()
                        elif event.key == pygame.K_RIGHT:
                            # step forward one tick (auto-pause if running)
                            if not paused:
                                paused = True
                            # simulate one fresh tick
                            cur_level = LEVELS[level_idx % NUM_LEVELS]
                            cur_evil = cur_level.get("evil_rules")
                            wl = count_walls(grid, underneath)
                            go = (wl > 0) and (len(agents) > 0 or step == 0) and (step < MAX_STEPS)
                            if go:
                                agents, spawned, sim_events = sim_step(agents, grid, verbs_list, underneath, cur_evil)
                                step += 1
                                total_spawned += spawned
                                if len(agents) > peak_pop:
                                    peak_pop = len(agents)
                                save_snapshot()
                                if sounds and sim_events["consumed"] > 0:
                                    sounds.play_consume()
                        elif event.key == pygame.K_LEFT:
                            # step backward one tick (auto-pause if running)
                            if not paused:
                                paused = True
                            if step > 0:
                                if not restore_snapshot(step - 1):
                                    # no snapshot for step-1, try step 0
                                    restore_snapshot(0)
                        elif event.key == pygame.K_r:
                            if testing_editor_level:
                                reset_test_level()
                            else:
                                reset_level()
                        elif event.key == pygame.K_n:
                            if not testing_editor_level:
                                change_level(level_idx + 1)
                        elif event.key == pygame.K_p:
                            if not testing_editor_level:
                                change_level(level_idx - 1)
                        elif event.key == pygame.K_l:
                            if testing_editor_level:
                                return_to_editor()
                            else:
                                screen_mode = "level_select"
                        elif event.key == pygame.K_TAB:
                            if num_teams() > 1:
                                active_team = (active_team + 1) % num_teams()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                if screen_mode == "title":
                    for bx, by, bw, bh, action in title_btn_rects:
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            if action == "play":
                                screen_mode = "level_select"
                            elif action == "editor":
                                enter_editor()
                            elif action == "settings":
                                screen_mode = "settings"
                            break

                elif screen_mode == "level_select":
                    # tab clicks
                    for bx, by, bw, bh, key in level_select_tab_rects:
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            level_select_tab = key
                            level_select_scroll = 0
                            break
                    # action buttons (load/share/delete)
                    for bx, by, bw, bh, action in level_select_action_rects:
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            if action == "load_pack":
                                try:
                                    raw = pygame.scrap.get(pygame.SCRAP_TEXT)
                                    if raw:
                                        code = raw.decode().strip().rstrip('\x00')
                                        name, levels = deserialize_pack(code)
                                        if levels:
                                            community_packs.append({"name": name, "code": code, "levels": levels})
                                            save_progress(stars, sim_speed, show_gridlines, community_packs)
                                except Exception:
                                    pass
                            elif action == "share_pack":
                                if community_packs and pack_idx < len(community_packs):
                                    code = community_packs[pack_idx].get("code", "")
                                    if code:
                                        try:
                                            pygame.scrap.put(pygame.SCRAP_TEXT, code.encode())
                                        except Exception:
                                            pass
                            elif isinstance(action, tuple) and action[0] == "delete_pack":
                                pi = action[1]
                                if 0 <= pi < len(community_packs):
                                    community_packs.pop(pi)
                                    if pack_idx >= len(community_packs):
                                        pack_idx = max(0, len(community_packs) - 1)
                                    save_progress(stars, sim_speed, show_gridlines, community_packs)
                            break
                    # level tile clicks
                    for rect in level_select_rects:
                        bx, by, bw, bh = rect[:4]
                        data = rect[4]
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            if isinstance(data, tuple) and data[0] == "level":
                                start_level(data[1])
                            elif isinstance(data, tuple) and data[0] == "pack_level":
                                pi, li = data[1], data[2]
                                if pi < len(community_packs) and li < len(community_packs[pi]["levels"]):
                                    pack_level = community_packs[pi]["levels"][li]
                                    # add as temp level and play it
                                    if len(LEVELS) > NUM_LEVELS:
                                        LEVELS.pop()
                                    LEVELS.append(pack_level)
                                    start_level(len(LEVELS) - 1)
                            elif isinstance(data, int):
                                start_level(data)
                            break

                elif screen_mode == "settings":
                    for bx, by, bw, bh, (key, val) in settings_rects:
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            if key == "speed":
                                sim_speed = val
                            elif key == "gridlines":
                                show_gridlines = val
                            elif key == "sound":
                                if sounds:
                                    sounds.enabled = val
                            elif key == "reset":
                                stars = [0] * NUM_LEVELS
                                save_progress(stars, sim_speed, show_gridlines, community_packs)
                            elif key == "back":
                                save_progress(stars, sim_speed, show_gridlines, community_packs)
                                screen_mode = "title"
                            break

                elif screen_mode == "play" and show_pause_menu:
                    for bx, by, bw, bh, action in pause_btn_rects:
                        if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                            if action == "resume":
                                show_pause_menu = False
                                paused = False
                            elif action == "restart":
                                show_pause_menu = False
                                reset_level()
                            elif action == "levels":
                                show_pause_menu = False
                                screen_mode = "level_select"
                            elif action == "quit":
                                save_progress(stars, sim_speed, show_gridlines, community_packs)
                                screen_mode = "title"
                            break

                elif screen_mode == "play":
                    if editor_mode:
                        mx, my = mouse_pos
                        gx, gy = mx // CELL, my // CELL
                        if mx < GRID_PX_W and 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                            agent_mode = editor_state.get("agent_place_mode", False)
                            if agent_mode or (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                                # agent placement mode
                                existing = [a for a in editor_agents if a["x"] == gx and a["y"] == gy]
                                if existing:
                                    a = existing[0]
                                    dirs = [(1,0),(0,1),(-1,0),(0,-1)]
                                    cur = (a["dx"], a["dy"])
                                    idx = dirs.index(cur) if cur in dirs else 0
                                    if idx < 3:
                                        a["dx"], a["dy"] = dirs[idx + 1]
                                        editor_state["status_msg"] = f"Agent rotated"
                                    else:
                                        editor_agents.remove(a)
                                        editor_state["status_msg"] = "Agent removed"
                                else:
                                    if len(editor_agents) < editor_state["num_agents"]:
                                        team = len(editor_agents)
                                        editor_agents.append({"x": gx, "y": gy, "dx": 1, "dy": 0, "team": team})
                                        grid[gy][gx] = EMPTY
                                        editor_state["status_msg"] = f"Agent {team+1} placed (click to rotate)"
                                    else:
                                        editor_state["status_msg"] = f"Max {editor_state['num_agents']} agents"
                            else:
                                editor_save_undo()
                                # use current brush (persists until changed)
                                brush = editor_state.get("brush", editor_state["selected"])
                                grid[gy][gx] = brush
                        else:
                            # panel clicks
                            for bx, by, bw, bh, cell_type in editor_palette_rects:
                                if bx <= mx < bx + bw and by <= my < by + bh:
                                    editor_state["selected"] = cell_type
                                    editor_state["brush"] = cell_type  # update brush
                                    editor_state["agent_place_mode"] = False
                                    break
                            for bx, by, bw, bh, key in editor_action_rects:
                                if bx <= mx < bx + bw and by <= my < by + bh:
                                    if key == "test":
                                        editor_test()
                                    elif key == "copy":
                                        editor_copy()
                                    elif key == "paste":
                                        editor_paste()
                                    elif key == "clear":
                                        if editor_state["clear_pending"] and (now - editor_state["clear_tick"]) < 1500:
                                            editor_save_undo()
                                            grid = [[EMPTY]*GRID_W for _ in range(GRID_H)]
                                            editor_agents = []
                                            editor_state["status_msg"] = "Cleared!"
                                            editor_state["clear_pending"] = False
                                        else:
                                            editor_state["clear_pending"] = True
                                            editor_state["clear_tick"] = now
                                            editor_state["status_msg"] = "Click Clear again to confirm"
                                    elif key == "agent_toggle":
                                        editor_state["agent_place_mode"] = not editor_state["agent_place_mode"]
                                    elif key == "help_toggle":
                                        editor_state["show_help"] = not editor_state.get("show_help", False)
                                    elif key == "per_agent_toggle":
                                        editor_state["per_agent"] = not editor_state["per_agent"]
                                        editor_state["status_msg"] = f"Per-agent: {'ON' if editor_state['per_agent'] else 'OFF'}"
                                    elif isinstance(key, tuple) and key[0] == "agent_count":
                                        editor_state["num_agents"] = key[1]
                                        if key[1] == 1:
                                            editor_state["per_agent"] = False
                                    break
                    elif is_place_agent() and step == 0:
                        # place_agent mode: click grid to place/rotate agent before running
                        mx, my = mouse_pos
                        gx, gy = mx // CELL, my // CELL
                        if mx < GRID_PX_W and 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                            # only place on empty cells (not on walls)
                            if grid[gy][gx] == EMPTY or grid[gy][gx] == AGENT:
                                existing = [a for a in agents if a["x"] == gx and a["y"] == gy]
                                if existing:
                                    a = existing[0]
                                    dirs = [(1,0),(0,1),(-1,0),(0,-1)]
                                    cur = (a["dx"], a["dy"])
                                    idx = dirs.index(cur) if cur in dirs else 0
                                    if idx < 3:
                                        a["dx"], a["dy"] = dirs[idx + 1]
                                    else:
                                        # remove agent
                                        grid[gy][gx] = EMPTY
                                        agents.remove(a)
                                        place_agent_pos = [{"x":a2["x"],"y":a2["y"],"dx":a2["dx"],"dy":a2["dy"]} for a2 in agents]
                                elif len(agents) < LEVELS[level_idx % NUM_LEVELS].get("max_agents", 1):
                                    new_a = {"x": gx, "y": gy, "dx": 1, "dy": 0, "alive": True, "team": 0}
                                    agents.append(new_a)
                                    grid[gy][gx] = AGENT
                                    total_spawned = len(agents)
                                    peak_pop = len(agents)
                                    place_agent_pos = [{"x":a2["x"],"y":a2["y"],"dx":a2["dx"],"dy":a2["dy"]} for a2 in agents]
                    else:
                        for tbx, tby, tbw, tbh, tidx in tab_hit_rects:
                            if tbx <= mouse_pos[0] < tbx + tbw and tby <= mouse_pos[1] < tby + tbh:
                                active_team = tidx
                                break
                        for bx, by, bw, bh, wall_type in btn_hit_rects:
                            if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                                disabled = get_disabled_verbs(LEVELS[level_idx % NUM_LEVELS]).get(wall_type, [])
                                verbs_list[active_team][wall_type] = cycle_verb(verbs_list[active_team][wall_type], disabled)
                                if sounds:
                                    sounds.play_click()
                                break

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if screen_mode == "play" and editor_mode:
                    mx, my = mouse_pos
                    gx, gy = mx // CELL, my // CELL
                    if mx < GRID_PX_W and 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                        editor_save_undo()
                        grid[gy][gx] = EMPTY
                        editor_agents = [a for a in editor_agents if not (a["x"] == gx and a["y"] == gy)]

            elif event.type == pygame.MOUSEWHEEL and screen_mode == "level_select":
                level_select_scroll = max(0, level_select_scroll - event.y * 30)

        # ── update ──
        tick_ms = SPEED_MS[sim_speed]

        if screen_mode == "play" and not editor_mode and not show_pause_menu:
            cur_level = LEVELS[level_idx % NUM_LEVELS]
            cur_evil_rules = cur_level.get("evil_rules")
            is_intercept = cur_level.get("mode") == "intercept"
            walls_left = count_walls(grid, underneath)

            evil_alive = sum(1 for a in agents if a.get("evil") and a.get("alive", True))
            hero_alive = sum(1 for a in agents if not a.get("evil") and a.get("alive", True))

            if is_intercept:
                game_over = (evil_alive == 0 and step > 0) or (hero_alive == 0 and step > 0) or (step >= MAX_STEPS)
            else:
                game_over = (walls_left == 0) or (len(agents) == 0 and step > 0) or (step >= MAX_STEPS)

            if game_over and step > 0:
                new_stars = calc_stars(walls_left, len(agents), step, cur_level)
                if is_intercept and evil_alive == 0:
                    new_stars = max(new_stars, 2)  # at least "perfect" for intercept win
                if level_idx < len(stars) and new_stars > stars[level_idx]:
                    stars[level_idx] = new_stars
                    save_progress(stars, sim_speed, show_gridlines, community_packs)

            if not paused and not game_over and now - last_sim_tick >= tick_ms:
                last_sim_tick = now
                prev_walls = count_walls(grid, underneath)
                prev_agents = len(agents)
                agents, spawned, sim_events = sim_step(agents, grid, verbs_list, underneath, cur_evil_rules)
                step += 1
                total_spawned += spawned
                if len(agents) > peak_pop:
                    peak_pop = len(agents)
                save_snapshot()

                # sound events
                if sounds:
                    if sim_events["consumed"] > 0:
                        sounds.play_consume()
                    if sim_events["dissolved"] > 0:
                        sounds.play_dissolve()
                    if sim_events["replicated"] > 0:
                        sounds.play_replicate()
                    if sim_events["turned"] > 0:
                        sounds.play_turn()
                    if sim_events["reversed"] > 0:
                        sounds.play_reverse()
                    if sim_events["teleported"] > 0:
                        sounds.play_teleport()

                # (event-based sounds already played above from sim_events)

            # sound for game end
            if sounds and game_over and step > 0 and not getattr(main, '_end_played', False):
                walls_left_now = count_walls(grid, underneath)
                if walls_left_now == 0 and len(agents) == 0:
                    sounds.play_perfect()
                elif walls_left_now == 0:
                    sounds.play_level_complete()
                else:
                    sounds.play_fail()
                main._end_played = True
            if not game_over:
                main._end_played = False

        # ── draw ──
        if screen_mode == "title":
            title_btn_rects = draw_title_screen(screen, font, font_sm, font_lg, mouse_pos, title_tick)

        elif screen_mode == "level_select":
            level_select_rects, level_select_tab_rects, level_select_action_rects = draw_level_select(
                screen, font, font_sm, stars, mouse_pos, level_select_scroll,
                level_select_tab, community_packs, pack_idx)

        elif screen_mode == "settings":
            sound_on = sounds.enabled if sounds else False
            settings_rects = draw_settings_screen(screen, font, font_sm, sim_speed, show_gridlines, mouse_pos, sound_on)

        elif screen_mode == "play":
            screen.fill(BG)
            if editor_mode:
                draw_editor_grid(screen, grid, editor_agents, underneath)
                mx, my = mouse_pos
                if mx < GRID_PX_W:
                    gx, gy = mx // CELL, my // CELL
                    if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
                        pygame.draw.rect(screen, (80, 80, 100), (gx * CELL, gy * CELL, CELL, CELL), 1)
                editor_palette_rects, editor_action_rects = draw_editor_panel(
                    screen, font, font_sm, editor_state, mouse_pos)

                # help overlay on grid
                if editor_state.get("show_help"):
                    overlay = pygame.Surface((GRID_PX_W, WIN_H))
                    overlay.set_alpha(220)
                    overlay.fill((20, 20, 30))
                    screen.blit(overlay, (0, 0))
                    hx, hy = 30, 30
                    screen.blit(font.render("EDITOR CONTROLS", True, (255, 200, 80)), (hx, hy))
                    hy += 30
                    help_lines = [
                        ("GRID", ""),
                        ("  Left-click", "Place selected cell"),
                        ("  Right-click", "Erase cell"),
                        ("  Shift+click", "Place/rotate/remove agent"),
                        ("", ""),
                        ("AGENT", ""),
                        ("  Click agent", "Rotate: right > down > left > up > remove"),
                        ("  PLACE AGENT btn", "Toggle agent placement mode"),
                        ("  1 / 2 / 3 / 4", "Set max agent count"),
                        ("  A", "Toggle per-agent rules"),
                        ("", ""),
                        ("CELLS", ""),
                        ("  Click palette", "Select cell type to place"),
                        ("  S", "Push selected color onto sandwich stack"),
                        ("  D", "Clear sandwich stack"),
                        ("  Click grid", "Place sandwich (if stack has layers)"),
                        ("", ""),
                        ("ACTIONS", ""),
                        ("  T", "Test level (switch to play mode)"),
                        ("  C", "Copy level code to clipboard"),
                        ("  V", "Paste level code from clipboard"),
                        ("  Z", "Undo last edit"),
                        ("  X (twice)", "Clear entire grid"),
                        ("", ""),
                        ("NAVIGATION", ""),
                        ("  E / ESC", "Exit editor"),
                        ("  H / ? btn", "Toggle this help"),
                    ]
                    for key, desc in help_lines:
                        if not key and not desc:
                            hy += 6
                            continue
                        if not desc:
                            screen.blit(font_sm.render(key, True, (150, 200, 255)), (hx, hy))
                        else:
                            screen.blit(font_sm.render(key, True, TEXT_COLOR), (hx, hy))
                            screen.blit(font_sm.render(desc, True, TEXT_DIM), (hx + 160, hy))
                        hy += 16
            else:
                walls_left = count_walls(grid, underneath)
                if show_gridlines:
                    for gx in range(GRID_W + 1):
                        pygame.draw.line(screen, (30, 30, 40), (gx * CELL, 0), (gx * CELL, GRID_PX_H))
                    for gy in range(GRID_H + 1):
                        pygame.draw.line(screen, (30, 30, 40), (0, gy * CELL), (GRID_PX_W, gy * CELL))
                draw_grid(screen, grid, agents, underneath)
                cur_lev = LEVELS[level_idx % NUM_LEVELS]
                cur_evil = cur_lev.get("evil_rules") or cur_lev.get("fixed_rules")
                btn_hit_rects, tab_hit_rects = draw_panel(
                    screen, font, font_sm, verbs_list, active_team, num_teams(),
                    step, agents, total_spawned, peak_pop, walls_left, walls_start,
                    paused, mouse_pos, level_idx, evil_rules=cur_evil,
                    is_testing=testing_editor_level)

                # star rating after level complete
                if walls_left == 0 and step > 0:
                    new_s = calc_stars(walls_left, len(agents), step, LEVELS[level_idx % NUM_LEVELS])
                    star_txt = STAR_CHARS[new_s]
                    star_labels = ["", "CLEARED", "PERFECT!", "EFFICIENT!"]
                    star_msg = f"{star_txt} {star_labels[new_s]}"
                    sc = STAR_COLORS[new_s]
                    screen.blit(font.render(star_msg, True, sc), (GRID_PX_W + 12, WIN_H - 35))

                if show_pause_menu:
                    pause_btn_rects = draw_pause_overlay(screen, font, font_sm, mouse_pos)

        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)  # yield control for pygbag

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
