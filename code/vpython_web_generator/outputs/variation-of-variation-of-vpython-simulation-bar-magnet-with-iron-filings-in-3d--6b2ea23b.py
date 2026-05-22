from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# VPython Variation:
# Two like-pole bar magnets with a central magnetic null zone.
# A charged particle is launched slowly through that null zone,
# so q(v x B) produces only a small magnetic deflection.
# ------------------------------------------------------------

scene = canvas(
    title="Slow Charged Particle Through a Magnetic Null Zone",
    width=1200,
    height=760,
    background=vector(0.96, 0.985, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-6.4, -3.1, -6.2)
scene.up = vector(0, 1, 0)
scene.range = 7.0

HELP_TEXT = """
Controls:
  Arrow keys : rotate both magnets as one rigid pair
  Q / E      : roll pair about its own axis
  W / S      : pitch pair
  A          : toggle very gentle auto-rotation
  P / Space  : pause / resume
  G          : relaunch the charged particle through the null zone
  + / -      : increase / decrease particle launch speed
  R          : reset filings and charged-particle run
  D          : scatter filings
  O          : small orbit burst for filings
  T          : toggle charged-particle trail
  C          : clear charged-particle trail
  H          : hide/show help

Variation focus:
  The two inner pole faces are both NORTH, so the magnetic field cancels near
  the center.  A positive charged particle is launched slowly through this
  central null zone.  Because both B and speed are small there, q(v x B) causes
  only a little deflection; the bright path remains close to the pale straight
  reference line.
"""
scene.caption = HELP_TEXT

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

FPS = 60
DT = 1.0 / FPS

MAGNET_LENGTH = 2.65
MAGNET_HEIGHT = 0.52
MAGNET_WIDTH = 0.72
CAP_THICKNESS = 0.16
CENTER_GAP = 1.22

BOUND = vector(6.0, 3.05, 3.75)

PARTICLE_COUNT = 75
FILING_LENGTH = 0.22
FILING_RADIUS = 0.026

FIELD_LINE_COUNT = 32
FIELD_LINE_STEPS = 130
FIELD_LINE_STEP_SIZE = 0.074

NULL_RADIUS = 0.72
NULL_RING_RADIUS = 0.88

CHARGED_SPEED_BASE = 0.46
CHARGED_Q_OVER_M = 0.62
LORENTZ_SCALE = 0.23

# ------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------

def clamp(x, a, b):
    return max(a, min(b, x))


def rand_range(a, b):
    return a + random.random() * (b - a)


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-9:
        return fallback
    return v / m


def limit_vec(v, max_len):
    m = mag(v)
    if m > max_len and m > 1e-9:
        return v * (max_len / m)
    return v


def random_unit_vector():
    z = rand_range(-1, 1)
    t = rand_range(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), z, r * math.sin(t))


def random_perpendicular(axis):
    a = safe_norm(axis)
    r = random_unit_vector()
    p = r - dot(r, a) * a
    return safe_norm(p, vector(0, 1, 0))


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def place_oriented_box(obj, center, axis_dir, length_value, height_value, width_value, up_dir):
    """Place a VPython box without relying on size + unit axis ambiguity.

    VPython boxes can appear collapsed or stacked if `size` and a short/unit
    `axis` are mixed during repeated redraws.  This helper always sets the
    visible center, direction, length, height, and width explicitly.
    """
    u = safe_norm(axis_dir, vector(1, 0, 0))
    v = up_dir - dot(up_dir, u) * u
    v = safe_norm(v, vector(0, 1, 0))
    obj.pos = center
    obj.axis = u * length_value
    obj.up = v
    obj.length = length_value
    obj.height = height_value
    obj.width = width_value


# ------------------------------------------------------------
# Light Environment
# ------------------------------------------------------------

container = box(
    pos=vector(0, 0, 0),
    size=vector(2 * BOUND.x, 2 * BOUND.y, 2 * BOUND.z),
    color=vector(0.72, 0.86, 1.0),
    opacity=0.055,
)

for x in [i * 0.5 for i in range(-12, 13)]:
    curve(
        pos=[vector(x, -BOUND.y, -BOUND.z), vector(x, -BOUND.y, BOUND.z)],
        color=vector(0.80, 0.86, 0.90),
        radius=0.003,
    )
for z in [i * 0.5 for i in range(-8, 9)]:
    curve(
        pos=[vector(-BOUND.x, -BOUND.y, z), vector(BOUND.x, -BOUND.y, z)],
        color=vector(0.80, 0.86, 0.90),
        radius=0.003,
    )

title_label = label(
    pos=vector(0, 3.55, 0),
    text="Slow Charged Particle Through the Central Magnetic Null Zone",
    height=18,
    box=False,
    color=vector(0.10, 0.13, 0.16),
)

null_label = label(
    pos=vector(0, 1.45, 0),
    text="central null zone\nB ≈ 0",
    height=12,
    box=True,
    border=5,
    color=vector(0.35, 0.08, 0.48),
    background=vector(1.0, 0.94, 1.0),
    opacity=0.65,
)

particle_label = label(
    pos=vector(3.9, 2.7, 2.3),
    text="charged particle status",
    height=12,
    box=True,
    border=6,
    color=vector(0.10, 0.12, 0.14),
    background=vector(1.0, 0.98, 0.82),
    opacity=0.75,
)

state_label = label(
    pos=vector(-5.15, 3.05, -3.0),
    text="state",
    height=11,
    box=True,
    border=5,
    color=vector(0.10, 0.12, 0.14),
    background=vector(0.96, 0.99, 1.0),
    opacity=0.75,
)

local_light(pos=vector(0, 5, 2), color=vector(0.75, 0.78, 0.84))
local_light(pos=vector(-4, 3, -4), color=vector(0.50, 0.58, 0.72))
local_light(pos=vector(4, 4, 3), color=vector(0.58, 0.54, 0.66))

# ------------------------------------------------------------
# Bar Magnets
# ------------------------------------------------------------

class MagnetPiece:
    def __init__(self, name, initial_pos=vector(0, 0, 0), initial_u=vector(1, 0, 0), initial_v=vector(0, 1, 0)):
        self.name = name
        self.pos = vector(0, 0, 0)
        self.u = vector(1, 0, 0)   # south -> north for THIS magnet
        self.v = vector(0, 1, 0)
        self.w = vector(0, 0, 1)
        self.set_frame(initial_pos, initial_u, initial_v)

        # Create the boxes with explicit length/height/width.  Do not use
        # `size=...` combined with a unit `axis`; that was the source of the
        # apparent overlap/collapse in some VPython renderers.
        half_len = MAGNET_LENGTH * 0.5
        self.south_half = box(
            pos=self.pos - self.u * (MAGNET_LENGTH * 0.25),
            axis=self.u * half_len,
            up=self.v,
            length=half_len,
            height=MAGNET_HEIGHT,
            width=MAGNET_WIDTH,
            color=vector(0.16, 0.35, 0.96),
            shininess=0.70,
        )
        self.north_half = box(
            pos=self.pos + self.u * (MAGNET_LENGTH * 0.25),
            axis=self.u * half_len,
            up=self.v,
            length=half_len,
            height=MAGNET_HEIGHT,
            width=MAGNET_WIDTH,
            color=vector(0.96, 0.16, 0.12),
            shininess=0.70,
        )
        self.center_band = box(
            pos=self.pos,
            axis=self.u * 0.07,
            up=self.v,
            length=0.07,
            height=MAGNET_HEIGHT * 1.07,
            width=MAGNET_WIDTH * 1.07,
            color=vector(0.98, 0.96, 0.82),
            shininess=0.65,
        )
        self.north_cap = cylinder(
            pos=self.north_world(),
            axis=self.u * CAP_THICKNESS,
            radius=0.46,
            color=vector(1.0, 0.28, 0.20),
            shininess=0.9,
        )
        self.south_cap = cylinder(
            pos=self.south_world(),
            axis=-self.u * CAP_THICKNESS,
            radius=0.46,
            color=vector(0.14, 0.36, 1.0),
            shininess=0.9,
        )
        self.n_label = label(
            pos=self.north_world() + self.v * 0.66,
            text="N",
            height=20,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.95, 0.10, 0.08),
            opacity=0.90,
        )
        self.s_label = label(
            pos=self.south_world() + self.v * 0.66,
            text="S",
            height=20,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.08, 0.18, 0.95),
            opacity=0.90,
        )
        self.redraw()

    def set_frame(self, pos, u, v):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.u = safe_norm(u, vector(1, 0, 0))
        self.v = v - dot(v, self.u) * self.u
        self.v = safe_norm(self.v, vector(0, 1, 0))
        self.w = safe_norm(cross(self.u, self.v), vector(0, 0, 1))
        self.v = safe_norm(cross(self.w, self.u), vector(0, 1, 0))

    def redraw(self):
        half_len = MAGNET_LENGTH * 0.5

        # Explicit endpoint/midpoint placement prevents the two bar magnets from
        # ever being drawn at the same center, even while the pair is rotating.
        south_center = self.pos - self.u * (MAGNET_LENGTH * 0.25)
        north_center = self.pos + self.u * (MAGNET_LENGTH * 0.25)

        place_oriented_box(
            self.south_half,
            south_center,
            self.u,
            half_len,
            MAGNET_HEIGHT,
            MAGNET_WIDTH,
            self.v,
        )
        place_oriented_box(
            self.north_half,
            north_center,
            self.u,
            half_len,
            MAGNET_HEIGHT,
            MAGNET_WIDTH,
            self.v,
        )
        place_oriented_box(
            self.center_band,
            self.pos,
            self.u,
            0.07,
            MAGNET_HEIGHT * 1.07,
            MAGNET_WIDTH * 1.07,
            self.v,
        )

        self.north_cap.pos = self.north_world()
        self.north_cap.axis = self.u * CAP_THICKNESS

        self.south_cap.pos = self.south_world()
        self.south_cap.axis = -self.u * CAP_THICKNESS

        self.n_label.pos = self.north_world() + self.v * 0.68
        self.s_label.pos = self.south_world() + self.v * 0.68

    def north_world(self):
        return self.pos + self.u * (MAGNET_LENGTH * 0.5)

    def south_world(self):
        return self.pos - self.u * (MAGNET_LENGTH * 0.5)

    def local_from_world(self, world):
        r = world - self.pos
        return vector(dot(r, self.u), dot(r, self.v), dot(r, self.w))

    def world_from_local(self, local):
        return self.pos + self.u * local.x + self.v * local.y + self.w * local.z

class RepellingMagnetPair:
    def __init__(self):
        self.pos = vector(0, 0, 0)
        self.u = vector(1, 0, 0)   # left magnet -> right magnet
        self.v = vector(0, 1, 0)
        self.w = vector(0, 0, 1)
        self.visuals_dirty = True
        self.spin_impulse = 0.0

        left_initial_center = self.pos - self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH * 0.5)
        right_initial_center = self.pos + self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH * 0.5)
        self.left = MagnetPiece("left", left_initial_center, self.u, self.v)
        self.right = MagnetPiece("right", right_initial_center, -self.u, self.v)

        self.axis_arrow = arrow(
            pos=self.pos - self.u * 1.10,
            axis=self.u * 2.20,
            shaftwidth=0.028,
            headwidth=0.12,
            headlength=0.18,
            color=vector(1.0, 0.76, 0.16),
            opacity=0.55,
        )
        self.repulse_left = arrow(
            pos=self.pos - self.u * 0.10,
            axis=-self.u * 0.48,
            shaftwidth=0.033,
            headwidth=0.14,
            headlength=0.17,
            color=vector(1.0, 0.30, 0.24),
            opacity=0.78,
        )
        self.repulse_right = arrow(
            pos=self.pos + self.u * 0.10,
            axis=self.u * 0.48,
            shaftwidth=0.033,
            headwidth=0.14,
            headlength=0.17,
            color=vector(1.0, 0.30, 0.24),
            opacity=0.78,
        )

        self.null_sphere = sphere(
            pos=self.pos,
            radius=NULL_RADIUS,
            color=vector(0.94, 0.62, 1.0),
            opacity=0.15,
            emissive=True,
            shininess=0.05,
        )
        self.null_ring_u = ring(
            pos=self.pos,
            axis=self.u,
            radius=NULL_RING_RADIUS,
            thickness=0.014,
            color=vector(0.78, 0.20, 1.0),
            opacity=0.58,
        )
        self.null_ring_v = ring(
            pos=self.pos,
            axis=self.v,
            radius=NULL_RING_RADIUS * 0.95,
            thickness=0.012,
            color=vector(1.0, 0.55, 0.92),
            opacity=0.45,
        )
        self.null_ring_w = ring(
            pos=self.pos,
            axis=self.w,
            radius=NULL_RING_RADIUS * 0.95,
            thickness=0.012,
            color=vector(0.55, 0.58, 1.0),
            opacity=0.45,
        )

        self.update_visuals()

    def orthonormalize(self):
        self.u = safe_norm(self.u, vector(1, 0, 0))
        self.v = self.v - dot(self.v, self.u) * self.u
        self.v = safe_norm(self.v, vector(0, 1, 0))
        self.w = safe_norm(cross(self.u, self.v), vector(0, 0, 1))
        self.v = safe_norm(cross(self.w, self.u), vector(0, 1, 0))

    def rotate_by(self, axis, angle):
        if abs(angle) < 1e-8:
            return
        axis = safe_norm(axis, vector(0, 1, 0))
        self.u = self.u.rotate(angle=angle, axis=axis)
        self.v = self.v.rotate(angle=angle, axis=axis)
        self.w = self.w.rotate(angle=angle, axis=axis)
        self.orthonormalize()
        self.spin_impulse += abs(angle)
        self.update_logical_frames()
        self.visuals_dirty = True

    def left_center(self):
        return self.pos - self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH * 0.5)

    def right_center(self):
        return self.pos + self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH * 0.5)

    def left_north_world(self):
        return self.pos - self.u * (CENTER_GAP * 0.5)

    def right_north_world(self):
        return self.pos + self.u * (CENTER_GAP * 0.5)

    def left_south_world(self):
        return self.pos - self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH)

    def right_south_world(self):
        return self.pos + self.u * (CENTER_GAP * 0.5 + MAGNET_LENGTH)

    def pair_local_from_world(self, world):
        r = world - self.pos
        return vector(dot(r, self.u), dot(r, self.v), dot(r, self.w))

    def world_from_pair_local(self, local):
        return self.pos + self.u * local.x + self.v * local.y + self.w * local.z

    def null_metric(self, point):
        local = self.pair_local_from_world(point)
        return math.sqrt(
            (local.x / max(CENTER_GAP * 0.58, 0.001)) ** 2
            + (local.y / NULL_RING_RADIUS) ** 2
            + (local.z / NULL_RING_RADIUS) ** 2
        )

    def null_outward_force(self, point):
        local = self.pair_local_from_world(point)
        metric = self.null_metric(point)
        if metric > 1.45:
            return vector(0, 0, 0)

        sideways = self.v * local.y + self.w * local.z
        if mag(sideways) < 0.06:
            sideways = random_perpendicular(self.u) * 0.08
        direction = safe_norm(sideways, self.v)

        influence = (1.0 - clamp(metric / 1.45, 0, 1)) ** 2
        return direction * 5.5 * influence + self.u * local.x * 0.45 * influence

    def update_logical_frames(self):
        self.left.set_frame(self.left_center(), self.u, self.v)
        self.right.set_frame(self.right_center(), -self.u, self.v)

    def update_visuals(self):
        self.update_logical_frames()
        self.left.redraw()
        self.right.redraw()

        self.axis_arrow.pos = self.pos - self.u * 1.10
        self.axis_arrow.axis = self.u * 2.20

        self.repulse_left.pos = self.pos - self.u * 0.10
        self.repulse_left.axis = -self.u * 0.48
        self.repulse_right.pos = self.pos + self.u * 0.10
        self.repulse_right.axis = self.u * 0.48

        pulse = 1.0 + 0.045 * math.sin(time.time() * 2.0)
        self.null_sphere.pos = self.pos
        self.null_sphere.radius = NULL_RADIUS * pulse

        self.null_ring_u.pos = self.pos
        self.null_ring_u.axis = self.u
        self.null_ring_u.radius = NULL_RING_RADIUS * pulse

        self.null_ring_v.pos = self.pos
        self.null_ring_v.axis = self.v
        self.null_ring_v.radius = NULL_RING_RADIUS * 0.95 * pulse

        self.null_ring_w.pos = self.pos
        self.null_ring_w.axis = self.w
        self.null_ring_w.radius = NULL_RING_RADIUS * 0.95 * pulse

        null_label.pos = self.pos + self.v * 1.43 + self.w * 0.08
        self.visuals_dirty = False

    def decay_spin_meter(self):
        self.spin_impulse *= 0.90


magnet = RepellingMagnetPair()

# ------------------------------------------------------------
# Magnetic Field Model
# ------------------------------------------------------------

def magnetic_field_at(point):
    # Magnetic pole approximation:
    # north poles are sources, south poles are sinks.
    poles = [
        (magnet.left_north_world(), 1.0),
        (magnet.right_north_world(), 1.0),
        (magnet.left_south_world(), -1.0),
        (magnet.right_south_world(), -1.0),
    ]

    b = vector(0, 0, 0)
    for pos, strength in poles:
        r = point - pos
        d = max(mag(r), 0.24)
        b += strength * r / (d ** 3)

    # Internal return-field hint inside magnet bodies.
    for piece in (magnet.left, magnet.right):
        local = piece.local_from_world(point)
        if (
            abs(local.x) < MAGNET_LENGTH * 0.5
            and abs(local.y) < MAGNET_HEIGHT
            and abs(local.z) < MAGNET_WIDTH
        ):
            b += -piece.u * 0.38

    # Gentle outward shaping near the N-N gap to make the null/bending region visible.
    local = magnet.pair_local_from_world(point)
    metric = magnet.null_metric(point)
    if metric < 1.40:
        radial = magnet.v * local.y + magnet.w * local.z
        if mag(radial) > 0.05:
            influence = (1.0 - clamp(metric / 1.40, 0, 1)) ** 2
            b += safe_norm(radial, magnet.v) * 1.15 * influence
            b += magnet.u * local.x * 0.23 * influence

    return limit_vec(b, 18.0)


def magnetic_strength(point):
    return mag(magnetic_field_at(point))


def field_gradient(point):
    eps = 0.23
    bx1 = magnetic_strength(point + vector(eps, 0, 0))
    bx0 = magnetic_strength(point - vector(eps, 0, 0))
    by1 = magnetic_strength(point + vector(0, eps, 0))
    by0 = magnetic_strength(point - vector(0, eps, 0))
    bz1 = magnetic_strength(point + vector(0, 0, eps))
    bz0 = magnetic_strength(point - vector(0, 0, eps))
    return limit_vec(vector(bx1 - bx0, by1 - by0, bz1 - bz0) / (2 * eps), 14.0)


# ------------------------------------------------------------
# Field Lines
# ------------------------------------------------------------

class FieldLineSystem:
    def __init__(self):
        self.lines = []
        self.seed_phases = []
        self.seed_layers = []
        self.seed_side = []

        for i in range(FIELD_LINE_COUNT):
            phase = 2 * math.pi * i / FIELD_LINE_COUNT
            layer = i % 3
            side = -1 if i % 2 == 0 else 1
            self.seed_phases.append(phase)
            self.seed_layers.append(layer)
            self.seed_side.append(side)

            c = curve(
                pos=[vector(0, 0, 0) for _ in range(FIELD_LINE_STEPS)],
                radius=0.016 if layer != 1 else 0.012,
                color=vector(0.12, 0.70, 1.0) if side < 0 else vector(1.0, 0.66, 0.18),
                emissive=True,
                opacity=0.74,
            )
            self.lines.append(c)

        self.update()

    def generate_line_points(self, phase, layer, side):
        ring_dir = math.cos(phase) * magnet.v + math.sin(phase) * magnet.w
        radius = 0.18 + 0.15 * layer

        if side < 0:
            p = magnet.left_north_world() + magnet.u * 0.06 + ring_dir * radius
        else:
            p = magnet.right_north_world() - magnet.u * 0.06 + ring_dir * radius

        pts = []
        last_good = p

        for step in range(FIELD_LINE_STEPS):
            pts.append(p)

            if magnet.null_metric(p) < 0.96:
                p += safe_norm(ring_dir, magnet.v) * FIELD_LINE_STEP_SIZE * 1.9

            b = magnetic_field_at(p)
            d = safe_norm(b, ring_dir)
            p = p + d * FIELD_LINE_STEP_SIZE
            last_good = p

            if step > 35:
                if mag(p - magnet.left_south_world()) < 0.34 + 0.04 * layer:
                    last_good = magnet.left_south_world() + ring_dir * 0.10
                    break
                if mag(p - magnet.right_south_world()) < 0.34 + 0.04 * layer:
                    last_good = magnet.right_south_world() + ring_dir * 0.10
                    break

            if abs(p.x) > BOUND.x * 1.35 or abs(p.y) > BOUND.y * 1.45 or abs(p.z) > BOUND.z * 1.45:
                break

        while len(pts) < FIELD_LINE_STEPS:
            pts.append(last_good)
        return pts[:FIELD_LINE_STEPS]

    def update(self):
        for i, c in enumerate(self.lines):
            pts = self.generate_line_points(self.seed_phases[i], self.seed_layers[i], self.seed_side[i])
            for j, p in enumerate(pts):
                c.modify(j, pos=p)


field_lines = FieldLineSystem()

# ------------------------------------------------------------
# Iron Filings
# ------------------------------------------------------------

def inside_any_magnet_box(point, pad=0.24):
    for piece in (magnet.left, magnet.right):
        local = piece.local_from_world(point)
        if (
            abs(local.x) < MAGNET_LENGTH * 0.5 + pad
            and abs(local.y) < MAGNET_HEIGHT * 0.5 + pad
            and abs(local.z) < MAGNET_WIDTH * 0.5 + pad
        ):
            return True
    return False


def random_cloud_position():
    for _ in range(500):
        p = vector(
            rand_range(-BOUND.x * 0.86, BOUND.x * 0.86),
            rand_range(-BOUND.y * 0.78, BOUND.y * 0.78),
            rand_range(-BOUND.z * 0.82, BOUND.z * 0.82),
        )
        if inside_any_magnet_box(p, pad=0.42):
            continue
        if magnet.null_metric(p) < 1.12:
            continue
        return p

    angle = rand_range(0, 2 * math.pi)
    side = magnet.v * math.cos(angle) + magnet.w * math.sin(angle)
    return magnet.pos + side * rand_range(1.5, 2.8) + magnet.u * rand_range(-3.1, 3.1)


class FilingParticle:
    def __init__(self, idx):
        self.idx = idx
        self.center = random_cloud_position()
        self.vel = random_unit_vector() * rand_range(0.01, 0.07)
        self.dir = random_unit_vector()
        self.flow_sign = 1 if random.random() < 0.5 else -1

        self.body = cylinder(
            pos=self.center - self.dir * (FILING_LENGTH * 0.5),
            axis=self.dir * FILING_LENGTH,
            radius=FILING_RADIUS,
            color=vector(0.43, 0.45, 0.44),
            shininess=0.88,
        )
        self.tip_a = sphere(
            pos=self.center + self.dir * FILING_LENGTH * 0.52,
            radius=FILING_RADIUS * 1.10,
            color=vector(0.62, 0.64, 0.63),
            shininess=0.85,
        )
        self.tip_b = sphere(
            pos=self.center - self.dir * FILING_LENGTH * 0.52,
            radius=FILING_RADIUS * 1.10,
            color=vector(0.35, 0.37, 0.36),
            shininess=0.85,
        )
        self.update_visual()

    def reset(self):
        self.center = random_cloud_position()
        self.vel = random_unit_vector() * rand_range(0.01, 0.07)
        self.dir = random_unit_vector()
        self.flow_sign = 1 if random.random() < 0.5 else -1
        self.update_visual()

    def update_visual(self):
        self.dir = safe_norm(self.dir, vector(1, 0, 0))
        self.body.pos = self.center - self.dir * (FILING_LENGTH * 0.5)
        self.body.axis = self.dir * FILING_LENGTH
        self.tip_a.pos = self.center + self.dir * FILING_LENGTH * 0.52
        self.tip_b.pos = self.center - self.dir * FILING_LENGTH * 0.52

        if magnet.null_metric(self.center) < 1.18:
            self.body.color = vector(0.78, 0.44, 0.84)
            self.tip_a.color = vector(0.95, 0.66, 1.0)
            self.tip_b.color = vector(0.60, 0.32, 0.68)
        else:
            self.body.color = vector(0.43, 0.45, 0.44)
            self.tip_a.color = vector(0.62, 0.64, 0.63)
            self.tip_b.color = vector(0.35, 0.37, 0.36)

    def collide_with_bounds(self):
        p = self.center
        v = self.vel
        bounce = 0.64

        if p.x > BOUND.x:
            p.x = BOUND.x
            v.x = -abs(v.x) * bounce
        elif p.x < -BOUND.x:
            p.x = -BOUND.x
            v.x = abs(v.x) * bounce

        if p.y > BOUND.y:
            p.y = BOUND.y
            v.y = -abs(v.y) * bounce
        elif p.y < -BOUND.y:
            p.y = abs(p.y) * 0 - BOUND.y
            v.y = abs(v.y) * bounce

        if p.z > BOUND.z:
            p.z = BOUND.z
            v.z = -abs(v.z) * bounce
        elif p.z < -BOUND.z:
            p.z = -BOUND.z
            v.z = abs(v.z) * bounce

        self.center = p
        self.vel = v

    def collide_with_magnets(self):
        for piece in (magnet.left, magnet.right):
            local = piece.local_from_world(self.center)
            expanded = vector(
                MAGNET_LENGTH * 0.5 + 0.15,
                MAGNET_HEIGHT * 0.5 + 0.13,
                MAGNET_WIDTH * 0.5 + 0.13,
            )

            if abs(local.x) < expanded.x and abs(local.y) < expanded.y and abs(local.z) < expanded.z:
                px = expanded.x - abs(local.x)
                py = expanded.y - abs(local.y)
                pz = expanded.z - abs(local.z)

                if px <= py and px <= pz:
                    n = piece.u * (1 if local.x >= 0 else -1)
                elif py <= px and py <= pz:
                    n = piece.v * (1 if local.y >= 0 else -1)
                else:
                    n = piece.w * (1 if local.z >= 0 else -1)

                if magnet.null_metric(self.center) < 1.35:
                    n = safe_norm(n + magnet.null_outward_force(self.center), n)

                self.center += n * 0.085
                self.vel = self.vel - 1.25 * dot(self.vel, n) * n + n * 0.035

    def update(self, dt, external_force=vector(0, 0, 0)):
        b = magnetic_field_at(self.center)
        bdir = safe_norm(b, magnet.u)
        if dot(self.dir, bdir) < 0:
            bdir = -bdir
        self.dir = safe_norm(lerp_vec(self.dir, bdir, clamp(6.2 * dt, 0, 1)), self.dir)

        strength = mag(b)
        f_grad = field_gradient(self.center) * 0.020
        f_flow = bdir * (0.055 * self.flow_sign) * clamp(strength, 0, 2.8)
        f_noise = random_unit_vector() * 0.006
        f_null = magnet.null_outward_force(self.center) * 0.12

        self.vel += limit_vec(f_grad + f_flow + f_noise + f_null + external_force, 0.95) * dt
        self.vel *= 0.972
        self.vel = limit_vec(self.vel, 1.15)
        self.center += self.vel * dt

        if magnet.null_metric(self.center) < 0.60:
            push = safe_norm(magnet.null_outward_force(self.center), random_perpendicular(magnet.u))
            self.vel += push * 0.08
            self.center += push * 0.028

        self.collide_with_magnets()
        self.collide_with_bounds()
        self.update_visual()


particles = [FilingParticle(i) for i in range(PARTICLE_COUNT)]

# ------------------------------------------------------------
# Slow Charged Particle Through Null Zone
# ------------------------------------------------------------

class ChargedParticle:
    def __init__(self):
        self.speed_scale = 1.0
        self.q_over_m = CHARGED_Q_OVER_M
        self.trails_enabled = True
        self.start = vector(0, 0, 0)
        self.reference_dir = vector(0, 1, 0)
        self.initial_speed = CHARGED_SPEED_BASE
        self.pos = vector(0, 0, 0)
        self.vel = vector(0, 1, 0) * CHARGED_SPEED_BASE
        self.max_deflection = 0.0
        self.max_b_seen = 0.0
        self.in_null_time = 0.0
        self.finished_pause = 0.0

        self.reference_line = curve(
            pos=[vector(0, -2.9, 0), vector(0, 2.9, 0)],
            radius=0.010,
            color=vector(0.65, 0.78, 0.86),
            opacity=0.72,
        )
        self.null_tunnel = curve(
            pos=[vector(0, -NULL_RADIUS, 0), vector(0, NULL_RADIUS, 0)],
            radius=0.030,
            color=vector(1.0, 0.92, 0.30),
            opacity=0.45,
        )
        self.body = sphere(
            pos=self.pos,
            radius=0.115,
            color=vector(1.0, 0.84, 0.10),
            emissive=True,
            shininess=0.90,
            make_trail=True,
            trail_radius=0.020,
            trail_color=vector(1.0, 0.62, 0.06),
            retain=520,
        )
        self.velocity_arrow = arrow(
            pos=self.pos,
            axis=self.vel * 0.70,
            shaftwidth=0.030,
            headwidth=0.12,
            headlength=0.18,
            color=vector(1.0, 0.58, 0.05),
            opacity=0.85,
        )
        self.force_arrow = arrow(
            pos=self.pos,
            axis=vector(0, 0, 0),
            shaftwidth=0.025,
            headwidth=0.10,
            headlength=0.15,
            color=vector(0.15, 0.56, 1.0),
            opacity=0.82,
        )
        self.charge_label = label(
            pos=self.pos + vector(0, 0.28, 0),
            text="+q",
            height=13,
            box=False,
            color=vector(0.72, 0.38, 0.02),
        )
        self.reset(clear=True)

    def reset(self, clear=True):
        # Launch along the pair's v-axis through the central gap.
        # A tiny w-offset makes the Lorentz force measurable but still very small.
        self.reference_dir = safe_norm(magnet.v, vector(0, 1, 0))
        self.start = magnet.pos - self.reference_dir * 2.85 + magnet.w * 0.045
        self.pos = self.start
        self.initial_speed = CHARGED_SPEED_BASE * self.speed_scale
        self.vel = self.reference_dir * self.initial_speed
        self.max_deflection = 0.0
        self.max_b_seen = 0.0
        self.in_null_time = 0.0
        self.finished_pause = 0.0

        end = magnet.pos + self.reference_dir * 2.85 + magnet.w * 0.045
        self.reference_line.clear()
        self.reference_line.append(pos=self.start)
        self.reference_line.append(pos=end)

        tunnel_a = magnet.pos - self.reference_dir * NULL_RADIUS
        tunnel_b = magnet.pos + self.reference_dir * NULL_RADIUS
        self.null_tunnel.clear()
        self.null_tunnel.append(pos=tunnel_a)
        self.null_tunnel.append(pos=tunnel_b)

        self.body.pos = self.pos
        if clear:
            self.clear_trail()
        self.body.make_trail = self.trails_enabled
        self.update_visual(vector(0, 0, 0))

    def clear_trail(self):
        try:
            self.body.clear_trail()
        except Exception:
            pass

    def set_trails(self, enabled):
        self.trails_enabled = enabled
        self.body.make_trail = enabled
        if not enabled:
            self.clear_trail()

    def line_deflection(self):
        along = dot(self.pos - self.start, self.reference_dir)
        closest = self.start + self.reference_dir * along
        return mag(self.pos - closest)

    def distance_along_reference(self):
        return dot(self.pos - self.start, self.reference_dir)

    def update_visual(self, force):
        self.body.pos = self.pos
        self.velocity_arrow.pos = self.pos
        self.velocity_arrow.axis = safe_norm(self.vel, self.reference_dir) * (0.36 + 0.55 * mag(self.vel))

        self.force_arrow.pos = self.pos
        if mag(force) > 1e-8:
            self.force_arrow.axis = safe_norm(force) * clamp(mag(force) * 2.8, 0.04, 0.55)
        else:
            self.force_arrow.axis = vector(0, 0, 0)

        self.charge_label.pos = self.pos + magnet.v * 0.30
        particle_label.pos = self.pos + magnet.u * 1.20 + magnet.v * 0.58 + magnet.w * 0.55

    def update(self, dt):
        if self.finished_pause > 0:
            self.finished_pause -= dt
            if self.finished_pause <= 0:
                self.reset(clear=True)
            else:
                self.update_visual(vector(0, 0, 0))
            return

        b = magnetic_field_at(self.pos)
        force = self.q_over_m * cross(self.vel, b) * LORENTZ_SCALE

        # A charged particle in a magnetic field changes direction, not speed.
        # The speed is deliberately slow, so even outside the exact null point
        # the sideways acceleration is small.
        self.vel += force * dt
        if mag(self.vel) > 1e-9:
            self.vel = safe_norm(self.vel, self.reference_dir) * self.initial_speed

        self.pos += self.vel * dt

        self.max_b_seen = max(self.max_b_seen, mag(b))
        deflection = self.line_deflection()
        self.max_deflection = max(self.max_deflection, deflection)

        if magnet.null_metric(self.pos) < 1.0:
            self.in_null_time += dt

        if self.distance_along_reference() > 5.70 or abs(self.pos.x) > BOUND.x or abs(self.pos.y) > BOUND.y or abs(self.pos.z) > BOUND.z:
            self.finished_pause = 1.0

        self.update_visual(force)


charged = ChargedParticle()

# ------------------------------------------------------------
# Actions and Controls
# ------------------------------------------------------------

paused = False
auto_rotate = False
show_help = True
frame_counter = 0
keys_down = set()


def scatter_filings():
    for p in particles:
        p.reset()


def orbit_burst(clockwise=True, strength=0.55):
    sign = 1 if clockwise else -1
    for p in particles:
        r = p.center - magnet.pos
        tangent = cross(magnet.u, r)
        if mag(tangent) < 0.10:
            tangent = cross(vector(0, 1, 0), r)
        p.vel += safe_norm(tangent, random_unit_vector()) * sign * rand_range(0.10, strength)


def reset_all():
    scatter_filings()
    charged.reset(clear=True)
    field_lines.update()


def on_keydown(evt):
    global paused, auto_rotate, show_help

    k = evt.key
    keys_down.add(k)

    if k in (" ", "p"):
        paused = not paused
    elif k == "a":
        auto_rotate = not auto_rotate
    elif k == "g":
        charged.reset(clear=True)
    elif k in ("+", "="):
        charged.speed_scale = clamp(charged.speed_scale * 1.18, 0.35, 3.00)
        charged.reset(clear=True)
    elif k in ("-", "_"):
        charged.speed_scale = clamp(charged.speed_scale / 1.18, 0.35, 3.00)
        charged.reset(clear=True)
    elif k == "r":
        reset_all()
    elif k == "d":
        scatter_filings()
    elif k == "o":
        orbit_burst(clockwise=random.random() < 0.5)
    elif k == "t":
        charged.set_trails(not charged.trails_enabled)
    elif k == "c":
        charged.clear_trail()
    elif k == "h":
        show_help = not show_help
        scene.caption = HELP_TEXT if show_help else ""


def on_keyup(evt):
    k = evt.key
    if k in keys_down:
        keys_down.remove(k)


scene.bind("keydown", on_keydown)
scene.bind("keyup", on_keyup)


def apply_human_controls():
    # Controls modify the logical rigid-pair frame first.  Visible objects are
    # redrawn once per frame, avoiding repeated partial updates or overlap flicker.
    amount = 0.030
    if "left" in keys_down:
        magnet.rotate_by(vector(0, 1, 0), amount)
    if "right" in keys_down:
        magnet.rotate_by(vector(0, 1, 0), -amount)
    if "up" in keys_down:
        magnet.rotate_by(vector(0, 0, 1), amount)
    if "down" in keys_down:
        magnet.rotate_by(vector(0, 0, 1), -amount)
    if "q" in keys_down:
        magnet.rotate_by(magnet.u, amount)
    if "e" in keys_down:
        magnet.rotate_by(magnet.u, -amount)
    if "w" in keys_down:
        magnet.rotate_by(vector(1, 0, 0), amount)
    if "s" in keys_down:
        magnet.rotate_by(vector(1, 0, 0), -amount)


# ------------------------------------------------------------
# Dynamic Labels
# ------------------------------------------------------------

def update_labels():
    near_null_b = magnetic_strength(magnet.pos)
    particle_b = magnetic_strength(charged.pos)
    defl = charged.line_deflection()

    particle_label.text = (
        f"+ charged particle: slow pass\n"
        f"speed: {charged.initial_speed:.2f} units/s\n"
        f"|B| at particle: {particle_b:.3f}\n"
        f"current deflection: {defl:.3f}\n"
        f"max deflection: {charged.max_deflection:.3f}\n"
        f"time inside null: {charged.in_null_time:.2f}s"
    )

    state_label.text = (
        f"{'PAUSED' if paused else 'RUNNING'} | auto-rotate: {'on' if auto_rotate else 'off'}\n"
        f"inner faces: N  ⇔  N\n"
        f"|B| at exact center: {near_null_b:.4f}\n"
        f"charged trail: {'on' if charged.trails_enabled else 'off'}\n"
        f"filings: {PARTICLE_COUNT}\n"
        f"press G to relaunch through null"
    )

    title_label.pos = magnet.pos + magnet.v * 3.38 - magnet.w * 0.05


# ------------------------------------------------------------
# Startup
# ------------------------------------------------------------

scatter_filings()
charged.reset(clear=True)
field_lines.update()
update_labels()

# ------------------------------------------------------------
# Main Loop
# ------------------------------------------------------------

while True:
    rate(FPS)
    frame_counter += 1

    if paused:
        magnet.update_visuals()
        charged.update_visual(vector(0, 0, 0))
        if frame_counter % 5 == 0:
            update_labels()
        continue

    apply_human_controls()

    if auto_rotate:
        phase = time.time() * 0.55
        magnet.rotate_by(vector(0, 1, 0), 0.0022)
        magnet.rotate_by(vector(0, 0, 1), 0.0012 * math.sin(phase))

    # Redraw the magnet pair immediately after any logical rotation so the
    # visible bars never lag behind or temporarily share the same render state.
    magnet.update_visuals()

    external_force = vector(0, 0, 0)
    for p in particles:
        p.update(DT, external_force=external_force)

    charged.update(DT)

    if frame_counter % 4 == 0:
        field_lines.update()

    magnet.decay_spin_meter()

    if frame_counter % 5 == 0:
        update_labels()
