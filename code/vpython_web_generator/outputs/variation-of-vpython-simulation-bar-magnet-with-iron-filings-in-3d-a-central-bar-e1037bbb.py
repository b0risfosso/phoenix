from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# 3D VPython Simulation:
# Two Repelling Bar Magnets + Iron Filings + Repulsion Bubble + AI Control
# Like north poles face each other; filings are pushed away from the center gap.
# ------------------------------------------------------------

scene = canvas(
    title="Two Repelling Bar Magnets - Iron Filings Avoid the Center Gap",
    width=1200,
    height=760,
    background=vector(0.94, 0.98, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-6.5, -3.0, -6.0)
scene.up = vector(0, 1, 0)
scene.range = 7.1

HELP_TEXT = """
Controls:
  Arrow keys : rotate both magnets as one repelling pair
  Q / E      : roll pair
  W / S      : pitch pair
  A          : toggle AI
  P / Space  : pause / resume simulation
  R          : reset round
  D          : detach all particles
  O          : orbit burst
  M          : mark aligned outward-bending chains
  T          : toggle trails
  C          : clear trails
  H          : hide/show help

Variation:
  Two bar magnets have LIKE POLES facing each other: N  ⇔  N.
  Filings avoid the center gap, bend outward around the null/repulsion region,
  and a transparent glowing “repulsion bubble” marks the pushed-away zone.
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
CENTER_GAP = 1.18

PARTICLE_COUNT = 120
PARTICLE_LENGTH = 0.21
PARTICLE_RADIUS = 0.027

FIELD_LINE_COUNT = 36
FIELD_LINE_STEPS = 145
FIELD_LINE_STEP_SIZE = 0.075

BOUND = vector(6.0, 3.05, 3.75)
TRAIL_RETAIN = 90

BUBBLE_RADIUS = 1.10
BUBBLE_X_RADIUS = CENTER_GAP * 0.72
BUBBLE_SIDE_RADIUS = 1.18

# ------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------

def clamp(x, a, b):
    return max(a, min(b, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def limit_vec(v, max_len):
    m = mag(v)
    if m > max_len and m > 1e-8:
        return v * (max_len / m)
    return v


def rand_range(a, b):
    return a + random.random() * (b - a)


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


# ------------------------------------------------------------
# Stationary Environment
# ------------------------------------------------------------

container = box(
    pos=vector(0, 0, 0),
    size=2 * BOUND,
    color=vector(0.72, 0.86, 1.0),
    opacity=0.070,
)

floor_grid_lines = []
for x in [i * 0.5 for i in range(-12, 13)]:
    floor_grid_lines.append(
        curve(
            pos=[vector(x, -BOUND.y, -BOUND.z), vector(x, -BOUND.y, BOUND.z)],
            color=vector(0.78, 0.84, 0.88),
            radius=0.003,
        )
    )
for z in [i * 0.5 for i in range(-8, 9)]:
    floor_grid_lines.append(
        curve(
            pos=[vector(-BOUND.x, -BOUND.y, z), vector(BOUND.x, -BOUND.y, z)],
            color=vector(0.78, 0.84, 0.88),
            radius=0.003,
        )
    )

title_label = label(
    pos=vector(0, 3.55, 0),
    text="Two Bar Magnets Repelling: N faces N",
    height=18,
    box=False,
    color=vector(0.12, 0.15, 0.18),
)

bubble_label = label(
    pos=vector(0, 1.75, 0),
    text="repulsion bubble\nfilings avoid this gap",
    height=12,
    box=True,
    border=5,
    color=vector(0.38, 0.12, 0.50),
    background=vector(1.0, 0.93, 1.0),
    opacity=0.60,
)

cloud_label = label(
    pos=vector(-5.2, 2.6, 2.95),
    text="iron filings bend outward",
    height=12,
    box=False,
    color=vector(0.28, 0.31, 0.34),
)

field_label = label(
    pos=vector(4.8, 2.55, -2.4),
    text="field lines avoid central null",
    height=12,
    box=False,
    color=vector(0.02, 0.42, 0.62),
)

ai_status_label = label(
    pos=vector(-5.55, 3.10, -3.15),
    text="AI: starting",
    height=12,
    box=True,
    border=6,
    color=vector(0.08, 0.12, 0.15),
    background=vector(0.95, 0.98, 1.0),
    opacity=0.74,
)

state_label = label(
    pos=vector(5.18, 3.10, 3.05),
    text="state",
    height=11,
    box=True,
    border=5,
    color=vector(0.10, 0.12, 0.13),
    background=vector(1.0, 0.98, 0.88),
    opacity=0.70,
)

# ------------------------------------------------------------
# Bar Magnet Pieces and Repelling Pair
# ------------------------------------------------------------

class MagnetPiece:
    def __init__(self, name):
        self.name = name
        self.pos = vector(0, 0, 0)
        self.u = vector(1, 0, 0)  # south -> north
        self.v = vector(0, 1, 0)
        self.w = vector(0, 0, 1)

        self.south_half = box(
            pos=self.pos - self.u * MAGNET_LENGTH * 0.25,
            size=vector(MAGNET_LENGTH * 0.5, MAGNET_HEIGHT, MAGNET_WIDTH),
            axis=self.u,
            up=self.v,
            color=vector(0.17, 0.34, 0.96),
            shininess=0.72,
        )
        self.north_half = box(
            pos=self.pos + self.u * MAGNET_LENGTH * 0.25,
            size=vector(MAGNET_LENGTH * 0.5, MAGNET_HEIGHT, MAGNET_WIDTH),
            axis=self.u,
            up=self.v,
            color=vector(0.96, 0.16, 0.12),
            shininess=0.72,
        )
        self.center_band = box(
            pos=self.pos,
            size=vector(0.07, MAGNET_HEIGHT * 1.07, MAGNET_WIDTH * 1.07),
            axis=self.u,
            up=self.v,
            color=vector(0.96, 0.96, 0.84),
            shininess=0.65,
        )
        self.north_cap = cylinder(
            pos=self.pos + self.u * (MAGNET_LENGTH * 0.5),
            axis=self.u * CAP_THICKNESS,
            radius=0.46,
            color=vector(1.0, 0.27, 0.20),
            shininess=0.9,
        )
        self.south_cap = cylinder(
            pos=self.pos - self.u * (MAGNET_LENGTH * 0.5),
            axis=-self.u * CAP_THICKNESS,
            radius=0.46,
            color=vector(0.15, 0.36, 1.0),
            shininess=0.9,
        )
        self.n_label = label(
            pos=self.north_world() + self.v * 0.64,
            text="N",
            height=20,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.95, 0.10, 0.08),
            opacity=0.88,
        )
        self.s_label = label(
            pos=self.south_world() + self.v * 0.64,
            text="S",
            height=20,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.08, 0.18, 0.95),
            opacity=0.88,
        )

    def set_frame(self, pos, u, v):
        """Update the magnet's logical transform without touching VPython objects.

        VPython renders asynchronously in the browser. If each tiny rotation writes
        every object position immediately, the viewer can briefly see a half-updated
        magnet pair. Keeping the logical transform separate lets the simulation
        perform many rotations in one frame, then redraw the visible objects once.
        """
        self.pos = pos
        self.u = safe_norm(u, vector(1, 0, 0))
        self.v = v - dot(v, self.u) * self.u
        self.v = safe_norm(self.v, vector(0, 1, 0))
        self.w = safe_norm(cross(self.u, self.v), vector(0, 0, 1))
        self.v = safe_norm(cross(self.w, self.u), vector(0, 1, 0))

    def redraw(self):
        self.south_half.pos = self.pos - self.u * MAGNET_LENGTH * 0.25
        self.south_half.axis = self.u
        self.south_half.up = self.v

        self.north_half.pos = self.pos + self.u * MAGNET_LENGTH * 0.25
        self.north_half.axis = self.u
        self.north_half.up = self.v

        self.center_band.pos = self.pos
        self.center_band.axis = self.u
        self.center_band.up = self.v

        self.north_cap.pos = self.pos + self.u * (MAGNET_LENGTH * 0.5)
        self.north_cap.axis = self.u * CAP_THICKNESS

        self.south_cap.pos = self.pos - self.u * (MAGNET_LENGTH * 0.5)
        self.south_cap.axis = -self.u * CAP_THICKNESS

        self.n_label.pos = self.north_world() + self.v * 0.68
        self.s_label.pos = self.south_world() + self.v * 0.68

    def update(self, pos, u, v):
        self.set_frame(pos, u, v)
        self.redraw()

    def north_world(self):
        return self.pos + self.u * (MAGNET_LENGTH * 0.5)

    def south_world(self):
        return self.pos - self.u * (MAGNET_LENGTH * 0.5)

    def world_from_local(self, local):
        return self.pos + self.u * local.x + self.v * local.y + self.w * local.z

    def local_from_world(self, world):
        r = world - self.pos
        return vector(dot(r, self.u), dot(r, self.v), dot(r, self.w))


class RepellingMagnetPair:
    def __init__(self):
        self.pos = vector(0, 0, 0)
        self.u = vector(1, 0, 0)  # from left magnet toward right magnet
        self.v = vector(0, 1, 0)
        self.w = vector(0, 0, 1)
        self.spin_impulse = 0.0
        self.visuals_dirty = True

        self.left = MagnetPiece("left")
        self.right = MagnetPiece("right")

        self.axis_arrow = arrow(
            pos=self.pos - self.u * 1.0,
            axis=self.u * 2.0,
            shaftwidth=0.030,
            headwidth=0.12,
            headlength=0.18,
            color=vector(1.0, 0.78, 0.20),
            opacity=0.55,
        )

        self.gap_arrow_l = arrow(
            pos=self.pos - self.u * 0.10,
            axis=-self.u * 0.46,
            shaftwidth=0.035,
            headwidth=0.15,
            headlength=0.18,
            color=vector(1.0, 0.30, 0.25),
            opacity=0.80,
        )
        self.gap_arrow_r = arrow(
            pos=self.pos + self.u * 0.10,
            axis=self.u * 0.46,
            shaftwidth=0.035,
            headwidth=0.15,
            headlength=0.18,
            color=vector(1.0, 0.30, 0.25),
            opacity=0.80,
        )

        self.bubble = sphere(
            pos=self.pos,
            radius=BUBBLE_RADIUS,
            color=vector(0.96, 0.58, 1.0),
            opacity=0.16,
            shininess=0.1,
            emissive=True,
        )

        self.bubble_ring_u = ring(
            pos=self.pos,
            axis=self.u,
            radius=BUBBLE_SIDE_RADIUS,
            thickness=0.018,
            color=vector(0.88, 0.22, 1.0),
            opacity=0.62,
        )
        self.bubble_ring_v = ring(
            pos=self.pos,
            axis=self.v,
            radius=BUBBLE_SIDE_RADIUS * 0.92,
            thickness=0.014,
            color=vector(1.0, 0.50, 0.90),
            opacity=0.45,
        )
        self.bubble_ring_w = ring(
            pos=self.pos,
            axis=self.w,
            radius=BUBBLE_SIDE_RADIUS * 0.92,
            thickness=0.014,
            color=vector(0.74, 0.40, 1.0),
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

    def world_from_pair_local(self, local):
        return self.pos + self.u * local.x + self.v * local.y + self.w * local.z

    def pair_local_from_world(self, world):
        r = world - self.pos
        return vector(dot(r, self.u), dot(r, self.v), dot(r, self.w))

    def bubble_metric(self, point):
        local = self.pair_local_from_world(point)
        return math.sqrt(
            (local.x / max(BUBBLE_X_RADIUS, 0.001)) ** 2
            + (local.y / BUBBLE_SIDE_RADIUS) ** 2
            + (local.z / BUBBLE_SIDE_RADIUS) ** 2
        )

    def repulsion_bubble_force(self, point):
        local = self.pair_local_from_world(point)
        metric = self.bubble_metric(point)
        if metric > 1.38:
            return vector(0, 0, 0)

        radial = self.v * local.y + self.w * local.z
        if mag(radial) < 0.06:
            radial = random_perpendicular(self.u) * 0.08

        radial_dir = safe_norm(radial, self.v)

        # Strongly push away sideways so filings visibly bend around the gap.
        sideways = radial_dir * (1.0 - clamp(metric / 1.38, 0, 1)) ** 2 * 8.5

        # A weaker axial split prevents grains from sitting exactly between the like poles.
        axial_dir = self.u * (1 if local.x >= 0 else -1)
        axial = axial_dir * (1.0 - clamp(metric / 1.38, 0, 1)) ** 2 * 1.6

        return sideways + axial

    def nearest_piece(self, point):
        dl = mag(point - self.left.pos)
        dr = mag(point - self.right.pos)
        return self.left if dl <= dr else self.right

    def update_logical_frames(self):
        self.left.set_frame(self.left_center(), self.u, self.v)
        self.right.set_frame(self.right_center(), -self.u, self.v)

    def update_visuals(self):
        self.update_logical_frames()
        self.left.redraw()
        self.right.redraw()

        self.axis_arrow.pos = self.pos - self.u * 1.05
        self.axis_arrow.axis = self.u * 2.10

        self.gap_arrow_l.pos = self.pos - self.u * 0.08
        self.gap_arrow_l.axis = -self.u * 0.48
        self.gap_arrow_r.pos = self.pos + self.u * 0.08
        self.gap_arrow_r.axis = self.u * 0.48

        pulse = 1.0 + 0.06 * math.sin(time.time() * 2.5)
        self.bubble.pos = self.pos
        self.bubble.radius = BUBBLE_RADIUS * pulse

        self.bubble_ring_u.pos = self.pos
        self.bubble_ring_u.axis = self.u
        self.bubble_ring_u.radius = BUBBLE_SIDE_RADIUS * pulse

        self.bubble_ring_v.pos = self.pos
        self.bubble_ring_v.axis = self.v
        self.bubble_ring_v.radius = BUBBLE_SIDE_RADIUS * 0.92 * pulse

        self.bubble_ring_w.pos = self.pos
        self.bubble_ring_w.axis = self.w
        self.bubble_ring_w.radius = BUBBLE_SIDE_RADIUS * 0.92 * pulse

        bubble_label.pos = self.pos + self.v * 1.72 + self.w * 0.10
        self.visuals_dirty = False

    def decay_spin_meter(self):
        self.spin_impulse *= 0.90


magnet = RepellingMagnetPair()

# ------------------------------------------------------------
# Initial Cloud Placement
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
            rand_range(-BOUND.x * 0.88, BOUND.x * 0.88),
            rand_range(-BOUND.y * 0.80, BOUND.y * 0.80),
            rand_range(-BOUND.z * 0.85, BOUND.z * 0.85),
        )
        if inside_any_magnet_box(p, pad=0.45):
            continue
        if magnet.bubble_metric(p) < 1.22:
            continue
        return p

    angle = rand_range(0, 2 * math.pi)
    side = magnet.v * math.cos(angle) + magnet.w * math.sin(angle)
    return magnet.pos + side * rand_range(1.6, 2.9) + magnet.u * rand_range(-3.2, 3.2)


# ------------------------------------------------------------
# Magnetic Field Model
# ------------------------------------------------------------

def magnetic_field_at(point):
    # Magnetic pole approximation:
    # each north pole is a source, each south pole is a sink.
    poles = [
        (magnet.left_north_world(), 1.0),
        (magnet.right_north_world(), 1.0),
        (magnet.left_south_world(), -1.0),
        (magnet.right_south_world(), -1.0),
    ]

    b = vector(0, 0, 0)
    for pos, charge in poles:
        r = point - pos
        d = max(mag(r), 0.24)
        b += charge * r / (d ** 3)

    # Inside each magnet, hint that the internal field returns from S to N.
    for piece in (magnet.left, magnet.right):
        local = piece.local_from_world(point)
        if (
            abs(local.x) < MAGNET_LENGTH * 0.5
            and abs(local.y) < MAGNET_HEIGHT
            and abs(local.z) < MAGNET_WIDTH
        ):
            b += -piece.u * 0.38

    # Artificial outward bending near the like-pole gap.
    # This makes the repulsion/null zone visually clear for filings and streamlines.
    local = magnet.pair_local_from_world(point)
    metric = magnet.bubble_metric(point)
    if metric < 1.55:
        radial = magnet.v * local.y + magnet.w * local.z
        if mag(radial) < 0.05:
            radial = magnet.v * 0.05
        radial_dir = safe_norm(radial, magnet.v)
        influence = (1.0 - clamp(metric / 1.55, 0, 1)) ** 2
        b += radial_dir * 2.25 * influence
        b += magnet.u * local.x * 0.38 * influence

    return limit_vec(b, 20.0)


def magnetic_strength(point):
    return mag(magnetic_field_at(point))


def field_gradient(point):
    eps = 0.22
    bx1 = magnetic_strength(point + vector(eps, 0, 0))
    bx0 = magnetic_strength(point - vector(eps, 0, 0))
    by1 = magnetic_strength(point + vector(0, eps, 0))
    by0 = magnetic_strength(point - vector(0, eps, 0))
    bz1 = magnetic_strength(point + vector(0, 0, eps))
    bz0 = magnetic_strength(point - vector(0, 0, eps))
    g = vector((bx1 - bx0), (by1 - by0), (bz1 - bz0)) / (2 * eps)
    return limit_vec(g, 18.0)


# ------------------------------------------------------------
# Field Line Tubes
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
                radius=0.017 if layer != 1 else 0.013,
                color=vector(0.12, 0.72, 1.0) if side < 0 else vector(1.0, 0.68, 0.20),
                emissive=True,
                opacity=0.78,
            )
            self.lines.append(c)

        self.update(force=True)

    def generate_line_points(self, phase, layer, side):
        radius = 0.18 + 0.15 * layer
        ring_dir = math.cos(phase) * magnet.v + math.sin(phase) * magnet.w

        if side < 0:
            # left inner north pole faces the gap; seed just off its face
            p = magnet.left_north_world() + magnet.u * 0.06 + ring_dir * radius
        else:
            # right inner north pole faces the gap; seed just off its face
            p = magnet.right_north_world() - magnet.u * 0.06 + ring_dir * radius

        pts = []
        last_good = p

        for step in range(FIELD_LINE_STEPS):
            pts.append(p)

            # When a streamline grazes the repulsion bubble, deflect it outward
            # rather than letting it cross the like-pole center.
            if magnet.bubble_metric(p) < 1.02:
                p += safe_norm(ring_dir, magnet.v) * FIELD_LINE_STEP_SIZE * 2.0
                last_good = p

            b = magnetic_field_at(p)
            d = safe_norm(b, ring_dir)
            p = p + d * FIELD_LINE_STEP_SIZE
            last_good = p

            # Stop if a line reaches either outer south pole.
            if step > 35:
                if mag(p - magnet.left_south_world()) < 0.34 + 0.05 * layer:
                    last_good = magnet.left_south_world() + ring_dir * 0.10
                    break
                if mag(p - magnet.right_south_world()) < 0.34 + 0.05 * layer:
                    last_good = magnet.right_south_world() + ring_dir * 0.10
                    break

            if abs(p.x) > BOUND.x * 1.35 or abs(p.y) > BOUND.y * 1.45 or abs(p.z) > BOUND.z * 1.45:
                break

        while len(pts) < FIELD_LINE_STEPS:
            pts.append(last_good)
        return pts[:FIELD_LINE_STEPS]

    def update(self, force=False):
        for i, c in enumerate(self.lines):
            pts = self.generate_line_points(self.seed_phases[i], self.seed_layers[i], self.seed_side[i])
            for j, p in enumerate(pts):
                c.modify(j, pos=p)


field_lines = FieldLineSystem()

# ------------------------------------------------------------
# Iron Filing Particles
# ------------------------------------------------------------

class FilingParticle:
    def __init__(self, idx):
        self.idx = idx
        self.center = random_cloud_position()
        self.vel = random_unit_vector() * rand_range(0.01, 0.08)
        self.dir = random_unit_vector()
        self.flow_sign = 1 if random.random() < 0.5 else -1
        self.attached = False
        self.attached_piece = None
        self.attached_local = vector(0, 0, 0)
        self.marked_timer = 0.0
        self.chain_score = 0.0
        self.trails_enabled = True

        self.body = cylinder(
            pos=self.center - self.dir * (PARTICLE_LENGTH * 0.5),
            axis=self.dir * PARTICLE_LENGTH,
            radius=PARTICLE_RADIUS,
            color=vector(0.43, 0.45, 0.44),
            shininess=0.92,
        )
        self.tip_a = sphere(
            pos=self.center + self.dir * PARTICLE_LENGTH * 0.52,
            radius=PARTICLE_RADIUS * 1.15,
            color=vector(0.62, 0.64, 0.63),
            shininess=0.9,
        )
        self.tip_b = sphere(
            pos=self.center - self.dir * PARTICLE_LENGTH * 0.52,
            radius=PARTICLE_RADIUS * 1.15,
            color=vector(0.36, 0.38, 0.37),
            shininess=0.9,
        )

        self.trail_anchor = sphere(
            pos=self.center,
            radius=0.008,
            color=vector(0.5, 0.74, 1.0),
            opacity=0.015,
            shininess=0,
        )
        attach_trail(
            self.trail_anchor,
            radius=0.006,
            color=vector(0.25, 0.58, 1.0),
            retain=TRAIL_RETAIN,
        )
        self.update_visual()

    def update_visual(self):
        self.dir = safe_norm(self.dir, vector(1, 0, 0))
        self.body.pos = self.center - self.dir * (PARTICLE_LENGTH * 0.5)
        self.body.axis = self.dir * PARTICLE_LENGTH

        self.tip_a.pos = self.center + self.dir * PARTICLE_LENGTH * 0.52
        self.tip_b.pos = self.center - self.dir * PARTICLE_LENGTH * 0.52
        self.trail_anchor.pos = self.center

        if self.marked_timer > 0:
            mark_color = vector(1.0, 0.76, 0.16)
            self.body.color = mark_color
            self.tip_a.color = vector(1.0, 0.90, 0.38)
            self.tip_b.color = vector(0.88, 0.55, 0.10)
        elif self.attached:
            self.body.color = vector(0.18, 0.19, 0.18)
            self.tip_a.color = vector(0.42, 0.42, 0.40)
            self.tip_b.color = vector(0.25, 0.25, 0.24)
        elif magnet.bubble_metric(self.center) < 1.35:
            self.body.color = vector(0.80, 0.45, 0.84)
            self.tip_a.color = vector(0.96, 0.66, 1.0)
            self.tip_b.color = vector(0.62, 0.33, 0.70)
        elif self.chain_score > 0.55:
            self.body.color = vector(0.54, 0.48, 0.38)
            self.tip_a.color = vector(0.66, 0.61, 0.50)
            self.tip_b.color = vector(0.42, 0.39, 0.33)
        else:
            self.body.color = vector(0.43, 0.45, 0.44)
            self.tip_a.color = vector(0.62, 0.64, 0.63)
            self.tip_b.color = vector(0.36, 0.38, 0.37)

    def clear_trail(self):
        try:
            self.trail_anchor.clear_trail()
        except Exception:
            pass

    def set_trails(self, enabled):
        self.trails_enabled = enabled
        self.trail_anchor.visible = enabled
        if not enabled:
            self.clear_trail()

    def reset(self):
        self.center = random_cloud_position()
        self.vel = random_unit_vector() * rand_range(0.01, 0.08)
        self.dir = random_unit_vector()
        self.flow_sign = 1 if random.random() < 0.5 else -1
        self.attached = False
        self.attached_piece = None
        self.marked_timer = 0
        self.chain_score = 0
        self.clear_trail()
        self.update_visual()

    def detach(self, impulse=None):
        if impulse is None:
            impulse = random_unit_vector() * rand_range(0.2, 0.75)
        self.attached = False
        self.attached_piece = None
        self.vel += impulse

    def attach_to_piece(self, piece):
        local = piece.local_from_world(self.center)

        # Avoid sticking directly in the N-N center gap.
        if local.x > MAGNET_LENGTH * 0.35 and magnet.bubble_metric(self.center) < 1.32:
            return False

        self.attached = True
        self.attached_piece = piece

        local.x = clamp(local.x, -MAGNET_LENGTH * 0.56, MAGNET_LENGTH * 0.50)
        local.y = clamp(local.y, -MAGNET_HEIGHT * 0.74, MAGNET_HEIGHT * 0.74)
        local.z = clamp(local.z, -MAGNET_WIDTH * 0.74, MAGNET_WIDTH * 0.74)

        # Prefer outer south ends and side edges, not the repelling center faces.
        if local.x > MAGNET_LENGTH * 0.30:
            if abs(local.y) > abs(local.z):
                local.y = MAGNET_HEIGHT * 0.70 * (1 if local.y >= 0 else -1)
            else:
                local.z = MAGNET_WIDTH * 0.70 * (1 if local.z >= 0 else -1)

        if abs(local.x) < MAGNET_LENGTH * 0.35 and random.random() < 0.55:
            local.x = -MAGNET_LENGTH * 0.50

        self.attached_local = local
        self.vel *= 0.12
        return True

    def collide_with_bounds(self):
        p = self.center
        v = self.vel
        bounce = 0.66

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
            p.y = -BOUND.y
            v.y = abs(v.y) * bounce

        if p.z > BOUND.z:
            p.z = BOUND.z
            v.z = -abs(v.z) * bounce
        elif p.z < -BOUND.z:
            p.z = -BOUND.z
            v.z = abs(v.z) * bounce

        self.center = p
        self.vel = v

    def collide_or_attach_with_magnets(self):
        for piece in (magnet.left, magnet.right):
            local = piece.local_from_world(self.center)
            expanded = vector(MAGNET_LENGTH * 0.5 + 0.15, MAGNET_HEIGHT * 0.5 + 0.13, MAGNET_WIDTH * 0.5 + 0.13)

            if abs(local.x) < expanded.x and abs(local.y) < expanded.y and abs(local.z) < expanded.z:
                near_outer_south = local.x < -MAGNET_LENGTH * 0.35
                near_side = abs(local.y) > MAGNET_HEIGHT * 0.42 or abs(local.z) > MAGNET_WIDTH * 0.42
                in_gap = local.x > MAGNET_LENGTH * 0.26 and magnet.bubble_metric(self.center) < 1.45

                if not in_gap and (near_outer_south or near_side or magnetic_strength(self.center) > 3.6):
                    if random.random() < 0.20:
                        if self.attach_to_piece(piece):
                            return

                px = expanded.x - abs(local.x)
                py = expanded.y - abs(local.y)
                pz = expanded.z - abs(local.z)

                if px <= py and px <= pz:
                    n = piece.u * (1 if local.x >= 0 else -1)
                elif py <= px and py <= pz:
                    n = piece.v * (1 if local.y >= 0 else -1)
                else:
                    n = piece.w * (1 if local.z >= 0 else -1)

                if in_gap:
                    n = safe_norm(n + magnet.repulsion_bubble_force(self.center), n)

                self.center += n * 0.08
                self.vel = self.vel - 1.35 * dot(self.vel, n) * n + n * 0.05

    def update(self, dt, external_force=vector(0, 0, 0)):
        self.marked_timer = max(0.0, self.marked_timer - dt)
        self.chain_score *= 0.94

        b = magnetic_field_at(self.center)
        bdir = safe_norm(b, magnet.u)

        # Rods have no magnetic polarity, so they align with either direction of B.
        if dot(self.dir, bdir) < 0:
            bdir = -bdir
        self.dir = safe_norm(lerp_vec(self.dir, bdir, clamp(7.0 * dt, 0, 1)), self.dir)

        if self.attached:
            if self.attached_piece is not None:
                self.center = self.attached_piece.world_from_local(self.attached_local)

            if magnet.spin_impulse > 0.035 and random.random() < clamp(magnet.spin_impulse * 0.020, 0, 0.11):
                outward = safe_norm(self.center - magnet.pos, random_unit_vector())
                self.detach(impulse=outward * 0.34 + random_unit_vector() * 0.22)
            else:
                self.vel *= 0.15
                self.update_visual()
                return

        strength = mag(b)
        grad = field_gradient(self.center)

        f_grad = grad * 0.030
        f_flow = bdir * (0.12 * self.flow_sign) * clamp(strength, 0, 2.6)
        f_noise = random_unit_vector() * 0.010
        f_bubble = magnet.repulsion_bubble_force(self.center) * 0.20

        f = f_grad + f_flow + f_noise + f_bubble + external_force

        self.vel += limit_vec(f, 1.15) * dt
        self.vel *= 0.965
        self.vel = limit_vec(self.vel, 1.55)

        self.center += self.vel * dt

        # Hard safety: grains that drift too deep into the center bubble are expelled sideways.
        if magnet.bubble_metric(self.center) < 0.72:
            push = magnet.repulsion_bubble_force(self.center)
            self.vel += safe_norm(push, random_perpendicular(magnet.u)) * 0.12
            self.center += safe_norm(push, random_perpendicular(magnet.u)) * 0.035

        self.collide_or_attach_with_magnets()
        self.collide_with_bounds()
        self.update_visual()


particles = [FilingParticle(i) for i in range(PARTICLE_COUNT)]

# ------------------------------------------------------------
# Bonds / Visible Clumps
# ------------------------------------------------------------

bond_curves = []
last_clump_count = 0


def update_clumping_and_bonds(frame_count):
    global bond_curves, last_clump_count

    clump_count = 0

    for i in range(len(particles)):
        p = particles[i]
        if p.attached:
            continue
        for j in range(i + 1, len(particles)):
            q = particles[j]
            if q.attached:
                continue

            midpoint = (p.center + q.center) * 0.5
            if magnet.bubble_metric(midpoint) < 1.08:
                continue

            delta = q.center - p.center
            d = mag(delta)
            if d < 0.34:
                aligned = abs(dot(safe_norm(p.dir), safe_norm(q.dir)))
                if aligned > 0.70:
                    n = safe_norm(delta)
                    pull = n * (0.020 * (0.34 - d) * aligned)
                    p.vel += pull
                    q.vel -= pull
                    avg_v = (p.vel + q.vel) * 0.5
                    p.vel = lerp_vec(p.vel, avg_v, 0.05)
                    q.vel = lerp_vec(q.vel, avg_v, 0.05)
                    p.chain_score = min(1.0, p.chain_score + 0.08)
                    q.chain_score = min(1.0, q.chain_score + 0.08)
                    clump_count += 1

    last_clump_count = clump_count

    if frame_count % 10 != 0:
        return

    for b in bond_curves:
        b.visible = False
    bond_curves = []

    shown = 0
    max_bonds = 68

    for i in range(len(particles)):
        if shown >= max_bonds:
            break
        p = particles[i]
        for j in range(i + 1, len(particles)):
            if shown >= max_bonds:
                break
            q = particles[j]
            d = mag(q.center - p.center)
            midpoint = (p.center + q.center) * 0.5
            if d < 0.30 and abs(dot(p.dir, q.dir)) > 0.75 and magnet.bubble_metric(midpoint) > 1.08:
                bond_curves.append(
                    curve(
                        pos=[p.center, q.center],
                        radius=0.007,
                        color=vector(0.56, 0.53, 0.46),
                        opacity=0.55,
                    )
                )
                shown += 1


# ------------------------------------------------------------
# Simulation State, Actions, Reset
# ------------------------------------------------------------

paused = False
ai_enabled = True
show_help = True
trails_enabled = True
human_override_timer = 0.0
frame_counter = 0
round_number = 1

keys_down = set()


def read_simulation_state():
    attached_count = sum(1 for p in particles if p.attached)
    free_count = PARTICLE_COUNT - attached_count
    avg_speed = sum(mag(p.vel) for p in particles) / PARTICLE_COUNT
    avg_alignment = 0.0
    avg_radius = 0.0
    marked_count = 0
    bubble_count = 0

    for p in particles:
        b = magnetic_field_at(p.center)
        bdir = safe_norm(b, magnet.u)
        avg_alignment += abs(dot(safe_norm(p.dir), bdir))
        avg_radius += mag(p.center - magnet.pos)
        if p.marked_timer > 0:
            marked_count += 1
        if magnet.bubble_metric(p.center) < 1.0:
            bubble_count += 1

    avg_alignment /= PARTICLE_COUNT
    avg_radius /= PARTICLE_COUNT

    return {
        "attached_count": attached_count,
        "free_count": free_count,
        "avg_speed": avg_speed,
        "avg_alignment": avg_alignment,
        "avg_radius": avg_radius,
        "clump_count": last_clump_count,
        "marked_count": marked_count,
        "bubble_count": bubble_count,
        "magnet_u": magnet.u,
        "magnet_spin": magnet.spin_impulse,
        "round_number": round_number,
    }


def detach_all(strength=0.5):
    for p in particles:
        if p.attached:
            outward = safe_norm(p.center - magnet.pos, random_unit_vector())
            p.detach(impulse=outward * rand_range(0.2, strength) + random_unit_vector() * 0.15)


def clear_all_trails():
    for p in particles:
        p.clear_trail()


def set_all_trails(enabled):
    global trails_enabled
    trails_enabled = enabled
    for p in particles:
        p.set_trails(enabled)


def mark_aligned_chains(duration=4.0):
    for p in particles:
        b = magnetic_field_at(p.center)
        align = abs(dot(safe_norm(p.dir), safe_norm(b, magnet.u)))
        if align > 0.84 or p.chain_score > 0.42 or p.attached:
            p.marked_timer = max(p.marked_timer, duration)


def orbit_burst(clockwise=True, strength=0.85):
    sign = 1 if clockwise else -1
    for p in particles:
        r = p.center - magnet.pos
        tangent = cross(magnet.u, r)
        if mag(tangent) < 0.1:
            tangent = cross(vector(0, 1, 0), r)
        tangent = safe_norm(tangent, random_unit_vector())
        p.vel += tangent * sign * rand_range(0.15, strength)


def spill_cloud(side=None):
    if side is None:
        side = random.choice(["left", "right", "top", "front", "ring"])

    for p in particles:
        p.attached = False
        p.attached_piece = None
        p.marked_timer = 0
        p.chain_score = 0

        if side == "left":
            p.center = vector(-BOUND.x * 0.90, rand_range(-1.8, 2.3), rand_range(-2.5, 2.5))
            p.vel = vector(rand_range(0.35, 0.95), rand_range(-0.15, 0.15), rand_range(-0.2, 0.2))
        elif side == "right":
            p.center = vector(BOUND.x * 0.90, rand_range(-1.8, 2.3), rand_range(-2.5, 2.5))
            p.vel = vector(rand_range(-0.95, -0.35), rand_range(-0.15, 0.15), rand_range(-0.2, 0.2))
        elif side == "front":
            p.center = vector(rand_range(-4.6, 4.6), rand_range(-1.6, 2.2), BOUND.z * 0.88)
            p.vel = vector(rand_range(-0.25, 0.25), rand_range(-0.1, 0.15), rand_range(-0.95, -0.35))
        elif side == "ring":
            angle = rand_range(0, 2 * math.pi)
            radial = magnet.v * math.cos(angle) + magnet.w * math.sin(angle)
            p.center = magnet.pos + radial * rand_range(1.65, 2.95) + magnet.u * rand_range(-3.5, 3.5)
            p.vel = -radial * rand_range(0.05, 0.25) + random_unit_vector() * 0.08
        else:
            p.center = vector(rand_range(-4.8, 4.8), BOUND.y * 0.90, rand_range(-2.8, 2.8))
            p.vel = vector(rand_range(-0.2, 0.2), rand_range(-0.95, -0.35), rand_range(-0.2, 0.2))

        if magnet.bubble_metric(p.center) < 1.18:
            p.center += safe_norm(magnet.repulsion_bubble_force(p.center), random_perpendicular(magnet.u)) * 1.2

        p.dir = random_unit_vector()
        p.clear_trail()
        p.update_visual()


def reset_simulation_round(randomize_orientation=True):
    global round_number
    round_number += 1

    for b in bond_curves:
        b.visible = False

    if randomize_orientation:
        magnet.u = random_unit_vector()
        if abs(dot(magnet.u, vector(0, 1, 0))) > 0.88:
            magnet.v = vector(1, 0, 0)
        else:
            magnet.v = safe_norm(vector(0, 1, 0) - dot(vector(0, 1, 0), magnet.u) * magnet.u)
        magnet.w = safe_norm(cross(magnet.u, magnet.v))
    else:
        magnet.u = vector(1, 0, 0)
        magnet.v = vector(0, 1, 0)
        magnet.w = vector(0, 0, 1)

    magnet.spin_impulse = 0
    magnet.orthonormalize()
    magnet.update_visuals()

    for p in particles:
        p.reset()

    clear_all_trails()
    field_lines.update(force=True)


# ------------------------------------------------------------
# AI Controller
# ------------------------------------------------------------

class AIController:
    MODES = [
        "OBSERVE",
        "OUTWARD_BEND",
        "ROTATE_SWEEP",
        "SHAKE_DETACH",
        "ORBIT_WRAP",
        "MARK_CHAINS",
        "SPILL_FROM_EDGE",
        "ARTIST_TRAILS",
        "CAREFUL_ALIGN",
        "CHAOTIC_MIX",
        "RESET_RITUAL",
    ]

    def __init__(self):
        self.enabled = True
        self.mode = "OBSERVE"
        self.mode_timer = 0.0
        self.mode_duration = 3.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.loop_cooldown = 0.0
        self.last_avg_speed = 999
        self.last_clumps = -1
        self.external_force = vector(0, 0, 0)
        self.round_seed = random.random()

    def choose_new_mode(self, state, reason="time"):
        attached_ratio = state["attached_count"] / PARTICLE_COUNT
        speed = state["avg_speed"]
        clumps = state["clump_count"]
        alignment = state["avg_alignment"]
        bubble_count = state["bubble_count"]

        possible = []

        if reason in ("complete", "stagnant"):
            possible += ["SPILL_FROM_EDGE", "SHAKE_DETACH", "RESET_RITUAL", "CHAOTIC_MIX"]
        elif bubble_count > 5:
            possible += ["OUTWARD_BEND", "ORBIT_WRAP", "ROTATE_SWEEP"]
        elif attached_ratio > 0.60:
            possible += ["SHAKE_DETACH", "ORBIT_WRAP", "MARK_CHAINS"]
        elif speed < 0.045 and clumps > 20:
            possible += ["MARK_CHAINS", "ARTIST_TRAILS", "ORBIT_WRAP"]
        elif alignment < 0.62:
            possible += ["CAREFUL_ALIGN", "OUTWARD_BEND", "ROTATE_SWEEP"]
        elif clumps < 12:
            possible += ["OUTWARD_BEND", "CAREFUL_ALIGN", "ROTATE_SWEEP"]
        else:
            possible += ["ROTATE_SWEEP", "ORBIT_WRAP", "ARTIST_TRAILS", "CHAOTIC_MIX", "MARK_CHAINS"]

        possible = [m for m in possible if m != self.mode] or self.MODES[:]
        self.mode = random.choice(possible)
        self.mode_timer = 0.0

        if self.mode == "OBSERVE":
            self.mode_duration = rand_range(1.2, 2.4)
        elif self.mode == "OUTWARD_BEND":
            self.mode_duration = rand_range(4.2, 7.0)
        elif self.mode == "ROTATE_SWEEP":
            self.mode_duration = rand_range(4.0, 6.4)
        elif self.mode == "SHAKE_DETACH":
            self.mode_duration = rand_range(2.0, 3.5)
        elif self.mode == "ORBIT_WRAP":
            self.mode_duration = rand_range(3.0, 5.8)
        elif self.mode == "MARK_CHAINS":
            self.mode_duration = rand_range(1.2, 2.2)
        elif self.mode == "SPILL_FROM_EDGE":
            self.mode_duration = rand_range(2.0, 3.2)
            spill_cloud(random.choice(["left", "right", "top", "front", "ring"]))
        elif self.mode == "ARTIST_TRAILS":
            self.mode_duration = rand_range(5.0, 8.0)
            set_all_trails(True)
        elif self.mode == "CAREFUL_ALIGN":
            self.mode_duration = rand_range(4.0, 6.8)
        elif self.mode == "CHAOTIC_MIX":
            self.mode_duration = rand_range(2.5, 4.2)
        elif self.mode == "RESET_RITUAL":
            self.mode_duration = rand_range(1.0, 2.0)
        else:
            self.mode_duration = rand_range(2.5, 5.0)

    def detect_stagnation_or_completion(self, state, dt):
        speed_change = abs(state["avg_speed"] - self.last_avg_speed)
        clump_change = abs(state["clump_count"] - self.last_clumps)
        attached_ratio = state["attached_count"] / PARTICLE_COUNT

        stable = state["avg_speed"] < 0.030 and speed_change < 0.004 and clump_change < 3
        complete = attached_ratio > 0.72 and state["avg_speed"] < 0.08
        empty_or_halted = state["free_count"] < 7 or state["avg_radius"] < 0.55

        if stable:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 0.8)

        if complete or empty_or_halted:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt)

        self.last_avg_speed = state["avg_speed"]
        self.last_clumps = state["clump_count"]

        if self.completion_timer > 3.0:
            return "complete"
        if self.stagnation_timer > 6.0:
            return "stagnant"
        return None

    def action_rotate(self, axis, amount):
        magnet.rotate_by(axis, amount)

    def action_shake(self, amount=0.045):
        magnet.rotate_by(random_unit_vector(), rand_range(-amount, amount))
        if random.random() < 0.18:
            detach_all(strength=0.8)

    def action_orbit(self, clockwise=True, strength=0.028):
        sign = 1 if clockwise else -1
        for p in particles:
            r = p.center - magnet.pos
            tangent = cross(magnet.u, r)
            if mag(tangent) < 0.1:
                tangent = cross(vector(0, 1, 0), r)
            tangent = safe_norm(tangent, random_unit_vector())
            p.vel += tangent * sign * strength

    def update(self, state, dt):
        self.external_force = vector(0, 0, 0)

        if not self.enabled:
            return self.external_force

        self.mode_timer += dt
        self.loop_cooldown = max(0.0, self.loop_cooldown - dt)

        condition = self.detect_stagnation_or_completion(state, dt)
        if condition and self.loop_cooldown <= 0:
            if condition == "complete":
                self.mode = "RESET_RITUAL"
                self.mode_timer = 0.0
                self.mode_duration = 1.1
                self.loop_cooldown = 5.0
            else:
                self.choose_new_mode(state, reason=condition)

        if self.mode_timer > self.mode_duration:
            self.choose_new_mode(state, reason="time")

        phase = time.time() * 0.8 + self.round_seed * 10

        if self.mode == "OBSERVE":
            self.action_rotate(vector(0, 1, 0), 0.002 * math.sin(phase))

        elif self.mode == "OUTWARD_BEND":
            self.action_rotate(vector(0, 1, 0), 0.005)
            self.action_rotate(vector(0, 0, 1), 0.002 * math.sin(phase * 1.7))
            # Extra outward puff from the center gap.
            for p in particles:
                if not p.attached and magnet.bubble_metric(p.center) < 1.7:
                    p.vel += magnet.repulsion_bubble_force(p.center) * 0.005

        elif self.mode == "ROTATE_SWEEP":
            self.action_rotate(vector(0, 1, 0), 0.012 + 0.006 * math.sin(phase))
            self.action_rotate(vector(0, 0, 1), 0.006 * math.sin(phase * 0.65))

        elif self.mode == "SHAKE_DETACH":
            self.action_shake(amount=0.055)
            self.external_force = random_unit_vector() * 0.20

        elif self.mode == "ORBIT_WRAP":
            self.action_rotate(vector(0, 1, 0), 0.014)
            self.action_rotate(vector(1, 0, 0), 0.004 * math.sin(phase * 1.3))
            self.action_orbit(clockwise=math.sin(phase) > 0, strength=0.020)

        elif self.mode == "MARK_CHAINS":
            mark_aligned_chains(duration=3.7)
            self.action_rotate(vector(0, 1, 0), 0.004)

        elif self.mode == "SPILL_FROM_EDGE":
            self.action_rotate(vector(0, 0, 1), 0.018 * math.sin(phase * 1.9))
            self.external_force = vector(0, -0.06, 0)

        elif self.mode == "ARTIST_TRAILS":
            self.action_rotate(vector(0, 1, 0), 0.007)
            self.action_rotate(vector(1, 0, 0), 0.006 * math.sin(phase * 0.9))
            self.action_orbit(clockwise=True, strength=0.011)
            if random.random() < 0.015:
                mark_aligned_chains(duration=1.4)

        elif self.mode == "CAREFUL_ALIGN":
            desired = vector(1, 0.15 * math.sin(phase), 0.25 * math.cos(phase * 0.8))
            axis = cross(magnet.u, safe_norm(desired))
            if mag(axis) > 0.001:
                self.action_rotate(axis, clamp(mag(axis) * 0.008, -0.012, 0.012))
            self.external_force = magnetic_field_at(vector(0.4 * math.sin(phase), 0, 0)) * 0.002

        elif self.mode == "CHAOTIC_MIX":
            self.action_shake(amount=0.038)
            self.action_rotate(vector(0, 1, 0), 0.017 * math.sin(phase * 2.2))
            self.action_orbit(clockwise=random.random() < 0.5, strength=0.025)
            if random.random() < 0.010:
                detach_all(strength=1.0)

        elif self.mode == "RESET_RITUAL":
            self.action_rotate(vector(0, 1, 0), 0.030)
            self.action_rotate(vector(0, 0, 1), 0.018)
            if self.mode_timer > self.mode_duration * 0.72:
                reset_simulation_round(randomize_orientation=True)
                self.stagnation_timer = 0
                self.completion_timer = 0
                self.choose_new_mode(read_simulation_state(), reason="reset")

        return self.external_force


ai = AIController()

# ------------------------------------------------------------
# Keyboard Input
# ------------------------------------------------------------

def on_keydown(evt):
    global paused, ai_enabled, show_help, trails_enabled, human_override_timer

    k = evt.key
    keys_down.add(k)
    human_override_timer = 1.25

    if k in (" ", "p"):
        paused = not paused
    elif k == "a":
        ai_enabled = not ai_enabled
        ai.enabled = ai_enabled
    elif k == "r":
        reset_simulation_round(randomize_orientation=True)
    elif k == "d":
        detach_all(strength=1.05)
    elif k == "o":
        orbit_burst(clockwise=random.random() < 0.5, strength=1.0)
    elif k == "m":
        mark_aligned_chains(duration=5.0)
    elif k == "t":
        set_all_trails(not trails_enabled)
    elif k == "c":
        clear_all_trails()
    elif k == "h":
        show_help = not show_help
        scene.caption = HELP_TEXT if show_help else ""


def on_keyup(evt):
    k = evt.key
    if k in keys_down:
        keys_down.remove(k)


scene.bind("keydown", on_keydown)
scene.bind("keyup", on_keyup)


def apply_human_controls(dt):
    amount = 0.034
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

def update_labels(state):
    ai_text = "ON" if ai.enabled else "OFF"
    pause_text = "PAUSED" if paused else "RUNNING"

    ai_status_label.text = (
        f"AI: {ai_text} | {pause_text}\n"
        f"mode: {ai.mode}\n"
        f"round: {round_number} | mode time: {ai.mode_timer:4.1f}s\n"
        f"stagnation: {ai.stagnation_timer:3.1f}s | completion: {ai.completion_timer:3.1f}s"
    )

    state_label.text = (
        f"attached: {state['attached_count']} / {PARTICLE_COUNT}\n"
        f"free: {state['free_count']} | clumps: {state['clump_count']}\n"
        f"in bubble: {state['bubble_count']}  (should stay low)\n"
        f"avg speed: {state['avg_speed']:.3f}\n"
        f"alignment: {state['avg_alignment']:.2f}\n"
        f"trails: {'on' if trails_enabled else 'off'}"
    )

    field_label.pos = magnet.pos + magnet.u * 3.8 + magnet.v * 1.85 - magnet.w * 1.15
    cloud_label.pos = magnet.pos - magnet.u * 4.1 + magnet.v * 2.25 + magnet.w * 1.6


# ------------------------------------------------------------
# Startup Visual State
# ------------------------------------------------------------

local_light(pos=vector(0, 5, 2), color=vector(0.74, 0.78, 0.84))
local_light(pos=vector(-4, 3, -4), color=vector(0.48, 0.58, 0.72))
local_light(pos=vector(4, 4, 3), color=vector(0.56, 0.52, 0.66))

spill_cloud("top")
ai.choose_new_mode(read_simulation_state(), reason="startup")

# ------------------------------------------------------------
# Main Loop
# ------------------------------------------------------------

while True:
    rate(FPS)
    frame_counter += 1

    human_override_timer = max(0.0, human_override_timer - DT)

    if paused:
        magnet.update_visuals()
        state = read_simulation_state()
        update_labels(state)
        continue

    apply_human_controls(DT)

    state = read_simulation_state()

    ai.enabled = ai_enabled
    ai_force = ai.update(state, DT)
    if human_override_timer > 0:
        ai_force *= 0.35

    for p in particles:
        p.update(DT, external_force=ai_force)

    update_clumping_and_bonds(frame_counter)

    if frame_counter % 3 == 0:
        field_lines.update()

    magnet.decay_spin_meter()
    magnet.update_visuals()

    if frame_counter % 5 == 0:
        state = read_simulation_state()
        update_labels(state)
