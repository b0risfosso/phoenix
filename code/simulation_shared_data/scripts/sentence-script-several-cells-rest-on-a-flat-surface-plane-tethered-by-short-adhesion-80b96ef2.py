from vpython import *
import random
import math

# ------------------------------------------------------------
# 3D Cell Adhesion / Detachment Simulation with Expressive AI
# Requires: pip install vpython
# Run: python this_file.py
# ------------------------------------------------------------

scene.title = "Cell Adhesion and Detachment on a Surface - VPython"
scene.width = 1200
scene.height = 760
scene.background = vector(0.965, 0.985, 1.0)
scene.forward = vector(-0.95, -0.55, -1.15)
scene.up = vector(0, 1, 0)
scene.camera.pos = vector(9, 8, 13)
scene.camera.axis = vector(-9, -6, -12)
scene.userspin = True
scene.userzoom = True

# -----------------------------
# World constants
# -----------------------------

WORLD_X = 10.5
WORLD_Z = 6.5
CELL_COUNT = 12

DT = 0.012
CELL_RADIUS = 0.42
CELL_MASS = 1.0
CELL_INERTIA = 0.4 * CELL_MASS * CELL_RADIUS * CELL_RADIUS

MAX_TETHERS_PER_CELL = 7
RECEPTORS_PER_CELL = 11

TETHER_K = 18.0
TETHER_DAMP = 1.55
TETHER_REST = 0.12
TETHER_SNAP = 0.86
TETHER_ATTACH_HEIGHT = 0.18

FLOW_DRAG_ATTACHED = 0.70
FLOW_DRAG_FREE = 1.35
SURFACE_FRICTION = 1.8
AIR_DRAG = 0.55
ROLLING_COUPLING = 4.0
CELL_COLLISION_K = 60.0
CELL_COLLISION_DAMP = 1.2

UP = vector(0, 1, 0)

# -----------------------------
# Global simulation state
# -----------------------------

cells = []
tethers = []
particles = []
footprints = []
flow_arrows = []
round_marks = []

sim_time = 0.0
paused = False
show_help = True
selected_index = 0
human_override_timer = 0.0
trail_enabled = True
wrap_enabled = True

flow_vec = vector(0.72, 0, 0.0)
base_flow_vec = vector(0.72, 0, 0.0)

# HUD positions moved away from the active adhesion field.
# These are still 3D VPython labels, but they sit high and to the right of the surface.
HUD_X = WORLD_X + 0.85
HUD_Z = -WORLD_Z + 0.45
HUD_STATUS_Y = 4.75
HUD_FLOW_Y = 4.25
HUD_HELP_Y = 3.15

# -----------------------------
# Visual scene objects
# -----------------------------

surface = box(
    pos=vector(0, -0.025, 0),
    size=vector(WORLD_X * 2.15, 0.05, WORLD_Z * 2.15),
    color=vector(0.90, 0.94, 0.91),
    opacity=0.92
)

surface_grid = []
for x in range(-10, 11, 2):
    surface_grid.append(curve(
        pos=[vector(x, 0.004, -WORLD_Z), vector(x, 0.004, WORLD_Z)],
        radius=0.006,
        color=vector(0.72, 0.80, 0.75)
    ))
for z in range(-6, 7, 2):
    surface_grid.append(curve(
        pos=[vector(-WORLD_X, 0.005, z), vector(WORLD_X, 0.005, z)],
        radius=0.006,
        color=vector(0.72, 0.80, 0.75)
    ))

flow_label = label(
    pos=vector(HUD_X, HUD_FLOW_Y, HUD_Z),
    text="",
    box=False,
    color=vector(0.12, 0.18, 0.22),
    height=13,
    opacity=0,
    align="left"
)

status_label = label(
    pos=vector(HUD_X, HUD_STATUS_Y, HUD_Z),
    text="",
    box=False,
    color=vector(0.10, 0.14, 0.16),
    height=13,
    opacity=0,
    align="left"
)

help_label = label(
    pos=vector(HUD_X, HUD_HELP_Y, HUD_Z),
    text="",
    box=True,
    border=12,
    color=vector(0.12, 0.16, 0.20),
    background=vector(1.0, 1.0, 0.94),
    opacity=0.72,
    height=12,
    align="left"
)

selection_ring = ring(
    pos=vector(0, 0.035, 0),
    axis=UP,
    radius=CELL_RADIUS * 1.35,
    thickness=0.025,
    color=vector(0.18, 0.35, 1.0),
    opacity=0.85
)

# -----------------------------
# Utility
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-9:
        return fallback
    return v / m

def rand_vec2(scale=1.0):
    return vector(random.uniform(-scale, scale), 0, random.uniform(-scale, scale))

def pastel_color():
    return vector(
        random.uniform(0.35, 0.85),
        random.uniform(0.55, 0.95),
        random.uniform(0.65, 1.0)
    )

def heat_color(t):
    t = clamp(t, 0, 1)
    return vector(0.25 + 0.75 * t, 0.95 - 0.60 * t, 0.28 - 0.18 * t)

def horizontal(v):
    return vector(v.x, 0, v.z)

def hide_obj(obj):
    try:
        obj.visible = False
    except Exception:
        pass

# -----------------------------
# Flow arrows
# -----------------------------

def create_flow_arrows():
    global flow_arrows
    for a in flow_arrows:
        hide_obj(a)
    flow_arrows = []

    for x in [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]:
        for z in [-4.5, -1.5, 1.5, 4.5]:
            arr = arrow(
                pos=vector(x, 0.13, z),
                axis=vector(0.65, 0, 0),
                shaftwidth=0.035,
                headwidth=0.13,
                headlength=0.20,
                color=vector(0.35, 0.66, 0.95),
                opacity=0.42
            )
            flow_arrows.append(arr)

def update_flow_arrows():
    f = horizontal(flow_vec)
    speed = mag(f)
    if speed < 0.02:
        axis = vector(0.05, 0, 0)
    else:
        axis = safe_norm(f) * clamp(0.38 + speed * 0.62, 0.05, 1.65)

    for i, a in enumerate(flow_arrows):
        a.axis = axis
        a.opacity = clamp(0.18 + speed * 0.28, 0.18, 0.68)
        a.color = vector(0.28, 0.55 + 0.18 * math.sin(sim_time + i), 0.95)

create_flow_arrows()

# -----------------------------
# Particles and marks
# -----------------------------

class SnapParticle:
    def __init__(self, pos, color_hint=vector(1.0, 0.40, 0.22)):
        self.life = random.uniform(0.42, 0.95)
        self.max_life = self.life
        self.vel = vector(
            random.uniform(-0.55, 0.55),
            random.uniform(0.10, 0.82),
            random.uniform(-0.55, 0.55)
        )
        self.obj = sphere(
            pos=pos,
            radius=random.uniform(0.025, 0.055),
            color=color_hint,
            opacity=0.70,
            shininess=0.15
        )

    def update(self, dt):
        self.life -= dt
        self.vel += vector(0, -0.65, 0) * dt
        self.vel += horizontal(flow_vec) * 0.18 * dt
        self.obj.pos += self.vel * dt
        self.obj.opacity = max(0, 0.72 * self.life / self.max_life)
        self.obj.radius *= 0.992
        if self.life <= 0:
            hide_obj(self.obj)
            return False
        return True

def burst(pos, n=10, color_hint=vector(1.0, 0.42, 0.22)):
    for _ in range(n):
        particles.append(SnapParticle(pos, color_hint))

def make_footprint(pos, col=vector(0.98, 0.72, 0.18), rad=0.055, opacity=0.62):
    fp = cylinder(
        pos=vector(pos.x, 0.006, pos.z),
        axis=vector(0, 0.007, 0),
        radius=rad,
        color=col,
        opacity=opacity
    )
    footprints.append(fp)
    if len(footprints) > 420:
        old = footprints.pop(0)
        hide_obj(old)
    return fp

def make_round_mark(text, pos, col=vector(0.25, 0.35, 0.6)):
    mk = label(
        pos=pos,
        text=text,
        box=False,
        color=col,
        height=11,
        opacity=0
    )
    round_marks.append([mk, 3.5])
    return mk

# -----------------------------
# Cell and tether classes
# -----------------------------

class Cell:
    def __init__(self, idx, pos):
        self.idx = idx
        self.radius = CELL_RADIUS * random.uniform(0.92, 1.10)
        self.mass = CELL_MASS * (self.radius / CELL_RADIUS) ** 3
        self.inertia = 0.4 * self.mass * self.radius * self.radius

        self.pos = pos
        self.vel = vector(random.uniform(-0.03, 0.03), 0, random.uniform(-0.03, 0.03))
        self.omega = vector(0, 0, 0)
        self.force = vector(0, 0, 0)
        self.torque = vector(0, 0, 0)

        self.base_color = pastel_color()
        self.mark_color = self.base_color
        self.detached_time = 0.0
        self.wraps = 0
        self.ai_tag = ""

        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.base_color,
            opacity=0.82,
            shininess=0.55
        )

        self.marker_dir = safe_norm(vector(random.uniform(-1, 1), 0.35, random.uniform(-1, 1)))
        self.marker = sphere(
            pos=self.pos + self.marker_dir * self.radius * 1.025,
            radius=self.radius * 0.135,
            color=vector(1.0, 1.0, 1.0),
            opacity=0.92,
            shininess=0.2
        )

        self.label = label(
            pos=self.pos + vector(0, self.radius * 1.7, 0),
            text=str(idx),
            box=False,
            height=10,
            color=vector(0.08, 0.12, 0.16),
            opacity=0
        )

        self.trail = curve(radius=0.018, color=self.base_color, opacity=0.44)
        self.trail_counter = 0

        self.receptor_dirs = []
        self._make_receptors()

    def _make_receptors(self):
        self.receptor_dirs.clear()

        # Lower hemisphere ring receptors
        for i in range(RECEPTORS_PER_CELL - 2):
            a = 2 * math.pi * i / (RECEPTORS_PER_CELL - 2)
            y = random.uniform(-0.98, -0.62)
            r = math.sqrt(max(0.0, 1.0 - y * y))
            self.receptor_dirs.append(safe_norm(vector(math.cos(a) * r, y, math.sin(a) * r)))

        # A near-bottom receptor and one tilted receptor for rolling variety
        self.receptor_dirs.append(vector(0, -1, 0))
        self.receptor_dirs.append(safe_norm(vector(0.30, -0.88, -0.18)))

    def receptor_world(self, i):
        return self.pos + self.receptor_dirs[i % len(self.receptor_dirs)] * self.radius

    def tether_count(self):
        return sum(1 for t in tethers if t.active and t.cell is self)

    def used_receptor_indices(self):
        return set(t.receptor_index for t in tethers if t.active and t.cell is self)

    def reset_forces(self):
        self.force = vector(0, 0, 0)
        self.torque = vector(0, 0, 0)

    def apply_force(self, f, at=None):
        self.force += f
        if at is not None:
            self.torque += cross(at - self.pos, f)

    def apply_impulse(self, impulse, at=None):
        self.vel += impulse / self.mass
        if at is not None:
            self.omega += cross(at - self.pos, impulse) / self.inertia

    def update_orientation(self, dt):
        if mag(self.omega) > 1e-8:
            for i, d in enumerate(self.receptor_dirs):
                nd = d + cross(self.omega, d) * dt
                self.receptor_dirs[i] = safe_norm(nd, d)

            md = self.marker_dir + cross(self.omega, self.marker_dir) * dt
            self.marker_dir = safe_norm(md, self.marker_dir)

    def integrate(self, dt):
        # Gravity-like settling plus buoyant lift when detached and under flow
        tether_n = self.tether_count()
        flow_speed = mag(horizontal(flow_vec))

        if tether_n == 0:
            self.detached_time += dt
            lift = clamp(flow_speed * 0.24 - 0.05, 0.0, 0.45)
            self.apply_force(vector(0, lift, 0) * self.mass)
            self.apply_force(horizontal(flow_vec - self.vel) * FLOW_DRAG_FREE)
        else:
            self.detached_time = 0.0
            self.apply_force(horizontal(flow_vec - self.vel) * FLOW_DRAG_ATTACHED)

        # Soft downward tendency keeps floating cells in the observation volume
        if self.pos.y > self.radius * 1.25:
            self.apply_force(vector(0, -0.13 * self.mass, 0))

        # Drag
        self.apply_force(-self.vel * AIR_DRAG)
        self.torque += -self.omega * 0.08

        # Integrate
        self.vel += (self.force / self.mass) * dt
        self.omega += (self.torque / self.inertia) * dt

        # Plane collision/contact
        if self.pos.y <= self.radius + 0.002:
            self.pos.y = self.radius + 0.002
            if self.vel.y < 0:
                self.vel.y *= -0.18

            hvel = horizontal(self.vel)
            friction_strength = SURFACE_FRICTION * (1.0 + 0.22 * tether_n)
            self.vel -= hvel * clamp(friction_strength * dt, 0, 0.45)

            # Rolling visual/physical coupling
            if mag(hvel) > 0.002:
                desired_omega = cross(UP, hvel) / max(self.radius, 1e-6)
                self.omega += (desired_omega - self.omega) * clamp(ROLLING_COUPLING * dt, 0, 0.25)

        # Ceiling softness
        if self.pos.y > 5.8:
            self.vel.y -= 1.2 * dt

        # Horizontal wrapping
        if wrap_enabled:
            wrapped = False
            old_pos = vector(self.pos)
            if self.pos.x > WORLD_X:
                self.pos.x = -WORLD_X
                wrapped = True
            elif self.pos.x < -WORLD_X:
                self.pos.x = WORLD_X
                wrapped = True

            if self.pos.z > WORLD_Z:
                self.pos.z = -WORLD_Z
                wrapped = True
            elif self.pos.z < -WORLD_Z:
                self.pos.z = WORLD_Z
                wrapped = True

            if wrapped:
                self.wraps += 1
                self.trail = curve(radius=0.018, color=self.mark_color, opacity=0.44)
                ring(
                    pos=vector(old_pos.x, 0.04, old_pos.z),
                    axis=UP,
                    radius=self.radius * 1.3,
                    thickness=0.018,
                    color=vector(0.48, 0.55, 1.0),
                    opacity=0.35
                )

        self.pos += self.vel * dt

        # Keep from going below plane after integration
        if self.pos.y < self.radius:
            self.pos.y = self.radius

        self.update_orientation(dt)

        self.obj.pos = self.pos
        self.marker.pos = self.pos + self.marker_dir * self.radius * 1.025
        self.label.pos = self.pos + vector(0, self.radius * 1.7, 0)

        # Color shows adhesion status and AI markings
        if tether_n == 0:
            target = vector(1.0, 0.74, 0.52)
        else:
            target = self.mark_color
        self.obj.color = self.obj.color * 0.94 + target * 0.06

        if trail_enabled:
            self.trail_counter += 1
            if self.trail_counter % 5 == 0:
                self.trail.append(pos=self.pos, retain=260)

    def hide(self):
        hide_obj(self.obj)
        hide_obj(self.marker)
        hide_obj(self.label)
        hide_obj(self.trail)


class Tether:
    def __init__(self, cell, receptor_index, anchor):
        self.cell = cell
        self.receptor_index = receptor_index
        self.anchor = vector(anchor.x, 0.0, anchor.z)
        self.rest = TETHER_REST * random.uniform(0.80, 1.18)
        self.k = TETHER_K * random.uniform(0.80, 1.25)
        self.damp = TETHER_DAMP
        self.age = 0.0
        self.active = True

        self.anchor_marker = make_footprint(
            self.anchor,
            col=vector(0.98, 0.78, 0.22),
            rad=random.uniform(0.045, 0.075),
            opacity=0.68
        )

        rec = self.cell.receptor_world(self.receptor_index)
        self.line = curve(
            pos=[self.anchor + vector(0, 0.012, 0), rec],
            radius=0.018,
            color=vector(0.18, 0.82, 0.32),
            opacity=0.78
        )

    def current_length(self):
        rec = self.cell.receptor_world(self.receptor_index)
        return mag(rec - self.anchor)

    def apply(self, dt):
        if not self.active:
            return

        self.age += dt

        rec = self.cell.receptor_world(self.receptor_index)
        r = rec - self.anchor
        L = mag(r)

        if L < 1e-6:
            return

        n = r / L
        stretch = max(0.0, L - self.rest)
        vpoint = self.cell.vel + cross(self.cell.omega, rec - self.cell.pos)
        f = -self.k * stretch * n - self.damp * dot(vpoint, n) * n
        self.cell.apply_force(f, rec)

        stretch_ratio = clamp((L - self.rest) / max(TETHER_SNAP - self.rest, 1e-6), 0, 1)
        self.line.modify(0, pos=self.anchor + vector(0, 0.012, 0))
        self.line.modify(1, pos=rec)
        self.line.color = heat_color(stretch_ratio)
        self.line.radius = 0.012 + 0.012 * (1.0 - stretch_ratio)
        self.anchor_marker.color = self.line.color

        # Mechanical snap and probabilistic unbinding
        flow_bonus = mag(horizontal(flow_vec)) * 0.012
        snap_probability = max(0.0, stretch_ratio - 0.72) * 0.55 + flow_bonus

        if L > TETHER_SNAP or random.random() < snap_probability * dt:
            self.break_tether(spill=True)

    def break_tether(self, spill=True):
        if not self.active:
            return
        self.active = False

        rec = self.cell.receptor_world(self.receptor_index)
        mid = (rec + self.anchor) * 0.5

        hide_obj(self.line)
        self.anchor_marker.color = vector(1.0, 0.34, 0.22)
        self.anchor_marker.opacity = 0.28
        self.anchor_marker.radius *= 0.72

        if spill:
            burst(mid, n=random.randint(5, 13), color_hint=vector(1.0, 0.44, 0.22))

    def hide(self):
        hide_obj(self.line)
        hide_obj(self.anchor_marker)

# -----------------------------
# Adhesion, collisions, reset
# -----------------------------

def attach_one_tether(cell, forced=False):
    if cell.tether_count() >= MAX_TETHERS_PER_CELL:
        return None

    used = cell.used_receptor_indices()
    candidates = []

    for i in range(len(cell.receptor_dirs)):
        if i in used:
            continue
        rec = cell.receptor_world(i)
        if rec.y <= TETHER_ATTACH_HEIGHT or forced:
            if abs(rec.x) < WORLD_X and abs(rec.z) < WORLD_Z:
                candidates.append((i, rec))

    if not candidates:
        return None

    i, rec = random.choice(candidates)
    anchor = vector(rec.x, 0, rec.z) + rand_vec2(0.035)
    t = Tether(cell, i, anchor)
    tethers.append(t)
    return t

def detach_cell(cell, spill=True):
    broke = 0
    for t in list(tethers):
        if t.active and t.cell is cell:
            t.break_tether(spill=spill)
            broke += 1
    if broke > 0:
        cell.apply_impulse(vector(random.uniform(0.0, 0.35), random.uniform(0.08, 0.28), random.uniform(-0.15, 0.15)))
    return broke

def natural_attachment_update(dt):
    for c in cells:
        if c.pos.y > c.radius + 0.12:
            continue

        missing = MAX_TETHERS_PER_CELL - c.tether_count()
        if missing <= 0:
            continue

        # More likely to bind when sliding slowly and close to surface
        speed = mag(horizontal(c.vel))
        p = clamp(0.95 - speed * 0.30, 0.04, 0.95) * 0.55

        for _ in range(missing):
            if random.random() < p * dt:
                attach_one_tether(c)

def collide_cells(dt):
    n = len(cells)
    for i in range(n):
        a = cells[i]
        for j in range(i + 1, n):
            b = cells[j]
            d = b.pos - a.pos
            dist = mag(d)
            min_dist = a.radius + b.radius

            if dist < min_dist and dist > 1e-8:
                normal = d / dist
                overlap = min_dist - dist

                # Separate
                a.pos -= normal * overlap * 0.52
                b.pos += normal * overlap * 0.52

                relv = b.vel - a.vel
                vn = dot(relv, normal)

                force_mag = CELL_COLLISION_K * overlap - CELL_COLLISION_DAMP * vn
                if force_mag > 0:
                    impulse = normal * force_mag * dt
                    a.apply_impulse(-impulse)
                    b.apply_impulse(impulse)

                # Small lateral mixing impulse
                tangent = safe_norm(cross(normal, UP), vector(1, 0, 0))
                mix = tangent * random.uniform(-0.006, 0.006)
                a.vel -= mix
                b.vel += mix

def create_cells():
    global cells

    cells = []
    attempts = 0

    while len(cells) < CELL_COUNT and attempts < 2000:
        attempts += 1
        p = vector(
            random.uniform(-WORLD_X * 0.62, WORLD_X * 0.32),
            CELL_RADIUS + 0.005,
            random.uniform(-WORLD_Z * 0.75, WORLD_Z * 0.75)
        )
        ok = True
        for c in cells:
            if mag(horizontal(p - c.pos)) < CELL_RADIUS * 2.4:
                ok = False
                break
        if ok:
            cells.append(Cell(len(cells), p))

    for c in cells:
        for _ in range(random.randint(3, MAX_TETHERS_PER_CELL)):
            attach_one_tether(c, forced=True)

def reset_simulation(randomize=True, announce=True):
    global cells, tethers, particles, footprints, sim_time, selected_index
    global flow_vec, base_flow_vec, round_marks

    for c in cells:
        c.hide()
    for t in tethers:
        t.hide()
    for p in particles:
        hide_obj(p.obj)
    for fp in footprints:
        hide_obj(fp)
    for mk, _life in round_marks:
        hide_obj(mk)

    cells = []
    tethers = []
    particles = []
    footprints = []
    round_marks = []
    selected_index = 0

    if randomize:
        base_flow_vec = vector(random.uniform(0.45, 0.95), 0, random.uniform(-0.10, 0.10))
        flow_vec = vector(base_flow_vec)
    else:
        base_flow_vec = vector(0.72, 0, 0)
        flow_vec = vector(base_flow_vec)

    create_cells()

    if announce:
        make_round_mark("new adhesion round", vector(0, 2.0, 0), vector(0.20, 0.38, 0.65))

# -----------------------------
# Expressive AI controller
# -----------------------------

class AIController:
    MODES = [
        "CAREFUL_GARDENER",
        "SHEAR_PULSE",
        "DETACHER",
        "ORBIT_SWIRL",
        "ORGANIZE_LINE",
        "RESCUE_DIP",
        "PAINT_MARK",
        "CHAOS_MIX",
        "CONSTRUCTIVE_WRAP",
        "RESET_RITUAL",
    ]

    def __init__(self):
        self.enabled = True
        self.mode = "CAREFUL_GARDENER"
        self.timer = 0.0
        self.mode_duration = 8.0
        self.round = 1
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_metric = None
        self.metric_timer = 0.0
        self.personality = random.choice(["careful", "curious", "playful", "chaotic", "ritual", "artistic"])
        self.auto_loop = True
        self.override_sensitive = True

    def set_mode(self, mode):
        if mode not in self.MODES:
            return
        self.mode = mode
        self.timer = 0.0
        self.mode_duration = random.uniform(6.0, 13.5)
        make_round_mark("AI: " + mode.lower().replace("_", " "), vector(0, 2.7, 0), vector(0.25, 0.32, 0.55))

    def next_mode(self):
        options = [m for m in self.MODES if m != self.mode and m != "RESET_RITUAL"]

        # Personality nudges
        if self.personality == "careful":
            weighted = ["CAREFUL_GARDENER", "RESCUE_DIP", "ORGANIZE_LINE", "CONSTRUCTIVE_WRAP", "PAINT_MARK"]
        elif self.personality == "chaotic":
            weighted = ["CHAOS_MIX", "DETACHER", "SHEAR_PULSE", "ORBIT_SWIRL", "PAINT_MARK"]
        elif self.personality == "artistic":
            weighted = ["PAINT_MARK", "ORBIT_SWIRL", "ORGANIZE_LINE", "CONSTRUCTIVE_WRAP", "SHEAR_PULSE"]
        elif self.personality == "ritual":
            weighted = ["ORGANIZE_LINE", "SHEAR_PULSE", "RESCUE_DIP", "RESET_RITUAL", "CONSTRUCTIVE_WRAP"]
        else:
            weighted = options

        candidates = [m for m in weighted if m != self.mode]
        self.set_mode(random.choice(candidates if candidates else options))

    def read_state(self):
        active_tethers = [t for t in tethers if t.active]
        tether_count = len(active_tethers)
        detached = [c for c in cells if c.tether_count() == 0]
        attached = [c for c in cells if c.tether_count() > 0]
        avg_speed = sum(mag(c.vel) for c in cells) / max(1, len(cells))
        avg_y = sum(c.pos.y for c in cells) / max(1, len(cells))
        avg_x = sum(c.pos.x for c in cells) / max(1, len(cells))
        spread = 0.0
        if cells:
            center = vector(
                sum(c.pos.x for c in cells) / len(cells),
                sum(c.pos.y for c in cells) / len(cells),
                sum(c.pos.z for c in cells) / len(cells)
            )
            spread = sum(mag(c.pos - center) for c in cells) / len(cells)
        else:
            center = vector(0, 0, 0)

        stretched = 0
        for t in active_tethers:
            if t.current_length() > TETHER_SNAP * 0.68:
                stretched += 1

        return {
            "tether_count": tether_count,
            "detached_count": len(detached),
            "attached_count": len(attached),
            "avg_speed": avg_speed,
            "avg_y": avg_y,
            "avg_x": avg_x,
            "spread": spread,
            "center": center,
            "stretched_count": stretched,
            "flow_speed": mag(horizontal(flow_vec)),
        }

    def detect_stagnation_and_completion(self, dt, state):
        self.metric_timer += dt

        halted = state["avg_speed"] < 0.035 and abs(state["flow_speed"]) < 0.18
        stable_attached = state["avg_speed"] < 0.045 and state["stretched_count"] == 0 and state["tether_count"] > CELL_COUNT * 3
        empty_or_complete = state["tether_count"] == 0 and state["detached_count"] >= max(1, int(CELL_COUNT * 0.80))
        far_drifted = abs(state["avg_x"]) > WORLD_X * 0.65 and state["detached_count"] > CELL_COUNT * 0.50

        if halted or stable_attached:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 1.4)

        if empty_or_complete or far_drifted:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 1.8)

        if self.metric_timer > 1.0:
            metric = (state["tether_count"], round(state["avg_speed"], 2), round(state["spread"], 1))
            if self.last_metric == metric:
                self.stagnation_timer += 1.0
            self.last_metric = metric
            self.metric_timer = 0.0

        if self.auto_loop and (self.stagnation_timer > 9.0 or self.completion_timer > 4.8):
            if self.mode != "RESET_RITUAL":
                self.set_mode("RESET_RITUAL")

    def choose_behavior(self, state):
        if self.mode == "RESET_RITUAL":
            return

        if self.timer > self.mode_duration:
            self.next_mode()
            return

        if state["detached_count"] > CELL_COUNT * 0.72 and self.mode in ["DETACHER", "CHAOS_MIX", "SHEAR_PULSE"]:
            self.set_mode(random.choice(["RESCUE_DIP", "ORBIT_SWIRL", "PAINT_MARK"]))
        elif state["tether_count"] > CELL_COUNT * MAX_TETHERS_PER_CELL * 0.78 and state["avg_speed"] < 0.07:
            self.set_mode(random.choice(["SHEAR_PULSE", "DETACHER", "PAINT_MARK"]))
        elif state["stretched_count"] > 7 and self.mode not in ["RESCUE_DIP", "DETACHER"]:
            self.set_mode(random.choice(["CAREFUL_GARDENER", "DETACHER", "SHEAR_PULSE"]))

    def update(self, dt):
        global flow_vec, base_flow_vec, trail_enabled

        if not self.enabled or paused:
            return

        state = self.read_state()
        self.detect_stagnation_and_completion(dt, state)

        self.timer += dt
        self.choose_behavior(state)

        # Human override allows keyboard activity to temporarily dominate.
        if human_override_timer > 0 and self.override_sensitive and self.mode != "RESET_RITUAL":
            flow_vec = flow_vec * 0.985 + base_flow_vec * 0.015
            return

        mode = self.mode

        if mode == "CAREFUL_GARDENER":
            target = vector(0.28, 0, 0.04 * math.sin(sim_time * 0.7))
            flow_vec = flow_vec * 0.96 + target * 0.04

            for c in cells:
                if c.tether_count() < 3 and c.pos.y < c.radius + 0.12 and random.random() < 0.42 * dt:
                    attach_one_tether(c, forced=True)
                if c.pos.y > c.radius * 1.7:
                    c.apply_impulse(vector(0, -0.030, 0))
                # Careful organizing nudge toward central band
                c.apply_impulse(vector(-0.003 * c.pos.x, 0, -0.002 * c.pos.z))

        elif mode == "SHEAR_PULSE":
            pulse = 0.85 + 0.85 * max(0, math.sin(self.timer * 1.35))
            wiggle = 0.22 * math.sin(self.timer * 2.2)
            flow_vec = vector(pulse, 0, wiggle)

            for c in cells:
                if random.random() < 0.10 * dt:
                    c.apply_impulse(vector(0.06, 0.0, random.uniform(-0.03, 0.03)))
                if c.tether_count() > 0 and random.random() < 0.05 * dt:
                    active = [t for t in tethers if t.active and t.cell is c]
                    if active:
                        random.choice(active).break_tether(spill=True)

        elif mode == "DETACHER":
            flow_vec = flow_vec * 0.94 + vector(1.45, 0, 0.12 * math.sin(sim_time * 1.7)) * 0.06

            victims = sorted(cells, key=lambda c: c.tether_count(), reverse=True)
            for c in victims[:4]:
                active = [t for t in tethers if t.active and t.cell is c]
                if active and random.random() < 0.22 * dt:
                    random.choice(active).break_tether(spill=True)
                if c.tether_count() <= 1 and random.random() < 0.12 * dt:
                    c.apply_impulse(vector(0.12, 0.18, random.uniform(-0.08, 0.08)))

        elif mode == "ORBIT_SWIRL":
            center = state["center"]
            center.y = 0
            flow_vec = vector(0.40 * math.cos(self.timer * 0.9), 0, 0.40 * math.sin(self.timer * 0.9))

            for c in cells:
                r = horizontal(c.pos - center)
                tangent = safe_norm(cross(UP, r), vector(1, 0, 0))
                inward = -safe_norm(r, vector(0, 0, 1)) * 0.008
                c.apply_impulse(tangent * 0.020 + inward)
                c.mark_color = c.mark_color * 0.96 + vector(0.55, 0.70, 1.0) * 0.04

        elif mode == "ORGANIZE_LINE":
            flow_vec = flow_vec * 0.97 + vector(0.18, 0, 0) * 0.03

            ordered = sorted(cells, key=lambda c: c.idx)
            if ordered:
                spacing = min(1.32, WORLD_X * 1.5 / max(1, len(ordered)))
                start = -spacing * (len(ordered) - 1) * 0.5
                for i, c in enumerate(ordered):
                    target = vector(start + i * spacing, c.radius + 0.002, 0.0)
                    delta = target - c.pos
                    c.apply_impulse(horizontal(delta) * 0.010)
                    if mag(horizontal(delta)) < 0.45 and c.tether_count() < 4 and random.random() < 0.35 * dt:
                        attach_one_tether(c, forced=True)
                    c.mark_color = c.mark_color * 0.97 + vector(0.55, 0.88, 0.66) * 0.03

        elif mode == "RESCUE_DIP":
            flow_vec = flow_vec * 0.96 + vector(0.08, 0, 0.0) * 0.04

            for c in cells:
                if c.tether_count() == 0:
                    c.apply_impulse(vector(-0.006 * c.pos.x, -0.045, -0.006 * c.pos.z))
                    if c.pos.y < c.radius + 0.18 and random.random() < 1.15 * dt:
                        attach_one_tether(c, forced=True)
                elif c.tether_count() < 5 and random.random() < 0.33 * dt:
                    attach_one_tether(c, forced=True)
                c.mark_color = c.mark_color * 0.96 + vector(0.70, 0.92, 0.90) * 0.04

        elif mode == "PAINT_MARK":
            trail_enabled = True
            angle = self.timer * 1.2
            flow_vec = vector(0.50 + 0.35 * math.cos(angle), 0, 0.35 * math.sin(angle * 0.7))

            for i, c in enumerate(cells):
                phase = self.timer * 1.5 + i * 0.8
                col = vector(
                    0.55 + 0.35 * math.sin(phase),
                    0.60 + 0.25 * math.sin(phase + 2.1),
                    0.75 + 0.22 * math.sin(phase + 4.2)
                )
                c.mark_color = c.mark_color * 0.90 + col * 0.10
                if random.random() < 0.10 * dt:
                    make_footprint(c.pos, col=col, rad=0.040, opacity=0.35)
                c.apply_impulse(vector(0.006 * math.sin(phase), 0, 0.006 * math.cos(phase)))

        elif mode == "CHAOS_MIX":
            jitter = vector(random.uniform(-0.35, 1.75), 0, random.uniform(-0.85, 0.85))
            flow_vec = flow_vec * 0.90 + jitter * 0.10

            for c in cells:
                if random.random() < 0.35 * dt:
                    c.apply_impulse(vector(random.uniform(-0.18, 0.30), random.uniform(0.0, 0.16), random.uniform(-0.16, 0.16)))
                if random.random() < 0.13 * dt and c.tether_count() > 0:
                    active = [t for t in tethers if t.active and t.cell is c]
                    if active:
                        random.choice(active).break_tether(spill=True)
                if random.random() < 0.09 * dt and c.pos.y < c.radius + 0.12:
                    attach_one_tether(c, forced=True)

        elif mode == "CONSTRUCTIVE_WRAP":
            flow_vec = flow_vec * 0.95 + vector(0.62, 0, 0.20 * math.sin(self.timer)) * 0.05

            radius = 2.25 + 0.45 * math.sin(self.timer * 0.8)
            for i, c in enumerate(cells):
                a = 2 * math.pi * i / max(1, len(cells)) + self.timer * 0.15
                target = vector(radius * math.cos(a), c.radius + 0.002, radius * math.sin(a))
                c.apply_impulse(horizontal(target - c.pos) * 0.008)
                if c.tether_count() < 4 and mag(horizontal(target - c.pos)) < 0.75 and random.random() < 0.45 * dt:
                    attach_one_tether(c, forced=True)
                c.mark_color = c.mark_color * 0.96 + vector(0.92, 0.82, 0.45) * 0.04

        elif mode == "RESET_RITUAL":
            flow_vec *= 0.955

            for i, c in enumerate(cells):
                a = self.timer * 2.2 + i * 0.65
                c.apply_impulse(vector(0.010 * math.cos(a), -0.012, 0.010 * math.sin(a)))
                c.mark_color = c.mark_color * 0.95 + vector(1.0, 0.93, 0.62) * 0.05

            if int(self.timer * 6) % 6 == 0 and random.random() < 0.14:
                make_round_mark("reset ritual", vector(random.uniform(-2, 2), 1.4 + random.uniform(0, 1), random.uniform(-1, 1)), vector(0.6, 0.45, 0.20))

            if self.timer > 3.2:
                self.round += 1
                self.stagnation_timer = 0
                self.completion_timer = 0
                self.personality = random.choice(["careful", "curious", "playful", "chaotic", "ritual", "artistic"])
                reset_simulation(randomize=True, announce=True)
                self.set_mode(random.choice(["CAREFUL_GARDENER", "SHEAR_PULSE", "ORBIT_SWIRL", "PAINT_MARK", "ORGANIZE_LINE"]))

ai = AIController()

# -----------------------------
# Human keyboard controls
# -----------------------------

def selected_cell():
    if not cells:
        return None
    return cells[selected_index % len(cells)]

def clear_trails():
    for c in cells:
        hide_obj(c.trail)
        c.trail = curve(radius=0.018, color=c.mark_color, opacity=0.44)

def set_human_override(seconds=2.0):
    global human_override_timer
    human_override_timer = max(human_override_timer, seconds)

def on_keydown(evt):
    global paused, selected_index, flow_vec, base_flow_vec, show_help
    global trail_enabled, wrap_enabled

    k = evt.key.lower()

    if k in [" ", "p"]:
        paused = not paused

    elif k == "a":
        ai.enabled = not ai.enabled

    elif k == "r":
        reset_simulation(randomize=True, announce=True)
        ai.stagnation_timer = 0
        ai.completion_timer = 0
        set_human_override(1.0)

    elif k == "n":
        selected_index = (selected_index + 1) % max(1, len(cells))
        set_human_override(1.0)

    elif k == "b":
        selected_index = (selected_index - 1) % max(1, len(cells))
        set_human_override(1.0)

    elif k == "d":
        c = selected_cell()
        if c:
            detach_cell(c, spill=True)
        set_human_override(3.0)

    elif k == "t":
        c = selected_cell()
        if c:
            for _ in range(2):
                attach_one_tether(c, forced=True)
        set_human_override(2.0)

    elif k == "x":
        c = selected_cell()
        if c:
            c.apply_impulse(vector(random.uniform(0.25, 0.75), random.uniform(0.08, 0.35), random.uniform(-0.35, 0.35)))
            burst(c.pos, n=8, color_hint=vector(0.45, 0.62, 1.0))
        set_human_override(2.5)

    elif k == "f":
        flow_vec += vector(0.16, 0, 0)
        base_flow_vec = vector(flow_vec)
        set_human_override(2.0)

    elif k == "g":
        flow_vec -= vector(0.16, 0, 0)
        base_flow_vec = vector(flow_vec)
        set_human_override(2.0)

    elif k == "q":
        flow_vec += vector(0, 0, -0.16)
        base_flow_vec = vector(flow_vec)
        set_human_override(2.0)

    elif k == "e":
        flow_vec += vector(0, 0, 0.16)
        base_flow_vec = vector(flow_vec)
        set_human_override(2.0)

    elif k == "c":
        clear_trails()
        set_human_override(1.0)

    elif k == "v":
        trail_enabled = not trail_enabled

    elif k == "w":
        wrap_enabled = not wrap_enabled

    elif k == "h":
        show_help = not show_help
        help_label.visible = show_help

    elif k == "o":
        ai.override_sensitive = not ai.override_sensitive

    elif k == "m":
        ai.next_mode()

    elif k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
        mapping = {
            "1": "CAREFUL_GARDENER",
            "2": "SHEAR_PULSE",
            "3": "DETACHER",
            "4": "ORBIT_SWIRL",
            "5": "ORGANIZE_LINE",
            "6": "RESCUE_DIP",
            "7": "PAINT_MARK",
            "8": "CHAOS_MIX",
            "9": "CONSTRUCTIVE_WRAP",
            "0": "RESET_RITUAL",
        }
        ai.set_mode(mapping[k])
        set_human_override(0.6)

    elif k == "left":
        c = selected_cell()
        if c:
            c.apply_impulse(vector(-0.18, 0, 0))
        set_human_override(1.0)

    elif k == "right":
        c = selected_cell()
        if c:
            c.apply_impulse(vector(0.18, 0, 0))
        set_human_override(1.0)

    elif k == "up":
        c = selected_cell()
        if c:
            c.apply_impulse(vector(0, 0.04, -0.18))
        set_human_override(1.0)

    elif k == "down":
        c = selected_cell()
        if c:
            c.apply_impulse(vector(0, 0.04, 0.18))
        set_human_override(1.0)

scene.bind("keydown", on_keydown)

# -----------------------------
# Main update helpers
# -----------------------------

def update_tethers(dt):
    for t in list(tethers):
        if t.active:
            t.apply(dt)

def remove_old_inactive_tethers():
    # Keep inactive tethers' red footprints visible, but trim dead tether objects.
    if len(tethers) < 450:
        return

    survivors = []
    removed = 0
    for t in tethers:
        if t.active:
            survivors.append(t)
        elif removed < 80:
            t.hide()
            removed += 1
        else:
            survivors.append(t)

    tethers[:] = survivors

def update_particles(dt):
    global particles
    particles = [p for p in particles if p.update(dt)]

def update_round_marks(dt):
    global round_marks
    survivors = []
    for mk, life in round_marks:
        life -= dt
        mk.pos.y += 0.10 * dt
        if life < 0.8:
            mk.color = mk.color * 0.98 + vector(1, 1, 1) * 0.02
        if life <= 0:
            hide_obj(mk)
        else:
            survivors.append([mk, life])
    round_marks = survivors

def update_selection_visual():
    c = selected_cell()
    if c:
        selection_ring.visible = True
        selection_ring.pos = vector(c.pos.x, 0.045, c.pos.z)
        selection_ring.radius = c.radius * (1.42 + 0.05 * math.sin(sim_time * 5))
        selection_ring.color = vector(0.18, 0.32, 1.0) if human_override_timer <= 0 else vector(1.0, 0.55, 0.20)

        for cell in cells:
            cell.label.visible = False
        c.label.visible = True
        c.label.text = "cell " + str(c.idx)
    else:
        selection_ring.visible = False

def update_status_labels():
    active_tether_count = sum(1 for t in tethers if t.active)
    detached_count = sum(1 for c in cells if c.tether_count() == 0)
    avg_speed = sum(mag(c.vel) for c in cells) / max(1, len(cells))

    flow_label.text = (
        "flow = ({:+.2f}, {:+.2f})   speed {:.2f}".format(
            flow_vec.x, flow_vec.z, mag(horizontal(flow_vec))
        )
    )

    status_label.text = (
        "round {} | cells {} | tethers {} | detached {} | avg speed {:.2f} | AI {} {} | mode {} | personality {}".format(
            ai.round,
            len(cells),
            active_tether_count,
            detached_count,
            avg_speed,
            "ON" if ai.enabled else "OFF",
            "(manual override)" if human_override_timer > 0 else "",
            ai.mode,
            ai.personality
        )
    )

    help_label.visible = show_help
    if show_help:
        help_label.text = (
            "Cell adhesion / detachment simulation\n"
            "Springs attach to the plane, stretch, snap, spill particles, and leave marks.\n\n"
            "Keyboard:\n"
            "Space/P pause | A toggle AI | R reset | H hide help\n"
            "N/B select cell | D detach selected | T attach selected | X impulse\n"
            "F/G flow +/- x | Q/E flow z | C clear trails | V trails | W wrapping\n"
            "M next AI mode | O toggle AI override sensitivity\n"
            "1 gardener  2 shear  3 detacher  4 orbit  5 organize\n"
            "6 rescue/dip  7 paint  8 chaos  9 construct/wrap  0 reset ritual\n"
            "Arrow keys push selected cell"
        )

def simulation_step(dt):
    global human_override_timer

    for c in cells:
        c.reset_forces()

    update_tethers(dt)
    natural_attachment_update(dt)
    collide_cells(dt)

    for c in cells:
        c.integrate(dt)

    remove_old_inactive_tethers()
    update_particles(dt)
    update_round_marks(dt)

    if human_override_timer > 0:
        human_override_timer = max(0.0, human_override_timer - dt)

# -----------------------------
# Start simulation
# -----------------------------

reset_simulation(randomize=False, announce=False)
make_round_mark("adhesion field initialized", vector(0, 2.1, 0), vector(0.25, 0.38, 0.60))

# -----------------------------
# Main loop
# -----------------------------

while True:
    rate(90)

    if not paused:
        sim_time += DT

        ai.update(DT)
        simulation_step(DT)

    update_flow_arrows()
    update_selection_visual()
    update_status_labels()
