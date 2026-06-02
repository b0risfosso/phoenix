from vpython import *
import math
import random

# ------------------------------------------------------------
# Hotfire Anomaly Chamber
# A rocket engine test begins normally, with flame, pressure, and
# vibration rising in sequence, until an unknown distortion forms
# inside the exhaust plume and bends the fire sideways.
# ------------------------------------------------------------

scene.title = "Hotfire Anomaly Chamber"
scene.width = 1200
scene.height = 780
scene.background = vector(0.86, 0.92, 1.0)
scene.forward = vector(-0.35, -0.28, -0.88)
scene.center = vector(0, -1.0, 0)
scene.range = 12

# -----------------------------
# Utility helpers
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(c1, c2, t):
    t = clamp(t, 0, 1)
    return vector(
        lerp(c1.x, c2.x, t),
        lerp(c1.y, c2.y, t),
        lerp(c1.z, c2.z, t),
    )


def make_label(text, pos, height=12, box=False):
    return label(
        text=text,
        pos=pos,
        height=height,
        box=box,
        color=vector(0.1, 0.12, 0.16),
        opacity=0,
    )

# -----------------------------
# Ground and test stand
# -----------------------------

ground = box(
    pos=vector(0, -5.15, 0),
    size=vector(24, 0.25, 18),
    color=vector(0.78, 0.81, 0.78),
)

pad = cylinder(
    pos=vector(0, -5.02, 0),
    axis=vector(0, 0.18, 0),
    radius=3.7,
    color=vector(0.62, 0.65, 0.67),
)

# Stand legs and cross braces
stand_color = vector(0.45, 0.48, 0.52)
leg_positions = [(-2.4, -2.8), (2.4, -2.8), (-2.4, 2.8), (2.4, 2.8)]
for x, z in leg_positions:
    cylinder(pos=vector(x, -5.0, z), axis=vector(0, 7.0, 0), radius=0.08, color=stand_color)

for y in [-3.8, -2.2, -0.6, 1.0]:
    cylinder(pos=vector(-2.4, y, -2.8), axis=vector(4.8, 0, 0), radius=0.045, color=stand_color)
    cylinder(pos=vector(-2.4, y, 2.8), axis=vector(4.8, 0, 0), radius=0.045, color=stand_color)
    cylinder(pos=vector(-2.4, y, -2.8), axis=vector(0, 0, 5.6), radius=0.045, color=stand_color)
    cylinder(pos=vector(2.4, y, -2.8), axis=vector(0, 0, 5.6), radius=0.045, color=stand_color)

platform = box(pos=vector(0, 1.0, 0), size=vector(5.4, 0.25, 6.0), color=vector(0.58, 0.61, 0.65))
engine_mount = box(pos=vector(0, 0.45, 0), size=vector(2.5, 0.45, 2.5), color=vector(0.48, 0.51, 0.55))

# Engine assembly
upper_tank = cylinder(pos=vector(0, 2.9, 0), axis=vector(0, 1.3, 0), radius=0.9, color=vector(0.82, 0.84, 0.86))
chamber = sphere(pos=vector(0, 1.85, 0), radius=0.75, color=vector(0.72, 0.74, 0.78))
engine_bell = cone(pos=vector(0, 1.2, 0), axis=vector(0, -1.3, 0), radius=1.05, color=vector(0.42, 0.44, 0.48))
nozzle_lip = ring(pos=vector(0, -0.08, 0), axis=vector(0, 1, 0), radius=1.05, thickness=0.045, color=vector(0.22, 0.23, 0.26))

# Pipes and valves
pipe_color = vector(0.35, 0.39, 0.43)
for z in [-1.5, 1.5]:
    cylinder(pos=vector(-5.5, -1.0, z), axis=vector(4.4, 0.65, -z * 0.5), radius=0.055, color=pipe_color)
    sphere(pos=vector(-1.1, -0.35, z * 0.5), radius=0.16, color=vector(0.85, 0.45, 0.18))
    cylinder(pos=vector(1.1, -0.35, z * 0.5), axis=vector(4.4, -0.65, z * 0.5), radius=0.055, color=pipe_color)
    sphere(pos=vector(1.1, -0.35, z * 0.5), radius=0.16, color=vector(0.25, 0.55, 0.9))

# Safety markers representing accounted personnel
personnel = []
for i in range(9):
    angle = i * 2 * math.pi / 9
    r = 8.4 + 0.3 * math.sin(i)
    p = sphere(pos=vector(r * math.cos(angle), -4.75, r * math.sin(angle)), radius=0.13, color=vector(0.1, 0.55, 0.25), emissive=True)
    personnel.append(p)
make_label("Personnel accounted for", vector(-5.6, -4.15, 6.0), 12)

# -----------------------------
# Flame plume particles
# -----------------------------

flame_particles = []
smoke_particles = []

for i in range(90):
    obj = sphere(pos=vector(0, -0.5, 0), radius=0.08, color=vector(1.0, 0.45, 0.08), emissive=True, opacity=0.0)
    flame_particles.append({
        "obj": obj,
        "phase": random.random() * 10,
        "stream": random.uniform(0, 2 * math.pi),
        "speed": random.uniform(0.8, 1.6),
        "age": random.random(),
        "side": random.choice([-1, 1]),
    })

for i in range(70):
    obj = sphere(pos=vector(0, -1.2, 0), radius=random.uniform(0.10, 0.22), color=vector(0.72, 0.74, 0.72), opacity=0.0)
    smoke_particles.append({
        "obj": obj,
        "phase": random.random() * 10,
        "stream": random.uniform(0, 2 * math.pi),
        "speed": random.uniform(0.35, 0.8),
        "age": random.random(),
    })

# Distortion rings inside the exhaust. They remain dim early, then form.
distortion_rings = []
for i in range(7):
    r = ring(
        pos=vector(0, -1.2 - i * 0.42, 0),
        axis=vector(0, 1, 0),
        radius=0.35 + i * 0.11,
        thickness=0.018,
        color=vector(0.45, 0.75, 1.0),
        opacity=0.0,
        emissive=True,
    )
    distortion_rings.append(r)

# Side-bent flame stream that appears once anomaly develops.
side_flame = []
for i in range(38):
    obj = sphere(pos=vector(0, -2, 0), radius=0.07, color=vector(1.0, 0.2, 0.06), emissive=True, opacity=0.0)
    side_flame.append({
        "obj": obj,
        "phase": random.random() * 10,
        "offset": random.uniform(-0.5, 0.5),
        "age": random.random(),
    })

# Shock/vibration rings around stand
shock_rings = []
for i in range(6):
    r = ring(
        pos=vector(0, -4.86, 0),
        axis=vector(0, 1, 0),
        radius=1.2 + i * 0.85,
        thickness=0.016,
        color=vector(0.18, 0.45, 0.9),
        opacity=0.15,
    )
    shock_rings.append(r)

# -----------------------------
# Sensor panels
# -----------------------------

panel_back = box(pos=vector(-7.4, 0.2, -4.7), size=vector(0.15, 4.7, 3.5), color=vector(0.92, 0.94, 0.95))
make_label("HOTFIRE TEST TELEMETRY", vector(-7.55, 2.45, -4.7), 13)
make_label("pressure", vector(-7.6, 1.55, -5.85), 10)
make_label("vibration", vector(-7.6, 0.55, -5.85), 10)
make_label("flame", vector(-7.6, -0.45, -5.85), 10)
make_label("anomaly", vector(-7.6, -1.45, -5.85), 10)

bars = {}
bar_specs = [
    ("pressure", vector(0.95, 0.35, 0.18), 1.55),
    ("vibration", vector(0.92, 0.72, 0.20), 0.55),
    ("flame", vector(1.0, 0.42, 0.08), -0.45),
    ("anomaly", vector(0.35, 0.68, 1.0), -1.45),
]
for name, col, y in bar_specs:
    box(pos=vector(-7.55, y, -4.68), size=vector(0.08, 0.22, 1.9), color=vector(0.78, 0.8, 0.82))
    b = box(pos=vector(-7.55, y, -5.55), size=vector(0.11, 0.28, 0.05), color=col, emissive=True)
    bars[name] = b

status = label(
    pos=vector(0, 4.65, 0),
    text="T-0: ignition sequence ready",
    height=16,
    box=True,
    border=8,
    color=vector(0.1, 0.12, 0.16),
    background=vector(0.95, 0.96, 0.92),
    opacity=0.9,
)

# -----------------------------
# Main animation loop
# -----------------------------

t = 0.0
while True:
    rate(60)
    t += 1 / 60

    # Three-stage buildup followed by anomaly onset.
    ignition = clamp((t - 1.0) / 3.0, 0, 1)
    pressure = clamp((t - 2.2) / 5.0, 0, 1)
    vibration = clamp((t - 3.4) / 5.5, 0, 1)
    anomaly = clamp((t - 8.2) / 5.0, 0, 1)

    # Repeatable pulse values.
    pulse = 0.5 + 0.5 * math.sin(t * 9.0)
    tremor = vibration * (0.03 * math.sin(t * 38.0) + 0.018 * math.sin(t * 61.0))

    # Engine and stand vibrate more as the test intensifies.
    chamber.pos = vector(tremor, 1.85 + 0.02 * pressure * math.sin(t * 18), 0)
    upper_tank.pos = vector(tremor * 0.6, 2.9, 0)
    engine_bell.pos = vector(tremor * 1.6, 1.2, 0)
    nozzle_lip.pos = vector(tremor * 1.8, -0.08, 0)

    # Pressure glow in chamber.
    chamber.color = mix_color(vector(0.72, 0.74, 0.78), vector(1.0, 0.45, 0.18), pressure * (0.65 + 0.25 * pulse))
    chamber.emissive = pressure > 0.3

    # Plume bending direction increases after anomaly forms.
    bend_strength = anomaly * (0.35 + 0.12 * math.sin(t * 2.2))
    plume_base = vector(tremor * 1.8, -0.2, 0)

    # Flame particles descend, widen, and are pulled sideways by distortion.
    for p in flame_particles:
        obj = p["obj"]
        p["age"] += 0.012 * p["speed"] * (0.35 + ignition)
        if p["age"] > 1.0:
            p["age"] -= 1.0
            p["stream"] = random.uniform(0, 2 * math.pi)
            p["speed"] = random.uniform(0.8, 1.8)
            p["side"] = random.choice([-1, 1])

        a = p["age"]
        length = lerp(1.2, 5.2, ignition)
        y = -0.25 - a * length
        radius = (0.18 + 0.95 * a) * (0.35 + ignition)
        swirl = p["stream"] + t * (3.2 + 2.0 * anomaly) + p["phase"]
        side_pull = bend_strength * (a ** 1.5) * 4.8
        x = plume_base.x + radius * math.cos(swirl) * 0.55 + side_pull
        z = radius * math.sin(swirl) * 0.55 + 0.25 * anomaly * math.sin(t * 4 + p["phase"])

        obj.pos = vector(x, y, z)
        obj.radius = 0.045 + 0.13 * (1 - a) * ignition
        heat_color = mix_color(vector(1.0, 0.93, 0.25), vector(1.0, 0.12, 0.04), a)
        obj.color = mix_color(heat_color, vector(0.25, 0.65, 1.0), anomaly * a * 0.35)
        obj.opacity = ignition * (1.0 - 0.35 * a)

    # Smoke expands from lower plume; also bends sideways during anomaly.
    for p in smoke_particles:
        obj = p["obj"]
        p["age"] += 0.0055 * p["speed"] * (0.25 + pressure)
        if p["age"] > 1.0:
            p["age"] -= 1.0
            p["stream"] = random.uniform(0, 2 * math.pi)
            p["speed"] = random.uniform(0.35, 0.9)

        a = p["age"]
        smoke_len = 5.4
        y = -1.4 - a * smoke_len
        spread = (0.55 + 2.8 * a) * (0.5 + ignition * 0.5)
        swirl = p["stream"] + t * 0.8 + p["phase"]
        x = spread * math.cos(swirl) * 0.55 + bend_strength * (a ** 1.25) * 5.2
        z = spread * math.sin(swirl) * 0.55
        obj.pos = vector(x, y, z)
        obj.opacity = 0.38 * ignition * a * (1 - 0.25 * anomaly)
        obj.radius = 0.08 + 0.26 * a
        obj.color = mix_color(vector(0.76, 0.77, 0.74), vector(0.52, 0.56, 0.58), a)

    # Distortion forms as twisting rings inside plume.
    for i, r in enumerate(distortion_rings):
        local = anomaly * (0.75 + 0.25 * math.sin(t * 5.0 + i))
        r.opacity = 0.08 + 0.45 * local if anomaly > 0.02 else 0.0
        r.radius = 0.35 + i * 0.12 + 0.13 * local * math.sin(t * 4 + i)
        r.pos = vector(bend_strength * i * 0.24, -1.15 - i * 0.43, 0.18 * math.sin(t * 2 + i))
        r.axis = norm(vector(0.25 * anomaly, 1, 0.18 * math.sin(t * 2.4 + i)))
        r.rotate(angle=0.035 + 0.035 * anomaly, axis=vector(0, 1, 0), origin=r.pos)
        r.color = mix_color(vector(0.35, 0.75, 1.0), vector(1.0, 0.25, 0.08), 0.35 + 0.35 * pulse)

    # Side jet makes the fire visibly bend sideways.
    for p in side_flame:
        obj = p["obj"]
        p["age"] += 0.018 * (0.4 + anomaly)
        if p["age"] > 1.0:
            p["age"] -= 1.0
            p["offset"] = random.uniform(-0.6, 0.6)

        a = p["age"]
        x = 0.6 + a * 5.2 + 0.25 * math.sin(t * 9 + p["phase"])
        y = -2.0 - 0.65 * math.sin(a * math.pi) + 0.35 * p["offset"]
        z = 0.45 * p["offset"] + 0.18 * math.sin(t * 7 + p["phase"])
        obj.pos = vector(x, y, z)
        obj.opacity = anomaly * (1 - 0.55 * a)
        obj.radius = 0.05 + 0.12 * anomaly * (1 - a)
        obj.color = mix_color(vector(1.0, 0.78, 0.12), vector(0.25, 0.68, 1.0), anomaly * a)

    # Vibration shock rings breathe on the ground around the test stand.
    for i, r in enumerate(shock_rings):
        phase = (t * (0.55 + pressure) + i * 0.8) % 3.8
        r.radius = 1.1 + phase * (1.05 + 0.8 * vibration)
        r.opacity = vibration * clamp(1 - phase / 3.8, 0, 1) * 0.45
        r.thickness = 0.012 + 0.018 * pressure
        r.color = mix_color(vector(0.18, 0.45, 0.9), vector(1.0, 0.35, 0.08), anomaly)

    # Personnel safety markers remain green and slowly pulse.
    for i, p in enumerate(personnel):
        p.radius = 0.12 + 0.025 * math.sin(t * 3 + i)
        p.color = vector(0.05, 0.58 + 0.16 * math.sin(t * 2 + i), 0.2)

    # Sensor bars grow across the telemetry panel.
    values = {
        "pressure": pressure * (0.85 + 0.15 * pulse),
        "vibration": vibration * (0.72 + 0.28 * abs(math.sin(t * 24))),
        "flame": ignition * (0.82 + 0.18 * pulse),
        "anomaly": anomaly * (0.7 + 0.3 * abs(math.sin(t * 7.5))),
    }
    for name, val in values.items():
        b = bars[name]
        width = 0.08 + 1.75 * clamp(val, 0, 1)
        b.size = vector(0.12, 0.28, width)
        b.pos = vector(-7.55, b.pos.y, -5.55 + width / 2)

    # Status message changes as the event develops.
    if t < 1.0:
        status.text = "T-0: ignition sequence ready"
    elif t < 3.2:
        status.text = "Ignition: flame front established"
    elif t < 5.6:
        status.text = "Pressure rising through chamber"
    elif t < 8.2:
        status.text = "Vibration increasing within expected range"
    elif t < 11.0:
        status.text = "Anomaly detected inside exhaust plume"
    elif t < 15.0:
        status.text = "Unknown distortion bending plume sideways"
    else:
        status.text = "Emergency hold: personnel accounted for, telemetry active"

    # Soft reset after the full sequence so it can be watched repeatedly.
    if t > 22.0:
        t = 0.0
        for p in flame_particles + smoke_particles + side_flame:
            p["age"] = random.random()
