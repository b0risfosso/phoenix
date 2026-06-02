"""
fractal_coral_v3_persistent_lightweight.py

A VPython simulation of a horizontal Fractal Coral whose branches all persist.

Concept:
- The coral starts from several tips near the center of a flat plane.
- Every living tip continues growing horizontally, then splits into child tips.
- Branches are not pruned or faded away. The coral keeps its full history.
- Rendering load is reduced by drawing each branch as a lightweight curve path,
  appending points only every few frames instead of creating a cylinder for every
  tiny growth step.

Controls:
  H       show/hide help
  P       pause/resume
  R       reset coral
  M       cycle autonomous mode
  C       clear temporary spark particles
  W/A/S/D move nutrient light on the ground plane
  Space   raise nutrient light
  Z       lower nutrient light
  + / -   zoom camera
  Arrow keys pan camera center
  J/L     rotate camera around coral
  I/K     tilt camera

Run:
  python fractal_coral_v3_persistent_lightweight.py

Requires:
  pip install vpython
"""

from vpython import *
import math
import random
from dataclasses import dataclass, field

# -----------------------------------------------------------------------------
# Scene setup
# -----------------------------------------------------------------------------
scene = canvas(
    title="Fractal Coral - persistent horizontal branch growth",
    width=1200,
    height=800,
    background=vector(0.92, 0.96, 1.0),
    center=vector(0, 0.45, 0),
)
scene.forward = vector(-0.38, -0.78, -0.50)
scene.range = 13

WORLD_RADIUS = 10.0
GROUND_Y = -0.08
BASE_DT = 1.0 / 30.0

# The visual history persists. These limits only throttle new *active* growth so
# the simulation stays responsive during long runs.
MAX_ACTIVE_TIPS = 320
MAX_STORED_TIPS = 2500
MAX_CURVE_OBJECTS = 2600
MAX_POINTS_PER_CURVE = 80
POINT_APPEND_DISTANCE = 0.10
TIP_UPDATES_PER_FRAME = 110
SPARKS_ENABLED = False

PALETTE = [
    vector(0.98, 0.45, 0.36),
    vector(0.95, 0.58, 0.28),
    vector(0.98, 0.72, 0.38),
    vector(0.64, 0.82, 0.52),
    vector(0.42, 0.72, 0.84),
    vector(0.62, 0.56, 0.88),
    vector(0.88, 0.52, 0.72),
]

MODE_NAMES = ["balanced", "nutrient_seek", "fan_growth", "spiral_mutation", "frontier_spread"]
mode_index = 0
paused = False
show_help = True
sim_time = 0.0
update_cursor = 0

branches = []
tips = []
resting_tips = []
particles = []
visited = {}
keys_down = set()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def rotate_y(v, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return vector(c * v.x + s * v.z, v.y, -s * v.x + c * v.z)


def blend(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t


def random_horizontal_dir():
    a = random.uniform(0, 2 * math.pi)
    return vector(math.cos(a), 0, math.sin(a))


def horizontal(v, fallback=None):
    if fallback is None:
        fallback = random_horizontal_dir()
    return safe_norm(vector(v.x, 0, v.z), fallback)


def cell_key(pos, size=0.8):
    return (round(pos.x / size), round(pos.z / size))


def current_mode():
    return MODE_NAMES[mode_index % len(MODE_NAMES)]

# -----------------------------------------------------------------------------
# Lightweight branch/tip structures
# -----------------------------------------------------------------------------
@dataclass
class BranchPath:
    curve_obj: object
    radius: float
    color: vector
    generation: int
    point_count: int = 1
    start: vector = field(default_factory=lambda: vector(0, 0, 0))
    end: vector = field(default_factory=lambda: vector(0, 0, 0))


@dataclass
class Tip:
    pos: vector
    direction: vector
    length_remaining: float
    radius: float
    generation: int
    energy: float
    branch_angle: float
    split_chance: float
    shrink: float
    color_bias: int
    branch: BranchPath
    age: float = 0.0
    last_draw_pos: vector = field(default_factory=lambda: vector(0, 0, 0))
    alive: bool = True
    sleeping: bool = False

# -----------------------------------------------------------------------------
# Static world objects
# -----------------------------------------------------------------------------
ground = cylinder(
    pos=vector(0, GROUND_Y - 0.04, 0),
    axis=vector(0, 0.04, 0),
    radius=WORLD_RADIUS + 1.2,
    color=vector(0.86, 0.90, 0.82),
    opacity=0.50,
)

boundary = ring(
    pos=vector(0, GROUND_Y + 0.015, 0),
    axis=vector(0, 1, 0),
    radius=WORLD_RADIUS,
    thickness=0.035,
    color=vector(0.62, 0.72, 0.68),
    opacity=0.34,
)

grid_lines = []
for i in range(-10, 11):
    if i % 2 == 0:
        grid_lines.append(curve(pos=[vector(i, GROUND_Y + 0.01, -10), vector(i, GROUND_Y + 0.01, 10)],
                                radius=0.006, color=vector(0.72, 0.78, 0.76), opacity=0.18))
        grid_lines.append(curve(pos=[vector(-10, GROUND_Y + 0.01, i), vector(10, GROUND_Y + 0.01, i)],
                                radius=0.006, color=vector(0.72, 0.78, 0.76), opacity=0.18))

root_core = sphere(pos=vector(0, 0.05, 0), radius=0.34, color=vector(0.95, 0.42, 0.34))
root_ring = ring(pos=root_core.pos, axis=vector(0, 1, 0), radius=0.52, thickness=0.025,
                 color=vector(1.0, 0.75, 0.45), opacity=0.6)

nutrient = sphere(pos=vector(3.5, 0.30, -3.0), radius=0.30, color=vector(0.35, 0.62, 1.0), emissive=True)
nutrient_halo = sphere(pos=nutrient.pos, radius=0.85, color=nutrient.color, opacity=0.13, emissive=True)

status = label(pos=vector(-10.2, 3.3, 0), text="", box=False, opacity=0, height=13,
               color=vector(0.18, 0.24, 0.25), align="left")
help_label = label(pos=vector(6.3, 3.2, 0), text="", box=True, height=11,
                   color=vector(0.1, 0.14, 0.16), background=vector(0.96, 0.98, 1.0),
                   border=10, opacity=0.78, align="left")

# -----------------------------------------------------------------------------
# Coral growth logic
# -----------------------------------------------------------------------------
def color_for_generation(color_bias, generation, pos):
    base = PALETTE[color_bias % len(PALETTE)]
    spread = clamp(mag(vector(pos.x, 0, pos.z)) / WORLD_RADIUS, 0, 1)
    gen = clamp(generation / 14.0, 0, 1)
    return blend(base, vector(1.0, 0.94, 0.68), 0.13 * spread + 0.11 * gen)


def make_branch_path(start, radius, generation, col):
    # One curve object can hold many path points. This is much lighter than one
    # cylinder per small segment.
    c = curve(pos=[start], radius=max(0.008, radius), color=col, opacity=0.82)
    b = BranchPath(c, radius, col, generation, point_count=1, start=start, end=start)
    branches.append(b)
    return b


def append_branch_point(branch, pos):
    # Keep old branches persistent, but keep each curve short enough that VPython
    # remains responsive. A new curve continues the same branch path when needed.
    if mag(pos - branch.end) < POINT_APPEND_DISTANCE:
        return branch
    if branch.point_count >= MAX_POINTS_PER_CURVE:
        new_branch = make_branch_path(branch.end, branch.radius, branch.generation, branch.color)
        branch = new_branch
    branch.curve_obj.append(pos=pos)
    branch.point_count += 1
    branch.end = pos
    visited[cell_key(pos)] = visited.get(cell_key(pos), 0) + 1
    return branch


def crowding_at(pos):
    kx, kz = cell_key(pos)
    total = 0
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            total += visited.get((kx + dx, kz + dz), 0)
    return total


def initial_tips():
    out = []
    for k in range(8):
        a = k * 2 * math.pi / 8
        d = vector(math.cos(a), 0, math.sin(a))
        start = vector(0, 0.06, 0)
        col = color_for_generation(k, 0, start)
        b = make_branch_path(start, 0.075, 0, col)
        out.append(Tip(
            pos=start,
            direction=d,
            length_remaining=random.uniform(1.0, 1.55),
            radius=0.075,
            generation=0,
            energy=1.0,
            branch_angle=math.radians(28),
            split_chance=0.62,
            shrink=0.82,
            color_bias=k,
            branch=b,
            last_draw_pos=start,
        ))
    return out


def reset_sim():
    global branches, tips, resting_tips, particles, visited, sim_time, mode_index, update_cursor
    for b in branches:
        b.curve_obj.visible = False
    for p in particles:
        p.visible = False
    branches = []
    tips = []
    resting_tips = []
    particles = []
    visited = {}
    tips.extend(initial_tips())
    sim_time = 0.0
    mode_index = 0
    update_cursor = 0
    nutrient.pos = vector(3.5, 0.30, -3.0)
    nutrient_halo.pos = nutrient.pos


def mutation_for_mode(tip):
    mode = current_mode()
    angle = tip.branch_angle
    split = tip.split_chance
    turn = 0.0

    if mode == "balanced":
        split += 0.02
    elif mode == "nutrient_seek":
        to_nutrient = horizontal(nutrient.pos - tip.pos, tip.direction)
        tip.direction = horizontal(blend(tip.direction, to_nutrient, 0.075), tip.direction)
        split += 0.05
    elif mode == "fan_growth":
        angle *= 1.28
        split += 0.14
    elif mode == "spiral_mutation":
        turn = 0.11 * math.sin(sim_time * 0.65 + tip.generation)
        angle *= 1.05 + 0.16 * math.sin(sim_time * 0.28)
        split += 0.08
    elif mode == "frontier_spread":
        radial = horizontal(tip.pos, tip.direction)
        if mag(vector(tip.pos.x, 0, tip.pos.z)) > 1.0:
            tip.direction = horizontal(blend(tip.direction, radial, 0.08), tip.direction)
        split += 0.06
        angle *= 0.95

    return clamp(angle, math.radians(12), math.radians(62)), clamp(split, 0.20, 0.92), turn


def wake_resting_tips():
    # All branch histories persist. To reduce load, very old frontier tips may be
    # stored in a resting queue and woken gradually, so growth spreads through the
    # whole coral without trying to update thousands of tips on the same frame.
    while resting_tips and len(tips) < MAX_ACTIVE_TIPS:
        t = resting_tips.pop(0)
        t.sleeping = False
        t.alive = True
        tips.append(t)


def split_tip(tip):
    if len(branches) > MAX_CURVE_OBJECTS:
        # Do not delete old branches. Only reduce how many new visual paths are
        # born after the scene is already dense.
        max_children = 1
    else:
        max_children = 3

    if tip.generation > 18 or tip.radius < 0.007 or tip.energy < 0.05:
        # Keep the branch persistent. Store a weak continuation that may wake
        # later as a thin exploratory branch instead of deleting it.
        if random.random() < 0.30 and len(resting_tips) < MAX_STORED_TIPS:
            tip.energy = random.uniform(0.20, 0.38)
            tip.radius = max(0.006, tip.radius * 0.94)
            tip.length_remaining = random.uniform(0.25, 0.55)
            tip.generation = min(20, tip.generation + 1)
            tip.alive = False
            tip.sleeping = True
            resting_tips.append(tip)
        return []

    angle, split_chance, turn = mutation_for_mode(tip)
    n_children = 1
    if random.random() < split_chance:
        n_children = 2
    if current_mode() in ("fan_growth", "frontier_spread") and random.random() < 0.24:
        n_children = 3
    n_children = min(n_children, max_children)

    children = []
    base_dir = horizontal(tip.direction)
    for i in range(n_children):
        if n_children == 1:
            offset = random.uniform(-angle * 0.42, angle * 0.42) + turn
        else:
            offset = -angle + 2 * angle * i / max(1, n_children - 1) + random.uniform(-0.10, 0.10) + turn

        d = rotate_y(base_dir, offset + random.uniform(-0.22, 0.22))

        radial = vector(tip.pos.x, 0, tip.pos.z)
        if mag(radial) > WORLD_RADIUS * 0.78:
            inward = horizontal(-radial, random_horizontal_dir())
            d = horizontal(blend(d, inward, 0.45), d)
        elif current_mode() == "frontier_spread" and mag(radial) > 0.7:
            outward = horizontal(radial, d)
            d = horizontal(blend(d, outward, 0.18), d)

        if crowding_at(tip.pos + d * 0.8) > 11:
            d = horizontal(d + random_horizontal_dir() * 0.7, d)

        radius = max(0.006, tip.radius * clamp(tip.shrink + random.uniform(-0.03, 0.025), 0.72, 0.90))
        generation = tip.generation + 1
        color_bias = (tip.color_bias + random.choice([-1, 0, 0, 1])) % len(PALETTE)
        col = color_for_generation(color_bias, generation, tip.pos)
        b = make_branch_path(tip.pos, radius, generation, col)
        child = Tip(
            pos=vector(tip.pos.x, tip.pos.y, tip.pos.z),
            direction=d,
            length_remaining=random.uniform(0.55, 1.15) * (0.985 ** min(generation, 15)),
            radius=radius,
            generation=generation,
            energy=tip.energy * random.uniform(0.78, 0.96),
            branch_angle=clamp(angle + random.uniform(-0.07, 0.07), math.radians(14), math.radians(62)),
            split_chance=clamp(split_chance + random.uniform(-0.06, 0.06), 0.16, 0.92),
            shrink=clamp(tip.shrink + random.uniform(-0.025, 0.025), 0.72, 0.90),
            color_bias=color_bias,
            branch=b,
            last_draw_pos=tip.pos,
        )
        children.append(child)

    return children


def update_tip(tip, dt):
    if not tip.alive:
        return []

    tip.age += dt
    mode = current_mode()
    speed = 0.50 + 0.42 * tip.energy
    if mode == "nutrient_seek":
        speed *= 1.12
    elif mode == "fan_growth":
        speed *= 1.05

    wander_strength = 0.035 if mode != "spiral_mutation" else 0.060
    tip.direction = horizontal(tip.direction + random_horizontal_dir() * wander_strength, tip.direction)

    # Slow planar nutrient pull, not vertical growth.
    if mode == "nutrient_seek":
        to_n = horizontal(nutrient.pos - tip.pos, tip.direction)
        tip.direction = horizontal(blend(tip.direction, to_n, 0.035), tip.direction)

    step_len = min(tip.length_remaining, speed * dt)
    if step_len <= 0.001:
        tip.alive = False
        return split_tip(tip)

    new_pos = tip.pos + tip.direction * step_len
    new_pos.y = 0.05 + 0.018 * math.sin(0.7 * sim_time + tip.generation * 0.6)

    radial = vector(new_pos.x, 0, new_pos.z)
    if mag(radial) > WORLD_RADIUS:
        inward = horizontal(-radial, random_horizontal_dir())
        tip.direction = horizontal(blend(tip.direction, inward, 0.72), inward)
        new_pos = tip.pos + tip.direction * step_len
        new_pos.y = 0.05

    tip.pos = new_pos
    tip.length_remaining -= step_len
    tip.energy -= dt * 0.010

    # Draw only after a noticeable distance. This keeps branches persistent while
    # using far fewer VPython objects and curve points.
    if mag(tip.pos - tip.last_draw_pos) >= POINT_APPEND_DISTANCE:
        tip.branch = append_branch_point(tip.branch, tip.pos)
        tip.last_draw_pos = vector(tip.pos.x, tip.pos.y, tip.pos.z)

    if SPARKS_ENABLED and random.random() < 0.012:
        p = sphere(pos=tip.pos, radius=max(0.012, tip.radius * 0.6),
                   color=blend(tip.branch.color, vector(1, 1, 1), 0.34),
                   opacity=0.35, emissive=True)
        p.birth = sim_time
        particles.append(p)

    if tip.length_remaining <= 0.006:
        tip.branch = append_branch_point(tip.branch, tip.pos)
        tip.alive = False
        return split_tip(tip)
    return []


def update_growth(dt):
    global tips, update_cursor
    wake_resting_tips()
    if not tips:
        wake_resting_tips()
    if not tips:
        tips.extend(initial_tips())

    new_tips = []
    live = []
    n = len(tips)
    updates = min(TIP_UPDATES_PER_FRAME, n)
    touched = set()

    for _ in range(updates):
        if n == 0:
            break
        idx = update_cursor % n
        update_cursor += 1
        touched.add(idx)
        t = tips[idx]
        if t.alive:
            new_tips.extend(update_tip(t, dt))

    for i, t in enumerate(tips):
        if t.alive:
            live.append(t)
        elif len(resting_tips) < MAX_STORED_TIPS and t.energy > 0.12 and random.random() < 0.02:
            t.sleeping = True
            resting_tips.append(t)

    tips = live + new_tips
    if len(tips) > MAX_ACTIVE_TIPS:
        # Store excess living tips rather than deleting their branches. They will
        # wake later and continue growth, spreading computation across time.
        random.shuffle(tips)
        overflow = tips[MAX_ACTIVE_TIPS:]
        tips = tips[:MAX_ACTIVE_TIPS]
        for t in overflow:
            t.sleeping = True
            t.alive = False
        resting_tips.extend(overflow[:max(0, MAX_STORED_TIPS - len(resting_tips))])

    # Fade only temporary particles; branch curves are never pruned.
    for p in list(particles):
        age = sim_time - getattr(p, "birth", sim_time)
        p.opacity = max(0, 0.35 * (1 - age / 3.5))
        if age > 3.5 or p.opacity <= 0.01:
            p.visible = False
            particles.remove(p)

# -----------------------------------------------------------------------------
# Input and camera
# -----------------------------------------------------------------------------
def keydown(evt):
    global paused, mode_index, show_help
    k = evt.key
    keys_down.add(k)
    if k in ("h", "H"):
        show_help = not show_help
    elif k in ("p", "P"):
        paused = not paused
    elif k in ("r", "R"):
        reset_sim()
    elif k in ("m", "M"):
        mode_index = (mode_index + 1) % len(MODE_NAMES)
    elif k in ("c", "C"):
        for p in list(particles):
            p.visible = False
        particles.clear()


def keyup(evt):
    keys_down.discard(evt.key)


scene.bind("keydown", keydown)
scene.bind("keyup", keyup)


def update_controls(dt):
    move = vector(0, 0, 0)
    if "w" in keys_down or "W" in keys_down:
        move.z -= 1
    if "s" in keys_down or "S" in keys_down:
        move.z += 1
    if "a" in keys_down or "A" in keys_down:
        move.x -= 1
    if "d" in keys_down or "D" in keys_down:
        move.x += 1
    if " " in keys_down:
        move.y += 1
    if "z" in keys_down or "Z" in keys_down:
        move.y -= 1
    if mag(move) > 0:
        nutrient.pos += safe_norm(move) * dt * 3.4
        nutrient.pos.x = clamp(nutrient.pos.x, -WORLD_RADIUS, WORLD_RADIUS)
        nutrient.pos.z = clamp(nutrient.pos.z, -WORLD_RADIUS, WORLD_RADIUS)
        nutrient.pos.y = clamp(nutrient.pos.y, 0.12, 1.1)
        nutrient_halo.pos = nutrient.pos

    pan = 0.06 * scene.range
    if "left" in keys_down:
        scene.center.x -= pan * dt
    if "right" in keys_down:
        scene.center.x += pan * dt
    if "up" in keys_down:
        scene.center.y += pan * dt
    if "down" in keys_down:
        scene.center.y -= pan * dt
    if "+" in keys_down or "=" in keys_down:
        scene.range = max(4, scene.range * (1 - 0.8 * dt))
    if "-" in keys_down or "_" in keys_down:
        scene.range = min(32, scene.range * (1 + 0.8 * dt))
    if "j" in keys_down or "J" in keys_down:
        scene.forward = rotate_y(scene.forward, -1.2 * dt)
    if "l" in keys_down or "L" in keys_down:
        scene.forward = rotate_y(scene.forward, 1.2 * dt)
    if "i" in keys_down or "I" in keys_down:
        scene.forward = safe_norm(scene.forward + vector(0, 0.55 * dt, 0), scene.forward)
    if "k" in keys_down or "K" in keys_down:
        scene.forward = safe_norm(scene.forward + vector(0, -0.55 * dt, 0), scene.forward)

# -----------------------------------------------------------------------------
# Display
# -----------------------------------------------------------------------------
def update_display():
    active_tips = sum(1 for t in tips if t.alive)
    root_core.radius = 0.34 + 0.035 * math.sin(sim_time * 2.2) + 0.018 * min(10, active_tips) / 10
    root_ring.radius = 0.52 + 0.045 * math.sin(sim_time * 1.5)
    nutrient_halo.radius = 0.85 + 0.10 * math.sin(sim_time * 2.0)
    nutrient_halo.opacity = 0.12 + 0.03 * math.sin(sim_time * 2.4)

    status.text = (
        "FRACTAL CORAL — PERSISTENT LIGHTWEIGHT GROWTH\n"
        f"mode: {current_mode()}\n"
        f"curve branches: {len(branches)} / soft {MAX_CURVE_OBJECTS}\n"
        f"active tips: {active_tips} / {MAX_ACTIVE_TIPS}\n"
        f"resting future tips: {len(resting_tips)}\n"
        f"covered cells: {len(visited)}\n"
        f"render: curves only, no branch pruning\n"
        f"paused: {paused}\n"
    )

    if show_help:
        help_label.visible = True
        help_label.text = (
            "Controls\n"
            "P pause/resume   R reset   M mode\n"
            "WASD move nutrient on plane\n"
            "Space/Z raise/lower nutrient\n"
            "Arrow keys pan camera\n"
            "J/L rotate   I/K tilt   +/- zoom\n"
            "C clear sparks   H help\n\n"
            "Behavior\n"
            "Every visible branch persists.\n"
            "Tips split and continue across the plane.\n"
            "Extra tips rest and wake later to reduce load."
        )
    else:
        help_label.visible = False

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
reset_sim()

while True:
    rate(30)
    dt = BASE_DT
    update_controls(dt)
    if not paused:
        sim_time += dt
        update_growth(dt)
    update_display()
