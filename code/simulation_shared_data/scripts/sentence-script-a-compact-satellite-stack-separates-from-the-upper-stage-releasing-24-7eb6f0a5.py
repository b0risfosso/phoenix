from vpython import *
import math
import random

# Twenty-Four Lights Released
# A compact satellite stack separates from the upper stage, releasing 24 small
# lights that slowly drift apart and arrange themselves into an orbital line.

scene = canvas(
    title="Twenty-Four Lights Released - Starlink Deployment Simulation",
    width=1180,
    height=720,
    background=vector(0.86, 0.91, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.55, -0.25, -1)
scene.range = 14
scene.autoscale = False

# -----------------------------
# Visual helpers
# -----------------------------
WHITE = vector(1.0, 1.0, 1.0)
SOFT_BLUE = vector(0.45, 0.66, 1.0)
DEEP_BLUE = vector(0.12, 0.22, 0.48)
ORANGE = vector(1.0, 0.55, 0.16)
YELLOW = vector(1.0, 0.88, 0.30)
PINK = vector(1.0, 0.56, 0.68)
GREEN = vector(0.25, 0.72, 0.55)
GRAY = vector(0.58, 0.62, 0.66)
DARK_GRAY = vector(0.28, 0.31, 0.36)


def clamp(value, low, high):
    return max(low, min(high, value))


def mix(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1 - t) + b * t

# -----------------------------
# Earth limb and orbital map
# -----------------------------
earth = sphere(
    pos=vector(-8.8, -5.1, -5.2),
    radius=5.2,
    color=vector(0.38, 0.65, 0.95),
    opacity=0.42,
    shininess=0.25,
)

# Subtle continent-like patches on visible Earth edge
for i in range(16):
    angle = i * 2 * math.pi / 16 + 0.2
    patch = ellipsoid(
        pos=earth.pos + vector(0.18 * math.cos(angle), 0.95 * math.sin(angle), 4.95),
        length=random.uniform(0.45, 0.9),
        height=random.uniform(0.08, 0.16),
        width=0.025,
        color=vector(0.33, 0.72, 0.45),
        opacity=0.35,
    )
    patch.rotate(angle=angle * 0.7, axis=vector(0, 0, 1))

orbit_rings = []
for j, rad in enumerate([6.8, 8.2, 9.7]):
    r = ring(
        pos=earth.pos,
        axis=vector(0.2, 1.0, 0.15),
        radius=rad,
        thickness=0.018,
        color=mix(vector(0.55, 0.68, 1.0), vector(1, 1, 1), j * 0.18),
        opacity=0.18,
    )
    orbit_rings.append(r)

# -----------------------------
# Upper stage and payload stack
# -----------------------------
stage_body = cylinder(
    pos=vector(-5.1, 0, 0),
    axis=vector(4.1, 0, 0),
    radius=0.62,
    color=WHITE,
    shininess=0.55,
)
stage_nose = cone(
    pos=stage_body.pos + stage_body.axis,
    axis=vector(0.75, 0, 0),
    radius=0.62,
    color=vector(0.86, 0.88, 0.90),
)
stage_engine = cylinder(
    pos=stage_body.pos - vector(0.30, 0, 0),
    axis=vector(0.35, 0, 0),
    radius=0.43,
    color=DARK_GRAY,
)
engine_glow = sphere(
    pos=stage_body.pos - vector(0.42, 0, 0),
    radius=0.22,
    color=ORANGE,
    emissive=True,
    opacity=0.55,
)

stage_label = label(
    pos=stage_body.pos + vector(1.2, 1.05, 0),
    text="upper stage coast",
    height=13,
    color=DEEP_BLUE,
    box=False,
    opacity=0,
)

payload_core = box(
    pos=vector(-0.35, 0, 0),
    size=vector(0.55, 1.25, 1.25),
    color=vector(0.74, 0.77, 0.80),
    shininess=0.35,
)
payload_band = ring(
    pos=payload_core.pos,
    axis=vector(1, 0, 0),
    radius=0.93,
    thickness=0.035,
    color=SOFT_BLUE,
    opacity=0.65,
)

# Stack plates to make the compact payload feel layered
stack_plates = []
for i in range(6):
    plate = box(
        pos=payload_core.pos + vector(0.035 * (i - 2.5), 0, 0),
        size=vector(0.035, 1.32, 1.32),
        color=mix(vector(0.58, 0.62, 0.68), vector(0.88, 0.91, 0.96), i / 5),
        opacity=0.62,
    )
    stack_plates.append(plate)

# Separation springs/rails
rails = []
for y in [-0.72, 0.72]:
    for z in [-0.72, 0.72]:
        rails.append(cylinder(
            pos=vector(-0.92, y, z),
            axis=vector(0.95, 0, 0),
            radius=0.025,
            color=GRAY,
        ))

# -----------------------------
# Satellites
# -----------------------------
NUM_SATS = 24
satellites = []

for i in range(NUM_SATS):
    row = i // 6
    col = i % 6
    y = (col - 2.5) * 0.28
    z = (row - 1.5) * 0.30
    start = vector(-0.22 + random.uniform(-0.025, 0.025), y, z)

    # Final orbital line bends gently upward and backward to read as an orbit track.
    spacing = 0.58
    line_x = 1.15 + i * spacing
    wave = math.sin(i * 0.55) * 0.35
    final = vector(line_x, -1.45 + 0.11 * i, wave)

    body = box(
        pos=start,
        size=vector(0.18, 0.085, 0.19),
        color=vector(0.92, 0.94, 0.98),
        emissive=False,
        shininess=0.45,
    )
    left_panel = box(
        pos=start + vector(0, -0.14, 0),
        size=vector(0.03, 0.23, 0.13),
        color=vector(0.23, 0.38, 0.82),
        opacity=0.75,
    )
    right_panel = box(
        pos=start + vector(0, 0.14, 0),
        size=vector(0.03, 0.23, 0.13),
        color=vector(0.23, 0.38, 0.82),
        opacity=0.75,
    )
    glow = sphere(
        pos=start,
        radius=0.055,
        color=YELLOW,
        emissive=True,
        opacity=0.0,
    )
    trail = curve(color=vector(1.0, 0.82, 0.28), radius=0.012, opacity=0.0)

    satellites.append({
        "body": body,
        "left": left_panel,
        "right": right_panel,
        "glow": glow,
        "trail": trail,
        "trail_positions": [],
        "start": start,
        "final": final,
        "base_final": final,
        "release_time": 2.5 + i * 0.13,
        "spin": random.uniform(0, 2 * math.pi),
        "released": False,
        "settled": False,
    })

# Final orbital guide line
orbital_line = curve(color=vector(0.38, 0.58, 1.0), radius=0.018, opacity=0.18)
for i in range(NUM_SATS):
    p = satellites[i]["final"]
    orbital_line.append(pos=p)

# -----------------------------
# Launch/deployment UI
# -----------------------------
status_label = label(
    pos=vector(2.2, 4.2, 0),
    text="Payload stack attached: 24 lights secured",
    height=16,
    color=DEEP_BLUE,
    box=True,
    line=False,
    background=vector(0.94, 0.97, 1.0),
    opacity=0.35,
)
count_label = label(
    pos=vector(2.2, 3.55, 0),
    text="released: 0 / 24",
    height=15,
    color=vector(0.12, 0.30, 0.62),
    box=False,
    opacity=0,
)
phase_label = label(
    pos=vector(-5.8, -2.2, 0),
    text="1. coast  2. separate stack  3. release lights  4. orbital line",
    height=12,
    color=vector(0.18, 0.24, 0.34),
    box=False,
    opacity=0,
)

# Data beam pulses from settled satellites
beams = []
for i in range(0, NUM_SATS, 3):
    beam = curve(color=vector(0.20, 0.66, 1.0), radius=0.01, opacity=0.0)
    beams.append((i, beam))

# Small stars, light and sparse
for i in range(90):
    sphere(
        pos=vector(random.uniform(-12, 16), random.uniform(-6, 7), random.uniform(-7, 3)),
        radius=random.uniform(0.012, 0.035),
        color=WHITE,
        emissive=True,
        opacity=random.uniform(0.25, 0.72),
    )

# Keyboard controls
paused = False
speed_scale = 1.0
show_guides = True
release_gap_scale = 1.0
line_spacing_scale = 1.0
manual_camera = False

INITIAL_SCENE_CENTER = vector(scene.center.x, scene.center.y, scene.center.z)
INITIAL_SCENE_RANGE = scene.range
STAGE_INITIALS = {
    "body": vector(stage_body.pos.x, stage_body.pos.y, stage_body.pos.z),
    "nose": vector(stage_nose.pos.x, stage_nose.pos.y, stage_nose.pos.z),
    "engine": vector(stage_engine.pos.x, stage_engine.pos.y, stage_engine.pos.z),
    "glow": vector(engine_glow.pos.x, engine_glow.pos.y, engine_glow.pos.z),
}
PAYLOAD_INITIAL = vector(payload_core.pos.x, payload_core.pos.y, payload_core.pos.z)
PLATE_OFFSETS = [vector(p.pos.x - payload_core.pos.x, p.pos.y - payload_core.pos.y, p.pos.z - payload_core.pos.z) for p in stack_plates]
RAIL_INITIALS = [vector(r.pos.x, r.pos.y, r.pos.z) for r in rails]
ORBITAL_LINE_ORIGIN = vector(1.15, -1.45, 0)

def controlled_final(sat):
    base = sat["base_final"]
    delta = base - ORBITAL_LINE_ORIGIN
    return ORBITAL_LINE_ORIGIN + delta * line_spacing_scale

def rebuild_orbital_line():
    orbital_line.clear()
    for sat in satellites:
        orbital_line.append(pos=controlled_final(sat))

def reset_simulation():
    global t, released_count, paused, manual_camera
    t = 0.0
    released_count = 0
    paused = False
    manual_camera = False
    scene.center = vector(INITIAL_SCENE_CENTER.x, INITIAL_SCENE_CENTER.y, INITIAL_SCENE_CENTER.z)
    scene.range = INITIAL_SCENE_RANGE

    stage_body.pos = vector(STAGE_INITIALS["body"].x, STAGE_INITIALS["body"].y, STAGE_INITIALS["body"].z)
    stage_nose.pos = vector(STAGE_INITIALS["nose"].x, STAGE_INITIALS["nose"].y, STAGE_INITIALS["nose"].z)
    stage_engine.pos = vector(STAGE_INITIALS["engine"].x, STAGE_INITIALS["engine"].y, STAGE_INITIALS["engine"].z)
    engine_glow.pos = vector(STAGE_INITIALS["glow"].x, STAGE_INITIALS["glow"].y, STAGE_INITIALS["glow"].z)

    payload_core.pos = vector(PAYLOAD_INITIAL.x, PAYLOAD_INITIAL.y, PAYLOAD_INITIAL.z)
    payload_band.pos = payload_core.pos
    for i, plate in enumerate(stack_plates):
        plate.pos = payload_core.pos + PLATE_OFFSETS[i]
    for i, rail in enumerate(rails):
        rail.pos = vector(RAIL_INITIALS[i].x, RAIL_INITIALS[i].y, RAIL_INITIALS[i].z)
        rail.opacity = 1.0

    for sat in satellites:
        sat["released"] = False
        sat["settled"] = False
        sat["trail_positions"].clear()
        sat["trail"].clear()
        sat["trail"].opacity = 0.0
        set_satellite_position(sat, sat["start"], 0.0, 0.0, 0.0)
    for _, beam in beams:
        beam.clear()
        beam.opacity = 0.0
    rebuild_orbital_line()

def move_camera(delta):
    global manual_camera
    manual_camera = True
    scene.center = scene.center + delta

def handle_keydown(evt):
    global paused, speed_scale, show_guides, release_gap_scale, line_spacing_scale, manual_camera
    key = evt.key
    lower = key.lower() if isinstance(key, str) else key
    if key == " ":
        paused = not paused
    elif key in ["+", "="]:
        speed_scale = min(4.0, speed_scale + 0.2)
    elif key in ["-", "_"]:
        speed_scale = max(0.10, speed_scale - 0.2)
    elif lower == "g":
        show_guides = not show_guides
        orbital_line.opacity = 0.18 if show_guides else 0.0
        for r in orbit_rings:
            r.opacity = 0.18 if show_guides else 0.0
    elif lower == "r":
        reset_simulation()
    elif lower == "b":
        release_gap_scale = 0.35 if release_gap_scale >= 1.0 else 1.0
    elif key == "[":
        line_spacing_scale = max(0.65, line_spacing_scale - 0.08)
        rebuild_orbital_line()
    elif key == "]":
        line_spacing_scale = min(1.55, line_spacing_scale + 0.08)
        rebuild_orbital_line()
    elif lower == "z":
        manual_camera = True
        scene.range = max(5, scene.range - 0.8)
    elif lower == "x":
        manual_camera = True
        scene.range = min(24, scene.range + 0.8)
    elif lower == "c":
        manual_camera = False
        scene.center = vector(INITIAL_SCENE_CENTER.x, INITIAL_SCENE_CENTER.y, INITIAL_SCENE_CENTER.z)
        scene.range = INITIAL_SCENE_RANGE
    elif key in ["left", "a"]:
        move_camera(vector(-0.65, 0, 0))
    elif key in ["right", "d"]:
        move_camera(vector(0.65, 0, 0))
    elif key in ["up", "w"]:
        move_camera(vector(0, 0.45, 0))
    elif key in ["down", "s"]:
        move_camera(vector(0, -0.45, 0))

scene.bind("keydown", handle_keydown)
controls_label = label(
    pos=vector(-4.8, 4.3, 0),
    text="controls: space pause | r reset | +/- speed | b burst | [] line spacing | g guides | wasd/arrows pan | z/x zoom | c recenter",
    height=12,
    color=vector(0.22, 0.27, 0.36),
    box=False,
    opacity=0,
)

# -----------------------------
# Animation functions
# -----------------------------
def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def set_satellite_position(sat, pos, unfold, glow_opacity, time_value):
    sat["body"].pos = pos
    sat["glow"].pos = pos

    panel_offset = 0.14 + 0.22 * unfold
    sat["left"].pos = pos + vector(0, -panel_offset, 0)
    sat["right"].pos = pos + vector(0, panel_offset, 0)
    sat["left"].size = vector(0.035, 0.23 + 0.40 * unfold, 0.13)
    sat["right"].size = vector(0.035, 0.23 + 0.40 * unfold, 0.13)
    sat["glow"].opacity = glow_opacity

    # Gentle self-stabilizing rotation, visible but not chaotic.
    angle = 0.012 * math.sin(time_value * 1.5 + sat["spin"])
    sat["body"].rotate(angle=angle, axis=vector(1, 0.2, 0), origin=pos)
    sat["left"].rotate(angle=angle, axis=vector(1, 0.2, 0), origin=pos)
    sat["right"].rotate(angle=angle, axis=vector(1, 0.2, 0), origin=pos)


def update_trail(sat, pos, visible):
    # Some VPython builds expose curve.npoints but not curve.points or curve.pop().
    # Keep our own short position history, then redraw the curve each frame.
    tr = sat["trail"]
    history = sat["trail_positions"]

    if visible:
        history.append(vector(pos.x, pos.y, pos.z))
        if len(history) > 35:
            del history[0:len(history) - 35]

        tr.clear()
        tr.opacity = 0.28
        for p in history:
            tr.append(pos=p)
    else:
        history.clear()
        tr.clear()
        tr.opacity = 0.0


def rebuild_beam(beam, start, end, opacity):
    beam.clear()
    beam.opacity = opacity
    steps = 12
    for j in range(steps + 1):
        f = j / steps
        mid = start * (1 - f) + end * f
        mid.z += math.sin(f * math.pi) * 0.28
        beam.append(pos=mid)

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
dt = 0.025
released_count = 0

while True:
    rate(60)
    if paused:
        status_label.text = "paused — 24-light deployment suspended"
        continue

    t += dt * speed_scale

    # Upper stage coast drift and subtle engine glow.
    coast = min(t / 2.0, 1.0)
    drift = vector(0.018 * math.sin(t * 0.45), 0.004 * math.sin(t * 0.8), 0)
    stage_body.pos += drift * dt
    stage_nose.pos += drift * dt
    stage_engine.pos += drift * dt
    engine_glow.pos += drift * dt
    engine_glow.radius = 0.18 + 0.05 * (1 + math.sin(t * 5.0))
    engine_glow.opacity = 0.35 + 0.20 * (1 + math.sin(t * 4.5)) * 0.5

    # Payload slowly separates from upper stage before releasing satellites.
    stack_sep = smoothstep((t - 1.0) / 2.2)
    payload_shift = vector(0.95 * stack_sep, 0.12 * math.sin(stack_sep * math.pi), 0)
    payload_core.pos = vector(-0.35, 0, 0) + payload_shift
    payload_band.pos = payload_core.pos
    for i, plate in enumerate(stack_plates):
        plate.pos = payload_core.pos + vector(0.035 * (i - 2.5), 0, 0)
    for rail in rails:
        rail.opacity = max(0.1, 1.0 - stack_sep)

    released_count = 0
    settled_count = 0

    for i, sat in enumerate(satellites):
        release_time = 2.5 + i * 0.13 * release_gap_scale
        release_progress = smoothstep((t - release_time) / 5.2)
        pre_release_offset = payload_shift + vector(0.015 * math.sin(t * 2 + i), 0, 0)

        if release_progress <= 0.0:
            pos = sat["start"] + pre_release_offset
            unfold = 0.0
            glow_opacity = 0.06 + 0.03 * math.sin(t * 2 + i)
            update_trail(sat, pos, False)
        else:
            released_count += 1
            sat["released"] = True
            start = sat["start"] + vector(0.95, 0.0, 0)
            final = controlled_final(sat)

            # The path begins with a slight fan-out, then converges into the final line.
            fan_angle = (i - (NUM_SATS - 1) / 2) * 0.065
            fan = vector(0.55 * math.cos(fan_angle), 1.1 * math.sin(fan_angle), 0.36 * math.sin(i * 0.8))
            mid = start + vector(2.2, 0, 0) + fan
            a = smoothstep(min(release_progress * 1.55, 1.0))
            b = smoothstep(max((release_progress - 0.28) / 0.72, 0.0))
            pos = start * (1 - a) + mid * a
            pos = pos * (1 - b) + final * b

            # Add tiny station-keeping motion after approaching the orbital line.
            pos += vector(0, 0.035 * math.sin(t * 1.6 + i), 0.035 * math.cos(t * 1.25 + i * 0.4)) * b
            unfold = smoothstep((release_progress - 0.10) / 0.50)
            glow_opacity = 0.25 + 0.55 * release_progress
            update_trail(sat, pos, True)
            if release_progress > 0.92:
                settled_count += 1

        set_satellite_position(sat, pos, unfold, glow_opacity, t)

    # Make the orbital guide brighten as the line fills.
    line_fill = released_count / NUM_SATS
    orbital_line.opacity = (0.12 + 0.36 * line_fill) if show_guides else 0.0
    orbital_line.color = mix(vector(0.38, 0.58, 1.0), vector(1.0, 0.86, 0.22), line_fill)
    for j, r in enumerate(orbit_rings):
        r.opacity = (0.14 + 0.10 * math.sin(t * 0.5 + j) + 0.12 * line_fill) if show_guides else 0.0
        r.rotate(angle=0.0015 * (j + 1), axis=vector(0.1, 1, 0.2), origin=earth.pos)

    # Beams become visible once several satellites settle.
    for index, beam in beams:
        sat_pos = satellites[index]["body"].pos
        if settled_count > index * 0.55:
            ground = earth.pos + vector(2.6 + 0.05 * index, 3.1 - 0.03 * index, 4.0)
            opacity = 0.12 + 0.22 * abs(math.sin(t * 1.2 + index))
            rebuild_beam(beam, sat_pos, ground, opacity)
        else:
            beam.clear()
            beam.opacity = 0.0

    # Status text.
    if t < 1.1:
        status_label.text = "upper stage coasting with compact payload stack"
    elif t < 2.6:
        status_label.text = "payload stack separating from the upper stage"
    elif released_count < NUM_SATS:
        status_label.text = "24 lights releasing one by one into low orbit"
    elif settled_count < NUM_SATS:
        status_label.text = "satellites drifting into a measured orbital line"
    else:
        status_label.text = "orbital line complete: 24 Starlink-style lights aligned"

    count_label.text = f"released: {released_count} / 24    aligned: {settled_count} / 24    speed: {speed_scale:.2f}x    burst: {release_gap_scale < 1.0}    line spacing: {line_spacing_scale:.2f}"

    # Slowly track the growing line without auto-spinning the camera.
    if t > 7 and not manual_camera:
        scene.center = mix(scene.center, vector(3.7, 0.1, 0), 0.008)
