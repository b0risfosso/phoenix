"""
Gravity Well Dynamo
Massive orbiting bodies fall forever around a controlled singularity,
converting endless motion into radiant power streams.

Controls:
  Space  : pause / resume
  R      : reset simulation
  Up     : increase collector load
  Down   : decrease collector load
  Left   : weaken singularity control field
  Right  : strengthen singularity control field

Requirements:
  pip install vpython

Styling:
  Light background and high-contrast objects for bright display.

Evolution added:
  Some fast, close-orbiting bodies develop unstable glowing tails as motion
  converts into stronger radiant power streams.

Run:
  python gravity_well_dynamo_unstable_tails.py
"""

from vpython import (
    canvas, vector, sphere, ring, cylinder, curve, color, rate,
    mag, norm, cross, dot, sin, cos, pi, random, label, box, distant_light
)
import math

# -----------------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------------
scene = canvas(
    title="Gravity Well Dynamo — endless falling motion converted into radiant power streams",
    width=1200,
    height=760,
    background=vector(0.94, 0.96, 1.00),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.45, -0.28, -1.0)
scene.range = 26
scene.autoscale = False
scene.userzoom = True
scene.userspin = True

distant_light(direction=vector(-1, -1, -2), color=vector(0.88, 0.90, 0.98))
distant_light(direction=vector(1, 0.5, 0.2), color=vector(0.70, 0.76, 0.92))

# -----------------------------------------------------------------------------
# Constants / simulation state
# -----------------------------------------------------------------------------
G = 22.0
CENTER_MASS = 45.0
DT = 0.010
SOFTENING = 1.05
BODY_COUNT = 13
TRAIL_POINTS = 90
TAIL_POINTS = 34
MAX_STREAMS = 48

paused = False
collector_load = 1.0
control_field = 1.0
stored_energy = 0.0
total_power = 0.0
phase = 0.0
sim_time = 0.0

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def orbital_velocity(radius):
    return math.sqrt(G * CENTER_MASS / max(radius, 0.1))


def tangential_direction(pos, tilt):
    radial = norm(pos)
    axis = norm(vector(math.sin(tilt), 1.0, math.cos(tilt) * 0.4))
    tangent = cross(axis, radial)
    if mag(tangent) < 0.001:
        tangent = cross(vector(0, 1, 0), radial)
    return norm(tangent)


def thermal_color(amount):
    amount = clamp(amount, 0.0, 1.0)
    return vector(0.18 + 0.82 * amount, 0.38 + 0.45 * amount, 0.92 - 0.62 * amount)


def format_power(v):
    if v >= 1000:
        return f"{v/1000:.2f} TW"
    return f"{v:.1f} GW"

# -----------------------------------------------------------------------------
# Central controlled singularity and containment machinery
# -----------------------------------------------------------------------------
singularity = sphere(
    pos=vector(0, 0, 0),
    radius=1.05,
    color=vector(0.22, 0.25, 0.34),
    emissive=True,
    shininess=0.0,
)
inner_glow = sphere(
    pos=vector(0, 0, 0),
    radius=1.32,
    color=vector(0.20, 0.46, 1.0),
    opacity=0.18,
    emissive=True,
)
outer_halo = sphere(
    pos=vector(0, 0, 0),
    radius=2.35,
    color=vector(0.35, 0.70, 1.0),
    opacity=0.07,
    emissive=True,
)

containment_rings = []
for i, (rad, axis, col) in enumerate([
    (4.2, vector(0, 1, 0), vector(0.18, 0.55, 1.0)),
    (4.7, vector(1, 0, 0), vector(0.45, 0.28, 1.0)),
    (5.2, vector(0, 0, 1), vector(0.10, 0.82, 0.95)),
]):
    containment_rings.append(
        ring(
            pos=vector(0, 0, 0),
            axis=axis,
            radius=rad,
            thickness=0.045 + i * 0.015,
            color=col,
            emissive=True,
            opacity=0.52,
        )
    )

collector_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=10.8,
    thickness=0.12,
    color=vector(1.0, 0.78, 0.25),
    emissive=True,
    opacity=0.75,
)
outer_grid = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=16.6,
    thickness=0.055,
    color=vector(0.20, 0.55, 0.95),
    emissive=True,
    opacity=0.35,
)

# Power output towers
power_towers = []
for k in range(8):
    ang = 2 * pi * k / 8
    base = vector(18 * cos(ang), -2.2, 18 * sin(ang))
    tower = cylinder(
        pos=base,
        axis=vector(0, 4.4, 0),
        radius=0.13,
        color=vector(0.20, 0.55, 0.95),
        emissive=True,
        opacity=0.62,
    )
    cap = sphere(
        pos=base + vector(0, 4.55, 0),
        radius=0.42,
        color=vector(1.0, 0.82, 0.32),
        emissive=True,
    )
    power_towers.append((tower, cap, ang))

# -----------------------------------------------------------------------------
# Orbiting massive bodies
# -----------------------------------------------------------------------------
bodies = []
for i in range(BODY_COUNT):
    radius = 6.6 + i * 0.72 + random() * 0.6
    ang = 2 * pi * i / BODY_COUNT
    height = (random() - 0.5) * 2.7
    tilt = i * 0.37
    pos = vector(radius * cos(ang), height, radius * sin(ang))
    tangent = tangential_direction(pos, tilt)
    speed = orbital_velocity(radius) * (0.87 + 0.17 * random())
    mass = 1.2 + random() * 2.5
    body_radius = 0.33 + mass * 0.075
    body = sphere(
        pos=pos,
        radius=body_radius,
        color=vector(0.42 + 0.20 * random(), 0.48 + 0.16 * random(), 0.70 + 0.16 * random()),
        emissive=True,
        make_trail=False,
    )
    body.mass = mass
    body.vel = tangent * speed
    body.heat = random() * 0.35
    body.phase = random() * 2 * pi
    body.safe_radius = 5.7 + random() * 1.1
    trail = curve(color=body.color, radius=0.022, opacity=0.28)
    unstable_tail = curve(color=vector(1.0, 0.72, 0.18), radius=0.055, opacity=0.0, emissive=True)
    bodies.append({
        "body": body,
        "trail": trail,
        "trail_positions": [],
        "unstable_tail": unstable_tail,
        "tail_positions": [],
        "tail_flicker": random() * 2 * pi,
        "tail_strength": 0.0,
    })

# Radiant power streams, reused instead of constantly creating objects
streams = []
for _ in range(MAX_STREAMS):
    c = cylinder(
        pos=vector(0, 0, 0),
        axis=vector(0, 0.001, 0),
        radius=0.035,
        color=vector(1.0, 0.78, 0.25),
        emissive=True,
        opacity=0.0,
    )
    c.life = 0.0
    c.max_life = 1.0
    streams.append(c)
stream_index = 0

# Arc flashes around the collector ring
arc_segments = []
for k in range(20):
    a0 = 2 * pi * k / 20
    pts = []
    for j in range(7):
        a = a0 + j * 0.045
        pts.append(vector(10.8 * cos(a), 0.25 * sin(j), 10.8 * sin(a)))
    arc_segments.append(curve(pos=pts, radius=0.025, color=vector(1.0, 0.86, 0.3), emissive=True, opacity=0.08))

info = label(
    pos=vector(-22, 12.5, 0),
    text="",
    height=13,
    color=vector(0.08, 0.10, 0.16),
    box=False,
    opacity=0,
    align="left",
)

meter_back = box(pos=vector(-15.0, -11.0, 0), size=vector(10.0, 0.32, 0.2), color=vector(0.76, 0.81, 0.90), opacity=0.72)
meter_fill = box(pos=vector(-19.95, -11.0, 0), size=vector(0.1, 0.34, 0.24), color=vector(1.0, 0.78, 0.25), emissive=True)

# -----------------------------------------------------------------------------
# Interaction
# -----------------------------------------------------------------------------
def reset_simulation():
    global stored_energy, total_power, sim_time, phase, collector_load, control_field
    stored_energy = 0.0
    total_power = 0.0
    sim_time = 0.0
    phase = 0.0
    collector_load = 1.0
    control_field = 1.0
    for i, entry in enumerate(bodies):
        body = entry["body"]
        radius = 6.6 + i * 0.72 + random() * 0.6
        ang = 2 * pi * i / BODY_COUNT
        pos = vector(radius * cos(ang), (random() - 0.5) * 2.7, radius * sin(ang))
        body.pos = pos
        body.vel = tangential_direction(pos, i * 0.37) * orbital_velocity(radius) * (0.90 + 0.12 * random())
        body.heat = random() * 0.35
        entry["trail_positions"] = []
        entry["tail_positions"] = []
        entry["tail_strength"] = 0.0
        entry["trail"].clear()
        entry["unstable_tail"].clear()
        entry["unstable_tail"].opacity = 0.0


def keydown(evt):
    global paused, collector_load, control_field
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ("r", "R"):
        reset_simulation()
    elif key == "up":
        collector_load = clamp(collector_load + 0.12, 0.35, 2.2)
    elif key == "down":
        collector_load = clamp(collector_load - 0.12, 0.35, 2.2)
    elif key == "right":
        control_field = clamp(control_field + 0.08, 0.45, 1.75)
    elif key == "left":
        control_field = clamp(control_field - 0.08, 0.45, 1.75)

scene.bind("keydown", keydown)

# -----------------------------------------------------------------------------
# Main dynamics
# -----------------------------------------------------------------------------
def emit_stream(start, end, intensity):
    global stream_index
    c = streams[stream_index]
    stream_index = (stream_index + 1) % len(streams)
    c.pos = start
    c.axis = end - start
    c.radius = 0.025 + 0.08 * clamp(intensity, 0.0, 1.0)
    c.color = vector(1.0, 0.65 + 0.25 * clamp(intensity, 0.0, 1.0), 0.18)
    c.opacity = 0.85
    c.life = 0.22 + 0.35 * clamp(intensity, 0.0, 1.0)
    c.max_life = c.life


def nearest_tower(pos):
    best = None
    best_d = 1e9
    for tower, cap, ang in power_towers:
        d = mag(cap.pos - pos)
        if d < best_d:
            best = cap.pos
            best_d = d
    return best

while True:
    rate(90)


    if paused:
        info.text = (
            "GRAVITY WELL DYNAMO  [PAUSED]\n"
            "Space resume | R reset | arrows tune field/load"
        )
        continue

    phase += DT
    sim_time += DT
    total_power = 0.0
    mean_radius = 0.0
    mean_speed = 0.0
    active_streams = 0
    unstable_tail_count = 0

    # Containment pulse and rotating field rings
    containment_pulse = 0.5 + 0.5 * sin(phase * 3.0)
    singularity.radius = 0.92 + 0.12 * sin(phase * 8.0)
    inner_glow.radius = 1.26 + 0.20 * containment_pulse
    inner_glow.opacity = 0.20 + 0.18 * containment_pulse
    outer_halo.radius = 2.25 + 0.55 * sin(phase * 1.7) ** 2
    outer_halo.opacity = 0.07 + 0.07 * control_field

    for idx, r in enumerate(containment_rings):
        r.rotate(angle=(0.010 + idx * 0.004) * control_field, axis=norm(r.axis + vector(0.01, 0.02, 0.015)), origin=vector(0, 0, 0))
        r.opacity = 0.34 + 0.28 * (0.5 + 0.5 * sin(phase * (2.2 + idx) + idx))
        r.thickness = 0.04 + 0.035 * control_field * (0.4 + 0.6 * containment_pulse)

    collector_ring.rotate(angle=0.006 * collector_load, axis=vector(0, 1, 0), origin=vector(0, 0, 0))
    outer_grid.rotate(angle=-0.0025 * collector_load, axis=vector(0, 1, 0), origin=vector(0, 0, 0))

    for i, entry in enumerate(bodies):
        body = entry["body"]
        pos = body.pos
        r = mag(pos)
        radial = norm(pos) if r > 0.001 else vector(1, 0, 0)

        # Gravity with softening: perpetual falling toward the controlled singularity.
        gravity_acc = -radial * (G * CENTER_MASS / (r * r + SOFTENING * SOFTENING))

        # Control field prevents impact and converts unstable plunge into orbital shear.
        safe = body.safe_radius / control_field
        if r < safe:
            repulse_strength = (safe - r) * 18.0 * control_field
            gravity_acc += radial * repulse_strength
            body.vel += tangential_direction(pos, body.phase) * (0.07 * repulse_strength * DT)

        # Dynamo collector load drains a tiny amount of orbital kinetic energy into power.
        tangent = tangential_direction(pos, body.phase)
        radial_speed = dot(body.vel, radial)
        shear = mag(body.vel - radial * radial_speed)
        harvest = collector_load * body.mass * shear * shear / max(r, 1.0) * 0.016
        total_power += harvest
        stored_energy += harvest * DT
        body.heat = clamp(body.heat * 0.992 + harvest * 0.010, 0.0, 1.0)

        # Motion-to-radiance conversion: fast close passes destabilize glowing tails.
        speed_norm = clamp(shear / 13.0, 0.0, 1.0)
        close_norm = clamp((12.5 - r) / 7.5, 0.0, 1.0)
        conversion_intensity = clamp(0.18 * body.heat + 0.58 * speed_norm + 0.34 * close_norm, 0.0, 1.0)
        tail_threshold = 0.53 + 0.10 * sin(body.phase + phase * 0.7)
        tail_target = clamp((conversion_intensity - tail_threshold) / 0.42, 0.0, 1.0)
        entry["tail_strength"] = clamp(entry["tail_strength"] * 0.90 + tail_target * 0.16, 0.0, 1.0)

        # Very small thrust-like correction keeps bodies falling forever instead of decaying.
        desired_speed = orbital_velocity(max(r, 3.0)) * (0.88 + 0.12 * sin(phase * 0.5 + body.phase))
        speed_error = desired_speed - shear
        gravity_acc += tangent * speed_error * 0.38 * control_field

        # Slight 3D orbital precession so the well looks alive rather than planar.
        precession = vector(0, sin(phase * 0.4 + body.phase), 0) * 0.18
        body.vel += (gravity_acc + precession) * DT
        body.pos += body.vel * DT

        # If a body is thrown too far, bend it back into the dynamo field.
        if mag(body.pos) > 22:
            body.vel += -norm(body.pos) * 3.0 * DT

        # Visual heat/color from power extraction.
        body.color = thermal_color(body.heat)
        body.radius = (0.33 + body.mass * 0.075) * (1.0 + 0.08 * body.heat * sin(phase * 12 + i))

        # Trail management.
        trail_positions = entry["trail_positions"]
        trail_positions.append(vector(body.pos.x, body.pos.y, body.pos.z))
        if len(trail_positions) > TRAIL_POINTS:
            trail_positions.pop(0)
        entry["trail"].clear()
        if len(trail_positions) > 1:
            entry["trail"].append(trail_positions)
            entry["trail"].color = body.color
            entry["trail"].opacity = 0.10 + 0.20 * body.heat

        # Unstable glowing tail: only some bodies sustain it, and it flickers with orbital shear.
        tail = entry["unstable_tail"]
        tail_strength = entry["tail_strength"]
        if tail_strength > 0.025:
            unstable_tail_count += 1
            back_dir = -norm(body.vel) if mag(body.vel) > 0.001 else -tangent
            side_dir = norm(cross(back_dir, radial)) if mag(cross(back_dir, radial)) > 0.001 else vector(0, 1, 0)
            flicker = sin(phase * (17.0 + i * 0.37) + entry["tail_flicker"])
            wake_length = (0.55 + 2.8 * tail_strength) * (0.75 + 0.25 * abs(flicker))
            wake = body.pos + back_dir * wake_length + side_dir * (0.16 * flicker * tail_strength)
            entry["tail_positions"].append(wake)
            if len(entry["tail_positions"]) > TAIL_POINTS:
                entry["tail_positions"].pop(0)
            tail.clear()
            tail.append(entry["tail_positions"])
            tail.radius = 0.035 + 0.105 * tail_strength * (0.55 + 0.45 * abs(flicker))
            tail.opacity = 0.18 + 0.66 * tail_strength
            tail.color = vector(1.0, 0.50 + 0.36 * tail_strength, 0.12 + 0.28 * body.heat)
        else:
            entry["tail_positions"] = []
            tail.clear()
            tail.opacity = 0.0

        # Emit power streams from hot / close bodies to the collector and grid towers.
        stream_intensity = clamp(body.heat * 0.52 + entry["tail_strength"] * 0.72 + close_norm * 0.25, 0.0, 1.0)
        if stream_intensity > 0.20 and (i + int(phase * (18 + 10 * entry["tail_strength"]))) % 5 == 0:
            collector_point = norm(vector(body.pos.x, 0, body.pos.z)) * collector_ring.radius
            collector_point.y = body.pos.y * 0.15
            emit_stream(body.pos, collector_point, stream_intensity)
        if stream_intensity > 0.45 and (i + int(phase * 12)) % 8 == 0:
            emit_stream(body.pos, nearest_tower(body.pos), stream_intensity)

        mean_radius += mag(body.pos)
        mean_speed += mag(body.vel)

    mean_radius /= BODY_COUNT
    mean_speed /= BODY_COUNT

    # Fade and throb active streams.
    for c in streams:
        if c.life > 0:
            c.life -= DT
            frac = clamp(c.life / max(c.max_life, 0.001), 0.0, 1.0)
            c.opacity = 0.85 * frac
            c.radius *= 0.996
            active_streams += 1
        else:
            c.opacity = 0.0

    # Collector arcs activate around the ring according to current power draw.
    power_norm = clamp(total_power / 38.0, 0.0, 1.0)
    for k, arc in enumerate(arc_segments):
        arc.opacity = 0.03 + power_norm * (0.10 + 0.36 * (0.5 + 0.5 * sin(phase * 6 + k)))
        arc.radius = 0.015 + 0.035 * power_norm

    # Towers brighten and stretch output based on energy flow.
    for tower, cap, ang in power_towers:
        pulse = 0.5 + 0.5 * sin(phase * 4.0 + ang * 2)
        tower.radius = 0.12 + 0.12 * power_norm * pulse
        tower.opacity = 0.40 + 0.45 * power_norm
        cap.radius = 0.34 + 0.28 * power_norm * pulse
        cap.color = vector(1.0, 0.72 + 0.25 * pulse, 0.22 + 0.25 * power_norm)

    # Meter.
    meter_value = clamp(stored_energy / 220.0, 0.0, 1.0)
    meter_fill.size = vector(10.0 * meter_value, 0.34, 0.24)
    meter_fill.pos = vector(-20 + 5.0 * meter_value, -11.0, 0)
    meter_fill.color = vector(1.0, 0.55 + 0.35 * power_norm, 0.18)

    info.text = (
        "GRAVITY WELL DYNAMO\n"
        f"radiant output: {format_power(total_power * 24.0)}\n"
        f"stored energy: {stored_energy:7.1f} plasma-units\n"
        f"control field: {control_field:4.2f}    collector load: {collector_load:4.2f}\n"
        f"mean orbit radius: {mean_radius:4.1f}    mean speed: {mean_speed:4.1f}\n"
        f"unstable glowing tails: {unstable_tail_count}/{BODY_COUNT}\n"
        "Space pause | R reset | ←/→ field | ↑/↓ load"
    )
