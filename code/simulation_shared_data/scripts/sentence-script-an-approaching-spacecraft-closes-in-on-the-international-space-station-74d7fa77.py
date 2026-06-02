"""
Approach to the Station

Story:
    The International Space Station over the Earth as seen by an approaching spacecraft.

Simulation seed:
    An approaching spacecraft closes in on the International Space Station while
    Earth slowly turns below, making the station grow from a small cross-shaped
    point into a vast orbital structure.

Controls:
    Mouse       : drag / scroll to control camera view
    Space       : pause / resume
    C           : toggle automatic approach camera
    R           : reset approach
    D           : toggle docking corridor markers
    E           : toggle Earth cloud bands
    Up / W      : speed up
    Down / S    : slow down

Run:
    python approach_to_the_station.py

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
    title="Approach to the Station",
    width=1200,
    height=780,
    background=vector(0.02, 0.025, 0.045),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.42, -0.18, -0.89)
scene.up = vector(0, 1, 0)
scene.range = 11

# Explicitly allow mouse camera controls.
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
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


# -----------------------------
# Colors
# -----------------------------
EARTH_BLUE = vector(0.04, 0.23, 0.58)
EARTH_LIGHT = vector(0.10, 0.43, 0.86)
LAND_GREEN = vector(0.12, 0.42, 0.20)
DESERT = vector(0.62, 0.48, 0.23)
CLOUD = vector(0.92, 0.96, 1.0)
ISS_WHITE = vector(0.82, 0.86, 0.86)
ISS_DARK = vector(0.26, 0.28, 0.30)
SOLAR_BLUE = vector(0.07, 0.18, 0.34)
SOLAR_GOLD = vector(0.95, 0.58, 0.18)
SHIP = vector(0.68, 0.72, 0.74)
SHIP_DARK = vector(0.24, 0.26, 0.29)
DOCK_GREEN = vector(0.30, 1.0, 0.48)

# -----------------------------
# Earth below
# -----------------------------
earth = sphere(
    pos=vector(0, -9.0, 0),
    radius=7.2,
    color=EARTH_BLUE,
    opacity=0.98,
    shininess=0.3,
)

atmosphere = sphere(
    pos=earth.pos,
    radius=7.38,
    color=vector(0.30, 0.70, 1.0),
    opacity=0.13,
    emissive=True,
)

# Continents as flattened patches on the visible top hemisphere.
continents = []
random.seed(8)
for i in range(34):
    theta = random.uniform(0, math.tau)
    r = random.uniform(1.2, 6.0)
    x = math.cos(theta) * r
    z = math.sin(theta) * r
    # Project patch onto upper surface of sphere.
    y = earth.pos.y + math.sqrt(max(0.0, earth.radius**2 - x**2 - z**2)) + 0.035
    patch = ellipsoid(
        pos=vector(x, y, z),
        length=random.uniform(0.55, 1.8),
        height=0.035,
        width=random.uniform(0.35, 1.0),
        color=mix_color(LAND_GREEN, DESERT, random.random() * 0.45),
        opacity=0.72,
    )
    patch.rotate(angle=random.uniform(0, math.tau), axis=vector(0, 1, 0), origin=earth.pos)
    continents.append({"obj": patch, "angle": random.uniform(0, math.tau), "speed": random.uniform(0.035, 0.065)})

# Cloud bands and storm spirals.
cloud_bands = []
for i in range(12):
    band = ring(
        pos=earth.pos + vector(0, 0.15 + i * 0.006, 0),
        axis=vector(0, 1, 0),
        radius=random.uniform(2.0, 6.9),
        thickness=random.uniform(0.018, 0.055),
        color=CLOUD,
        opacity=random.uniform(0.10, 0.26),
    )
    band.rotate(angle=random.uniform(-0.55, 0.55), axis=vector(1, 0, 0), origin=earth.pos)
    cloud_bands.append({"obj": band, "phase": random.random() * math.tau, "speed": random.uniform(0.05, 0.12)})

storm_markers = []
for i in range(4):
    storm = ring(
        pos=earth.pos + vector(random.uniform(-4.5, 4.5), earth.radius + 0.22, random.uniform(-3.5, 3.5)),
        axis=vector(0, 1, 0),
        radius=random.uniform(0.26, 0.55),
        thickness=0.025,
        color=CLOUD,
        opacity=0.32,
    )
    storm_markers.append({"obj": storm, "phase": random.random() * math.tau})

# Star field.
stars = []
for i in range(160):
    pos = vector(random.uniform(-22, 22), random.uniform(-2, 16), random.uniform(-18, 14))
    if mag(pos - vector(0, 0, 0)) < 4:
        continue
    star = sphere(
        pos=pos,
        radius=random.uniform(0.012, 0.040),
        color=vector(0.85, 0.90, 1.0),
        emissive=True,
        opacity=random.uniform(0.35, 0.90),
    )
    stars.append({"obj": star, "phase": random.random() * math.tau})

# -----------------------------
# ISS model
# -----------------------------
iss_root = vector(0, 0.4, 0)
iss_parts = []

# Main truss: a long cross-shaped orbital structure.
main_truss = cylinder(
    pos=iss_root + vector(-3.3, 0, 0),
    axis=vector(6.6, 0, 0),
    radius=0.055,
    color=ISS_WHITE,
)
iss_parts.append(main_truss)

center_node = sphere(pos=iss_root, radius=0.20, color=ISS_WHITE)
iss_parts.append(center_node)

# Pressurized modules along the station axis.
for x in [-1.10, -0.65, -0.28, 0.33, 0.78, 1.18]:
    module = cylinder(
        pos=iss_root + vector(x - 0.18, 0, -0.03),
        axis=vector(0.36, 0, 0),
        radius=0.145,
        color=mix_color(ISS_WHITE, ISS_DARK, 0.12 + 0.08 * abs(x)),
    )
    iss_parts.append(module)
    cap1 = sphere(pos=module.pos, radius=0.145, color=module.color)
    cap2 = sphere(pos=module.pos + module.axis, radius=0.145, color=module.color)
    iss_parts.extend([cap1, cap2])

# Vertical docking spine.
docking_spine = cylinder(
    pos=iss_root + vector(0, -0.95, 0),
    axis=vector(0, 1.9, 0),
    radius=0.038,
    color=ISS_WHITE,
)
iss_parts.append(docking_spine)

for y in [-0.78, -0.42, 0.42, 0.78]:
    node = cylinder(
        pos=iss_root + vector(-0.11, y, 0),
        axis=vector(0.22, 0, 0),
        radius=0.12,
        color=ISS_WHITE,
    )
    iss_parts.append(node)

# Solar arrays.
solar_panels = []
panel_positions = [-2.95, -2.05, 2.05, 2.95]
for x in panel_positions:
    for side in [-1, 1]:
        boom = cylinder(
            pos=iss_root + vector(x, 0, 0),
            axis=vector(0, side * 0.95, 0),
            radius=0.026,
            color=ISS_WHITE,
        )
        panel = box(
            pos=iss_root + vector(x, side * 1.42, 0),
            size=vector(0.72, 0.12, 1.55),
            color=SOLAR_BLUE,
            opacity=0.92,
        )
        gold_grid = []
        for k in [-0.24, 0, 0.24]:
            strip = cylinder(
                pos=panel.pos + vector(k, -0.072 * side, -0.74),
                axis=vector(0, 0, 1.48),
                radius=0.006,
                color=SOLAR_GOLD,
                opacity=0.72,
            )
            gold_grid.append(strip)
        solar_panels.append({"panel": panel, "boom": boom, "grid": gold_grid, "x": x, "side": side, "phase": random.random() * math.tau})
        iss_parts.extend([boom, panel] + gold_grid)

# Radiators.
radiators = []
for x in [-1.52, 1.52]:
    rad = box(
        pos=iss_root + vector(x, 0, 0.48),
        size=vector(0.70, 0.06, 0.36),
        color=vector(0.90, 0.92, 0.88),
        opacity=0.88,
    )
    radiators.append(rad)
    iss_parts.append(rad)

# Docking port facing approaching spacecraft.
docking_port = ring(
    pos=iss_root + vector(0, 0, -0.70),
    axis=vector(0, 0, 1),
    radius=0.22,
    thickness=0.030,
    color=DOCK_GREEN,
    emissive=True,
)
iss_parts.append(docking_port)

# Store initial offsets for ISS scale/rotation.
iss_base = {}
for obj in iss_parts:
    iss_base[obj] = {
        "pos": vector(obj.pos.x, obj.pos.y, obj.pos.z),
        "axis": vector(obj.axis.x, obj.axis.y, obj.axis.z) if hasattr(obj, "axis") else None,
        "size": vector(obj.size.x, obj.size.y, obj.size.z) if hasattr(obj, "size") else None,
        "radius": getattr(obj, "radius", None),
        "height": getattr(obj, "height", None),
        "width": getattr(obj, "width", None),
        "length": getattr(obj, "length", None),
        "thickness": getattr(obj, "thickness", None),
    }

# -----------------------------
# Approaching spacecraft
# -----------------------------
ship_parts = []
ship_root_start = vector(0, 0.1, -9.4)

ship_body = cone(
    pos=ship_root_start + vector(0, 0, -0.40),
    axis=vector(0, 0, 0.86),
    radius=0.32,
    color=SHIP,
)
ship_capsule = sphere(
    pos=ship_root_start + vector(0, 0, 0.18),
    radius=0.28,
    color=SHIP,
)
ship_window = ellipsoid(
    pos=ship_root_start + vector(0, 0.10, 0.42),
    length=0.24,
    height=0.08,
    width=0.035,
    color=vector(0.10, 0.38, 0.68),
    emissive=True,
)
for obj in [ship_body, ship_capsule, ship_window]:
    ship_parts.append(obj)

for side in [-1, 1]:
    fin = box(
        pos=ship_root_start + vector(side * 0.38, -0.04, -0.12),
        size=vector(0.38, 0.065, 0.48),
        color=SHIP_DARK,
        opacity=0.90,
    )
    ship_parts.append(fin)

ship_thruster = cylinder(
    pos=ship_root_start + vector(0, 0, -0.70),
    axis=vector(0, 0, -0.20),
    radius=0.16,
    color=SHIP_DARK,
)
ship_parts.append(ship_thruster)

thruster_glow = cone(
    pos=ship_root_start + vector(0, 0, -0.90),
    axis=vector(0, 0, -0.62),
    radius=0.18,
    color=vector(0.38, 0.76, 1.0),
    emissive=True,
    opacity=0.42,
)
ship_parts.append(thruster_glow)

ship_base_offsets = {obj: obj.pos - ship_root_start for obj in ship_parts}

# -----------------------------
# Docking corridor markers
# -----------------------------
corridor_markers = []
for i in range(18):
    z = -8.7 + i * 0.48
    radius = lerp(1.05, 0.24, i / 17)
    ring_marker = ring(
        pos=vector(0, 0, z),
        axis=vector(0, 0, 1),
        radius=radius,
        thickness=0.010,
        color=DOCK_GREEN,
        opacity=0.20 + 0.22 * (i / 17),
        emissive=True,
    )
    corridor_markers.append({"obj": ring_marker, "phase": random.random() * math.tau, "base_radius": radius})

alignment_dots = []
for i in range(8):
    dot = sphere(
        pos=vector(math.cos(i * math.tau / 8) * 1.25, math.sin(i * math.tau / 8) * 1.25, -4.0),
        radius=0.035,
        color=DOCK_GREEN,
        emissive=True,
        opacity=0.55,
    )
    alignment_dots.append({"obj": dot, "angle": i * math.tau / 8})

# -----------------------------
# Labels
# -----------------------------
title = label(
    pos=vector(0, 3.9, -4.8),
    text="Approach to the Station",
    height=24,
    box=False,
    color=vector(0.82, 0.92, 1.0),
)
subtitle = label(
    pos=vector(0, 3.45, -4.8),
    text="Earth turns below as the ISS grows from a small cross into a vast orbital structure.",
    height=12,
    box=False,
    color=vector(0.62, 0.78, 0.95),
)
status = label(
    pos=vector(-6.4, 2.75, -5.2),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.85, 0.95, 1.0),
    background=vector(0.04, 0.06, 0.10),
    opacity=0.78,
)
legend = label(
    pos=vector(6.1, 2.6, -5.1),
    text="The approaching craft closes on the docking port.\nThe station expands visually as distance falls.\nEarth rotates beneath the orbiting structure.",
    height=12,
    box=True,
    border=8,
    color=vector(0.85, 0.95, 1.0),
    background=vector(0.04, 0.06, 0.10),
    opacity=0.78,
)

# -----------------------------
# State and controls
# -----------------------------
paused = False
auto_camera = True
show_corridor = True
show_clouds = True
speed = 1.0
sim_t = 0.0


def reset_sim():
    global sim_t, speed, auto_camera
    sim_t = 0.0
    speed = 1.0
    auto_camera = True


def on_keydown(evt):
    global paused, auto_camera, show_corridor, show_clouds, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_sim()
    elif key == "c":
        auto_camera = not auto_camera
    elif key == "d":
        show_corridor = not show_corridor
        for item in corridor_markers:
            item["obj"].visible = show_corridor
        for item in alignment_dots:
            item["obj"].visible = show_corridor
    elif key == "e":
        show_clouds = not show_clouds
        for item in cloud_bands:
            item["obj"].visible = show_clouds
        for item in storm_markers:
            item["obj"].visible = show_clouds
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down", "s"):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Group transforms
# -----------------------------
def update_ship(root, wobble):
    for obj, offset in ship_base_offsets.items():
        # Slight approach roll and micro-correction.
        x = offset.x * math.cos(wobble) - offset.y * math.sin(wobble)
        y = offset.x * math.sin(wobble) + offset.y * math.cos(wobble)
        obj.pos = root + vector(x, y, offset.z)

    flame = 0.5 + 0.5 * math.sin(sim_t * 14.0)
    thruster_glow.radius = 0.12 + 0.10 * flame
    thruster_glow.opacity = 0.20 + 0.32 * flame


def update_iss(scale, yaw, pitch):
    # The ISS grows in apparent scale during the approach. This is a visual
    # storytelling device that makes the small cross become a large structure.
    cy = math.cos(yaw)
    sy = math.sin(yaw)
    cp = math.cos(pitch)
    sp = math.sin(pitch)

    def transform(v):
        # yaw around y, then pitch around x.
        x1 = v.x * cy - v.z * sy
        z1 = v.x * sy + v.z * cy
        y1 = v.y
        y2 = y1 * cp - z1 * sp
        z2 = y1 * sp + z1 * cp
        return vector(x1, y2, z2) * scale

    for obj, base in iss_base.items():
        off = base["pos"] - iss_root
        obj.pos = iss_root + transform(off)

        if base["axis"] is not None:
            obj.axis = transform(base["axis"])

        if base["size"] is not None:
            obj.size = base["size"] * scale

        if base["radius"] is not None:
            obj.radius = base["radius"] * scale
        if base["height"] is not None and hasattr(obj, "height"):
            obj.height = base["height"] * scale
        if base["width"] is not None and hasattr(obj, "width"):
            obj.width = base["width"] * scale
        if base["length"] is not None and hasattr(obj, "length"):
            obj.length = base["length"] * scale
        if base["thickness"] is not None and hasattr(obj, "thickness"):
            obj.thickness = base["thickness"] * scale


# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.018 * speed
    sim_t += dt

    # Approach progress: slow at first, then visible closure.
    cycle = (sim_t * 0.030) % 1.0
    approach = 1.0 - (1.0 - cycle) ** 2.15
    distance = lerp(9.4, 1.12, approach)

    # Spacecraft moves along docking corridor toward station.
    lateral_correction = vector(
        0.28 * math.sin(sim_t * 0.58) * (1.0 - approach),
        0.18 * math.sin(sim_t * 0.83 + 1.2) * (1.0 - approach),
        0,
    )
    ship_root = vector(0, 0, -distance) + lateral_correction
    update_ship(ship_root, 0.06 * math.sin(sim_t * 1.7))

    # ISS grows from a tiny cross-shaped point into a large structure.
    apparent_scale = lerp(0.28, 1.15, approach)
    iss_yaw = 0.12 * math.sin(sim_t * 0.16)
    iss_pitch = 0.07 * math.sin(sim_t * 0.22 + 0.8)
    update_iss(apparent_scale, iss_yaw, iss_pitch)

    # Earth rotation below.
    earth.rotate(angle=dt * 0.12, axis=vector(0, 1, 0), origin=earth.pos)
    atmosphere.rotate(angle=dt * 0.10, axis=vector(0, 1, 0), origin=earth.pos)

    for item in continents:
        item["obj"].rotate(angle=dt * item["speed"], axis=vector(0, 1, 0), origin=earth.pos)

    for item in cloud_bands:
        item["obj"].rotate(angle=dt * item["speed"], axis=vector(0, 1, 0), origin=earth.pos)
        item["obj"].opacity = 0.08 + 0.20 * (0.5 + 0.5 * math.sin(sim_t * 0.6 + item["phase"]))

    for item in storm_markers:
        item["obj"].rotate(angle=dt * 0.35, axis=vector(0, 1, 0), origin=item["obj"].pos)
        item["obj"].opacity = 0.16 + 0.20 * math.sin(sim_t * 0.8 + item["phase"]) ** 2

    # Docking corridor pulses toward the station.
    for i, item in enumerate(corridor_markers):
        obj = item["obj"]
        pulse = 0.5 + 0.5 * math.sin(sim_t * 4.0 - i * 0.7)
        obj.radius = item["base_radius"] * (0.96 + 0.08 * pulse)
        obj.opacity = 0.08 + 0.36 * pulse * (0.5 + 0.5 * approach)
        obj.color = mix_color(vector(0.10, 0.46, 0.26), DOCK_GREEN, pulse)

    for item in alignment_dots:
        ang = item["angle"] + sim_t * 0.18
        rad = lerp(1.25, 0.38, approach)
        item["obj"].pos = vector(math.cos(ang) * rad, math.sin(ang) * rad, lerp(-4.0, -0.65, approach))
        item["obj"].opacity = 0.18 + 0.55 * approach

    # Solar panel glints.
    for panel_data in solar_panels:
        glint = 0.5 + 0.5 * math.sin(sim_t * 2.1 + panel_data["phase"])
        panel_data["panel"].color = mix_color(SOLAR_BLUE, vector(0.16, 0.38, 0.70), 0.20 * glint)

    # Star twinkle.
    for item in stars:
        item["obj"].opacity = 0.28 + 0.60 * math.sin(sim_t * 0.9 + item["phase"]) ** 2

    # Automatic camera behaves like the approaching spacecraft view. When off,
    # the script stops changing scene.forward/range so mouse controls stay active.
    if auto_camera:
        scene.center = mix_color(vector(0, 0.2, -2.8), iss_root, clamp(approach * 1.4))
        scene.forward = safe_norm(iss_root - (ship_root + vector(0.15, 0.10, -0.75)))
        scene.range = lerp(10.5, 4.2, approach)

    status.text = (
        f"Approach progress: {int(approach * 100)}%\n"
        f"Range to station: {distance:4.2f} units\n"
        f"ISS apparent scale: {apparent_scale:4.2f}x\n"
        f"Auto camera: {'on' if auto_camera else 'off'}\n"
        f"Docking corridor: {'on' if show_corridor else 'off'}\n"
        f"Cloud bands: {'on' if show_clouds else 'off'}\n"
        f"Speed: {speed:.2f}x\n"
        "Mouse camera | Space pause | C camera | D corridor | E clouds | R reset"
    )
