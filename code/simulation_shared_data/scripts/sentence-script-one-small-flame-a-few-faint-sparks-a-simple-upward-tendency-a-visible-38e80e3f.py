"""
Fire That Wants To Become A Star — Initial Simulation

This is the first iteration only.

The simulation intentionally begins small:
- one small flame
- a few faint sparks
- a simple upward tendency
- a visible "will to become a star"

It does NOT yet form a stable core, orbiting sparks, smoke boundary, or flame bands.
Those are later iterations.

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

# -----------------------------
# Scene
# -----------------------------
scene.title = "Fire That Wants To Become A Star — Initial Seed"
scene.width = 1100
scene.height = 700
scene.background = vector(0.96, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.range = 5.5
scene.center = vector(0, 1.2, 0)

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

# A faint imagined star above the flame: not reached yet.
desired_star = sphere(
    pos=vector(0, 3.15, 0),
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

# -----------------------------
# Small sparks
# -----------------------------
sparks = []
for _ in range(16):
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

# -----------------------------
# Labels
# -----------------------------
title_label = label(
    pos=vector(0, 4.1, 0),
    text="A small flame with a will to become a star",
    height=16,
    box=False,
    color=vector(0.15, 0.12, 0.08)
)

status_label = label(
    pos=vector(0, 3.72, 0),
    text="",
    height=12,
    box=False,
    color=vector(0.20, 0.15, 0.08)
)

help_label = label(
    pos=vector(-3.7, 4.55, 0),
    text="H help | P pause | R reset | W strengthen will | Space breath upward",
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

# The first seed's central variable.
# It is desire, not achievement.
will_to_become_star = 0.18
breath = 0.0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def reset_spark(p):
    p["obj"].pos = vector(
        random.uniform(-0.12, 0.12),
        random.uniform(0.25, 0.55),
        random.uniform(-0.12, 0.12)
    )
    p["obj"].opacity = 0.85
    p["vel"] = vector(
        random.uniform(-0.10, 0.10),
        random.uniform(0.35, 0.85),
        random.uniform(-0.10, 0.10)
    )
    p["age"] = 0.0
    p["life"] = random.uniform(1.4, 2.8)

def reset_simulation():
    global t, will_to_become_star, breath
    t = 0.0
    will_to_become_star = 0.18
    breath = 0.0
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

    # The will makes the flame lean upward and glow slightly more,
    # but it remains only a small flame.
    height = 0.58 + 0.18 * flicker + 0.22 * will_to_become_star + 0.20 * breath
    width = 0.21 + 0.035 * math.sin(t * 7.0)

    flame_base.radius = 0.16 + 0.04 * flicker
    flame_base.pos = vector(0.025 * math.sin(t * 5.0), 0.17, 0.025 * math.cos(t * 4.4))
    flame_base.color = vector(1.0, 0.23 + 0.16 * will_to_become_star, 0.03)

    flame_tip.pos = flame_base.pos + vector(0, 0.08, 0)
    flame_tip.axis = vector(
        0.04 * math.sin(t * 6.0),
        height,
        0.04 * math.cos(t * 5.3)
    )
    flame_tip.radius = width
    flame_tip.color = vector(1.0, 0.42 + 0.22 * will_to_become_star, 0.06)

    inner_flame.pos = flame_base.pos + vector(0, 0.12, 0)
    inner_flame.axis = vector(
        0.025 * math.sin(t * 8.0),
        height * 0.68,
        0.025 * math.cos(t * 7.5)
    )
    inner_flame.radius = width * 0.48
    inner_flame.color = vector(1.0, 0.82 + 0.12 * will_to_become_star, 0.22)

    flame_light.pos = flame_base.pos + vector(0, 0.45, 0)
    flame_light.color = vector(1.0, 0.36 + 0.34 * will_to_become_star, 0.08)

    # The imagined star brightens only as an aspiration.
    desired_star.opacity = 0.13 + 0.24 * will_to_become_star + 0.05 * slow_pulse
    desired_star.radius = 0.16 + 0.08 * will_to_become_star + 0.02 * slow_pulse

    will_line.clear()
    will_line.append(pos=flame_tip.pos + flame_tip.axis)
    will_line.append(pos=desired_star.pos)
    will_line.radius = 0.006 + 0.012 * will_to_become_star
    will_line.color = vector(1.0, 0.46 + 0.34 * will_to_become_star, 0.04)

    breath *= 0.94

def update_sparks():
    for p in sparks:
        obj = p["obj"]
        p["age"] += dt

        # Sparks still escape upward. This first iteration has not learned containment.
        desire_pull = vector(0, 0.12 * will_to_become_star, 0)
        p["vel"] += desire_pull * dt
        p["vel"] += vector(
            random.uniform(-0.018, 0.018),
            random.uniform(-0.004, 0.018),
            random.uniform(-0.018, 0.018)
        )
        p["vel"] *= 0.985

        obj.pos += p["vel"] * dt
        obj.opacity = clamp(1.0 - p["age"] / p["life"], 0.0, 0.9)

        if p["age"] > p["life"] or obj.pos.y > 2.1:
            reset_spark(p)

def update_status():
    bars = int(will_to_become_star * 20)
    will_bar = "█" * bars + "░" * (20 - bars)
    status_label.text = (
        f"will to become a star: {will_to_become_star:0.2f}\n"
        f"[{will_bar}]\n"
        "state: small flame, not yet self-contained"
    )

while True:
    rate(60)

    if paused:
        continue

    t += dt

    # The will grows slowly on its own, but remains modest in this first seed.
    will_to_become_star = clamp(will_to_become_star + 0.00045, 0.0, 0.72)

    update_flame_shape()
    update_sparks()
    update_status()
