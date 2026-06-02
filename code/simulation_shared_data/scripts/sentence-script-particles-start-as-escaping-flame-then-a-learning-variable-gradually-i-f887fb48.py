"""
Fire That Learns To Hold Itself Together
VPython simulation

Story:
A small flame begins by rising and dispersing. It wants to become a star, but every part
of it escapes upward. Over time, a learning variable increases inward curl. Heat curls
back toward the center, sparks begin to orbit instead of fleeing, and smoke forms a
boundary layer. Completion occurs when a stable glowing core is surrounded by rotating
flame bands.

Controls:
    H       show/hide help
    P       pause/resume
    R       reset simulation
    L       toggle learning on/off
    F       feed the core with extra fuel/heat
    1       weak containment
    2       medium containment
    3       strong containment
    W/A/S/D move the camera focus point
    Space   move focus up
    C       move focus down
    J/L     rotate camera around focus
    I/K     tilt camera up/down
    +/-     zoom camera
"""

from vpython import *
import random
import math

# -----------------------------
# Scene setup
# -----------------------------
scene.title = "Fire That Learns To Hold Itself Together"
scene.width = 1150
scene.height = 720
scene.background = vector(0.93, 0.96, 1.0)
scene.forward = vector(-0.35, -0.32, -1.0)
scene.range = 9.0

# Ground and simple environment
ground = box(
    pos=vector(0, -0.06, 0),
    size=vector(16, 0.08, 16),
    color=vector(0.78, 0.74, 0.66),
)
birth_ring = ring(
    pos=vector(0, 0.04, 0),
    axis=vector(0, 1, 0),
    radius=1.0,
    thickness=0.035,
    color=vector(0.55, 0.42, 0.30),
)

# -----------------------------
# Visual groups
# -----------------------------
flames = []
sparks = []
smoke = []
flame_bands = []

# Core/star objects
core = sphere(
    pos=vector(0, 0.85, 0),
    radius=0.28,
    color=vector(1.0, 0.42, 0.08),
    emissive=True,
)
core_light = local_light(pos=core.pos, color=vector(1.0, 0.55, 0.25))
core_halo = sphere(
    pos=core.pos,
    radius=0.62,
    color=vector(1.0, 0.66, 0.16),
    opacity=0.18,
    emissive=True,
)

# Smoke boundary shell
boundary_shell = sphere(
    pos=core.pos,
    radius=2.4,
    color=vector(0.55, 0.56, 0.58),
    opacity=0.04,
)

# Flame bands: rotating rings around final core
for i in range(4):
    band = ring(
        pos=core.pos,
        axis=norm(vector(random.uniform(-0.4, 0.4), 1.0, random.uniform(-0.4, 0.4))),
        radius=1.1 + i * 0.22,
        thickness=0.025,
        color=vector(1.0, 0.35 + 0.12 * i, 0.06),
        opacity=0.0,
        emissive=True,
    )
    flame_bands.append({"obj": band, "spin": random.choice([-1, 1]) * (0.45 + i * 0.13), "phase": random.random() * 6.28})

# -----------------------------
# Labels and UI
# -----------------------------
status = label(
    pos=vector(0, 3.9, 0),
    text="",
    height=15,
    box=False,
    color=vector(0.15, 0.12, 0.08),
)

help_label = label(
    pos=vector(-6.6, 4.6, 0),
    text=(
        "H help | P pause | R reset | L learning | F feed core\n"
        "1/2/3 containment | WASD/Space/C pan | J/L rotate | I/K tilt | +/- zoom"
    ),
    height=11,
    box=False,
    align="left",
    color=vector(0.12, 0.12, 0.12),
)

# -----------------------------
# Simulation state
# -----------------------------
paused = False
show_help = True
learning_enabled = True
manual_containment = 0.0
t = 0.0
dt = 0.025
round_age = 0.0
heat_memory = 0.0
containment = 0.0
completion = 0.0
core_heat = 0.0
phase_name = "escaping flame"

camera_focus = vector(0, 1.0, 0)
keys_down = set()

MAX_FLAMES = 120
MAX_SPARKS = 85
MAX_SMOKE = 95

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def rand_vec(scale=1.0):
    return vector(random.uniform(-scale, scale), random.uniform(-scale, scale), random.uniform(-scale, scale))

def flat_tangent(v):
    # Tangent around the vertical axis, used for orbit/curl.
    return vector(-v.z, 0, v.x)

def heat_color(energy, age_factor=1.0):
    e = clamp(energy, 0.0, 1.0)
    # Red/orange/yellow/white transition.
    return vector(
        clamp(0.55 + 0.55 * e, 0, 1),
        clamp(0.10 + 0.80 * e * age_factor, 0, 1),
        clamp(0.02 + 0.25 * e * e, 0, 1),
    )

def reset_particle(p, kind="flame"):
    angle = random.random() * 2 * math.pi
    r = random.uniform(0.05, 0.55)
    p["pos"] = vector(math.cos(angle) * r, random.uniform(0.05, 0.45), math.sin(angle) * r)
    p["vel"] = vector(
        random.uniform(-0.35, 0.35),
        random.uniform(1.2, 2.2),
        random.uniform(-0.35, 0.35),
    )
    p["age"] = 0.0
    p["life"] = random.uniform(2.3, 4.8)
    p["energy"] = random.uniform(0.55, 1.0)
    p["orbit_bias"] = random.uniform(0.4, 1.2)
    p["learned"] = False

    obj = p["obj"]
    obj.visible = True
    obj.pos = p["pos"]
    if kind == "flame":
        obj.radius = random.uniform(0.07, 0.15)
        obj.color = heat_color(p["energy"])
        obj.opacity = 0.75
    elif kind == "spark":
        obj.radius = random.uniform(0.025, 0.055)
        obj.color = vector(1.0, random.uniform(0.55, 0.90), 0.12)
        obj.opacity = 1.0
    else:
        obj.radius = random.uniform(0.08, 0.18)
        obj.color = vector(0.50, 0.51, 0.52)
        obj.opacity = 0.14

def make_flame():
    obj = sphere(pos=vector(0, 0.1, 0), radius=0.1, color=vector(1, 0.3, 0.05), emissive=True)
    p = {"obj": obj}
    reset_particle(p, "flame")
    return p

def make_spark():
    obj = sphere(pos=vector(0, 0.1, 0), radius=0.035, color=vector(1, 0.75, 0.12), emissive=True)
    tr = curve(color=vector(1, 0.55, 0.1), radius=0.007)
    p = {"obj": obj, "trail": tr}
    reset_particle(p, "spark")
    return p

def make_smoke():
    obj = sphere(pos=vector(0, 0.1, 0), radius=0.12, color=vector(0.52, 0.52, 0.52), opacity=0.12)
    p = {"obj": obj}
    reset_particle(p, "smoke")
    return p

def clear_trails():
    for p in sparks:
        p["trail"].clear()

def reset_simulation():
    global t, round_age, heat_memory, containment, completion, core_heat, phase_name, manual_containment
    t = 0.0
    round_age = 0.0
    heat_memory = 0.0
    containment = 0.0
    completion = 0.0
    core_heat = 0.0
    manual_containment = 0.0
    phase_name = "escaping flame"

    for p in flames:
        reset_particle(p, "flame")
    for p in sparks:
        p["trail"].clear()
        reset_particle(p, "spark")
    for p in smoke:
        reset_particle(p, "smoke")

    core.radius = 0.28
    core.color = vector(1.0, 0.42, 0.08)
    core.pos = vector(0, 0.85, 0)
    core_halo.pos = core.pos
    core_light.pos = core.pos
    core_halo.radius = 0.62
    core_halo.opacity = 0.18
    boundary_shell.pos = core.pos
    boundary_shell.opacity = 0.04
    boundary_shell.radius = 2.4
    for band in flame_bands:
        band["obj"].pos = core.pos
        band["obj"].opacity = 0.0

# -----------------------------
# Create particles
# -----------------------------
for _ in range(MAX_FLAMES):
    flames.append(make_flame())

for _ in range(MAX_SPARKS):
    sparks.append(make_spark())

for _ in range(MAX_SMOKE):
    smoke.append(make_smoke())

# -----------------------------
# Keyboard controls
# -----------------------------
def keydown(evt):
    global paused, show_help, learning_enabled, manual_containment, core_heat
    k = evt.key.lower()
    keys_down.add(k)

    if k == "p":
        paused = not paused
    elif k == "h":
        show_help = not show_help
        help_label.visible = show_help
    elif k == "r":
        reset_simulation()
    elif k == "l":
        learning_enabled = not learning_enabled
    elif k == "f":
        core_heat = clamp(core_heat + 0.18, 0, 1.8)
        manual_containment = clamp(manual_containment + 0.08, 0, 1.0)
    elif k == "1":
        manual_containment = 0.15
    elif k == "2":
        manual_containment = 0.45
    elif k == "3":
        manual_containment = 0.80

def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

# -----------------------------
# Camera controls
# -----------------------------
def update_camera():
    global camera_focus
    move_speed = 0.08 * scene.range
    right = norm(cross(scene.forward, vector(0, 1, 0)))
    if mag(right) < 0.001:
        right = vector(1, 0, 0)
    forward_flat = norm(vector(scene.forward.x, 0, scene.forward.z))
    if mag(forward_flat) < 0.001:
        forward_flat = vector(0, 0, -1)

    if "w" in keys_down:
        camera_focus += forward_flat * move_speed * 0.025
    if "s" in keys_down:
        camera_focus -= forward_flat * move_speed * 0.025
    if "a" in keys_down:
        camera_focus -= right * move_speed * 0.025
    if "d" in keys_down:
        camera_focus += right * move_speed * 0.025
    if " " in keys_down:
        camera_focus.y += move_speed * 0.025
    if "c" in keys_down:
        camera_focus.y -= move_speed * 0.025

    if "j" in keys_down:
        scene.forward = rotate(scene.forward, angle=0.025, axis=vector(0, 1, 0))
    if "l" in keys_down:
        scene.forward = rotate(scene.forward, angle=-0.025, axis=vector(0, 1, 0))
    if "i" in keys_down:
        scene.forward = rotate(scene.forward, angle=0.018, axis=right)
    if "k" in keys_down:
        scene.forward = rotate(scene.forward, angle=-0.018, axis=right)

    if "+" in keys_down or "=" in keys_down:
        scene.range = max(3.0, scene.range * 0.985)
    if "-" in keys_down or "_" in keys_down:
        scene.range = min(20.0, scene.range * 1.015)

    scene.center = camera_focus

# -----------------------------
# Main simulation logic
# -----------------------------
def update_learning():
    global heat_memory, containment, completion, phase_name, core_heat

    # Heat memory rises as particles repeatedly return near the core.
    near_count = 0
    orbit_count = 0

    for p in flames:
        dist = mag(p["pos"] - core.pos)
        if dist < 1.25:
            near_count += 1
        if dist < 2.1 and abs(p["vel"].y) < 1.3:
            orbit_count += 1

    for p in sparks:
        dist = mag(p["pos"] - core.pos)
        if dist < 1.65:
            near_count += 1
        if dist < 2.4 and mag(flat_tangent(p["pos"] - core.pos)) > 0.1:
            orbit_count += 1

    near_ratio = near_count / float(MAX_FLAMES + MAX_SPARKS)
    orbit_ratio = orbit_count / float(MAX_FLAMES + MAX_SPARKS)

    if learning_enabled:
        heat_memory = clamp(heat_memory + (near_ratio * 0.026 + orbit_ratio * 0.018 - 0.002), 0.0, 1.0)
    else:
        heat_memory = clamp(heat_memory - 0.0009, 0.0, 1.0)

    containment = clamp(0.12 + heat_memory * 0.85 + manual_containment * 0.35, 0.0, 1.0)
    core_heat = clamp(core_heat * 0.998 + near_ratio * 0.012 + heat_memory * 0.002, 0.0, 1.65)
    completion = clamp((heat_memory * 0.55 + containment * 0.30 + min(core_heat, 1.0) * 0.15), 0.0, 1.0)

    if completion < 0.25:
        phase_name = "escaping flame"
    elif completion < 0.50:
        phase_name = "learning inward curl"
    elif completion < 0.78:
        phase_name = "orbiting sparks and smoke boundary"
    else:
        phase_name = "stable newborn star"

def update_core_visuals():
    pulse = 0.5 + 0.5 * math.sin(t * (3.0 + completion * 3.5))
    core.radius = 0.28 + 0.34 * completion + 0.04 * pulse
    core.color = vector(
        1.0,
        clamp(0.35 + 0.48 * completion + 0.10 * pulse, 0, 1),
        clamp(0.05 + 0.22 * completion, 0, 1),
    )
    core.pos = vector(0, 0.82 + 0.18 * completion + 0.04 * math.sin(t * 1.2), 0)
    core_light.pos = core.pos
    core_light.color = vector(1.0, 0.45 + 0.35 * completion, 0.18 + 0.15 * completion)

    core_halo.pos = core.pos
    core_halo.radius = 0.70 + 1.05 * completion + 0.08 * pulse
    core_halo.opacity = 0.12 + 0.18 * completion
    core_halo.color = vector(1.0, 0.58 + 0.25 * completion, 0.10)

    boundary_shell.pos = core.pos
    boundary_shell.radius = 2.25 - 0.45 * completion + 0.05 * math.sin(t * 1.5)
    boundary_shell.opacity = 0.04 + 0.13 * completion
    boundary_shell.color = vector(0.48 + 0.18 * completion, 0.50 + 0.14 * completion, 0.54 + 0.08 * completion)

    for i, b in enumerate(flame_bands):
        obj = b["obj"]
        b["phase"] += b["spin"] * dt
        obj.pos = core.pos
        obj.radius = 1.05 + i * 0.25 + 0.07 * math.sin(t * 2.2 + i)
        obj.thickness = 0.016 + 0.022 * completion
        obj.opacity = clamp((completion - 0.36) * 1.55, 0, 0.68)
        obj.axis = norm(rotate(obj.axis, angle=0.014 * b["spin"], axis=vector(0, 1, 0)))
        obj.color = vector(1.0, clamp(0.32 + 0.12 * i + 0.35 * completion, 0, 1), 0.04)

def update_flame_particle(p):
    obj = p["obj"]
    p["age"] += dt
    rel = p["pos"] - core.pos
    dist = mag(rel) + 0.001

    # The early fire escapes upward; learned fire curls inward.
    outward_escape = norm(vector(rel.x, 0.25, rel.z) + rand_vec(0.05)) * (0.18 * (1.0 - containment))
    rise = vector(0, 1.35 * (1.0 - containment), 0)

    inward = -norm(rel) * (0.65 + 1.35 * containment) / (0.45 + dist)
    tangent = norm(flat_tangent(rel) + rand_vec(0.03)) * (0.35 + 1.50 * containment) * p["orbit_bias"]
    thermal_noise = rand_vec(0.12 + 0.15 * (1.0 - completion))

    # Boundary pressure pushes particles back if they rise too far or drift too far.
    boundary_radius = boundary_shell.radius
    boundary_push = vector(0, 0, 0)
    if dist > boundary_radius:
        boundary_push += -norm(rel) * (1.2 + containment * 1.5)
    if p["pos"].y > 3.3 - completion * 1.2:
        boundary_push += vector(0, -1.0 - containment * 1.8, 0)

    p["vel"] += (rise + outward_escape + inward * containment + tangent * containment + boundary_push + thermal_noise) * dt
    p["vel"] *= 0.986 - 0.012 * completion

    p["pos"] += p["vel"] * dt
    p["energy"] = clamp(p["energy"] * 0.997 + containment * 0.0025 + (1.0 / (1.0 + dist)) * 0.002, 0.0, 1.25)

    if p["age"] > p["life"] or p["pos"].y > 5.5 or dist > 5.5 or p["energy"] < 0.05:
        reset_particle(p, "flame")
        return

    age_frac = p["age"] / p["life"]
    obj.pos = p["pos"]
    obj.radius = clamp(0.05 + p["energy"] * 0.13 * (1.0 - age_frac * 0.35), 0.035, 0.24)
    obj.color = heat_color(p["energy"], 1.0 - age_frac * 0.25)
    obj.opacity = clamp(0.25 + 0.62 * p["energy"] - age_frac * 0.25, 0.10, 0.88)

def update_spark_particle(p):
    obj = p["obj"]
    tr = p["trail"]
    p["age"] += dt
    rel = p["pos"] - core.pos
    dist = mag(rel) + 0.001

    # Sparks initially fly upward; as containment learns, they become orbital.
    lift = vector(0, 1.0 * (1.0 - containment), 0)
    inward = -norm(rel) * (0.55 + 1.1 * containment) / (0.4 + dist)
    tangent = norm(flat_tangent(rel) + rand_vec(0.02)) * (1.1 + 2.4 * containment) * p["orbit_bias"]
    jitter = rand_vec(0.20 * (1.0 - completion) + 0.04)

    if dist > boundary_shell.radius * 1.05:
        p["vel"] += -norm(rel) * (1.8 + 1.7 * containment) * dt

    p["vel"] += (lift + inward * containment + tangent * containment + jitter) * dt
    p["vel"] *= 0.988

    p["pos"] += p["vel"] * dt
    p["energy"] = clamp(p["energy"] * 0.996 + containment * 0.003, 0.0, 1.2)

    if p["age"] > p["life"] or p["pos"].y > 5.7 or dist > 6.0:
        tr.clear()
        reset_particle(p, "spark")
        return

    obj.pos = p["pos"]
    obj.radius = clamp(0.018 + 0.035 * p["energy"], 0.015, 0.075)
    obj.color = vector(1.0, clamp(0.45 + 0.45 * p["energy"], 0, 1), 0.08)
    obj.opacity = clamp(0.35 + 0.65 * p["energy"], 0.25, 1.0)

    # Keep trail bounded without relying on unsupported curve.points.
    tr.append(pos=p["pos"])
    if tr.npoints > 18:
        tr.pop(0)

def update_smoke_particle(p):
    obj = p["obj"]
    p["age"] += dt
    rel = p["pos"] - core.pos
    dist = mag(rel) + 0.001

    # Smoke becomes a boundary rather than simply disappearing upward.
    target_radius = boundary_shell.radius * random.uniform(0.82, 1.08)
    radial_error = dist - target_radius

    drift_up = vector(0, 0.30 * (1.0 - completion), 0)
    shell_force = -norm(rel) * radial_error * (0.25 + 1.25 * containment)
    tangent = norm(flat_tangent(rel) + rand_vec(0.04)) * (0.15 + 0.65 * containment)
    curl_noise = rand_vec(0.045)

    p["vel"] += (drift_up + shell_force + tangent + curl_noise) * dt
    p["vel"] *= 0.984
    p["pos"] += p["vel"] * dt

    if p["age"] > p["life"] or p["pos"].y > 5.0 or dist > 5.8:
        reset_particle(p, "smoke")
        # Spawn smoke closer to upper flame edge.
        p["pos"].y = random.uniform(0.8, 1.9)
        return

    age_frac = p["age"] / p["life"]
    obj.pos = p["pos"]
    obj.radius = clamp(0.08 + 0.18 * age_frac + 0.09 * completion, 0.06, 0.36)
    obj.color = vector(0.42 + 0.18 * completion, 0.43 + 0.17 * completion, 0.45 + 0.15 * completion)
    obj.opacity = clamp(0.05 + 0.16 * completion - age_frac * 0.05, 0.03, 0.23)

def update_status():
    stability_bar_count = int(completion * 24)
    bar = "█" * stability_bar_count + "░" * (24 - stability_bar_count)
    learning_text = "ON" if learning_enabled else "OFF"
    status.text = (
        f"phase: {phase_name}\n"
        f"learning: {learning_text} | containment: {containment:0.2f} | heat memory: {heat_memory:0.2f} | completion: {completion:0.2f}\n"
        f"[{bar}]"
    )

# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(60)
    update_camera()

    if paused:
        status.text = status.text + "\nPAUSED" if "PAUSED" not in status.text else status.text
        continue

    t += dt
    round_age += dt

    update_learning()
    update_core_visuals()

    for p in flames:
        update_flame_particle(p)
    for p in sparks:
        update_spark_particle(p)
    for p in smoke:
        update_smoke_particle(p)

    # The birth ring dims as the fire becomes less tied to ground fuel.
    birth_ring.opacity = clamp(0.72 - completion * 0.50, 0.18, 0.72)
    birth_ring.radius = 1.0 + 0.18 * math.sin(t * 1.5) * (1.0 - completion)

    update_status()
