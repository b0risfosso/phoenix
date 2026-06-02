"""
Defeat Refusal Engine
VPython simulation based on the seed:

A machine is knocked apart again and again, but its scattered pieces crawl back
together, rebuilding into stronger forms after every failure.

Scene:
- A central machine assembles from scattered parts.
- Periodic impact waves knock the machine apart.
- Pieces crawl, roll, and drag themselves back toward the core.
- Every rebuild makes the machine stronger: more bracing, brighter core,
  thicker armor rings, and faster recovery.
- The machine never accepts defeat; it becomes harder to break each cycle.

Controls:
- Space: pause/resume
- B: trigger breakdown
- R: reset
- Up/Down: increase/decrease impact force
- C: cycle camera

Light styling. No CSV logging.
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="Defeat Refusal Engine",
    width=1200,
    height=760,
    background=vector(0.92, 0.95, 1.0),
    center=vector(0, 0.8, 0),
    forward=vector(-0.55, -0.28, -0.78),
    range=18,
)

scene.caption = """
Defeat Refusal Engine
The machine is broken apart, crawls back together, and rebuilds stronger each time.
Space pause/resume | B break | R reset | Up/Down impact force | C camera
"""

# -----------------------------
# Colors
# -----------------------------

FLOOR = vector(0.84, 0.87, 0.82)
GRID = vector(0.62, 0.70, 0.78)
IRON = vector(0.45, 0.48, 0.52)
DARK_IRON = vector(0.25, 0.27, 0.30)
STEEL = vector(0.66, 0.70, 0.74)
CORE = vector(1.0, 0.46, 0.16)
CORE_GOLD = vector(1.0, 0.74, 0.24)
BLUE = vector(0.24, 0.50, 0.95)
GREEN = vector(0.24, 0.70, 0.40)
PURPLE = vector(0.58, 0.40, 0.90)
RED = vector(0.95, 0.22, 0.18)
TEXT = vector(0.10, 0.12, 0.16)
DUST = vector(0.62, 0.56, 0.48)

# -----------------------------
# Utility
# -----------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a + (b - a) * t


def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-7:
        return fallback
    return v / m


def rand_ground_vec(scale=1.0):
    a = random.uniform(0, 2 * math.pi)
    r = random.uniform(0.2, 1.0) * scale
    return vector(r * math.cos(a), random.uniform(-0.1, 0.35), r * math.sin(a))


def rotate_y(v, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return vector(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca)


def make_curve(points, radius, color, opacity=1.0):
    # VPython curve cannot be initialized with an empty pos list.
    return curve(pos=points, radius=radius, color=color, opacity=opacity)

# -----------------------------
# Floor and arena
# -----------------------------

floor = box(
    pos=vector(0, -3.2, 0),
    size=vector(34, 0.26, 24),
    color=FLOOR,
)

grid_lines = []
for x in range(-16, 17, 2):
    grid_lines.append(curve(pos=[vector(x, -3.04, -11), vector(x, -3.04, 11)], radius=0.008, color=GRID, opacity=0.22))
for z in range(-10, 11, 2):
    grid_lines.append(curve(pos=[vector(-16, -3.03, z), vector(16, -3.03, z)], radius=0.008, color=GRID, opacity=0.22))

arena_ring = ring(
    pos=vector(0, -2.93, 0),
    axis=vector(0, 1, 0),
    radius=7.2,
    thickness=0.035,
    color=GRID,
    opacity=0.45,
)

# Background impact pylons
for i in range(8):
    a = i * math.tau / 8
    p = vector(9.5 * math.cos(a), -2.4, 9.5 * math.sin(a))
    cylinder(pos=p, axis=vector(0, 1.1, 0), radius=0.13, color=STEEL, opacity=0.55)
    sphere(pos=p + vector(0, 1.18, 0), radius=0.22, color=BLUE, opacity=0.65, emissive=True)

# -----------------------------
# Machine part definitions
# -----------------------------

part_specs = [
    # name, shape, target local position, size/radius/axis info, base color
    ("core_shell", "box", vector(0, 0.0, 0), vector(1.4, 1.1, 1.4), STEEL),
    ("left_leg", "cyl", vector(-0.72, -1.15, -0.32), vector(0, 1.3, 0), DARK_IRON),
    ("right_leg", "cyl", vector(0.72, -1.15, -0.32), vector(0, 1.3, 0), DARK_IRON),
    ("back_leg", "cyl", vector(0, -1.15, 0.72), vector(0, 1.25, 0), DARK_IRON),
    ("front_leg", "cyl", vector(0, -1.15, -0.92), vector(0, 1.25, 0), DARK_IRON),
    ("left_arm", "box", vector(-1.28, 0.15, 0), vector(1.15, 0.24, 0.32), IRON),
    ("right_arm", "box", vector(1.28, 0.15, 0), vector(1.15, 0.24, 0.32), IRON),
    ("upper_brace", "box", vector(0, 0.75, 0), vector(2.3, 0.18, 0.28), STEEL),
    ("lower_brace", "box", vector(0, -0.68, 0), vector(2.05, 0.18, 0.28), STEEL),
    ("left_shoulder", "sphere", vector(-1.86, 0.15, 0), vector(0.32, 0, 0), BLUE),
    ("right_shoulder", "sphere", vector(1.86, 0.15, 0), vector(0.32, 0, 0), BLUE),
    ("spine", "cyl", vector(0, 0.0, 0.75), vector(0, 1.9, 0), IRON),
    ("head", "box", vector(0, 1.3, -0.05), vector(0.9, 0.55, 0.65), STEEL),
    ("left_sensor", "sphere", vector(-0.22, 1.38, -0.42), vector(0.09, 0, 0), CORE_GOLD),
    ("right_sensor", "sphere", vector(0.22, 1.38, -0.42), vector(0.09, 0, 0), CORE_GOLD),
]

machine_origin = vector(0, -1.1, 0)
parts = []
repair_lines = []
armor_objects = []
impact_waves = []
dust_clouds = []
sparks = []

class MachinePart:
    def __init__(self, spec, index):
        self.name, self.kind, self.local_target, self.dim, self.base_color = spec
        self.index = index
        self.target = machine_origin + self.local_target
        self.pos = self.target + rand_ground_vec(5.8)
        self.vel = rand_ground_vec(0.04)
        self.assembled = False
        self.crawl_phase = random.uniform(0, math.tau)
        self.strength_memory = 0.0
        self.repair_line = None

        if self.kind == "box":
            self.obj = box(pos=self.pos, size=self.dim, color=self.base_color, opacity=0.95)
        elif self.kind == "cyl":
            self.obj = cylinder(pos=self.pos - self.dim * 0.5, axis=self.dim, radius=0.12, color=self.base_color, opacity=0.95)
        elif self.kind == "sphere":
            self.obj = sphere(pos=self.pos, radius=self.dim.x, color=self.base_color, opacity=0.95, emissive=(self.base_color == CORE_GOLD))
        else:
            self.obj = sphere(pos=self.pos, radius=0.2, color=self.base_color)

        self.last_pos = vector(self.pos.x, self.pos.y, self.pos.z)
        self.trail = curve(
            pos=[self.pos, self.pos + vector(0.001, 0, 0)],
            radius=0.012,
            color=lerp(self.base_color, GREEN, 0.35),
            opacity=0.18,
        )

    def set_visual_pos(self, p):
        self.pos = vector(p.x, p.y, p.z)
        if self.kind == "cyl":
            self.obj.pos = self.pos - self.dim * 0.5
            self.obj.axis = self.dim
        else:
            self.obj.pos = self.pos

    def scatter(self, force, cycle_strength):
        outward = safe_norm(self.pos - machine_origin, rand_ground_vec(1.0))
        random_dir = safe_norm(outward + rand_ground_vec(0.8))
        throw_distance = force * random.uniform(2.0, 5.3) / (1.0 + 0.35 * cycle_strength)
        self.vel = random_dir * random.uniform(0.08, 0.18) * force
        self.set_visual_pos(self.target + random_dir * throw_distance + vector(0, random.uniform(0.3, 1.6), 0))
        self.assembled = False
        self.strength_memory = cycle_strength
        if self.repair_line:
            self.repair_line.visible = False
            self.repair_line = None

    def update(self, dt, t, phase, resilience, recovery_speed):
        self.target = machine_origin + self.local_target

        if phase == "rebuilding":
            to_target = self.target - self.pos
            d = mag(to_target)
            crawl = safe_norm(to_target) * (0.018 + 0.030 * recovery_speed + 0.008 * resilience)
            wiggle = vector(
                math.sin(t * 5.0 + self.crawl_phase) * 0.010,
                math.sin(t * 7.0 + self.crawl_phase) * 0.006,
                math.cos(t * 4.4 + self.crawl_phase) * 0.010,
            )

            if d > 0.12:
                self.vel += crawl + wiggle
                self.vel *= 0.86
                self.set_visual_pos(self.pos + self.vel)
                self.assembled = False
            else:
                self.set_visual_pos(lerp(self.pos, self.target, 0.26 + 0.08 * recovery_speed))
                self.vel *= 0.5
                self.assembled = mag(self.target - self.pos) < 0.08

            # Ground crawling look: pieces scrape near floor before lifting into place.
            if not self.assembled and self.pos.y < -2.0:
                self.pos.y = max(self.pos.y, -2.82 + 0.08 * math.sin(t * 8 + self.index))
                self.set_visual_pos(self.pos)

            # Repair line from part to target.
            if self.repair_line is None:
                self.repair_line = curve(pos=[self.pos, self.target], radius=0.012, color=GREEN, opacity=0.18)
            else:
                self.repair_line.clear()
                self.repair_line.append(pos=self.pos)
                self.repair_line.append(pos=self.target)
                self.repair_line.opacity = clamp(0.12 + 0.35 * (1.0 - min(d / 7.0, 1.0)), 0.08, 0.42)

        elif phase == "assembled":
            # Hold shape with small living vibration.
            pulse = 0.018 * math.sin(t * 3.0 + self.index)
            hold_pos = self.target + vector(0, pulse, 0)
            self.set_visual_pos(lerp(self.pos, hold_pos, 0.18))
            self.vel *= 0.6
            self.assembled = True
            if self.repair_line:
                self.repair_line.opacity *= 0.92

        elif phase == "broken":
            self.vel += vector(0, -0.002, 0)
            self.vel *= 0.982
            next_pos = self.pos + self.vel
            if next_pos.y < -2.78:
                next_pos.y = -2.78
                self.vel.y *= -0.18
                self.vel.x *= 0.92
                self.vel.z *= 0.92
            self.set_visual_pos(next_pos)
            self.assembled = False

        # Strength tint.
        strength_tint = clamp(resilience / 7.0, 0, 1)
        self.obj.color = lerp(self.base_color, CORE_GOLD, 0.18 * strength_tint)

        # Trails.
        if self.trail.npoints > 28:
            self.trail.clear()
            self.trail.append(pos=self.pos)
        self.trail.append(pos=self.pos)


class Spark:
    def __init__(self, origin, intensity=1.0):
        self.age = 0.0
        self.vel = rand_ground_vec(0.12 * intensity) + vector(0, random.uniform(0.03, 0.12) * intensity, 0)
        self.obj = sphere(
            pos=origin + rand_ground_vec(0.35),
            radius=random.uniform(0.035, 0.075) * intensity,
            color=lerp(CORE_GOLD, RED, random.random() * 0.5),
            opacity=0.8,
            emissive=True,
        )

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.vel
        self.vel += vector(0, -0.003, 0)
        self.vel *= 0.97
        fade = clamp(1 - self.age / 1.5, 0, 1)
        self.obj.opacity = 0.78 * fade
        return self.age < 1.5

    def hide(self):
        self.obj.visible = False


class ImpactWave:
    def __init__(self, force):
        self.age = 0.0
        self.force = force
        self.ring = ring(
            pos=machine_origin + vector(0, 0.15, 0),
            axis=vector(0, 1, 0),
            radius=0.4,
            thickness=0.04,
            color=RED,
            opacity=0.62,
        )

    def update(self, dt):
        self.age += dt
        fade = clamp(1 - self.age / 1.7, 0, 1)
        self.ring.radius = 0.4 + self.age * (4.5 + self.force)
        self.ring.opacity = 0.56 * fade
        self.ring.thickness = 0.02 + 0.03 * fade
        return self.age < 1.7

    def hide(self):
        self.ring.visible = False


class DustCloud:
    def __init__(self, origin, force):
        self.age = 0.0
        self.obj = ellipsoid(
            pos=origin + vector(random.uniform(-0.5, 0.5), -2.55, random.uniform(-0.5, 0.5)),
            length=random.uniform(0.8, 1.8) * force,
            height=random.uniform(0.12, 0.28),
            width=random.uniform(0.7, 1.5) * force,
            color=DUST,
            opacity=0.28,
        )
        self.drift = rand_ground_vec(0.014)

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.drift
        fade = clamp(1 - self.age / 2.4, 0, 1)
        self.obj.opacity = 0.26 * fade
        self.obj.length *= 1.006
        self.obj.width *= 1.006
        return self.age < 2.4

    def hide(self):
        self.obj.visible = False


for i, spec in enumerate(part_specs):
    parts.append(MachinePart(spec, i))

# Core light and armor
core_light = sphere(
    pos=machine_origin + vector(0, 0.04, 0),
    radius=0.36,
    color=CORE,
    emissive=True,
    opacity=0.86,
)

core_halo = sphere(
    pos=core_light.pos,
    radius=0.72,
    color=CORE_GOLD,
    opacity=0.14,
    emissive=True,
)

shield_ring = ring(
    pos=machine_origin + vector(0, 0.05, 0),
    axis=vector(0, 1, 0),
    radius=1.8,
    thickness=0.035,
    color=BLUE,
    opacity=0.18,
)

upper_shield = ring(
    pos=machine_origin + vector(0, 0.85, 0),
    axis=vector(0, 1, 0),
    radius=1.1,
    thickness=0.028,
    color=PURPLE,
    opacity=0.0,
)

# -----------------------------
# Rebuild upgrades
# -----------------------------

def create_armor_for_cycle(cycle):
    """Add visible structure after each defeat."""
    color_value = lerp(BLUE, CORE_GOLD, clamp(cycle / 7.0, 0, 1))

    if cycle == 1:
        obj = ring(pos=machine_origin + vector(0, -0.35, 0), axis=vector(0, 1, 0), radius=2.1, thickness=0.045, color=color_value, opacity=0.42)
        armor_objects.append(obj)
    elif cycle == 2:
        for x in [-1.55, 1.55]:
            obj = cylinder(pos=machine_origin + vector(x, -0.85, -0.75), axis=vector(0, 1.9, 1.45), radius=0.055, color=color_value, opacity=0.72)
            armor_objects.append(obj)
    elif cycle == 3:
        for x in [-1.55, 1.55]:
            obj = cylinder(pos=machine_origin + vector(x, -0.85, 0.75), axis=vector(0, 1.9, -1.45), radius=0.055, color=color_value, opacity=0.72)
            armor_objects.append(obj)
    elif cycle == 4:
        obj = ring(pos=machine_origin + vector(0, 0.85, 0), axis=vector(0, 1, 0), radius=1.5, thickness=0.05, color=color_value, opacity=0.50)
        armor_objects.append(obj)
    elif cycle == 5:
        for z in [-1.35, 1.35]:
            obj = box(pos=machine_origin + vector(0, 0.2, z), size=vector(2.9, 0.16, 0.12), color=color_value, opacity=0.68)
            armor_objects.append(obj)
    else:
        obj = ring(pos=machine_origin + vector(0, 0.1 + 0.12 * (cycle % 3), 0), axis=vector(1, 0.2, 0), radius=2.0 + 0.08 * cycle, thickness=0.028, color=color_value, opacity=0.34)
        armor_objects.append(obj)

# -----------------------------
# Labels and meters
# -----------------------------

title_label = label(
    pos=vector(-9.6, 7.1, -4.8),
    text="Defeat Refusal Engine",
    height=16,
    color=TEXT,
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-9.7, 6.0, -4.8),
    text="",
    height=12,
    color=TEXT,
    box=False,
    opacity=0,
)

cycle_label = label(
    pos=vector(8.0, 6.6, -4.8),
    text="",
    height=13,
    color=TEXT,
    box=False,
    opacity=0,
)

bar_back = box(
    pos=vector(8.0, 5.65, -4.8),
    size=vector(6.4, 0.20, 0.12),
    color=vector(0.72, 0.77, 0.83),
    opacity=0.60,
)

bar_fill = box(
    pos=vector(4.86, 5.65, -4.72),
    size=vector(0.08, 0.34, 0.16),
    color=GREEN,
    opacity=0.85,
)

resilience_back = box(
    pos=vector(8.0, 4.95, -4.8),
    size=vector(6.4, 0.18, 0.10),
    color=vector(0.72, 0.77, 0.83),
    opacity=0.50,
)

resilience_fill = box(
    pos=vector(4.86, 4.95, -4.72),
    size=vector(0.08, 0.30, 0.14),
    color=CORE_GOLD,
    opacity=0.85,
)

legend_piece = box(pos=vector(-9.7, 4.45, -4.8), size=vector(0.28, 0.18, 0.18), color=STEEL)
legend_signal = sphere(pos=vector(-9.7, 3.92, -4.8), radius=0.13, color=GREEN, emissive=True)
legend_armor = ring(pos=vector(-9.7, 3.38, -4.8), axis=vector(0, 1, 0), radius=0.18, thickness=0.025, color=CORE_GOLD)

label(pos=vector(-8.85, 4.45, -4.8), text="scattered pieces", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-8.85, 3.92, -4.8), text="repair signals", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-8.85, 3.38, -4.8), text="stronger rebuilds", height=10, color=TEXT, box=False, opacity=0)

# -----------------------------
# Simulation state
# -----------------------------

paused = False
camera_mode = 0
phase = "rebuilding"
cycle_count = 0
resilience = 0.0
impact_force = 1.0
phase_timer = 0.0
next_break_timer = 8.0
rebuild_completion = 0.0
sim_time = 0.0


def trigger_breakdown():
    global phase, phase_timer, cycle_count, resilience, next_break_timer
    phase = "broken"
    phase_timer = 0.0
    cycle_count += 1

    # The engine becomes stronger after every failure.
    resilience = clamp(resilience + 0.9, 0.0, 8.0)
    force_seen = impact_force

    for p in parts:
        p.scatter(force_seen, resilience)

    impact_waves.append(ImpactWave(force_seen))
    for _ in range(12):
        sparks.append(Spark(machine_origin + rand_ground_vec(0.9), intensity=1.0 + 0.15 * force_seen))
    for _ in range(6):
        dust_clouds.append(DustCloud(machine_origin, 0.8 + 0.2 * force_seen))

    create_armor_for_cycle(cycle_count)
    next_break_timer = max(4.0, 9.5 - resilience * 0.55)


def reset_simulation():
    global phase, cycle_count, resilience, impact_force, phase_timer, next_break_timer, rebuild_completion, sim_time
    phase = "rebuilding"
    cycle_count = 0
    resilience = 0.0
    impact_force = 1.0
    phase_timer = 0.0
    next_break_timer = 8.0
    rebuild_completion = 0.0
    sim_time = 0.0

    for obj in armor_objects:
        obj.visible = False
    armor_objects.clear()

    for item in impact_waves:
        item.hide()
    impact_waves.clear()

    for item in dust_clouds:
        item.hide()
    dust_clouds.clear()

    for s in sparks:
        s.hide()
    sparks.clear()

    for p in parts:
        p.set_visual_pos(p.target + rand_ground_vec(5.2))
        p.vel = rand_ground_vec(0.04)
        p.assembled = False
        p.trail.clear()
        p.trail.append(pos=p.pos)
        p.trail.append(pos=p.pos + vector(0.001, 0, 0))
        if p.repair_line:
            p.repair_line.visible = False
            p.repair_line = None


def on_keydown(evt):
    global paused, camera_mode, impact_force
    key = evt.key

    if key == " ":
        paused = not paused
    elif key in ["b", "B"]:
        trigger_breakdown()
    elif key in ["r", "R"]:
        reset_simulation()
    elif key == "up":
        impact_force = clamp(impact_force + 0.15, 0.4, 2.8)
    elif key == "down":
        impact_force = clamp(impact_force - 0.15, 0.4, 2.8)
    elif key in ["c", "C"]:
        camera_mode = (camera_mode + 1) % 3


scene.bind("keydown", on_keydown)

# -----------------------------
# Animation loop
# -----------------------------

while True:
    rate(60)

    if paused:
        continue

    dt = 1.0 / 60.0
    sim_time += dt
    phase_timer += dt

    recovery_speed = 0.75 + resilience * 0.16

    # Phase transitions.
    if phase == "broken" and phase_timer > max(0.85, 1.85 - resilience * 0.10):
        phase = "rebuilding"
        phase_timer = 0.0

    if phase == "assembled" and phase_timer > next_break_timer:
        trigger_breakdown()

    # Update parts.
    assembled_count = 0
    for p in parts:
        p.update(dt, sim_time, phase, resilience, recovery_speed)
        if p.assembled:
            assembled_count += 1

    rebuild_completion = assembled_count / len(parts)

    if phase == "rebuilding" and rebuild_completion > 0.96:
        phase = "assembled"
        phase_timer = 0.0
        for _ in range(8):
            sparks.append(Spark(machine_origin + rand_ground_vec(1.2), intensity=0.8 + 0.06 * resilience))

    # Core and shields.
    core_light.pos = machine_origin + vector(0, 0.04 + 0.05 * math.sin(sim_time * 4.0), 0)
    core_light.radius = 0.34 + 0.05 * math.sin(sim_time * 6.0) + 0.025 * resilience
    core_light.color = lerp(CORE, CORE_GOLD, clamp(resilience / 8.0, 0, 1))
    core_halo.pos = core_light.pos
    core_halo.radius = 0.65 + 0.08 * resilience + 0.07 * math.sin(sim_time * 3.0)
    core_halo.opacity = 0.10 + 0.035 * resilience

    shield_ring.pos = machine_origin + vector(0, -0.08 + 0.04 * math.sin(sim_time * 2.0), 0)
    shield_ring.radius = 1.7 + 0.11 * resilience + 0.05 * math.sin(sim_time * 2.7)
    shield_ring.opacity = 0.16 + 0.045 * resilience
    shield_ring.rotate(angle=0.025 + resilience * 0.003, axis=vector(0, 1, 0))

    upper_shield.opacity = clamp((resilience - 2.2) / 6.0, 0, 0.55)
    upper_shield.radius = 1.1 + 0.09 * resilience
    upper_shield.rotate(angle=-0.018 - resilience * 0.002, axis=vector(0, 1, 0))

    # Armor motion: each added brace becomes part of the living mechanism.
    for i, obj in enumerate(armor_objects):
        if hasattr(obj, "rotate"):
            try:
                obj.rotate(angle=0.002 + 0.001 * i, axis=vector(0, 1, 0), origin=machine_origin)
            except Exception:
                pass
        obj.opacity = min(0.78, obj.opacity + 0.002)

    # Impact wave updates.
    live_waves = []
    for w in impact_waves:
        if w.update(dt):
            live_waves.append(w)
        else:
            w.hide()
    impact_waves[:] = live_waves

    # Dust updates.
    live_dust = []
    for d in dust_clouds:
        if d.update(dt):
            live_dust.append(d)
        else:
            d.hide()
    dust_clouds[:] = live_dust

    # Spark updates.
    live_sparks = []
    for s in sparks:
        if s.update(dt):
            live_sparks.append(s)
        else:
            s.hide()
    sparks[:] = live_sparks

    # Grid pulse during repair.
    for i, line in enumerate(grid_lines):
        line.opacity = 0.14 + 0.10 * (0.5 + 0.5 * math.sin(sim_time * 0.8 + i))
        if phase == "rebuilding":
            line.opacity += 0.04 * rebuild_completion

    arena_ring.radius = 7.2 + 0.12 * math.sin(sim_time * 2.0)
    arena_ring.opacity = 0.28 + 0.18 * rebuild_completion

    # Progress meters.
    bar_fill.size.x = 6.2 * rebuild_completion
    bar_fill.pos.x = 4.9 + bar_fill.size.x / 2.0
    bar_fill.color = lerp(RED, GREEN, rebuild_completion)

    resilience_fill.size.x = 6.2 * clamp(resilience / 8.0, 0, 1)
    resilience_fill.pos.x = 4.9 + resilience_fill.size.x / 2.0

    status_label.text = (
        f"state: {phase}\n"
        "failure is absorbed into design\n"
        "pieces crawl back toward the core"
    )

    cycle_label.text = (
        f"defeats survived: {cycle_count}\n"
        f"rebuild progress: {rebuild_completion:.2f}\n"
        f"resilience: {resilience:.2f}\n"
        f"impact force: {impact_force:.2f}"
    )

    # Camera modes.
    if camera_mode == 0:
        scene.center = vector(0, 0.75, 0)
        scene.forward = vector(-0.55, -0.28, -0.78)
        scene.range = 18
    elif camera_mode == 1:
        scene.center = machine_origin + vector(0, 0.3, 0)
        scene.forward = vector(-0.20, -0.12, -0.97)
        scene.range = 7.6
    else:
        scene.center = vector(0, -1.0, 0)
        scene.forward = vector(-0.08, -0.92, -0.38)
        scene.range = 13.5
