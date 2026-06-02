"""
Fire That Wants To Become A Star — Iteration 9
Circular Heat Paths

Story:
The flame has a fragile proto-core and can bend some nearby sparks into partial loops.
Now repeated partial loops leave faint circular heat paths around the proto-core.

Those paths are not stable flame bands yet. They are weak, broken, fading memory routes.
Later sparks become more likely to follow the same curved paths, but sparks can still
escape, fade, or collapse back into disorder.

New in this version:
- partial loops leave faint circular heat paths
- heat paths guide later sparks into similar curved routes
- path strength fades if sparks stop looping
- the HUD is moved to the right side of the flame

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
"""

from vpython import *
import random
import math

# -----------------------------
# Scene
# -----------------------------
scene.title = "Fire That Wants To Become A Star — Circular Heat Paths"
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
    radius=0.66,
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

# New: broken circular heat paths. They are reusable memory routes, not stable bands.
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

MAX_MEMORY_MARKS = 85
MAX_RETURN_EMBERS = 50
MAX_STORAGE_MOTES = 60
MAX_COLLAPSE_SHARDS = 40
MAX_LOOP_ECHOES = 45
MAX_PATH_MOTES = 70

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
        "bendable": random.random() < 0.58,
        "loopable": random.random() < 0.50,
        "return_glow": 0.0,
        "loop_glow": 0.0,
        "path_glow": 0.0,
        "has_bent": False,
        "has_looped": False,
        "followed_path": False,
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
# Labels / HUD moved to right side
# -----------------------------
title_label = label(
    pos=vector(2.95, 4.18, 0),
    text="Repeated loops leave faint circular heat paths",
    height=15,
    box=False,
    color=vector(0.15, 0.12, 0.08),
    align="left"
)

status_label = label(
    pos=vector(2.95, 3.68, 0),
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
    pos=vector(2.95, 4.55, 0),
    text="H help | P pause | R reset | W will | Space breath | I pull | C cycle | E core | O loop | G guide",
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

will_to_become_star = 0.32
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

inward_pull = 0.14
manual_pull_boost = 0.0
bent_spark_count = 0

returned_heat = 0.0
return_reward_count = 0
base_brighten = 0.0

cycle_time = 0.0
cycle_duration = 5.8
cycle_number = 1
cycle_phase = "rise"
cycle_energy = 0.28
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

# New heat-path learning state.
heat_path_memory = 0.0
path_guidance = 0.0
manual_path_boost = 0.0
path_follow_count = 0
path_reinforce_count = 0
last_cycle_path_count = 0
cycle_start_path_follows = 0

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
    p["life"] = random.uniform(1.5, 3.4)
    p["bendable"] = random.random() < 0.58
    p["loopable"] = random.random() < 0.50
    p["return_glow"] = 0.0
    p["loop_glow"] = 0.0
    p["path_glow"] = 0.0
    p["has_bent"] = False
    p["has_looped"] = False
    p["followed_path"] = False
    p["rewarded"] = False
    p["cycle_birth"] = cycle_number
    p["last_angle"] = math.atan2(p["obj"].pos.z - unstable_ember.pos.z, p["obj"].pos.x - unstable_ember.pos.x)
    p["angle_travel"] = 0.0
    p["loop_time"] = 0.0

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.021, 0.0, 1.0)

    dot = sphere(
        pos=pos,
        radius=random.uniform(0.035, 0.065),
        color=vector(1.0, 0.42, 0.04),
        opacity=0.32,
        emissive=True
    )

    stroke_length = random.uniform(0.18, 0.42)
    stroke = curve(
        pos=[pos, pos - vector(0, stroke_length, 0)],
        radius=random.uniform(0.004, 0.008),
        color=vector(1.0, 0.36, 0.04)
    )
    stroke.opacity = 0.24

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

    return_reward_count += 1
    returned_heat = clamp(returned_heat + (0.044 + (0.020 if from_loop else 0.0) + (0.012 if p["followed_path"] else 0.0)), 0.0, 1.0)
    base_brighten = clamp(base_brighten + 0.43, 0.0, 1.0)

    cycle_energy = clamp(cycle_energy + 0.035 + (0.018 if from_loop else 0.0), 0.0, 1.0)
    inward_pull = clamp(inward_pull + 0.008, 0.02, 0.60)

    if from_loop:
        loop_return_count += 1
        proto_core_persistence = clamp(proto_core_persistence + 0.012, 0.0, 0.90)

    add_return_ember(p["obj"].pos)

def mark_partial_loop(p, path_index=None):
    global partial_loop_count, loop_strength, survival_flash, proto_core_persistence

    p["has_looped"] = True
    p["loop_glow"] = 1.0
    partial_loop_count += 1
    loop_strength = clamp(loop_strength + 0.019, 0.0, 0.78)
    survival_flash = clamp(survival_flash + 0.20, 0.0, 1.0)
    proto_core_persistence = clamp(proto_core_persistence + 0.006, 0.0, 0.90)
    add_loop_echo(p["obj"].pos)

    if path_index is not None:
        reinforce_heat_path(path_index, 0.060)

def store_returned_heat_during_rest():
    global returned_heat, inner_ember_heat, stored_heat_events, base_brighten, last_rest_storage_tick
    global proto_core_persistence

    if cycle_phase != "rest":
        return
    if returned_heat <= 0.015:
        return
    if t - last_rest_storage_tick < 0.22:
        return

    efficiency = 1.0 + 0.55 * proto_core_persistence + 0.18 * heat_path_memory
    amount = min((0.028 + 0.040 * returned_heat) * efficiency, returned_heat * 0.46)

    returned_heat = clamp(returned_heat - amount * 0.34, 0.0, 1.0)
    inner_ember_heat = clamp(inner_ember_heat + amount, 0.0, 0.94)
    base_brighten = clamp(base_brighten + amount * 3.4, 0.0, 1.0)
    stored_heat_events += 1
    last_rest_storage_tick = t

    add_storage_mote()

def evaluate_cycle_survival():
    global cycle_start_returns, cycle_start_storage, cycle_start_loops, cycle_start_path_follows
    global last_cycle_return_count, last_cycle_store_count, last_cycle_loop_count, last_cycle_path_count
    global proto_core_persistence, proto_core_survival_streak, proto_core_collapse_count
    global collapse_flash, survival_flash, inner_ember_heat, loop_strength, path_guidance, heat_path_memory

    cycle_returns = return_reward_count - cycle_start_returns
    cycle_stores = stored_heat_events - cycle_start_storage
    cycle_loops = partial_loop_count - cycle_start_loops
    cycle_paths = path_follow_count - cycle_start_path_follows

    last_cycle_return_count = cycle_returns
    last_cycle_store_count = cycle_stores
    last_cycle_loop_count = cycle_loops
    last_cycle_path_count = cycle_paths

    survived = cycle_stores > 0 and (inner_ember_heat > 0.09 or cycle_returns > 0)
    loop_help = min(cycle_loops, 4) * 0.014
    path_help = min(cycle_paths, 5) * 0.010

    if survived:
        proto_core_survival_streak += 1
        gain = 0.036 + 0.023 * min(proto_core_survival_streak, 5) + 0.015 * min(cycle_stores, 4) + loop_help + path_help
        proto_core_persistence = clamp(proto_core_persistence + gain, 0.0, 0.90)
        survival_flash = 1.0
        inner_ember_heat = clamp(inner_ember_heat + 0.016 * proto_core_persistence + 0.008 * min(cycle_loops, 3), 0.0, 0.94)
    else:
        proto_core_survival_streak = 0
        loss = 0.080 + 0.054 * (1.0 - returned_heat)
        proto_core_persistence = clamp(proto_core_persistence - loss, 0.0, 0.90)
        loop_strength = clamp(loop_strength - 0.055, 0.0, 0.78)
        path_guidance = clamp(path_guidance - 0.055, 0.0, 0.90)
        heat_path_memory = clamp(heat_path_memory - 0.040, 0.0, 1.0)
        if inner_ember_heat > 0.06 or proto_core_persistence > 0.05:
            proto_core_collapse_count += 1
            collapse_flash = 1.0
            add_collapse_shards()
        inner_ember_heat = clamp(inner_ember_heat * 0.72, 0.0, 0.94)

    cycle_start_returns = return_reward_count
    cycle_start_storage = stored_heat_events
    cycle_start_loops = partial_loop_count
    cycle_start_path_follows = path_follow_count

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

    for hp in heat_paths:
        hp["strength"] = 0.0
        hp["obj"].opacity = 0.0

    for group in (memory_marks, return_embers, storage_motes, collapse_shards, loop_echoes, path_motes):
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
    will_to_become_star = 0.32
    breath = 0.0
    inward_pull = 0.14
    manual_pull_boost = 0.0

    cycle_time = 0.0
    cycle_number = 1
    cycle_phase = "rise"
    last_phase = "rise"
    cycle_energy = 0.28

    reset_all_evolving_state()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath, manual_pull_boost
    global cycle_time, cycle_energy, ember_feed_boost, inner_ember_heat, proto_core_persistence, survival_flash
    global manual_loop_boost, loop_strength, manual_path_boost, path_guidance, heat_path_memory

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
        inner_ember_heat = clamp(inner_ember_heat + 0.08, 0.0, 0.94)
        proto_core_persistence = clamp(proto_core_persistence + 0.025, 0.0, 0.90)
        survival_flash = 0.75
    elif k == "o":
        manual_loop_boost = 0.45
        loop_strength = clamp(loop_strength + 0.08, 0.0, 0.78)
    elif k == "g":
        manual_path_boost = 0.45
        path_guidance = clamp(path_guidance + 0.10, 0.0, 0.90)
        heat_path_memory = clamp(heat_path_memory + 0.06, 0.0, 1.0)
        for idx in range(len(heat_paths)):
            reinforce_heat_path(idx, 0.018)

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
            cycle_energy * 0.66
            + returned_heat * 0.18
            + inner_ember_heat * 0.10
            + proto_core_persistence * 0.07
            + loop_strength * 0.04
            + heat_path_memory * 0.035
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
            base_brighten = clamp(base_brighten + 0.14 + 0.04 * path_guidance, 0.0, 1.0)
        elif cycle_phase == "rest":
            base_brighten = clamp(base_brighten + 0.10 + 0.18 * returned_heat + 0.08 * proto_core_persistence, 0.0, 1.0)
        last_phase = cycle_phase

def update_learning_state():
    global inward_pull, manual_pull_boost, escape_noticing, returned_heat
    global base_brighten, cycle_energy, inner_ember_heat, inner_ember_instability, ember_feed_boost
    global proto_core_persistence, collapse_flash, survival_flash, loop_strength, manual_loop_boost
    global heat_path_memory, path_guidance, manual_path_boost

    target_pull = (
        0.05
        + 0.10 * escape_noticing
        + 0.08 * will_to_become_star
        + 0.10 * returned_heat
        + 0.08 * inner_ember_heat
        + 0.12 * proto_core_persistence
        + 0.05 * loop_strength
        + 0.06 * heat_path_memory
        + 0.23 * pull_drive
        + manual_pull_boost
    )
    inward_pull += (target_pull - inward_pull) * 0.020
    inward_pull = clamp(inward_pull, 0.02, 0.60)

    target_loop = (
        0.02
        + 0.10 * inner_ember_heat
        + 0.28 * proto_core_persistence
        + 0.14 * heat_path_memory
        + 0.12 * pull_drive
        + 0.08 * receive_drive
        + manual_loop_boost
    )
    loop_strength += (target_loop - loop_strength) * 0.018
    loop_strength = clamp(loop_strength, 0.0, 0.78)

    target_guidance = (
        0.04 * loop_strength
        + 0.10 * proto_core_persistence
        + 0.55 * heat_path_memory
        + 0.10 * pull_drive
        + 0.08 * receive_drive
        + manual_path_boost
    )
    path_guidance += (target_guidance - path_guidance) * 0.016
    path_guidance = clamp(path_guidance, 0.0, 0.90)

    manual_pull_boost *= 0.94
    manual_loop_boost *= 0.93
    manual_path_boost *= 0.92
    ember_feed_boost *= 0.93
    collapse_flash *= 0.90
    survival_flash *= 0.91

    escape_noticing = clamp(escape_noticing - 0.00023, 0.0, 1.0)
    returned_heat = clamp(returned_heat - 0.00017, 0.0, 1.0)
    base_brighten = clamp(base_brighten * 0.945, 0.0, 1.0)

    # Heat paths fade. They are memory, not stable structure yet.
    total_path = 0.0
    for hp in heat_paths:
        hp["strength"] = clamp(hp["strength"] - 0.00042 * (1.0 + 0.30 * rise_drive), 0.0, 1.0)
        total_path += hp["strength"]
    heat_path_memory = clamp(total_path / len(heat_paths), 0.0, 1.0)

    store_returned_heat_during_rest()

    persistence_protection = 1.0 - 0.48 * proto_core_persistence
    loss = (0.00064 + 0.00074 * (1.0 - returned_heat) + 0.00048 * rise_drive) * persistence_protection
    if cycle_phase == "rest":
        loss *= 0.58
    if cycle_phase == "receive" and returned_heat > 0.02:
        loss *= 0.72

    inner_ember_heat = clamp(inner_ember_heat + 0.0020 * ember_feed_boost - loss, 0.0, 0.94)

    if cycle_phase != "rest":
        proto_core_persistence = clamp(proto_core_persistence - 0.000095 * (1.0 - inner_ember_heat), 0.0, 0.90)

    inner_ember_instability = clamp(
        1.0 - inner_ember_heat * 0.45 - proto_core_persistence * 0.39 - loop_strength * 0.11 - heat_path_memory * 0.10 + 0.12 * math.sin(t * 3.7),
        0.20,
        1.0
    )

    if cycle_phase == "rest":
        cycle_energy = clamp(
            cycle_energy + 0.00038 * returned_heat + 0.00024 * inner_ember_heat + 0.00018 * proto_core_persistence + 0.00012 * heat_path_memory - 0.00014,
            0.0,
            1.0
        )

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    proto_pulse = 0.5 + 0.5 * math.sin(t * (3.4 + 5.0 * inner_ember_instability))
    ember_pulse = 0.5 + 0.5 * math.sin(t * (4.0 + 7.0 * inner_ember_instability))

    collapse_jitter = random.uniform(-0.050, 0.050) * inner_ember_instability * (inner_ember_heat + 0.20 * proto_core_persistence)
    notice_tremble = 0.014 * escape_noticing * math.sin(t * 14.0)

    heat_pulse = base_brighten
    cycle_expand = 0.10 * rise_drive - 0.06 * rest_drive
    cycle_contract = 0.08 * pull_drive

    core_effect = inner_ember_heat * 0.60 + proto_core_persistence * 0.70

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
        - 0.023 * inward_pull
        + 0.026 * heat_pulse
        + 0.042 * core_effect
        + cycle_expand
        - cycle_contract
    )

    flame_base.radius = (
        0.16
        + 0.04 * flicker
        + 0.015 * inward_pull
        + 0.067 * heat_pulse
        + 0.068 * inner_ember_heat
        + 0.063 * proto_core_persistence
        + 0.020 * heat_path_memory
        + 0.030 * receive_drive
    )
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble + collapse_jitter,
        0.17,
        0.025 * math.cos(t * 4.4) - collapse_jitter * 0.4
    )
    flame_base.color = vector(
        1.0,
        clamp(0.24 + 0.12 * will_to_become_star + 0.10 * inward_pull + 0.33 * heat_pulse + 0.25 * inner_ember_heat + 0.24 * proto_core_persistence + 0.08 * heat_path_memory, 0.0, 1.0),
        clamp(0.03 + 0.13 * heat_pulse + 0.10 * inner_ember_heat + 0.10 * proto_core_persistence, 0.0, 1.0)
    )

    base_heat_glow.pos = flame_base.pos + vector(0, 0.02, 0)
    base_heat_glow.radius = 0.21 + 0.30 * heat_pulse + 0.08 * returned_heat + 0.11 * inner_ember_heat + 0.14 * proto_core_persistence + 0.05 * loop_strength + 0.05 * heat_path_memory + 0.08 * receive_drive
    base_heat_glow.opacity = clamp(
        0.05 + 0.35 * heat_pulse + 0.09 * returned_heat + 0.18 * inner_ember_heat + 0.20 * proto_core_persistence + 0.06 * loop_strength + 0.06 * heat_path_memory + 0.12 * receive_drive,
        0.04,
        0.86
    )
    base_heat_glow.color = vector(1.0, 0.45 + 0.25 * heat_pulse + 0.17 * inner_ember_heat + 0.15 * proto_core_persistence + 0.07 * heat_path_memory, 0.05 + 0.10 * heat_pulse)

    core_pos = flame_base.pos + vector(0, 0.065 + 0.012 * ember_pulse, 0)
    unstable_ember.pos = core_pos
    unstable_ember.radius = 0.045 + 0.14 * inner_ember_heat + 0.074 * proto_core_persistence + 0.020 * loop_strength + 0.018 * heat_path_memory + 0.030 * proto_pulse * core_effect
    unstable_ember.opacity = clamp(0.08 + 0.58 * inner_ember_heat + 0.46 * proto_core_persistence + 0.09 * loop_strength + 0.08 * heat_path_memory + 0.08 * proto_pulse - 0.20 * collapse_flash, 0.05, 0.92)
    unstable_ember.color = vector(
        1.0,
        clamp(0.40 + 0.35 * inner_ember_heat + 0.31 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.10 * proto_pulse, 0.0, 1.0),
        clamp(0.05 + 0.18 * inner_ember_heat + 0.18 * proto_core_persistence + 0.04 * loop_strength, 0.0, 1.0)
    )

    proto_core_shell.pos = core_pos
    proto_core_shell.radius = 0.10 + 0.25 * proto_core_persistence + 0.10 * inner_ember_heat + 0.05 * loop_strength + 0.05 * heat_path_memory + 0.03 * proto_pulse
    proto_core_shell.opacity = clamp(0.02 + 0.38 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.12 * survival_flash - 0.12 * collapse_flash, 0.015, 0.55)
    proto_core_shell.color = vector(
        1.0,
        clamp(0.42 + 0.37 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.12 * survival_flash, 0, 1),
        0.05 + 0.16 * proto_core_persistence
    )

    ember_pulse_ring.pos = unstable_ember.pos
    ember_pulse_ring.radius = 0.14 + 0.33 * inner_ember_heat + 0.19 * proto_core_persistence + 0.08 * loop_strength + 0.08 * heat_path_memory + 0.05 * ember_pulse
    ember_pulse_ring.thickness = 0.004 + 0.016 * inner_ember_heat + 0.010 * proto_core_persistence + 0.004 * loop_strength + 0.003 * heat_path_memory
    ember_pulse_ring.opacity = clamp(0.04 + 0.31 * inner_ember_heat * ember_pulse + 0.25 * proto_core_persistence + 0.11 * loop_strength + 0.10 * heat_path_memory + 0.10 * survival_flash, 0.02, 0.55)

    survival_ring.pos = unstable_ember.pos
    survival_ring.radius = 0.22 + 0.44 * proto_core_persistence + 0.06 * loop_strength + 0.05 * heat_path_memory + 0.05 * math.sin(t * 2.8)
    survival_ring.thickness = 0.004 + 0.020 * proto_core_persistence + 0.004 * loop_strength + 0.003 * heat_path_memory
    survival_ring.opacity = clamp(0.02 + 0.33 * proto_core_persistence + 0.07 * loop_strength + 0.06 * heat_path_memory + 0.20 * survival_flash - 0.14 * collapse_flash, 0.01, 0.48)

    loop_guide_ring.pos = flame_base.pos + vector(0, 0.45 + 0.08 * math.sin(t * 2.0), 0)
    loop_guide_ring.radius = 0.48 + 0.34 * loop_strength + 0.08 * heat_path_memory + 0.10 * math.sin(t * 2.4)
    loop_guide_ring.thickness = 0.004 + 0.016 * loop_strength + 0.006 * heat_path_memory
    loop_guide_ring.opacity = clamp(0.02 + 0.34 * loop_strength + 0.15 * heat_path_memory + 0.08 * pull_drive, 0.01, 0.44)
    loop_guide_ring.color = vector(1.0, clamp(0.42 + 0.34 * loop_strength + 0.12 * heat_path_memory, 0, 1), 0.05)

    # Heat paths are deliberately faint and broken-feeling through flicker/tilt.
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
    flame_tip.color = vector(
        1.0,
        clamp(0.42 + 0.14 * will_to_become_star + 0.08 * inward_pull + 0.17 * heat_pulse + 0.14 * core_effect + 0.07 * loop_strength + 0.05 * heat_path_memory + 0.10 * rise_drive, 0.0, 1.0),
        0.06
    )

    inner_flame.pos = flame_base.pos + vector(0, 0.12, 0)
    inner_flame.axis = vector(
        0.025 * math.sin(t * 8.0) + notice_tremble * 0.5,
        height * 0.68,
        0.025 * math.cos(t * 7.5)
    )
    inner_flame.radius = flame_tip.radius * 0.48
    inner_flame.color = vector(
        1.0,
        clamp(0.82 + 0.07 * will_to_become_star + 0.06 * heat_pulse + 0.10 * core_effect + 0.04 * loop_strength + 0.04 * heat_path_memory, 0.0, 1.0),
        clamp(0.22 + 0.06 * heat_pulse + 0.08 * core_effect, 0.0, 1.0)
    )

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(
        1.0,
        clamp(0.36 + 0.22 * will_to_become_star + 0.10 * inward_pull + 0.20 * heat_pulse + 0.20 * core_effect + 0.06 * loop_strength + 0.05 * heat_path_memory, 0.0, 1.0),
        0.08 + 0.05 * core_effect
    )

    desired_star.opacity = 0.13 + 0.17 * will_to_become_star + 0.05 * slow_pulse + 0.03 * cycle_energy + 0.03 * proto_core_persistence + 0.02 * heat_path_memory
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse + 0.02 * proto_core_persistence

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.008 * will_to_become_star + 0.004 * cycle_energy + 0.004 * proto_core_persistence
    will_line.color = vector(1.0, 0.46 + 0.25 * will_to_become_star + 0.10 * proto_core_persistence, 0.04)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.20 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.005 * escape_noticing
    escape_column.color = vector(1.0, 0.40 + 0.23 * escape_noticing, 0.05)

    inward_field_ring.pos = vector(0, 0.78 + 0.04 * math.sin(t * 2.0), 0)
    inward_field_ring.radius = 0.62 + 0.13 * math.sin(t * 3.0) - 0.10 * pull_drive - 0.05 * core_effect
    inward_field_ring.thickness = 0.006 + 0.020 * inward_pull + 0.010 * pull_drive + 0.006 * proto_core_persistence
    inward_field_ring.opacity = 0.04 + 0.16 * inward_pull + 0.10 * pull_drive + 0.05 * returned_heat + 0.08 * proto_core_persistence + 0.04 * heat_path_memory

    cycle_halo.pos = vector(0, 0.31 + 0.03 * math.sin(t * 2.5), 0)
    cycle_halo.radius = 0.42 + 0.26 * rise_drive - 0.10 * pull_drive + 0.10 * receive_drive - 0.04 * rest_drive
    cycle_halo.thickness = 0.006 + 0.018 * (rise_drive + pull_drive + receive_drive) + 0.008 * cycle_energy + 0.004 * proto_core_persistence
    cycle_halo.opacity = 0.08 + 0.15 * cycle_energy + 0.12 * max(rise_drive, pull_drive, receive_drive) + 0.06 * proto_core_persistence + 0.04 * heat_path_memory

    if cycle_phase == "rise":
        cycle_halo.color = vector(1.0, 0.50, 0.06)
    elif cycle_phase == "pull":
        cycle_halo.color = vector(1.0, 0.34, 0.04)
    elif cycle_phase == "receive":
        cycle_halo.color = vector(1.0, 0.72, 0.12)
    else:
        cycle_halo.color = vector(1.0, 0.45 + 0.25 * core_effect, 0.06)

    breath *= 0.94

def update_sparks():
    global bent_spark_count, loop_escape_count, path_follow_count

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
            0.10 * will_to_become_star + 0.24 * rise_drive + 0.04 * cycle_energy + 0.030 * inner_ember_heat + 0.020 * proto_core_persistence,
            0
        )

        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.22

        if p["bendable"] and pull_zone:
            pull_strength = (
                inward_pull
                * (0.25 + 0.33 * escape_noticing + 0.24 * returned_heat + 0.18 * inner_ember_heat + 0.25 * proto_core_persistence + 0.10 * heat_path_memory + 1.02 * pull_drive)
                / (0.75 + distance)
            )
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.031 * inward_pull * (escape_noticing + returned_heat + pull_drive + 0.5 * inner_ember_heat + 0.6 * proto_core_persistence), 0)
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
            and 0.26 < obj.pos.y < 1.72
        )

        if path_zone:
            tangent = tangent_around_y(rel_loop)
            radial_error = flat_dist - hp["target_radius"]
            vertical_error = rel_loop.y - hp["height"]

            radial_force = -safe_norm(vector(rel_loop.x, 0, rel_loop.z)) * radial_error * (0.12 + 0.38 * hp["strength"] + 0.22 * path_guidance)
            vertical_force = vector(0, -vertical_error * (0.05 + 0.20 * hp["strength"]), 0)
            guided_drive = 0.18 + 0.85 * hp["strength"] + 0.55 * path_guidance + 0.22 * loop_strength

            p["vel"] += (tangent * guided_drive + radial_force + vertical_force) * dt
            p["path_glow"] = clamp(p["path_glow"] + 0.045, 0.0, 1.0)
            p["loop_glow"] = clamp(p["loop_glow"] + 0.025, 0.0, 1.0)

            if not p["followed_path"]:
                p["followed_path"] = True
                path_follow_count += 1
                reinforce_heat_path(path_index, 0.018)

        # Partial-loop behavior remains, now supported by heat paths.
        loop_zone = (
            p["loopable"]
            and (0.30 < obj.pos.y < 1.70)
            and (0.18 < flat_dist < 1.20)
            and proto_core_persistence > 0.05
        )
        if loop_zone:
            tangent = tangent_around_y(rel_loop)
            radial_target = 0.54 + 0.24 * (1.0 - proto_core_persistence)
            radial_error = flat_dist - radial_target
            radial_force = -safe_norm(vector(rel_loop.x, 0, rel_loop.z)) * radial_error * (0.07 + 0.21 * loop_strength + 0.18 * heat_path_memory)

            loop_drive = (
                0.18
                + 0.86 * loop_strength
                + 0.40 * proto_core_persistence
                + 0.18 * heat_path_memory
                + 0.22 * pull_drive
                + 0.20 * receive_drive
            )
            vertical_hold = vector(0, -0.08 * max(0.0, obj.pos.y - 0.95), 0)
            p["vel"] += (tangent * loop_drive + radial_force + vertical_hold) * dt
            p["loop_time"] += dt
            p["loop_glow"] = clamp(p["loop_glow"] + 0.032, 0.0, 1.0)

            if not p["has_looped"] and (p["angle_travel"] > math.pi * 1.25 or p["loop_time"] > 1.10):
                mark_partial_loop(p, path_index=path_index)

        return_distance = mag(obj.pos - reward_zone_center)
        reward_radius = 0.39 + 0.12 * receive_drive + 0.05 * inner_ember_heat + 0.07 * proto_core_persistence + 0.04 * loop_strength + 0.04 * heat_path_memory
        if p["has_bent"] and not p["rewarded"] and return_distance < reward_radius and obj.pos.y < 0.93:
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

        core_glow = 0.5 * inner_ember_heat + 0.7 * proto_core_persistence + 0.35 * loop_strength + 0.30 * heat_path_memory
        age_fade = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)
        obj.opacity = clamp(age_fade + 0.21 * p["return_glow"] + 0.13 * p["loop_glow"] + 0.16 * p["path_glow"] + 0.08 * rise_drive + 0.030 * core_glow, 0.0, 1.0)
        obj.radius = clamp(0.016 + 0.018 * p["return_glow"] + 0.011 * p["loop_glow"] + 0.010 * p["path_glow"] + 0.006 * rise_drive + 0.004 * core_glow, 0.012, 0.070)
        obj.color = vector(
            1.0,
            clamp(0.48 + 0.27 * p["return_glow"] + 0.20 * p["loop_glow"] + 0.22 * p["path_glow"] + 0.12 * rise_drive + 0.09 * core_glow + 0.11 * random.random(), 0.0, 1.0),
            clamp(0.07 + 0.08 * p["return_glow"] + 0.09 * p["loop_glow"] + 0.10 * p["path_glow"] + 0.04 * core_glow, 0.0, 1.0)
        )

        if p["loop_glow"] > 0.10 or p["path_glow"] > 0.10 or p["has_looped"]:
            p["trail"].append(pos=obj.pos)
            p["trail"].color = vector(1.0, clamp(0.38 + 0.30 * p["loop_glow"] + 0.28 * p["path_glow"], 0, 1), 0.05)
            p["trail"].radius = 0.004 + 0.004 * p["loop_glow"] + 0.004 * p["path_glow"]
            if p["trail"].npoints > 30:
                p["trail"].pop(0)

        escaped_high = obj.pos.y > 2.20
        burned_out_high = p["age"] > p["life"] and obj.pos.y > 1.05

        if escaped_high or burned_out_high:
            if p["has_looped"]:
                loop_escape_count += 1
            add_memory_mark(vector(obj.pos.x, obj.pos.y, obj.pos.z))
            reset_spark(p)
        elif p["age"] > p["life"]:
            reset_spark(p)

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
            0.12 * inward_pull + 0.09 * returned_heat + 0.10 * pull_drive + 0.08 * inner_ember_heat + 0.11 * proto_core_persistence + 0.05 * loop_strength + 0.05 * heat_path_memory
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

def update_return_embers():
    to_remove = []
    for e in return_embers:
        e["age"] += dt
        frac = e["age"] / e["life"]

        e["obj"].pos += e["drift"]
        e["obj"].radius = e["base_radius"] * (1.0 + 0.7 * (1.0 - frac))
        e["obj"].opacity = clamp((1.0 - frac) * 0.56, 0.0, 0.56)
        e["obj"].color = vector(1.0, clamp(0.55 + 0.28 * (1.0 - frac), 0, 1), 0.08)

        if frac >= 1.0:
            e["obj"].visible = False
            to_remove.append(e)

    for e in to_remove:
        if e in return_embers:
            return_embers.remove(e)

def update_storage_motes():
    to_remove = []
    for s in storage_motes:
        s["age"] += dt
        frac = s["age"] / s["life"]

        s["angle"] += s["spin"] * dt * (1.0 + 0.35 * proto_core_persistence + 0.20 * loop_strength + 0.14 * heat_path_memory)
        r = s["radius"] * (1.0 - 0.45 * frac)
        center = unstable_ember.pos
        s["obj"].pos = center + vector(math.cos(s["angle"]) * r, 0.02 + 0.08 * math.sin(t * 2.0 + s["angle"]), math.sin(s["angle"]) * r)
        s["obj"].opacity = clamp((1.0 - frac) * (0.22 + 0.34 * inner_ember_heat + 0.23 * proto_core_persistence + 0.13 * loop_strength + 0.10 * heat_path_memory), 0.0, 0.55)
        s["obj"].radius = clamp(0.010 + 0.026 * (1.0 - frac), 0.006, 0.035)

        if frac >= 1.0:
            s["obj"].visible = False
            to_remove.append(s)

    for s in to_remove:
        if s in storage_motes:
            storage_motes.remove(s)

def update_collapse_shards():
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

def update_loop_echoes():
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

def update_path_motes():
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
    notice_bars = int(escape_noticing * 18)
    pull_bars = int(inward_pull * 31)
    heat_bars = int(returned_heat * 18)
    cycle_bars = int((cycle_time / cycle_duration) * 18)
    energy_bars = int(cycle_energy * 18)
    ember_bars = int(inner_ember_heat * 19)
    proto_bars = int(proto_core_persistence * 20)
    loop_bars = int(loop_strength * 23)
    path_bars = int(heat_path_memory * 18)

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)
    pull_bar = "█" * min(pull_bars, 18) + "░" * max(0, 18 - pull_bars)
    heat_bar = "█" * heat_bars + "░" * (18 - heat_bars)
    cycle_bar = "█" * cycle_bars + "░" * (18 - cycle_bars)
    energy_bar = "█" * energy_bars + "░" * (18 - energy_bars)
    ember_bar = "█" * min(ember_bars, 18) + "░" * max(0, 18 - ember_bars)
    proto_bar = "█" * min(proto_bars, 18) + "░" * max(0, 18 - proto_bars)
    loop_bar = "█" * min(loop_bars, 18) + "░" * max(0, 18 - loop_bars)
    path_bar = "█" * path_bars + "░" * (18 - path_bars)

    status_label.pos = vector(2.95, 3.70, 0)
    status_label.text = (
        f"cycle {cycle_number}: {cycle_phase.upper()} [{cycle_bar}]\n"
        f"heat path memory: {heat_path_memory:0.2f} [{path_bar}]\n"
        f"path guidance: {path_guidance:0.2f} | follows: {path_follow_count} | reinforces: {path_reinforce_count}\n"
        f"partial loop strength: {loop_strength:0.2f} [{loop_bar[:18]}]\n"
        f"partial loops: {partial_loop_count} | loop returns: {loop_return_count} | loop escapes: {loop_escape_count}\n"
        f"fragile proto-core: {proto_core_persistence:0.2f} [{proto_bar[:18]}]\n"
        f"inner ember heat: {inner_ember_heat:0.2f} [{ember_bar[:18]}]\n"
        f"survival streak: {proto_core_survival_streak} | collapses: {proto_core_collapse_count}\n"
        f"last cycle returns: {last_cycle_return_count} | stored: {last_cycle_store_count} | loops: {last_cycle_loop_count} | paths: {last_cycle_path_count}\n"
        f"cycle energy: {cycle_energy:0.2f} [{energy_bar}]\n"
        f"returned heat: {returned_heat:0.2f} [{heat_bar}] | stored events: {stored_heat_events}\n"
        f"will: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"weak inward pull: {inward_pull:0.2f} [{pull_bar[:18]}]\n"
        f"escaped: {escaped_spark_count} | bent: {bent_spark_count} | returns: {return_reward_count}\n"
        "state: circular heat paths, not yet flame bands"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00023, 0.0, 0.80)

    update_cycle()
    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_return_embers()
    update_storage_motes()
    update_collapse_shards()
    update_loop_echoes()
    update_path_motes()
    update_status()
