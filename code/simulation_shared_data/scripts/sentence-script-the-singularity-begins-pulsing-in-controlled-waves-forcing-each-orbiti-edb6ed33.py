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

New behavior:
  The singularity now pulses in controlled gravity waves. Each passing wave
  temporarily deepens the well, forcing every massive body to make visible
  orbital corrections. Bodies that drift too close flare red and receive
  emergency tangential / outward correction before they cross the risk zone.

Requirements:
  pip install vpython

Styling:
  Light background and high-contrast objects for bright display.

Run:
  python gravity_well_dynamo_pulsing_singularity.py
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
MAX_STREAMS = 38

paused = False
collector_load = 1.0
control_field = 1.0
stored_energy = 0.0
total_power = 0.0
phase = 0.0
sim_time = 0.0
pulse_phase = 0.0
pulse_strength = 0.0
near_risk_count = 0

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

# Controlled gravity wave shells: expanding pulse rings show the singularity's
# regulated waves before they reach and disturb the orbiting bodies.
pulse_wave_rings = []
for n in range(6):
    pulse_wave_rings.append(
        ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=3.2 + n * 3.1,
            thickness=0.035,
            color=vector(0.18, 0.56, 1.0),
            emissive=True,
            opacity=0.08,
        )
    )

risk_zone = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=5.8,
    thickness=0.055,
    color=vector(1.0, 0.28, 0.18),
    emissive=True,
    opacity=0.20,
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
    body.base_radius = body_radius
    body.adjust_flash = 0.0
    body.risk_flash = 0.0
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
        body.adjust_flash = 0.0
        body.risk_flash = 0.0
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
    pulse_phase += DT * (1.05 + 0.25 * control_field)
    pulse_strength = 0.5 + 0.5 * sin(pulse_phase * 2.0)
    total_power = 0.0
    mean_radius = 0.0
    mean_speed = 0.0
    active_streams = 0
    near_risk_count = 0

    # Containment pulse and rotating field rings. The singularity now releases
    # controlled gravity waves; the visible rings expand outward and the
    # gravitational pull rises and falls with the wave phase.
    containment_pulse = 0.5 + 0.5 * sin(phase * 3.0)
    gravity_wave = 0.78 + 0.44 * pulse_strength
    singularity.radius = 0.86 + 0.24 * pulse_strength
    singularity.color = vector(0.18 + 0.18 * pulse_strength, 0.20 + 0.10 * pulse_strength, 0.30 + 0.18 * pulse_strength)
    inner_glow.radius = 1.18 + 0.44 * pulse_strength
    inner_glow.opacity = 0.18 + 0.28 * pulse_strength
    outer_halo.radius = 2.10 + 0.90 * pulse_strength
    outer_halo.opacity = 0.06 + 0.12 * pulse_strength + 0.04 * control_field
    risk_zone.radius = 5.5 + 0.45 * pulse_strength
    risk_zone.opacity = 0.12 + 0.25 * pulse_strength
    risk_zone.rotate(angle=0.004 + 0.006 * pulse_strength, axis=vector(0, 1, 0), origin=vector(0, 0, 0))

    for n, wave_ring in enumerate(pulse_wave_rings):
        offset = (pulse_phase * 5.2 + n * 3.2) % 18.5
        wave_ring.radius = 3.2 + offset
        wave_ring.thickness = 0.025 + 0.055 * pulse_strength * (1.0 - offset / 20.0)
        wave_ring.opacity = clamp((0.28 + 0.22 * pulse_strength) * (1.0 - offset / 20.0), 0.02, 0.42)
        wave_ring.color = vector(0.12 + 0.22 * pulse_strength, 0.46 + 0.28 * pulse_strength, 1.0)

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
        # Pulse waves periodically deepen the well, making all orbits visibly tighten.
        local_wave = 0.82 + 0.34 * sin(pulse_phase * 2.0 - r * 0.43 + body.phase)
        effective_pull = gravity_wave * local_wave
        gravity_acc = -radial * (G * CENTER_MASS * effective_pull / (r * r + SOFTENING * SOFTENING))

        # Control field prevents impact and converts unstable plunge into orbital shear.
        # During pulse peaks, each body must actively correct its path or enter the risk zone.
        safe = (body.safe_radius + 0.55 * pulse_strength) / control_field
        risk_margin = clamp((safe + 1.45 - r) / 2.4, 0.0, 1.0)
        pulse_pressure = clamp((pulse_strength - 0.42) * 1.7, 0.0, 1.0)
        correction_need = clamp(risk_margin * 0.70 + pulse_pressure * 0.55, 0.0, 1.0)
        if correction_need > 0.05:
            tangent_correction = tangential_direction(pos, body.phase) * (2.2 + 3.0 * pulse_pressure) * correction_need
            outward_correction = radial * (1.2 + 7.0 * risk_margin) * correction_need
            gravity_acc += tangent_correction + outward_correction
            body.adjust_flash = clamp(body.adjust_flash + 0.18 * correction_need, 0.0, 1.0)
        if r < safe:
            near_risk_count += 1
            repulse_strength = (safe - r) * 24.0 * control_field * (1.0 + pulse_strength)
            gravity_acc += radial * repulse_strength
            body.vel += tangential_direction(pos, body.phase) * (0.11 * repulse_strength * DT)
            body.risk_flash = 1.0

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

        # Visual heat/color from power extraction plus blue correction flashes and red risk flares.
        base_col = thermal_color(body.heat)
        adjust_col = vector(0.12, 0.62, 1.0)
        risk_col = vector(1.0, 0.16, 0.08)
        body.color = base_col * (1.0 - 0.55 * body.adjust_flash) + adjust_col * (0.55 * body.adjust_flash)
        body.color = body.color * (1.0 - 0.75 * body.risk_flash) + risk_col * (0.75 * body.risk_flash)
        body.radius = body.base_radius * (1.0 + 0.08 * body.heat * sin(phase * 12 + i) + 0.18 * body.adjust_flash + 0.22 * body.risk_flash)
        body.adjust_flash *= 0.92
        body.risk_flash *= 0.86

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

        # Emit power streams from hot / close bodies to the collector and grid towers.
        if body.heat > 0.18 and (i + int(phase * 18)) % 5 == 0:
            collector_point = norm(vector(body.pos.x, 0, body.pos.z)) * collector_ring.radius
            collector_point.y = body.pos.y * 0.15
            emit_stream(body.pos, collector_point, body.heat)
        if body.heat > 0.35 and (i + int(phase * 12)) % 9 == 0:
            emit_stream(body.pos, nearest_tower(body.pos), body.heat)

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
        f"gravity pulse: {pulse_strength:4.2f}    bodies near risk: {near_risk_count:2d}\n"
        f"mean orbit radius: {mean_radius:4.1f}    mean speed: {mean_speed:4.1f}\n"
        "blue flash = path correction | red flare = too close | Space pause | R reset"
    )
