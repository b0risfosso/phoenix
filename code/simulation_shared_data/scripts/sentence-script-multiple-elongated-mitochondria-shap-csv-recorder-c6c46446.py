from vpython import *
import random
import math
import time
import csv
import os
from datetime import datetime

# ------------------------------------------------------------
# CSV STORAGE VERSION
# 3D VPython Simulation: Mitochondria as Dynamic Power Stations
# Web-app compatible CSV output.
# Reads:
#   SIMULATION_CSV_OUTPUT_DIR
#   SIMULATION_CSV_RUN_ID
#   SIMULATION_CSV_RUN_SECONDS
# Fallback:
#   SIM_STATE_CSV_PATH
# ------------------------------------------------------------

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10
CSV_TRACK_STATIC_INTERVAL = 1.00

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-mitochondria-power-stations-state-log.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "mitochondria_power_stations_state_log.csv")
    )

csv_run_id = _csv_run_id

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="Mitochondria as Dynamic Power Stations - CSV Storage Run",
    width=1200,
    height=760,
    background=vector(0.94, 0.98, 1.0),
    center=vector(0, 0, 0)
)
scene.camera.pos = vector(0, -17, 10)
scene.camera.axis = vector(0, 17, -10)
scene.autoscale = False
scene.range = 9

# ------------------------------------------------------------
# Constants and state
# ------------------------------------------------------------

CELL_RADIUS = 7.0
NUCLEUS_RADIUS = 1.55
MAX_MITOCHONDRIA = 14
MIN_MITOCHONDRIA = 3
MAX_PARTICLES = 145
INITIAL_MITOCHONDRIA = 6
INITIAL_FUEL_PARTICLES = 32
DT = 0.025
ATP_COMPLETE_LEVEL = 235
ATP_EMPTY_LEVEL = 8

mitochondria = []
particles = []
decorations = []
round_number = 1
paused = False
ai_enabled = True
human_override_timer = 0.0
selected_index = 0
sim_time = 0.0
last_reset_time = 0.0
frame_count = 0

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return norm(fallback)
    return norm(v)


def random_unit_vector():
    z = random.uniform(-1, 1)
    t = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), r * math.sin(t), z)


def random_inside_cell(radius_margin=0.8):
    for _ in range(100):
        p = vector(
            random.uniform(-CELL_RADIUS + radius_margin, CELL_RADIUS - radius_margin),
            random.uniform(-CELL_RADIUS + radius_margin, CELL_RADIUS - radius_margin),
            random.uniform(-CELL_RADIUS + radius_margin, CELL_RADIUS - radius_margin)
        )
        if mag(p) < CELL_RADIUS - radius_margin and mag(p - nucleus.pos) > NUCLEUS_RADIUS + 0.55:
            return p
    return random_unit_vector() * random.uniform(1.0, CELL_RADIUS - radius_margin)


def random_on_cell_boundary():
    return random_unit_vector() * (CELL_RADIUS * random.uniform(0.92, 0.99))


def any_perpendicular(v):
    v = safe_norm(v)
    if abs(dot(v, vector(0, 0, 1))) < 0.85:
        p = cross(v, vector(0, 0, 1))
    else:
        p = cross(v, vector(0, 1, 0))
    return safe_norm(p, vector(0, 1, 0))


def segment_distance_to_point(a, b, p):
    ab = b - a
    denom = dot(ab, ab)
    if denom < 1e-8:
        return mag(p - a)
    u = clamp(dot(p - a, ab) / denom, 0, 1)
    return mag(p - (a + u * ab))


def hide_object(obj):
    try:
        if hasattr(obj, "clear_trail"):
            obj.clear_trail()
    except Exception:
        pass
    try:
        obj.visible = False
    except Exception:
        pass


def scaled_color(base, factor):
    return vector(clamp(base.x * factor, 0, 1), clamp(base.y * factor, 0, 1), clamp(base.z * factor, 0, 1))

# ------------------------------------------------------------
# Static world objects
# ------------------------------------------------------------

cell = sphere(pos=vector(0, 0, 0), radius=CELL_RADIUS, color=vector(0.65, 0.88, 1.0), opacity=0.11, shininess=0.35)
cell_shell = sphere(pos=vector(0, 0, 0), radius=CELL_RADIUS * 1.008, color=vector(0.40, 0.72, 0.95), opacity=0.055, shininess=0.55)
nucleus = sphere(pos=vector(-2.15, 1.75, -0.45), radius=NUCLEUS_RADIUS, color=vector(0.75, 0.70, 1.0), opacity=0.23, shininess=0.4)
nucleus_label = label(pos=nucleus.pos + vector(0, 0, NUCLEUS_RADIUS + 0.35), text="stationary nucleus", height=11, color=vector(0.38, 0.28, 0.7), box=False, opacity=0)
atp_label = label(pos=vector(-6.4, -6.9, 4.0), text="ATP level: 0", height=18, color=vector(0.05, 0.22, 0.32), box=True, border=7, background=vector(0.92, 0.98, 1.0), opacity=0.55)
mode_label = label(pos=vector(2.1, -6.9, 4.0), text="AI: starting", height=14, color=vector(0.10, 0.22, 0.32), box=True, border=6, background=vector(0.96, 1.0, 0.94), opacity=0.50)
help_label = label(pos=vector(0, 7.4, 4.8), text="CSV run | A AI | P pause | R reset | TAB select | F split | G fuse | N fuel", height=11, color=vector(0.08, 0.20, 0.30), box=False, opacity=0)
selected_label = label(pos=vector(0, 0, 0), text="", height=11, color=vector(0.1, 0.2, 0.25), box=False, opacity=0)
distant_light(direction=vector(-0.35, -0.55, -0.65), color=vector(0.72, 0.78, 0.85))
distant_light(direction=vector(0.45, 0.2, 0.4), color=vector(0.65, 0.72, 0.78))

# ------------------------------------------------------------
# Objects
# ------------------------------------------------------------

class Mitochondrion:
    next_id = 1

    def __init__(self, pos=None, axis=None, length=None, radius=None, activity=None):
        self.id = Mitochondrion.next_id
        Mitochondrion.next_id += 1
        self.pos = pos if pos is not None else random_inside_cell(1.2)
        self.axis = safe_norm(axis if axis is not None else random_unit_vector())
        self.length = length if length is not None else random.uniform(1.45, 2.65)
        self.radius = radius if radius is not None else random.uniform(0.30, 0.46)
        self.vel = random_unit_vector() * random.uniform(0.12, 0.35)
        self.spin = random.uniform(-0.55, 0.55)
        self.activity = activity if activity is not None else random.uniform(0.35, 0.95)
        self.atp = random.uniform(7, 18) * self.activity
        self.phase = random.uniform(0, 2 * math.pi)
        self.alive = True
        self.marked = False
        self.wrapped = False
        self.orbiting = False
        self.dipping = False
        self.organize_target = None
        self.ai_push = vector(0, 0, 0)
        self.outer_base = vector(1.0, 0.50, 0.16)
        self.inner_base = vector(1.0, 0.86, 0.30)
        self.body = cylinder(pos=self.pos - self.axis * self.length * 0.5, axis=self.axis * self.length, radius=self.radius, color=self.outer_base, opacity=0.62, shininess=0.75)
        self.end_a = sphere(pos=self.pos - self.axis * self.length * 0.5, radius=self.radius, color=self.outer_base, opacity=0.62, shininess=0.75)
        self.end_b = sphere(pos=self.pos + self.axis * self.length * 0.5, radius=self.radius, color=self.outer_base, opacity=0.62, shininess=0.75)
        self.glow = sphere(pos=self.pos, radius=self.radius * 1.65, color=vector(1.0, 0.78, 0.28), opacity=0.12, shininess=0, emissive=True)
        self.inner_points_count = 22
        self.inner_curve = curve(pos=self._inner_curve_points(), radius=max(0.018, self.radius * 0.045), color=self.inner_base, opacity=0.82)
        self.marker_ring = ring(pos=self.pos, axis=self.axis, radius=self.radius * 1.85, thickness=0.025, color=vector(0.1, 0.55, 1.0), opacity=0.0)
        self.wrapper = helix(pos=self.pos - self.axis * self.length * 0.55, axis=self.axis * self.length * 1.10, radius=self.radius * 1.22, coils=5, thickness=0.018, color=vector(0.12, 0.75, 0.55), opacity=0.0)

    def _inner_curve_points(self):
        points = []
        u = safe_norm(self.axis)
        p = any_perpendicular(u)
        q = safe_norm(cross(u, p), vector(0, 0, 1))
        for i in range(self.inner_points_count):
            t = i / (self.inner_points_count - 1)
            x = (t - 0.5) * self.length * 0.82
            wave = math.sin(t * math.pi * 7.0 + self.phase) * self.radius * 0.35
            wave2 = math.cos(t * math.pi * 5.0 + self.phase * 0.7) * self.radius * 0.18
            points.append(self.pos + u * x + p * wave + q * wave2)
        return points

    def endpoints(self):
        return self.pos - self.axis * self.length * 0.5, self.pos + self.axis * self.length * 0.5

    def contains_point(self, p, extra=0.0):
        a, b = self.endpoints()
        return segment_distance_to_point(a, b, p) <= self.radius + extra

    def add_force(self, f):
        self.ai_push += f

    def mark(self, value=True):
        self.marked = bool(value)
        self.marker_ring.opacity = 0.55 if self.marked else 0.0

    def wrap(self, value=True):
        self.wrapped = bool(value)
        self.wrapper.opacity = 0.58 if self.wrapped else 0.0

    def detach_all_visuals(self):
        self.mark(False); self.wrap(False); self.orbiting = False; self.dipping = False; self.organize_target = None

    def absorb_fuel(self, amount=1.0):
        self.activity = clamp(self.activity + 0.045 * amount, 0.05, 1.85)
        self.atp += random.uniform(2.3, 4.8) * amount
        self.glow.opacity = clamp(self.glow.opacity + 0.025, 0.05, 0.34)

    def emit_waste(self, count=1):
        for _ in range(count):
            if len(particles) < MAX_PARTICLES:
                particles.append(Particle(kind="waste", source=self))

    def spill(self, strength=1.0):
        self.emit_waste(random.randint(4, 8))
        self.activity = clamp(self.activity - 0.08 * strength, 0.05, 1.7)
        self.atp = max(0, self.atp - random.uniform(2.0, 5.0) * strength)

    def update(self, dt, t):
        if not self.alive:
            return
        flicker = 0.12 * math.sin(t * 2.0 + self.phase) + 0.05 * math.sin(t * 7.3 + self.phase * 0.3)
        self.activity = clamp(self.activity + random.uniform(-0.006, 0.006), 0.05, 1.8)
        visible_activity = clamp(self.activity + flicker, 0.05, 1.9)
        swim = vector(math.sin(t * 0.43 + self.phase), math.cos(t * 0.37 + self.phase * 0.7), math.sin(t * 0.31 + self.phase * 1.3)) * 0.018
        self.vel += swim + self.ai_push * dt
        self.ai_push *= 0.86
        if self.organize_target is not None:
            desired = self.organize_target - self.pos
            self.vel += safe_norm(desired) * clamp(mag(desired), 0, 1.2) * 0.045
        if self.orbiting:
            radial = self.pos if mag(self.pos) >= 0.1 else vector(1, 0, 0)
            tangent = safe_norm(cross(vector(0, 0, 1), radial), vector(0, 1, 0))
            self.vel += tangent * 0.075 - safe_norm(radial) * 0.026
        if self.dipping:
            self.vel.z += math.sin(t * 2.4 + self.phase) * 0.035
        away_nucleus = self.pos - nucleus.pos
        min_nucleus_dist = NUCLEUS_RADIUS + self.radius + 0.25
        if mag(away_nucleus) < min_nucleus_dist:
            self.vel += safe_norm(away_nucleus, random_unit_vector()) * 0.12
        future = self.pos + self.vel * dt
        boundary_limit = CELL_RADIUS - self.radius - self.length * 0.48
        if mag(future) > boundary_limit:
            n = safe_norm(future)
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.72
            self.pos = n * boundary_limit
        else:
            self.pos = future
        self.vel *= 0.992
        rot_axis = safe_norm(cross(self.axis, self.vel), any_perpendicular(self.axis))
        self.axis = safe_norm(rotate(self.axis, angle=self.spin * dt * 0.16, axis=rot_axis))
        self.axis = safe_norm(self.axis + safe_norm(self.vel, self.axis) * 0.003)
        self.atp = max(0, self.atp - dt * random.uniform(0.045, 0.10) * (0.5 + self.activity))
        if random.random() < 0.006 + self.activity * 0.002:
            self.emit_waste(1)
        self._update_visuals(visible_activity)

    def _update_visuals(self, visible_activity):
        c = scaled_color(self.outer_base, 0.55 + visible_activity * 0.55)
        inner_c = scaled_color(self.inner_base, 0.65 + visible_activity * 0.45)
        self.body.pos = self.pos - self.axis * self.length * 0.5
        self.body.axis = self.axis * self.length
        self.body.radius = self.radius
        self.body.color = c
        self.body.opacity = 0.52 + clamp(visible_activity, 0, 1.6) * 0.12
        self.end_a.pos = self.pos - self.axis * self.length * 0.5
        self.end_b.pos = self.pos + self.axis * self.length * 0.5
        self.end_a.radius = self.radius
        self.end_b.radius = self.radius
        self.end_a.color = c
        self.end_b.color = c
        self.end_a.opacity = self.body.opacity
        self.end_b.opacity = self.body.opacity
        self.glow.pos = self.pos
        self.glow.radius = self.radius * (1.7 + 0.25 * visible_activity)
        self.glow.opacity = clamp(0.04 + 0.105 * visible_activity, 0.035, 0.31)
        pts = self._inner_curve_points()
        for i, p in enumerate(pts):
            try:
                self.inner_curve.modify(i, pos=p, color=inner_c)
            except Exception:
                pass
        self.inner_curve.color = inner_c
        self.marker_ring.pos = self.pos
        self.marker_ring.axis = self.axis
        self.marker_ring.radius = self.radius * (1.9 + 0.12 * math.sin(sim_time * 4 + self.phase))
        self.marker_ring.opacity = 0.62 if self.marked else 0.0
        self.wrapper.pos = self.pos - self.axis * self.length * 0.56
        self.wrapper.axis = self.axis * self.length * 1.12
        self.wrapper.radius = self.radius * 1.22
        self.wrapper.opacity = 0.55 if self.wrapped else 0.0

    def hide(self):
        self.alive = False
        for obj in [self.body, self.end_a, self.end_b, self.glow, self.inner_curve, self.marker_ring, self.wrapper]:
            hide_object(obj)


class Particle:
    next_id = 1

    def __init__(self, kind="fuel", source=None, target=None):
        self.id = Particle.next_id
        Particle.next_id += 1
        self.kind = kind
        self.alive = True
        self.age = 0.0
        self.max_age = random.uniform(8.0, 16.0)
        self.attached = False
        self.attach_timer = 0.0
        self.attach_phase = random.uniform(0, 2 * math.pi)
        self.target = target
        self.source = source
        if kind == "fuel":
            self.pos = random_on_cell_boundary()
            self.vel = -safe_norm(self.pos) * random.uniform(0.22, 0.55) + random_unit_vector() * 0.08
            self.radius = random.uniform(0.045, 0.075)
            self.color = vector(0.35, 1.0, 0.42)
            self.opacity = 0.92
            self.trail_color = vector(0.55, 1.0, 0.55)
            self.max_age = random.uniform(12.0, 21.0)
        else:
            self.pos = source.pos + random_unit_vector() * source.radius * 1.35 if source is not None else random_inside_cell(0.4)
            self.vel = random_unit_vector() * random.uniform(0.25, 0.58)
            if source is not None:
                self.vel += source.vel * 0.5
            self.radius = random.uniform(0.035, 0.060)
            self.color = vector(0.46, 0.62, 0.78)
            self.opacity = 0.34
            self.trail_color = vector(0.50, 0.62, 0.72)
            self.max_age = random.uniform(4.5, 9.5)
        self.obj = sphere(pos=self.pos, radius=self.radius, color=self.color, opacity=self.opacity, emissive=(self.kind == "fuel"), make_trail=True, retain=18 if self.kind == "fuel" else 9, trail_radius=self.radius * 0.36, trail_color=self.trail_color)

    def choose_target(self):
        living = [m for m in mitochondria if m.alive]
        self.target = None if not living else sorted(living, key=lambda m: mag(m.pos - self.pos) - m.activity * 1.3)[0]

    def update(self, dt, t):
        if not self.alive:
            return
        self.age += dt
        if self.kind == "fuel":
            if self.target is None or not self.target.alive or random.random() < 0.006:
                self.choose_target()
            if self.target is not None:
                to_target = self.target.pos - self.pos
                d = mag(to_target)
                if self.attached:
                    self.attach_timer += dt
                    u = self.target.axis
                    p = any_perpendicular(u)
                    q = safe_norm(cross(u, p), vector(0, 0, 1))
                    orbit_r = self.target.radius * 1.35
                    angle = self.attach_phase + self.attach_timer * 9.0
                    axial = math.sin(self.attach_timer * 4.3 + self.attach_phase) * self.target.length * 0.35
                    desired = self.target.pos + u * axial + p * math.cos(angle) * orbit_r + q * math.sin(angle) * orbit_r
                    self.pos = self.pos * 0.72 + desired * 0.28
                    self.vel *= 0.75
                    if self.attach_timer > random.uniform(0.36, 0.8):
                        self.target.absorb_fuel(1.0)
                        self.kill()
                        return
                else:
                    attraction = safe_norm(to_target) * (0.40 + self.target.activity * 0.22)
                    swirl = safe_norm(cross(to_target, self.target.axis), random_unit_vector()) * 0.055
                    self.vel += (attraction + swirl) * dt
                    self.pos += self.vel * dt
                    if d < self.target.radius * 1.75:
                        self.attached = True
                        self.attach_timer = 0.0
            else:
                self.vel += -safe_norm(self.pos) * 0.015
                self.pos += self.vel * dt
        else:
            self.vel += safe_norm(self.pos, random_unit_vector()) * 0.006 + random_unit_vector() * 0.006
            self.pos += self.vel * dt
            self.vel *= 0.992
        if mag(self.pos) > CELL_RADIUS * 1.04:
            if self.kind == "waste":
                self.kill(); return
            n = safe_norm(self.pos)
            self.pos = n * CELL_RADIUS * 0.98
            self.vel = self.vel - 1.55 * dot(self.vel, n) * n
        if self.age > self.max_age:
            if self.kind == "fuel":
                self.kind = "waste"
                self.color = vector(0.46, 0.62, 0.78)
                self.obj.color = self.color
                self.obj.opacity = 0.30
                self.target = None
                self.max_age = self.age + random.uniform(3.0, 6.0)
            else:
                self.kill(); return
        self.obj.pos = self.pos
        pulse = 0.5 + 0.5 * math.sin(t * 8 + self.attach_phase)
        self.obj.radius = self.radius * ((0.92 + 0.28 * pulse) if self.kind == "fuel" else (0.9 + 0.16 * pulse))
        self.obj.opacity = 0.78 + 0.18 * pulse if self.kind == "fuel" else max(0.08, self.opacity * (1 - self.age / max(self.max_age, 0.1)))

    def kill(self):
        self.alive = False
        hide_object(self.obj)

# ------------------------------------------------------------
# Mechanics
# ------------------------------------------------------------

def total_atp():
    return sum(m.atp for m in mitochondria if m.alive)


def living_mitochondria():
    return [m for m in mitochondria if m.alive]


def selected_mito():
    living = living_mitochondria()
    return None if not living else living[selected_index % len(living)]


def spawn_fuel(count=1, target=None):
    for _ in range(count):
        if len(particles) < MAX_PARTICLES:
            particles.append(Particle(kind="fuel", target=target))


def spawn_mitochondrion(pos=None, axis=None, length=None, radius=None, activity=None):
    m = Mitochondrion(pos=pos, axis=axis, length=length, radius=radius, activity=activity)
    mitochondria.append(m)
    return m


def split_mitochondrion(m):
    if m is None or not m.alive or len(living_mitochondria()) >= MAX_MITOCHONDRIA or m.length < 1.05:
        return None
    split_dir = any_perpendicular(m.axis)
    child_length = clamp(m.length * random.uniform(0.48, 0.62), 0.85, 1.75)
    parent_length = clamp(m.length * random.uniform(0.58, 0.70), 0.95, 2.2)
    child_pos = m.pos + split_dir * (m.radius * 1.65)
    m.pos = m.pos - split_dir * (m.radius * 1.25)
    m.length = parent_length
    m.activity = clamp(m.activity * 0.86, 0.05, 1.6)
    m.atp *= 0.62
    m.vel += -split_dir * 0.28
    child = spawn_mitochondrion(pos=child_pos, axis=safe_norm(rotate(m.axis, angle=random.uniform(-0.55, 0.55), axis=split_dir)), length=child_length, radius=m.radius * random.uniform(0.90, 1.02), activity=clamp(m.activity * random.uniform(0.75, 1.1), 0.05, 1.4))
    child.atp = max(4, m.atp * random.uniform(0.55, 0.9))
    child.vel = split_dir * random.uniform(0.18, 0.38) + random_unit_vector() * 0.07
    child.mark(True)
    spawn_fuel(8, target=random.choice([m, child]))
    return child


def merge_mitochondria(a, b):
    if a is None or b is None or a is b or not a.alive or not b.alive:
        return None
    heavier = a if a.length >= b.length else b
    lighter = b if heavier is a else a
    total_len = clamp(a.length + b.length * 0.72, 1.1, 3.9)
    total_energy = a.atp + b.atp
    heavier.pos = (a.pos * a.length + b.pos * b.length) / max(a.length + b.length, 0.1)
    heavier.axis = safe_norm(a.axis * a.length + b.axis * b.length, heavier.axis)
    heavier.length = total_len
    heavier.radius = clamp((a.radius + b.radius) * 0.55, 0.28, 0.56)
    heavier.activity = clamp((a.activity + b.activity) * 0.58 + 0.08, 0.05, 1.8)
    heavier.atp = total_energy * 0.92
    heavier.vel = (a.vel + b.vel) * 0.48
    heavier.mark(True); heavier.wrap(True)
    lighter.hide()
    for _ in range(6):
        particles.append(Particle(kind="waste", source=heavier))
    return heavier


def handle_mitochondria_collisions():
    living = living_mitochondria()
    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a, b = living[i], living[j]
            d = mag(a.pos - b.pos)
            min_d = (a.radius + b.radius) * 1.6
            if d < min_d:
                n = safe_norm(a.pos - b.pos, random_unit_vector())
                overlap = min_d - d
                a.pos += n * overlap * 0.5
                b.pos -= n * overlap * 0.5
                av, bv = dot(a.vel, n), dot(b.vel, n)
                a.vel += (bv - av) * n * 0.6
                b.vel += (av - bv) * n * 0.6
                if d < (a.radius + b.radius) * 1.05 and len(living_mitochondria()) > MIN_MITOCHONDRIA and (a.marked or b.marked or a.wrapped or b.wrapped or random.random() < 0.012):
                    merge_mitochondria(a, b)
                    return


def clean_dead_objects():
    global particles, mitochondria
    particles = [p for p in particles if p.alive]
    mitochondria = [m for m in mitochondria if m.alive]


def update_labels():
    living = living_mitochondria()
    atp = total_atp()
    atp_label.text = f"ATP level: {atp:05.1f}   mitochondria: {len(living)}   fuel/waste: {len(particles)}   round: {round_number}"
    sm = selected_mito()
    if sm is not None:
        selected_label.pos = sm.pos + vector(0, 0, sm.radius + 0.65)
        selected_label.text = f"selected mito {sm.id}"
        selected_label.visible = True
    else:
        selected_label.visible = False


def reset_simulation(new_round=True):
    global mitochondria, particles, decorations, selected_index, round_number, sim_time, last_reset_time
    for m in mitochondria:
        m.hide()
    for p in particles:
        p.kill()
    for d in decorations:
        hide_object(d)
    mitochondria = []
    particles = []
    decorations = []
    selected_index = 0
    if new_round:
        round_number += 1
    for _ in range(INITIAL_MITOCHONDRIA):
        spawn_mitochondrion()
    for _ in range(INITIAL_FUEL_PARTICLES):
        spawn_fuel(1)
    last_reset_time = sim_time

# ------------------------------------------------------------
# AI Controller
# ------------------------------------------------------------

class MitoAIController:
    def __init__(self):
        self.enabled = True
        self.mode = "NOURISH"
        self.behavior_modes = ["NOURISH", "FUSION", "FISSION", "ORBIT", "ORGANIZE", "MARK_AND_WRAP", "SPILL", "CHAOS", "CALM", "ARTIST"]
        self.mode_started = 0.0
        self.next_mode_time = 4.0
        self.last_action_time = 0.0
        self.last_snapshot_time = 0.0
        self.last_snapshot = None
        self.stagnation_time = 0.0
        self.completion_hold = 0.0
        self.mode_history = []
        self.ritual_angle = 0.0

    def read_state(self):
        living = living_mitochondria()
        fuel = [p for p in particles if p.alive and p.kind == "fuel"]
        waste = [p for p in particles if p.alive and p.kind == "waste"]
        avg_activity = sum(m.activity for m in living) / max(1, len(living))
        avg_radius = sum(m.radius for m in living) / max(1, len(living))
        atp = total_atp()
        close_pairs = sum(1 for i in range(len(living)) for j in range(i + 1, len(living)) if mag(living[i].pos - living[j].pos) < 1.3)
        return {"time": sim_time, "mitochondria": living, "mitochondria_count": len(living), "fuel": fuel, "waste": waste, "fuel_count": len(fuel), "waste_count": len(waste), "particle_count": len(particles), "avg_activity": avg_activity, "avg_radius": avg_radius, "atp": atp, "close_pairs": close_pairs}

    def detect_stagnation_or_completion(self, state, dt):
        snapshot = (round(state["atp"], 1), state["mitochondria_count"], state["fuel_count"], state["waste_count"], round(state["avg_activity"], 2), state["close_pairs"])
        if self.last_snapshot is None:
            self.last_snapshot = snapshot
            self.last_snapshot_time = sim_time
            return False, False
        change = abs(snapshot[0] - self.last_snapshot[0]) + abs(snapshot[1] - self.last_snapshot[1]) * 12 + abs(snapshot[2] - self.last_snapshot[2]) * 0.35 + abs(snapshot[3] - self.last_snapshot[3]) * 0.25 + abs(snapshot[4] - self.last_snapshot[4]) * 20 + abs(snapshot[5] - self.last_snapshot[5]) * 3
        if sim_time - self.last_snapshot_time > 1.0:
            self.stagnation_time = self.stagnation_time + (sim_time - self.last_snapshot_time) if change < 1.25 else self.stagnation_time * 0.45
            self.last_snapshot = snapshot
            self.last_snapshot_time = sim_time
        complete = state["atp"] > ATP_COMPLETE_LEVEL or state["mitochondria_count"] <= 0 or (state["fuel_count"] <= 0 and state["atp"] < ATP_EMPTY_LEVEL and sim_time - last_reset_time > 8)
        return self.stagnation_time > 10.5 and sim_time - last_reset_time > 10, complete

    def choose_mode(self, state, force=False):
        if not force and sim_time < self.next_mode_time:
            return
        old_mode = self.mode
        if state["mitochondria_count"] < MIN_MITOCHONDRIA + 1:
            candidates = ["FISSION", "NOURISH", "ORGANIZE"]
        elif state["atp"] < 55:
            candidates = ["NOURISH", "CALM", "MARK_AND_WRAP"]
        elif state["fuel_count"] < 10:
            candidates = ["NOURISH", "ARTIST", "SPILL"]
        elif state["mitochondria_count"] > 10:
            candidates = ["FUSION", "ORGANIZE", "CALM"]
        elif state["close_pairs"] >= 2:
            candidates = ["FUSION", "SPILL", "ARTIST"]
        elif state["avg_activity"] > 1.25:
            candidates = ["SPILL", "ORBIT", "CHAOS", "ARTIST"]
        else:
            candidates = self.behavior_modes[:]
        recent = self.mode_history[-3:]
        candidates = [c for c in candidates if recent.count(c) < 2] or self.behavior_modes[:]
        self.mode = random.choice(candidates)
        self.mode_history.append(self.mode)
        self.mode_started = sim_time
        self.next_mode_time = sim_time + random.uniform(5.0, 10.0)
        if old_mode != self.mode:
            for m in state["mitochondria"]:
                if random.random() < 0.45: m.mark(False)
                if random.random() < 0.35: m.wrap(False)
                if self.mode not in ["ORBIT", "ARTIST"]: m.orbiting = False
                if self.mode != "ORGANIZE": m.organize_target = None

    def update(self, dt):
        global human_override_timer
        if not self.enabled or not ai_enabled:
            return
        if human_override_timer > 0:
            human_override_timer -= dt
            return
        state = self.read_state()
        stagnant, complete = self.detect_stagnation_or_completion(state, dt)
        if complete:
            self.completion_hold += dt
            mode_label.text = f"AI: COMPLETE - looping soon ({self.completion_hold:0.1f})"
            if self.completion_hold > 2.4:
                self.reset_round()
            return
        else:
            self.completion_hold = 0.0
        if stagnant:
            mode_label.text = "AI: STAGNATION DETECTED - stirring/resetting"
            self.stagnation_time = 0.0
            if random.random() < 0.50:
                self.mode = "CHAOS"
                self.next_mode_time = sim_time + 5.0
                self.perform_chaos(state, strong=True)
            else:
                self.reset_round()
            return
        self.choose_mode(state)
        {"NOURISH": self.perform_nourish, "FUSION": self.perform_fusion, "FISSION": self.perform_fission, "ORBIT": self.perform_orbit, "ORGANIZE": self.perform_organize, "MARK_AND_WRAP": self.perform_mark_and_wrap, "SPILL": self.perform_spill, "CHAOS": self.perform_chaos, "CALM": self.perform_calm, "ARTIST": self.perform_artist}.get(self.mode, self.perform_nourish)(state)
        mode_label.text = f"AI: {self.mode} | stagnation {self.stagnation_time:0.1f}s | override {'on' if human_override_timer > 0 else 'off'}"

    def reset_round(self):
        self.stagnation_time = 0.0
        self.completion_hold = 0.0
        self.last_snapshot = None
        self.next_mode_time = sim_time + 2.0
        self.mode = "NOURISH"
        reset_simulation(new_round=True)

    def perform_nourish(self, state):
        living = state["mitochondria"]
        if not living: return
        target = sorted(living, key=lambda m: m.atp + m.activity * 8)[0]
        target.mark(True)
        if sim_time - self.last_action_time > 0.22 and state["particle_count"] < MAX_PARTICLES:
            spawn_fuel(random.randint(1, 3), target=target)
            self.last_action_time = sim_time
        for p in state["fuel"][:25]:
            if p.target is None or random.random() < 0.05: p.target = target

    def perform_fusion(self, state):
        living = state["mitochondria"]
        if len(living) < 2: return
        center = sum((m.pos for m in living), vector(0, 0, 0)) / len(living)
        pair = sorted(living, key=lambda m: mag(m.pos - center))[:2]
        for m in pair:
            m.mark(True); m.wrap(True); m.add_force(safe_norm(center - m.pos, random_unit_vector()) * 2.8)
        if len(pair) == 2 and mag(pair[0].pos - pair[1].pos) < 0.85:
            merge_mitochondria(pair[0], pair[1])
            self.last_action_time = sim_time

    def perform_fission(self, state):
        living = state["mitochondria"]
        if not living: return
        target = sorted(living, key=lambda m: m.length + m.atp * 0.01, reverse=True)[0]
        target.mark(True); target.wrap(False)
        if sim_time - self.last_action_time > random.uniform(1.2, 2.2):
            split_mitochondrion(target)
            self.last_action_time = sim_time
        if state["fuel_count"] < 20: spawn_fuel(2, target=target)

    def perform_orbit(self, state):
        living = state["mitochondria"]
        for i, m in enumerate(living):
            m.orbiting = True; m.mark(i % 2 == 0)
            radial = m.pos if mag(m.pos) >= 1.0 else random_unit_vector() * 2
            target_radius = 3.4 + 0.8 * math.sin(sim_time * 0.5 + i)
            desired = safe_norm(radial) * target_radius
            tangent = safe_norm(cross(vector(0, 0, 1), radial), vector(0, 1, 0))
            m.add_force((desired - m.pos) * 0.45 + tangent * 0.85)
        if living and sim_time - self.last_action_time > 0.65:
            spawn_fuel(1, target=random.choice(living)); self.last_action_time = sim_time

    def perform_organize(self, state):
        living = state["mitochondria"]
        n = len(living)
        if n == 0: return
        ring_radius = clamp(1.7 + n * 0.24, 2.3, 4.8)
        for i, m in enumerate(living):
            angle = 2 * math.pi * i / n + 0.25 * math.sin(sim_time * 0.25)
            m.organize_target = vector(ring_radius * math.cos(angle), ring_radius * math.sin(angle), 0.9 * math.sin(angle * 2 + sim_time * 0.35))
            m.mark(i == selected_index % max(1, n)); m.wrap(False)

    def perform_mark_and_wrap(self, state):
        living = state["mitochondria"]
        for i, m in enumerate(living):
            m.mark(i % 2 == int(sim_time) % 2)
            if random.random() < 0.01: m.wrap(not m.wrapped)
        if living and sim_time - self.last_action_time > 1.2:
            target = random.choice(living); target.wrap(True); spawn_fuel(2, target=target); self.last_action_time = sim_time

    def perform_spill(self, state):
        living = state["mitochondria"]
        if not living: return
        target = sorted(living, key=lambda m: m.activity + m.atp * 0.01, reverse=True)[0]
        target.mark(True); target.dipping = True
        if sim_time - self.last_action_time > 1.0:
            target.spill(strength=0.75); self.last_action_time = sim_time
        for m in living[1:]: m.dipping = random.random() < 0.12

    def perform_chaos(self, state, strong=False):
        living = state["mitochondria"]
        strength = 3.4 if strong else 1.4
        for m in living:
            m.add_force(random_unit_vector() * random.uniform(0.6, strength))
            m.orbiting = random.random() < 0.32
            m.dipping = random.random() < 0.50
            if random.random() < 0.035: m.spill(0.6)
            if random.random() < 0.05: m.mark(not m.marked)
        if living and sim_time - self.last_action_time > 0.55:
            spawn_fuel(random.randint(1, 4), target=random.choice(living)); self.last_action_time = sim_time

    def perform_calm(self, state):
        living = state["mitochondria"]
        for m in living:
            m.orbiting = False; m.dipping = False; m.organize_target = None; m.vel *= 0.965; m.add_force(-m.pos * 0.035)
            if random.random() < 0.01: m.mark(False); m.wrap(False)
        if living and state["fuel_count"] < 12 and sim_time - self.last_action_time > 1.5:
            spawn_fuel(2, target=random.choice(living)); self.last_action_time = sim_time

    def perform_artist(self, state):
        living = state["mitochondria"]
        if not living: return
        self.ritual_angle += 0.03
        n = len(living)
        for i, m in enumerate(living):
            angle = self.ritual_angle + i * 2 * math.pi / n
            flower_radius = 2.6 + 1.0 * math.sin(3 * angle + sim_time * 0.5)
            m.organize_target = vector(flower_radius * math.cos(angle), flower_radius * math.sin(angle), 1.2 * math.sin(2 * angle))
            m.mark(True); m.wrap(i % 3 == int(sim_time) % 3); m.dipping = i % 2 == 0
        if sim_time - self.last_action_time > 0.35:
            target = random.choice(living); spawn_fuel(1, target=target)
            if random.random() < 0.25: target.emit_waste(1)
            self.last_action_time = sim_time

ai_controller = MitoAIController()

# ------------------------------------------------------------
# Keyboard control
# ------------------------------------------------------------

def human_override(seconds=3.5):
    global human_override_timer
    human_override_timer = max(human_override_timer, seconds)


def move_selected(direction):
    m = selected_mito()
    if m is not None:
        m.add_force(direction * 5.0); m.mark(True); human_override()


def keydown(evt):
    global paused, ai_enabled, selected_index
    k = evt.key.lower()
    if k in ["p", " "]:
        paused = not paused; human_override(1.0)
    elif k == "a":
        ai_enabled = not ai_enabled; ai_controller.enabled = ai_enabled; human_override(1.5)
    elif k == "r":
        reset_simulation(new_round=True); human_override(2.0)
    elif k == "tab":
        living = living_mitochondria()
        if living:
            selected_index = (selected_index + 1) % len(living)
            for m in living: m.mark(False)
            selected_mito().mark(True)
        human_override()
    elif k == "left": move_selected(vector(-1, 0, 0))
    elif k == "right": move_selected(vector(1, 0, 0))
    elif k == "up": move_selected(vector(0, 1, 0))
    elif k == "down": move_selected(vector(0, -1, 0))
    elif k == "pageup": move_selected(vector(0, 0, 1))
    elif k == "pagedown": move_selected(vector(0, 0, -1))
    elif k == "f": split_mitochondrion(selected_mito()); human_override()
    elif k == "g":
        living = living_mitochondria(); m = selected_mito()
        if m is not None and len(living) > 1:
            nearest = sorted([x for x in living if x is not m], key=lambda x: mag(x.pos - m.pos))[0]
            merge_mitochondria(m, nearest)
        human_override()
    elif k == "o":
        m = selected_mito()
        if m is not None: m.orbiting = not m.orbiting; m.mark(True)
        human_override()
    elif k == "d":
        m = selected_mito()
        if m is not None: m.spill(1.0)
        human_override()
    elif k == "w":
        m = selected_mito()
        if m is not None: m.wrap(not m.wrapped); m.mark(True)
        human_override()
    elif k == "m":
        m = selected_mito()
        if m is not None: m.mark(not m.marked)
        human_override()
    elif k == "n": spawn_fuel(8, target=selected_mito()); human_override()
    elif k == "c":
        for m in living_mitochondria(): m.detach_all_visuals()
        human_override()
    elif k == "s":
        m = selected_mito()
        if m is not None: m.dipping = not m.dipping; m.mark(True)
        human_override()

scene.bind("keydown", keydown)

# ------------------------------------------------------------
# CSV recording helpers
# ------------------------------------------------------------

CSV_FIELDS = [
    "run_id", "sim_time", "frame", "row_type", "entity_id", "entity_kind", "round_number",
    "ai_enabled", "ai_mode", "human_override_timer", "selected_index", "paused",
    "mitochondria_count", "fuel_count", "waste_count", "particle_count", "total_atp", "avg_activity", "close_pairs",
    "x", "y", "z", "vx", "vy", "vz", "axis_x", "axis_y", "axis_z",
    "length", "radius", "activity", "atp", "marked", "wrapped", "orbiting", "dipping", "organize_target_x", "organize_target_y", "organize_target_z",
    "particle_kind", "particle_age", "particle_max_age", "attached", "target_mito_id", "source_mito_id",
    "cell_radius", "nucleus_x", "nucleus_y", "nucleus_z", "nucleus_radius",
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDS)
_csv_writer.writeheader()
_next_csv_sample_time = 0.0
_next_static_sample_time = 0.0

def _base_csv_row(row_type, entity_id="", entity_kind=""):
    living = living_mitochondria()
    fuel_count = sum(1 for p in particles if p.alive and p.kind == "fuel")
    waste_count = sum(1 for p in particles if p.alive and p.kind == "waste")
    avg_activity = sum(m.activity for m in living) / max(1, len(living))
    close_pairs = sum(1 for i in range(len(living)) for j in range(i + 1, len(living)) if mag(living[i].pos - living[j].pos) < 1.3)
    return {
        "run_id": csv_run_id,
        "sim_time": round(sim_time, 5),
        "frame": frame_count,
        "row_type": row_type,
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "round_number": round_number,
        "ai_enabled": ai_enabled,
        "ai_mode": getattr(ai_controller, "mode", ""),
        "human_override_timer": round(human_override_timer, 5),
        "selected_index": selected_index,
        "paused": paused,
        "mitochondria_count": len(living),
        "fuel_count": fuel_count,
        "waste_count": waste_count,
        "particle_count": len(particles),
        "total_atp": round(total_atp(), 5),
        "avg_activity": round(avg_activity, 5),
        "close_pairs": close_pairs,
        "cell_radius": CELL_RADIUS,
        "nucleus_x": round(nucleus.pos.x, 5),
        "nucleus_y": round(nucleus.pos.y, 5),
        "nucleus_z": round(nucleus.pos.z, 5),
        "nucleus_radius": NUCLEUS_RADIUS,
    }


def _write_row(row):
    full = {field: "" for field in CSV_FIELDS}
    full.update(row)
    _csv_writer.writerow(full)


def record_csv_snapshot(include_static=False):
    _write_row(_base_csv_row("summary", "simulation", "summary"))

    for m in living_mitochondria():
        row = _base_csv_row("mitochondrion", m.id, "mitochondrion")
        row.update({
            "x": round(m.pos.x, 5), "y": round(m.pos.y, 5), "z": round(m.pos.z, 5),
            "vx": round(m.vel.x, 5), "vy": round(m.vel.y, 5), "vz": round(m.vel.z, 5),
            "axis_x": round(m.axis.x, 5), "axis_y": round(m.axis.y, 5), "axis_z": round(m.axis.z, 5),
            "length": round(m.length, 5), "radius": round(m.radius, 5), "activity": round(m.activity, 5), "atp": round(m.atp, 5),
            "marked": m.marked, "wrapped": m.wrapped, "orbiting": m.orbiting, "dipping": m.dipping,
        })
        if m.organize_target is not None:
            row.update({"organize_target_x": round(m.organize_target.x, 5), "organize_target_y": round(m.organize_target.y, 5), "organize_target_z": round(m.organize_target.z, 5)})
        _write_row(row)

    for p in particles:
        if not p.alive:
            continue
        row = _base_csv_row("particle", p.id, p.kind)
        row.update({
            "x": round(p.pos.x, 5), "y": round(p.pos.y, 5), "z": round(p.pos.z, 5),
            "vx": round(p.vel.x, 5), "vy": round(p.vel.y, 5), "vz": round(p.vel.z, 5),
            "radius": round(p.radius, 5), "particle_kind": p.kind, "particle_age": round(p.age, 5), "particle_max_age": round(p.max_age, 5),
            "attached": p.attached,
            "target_mito_id": getattr(p.target, "id", "") if p.target is not None else "",
            "source_mito_id": getattr(p.source, "id", "") if p.source is not None else "",
        })
        _write_row(row)

    if include_static:
        row = _base_csv_row("static_cell", "cell", "cell")
        row.update({"x": 0, "y": 0, "z": 0, "cell_radius": CELL_RADIUS})
        _write_row(row)
        row = _base_csv_row("static_nucleus", "nucleus", "nucleus")
        row.update({"x": round(nucleus.pos.x, 5), "y": round(nucleus.pos.y, 5), "z": round(nucleus.pos.z, 5), "radius": NUCLEUS_RADIUS})
        _write_row(row)

# ------------------------------------------------------------
# Initial scene setup
# ------------------------------------------------------------

for _ in range(INITIAL_MITOCHONDRIA):
    spawn_mitochondrion()
for _ in range(INITIAL_FUEL_PARTICLES):
    spawn_fuel(1)
if mitochondria:
    mitochondria[0].mark(True)

record_csv_snapshot(include_static=True)
update_labels()

# ------------------------------------------------------------
# Main simulation loop with finite CSV run
# ------------------------------------------------------------

while sim_time < CSV_RUN_SECONDS:
    rate(40)
    frame_count += 1

    if paused:
        mode_label.text = "PAUSED | P resumes | A toggles AI | R resets"
        record_csv_snapshot(include_static=False)
        continue

    sim_time += DT

    if ai_enabled:
        ai_controller.update(DT)

    if random.random() < 0.0015 and len(living_mitochondria()) < MAX_MITOCHONDRIA:
        candidates = [m for m in living_mitochondria() if m.length > 1.55 and m.activity > 0.35]
        if candidates:
            split_mitochondrion(random.choice(candidates))

    if random.random() < 0.008 and len(particles) < MAX_PARTICLES:
        target = random.choice(living_mitochondria()) if living_mitochondria() else None
        spawn_fuel(1, target=target)

    for m in list(mitochondria):
        m.update(DT, sim_time)
    for p in list(particles):
        p.update(DT, sim_time)

    handle_mitochondria_collisions()
    clean_dead_objects()

    if len(living_mitochondria()) < MIN_MITOCHONDRIA and sim_time - last_reset_time > 4:
        spawn_mitochondrion()
    if len(particles) < 8 and sim_time - last_reset_time > 4:
        spawn_fuel(4, target=selected_mito())

    sm = selected_mito()
    if sm is not None and not any(m.marked for m in living_mitochondria()):
        sm.mark(True)

    if sim_time >= _next_csv_sample_time:
        record_csv_snapshot(include_static=sim_time >= _next_static_sample_time)
        _next_csv_sample_time += CSV_SAMPLE_INTERVAL
        if sim_time >= _next_static_sample_time:
            _next_static_sample_time += CSV_TRACK_STATIC_INTERVAL
        if frame_count % 20 == 0:
            _csv_file.flush()

    update_labels()

record_csv_snapshot(include_static=True)
_csv_file.flush()
_csv_file.close()
mode_label.text = f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}"
print(f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {CSV_OUTPUT_PATH}")
