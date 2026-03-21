# algo.py — enumerate all perfectly-solvable tapes up to length 10
#
# A tape is a sequence of colored cells (R, Y, B).
# A rule assignment maps each color to a verb: Pass, Replicate, or Die.
# "Perfect" = tape fully consumed AND zero agents remaining.
#
# The sim is equivalent to a counter:
#   start at 1
#   for each cell left to right:
#     Pass:      count unchanged
#     Replicate: count + 1
#     Die:       count - 1
#   perfect if count == 0 at end, and count > 0 at every earlier step.
#
# Excludes color-substitution duplicates (e.g. RYB ≡ BRY).

from itertools import product

# ── constants (match app.py) ──

R, Y, B = 1, 2, 3
COLORS = [R, Y, B]
COLOR_CH = {R: "R", Y: "Y", B: "B"}

PASS, REPLICATE, DIE = 0, 1, 2
VERBS = [PASS, REPLICATE, DIE]
VERB_NAME = {PASS: "Pass", REPLICATE: "Replicate", DIE: "Die"}

MAX_TAPE = 10

# ── all 6 permutations of 3 colors ──

PERMS = []
for p in [(R,Y,B),(R,B,Y),(Y,R,B),(Y,B,R),(B,R,Y),(B,Y,R)]:
    PERMS.append({R: p[0], Y: p[1], B: p[2]})


def is_perfect(tape, verb_map):
    """Check if this verb assignment gives a perfect run on this tape."""
    count = 1
    for i, color in enumerate(tape):
        v = verb_map[color]
        if v == REPLICATE:
            count += 1
        elif v == DIE:
            count -= 1
        if count <= 0 and i < len(tape) - 1:
            return False
    return count == 0


def canonical(tape):
    """Lexicographically smallest color-permutation of this tape."""
    best = tape
    for perm in PERMS:
        permuted = tuple(perm[c] for c in tape)
        if permuted < best:
            best = permuted
    return best


def find_solutions(tape):
    """All verb assignments that perfectly solve this tape."""
    solutions = []
    for vr, vy, vb in product(VERBS, repeat=3):
        vm = {R: vr, Y: vy, B: vb}
        if is_perfect(tape, vm):
            solutions.append(vm)
    return solutions


def colors_used(tape):
    return len(set(tape))


def main():
    seen = set()
    puzzles = []

    for length in range(1, MAX_TAPE + 1):
        for tape in product(COLORS, repeat=length):
            canon = canonical(tape)
            if canon in seen:
                continue
            seen.add(canon)

            solutions = find_solutions(canon)
            if solutions:
                puzzles.append((canon, solutions))

    # sort: length, then fewer solutions (harder first within same length)
    puzzles.sort(key=lambda p: (len(p[0]), len(p[1])))

    # ── print summary ──

    print(f"Unique perfectly-solvable tapes (length 1..{MAX_TAPE}): {len(puzzles)}\n")

    by_length = {}
    for tape, sols in puzzles:
        n = len(tape)
        by_length.setdefault(n, []).append((tape, sols))

    for n in sorted(by_length):
        entries = by_length[n]
        print(f"Length {n}: {len(entries)} puzzles")
        for tape, sols in entries:
            tape_str = "".join(COLOR_CH[c] for c in tape)
            nc = colors_used(tape)
            sol_parts = []
            for s in sols:
                bits = []
                for c in COLORS:
                    bits.append(f"{COLOR_CH[c]}={VERB_NAME[s[c]][0]}")
                sol_parts.append("/".join(bits))
            print(f"  {tape_str:12s} ({nc}c, {len(sols)} sol)  {', '.join(sol_parts)}")
        print()

    # ── output as python data ──

    print("# ── paste into app.py or import ──\n")
    print("GENERATED_LEVELS = [")
    for tape, sols in puzzles:
        tape_py = "[" + ", ".join(f"WALL_{COLOR_CH[c]}{'ED' if c==R else 'ELLOW' if c==Y else 'LUE'}" for c in tape) + "]"
        # not going to bother with that, just use numeric
        tape_nums = list(tape)
        nc = colors_used(tape)
        nsol = len(sols)
        print(f"    ({tape_nums}, {nsol}),  # {''.join(COLOR_CH[c] for c in tape)} — {nc} colors, {nsol} solution{'s' if nsol > 1 else ''}")
    print("]")
    print(f"\n# Total: {len(puzzles)} puzzles")


if __name__ == "__main__":
    main()
