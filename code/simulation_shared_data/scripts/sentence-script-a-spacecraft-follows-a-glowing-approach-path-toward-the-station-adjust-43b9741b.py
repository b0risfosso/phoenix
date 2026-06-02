from vpython import *
import math
import random

# ISS Docking Corridor
# A spacecraft follows a glowing approach path toward the station, adjusting speed,
# angle, and alignment as docking markers pulse around the target port.

scene = canvas(
    title="ISS Docking Corridor",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.72, -0.28, -0.63)
scene.range = 24
scene.userspin = True
scene.userzoom = True
scene.caption = "Mouse: orbit/zoom camera. The spacecraft repeatedly aligns with the ISS docking corridor.\n"

# ---------- Utility ----------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, f):
    return a + (b - a) * f


def vlerp(a, b, f):
    return a + (b - a) * f


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) <= 1e-9:
        return fallback
    return norm(v)


def make_label(pos, text, height=11):
    return label(
        pos=pos,
        text=text,
        height=height,
        color=vector(0.12, 0.16, 0.22),
        box=False,
        opacity=0,
        line=False,
    )

# ---------- Earth ----------

earth_center = vector(-18, -21, -22)
earth = sphere(
    pos=earth_center,
    radius=22,
    color=vector(0.20, 0.48, 0.86),
    shininess=0.55,
    opacity=0.92,
)
cloud_bands = []
for i in range(14):
    angle = i * math.pi / 7
    band = ring(
        pos=earth_center + vector(0, 0.08 * math.sin(i), 0),
        axis=vector(math.sin(angle) * 0.25, 1, math.cos(angle) * 0.25),
        radius=22.15 + 0.05 * math.sin(i),
        thickness=0.045,
        color=vector(1, 1, 1),
        opacity=0.25,
    )
    cloud_bands.append(band)

continents = []
continent_specs = [
    (-11, -7, -6, 4.0, 1.1), (-24, -18, -13, 4.8, 1.2), (-9, -26, -10, 3.5, 0.9),
    (-18, -5, -28, 5.2, 1.0), (-31, -15, -22, 3.6, 0.8), (-2, -16, -30, 4.1, 0.7),
]
for x, y, z, r, op in continent_specs:
    continents.append(sphere(pos=vector(x, y, z), radius=r, color=vector(0.22, 0.62, 0.37), opacity=0.28 * op, shininess=0.1))

atmosphere = sphere(pos=earth_center, radius=22.8, color=vector(0.55, 0.78, 1.0), opacity=0.16)

# ---------- ISS model ----------

iss_anchor = vector(8, 1.3, 0)
dock_pos = iss_anchor + vector(-3.2, -0.05, 0)

station_parts = []
station_parts.append(cylinder(pos=iss_anchor + vector(-1.3, 0, 0), axis=vector(5.2, 0, 0), radius=0.36, color=vector(0.82, 0.86, 0.88), shininess=0.8))
station_parts.append(cylinder(pos=iss_anchor + vector(0.6, 0.52, 0), axis=vector(1.5, 0, 0), radius=0.26, color=vector(0.76, 0.80, 0.82), shininess=0.8))
station_parts.append(cylinder(pos=iss_anchor + vector(0.1, -0.52, 0), axis=vector(1.2, 0, 0), radius=0.23, color=vector(0.76, 0.80, 0.82), shininess=0.8))
station_parts.append(box(pos=iss_anchor + vector(0.0, 0, 0), size=vector(0.55, 0.95, 0.95), color=vector(0.68, 0.72, 0.76), shininess=0.5))
station_parts.append(box(pos=iss_anchor + vector(2.4, 0, 0), size=vector(0.55, 0.75, 0.75), color=vector(0.78, 0.82, 0.85), shininess=0.5))
station_parts.append(cylinder(pos=dock_pos + vector(-0.15, 0, 0), axis=vector(0.7, 0, 0), radius=0.54, color=vector(0.58, 0.62, 0.66), shininess=0.7))
station_parts.append(ring(pos=dock_pos + vector(-0.25, 0, 0), axis=vector(1, 0, 0), radius=0.70, thickness=0.045, color=vector(0.20, 0.50, 0.92)))

# truss and solar arrays
station_parts.append(cylinder(pos=iss_anchor + vector(-2.6, 0, 0), axis=vector(0, 0, 8.5), radius=0.055, color=vector(0.60, 0.64, 0.67)))
station_parts.append(cylinder(pos=iss_anchor + vector(2.7, 0, 0), axis=vector(0, 0, 8.5), radius=0.055, color=vector(0.60, 0.64, 0.67)))
solar_arrays = []
for sx in [-2.6, 2.7]:
    for zsign in [-1, 1]:
        for k in range(3):
            panel = box(
                pos=iss_anchor + vector(sx, 0.02 * ((-1) ** k), zsign * (1.55 + 1.05 * k)),
                size=vector(0.12, 2.25, 0.86),
                color=vector(0.16, 0.30, 0.62),
                opacity=0.82,
                shininess=0.4,
            )
            solar_arrays.append(panel)

# antennas and small modules
for idx, zoff in enumerate([-1.05, 1.05]):
    station_parts.append(cylinder(pos=iss_anchor + vector(1.3, 0.25, zoff), axis=vector(0, 1.35, 0.35 * zoff), radius=0.028, color=vector(0.48, 0.50, 0.52)))
    station_parts.append(sphere(pos=iss_anchor + vector(1.3, 1.55, zoff + 0.35 * zoff), radius=0.08, color=vector(0.9, 0.9, 0.78)))

# ---------- Approach corridor ----------

start_pos = vector(-15, -4.2, -4.8)
mid_pos = vector(-5.5, -0.8, -1.5)
near_pos = dock_pos + vector(-4.2, 0.15, 0.2)
axis_to_dock = safe_norm(dock_pos - near_pos, vector(1, 0, 0))

corridor_rings = []
ring_count = 11
for i in range(ring_count):
    u = i / (ring_count - 1)
    p = vlerp(start_pos, near_pos, u)
    p.y += math.sin(u * math.pi) * 1.3
    p.z += math.sin(u * math.pi * 1.4) * 0.55
    radius = lerp(2.2, 0.72, u)
    r = ring(pos=p, axis=axis_to_dock, radius=radius, thickness=0.035, color=vector(0.20, 0.66, 1.0), opacity=0.40)
    corridor_rings.append(r)

path_nodes = []
for i in range(ring_count - 1):
    a = corridor_rings[i].pos
    b = corridor_rings[i + 1].pos
    path_nodes.append(curve(pos=[a, b], color=vector(0.25, 0.70, 1.0), radius=0.018, opacity=0.35))

marker_lights = []
for angle_i in range(12):
    ang = 2 * math.pi * angle_i / 12
    p = dock_pos + vector(-0.35, math.cos(ang) * 1.05, math.sin(ang) * 1.05)
    marker_lights.append(sphere(pos=p, radius=0.08, color=vector(0.2, 0.7, 1.0), emissive=True))

docking_cone = cone(pos=dock_pos + vector(-2.2, 0, 0), axis=vector(2.05, 0, 0), radius=1.05, color=vector(0.25, 0.75, 1.0), opacity=0.11)

# ---------- Spacecraft ----------

ship = compound([
    cone(pos=vector(0.72, 0, 0), axis=vector(0.72, 0, 0), radius=0.38, color=vector(0.92, 0.94, 0.96), shininess=0.7),
    cylinder(pos=vector(-0.55, 0, 0), axis=vector(1.25, 0, 0), radius=0.38, color=vector(0.72, 0.77, 0.81), shininess=0.65),
    box(pos=vector(-0.15, 0.56, 0), size=vector(0.65, 0.08, 1.55), color=vector(0.14, 0.30, 0.62), opacity=0.88),
    box(pos=vector(-0.15, -0.56, 0), size=vector(0.65, 0.08, 1.55), color=vector(0.14, 0.30, 0.62), opacity=0.88),
    cylinder(pos=vector(-0.74, 0, 0), axis=vector(-0.25, 0, 0), radius=0.28, color=vector(0.42, 0.44, 0.46), shininess=0.3),
], pos=start_pos)
ship.axis = vector(1, 0.12, 0.15)

engine_glow = sphere(pos=ship.pos - norm(ship.axis) * 0.85, radius=0.20, color=vector(1.0, 0.55, 0.15), emissive=True, opacity=0.7)
ship_trail = curve(color=vector(0.08, 0.46, 0.95), radius=0.025, opacity=0.55)

alignment_beam = cylinder(pos=ship.pos, axis=dock_pos - ship.pos, radius=0.018, color=vector(0.15, 0.68, 1.0), opacity=0.20)

thruster_puffs = []
for _ in range(28):
    puff = sphere(pos=ship.pos, radius=0.035, color=vector(1.0, 0.65, 0.25), opacity=0, emissive=True)
    puff.vel = vector(0, 0, 0)
    puff.life = 0
    thruster_puffs.append(puff)

# ---------- HUD / readouts ----------

status_label = make_label(vector(-14.5, 7.0, 1.5), "", 13)
phase_label = make_label(vector(4.7, 4.2, 0), "DOCKING PORT", 10)
phase_label.color = vector(0.10, 0.26, 0.48)

speed_bar_back = box(pos=vector(-12.5, 5.8, 1.5), size=vector(4.2, 0.22, 0.04), color=vector(0.82, 0.86, 0.88), opacity=0.75)
speed_bar = box(pos=vector(-14.6, 5.8, 1.55), size=vector(0.3, 0.18, 0.05), color=vector(0.20, 0.65, 1.0), opacity=0.85)
alignment_bar_back = box(pos=vector(-12.5, 5.38, 1.5), size=vector(4.2, 0.22, 0.04), color=vector(0.82, 0.86, 0.88), opacity=0.75)
alignment_bar = box(pos=vector(-14.6, 5.38, 1.55), size=vector(0.3, 0.18, 0.05), color=vector(0.25, 0.80, 0.42), opacity=0.85)

# ---------- Motion systems ----------

round_timer = 0.0
round_length = 34.0
phase = "far approach"
ship.pos = start_pos
velocity = vector(0.25, 0.04, 0.02)
ship_angle_error = 0.6
capture_count = 0

control_noise = vector(0, 0, 0)
next_puff = 0


def reset_round():
    global round_timer, ship_angle_error, velocity, control_noise, capture_count
    round_timer = 0.0
    ship.pos = start_pos + vector(0, random.uniform(-0.45, 0.45), random.uniform(-0.45, 0.45))
    ship.axis = safe_norm(vector(1, random.uniform(-0.20, 0.22), random.uniform(-0.20, 0.22)))
    ship_angle_error = random.uniform(0.42, 0.78)
    velocity = vector(0.18, random.uniform(-0.02, 0.05), random.uniform(-0.03, 0.04))
    control_noise = vector(random.uniform(-0.04, 0.04), random.uniform(-0.07, 0.07), random.uniform(-0.07, 0.07))
    ship_trail.clear()


def bezier_path(u):
    # Cubic-ish staged approach path using two interpolations.
    u = clamp(u, 0, 1)
    a = vlerp(start_pos, mid_pos, u)
    b = vlerp(mid_pos, near_pos, u)
    c = vlerp(a, b, u)
    c.y += math.sin(u * math.pi) * 0.8
    c.z += math.sin(u * math.pi * 1.2) * 0.34
    return c


def emit_thruster(pos, direction, strength):
    global next_puff
    p = thruster_puffs[next_puff]
    next_puff = (next_puff + 1) % len(thruster_puffs)
    p.pos = pos
    p.radius = 0.045 + 0.07 * strength
    p.opacity = 0.75
    p.life = 1.0
    jitter = vector(random.uniform(-0.05, 0.05), random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08))
    p.vel = -safe_norm(direction, vector(1, 0, 0)) * (0.25 + strength * 0.35) + jitter

reset_round()

# ---------- Animation loop ----------

t = 0.0
dt = 0.025
while True:
    rate(60)
    t += dt
    round_timer += dt

    if round_timer > round_length:
        reset_round()

    progress = round_timer / round_length
    path_target = bezier_path(progress)
    dock_vec = dock_pos - ship.pos
    distance_to_dock = mag(dock_vec)
    desired_dir = safe_norm(dock_vec, vector(1, 0, 0))

    # Staged approach: far travel, alignment correction, slow final corridor hold, soft contact.
    if progress < 0.46:
        phase = "FAR APPROACH"
        target_speed = 0.125
        correction_gain = 0.038
    elif progress < 0.76:
        phase = "ANGLE + ALIGNMENT CORRECTION"
        target_speed = 0.083
        correction_gain = 0.060
    elif progress < 0.94:
        phase = "FINAL DOCKING CORRIDOR"
        target_speed = 0.043
        correction_gain = 0.085
    else:
        phase = "SOFT CAPTURE / RESET"
        target_speed = 0.018
        correction_gain = 0.105

    # Guidance correction toward moving target path and docking axis.
    lateral_error = path_target - ship.pos
    alignment_pull = (dock_pos - ship.pos) * 0.006
    sway = vector(0, math.sin(t * 2.1) * 0.006, math.cos(t * 1.7) * 0.006) * (1 - progress)
    acceleration = lateral_error * correction_gain + alignment_pull + sway + control_noise * (0.02 * (1 - progress))
    velocity += acceleration * dt

    current_speed = mag(velocity)
    if current_speed > target_speed:
        velocity *= lerp(1, target_speed / max(current_speed, 1e-6), 0.18)
    elif current_speed < target_speed * 0.55:
        velocity += desired_dir * target_speed * 0.08

    ship.pos += velocity

    # Smooth ship orientation toward docking port.
    ship.axis = safe_norm(vlerp(ship.axis, desired_dir, 0.035 + 0.08 * progress), vector(1, 0, 0))
    engine_glow.pos = ship.pos - safe_norm(ship.axis) * 0.96
    engine_glow.radius = 0.16 + 0.08 * math.sin(t * 11) ** 2 + 0.06 * (current_speed / 0.14)
    engine_glow.opacity = 0.45 + 0.25 * math.sin(t * 13) ** 2

    # Alignment beam and trail.
    alignment_beam.pos = ship.pos + safe_norm(ship.axis) * 0.4
    alignment_beam.axis = dock_pos - alignment_beam.pos
    alignment_beam.opacity = 0.10 + 0.18 * progress
    ship_trail.append(pos=ship.pos)
    # Avoid curve.points; only use npoints for compatibility with this VPython environment.
    if hasattr(ship_trail, "npoints") and ship_trail.npoints > 220:
        ship_trail.clear()

    # Thrusters fire when lateral error is visible.
    if int(t * 12) % 5 == 0:
        err_strength = clamp(mag(lateral_error) / 8, 0.05, 1.0)
        emit_thruster(ship.pos - safe_norm(ship.axis) * 0.78, lateral_error + vector(0.2, 0, 0), err_strength)

    for p in thruster_puffs:
        if p.life > 0:
            p.life -= dt * 1.8
            p.pos += p.vel
            p.opacity = max(0, p.life * 0.65)
            p.radius *= 1.006
        else:
            p.opacity = 0

    # Pulse corridor rings and docking markers.
    for i, r in enumerate(corridor_rings):
        pulse = 0.5 + 0.5 * math.sin(t * 3.3 - i * 0.55)
        r.opacity = 0.20 + 0.34 * pulse
        r.thickness = 0.024 + 0.025 * pulse
        r.color = vlerp(vector(0.12, 0.50, 1.0), vector(0.60, 0.92, 1.0), pulse)

    for i, m in enumerate(marker_lights):
        pulse = 0.5 + 0.5 * math.sin(t * 5.5 + i * 0.7)
        m.radius = 0.065 + 0.07 * pulse
        m.color = vlerp(vector(0.08, 0.45, 1.0), vector(0.85, 0.98, 1.0), pulse)

    docking_cone.opacity = 0.07 + 0.08 * (0.5 + 0.5 * math.sin(t * 4.0))

    # ISS solar array subtle flex/orbit motion.
    for i, panel in enumerate(solar_arrays):
        panel.rotate(angle=0.0018 * math.sin(t * 1.4 + i), axis=vector(1, 0, 0), origin=iss_anchor)

    for i, band in enumerate(cloud_bands):
        band.rotate(angle=0.0009 + i * 0.000025, axis=vector(0, 1, 0), origin=earth_center)
    atmosphere.opacity = 0.13 + 0.035 * math.sin(t * 1.1) ** 2

    # HUD metrics.
    alignment_error = mag(cross(safe_norm(ship.axis), desired_dir))
    alignment_score = clamp(1 - alignment_error, 0, 1)
    speed_score = clamp(current_speed / 0.14, 0, 1)
    speed_bar.size.x = 4.2 * speed_score
    speed_bar.pos.x = -14.6 + speed_bar.size.x / 2
    alignment_bar.size.x = 4.2 * alignment_score
    alignment_bar.pos.x = -14.6 + alignment_bar.size.x / 2

    dock_ready = distance_to_dock < 0.95 and alignment_score > 0.95 and current_speed < 0.07
    if dock_ready:
        station_parts[-1].color = vector(0.25, 0.85, 0.38)
    else:
        station_parts[-1].color = vector(0.9, 0.9, 0.78)

    status_label.text = (
        f"ISS DOCKING CORRIDOR\n"
        f"Phase: {phase}\n"
        f"Distance to port: {distance_to_dock:4.2f}\n"
        f"Speed: {current_speed:4.3f}\n"
        f"Alignment: {alignment_score * 100:4.0f}%"
    )
