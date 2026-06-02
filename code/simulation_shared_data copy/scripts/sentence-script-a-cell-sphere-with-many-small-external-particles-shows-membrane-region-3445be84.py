from vpython import *
import random
import math
import time as pytime
import os
import csv
import json
import atexit
from pathlib import Path

# ============================================================
# 3D VPython Simulation with CSV logging:
# Endocytosis and Exocytosis at a Cell Membrane
# Compatible with the core sentence branching web app CSV runner.
# ============================================================

# ----------------------------
# CSV logger
# ----------------------------
class CSVLogger:
    def __init__(self, simulation_name="endocytosis_exocytosis_membrane"):
        self.simulation_name = simulation_name
        self.run_id = os.environ.get("SIMULATION_CSV_RUN_ID", pytime.strftime("%Y%m%d_%H%M%S"))
        self.run_seconds = self._float_env("SIMULATION_CSV_RUN_SECONDS", 60.0)
        self.sample_hz = max(0.1, self._float_env("SIMULATION_CSV_SAMPLE_HZ", 5.0))
        self.sample_interval = 1.0 / self.sample_hz
        self.started = pytime.time()
        self.last_sample = -1.0
        self.rows = 0
        self.closed = False

        output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
        fallback_path = os.environ.get("SIM_STATE_CSV_PATH")
        if output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = out_dir / f"{self.run_id}_{simulation_name}.csv"
        elif fallback_path:
            self.csv_path = Path(fallback_path)
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path.cwd() / "csv_runs"
            out_dir.mkdir(parents=True, exist_ok=True)
            self.csv_path = out_dir / f"{self.run_id}_{simulation_name}.csv"

        self.metadata_path = self.csv_path.with_suffix(".metadata.json")
        self.fields = [
            "run_id", "wall_time_s", "sim_time_s", "frame", "dt", "round_index", "paused",
            "ai_enabled", "ai_mode", "ai_mode_time", "ai_stagnation_time", "ai_completion_countdown_s",
            "external_free", "released", "captured", "near_membrane", "particle_count", "mean_particle_speed",
            "active_pits", "captured_per_pit", "vesicle_count", "drifting_vesicles", "moving_vesicles",
            "endocytosis_vesicles", "internal_vesicles", "active_events", "motion_score",
            "swirl_strength", "diffusion_boost", "selected_vesicle_index", "selected_x", "selected_y", "selected_z",
            "selected_state", "selected_origin", "first_particle_x", "first_particle_y", "first_particle_z",
            "cell_radius", "world_radius"
        ]
        self.file = self.csv_path.open("w", newline="")
        self.writer = csv.DictWriter(self.file, fieldnames=self.fields)
        self.writer.writeheader()
        self.metadata_path.write_text(json.dumps({
            "run_id": self.run_id,
            "simulation_name": simulation_name,
            "csv_path": str(self.csv_path),
            "run_seconds": self.run_seconds,
            "sample_hz": self.sample_hz,
            "created_wall_time": self.started,
            "description": "Visible VPython endocytosis/exocytosis simulation with CSV state logging."
        }, indent=2))
        atexit.register(self.close)

    def _float_env(self, name, default):
        try:
            return float(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    def elapsed(self):
        return pytime.time() - self.started

    def should_stop(self):
        return self.run_seconds > 0 and self.elapsed() >= self.run_seconds

    def log(self, sim, dt, frame):
        wall = self.elapsed()
        if self.last_sample >= 0 and wall - self.last_sample < self.sample_interval:
            return
        self.last_sample = wall
        st = sim.get_state()
        selected = sim.selected_vesicle()
        first_particle = next((p for p in sim.particles if p.alive), None)
        active_pits = [p for p in sim.pits if not p.done]
        living_vesicles = [v for v in sim.vesicles if not v.done]
        captured_per_pit = sum(len(p.captured) for p in active_pits) / max(1, len(active_pits))
        row = {
            "run_id": self.run_id,
            "wall_time_s": round(wall, 4),
            "sim_time_s": round(sim.time, 4),
            "frame": frame,
            "dt": round(dt, 5),
            "round_index": sim.round_index,
            "paused": int(sim.paused),
            "ai_enabled": int(sim.ai.enabled),
            "ai_mode": sim.ai.mode,
            "ai_mode_time": round(sim.ai.mode_time, 4),
            "ai_stagnation_time": round(sim.ai.stagnation_time, 4),
            "ai_completion_countdown_s": "" if sim.ai.completion_countdown is None else round(sim.ai.completion_countdown, 4),
            "external_free": st["external_free"],
            "released": st["released"],
            "captured": st["captured"],
            "near_membrane": st["near_membrane"],
            "particle_count": st["particle_count"],
            "mean_particle_speed": round(st["mean_particle_speed"], 6),
            "active_pits": st["active_pits"],
            "captured_per_pit": round(captured_per_pit, 4),
            "vesicle_count": st["vesicle_count"],
            "drifting_vesicles": st["drifting_vesicles"],
            "moving_vesicles": st["moving_vesicles"],
            "endocytosis_vesicles": sum(1 for v in living_vesicles if v.origin == "endocytosis"),
            "internal_vesicles": sum(1 for v in living_vesicles if v.origin == "internal"),
            "active_events": st["active_events"],
            "motion_score": round(st["motion"], 6),
            "swirl_strength": round(sim.swirl_strength, 6),
            "diffusion_boost": round(sim.diffusion_boost, 6),
            "selected_vesicle_index": sim.selected_vesicle_index,
            "selected_x": round(selected.pos.x, 5) if selected else "",
            "selected_y": round(selected.pos.y, 5) if selected else "",
            "selected_z": round(selected.pos.z, 5) if selected else "",
            "selected_state": selected.state if selected else "",
            "selected_origin": selected.origin if selected else "",
            "first_particle_x": round(first_particle.pos.x, 5) if first_particle else "",
            "first_particle_y": round(first_particle.pos.y, 5) if first_particle else "",
            "first_particle_z": round(first_particle.pos.z, 5) if first_particle else "",
            "cell_radius": CELL_R,
            "world_radius": WORLD_R,
        }
        self.writer.writerow(row)
        self.rows += 1
        if self.rows % 10 == 0:
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

# ----------------------------
# Scene setup
# ----------------------------
scene.title = "Endocytosis and Exocytosis at the Membrane — VPython CSV Logger"
scene.width = 1180
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-1.6, -1.05, -1.25)
scene.center = vector(0, 0, 0)
scene.range = 8.2
scene.ambient = color.gray(0.78)

scene.caption = """
Controls:
  SPACE / P : pause / resume
  A         : toggle AI controller
  R         : reset simulation round
  E         : start an endocytic wrapping event
  X         : send an internal vesicle outward for exocytosis
  V         : spawn internal vesicle
  N         : select next vesicle
  I/K/J/L/U/O : nudge selected vesicle
  M         : cycle AI behavior mode
  C         : force chaotic AI mode
  S         : force orbit/swirl AI mode
  H         : temporary human override of AI
"""

CELL_R = 3.15
WORLD_R = 7.6
PARTICLE_R = 0.075
VESICLE_R = 0.34
MAX_ACTIVE_PITS = 5
MAX_PARTICLES = 170

COL_MEMBRANE = vector(0.80, 0.92, 1.0)
COL_MEMBRANE_EDGE = vector(0.48, 0.74, 1.0)
COL_PARTICLE = vector(0.95, 0.55, 0.72)
COL_CAPTURED = vector(1.0, 0.38, 0.72)
COL_RELEASED = vector(1.0, 0.78, 0.24)
COL_VESICLE = vector(0.38, 0.82, 0.62)
COL_EXO_VESICLE = vector(1.0, 0.68, 0.26)
COL_PIT = vector(0.42, 0.58, 1.0)
COL_FUSION = vector(1.0, 0.75, 0.15)
COL_AI = vector(0.30, 0.38, 0.75)


def clamp(x, a, b):
    return max(a, min(b, x))


def randf(a, b):
    return random.uniform(a, b)


def random_unit():
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        if mag(v) > 1e-6:
            return norm(v)


def safe_norm(v, fallback=vector(1, 0, 0)):
    return fallback if mag(v) < 1e-8 else norm(v)


def random_tangent(n):
    t = cross(safe_norm(n), random_unit())
    if mag(t) < 1e-5:
        t = cross(safe_norm(n), vector(0, 1, 0))
    return safe_norm(t, vector(1, 0, 0))


def tangent_basis(n):
    t1 = random_tangent(n)
    t2 = safe_norm(cross(safe_norm(n), t1), vector(0, 1, 0))
    return t1, t2


def smoothstep(x):
    x = clamp(x, 0, 1)
    return x * x * (3 - 2 * x)


def mix_vec(a, b, f):
    return a * (1 - f) + b * f


def color_mix(a, b, f):
    return vector(a.x * (1 - f) + b.x * f, a.y * (1 - f) + b.y * f, a.z * (1 - f) + b.z * f)


class Particle:
    def __init__(self, sim, pos, vel=None, kind="external", col=None, trail=False):
        self.sim = sim
        self.pos = vector(pos)
        self.prev_pos = vector(pos)
        self.vel = vector(vel) if vel is not None else random_unit() * randf(0.08, 0.25)
        self.kind = kind
        self.alive = True
        self.captured_by = None
        self.age = 0.0
        self.diffusion = randf(0.20, 0.55)
        self.obj = sphere(pos=self.pos, radius=PARTICLE_R, color=col or COL_PARTICLE, opacity=0.95,
                          shininess=0.45, make_trail=trail, retain=70, trail_radius=0.012)

    def mark(self, col=vector(1, 0.22, 0.65)):
        self.obj.color = col

    def attach_to(self, pit):
        self.captured_by = pit
        self.kind = "captured"
        self.vel = vector(0, 0, 0)
        self.obj.color = COL_CAPTURED
        self.obj.radius = PARTICLE_R * 1.1

    def hide(self):
        self.alive = False
        self.obj.visible = False
        if hasattr(self.obj, "clear_trail"):
            try:
                self.obj.clear_trail()
            except Exception:
                pass

    def update(self, dt):
        if not self.alive:
            return
        self.age += dt
        self.prev_pos = vector(self.pos)
        if self.captured_by is not None:
            self.obj.pos = self.pos
            return
        self.vel += random_unit() * self.diffusion * (0.70 + self.sim.diffusion_boost) * math.sqrt(max(dt, 1e-4))
        self.vel *= (1.0 - 0.40 * dt)
        if self.sim.swirl_strength > 0.01:
            tangent = cross(self.sim.swirl_axis, self.pos)
            if mag(tangent) > 0.001:
                self.vel += norm(tangent) * self.sim.swirl_strength * 0.10 * dt
        self.pos += self.vel * dt
        rmag = mag(self.pos)
        if rmag < CELL_R + PARTICLE_R * 1.3:
            n = safe_norm(self.pos)
            self.pos = n * (CELL_R + PARTICLE_R * 1.35)
            radial = dot(self.vel, n)
            if radial < 0:
                self.vel -= 1.65 * radial * n
            self.vel += n * 0.05
        if mag(self.pos) > WORLD_R:
            n = safe_norm(self.pos)
            self.pos = n * WORLD_R
            radial = dot(self.vel, n)
            if radial > 0:
                self.vel -= 1.35 * radial * n
        self.obj.pos = self.pos


class EndocyticPit:
    def __init__(self, sim, normal, playful=False):
        self.sim = sim
        self.n = safe_norm(normal)
        self.t1, self.t2 = tangent_basis(self.n)
        self.age = 0.0
        self.duration = randf(3.8, 6.0) if playful else randf(6.0, 9.5)
        self.progress = 0.0
        self.captured = []
        self.done = False
        self.mouth_radius = randf(0.55, 0.78)
        self.max_depth = randf(0.95, 1.25)
        self.phase = randf(0, 2 * math.pi)
        self.max_cargo = random.randint(4, 9)
        self.rings = [ring(pos=self.n * CELL_R, axis=self.n, radius=self.mouth_radius * (1 - 0.05 * i),
                           thickness=0.020 + 0.004 * i, color=color_mix(COL_PIT, vector(0.72, 0.45, 1.0), (i + 1) / 7),
                           opacity=0.50) for i in range(7)]
        self.marker = sphere(pos=self.n * (CELL_R + 0.035), radius=0.12, color=vector(0.44, 0.65, 1.0), opacity=0.35)

    def hide(self):
        for r in self.rings:
            r.visible = False
        self.marker.visible = False

    def capture_nearby_particles(self):
        site = self.n * CELL_R
        for p in self.sim.particles:
            if len(self.captured) >= self.max_cargo:
                return
            if not p.alive or p.captured_by is not None or p.kind not in ("external", "released"):
                continue
            align = dot(safe_norm(p.pos), self.n)
            d = mag(p.pos - site)
            if align > 0.58 and d < self.mouth_radius * (1.55 + 0.45 * self.progress):
                p.attach_to(self)
                self.captured.append(p)

    def arrange_captured(self, dt):
        site = self.n * CELL_R
        p = smoothstep(self.progress)
        for i, part in enumerate(self.captured):
            angle = self.phase + i * 2.39996 + self.age * 0.12
            cup_radius = self.mouth_radius * (1.0 - 0.72 * p) * (0.35 + 0.18 * (i % 4))
            cup_depth = self.max_depth * p * (0.35 + 0.26 * (i % 3))
            target = site - self.n * cup_depth + (math.cos(angle) * self.t1 + math.sin(angle) * self.t2) * cup_radius
            part.pos = mix_vec(part.pos, target, clamp(7.5 * dt, 0, 1))
            part.obj.pos = part.pos

    def update_visual(self):
        p = smoothstep(self.progress)
        site = self.n * CELL_R
        for i, rr in enumerate(self.rings):
            f = (i + 1) / len(self.rings)
            rr.pos = site - self.n * (self.max_depth * p * f)
            rr.axis = self.n
            rr.radius = max(0.075, self.mouth_radius * (1.0 - 0.76 * p * f))
            rr.thickness = 0.020 + 0.014 * p * f
            rr.opacity = 0.34 + 0.28 * (1 - f)
            rr.color = color_mix(COL_PIT, vector(0.72, 0.39, 0.95), p * f)
        self.marker.pos = site - self.n * (self.max_depth * p * 0.62)
        self.marker.radius = 0.12 + 0.18 * p

    def pinch_off(self):
        cargo = max(2, len(self.captured))
        for p in self.captured:
            p.hide()
        ves = Vesicle(self.sim, pos=self.n * (CELL_R - 0.78), cargo_count=cargo, col=COL_VESICLE, origin="endocytosis")
        ves.vel = -self.n * randf(0.04, 0.13) + random_tangent(self.n) * randf(0.02, 0.08)
        self.sim.vesicles.append(ves)
        self.sim.events.append(FusionFlash(self.sim, self.n, vector(0.58, 0.54, 1.0), inward=True, max_radius=self.mouth_radius * 0.75, duration=0.75))
        self.hide()
        self.done = True

    def update(self, dt):
        self.age += dt
        self.progress = clamp(self.age / self.duration, 0, 1)
        if self.progress < 0.92:
            self.capture_nearby_particles()
        self.arrange_captured(dt)
        self.update_visual()
        if self.progress >= 1.0:
            self.pinch_off()


class Vesicle:
    def __init__(self, sim, pos=None, cargo_count=None, col=COL_EXO_VESICLE, origin="internal"):
        self.sim = sim
        self.pos = vector(pos) if pos is not None else random_unit() * randf(0.35, CELL_R - 0.9)
        self.prev_pos = vector(self.pos)
        self.vel = random_unit() * randf(0.035, 0.10)
        self.radius = VESICLE_R * randf(0.86, 1.18)
        self.cargo_count = cargo_count if cargo_count is not None else random.randint(4, 10)
        self.origin = origin
        self.state = "drift"
        self.target_n = None
        self.age = 0.0
        self.done = False
        self.selected = False
        self.orbit_axis = random_unit()
        self.obj = sphere(pos=self.pos, radius=self.radius, color=col, opacity=0.38, shininess=0.65)
        self.shell = sphere(pos=self.pos, radius=self.radius * 1.05, color=color.white, opacity=0.08)
        self.cargo_offsets = [random_unit() * randf(0.02, self.radius * 0.58) for _ in range(self.cargo_count)]
        self.cargo_objs = [sphere(pos=self.pos + off, radius=PARTICLE_R * 0.55,
                                  color=vector(1.0, 0.83, 0.38) if origin != "endocytosis" else vector(0.95, 0.46, 0.75),
                                  opacity=0.85) for off in self.cargo_offsets]

    def hide(self):
        self.done = True
        self.obj.visible = False
        self.shell.visible = False
        for c in self.cargo_objs:
            c.visible = False

    def command_to_membrane(self, normal=None):
        self.target_n = safe_norm(normal if normal is not None else self.pos, random_unit())
        self.state = "to_membrane"
        self.obj.color = COL_EXO_VESICLE
        self.obj.opacity = 0.50

    def nudge(self, direction):
        self.vel += direction * 0.35
        self.selected = True
        self.obj.color = vector(1.0, 0.52, 0.18)

    def fuse(self):
        n = self.target_n if self.target_n is not None else safe_norm(self.pos)
        self.sim.events.append(FusionFlash(self.sim, n, COL_FUSION, inward=False, max_radius=self.radius * 2.5, duration=1.15))
        self.sim.release_particles(n, self.cargo_count)
        self.hide()

    def update(self, dt):
        self.age += dt
        self.prev_pos = vector(self.pos)
        if self.state == "to_membrane":
            target = self.target_n * (CELL_R - self.radius * 0.45)
            to_target = target - self.pos
            self.vel += safe_norm(to_target, self.target_n) * 1.30 * dt
            self.vel *= (1.0 - 0.55 * dt)
            if mag(to_target) < 0.16:
                self.fuse()
                return
        else:
            self.vel += random_unit() * 0.11 * math.sqrt(max(dt, 1e-4))
            self.vel *= (1.0 - 0.35 * dt)
            if self.sim.swirl_strength > 0.01:
                tangent = cross(self.sim.swirl_axis, self.pos)
                if mag(tangent) > 0.001:
                    self.vel += norm(tangent) * self.sim.swirl_strength * 0.20 * dt
        self.pos += self.vel * dt
        allowed = CELL_R - self.radius * 1.25
        if mag(self.pos) > allowed and self.state != "to_membrane":
            n = safe_norm(self.pos)
            self.pos = n * allowed
            radial = dot(self.vel, n)
            if radial > 0:
                self.vel -= 1.55 * radial * n
            self.vel += -n * 0.035
        self.obj.pos = self.pos
        self.shell.pos = self.pos
        self.shell.color = vector(1.0, 0.72, 0.28) if self.selected else color.white
        self.shell.opacity = 0.20 + 0.05 * math.sin(self.age * 8.0) if self.selected else 0.08
        for off, c in zip(self.cargo_offsets, self.cargo_objs):
            c.pos = self.pos + off.rotate(angle=self.age * 0.22, axis=self.orbit_axis)


class FusionFlash:
    def __init__(self, sim, normal, col=COL_FUSION, inward=False, max_radius=0.65, duration=1.0):
        self.sim = sim
        self.n = safe_norm(normal)
        self.age = 0.0
        self.duration = duration
        self.max_radius = max_radius
        self.done = False
        self.inward = inward
        self.col = col
        self.rings = [ring(pos=self.n * (CELL_R + (0.02 if not inward else -0.02)), axis=self.n,
                           radius=0.10 + i * 0.035, thickness=0.020, color=col, opacity=0.62) for i in range(4)]
        self.sparkles = []
        t1, t2 = tangent_basis(self.n)
        for _ in range(10):
            a = randf(0, 2 * math.pi)
            off = (math.cos(a) * t1 + math.sin(a) * t2) * randf(0.0, max_radius)
            s = sphere(pos=self.n * CELL_R + off, radius=0.028, color=col, opacity=0.75)
            self.sparkles.append((s, off, randf(0.6, 1.4)))

    def hide(self):
        for r in self.rings:
            r.visible = False
        for s, _, _ in self.sparkles:
            s.visible = False

    def update(self, dt):
        self.age += dt
        p = clamp(self.age / self.duration, 0, 1)
        eased = smoothstep(p)
        for i, rr in enumerate(self.rings):
            f = (i + 1) / len(self.rings)
            rr.radius = 0.08 + self.max_radius * eased * f
            rr.thickness = 0.026 * (1 - p) + 0.006
            rr.opacity = 0.58 * (1 - p) * (1.0 - 0.12 * i)
            rr.pos = self.n * (CELL_R + (0.035 if not self.inward else -0.035) * math.sin(p * math.pi))
        for s, off, speed in self.sparkles:
            s.pos = self.n * CELL_R + off * (1 + eased * speed * 0.7) + self.n * (0.08 * math.sin(p * math.pi))
            s.opacity = 0.75 * (1 - p)
        if p >= 1.0:
            self.hide()
            self.done = True


class AIController:
    MODES = ["BALANCE", "HARVEST", "SECRETE", "ORBIT", "CAREFUL", "CHAOS", "ARTIST"]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "BALANCE"
        self.mode_time = 0.0
        self.mode_duration = randf(8.0, 15.0)
        self.action_timer = 0.0
        self.override_until = 0.0
        self.stagnation_time = 0.0
        self.completion_countdown = None
        self.last_signature = None
        self.artist_index = 0

    def after_reset(self):
        self.mode_time = 0.0
        self.action_timer = 0.0
        self.stagnation_time = 0.0
        self.completion_countdown = None
        self.last_signature = None
        self.artist_index = 0
        self.choose_mode(random.choice(["BALANCE", "HARVEST", "SECRETE", "ARTIST"]))

    def display_text(self):
        if not self.enabled:
            return "AI disabled — human/manual simulation control"
        if self.sim.time < self.override_until:
            return f"AI waiting: human override ({self.override_until - self.sim.time:0.1f}s)"
        if self.completion_countdown is not None:
            return f"AI loop reset in {self.completion_countdown:0.1f}s"
        return f"AI behavior: {self.mode} | next mode in {max(0, self.mode_duration - self.mode_time):0.1f}s"

    def human_override(self, seconds=4.0):
        self.override_until = max(self.override_until, self.sim.time + seconds)

    def choose_mode(self, force=None):
        if force not in self.MODES:
            force = random.choice(self.MODES)
        if force == self.mode:
            choices = [m for m in self.MODES if m != self.mode]
            force = random.choice(choices)
        self.mode = force
        self.mode_time = 0.0
        self.action_timer = 0.0
        self.mode_duration = randf(8.0, 16.5)

    def cycle_mode(self):
        idx = self.MODES.index(self.mode) if self.mode in self.MODES else -1
        self.choose_mode(self.MODES[(idx + 1) % len(self.MODES)])

    def next_mode(self):
        st = self.sim.get_state()
        weighted = []
        if st["external_free"] > 35:
            weighted += ["HARVEST", "BALANCE", "CAREFUL"]
        if st["drifting_vesicles"] > 1:
            weighted += ["SECRETE", "BALANCE", "ARTIST"]
        if st["active_pits"] == 0 and st["moving_vesicles"] == 0:
            weighted += ["CHAOS", "ARTIST", "ORBIT"]
        weighted += [m for m in self.MODES if m != self.mode]
        self.choose_mode(random.choice(weighted))

    def detect_completion(self, st, dt):
        sig = st["signature"]
        no_process = st["active_pits"] == 0 and st["moving_vesicles"] == 0 and st["active_events"] == 0
        if self.last_signature == sig and st["motion"] < 0.035 and no_process:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0.0, self.stagnation_time - 0.8 * dt)
        self.last_signature = sig
        return (st["external_free"] < 8 and st["drifting_vesicles"] < 1 and no_process) or self.stagnation_time > 11.0

    def update_completion_loop(self, dt):
        if self.completion_countdown is None:
            return False
        self.completion_countdown -= dt
        self.sim.swirl_strength = max(self.sim.swirl_strength, 0.75)
        self.sim.diffusion_boost = max(self.sim.diffusion_boost, 0.45)
        if random.random() < 0.035:
            self.sim.command_exocytosis(random_unit())
        if random.random() < 0.025:
            self.sim.start_endocytosis(random_unit(), playful=True)
        if self.completion_countdown <= 0:
            self.completion_countdown = None
            self.sim.reset(initial=False)
            return True
        return False

    def update(self, dt):
        if not self.enabled:
            return
        st = self.sim.get_state()
        if self.detect_completion(st, dt) and self.completion_countdown is None:
            self.completion_countdown = 4.0
            self.choose_mode("ARTIST")
        if self.update_completion_loop(dt):
            return
        if self.sim.time < self.override_until:
            return
        self.mode_time += dt
        self.action_timer += dt
        if self.mode_time > self.mode_duration:
            self.next_mode()
        if self.mode == "BALANCE":
            self.sim.swirl_strength = max(self.sim.swirl_strength, 0.15)
            if self.action_timer > 2.2:
                self.action_timer = 0.0
                if st["external_free"] > st["drifting_vesicles"] * 6 and st["active_pits"] < 3:
                    self.sim.start_endocytosis(self.sim.best_particle_dense_normal())
                else:
                    self.sim.command_exocytosis()
        elif self.mode == "HARVEST":
            if self.action_timer > randf(1.6, 2.8):
                self.action_timer = 0.0
                n = self.sim.best_particle_dense_normal()
                self.sim.start_endocytosis(n)
                site = n * CELL_R
                for p in self.sim.particles:
                    if p.alive and p.captured_by is None and mag(p.pos - site) < 1.6:
                        p.mark()
        elif self.mode == "SECRETE":
            if st["drifting_vesicles"] < 2 and len(self.sim.vesicles) < 12 and random.random() < 0.02:
                self.sim.spawn_internal_vesicle()
            if self.action_timer > randf(1.2, 2.2):
                self.action_timer = 0.0
                self.sim.command_exocytosis()
        elif self.mode == "ORBIT":
            self.sim.swirl_strength = max(self.sim.swirl_strength, 1.15)
            self.sim.swirl_axis = norm(vector(math.sin(self.sim.time * 0.27) * 0.45 + 0.2, 1.0, math.cos(self.sim.time * 0.21) * 0.45))
            if self.action_timer > 4.0:
                self.action_timer = 0.0
                (self.sim.command_exocytosis if random.random() < 0.55 else self.sim.start_endocytosis)(random_unit())
        elif self.mode == "CAREFUL":
            self.sim.swirl_strength = max(self.sim.swirl_strength, 0.03)
            if self.action_timer > 3.2:
                self.action_timer = 0.0
                if st["active_pits"] == 0 and st["external_free"] > 10:
                    self.sim.start_endocytosis(self.sim.best_particle_dense_normal())
                elif st["moving_vesicles"] == 0 and st["drifting_vesicles"] > 0:
                    self.sim.command_exocytosis()
        elif self.mode == "CHAOS":
            self.sim.swirl_strength = max(self.sim.swirl_strength, 1.6)
            self.sim.diffusion_boost = max(self.sim.diffusion_boost, 0.90)
            if random.random() < 0.045:
                for p in random.sample(self.sim.particles, min(8, len(self.sim.particles))):
                    if p.alive and p.captured_by is None:
                        p.vel += random_unit() * randf(0.25, 0.75)
            if self.action_timer > randf(0.75, 1.35):
                self.action_timer = 0.0
                if random.random() < 0.42:
                    self.sim.start_endocytosis(random_unit(), playful=True)
                elif random.random() < 0.82:
                    self.sim.command_exocytosis(random_unit())
                else:
                    self.sim.spawn_internal_vesicle(random_unit() * randf(0.2, CELL_R - 1.0))
        elif self.mode == "ARTIST":
            self.sim.swirl_strength = max(self.sim.swirl_strength, 0.45)
            if self.action_timer > 2.0:
                self.action_timer = 0.0
                k = self.artist_index
                golden = math.pi * (3 - math.sqrt(5))
                z = 1 - 2 * ((k % 21) / 20.0)
                rr = math.sqrt(max(0, 1 - z * z))
                n = norm(vector(math.cos(k * golden) * rr, z, math.sin(k * golden) * rr))
                self.artist_index += 1
                if self.artist_index % 2 == 0:
                    self.sim.start_endocytosis(n, playful=True)
                else:
                    self.sim.command_exocytosis(n)


class Simulation:
    def __init__(self):
        self.time = 0.0
        self.round_index = 0
        self.paused = False
        self.particles = []
        self.vesicles = []
        self.pits = []
        self.events = []
        self.swirl_strength = 0.0
        self.swirl_axis = norm(vector(0.25, 1.0, 0.18))
        self.diffusion_boost = 0.0
        self.selected_vesicle_index = 0
        self.make_static_scene()
        self.ai = AIController(self)
        self.reset(initial=True)

    def make_static_scene(self):
        self.cell = sphere(pos=vector(0, 0, 0), radius=CELL_R, color=COL_MEMBRANE, opacity=0.18, shininess=0.18)
        self.mem_rings = [
            ring(pos=vector(0, 0, 0), axis=vector(0, 0, 1), radius=CELL_R, thickness=0.012, color=COL_MEMBRANE_EDGE, opacity=0.32),
            ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=CELL_R, thickness=0.012, color=COL_MEMBRANE_EDGE, opacity=0.24),
            ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=CELL_R, thickness=0.012, color=COL_MEMBRANE_EDGE, opacity=0.20)
        ]
        self.cytoplasm = sphere(pos=vector(0, 0, 0), radius=CELL_R * 0.94, color=vector(0.86, 1.0, 0.91), opacity=0.055)
        self.status = label(pos=vector(-6.4, 5.0, 0), text="", height=13, color=vector(0.16, 0.22, 0.36), box=False, opacity=0, align="left")
        self.ai_label = label(pos=vector(0, -5.25, 0), text="", height=15, color=COL_AI, box=False, opacity=0)
        self.legend = label(pos=vector(5.4, 4.9, 0), text="Pink dots: external cargo\nBlue-purple cups: endocytosis\nGreen/orange spheres: vesicles\nGold bursts: exocytosis",
                            height=12, color=vector(0.22, 0.29, 0.40), box=False, opacity=0, align="left")

    def clear_dynamic(self):
        for obj in self.particles + self.vesicles + self.pits + self.events:
            obj.hide()
        self.particles, self.vesicles, self.pits, self.events = [], [], [], []

    def reset(self, initial=False):
        self.clear_dynamic()
        self.round_index += 1
        self.time = 0.0
        self.swirl_strength = 0.0
        self.diffusion_boost = 0.0
        self.selected_vesicle_index = 0
        for _ in range(82 if initial else random.randint(65, 105)):
            n = random_unit()
            pos = n * randf(CELL_R + 0.55, WORLD_R - 0.65) + random_tangent(n) * randf(-0.55, 0.55)
            self.particles.append(Particle(self, pos, random_unit() * randf(0.03, 0.20), kind="external", col=COL_PARTICLE))
        for _ in range(random.randint(5, 8)):
            self.spawn_internal_vesicle()
        self.start_endocytosis(self.best_particle_dense_normal())
        if not initial and random.random() < 0.55:
            self.command_exocytosis()
        self.ai.after_reset()

    def spawn_internal_vesicle(self, pos=None):
        v = Vesicle(self, pos=pos, cargo_count=random.randint(4, 10), col=COL_EXO_VESICLE, origin="internal")
        self.vesicles.append(v)
        self.update_selected_visual()
        return v

    def release_particles(self, normal, count):
        n = safe_norm(normal)
        t1, t2 = tangent_basis(n)
        for _ in range(count):
            if len(self.particles) > MAX_PARTICLES:
                break
            a = randf(0, 2 * math.pi)
            tangent = math.cos(a) * t1 + math.sin(a) * t2
            pos = n * (CELL_R + 0.18 + randf(0, 0.14)) + tangent * randf(0.0, 0.22)
            vel = n * randf(0.65, 1.35) + tangent * randf(0.15, 0.75) + random_unit() * 0.08
            p = Particle(self, pos, vel, kind="released", col=COL_RELEASED, trail=True)
            p.diffusion = randf(0.16, 0.38)
            self.particles.append(p)

    def start_endocytosis(self, normal=None, playful=False):
        active = [p for p in self.pits if not p.done]
        if len(active) >= MAX_ACTIVE_PITS:
            return None
        n = safe_norm(normal if normal is not None else self.best_particle_dense_normal())
        for pit in active:
            if dot(pit.n, n) > 0.92:
                n = safe_norm(n + random_tangent(n) * 0.55)
                break
        pit = EndocyticPit(self, n, playful=playful)
        self.pits.append(pit)
        return pit

    def command_exocytosis(self, normal=None):
        candidates = [v for v in self.vesicles if not v.done and v.state == "drift"]
        if not candidates:
            if len(self.vesicles) < 10:
                candidates = [self.spawn_internal_vesicle()]
            else:
                return None
        if normal is None:
            v = min(candidates, key=lambda vv: mag(vv.pos - safe_norm(vv.pos) * CELL_R))
            normal = safe_norm(v.pos, random_unit())
        else:
            v = min(candidates, key=lambda vv: mag(vv.pos - normal * CELL_R))
        v.command_to_membrane(normal)
        return v

    def best_particle_dense_normal(self):
        free = [p for p in self.particles if p.alive and p.captured_by is None and mag(p.pos) > CELL_R]
        candidates = [random_unit() for _ in range(18)] + [safe_norm(p.pos) for p in random.sample(free, min(18, len(free)))]
        best_n, best_score = random_unit(), -1
        for n in candidates:
            site = n * CELL_R
            score = 0.0
            for p in free:
                d = mag(p.pos - site)
                align = dot(safe_norm(p.pos), n)
                if align > 0.45 and d < 1.45:
                    score += (1.45 - d) + 0.25 * align
            if score > best_score:
                best_score, best_n = score, n
        return best_n

    def living_vesicles(self):
        return [v for v in self.vesicles if not v.done]

    def selected_vesicle(self):
        living = self.living_vesicles()
        if not living:
            return None
        self.selected_vesicle_index %= len(living)
        return living[self.selected_vesicle_index]

    def update_selected_visual(self):
        living = self.living_vesicles()
        if not living:
            return
        self.selected_vesicle_index %= len(living)
        for i, v in enumerate(living):
            v.selected = (i == self.selected_vesicle_index)

    def select_next_vesicle(self):
        if self.living_vesicles():
            self.selected_vesicle_index = (self.selected_vesicle_index + 1) % len(self.living_vesicles())
            self.update_selected_visual()

    def nudge_selected(self, direction):
        v = self.selected_vesicle()
        if v:
            v.nudge(direction)
            self.ai.human_override(4.0)

    def get_state(self):
        free_external = released = captured = near_membrane = particle_count = 0
        mean_speed = 0.0
        for p in self.particles:
            if not p.alive:
                continue
            particle_count += 1
            mean_speed += mag(p.vel)
            if p.captured_by is not None:
                captured += 1
            elif p.kind == "released":
                released += 1
            else:
                free_external += 1
            if abs(mag(p.pos) - CELL_R) < 0.9:
                near_membrane += 1
        if particle_count:
            mean_speed /= particle_count
        active_pits = len([p for p in self.pits if not p.done])
        drifting = len([v for v in self.vesicles if not v.done and v.state == "drift"])
        moving = len([v for v in self.vesicles if not v.done and v.state == "to_membrane"])
        ves_count = len(self.living_vesicles())
        active_events = len([e for e in self.events if not e.done])
        motion = sum(mag(p.pos - p.prev_pos) for p in self.particles if p.alive) + sum(mag(v.pos - v.prev_pos) for v in self.vesicles if not v.done)
        return {
            "external_free": free_external, "released": released, "captured": captured, "near_membrane": near_membrane,
            "particle_count": particle_count, "mean_particle_speed": mean_speed, "active_pits": active_pits,
            "drifting_vesicles": drifting, "moving_vesicles": moving, "vesicle_count": ves_count,
            "active_events": active_events, "motion": motion,
            "signature": (round(free_external / 5), round(released / 5), active_pits, drifting, moving, active_events)
        }

    def cleanup(self):
        self.particles = [p for p in self.particles if p.alive]
        self.pits = [p for p in self.pits if not p.done]
        self.vesicles = [v for v in self.vesicles if not v.done]
        self.events = [e for e in self.events if not e.done]
        self.update_selected_visual()

    def update_labels(self):
        st = self.get_state()
        self.status.text = (f"Round {self.round_index}\nAI: {'ON' if self.ai.enabled else 'OFF'} | Mode: {self.ai.mode}\n"
                            f"Pause: {'YES' if self.paused else 'NO'}\nExternal/free: {st['external_free']}  Released: {st['released']}\n"
                            f"Captured/wrapping: {st['captured']}  Active pits: {st['active_pits']}\n"
                            f"Vesicles: {st['vesicle_count']}  Moving to membrane: {st['moving_vesicles']}\n"
                            f"Stagnation: {self.ai.stagnation_time:4.1f}s")
        self.ai_label.text = self.ai.display_text()

    def update(self, dt):
        if self.paused:
            self.update_labels()
            return
        self.time += dt
        self.swirl_strength *= (1.0 - 0.55 * dt)
        self.diffusion_boost *= (1.0 - 0.70 * dt)
        self.ai.update(dt)
        for pit in list(self.pits):
            pit.update(dt)
        for v in list(self.vesicles):
            v.update(dt)
        for p in list(self.particles):
            p.update(dt)
        for ev in list(self.events):
            ev.update(dt)
        if int(self.time * 5) != int((self.time - dt) * 5):
            self.cleanup()
            self.update_labels()


sim = Simulation()
csv_logger = CSVLogger("endocytosis_exocytosis_membrane")
scene.append_to_caption(f"\nCSV logging to: {csv_logger.csv_path}\n")


def keydown(evt):
    key = evt.key.lower()
    if key in [" ", "p"]:
        sim.paused = not sim.paused
    elif key == "a":
        sim.ai.enabled = not sim.ai.enabled
    elif key == "r":
        sim.reset(initial=False)
    elif key == "e":
        sim.start_endocytosis(sim.best_particle_dense_normal(), playful=True)
        sim.ai.human_override(4.0)
    elif key == "x":
        sim.command_exocytosis()
        sim.ai.human_override(4.0)
    elif key == "v":
        sim.spawn_internal_vesicle()
        sim.ai.human_override(4.0)
    elif key == "n":
        sim.select_next_vesicle()
        sim.ai.human_override(4.0)
    elif key == "m":
        sim.ai.cycle_mode()
        sim.ai.human_override(1.0)
    elif key == "c":
        sim.ai.choose_mode("CHAOS")
        sim.ai.enabled = True
    elif key == "s":
        sim.ai.choose_mode("ORBIT")
        sim.ai.enabled = True
    elif key == "h":
        sim.ai.human_override(8.0)
    elif key == "i":
        sim.nudge_selected(vector(0, 0.35, 0))
    elif key == "k":
        sim.nudge_selected(vector(0, -0.35, 0))
    elif key == "j":
        sim.nudge_selected(vector(-0.35, 0, 0))
    elif key == "l":
        sim.nudge_selected(vector(0.35, 0, 0))
    elif key == "u":
        sim.nudge_selected(vector(0, 0, 0.35))
    elif key == "o":
        sim.nudge_selected(vector(0, 0, -0.35))


scene.bind("keydown", keydown)

last = pytime.time()
frame = 0
sim.update_labels()

while True:
    rate(60)
    now = pytime.time()
    dt = clamp(now - last, 0.001, 0.045)
    last = now
    frame += 1
    sim.update(dt)
    csv_logger.log(sim, dt, frame)
    if csv_logger.should_stop():
        csv_logger.close()
        scene.append_to_caption(f"\nCSV run complete: {csv_logger.csv_path}\n")
        break
