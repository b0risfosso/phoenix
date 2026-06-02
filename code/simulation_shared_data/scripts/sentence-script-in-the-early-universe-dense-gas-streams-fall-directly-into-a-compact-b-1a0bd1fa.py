"""
Cosmic Dawn Feeding Core
VPython simulation based on the seed:

In the early universe, dense gas streams fall directly into a compact black hole,
allowing it to grow rapidly before a large galaxy can assemble.

Scene:
- A compact central black hole with a glowing accretion region.
- Dense cosmic gas streams fall inward from different directions.
- The black hole grows visibly as direct feeding continues.
- A faint host galaxy tries to assemble slowly around it.
- Early-universe background uses light styling rather than a dark scene.

Controls:
- Space: pause/resume
- R: reset simulation
- Up/Down: increase/decrease gas inflow strength
- G: toggle forming galaxy visibility
- C: cycle camera mode
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="Cosmic Dawn Feeding Core",
    width=1200,
    height=760,
    background=vector(0.86, 0.91, 1.0),
    center=vector(0, 0, 0),
    forward=vector(-0.45, -0.25, -0.86),
    range=20,
)

scene.caption = """
Cosmic Dawn Feeding Core
Dense gas streams feed a compact black hole before a large host galaxy forms.
Space pause/resume | R reset | Up/Down inflow | G galaxy | C camera
"""

# -----------------------------
# Colors
# -----------------------------

BG = vector(0.86, 0.91, 1.0)
GAS_BLUE = vector(0.30, 0.58, 1.0)
GAS_CYAN = vector(0.36, 0.86, 0.96)
GAS_GOLD = vector(1.0, 0.68, 0.22)
CORE_DARK = vector(0.03, 0.025, 0.035)
ACCRETION_ORANGE = vector(1.0, 0.46, 0.12)
ACCRETION_GOLD = vector(1.0, 0.78, 0.25)
GALAXY_LAVENDER = vector(0.62, 0.55, 0.92)
HALO_BLUE = vector(0.54, 0.73, 1.0)
TEXT = vector(0.10, 0.13, 0.18)
STREAM_GUIDE = vector(0.55, 0.72, 0.95)

# -----------------------------
# Utility
# -----------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)


def rand_unit():
    theta = random.uniform(0, 2 * math.pi)
    z = random.uniform(-0.45, 0.45)
    r = math.sqrt(max(0.0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))


def rotate_y(v, a):
    ca = math.cos(a)
    sa = math.sin(a)
    return vector(v.x * ca + v.z * sa, v.y, -v.x * sa + v.z * ca)


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-6:
        return fallback
    return v / m


def make_curve(points, radius, color, opacity=1.0):
    # VPython curve must receive non-empty position data.
    return curve(pos=points, radius=radius, color=color, opacity=opacity)

# -----------------------------
# Background cosmic dawn field
# -----------------------------

stars = []
for i in range(170):
    d = random.uniform(18, 46)
    direction = rand_unit()
    p = direction * d
    s = sphere(
        pos=p,
        radius=random.uniform(0.035, 0.11),
        color=lerp(vector(1, 1, 1), vector(0.78, 0.86, 1.0), random.random()),
        opacity=random.uniform(0.35, 0.8),
        emissive=True,
    )
    stars.append(s)

# Pale early-universe gas fog sheets
fog_layers = []
for i in range(10):
    p = vector(random.uniform(-18, 18), random.uniform(-6, 8), random.uniform(-14, 14))
    layer = ellipsoid(
        pos=p,
        length=random.uniform(7, 15),
        height=random.uniform(0.18, 0.42),
        width=random.uniform(2.2, 5.5),
        color=lerp(HALO_BLUE, GALAXY_LAVENDER, random.random()),
        opacity=0.08,
    )
    fog_layers.append(layer)

# -----------------------------
# Black hole and host assembly
# -----------------------------

black_hole = sphere(
    pos=vector(0, 0, 0),
    radius=0.78,
    color=CORE_DARK,
    emissive=False,
)

event_horizon_glow = sphere(
    pos=vector(0, 0, 0),
    radius=1.02,
    color=vector(0.1, 0.1, 0.16),
    opacity=0.20,
    emissive=True,
)

accretion_ring_1 = ring(
    pos=vector(0, 0, 0),
    axis=vector(0.18, 1, 0.12),
    radius=1.42,
    thickness=0.07,
    color=ACCRETION_ORANGE,
    opacity=0.82,
)

accretion_ring_2 = ring(
    pos=vector(0, 0, 0),
    axis=vector(-0.25, 1, 0.2),
    radius=1.78,
    thickness=0.045,
    color=ACCRETION_GOLD,
    opacity=0.46,
)

hot_inner_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0.08, 1, -0.2),
    radius=1.08,
    thickness=0.035,
    color=vector(1.0, 0.92, 0.48),
    opacity=0.70,
)

# Forming galaxy disk appears slower and smaller than the feeding core.
galaxy_objects = []
galaxy_visible = True

for i in range(55):
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(3.2, 8.6)
    y = random.uniform(-0.18, 0.18)
    p = vector(r * math.cos(angle), y, r * math.sin(angle))
    arm_bias = 0.28 * math.sin(2 * angle + r * 0.45)
    p.y += arm_bias * 0.18
    star = sphere(
        pos=p,
        radius=random.uniform(0.035, 0.09),
        color=lerp(GALAXY_LAVENDER, vector(1.0, 0.9, 0.58), random.random() * 0.45),
        opacity=0.28,
        emissive=True,
    )
    galaxy_objects.append(star)

galaxy_halo = ellipsoid(
    pos=vector(0, 0, 0),
    length=14.5,
    height=1.4,
    width=14.5,
    color=GALAXY_LAVENDER,
    opacity=0.055,
)
galaxy_objects.append(galaxy_halo)

dark_matter_halo = sphere(
    pos=vector(0, 0, 0),
    radius=9.8,
    color=HALO_BLUE,
    opacity=0.035,
)
galaxy_objects.append(dark_matter_halo)

# -----------------------------
# Feeding stream system
# -----------------------------

stream_anchors = [
    vector(-15, 4.2, -8),
    vector(14, 3.8, -7),
    vector(-12, -2.6, 10),
    vector(11, 5.6, 8),
    vector(-5, 7.4, 13),
    vector(6, -4.5, -13),
]

streams = []
gas_particles = []
impact_flashes = []


class GasStream:
    def __init__(self, anchor, index):
        self.anchor = vector(anchor.x, anchor.y, anchor.z)
        self.index = index
        self.phase = random.uniform(0, 2 * math.pi)
        self.active = True

        pts = []
        for j in range(28):
            u = j / 27.0
            bend = vector(
                math.sin(u * math.pi + self.phase) * 1.2,
                math.sin(u * 2.4 + self.phase) * 0.5,
                math.cos(u * math.pi + self.phase) * 1.0,
            )
            pts.append(self.anchor * (1 - u) + bend * math.sin(u * math.pi) + vector(0, 0, 0) * u)

        self.line = make_curve(
            pts,
            radius=0.045,
            color=lerp(GAS_BLUE, GAS_CYAN, index / max(1, len(stream_anchors) - 1)),
            opacity=0.42,
        )

        self.guide = make_curve(
            [self.anchor, vector(0, 0, 0)],
            radius=0.012,
            color=STREAM_GUIDE,
            opacity=0.18,
        )

    def update(self, t, inflow_strength):
        pts = []
        for j in range(28):
            u = j / 27.0
            swirl = 1.15 + 0.45 * math.sin(t * 0.7 + self.index)
            bend = vector(
                math.sin(u * math.pi * 1.3 + self.phase + t * 0.35) * swirl,
                math.sin(u * 2.7 + self.phase + t * 0.25) * 0.58,
                math.cos(u * math.pi * 1.2 + self.phase - t * 0.28) * swirl,
            )
            pinch = math.sin(u * math.pi)
            p = self.anchor * (1 - u) + bend * pinch * (1.0 - 0.28 * u)
            pts.append(p)

        self.line.clear()
        for p in pts:
            self.line.append(pos=p)

        self.line.radius = 0.035 + 0.04 * inflow_strength + 0.009 * math.sin(t * 4 + self.index)
        self.line.opacity = 0.28 + 0.34 * inflow_strength
        self.line.color = lerp(GAS_BLUE, GAS_GOLD, 0.35 + 0.25 * math.sin(t * 0.6 + self.index))


class GasParticle:
    def __init__(self, stream):
        self.stream = stream
        self.u = random.uniform(0.0, 0.3)
        self.speed = random.uniform(0.16, 0.34)
        self.phase = random.uniform(0, 2 * math.pi)
        self.mass = random.uniform(0.6, 1.4)
        self.obj = sphere(
            pos=stream.anchor,
            radius=random.uniform(0.07, 0.15),
            color=lerp(GAS_CYAN, GAS_GOLD, random.random()),
            opacity=0.72,
            emissive=True,
        )
        self.trail = curve(
            pos=[stream.anchor, stream.anchor * 0.995],
            radius=0.016,
            color=self.obj.color,
            opacity=0.22,
        )

    def stream_position(self, u, t):
        anchor = self.stream.anchor
        swirl_amp = 1.4 * (1.0 - 0.35 * u)
        bend = vector(
            math.sin(u * math.pi * 2.1 + self.phase + t * 0.9) * swirl_amp,
            math.sin(u * 4.0 + self.phase + t * 0.45) * 0.7,
            math.cos(u * math.pi * 1.7 + self.phase - t * 0.6) * swirl_amp,
        )
        pinch = math.sin(u * math.pi)
        return anchor * (1 - u) + bend * pinch

    def update(self, dt, t, inflow_strength):
        self.u += dt * self.speed * (0.75 + 1.6 * inflow_strength) * (1 + self.u * 1.7)

        if self.u >= 1.0:
            create_impact_flash(self.obj.pos, self.mass)
            self.reset()
            return self.mass

        p = self.stream_position(self.u, t)
        self.obj.pos = p

        # Brighten and shrink as it nears the event horizon.
        closeness = smoothstep(self.u)
        self.obj.radius = (0.08 + 0.09 * self.mass) * (1.0 - 0.35 * closeness)
        self.obj.color = lerp(GAS_CYAN, ACCRETION_GOLD, closeness)
        self.obj.opacity = 0.52 + 0.42 * closeness

        if self.trail.npoints > 28:
            self.trail.clear()
            self.trail.append(pos=p)
        self.trail.append(pos=p)
        return 0.0

    def reset(self):
        self.u = random.uniform(0.0, 0.18)
        self.speed = random.uniform(0.16, 0.34)
        self.mass = random.uniform(0.6, 1.4)
        self.obj.pos = self.stream.anchor
        self.trail.clear()
        self.trail.append(pos=self.stream.anchor)
        self.trail.append(pos=self.stream.anchor * 0.995)


def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def create_impact_flash(pos, mass_value):
    flash = sphere(
        pos=safe_norm(pos) * 1.15,
        radius=0.15 + 0.09 * mass_value,
        color=ACCRETION_GOLD,
        opacity=0.65,
        emissive=True,
    )
    ripple = ring(
        pos=vector(0, 0, 0),
        axis=safe_norm(pos, vector(0, 1, 0)),
        radius=1.18,
        thickness=0.025,
        color=ACCRETION_GOLD,
        opacity=0.58,
    )
    impact_flashes.append({"flash": flash, "ripple": ripple, "age": 0.0, "mass": mass_value})


for i, anchor in enumerate(stream_anchors):
    streams.append(GasStream(anchor, i))

for s in streams:
    for _ in range(9):
        gas_particles.append(GasParticle(s))

# -----------------------------
# Labels and progress displays
# -----------------------------

title_label = label(
    pos=vector(-10.8, 9.4, -5.5),
    text="Cosmic Dawn Feeding Core",
    height=16,
    color=TEXT,
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-11.2, 8.3, -5.5),
    text="",
    height=12,
    color=TEXT,
    box=False,
    opacity=0,
)

mass_label = label(
    pos=vector(8.8, 8.6, -5.5),
    text="",
    height=13,
    color=TEXT,
    box=False,
    opacity=0,
)

bar_back = box(
    pos=vector(8.8, 7.65, -5.5),
    size=vector(6.8, 0.22, 0.12),
    color=vector(0.72, 0.78, 0.86),
    opacity=0.75,
)

bar_fill = box(
    pos=vector(5.45, 7.65, -5.42),
    size=vector(0.1, 0.34, 0.16),
    color=ACCRETION_ORANGE,
    opacity=0.88,
)

galaxy_bar_back = box(
    pos=vector(8.8, 6.95, -5.5),
    size=vector(6.8, 0.18, 0.10),
    color=vector(0.72, 0.78, 0.86),
    opacity=0.55,
)

galaxy_bar_fill = box(
    pos=vector(5.45, 6.95, -5.42),
    size=vector(0.1, 0.28, 0.14),
    color=GALAXY_LAVENDER,
    opacity=0.72,
)

legend_core = sphere(pos=vector(-11.6, 6.9, -5.5), radius=0.16, color=ACCRETION_ORANGE, emissive=True)
legend_galaxy = sphere(pos=vector(-11.6, 6.25, -5.5), radius=0.16, color=GALAXY_LAVENDER, emissive=True, opacity=0.7)
legend_stream = sphere(pos=vector(-11.6, 5.6, -5.5), radius=0.16, color=GAS_CYAN, emissive=True)

label(pos=vector(-10.7, 6.9, -5.5), text="black hole growth", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-10.7, 6.25, -5.5), text="slow host assembly", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-10.7, 5.6, -5.5), text="direct gas streams", height=10, color=TEXT, box=False, opacity=0)

# -----------------------------
# Simulation state and controls
# -----------------------------

paused = False
camera_mode = 0
inflow_strength = 0.72
black_hole_mass = 1.0
galaxy_assembly = 0.10
time_elapsed = 0.0


def set_galaxy_visibility(visible):
    for obj in galaxy_objects:
        obj.visible = visible


def reset_simulation():
    global black_hole_mass, galaxy_assembly, inflow_strength, time_elapsed
    black_hole_mass = 1.0
    galaxy_assembly = 0.10
    inflow_strength = 0.72
    time_elapsed = 0.0

    for p in gas_particles:
        p.reset()

    for item in impact_flashes:
        item["flash"].visible = False
        item["ripple"].visible = False
    impact_flashes.clear()

    black_hole.radius = 0.78
    event_horizon_glow.radius = 1.02
    accretion_ring_1.radius = 1.42
    accretion_ring_2.radius = 1.78
    hot_inner_ring.radius = 1.08


def on_keydown(evt):
    global paused, inflow_strength, galaxy_visible, camera_mode
    key = evt.key

    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_simulation()
    elif key == "up":
        inflow_strength = clamp(inflow_strength + 0.08, 0.12, 1.35)
    elif key == "down":
        inflow_strength = clamp(inflow_strength - 0.08, 0.12, 1.35)
    elif key in ["g", "G"]:
        galaxy_visible = not galaxy_visible
        set_galaxy_visibility(galaxy_visible)
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
    time_elapsed += dt

    # Update gas streams.
    for s in streams:
        s.update(time_elapsed, inflow_strength)

    # Particle infall and black hole growth.
    accreted_mass = 0.0
    for p in gas_particles:
        accreted_mass += p.update(dt, time_elapsed, inflow_strength)

    black_hole_mass += accreted_mass * 0.0048 * inflow_strength
    black_hole_mass = clamp(black_hole_mass, 1.0, 4.2)

    # Galaxy assembly rises slowly, emphasizing core growth before host growth.
    galaxy_assembly += dt * 0.0065 * (0.45 + 0.22 * math.sin(time_elapsed * 0.2))
    galaxy_assembly = clamp(galaxy_assembly, 0.10, 1.0)

    # Update core sizes.
    growth = (black_hole_mass - 1.0) / 3.2
    black_hole.radius = 0.78 + 0.58 * growth
    event_horizon_glow.radius = black_hole.radius + 0.28 + 0.12 * math.sin(time_elapsed * 3.0)
    event_horizon_glow.opacity = 0.16 + 0.10 * growth

    accretion_ring_1.radius = 1.42 + 0.62 * growth + 0.05 * math.sin(time_elapsed * 5.0)
    accretion_ring_2.radius = 1.78 + 0.75 * growth + 0.04 * math.sin(time_elapsed * 3.7)
    hot_inner_ring.radius = 1.08 + 0.35 * growth + 0.03 * math.sin(time_elapsed * 7.2)

    accretion_ring_1.rotate(angle=0.028 + 0.020 * inflow_strength, axis=accretion_ring_1.axis)
    accretion_ring_2.rotate(angle=-0.018 - 0.012 * inflow_strength, axis=accretion_ring_2.axis)
    hot_inner_ring.rotate(angle=0.045 + 0.025 * inflow_strength, axis=hot_inner_ring.axis)

    accretion_ring_1.opacity = 0.58 + 0.28 * inflow_strength
    accretion_ring_2.opacity = 0.34 + 0.22 * inflow_strength
    hot_inner_ring.opacity = 0.52 + 0.26 * inflow_strength

    # Update galaxy stars slowly: faint orbital assembly.
    for i, obj in enumerate(galaxy_objects):
        if obj is galaxy_halo or obj is dark_matter_halo:
            continue

        angle = 0.0015 * (1 + galaxy_assembly) * (1 if i % 2 == 0 else -0.6)
        obj.pos = rotate_y(obj.pos, angle)
        obj.opacity = 0.12 + 0.45 * galaxy_assembly * (0.5 + 0.5 * math.sin(time_elapsed * 0.3 + i))

    galaxy_halo.opacity = 0.035 + 0.08 * galaxy_assembly
    dark_matter_halo.opacity = 0.025 + 0.035 * galaxy_assembly

    # Impact flash updates.
    live_flashes = []
    for item in impact_flashes:
        item["age"] += dt
        age = item["age"]
        fade = clamp(1.0 - age / 1.45, 0.0, 1.0)
        item["flash"].radius = 0.14 + item["mass"] * 0.12 + age * 0.55
        item["flash"].opacity = 0.62 * fade
        item["ripple"].radius = 1.1 + age * 1.55
        item["ripple"].opacity = 0.48 * fade
        item["ripple"].thickness = 0.022 + 0.018 * fade
        if age < 1.45:
            live_flashes.append(item)
        else:
            item["flash"].visible = False
            item["ripple"].visible = False
    impact_flashes[:] = live_flashes

    # Fog and background motion.
    for i, layer in enumerate(fog_layers):
        layer.pos.x += 0.003 * math.sin(time_elapsed * 0.12 + i)
        layer.pos.z += 0.002 * math.cos(time_elapsed * 0.10 + i)

    for i, s in enumerate(stars):
        if i % 7 == 0:
            s.opacity = 0.35 + 0.45 * (0.5 + 0.5 * math.sin(time_elapsed * 0.9 + i))

    # Progress bars.
    core_fill = clamp(growth, 0.0, 1.0)
    gal_fill = clamp(galaxy_assembly, 0.0, 1.0)

    bar_fill.size.x = 6.6 * core_fill
    bar_fill.pos.x = 5.5 + bar_fill.size.x / 2.0

    galaxy_bar_fill.size.x = 6.6 * gal_fill
    galaxy_bar_fill.pos.x = 5.5 + galaxy_bar_fill.size.x / 2.0

    status_label.text = (
        "direct inflow: dense streams fall inward\n"
        "host galaxy: still assembling\n"
        "core growth leads the surrounding structure"
    )

    mass_label.text = (
        f"black hole growth: {black_hole_mass:.2f}x\n"
        f"host assembly: {galaxy_assembly:.2f}\n"
        f"inflow strength: {inflow_strength:.2f}"
    )

    # Camera modes.
    if camera_mode == 0:
        scene.center = vector(0, 0.2, 0)
        scene.forward = vector(-0.45, -0.25, -0.86)
        scene.range = 20
    elif camera_mode == 1:
        scene.center = vector(0, 0, 0)
        scene.forward = vector(-0.10, -0.92, -0.38)
        scene.range = 15
    else:
        scene.center = vector(0, 0, 0)
        scene.forward = vector(-0.88, -0.12, -0.46)
        scene.range = 10
