from vpython import *
import random
import math
import os
import csv
import json
import atexit
from datetime import datetime
from pathlib import Path

# ============================================================
# 3D Cell Colony Growing and Packing Simulation with AI Control
# VPython, self-contained
# ============================================================

scene.title = "3D Cell Colony Growing and Packing - AI Controlled"
scene.width = 1200
scene.height = 780
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-1.25, -1.45, -0.82)
scene.up = vector(0, 0, 1)
scene.center = vector(0, 0, 2.0)
scene.range = 8.5
scene.ambient = color.gray(0.78)

distant_light(direction=vector(-0.5, -0.4, -1.0), color=vector(0.85, 0.9, 1.0))
local_light(pos=vector(0, -6, 8), color=vector(0.6, 0.7, 1.0))

# -----------------------------
# Simulation constants
# -----------------------------

BASE_RADIUS = 0.45
MIN_RADIUS = 0.25
MAX_CELLS_DEFAULT = 135
DT = 0.018
SOFT_SPRING = 42.0
ADHESION = 1.25
DAMPING = 0.955
FLOOR_Z = 0.0
WORLD_RADIUS_LIMIT = 16.0

# -----------------------------
# CSV logging support
# -----------------------------
# Compatible with the core sentence branching CSV web app.
# Environment variables read by the web app runner:
#   SIMULATION_CSV_OUTPUT_DIR   directory where CSV/metadata should be written
#   SIMULATION_CSV_RUN_ID       unique id for this run
#   SIMULATION_CSV_RUN_SECONDS  run duration; defaults to 60 seconds
#   SIMULATION_CSV_SAMPLE_HZ    optional logging frequency; defaults to 5 Hz
# Fallback:
#   SIM_STATE_CSV_PATH          exact CSV path, used only if output dir is not supplied

class SimulationCSVLogger:
    def __init__(self):
        self.output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR", "").strip()
        self.run_id = os.environ.get("SIMULATION_CSV_RUN_ID", "cell_colony_growing_packing") or "cell_colony_growing_packing"
        self.run_seconds = self._float_env("SIMULATION_CSV_RUN_SECONDS", 60.0)
        self.sample_hz = max(0.1, self._float_env("SIMULATION_CSV_SAMPLE_HZ", 5.0))
        self.sample_interval = 1.0 / self.sample_hz
        self.next_sample_time = 0.0
        self.rows_written = 0
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.finished = False

        fallback_csv = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
        if self.output_dir:
            out_dir = Path(self.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_run_id = self._safe_name(self.run_id)
            self.csv_path = out_dir / f"{safe_run_id}_cell_colony_growth.csv"
        elif fallback_csv:
            self.csv_path = Path(fallback_csv)
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path.cwd() / "csv_runs"
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_run_id = self._safe_name(self.run_id)
            self.csv_path = out_dir / f"{safe_run_id}_cell_colony_growth.csv"

        self.metadata_path = self.csv_path.with_suffix(".metadata.json")
        self.fieldnames = [
            "wall_timestamp",
            "run_id",
            "sim_time",
            "round_time",
            "round_index",
            "paused",
            "ai_enabled",
            "ai_mode",
            "ai_human_override",
            "ai_reset_countdown",
            "ai_stagnant_timer",
            "cell_count",
            "max_cells",
            "particle_count",
            "link_count",
            "boundary_cell_count",
            "selected_cell_count",
            "colony_center_x",
            "colony_center_y",
            "colony_center_z",
            "colony_radius",
            "colony_height",
            "avg_speed",
            "packing_score",
            "avg_cell_radius",
            "avg_cell_age",
            "avg_cell_nutrient",
            "avg_cell_z",
            "min_cell_z",
            "max_cell_z",
            "avg_generation",
            "division_multiplier",
            "adhesion_multiplier",
            "packing_bonus",
            "wrap_opacity",
            "cursor_x",
            "cursor_y",
            "cursor_z",
            "cursor_target_x",
            "cursor_target_y",
            "cursor_target_z",
        ]
        self.csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames)
        self.writer.writeheader()
        self.csv_file.flush()
        atexit.register(self.close)
        self._write_metadata(status="started")

    def _float_env(self, name, default):
        raw = os.environ.get(name, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
            return value if value > 0 else default
        except ValueError:
            return default

    def _safe_name(self, name):
        safe = []
        for ch in str(name):
            if ch.isalnum() or ch in ("-", "_", "."):
                safe.append(ch)
            else:
                safe.append("_")
        return "".join(safe).strip("_") or "cell_colony_growing_packing"

    def _vec_components(self, v):
        return float(v.x), float(v.y), float(v.z)

    def _write_metadata(self, status="running"):
        meta = {
            "status": status,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "csv_path": str(self.csv_path),
            "run_seconds": self.run_seconds,
            "sample_hz": self.sample_hz,
            "rows_written": self.rows_written,
            "simulation": "3D Cell Colony Growing and Packing - AI Controlled",
            "vpython": True,
        }
        try:
            self.metadata_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass

    def should_sample(self, current_sim_time):
        return current_sim_time + 1e-9 >= self.next_sample_time

    def collect_row(self):
        global sim_time, round_time, round_index, paused, max_cells
        global cells, particles, links, colony_center, colony_radius, colony_height, avg_speed, packing_score, boundary_cells, ai

        if cells:
            n = len(cells)
            avg_cell_radius = sum(c.radius for c in cells) / n
            avg_cell_age = sum(c.age for c in cells) / n
            avg_cell_nutrient = sum(c.nutrient for c in cells) / n
            avg_cell_z = sum(c.pos.z for c in cells) / n
            min_cell_z = min(c.pos.z for c in cells)
            max_cell_z = max(c.pos.z for c in cells)
            avg_generation = sum(c.generation for c in cells) / n
            selected_cell_count = sum(1 for c in cells if c.selected)
        else:
            avg_cell_radius = avg_cell_age = avg_cell_nutrient = 0.0
            avg_cell_z = min_cell_z = max_cell_z = avg_generation = 0.0
            selected_cell_count = 0

        ccx, ccy, ccz = self._vec_components(colony_center)
        curx, cury, curz = self._vec_components(ai.cursor.pos)
        tarx, tary, tarz = self._vec_components(ai.cursor_target)

        return {
            "wall_timestamp": datetime.now().isoformat(timespec="milliseconds"),
            "run_id": self.run_id,
            "sim_time": round(sim_time, 6),
            "round_time": round(round_time, 6),
            "round_index": round_index,
            "paused": int(bool(paused)),
            "ai_enabled": int(bool(ai.enabled)),
            "ai_mode": ai.mode,
            "ai_human_override": int(bool(ai.human_override)),
            "ai_reset_countdown": round(ai.reset_countdown, 6),
            "ai_stagnant_timer": round(ai.stagnant_timer, 6),
            "cell_count": len(cells),
            "max_cells": max_cells,
            "particle_count": len(particles),
            "link_count": len(links),
            "boundary_cell_count": len(boundary_cells),
            "selected_cell_count": selected_cell_count,
            "colony_center_x": round(ccx, 6),
            "colony_center_y": round(ccy, 6),
            "colony_center_z": round(ccz, 6),
            "colony_radius": round(colony_radius, 6),
            "colony_height": round(colony_height, 6),
            "avg_speed": round(avg_speed, 6),
            "packing_score": round(packing_score, 6),
            "avg_cell_radius": round(avg_cell_radius, 6),
            "avg_cell_age": round(avg_cell_age, 6),
            "avg_cell_nutrient": round(avg_cell_nutrient, 6),
            "avg_cell_z": round(avg_cell_z, 6),
            "min_cell_z": round(min_cell_z, 6),
            "max_cell_z": round(max_cell_z, 6),
            "avg_generation": round(avg_generation, 6),
            "division_multiplier": round(ai.division_multiplier, 6),
            "adhesion_multiplier": round(ai.adhesion_multiplier, 6),
            "packing_bonus": round(ai.packing_bonus, 6),
            "wrap_opacity": round(ai.wrap_opacity, 6),
            "cursor_x": round(curx, 6),
            "cursor_y": round(cury, 6),
            "cursor_z": round(curz, 6),
            "cursor_target_x": round(tarx, 6),
            "cursor_target_y": round(tary, 6),
            "cursor_target_z": round(tarz, 6),
        }

    def sample(self, current_sim_time):
        if self.finished:
            return
        if not self.should_sample(current_sim_time):
            return
        row = self.collect_row()
        self.writer.writerow(row)
        self.rows_written += 1
        self.next_sample_time += self.sample_interval
        # If the simulation jumps or pauses for a long time, prevent a backlog of samples.
        if self.next_sample_time < current_sim_time - self.sample_interval:
            self.next_sample_time = current_sim_time + self.sample_interval
        if self.rows_written % max(1, int(self.sample_hz * 5)) == 0:
            self.csv_file.flush()
            self._write_metadata(status="running")

    def close(self):
        if self.finished:
            return
        self.finished = True
        try:
            self.csv_file.flush()
            self.csv_file.close()
        except Exception:
            pass
        self._write_metadata(status="finished")

    def reached_end(self, current_sim_time):
        return self.run_seconds > 0 and current_sim_time >= self.run_seconds

cells = []
particles = []
links = []

sim_time = 0.0
round_time = 0.0
round_index = 1
paused = False
cell_id_counter = 0
max_cells = MAX_CELLS_DEFAULT

colony_center = vector(0, 0, 0)
colony_radius = 0.5
colony_height = 0.9
avg_speed = 0.0
packing_score = 0.0
boundary_cells = []

# -----------------------------
# Stationary environment
# -----------------------------

floor = box(
    pos=vector(0, 0, -0.035),
    size=vector(34, 34, 0.07),
    color=vector(0.86, 0.91, 0.92),
    shininess=0.25
)

floor_grid = []
for r in [2, 4, 6, 8, 10, 12, 14, 16]:
    pts = []
    for k in range(97):
        a = 2 * math.pi * k / 96
        pts.append(vector(r * math.cos(a), r * math.sin(a), 0.006))
    floor_grid.append(curve(pos=pts, radius=0.008, color=vector(0.74, 0.82, 0.83), opacity=0.38))

for a in range(0, 180, 30):
    rad = math.radians(a)
    p1 = vector(-16 * math.cos(rad), -16 * math.sin(rad), 0.007)
    p2 = vector(16 * math.cos(rad), 16 * math.sin(rad), 0.007)
    floor_grid.append(curve(pos=[p1, p2], radius=0.006, color=vector(0.78, 0.86, 0.86), opacity=0.28))


# -----------------------------
# Boundary dome visualization
# -----------------------------

class BoundaryDome:
    def __init__(self):
        self.rings = []
        self.meridians = []
        self.n_ring_points = 96
        self.n_rings = 6
        self.n_meridians = 12
        self.visible = True

        for _ in range(self.n_rings):
            pts = [vector(0, 0, 0) for _ in range(self.n_ring_points + 1)]
            self.rings.append(curve(pos=pts, radius=0.018, color=vector(1.0, 0.73, 0.27), opacity=0.44))

        for _ in range(self.n_meridians):
            pts = [vector(0, 0, 0) for _ in range(self.n_rings)]
            self.meridians.append(curve(pos=pts, radius=0.012, color=vector(1.0, 0.72, 0.32), opacity=0.28))

        self.base_ring = curve(
            pos=[vector(0, 0, 0) for _ in range(self.n_ring_points + 1)],
            radius=0.035,
            color=vector(1.0, 0.56, 0.13),
            opacity=0.72
        )

    def set_opacity(self, opacity):
        for r in self.rings:
            r.opacity = opacity
        for m in self.meridians:
            m.opacity = opacity * 0.7
        self.base_ring.opacity = min(0.92, opacity + 0.25)

    def update(self, center, radius, height):
        radius = max(radius, 0.8)
        height = max(height, 0.8)
        center = vector(center.x, center.y, 0)

        for ri in range(self.n_rings):
            f = ri / (self.n_rings - 1)
            z = height * f
            rr = radius * math.sqrt(max(0.0, 1.0 - f * f))
            pts = []
            for k in range(self.n_ring_points + 1):
                a = 2 * math.pi * k / self.n_ring_points
                pts.append(vector(center.x + rr * math.cos(a), center.y + rr * math.sin(a), z))
            for k, p in enumerate(pts):
                self.rings[ri].modify(k, pos=p)

        base_pts = []
        for k in range(self.n_ring_points + 1):
            a = 2 * math.pi * k / self.n_ring_points
            base_pts.append(vector(center.x + radius * math.cos(a), center.y + radius * math.sin(a), 0.04))
        for k, p in enumerate(base_pts):
            self.base_ring.modify(k, pos=p)

        for mi in range(self.n_meridians):
            a = 2 * math.pi * mi / self.n_meridians
            pts = []
            for ri in range(self.n_rings):
                f = ri / (self.n_rings - 1)
                z = height * f
                rr = radius * math.sqrt(max(0.0, 1.0 - f * f))
                pts.append(vector(center.x + rr * math.cos(a), center.y + rr * math.sin(a), z))
            for k, p in enumerate(pts):
                self.meridians[mi].modify(k, pos=p)


boundary_dome = BoundaryDome()


# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v):
    m = mag(v)
    if m < 1e-9:
        return vector(1, 0, 0)
    return v / m


def random_unit():
    z = random.uniform(-1, 1)
    a = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), r * math.sin(a), z)


def random_unit_upward():
    d = random_unit()
    d.z = abs(d.z) * 0.95 + 0.12
    return safe_norm(d)


def xy(v):
    return vector(v.x, v.y, 0)


def make_color_from_hsv(h, s, v):
    return color.hsv_to_rgb(vector(h % 1.0, clamp(s, 0, 1), clamp(v, 0, 1)))


# -----------------------------
# Cell, particles, links
# -----------------------------

class Cell:
    def __init__(self, pos, radius=BASE_RADIUS, target_radius=BASE_RADIUS, parent_id=None):
        global cell_id_counter
        self.id = cell_id_counter
        cell_id_counter += 1

        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.force = vector(0, 0, 0)
        self.radius = radius
        self.target_radius = target_radius
        self.age = 0.0
        self.birth_time = sim_time
        self.parent_id = parent_id
        self.generation = 0
        self.timer = random.uniform(5.2, 10.5)
        self.marked_timer = 0.0
        self.nutrient = random.uniform(0.35, 0.9)
        self.boundary = False
        self.inner = False
        self.selected = False
        self.mass = max(0.08, self.radius ** 3)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=vector(0.55, 0.83, 0.94),
            shininess=0.55,
            opacity=0.96
        )
        self.halo = sphere(
            pos=self.pos,
            radius=self.radius * 1.14,
            color=vector(1.0, 0.78, 0.15),
            opacity=0.0,
            shininess=0.2
        )
        self.axis_mark = curve(
            pos=[self.pos, self.pos + vector(0, 0, self.radius * 1.25)],
            radius=0.012,
            color=vector(1.0, 1.0, 1.0),
            opacity=0.0
        )

    def destroy(self):
        self.body.visible = False
        self.halo.visible = False
        self.axis_mark.visible = False

    def update_visual(self, center, radius, ai_mode="OBSERVE"):
        radial = mag(xy(self.pos - center))
        outer_fraction = radial / max(radius, 0.01)

        self.boundary = outer_fraction > 0.82 or self.pos.z > colony_height * 0.82
        self.inner = outer_fraction < 0.45 and self.pos.z < colony_height * 0.75

        if self.marked_timer > 0:
            self.marked_timer -= DT
            base_color = vector(1.0, 0.42, 0.62)
        else:
            # Inner cells slowly become denser-looking, deeper, more saturated.
            if self.inner:
                density_tint = clamp(round_time / 80.0, 0.0, 1.0)
                base_color = vector(0.34 + 0.08 * density_tint, 0.67 - 0.10 * density_tint, 0.91 - 0.16 * density_tint)
            elif self.boundary:
                base_color = vector(0.55, 0.91, 0.96)
            else:
                hue = 0.53 + 0.05 * math.sin(0.7 * self.age + self.id)
                base_color = make_color_from_hsv(hue, 0.38, 0.93)

            if ai_mode == "ARTIST":
                wave = 0.5 + 0.5 * math.sin(sim_time * 1.5 + self.id * 0.27 + radial)
                base_color = make_color_from_hsv(0.48 + 0.32 * wave, 0.45, 0.96)
            elif ai_mode == "CHAOS":
                base_color = vector(0.95, 0.56 + random.random() * 0.12, 0.42)
            elif ai_mode == "NURTURE":
                base_color = base_color * 0.85 + vector(0.45, 1.0, 0.55) * 0.15
            elif ai_mode == "COMPACT":
                base_color = base_color * 0.88 + vector(0.32, 0.46, 0.85) * 0.12
            elif ai_mode == "WRAP":
                base_color = base_color * 0.82 + vector(1.0, 0.76, 0.2) * 0.18

        self.body.pos = self.pos
        self.body.radius = self.radius
        self.body.color = base_color

        halo_opacity = 0.0
        halo_color = vector(1.0, 0.76, 0.12)
        if self.boundary:
            halo_opacity = 0.13
        if self.marked_timer > 0:
            halo_opacity = 0.28
            halo_color = vector(1.0, 0.25, 0.45)
        if self.selected:
            halo_opacity = 0.36
            halo_color = vector(0.75, 0.25, 1.0)

        self.halo.pos = self.pos
        self.halo.radius = self.radius * (1.13 + 0.04 * math.sin(sim_time * 4 + self.id))
        self.halo.opacity = halo_opacity
        self.halo.color = halo_color

        axis_top = self.pos + safe_norm(vector(math.sin(self.id), math.cos(self.id * 1.7), 1.2)) * self.radius * 1.22
        self.axis_mark.modify(0, pos=self.pos)
        self.axis_mark.modify(1, pos=axis_top)
        self.axis_mark.opacity = 0.24 if self.selected else 0.0

    def grow(self):
        self.age += DT
        if self.radius < self.target_radius:
            self.radius += (self.target_radius - self.radius) * 0.035
        self.mass = max(0.08, self.radius ** 3)


class PulseParticle:
    def __init__(self, pos, vel, color_value, radius=0.045, life=1.0):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.life = life
        self.max_life = life
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=color_value,
            opacity=0.55,
            emissive=True
        )

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.vel.z -= 0.04 * dt
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0.0, 0.55 * self.life / self.max_life)
        self.obj.radius *= 0.992
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


class CellLink:
    def __init__(self, a, b, col=vector(1.0, 0.7, 0.2), opacity=0.34):
        self.a = a
        self.b = b
        self.obj = curve(pos=[a.pos, b.pos], radius=0.018, color=col, opacity=opacity)
        self.life = random.uniform(2.0, 5.5)

    def update(self, dt):
        self.life -= dt
        if self.a not in cells or self.b not in cells or self.life <= 0:
            self.obj.visible = False
            return False
        self.obj.modify(0, pos=self.a.pos)
        self.obj.modify(1, pos=self.b.pos)
        self.obj.opacity = min(self.obj.opacity, max(0.0, self.life / 5.0) * 0.4)
        return True


# -----------------------------
# AI Controller
# -----------------------------

class AIController:
    MODES = [
        "OBSERVE",
        "NURTURE",
        "COMPACT",
        "ORBIT",
        "DIP",
        "WRAP",
        "ARTIST",
        "CHAOS"
    ]

    def __init__(self):
        self.enabled = True
        self.human_override = False
        self.mode = "OBSERVE"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 9.0
        self.manual_mode_timer = 0.0
        self.stagnant_timer = 0.0
        self.completion_timer = 0.0
        self.reset_countdown = -1.0
        self.last_state_sample = None
        self.last_sample_time = 0.0
        self.division_multiplier = 1.0
        self.adhesion_multiplier = 1.0
        self.packing_bonus = 0.0
        self.wrap_opacity = 0.44
        self.global_impulse_timer = 0.0
        self.cursor_angle = 0.0
        self.cursor_height_phase = 0.0
        self.cursor_target = vector(0, 0, 2.0)
        self.cursor_manual_offset = vector(0, 0, 0)
        self.cursor = sphere(
            pos=vector(1.8, 0, 2.2),
            radius=0.23,
            color=vector(0.96, 0.32, 0.78),
            opacity=0.42,
            emissive=True
        )
        self.cursor_ring = curve(
            pos=[vector(0, 0, 0) for _ in range(65)],
            radius=0.015,
            color=vector(0.92, 0.2, 0.78),
            opacity=0.5
        )

    def reset_internal(self):
        self.mode = "NURTURE"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 8.0
        self.stagnant_timer = 0.0
        self.completion_timer = 0.0
        self.reset_countdown = -1.0
        self.last_state_sample = None
        self.last_sample_time = sim_time
        self.cursor_manual_offset = vector(0, 0, 0)

    def set_mode(self, mode, manual=False):
        if mode not in self.MODES:
            return
        self.previous_mode = self.mode
        self.mode = mode
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(7.5, 15.5)
        if manual:
            self.manual_mode_timer = 7.0
        self.flash_cursor()

    def next_mode(self, manual=False):
        options = [m for m in self.MODES if m != self.mode and m != self.previous_mode]
        if not options:
            options = self.MODES[:]
        self.set_mode(random.choice(options), manual=manual)

    def flash_cursor(self):
        for _ in range(18):
            vel = random_unit() * random.uniform(0.6, 1.7)
            particles.append(PulseParticle(self.cursor.pos, vel, vector(1.0, 0.35, 0.9), radius=0.035, life=0.75))

    def read_state(self):
        return {
            "time": sim_time,
            "round_time": round_time,
            "round": round_index,
            "n_cells": len(cells),
            "max_cells": max_cells,
            "center": colony_center,
            "radius": colony_radius,
            "height": colony_height,
            "avg_speed": avg_speed,
            "packing": packing_score,
            "boundary_count": len(boundary_cells),
            "complete": len(cells) >= max_cells,
            "empty": len(cells) == 0
        }

    def detect_stagnation_or_completion(self, state, dt):
        if state["empty"]:
            self.reset_countdown = 1.5
            return

        if sim_time - self.last_sample_time > 1.0:
            current = vector(state["n_cells"], state["radius"], state["height"])
            if self.last_state_sample is not None:
                change = mag(current - self.last_state_sample)
                if change < 0.055 and state["avg_speed"] < 0.030:
                    self.stagnant_timer += sim_time - self.last_sample_time
                else:
                    self.stagnant_timer = max(0.0, self.stagnant_timer - 1.2)

            self.last_state_sample = current
            self.last_sample_time = sim_time

        if state["complete"] and state["avg_speed"] < 0.055:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 0.5)

        if self.stagnant_timer > 10.0 or self.completion_timer > 8.0:
            if self.reset_countdown < 0:
                self.reset_countdown = 5.0
                self.set_mode("ARTIST")

        if self.reset_countdown >= 0:
            self.reset_countdown -= dt
            if self.reset_countdown <= 0:
                reset_simulation()

    def choose_behavior(self, state, dt):
        if not self.enabled:
            return

        self.mode_timer += dt
        if self.manual_mode_timer > 0:
            self.manual_mode_timer -= dt

        if self.human_override:
            return

        if state["empty"]:
            self.set_mode("NURTURE")
            return

        if state["n_cells"] < 8 and self.mode not in ["NURTURE", "OBSERVE"]:
            self.set_mode("NURTURE")
            return

        if state["complete"]:
            if self.mode not in ["ARTIST", "WRAP", "COMPACT"]:
                self.set_mode(random.choice(["ARTIST", "WRAP", "COMPACT"]))
            return

        if self.manual_mode_timer <= 0 and self.mode_timer > self.mode_duration:
            if state["packing"] < 2.2 and state["n_cells"] > 18:
                self.set_mode(random.choice(["COMPACT", "WRAP", "ORBIT"]))
            elif state["avg_speed"] < 0.025 and state["n_cells"] > 25:
                self.set_mode(random.choice(["CHAOS", "ORBIT", "DIP"]))
            elif state["height"] < 1.9 and state["n_cells"] > 30:
                self.set_mode(random.choice(["DIP", "COMPACT", "NURTURE"]))
            else:
                self.next_mode()

    def update_cursor(self, state, dt):
        r = max(1.0, state["radius"] * 1.08)
        h = max(1.2, state["height"] + 0.9)
        self.cursor_angle += dt * (0.55 if self.mode != "CHAOS" else 1.9)
        self.cursor_height_phase += dt

        if self.mode == "OBSERVE":
            target = state["center"] + vector(r * math.cos(self.cursor_angle), r * math.sin(self.cursor_angle), h * 0.92)
            self.cursor.color = vector(0.42, 0.72, 1.0)
            self.cursor.opacity = 0.25
        elif self.mode == "NURTURE":
            target = state["center"] + vector(r * 0.45 * math.cos(self.cursor_angle), r * 0.45 * math.sin(self.cursor_angle), h * 1.1)
            self.cursor.color = vector(0.35, 1.0, 0.55)
            self.cursor.opacity = 0.36
        elif self.mode == "COMPACT":
            target = state["center"] + vector(0.3 * math.cos(self.cursor_angle), 0.3 * math.sin(self.cursor_angle), h * 0.8)
            self.cursor.color = vector(0.35, 0.45, 1.0)
            self.cursor.opacity = 0.43
        elif self.mode == "ORBIT":
            target = state["center"] + vector(r * 0.95 * math.cos(self.cursor_angle), r * 0.95 * math.sin(self.cursor_angle), 0.85 + 0.5 * math.sin(self.cursor_height_phase * 1.7))
            self.cursor.color = vector(0.95, 0.35, 1.0)
            self.cursor.opacity = 0.46
        elif self.mode == "DIP":
            dip_z = max(0.8, state["height"] * (0.65 + 0.25 * math.sin(self.cursor_height_phase * 1.4)))
            target = state["center"] + vector(0.38 * math.cos(self.cursor_angle * 0.7), 0.38 * math.sin(self.cursor_angle * 0.7), dip_z)
            self.cursor.color = vector(1.0, 0.48, 0.28)
            self.cursor.opacity = 0.50
        elif self.mode == "WRAP":
            target = state["center"] + vector(r * math.cos(-self.cursor_angle * 0.72), r * math.sin(-self.cursor_angle * 0.72), h * 0.7)
            self.cursor.color = vector(1.0, 0.72, 0.15)
            self.cursor.opacity = 0.42
        elif self.mode == "ARTIST":
            target = state["center"] + vector(r * 0.72 * math.cos(self.cursor_angle * 1.3), r * 0.72 * math.sin(self.cursor_angle * 2.1), h * 0.75 + 0.5 * math.sin(self.cursor_height_phase * 2.8))
            self.cursor.color = make_color_from_hsv(0.75 + 0.14 * math.sin(sim_time), 0.65, 1.0)
            self.cursor.opacity = 0.48
        else:  # CHAOS
            target = state["center"] + vector(r * random.uniform(-0.8, 0.8), r * random.uniform(-0.8, 0.8), random.uniform(0.7, h * 1.1))
            self.cursor.color = vector(1.0, 0.38, 0.18)
            self.cursor.opacity = 0.56

        target += self.cursor_manual_offset
        self.cursor_target = target
        self.cursor.pos += (target - self.cursor.pos) * clamp(dt * 4.5, 0, 1)

        ring_pts = []
        rr = self.cursor.radius * 2.2
        for k in range(65):
            a = 2 * math.pi * k / 64
            ring_pts.append(self.cursor.pos + vector(rr * math.cos(a), rr * math.sin(a), 0))
        for k, p in enumerate(ring_pts):
            self.cursor_ring.modify(k, pos=p)
        self.cursor_ring.color = self.cursor.color
        self.cursor_ring.opacity = self.cursor.opacity * 0.9

    def configure_modifiers(self):
        self.division_multiplier = 1.0
        self.adhesion_multiplier = 1.0
        self.packing_bonus = 0.0
        self.wrap_opacity = 0.42

        if not self.enabled:
            self.wrap_opacity = 0.25
            return

        if self.mode == "NURTURE":
            self.division_multiplier = 1.75
            self.adhesion_multiplier = 0.85
            self.packing_bonus = -0.02
            self.wrap_opacity = 0.36
        elif self.mode == "COMPACT":
            self.division_multiplier = 0.92
            self.adhesion_multiplier = 1.55
            self.packing_bonus = 0.07
            self.wrap_opacity = 0.50
        elif self.mode == "ORBIT":
            self.division_multiplier = 1.1
            self.adhesion_multiplier = 1.05
            self.packing_bonus = 0.02
            self.wrap_opacity = 0.48
        elif self.mode == "DIP":
            self.division_multiplier = 1.05
            self.adhesion_multiplier = 1.25
            self.packing_bonus = 0.04
            self.wrap_opacity = 0.55
        elif self.mode == "WRAP":
            self.division_multiplier = 0.88
            self.adhesion_multiplier = 1.75
            self.packing_bonus = 0.08
            self.wrap_opacity = 0.70
        elif self.mode == "ARTIST":
            self.division_multiplier = 0.96
            self.adhesion_multiplier = 1.1
            self.packing_bonus = 0.02
            self.wrap_opacity = 0.62
        elif self.mode == "CHAOS":
            self.division_multiplier = 1.25
            self.adhesion_multiplier = 0.65
            self.packing_bonus = -0.06
            self.wrap_opacity = 0.32

    def apply_force_to_cell(self, c, state):
        if not self.enabled:
            return vector(0, 0, 0)

        center = state["center"]
        to_center = xy(center - c.pos)
        from_center = xy(c.pos - center)
        radial_dist = mag(from_center)
        radial_dir = safe_norm(from_center) if radial_dist > 0.01 else random_unit()
        force = vector(0, 0, 0)

        cursor_vec = c.pos - self.cursor.pos
        cursor_dist = mag(cursor_vec)
        cursor_dir = safe_norm(cursor_vec)

        if self.mode == "OBSERVE":
            if c.boundary and random.random() < 0.002:
                c.marked_timer = 0.8

        elif self.mode == "NURTURE":
            # Nutrient rain: gentle upward and outward breathing, visible green pulses.
            force += vector(0, 0, 0.10)
            if c.boundary:
                force += radial_dir * 0.045
            if cursor_dist < 2.4:
                force += safe_norm(c.pos - center + vector(0, 0, 0.4)) * 0.10
                c.nutrient = min(1.0, c.nutrient + 0.003)

        elif self.mode == "COMPACT":
            # Organize and pack: draw cells toward center and gently upward if crowded.
            force += safe_norm(to_center) * min(0.28, 0.035 * radial_dist)
            if c.inner:
                force += vector(0, 0, 0.08)
            if c.boundary:
                c.marked_timer = max(c.marked_timer, 0.05)

        elif self.mode == "ORBIT":
            # Orbit: tangential stirring around the colony.
            tangent = vector(-radial_dir.y, radial_dir.x, 0)
            force += tangent * (0.13 + 0.05 * math.sin(sim_time + c.id))
            if cursor_dist < 1.8:
                force += cursor_dir * 0.22

        elif self.mode == "DIP":
            # Dip: the AI cursor acts like a soft probe, compressing the top and encouraging rearrangement.
            if cursor_dist < 1.7:
                force += cursor_dir * 0.32
                force.z -= 0.10
                c.marked_timer = max(c.marked_timer, 0.10)
            if c.inner and c.pos.z < state["height"] * 0.55:
                force += vector(0, 0, 0.10)

        elif self.mode == "WRAP":
            # Wrap: boundary is held together by a ritual ring.
            if c.boundary:
                force += safe_norm(to_center) * 0.18
                force += vector(0, 0, 0.025)
                c.marked_timer = max(c.marked_timer, 0.08)

        elif self.mode == "ARTIST":
            # Artistic: colored marking, playful linking, gentle waves.
            wave = math.sin(sim_time * 1.7 + c.id * 0.37 + radial_dist)
            force += vector(-radial_dir.y, radial_dir.x, 0) * 0.035 * wave
            force += vector(0, 0, 0.035 * math.cos(sim_time * 1.1 + c.id))
            if random.random() < 0.0028:
                c.marked_timer = random.uniform(0.5, 1.8)

        elif self.mode == "CHAOS":
            # Chaotic: occasional pushes, spills, detachment-like separation.
            if random.random() < 0.012:
                force += random_unit() * random.uniform(0.4, 1.3)
                c.marked_timer = 0.25
            if cursor_dist < 2.2:
                force += cursor_dir * 0.40

        return force

    def create_visible_actions(self, state, dt):
        if not self.enabled:
            return

        if self.mode == "NURTURE" and random.random() < 0.18:
            p = self.cursor.pos + random_unit() * 0.25
            vel = vector(random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), -random.uniform(0.2, 0.8))
            particles.append(PulseParticle(p, vel, vector(0.35, 1.0, 0.45), radius=0.035, life=1.2))

        if self.mode == "CHAOS" and random.random() < 0.22:
            p = self.cursor.pos + random_unit() * 0.25
            particles.append(PulseParticle(p, random_unit() * random.uniform(0.8, 2.8), vector(1.0, 0.38, 0.12), radius=0.045, life=0.85))

        if self.mode == "ARTIST" and len(cells) > 2 and len(links) < 34 and random.random() < 0.04:
            a = random.choice(cells)
            near = [b for b in cells if b is not a and mag(a.pos - b.pos) < BASE_RADIUS * 2.8]
            if near:
                b = random.choice(near)
                col = make_color_from_hsv(random.random(), 0.55, 1.0)
                links.append(CellLink(a, b, col=col, opacity=0.34))

        if self.mode == "COMPACT" and len(cells) > 8 and len(links) < 18 and random.random() < 0.025:
            inners = [c for c in cells if c.inner]
            if len(inners) >= 2:
                a = random.choice(inners)
                b = random.choice(inners)
                if a is not b and mag(a.pos - b.pos) < BASE_RADIUS * 2.6:
                    links.append(CellLink(a, b, col=vector(0.35, 0.55, 1.0), opacity=0.26))

        if self.mode == "WRAP" and random.random() < 0.03:
            for c in boundary_cells[:6]:
                c.marked_timer = max(c.marked_timer, 0.25)

    def update(self, dt):
        state = self.read_state()
        self.detect_stagnation_or_completion(state, dt)
        self.choose_behavior(state, dt)
        self.configure_modifiers()
        self.update_cursor(state, dt)
        self.create_visible_actions(state, dt)


ai = AIController()


# -----------------------------
# Colony state and physics
# -----------------------------

def compute_colony_state():
    global colony_center, colony_radius, colony_height, avg_speed, packing_score, boundary_cells

    if not cells:
        colony_center = vector(0, 0, 0)
        colony_radius = 0.5
        colony_height = 0.9
        avg_speed = 0.0
        packing_score = 0.0
        boundary_cells = []
        return

    sx = sy = sz = 0.0
    for c in cells:
        sx += c.pos.x
        sy += c.pos.y
        sz += c.pos.z
    center = vector(sx / len(cells), sy / len(cells), 0)
    colony_center = center

    max_r = 0.5
    max_h = 0.8
    total_speed = 0.0
    neighbor_sum = 0.0

    for i, c in enumerate(cells):
        rr = mag(xy(c.pos - center)) + c.radius
        max_r = max(max_r, rr)
        max_h = max(max_h, c.pos.z + c.radius)
        total_speed += mag(c.vel)

        local_neighbors = 0
        for j, other in enumerate(cells):
            if i == j:
                continue
            if mag(c.pos - other.pos) < BASE_RADIUS * 2.45:
                local_neighbors += 1
        neighbor_sum += local_neighbors

    colony_radius = max_r
    colony_height = max_h
    avg_speed = total_speed / max(1, len(cells))
    packing_score = neighbor_sum / max(1, len(cells))

    boundary_cells = []
    for c in cells:
        radial = mag(xy(c.pos - center))
        if radial > 0.82 * colony_radius or c.pos.z > 0.82 * colony_height:
            boundary_cells.append(c)


def divide_cell(parent):
    if len(cells) >= max_cells:
        return

    radial = xy(parent.pos - colony_center)
    if mag(radial) < 0.15:
        radial_dir = random_unit_upward()
    else:
        radial_dir = safe_norm(radial)

    crowd_bias = clamp((packing_score - 3.0) / 5.0, 0.0, 1.0)
    outward = safe_norm(radial_dir + random_unit() * 0.35 + vector(0, 0, 0.45 + 1.2 * crowd_bias))

    if parent.boundary:
        direction = safe_norm(radial_dir * 0.9 + random_unit_upward() * 0.5)
    else:
        direction = outward

    child_pos = parent.pos + direction * parent.radius * 0.72
    child_pos.z = max(child_pos.z, MIN_RADIUS + 0.03)

    child = Cell(
        child_pos,
        radius=MIN_RADIUS * random.uniform(0.9, 1.1),
        target_radius=BASE_RADIUS * random.uniform(0.96, 1.05),
        parent_id=parent.id
    )
    child.generation = parent.generation + 1

    push = direction * random.uniform(0.45, 0.8)
    child.vel = parent.vel + push
    parent.vel -= push * 0.52
    parent.timer = random.uniform(5.8, 10.8)
    parent.age = random.uniform(0.0, 1.2)

    cells.append(child)

    for _ in range(10):
        vel = direction * random.uniform(0.2, 1.0) + random_unit() * random.uniform(0.15, 0.6)
        particles.append(PulseParticle(parent.pos, vel, vector(0.62, 1.0, 0.88), radius=0.035, life=random.uniform(0.6, 1.25)))


def try_divisions():
    if len(cells) >= max_cells:
        return

    candidates = []
    for c in cells:
        if c.age > c.timer / max(0.2, ai.division_multiplier) and c.radius > c.target_radius * 0.88:
            # Crowded inner cells divide more slowly, boundary cells divide more freely.
            crowd_penalty = 0.0
            if c.inner and packing_score > 4.0:
                crowd_penalty = 0.35
            chance = 0.65 - crowd_penalty
            if random.random() < chance:
                candidates.append(c)

    random.shuffle(candidates)
    max_divs = 1
    if len(cells) < 18:
        max_divs = 2
    elif ai.mode == "NURTURE" and random.random() < 0.35:
        max_divs = 2

    for c in candidates[:max_divs]:
        if len(cells) < max_cells:
            divide_cell(c)


def apply_physics():
    if not cells:
        return

    # Packing factor decreases over time: inner cells become more tightly packed.
    time_packing = 1.04 - 0.13 * clamp(round_time / 95.0, 0.0, 1.0)
    packing_factor = clamp(time_packing - ai.packing_bonus, 0.84, 1.08)

    for c in cells:
        c.force = vector(0, 0, -0.20 * c.mass)
        c.force += xy(colony_center - c.pos) * 0.012
        c.force += ai.apply_force_to_cell(c, ai.read_state())

    n = len(cells)
    neighbor_counts = [0 for _ in cells]

    for i in range(n):
        ci = cells[i]
        for j in range(i + 1, n):
            cj = cells[j]
            delta = ci.pos - cj.pos
            dist = mag(delta)
            if dist < 1e-6:
                delta = random_unit() * 0.001
                dist = mag(delta)
            normal = delta / dist

            desired = (ci.radius + cj.radius) * packing_factor
            contact = ci.radius + cj.radius
            adhesion_range = contact * 1.38

            if dist < adhesion_range:
                neighbor_counts[i] += 1
                neighbor_counts[j] += 1

            if dist < desired:
                overlap = desired - dist
                relv = dot(ci.vel - cj.vel, normal)
                f = normal * (SOFT_SPRING * overlap - 1.2 * relv)
                ci.force += f
                cj.force -= f
            elif dist < adhesion_range:
                stretch = dist - desired
                f = -normal * (ADHESION * ai.adhesion_multiplier * stretch)
                ci.force += f
                cj.force -= f

    for idx, c in enumerate(cells):
        density = neighbor_counts[idx]
        radial = mag(xy(c.pos - colony_center))
        center_factor = 1.0 - clamp(radial / max(colony_radius, 0.1), 0.0, 1.0)

        if density > 4:
            # Dome-forming upward rearrangement in crowded central cells.
            c.force += vector(0, 0, 0.055 * (density - 3) * (0.3 + center_factor))

        # Soft world limit; cells spill less far than the floor.
        if radial > WORLD_RADIUS_LIMIT:
            c.force += safe_norm(xy(colony_center - c.pos)) * (radial - WORLD_RADIUS_LIMIT) * 0.35

    for c in cells:
        acc = c.force / max(c.mass, 0.05)
        c.vel += acc * DT
        c.vel *= DAMPING

        # Extra damping for dense inner cells to show settled packing over time.
        if c.inner:
            c.vel *= 0.992

        c.pos += c.vel * DT

        # Stationary flat surface collision.
        if c.pos.z < FLOOR_Z + c.radius:
            c.pos.z = FLOOR_Z + c.radius
            if c.vel.z < 0:
                c.vel.z *= -0.18
            c.vel.x *= 0.965
            c.vel.y *= 0.965

        c.grow()


def update_visuals():
    compute_colony_state()
    boundary_dome.set_opacity(ai.wrap_opacity)
    boundary_dome.update(colony_center, colony_radius + 0.18, colony_height + 0.18)

    for c in cells:
        c.selected = False
        c.update_visual(colony_center, colony_radius, ai.mode)

    if cells:
        nearest = min(cells, key=lambda cell: mag(cell.pos - ai.cursor.pos))
        if mag(nearest.pos - ai.cursor.pos) < 1.2:
            nearest.selected = True


def update_particles_and_links():
    global particles, links
    particles = [p for p in particles if p.update(DT)]
    links = [l for l in links if l.update(DT)]


# -----------------------------
# Reset and loop system
# -----------------------------

def clear_scene_objects():
    global particles, links
    for c in cells:
        c.destroy()
    for p in particles:
        p.obj.visible = False
    for l in links:
        l.obj.visible = False
    particles = []
    links = []


def reset_simulation():
    global cells, sim_time, round_time, round_index, cell_id_counter
    global colony_center, colony_radius, colony_height, avg_speed, packing_score, boundary_cells

    clear_scene_objects()
    cells = []
    particles.clear()
    links.clear()

    round_index += 1
    round_time = 0.0
    cell_id_counter = 0

    start = Cell(vector(0, 0, BASE_RADIUS), radius=BASE_RADIUS * 0.92, target_radius=BASE_RADIUS)
    start.timer = 2.0
    cells.append(start)

    colony_center = vector(0, 0, 0)
    colony_radius = 0.6
    colony_height = 0.9
    avg_speed = 0.0
    packing_score = 0.0
    boundary_cells = []

    ai.reset_internal()

    for _ in range(24):
        particles.append(PulseParticle(vector(0, 0, 0.7), random_unit_upward() * random.uniform(0.5, 2.2), vector(0.6, 1.0, 0.85), radius=0.035, life=random.uniform(0.8, 1.6)))


# -----------------------------
# Human keyboard control
# -----------------------------

help_text = """
Controls:
SPACE pause/resume | A toggle AI | H human override | N next AI mode | R reset
1 observe | 2 nurture | 3 compact | 4 orbit | 5 dip | 6 wrap | 7 artist | 8 chaos
Arrow keys / W,S move AI cursor offset | C chaos pulse | M mark boundary | +,- max cells
"""

scene.append_to_caption(help_text)
status_text = wtext(text="\nStarting...\n")


def mark_boundary():
    for c in boundary_cells:
        c.marked_timer = random.uniform(0.8, 2.0)


def chaos_pulse():
    if not cells:
        return
    for c in cells:
        d = safe_norm(c.pos - colony_center + random_unit() * 0.4)
        c.vel += d * random.uniform(0.25, 1.15)
        if random.random() < 0.3:
            c.marked_timer = 0.5
    for _ in range(35):
        particles.append(PulseParticle(colony_center + vector(0, 0, colony_height * 0.6), random_unit() * random.uniform(0.8, 3.2), vector(1.0, 0.42, 0.16), radius=0.04, life=random.uniform(0.5, 1.2)))


def on_keydown(evt):
    global paused, max_cells
    k = evt.key

    if k == ' ':
        paused = not paused
    elif k in ['a', 'A']:
        ai.enabled = not ai.enabled
    elif k in ['h', 'H']:
        ai.human_override = not ai.human_override
    elif k in ['r', 'R']:
        reset_simulation()
    elif k in ['n', 'N']:
        ai.next_mode(manual=True)
    elif k == '1':
        ai.set_mode("OBSERVE", manual=True)
    elif k == '2':
        ai.set_mode("NURTURE", manual=True)
    elif k == '3':
        ai.set_mode("COMPACT", manual=True)
    elif k == '4':
        ai.set_mode("ORBIT", manual=True)
    elif k == '5':
        ai.set_mode("DIP", manual=True)
    elif k == '6':
        ai.set_mode("WRAP", manual=True)
    elif k == '7':
        ai.set_mode("ARTIST", manual=True)
    elif k == '8':
        ai.set_mode("CHAOS", manual=True)
    elif k in ['c', 'C']:
        chaos_pulse()
    elif k in ['m', 'M']:
        mark_boundary()
    elif k in ['+', '=']:
        max_cells = min(260, max_cells + 10)
    elif k in ['-', '_']:
        max_cells = max(20, max_cells - 10)

    # Human can still steer the AI cursor even while AI is automatic.
    step = 0.45
    if k == 'left':
        ai.cursor_manual_offset.x -= step
    elif k == 'right':
        ai.cursor_manual_offset.x += step
    elif k == 'up':
        ai.cursor_manual_offset.y += step
    elif k == 'down':
        ai.cursor_manual_offset.y -= step
    elif k in ['w', 'W']:
        ai.cursor_manual_offset.z += step
    elif k in ['s', 'S']:
        ai.cursor_manual_offset.z -= step
    elif k in ['x', 'X']:
        ai.cursor_manual_offset = vector(0, 0, 0)


scene.bind('keydown', on_keydown)


# -----------------------------
# Status display
# -----------------------------

def update_status():
    reset_info = ""
    if ai.reset_countdown >= 0:
        reset_info = " | reset in %.1fs" % max(0, ai.reset_countdown)

    status_text.text = (
        "\nRound: %d | Cells: %d/%d | Mode: %s | AI: %s | Override: %s | Paused: %s%s\n"
        "Radius: %.2f | Height: %.2f | Packing: %.2f | Avg speed: %.3f | Stagnant: %.1fs\n"
        % (
            round_index,
            len(cells),
            max_cells,
            ai.mode,
            "on" if ai.enabled else "off",
            "on" if ai.human_override else "off",
            "yes" if paused else "no",
            reset_info,
            colony_radius,
            colony_height,
            packing_score,
            avg_speed,
            ai.stagnant_timer
        )
    )


# -----------------------------
# Initialize and run
# -----------------------------

round_index = 0
reset_simulation()

status_timer = 0.0
csv_logger = SimulationCSVLogger()

while True:
    rate(60)

    if not paused:
        sim_time += DT
        round_time += DT

        compute_colony_state()
        ai.update(DT)
        try_divisions()
        apply_physics()
        update_visuals()
        update_particles_and_links()

    else:
        # Cursor still glows while paused.
        ai.cursor.opacity = 0.22 + 0.08 * math.sin(sim_time * 3.0)

    status_timer += DT
    if status_timer > 0.18:
        status_timer = 0.0
        update_status()

    csv_logger.sample(sim_time)
    if csv_logger.reached_end(sim_time):
        csv_logger.close()
        break
