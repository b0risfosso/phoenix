"""
Shockwave Sculptor
VPython simulation inspired by NASA's X-59 quiet supersonic aircraft.

Scene:
- A long-nosed X-59-like aircraft flies across a light sky.
- Its shaped body creates several smaller shockwave packets instead of one large boom.
- Wave arcs drift downward toward ground sensors as quiet thumps.
- Flight-condition markers show speed, altitude, and evaluation zones.

Controls:
- Space: pause/resume
- R: reset
- Up/Down: increase/decrease speed
- Left/Right: change angle of attack
- C: cycle camera view

This script uses VPython primitives only and avoids torus/curve empty initialization issues.
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="Shockwave Sculptor — X-59 Quiet Supersonic Flight",
    width=1200,
    height=760,
    background=vector(0.83, 0.93, 1.0),
    center=vector(0, 1.8, 0),
    forward=vector(-0.62, -0.18, -0.76),
    range=26,
)

scene.caption = """
Shockwave Sculptor
The long-nosed aircraft divides one harsh boom into many smaller pressure waves.
Space pause/resume | R reset | Up/Down speed | Left/Right angle | C camera
"""

# Colors
SKY_BLUE = vector(0.83, 0.93, 1.0)
GROUND_GREEN = vector(0.56, 0.74, 0.47)
GROUND_DARK = vector(0.38, 0.58, 0.34)
AIRCRAFT_WHITE = vector(0.94, 0.96, 0.98)
AIRCRAFT_BLUE = vector(0.15, 0.32, 0.68)
AIRCRAFT_ORANGE = vector(1.0, 0.53, 0.18)
WAVE_BLUE = vector(0.20, 0.55, 1.0)
WAVE_SOFT = vector(0.63, 0.82, 1.0)
SENSOR_GREEN = vector(0.15, 0.62, 0.30)
TEXT_DARK = vector(0.12, 0.16, 0.20)
GUIDE = vector(0.73, 0.83, 0.92)
EVAL_PURPLE = vector(0.62, 0.44, 0.94)

# -----------------------------
# Utility functions
# -----------------------------

def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def rotate_y(v, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return vector(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca)


def rotate_z(v, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return vector(v.x * ca - v.y * sa, v.x * sa + v.y * ca, v.z)


def make_arc_points(center_pos, radius, spread, steps, direction, vertical_drop=0.0):
    """Make a curved shockwave arc behind the aircraft.

    Every curve is created with real point data, never an empty list.
    """
    pts = []
    half = spread * 0.5
    for i in range(steps):
        u = -half + spread * (i / max(1, steps - 1))
        x = center_pos.x - direction * radius * math.cos(u)
        y = center_pos.y + radius * math.sin(u) - vertical_drop
        z = center_pos.z + 0.12 * radius * math.sin(2 * u)
        pts.append(vector(x, y, z))
    return pts


# -----------------------------
# World objects
# -----------------------------

ground = box(
    pos=vector(0, -6.2, 0),
    size=vector(72, 0.24, 32),
    color=GROUND_GREEN,
)

# subtle terrain bands
for i in range(10):
    x = -34 + i * 7.5
    box(
        pos=vector(x, -6.05, -7.2 + 0.5 * math.sin(i)),
        size=vector(4.5, 0.04, 0.12),
        color=GROUND_DARK,
        opacity=0.45,
    )

# cloud wisps
for i in range(18):
    cx = random.uniform(-34, 34)
    cy = random.uniform(5.8, 10.0)
    cz = random.uniform(-9.0, 7.0)
    ellipsoid(
        pos=vector(cx, cy, cz),
        length=random.uniform(2.0, 4.8),
        height=random.uniform(0.22, 0.45),
        width=random.uniform(0.5, 1.3),
        color=vector(1, 1, 1),
        opacity=0.35,
    )

# evaluation corridor markers
corridor_lines = []
for z in [-4.0, 4.0]:
    line = curve(
        pos=[vector(-34, 1.8, z), vector(34, 1.8, z)],
        radius=0.025,
        color=GUIDE,
        opacity=0.52,
    )
    corridor_lines.append(line)

for x in range(-30, 31, 10):
    ring(
        pos=vector(x, 1.8, 0),
        axis=vector(1, 0, 0),
        radius=4.0,
        thickness=0.035,
        color=EVAL_PURPLE,
        opacity=0.18,
    )

# ground sensor stations
sensors = []
sensor_labels = []
for x in [-24, -14, -4, 6, 16, 26]:
    base = cylinder(
        pos=vector(x, -5.95, 4.7),
        axis=vector(0, 0.45, 0),
        radius=0.32,
        color=SENSOR_GREEN,
    )
    dish = sphere(
        pos=vector(x, -5.42, 4.7),
        radius=0.42,
        color=vector(0.72, 0.92, 0.76),
        opacity=0.78,
    )
    pulse = ring(
        pos=vector(x, -5.37, 4.7),
        axis=vector(0, 1, 0),
        radius=0.55,
        thickness=0.025,
        color=SENSOR_GREEN,
        opacity=0.18,
    )
    label_obj = label(
        pos=vector(x, -4.55, 4.7),
        text="quiet",
        height=10,
        box=False,
        color=TEXT_DARK,
        opacity=0,
    )
    sensors.append({"base": base, "dish": dish, "pulse": pulse, "amp": 0.0})
    sensor_labels.append(label_obj)


# -----------------------------
# Aircraft model
# -----------------------------

aircraft_parts = []


def add_part(obj):
    aircraft_parts.append(obj)
    return obj


class X59Aircraft:
    def __init__(self):
        self.base_pos = vector(-25, 2.4, 0)
        self.pos = vector(self.base_pos.x, self.base_pos.y, self.base_pos.z)
        self.speed = 1.06
        self.angle = 0.0
        self.bank = 0.0
        self.phase = 0.0
        self.direction = vector(1, 0, 0)
        self.parts = []

        # Long nose and body aligned along x-axis.
        self.nose = add_part(cone(
            pos=self.pos + vector(-4.6, 0, 0),
            axis=vector(4.4, 0, 0),
            radius=0.34,
            color=AIRCRAFT_WHITE,
        ))
        self.body = add_part(cylinder(
            pos=self.pos + vector(-0.35, 0, 0),
            axis=vector(4.9, 0, 0),
            radius=0.48,
            color=AIRCRAFT_WHITE,
        ))
        self.tail = add_part(cone(
            pos=self.pos + vector(4.45, 0, 0),
            axis=vector(1.0, 0, 0),
            radius=0.48,
            color=AIRCRAFT_BLUE,
        ))
        self.canopy = add_part(ellipsoid(
            pos=self.pos + vector(-0.45, 0.36, 0),
            length=1.05,
            height=0.34,
            width=0.46,
            color=vector(0.27, 0.47, 0.82),
            opacity=0.82,
        ))
        self.left_wing = add_part(box(
            pos=self.pos + vector(1.2, -0.04, -1.05),
            size=vector(2.2, 0.08, 2.25),
            color=vector(0.90, 0.93, 0.96),
        ))
        self.right_wing = add_part(box(
            pos=self.pos + vector(1.2, -0.04, 1.05),
            size=vector(2.2, 0.08, 2.25),
            color=vector(0.90, 0.93, 0.96),
        ))
        self.tail_fin = add_part(box(
            pos=self.pos + vector(4.45, 0.62, 0),
            size=vector(0.55, 1.15, 0.08),
            color=AIRCRAFT_BLUE,
        ))
        self.left_stabilizer = add_part(box(
            pos=self.pos + vector(4.35, 0.02, -0.72),
            size=vector(0.9, 0.06, 1.1),
            color=AIRCRAFT_BLUE,
        ))
        self.right_stabilizer = add_part(box(
            pos=self.pos + vector(4.35, 0.02, 0.72),
            size=vector(0.9, 0.06, 1.1),
            color=AIRCRAFT_BLUE,
        ))
        self.engine_glow = add_part(sphere(
            pos=self.pos + vector(5.15, 0, 0),
            radius=0.28,
            color=AIRCRAFT_ORANGE,
            emissive=True,
            opacity=0.75,
        ))

        self.parts = list(aircraft_parts)

        self.trail = curve(
            pos=[self.pos + vector(4.8, 0, 0), self.pos + vector(5.4, 0, 0)],
            radius=0.035,
            color=AIRCRAFT_ORANGE,
            opacity=0.38,
        )

    def local_to_world(self, local):
        v = rotate_z(local, self.angle)
        v = rotate_y(v, self.bank)
        return self.pos + v

    def update_part(self, obj, local_pos, axis=None):
        obj.pos = self.local_to_world(local_pos)
        if axis is not None:
            a = rotate_z(axis, self.angle)
            a = rotate_y(a, self.bank)
            obj.axis = a

    def update(self, dt, t):
        self.phase += dt
        self.pos.x += self.speed * dt * 3.2
        self.pos.y = 2.35 + 0.24 * math.sin(t * 0.62)
        self.bank = 0.025 * math.sin(t * 0.8)

        if self.pos.x > 35:
            self.pos.x = -35

        # Reposition parts.
        self.update_part(self.nose, vector(-4.6, 0, 0), vector(4.4, 0, 0))
        self.update_part(self.body, vector(-0.35, 0, 0), vector(4.9, 0, 0))
        self.update_part(self.tail, vector(4.45, 0, 0), vector(1.0, 0, 0))
        self.update_part(self.canopy, vector(-0.45, 0.36, 0))
        self.update_part(self.left_wing, vector(1.2, -0.04, -1.05))
        self.update_part(self.right_wing, vector(1.2, -0.04, 1.05))
        self.update_part(self.tail_fin, vector(4.45, 0.62, 0))
        self.update_part(self.left_stabilizer, vector(4.35, 0.02, -0.72))
        self.update_part(self.right_stabilizer, vector(4.35, 0.02, 0.72))
        self.update_part(self.engine_glow, vector(5.15, 0, 0))

        # Angle visible on wings/fin through small rotations.
        self.left_wing.rotate(angle=0.0, axis=vector(0, 1, 0))
        self.right_wing.rotate(angle=0.0, axis=vector(0, 1, 0))

        self.engine_glow.radius = 0.24 + 0.08 * abs(math.sin(t * 7.0)) + 0.04 * (self.speed - 1.0)

        # Trail append only; reset periodically to avoid large memory use.
        if self.trail.npoints > 80:
            self.trail.clear()
            self.trail.append(pos=self.local_to_world(vector(4.8, 0, 0)))
        self.trail.append(pos=self.local_to_world(vector(5.4, 0, 0)))


aircraft = X59Aircraft()

# -----------------------------
# Shockwave system
# -----------------------------

shockwaves = []
thump_marks = []

class ShockwavePacket:
    def __init__(self, origin, packet_index, speed_value, angle_value):
        self.origin = vector(origin.x, origin.y, origin.z)
        self.age = 0.0
        self.packet_index = packet_index
        self.speed_value = speed_value
        self.angle_value = angle_value

        # Multiple shaped waves: nose, canopy, wing, tail.
        self.delay = packet_index * 0.13
        self.radius = 0.55 + packet_index * 0.2
        self.down = 0.0
        self.amplitude = max(0.12, 0.46 - packet_index * 0.065)
        self.spread = math.radians(60 + packet_index * 5)
        self.side_offset = (packet_index - 2.5) * 0.18

        pts = make_arc_points(
            self.origin + vector(-0.5 * packet_index, 0, self.side_offset),
            self.radius,
            self.spread,
            22,
            direction=1,
            vertical_drop=0.0,
        )
        self.body = curve(
            pos=pts,
            radius=0.026 + 0.006 * self.amplitude,
            color=lerp(WAVE_BLUE, WAVE_SOFT, packet_index / 6.0),
            opacity=0.68,
        )

        self.dot = sphere(
            pos=self.origin + vector(-self.radius, 0, self.side_offset),
            radius=0.06,
            color=WAVE_BLUE,
            emissive=True,
            opacity=0.55,
        )

    def update(self, dt):
        self.age += dt
        active_age = max(0.0, self.age - self.delay)
        expand = 1.0 + active_age * (1.4 + 0.12 * self.packet_index)
        self.down = active_age * (1.22 + 0.05 * self.packet_index)
        wobble = 0.16 * math.sin(active_age * 5.0 + self.packet_index)

        current_radius = self.radius * expand
        center = self.origin + vector(
            -0.55 * self.packet_index - active_age * 1.75,
            0.06 * wobble,
            self.side_offset + 0.15 * math.sin(active_age * 2 + self.packet_index),
        )

        pts = make_arc_points(
            center,
            current_radius,
            self.spread,
            22,
            direction=1,
            vertical_drop=self.down,
        )
        self.body.clear()
        for p in pts:
            self.body.append(pos=p)

        fade = clamp(1.0 - active_age / 6.8, 0.0, 1.0)
        softness = smoothstep(active_age / 4.8)
        self.body.opacity = 0.55 * fade
        self.body.radius = 0.018 + 0.020 * fade * self.amplitude
        self.body.color = lerp(WAVE_BLUE, WAVE_SOFT, softness)

        self.dot.pos = pts[len(pts) // 2]
        self.dot.opacity = 0.38 * fade
        self.dot.radius = 0.04 + 0.04 * fade

        # When wave reaches sensor height, create a quiet thump marker.
        if self.dot.pos.y < -4.8 and not hasattr(self, "hit_ground"):
            self.hit_ground = True
            make_quiet_thump(self.dot.pos, self.amplitude)

        return active_age < 7.2

    def hide(self):
        self.body.visible = False
        self.dot.visible = False


def make_quiet_thump(pos, amplitude):
    thump = ring(
        pos=vector(pos.x, -5.38, pos.z),
        axis=vector(0, 1, 0),
        radius=0.25,
        thickness=0.025,
        color=lerp(SENSOR_GREEN, WAVE_SOFT, 0.42),
        opacity=0.45,
    )
    label_obj = label(
        pos=vector(pos.x, -4.25, pos.z),
        text="soft thump",
        height=11,
        box=False,
        color=TEXT_DARK,
        opacity=0,
    )
    thump_marks.append({"ring": thump, "label": label_obj, "age": 0.0, "amp": amplitude})


def emit_shockwave_burst():
    # Split the boom into a sequence of smaller waves generated along the shaped aircraft.
    local_sources = [
        vector(-4.7, 0.0, 0),
        vector(-2.7, 0.05, 0),
        vector(-0.4, 0.18, 0),
        vector(1.4, -0.04, 0),
        vector(3.2, 0.0, 0),
        vector(4.7, 0.0, 0),
    ]
    for idx, local in enumerate(local_sources):
        shockwaves.append(
            ShockwavePacket(
                aircraft.local_to_world(local),
                idx,
                aircraft.speed,
                aircraft.angle,
            )
        )


# -----------------------------
# UI labels and meters
# -----------------------------

status = label(
    pos=vector(-23, 9.2, -5.5),
    text="",
    height=14,
    box=False,
    color=TEXT_DARK,
    opacity=0,
)

mach_label = label(
    pos=vector(17, 8.7, -5.5),
    text="",
    height=14,
    box=False,
    color=TEXT_DARK,
    opacity=0,
)

quiet_meter_back = box(pos=vector(17, 7.95, -5.5), size=vector(6.2, 0.22, 0.12), color=vector(0.90, 0.92, 0.94))
quiet_meter = box(pos=vector(14.0, 7.95, -5.42), size=vector(0.2, 0.32, 0.16), color=vector(0.21, 0.68, 0.42))

condition_markers = []
for i, name in enumerate(["low lift", "cruise", "turn", "descent", "trim"]):
    marker = sphere(
        pos=vector(-18 + i * 5.0, 6.7, -5.5),
        radius=0.22,
        color=EVAL_PURPLE,
        opacity=0.55,
    )
    txt = label(
        pos=marker.pos + vector(0, 0.55, 0),
        text=name,
        height=9,
        box=False,
        color=TEXT_DARK,
        opacity=0,
    )
    condition_markers.append((marker, txt))


# -----------------------------
# Controls
# -----------------------------

paused = False
camera_mode = 0

def reset_simulation():
    global shockwaves, thump_marks, t, last_emit
    for sw in shockwaves:
        sw.hide()
    shockwaves = []

    for mark in thump_marks:
        mark["ring"].visible = False
        mark["label"].visible = False
    thump_marks = []

    aircraft.pos = vector(-25, 2.4, 0)
    aircraft.speed = 1.06
    aircraft.angle = 0.0
    aircraft.trail.clear()
    aircraft.trail.append(pos=aircraft.local_to_world(vector(4.8, 0, 0)))
    aircraft.trail.append(pos=aircraft.local_to_world(vector(5.4, 0, 0)))
    t = 0.0
    last_emit = -10.0


def on_keydown(evt):
    global paused, camera_mode
    key = evt.key

    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_simulation()
    elif key == "up":
        aircraft.speed = clamp(aircraft.speed + 0.04, 0.78, 1.34)
    elif key == "down":
        aircraft.speed = clamp(aircraft.speed - 0.04, 0.78, 1.34)
    elif key == "left":
        aircraft.angle = clamp(aircraft.angle + 0.018, -0.16, 0.16)
    elif key == "right":
        aircraft.angle = clamp(aircraft.angle - 0.018, -0.16, 0.16)
    elif key in ["c", "C"]:
        camera_mode = (camera_mode + 1) % 3


scene.bind("keydown", on_keydown)


# -----------------------------
# Animation loop
# -----------------------------

t = 0.0
last_emit = -10.0

while True:
    rate(60)
    if paused:
        continue

    dt = 1.0 / 60.0
    t += dt

    aircraft.update(dt, t)

    # Automatic flight condition changes.
    aircraft.angle += 0.0009 * math.sin(t * 0.41)
    aircraft.angle = clamp(aircraft.angle, -0.16, 0.16)
    aircraft.speed += 0.0015 * math.sin(t * 0.29)
    aircraft.speed = clamp(aircraft.speed, 0.82, 1.32)

    # Emit bursts more often at higher speed.
    emit_interval = lerp(2.35, 1.25, clamp((aircraft.speed - 0.78) / 0.56, 0, 1))
    if t - last_emit > emit_interval:
        emit_shockwave_burst()
        last_emit = t

    # Update shockwaves.
    alive = []
    for sw in shockwaves:
        if sw.update(dt):
            alive.append(sw)
        else:
            sw.hide()
    shockwaves = alive

    # Update quiet thump rings.
    live_marks = []
    for mark in thump_marks:
        mark["age"] += dt
        age = mark["age"]
        fade = clamp(1.0 - age / 2.8, 0.0, 1.0)
        mark["ring"].radius = 0.25 + age * (1.05 + mark["amp"])
        mark["ring"].opacity = 0.32 * fade
        mark["ring"].thickness = 0.02 + 0.01 * fade
        mark["label"].opacity = 0
        if age < 2.8:
            live_marks.append(mark)
        else:
            mark["ring"].visible = False
            mark["label"].visible = False
    thump_marks = live_marks

    # Sensors respond to nearby thumps/waves.
    for idx, sensor in enumerate(sensors):
        sensor["amp"] *= 0.92
        sx = sensor["base"].pos.x
        for mark in thump_marks:
            dist = abs(mark["ring"].pos.x - sx)
            if dist < 3.2:
                sensor["amp"] = max(sensor["amp"], (1.0 - dist / 3.2) * mark["amp"])
        amp = sensor["amp"]
        sensor["dish"].radius = 0.42 + 0.16 * amp
        sensor["pulse"].radius = 0.55 + 0.55 * amp + 0.08 * math.sin(t * 6 + idx)
        sensor["pulse"].opacity = 0.10 + 0.35 * amp
        sensor_labels[idx].text = "quiet" if amp < 0.34 else "thump"

    # Condition markers pulse one at a time.
    active_condition = int((t * 0.45) % len(condition_markers))
    for i, (marker, txt) in enumerate(condition_markers):
        if i == active_condition:
            marker.radius = 0.28 + 0.04 * math.sin(t * 6)
            marker.opacity = 0.82
        else:
            marker.radius = 0.20
            marker.opacity = 0.36

    # Quiet-meter: more split waves = lower boom intensity.
    wave_count_factor = clamp(len(shockwaves) / 24.0, 0, 1)
    speed_factor = clamp((aircraft.speed - 0.78) / 0.56, 0, 1)
    quiet_score = clamp(0.84 - 0.22 * speed_factor + 0.18 * wave_count_factor, 0.25, 0.96)
    quiet_meter.size.x = 6.0 * quiet_score
    quiet_meter.pos.x = 14.0 + quiet_meter.size.x / 2.0

    status.text = (
        "X-59 shaped flight test model\n"
        "single boom split into smaller waves\n"
        "downward drift becomes soft ground thumps"
    )
    mach_label.text = (
        f"Mach model: {aircraft.speed:.2f}\n"
        f"angle trim: {math.degrees(aircraft.angle):+.1f}°\n"
        f"quiet score: {quiet_score:.2f}"
    )

    # Camera modes.
    if camera_mode == 0:
        scene.center = vector(aircraft.pos.x + 2, 1.2, 0)
        scene.forward = vector(-0.62, -0.18, -0.76)
        scene.range = 22
    elif camera_mode == 1:
        scene.center = aircraft.pos + vector(0, -1.5, 0)
        scene.forward = vector(-0.94, -0.12, -0.20)
        scene.range = 12
    else:
        scene.center = vector(0, -1.2, 0)
        scene.forward = vector(-0.1, -0.75, -0.65)
        scene.range = 33
