"""
Infinity Snail v2 - spatial explorer
A VPython simulation of an organism that plays with limits, convergence, and infinite approach while exploring space.

Run:
    python infinity_snail_v2_spatial_explorer.py

Controls:
    W/A/S/D  - nudge snail on the ground plane
    Space/C  - raise/lower camera focus marker lightly
    M        - switch autonomous mode
    P        - pause/resume
    R        - reset
    T        - toggle trail visibility
    H        - toggle help panel
    Arrow keys - pan camera
    J/L      - rotate camera left/right
    I/K      - rotate camera up/down
    +/-      - zoom camera
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Infinity Snail v2 - spatial explorer",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.55, -0.42, -0.72)
scene.range = 18

WORLD_RADIUS = 13.5
GROUND_Y = 0
MIN_LIMIT_GAP = 1.65       # target is never allowed to collapse directly onto the limit orb
SCOUT_RADIUS_MIN = 5.0     # scout goals are deliberately far enough to pull the snail outward
paused = False
show_help = True
show_trail = True
manual_push = vector(0, 0, 0)
keys_down = set()

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def flat(v):
    return vector(v.x, 0, v.z)


def mag2d(v):
    return math.sqrt(v.x * v.x + v.z * v.z)


def norm2d(v, fallback=vector(1, 0, 0)):
    m = mag2d(v)
    if m < 1e-7:
        return fallback
    return vector(v.x / m, 0, v.z / m)


def lerp(a, b, t):
    return a * (1 - t) + b * t


def rand_dir():
    a = random.uniform(0, 2 * math.pi)
    return vector(math.cos(a), 0, math.sin(a))


def format_float(x):
    if abs(x) >= 100:
        return f"{x:.0f}"
    if abs(x) >= 10:
        return f"{x:.1f}"
    return f"{x:.2f}"

# -----------------------------
# World objects
# -----------------------------
ground = box(
    pos=vector(0, -0.045, 0),
    size=vector(WORLD_RADIUS * 2.2, 0.05, WORLD_RADIUS * 2.2),
    color=vector(0.88, 0.94, 0.90),
    opacity=0.82,
)

# grid lines
grid_lines = []
for i in range(-13, 14):
    col = vector(0.74, 0.82, 0.78) if i != 0 else vector(0.55, 0.65, 0.62)
    grid_lines.append(curve(pos=[vector(i, 0.003, -13.5), vector(i, 0.003, 13.5)], color=col, radius=0.01))
    grid_lines.append(curve(pos=[vector(-13.5, 0.003, i), vector(13.5, 0.003, i)], color=col, radius=0.01))

boundary = ring(pos=vector(0, 0.02, 0), axis=vector(0, 1, 0), radius=WORLD_RADIUS, thickness=0.035,
                color=vector(0.45, 0.58, 0.53), opacity=0.45)

origin_marker = sphere(pos=vector(0, 0.08, 0), radius=0.18, color=vector(0.3, 0.55, 0.85), opacity=0.75)
origin_label = label(pos=vector(0, 0.55, 0), text="0", height=13, box=False, opacity=0, color=vector(0.25, 0.35, 0.45))

# The far ideal destination and the current reachable target.
ideal_goal = vector(10.8, 0, 0)
current_target = vector(5.4, 0, 0)
previous_target = vector(0, 0, 0)

ideal_goal_marker = sphere(pos=ideal_goal + vector(0, 0.18, 0), radius=0.28, color=vector(1.0, 0.72, 0.25), opacity=0.45)
ideal_goal_ring = ring(pos=ideal_goal + vector(0, 0.04, 0), axis=vector(0, 1, 0), radius=0.62,
                       thickness=0.025, color=vector(1.0, 0.62, 0.15), opacity=0.45)
ideal_goal_label = label(pos=ideal_goal + vector(0, 0.95, 0), text="limit / never fully reached", height=12,
                         box=False, opacity=0, color=vector(0.55, 0.37, 0.08))

current_target_marker = sphere(pos=current_target + vector(0, 0.18, 0), radius=0.23, color=vector(0.15, 0.55, 1.0), opacity=0.78)
current_target_ring = ring(pos=current_target + vector(0, 0.04, 0), axis=vector(0, 1, 0), radius=0.48,
                           thickness=0.025, color=vector(0.12, 0.42, 0.95), opacity=0.70)
current_target_label = label(pos=current_target + vector(0, 0.72, 0), text="next halfway point", height=12,
                             box=False, opacity=0, color=vector(0.10, 0.25, 0.55))

approach_line = curve(pos=[vector(0, 0.04, 0), ideal_goal + vector(0, 0.04, 0)], color=vector(0.78, 0.65, 0.35), radius=0.025)
remaining_line = curve(pos=[current_target + vector(0, 0.08, 0), ideal_goal + vector(0, 0.08, 0)],
                       color=vector(1.0, 0.55, 0.22), radius=0.018)

# ghost markers for previous halfway points
halfway_markers = []

# -----------------------------
# Snail body
# -----------------------------
snail_pos = vector(-10.5, 0, -4.0)
snail_vel = vector(0.03, 0, 0.02)
heading = norm2d(current_target - snail_pos)

body = ellipsoid(pos=snail_pos + vector(0, 0.35, 0), length=1.15, height=0.48, width=0.68,
                 color=vector(0.44, 0.78, 0.58), opacity=0.96)
shell = sphere(pos=snail_pos + vector(-0.33, 0.62, 0), radius=0.42, color=vector(0.93, 0.72, 0.40), opacity=0.96)
shell_ring_1 = ring(pos=shell.pos, axis=vector(0, 1, 0), radius=0.30, thickness=0.022, color=vector(0.64, 0.42, 0.18))
shell_ring_2 = ring(pos=shell.pos + vector(0, 0.015, 0), axis=vector(0, 0, 1), radius=0.24, thickness=0.018, color=vector(0.72, 0.50, 0.22))
head = sphere(pos=snail_pos + heading * 0.62 + vector(0, 0.36, 0), radius=0.26, color=vector(0.52, 0.86, 0.63))
left_eye = sphere(pos=head.pos + vector(0.12, 0.25, 0.12), radius=0.045, color=vector(0.04, 0.08, 0.06))
right_eye = sphere(pos=head.pos + vector(0.12, 0.25, -0.12), radius=0.045, color=vector(0.04, 0.08, 0.06))
left_stalk = curve(pos=[head.pos, left_eye.pos], color=vector(0.38, 0.68, 0.45), radius=0.025)
right_stalk = curve(pos=[head.pos, right_eye.pos], color=vector(0.38, 0.68, 0.45), radius=0.025)

trail = curve(pos=[snail_pos + vector(0, 0.035, 0)], radius=0.04, color=vector(0.48, 0.78, 0.88))
trail.opacity = 0.60

# -----------------------------
# Math state
# -----------------------------
iteration = 0
step_fraction = 0.5
modes = ["converge", "frontier_scout", "spiral_question", "oscillate", "wander_limit", "reset_drift"]
mode_index = 0
mode = modes[mode_index]
mode_timer = 0.0
trail_timer = 0.0
last_target_advance_t = 0.0
snail_distance_record = []
recent_positions = []
scout_goal = vector(-7.0, 0, 7.0)
scout_timer = 0.0
orbit_escape_timer = 0.0
limit_relocation_count = 0
visited_cells = set()

# small collectible symbols that affect convergence behavior
symbols = []
symbol_values = ["1/2", "1/3", "2/3", "ε", "∞", "lim", "+", "?"]


def make_symbol():
    r = random.uniform(2.0, WORLD_RADIUS - 1.2)
    a = random.uniform(0, 2 * math.pi)
    txt = random.choice(symbol_values)
    p = vector(math.cos(a) * r, 0.16, math.sin(a) * r)
    s = sphere(pos=p, radius=0.18, color=vector(0.75, 0.62, 1.0), opacity=0.74)
    lab = label(pos=p + vector(0, 0.42, 0), text=txt, height=11, box=False, opacity=0, color=vector(0.28, 0.20, 0.52))
    return {"ball": s, "label": lab, "text": txt, "alive": True, "phase": random.random() * 6.28}

for _ in range(16):
    symbols.append(make_symbol())


def choose_scout_goal(away_from=None):
    """Choose a wide horizontal waypoint that encourages coverage of new space."""
    if away_from is None:
        away_from = current_target
    best_point = None
    best_score = -999999
    for _ in range(34):
        # Prefer outer ring positions, but keep enough margin for edge recovery.
        r = random.uniform(SCOUT_RADIUS_MIN, WORLD_RADIUS - 1.15)
        a = random.uniform(0, 2 * math.pi)
        candidate = vector(math.cos(a) * r, 0, math.sin(a) * r)
        cell = (round(candidate.x / 2.2), round(candidate.z / 2.2))
        novelty = 2.4 if cell not in visited_cells else -0.7
        from_snail = mag2d(candidate - snail_pos)
        from_target = mag2d(candidate - away_from)
        from_goal = mag2d(candidate - ideal_goal)
        score = from_snail * 0.38 + from_target * 0.55 + from_goal * 0.20 + novelty + random.uniform(0, 1.0)
        if score > best_score:
            best_score = score
            best_point = candidate
    return best_point if best_point is not None else rand_dir() * (WORLD_RADIUS * 0.65)


def relocate_limit(reason="near"):
    """Move the limit to a fresh far point and restart the next reachable target.

    The limit is still unreachable, but it no longer becomes a fixed orbital trap.
    """
    global ideal_goal, current_target, previous_target, iteration, scout_goal, scout_timer
    global orbit_escape_timer, limit_relocation_count
    old_goal = vector(ideal_goal.x, 0, ideal_goal.z)
    new_goal = choose_scout_goal(away_from=old_goal)
    # Keep the new limit separated from the current snail position.
    if mag2d(new_goal - snail_pos) < 6.0:
        new_goal = norm2d(new_goal - snail_pos, rand_dir()) * 7.5 + snail_pos
        if mag2d(new_goal) > WORLD_RADIUS - 1.3:
            new_goal = norm2d(new_goal) * (WORLD_RADIUS - 1.3)
    ideal_goal = vector(new_goal.x, 0, new_goal.z)
    previous_target = vector(snail_pos.x, 0, snail_pos.z)
    current_target = lerp(previous_target, ideal_goal, 0.52)
    iteration = 0
    scout_goal = choose_scout_goal(away_from=ideal_goal)
    scout_timer = 7.5
    orbit_escape_timer = 6.0
    limit_relocation_count += 1
    ideal_goal_marker.pos = ideal_goal + vector(0, 0.18, 0)
    ideal_goal_ring.pos = ideal_goal + vector(0, 0.04, 0)
    ideal_goal_label.pos = ideal_goal + vector(0, 0.95, 0)
    ideal_goal_label.text = f"limit moved: {reason}"
    approach_line.clear()
    approach_line.append(vector(0, 0.04, 0))
    approach_line.append(ideal_goal + vector(0, 0.04, 0))


def orbit_detected():
    """Detect small repeated motion near a target/limit trap."""
    if len(recent_positions) < 70:
        return False
    last = recent_positions[-1]
    near_current = mag2d(last - current_target) < 2.4
    near_limit = mag2d(last - ideal_goal) < 2.8
    if not (near_current or near_limit):
        return False
    center = current_target if near_current else ideal_goal
    radii = [mag2d(p - center) for p in recent_positions[-50:]]
    radial_change = max(radii) - min(radii)
    net_displacement = mag2d(recent_positions[-1] - recent_positions[-50])
    return radial_change < 0.75 and net_displacement < 1.4

# -----------------------------
# UI labels
# -----------------------------
status = label(
    pos=vector(-13.0, 6.2, 0),
    text="",
    height=13,
    box=True,
    border=8,
    opacity=0.72,
    color=vector(0.05, 0.12, 0.14),
    background=vector(0.90, 0.96, 0.93),
)

help_label = label(
    pos=vector(8.3, 6.15, 0),
    text="",
    height=11,
    box=True,
    border=8,
    opacity=0.72,
    color=vector(0.08, 0.12, 0.16),
    background=vector(0.95, 0.97, 1.0),
)

# -----------------------------
# Core behavior
# -----------------------------
def reset_sim():
    global snail_pos, snail_vel, heading, ideal_goal, current_target, previous_target, iteration, step_fraction
    global mode_index, mode, mode_timer, trail_timer, last_target_advance_t, halfway_markers, trail
    global scout_goal, scout_timer, orbit_escape_timer, limit_relocation_count, visited_cells
    snail_pos = vector(-10.5, 0, -4.0)
    snail_vel = vector(0.03, 0, 0.02)
    ideal_goal = vector(10.8, 0, 0)
    heading = norm2d(current_target - snail_pos)
    previous_target = vector(snail_pos.x, 0, snail_pos.z)
    current_target = lerp(previous_target, ideal_goal, step_fraction)
    scout_goal = vector(-7.0, 0, 7.0)
    scout_timer = 0.0
    orbit_escape_timer = 0.0
    limit_relocation_count = 0
    visited_cells.clear()
    ideal_goal_marker.pos = ideal_goal + vector(0, 0.18, 0)
    ideal_goal_ring.pos = ideal_goal + vector(0, 0.04, 0)
    ideal_goal_label.pos = ideal_goal + vector(0, 0.95, 0)
    ideal_goal_label.text = "limit / never fully reached"
    approach_line.clear()
    approach_line.append(vector(0, 0.04, 0))
    approach_line.append(ideal_goal + vector(0, 0.04, 0))
    iteration = 0
    step_fraction = 0.5
    mode_index = 0
    mode = modes[mode_index]
    mode_timer = 0.0
    trail_timer = 0.0
    last_target_advance_t = 0.0
    for m in halfway_markers:
        m.visible = False
    halfway_markers = []
    trail.visible = False
    trail = curve(pos=[snail_pos + vector(0, 0.035, 0)], radius=0.04, color=vector(0.48, 0.78, 0.88))
    trail.opacity = 0.60 if show_trail else 0.0
    recent_positions.clear()
    snail_distance_record.clear()
    for obj in symbols:
        obj["ball"].visible = False
        obj["label"].visible = False
    symbols.clear()
    for _ in range(16):
        symbols.append(make_symbol())


def switch_mode():
    global mode_index, mode, mode_timer
    mode_index = (mode_index + 1) % len(modes)
    mode = modes[mode_index]
    mode_timer = 0.0


def advance_target():
    """Move the current target partway toward the ideal limit without collapsing onto it."""
    global current_target, previous_target, iteration, last_target_advance_t
    global scout_goal, scout_timer, orbit_escape_timer
    previous_target = vector(current_target.x, 0, current_target.z)
    proposed_target = lerp(previous_target, ideal_goal, step_fraction)

    # If repeated halfway steps would visually merge with the limit orb, move the limit instead.
    # This keeps the concept of infinite approach while giving the organism new territory.
    if mag2d(ideal_goal - proposed_target) < MIN_LIMIT_GAP:
        relocate_limit("gap too small")
        return

    current_target = proposed_target
    iteration += 1
    last_target_advance_t = mode_timer

    # Every few successful approaches, force a broad scouting excursion before more convergence.
    if iteration > 0 and iteration % 5 == 0:
        scout_goal = choose_scout_goal(away_from=current_target)
        scout_timer = 5.5
        orbit_escape_timer = max(orbit_escape_timer, 3.5)

    # Leave a persistent mathematical marker.
    mk = ring(pos=previous_target + vector(0, 0.06, 0), axis=vector(0, 1, 0), radius=0.22,
              thickness=0.014, color=vector(0.22, 0.48, 0.85), opacity=0.30)
    halfway_markers.append(mk)
    if len(halfway_markers) > 90:
        old = halfway_markers.pop(0)
        old.visible = False


def update_target_visuals():
    current_target_marker.pos = current_target + vector(0, 0.18, 0)
    current_target_ring.pos = current_target + vector(0, 0.04, 0)
    current_target_label.pos = current_target + vector(0, 0.72, 0)
    current_target_label.text = f"target {iteration}: reachable point"
    remaining_line.clear()
    remaining_line.append(current_target + vector(0, 0.08, 0))
    remaining_line.append(ideal_goal + vector(0, 0.08, 0))


def update_snail_visuals(t):
    global heading
    if mag2d(snail_vel) > 0.02:
        heading = norm2d(snail_vel, heading)
    side = vector(-heading.z, 0, heading.x)
    bob = math.sin(t * 4.4) * 0.035
    body.pos = snail_pos + vector(0, 0.35 + bob, 0)
    body.axis = heading
    shell.pos = snail_pos - heading * 0.28 + vector(0, 0.62 + bob * 0.35, 0)
    shell_ring_1.pos = shell.pos
    shell_ring_1.axis = vector(0, 1, 0)
    shell_ring_2.pos = shell.pos + vector(0, 0.015, 0)
    shell_ring_2.axis = heading
    head.pos = snail_pos + heading * 0.63 + vector(0, 0.37 + bob, 0)
    left_eye.pos = head.pos + heading * 0.13 + side * 0.14 + vector(0, 0.25, 0)
    right_eye.pos = head.pos + heading * 0.13 - side * 0.14 + vector(0, 0.25, 0)
    left_stalk.clear(); left_stalk.append(head.pos); left_stalk.append(left_eye.pos)
    right_stalk.clear(); right_stalk.append(head.pos); right_stalk.append(right_eye.pos)

    # Shell color subtly tightens as the remaining limit distance shrinks.
    remaining = mag2d(ideal_goal - current_target)
    tightness = 1 - clamp(remaining / mag2d(ideal_goal), 0, 1)
    shell.color = vector(0.90 + 0.08 * tightness, 0.72 - 0.10 * tightness, 0.38 + 0.20 * tightness)
    body.color = vector(0.40 + 0.12 * tightness, 0.76 + 0.08 * math.sin(t * 0.7), 0.54 + 0.10 * tightness)


def loop_detected():
    if len(recent_positions) < 80:
        return False
    first = recent_positions[0]
    last = recent_positions[-1]
    displacement = mag2d(last - first)
    spread = max(mag2d(p - last) for p in recent_positions)
    return displacement < 0.7 and spread < 1.2


def choose_force(dt, t):
    global mode, mode_index, mode_timer, scout_goal, scout_timer, orbit_escape_timer
    to_target = flat(current_target - snail_pos)
    to_goal = flat(ideal_goal - snail_pos)
    to_scout = flat(scout_goal - snail_pos)
    d_target = mag2d(to_target)
    d_goal = mag2d(to_goal)
    d_scout = mag2d(to_scout)
    target_dir = norm2d(to_target, heading)
    goal_dir = norm2d(to_goal, heading)
    scout_dir = norm2d(to_scout, rand_dir())
    side = vector(-target_dir.z, 0, target_dir.x)

    # Decay exploration timers here so the force chooser can override target fixation.
    if scout_timer > 0:
        scout_timer = max(0, scout_timer - dt)
    if orbit_escape_timer > 0:
        orbit_escape_timer = max(0, orbit_escape_timer - dt)

    force = vector(0, 0, 0)

    # Refresh scout waypoint when reached or stale.
    if d_scout < 0.9 or (mode_timer > 5 and random.random() < 0.006):
        scout_goal = choose_scout_goal(away_from=current_target)
        to_scout = flat(scout_goal - snail_pos)
        scout_dir = norm2d(to_scout, rand_dir())

    # Escape has priority. It sends the snail away from the collapsed orbit area.
    if orbit_escape_timer > 0:
        away_target = norm2d(snail_pos - current_target, rand_dir())
        away_limit = norm2d(snail_pos - ideal_goal, rand_dir())
        force += scout_dir * 0.076 + away_target * 0.038 + away_limit * 0.026
        force += vector(-scout_dir.z, 0, scout_dir.x) * math.sin(t * 1.15) * 0.034
        return force + manual_push * 0.085

    if scout_timer > 0:
        # Broad excursions keep the snail from living only on the current limit line.
        force += scout_dir * 0.074
        force += vector(-scout_dir.z, 0, scout_dir.x) * math.sin(t * 0.75 + iteration) * 0.026

    elif mode == "converge":
        # Mostly approach the reachable target, but with enough sideways arc to avoid fixed orbiting.
        force += target_dir * 0.052
        force += side * math.sin(t * 0.55 + iteration * 0.7) * 0.026
        if d_target < 2.2:
            force += scout_dir * 0.030

    elif mode == "frontier_scout":
        # Purposefully ignore the nearest target for a while and map a wider region.
        force += scout_dir * 0.078
        force += goal_dir * 0.012
        force += rand_dir() * 0.010

    elif mode == "spiral_question":
        # The spiral is now loose and outward biased, not a tight orbit around the target.
        orbit = side * (0.045 if d_target < 3.0 else 0.026)
        outward = norm2d(snail_pos - current_target, rand_dir()) * (0.030 if d_target < 2.4 else 0.0)
        force += target_dir * 0.032 + orbit * math.sin(t * 0.45 + 1.0) + outward + scout_dir * 0.020

    elif mode == "oscillate":
        # Alternating error with lateral travel across the field.
        wave = math.sin(t * 1.8)
        force += target_dir * (0.045 + 0.016 * wave)
        force += side * wave * 0.030
        force += scout_dir * 0.020

    elif mode == "wander_limit":
        # Explore nearby symbols, but choose farther symbols first when available.
        nearest = None
        best_score = -999
        for s in symbols:
            if not s["alive"]:
                continue
            pos = flat(s["ball"].pos)
            dist = mag2d(pos - snail_pos)
            if dist < 8.5:
                score = dist * 0.18 + mag2d(pos - current_target) * 0.10 + random.uniform(0, 0.8)
                if score > best_score:
                    best_score = score
                    nearest = s
        if nearest:
            force += norm2d(flat(nearest["ball"].pos) - snail_pos, heading) * 0.060
        else:
            force += scout_dir * 0.055 + rand_dir() * 0.012
        force += side * math.sin(t * 0.9) * 0.022

    elif mode == "reset_drift":
        # Drift away from the limit line, then return after enough error accumulates.
        away = norm2d(snail_pos - current_target, rand_dir())
        if d_target < 3.0:
            force += away * 0.058 + scout_dir * 0.040
        else:
            force += target_dir * 0.045 + scout_dir * 0.016

    # Soft edge repulsion with tangent motion so edge contact becomes a turn, not a stall.
    r = mag2d(snail_pos)
    if r > WORLD_RADIUS - 2.2:
        inward = norm2d(-snail_pos, -heading)
        tangent = vector(-inward.z, 0, inward.x)
        force += inward * (0.055 + 0.080 * clamp((r - (WORLD_RADIUS - 2.2)) / 2.2, 0, 1))
        force += tangent * math.sin(t * 0.8) * 0.030

    # Break local loops with a broad scout movement and a temporary target escape.
    if loop_detected() or orbit_detected():
        scout_goal = choose_scout_goal(away_from=current_target)
        scout_timer = 6.0
        orbit_escape_timer = 4.5
        force += scout_dir * 0.082 + side * 0.045

    force += manual_push * 0.085
    return force

def handle_symbols(t):
    global step_fraction, mode_index, mode, mode_timer
    for s in symbols:
        if not s["alive"]:
            continue
        s["phase"] += 0.04
        s["ball"].pos.y = 0.16 + 0.05 * math.sin(s["phase"])
        s["label"].pos = s["ball"].pos + vector(0, 0.42, 0)
        dist = mag2d(flat(s["ball"].pos) - snail_pos)
        if dist < 0.72:
            s["alive"] = False
            s["ball"].visible = False
            s["label"].visible = False
            txt = s["text"]
            if txt == "1/3":
                step_fraction = 1 / 3
            elif txt == "2/3":
                step_fraction = 2 / 3
            elif txt == "1/2":
                step_fraction = 0.5
            elif txt == "ε":
                # epsilon tightens the threshold for accepting near-target arrival.
                pass
            elif txt == "∞":
                step_fraction = 0.5
                mode_index = 1
                mode = modes[mode_index]
                mode_timer = 0.0
            elif txt == "lim":
                mode_index = 0
                mode = modes[mode_index]
                mode_timer = 0.0
            elif txt == "+":
                step_fraction = clamp(step_fraction + 0.08, 0.25, 0.75)
            elif txt == "?":
                switch_mode()


def update_status(t):
    d_to_current = mag2d(current_target - snail_pos)
    remaining_limit = mag2d(ideal_goal - current_target)
    d_snail_to_limit = mag2d(ideal_goal - snail_pos)
    convergence = 1 - clamp(remaining_limit / mag2d(ideal_goal), 0, 1)
    status.text = (
        f"Infinity Snail\n"
        f"mode: {mode} {'PAUSED' if paused else ''}\n"
        f"iteration: {iteration}\n"
        f"step fraction: {step_fraction:.2f}\n"
        f"distance to current target: {format_float(d_to_current)}\n"
        f"remaining target-to-limit: {format_float(remaining_limit)}\n"
        f"snail-to-limit distance: {format_float(d_snail_to_limit)}\n"
        f"convergence of target: {convergence * 100:.1f}%\n"
        f"scout timer: {scout_timer:.1f} | escape: {orbit_escape_timer:.1f}\n"
        f"limit relocations: {limit_relocation_count}\n"
        f"visited cells: {len(visited_cells)}\n"
        f"trail points: {trail.npoints if hasattr(trail, 'npoints') else '?'}"
    )
    help_label.visible = show_help
    if show_help:
        help_label.text = (
            "Controls\n"
            "WASD: nudge snail\n"
            "M: switch mode\n"
            "P: pause/resume\n"
            "R: reset\n"
            "T: trail on/off\n"
            "H: help on/off\n"
            "Arrows/JL/IK/+/-: camera\n\n"
            "Meaning\n"
            "The blue target moves partway\n"
            "toward the golden limit, but\n"
            "does not merge with the orb.\n"
            "When trapped, the snail scouts\n"
            "new space before returning."
        )

# -----------------------------
# Input handling
# -----------------------------
def keydown(evt):
    global paused, show_help, show_trail, manual_push
    k = evt.key.lower()
    keys_down.add(k)
    if k == 'p':
        paused = not paused
    elif k == 'h':
        show_help = not show_help
    elif k == 'm':
        switch_mode()
    elif k == 'r':
        reset_sim()
    elif k == 't':
        show_trail = not show_trail
        trail.opacity = 0.60 if show_trail else 0.0
    elif k in ['+', '=']:
        scene.range = max(5, scene.range * 0.90)
    elif k in ['-', '_']:
        scene.range = min(38, scene.range * 1.10)


def keyup(evt):
    keys_down.discard(evt.key.lower())

scene.bind('keydown', keydown)
scene.bind('keyup', keyup)


def update_controls():
    global manual_push
    push = vector(0, 0, 0)
    if 'w' in keys_down:
        push.z -= 1
    if 's' in keys_down:
        push.z += 1
    if 'a' in keys_down:
        push.x -= 1
    if 'd' in keys_down:
        push.x += 1
    manual_push = norm2d(push, vector(0, 0, 0)) if mag2d(push) > 0 else vector(0, 0, 0)

    pan = 0.18 * scene.range / 18
    if 'left' in keys_down:
        scene.center.x -= pan
    if 'right' in keys_down:
        scene.center.x += pan
    if 'up' in keys_down:
        scene.center.z -= pan
    if 'down' in keys_down:
        scene.center.z += pan
    if 'j' in keys_down:
        scene.forward = rotate(scene.forward, angle=0.025, axis=vector(0, 1, 0))
    if 'l' in keys_down:
        scene.forward = rotate(scene.forward, angle=-0.025, axis=vector(0, 1, 0))
    right = cross(scene.forward, vector(0, 1, 0))
    if mag(right) > 0.01:
        right = norm(right)
        if 'i' in keys_down:
            scene.forward = rotate(scene.forward, angle=0.018, axis=right)
        if 'k' in keys_down:
            scene.forward = rotate(scene.forward, angle=-0.018, axis=right)

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
dt = 1 / 45
reset_sim()

while True:
    rate(45)
    update_controls()
    if paused:
        update_status(t)
        continue

    t += dt
    mode_timer += dt
    trail_timer += dt
    visited_cells.add((round(snail_pos.x / 2.0), round(snail_pos.z / 2.0)))

    force = choose_force(dt, t)
    snail_vel = snail_vel * 0.955 + force
    sp = mag2d(snail_vel)
    max_speed = 0.135
    if sp > max_speed:
        snail_vel = norm2d(snail_vel, heading) * max_speed
    if sp < 0.006:
        snail_vel += rand_dir() * 0.006

    snail_pos += snail_vel

    # Keep on horizontal plane and inside world.
    snail_pos.y = 0
    r = mag2d(snail_pos)
    if r > WORLD_RADIUS - 0.35:
        snail_pos = norm2d(snail_pos) * (WORLD_RADIUS - 0.35)
        snail_vel += norm2d(-snail_pos, -heading) * 0.065

    # Reaching the current target advances the math but never finishes the destination.
    d_target = mag2d(current_target - snail_pos)
    epsilon = max(0.30, 0.78 - 0.018 * iteration)
    if d_target < epsilon:
        advance_target()

    # If the target has become too close to the limit or the snail is orbiting the same area, open a new frontier.
    if mag2d(ideal_goal - current_target) < MIN_LIMIT_GAP or orbit_detected():
        if mag2d(ideal_goal - current_target) < MIN_LIMIT_GAP:
            relocate_limit("target reached limit gap")
        else:
            scout_goal = choose_scout_goal(away_from=current_target)
            scout_timer = 6.0
            orbit_escape_timer = 4.0

    # Automatic mode changes keep behavior alive.
    if mode_timer > 15 + random.random() * 4:
        switch_mode()

    handle_symbols(t)
    update_target_visuals()
    update_snail_visuals(t)

    # Add lightweight trail points only after movement.
    if show_trail and trail_timer > 0.18:
        trail.append(snail_pos + vector(0, 0.035, 0))
        trail_timer = 0.0
        if trail.npoints > 520:
            # Rebuild a shorter trail without relying on unavailable curve.points.
            old_visible = trail.visible
            trail.visible = False
            trail = curve(pos=[snail_pos + vector(0, 0.035, 0)], radius=0.04, color=vector(0.48, 0.78, 0.88))
            trail.opacity = 0.60 if show_trail else 0.0
            trail.visible = old_visible

    recent_positions.append(vector(snail_pos.x, 0, snail_pos.z))
    if len(recent_positions) > 100:
        recent_positions.pop(0)

    update_status(t)
