"""
Yellow-Eyed Feeding Dive

Story:
    Feeding dive of a yellow-eyed penguin (Megadyptes antipodes)
    in Otago Peninsula, New Zealand.

Simulation seed:
    A yellow-eyed penguin leaves the Otago Peninsula shoreline, dives beneath
    rolling waves, and hunts glowing fish schools through layered blue water.

Controls:
    Space : pause / resume
    R     : reset dive
    F     : toggle fish glow/trails
    W     : toggle rolling wave markers
    C     : toggle camera follow
    Up/W  : speed up
    Down/S: slow down

Run:
    python yellow_eyed_feeding_dive.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Yellow-Eyed Feeding Dive",
    width=1200,
    height=780,
    background=vector(0.88, 0.95, 1.0),
    center=vector(0, -2.0, 0),
)
scene.forward = vector(-0.45, -0.38, -0.80)
scene.up = vector(0, 1, 0)
scene.range = 13.5

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return vector(
        lerp(a.x, b.x, t),
        lerp(a.y, b.y, t),
        lerp(a.z, b.z, t),
    )


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def rotate2(x, z, ang):
    ca = math.cos(ang)
    sa = math.sin(ang)
    return x * ca - z * sa, x * sa + z * ca


# -----------------------------
# Colors
# -----------------------------
SKY = vector(0.88, 0.95, 1.0)
SHORE = vector(0.74, 0.67, 0.52)
GRASS = vector(0.38, 0.56, 0.30)
CLIFF = vector(0.45, 0.40, 0.34)
SURFACE = vector(0.45, 0.72, 0.88)
DEEP_BLUE = vector(0.05, 0.23, 0.48)
MID_BLUE = vector(0.18, 0.50, 0.75)
LIGHT_BLUE = vector(0.52, 0.78, 0.92)
FISH_GLOW = vector(0.36, 0.95, 1.0)
YELLOW_EYE = vector(1.0, 0.82, 0.16)
PENGUIN_BLACK = vector(0.05, 0.06, 0.07)
PENGUIN_WHITE = vector(0.93, 0.91, 0.82)
PINK_FEET = vector(0.95, 0.48, 0.42)

# -----------------------------
# Environment: coast, water layers, surface
# -----------------------------
sea_floor = box(
    pos=vector(0, -7.35, 0),
    size=vector(24, 0.12, 18),
    color=vector(0.46, 0.42, 0.32),
    opacity=0.90,
)

# Layered blue water volumes below surface.
water_layers = []
layer_data = [
    (-0.55, 1.0, LIGHT_BLUE, 0.20, "sunlit surface layer"),
    (-2.00, 1.7, MID_BLUE, 0.18, "blue hunting layer"),
    (-4.15, 2.1, vector(0.11, 0.36, 0.64), 0.16, "deepening water layer"),
    (-6.40, 2.3, DEEP_BLUE, 0.14, "dim lower layer"),
]
for y, height, col, op, _ in layer_data:
    water_layers.append(
        box(
            pos=vector(1.2, y, 0),
            size=vector(22, height, 17),
            color=col,
            opacity=op,
        )
    )

surface_sheet = box(
    pos=vector(1.2, 0.03, 0),
    size=vector(22, 0.04, 17),
    color=SURFACE,
    opacity=0.30,
)

# Stylized Otago Peninsula shoreline at left.
shore_points = []
for i in range(18):
    z = -8.0 + i * (16.0 / 17)
    x = -8.1 + 0.55 * math.sin(i * 0.85) + 0.25 * math.sin(i * 1.7)
    shore_points.append(vector(x, 0.10, z))

shore_tiles = []
for i, p in enumerate(shore_points):
    width = 2.2 + 0.35 * math.sin(i)
    tile = box(
        pos=vector(p.x - 1.0, -0.03, p.z),
        size=vector(width, 0.16, 0.95),
        color=mix_color(SHORE, CLIFF, 0.25 + 0.20 * math.sin(i * 0.7)),
    )
    shore_tiles.append(tile)

# Hills / cliff markers.
for i in range(11):
    z = -7.0 + i * 1.35
    x = -9.2 + 0.35 * math.sin(i * 1.1)
    hill = cone(
        pos=vector(x, 0.02, z),
        axis=vector(0, 0.95 + 0.45 * random.random(), 0),
        radius=0.70 + 0.25 * random.random(),
        color=mix_color(CLIFF, GRASS, 0.35 + 0.35 * random.random()),
        opacity=0.92,
    )

# Water depth guide lines.
depth_lines = []
for y in [-1.0, -2.4, -3.8, -5.2, -6.6]:
    line = cylinder(
        pos=vector(-9.2, y, -8.2),
        axis=vector(18.2, 0, 0),
        radius=0.012,
        color=vector(0.78, 0.92, 1.0),
        opacity=0.18,
    )
    depth_lines.append(line)

depth_labels = [
    label(pos=vector(9.5, -0.9, 7.3), text="sunlit rolling waves", height=11, box=False, color=vector(0.12, 0.28, 0.40)),
    label(pos=vector(9.5, -2.5, 7.3), text="active feeding layer", height=11, box=False, color=vector(0.08, 0.24, 0.38)),
    label(pos=vector(9.5, -4.8, 7.3), text="deeper blue water", height=11, box=False, color=vector(0.05, 0.18, 0.32)),
]

# Rolling waves represented by transparent crest cylinders.
wave_crests = []
for i in range(16):
    x = -6.0 + i * 1.25
    z = -7.0 + (i % 5) * 3.4
    crest = cylinder(
        pos=vector(x, 0.16, z),
        axis=vector(0.85, 0.0, 0.0),
        radius=0.030,
        color=vector(0.86, 0.98, 1.0),
        opacity=0.55,
    )
    wave_crests.append({"obj": crest, "base": vector(x, 0.16, z), "phase": random.random() * math.tau})

# Bubbles and suspended particles.
bubbles = []
for i in range(70):
    bubble = sphere(
        pos=vector(random.uniform(-6.5, 8.5), random.uniform(-6.8, -0.4), random.uniform(-7.5, 7.5)),
        radius=random.uniform(0.025, 0.075),
        color=vector(0.82, 0.96, 1.0),
        opacity=random.uniform(0.18, 0.46),
    )
    bubbles.append({"obj": bubble, "rise": random.uniform(0.010, 0.035), "phase": random.random() * math.tau})

# -----------------------------
# Penguin model
# -----------------------------
penguin_root = vector(-7.4, 0.45, -3.0)
penguin_parts = []

body = ellipsoid(
    pos=penguin_root,
    length=0.72,
    height=1.08,
    width=0.54,
    color=PENGUIN_BLACK,
)
belly = ellipsoid(
    pos=penguin_root + vector(0.03, -0.03, -0.16),
    length=0.45,
    height=0.82,
    width=0.13,
    color=PENGUIN_WHITE,
)
head = sphere(
    pos=penguin_root + vector(0.0, 0.62, -0.03),
    radius=0.28,
    color=PENGUIN_BLACK,
)
beak = cone(
    pos=penguin_root + vector(0.0, 0.61, -0.29),
    axis=vector(0, 0, -0.30),
    radius=0.065,
    color=vector(0.88, 0.52, 0.16),
)
eye_l = sphere(pos=penguin_root + vector(-0.11, 0.70, -0.25), radius=0.040, color=YELLOW_EYE, emissive=True)
eye_r = sphere(pos=penguin_root + vector(0.11, 0.70, -0.25), radius=0.040, color=YELLOW_EYE, emissive=True)
yellow_band = ring(
    pos=penguin_root + vector(0, 0.71, -0.05),
    axis=vector(0, 1, 0),
    radius=0.285,
    thickness=0.018,
    color=YELLOW_EYE,
    opacity=0.85,
)
flipper_l = ellipsoid(
    pos=penguin_root + vector(-0.35, 0.03, -0.01),
    length=0.18,
    height=0.72,
    width=0.09,
    color=PENGUIN_BLACK,
)
flipper_r = ellipsoid(
    pos=penguin_root + vector(0.35, 0.03, -0.01),
    length=0.18,
    height=0.72,
    width=0.09,
    color=PENGUIN_BLACK,
)
foot_l = ellipsoid(pos=penguin_root + vector(-0.14, -0.59, -0.12), length=0.18, height=0.05, width=0.30, color=PINK_FEET)
foot_r = ellipsoid(pos=penguin_root + vector(0.14, -0.59, -0.12), length=0.18, height=0.05, width=0.30, color=PINK_FEET)

penguin_parts = [body, belly, head, beak, eye_l, eye_r, yellow_band, flipper_l, flipper_r, foot_l, foot_r]

# Local offsets for moving penguin as a group.
base_offsets = {}
for part in penguin_parts:
    base_offsets[part] = part.pos - penguin_root

# Orientation state for penguin group.
penguin_pos = vector(penguin_root.x, penguin_root.y, penguin_root.z)
penguin_dir = vector(1, -0.25, 0)
penguin_roll = 0.0

# Dive path control points.
dive_points = [
    vector(-7.4, 0.45, -3.0),   # shoreline start
    vector(-6.2, 0.22, -2.0),   # surf entry
    vector(-4.5, -0.65, -1.0),  # below waves
    vector(-1.6, -2.25, 0.4),   # first descent
    vector(2.1, -4.2, -1.6),    # deep hunting arc
    vector(5.7, -3.2, 1.8),     # chase fish school
    vector(7.1, -1.7, -0.5),    # rising turn
    vector(4.0, -3.9, -3.5),    # second hunt
    vector(0.2, -5.2, -1.2),    # lower turn
    vector(-2.9, -2.4, 2.2),    # return through school
    vector(-5.3, -0.50, 0.7),   # near surface
    vector(-6.6, 0.18, -1.2),   # surf
]

def catmull_rom(points, t):
    """Closed-ish Catmull-Rom path through dive points."""
    n = len(points)
    total = n - 1
    scaled = clamp(t) * total
    i = int(min(total - 1, math.floor(scaled)))
    local = scaled - i

    p0 = points[max(0, i - 1)]
    p1 = points[i]
    p2 = points[min(n - 1, i + 1)]
    p3 = points[min(n - 1, i + 2)]

    tt = local
    tt2 = tt * tt
    tt3 = tt2 * tt

    return 0.5 * (
        (2 * p1)
        + (-p0 + p2) * tt
        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * tt2
        + (-p0 + 3 * p1 - 3 * p2 + p3) * tt3
    )

# Trail behind penguin.
trail_points = []
trail_objs = []
for i in range(42):
    trail = sphere(
        pos=penguin_pos,
        radius=0.035 * (1.0 - i / 58.0),
        color=vector(0.88, 0.98, 1.0),
        opacity=0.18,
    )
    trail_objs.append(trail)
    trail_points.append(vector(penguin_pos.x, penguin_pos.y, penguin_pos.z))

# -----------------------------
# Fish schools
# -----------------------------
fish_schools = []
fish_objs = []

def make_fish(pos, school_index):
    body_f = ellipsoid(
        pos=pos,
        length=0.26,
        height=0.09,
        width=0.12,
        color=FISH_GLOW,
        emissive=True,
        opacity=0.82,
    )
    tail = cone(
        pos=pos + vector(-0.16, 0, 0),
        axis=vector(-0.13, 0, 0),
        radius=0.065,
        color=vector(0.18, 0.75, 0.95),
        emissive=True,
        opacity=0.75,
    )
    return {"body": body_f, "tail": tail, "school": school_index, "phase": random.random() * math.tau, "caught": False}

school_centers = [
    vector(-0.5, -2.4, 1.6),
    vector(3.8, -4.1, -1.2),
    vector(6.1, -2.2, 2.0),
    vector(1.2, -5.4, -3.3),
]

for si, center in enumerate(school_centers):
    school = {"center": center, "base": center, "fish": [], "phase": random.random() * math.tau, "scatter": 0.0}
    for j in range(18):
        offset = vector(
            random.uniform(-0.70, 0.70),
            random.uniform(-0.35, 0.35),
            random.uniform(-0.55, 0.55),
        )
        fish = make_fish(center + offset, si)
        school["fish"].append(fish)
        fish_objs.append(fish)
    fish_schools.append(school)

# Capture flashes when fish are caught.
capture_flashes = []
for i in range(10):
    capture_flashes.append(
        sphere(pos=vector(0, -10, 0), radius=0.01, color=vector(1.0, 0.95, 0.45), emissive=True, opacity=0.0)
    )

# -----------------------------
# Labels and UI
# -----------------------------
title = label(
    pos=vector(0, 2.35, -7.7),
    text="Yellow-Eyed Feeding Dive",
    height=24,
    box=False,
    color=vector(0.05, 0.16, 0.24),
)
subtitle = label(
    pos=vector(0, 1.85, -7.7),
    text="Otago Peninsula shoreline → rolling waves → layered blue water → glowing fish schools",
    height=12,
    box=False,
    color=vector(0.08, 0.24, 0.34),
)
status = label(
    pos=vector(-8.8, 1.6, 7.6),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.05, 0.14, 0.20),
    background=vector(0.92, 0.98, 1.0),
    opacity=0.78,
)
legend = label(
    pos=vector(7.6, 1.55, 7.5),
    text="Yellow eye-band marks the penguin.\nGlowing fish schools scatter and regroup.\nLayered water shows the feeding dive depth.",
    height=12,
    box=True,
    border=8,
    color=vector(0.05, 0.14, 0.20),
    background=vector(0.92, 0.98, 1.0),
    opacity=0.78,
)

# -----------------------------
# State and controls
# -----------------------------
paused = False
show_fish_glow = True
show_waves = True
camera_follow = False
speed = 1.0
sim_t = 0.0
caught_count = 0
last_capture_index = 0


def reset_sim():
    global sim_t, caught_count
    sim_t = 0.0
    caught_count = 0
    for school in fish_schools:
        school["center"] = vector(school["base"].x, school["base"].y, school["base"].z)
        school["scatter"] = 0.0
        for fish in school["fish"]:
            fish["caught"] = False
            fish["body"].visible = True
            fish["tail"].visible = True
            fish["body"].opacity = 0.82
            fish["tail"].opacity = 0.75
    for flash in capture_flashes:
        flash.opacity = 0.0
        flash.radius = 0.01


def on_keydown(evt):
    global paused, show_fish_glow, show_waves, camera_follow, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_sim()
    elif key == "f":
        show_fish_glow = not show_fish_glow
        for fish in fish_objs:
            fish["body"].emissive = show_fish_glow
            fish["tail"].emissive = show_fish_glow
    elif key == "c":
        camera_follow = not camera_follow
    elif key == "w":
        # W doubles as speed-up when Shift/Up is awkward, but this toggle is useful here.
        show_waves = not show_waves
        for wv in wave_crests:
            wv["obj"].visible = show_waves
    elif key in ("up",):
        speed = min(4.0, speed + 0.25)
    elif key in ("down", "s"):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Penguin group transform
# -----------------------------
def update_penguin(pos, direction, t):
    forward = safe_norm(direction, vector(1, -0.2, 0))
    # Body local model points mostly along vertical; rotate by pitch derived from direction.
    pitch = math.atan2(forward.y, math.sqrt(forward.x * forward.x + forward.z * forward.z))
    yaw = math.atan2(forward.z, forward.x)
    swim_roll = 0.18 * math.sin(t * 8.0)

    for part in penguin_parts:
        off = base_offsets[part]

        # Convert local offsets into a direction-facing coordinate system.
        # Local y is body length. During dive, local y tilts toward swimming direction.
        local_forward = vector(off.y, 0, 0)
        local_side = vector(0, off.x, 0)
        local_depth = vector(0, 0, off.z)

        # Build basis.
        fwd = forward
        side = safe_norm(cross(vector(0, 1, 0), fwd), vector(0, 0, 1))
        upv = safe_norm(cross(fwd, side), vector(0, 1, 0))

        # Slight roll around forward.
        side2 = side * math.cos(swim_roll) + upv * math.sin(swim_roll)
        up2 = upv * math.cos(swim_roll) - side * math.sin(swim_roll)

        newpos = pos + fwd * off.y + side2 * off.x + up2 * off.z
        part.pos = newpos

    # Animate flippers against the swimming direction.
    beat = math.sin(t * 10.5)
    flipper_l.pos += vector(0, 0.055 * beat, 0)
    flipper_r.pos += vector(0, -0.055 * beat, 0)

    # Stretch flippers during underwater phase.
    underwater = 1.0 if pos.y < -0.15 else 0.0
    flipper_l.height = 0.72 + 0.20 * underwater * abs(beat)
    flipper_r.height = 0.72 + 0.20 * underwater * abs(beat)


# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Fish caught: {caught_count}\n"
            f"Speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.018 * speed
    sim_t += dt

    # Dive progresses, loops after reaching the surf again.
    cycle = (sim_t * 0.035) % 1.0
    pos = catmull_rom(dive_points, cycle)
    pos_next = catmull_rom(dive_points, (cycle + 0.006) % 1.0)
    direction = safe_norm(pos_next - pos, penguin_dir)
    penguin_pos = pos
    update_penguin(penguin_pos, direction, sim_t)

    # Camera follow optional.
    if camera_follow:
        scene.center = penguin_pos + vector(0, -0.3, 0)
        scene.range = 8.0
    else:
        scene.center = vector(0, -2.0, 0)
        scene.range = 13.5

    # Rolling waves on surface.
    for i, wv in enumerate(wave_crests):
        obj = wv["obj"]
        phase = wv["phase"]
        travel = (sim_t * 0.55 + i * 0.11) % 12.0
        obj.pos = wv["base"] + vector((travel - 6.0) * 0.08, 0.05 * math.sin(sim_t * 2.8 + phase), 0)
        obj.axis = vector(0.75 + 0.25 * math.sin(sim_t * 1.7 + phase), 0, 0)
        obj.radius = 0.025 + 0.025 * (0.5 + 0.5 * math.sin(sim_t * 3.0 + phase))
        obj.opacity = 0.28 + 0.32 * (0.5 + 0.5 * math.sin(sim_t * 2.4 + phase))

    # Bubbles rise and respawn below.
    for b in bubbles:
        obj = b["obj"]
        obj.pos.y += b["rise"] * speed
        obj.pos.x += 0.004 * math.sin(sim_t * 1.5 + b["phase"])
        obj.pos.z += 0.004 * math.cos(sim_t * 1.7 + b["phase"])
        if obj.pos.y > -0.2:
            obj.pos = vector(random.uniform(-6.5, 8.5), random.uniform(-7.1, -5.2), random.uniform(-7.5, 7.5))
            obj.radius = random.uniform(0.025, 0.075)

    # Penguin trail.
    trail_points.insert(0, vector(penguin_pos.x, penguin_pos.y, penguin_pos.z))
    trail_points = trail_points[:len(trail_objs)]
    for i, tr in enumerate(trail_objs):
        tr.pos = trail_points[i]
        fade = 1.0 - i / len(trail_objs)
        tr.radius = 0.025 + 0.055 * fade
        tr.opacity = 0.04 + 0.22 * fade if penguin_pos.y < 0.1 else 0.02 * fade

    # Fish schools react to penguin.
    nearest_school_distance = 999.0
    for si, school in enumerate(fish_schools):
        center = school["center"]
        dist_to_penguin = mag(center - penguin_pos)
        nearest_school_distance = min(nearest_school_distance, dist_to_penguin)

        # Scatter when penguin approaches, regroup otherwise.
        school["scatter"] += (clamp(1.7 - dist_to_penguin, 0, 1) - school["scatter"]) * 0.045
        flee = safe_norm(center - penguin_pos, vector(1, 0, 0))
        drift = vector(
            0.010 * math.sin(sim_t * 0.9 + school["phase"]),
            0.006 * math.sin(sim_t * 0.7 + si),
            0.012 * math.cos(sim_t * 0.8 + school["phase"]),
        )
        school["center"] += drift + flee * 0.018 * school["scatter"]
        school["center"].x = clamp(school["center"].x, -4.0, 8.2)
        school["center"].y = clamp(school["center"].y, -6.4, -1.0)
        school["center"].z = clamp(school["center"].z, -6.8, 6.8)

        for j, fish in enumerate(school["fish"]):
            if fish["caught"]:
                continue

            ang = sim_t * (1.5 + 0.04 * j) + fish["phase"]
            radius = 0.34 + 0.035 * j + 0.58 * school["scatter"]
            offset = vector(
                math.cos(ang) * radius,
                0.20 * math.sin(ang * 1.7 + j),
                math.sin(ang * 1.2) * radius * 0.70,
            )

            # When scattering, fish stretch away from the penguin.
            offset += flee * school["scatter"] * (0.20 + 0.035 * j)

            fpos = school["center"] + offset
            fish["body"].pos = fpos
            fish["tail"].pos = fpos - vector(0.15, 0, 0)

            # Swim direction is roughly tangent to school motion.
            tangent = vector(-math.sin(ang), 0.12 * math.cos(ang * 1.7), math.cos(ang * 1.2))
            fish["body"].axis = safe_norm(tangent) * 0.26
            fish["tail"].axis = -safe_norm(tangent) * 0.13

            glow = 0.45 + 0.55 * math.sin(sim_t * 5.0 + fish["phase"]) ** 2
            if show_fish_glow:
                fish["body"].color = mix_color(vector(0.10, 0.65, 0.85), FISH_GLOW, glow)
                fish["tail"].color = mix_color(vector(0.08, 0.50, 0.72), FISH_GLOW, 0.55 * glow)
                fish["body"].opacity = 0.62 + 0.32 * glow
                fish["tail"].opacity = 0.50 + 0.30 * glow
            else:
                fish["body"].color = vector(0.24, 0.50, 0.62)
                fish["tail"].color = vector(0.18, 0.38, 0.50)

            # Capture event when very close to the penguin's beak/body.
            if penguin_pos.y < -0.4 and mag(fpos - penguin_pos) < 0.33 and random.random() < 0.09:
                fish["caught"] = True
                fish["body"].visible = False
                fish["tail"].visible = False
                caught_count += 1

                flash = capture_flashes[last_capture_index % len(capture_flashes)]
                last_capture_index += 1
                flash.pos = fpos
                flash.radius = 0.22
                flash.opacity = 0.90

    # Capture flashes fade.
    for flash in capture_flashes:
        if flash.opacity > 0.01:
            flash.opacity *= 0.94
            flash.radius *= 1.025
        else:
            flash.opacity = 0.0

    # Water layer subtle pulsing by depth.
    for i, layer in enumerate(water_layers):
        layer.opacity = layer_data[i][3] + 0.035 * math.sin(sim_t * 0.8 + i) ** 2

    # Shore foam around surf entry.
    surface_sheet.opacity = 0.24 + 0.08 * math.sin(sim_t * 1.6) ** 2

    depth = max(0.0, -penguin_pos.y)
    status.text = (
        f"Dive phase: {int(cycle * 100)}%\n"
        f"Penguin depth: {depth:4.1f} units\n"
        f"Nearest fish school: {nearest_school_distance:4.1f}\n"
        f"Fish caught: {caught_count}\n"
        f"Fish glow: {'on' if show_fish_glow else 'off'}\n"
        f"Waves: {'on' if show_waves else 'off'} | Camera follow: {'on' if camera_follow else 'off'}\n"
        f"Speed: {speed:.2f}x\n"
        "Space pause | R reset | F fish | W waves | C camera | Up/Down speed"
    )
