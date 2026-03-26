# Asteroid Swarm — Design & Roadmap

## Elevator Pitch
An idle asteroid-mining game where simple local rules create emergent, self-organizing replicator swarms. Players start babysitting clunky machines and end up nurturing a cohesive, almost-biological super-organism. Built on the Replic8 engine.

## Emotional Arc
Cold machines → Fragile colony → Resilient swarm → Living organism

The player's relationship with the swarm mirrors parenting: anxious micromanagement → tentative trust → pride in independence → "they grew up so fast."

---

## Architecture: What We Reuse from Replic8

### Direct Reuse (copy + rename)
| Replic8 Component | Asteroid Equivalent | Changes Needed |
|---|---|---|
| Grid system (38x26 cells) | Asteroid surface (variable size) | Make dimensions configurable |
| Agent movement + direction | Bot movement | None |
| Verb system (Pass/Rep/Dissolve/Turn) | Behavior triggers | Rename verbs to mining actions |
| Cell types (R/Y/B/W/G/P) | Resource types (Nickel/Platinum/Iron/Ice) | New colors, same mechanic |
| Sandwich cells (stacked layers) | Layered ore deposits | None |
| Replication + stacking | Bot replication + queue | None |
| Sim step loop | Mining tick loop | Add error roll |
| Serialization (TGUSF1-...) | Asteroid save format | Same zlib+b64 approach |
| Editor (click to place cells) | Asteroid designer / debug tool | Reskin |
| Sound system (pentatonic) | Evolving audio (mechanical → organic) | Parameterize timbre |
| Star scoring | Mining efficiency rating | Different metrics |
| draw_grid / draw_cell | Same | Add glow effects later |

### Extend (modify existing)
| Component | Extension |
|---|---|
| Level = static puzzle | Asteroid = persistent evolving state |
| Player sets rules before sim | Rules set once, swarm runs autonomously |
| Win = clear all cells | Win = mine target quota / survive N ticks |
| Fixed cell types | Resource grades (Iron A-D = different durability) |
| Agent teams | Bot tiers (T1 basic → T3 hybrid) |
| Per-agent rules | Per-tier behavior sets |

### Build New
| Component | Description | Complexity |
|---|---|---|
| Error/mutation system | Per-replication chance of defunct/haywire | Small |
| Idle simulation | Fast-forward when player away | Medium |
| Tech tree / economy | Credits → upgrades → better bots | Medium |
| Inspector bots | Sweep + report on check-in | Small |
| Repair vs replace UI | Check-in decision screen | Small |
| Visual evolution | Rendering shifts over time | Medium (art) |
| Asteroid generation | Irregular shapes via noise | Small |
| Pheromone/signaling | Grid-based communication layer | Medium |

---

## Chunk Roadmap

### Chunk 1: Core Simulation Foundation
**Goal:** Old replicators running on an irregular asteroid shape.

**Tasks:**
1. Fork Replic8 repo → new project
2. Extract core engine into `engine.py`: grid, agents, sim_step, verbs, rendering
3. Replace square grid with asteroid shape generator:
   - Perlin noise or simplex for irregular outline
   - Fill interior with resource cells
   - Empty cells outside the asteroid boundary
4. Single asteroid loads and renders
5. Old replicator verbs work on asteroid resources
6. Basic camera/viewport (asteroid may be larger than screen)

**Reuse:** ~90% of app.py simulation + rendering
**New code:** Asteroid shape generator (~50 lines), viewport panning (~30 lines)
**Test:** Place a replicator on an asteroid, press space, watch it move and consume cells.

### Chunk 2: Resource System & Trigger Rules
**Goal:** Different resources trigger different bot behaviors. The verb system becomes a resource-behavior mapping.

**Tasks:**
1. Define resource types:
   - `NICKEL` — common, triggers replicate
   - `IRON_A/B/C/D` — grades, higher grade = more wear on bots
   - `PLATINUM` — rare, triggers replicate + speed boost
   - `ICE` — replenishes bot "health"
   - `VOID` — empty space inside asteroid (navigable but no resource)
2. Map resources to verbs: `{NICKEL: REPLICATE, IRON_A: PASS, PLATINUM: REPLICATE_BOOST, ICE: HEAL}`
3. Player configures these mappings in a UI panel (reuse Replic8 rule buttons)
4. Resources have quantity (like sandwich depth) — multiple mining passes to extract
5. Mined resources add to a global credit counter

**Reuse:** Verb assignment UI, sandwich/stack mechanic, cell colors
**New code:** Resource definitions (~20 lines), credit counter (~10 lines), heal verb (~15 lines)
**Test:** Set Nickel=Replicate, watch population grow near nickel veins. Set Iron=Pass, bots traverse iron safely.

### Chunk 3: Error Rate & Haywire/Defunct
**Goal:** Replication isn't perfect. Bots can fail or mutate. This creates tension and emergent surprises.

**Tasks:**
1. Per-replication error roll:
   - Base rate: 0.5% (configurable per bot tier)
   - Iron grade multiplier: Iron_D = 4x error rate
   - Roll on each replicate verb execution
2. Error outcomes (equal probability):
   - **Defunct:** Bot stops moving, becomes obstacle. Grey color. Must be culled or decays after N ticks.
   - **Haywire:** One random verb in bot's rule set mutates to a different verb. Pink tint. Might be beneficial!
3. Visual: defunct bots dim and stop. Haywire bots have a glitch particle effect (random pixel flicker).
4. Track error stats: total errors, defunct count, haywire count, beneficial mutations found.

**Reuse:** Replication code (add error roll after spawn)
**New code:** Error system (~40 lines), defunct/haywire states (~20 lines), visual effects (~30 lines)
**Test:** Run a large swarm for 500 ticks. See some go defunct, some go haywire. Occasionally a haywire bot discovers a useful pattern.

### Chunk 4: Self-Reporting & Inspector Bots
**Goal:** The swarm communicates its state. The player gets a dashboard on check-in.

**Tasks:**
1. **Telemetry:** Each bot periodically records: position, last resource type seen, error flag, ticks alive.
2. **Heatmap overlay:** Toggle view showing resource density, bot density, error hotspots. Colored grid overlay.
3. **Inspector bots:** Special bot type (doesn't mine, doesn't replicate). Sweeps a region, reports:
   - Resource remaining in area
   - Bot health/error summary
   - Estimated ticks to depletion
4. **Check-in summary:** When player returns from idle, show:
   - "While you were away: 342 resources mined, 12 bots replicated, 3 errors (1 beneficial mutation found)"
   - Heatmap of activity
   - Flagged events (haywire bot worth stabilizing, defunct cluster blocking path)

**Reuse:** Grid data, agent tracking
**New code:** Heatmap renderer (~50 lines), inspector bot type (~30 lines), summary screen (~60 lines)
**Test:** Run sim for 200 ticks, toggle heatmap, see activity patterns. Deploy inspector, get region report.

### Chunk 5: Repair vs Replacement
**Goal:** Every check-in has a meaningful decision. Repair costs resources but saves valuable bots.

**Tasks:**
1. **Repair cost calculator:**
   - Defunct bot: 10 credits to repair (restores to working state)
   - Haywire bot: 5 credits to stabilize (keeps mutated verb permanently)
   - Haywire bot: 3 credits to revert (restore original verbs)
2. **Check-in actions:**
   - "Cull all defunct" — free, removes dead weight
   - "Repair all defunct" — costs N credits, restores them
   - "Stabilize positive mutations" — costs N credits, locks in beneficial haywire
   - "Revert all haywire" — costs N credits, restores original behavior
   - "Ignore" — leave everything as-is
3. **Positive mutation detection:**
   - Track haywire bots' mining efficiency vs normal bots
   - Flag if haywire bot mines >20% faster than average
   - Show "This haywire bot discovered: Iron → TurnLeft (mines 34% faster). Stabilize for 5 credits?"

**Reuse:** Error states from Chunk 3
**New code:** Repair UI (~50 lines), cost calculator (~20 lines), mutation tracker (~30 lines)
**Test:** After a long run, check in, see repair options, stabilize a useful mutation, watch it spread through future replications.

### Chunk 6: Economy & Bot Upgrades
**Goal:** Resources become progression. The swarm visibly evolves.

**Tasks:**
1. **Credit system:** Mined resources → credits (Nickel=1, Iron=2-5 by grade, Platinum=10, Ice=0)
2. **Tech tree (3 tiers):**
   - **T1 Basic Bot** (free): 3% error rate, 1 resource/tick, basic verbs only
   - **T2 Specialist** (50 credits): 1.5% error rate, 2 resources/tick, can use Turn verbs
   - **T3 Hybrid** (200 credits): 0.5% error rate, 3 resources/tick, all verbs, self-repair
3. **Integration mechanic:** New bots don't replace old ones — they're added to the swarm.
   - "Deploy 5x T2 Specialists to Sector B" — click on asteroid region
   - New bots inherit the region's rule set but with their tier bonuses
4. **Upgrade existing:** Pay credits to upgrade a T1 → T2 in-place (cheaper than deploying new)
5. **Visual:** T1 = small green circle. T2 = medium blue circle with ring. T3 = large gold circle with glow.

**Reuse:** Agent team system (team = tier), per-agent rules
**New code:** Tech tree UI (~80 lines), credit economy (~30 lines), tier stats (~20 lines), deploy mechanic (~40 lines)
**Test:** Start with T1 bots, mine enough credits for T2, deploy specialists, see efficiency jump.

### Chunk 7: Idle Simulation & Persistence
**Goal:** The game runs while you're away. Coming back feels like checking on a garden.

**Tasks:**
1. **Idle mode:** When player closes game or switches away:
   - Save current state (grid + all agents + credits + tick count)
   - On return: calculate elapsed real-time, fast-forward sim
   - Fast-forward: run sim at max speed (no rendering) for elapsed ticks
   - Cap at ~10,000 ticks per idle session (prevent runaway)
2. **Persistence:** Save to JSON file:
   ```json
   {
     "seed": 42,
     "tick": 15234,
     "credits": 1850,
     "grid": [...],
     "agents": [...],
     "errors_total": 47,
     "mutations_stabilized": 3
   }
   ```
3. **Return screen:** "Welcome back! 4 hours passed (2,400 ticks simulated)"
   - Show summary (Chunk 4)
   - Show repair options (Chunk 5)
   - Show upgrade options (Chunk 6)
   - "Continue watching" → live sim view

**Reuse:** Serialization, sim loop, save/load
**New code:** Fast-forward mode (~20 lines), elapsed time calc (~15 lines), return screen (~40 lines)
**Test:** Run game, close it, wait 5 minutes, reopen. See fast-forward progress and summary.

### Chunk 8: Visual & Audio Evolution
**Goal:** The swarm looks and sounds alive. Late-game asteroids are beautiful.

**Tasks:**
1. **Visual progression (tied to swarm maturity = total ticks):**
   - Ticks 0-500: Blocky, sharp edges, mechanical colors (grey, blue, green)
   - Ticks 500-2000: Softer edges, warmer colors, occasional pulse when bots replicate
   - Ticks 2000-5000: Organic glow around active clusters, synchronized movement pulses
   - Ticks 5000+: Full organism — bots leave glowing trails, swarm breathes (expands/contracts slightly), resource veins pulse with light
2. **Audio progression (reuse pentatonic system):**
   - Early: Individual note per event (like Replic8). Mechanical tones.
   - Mid: Notes harmonize when multiple bots act simultaneously. Softer attack.
   - Late: Ambient drone that shifts with swarm activity. Mining creates rhythmic patterns. Replication creates chord progressions.
3. **Flavor text on check-in:**
   - Early: "Your bots mined 50 units of nickel."
   - Mid: "The swarm found a rich platinum vein and clustered around it."
   - Late: "The colony pulsed with satisfaction as it cleared the northern ridge."
4. **Particle effects:**
   - Mining: Small sparks in resource color
   - Replication: Bright flash
   - Error: Red glitch pixels
   - Defunct: Slow fade to grey
   - Haywire: Rapid color cycling

**Reuse:** Sound system, rendering pipeline
**New code:** Glow/trail renderer (~60 lines), audio evolution (~40 lines), particle system (~80 lines), flavor text (~30 lines)
**Test:** Run a swarm from tick 0 to 5000 on fast-forward, watch the visual and audio transform.

---

## Post-MVP Expansion

### Multiple Asteroids
- Galaxy map screen (grid of discovered asteroids)
- Each asteroid has unique seed → unique shape + resource distribution
- Player manages multiple colonies simultaneously
- Transfer bots between asteroids (costs credits)

### Shareable Seeds
- Asteroid seed = short string (like Replic8 level codes)
- "Try my asteroid: AST-7X4K2M" → same shape + resources, different player strategy
- Leaderboard: fastest to mine X resources on seed Y

### Crystallize Mode (Replic8 crossover)
- End-game: fully mined asteroid → construction mode
- Bots stop mining, start BUILDING (Crystallize verb from Replic8 design notes)
- Player designs a factory/station layout
- Bots construct it cell by cell
- Completed station generates passive credits

### Steam Workshop
- Share asteroid seeds
- Share bot rule sets ("my optimized nickel mining config")
- Share factory blueprints
- Community challenges ("mine asteroid X in under 1000 ticks")

---

## Technical Notes

### Engine Extraction
The first task is extracting the core engine from `app.py` into reusable modules:
```
engine/
  grid.py      — Grid, cell types, bounds checking
  agents.py    — Agent struct, movement, direction
  sim.py       — sim_step, verb execution, stacking
  verbs.py     — Verb definitions, get_verb, fixed verbs
  serialize.py — Save/load, level codes
  render.py    — draw_grid, draw_cell, draw_agent
  sound.py     — Tone generation, event sounds
```

Replic8 and Asteroid Swarm both import from `engine/`. Bug fixes benefit both games.

### Performance Considerations
- Idle fast-forward needs to run 10K+ ticks quickly
- Current sim_step processes agents sequentially — fine for 100 agents
- For 500+ agents: batch processing, spatial hashing for collision detection
- Grid operations are O(1) — no concern there
- Consider numpy arrays for grid if performance matters

### Save Format
Extend Replic8's TGUSF1- format:
```
ASWARM1-<base64 zlib json>
{
  "v": 1,
  "seed": 42,
  "tick": 15234,
  "credits": 1850,
  "grid": [[x, y, type, depth], ...],
  "agents": [[x, y, dx, dy, tier, error_state, verbs_hash], ...],
  "config": {"error_rate": 0.02, "rules": {...}},
  "stats": {"mined": 5000, "errors": 47, "mutations": 3}
}
```

---

## Design Principles (carried from Replic8)

1. **Brutal simplicity** — each mechanic earnable in one sentence
2. **Emergent complexity** — simple rules, surprising outcomes
3. **Visual clarity** — you should be able to read the game state at a glance
4. **Earned spectacle** — the "wow" moments come from your decisions, not cutscenes
5. **Respect the player's time** — idle mode means the game works FOR you
6. **Stories from systems** — the best moments are unscripted (a haywire bot saving a colony)
