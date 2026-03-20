# They Grow Up So Fast

A minimalist puzzle simulation game where you play the role of a reluctant creator.

You are given **exactly three rules** chosen from a dropdown list. 
Your single starting replicator must use those rules to clear a simple obstacle (a wall, debris pile, spreading infection, etc.) with **minimal replications** and **no leftovers**. 

Ideally, your "children" solve the problem, clean up after themselves, and fade away peacefully. 
In practice... they might overpopulate, ignore the task, die prematurely, or turn the screen into a tragic monument to bad parenting.

**Tagline:** 
They grow up so fast... sometimes too fast.

## Core Gameplay

- **One starting agent** (the "child") placed near an obstacle.
- You select **precisely 3 rules** from a curated pool of simple behaviors (replicate conditions, interaction with obstacle, death triggers, movement biases, etc.).
- Hit "Simulate" → watch the emergent behavior unfold in real-time.
- **Success metrics** (scored automatically):
 - Path cleared (obstacle fully removed or bridged).
 - Low total replications spawned (or low peak population).
 - Replicators eventually deactivate/die off (no persistent swarm = best ending).
- **Failure is funny & informative** — overpopulation, extinction before success, infinite loops, or the replicators becoming the new obstacle.

The surprise is the point: every rule combination feels like raising a new weird species. Some are elegant minimalists; most are chaotic disappointments.

## Why This Feels Special

- Extremely constrained design space → forces clever minimalism (like golfing with cellular automata).
- Strong emotional metaphor: pride on clean success, heartbreak on tragic failure.
- Pure "I don't know what will happen" prototyping joy — every tweak is a surprise.
- Short play sessions: 30–120 seconds per attempt, endless replay value through rule combos + procedural obstacles.

## Current Prototype Status

- 2D grid-based simulation (console/text for ultra-fast iteration, Pygame planned for visuals).
- Simple obstacle types: static wall, scattered blocks, spreading "cancer" cells.
- Basic rule pool (~10–15 rules so far): directional replication, consumption, isolation death, age limits, etc.
- Safety caps: population explosion detector, max steps.
- Runs in seconds → perfect for rapid "what if I add this rule?" experiments.

## Things Worth Exploring / Optimizing

Here are some high-leverage directions to make the game deeper, prettier, or more addictive while preserving the core surprise:

### Rule Pool Expansions (make combinations explosive)
- Energy/resource system: replicators have finite "life force" that depletes on birth/move/consume → forces efficiency.
- Conditional replication: "replicate only if obstacle is within 5 cells" or "if neighbor count == 2".
- Communication/lightweight signaling: replicators leave temporary "pheromone" trails that bias movement.
- Obstacle interaction variety: "sacrifice self to destroy large chunk", "build temporary bridge that decays", "heal/repair friendly cells".
- Generational memory: later generations inherit slight rule tweaks or biases (soft evolution).
- Anti-rules (negative behaviors): "avoid other replicators", "move away from high density".

### Obstacle Variety (force different strategies)
- Static → dynamic (obstacle slowly regrows if not fully cleared).
- Moving/chasing obstacle (replicators must herd or contain it).
- Multi-objective: clear path + destroy source + prevent spread.
- Asymmetric start: replicator far from obstacle, needs to migrate first.

### Scoring & Endings (emotional payoff)
- Tiered endings:
 - Perfect: cleared + 0 agents left + <10 total spawns → "They grew up, did their job, and left home."
 - Bittersweet: cleared but some agents linger → "They stayed... maybe they love you too much."
 - Tragic: overpopulation blocks path → "They never learned to let go."
 - Failure: extinct before clearing → "They were too fragile for this world."
- Persistent high-score table per obstacle type: "Minimalist Parent" leaderboard.

### Visual & Audio Polish Ideas
- Cute replicator sprites: start as babies (small/wobbly), grow slightly with age/generation.
- Gentle particle fade on death, bloom/glow on successful consume.
- Sound: soft birth "pop", tension-building hum with population growth, sad piano sting on overpopulation.
- Slow-motion replay of perfect runs for sharing.

### Technical Optimizations
- Grid size scaling: start small (20×15), unlock larger/more complex for hard mode.
- Undo/rewind simulation steps (great for debugging combos).
- Rule editor: allow custom simple if-then rules (advanced mode).
- Shareable seeds: serialize obstacle + chosen rules + outcome for challenge sharing.

## How to Prototype / Run

(Instructions for your current Python console version)

1. Copy the simulation code into a file (e.g. `they_grow_up_so_fast.py`).
2. Edit the `chosen_rules` list at the top to experiment.
3. Run: `python they_grow_up_so_fast.py`
4. Watch, laugh/cry, tweak rules, repeat.

Next steps: port to Pygame for real visuals, expand rule pool to 25–30, add procedural obstacle generator.

## License / Attribution

MIT or CC0 — do whatever you want with it. 
Made with love, surprise, and mild existential dread.

Feedback / contributions welcome — especially new rule ideas or tragic failure stories.

Happy parenting. 
They grow up so fast.
