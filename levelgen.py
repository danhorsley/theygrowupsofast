# levelgen.py — brute force level generator with heuristic scoring
#
# 1. Generate random 2D connected shapes with mixed colors, sandwiches, gaps
# 2. Solve exhaustively (all 125 verb assignments, <1ms each)
# 3. Score with heuristics: unique solution, uses all verbs, peak agents, etc.
# 4. Deduplicate: skip levels that are color-permutations of existing ones
# 5. Output the best candidates

import random
from itertools import product

# ── constants (match app.py) ──

R, Y, B = 1, 2, 3
G, P, O, C = 5, 6, 7, 8
ASSIGNABLE = (R, Y, B)
FIXED = (G, P, O, C)
ALL_WALL = ASSIGNABLE + FIXED
PASS, REP, DISS, TL, TR = 0, 1, 2, 3, 4
VERBS = [PASS, REP, DISS, TL, TR]
FIXED_VERB = {G: REP, P: DISS, O: TR, C: TL}
RIGHT = (1, 0)

VN = {PASS: "Pass", REP: "Rep", DISS: "Diss", TL: "TurnL", TR: "TurnR"}
CN = {R: "R", Y: "Y", B: "B", G: "G", P: "P", O: "O", C: "C"}


def turn_left(dx, dy):
    return (dy, -dx)

def turn_right(dx, dy):
    return (-dy, dx)

def get_verb(color, vm):
    if color in FIXED_VERB:
        return FIXED_VERB[color]
    return vm.get(color, PASS)

def is_wall(cell):
    if isinstance(cell, tuple):
        return len(cell) > 0
    return cell in ALL_WALL

def pop_top(cell):
    if isinstance(cell, tuple):
        top = cell[0]
        rest = cell[1:]
        if len(rest) == 0:
            return top, 0
        if len(rest) == 1:
            return top, rest[0]
        return top, rest
    return cell, 0


# ── simulator ──

def simulate(cell_list, vm, start, direction, max_ticks=300):
    """Run sim. Returns (all_consumed, alive_count, peak_agents, ticks_used)."""
    cells = {}
    for x, y, c in cell_list:
        cells[(x, y)] = c
    underneath = {}

    def count_remaining():
        n = 0
        for v in cells.values():
            if isinstance(v, tuple):
                n += len(v)
            elif is_wall(v):
                n += 1
        for layers in underneath.values():
            n += len(layers)
        return n

    sx, sy = start
    dx, dy = direction
    agents = [{"x": sx, "y": sy, "dx": dx, "dy": dy}]
    peak = 1

    for tick in range(max_ticks):
        if not agents or count_remaining() == 0:
            break

        dead = []
        new_agents = []

        for a in agents:
            ax, ay = a["x"], a["y"]
            adx, ady = a["dx"], a["dy"]
            nx, ny = ax + adx, ay + ady
            target = cells.get((nx, ny), 0)

            if is_wall(target):
                top, rem = pop_top(target)
                verb = get_verb(top, vm)
                has_rem = rem != 0

                # vacate old position
                if verb in (PASS, TL, TR, DISS):
                    if (ax, ay) in underneath:
                        r = underneath.pop((ax, ay))
                        cells[(ax, ay)] = r[0] if len(r) == 1 else tuple(r)
                    else:
                        cells[(ax, ay)] = 0

                if verb == PASS:
                    a["x"], a["y"] = nx, ny
                    cells[(nx, ny)] = 4
                    if has_rem:
                        underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]

                elif verb == REP:
                    new_agents.append({"x": nx, "y": ny, "dx": adx, "dy": ady})
                    cells[(nx, ny)] = 4
                    if has_rem:
                        underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]

                elif verb == DISS:
                    dead.append(a)
                    if has_rem:
                        cells[(nx, ny)] = rem
                    else:
                        cells[(nx, ny)] = 0

                elif verb == TL:
                    a["x"], a["y"] = nx, ny
                    a["dx"], a["dy"] = turn_left(adx, ady)
                    cells[(nx, ny)] = 4
                    if has_rem:
                        underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]

                elif verb == TR:
                    a["x"], a["y"] = nx, ny
                    a["dx"], a["dy"] = turn_right(adx, ady)
                    cells[(nx, ny)] = 4
                    if has_rem:
                        underneath[(nx, ny)] = list(rem) if isinstance(rem, tuple) else [rem]

            elif target == 0:
                if (ax, ay) in underneath:
                    r = underneath.pop((ax, ay))
                    cells[(ax, ay)] = r[0] if len(r) == 1 else tuple(r)
                else:
                    cells[(ax, ay)] = 0
                a["x"], a["y"] = nx, ny

        for d in dead:
            agents.remove(d)
        agents.extend(new_agents)
        if len(agents) > peak:
            peak = len(agents)

    remaining = count_remaining()
    return remaining == 0 and len(agents) == 0, len(agents), peak, tick


def find_solutions(cell_list, start=(-1, 0), direction=RIGHT):
    """Find all perfect verb assignments. Returns list of (verb_map, peak)."""
    solutions = []
    for vr, vy, vb in product(VERBS, repeat=3):
        vm = {R: vr, Y: vy, B: vb}
        ok, alive, peak, ticks = simulate(cell_list, vm, start, direction)
        if ok and alive == 0:
            solutions.append((vm, peak, ticks))
    return solutions


# ── shape generators ──

def gen_tape(min_len=3, max_len=8):
    """Random 1D tape of assignable colors."""
    length = random.randint(min_len, max_len)
    colors = [random.choice(ASSIGNABLE) for _ in range(length)]
    cells = [(i, 0, c) for i, c in enumerate(colors)]
    return cells, (-1, 0), RIGHT


def gen_l_shape():
    """L-shape: horizontal then vertical. Random colors at each position."""
    horiz_len = random.randint(2, 4)
    vert_len = random.randint(2, 4)
    cells = []
    for i in range(horiz_len):
        cells.append((i, 0, random.choice(ASSIGNABLE)))
    corner = horiz_len
    cells.append((corner, 0, random.choice(ASSIGNABLE)))
    for j in range(1, vert_len + 1):
        cells.append((corner, j, random.choice(ASSIGNABLE)))
    return cells, (-1, 0), RIGHT


def gen_t_shape():
    """T-junction with a sandwich at the corner."""
    trunk_len = random.randint(2, 5)
    branch_len = random.randint(2, 4)
    tail_len = random.randint(1, 3)

    cells = []
    # trunk before junction
    for i in range(trunk_len):
        cells.append((i, 0, random.choice(ASSIGNABLE)))

    # replicate before junction
    jx = trunk_len
    cells.append((jx, 0, G))

    # sandwich at junction: top = turn, bottom = pass-through
    sx = jx + 1
    top_color = random.choice(ASSIGNABLE)
    bottom_color = random.choice(ASSIGNABLE)
    cells.append((sx, 0, (top_color, bottom_color)))

    # tail (parent continues right)
    for i in range(1, tail_len + 1):
        cells.append((sx + i, 0, random.choice(ASSIGNABLE)))

    # branch (child goes down)
    for j in range(1, branch_len + 1):
        cells.append((sx, j, random.choice(ASSIGNABLE)))

    return cells, (-1, 0), RIGHT


def gen_u_shape():
    """U-shape: right, down, left. Random colors."""
    w = random.randint(2, 4)
    h = random.randint(2, 4)
    cells = []
    for i in range(w + 1):
        cells.append((i, 0, random.choice(ASSIGNABLE)))
    for j in range(1, h):
        cells.append((w, j, random.choice(ASSIGNABLE)))
    for i in range(w, -1, -1):
        cells.append((i, h, random.choice(ASSIGNABLE)))
    return cells, (-1, 0), RIGHT


def gen_tape_with_fixed():
    """Tape mixing assignable and fixed cells."""
    length = random.randint(4, 8)
    cells = []
    for i in range(length):
        if random.random() < 0.25:
            cells.append((i, 0, random.choice([G, P])))
        else:
            cells.append((i, 0, random.choice(ASSIGNABLE)))
    return cells, (-1, 0), RIGHT


def gen_gap_fork():
    """Fork with air gaps for timing control."""
    # main path with gap
    gap_len = random.randint(1, 4)
    tail_len = random.randint(1, 3)
    branch_len = random.randint(2, 4)

    cells = []
    cells.append((0, 0, random.choice(ASSIGNABLE)))
    cells.append((1, 0, G))

    # sandwich at fork
    top = random.choice(ASSIGNABLE)
    bot = random.choice(ASSIGNABLE)
    cells.append((2, 0, (top, bot)))

    # parent continues right after gap
    end_x = 2 + gap_len + 1
    for i in range(tail_len):
        cells.append((end_x + i, 0, random.choice(ASSIGNABLE)))

    # child goes down
    for j in range(1, branch_len + 1):
        cells.append((2, j, random.choice(ASSIGNABLE)))

    return cells, (-1, 0), RIGHT


def gen_sandwich_tape():
    """1D tape with sandwiches mixed in."""
    length = random.randint(4, 7)
    cells = []
    for i in range(length):
        if random.random() < 0.2:
            c1 = random.choice(ASSIGNABLE)
            c2 = random.choice(ASSIGNABLE)
            cells.append((i, 0, (c1, c2)))
        else:
            cells.append((i, 0, random.choice(ASSIGNABLE)))
    return cells, (-1, 0), RIGHT


GENERATORS = [
    gen_tape, gen_l_shape, gen_t_shape, gen_u_shape,
    gen_tape_with_fixed, gen_gap_fork, gen_sandwich_tape,
]


# ── scoring ──

def score_level(cell_list, solutions, start, direction):
    """Score a level. Higher = better puzzle."""
    if not solutions:
        return -1

    score = 0
    n_sols = len(solutions)

    # unique solution is best
    if n_sols == 1:
        score += 100
    elif n_sols == 2:
        score += 40
    elif n_sols <= 5:
        score += 10
    else:
        return 0  # too many solutions, boring

    vm, peak, ticks = solutions[0]

    # uses all 3 assignable colors in the level
    colors_used = set()
    for _, _, c in cell_list:
        if isinstance(c, tuple):
            for color in c:
                if color in ASSIGNABLE:
                    colors_used.add(color)
        elif c in ASSIGNABLE:
            colors_used.add(c)
    score += len(colors_used) * 10

    # solution uses non-trivial verbs (not all Pass)
    verb_types = set(vm[c] for c in ASSIGNABLE if c in colors_used)
    if REP in verb_types:
        score += 20
    if TR in verb_types or TL in verb_types:
        score += 20
    if DISS in verb_types:
        score += 10
    if len(verb_types) >= 3:
        score += 15  # uses 3+ different verbs

    # peak agents > 1 means replication happens (visual interest)
    if peak >= 2:
        score += 15
    if peak >= 4:
        score += 10

    # compact: fewer cells for same difficulty
    total_layers = sum(len(c) if isinstance(c, tuple) else 1 for _, _, c in cell_list)
    if total_layers <= 8:
        score += 10
    elif total_layers <= 12:
        score += 5

    # has sandwiches (interesting mechanic)
    has_sandwich = any(isinstance(c, tuple) for _, _, c in cell_list)
    if has_sandwich:
        score += 10

    # penalize if unused colors (B can be anything)
    for c in ASSIGNABLE:
        if c not in colors_used:
            score -= 15  # unused color = less interesting

    return score


def canonical_solution(vm, colors_used):
    """Canonical form of a solution for deduplication.
    Normalize by mapping colors to a canonical order based on their verbs."""
    # sort colors by their verb assignment
    verb_list = sorted((vm.get(c, PASS), c) for c in ASSIGNABLE if c in colors_used)
    return tuple(v for v, _ in verb_list)


# ── main generator ──

def generate_levels(n_candidates=50000, top_n=30, seed=42):
    """Generate n_candidates random levels, return the top_n best."""
    random.seed(seed)

    scored = []

    for _ in range(n_candidates):
        gen = random.choice(GENERATORS)
        cell_list, start, direction = gen()

        # quick check: skip tiny levels
        total = sum(len(c) if isinstance(c, tuple) else 1 for _, _, c in cell_list)
        if total < 3:
            continue

        # check for position collisions
        positions = [(x, y) for x, y, _ in cell_list]
        if len(positions) != len(set(positions)):
            continue

        solutions = find_solutions(cell_list, start, direction)
        s = score_level(cell_list, solutions, start, direction)

        if s > 50:  # minimum quality threshold
            scored.append((s, cell_list, solutions, start, direction))

    # sort by score descending
    scored.sort(key=lambda x: -x[0])

    # deduplicate: skip levels with identical solution canonical forms
    seen_solutions = set()
    selected = []

    for s, cells, solutions, start, direction in scored:
        colors_used = set()
        for _, _, c in cells:
            if isinstance(c, tuple):
                for color in c:
                    if color in ASSIGNABLE:
                        colors_used.add(color)
            elif c in ASSIGNABLE:
                colors_used.add(c)

        canon = canonical_solution(solutions[0][0], colors_used)
        # also include shape signature for dedup
        shape_sig = tuple(sorted((x, y) for x, y, _ in cells))

        key = (canon, shape_sig)
        if key in seen_solutions:
            continue
        seen_solutions.add(key)
        selected.append((s, cells, solutions, start, direction))

        if len(selected) >= top_n:
            break

    return selected


if __name__ == "__main__":
    print("Generating levels...\n")
    levels = generate_levels(n_candidates=100000, top_n=40)

    print(f"Found {len(levels)} unique high-quality levels:\n")

    for i, (score, cells, solutions, start, direction) in enumerate(levels):
        total = sum(len(c) if isinstance(c, tuple) else 1 for _, _, c in cells)
        vm, peak, ticks = solutions[0]

        # cell visualization
        cell_strs = []
        for x, y, c in sorted(cells, key=lambda t: (t[1], t[0])):
            if isinstance(c, tuple):
                cell_strs.append(f"({''.join(CN.get(cc, '?') for cc in c)})")
            else:
                cell_strs.append(CN.get(c, "?"))

        sol_str = " ".join(f"{CN[c]}={VN[vm[c]]}" for c in ASSIGNABLE)
        sw = " SW" if any(isinstance(c, tuple) for _, _, c in cells) else ""
        xs = [x for x, _, _ in cells]
        ys = [y for _, y, _ in cells]

        is_2d = (max(ys) - min(ys)) > 0

        print(f"  #{i+1:2d} score={score:3d} {total:2d}c {'2D' if is_2d else '1D'} pk{peak}"
              f"{sw} sol: {sol_str}  ({len(solutions)} sol)")

        # print shape
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        cell_map = {}
        for x, y, c in cells:
            cell_map[(x, y)] = c
        for row in range(min_y, max_y + 1):
            line = "       "
            for col in range(min_x, max_x + 1):
                c = cell_map.get((col, row))
                if c is None:
                    line += ". "
                elif isinstance(c, tuple):
                    line += f"{''.join(CN.get(cc,'?') for cc in c)[:2]:2s}"
                else:
                    line += f"{CN.get(c, '?')} "
            print(line.rstrip())
        print()

    # output as python data
    print("\n# ── paste into app.py ──\n")
    print("GENERATED = [")
    for score, cells, solutions, start, direction in levels[:15]:
        vm = solutions[0][0]
        sol_str = " ".join(f"{CN[c]}={VN[vm[c]]}" for c in ASSIGNABLE)
        print(f"    # score={score} sol: {sol_str}")
        print(f"    {{\"cells\": {cells}, \"start\": {start}, \"dir\": {direction}}},")
    print("]")
