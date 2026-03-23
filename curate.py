# curate.py — Level curation tool
# Play through all levels, tag each as KEEP / REWORK / CUT with notes.
# Saves to curate_results.json. Resume where you left off.
#
# Controls:
#   SPACE     run/pause simulation
#   R         reset level
#   K         tag as KEEP
#   X         tag as CUT
#   W         tag as REWORK
#   T         open text input for notes
#   N         next level (auto-saves tag)
#   P         previous level
#   ENTER     confirm text input
#   ESC       quit (saves progress)

import pygame
import sys
import os
import json

# import the game module
sys.path.insert(0, os.path.dirname(__file__))
from app import (
    LEVELS, NUM_LEVELS, EMPTY, AGENT, CELL, GRID_W, GRID_H,
    GRID_PX_W, GRID_PX_H, PANEL_W, WIN_W, WIN_H, FPS,
    MAX_STEPS, SIM_TICK_MS, BG, PANEL_BG, TEXT_COLOR, TEXT_DIM,
    STATUS_GREEN, STATUS_YELLOW, STATUS_RED,
    WCOLOR, FIXED_TYPES, ASSIGNABLE_TYPES, COLOR_NAMES,
    VERB_NAMES, VERB_COLOR, VERB_PASS, VERB_COUNT,
    WALL_RED, WALL_YELLOW, WALL_BLUE,
    make_grid, count_walls, sim_step, draw_grid, draw_cell,
    is_wall, TEAM_COLORS,
)

SAVE_FILE = os.path.join(os.path.dirname(__file__), "curate_results.json")

TAG_COLORS = {
    "": (60, 60, 70),          # untagged
    "KEEP": (40, 120, 60),     # green
    "REWORK": (160, 140, 30),  # yellow
    "CUT": (150, 40, 40),      # red
}

TAG_KEYS = {
    pygame.K_k: "KEEP",
    pygame.K_x: "CUT",
    pygame.K_w: "REWORK",
}


def load_curation():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return {}


def save_curation(data):
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def level_summary(level):
    """One-line summary of level structure."""
    cells = level.get("cells", [])
    n_cells = len(cells)

    # count cell types
    colors_used = set()
    has_sandwich = False
    has_fixed = False
    for x, y, c in cells:
        if isinstance(c, tuple):
            has_sandwich = True
            for cc in c:
                if cc in FIXED_TYPES:
                    has_fixed = True
                colors_used.add(cc)
        else:
            if c in FIXED_TYPES:
                has_fixed = True
            colors_used.add(c)

    # agent count
    if "agents" in level:
        n_agents = len(level["agents"])
    else:
        n_agents = 1

    mode = level.get("mode", "clear")
    per_agent = "per-agent" if level.get("per_agent_rules") else ""

    parts = [f"{n_cells}c"]
    if n_agents > 1:
        parts.append(f"{n_agents}ag")
    if has_sandwich:
        parts.append("sandwich")
    if has_fixed:
        parts.append("fixed")
    if per_agent:
        parts.append(per_agent)
    if mode != "clear":
        parts.append(mode)

    return " | ".join(parts)


def draw_curate_panel(screen, font, font_sm, level_idx, curation, verbs,
                      step, agents, walls_left, walls_start, paused, mouse_pos,
                      text_input_active, text_buffer):
    px = GRID_PX_W
    pygame.draw.rect(screen, PANEL_BG, (px, 0, PANEL_W, WIN_H))

    y = 10
    screen.blit(font.render("LEVEL CURATOR", True, (255, 200, 80)), (px + 10, y))
    y += 26

    # level number and progress
    tagged = sum(1 for k, v in curation.items() if v.get("tag", ""))
    screen.blit(font_sm.render(f"Level {level_idx + 1} / {NUM_LEVELS}", True, TEXT_COLOR), (px + 10, y))
    y += 16
    screen.blit(font_sm.render(f"Tagged: {tagged} / {NUM_LEVELS}", True, TEXT_DIM), (px + 10, y))
    y += 20

    # level info
    level = LEVELS[level_idx]
    summary = level_summary(level)
    screen.blit(font_sm.render(summary, True, TEXT_DIM), (px + 10, y))
    y += 20

    # stats
    for s in [
        f"Step: {step}",
        f"Agents: {len(agents)}",
        f"Cells: {walls_left}/{walls_start}",
    ]:
        screen.blit(font_sm.render(s, True, TEXT_DIM), (px + 10, y))
        y += 16

    # status
    y += 4
    if walls_left == 0 and len(agents) == 0:
        screen.blit(font.render("PERFECT!", True, STATUS_GREEN), (px + 10, y))
    elif walls_left == 0:
        screen.blit(font.render("CLEARED", True, STATUS_GREEN), (px + 10, y))
    elif len(agents) == 0 and step > 0:
        screen.blit(font.render("ALL DISSOLVED", True, STATUS_RED), (px + 10, y))
    elif paused and step == 0:
        screen.blit(font.render("SET RULES → SPACE", True, STATUS_YELLOW), (px + 10, y))
    elif paused:
        screen.blit(font.render("PAUSED", True, STATUS_YELLOW), (px + 10, y))
    else:
        screen.blit(font.render("RUNNING...", True, STATUS_GREEN), (px + 10, y))
    y += 28

    # current tag
    key = str(level_idx)
    entry = curation.get(key, {})
    tag = entry.get("tag", "")
    notes = entry.get("notes", "")

    # tag display
    screen.blit(font_sm.render("TAG:", True, TEXT_COLOR), (px + 10, y))
    tag_color = TAG_COLORS.get(tag, TAG_COLORS[""])
    tag_text = tag if tag else "(none)"
    pygame.draw.rect(screen, tag_color, (px + 50, y - 2, 100, 18), border_radius=3)
    screen.blit(font_sm.render(tag_text, True, (255, 255, 255)), (px + 55, y))
    y += 24

    # tag buttons
    screen.blit(font_sm.render("K=Keep  W=Rework  X=Cut", True, TEXT_DIM), (px + 10, y))
    y += 20

    # notes
    screen.blit(font_sm.render("NOTES (T to edit):", True, TEXT_COLOR), (px + 10, y))
    y += 16

    if text_input_active:
        # text input box
        pygame.draw.rect(screen, (50, 50, 70), (px + 8, y, PANEL_W - 16, 60))
        pygame.draw.rect(screen, (100, 160, 220), (px + 8, y, PANEL_W - 16, 60), 1)
        # word wrap the buffer
        chars_per_line = (PANEL_W - 24) // 7
        lines = []
        for i in range(0, max(1, len(text_buffer)), chars_per_line):
            lines.append(text_buffer[i:i + chars_per_line])
        for i, line in enumerate(lines[:3]):
            screen.blit(font_sm.render(line + ("_" if i == len(lines) - 1 else ""), True, TEXT_COLOR), (px + 12, y + 4 + i * 16))
        y += 64
        screen.blit(font_sm.render("ENTER=save  ESC=cancel", True, (100, 160, 220)), (px + 10, y))
    else:
        if notes:
            chars_per_line = (PANEL_W - 24) // 7
            for i in range(0, len(notes), chars_per_line):
                screen.blit(font_sm.render(notes[i:i + chars_per_line], True, TEXT_DIM), (px + 10, y))
                y += 14
        else:
            screen.blit(font_sm.render("(no notes yet)", True, (60, 60, 70)), (px + 10, y))
    y += 20

    # controls help
    y += 10
    screen.blit(font_sm.render("CONTROLS:", True, TEXT_COLOR), (px + 10, y))
    y += 16
    for line in [
        "SPACE  run/pause",
        "R      reset level",
        "N      next level",
        "P      previous level",
        "K      tag KEEP",
        "W      tag REWORK",
        "X      tag CUT",
        "T      edit notes",
        "ESC    save & quit",
    ]:
        screen.blit(font_sm.render(line, True, TEXT_DIM), (px + 10, y))
        y += 14

    # rules buttons
    y += 10
    screen.blit(font_sm.render("RULES (click to cycle):", True, TEXT_COLOR), (px + 10, y))
    y += 18

    btn_rects = []
    for wall_type in ASSIGNABLE_TYPES:
        if wall_type not in [WALL_RED, WALL_YELLOW, WALL_BLUE]:
            continue
        cname = COLOR_NAMES[wall_type]
        verb = verbs.get(wall_type, VERB_PASS)
        vname = VERB_NAMES[verb]
        bx, by = px + 8, y
        bw, bh = PANEL_W - 16, 28
        hovered = bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh
        bg = (50, 50, 65) if hovered else (38, 38, 52)
        pygame.draw.rect(screen, bg, (bx, by, bw, bh))
        pygame.draw.rect(screen, WCOLOR[wall_type], (bx + 4, by + 4, 20, bh - 8))
        screen.blit(font_sm.render(f"{cname} -> {vname}", True, TEXT_COLOR), (bx + 30, by + 6))
        btn_rects.append((bx, by, bw, bh, wall_type))
        y += bh + 3

    # progress bar at bottom
    bar_y = WIN_H - 20
    bar_w = PANEL_W - 20
    pygame.draw.rect(screen, (40, 40, 50), (px + 10, bar_y, bar_w, 10))
    if NUM_LEVELS > 0:
        fill = int(bar_w * (level_idx + 1) / NUM_LEVELS)
        pygame.draw.rect(screen, (80, 160, 100), (px + 10, bar_y, fill, 10))

    # mini tag overview (colored dots)
    dot_y = bar_y - 16
    dot_w = max(2, bar_w // NUM_LEVELS)
    for i in range(NUM_LEVELS):
        ik = str(i)
        t = curation.get(ik, {}).get("tag", "")
        c = TAG_COLORS.get(t, TAG_COLORS[""])
        dx = px + 10 + (bar_w * i) // NUM_LEVELS
        pygame.draw.rect(screen, c, (dx, dot_y, max(1, dot_w - 1), 8))
    # current position marker
    cx = px + 10 + (bar_w * level_idx) // NUM_LEVELS
    pygame.draw.rect(screen, (255, 255, 255), (cx, dot_y - 2, max(2, dot_w), 12), 1)

    return btn_rects


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("TGUSF — Level Curator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 15)
    font_sm = pygame.font.SysFont("consolas", 13)

    curation = load_curation()
    level_idx = 0

    # find first untagged level to start from
    for i in range(NUM_LEVELS):
        if str(i) not in curation or not curation[str(i)].get("tag"):
            level_idx = i
            break

    verbs = {WALL_RED: VERB_PASS, WALL_YELLOW: VERB_PASS, WALL_BLUE: VERB_PASS}
    grid, agents, underneath = make_grid(LEVELS[level_idx])
    walls_start = count_walls(grid, underneath)
    paused = True
    step = 0
    total_spawned = 1
    peak_pop = 1
    last_sim_tick = 0
    btn_rects = []

    text_input_active = False
    text_buffer = ""

    def reset():
        nonlocal grid, agents, underneath, walls_start, paused, step
        grid, agents, underneath = make_grid(LEVELS[level_idx])
        walls_start = count_walls(grid, underneath)
        paused = True
        step = 0

    def change(new_idx):
        nonlocal level_idx, verbs
        level_idx = new_idx % NUM_LEVELS
        verbs = {WALL_RED: VERB_PASS, WALL_YELLOW: VERB_PASS, WALL_BLUE: VERB_PASS}
        reset()

    running = True
    while running:
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_curation(curation)
                running = False

            elif event.type == pygame.KEYDOWN:
                if text_input_active:
                    if event.key == pygame.K_RETURN:
                        # save notes
                        key = str(level_idx)
                        if key not in curation:
                            curation[key] = {}
                        curation[key]["notes"] = text_buffer
                        save_curation(curation)
                        text_input_active = False
                    elif event.key == pygame.K_ESCAPE:
                        text_input_active = False
                    elif event.key == pygame.K_BACKSPACE:
                        text_buffer = text_buffer[:-1]
                    else:
                        if event.unicode and len(text_buffer) < 200:
                            text_buffer += event.unicode
                else:
                    if event.key == pygame.K_ESCAPE:
                        save_curation(curation)
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_r:
                        reset()
                    elif event.key == pygame.K_n:
                        change(level_idx + 1)
                    elif event.key == pygame.K_p:
                        change(level_idx - 1)
                    elif event.key in TAG_KEYS:
                        key = str(level_idx)
                        tag = TAG_KEYS[event.key]
                        if key not in curation:
                            curation[key] = {}
                        # toggle: if already this tag, clear it
                        if curation[key].get("tag") == tag:
                            curation[key]["tag"] = ""
                        else:
                            curation[key]["tag"] = tag
                        save_curation(curation)
                    elif event.key == pygame.K_t:
                        # start text input
                        key = str(level_idx)
                        text_buffer = curation.get(key, {}).get("notes", "")
                        text_input_active = True

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for bx, by, bw, bh, wall_type in btn_rects:
                    if bx <= mouse_pos[0] < bx + bw and by <= mouse_pos[1] < by + bh:
                        verbs[wall_type] = (verbs[wall_type] + 1) % VERB_COUNT
                        break

        # sim
        walls_left = count_walls(grid, underneath)
        game_over = (walls_left == 0) or (len(agents) == 0 and step > 0) or (step >= MAX_STEPS)
        if not paused and not game_over and now - last_sim_tick >= SIM_TICK_MS:
            last_sim_tick = now
            agents, spawned = sim_step(agents, grid, [verbs], underneath)
            step += 1

        # draw
        walls_left = count_walls(grid, underneath)
        screen.fill(BG)
        draw_grid(screen, grid, agents, underneath)
        btn_rects = draw_curate_panel(screen, font, font_sm, level_idx, curation, verbs,
                                       step, agents, walls_left, walls_start, paused, mouse_pos,
                                       text_input_active, text_buffer)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
