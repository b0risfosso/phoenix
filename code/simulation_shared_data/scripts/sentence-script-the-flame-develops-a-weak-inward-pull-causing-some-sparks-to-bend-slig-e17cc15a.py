"""
Fire That Wants To Become A Star — Iteration 3
Weak Inward Pull

Story:
The flame is still small. It remembers where sparks disappear, and now it develops
its first correction: a weak inward pull. Some sparks still escape upward, but some
bend slightly back toward the flame before fading.

This is not full containment yet.
There is no stable core, no orbiting spark system, no smoke boundary, and no flame bands.

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
scene.title = "Fire That Wants To Become A Star — Weak Inward Pull"
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

# New visual: a faint inward field ring around the flame.
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
MAX_MEMORY_MARKS = 80

for _ in range(20):
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
        "bendable": random.random() < 0.45,
        "return_glow": 0.0,
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
    text="A small flame learns its first inward pull",
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

will_to_become_star = 0.20
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

# New state: the first corrective force.
inward_pull = 0.08
manual_pull_boost = 0.0
bent_spark_count = 0

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
    p["bendable"] = random.random() < 0.45
    p["return_glow"] = 0.0

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.030, 0.0, 1.0)

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

def reset_memory():
    global escape_noticing, escaped_spark_count, bent_spark_count
    escape_noticing = 0.0
    escaped_spark_count = 0
    bent_spark_count = 0
    for m in memory_marks:
        m["dot"].visible = False
        m["stroke"].visible = False
    memory_marks.clear()

def reset_simulation():
    global t, will_to_become_star, breath, inward_pull, manual_pull_boost
    t = 0.0
    will_to_become_star = 0.20
    breath = 0.0
    inward_pull = 0.08
    manual_pull_boost = 0.0
    reset_memory()
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
    global inward_pull, manual_pull_boost, escape_noticing

    # The more the flame notices escape, the more it attempts a weak inward correction.
    # It remains weak in this iteration.
    target_pull = 0.05 + 0.22 * escape_noticing + 0.10 * will_to_become_star + manual_pull_boost
    inward_pull += (target_pull - inward_pull) * 0.018
    inward_pull = clamp(inward_pull, 0.02, 0.42)

    # The manual boost fades quickly.
    manual_pull_boost *= 0.94

    # Noticing fades slowly unless sparks keep escaping.
    escape_noticing = clamp(escape_noticing - 0.00032, 0.0, 1.0)

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    notice_tremble = 0.022 * escape_noticing * math.sin(t * 14.0)

    # The flame is still small, but now it narrows slightly when it pulls inward.
    height = 0.58 + 0.16 * flicker + 0.16 * will_to_become_star + 0.18 * breath
    width = 0.21 + 0.030 * math.sin(t * 7.0) - 0.035 * inward_pull

    flame_base.radius = 0.16 + 0.04 * flicker + 0.018 * inward_pull
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble,
        0.17,
        0.025 * math.cos(t * 4.4)
    )
    flame_base.color = vector(1.0, 0.23 + 0.14 * will_to_become_star + 0.10 * inward_pull, 0.03)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = clamp(width, 0.13, 0.24)
    flame_tip.color = vector(1.0, 0.42 + 0.18 * will_to_become_star + 0.10 * inward_pull, 0.06)

    inner_flame.pos = flame_base.pos + vector(0, 0.12, 0)
    inner_flame.axis = vector(
        0.025 * math.sin(t * 8.0) + notice_tremble * 0.5,
        height * 0.68,
        0.025 * math.cos(t * 7.5)
    )
    inner_flame.radius = flame_tip.radius * 0.48
    inner_flame.color = vector(1.0, 0.82 + 0.10 * will_to_become_star + 0.05 * inward_pull, 0.22)

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(1.0, 0.36 + 0.28 * will_to_become_star + 0.15 * inward_pull, 0.08)

    desired_star.opacity = 0.13 + 0.20 * will_to_become_star + 0.05 * slow_pulse
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.009 * will_to_become_star
    will_line.color = vector(1.0, 0.46 + 0.30 * will_to_become_star, 0.04)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.22 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.005 * escape_noticing
    escape_column.color = vector(1.0, 0.40 + 0.28 * escape_noticing, 0.05)

    # The inward field is faint and incomplete.
    inward_field_ring.pos = vector(0, 0.78 + 0.05 * math.sin(t * 2.0), 0)
    inward_field_ring.radius = 0.62 + 0.16 * math.sin(t * 3.0)
    inward_field_ring.thickness = 0.006 + 0.020 * inward_pull
    inward_field_ring.opacity = 0.04 + 0.26 * inward_pull

    breath *= 0.94

def update_sparks():
    global bent_spark_count

    flame_center = flame_base.pos + vector(0, 0.35, 0)

    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        # Sparks still have an upward bias.
        upward_lift = vector(0, 0.12 * will_to_become_star, 0)

        # New behavior:
        # Some sparks are bendable. They receive a weak inward/downward force after
        # rising above the flame. This curves their path but usually does not save them yet.
        rel_to_flame = flame_center - obj.pos
        distance = mag(rel_to_flame) + 0.001
        pull_zone = 0.45 < obj.pos.y < 2.15

        if p["bendable"] and pull_zone:
            pull_strength = inward_pull * (0.35 + 0.65 * escape_noticing) / (0.75 + distance)
            inward_force = safe_norm(rel_to_flame) * pull_strength
            downward_memory = vector(0, -0.04 * inward_pull * escape_noticing, 0)
            p["vel"] += (inward_force + downward_memory) * dt

            # Count a spark once when its upward motion has been visibly bent.
            if p["vel"].y < 0.22 and p["return_glow"] <= 0.0:
                bent_spark_count += 1
                p["return_glow"] = 1.0

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
        obj.radius = clamp(0.017 + 0.020 * p["return_glow"], 0.012, 0.055)
        obj.color = vector(
            1.0,
            clamp(0.48 + 0.30 * p["return_glow"] + 0.20 * random.random(), 0.0, 1.0),
            0.07
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
        m["dot"].opacity = clamp((1.0 - frac) * (0.14 + 0.34 * escape_noticing), 0.0, 0.40)

        pos = m["dot"].pos
        length = 0.20 + 0.30 * (1.0 - frac)

        # Strokes now angle faintly back toward the flame center, visualizing the
        # first idea of return.
        toward_flame = safe_norm(flame_base.pos + vector(0, 0.25, 0) - pos)
        end_pos = pos - vector(0, length, 0) + toward_flame * (0.14 * inward_pull)

        m["stroke"].clear()
        m["stroke"].append(pos=pos)
        m["stroke"].append(pos=end_pos)
        m["stroke"].opacity = clamp((1.0 - frac) * (0.10 + 0.24 * escape_noticing), 0.0, 0.32)

        if frac >= 1.0:
            m["dot"].visible = False
            m["stroke"].visible = False
            to_remove.append(m)

    for m in to_remove:
        if m in memory_marks:
            memory_marks.remove(m)

def update_status():
    will_bars = int(will_to_become_star * 18)
    notice_bars = int(escape_noticing * 18)
    pull_bars = int(inward_pull * 42)

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)
    pull_bar = "█" * pull_bars + "░" * max(0, 18 - pull_bars)

    status_label.text = (
        f"will to become a star: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing upward escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"weak inward pull: {inward_pull:0.2f} [{pull_bar[:18]}]\n"
        f"escaped sparks remembered: {escaped_spark_count} | bent sparks: {bent_spark_count}\n"
        "state: first correction, not yet self-contained"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt

    # The will grows slowly, but this remains early-stage.
    will_to_become_star = clamp(will_to_become_star + 0.00034, 0.0, 0.72)

    update_learning_state()
    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_status()
