# gen2d.py — 2D puzzle generator
#
# Generates random connected 2D shapes using assignable colors (R/Y/B),
# fixed cells (G/P/O/C/W), sandwiches, and air gaps.
# Verifies solvability via brute force, scores for quality.
#
# Usage: python gen2d.py [--count N] [--min-cells 5] [--max-cells 20]

import random
import sys
import argparse
from itertools import product as iprod
from collections import deque

# ── constants (match app.py) ──

EMPTY = 0
R, Y, B = 1, 2, 3
AGENT = 4
G, P, O, C, W = 5, 6, 7, 8, 9

ASSIGNABLE = (R, Y, B)
FIXED_TYPES = (G, P, O, C, W)
ALL_WALL = ASSIGNABLE + FIXED_TYPES

PASS, REP, DISS, TL, TR = 0, 1, 2, 3, 4
VERBS = [PASS, REP, DISS, TL, TR]
FIXED_VERB = {W: PASS, G: REP, P: DISS, O: TR, C: TL}

CN = {R: "R", Y: "Y", B: "B", G: "G", P: "P", O: "O", C: "C", W: "w"}
VN = {PASS: "Pass", REP: "Rep", DISS: "Diss", TL: "TL", TR: "TR"}

RIGHT, DOWN, LEFT, UP = (1, 0), (0, 1), (-1, 0), (0, -1)
DIRS = [RIGHT, DOWN, LEFT, UP]

def tl(dx, dy): return (dy, -dx)
def tr(dx, dy): return (-dy, dx)
def gv(color, vm):
    if color in FIXED_VERB: return FIXED_VERB[color]
    return vm.get(color, PASS)


# ── shape generation ──

def random_connected_shape(n_cells, width_max=12, height_max=10):
    """Grow a random connected shape of n_cells via random walk from origin."""
    cells = {(0, 0)}
    frontier = [(0, 0)]
    while len(cells) < n_cells:
        if not frontier:
            break
        pos = random.choice(frontier)
        dx, dy = random.choice(DIRS)
        nx, ny = pos[0] + dx, pos[1] + dy
        if (nx, ny) not in cells and abs(nx) < width_max and abs(ny) < height_max:
            cells.add((nx, ny))
            frontier.append((nx, ny))
        # prune dead-end frontier nodes occasionally
        if random.random() < 0.1:
            frontier = [p for p in frontier if any(
                (p[0]+d[0], p[1]+d[1]) not in cells for d in DIRS)]
            if not frontier:
                frontier = list(cells)
    return cells


def assign_colors(positions, config):
    """Assign colors to positions based on config strategy."""
    cells = {}
    pos_list = sorted(positions)

    strategy = config.get("strategy", "mixed")

    if strategy == "all_assignable":
        for p in pos_list:
            cells[p] = random.choice(ASSIGNABLE)

    elif strategy == "mixed":
        # mostly assignable, some fixed
        for p in pos_list:
            r = random.random()
            if r < 0.65:
                cells[p] = random.choice(ASSIGNABLE)
            elif r < 0.75:
                cells[p] = W  # grey road
            elif r < 0.85:
                cells[p] = random.choice([G, P])  # replicate/dissolve
            else:
                cells[p] = random.choice([O, C])  # turns

    elif strategy == "grey_road":
        # mostly grey with assignable at decision points
        for i, p in enumerate(pos_list):
            if i == 0 or i == len(pos_list) - 1:
                cells[p] = random.choice(ASSIGNABLE)
            elif random.random() < 0.3:
                cells[p] = random.choice(ASSIGNABLE)
            else:
                cells[p] = W

    elif strategy == "sandwich_heavy":
        for p in pos_list:
            if random.random() < 0.2:
                n = random.choice([2, 3])
                cells[p] = tuple(random.choice(ASSIGNABLE) for _ in range(n))
            else:
                cells[p] = random.choice(ASSIGNABLE)

    return cells


def add_air_gaps(cells, gap_chance=0.15):
    """Randomly remove some cells to create air gaps (empty spaces in the path)."""
    if len(cells) < 5:
        return cells
    positions = sorted(cells.keys())
    to_remove = []
    for p in positions[1:-1]:  # never remove first/last
        if random.random() < gap_chance:
            # only remove if shape stays connected without it
            test = {k: v for k, v in cells.items() if k != p}
            if is_connected(set(test.keys())):
                to_remove.append(p)
    for p in to_remove:
        del cells[p]
    return cells


def is_connected(positions):
    """Check if positions form a connected shape (4-connected)."""
    if not positions:
        return False
    start = next(iter(positions))
    visited = set()
    queue = deque([start])
    while queue:
        p = queue.popleft()
        if p in visited:
            continue
        visited.add(p)
        for dx, dy in DIRS:
            nb = (p[0] + dx, p[1] + dy)
            if nb in positions and nb not in visited:
                queue.append(nb)
    return len(visited) == len(positions)


def pick_agent_start(cells):
    """Pick agent start: just outside the shape, facing inward."""
    positions = set(cells.keys())
    # find boundary cells (cells with at least one empty neighbor)
    boundary = []
    for p in positions:
        for dx, dy in DIRS:
            nb = (p[0] + dx, p[1] + dy)
            if nb not in positions:
                boundary.append((nb, (-dx, -dy)))  # outside pos, facing inward

    if not boundary:
        p = min(positions)
        return (p[0] - 1, p[1]), RIGHT

    start_pos, start_dir = random.choice(boundary)
    return start_pos, start_dir


# ── simulation ──

def pop_top(cell):
    if isinstance(cell, tuple):
        top = cell[0]; rest = cell[1:]
        if len(rest) == 0: return top, 0
        if len(rest) == 1: return top, rest[0]
        return top, rest
    return cell, 0

def is_wall(cell):
    if isinstance(cell, tuple): return len(cell) > 0
    return cell in ALL_WALL

def simulate(level, vm, max_ticks=100):
    """Run sim, return (perfect, alive, peak, ticks_used)."""
    cells = {}
    for x, y, c in level["cells"]:
        cells[(x, y)] = c
    underneath = {}

    def cnt():
        n = 0
        for v in cells.values():
            if isinstance(v, tuple): n += len(v)
            elif is_wall(v): n += 1
        for l in underneath.values(): n += len(l)
        return n

    agents_def = level.get("agents", [{"x": level["start"][0], "y": level["start"][1],
                                        "dx": level["dir"][0], "dy": level["dir"][1]}])
    agents = [dict(a) for a in agents_def]
    peak = len(agents)

    for tick in range(max_ticks):
        if not agents or cnt() == 0:
            return cnt() == 0 and len(agents) == 0, len(agents), peak, tick
        dead = []; new = []
        for a in agents:
            ax, ay, adx, ady = a["x"], a["y"], a["dx"], a["dy"]
            nx, ny = ax + adx, ay + ady
            target = cells.get((nx, ny), 0)
            if is_wall(target):
                top, rem = pop_top(target)
                verb = gv(top, vm)
                hr = rem != 0
                if verb in (PASS, TL, TR, DISS):
                    if (ax, ay) in underneath:
                        r = underneath.pop((ax, ay))
                        cells[(ax, ay)] = r[0] if len(r) == 1 else tuple(r)
                    else:
                        cells[(ax, ay)] = 0
                if verb == PASS:
                    a["x"], a["y"] = nx, ny; cells[(nx, ny)] = AGENT
                    if hr: underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]
                elif verb == REP:
                    new.append({"x": nx, "y": ny, "dx": adx, "dy": ady}); cells[(nx, ny)] = AGENT
                    if hr: underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]
                elif verb == DISS:
                    dead.append(a)
                    if hr: cells[(nx, ny)] = rem
                    else: cells[(nx, ny)] = 0
                elif verb == TL:
                    a["x"], a["y"] = nx, ny; a["dx"], a["dy"] = tl(adx, ady); cells[(nx, ny)] = AGENT
                    if hr: underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]
                elif verb == TR:
                    a["x"], a["y"] = nx, ny; a["dx"], a["dy"] = tr(adx, ady); cells[(nx, ny)] = AGENT
                    if hr: underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]
            elif target == 0:
                if (ax, ay) in underneath:
                    r = underneath.pop((ax, ay))
                    cells[(ax, ay)] = r[0] if len(r) == 1 else tuple(r)
                else:
                    cells[(ax, ay)] = 0
                a["x"], a["y"] = nx, ny
        for d in dead: agents.remove(d)
        agents.extend(new)
        if len(agents) > peak: peak = len(agents)

    return cnt() == 0 and len(agents) == 0, len(agents), peak, max_ticks


def find_solutions(level):
    """Brute-force all 125 verb assignments, return perfect solutions."""
    solutions = []
    for vr, vy, vb in iprod(VERBS, repeat=3):
        vm = {R: vr, Y: vy, B: vb}
        perfect, alive, peak, ticks = simulate(level, vm)
        if perfect:
            solutions.append((vm, peak, ticks))
    return solutions


# ── scoring ──

def score_level(level, solutions):
    """Score a level for puzzle quality. Higher = better."""
    if not solutions:
        return -1

    n_sol = len(solutions)
    cells = level["cells"]
    n_cells = sum(len(c) if isinstance(c, tuple) else 1 for _, _, c in cells)

    # colors used
    flat_colors = []
    for _, _, c in cells:
        if isinstance(c, tuple):
            flat_colors.extend(c)
        else:
            flat_colors.append(c)
    assignable_used = len(set(c for c in flat_colors if c in ASSIGNABLE))

    # best solution stats
    best = min(solutions, key=lambda s: s[2])  # fastest
    vm, peak, ticks = best

    # verb diversity in solution
    used_verbs = set(vm[c] for c in ASSIGNABLE if c in set(flat_colors))

    sc = 0

    # fewer solutions = harder = better
    if n_sol == 1: sc += 60
    elif n_sol == 2: sc += 40
    elif n_sol <= 5: sc += 20
    elif n_sol <= 10: sc += 5
    else: return 0  # too many solutions, boring

    # uses all 3 assignable colors meaningfully
    sc += assignable_used * 15

    # verb diversity (not all Pass)
    sc += len(used_verbs) * 10
    if REP in used_verbs: sc += 15  # replication makes it visual
    if TL in used_verbs or TR in used_verbs: sc += 10  # turns = 2D puzzle

    # peak agents (spectacle)
    sc += min(peak * 3, 20)

    # compact shape (fewer cells for same difficulty = tighter puzzle)
    if n_cells <= 8: sc += 10
    elif n_cells <= 15: sc += 5

    # has fixed cells (teaches mechanics)
    has_fixed = any(c in FIXED_TYPES for c in flat_colors)
    if has_fixed: sc += 5

    # has sandwiches
    has_sandwich = any(isinstance(c, tuple) for _, _, c in cells)
    if has_sandwich: sc += 10

    return sc


# ── main generator ──

def generate_path_level(min_cells=5, max_cells=18):
    """Generate a traversable path with turns, branches, and mixed colors."""
    n_target = random.randint(min_cells, max_cells)

    # start at origin going right
    x, y = 0, 0
    dx, dy = random.choice(DIRS)
    cells = {}
    path = [(x, y)]

    # walk forward, occasionally turning
    for _ in range(n_target - 1):
        # decide: go straight, turn left, or turn right
        r = random.random()
        if r < 0.6:
            pass  # straight
        elif r < 0.8:
            dx, dy = tl(dx, dy)
        else:
            dx, dy = tr(dx, dy)

        nx, ny = x + dx, y + dy
        if (nx, ny) in cells or (nx, ny) in [(p[0], p[1]) for p in path]:
            # collision with existing path — try other directions
            for alt_dx, alt_dy in DIRS:
                nx2, ny2 = x + alt_dx, y + alt_dy
                if (nx2, ny2) not in cells and (nx2, ny2) not in [(p[0], p[1]) for p in path]:
                    dx, dy = alt_dx, alt_dy
                    nx, ny = nx2, ny2
                    break
            else:
                break  # stuck

        path.append((nx, ny))
        x, y = nx, ny

    if len(path) < min_cells:
        return None

    # assign colors — path-aware: turns get turn colors, ends get dissolve
    strategy = random.choice(["all_assignable", "mixed", "grey_road", "sandwich_heavy"])

    for i, (px, py) in enumerate(path):
        if strategy == "all_assignable":
            cells[(px, py)] = random.choice(ASSIGNABLE)
        elif strategy == "mixed":
            r = random.random()
            if r < 0.55:
                cells[(px, py)] = random.choice(ASSIGNABLE)
            elif r < 0.7:
                cells[(px, py)] = W
            elif r < 0.85:
                cells[(px, py)] = random.choice([G, P])
            else:
                cells[(px, py)] = random.choice([O, C])
        elif strategy == "grey_road":
            if i == 0 or i == len(path) - 1 or random.random() < 0.35:
                cells[(px, py)] = random.choice(ASSIGNABLE)
            else:
                cells[(px, py)] = W
        elif strategy == "sandwich_heavy":
            if random.random() < 0.25 and len(path) > 4:
                n = random.choice([2, 3])
                cells[(px, py)] = tuple(random.choice(ASSIGNABLE) for _ in range(n))
            else:
                cells[(px, py)] = random.choice(ASSIGNABLE)

    # optionally add air gaps (remove some cells)
    if random.random() < 0.25 and len(cells) > 5:
        keys = list(cells.keys())
        for k in keys[1:-1]:
            if random.random() < 0.15:
                del cells[k]

    # agent starts just before the first cell
    sx, sy = path[0]
    # figure out initial direction from first two path cells
    if len(path) >= 2:
        init_dx = path[1][0] - path[0][0]
        init_dy = path[1][1] - path[0][1]
        if init_dx == 0 and init_dy == 0:
            init_dx, init_dy = 1, 0
    else:
        init_dx, init_dy = 1, 0

    start = (sx - init_dx, sy - init_dy)

    cell_list = [(x, y, c) for (x, y), c in sorted(cells.items())]
    return {"cells": cell_list, "start": start, "dir": (init_dx, init_dy)}


def generate_level(min_cells=5, max_cells=18):
    """Generate a random 2D level and check solvability."""
    return generate_path_level(min_cells, max_cells)


def main():
    parser = argparse.ArgumentParser(description="Generate 2D puzzle levels")
    parser.add_argument("--count", type=int, default=5000, help="Candidates to generate")
    parser.add_argument("--min-cells", type=int, default=5, help="Min cells per level")
    parser.add_argument("--max-cells", type=int, default=18, help="Max cells per level")
    parser.add_argument("--top", type=int, default=30, help="Top N levels to output")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print(f"Generating {args.count} candidates ({args.min_cells}-{args.max_cells} cells)...\n")

    results = []
    solvable = 0

    for i in range(args.count):
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{args.count} checked, {solvable} solvable, {len(results)} scored...", flush=True)

        level = generate_level(args.min_cells, args.max_cells)
        solutions = find_solutions(level)

        if solutions:
            solvable += 1
            sc = score_level(level, solutions)
            if sc > 0:
                results.append((level, solutions, sc))

    results.sort(key=lambda x: -x[2])
    top = results[:args.top]

    print(f"\nDone. {solvable} solvable out of {args.count}. {len(results)} scored > 0.\n")
    print(f"Top {len(top)} levels:\n")

    for rank, (level, solutions, sc) in enumerate(top, 1):
        cells = level["cells"]
        n_cells = sum(len(c) if isinstance(c, tuple) else 1 for _, _, c in cells)
        xs = [x for x, _, _ in cells]; ys = [y for _, y, _ in cells]
        w = max(xs) - min(xs) + 1; h = max(ys) - min(ys) + 1

        # shape preview
        grid = {}
        for x, y, c in cells:
            if isinstance(c, tuple):
                grid[(x, y)] = "/".join(CN.get(cc, "?") for cc in c)
            else:
                grid[(x, y)] = CN.get(c, "?")

        vm, peak, ticks = solutions[0]
        sol_str = " ".join(f"{CN[c]}={VN[vm[c]]}" for c in ASSIGNABLE if c in vm)

        print(f"  #{rank} sc={sc} | {n_cells}c {w}x{h} | {len(solutions)} sol | pk{peak} t{ticks} | {sol_str}")

        # mini grid
        for row_y in range(min(ys), max(ys) + 1):
            row = ""
            for col_x in range(min(xs), max(xs) + 1):
                row += f" {grid.get((col_x, row_y), '.'):>3}"
            print(f"    {row}")
        print()

    # output as Python
    print("\n# ── paste into app.py ──\n")
    print("GENERATED_2D = [")
    for level, solutions, sc in top:
        cells_py = repr(level["cells"])
        start = level["start"]
        d = level["dir"]
        n_sol = len(solutions)
        print(f"    # sc={sc}, {n_sol} sol")
        print(f'    {{"cells": {cells_py}, "start": {start}, "dir": {d}}},')
    print("]")


if __name__ == "__main__":
    main()
