"""
Indomitable Spirit Core

Story:
    INDOMITABLE
    If someone has an indomitable spirit, they never give up or admit defeat.

Simulation seed:
    A small glowing core is repeatedly struck by storms, pressure waves, and
    falling debris, but each impact makes it shine brighter instead of breaking.

Controls:
    Mouse       : drag / scroll to control camera
    Space       : pause / resume
    R           : reset simulation
    C           : toggle camera follow
    S           : toggle storm bolts
    P           : toggle pressure waves
    D           : toggle debris impacts
    Up / W      : increase intensity/speed
    Down        : decrease intensity/speed

Run:
    python indomitable_spirit_core.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Indomitable Spirit Core",
    width=1200,
    height=780,
    background=vector(0.94, 0.96, 1.0),
    center=vector(0, 1.15, 0),
)
scene.forward = vector(-0.48, -0.32, -0.82)
scene.up = vector(0, 1, 0)
scene.range = 9.2

scene.userspin = True
scene.userzoom = True
scene.userpan = True

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return vector(
        lerp(a.x, b.x, t),
        lerp(a.y, b.y, t),
        lerp(a.z, b.z, t),
    )


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def random_unit():
    v = vector(random.uniform(-1, 1), random.uniform(-0.2, 1), random.uniform(-1, 1))
    return safe_norm(v, vector(0, 1, 0))


# -----------------------------
# Colors
# -----------------------------
CORE_GOLD = vector(1.0, 0.76, 0.22)
CORE_WHITE = vector(1.0, 0.96, 0.72)
CORE_ORANGE = vector(1.0, 0.42, 0.12)
STORM_BLUE = vector(0.30, 0.55, 1.0)
STORM_PURPLE = vector(0.55, 0.32, 0.90)
PRESSURE_CYAN = vector(0.40, 0.95, 1.0)
DEBRIS_DARK = vector(0.26, 0.22, 0.18)
GROUND = vector(0.72, 0.69, 0.58)
CRACK_DARK = vector(0.25, 0.22, 0.19)
RESOLVE_GREEN = vector(0.36, 0.88, 0.46)

# -----------------------------
# Environment
# -----------------------------
floor = box(
    pos=vector(0, -0.08, 0),
    size=vector(16, 0.12, 12),
    color=GROUND,
    opacity=0.95,
)

impact_scar_rings = []
for i in range(7):
    r = 1.0 + i * 0.55
    scar = ring(
        pos=vector(0, 0.01, 0),
        axis=vector(0, 1, 0),
        radius=r,
        thickness=0.012,
        color=CRACK_DARK,
        opacity=0.10,
    )
    impact_scar_rings.append({"obj": scar, "phase": random.random() * math.tau})

# Stylized storm ceiling.
storm_clouds = []
for i in range(24):
    cloud = ellipsoid(
        pos=vector(random.uniform(-7, 7), random.uniform(5.3, 6.7), random.uniform(-5, 5)),
        length=random.uniform(0.9, 2.2),
        height=random.uniform(0.16, 0.36),
        width=random.uniform(0.45, 1.2),
        color=mix_color(vector(0.55, 0.58, 0.65), vector(0.35, 0.35, 0.45), random.random()),
        opacity=random.uniform(0.26, 0.55),
    )
    storm_clouds.append({"obj": cloud, "phase": random.random() * math.tau, "speed": random.uniform(0.005, 0.018)})

# -----------------------------
# Indomitable core
# -----------------------------
core_pos = vector(0, 1.25, 0)

core = sphere(
    pos=core_pos,
    radius=0.38,
    color=CORE_GOLD,
    emissive=True,
    opacity=0.98,
)

inner_core = sphere(
    pos=core_pos,
    radius=0.22,
    color=CORE_WHITE,
    emissive=True,
    opacity=0.85,
)

aura = sphere(
    pos=core_pos,
    radius=0.75,
    color=CORE_GOLD,
    emissive=True,
    opacity=0.16,
)

resolve_ring_1 = ring(
    pos=core_pos,
    axis=vector(0, 1, 0),
    radius=0.82,
    thickness=0.035,
    color=CORE_GOLD,
    emissive=True,
    opacity=0.55,
)
resolve_ring_2 = ring(
    pos=core_pos,
    axis=vector(1, 0.2, 0),
    radius=1.02,
    thickness=0.020,
    color=RESOLVE_GREEN,
    emissive=True,
    opacity=0.30,
)
resolve_ring_3 = ring(
    pos=core_pos,
    axis=vector(0.1, 0.4, 1),
    radius=1.20,
    thickness=0.014,
    color=PRESSURE_CYAN,
    emissive=True,
    opacity=0.22,
)

# Shield facets appear after impacts.
shield_facets = []
for i in range(18):
    ang = i * math.tau / 18
    facet = box(
        pos=core_pos + vector(math.cos(ang) * 1.06, 0, math.sin(ang) * 1.06),
        size=vector(0.32, 0.04, 0.14),
        color=CORE_GOLD,
        opacity=0.0,
        emissive=True,
    )
    facet.rotate(angle=-ang, axis=vector(0, 1, 0), origin=facet.pos)
    shield_facets.append({"obj": facet, "angle": ang, "phase": random.random() * math.tau})

# Strength particles orbiting the core.
strength_particles = []
for i in range(70):
    p = sphere(
        pos=core_pos,
        radius=random.uniform(0.018, 0.055),
        color=mix_color(CORE_GOLD, CORE_WHITE, random.random()),
        emissive=True,
        opacity=0.0,
    )
    strength_particles.append({
        "obj": p,
        "r": random.uniform(0.8, 2.2),
        "angle": random.random() * math.tau,
        "height": random.uniform(-0.7, 0.9),
        "speed": random.uniform(0.4, 1.4),
        "phase": random.random() * math.tau,
    })

# -----------------------------
# Storm bolts
# -----------------------------
storm_bolts = []
for i in range(8):
    bolt = cylinder(
        pos=vector(0, 6, 0),
        axis=vector(0, -4, 0),
        radius=0.025,
        color=STORM_BLUE,
        emissive=True,
        opacity=0.0,
    )
    branch1 = cylinder(
        pos=vector(0, 3.5, 0),
        axis=vector(0.6, -0.8, 0.3),
        radius=0.012,
        color=STORM_PURPLE,
        emissive=True,
        opacity=0.0,
    )
    branch2 = cylinder(
        pos=vector(0, 3.0, 0),
        axis=vector(-0.5, -0.7, -0.25),
        radius=0.012,
        color=STORM_PURPLE,
        emissive=True,
        opacity=0.0,
    )
    storm_bolts.append({
        "main": bolt,
        "branch1": branch1,
        "branch2": branch2,
        "timer": random.uniform(0, 1),
        "active": 0.0,
        "source": vector(0, 6, 0),
    })

# -----------------------------
# Pressure waves
# -----------------------------
pressure_waves = []
for i in range(12):
    wave = ring(
        pos=vector(0, 1.25, 0),
        axis=vector(0, 1, 0),
        radius=0.4,
        thickness=0.020,
        color=PRESSURE_CYAN,
        emissive=True,
        opacity=0.0,
    )
    pressure_waves.append({"obj": wave, "phase": i / 12, "direction": random_unit()})

# -----------------------------
# Falling debris
# -----------------------------
debris_objects = []
for i in range(18):
    pos = vector(random.uniform(-5, 5), random.uniform(3.5, 7.0), random.uniform(-4, 4))
    rock = box(
        pos=pos,
        size=vector(random.uniform(0.16, 0.42), random.uniform(0.14, 0.38), random.uniform(0.16, 0.42)),
        color=mix_color(DEBRIS_DARK, vector(0.45, 0.37, 0.30), random.random()),
        opacity=0.9,
    )
    debris_objects.append({
        "obj": rock,
        "vel": vector(random.uniform(-0.025, 0.025), random.uniform(-0.060, -0.025), random.uniform(-0.025, 0.025)),
        "spin": random.uniform(0.03, 0.12),
        "active": True,
        "impact_flash": 0.0,
    })

# Impact flashes that spawn at the core or ground.
impact_flashes = []
for i in range(14):
    flash = sphere(
        pos=core_pos,
        radius=0.05,
        color=CORE_WHITE,
        emissive=True,
        opacity=0.0,
    )
    impact_flashes.append({"obj": flash, "life": 0.0})

# Crack lines on the ground convert into glowing resilience lines.
cracks = []
for i in range(20):
    ang = random.random() * math.tau
    start_r = random.uniform(0.6, 1.7)
    length = random.uniform(0.6, 1.6)
    start = vector(math.cos(ang) * start_r, 0.02, math.sin(ang) * start_r)
    axis = vector(math.cos(ang) * length, 0, math.sin(ang) * length)
    crack = cylinder(
        pos=start,
        axis=axis,
        radius=random.uniform(0.008, 0.018),
        color=CRACK_DARK,
        opacity=0.22,
    )
    cracks.append({"obj": crack, "phase": random.random() * math.tau})

# -----------------------------
# Labels
# -----------------------------
title = label(
    pos=vector(0, 6.2, -4.9),
    text="Indomitable Spirit Core",
    height=24,
    box=False,
    color=vector(0.12, 0.12, 0.10),
)
subtitle = label(
    pos=vector(0, 5.76, -4.9),
    text="Storms, pressure waves, and debris strike the core; every impact makes it brighter.",
    height=12,
    box=False,
    color=vector(0.20, 0.18, 0.13),
)
status = label(
    pos=vector(-6.6, 4.95, -4.9),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.14, 0.13, 0.10),
    background=vector(0.96, 0.95, 0.88),
    opacity=0.82,
)
legend = label(
    pos=vector(6.5, 4.87, -4.9),
    text="Blue bolts: storm strikes\nCyan rings: pressure waves\nDark blocks: falling debris\nGold aura: strength gained from impact",
    height=12,
    box=True,
    border=8,
    color=vector(0.14, 0.13, 0.10),
    background=vector(0.96, 0.95, 0.88),
    opacity=0.82,
)

# -----------------------------
# State and controls
# -----------------------------
paused = False
camera_follow = False
show_storms = True
show_pressure = True
show_debris = True
speed = 1.0
sim_t = 0.0
resilience = 0.18
impact_count = 0
impact_energy = 0.0


def spawn_flash(pos, color=CORE_WHITE, size=0.26):
    for item in impact_flashes:
        if item["life"] <= 0.02:
            item["obj"].pos = pos
            item["obj"].radius = size
            item["obj"].color = color
            item["obj"].opacity = 0.95
            item["life"] = 1.0
            return


def add_impact(amount, pos):
    global resilience, impact_count, impact_energy
    resilience = clamp(resilience + amount, 0.0, 1.0)
    impact_count += 1
    impact_energy = clamp(impact_energy + 0.45, 0.0, 1.0)
    spawn_flash(pos, CORE_WHITE, 0.18 + 0.28 * amount)


def reset_debris_item(item):
    obj = item["obj"]
    obj.pos = vector(random.uniform(-5, 5), random.uniform(4.8, 7.4), random.uniform(-4, 4))
    item["vel"] = vector(
        random.uniform(-0.028, 0.028),
        random.uniform(-0.080, -0.035),
        random.uniform(-0.028, 0.028),
    )
    item["active"] = True


def reset_sim():
    global sim_t, resilience, impact_count, impact_energy, speed
    sim_t = 0.0
    resilience = 0.18
    impact_count = 0
    impact_energy = 0.0
    speed = 1.0
    for item in debris_objects:
        reset_debris_item(item)
    for item in impact_flashes:
        item["life"] = 0.0
        item["obj"].opacity = 0.0


def on_keydown(evt):
    global paused, camera_follow, show_storms, show_pressure, show_debris, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_sim()
    elif key == "c":
        camera_follow = not camera_follow
    elif key == "s":
        show_storms = not show_storms
        for b in storm_bolts:
            b["main"].visible = show_storms
            b["branch1"].visible = show_storms
            b["branch2"].visible = show_storms
    elif key == "p":
        show_pressure = not show_pressure
        for w in pressure_waves:
            w["obj"].visible = show_pressure
    elif key == "d":
        show_debris = not show_debris
        for item in debris_objects:
            item["obj"].visible = show_debris
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down",):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Main animation loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Resilience: {int(resilience * 100)}%\n"
            f"Impacts endured: {impact_count}\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.018 * speed
    sim_t += dt
    impact_energy *= 0.965

    # Core brightens and grows stronger after every strike.
    pulse = 0.5 + 0.5 * math.sin(sim_t * (2.0 + 3.5 * resilience))
    fast_pulse = 0.5 + 0.5 * math.sin(sim_t * (7.5 + 8.0 * resilience))

    core.radius = 0.32 + 0.30 * resilience + 0.08 * pulse + 0.11 * impact_energy
    inner_core.radius = 0.16 + 0.18 * resilience + 0.05 * fast_pulse
    aura.radius = 0.70 + 1.65 * resilience + 0.38 * pulse + 0.32 * impact_energy
    aura.opacity = 0.08 + 0.30 * resilience + 0.18 * impact_energy
    core.color = mix_color(CORE_ORANGE, CORE_WHITE, 0.30 + 0.70 * resilience)
    inner_core.color = mix_color(CORE_GOLD, CORE_WHITE, 0.45 + 0.55 * fast_pulse)

    resolve_ring_1.radius = 0.74 + 0.95 * resilience + 0.12 * pulse
    resolve_ring_1.thickness = 0.020 + 0.055 * resilience
    resolve_ring_1.opacity = 0.32 + 0.48 * resilience
    resolve_ring_1.rotate(angle=dt * (0.8 + 2.0 * resilience), axis=vector(0, 1, 0), origin=core_pos)

    resolve_ring_2.radius = 0.95 + 1.20 * resilience + 0.18 * fast_pulse
    resolve_ring_2.opacity = 0.14 + 0.42 * resilience
    resolve_ring_2.rotate(angle=-dt * (0.55 + 1.6 * resilience), axis=vector(1, 0.2, 0), origin=core_pos)

    resolve_ring_3.radius = 1.18 + 1.45 * resilience + 0.20 * pulse
    resolve_ring_3.opacity = 0.10 + 0.35 * resilience
    resolve_ring_3.rotate(angle=dt * (0.45 + 1.3 * resilience), axis=vector(0.1, 0.4, 1), origin=core_pos)

    # Shield facets become more visible with resilience.
    for facet in shield_facets:
        obj = facet["obj"]
        ang = facet["angle"] + sim_t * (0.22 + resilience * 0.65)
        radius = 1.02 + 0.74 * resilience + 0.08 * math.sin(sim_t * 2.5 + facet["phase"])
        obj.pos = core_pos + vector(math.cos(ang) * radius, 0.20 * math.sin(ang * 2 + sim_t), math.sin(ang) * radius)
        obj.opacity = 0.05 + 0.46 * resilience
        obj.color = mix_color(CORE_GOLD, CORE_WHITE, 0.28 * fast_pulse)
        obj.rotate(angle=0.012, axis=vector(0, 1, 0), origin=obj.pos)

    # Strength particles orbit faster as the core becomes more indomitable.
    for p in strength_particles:
        obj = p["obj"]
        p["angle"] += dt * p["speed"] * (0.7 + 2.2 * resilience)
        r = p["r"] * (0.70 + 0.55 * resilience)
        y = core_pos.y + p["height"] + 0.25 * math.sin(sim_t * 2.0 + p["phase"])
        obj.pos = vector(math.cos(p["angle"]) * r, y, math.sin(p["angle"]) * r)
        obj.opacity = 0.08 + 0.72 * resilience * (0.45 + 0.55 * math.sin(sim_t * 3.0 + p["phase"]) ** 2)
        obj.radius = 0.012 + 0.050 * resilience

    # Storm cloud movement.
    for c in storm_clouds:
        obj = c["obj"]
        obj.pos.x += c["speed"] * math.sin(sim_t * 0.4 + c["phase"]) * speed
        obj.opacity = 0.20 + 0.38 * math.sin(sim_t * 0.6 + c["phase"]) ** 2

    # Storm bolts strike the core.
    storm_intensity = 0.6 + 1.1 * speed
    for b in storm_bolts:
        b["timer"] -= dt * storm_intensity
        if b["timer"] <= 0:
            source = vector(random.uniform(-4.5, 4.5), random.uniform(5.2, 6.8), random.uniform(-3.6, 3.6))
            target = core_pos + vector(random.uniform(-0.20, 0.20), random.uniform(-0.20, 0.20), random.uniform(-0.20, 0.20))
            b["source"] = source
            b["main"].pos = source
            b["main"].axis = target - source
            b["branch1"].pos = source * 0.55 + target * 0.45
            b["branch1"].axis = vector(random.uniform(-0.7, 0.7), random.uniform(-0.9, -0.2), random.uniform(-0.7, 0.7))
            b["branch2"].pos = source * 0.35 + target * 0.65
            b["branch2"].axis = vector(random.uniform(-0.7, 0.7), random.uniform(-0.9, -0.2), random.uniform(-0.7, 0.7))
            b["active"] = 1.0
            b["timer"] = random.uniform(0.75, 1.8)
            if show_storms:
                add_impact(0.018, target)

        b["active"] *= 0.84
        opacity = b["active"] if show_storms else 0.0
        b["main"].opacity = 0.70 * opacity
        b["branch1"].opacity = 0.45 * opacity
        b["branch2"].opacity = 0.45 * opacity
        b["main"].radius = 0.015 + 0.035 * opacity
        b["main"].color = mix_color(STORM_BLUE, CORE_WHITE, resilience * 0.45)

    # Pressure waves repeatedly compress toward the core.
    for w in pressure_waves:
        phase = (sim_t * 0.22 * speed + w["phase"]) % 1.0
        inward = 1.0 - phase
        radius = 0.35 + 5.2 * inward
        w["obj"].pos = core_pos
        w["obj"].radius = radius
        w["obj"].thickness = 0.010 + 0.030 * phase
        w["obj"].opacity = (0.02 + 0.34 * phase * (1.0 - resilience * 0.35)) if show_pressure else 0.0
        w["obj"].color = mix_color(PRESSURE_CYAN, CORE_WHITE, 0.30 * resilience)
        if phase > 0.965 and show_pressure:
            add_impact(0.010, core_pos + random_unit() * 0.45)

    # Debris falls, hits the core shield or ground, then resets.
    for item in debris_objects:
        obj = item["obj"]
        obj.pos += item["vel"] * speed
        obj.rotate(angle=item["spin"], axis=vector(0.4, 1, 0.2), origin=obj.pos)

        if not show_debris:
            continue

        if mag(obj.pos - core_pos) < aura.radius * 0.62 + 0.25:
            add_impact(0.016, obj.pos)
            reset_debris_item(item)

        elif obj.pos.y < 0.10:
            spawn_flash(vector(obj.pos.x, 0.08, obj.pos.z), PRESSURE_CYAN, 0.12)
            reset_debris_item(item)

    # Impact flashes fade outward.
    for item in impact_flashes:
        if item["life"] > 0.0:
            item["life"] *= 0.91
            item["obj"].opacity = 0.85 * item["life"]
            item["obj"].radius *= 1.035
        else:
            item["obj"].opacity = 0.0

    # Ground cracks turn from dark scars to gold lines as the core converts damage into strength.
    for cr in cracks:
        obj = cr["obj"]
        glow = resilience * (0.45 + 0.55 * math.sin(sim_t * 2.0 + cr["phase"]) ** 2)
        obj.color = mix_color(CRACK_DARK, CORE_GOLD, glow)
        obj.opacity = 0.18 + 0.45 * glow
        obj.radius = 0.006 + 0.018 * glow

    for scar in impact_scar_rings:
        obj = scar["obj"]
        pulse_scar = 0.5 + 0.5 * math.sin(sim_t * 1.5 + scar["phase"])
        obj.color = mix_color(CRACK_DARK, CORE_GOLD, resilience * pulse_scar)
        obj.opacity = 0.06 + 0.25 * resilience * pulse_scar

    # Optional camera follow.
    if camera_follow:
        scene.center = core_pos + vector(0, 0.35, 0)
        scene.forward = safe_norm(core_pos - vector(5.8, 3.9, 7.0))
        scene.range = 6.2

    status.text = (
        f"Resilience: {int(resilience * 100)}%\n"
        f"Impacts endured: {impact_count}\n"
        f"Impact energy: {int(impact_energy * 100)}%\n"
        f"Core brightness: {int((0.35 + 0.65 * resilience + 0.20 * pulse) * 100)}%\n"
        f"Storms: {'on' if show_storms else 'off'} | Pressure: {'on' if show_pressure else 'off'}\n"
        f"Debris: {'on' if show_debris else 'off'} | Camera: {'follow' if camera_follow else 'mouse'}\n"
        f"Speed: {speed:.2f}x\n"
        "Mouse camera | Space pause | R reset | C follow | S storms | P waves | D debris"
    )
