"""
Fire That Wants To Become A Star — Iteration 4
Returning Heat Strengthens the Base

Story:
The flame is still small. It has noticed that sparks escape upward, and it has
developed a weak inward pull. Now it learns its first reward:

When bent sparks pass close to the flame again, the base briefly brightens.
This teaches the flame that returning heat can strengthen it.

This is still early-stage:
- no stable glowing core
- no smoke boundary
- no orbiting spark system
- no rotating flame bands

Controls:
    H       show/hide help
    P       pause/resume
    R       reset
    W       strengthen the will to become a star
    Space   give the flame a small upward breath
    I       briefly strengthen inward pull
"""

from vpython import *
import random
import math

# -----------------------------
# Scene
# -----------------------------
scene.title = "Fire That Wants To Become A Star — Returning Heat"
scene.width = 1100
scene.height = 700
scene.background = vector(0.96, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.range = 5.5
scene.center = vector(0, 1.35, 0)

ground = box(
    pos=vector(0, -0.04, 0),
    size=vector(8, 0.06, 8),
    color=vector(0.78, 0.73, 0.65)
)

charred_patch = cylinder(
    pos=vector(0, 0.005, 0),
    axis=vector(0, 0.01, 0),
    radius=0.55,
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

# New: a small base glow that brightens when returning sparks pass close.
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
    pos=vector(0, 3.25, 0),
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

# Faint inward field ring around the flame.
inward_field_ring = ring(
    pos=vector(0, 0.78, 0),
    axis=vector(0, 1, 0),
    radius=0.78,
    thickness=0.01,
    color=vector(1.0, 0.38, 0.05),
    opacity=0.10,
    emissive=True
)

# -----------------------------
# Sparks and memory marks
# -----------------------------
sparks = []
memory_marks = []
return_embers = []
MAX_MEMORY_MARKS = 80
MAX_RETURN_EMBERS = 45

for _ in range(22):
    s = sphere(
        pos=vector(random.uniform(-0.12, 0.12), random.uniform(0.3, 0.65), random.uniform(-0.12, 0.12)),
        radius=random.uniform(0.015, 0.035),
        color=vector(1.0, random.uniform(0.45, 0.85), 0.08),
        emissive=True,
        opacity=0.85
    )
    sparks.append({
        "obj": s,
        "vel": vector(random.uniform(-0.10, 0.10), random.uniform(0.35, 0.85), random.uniform(-0.10, 0.10)),
        "age": random.random() * 2.0,
        "life": random.uniform(1.5, 3.0),
        "bendable": random.random() < 0.48,
        "return_glow": 0.0,
        "has_bent": False,
        "rewarded": False,
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
    pos=vector(0, 4.2, 0),
    text="A small flame learns that returning heat strengthens it",
    height=16,
    box=False,
    color=vector(0.15, 0.12, 0.08)
)

status_label = label(
    pos=vector(0, 3.78, 0),
    text="",
    height=12,
    box=False,
    color=vector(0.20, 0.15, 0.08)
)

help_label = label(
    pos=vector(-3.7, 4.65, 0),
    text="H help | P pause | R reset | W strengthen will | Space breath | I inward pull",
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

will_to_become_star = 0.22
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

inward_pull = 0.09
manual_pull_boost = 0.0
bent_spark_count = 0

# New learning signal.
returned_heat = 0.0
return_reward_count = 0
base_brighten = 0.0

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
        random.uniform(0.35, 0.85),
        random.uniform(-0.10, 0.10)
    )
    p["age"] = 0.0
    p["life"] = random.uniform(1.5, 3.0)
    p["bendable"] = random.random() < 0.48
    p["return_glow"] = 0.0
    p["has_bent"] = False
    p["rewarded"] = False

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.028, 0.0, 1.0)

    dot = sphere(
        pos=pos,
        radius=random.uniform(0.035, 0.065),
        color=vector(1.0, 0.42, 0.04),
        opacity=0.34,
        emissive=True
    )

    stroke_length = random.uniform(0.18, 0.42)
    stroke = curve(
        pos=[pos, pos - vector(0, stroke_length, 0)],
        radius=random.uniform(0.004, 0.008),
        color=vector(1.0, 0.36, 0.04)
    )
    stroke.opacity = 0.25

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
    global returned_heat, return_reward_count, base_brighten, inward_pull

    p["rewarded"] = True
    p["return_glow"] = 1.0

    return_reward_count += 1
    returned_heat = clamp(returned_heat + 0.055, 0.0, 1.0)
    base_brighten = clamp(base_brighten + 0.50, 0.0, 1.0)

    # Reward slightly strengthens the weak pull, but not enough for full containment.
    inward_pull = clamp(inward_pull + 0.012, 0.02, 0.46)

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
    t = 0.0
    will_to_become_star = 0.22
    breath = 0.0
    inward_pull = 0.09
    manual_pull_boost = 0.0
    reset_memory_and_rewards()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath, manual_pull_boost

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

scene.bind("keydown", keydown)

def update_learning_state():
    global inward_pull, manual_pull_boost, escape_noticing, returned_heat, base_brighten

    # The flame still learns mostly from loss, but now returning heat reinforces the pull.
    target_pull = (
        0.05
        + 0.18 * escape_noticing
        + 0.09 * will_to_become_star
        + 0.16 * returned_heat
        + manual_pull_boost
    )
    inward_pull += (target_pull - inward_pull) * 0.018
    inward_pull = clamp(inward_pull, 0.02, 0.46)

    manual_pull_boost *= 0.94
    escape_noticing = clamp(escape_noticing - 0.00030, 0.0, 1.0)
    returned_heat = clamp(returned_heat - 0.00022, 0.0, 1.0)
    base_brighten = clamp(base_brighten * 0.945, 0.0, 1.0)

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    notice_tremble = 0.020 * escape_noticing * math.sin(t * 14.0)

    # The base brightens and thickens briefly when heat returns.
    heat_pulse = base_brighten
    height = 0.58 + 0.16 * flicker + 0.15 * will_to_become_star + 0.18 * breath + 0.06 * heat_pulse
    width = 0.21 + 0.030 * math.sin(t * 7.0) - 0.030 * inward_pull + 0.035 * heat_pulse

    flame_base.radius = 0.16 + 0.04 * flicker + 0.018 * inward_pull + 0.09 * heat_pulse
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble,
        0.17,
        0.025 * math.cos(t * 4.4)
    )
    flame_base.color = vector(
        1.0,
        clamp(0.24 + 0.14 * will_to_become_star + 0.12 * inward_pull + 0.45 * heat_pulse, 0.0, 1.0),
        clamp(0.03 + 0.16 * heat_pulse, 0.0, 1.0)
    )

    base_heat_glow.pos = flame_base.pos + vector(0, 0.02, 0)
    base_heat_glow.radius = 0.22 + 0.36 * heat_pulse + 0.05 * returned_heat
    base_heat_glow.opacity = 0.06 + 0.46 * heat_pulse + 0.10 * returned_heat
    base_heat_glow.color = vector(1.0, 0.45 + 0.36 * heat_pulse, 0.05 + 0.13 * heat_pulse)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = clamp(width, 0.13, 0.28)
    flame_tip.color = vector(
        1.0,
        clamp(0.42 + 0.16 * will_to_become_star + 0.08 * inward_pull + 0.22 * heat_pulse, 0.0, 1.0),
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
        clamp(0.82 + 0.08 * will_to_become_star + 0.08 * heat_pulse, 0.0, 1.0),
        clamp(0.22 + 0.08 * heat_pulse, 0.0, 1.0)
    )

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(
        1.0,
        clamp(0.36 + 0.26 * will_to_become_star + 0.12 * inward_pull + 0.26 * heat_pulse, 0.0, 1.0),
        0.08
    )

    desired_star.opacity = 0.13 + 0.19 * will_to_become_star + 0.05 * slow_pulse
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.009 * will_to_become_star
    will_line.color = vector(1.0, 0.46 + 0.28 * will_to_become_star, 0.04)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.22 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.005 * escape_noticing
    escape_column.color = vector(1.0, 0.40 + 0.26 * escape_noticing, 0.05)

    inward_field_ring.pos = vector(0, 0.78 + 0.05 * math.sin(t * 2.0), 0)
    inward_field_ring.radius = 0.62 + 0.16 * math.sin(t * 3.0)
    inward_field_ring.thickness = 0.006 + 0.020 * inward_pull
    inward_field_ring.opacity = 0.04 + 0.22 * inward_pull + 0.08 * returned_heat

    breath *= 0.94

def update_sparks():
    global bent_spark_count

    flame_center = flame_base.pos + vector(0, 0.35, 0)
    reward_zone_center = flame_base.pos + vector(0, 0.28, 0)

    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        upward_lift = vector(0, 0.12 * will_to_become_star, 0)

        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.15

        if p["bendable"] and pull_zone:
            pull_strength = inward_pull * (0.33 + 0.50 * escape_noticing + 0.35 * returned_heat) / (0.75 + distance)
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.04 * inward_pull * (escape_noticing + returned_heat), 0)
            p["vel"] += (inward_force + downward_memory) * dt

            # Mark spark as bent once its upward escape has visibly slowed.
            if p["vel"].y < 0.24 and not p["has_bent"]:
                bent_spark_count += 1
                p["has_bent"] = True
                p["return_glow"] = 0.75

        # New reward condition:
        # A spark that has already bent passes close to the flame base again.
        return_distance = mag(obj.pos - reward_zone_center)
        if p["has_bent"] and not p["rewarded"] and return_distance < 0.42 and obj.pos.y < 0.82:
            reward_returning_spark(p)

        p["vel"] += upward_lift * dt
        p["vel"] += vector(
            random.uniform(-0.018, 0.018),
            random.uniform(-0.004, 0.018),
            random.uniform(-0.018, 0.018)
        )
        p["vel"] *= 0.985

        obj.pos += p["vel"] * dt
        p["return_glow"] *= 0.94

        age_fade = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)
        obj.opacity = clamp(age_fade + 0.25 * p["return_glow"], 0.0, 1.0)
        obj.radius = clamp(0.017 + 0.021 * p["return_glow"], 0.012, 0.058)
        obj.color = vector(
            1.0,
            clamp(0.48 + 0.32 * p["return_glow"] + 0.18 * random.random(), 0.0, 1.0),
            clamp(0.07 + 0.10 * p["return_glow"], 0.0, 1.0)
        )

        escaped_high = obj.pos.y > 2.1
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
        m["dot"].opacity = clamp((1.0 - frac) * (0.14 + 0.32 * escape_noticing), 0.0, 0.40)

        pos = m["dot"].pos
        length = 0.20 + 0.30 * (1.0 - frac)
        toward_flame = safe_norm(flame_base.pos + vector(0, 0.25, 0) - pos)
        end_pos = pos - vector(0, length, 0) + toward_flame * (0.14 * inward_pull + 0.10 * returned_heat)

        m["stroke"].clear()
        m["stroke"].append(pos=pos)
        m["stroke"].append(pos=end_pos)
        m["stroke"].opacity = clamp((1.0 - frac) * (0.10 + 0.22 * escape_noticing), 0.0, 0.32)

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
    pull_bars = int(inward_pull * 40)
    heat_bars = int(returned_heat * 18)

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)
    pull_bar = "█" * min(pull_bars, 18) + "░" * max(0, 18 - pull_bars)
    heat_bar = "█" * heat_bars + "░" * (18 - heat_bars)

    status_label.text = (
        f"will to become a star: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing upward escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"weak inward pull: {inward_pull:0.2f} [{pull_bar[:18]}]\n"
        f"returned heat: {returned_heat:0.2f} [{heat_bar}]\n"
        f"escaped remembered: {escaped_spark_count} | bent: {bent_spark_count} | returns: {return_reward_count}\n"
        "state: first reward loop, not yet self-contained"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00032, 0.0, 0.72)

    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_return_embers()
    update_status()
