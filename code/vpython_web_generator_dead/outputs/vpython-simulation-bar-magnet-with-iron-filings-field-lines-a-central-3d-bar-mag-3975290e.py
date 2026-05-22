"""
VPython Magnetic Shapes Simulation
----------------------------------
A 3D magnetic-field visualization with iron filings and switchable magnet shapes.

Shapes included:
  1 Bar magnet
  2 Horseshoe magnet
  3 Ring magnet
  4 Disk magnet
  5 Dual bar magnets

Controls:
  SPACE  pause/resume
  1      bar magnet
  2      horseshoe magnet
  3      ring magnet
  4      disk magnet
  5      dual bar magnets
  R      reset filings
  C      organize filings onto field lines
  D      detach/spill filings
  O      orbit burst
  H      chaos burst
  LEFT/RIGHT rotate shape around Y
  UP/DOWN rotate shape around Z
  +/-    increase/decrease field strength

Run:
  pip install vpython
  python vpython_magnetic_shapes_simulation.py
"""

import math
import random
import time
import vpython as vp

# ============================================================
# Scene
# ============================================================

scene = vp.canvas(
    title="3D Magnetic Shapes With Iron Filings",
    width=1150,
    height=760,
    background=vp.vector(0.94, 0.97, 1.0),
    center=vp.vector(0, 0, 0),
)
scene.forward = vp.vector(-4.4, -2.4, -3.4)
scene.up = vp.vector(0, 1, 0)
scene.range = 5.5
scene.autoscale = False

scene.append_to_caption(
    "\nControls:\n"
    "  SPACE pause/resume\n"
    "  1 bar magnet    2 horseshoe magnet    3 ring magnet\n"
    "  4 disk magnet   5 dual bar magnets\n"
    "  R reset filings    C organize filings    D spill filings\n"
    "  O orbit burst      H chaos burst\n"
    "  LEFT/RIGHT rotate around Y    UP/DOWN rotate around Z\n"
    "  +/- field strength\n"
)

vp.distant_light(direction=vp.vector(-1, -1, -0.5), color=vp.vector(0.9, 0.9, 0.85))
vp.distant_light(direction=vp.vector(1, -0.4, 0.8), color=vp.vector(0.65, 0.72, 1.0))
vp.local_light(pos=vp.vector(0, 3.8, 2.8), color=vp.vector(0.75, 0.82, 1.0))

# ============================================================
# Constants
# ============================================================

WORLD_LIMIT = 4.35
FILING_COUNT = 260
ROD_MIN_LENGTH = 0.14
ROD_MAX_LENGTH = 0.25
ROD_RADIUS = 0.011

FIELD_LINE_COUNT = 44
FIELD_STEP = 0.055
FIELD_MAX_STEPS = 270
FIELD_FAR_LIMIT = 5.2
FIELD_STOP_RADIUS = 0.20

NORTH_COLOR = vp.vector(0.95, 0.17, 0.12)
SOUTH_COLOR = vp.vector(0.12, 0.33, 0.92)
IRON_COLOR = vp.vector(0.31, 0.30, 0.28)
ATTACHED_COLOR = vp.vector(0.98, 0.66, 0.20)
FLOATING_COLOR = vp.vector(0.35, 0.34, 0.32)
FIELD_COLOR_A = vp.vector(1.0, 0.76, 0.18)
FIELD_COLOR_B = vp.vector(0.98, 0.43, 0.10)

# ============================================================
# Helpers
# ============================================================

def clamp(x, a, b):
    return max(a, min(b, x))


def safe_norm(v, fallback=vp.vector(1, 0, 0)):
    m = vp.mag(v)
    if m < 1e-9:
        return fallback
    return v / m


def mix(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t


def mix_scalar(a, b, t):
    return a * (1 - t) + b * t


def random_unit():
    while True:
        v = vp.vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if vp.mag(v) > 0.001:
            return vp.norm(v)


def random_in_box(x, y, z):
    return vp.vector(random.uniform(-x, x), random.uniform(-y, y), random.uniform(-z, z))


def rotate_vec(v, angle, axis):
    return vp.rotate(v, angle=angle, axis=axis)


def local_basis(axis, up_hint=vp.vector(0, 1, 0)):
    axis = safe_norm(axis, vp.vector(1, 0, 0))
    up = up_hint - axis * vp.dot(up_hint, axis)
    up = safe_norm(up, vp.vector(0, 1, 0))
    side = safe_norm(vp.cross(axis, up), vp.vector(0, 0, 1))
    return axis, up, side


def field_from_poles(p, poles, strength=1.0):
    """Positive pole is north/source, negative pole is south/sink."""
    b = vp.vector(0, 0, 0)
    for pole_pos, pole_strength in poles:
        r = p - pole_pos
        d = max(vp.mag(r), 0.14)
        b += pole_strength * r / (d ** 3)
    return b * strength

# ============================================================
# Magnetic shape model
# ============================================================

class MagneticShape:
    def __init__(self):
        self.kind = "bar"
        self.axis = vp.vector(1, 0, 0)
        self.up = vp.vector(0, 1, 0)
        self.side = vp.vector(0, 0, 1)
        self.strength = 1.0
        self.objects = []
        self.poles = []
        self.center = vp.vector(0, 0, 0)

    def clear(self):
        for obj in self.objects:
            obj.visible = False
        self.objects = []

    def set_kind(self, kind):
        self.kind = kind
        self.build()

    def rotate(self, angle, rot_axis):
        self.axis = rotate_vec(self.axis, angle, rot_axis)
        self.up = rotate_vec(self.up, angle, rot_axis)
        self.axis, self.up, self.side = local_basis(self.axis, self.up)
        self.build()

    def build(self):
        self.clear()
        self.axis, self.up, self.side = local_basis(self.axis, self.up)
        if self.kind == "bar":
            self._build_bar()
        elif self.kind == "horseshoe":
            self._build_horseshoe()
        elif self.kind == "ring":
            self._build_ring()
        elif self.kind == "disk":
            self._build_disk()
        elif self.kind == "dual":
            self._build_dual()
        else:
            self.kind = "bar"
            self._build_bar()

    def _add_label(self, pos, text, color):
        self.objects.append(vp.label(pos=pos, text=text, height=18, color=color, box=False, opacity=0))

    def _build_bar(self):
        length = 2.9
        height = 0.56
        width = 0.60
        c = self.center
        a = self.axis
        u = self.up
        self.objects.append(vp.box(pos=c + a * length * 0.25, size=vp.vector(length * 0.5, height, width), axis=a, up=u, color=NORTH_COLOR, shininess=0.6))
        self.objects.append(vp.box(pos=c - a * length * 0.25, size=vp.vector(length * 0.5, height, width), axis=a, up=u, color=SOUTH_COLOR, shininess=0.6))
        self.objects.append(vp.box(pos=c, size=vp.vector(0.045, height * 1.05, width * 1.05), axis=a, up=u, color=vp.vector(0.96, 0.96, 0.96), shininess=0.5))
        n = c + a * length * 0.5
        s = c - a * length * 0.5
        self.objects.append(vp.sphere(pos=n, radius=0.22, color=NORTH_COLOR, opacity=0.18, emissive=True))
        self.objects.append(vp.sphere(pos=s, radius=0.22, color=SOUTH_COLOR, opacity=0.18, emissive=True))
        self._add_label(n + u * 0.55, "N", NORTH_COLOR)
        self._add_label(s + u * 0.55, "S", SOUTH_COLOR)
        self.poles = [(n, 1.0), (s, -1.0)]

    def _build_horseshoe(self):
        c = self.center
        a = self.axis
        u = self.up
        s = self.side
        gap = 1.25
        arm_len = 2.45
        arm_thick = 0.32
        bridge_len = gap + arm_thick
        left = c - s * gap * 0.5
        right = c + s * gap * 0.5
        back = c - a * 0.35
        front = c + a * 0.85

        self.objects.append(vp.box(pos=(left + back) * 0.5 + a * 0.15, size=vp.vector(arm_len, arm_thick, arm_thick), axis=a, up=u, color=SOUTH_COLOR, shininess=0.55))
        self.objects.append(vp.box(pos=(right + back) * 0.5 + a * 0.15, size=vp.vector(arm_len, arm_thick, arm_thick), axis=a, up=u, color=NORTH_COLOR, shininess=0.55))
        self.objects.append(vp.box(pos=c - a * 1.05, size=vp.vector(arm_thick, arm_thick, bridge_len), axis=a, up=u, color=vp.vector(0.50, 0.18, 0.72), shininess=0.55))

        n = front + s * gap * 0.5
        south = front - s * gap * 0.5
        self.objects.append(vp.sphere(pos=n, radius=0.21, color=NORTH_COLOR, opacity=0.22, emissive=True))
        self.objects.append(vp.sphere(pos=south, radius=0.21, color=SOUTH_COLOR, opacity=0.22, emissive=True))
        self._add_label(n + u * 0.40, "N", NORTH_COLOR)
        self._add_label(south + u * 0.40, "S", SOUTH_COLOR)
        self.poles = [(n, 1.25), (south, -1.25), (c - a * 1.1 + s * 0.62, 0.35), (c - a * 1.1 - s * 0.62, -0.35)]

    def _build_ring(self):
        c = self.center
        a = self.axis
        u = self.up
        s = self.side
        radius = 1.05
        tube = 0.075
        segments = 72
        for i in range(segments):
            t0 = 2 * math.pi * i / segments
            t1 = 2 * math.pi * (i + 1) / segments
            p0 = c + math.cos(t0) * u * radius + math.sin(t0) * s * radius
            p1 = c + math.cos(t1) * u * radius + math.sin(t1) * s * radius
            color = mix(NORTH_COLOR, SOUTH_COLOR, (math.sin(t0) + 1) * 0.5)
            self.objects.append(vp.cylinder(pos=p0, axis=p1 - p0, radius=tube, color=color, shininess=0.5))
        self.objects.append(vp.sphere(pos=c + a * 0.42, radius=0.20, color=NORTH_COLOR, opacity=0.18, emissive=True))
        self.objects.append(vp.sphere(pos=c - a * 0.42, radius=0.20, color=SOUTH_COLOR, opacity=0.18, emissive=True))
        self._add_label(c + a * 0.68 + u * 1.18, "N face", NORTH_COLOR)
        self._add_label(c - a * 0.68 - u * 1.18, "S face", SOUTH_COLOR)

        self.poles = []
        for i in range(12):
            t = 2 * math.pi * i / 12
            ring_p = c + math.cos(t) * u * radius + math.sin(t) * s * radius
            self.poles.append((ring_p + a * 0.38, 0.18))
            self.poles.append((ring_p - a * 0.38, -0.18))

    def _build_disk(self):
        c = self.center
        a = self.axis
        u = self.up
        radius = 0.95
        thickness = 0.44
        self.objects.append(vp.cylinder(pos=c - a * thickness * 0.5, axis=a * thickness, radius=radius, color=vp.vector(0.55, 0.32, 0.72), shininess=0.62))
        self.objects.append(vp.cylinder(pos=c + a * 0.02, axis=a * 0.035, radius=radius * 1.01, color=NORTH_COLOR, opacity=0.72, shininess=0.62))
        self.objects.append(vp.cylinder(pos=c - a * 0.055, axis=-a * 0.035, radius=radius * 1.01, color=SOUTH_COLOR, opacity=0.72, shininess=0.62))
        self._add_label(c + a * 0.55 + u * 1.05, "N", NORTH_COLOR)
        self._add_label(c - a * 0.55 - u * 1.05, "S", SOUTH_COLOR)
        self.poles = []
        # Keep the disk physics lightweight. The earlier version used
        # 37 north/south pairs, which made field tracing and per-frame
        # filing updates too expensive in disk mode. These 17 pairs still
        # approximate two magnetized faces while keeping the scene responsive.
        rings = [0.0, 0.55, 0.90]
        counts = [1, 6, 10]
        for r, count in zip(rings, counts):
            for i in range(count):
                t = 2 * math.pi * i / count if count > 1 else 0
                radial = math.cos(t) * self.up + math.sin(t) * self.side
                p = c + radial * r
                weight = 0.30 if r == 0 else 0.16
                self.poles.append((p + a * thickness * 0.55, weight))
                self.poles.append((p - a * thickness * 0.55, -weight))

    def _build_dual(self):
        c = self.center
        a = self.axis
        u = self.up
        s = self.side
        length = 2.15
        height = 0.42
        width = 0.46
        offset = 0.82
        self.poles = []
        for lane, reverse in [(-1, False), (1, True)]:
            cc = c + s * lane * offset
            dir_axis = -a if reverse else a
            north_center = cc + dir_axis * length * 0.25
            south_center = cc - dir_axis * length * 0.25
            self.objects.append(vp.box(pos=north_center, size=vp.vector(length * 0.5, height, width), axis=dir_axis, up=u, color=NORTH_COLOR, shininess=0.55))
            self.objects.append(vp.box(pos=south_center, size=vp.vector(length * 0.5, height, width), axis=dir_axis, up=u, color=SOUTH_COLOR, shininess=0.55))
            n = cc + dir_axis * length * 0.5
            south = cc - dir_axis * length * 0.5
            self.objects.append(vp.sphere(pos=n, radius=0.18, color=NORTH_COLOR, opacity=0.20, emissive=True))
            self.objects.append(vp.sphere(pos=south, radius=0.18, color=SOUTH_COLOR, opacity=0.20, emissive=True))
            self.poles.append((n, 1.0))
            self.poles.append((south, -1.0))
        self._add_label(c + u * 0.65, "Dual opposing bars", vp.vector(0.15, 0.17, 0.22))

    def magnetic_field(self, p):
        b = field_from_poles(p, self.poles, self.strength)
        if vp.mag(b) < 1e-8:
            return self.axis
        return b

    def field_strength(self, p):
        return vp.mag(self.magnetic_field(p))

    def seed_points(self):
        seeds = []
        if not self.poles:
            return seeds
        positive_poles = [(p, q) for p, q in self.poles if q > 0]
        # Dense shapes such as the disk can have many pseudo-poles.
        # Cap seed count per pole to avoid creating an oversized temporary
        # seed list before slicing to FIELD_LINE_COUNT.
        dense_shape = len(positive_poles) > 12
        for pole_pos, pole_strength in positive_poles:
            if dense_shape:
                count = 1
            else:
                count = max(3, int(FIELD_LINE_COUNT * abs(pole_strength) / max(1, len(positive_poles))))
            for i in range(count):
                theta = 2 * math.pi * (i / count)
                z = -0.75 + 1.5 * ((i * 7) % count) / max(1, count - 1)
                if count == 1:
                    theta = random.uniform(0, 2 * math.pi)
                    z = random.uniform(-0.35, 0.75)
                r = math.sqrt(max(0.0, 1 - z * z))
                local = safe_norm(self.axis * z + self.up * (r * math.cos(theta)) + self.side * (r * math.sin(theta)), self.axis)
                seeds.append(pole_pos + local * 0.25)
        random.shuffle(seeds)
        return seeds[:FIELD_LINE_COUNT]

    def point_inside_shape(self, p, margin=0.0):
        # Simple broad-phase protection: keep filings outside visible magnetic bodies.
        if self.kind == "bar":
            q = p - self.center
            x = vp.dot(q, self.axis)
            y = vp.dot(q, self.up)
            z = vp.dot(q, self.side)
            return abs(x) < 1.48 + margin and abs(y) < 0.31 + margin and abs(z) < 0.34 + margin
        if self.kind == "disk":
            q = p - self.center
            x = abs(vp.dot(q, self.axis))
            radial = vp.mag(q - self.axis * vp.dot(q, self.axis))
            return x < 0.26 + margin and radial < 1.0 + margin
        if self.kind == "ring":
            q = p - self.center
            x = abs(vp.dot(q, self.axis))
            radial = vp.mag(q - self.axis * vp.dot(q, self.axis))
            return x < 0.18 + margin and 0.82 - margin < radial < 1.18 + margin
        # For complex shapes, use only a soft central exclusion.
        return vp.mag(p - self.center) < 0.26 + margin

# ============================================================
# Iron filings
# ============================================================

class IronFiling:
    def __init__(self, sim, idx, center):
        self.sim = sim
        self.idx = idx
        self.center = vp.vector(center.x, center.y, center.z)
        self.velocity = random_unit() * random.uniform(0.0, 0.35)
        self.length = random.uniform(ROD_MIN_LENGTH, ROD_MAX_LENGTH)
        self.radius = random.uniform(ROD_RADIUS * 0.8, ROD_RADIUS * 1.45)
        self.axis_dir = random_unit()
        self.attached = False
        self.line_index = 0
        self.line_j = 0
        self.line_u = 0.0
        self.offset = vp.vector(0, 0, 0)
        self.slide_speed = random.uniform(-2.4, 2.4)
        self.cached_nearest_p = self.center
        self.cached_line_index = 0
        self.cached_line_j = 0
        self.cached_line_dist = 999
        self.body = vp.cylinder(
            pos=self.center - self.axis_dir * self.length * 0.5,
            axis=self.axis_dir * self.length,
            radius=self.radius,
            color=IRON_COLOR,
            shininess=0.45,
        )

    def hide(self):
        self.body.visible = False

    def attach_to_line(self, li, j, offset_scale=0.05):
        if li < 0 or li >= len(self.sim.field_line_points):
            return
        pts = self.sim.field_line_points[li]
        if not pts:
            return
        self.attached = True
        self.line_index = li
        self.line_j = int(clamp(j, 0, len(pts) - 1))
        self.line_u = float(self.line_j)
        tangent = self.sim.line_tangent(li, self.line_j)
        radial = safe_norm(vp.cross(tangent, random_unit()), random_unit())
        self.offset = radial * offset_scale * random.uniform(0.25, 1.2)
        self.velocity *= 0.45

    def detach(self, boost=True):
        self.attached = False
        if boost:
            self.velocity += random_unit() * random.uniform(0.15, 0.55)

    def update_nearest_cache(self):
        p, li, j, d = self.sim.nearest_field_sample(self.center)
        self.cached_nearest_p = p
        self.cached_line_index = li
        self.cached_line_j = j
        self.cached_line_dist = d

    def update(self, dt):
        sim = self.sim
        c = sim.controls

        if sim.frame % 7 == self.idx % 7:
            self.update_nearest_cache()

        if self.attached and self.line_index < len(sim.field_line_points):
            pts = sim.field_line_points[self.line_index]
            if len(pts) < 2:
                self.detach(boost=False)
            else:
                self.line_u += self.slide_speed * c["slide"] * dt
                self.line_u = clamp(self.line_u, 0, len(pts) - 1)
                self.line_j = int(self.line_u)
                target = pts[self.line_j] + self.offset
                tangent = sim.line_tangent(self.line_index, self.line_j)
                spring = target - self.center
                self.velocity += spring * 4.8 * dt
                self.velocity *= (1.0 - 0.88 * dt)
                self.axis_dir = safe_norm(self.axis_dir * (1 - c["align"] * dt) + tangent * c["align"] * dt, self.axis_dir)
                if random.random() < c["detach_probability"] * dt:
                    self.detach(boost=True)
        else:
            b = sim.shape.magnetic_field(self.center)
            bdir = safe_norm(b, sim.shape.axis)
            nearest = self.cached_nearest_p
            to_line = nearest - self.center
            dist = max(0.001, vp.mag(to_line))
            line_dir = to_line / dist

            force = vp.vector(0, 0, 0)
            force += line_dir * c["attract"] * clamp(1.2 - dist, 0.0, 1.4)
            force += bdir * 0.075

            # Pole attraction. Iron is attracted to strong field regions near both poles.
            for pole_pos, pole_strength in sim.shape.poles:
                d = max(0.16, vp.mag(self.center - pole_pos))
                force += safe_norm(pole_pos - self.center) * clamp(0.08 * abs(pole_strength) / (d * d), 0, 0.75)

            radial = self.center - sim.shape.center
            tangent = vp.cross(sim.shape.axis, radial)
            if vp.mag(tangent) > 0.001:
                force += safe_norm(tangent) * c["orbit"] * clamp(vp.mag(radial), 0.2, 2.8) * 0.22

            force += random_unit() * c["noise"] * random.uniform(0.0, 0.45)
            force += random_unit() * c["chaos"] * random.uniform(0.0, 1.0)
            force += -self.velocity * c["damping"]

            self.velocity += force * dt
            speed = vp.mag(self.velocity)
            if speed > 2.4:
                self.velocity = self.velocity / speed * 2.4

            self.axis_dir = safe_norm(
                self.axis_dir * (1 - c["align"] * dt) + bdir * c["align"] * dt + random_unit() * c["noise"] * 0.02,
                self.axis_dir,
            )

            attach_chance = c["attach_probability"] * dt * clamp((0.34 - dist) / 0.34, 0, 1)
            if dist < 0.34 and random.random() < attach_chance:
                self.attach_to_line(self.cached_line_index, self.cached_line_j, offset_scale=random.uniform(0.012, 0.075))

        self.center += self.velocity * dt
        sim.collide_with_world(self)
        self.apply_visual()

    def apply_visual(self):
        self.body.pos = self.center - self.axis_dir * self.length * 0.5
        self.body.axis = self.axis_dir * self.length
        if self.attached:
            self.body.color = mix(self.body.color, ATTACHED_COLOR, 0.14)
        else:
            self.body.color = mix(self.body.color, FLOATING_COLOR, 0.08)

# ============================================================
# Simulation
# ============================================================

class MagneticShapesSimulation:
    def __init__(self):
        self.paused = False
        self.frame = 0
        self.shape = MagneticShape()
        self.shape.build()
        self.field_curves = []
        self.field_line_points = []
        self.flat_field_samples = []
        self.line_particles = []
        self.filings = []
        self.controls = {
            "attract": 0.62,
            "align": 8.5,
            "noise": 0.16,
            "attach_probability": 0.72,
            "detach_probability": 0.0,
            "slide": 0.0,
            "chaos": 0.0,
            "orbit": 0.0,
            "damping": 0.66,
        }
        self.last_field_redraw = 0
        self.field_redraw_requested = True
        self.floor = vp.box(pos=vp.vector(0, -1.65, 0), size=vp.vector(8.9, 0.025, 6.9), color=vp.vector(0.90, 0.94, 0.96), opacity=0.50)
        self.boundary = vp.box(pos=vp.vector(0, 0, 0), size=vp.vector(WORLD_LIMIT * 2, WORLD_LIMIT * 1.48, WORLD_LIMIT * 1.45), color=vp.vector(0.78, 0.86, 0.92), opacity=0.035)
        self.status_label = vp.label(pos=vp.vector(-4.05, 2.45, 0), text="", height=12, color=vp.vector(0.12, 0.16, 0.20), box=False, opacity=0, align="left")
        self.title_label = vp.label(pos=vp.vector(0, 2.75, 0), text="Magnetic Shapes: Bar, Horseshoe, Ring, Disk, Dual", height=18, color=vp.vector(0.12, 0.16, 0.20), box=False, opacity=0)
        self.generate_field_lines()
        self.create_particles_on_field_lines()
        self.create_filings()

    def set_shape(self, kind):
        self.shape.set_kind(kind)
        self.field_redraw_requested = True
        self.generate_field_lines()
        self.create_particles_on_field_lines()
        self.detach_all(spill=True)

    def trace_field_line(self, start):
        pts = []
        p = vp.vector(start.x, start.y, start.z)
        for _ in range(FIELD_MAX_STEPS):
            pts.append(vp.vector(p.x, p.y, p.z))
            if vp.mag(p - self.shape.center) > FIELD_FAR_LIMIT:
                break
            b = self.shape.magnetic_field(p)
            p = p + safe_norm(b, self.shape.axis) * FIELD_STEP

            # Stop near any south pole.
            for pole_pos, pole_strength in self.shape.poles:
                if pole_strength < 0 and vp.mag(p - pole_pos) < FIELD_STOP_RADIUS:
                    pts.append(vp.vector(p.x, p.y, p.z))
                    return pts
        return pts

    def generate_field_lines(self):
        for curve in self.field_curves:
            curve.visible = False
        self.field_curves = []
        self.field_line_points = []
        self.flat_field_samples = []

        seeds = self.shape.seed_points()
        for line_index, seed in enumerate(seeds):
            pts = self.trace_field_line(seed)
            if len(pts) < 8:
                continue
            color_t = (math.sin(line_index * 0.83) + 1) * 0.5
            color = mix(FIELD_COLOR_A, FIELD_COLOR_B, color_t)
            curve = vp.curve(pos=pts, radius=0.014, color=color, opacity=0.68, emissive=True)
            self.field_curves.append(curve)
            self.field_line_points.append(pts)
            for j in range(0, len(pts), 3):
                self.flat_field_samples.append((pts[j], len(self.field_line_points) - 1, j))

        self.last_field_redraw = time.time()
        self.field_redraw_requested = False

    def maybe_redraw_field_lines(self):
        if self.field_redraw_requested and time.time() - self.last_field_redraw > 0.20:
            self.generate_field_lines()
            self.create_particles_on_field_lines()

    def nearest_field_sample(self, p):
        if not self.flat_field_samples:
            return p, 0, 0, 999
        best_p, best_li, best_j = self.flat_field_samples[0]
        best_d2 = vp.mag2(p - best_p)
        for sample_p, li, j in self.flat_field_samples[1:]:
            d2 = vp.mag2(p - sample_p)
            if d2 < best_d2:
                best_d2 = d2
                best_p, best_li, best_j = sample_p, li, j
        return best_p, best_li, best_j, math.sqrt(best_d2)

    def line_tangent(self, li, j):
        if li < 0 or li >= len(self.field_line_points):
            return self.shape.axis
        pts = self.field_line_points[li]
        if len(pts) < 2:
            return self.shape.axis
        j0 = int(clamp(j - 1, 0, len(pts) - 1))
        j1 = int(clamp(j + 1, 0, len(pts) - 1))
        return safe_norm(pts[j1] - pts[j0], self.shape.axis)

    def create_particles_on_field_lines(self):
        for particle in self.line_particles:
            particle["obj"].visible = False
        self.line_particles = []
        count = 46
        for i in range(count):
            if not self.field_line_points:
                break
            li = i % len(self.field_line_points)
            pts = self.field_line_points[li]
            if not pts:
                continue
            obj = vp.sphere(pos=pts[random.randrange(len(pts))], radius=random.uniform(0.020, 0.035), color=mix(vp.vector(1, 1, 1), FIELD_COLOR_A, random.random()), opacity=0.60, emissive=True)
            self.line_particles.append({"obj": obj, "line": li, "u": random.uniform(0, max(1, len(pts) - 1)), "speed": random.uniform(12, 28)})

    def update_field_particles(self, dt):
        if not self.field_line_points:
            return
        for particle in self.line_particles:
            li = particle["line"] % len(self.field_line_points)
            pts = self.field_line_points[li]
            if len(pts) < 2:
                continue
            particle["u"] = (particle["u"] + particle["speed"] * dt) % (len(pts) - 1)
            j = int(particle["u"])
            t = particle["u"] - j
            particle["obj"].pos = pts[j] * (1 - t) + pts[min(j + 1, len(pts) - 1)] * t

    def pulse_field_lines(self):
        pulse = 0.5 + 0.5 * math.sin(time.time() * 2.4)
        for i, curve in enumerate(self.field_curves):
            try:
                curve.radius = 0.012 + 0.010 * (0.35 + 0.65 * pulse) * (1 + 0.12 * math.sin(i))
                curve.opacity = 0.54 + 0.22 * pulse
            except Exception:
                pass

    def create_filings(self):
        for filing in self.filings:
            filing.hide()
        self.filings = []
        for i in range(FILING_COUNT):
            p = random_in_box(3.85, 1.75, 2.65)
            attempts = 0
            while self.shape.point_inside_shape(p, margin=0.18) and attempts < 100:
                p = random_in_box(3.85, 1.75, 2.65)
                attempts += 1
            self.filings.append(IronFiling(self, i, p))

    def reset_filings(self):
        self.create_filings()

    def detach_all(self, spill=True):
        for filing in self.filings:
            filing.detach(boost=spill)
            if spill:
                outward = safe_norm(filing.center - self.shape.center, random_unit())
                filing.velocity += outward * random.uniform(0.45, 1.15) + self.shape.up * random.uniform(0.08, 0.40)

    def organize_all(self, fraction=0.75):
        for filing in self.filings:
            if random.random() < fraction:
                p, li, j, d = self.nearest_field_sample(filing.center)
                filing.attach_to_line(li, j, offset_scale=random.uniform(0.014, 0.080))

    def orbit_burst(self, strength=1.2):
        for filing in self.filings:
            r = filing.center - self.shape.center
            tangent = vp.cross(self.shape.axis, r)
            if vp.mag(tangent) > 0.001:
                filing.velocity += safe_norm(tangent) * random.uniform(0.25, strength)

    def chaos_burst(self, strength=1.0):
        for filing in self.filings:
            if random.random() < 0.68:
                filing.detach(boost=False)
                filing.velocity += random_unit() * random.uniform(0.15, strength)

    def collide_with_world(self, filing):
        p = filing.center
        v = filing.velocity
        limit_x = WORLD_LIMIT
        limit_y = WORLD_LIMIT * 0.72
        limit_z = WORLD_LIMIT * 0.72
        bounced = False

        if p.x > limit_x:
            p.x = limit_x
            v.x *= -0.72
            bounced = True
        elif p.x < -limit_x:
            p.x = -limit_x
            v.x *= -0.72
            bounced = True

        if p.y > limit_y:
            p.y = limit_y
            v.y *= -0.72
            bounced = True
        elif p.y < -1.55:
            p.y = -1.55
            v.y *= -0.55
            v.x *= 0.88
            v.z *= 0.88
            bounced = True

        if p.z > limit_z:
            p.z = limit_z
            v.z *= -0.72
            bounced = True
        elif p.z < -limit_z:
            p.z = -limit_z
            v.z *= -0.72
            bounced = True

        if self.shape.point_inside_shape(p, margin=0.03):
            normal = safe_norm(p - self.shape.center, random_unit())
            p += normal * 0.13
            v = v - 1.35 * vp.dot(v, normal) * normal + normal * 0.10
            filing.detach(boost=False)
            bounced = True

        filing.center = p
        filing.velocity = v
        if bounced:
            filing.body.color = mix(filing.body.color, vp.vector(1.0, 0.88, 0.18), 0.18)

    def handle_pair_collisions(self):
        samples = 130
        n = len(self.filings)
        if n < 2:
            return
        for _ in range(samples):
            a = self.filings[random.randrange(n)]
            b = self.filings[random.randrange(n)]
            if a is b:
                continue
            delta = b.center - a.center
            d2 = vp.mag2(delta)
            min_d = 0.074
            if 1e-8 < d2 < min_d * min_d:
                d = math.sqrt(d2)
                normal = delta / d
                overlap = min_d - d
                a.center -= normal * overlap * 0.52
                b.center += normal * overlap * 0.52
                rel = vp.dot(b.velocity - a.velocity, normal)
                impulse = normal * (0.018 - 0.28 * rel)
                a.velocity -= impulse
                b.velocity += impulse

    def update_status_label(self):
        attached = 0
        avg_speed = 0
        for f in self.filings:
            attached += 1 if f.attached else 0
            avg_speed += vp.mag(f.velocity)
        count = max(1, len(self.filings))
        attached_ratio = attached / count
        avg_speed /= count
        self.status_label.text = (
            f"Shape: {self.shape.kind.upper()}\n"
            f"Simulation: {'PAUSED' if self.paused else 'RUNNING'}\n"
            f"Field strength: {self.shape.strength:.2f}\n"
            f"Filings: {len(self.filings)}\n"
            f"Attached: {attached_ratio * 100:4.1f}%\n"
            f"Avg speed: {avg_speed:.3f}"
        )

    def update(self, dt):
        self.frame += 1
        if not self.paused:
            self.maybe_redraw_field_lines()
            self.update_field_particles(dt)
            self.pulse_field_lines()
            self.controls["chaos"] = mix_scalar(self.controls["chaos"], 0.0, 0.035)
            self.controls["orbit"] = mix_scalar(self.controls["orbit"], 0.0, 0.025)
            self.controls["slide"] = mix_scalar(self.controls["slide"], 0.0, 0.025)
            for filing in self.filings:
                filing.update(dt)
            if self.frame % 2 == 0:
                self.handle_pair_collisions()
        self.update_status_label()

# ============================================================
# Keyboard input and main loop
# ============================================================

sim = MagneticShapesSimulation()


def on_keydown(evt):
    k = evt.key.lower()
    if k == " ":
        sim.paused = not sim.paused
    elif k == "1":
        sim.set_shape("bar")
    elif k == "2":
        sim.set_shape("horseshoe")
    elif k == "3":
        sim.set_shape("ring")
    elif k == "4":
        sim.set_shape("disk")
    elif k == "5":
        sim.set_shape("dual")
    elif k == "r":
        sim.reset_filings()
    elif k == "c":
        sim.organize_all(fraction=0.78)
        sim.controls["slide"] = 0.30
    elif k == "d":
        sim.detach_all(spill=True)
    elif k == "o":
        sim.orbit_burst(strength=1.35)
        sim.controls["orbit"] = 1.25
    elif k == "h":
        sim.chaos_burst(strength=1.35)
        sim.controls["chaos"] = 1.1
    elif k == "left":
        sim.shape.rotate(0.12, vp.vector(0, 1, 0))
        sim.field_redraw_requested = True
        sim.detach_all(spill=False)
    elif k == "right":
        sim.shape.rotate(-0.12, vp.vector(0, 1, 0))
        sim.field_redraw_requested = True
        sim.detach_all(spill=False)
    elif k == "up":
        sim.shape.rotate(0.12, vp.vector(0, 0, 1))
        sim.field_redraw_requested = True
        sim.detach_all(spill=False)
    elif k == "down":
        sim.shape.rotate(-0.12, vp.vector(0, 0, 1))
        sim.field_redraw_requested = True
        sim.detach_all(spill=False)
    elif k in ["+", "="]:
        sim.shape.strength = clamp(sim.shape.strength + 0.15, 0.15, 3.0)
    elif k in ["-", "_"]:
        sim.shape.strength = clamp(sim.shape.strength - 0.15, 0.15, 3.0)


scene.bind("keydown", on_keydown)

previous = time.time()
while True:
    vp.rate(60)
    now = time.time()
    dt = clamp(now - previous, 0.001, 0.035)
    previous = now
    sim.update(dt)
