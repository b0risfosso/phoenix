"""
Fire That Wants To Become A Star — Iteration 2
Memory of Escaping Sparks

The flame is still only a small flame with a will to become a star.
It has not learned containment yet.

New behavior:
The flame begins to notice that its sparks always escape upward.
Whenever a spark disappears above the flame, a faint memory mark appears at that
disappearance point. These marks slowly fade, forming a visible record of escape.

Controls:
    H       show/hide help
    P       pause/resume
    R       reset
    W       strengthen the will to become a star
    Space   give the flame a small upward breath
"""

from vpython import *
import random
import math

scene.title = "Fire That Wants To Become A Star — Memory of Escape"
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

sparks = []
memory_marks = []
MAX_MEMORY_MARKS = 80

for _ in range(18):
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
        "life": random.uniform(1.4, 2.8),
    })

escape_column = curve(
    pos=[vector(0, 0.5, 0), vector(0, 2.45, 0)],
    radius=0.006,
    color=vector(1.0, 0.48, 0.08)
)
escape_column.opacity = 0.18

title_label = label(
    pos=vector(0, 4.2, 0),
    text="A small flame begins to notice where its sparks disappear",
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
    text="H help | P pause | R reset | W strengthen will | Space breath upward",
    height=10,
    box=False,
    align="left",
    color=vector(0.12, 0.12, 0.12)
)

t = 0.0
dt = 0.025
paused = False
show_help = True

will_to_become_star = 0.18
breath = 0.0
escape_noticing = 0.0
escaped_spark_count = 0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def reset_spark(p):
    p["obj"].pos = vector(
        random.uniform(-0.12, 0.12),
        random.uniform(0.25, 0.55),
        random.uniform(-0.12, 0.12)
    )
    p["obj"].opacity = 0.85
    p["obj"].visible = True
    p["vel"] = vector(
        random.uniform(-0.10, 0.10),
        random.uniform(0.35, 0.85),
        random.uniform(-0.10, 0.10)
    )
    p["age"] = 0.0
    p["life"] = random.uniform(1.4, 2.8)

def add_memory_mark(pos):
    global escaped_spark_count, escape_noticing

    escaped_spark_count += 1
    escape_noticing = clamp(escape_noticing + 0.035, 0.0, 1.0)

    dot = sphere(
        pos=pos,
        radius=random.uniform(0.035, 0.065),
        color=vector(1.0, 0.42, 0.04),
        opacity=0.36,
        emissive=True
    )

    stroke_length = random.uniform(0.18, 0.42)
    stroke = curve(
        pos=[pos, pos - vector(0, stroke_length, 0)],
        radius=random.uniform(0.004, 0.008),
        color=vector(1.0, 0.36, 0.04)
    )
    stroke.opacity = 0.28

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
    global escape_noticing, escaped_spark_count
    escape_noticing = 0.0
    escaped_spark_count = 0
    for m in memory_marks:
        m["dot"].visible = False
        m["stroke"].visible = False
    memory_marks.clear()

def reset_simulation():
    global t, will_to_become_star, breath
    t = 0.0
    will_to_become_star = 0.18
    breath = 0.0
    reset_memory()
    for p in sparks:
        reset_spark(p)

def keydown(evt):
    global paused, show_help, will_to_become_star, breath

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

scene.bind("keydown", keydown)

def update_flame_shape():
    global breath

    flicker = 0.5 + 0.5 * math.sin(t * 9.0) + random.uniform(-0.08, 0.08)
    slow_pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    notice_tremble = 0.025 * escape_noticing * math.sin(t * 14.0)

    height = 0.58 + 0.18 * flicker + 0.18 * will_to_become_star + 0.20 * breath
    width = 0.21 + 0.035 * math.sin(t * 7.0)

    flame_base.radius = 0.16 + 0.04 * flicker
    flame_base.pos = vector(
        0.025 * math.sin(t * 5.0) + notice_tremble,
        0.17,
        0.025 * math.cos(t * 4.4)
    )
    flame_base.color = vector(1.0, 0.23 + 0.16 * will_to_become_star, 0.03)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0) + notice_tremble,
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = width
    flame_tip.color = vector(1.0, 0.42 + 0.22 * will_to_become_star, 0.06)

    inner_flame.pos = flame_base.pos + vector(0, 0.12, 0)
    inner_flame.axis = vector(
        0.025 * math.sin(t * 8.0) + notice_tremble * 0.5,
        height * 0.68,
        0.025 * math.cos(t * 7.5)
    )
    inner_flame.radius = width * 0.48
    inner_flame.color = vector(1.0, 0.82 + 0.12 * will_to_become_star, 0.22)

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(1.0, 0.36 + 0.34 * will_to_become_star, 0.08)

    desired_star.opacity = 0.13 + 0.22 * will_to_become_star + 0.05 * slow_pulse
    desired_star.radius = 0.16 + 0.07 * will_to_become_star + 0.02 * slow_pulse

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.010 * will_to_become_star
    will_line.color = vector(1.0, 0.46 + 0.34 * will_to_become_star, 0.04)

    escape_column.clear()
    escape_column.append(pos=vector(0, 0.45, 0))
    escape_column.append(pos=vector(0, 2.50 + 0.25 * escape_noticing, 0))
    escape_column.radius = 0.004 + 0.006 * escape_noticing
    escape_column.color = vector(1.0, 0.40 + 0.30 * escape_noticing, 0.05)

    breath *= 0.94

def update_sparks():
    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        desire_lift = vector(0, 0.12 * will_to_become_star, 0)
        p["vel"] += desire_lift * dt
        p["vel"] += vector(
            random.uniform(-0.018, 0.018),
            random.uniform(-0.004, 0.018),
            random.uniform(-0.018, 0.018)
        )
        p["vel"] *= 0.985

        obj.pos += p["vel"] * dt
        obj.opacity = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)

        escaped_high = obj.pos.y > 2.1
        burned_out_high = p["age"] > p["life"] and obj.pos.y > 1.05

        if escaped_high or burned_out_high:
            add_memory_mark(vector(obj.pos.x, obj.pos.y, obj.pos.z))
            reset_spark(p)
        elif p["age"] > p["life"]:
            reset_spark(p)

def update_memory_marks():
    global escape_noticing

    escape_noticing = clamp(escape_noticing - 0.00035, 0.0, 1.0)

    to_remove = []
    for m in memory_marks:
        m["age"] += dt
        frac = m["age"] / m["life"]

        m["dot"].pos += m["drift"]
        m["dot"].radius = m["base_radius"] * (1.0 + 0.45 * math.sin(t * 3.0 + m["age"]))
        m["dot"].opacity = clamp((1.0 - frac) * (0.16 + 0.36 * escape_noticing), 0.0, 0.42)

        pos = m["dot"].pos
        length = 0.20 + 0.30 * (1.0 - frac)
        m["stroke"].clear()
        m["stroke"].append(pos=pos)
        m["stroke"].append(pos=pos - vector(0, length, 0))
        m["stroke"].opacity = clamp((1.0 - frac) * (0.12 + 0.24 * escape_noticing), 0.0, 0.34)

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

    will_bar = "█" * will_bars + "░" * (18 - will_bars)
    notice_bar = "█" * notice_bars + "░" * (18 - notice_bars)

    status_label.text = (
        f"will to become a star: {will_to_become_star:0.2f} [{will_bar}]\n"
        f"noticing upward escape: {escape_noticing:0.2f} [{notice_bar}]\n"
        f"escaped sparks remembered: {escaped_spark_count}\n"
        "state: small flame with memory, not yet self-contained"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt
    will_to_become_star = clamp(will_to_become_star + 0.00038, 0.0, 0.72)

    update_flame_shape()
    update_sparks()
    update_memory_marks()
    update_status()
