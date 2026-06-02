from vpython import *
import math
import random

# Star Tap Engine
# Light-styled version with a pale background and readable labels.
# A civilization builds a glowing siphon around a star, drawing energy through
# rotating rings that brighten, strain, and self-correct as demand increases.
# Evolution: uneven civilization demand surges make individual rings overheat,
# dim, and redirect flow toward overloaded city sectors.
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
surge_timer = 0.0
surge_focus = 0

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
        "local_demand": 0.25,
        "overheat": 0.0,
        "redirect": 0.0,
        "dim": 0.0,
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

# Four civilization districts draw uneven power from matching siphon rings.
# When one district surges, its ring overheats while low-demand rings dim and bend
# surplus flow toward the stressed district.
city_sectors = []
sector_colors = [
    vector(0.16, 0.62, 1.0),
    vector(0.18, 0.86, 0.56),
    vector(1.0, 0.68, 0.18),
    vector(0.78, 0.34, 1.0),
]
for i in range(4):
    a = i * math.pi / 2 + math.pi / 4
    base = vector(13.2 + 3.0 * math.cos(a), -1.25, 3.0 * math.sin(a))
    mast = cylinder(pos=base, axis=vector(0, 1.15, 0), radius=0.12, color=vector(0.72, 0.78, 0.84), opacity=0.9)
    dome = sphere(pos=base + vector(0, 1.28, 0), radius=0.36, color=sector_colors[i], emissive=True)
    ringlet = ring(pos=base + vector(0, 1.73, 0), axis=vector(0, 1, 0), radius=0.62, thickness=0.025, color=sector_colors[i], emissive=True)
    city_sectors.append({
        "mast": mast,
        "dome": dome,
        "ring": ringlet,
        "angle": a,
        "demand": 0.28,
        "target": 0.28,
        "phase": random.uniform(0, 2 * math.pi),
    })

# Curved redirect conduits from dim rings to the currently overloaded district.
redirect_curves = []
for i in range(4):
    c = curve(radius=0.025, color=vector(0.18, 0.70, 1.0), emissive=True, visible=True)
    redirect_curves.append(c)

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
    global paused, demand_target, strain, instability, auto_camera, transmitted_energy, stored_energy, surge_timer, surge_focus
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
        surge_timer = 0.0
        surge_focus = 0
        for item in rings:
            item["health"] = 1.0
            item["local_strain"] = 0.0
            item["local_demand"] = 0.25
            item["overheat"] = 0.0
            item["redirect"] = 0.0
            item["dim"] = 0.0
        for i, sector in enumerate(city_sectors):
            sector["target"] = 0.28
            sector["demand"] = 0.28
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
    focus_sector = city_sectors[surge_focus]
    redirect_amt = rings[lane].get("redirect", 0.0)
    end = vector(9.25, math.sin(phase + t * 2.1) * 0.32, math.cos(phase + t * 1.7) * 0.32)
    end += vector(0, 0.55 * math.sin(focus_sector["angle"]) * redirect_amt, 0.55 * math.cos(focus_sector["angle"]) * redirect_amt)
    bend = vector(3.0 + 2.4 * q, math.sin(phase + q * math.pi) * 1.2, math.cos(phase + q * math.pi) * 1.2)
    bend += vector(0.0, 1.6 * math.sin(focus_sector["angle"]) * redirect_amt, 1.6 * math.cos(focus_sector["angle"]) * redirect_amt)
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

    # Uneven city demand: a different district periodically surges, pulling hard
    # on its assigned ring while neighboring districts dip and redirect spare flow.
    surge_timer -= dt
    if surge_timer <= 0:
        surge_focus = random.randrange(len(city_sectors))
        surge_timer = random.uniform(3.8, 7.0)
        for i, sector in enumerate(city_sectors):
            if i == surge_focus:
                sector["target"] = random.uniform(0.95, 1.45)
            elif random.random() < 0.55:
                sector["target"] = random.uniform(0.08, 0.28)
            else:
                sector["target"] = random.uniform(0.30, 0.65)

    sector_total = 0.0
    for i, sector in enumerate(city_sectors):
        # gentle district flicker keeps demand visibly uneven between major surges
        sector["target"] += 0.003 * math.sin(time_t * (0.9 + 0.17 * i) + sector["phase"])
        sector["target"] = clamp(sector["target"], 0.05, 1.55)
        sector["demand"] += (sector["target"] - sector["demand"]) * 0.035
        sector_total += sector["demand"]

    unevenness = max(sector["demand"] for sector in city_sectors) - min(sector["demand"] for sector in city_sectors)
    demand = clamp(0.58 * demand + 0.42 * (sector_total / len(city_sectors)), 0.06, 1.65)

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

    # Star breathing and flare activity.
    star_pulse = 0.5 + 0.5 * math.sin(time_t * 2.2)
    star_core.radius = 2.12 + 0.055 * star_pulse + 0.08 * extracted
    star_glow_1.radius = 2.80 + 0.16 * star_pulse + 0.22 * extracted
    star_glow_2.radius = 3.55 + 0.28 * star_pulse + 0.40 * strain
    star_core.color = mix_color(vector(1.0, 0.56, 0.15), vector(1.0, 0.95, 0.42), clamp(extracted * 0.55, 0, 1))
    star_glow_1.opacity = clamp(0.12 + 0.07 * extracted, 0.08, 0.32)
    star_glow_2.opacity = clamp(0.05 + 0.05 * strain, 0.035, 0.17)

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
        local_demand = city_sectors[idx]["demand"]
        item["local_demand"] = local_demand
        item["overheat"] += (clamp((local_demand - 0.64) / 0.78, 0, 1) - item["overheat"]) * 0.055
        item["dim"] += (clamp((0.35 - local_demand) / 0.32, 0, 1) - item["dim"]) * 0.045
        item["redirect"] += (clamp(unevenness * item["dim"], 0, 1) - item["redirect"]) * 0.050
        item["local_strain"] = clamp(strain * (0.60 + 0.25 * local_wave) + overload * 0.42 + item["overheat"] * 0.72, 0.0, 1.55)

        # Damage accumulates only under strong local overheating; dim rings repair faster.
        if item["local_strain"] > 0.92:
            item["health"] -= (item["local_strain"] - 0.92) * 0.006
        else:
            item["health"] += (correction_strength * 0.0025 + item["dim"] * 0.0018)
        item["health"] = clamp(item["health"], 0.42, 1.0)

        heat_color = mix_color(vector(0.08, 0.74, 1.0), vector(1.0, 0.16, 0.03), clamp(item["overheat"], 0, 1))
        dim_color = mix_color(vector(0.10, 0.45, 0.78), vector(0.62, 0.70, 0.78), clamp(item["dim"], 0, 1))
        stable_color = mix_color(vector(0.08, 0.74, 1.0), vector(0.25, 1.0, 0.72), correction_strength * item["health"] * 0.65)
        final_color = mix_color(stable_color, heat_color, clamp(item["local_strain"] * 0.72 + item["overheat"] * 0.45, 0, 1))
        final_color = mix_color(final_color, dim_color, clamp(item["dim"] * 0.75, 0, 1))

        item["ring"].color = final_color
        item["halo"].color = mix_color(final_color, vector(1.0, 1.0, 1.0), 0.20)
        item["ring"].opacity = clamp(0.30 + 0.34 * extracted + 0.22 * local_demand + 0.18 * local_wave - 0.28 * item["dim"], 0.20, 0.98)
        item["halo"].opacity = clamp(0.05 + 0.22 * item["local_strain"] + 0.18 * item["overheat"] + 0.08 * item["redirect"], 0.04, 0.52)
        # radius oscillates outward under strain, overheats with swelling, then corrects inward.
        deform = 0.08 * math.sin(time_t * 4.6 + idx) * item["local_strain"] + 0.18 * overload + 0.22 * item["overheat"] - 0.08 * item["dim"]
        item["ring"].radius = item["base_radius"] + deform
        item["halo"].radius = item["base_radius"] + 0.15 + deform * 1.25
        # Ring axis precesses slightly, showing rotation and stabilization.
        pre = 0.035 * math.sin(time_t * item["spin_speed"] * 5 + idx) * (1 + item["local_strain"])
        base_axis = item["axis"]
        item["ring"].axis = safe_norm(base_axis + vector(pre, pre * 0.6, -pre * 0.4))
        item["halo"].axis = item["ring"].axis
        item["phase"] += item["spin_speed"] * dt * (1.0 + 1.4 * demand - 0.65 * instability)

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
        lane_state = rings[p["lane"]]
        heat_t = clamp(p["u"] * 0.8 + lane_state["local_demand"] * 0.25, 0, 1)
        p["obj"].color = mix_color(vector(1.0, 0.65, 0.10), vector(0.22, 0.92, 1.0), heat_t)
        p["obj"].color = mix_color(p["obj"].color, vector(1.0, 0.14, 0.03), lane_state["overheat"] * 0.75)
        p["obj"].color = mix_color(p["obj"].color, vector(0.56, 0.66, 0.78), lane_state["dim"] * 0.65)
        if (strain > 0.74 or lane_state["overheat"] > 0.55) and random.random() < 0.035:
            p["obj"].color = vector(1.0, 0.20, 0.04)
        p["obj"].radius = clamp(0.020 + 0.052 * (0.25 + lane_state["local_demand"]) * (0.6 + 0.4 * math.sin(time_t * 6 + p["phase"])), 0.014, 0.105)

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

    # City sectors reveal uneven demand: hot districts flare; low-demand districts dim.
    for i, sector in enumerate(city_sectors):
        local = sector["demand"]
        over = rings[i]["overheat"]
        dim = rings[i]["dim"]
        sector["dome"].radius = 0.25 + 0.34 * clamp(local, 0, 1.5) + 0.05 * math.sin(time_t * 5 + sector["phase"])
        sector["dome"].color = mix_color(sector_colors[i], vector(1.0, 0.18, 0.04), over)
        sector["dome"].color = mix_color(sector["dome"].color, vector(0.60, 0.68, 0.76), dim * 0.75)
        sector["ring"].radius = 0.45 + 0.36 * clamp(local, 0, 1.5)
        sector["ring"].opacity = clamp(0.20 + 0.50 * local - 0.30 * dim, 0.08, 0.86)
        sector["ring"].color = sector["dome"].color
        sector["ring"].rotate(angle=0.025 + 0.035 * local, axis=vector(0, 1, 0), origin=sector["ring"].pos)

    # Redirect curves bend from dimmed rings toward the highest-demand city sector.
    focus_sector = city_sectors[surge_focus]
    focus_end = focus_sector["dome"].pos
    for i, c in enumerate(redirect_curves):
        item = rings[i]
        c.clear()
        c.visible = item["redirect"] > 0.05 or item["overheat"] > 0.28
        c.radius = 0.010 + 0.035 * max(item["redirect"], item["overheat"])
        c.color = mix_color(vector(0.12, 0.68, 1.0), vector(1.0, 0.30, 0.05), item["overheat"])
        if c.visible:
            u, v = orthonormal_basis(item["ring"].axis)
            start = item["ring"].pos + u * item["base_radius"] * 0.72 + v * item["base_radius"] * 0.20
            mid = vector(9.4, 0.6 * math.sin(focus_sector["angle"]), 0.6 * math.cos(focus_sector["angle"]))
            for k in range(9):
                q = k / 8
                a = start * (1 - q) + mid * q
                b = mid * (1 - q) + focus_end * q
                pt = a * (1 - q) + b * q
                pt += vector(0, math.sin(time_t * 5 + k + i) * 0.03, math.cos(time_t * 4 + k) * 0.03)
                c.append(pt)

    # Demand and strain meters.
    demand_meter = clamp(demand / 1.55, 0, 1)
    strain_meter = clamp(strain / 1.25, 0, 1)
    meter_fill.size.x = 4.2 * demand_meter
    meter_fill.pos.x = -13.6 + meter_fill.size.x / 2
    meter_fill.color = mix_color(vector(0.14, 0.78, 1.0), vector(1.0, 0.70, 0.16), demand_meter)
    strain_fill.size.x = 4.2 * strain_meter
    strain_fill.pos.x = -13.6 + strain_fill.size.x / 2
    strain_fill.color = mix_color(vector(0.16, 0.88, 0.52), vector(1.0, 0.16, 0.05), strain_meter)

    if strain < 0.45:
        mode = "stable siphon"
    elif strain < 0.78:
        mode = "rising load: rings brightening"
    elif strain < 1.02:
        mode = "strain warning: correction drones active"
    else:
        mode = "critical draw: system self-correcting"

    status.text = (
        f"DEMAND {demand:0.2f}   UNEVEN {unevenness:0.2f}   STRAIN {strain:0.2f}   "
        f"RING HEALTH {avg_health:0.2f}   ENERGY SENT {transmitted_energy:0.1f}"
    )
    mode_label.text = (
        f"{mode}  |  red rings overheat, gray rings dim/redirect  |  UP/DOWN demand  |  R reset"
    )

    # Optional slow camera drift.
    if auto_camera:
        scene.forward = vector(
            -0.55 + 0.10 * math.sin(time_t * 0.10),
            -0.28 + 0.06 * math.sin(time_t * 0.07),
            -0.78 + 0.10 * math.cos(time_t * 0.09),
        )
