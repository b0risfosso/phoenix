"""
Norway Forest Recovery Map
A VPython simulation of a national forest map slowly shifting from damaged patches
to expanding green zones as protected regions reconnect across mountains, valleys,
and coastlines.

Controls:
    Space : pause / resume
    R     : reset recovery
    C     : toggle ecological corridor beams
    M     : toggle moving monitoring markers
    Up    : speed up recovery
    Down  : slow down recovery

Run:
    python norway_forest_recovery_map.py

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
    title="Norway Forest Recovery Map",
    width=1200,
    height=780,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.55, -0.62, -0.55)
scene.up = vector(0, 1, 0)
scene.range = 15

# -----------------------------
# Utility functions
# -----------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(c1, c2, t):
    return vector(
        lerp(c1.x, c2.x, t),
        lerp(c1.y, c2.y, t),
        lerp(c1.z, c2.z, t),
    )


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def map_width_at_y(y):
    """Approximate Norway's long narrow outline width at a north-south coordinate."""
    base = 1.15 + 0.72 * math.sin((y + 8.5) * 0.55) ** 2
    waist = 0.72 * math.exp(-((y - 0.5) ** 2) / 10.0)
    north = 0.55 * math.exp(-((y - 7.4) ** 2) / 5.0)
    south = 0.38 * math.exp(-((y + 7.4) ** 2) / 2.4)
    return base + waist + north + south


def centerline_x(y):
    """Curved spine of the stylized map."""
    return 1.0 * math.sin(y * 0.52) + 0.42 * math.sin(y * 1.12)


def inside_map(x, y):
    return abs(x - centerline_x(y)) < map_width_at_y(y)


def terrain_height(x, y):
    ridge = 0.46 * math.exp(-((x - centerline_x(y) + 0.55) ** 2) / 0.55)
    undulate = 0.09 * math.sin(1.6 * y + 0.7 * x) + 0.06 * math.cos(2.2 * x - 0.5 * y)
    north_lift = 0.18 * clamp((y + 1.0) / 8.5)
    return ridge + undulate + north_lift


# -----------------------------
# Colors
# -----------------------------
WATER = vector(0.67, 0.84, 0.94)
LAND = vector(0.78, 0.80, 0.68)
DAMAGED = vector(0.57, 0.45, 0.36)
RECOVERING = vector(0.49, 0.69, 0.34)
FOREST = vector(0.17, 0.52, 0.23)
PROTECTED = vector(0.10, 0.62, 0.34)
MOUNTAIN = vector(0.74, 0.76, 0.72)
COAST = vector(0.42, 0.67, 0.82)
VALLEY = vector(0.62, 0.77, 0.45)
GLOW = vector(0.53, 0.93, 0.56)

# -----------------------------
# Base environment
# -----------------------------
ocean = box(
    pos=vector(0, -0.12, 0),
    size=vector(13.5, 0.08, 22.5),
    color=WATER,
    opacity=0.72,
)

map_shadow = box(
    pos=vector(0.25, -0.055, 0),
    size=vector(8.2, 0.03, 19.2),
    color=vector(0.70, 0.77, 0.77),
    opacity=0.25,
)

# -----------------------------
# Build stylized national map from small terrain cells
# VPython uses x/z as horizontal plane and y as height.
# -----------------------------
cells = []
damaged_cells = []
coastal_cells = []
mountain_cells = []
valley_cells = []

cell_size = 0.46
ys = [round(-8.5 + i * cell_size, 3) for i in range(int(17 / cell_size) + 1)]

for y in ys:
    width = map_width_at_y(y)
    cx = centerline_x(y)
    steps = int((width * 2.2) / cell_size)
    for j in range(-steps, steps + 1):
        x = cx + j * cell_size
        if not inside_map(x, y):
            continue

        dist_to_edge = width - abs(x - cx)
        h = terrain_height(x, y)
        is_coast = dist_to_edge < 0.42
        is_mountain = h > 0.48 and x < cx + 0.45
        is_valley = (not is_mountain) and (0.15 < h < 0.38) and (abs(math.sin(y * 0.9 + x)) > 0.38)

        base_col = LAND
        height = 0.08
        if is_coast:
            base_col = COAST
            height = 0.06
        elif is_mountain:
            base_col = MOUNTAIN
            height = 0.16 + 0.55 * h
        elif is_valley:
            base_col = VALLEY
            height = 0.10
        else:
            base_col = mix_color(LAND, RECOVERING, 0.25)

        obj = box(
            pos=vector(x, height / 2.0, y),
            size=vector(cell_size * 0.92, height, cell_size * 0.92),
            color=base_col,
            opacity=0.96,
        )

        cell = {
            "obj": obj,
            "x": x,
            "z": y,
            "h": height,
            "base": base_col,
            "recovery": 0.0,
            "target": 0.0,
            "is_coast": is_coast,
            "is_mountain": is_mountain,
            "is_valley": is_valley,
            "phase": random.random() * math.tau,
        }
        cells.append(cell)

        if is_coast:
            coastal_cells.append(cell)
        if is_mountain:
            mountain_cells.append(cell)
        if is_valley:
            valley_cells.append(cell)

# -----------------------------
# Damaged patches and protected hubs
# -----------------------------
damage_centers = [
    vector(centerline_x(-6.7) + 0.20, 0, -6.7),
    vector(centerline_x(-3.8) - 0.75, 0, -3.8),
    vector(centerline_x(-0.9) + 0.55, 0, -0.9),
    vector(centerline_x(2.6) - 0.55, 0, 2.6),
    vector(centerline_x(5.6) + 0.35, 0, 5.6),
    vector(centerline_x(7.4) - 0.25, 0, 7.4),
]

protected_centers = [
    vector(centerline_x(-7.3) - 0.05, 0.36, -7.3),
    vector(centerline_x(-4.7) + 0.35, 0.42, -4.7),
    vector(centerline_x(-1.7) - 0.28, 0.44, -1.7),
    vector(centerline_x(1.2) + 0.52, 0.42, 1.2),
    vector(centerline_x(3.8) - 0.36, 0.48, 3.8),
    vector(centerline_x(6.4) + 0.20, 0.55, 6.4),
    vector(centerline_x(8.1) - 0.12, 0.58, 8.1),
]

for cell in cells:
    p = vector(cell["x"], 0, cell["z"])

    # Initial damage is strongest near selected centers.
    damage_strength = 0.0
    for dc in damage_centers:
        d = mag(p - dc)
        damage_strength = max(damage_strength, clamp(1.0 - d / 1.25))

    # Recovery target is boosted around protected centers and later spreads through corridors.
    protect_strength = 0.0
    for pc in protected_centers:
        d = mag(p - vector(pc.x, 0, pc.z))
        protect_strength = max(protect_strength, clamp(1.0 - d / 1.55))

    if damage_strength > 0.18:
        cell["recovery"] = 0.0
        cell["damage"] = damage_strength
        cell["target"] = 0.45 + 0.35 * protect_strength
        damaged_cells.append(cell)
        cell["obj"].color = mix_color(DAMAGED, cell["base"], 0.18)
        cell["obj"].height = max(cell["h"] * 0.72, 0.045)
        cell["obj"].pos.y = cell["obj"].height / 2.0
    else:
        cell["recovery"] = 0.28 + 0.55 * protect_strength + random.random() * 0.08
        cell["damage"] = 0.0
        cell["target"] = clamp(0.55 + 0.35 * protect_strength)

# Protected-zone markers
protected_markers = []
for i, pc in enumerate(protected_centers):
    marker = cylinder(
        pos=vector(pc.x, 0.17, pc.z),
        axis=vector(0, 0.025, 0),
        radius=0.68,
        color=PROTECTED,
        opacity=0.18,
    )
    ring_marker = ring(
        pos=vector(pc.x, 0.23, pc.z),
        axis=vector(0, 1, 0),
        radius=0.70,
        thickness=0.035,
        color=PROTECTED,
        opacity=0.55,
    )
    beacon = sphere(
        pos=vector(pc.x, 0.34, pc.z),
        radius=0.11,
        color=PROTECTED,
        emissive=True,
    )
    protected_markers.append((marker, ring_marker, beacon))

# Corridor beams connecting protected regions
corridors = []
for a, b in zip(protected_centers[:-1], protected_centers[1:]):
    start = vector(a.x, 0.32, a.z)
    end = vector(b.x, 0.32, b.z)
    mid = (start + end) * 0.5
    axis = end - start
    beam = cylinder(
        pos=start,
        axis=axis,
        radius=0.035,
        color=GLOW,
        opacity=0.22,
        emissive=True,
    )
    pulse = sphere(pos=start, radius=0.09, color=GLOW, emissive=True)
    corridors.append({"beam": beam, "pulse": pulse, "a": start, "b": end, "phase": random.random() * math.tau})

# Mountain ridge indicators
ridge_segments = []
for y in [-7.5, -6.3, -5.2, -4.1, -2.8, -1.5, -0.4, 0.8, 2.0, 3.3, 4.7, 6.2, 7.6]:
    cx = centerline_x(y) - 0.70
    ridge = cone(
        pos=vector(cx, 0.40 + 0.08 * random.random(), y),
        axis=vector(0, 0.70 + 0.22 * random.random(), 0),
        radius=0.34,
        color=vector(0.68, 0.70, 0.67),
        opacity=0.86,
    )
    ridge_segments.append(ridge)

# Valley streams and coastal reconnect paths
water_paths = []
for y0 in [-6.8, -3.9, -1.0, 2.4, 5.5, 7.2]:
    cx = centerline_x(y0)
    stream = cylinder(
        pos=vector(cx - 1.0, 0.13, y0 - 0.28),
        axis=vector(2.0, 0.0, 0.56),
        radius=0.025,
        color=vector(0.42, 0.65, 0.90),
        opacity=0.55,
    )
    water_paths.append(stream)

# Monitoring markers that travel along corridors
monitor_markers = []
for c in corridors:
    s = sphere(pos=c["a"], radius=0.065, color=vector(1.0, 0.76, 0.25), emissive=True)
    monitor_markers.append(s)

# Labels
title = label(
    pos=vector(0, 2.25, -9.8),
    text="Norway Forest Recovery Map",
    height=22,
    box=False,
    color=vector(0.08, 0.18, 0.12),
)
status_label = label(
    pos=vector(-6.0, 1.35, 8.8),
    text="",
    height=13,
    box=True,
    border=8,
    color=vector(0.08, 0.15, 0.10),
    background=vector(0.95, 0.98, 0.94),
    opacity=0.75,
)
legend = label(
    pos=vector(5.2, 1.05, 8.9),
    text="Brown = damaged patches\nGreen = recovered forest\nGlowing links = protected corridors\nGray ridges = mountains\nBlue edges = coastlines",
    height=12,
    box=True,
    border=8,
    color=vector(0.08, 0.18, 0.16),
    background=vector(0.95, 0.98, 1.0),
    opacity=0.78,
)

# Recovery wave rings around protected zones
recovery_rings = []
for pc in protected_centers:
    rr = ring(
        pos=vector(pc.x, 0.36, pc.z),
        axis=vector(0, 1, 0),
        radius=0.18,
        thickness=0.018,
        color=GLOW,
        opacity=0.55,
    )
    recovery_rings.append({"ring": rr, "phase": random.random() * math.tau})

# -----------------------------
# Interaction state
# -----------------------------
paused = False
show_corridors = True
show_monitors = True
speed = 1.0
time_value = 0.0
global_progress = 0.0


def reset_recovery():
    global time_value, global_progress
    time_value = 0.0
    global_progress = 0.0
    for cell in cells:
        p = vector(cell["x"], 0, cell["z"])

        damage_strength = 0.0
        for dc in damage_centers:
            d = mag(p - dc)
            damage_strength = max(damage_strength, clamp(1.0 - d / 1.25))

        protect_strength = 0.0
        for pc in protected_centers:
            d = mag(p - vector(pc.x, 0, pc.z))
            protect_strength = max(protect_strength, clamp(1.0 - d / 1.55))

        if damage_strength > 0.18:
            cell["recovery"] = 0.0
            cell["damage"] = damage_strength
            cell["target"] = 0.45 + 0.35 * protect_strength
        else:
            cell["recovery"] = 0.28 + 0.55 * protect_strength + random.random() * 0.08
            cell["damage"] = 0.0
            cell["target"] = clamp(0.55 + 0.35 * protect_strength)


def on_keydown(evt):
    global paused, show_corridors, show_monitors, speed
    key = evt.key.lower()

    if key == " ":
        paused = not paused
    elif key == "r":
        reset_recovery()
    elif key == "c":
        show_corridors = not show_corridors
        for c in corridors:
            c["beam"].visible = show_corridors
            c["pulse"].visible = show_corridors
    elif key == "m":
        show_monitors = not show_monitors
        for m in monitor_markers:
            m.visible = show_monitors
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down", "s"):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Main animation loop
# -----------------------------
while True:
    rate(45)

    if paused:
        status_label.text = (
            "Paused\n"
            f"Recovery speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.022 * speed
    time_value += dt
    global_progress = clamp(time_value / 38.0)

    # Corridors become stronger as protected regions reconnect.
    corridor_strength = clamp((global_progress - 0.10) / 0.70)

    # Update terrain cells.
    recovered_count = 0
    damaged_count = 0
    for cell in cells:
        p = vector(cell["x"], 0, cell["z"])

        # Distance to protected network.
        network_pull = 0.0
        for pc in protected_centers:
            d = mag(p - vector(pc.x, 0, pc.z))
            network_pull = max(network_pull, clamp(1.0 - d / (1.25 + 3.0 * corridor_strength)))

        # Corridors spread recovery along the national spine.
        corridor_pull = 0.0
        for c in corridors:
            a = vector(c["a"].x, 0, c["a"].z)
            b = vector(c["b"].x, 0, c["b"].z)
            ap = p - a
            ab = b - a
            tproj = clamp(dot(ap, ab) / max(0.001, dot(ab, ab)))
            nearest = a + ab * tproj
            d = mag(p - nearest)
            corridor_pull = max(corridor_pull, clamp(1.0 - d / (0.48 + 1.05 * corridor_strength)))

        coast_bonus = 0.12 if cell["is_coast"] and global_progress > 0.55 else 0.0
        valley_bonus = 0.16 if cell["is_valley"] and global_progress > 0.28 else 0.0
        mountain_delay = -0.10 if cell["is_mountain"] and global_progress < 0.65 else 0.0

        target = clamp(
            cell["target"]
            + 0.55 * network_pull * global_progress
            + 0.40 * corridor_pull * corridor_strength
            + coast_bonus
            + valley_bonus
            + mountain_delay
        )

        # Smooth recovery with slight local variation.
        local_rate = 0.010 + 0.014 * network_pull + 0.012 * corridor_pull
        cell["recovery"] += (target - cell["recovery"]) * local_rate * speed
        cell["recovery"] = clamp(cell["recovery"])

        r = cell["recovery"]

        # Color transitions: damaged brown -> recovering yellow-green -> forest green.
        if cell["damage"] > 0.15 and r < 0.42:
            col = mix_color(DAMAGED, RECOVERING, r / 0.42)
            damaged_count += 1
        else:
            col = mix_color(RECOVERING, FOREST, clamp((r - 0.30) / 0.70))

        if cell["is_mountain"]:
            col = mix_color(col, MOUNTAIN, 0.28)
        if cell["is_coast"]:
            col = mix_color(col, COAST, 0.20)

        # Small pulse as a patch transitions into healthy forest.
        pulse = 0.018 * math.sin(time_value * 3.4 + cell["phase"]) * clamp((r - 0.4) / 0.6)
        height = cell["h"] * (0.72 + 0.43 * r) + pulse
        cell["obj"].size.y = max(0.035, height)
        cell["obj"].pos.y = cell["obj"].size.y / 2.0
        cell["obj"].color = col

        if r > 0.68:
            recovered_count += 1

    # Protected rings pulse outward to show recovery expansion.
    for item in recovery_rings:
        rr = item["ring"]
        phase = item["phase"]
        wave = (time_value * 0.42 + phase) % 1.0
        rr.radius = 0.25 + 1.25 * wave
        rr.opacity = 0.44 * (1.0 - wave)
        rr.thickness = 0.016 + 0.014 * (1.0 - wave)

    # Corridor beam brightness and pulses.
    for i, c in enumerate(corridors):
        beam = c["beam"]
        pulse = c["pulse"]
        beam.opacity = 0.12 + 0.42 * corridor_strength * (0.72 + 0.28 * math.sin(time_value * 2.0 + c["phase"]))
        beam.radius = 0.025 + 0.025 * corridor_strength

        q = (time_value * (0.15 + 0.03 * i) + c["phase"]) % 1.0
        pulse.pos = c["a"] + (c["b"] - c["a"]) * q
        pulse.radius = 0.055 + 0.07 * corridor_strength
        pulse.opacity = 0.35 + 0.40 * corridor_strength

    # Monitoring markers crawl through reconnecting protected zones.
    for i, m in enumerate(monitor_markers):
        c = corridors[i % len(corridors)]
        q = (time_value * (0.09 + 0.015 * i) + i * 0.21) % 1.0
        m.pos = c["a"] + (c["b"] - c["a"]) * q + vector(0, 0.12 + 0.04 * math.sin(time_value * 4 + i), 0)
        m.radius = 0.055 + 0.025 * math.sin(time_value * 3 + i) ** 2

    # Beacons brighten as the network becomes continuous.
    for idx, (_, ring_marker, beacon) in enumerate(protected_markers):
        glow = 0.5 + 0.5 * math.sin(time_value * 2.5 + idx)
        beacon.radius = 0.10 + 0.035 * glow + 0.05 * corridor_strength
        ring_marker.thickness = 0.025 + 0.025 * glow
        ring_marker.opacity = 0.38 + 0.25 * corridor_strength

    recovered_percent = 100.0 * recovered_count / max(1, len(cells))
    damaged_percent = 100.0 * damaged_count / max(1, len(cells))
    connected_percent = int(100 * corridor_strength)

    status_label.text = (
        f"Recovery progress: {int(global_progress * 100)}%\n"
        f"Healthy forest cells: {recovered_percent:4.1f}%\n"
        f"Still damaged cells: {damaged_percent:4.1f}%\n"
        f"Protected corridor connection: {connected_percent}%\n"
        f"Speed: {speed:.2f}x\n"
        "Space pause | R reset | C corridors | M monitors"
    )
