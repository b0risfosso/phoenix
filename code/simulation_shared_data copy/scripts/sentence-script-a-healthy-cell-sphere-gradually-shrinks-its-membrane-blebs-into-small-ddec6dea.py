from vpython import *
import random
import math
import csv
import os
import json
from datetime import datetime

# ============================================================
# Apoptotic Cell Fragmentation and Cleanup
# Full standalone VPython simulation with integrated CSV logging
# Compatible with the core sentence branching web app
# ============================================================

scene.title = "Apoptotic Cell Fragmentation and Cleanup - VPython CSV Logger"
scene.width = 1200
scene.height = 780
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.up = vector(0, 1, 0)
scene.camera.pos = vector(0, 4.5, 12)
scene.camera.axis = vector(0, -2.0, -12)
scene.autoscale = False
scene.range = 9.5

random.seed()

ARENA_RADIUS = 8.0
DT = 1.0 / 60.0

visuals = []
bodies = []
blebs = []
particles = []
scavengers = []
internal_structures = []

sim_time = 0.0
phase = "healthy"
paused = False
ai_enabled = True
manual_override = False
selected_scavenger_index = 0
pending_reset = False
round_number = 0
cleared_count = 0
body_serial = 0
keys_down = set()

BEHAVIOR_MODES = [
    "OBSERVE", "ORBIT", "MARK", "HERD", "ENGULF",
    "CAREFUL", "CHAOTIC", "ARTISTIC", "RESET_WAIT"
]

# ------------------------------------------------------------
# CSV logging configuration
# ------------------------------------------------------------

def _env_float(name, default):
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return float(default)

CSV_RUN_SECONDS = max(0.0, _env_float("SIMULATION_CSV_RUN_SECONDS", 60.0))
CSV_SAMPLE_HZ = max(0.05, _env_float("SIMULATION_CSV_SAMPLE_HZ", 10.0))
CSV_SAMPLE_INTERVAL = 1.0 / CSV_SAMPLE_HZ
CSV_OUTPUT_DIR = os.environ.get("SIMULATION_CSV_OUTPUT_DIR", "").strip()
CSV_RUN_ID = os.environ.get("SIMULATION_CSV_RUN_ID", "").strip() or datetime.now().strftime("%Y%m%d_%H%M%S")

if CSV_OUTPUT_DIR:
    os.makedirs(CSV_OUTPUT_DIR, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(CSV_OUTPUT_DIR, f"{CSV_RUN_ID}-apoptotic-fragmentation-cleanup-state-log.csv")
else:
    fallback_path = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
    if fallback_path:
        CSV_OUTPUT_PATH = fallback_path
        parent = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
        if parent:
            os.makedirs(parent, exist_ok=True)
    else:
        CSV_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apoptotic_fragmentation_cleanup_state_log.csv")

CSV_METADATA_PATH = os.path.splitext(CSV_OUTPUT_PATH)[0] + ".metadata.json"

CSV_FIELDNAMES = [
    "csv_run_id", "csv_elapsed_seconds", "simulation_time", "frame",
    "row_type", "object_id", "object_kind",
    "round_number", "phase", "paused", "ai_enabled", "manual_override",
    "ai_mode", "ai_mode_timer", "ai_stagnation_timer", "ai_reset_wait",
    "pending_reset", "selected_scavenger_index", "cleared_count",
    "body_count", "free_body_count", "marked_body_count", "captured_body_count",
    "bleb_count", "particle_count", "scavenger_count", "visual_count",
    "avg_body_speed", "avg_body_radius", "avg_scavenger_speed",
    "main_cell_radius", "main_cell_fragmented",
    "name", "source", "state", "marked", "captured_by", "dead",
    "x", "y", "z", "vx", "vy", "vz",
    "radius", "age", "life", "max_life",
    "engulfed_count", "wrap_timer", "target_body_id", "opacity",
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
_csv_writer.writeheader()
_csv_file.flush()

def _vec_fields(v, prefix=""):
    return {f"{prefix}x": float(v.x), f"{prefix}y": float(v.y), f"{prefix}z": float(v.z)}

def _opacity(obj):
    try:
        return obj.opacity
    except Exception:
        return ""

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def reg(obj):
    visuals.append(obj)
    return obj

def clamp(x, a, b):
    return max(a, min(b, x))

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def safe_norm(v):
    if mag(v) < 1e-8:
        return vector(1, 0, 0)
    return norm(v)

def rand_unit():
    z = random.uniform(-1, 1)
    a = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), z, r * math.sin(a))

def rand_in_sphere(radius=1.0):
    return rand_unit() * radius * (random.random() ** (1 / 3))

def rand_tangent(direction):
    d = safe_norm(direction)
    candidate = rand_unit()
    t = cross(d, candidate)
    if mag(t) < 0.01:
        t = cross(d, vector(0, 1, 0))
    return safe_norm(t)

def color_lerp(c1, c2, t):
    return vector(c1.x + (c2.x - c1.x) * t, c1.y + (c2.y - c1.y) * t, c1.z + (c2.z - c1.z) * t)

def hide_obj(obj):
    try:
        obj.visible = False
    except Exception:
        pass
    try:
        obj.clear_trail()
    except Exception:
        pass

# ------------------------------------------------------------
# Simulation objects
# ------------------------------------------------------------

class MainCell:
    def __init__(self):
        self.center = vector(0, 0, 0)
        self.initial_radius = 2.25
        self.radius = self.initial_radius
        self.fragmented = False
        self.bleb_timer = 0.0

        self.membrane = reg(sphere(pos=self.center, radius=self.radius, color=vector(1.0, 0.72, 0.78), opacity=0.32, shininess=0.35))
        self.inner_glow = reg(sphere(pos=self.center, radius=self.radius * 0.84, color=vector(1.0, 0.83, 0.88), opacity=0.12, shininess=0.15))
        self.nucleus = reg(sphere(pos=self.center + vector(-0.25, 0.08, 0.05), radius=0.78, color=vector(0.62, 0.48, 0.86), opacity=0.62, shininess=0.4))
        self.nucleus_label = reg(label(pos=self.nucleus.pos + vector(0, 0.85, 0), text="condensing nucleus", height=10, color=vector(0.38, 0.26, 0.62), box=False, opacity=0))
        self.label = reg(label(pos=self.center + vector(0, self.radius + 0.45, 0), text="healthy cell", height=15, color=vector(0.45, 0.15, 0.25), box=False, opacity=0))

        for _ in range(18):
            p = rand_in_sphere(self.radius * 0.65)
            r = random.uniform(0.055, 0.13)
            col = random.choice([vector(0.95, 0.48, 0.33), vector(0.70, 0.80, 0.45), vector(0.45, 0.75, 0.90), vector(0.88, 0.66, 0.30)])
            obj = reg(sphere(pos=self.center + p, radius=r, color=col, opacity=0.78, shininess=0.2))
            internal_structures.append({"obj": obj, "base": p, "spin": rand_tangent(p), "phase": random.uniform(0, 2 * math.pi), "radius": r})

    def update(self, t, dt):
        global phase
        if t < 5:
            phase = "healthy"
            self.radius = self.initial_radius + 0.035 * math.sin(t * 2.2)
            self.membrane.opacity = 0.32
            self.inner_glow.opacity = 0.12
            self.label.text = "healthy cell"
        elif t < 15:
            phase = "blebbing"
            k = (t - 5) / 10.0
            self.radius = lerp(self.initial_radius, 1.38, k) + 0.06 * math.sin(t * 4.5)
            self.membrane.opacity = 0.28
            self.inner_glow.opacity = 0.10
            self.label.text = "membrane blebbing + shrinkage"
            self.bleb_timer -= dt
            if self.bleb_timer <= 0 and len(blebs) < 38:
                blebs.append(Bleb(self, rand_unit()))
                self.bleb_timer = random.uniform(0.18, 0.55)
        elif t < 20:
            phase = "fragmentation"
            k = (t - 15) / 5.0
            self.radius = lerp(1.38, 0.55, k)
            self.membrane.opacity = max(0.04, 0.25 * (1 - k))
            self.inner_glow.opacity = max(0.0, 0.09 * (1 - k))
            self.label.text = "fragmentation into apoptotic bodies"
            if not self.fragmented and t > 16.2:
                self.fragmented = True
                self.create_apoptotic_bodies()
        else:
            phase = "cleanup" if len(bodies) > 0 else "complete"
            self.radius = max(0.1, self.radius * 0.985)
            self.membrane.opacity *= 0.97
            self.inner_glow.opacity *= 0.95
            self.label.text = "cleanup phase"

        self.membrane.radius = max(0.02, self.radius)
        self.inner_glow.radius = max(0.02, self.radius * 0.84)
        self.label.pos = self.center + vector(0, self.radius + 0.45, 0)

        if t > 5:
            k = clamp((t - 5) / 12.0, 0, 1)
            self.nucleus.radius = lerp(0.78, 0.32, k)
            self.nucleus.pos = lerp(self.nucleus.pos, self.center + vector(0.08, -0.04, 0), 0.025)
            self.nucleus.color = color_lerp(vector(0.62, 0.48, 0.86), vector(0.34, 0.16, 0.58), k)
            self.nucleus.opacity = max(0.08, 0.62 * (1 - clamp((t - 17) / 3.0, 0, 1)))
            self.nucleus_label.pos = self.nucleus.pos + vector(0, self.nucleus.radius + 0.25, 0)
            self.nucleus_label.text = "condensed chromatin"

        if t > 18.5:
            self.nucleus.visible = False
            self.nucleus_label.visible = False

        for item in internal_structures:
            obj = item["obj"]
            if not getattr(obj, "visible", True):
                continue
            if t < 16:
                k = clamp((t - 5) / 11.0, 0, 1)
                swirl = item["spin"] * 0.045 * math.sin(t * 2.0 + item["phase"])
                obj.pos = self.center + item["base"] * lerp(1.0, 0.38, k) + swirl
                obj.radius = item["radius"] * lerp(1.0, 0.62, k)
                obj.opacity = 0.78
            else:
                obj.opacity *= 0.94
                if obj.opacity < 0.04:
                    obj.visible = False

    def create_apoptotic_bodies(self):
        for _ in range(42):
            direction = rand_unit()
            local = rand_in_sphere(max(0.2, self.radius * 1.35))
            p = self.center + local + direction * random.uniform(0.2, 0.85)
            v = direction * random.uniform(0.15, 0.58) + rand_tangent(direction) * random.uniform(-0.11, 0.11)
            bodies.append(ApoptoticBody(p, v, random.uniform(0.095, 0.28), source="fragment"))
        for item in internal_structures:
            if getattr(item["obj"], "visible", True) and random.random() < 0.65:
                p = item["obj"].pos
                v = safe_norm(p - self.center) * random.uniform(0.12, 0.36) + rand_unit() * 0.08
                bodies.append(ApoptoticBody(p, v, random.uniform(0.06, 0.16), source="condensed organelle"))
            item["obj"].visible = False
        for b in blebs[:]:
            b.detach(force=True)
        self.nucleus.visible = False
        self.nucleus_label.visible = False

class Bleb:
    def __init__(self, cell, direction):
        self.cell = cell
        self.direction = safe_norm(direction)
        self.radius = random.uniform(0.10, 0.22)
        self.target_radius = random.uniform(0.22, 0.44)
        self.age = 0.0
        self.detached = False
        self.angular_axis = rand_tangent(self.direction)
        self.obj = reg(sphere(pos=self.cell.center + self.direction * (self.cell.radius + self.radius * 0.55), radius=self.radius, color=vector(1.0, 0.64, 0.73), opacity=0.46, shininess=0.45))

    def update(self, dt):
        if self.detached:
            return
        self.age += dt
        self.direction = rotate(self.direction, angle=0.18 * dt * math.sin(self.age * 1.7), axis=self.angular_axis)
        self.direction = safe_norm(self.direction)
        self.radius = lerp(self.radius, self.target_radius, 0.025)
        wobble = rand_tangent(self.direction) * 0.035 * math.sin(self.age * 5.0)
        self.obj.pos = self.cell.center + self.direction * (self.cell.radius + self.radius * 0.55) + wobble
        self.obj.radius = self.radius
        self.obj.opacity = 0.46 + 0.08 * math.sin(self.age * 3.1)
        if phase == "fragmentation" and (self.age > random.uniform(4.0, 8.0) or random.random() < 0.003):
            self.detach(force=True)

    def detach(self, force=False):
        if self.detached:
            return
        self.detached = True
        p = vector(self.obj.pos.x, self.obj.pos.y, self.obj.pos.z)
        v = safe_norm(p - self.cell.center) * random.uniform(0.2, 0.56) + rand_unit() * 0.06
        bodies.append(ApoptoticBody(p, v, max(0.06, self.radius * random.uniform(0.72, 0.95)), source="detached bleb"))
        self.obj.visible = False
        if self in blebs:
            blebs.remove(self)

class ApoptoticBody:
    def __init__(self, pos, vel, radius, source="fragment"):
        global body_serial
        body_serial += 1
        self.id = body_serial
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(vel.x, vel.y, vel.z)
        self.radius = radius
        self.source = source
        self.age = 0.0
        self.state = "free"
        self.marked = False
        self.captured_by = None
        self.capture_offset = vector(0, 0, 0)
        self.dead = False
        self.trail_timer = 0.0
        self.spin_axis = rand_unit()
        self.marker_ring = None
        col, op = (vector(0.56, 0.38, 0.76), 0.82) if source == "condensed organelle" else ((vector(1.0, 0.60, 0.70), 0.47) if source == "detached bleb" else (vector(1.0, 0.72, 0.62), 0.66))
        self.obj = reg(sphere(pos=self.pos, radius=self.radius, color=col, opacity=op, shininess=0.3))
        self.trail = reg(curve(color=vector(0.95, 0.72, 0.82), radius=0.008, retain=36))

    def mark(self):
        if self.dead or self.marked:
            return
        self.marked = True
        self.state = "marked"
        self.obj.color = vector(1.0, 0.82, 0.22)
        self.obj.opacity = max(self.obj.opacity, 0.72)
        self.marker_ring = reg(ring(pos=self.pos, axis=rand_unit(), radius=self.radius * 1.23, thickness=max(0.008, self.radius * 0.065), color=vector(1.0, 0.88, 0.16), opacity=0.72))

    def capture(self, scavenger):
        if self.dead or self.captured_by is not None:
            return
        self.captured_by = scavenger
        self.state = "captured"
        self.capture_offset = rand_in_sphere(scavenger.radius * 0.36)
        self.mark()
        self.obj.color = vector(0.98, 0.60, 0.18)
        self.obj.opacity = 0.78
        scavenger.engulfed_count += 1
        scavenger.wrap_timer = 1.0

    def update(self, dt):
        global cleared_count
        if self.dead:
            return
        self.age += dt
        if self.captured_by is None:
            self.vel *= 0.992
            self.vel += rand_unit() * 0.004
            self.pos += self.vel * dt
            if mag(self.pos) > ARENA_RADIUS:
                n = safe_norm(self.pos)
                self.pos = n * ARENA_RADIUS
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.76
            floor_y = -3.15
            if self.pos.y - self.radius < floor_y:
                self.pos.y = floor_y + self.radius
                if self.vel.y < 0:
                    self.vel.y *= -0.55
                    self.vel.x *= 0.92
                    self.vel.z *= 0.92
        else:
            target = self.captured_by.pos + self.capture_offset
            self.pos = lerp(self.pos, target, 0.075)
            self.vel = vector(0, 0, 0)
            self.radius *= 0.986
            if self.radius < 0.028 or mag(self.pos - self.captured_by.pos) < 0.05:
                self.delete()
                cleared_count += 1
                return

        self.obj.pos = self.pos
        self.obj.radius = self.radius
        if self.marker_ring:
            self.marker_ring.pos = self.pos
            self.marker_ring.axis = rotate(self.marker_ring.axis, angle=dt * 1.4, axis=self.spin_axis)
            self.marker_ring.radius = max(0.01, self.radius * 1.23)
        self.trail_timer += dt
        if self.trail_timer > 0.12:
            self.trail.append(pos=self.pos)
            self.trail_timer = 0.0

    def delete(self):
        self.dead = True
        self.obj.visible = False
        self.trail.visible = False
        if self.marker_ring:
            self.marker_ring.visible = False
        if self in bodies:
            bodies.remove(self)

class Particle:
    def __init__(self, pos, vel, color_value=vector(0.45, 0.84, 1.0), life=2.4, radius=0.035):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(vel.x, vel.y, vel.z)
        self.life = life
        self.max_life = life
        self.radius = radius
        self.dead = False
        self.obj = reg(sphere(pos=self.pos, radius=radius, color=color_value, opacity=0.42, shininess=0.2))

    def update(self, dt):
        if self.dead:
            return
        self.life -= dt
        self.vel *= 0.985
        self.vel += rand_unit() * 0.002
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0, 0.42 * self.life / self.max_life)
        for b in bodies:
            if b.dead or b.captured_by:
                continue
            if mag(b.pos - self.pos) < b.radius + self.radius + 0.18:
                b.mark()
                b.vel += safe_norm(b.pos - self.pos) * 0.035
        if self.life <= 0:
            self.dead = True
            self.obj.visible = False
            if self in particles:
                particles.remove(self)

class Scavenger:
    def __init__(self, pos, index, color_value):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(0, 0, 0)
        self.index = index
        self.radius = 0.86
        self.base_radius = self.radius
        self.color_value = color_value
        self.target = None
        self.engulfed_count = 0
        self.wrap_timer = 0.0
        self.spill_timer = random.uniform(0.3, 1.5)
        self.obj = reg(sphere(pos=self.pos, radius=self.radius, color=color_value, opacity=0.36, shininess=0.25))
        self.core = reg(sphere(pos=self.pos, radius=self.radius * 0.34, color=color_lerp(color_value, vector(1, 1, 1), 0.45), opacity=0.24, shininess=0.18))
        self.label = reg(label(pos=self.pos + vector(0, self.radius + 0.28, 0), text="scavenger", height=11, color=vector(0.18, 0.42, 0.50), box=False, opacity=0))
        self.pseudopods = [reg(cone(pos=self.pos, axis=vector(0, 0.01, 0), radius=0.08, color=color_lerp(color_value, vector(1, 1, 1), 0.25), opacity=0.30, visible=False)) for _ in range(4)]

    def nearest_body(self, marked_preferred=False):
        candidates = [b for b in bodies if not b.dead and b.captured_by is None]
        if marked_preferred:
            marked = [b for b in candidates if b.marked]
            if marked:
                candidates = marked
        if not candidates:
            return None
        return min(candidates, key=lambda b: mag(b.pos - self.pos))

    def move_toward(self, target_pos, speed=1.0, careful=False):
        desired = target_pos - self.pos
        dist = mag(desired)
        if dist < 0.001:
            return
        desired_dir = desired / dist
        max_speed = speed * (clamp(dist / 2.2, 0.25, 1.0) if careful else 1.0)
        avoid = vector(0, 0, 0)
        for other in scavengers:
            if other is self:
                continue
            dvec = self.pos - other.pos
            d = mag(dvec)
            if 0.001 < d < self.radius * 2.35:
                avoid += safe_norm(dvec) * (self.radius * 2.35 - d) * 0.75
        self.vel = lerp(self.vel, desired_dir * max_speed + avoid, 0.06)

    def orbit(self, center, angular_speed, orbit_radius, phase_offset=0.0, vertical_amp=0.4):
        a = sim_time * angular_speed + phase_offset
        target = center + vector(math.cos(a) * orbit_radius, math.sin(a * 0.7) * vertical_amp, math.sin(a) * orbit_radius)
        self.move_toward(target, speed=1.25)

    def spill_enzymes(self, amount=3):
        for _ in range(amount):
            direction = rand_unit()
            particles.append(Particle(self.pos + direction * self.radius * 0.9, direction * random.uniform(0.18, 0.55) + self.vel * 0.15, color_value=vector(0.45, 0.84, 1.0), life=random.uniform(1.2, 2.8), radius=random.uniform(0.022, 0.045)))

    def update(self, dt):
        self.spill_timer -= dt
        self.wrap_timer = max(0, self.wrap_timer - dt)
        self.pos += self.vel * dt
        self.vel *= 0.965
        if mag(self.pos) > ARENA_RADIUS - self.radius * 0.5:
            n = safe_norm(self.pos)
            self.pos = n * (ARENA_RADIUS - self.radius * 0.5)
            self.vel -= n * dot(self.vel, n) * 1.2
        self.radius = self.base_radius * (1.0 + 0.035 * math.sin(sim_time * 2.2 + self.index))
        if self.wrap_timer > 0:
            self.radius *= 1.0 + 0.08 * self.wrap_timer
        self.obj.pos = self.pos
        self.obj.radius = self.radius
        self.core.pos = self.pos + vector(0, 0.02 * math.sin(sim_time * 2.7), 0)
        self.core.radius = self.radius * 0.34
        self.label.pos = self.pos + vector(0, self.radius + 0.25, 0)
        self.label.text = "scavenger " + str(self.index + 1) + " cleared:" + str(self.engulfed_count)
        target_body = self.target
        if target_body is None or target_body.dead or target_body.captured_by is not None:
            target_body = self.nearest_body(marked_preferred=True)
        self.update_pseudopods(target_body)
        for b in bodies[:]:
            if b.dead or b.captured_by is not None:
                continue
            d = mag(b.pos - self.pos)
            if d < self.radius + b.radius + 0.20:
                b.mark()
                self.wrap_timer = 0.75
                b.capture(self)
            elif d < self.radius + b.radius + 0.72:
                b.mark()
                b.vel += safe_norm(self.pos - b.pos) * 0.028

    def update_pseudopods(self, body):
        if body is None or body.dead:
            for p in self.pseudopods:
                p.visible = False
            return
        direction = safe_norm(body.pos - self.pos)
        distance = mag(body.pos - self.pos)
        active_count = 4 if distance < 2.8 else 2
        for i, pod in enumerate(self.pseudopods):
            if i >= active_count:
                pod.visible = False
                continue
            side = rand_tangent(direction) * (0.05 * math.sin(sim_time * 3 + i))
            axis_dir = safe_norm(direction + side)
            start = self.pos + axis_dir * self.radius * 0.55
            length = clamp(distance - self.radius * 0.35, 0.12, 1.25)
            pod.visible = True
            pod.pos = start
            pod.axis = axis_dir * length
            pod.radius = 0.09 + 0.04 * math.sin(sim_time * 4 + i)
            pod.opacity = 0.23 + 0.22 * self.wrap_timer

# ------------------------------------------------------------
# AI controller
# ------------------------------------------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode = "OBSERVE"
        self.mode_timer = 0.0
        self.mode_duration = 6.0
        self.last_mode = None
        self.stagnation_timer = 0.0
        self.last_body_count = 0
        self.last_cleared = 0
        self.reset_wait = 0.0
        self.chaos_seed = random.uniform(0, 1000)

    def read_state(self):
        free = [b for b in bodies if not b.dead and b.captured_by is None]
        marked = [b for b in free if b.marked]
        captured = [b for b in bodies if not b.dead and b.captured_by is not None]
        avg_speed = sum(mag(b.vel) for b in free) / max(1, len(free))
        center = vector(0, 0, 0)
        if free:
            for b in free:
                center += b.pos
            center /= len(free)
        return {"phase": phase, "free": free, "marked": marked, "captured": captured, "body_count": len(bodies), "free_count": len(free), "marked_count": len(marked), "captured_count": len(captured), "avg_speed": avg_speed, "center": center, "cleared": cleared_count}

    def detect_stagnation_or_completion(self, state, dt):
        global pending_reset
        complete = (phase == "complete" and state["body_count"] == 0 and sim_time > 20)
        empty_cleanup = (phase == "cleanup" and state["body_count"] == 0 and sim_time > 20)
        slow = state["avg_speed"] < 0.012
        unchanged = (state["body_count"] == self.last_body_count and cleared_count == self.last_cleared)
        if sim_time > 21 and unchanged and slow:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 0.8)
        self.last_body_count = state["body_count"]
        self.last_cleared = cleared_count
        if complete or empty_cleanup:
            self.mode = "RESET_WAIT"
            self.reset_wait += dt
            if self.reset_wait > 4.0:
                pending_reset = True
        elif self.stagnation_timer > 9.0:
            self.mode = "RESET_WAIT"
            self.reset_wait += dt
            if self.reset_wait > 2.0:
                pending_reset = True
        else:
            if self.mode != "RESET_WAIT":
                self.reset_wait = 0.0

    def set_mode(self, mode_name):
        if mode_name == self.mode:
            return
        self.last_mode = self.mode
        self.mode = mode_name
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(4.0, 9.5)
        if mode_name == "CHAOTIC":
            self.mode_duration = random.uniform(2.2, 5.0)
        if mode_name == "CAREFUL":
            self.mode_duration = random.uniform(5.0, 11.0)

    def choose_mode(self, state, dt):
        if self.mode == "RESET_WAIT":
            return
        self.mode_timer += dt
        force_change = self.mode_timer > self.mode_duration
        if phase in ["healthy", "blebbing"]:
            if force_change or self.mode not in ["OBSERVE", "ORBIT", "ARTISTIC"]:
                self.set_mode(random.choice(["OBSERVE", "ORBIT", "ARTISTIC"]))
            return
        if phase == "fragmentation":
            if force_change or self.mode == "OBSERVE":
                self.set_mode(random.choice(["ORBIT", "MARK", "HERD", "ARTISTIC"]))
            return
        if phase == "cleanup":
            free_count = state["free_count"]
            marked_count = state["marked_count"]
            if free_count == 0:
                self.set_mode("RESET_WAIT")
                return
            if marked_count < max(2, free_count * 0.35):
                pool = ["MARK", "HERD", "ARTISTIC"]
            elif free_count > 20:
                pool = ["HERD", "ENGULF", "CHAOTIC", "MARK"]
            elif free_count > 6:
                pool = ["ENGULF", "CAREFUL", "HERD", "ARTISTIC"]
            else:
                pool = ["CAREFUL", "ENGULF", "ORBIT"]
            if force_change or self.mode not in pool:
                self.set_mode(random.choice(pool))

    def controllable_scavengers(self):
        return [(i, s) for i, s in enumerate(scavengers) if not (manual_override and i == selected_scavenger_index)]

    def update(self, dt):
        if not self.enabled:
            return
        state = self.read_state()
        self.detect_stagnation_or_completion(state, dt)
        self.choose_mode(state, dt)

        if self.mode == "RESET_WAIT":
            for i, s in self.controllable_scavengers():
                s.orbit(vector(0, 0, 0), 0.32 + i * 0.04, 4.4 + 0.25 * i, phase_offset=i * 2.1, vertical_amp=0.25)
            return
        if self.mode == "OBSERVE":
            self.behave_observe(state, dt)
        elif self.mode == "ORBIT":
            self.behave_orbit(state, dt)
        elif self.mode == "MARK":
            self.behave_mark(state, dt)
        elif self.mode == "HERD":
            self.behave_herd(state, dt)
        elif self.mode == "ENGULF":
            self.behave_engulf(state, dt)
        elif self.mode == "CAREFUL":
            self.behave_careful(state, dt)
        elif self.mode == "CHAOTIC":
            self.behave_chaotic(state, dt)
        elif self.mode == "ARTISTIC":
            self.behave_artistic(state, dt)

    def behave_observe(self, state, dt):
        for i, s in self.controllable_scavengers():
            s.target = None
            s.orbit(vector(0, 0, 0), 0.18 + i * 0.05, 5.8 + i * 0.25, phase_offset=i * 2.0, vertical_amp=0.65)

    def behave_orbit(self, state, dt):
        radius = 3.4 if phase in ["healthy", "blebbing", "fragmentation"] else 5.0
        for i, s in self.controllable_scavengers():
            s.target = None
            s.orbit(vector(0, 0, 0), 0.42 + i * 0.08, radius + 0.22 * i, phase_offset=i * 2.1, vertical_amp=0.9)
            if phase == "fragmentation" and random.random() < 0.025:
                s.spill_enzymes(1)

    def behave_mark(self, state, dt):
        unmarked = [b for b in state["free"] if not b.marked]
        for i, s in self.controllable_scavengers():
            if unmarked:
                b = min(unmarked, key=lambda x: mag(x.pos - s.pos))
                s.target = b
                s.move_toward(b.pos + safe_norm(s.pos - b.pos) * 0.55, speed=1.35)
                if mag(b.pos - s.pos) < 1.7:
                    b.mark()
                    if s.spill_timer <= 0:
                        s.spill_enzymes(2)
                        s.spill_timer = random.uniform(0.7, 1.8)
            else:
                s.orbit(state["center"], 0.5 + i * 0.1, 2.3 + i * 0.25, phase_offset=i * 2.0, vertical_amp=0.3)

    def behave_herd(self, state, dt):
        free = state["free"]
        if not free:
            self.behave_orbit(state, dt)
            return
        cleanup_center = vector(0, -0.2, 0)
        for b in free:
            to_center = cleanup_center - b.pos
            if mag(to_center) > 0.5:
                b.vel += safe_norm(to_center) * 0.006
            b.vel += cross(vector(0, 1, 0), safe_norm(b.pos - cleanup_center)) * 0.002
        for i, s in self.controllable_scavengers():
            farthest = max(free, key=lambda x: mag(x.pos - cleanup_center))
            s.target = farthest
            s.move_toward(farthest.pos + safe_norm(farthest.pos - cleanup_center) * 0.85, speed=1.45)
            if mag(s.pos - farthest.pos) < 1.7:
                farthest.mark()

    def behave_engulf(self, state, dt):
        for i, s in self.controllable_scavengers():
            target = s.nearest_body(marked_preferred=True)
            s.target = target
            if target:
                s.move_toward(target.pos + target.vel * 0.7, speed=1.75)
                if mag(target.pos - s.pos) < 1.9:
                    target.mark()
                if s.spill_timer <= 0 and random.random() < 0.35:
                    s.spill_enzymes(1)
                    s.spill_timer = random.uniform(1.0, 2.2)
            else:
                s.orbit(vector(0, 0, 0), 0.35, 4.2, phase_offset=i * 2.2)

    def behave_careful(self, state, dt):
        for i, s in self.controllable_scavengers():
            target = s.nearest_body(marked_preferred=True)
            s.target = target
            if target:
                s.move_toward(target.pos + rand_tangent(target.pos - s.pos) * 0.15, speed=0.95, careful=True)
                if mag(target.pos - s.pos) < 2.1:
                    target.mark()
            else:
                s.orbit(vector(0, 0, 0), 0.22 + i * 0.03, 3.6, phase_offset=i * 2.2)
        for b in state["free"]:
            b.vel *= 0.997

    def behave_chaotic(self, state, dt):
        for i, s in self.controllable_scavengers():
            a = sim_time * (1.7 + i * 0.19) + self.chaos_seed + i * 2.3
            target = vector(math.sin(a * 0.7) * 5.0, math.sin(a * 1.1) * 2.3, math.cos(a * 0.9) * 5.0)
            s.target = None
            s.move_toward(target, speed=2.15)
            if s.spill_timer <= 0:
                s.spill_enzymes(random.randint(2, 5))
                s.spill_timer = random.uniform(0.25, 0.75)
        for b in state["free"]:
            r = b.pos
            if mag(r) > 0.3:
                b.vel += cross(vector(0, 1, 0), safe_norm(r)) * 0.009
            if random.random() < 0.003:
                b.mark()

    def behave_artistic(self, state, dt):
        free = state["free"]
        ring_radius = 2.6 + 0.5 * math.sin(sim_time * 0.5)
        for n, b in enumerate(free):
            angle = (n / max(1, len(free))) * 2 * math.pi + sim_time * 0.12
            desired = vector(math.cos(angle) * ring_radius, 0.45 * math.sin(angle * 2 + sim_time), math.sin(angle) * ring_radius)
            b.vel += (desired - b.pos) * 0.0025
            if random.random() < 0.0025:
                b.mark()
        for i, s in self.controllable_scavengers():
            angle = sim_time * 0.55 + i * 2 * math.pi / max(1, len(scavengers))
            target = vector(math.cos(angle) * 4.0, 0.6 * math.sin(angle * 1.5), math.sin(angle) * 4.0)
            s.target = None
            s.move_toward(target, speed=1.25)
            if free and random.random() < 0.025:
                chosen = random.choice(free)
                if mag(chosen.pos - s.pos) < 2.0:
                    chosen.mark()

# ------------------------------------------------------------
# Environment, reset, controls, CSV snapshots
# ------------------------------------------------------------

main_cell = None
ai_controller = AIController()
floor_obj = None
hud = None
mode_label = None

def make_environment():
    global floor_obj
    floor_obj = reg(box(pos=vector(0, -3.22, 0), size=vector(14.5, 0.035, 14.5), color=vector(0.90, 0.95, 0.97), opacity=0.40))
    for x in range(-7, 8):
        reg(curve(pos=[vector(x, -3.195, -7), vector(x, -3.195, 7)], color=vector(0.80, 0.88, 0.92), radius=0.004))
    for z in range(-7, 8):
        reg(curve(pos=[vector(-7, -3.19, z), vector(7, -3.19, z)], color=vector(0.80, 0.88, 0.92), radius=0.004))
    reg(ring(pos=vector(0, -3.16, 0), axis=vector(0, 1, 0), radius=ARENA_RADIUS, thickness=0.015, color=vector(0.64, 0.78, 0.84), opacity=0.40))
    reg(label(pos=vector(0, -3.0, -7.35), text="light extracellular space", height=11, color=vector(0.32, 0.48, 0.56), box=False, opacity=0))

def create_scavengers():
    colors = [vector(0.46, 0.86, 0.92), vector(0.52, 0.78, 0.96), vector(0.55, 0.90, 0.72)]
    starts = [vector(-5.7, 0.15, -2.5), vector(5.6, 0.45, 2.2), vector(0.6, 0.25, 5.9)]
    for i in range(3):
        scavengers.append(Scavenger(starts[i], i, colors[i]))

def clear_visuals():
    for obj in visuals:
        hide_obj(obj)
    visuals[:] = []
    bodies[:] = []
    blebs[:] = []
    particles[:] = []
    scavengers[:] = []
    internal_structures[:] = []

def reset_simulation():
    global main_cell, sim_time, phase, pending_reset, round_number, cleared_count, body_serial, selected_scavenger_index
    clear_visuals()
    sim_time = 0.0
    phase = "healthy"
    pending_reset = False
    cleared_count = 0
    body_serial = 0
    selected_scavenger_index = 0
    round_number += 1
    make_environment()
    main_cell = MainCell()
    create_scavengers()
    ai_controller.mode = "OBSERVE"
    ai_controller.mode_timer = 0.0
    ai_controller.mode_duration = 5.0
    ai_controller.stagnation_timer = 0.0
    ai_controller.reset_wait = 0.0
    ai_controller.last_body_count = 0
    ai_controller.last_cleared = 0

def collide_bodies():
    for i in range(len(bodies)):
        a = bodies[i]
        if a.dead or a.captured_by is not None:
            continue
        for j in range(i + 1, len(bodies)):
            b = bodies[j]
            if b.dead or b.captured_by is not None:
                continue
            delta = b.pos - a.pos
            d = mag(delta)
            min_d = a.radius + b.radius
            if 0.0001 < d < min_d:
                n = delta / d
                overlap = min_d - d
                a.pos -= n * overlap * 0.5
                b.pos += n * overlap * 0.5
                rel = b.vel - a.vel
                vn = dot(rel, n)
                if vn < 0:
                    impulse = -vn * 0.52
                    a.vel -= n * impulse
                    b.vel += n * impulse

def manual_control_update(dt):
    if not manual_override or not scavengers:
        return
    s = scavengers[selected_scavenger_index % len(scavengers)]
    move = vector(0, 0, 0)
    if "w" in keys_down or "up" in keys_down:
        move += vector(0, 0, -1)
    if "s" in keys_down or "down" in keys_down:
        move += vector(0, 0, 1)
    if "a" in keys_down or "left" in keys_down:
        move += vector(-1, 0, 0)
    if "d" in keys_down or "right" in keys_down:
        move += vector(1, 0, 0)
    if "q" in keys_down:
        move += vector(0, 1, 0)
    if "e" in keys_down:
        move += vector(0, -1, 0)
    if mag(move) > 0:
        s.vel = lerp(s.vel, safe_norm(move) * 2.0, 0.18)
    if "m" in keys_down:
        b = s.nearest_body(marked_preferred=False)
        if b and mag(b.pos - s.pos) < 2.5:
            b.mark()
    if "x" in keys_down:
        s.spill_enzymes(1)

def update_highlight():
    for i, s in enumerate(scavengers):
        if manual_override and i == selected_scavenger_index:
            s.obj.opacity = 0.55
            s.obj.color = vector(0.30, 0.72, 0.95)
            s.label.color = vector(0.05, 0.32, 0.55)
        else:
            s.obj.opacity = 0.36
            s.obj.color = s.color_value
            s.label.color = vector(0.18, 0.42, 0.50)

def update_hud():
    if hud is None:
        return
    remaining = len([b for b in bodies if not b.dead])
    free = len([b for b in bodies if not b.dead and b.captured_by is None])
    marked = len([b for b in bodies if not b.dead and b.marked])
    captured = len([b for b in bodies if not b.dead and b.captured_by is not None])
    hud.text = f"Round: {round_number}   Phase: {phase}   Bodies: {remaining}   Free: {free}   Marked: {marked}   Captured: {captured}   Cleared: {cleared_count}"
    mode_label.text = (
        "AI: " + ("ON" if ai_enabled else "OFF") +
        "   Mode: " + ai_controller.mode +
        "   Human override: " + ("ON" if manual_override else "OFF") +
        "   Selected scavenger: " + str(selected_scavenger_index + 1) +
        "\nKeys: Space pause | I toggle AI | H human override | Tab select | WASD/arrows move | Q/E up/down | M mark | X spill | R reset"
    )

def keydown(evt):
    global paused, ai_enabled, manual_override, selected_scavenger_index, pending_reset
    k = evt.key
    keys_down.add(k.lower())
    if k == " ":
        paused = not paused
    elif k in ["i", "I"]:
        ai_enabled = not ai_enabled
        ai_controller.enabled = ai_enabled
    elif k in ["h", "H"]:
        manual_override = not manual_override
    elif k == "tab":
        if scavengers:
            selected_scavenger_index = (selected_scavenger_index + 1) % len(scavengers)
    elif k in ["r", "R"]:
        pending_reset = True
    elif k in ["p", "P"]:
        paused = not paused
    elif k in ["1", "2", "3"]:
        idx = int(k) - 1
        if idx < len(scavengers):
            selected_scavenger_index = idx
            manual_override = True

def keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

hud = label(pos=vector(0, 4.45, 0), text="", height=13, color=vector(0.16, 0.25, 0.32), box=False, opacity=0)
mode_label = label(pos=vector(0, 4.05, 0), text="", height=11, color=vector(0.22, 0.38, 0.45), box=False, opacity=0)

def csv_scene_state():
    live_bodies = [b for b in bodies if not b.dead]
    free_bodies = [b for b in live_bodies if b.captured_by is None]
    marked_bodies = [b for b in live_bodies if b.marked]
    captured_bodies = [b for b in live_bodies if b.captured_by is not None]
    avg_body_speed = sum(mag(b.vel) for b in live_bodies) / max(1, len(live_bodies))
    avg_body_radius = sum(b.radius for b in live_bodies) / max(1, len(live_bodies))
    avg_scavenger_speed = sum(mag(s.vel) for s in scavengers) / max(1, len(scavengers))
    return {
        "round_number": round_number,
        "phase": phase,
        "paused": paused,
        "ai_enabled": ai_enabled,
        "manual_override": manual_override,
        "ai_mode": ai_controller.mode,
        "ai_mode_timer": ai_controller.mode_timer,
        "ai_stagnation_timer": ai_controller.stagnation_timer,
        "ai_reset_wait": ai_controller.reset_wait,
        "pending_reset": pending_reset,
        "selected_scavenger_index": selected_scavenger_index,
        "cleared_count": cleared_count,
        "body_count": len(live_bodies),
        "free_body_count": len(free_bodies),
        "marked_body_count": len(marked_bodies),
        "captured_body_count": len(captured_bodies),
        "bleb_count": len(blebs),
        "particle_count": len(particles),
        "scavenger_count": len(scavengers),
        "visual_count": len(visuals),
        "avg_body_speed": avg_body_speed,
        "avg_body_radius": avg_body_radius,
        "avg_scavenger_speed": avg_scavenger_speed,
        "main_cell_radius": main_cell.radius if main_cell is not None else "",
        "main_cell_fragmented": main_cell.fragmented if main_cell is not None else "",
    }

def csv_base_row(csv_elapsed_seconds, frame, row_type, object_id="", object_kind=""):
    row = {
        "csv_run_id": CSV_RUN_ID,
        "csv_elapsed_seconds": round(csv_elapsed_seconds, 4),
        "simulation_time": round(sim_time, 4),
        "frame": frame,
        "row_type": row_type,
        "object_id": object_id,
        "object_kind": object_kind,
    }
    row.update(csv_scene_state())
    return row

def write_csv_snapshot(csv_elapsed_seconds, frame):
    _csv_writer.writerow(csv_base_row(csv_elapsed_seconds, frame, "summary", "apoptosis_scene", "summary"))
    if main_cell is not None:
        row = csv_base_row(csv_elapsed_seconds, frame, "main_cell", "main_cell", "cell")
        row.update({"state": phase, "radius": main_cell.radius, "dead": main_cell.fragmented, "opacity": _opacity(main_cell.membrane)})
        row.update(_vec_fields(main_cell.center, ""))
        _csv_writer.writerow(row)
    for i, b in enumerate(list(bodies)):
        row = csv_base_row(csv_elapsed_seconds, frame, "apoptotic_body", f"body_{getattr(b, 'id', i)}", "apoptotic_body")
        row.update({
            "source": b.source, "state": b.state, "marked": b.marked,
            "captured_by": b.captured_by.index if b.captured_by is not None else "",
            "dead": b.dead, "radius": b.radius, "age": b.age, "opacity": _opacity(b.obj),
        })
        row.update(_vec_fields(b.pos, ""))
        row.update(_vec_fields(b.vel, "v"))
        _csv_writer.writerow(row)
    for i, s in enumerate(scavengers):
        target_id = s.target.id if s.target is not None and hasattr(s.target, "id") else ""
        row = csv_base_row(csv_elapsed_seconds, frame, "scavenger", f"scavenger_{i}", "scavenger")
        row.update({"state": "active", "radius": s.radius, "engulfed_count": s.engulfed_count, "wrap_timer": s.wrap_timer, "target_body_id": target_id, "opacity": _opacity(s.obj)})
        row.update(_vec_fields(s.pos, ""))
        row.update(_vec_fields(s.vel, "v"))
        _csv_writer.writerow(row)
    for i, bl in enumerate(list(blebs)):
        row = csv_base_row(csv_elapsed_seconds, frame, "bleb", f"bleb_{i}", "bleb")
        row.update({"state": "detached" if bl.detached else "attached", "dead": bl.detached, "radius": bl.radius, "age": bl.age, "opacity": _opacity(bl.obj)})
        row.update(_vec_fields(bl.obj.pos, ""))
        _csv_writer.writerow(row)
    for i, p in enumerate(list(particles)):
        row = csv_base_row(csv_elapsed_seconds, frame, "enzyme_particle", f"particle_{i}", "particle")
        row.update({"state": "dead" if p.dead else "active", "dead": p.dead, "radius": p.radius, "life": p.life, "max_life": p.max_life, "opacity": _opacity(p.obj)})
        row.update(_vec_fields(p.pos, ""))
        row.update(_vec_fields(p.vel, "v"))
        _csv_writer.writerow(row)
    _csv_file.flush()

def write_csv_metadata():
    metadata = {
        "csv_run_id": CSV_RUN_ID,
        "csv_output_path": CSV_OUTPUT_PATH,
        "csv_metadata_path": CSV_METADATA_PATH,
        "simulation_name": "Apoptotic Cell Fragmentation and Cleanup - AI Controlled 3D Simulation",
        "script_type": "full_vpython_csv_logger",
        "run_seconds": CSV_RUN_SECONDS,
        "sample_hz": CSV_SAMPLE_HZ,
        "sample_interval": CSV_SAMPLE_INTERVAL,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "row_types": ["summary", "main_cell", "apoptotic_body", "scavenger", "bleb", "enzyme_particle"],
        "environment_variables": {
            "SIMULATION_CSV_OUTPUT_DIR": CSV_OUTPUT_DIR,
            "SIMULATION_CSV_RUN_ID": CSV_RUN_ID,
            "SIMULATION_CSV_RUN_SECONDS": CSV_RUN_SECONDS,
            "SIMULATION_CSV_SAMPLE_HZ": CSV_SAMPLE_HZ,
            "SIM_STATE_CSV_PATH": os.environ.get("SIM_STATE_CSV_PATH", ""),
        },
    }
    with open(CSV_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

write_csv_metadata()

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

reset_simulation()

csv_elapsed_seconds = 0.0
csv_sample_timer = CSV_SAMPLE_INTERVAL
csv_frame = 0

try:
    while csv_elapsed_seconds < CSV_RUN_SECONDS:
        rate(60)
        csv_frame += 1
        csv_elapsed_seconds += DT
        csv_sample_timer += DT

        if pending_reset:
            reset_simulation()

        update_hud()
        update_highlight()

        if paused:
            if csv_sample_timer >= CSV_SAMPLE_INTERVAL:
                csv_sample_timer = 0.0
                write_csv_snapshot(csv_elapsed_seconds, csv_frame)
            continue

        sim_time += DT

        if main_cell:
            main_cell.update(sim_time, DT)

        for b in blebs[:]:
            b.update(DT)

        for p in particles[:]:
            p.update(DT)

        if ai_enabled:
            ai_controller.update(DT)

        manual_control_update(DT)
        collide_bodies()

        for b in bodies[:]:
            b.update(DT)

        for s in scavengers:
            s.update(DT)

        if phase == "cleanup" and len(bodies) == 0 and sim_time > 22:
            phase = "complete"

        if csv_sample_timer >= CSV_SAMPLE_INTERVAL:
            csv_sample_timer = 0.0
            write_csv_snapshot(csv_elapsed_seconds, csv_frame)

    write_csv_snapshot(csv_elapsed_seconds, csv_frame)
    mode_label.text = "CSV recording complete: " + str(round(CSV_RUN_SECONDS, 1)) + "s saved to " + os.path.basename(CSV_OUTPUT_PATH)
finally:
    _csv_file.flush()
    _csv_file.close()
