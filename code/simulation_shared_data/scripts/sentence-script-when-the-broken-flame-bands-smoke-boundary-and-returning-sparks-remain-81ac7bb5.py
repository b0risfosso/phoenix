"""
Fire That Wants To Become A Star — Iteration 12
Stable Glowing Core

Story:
The flame has a fragile proto-core and faint circular heat paths.
Broken flame bands, smoke boundary, and returning sparks now synchronize across
several cycles. When their rhythms align, the fragile proto-core condenses into a
stable glowing core that holds heat even when fewer sparks return.

This is still not a completed star:
- the smoke layer is uneven and weak
- sparks can still escape
- the core can become stable after repeated synchronized cycles
- the flame bands can still flicker and break
- there is no sealed shell or completed star yet

Controls:
    H       show/hide help
    P       pause/resume
    R       reset
    W       strengthen will
    Space   upward breath
    I       brief inward pull boost
    C       advance/energize the current cycle
    E       briefly feed the proto-core
    O       briefly encourage spark looping
    G       briefly strengthen heat-path guidance
    S       briefly thicken smoke boundary
    B       briefly strengthen broken flame bands
    X       briefly synchronize bands, smoke, and returns
"""

from vpython import *
import random
import math

# -----------------------------
# Scene
# -----------------------------
scene.title = "Fire That Wants To Become A Star — Stable Glowing Core"
scene.width = 1160
scene.height = 740
scene.background = vector(0.96, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.range = 6.15
scene.center = vector(0.75, 1.42, 0)

ground = box(
    pos=vector(0, -0.04, 0),
    size=vector(8, 0.06, 8),
    color=vector(0.78, 0.73, 0.65)
)

charred_patch = cylinder(
    pos=vector(0, 0.005, 0),
    axis=vector(0, 0.01, 0),
    radius=0.68,
    color=vector(0.18, 0.15, 0.12),
    opacity=0.55
)

# -----------------------------
# Flame body
# -----------------------------
flame_base = sphere(
    pos=vector(0, 0.18, 0),
    radius=0.18,
    color=vector(1.0, 0.28, 0.04),
    emissive=True
)

base_heat_glow = sphere(
    pos=vector(0, 0.20, 0),
    radius=0.25,
    color=vector(1.0, 0.52, 0.05),
    opacity=0.10,
    emissive=True
)

unstable_ember = sphere(
    pos=vector(0, 0.23, 0),
    radius=0.055,
    color=vector(1.0, 0.62, 0.08),
    opacity=0.14,
    emissive=True
)

proto_core_shell = sphere(
    pos=unstable_ember.pos,
    radius=0.11,
    color=vector(1.0, 0.50, 0.06),
    opacity=0.035,
    emissive=True
)

# New: stable core. It starts invisible and condenses after synchronized cycles.
stable_core = sphere(
    pos=unstable_ember.pos,
    radius=0.07,
    color=vector(1.0, 0.78, 0.16),
    opacity=0.0,
    emissive=True
)

stable_core_halo = sphere(
    pos=unstable_ember.pos,
    radius=0.24,
    color=vector(1.0, 0.62, 0.10),
    opacity=0.0,
    emissive=True
)

ember_pulse_ring = ring(
    pos=unstable_ember.pos,
    axis=vector(0, 1, 0),
    radius=0.18,
    thickness=0.006,
    color=vector(1.0, 0.48, 0.05),
    opacity=0.07,
    emissive=True
)

loop_guide_ring = ring(
    pos=vector(0, 0.58, 0),
    axis=vector(0, 1, 0),
    radius=0.72,
    thickness=0.006,
    color=vector(1.0, 0.58, 0.08),
    opacity=0.02,
    emissive=True
)

# Weak smoke boundary visual. It is not a shell yet; it is just a soft, uneven upper layer.
smoke_boundary_ring = ring(
    pos=vector(0, 1.92, 0),
    axis=vector(0, 1, 0),
    radius=1.05,
    thickness=0.018,
    color=vector(0.55, 0.56, 0.56),
    opacity=0.025
)

smoke_boundary_haze = sphere(
    pos=vector(0, 1.85, 0),
    radius=1.10,
    color=vector(0.62, 0.63, 0.62),
    opacity=0.018
)

# New: broken rotating flame bands grown from repeated heat paths.
# These are not stable star bands yet. They thicken, rotate, and break/fade.
broken_flame_bands = []
for i in range(4):
    broken_flame_bands.append({
        "obj": ring(
            pos=vector(0, 0.62 + i * 0.18, 0),
            axis=norm(vector(random.uniform(-0.18, 0.18), 1.0, random.uniform(-0.18, 0.18))),
            radius=0.56 + i * 0.18,
            thickness=0.004,
            color=vector(1.0, 0.36 + 0.09 * i, 0.04),
            opacity=0.0,
            emissive=True
        ),
        "strength": 0.0,
        "break_phase": random.random() * math.tau,
        "spin": random.choice([-1, 1]) * random.uniform(0.45, 0.90),
        "height": 0.62 + i * 0.18,
        "radius": 0.56 + i * 0.18,
    })

# Broken circular heat paths. They are reusable memory routes, not stable bands.
heat_paths = []
for i in range(5):
    heat_paths.append({
        "obj": ring(
            pos=vector(0, 0.42 + i * 0.12, 0),
            axis=norm(vector(random.uniform(-0.10, 0.10), 1.0, random.uniform(-0.10, 0.10))),
            radius=0.38 + i * 0.12,
            thickness=0.003,
            color=vector(1.0, 0.46 + 0.05 * i, 0.04),
            opacity=0.0,
            emissive=True
        ),
        "strength": 0.0,
        "target_radius": 0.38 + i * 0.12,
        "height": 0.42 + i * 0.12,
        "spin": random.choice([-1, 1]) * random.uniform(0.18, 0.42),
        "phase": random.random() * math.tau,
    })

flame_tip = cone(
    pos=vector(0, 0.25, 0),
    axis=vector(0, 0.72, 0),
    radius=0.22,
    color=vector(1.0, 0.52, 0.08),
    opacity=0.86,
    emissive=True
)

inner_flame = cone(
    pos=vector(0, 0.28, 0),
    axis=vector(0, 0.48, 0),
    radius=0.11,
    color=vector(1.0, 0.90, 0.30),
    opacity=0.72,
    emissive=True
)

desired_star = sphere(
    pos=vector(0, 3.34, 0),
    radius=0.18,
    color=vector(1.0, 0.85, 0.20),
    opacity=0.22,
    emissive=True
)

will_line = curve(
    pos=[flame_tip.pos + vector(0, 0.45, 0), desired_star.pos],
    radius=0.01,
    color=vector(1.0, 0.62, 0.05)
)

flame_light = local_light(
    pos=vector(0, 0.55, 0),
    color=vector(1.0, 0.45, 0.10)
)

inward_field_ring = ring(
    pos=vector(0, 0.78, 0),
    axis=vector(0, 1, 0),
    radius=0.78,
    thickness=0.01,
    color=vector(1.0, 0.38, 0.05),
    opacity=0.10,
    emissive=True
)

cycle_halo = ring(
    pos=vector(0, 0.32, 0),
    axis=vector(0, 1, 0),
    radius=0.45,
    thickness=0.012,
    color=vector(1.0, 0.48, 0.06),
    opacity=0.16,
    emissive=True
)

survival_ring = ring(
    pos=vector(0, 0.26, 0),
    axis=vector(0, 1, 0),
    radius=0.30,
    thickness=0.007,
    color=vector(1.0, 0.65, 0.10),
    opacity=0.03,
    emissive=True
)

# -----------------------------
# Particles and marks
# -----------------------------
sparks = []
memory_marks = []
return_embers = []
storage_motes = []
collapse_shards = []
loop_echoes = []
path_motes = []
smoke_wisps = []

MAX_MEMORY_MARKS = 85
MAX_RETURN_EMBERS = 50
MAX_STORAGE_MOTES = 60
MAX_COLLAPSE_SHARDS = 40
MAX_LOOP_ECHOES = 45
MAX_PATH_MOTES = 70
MAX_SMOKE_WISPS = 90

for _ in range(30):
    s = sphere(
        pos=vector(random.uniform(-0.12, 0.12), random.uniform(0.3, 0.65), random.uniform(-0.12, 0.12)),
        radius=random.uniform(0.015, 0.035),
        color=vector(1.0, random.uniform(0.45, 0.85), 0.08),
        emissive=True,
        opacity=0.85
    )
    tr = curve(radius=0.006, color=vector(1.0, 0.45, 0.05))
    sparks.append({
        "obj": s,
        "trail": tr,
        "vel": vector(random.uniform(-0.10, 0.10), random.uniform(0.30, 0.75), random.uniform(-0.10, 0.10)),
        "age": random.random() * 2.0,
        "life": random.uniform(1.5, 3.4),
        "bendable": random.random() < 0.60,
        "loopable": random.random() < 0.52,
        "return_glow": 0.0,
        "loop_glow": 0.0,
        "path_glow": 0.0,
        "smoke_slow_glow": 0.0,
        "has_bent": False,
        "has_looped": False,
        "followed_path": False,
        "slowed_by_smoke": False,
        "rewarded": False,
        "cycle_birth": 0,
        "last_angle": 0.0,
        "angle_travel": 0.0,
        "loop_time": 0.0,
    })

escape_column = curve(
    pos=[vector(0, 0.5, 0), vector(0, 2.45, 0)],
    radius=0.006,
    color=vector(1.0, 0.48, 0.08)
)
escape_column.opacity = 0.18

# -----------------------------
# Labels / HUD on right side
# -----------------------------
title_label = label(
    pos=vector(3.05, 4.18, 0),
    text="Synchronized bands, smoke, and returns condense a stable core",
    height=15,
    box=False,
    color=vector(0.15, 0.12, 0.08),
    align="left"
)

status_label = label(
    pos=vector(3.05, 3.68, 0),
    text="",
    height=10,
    box=True,
    border=7,
    opacity=0.12,
    color=vector(0.20, 0.15, 0.08),
    background=vector(1.0, 0.96, 0.86),
    align="left"
)

help_label = label(
    pos=vector(3.05, 4.55, 0),
    text="H help | P pause | R reset | W will | Space breath | I pull | C cycle | E core | O loop | G guide | S smoke | B bands | X sync",
    height=9,
    box=False,
    align="left",
    color=vector(0.12, 0.12, 0.12)
)

# -----------------------------
# State
# -----------------------------
t = 0.0
dt = 0.025
paused = False
show_help = True

will_to_become_star = 0.34
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

inward_pull = 0.15
manual_pull_boost = 0.0
bent_spark_count = 0

returned_heat = 0.0
return_reward_count = 0
base_brighten = 0.0

cycle_time = 0.0
cycle_duration = 5.8
cycle_number = 1
cycle_phase = "rise"
cycle_energy = 0.30
last_phase = "rise"

rise_drive = 0.0
pull_drive = 0.0
receive_drive = 0.0
rest_drive = 0.0

inner_ember_heat = 0.0
inner_ember_instability = 1.0
stored_heat_events = 0
ember_feed_boost = 0.0
last_rest_storage_tick = 0.0

proto_core_persistence = 0.0
proto_core_survival_streak = 0
proto_core_collapse_count = 0
last_cycle_return_count = 0
last_cycle_store_count = 0
cycle_start_returns = 0
cycle_start_storage = 0
collapse_flash = 0.0
survival_flash = 0.0

loop_strength = 0.0
manual_loop_boost = 0.0
partial_loop_count = 0
loop_return_count = 0
loop_escape_count = 0
last_cycle_loop_count = 0
cycle_start_loops = 0

heat_path_memory = 0.0
path_guidance = 0.0
manual_path_boost = 0.0
path_follow_count = 0
path_reinforce_count = 0
last_cycle_path_count = 0
cycle_start_path_follows = 0

# New smoke-boundary state.
smoke_memory = 0.0
smoke_boundary_strength = 0.0
manual_smoke_boost = 0.0
smoke_wisp_count = 0
smoke_slow_count = 0
last_cycle_smoke_slow_count = 0
cycle_start_smoke_slows = 0


# New flame-band state.
flame_band_memory = 0.0
flame_band_strength = 0.0
manual_band_boost = 0.0
band_reinforce_count = 0
band_break_count = 0
last_cycle_band_gain = 0
cycle_start_band_reinforces = 0

# New stable-core state.
core_synchrony = 0.0
stable_core_strength = 0.0
stable_core_heat = 0.0
stable_core_cycles = 0
core_condense_events = 0
core_stability_flash = 0.0
manual_sync_boost = 0.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v):
    if mag(v) < 0.0001:
        return vector(0, 0, 0)
    return norm(v)

def tangent_around_y(rel):
    flat = vector(rel.x, 0, rel.z)
    if mag(flat) < 0.0001:
        return vector(0, 0, 0)
    return norm(vector(-flat.z, 0, flat.x))

def signed_angle_step(prev_angle, new_angle):
    d = new_angle - prev_angle
    while d > math.pi:
        d -= math.tau
    while d < -math.pi:
        d += math.tau
    return d

def nearest_heat_path(rel_loop):
    flat_dist = mag(vector(rel_loop.x, 0, rel_loop.z))
    y = rel_loop.y
    best = heat_paths[0]
    best_score = 999.0
    for hp in heat_paths:
        score = abs(flat_dist - hp["target_radius"]) + abs(y - hp["height"]) * 0.55
        if score < best_score:
            best_score = score
            best = hp
    return best, best_score

def reset_spark(p):
    p["obj"].pos = vector(
        random.uniform(-0.12, 0.12),
        random.uniform(0.25, 0.55),
        random.uniform(-0.12, 0.12)
    )
    p["obj"].opacity = 0.85
    p["obj"].visible = True
    p["obj"].radius = random.uniform(0.015, 0.035)
    p["trail"].clear()
    p["vel"] = vector(
        random.uniform(-0.10, 0.10),
        random.uniform(0.30, 0.75),
        random.uniform(-0.10, 0.10)
    )
    p["age"] = 0.0
    p["life"] = random.uniform(1.6, 3.6)
    p["bendable"] = random.random() < 0.60
    p["loopable"] = random.random() < 0.52
    p["return_glow"] = 0.0
    p["loop_glow"] = 0.0
    p["path_glow"] = 0.0
    p["smoke_slow_glow"] = 0.0
    p["has_bent"] = False
    p["has_looped"] = False
    p["followed_path"] = False
    p["slowed_by_smoke"] = False
    p["rewarded"] = False
    p["cycle_birth"] = cycle_number
    p["last_angle"] = math.atan2(p["obj"].pos.z - unstable_ember.pos.z, p["obj"].pos.x - unstable_ember.pos.x)
    p["angle_travel"] = 0.0
    p["loop_time"] = 0.0

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.020, 0.0, 1.0)

    dot = sphere(
        pos=pos,
        radius=random.uniform(0.035, 0.065),
        color=vector(1.0, 0.42, 0.04),
        opacity=0.30,
        emissive=True
    )

    stroke_length = random.uniform(0.18, 0.42)
    stroke = curve(
        pos=[pos, pos - vector(0, stroke_length, 0)],
        radius=random.uniform(0.004, 0.008),
        color=vector(1.0, 0.36, 0.04)
    )
    stroke.opacity = 0.22

    memory_marks.append({
        "dot": dot,
        "stroke": stroke,
        "age": 0.0,
        "life": random.uniform(5.0, 8.5),
        "base_radius": dot.radius,
        "drift": vector(random.uniform(-0.004, 0.004), random.uniform(0.002, 0.010), random.uniform(-0.004, 0.004)),
    })

    while len(memory_marks) > MAX_MEMORY_MARKS:
        old = memory_marks.pop(0)
        old["dot"].visible = False
        old["stroke"].visible = False

def add_smoke_wisp(pos, from_slow=False):
    global smoke_wisp_count, smoke_memory, smoke_boundary_strength

    smoke_wisp_count += 1
    smoke_memory = clamp(smoke_memory + (0.026 if not from_slow else 0.012), 0.0, 1.0)
    smoke_boundary_strength = clamp(smoke_boundary_strength + (0.018 if not from_slow else 0.008), 0.0, 0.86)

    w = sphere(
        pos=pos + vector(random.uniform(-0.05, 0.05), random.uniform(-0.02, 0.08), random.uniform(-0.05, 0.05)),
        radius=random.uniform(0.045, 0.095),
        color=vector(0.52 + random.uniform(-0.04, 0.04), 0.53 + random.uniform(-0.03, 0.03), 0.53 + random.uniform(-0.03, 0.03)),
        opacity=0.16,
    )
    smoke_wisps.append({
        "obj": w,
        "age": 0.0,
        "life": random.uniform(5.8, 9.2),
        "drift": vector(random.uniform(-0.010, 0.010), random.uniform(0.006, 0.022), random.uniform(-0.010, 0.010)),
        "swirl": random.choice([-1, 1]) * random.uniform(0.25, 0.70),
        "angle": random.random() * math.tau,
        "target_y": random.uniform(1.55, 2.30),
    })

    while len(smoke_wisps) > MAX_SMOKE_WISPS:
        old = smoke_wisps.pop(0)
        old["obj"].visible = False

def add_return_ember(pos):
    ember = sphere(
        pos=pos + vector(random.uniform(-0.035, 0.035), random.uniform(-0.01, 0.04), random.uniform(-0.035, 0.035)),
        radius=random.uniform(0.025, 0.055),
        color=vector(1.0, 0.62, 0.08),
        opacity=0.55,
        emissive=True
    )

    return_embers.append({
        "obj": ember,
        "age": 0.0,
        "life": random.uniform(1.2, 2.1),
        "drift": vector(random.uniform(-0.003, 0.003), random.uniform(0.002, 0.009), random.uniform(-0.003, 0.003)),
        "base_radius": ember.radius,
    })

    while len(return_embers) > MAX_RETURN_EMBERS:
        old = return_embers.pop(0)
        old["obj"].visible = False

def add_storage_mote():
    angle = random.random() * math.tau
    radius = random.uniform(0.06, 0.24)
    pos = flame_base.pos + vector(math.cos(angle) * radius, random.uniform(0.02, 0.16), math.sin(angle) * radius)
    mote = sphere(
        pos=pos,
        radius=random.uniform(0.014, 0.030),
        color=vector(1.0, 0.54, 0.07),
        opacity=0.35,
        emissive=True
    )
    storage_motes.append({
        "obj": mote,
        "age": 0.0,
        "life": random.uniform(1.4, 2.6),
        "angle": angle,
        "radius": radius,
        "spin": random.choice([-1, 1]) * random.uniform(0.35, 0.85),
        "base_y": pos.y,
    })

    while len(storage_motes) > MAX_STORAGE_MOTES:
        old = storage_motes.pop(0)
        old["obj"].visible = False

def add_loop_echo(pos):
    echo = ring(
        pos=pos,
        axis=vector(0, 1, 0),
        radius=random.uniform(0.08, 0.16),
        thickness=random.uniform(0.003, 0.007),
        color=vector(1.0, 0.52, 0.06),
        opacity=0.26,
        emissive=True
    )
    loop_echoes.append({
        "obj": echo,
        "age": 0.0,
        "life": random.uniform(0.75, 1.35),
        "grow": random.uniform(0.16, 0.32),
    })

    while len(loop_echoes) > MAX_LOOP_ECHOES:
        old = loop_echoes.pop(0)
        old["obj"].visible = False

def add_path_mote(path_index, angle):
    hp = heat_paths[path_index]
    pos = flame_base.pos + vector(
        math.cos(angle) * hp["target_radius"],
        hp["height"],
        math.sin(angle) * hp["target_radius"]
    )
    mote = sphere(
        pos=pos,
        radius=random.uniform(0.010, 0.022),
        color=vector(1.0, 0.48, 0.05),
        opacity=0.34,
        emissive=True
    )
    path_motes.append({
        "obj": mote,
        "age": 0.0,
        "life": random.uniform(0.9, 1.8),
        "path": path_index,
        "angle": angle,
        "spin": hp["spin"],
    })
    while len(path_motes) > MAX_PATH_MOTES:
        old = path_motes.pop(0)
        old["obj"].visible = False

def add_collapse_shards():
    for _ in range(9):
        angle = random.random() * math.tau
        shard = sphere(
            pos=unstable_ember.pos + vector(random.uniform(-0.04, 0.04), random.uniform(-0.02, 0.04), random.uniform(-0.04, 0.04)),
            radius=random.uniform(0.014, 0.030),
            color=vector(1.0, 0.30, 0.03),
            opacity=0.55,
            emissive=True
        )
        vel = vector(math.cos(angle) * random.uniform(0.12, 0.32), random.uniform(0.03, 0.20), math.sin(angle) * random.uniform(0.12, 0.32))
        collapse_shards.append({
            "obj": shard,
            "vel": vel,
            "age": 0.0,
            "life": random.uniform(0.65, 1.25),
        })

    while len(collapse_shards) > MAX_COLLAPSE_SHARDS:
        old = collapse_shards.pop(0)
        old["obj"].visible = False

def reinforce_heat_path(path_index, amount=0.055):
    global heat_path_memory, path_reinforce_count, path_guidance
    hp = heat_paths[path_index]
    hp["strength"] = clamp(hp["strength"] + amount, 0.0, 1.0)
    heat_path_memory = clamp(heat_path_memory + amount * 0.38, 0.0, 1.0)
    path_guidance = clamp(path_guidance + amount * 0.25, 0.0, 0.90)
    path_reinforce_count += 1
    add_path_mote(path_index, random.random() * math.tau)

def reward_returning_spark(p, from_loop=False):
    global returned_heat, return_reward_count, base_brighten, inward_pull, cycle_energy
    global loop_return_count, proto_core_persistence

    p["rewarded"] = True
    p["return_glow"] = 1.0

    smoke_bonus = 0.010 if p["slowed_by_smoke"] else 0.0
    return_reward_count += 1
    returned_heat = clamp(0.0 + returned_heat + 0.044 + (0.020 if from_loop else 0.0) + (0.012 if p["followed_path"] else 0.0) + smoke_bonus, 0.0, 1.0)
    base_brighten = clamp(base_brighten + 0.43, 0.0, 1.0)

    cycle_energy = clamp(cycle_energy + 0.035 + (0.018 if from_loop else 0.0) + smoke_bonus, 0.0, 1.0)
    inward_pull = clamp(inward_pull + 0.008, 0.02, 0.62)

    if from_loop:
        loop_return_count += 1
        proto_core_persistence = clamp(proto_core_persistence + 0.012, 0.0, 0.92)

    if p["followed_path"] or from_loop:
        reinforce_flame_band(0.014 + 0.010 * path_guidance)

    add_return_ember(p["obj"].pos)

def reinforce_core_synchrony(amount=0.020):
    """Core stability grows when bands, smoke, and returning sparks align."""
    global core_synchrony, stable_core_heat, core_stability_flash

    core_synchrony = clamp(core_synchrony + amount, 0.0, 1.0)
    stable_core_heat = clamp(stable_core_heat + amount * 0.55, 0.0, 1.0)
    core_stability_flash = clamp(core_stability_flash + amount * 2.0, 0.0, 1.0)

def reinforce_flame_band(amount=0.030):
    """Repeated heat-path following thickens broken flame bands."""
    global flame_band_memory, flame_band_strength, band_reinforce_count

    band_reinforce_count += 1
    reinforce_core_synchrony(0.006 + 0.006 * smoke_boundary_strength)
    flame_band_memory = clamp(flame_band_memory + amount * 0.65, 0.0, 1.0)
    flame_band_strength = clamp(flame_band_strength + amount, 0.0, 0.88)

    # Reinforce the band whose radius is closest to the active heat path layer.
    best = min(broken_flame_bands, key=lambda b: abs(b["strength"] - flame_band_strength))
    best["strength"] = clamp(best["strength"] + amount * 1.3, 0.0, 1.0)

def mark_partial_loop(p, path_index=None):
    global partial_loop_count, loop_strength, survival_flash, proto_core_persistence

    p["has_looped"] = True
    p["loop_glow"] = 1.0
    partial_loop_count += 1
    loop_strength = clamp(loop_strength + 0.018, 0.0, 0.80)
    survival_flash = clamp(survival_flash + 0.20, 0.0, 1.0)
    proto_core_persistence = clamp(proto_core_persistence + 0.006, 0.0, 0.92)
    add_loop_echo(p["obj"].pos)

    if path_index is not None:
        reinforce_heat_path(path_index, 0.058)
        reinforce_flame_band(0.020 + 0.018 * heat_path_memory)

def store_returned_heat_during_rest():
    global returned_heat, inner_ember_heat, stored_heat_events, base_brighten, last_rest_storage_tick
    global proto_core_persistence

    if cycle_phase != "rest":
        return
    if returned_heat <= 0.015:
        return
    if t - last_rest_storage_tick < 0.22:
        return

    efficiency = 1.0 + 0.55 * proto_core_persistence + 0.18 * heat_path_memory + 0.10 * smoke_boundary_strength
    amount = min((0.028 + 0.040 * returned_heat) * efficiency, returned_heat * 0.46)

    returned_heat = clamp(returned_heat - amount * 0.34, 0.0, 1.0)
    inner_ember_heat = clamp(inner_ember_heat + amount, 0.0, 0.96)
    base_brighten = clamp(base_brighten + amount * 3.4, 0.0, 1.0)
    stored_heat_events += 1
    last_rest_storage_tick = t

    add_storage_mote()

def evaluate_cycle_survival():
    global cycle_start_returns, cycle_start_storage, cycle_start_loops, cycle_start_path_follows, cycle_start_smoke_slows
    global last_cycle_return_count, last_cycle_store_count, last_cycle_loop_count, last_cycle_path_count, last_cycle_smoke_slow_count
    global proto_core_persistence, proto_core_survival_streak, proto_core_collapse_count
    global collapse_flash, survival_flash, inner_ember_heat, loop_strength, path_guidance, heat_path_memory
    global smoke_memory, smoke_boundary_strength
    global core_synchrony, stable_core_strength, stable_core_heat, stable_core_cycles, core_condense_events
    global core_stability_flash, manual_sync_boost
    global flame_band_memory, flame_band_strength, last_cycle_band_gain, cycle_start_band_reinforces, band_break_count
    global core_synchrony, stable_core_strength, stable_core_heat, stable_core_cycles, core_condense_events, core_stability_flash

    cycle_returns = return_reward_count - cycle_start_returns
    cycle_stores = stored_heat_events - cycle_start_storage
    cycle_loops = partial_loop_count - cycle_start_loops
    cycle_paths = path_follow_count - cycle_start_path_follows
    cycle_smoke_slows = smoke_slow_count - cycle_start_smoke_slows
    cycle_band_gain = band_reinforce_count - cycle_start_band_reinforces

    synchronized_cycle = (
        cycle_returns >= 1
        and cycle_smoke_slows >= 1
        and cycle_band_gain >= 1
        and flame_band_strength > 0.14
        and smoke_boundary_strength > 0.12
        and proto_core_persistence > 0.12
    )

    last_cycle_return_count = cycle_returns
    last_cycle_store_count = cycle_stores
    last_cycle_loop_count = cycle_loops
    last_cycle_path_count = cycle_paths
    last_cycle_smoke_slow_count = cycle_smoke_slows
    last_cycle_band_gain = cycle_band_gain

    survived = cycle_stores > 0 and (inner_ember_heat > 0.09 or cycle_returns > 0)
    loop_help = min(cycle_loops, 4) * 0.014
    path_help = min(cycle_paths, 5) * 0.010
    smoke_help = min(cycle_smoke_slows, 6) * 0.006
    band_help = min(cycle_band_gain, 5) * 0.008

    if survived:
        proto_core_survival_streak += 1
        gain = 0.034 + 0.022 * min(proto_core_survival_streak, 5) + 0.014 * min(cycle_stores, 4) + loop_help + path_help + smoke_help + band_help + band_help
        proto_core_persistence = clamp(proto_core_persistence + gain, 0.0, 0.92)
        survival_flash = 1.0
        inner_ember_heat = clamp(inner_ember_heat + 0.015 * proto_core_persistence + 0.008 * min(cycle_loops, 3), 0.0, 0.96)
    else:
        proto_core_survival_streak = 0
        loss = 0.078 + 0.052 * (1.0 - returned_heat)
        proto_core_persistence = clamp(proto_core_persistence - loss, 0.0, 0.92)
        loop_strength = clamp(loop_strength - 0.052, 0.0, 0.80)
        path_guidance = clamp(path_guidance - 0.052, 0.0, 0.90)
        heat_path_memory = clamp(heat_path_memory - 0.038, 0.0, 1.0)
        flame_band_memory = clamp(flame_band_memory - 0.050, 0.0, 1.0)
        flame_band_strength = clamp(flame_band_strength - 0.060, 0.0, 0.88)
        if cycle_band_gain <= 0 and flame_band_strength > 0.10:
            band_break_count += 1
        if inner_ember_heat > 0.06 or proto_core_persistence > 0.05:
            proto_core_collapse_count += 1
            collapse_flash = 1.0
            add_collapse_shards()
        inner_ember_heat = clamp(inner_ember_heat * (0.72 + 0.20 * stable_core_strength), 0.0, 0.96)

    # Smoke is not a perfect container. It thins after each cycle unless reinforced.
    smoke_memory = clamp(smoke_memory - 0.012 + 0.004 * min(cycle_smoke_slows, 4), 0.0, 1.0)
    smoke_boundary_strength = clamp(smoke_boundary_strength - 0.014 + 0.004 * min(cycle_smoke_slows, 5), 0.0, 0.86)

    # Stable core holds heat even when fewer sparks return.
    stable_core_heat = clamp(
        stable_core_heat
        + 0.012 * stable_core_strength
        - 0.010 * (1.0 - stable_core_strength) * (1.0 - min(cycle_returns, 1)),
        0.0,
        1.0
    )
    if stable_core_strength > 0.18:
        proto_core_persistence = clamp(proto_core_persistence + 0.010 * stable_core_strength, 0.0, 0.92)
        inner_ember_heat = clamp(inner_ember_heat + 0.010 * stable_core_heat, 0.0, 0.96)

    cycle_start_returns = return_reward_count
    cycle_start_storage = stored_heat_events
    cycle_start_loops = partial_loop_count
    cycle_start_path_follows = path_follow_count
    cycle_start_smoke_slows = smoke_slow_count
    cycle_start_band_reinforces = band_reinforce_count

def reset_all_evolving_state():
    global escape_noticing, escaped_spark_count, bent_spark_count
    global returned_heat, return_reward_count, base_brighten
    global inner_ember_heat, inner_ember_instability, stored_heat_events, ember_feed_boost, last_rest_storage_tick
    global proto_core_persistence, proto_core_survival_streak, proto_core_collapse_count
    global last_cycle_return_count, last_cycle_store_count, cycle_start_returns, cycle_start_storage
    global collapse_flash, survival_flash
    global loop_strength, manual_loop_boost, partial_loop_count, loop_return_count, loop_escape_count
    global last_cycle_loop_count, cycle_start_loops
    global heat_path_memory, path_guidance, manual_path_boost, path_follow_count, path_reinforce_count
    global last_cycle_path_count, cycle_start_path_follows
    global smoke_memory, smoke_boundary_strength
    global flame_band_memory, flame_band_strength, manual_band_boost
    global core_synchrony, stable_core_strength, stable_core_heat, stable_core_cycles, core_condense_events, core_stability_flash, manual_sync_boost, band_reinforce_count, last_cycle_band_gain, cycle_start_band_reinforces, band_break_count, manual_smoke_boost, smoke_wisp_count, smoke_slow_count
    global last_cycle_smoke_slow_count, cycle_start_smoke_slows

    escape_noticing = 0.0
    escaped_spark_count = 0
    bent_spark_count = 0
    returned_heat = 0.0
    return_reward_count = 0
    base_brighten = 0.0

    inner_ember_heat = 0.0
    inner_ember_instability = 1.0
    stored_heat_events = 0
    ember_feed_boost = 0.0
    last_rest_storage_tick = 0.0

    proto_core_persistence = 0.0
    proto_core_survival_streak = 0
    proto_core_collapse_count = 0
    last_cycle_return_count = 0
    last_cycle_store_count = 0
    cycle_start_returns = 0
    cycle_start_storage = 0
    collapse_flash = 0.0
    survival_flash = 0.0

    loop_strength = 0.0
    manual_loop_boost = 0.0
    partial_loop_count = 0
    loop_return_count = 0
    loop_escape_count = 0
    last_cycle_loop_count = 0
    cycle_start_loops = 0

    heat_path_memory = 0.0
    path_guidance = 0.0
    manual_path_boost = 0.0
    path_follow_count = 0
    path_reinforce_count = 0
    last_cycle_path_count = 0
    cycle_start_path_follows = 0

    smoke_memory = 0.0
    smoke_boundary_strength = 0.0
    manual_smoke_boost = 0.0
    smoke_wisp_count = 0
    smoke_slow_count = 0
    last_cycle_smoke_slow_count = 0
    cycle_start_smoke_slows = 0

    flame_band_memory = 0.0
    flame_band_strength = 0.0
    manual_band_boost = 0.0
    band_reinforce_count = 0
    band_break_count = 0
    last_cycle_band_gain = 0
    cycle_start_band_reinforces = 0

    core_synchrony = 0.0
    stable_core_strength = 0.0
    stable_core_heat = 0.0
    stable_core_cycles = 0
    core_condense_events = 0
    core_stability_flash = 0.0
    manual_sync_boost = 0.0

    for hp in heat_paths:
        hp["strength"] = 0.0
        hp["obj"].opacity = 0.0

    for band in broken_flame_bands:
        band["strength"] = 0.0
        band["obj"].opacity = 0.0

    for group in (memory_marks, return_embers, storage_motes, collapse_shards, loop_echoes, path_motes, smoke_wisps):
        for item in group:
            if "dot" in item:
                item["dot"].visible = False
            if "stroke" in item:
                item["stroke"].visible = False
            if "obj" in item:
                item["obj"].visible = False
        group.clear()

def reset_simulation():
    global t, will_to_become_star, breath, inward_pull, manual_pull_boost
    global cycle_time, cycle_number, cycle_phase, last_phase, cycle_energy

    t = 0.0
    will_to_become_star = 0.34
    breath = 0.0
    inward_pull = 0.15
    manual_pull_boost = 0.0

    cycle_time = 0.0
    cycle_number = 1
    cycle_phase = "rise"
    last_phase = "rise"
    cycle_energy = 0.30

    reset_all_evolving_state()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath, manual_pull_boost
    global cycle_time, cycle_energy, ember_feed_boost, inner_ember_heat, proto_core_persistence, survival_flash
    global manual_loop_boost, loop_strength, manual_path_boost, path_guidance, heat_path_memory
    global manual_smoke_boost, smoke_memory, smoke_boundary_strength
    global manual_band_boost, flame_band_memory, flame_band_strength
    global manual_sync_boost, core_synchrony, stable_core_heat, core_stability_flash

    k = evt.key.lower()

    if k == "p":
        paused = not paused
    elif k == "h":
        show_help = not show_help
        help_label.visible = show_help
    elif k == "r":
        reset_simulation()
    elif k == "w":
        will_to_become_star = clamp(will_to_become_star + 0.06, 0.0, 1.0)
    elif k == " ":
        breath = 1.0
    elif k == "i":
        manual_pull_boost = 0.35
    elif k == "c":
        cycle_time = min(cycle_time + 1.15, cycle_duration - 0.1)
        cycle_energy = clamp(cycle_energy + 0.08, 0.0, 1.0)
    elif k == "e":
        ember_feed_boost = 0.45
        inner_ember_heat = clamp(inner_ember_heat + 0.08, 0.0, 0.96)
        proto_core_persistence = clamp(proto_core_persistence + 0.025, 0.0, 0.92)
        survival_flash = 0.75
    elif k == "o":
        manual_loop_boost = 0.45
        loop_strength = clamp(loop_strength + 0.08, 0.0, 0.80)
    elif k == "g":
        manual_path_boost = 0.45
        path_guidance = clamp(path_guidance + 0.10, 0.0, 0.90)
        heat_path_memory = clamp(heat_path_memory + 0.06, 0.0, 1.0)
        for idx in range(len(heat_paths)):
            reinforce_heat_path(idx, 0.018)
    elif k == "s":
        manual_smoke_boost = 0.45
        smoke_memory = clamp(smoke_memory + 0.10, 0.0, 1.0)
        smoke_boundary_strength = clamp(smoke_boundary_strength + 0.12, 0.0, 0.86)
        for _ in range(8):
            add_smoke_wisp(vector(random.uniform(-0.65, 0.65), random.uniform(1.65, 2.25), random.uniform(-0.65, 0.65)), from_slow=True)
    elif k == "b":
        manual_band_boost = 0.45
        flame_band_memory = clamp(flame_band_memory + 0.08, 0.0, 1.0)
        flame_band_strength = clamp(flame_band_strength + 0.10, 0.0, 0.88)
        for _ in range(4):
            reinforce_flame_band(0.020)
    elif k == "x":
        manual_sync_boost = 0.45
        core_synchrony = clamp(core_synchrony + 0.10, 0.0, 1.0)
        stable_core_heat = clamp(stable_core_heat + 0.08, 0.0, 1.0)
        core_stability_flash = 1.0

scene.bind("keydown", keydown)

def update_cycle():
    global cycle_time, cycle_number, cycle_phase, last_phase
    global rise_drive, pull_drive, receive_drive, rest_drive, cycle_energy, base_brighten

    cycle_time += dt
    progress = cycle_time / cycle_duration

    if progress >= 1.0:
        evaluate_cycle_survival()
        cycle_time = 0.0
        cycle_number += 1
        cycle_energy = clamp(
            cycle_energy * 0.65
            + returned_heat * 0.18
            + inner_ember_heat * 0.10
            + proto_core_persistence * 0.07
            + loop_strength * 0.04
            + heat_path_memory * 0.035
            + smoke_boundary_strength * 0.025
            + flame_band_strength * 0.025
            + will_to_become_star * 0.05,
            0.05,
            1.0
        )
        progress = 0.0

    if progress < 0.28:
        cycle_phase = "rise"
    elif progress < 0.58:
        cycle_phase = "pull"
    elif progress < 0.78:
        cycle_phase = "receive"
    else:
        cycle_phase = "rest"

    rise_drive = 0.0
    pull_drive = 0.0
    receive_drive = 0.0
    rest_drive = 0.0

    if cycle_phase == "rise":
        local = progress / 0.28
        rise_drive = math.sin(local * math.pi)
    elif cycle_phase == "pull":
        local = (progress - 0.28) / 0.30
        pull_drive = math.sin(local * math.pi)
    elif cycle_phase == "receive":
        local = (progress - 0.58) / 0.20
        receive_drive = math.sin(local * math.pi)
    else:
        local = (progress - 0.78) / 0.22
        rest_drive = math.sin(local * math.pi)

    if cycle_phase != last_phase:
        if cycle_phase == "rise":
            base_brighten = clamp(base_brighten + 0.08 + 0.07 * inner_ember_heat + 0.05 * proto_core_persistence, 0.0, 1.0)
        elif cycle_phase == "pull":
            base_brighten = clamp(base_brighten + 0.07 + 0.05 * heat_path_memory, 0.0, 1.0)
        elif cycle_phase == "receive":
            base_brighten = clamp(base_brighten + 0.14 + 0.04 * path_guidance + 0.04 * smoke_boundary_strength, 0.0, 1.0)
        elif cycle_phase == "rest":
            base_brighten = clamp(base_brighten + 0.10 + 0.18 * returned_heat + 0.08 * proto_core_persistence, 0.0, 1.0)
        last_phase = cycle_phase

def update_learning_state():
    global inward_pull, manual_pull_boost, escape_noticing, returned_heat
    global base_brighten, cycle_energy, inner_ember_heat, inner_ember_instability, ember_feed_boost
    global proto_core_persistence, collapse_flash, survival_flash, loop_strength, manual_loop_boost
    global heat_path_memory, path_guidance, manual_path_boost
    global smoke_memory, smoke_boundary_strength
    global flame_band_memory, flame_band_strength, manual_band_boost, last_cycle_band_gain, cycle_start_band_reinforces, band_break_count, manual_smoke_boost
    global core_synchrony, stable_core_strength, stable_core_heat, core_stability_flash, manual_sync_boost

    target_pull = (
        0.05
        + 0.10 * escape_noticing
        + 0.08 * will_to_become_star
        + 0.10 * returned_heat
        + 0.08 * inner_ember_heat
        + 0.12 * proto_core_persistence
        + 0.05 * loop_strength
        + 0.06 * heat_path_memory
        + 0.05 * smoke_boundary_strength
        + 0.06 * flame_band_strength
        + 0.10 * stable_core_strength
        + 0.22 * pull_drive
        + manual_pull_boost
    )
    inward_pull += (target_pull - inward_pull) * 0.020
    inward_pull = clamp(inward_pull, 0.02, 0.62)

    target_loop = (
        0.02
        + 0.10 * inner_ember_heat
        + 0.27 * proto_core_persistence
        + 0.14 * heat_path_memory
        + 0.08 * smoke_boundary_strength
        + 0.10 * flame_band_strength
        + 0.10 * stable_core_strength
        + 0.12 * pull_drive
        + 0.08 * receive_drive
        + manual_loop_boost
    )
    loop_strength += (target_loop - loop_strength) * 0.018
    loop_strength = clamp(loop_strength, 0.0, 0.80)

    target_guidance = (
        0.04 * loop_strength
        + 0.10 * proto_core_persistence
        + 0.54 * heat_path_memory
        + 0.06 * smoke_boundary_strength
        + 0.14 * flame_band_memory
        + 0.10 * pull_drive
        + 0.08 * receive_drive
        + manual_path_boost
    )
    path_guidance += (target_guidance - path_guidance) * 0.016
    path_guidance = clamp(path_guidance, 0.0, 0.90)

    target_smoke = (
        0.04
        + 0.50 * smoke_memory
        + 0.10 * escape_noticing
        + 0.04 * heat_path_memory
        + manual_smoke_boost
    )
    smoke_boundary_strength += (target_smoke - smoke_boundary_strength) * 0.012
    smoke_boundary_strength = clamp(smoke_boundary_strength, 0.0, 0.86)

    target_band = (
        0.03 * proto_core_persistence
        + 0.18 * heat_path_memory
        + 0.14 * path_guidance
        + 0.08 * loop_strength
        + 0.05 * smoke_boundary_strength
        + manual_band_boost
    )
    flame_band_strength += (target_band - flame_band_strength) * 0.012
    flame_band_strength = clamp(flame_band_strength, 0.0, 0.88)

    sync_target = (
        0.18 * flame_band_strength
        + 0.16 * smoke_boundary_strength
        + 0.16 * returned_heat
        + 0.12 * proto_core_persistence
        + 0.10 * heat_path_memory
        + manual_sync_boost
    )
    core_synchrony += (sync_target - core_synchrony) * 0.010
    core_synchrony = clamp(core_synchrony, 0.0, 1.0)

    stable_target = max(0.0, core_synchrony - 0.58) * 1.45 + stable_core_heat * 0.12
    stable_core_strength += (stable_target - stable_core_strength) * 0.006
    stable_core_strength = clamp(stable_core_strength, 0.0, 0.95)

    manual_pull_boost *= 0.94
    manual_loop_boost *= 0.93
    manual_path_boost *= 0.92
    manual_smoke_boost *= 0.92
    manual_band_boost *= 0.92
    manual_sync_boost *= 0.92
    core_stability_flash *= 0.90
    ember_feed_boost *= 0.93
    collapse_flash *= 0.90
    survival_flash *= 0.91

    escape_noticing = clamp(escape_noticing - 0.00022, 0.0, 1.0)
    returned_heat = clamp(returned_heat - 0.00016, 0.0, 1.0)
    base_brighten = clamp(base_brighten * 0.945, 0.0, 1.0)
    smoke_memory = clamp(smoke_memory - 0.00020, 0.0, 1.0)
    rhythm_loss = 0.00034 * (1.0 + rest_drive + max(0.0, 0.30 - cycle_energy))
    flame_band_memory = clamp(flame_band_memory - rhythm_loss, 0.0, 1.0)
    flame_band_strength = clamp(flame_band_strength - rhythm_loss * 0.85, 0.0, 0.88)

    total_path = 0.0
    for hp in heat_paths:
        hp["strength"] = clamp(hp["strength"] - 0.00040 * (1.0 + 0.30 * rise_drive), 0.0, 1.0)
        total_path += hp["strength"]
    heat_path_memory = clamp(total_path / len(heat_paths), 0.0, 1.0)

    store_returned_heat_during_rest()

    persistence_protection = 1.0 - 0.48 * proto_core_persistence - 0.30 * stable_core_strength
    loss = (0.00062 + 0.00072 * (1.0 - returned_heat) + 0.00045 * rise_drive) * persistence_protection
    if cycle_phase == "rest":
        loss *= 0.58
    if cycle_phase == "receive" and returned_heat > 0.02:
        loss *= 0.72

    inner_ember_heat = clamp(inner_ember_heat + 0.0020 * ember_feed_boost - loss, 0.0, 0.96)

    if cycle_phase != "rest":
        proto_core_persistence = clamp(proto_core_persistence - 0.000090 * (1.0 - inner_ember_heat), 0.0, 0.92)

    inner_ember_instability = clamp(
        1.0
        - inner_ember_heat * 0.44
        - proto_core_persistence * 0.38
        - loop_strength * 0.10
        - heat_path_memory * 0.10
        - smoke_boundary_strength * 0.08
        - flame_band_strength * 0.08
        - stable_core_strength * 0.16
        + 0.12 * math.sin(t * 3.7),
        0.18,
        1.0
    )

    stable_core_heat = clamp(stable_core_heat + 0.00055 * stable_core_strength - 0.00018 * (1.0 - core_synchrony), 0.0, 1.0)

    if cycle_phase == "rest":
        cycle_energy = clamp(
            cycle_energy
            + 0.00036 * returned_heat
            + 0.00024 * inner_ember_heat
            + 0.00018 * proto_core_persistence
            + 0.00012 * heat_path_memory
            + 0.00008 * smoke_boundary_strength
            - 0.00014,
            0.0,
            1.0
        )

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    proto_pulse = 0.5 + 0.5 * math.sin(t * (3.4 + 5.0 * inner_ember_instability))
    ember_pulse = 0.5 + 0.5 * math.sin(t * (4.0 + 7.0 * inner_ember_instability))

    collapse_jitter = random.uniform(-0.048, 0.048) * inner_ember_instability * (inner_ember_heat + 0.20 * proto_core_persistence)
    notice_tremble = 0.014 * escape_noticing * math.sin(t * 14.0)

    heat_pulse = base_brighten
    cycle_expand = 0.10 * rise_drive - 0.06 * rest_drive
    cycle_contract = 0.08 * pull_drive
    core_effect = inner_ember_heat * 0.58 + proto_core_persistence * 0.68

    height = (
        0.56
        + 0.15 * flicker
        + 0.13 * will_to_become_star
        + 0.16 * breath
        + 0.07 * heat_pulse
        + 0.13 * core_effect
        + 0.16 * rise_drive
        - 0.065 * rest_drive
    )
    width = (
        0.21
        + 0.030 * math.sin(t * 7.0)
        - 0.022 * inward_pull
        + 0.025 * heat_pulse
        + 0.041 * core_effect
        + cycle_expand
        - cycle_contract
    )

    flame_base.radius = (
        0.16
        + 0.04 * flicker
        + 0.015 * inward_pull
        + 0.066 * heat_pulse
        + 0.066 * inner_ember_heat
        + 0.062 * proto_core_persistence
        + 0.020 * heat_path_memory
        + 0.015 * smoke_boundary_strength
        + 0.030 * receive_drive
    )
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble + collapse_jitter,
        0.17,
        0.025 * math.cos(t * 4.4) - collapse_jitter * 0.4
    )
    flame_base.color = vector(
        1.0,
        clamp(0.24 + 0.12 * will_to_become_star + 0.10 * inward_pull + 0.32 * heat_pulse + 0.25 * inner_ember_heat + 0.23 * proto_core_persistence + 0.08 * heat_path_memory, 0.0, 1.0),
        clamp(0.03 + 0.13 * heat_pulse + 0.10 * inner_ember_heat + 0.10 * proto_core_persistence, 0.0, 1.0)
    )

    base_heat_glow.pos = flame_base.pos + vector(0, 0.02, 0)
    base_heat_glow.radius = 0.21 + 0.29 * heat_pulse + 0.08 * returned_heat + 0.11 * inner_ember_heat + 0.14 * proto_core_persistence + 0.05 * loop_strength + 0.05 * heat_path_memory + 0.04 * smoke_boundary_strength + 0.08 * receive_drive
    base_heat_glow.opacity = clamp(
        0.05 + 0.34 * heat_pulse + 0.09 * returned_heat + 0.18 * inner_ember_heat + 0.19 * proto_core_persistence + 0.06 * loop_strength + 0.06 * heat_path_memory + 0.04 * smoke_boundary_strength + 0.12 * receive_drive,
        0.04,
        0.86
    )
    base_heat_glow.color = vector(1.0, 0.45 + 0.25 * heat_pulse + 0.17 * inner_ember_heat + 0.15 * proto_core_persistence + 0.07 * heat_path_memory, 0.05 + 0.10 * heat_pulse)

    core_pos = flame_base.pos + vector(0, 0.065 + 0.012 * ember_pulse, 0)
    unstable_ember.pos = core_pos
    unstable_ember.radius = 0.045 + 0.14 * inner_ember_heat + 0.074 * proto_core_persistence + 0.020 * loop_strength + 0.018 * heat_path_memory + 0.012 * smoke_boundary_strength + 0.030 * proto_pulse * core_effect
    unstable_ember.opacity = clamp(0.08 + 0.57 * inner_ember_heat + 0.45 * proto_core_persistence + 0.09 * loop_strength + 0.08 * heat_path_memory + 0.05 * smoke_boundary_strength + 0.08 * proto_pulse - 0.20 * collapse_flash, 0.05, 0.92)
    unstable_ember.color = vector(
        1.0,
        clamp(0.40 + 0.34 * inner_ember_heat + 0.30 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.10 * proto_pulse, 0.0, 1.0),
        clamp(0.05 + 0.18 * inner_ember_heat + 0.18 * proto_core_persistence + 0.04 * loop_strength, 0.0, 1.0)
    )

    proto_core_shell.pos = core_pos
    proto_core_shell.radius = (
        0.10
        + 0.25 * proto_core_persistence
        + 0.10 * inner_ember_heat
        + 0.05 * loop_strength
        + 0.05 * heat_path_memory
        + 0.03 * smoke_boundary_strength
        + 0.04 * flame_band_strength + 0.06 * stable_core_strength
        + 0.03 * proto_pulse
    )
    proto_core_shell.opacity = clamp(
        0.02 + 0.37 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory
        + 0.04 * smoke_boundary_strength + 0.12 * survival_flash + 0.12 * stable_core_strength
        - 0.12 * collapse_flash,
        0.015,
        0.65
    )

    # Stable core appears as a steady glow that survives weak return cycles.
    stable_core.pos = core_pos
    stable_core.radius = 0.055 + 0.23 * stable_core_strength + 0.055 * stable_core_heat + 0.018 * core_stability_flash
    stable_core.opacity = clamp(0.02 + 0.82 * stable_core_strength + 0.18 * stable_core_heat + 0.10 * core_stability_flash, 0.0, 0.96)
    stable_core.color = vector(
        1.0,
        clamp(0.54 + 0.36 * stable_core_strength + 0.16 * stable_core_heat, 0.0, 1.0),
        clamp(0.08 + 0.26 * stable_core_strength + 0.10 * stable_core_heat, 0.0, 1.0)
    )
    stable_core_halo.pos = core_pos
    stable_core_halo.radius = 0.18 + 0.58 * stable_core_strength + 0.12 * stable_core_heat
    stable_core_halo.opacity = clamp(0.02 + 0.30 * stable_core_strength + 0.08 * stable_core_heat + 0.12 * core_stability_flash, 0.0, 0.42)
    stable_core_halo.color = vector(1.0, 0.52 + 0.28 * stable_core_strength, 0.07 + 0.12 * stable_core_strength)

    ember_pulse_ring.pos = unstable_ember.pos
    ember_pulse_ring.radius = 0.14 + 0.33 * inner_ember_heat + 0.19 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.04 * smoke_boundary_strength + 0.05 * ember_pulse
    ember_pulse_ring.thickness = 0.004 + 0.016 * inner_ember_heat + 0.010 * proto_core_persistence + 0.004 * loop_strength + 0.003 * heat_path_memory
    ember_pulse_ring.opacity = clamp(0.04 + 0.30 * inner_ember_heat * ember_pulse + 0.24 * proto_core_persistence + 0.11 * loop_strength + 0.10 * heat_path_memory + 0.05 * smoke_boundary_strength + 0.10 * survival_flash, 0.02, 0.55)

    survival_ring.pos = unstable_ember.pos
    survival_ring.radius = 0.22 + 0.43 * proto_core_persistence + 0.06 * loop_strength + 0.05 * heat_path_memory + 0.04 * smoke_boundary_strength + 0.05 * math.sin(t * 2.8)
    survival_ring.thickness = 0.004 + 0.020 * proto_core_persistence + 0.004 * loop_strength + 0.003 * heat_path_memory
    survival_ring.opacity = clamp(0.02 + 0.32 * proto_core_persistence + 0.07 * loop_strength + 0.06 * heat_path_memory + 0.04 * smoke_boundary_strength + 0.20 * survival_flash - 0.14 * collapse_flash, 0.01, 0.48)

    loop_guide_ring.pos = flame_base.pos + vector(0, 0.45 + 0.08 * math.sin(t * 2.0), 0)
    loop_guide_ring.radius = 0.48 + 0.34 * loop_strength + 0.08 * heat_path_memory + 0.05 * smoke_boundary_strength + 0.10 * math.sin(t * 2.4)
    loop_guide_ring.thickness = 0.004 + 0.016 * loop_strength + 0.006 * heat_path_memory
    loop_guide_ring.opacity = clamp(0.02 + 0.33 * loop_strength + 0.15 * heat_path_memory + 0.05 * smoke_boundary_strength + 0.08 * pull_drive, 0.01, 0.44)

    smoke_boundary_ring.pos = flame_base.pos + vector(0, 1.65 + 0.25 * smoke_boundary_strength + 0.05 * math.sin(t * 1.4), 0)
    smoke_boundary_ring.radius = 0.78 + 0.62 * smoke_boundary_strength + 0.10 * math.sin(t * 1.7)
    smoke_boundary_ring.thickness = 0.010 + 0.052 * smoke_boundary_strength
    smoke_boundary_ring.opacity = clamp(0.015 + 0.30 * smoke_boundary_strength, 0.01, 0.34)
    smoke_boundary_ring.color = vector(0.48 + 0.12 * smoke_boundary_strength, 0.50 + 0.10 * smoke_boundary_strength, 0.50 + 0.08 * smoke_boundary_strength)

    smoke_boundary_haze.pos = smoke_boundary_ring.pos + vector(0, -0.06, 0)
    smoke_boundary_haze.radius = 0.72 + 0.76 * smoke_boundary_strength
    smoke_boundary_haze.opacity = clamp(0.010 + 0.105 * smoke_boundary_strength, 0.008, 0.13)
    smoke_boundary_haze.color = vector(0.60, 0.61, 0.60)

    # Broken flame bands thicken from repeated path use, rotate, and remain uneven.
    for idx, band in enumerate(broken_flame_bands):
        obj = band["obj"]
        band["break_phase"] += band["spin"] * dt * (0.55 + flame_band_strength)
        # Individual band strengths follow global memory but lag/fade separately.
        desired = clamp(flame_band_strength * (0.65 + 0.12 * idx) + flame_band_memory * 0.20 + stable_core_strength * 0.18, 0.0, 1.0)
        band["strength"] += (desired - band["strength"]) * 0.018
        band["strength"] = clamp(band["strength"] - 0.00022 * (1.0 + rest_drive), 0.0, 1.0)

        brokenness = 0.45 + 0.55 * abs(math.sin(band["break_phase"] + idx * 1.7))
        obj.pos = flame_base.pos + vector(0, band["height"] + 0.035 * math.sin(t * 1.5 + idx), 0)
        obj.radius = band["radius"] + 0.050 * math.sin(t * 2.2 + idx)
        obj.thickness = 0.003 + 0.045 * band["strength"] * brokenness
        obj.opacity = clamp(0.02 + 0.48 * band["strength"] * brokenness - 0.10 * collapse_flash, 0.0, 0.58)
        obj.axis = norm(rotate(obj.axis, angle=0.022 * band["spin"] * (0.4 + band["strength"]), axis=vector(0, 1, 0)))
        obj.color = vector(1.0, clamp(0.30 + 0.46 * band["strength"] + 0.08 * idx, 0, 1), 0.035 + 0.12 * band["strength"])

    for idx, hp in enumerate(heat_paths):
        obj = hp["obj"]
        hp["phase"] += hp["spin"] * dt
        obj.pos = flame_base.pos + vector(0, hp["height"] + 0.025 * math.sin(t * 2.0 + idx), 0)
        obj.radius = hp["target_radius"] + 0.025 * math.sin(t * 2.5 + idx)
        obj.thickness = 0.0025 + 0.018 * hp["strength"]
        obj.opacity = clamp(0.015 + 0.34 * hp["strength"] + 0.035 * path_guidance, 0.0, 0.42)
        obj.axis = norm(rotate(obj.axis, angle=0.010 * hp["spin"], axis=vector(0, 1, 0)))
        obj.color = vector(1.0, clamp(0.38 + 0.42 * hp["strength"], 0, 1), 0.04 + 0.08 * hp["strength"])

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = clamp(width, 0.12, 0.34)

    inner_flame.pos = flame_base.pos + vector(0, 0.12, 0)
    inner_flame.axis = vector(
        0.025 * math.sin(t * 8.0) + notice_tremble * 0.5,
        height * 0.68,
        0.025 * math.cos(t * 7.5)
    )
    inner_flame.radius = flame_tip.radius * 0.48

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)

    desired_star.opacity = 0.13 + 0.17 * will_to_become_star + 0.05 * slow_pulse + 0.03 * cycle_energy + 0.03 * proto_core_persistence + 0.02 * heat_path_memory
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse + 0.02 * proto_core_persistence

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.20 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.005 * escape_noticing

    inward_field_ring.pos = vector(0, 0.78 + 0.04 * math.sin(t * 2.0), 0)
    inward_field_ring.radius = 0.62 + 0.13 * math.sin(t * 3.0) - 0.10 * pull_drive - 0.05 * core_effect
    inward_field_ring.thickness = 0.006 + 0.020 * inward_pull + 0.010 * pull_drive + 0.006 * proto_core_persistence
    inward_field_ring.opacity = (
        0.04 + 0.15 * inward_pull + 0.10 * pull_drive + 0.05 * returned_heat
        + 0.08 * proto_core_persistence + 0.04 * heat_path_memory
        + 0.03 * smoke_boundary_strength + 0.04 * flame_band_strength
    )

    cycle_halo.pos = vector(0, 0.31 + 0.03 * math.sin(t * 2.5), 0)
    cycle_halo.radius = 0.42 + 0.26 * rise_drive - 0.10 * pull_drive + 0.10 * receive_drive - 0.04 * rest_drive
    cycle_halo.opacity = (
        0.08 + 0.15 * cycle_energy + 0.12 * max(rise_drive, pull_drive, receive_drive)
        + 0.06 * proto_core_persistence + 0.04 * heat_path_memory
        + 0.03 * smoke_boundary_strength + 0.04 * flame_band_strength
    )

    breath *= 0.94

def update_sparks():
    global bent_spark_count, loop_escape_count, path_follow_count, smoke_slow_count

    flame_center = flame_base.pos + vector(0, 0.35, 0)
    reward_zone_center = flame_base.pos + vector(0, 0.28, 0)
    loop_center = unstable_ember.pos + vector(0, 0.20, 0)

    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        rel_loop = obj.pos - loop_center
        flat_dist = mag(vector(rel_loop.x, 0, rel_loop.z)) + 0.001
        current_angle = math.atan2(rel_loop.z, rel_loop.x)
        angle_step = signed_angle_step(p["last_angle"], current_angle)
        p["last_angle"] = current_angle

        if abs(angle_step) < 1.2:
            p["angle_travel"] += abs(angle_step)

        upward_lift = vector(
            0,
            0.10 * will_to_become_star + 0.24 * rise_drive + 0.04 * cycle_energy + 0.030 * inner_ember_heat + 0.020 * proto_core_persistence + 0.030 * stable_core_strength,
            0
        )

        # Smoke boundary slows upward-moving sparks before they disappear.
        smoke_rel = obj.pos - smoke_boundary_ring.pos
        smoke_flat = mag(vector(smoke_rel.x, 0, smoke_rel.z))
        in_smoke_height = -0.42 < smoke_rel.y < 0.44
        in_smoke_radius = smoke_flat < smoke_boundary_ring.radius + 0.35
        if smoke_boundary_strength > 0.05 and in_smoke_height and in_smoke_radius and p["vel"].y > 0.05:
            slow_amount = (0.008 + 0.040 * smoke_boundary_strength) * (1.0 + 0.4 * max(0, smoke_rel.y))
            p["vel"].y -= slow_amount
            p["vel"] += -safe_norm(vector(smoke_rel.x, 0, smoke_rel.z)) * 0.012 * smoke_boundary_strength
            p["smoke_slow_glow"] = clamp(p["smoke_slow_glow"] + 0.070, 0.0, 1.0)
            if not p["slowed_by_smoke"]:
                p["slowed_by_smoke"] = True
                smoke_slow_count += 1
                # Slowing a spark also creates a tiny wisp: the boundary learns from contact.
                if random.random() < 0.36:
                    add_smoke_wisp(obj.pos, from_slow=True)

        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.24

        if p["bendable"] and pull_zone:
            pull_strength = (
                inward_pull
                * (0.25 + 0.32 * escape_noticing + 0.24 * returned_heat + 0.18 * inner_ember_heat + 0.24 * proto_core_persistence + 0.10 * heat_path_memory + 0.08 * smoke_boundary_strength + 0.10 * flame_band_strength + 0.14 * stable_core_strength + 1.00 * pull_drive)
                / (0.75 + distance)
            )
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.031 * inward_pull * (escape_noticing + returned_heat + pull_drive + 0.5 * inner_ember_heat + 0.6 * proto_core_persistence + 0.30 * smoke_boundary_strength), 0)
            p["vel"] += (inward_force + downward_memory) * dt

            if p["vel"].y < 0.25 and not p["has_bent"]:
                bent_spark_count += 1
                p["has_bent"] = True
                p["return_glow"] = 0.72

        hp, hp_score = nearest_heat_path(rel_loop)
        path_index = heat_paths.index(hp)
        path_zone = (
            p["loopable"]
            and path_guidance > 0.06
            and hp["strength"] > 0.04
            and hp_score < 0.34
            and 0.26 < obj.pos.y < 1.75
        )

        if path_zone:
            tangent = tangent_around_y(rel_loop)
            radial_error = flat_dist - hp["target_radius"]
            vertical_error = rel_loop.y - hp["height"]

            radial_force = -safe_norm(vector(rel_loop.x, 0, rel_loop.z)) * radial_error * (0.12 + 0.38 * hp["strength"] + 0.22 * path_guidance)
            vertical_force = vector(0, -vertical_error * (0.05 + 0.20 * hp["strength"]), 0)
            guided_drive = 0.18 + 0.85 * hp["strength"] + 0.54 * path_guidance + 0.22 * loop_strength

            p["vel"] += (tangent * guided_drive + radial_force + vertical_force) * dt
            p["path_glow"] = clamp(p["path_glow"] + 0.045, 0.0, 1.0)
            p["loop_glow"] = clamp(p["loop_glow"] + 0.025, 0.0, 1.0)

            if not p["followed_path"]:
                p["followed_path"] = True
                path_follow_count += 1
                reinforce_heat_path(path_index, 0.018)

        loop_zone = (
            p["loopable"]
            and (0.30 < obj.pos.y < 1.74)
            and (0.18 < flat_dist < 1.23)
            and proto_core_persistence > 0.05
        )
        if loop_zone:
            tangent = tangent_around_y(rel_loop)
            radial_target = 0.54 + 0.24 * (1.0 - proto_core_persistence)
            radial_error = flat_dist - radial_target
            radial_force = -safe_norm(vector(rel_loop.x, 0, rel_loop.z)) * radial_error * (0.07 + 0.21 * loop_strength + 0.18 * heat_path_memory)

            loop_drive = (
                0.18
                + 0.84 * loop_strength
                + 0.38 * proto_core_persistence
                + 0.18 * heat_path_memory
                + 0.10 * smoke_boundary_strength
                + 0.18 * flame_band_strength
                + 0.20 * stable_core_strength
                + 0.22 * pull_drive
                + 0.20 * receive_drive
            )
            vertical_hold = vector(0, -0.08 * max(0.0, obj.pos.y - 0.95), 0)
            p["vel"] += (tangent * loop_drive + radial_force + vertical_hold) * dt
            p["loop_time"] += dt
            p["loop_glow"] = clamp(p["loop_glow"] + 0.032, 0.0, 1.0)

            if not p["has_looped"] and (p["angle_travel"] > math.pi * 1.25 or p["loop_time"] > 1.10):
                mark_partial_loop(p, path_index=path_index)

        # Broken flame bands add a broader rotating push, but not enough for stable orbit.
        if flame_band_strength > 0.06 and 0.42 < obj.pos.y < 1.55 and 0.22 < flat_dist < 1.35:
            band_tangent = tangent_around_y(rel_loop)
            band_pull = -safe_norm(vector(rel_loop.x, 0, rel_loop.z)) * 0.018 * flame_band_strength
            p["vel"] += (band_tangent * (0.22 + 0.70 * flame_band_strength) + band_pull) * dt
            p["loop_glow"] = clamp(p["loop_glow"] + 0.020 * flame_band_strength, 0.0, 1.0)

        return_distance = mag(obj.pos - reward_zone_center)
        reward_radius = 0.39 + 0.12 * receive_drive + 0.05 * inner_ember_heat + 0.07 * proto_core_persistence + 0.04 * loop_strength + 0.04 * heat_path_memory + 0.03 * smoke_boundary_strength
        + 0.04 * flame_band_strength
        if p["has_bent"] and not p["rewarded"] and return_distance < reward_radius and obj.pos.y < 0.95:
            reward_returning_spark(p, from_loop=p["has_looped"])

        p["vel"] += upward_lift * dt
        p["vel"] += vector(
            random.uniform(-0.014, 0.014),
            random.uniform(-0.004, 0.016),
            random.uniform(-0.014, 0.014)
        )
        p["vel"] *= 0.985 - 0.014 * rest_drive

        obj.pos += p["vel"] * dt
        p["return_glow"] *= 0.94
        p["loop_glow"] *= 0.965
        p["path_glow"] *= 0.970
        p["smoke_slow_glow"] *= 0.94

        core_glow = 0.5 * inner_ember_heat + 0.7 * proto_core_persistence + 0.35 * loop_strength + 0.30 * heat_path_memory
        age_fade = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)
        obj.opacity = clamp(age_fade + 0.21 * p["return_glow"] + 0.13 * p["loop_glow"] + 0.16 * p["path_glow"] + 0.15 * p["smoke_slow_glow"] + 0.08 * rise_drive + 0.030 * core_glow, 0.0, 1.0)
        obj.radius = clamp(0.016 + 0.018 * p["return_glow"] + 0.011 * p["loop_glow"] + 0.010 * p["path_glow"] + 0.008 * p["smoke_slow_glow"] + 0.006 * rise_drive + 0.004 * core_glow, 0.012, 0.070)

        if p["loop_glow"] > 0.10 or p["path_glow"] > 0.10 or p["smoke_slow_glow"] > 0.18 or p["has_looped"]:
            p["trail"].append(pos=obj.pos)
            p["trail"].color = vector(
                1.0,
                clamp(0.38 + 0.30 * p["loop_glow"] + 0.28 * p["path_glow"] + 0.10 * p["smoke_slow_glow"], 0, 1),
                0.05
            )
            p["trail"].radius = 0.004 + 0.004 * p["loop_glow"] + 0.004 * p["path_glow"]
            if p["trail"].npoints > 30:
                p["trail"].pop(0)

        escaped_high = obj.pos.y > 2.22
        burned_out_high = p["age"] > p["life"] and obj.pos.y > 1.05

        if escaped_high or burned_out_high:
            if p["has_looped"]:
                loop_escape_count += 1
            add_memory_mark(vector(obj.pos.x, obj.pos.y, obj.pos.z))
            add_smoke_wisp(vector(obj.pos.x, obj.pos.y, obj.pos.z))
            reset_spark(p)
        elif p["age"] > p["life"]:
            reset_spark(p)

def update_smoke_wisps():
    to_remove = []
    for w in smoke_wisps:
        w["age"] += dt
        frac = w["age"] / w["life"]

        rel = w["obj"].pos - flame_base.pos
        w["angle"] += w["swirl"] * dt * (0.35 + smoke_boundary_strength)
        target_radius = clamp(0.60 + 0.52 * smoke_boundary_strength + 0.06 * math.sin(t + w["angle"]), 0.45, 1.35)

        current_flat = vector(rel.x, 0, rel.z)
        if mag(current_flat) > 0.001:
            radial_target_pos = flame_base.pos + norm(current_flat) * target_radius + vector(0, w["target_y"], 0)
        else:
            radial_target_pos = flame_base.pos + vector(math.cos(w["angle"]) * target_radius, w["target_y"], math.sin(w["angle"]) * target_radius)

        gather_force = (radial_target_pos - w["obj"].pos) * (0.003 + 0.006 * smoke_boundary_strength)
        swirl_force = tangent_around_y(w["obj"].pos - flame_base.pos) * 0.006 * smoke_boundary_strength
        w["obj"].pos += w["drift"] + gather_force + swirl_force

        w["obj"].radius = clamp(0.045 + 0.20 * frac + 0.10 * smoke_boundary_strength, 0.04, 0.36)
        w["obj"].opacity = clamp((1.0 - frac) * (0.055 + 0.16 * smoke_boundary_strength), 0.0, 0.22)
        w["obj"].color = vector(0.48 + 0.08 * smoke_boundary_strength, 0.49 + 0.08 * smoke_boundary_strength, 0.50 + 0.07 * smoke_boundary_strength)

        if frac >= 1.0:
            w["obj"].visible = False
            to_remove.append(w)

    for w in to_remove:
        if w in smoke_wisps:
            smoke_wisps.remove(w)

def update_memory_marks():
    to_remove = []
    for m in memory_marks:
        m["age"] += dt
        frac = m["age"] / m["life"]

        m["dot"].pos += m["drift"]
        m["dot"].radius = m["base_radius"] * (1.0 + 0.45 * math.sin(t * 3.0 + m["age"]))
        m["dot"].opacity = clamp((1.0 - frac) * (0.12 + 0.30 * escape_noticing), 0.0, 0.38)

        pos = m["dot"].pos
        length = 0.20 + 0.30 * (1.0 - frac)
        toward_flame = safe_norm(flame_base.pos + vector(0, 0.25, 0) - pos)
        end_pos = pos - vector(0, length, 0) + toward_flame * (
            0.12 * inward_pull + 0.09 * returned_heat + 0.10 * pull_drive + 0.08 * inner_ember_heat + 0.11 * proto_core_persistence + 0.05 * loop_strength + 0.05 * heat_path_memory + 0.05 * smoke_boundary_strength
        )

        m["stroke"].clear()
        m["stroke"].append(pos=pos)
        m["stroke"].append(pos=end_pos)
        m["stroke"].opacity = clamp((1.0 - frac) * (0.10 + 0.20 * escape_noticing), 0.0, 0.30)

        if frac >= 1.0:
            m["dot"].visible = False
            m["stroke"].visible = False
            to_remove.append(m)

    for m in to_remove:
        if m in memory_marks:
            memory_marks.remove(m)

def update_simple_particles():
    # Return embers
    to_remove = []
    for e in return_embers:
        e["age"] += dt
        frac = e["age"] / e["life"]
        e["obj"].pos += e["drift"]
        e["obj"].radius = e["base_radius"] * (1.0 + 0.7 * (1.0 - frac))
        e["obj"].opacity = clamp((1.0 - frac) * 0.56, 0.0, 0.56)
        if frac >= 1.0:
            e["obj"].visible = False
            to_remove.append(e)
    for e in to_remove:
        if e in return_embers:
            return_embers.remove(e)

    # Collapse shards
    to_remove = []
    for c in collapse_shards:
        c["age"] += dt
        frac = c["age"] / c["life"]
        c["vel"] *= 0.97
        c["vel"].y -= 0.10 * dt
        c["obj"].pos += c["vel"] * dt
        c["obj"].opacity = clamp((1.0 - frac) * 0.55, 0.0, 0.55)
        c["obj"].radius *= 0.992
        if frac >= 1.0:
            c["obj"].visible = False
            to_remove.append(c)
    for c in to_remove:
        if c in collapse_shards:
            collapse_shards.remove(c)

    # Loop echoes
    to_remove = []
    for e in loop_echoes:
        e["age"] += dt
        frac = e["age"] / e["life"]
        e["obj"].radius += e["grow"] * dt
        e["obj"].opacity = clamp((1.0 - frac) * 0.28, 0.0, 0.28)
        e["obj"].thickness = max(0.002, e["obj"].thickness * 0.995)
        if frac >= 1.0:
            e["obj"].visible = False
            to_remove.append(e)
    for e in to_remove:
        if e in loop_echoes:
            loop_echoes.remove(e)

    # Storage motes
    to_remove = []
    for s in storage_motes:
        s["age"] += dt
        frac = s["age"] / s["life"]
        s["angle"] += s["spin"] * dt * (1.0 + 0.35 * proto_core_persistence + 0.20 * loop_strength + 0.14 * heat_path_memory)
        r = s["radius"] * (1.0 - 0.45 * frac)
        center = unstable_ember.pos
        s["obj"].pos = center + vector(math.cos(s["angle"]) * r, 0.02 + 0.08 * math.sin(t * 2.0 + s["angle"]), math.sin(s["angle"]) * r)
        s["obj"].opacity = clamp((1.0 - frac) * (0.22 + 0.34 * inner_ember_heat + 0.23 * proto_core_persistence + 0.13 * loop_strength + 0.10 * heat_path_memory), 0.0, 0.55)
        if frac >= 1.0:
            s["obj"].visible = False
            to_remove.append(s)
    for s in to_remove:
        if s in storage_motes:
            storage_motes.remove(s)

    # Path motes
    to_remove = []
    for m in path_motes:
        m["age"] += dt
        frac = m["age"] / m["life"]
        hp = heat_paths[m["path"]]
        m["angle"] += m["spin"] * dt * (1.0 + 0.50 * hp["strength"])
        center = flame_base.pos
        m["obj"].pos = center + vector(
            math.cos(m["angle"]) * hp["target_radius"],
            hp["height"] + 0.02 * math.sin(t * 2.5 + m["angle"]),
            math.sin(m["angle"]) * hp["target_radius"]
        )
        m["obj"].opacity = clamp((1.0 - frac) * (0.20 + 0.34 * hp["strength"]), 0.0, 0.45)
        m["obj"].radius *= 0.995
        if frac >= 1.0:
            m["obj"].visible = False
            to_remove.append(m)
    for m in to_remove:
        if m in path_motes:
            path_motes.remove(m)

def update_status():
    will_bars = int(will_to_become_star * 18)
    smoke_bars = int(smoke_boundary_strength * 21)
    band_bars = int(flame_band_strength * 21)
    core_bars = int(stable_core_strength * 19)
    sync_bars = int(core_synchrony * 18)
    path_bars = int(heat_path_memory * 18)
    loop_bars = int(loop_strength * 22)
    proto_bars = int(proto_core_persistence * 20)
    ember_bars = int(inner_ember_heat * 19)
    cycle_bars = int((cycle_time / cycle_duration) * 18)

    def bar(n):
        return "█" * min(n, 18) + "░" * max(0, 18 - n)

    status_label.pos = vector(3.05, 3.70, 0)
    status_label.text = (
        f"cycle {cycle_number}: {cycle_phase.upper()} [{bar(cycle_bars)}]\n"
        f"stable glowing core: {stable_core_strength:0.2f} [{bar(core_bars)}]\n"
        f"core synchrony: {core_synchrony:0.2f} [{bar(sync_bars)}] | stable cycles: {stable_core_cycles} | condenses: {core_condense_events}\n"
        f"core heat reserve: {stable_core_heat:0.2f}\n"
        f"broken flame bands: {flame_band_strength:0.2f} [{bar(band_bars)}]\n"
        f"band memory: {flame_band_memory:0.2f} | reinforces: {band_reinforce_count} | breaks: {band_break_count} | last gain: {last_cycle_band_gain}\n"
        f"smoke boundary: {smoke_boundary_strength:0.2f} [{bar(smoke_bars)}]\n"
        f"smoke wisps: {smoke_wisp_count} | slowed sparks: {smoke_slow_count} | last cycle slowed: {last_cycle_smoke_slow_count}\n"
        f"heat path memory: {heat_path_memory:0.2f} [{bar(path_bars)}]\n"
        f"path guidance: {path_guidance:0.2f} | follows: {path_follow_count} | reinforces: {path_reinforce_count}\n"
        f"partial loop strength: {loop_strength:0.2f} [{bar(loop_bars)}]\n"
        f"partial loops: {partial_loop_count} | loop returns: {loop_return_count} | loop escapes: {loop_escape_count}\n"
        f"fragile proto-core: {proto_core_persistence:0.2f} [{bar(proto_bars)}]\n"
        f"inner ember heat: {inner_ember_heat:0.2f} [{bar(ember_bars)}]\n"
        f"survival streak: {proto_core_survival_streak} | collapses: {proto_core_collapse_count}\n"
        f"last cycle returns: {last_cycle_return_count} | stored: {last_cycle_store_count} | loops: {last_cycle_loop_count} | paths: {last_cycle_path_count}\n"
        f"returned heat: {returned_heat:0.2f} | stored events: {stored_heat_events}\n"
        f"will: {will_to_become_star:0.2f} [{bar(will_bars)}]\n"
        f"escape memory: {escape_noticing:0.2f} | escaped: {escaped_spark_count} | bent: {bent_spark_count}\n"
        "state: stable glowing core emerging, not yet completed star"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00022, 0.0, 0.82)

    update_cycle()
    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_smoke_wisps()
    update_memory_marks()
    update_simple_particles()
    update_status()
