"""
Fire That Wants To Become A Star — Iteration 5
Pulse Cycle: Rise, Pull, Receive, Rest

Story:
The flame is still small, but it is no longer only reacting.
It begins to pulse in cycles:

1. RISE    — sends sparks upward
2. PULL    — tries to bend some sparks back
3. RECEIVE — brightens when returning sparks pass near the base
4. REST    — shrinks and stores the lesson before trying again

This is still not a star:
- no stable core
- no smoke boundary
- no full orbiting spark system
- no rotating flame bands

Controls:
    H       show/hide help
    P       pause/resume
    R       reset
    W       strengthen will
    Space   upward breath
    I       brief inward pull boost
    C       shorten/energize the current cycle
"""

from vpython import *
import random
import math

scene.title = "Fire That Wants To Become A Star — Pulse Cycle"
scene.width = 1120
scene.height = 720
scene.background = vector(0.96, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.range = 5.7
scene.center = vector(0, 1.35, 0)

ground = box(
    pos=vector(0, -0.04, 0),
    size=vector(8, 0.06, 8),
    color=vector(0.78, 0.73, 0.65)
)

charred_patch = cylinder(
    pos=vector(0, 0.005, 0),
    axis=vector(0, 0.01, 0),
    radius=0.58,
    color=vector(0.18, 0.15, 0.12),
    opacity=0.55
)

# Flame body
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
    pos=vector(0, 3.28, 0),
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

# New: a visible cycle halo that expands/contracts with the current phase.
cycle_halo = ring(
    pos=vector(0, 0.32, 0),
    axis=vector(0, 1, 0),
    radius=0.45,
    thickness=0.012,
    color=vector(1.0, 0.48, 0.06),
    opacity=0.16,
    emissive=True
)

# Particles and marks
sparks = []
memory_marks = []
return_embers = []
MAX_MEMORY_MARKS = 85
MAX_RETURN_EMBERS = 50

for _ in range(24):
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
        "bendable": random.random() < 0.50,
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

title_label = label(
    pos=vector(0, 4.25, 0),
    text="The flame learns a cycle: rise, pull, receive, rest",
    height=16,
    box=False,
    color=vector(0.15, 0.12, 0.08)
)

status_label = label(
    pos=vector(0, 3.80, 0),
    text="",
    height=12,
    box=False,
    color=vector(0.20, 0.15, 0.08)
)

help_label = label(
    pos=vector(-3.85, 4.72, 0),
    text="H help | P pause | R reset | W will | Space breath | I pull | C cycle",
    height=10,
    box=False,
    align="left",
    color=vector(0.12, 0.12, 0.12)
)

# State
t = 0.0
dt = 0.025
paused = False
show_help = True

will_to_become_star = 0.24
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

inward_pull = 0.10
manual_pull_boost = 0.0
bent_spark_count = 0

returned_heat = 0.0
return_reward_count = 0
base_brighten = 0.0

# New cycle state
cycle_time = 0.0
cycle_duration = 5.8
cycle_number = 1
cycle_phase = "rise"
cycle_energy = 0.20
last_phase = "rise"

# Phase intensities used by physics and visuals
rise_drive = 0.0
pull_drive = 0.0
receive_drive = 0.0
rest_drive = 0.0

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
    p["bendable"] = random.random() < 0.50
    p["return_glow"] = 0.0
    p["has_bent"] = False
    p["rewarded"] = False
    p["cycle_birth"] = cycle_number

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.025, 0.0, 1.0)

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

def reward_returning_spark(p):
    global returned_heat, return_reward_count, base_brighten, inward_pull, cycle_energy

    p["rewarded"] = True
    p["return_glow"] = 1.0

    return_reward_count += 1
    returned_heat = clamp(returned_heat + 0.048, 0.0, 1.0)
    base_brighten = clamp(base_brighten + 0.48, 0.0, 1.0)

    # The reward feeds the next cycle rather than forming a stable core yet.
    cycle_energy = clamp(cycle_energy + 0.040, 0.0, 1.0)
    inward_pull = clamp(inward_pull + 0.010, 0.02, 0.50)

    add_return_ember(p["obj"].pos)

def reset_memory_and_rewards():
    global escape_noticing, escaped_spark_count, bent_spark_count
    global returned_heat, return_reward_count, base_brighten

    escape_noticing = 0.0
    escaped_spark_count = 0
    bent_spark_count = 0
    returned_heat = 0.0
    return_reward_count = 0
    base_brighten = 0.0

    for m in memory_marks:
        m["dot"].visible = False
        m["stroke"].visible = False
    memory_marks.clear()

    for e in return_embers:
        e["obj"].visible = False
    return_embers.clear()

def reset_simulation():
    global t, will_to_become_star, breath, inward_pull, manual_pull_boost
    global cycle_time, cycle_number, cycle_phase, last_phase, cycle_energy

    t = 0.0
    will_to_become_star = 0.24
    breath = 0.0
    inward_pull = 0.10
    manual_pull_boost = 0.0

    cycle_time = 0.0
    cycle_number = 1
    cycle_phase = "rise"
    last_phase = "rise"
    cycle_energy = 0.20

    reset_memory_and_rewards()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath, manual_pull_boost, cycle_time, cycle_energy

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

scene.bind("keydown", keydown)

def update_cycle():
    global cycle_time, cycle_number, cycle_phase, last_phase
    global rise_drive, pull_drive, receive_drive, rest_drive, cycle_energy, base_brighten

    cycle_time += dt
    progress = cycle_time / cycle_duration

    if progress >= 1.0:
        cycle_time = 0.0
        cycle_number += 1
        # Successful returns make the next cycle a little more confident.
        cycle_energy = clamp(cycle_energy * 0.72 + returned_heat * 0.25 + will_to_become_star * 0.05, 0.05, 1.0)
        progress = 0.0

    if progress < 0.28:
        cycle_phase = "rise"
    elif progress < 0.58:
        cycle_phase = "pull"
    elif progress < 0.78:
        cycle_phase = "receive"
    else:
        cycle_phase = "rest"

    local = progress
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

    # Phase transition pulse.
    if cycle_phase != last_phase:
        if cycle_phase == "rise":
            base_brighten = clamp(base_brighten + 0.10, 0.0, 1.0)
        elif cycle_phase == "pull":
            base_brighten = clamp(base_brighten + 0.08, 0.0, 1.0)
        elif cycle_phase == "receive":
            base_brighten = clamp(base_brighten + 0.16, 0.0, 1.0)
        last_phase = cycle_phase

def update_learning_state():
    global inward_pull, manual_pull_boost, escape_noticing, returned_heat, base_brighten, cycle_energy

    target_pull = (
        0.05
        + 0.13 * escape_noticing
        + 0.08 * will_to_become_star
        + 0.13 * returned_heat
        + 0.26 * pull_drive
        + manual_pull_boost
    )
    inward_pull += (target_pull - inward_pull) * 0.020
    inward_pull = clamp(inward_pull, 0.02, 0.50)

    manual_pull_boost *= 0.94
    escape_noticing = clamp(escape_noticing - 0.00028, 0.0, 1.0)
    returned_heat = clamp(returned_heat - 0.00020, 0.0, 1.0)
    base_brighten = clamp(base_brighten * 0.945, 0.0, 1.0)

    # Rest stores a tiny amount of successful rhythm as cycle energy.
    if cycle_phase == "rest":
        cycle_energy = clamp(cycle_energy + 0.00055 * returned_heat - 0.00018, 0.0, 1.0)

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    notice_tremble = 0.018 * escape_noticing * math.sin(t * 14.0)

    heat_pulse = base_brighten
    cycle_expand = 0.10 * rise_drive - 0.06 * rest_drive
    cycle_contract = 0.08 * pull_drive

    height = (
        0.56
        + 0.15 * flicker
        + 0.14 * will_to_become_star
        + 0.16 * breath
        + 0.08 * heat_pulse
        + 0.18 * rise_drive
        - 0.07 * rest_drive
    )
    width = (
        0.21
        + 0.030 * math.sin(t * 7.0)
        - 0.028 * inward_pull
        + 0.030 * heat_pulse
        + cycle_expand
        - cycle_contract
    )

    flame_base.radius = 0.16 + 0.04 * flicker + 0.018 * inward_pull + 0.08 * heat_pulse + 0.04 * receive_drive
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble,
        0.17,
        0.025 * math.cos(t * 4.4)
    )
    flame_base.color = vector(
        1.0,
        clamp(0.24 + 0.13 * will_to_become_star + 0.11 * inward_pull + 0.42 * heat_pulse + 0.15 * receive_drive, 0.0, 1.0),
        clamp(0.03 + 0.16 * heat_pulse + 0.06 * receive_drive, 0.0, 1.0)
    )

    base_heat_glow.pos = flame_base.pos + vector(0, 0.02, 0)
    base_heat_glow.radius = 0.21 + 0.34 * heat_pulse + 0.08 * returned_heat + 0.08 * receive_drive
    base_heat_glow.opacity = 0.05 + 0.43 * heat_pulse + 0.10 * returned_heat + 0.15 * receive_drive
    base_heat_glow.color = vector(1.0, 0.45 + 0.34 * heat_pulse + 0.12 * receive_drive, 0.05 + 0.12 * heat_pulse)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = clamp(width, 0.12, 0.31)
    flame_tip.color = vector(
        1.0,
        clamp(0.42 + 0.15 * will_to_become_star + 0.08 * inward_pull + 0.20 * heat_pulse + 0.12 * rise_drive, 0.0, 1.0),
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
        clamp(0.82 + 0.08 * will_to_become_star + 0.08 * heat_pulse + 0.05 * receive_drive, 0.0, 1.0),
        clamp(0.22 + 0.08 * heat_pulse, 0.0, 1.0)
    )

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(
        1.0,
        clamp(0.36 + 0.25 * will_to_become_star + 0.11 * inward_pull + 0.24 * heat_pulse + 0.10 * receive_drive, 0.0, 1.0),
        0.08
    )

    desired_star.opacity = 0.13 + 0.18 * will_to_become_star + 0.05 * slow_pulse + 0.03 * cycle_energy
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.008 * will_to_become_star + 0.004 * cycle_energy
    will_line.color = vector(1.0, 0.46 + 0.27 * will_to_become_star, 0.04)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.20 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.005 * escape_noticing
    escape_column.color = vector(1.0, 0.40 + 0.24 * escape_noticing, 0.05)

    inward_field_ring.pos = vector(0, 0.78 + 0.04 * math.sin(t * 2.0), 0)
    inward_field_ring.radius = 0.62 + 0.13 * math.sin(t * 3.0) - 0.10 * pull_drive
    inward_field_ring.thickness = 0.006 + 0.020 * inward_pull + 0.010 * pull_drive
    inward_field_ring.opacity = 0.04 + 0.20 * inward_pull + 0.12 * pull_drive + 0.06 * returned_heat

    cycle_halo.pos = vector(0, 0.31 + 0.03 * math.sin(t * 2.5), 0)
    cycle_halo.radius = 0.42 + 0.28 * rise_drive - 0.10 * pull_drive + 0.10 * receive_drive - 0.04 * rest_drive
    cycle_halo.thickness = 0.006 + 0.020 * (rise_drive + pull_drive + receive_drive) + 0.008 * cycle_energy
    cycle_halo.opacity = 0.08 + 0.18 * cycle_energy + 0.13 * max(rise_drive, pull_drive, receive_drive)
    if cycle_phase == "rise":
        cycle_halo.color = vector(1.0, 0.50, 0.06)
    elif cycle_phase == "pull":
        cycle_halo.color = vector(1.0, 0.34, 0.04)
    elif cycle_phase == "receive":
        cycle_halo.color = vector(1.0, 0.72, 0.12)
    else:
        cycle_halo.color = vector(0.90, 0.34, 0.06)

    breath *= 0.94

def update_sparks():
    global bent_spark_count

    flame_center = flame_base.pos + vector(0, 0.35, 0)
    reward_zone_center = flame_base.pos + vector(0, 0.28, 0)

    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        # RISE phase sends sparks upward more strongly.
        upward_lift = vector(0, 0.10 * will_to_become_star + 0.28 * rise_drive + 0.04 * cycle_energy, 0)

        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.20

        if p["bendable"] and pull_zone:
            # PULL phase gives the strongest bend back.
            pull_strength = (
                inward_pull
                * (0.30 + 0.40 * escape_noticing + 0.30 * returned_heat + 1.15 * pull_drive)
                / (0.75 + distance)
            )
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.035 * inward_pull * (escape_noticing + returned_heat + pull_drive), 0)
            p["vel"] += (inward_force + downward_memory) * dt

            if p["vel"].y < 0.25 and not p["has_bent"]:
                bent_spark_count += 1
                p["has_bent"] = True
                p["return_glow"] = 0.72

        # RECEIVE phase makes close returning sparks easier to reward.
        return_distance = mag(obj.pos - reward_zone_center)
        reward_radius = 0.39 + 0.14 * receive_drive
        if p["has_bent"] and not p["rewarded"] and return_distance < reward_radius and obj.pos.y < 0.86:
            reward_returning_spark(p)

        # REST phase damps new upward escape.
        p["vel"] += upward_lift * dt
        p["vel"] += vector(
            random.uniform(-0.016, 0.016),
            random.uniform(-0.004, 0.016),
            random.uniform(-0.016, 0.016)
        )
        p["vel"] *= 0.985 - 0.018 * rest_drive

        obj.pos += p["vel"] * dt
        p["return_glow"] *= 0.94

        age_fade = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)
        obj.opacity = clamp(age_fade + 0.24 * p["return_glow"] + 0.10 * rise_drive, 0.0, 1.0)
        obj.radius = clamp(0.016 + 0.020 * p["return_glow"] + 0.006 * rise_drive, 0.012, 0.060)
        obj.color = vector(
            1.0,
            clamp(0.48 + 0.31 * p["return_glow"] + 0.14 * rise_drive + 0.14 * random.random(), 0.0, 1.0),
            clamp(0.07 + 0.09 * p["return_glow"], 0.0, 1.0)
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
        end_pos = pos - vector(0, length, 0) + toward_flame * (0.12 * inward_pull + 0.10 * returned_heat + 0.10 * pull_drive)

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
        e["obj"].opacity = clamp((1.0 - frac) * 0.58, 0.0, 0.58)
        e["obj"].color = vector(1.0, clamp(0.55 + 0.28 * (1.0 - frac), 0, 1), 0.08)

        if frac >= 1.0:
            e["obj"].visible = False
            to_remove.append(e)

    for e in to_remove:
        if e in return_embers:
            return_embers.remove(e)

def update_status():
    will_bars = int(will_to_become_star * 18)
    notice_bars = int(escape_noticing * 18)
    pull_bars = int(inward_pull * 38)
    heat_bars = int(returned_heat * 18)
    cycle_bars = int((cycle_time / cycle_duration) * 18)
    energy_bars = int(cycle_energy * 18)

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)
    pull_bar = "█" * min(pull_bars, 18) + "░" * max(0, 18 - pull_bars)
    heat_bar = "█" * heat_bars + "░" * (18 - heat_bars)
    cycle_bar = "█" * cycle_bars + "░" * (18 - cycle_bars)
    energy_bar = "█" * energy_bars + "░" * (18 - energy_bars)

    status_label.text = (
        f"cycle {cycle_number}: {cycle_phase.upper()} [{cycle_bar}]\n"
        f"cycle energy: {cycle_energy:0.2f} [{energy_bar}]\n"
        f"will: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"weak inward pull: {inward_pull:0.2f} [{pull_bar[:18]}]\n"
        f"returned heat: {returned_heat:0.2f} [{heat_bar}]\n"
        f"escaped: {escaped_spark_count} | bent: {bent_spark_count} | returns: {return_reward_count}\n"
        "state: rhythmic learning, not yet self-contained"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00030, 0.0, 0.72)

    update_cycle()
    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_return_embers()
    update_status()
