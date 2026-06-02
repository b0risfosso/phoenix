from vpython import *
import math
import random

# The World's Most Interesting Moth
# Baorisa hieroglyphica-inspired VPython simulation
# A single stylized moth shifts between camouflage, warning display,
# and hypnotic wing-pattern communication.

scene = canvas(
    title="The World's Most Interesting Moth - Baorisa hieroglyphica",
    width=1200,
    height=760,
    background=vector(0.88, 0.94, 0.90),
    center=vector(0, 0.35, 0),
)
scene.forward = vector(0, -0.28, -1)
scene.range = 8.0
scene.autoscale = False

# -----------------------------
# Color palette
# -----------------------------
CREAM = vector(0.96, 0.93, 0.82)
LEAF = vector(0.34, 0.55, 0.28)
LEAF_DARK = vector(0.19, 0.36, 0.17)
BARK = vector(0.48, 0.33, 0.19)
BARK_DARK = vector(0.31, 0.22, 0.15)
WHITE_WING = vector(0.98, 0.96, 0.88)
INK = vector(0.05, 0.05, 0.06)
YELLOW = vector(1.0, 0.78, 0.10)
CORAL = vector(0.95, 0.28, 0.22)
BLUE = vector(0.12, 0.38, 0.82)
VIOLET = vector(0.55, 0.20, 0.80)
SOFT_SHADOW = vector(0.40, 0.44, 0.38)

# -----------------------------
# Utility helpers
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def mix(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1 - t) + b * t


def pulse_color(base, glow, amount):
    return mix(base, glow, clamp(amount, 0, 1))


def make_label(pos, text, height=13, color_value=vector(0.08, 0.12, 0.08), box=False):
    return label(
        pos=pos,
        text=text,
        height=height,
        color=color_value,
        box=box,
        opacity=0.0,
        line=False,
        font="sans",
    )

# -----------------------------
# Habitat stage
# -----------------------------
ground = box(pos=vector(0, -2.75, 0), size=vector(16, 0.12, 8), color=CREAM)
branch = cylinder(pos=vector(-7.0, -1.35, 0.25), axis=vector(14.0, 0.7, -0.3), radius=0.22, color=BARK)
branch2 = cylinder(pos=vector(-5.5, -1.7, -0.45), axis=vector(7.0, 1.2, 0.15), radius=0.09, color=BARK_DARK)
branch3 = cylinder(pos=vector(1.5, -1.5, 0.5), axis=vector(4.5, 1.0, -0.2), radius=0.08, color=BARK_DARK)

# Leaf clusters with different shades to make camouflage meaningful.
leaves = []
for i in range(42):
    x = random.uniform(-7.2, 7.2)
    y = random.uniform(-2.1, 2.3)
    z = random.uniform(-1.2, 1.0)
    leaf_col = mix(LEAF_DARK, LEAF, random.random())
    leaf = ellipsoid(
        pos=vector(x, y, z),
        length=random.uniform(0.55, 1.1),
        height=random.uniform(0.18, 0.34),
        width=random.uniform(0.06, 0.13),
        axis=vector(random.uniform(-0.5, 0.5), random.uniform(0.25, 0.95), random.uniform(-0.1, 0.1)),
        color=leaf_col,
        opacity=0.82,
    )
    leaves.append(leaf)

# Soft background moon/light disk.
moon = sphere(pos=vector(5.9, 3.4, -2.2), radius=0.55, color=vector(1.0, 0.94, 0.68), opacity=0.55)

# -----------------------------
# Moth body and wings
# -----------------------------
moth_root = vector(0, 0, 0)
body = ellipsoid(pos=moth_root + vector(0, 0, 0), length=0.43, height=1.25, width=0.34, color=vector(0.39, 0.31, 0.20))
head = sphere(pos=moth_root + vector(0, 0.74, 0.03), radius=0.20, color=vector(0.32, 0.25, 0.16))
neck = sphere(pos=moth_root + vector(0, 0.50, 0.02), radius=0.17, color=vector(0.47, 0.38, 0.25))

# Eyes and antennae
eye_l = sphere(pos=vector(-0.12, 0.82, 0.19), radius=0.045, color=INK)
eye_r = sphere(pos=vector(0.12, 0.82, 0.19), radius=0.045, color=INK)
ant_l = curve(pos=[vector(-0.08, 0.92, 0.08), vector(-0.35, 1.28, 0.08), vector(-0.62, 1.45, 0.08)], radius=0.014, color=INK)
ant_r = curve(pos=[vector(0.08, 0.92, 0.08), vector(0.35, 1.28, 0.08), vector(0.62, 1.45, 0.08)], radius=0.014, color=INK)

# Wings are flattened ellipsoids, arranged as abstract moth forewings/hindwings.
left_wing = ellipsoid(pos=vector(-0.86, 0.15, 0), length=1.95, height=2.95, width=0.045, axis=vector(-0.58, 0.82, 0), color=WHITE_WING)
right_wing = ellipsoid(pos=vector(0.86, 0.15, 0), length=1.95, height=2.95, width=0.045, axis=vector(0.58, 0.82, 0), color=WHITE_WING)
left_hind = ellipsoid(pos=vector(-0.54, -0.72, -0.03), length=1.45, height=1.45, width=0.04, axis=vector(-0.55, -0.35, 0), color=WHITE_WING)
right_hind = ellipsoid(pos=vector(0.54, -0.72, -0.03), length=1.45, height=1.45, width=0.04, axis=vector(0.55, -0.35, 0), color=WHITE_WING)
wings = [left_wing, right_wing, left_hind, right_hind]

# Picasso-like abstract wing markings. Paired mirrored dots/strokes make communication visible.
patterns = []
pattern_specs = [
    (-1, vector(-0.75, 0.72, 0.07), 0.12, YELLOW),
    (1, vector(0.75, 0.72, 0.07), 0.12, YELLOW),
    (-1, vector(-1.12, 0.05, 0.08), 0.10, CORAL),
    (1, vector(1.12, 0.05, 0.08), 0.10, CORAL),
    (-1, vector(-0.44, -0.35, 0.09), 0.08, BLUE),
    (1, vector(0.44, -0.35, 0.09), 0.08, BLUE),
    (-1, vector(-0.88, -0.72, 0.09), 0.07, VIOLET),
    (1, vector(0.88, -0.72, 0.09), 0.07, VIOLET),
]
for side, pos, rad, col in pattern_specs:
    patterns.append(sphere(pos=pos, radius=rad, color=col, emissive=False))

# Black brushstroke curves on wings.
strokes = []
for side in [-1, 1]:
    strokes.append(curve(
        pos=[vector(side * 0.34, 0.65, 0.11), vector(side * 0.76, 0.43, 0.11), vector(side * 1.05, 0.65, 0.11)],
        radius=0.018,
        color=INK,
    ))
    strokes.append(curve(
        pos=[vector(side * 0.36, -0.12, 0.11), vector(side * 0.74, -0.26, 0.11), vector(side * 1.18, -0.06, 0.11)],
        radius=0.016,
        color=INK,
    ))
    strokes.append(curve(
        pos=[vector(side * 0.24, -0.68, 0.11), vector(side * 0.58, -0.92, 0.11), vector(side * 0.94, -0.83, 0.11)],
        radius=0.014,
        color=INK,
    ))

# Communication rings that radiate from wing pattern during signal mode.
signal_rings = []
for i in range(6):
    r = ring(pos=vector(0, 0.05, 0.13), axis=vector(0, 0, 1), radius=0.5 + i * 0.35, thickness=0.012, color=BLUE, opacity=0.0)
    signal_rings.append(r)

# Camouflage shadows/speckles overlay the wings in camouflage mode.
speckles = []
for i in range(28):
    side = -1 if i % 2 == 0 else 1
    speck = sphere(
        pos=vector(side * random.uniform(0.28, 1.24), random.uniform(-0.95, 0.88), 0.14),
        radius=random.uniform(0.025, 0.055),
        color=mix(LEAF_DARK, BARK, random.random()),
        opacity=0.0,
    )
    speckles.append(speck)

# Warning aura around the moth.
warning_halo = ring(pos=vector(0, 0.0, 0.0), axis=vector(0, 0, 1), radius=1.9, thickness=0.035, color=CORAL, opacity=0.0)

# Threat/predator silhouette so warning display has a reason to appear.
predator = ellipsoid(pos=vector(-6.2, 1.4, -0.15), length=0.7, height=0.35, width=0.18, axis=vector(1, -0.05, 0), color=SOFT_SHADOW, opacity=0.32)
predator_wing_l = ellipsoid(pos=predator.pos + vector(-0.12, 0.18, 0), length=0.6, height=0.18, width=0.04, axis=vector(-0.7, 0.65, 0), color=SOFT_SHADOW, opacity=0.25)
predator_wing_r = ellipsoid(pos=predator.pos + vector(0.12, 0.18, 0), length=0.6, height=0.18, width=0.04, axis=vector(0.7, 0.65, 0), color=SOFT_SHADOW, opacity=0.25)

# Status labels and mode meters.
title_label = make_label(vector(0, 3.45, 0), "The World's Most Interesting Moth", height=21, color_value=vector(0.05, 0.10, 0.07))
mode_label = make_label(vector(0, 3.05, 0), "mode: camouflage", height=15, color_value=vector(0.07, 0.14, 0.08))
legend_label = make_label(
    vector(0, -3.15, 0),
    "1 camouflage   2 warning display   3 hypnotic signal   SPACE pause   R reset path",
    height=12,
    color_value=vector(0.10, 0.14, 0.10),
)

# Bars showing internal state.
bar_base_x = -6.7
bar_y = 2.95
bar_names = ["camouflage", "warning", "signal"]
bar_cols = [LEAF, CORAL, BLUE]
bar_fills = []
for i, name in enumerate(bar_names):
    y = bar_y - i * 0.35
    box(pos=vector(bar_base_x, y, 0), size=vector(1.35, 0.12, 0.04), color=vector(0.80, 0.84, 0.76), opacity=0.6)
    fill = box(pos=vector(bar_base_x - 0.675, y, 0.03), size=vector(0.02, 0.14, 0.04), color=bar_cols[i])
    bar_fills.append(fill)
    make_label(vector(bar_base_x + 1.25, y - 0.02, 0), name, height=10, color_value=vector(0.10, 0.14, 0.10))

# Moth path trail.
trail = curve(radius=0.01, color=vector(0.46, 0.57, 0.41), retain=220)

# -----------------------------
# Simulation state
# -----------------------------
paused = False
manual_mode = None
mode = "camouflage"
mode_timer = 0.0
flight_phase = 0.0
path_reset_flash = 0.0

camouflage_strength = 1.0
warning_strength = 0.0
signal_strength = 0.0

# Mode cycle durations for autonomous behavior.
mode_cycle = [
    ("camouflage", 8.0),
    ("warning", 5.2),
    ("signal", 7.0),
    ("camouflage", 5.5),
    ("signal", 5.0),
]
cycle_index = 0
cycle_elapsed = 0.0

# -----------------------------
# Keyboard controls
# -----------------------------
def keydown(evt):
    global paused, manual_mode, mode, mode_timer, cycle_elapsed, cycle_index, trail, path_reset_flash
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "1":
        manual_mode = "camouflage"
        mode = manual_mode
        mode_timer = 0.0
    elif key == "2":
        manual_mode = "warning"
        mode = manual_mode
        mode_timer = 0.0
    elif key == "3":
        manual_mode = "signal"
        mode = manual_mode
        mode_timer = 0.0
    elif key == "a":
        manual_mode = None
        cycle_index = 0
        cycle_elapsed = 0.0
    elif key == "r":
        trail.clear()
        path_reset_flash = 1.0

scene.bind("keydown", keydown)

# -----------------------------
# Animation helpers
# -----------------------------
def set_moth_offset(offset):
    # Move body components by assigning positions relative to a world offset.
    body.pos = offset + vector(0, 0, 0)
    head.pos = offset + vector(0, 0.74, 0.03)
    neck.pos = offset + vector(0, 0.50, 0.02)
    eye_l.pos = offset + vector(-0.12, 0.82, 0.19)
    eye_r.pos = offset + vector(0.12, 0.82, 0.19)
    ant_l.modify(0, pos=offset + vector(-0.08, 0.92, 0.08))
    ant_l.modify(1, pos=offset + vector(-0.35, 1.28, 0.08))
    ant_l.modify(2, pos=offset + vector(-0.62, 1.45, 0.08))
    ant_r.modify(0, pos=offset + vector(0.08, 0.92, 0.08))
    ant_r.modify(1, pos=offset + vector(0.35, 1.28, 0.08))
    ant_r.modify(2, pos=offset + vector(0.62, 1.45, 0.08))


def set_wing_geometry(offset, flap, spread, shimmer):
    # spread and flap update axes and positions while keeping a simple stylized top view.
    left_wing.pos = offset + vector(-0.80 - 0.16 * spread, 0.12 + 0.04 * flap, 0.02 * shimmer)
    right_wing.pos = offset + vector(0.80 + 0.16 * spread, 0.12 - 0.04 * flap, -0.02 * shimmer)
    left_hind.pos = offset + vector(-0.50 - 0.07 * spread, -0.72, -0.03)
    right_hind.pos = offset + vector(0.50 + 0.07 * spread, -0.72, -0.03)

    left_wing.axis = vector(-0.48 - 0.14 * spread, 0.88 - 0.05 * abs(flap), 0.02 * flap)
    right_wing.axis = vector(0.48 + 0.14 * spread, 0.88 - 0.05 * abs(flap), -0.02 * flap)
    left_hind.axis = vector(-0.55 - 0.08 * spread, -0.36, 0)
    right_hind.axis = vector(0.55 + 0.08 * spread, -0.36, 0)

    # Patterns ride over the wing surfaces.
    local_positions = [
        vector(-0.75 - 0.05 * spread, 0.72, 0.10),
        vector(0.75 + 0.05 * spread, 0.72, 0.10),
        vector(-1.12 - 0.08 * spread, 0.05, 0.11),
        vector(1.12 + 0.08 * spread, 0.05, 0.11),
        vector(-0.44 - 0.02 * spread, -0.35, 0.12),
        vector(0.44 + 0.02 * spread, -0.35, 0.12),
        vector(-0.88 - 0.04 * spread, -0.72, 0.12),
        vector(0.88 + 0.04 * spread, -0.72, 0.12),
    ]
    for obj, local in zip(patterns, local_positions):
        obj.pos = offset + local

    # Move brushstrokes.
    stroke_templates = []
    for side in [-1, 1]:
        stroke_templates.append([vector(side * (0.34 + 0.02 * spread), 0.65, 0.13), vector(side * (0.76 + 0.05 * spread), 0.43, 0.13), vector(side * (1.05 + 0.07 * spread), 0.65, 0.13)])
        stroke_templates.append([vector(side * (0.36 + 0.03 * spread), -0.12, 0.13), vector(side * (0.74 + 0.06 * spread), -0.26, 0.13), vector(side * (1.18 + 0.08 * spread), -0.06, 0.13)])
        stroke_templates.append([vector(side * (0.24 + 0.02 * spread), -0.68, 0.13), vector(side * (0.58 + 0.03 * spread), -0.92, 0.13), vector(side * (0.94 + 0.04 * spread), -0.83, 0.13)])
    for curve_obj, pts in zip(strokes, stroke_templates):
        for j, p in enumerate(pts):
            curve_obj.modify(j, pos=offset + p)

    # Speckles remain on the wing field.
    for idx, speck in enumerate(speckles):
        side = -1 if idx % 2 == 0 else 1
        phase = idx * 0.41
        speck.pos = offset + vector(
            side * (random_speck_x[idx] + 0.04 * spread * side),
            random_speck_y[idx] + 0.015 * math.sin(flight_phase + phase),
            0.145,
        )

# Speckle local coordinates fixed after creation.
random_speck_x = [abs(s.pos.x) for s in speckles]
random_speck_y = [s.pos.y for s in speckles]


def update_modes(dt):
    global mode, mode_timer, cycle_elapsed, cycle_index
    mode_timer += dt
    if manual_mode is None:
        cycle_elapsed += dt
        current_name, duration = mode_cycle[cycle_index]
        mode = current_name
        if cycle_elapsed >= duration:
            cycle_elapsed = 0.0
            cycle_index = (cycle_index + 1) % len(mode_cycle)
            mode_timer = 0.0


def update_strengths(dt):
    global camouflage_strength, warning_strength, signal_strength
    target_cam = 1.0 if mode == "camouflage" else 0.0
    target_warn = 1.0 if mode == "warning" else 0.0
    target_sig = 1.0 if mode == "signal" else 0.0
    rate = 2.2 * dt
    camouflage_strength += (target_cam - camouflage_strength) * rate
    warning_strength += (target_warn - warning_strength) * rate
    signal_strength += (target_sig - signal_strength) * rate


def update_visuals(t, offset):
    # Camouflage blends into bark/leaf colors; warning blasts coral/yellow;
    # signal emphasizes blue/violet pulses and rings.
    cam = camouflage_strength
    warn = warning_strength
    sig = signal_strength

    base_wing = mix(WHITE_WING, mix(LEAF, BARK, 0.45), cam * 0.72)
    base_wing = pulse_color(base_wing, vector(1.0, 0.86, 0.18), warn * (0.35 + 0.25 * math.sin(t * 9)))
    base_wing = pulse_color(base_wing, vector(0.72, 0.88, 1.0), sig * (0.20 + 0.18 * math.sin(t * 6)))
    for w in wings:
        w.color = base_wing

    body.color = mix(vector(0.39, 0.31, 0.20), LEAF_DARK, cam * 0.5)
    head.color = mix(vector(0.32, 0.25, 0.16), LEAF_DARK, cam * 0.45)
    neck.color = mix(vector(0.47, 0.38, 0.25), BARK, cam * 0.45)

    # Pattern intensity by state.
    for idx, p in enumerate(patterns):
        original = pattern_specs[idx][3]
        if mode == "camouflage":
            p.color = mix(original, mix(LEAF_DARK, BARK, 0.6), cam * 0.72)
            p.emissive = False
        elif mode == "warning":
            p.color = pulse_color(original, vector(1.0, 0.18, 0.08), warn * (0.55 + 0.45 * abs(math.sin(t * 8 + idx))))
            p.emissive = warn > 0.45
        else:
            p.color = pulse_color(original, vector(0.16, 0.80, 1.0), sig * (0.45 + 0.35 * math.sin(t * 5 + idx * 0.9)))
            p.emissive = sig > 0.35
        p.radius = pattern_specs[idx][2] * (1.0 + 0.38 * warn * abs(math.sin(t * 7 + idx)) + 0.25 * sig * abs(math.sin(t * 3 + idx)))

    # Strokes pulse faintly in signal mode.
    for i, s in enumerate(strokes):
        s.color = pulse_color(INK, BLUE, sig * (0.2 + 0.3 * abs(math.sin(t * 4 + i))))
        s.radius = 0.014 + 0.008 * sig * abs(math.sin(t * 5 + i * 0.4)) + 0.004 * warn

    # Camouflage speckles become visible during camouflage.
    for i, speck in enumerate(speckles):
        speck.opacity = 0.62 * cam * (0.75 + 0.25 * math.sin(t * 1.6 + i))
        speck.color = mix(LEAF_DARK, BARK, 0.5 + 0.5 * math.sin(i * 1.7))

    # Warning halo.
    warning_halo.pos = offset + vector(0, -0.02, 0.02)
    warning_halo.radius = 1.75 + 0.25 * math.sin(t * 7) * warn
    warning_halo.opacity = 0.12 + 0.38 * warn if warn > 0.04 else 0.0
    warning_halo.color = pulse_color(CORAL, YELLOW, 0.5 + 0.5 * math.sin(t * 9))

    # Hypnotic communication rings.
    for i, r in enumerate(signal_rings):
        ring_phase = (t * 0.65 + i / len(signal_rings)) % 1.0
        r.pos = offset + vector(0, 0.04, 0.16 + i * 0.002)
        r.radius = 0.45 + ring_phase * 2.6
        r.thickness = 0.01 + 0.012 * sig
        r.opacity = sig * (1.0 - ring_phase) * 0.48
        r.color = mix(BLUE, VIOLET, 0.5 + 0.5 * math.sin(t * 2.2 + i))

    # Predator movement reacts to warning mode.
    predator.pos = vector(-6.0 + 1.25 * math.sin(t * 0.33), 1.2 + 0.22 * math.sin(t * 1.2), -0.15)
    if warn > 0.4:
        predator.pos.x -= 0.85 * warn
        predator.opacity = 0.12 + 0.20 * (1 - warn)
    else:
        predator.opacity = 0.30
    predator_wing_l.pos = predator.pos + vector(-0.12, 0.18 + 0.04 * math.sin(t * 8), 0)
    predator_wing_r.pos = predator.pos + vector(0.12, 0.18 - 0.04 * math.sin(t * 8), 0)
    predator_wing_l.opacity = predator.opacity * 0.8
    predator_wing_r.opacity = predator.opacity * 0.8

    # Bar meters.
    values = [cam, warn, sig]
    for fill, val in zip(bar_fills, values):
        fill.size.x = 1.35 * val
        fill.pos.x = bar_base_x - 0.675 + fill.size.x / 2

    mode_label.text = "mode: " + (mode if manual_mode is None else mode + "  (manual; press A for auto)")
    if paused:
        mode_label.text += "  | paused"

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
dt = 1 / 60
while True:
    rate(60)
    if paused:
        continue

    t += dt
    flight_phase += dt * 6.0
    update_modes(dt)
    update_strengths(dt)

    # Smooth hovering path over the branch/leaf field.
    x = 1.65 * math.sin(t * 0.42) + 0.45 * math.sin(t * 1.07)
    y = 0.05 + 0.42 * math.sin(t * 0.64 + 0.7) + 0.08 * math.sin(t * 2.1)
    z = 0.12 * math.sin(t * 0.8)
    offset = vector(x, y, z)

    # Mode affects motion: camouflage is stiller, warning spreads, signal ripples.
    flap_speed = 1.4 + 2.2 * warning_strength + 1.0 * signal_strength
    flap = math.sin(t * 8.0 * flap_speed)
    spread = 0.2 + 0.55 * warning_strength + 0.30 * signal_strength + 0.06 * math.sin(t * 2)
    shimmer = signal_strength * math.sin(t * 9.0)

    set_moth_offset(offset)
    set_wing_geometry(offset, flap, spread, shimmer)
    update_visuals(t, offset)

    # Add trail slowly; it becomes faintly communicative during signal mode.
    if int(t * 20) % 2 == 0:
        trail.append(pos=offset + vector(0, -0.45, 0.02), color=mix(vector(0.46, 0.57, 0.41), BLUE, signal_strength * 0.8))
