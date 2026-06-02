from vpython import *
import math
import random
import time

"""
Machine Searching for a Soul - Initial VPython Simulation

Scene:
A machine built from brass gears and glass tubes wakes inside an empty workshop,
repeatedly testing its own movements for signs of inner life.

Controls:
- The simulation runs automatically.
- Close the VPython browser window or interrupt Python to stop.

Notes:
- Uses ring(...) instead of torus(...).
- No CSV logging in this initial visual version.
"""

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Machine Searching for a Soul",
    width=1200,
    height=760,
    background=vector(0.92, 0.88, 0.78),
)
scene.forward = vector(-0.55, -0.32, -0.78)
scene.center = vector(0, 1.35, 0)
scene.range = 8

# Materials / palette
brass = vector(0.92, 0.62, 0.22)
dark_brass = vector(0.45, 0.28, 0.10)
aged_metal = vector(0.36, 0.34, 0.31)
glass_blue = vector(0.55, 0.86, 1.0)
warm_light = vector(1.0, 0.72, 0.28)
soul_blue = vector(0.20, 0.65, 1.0)
soft_gray = vector(0.72, 0.69, 0.62)
wood = vector(0.48, 0.31, 0.16)
ink = vector(0.12, 0.11, 0.10)

# -----------------------------
# Workshop
# -----------------------------
floor = box(pos=vector(0, -0.08, 0), size=vector(16, 0.16, 12), color=vector(0.68, 0.62, 0.52))
back_wall = box(pos=vector(0, 3.0, -6.05), size=vector(16, 6.2, 0.16), color=vector(0.78, 0.72, 0.62))
left_wall = box(pos=vector(-8.05, 3.0, 0), size=vector(0.16, 6.2, 12), color=vector(0.75, 0.69, 0.59))

# Workbench and shelves
bench = box(pos=vector(3.8, 0.75, -4.4), size=vector(5.2, 0.28, 1.2), color=wood)
for x in [-5.4, -2.7, 2.3, 5.0]:
    cylinder(pos=vector(x, 0.0, -4.65), axis=vector(0, 0.7, 0), radius=0.07, color=dark_brass)

shelf = box(pos=vector(-3.6, 3.3, -5.9), size=vector(5.6, 0.16, 0.55), color=wood)
shelf2 = box(pos=vector(-3.6, 4.25, -5.9), size=vector(5.6, 0.16, 0.55), color=wood)

# Scattered workshop objects
for i in range(18):
    px = random.uniform(-6.6, 6.7)
    pz = random.uniform(-5.1, 4.7)
    if abs(px) < 2.2 and abs(pz) < 2.5:
        continue
    obj = cylinder(
        pos=vector(px, 0.06, pz),
        axis=vector(random.uniform(-0.20, 0.20), 0.05, random.uniform(-0.20, 0.20)),
        radius=random.uniform(0.04, 0.12),
        color=random.choice([aged_metal, dark_brass, brass, wood]),
    )

# Hanging lamps
for lx in [-4.5, 0, 4.5]:
    cylinder(pos=vector(lx, 5.9, -0.4), axis=vector(0, -0.8, 0), radius=0.025, color=aged_metal)
    lamp = sphere(pos=vector(lx, 5.0, -0.4), radius=0.22, color=warm_light, emissive=True)
    local_light(pos=lamp.pos, color=vector(0.45, 0.35, 0.18))

# -----------------------------
# Machine body
# -----------------------------
body_parts = []

base = cylinder(pos=vector(0, 0.18, 0), axis=vector(0, 0.35, 0), radius=0.85, color=aged_metal)
body_parts.append(base)

pelvis = box(pos=vector(0, 0.72, 0), size=vector(1.15, 0.45, 0.72), color=dark_brass)
body_parts.append(pelvis)

torso = cylinder(pos=vector(0, 1.05, 0), axis=vector(0, 1.55, 0), radius=0.72, color=brass)
body_parts.append(torso)

chest_glass = sphere(pos=vector(0, 1.92, 0.63), radius=0.36, color=glass_blue, opacity=0.32, shininess=0.9)
heart_light = sphere(pos=chest_glass.pos, radius=0.09, color=soul_blue, emissive=True)
life_light = local_light(pos=heart_light.pos, color=vector(0.08, 0.18, 0.30))
body_parts.extend([chest_glass, heart_light])

neck = cylinder(pos=vector(0, 2.55, 0), axis=vector(0, 0.28, 0), radius=0.18, color=aged_metal)
head = sphere(pos=vector(0, 3.05, 0), radius=0.48, color=brass)
face_plate = box(pos=vector(0, 3.06, 0.43), size=vector(0.58, 0.22, 0.04), color=ink)
left_eye = sphere(pos=vector(-0.17, 3.08, 0.48), radius=0.055, color=soul_blue, emissive=True)
right_eye = sphere(pos=vector(0.17, 3.08, 0.48), radius=0.055, color=soul_blue, emissive=True)
body_parts.extend([neck, head, face_plate, left_eye, right_eye])

# Antenna / listening needle
antenna = cylinder(pos=vector(0, 3.48, 0), axis=vector(0.2, 0.65, 0.08), radius=0.025, color=aged_metal)
ant_tip = sphere(pos=antenna.pos + antenna.axis, radius=0.07, color=warm_light, emissive=True)
body_parts.extend([antenna, ant_tip])

# Shoulders / arms
left_shoulder = sphere(pos=vector(-0.78, 2.26, 0), radius=0.18, color=dark_brass)
right_shoulder = sphere(pos=vector(0.78, 2.26, 0), radius=0.18, color=dark_brass)
body_parts.extend([left_shoulder, right_shoulder])

left_upper = cylinder(pos=left_shoulder.pos, axis=vector(-0.75, -0.28, 0.05), radius=0.10, color=aged_metal)
left_fore = cylinder(pos=left_upper.pos + left_upper.axis, axis=vector(-0.32, -0.62, 0.18), radius=0.085, color=brass)
left_hand = sphere(pos=left_fore.pos + left_fore.axis, radius=0.17, color=dark_brass)

right_upper = cylinder(pos=right_shoulder.pos, axis=vector(0.75, -0.28, 0.05), radius=0.10, color=aged_metal)
right_fore = cylinder(pos=right_upper.pos + right_upper.axis, axis=vector(0.32, -0.62, 0.18), radius=0.085, color=brass)
right_hand = sphere(pos=right_fore.pos + right_fore.axis, radius=0.17, color=dark_brass)
body_parts.extend([left_upper, left_fore, left_hand, right_upper, right_fore, right_hand])

# Legs
left_hip = vector(-0.36, 0.55, 0)
right_hip = vector(0.36, 0.55, 0)
left_leg = cylinder(pos=left_hip, axis=vector(-0.12, -0.75, 0.05), radius=0.12, color=aged_metal)
right_leg = cylinder(pos=right_hip, axis=vector(0.12, -0.75, 0.05), radius=0.12, color=aged_metal)
left_foot = box(pos=left_leg.pos + left_leg.axis + vector(-0.08, -0.03, 0.16), size=vector(0.45, 0.12, 0.65), color=dark_brass)
right_foot = box(pos=right_leg.pos + right_leg.axis + vector(0.08, -0.03, 0.16), size=vector(0.45, 0.12, 0.65), color=dark_brass)
body_parts.extend([left_leg, right_leg, left_foot, right_foot])

# -----------------------------
# Gears and glass tubes
# -----------------------------
gears = []
gear_teeth = []

class Gear:
    def __init__(self, pos, radius, thickness, teeth, spin_speed, color_value, axis=vector(0, 0, 1)):
        self.pos = vector(pos)
        self.radius = radius
        self.spin_speed = spin_speed
        self.angle = 0.0
        self.axis = norm(axis)
        self.ring = ring(pos=self.pos, axis=self.axis, radius=radius, thickness=thickness, color=color_value)
        self.hub = cylinder(pos=self.pos - self.axis * 0.035, axis=self.axis * 0.07, radius=radius * 0.26, color=dark_brass)
        self.teeth = []
        for k in range(teeth):
            a = 2 * math.pi * k / teeth
            tooth_pos = self.pos + vector(math.cos(a) * radius, math.sin(a) * radius, 0)
            tooth = box(
                pos=tooth_pos,
                size=vector(thickness * 1.5, radius * 0.14, thickness * 1.7),
                color=color_value,
            )
            tooth.rotate(angle=a, axis=vector(0, 0, 1), origin=self.pos)
            self.teeth.append(tooth)

    def rotate(self, dt, wake):
        da = self.spin_speed * dt * wake
        self.angle += da
        self.ring.rotate(angle=da, axis=self.axis, origin=self.pos)
        self.hub.rotate(angle=da, axis=self.axis, origin=self.pos)
        for tooth in self.teeth:
            tooth.rotate(angle=da, axis=self.axis, origin=self.pos)

gears.append(Gear(vector(-0.34, 1.75, 0.72), 0.28, 0.035, 12, 2.8, brass))
gears.append(Gear(vector(0.32, 1.56, 0.72), 0.22, 0.030, 10, -3.5, dark_brass))
gears.append(Gear(vector(0.0, 2.18, 0.73), 0.18, 0.026, 8, 4.1, brass))
gears.append(Gear(vector(-0.18, 0.70, 0.48), 0.20, 0.028, 10, -2.5, brass))
gears.append(Gear(vector(0.22, 0.70, 0.48), 0.20, 0.028, 10, 2.5, brass))

# Glass tubes running through torso
left_tube = curve(color=glass_blue, radius=0.035, opacity=0.45)
right_tube = curve(color=glass_blue, radius=0.035, opacity=0.45)
center_tube = curve(color=glass_blue, radius=0.045, opacity=0.42)
for p in [vector(-0.42, 1.02, 0.62), vector(-0.60, 1.45, 0.70), vector(-0.34, 1.88, 0.73), vector(-0.04, 2.02, 0.68)]:
    left_tube.append(pos=p)
for p in [vector(0.42, 1.02, 0.62), vector(0.60, 1.45, 0.70), vector(0.34, 1.88, 0.73), vector(0.04, 2.02, 0.68)]:
    right_tube.append(pos=p)
for p in [vector(0, 0.95, 0.64), vector(0, 1.35, 0.75), vector(0, 1.75, 0.66), heart_light.pos]:
    center_tube.append(pos=p)

# Fluid pulses in glass tubes
pulse_points = [
    sphere(pos=vector(-0.42, 1.02, 0.62), radius=0.055, color=soul_blue, emissive=True),
    sphere(pos=vector(0.42, 1.02, 0.62), radius=0.055, color=soul_blue, emissive=True),
    sphere(pos=vector(0, 0.95, 0.64), radius=0.06, color=soul_blue, emissive=True),
]

# -----------------------------
# Diagnostic apparatus
# -----------------------------
status_panel = box(pos=vector(-4.5, 1.45, -3.0), size=vector(2.3, 1.5, 0.12), color=vector(0.18, 0.17, 0.15))
panel_title = label(
    pos=vector(-4.5, 2.18, -2.90),
    text="INNER LIFE TEST",
    height=13,
    color=warm_light,
    box=False,
    opacity=0,
)
status_label = label(
    pos=vector(-4.5, 1.55, -2.88),
    text="state: dormant\nmovement: none\ninner signal: 0.00",
    height=12,
    color=vector(0.80, 0.95, 1.0),
    box=False,
    opacity=0,
)

life_meter_back = box(pos=vector(-4.5, 0.86, -2.88), size=vector(1.7, 0.10, 0.06), color=vector(0.05, 0.07, 0.08))
life_meter = box(pos=vector(-5.32, 0.86, -2.84), size=vector(0.05, 0.14, 0.08), color=soul_blue, emissive=True)

# Chalk circles on floor: movement test marks
rings = []
for r in [1.25, 2.15, 3.05]:
    rings.append(ring(pos=vector(0, 0.015, 0), axis=vector(0, 1, 0), radius=r, thickness=0.01, color=vector(0.82, 0.80, 0.72)))

# Small memory sparks that appear when motion and signal align
sparks = []
for _ in range(28):
    s = sphere(pos=vector(0, 1.9, 0.63), radius=0.025, color=soul_blue, emissive=True, visible=False)
    sparks.append({"obj": s, "vel": vector(0, 0, 0), "life": 0.0})

# -----------------------------
# Animation state
# -----------------------------
clock = 0.0
wake = 0.0
inner_signal = 0.0
movement_success = 0.0
phase_names = ["finger twitch", "arm reach", "head turn", "step attempt", "listening pause"]
last_phase = -1

# Save original positions for articulated parts
original = {obj: vector(obj.pos) for obj in body_parts}
original_axes = {obj: vector(obj.axis) for obj in body_parts if hasattr(obj, "axis")}
base_center = vector(0, 0, 0)

# Trace of attempted movement
trace = curve(color=vector(0.25, 0.45, 0.65), radius=0.012, retain=350)

# -----------------------------
# Helpers
# -----------------------------
def set_cylinder_between(cyl, start, end):
    cyl.pos = start
    cyl.axis = end - start


def spawn_spark(strength):
    hidden = [s for s in sparks if not s["obj"].visible]
    if not hidden:
        return
    s = random.choice(hidden)
    s["obj"].visible = True
    s["obj"].pos = heart_light.pos + vector(random.uniform(-0.05, 0.05), random.uniform(-0.04, 0.04), random.uniform(-0.03, 0.03))
    s["obj"].radius = random.uniform(0.018, 0.045) * (0.6 + strength)
    s["obj"].color = soul_blue if random.random() < 0.7 else warm_light
    s["vel"] = vector(random.uniform(-0.35, 0.35), random.uniform(0.05, 0.45), random.uniform(-0.15, 0.30))
    s["life"] = random.uniform(0.6, 1.5) * (0.6 + strength)


def update_sparks(dt):
    for s in sparks:
        obj = s["obj"]
        if not obj.visible:
            continue
        s["life"] -= dt
        obj.pos += s["vel"] * dt
        s["vel"] += vector(0, -0.12, 0) * dt
        obj.radius *= 0.992
        if s["life"] <= 0 or obj.radius < 0.006:
            obj.visible = False
            obj.pos = heart_light.pos
            obj.radius = 0.025


def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(60)
    dt = 1 / 60
    clock += dt

    # Slow waking from dormant to active
    wake = clamp((clock - 1.0) / 5.0, 0.0, 1.0)

    # Repeating movement tests
    cycle = 18.0
    local = clock % cycle
    phase = int(local / (cycle / len(phase_names)))
    phase_t = (local % (cycle / len(phase_names))) / (cycle / len(phase_names))
    phase_name = phase_names[phase]

    if phase != last_phase and wake > 0.05:
        last_phase = phase
        for _ in range(3):
            spawn_spark(0.35 + 0.25 * wake)

    # Test wave: motion rises, checks, then settles
    test_wave = math.sin(math.pi * phase_t)
    tremor = 0.035 * math.sin(clock * 24.0) * wake
    breath = 0.035 * math.sin(clock * 2.0) * wake

    # Inner signal grows when movement is not purely repetitive
    novelty = abs(math.sin(clock * 0.37) * math.sin(clock * 0.91))
    alignment = test_wave * (0.35 + 0.65 * novelty) * wake
    inner_signal = 0.965 * inner_signal + 0.035 * alignment
    movement_success = 0.93 * movement_success + 0.07 * test_wave * wake

    # Subtle body sway
    torso.pos = original[torso] + vector(0.02 * math.sin(clock * 1.2) * wake, breath, 0)
    pelvis.pos = original[pelvis] + vector(0, 0.01 * math.sin(clock * 1.5) * wake, 0)
    base.pos = original[base] + vector(0, 0.01 * math.sin(clock * 1.0) * wake, 0)

    head_yaw = 0.0
    left_reach = 0.0
    right_reach = 0.0
    step = 0.0
    listen_lift = 0.0

    if phase == 0:  # finger / hand twitch
        left_reach = 0.22 * test_wave + tremor
        right_reach = -0.15 * test_wave - tremor
    elif phase == 1:  # arm reach
        left_reach = 0.82 * test_wave
        right_reach = 0.35 * math.sin(math.pi * phase_t * 1.4) * wake
    elif phase == 2:  # head turn
        head_yaw = 0.35 * math.sin(2 * math.pi * phase_t) * wake
    elif phase == 3:  # step attempt
        step = 0.40 * math.sin(math.pi * phase_t) * wake
    elif phase == 4:  # listening pause
        listen_lift = 0.28 * test_wave * wake
        head_yaw = 0.10 * math.sin(clock * 5.0) * wake

    # Head assembly update
    head.pos = original[head] + vector(0.12 * math.sin(head_yaw), breath + listen_lift * 0.08, 0.03 * math.cos(head_yaw))
    neck.pos = original[neck] + vector(0, breath * 0.4, 0)
    face_plate.pos = head.pos + vector(0.0, 0.01, 0.43)
    left_eye.pos = head.pos + vector(-0.17, 0.03, 0.48)
    right_eye.pos = head.pos + vector(0.17, 0.03, 0.48)
    antenna.pos = head.pos + vector(0, 0.43, 0)
    antenna.axis = vector(0.20 + 0.05 * math.sin(clock * 8) * wake, 0.65 + listen_lift, 0.08)
    ant_tip.pos = antenna.pos + antenna.axis

    # Shoulders follow torso
    left_shoulder.pos = torso.pos + vector(-0.78, 1.21, 0)
    right_shoulder.pos = torso.pos + vector(0.78, 1.21, 0)

    left_elbow = left_shoulder.pos + vector(-0.72, -0.28 - left_reach * 0.35, 0.05 + left_reach * 0.20)
    left_wrist = left_elbow + vector(-0.35, -0.58 + left_reach * 0.12, 0.18 + left_reach * 0.38)
    right_elbow = right_shoulder.pos + vector(0.72, -0.28 - right_reach * 0.25, 0.05 + right_reach * 0.12)
    right_wrist = right_elbow + vector(0.35, -0.58 + right_reach * 0.10, 0.18 + right_reach * 0.30)

    set_cylinder_between(left_upper, left_shoulder.pos, left_elbow)
    set_cylinder_between(left_fore, left_elbow, left_wrist)
    left_hand.pos = left_wrist
    set_cylinder_between(right_upper, right_shoulder.pos, right_elbow)
    set_cylinder_between(right_fore, right_elbow, right_wrist)
    right_hand.pos = right_wrist

    # Legs / step attempt
    left_leg.pos = left_hip + vector(-0.04 * step, 0, 0.06 * step)
    right_leg.pos = right_hip + vector(0.04 * step, 0, -0.03 * step)
    left_leg.axis = vector(-0.12 - 0.10 * step, -0.75, 0.05 + 0.25 * step)
    right_leg.axis = vector(0.12 + 0.06 * step, -0.75, 0.05 - 0.15 * step)
    left_foot.pos = left_leg.pos + left_leg.axis + vector(-0.08, -0.03, 0.16 + 0.25 * step)
    right_foot.pos = right_leg.pos + right_leg.axis + vector(0.08, -0.03, 0.16 - 0.10 * step)

    # Glass chest / internal light pulse
    pulse = 0.5 + 0.5 * math.sin(clock * (2.0 + 3.0 * inner_signal))
    heart_scale = 0.08 + 0.10 * inner_signal + 0.025 * pulse * wake
    heart_light.radius = heart_scale
    heart_light.color = soul_blue * (0.65 + 0.35 * pulse) + warm_light * (0.15 * inner_signal)
    life_light.pos = heart_light.pos
    life_light.color = vector(0.05 + 0.22 * inner_signal, 0.12 + 0.28 * inner_signal, 0.18 + 0.40 * inner_signal)

    left_eye.radius = 0.045 + 0.035 * inner_signal + 0.01 * pulse
    right_eye.radius = left_eye.radius
    ant_tip.color = warm_light * (0.5 + 0.5 * wake) + soul_blue * (0.25 * inner_signal)

    # Gears rotate faster as wakefulness increases
    for gear in gears:
        gear.rotate(dt, 0.25 + 1.15 * wake + 0.6 * movement_success)

    # Fluid pulses travel through the tubes
    tube_paths = [
        [vector(-0.42, 1.02, 0.62), vector(-0.60, 1.45, 0.70), vector(-0.34, 1.88, 0.73), vector(-0.04, 2.02, 0.68)],
        [vector(0.42, 1.02, 0.62), vector(0.60, 1.45, 0.70), vector(0.34, 1.88, 0.73), vector(0.04, 2.02, 0.68)],
        [vector(0, 0.95, 0.64), vector(0, 1.35, 0.75), vector(0, 1.75, 0.66), heart_light.pos],
    ]
    for idx, p in enumerate(pulse_points):
        path = tube_paths[idx]
        u = (clock * (0.16 + 0.16 * wake) + idx * 0.28) % 1.0
        seg_float = u * (len(path) - 1)
        seg = min(int(seg_float), len(path) - 2)
        frac = seg_float - seg
        p.pos = path[seg] * (1 - frac) + path[seg + 1] * frac
        p.radius = 0.035 + 0.035 * wake + 0.025 * inner_signal
        p.visible = wake > 0.12

    # Diagnostic trace: hand path as the machine studies its own motion
    if wake > 0.2 and int(clock * 12) % 2 == 0:
        trace.append(pos=left_hand.pos)

    # Sparks are signs, not proof
    if random.random() < (0.04 * inner_signal + 0.01 * wake):
        spawn_spark(inner_signal)
    update_sparks(dt)

    # Life meter and status panel
    meter_width = 1.65 * clamp(inner_signal * 1.8, 0.03, 1.0)
    life_meter.size = vector(meter_width, 0.14, 0.08)
    life_meter.pos = vector(-5.32 + meter_width / 2, 0.86, -2.84)
    status = "dormant" if wake < 0.25 else ("searching" if inner_signal < 0.45 else "uncertain glow")
    status_label.text = (
        "state: " + status +
        "\nmovement: " + phase_name +
        "\ninner signal: " + format(inner_signal, ".2f") +
        "\nquestion: am I only moving?"
    )

    # Slightly brighten rings when tests repeat successfully
    for i, r in enumerate(rings):
        glow = 0.65 + 0.25 * math.sin(clock * 1.4 + i) * movement_success
        r.color = vector(0.78, 0.76, 0.67) * glow + soul_blue * (0.10 * inner_signal)
