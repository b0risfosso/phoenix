from vpython import *
import random
import math
import time
import csv
import os
from datetime import datetime

# Immune Cell Chasing a Bacterium — CSV storage version
# Web-app-compatible CSV recorder.
#
# Environment variables supported:
#   SIMULATION_CSV_OUTPUT_DIR
#   SIMULATION_CSV_RUN_ID
#   SIMULATION_CSV_RUN_SECONDS
# Fallback:
#   SIM_STATE_CSV_PATH

scene = canvas(
    title="Immune Cell Chasing a Bacterium - CSV Storage Version",
    width=1200,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 1.2, 0),
)
scene.forward = vector(-0.65, -0.34, -0.68)
scene.range = 10.5
scene.autoscale = False

# ----------------------------- CSV settings -----------------------------

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(
        _csv_output_dir,
        f"{_csv_run_id}-immune-cell-bacterium-state-log.csv"
    )
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "immune_cell_bacterium_state_log.csv")
    )

csv_run_id = _csv_run_id

CSV_FIELDNAMES = [
    "run_id", "sample_index", "time_seconds", "row_type",
    "round_id", "phase", "phase_progress", "ai_enabled", "ai_mode",
    "ai_mode_timer", "ai_stagnation_timer", "manual_override_timer",
    "object_id", "object_name", "state",
    "pos_x", "pos_y", "pos_z",
    "vel_x", "vel_y", "vel_z",
    "radius", "length", "opacity",
    "orientation_x", "orientation_y", "orientation_z",
    "target_dir_x", "target_dir_y", "target_dir_z",
    "wrap_factor", "digest_pulse", "chase_factor", "ritual_factor",
    "alive", "captured", "visible",
    "age", "life", "marker_count", "digestion_particle_count", "extra"
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES)
_csv_writer.writeheader()
_csv_sample_index = 0
_csv_next_sample_time = 0.0
_csv_closed = False

# ----------------------------- helpers -----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)

def lerp_vec(a, b, f):
    return a * (1.0 - f) + b * f

def rand_range(a, b):
    return a + random.random() * (b - a)

def random_unit_xz():
    a = random.random() * 2.0 * math.pi
    return vector(math.cos(a), 0, math.sin(a))

def random_unit_3d():
    z = rand_range(-1, 1)
    a = random.random() * 2.0 * math.pi
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), z, r * math.sin(a))

def fibonacci_sphere_points(n):
    pts = []
    phi = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (i / float(n - 1)) * 2.0 if n > 1 else 0
        radius = math.sqrt(max(0, 1.0 - y * y))
        theta = phi * i
        pts.append(vector(math.cos(theta) * radius, y, math.sin(theta) * radius))
    return pts

def vec_fields(prefix, v):
    return {
        f"{prefix}_x": getattr(v, "x", ""),
        f"{prefix}_y": getattr(v, "y", ""),
        f"{prefix}_z": getattr(v, "z", ""),
    }

# ----------------------------- environment -----------------------------

floor = box(
    pos=vector(0, -0.08, 0),
    size=vector(20, 0.04, 20),
    color=vector(0.90, 0.96, 0.95),
    opacity=0.55,
)

grid_lines = []
for x in range(-10, 11):
    grid_lines.append(curve(
        pos=[vector(x, -0.055, -10), vector(x, -0.055, 10)],
        color=vector(0.78, 0.88, 0.88),
        radius=0.008,
    ))
for z in range(-10, 11):
    grid_lines.append(curve(
        pos=[vector(-10, -0.054, z), vector(10, -0.054, z)],
        color=vector(0.78, 0.88, 0.88),
        radius=0.008,
    ))

arena_ring = ring(
    pos=vector(0, -0.02, 0),
    axis=vector(0, 1, 0),
    radius=9.2,
    thickness=0.035,
    color=vector(0.55, 0.73, 0.78),
    opacity=0.45,
)

scene.caption = "CSV storage run: immune cell chases, attaches, engulfs, digests, and resets while state snapshots are recorded.\n"

# ----------------------------- objects -----------------------------

class Bacterium:
    def __init__(self, pos):
        self.length = 1.45
        self.radius = 0.34
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.orientation = safe_norm(random_unit_xz())
        self.opacity = 1.0
        self.alive = True
        self.captured = False
        self.wobble_phase = random.random() * 10.0

        self.body = cylinder(
            pos=self.pos - self.orientation * self.length * 0.5,
            axis=self.orientation * self.length,
            radius=self.radius,
            color=vector(0.22, 0.72, 0.63),
            opacity=self.opacity,
        )
        self.cap_a = sphere(pos=self.pos - self.orientation * self.length * 0.5, radius=self.radius, color=vector(0.18, 0.64, 0.58), opacity=self.opacity)
        self.cap_b = sphere(pos=self.pos + self.orientation * self.length * 0.5, radius=self.radius, color=vector(0.30, 0.82, 0.70), opacity=self.opacity)
        self.rings = []
        for s in [-0.35, 0.0, 0.35]:
            self.rings.append(ring(
                pos=self.pos + self.orientation * self.length * s,
                axis=self.orientation,
                radius=self.radius * 1.04,
                thickness=0.028,
                color=vector(0.96, 0.82, 0.42),
                opacity=0.85,
            ))
        self.hairs = []
        for _ in range(10):
            side = random_unit_3d()
            side.y *= 0.35
            side = safe_norm(side)
            along = rand_range(-0.45, 0.45)
            self.hairs.append({
                "side": side,
                "along": along,
                "obj": cylinder(pos=self.pos, axis=side * 0.36, radius=0.018, color=vector(0.26, 0.58, 0.50), opacity=0.55)
            })

    def set_visible(self, visible):
        for obj in [self.body, self.cap_a, self.cap_b] + self.rings + [h["obj"] for h in self.hairs]:
            obj.visible = visible

    def set_opacity(self, op):
        self.opacity = clamp(op, 0.0, 1.0)
        for obj in [self.body, self.cap_a, self.cap_b]:
            obj.opacity = self.opacity
        for r in self.rings:
            r.opacity = self.opacity * 0.85
        for h in self.hairs:
            h["obj"].opacity = self.opacity * 0.55

    def reset(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.orientation = safe_norm(random_unit_xz())
        self.alive = True
        self.captured = False
        self.set_opacity(1.0)
        self.set_visible(True)
        self.update_geometry(0)

    def update_free_motion(self, dt, move_velocity, rotate_cmd=0.0):
        self.vel = self.vel * 0.82 + move_velocity * 0.18
        self.pos += self.vel * dt
        if mag(self.vel) > 0.05:
            desired = safe_norm(vector(self.vel.x, self.vel.y * 0.15, self.vel.z), self.orientation)
            self.orientation = safe_norm(lerp_vec(self.orientation, desired, 0.055), self.orientation)
        if abs(rotate_cmd) > 0.001:
            a = rotate_cmd * dt * 1.4
            c = math.cos(a)
            s = math.sin(a)
            o = self.orientation
            self.orientation = safe_norm(vector(o.x * c - o.z * s, o.y, o.x * s + o.z * c), self.orientation)

    def update_geometry(self, t):
        wobble = 0.08 * math.sin(t * 2.4 + self.wobble_phase)
        tilted = safe_norm(self.orientation + vector(0, wobble, 0), self.orientation)
        self.body.pos = self.pos - tilted * self.length * 0.5
        self.body.axis = tilted * self.length
        self.cap_a.pos = self.pos - tilted * self.length * 0.5
        self.cap_b.pos = self.pos + tilted * self.length * 0.5
        for idx, s in enumerate([-0.35, 0.0, 0.35]):
            self.rings[idx].pos = self.pos + tilted * self.length * s
            self.rings[idx].axis = tilted
        for h in self.hairs:
            base = self.pos + tilted * self.length * h["along"] + h["side"] * self.radius * 0.82
            wave = safe_norm(h["side"] + vector(0, 0.25 * math.sin(t * 4 + h["along"] * 8), 0), h["side"])
            h["obj"].pos = base
            h["obj"].axis = wave * (0.25 + 0.06 * math.sin(t * 5 + h["along"] * 13))

class Pseudopod:
    def __init__(self, base_dir, phase, color_value):
        self.base_dir = safe_norm(base_dir)
        self.dir = self.base_dir
        self.phase = phase
        self.length = 0.8
        self.shaft = cylinder(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=0.11, color=color_value, opacity=0.42)
        self.tip = sphere(pos=vector(0, 0, 0), radius=0.18, color=color_value, opacity=0.55)

    def update(self, center, radius, target_dir, t, wrap_factor, chase_factor, ritual_factor):
        front = max(0.0, dot(self.base_dir, target_dir))
        side_swirl = cross(target_dir, vector(0, 1, 0))
        if mag(side_swirl) < 0.01:
            side_swirl = vector(1, 0, 0)
        side_swirl = safe_norm(side_swirl)
        ring_dir = safe_norm(target_dir * 0.55 + side_swirl * math.sin(self.phase * 2.7) * 0.65 + vector(0, math.cos(self.phase * 1.9) * 0.25, 0))
        desired = safe_norm(
            self.base_dir * (1.0 - 0.45 * front * chase_factor) +
            target_dir * (0.85 * front * chase_factor) +
            ring_dir * (wrap_factor * 1.6),
            self.dir
        )
        self.dir = safe_norm(lerp_vec(self.dir, desired, 0.08 + 0.05 * wrap_factor), self.dir)
        pulse = 0.35 + 0.32 * math.sin(t * 2.3 + self.phase) + 0.16 * math.sin(t * 4.9 + self.phase * 1.7)
        self.length = radius * (0.25 + pulse + (front ** 2.2) * chase_factor * 1.05 + ritual_factor * 0.30 + wrap_factor * 1.35)
        self.length = clamp(self.length, radius * 0.25, radius * 2.35)
        self.shaft.pos = center + self.dir * radius * 0.58
        self.shaft.axis = self.dir * self.length
        self.shaft.radius = 0.09 + 0.035 * wrap_factor
        self.tip.pos = self.shaft.pos + self.shaft.axis
        self.tip.radius = 0.15 + 0.08 * wrap_factor
        self.shaft.opacity = 0.32 + 0.20 * wrap_factor
        self.tip.opacity = 0.48 + 0.22 * wrap_factor

    def tip_position(self):
        return self.tip.pos

class ImmuneCell:
    def __init__(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.radius = 1.35
        self.wrap_factor = 0.0
        self.digest_pulse = 0.0
        self.chase_factor = 1.0
        self.ritual_factor = 0.0
        self.target_dir = vector(1, 0, 0)
        self.body = sphere(pos=self.pos, radius=self.radius, color=vector(1.0, 0.62, 0.78), opacity=0.36, shininess=0.35)
        self.core = sphere(pos=self.pos, radius=self.radius * 0.46, color=vector(0.82, 0.37, 0.70), opacity=0.22)
        self.membrane_normals = fibonacci_sphere_points(58)
        self.membrane_phases = [random.random() * 10.0 for _ in self.membrane_normals]
        self.membrane = [sphere(pos=self.pos + n * self.radius, radius=0.095, color=vector(1.0, 0.48, 0.78), opacity=0.50) for n in self.membrane_normals]
        dirs = fibonacci_sphere_points(13)
        self.pseudopods = []
        for d in dirs:
            if d.y < -0.7:
                d.y *= 0.3
                d = safe_norm(d)
            self.pseudopods.append(Pseudopod(d, random.random() * 10.0, vector(1.0, 0.60, 0.78)))
        self.engulf_lobes = [sphere(pos=self.pos, radius=0.35, color=vector(1.0, 0.58, 0.76), opacity=0.0) for _ in range(7)]
        self.phagosome = sphere(pos=self.pos, radius=0.2, color=vector(1.0, 0.92, 0.45), opacity=0.0)
        self.path = curve(color=vector(0.98, 0.50, 0.70), radius=0.018, opacity=0.42)
        self.path.append(self.pos)
        self.path_timer = 0.0

    def reset(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.wrap_factor = 0.0
        self.digest_pulse = 0.0
        self.chase_factor = 1.0
        self.ritual_factor = 0.0
        self.target_dir = vector(1, 0, 0)
        self.path.clear()
        self.path.append(self.pos)
        for l in self.engulf_lobes:
            l.opacity = 0
        self.phagosome.opacity = 0

    def move(self, velocity, dt):
        self.vel = self.vel * 0.82 + velocity * 0.18
        self.pos += self.vel * dt

    def update(self, dt, t, target_pos, phase, ai_mode="CHASE"):
        to_target = target_pos - self.pos
        if mag(to_target) > 1e-5:
            self.target_dir = safe_norm(to_target, self.target_dir)
        if phase == "seek":
            desired_wrap, desired_digest, self.chase_factor = 0.0, 0.0, 1.0
        elif phase == "attach":
            desired_wrap, desired_digest, self.chase_factor = 0.25, 0.0, 1.25
        elif phase == "engulf":
            desired_wrap, desired_digest, self.chase_factor = 1.0, 0.15, 1.15
        elif phase == "digest":
            desired_wrap, desired_digest, self.chase_factor = 0.45, 1.0, 0.35
        else:
            desired_wrap, desired_digest, self.chase_factor = 0.12, 0.25, 0.25
        self.ritual_factor = 1.0 if ai_mode in ["RITUAL_WRAP", "ARTISTIC_MARK", "ORBIT"] else 0.25 if ai_mode == "POKE" else 0.0
        self.wrap_factor += (desired_wrap - self.wrap_factor) * clamp(dt * 2.1, 0, 1)
        self.digest_pulse += (desired_digest - self.digest_pulse) * clamp(dt * 2.0, 0, 1)
        breathing = 1.0 + 0.035 * math.sin(t * 2.0) + 0.03 * self.digest_pulse * math.sin(t * 8.0)
        self.body.pos = self.pos
        self.body.radius = self.radius * breathing * (1.0 + 0.06 * self.wrap_factor)
        self.core.pos = self.pos + vector(0.08 * math.sin(t * 1.4), 0.06 * math.sin(t * 1.7), 0.08 * math.cos(t * 1.3))
        for i, n in enumerate(self.membrane_normals):
            phase_i = self.membrane_phases[i]
            front = max(0.0, dot(n, self.target_dir))
            wave = 0.065 * math.sin(t * 2.2 + phase_i)
            local_radius = self.radius * (1.0 + wave + 0.52 * (front ** 3.8) * self.chase_factor + self.wrap_factor * 0.48 * (front ** 1.9))
            p = self.pos + n * local_radius
            if front > 0.72 and self.wrap_factor > 0.2:
                p += self.target_dir * self.radius * self.wrap_factor * 0.35
            self.membrane[i].pos = p
            self.membrane[i].opacity = 0.42 + 0.18 * front + 0.08 * self.wrap_factor
        for p in self.pseudopods:
            p.update(self.pos, self.radius, self.target_dir, t, self.wrap_factor, self.chase_factor, self.ritual_factor)
        for i, lobe in enumerate(self.engulf_lobes):
            angle = i * 2.0 * math.pi / len(self.engulf_lobes) + t * 0.7
            side = cross(self.target_dir, vector(0, 1, 0))
            if mag(side) < 0.01:
                side = vector(1, 0, 0)
            side = safe_norm(side)
            up = safe_norm(cross(side, self.target_dir), vector(0, 1, 0))
            ring_offset = side * math.cos(angle) * self.radius * 0.62 + up * math.sin(angle) * self.radius * 0.62
            lobe.pos = self.pos + self.target_dir * self.radius * (0.55 + 0.28 * self.wrap_factor) + ring_offset * (0.5 + 0.4 * self.wrap_factor)
            lobe.radius = self.radius * (0.18 + 0.20 * self.wrap_factor)
            lobe.opacity = 0.02 + 0.30 * self.wrap_factor
        self.phagosome.pos = lerp_vec(self.phagosome.pos, target_pos, clamp(dt * 4.0, 0, 1))
        self.phagosome.radius = self.radius * (0.16 + 0.43 * self.wrap_factor + 0.05 * self.digest_pulse * math.sin(t * 5))
        self.phagosome.opacity = 0.02 + 0.20 * self.wrap_factor + 0.12 * self.digest_pulse
        self.path_timer += dt
        if self.path_timer > 0.18:
            self.path_timer = 0.0
            self.path.append(self.pos)

    def pseudopod_tip_positions(self):
        return [p.tip_position() for p in self.pseudopods]

class DigestionParticle:
    def __init__(self):
        self.phase = random.random() * math.tau
        self.phase2 = random.random() * math.tau
        self.radius = rand_range(0.18, 1.05)
        self.speed = rand_range(0.9, 2.2)
        self.obj = sphere(
            pos=vector(0, 0, 0),
            radius=rand_range(0.035, 0.075),
            color=random.choice([vector(1.0, 0.92, 0.25), vector(0.74, 1.0, 0.32), vector(1.0, 0.67, 0.28), vector(0.45, 0.95, 0.85)]),
            opacity=0.0,
            emissive=True,
        )

    def update(self, center, t, active, intensity=1.0):
        if not active:
            self.obj.opacity += (0.0 - self.obj.opacity) * 0.12
            return
        a = self.phase + t * self.speed * intensity
        b = self.phase2 + t * self.speed * 0.63 * intensity
        r = self.radius * (0.65 + 0.25 * math.sin(t * 1.5 + self.phase2))
        pos = center + vector(math.cos(a) * r, math.sin(b) * r * 0.55, math.sin(a) * r)
        pos += vector(0.16 * math.sin(t * 3.2 + self.phase), 0.12 * math.cos(t * 2.4 + self.phase2), 0.16 * math.cos(t * 2.8 + self.phase))
        self.obj.pos = pos
        self.obj.opacity += (0.78 - self.obj.opacity) * 0.08
        self.obj.radius = 0.04 + 0.025 * (0.5 + 0.5 * math.sin(t * 6 + self.phase))

class ExpressiveAIController:
    def __init__(self):
        self.enabled = True
        self.modes = ["CHASE", "ORBIT", "POKE", "CAREFUL", "CURIOUS", "CHAOTIC", "ARTISTIC_MARK", "RITUAL_WRAP", "DIGESTION_DANCE"]
        self.mode = "CHASE"
        self.previous_modes = []
        self.mode_timer = 0.0
        self.mode_duration = rand_range(5.0, 9.0)
        self.stagnation_timer = 0.0
        self.last_signature = None
        self.completion_timer = 0.0
        self.reset_requested = False
        self.ai_clock = 0.0

    def choose_new_mode(self, sim):
        if sim.phase == "seek":
            candidates = ["CHASE", "ORBIT", "POKE", "CAREFUL", "CURIOUS", "CHAOTIC", "ARTISTIC_MARK"]
        elif sim.phase == "attach":
            candidates = ["POKE", "RITUAL_WRAP", "CAREFUL", "ORBIT"]
        elif sim.phase in ["engulf", "digest"]:
            candidates = ["RITUAL_WRAP", "ARTISTIC_MARK", "DIGESTION_DANCE"]
        else:
            candidates = ["ARTISTIC_MARK", "CURIOUS", "CHASE"]
        candidates = [m for m in candidates if m not in self.previous_modes[-2:]] or candidates
        self.mode = random.choice(candidates)
        self.previous_modes.append(self.mode)
        self.previous_modes = self.previous_modes[-6:]
        self.mode_timer = 0.0
        self.mode_duration = rand_range(4.5, 10.0)

    def update(self, sim, dt):
        self.ai_clock += dt
        action = {
            "immune_velocity": vector(0, 0, 0),
            "bacterium_velocity": vector(0, 0, 0),
            "bacterium_rotate": 0.0,
            "mark": False,
            "spill": False,
            "particle_intensity": 1.0,
        }
        if not self.enabled:
            return action
        d = mag(sim.bacterium.pos - sim.immune.pos)
        progress = sim.phase_progress()
        signature = (round(d, 2), round(progress, 2), sim.round_id, sim.phase)
        if self.last_signature == signature and sim.phase in ["seek", "attach", "engulf"]:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 1.5)
        self.last_signature = signature
        if sim.phase == "complete":
            self.completion_timer += dt
            if self.completion_timer > 4.2:
                self.reset_requested = True
        else:
            self.completion_timer = 0
        if self.stagnation_timer > 18:
            self.reset_requested = True
        if self.reset_requested:
            sim.reset_round()
            self.reset_requested = False
            self.stagnation_timer = 0
            self.completion_timer = 0
            self.choose_new_mode(sim)
            return action
        self.mode_timer += dt
        if self.mode_timer > self.mode_duration:
            self.choose_new_mode(sim)

        immune = sim.immune
        bac = sim.bacterium
        to_bac = bac.pos - immune.pos
        dist = mag(to_bac)
        dir_to_bac = safe_norm(to_bac, vector(1, 0, 0))
        tangent = safe_norm(cross(vector(0, 1, 0), dir_to_bac), vector(0, 0, 1))
        if math.sin(self.ai_clock * 0.35) < 0:
            tangent *= -1
        flee_dir = safe_norm(bac.pos - immune.pos, random_unit_xz())
        playful_wave = vector(math.sin(self.ai_clock * 1.7), 0.25 * math.sin(self.ai_clock * 2.3), math.cos(self.ai_clock * 1.3))
        if sim.phase in ["engulf", "digest", "complete"]:
            self.mode = "DIGESTION_DANCE"
        if self.mode == "CHASE":
            action["immune_velocity"] = dir_to_bac * 1.35
            action["bacterium_velocity"] = flee_dir * 0.22 + playful_wave * 0.08
            action["bacterium_rotate"] = 0.5 * math.sin(self.ai_clock)
        elif self.mode == "ORBIT":
            action["immune_velocity"] = tangent * 0.95 + dir_to_bac * clamp((dist - 1.8) * 0.35, -0.2, 0.8)
            action["bacterium_velocity"] = -tangent * 0.25 + flee_dir * 0.05
            action["bacterium_rotate"] = 1.1
            action["mark"] = True
        elif self.mode == "POKE":
            pulse = 0.4 + 0.9 * max(0, math.sin(self.ai_clock * 2.6))
            action["immune_velocity"] = dir_to_bac * pulse + tangent * 0.18 * math.sin(self.ai_clock * 5.0)
            action["bacterium_velocity"] = flee_dir * 0.18 * max(0, math.sin(self.ai_clock * 2.6 - 0.7))
            action["spill"] = dist < 2.3 and random.random() < 0.015
        elif self.mode == "CAREFUL":
            ideal = 2.3
            approach = clamp((dist - ideal) * 0.45, -0.45, 0.65)
            action["immune_velocity"] = dir_to_bac * approach + tangent * 0.18
            action["bacterium_velocity"] = playful_wave * 0.05
        elif self.mode == "CURIOUS":
            action["immune_velocity"] = dir_to_bac * 0.55 + playful_wave * 0.45
            action["bacterium_velocity"] = -playful_wave * 0.18 + tangent * 0.12
            action["mark"] = random.random() < 0.01
        elif self.mode == "CHAOTIC":
            jitter = safe_norm(playful_wave + random_unit_3d() * 0.7)
            action["immune_velocity"] = dir_to_bac * 0.75 + jitter * 0.65
            action["bacterium_velocity"] = flee_dir * 0.45 + random_unit_xz() * 0.35
            action["bacterium_rotate"] = rand_range(-2.5, 2.5)
            action["spill"] = random.random() < 0.025
        elif self.mode == "ARTISTIC_MARK":
            action["immune_velocity"] = tangent * 0.55 + dir_to_bac * 0.25 + vector(0, 0.14 * math.sin(self.ai_clock * 2.2), 0)
            action["bacterium_velocity"] = -tangent * 0.15
            action["mark"] = True
            action["particle_intensity"] = 1.4
        elif self.mode == "RITUAL_WRAP":
            action["immune_velocity"] = dir_to_bac * clamp((dist - 0.45) * 0.22, 0, 0.42) + tangent * 0.22 * math.sin(self.ai_clock * 1.8)
            action["bacterium_rotate"] = 0.35 * math.sin(self.ai_clock * 2.0)
            action["mark"] = random.random() < 0.04
            action["particle_intensity"] = 1.7
        elif self.mode == "DIGESTION_DANCE":
            action["immune_velocity"] = vector(0.18 * math.sin(self.ai_clock * 1.4), 0.08 * math.sin(self.ai_clock * 2.1), 0.18 * math.cos(self.ai_clock * 1.2))
            action["particle_intensity"] = 2.4
            action["spill"] = random.random() < 0.035
        return action

class Simulation:
    def __init__(self):
        self.t = 0.0
        self.round_id = 0
        self.paused = False
        self.help_visible = False
        self.arena_radius = 8.9
        self.immune = ImmuneCell(vector(-4.8, 1.25, -2.2))
        self.bacterium = Bacterium(vector(4.6, 0.7, 2.2))
        self.ai = ExpressiveAIController()
        self.phase = "seek"
        self.phase_timer = 0.0
        self.attach_dir = vector(1, 0, 0)
        self.engulf_start_pos = vector(0, 0, 0)
        self.digest_center = vector(0, 0, 0)
        self.particles = [DigestionParticle() for _ in range(80)]
        self.markers = []
        self.marker_timer = 0.0
        self.spill_timer = 0.0
        self.manual_override_timer = 0.0
        self.status_label = label(pos=vector(-8.9, 5.4, -7.9), text="", box=True, border=8, opacity=0.18, color=vector(0.1, 0.22, 0.28), background=vector(1, 1, 1), height=13)
        self.reset_round()

    def phase_progress(self):
        if self.phase == "seek":
            d = mag(self.bacterium.pos - self.immune.pos)
            return clamp(1.0 - d / 11.0, 0, 1)
        if self.phase == "attach":
            return clamp(self.phase_timer / 1.6, 0, 1)
        if self.phase == "engulf":
            return clamp(self.phase_timer / 4.0, 0, 1)
        if self.phase == "digest":
            return clamp(self.phase_timer / 7.0, 0, 1)
        return 1.0

    def reset_round(self):
        self.round_id += 1
        self.phase = "seek"
        self.phase_timer = 0.0
        self.attach_dir = random_unit_xz()
        immune_pos = random_unit_xz() * rand_range(4.0, 6.5) + vector(0, 1.25, 0)
        bac_pos = -safe_norm(vector(immune_pos.x, 0, immune_pos.z), random_unit_xz()) * rand_range(4.0, 6.8) + vector(0, 0.7, 0)
        bac_pos += random_unit_xz() * rand_range(0.0, 1.0)
        self.immune.reset(immune_pos)
        self.bacterium.reset(bac_pos)
        for p in self.particles:
            p.obj.opacity = 0.0
        for m in self.markers:
            m["obj"].visible = False
        self.markers = []
        self.ai.stagnation_timer = 0
        self.ai.completion_timer = 0
        self.ai.last_signature = None
        self.ai.choose_new_mode(self)

    def add_marker(self, pos, color_value=None, size=0.08, life=7.5):
        if color_value is None:
            color_value = random.choice([vector(1.0, 0.66, 0.82), vector(0.96, 0.82, 0.35), vector(0.48, 0.90, 0.86), vector(0.72, 0.70, 1.0)])
        m = sphere(pos=pos, radius=size, color=color_value, opacity=0.45)
        self.markers.append({"obj": m, "age": 0.0, "life": life})
        if len(self.markers) > 180:
            old = self.markers.pop(0)
            old["obj"].visible = False

    def spill_particles(self, origin, count=8):
        for _ in range(count):
            self.add_marker(origin + random_unit_3d() * rand_range(0.05, 0.55), random.choice([vector(1, 0.88, 0.25), vector(0.7, 1, 0.35), vector(0.38, 0.88, 0.82)]), rand_range(0.035, 0.085), rand_range(3.0, 6.5))

    def update_markers(self, dt):
        alive = []
        for m in self.markers:
            m["age"] += dt
            f = 1.0 - m["age"] / m["life"]
            if f <= 0:
                m["obj"].visible = False
            else:
                m["obj"].opacity = 0.45 * f
                m["obj"].radius *= 1.0 + 0.05 * dt
                alive.append(m)
        self.markers = alive

    def constrain_to_arena(self, obj, min_y=0.28, max_y=3.2):
        flat = vector(obj.pos.x, 0, obj.pos.z)
        r = mag(flat)
        if r > self.arena_radius:
            n = safe_norm(flat, random_unit_xz())
            obj.pos.x = n.x * self.arena_radius
            obj.pos.z = n.z * self.arena_radius
            if hasattr(obj, "vel"):
                obj.vel -= 1.8 * dot(obj.vel, n) * n
                obj.vel *= 0.65
        obj.pos.y = clamp(obj.pos.y, min_y, max_y)

    def update_phase_logic(self, dt):
        self.phase_timer += dt
        immune = self.immune
        bac = self.bacterium
        dist = mag(bac.pos - immune.pos)
        if self.phase == "seek":
            collided = dist < immune.radius * 1.05 + bac.radius * 0.85
            pseudopod_contact = any(mag(tip - bac.pos) < bac.radius + 0.35 for tip in immune.pseudopod_tip_positions())
            if collided or pseudopod_contact:
                self.phase = "attach"
                self.phase_timer = 0.0
                self.attach_dir = safe_norm(bac.pos - immune.pos, vector(1, 0, 0))
                bac.captured = True
                bac.vel = vector(0, 0, 0)
                self.spill_particles(bac.pos, 10)
        elif self.phase == "attach":
            p = smoothstep(self.phase_timer / 1.6)
            contact_pos = immune.pos + self.attach_dir * immune.radius * 0.92 + vector(0, 0.06 * math.sin(self.t * 8), 0)
            bac.pos = lerp_vec(bac.pos, contact_pos, 0.10 + 0.12 * p)
            bac.orientation = safe_norm(lerp_vec(bac.orientation, -self.attach_dir, 0.04), bac.orientation)
            if self.phase_timer > 1.6:
                self.phase = "engulf"
                self.phase_timer = 0.0
                self.engulf_start_pos = bac.pos
                self.spill_particles(bac.pos, 14)
        elif self.phase == "engulf":
            p = smoothstep(self.phase_timer / 4.0)
            inside_target = immune.pos + self.attach_dir * immune.radius * (0.75 * (1.0 - p)) + vector(0, 0.05 * math.sin(self.t * 6), 0)
            bac.pos = lerp_vec(self.engulf_start_pos, inside_target, p)
            bac.set_opacity(1.0 - 0.25 * p)
            self.digest_center = bac.pos
            if self.phase_timer > 4.0:
                self.phase = "digest"
                self.phase_timer = 0.0
                self.digest_center = immune.pos
                self.spill_particles(immune.pos, 22)
        elif self.phase == "digest":
            p = smoothstep(self.phase_timer / 7.0)
            swirl = vector(math.cos(self.t * 2.2) * 0.36 * (1 - p), math.sin(self.t * 3.1) * 0.22 * (1 - p), math.sin(self.t * 2.2) * 0.36 * (1 - p))
            bac.pos = immune.pos + swirl
            bac.set_opacity((1.0 - p) * 0.68)
            self.digest_center = bac.pos
            if self.phase_timer > 7.0:
                self.phase = "complete"
                self.phase_timer = 0.0
                bac.set_opacity(0.0)
                bac.set_visible(False)
                self.spill_particles(immune.pos, 32)

    def update_labels(self):
        ai_status = "ON" if self.ai.enabled else "OFF"
        manual = "manual override" if self.manual_override_timer > 0 else "auto"
        self.status_label.text = (
            f"Round {self.round_id} | Phase: {self.phase.upper()} | AI: {ai_status} | Mode: {self.ai.mode}\n"
            f"Progress: {self.phase_progress():.2f} | Control: {manual} | Stagnation: {self.ai.stagnation_timer:.1f}s\n"
            f"CSV: {os.path.basename(CSV_OUTPUT_PATH)}"
        )

    def update(self, dt):
        if self.paused:
            self.update_labels()
            return
        self.t += dt
        self.manual_override_timer = max(0, self.manual_override_timer - dt)
        ai_action = self.ai.update(self, dt)
        immune_vel = ai_action["immune_velocity"]
        bac_vel = ai_action["bacterium_velocity"]
        bac_rot = ai_action["bacterium_rotate"]
        if self.phase in ["seek", "attach"]:
            self.immune.move(immune_vel, dt)
        elif self.phase in ["engulf", "digest", "complete"]:
            self.immune.move(immune_vel * 0.45, dt)
        self.constrain_to_arena(self.immune, min_y=0.55, max_y=3.2)
        if self.phase == "seek" and not self.bacterium.captured:
            self.bacterium.update_free_motion(dt, bac_vel, bac_rot)
            self.constrain_to_arena(self.bacterium, min_y=0.34, max_y=2.4)
        self.update_phase_logic(dt)
        target_pos = self.bacterium.pos if self.bacterium.body.visible else self.immune.pos + self.immune.target_dir
        self.immune.update(dt, self.t, target_pos, self.phase, self.ai.mode)
        self.bacterium.update_geometry(self.t)
        digestion_active = self.phase in ["digest", "complete", "engulf"]
        intensity = ai_action["particle_intensity"]
        particle_center = self.bacterium.pos if self.phase == "engulf" else self.immune.pos
        for p in self.particles:
            p.update(particle_center, self.t, digestion_active, intensity)
        self.marker_timer += dt
        self.spill_timer += dt
        if ai_action["mark"] and self.marker_timer > 0.12:
            self.marker_timer = 0
            self.add_marker(self.immune.pos + random_unit_3d() * rand_range(0.8, 1.5), size=rand_range(0.035, 0.075), life=rand_range(5, 10))
        if ai_action["spill"] and self.spill_timer > 0.35:
            self.spill_timer = 0
            origin = self.bacterium.pos if self.phase in ["seek", "attach"] else self.immune.pos
            self.spill_particles(origin, random.randint(3, 9))
        self.update_markers(dt)
        self.update_labels()

# ----------------------------- CSV recording -----------------------------

def _base_csv_row(sim, row_type, object_id="", object_name="", state="", extra=""):
    return {
        "run_id": csv_run_id,
        "sample_index": _csv_sample_index,
        "time_seconds": f"{sim.t:.4f}",
        "row_type": row_type,
        "round_id": sim.round_id,
        "phase": sim.phase,
        "phase_progress": f"{sim.phase_progress():.5f}",
        "ai_enabled": sim.ai.enabled,
        "ai_mode": sim.ai.mode,
        "ai_mode_timer": f"{sim.ai.mode_timer:.4f}",
        "ai_stagnation_timer": f"{sim.ai.stagnation_timer:.4f}",
        "manual_override_timer": f"{sim.manual_override_timer:.4f}",
        "object_id": object_id,
        "object_name": object_name,
        "state": state,
        "pos_x": "", "pos_y": "", "pos_z": "",
        "vel_x": "", "vel_y": "", "vel_z": "",
        "radius": "", "length": "", "opacity": "",
        "orientation_x": "", "orientation_y": "", "orientation_z": "",
        "target_dir_x": "", "target_dir_y": "", "target_dir_z": "",
        "wrap_factor": "", "digest_pulse": "", "chase_factor": "", "ritual_factor": "",
        "alive": "", "captured": "", "visible": "",
        "age": "", "life": "",
        "marker_count": len(sim.markers),
        "digestion_particle_count": len(sim.particles),
        "extra": extra,
    }

def record_csv_snapshot(sim):
    rows = []
    distance = mag(sim.bacterium.pos - sim.immune.pos)
    rows.append(_base_csv_row(sim, "summary", object_name="simulation", state=sim.phase, extra=f"distance={distance:.5f};arena_radius={sim.arena_radius:.5f}"))

    immune = sim.immune
    row = _base_csv_row(sim, "immune_cell", object_id="immune", object_name="immune_cell", state="active")
    row.update(vec_fields("pos", immune.pos))
    row.update(vec_fields("vel", immune.vel))
    row.update(vec_fields("target_dir", immune.target_dir))
    row.update({
        "radius": f"{immune.radius:.5f}",
        "wrap_factor": f"{immune.wrap_factor:.5f}",
        "digest_pulse": f"{immune.digest_pulse:.5f}",
        "chase_factor": f"{immune.chase_factor:.5f}",
        "ritual_factor": f"{immune.ritual_factor:.5f}",
        "visible": getattr(immune.body, "visible", True),
        "extra": f"pseudopods={len(immune.pseudopods)};membrane_points={len(immune.membrane)}"
    })
    rows.append(row)

    bac = sim.bacterium
    row = _base_csv_row(sim, "bacterium", object_id="bacterium", object_name="bacterium_capsule", state="captured" if bac.captured else "free")
    row.update(vec_fields("pos", bac.pos))
    row.update(vec_fields("vel", bac.vel))
    row.update(vec_fields("orientation", bac.orientation))
    row.update({
        "radius": f"{bac.radius:.5f}",
        "length": f"{bac.length:.5f}",
        "opacity": f"{bac.opacity:.5f}",
        "alive": bac.alive,
        "captured": bac.captured,
        "visible": getattr(bac.body, "visible", True),
        "extra": f"wobble_phase={bac.wobble_phase:.5f}"
    })
    rows.append(row)

    for i, pod in enumerate(immune.pseudopods):
        row = _base_csv_row(sim, "pseudopod", object_id=i, object_name=f"pseudopod_{i}", state="extended")
        row.update(vec_fields("pos", pod.tip_position()))
        row.update(vec_fields("orientation", pod.dir))
        row.update({
            "radius": f"{getattr(pod.tip, 'radius', 0):.5f}",
            "length": f"{pod.length:.5f}",
            "opacity": f"{getattr(pod.tip, 'opacity', 0):.5f}",
            "extra": f"phase={pod.phase:.5f}"
        })
        rows.append(row)

    for i, p in enumerate(sim.particles):
        row = _base_csv_row(sim, "digestion_particle", object_id=i, object_name=f"digestion_particle_{i}", state="active")
        row.update(vec_fields("pos", p.obj.pos))
        row.update({
            "radius": f"{getattr(p.obj, 'radius', 0):.5f}",
            "opacity": f"{getattr(p.obj, 'opacity', 0):.5f}",
            "extra": f"phase={p.phase:.5f};phase2={p.phase2:.5f};speed={p.speed:.5f}"
        })
        rows.append(row)

    for i, m in enumerate(sim.markers):
        obj = m["obj"]
        row = _base_csv_row(sim, "marker", object_id=i, object_name=f"marker_{i}", state="visible")
        row.update(vec_fields("pos", obj.pos))
        row.update({
            "radius": f"{getattr(obj, 'radius', 0):.5f}",
            "opacity": f"{getattr(obj, 'opacity', 0):.5f}",
            "age": f"{m.get('age', 0):.5f}",
            "life": f"{m.get('life', 0):.5f}",
            "visible": getattr(obj, "visible", True)
        })
        rows.append(row)

    for row in rows:
        _csv_writer.writerow(row)

def maybe_record_csv_snapshot(sim):
    global _csv_sample_index, _csv_next_sample_time
    if sim.t + 1e-9 >= _csv_next_sample_time:
        record_csv_snapshot(sim)
        _csv_sample_index += 1
        _csv_next_sample_time += CSV_SAMPLE_INTERVAL
        if _csv_sample_index % 10 == 0:
            _csv_file.flush()

def close_csv_storage(sim):
    global _csv_closed
    if _csv_closed:
        return
    record_csv_snapshot(sim)
    _csv_file.flush()
    _csv_file.close()
    _csv_closed = True
    try:
        sim.status_label.text = (
            f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to "
            f"{os.path.basename(CSV_OUTPUT_PATH)}"
        )
    except Exception:
        pass

# ----------------------------- run -----------------------------

sim = Simulation()
last_time = time.time()
maybe_record_csv_snapshot(sim)

while sim.t < CSV_RUN_SECONDS:
    rate(60)
    now = time.time()
    dt = clamp(now - last_time, 0.001, 0.05)
    last_time = now
    sim.update(dt)
    maybe_record_csv_snapshot(sim)

close_csv_storage(sim)

while True:
    rate(5)
