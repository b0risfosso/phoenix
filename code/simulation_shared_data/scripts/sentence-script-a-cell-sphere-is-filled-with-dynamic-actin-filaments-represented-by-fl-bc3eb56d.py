from vpython import *
import random
import math
import os
import csv
import json
import time
import uuid
import atexit
from pathlib import Path

# Cytoskeleton Remodeling and Cell Shape Change
# Self-contained VPython simulation with rule-based + expressive AI controller.
#
# Keyboard:
#   A  : toggle AI on/off
#   P  : pause/resume
#   R  : reset round
#   LEFT/RIGHT : rotate crawl direction
#   UP : boost protrusion/growth
#   DOWN : boost rear contraction/disassembly
#   SPACE : branch burst
#   F : add a new filament
#   M : drop floor mark
#   O : organize/align actin
#   C : chaotic AI mode
#   1-7 : force AI behavior mode
#   H : show/hide help

scene = canvas(
    title="3D Cytoskeleton Remodeling and Cell Crawling - VPython",
    width=1200,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0, 1.2)
)
scene.forward = vector(-0.72, -0.55, -0.42)
scene.up = vector(0, 0, 1)
scene.range = 6.2

random.seed()

SOFT_BLUE = vector(0.38, 0.82, 1.0)
MEMBRANE_BLUE = vector(0.45, 0.92, 1.0)
BULGE_GREEN = vector(0.55, 1.0, 0.68)
REAR_ROSE = vector(1.0, 0.55, 0.55)
ACTIN_MAGENTA = vector(0.95, 0.25, 0.78)
ACTIN_ORANGE = vector(1.0, 0.62, 0.22)
ACTIN_YELLOW = vector(1.0, 0.86, 0.28)
NUCLEUS_LAVENDER = vector(0.70, 0.55, 1.0)
ADHESION_GREEN = vector(0.25, 0.82, 0.38)
ADHESION_OLD = vector(1.0, 0.60, 0.28)
MONOMER_CYAN = vector(0.1, 0.72, 1.0)
TRAIL_PURPLE = vector(0.65, 0.45, 1.0)

floor = box(
    pos=vector(0, 0, -0.025),
    size=vector(18, 12, 0.05),
    color=vector(0.86, 0.91, 0.86),
    shininess=0.1
)

grid_lines = []
for x in range(-9, 10):
    grid_lines.append(curve(pos=[vector(x, -6, 0.002), vector(x, 6, 0.002)],
                            radius=0.004, color=vector(0.76, 0.82, 0.76)))
for y in range(-6, 7):
    grid_lines.append(curve(pos=[vector(-9, y, 0.003), vector(9, y, 0.003)],
                            radius=0.004, color=vector(0.76, 0.82, 0.76)))

help_text = label(
    pos=vector(-5.9, -4.9, 3.6),
    text="A AI | P pause | R reset | arrows steer | SPACE branch | UP grow | DOWN retract | 1-7 AI modes",
    height=13,
    color=vector(0.15, 0.18, 0.22),
    box=False,
    opacity=0
)

status_label = label(
    pos=vector(3.8, -5.0, 3.2),
    text="",
    height=12,
    color=vector(0.12, 0.15, 0.18),
    box=False,
    opacity=0
)

mode_label = label(
    pos=vector(0, 0, 3.8),
    text="",
    height=16,
    color=vector(0.08, 0.12, 0.18),
    box=False,
    opacity=0
)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def rand_unit():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) > 0.001:
            return norm(v)


def rand_horizontal():
    a = random.uniform(0, 2 * math.pi)
    return vector(math.cos(a), math.sin(a), 0)


def rotate_horizontal(v, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return norm(vector(v.x * c - v.y * s, v.x * s + v.y * c, 0))


def horizontal_perp(v):
    return norm(vector(-v.y, v.x, 0))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def mix_color(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t



# -----------------------------
# CSV logging support for core sentence branching web app
# -----------------------------

class SimulationCSVLogger:
    """Writes visible VPython simulation state to CSV while the scene runs."""

    def __init__(self):
        self.output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR", "").strip()
        self.run_id = os.environ.get("SIMULATION_CSV_RUN_ID", "").strip() or uuid.uuid4().hex[:12]
        self.run_seconds = self._read_float("SIMULATION_CSV_RUN_SECONDS", 60.0)
        self.sample_hz = max(0.1, self._read_float("SIMULATION_CSV_SAMPLE_HZ", 10.0))
        self.sample_interval = 1.0 / self.sample_hz
        self.next_sample_elapsed = 0.0
        self.start_wall = time.time()
        self.start_monotonic = time.monotonic()
        self.closed = False

        explicit_csv = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
        if self.output_dir:
            out_dir = Path(self.output_dir).expanduser()
            out_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = out_dir / f"cytoskeleton_remodeling_{self.run_id}.csv"
        elif explicit_csv:
            self.csv_path = Path(explicit_csv).expanduser()
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path.cwd() / "csv_runs"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = out_dir / f"cytoskeleton_remodeling_{self.run_id}.csv"

        self.meta_path = self.csv_path.with_suffix(".metadata.json")
        self.fieldnames = [
            "run_id", "frame", "wall_timestamp", "elapsed_seconds", "sim_time", "round_index",
            "paused", "ai_enabled", "ai_mode", "ai_mode_time", "ai_mode_duration",
            "human_override_active", "stagnation_timer", "completion_timer",
            "cell_x", "cell_y", "cell_z", "leading_dir_x", "leading_dir_y", "leading_dir_z",
            "progress_x", "displacement_since_sample", "filament_count", "live_filament_count",
            "total_filament_points", "avg_filament_length", "total_filament_length", "longest_filament_length",
            "front_tip_count", "rear_root_count", "adhesion_count", "attached_adhesion_count",
            "detached_adhesion_count", "monomer_count", "mark_count", "trail_count",
            "growth_drive", "shrink_drive", "branch_drive", "detach_drive", "retrograde_rate",
            "flex_noise", "growth_scale", "contractility", "shape_bulge", "dip",
            "base_radius", "max_filaments", "max_points_per_filament",
        ]
        self.file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)
        self.writer.writeheader()
        self.write_metadata()
        atexit.register(self.close)

    @staticmethod
    def _read_float(name, default):
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    @staticmethod
    def _round(x, places=6):
        try:
            return round(float(x), places)
        except Exception:
            return x

    def write_metadata(self):
        payload = {
            "run_id": self.run_id,
            "csv_path": str(self.csv_path),
            "started_wall_time": self.start_wall,
            "started_wall_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.start_wall)),
            "run_seconds": self.run_seconds,
            "sample_hz": self.sample_hz,
            "simulation": "Cytoskeleton Remodeling and Cell Shape Change - VPython CSV Logger",
            "environment_variables": {
                "SIMULATION_CSV_OUTPUT_DIR": os.environ.get("SIMULATION_CSV_OUTPUT_DIR", ""),
                "SIMULATION_CSV_RUN_ID": os.environ.get("SIMULATION_CSV_RUN_ID", ""),
                "SIMULATION_CSV_RUN_SECONDS": os.environ.get("SIMULATION_CSV_RUN_SECONDS", ""),
                "SIMULATION_CSV_SAMPLE_HZ": os.environ.get("SIMULATION_CSV_SAMPLE_HZ", ""),
                "SIM_STATE_CSV_PATH": os.environ.get("SIM_STATE_CSV_PATH", ""),
            },
            "notes": "Logs visible VPython simulation state during the rendered simulation loop.",
        }
        with self.meta_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def should_stop(self):
        if self.run_seconds <= 0:
            return False
        return (time.monotonic() - self.start_monotonic) >= self.run_seconds

    def update(self, frame, sim, ai):
        if self.closed:
            return
        elapsed = time.monotonic() - self.start_monotonic
        if elapsed + 1e-9 < self.next_sample_elapsed:
            return
        self.next_sample_elapsed += self.sample_interval
        self.log(frame, sim, ai, elapsed)

    def log(self, frame, sim, ai, elapsed):
        state = sim.get_state()
        live_filaments = [f for f in sim.filaments if not f.dead]
        lengths = [f.length() for f in live_filaments]
        total_length = sum(lengths)
        total_points = sum(len(f.points) for f in live_filaments)
        detached_adh = state["adhesion_count"] - state["attached_adhesion_count"]
        override_active = sim.time < ai.override_until

        row = {
            "run_id": self.run_id,
            "frame": frame,
            "wall_timestamp": self._round(time.time(), 6),
            "elapsed_seconds": self._round(elapsed, 6),
            "sim_time": self._round(state["time"], 6),
            "round_index": state["round"],
            "paused": int(sim.paused),
            "ai_enabled": int(ai.enabled),
            "ai_mode": ai.mode,
            "ai_mode_time": self._round(ai.mode_time, 6),
            "ai_mode_duration": self._round(ai.mode_duration, 6),
            "human_override_active": int(override_active),
            "stagnation_timer": self._round(ai.stagnation_timer, 6),
            "completion_timer": self._round(ai.completion_timer, 6),
            "cell_x": self._round(state["cell_pos"].x),
            "cell_y": self._round(state["cell_pos"].y),
            "cell_z": self._round(state["cell_pos"].z),
            "leading_dir_x": self._round(state["leading_dir"].x),
            "leading_dir_y": self._round(state["leading_dir"].y),
            "leading_dir_z": self._round(state["leading_dir"].z),
            "progress_x": self._round(state["progress_x"]),
            "displacement_since_sample": self._round(state["displacement_since_sample"]),
            "filament_count": state["filament_count"],
            "live_filament_count": len(live_filaments),
            "total_filament_points": total_points,
            "avg_filament_length": self._round(state["avg_filament_length"]),
            "total_filament_length": self._round(total_length),
            "longest_filament_length": self._round(max(lengths) if lengths else 0.0),
            "front_tip_count": state["front_tip_count"],
            "rear_root_count": state["rear_root_count"],
            "adhesion_count": state["adhesion_count"],
            "attached_adhesion_count": state["attached_adhesion_count"],
            "detached_adhesion_count": detached_adh,
            "monomer_count": state["monomer_count"],
            "mark_count": state["mark_count"],
            "trail_count": len(sim.trails),
            "growth_drive": self._round(state["growth_drive"]),
            "shrink_drive": self._round(state["shrink_drive"]),
            "branch_drive": self._round(state["branch_drive"]),
            "detach_drive": self._round(sim.detach_drive),
            "retrograde_rate": self._round(sim.retrograde_rate),
            "flex_noise": self._round(sim.flex_noise),
            "growth_scale": self._round(sim.growth_scale),
            "contractility": self._round(sim.contractility),
            "shape_bulge": self._round(state["shape_bulge"]),
            "dip": self._round(sim.dip),
            "base_radius": self._round(sim.base_radius),
            "max_filaments": sim.max_filaments,
            "max_points_per_filament": sim.max_points_per_filament,
        }
        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        if self.closed:
            return
        try:
            self.file.flush()
            self.file.close()
        except Exception:
            pass
        self.closed = True


class Filament:
    def __init__(self, sim, root_local=None, direction=None, generation=0, length_points=None):
        self.sim = sim
        self.generation = generation
        self.radius = 0.018 if generation == 0 else 0.014
        self.dead = False
        self.age = 0.0
        self.wrap_flashes = []
        if root_local is None:
            root_local = self.random_inside_cell()
        if direction is None:
            direction = safe_norm(rand_unit() * 0.45 + sim.leading_dir * 0.9 + vector(0, 0, random.uniform(-0.15, 0.2)))
        direction = safe_norm(direction, sim.leading_dir)

        if length_points is None:
            length_points = random.randint(5, 10)

        self.points = [root_local]
        step = random.uniform(0.12, 0.18)
        for i in range(1, length_points):
            wiggle = rand_unit() * 0.22
            p = self.points[-1] + safe_norm(direction + wiggle, direction) * step
            p = sim.constrain_local(p)
            self.points.append(p)

        c = mix_color(ACTIN_MAGENTA, ACTIN_ORANGE, random.random() * 0.45)
        if generation > 0:
            c = mix_color(ACTIN_YELLOW, ACTIN_MAGENTA, random.random() * 0.35)
        self.base_color = c
        self.obj = curve(pos=self.world_points(), radius=self.radius, color=self.base_color, opacity=0.86)
        self.tip = sphere(pos=self.sim.local_to_world(self.points[-1]),
                          radius=self.radius * 2.4,
                          color=ACTIN_YELLOW,
                          opacity=0.9,
                          shininess=0.25)

    def random_inside_cell(self):
        r = self.sim.base_radius * random.uniform(0.15, 0.82)
        v = rand_unit()
        p = v * r
        p.z = clamp(p.z, -self.sim.base_radius * 0.75, self.sim.base_radius * 0.78)
        return p

    def world_points(self):
        return [self.sim.local_to_world(p) for p in self.points]

    def update_visual(self):
        if self.dead:
            return
        wp = self.world_points()
        try:
            self.obj.clear()
            for p in wp:
                self.obj.append(pos=p)
        except Exception:
            self.obj.visible = False
            self.obj = curve(pos=wp, radius=self.radius, color=self.base_color, opacity=0.86)

        frontness = dot(safe_norm(self.points[-1]), self.sim.leading_dir)
        self.obj.color = mix_color(ACTIN_MAGENTA, ACTIN_YELLOW, clamp((frontness + 1) * 0.5, 0, 1))
        if self.generation > 0:
            self.obj.color = mix_color(self.obj.color, ACTIN_ORANGE, 0.35)
        self.tip.pos = self.sim.local_to_world(self.points[-1])
        self.tip.color = mix_color(ACTIN_YELLOW, BULGE_GREEN, clamp(frontness, 0, 1))

    def length(self):
        if len(self.points) < 2:
            return 0
        total = 0
        for i in range(1, len(self.points)):
            total += mag(self.points[i] - self.points[i - 1])
        return total

    def grow_tip(self, amount):
        if len(self.points) < 2:
            direction = self.sim.leading_dir
        else:
            direction = safe_norm(self.points[-1] - self.points[-2], self.sim.leading_dir)

        front_bias = clamp(dot(safe_norm(self.points[-1]), self.sim.leading_dir), -1, 1)
        noise = rand_unit() * self.sim.flex_noise
        membrane_seek = self.sim.leading_dir * (0.15 + 0.65 * clamp(front_bias, 0, 1))
        upward_softness = vector(0, 0, random.uniform(-0.08, 0.08))
        direction = safe_norm(direction * 0.72 + membrane_seek + noise + upward_softness, direction)
        newp = self.points[-1] + direction * amount
        newp = self.sim.constrain_local(newp)
        if mag(newp - self.points[-1]) > 0.025:
            self.points.append(newp)

    def shrink_rear(self, intensity=1.0):
        if len(self.points) <= 3:
            if random.random() < 0.025 * intensity:
                self.kill()
            return None

        disassembled_world = self.sim.local_to_world(self.points[0])
        if random.random() < 0.75 * intensity:
            self.points.pop(0)
        else:
            self.points[0] = self.points[0] + safe_norm(self.points[1] - self.points[0], self.sim.leading_dir) * 0.06
        return disassembled_world

    def retrograde_flow(self, dt):
        flow = self.sim.leading_dir * self.sim.retrograde_rate * dt
        for i in range(len(self.points)):
            self.points[i] = self.sim.constrain_local(self.points[i] - flow)

    def organize(self, strength):
        if len(self.points) < 2:
            return
        for i in range(1, len(self.points)):
            desired = self.points[i - 1] + safe_norm((self.points[i] - self.points[i - 1]) * (1 - strength) +
                                                      self.sim.leading_dir * strength,
                                                      self.sim.leading_dir) * mag(self.points[i] - self.points[i - 1])
            self.points[i] = self.sim.constrain_local(self.points[i] * 0.75 + desired * 0.25)

    def branch(self):
        if len(self.points) < 5 or len(self.sim.filaments) > self.sim.max_filaments:
            return None
        idx = random.randint(1, len(self.points) - 3)
        root = self.points[idx]
        tangent = safe_norm(self.points[idx + 1] - self.points[idx - 1], self.sim.leading_dir)
        side = safe_norm(tangent * 0.45 + self.sim.leading_dir * 0.55 + rand_unit() * 0.75, self.sim.leading_dir)
        if random.random() < 0.5:
            side = safe_norm(side + horizontal_perp(self.sim.leading_dir) * random.uniform(-0.6, 0.6), side)
        return Filament(self.sim, root_local=root, direction=side, generation=self.generation + 1, length_points=random.randint(3, 6))

    def update(self, dt):
        if self.dead:
            return []

        self.age += dt
        new_branches = []

        self.retrograde_flow(dt)

        frontness = dot(safe_norm(self.points[-1]), self.sim.leading_dir)
        rearness = -dot(safe_norm(self.points[0]), self.sim.leading_dir)

        growth_probability = dt * self.sim.growth_drive * (0.25 + 1.35 * clamp(frontness, 0, 1))
        if random.random() < growth_probability:
            self.grow_tip(random.uniform(0.055, 0.11) * self.sim.growth_scale)

        shrink_probability = dt * self.sim.shrink_drive * (0.18 + 1.4 * clamp(rearness, 0, 1))
        if random.random() < shrink_probability:
            p = self.shrink_rear(self.sim.shrink_drive)
            if p is not None:
                self.sim.emit_monomers(p, count=random.randint(1, 3))

        branch_probability = dt * self.sim.branch_drive * (0.10 + 1.5 * clamp(frontness, 0, 1))
        if random.random() < branch_probability:
            b = self.branch()
            if b is not None:
                new_branches.append(b)

        if len(self.points) > self.sim.max_points_per_filament:
            if random.random() < 0.55:
                p = self.shrink_rear(1.5)
                if p is not None:
                    self.sim.emit_monomers(p, count=1)

        for i in range(len(self.points)):
            before = self.points[i]
            after = self.sim.constrain_local(before)
            if mag(before - after) > 0.035:
                self.wrap_flashes.append(self.sim.local_to_world(after))
            self.points[i] = after

        self.update_visual()
        return new_branches

    def kill(self):
        self.dead = True
        self.obj.visible = False
        self.tip.visible = False


class Adhesion:
    def __init__(self, sim, pos, color_override=None):
        self.sim = sim
        self.pos = vector(pos.x, pos.y, 0.012)
        self.age = 0.0
        self.attached = True
        self.life = random.uniform(6.0, 14.0)
        c = color_override if color_override is not None else ADHESION_GREEN
        self.obj = cylinder(pos=vector(self.pos.x, self.pos.y, 0.002),
                            axis=vector(0, 0, 0.024),
                            radius=random.uniform(0.045, 0.075),
                            color=c,
                            opacity=0.85,
                            shininess=0.15)

    def update(self, dt):
        self.age += dt
        rel = self.pos - self.sim.center
        rear = dot(rel, self.sim.leading_dir) < -self.sim.base_radius * 0.18
        far = mag(vector(rel.x, rel.y, 0)) > self.sim.base_radius * 1.8

        if rear and random.random() < dt * self.sim.detach_drive:
            self.attached = False
        if self.age > self.life:
            self.attached = False
        if far:
            self.attached = False

        if self.attached:
            self.obj.color = mix_color(ADHESION_GREEN, BULGE_GREEN, 0.35 + 0.25 * math.sin(self.age * 4))
            self.obj.opacity = 0.78
        else:
            self.obj.color = ADHESION_OLD
            self.obj.opacity *= 0.965
            self.obj.radius *= 0.998

        if self.obj.opacity < 0.05:
            self.obj.visible = False
            return False
        return True

    def remove(self):
        self.obj.visible = False


class Monomer:
    def __init__(self, sim, pos):
        self.sim = sim
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = rand_unit() * random.uniform(0.05, 0.28) + sim.leading_dir * random.uniform(0.02, 0.14)
        self.age = 0.0
        self.life = random.uniform(3.0, 7.0)
        self.obj = sphere(pos=self.pos,
                          radius=random.uniform(0.025, 0.045),
                          color=mix_color(MONOMER_CYAN, ACTIN_YELLOW, random.random() * 0.25),
                          opacity=0.72,
                          shininess=0.2)

    def update(self, dt):
        self.age += dt
        front_target = self.sim.center + self.sim.leading_dir * self.sim.base_radius * 0.85 + vector(0, 0, random.uniform(-0.2, 0.45))
        to_front = safe_norm(front_target - self.pos, self.sim.leading_dir)
        self.vel += to_front * 0.10 * dt
        self.vel += rand_unit() * 0.12 * dt
        self.vel *= 0.985
        self.pos += self.vel * dt

        if self.pos.z < 0.08:
            self.pos.z = 0.08
            self.vel.z = abs(self.vel.z) * 0.55

        local = self.sim.world_to_local(self.pos)
        if mag(local) > self.sim.base_radius * 1.35:
            local = safe_norm(local) * self.sim.base_radius * 1.28
            self.pos = self.sim.local_to_world(local)
            self.vel *= -0.25

        if mag(self.pos - front_target) < 0.33 and random.random() < 0.06:
            self.obj.visible = False
            if len(self.sim.filaments) < self.sim.max_filaments and random.random() < 0.35:
                self.sim.add_filament(root_local=self.sim.world_to_local(self.pos), direction=self.sim.leading_dir)
            return False

        fade = clamp(1 - self.age / self.life, 0, 1)
        self.obj.pos = self.pos
        self.obj.opacity = 0.72 * fade

        if self.age > self.life:
            self.obj.visible = False
            return False
        return True

    def remove(self):
        self.obj.visible = False


class CytoskeletonSimulation:
    def __init__(self):
        self.round_index = 0
        self.paused = False
        self.help_visible = True
        self.max_filaments = 64
        self.max_points_per_filament = 24
        self.base_radius = 1.32
        self.center = vector(-3.2, -0.3, self.base_radius * 0.96)
        self.leading_dir = norm(vector(1, 0.13, 0))
        self.time = 0.0
        self.last_center_for_motion = vector(self.center.x, self.center.y, self.center.z)

        self.growth_drive = 1.15
        self.shrink_drive = 0.95
        self.branch_drive = 0.20
        self.detach_drive = 0.55
        self.retrograde_rate = 0.055
        self.flex_noise = 0.30
        self.growth_scale = 1.0
        self.contractility = 0.75
        self.ai_shape_bulge = 0.0
        self.dip = 0.0
        self.manual_override_until = 0.0

        self.filaments = []
        self.adhesions = []
        self.monomers = []
        self.trails = []
        self.marks = []

        self.membrane = sphere(pos=self.center,
                               radius=self.base_radius,
                               color=MEMBRANE_BLUE,
                               opacity=0.20,
                               shininess=0.55)
        self.front_bulge = sphere(pos=self.center + self.leading_dir * self.base_radius * 0.86,
                                  radius=0.58,
                                  color=BULGE_GREEN,
                                  opacity=0.26,
                                  shininess=0.7)
        self.rear_shadow = sphere(pos=self.center - self.leading_dir * self.base_radius * 0.82,
                                  radius=0.42,
                                  color=REAR_ROSE,
                                  opacity=0.18)
        self.nucleus = sphere(pos=self.center + vector(-0.08, 0, 0.03),
                              radius=0.42,
                              color=NUCLEUS_LAVENDER,
                              opacity=0.62,
                              shininess=0.4)
        self.direction_arrow = arrow(pos=self.center + vector(0, 0, 1.65),
                                     axis=self.leading_dir * 0.9,
                                     shaftwidth=0.035,
                                     color=vector(0.15, 0.45, 0.9),
                                     opacity=0.65)

        self.reset()

    def reset(self):
        for f in getattr(self, "filaments", []):
            f.kill()
        for a in getattr(self, "adhesions", []):
            a.remove()
        for m in getattr(self, "monomers", []):
            m.remove()
        for t in getattr(self, "trails", []):
            t.visible = False
        for m in getattr(self, "marks", []):
            m.visible = False

        self.filaments = []
        self.adhesions = []
        self.monomers = []
        self.trails = []
        self.marks = []

        self.round_index += 1
        self.time = 0.0
        self.center = vector(-3.6, random.uniform(-0.6, 0.6), self.base_radius * 0.96)
        self.leading_dir = norm(vector(1, random.uniform(-0.22, 0.22), 0))
        self.last_center_for_motion = vector(self.center.x, self.center.y, self.center.z)

        self.growth_drive = 1.15
        self.shrink_drive = 0.95
        self.branch_drive = 0.22
        self.detach_drive = 0.60
        self.retrograde_rate = 0.055
        self.flex_noise = 0.32
        self.growth_scale = 1.0
        self.contractility = 0.76
        self.ai_shape_bulge = 0.0
        self.dip = 0.0

        for _ in range(28):
            self.add_filament()
        for _ in range(10):
            self.add_front_adhesion(scatter=1.2)

        self.drop_mark(color_override=vector(0.70, 0.82, 1.0), radius=0.20)
        self.update_visuals(0.0)

    def local_to_world(self, p):
        return self.center + p

    def world_to_local(self, p):
        return p - self.center

    def membrane_allowed_radius(self, p):
        if mag(p) < 1e-6:
            return self.base_radius
        u = norm(p)
        frontness = dot(u, self.leading_dir)
        lateral = mag(vector(u.x, u.y, 0) - self.leading_dir * dot(vector(u.x, u.y, 0), self.leading_dir))
        bulge = (0.18 + 0.22 * self.ai_shape_bulge) * max(0, frontness) ** 2
        rear_indent = 0.13 * max(0, -frontness) ** 2 * self.contractility
        bottom_flatten = 0.11 if p.z < -self.base_radius * 0.55 else 0.0
        return self.base_radius * (1 + bulge - rear_indent - bottom_flatten + 0.03 * lateral)

    def constrain_local(self, p):
        floor_local_z = 0.065 - self.center.z
        if p.z < floor_local_z:
            p.z = floor_local_z + abs(p.z - floor_local_z) * 0.06

        r = mag(p)
        allowed = self.membrane_allowed_radius(p) - 0.045
        if r > allowed:
            p = safe_norm(p) * allowed
        return p

    def add_filament(self, root_local=None, direction=None):
        if len(self.filaments) >= self.max_filaments:
            return None
        f = Filament(self, root_local=root_local, direction=direction)
        self.filaments.append(f)
        return f

    def emit_monomers(self, pos, count=2):
        if len(self.monomers) > 80:
            return
        for _ in range(count):
            self.monomers.append(Monomer(self, pos + rand_unit() * 0.035))

    def add_front_adhesion(self, scatter=0.55, color_override=None):
        front = self.center + self.leading_dir * random.uniform(self.base_radius * 0.55, self.base_radius * 1.10)
        side = horizontal_perp(self.leading_dir) * random.uniform(-scatter, scatter)
        pos = vector(front.x + side.x, front.y + side.y, 0.012)
        self.adhesions.append(Adhesion(self, pos, color_override=color_override))

    def drop_mark(self, color_override=None, radius=0.12):
        if len(self.marks) > 120:
            old = self.marks.pop(0)
            old.visible = False

        c = color_override if color_override is not None else mix_color(TRAIL_PURPLE, BULGE_GREEN, random.random())
        p = self.center - self.leading_dir * self.base_radius * random.uniform(0.2, 0.7)
        mark = cylinder(pos=vector(p.x, p.y, 0.004),
                        axis=vector(0, 0, 0.012),
                        radius=radius * random.uniform(0.7, 1.25),
                        color=c,
                        opacity=0.30,
                        shininess=0.05)
        self.marks.append(mark)

    def branch_burst(self, amount=6):
        candidates = [f for f in self.filaments if not f.dead and len(f.points) > 5]
        random.shuffle(candidates)
        created = 0
        for f in candidates[:amount * 2]:
            if created >= amount:
                break
            b = f.branch()
            if b is not None:
                self.filaments.append(b)
                created += 1

    def rotate_direction(self, angle):
        self.leading_dir = rotate_horizontal(self.leading_dir, angle)

    def organize_filaments(self, strength=0.25):
        for f in self.filaments:
            f.organize(strength)

    def induce_spill(self, amount=12):
        rear = self.center - self.leading_dir * self.base_radius * 0.9 + vector(0, 0, 0.4)
        for _ in range(amount):
            self.emit_monomers(rear + rand_unit() * random.uniform(0.05, 0.35), count=1)

    def detach_rear_adhesions(self, force=0.35):
        for a in self.adhesions:
            rel = a.pos - self.center
            if dot(rel, self.leading_dir) < 0 and random.random() < force:
                a.attached = False

    def get_state(self):
        lengths = [f.length() for f in self.filaments if not f.dead]
        avg_length = sum(lengths) / max(1, len(lengths))
        front_tips = 0
        rear_roots = 0
        for f in self.filaments:
            if f.dead:
                continue
            if dot(safe_norm(f.points[-1]), self.leading_dir) > 0.35:
                front_tips += 1
            if dot(safe_norm(f.points[0]), self.leading_dir) < -0.25:
                rear_roots += 1
        attached = sum(1 for a in self.adhesions if a.attached)
        displacement = mag(vector(self.center.x - self.last_center_for_motion.x,
                                  self.center.y - self.last_center_for_motion.y, 0))
        return {
            "time": self.time,
            "round": self.round_index,
            "cell_pos": vector(self.center.x, self.center.y, self.center.z),
            "leading_dir": vector(self.leading_dir.x, self.leading_dir.y, self.leading_dir.z),
            "filament_count": len(self.filaments),
            "avg_filament_length": avg_length,
            "front_tip_count": front_tips,
            "rear_root_count": rear_roots,
            "adhesion_count": len(self.adhesions),
            "attached_adhesion_count": attached,
            "monomer_count": len(self.monomers),
            "mark_count": len(self.marks),
            "growth_drive": self.growth_drive,
            "shrink_drive": self.shrink_drive,
            "branch_drive": self.branch_drive,
            "displacement_since_sample": displacement,
            "progress_x": self.center.x,
            "shape_bulge": self.ai_shape_bulge
        }

    def crawl_motion(self, dt):
        front_tips = 0
        rear_roots = 0
        attached_front = 0
        for f in self.filaments:
            if f.dead:
                continue
            if dot(safe_norm(f.points[-1]), self.leading_dir) > 0.28:
                front_tips += 1
            if dot(safe_norm(f.points[0]), self.leading_dir) < -0.25:
                rear_roots += 1
        for a in self.adhesions:
            if a.attached and dot(a.pos - self.center, self.leading_dir) > 0:
                attached_front += 1

        protrusion = clamp(front_tips / 22.0, 0, 1.8)
        rear_pull = clamp(rear_roots / 16.0, 0, 1.5)
        grip = clamp(attached_front / 8.0, 0.15, 1.2)

        speed = (0.09 * protrusion + 0.035 * rear_pull * self.contractility) * grip
        self.center += self.leading_dir * speed * dt
        self.center.z = self.base_radius * 0.96 + self.dip

        if self.center.x > 6.2 or abs(self.center.y) > 4.8:
            self.drop_mark(color_override=vector(1.0, 0.65, 0.38), radius=0.22)

        self.ai_shape_bulge = clamp(self.ai_shape_bulge * 0.96 + protrusion * 0.04, 0, 1.4)

    def update_visuals(self, dt):
        front_pos = self.center + self.leading_dir * self.base_radius * (0.78 + 0.18 * self.ai_shape_bulge)
        rear_pos = self.center - self.leading_dir * self.base_radius * (0.72 + 0.08 * self.contractility)

        self.membrane.pos = self.center
        self.membrane.radius = self.base_radius
        self.membrane.opacity = 0.18 + 0.03 * math.sin(self.time * 2.1)
        self.membrane.color = mix_color(MEMBRANE_BLUE, BULGE_GREEN, clamp(self.ai_shape_bulge * 0.20, 0, 0.35))

        self.front_bulge.pos = front_pos
        self.front_bulge.radius = 0.48 + 0.22 * clamp(self.ai_shape_bulge, 0, 1.2)
        self.front_bulge.opacity = 0.22 + 0.10 * clamp(self.ai_shape_bulge, 0, 1.0)

        self.rear_shadow.pos = rear_pos
        self.rear_shadow.radius = 0.38 + 0.13 * clamp(self.contractility, 0, 1.4)
        self.rear_shadow.opacity = 0.12 + 0.06 * clamp(self.shrink_drive, 0, 2) / 2

        nucleus_lag = -self.leading_dir * 0.12 + vector(0, 0, 0.02 * math.sin(self.time * 1.3))
        self.nucleus.pos = self.center + nucleus_lag
        self.nucleus.radius = 0.40 + 0.025 * math.sin(self.time * 1.7)

        self.direction_arrow.pos = self.center + vector(0, 0, 1.65)
        self.direction_arrow.axis = self.leading_dir * (0.85 + 0.15 * self.ai_shape_bulge)

        if random.random() < dt * 0.45:
            trailp = self.center - self.leading_dir * self.base_radius * 0.9
            tr = sphere(pos=vector(trailp.x, trailp.y, 0.035),
                        radius=random.uniform(0.025, 0.055),
                        color=mix_color(TRAIL_PURPLE, SOFT_BLUE, random.random() * 0.4),
                        opacity=0.35)
            self.trails.append(tr)
            if len(self.trails) > 160:
                old = self.trails.pop(0)
                old.visible = False

        for i, t in enumerate(self.trails):
            t.opacity *= 0.997
            if t.opacity < 0.03:
                t.visible = False

    def update(self, dt):
        if self.paused:
            return

        self.time += dt

        self.growth_drive = clamp(self.growth_drive * 0.997 + 1.08 * 0.003, 0.15, 3.8)
        self.shrink_drive = clamp(self.shrink_drive * 0.997 + 0.92 * 0.003, 0.10, 3.6)
        self.branch_drive = clamp(self.branch_drive * 0.996 + 0.20 * 0.004, 0.02, 1.4)
        self.detach_drive = clamp(self.detach_drive * 0.997 + 0.55 * 0.003, 0.05, 2.4)
        self.flex_noise = clamp(self.flex_noise * 0.998 + 0.30 * 0.002, 0.04, 1.2)
        self.contractility = clamp(self.contractility * 0.997 + 0.75 * 0.003, 0.05, 2.0)
        self.growth_scale = clamp(self.growth_scale * 0.997 + 1.0 * 0.003, 0.25, 2.5)
        self.dip *= 0.985

        new_filaments = []
        for f in list(self.filaments):
            if f.dead:
                continue
            new_filaments.extend(f.update(dt))

        self.filaments = [f for f in self.filaments if not f.dead]
        for nf in new_filaments:
            if len(self.filaments) < self.max_filaments:
                self.filaments.append(nf)
            else:
                nf.kill()

        if len(self.filaments) < 16 and random.random() < dt * 2.0:
            self.add_filament(direction=self.leading_dir)

        if random.random() < dt * (0.45 + 0.25 * self.growth_drive):
            self.add_front_adhesion(scatter=0.65)

        self.adhesions = [a for a in self.adhesions if a.update(dt)]
        if len(self.adhesions) > 55:
            for a in self.adhesions[:len(self.adhesions) - 55]:
                a.attached = False

        self.monomers = [m for m in self.monomers if m.update(dt)]

        if random.random() < dt * 0.10:
            self.drop_mark(radius=random.uniform(0.06, 0.11))

        self.crawl_motion(dt)
        self.update_visuals(dt)


class ExpressiveAIController:
    MODES = [
        "CURIOUS",
        "CONSTRUCTIVE",
        "DESTRUCTIVE",
        "PLAYFUL",
        "CAREFUL",
        "CHAOTIC",
        "RITUAL"
    ]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "CURIOUS"
        self.mode_time = 0.0
        self.mode_duration = random.uniform(7.0, 13.0)
        self.last_switch_time = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.loop_pause_timer = 0.0
        self.reset_requested = False
        self.sample_timer = 0.0
        self.prev_state = None
        self.recent_changes = []
        self.override = False
        self.override_until = 0.0
        self.ritual_angle = 0.0
        self.playful_phase = random.uniform(0, 10)

    def set_mode(self, mode):
        if mode in self.MODES:
            self.mode = mode
            self.mode_time = 0.0
            self.mode_duration = random.uniform(6.0, 14.0)
            self.last_switch_time = self.sim.time
            self.playful_phase = random.uniform(0, 10)
            mode_label.text = "AI mode: " + self.mode

    def choose_next_mode(self, state):
        options = list(self.MODES)

        if state["filament_count"] < 20:
            weighted = ["CONSTRUCTIVE", "CONSTRUCTIVE", "CURIOUS", "RITUAL"]
        elif state["filament_count"] > 58:
            weighted = ["DESTRUCTIVE", "CAREFUL", "CHAOTIC"]
        elif state["avg_filament_length"] < 0.65:
            weighted = ["CONSTRUCTIVE", "PLAYFUL", "CURIOUS"]
        elif state["attached_adhesion_count"] < 5:
            weighted = ["CAREFUL", "CONSTRUCTIVE", "RITUAL"]
        elif abs(state["cell_pos"].y) > 3.8:
            weighted = ["CAREFUL", "CURIOUS"]
        else:
            weighted = options + ["PLAYFUL", "CURIOUS"]

        if self.mode in weighted and len(weighted) > 1:
            weighted = [m for m in weighted if m != self.mode] or weighted
        self.set_mode(random.choice(weighted))

    def detect_stagnation_or_completion(self, dt, state):
        self.sample_timer += dt
        completed = state["progress_x"] > 6.0 or abs(state["cell_pos"].y) > 5.0
        empty = state["filament_count"] < 6
        overfull_stable = state["filament_count"] > 62 and state["avg_filament_length"] < 0.25

        if self.prev_state is not None and self.sample_timer > 1.0:
            move_change = mag(state["cell_pos"] - self.prev_state["cell_pos"])
            length_change = abs(state["avg_filament_length"] - self.prev_state["avg_filament_length"])
            count_change = abs(state["filament_count"] - self.prev_state["filament_count"])
            activity_score = move_change * 3.0 + length_change * 0.8 + count_change * 0.04
            self.recent_changes.append(activity_score)
            if len(self.recent_changes) > 8:
                self.recent_changes.pop(0)
            self.prev_state = state.copy()
            self.sample_timer = 0.0
        elif self.prev_state is None:
            self.prev_state = state.copy()

        if len(self.recent_changes) >= 6 and sum(self.recent_changes) / len(self.recent_changes) < 0.035:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 0.5)

        if completed or empty or overfull_stable:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0, self.completion_timer - dt)

        return self.stagnation_timer > 5.0 or self.completion_timer > 2.0

    def begin_new_round(self):
        self.sim.drop_mark(color_override=vector(1.0, 0.78, 0.38), radius=0.35)
        self.sim.reset()
        self.prev_state = None
        self.recent_changes = []
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.loop_pause_timer = random.uniform(0.5, 1.2)
        self.set_mode(random.choice(["CURIOUS", "CONSTRUCTIVE", "RITUAL"]))

    def apply_behavior(self, dt, state):
        manual_active = self.sim.time < self.override_until
        if manual_active:
            return

        if self.mode == "CURIOUS":
            self.sim.rotate_direction(math.sin(self.sim.time * 0.55) * 0.006)
            self.sim.growth_drive += 0.22 * dt
            self.sim.branch_drive += 0.035 * dt
            self.sim.flex_noise += 0.02 * dt
            if random.random() < dt * 0.18:
                self.sim.add_front_adhesion(scatter=0.7)
            if random.random() < dt * 0.10:
                self.sim.drop_mark(color_override=vector(0.54, 0.76, 1.0), radius=0.09)

        elif self.mode == "CONSTRUCTIVE":
            self.sim.growth_drive += 0.75 * dt
            self.sim.branch_drive += 0.16 * dt
            self.sim.growth_scale += 0.14 * dt
            self.sim.ai_shape_bulge += 0.20 * dt
            if random.random() < dt * 0.65:
                self.sim.add_front_adhesion(scatter=0.42, color_override=BULGE_GREEN)
            if random.random() < dt * 0.42:
                self.sim.branch_burst(amount=2)
            if state["filament_count"] < 36 and random.random() < dt * 1.2:
                self.sim.add_filament(direction=self.sim.leading_dir)

        elif self.mode == "DESTRUCTIVE":
            self.sim.shrink_drive += 0.82 * dt
            self.sim.detach_drive += 0.55 * dt
            self.sim.contractility += 0.35 * dt
            self.sim.ai_shape_bulge *= 0.99
            if random.random() < dt * 0.45:
                self.sim.detach_rear_adhesions(force=0.75)
            if random.random() < dt * 0.38:
                self.sim.induce_spill(amount=random.randint(3, 7))
            if random.random() < dt * 0.12:
                self.sim.drop_mark(color_override=REAR_ROSE, radius=0.15)

        elif self.mode == "PLAYFUL":
            self.playful_phase += dt
            self.sim.rotate_direction(math.sin(self.playful_phase * 2.4) * 0.018)
            self.sim.growth_drive += (0.25 + 0.2 * math.sin(self.playful_phase * 3.0)) * dt
            self.sim.branch_drive += 0.18 * dt
            self.sim.flex_noise += 0.18 * dt
            self.sim.dip += 0.0035 * math.sin(self.playful_phase * 8.0)
            if random.random() < dt * 0.55:
                self.sim.drop_mark(color_override=mix_color(vector(1.0, 0.55, 0.85), vector(0.55, 1.0, 0.85), random.random()),
                                   radius=random.uniform(0.07, 0.16))
            if random.random() < dt * 0.34:
                self.sim.branch_burst(amount=random.randint(2, 5))

        elif self.mode == "CAREFUL":
            target = vector(1, -0.10 * self.sim.center.y, 0)
            self.sim.leading_dir = safe_norm(self.sim.leading_dir * 0.985 + safe_norm(target) * 0.015, self.sim.leading_dir)
            self.sim.organize_filaments(strength=0.11)
            self.sim.growth_drive += 0.10 * dt
            self.sim.shrink_drive += 0.06 * dt
            self.sim.branch_drive -= 0.05 * dt
            self.sim.flex_noise -= 0.08 * dt
            if random.random() < dt * 0.26:
                self.sim.add_front_adhesion(scatter=0.25)
            if random.random() < dt * 0.08:
                self.sim.drop_mark(color_override=vector(0.75, 0.95, 0.88), radius=0.07)

        elif self.mode == "CHAOTIC":
            self.sim.rotate_direction(random.uniform(-0.045, 0.045))
            self.sim.growth_drive += random.uniform(0.0, 0.65) * dt
            self.sim.shrink_drive += random.uniform(0.0, 0.65) * dt
            self.sim.branch_drive += random.uniform(0.05, 0.32) * dt
            self.sim.flex_noise += 0.55 * dt
            self.sim.contractility += random.uniform(-0.1, 0.25) * dt
            self.sim.dip += random.uniform(-0.006, 0.006)
            if random.random() < dt * 0.72:
                self.sim.branch_burst(amount=random.randint(1, 7))
            if random.random() < dt * 0.55:
                self.sim.induce_spill(amount=random.randint(1, 6))
            if random.random() < dt * 0.48:
                self.sim.drop_mark(color_override=mix_color(ACTIN_ORANGE, ACTIN_MAGENTA, random.random()),
                                   radius=random.uniform(0.08, 0.22))

        elif self.mode == "RITUAL":
            self.ritual_angle += dt * 0.45
            desired = norm(vector(math.cos(self.ritual_angle), math.sin(self.ritual_angle) * 0.35, 0))
            self.sim.leading_dir = safe_norm(self.sim.leading_dir * 0.96 + desired * 0.04, self.sim.leading_dir)
            pulse = 0.5 + 0.5 * math.sin(self.sim.time * 2.0)
            self.sim.growth_drive += (0.10 + 0.28 * pulse) * dt
            self.sim.shrink_drive += (0.05 + 0.18 * (1 - pulse)) * dt
            self.sim.branch_drive += 0.06 * pulse * dt
            self.sim.contractility += 0.05 * (1 - pulse) * dt
            if random.random() < dt * 0.20:
                self.sim.add_front_adhesion(scatter=0.18, color_override=vector(0.9, 0.78, 1.0))
            if random.random() < dt * 0.20:
                self.sim.drop_mark(color_override=vector(0.78, 0.68, 1.0), radius=0.13 + 0.05 * pulse)

        self.sim.growth_drive = clamp(self.sim.growth_drive, 0.05, 3.8)
        self.sim.shrink_drive = clamp(self.sim.shrink_drive, 0.05, 3.6)
        self.sim.branch_drive = clamp(self.sim.branch_drive, 0.01, 1.4)
        self.sim.detach_drive = clamp(self.sim.detach_drive, 0.05, 2.4)
        self.sim.flex_noise = clamp(self.sim.flex_noise, 0.03, 1.25)
        self.sim.contractility = clamp(self.sim.contractility, 0.05, 2.0)
        self.sim.growth_scale = clamp(self.sim.growth_scale, 0.3, 2.6)
        self.sim.dip = clamp(self.sim.dip, -0.10, 0.12)

    def update(self, dt):
        if not self.enabled or self.sim.paused:
            return

        if self.loop_pause_timer > 0:
            self.loop_pause_timer -= dt
            return

        state = self.sim.get_state()

        if self.detect_stagnation_or_completion(dt, state):
            self.begin_new_round()
            return

        self.mode_time += dt
        if self.mode_time > self.mode_duration:
            self.choose_next_mode(state)

        self.apply_behavior(dt, state)

    def human_override(self, seconds=2.0):
        self.override_until = self.sim.time + seconds


sim = CytoskeletonSimulation()
ai = ExpressiveAIController(sim)
csv_logger = SimulationCSVLogger()


def keydown(evt):
    k = evt.key.lower()

    if k == 'a':
        ai.enabled = not ai.enabled
        ai.human_override(0.8)
    elif k == 'p':
        sim.paused = not sim.paused
    elif k == 'r':
        sim.reset()
        ai.prev_state = None
        ai.recent_changes = []
        ai.human_override(1.0)
    elif k == 'left':
        sim.rotate_direction(0.18)
        ai.human_override(2.0)
    elif k == 'right':
        sim.rotate_direction(-0.18)
        ai.human_override(2.0)
    elif k == 'up':
        sim.growth_drive += 0.8
        sim.growth_scale += 0.25
        sim.ai_shape_bulge += 0.25
        sim.add_front_adhesion()
        ai.human_override(2.0)
    elif k == 'down':
        sim.shrink_drive += 0.8
        sim.contractility += 0.35
        sim.detach_rear_adhesions(force=0.55)
        sim.induce_spill(amount=8)
        ai.human_override(2.0)
    elif k == ' ':
        sim.branch_burst(amount=10)
        ai.human_override(1.5)
    elif k == 'f':
        sim.add_filament(direction=sim.leading_dir)
        ai.human_override(1.5)
    elif k == 'm':
        sim.drop_mark(radius=0.18)
        ai.human_override(1.0)
    elif k == 'o':
        sim.organize_filaments(strength=0.35)
        ai.set_mode("CAREFUL")
        ai.human_override(0.5)
    elif k == 'c':
        ai.set_mode("CHAOTIC")
    elif k == 'h':
        sim.help_visible = not sim.help_visible
        help_text.visible = sim.help_visible
    elif k in ['1', '2', '3', '4', '5', '6', '7']:
        idx = int(k) - 1
        if 0 <= idx < len(ai.MODES):
            ai.set_mode(ai.MODES[idx])


scene.bind('keydown', keydown)

dt = 1.0 / 45.0
frame = 0

while True:
    rate(45)
    frame += 1

    ai.update(dt)
    sim.update(dt)
    csv_logger.update(frame, sim, ai)
    if csv_logger.should_stop():
        csv_logger.close()
        break

    if frame % 6 == 0:
        state = sim.get_state()
        status_label.text = (
            "Round {round} | AI {ai_state} | {mode}\n"
            "filaments {filament_count} | avg length {avg:.2f} | adhesions {adh}/{adh_total} | monomers {mon}\n"
            "growth {g:.2f} shrink {s:.2f} branch {b:.2f} | pos ({x:.1f}, {y:.1f})"
        ).format(
            round=state["round"],
            ai_state="ON" if ai.enabled else "OFF",
            mode=ai.mode,
            filament_count=state["filament_count"],
            avg=state["avg_filament_length"],
            adh=state["attached_adhesion_count"],
            adh_total=state["adhesion_count"],
            mon=state["monomer_count"],
            g=state["growth_drive"],
            s=state["shrink_drive"],
            b=state["branch_drive"],
            x=state["cell_pos"].x,
            y=state["cell_pos"].y
        )

        if sim.paused:
            mode_label.text = "PAUSED - press P to resume"
        else:
            mode_label.text = "AI mode: " + ai.mode + ("   (human override)" if sim.time < ai.override_until else "")

        help_text.visible = sim.help_visible

        if frame % 45 == 0:
            sim.last_center_for_motion = vector(sim.center.x, sim.center.y, sim.center.z)
