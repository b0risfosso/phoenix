"""
Gravity Well Dynamo
Massive orbiting bodies fall forever around a controlled singularity,
converting endless motion into radiant power streams.

Evolution: rotating power collectors align around the well, catching only
the brightest streams while weaker streams leak back into orbit.

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

Run:
  python gravity_well_dynamo_light.py
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
MAX_STREAMS = 52
COLLECTOR_COUNT = 12
BRIGHT_STREAM_THRESHOLD = 0.54

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

# Rotating collector vanes: these actively align with bright streams.
# A vane that faces an incoming stream captures it; weak or misaligned streams leak away.
collector_vanes = []
for k in range(COLLECTOR_COUNT):
    ang = 2 * pi * k / COLLECTOR_COUNT
    radial = vector(cos(ang), 0, sin(ang))
    pos = radial * collector_ring.radius
    vane = box(
        pos=pos,
        size=vector(1.45, 0.18, 0.72),
        axis=radial,
        color=vector(1.0, 0.76, 0.28),
        opacity=0.72,
        emissive=True,
    )
    aperture = ring(
        pos=pos + radial * 0.22,
        axis=radial,
        radius=0.48,
        thickness=0.035,
        color=vector(1.0, 0.92, 0.44),
        opacity=0.64,
        emissive=True,
    )
    collector_vanes.append({
        "vane": vane,
        "aperture": aperture,
        "angle": ang,
        "spin": 0.0,
        "brightness": 0.0,
        "capture": 0.0,
    })

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
    bodies.append({"body": body, "trail": trail, "trail_positions": []})

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
    c.kind = "captured"
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
        entry["trail"].clear()


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
def emit_stream(start, end, intensity, kind="captured"):
    global stream_index
    c = streams[stream_index]
    stream_index = (stream_index + 1) % len(streams)
    c.pos = start
    c.axis = end - start
    intensity = clamp(intensity, 0.0, 1.0)
    c.radius = 0.022 + 0.085 * intensity
    if kind == "captured":
        c.color = vector(1.0, 0.66 + 0.28 * intensity, 0.16)
        c.opacity = 0.90
        c.life = 0.22 + 0.36 * intensity
    else:
        c.color = vector(0.25, 0.58 + 0.20 * intensity, 1.0)
        c.opacity = 0.52
        c.life = 0.34 + 0.30 * intensity
    c.max_life = c.life
    c.kind = kind


def stream_brightness(body, shear, radius):
    close_pass_boost = clamp((13.5 - radius) / 8.0, 0.0, 1.0)
    heat_boost = body.heat
    speed_boost = clamp(shear / 13.0, 0.0, 1.0)
    return clamp(0.18 + 0.45 * heat_boost + 0.25 * speed_boost + 0.28 * close_pass_boost, 0.0, 1.0)


def collector_for_position(pos):
    # Match a body/stream to the closest collector vane by azimuth.
    angle = math.atan2(pos.z, pos.x)
    if angle < 0:
        angle += 2 * pi
    idx = int((angle / (2 * pi)) * COLLECTOR_COUNT + 0.5) % COLLECTOR_COUNT
    return collector_vanes[idx]


def collector_alignment(vane_entry, source_pos):
    # Collectors rotate toward the stream direction. Alignment rises as the vane aperture faces the incoming stream.
    radial = norm(vector(vane_entry["vane"].pos.x, 0, vane_entry["vane"].pos.z))
    incoming = norm(source_pos - vane_entry["vane"].pos)
    return clamp(dot(radial, incoming), 0.0, 1.0)


def leak_target(pos, intensity, phase_offset):
    # Weak streams are bent back into outer orbit instead of entering the collector grid.
    radial = norm(vector(pos.x, 0, pos.z))
    tangent = norm(cross(vector(0, 1, 0), radial))
    if mag(tangent) < 0.001:
        tangent = vector(1, 0, 0)
    return radial * (12.8 + 2.2 * intensity) + tangent * (2.4 + 1.8 * sin(phase + phase_offset)) + vector(0, pos.y * 0.25, 0)


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
    captured_streams = 0
    leaked_streams = 0

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

    # Collectors rotate into alternating alignment windows. Only bright streams arriving during
    # these windows are captured; weaker streams are visibly bent back into orbit.
    for k, vane_entry in enumerate(collector_vanes):
        vane = vane_entry["vane"]
        aperture = vane_entry["aperture"]
        orbit_angle = vane_entry["angle"] + phase * 0.19 * collector_load
        radial = vector(cos(orbit_angle), 0, sin(orbit_angle))
        tangent = vector(-sin(orbit_angle), 0, cos(orbit_angle))
        pos = radial * collector_ring.radius
        vane.pos = pos
        aperture.pos = pos + radial * 0.24

        alignment_wave = 0.5 + 0.5 * sin(phase * 1.85 + k * 0.72)
        vane_entry["spin"] += (0.025 + 0.035 * alignment_wave) * collector_load
        vane.axis = norm(radial * (0.45 + alignment_wave) + tangent * (0.85 - 0.55 * alignment_wave))
        aperture.axis = vane.axis
        vane_entry["brightness"] *= 0.92
        vane_entry["capture"] *= 0.90

        glow = clamp(vane_entry["brightness"], 0.0, 1.0)
        capture_glow = clamp(vane_entry["capture"], 0.0, 1.0)
        vane.color = vector(1.0, 0.68 + 0.25 * capture_glow, 0.22 + 0.42 * glow)
        vane.opacity = 0.44 + 0.42 * alignment_wave + 0.14 * capture_glow
        vane.size = vector(1.25 + 0.55 * alignment_wave, 0.16 + 0.10 * capture_glow, 0.58 + 0.30 * capture_glow)
        aperture.color = vector(1.0, 0.84 + 0.14 * capture_glow, 0.32 + 0.36 * glow)
        aperture.opacity = 0.34 + 0.42 * alignment_wave + 0.20 * capture_glow
        aperture.radius = 0.40 + 0.22 * alignment_wave + 0.16 * capture_glow

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

        # Emit streams toward collector vanes. Bright aligned streams are caught; weaker
        # streams leak back into orbit as blue arcs and do not fully contribute to output.
        brightness = stream_brightness(body, shear, r)
        if body.heat > 0.16 and (i + int(phase * 18)) % 4 == 0:
            vane_entry = collector_for_position(body.pos)
            vane_pos = vane_entry["aperture"].pos
            alignment = collector_alignment(vane_entry, body.pos)
            can_capture = brightness >= BRIGHT_STREAM_THRESHOLD and alignment > 0.48
            vane_entry["brightness"] = max(vane_entry["brightness"], brightness)
            if can_capture:
                vane_entry["capture"] = 1.0
                emit_stream(body.pos, vane_pos, brightness, "captured")
                if brightness > 0.70 and (i + int(phase * 10)) % 5 == 0:
                    emit_stream(vane_pos, nearest_tower(vane_pos), brightness, "captured")
            else:
                # Return leaked energy to the orbital path as a weaker recirculating stream.
                emit_stream(body.pos, leak_target(body.pos, brightness, body.phase), brightness, "leaked")
                body.vel += tangential_direction(body.pos, body.phase) * 0.018 * (1.0 - brightness)
                stored_energy -= min(stored_energy, 0.015 * (1.0 - brightness))

        mean_radius += mag(body.pos)
        mean_speed += mag(body.vel)

    mean_radius /= BODY_COUNT
    mean_speed /= BODY_COUNT

    # Fade and throb active streams. Captured streams remain warm gold; leaked streams
    # fade cooler and curve back visually into the orbital field.
    for c in streams:
        if c.life > 0:
            c.life -= DT
            frac = clamp(c.life / max(c.max_life, 0.001), 0.0, 1.0)
            if c.kind == "captured":
                c.opacity = 0.88 * frac
                captured_streams += 1
            else:
                c.opacity = 0.48 * frac
                leaked_streams += 1
            c.radius *= 0.996
            active_streams += 1
        else:
            c.opacity = 0.0

    # Collector arcs activate around the ring according to current power draw.
    power_norm = clamp(total_power / 38.0, 0.0, 1.0)
    capture_ratio = captured_streams / max(active_streams, 1)
    for k, arc in enumerate(arc_segments):
        arc.opacity = 0.03 + power_norm * (0.08 + 0.28 * capture_ratio + 0.20 * (0.5 + 0.5 * sin(phase * 6 + k)))
        arc.radius = 0.015 + 0.035 * power_norm * (0.55 + 0.45 * capture_ratio)

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
        f"captured streams: {captured_streams:2d}    leaked streams: {leaked_streams:2d}    capture ratio: {capture_ratio:4.2f}\n"
        "Space pause | R reset | ←/→ field | ↑/↓ load"
    )
