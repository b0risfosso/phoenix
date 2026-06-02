"""
fractal_coral_v2_horizontal_growth.py

A VPython simulation of a living fractal coral organism.

Concept:
- A coral begins as one growing tip on a flat ground plane.
- Each tip grows horizontally across the X/Z plane, then splits, rotates, shrinks, and repeats.
- Mutations change branch angle, color, thickness, and growth rhythm without climbing upward.
- The coral tries to cover horizontal space while preserving symmetry and avoiding overcrowding.

Controls:
  H       show/hide help
  P       pause/resume
  R       reset coral
  M       cycle autonomous mode
  C       clear old faded particles/labels
  W/A/S/D move the nutrient light source on the ground plane
  Space   raise nutrient light
  Z       lower nutrient light
  + / -   zoom camera
  Arrow keys pan camera center
  J/L     rotate camera around coral
  I/K     tilt camera

Run:
  python fractal_coral_v2_horizontal_growth.py

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
    title="Fractal Coral - living mathematical growth",
    width=1200,
    height=800,
    background=vector(0.92, 0.96, 1.0),
    center=vector(0, 0.6, 0),
)
scene.forward = vector(-0.45, -0.72, -0.55)
scene.range = 12

WORLD_RADIUS = 9.5
GROUND_Y = -0.08
MAX_BRANCHES = 900
MAX_TIPS = 180
BASE_DT = 1.0 / 60.0

# Soft palette, light background friendly
PALETTE = [
    vector(0.98, 0.45, 0.36),
    vector(0.95, 0.58, 0.28),
    vector(0.98, 0.72, 0.38),
    vector(0.64, 0.82, 0.52),
    vector(0.42, 0.72, 0.84),
    vector(0.62, 0.56, 0.88),
    vector(0.88, 0.52, 0.72),
]

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(0, 1, 0)):
    if mag(v) < 1e-6:
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


def cell_key(pos, size=1.0):
    return (round(pos.x / size), round(pos.y / size), round(pos.z / size))

# -----------------------------------------------------------------------------
# Data structures
# -----------------------------------------------------------------------------
@dataclass
class Branch:
    start: vector
    end: vector
    radius: float
    age: float
    generation: int
    color: vector
    shape: object
    glow: object = None


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
    age: float = 0.0
    grow_clock: float = 0.0
    alive: bool = True
    parent_key: tuple = field(default_factory=tuple)

# -----------------------------------------------------------------------------
# World objects
# -----------------------------------------------------------------------------
ground = cylinder(
    pos=vector(0, GROUND_Y - 0.04, 0),
    axis=vector(0, 0.04, 0),
    radius=WORLD_RADIUS + 1.2,
    color=vector(0.86, 0.90, 0.82),
    opacity=0.55,
)

boundary = ring(
    pos=vector(0, GROUND_Y + 0.015, 0),
    axis=vector(0, 1, 0),
    radius=WORLD_RADIUS,
    thickness=0.035,
    color=vector(0.62, 0.72, 0.68),
    opacity=0.35,
)

# faint grid
grid_lines = []
for i in range(-9, 10):
    grid_lines.append(curve(pos=[vector(i, GROUND_Y + 0.01, -9), vector(i, GROUND_Y + 0.01, 9)],
                            radius=0.008, color=vector(0.72, 0.78, 0.76), opacity=0.25))
    grid_lines.append(curve(pos=[vector(-9, GROUND_Y + 0.01, i), vector(9, GROUND_Y + 0.01, i)],
                            radius=0.008, color=vector(0.72, 0.78, 0.76), opacity=0.25))

root_core = sphere(pos=vector(0, 0, 0), radius=0.34, color=vector(0.95, 0.42, 0.34), emissive=False)
root_ring = ring(pos=root_core.pos, axis=vector(0, 1, 0), radius=0.52, thickness=0.025,
                 color=vector(1.0, 0.75, 0.45), opacity=0.6)

nutrient = sphere(pos=vector(3.2, 0.35, -2.8), radius=0.32, color=vector(0.35, 0.62, 1.0), emissive=True)
nutrient_halo = sphere(pos=nutrient.pos, radius=0.85, color=nutrient.color, opacity=0.14, emissive=True)

status = label(pos=vector(-9.8, 3.4, 0), text="", box=False, opacity=0, height=13,
               color=vector(0.18, 0.24, 0.25), align="left")
help_label = label(pos=vector(6.4, 3.2, 0), text="", box=True, height=11,
                   color=vector(0.1, 0.14, 0.16), background=vector(0.96, 0.98, 1.0),
                   border=10, opacity=0.78, align="left")

MODE_NAMES = ["symmetry", "nutrient_seek", "fan_growth", "spiral_mutation", "rest_prune"]
mode_index = 0
paused = False
show_help = True
sim_time = 0.0

branches = []
tips = []
particles = []
visited = {}
keys_down = set()

# -----------------------------------------------------------------------------
# Coral growth logic
# -----------------------------------------------------------------------------
def make_branch(start, end, radius, generation, col):
    axis = end - start
    if mag(axis) < 1e-5:
        return None
    obj = cylinder(
        pos=start,
        axis=axis,
        radius=max(0.012, radius),
        color=col,
        opacity=0.82,
    )
    glow = sphere(
        pos=end,
        radius=max(0.025, radius * 1.8),
        color=blend(col, vector(1, 1, 1), 0.22),
        opacity=0.28,
        emissive=True,
    )
    b = Branch(start=start, end=end, radius=radius, age=0, generation=generation, color=col, shape=obj, glow=glow)
    branches.append(b)
    visited[cell_key(end, 0.75)] = visited.get(cell_key(end, 0.75), 0) + 1
    return b


def initial_tips():
    new_tips = []
    for k in range(6):
        a = k * 2 * math.pi / 6
        # Horizontal first generation: spread outward across X/Z instead of climbing upward.
        d = safe_norm(vector(math.cos(a), 0.03, math.sin(a)), random_horizontal_dir())
        new_tips.append(Tip(
            pos=vector(0, 0.08, 0),
            direction=d,
            length_remaining=random.uniform(0.55, 0.9),
            radius=0.09,
            generation=0,
            energy=1.0,
            branch_angle=math.radians(31),
            split_chance=0.38,
            shrink=0.76,
            color_bias=k % len(PALETTE),
            parent_key=(0, 0, 0),
        ))
    return new_tips


def reset_sim():
    global branches, tips, particles, visited, sim_time, mode_index
    for b in branches:
        b.shape.visible = False
        if b.glow:
            b.glow.visible = False
    for p in particles:
        p.visible = False
    branches = []
    particles = []
    visited = {}
    tips = initial_tips()
    sim_time = 0
    mode_index = 0
    root_core.radius = 0.34
    nutrient.pos = vector(3.2, 0.35, -2.8)
    nutrient_halo.pos = nutrient.pos


def current_mode():
    return MODE_NAMES[mode_index % len(MODE_NAMES)]


def color_for_tip(tip):
    base = PALETTE[tip.color_bias % len(PALETTE)]
    spread_tint = clamp(mag(vector(tip.pos.x, 0, tip.pos.z)) / WORLD_RADIUS, 0, 1)
    gen_tint = clamp(tip.generation / 10.0, 0, 1)
    return blend(base, vector(1.0, 0.95, 0.72), 0.18 * spread_tint + 0.10 * gen_tint)


def crowding_at(pos):
    c = 0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                key = (round(pos.x / 0.75) + dx, round(pos.y / 0.75) + dy, round(pos.z / 0.75) + dz)
                c += visited.get(key, 0)
    return c


def mutation_for_mode(tip):
    mode = current_mode()
    angle = tip.branch_angle
    split = tip.split_chance
    upward = 0.0
    twist = 0.0

    if mode == "symmetry":
        angle *= 0.85
        split += 0.04
        upward = 0.01
    elif mode == "nutrient_seek":
        to_nutrient = safe_norm(nutrient.pos - tip.pos, tip.direction)
        tip.direction = safe_norm(blend(tip.direction, to_nutrient, 0.045), tip.direction)
        split += 0.02
        upward = 0.0
    elif mode == "fan_growth":
        angle *= 1.22
        split += 0.10
        upward = 0.0
    elif mode == "spiral_mutation":
        twist = 0.09 * math.sin(sim_time * 0.8 + tip.generation)
        angle *= 1.05 + 0.15 * math.sin(sim_time * 0.3)
        split += 0.05
        upward = 0.0
    elif mode == "rest_prune":
        split -= 0.15
        upward = 0.01

    return angle, clamp(split, 0.08, 0.68), upward, twist


def split_tip(tip):
    angle, split_chance, upward, twist = mutation_for_mode(tip)
    if len(tips) > MAX_TIPS or len(branches) > MAX_BRANCHES:
        return []

    # Stop very old or tiny tips, but leave their branches visible.
    if tip.generation > 11 or tip.radius < 0.015 or tip.energy < 0.10:
        return []

    crowd = crowding_at(tip.pos)
    if crowd > 8 and random.random() < 0.7:
        return []

    n_children = 1
    if random.random() < split_chance:
        n_children = 2
    if current_mode() == "fan_growth" and random.random() < 0.18 and tip.generation < 7:
        n_children = 3

    children = []
    # Project growth back onto the horizontal X/Z plane. A tiny Y component keeps
    # branches visible above the ground without producing vertical coral towers.
    base_dir = safe_norm(vector(tip.direction.x, 0, tip.direction.z) + vector(0, upward, 0), random_horizontal_dir())
    side_axis = safe_norm(cross(base_dir, vector(0, 1, 0)), random_horizontal_dir())

    for i in range(n_children):
        if n_children == 1:
            offset_angle = random.uniform(-angle * 0.35, angle * 0.35) + twist
        else:
            offset_angle = (-angle + 2 * angle * i / max(1, n_children - 1)) + random.uniform(-0.12, 0.12) + twist

        horizontal_turn = random.uniform(-0.7, 0.7)
        d = rotate_y(base_dir, horizontal_turn)
        d = safe_norm(d + side_axis * math.sin(offset_angle) * 0.75 + vector(0, 0.006, 0), base_dir)
        d = safe_norm(vector(d.x, clamp(d.y, -0.015, 0.035), d.z), base_dir)

        # Stay within world: bend inward if outside the boundary.
        radial = vector(tip.pos.x, 0, tip.pos.z)
        if mag(radial) > WORLD_RADIUS * 0.78:
            inward = safe_norm(-radial, random_horizontal_dir())
            d = safe_norm(blend(d, vector(inward.x, 0.01, inward.z), 0.48), d)

        # Avoid excessive local density.
        test_pos = tip.pos + d * 0.7
        if crowding_at(test_pos) > 8:
            d = safe_norm(d + random_horizontal_dir() * 0.70 + vector(0, 0.004, 0), d)

        mut_angle = clamp(angle + random.uniform(-0.07, 0.07), math.radians(16), math.radians(58))
        mut_split = clamp(split_chance + random.uniform(-0.08, 0.08), 0.05, 0.72)
        mut_shrink = clamp(tip.shrink + random.uniform(-0.035, 0.035), 0.66, 0.84)
        child_radius = tip.radius * mut_shrink
        child_energy = tip.energy * random.uniform(0.76, 0.94)
        length = random.uniform(0.42, 0.86) * (0.96 ** tip.generation)
        children.append(Tip(
            pos=vector(tip.pos.x, tip.pos.y, tip.pos.z),
            direction=d,
            length_remaining=max(0.18, length),
            radius=child_radius,
            generation=tip.generation + 1,
            energy=child_energy,
            branch_angle=mut_angle,
            split_chance=mut_split,
            shrink=mut_shrink,
            color_bias=(tip.color_bias + random.choice([0, 0, 1, -1])) % len(PALETTE),
            parent_key=cell_key(tip.pos, 0.75),
        ))
    return children


def update_tip(tip, dt):
    if not tip.alive:
        return []

    # Growth step: slow enough to watch; fast enough to develop in seconds.
    tip.age += dt
    tip.grow_clock += dt
    speed = 0.35 + 0.35 * tip.energy + 0.08 * math.sin(sim_time * 2 + tip.generation)

    if current_mode() == "rest_prune":
        speed *= 0.55
    elif current_mode() == "nutrient_seek":
        speed *= 1.10

    step_len = min(tip.length_remaining, speed * dt)
    if step_len <= 0.002:
        tip.alive = False
        return split_tip(tip)

    old = vector(tip.pos.x, tip.pos.y, tip.pos.z)
    wander = random_horizontal_dir() * 0.018
    # Keep motion broad and planar; the coral crawls across the ground plane.
    planar_dir = vector(tip.direction.x, 0, tip.direction.z)
    tip.direction = safe_norm(planar_dir + wander + vector(0, 0.002, 0), random_horizontal_dir())

    new_pos = tip.pos + tip.direction * step_len
    if new_pos.y < 0.02:
        new_pos.y = 0.02
        tip.direction = safe_norm(vector(tip.direction.x, 0.006, tip.direction.z), random_horizontal_dir())

    radial = vector(new_pos.x, 0, new_pos.z)
    if mag(radial) > WORLD_RADIUS:
        inward = safe_norm(-radial, vector(0, 0, 1))
        tip.direction = safe_norm(vector(inward.x, 0.006, inward.z), random_horizontal_dir())
        new_pos = tip.pos + tip.direction * step_len

    col = color_for_tip(tip)
    make_branch(old, new_pos, tip.radius, tip.generation, col)
    tip.pos = new_pos
    tip.length_remaining -= step_len
    tip.energy -= dt * 0.015

    # Occasional glowing growth particle.
    if random.random() < 0.04:
        p = sphere(pos=new_pos, radius=max(0.018, tip.radius * 0.7), color=blend(col, vector(1, 1, 1), 0.3),
                   opacity=0.42, emissive=True)
        p.birth = sim_time
        particles.append(p)

    if tip.length_remaining <= 0.01:
        tip.alive = False
        return split_tip(tip)
    return []


def prune_old_geometry():
    # Thin and fade crowded/tangled old growth to keep the coral readable.
    remove = []
    for b in branches:
        b.age += BASE_DT
        if current_mode() == "rest_prune":
            b.shape.opacity = max(0.22, b.shape.opacity * 0.9993)
        if len(branches) > MAX_BRANCHES and b.generation > 4:
            b.shape.opacity *= 0.992
            if b.glow:
                b.glow.opacity *= 0.990
        if b.shape.opacity < 0.045:
            remove.append(b)
    for b in remove[:25]:
        b.shape.visible = False
        if b.glow:
            b.glow.visible = False
        try:
            branches.remove(b)
        except ValueError:
            pass

    # Particle fade.
    for p in list(particles):
        age = sim_time - getattr(p, "birth", sim_time)
        p.opacity = max(0, 0.42 * (1 - age / 5.0))
        p.radius *= 0.999
        if age > 5.0 or p.opacity <= 0.01:
            p.visible = False
            particles.remove(p)


def clear_particles():
    for p in list(particles):
        p.visible = False
    particles.clear()

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
        clear_particles()


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
        nutrient.pos += safe_norm(move) * dt * 3.3
        nutrient.pos.x = clamp(nutrient.pos.x, -WORLD_RADIUS, WORLD_RADIUS)
        nutrient.pos.z = clamp(nutrient.pos.z, -WORLD_RADIUS, WORLD_RADIUS)
        nutrient.pos.y = clamp(nutrient.pos.y, 0.15, 1.4)
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
        scene.range = min(28, scene.range * (1 + 0.8 * dt))
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
    coverage = len(visited)
    root_core.radius = 0.34 + 0.04 * math.sin(sim_time * 2.6) + 0.018 * min(8, active_tips) / 8
    root_ring.radius = 0.52 + 0.05 * math.sin(sim_time * 1.7)
    nutrient_halo.radius = 0.85 + 0.12 * math.sin(sim_time * 2.2)
    nutrient_halo.opacity = 0.12 + 0.035 * math.sin(sim_time * 2.7)

    status.text = (
        f"FRACTAL CORAL — HORIZONTAL GROWTH\n"
        f"mode: {current_mode()}\n"
        f"branches: {len(branches)} / {MAX_BRANCHES}\n"
        f"active tips: {active_tips}\n"
        f"covered cells: {coverage}\n"
        f"nutrient: ({nutrient.pos.x: .1f}, {nutrient.pos.y: .1f}, {nutrient.pos.z: .1f})\n"
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
            "C clear particles   H help\n\n"
            "Goal\n"
            "Grow a branching coral from repeated\n"
            "split, rotate, shrink, and mutate rules."
        )
    else:
        help_label.visible = False

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
reset_sim()

while True:
    rate(60)
    dt = BASE_DT
    update_controls(dt)

    if not paused:
        sim_time += dt

        # If no tips are alive, seed a new generation from strong branch ends.
        if not any(t.alive for t in tips):
            candidates = branches[-80:] if len(branches) >= 4 else []
            random.shuffle(candidates)
            for b in candidates[:8]:
                if len(tips) >= MAX_TIPS:
                    break
                d = safe_norm(vector((b.end - b.start).x, 0.006, (b.end - b.start).z), random_horizontal_dir())
                tips.append(Tip(
                    pos=b.end,
                    direction=d,
                    length_remaining=random.uniform(0.36, 0.72),
                    radius=max(0.018, b.radius * random.uniform(0.72, 0.88)),
                    generation=min(12, b.generation + 1),
                    energy=random.uniform(0.45, 0.82),
                    branch_angle=random.uniform(math.radians(22), math.radians(45)),
                    split_chance=random.uniform(0.18, 0.44),
                    shrink=random.uniform(0.68, 0.82),
                    color_bias=random.randrange(len(PALETTE)),
                ))
            if not candidates:
                tips.extend(initial_tips())

        new_tips = []
        live_tips = []
        # Randomize update order to avoid rigid symmetry while keeping symmetry visible.
        random.shuffle(tips)
        for tip in tips[:MAX_TIPS]:
            if tip.alive:
                children = update_tip(tip, dt)
                new_tips.extend(children)
            if tip.alive:
                live_tips.append(tip)

        # Keep freshest active tips plus new children.
        tips = (live_tips + new_tips)[-MAX_TIPS:]
        prune_old_geometry()

    update_display()
