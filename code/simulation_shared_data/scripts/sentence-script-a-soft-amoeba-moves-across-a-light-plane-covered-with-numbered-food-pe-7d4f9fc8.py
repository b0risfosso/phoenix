"""
Number-Eating Amoeba v4 - Seek Exploration Explorer
A self-contained VPython simulation.

Concept:
- A soft amoeba moves across a light plane covered with numbered food pellets.
- When it eats a number, the number is added, subtracted, multiplied, or divided into its internal value.
- The amoeba changes size, color, pulse speed, and behavior based on its math state.
- The goal is to reach the target value without overshooting too wildly.

Controls:
- W / A / S / D : push amoeba forward / left / back / right
- Space         : pulse jump upward briefly
- R             : reset round
- H             : show/hide help panel
- P             : pause/resume
- M             : switch mode: wander, seek_target, avoid_overshoot
- C             : clear eaten markers

Requirements:
- pip install vpython
- Run with: python number_eating_amoeba_v4_seek_exploration.py
"""

from vpython import *
import random
import math

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Number-Eating Amoeba v4 - Seek Exploration Explorer",
    width=1200,
    height=760,
    background=vector(0.93, 0.96, 1.0),
    center=vector(0, 1.2, 0),
)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.range = 18

# -----------------------------
# Constants
# -----------------------------
WORLD_SIZE = 28
HALF_WORLD = WORLD_SIZE / 2
# Seek mode now alternates between math pursuit and exploratory scouting.
# This keeps the organism from acting like a direct target-seeking missile.
SEEK_EXPLORE_INTERVAL = 3.2
SEEK_EXPLORE_DURATION = 1.65
SEEK_SCOUT_RADIUS = HALF_WORLD * 0.72
FOOD_COUNT = 54
TARGET_VALUE = 42
START_VALUE = 1.0
AMOEBA_BASE_RADIUS = 0.78
MAX_SPEED = 0.13
FRICTION = 0.94
EDGE_SOFT_ZONE = 4.2
EDGE_REPULSE_STRENGTH = 0.045
EDGE_ESCAPE_BOOST = 0.055
LOOP_WINDOW = 90
LOOP_MIN_SPREAD = 1.15
LOOP_PROGRESS_EPS = 0.18
ESCAPE_DURATION = 2.4
WAYPOINT_RADIUS = HALF_WORLD * 0.58
EAT_DISTANCE = 0.9
FOOD_RESPAWN_TIME = 1.8

MODE_NAMES = ["wander", "seek_target", "avoid_overshoot"]
mode_index = 0
paused = False
show_help = True

# -----------------------------
# Math helpers
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def random_food_value():
    # More small numbers than large numbers, with occasional negative/prime values.
    pool = [-9, -7, -5, -3, -2, -1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 7, 8, 9, 10, 11, 13]
    return random.choice(pool)


def random_operator():
    # Addition is most common, multiplication/division less common because they change state strongly.
    return random.choices(["+", "-", "×", "÷"], weights=[0.50, 0.25, 0.17, 0.08])[0]


def apply_math(current, operator, value):
    if operator == "+":
        return current + value
    if operator == "-":
        return current - value
    if operator == "×":
        return current * value
    if operator == "÷":
        if value == 0:
            return current
        return current / value
    return current


def value_color(value):
    # Positive values are warm, negative values cool, target-near values green.
    distance = abs(TARGET_VALUE - value)
    if distance < 2.0:
        return vector(0.20, 0.95, 0.35)
    if value < 0:
        return vector(0.25, 0.45, 1.0)
    if value > TARGET_VALUE * 1.5:
        return vector(1.0, 0.28, 0.18)
    return vector(0.95, 0.62, 0.22)


def food_color(operator, value):
    if operator == "+":
        return vector(0.36, 0.78, 0.38)
    if operator == "-":
        return vector(0.90, 0.42, 0.35)
    if operator == "×":
        return vector(0.58, 0.42, 0.92)
    if operator == "÷":
        return vector(0.30, 0.68, 0.95)
    return vector(0.9, 0.9, 0.9)


def target_score(value):
    # Higher is better. Used by seek behavior.
    return -abs(TARGET_VALUE - value)

# -----------------------------
# World objects
# -----------------------------
floor = box(
    pos=vector(0, -0.05, 0),
    size=vector(WORLD_SIZE, 0.08, WORLD_SIZE),
    color=vector(0.88, 0.91, 0.87),
)

# Grid lines
for i in range(-int(HALF_WORLD), int(HALF_WORLD) + 1, 2):
    curve(pos=[vector(i, 0.01, -HALF_WORLD), vector(i, 0.01, HALF_WORLD)], color=vector(0.75, 0.79, 0.75), radius=0.01)
    curve(pos=[vector(-HALF_WORLD, 0.01, i), vector(HALF_WORLD, 0.01, i)], color=vector(0.75, 0.79, 0.75), radius=0.01)

# Target ring
ring(
    pos=vector(0, 0.05, 0),
    axis=vector(0, 1, 0),
    radius=2.25,
    thickness=0.045,
    color=vector(0.2, 0.82, 0.28),
)
label(
    pos=vector(0, 0.25, 0),
    text=f"target {TARGET_VALUE}",
    height=13,
    box=False,
    opacity=0,
    color=vector(0.16, 0.45, 0.2),
)

# Amoeba body: several translucent blobs around a central sphere.
amoeba_core = sphere(
    pos=vector(-8, AMOEBA_BASE_RADIUS, -6),
    radius=AMOEBA_BASE_RADIUS,
    color=vector(0.95, 0.62, 0.22),
    opacity=0.72,
    shininess=0.2,
)
amoeba_nucleus = sphere(
    pos=amoeba_core.pos + vector(0.15, 0.08, 0.05),
    radius=0.25,
    color=vector(0.28, 0.16, 0.42),
    opacity=0.8,
)

pseudopods = []
for k in range(9):
    angle = 2 * math.pi * k / 9
    pseudopods.append(
        sphere(
            pos=amoeba_core.pos + vector(math.cos(angle) * 0.58, 0, math.sin(angle) * 0.58),
            radius=0.32,
            color=amoeba_core.color,
            opacity=0.46,
            shininess=0.1,
        )
    )

sense_ring = ring(
    pos=amoeba_core.pos + vector(0, 0.02, 0),
    axis=vector(0, 1, 0),
    radius=2.2,
    thickness=0.018,
    color=vector(0.22, 0.55, 0.95),
    opacity=0.28,
)

value_label = label(
    pos=amoeba_core.pos + vector(0, 1.45, 0),
    text="value: 1",
    height=16,
    box=True,
    border=8,
    opacity=0.75,
    color=vector(0.1, 0.12, 0.14),
    background=vector(1, 1, 1),
)

status_label = label(
    pos=vector(-13.4, 4.8, -13.2),
    text="",
    height=13,
    box=True,
    border=8,
    opacity=0.78,
    color=vector(0.05, 0.07, 0.09),
    background=vector(1, 1, 1),
)

help_label = label(
    pos=vector(8.8, 4.8, -13.2),
    text="",
    height=11,
    box=True,
    border=8,
    opacity=0.70,
    color=vector(0.05, 0.07, 0.09),
    background=vector(1, 1, 1),
)

# -----------------------------
# Simulation state
# -----------------------------
keys_down = set()
foods = []
eaten_markers = []
value_history = []
round_number = 1
amoeba_value = START_VALUE
amoeba_velocity = vector(0.04, 0, 0.025)
last_jump_time = -10
wander_angle = random.random() * math.tau
edge_escape_timer = 0.0

# Anti-loop movement state. These values prevent seek_target and
# avoid_overshoot from turning into repeated orbits around one pellet or
# into a stable push-pull equilibrium between pellet seeking and avoidance.
recent_positions = []
recent_target_keys = []
last_target_key = None
same_target_timer = 0.0
escape_timer = 0.0
escape_waypoint = None
escape_turn_sign = 1

# Extra seek-target exploration state. In seek mode, the amoeba periodically
# scouts an open-space waypoint before returning to math-target pursuit.
seek_explore_timer = 0.0
seek_explore_cooldown = SEEK_EXPLORE_INTERVAL
seek_explore_waypoint = None
seek_arc_sign = 1

# -----------------------------
# Food creation
# -----------------------------
def create_food(pos=None):
    value = random_food_value()
    operator = random_operator()
    if pos is None:
        pos = vector(
            random.uniform(-HALF_WORLD + 1, HALF_WORLD - 1),
            0.22,
            random.uniform(-HALF_WORLD + 1, HALF_WORLD - 1),
        )
    pellet = sphere(
        pos=pos,
        radius=0.25 + 0.025 * min(abs(value), 10),
        color=food_color(operator, value),
        shininess=0.25,
    )
    txt = label(
        pos=pos + vector(0, 0.45, 0),
        text=f"{operator}{value}",
        height=10,
        box=False,
        opacity=0,
        color=vector(0.05, 0.07, 0.09),
    )
    halo = ring(
        pos=pos + vector(0, -0.17, 0),
        axis=vector(0, 1, 0),
        radius=0.38,
        thickness=0.015,
        color=pellet.color,
        opacity=0.22,
    )
    return {"value": value, "operator": operator, "pellet": pellet, "label": txt, "halo": halo, "respawn": 0}


def populate_foods():
    for _ in range(FOOD_COUNT):
        foods.append(create_food())

populate_foods()

# -----------------------------
# Visual/state update functions
# -----------------------------
def update_amoeba_visual(t):
    global amoeba_core
    distance = abs(TARGET_VALUE - amoeba_value)
    closeness = clamp(1.0 - distance / max(1, TARGET_VALUE), 0, 1)
    base_radius = AMOEBA_BASE_RADIUS + 0.010 * clamp(abs(amoeba_value), 0, 80)
    pulse = 0.08 * math.sin(t * (2.4 + 4.0 * closeness))
    amoeba_core.radius = clamp(base_radius + pulse, 0.55, 1.75)
    amoeba_core.color = value_color(amoeba_value)
    amoeba_core.opacity = 0.62 + 0.20 * closeness

    amoeba_nucleus.pos = amoeba_core.pos + vector(0.15 * math.cos(t * 1.7), 0.08, 0.12 * math.sin(t * 1.3))
    amoeba_nucleus.radius = 0.22 + 0.05 * closeness

    # Pseudopods wave around the core, stretching more in direction of movement.
    speed = mag(amoeba_velocity)
    direction = norm(amoeba_velocity) if speed > 0.001 else vector(math.cos(wander_angle), 0, math.sin(wander_angle))
    for k, pod in enumerate(pseudopods):
        angle = 2 * math.pi * k / len(pseudopods) + 0.35 * math.sin(t * 1.2 + k)
        radial = vector(math.cos(angle), 0, math.sin(angle))
        forward_bias = dot(radial, direction)
        stretch = 0.55 + 0.22 * math.sin(t * 2.5 + k * 0.9) + 0.42 * max(0, forward_bias)
        pod.pos = amoeba_core.pos + radial * stretch
        pod.pos.y = AMOEBA_BASE_RADIUS + 0.03 * math.sin(t * 4 + k)
        pod.radius = clamp(0.27 + 0.06 * math.sin(t * 3.1 + k) + 0.10 * max(0, forward_bias), 0.18, 0.48)
        pod.color = amoeba_core.color
        pod.opacity = 0.35 + 0.18 * closeness

    sense_ring.pos = vector(amoeba_core.pos.x, 0.05, amoeba_core.pos.z)
    sense_ring.radius = 1.8 + 0.015 * clamp(abs(TARGET_VALUE - amoeba_value), 0, 80)
    sense_ring.opacity = 0.16 + 0.18 * closeness

    value_label.pos = amoeba_core.pos + vector(0, amoeba_core.radius + 0.65, 0)
    value_label.text = f"value: {amoeba_value:.2f}\nΔ target: {TARGET_VALUE - amoeba_value:.2f}"


def update_labels(t):
    mode = MODE_NAMES[mode_index]
    status_label.text = (
        f"Number-Eating Amoeba\n"
        f"round: {round_number}\n"
        f"target: {TARGET_VALUE}\n"
        f"current: {amoeba_value:.2f}\n"
        f"mode: {mode}\n"
        f"escape: {escape_timer:.1f}s\n"
        f"seek scout: {seek_explore_timer:.1f}s\n"
        f"eaten: {len(value_history)}\n"
        f"paused: {paused}"
    )
    if show_help:
        help_label.visible = True
        help_label.text = (
            "Controls\n"
            "WASD: push amoeba\n"
            "Space: pulse jump\n"
            "M: change math behavior\n"
            "R: reset round\n"
            "P: pause/resume\n"
            "C: clear eaten markers\n"
            "H: hide/show this panel\n\n"
            "Food colors\n"
            "+ green, - red\n"
            "× purple, ÷ blue"
        )
    else:
        help_label.visible = False


def add_eaten_marker(pos, operator, value, old_value, new_value):
    marker = sphere(
        pos=vector(pos.x, 0.08, pos.z),
        radius=0.12,
        color=value_color(new_value),
        opacity=0.45,
    )
    txt = label(
        pos=vector(pos.x, 0.45, pos.z),
        text=f"{old_value:.1f} {operator} {value} = {new_value:.1f}",
        height=8,
        box=False,
        opacity=0,
        color=vector(0.1, 0.1, 0.1),
    )
    eaten_markers.append((marker, txt))


def clear_markers():
    for marker, txt in eaten_markers:
        marker.visible = False
        txt.visible = False
    eaten_markers.clear()


def reset_round():
    global amoeba_value, amoeba_velocity, round_number, wander_angle, edge_escape_timer
    global recent_positions, recent_target_keys, last_target_key, same_target_timer
    global escape_timer, escape_waypoint, escape_turn_sign
    global seek_explore_timer, seek_explore_cooldown, seek_explore_waypoint, seek_arc_sign
    round_number += 1
    amoeba_value = START_VALUE
    amoeba_velocity = vector(random.uniform(-0.04, 0.04), 0, random.uniform(-0.04, 0.04))
    amoeba_core.pos = vector(random.uniform(-8, 8), AMOEBA_BASE_RADIUS, random.uniform(-8, 8))
    value_history.clear()
    wander_angle = random.random() * math.tau
    edge_escape_timer = 0.0
    recent_positions.clear()
    recent_target_keys.clear()
    last_target_key = None
    same_target_timer = 0.0
    escape_timer = 0.0
    escape_waypoint = None
    escape_turn_sign = random.choice([-1, 1])
    seek_explore_timer = 0.0
    seek_explore_cooldown = random.uniform(1.2, SEEK_EXPLORE_INTERVAL)
    seek_explore_waypoint = None
    seek_arc_sign = random.choice([-1, 1])
    clear_markers()
    for item in foods:
        item["pellet"].visible = False
        item["label"].visible = False
        item["halo"].visible = False
    foods.clear()
    populate_foods()

# -----------------------------
# Behavior functions
# -----------------------------
def nearest_food():
    best = None
    best_dist = 1e9
    for item in foods:
        if not item["pellet"].visible:
            continue
        d = mag(item["pellet"].pos - amoeba_core.pos)
        if d < best_dist:
            best = item
            best_dist = d
    return best, best_dist


def best_math_food():
    best = None
    best_score = -1e9
    for item in foods:
        if not item["pellet"].visible:
            continue
        candidate = apply_math(amoeba_value, item["operator"], item["value"])
        score = target_score(candidate)
        distance = mag(item["pellet"].pos - amoeba_core.pos)
        score -= 0.08 * distance
        # Prefer safe steps unless already far from target.
        if abs(candidate) > 160:
            score -= 25
        if score > best_score:
            best_score = score
            best = item
    return best



def edge_escape_force():
    """Return an inward steering force before the amoeba reaches the wall.

    The original version only bounced after hitting the hard boundary. If the
    active mode kept selecting food near the wall, the amoeba could repeatedly
    press into the edge and appear stuck. This soft field starts redirecting it
    several units before the boundary, making it prefer open central space.
    """
    global wander_angle, edge_escape_timer
    margin = HALF_WORLD - 0.8
    inner = margin - EDGE_SOFT_ZONE
    inward = vector(0, 0, 0)

    if amoeba_core.pos.x < -inner:
        depth = (-inner - amoeba_core.pos.x) / EDGE_SOFT_ZONE
        inward.x += clamp(depth, 0, 1)
    elif amoeba_core.pos.x > inner:
        depth = (amoeba_core.pos.x - inner) / EDGE_SOFT_ZONE
        inward.x -= clamp(depth, 0, 1)

    if amoeba_core.pos.z < -inner:
        depth = (-inner - amoeba_core.pos.z) / EDGE_SOFT_ZONE
        inward.z += clamp(depth, 0, 1)
    elif amoeba_core.pos.z > inner:
        depth = (amoeba_core.pos.z - inner) / EDGE_SOFT_ZONE
        inward.z -= clamp(depth, 0, 1)

    if mag(inward) > 0:
        # Re-aim wandering toward the open interior so future autonomous motion
        # cooperates with the escape instead of fighting it.
        n = norm(inward)
        wander_angle = math.atan2(n.z, n.x) + random.uniform(-0.45, 0.45)
        edge_escape_timer = max(edge_escape_timer, 0.75)
        return n * EDGE_REPULSE_STRENGTH
    return vector(0, 0, 0)


def open_space_bias_force():
    """Small preference for drifting through underused central space."""
    center_pull = -vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    if mag(center_pull) == 0:
        return vector(0, 0, 0)
    distance_from_center = mag(center_pull)
    # Almost no pull near the middle, stronger near the outer third.
    strength = 0.002 + 0.010 * clamp((distance_from_center - HALF_WORLD * 0.35) / (HALF_WORLD * 0.45), 0, 1)
    return norm(center_pull) * strength

def food_key(item):
    """Stable enough key for detecting repeated pursuit of the same pellet."""
    if item is None:
        return None
    p = item["pellet"].pos
    return (round(p.x, 1), round(p.z, 1), item["operator"], item["value"])



def choose_seek_explore_waypoint(target_item=None):
    """Choose an open-space scouting point for seek_target mode.

    The point is usually not the best pellet itself. It is offset sideways or
    into underused interior space so the amoeba searches around the target
    region instead of repeating one direct path.
    """
    current = vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    if target_item is not None and target_item["pellet"].visible:
        target = vector(target_item["pellet"].pos.x, 0, target_item["pellet"].pos.z)
        to_target = target - current
        if mag(to_target) > 0.1:
            n = norm(to_target)
            side = vector(-n.z, 0, n.x) * random.choice([-1, 1])
            offset_distance = random.uniform(2.8, 5.8)
            ahead_distance = random.uniform(1.0, 3.5)
            candidate = target + side * offset_distance - n * ahead_distance
            candidate.x = clamp(candidate.x, -HALF_WORLD + 2.2, HALF_WORLD - 2.2)
            candidate.z = clamp(candidate.z, -HALF_WORLD + 2.2, HALF_WORLD - 2.2)
            if mag(candidate - current) > 2.0:
                return candidate

    # Fallback: pick a broad interior scouting point, biased away from the
    # current location.
    for _ in range(20):
        angle = random.random() * math.tau
        radius = random.uniform(SEEK_SCOUT_RADIUS * 0.25, SEEK_SCOUT_RADIUS)
        candidate = vector(math.cos(angle) * radius, 0, math.sin(angle) * radius)
        if mag(candidate - current) > 4.0:
            return candidate
    return -current if mag(current) > 1 else vector(random.uniform(-7, 7), 0, random.uniform(-7, 7))


def seek_exploration_force(target_item, t):
    """Interleave scouting arcs into seek_target mode."""
    global seek_explore_timer, seek_explore_cooldown, seek_explore_waypoint, seek_arc_sign

    seek_explore_cooldown = max(0, seek_explore_cooldown - dt)

    # Start a scouting beat periodically, and also when the same target has
    # held attention for a while. This increases visible exploration without
    # fully abandoning the target objective.
    if seek_explore_timer <= 0 and (seek_explore_cooldown <= 0 or same_target_timer > 1.45):
        seek_explore_timer = SEEK_EXPLORE_DURATION + random.uniform(-0.25, 0.45)
        seek_explore_cooldown = SEEK_EXPLORE_INTERVAL + random.uniform(-0.6, 1.0)
        seek_explore_waypoint = choose_seek_explore_waypoint(target_item)
        seek_arc_sign = random.choice([-1, 1])

    if seek_explore_timer <= 0 or seek_explore_waypoint is None:
        return vector(0, 0, 0)

    seek_explore_timer = max(0, seek_explore_timer - dt)
    current = vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    to_waypoint = seek_explore_waypoint - current
    if mag(to_waypoint) < 0.9:
        seek_explore_waypoint = choose_seek_explore_waypoint(target_item)
        to_waypoint = seek_explore_waypoint - current
    if mag(to_waypoint) == 0:
        return vector(0, 0, 0)

    n = norm(to_waypoint)
    tangent = vector(-n.z, 0, n.x) * seek_arc_sign
    pulse = 0.5 + 0.5 * math.sin(t * 4.8)
    return n * 0.022 + tangent * (0.010 + 0.007 * pulse)

def choose_escape_waypoint():
    """Pick a fresh interior point that is not close to the current loop."""
    current = vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    for _ in range(18):
        angle = random.random() * math.tau
        radius = random.uniform(WAYPOINT_RADIUS * 0.35, WAYPOINT_RADIUS)
        candidate = vector(math.cos(angle) * radius, 0, math.sin(angle) * radius)
        if mag(candidate - current) > 4.0:
            return candidate
    return -current if mag(current) > 1 else vector(random.uniform(-6, 6), 0, random.uniform(-6, 6))


def begin_escape(reason="loop"):
    """Temporarily abandon the selected math pellet and move through open space."""
    global escape_timer, escape_waypoint, escape_turn_sign, wander_angle, same_target_timer
    escape_timer = ESCAPE_DURATION
    escape_waypoint = choose_escape_waypoint()
    escape_turn_sign = random.choice([-1, 1])
    same_target_timer = 0.0
    direction = escape_waypoint - vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    if mag(direction) > 0:
        n = norm(direction)
        wander_angle = math.atan2(n.z, n.x)


def loop_escape_force(t):
    """Curved force toward a temporary waypoint, used when a mode becomes repetitive."""
    global escape_timer, escape_waypoint
    if escape_timer <= 0 or escape_waypoint is None:
        return vector(0, 0, 0)
    escape_timer = max(0, escape_timer - dt)
    to_waypoint = escape_waypoint - vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    if mag(to_waypoint) < 1.1:
        escape_waypoint = choose_escape_waypoint()
        to_waypoint = escape_waypoint - vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    if mag(to_waypoint) == 0:
        return vector(0, 0, 0)
    n = norm(to_waypoint)
    # Add sideways steering so the amoeba breaks circular or back-and-forth loops.
    tangent = vector(-n.z, 0, n.x) * escape_turn_sign
    pulse = 0.5 + 0.5 * math.sin(t * 5.5)
    return n * 0.034 + tangent * (0.012 + 0.010 * pulse) + open_space_bias_force() + edge_escape_force()


def update_loop_detector(target_item, t):
    """Detect low-progress repetition in target-seeking modes."""
    global last_target_key, same_target_timer
    mode = MODE_NAMES[mode_index]
    if mode not in ("seek_target", "avoid_overshoot"):
        return

    current_pos = vector(amoeba_core.pos.x, 0, amoeba_core.pos.z)
    recent_positions.append(current_pos)
    if len(recent_positions) > LOOP_WINDOW:
        recent_positions.pop(0)

    key = food_key(target_item)
    recent_target_keys.append(key)
    if len(recent_target_keys) > LOOP_WINDOW:
        recent_target_keys.pop(0)

    if key == last_target_key and key is not None:
        same_target_timer += dt
    else:
        same_target_timer = 0.0
        last_target_key = key

    if len(recent_positions) < LOOP_WINDOW:
        return

    xs = [p.x for p in recent_positions]
    zs = [p.z for p in recent_positions]
    spread = max(max(xs) - min(xs), max(zs) - min(zs))
    net_progress = mag(recent_positions[-1] - recent_positions[0])
    repeated_target_ratio = recent_target_keys.count(key) / max(1, len(recent_target_keys)) if key else 0

    trapped_small_loop = spread < LOOP_MIN_SPREAD and net_progress < LOOP_PROGRESS_EPS
    overcommitted_to_target = same_target_timer > 3.6 and repeated_target_ratio > 0.70 and net_progress < 2.0
    nearly_stopped = mag(amoeba_velocity) < 0.012 and same_target_timer > 1.8

    if trapped_small_loop or overcommitted_to_target or nearly_stopped:
        begin_escape("repetition")
        recent_positions.clear()
        recent_target_keys.clear()

def autonomous_force(t):
    global wander_angle, edge_escape_timer
    mode = MODE_NAMES[mode_index]

    if edge_escape_timer > 0:
        edge_escape_timer = max(0, edge_escape_timer - dt)

    # Highest priority: break repeated movement loops by temporarily leaving the
    # current math target and moving through a curved interior waypoint path.
    if escape_timer > 0:
        return loop_escape_force(t)

    if mode == "wander":
        wander_angle += random.uniform(-0.07, 0.07)
        force = vector(math.cos(wander_angle), 0, math.sin(wander_angle)) * 0.016
        near, dist = nearest_food()
        if near and dist < 4.5 and edge_escape_timer <= 0:
            # Follow nearby food only when not actively escaping an edge.
            force += norm(near["pellet"].pos - amoeba_core.pos) * 0.010
        return force + open_space_bias_force() + edge_escape_force()

    if mode == "seek_target":
        target_food = best_math_food()
        update_loop_detector(target_food, t)
        if escape_timer > 0:
            return loop_escape_force(t)

        # Extra exploration layer: seek mode now moves through scouting arcs
        # around promising math regions instead of always moving directly toward
        # the single best pellet.
        scout_force = seek_exploration_force(target_food, t)
        force = scout_force

        if target_food and edge_escape_timer <= 0:
            desired = target_food["pellet"].pos - amoeba_core.pos
            if mag(desired) > 0:
                n = norm(desired)
                tangent = vector(-n.z, 0, n.x) * (0.007 * math.sin(t * 3.7))
                # During scouting, the target pull is weaker so exploration
                # visibly wins for a moment. Outside scouting, pursuit resumes.
                target_strength = 0.012 if seek_explore_timer > 0 else 0.021
                force += n * target_strength + tangent

        # Add mild wandering noise in seek mode. This makes it sample free space
        # and nearby pellets rather than locking to a single line.
        explore_noise = vector(math.cos(wander_angle + math.sin(t * 1.4)), 0, math.sin(wander_angle + math.cos(t * 1.1))) * 0.004
        return force + explore_noise + open_space_bias_force() + edge_escape_force()

    if mode == "avoid_overshoot":
        target_food = best_math_food()
        update_loop_detector(target_food, t)
        if escape_timer > 0:
            return loop_escape_force(t)
        near, dist = nearest_food()
        force = vector(0, 0, 0)
        if target_food:
            desired = target_food["pellet"].pos - amoeba_core.pos
            if mag(desired) > 0:
                force += norm(desired) * 0.020
        if near:
            candidate = apply_math(amoeba_value, near["operator"], near["value"])
            if abs(candidate - TARGET_VALUE) > abs(amoeba_value - TARGET_VALUE) + 12 and dist < 3.5:
                away = amoeba_core.pos - near["pellet"].pos
                if mag(away) > 0:
                    # Repulsion is capped below the target-seeking + escape forces so
                    # it cannot create a permanent push-pull loop.
                    force += norm(away) * 0.020
                    side = vector(-norm(away).z, 0, norm(away).x)
                    force += side * (0.006 * math.sin(t * 4.1))
        return force + open_space_bias_force() + edge_escape_force()

    return open_space_bias_force() + edge_escape_force()


def keyboard_force():
    force = vector(0, 0, 0)
    step = 0.035
    if "w" in keys_down:
        force += vector(0, 0, -step)
    if "s" in keys_down:
        force += vector(0, 0, step)
    if "a" in keys_down:
        force += vector(-step, 0, 0)
    if "d" in keys_down:
        force += vector(step, 0, 0)
    return force


def eat_food_if_close(t):
    global amoeba_value
    for item in foods:
        pellet = item["pellet"]
        if not pellet.visible:
            continue
        d = mag(pellet.pos - amoeba_core.pos)
        if d < EAT_DISTANCE + amoeba_core.radius * 0.35:
            old_value = amoeba_value
            amoeba_value = apply_math(amoeba_value, item["operator"], item["value"])
            amoeba_value = clamp(amoeba_value, -250, 250)
            value_history.append((item["operator"], item["value"], amoeba_value))
            add_eaten_marker(pellet.pos, item["operator"], item["value"], old_value, amoeba_value)
            pellet.visible = False
            item["label"].visible = False
            item["halo"].visible = False
            item["respawn"] = t + FOOD_RESPAWN_TIME + random.random() * 1.5


def respawn_foods(t):
    for item in foods:
        if item["pellet"].visible:
            continue
        if t >= item["respawn"]:
            value = random_food_value()
            operator = random_operator()
            pos = vector(
                random.uniform(-HALF_WORLD + 1, HALF_WORLD - 1),
                0.22,
                random.uniform(-HALF_WORLD + 1, HALF_WORLD - 1),
            )
            item["value"] = value
            item["operator"] = operator
            item["pellet"].pos = pos
            item["pellet"].radius = 0.25 + 0.025 * min(abs(value), 10)
            item["pellet"].color = food_color(operator, value)
            item["pellet"].visible = True
            item["label"].pos = pos + vector(0, 0.45, 0)
            item["label"].text = f"{operator}{value}"
            item["label"].visible = True
            item["halo"].pos = pos + vector(0, -0.17, 0)
            item["halo"].color = item["pellet"].color
            item["halo"].visible = True


def keep_inside_world():
    global amoeba_velocity, wander_angle, edge_escape_timer
    margin = HALF_WORLD - 0.8
    hit_edge = False
    inward = vector(0, 0, 0)

    if amoeba_core.pos.x < -margin:
        amoeba_core.pos.x = -margin
        amoeba_velocity.x = abs(amoeba_velocity.x) * 0.35 + EDGE_ESCAPE_BOOST
        inward.x += 1
        hit_edge = True
    if amoeba_core.pos.x > margin:
        amoeba_core.pos.x = margin
        amoeba_velocity.x = -abs(amoeba_velocity.x) * 0.35 - EDGE_ESCAPE_BOOST
        inward.x -= 1
        hit_edge = True
    if amoeba_core.pos.z < -margin:
        amoeba_core.pos.z = -margin
        amoeba_velocity.z = abs(amoeba_velocity.z) * 0.35 + EDGE_ESCAPE_BOOST
        inward.z += 1
        hit_edge = True
    if amoeba_core.pos.z > margin:
        amoeba_core.pos.z = margin
        amoeba_velocity.z = -abs(amoeba_velocity.z) * 0.35 - EDGE_ESCAPE_BOOST
        inward.z -= 1
        hit_edge = True

    if hit_edge and mag(inward) > 0:
        n = norm(inward)
        amoeba_velocity += n * EDGE_ESCAPE_BOOST
        wander_angle = math.atan2(n.z, n.x) + random.uniform(-0.35, 0.35)
        edge_escape_timer = 1.15

# -----------------------------
# Keyboard events
# -----------------------------
def keydown(evt):
    global paused, show_help, mode_index, last_jump_time, amoeba_velocity
    key = evt.key.lower()
    keys_down.add(key)
    if key == "p":
        paused = not paused
    elif key == "h":
        show_help = not show_help
    elif key == "m":
        mode_index = (mode_index + 1) % len(MODE_NAMES)
    elif key == "r":
        reset_round()
    elif key == "c":
        clear_markers()
    elif key == " ":
        # Visual pulse jump: not a full physics jump, but gives a living response.
        amoeba_velocity += vector(random.uniform(-0.025, 0.025), 0, random.uniform(-0.025, 0.025))
        last_jump_time = clock()


def keyup(evt):
    key = evt.key.lower()
    if key in keys_down:
        keys_down.remove(key)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
dt = 0.025
while True:
    rate(40)
    if paused:
        update_labels(t)
        continue

    t += dt

    # Movement: autonomous force plus optional keyboard pushes.
    amoeba_velocity += autonomous_force(t)
    amoeba_velocity += keyboard_force()
    amoeba_velocity *= FRICTION
    if mag(amoeba_velocity) > MAX_SPEED:
        amoeba_velocity = norm(amoeba_velocity) * MAX_SPEED

    amoeba_core.pos += amoeba_velocity
    amoeba_core.pos.y = AMOEBA_BASE_RADIUS + 0.03 * math.sin(t * 2.5)
    keep_inside_world()

    eat_food_if_close(t)
    respawn_foods(t)
    update_amoeba_visual(t)
    update_labels(t)

    # If the target is reached closely, make the organism celebrate, then begin a new round.
    if abs(amoeba_value - TARGET_VALUE) < 0.75 and len(value_history) > 0:
        for _ in range(16):
            theta = random.random() * math.tau
            r = random.uniform(0.3, 1.8)
            pos = amoeba_core.pos + vector(math.cos(theta) * r, random.uniform(0.2, 1.4), math.sin(theta) * r)
            spark = sphere(pos=pos, radius=0.07, color=vector(0.25, 1.0, 0.35), opacity=0.55)
            eaten_markers.append((spark, label(pos=pos + vector(0, 0.2, 0), text="✓", height=8, box=False, opacity=0)))
        reset_round()
