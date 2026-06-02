from vpython import *
import math
import random

# Star Tap Engine
# Light-styled version with a pale background and readable labels.
# A civilization builds a glowing siphon around a star, drawing energy through
# rotating rings that brighten, strain, and self-correct as demand increases.
# New behavior: the star resists extraction by releasing bright pressure waves
# that force the rings to widen, tilt, and stabilize.
#
# Controls:
#   SPACE  : pause / resume
#   UP     : increase civilization demand
#   DOWN   : decrease civilization demand
#   R      : reset demand and strain
#   V      : toggle slow camera drift
#
# This script uses ring(...) instead of torus(...) for VPython compatibility.

scene.title = "Star Tap Engine — glowing siphon around a star"
scene.width = 1200
scene.height = 760
scene.background = vector(0.92, 0.96, 1.0)
scene.center = vector(0, 0, 0)
scene.range = 18
scene.forward = vector(-0.55, -0.28, -0.78)
scene.userspin = True
scene.userzoom = True

# ----------------------------- Utility helpers -----------------------------

def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return vector(lerp(c1.x, c2.x, t), lerp(c1.y, c2.y, t), lerp(c1.z, c2.z, t))


def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(0, 0, 0)
    return v / m

distant_light(direction=vector(-0.4, -0.6, -0.7), color=vector(0.95, 0.92, 0.86))
local_light(pos=vector(0, 4, 8), color=vector(0.55, 0.70, 1.0))

# ------------------------------- Scene state --------------------------------
paused = False
auto_camera = False
time_t = 0.0

base_demand = 0.55
demand = base_demand
demand_target = 0.68
strain = 0.15
instability = 0.0
correction_strength = 0.18
stored_energy = 0.0
transmitted_energy = 0.0
star_resistance = 0.08
pressure_wave_energy = 0.0
next_pressure_wave_time = 1.4

# ----------------------------- Central star ---------------------------------
star_core = sphere(
    pos=vector(0, 0, 0),
    radius=2.15,
    color=vector(1.0, 0.63, 0.18),
    emissive=True,
    shininess=0.7,
)
star_glow_1 = sphere(
    pos=vector(0, 0, 0),
    radius=2.85,
    color=vector(1.0, 0.42, 0.08),
    opacity=0.18,
    emissive=True,
)
star_glow_2 = sphere(
    pos=vector(0, 0, 0),
    radius=3.65,
    color=vector(1.0, 0.20, 0.03),
    opacity=0.075,
    emissive=True,
)

# Surface flares on the star.
flares = []
for i in range(34):
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(-0.95, 0.95)
    r = 2.20
    pos = vector(r * math.cos(theta) * math.cos(phi), r * math.sin(phi), r * math.sin(theta) * math.cos(phi))
    flares.append({
        "obj": sphere(pos=pos, radius=random.uniform(0.045, 0.12), color=vector(1, 0.92, 0.38), emissive=True),
        "theta": theta,
        "phi": phi,
        "speed": random.uniform(0.25, 0.75),
        "phase": random.uniform(0, 2 * math.pi),
    })

# ---------------------------- Siphon ring array -----------------------------
ring_specs = [
    (4.0, vector(0, 0, 0), vector(0, 1, 0), 0.050),
    (5.25, vector(0, 0, 0), vector(1, 0, 0), 0.045),
    (6.55, vector(0, 0, 0), vector(0, 0, 1), 0.042),
    (7.75, vector(0, 0, 0), vector(0.7, 1, 0.25), 0.040),
]

rings = []
for i, (radius, pos, axis, thickness) in enumerate(ring_specs):
    r = ring(
        pos=pos,
        axis=safe_norm(axis),
        radius=radius,
        thickness=thickness,
        color=vector(0.2, 0.75, 1.0),
        emissive=True,
    )
    r.opacity = 0.74
    # Larger transparent strain halo around each collector ring.
    halo = ring(
        pos=pos,
        axis=safe_norm(axis),
        radius=radius + 0.10,
        thickness=thickness * 2.4,
        color=vector(0.05, 0.45, 1.0),
        emissive=True,
        opacity=0.13,
    )
    rings.append({
        "ring": r,
        "halo": halo,
        "base_radius": radius,
        "axis": safe_norm(axis),
        "spin_speed": 0.26 + i * 0.09,
        "phase": random.uniform(0, 2 * math.pi),
        "health": 1.0,
        "local_strain": 0.0,
        "wave_push": 0.0,
        "target_widen": 0.0,
        "target_tilt": 0.0,
        "stabilized": 0.0,
        "current_axis": safe_norm(axis),
    })

# Siphon mouth: a narrow intake aperture facing the output conduit.
intake = ring(
    pos=vector(9.25, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.65,
    thickness=0.075,
    color=vector(0.20, 0.90, 1.0),
    emissive=True,
)
intake_halo = ring(
    pos=vector(9.25, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.86,
    thickness=0.18,
    color=vector(0.08, 0.55, 1.0),
    opacity=0.16,
    emissive=True,
)

# Civilization receiver / demand city.
city_base = cylinder(
    pos=vector(13.2, -1.4, 0),
    axis=vector(0, 2.8, 0),
    radius=1.2,
    color=vector(0.78, 0.84, 0.90),
    opacity=0.92,
)
city_core = sphere(
    pos=vector(13.2, 1.55, 0),
    radius=0.92,
    color=vector(0.15, 0.75, 1.0),
    emissive=True,
)
city_beacon = ring(
    pos=vector(13.2, 2.62, 0),
    axis=vector(0, 1, 0),
    radius=1.45,
    thickness=0.035,
    color=vector(0.18, 0.85, 1.0),
    emissive=True,
)

# Receiver towers that brighten as demand rises.
towers = []
for i in range(16):
    a = 2 * math.pi * i / 16
    rr = random.uniform(1.6, 2.65)
    h = random.uniform(0.65, 1.75)
    p = vector(13.2 + rr * math.cos(a), -1.4, rr * math.sin(a))
    tw = cylinder(pos=p, axis=vector(0, h, 0), radius=random.uniform(0.045, 0.09), color=vector(0.62, 0.72, 0.82))
    cap = sphere(pos=p + vector(0, h, 0), radius=tw.radius * 1.8, color=vector(0.08, 0.65, 1.0), emissive=True)
    towers.append((tw, cap, random.uniform(0, 2 * math.pi)))

# Main output beam and inner pulse beads.
main_beam = cylinder(
    pos=vector(9.25, 0, 0),
    axis=vector(3.65, 0, 0),
    radius=0.13,
    color=vector(0.15, 0.78, 1.0),
    opacity=0.42,
    emissive=True,
)
beam_halo = cylinder(
    pos=vector(9.25, 0, 0),
    axis=vector(3.65, 0, 0),
    radius=0.34,
    color=vector(0.08, 0.45, 1.0),
    opacity=0.13,
    emissive=True,
)

pulse_beads = []
for i in range(28):
    pulse_beads.append({
        "obj": sphere(pos=vector(9.25, 0, 0), radius=0.06, color=vector(0.55, 0.95, 1.0), emissive=True),
        "u": i / 28.0,
        "offset": vector(0, random.uniform(-0.22, 0.22), random.uniform(-0.22, 0.22)),
    })

# Energy streams: particles spiral from the star into collector rings and then toward intake.
stream_particles = []
stream_count = 180
for i in range(stream_count):
    stream_particles.append({
        "obj": sphere(pos=vector(0, 0, 0), radius=random.uniform(0.025, 0.065), color=vector(1.0, 0.75, 0.18), emissive=True),
        "u": random.random(),
        "lane": random.randrange(len(rings)),
        "phase": random.uniform(0, 2 * math.pi),
        "speed": random.uniform(0.10, 0.34),
        "trail": None,
    })

# Self-correction drones: small blue stabilizers that orbit strained rings.
drones = []
for i in range(18):
    lane = i % len(rings)
    drones.append({
        "obj": sphere(pos=vector(0, 0, 0), radius=0.10, color=vector(0.18, 1.0, 0.72), emissive=True),
        "lane": lane,
        "angle": random.uniform(0, 2 * math.pi),
        "speed": random.uniform(0.7, 1.1),
        "active": 0.0,
    })

# Warning fracture arcs. They appear when the collector is strained.
fractures = []
for i in range(26):
    c = curve(radius=0.018, color=vector(1.0, 0.18, 0.04), emissive=True, visible=False)
    fractures.append({"curve": c, "phase": random.uniform(0, 2 * math.pi), "lane": random.randrange(len(rings))})

# Stellar resistance pressure waves. Bright expanding shells start at the star,
# pass through the collector rings, and force them to widen/tilt before they stabilize.
pressure_waves = []
for i in range(9):
    shell = sphere(
        pos=vector(0, 0, 0),
        radius=2.35,
        color=vector(1.0, 0.72, 0.14),
        opacity=0.0,
        emissive=True,
        visible=False,
    )
    rim = ring(
        pos=vector(0, 0, 0),
        axis=vector(0, 1, 0),
        radius=2.35,
        thickness=0.035,
        color=vector(1.0, 0.82, 0.18),
        opacity=0.0,
        emissive=True,
        visible=False,
    )
    pressure_waves.append({
        "shell": shell,
        "rim": rim,
        "active": False,
        "radius": 2.35,
        "speed": 6.2,
        "strength": 0.0,
        "age": 0.0,
        "phase": random.uniform(0, 2 * math.pi),
        "hit": [False for _ in rings],
    })

resistance_label = label(
    pos=vector(0, 7.25, 0),
    text="",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.42, 0.18, 0.06),
)

# Demand meter and status labels.
meter_back = box(pos=vector(-11.5, 6.3, 0), size=vector(4.2, 0.16, 0.16), color=vector(0.72, 0.80, 0.88))
meter_fill = box(pos=vector(-13.55, 6.3, 0), size=vector(0.1, 0.22, 0.22), color=vector(0.18, 0.80, 1.0), emissive=True)
strain_back = box(pos=vector(-11.5, 5.85, 0), size=vector(4.2, 0.16, 0.16), color=vector(0.88, 0.78, 0.72))
strain_fill = box(pos=vector(-13.55, 5.85, 0), size=vector(0.1, 0.22, 0.22), color=vector(1.0, 0.35, 0.10), emissive=True)

status = label(
    pos=vector(-11.5, 6.95, 0),
    text="",
    height=13,
    border=8,
    box=False,
    opacity=0,
    color=vector(0.10, 0.24, 0.36),
)
mode_label = label(
    pos=vector(0, -8.0, 0),
    text="",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.14, 0.28, 0.40),
)

# Pale orbital guide lines.
for rad in [4.0, 5.25, 6.55, 7.75]:
    guide = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=rad, thickness=0.008, color=vector(0.55, 0.64, 0.72), opacity=0.30)

# ------------------------------ Event handling ------------------------------

def on_keydown(evt):
    global paused, demand_target, strain, instability, auto_camera, transmitted_energy, stored_energy, star_resistance, pressure_wave_energy, next_pressure_wave_time
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ("up", "w"):
        demand_target = clamp(demand_target + 0.12, 0.05, 1.55)
    elif key in ("down", "s"):
        demand_target = clamp(demand_target - 0.12, 0.05, 1.55)
    elif key == "r":
        demand_target = base_demand
        strain = 0.12
        instability = 0.0
        transmitted_energy = 0.0
        stored_energy = 0.0
        star_resistance = 0.08
        pressure_wave_energy = 0.0
        next_pressure_wave_time = time_t + 1.2
        for item in rings:
            item["health"] = 1.0
            item["local_strain"] = 0.0
            item["wave_push"] = 0.0
            item["target_widen"] = 0.0
            item["target_tilt"] = 0.0
            item["stabilized"] = 0.0
        for wave in pressure_waves:
            wave["active"] = False
            wave["shell"].visible = False
            wave["rim"].visible = False
            wave["shell"].opacity = 0.0
            wave["rim"].opacity = 0.0
    elif key == "v":
        auto_camera = not auto_camera

scene.bind("keydown", on_keydown)

# ----------------------------- Geometry helpers -----------------------------

def spiral_position(u, lane, phase, t):
    """Return particle position along a siphon stream."""
    ring_radius = rings[lane]["base_radius"]
    # Segment 1: star surface to ring field.
    if u < 0.62:
        q = u / 0.62
        q_smooth = q * q * (3 - 2 * q)
        radius = lerp(2.45, ring_radius, q_smooth)
        angle = phase + 4.8 * q + t * (0.55 + 0.08 * lane)
        y_wave = math.sin(angle * 1.4 + t * 0.9) * 0.55 * (1 - q) + math.sin(phase + t) * 0.10
        # Different lanes sit in slightly different planes.
        if lane == 0:
            return vector(radius * math.cos(angle), y_wave, radius * math.sin(angle))
        elif lane == 1:
            return vector(y_wave, radius * math.cos(angle), radius * math.sin(angle))
        elif lane == 2:
            return vector(radius * math.cos(angle), radius * math.sin(angle), y_wave)
        else:
            tilt = 0.38
            return vector(radius * math.cos(angle), radius * math.sin(angle) * tilt + y_wave, radius * math.sin(angle))
    # Segment 2: ring field to intake.
    q = (u - 0.62) / 0.38
    q_smooth = q * q * (3 - 2 * q)
    start_angle = phase + 4.8 + t * (0.55 + 0.08 * lane)
    start = vector(ring_radius * math.cos(start_angle), math.sin(start_angle + phase) * 0.65, ring_radius * math.sin(start_angle))
    end = vector(9.25, math.sin(phase + t * 2.1) * 0.32, math.cos(phase + t * 1.7) * 0.32)
    bend = vector(3.0 + 2.4 * q, math.sin(phase + q * math.pi) * 1.2, math.cos(phase + q * math.pi) * 1.2)
    # Quadratic Bezier curve from ring to intake.
    a = start * (1 - q_smooth) + bend * q_smooth
    b = bend * (1 - q_smooth) + end * q_smooth
    return a * (1 - q_smooth) + b * q_smooth


def orthonormal_basis(axis):
    axis = safe_norm(axis)
    helper = vector(0, 1, 0) if abs(dot(axis, vector(0, 1, 0))) < 0.9 else vector(1, 0, 0)
    u = safe_norm(cross(axis, helper))
    v = safe_norm(cross(axis, u))
    return u, v


def launch_pressure_wave(strength):
    """Activate one reusable pressure wave shell from the star."""
    for wave in pressure_waves:
        if not wave["active"]:
            wave["active"] = True
            wave["radius"] = 2.35
            wave["speed"] = 5.4 + 3.6 * strength
            wave["strength"] = clamp(strength, 0.10, 1.0)
            wave["age"] = 0.0
            wave["phase"] = random.uniform(0, 2 * math.pi)
            wave["hit"] = [False for _ in rings]
            wave["shell"].visible = True
            wave["rim"].visible = True
            return True
    return False

# -------------------------------- Main loop ----------------------------------
while True:
    rate(60)
    if paused:
        mode_label.text = "PAUSED  |  SPACE resumes  |  UP/DOWN changes demand  |  R resets"
        continue

    dt = 1 / 60.0
    time_t += dt

    # Demand slowly pulses upward/downward, with user-controlled target.
    demand_target += math.sin(time_t * 0.065) * 0.0009 + random.uniform(-0.0012, 0.0012)
    demand_target = clamp(demand_target, 0.08, 1.55)
    demand += (demand_target - demand) * 0.025

    # Energy extraction capacity: rises when correction is active, falls with ring damage.
    avg_health = sum(item["health"] for item in rings) / len(rings)
    correction_strength = clamp(0.13 + 0.62 * strain + 0.16 * instability, 0.10, 0.92)
    capacity = 0.70 + 0.55 * avg_health + correction_strength * 0.32
    overload = max(0.0, demand - capacity * 0.78)

    # Strain dynamics: demand increases strain; correction pulls it down.
    strain += (demand * 0.020 + overload * 0.055 - correction_strength * 0.018 - avg_health * 0.006)
    strain += math.sin(time_t * 2.4) * 0.0018
    strain = clamp(strain, 0.0, 1.25)
    instability += (overload * 0.040 + max(0, strain - 0.72) * 0.018 - correction_strength * 0.018)
    instability = clamp(instability, 0.0, 1.0)

    extracted = clamp(demand * (1.0 - 0.30 * instability) * avg_health, 0.0, 1.4)
    transmitted_energy += extracted * dt
    stored_energy += (extracted - demand * 0.64) * dt
    stored_energy = clamp(stored_energy, -2.5, 8.0)

    # Stellar resistance rises with extraction pressure. When resistance peaks,
    # the star throws pressure waves outward into the collector array.
    star_resistance += (0.10 + 0.58 * extracted + 0.30 * strain - star_resistance) * 0.018
    pressure_wave_energy += max(0.0, extracted - 0.42) * dt * (0.50 + 0.65 * demand)
    spontaneous_resistance = star_resistance > 0.55 and time_t > next_pressure_wave_time
    stored_wave = pressure_wave_energy > 0.62 and time_t > next_pressure_wave_time
    if spontaneous_resistance or stored_wave:
        wave_strength = clamp(0.28 + 0.46 * star_resistance + 0.24 * strain + random.uniform(-0.05, 0.08), 0.18, 1.0)
        if launch_pressure_wave(wave_strength):
            pressure_wave_energy = max(0.0, pressure_wave_energy - 0.58)
            next_pressure_wave_time = time_t + lerp(2.8, 1.05, clamp(demand / 1.55, 0, 1)) + random.uniform(0.0, 0.9)
            instability = clamp(instability + 0.07 * wave_strength, 0.0, 1.0)

    active_wave_strength = 0.0
    for wave in pressure_waves:
        if not wave["active"]:
            continue
        wave["age"] += dt
        wave["radius"] += wave["speed"] * dt
        active_wave_strength = max(active_wave_strength, wave["strength"] * clamp(1.0 - wave["age"] / 3.2, 0.0, 1.0))
        fade = clamp(1.0 - (wave["radius"] - 2.2) / 9.0, 0.0, 1.0)
        shell = wave["shell"]
        rim = wave["rim"]
        shell.radius = wave["radius"]
        shell.opacity = 0.035 * fade * wave["strength"]
        shell.color = mix_color(vector(1.0, 0.66, 0.14), vector(1.0, 0.96, 0.42), wave["strength"])
        rim.radius = wave["radius"]
        rim.thickness = 0.025 + 0.060 * wave["strength"]
        rim.opacity = 0.28 * fade * wave["strength"]
        rim.axis = safe_norm(vector(0.18 * math.sin(time_t * 1.4 + wave["phase"]), 1.0, 0.18 * math.cos(time_t * 1.2 + wave["phase"])))
        rim.color = mix_color(vector(1.0, 0.50, 0.08), vector(1.0, 1.0, 0.60), wave["strength"])

        for idx, item in enumerate(rings):
            # The expanding wave visibly hits each ring near its orbital radius.
            if not wave["hit"][idx] and wave["radius"] >= item["base_radius"] - 0.18:
                wave["hit"][idx] = True
                push = wave["strength"] * (1.05 - 0.08 * idx)
                item["wave_push"] = clamp(item["wave_push"] + 0.72 * push, 0.0, 1.65)
                item["target_widen"] = clamp(item["target_widen"] + 0.58 * push, 0.0, 1.45)
                item["target_tilt"] = clamp(item["target_tilt"] + 0.26 * push, 0.0, 0.74)
                item["stabilized"] = 0.0
        if wave["radius"] > 11.8 or fade <= 0.0:
            wave["active"] = False
            shell.visible = False
            rim.visible = False
            shell.opacity = 0.0
            rim.opacity = 0.0

    # Star breathing and flare activity.
    star_pulse = 0.5 + 0.5 * math.sin(time_t * 2.2)
    resistance_pulse = active_wave_strength + 0.25 * star_resistance
    star_core.radius = 2.12 + 0.055 * star_pulse + 0.08 * extracted + 0.045 * resistance_pulse
    star_glow_1.radius = 2.80 + 0.16 * star_pulse + 0.22 * extracted + 0.22 * resistance_pulse
    star_glow_2.radius = 3.55 + 0.28 * star_pulse + 0.40 * strain + 0.55 * resistance_pulse
    base_star_color = mix_color(vector(1.0, 0.56, 0.15), vector(1.0, 0.95, 0.42), clamp(extracted * 0.55, 0, 1))
    star_core.color = mix_color(base_star_color, vector(1.0, 0.32, 0.05), clamp(star_resistance * 0.55 + active_wave_strength * 0.35, 0, 1))
    star_glow_1.opacity = clamp(0.12 + 0.07 * extracted + 0.05 * active_wave_strength, 0.08, 0.38)
    star_glow_2.opacity = clamp(0.05 + 0.05 * strain + 0.06 * active_wave_strength, 0.035, 0.24)

    for f in flares:
        f["theta"] += f["speed"] * dt * (0.45 + extracted)
        phi = f["phi"] + 0.05 * math.sin(time_t * 1.1 + f["phase"])
        r = 2.18 + 0.10 * math.sin(time_t * 3.0 + f["phase"])
        f["obj"].pos = vector(r * math.cos(f["theta"]) * math.cos(phi), r * math.sin(phi), r * math.sin(f["theta"]) * math.cos(phi))
        f["obj"].radius = 0.035 + 0.09 * (0.5 + 0.5 * math.sin(time_t * 5.0 + f["phase"])) * (0.6 + extracted)
        f["obj"].color = mix_color(vector(1.0, 0.60, 0.10), vector(1.0, 1.0, 0.55), random.uniform(0.15, 0.45))

    # Rings brighten, strain, deform, and self-correct.
    for idx, item in enumerate(rings):
        local_wave = 0.5 + 0.5 * math.sin(time_t * (1.8 + idx * 0.34) + item["phase"])
        item["wave_push"] *= 0.975
        item["target_widen"] *= 0.992
        item["target_tilt"] *= 0.988
        target_stability = clamp(correction_strength * item["health"] - item["wave_push"] * 0.10, 0.0, 1.0)
        item["stabilized"] += (target_stability - item["stabilized"]) * 0.025
        item["local_strain"] = clamp(strain * (0.75 + 0.34 * local_wave) + overload * 0.45 + item["wave_push"] * 0.38, 0.0, 1.55)

        # Damage accumulates only under strong strain, repairs slowly when correction succeeds.
        if item["local_strain"] > 0.92:
            item["health"] -= (item["local_strain"] - 0.92) * 0.006
        else:
            item["health"] += correction_strength * 0.0025
        item["health"] = clamp(item["health"], 0.42, 1.0)

        strain_color = mix_color(vector(0.08, 0.74, 1.0), vector(1.0, 0.24, 0.05), clamp((item["local_strain"] - 0.35) / 0.85, 0, 1))
        stable_color = mix_color(vector(0.08, 0.74, 1.0), vector(0.25, 1.0, 0.72), correction_strength * item["health"] * 0.65)
        final_color = mix_color(stable_color, strain_color, clamp(item["local_strain"], 0, 1))

        item["ring"].color = final_color
        item["halo"].color = mix_color(final_color, vector(1.0, 1.0, 1.0), 0.20)
        item["ring"].opacity = clamp(0.48 + 0.35 * extracted + 0.18 * local_wave, 0.42, 0.95)
        item["halo"].opacity = clamp(0.08 + 0.18 * item["local_strain"] + 0.08 * correction_strength, 0.05, 0.42)
        # Pressure waves force rings to widen. Stabilization slowly pulls them
        # toward an expanded safe radius rather than snapping back.
        wave_widen = item["target_widen"] * (0.55 + 0.45 * math.sin(time_t * 5.2 + idx) ** 2)
        stabilization_widen = 0.30 * item["stabilized"] * clamp(star_resistance, 0.0, 1.0)
        deform = 0.08 * math.sin(time_t * 4.6 + idx) * item["local_strain"] + 0.18 * overload + wave_widen + stabilization_widen
        item["ring"].radius = item["base_radius"] + deform
        item["halo"].radius = item["base_radius"] + 0.15 + deform * 1.25

        # Pressure waves also tilt the rings. Correction drones damp the wobble
        # until the ring stabilizes in a slightly safer orientation.
        pre = 0.035 * math.sin(time_t * item["spin_speed"] * 5 + idx) * (1 + item["local_strain"])
        wave_tilt = item["target_tilt"] * (0.35 + 0.65 * math.sin(time_t * 3.1 + idx))
        stable_tilt = 0.12 * item["stabilized"] * math.sin(idx * 1.7 + 0.4)
        base_axis = item["axis"]
        desired_axis = safe_norm(base_axis + vector(pre + wave_tilt, pre * 0.6 + stable_tilt, -pre * 0.4 + wave_tilt * 0.45))
        item["current_axis"] = safe_norm(item["current_axis"] * 0.86 + desired_axis * 0.14)
        item["ring"].axis = item["current_axis"]
        item["halo"].axis = item["ring"].axis
        item["phase"] += item["spin_speed"] * dt * (1.0 + 1.4 * demand - 0.65 * instability + 0.35 * item["stabilized"])

    # Intake and beam respond to demand/strain.
    intake.radius = 1.55 + 0.12 * math.sin(time_t * 3.4) + 0.18 * extracted
    intake.thickness = 0.055 + 0.055 * demand
    intake.color = mix_color(vector(0.08, 0.72, 1.0), vector(1.0, 0.42, 0.12), strain * 0.65)
    intake_halo.radius = intake.radius + 0.24 + 0.12 * strain
    intake_halo.opacity = clamp(0.10 + 0.18 * demand + 0.08 * strain, 0.08, 0.45)

    main_beam.radius = clamp(0.10 + 0.17 * extracted + 0.04 * math.sin(time_t * 8), 0.08, 0.42)
    beam_halo.radius = main_beam.radius * (2.3 + strain)
    main_beam.opacity = clamp(0.28 + 0.30 * extracted, 0.24, 0.82)
    beam_halo.opacity = clamp(0.08 + 0.12 * demand + 0.05 * strain, 0.05, 0.34)
    main_beam.color = mix_color(vector(0.12, 0.78, 1.0), vector(1.0, 0.55, 0.18), strain * 0.7)
    beam_halo.color = mix_color(vector(0.06, 0.45, 1.0), vector(1.0, 0.18, 0.06), strain * 0.55)

    # Energy particles along siphon streams.
    for p in stream_particles:
        p["u"] += dt * p["speed"] * (0.52 + 1.35 * demand)
        if p["u"] > 1.0:
            p["u"] -= 1.0
            p["lane"] = random.randrange(len(rings))
            p["phase"] = random.uniform(0, 2 * math.pi)
            p["speed"] = random.uniform(0.10, 0.34)
        pos = spiral_position(p["u"], p["lane"], p["phase"], time_t)
        jitter = vector(random.uniform(-0.015, 0.015), random.uniform(-0.015, 0.015), random.uniform(-0.015, 0.015)) * (1 + strain)
        p["obj"].pos = pos + jitter
        heat_t = clamp(p["u"] * 0.8 + demand * 0.2, 0, 1)
        p["obj"].color = mix_color(vector(1.0, 0.65, 0.10), vector(0.22, 0.92, 1.0), heat_t)
        if strain > 0.74 and random.random() < 0.035:
            p["obj"].color = vector(1.0, 0.20, 0.04)
        p["obj"].radius = clamp(0.022 + 0.060 * demand * (0.6 + 0.4 * math.sin(time_t * 6 + p["phase"])), 0.018, 0.10)

    # Output beam bead motion.
    for bead in pulse_beads:
        bead["u"] += dt * (0.42 + 1.2 * extracted)
        if bead["u"] > 1:
            bead["u"] -= 1
            bead["offset"] = vector(0, random.uniform(-0.22, 0.22), random.uniform(-0.22, 0.22))
        q = bead["u"]
        bead["obj"].pos = vector(9.25 + 3.65 * q, 0, 0) + bead["offset"] * (0.3 + 0.8 * math.sin(math.pi * q))
        bead["obj"].radius = 0.035 + 0.09 * demand * math.sin(math.pi * q)
        bead["obj"].color = mix_color(vector(0.48, 0.92, 1.0), vector(1.0, 0.55, 0.15), strain * 0.60)

    # Self-correction drones orbit the most strained rings and visibly cool them.
    for d in drones:
        lane = d["lane"]
        item = rings[lane]
        d["active"] += (clamp(item["local_strain"] - 0.35, 0, 1) - d["active"]) * 0.07
        d["angle"] += dt * d["speed"] * (0.55 + 2.0 * d["active"])
        u, v = orthonormal_basis(item["ring"].axis)
        rad = item["base_radius"] + 0.42 + 0.18 * math.sin(time_t * 3 + d["angle"])
        d["obj"].pos = item["ring"].pos + u * math.cos(d["angle"]) * rad + v * math.sin(d["angle"]) * rad
        d["obj"].radius = 0.065 + 0.105 * d["active"]
        d["obj"].color = mix_color(vector(0.15, 0.85, 1.0), vector(0.35, 1.0, 0.55), d["active"])

    # Warning fractures: jagged red arcs appear under high strain, then fade after correction.
    for f in fractures:
        lane = f["lane"]
        item = rings[lane]
        visible = item["local_strain"] > 0.78 and random.random() < (0.18 + 0.48 * instability)
        c = f["curve"]
        c.visible = visible
        if visible:
            c.clear()
            u, v = orthonormal_basis(item["ring"].axis)
            start = f["phase"] + time_t * 0.8
            arc_len = random.uniform(0.18, 0.52)
            pts = []
            for k in range(6):
                a = start + arc_len * k
                rad = item["base_radius"] + random.uniform(-0.08, 0.16)
                offset = item["ring"].pos + u * math.cos(a) * rad + v * math.sin(a) * rad
                offset += item["ring"].axis * random.uniform(-0.08, 0.08)
                pts.append(offset)
            for pt in pts:
                c.append(pt)
            c.color = mix_color(vector(1.0, 0.12, 0.02), vector(1.0, 0.82, 0.20), random.random() * 0.3)
            c.radius = 0.010 + 0.025 * strain

    # Civilization receiver responds to incoming energy and demand.
    city_brightness = clamp(0.22 + 0.70 * extracted + 0.25 * stored_energy / 8.0, 0.10, 1.0)
    city_core.radius = 0.75 + 0.22 * city_brightness + 0.08 * math.sin(time_t * 4.0)
    city_core.color = mix_color(vector(0.08, 0.48, 0.85), vector(0.50, 1.0, 0.95), city_brightness)
    city_beacon.radius = 1.26 + 0.35 * demand + 0.05 * math.sin(time_t * 5)
    city_beacon.color = mix_color(vector(0.10, 0.65, 1.0), vector(1.0, 0.80, 0.22), clamp(demand - 0.55, 0, 1))
    city_beacon.rotate(angle=0.03 + 0.03 * demand, axis=vector(0, 1, 0), origin=city_beacon.pos)
    for tw, cap, ph in towers:
        cap.color = mix_color(vector(0.08, 0.50, 0.92), vector(0.68, 1.0, 0.96), clamp(city_brightness + 0.15 * math.sin(time_t * 3 + ph), 0, 1))
        cap.radius = tw.radius * (1.5 + 1.7 * city_brightness + 0.35 * math.sin(time_t * 2.0 + ph))

    # Demand and strain meters.
    demand_meter = clamp(demand / 1.55, 0, 1)
    strain_meter = clamp(strain / 1.25, 0, 1)
    meter_fill.size.x = 4.2 * demand_meter
    meter_fill.pos.x = -13.6 + meter_fill.size.x / 2
    meter_fill.color = mix_color(vector(0.14, 0.78, 1.0), vector(1.0, 0.70, 0.16), demand_meter)
    strain_fill.size.x = 4.2 * strain_meter
    strain_fill.pos.x = -13.6 + strain_fill.size.x / 2
    strain_fill.color = mix_color(vector(0.16, 0.88, 0.52), vector(1.0, 0.16, 0.05), strain_meter)

    if active_wave_strength > 0.20:
        mode = "stellar resistance: pressure wave crossing rings"
    elif star_resistance > 0.58:
        mode = "star resisting extraction: rings widened and stabilizing"
    elif strain < 0.45:
        mode = "stable siphon"
    elif strain < 0.78:
        mode = "rising load: rings brightening"
    elif strain < 1.02:
        mode = "strain warning: correction drones active"
    else:
        mode = "critical draw: system self-correcting"

    status.text = (
        f"DEMAND {demand:0.2f}   STRAIN {strain:0.2f}   "
        f"RESISTANCE {star_resistance:0.2f}   RING HEALTH {avg_health:0.2f}   ENERGY SENT {transmitted_energy:0.1f}"
    )
    mode_label.text = (
        f"{mode}  |  UP/DOWN demand  |  SPACE pause  |  R reset  |  V camera"
    )
    resistance_label.text = (
        "STAR PRESSURE WAVES FORCE RINGS TO WIDEN, TILT, THEN STABILIZE"
        if star_resistance > 0.48 or active_wave_strength > 0.12 else
        "star resistance building beneath the siphon"
    )

    # Optional slow camera drift.
    if auto_camera:
        scene.forward = vector(
            -0.55 + 0.10 * math.sin(time_t * 0.10),
            -0.28 + 0.06 * math.sin(time_t * 0.07),
            -0.78 + 0.10 * math.cos(time_t * 0.09),
        )
