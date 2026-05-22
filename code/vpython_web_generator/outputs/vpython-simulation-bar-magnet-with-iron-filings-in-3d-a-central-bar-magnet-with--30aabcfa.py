from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# 3D VPython Simulation:
# Bar Magnet With Iron Filings in 3D + Human Control + AI Control
# ------------------------------------------------------------

scene = canvas(
    title="3D Bar Magnet With Iron Filings - AI Controlled Magnetic Field Simulation",
    width=1200,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-6, -3.2, -6)
scene.up = vector(0, 1, 0)
scene.range = 6.5

scene.caption = """
Controls:
  Arrow keys : rotate magnet
  Q / E      : roll magnet
  W / S      : pitch magnet
  A          : toggle AI
  P / Space  : pause / resume simulation
  R          : reset round
  D          : detach all particles
  O          : orbit burst
  M          : mark aligned chains
  T          : toggle trails
  C          : clear trails
  H          : hide/show help

AI:
  The built-in AI reads simulation state, chooses behavior modes, rotates/shakes/marks/spills/orbits,
  detects stagnation/completion, and automatically starts new rounds.
"""

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

FPS = 60
DT = 1.0 / FPS

MAGNET_LENGTH = 3.4
MAGNET_HEIGHT = 0.55
MAGNET_WIDTH = 0.75
CAP_THICKNESS = 0.18

PARTICLE_COUNT = 95
PARTICLE_LENGTH = 0.22
PARTICLE_RADIUS = 0.028

FIELD_LINE_COUNT = 24
FIELD_LINE_STEPS = 125
FIELD_LINE_STEP_SIZE = 0.09

BOUND = vector(5.2, 2.9, 3.4)

TRAIL_RETAIN = 85

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


def random_cloud_position():
    for _ in range(400):
        p = vector(
            rand_range(-BOUND.x * 0.88, BOUND.x * 0.88),
            rand_range(-BOUND.y * 0.80, BOUND.y * 0.80),
            rand_range(-BOUND.z * 0.85, BOUND.z * 0.85),
        )
        if abs(p.x) < MAGNET_LENGTH * 0.72 and abs(p.y) < 0.75 and abs(p.z) < 0.95:
            continue
        if mag(p) < 0.95:
            continue
        return p
    return vector(rand_range(-4, 4), rand_range(-2, 2), rand_range(-2.6, 2.6))


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


# ------------------------------------------------------------
# Stationary Environment
# ------------------------------------------------------------

container = box(
    pos=vector(0, 0, 0),
    size=2 * BOUND,
    color=vector(0.75, 0.86, 1.0),
    opacity=0.075,
)

floor_grid_lines = []
for x in [i * 0.5 for i in range(-10, 11)]:
    floor_grid_lines.append(
        curve(
            pos=[vector(x, -BOUND.y, -BOUND.z), vector(x, -BOUND.y, BOUND.z)],
            color=vector(0.78, 0.84, 0.88),
            radius=0.003,
        )
    )
for z in [i * 0.5 for i in range(-7, 8)]:
    floor_grid_lines.append(
        curve(
            pos=[vector(-BOUND.x, -BOUND.y, z), vector(BOUND.x, -BOUND.y, z)],
            color=vector(0.78, 0.84, 0.88),
            radius=0.003,
        )
    )

title_label = label(
    pos=vector(0, 3.45, 0),
    text="Bar Magnet + Iron Filings + Field Lines + AI Controller",
    height=17,
    box=False,
    color=vector(0.1, 0.14, 0.18),
)

cloud_label = label(
    pos=vector(-4.6, 2.55, 2.75),
    text="iron filings cloud",
    height=12,
    box=False,
    color=vector(0.27, 0.31, 0.34),
)

field_label = label(
    pos=vector(3.9, 2.45, -2.35),
    text="glowing magnetic field-line tubes",
    height=12,
    box=False,
    color=vector(0.0, 0.42, 0.62),
)

ai_status_label = label(
    pos=vector(-4.9, 3.02, -2.95),
    text="AI: starting",
    height=12,
    box=True,
    border=6,
    color=vector(0.08, 0.12, 0.15),
    background=vector(0.95, 0.98, 1.0),
    opacity=0.72,
)

state_label = label(
    pos=vector(4.65, 3.02, 2.75),
    text="state",
    height=11,
    box=True,
    border=5,
    color=vector(0.1, 0.12, 0.13),
    background=vector(1.0, 0.98, 0.88),
    opacity=0.68,
)

# ------------------------------------------------------------
# Bar Magnet
# ------------------------------------------------------------

class BarMagnet:
    def __init__(self):
        self.pos = vector(0, 0, 0)
        self.u = vector(1, 0, 0)
        self.v = vector(0, 1, 0)
        self.w = vector(0, 0, 1)
        self.spin_impulse = 0.0

        self.south_half = box(
            pos=self.pos - self.u * MAGNET_LENGTH * 0.25,
            size=vector(MAGNET_LENGTH * 0.5, MAGNET_HEIGHT, MAGNET_WIDTH),
            axis=self.u,
            up=self.v,
            color=vector(0.18, 0.32, 0.94),
            shininess=0.75,
        )
        self.north_half = box(
            pos=self.pos + self.u * MAGNET_LENGTH * 0.25,
            size=vector(MAGNET_LENGTH * 0.5, MAGNET_HEIGHT, MAGNET_WIDTH),
            axis=self.u,
            up=self.v,
            color=vector(0.95, 0.16, 0.12),
            shininess=0.75,
        )

        self.north_cap = cylinder(
            pos=self.pos + self.u * (MAGNET_LENGTH * 0.5),
            axis=self.u * CAP_THICKNESS,
            radius=0.50,
            color=vector(1.0, 0.28, 0.22),
            shininess=0.9,
        )
        self.south_cap = cylinder(
            pos=self.pos - self.u * (MAGNET_LENGTH * 0.5),
            axis=-self.u * CAP_THICKNESS,
            radius=0.50,
            color=vector(0.16, 0.36, 1.0),
            shininess=0.9,
        )

        self.center_band = box(
            pos=self.pos,
            size=vector(0.08, MAGNET_HEIGHT * 1.07, MAGNET_WIDTH * 1.07),
            axis=self.u,
            up=self.v,
            color=vector(0.96, 0.96, 0.86),
            shininess=0.65,
        )

        self.n_label = label(
            pos=self.north_world() + self.v * 0.65,
            text="N",
            height=22,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.95, 0.10, 0.08),
            opacity=0.88,
        )
        self.s_label = label(
            pos=self.south_world() + self.v * 0.65,
            text="S",
            height=22,
            box=True,
            border=4,
            color=color.white,
            background=vector(0.08, 0.18, 0.95),
            opacity=0.88,
        )

        self.axis_arrow = arrow(
            pos=self.pos - self.u * 0.9,
            axis=self.u * 1.8,
            shaftwidth=0.035,
            headwidth=0.13,
            headlength=0.18,
            color=vector(1.0, 0.78, 0.22),
            opacity=0.7,
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
        self.update_visuals()

    def north_world(self):
        return self.pos + self.u * (MAGNET_LENGTH * 0.5)

    def south_world(self):
        return self.pos - self.u * (MAGNET_LENGTH * 0.5)

    def world_from_local(self, local):
        return self.pos + self.u * local.x + self.v * local.y + self.w * local.z

    def local_from_world(self, world):
        r = world - self.pos
        return vector(dot(r, self.u), dot(r, self.v), dot(r, self.w))

    def update_visuals(self):
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

        self.n_label.pos = self.north_world() + self.v * 0.72
        self.s_label.pos = self.south_world() + self.v * 0.72

        self.axis_arrow.pos = self.pos - self.u * 0.95
        self.axis_arrow.axis = self.u * 1.9

    def decay_spin_meter(self):
        self.spin_impulse *= 0.90


magnet = BarMagnet()

# ------------------------------------------------------------
# Magnetic Field Model
# ------------------------------------------------------------

def magnetic_field_at(point):
    npos = magnet.north_world()
    spos = magnet.south_world()

    rn = point - npos
    rs = point - spos

    dn = max(mag(rn), 0.22)
    ds = max(mag(rs), 0.22)

    # Simple pole-pair field: field exits N and enters S.
    b = rn / (dn ** 3) - rs / (ds ** 3)

    # Mild central smoothing / inside-magnet hint.
    local = magnet.local_from_world(point)
    if abs(local.x) < MAGNET_LENGTH * 0.5 and abs(local.y) < MAGNET_HEIGHT and abs(local.z) < MAGNET_WIDTH:
        b += -magnet.u * 0.55

    return limit_vec(b, 18.0)


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
    return limit_vec(g, 16.0)


# ------------------------------------------------------------
# Field Line Tubes
# ------------------------------------------------------------

class FieldLineSystem:
    def __init__(self):
        self.lines = []
        self.seed_phases = []
        self.seed_layers = []

        for i in range(FIELD_LINE_COUNT):
            phase = 2 * math.pi * i / FIELD_LINE_COUNT
            layer = i % 3
            self.seed_phases.append(phase)
            self.seed_layers.append(layer)
            pts = [vector(0, 0, 0) for _ in range(FIELD_LINE_STEPS)]
            c = curve(
                pos=pts,
                radius=0.018 if layer != 1 else 0.014,
                color=vector(0.12, 0.74, 1.0) if layer != 2 else vector(1.0, 0.78, 0.18),
                emissive=True,
            )
            self.lines.append(c)

        self.update(force=True)

    def generate_line_points(self, phase, layer):
        radius = 0.20 + 0.16 * layer
        ring = math.cos(phase) * magnet.v + math.sin(phase) * magnet.w

        # Seed slightly outside the north pole cap.
        p = magnet.north_world() + magnet.u * 0.18 + ring * radius
        pts = []

        last_good = p
        for step in range(FIELD_LINE_STEPS):
            pts.append(p)
            b = magnetic_field_at(p)
            d = safe_norm(b, magnet.u)
            p = p + d * FIELD_LINE_STEP_SIZE
            last_good = p

            # Stop if the curve reaches the south pole; fill remaining points.
            if step > 22 and mag(p - magnet.south_world()) < 0.33 + 0.06 * layer:
                last_good = magnet.south_world() + ring * 0.10 - magnet.u * 0.10
                p = last_good
                break

            # Keep streamlines from running away forever.
            if abs(p.x) > BOUND.x * 1.3 or abs(p.y) > BOUND.y * 1.35 or abs(p.z) > BOUND.z * 1.35:
                break

        while len(pts) < FIELD_LINE_STEPS:
            pts.append(last_good)
        return pts[:FIELD_LINE_STEPS]

    def update(self, force=False):
        for i, c in enumerate(self.lines):
            pts = self.generate_line_points(self.seed_phases[i], self.seed_layers[i])
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

        if self.trails_enabled:
            self.trail_anchor.pos = self.center
        else:
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
        self.marked_timer = 0
        self.chain_score = 0
        self.clear_trail()
        self.update_visual()

    def detach(self, impulse=None):
        if impulse is None:
            impulse = random_unit_vector() * rand_range(0.2, 0.75)
        self.attached = False
        self.vel += impulse

    def attach_to_magnet(self):
        self.attached = True
        local = magnet.local_from_world(self.center)

        # Stick mostly around pole caps and near field-intense corners.
        local.x = clamp(local.x, -MAGNET_LENGTH * 0.56, MAGNET_LENGTH * 0.56)
        local.y = clamp(local.y, -MAGNET_HEIGHT * 0.72, MAGNET_HEIGHT * 0.72)
        local.z = clamp(local.z, -MAGNET_WIDTH * 0.72, MAGNET_WIDTH * 0.72)

        if abs(local.x) < MAGNET_LENGTH * 0.42:
            local.x = MAGNET_LENGTH * 0.50 * (1 if local.x >= 0 else -1)

        self.attached_local = local
        self.vel *= 0.15

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

    def collide_or_attach_with_magnet(self):
        local = magnet.local_from_world(self.center)
        expanded = vector(MAGNET_LENGTH * 0.5 + 0.16, MAGNET_HEIGHT * 0.5 + 0.13, MAGNET_WIDTH * 0.5 + 0.13)

        if abs(local.x) < expanded.x and abs(local.y) < expanded.y and abs(local.z) < expanded.z:
            near_pole = abs(local.x) > MAGNET_LENGTH * 0.37
            if near_pole or magnetic_strength(self.center) > 3.2:
                if random.random() < 0.24:
                    self.attach_to_magnet()
                    return

            px = expanded.x - abs(local.x)
            py = expanded.y - abs(local.y)
            pz = expanded.z - abs(local.z)

            if px <= py and px <= pz:
                n = magnet.u * (1 if local.x >= 0 else -1)
            elif py <= px and py <= pz:
                n = magnet.v * (1 if local.y >= 0 else -1)
            else:
                n = magnet.w * (1 if local.z >= 0 else -1)

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
        self.dir = safe_norm(lerp_vec(self.dir, bdir, clamp(7.2 * dt, 0, 1)), self.dir)

        if self.attached:
            self.center = magnet.world_from_local(self.attached_local)

            # Strong rotation can shake loose some filings.
            if magnet.spin_impulse > 0.035 and random.random() < clamp(magnet.spin_impulse * 0.018, 0, 0.10):
                self.detach(impulse=(self.center - magnet.pos) * 0.35 + random_unit_vector() * 0.22)
            else:
                self.vel *= 0.15
                self.update_visual()
                return

        strength = mag(b)
        grad = field_gradient(self.center)

        # Ferromagnetic grains migrate toward stronger field regions and drift along lines.
        f_grad = grad * 0.030
        f_flow = bdir * (0.12 * self.flow_sign) * clamp(strength, 0, 2.4)
        f_noise = random_unit_vector() * 0.010
        f = f_grad + f_flow + f_noise + external_force

        self.vel += limit_vec(f, 0.55) * dt
        self.vel *= 0.965
        self.vel = limit_vec(self.vel, 1.45)

        self.center += self.vel * dt

        self.collide_or_attach_with_magnet()
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
    max_bonds = 54

    for i in range(len(particles)):
        if shown >= max_bonds:
            break
        p = particles[i]
        for j in range(i + 1, len(particles)):
            if shown >= max_bonds:
                break
            q = particles[j]
            d = mag(q.center - p.center)
            if d < 0.30 and abs(dot(p.dir, q.dir)) > 0.75:
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

    for p in particles:
        b = magnetic_field_at(p.center)
        bdir = safe_norm(b, magnet.u)
        avg_alignment += abs(dot(safe_norm(p.dir), bdir))
        avg_radius += mag(p.center - magnet.pos)
        if p.marked_timer > 0:
            marked_count += 1

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
        if align > 0.86 or p.chain_score > 0.45 or p.attached:
            p.marked_timer = max(p.marked_timer, duration)


def orbit_burst(clockwise=True, strength=0.85):
    sign = 1 if clockwise else -1
    for p in particles:
        r = p.center - magnet.pos
        tangent = cross(vector(0, 1, 0), r)
        if mag(tangent) < 0.1:
            tangent = cross(magnet.u, r)
        tangent = safe_norm(tangent, random_unit_vector())
        p.vel += tangent * sign * rand_range(0.15, strength)


def spill_cloud(side=None):
    if side is None:
        side = random.choice(["left", "right", "top", "front"])

    for i, p in enumerate(particles):
        p.attached = False
        p.marked_timer = 0
        p.chain_score = 0

        if side == "left":
            p.center = vector(-BOUND.x * 0.88, rand_range(-1.7, 2.2), rand_range(-2.4, 2.4))
            p.vel = vector(rand_range(0.35, 0.9), rand_range(-0.15, 0.15), rand_range(-0.2, 0.2))
        elif side == "right":
            p.center = vector(BOUND.x * 0.88, rand_range(-1.7, 2.2), rand_range(-2.4, 2.4))
            p.vel = vector(rand_range(-0.9, -0.35), rand_range(-0.15, 0.15), rand_range(-0.2, 0.2))
        elif side == "front":
            p.center = vector(rand_range(-3.8, 3.8), rand_range(-1.6, 2.1), BOUND.z * 0.86)
            p.vel = vector(rand_range(-0.25, 0.25), rand_range(-0.1, 0.15), rand_range(-0.9, -0.35))
        else:
            p.center = vector(rand_range(-4.1, 4.1), BOUND.y * 0.88, rand_range(-2.6, 2.6))
            p.vel = vector(rand_range(-0.2, 0.2), rand_range(-0.9, -0.35), rand_range(-0.2, 0.2))

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
        "GATHER",
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
        self.last_switch_time = time.time()

    def choose_new_mode(self, state, reason="time"):
        attached_ratio = state["attached_count"] / PARTICLE_COUNT
        speed = state["avg_speed"]
        clumps = state["clump_count"]
        alignment = state["avg_alignment"]

        possible = []

        if reason in ("complete", "stagnant"):
            possible += ["SPILL_FROM_EDGE", "SHAKE_DETACH", "RESET_RITUAL", "CHAOTIC_MIX"]
        elif attached_ratio > 0.62:
            possible += ["SHAKE_DETACH", "ORBIT_WRAP", "MARK_CHAINS"]
        elif speed < 0.045 and clumps > 18:
            possible += ["MARK_CHAINS", "ARTIST_TRAILS", "ORBIT_WRAP"]
        elif alignment < 0.62:
            possible += ["CAREFUL_ALIGN", "GATHER", "ROTATE_SWEEP"]
        elif clumps < 10:
            possible += ["GATHER", "CAREFUL_ALIGN", "ROTATE_SWEEP"]
        else:
            possible += ["ROTATE_SWEEP", "ORBIT_WRAP", "ARTIST_TRAILS", "CHAOTIC_MIX", "MARK_CHAINS"]

        # Avoid repeating the same mode forever.
        possible = [m for m in possible if m != self.mode] or self.MODES[:]

        self.mode = random.choice(possible)
        self.mode_timer = 0.0
        self.last_switch_time = time.time()

        if self.mode == "OBSERVE":
            self.mode_duration = rand_range(1.2, 2.4)
        elif self.mode == "GATHER":
            self.mode_duration = rand_range(4.0, 7.0)
        elif self.mode == "ROTATE_SWEEP":
            self.mode_duration = rand_range(4.0, 6.5)
        elif self.mode == "SHAKE_DETACH":
            self.mode_duration = rand_range(2.0, 3.6)
        elif self.mode == "ORBIT_WRAP":
            self.mode_duration = rand_range(3.0, 5.8)
        elif self.mode == "MARK_CHAINS":
            self.mode_duration = rand_range(1.2, 2.2)
        elif self.mode == "SPILL_FROM_EDGE":
            self.mode_duration = rand_range(2.0, 3.2)
            spill_cloud(random.choice(["left", "right", "top", "front"]))
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
        complete = attached_ratio > 0.78 and state["avg_speed"] < 0.08
        empty_or_halted = state["free_count"] < 5 or state["avg_radius"] < 0.55

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

        t = self.mode_timer
        phase = time.time() * 0.8 + self.round_seed * 10

        if self.mode == "OBSERVE":
            self.action_rotate(vector(0, 1, 0), 0.002 * math.sin(phase))

        elif self.mode == "GATHER":
            self.action_rotate(vector(0, 1, 0), 0.004)
            self.action_rotate(vector(0, 0, 1), 0.0015 * math.sin(phase * 1.7))

        elif self.mode == "ROTATE_SWEEP":
            self.action_rotate(vector(0, 1, 0), 0.012 + 0.006 * math.sin(phase))
            self.action_rotate(vector(0, 0, 1), 0.006 * math.sin(phase * 0.65))

        elif self.mode == "SHAKE_DETACH":
            self.action_shake(amount=0.055)
            self.external_force = random_unit_vector() * 0.20

        elif self.mode == "ORBIT_WRAP":
            self.action_rotate(vector(0, 1, 0), 0.015)
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
    elif k == "s":
        spill_cloud(random.choice(["left", "right", "top", "front"]))
    elif k == "h":
        show_help = not show_help
        scene.caption = scene.caption if show_help else ""


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
        f"avg speed: {state['avg_speed']:.3f}\n"
        f"alignment: {state['avg_alignment']:.2f}\n"
        f"trails: {'on' if trails_enabled else 'off'}"
    )

    field_label.pos = magnet.north_world() + magnet.v * 1.75 + magnet.w * 1.2
    cloud_label.pos = vector(-4.6, 2.55, 2.75)


# ------------------------------------------------------------
# Startup Visual State
# ------------------------------------------------------------

local_light(pos=vector(0, 5, 2), color=vector(0.7, 0.75, 0.8))
local_light(pos=vector(-4, 3, -4), color=vector(0.45, 0.55, 0.70))

# Give the opening scene a gentle spill so the cloud is visibly moving.
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
        state = read_simulation_state()
        update_labels(state)
        continue

    apply_human_controls(DT)

    state = read_simulation_state()

    # AI can run automatically while human control still works.
    # Human input does not disable AI; it temporarily softens the AI's external force.
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

    if frame_counter % 5 == 0:
        state = read_simulation_state()
        update_labels(state)
