"""
Fiftieth Starlink Pulse
A VPython simulation of repeated Starlink-style launch completions adding
new glowing orbital rings around Earth until the counter reaches 50.

Run with:
    python fiftieth_starlink_pulse.py

Controls:
    Space  - pause / resume
    R      - reset simulation
    F      - add one launch immediately
    Up     - speed up launch cadence
    Down   - slow down launch cadence
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene = canvas(
    title="Fiftieth Starlink Pulse — 50th Mission Orbital Brightening",
    width=1200,
    height=780,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 10, 22)
scene.camera.axis = vector(0, -8, -22)
scene.forward = vector(0, -0.25, -1)
scene.up = vector(0, 1, 0)
scene.range = 11

# -----------------------------
# Constants
# -----------------------------
MAX_LAUNCHES = 50
EARTH_RADIUS = 2.35
BASE_ORBIT_RADIUS = 4.0
RING_GAP = 0.055
SATELLITES_PER_RING = 18
DEFAULT_LAUNCH_INTERVAL = 0.75

paused = False
launch_count = 0
launch_interval = DEFAULT_LAUNCH_INTERVAL
launch_timer = 0.0
time_value = 0.0
pulse_timer = 0.0

rings = []
satellites = []
launch_flares = []
data_beams = []

# -----------------------------
# Text labels / dashboard
# -----------------------------
title_label = label(
    pos=vector(0, 6.2, 0),
    text="Fiftieth Starlink Pulse",
    height=24,
    color=vector(0.05, 0.09, 0.18),
    box=False,
    opacity=0,
)

counter_label = label(
    pos=vector(-8.4, 5.2, 0),
    text="Launches completed: 0 / 50",
    height=18,
    color=vector(0.05, 0.09, 0.18),
    box=False,
    opacity=0,
)

sat_label = label(
    pos=vector(-8.4, 4.65, 0),
    text="Orbital rings active: 0",
    height=14,
    color=vector(0.12, 0.20, 0.32),
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(6.8, 5.15, 0),
    text="Countdown cycling",
    height=15,
    color=vector(0.12, 0.22, 0.38),
    box=False,
    opacity=0,
)

controls_label = label(
    pos=vector(0, -6.35, 0),
    text="Space pause/resume | R reset | F force launch | Up/Down cadence",
    height=12,
    color=vector(0.22, 0.27, 0.33),
    box=False,
    opacity=0,
)

# -----------------------------
# Earth and orbital map elements
# -----------------------------
earth = sphere(
    pos=vector(0, 0, 0),
    radius=EARTH_RADIUS,
    color=vector(0.22, 0.48, 0.85),
    shininess=0.35,
)

# Soft atmosphere shell
atmosphere = sphere(
    pos=vector(0, 0, 0),
    radius=EARTH_RADIUS * 1.035,
    color=vector(0.55, 0.78, 1.0),
    opacity=0.22,
    shininess=0.2,
)

# Simple continent marks on the globe
continents = []
continent_specs = [
    (-0.8, 0.55, 0.90, 0.26, 0.18),
    (0.65, 0.38, 0.76, 0.31, 0.15),
    (-1.35, -0.22, 0.66, 0.22, 0.12),
    (1.28, -0.48, 0.57, 0.20, 0.10),
    (0.10, -1.02, 0.40, 0.24, 0.08),
]
for lon, lat, size, sx, sy in continent_specs:
    x = EARTH_RADIUS * math.cos(lat) * math.cos(lon)
    y = EARTH_RADIUS * math.sin(lat)
    z = EARTH_RADIUS * math.cos(lat) * math.sin(lon)
    mark = ellipsoid(
        pos=vector(x, y, z) * 1.012,
        length=size * sx,
        height=size * sy,
        width=0.035,
        color=vector(0.35, 0.68, 0.38),
        opacity=0.86,
    )
    mark.axis = norm(vector(x, y, z)) * 0.03
    continents.append(mark)

# Ground station nodes that brighten as the orbital grid grows
station_positions = []
for lon, lat in [(-1.5, 0.2), (-0.45, 0.7), (0.4, -0.15), (1.4, 0.35), (2.1, -0.45), (-2.3, -0.35)]:
    x = EARTH_RADIUS * math.cos(lat) * math.cos(lon)
    y = EARTH_RADIUS * math.sin(lat)
    z = EARTH_RADIUS * math.cos(lat) * math.sin(lon)
    station_positions.append(vector(x, y, z) * 1.07)

ground_stations = [
    sphere(pos=p, radius=0.08, color=vector(1.0, 0.9, 0.35), emissive=True) for p in station_positions
]

# Launch timeline bar
bar_base = vector(-7.4, -4.9, 0)
timeline_back = box(
    pos=bar_base + vector(3.7, 0, 0),
    size=vector(7.4, 0.08, 0.08),
    color=vector(0.74, 0.78, 0.84),
)
timeline_fill = box(
    pos=bar_base,
    size=vector(0.01, 0.12, 0.12),
    color=vector(0.24, 0.55, 1.0),
    emissive=True,
)
timeline_ticks = []
for i in range(0, MAX_LAUNCHES + 1, 10):
    x = bar_base.x + 7.4 * (i / MAX_LAUNCHES)
    tick = box(pos=vector(x, -4.9, 0), size=vector(0.035, 0.35, 0.035), color=vector(0.45, 0.50, 0.60))
    timeline_ticks.append(tick)
    label(pos=vector(x, -5.25, 0), text=str(i), height=9, box=False, opacity=0, color=vector(0.3, 0.35, 0.45))

# Countdown orb beside the scene
countdown_orb = sphere(pos=vector(7.2, -4.9, 0), radius=0.22, color=vector(1.0, 0.58, 0.18), emissive=True)
countdown_ring = ring(pos=countdown_orb.pos, axis=vector(0, 1, 0), radius=0.55, thickness=0.025, color=vector(1.0, 0.72, 0.24), opacity=0.65)

# -----------------------------
# Helpers
# -----------------------------
def orbital_point(radius, angle, inclination, phase=0.0):
    """Point on a tilted circular orbit."""
    x = radius * math.cos(angle)
    z = radius * math.sin(angle)
    y = z * math.sin(inclination)
    z2 = z * math.cos(inclination)
    # Rotate whole ring slightly around vertical axis for lane diversity.
    c = math.cos(phase)
    s = math.sin(phase)
    return vector(x * c - z2 * s, y, x * s + z2 * c)


def ring_color_for_launch(n):
    progress = n / MAX_LAUNCHES
    return vector(0.18 + 0.30 * progress, 0.50 + 0.36 * progress, 1.00)


def update_dashboard():
    global timeline_fill
    progress = launch_count / MAX_LAUNCHES
    counter_label.text = f"Launches completed: {launch_count} / {MAX_LAUNCHES}"
    sat_label.text = f"Orbital rings active: {len(rings)} | Satellites shown: {len(satellites)}"
    status_label.text = "50th mission reached — global map brightened" if launch_count >= MAX_LAUNCHES else "Countdown cycling"

    fill_len = max(0.01, 7.4 * progress)
    timeline_fill.size = vector(fill_len, 0.12, 0.12)
    timeline_fill.pos = bar_base + vector(fill_len / 2, 0, 0)

    glow = min(1.0, 0.22 + progress * 0.78)
    atmosphere.opacity = 0.18 + 0.25 * progress
    for st in ground_stations:
        st.radius = 0.075 + 0.06 * glow
        st.color = vector(1.0, 0.78 + 0.2 * glow, 0.25)


def make_launch_flare(n):
    """Create a small launch flame pulse rising from Earth into orbit."""
    lon = -2.2 + (n % 9) * 0.5
    lat = -0.65 + ((n * 7) % 10) * 0.13
    launch_site = vector(
        EARTH_RADIUS * math.cos(lat) * math.cos(lon),
        EARTH_RADIUS * math.sin(lat),
        EARTH_RADIUS * math.cos(lat) * math.sin(lon),
    ) * 1.08
    outward = norm(launch_site)
    flare = sphere(
        pos=launch_site,
        radius=0.12,
        color=vector(1.0, 0.45, 0.08),
        emissive=True,
    )
    trail = curve(color=vector(1.0, 0.62, 0.20), radius=0.018)
    trail.append(launch_site)
    launch_flares.append({"body": flare, "trail": trail, "origin": launch_site, "dir": outward, "age": 0.0, "life": 1.25})


def add_data_beam():
    if not satellites or not ground_stations:
        return
    sat = random.choice(satellites)["body"]
    station = random.choice(ground_stations)
    beam = curve(color=vector(0.22, 0.68, 1.0), radius=0.012)
    beam.append(sat.pos)
    beam.append(station.pos)
    data_beams.append({"beam": beam, "age": 0.0, "life": 0.55})


def add_launch(force=False):
    global launch_count, pulse_timer
    if launch_count >= MAX_LAUNCHES:
        return

    launch_count += 1
    n = launch_count
    radius = BASE_ORBIT_RADIUS + RING_GAP * n
    inclination = radians(18 + (n * 11) % 58)
    phase = radians((n * 23) % 360)
    color_val = ring_color_for_launch(n)

    orbit_ring = ring(
        pos=vector(0, 0, 0),
        axis=vector(0, math.cos(inclination), math.sin(inclination)),
        radius=radius,
        thickness=0.012 + 0.002 * min(1, n / MAX_LAUNCHES),
        color=color_val,
        opacity=0.18 + 0.36 * (n / MAX_LAUNCHES),
        emissive=True,
    )
    rings.append({
        "body": orbit_ring,
        "base_radius": radius,
        "pulse": 1.0,
        "spin": 0.001 + 0.00004 * n,
        "inclination": inclination,
    })

    # Satellites on this ring are sparse to keep performance stable.
    for k in range(SATELLITES_PER_RING):
        angle = 2 * math.pi * k / SATELLITES_PER_RING + random.uniform(-0.035, 0.035)
        p = orbital_point(radius, angle, inclination, phase)
        sat = box(
            pos=p,
            size=vector(0.11, 0.035, 0.055),
            color=vector(0.94, 0.96, 1.0),
            emissive=True,
            shininess=0.7,
        )
        sat.axis = norm(cross(p, vector(0, 1, 0))) if mag(cross(p, vector(0, 1, 0))) > 0.001 else vector(1, 0, 0)
        panel_l = box(pos=p + vector(0, 0.055, 0), size=vector(0.035, 0.13, 0.01), color=vector(0.12, 0.32, 0.7), opacity=0.85)
        panel_r = box(pos=p - vector(0, 0.055, 0), size=vector(0.035, 0.13, 0.01), color=vector(0.12, 0.32, 0.7), opacity=0.85)
        satellites.append({
            "body": sat,
            "panel_l": panel_l,
            "panel_r": panel_r,
            "radius": radius,
            "angle": angle,
            "speed": 0.18 + random.random() * 0.035,
            "inclination": inclination,
            "phase": phase,
            "ring_index": n,
        })

    make_launch_flare(n)
    for _ in range(2 if n < MAX_LAUNCHES else 8):
        add_data_beam()

    pulse_timer = 0.45
    update_dashboard()


def reset_simulation():
    global launch_count, launch_timer, time_value, pulse_timer, paused, rings, satellites, launch_flares, data_beams
    for item in rings:
        item["body"].visible = False
    for sat in satellites:
        sat["body"].visible = False
        sat["panel_l"].visible = False
        sat["panel_r"].visible = False
    for flare in launch_flares:
        flare["body"].visible = False
        flare["trail"].visible = False
    for beam in data_beams:
        beam["beam"].visible = False

    rings = []
    satellites = []
    launch_flares = []
    data_beams = []
    launch_count = 0
    launch_timer = 0.0
    time_value = 0.0
    pulse_timer = 0.0
    paused = False
    earth.radius = EARTH_RADIUS
    atmosphere.radius = EARTH_RADIUS * 1.035
    update_dashboard()


def handle_key(evt):
    global paused, launch_interval
    key = evt.key
    if key == " ":
        paused = not paused
        status_label.text = "Paused" if paused else "Countdown cycling"
    elif key in ("r", "R"):
        reset_simulation()
    elif key in ("f", "F"):
        add_launch(force=True)
    elif key == "up":
        launch_interval = max(0.18, launch_interval * 0.78)
    elif key == "down":
        launch_interval = min(2.5, launch_interval * 1.25)


scene.bind("keydown", handle_key)
update_dashboard()

# -----------------------------
# Main animation loop
# -----------------------------
last_t = 0.0
while True:
    rate(60)
    dt = 1.0 / 60.0

    if paused:
        countdown_ring.rotate(angle=0.01, axis=vector(0, 1, 0), origin=countdown_ring.pos)
        continue

    time_value += dt
    launch_timer += dt

    # Earth and atmosphere motion
    earth.rotate(angle=0.0025, axis=vector(0, 1, 0), origin=earth.pos)
    atmosphere.rotate(angle=0.0015, axis=vector(0, 1, 0), origin=atmosphere.pos)
    for c in continents:
        c.rotate(angle=0.0025, axis=vector(0, 1, 0), origin=earth.pos)
    for st in ground_stations:
        st.rotate(angle=0.0025, axis=vector(0, 1, 0), origin=earth.pos)

    # Add a new launch once the interval completes.
    if launch_count < MAX_LAUNCHES and launch_timer >= launch_interval:
        launch_timer = 0.0
        add_launch()

    # Countdown orb pulses toward next launch.
    cadence_progress = min(1.0, launch_timer / max(0.001, launch_interval)) if launch_count < MAX_LAUNCHES else 1.0
    countdown_orb.radius = 0.16 + 0.18 * cadence_progress
    countdown_orb.color = vector(1.0, 0.42 + 0.36 * cadence_progress, 0.10)
    countdown_ring.radius = 0.45 + 0.35 * cadence_progress
    countdown_ring.rotate(angle=0.035, axis=vector(0, 1, 0), origin=countdown_ring.pos)

    # Mission pulse when a ring is added or when 50 is reached.
    if pulse_timer > 0:
        pulse_timer = max(0.0, pulse_timer - dt)
        pulse = pulse_timer / 0.45
        earth.radius = EARTH_RADIUS * (1.0 + 0.025 * pulse)
        atmosphere.radius = EARTH_RADIUS * (1.035 + 0.075 * pulse)
    else:
        earth.radius = EARTH_RADIUS
        atmosphere.radius = EARTH_RADIUS * 1.035

    # Animate orbital rings and satellites.
    for item in rings:
        body = item["body"]
        body.rotate(angle=item["spin"], axis=vector(0, 1, 0), origin=vector(0, 0, 0))
        if item["pulse"] > 0:
            item["pulse"] = max(0.0, item["pulse"] - dt * 1.8)
            body.thickness = 0.012 + 0.045 * item["pulse"]
            body.opacity = min(0.8, body.opacity + 0.002)

    for sat in satellites:
        sat["angle"] += sat["speed"] * dt
        p = orbital_point(sat["radius"], sat["angle"], sat["inclination"], sat["phase"])
        sat["body"].pos = p
        axis = cross(p, vector(0, 1, 0))
        if mag(axis) > 0.001:
            sat["body"].axis = norm(axis) * 0.11
        side = norm(cross(norm(p), vector(0, 1, 0))) if mag(cross(norm(p), vector(0, 1, 0))) > 0.001 else vector(1, 0, 0)
        upv = norm(cross(side, norm(p)))
        sat["panel_l"].pos = p + upv * 0.09
        sat["panel_r"].pos = p - upv * 0.09
        sat["panel_l"].axis = side * 0.035
        sat["panel_r"].axis = side * 0.035

    # Launch flare animation.
    for flare in list(launch_flares):
        flare["age"] += dt
        age_ratio = flare["age"] / flare["life"]
        flare["body"].pos = flare["origin"] + flare["dir"] * (0.25 + 2.7 * age_ratio)
        flare["body"].radius = 0.14 * (1.0 - 0.55 * age_ratio)
        flare["trail"].append(flare["body"].pos)
        if flare["age"] > flare["life"]:
            flare["body"].visible = False
            flare["trail"].visible = False
            launch_flares.remove(flare)

    # Add occasional brief data beams as the constellation becomes denser.
    if satellites and random.random() < 0.025 + 0.04 * (launch_count / MAX_LAUNCHES):
        add_data_beam()

    for beam_item in list(data_beams):
        beam_item["age"] += dt
        fade = 1.0 - beam_item["age"] / beam_item["life"]
        beam_item["beam"].radius = max(0.002, 0.014 * fade)
        beam_item["beam"].color = vector(0.18, 0.52 + 0.35 * fade, 1.0)
        if beam_item["age"] >= beam_item["life"]:
            beam_item["beam"].visible = False
            data_beams.remove(beam_item)

    # Final 50th-launch brightening: all rings breathe together.
    if launch_count >= MAX_LAUNCHES:
        breathe = 0.5 + 0.5 * math.sin(time_value * 3.0)
        atmosphere.opacity = 0.38 + 0.10 * breathe
        for i, item in enumerate(rings):
            item["body"].opacity = 0.36 + 0.22 * breathe
            if i % 7 == int(time_value * 2) % 7:
                item["body"].thickness = 0.022 + 0.012 * breathe

    update_dashboard()
