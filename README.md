# They Grow Up So Fast

A puzzle game where you assign simple rules to colored cells, then watch your replicator agents clear the board through emergent behavior.

## How to Play

```bash
cd theygrowupsofast
python app.py
```

**Controls:** SPACE run/pause, R reset, N/P next/prev level, E editor, ESC quit

## Game Mechanics

- **Assign a verb to each color** (Red, Yellow, Blue): Pass, Replicate, Dissolve, Turn Left, Turn Right
- **Every contact consumes** the cell — the verb determines the side effect
- **Perfect solution** = all cells consumed AND zero agents remaining
- One rule set governs everything — find the assignment that works

## Level Progression (49 levels)

1. **1D tapes** (L1-10): Learn verbs on simple color sequences
2. **Fixed cells** (L4-6): Green auto-replicates, Purple auto-dissolves — teaching by observation
3. **Grey road** (L7+): Grey cells auto-pass, assignable colors only at decision points
4. **2D shapes** (L11-14): L-shapes, U-shapes with turns
5. **Fractals** (L15-18): Self-similar patterns — solve the unit, solve the whole thing
6. **Key + fractal** (L19-26): Solve a small timing puzzle, watch it amplify across a fractal
7. **Sandwiches** (L19-21): Stacked cells — each agent pops the top layer, different agents get different verbs
8. **Air gaps** (L24-26): Empty cells for timing control without consuming
9. **Multi-agent** (L27-42): Two agents, shared or separate rule sets
10. **Dual-fractal** (L48-49): Two agents clear a huge grid from opposite corners

## Key Concepts

- **Sandwiches**: Stacked colored cells (drawn as horizontal stripes). Top color consumed first.
- **Fixed cells**: Green (replicate), Purple (dissolve), Orange (turn R), Cyan (turn L), Grey (pass) — always do their thing, no player choice.
- **Per-agent rules**: Later levels give each agent its own verb assignment.
- **Fractal levels**: Self-similar patterns where one solution propagates across the whole grid.

## Cell Types

### Campaign (assignable — player picks verb)
| Cell | Color | Description |
|------|-------|-------------|
| Red | Bright red | Player assigns verb |
| Yellow | Gold | Player assigns verb |
| Blue | Deep blue | Player assigns verb |

### Campaign (fixed — always perform their action)
| Cell | Color | Action |
|------|-------|--------|
| Green | Bright green | Always replicate |
| Purple | Violet | Always dissolve |
| Orange | Warm orange | Always turn right |
| Cyan | Light blue | Always turn left |
| Grey | Neutral grey | Always pass (road filler) |

### Editor-only (community level creation)
| Cell | Color | Action |
|------|-------|--------|
| Pink (Reverse) | Rose pink | Agent reverses direction 180 degrees |
| Lime (Skip) | Yellow-green | Agent consumes cell and jumps over the next |
| Gate (4 dirs) | Light grey + arrow | Passable in one direction only, blocks others |
| Teleport In | Magenta (hollow circle) | Agent enters here, exits at Teleport Out |
| Teleport Out | Magenta (filled circle) | Paired exit for Teleport In |

## Level Editor

Press **E** to enter the editor:
- Left-click to place cells, right-click to erase
- Shift+click to place agents (shift+click again to cycle direction)
- **S** to build sandwich stacks, **D** to clear stack
- **T** to test, **C** to copy level code, **V** to paste
- **1/2/3** to set agent count, **A** to toggle per-agent rules

Level codes (e.g. `TGUSF1-...`) can be shared via clipboard — paste in Discord, itch.io comments, etc.

## Architecture

- `app.py` — game loop, rendering, editor, serialization (~1300 lines)
- `fractal.py` — fractal level generators
- `algo.py` — brute-force puzzle enumerator (generates solvable tapes)

## Future Directions

### Crystallize verb (late-game unlock)
Agent stops moving and becomes a permanent cell. Inverts the puzzle: instead of "clear this" it's "build this target shape." Uses the same replication/fractal mechanics — agents swarm then freeze into a pattern. Could combine both: consume raw materials on the left, crystallize into target shape on the right. One new verb, massive design space expansion. **Explore this for final 10% of levels.**

### Editor-only experimental cells (added, not used in campaign)
These are available in the level editor for community creators to explore. We deliberately keep them out of the campaign to preserve the clean core mechanic, but players may discover amazing puzzles with them:
- **Reverse** — 180-degree bounce. Creates ping-pong oscillation patterns.
- **Skip** — jump over next cell. Spacing and timing puzzles.
- **One-way gates** — directional barriers. Asymmetric paths without consuming.
- **Teleport pairs** — warp between two linked cells. Community catnip.

### Ideas explored and shelved
- **Navigate obstacle** (get A to B): Weaker puzzle, no spectacle. Shelved.
- **Tidy up** (rearrange cells): Needs push/swap verb, breaks consume-everything unity. Different game.
- **Alternator cells** (flip on consume): Adds state, high complexity. Season 2 material.
- **Fork verb** (split both directions): Sandwich + replicate already does this. Not needed.
- **Timer cells** (auto-dissolve after N ticks): Complex (needs per-cell tick counter). Save for later.

### Platform features
- Procedural level generator with heuristic scoring (brute-force + quality filter)
- Community level sharing via clipboard codes (itch.io/Steam) — IMPLEMENTED
- Level editor with full palette — IMPLEMENTED
- Level browser/rating system (server-backed, later)
