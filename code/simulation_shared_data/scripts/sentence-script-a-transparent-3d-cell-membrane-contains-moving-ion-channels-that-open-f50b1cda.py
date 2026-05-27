from vpython import *
import random as pyrandom
import math
from collections import deque
import csv
import json
import os
import time as pytime
import atexit
from pathlib import Path

# ============================================================
# 3D Cell Membrane + Moving Ion Channels + Expressive AI
# Self-contained VPython simulation
# ============================================================

# -----------------------------
# Scene styling
# -----------------------------
scene.title = "Cell Membrane with Moving Ion Channels, Drifting Ions, Trails, Meter, and AI Controller"
scene.width = 1200
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-1.8, -0.8, -1.6)
scene.up = vector(0, 1, 0)
scene.range = 11.5
scene.center = vector(0, 0, 0)

scene.caption = """
Controls:
  SPACE = pause/resume        A = AI on/off        M = next AI mode        R = reset round
  O = open all channels       C = close all        1-9/0 = toggle channel
  T = toggle ion trails       P = spill/spawn ions
  I = pump inward             U = pump outward     B = balance mode
  H = human override timer    F = clear trails
"""

# -----------------------------
# Constants
# -----------------------------
R = 5.0                         # membrane radius
MEMBRANE_THICKNESS = 0.85
WORLD_R = 9.2
CHANNEL_COUNT = 10
CHANNEL_LENGTH = 1.45
CHANNEL_RADIUS = 0.34
CHANNEL_APERTURE = 0.95
ION_RADIUS = 0.115
INITIAL_IONS = 64
MAX_IONS = 95
DT = 0.020
COLLISION_INTERVAL = 3

ION_PLUS_COLOR = vector(1.0, 0.42, 0.22)
ION_MINUS_COLOR = vector(0.16, 0.48, 1.0)
ION_MARK_COLOR = vector(0.78, 0.18, 1.0)
OPEN_COLOR = vector(0.18, 0.85, 0.42)
CLOSED_COLOR = vector(1.0, 0.32, 0.20)
REST_COLOR = vector(0.32, 0.68, 0.95)


# -----------------------------
# CSV logging support for core sentence branching web app
# -----------------------------
CSV_RUN_ID = os.environ.get("SIMULATION_CSV_RUN_ID") or os.environ.get("CSV_RUN_ID") or f"ion_channels_{int(pytime.time())}"
CSV_OUTPUT_DIR = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_HZ = float(os.environ.get("SIMULATION_CSV_SAMPLE_HZ", "10"))
CSV_SAMPLE_INTERVAL = 1.0 / max(0.1, CSV_SAMPLE_HZ)

_csv_file = None
_csv_writer = None
_csv_path = None
_csv_meta_path = None
_csv_last_sample_time = -1e9
_csv_wall_start = pytime.time()
_csv_rows_written = 0
_csv_closed = False

CSV_FIELDS = [
    "run_id", "row_index", "wall_elapsed_s", "sim_elapsed_s", "frame", "round",
    "paused", "trails_enabled", "ai_enabled", "ai_mode", "ai_time_in_mode_s",
    "ai_stagnant_time_s", "ai_completion_time_s", "ai_human_override_s",
    "ion_count", "inside_count", "outside_count", "inside_fraction", "outside_fraction",
    "open_channel_count", "closed_channel_count", "total_crossings", "attached_ion_count",
    "marked_ion_count", "avg_ion_speed", "max_ion_speed", "mean_radius", "mean_inside_radius", "mean_outside_radius",
    "global_pressure_bias", "global_swirl_strength", "electric_field_x", "electric_field_y", "electric_field_z",
    "channel_open_pattern", "channel_attached_counts",
    "wand_x", "wand_y", "wand_z",
    "sample_note"
]

def _csv_resolve_paths():
    global _csv_path, _csv_meta_path
    fallback = os.environ.get("SIM_STATE_CSV_PATH")
    if CSV_OUTPUT_DIR:
        out_dir = Path(CSV_OUTPUT_DIR).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        _csv_path = out_dir / f"{CSV_RUN_ID}_ion_channels.csv"
    elif fallback:
        _csv_path = Path(fallback).expanduser()
        _csv_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path.cwd() / "csv_runs"
        out_dir.mkdir(parents=True, exist_ok=True)
        _csv_path = out_dir / f"{CSV_RUN_ID}_ion_channels.csv"
    _csv_meta_path = _csv_path.with_suffix(".metadata.json")


def csv_logger_start():
    global _csv_file, _csv_writer
    _csv_resolve_paths()
    _csv_file = open(_csv_path, "w", newline="", encoding="utf-8")
    _csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDS)
    _csv_writer.writeheader()
    _csv_file.flush()
    meta = {
        "run_id": CSV_RUN_ID,
        "simulation": "Cell Membrane with Moving Ion Channels, Drifting Ions, Trails, Meter, and AI Controller",
        "csv_path": str(_csv_path),
        "sample_hz": CSV_SAMPLE_HZ,
        "run_seconds": CSV_RUN_SECONDS,
        "default_run_seconds": 60,
        "environment": {
            "SIMULATION_CSV_OUTPUT_DIR": CSV_OUTPUT_DIR,
            "SIMULATION_CSV_RUN_ID": CSV_RUN_ID,
            "SIMULATION_CSV_RUN_SECONDS": CSV_RUN_SECONDS,
            "SIMULATION_CSV_SAMPLE_HZ": CSV_SAMPLE_HZ,
            "SIM_STATE_CSV_PATH": os.environ.get("SIM_STATE_CSV_PATH"),
        },
        "fields": CSV_FIELDS,
    }
    with open(_csv_meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def _safe_vec_components(v):
    try:
        return float(v.x), float(v.y), float(v.z)
    except Exception:
        return 0.0, 0.0, 0.0


def csv_collect_state(sample_note=""):
    global _csv_rows_written
    inside = sum(1 for ion in ions if ion.is_inside())
    outside = len(ions) - inside
    total = max(1, len(ions))
    speeds = [mag(ion.vel) for ion in ions]
    radii = [mag(ion.pos) for ion in ions]
    inside_radii = [mag(ion.pos) for ion in ions if ion.is_inside()]
    outside_radii = [mag(ion.pos) for ion in ions if not ion.is_inside()]
    open_count = sum(1 for ch in channels if ch.open)
    attached = sum(1 for ion in ions if ion.attached_channel is not None)
    marked = sum(1 for ion in ions if ion.marked)
    ex, ey, ez = _safe_vec_components(global_electric_field)
    wx, wy, wz = _safe_vec_components(ai.wand.pos if "ai" in globals() else vector(0, 0, 0))
    wall_elapsed = pytime.time() - _csv_wall_start
    sim_elapsed = frame_count * DT
    row = {
        "run_id": CSV_RUN_ID,
        "row_index": _csv_rows_written,
        "wall_elapsed_s": round(wall_elapsed, 6),
        "sim_elapsed_s": round(sim_elapsed, 6),
        "frame": frame_count,
        "round": round_number,
        "paused": int(paused),
        "trails_enabled": int(trails_enabled),
        "ai_enabled": int(ai.enabled),
        "ai_mode": ai.mode,
        "ai_time_in_mode_s": round(ai.time_in_mode, 6),
        "ai_stagnant_time_s": round(ai.stagnant_time, 6),
        "ai_completion_time_s": round(ai.completion_time, 6),
        "ai_human_override_s": round(ai.human_override_timer, 6),
        "ion_count": len(ions),
        "inside_count": inside,
        "outside_count": outside,
        "inside_fraction": round(inside / total, 6),
        "outside_fraction": round(outside / total, 6),
        "open_channel_count": open_count,
        "closed_channel_count": len(channels) - open_count,
        "total_crossings": total_crossings,
        "attached_ion_count": attached,
        "marked_ion_count": marked,
        "avg_ion_speed": round(sum(speeds) / max(1, len(speeds)), 6),
        "max_ion_speed": round(max(speeds) if speeds else 0.0, 6),
        "mean_radius": round(sum(radii) / max(1, len(radii)), 6),
        "mean_inside_radius": round(sum(inside_radii) / max(1, len(inside_radii)), 6),
        "mean_outside_radius": round(sum(outside_radii) / max(1, len(outside_radii)), 6),
        "global_pressure_bias": round(global_pressure_bias, 6),
        "global_swirl_strength": round(global_swirl_strength, 6),
        "electric_field_x": round(ex, 6),
        "electric_field_y": round(ey, 6),
        "electric_field_z": round(ez, 6),
        "channel_open_pattern": "".join("1" if ch.open else "0" for ch in channels),
        "channel_attached_counts": ";".join(str(ch.attached_count) for ch in channels),
        "wand_x": round(wx, 6),
        "wand_y": round(wy, 6),
        "wand_z": round(wz, 6),
        "sample_note": sample_note,
    }
    return row


def csv_logger_sample(force=False, sample_note=""):
    global _csv_last_sample_time, _csv_rows_written
    if _csv_writer is None:
        return
    elapsed = pytime.time() - _csv_wall_start
    if not force and elapsed - _csv_last_sample_time < CSV_SAMPLE_INTERVAL:
        return
    _csv_last_sample_time = elapsed
    row = csv_collect_state(sample_note)
    _csv_writer.writerow(row)
    _csv_rows_written += 1
    if _csv_rows_written % 10 == 0:
        _csv_file.flush()


def csv_logger_should_stop():
    return CSV_RUN_SECONDS > 0 and (pytime.time() - _csv_wall_start) >= CSV_RUN_SECONDS


def csv_logger_close():
    global _csv_closed
    if _csv_closed:
        return
    _csv_closed = True
    try:
        csv_logger_sample(force=True, sample_note="final")
    except Exception:
        pass
    try:
        if _csv_file is not None:
            _csv_file.flush()
            _csv_file.close()
    except Exception:
        pass

atexit.register(csv_logger_close)

# -----------------------------
# Global simulation state
# -----------------------------
ions = []
channels = []
frame_count = 0
paused = False
trails_enabled = True
round_number = 1
total_crossings = 0
last_counts = (0, 0)
global_pressure_bias = 0.0       # negative = inward, positive = outward
global_swirl_strength = 0.0
global_electric_field = vector(0, 0, 0)
completion_pending = False
completion_timer = 0.0

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
    z = pyrandom.uniform(-1, 1)
    a = pyrandom.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), r * math.sin(a), z)

def random_inside_position(scale=0.88):
    d = random_unit()
    radius = R * scale * (pyrandom.random() ** (1 / 3))
    return d * radius

def random_outside_position():
    d = random_unit()
    radius = pyrandom.uniform(R + 1.1, WORLD_R * 0.88)
    return d * radius

def fibonacci_directions(n):
    dirs = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2 if n > 1 else 0
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        dirs.append(vector(x, y, z))
    return dirs

def tangent_swirl(pos, strength):
    if strength == 0:
        return vector(0, 0, 0)
    axis = vector(0, 1, 0)
    radial = safe_norm(pos)
    tang = cross(axis, radial)
    if mag(tang) < 0.01:
        tang = cross(vector(1, 0, 0), radial)
    return safe_norm(tang) * strength

def angular_surface_distance(a, b):
    aa = safe_norm(a)
    bb = safe_norm(b)
    c = clamp(dot(aa, bb), -1, 1)
    return R * math.acos(c)

def dispose_obj(obj):
    try:
        obj.clear_trail()
    except Exception:
        pass
    obj.visible = False

# -----------------------------
# Membrane visual
# -----------------------------
membrane = sphere(
    pos=vector(0, 0, 0),
    radius=R,
    color=vector(0.70, 0.88, 1.0),
    opacity=0.18,
    shininess=0.65
)

inner_glow = sphere(
    pos=vector(0, 0, 0),
    radius=R * 0.985,
    color=vector(0.84, 0.96, 1.0),
    opacity=0.055
)

def make_ring_xy(radius, z=0, col=vector(0.52, 0.72, 0.92), opacity=0.35):
    pts = []
    for i in range(145):
        a = 2 * math.pi * i / 144
        pts.append(vector(radius * math.cos(a), radius * math.sin(a), z))
    return curve(pos=pts, color=col, radius=0.012, opacity=opacity)

equator_xy = make_ring_xy(R)
equator_xz = curve(
    pos=[vector(R * math.cos(2 * math.pi * i / 144), 0, R * math.sin(2 * math.pi * i / 144)) for i in range(145)],
    color=vector(0.52, 0.72, 0.92),
    radius=0.012,
    opacity=0.35
)
equator_yz = curve(
    pos=[vector(0, R * math.cos(2 * math.pi * i / 144), R * math.sin(2 * math.pi * i / 144)) for i in range(145)],
    color=vector(0.52, 0.72, 0.92),
    radius=0.012,
    opacity=0.35
)

# -----------------------------
# Labels and meter
# -----------------------------
title_label = label(
    pos=vector(0, 6.55, 0),
    text="Transparent Cell Membrane",
    height=17,
    color=vector(0.12, 0.25, 0.38),
    box=False,
    opacity=0
)

status_label = label(
    pos=vector(0, -6.35, 0),
    text="",
    height=13,
    color=vector(0.08, 0.18, 0.28),
    box=False,
    opacity=0
)

ai_label = label(
    pos=vector(0, 7.25, 0),
    text="",
    height=13,
    color=vector(0.35, 0.12, 0.55),
    box=False,
    opacity=0
)

meter_back = box(
    pos=vector(-8.55, 0, 0),
    size=vector(0.12, 5.2, 0.22),
    color=vector(0.82, 0.88, 0.94),
    opacity=0.42
)

inside_bar = box(
    pos=vector(-8.95, -2.5, 0),
    size=vector(0.34, 0.01, 0.34),
    color=vector(0.16, 0.48, 1.0),
    opacity=0.78
)

outside_bar = box(
    pos=vector(-8.25, -2.5, 0),
    size=vector(0.34, 0.01, 0.34),
    color=vector(1.0, 0.55, 0.18),
    opacity=0.78
)

meter_inside_label = label(
    pos=vector(-9.2, 2.95, 0),
    text="inside",
    height=10,
    color=vector(0.13, 0.32, 0.65),
    box=False,
    opacity=0
)

meter_outside_label = label(
    pos=vector(-8.05, 2.95, 0),
    text="outside",
    height=10,
    color=vector(0.72, 0.32, 0.08),
    box=False,
    opacity=0
)

meter_count_label = label(
    pos=vector(-8.6, -3.15, 0),
    text="",
    height=10,
    color=vector(0.12, 0.18, 0.24),
    box=False,
    opacity=0
)

# -----------------------------
# Ion channel class
# -----------------------------
class IonChannel:
    def __init__(self, idx, direction):
        self.idx = idx
        self.n = safe_norm(direction)
        self.open = pyrandom.random() < 0.55
        self.flash = 0.0
        self.pulse_phase = pyrandom.random() * 2 * math.pi
        self.attached_count = 0

        self.body = cylinder(
            pos=self.n * (R - CHANNEL_LENGTH / 2),
            axis=self.n * CHANNEL_LENGTH,
            radius=CHANNEL_RADIUS,
            color=OPEN_COLOR if self.open else CLOSED_COLOR,
            opacity=0.45 if self.open else 0.64,
            shininess=0.85
        )

        self.pore_core = cylinder(
            pos=self.n * (R - CHANNEL_LENGTH / 2 + 0.04),
            axis=self.n * (CHANNEL_LENGTH - 0.08),
            radius=CHANNEL_RADIUS * 0.48,
            color=vector(0.92, 1.0, 0.92),
            opacity=0.18 if self.open else 0.03
        )

        self.gate = cylinder(
            pos=self.n * R,
            axis=self.n * 0.105,
            radius=CHANNEL_RADIUS * 1.22,
            color=CLOSED_COLOR,
            opacity=0 if self.open else 0.82,
            shininess=0.4
        )

        self.halo = ring(
            pos=self.n * (R + 0.42),
            axis=self.n,
            radius=CHANNEL_RADIUS * 1.55,
            thickness=0.025,
            color=OPEN_COLOR if self.open else CLOSED_COLOR,
            opacity=0.38
        )

        self.lbl = label(
            pos=self.n * (R + 0.82),
            text=str((idx + 1) % 10),
            height=9,
            color=vector(0.1, 0.18, 0.24),
            box=False,
            opacity=0
        )

        self.update_visual(0)

    def set_open(self, value):
        self.open = bool(value)
        self.update_visual(0)

    def toggle(self):
        self.set_open(not self.open)

    def transfer_flash(self):
        self.flash = 1.0

    def update_visual(self, dt):
        self.pulse_phase += dt * 2.0
        self.flash = max(0.0, self.flash - dt * 2.2)
        breathe = 1.0 + 0.07 * math.sin(self.pulse_phase)

        if self.open:
            base_col = OPEN_COLOR
            self.body.color = base_col + vector(0.45, 0.35, 0.15) * self.flash
            self.body.opacity = 0.34 + 0.25 * self.flash
            self.body.radius = CHANNEL_RADIUS * (1.06 + 0.06 * breathe + 0.12 * self.flash)
            self.pore_core.opacity = 0.25 + 0.35 * self.flash
            self.gate.opacity = 0.0
            self.halo.color = base_col + vector(0.45, 0.25, 0.05) * self.flash
            self.halo.opacity = 0.35 + 0.35 * self.flash
            self.halo.radius = CHANNEL_RADIUS * (1.55 + 0.14 * math.sin(self.pulse_phase))
        else:
            base_col = CLOSED_COLOR
            self.body.color = base_col
            self.body.opacity = 0.55
            self.body.radius = CHANNEL_RADIUS * (0.92 + 0.03 * breathe)
            self.pore_core.opacity = 0.03
            self.gate.opacity = 0.78
            self.gate.color = CLOSED_COLOR
            self.halo.color = CLOSED_COLOR
            self.halo.opacity = 0.30
            self.halo.radius = CHANNEL_RADIUS * 1.32

    def surface_point(self):
        return self.n * R

# -----------------------------
# Ion particle class
# -----------------------------
class Ion:
    def __init__(self, pos, charge=None):
        self.charge = charge if charge is not None else (1 if pyrandom.random() < 0.5 else -1)
        self.pos = vector(pos)
        self.vel = random_unit() * pyrandom.uniform(0.25, 0.85)
        self.birth_time = 0.0
        self.attached_channel = None
        self.attach_timer = 0.0
        self.attach_side = 1
        self.marked = False
        self.recent_transfer_timer = 0.0
        self.trail_retain = 95

        col = ION_PLUS_COLOR if self.charge > 0 else ION_MINUS_COLOR
        self.obj = sphere(
            pos=self.pos,
            radius=ION_RADIUS,
            color=col,
            emissive=False,
            make_trail=trails_enabled,
            retain=self.trail_retain,
            trail_radius=0.018,
            trail_color=col * 0.8 + vector(0.1, 0.1, 0.1)
        )

    def set_marked(self, value=True):
        self.marked = bool(value)
        if self.marked:
            self.obj.color = ION_MARK_COLOR
            self.obj.trail_color = ION_MARK_COLOR
            self.obj.radius = ION_RADIUS * 1.22
            self.obj.emissive = True
        else:
            col = ION_PLUS_COLOR if self.charge > 0 else ION_MINUS_COLOR
            self.obj.color = col
            self.obj.trail_color = col * 0.8 + vector(0.1, 0.1, 0.1)
            self.obj.radius = ION_RADIUS
            self.obj.emissive = False

    def clear_trail(self):
        try:
            self.obj.clear_trail()
        except Exception:
            pass

    def dispose(self):
        dispose_obj(self.obj)

    def is_inside(self):
        return mag(self.pos) < R

    def update(self, dt):
        global total_crossings

        self.recent_transfer_timer = max(0, self.recent_transfer_timer - dt)

        if self.attached_channel is not None:
            ch = self.attached_channel
            self.attach_timer -= dt
            wobble = tangent_swirl(ch.n + vector(0.03, 0.01, 0.02), 0.05 * math.sin(frame_count * 0.2))
            self.pos = ch.n * (R + self.attach_side * 0.21) + wobble
            self.vel = vector(0, 0, 0)
            self.obj.pos = self.pos

            if self.attach_timer <= 0 or ch.open:
                outward = ch.n * self.attach_side
                tang = tangent_swirl(ch.n, pyrandom.uniform(0.12, 0.42))
                self.vel = outward * pyrandom.uniform(0.45, 0.9) + tang
                self.attached_channel = None
                self.attach_timer = 0
            return

        old_pos = vector(self.pos)
        old_r = mag(old_pos)

        radial = safe_norm(self.pos)
        brownian = random_unit() * pyrandom.uniform(0.0, 0.34)
        pressure = radial * global_pressure_bias
        electric = global_electric_field * self.charge
        swirl = tangent_swirl(self.pos, global_swirl_strength)

        channel_pull = vector(0, 0, 0)
        near_membrane = abs(old_r - R) < 2.0
        if near_membrane:
            nearest = find_nearest_channel_dir(radial)
            if nearest is not None:
                ch, surf_dist = nearest
                if ch.open and surf_dist < CHANNEL_APERTURE * 2.2:
                    target = ch.surface_point()
                    tangent_pull = target - radial * R
                    channel_pull += safe_norm(tangent_pull) * clamp((CHANNEL_APERTURE * 2.2 - surf_dist), 0, 1.5) * 0.42
                    channel_pull += ch.n * global_pressure_bias * 0.35

        if self.marked:
            swirl *= 1.45
            brownian *= 1.25

        accel = brownian + pressure + electric + swirl + channel_pull
        self.vel += accel * dt
        self.vel *= 0.992

        speed = mag(self.vel)
        if speed > 2.8:
            self.vel = safe_norm(self.vel) * 2.8

        new_pos = self.pos + self.vel * dt
        new_r = mag(new_pos)

        crossed_membrane = (old_r < R and new_r >= R) or (old_r >= R and new_r < R)

        if crossed_membrane:
            direction = safe_norm(new_pos if mag(new_pos) > 0.01 else old_pos)
            selected = find_channel_for_crossing(direction)

            if selected is not None:
                ch, dist_to_channel = selected
                if ch.open:
                    ch.transfer_flash()
                    self.recent_transfer_timer = 0.8
                    total_crossings += 1
                    if pyrandom.random() < 0.28:
                        self.set_marked(True)
                    new_pos += direction * 0.10
                    self.vel += direction * global_pressure_bias * 0.32
                else:
                    # closed pore: attach briefly or bounce
                    side = -1 if old_r < R else 1
                    if dist_to_channel < CHANNEL_APERTURE * 0.82 and pyrandom.random() < 0.72:
                        self.attached_channel = ch
                        self.attach_side = side
                        self.attach_timer = pyrandom.uniform(0.24, 0.74)
                        ch.attached_count += 1
                        self.vel = vector(0, 0, 0)
                        new_pos = ch.n * (R + side * 0.21)
                    else:
                        n = direction
                        self.vel = self.vel - 2 * dot(self.vel, n) * n
                        self.vel += tangent_swirl(n, pyrandom.uniform(-0.18, 0.18))
                        new_pos = n * (R - 0.06 if old_r < R else R + 0.06)
            else:
                n = direction
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel += tangent_swirl(n, pyrandom.uniform(-0.12, 0.12))
                new_pos = n * (R - 0.06 if old_r < R else R + 0.06)

        if mag(new_pos) > WORLD_R:
            n = safe_norm(new_pos)
            new_pos = n * WORLD_R
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.84

        self.pos = new_pos
        self.obj.pos = self.pos

# -----------------------------
# Channel lookup
# -----------------------------
def find_channel_for_crossing(direction):
    best = None
    best_dist = 1e9
    for ch in channels:
        d = angular_surface_distance(direction, ch.n)
        if d < best_dist:
            best_dist = d
            best = ch
    if best is not None and best_dist <= CHANNEL_APERTURE:
        return best, best_dist
    return None

def find_nearest_channel_dir(direction):
    best = None
    best_dist = 1e9
    for ch in channels:
        d = angular_surface_distance(direction, ch.n)
        if d < best_dist:
            best_dist = d
            best = ch
    if best is None:
        return None
    return best, best_dist

# -----------------------------
# Create channels
# -----------------------------
for idx, d in enumerate(fibonacci_directions(CHANNEL_COUNT)):
    channels.append(IonChannel(idx, d))

# -----------------------------
# AI controller with multiple modes
# -----------------------------
class MembraneAI:
    def __init__(self):
        self.enabled = True
        self.mode = "BALANCE"
        self.modes = [
            "BALANCE",
            "PUMP_IN",
            "PUMP_OUT",
            "MIX",
            "PULSE",
            "ORBIT",
            "ARTIST",
            "CHAOS",
            "CAREFUL",
            "RESET"
        ]
        self.mode_index = 0
        self.time_in_mode = 0.0
        self.mode_duration = 12.0
        self.action_timer = 0.0
        self.switch_cooldown = 0.0
        self.history = deque(maxlen=18)
        self.history_timer = 0.0
        self.stagnant_time = 0.0
        self.completion_time = 0.0
        self.human_override_timer = 0.0
        self.focus_index = 0
        self.phase = 0.0
        self.chaos_vector = random_unit() * 0.3
        self.recent_modes = deque(maxlen=4)
        self.reset_wait = 0.0

        self.wand = sphere(
            pos=vector(0, 0, 0),
            radius=0.18,
            color=vector(0.75, 0.22, 1.0),
            emissive=True,
            make_trail=True,
            retain=80,
            trail_radius=0.018,
            trail_color=vector(0.70, 0.25, 1.0)
        )
        self.wand_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=0.32,
            thickness=0.025,
            color=vector(0.75, 0.22, 1.0),
            opacity=0.65
        )

    def read_state(self):
        inside = sum(1 for ion in ions if ion.is_inside())
        outside = len(ions) - inside
        avg_speed = sum(mag(ion.vel) for ion in ions) / max(1, len(ions))
        open_count = sum(1 for ch in channels if ch.open)
        attached = sum(1 for ion in ions if ion.attached_channel is not None)
        marked = sum(1 for ion in ions if ion.marked)
        return {
            "inside": inside,
            "outside": outside,
            "total": len(ions),
            "avg_speed": avg_speed,
            "open_count": open_count,
            "attached": attached,
            "marked": marked,
            "crossings": total_crossings,
            "round": round_number
        }

    def set_mode(self, mode):
        if mode not in self.modes:
            return
        self.mode = mode
        self.mode_index = self.modes.index(mode)
        self.time_in_mode = 0.0
        self.mode_duration = pyrandom.uniform(8.0, 17.0)
        if mode == "CHAOS":
            self.mode_duration = pyrandom.uniform(5.0, 10.0)
        if mode == "CAREFUL":
            self.mode_duration = pyrandom.uniform(10.0, 20.0)
        if mode == "RESET":
            self.mode_duration = 3.0
            self.reset_wait = 1.4
        self.recent_modes.append(mode)

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.set_mode(self.modes[self.mode_index])

    def choose_new_mode(self, state, force=False):
        if self.switch_cooldown > 0 and not force:
            return

        inside = state["inside"]
        outside = state["outside"]
        total = max(1, state["total"])
        diff = inside - outside

        candidates = ["BALANCE", "MIX", "PULSE", "ORBIT", "ARTIST", "CAREFUL"]
        if outside > inside + max(6, total * 0.18):
            candidates += ["PUMP_IN", "PUMP_IN", "CAREFUL"]
        if inside > outside + max(6, total * 0.18):
            candidates += ["PUMP_OUT", "PUMP_OUT", "CAREFUL"]
        if self.stagnant_time > 10:
            candidates += ["CHAOS", "PULSE", "ARTIST"]
        if abs(diff) < total * 0.13:
            candidates += ["MIX", "ORBIT", "ARTIST"]
        if total < 25:
            candidates += ["RESET"]

        pyrandom.shuffle(candidates)
        for c in candidates:
            if c not in self.recent_modes or force:
                self.set_mode(c)
                self.switch_cooldown = 3.0
                return

        self.set_mode(pyrandom.choice(candidates))
        self.switch_cooldown = 3.0

    def detect_stagnation_and_completion(self, dt, state):
        self.history_timer += dt
        if self.history_timer >= 1.0:
            self.history_timer = 0.0
            self.history.append((state["inside"], state["outside"], state["crossings"], round(state["avg_speed"], 2)))

        if len(self.history) >= 8:
            recent = list(self.history)[-8:]
            same_counts = all(item[0] == recent[0][0] and item[1] == recent[0][1] for item in recent)
            same_crossings = all(item[2] == recent[0][2] for item in recent)
            slowish = sum(item[3] for item in recent) / len(recent) < 0.42
            if same_counts and same_crossings:
                self.stagnant_time += dt
            elif same_crossings and slowish:
                self.stagnant_time += dt * 0.5
            else:
                self.stagnant_time = max(0, self.stagnant_time - dt * 1.5)

        total = max(1, state["total"])
        one_side_dominates = max(state["inside"], state["outside"]) > total * 0.92
        many_crossings = state["crossings"] > max(26, total * 0.55)
        too_long = self.time_in_mode > 35

        if one_side_dominates and many_crossings:
            self.completion_time += dt
        else:
            self.completion_time = max(0, self.completion_time - dt)

        if self.stagnant_time > 18 or self.completion_time > 5 or too_long and self.mode == "RESET":
            self.set_mode("RESET")

    def apply_channel_pattern(self, pattern, state):
        if pattern == "all_open":
            for ch in channels:
                ch.set_open(True)
        elif pattern == "all_closed":
            for ch in channels:
                ch.set_open(False)
        elif pattern == "alternating":
            for i, ch in enumerate(channels):
                ch.set_open((i + int(self.phase)) % 2 == 0)
        elif pattern == "focus":
            for i, ch in enumerate(channels):
                surface_dist = angular_surface_distance(ch.n, channels[self.focus_index].n)
                ch.set_open(surface_dist < R * 0.9 or i == self.focus_index)
        elif pattern == "traveler":
            for i, ch in enumerate(channels):
                ch.set_open(i == self.focus_index or i == (self.focus_index + 1) % len(channels))
        elif pattern == "careful":
            inside = state["inside"]
            outside = state["outside"]
            desired_open = 2 if abs(inside - outside) < 10 else 4
            ranked = sorted(channels, key=lambda c: angular_surface_distance(c.n, self.wand.pos))
            for i, ch in enumerate(ranked):
                ch.set_open(i < desired_open)
        elif pattern == "random":
            for ch in channels:
                if pyrandom.random() < 0.28:
                    ch.toggle()

    def mark_near_wand(self):
        for ion in ions:
            if mag(ion.pos - self.wand.pos) < 2.1 and pyrandom.random() < 0.18:
                ion.set_marked(True)

    def unmark_some(self, chance=0.015):
        for ion in ions:
            if ion.marked and pyrandom.random() < chance:
                ion.set_marked(False)

    def step(self, dt):
        global global_pressure_bias, global_swirl_strength, global_electric_field

        state = self.read_state()
        self.detect_stagnation_and_completion(dt, state)

        self.time_in_mode += dt
        self.phase += dt
        self.action_timer -= dt
        self.switch_cooldown = max(0, self.switch_cooldown - dt)

        if self.human_override_timer > 0:
            self.human_override_timer -= dt
            global_pressure_bias *= 0.92
            global_swirl_strength *= 0.92
            global_electric_field *= 0.92
            self.update_wand(dt, state)
            return

        if not self.enabled:
            global_pressure_bias *= 0.96
            global_swirl_strength *= 0.96
            global_electric_field *= 0.96
            self.update_wand(dt, state)
            return

        if self.time_in_mode > self.mode_duration and self.mode != "RESET":
            self.choose_new_mode(state)

        inside = state["inside"]
        outside = state["outside"]
        total = max(1, state["total"])

        # Default decay before each behavior writes stronger intent.
        global_pressure_bias *= 0.90
        global_swirl_strength *= 0.90
        global_electric_field *= 0.90

        if self.mode == "BALANCE":
            self.apply_channel_pattern("alternating", state)
            if inside > outside + 3:
                global_pressure_bias = 0.72
            elif outside > inside + 3:
                global_pressure_bias = -0.72
            else:
                global_pressure_bias = 0.08 * math.sin(self.phase * 1.7)
            global_swirl_strength = 0.18
            global_electric_field = vector(0.04 * math.sin(self.phase), 0.02, 0.03 * math.cos(self.phase))

        elif self.mode == "PUMP_IN":
            self.focus_index = int((self.phase * 0.65) % len(channels))
            self.apply_channel_pattern("focus", state)
            global_pressure_bias = -1.05
            global_swirl_strength = 0.12
            global_electric_field = safe_norm(channels[self.focus_index].n) * -0.10

        elif self.mode == "PUMP_OUT":
            self.focus_index = int((self.phase * 0.65) % len(channels))
            self.apply_channel_pattern("focus", state)
            global_pressure_bias = 1.05
            global_swirl_strength = 0.12
            global_electric_field = safe_norm(channels[self.focus_index].n) * 0.10

        elif self.mode == "MIX":
            if self.action_timer <= 0:
                self.action_timer = pyrandom.uniform(0.9, 1.8)
                self.apply_channel_pattern("random", state)
            if sum(1 for ch in channels if ch.open) < 3:
                pyrandom.choice(channels).set_open(True)
            global_pressure_bias = 0.24 * math.sin(self.phase * 2.2)
            global_swirl_strength = 0.52 + 0.15 * math.sin(self.phase)
            global_electric_field = vector(0.08 * math.sin(self.phase * 1.1), 0.03 * math.cos(self.phase * 0.7), 0.05)

        elif self.mode == "PULSE":
            pulse = math.sin(self.phase * 3.2)
            for i, ch in enumerate(channels):
                ch.set_open(math.sin(self.phase * 3.2 + i * 0.42) > -0.15)
            global_pressure_bias = 1.12 if pulse > 0 else -1.12
            global_swirl_strength = 0.08
            global_electric_field = vector(0, 0.14 * pulse, 0)

        elif self.mode == "ORBIT":
            self.apply_channel_pattern("all_open", state)
            global_pressure_bias = 0.12 * math.sin(self.phase * 0.8)
            global_swirl_strength = 0.95
            global_electric_field = vector(0.06 * math.sin(self.phase), 0.0, 0.06 * math.cos(self.phase))
            for ion in ions:
                if ion.marked or pyrandom.random() < 0.008:
                    ion.set_marked(True)
                    ion.vel += tangent_swirl(ion.pos, 0.18) * dt * 8

        elif self.mode == "ARTIST":
            if self.action_timer <= 0:
                self.action_timer = 1.25
                self.focus_index = (self.focus_index + 1) % len(channels)
                self.apply_channel_pattern("traveler", state)
                self.mark_near_wand()
            global_pressure_bias = 0.45 * math.sin(self.phase * 1.3)
            global_swirl_strength = 0.38
            global_electric_field = vector(0.05 * math.sin(self.phase * 0.9), 0.05 * math.cos(self.phase * 1.1), 0.02)
            self.unmark_some(0.004)

        elif self.mode == "CHAOS":
            if self.action_timer <= 0:
                self.action_timer = pyrandom.uniform(0.22, 0.55)
                self.apply_channel_pattern("random", state)
                self.chaos_vector = random_unit() * pyrandom.uniform(0.1, 0.38)
                if len(ions) < MAX_IONS and pyrandom.random() < 0.35:
                    spill_ions(pyrandom.randint(1, 3))
            global_pressure_bias = pyrandom.uniform(-1.35, 1.35)
            global_swirl_strength = pyrandom.uniform(-0.95, 1.15)
            global_electric_field = self.chaos_vector
            for ion in ions:
                if pyrandom.random() < 0.006:
                    ion.set_marked(not ion.marked)

        elif self.mode == "CAREFUL":
            self.apply_channel_pattern("careful", state)
            if inside > outside + 5:
                global_pressure_bias = 0.42
            elif outside > inside + 5:
                global_pressure_bias = -0.42
            else:
                global_pressure_bias = 0.0
            global_swirl_strength = 0.06
            global_electric_field = vector(0.025 * math.sin(self.phase), 0.025 * math.cos(self.phase), 0)

        elif self.mode == "RESET":
            self.apply_channel_pattern("all_closed", state)
            global_pressure_bias = 0
            global_swirl_strength = 0.0
            global_electric_field = vector(0, 0, 0)
            self.reset_wait -= dt
            if self.reset_wait <= 0:
                reset_simulation(round_increment=True)
                self.stagnant_time = 0
                self.completion_time = 0
                self.history.clear()
                self.choose_new_mode(self.read_state(), force=True)

        self.update_wand(dt, state)

    def update_wand(self, dt, state):
        mode_col = {
            "BALANCE": vector(0.25, 0.65, 1.0),
            "PUMP_IN": vector(0.2, 0.9, 0.45),
            "PUMP_OUT": vector(1.0, 0.45, 0.18),
            "MIX": vector(0.3, 0.8, 0.95),
            "PULSE": vector(1.0, 0.75, 0.15),
            "ORBIT": vector(0.65, 0.2, 1.0),
            "ARTIST": vector(0.95, 0.25, 0.95),
            "CHAOS": vector(1.0, 0.18, 0.12),
            "CAREFUL": vector(0.35, 0.95, 0.72),
            "RESET": vector(0.5, 0.5, 0.5),
        }.get(self.mode, vector(0.8, 0.2, 1.0))

        if channels:
            if self.mode in ["PUMP_IN", "PUMP_OUT", "ARTIST"]:
                target_dir = channels[self.focus_index % len(channels)].n
                target = target_dir * (R + 1.05)
                self.wand.pos = self.wand.pos * 0.86 + target * 0.14
            else:
                a = self.phase * (0.55 if self.mode != "CHAOS" else 1.7)
                b = self.phase * 0.37
                self.wand.pos = vector(
                    (R + 1.25) * math.cos(a) * math.cos(b),
                    (R + 1.25) * math.sin(b),
                    (R + 1.25) * math.sin(a) * math.cos(b)
                )

        self.wand.color = mode_col
        self.wand.trail_color = mode_col
        self.wand_ring.pos = self.wand.pos
        self.wand_ring.axis = safe_norm(self.wand.pos)
        self.wand_ring.color = mode_col
        self.wand_ring.radius = 0.32 + 0.08 * math.sin(self.phase * 4)

ai = MembraneAI()

# -----------------------------
# Ion spawning/reset
# -----------------------------
def create_ion(distribution="split"):
    if distribution == "inside":
        pos = random_inside_position()
    elif distribution == "outside":
        pos = random_outside_position()
    elif distribution == "band":
        pos = random_unit() * pyrandom.uniform(R - 0.65, R + 0.65)
    else:
        pos = random_inside_position() if pyrandom.random() < 0.5 else random_outside_position()
    ion = Ion(pos)
    if distribution == "band":
        ion.vel += tangent_swirl(pos, pyrandom.uniform(0.2, 0.7))
    return ion

def spill_ions(count=5):
    for _ in range(count):
        if len(ions) >= MAX_IONS:
            return
        ion = create_ion("outside")
        ion.vel = -safe_norm(ion.pos) * pyrandom.uniform(0.4, 1.15) + random_unit() * 0.25
        ions.append(ion)

def reset_simulation(round_increment=False):
    global ions, round_number, total_crossings, global_pressure_bias, global_swirl_strength, global_electric_field

    for ion in ions:
        ion.dispose()
    ions = []

    if round_increment:
        round_number += 1

    total_crossings = 0
    global_pressure_bias = 0.0
    global_swirl_strength = 0.0
    global_electric_field = vector(0, 0, 0)

    pattern = round_number % 4
    if pattern == 0:
        distribution = "split"
    elif pattern == 1:
        distribution = "outside"
    elif pattern == 2:
        distribution = "inside"
    else:
        distribution = "band"

    for _ in range(INITIAL_IONS):
        ions.append(create_ion(distribution))

    for ch in channels:
        ch.set_open(pyrandom.random() < 0.55)
        ch.flash = 0.0
        ch.attached_count = 0

    try:
        ai.wand.clear_trail()
    except Exception:
        pass

def toggle_trails():
    global trails_enabled
    trails_enabled = not trails_enabled
    for ion in ions:
        ion.obj.make_trail = trails_enabled
        if not trails_enabled:
            ion.clear_trail()

def clear_all_trails():
    for ion in ions:
        ion.clear_trail()
    try:
        ai.wand.clear_trail()
    except Exception:
        pass

reset_simulation(round_increment=False)

# -----------------------------
# Particle collisions
# -----------------------------
def handle_ion_collisions():
    n = len(ions)
    min_d = ION_RADIUS * 2.02
    min_d2 = min_d * min_d
    for i in range(n):
        a = ions[i]
        if a.attached_channel is not None:
            continue
        for j in range(i + 1, n):
            b = ions[j]
            if b.attached_channel is not None:
                continue
            delta = b.pos - a.pos
            d2 = mag2(delta)
            if 1e-8 < d2 < min_d2:
                d = math.sqrt(d2)
                normal = delta / d
                overlap = min_d - d
                a.pos -= normal * overlap * 0.5
                b.pos += normal * overlap * 0.5

                va_n = dot(a.vel, normal)
                vb_n = dot(b.vel, normal)
                a.vel += (vb_n - va_n) * normal * 0.82
                b.vel += (va_n - vb_n) * normal * 0.82

                a.obj.pos = a.pos
                b.obj.pos = b.pos

# -----------------------------
# Visual updates
# -----------------------------
def update_meter_and_labels():
    global last_counts
    inside = sum(1 for ion in ions if ion.is_inside())
    outside = len(ions) - inside
    last_counts = (inside, outside)

    total = max(1, len(ions))
    max_h = 4.8
    inside_h = max_h * inside / total
    outside_h = max_h * outside / total

    inside_bar.size = vector(0.34, max(0.03, inside_h), 0.34)
    inside_bar.pos = vector(-8.95, -2.5 + inside_h / 2, 0)

    outside_bar.size = vector(0.34, max(0.03, outside_h), 0.34)
    outside_bar.pos = vector(-8.25, -2.5 + outside_h / 2, 0)

    meter_count_label.text = f"Ions: {len(ions)}\nIn {inside} | Out {outside}"

    open_count = sum(1 for ch in channels if ch.open)
    status_label.text = (
        f"Round {round_number}   Inside: {inside}   Outside: {outside}   "
        f"Open channels: {open_count}/{len(channels)}   Transfers: {total_crossings}"
    )

    ai_state = "ON" if ai.enabled else "OFF"
    override = f" | human override {ai.human_override_timer:0.1f}s" if ai.human_override_timer > 0 else ""
    pause_text = " | PAUSED" if paused else ""
    ai_label.text = (
        f"AI {ai_state}: {ai.mode}   stagnation {ai.stagnant_time:0.1f}s"
        f"{override}{pause_text}"
    )

def update_channel_visuals(dt):
    for ch in channels:
        ch.update_visual(dt)

# -----------------------------
# Keyboard controls
# -----------------------------
def on_keydown(evt):
    global paused, global_pressure_bias

    k = evt.key.lower()

    if k == " ":
        paused = not paused
    elif k == "a":
        ai.enabled = not ai.enabled
    elif k == "m":
        ai.next_mode()
    elif k == "r":
        reset_simulation(round_increment=True)
        ai.human_override_timer = 0
    elif k == "o":
        for ch in channels:
            ch.set_open(True)
        ai.human_override_timer = 5.0
    elif k == "c":
        for ch in channels:
            ch.set_open(False)
        ai.human_override_timer = 5.0
    elif k == "t":
        toggle_trails()
    elif k == "f":
        clear_all_trails()
    elif k == "p":
        spill_ions(8)
        ai.human_override_timer = 4.0
    elif k == "i":
        global_pressure_bias = -1.2
        ai.set_mode("PUMP_IN")
        ai.human_override_timer = 2.0
    elif k == "u":
        global_pressure_bias = 1.2
        ai.set_mode("PUMP_OUT")
        ai.human_override_timer = 2.0
    elif k == "b":
        ai.set_mode("BALANCE")
    elif k == "h":
        ai.human_override_timer = 8.0
    elif k.isdigit():
        idx = 9 if k == "0" else int(k) - 1
        if 0 <= idx < len(channels):
            channels[idx].toggle()
            ai.human_override_timer = 6.0

scene.bind("keydown", on_keydown)

# -----------------------------
# Main simulation loop with CSV logging
# -----------------------------
csv_logger_start()
csv_logger_sample(force=True, sample_note="initial")

while True:
    rate(60)
    frame_count += 1

    if paused:
        update_meter_and_labels()
        csv_logger_sample(sample_note="paused")
        if csv_logger_should_stop():
            break
        continue

    ai.step(DT)

    for ion in ions:
        ion.update(DT)

    if frame_count % COLLISION_INTERVAL == 0:
        handle_ion_collisions()

    update_channel_visuals(DT)
    update_meter_and_labels()
    csv_logger_sample(sample_note="running")

    if csv_logger_should_stop():
        break

csv_logger_close()
print(f"CSV log saved to: {_csv_path}")
print(f"CSV metadata saved to: {_csv_meta_path}")
