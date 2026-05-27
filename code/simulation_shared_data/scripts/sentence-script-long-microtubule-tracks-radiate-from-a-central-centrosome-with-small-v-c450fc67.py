from vpython import *
import csv
import json
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

# ------------------------------------------------------------
# VPython CSV Logger: Vesicle Trafficking Along Microtubules
# ------------------------------------------------------------
# This version DOES render the VPython scene. It logs CSV rows while the
# visible simulation runs.
#
# Web-app environment variables:
#   SIMULATION_CSV_OUTPUT_DIR   directory for output files
#   SIMULATION_CSV_RUN_ID       run id used in filenames
#   SIMULATION_CSV_RUN_SECONDS  run duration, default 60 seconds
#   SIMULATION_CSV_SAMPLE_HZ    CSV sample rate, default 10 Hz
#
# Fallback:
#   SIM_STATE_CSV_PATH          direct CSV path if no output dir is provided
#
# Controls:
#   SPACE / P : pause or resume simulation
#   A         : toggle AI controller
#   R         : reset / new round
#   N         : select next vesicle
#   D         : detach selected vesicle
#   T         : attach selected vesicle to nearest track
#   S / LEFT / RIGHT : switch selected vesicle to another track
#   O         : put selected vesicle into orbit
#   F         : force selected vesicle outward toward fusion
#   C         : chaotic impulse to selected vesicle
#   UP / DOWN : move selected vesicle outward / inward if attached, impulse if detached
#   M         : manually change AI mode
#   H         : brief human override of AI
# ------------------------------------------------------------

# -----------------------------
# CSV run configuration
# -----------------------------

def _safe_float(value, default, minimum=None):
    try:
        result = float(value) if value not in (None, "") else default
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    return result


def _safe_text(value, default):
    value = (value or "").strip()
    return value if value else default


RUN_ID = _safe_text(os.getenv("SIMULATION_CSV_RUN_ID"), datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S"))
RUN_SECONDS = _safe_float(os.getenv("SIMULATION_CSV_RUN_SECONDS"), 60.0, minimum=0.0)
SAMPLE_HZ = _safe_float(os.getenv("SIMULATION_CSV_SAMPLE_HZ"), 10.0, minimum=0.1)
SAMPLE_INTERVAL = 1.0 / SAMPLE_HZ

_output_dir = os.getenv("SIMULATION_CSV_OUTPUT_DIR")
_fallback_csv = os.getenv("SIM_STATE_CSV_PATH")

if _output_dir:
    OUTPUT_DIR = Path(_output_dir).expanduser()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CSV_PATH = OUTPUT_DIR / f"{RUN_ID}_vesicle_trafficking_vpython_state.csv"
else:
    CSV_PATH = Path(_fallback_csv).expanduser() if _fallback_csv else Path(f"{RUN_ID}_vesicle_trafficking_vpython_state.csv")
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR = CSV_PATH.parent

METADATA_PATH = CSV_PATH.with_suffix(".metadata.json")

# -----------------------------
# Simulation constants
# -----------------------------

TRACK_COUNT = 30
VESICLE_COUNT = 22
MEMBRANE_RADIUS = 8.2
TRACK_LENGTH = 7.8
CENTROSOME_RADIUS = 0.42
VESICLE_RADIUS = 0.18
VESICLE_STEP_SIZE = 0.18
VESICLE_STEP_INTERVAL_MIN = 0.09
VESICLE_STEP_INTERVAL_MAX = 0.24
DETACHED_DRAG = 0.985
PARTICLE_LIFETIME = 2.0
STAGNATION_LIMIT = 11.5
COMPLETION_RESET_DELAY = 3.0
HUMAN_OVERRIDE_SECONDS = 4.0

PALE_BLUE = vector(0.72, 0.88, 1.0)
MEMBRANE_BLUE = vector(0.62, 0.84, 1.0)
MICROTUBULE_COLOR = vector(0.16, 0.62, 0.78)
MICROTUBULE_ALT = vector(0.25, 0.77, 0.82)
CENTROSOME_COLOR = vector(1.0, 0.76, 0.28)
MOTOR_COLOR = vector(0.18, 0.21, 0.25)
SELECT_COLOR = vector(1.0, 0.55, 0.08)

random.seed(os.getenv("SIMULATION_RANDOM_SEED") or None)

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def random_unit_vector():
    z = random.uniform(-1, 1)
    a = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), z, r * math.sin(a))


def fibonacci_sphere_direction(i, n):
    golden = math.pi * (3 - math.sqrt(5))
    y = 1 - (i / float(n - 1)) * 2
    radius = math.sqrt(max(0, 1 - y * y))
    theta = golden * i
    return safe_norm(vector(math.cos(theta) * radius, y, math.sin(theta) * radius))


def perpendicular_basis(direction):
    up = vector(0, 1, 0)
    if abs(dot(direction, up)) > 0.92:
        up = vector(1, 0, 0)
    side = safe_norm(cross(direction, up))
    other = safe_norm(cross(direction, side))
    return side, other


def random_cargo_color():
    palette = [
        vector(1.00, 0.38, 0.32),
        vector(1.00, 0.70, 0.25),
        vector(0.34, 0.82, 0.46),
        vector(0.33, 0.62, 1.00),
        vector(0.68, 0.45, 1.00),
        vector(1.00, 0.45, 0.76),
        vector(0.25, 0.88, 0.86),
    ]
    c = random.choice(palette)
    return vector(
        clamp(c.x + random.uniform(-0.06, 0.06), 0, 1),
        clamp(c.y + random.uniform(-0.06, 0.06), 0, 1),
        clamp(c.z + random.uniform(-0.06, 0.06), 0, 1),
    )


def mix_colors(a, b, bias=0.5):
    return vector(
        clamp(a.x * (1 - bias) + b.x * bias, 0, 1),
        clamp(a.y * (1 - bias) + b.y * bias, 0, 1),
        clamp(a.z * (1 - bias) + b.z * bias, 0, 1),
    )


def hsv_color(h, s=0.75, v=0.95):
    return color.hsv_to_rgb(vector(h % 1.0, s, v))


def vec_tuple(v):
    return (float(v.x), float(v.y), float(v.z))

# -----------------------------
# VPython scene
# -----------------------------

scene = canvas(
    title="3D Vesicle Trafficking Along Microtubules - VPython CSV Logger",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.range = 10.5
scene.forward = vector(-1.2, -0.65, -1.35)
scene.up = vector(0, 1, 0)

centrosome = sphere(pos=vector(0, 0, 0), radius=CENTROSOME_RADIUS, color=CENTROSOME_COLOR)
centrosome_halo = sphere(pos=vector(0, 0, 0), radius=CENTROSOME_RADIUS * 1.45, color=vector(1.0, 0.88, 0.38), opacity=0.18)
membrane = sphere(pos=vector(0, 0, 0), radius=MEMBRANE_RADIUS, color=MEMBRANE_BLUE, opacity=0.16)
membrane_inner_glow = sphere(pos=vector(0, 0, 0), radius=MEMBRANE_RADIUS * 0.985, color=vector(0.92, 0.98, 1.0), opacity=0.055)
wrap_band = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=MEMBRANE_RADIUS, thickness=0.025, color=vector(0.38, 0.72, 1.0), opacity=0.62)

centrosome_label = label(pos=vector(0, 0.95, 0), text="centrosome", height=13, color=vector(0.42, 0.28, 0.05), box=False, opacity=0)
membrane_label = label(pos=vector(0, MEMBRANE_RADIUS + 0.55, 0), text="target membrane sphere: fusion marks appear here", height=12, color=vector(0.10, 0.32, 0.52), box=False, opacity=0)
status_label = label(pos=vector(-8.8, 8.9, 0), text="", height=13, color=vector(0.08, 0.12, 0.16), box=True, border=8, opacity=0.28, background=vector(1, 1, 1))
help_label = label(pos=vector(7.7, -8.6, 0), text="Keys: A AI | SPACE pause | R reset | N select | D detach | T attach | S switch | O orbit | F fuse", height=10, color=vector(0.12, 0.18, 0.24), box=False, opacity=0)

# -----------------------------
# World objects
# -----------------------------

class Track:
    def __init__(self, idx, direction):
        self.idx = idx
        self.dir = safe_norm(direction)
        self.length = TRACK_LENGTH
        self.side, self.other = perpendicular_basis(self.dir)
        tint = MICROTUBULE_COLOR if idx % 2 == 0 else MICROTUBULE_ALT
        self.body = cylinder(pos=self.dir * (CENTROSOME_RADIUS * 0.75), axis=self.dir * self.length, radius=0.045, color=tint, opacity=0.82)
        self.plus_end = sphere(pos=self.dir * (CENTROSOME_RADIUS * 0.75 + self.length), radius=0.105, color=vector(0.03, 0.48, 0.62), opacity=0.78)

    def point(self, s):
        return self.dir * clamp(s, 0.15, self.length)


tracks = [Track(i, fibonacci_sphere_direction(i, TRACK_COUNT)) for i in range(TRACK_COUNT)]

class FusionEffect:
    def __init__(self, pos, col):
        n = safe_norm(pos)
        self.age = 0.0
        self.lifetime = 4.2
        self.patch = sphere(pos=n * (MEMBRANE_RADIUS + 0.025), radius=0.31, color=col, opacity=0.76)
        self.patch.scale = vector(1.0, 0.55, 1.0)
        self.ring = ring(pos=n * (MEMBRANE_RADIUS + 0.045), axis=n, radius=0.38, thickness=0.025, color=col, opacity=0.8)

    def update(self, dt):
        self.age += dt
        pulse = 0.5 + 0.5 * math.sin(self.age * 7.0)
        self.ring.radius = 0.38 + self.age * 0.12
        self.ring.opacity = max(0.0, 0.8 * (1 - self.age / self.lifetime))
        self.patch.opacity = clamp(0.48 + 0.22 * pulse, 0.25, 0.85)
        return self.age < self.lifetime

    def hide(self):
        self.patch.visible = False
        self.ring.visible = False


class Particle:
    def __init__(self, pos, vel, col, radius=0.045, lifetime=PARTICLE_LIFETIME):
        self.age = 0.0
        self.lifetime = lifetime
        self.vel = vel
        self.obj = sphere(pos=pos, radius=radius, color=col, opacity=0.72)

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.vel * dt
        self.vel *= 0.96
        self.obj.opacity = max(0, 0.72 * (1 - self.age / self.lifetime))
        return self.age < self.lifetime

    def hide(self):
        self.obj.visible = False


vesicles = []
particles = []
fusion_effects = []
fusion_count = 0
round_index = 0
selected_index = 0
paused = False

stats = {
    "detach_events": 0,
    "attach_events": 0,
    "track_switch_events": 0,
    "orbit_events": 0,
    "force_outward_events": 0,
    "collision_events": 0,
    "manual_events": 0,
    "reset_events": 0,
}

selection_ring = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=0.36, thickness=0.025, color=SELECT_COLOR, opacity=0.95, visible=False)
ai_cursor = sphere(pos=vector(0, 0, 0), radius=0.11, color=vector(1.0, 0.45, 0.16), opacity=0.45, visible=True)

class Vesicle:
    def __init__(self, idx):
        self.idx = idx
        self.radius = VESICLE_RADIUS * random.uniform(0.88, 1.18)
        self.cargo_color = random_cargo_color()
        self.state = "attached"
        self.track = random.randrange(len(tracks))
        self.s = random.uniform(0.65, 2.8)
        self.direction = 1
        self.speed_multiplier = random.uniform(0.85, 1.35)
        self.step_timer = random.uniform(0.02, 0.20)
        self.velocity = vector(0, 0, 0)
        self.spin_phase = random.uniform(0, 2 * math.pi)
        self.last_pos = tracks[self.track].point(self.s)
        self.intent = "born"
        self.fused_at = None
        self.collision_cooldown = 0.0
        self.orbit_axis = safe_norm(random_unit_vector())
        self.orbiting = False
        self.body = sphere(pos=self.compute_attached_pos(), radius=self.radius, color=self.cargo_color, opacity=0.97)
        self.shell = sphere(pos=self.body.pos, radius=self.radius * 1.16, color=vector(1, 1, 1), opacity=0.18)
        self.motor = cylinder(pos=self.body.pos, axis=vector(0, -0.1, 0), radius=0.024, color=MOTOR_COLOR, opacity=0.82)
        self.trail = curve(color=self.cargo_color, radius=0.014, retain=95)
        self.trail.append(pos=self.body.pos)

    def compute_attached_pos(self):
        t = tracks[self.track]
        lateral = t.side * (self.radius + 0.09)
        wiggle = t.other * (0.035 * math.sin(self.spin_phase))
        return t.point(self.s) + lateral + wiggle

    def set_track(self, new_track, preserve_s=True):
        old_pos = self.body.pos
        old_track = self.track
        self.track = int(new_track) % len(tracks)
        if preserve_s:
            self.s = clamp(dot(old_pos, tracks[self.track].dir), 0.4, TRACK_LENGTH)
        self.spin_phase += random.uniform(0.5, 2.0)
        if self.track != old_track:
            stats["track_switch_events"] += 1

    def attach_to_nearest_track(self):
        if self.state == "fused":
            return
        best = 0
        best_score = -999
        pdir = safe_norm(self.body.pos)
        for tr in tracks:
            score = dot(pdir, tr.dir)
            if score > best_score:
                best_score = score
                best = tr.idx
        self.state = "attached"
        self.orbiting = False
        self.set_track(best, preserve_s=True)
        self.s = clamp(dot(self.body.pos, tracks[self.track].dir), 0.5, TRACK_LENGTH - 0.05)
        self.direction = 1
        self.velocity = vector(0, 0, 0)
        self.motor.visible = True
        self.intent = "attached"
        stats["attach_events"] += 1

    def detach(self, impulse=None):
        if self.state != "attached":
            return
        self.state = "detached"
        self.motor.visible = False
        base = tracks[self.track].dir * (0.18 * self.direction)
        jitter = random_unit_vector() * random.uniform(0.08, 0.33)
        self.velocity = base + jitter if impulse is None else impulse
        self.intent = "detached"
        stats["detach_events"] += 1

    def switch_track(self, randomize=True, target_track=None):
        if self.state == "fused":
            return
        if target_track is None:
            if randomize:
                choices = list(range(len(tracks)))
                if self.track in choices:
                    choices.remove(self.track)
                target_track = random.choice(choices)
            else:
                pdir = safe_norm(self.body.pos)
                candidates = sorted(tracks, key=lambda tr: dot(pdir, tr.dir), reverse=True)
                target_track = candidates[min(3, len(candidates) - 1)].idx
        self.set_track(target_track, preserve_s=True)
        self.state = "attached"
        self.motor.visible = True
        self.orbiting = False
        self.intent = "switched"

    def make_orbit(self, strength=1.15):
        if self.state == "fused":
            return
        self.state = "detached"
        self.motor.visible = False
        r = self.body.pos
        axis = self.orbit_axis
        tangent = safe_norm(cross(axis, r), random_unit_vector())
        self.velocity = tangent * strength + safe_norm(r) * random.uniform(-0.05, 0.08)
        self.orbiting = True
        self.intent = "orbit"
        stats["orbit_events"] += 1

    def force_outward(self):
        if self.state == "fused":
            return
        if self.state == "detached":
            self.attach_to_nearest_track()
        self.direction = 1
        self.s = clamp(max(self.s, TRACK_LENGTH * 0.72), 0.7, TRACK_LENGTH - 0.15)
        self.speed_multiplier = max(self.speed_multiplier, 1.45)
        self.intent = "deliver"
        stats["force_outward_events"] += 1

    def fuse(self):
        if self.state == "fused":
            return
        self.state = "fused"
        self.fused_at = safe_norm(self.body.pos) * MEMBRANE_RADIUS
        self.body.visible = False
        self.shell.visible = False
        self.motor.visible = False
        self.intent = "fused"
        create_fusion(self.fused_at, self.cargo_color)

    def update_attached(self, dt):
        self.step_timer -= dt
        self.spin_phase += dt * 6.0
        if random.random() < 0.0008:
            self.direction *= -1
        if self.step_timer <= 0:
            self.s += self.direction * VESICLE_STEP_SIZE * self.speed_multiplier
            self.step_timer = random.uniform(VESICLE_STEP_INTERVAL_MIN, VESICLE_STEP_INTERVAL_MAX)
            if self.s < 0.48:
                self.s = 0.48
                self.direction = 1
            if random.random() < 0.008:
                self.detach()
                return
            if random.random() < 0.004:
                self.switch_track(randomize=True)
                return
        if self.s >= TRACK_LENGTH - 0.08 or mag(self.body.pos) >= MEMBRANE_RADIUS - self.radius * 1.2:
            self.fuse()
            return
        new_pos = self.compute_attached_pos()
        self.velocity = (new_pos - self.body.pos) / max(dt, 1e-4)
        self.body.pos = new_pos
        self.shell.pos = new_pos
        foot = tracks[self.track].point(self.s)
        self.motor.pos = foot
        self.motor.axis = self.body.pos - foot
        self.motor.visible = True

    def update_detached(self, dt):
        r = self.body.pos
        if self.orbiting:
            tangent = safe_norm(cross(self.orbit_axis, r), random_unit_vector())
            desired = tangent * 1.05
            self.velocity = self.velocity * 0.965 + desired * 0.035
            self.velocity += -safe_norm(r) * 0.015
        self.velocity *= DETACHED_DRAG
        self.velocity += random_unit_vector() * 0.006
        self.body.pos += self.velocity * dt * 5.2
        self.shell.pos = self.body.pos
        d = mag(self.body.pos)
        if d > MEMBRANE_RADIUS - self.radius:
            n = safe_norm(self.body.pos)
            self.body.pos = n * (MEMBRANE_RADIUS - self.radius)
            self.shell.pos = self.body.pos
            vn = dot(self.velocity, n)
            if vn > 0:
                self.velocity -= 1.75 * vn * n
                self.velocity += random_unit_vector() * 0.08
            if random.random() < 0.025:
                self.fuse()
                return
        if d < CENTROSOME_RADIUS + self.radius * 1.2:
            n = safe_norm(self.body.pos, random_unit_vector())
            self.body.pos = n * (CENTROSOME_RADIUS + self.radius * 1.25)
            self.shell.pos = self.body.pos
            self.velocity += n * 0.18
        if random.random() < 0.010:
            self.attach_to_nearest_track()

    def update(self, dt):
        if self.state == "fused":
            return
        self.collision_cooldown = max(0, self.collision_cooldown - dt)
        self.last_pos = vector(self.body.pos.x, self.body.pos.y, self.body.pos.z)
        if self.state == "attached":
            self.update_attached(dt)
        elif self.state == "detached":
            self.update_detached(dt)
        if self.state != "fused":
            self.body.rotate(angle=dt * 1.8, axis=vector(0.7, 1.0, 0.25), origin=self.body.pos)
            self.shell.pos = self.body.pos
            if random.random() < 0.70:
                self.trail.append(pos=self.body.pos)

    def hide(self):
        self.body.visible = False
        self.shell.visible = False
        self.motor.visible = False
        self.trail.visible = False

# -----------------------------
# Dynamic functions
# -----------------------------

def create_fusion(pos, col):
    global fusion_count
    fusion_count += 1
    fusion_effects.append(FusionEffect(pos, col))
    n = safe_norm(pos)
    for _ in range(18):
        tang = safe_norm(cross(n, random_unit_vector()), random_unit_vector())
        vel = (n * random.uniform(0.06, 0.32) + tang * random.uniform(-0.42, 0.42)) * random.uniform(1.5, 3.2)
        particles.append(Particle(n * (MEMBRANE_RADIUS + 0.04), vel, col, radius=random.uniform(0.025, 0.055), lifetime=random.uniform(1.0, 2.5)))


def clear_dynamic_objects():
    global vesicles, particles, fusion_effects
    for v in vesicles:
        v.hide()
    for p in particles:
        p.hide()
    for f in fusion_effects:
        f.hide()
    vesicles = []
    particles = []
    fusion_effects = []


def create_vesicles(count=VESICLE_COUNT):
    global vesicles
    vesicles = [Vesicle(i) for i in range(count)]


def reset_simulation(reason="new round"):
    global fusion_count, selected_index, round_index
    clear_dynamic_objects()
    fusion_count = 0
    selected_index = 0
    round_index += 1
    stats["reset_events"] += 1
    create_vesicles(VESICLE_COUNT)
    membrane.color = MEMBRANE_BLUE
    wrap_band.color = vector(0.38, 0.72, 1.0)
    wrap_band.axis = random_unit_vector()
    ai_cursor.visible = True
    for _ in range(12):
        particles.append(Particle(random_unit_vector() * random.uniform(0.3, 1.1), random_unit_vector() * random.uniform(0.35, 0.95), vector(0.8, 0.92, 1.0), radius=random.uniform(0.025, 0.045), lifetime=random.uniform(0.8, 1.5)))
    if "ai" in globals():
        ai.after_reset(reason)


def handle_vesicle_collisions():
    for i in range(len(vesicles)):
        a = vesicles[i]
        if a.state == "fused":
            continue
        for j in range(i + 1, len(vesicles)):
            b = vesicles[j]
            if b.state == "fused":
                continue
            delta = b.body.pos - a.body.pos
            d = mag(delta)
            min_d = a.radius + b.radius
            if 1e-6 < d < min_d:
                stats["collision_events"] += 1
                n = delta / d
                overlap = min_d - d
                if a.state == "detached":
                    a.body.pos -= n * overlap * 0.5
                    a.shell.pos = a.body.pos
                if b.state == "detached":
                    b.body.pos += n * overlap * 0.5
                    b.shell.pos = b.body.pos
                if a.collision_cooldown <= 0 and b.collision_cooldown <= 0:
                    mixed = mix_colors(a.cargo_color, b.cargo_color, 0.5)
                    a.cargo_color = mix_colors(a.cargo_color, mixed, 0.35)
                    b.cargo_color = mix_colors(b.cargo_color, mixed, 0.35)
                    a.body.color = a.cargo_color
                    b.body.color = b.cargo_color
                    a.trail.color = a.cargo_color
                    b.trail.color = b.cargo_color
                    a.collision_cooldown = 0.45
                    b.collision_cooldown = 0.45
                    contact = (a.body.pos + b.body.pos) * 0.5
                    for _ in range(4):
                        particles.append(Particle(contact, random_unit_vector() * random.uniform(0.12, 0.45), mixed, radius=0.026, lifetime=0.75))
                if a.state == "detached":
                    va = dot(a.velocity, n)
                    if va > 0:
                        a.velocity -= 1.15 * va * n
                if b.state == "detached":
                    vb = dot(b.velocity, -n)
                    if vb > 0:
                        b.velocity += 1.15 * vb * n
                if (a.state == "attached" or b.state == "attached") and random.random() < 0.10:
                    if a.state == "attached":
                        a.detach(impulse=-n * random.uniform(0.15, 0.35))
                    if b.state == "attached":
                        b.detach(impulse=n * random.uniform(0.15, 0.35))

# -----------------------------
# AI controller
# -----------------------------

class AIController:
    MODES = ["DELIVER", "CURIOUS_SWITCH", "ORBIT_DANCE", "PAINT_MEMBRANE", "ORGANIZE", "CHAOS", "CAREFUL", "DIP_AND_RETURN", "RESETTING"]

    def __init__(self):
        self.enabled = True
        self.mode = "DELIVER"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 9.0
        self.override_timer = 0.0
        self.reset_timer = 0.0
        self.last_fusion_count = 0
        self.last_active_count = VESICLE_COUNT
        self.last_motion_score = 0.0
        self.stagnant_timer = 0.0
        self.completion_timer = 0.0
        self.behavior_bias = random.random()
        self.mode_color = vector(1.0, 0.45, 0.16)
        self.round_started = time.time()
        self.last_state = {}

    def after_reset(self, reason):
        self.mode = random.choice(["DELIVER", "PAINT_MEMBRANE", "ORGANIZE", "CURIOUS_SWITCH"])
        self.previous_mode = None
        self.mode_timer = 0
        self.mode_duration = random.uniform(7.0, 13.0)
        self.reset_timer = 0
        self.completion_timer = 0
        self.stagnant_timer = 0
        self.last_fusion_count = 0
        self.last_active_count = len(vesicles)
        self.behavior_bias = random.random()
        self.round_started = time.time()

    def human_override(self):
        self.override_timer = HUMAN_OVERRIDE_SECONDS

    def active_vesicles(self):
        return [v for v in vesicles if v.state != "fused"]

    def estimate_clustering(self, active):
        if len(active) < 2:
            return 0.0
        close = 0
        checks = 0
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                checks += 1
                if mag(active[i].body.pos - active[j].body.pos) < 0.75:
                    close += 1
        return close / max(1, checks)

    def read_state(self):
        active = self.active_vesicles()
        attached = [v for v in active if v.state == "attached"]
        detached = [v for v in active if v.state == "detached"]
        fused = [v for v in vesicles if v.state == "fused"]
        avg_s = sum(v.s for v in attached) / max(1, len(attached))
        avg_radius = sum(mag(v.body.pos) for v in active) / max(1, len(active))
        motion = sum(mag(v.body.pos - v.last_pos) for v in active)
        near_membrane = sum(1 for v in active if mag(v.body.pos) > MEMBRANE_RADIUS * 0.78)
        clustered = self.estimate_clustering(active)
        state = {
            "active_count": len(active),
            "attached_count": len(attached),
            "detached_count": len(detached),
            "fused_count": len(fused),
            "fusion_count": fusion_count,
            "avg_s": avg_s,
            "avg_radius": avg_radius,
            "motion_score": motion,
            "near_membrane": near_membrane,
            "clustered": clustered,
            "round_index": round_index,
            "mode": self.mode,
        }
        self.last_state = state
        return state

    def detect_stagnation_or_completion(self, state, dt):
        changed = (
            state["fusion_count"] != self.last_fusion_count
            or state["active_count"] != self.last_active_count
            or abs(state["motion_score"] - self.last_motion_score) > 0.025
            or state["motion_score"] > 0.07
        )
        self.stagnant_timer = 0.0 if changed else self.stagnant_timer + dt
        complete = state["active_count"] == 0 or state["fused_count"] >= len(vesicles)
        almost_complete = state["active_count"] <= 2 and state["fusion_count"] > VESICLE_COUNT * 0.65
        self.completion_timer = self.completion_timer + dt if complete or almost_complete else 0.0
        self.last_fusion_count = state["fusion_count"]
        self.last_active_count = state["active_count"]
        self.last_motion_score = state["motion_score"]
        return complete, almost_complete, self.stagnant_timer > STAGNATION_LIMIT

    def choose_next_mode(self, state, reason="timer"):
        old = self.mode
        candidates = ["DELIVER", "CURIOUS_SWITCH", "ORBIT_DANCE", "PAINT_MEMBRANE", "ORGANIZE", "CHAOS", "CAREFUL", "DIP_AND_RETURN"]
        if reason == "stagnant":
            candidates = ["CHAOS", "ORBIT_DANCE", "CURIOUS_SWITCH", "DELIVER"]
        elif state.get("detached_count", 0) > state.get("attached_count", 0) + 5:
            candidates = ["CAREFUL", "ORGANIZE", "DELIVER"]
        elif state.get("near_membrane", 0) > max(4, state.get("active_count", 0) * 0.45):
            candidates = ["PAINT_MEMBRANE", "DIP_AND_RETURN", "DELIVER"]
        elif state.get("clustered", 0) > 0.12:
            candidates = ["CHAOS", "ORBIT_DANCE", "CURIOUS_SWITCH"]
        elif state.get("fusion_count", 0) < 3 and time.time() - self.round_started > 16:
            candidates = ["DELIVER", "PAINT_MEMBRANE", "CHAOS"]
        if old in candidates and len(candidates) > 1:
            candidates.remove(old)
        self.previous_mode = old
        self.mode = random.choice(candidates)
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(6.0, 15.0)
        self.mode_color = hsv_color(random.random(), 0.72, 0.96)
        ai_cursor.color = self.mode_color

    def choose_vesicle(self, prefer=None):
        active = self.active_vesicles()
        if not active:
            return None
        if prefer == "detached":
            pool = [v for v in active if v.state == "detached"]
            return random.choice(pool) if pool else random.choice(active)
        if prefer == "attached":
            pool = [v for v in active if v.state == "attached"]
            return random.choice(pool) if pool else random.choice(active)
        if prefer == "inner":
            return min(active, key=lambda v: mag(v.body.pos))
        if prefer == "outer":
            return max(active, key=lambda v: mag(v.body.pos))
        return random.choice(active)

    def update(self, dt):
        if not self.enabled:
            return
        self.override_timer = max(0.0, self.override_timer - dt)
        state = self.read_state()
        complete, almost_complete, stagnant = self.detect_stagnation_or_completion(state, dt)
        if complete or (almost_complete and self.completion_timer > COMPLETION_RESET_DELAY):
            self.mode = "RESETTING"
            self.reset_timer += dt
            if self.reset_timer > COMPLETION_RESET_DELAY:
                reset_simulation("completion loop")
            return
        if stagnant:
            self.choose_next_mode(state, reason="stagnant")
            self.stagnant_timer = 0.0
        self.mode_timer += dt
        if self.mode_timer > self.mode_duration:
            self.choose_next_mode(state, reason="timer")
        if self.override_timer > 0:
            return
        if self.mode == "DELIVER":
            self.behavior_deliver(state, dt)
        elif self.mode == "CURIOUS_SWITCH":
            self.behavior_curious_switch(state, dt)
        elif self.mode == "ORBIT_DANCE":
            self.behavior_orbit_dance(state, dt)
        elif self.mode == "PAINT_MEMBRANE":
            self.behavior_paint_membrane(state, dt)
        elif self.mode == "ORGANIZE":
            self.behavior_organize(state, dt)
        elif self.mode == "CHAOS":
            self.behavior_chaos(state, dt)
        elif self.mode == "CAREFUL":
            self.behavior_careful(state, dt)
        elif self.mode == "DIP_AND_RETURN":
            self.behavior_dip_and_return(state, dt)

    def behavior_deliver(self, state, dt):
        if random.random() < 0.16:
            v = self.choose_vesicle("detached")
            if v:
                v.attach_to_nearest_track(); v.direction = 1; v.speed_multiplier = random.uniform(1.1, 1.85)
        if random.random() < 0.08:
            v = self.choose_vesicle("inner")
            if v:
                v.direction = 1; v.speed_multiplier = max(v.speed_multiplier, 1.35)
        if random.random() < 0.015:
            v = self.choose_vesicle("attached")
            if v:
                v.force_outward()

    def behavior_curious_switch(self, state, dt):
        if random.random() < 0.10:
            v = self.choose_vesicle("attached")
            if v:
                v.switch_track(target_track=random.randrange(len(tracks)))
        if random.random() < 0.035:
            v = self.choose_vesicle()
            if v and v.state == "attached":
                v.detach()
        if random.random() < 0.045:
            v = self.choose_vesicle()
            if v:
                particles.append(Particle(v.body.pos, random_unit_vector() * 0.35, v.cargo_color, radius=0.028, lifetime=0.9))

    def behavior_orbit_dance(self, state, dt):
        if random.random() < 0.11:
            v = self.choose_vesicle()
            if v:
                v.make_orbit(strength=random.uniform(0.8, 1.45))
        wrap_band.axis = safe_norm(wrap_band.axis * 0.99 + random_unit_vector() * 0.01)
        wrap_band.color = mix_colors(wrap_band.color, self.mode_color, 0.015)

    def behavior_paint_membrane(self, state, dt):
        if random.random() < 0.13:
            v = self.choose_vesicle()
            if v:
                v.force_outward()
                if random.random() < 0.25:
                    v.cargo_color = hsv_color((time.time() * 0.07 + v.idx * 0.09) % 1, 0.78, 0.98)
                    v.body.color = v.cargo_color
                    v.trail.color = v.cargo_color
        if random.random() < 0.035:
            v = self.choose_vesicle("outer")
            if v and mag(v.body.pos) > MEMBRANE_RADIUS * 0.86:
                v.fuse()

    def behavior_organize(self, state, dt):
        active = self.active_vesicles()
        if not active:
            return
        if random.random() < 0.16:
            v = self.choose_vesicle("detached")
            if v:
                v.attach_to_nearest_track()
        if random.random() < 0.08:
            v = self.choose_vesicle("attached")
            if v:
                target_track = (v.idx * 3 + round_index) % len(tracks)
                v.switch_track(target_track=target_track)
                target_s = 1.0 + (v.idx % 7) * 0.75
                v.s = clamp(v.s * 0.85 + target_s * 0.15, 0.6, TRACK_LENGTH - 0.5)
                v.direction = 1 if random.random() < 0.7 else -1
                v.speed_multiplier = 0.8

    def behavior_chaos(self, state, dt):
        if random.random() < 0.14:
            v = self.choose_vesicle()
            if v:
                impulse = random_unit_vector() * random.uniform(0.28, 0.85)
                if v.state == "attached":
                    v.detach(impulse=impulse)
                else:
                    v.velocity += impulse
                v.cargo_color = mix_colors(v.cargo_color, hsv_color(random.random(), 0.9, 1.0), 0.35)
                v.body.color = v.cargo_color
                v.trail.color = v.cargo_color
        if random.random() < 0.06:
            v = self.choose_vesicle()
            if v:
                particles.append(Particle(v.body.pos, random_unit_vector() * 0.9, v.cargo_color, radius=0.035, lifetime=1.1))

    def behavior_careful(self, state, dt):
        for v in self.active_vesicles():
            v.speed_multiplier = max(0.62, v.speed_multiplier * 0.995)
        if random.random() < 0.12:
            v = self.choose_vesicle("detached")
            if v:
                v.attach_to_nearest_track(); v.speed_multiplier = 0.75
        if state.get("clustered", 0) > 0.08 and random.random() < 0.12:
            v = self.choose_vesicle("attached")
            if v:
                v.switch_track(randomize=True)

    def behavior_dip_and_return(self, state, dt):
        if random.random() < 0.12:
            v = self.choose_vesicle("attached")
            if v:
                if v.s > TRACK_LENGTH * 0.45 and random.random() < 0.55:
                    v.direction = -1; v.speed_multiplier = random.uniform(1.0, 1.45)
                else:
                    v.direction = 1; v.speed_multiplier = random.uniform(1.15, 1.75)
        if random.random() < 0.025:
            v = self.choose_vesicle("outer")
            if v:
                v.direction = 1

ai = AIController()

# -----------------------------
# Keyboard controls
# -----------------------------

def selected_vesicle():
    global selected_index
    if not vesicles:
        return None
    selected_index %= len(vesicles)
    return vesicles[selected_index]


def manual_override():
    stats["manual_events"] += 1
    ai.human_override()


def on_keydown(evt):
    global paused, selected_index
    k = evt.key.lower()
    if k in [" ", "space", "p"]:
        paused = not paused
        return
    if k == "a":
        ai.enabled = not ai.enabled
        return
    if k == "r":
        manual_override(); reset_simulation("manual"); return
    if k == "m":
        manual_override(); ai.choose_next_mode(ai.read_state(), reason="manual"); return
    if k == "h":
        manual_override(); return
    v = selected_vesicle()
    if v is None:
        return
    if k == "n":
        selected_index = (selected_index + 1) % len(vesicles); manual_override()
    elif k == "d":
        if v.state == "attached":
            v.detach()
        manual_override()
    elif k == "t":
        v.attach_to_nearest_track(); manual_override()
    elif k in ["s", "left", "right"]:
        step = 1 if k != "left" else -1
        v.switch_track(target_track=(v.track + step) % len(tracks)); manual_override()
    elif k == "o":
        v.make_orbit(strength=1.4); manual_override()
    elif k == "f":
        v.force_outward(); manual_override()
    elif k == "c":
        if v.state == "attached":
            v.detach(impulse=random_unit_vector() * 0.7)
        else:
            v.velocity += random_unit_vector() * 0.7
        manual_override()
    elif k == "up":
        if v.state == "attached":
            v.s = clamp(v.s + 0.55, 0.5, TRACK_LENGTH - 0.1); v.direction = 1
        else:
            v.velocity += safe_norm(v.body.pos) * 0.35
        manual_override()
    elif k == "down":
        if v.state == "attached":
            v.s = clamp(v.s - 0.55, 0.5, TRACK_LENGTH - 0.1); v.direction = -1
        else:
            v.velocity -= safe_norm(v.body.pos) * 0.35
        manual_override()

scene.bind("keydown", on_keydown)

# -----------------------------
# Visual updates
# -----------------------------

def update_particles(dt):
    global particles
    alive = []
    for p in particles:
        if p.update(dt):
            alive.append(p)
        else:
            p.hide()
    particles = alive


def update_fusion_effects(dt):
    global fusion_effects
    alive = []
    for f in fusion_effects:
        if f.update(dt):
            alive.append(f)
        else:
            f.ring.visible = False
            f.patch.opacity = 0.62
            alive.append(f)
    fusion_effects = alive


def update_selection_visual():
    v = selected_vesicle()
    if v and v.state != "fused":
        selection_ring.visible = True
        selection_ring.pos = v.body.pos
        selection_ring.radius = v.radius * 1.95
        selection_ring.axis = safe_norm(scene.forward, vector(0, 1, 0))
        selection_ring.color = SELECT_COLOR if ai.override_timer > 0 else ai.mode_color
    else:
        selection_ring.visible = False


def update_ai_cursor(dt):
    active = [v for v in vesicles if v.state != "fused"]
    if active:
        if ai.mode == "DELIVER":
            target = max(active, key=lambda v: v.s if v.state == "attached" else mag(v.body.pos)).body.pos
        elif ai.mode == "ORBIT_DANCE":
            phase = time.time() * 0.9
            target = vector(math.cos(phase), 0.35 * math.sin(phase * 0.7), math.sin(phase)) * 3.0
        elif ai.mode == "PAINT_MEMBRANE":
            phase = time.time() * 0.22
            target = safe_norm(vector(math.cos(phase * 2.1), math.sin(phase * 1.7), math.sin(phase * 2.1))) * (MEMBRANE_RADIUS + 0.25)
        else:
            target = random.choice(active).body.pos
        ai_cursor.pos = ai_cursor.pos * 0.94 + target * 0.06
        ai_cursor.visible = ai.enabled
    else:
        ai_cursor.visible = False


def update_membrane_visual(dt):
    pulse = 0.5 + 0.5 * math.sin(time.time() * 1.4)
    membrane.opacity = 0.14 + 0.035 * pulse
    membrane.color = mix_colors(MEMBRANE_BLUE, ai.mode_color if ai.enabled else PALE_BLUE, 0.06)
    wrap_band.rotate(angle=dt * 0.10, axis=safe_norm(wrap_band.axis), origin=vector(0, 0, 0))
    wrap_band.opacity = 0.45 + 0.18 * pulse


def update_status_label(elapsed=0.0, logger_done=False):
    state = ai.last_state if ai.last_state else ai.read_state()
    csv_text = f"CSV {CSV_PATH.name} | {elapsed:.1f}/{RUN_SECONDS:.1f}s" if RUN_SECONDS > 0 else f"CSV {CSV_PATH.name} | {elapsed:.1f}s"
    if logger_done:
        csv_text += " | complete"
    status_label.text = (
        f"Round {round_index} | AI {'ON' if ai.enabled else 'OFF'} | Mode: {ai.mode}"
        f"{' | PAUSED' if paused else ''}"
        f"{' | Human override' if ai.override_timer > 0 else ''}\n"
        f"Vesicles active {state.get('active_count', 0)} | attached {state.get('attached_count', 0)} | "
        f"detached {state.get('detached_count', 0)} | fused {state.get('fused_count', 0)} | "
        f"fusion marks {fusion_count}\n"
        f"{csv_text}"
    )
    status_label.pos = scene.center + vector(-8.6, 8.85, 0)

# -----------------------------
# CSV logging
# -----------------------------

CSV_FIELDS = [
    "run_id", "elapsed_seconds", "wall_time_utc", "step_index", "round_index", "paused",
    "ai_enabled", "ai_mode", "ai_previous_mode", "ai_mode_timer", "ai_mode_duration", "ai_stagnant_timer", "ai_completion_timer", "ai_override_timer",
    "active_count", "attached_count", "detached_count", "fused_count", "orbiting_count", "fusion_count", "fusion_effect_count", "particle_count",
    "avg_track_position_s", "avg_radius_from_centrosome", "mean_speed", "max_speed", "near_membrane_count", "inner_count", "outer_count", "clustered_score", "motion_score",
    "detach_events", "attach_events", "track_switch_events", "orbit_events", "force_outward_events", "collision_events", "manual_events", "reset_events",
    "selected_vesicle_id", "selected_state", "selected_track", "selected_s", "selected_speed_multiplier", "selected_direction", "selected_radius_from_centrosome",
    "selected_x", "selected_y", "selected_z", "selected_vx", "selected_vy", "selected_vz", "selected_intent",
]

class CSVLogger:
    def __init__(self):
        self.path = CSV_PATH
        self.metadata_path = METADATA_PATH
        self.interval = SAMPLE_INTERVAL
        self.next_sample = 0.0
        self.row_count = 0
        self.closed = False
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=CSV_FIELDS, extrasaction="ignore")
        self.writer.writeheader()
        self.file.flush()

    def should_stop(self, elapsed):
        return RUN_SECONDS > 0 and elapsed >= RUN_SECONDS

    def log(self, elapsed, step_index, dt):
        if self.closed or elapsed + 1e-9 < self.next_sample:
            return
        row = self.snapshot(elapsed, step_index, dt)
        self.writer.writerow(row)
        self.row_count += 1
        self.next_sample += self.interval
        if self.row_count % 20 == 0:
            self.file.flush()

    def snapshot(self, elapsed, step_index, dt):
        state = ai.last_state if ai.last_state else ai.read_state()
        active = [v for v in vesicles if v.state != "fused"]
        orbiting = [v for v in active if v.orbiting]
        speeds = [mag(v.velocity) for v in active]
        selected = selected_vesicle()
        if selected and selected.state != "fused":
            sx, sy, sz = vec_tuple(selected.body.pos)
            svx, svy, svz = vec_tuple(selected.velocity)
            selected_radius = mag(selected.body.pos)
            selected_state = selected.state
            selected_track = selected.track
            selected_s = selected.s
            selected_speed_multiplier = selected.speed_multiplier
            selected_direction = selected.direction
            selected_intent = selected.intent
            selected_id = selected.idx
        else:
            sx = sy = sz = svx = svy = svz = selected_radius = selected_s = selected_speed_multiplier = ""
            selected_state = selected_track = selected_direction = selected_intent = selected_id = ""
        return {
            "run_id": RUN_ID,
            "elapsed_seconds": round(elapsed, 4),
            "wall_time_utc": datetime.now(timezone.utc).isoformat(),
            "step_index": step_index,
            "round_index": round_index,
            "paused": int(paused),
            "ai_enabled": int(ai.enabled),
            "ai_mode": ai.mode,
            "ai_previous_mode": ai.previous_mode or "",
            "ai_mode_timer": round(ai.mode_timer, 4),
            "ai_mode_duration": round(ai.mode_duration, 4),
            "ai_stagnant_timer": round(ai.stagnant_timer, 4),
            "ai_completion_timer": round(ai.completion_timer, 4),
            "ai_override_timer": round(ai.override_timer, 4),
            "active_count": state.get("active_count", 0),
            "attached_count": state.get("attached_count", 0),
            "detached_count": state.get("detached_count", 0),
            "fused_count": state.get("fused_count", 0),
            "orbiting_count": len(orbiting),
            "fusion_count": fusion_count,
            "fusion_effect_count": len(fusion_effects),
            "particle_count": len(particles),
            "avg_track_position_s": round(state.get("avg_s", 0), 6),
            "avg_radius_from_centrosome": round(state.get("avg_radius", 0), 6),
            "mean_speed": round(sum(speeds) / max(1, len(speeds)), 6),
            "max_speed": round(max(speeds) if speeds else 0, 6),
            "near_membrane_count": state.get("near_membrane", 0),
            "inner_count": sum(1 for v in active if mag(v.body.pos) < MEMBRANE_RADIUS * 0.35),
            "outer_count": sum(1 for v in active if mag(v.body.pos) > MEMBRANE_RADIUS * 0.70),
            "clustered_score": round(state.get("clustered", 0), 6),
            "motion_score": round(state.get("motion_score", 0), 6),
            "detach_events": stats["detach_events"],
            "attach_events": stats["attach_events"],
            "track_switch_events": stats["track_switch_events"],
            "orbit_events": stats["orbit_events"],
            "force_outward_events": stats["force_outward_events"],
            "collision_events": stats["collision_events"],
            "manual_events": stats["manual_events"],
            "reset_events": stats["reset_events"],
            "selected_vesicle_id": selected_id,
            "selected_state": selected_state,
            "selected_track": selected_track,
            "selected_s": round(selected_s, 6) if selected_s != "" else "",
            "selected_speed_multiplier": round(selected_speed_multiplier, 6) if selected_speed_multiplier != "" else "",
            "selected_direction": selected_direction,
            "selected_radius_from_centrosome": round(selected_radius, 6) if selected_radius != "" else "",
            "selected_x": round(sx, 6) if sx != "" else "",
            "selected_y": round(sy, 6) if sy != "" else "",
            "selected_z": round(sz, 6) if sz != "" else "",
            "selected_vx": round(svx, 6) if svx != "" else "",
            "selected_vy": round(svy, 6) if svy != "" else "",
            "selected_vz": round(svz, 6) if svz != "" else "",
            "selected_intent": selected_intent,
        }

    def close(self, final_elapsed):
        if self.closed:
            return
        self.file.flush()
        self.file.close()
        metadata = {
            "script": "vesicle_trafficking_vpython_csv_logger.py",
            "source_simulation": "Vesicle Trafficking Along Microtubules",
            "vpython_enabled": True,
            "run_id": RUN_ID,
            "csv_path": str(CSV_PATH),
            "metadata_path": str(METADATA_PATH),
            "run_seconds_requested": RUN_SECONDS,
            "sample_hz": SAMPLE_HZ,
            "row_count": self.row_count,
            "final_elapsed_seconds": round(final_elapsed, 4),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment_variables": {
                "SIMULATION_CSV_OUTPUT_DIR": os.getenv("SIMULATION_CSV_OUTPUT_DIR"),
                "SIMULATION_CSV_RUN_ID": os.getenv("SIMULATION_CSV_RUN_ID"),
                "SIMULATION_CSV_RUN_SECONDS": os.getenv("SIMULATION_CSV_RUN_SECONDS"),
                "SIMULATION_CSV_SAMPLE_HZ": os.getenv("SIMULATION_CSV_SAMPLE_HZ"),
                "SIM_STATE_CSV_PATH": os.getenv("SIM_STATE_CSV_PATH"),
            },
            "logged_fields": CSV_FIELDS,
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self.closed = True

# -----------------------------
# Initialize and run visibly
# -----------------------------

reset_simulation("initial")
csv_logger = CSVLogger()

last_time = time.time()
start_time = last_time
step_index = 0
logger_done = False

try:
    while True:
        rate(60)
        now = time.time()
        dt = clamp(now - last_time, 0.001, 0.05)
        last_time = now
        elapsed = now - start_time

        if paused:
            update_selection_visual()
            update_status_label(elapsed, logger_done=logger_done)
            csv_logger.log(elapsed, step_index, dt)
            if csv_logger.should_stop(elapsed):
                logger_done = True
                break
            step_index += 1
            continue

        ai.update(dt)
        for v in vesicles:
            v.update(dt)
        handle_vesicle_collisions()
        update_particles(dt)
        update_fusion_effects(dt)
        update_selection_visual()
        update_ai_cursor(dt)
        update_membrane_visual(dt)
        update_status_label(elapsed, logger_done=logger_done)
        csv_logger.log(elapsed, step_index, dt)

        if csv_logger.should_stop(elapsed):
            logger_done = True
            break
        step_index += 1
finally:
    final_elapsed = time.time() - start_time
    csv_logger.close(final_elapsed)
    update_status_label(final_elapsed, logger_done=True)
    scene.caption = f"\nCSV log written: {CSV_PATH}\nMetadata written: {METADATA_PATH}\n"
