"""
Fire That Wants To Become A Star — Iteration 7
Fragile Proto-Core

Story:
The flame has learned rhythm and has an unstable inner ember.
Now repeated rest phases make the inner ember persist longer, forming a fragile
proto-core that flickers between collapse and survival.

This is still not a completed star:
- the proto-core survives only when enough returned heat is stored
- failed cycles make it collapse back into a weak ember
- sparks do not fully orbit yet
- there is no smoke boundary
- there are no rotating flame bands

Controls:
    H       show/hide help
    P       pause/resume
    R       reset
    W       strengthen will
    Space   upward breath
    I       brief inward pull boost
    C       advance/energize the current cycle
    E       briefly feed the proto-core
"""

from vpython import *
import random
import math

# -----------------------------
# Scene
# -----------------------------
scene.title = "Fire That Wants To Become A Star — Fragile Proto-Core"
scene.width = 1120
scene.height = 720
scene.background = vector(0.96, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.range = 5.8
scene.center = vector(0, 1.38, 0)

ground = box(
    pos=vector(0, -0.04, 0),
    size=vector(8, 0.06, 8),
    color=vector(0.78, 0.73, 0.65)
)

charred_patch = cylinder(
    pos=vector(0, 0.005, 0),
    axis=vector(0, 0.01, 0),
    radius=0.62,
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

# Inner ember/proto-core visuals.
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
    pos=vector(0, 3.30, 0),
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

# New visual: survival/collapse halo. It brightens when persistence survives cycles.
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

MAX_MEMORY_MARKS = 85
MAX_RETURN_EMBERS = 50
MAX_STORAGE_MOTES = 60
MAX_COLLAPSE_SHARDS = 40

for _ in range(26):
    s = sphere(
        pos=vector(random.uniform(-0.12, 0.12), random.uniform(0.3, 0.65), random.uniform(-0.12, 0.12)),
        radius=random.uniform(0.015, 0.035),
        color=vector(1.0, random.uniform(0.45, 0.85), 0.08),
        emissive=True,
        opacity=0.85
    )
    sparks.append({
        "obj": s,
        "vel": vector(random.uniform(-0.10, 0.10), random.uniform(0.30, 0.75), random.uniform(-0.10, 0.10)),
        "age": random.random() * 2.0,
        "life": random.uniform(1.5, 3.2),
        "bendable": random.random() < 0.54,
        "return_glow": 0.0,
        "has_bent": False,
        "rewarded": False,
        "cycle_birth": 0,
    })

escape_column = curve(
    pos=[vector(0, 0.5, 0), vector(0, 2.45, 0)],
    radius=0.006,
    color=vector(1.0, 0.48, 0.08)
)
escape_column.opacity = 0.18

# -----------------------------
# Labels
# -----------------------------
title_label = label(
    pos=vector(0, 4.28, 0),
    text="Repeated rests form a fragile proto-core",
    height=16,
    box=False,
    color=vector(0.15, 0.12, 0.08)
)

status_label = label(
    pos=vector(0, 3.82, 0),
    text="",
    height=12,
    box=False,
    color=vector(0.20, 0.15, 0.08)
)

help_label = label(
    pos=vector(-3.90, 4.75, 0),
    text="H help | P pause | R reset | W will | Space breath | I pull | C cycle | E core",
    height=10,
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

will_to_become_star = 0.28
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

inward_pull = 0.12
manual_pull_boost = 0.0
bent_spark_count = 0

returned_heat = 0.0
return_reward_count = 0
base_brighten = 0.0

cycle_time = 0.0
cycle_duration = 5.8
cycle_number = 1
cycle_phase = "rise"
cycle_energy = 0.24
last_phase = "rise"

rise_drive = 0.0
pull_drive = 0.0
receive_drive = 0.0
rest_drive = 0.0

# Storage/proto-core state.
inner_ember_heat = 0.0
inner_ember_instability = 1.0
stored_heat_events = 0
ember_feed_boost = 0.0
last_rest_storage_tick = 0.0

# New: persistence is the fragile proto-core's identity.
proto_core_persistence = 0.0
proto_core_survival_streak = 0
proto_core_collapse_count = 0
last_cycle_return_count = 0
last_cycle_store_count = 0
cycle_start_returns = 0
cycle_start_storage = 0
collapse_flash = 0.0
survival_flash = 0.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v):
    if mag(v) < 0.0001:
        return vector(0, 0, 0)
    return norm(v)

def reset_spark(p):
    p["obj"].pos = vector(
        random.uniform(-0.12, 0.12),
        random.uniform(0.25, 0.55),
        random.uniform(-0.12, 0.12)
    )
    p["obj"].opacity = 0.85
    p["obj"].visible = True
    p["obj"].radius = random.uniform(0.015, 0.035)
    p["vel"] = vector(
        random.uniform(-0.10, 0.10),
        random.uniform(0.30, 0.75),
        random.uniform(-0.10, 0.10)
    )
    p["age"] = 0.0
    p["life"] = random.uniform(1.5, 3.2)
    p["bendable"] = random.random() < 0.54
    p["return_glow"] = 0.0
    p["has_bent"] = False
    p["rewarded"] = False
    p["cycle_birth"] = cycle_number

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.023, 0.0, 1.0)

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

def reward_returning_spark(p):
    global returned_heat, return_reward_count, base_brighten, inward_pull, cycle_energy

    p["rewarded"] = True
    p["return_glow"] = 1.0

    return_reward_count += 1
    returned_heat = clamp(returned_heat + 0.045, 0.0, 1.0)
    base_brighten = clamp(base_brighten + 0.44, 0.0, 1.0)

    cycle_energy = clamp(cycle_energy + 0.036, 0.0, 1.0)
    inward_pull = clamp(inward_pull + 0.009, 0.02, 0.55)

    add_return_ember(p["obj"].pos)

def store_returned_heat_during_rest():
    global returned_heat, inner_ember_heat, stored_heat_events, base_brighten, last_rest_storage_tick
    global proto_core_persistence

    if cycle_phase != "rest":
        return
    if returned_heat <= 0.015:
        return
    if t - last_rest_storage_tick < 0.22:
        return

    # Persistence makes storage more efficient, but the system is still fragile.
    efficiency = 1.0 + 0.55 * proto_core_persistence
    amount = min((0.028 + 0.040 * returned_heat) * efficiency, returned_heat * 0.46)

    returned_heat = clamp(returned_heat - amount * 0.34, 0.0, 1.0)
    inner_ember_heat = clamp(inner_ember_heat + amount, 0.0, 0.92)
    base_brighten = clamp(base_brighten + amount * 3.4, 0.0, 1.0)
    stored_heat_events += 1
    last_rest_storage_tick = t

    add_storage_mote()

def evaluate_cycle_survival():
    """Called when a new cycle starts. Rewards repeated successful rests."""
    global cycle_start_returns, cycle_start_storage, last_cycle_return_count, last_cycle_store_count
    global proto_core_persistence, proto_core_survival_streak, proto_core_collapse_count
    global collapse_flash, survival_flash, inner_ember_heat

    cycle_returns = return_reward_count - cycle_start_returns
    cycle_stores = stored_heat_events - cycle_start_storage
    last_cycle_return_count = cycle_returns
    last_cycle_store_count = cycle_stores

    # Survival condition: the previous cycle returned heat and stored some during rest.
    survived = cycle_stores > 0 and (inner_ember_heat > 0.09 or cycle_returns > 0)

    if survived:
        proto_core_survival_streak += 1
        gain = 0.040 + 0.025 * min(proto_core_survival_streak, 5) + 0.018 * min(cycle_stores, 4)
        proto_core_persistence = clamp(proto_core_persistence + gain, 0.0, 0.86)
        survival_flash = 1.0
        # Persistence protects a small part of ember heat across the next rise phase.
        inner_ember_heat = clamp(inner_ember_heat + 0.018 * proto_core_persistence, 0.0, 0.92)
    else:
        proto_core_survival_streak = 0
        loss = 0.085 + 0.060 * (1.0 - returned_heat)
        proto_core_persistence = clamp(proto_core_persistence - loss, 0.0, 0.86)
        if inner_ember_heat > 0.06 or proto_core_persistence > 0.05:
            proto_core_collapse_count += 1
            collapse_flash = 1.0
            add_collapse_shards()
        inner_ember_heat = clamp(inner_ember_heat * 0.72, 0.0, 0.92)

    cycle_start_returns = return_reward_count
    cycle_start_storage = stored_heat_events

def reset_memory_rewards_and_storage():
    global escape_noticing, escaped_spark_count, bent_spark_count
    global returned_heat, return_reward_count, base_brighten
    global inner_ember_heat, inner_ember_instability, stored_heat_events, ember_feed_boost, last_rest_storage_tick
    global proto_core_persistence, proto_core_survival_streak, proto_core_collapse_count
    global last_cycle_return_count, last_cycle_store_count, cycle_start_returns, cycle_start_storage
    global collapse_flash, survival_flash

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

    for m in memory_marks:
        m["dot"].visible = False
        m["stroke"].visible = False
    memory_marks.clear()

    for e in return_embers:
        e["obj"].visible = False
    return_embers.clear()

    for s in storage_motes:
        s["obj"].visible = False
    storage_motes.clear()

    for c in collapse_shards:
        c["obj"].visible = False
    collapse_shards.clear()

def reset_simulation():
    global t, will_to_become_star, breath, inward_pull, manual_pull_boost
    global cycle_time, cycle_number, cycle_phase, last_phase, cycle_energy

    t = 0.0
    will_to_become_star = 0.28
    breath = 0.0
    inward_pull = 0.12
    manual_pull_boost = 0.0

    cycle_time = 0.0
    cycle_number = 1
    cycle_phase = "rise"
    last_phase = "rise"
    cycle_energy = 0.24

    reset_memory_rewards_and_storage()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath, manual_pull_boost
    global cycle_time, cycle_energy, ember_feed_boost, inner_ember_heat, proto_core_persistence, survival_flash

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
        inner_ember_heat = clamp(inner_ember_heat + 0.08, 0.0, 0.92)
        proto_core_persistence = clamp(proto_core_persistence + 0.025, 0.0, 0.86)
        survival_flash = 0.75

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
            cycle_energy * 0.68
            + returned_heat * 0.20
            + inner_ember_heat * 0.10
            + proto_core_persistence * 0.07
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
            base_brighten = clamp(base_brighten + 0.07, 0.0, 1.0)
        elif cycle_phase == "receive":
            base_brighten = clamp(base_brighten + 0.14, 0.0, 1.0)
        elif cycle_phase == "rest":
            base_brighten = clamp(base_brighten + 0.10 + 0.18 * returned_heat + 0.08 * proto_core_persistence, 0.0, 1.0)
        last_phase = cycle_phase

def update_learning_state():
    global inward_pull, manual_pull_boost, escape_noticing, returned_heat
    global base_brighten, cycle_energy, inner_ember_heat, inner_ember_instability, ember_feed_boost
    global proto_core_persistence, collapse_flash, survival_flash

    target_pull = (
        0.05
        + 0.11 * escape_noticing
        + 0.08 * will_to_become_star
        + 0.11 * returned_heat
        + 0.08 * inner_ember_heat
        + 0.12 * proto_core_persistence
        + 0.24 * pull_drive
        + manual_pull_boost
    )
    inward_pull += (target_pull - inward_pull) * 0.020
    inward_pull = clamp(inward_pull, 0.02, 0.55)

    manual_pull_boost *= 0.94
    ember_feed_boost *= 0.93
    collapse_flash *= 0.90
    survival_flash *= 0.91

    escape_noticing = clamp(escape_noticing - 0.00025, 0.0, 1.0)
    returned_heat = clamp(returned_heat - 0.00017, 0.0, 1.0)
    base_brighten = clamp(base_brighten * 0.945, 0.0, 1.0)

    store_returned_heat_during_rest()

    # Persistence prevents immediate loss; failed return periods still erode heat.
    persistence_protection = 1.0 - 0.48 * proto_core_persistence
    loss = (0.00068 + 0.00078 * (1.0 - returned_heat) + 0.00052 * rise_drive) * persistence_protection
    if cycle_phase == "rest":
        loss *= 0.58
    if cycle_phase == "receive" and returned_heat > 0.02:
        loss *= 0.72

    inner_ember_heat = clamp(inner_ember_heat + 0.0020 * ember_feed_boost - loss, 0.0, 0.92)

    # Persistence itself is fragile and slowly decays unless supported by storage.
    if cycle_phase != "rest":
        proto_core_persistence = clamp(proto_core_persistence - 0.00010 * (1.0 - inner_ember_heat), 0.0, 0.86)

    inner_ember_instability = clamp(
        1.0 - inner_ember_heat * 0.48 - proto_core_persistence * 0.42 + 0.12 * math.sin(t * 3.7),
        0.24,
        1.0
    )

    if cycle_phase == "rest":
        cycle_energy = clamp(
            cycle_energy + 0.00042 * returned_heat + 0.00024 * inner_ember_heat + 0.00018 * proto_core_persistence - 0.00014,
            0.0,
            1.0
        )

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    proto_pulse = 0.5 + 0.5 * math.sin(t * (3.4 + 5.0 * inner_ember_instability))
    ember_pulse = 0.5 + 0.5 * math.sin(t * (4.0 + 7.0 * inner_ember_instability))

    # Collapse flicker makes the proto-core visibly unstable.
    collapse_jitter = random.uniform(-0.055, 0.055) * inner_ember_instability * (inner_ember_heat + 0.20 * proto_core_persistence)
    notice_tremble = 0.016 * escape_noticing * math.sin(t * 14.0)

    heat_pulse = base_brighten
    cycle_expand = 0.10 * rise_drive - 0.06 * rest_drive
    cycle_contract = 0.08 * pull_drive

    core_effect = inner_ember_heat * 0.65 + proto_core_persistence * 0.75

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
        - 0.025 * inward_pull
        + 0.027 * heat_pulse
        + 0.045 * core_effect
        + cycle_expand
        - cycle_contract
    )

    flame_base.radius = (
        0.16
        + 0.04 * flicker
        + 0.016 * inward_pull
        + 0.070 * heat_pulse
        + 0.072 * inner_ember_heat
        + 0.065 * proto_core_persistence
        + 0.032 * receive_drive
    )
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble + collapse_jitter,
        0.17,
        0.025 * math.cos(t * 4.4) - collapse_jitter * 0.4
    )
    flame_base.color = vector(
        1.0,
        clamp(0.24 + 0.12 * will_to_become_star + 0.10 * inward_pull + 0.36 * heat_pulse + 0.27 * inner_ember_heat + 0.26 * proto_core_persistence, 0.0, 1.0),
        clamp(0.03 + 0.13 * heat_pulse + 0.10 * inner_ember_heat + 0.11 * proto_core_persistence, 0.0, 1.0)
    )

    base_heat_glow.pos = flame_base.pos + vector(0, 0.02, 0)
    base_heat_glow.radius = 0.21 + 0.30 * heat_pulse + 0.08 * returned_heat + 0.11 * inner_ember_heat + 0.14 * proto_core_persistence + 0.08 * receive_drive
    base_heat_glow.opacity = clamp(
        0.05 + 0.38 * heat_pulse + 0.09 * returned_heat + 0.18 * inner_ember_heat + 0.22 * proto_core_persistence + 0.12 * receive_drive,
        0.04,
        0.86
    )
    base_heat_glow.color = vector(1.0, 0.45 + 0.28 * heat_pulse + 0.18 * inner_ember_heat + 0.16 * proto_core_persistence, 0.05 + 0.10 * heat_pulse)

    # Proto-core visual: not stable, but now it persists longer after successful rest phases.
    core_pos = flame_base.pos + vector(0, 0.065 + 0.012 * ember_pulse, 0)
    unstable_ember.pos = core_pos
    unstable_ember.radius = 0.045 + 0.14 * inner_ember_heat + 0.075 * proto_core_persistence + 0.030 * proto_pulse * core_effect
    unstable_ember.opacity = clamp(0.08 + 0.62 * inner_ember_heat + 0.50 * proto_core_persistence + 0.08 * proto_pulse - 0.20 * collapse_flash, 0.05, 0.92)
    unstable_ember.color = vector(
        1.0,
        clamp(0.40 + 0.38 * inner_ember_heat + 0.33 * proto_core_persistence + 0.10 * proto_pulse, 0.0, 1.0),
        clamp(0.05 + 0.18 * inner_ember_heat + 0.18 * proto_core_persistence, 0.0, 1.0)
    )

    proto_core_shell.pos = core_pos
    proto_core_shell.radius = 0.10 + 0.26 * proto_core_persistence + 0.10 * inner_ember_heat + 0.03 * proto_pulse
    proto_core_shell.opacity = clamp(0.02 + 0.42 * proto_core_persistence + 0.12 * survival_flash - 0.12 * collapse_flash, 0.015, 0.55)
    proto_core_shell.color = vector(
        1.0,
        clamp(0.42 + 0.40 * proto_core_persistence + 0.12 * survival_flash, 0, 1),
        0.05 + 0.16 * proto_core_persistence
    )

    ember_pulse_ring.pos = unstable_ember.pos
    ember_pulse_ring.radius = 0.14 + 0.34 * inner_ember_heat + 0.20 * proto_core_persistence + 0.05 * ember_pulse
    ember_pulse_ring.thickness = 0.004 + 0.016 * inner_ember_heat + 0.010 * proto_core_persistence
    ember_pulse_ring.opacity = clamp(0.04 + 0.34 * inner_ember_heat * ember_pulse + 0.28 * proto_core_persistence + 0.10 * survival_flash, 0.02, 0.55)

    survival_ring.pos = unstable_ember.pos
    survival_ring.radius = 0.22 + 0.46 * proto_core_persistence + 0.05 * math.sin(t * 2.8)
    survival_ring.thickness = 0.004 + 0.020 * proto_core_persistence
    survival_ring.opacity = clamp(0.02 + 0.36 * proto_core_persistence + 0.20 * survival_flash - 0.14 * collapse_flash, 0.01, 0.48)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = clamp(width, 0.12, 0.34)
    flame_tip.color = vector(
        1.0,
        clamp(0.42 + 0.14 * will_to_become_star + 0.08 * inward_pull + 0.18 * heat_pulse + 0.15 * core_effect + 0.10 * rise_drive, 0.0, 1.0),
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
        clamp(0.82 + 0.07 * will_to_become_star + 0.06 * heat_pulse + 0.11 * core_effect, 0.0, 1.0),
        clamp(0.22 + 0.06 * heat_pulse + 0.08 * core_effect, 0.0, 1.0)
    )

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(
        1.0,
        clamp(0.36 + 0.22 * will_to_become_star + 0.10 * inward_pull + 0.20 * heat_pulse + 0.20 * core_effect, 0.0, 1.0),
        0.08 + 0.05 * core_effect
    )

    desired_star.opacity = 0.13 + 0.17 * will_to_become_star + 0.05 * slow_pulse + 0.03 * cycle_energy + 0.03 * proto_core_persistence
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
    inward_field_ring.opacity = 0.04 + 0.17 * inward_pull + 0.10 * pull_drive + 0.05 * returned_heat + 0.09 * proto_core_persistence

    cycle_halo.pos = vector(0, 0.31 + 0.03 * math.sin(t * 2.5), 0)
    cycle_halo.radius = 0.42 + 0.26 * rise_drive - 0.10 * pull_drive + 0.10 * receive_drive - 0.04 * rest_drive
    cycle_halo.thickness = 0.006 + 0.018 * (rise_drive + pull_drive + receive_drive) + 0.008 * cycle_energy + 0.004 * proto_core_persistence
    cycle_halo.opacity = 0.08 + 0.16 * cycle_energy + 0.12 * max(rise_drive, pull_drive, receive_drive) + 0.06 * proto_core_persistence

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
    global bent_spark_count

    flame_center = flame_base.pos + vector(0, 0.35, 0)
    reward_zone_center = flame_base.pos + vector(0, 0.28, 0)

    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        upward_lift = vector(
            0,
            0.10 * will_to_become_star + 0.26 * rise_drive + 0.04 * cycle_energy + 0.030 * inner_ember_heat + 0.020 * proto_core_persistence,
            0
        )

        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.20

        if p["bendable"] and pull_zone:
            pull_strength = (
                inward_pull
                * (0.27 + 0.36 * escape_noticing + 0.26 * returned_heat + 0.20 * inner_ember_heat + 0.28 * proto_core_persistence + 1.06 * pull_drive)
                / (0.75 + distance)
            )
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.033 * inward_pull * (escape_noticing + returned_heat + pull_drive + 0.5 * inner_ember_heat + 0.6 * proto_core_persistence), 0)
            p["vel"] += (inward_force + downward_memory) * dt

            if p["vel"].y < 0.25 and not p["has_bent"]:
                bent_spark_count += 1
                p["has_bent"] = True
                p["return_glow"] = 0.72

        return_distance = mag(obj.pos - reward_zone_center)
        reward_radius = 0.39 + 0.12 * receive_drive + 0.05 * inner_ember_heat + 0.07 * proto_core_persistence
        if p["has_bent"] and not p["rewarded"] and return_distance < reward_radius and obj.pos.y < 0.89:
            reward_returning_spark(p)

        p["vel"] += upward_lift * dt
        p["vel"] += vector(
            random.uniform(-0.016, 0.016),
            random.uniform(-0.004, 0.016),
            random.uniform(-0.016, 0.016)
        )
        p["vel"] *= 0.985 - 0.016 * rest_drive

        obj.pos += p["vel"] * dt
        p["return_glow"] *= 0.94

        core_glow = 0.5 * inner_ember_heat + 0.7 * proto_core_persistence
        age_fade = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)
        obj.opacity = clamp(age_fade + 0.24 * p["return_glow"] + 0.09 * rise_drive + 0.035 * core_glow, 0.0, 1.0)
        obj.radius = clamp(0.016 + 0.020 * p["return_glow"] + 0.006 * rise_drive + 0.004 * core_glow, 0.012, 0.064)
        obj.color = vector(
            1.0,
            clamp(0.48 + 0.30 * p["return_glow"] + 0.13 * rise_drive + 0.10 * core_glow + 0.13 * random.random(), 0.0, 1.0),
            clamp(0.07 + 0.09 * p["return_glow"] + 0.04 * core_glow, 0.0, 1.0)
        )

        escaped_high = obj.pos.y > 2.16
        burned_out_high = p["age"] > p["life"] and obj.pos.y > 1.05

        if escaped_high or burned_out_high:
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
            0.12 * inward_pull + 0.09 * returned_heat + 0.10 * pull_drive + 0.08 * inner_ember_heat + 0.11 * proto_core_persistence
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

        s["angle"] += s["spin"] * dt * (1.0 + 0.35 * proto_core_persistence)
        r = s["radius"] * (1.0 - 0.45 * frac)
        center = unstable_ember.pos
        s["obj"].pos = center + vector(math.cos(s["angle"]) * r, 0.02 + 0.08 * math.sin(t * 2.0 + s["angle"]), math.sin(s["angle"]) * r)
        s["obj"].opacity = clamp((1.0 - frac) * (0.22 + 0.36 * inner_ember_heat + 0.26 * proto_core_persistence), 0.0, 0.55)
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

def update_status():
    will_bars = int(will_to_become_star * 18)
    notice_bars = int(escape_noticing * 18)
    pull_bars = int(inward_pull * 34)
    heat_bars = int(returned_heat * 18)
    cycle_bars = int((cycle_time / cycle_duration) * 18)
    energy_bars = int(cycle_energy * 18)
    ember_bars = int(inner_ember_heat * 20)
    proto_bars = int(proto_core_persistence * 21)

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)
    pull_bar = "█" * min(pull_bars, 18) + "░" * max(0, 18 - pull_bars)
    heat_bar = "█" * heat_bars + "░" * (18 - heat_bars)
    cycle_bar = "█" * cycle_bars + "░" * (18 - cycle_bars)
    energy_bar = "█" * energy_bars + "░" * (18 - energy_bars)
    ember_bar = "█" * min(ember_bars, 18) + "░" * max(0, 18 - ember_bars)
    proto_bar = "█" * min(proto_bars, 18) + "░" * max(0, 18 - proto_bars)

    status_label.text = (
        f"cycle {cycle_number}: {cycle_phase.upper()} [{cycle_bar}]\n"
        f"fragile proto-core: {proto_core_persistence:0.2f} [{proto_bar[:18]}]\n"
        f"inner ember heat: {inner_ember_heat:0.2f} [{ember_bar[:18]}]\n"
        f"survival streak: {proto_core_survival_streak} | collapses: {proto_core_collapse_count}\n"
        f"last cycle returns: {last_cycle_return_count} | stored: {last_cycle_store_count}\n"
        f"cycle energy: {cycle_energy:0.2f} [{energy_bar}]\n"
        f"returned heat: {returned_heat:0.2f} [{heat_bar}] | stored events: {stored_heat_events}\n"
        f"will: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"weak inward pull: {inward_pull:0.2f} [{pull_bar[:18]}]\n"
        f"escaped: {escaped_spark_count} | bent: {bent_spark_count} | returns: {return_reward_count}\n"
        "state: fragile proto-core, not yet stable"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00026, 0.0, 0.76)

    update_cycle()
    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_return_embers()
    update_storage_motes()
    update_collapse_shards()
    update_status()
