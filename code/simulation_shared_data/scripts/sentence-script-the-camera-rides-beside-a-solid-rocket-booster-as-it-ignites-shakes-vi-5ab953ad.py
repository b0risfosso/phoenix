"""
Booster Ride to Space — VPython simulation

A cinematic VPython scene where the camera rides beside a solid rocket booster as it
ignites, shakes violently, climbs through clouds, and pushes a shuttle stack toward space.

Controls
--------
SPACE : pause / resume
C     : toggle camera mode: ride / chase / wide
V     : toggle vibration
R     : reset simulation
+/-   : increase / decrease time scale
H     : show / hide help

Run with:
    python booster_ride_to_space_vpython.py
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene = canvas(
    title="Booster Ride to Space — camera beside the solid rocket booster",
    width=1280,
    height=760,
    background=vector(0.84, 0.92, 1.0),
    center=vector(0, 60, 0),
)
scene.forward = vector(-0.35, -0.18, -1.0)
scene.up = vector(0, 1, 0)
scene.range = 70
scene.userspin = False
scene.userzoom = True
scene.autoscale = False

# -----------------------------
# Constants and state
# -----------------------------
GROUND_Y = 0.0
BOOSTER_HEIGHT = 44.0
BOOSTER_RADIUS = 2.0
TANK_HEIGHT = 50.0
TANK_RADIUS = 3.3
SHUTTLE_LENGTH = 32.0

paused = False
show_help = True
vibration_enabled = True
camera_modes = ["ride", "chase", "wide"]
camera_mode_index = 0
time_scale = 1.0

t = 0.0
altitude = 0.0
velocity = 0.0
acceleration = 0.0
max_altitude = 0.0

# -----------------------------
# Helper functions
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def smoothstep(edge0, edge1, x):
    u = clamp((x - edge0) / max(1e-9, edge1 - edge0), 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def make_cylinder_between(start, end, radius, color_value, opacity=1.0):
    return cylinder(pos=start, axis=end - start, radius=radius, color=color_value, opacity=opacity)


def set_group_visible(items, visible):
    for item in items:
        item.visible = visible

# -----------------------------
# World objects
# -----------------------------
ground = box(pos=vector(0, -0.65, 0), size=vector(420, 1.2, 420), color=vector(0.68, 0.78, 0.61))
launch_pad = cylinder(pos=vector(0, 0, 0), axis=vector(0, 1.1, 0), radius=10.5, color=vector(0.52, 0.54, 0.55))
flame_trench = box(pos=vector(0, -0.03, 0), size=vector(18, 0.18, 6), color=vector(0.26, 0.28, 0.30))

# Launch tower, made with simple cylinders and cross braces
tower_parts = []
tower_x = -18
for dx in [-2.2, 2.2]:
    for dz in [-2.2, 2.2]:
        tower_parts.append(cylinder(pos=vector(tower_x + dx, 0, dz), axis=vector(0, 65, 0), radius=0.18, color=vector(0.55, 0.50, 0.46)))
for y in range(5, 66, 8):
    tower_parts.append(make_cylinder_between(vector(tower_x - 2.2, y, -2.2), vector(tower_x + 2.2, y, -2.2), 0.12, vector(0.55, 0.50, 0.46)))
    tower_parts.append(make_cylinder_between(vector(tower_x - 2.2, y, 2.2), vector(tower_x + 2.2, y, 2.2), 0.12, vector(0.55, 0.50, 0.46)))
    tower_parts.append(make_cylinder_between(vector(tower_x - 2.2, y, -2.2), vector(tower_x - 2.2, y, 2.2), 0.12, vector(0.55, 0.50, 0.46)))
    tower_parts.append(make_cylinder_between(vector(tower_x + 2.2, y, -2.2), vector(tower_x + 2.2, y, 2.2), 0.12, vector(0.55, 0.50, 0.46)))
    tower_parts.append(make_cylinder_between(vector(tower_x - 2.2, y, -2.2), vector(tower_x + 2.2, y + 5, -2.2), 0.08, vector(0.62, 0.56, 0.50)))
service_arm = make_cylinder_between(vector(tower_x + 2.2, 42, 0), vector(-3, 42, 0), 0.22, vector(0.66, 0.58, 0.48))

# Parent position for shuttle stack components.
stack_y = 1.2
stack_x = 0.0
stack_z = 0.0

# Main external tank
tank = cylinder(pos=vector(stack_x, stack_y, stack_z), axis=vector(0, TANK_HEIGHT, 0), radius=TANK_RADIUS, color=vector(0.95, 0.47, 0.18))
tank_top = cone(pos=tank.pos + tank.axis, axis=vector(0, 5.5, 0), radius=TANK_RADIUS, color=vector(0.95, 0.52, 0.22))
tank_bottom = cone(pos=tank.pos, axis=vector(0, -3.0, 0), radius=TANK_RADIUS, color=vector(0.90, 0.42, 0.16))

# Two solid rocket boosters
booster_offsets = [vector(-5.0, 0, 0), vector(5.0, 0, 0)]
boosters = []
booster_details = []
for i, off in enumerate(booster_offsets):
    body = cylinder(pos=vector(stack_x, stack_y, stack_z) + off, axis=vector(0, BOOSTER_HEIGHT, 0), radius=BOOSTER_RADIUS, color=vector(0.96, 0.96, 0.94))
    nose = cone(pos=body.pos + body.axis, axis=vector(0, 5.0, 0), radius=BOOSTER_RADIUS, color=vector(0.90, 0.90, 0.90))
    nozzle = cone(pos=body.pos + vector(0, -2.7, 0), axis=vector(0, 2.2, 0), radius=1.2, color=vector(0.25, 0.25, 0.27))
    stripe1 = cylinder(pos=body.pos + vector(0, 8, 0), axis=vector(0, 0.7, 0), radius=BOOSTER_RADIUS * 1.015, color=vector(0.10, 0.20, 0.70))
    stripe2 = cylinder(pos=body.pos + vector(0, 29, 0), axis=vector(0, 0.7, 0), radius=BOOSTER_RADIUS * 1.015, color=vector(0.10, 0.20, 0.70))
    boosters.append({"body": body, "nose": nose, "nozzle": nozzle, "stripe1": stripe1, "stripe2": stripe2, "offset": off})
    booster_details.extend([body, nose, nozzle, stripe1, stripe2])

# Orbiter/shuttle simplified shape, attached to one side of tank
orbiter_parts = []
orbiter_offset = vector(0, 9.0, -7.1)
orbiter_body = cylinder(pos=vector(stack_x, stack_y, stack_z) + orbiter_offset, axis=vector(0, SHUTTLE_LENGTH, 0), radius=1.65, color=vector(0.93, 0.94, 0.95))
orbiter_nose = cone(pos=orbiter_body.pos + orbiter_body.axis, axis=vector(0, 4.0, 0), radius=1.65, color=vector(0.90, 0.92, 0.94))
orbiter_tail = box(pos=orbiter_body.pos + vector(0, 3.0, 0.0), size=vector(0.45, 7.0, 4.2), color=vector(0.80, 0.82, 0.84))
left_wing = pyramid(pos=orbiter_body.pos + vector(-0.1, 11.0, 0.0), size=vector(9.0, 1.2, 6.0), color=vector(0.82, 0.84, 0.86))
right_wing = pyramid(pos=orbiter_body.pos + vector(0.1, 11.0, 0.0), size=vector(9.0, 1.2, 6.0), color=vector(0.82, 0.84, 0.86))
left_wing.rotate(angle=math.radians(90), axis=vector(0, 1, 0))
right_wing.rotate(angle=math.radians(-90), axis=vector(0, 1, 0))
window = box(pos=orbiter_nose.pos + vector(0, 1.15, -1.50), size=vector(2.2, 0.55, 0.08), color=vector(0.08, 0.20, 0.35))
orbiter_parts.extend([orbiter_body, orbiter_nose, orbiter_tail, left_wing, right_wing, window])

stack_parts = [tank, tank_top, tank_bottom] + booster_details + orbiter_parts

# Attachment beams connecting boosters to the external tank
connector_parts = []
for off in booster_offsets:
    for yy in [13, 31]:
        connector_parts.append(make_cylinder_between(vector(off.x, stack_y + yy, off.z), vector(0, stack_y + yy, 0), 0.14, vector(0.70, 0.70, 0.70)))
stack_parts.extend(connector_parts)

# Exhaust and smoke particles
flames = []
for i in range(90):
    side = -1 if i < 45 else 1
    pos = vector(5.0 * side + random.uniform(-0.8, 0.8), -1.6 - random.uniform(0, 7), random.uniform(-0.9, 0.9))
    p = sphere(pos=pos, radius=random.uniform(0.4, 1.3), color=vector(1.0, random.uniform(0.45, 0.85), 0.08), opacity=0.65)
    p.v = vector(random.uniform(-0.4, 0.4), -random.uniform(14, 35), random.uniform(-0.4, 0.4))
    p.side = side
    flames.append(p)

smoke = []
for i in range(120):
    p = sphere(pos=vector(random.uniform(-16, 16), random.uniform(-1, 3), random.uniform(-12, 12)), radius=random.uniform(1.2, 3.5), color=vector(0.82, 0.82, 0.78), opacity=random.uniform(0.12, 0.30))
    p.v = vector(random.uniform(-3, 3), random.uniform(0.4, 2.0), random.uniform(-3, 3))
    smoke.append(p)

# Cloud layers the rocket passes through
clouds = []
for layer_y, spread, count, alpha in [(92, 85, 45, 0.32), (150, 110, 55, 0.25), (218, 145, 45, 0.20)]:
    for i in range(count):
        c = sphere(
            pos=vector(random.uniform(-spread, spread), layer_y + random.uniform(-8, 8), random.uniform(-spread * 0.35, spread * 0.35)),
            radius=random.uniform(6, 15),
            color=vector(1, 1, 1),
            opacity=alpha,
        )
        c.base_opacity = alpha
        clouds.append(c)

# Altitude markers
markers = []
for y, label_text in [(50, "50 m"), (100, "Cloud deck"), (150, "150 m"), (220, "Upper clouds"), (310, "Near space")]:
    markers.append(cylinder(pos=vector(-36, y, 0), axis=vector(28, 0, 0), radius=0.08, color=vector(0.48, 0.57, 0.67), opacity=0.45))
    markers.append(label(pos=vector(-52, y, 0), text=label_text, height=11, color=vector(0.25, 0.30, 0.36), box=False, opacity=0))

# Sensor HUD and labels
hud = label(
    pos=vector(0, 0, 0),
    text="",
    height=14,
    color=vector(0.08, 0.10, 0.12),
    box=True,
    background=vector(0.95, 0.97, 1.0),
    opacity=0.78,
)
help_label = label(
    pos=vector(0, 0, 0),
    text="",
    height=12,
    color=vector(0.08, 0.10, 0.12),
    box=True,
    background=vector(1.0, 0.98, 0.88),
    opacity=0.70,
)
phase_label = label(
    pos=vector(0, 63, -12),
    text="IGNITION",
    height=18,
    color=vector(0.90, 0.25, 0.08),
    box=False,
    opacity=0,
)

# Star specks that appear higher up
stars = []
for i in range(100):
    s = sphere(pos=vector(random.uniform(-180, 180), random.uniform(250, 460), random.uniform(-210, -90)), radius=random.uniform(0.25, 0.7), color=vector(1, 1, 1), opacity=0.0)
    stars.append(s)

# Trails: avoid curve.points access for compatibility
left_trail = curve(color=vector(0.98, 0.64, 0.12), radius=0.10, retain=240)
right_trail = curve(color=vector(0.98, 0.64, 0.12), radius=0.10, retain=240)

# Store original offsets for all stack parts relative to stack origin
base_origin = vector(stack_x, stack_y, stack_z)
part_offsets = {obj: obj.pos - base_origin for obj in stack_parts}

# For cone/cylinder axes that need to stay fixed under position update
axis_map = {obj: vector(obj.axis) for obj in stack_parts if hasattr(obj, "axis")}

# -----------------------------
# Keyboard controls
# -----------------------------
def reset_simulation():
    global t, altitude, velocity, acceleration, max_altitude, paused, time_scale
    t = 0.0
    altitude = 0.0
    velocity = 0.0
    acceleration = 0.0
    max_altitude = 0.0
    paused = False
    time_scale = 1.0
    left_trail.clear()
    right_trail.clear()
    for s in stars:
        s.opacity = 0.0
    for c in clouds:
        c.opacity = c.base_opacity


def on_keydown(evt):
    global paused, show_help, vibration_enabled, camera_mode_index, time_scale
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "c":
        camera_mode_index = (camera_mode_index + 1) % len(camera_modes)
    elif key == "v":
        vibration_enabled = not vibration_enabled
    elif key == "r":
        reset_simulation()
    elif key in ["+", "="]:
        time_scale = clamp(time_scale + 0.25, 0.25, 4.0)
    elif key in ["-", "_"]:
        time_scale = clamp(time_scale - 0.25, 0.25, 4.0)
    elif key == "h":
        show_help = not show_help

scene.bind("keydown", on_keydown)

# -----------------------------
# Main update functions
# -----------------------------
def current_phase(local_t, alt):
    if local_t < 3.0:
        return "IGNITION HOLD-DOWN: booster flame builds"
    if alt < 75:
        return "LIFTOFF: violent shake and tower clear"
    if alt < 170:
        return "CLOUD PUNCH: stack climbs through vapor"
    if alt < 285:
        return "MAX-Q FEEL: vibration eases as air thins"
    return "EDGE OF SPACE: sky darkens and stars appear"


def sky_color_for_altitude(alt):
    u = clamp(alt / 330.0, 0.0, 1.0)
    return vector(0.84 - 0.70 * u, 0.92 - 0.80 * u, 1.0 - 0.86 * u)


def update_stack_position(dt):
    global altitude, velocity, acceleration, max_altitude

    # Thrust ramp, liftoff hold-down, then upward climb.
    ignition_ramp = smoothstep(0.2, 3.0, t)
    hold_down = 0.0 if t < 3.0 else 1.0
    air_thin = smoothstep(80, 260, altitude)
    throttle = 0.86 + 0.14 * math.sin(t * 0.55)
    acceleration = hold_down * (7.5 + 10.0 * ignition_ramp + 5.0 * air_thin) * throttle

    velocity += acceleration * dt
    velocity = clamp(velocity, 0.0, 92.0)
    altitude += velocity * dt
    max_altitude = max(max_altitude, altitude)

    # Shake is strongest around ignition and early ascent.
    shake_strength = 0.0
    if vibration_enabled:
        shake_strength = (1.7 * ignition_ramp * (1.0 - smoothstep(165, 310, altitude)))
        if t < 3.0:
            shake_strength *= 0.55
    shake = vector(
        math.sin(t * 42.0) * shake_strength + random.uniform(-0.15, 0.15) * shake_strength,
        math.sin(t * 35.0) * 0.16 * shake_strength,
        math.cos(t * 38.0) * shake_strength + random.uniform(-0.15, 0.15) * shake_strength,
    )

    origin = base_origin + vector(0, altitude, 0) + shake

    for obj, offset in part_offsets.items():
        obj.pos = origin + offset
        if obj in axis_map:
            obj.axis = axis_map[obj]

    # Connector endpoints must be recalculated, since these cylinders span between moving objects.
    # Rebuild their geometric positions without creating new objects.
    idx = 0
    for off in booster_offsets:
        for yy in [13, 31]:
            conn = connector_parts[idx]
            start = origin + vector(off.x, yy, off.z)
            end = origin + vector(0, yy, 0)
            conn.pos = start
            conn.axis = end - start
            idx += 1

    # Trails behind boosters.
    left_trail.append(pos=origin + vector(-5.0, -2.4, 0))
    right_trail.append(pos=origin + vector(5.0, -2.4, 0))

    return origin, shake_strength


def update_plume(dt, origin, shake_strength):
    flame_power = smoothstep(0.3, 3.2, t)
    if altitude > 285:
        flame_power *= 0.75

    for p in flames:
        root = origin + vector(5.0 * p.side, -2.5, 0)
        p.pos += (p.v * (0.05 + flame_power * 0.08) + vector(random.uniform(-0.25, 0.25), 0, random.uniform(-0.25, 0.25))) * dt * 18
        p.radius *= 1.0 + 0.006 * flame_power
        p.opacity = 0.15 + 0.55 * flame_power
        p.color = vector(1.0, random.uniform(0.38, 0.85), random.uniform(0.02, 0.15))
        if p.pos.y < origin.y - 40 or random.random() < 0.018:
            p.pos = root + vector(random.uniform(-0.65, 0.65), random.uniform(-3.0, -0.5), random.uniform(-0.65, 0.65))
            p.radius = random.uniform(0.35, 1.25) * (1.0 + 0.25 * flame_power)
            p.v = vector(random.uniform(-0.5, 0.5), -random.uniform(16, 40), random.uniform(-0.5, 0.5))

    # Smoke starts dense near ground; later it trails far below.
    smoke_fade = 1.0 - smoothstep(90, 230, altitude)
    for p in smoke:
        p.pos += p.v * dt * (1.0 + 0.4 * flame_power)
        p.radius *= 1.0 + 0.0015
        p.opacity = clamp(p.opacity * 0.998, 0.04, 0.34) * (0.45 + 0.55 * smoke_fade)
        if p.pos.y > altitude + 10 or mag(p.pos - vector(0, altitude, 0)) > 130 or random.random() < 0.004:
            p.pos = vector(random.uniform(-18, 18), max(-0.3, altitude - random.uniform(25, 55)), random.uniform(-14, 14))
            p.radius = random.uniform(1.4, 4.2)
            p.opacity = random.uniform(0.08, 0.28) * (0.4 + 0.6 * smoke_fade)
            p.v = vector(random.uniform(-3.5, 3.5), random.uniform(0.3, 2.4), random.uniform(-3.5, 3.5))


def update_clouds_and_sky():
    scene.background = sky_color_for_altitude(altitude)
    for c in clouds:
        # Clouds become translucent after the camera/stack passes them.
        passed = smoothstep(c.pos.y - 8, c.pos.y + 22, altitude)
        near = 1.0 - smoothstep(0, 60, abs(c.pos.y - altitude))
        c.opacity = clamp(c.base_opacity * (1.0 - 0.75 * passed + 0.45 * near), 0.03, 0.45)
        c.pos.x += math.sin(t * 0.2 + c.pos.y * 0.03) * 0.006

    star_alpha = smoothstep(230, 340, altitude)
    for s in stars:
        s.opacity = 0.05 + 0.85 * star_alpha


def update_camera(origin, shake_strength):
    mode = camera_modes[camera_mode_index]
    extra_shake = vector(0, 0, 0)
    if vibration_enabled:
        extra_shake = vector(
            math.sin(t * 55) * 0.4 * shake_strength,
            math.cos(t * 47) * 0.25 * shake_strength,
            math.sin(t * 61) * 0.35 * shake_strength,
        )

    if mode == "ride":
        # Beside the left booster: close, vibrating, cinematic.
        scene.camera.pos = origin + vector(-13, 18, -20) + extra_shake
        scene.camera.axis = (origin + vector(-3.5, 20, 0)) - scene.camera.pos
        scene.range = 42
    elif mode == "chase":
        scene.camera.pos = origin + vector(0, -28, -85) + extra_shake * 0.35
        scene.camera.axis = (origin + vector(0, 26, 0)) - scene.camera.pos
        scene.range = 82
    else:
        scene.camera.pos = vector(85, altitude + 70, -160)
        scene.camera.axis = (origin + vector(0, 25, 0)) - scene.camera.pos
        scene.range = 145


def update_hud(origin, shake_strength):
    phase = current_phase(t, altitude)
    phase_label.pos = origin + vector(0, 62, -12)
    phase_label.text = phase
    phase_label.color = vector(0.90, 0.25 + 0.30 * smoothstep(80, 250, altitude), 0.08)

    hud.pos = scene.camera.pos + norm(scene.camera.axis) * 28 + vector(0, 9, 0)
    hud.text = (
        f"Booster Ride to Space\n"
        f"Phase: {phase}\n"
        f"Altitude: {altitude:6.1f} m    Velocity: {velocity:5.1f} m/s\n"
        f"Shake: {shake_strength:4.2f}    Camera: {camera_modes[camera_mode_index]}    Time scale: {time_scale:.2f}x"
    )

    help_label.visible = show_help
    if show_help:
        help_label.pos = scene.camera.pos + norm(scene.camera.axis) * 28 + vector(0, -11, 0)
        help_label.text = "SPACE pause/resume   C camera   V vibration   +/- speed   R reset   H hide help"

# -----------------------------
# Main simulation loop
# -----------------------------
while True:
    rate(60)
    dt = (1.0 / 60.0) * time_scale
    if paused:
        update_hud(base_origin + vector(0, altitude, 0), 0.0)
        continue

    t += dt

    if altitude > 385:
        # Loop into another ride rather than ending abruptly.
        reset_simulation()
        continue

    stack_origin, shake_value = update_stack_position(dt)
    update_plume(dt, stack_origin, shake_value)
    update_clouds_and_sky()
    update_camera(stack_origin, shake_value)
    update_hud(stack_origin, shake_value)
