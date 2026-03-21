# fractal.py — self-similar level generator
#
# Two layout strategies:
#   1. Spiral fractal (depth 1-3): binary tree, all turns go right.
#      Clockwise spiral, max depth 3 before branches collide.
#   2. Multi-branch (any peak count): long trunk with independent
#      sub-fractals hanging off it. Scales to any agent count.
#
# The split mechanic:
#   Agent hits branch_color (Replicate): child ahead, parent behind.
#   Child hits turn_color (TurnRight): child turns down, cell consumed.
#   Parent walks through consumed cell, continues straight. They diverge.
#
# Solution is always:
#   seg_color   = Pass
#   branch_color = Replicate
#   turn_color   = Turn Right
#   Fixed Purple at every leaf tip = Dissolve (automatic)
#
# Different levels use different color mappings so the answer changes.

R, Y, B = 1, 2, 3
P = 6  # fixed dissolve

RIGHT = (1, 0)
DOWN  = (0, 1)
LEFT  = (-1, 0)
UP    = (0, -1)

def turn_right(dx, dy):
    return (-dy, dx)


def build_spiral_fractal(depth, seg_len=2, seg_color=R, branch_color=Y, turn_color=B):
    """
    Binary-branching spiral fractal. All turns go clockwise.
    Max depth 3 (depth 4+ causes cell collisions).

    seg_color at straight segments   → player sets to Pass
    branch_color at fork points      → player sets to Replicate
    turn_color at turn points        → player sets to Turn Right
    Fixed Purple at leaf tips        → auto Dissolve

    Returns level dict for app.py.
    """
    assert depth <= 3, "spiral fractals collide at depth 4+"
    cells = {}

    def place(x, y, c):
        cells[(x, y)] = c

    def branch(x, y, dx, dy, d):
        for i in range(seg_len):
            place(x + dx * i, y + dy * i, seg_color)
        ex, ey = x + dx * seg_len, y + dy * seg_len

        if d == 0:
            place(ex, ey, P)
            return

        place(ex, ey, branch_color)
        bx, by = ex + dx, ey + dy
        place(bx, by, turn_color)

        cdx, cdy = turn_right(dx, dy)
        branch(bx + dx, by + dy, dx, dy, d - 1)
        branch(bx + cdx, by + cdy, cdx, cdy, d - 1)

    branch(0, 0, 1, 0, depth)

    return {
        "cells": [(x, y, c) for (x, y), c in cells.items()],
        "start": (-1, 0),
        "dir": RIGHT,
    }


def build_multi_fractal(n_branches, sub_depth, seg_len=2, trunk_seg=6,
                         seg_color=R, branch_color=Y, turn_color=B):
    """
    Long trunk going right with N independent sub-fractals hanging down.
    Each sub-fractal is a spiral of sub_depth.
    Peak agents = n_branches * 2^sub_depth.

    trunk_seg controls spacing between branch points along the trunk.
    Must be large enough to prevent horizontal overlap of sub-trees.
    """
    cells = {}

    def place(x, y, c):
        cells[(x, y)] = c

    def subtree(x, y, dx, dy, d):
        """Place a spiral sub-tree rooted at (x,y) going in direction (dx,dy)."""
        for i in range(seg_len):
            place(x + dx * i, y + dy * i, seg_color)
        ex, ey = x + dx * seg_len, y + dy * seg_len

        if d == 0:
            place(ex, ey, P)
            return

        place(ex, ey, branch_color)
        bx, by = ex + dx, ey + dy
        place(bx, by, turn_color)

        cdx, cdy = turn_right(dx, dy)
        subtree(bx + dx, by + dy, dx, dy, d - 1)
        subtree(bx + cdx, by + cdy, cdx, cdy, d - 1)

    x = 0
    for i in range(n_branches):
        # trunk segment before branch
        for j in range(trunk_seg):
            place(x + j, 0, seg_color)
        x += trunk_seg

        # branch point + turn
        place(x, 0, branch_color)
        place(x + 1, 0, turn_color)

        # child sub-tree going down
        subtree(x + 1, 1, 0, 1, sub_depth)
        x += 2

    # trunk ending
    for j in range(trunk_seg):
        place(x + j, 0, seg_color)
    place(x + trunk_seg, 0, P)

    return {
        "cells": [(x, y, c) for (x, y), c in cells.items()],
        "start": (-1, 0),
        "dir": RIGHT,
    }
