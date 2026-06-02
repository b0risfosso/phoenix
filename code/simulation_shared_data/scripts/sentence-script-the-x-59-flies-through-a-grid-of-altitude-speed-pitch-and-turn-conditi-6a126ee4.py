"""
X-59 Envelope Expansion Flight
VPython simulation

Story seed:
NASA's X-59 flies through a grid of altitude, speed, pitch, and turn conditions,
lighting up each test zone as engineers confirm the aircraft can safely move
closer to supersonic speed.

Controls:
  Space  - pause / resume
  R      - reset the current envelope campaign
  V      - toggle camera follow mode
  G      - toggle grid emphasis

Compatibility notes:
  - Uses ring(...) instead of torus(...).
  - Does not use curve.points; trail point count uses npoints only.
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="X-59 Envelope Expansion Flight",
    width=1180,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 1.8, 0),
)
scene.forward = vector(-0.58, -0.25, -0.78)
scene.up = vector(0, 1, 0)
scene.range = 42
scene.autoscale = False
scene.userzoom = True
scene.userspin = True

# -----------------------------
# Colors
# -----------------------------
SKY = vector(0.78, 0.90, 1.0)
GRID = vector(0.55, 0.68, 0.78)
GRID_SOFT = vector(0.75, 0.84, 0.90)
X59_GOLD = vector(1.0, 0.84, 0.30)
X59_DEEP = vector(0.20, 0.28, 0.45)
X59_NOSE = vector(0.95, 0.95, 0.88)
ENGINE = vector(0.70, 0.72, 0.78)
SAFE_GREEN = vector(0.18, 0.75, 0.38)
CAUTION = vector(1.0, 0.65, 0.22)
TEST_BLUE = vector(0.12, 0.46, 0.95)
TEST_PURPLE = vector(0.60, 0.38, 0.95)
WHITE = vector(1, 1, 1)
DARK = vector(0.14, 0.20, 0.30)
RED = vector(1.0, 0.25, 0.20)

# -----------------------------
# Global settings
# -----------------------------
paused = False
follow_camera = True
grid_emphasis = True
campaign_round = 1
current_zone_index = 0
zone_timer = 0.0
zone_duration = 8.5
confirmed_count = 0

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, f):
    return a + (b - a) * clamp(f, 0, 1)

def smoothstep(x):
    x = clamp(x, 0, 1)
    return x * x * (3 - 2 * x)

# -----------------------------
# Environment
# -----------------------------
# Earth/horizon plane far below
horizon = box(
    pos=vector(0, -10.5, 0),
    size=vector(140, 0.15, 80),
    color=vector(0.72, 0.89, 0.72),
    opacity=0.42,
)

# Soft cloud strips
clouds = []
for i in range(22):
    c = ellipsoid(
        pos=vector(random.uniform(-58, 58), random.uniform(-8.7, -6.2), random.uniform(-28, 28)),
        length=random.uniform(4.0, 9.0),
        height=random.uniform(0.25, 0.6),
        width=random.uniform(1.4, 3.2),
        color=WHITE,
        opacity=0.35,
    )
    clouds.append(c)

# Supersonic threshold gate near the far end
mach_gate = ring(
    pos=vector(30, 4.5, 0),
    axis=vector(1, 0, 0),
    radius=6.0,
    thickness=0.08,
    color=RED,
    opacity=0.45,
)
mach_gate_label = label(
    pos=mach_gate.pos + vector(0, 7.0, 0),
    text="MACH 1 APPROACH GATE",
    height=13,
    color=RED,
    box=False,
    opacity=0,
)

# -----------------------------
# Envelope grid
# -----------------------------
# Axes: x = speed/Mach expansion, y = altitude, z = pitch/turn offset
axis_x = arrow(pos=vector(-32, -4, -14), axis=vector(66, 0, 0), shaftwidth=0.08, color=GRID)
axis_y = arrow(pos=vector(-32, -4, -14), axis=vector(0, 24, 0), shaftwidth=0.08, color=GRID)
axis_z = arrow(pos=vector(-32, -4, -14), axis=vector(0, 0, 29), shaftwidth=0.08, color=GRID)
label(pos=axis_x.pos + axis_x.axis + vector(2, 0, 0), text="speed →", height=11, box=False, color=DARK)
label(pos=axis_y.pos + axis_y.axis + vector(0, 1.5, 0), text="altitude", height=11, box=False, color=DARK)
label(pos=axis_z.pos + axis_z.axis + vector(0, 0, 2), text="pitch / turn", height=11, box=False, color=DARK)

grid_lines = []
# Speed-altitude grid at three pitch/turn layers
for z in [-12, 0, 12]:
    for x in range(-30, 31, 10):
        line = curve(pos=[vector(x, -4, z), vector(x, 20, z)], color=GRID_SOFT, radius=0.025)
        grid_lines.append(line)
    for y in range(-4, 21, 4):
        line = curve(pos=[vector(-30, y, z), vector(30, y, z)], color=GRID_SOFT, radius=0.025)
        grid_lines.append(line)
# Cross pitch/turn rails
for x in range(-30, 31, 10):
    for y in [-4, 4, 12, 20]:
        line = curve(pos=[vector(x, y, -12), vector(x, y, 12)], color=GRID_SOFT, radius=0.02)
        grid_lines.append(line)

# Test zones: progressively closer to Mach 1, with different altitude/pitch/turn settings
base_zones = [
    {"name": "Low-speed handling",      "mach": 0.58, "alt": 2.0,  "pitch": -5, "turn": -9,  "risk": 0.12},
    {"name": "Climb stability",          "mach": 0.64, "alt": 7.0,  "pitch": 7,  "turn": -4,  "risk": 0.16},
    {"name": "Level acceleration",       "mach": 0.70, "alt": 10.0, "pitch": 0,  "turn": 0,   "risk": 0.18},
    {"name": "Gentle bank",              "mach": 0.76, "alt": 12.5, "pitch": 3,  "turn": 8,   "risk": 0.22},
    {"name": "High-altitude trim",       "mach": 0.82, "alt": 16.0, "pitch": -2, "turn": -7,  "risk": 0.28},
    {"name": "Pitch response check",     "mach": 0.87, "alt": 14.0, "pitch": 10, "turn": 2,   "risk": 0.34},
    {"name": "Turn response check",      "mach": 0.91, "alt": 13.0, "pitch": -4, "turn": 11,  "risk": 0.42},
    {"name": "Transonic edge survey",    "mach": 0.95, "alt": 17.0, "pitch": 5,  "turn": -10, "risk": 0.55},
    {"name": "Near-supersonic corridor", "mach": 0.98, "alt": 18.5, "pitch": 1,  "turn": 0,   "risk": 0.68},
]

def zone_position(zone):
    # Map Mach 0.55..1.0 to x -29..29, altitude 0..20 to y -2..20, turn -12..12 to z
    x = -30 + (zone["mach"] - 0.55) / 0.45 * 60
    y = -3.2 + zone["alt"] / 20.0 * 22
    z = clamp(zone["turn"], -12, 12)
    return vector(x, y, z)

zone_markers = []
zone_labels = []
for i, zdata in enumerate(base_zones):
    p = zone_position(zdata)
    marker = box(
        pos=p,
        size=vector(3.0, 1.1, 2.4),
        color=TEST_BLUE,
        opacity=0.18,
    )
    ring_marker = ring(
        pos=p + vector(0, 0.12, 0),
        axis=vector(0, 1, 0),
        radius=1.9,
        thickness=0.04,
        color=TEST_BLUE,
        opacity=0.35,
    )
    lab = label(
        pos=p + vector(0, 1.8, 0),
        text=str(i + 1),
        height=10,
        color=DARK,
        box=False,
        opacity=0,
    )
    zone_markers.append({"box": marker, "ring": ring_marker, "confirmed": False})
    zone_labels.append(lab)

# -----------------------------
# X-59 aircraft model
# -----------------------------
aircraft = compound([
    # Long slender fuselage
    cylinder(pos=vector(-3.2, 0, 0), axis=vector(6.4, 0, 0), radius=0.34, color=X59_GOLD),
    cone(pos=vector(3.15, 0, 0), axis=vector(2.6, 0, 0), radius=0.29, color=X59_NOSE),
    cone(pos=vector(-3.35, 0, 0), axis=vector(-0.7, 0, 0), radius=0.34, color=X59_DEEP),
    # Canopy
    ellipsoid(pos=vector(0.7, 0.35, 0), length=1.0, height=0.32, width=0.48, color=vector(0.20, 0.42, 0.68), opacity=0.82),
    # Wings
    box(pos=vector(-0.7, -0.03, 0), size=vector(1.5, 0.08, 4.4), color=X59_DEEP),
    box(pos=vector(-0.7, -0.04, 1.6), size=vector(2.5, 0.07, 0.38), color=X59_DEEP),
    box(pos=vector(-0.7, -0.04, -1.6), size=vector(2.5, 0.07, 0.38), color=X59_DEEP),
    # Tailplanes / vertical fin
    box(pos=vector(-3.2, 0.2, 0), size=vector(0.7, 1.2, 0.12), color=X59_DEEP),
    box(pos=vector(-3.15, -0.02, 0.9), size=vector(0.9, 0.06, 1.2), color=X59_DEEP),
    box(pos=vector(-3.15, -0.02, -0.9), size=vector(0.9, 0.06, 1.2), color=X59_DEEP),
    # Engine glow
    cylinder(pos=vector(-4.05, 0, 0), axis=vector(-0.25, 0, 0), radius=0.26, color=ENGINE),
], pos=zone_position(base_zones[0]) + vector(-7, -1.5, -5))
aircraft.axis = vector(1, 0, 0)

# Aircraft trail
flight_trail = curve(color=vector(0.05, 0.45, 0.95), radius=0.06)

# Speed/control indicators near aircraft
nose_vector = arrow(pos=aircraft.pos, axis=vector(3, 0, 0), shaftwidth=0.05, color=SAFE_GREEN)
alignment_beam = curve(pos=[aircraft.pos, zone_position(base_zones[0])], color=TEST_PURPLE, radius=0.025)

# Sonic pressure rings that pulse more strongly near Mach 1
pressure_rings = []
for i in range(5):
    pr = ring(
        pos=aircraft.pos - vector(i * 1.1, 0, 0),
        axis=vector(1, 0, 0),
        radius=1.0 + i * 0.25,
        thickness=0.035,
        color=vector(0.30, 0.65, 1.0),
        opacity=0.12,
    )
    pressure_rings.append(pr)

# Engineer console / dashboard
panel = box(pos=vector(-43, 21, -18), size=vector(0.35, 13.0, 17.5), color=WHITE, opacity=0.72)
status_label = label(
    pos=panel.pos + vector(0.4, 4.8, 0),
    text="",
    height=11,
    color=DARK,
    box=False,
    align="left",
    opacity=0,
)
condition_label = label(
    pos=panel.pos + vector(0.4, -1.2, 0),
    text="",
    height=10,
    color=DARK,
    box=False,
    align="left",
    opacity=0,
)

# Confirmation lamps along the console
lamps = []
for i in range(len(base_zones)):
    lamp = sphere(
        pos=panel.pos + vector(0.6, 4.6 - i * 1.05, -7.2),
        radius=0.22,
        color=GRID_SOFT,
        emissive=False,
    )
    lamps.append(lamp)

# -----------------------------
# State management
# -----------------------------
current_pos = vector(aircraft.pos.x, aircraft.pos.y, aircraft.pos.z)
current_vel = vector(0.14, 0.0, 0.0)
current_pitch = 0.0
current_turn = 0.0
current_mach = 0.55
altitude_reading = 0.0
safety_margin = 1.0
last_zone_name = ""


def reset_campaign():
    global campaign_round, current_zone_index, zone_timer, confirmed_count
    global current_pos, current_vel, current_pitch, current_turn, current_mach, altitude_reading, safety_margin
    global flight_trail
    current_zone_index = 0
    zone_timer = 0.0
    confirmed_count = 0
    current_pos = zone_position(base_zones[0]) + vector(-7, -1.5, -5)
    current_vel = vector(0.14, 0.0, 0.0)
    current_pitch = 0.0
    current_turn = 0.0
    current_mach = 0.55
    altitude_reading = 0.0
    safety_margin = 1.0
    aircraft.pos = current_pos
    aircraft.axis = vector(1, 0, 0)
    flight_trail.visible = False
    flight_trail = curve(color=vector(0.05, 0.45, 0.95), radius=0.06)
    for i, zm in enumerate(zone_markers):
        zm["confirmed"] = False
        zm["box"].color = TEST_BLUE
        zm["box"].opacity = 0.18
        zm["ring"].color = TEST_BLUE
        zm["ring"].opacity = 0.35
        lamps[i].color = GRID_SOFT
        lamps[i].emissive = False


def next_zone():
    global current_zone_index, zone_timer, confirmed_count, campaign_round
    if current_zone_index < len(base_zones):
        zone_markers[current_zone_index]["confirmed"] = True
        zone_markers[current_zone_index]["box"].color = SAFE_GREEN
        zone_markers[current_zone_index]["box"].opacity = 0.36
        zone_markers[current_zone_index]["ring"].color = SAFE_GREEN
        zone_markers[current_zone_index]["ring"].opacity = 0.70
        lamps[current_zone_index].color = SAFE_GREEN
        lamps[current_zone_index].emissive = True
        confirmed_count += 1
    current_zone_index += 1
    zone_timer = 0.0
    if current_zone_index >= len(base_zones):
        campaign_round += 1
        # Hold briefly at the near-supersonic gate then restart with a slightly different cadence
        current_zone_index = 0
        for zm in zone_markers:
            zm["box"].opacity = 0.16
            zm["ring"].opacity = 0.28
        confirmed_count = 0


def keydown(evt):
    global paused, follow_camera, grid_emphasis
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_campaign()
    elif key == "v":
        follow_camera = not follow_camera
    elif key == "g":
        grid_emphasis = not grid_emphasis

scene.bind("keydown", keydown)

# -----------------------------
# Animation loop
# -----------------------------
t = 0.0
dt = 1.0 / 60.0

while True:
    rate(60)
    if paused:
        status_label.text = "PAUSED\nSpace: resume\nR: reset\nV: camera\nG: grid"
        continue

    t += dt
    zone_timer += dt

    # Move clouds slowly for altitude cue
    for i, c in enumerate(clouds):
        c.pos.x += 0.018 + 0.008 * math.sin(t * 0.3 + i)
        if c.pos.x > 64:
            c.pos.x = -64
            c.pos.z = random.uniform(-28, 28)

    zone = base_zones[current_zone_index]
    target = zone_position(zone)
    phase = smoothstep(zone_timer / zone_duration)

    # Simulated control corrections: overshoot, then lock into zone
    wobble_amp = (1.0 - phase) * (1.5 + zone["risk"] * 2.0)
    desired = target + vector(
        math.sin(t * 1.2 + current_zone_index) * wobble_amp,
        math.sin(t * 0.9 + current_zone_index * 0.7) * wobble_amp * 0.45,
        math.cos(t * 1.4 + current_zone_index) * wobble_amp,
    )

    # Velocity damps toward desired path
    to_desired = desired - current_pos
    current_vel = current_vel * 0.90 + to_desired * (0.018 + 0.020 * phase)
    # Higher Mach zones move a little faster along x
    current_vel.x += 0.0025 * (zone["mach"] - current_mach)
    current_pos += current_vel

    # Readouts approach test condition
    current_mach = lerp(current_mach, zone["mach"] + 0.008 * math.sin(t * 2.2), 0.035)
    altitude_reading = lerp(altitude_reading, zone["alt"] + 0.35 * math.sin(t * 1.1), 0.04)
    current_pitch = lerp(current_pitch, zone["pitch"] + 0.8 * math.sin(t * 2.0), 0.05)
    current_turn = lerp(current_turn, zone["turn"] + 1.2 * math.cos(t * 1.6), 0.05)

    # Safety margin narrows near Mach 1; stabilizes as zone confirmation approaches
    raw_margin = 1.0 - zone["risk"] + 0.30 * phase - 0.05 * abs(math.sin(t * 2.5))
    safety_margin = clamp(raw_margin, 0.12, 1.0)

    # Aircraft orientation: angle from velocity with pitch/turn influence
    forward = norm(vector(1.0, 0.055 * current_pitch, 0.045 * current_turn))
    aircraft.pos = current_pos
    aircraft.axis = forward
    aircraft.up = vector(0, 1, 0)

    # Trail: avoid curve.points, only track npoints
    flight_trail.append(pos=current_pos)
    if hasattr(flight_trail, "npoints") and flight_trail.npoints > 520:
        # VPython curve trimming APIs vary, so start a new visible segment instead of reading points.
        old = flight_trail
        old.opacity = 0.18
        flight_trail = curve(color=vector(0.05, 0.45, 0.95), radius=0.06)
        flight_trail.append(pos=current_pos)

    # Current target beam
    alignment_beam.clear()
    alignment_beam.append(pos=current_pos)
    alignment_beam.append(pos=target)
    alignment_beam.color = SAFE_GREEN if phase > 0.74 else TEST_PURPLE
    alignment_beam.radius = 0.025 + 0.02 * phase

    # Nose vector
    nose_vector.pos = current_pos + forward * 2.2
    nose_vector.axis = forward * (2.4 + 2.2 * current_mach)
    nose_vector.color = CAUTION if current_mach > 0.92 else SAFE_GREEN

    # Test zone marker activity
    for i, zm in enumerate(zone_markers):
        pulse = 0.5 + 0.5 * math.sin(t * 3.2 + i)
        zm["ring"].radius = 1.65 + 0.34 * pulse
        if i == current_zone_index:
            zm["box"].color = CAUTION if current_mach > 0.92 else TEST_PURPLE
            zm["box"].opacity = 0.24 + 0.28 * pulse
            zm["ring"].color = CAUTION if current_mach > 0.92 else TEST_PURPLE
            zm["ring"].opacity = 0.50 + 0.36 * pulse
        elif zm["confirmed"]:
            zm["box"].color = SAFE_GREEN
            zm["ring"].color = SAFE_GREEN
        else:
            zm["box"].color = TEST_BLUE
            zm["box"].opacity = 0.13 if not grid_emphasis else 0.18
            zm["ring"].color = TEST_BLUE
            zm["ring"].opacity = 0.22 if not grid_emphasis else 0.32

    # Grid emphasis toggle
    for gl in grid_lines:
        gl.opacity = 0.52 if grid_emphasis else 0.16
        gl.radius = 0.025 if grid_emphasis else 0.015

    # Sonic/pressure rings intensify as Mach increases
    mach_intensity = clamp((current_mach - 0.75) / 0.25, 0, 1)
    for i, pr in enumerate(pressure_rings):
        spread = i * (0.95 + 0.3 * mach_intensity)
        pr.pos = current_pos - forward * (1.0 + spread)
        pr.axis = forward
        pr.radius = 0.8 + i * 0.28 + mach_intensity * (0.6 + 0.18 * math.sin(t * 4 + i))
        pr.opacity = 0.04 + mach_intensity * (0.14 + 0.05 * math.sin(t * 5 + i))
        pr.color = CAUTION if current_mach > 0.92 else vector(0.30, 0.65, 1.0)

    # Mach gate pulse
    mach_gate.radius = 5.7 + 0.45 * math.sin(t * 2.6)
    mach_gate.opacity = 0.25 + 0.35 * mach_intensity
    mach_gate.color = CAUTION if current_mach > 0.92 else RED

    # Confirm zone after stable dwell near target
    dist = mag(current_pos - target)
    stable = dist < 2.6 and phase > 0.70 and safety_margin > 0.20
    if stable and zone_timer > zone_duration * 0.78:
        next_zone()

    # Dashboard
    margin_word = "CONFIRMING" if stable else ("CAUTION" if safety_margin < 0.42 else "STABLE")
    status_label.text = (
        f"X-59 ENVELOPE EXPANSION\n"
        f"Round: {campaign_round}\n"
        f"Test zone: {current_zone_index + 1} / {len(base_zones)}\n"
        f"Confirmed zones: {confirmed_count}\n"
        f"Mode: {margin_word}\n"
        f"Space pause | R reset | V camera"
    )
    condition_label.text = (
        f"Current condition:\n"
        f"{zone['name']}\n\n"
        f"Mach: {current_mach:0.2f}\n"
        f"Altitude index: {altitude_reading:0.1f}\n"
        f"Pitch: {current_pitch:+0.1f} deg\n"
        f"Turn: {current_turn:+0.1f} deg\n"
        f"Safety margin: {safety_margin:0.2f}\n"
        f"Alignment error: {dist:0.1f}"
    )

    # Camera follows but allows manual mouse movement to continue working if toggled off
    if follow_camera:
        scene.center = lerp(scene.center, current_pos + vector(3, 2.0, 0), 0.035)
        scene.range = lerp(scene.range, 28 + 10 * mach_intensity, 0.015)
