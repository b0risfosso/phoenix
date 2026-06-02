from vpython import *
import math
import random

# Wing Script Awakening
# A light-styled VPython simulation inspired by Baorisa hieroglyphica-like wing markings.
# The moth's still markings separate into glowing lines that move across the wings like an unknown alphabet.

scene = canvas(
    title="Wing Script Awakening",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0.25, 0),
)
scene.forward = vector(-0.25, -0.42, -1.0)
scene.range = 8.2
scene.caption = "\nWing Script Awakening: markings detach from the moth's wings and move like a living alphabet.\n"

# ---------- colors ----------
GROUND = vector(0.84, 0.91, 0.82)
WING_BASE = vector(0.82, 0.73, 0.55)
WING_EDGE = vector(0.34, 0.22, 0.12)
BODY = vector(0.23, 0.17, 0.12)
BODY_LIGHT = vector(0.42, 0.31, 0.21)
GLYPH_DARK = vector(0.19, 0.11, 0.07)
GLYPH_GLOW = vector(0.98, 0.69, 0.20)
PULSE = vector(0.25, 0.78, 0.94)
LEAF = vector(0.31, 0.63, 0.32)
FLOWER = vector(0.86, 0.62, 0.78)

# ---------- scene base ----------
ground = box(pos=vector(0, -1.05, 0), size=vector(16, 0.08, 11), color=GROUND)
perch = cylinder(pos=vector(-5.8, -0.78, -0.75), axis=vector(11.6, 0.08, 1.5), radius=0.07, color=vector(0.50, 0.34, 0.18))

# scattered leaves and small flowers
for i in range(36):
    x = random.uniform(-7.2, 7.2)
    z = random.uniform(-5.0, 4.8)
    y = -0.98 + random.uniform(0, 0.025)
    leaf = ellipsoid(pos=vector(x, y, z), length=random.uniform(0.22, 0.42), height=0.018,
                     width=random.uniform(0.07, 0.16), color=LEAF)
    leaf.rotate(angle=random.uniform(0, math.pi), axis=vector(0, 1, 0))

for i in range(14):
    flower_center = sphere(pos=vector(random.uniform(-7, 7), -0.91, random.uniform(-4.5, 4.3)), radius=0.035,
                           color=vector(0.96, 0.75, 0.25))
    for k in range(5):
        ang = 2 * math.pi * k / 5
        petal = ellipsoid(pos=flower_center.pos + vector(0.07 * math.cos(ang), 0.01, 0.07 * math.sin(ang)),
                          length=0.09, height=0.025, width=0.045, color=FLOWER)
        petal.rotate(angle=ang, axis=vector(0, 1, 0))

# ---------- moth structure ----------
body = ellipsoid(pos=vector(0, 0.0, 0), length=0.70, height=2.25, width=0.62, color=BODY)
head = sphere(pos=vector(0, 1.33, 0), radius=0.34, color=BODY_LIGHT)
thorax = ellipsoid(pos=vector(0, 0.40, 0), length=0.55, height=0.72, width=0.72, color=BODY_LIGHT)
abdomen = ellipsoid(pos=vector(0, -0.60, 0), length=0.45, height=1.18, width=0.52, color=BODY)

# eyes and antennae
eye_l = sphere(pos=vector(-0.16, 1.42, -0.26), radius=0.055, color=vector(0.04, 0.03, 0.02))
eye_r = sphere(pos=vector(0.16, 1.42, -0.26), radius=0.055, color=vector(0.04, 0.03, 0.02))
antenna_l = curve(pos=[vector(-0.10, 1.58, -0.05), vector(-0.52, 2.10, -0.12), vector(-0.95, 2.28, -0.06)],
                  radius=0.018, color=BODY)
antenna_r = curve(pos=[vector(0.10, 1.58, -0.05), vector(0.52, 2.10, -0.12), vector(0.95, 2.28, -0.06)],
                  radius=0.018, color=BODY)

# wing surfaces are flattened ellipsoids, tilted and animated by changing position/axis via rotation
left_wing = ellipsoid(pos=vector(-1.65, 0.18, 0.05), length=3.35, height=4.45, width=0.075, color=WING_BASE, opacity=0.92)
right_wing = ellipsoid(pos=vector(1.65, 0.18, 0.05), length=3.35, height=4.45, width=0.075, color=WING_BASE, opacity=0.92)
left_wing.rotate(angle=0.42, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
right_wing.rotate(angle=-0.42, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))

# add boundary curves around each wing using parametric ellipse outlines
left_outline = curve(radius=0.025, color=WING_EDGE)
right_outline = curve(radius=0.025, color=WING_EDGE)
left_outline_points = []
right_outline_points = []
for i in range(145):
    a = 2 * math.pi * i / 144
    # local ellipse coordinates before side tilt
    lx = -1.65 + 1.55 * math.cos(a)
    ly = 0.18 + 2.05 * math.sin(a)
    rx = 1.65 + 1.55 * math.cos(a)
    ry = 0.18 + 2.05 * math.sin(a)
    # taper inner side to give a wing-like silhouette
    if lx > -1.65:
        ly *= 0.96
    if rx < 1.65:
        ry *= 0.96
    left_outline_points.append(vector(lx, ly, -0.02))
    right_outline_points.append(vector(rx, ry, -0.02))
left_outline.append(left_outline_points)
right_outline.append(right_outline_points)
left_outline.rotate(angle=0.42, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
right_outline.rotate(angle=-0.42, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))

# ---------- glyph markings ----------
# A glyph stroke is a small curve on a wing. It starts dark and still, then glows and detaches into a moving script line.
class GlyphStroke:
    def __init__(self, side, local_anchor, shape_id, delay):
        self.side = side
        self.anchor = local_anchor
        self.shape_id = shape_id
        self.delay = delay
        self.detached = False
        self.progress = 0.0
        self.speed = random.uniform(0.0019, 0.0037)
        self.float_phase = random.uniform(0, 2 * math.pi)
        self.float_amp = random.uniform(0.05, 0.16)
        self.base_points = self.make_shape()
        self.curve = curve(pos=self.transformed_points(0.0, attached=True), radius=random.uniform(0.014, 0.024), color=GLYPH_DARK)
        self.halo = curve(pos=self.transformed_points(0.0, attached=True), radius=0.006, color=GLYPH_GLOW, opacity=0.0, emissive=True)

    def make_shape(self):
        pts = []
        if self.shape_id == 0:  # hook
            for k in range(8):
                u = k / 7
                pts.append(vector(0.00 + 0.18 * math.sin(u * math.pi), 0.30 * (u - 0.5), 0))
            for k in range(6):
                u = k / 5
                pts.append(vector(0.18 - 0.21 * u, 0.15 + 0.10 * math.sin(u * math.pi), 0))
        elif self.shape_id == 1:  # broken zigzag
            pts = [vector(-0.17, -0.18, 0), vector(0.12, -0.06, 0), vector(-0.08, 0.06, 0), vector(0.18, 0.20, 0)]
        elif self.shape_id == 2:  # small spiral-ish stroke
            for k in range(16):
                u = k / 15
                r = 0.20 * (1 - 0.55 * u)
                ang = 1.4 * math.pi * u
                pts.append(vector(r * math.cos(ang), r * math.sin(ang), 0))
        elif self.shape_id == 3:  # letter-like fork
            pts = [vector(0, -0.23, 0), vector(0, 0.22, 0), vector(0.16, 0.05, 0), vector(0, 0.02, 0), vector(-0.15, 0.14, 0)]
        else:  # eye mark
            for k in range(18):
                a = 2 * math.pi * k / 17
                pts.append(vector(0.20 * math.cos(a), 0.10 * math.sin(a), 0))
        return pts

    def wing_transform(self, p, wing_angle):
        # local anchor already in side wing coordinates. Rotate around body center to match wing tilt.
        x = self.anchor.x + p.x
        y = self.anchor.y + p.y
        v = vector(x, y, -0.13)
        ca, sa = math.cos(wing_angle), math.sin(wing_angle)
        origin = vector(0, 0.25, 0)
        q = v - origin
        return origin + vector(q.x * ca - q.y * sa, q.x * sa + q.y * ca, q.z)

    def transformed_points(self, t, attached=True):
        wing_angle = 0.42 * self.side + 0.055 * self.side * math.sin(2.2 * t)
        pts = []
        if attached:
            lift = vector(0, 0, 0)
            drift = vector(0, 0, 0)
        else:
            direction = vector(0.42 * self.side, 0.20 + 0.18 * math.sin(self.float_phase + t), -0.48)
            lift = direction * (self.progress * 1.65)
            drift = vector(0, self.float_amp * math.sin(4.0 * self.progress + self.float_phase), 0)
        for p in self.base_points:
            pts.append(self.wing_transform(p, wing_angle) + lift + drift)
        return pts

    def update(self, t):
        glow = max(0.0, min(1.0, (t - self.delay) / 2.2))
        if t > self.delay + 1.2:
            self.detached = True
        if self.detached:
            self.progress += self.speed * (1.0 + 0.7 * math.sin(t + self.float_phase))
            if self.progress > 1.0:
                self.progress = 0.0
                self.detached = False
                self.delay = t + random.uniform(1.0, 3.5)
        attached = not self.detached
        pts = self.transformed_points(t, attached=attached)
        self.curve.clear()
        self.curve.append(pts)
        self.halo.clear()
        self.halo.append(pts)
        self.curve.color = GLYPH_DARK * (1 - 0.35 * glow) + GLYPH_GLOW * (0.35 * glow)
        self.halo.opacity = 0.12 + 0.55 * glow if self.detached else 0.06 + 0.18 * glow
        self.halo.radius = 0.010 + 0.012 * glow

# anchors are placed on left and right wings as if they were hieroglyphic markings
strokes = []
anchors_left = [
    vector(-1.75, 1.58, 0), vector(-2.20, 0.82, 0), vector(-1.22, 0.94, 0), vector(-2.52, 0.10, 0),
    vector(-1.50, 0.08, 0), vector(-2.10, -0.64, 0), vector(-0.92, -0.58, 0), vector(-1.78, -1.32, 0),
    vector(-2.75, 1.08, 0), vector(-0.92, 1.60, 0), vector(-2.58, -1.05, 0), vector(-1.16, -1.50, 0)
]
for i, a in enumerate(anchors_left):
    strokes.append(GlyphStroke(-1, a, i % 5, delay=0.35 * i))
    mirror = vector(-a.x, a.y, 0)
    strokes.append(GlyphStroke(1, mirror, (i + 2) % 5, delay=0.35 * i + 0.6))

# Larger still blotches beneath the script, to make the wing look richly patterned.
blotches = []
for side in [-1, 1]:
    for i in range(15):
        px = side * random.uniform(0.72, 3.0)
        py = random.uniform(-1.55, 1.75)
        if abs(px) < 0.9 and abs(py) < 0.55:
            continue
        m = ellipsoid(pos=vector(px, py, -0.115), length=random.uniform(0.12, 0.38), height=random.uniform(0.035, 0.10), width=0.018,
                      color=vector(0.25, 0.15, 0.08), opacity=0.58)
        m.rotate(angle=side * 0.42 + random.uniform(-0.8, 0.8), axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
        blotches.append(m)

# ---------- signal wave arcs crossing both wings ----------
class WingPulse:
    def __init__(self, delay, side):
        self.delay = delay
        self.side = side
        self.progress = 0.0
        self.curve = curve(pos=[vector(0, 0, -0.22), vector(0.01, 0, -0.22)], radius=0.018, color=PULSE, emissive=True, opacity=0.0)

    def update(self, t):
        if t < self.delay:
            self.curve.opacity = 0.0
            return
        self.progress = ((t - self.delay) * 0.18) % 1.0
        y = -1.75 + 3.65 * self.progress
        pts = []
        for k in range(34):
            u = k / 33
            x = self.side * (0.45 + 2.55 * u)
            wave = 0.12 * math.sin(8.0 * u + 7.0 * self.progress)
            pts.append(vector(x, y + wave, -0.24))
        self.curve.clear()
        self.curve.append(pts)
        self.curve.opacity = max(0.0, 0.55 * math.sin(math.pi * self.progress))

wing_pulses = [WingPulse(0.5, -1), WingPulse(1.2, 1), WingPulse(2.4, -1), WingPulse(3.1, 1)]

# ---------- labels ----------
title_label = label(pos=vector(0, 3.05, 0), text="Wing Script Awakening", height=22, box=False, color=vector(0.22, 0.17, 0.11))
status_label = label(pos=vector(0, -2.8, 0), text="still pattern → glowing glyphs → moving alphabet", height=14, box=False, color=vector(0.30, 0.24, 0.15))

# ---------- animation loop ----------
t = 0.0
while True:
    rate(60)
    t += 1 / 60

    # gentle living wing motion: rotate wings and outlines by tiny incremental angles
    flap_delta = 0.0045 * math.sin(2.2 * t)
    left_wing.rotate(angle=flap_delta, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
    right_wing.rotate(angle=-flap_delta, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
    left_outline.rotate(angle=flap_delta, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
    right_outline.rotate(angle=-flap_delta, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))
    for b in blotches:
        side = -1 if b.pos.x < 0 else 1
        b.rotate(angle=side * flap_delta * 0.65, axis=vector(0, 0, 1), origin=vector(0, 0.25, 0))

    # body breathing shimmer
    thorax.size = vector(0.55 + 0.025 * math.sin(3.0 * t), 0.72 + 0.030 * math.sin(3.0 * t), 0.72 + 0.030 * math.sin(3.0 * t))
    abdomen.pos.y = -0.60 + 0.025 * math.sin(2.0 * t + 1.1)

    for s in strokes:
        s.update(t)

    for p in wing_pulses:
        p.update(t)

    # status text changes as the system cycles through awakening stages
    phase = int((t / 5.0) % 3)
    if phase == 0:
        status_label.text = "the markings hold still, like ink pressed into the wings"
    elif phase == 1:
        status_label.text = "gold light separates the dark strokes into moving glyphs"
    else:
        status_label.text = "the wing script travels outward like an unknown alphabet"
