from vpython import *
import math
import random

# ============================================================
# 3D VPython Simulation:
# Magnetic Field of a Circular Loop Coil with Floating Compass Needles
# Includes an expressive AI controller with behavior modes, reset loop,
# stagnation detection, and human override controls.
# ============================================================

scene = canvas(
    title="Magnetic Field of a Circular Loop Coil — Compass Needle AI Simulation",
    width=1200,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0.15, 0),
)
scene.forward = vector(-1.9, -1.05, -2.15)
scene.range = 4.7
scene.autoscale = False

# -----------------------------
# Global Simulation Parameters
# -----------------------------
LOOP_RADIUS = 1.15
COIL_THICKNESS = 0.045
SEGMENTS = 56
FIELD_SCALE = 0.075
SOFTENING = 0.055
BOUND_X = 3.15
BOUND_Y = 2.20
BOUND_Z = 3.15

MAX_NEEDLES = 30
NEEDLE_LENGTH = 0.34
NEEDLE_WIDTH = 0.042

dt = 0.018
sim_time = 0.0
paused = False
show_trails = True
show_labels = True

current_strength = 1.0
selected_index = 0
human_override_timer = 0.0

needles = []
particles = []
markers = []
field_curves = []
field_line_points = []
coil_current_arrows = []

# -----------------------------
# Caption / Controls
# -----------------------------
scene.caption = """
Controls:
SPACE pause/resume | A toggle AI | M next AI mode | R reset round | C clear trails/marks
+ / - change current | I invert current | N select compass needle
Arrow keys move selected needle on X/Z | PgUp/PgDn move Y | D detach | O attach orbit | F attach field line
P drop marker | L labels | T trails | H short human override

The AI can read state, move/organize needles, attach/detach them, orbit, wrap, paint markers,
reverse current, detect stagnation/completion, and start new rounds automatically.
"""

# ============================================================
# Utility Functions
# ============================================================

def clamp(x, a, b):
    return max(a, min(b, x))

def safe_norm(v, fallback=vector(0, 1, 0)):
    m = mag(v)
    if m < 1e-9:
        return fallback
    return v / m

def lerp(a, b, t):
    return a * (1 - t) + b * t

def rotate_y(p, ang):
    c = math.cos(ang)
    s = math.sin(ang)
    return vector(c * p.x + s * p.z, p.y, -s * p.x + c * p.z)

def palette(t):
    """Light-field scientific colormap: deep blue -> cyan -> green -> yellow -> red."""
    t = clamp(t, 0, 1)
    stops = [
        (0.00, vector(0.18, 0.30, 0.92)),
        (0.25, vector(0.05, 0.72, 1.00)),
        (0.50, vector(0.13, 0.86, 0.44)),
        (0.74, vector(1.00, 0.88, 0.20)),
        (1.00, vector(1.00, 0.20, 0.12)),
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            return lerp(c0, c1, (t - t0) / (t1 - t0))
    return stops[-1][1]

def field_color_from_strength(bmag):
    n = math.log(1 + 2.15 * bmag) / math.log(1 + 5.3)
    return palette(clamp(n, 0, 1))

def nearest_wire_vector(p):
    radial = vector(p.x, 0, p.z)
    if mag(radial) < 1e-8:
        wire_point = vector(LOOP_RADIUS, 0, 0)
    else:
        wire_point = safe_norm(radial) * LOOP_RADIUS
    return p - wire_point

# ============================================================
# Magnetic Field Model: Circular Current Loop in horizontal XZ plane
# Axis is vertical Y. Numerical Biot-Savart integration.
# ============================================================

segment_positions = []
segment_dls = []

def build_loop_segments():
    segment_positions.clear()
    segment_dls.clear()
    dtheta = 2 * math.pi / SEGMENTS
    for i in range(SEGMENTS):
        theta = (i + 0.5) * dtheta
        pos = vector(LOOP_RADIUS * math.cos(theta), 0, LOOP_RADIUS * math.sin(theta))
        dl = vector(-LOOP_RADIUS * math.sin(theta), 0, LOOP_RADIUS * math.cos(theta)) * dtheta
        segment_positions.append(pos)
        segment_dls.append(dl)

def magnetic_field_at(p):
    B = vector(0, 0, 0)
    for r0, dl in zip(segment_positions, segment_dls):
        r = p - r0
        r2 = dot(r, r) + SOFTENING * SOFTENING
        B += cross(dl, r) / (r2 * math.sqrt(r2))
    return B * FIELD_SCALE * current_strength

def field_strength_at(p):
    return mag(magnetic_field_at(p))

def field_unit_at(p):
    return safe_norm(magnetic_field_at(p), vector(0, 1 if current_strength >= 0 else -1, 0))

build_loop_segments()

# ============================================================
# Stationary Scene Objects
# ============================================================

floor_box = box(
    pos=vector(0, -BOUND_Y - 0.06, 0),
    size=vector(2 * BOUND_X + 0.4, 0.025, 2 * BOUND_Z + 0.4),
    color=vector(0.86, 0.91, 0.94),
    opacity=0.35,
)

boundary_box = box(
    pos=vector(0, 0, 0),
    size=vector(2 * BOUND_X, 2 * BOUND_Y, 2 * BOUND_Z),
    color=vector(0.65, 0.78, 0.90),
    opacity=0.055,
)

axis_y = arrow(
    pos=vector(0, -1.9, 0),
    axis=vector(0, 3.8, 0),
    shaftwidth=0.012,
    headwidth=0.07,
    headlength=0.13,
    color=vector(0.50, 0.58, 0.68),
    opacity=0.55,
)

axis_label = label(
    pos=vector(0.17, 2.07, 0),
    text="coil axis / B through center",
    height=12,
    box=False,
    color=vector(0.26, 0.33, 0.43),
)

coil_rings = []
for yy, op, rad_shift in [(-0.055, 0.42, -0.015), (0, 1.0, 0), (0.055, 0.42, 0.015)]:
    coil_rings.append(
        ring(
            pos=vector(0, yy, 0),
            axis=vector(0, 1, 0),
            radius=LOOP_RADIUS + rad_shift,
            thickness=COIL_THICKNESS,
            color=vector(1.0, 0.52, 0.12),
            opacity=op,
        )
    )

coil_label = label(
    pos=vector(1.55, 0.17, 0.0),
    text="stationary current loop coil",
    height=13,
    box=False,
    color=vector(0.54, 0.27, 0.05),
)

center_label = label(
    pos=vector(-0.42, 0.23, 0.05),
    text="strong central field",
    height=11,
    box=False,
    color=vector(0.24, 0.30, 0.42),
)

def build_current_arrows():
    global coil_current_arrows
    for a in coil_current_arrows:
        a.visible = False
    coil_current_arrows = []
    for i in range(10):
        th = 2 * math.pi * i / 10.0
        p = vector(LOOP_RADIUS * math.cos(th), 0.09, LOOP_RADIUS * math.sin(th))
        tangent = vector(-math.sin(th), 0, math.cos(th))
        arr = arrow(
            pos=p - tangent * 0.105,
            axis=tangent * 0.21,
            shaftwidth=0.023,
            headwidth=0.07,
            headlength=0.08,
            color=vector(1.0, 0.35, 0.08),
        )
        coil_current_arrows.append(arr)

def update_current_arrows():
    sign = 1 if current_strength >= 0 else -1
    for i, arr in enumerate(coil_current_arrows):
        th = 2 * math.pi * i / len(coil_current_arrows)
        tangent = vector(-math.sin(th), 0, math.cos(th)) * sign
        p = vector(LOOP_RADIUS * math.cos(th), 0.09, LOOP_RADIUS * math.sin(th))
        arr.pos = p - tangent * 0.105
        arr.axis = tangent * 0.21
        arr.color = vector(1.0, 0.31, 0.06) if sign > 0 else vector(0.15, 0.45, 1.0)

build_current_arrows()

# ============================================================
# Field Line Visualization
# ============================================================

def integrate_field_line(seed, direction=1, step=0.058, steps=220):
    pts = []
    p = vector(seed.x, seed.y, seed.z)
    for _ in range(steps):
        if abs(p.x) > BOUND_X * 1.15 or abs(p.y) > BOUND_Y * 1.15 or abs(p.z) > BOUND_Z * 1.15:
            break
        pts.append(vector(p.x, p.y, p.z))
        b = magnetic_field_at(p)
        if mag(b) < 1e-7:
            break
        p = p + safe_norm(b) * step * direction
    return pts

def make_field_lines():
    global field_curves, field_line_points
    for c in field_curves:
        c.visible = False
    field_curves = []
    field_line_points = []

    seeds = [
        vector(0.16, 0.0, 0),
        vector(0.36, 0.0, 0),
        vector(0.62, 0.0, 0),
        vector(0.88, 0.0, 0),
        vector(1.26, 0.0, 0),
        vector(1.55, 0.0, 0),
        vector(1.92, 0.0, 0),
    ]

    planes = 10
    for j in range(planes):
        ang = 2 * math.pi * j / planes
        for seed in seeds:
            fwd = integrate_field_line(seed, 1)
            bwd = integrate_field_line(seed, -1)
            pts_2d = list(reversed(bwd)) + [seed] + fwd
            if len(pts_2d) < 8:
                continue

            pts = [rotate_y(p, ang) for p in pts_2d]
            seed_strength = field_strength_at(rotate_y(seed, ang))
            col = field_color_from_strength(seed_strength)
            crv = curve(pos=pts, radius=0.0075, color=col, opacity=0.72)
            field_curves.append(crv)
            field_line_points.append(pts)

make_field_lines()

# ============================================================
# Field Strength Color Bar
# ============================================================

colorbar_items = []
def build_colorbar():
    x = 3.72
    z = -2.92
    y0 = -1.20
    h = 0.18
    n = 15
    for i in range(n):
        t = i / (n - 1)
        b = box(
            pos=vector(x, y0 + i * h, z),
            size=vector(0.14, h * 0.92, 0.05),
            color=palette(t),
            opacity=0.92,
        )
        colorbar_items.append(b)
    label(pos=vector(x + 0.05, y0 + n * h + 0.04, z), text="|B| high", height=11, box=False, color=vector(0.30, 0.25, 0.25))
    label(pos=vector(x + 0.05, y0 - 0.16, z), text="|B| low", height=11, box=False, color=vector(0.30, 0.25, 0.25))
    label(pos=vector(x - 0.03, y0 + 0.5 * n * h, z - 0.02), text="field strength", height=12, box=False, color=vector(0.20, 0.25, 0.30))

build_colorbar()

# ============================================================
# Visual Particle / Marker Classes
# ============================================================

class FieldParticle:
    def __init__(self, pos, vel=None, col=None, lifetime=3.2):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vel if vel is not None else vector(random.uniform(-0.2, 0.2), random.uniform(-0.1, 0.2), random.uniform(-0.2, 0.2))
        self.age = 0
        self.lifetime = lifetime
        self.obj = sphere(
            pos=self.pos,
            radius=random.uniform(0.018, 0.035),
            color=col if col is not None else field_color_from_strength(field_strength_at(pos)),
            opacity=0.72,
            shininess=0.25,
        )

    def update(self, dt):
        self.age += dt
        b = field_unit_at(self.pos)
        self.vel += b * 0.12 * dt
        self.vel *= 0.992
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0, 0.72 * (1 - self.age / self.lifetime))
        if self.age >= self.lifetime:
            self.obj.visible = False
            return False
        return True

def drop_marker(pos, col=None, radius=0.035, permanent=True):
    global markers
    if len(markers) > 180:
        old = markers.pop(0)
        old.visible = False
    m = sphere(
        pos=pos,
        radius=radius,
        color=col if col is not None else field_color_from_strength(field_strength_at(pos)),
        opacity=0.74 if permanent else 0.45,
        shininess=0.1,
    )
    markers.append(m)
    return m

def clear_markers():
    for m in markers:
        m.visible = False
    markers.clear()

# ============================================================
# Compass Needle Object
# ============================================================

class CompassNeedle:
    def __init__(self, idx, pos):
        self.idx = idx
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(random.uniform(-0.06, 0.06), random.uniform(-0.03, 0.03), random.uniform(-0.06, 0.06))
        self.dir = safe_norm(vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        self.lock = random.uniform(0.12, 0.5)
        self.attached = None
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.orbit_radius = random.uniform(1.28, 2.0)
        self.orbit_y = random.uniform(-0.45, 0.45)
        self.orbit_speed = random.choice([-1, 1]) * random.uniform(0.25, 0.75)
        self.field_line_id = 0
        self.field_u = 0.0
        self.field_speed = random.uniform(8.0, 18.0)
        self.field_dir = random.choice([-1, 1])
        self.ai_force = vector(0, 0, 0)
        self.desired_pos = None
        self.human_force = vector(0, 0, 0)

        self.body = arrow(
            pos=self.pos - self.dir * NEEDLE_LENGTH * 0.5,
            axis=self.dir * NEEDLE_LENGTH,
            shaftwidth=NEEDLE_WIDTH,
            headwidth=NEEDLE_WIDTH * 2.7,
            headlength=NEEDLE_LENGTH * 0.26,
            color=field_color_from_strength(field_strength_at(self.pos)),
        )
        self.pivot = sphere(
            pos=self.pos,
            radius=0.045,
            color=vector(0.98, 0.98, 1.0),
            opacity=0.85,
            shininess=0.45,
        )
        self.trail = curve(pos=[self.pos], radius=0.006, color=vector(0.22, 0.48, 1.0), opacity=0.45, retain=95)
        self.lbl = label(
            pos=self.pos + vector(0, 0.18, 0),
            text="",
            height=9,
            box=False,
            color=vector(0.10, 0.17, 0.25),
            opacity=0,
            visible=False,
        )

    def reset(self, pos=None):
        if pos is None:
            pos = vector(
                random.uniform(-2.55, 2.55),
                random.uniform(-1.05, 1.65),
                random.uniform(-2.55, 2.55),
            )
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(random.uniform(-0.10, 0.10), random.uniform(-0.05, 0.05), random.uniform(-0.10, 0.10))
        self.dir = safe_norm(vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
        self.lock = random.uniform(0.10, 0.42)
        self.attached = None
        self.desired_pos = None
        self.ai_force = vector(0, 0, 0)
        self.human_force = vector(0, 0, 0)
        self.trail.clear()
        self.trail.append(self.pos)
        self.update_visuals()

    def clear_trail(self):
        self.trail.clear()
        self.trail.append(self.pos)

    def attach_orbit(self, radius=None, y=None, speed=None):
        self.attached = "orbit"
        if radius is not None:
            self.orbit_radius = radius
        if y is not None:
            self.orbit_y = y
        if speed is not None:
            self.orbit_speed = speed
        self.orbit_angle = math.atan2(self.pos.z, self.pos.x)

    def attach_field_line(self, line_id=None, speed=None):
        if not field_line_points:
            return
        self.attached = "field"
        self.field_line_id = int(line_id if line_id is not None else random.randrange(len(field_line_points))) % len(field_line_points)
        pts = field_line_points[self.field_line_id]
        best_i = 0
        best_d = 1e9
        for i, p in enumerate(pts):
            d = mag2(self.pos - p)
            if d < best_d:
                best_d = d
                best_i = i
        self.field_u = float(best_i)
        self.field_dir = random.choice([-1, 1])
        if speed is not None:
            self.field_speed = speed

    def detach(self, impulse=True):
        if self.attached and impulse:
            self.vel += self.dir * random.uniform(0.08, 0.22)
        self.attached = None
        self.desired_pos = None

    def bounce_bounds(self):
        bounce = 0.64
        if self.pos.x > BOUND_X:
            self.pos.x = BOUND_X
            self.vel.x *= -bounce
        if self.pos.x < -BOUND_X:
            self.pos.x = -BOUND_X
            self.vel.x *= -bounce
        if self.pos.y > BOUND_Y:
            self.pos.y = BOUND_Y
            self.vel.y *= -bounce
        if self.pos.y < -BOUND_Y:
            self.pos.y = -BOUND_Y
            self.vel.y *= -bounce
        if self.pos.z > BOUND_Z:
            self.pos.z = BOUND_Z
            self.vel.z *= -bounce
        if self.pos.z < -BOUND_Z:
            self.pos.z = -BOUND_Z
            self.vel.z *= -bounce

    def update_free_motion(self, dt):
        b = magnetic_field_at(self.pos)
        bu = safe_norm(b, self.dir)
        bmag = mag(b)

        # Compass alignment: needle rotates and locks to local magnetic field direction.
        lock_rate = clamp(0.06 + 0.08 * bmag + self.lock, 0.05, 0.75)
        self.dir = safe_norm(lerp(self.dir, bu, lock_rate * dt * 5.5), bu)
        self.lock = clamp(self.lock + dt * 0.023 * (0.8 + bmag), 0.08, 0.96)

        # Floating drift: field-guided flow + attraction toward high-gradient coil region.
        wire_vec = nearest_wire_vector(self.pos)
        to_wire = -safe_norm(wire_vec) / (0.75 + mag(wire_vec) ** 2)
        field_flow = bu * (0.030 + 0.032 * clamp(bmag, 0, 2.0))
        bob = vector(0, 0.018 * math.sin(sim_time * 1.7 + self.idx), 0)
        wander = vector(
            random.uniform(-0.018, 0.018),
            random.uniform(-0.010, 0.010),
            random.uniform(-0.018, 0.018),
        )

        if self.desired_pos is not None:
            spring = (self.desired_pos - self.pos) * 0.70
        else:
            spring = vector(0, 0, 0)

        accel = field_flow + to_wire * 0.055 + bob + wander + self.ai_force + self.human_force + spring
        self.vel += accel * dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.bounce_bounds()

    def update_orbit(self, dt):
        self.orbit_angle += self.orbit_speed * dt * (1.0 + 0.18 * math.sin(sim_time + self.idx))
        bob = 0.10 * math.sin(2.3 * sim_time + self.idx)
        target = vector(
            self.orbit_radius * math.cos(self.orbit_angle),
            self.orbit_y + bob,
            self.orbit_radius * math.sin(self.orbit_angle),
        )
        self.vel = (target - self.pos) / max(dt, 1e-6) * 0.34
        self.pos = lerp(self.pos, target, 0.11)
        bu = field_unit_at(self.pos)
        self.dir = safe_norm(lerp(self.dir, bu, 0.25), bu)

    def update_field_attachment(self, dt):
        if not field_line_points:
            self.detach(False)
            return
        pts = field_line_points[self.field_line_id % len(field_line_points)]
        if len(pts) < 2:
            self.detach(False)
            return
        self.field_u += self.field_dir * self.field_speed * dt
        if self.field_u >= len(pts) - 2:
            self.field_u = len(pts) - 2
            self.field_dir = -1
        if self.field_u <= 0:
            self.field_u = 0
            self.field_dir = 1

        i = int(self.field_u)
        f = self.field_u - i
        p = lerp(pts[i], pts[i + 1], f)
        tangent = safe_norm(pts[i + 1] - pts[i], field_unit_at(p))
        self.vel = (p - self.pos) / max(dt, 1e-6) * 0.23
        self.pos = lerp(self.pos, p, 0.18)
        self.dir = safe_norm(lerp(self.dir, tangent * self.field_dir, 0.22), field_unit_at(self.pos))

    def update(self, dt):
        if self.attached == "orbit":
            self.update_orbit(dt)
        elif self.attached == "field":
            self.update_field_attachment(dt)
        else:
            self.update_free_motion(dt)

        self.ai_force = vector(0, 0, 0)
        self.human_force = vector(0, 0, 0)
        self.update_visuals()

    def update_visuals(self):
        bmag = field_strength_at(self.pos)
        col = field_color_from_strength(bmag)
        if self.idx == selected_index:
            self.body.color = vector(1.0, 0.16, 0.18)
            self.pivot.color = vector(1.0, 0.95, 0.35)
        else:
            self.body.color = col
            self.pivot.color = vector(0.97, 0.985, 1.0)

        self.body.pos = self.pos - self.dir * NEEDLE_LENGTH * 0.5
        self.body.axis = self.dir * NEEDLE_LENGTH
        self.pivot.pos = self.pos

        self.trail.visible = show_trails
        if show_trails:
            self.trail.append(self.pos)

        self.lbl.visible = show_labels and (self.idx == selected_index or self.idx < 5)
        if self.lbl.visible:
            state = "free" if self.attached is None else self.attached
            self.lbl.pos = self.pos + vector(0, 0.18, 0)
            self.lbl.text = f"N{self.idx} {state}\n|B|={bmag:.2f}"

# ============================================================
# Needles and Collisions
# ============================================================

def create_needles():
    needles.clear()
    for i in range(MAX_NEEDLES):
        p = vector(
            random.uniform(-2.55, 2.55),
            random.uniform(-0.90, 1.65),
            random.uniform(-2.55, 2.55),
        )
        if mag(vector(p.x, 0, p.z)) < 0.45:
            p.x += random.choice([-1, 1]) * 0.7
        needles.append(CompassNeedle(i, p))

def collide_needles():
    min_d = 0.17
    for i in range(len(needles)):
        for j in range(i + 1, len(needles)):
            a = needles[i]
            b = needles[j]
            delta = b.pos - a.pos
            d = mag(delta)
            if 1e-7 < d < min_d:
                n = delta / d
                overlap = min_d - d
                if a.attached is None:
                    a.pos -= n * overlap * 0.5
                    a.vel -= n * 0.035
                if b.attached is None:
                    b.pos += n * overlap * 0.5
                    b.vel += n * 0.035
                for _ in range(2):
                    particles.append(FieldParticle((a.pos + b.pos) * 0.5, vel=n * random.uniform(-0.15, 0.15), col=vector(1.0, 0.72, 0.16), lifetime=0.9))

create_needles()

# ============================================================
# Reset / Round Loop
# ============================================================

round_label = label(
    pos=vector(-3.35, 2.33, -2.95),
    text="",
    height=13,
    box=True,
    border=5,
    color=vector(0.12, 0.20, 0.30),
    background=vector(0.94, 0.98, 1.0),
    opacity=0.55,
)

def clear_particles():
    for p in particles:
        p.obj.visible = False
    particles.clear()

def reset_round(reason="manual reset", keep_current=False):
    global current_strength, selected_index
    clear_particles()
    clear_markers()
    selected_index = 0

    if not keep_current:
        current_strength = random.choice([-1, 1]) * random.uniform(0.75, 1.35)
        update_current_arrows()

    for i, n in enumerate(needles):
        angle = 2 * math.pi * i / len(needles)
        radius = random.uniform(1.45, 2.85)
        p = vector(
            radius * math.cos(angle) + random.uniform(-0.25, 0.25),
            random.uniform(-1.0, 1.55),
            radius * math.sin(angle) + random.uniform(-0.25, 0.25),
        )
        n.reset(p)

    for k in range(24):
        th = 2 * math.pi * k / 24
        p = vector(LOOP_RADIUS * math.cos(th), random.uniform(-0.05, 0.25), LOOP_RADIUS * math.sin(th))
        particles.append(FieldParticle(p, vel=field_unit_at(p) * random.uniform(0.10, 0.35), col=vector(1.0, 0.50, 0.10), lifetime=1.8))

# ============================================================
# Expressive AI Controller
# ============================================================

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode = "observe"
        self.modes = [
            "observe",
            "align",
            "gather",
            "scatter",
            "orbit",
            "paint",
            "wrap",
            "invert",
            "careful_sort",
            "chaos_spill",
        ]
        self.mode_index = 0
        self.mode_timer = 0.0
        self.mode_duration = 7.5
        self.round = 1
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_avg_pos = vector(0, 0, 0)
        self.activity_ema = 1.0
        self.last_marker_time = 0.0
        self.loop_delay = 2.4
        self.round_complete = False

    def next_mode(self, forced=None):
        if forced is not None:
            self.mode = forced
            self.mode_index = self.modes.index(forced) if forced in self.modes else 0
        else:
            self.mode_index = (self.mode_index + 1) % len(self.modes)
            self.mode = self.modes[self.mode_index]
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(5.0, 10.5)

        if self.mode == "scatter":
            self.detach_all()
        if self.mode == "orbit":
            self.attach_orbit_ring()
        if self.mode == "paint":
            self.detach_all()
        if self.mode == "wrap":
            self.detach_all()
        if self.mode == "invert":
            self.invert_current()
        if self.mode == "chaos_spill":
            self.detach_all()

    def read_state(self):
        if not needles:
            return {
                "avg_speed": 0,
                "avg_align_error": 1,
                "avg_b": 0,
                "attached_count": 0,
                "avg_pos": vector(0, 0, 0),
                "spread": 0,
                "selected_b": 0,
            }

        avg_speed = 0
        avg_align_error = 0
        avg_b = 0
        attached_count = 0
        avg_pos = vector(0, 0, 0)

        for n in needles:
            avg_speed += mag(n.vel)
            bu = field_unit_at(n.pos)
            avg_align_error += 1 - abs(dot(safe_norm(n.dir), bu))
            avg_b += field_strength_at(n.pos)
            avg_pos += n.pos
            if n.attached is not None:
                attached_count += 1

        count = len(needles)
        avg_speed /= count
        avg_align_error /= count
        avg_b /= count
        avg_pos /= count

        spread = 0
        for n in needles:
            spread += mag(n.pos - avg_pos)
        spread /= count

        return {
            "avg_speed": avg_speed,
            "avg_align_error": avg_align_error,
            "avg_b": avg_b,
            "attached_count": attached_count,
            "avg_pos": avg_pos,
            "spread": spread,
            "selected_b": field_strength_at(needles[selected_index].pos),
        }

    def detect_stagnation_or_completion(self, state, dt):
        movement = state["avg_speed"] + state["avg_align_error"] * 0.08 + mag(state["avg_pos"] - self.last_avg_pos) * 0.10
        self.activity_ema = 0.94 * self.activity_ema + 0.06 * movement
        self.last_avg_pos = state["avg_pos"]

        stable = state["avg_speed"] < 0.026 and state["avg_align_error"] < 0.075
        all_attached_stable = state["attached_count"] >= int(0.84 * len(needles)) and state["avg_speed"] < 0.06
        low_activity = self.activity_ema < 0.035

        if stable or all_attached_stable or low_activity:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 0.55)

        complete = self.stagnation_timer > 8.0 or len(needles) == 0
        return complete

    def update(self, dt):
        global human_override_timer

        if not self.enabled:
            return

        if human_override_timer > 0:
            return

        state = self.read_state()
        self.mode_timer += dt

        complete = self.detect_stagnation_or_completion(state, dt)
        if complete:
            self.completion_timer += dt
            self.round_complete = True
            if self.completion_timer > self.loop_delay:
                self.round += 1
                reset_round("AI loop reset")
                self.stagnation_timer = 0
                self.completion_timer = 0
                self.round_complete = False
                self.next_mode(random.choice(["observe", "align", "paint", "orbit"]))
                return
        else:
            self.completion_timer = 0
            self.round_complete = False

        if self.mode_timer > self.mode_duration:
            if state["spread"] < 1.15:
                self.next_mode(random.choice(["scatter", "chaos_spill", "orbit"]))
            elif state["avg_align_error"] > 0.24:
                self.next_mode("align")
            elif state["attached_count"] > len(needles) * 0.72:
                self.next_mode(random.choice(["paint", "invert", "scatter"]))
            else:
                self.next_mode()

        if self.mode == "observe":
            self.behavior_observe(state, dt)
        elif self.mode == "align":
            self.behavior_align(state, dt)
        elif self.mode == "gather":
            self.behavior_gather(state, dt)
        elif self.mode == "scatter":
            self.behavior_scatter(state, dt)
        elif self.mode == "orbit":
            self.behavior_orbit(state, dt)
        elif self.mode == "paint":
            self.behavior_paint(state, dt)
        elif self.mode == "wrap":
            self.behavior_wrap(state, dt)
        elif self.mode == "invert":
            self.behavior_invert(state, dt)
        elif self.mode == "careful_sort":
            self.behavior_careful_sort(state, dt)
        elif self.mode == "chaos_spill":
            self.behavior_chaos_spill(state, dt)

    def detach_all(self):
        for n in needles:
            n.detach(impulse=False)

    def invert_current(self):
        global current_strength
        current_strength *= -1
        update_current_arrows()
        for n in needles:
            n.lock = max(0.08, n.lock * 0.38)
            n.vel += field_unit_at(n.pos) * random.uniform(-0.06, 0.06)

    def attach_orbit_ring(self):
        for i, n in enumerate(needles):
            radius = random.uniform(1.42, 2.45)
            y = -0.75 + 1.5 * (i / max(1, len(needles) - 1))
            speed = random.choice([-1, 1]) * random.uniform(0.34, 0.86)
            if i % 4 != 0:
                n.attach_orbit(radius=radius, y=y, speed=speed)

    def behavior_observe(self, state, dt):
        for i, n in enumerate(needles):
            if n.attached is not None and random.random() < 0.006:
                n.detach()
            if n.attached is None:
                n.ai_force += field_unit_at(n.pos) * 0.012
            if random.random() < 0.0017:
                drop_marker(n.pos, field_color_from_strength(field_strength_at(n.pos)), radius=0.022)

    def behavior_align(self, state, dt):
        for n in needles:
            if n.attached is not None and random.random() < 0.022:
                n.detach(False)
            bu = field_unit_at(n.pos)
            n.ai_force += bu * 0.055
            n.lock = clamp(n.lock + dt * 0.19, 0.1, 1.0)
            if random.random() < 0.001:
                particles.append(FieldParticle(n.pos, vel=bu * 0.22, col=field_color_from_strength(field_strength_at(n.pos)), lifetime=1.4))

    def behavior_gather(self, state, dt):
        target_ring = 0.62 + 0.13 * math.sin(sim_time * 1.1)
        for i, n in enumerate(needles):
            n.detach(False) if n.attached and random.random() < 0.010 else None
            angle = 2 * math.pi * i / len(needles) + 0.22 * math.sin(sim_time * 0.5)
            target = vector(target_ring * math.cos(angle), 0.42 * math.sin(angle * 2 + sim_time), target_ring * math.sin(angle))
            n.desired_pos = target
            n.ai_force += (target - n.pos) * 0.22
        if random.random() < 0.04:
            drop_marker(vector(0, 0, 0), vector(1.0, 0.85, 0.20), radius=0.025)

    def behavior_scatter(self, state, dt):
        for n in needles:
            n.desired_pos = None
            outward = safe_norm(vector(n.pos.x, 0.25 * n.pos.y, n.pos.z), vector(random.uniform(-1, 1), 0, random.uniform(-1, 1)))
            n.ai_force += outward * 0.115 + vector(random.uniform(-0.07, 0.07), random.uniform(-0.035, 0.035), random.uniform(-0.07, 0.07))
            if random.random() < 0.002:
                n.attach_field_line(random.randrange(len(field_line_points)) if field_line_points else None)
        if random.random() < 0.055:
            p = vector(random.uniform(-1.2, 1.2), random.uniform(-0.6, 1.4), random.uniform(-1.2, 1.2))
            particles.append(FieldParticle(p, vel=safe_norm(p, vector(1, 0, 0)) * 0.35, col=palette(random.random()), lifetime=2.0))

    def behavior_orbit(self, state, dt):
        for i, n in enumerate(needles):
            if n.attached != "orbit" and random.random() < 0.012:
                n.attach_orbit(
                    radius=random.uniform(1.32, 2.38),
                    y=random.uniform(-0.9, 1.0),
                    speed=random.choice([-1, 1]) * random.uniform(0.32, 0.92),
                )
            if n.attached == "orbit" and random.random() < 0.001:
                n.detach()
            if random.random() < 0.0022:
                drop_marker(n.pos, vector(0.2, 0.55, 1.0), radius=0.020)

    def behavior_paint(self, state, dt):
        for i, n in enumerate(needles):
            if n.attached is None and field_line_points and random.random() < 0.011:
                n.attach_field_line((i * 7 + int(sim_time)) % len(field_line_points), speed=random.uniform(7, 20))
            elif n.attached == "field" and random.random() < 0.002:
                n.detach()
            if random.random() < 0.018:
                drop_marker(n.pos, field_color_from_strength(field_strength_at(n.pos)), radius=random.uniform(0.015, 0.030))
        if random.random() < 0.015:
            p = vector(random.uniform(-2.3, 2.3), random.uniform(-1.2, 1.8), random.uniform(-2.3, 2.3))
            particles.append(FieldParticle(p, vel=field_unit_at(p) * 0.25, col=field_color_from_strength(field_strength_at(p)), lifetime=2.8))

    def behavior_wrap(self, state, dt):
        count = len(needles)
        phase_speed = 0.55
        for i, n in enumerate(needles):
            n.detach(False) if n.attached else None
            theta = 2 * math.pi * i / count + sim_time * 0.19
            wrap_phase = 2.8 * theta + sim_time * phase_speed
            radial = vector(math.cos(theta), 0, math.sin(theta))
            wire_center = radial * LOOP_RADIUS
            target = wire_center + radial * (0.25 * math.cos(wrap_phase)) + vector(0, 0.25 * math.sin(wrap_phase), 0)
            n.desired_pos = target
            n.ai_force += (target - n.pos) * 0.58
            if random.random() < 0.004:
                drop_marker(target, vector(1.0, 0.45, 0.10), radius=0.018)

    def behavior_invert(self, state, dt):
        if int(self.mode_timer * 2.0) != int((self.mode_timer - dt) * 2.0):
            if random.random() < 0.35:
                self.invert_current()
                for _ in range(9):
                    p = vector(random.uniform(-1.4, 1.4), random.uniform(-0.5, 1.5), random.uniform(-1.4, 1.4))
                    particles.append(FieldParticle(p, vel=field_unit_at(p) * random.uniform(0.15, 0.45), col=vector(0.2, 0.55, 1.0), lifetime=1.5))
        for n in needles:
            n.ai_force += field_unit_at(n.pos) * 0.035
            n.lock = max(0.08, n.lock - dt * 0.10)

    def behavior_careful_sort(self, state, dt):
        # Constructive / careful behavior: sort needles by field strength into three altitude bands.
        for i, n in enumerate(needles):
            n.detach(False) if n.attached else None
            b = field_strength_at(n.pos)
            band = -0.75 if b < 0.55 else (0.05 if b < 1.05 else 0.85)
            angle = 2 * math.pi * i / len(needles) + 0.1 * math.sin(sim_time)
            radius = 1.85 + 0.18 * math.sin(i)
            target = vector(radius * math.cos(angle), band, radius * math.sin(angle))
            n.desired_pos = target
            n.ai_force += (target - n.pos) * 0.37
            if random.random() < 0.002:
                drop_marker(target, vector(0.32, 0.80, 0.45), radius=0.019)

    def behavior_chaos_spill(self, state, dt):
        for n in needles:
            n.desired_pos = None
            n.detach(False) if n.attached and random.random() < 0.03 else None
            swirl = cross(vector(0, 1, 0), safe_norm(vector(n.pos.x, 0, n.pos.z), vector(1, 0, 0)))
            n.ai_force += swirl * 0.16 + vector(random.uniform(-0.13, 0.13), random.uniform(-0.06, 0.08), random.uniform(-0.13, 0.13))
            n.lock = max(0.08, n.lock - dt * 0.08)

        if random.random() < 0.09:
            p = vector(random.uniform(-1.8, 1.8), random.uniform(-0.7, 1.7), random.uniform(-1.8, 1.8))
            for _ in range(random.randint(2, 5)):
                particles.append(FieldParticle(p, vel=vector(random.uniform(-0.45, 0.45), random.uniform(-0.16, 0.35), random.uniform(-0.45, 0.45)), col=palette(random.random()), lifetime=random.uniform(1.0, 2.6)))

ai = AIController()

# ============================================================
# Human Keyboard Control
# ============================================================

def apply_human_override(seconds=4.0):
    global human_override_timer
    human_override_timer = max(human_override_timer, seconds)

def selected_needle():
    if not needles:
        return None
    return needles[selected_index % len(needles)]

def on_keydown(evt):
    global paused, selected_index, current_strength, show_trails, show_labels

    key = evt.key

    if key == " ":
        paused = not paused
        return

    if key in ["a", "A"]:
        ai.enabled = not ai.enabled
        return

    if key in ["m", "M"]:
        ai.next_mode()
        return

    if key in ["r", "R"]:
        reset_round("human reset")
        ai.stagnation_timer = 0
        ai.completion_timer = 0
        apply_human_override(1.0)
        return

    if key in ["c", "C"]:
        for n in needles:
            n.clear_trail()
        clear_markers()
        clear_particles()
        apply_human_override(1.5)
        return

    if key in ["+", "="]:
        current_strength = clamp(current_strength + 0.15, -2.5, 2.5)
        if abs(current_strength) < 0.05:
            current_strength = 0.15
        update_current_arrows()
        apply_human_override(1.0)
        return

    if key in ["-", "_"]:
        current_strength = clamp(current_strength - 0.15, -2.5, 2.5)
        if abs(current_strength) < 0.05:
            current_strength = -0.15
        update_current_arrows()
        apply_human_override(1.0)
        return

    if key in ["i", "I"]:
        current_strength *= -1
        update_current_arrows()
        apply_human_override(1.0)
        return

    if key in ["n", "N"]:
        selected_index = (selected_index + 1) % len(needles)
        apply_human_override(2.5)
        return

    if key in ["l", "L"]:
        show_labels = not show_labels
        return

    if key in ["t", "T"]:
        show_trails = not show_trails
        return

    n = selected_needle()
    if n is None:
        return

    force = 1.8
    if key == "left":
        n.detach(False)
        n.human_force += vector(-force, 0, 0)
        apply_human_override()
    elif key == "right":
        n.detach(False)
        n.human_force += vector(force, 0, 0)
        apply_human_override()
    elif key == "up":
        n.detach(False)
        n.human_force += vector(0, 0, -force)
        apply_human_override()
    elif key == "down":
        n.detach(False)
        n.human_force += vector(0, 0, force)
        apply_human_override()
    elif key in ["pageup", "u", "U"]:
        n.detach(False)
        n.human_force += vector(0, force, 0)
        apply_human_override()
    elif key in ["pagedown", "j", "J"]:
        n.detach(False)
        n.human_force += vector(0, -force, 0)
        apply_human_override()
    elif key in ["d", "D"]:
        n.detach()
        apply_human_override()
    elif key in ["o", "O"]:
        n.attach_orbit(radius=random.uniform(1.3, 2.4), y=random.uniform(-0.9, 1.2), speed=random.choice([-1, 1]) * random.uniform(0.45, 1.0))
        apply_human_override()
    elif key in ["f", "F"]:
        n.attach_field_line(random.randrange(len(field_line_points)) if field_line_points else None)
        apply_human_override()
    elif key in ["p", "P"]:
        drop_marker(n.pos, vector(1.0, 0.12, 0.18), radius=0.045)
        apply_human_override()
    elif key in ["h", "H"]:
        apply_human_override(6.0)

scene.bind("keydown", on_keydown)

# ============================================================
# HUD
# ============================================================

def update_hud(state):
    ai_status = "ON" if ai.enabled else "OFF"
    override = f" | HUMAN OVERRIDE {human_override_timer:.1f}s" if human_override_timer > 0 else ""
    pause_text = "PAUSED | " if paused else ""
    complete = " | round complete → reset soon" if ai.round_complete else ""
    round_label.text = (
        f"{pause_text}AI {ai_status}: {ai.mode}{override}{complete}\n"
        f"round {ai.round} | I={current_strength:+.2f} | selected N{selected_index}\n"
        f"avg speed {state['avg_speed']:.3f} | align error {state['avg_align_error']:.3f} | attached {state['attached_count']}/{len(needles)}"
    )

# ============================================================
# Main Loop
# ============================================================

reset_round("initial", keep_current=True)

while True:
    rate(60)

    if not paused:
        sim_time += dt

        if human_override_timer > 0:
            human_override_timer = max(0, human_override_timer - dt)

        ai.update(dt)

        for n in needles:
            n.update(dt)

        collide_needles()

        alive = []
        for p in particles:
            if p.update(dt):
                alive.append(p)
        particles = alive

    state = ai.read_state()
    update_hud(state)

    for r in coil_rings:
        r.color = vector(1.0, 0.52, 0.12) if current_strength >= 0 else vector(0.20, 0.48, 1.0)
        r.opacity = 0.42 if abs(r.pos.y) > 0 else 1.0

    update_current_arrows()
