"""
Snow Bunny Simulation - VPython

A light-styled VPython scene of a gray bunny sitting and moving through snow.
The bunny alternates between sitting, sniffing, hopping, and pausing.
It leaves soft footprints behind and small snow puffs when it lands.

Run with:
    python snow_bunny_simulation.py

Controls:
    SPACE  pause / resume
    R      reset bunny and tracks
    W      toggle snowfall
    F      toggle footprint fading
    H      show / hide help
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Snow Bunny — sitting, hopping, and moving through snow",
    width=1200,
    height=760,
    background=vector(0.78, 0.88, 1.0),
    center=vector(0, 1.0, 0),
)
scene.forward = vector(-0.45, -0.30, -0.85)
scene.range = 9.5
scene.autoscale = False
scene.userzoom = True
scene.userspin = True

# Lighting
scene.ambient = color.gray(0.78)
distant_light(direction=vector(-0.6, -1.0, -0.4), color=vector(0.72, 0.78, 0.86))
distant_light(direction=vector(0.5, -0.4, 0.8), color=vector(0.55, 0.62, 0.70))

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def make_text_label():
    return label(
        pos=vector(-6.9, 4.6, 0),
        text=(
            "Snow Bunny\n"
            "SPACE pause/resume | R reset | W snowfall | F fade tracks | H help\n"
            "The gray bunny sits, sniffs, hops, and leaves footprints in the snow."
        ),
        align="left",
        height=13,
        border=6,
        box=True,
        opacity=0.78,
        color=vector(0.12, 0.16, 0.20),
        background=vector(0.94, 0.98, 1.0),
    )

# -----------------------------
# World objects
# -----------------------------
snow_ground = box(
    pos=vector(0, -0.05, 0),
    size=vector(18, 0.10, 11),
    color=vector(0.96, 0.985, 1.0),
)

# Slight blue shadow plate beneath snow for depth
under_snow = box(
    pos=vector(0, -0.12, 0),
    size=vector(18.5, 0.05, 11.5),
    color=vector(0.72, 0.82, 0.92),
)

# Soft rolling snow banks
snow_banks = []
for i in range(16):
    x = random.uniform(-8.2, 8.2)
    z = random.choice([-5.35, 5.35]) + random.uniform(-0.2, 0.2)
    bank = ellipsoid(
        pos=vector(x, 0.05, z),
        length=random.uniform(1.0, 2.4),
        height=random.uniform(0.15, 0.38),
        width=random.uniform(0.5, 1.1),
        color=vector(0.91, 0.96, 1.0),
        opacity=0.92,
    )
    snow_banks.append(bank)

# Background trees
for i in range(12):
    x = -8.5 + i * 1.55 + random.uniform(-0.25, 0.25)
    z = 5.15 + random.uniform(-0.25, 0.15)
    trunk = cylinder(
        pos=vector(x, 0.0, z),
        axis=vector(0, 1.15 + random.uniform(-0.15, 0.25), 0),
        radius=0.08,
        color=vector(0.42, 0.28, 0.16),
    )
    for j in range(3):
        cone(
            pos=vector(x, 0.75 + j * 0.52, z),
            axis=vector(0, 0.82, 0),
            radius=0.44 - 0.07 * j,
            color=vector(0.35, 0.55, 0.45),
            opacity=0.92,
        )

# Sparse snow mounds / sparkle crystals
sparkles = []
for i in range(55):
    s = sphere(
        pos=vector(random.uniform(-8.6, 8.6), 0.025, random.uniform(-4.8, 4.8)),
        radius=random.uniform(0.018, 0.045),
        color=vector(0.82, 0.91, 1.0),
        opacity=random.uniform(0.35, 0.75),
    )
    sparkles.append(s)

# -----------------------------
# Bunny construction
# -----------------------------
bunny_parts = []

# Group positions are updated manually with local offsets.
bunny_pos = vector(-5.7, 0.42, -0.5)
bunny_heading = vector(1, 0, 0)

FUR = vector(0.43, 0.45, 0.47)
FUR_SHADOW = vector(0.30, 0.32, 0.34)
FUR_LIGHT = vector(0.62, 0.64, 0.66)
PINK = vector(1.0, 0.64, 0.73)
DARK = vector(0.08, 0.08, 0.09)

body = ellipsoid(pos=bunny_pos, length=1.25, height=0.72, width=0.58, color=FUR)
chest = ellipsoid(pos=bunny_pos + vector(0.34, 0.07, 0), length=0.55, height=0.55, width=0.50, color=FUR_LIGHT)
head = ellipsoid(pos=bunny_pos + vector(0.78, 0.42, 0), length=0.58, height=0.50, width=0.46, color=FUR)
nose = sphere(pos=head.pos + vector(0.32, -0.02, 0), radius=0.055, color=PINK)
left_eye = sphere(pos=head.pos + vector(0.19, 0.10, -0.17), radius=0.045, color=DARK)
right_eye = sphere(pos=head.pos + vector(0.19, 0.10, 0.17), radius=0.045, color=DARK)
tail = sphere(pos=bunny_pos + vector(-0.65, 0.12, 0), radius=0.19, color=FUR_LIGHT)

left_ear_outer = ellipsoid(pos=head.pos + vector(-0.05, 0.56, -0.14), length=0.18, height=0.88, width=0.13, color=FUR)
right_ear_outer = ellipsoid(pos=head.pos + vector(-0.05, 0.56, 0.14), length=0.18, height=0.88, width=0.13, color=FUR)
left_ear_inner = ellipsoid(pos=head.pos + vector(0.00, 0.56, -0.145), length=0.08, height=0.67, width=0.065, color=PINK)
right_ear_inner = ellipsoid(pos=head.pos + vector(0.00, 0.56, 0.145), length=0.08, height=0.67, width=0.065, color=PINK)

left_front_paw = ellipsoid(pos=bunny_pos + vector(0.45, -0.31, -0.20), length=0.34, height=0.16, width=0.15, color=FUR_SHADOW)
right_front_paw = ellipsoid(pos=bunny_pos + vector(0.45, -0.31, 0.20), length=0.34, height=0.16, width=0.15, color=FUR_SHADOW)
left_back_paw = ellipsoid(pos=bunny_pos + vector(-0.34, -0.30, -0.22), length=0.58, height=0.18, width=0.18, color=FUR_SHADOW)
right_back_paw = ellipsoid(pos=bunny_pos + vector(-0.34, -0.30, 0.22), length=0.58, height=0.18, width=0.18, color=FUR_SHADOW)

whiskers = []
for side in [-1, 1]:
    for k, dy in enumerate([-0.04, 0.01, 0.06]):
        w = curve(
            pos=[
                nose.pos + vector(-0.02, dy, 0.03 * side),
                nose.pos + vector(0.12, dy + 0.02 * (k - 1), 0.42 * side),
            ],
            radius=0.008,
            color=vector(0.22, 0.23, 0.24),
        )
        whiskers.append(w)

bunny_parts.extend([
    body, chest, head, nose, left_eye, right_eye, tail,
    left_ear_outer, right_ear_outer, left_ear_inner, right_ear_inner,
    left_front_paw, right_front_paw, left_back_paw, right_back_paw,
])

# Store local offsets and base dimensions for all non-curve parts
base_offsets = {}
base_dims = {}
for part in bunny_parts:
    base_offsets[part] = part.pos - bunny_pos
    base_dims[part] = (getattr(part, "length", None), getattr(part, "height", None), getattr(part, "width", None), getattr(part, "radius", None))

# Whisker local endpoints
whisker_offsets = []
for w in whiskers:
    pts = []
    for p in w.point(0)['pos'], w.point(1)['pos']:
        pts.append(p - bunny_pos)
    whisker_offsets.append(pts)

# -----------------------------
# Animation state
# -----------------------------
paused = False
show_help = True
snowfall_on = True
fade_footprints = True
state = "sit"
state_timer = 0.0
state_duration = 2.2
hop_start = bunny_pos
hop_target = bunny_pos + vector(1.0, 0, 0)
hop_progress = 0.0
step_count = 0
breath_phase = 0.0
blink_timer = 0.0
blink_until = 0.0

footprints = []
snowflakes = []
puffs = []
help_label = make_text_label()

# Snowflakes
for i in range(150):
    flake = sphere(
        pos=vector(random.uniform(-8.8, 8.8), random.uniform(1.2, 6.2), random.uniform(-5.2, 5.2)),
        radius=random.uniform(0.015, 0.04),
        color=vector(1, 1, 1),
        opacity=random.uniform(0.45, 0.9),
    )
    flake.vel = vector(random.uniform(-0.08, 0.08), random.uniform(-0.45, -0.18), random.uniform(-0.05, 0.05))
    snowflakes.append(flake)


def choose_new_state():
    global state, state_timer, state_duration, hop_start, hop_target, hop_progress, bunny_heading
    state_timer = 0.0
    r = random.random()
    if state == "hop":
        state = "sit" if r < 0.45 else "sniff"
        state_duration = random.uniform(1.1, 2.5)
        return
    if r < 0.52:
        state = "hop"
        state_duration = random.uniform(0.75, 1.05)
        hop_progress = 0.0
        hop_start = vector(bunny_pos.x, bunny_pos.y, bunny_pos.z)
        # wandering direction, mostly across the snowfield
        angle = random.uniform(-0.55, 0.55)
        if bunny_pos.x > 6.2:
            base = math.pi
        elif bunny_pos.x < -6.2:
            base = 0.0
        else:
            base = 0.0 if bunny_heading.x >= 0 else math.pi
            if random.random() < 0.18:
                base += math.pi
        direction = vector(math.cos(base + angle), 0, math.sin(base + angle))
        bunny_heading = norm(direction)
        distance = random.uniform(0.72, 1.25)
        target = hop_start + bunny_heading * distance
        target.x = clamp(target.x, -7.0, 7.0)
        target.z = clamp(target.z, -4.0, 4.0)
        hop_target = vector(target.x, 0.42, target.z)
    elif r < 0.76:
        state = "sit"
        state_duration = random.uniform(1.4, 3.2)
    else:
        state = "sniff"
        state_duration = random.uniform(1.0, 2.0)


def add_footprints(pos, heading):
    # two soft oval impressions behind the bunny
    side = vector(-heading.z, 0, heading.x)
    back = -heading * 0.28
    for s in [-1, 1]:
        fp = ellipsoid(
            pos=vector(pos.x, 0.012, pos.z) + side * (0.18 * s) + back,
            length=0.34,
            height=0.018,
            width=0.16,
            color=vector(0.72, 0.84, 0.95),
            opacity=0.56,
        )
        fp.axis = heading * 0.34
        fp.age = 0.0
        footprints.append(fp)


def add_snow_puff(pos):
    for i in range(9):
        puff = sphere(
            pos=vector(pos.x, 0.10, pos.z) + vector(random.uniform(-0.18, 0.18), 0, random.uniform(-0.18, 0.18)),
            radius=random.uniform(0.025, 0.055),
            color=vector(1, 1, 1),
            opacity=0.70,
        )
        puff.vel = vector(random.uniform(-0.18, 0.18), random.uniform(0.18, 0.45), random.uniform(-0.18, 0.18))
        puff.age = 0.0
        puffs.append(puff)


def orient_offset(local_offset, heading):
    # local x follows heading; local z follows sideways direction
    side = vector(-heading.z, 0, heading.x)
    return heading * local_offset.x + vector(0, local_offset.y, 0) + side * local_offset.z


def update_bunny_pose(dt):
    global breath_phase, blink_timer, blink_until
    breath_phase += dt * 2.8
    blink_timer += dt
    if blink_timer > random.uniform(3.0, 6.0):
        blink_timer = 0.0
        blink_until = 0.16
    if blink_until > 0:
        blink_until -= dt

    breathe = 1.0 + 0.035 * math.sin(breath_phase)
    hop_squash = 1.0
    vertical_lift = 0.0
    sniff_dip = 0.0
    ear_wiggle = 0.05 * math.sin(breath_phase * 1.2)

    if state == "hop":
        phase = math.sin(math.pi * hop_progress)
        vertical_lift = 0.58 * phase
        hop_squash = 1.0 - 0.11 * phase
        ear_wiggle += 0.16 * math.sin(math.pi * hop_progress)
    elif state == "sniff":
        sniff_dip = 0.16 * (0.5 + 0.5 * math.sin(breath_phase * 2.2))
        ear_wiggle += 0.10 * math.sin(breath_phase * 2.8)
    elif state == "sit":
        ear_wiggle += 0.025 * math.sin(breath_phase * 0.8)

    for part in bunny_parts:
        off = base_offsets[part]
        adjusted = vector(off.x, off.y, off.z)

        # head lowers while sniffing
        if part in [head, nose, left_eye, right_eye, left_ear_outer, right_ear_outer, left_ear_inner, right_ear_inner]:
            adjusted.y -= sniff_dip
            adjusted.x += 0.04 * math.sin(breath_phase * 1.5) if state == "sniff" else 0

        # ears wiggle mostly upward/backward
        if part in [left_ear_outer, right_ear_outer, left_ear_inner, right_ear_inner]:
            adjusted.x += ear_wiggle
            adjusted.y += 0.03 * math.sin(breath_phase * 1.6)

        # paws tuck during sitting, stretch during hop
        if part in [left_back_paw, right_back_paw]:
            if state == "hop":
                adjusted.x -= 0.16 * math.sin(math.pi * hop_progress)
            else:
                adjusted.x += 0.05
        if part in [left_front_paw, right_front_paw]:
            if state == "hop":
                adjusted.x += 0.18 * math.sin(math.pi * hop_progress)

        part.pos = bunny_pos + vector(0, vertical_lift, 0) + orient_offset(adjusted, bunny_heading)

    # breathing scale on body/chest
    body.height = 0.72 * breathe * hop_squash
    body.width = 0.58 * breathe
    chest.height = 0.55 * breathe
    chest.width = 0.50 * breathe

    # blink by briefly shrinking eyes
    eye_radius = 0.014 if blink_until > 0 else 0.045
    left_eye.radius = eye_radius
    right_eye.radius = eye_radius

    # update whiskers from local offsets, with sniffing tremble
    for wi, w in enumerate(whiskers):
        pts = []
        tremble = 0.03 * math.sin(breath_phase * 7 + wi) if state == "sniff" else 0.0
        for j, off in enumerate(whisker_offsets[wi]):
            adjusted = vector(off.x, off.y - sniff_dip, off.z + tremble * (1 if off.z >= 0 else -1))
            pts.append(bunny_pos + vector(0, vertical_lift, 0) + orient_offset(adjusted, bunny_heading))
        w.clear()
        w.append(pos=pts[0])
        w.append(pos=pts[1])


def update_snow(dt):
    if not snowfall_on:
        for flake in snowflakes:
            flake.visible = False
        return
    for flake in snowflakes:
        flake.visible = True
        flake.pos += flake.vel * dt
        flake.pos.x += 0.10 * math.sin(0.6 * scene.time + flake.pos.y) * dt
        if flake.pos.y < 0.04:
            flake.pos = vector(random.uniform(-8.8, 8.8), random.uniform(4.5, 6.8), random.uniform(-5.2, 5.2))


def update_footprints(dt):
    for fp in list(footprints):
        fp.age += dt
        if fade_footprints:
            fp.opacity = max(0.0, 0.56 * (1.0 - fp.age / 28.0))
            if fp.opacity <= 0.02:
                fp.visible = False
                footprints.remove(fp)
    # hard cap to avoid rendering load
    while len(footprints) > 80:
        old = footprints.pop(0)
        old.visible = False


def update_puffs(dt):
    for puff in list(puffs):
        puff.age += dt
        puff.pos += puff.vel * dt
        puff.vel.y -= 0.85 * dt
        puff.opacity = max(0, 0.70 * (1.0 - puff.age / 1.0))
        puff.radius *= 1.0 + 0.75 * dt
        if puff.age > 1.0:
            puff.visible = False
            puffs.remove(puff)


def reset_scene():
    global bunny_pos, bunny_heading, state, state_timer, state_duration, hop_progress, step_count
    bunny_pos = vector(-5.7, 0.42, -0.5)
    bunny_heading = vector(1, 0, 0)
    state = "sit"
    state_timer = 0.0
    state_duration = 1.6
    hop_progress = 0.0
    step_count = 0
    for fp in footprints:
        fp.visible = False
    footprints.clear()
    for puff in puffs:
        puff.visible = False
    puffs.clear()


def keydown(evt):
    global paused, snowfall_on, fade_footprints, show_help
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_scene()
    elif key == "w":
        snowfall_on = not snowfall_on
    elif key == "f":
        fade_footprints = not fade_footprints
    elif key == "h":
        show_help = not show_help
        help_label.visible = show_help

scene.bind("keydown", keydown)

# Give canvas a time attribute for snow sway convenience
scene.time = 0.0

# -----------------------------
# Main loop
# -----------------------------
last_hop_progress = 0.0
while True:
    rate(60)
    dt = 1.0 / 60.0
    scene.time += dt

    if paused:
        update_bunny_pose(dt)
        continue

    state_timer += dt

    if state == "hop":
        last_hop_progress = hop_progress
        hop_progress = clamp(state_timer / state_duration, 0.0, 1.0)
        s = smoothstep(hop_progress)
        bunny_pos = hop_start + (hop_target - hop_start) * s

        # create footprints and puff on landing
        if last_hop_progress < 0.88 <= hop_progress:
            add_footprints(hop_target, bunny_heading)
            add_snow_puff(hop_target)
            step_count += 1

    if state_timer >= state_duration:
        choose_new_state()

    update_bunny_pose(dt)
    update_snow(dt)
    update_footprints(dt)
    update_puffs(dt)

    # subtle sparkle twinkle
    for i, sp in enumerate(sparkles):
        sp.opacity = 0.42 + 0.22 * (0.5 + 0.5 * math.sin(scene.time * 1.6 + i * 0.41))
