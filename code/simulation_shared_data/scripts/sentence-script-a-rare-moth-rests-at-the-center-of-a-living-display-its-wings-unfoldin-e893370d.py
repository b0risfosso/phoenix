"""
Hieroglyph Moth Gallery

A VPython simulation of a rare moth resting at the center of an open living display.
Its enlarged wings unfold across the full length of the body into intricate abstract symbols that pulse like painted language.

Controls:
    Space : pause / resume
    U     : unfold / fold wings
    G     : toggle glyph pulse animation
    S     : toggle symbol streams
    R     : reset
    Up/W  : speed up
    Down/S: slow down

Run:
    python hieroglyph_moth_gallery.py

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
    title="Hieroglyph Moth Gallery",
    width=1200,
    height=780,
    background=vector(0.97, 0.95, 0.90),
    center=vector(0, 1.1, 0),
)
scene.forward = vector(-0.45, -0.32, -0.83)
scene.up = vector(0, 1, 0)
scene.range = 7.8

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


def rotate_2d(x, y, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return x * ca - y * sa, x * sa + y * ca


def local_to_world(side, u, v, open_angle, y_lift=0.0):
    """
    Convert wing-local coordinates into world coordinates.
    side: -1 left, +1 right
    u: outward coordinate from body
    v: vertical wing coordinate
    open_angle: unfolding rotation angle
    """
    # Folded wings are steep and close; open wings spread out horizontally.
    spread = lerp(0.42, 1.18, open_angle)
    rise = lerp(1.05, 0.55, open_angle)
    sweep = lerp(0.42, -0.15, open_angle)

    # Wings are vertically centered on the body and scaled tall enough to cover
    # the moth from lower abdomen to head when unfolded.
    x = side * (0.36 + u * spread)
    y = 1.48 + v * rise + y_lift
    z = -0.04 + side * u * sweep

    # Slight fan rotation for organic unfolding.
    fan = side * lerp(0.42, 0.03, open_angle)
    rx, rz = rotate_2d(x - side * 0.38, z, fan)
    return vector(side * 0.38 + rx, y, rz)


# -----------------------------
# Colors
# -----------------------------
CREAM = vector(0.94, 0.87, 0.72)
AMBER = vector(0.88, 0.57, 0.23)
DARK = vector(0.16, 0.10, 0.07)
INK = vector(0.10, 0.07, 0.05)
GOLD = vector(1.0, 0.74, 0.25)
GREEN = vector(0.22, 0.58, 0.36)
BLUE = vector(0.25, 0.52, 0.74)
ROSE = vector(0.72, 0.32, 0.42)
STONE = vector(0.76, 0.72, 0.64)
GLASS = vector(0.82, 0.93, 0.96)

# -----------------------------
# Gallery setting
# -----------------------------
floor = box(
    pos=vector(0, -0.06, 0),
    size=vector(12, 0.08, 10),
    color=vector(0.86, 0.82, 0.72),
)
# Walls removed: the moth now appears in an open gallery space.

pedestal = cylinder(
    pos=vector(0, 0, 0),
    axis=vector(0, 0.70, 0),
    radius=1.18,
    color=vector(0.72, 0.68, 0.60),
)
display_top = cylinder(
    pos=vector(0, 0.70, 0),
    axis=vector(0, 0.08, 0),
    radius=1.36,
    color=vector(0.82, 0.78, 0.68),
)

glass_case = box(
    pos=vector(0, 1.75, 0),
    size=vector(5.4, 2.3, 1.25),
    color=GLASS,
    opacity=0.13,
)

case_edges = []
for sx in [-1, 1]:
    for sz in [-1, 1]:
        case_edges.append(
            cylinder(
                pos=vector(sx * 2.7, 0.72, sz * 0.625),
                axis=vector(0, 2.08, 0),
                radius=0.012,
                color=vector(0.55, 0.65, 0.68),
                opacity=0.45,
            )
        )

# Free-standing gallery placards replacing the removed wall display.
panel_symbols = []
placard_stands = []
for i, x in enumerate([-4.2, -2.1, 2.1, 4.2]):
    stand = cylinder(
        pos=vector(x, 0.02, 2.48),
        axis=vector(0, 1.32, 0),
        radius=0.025,
        color=vector(0.47, 0.38, 0.28),
        opacity=0.70,
    )
    foot = cylinder(
        pos=vector(x, 0.02, 2.48),
        axis=vector(0, 0.035, 0),
        radius=0.28,
        color=vector(0.60, 0.51, 0.39),
        opacity=0.70,
    )
    panel = box(
        pos=vector(x, 1.98, 2.48),
        size=vector(1.45, 1.85, 0.06),
        color=vector(0.96, 0.92, 0.82),
    )
    frame = box(
        pos=vector(x, 1.98, 2.445),
        size=vector(1.60, 2.00, 0.035),
        color=vector(0.54, 0.42, 0.28),
        opacity=0.32,
    )
    placard_stands.extend([stand, foot, panel, frame])
    for j in range(5):
        glyph = cylinder(
            pos=vector(x - 0.42 + 0.21 * (j % 3), 1.43 + 0.24 * j, 2.40),
            axis=vector(0.22 + 0.06 * (j % 2), 0.03, 0),
            radius=0.018,
            color=mix_color(INK, GOLD, 0.15 * j),
            opacity=0.72,
        )
        panel_symbols.append(glyph)

# -----------------------------
# Moth body
# -----------------------------
body = ellipsoid(
    pos=vector(0, 1.34, -0.04),
    length=0.52,
    height=1.02,
    width=0.34,
    color=vector(0.24, 0.15, 0.09),
)
thorax = sphere(
    pos=vector(0, 1.50, -0.05),
    radius=0.25,
    color=vector(0.31, 0.20, 0.12),
)
head = sphere(
    pos=vector(0, 1.95, -0.04),
    radius=0.17,
    color=vector(0.20, 0.13, 0.08),
)
eye_l = sphere(pos=vector(-0.08, 2.00, -0.18), radius=0.035, color=vector(0.03, 0.02, 0.01), emissive=True)
eye_r = sphere(pos=vector(0.08, 2.00, -0.18), radius=0.035, color=vector(0.03, 0.02, 0.01), emissive=True)

# Antennae made of curved bead chains.
antennae = []
for side in [-1, 1]:
    prev = vector(side * 0.08, 2.05, -0.05)
    for k in range(8):
        t = (k + 1) / 8.0
        pos = vector(
            side * (0.08 + 0.55 * t),
            2.05 + 0.30 * math.sin(t * math.pi),
            -0.06 - 0.18 * t,
        )
        segment = cylinder(
            pos=prev,
            axis=pos - prev,
            radius=0.012 * (1.0 - 0.05 * k),
            color=DARK,
        )
        bead = sphere(pos=pos, radius=0.018 * (1.0 - 0.04 * k), color=DARK)
        antennae.extend([segment, bead])
        prev = pos

# Legs
legs = []
for side in [-1, 1]:
    for i, y in enumerate([1.22, 1.38, 1.55]):
        hip = vector(side * 0.16, y, -0.03)
        knee = vector(side * (0.45 + 0.12 * i), y - 0.18, -0.10 - 0.06 * i)
        foot = vector(side * (0.62 + 0.15 * i), y - 0.31, -0.18 - 0.10 * i)
        upper = cylinder(pos=hip, axis=knee - hip, radius=0.014, color=DARK)
        lower = cylinder(pos=knee, axis=foot - knee, radius=0.011, color=DARK)
        legs.extend([upper, lower])

# -----------------------------
# Wing tiles
# -----------------------------
wing_tiles = []
wing_outline = []

# Irregular wing plan: top and lower lobes.
for side in [-1, 1]:
    for row in range(17):
        v = -0.92 + row * 0.115
        max_u = 1.48 - 0.34 * abs(v + 0.04) + 0.22 * math.cos((v + 0.92) * math.pi * 1.15)
        max_u = max(0.52, max_u)
        cols = max(4, int(max_u / 0.145))
        for col in range(cols):
            u = 0.16 + col * 0.145
            if u > max_u:
                continue

            # Natural edge taper.
            edge_t = u / max_u
            tile_size = 0.19 * (1.08 - 0.22 * edge_t)
            pos = local_to_world(side, u, v, 0.0)

            base_color = mix_color(CREAM, AMBER, 0.25 + 0.33 * edge_t + 0.10 * random.random())
            tile = box(
                pos=pos,
                size=vector(tile_size, 0.018, tile_size * 0.82),
                color=base_color,
                opacity=0.96,
            )
            tile.rotate(angle=side * 0.10 + 0.05 * math.sin(row), axis=vector(0, 1, 0), origin=pos)

            wing_tiles.append(
                {
                    "obj": tile,
                    "side": side,
                    "u": u,
                    "v": v,
                    "size": tile_size,
                    "base": base_color,
                    "phase": random.random() * math.tau,
                    "edge": edge_t,
                }
            )

    # Wing outer contour beads
    for n in range(46):
        theta = n / 45.0
        v = -0.94 + 1.88 * theta
        max_u = 1.48 - 0.34 * abs(v + 0.04) + 0.22 * math.cos((v + 0.92) * math.pi * 1.15)
        pos = local_to_world(side, max_u + 0.03, v, 0.0, 0.015)
        bead = sphere(pos=pos, radius=0.032, color=vector(0.20, 0.12, 0.07), opacity=0.84)
        wing_outline.append({"obj": bead, "side": side, "u": max_u + 0.03, "v": v, "phase": random.random() * math.tau})

# -----------------------------
# Abstract glyph markings on wings
# -----------------------------
glyphs = []
glyph_colors = [INK, GOLD, GREEN, BLUE, ROSE]

def create_glyph(side, u, v, kind, glyph_color, scale=1.0):
    pos = local_to_world(side, u, v, 0.0, 0.035)
    items = []

    if kind == "bar":
        item = cylinder(
            pos=pos + vector(-side * 0.08 * scale, 0, 0),
            axis=vector(side * 0.22 * scale, 0, 0.02 * scale),
            radius=0.020 * scale,
            color=glyph_color,
            emissive=False,
        )
        items.append(item)

    elif kind == "hook":
        stem = cylinder(
            pos=pos + vector(0, -0.05 * scale, 0),
            axis=vector(0, 0.16 * scale, 0.02 * scale),
            radius=0.015 * scale,
            color=glyph_color,
        )
        dot = sphere(
            pos=pos + vector(side * 0.10 * scale, 0.08 * scale, 0.01),
            radius=0.040 * scale,
            color=glyph_color,
        )
        items.extend([stem, dot])

    elif kind == "eye":
        ring_glyph = ring(
            pos=pos,
            axis=vector(0, 1, 0),
            radius=0.075 * scale,
            thickness=0.012 * scale,
            color=glyph_color,
        )
        pupil = sphere(
            pos=pos + vector(0, 0.008, 0),
            radius=0.026 * scale,
            color=INK,
            emissive=True,
        )
        items.extend([ring_glyph, pupil])

    elif kind == "branch":
        base = pos + vector(-side * 0.09 * scale, -0.06 * scale, 0)
        main = cylinder(
            pos=base,
            axis=vector(side * 0.19 * scale, 0.13 * scale, 0.01),
            radius=0.012 * scale,
            color=glyph_color,
        )
        twig1 = cylinder(
            pos=base + vector(side * 0.08 * scale, 0.055 * scale, 0),
            axis=vector(side * 0.07 * scale, -0.09 * scale, 0.01),
            radius=0.010 * scale,
            color=glyph_color,
        )
        twig2 = cylinder(
            pos=base + vector(side * 0.12 * scale, 0.085 * scale, 0),
            axis=vector(side * 0.08 * scale, 0.06 * scale, 0.01),
            radius=0.010 * scale,
            color=glyph_color,
        )
        items.extend([main, twig1, twig2])

    elif kind == "stack":
        for i in range(3):
            bar = cylinder(
                pos=pos + vector(-side * 0.08 * scale, (-0.06 + 0.06 * i) * scale, 0),
                axis=vector(side * 0.17 * scale, 0, 0),
                radius=0.010 * scale,
                color=glyph_color,
            )
            items.append(bar)

    return {
        "items": items,
        "side": side,
        "u": u,
        "v": v,
        "kind": kind,
        "color": glyph_color,
        "scale": scale,
        "phase": random.random() * math.tau,
    }


kinds = ["bar", "hook", "eye", "branch", "stack"]
for side in [-1, 1]:
    positions = [
        (0.34, 0.82), (0.68, 0.74), (1.05, 0.62),
        (0.42, 0.48), (0.82, 0.34), (1.22, 0.20),
        (0.36, 0.04), (0.78, -0.08), (1.28, -0.18),
        (0.42, -0.38), (0.82, -0.52), (1.18, -0.66),
        (0.34, -0.78), (0.70, -0.86),
    ]
    for i, (u, v) in enumerate(positions):
        color_choice = glyph_colors[(i + (0 if side < 0 else 2)) % len(glyph_colors)]
        glyphs.append(create_glyph(side, u, v, kinds[i % len(kinds)], color_choice, 0.85 + 0.22 * (i % 3)))

# Floating symbol streams above the moth
symbol_streams = []
for i in range(34):
    angle = random.random() * math.tau
    rad = random.uniform(0.7, 2.5)
    y = random.uniform(2.1, 3.25)
    pos = vector(math.cos(angle) * rad, y, math.sin(angle) * 0.32 - 0.25)
    kind = random.choice(["bar", "dot", "ring", "stroke"])
    if kind == "bar":
        obj = cylinder(
            pos=pos,
            axis=vector(random.uniform(-0.16, 0.16), random.uniform(-0.03, 0.09), random.uniform(-0.04, 0.04)),
            radius=random.uniform(0.008, 0.018),
            color=random.choice(glyph_colors),
            opacity=0.55,
        )
    elif kind == "dot":
        obj = sphere(pos=pos, radius=random.uniform(0.025, 0.055), color=random.choice(glyph_colors), opacity=0.50)
    elif kind == "ring":
        obj = ring(pos=pos, axis=vector(0, 1, 0), radius=random.uniform(0.04, 0.08), thickness=0.009, color=random.choice(glyph_colors), opacity=0.55)
    else:
        obj = box(pos=pos, size=vector(0.04, 0.012, 0.16), color=random.choice(glyph_colors), opacity=0.50)
    symbol_streams.append({"obj": obj, "angle": angle, "rad": rad, "base_y": y, "phase": random.random() * math.tau, "speed": random.uniform(0.2, 0.55)})

# Thin light beams from gallery to display
light_beams = []
for x in [-2.2, 0, 2.2]:
    beam = cylinder(
        pos=vector(x, 4.35, -2.2),
        axis=vector(-x * 0.16, -2.50, 2.0),
        radius=0.035,
        color=vector(1.0, 0.92, 0.68),
        opacity=0.18,
    )
    light_beams.append(beam)

# Text labels
title = label(
    pos=vector(0, 4.2, -1.0),
    text="Hieroglyph Moth Gallery",
    height=24,
    box=False,
    color=vector(0.14, 0.10, 0.07),
)
status = label(
    pos=vector(-5.0, 3.65, -1.0),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.13, 0.09, 0.06),
    background=vector(0.96, 0.92, 0.82),
    opacity=0.78,
)
legend = label(
    pos=vector(4.85, 3.55, -1.0),
    text="The moth rests inside a living gallery.\nIts enlarged wings cover the full body.\nGlyphs pulse, drift, and echo through open space.",
    height=12,
    box=True,
    border=8,
    color=vector(0.13, 0.09, 0.06),
    background=vector(0.96, 0.92, 0.82),
    opacity=0.78,
)

# -----------------------------
# Animation state
# -----------------------------
paused = False
target_open = 1.0
open_amount = 0.0
glyph_pulse_enabled = True
streams_enabled = True
speed = 1.0
t = 0.0


def set_obj_opacity(obj, opacity):
    try:
        obj.opacity = opacity
    except Exception:
        pass


def reset_scene():
    global t, open_amount, target_open, speed
    t = 0.0
    open_amount = 0.0
    target_open = 1.0
    speed = 1.0


def on_keydown(evt):
    global paused, target_open, glyph_pulse_enabled, streams_enabled, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "u":
        target_open = 0.0 if target_open > 0.5 else 1.0
    elif key == "g":
        glyph_pulse_enabled = not glyph_pulse_enabled
    elif key == "r":
        reset_scene()
    elif key == "s":
        # Down arrow sometimes appears as "down"; S toggles streams.
        streams_enabled = not streams_enabled
        for item in symbol_streams:
            item["obj"].visible = streams_enabled
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down",):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Wing openness: {int(open_amount * 100)}%\n"
            f"Speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.025 * speed
    t += dt

    # Smooth wing unfolding.
    open_amount += (target_open - open_amount) * 0.045 * speed
    open_amount = clamp(open_amount)

    # Body breathing shimmer.
    breath = 0.5 + 0.5 * math.sin(t * 2.0)
    thorax.radius = 0.245 + 0.018 * breath
    body.color = mix_color(vector(0.21, 0.13, 0.08), vector(0.33, 0.22, 0.13), 0.35 * breath)

    # Antennae subtle living motion.
    for idx, obj in enumerate(antennae):
        if isinstance(obj, sphere):
            obj.pos.y += 0.0008 * math.sin(t * 3.0 + idx)

    # Wing tiles unfold and pulse.
    language_energy = clamp(open_amount * (0.6 + 0.4 * math.sin(t * 0.55) ** 2))
    for tile in wing_tiles:
        obj = tile["obj"]
        side = tile["side"]
        u = tile["u"]
        v = tile["v"]
        pos = local_to_world(side, u, v, open_amount)

        flutter = 0.012 * math.sin(t * 4.0 + tile["phase"]) * open_amount
        obj.pos = pos + vector(0, flutter, 0)

        # Tile sizes expand slightly as wings open.
        s = tile["size"] * (0.72 + 0.38 * open_amount)
        obj.size = vector(s, 0.018, s * 0.82)

        # Markings brighten in waves from body to edge.
        wave = 0.5 + 0.5 * math.sin(t * 3.2 - u * 3.0 + tile["phase"])
        active = language_energy * (0.35 + 0.65 * wave)
        obj.color = mix_color(tile["base"], GOLD, 0.18 * active * (1.0 - 0.45 * tile["edge"]))

    for bead in wing_outline:
        obj = bead["obj"]
        obj.pos = local_to_world(bead["side"], bead["u"], bead["v"], open_amount, 0.02)
        pulse = 0.5 + 0.5 * math.sin(t * 4.0 + bead["phase"])
        obj.radius = 0.026 + 0.018 * open_amount + 0.010 * pulse
        obj.color = mix_color(DARK, GOLD, 0.20 * open_amount * pulse)

    # Update glyph positions and pulse.
    for g in glyphs:
        side = g["side"]
        pos = local_to_world(side, g["u"], g["v"], open_amount, 0.055)
        pulse = 0.5 + 0.5 * math.sin(t * 3.6 + g["phase"] + g["u"] * 2.1)
        bright = language_energy * (pulse if glyph_pulse_enabled else 0.45)
        glyph_col = mix_color(g["color"], GOLD, 0.45 * bright)

        for k, item in enumerate(g["items"]):
            # Keep each glyph component's rough offset relative to glyph center.
            if isinstance(item, cylinder):
                # Store original offsets lazily.
                if not hasattr(item, "_base_axis"):
                    item._base_axis = vector(item.axis.x, item.axis.y, item.axis.z)
                    item._base_offset = item.pos - local_to_world(side, g["u"], g["v"], 0.0, 0.055)
                item.pos = pos + item._base_offset * (0.72 + 0.28 * open_amount)
                item.axis = item._base_axis * (0.70 + 0.30 * open_amount) * (1.0 + 0.10 * bright)
                item.radius = max(0.006, item.radius * 0.985 + (0.010 + 0.011 * bright) * 0.015)
                item.color = glyph_col
                item.opacity = 0.50 + 0.45 * open_amount
            elif isinstance(item, ring):
                if not hasattr(item, "_base_offset"):
                    item._base_offset = item.pos - local_to_world(side, g["u"], g["v"], 0.0, 0.055)
                    item._base_radius = item.radius
                item.pos = pos + item._base_offset * (0.72 + 0.28 * open_amount)
                item.radius = item._base_radius * (0.75 + 0.25 * open_amount) * (1.0 + 0.16 * bright)
                item.thickness = 0.009 + 0.010 * bright
                item.color = glyph_col
                item.opacity = 0.45 + 0.50 * open_amount
            elif isinstance(item, sphere):
                if not hasattr(item, "_base_offset"):
                    item._base_offset = item.pos - local_to_world(side, g["u"], g["v"], 0.0, 0.055)
                    item._base_radius = item.radius
                item.pos = pos + item._base_offset * (0.72 + 0.28 * open_amount)
                item.radius = item._base_radius * (0.75 + 0.25 * open_amount) * (1.0 + 0.18 * bright)
                item.color = mix_color(glyph_col, vector(1, 0.95, 0.55), 0.20 * bright)
                item.opacity = 0.48 + 0.50 * open_amount

    # Floating symbol streams orbit and rise like painted language.
    for item in symbol_streams:
        obj = item["obj"]
        if streams_enabled:
            item["angle"] += dt * item["speed"] * (0.35 + 0.65 * language_energy)
            y_wave = 0.23 * math.sin(t * 1.3 + item["phase"])
            obj.pos = vector(
                math.cos(item["angle"]) * item["rad"],
                item["base_y"] + y_wave + 0.18 * open_amount,
                math.sin(item["angle"]) * 0.38 - 0.25,
            )
            opacity = 0.12 + 0.55 * language_energy * (0.5 + 0.5 * math.sin(t * 2.4 + item["phase"]) ** 2)
            set_obj_opacity(obj, opacity)
            if isinstance(obj, sphere):
                obj.radius = 0.025 + 0.035 * opacity
            elif isinstance(obj, ring):
                obj.radius = 0.04 + 0.055 * opacity
                obj.thickness = 0.007 + 0.007 * opacity
            elif isinstance(obj, cylinder):
                obj.radius = 0.007 + 0.012 * opacity

    # Back-wall symbols echo the wing pulse.
    for i, glyph in enumerate(panel_symbols):
        p = 0.5 + 0.5 * math.sin(t * 2.1 + i * 0.75)
        glyph.color = mix_color(INK, GOLD, open_amount * 0.55 * p)
        glyph.radius = 0.012 + 0.012 * p * open_amount

    # Light beams brighten as the glyph language activates.
    for i, beam in enumerate(light_beams):
        beam.opacity = 0.12 + 0.15 * open_amount * (0.5 + 0.5 * math.sin(t * 1.9 + i))

    status.text = (
        f"Wing openness: {int(open_amount * 100)}%\n"
        f"Painted-language pulse: {int(language_energy * 100)}%\n"
        f"Glyph animation: {'on' if glyph_pulse_enabled else 'off'}\n"
        f"Symbol streams: {'on' if streams_enabled else 'off'}\n"
        f"Speed: {speed:.2f}x\n"
        "Space pause | U fold/unfold | G glyphs | S streams | R reset"
    )
