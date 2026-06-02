from vpython import *
import random
import math
import time
import csv
import os
import json
from datetime import datetime

# ============================================================
# 3D VPython Simulation:
# Cell as a Miniature Factory with Energy Flows + AI Controller
# ============================================================

scene.title = "Cell Miniature Factory with Energy Flows and AI Controller"
scene.width = 1200
scene.height = 760
scene.background = vector(0.92, 0.97, 1.0)
scene.forward = vector(-0.6, -0.35, -1.0)
scene.center = vector(0, 0, 0)
scene.range = 11

distant_light(direction=vector(1, -2, -1), color=color.white)
distant_light(direction=vector(-1, 1, 2), color=vector(0.75, 0.85, 1.0))

# --------------------------
# Colors
# --------------------------

RAW_COLOR = vector(0.25, 0.75, 1.0)
BLUEPRINT_COLOR = vector(0.45, 0.45, 1.0)
PROTEIN_COLOR = vector(1.0, 0.45, 0.78)
PRODUCT_COLOR = vector(1.0, 0.73, 0.18)
WASTE_COLOR = vector(0.55, 0.55, 0.55)
ENERGY_COLOR = vector(0.35, 1.0, 0.78)
MEMBRANE_COLOR = vector(0.72, 0.92, 1.0)
NUCLEUS_COLOR = vector(0.68, 0.55, 1.0)
MITO_COLOR = vector(1.0, 0.55, 0.28)
RIBO_COLOR = vector(0.95, 0.28, 0.42)
DRONE_COLOR = vector(0.1, 0.75, 0.9)
ER_COLOR = vector(0.55, 0.85, 1.0)

KIND_COLORS = {
    "raw": RAW_COLOR,
    "blueprint": BLUEPRINT_COLOR,
    "protein": PROTEIN_COLOR,
    "product": PRODUCT_COLOR,
    "waste": WASTE_COLOR,
    "energy": ENERGY_COLOR,
}

KIND_RADII = {
    "raw": 0.16,
    "blueprint": 0.14,
    "protein": 0.18,
    "product": 0.20,
    "waste": 0.14,
    "energy": 0.10,
}


# --------------------------
# CSV logging configuration
# --------------------------
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
    CSV_OUTPUT_PATH = os.path.join(CSV_OUTPUT_DIR, f"{CSV_RUN_ID}-cell-factory-state-log.csv")
else:
    fallback_path = os.environ.get("SIM_STATE_CSV_PATH", "").strip()
    if fallback_path:
        CSV_OUTPUT_PATH = fallback_path
        parent = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
        if parent:
            os.makedirs(parent, exist_ok=True)
    else:
        CSV_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cell_factory_state_log.csv")

CSV_METADATA_PATH = os.path.splitext(CSV_OUTPUT_PATH)[0] + ".metadata.json"

CSV_FIELDNAMES = [
    "csv_run_id", "csv_elapsed_seconds", "simulation_time", "frame",
    "row_type", "object_id", "object_kind",
    "round_number", "round_goal", "spawned_this_round", "completed_products",
    "active_count", "raw_count", "blueprint_count", "protein_count", "product_count",
    "avg_speed", "avg_energy_charge", "ai_enabled", "ai_mode", "ai_stagnant_time",
    "ai_completion_time", "paused", "drone_x", "drone_y", "drone_z",
    "drone_vx", "drone_vy", "drone_vz", "drone_target_x", "drone_target_y", "drone_target_z",
    "attached_count", "particle_count", "effect_count", "station_count", "energy_stream_count",
    "particle_id", "kind", "alive", "attached", "marked", "age", "processing_cooldown",
    "x", "y", "z", "vx", "vy", "vz", "target_x", "target_y", "target_z",
    "radius", "last_speed", "station_name", "station_type", "station_charge",
    "station_touch_count", "station_last_touched", "effect_type"
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
_csv_writer.writeheader()
_csv_file.flush()


def _v_components(v, prefix=""):
    return {
        f"{prefix}x": float(v.x),
        f"{prefix}y": float(v.y),
        f"{prefix}z": float(v.z),
    }


def write_csv_metadata():
    metadata = {
        "csv_run_id": CSV_RUN_ID,
        "csv_output_path": CSV_OUTPUT_PATH,
        "csv_metadata_path": CSV_METADATA_PATH,
        "simulation_name": "Cell Miniature Factory with Energy Flows and AI Controller",
        "script_type": "full_vpython_csv_logger",
        "run_seconds": CSV_RUN_SECONDS,
        "sample_hz": CSV_SAMPLE_HZ,
        "sample_interval": CSV_SAMPLE_INTERVAL,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "row_types": ["summary", "drone", "particle", "station", "attached_particle", "effect"],
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

# --------------------------
# Utility Functions
# --------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def safe_norm(v):
    if mag(v) < 1e-7:
        return vector(1, 0, 0)
    return norm(v)

def limit_vec(v, max_mag):
    m = mag(v)
    if m > max_mag:
        return v * (max_mag / m)
    return v

def randf(a, b):
    return random.uniform(a, b)

def random_unit_vector():
    z = randf(-1, 1)
    a = randf(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), r * math.sin(a), z)

def random_inside_sphere(radius):
    return random_unit_vector() * (radius * (random.random() ** (1 / 3)))

def random_inside_cell(radius):
    return random_inside_sphere(radius * 0.9)

def choose(seq):
    return random.choice(seq)

# --------------------------
# Station
# --------------------------

class FactoryStation:
    def __init__(self, name, stype, pos, radius, visual, label_offset=vector(0, 1.2, 0)):
        self.name = name
        self.stype = stype
        self.pos = pos
        self.radius = radius
        self.visual = visual
        self.charge = 0.0
        self.touch_count = 0
        self.last_touched = 0.0
        self.base_radius = radius

        self.halo = sphere(
            pos=pos,
            radius=radius * 1.18,
            color=visual.color if hasattr(visual, "color") else color.white,
            opacity=0.08,
            emissive=True,
        )

        self.lbl = label(
            pos=pos + label_offset,
            text=name,
            height=13,
            color=vector(0.1, 0.15, 0.22),
            box=False,
            opacity=0,
        )

    def pulse(self, amount=1.0):
        self.charge = clamp(self.charge + amount, 0, 5)
        self.touch_count += 1
        self.last_touched = time.time()

    def update(self, t, dt):
        self.charge = max(0, self.charge - dt * 0.7)
        glow = 0.07 + 0.04 * self.charge + 0.025 * math.sin(t * 4 + self.pos.x)
        self.halo.opacity = clamp(glow, 0.04, 0.35)
        self.halo.radius = self.radius * (1.12 + 0.035 * self.charge + 0.025 * math.sin(t * 3))

        if self.stype == "mitochondrion":
            try:
                self.visual.rotate(angle=dt * (0.4 + 0.1 * self.charge), axis=vector(0, 1, 0), origin=self.pos)
            except Exception:
                pass

# --------------------------
# Energy Stream
# --------------------------

class EnergyStream:
    def __init__(self, start_station, end_station, color_value=ENERGY_COLOR, particles=8):
        self.start = start_station
        self.end = end_station
        self.color = color_value
        self.phase = randf(0, 2 * math.pi)
        self.amp = randf(0.25, 0.45)

        self.static_curve = curve(
            color=self.color,
            radius=0.025,
            emissive=True,
            opacity=0.35,
        )

        self.flow = []
        for i in range(particles):
            s = sphere(
                pos=self.point(i / particles, 0),
                radius=0.07,
                color=self.color,
                emissive=True,
                opacity=0.75,
            )
            self.flow.append({"obj": s, "u": i / particles, "speed": randf(0.16, 0.34)})

        self.rebuild_curve()

    def point(self, u, t):
        a = self.start.pos
        b = self.end.pos
        mid = a * (1 - u) + b * u
        wobble = vector(
            0,
            math.sin(u * math.pi * 2 + t * 1.3 + self.phase),
            math.cos(u * math.pi * 2 + t * 1.0 + self.phase),
        ) * self.amp * math.sin(math.pi * u)
        return mid + wobble

    def rebuild_curve(self):
        pts = []
        for i in range(28):
            u = i / 27
            pts.append(self.point(u, 0))
        self.static_curve.clear()
        for p in pts:
            self.static_curve.append(p)

    def update(self, t, dt):
        total_charge = self.start.charge + self.end.charge
        self.static_curve.opacity = clamp(0.22 + total_charge * 0.045, 0.18, 0.68)
        for item in self.flow:
            item["u"] = (item["u"] + dt * item["speed"] * (1 + 0.18 * total_charge)) % 1.0
            item["obj"].pos = self.point(item["u"], t)
            item["obj"].radius = 0.06 + 0.025 * math.sin(t * 6 + item["u"] * 10) + 0.008 * total_charge
            item["obj"].opacity = clamp(0.52 + 0.06 * total_charge, 0.45, 0.95)

    def hide(self):
        self.static_curve.visible = False
        for item in self.flow:
            item["obj"].visible = False

# --------------------------
# Effects
# --------------------------

class WrapEffect:
    def __init__(self, station, ttl=7.0, color_value=vector(0.15, 0.75, 1.0)):
        self.station = station
        self.ttl = ttl
        self.age = 0.0
        self.obj = curve(radius=0.028, color=color_value, emissive=True, opacity=0.7)

        turns = 3.0
        points = 90
        height = station.radius * 2.5
        for i in range(points):
            u = i / (points - 1)
            a = u * turns * 2 * math.pi
            r = station.radius * (1.22 + 0.1 * math.sin(a * 2))
            p = station.pos + vector(
                r * math.cos(a),
                height * (u - 0.5),
                r * math.sin(a),
            )
            self.obj.append(p)

    def update(self, dt):
        self.age += dt
        try:
            self.obj.rotate(angle=dt * 0.9, axis=vector(0, 1, 0), origin=self.station.pos)
        except Exception:
            pass
        self.obj.opacity = clamp(0.7 * (1 - self.age / self.ttl), 0, 0.7)
        if self.age >= self.ttl:
            self.obj.visible = False
            return False
        return True

class MarkEffect:
    def __init__(self, particle, ttl=5.0, color_value=vector(1.0, 0.85, 0.1)):
        self.particle = particle
        self.ttl = ttl
        self.age = 0.0
        self.obj = ring(
            pos=particle.pos,
            axis=vector(0, 1, 0),
            radius=particle.radius * 2.1,
            thickness=0.025,
            color=color_value,
            emissive=True,
            opacity=0.75,
        )

    def update(self, dt):
        self.age += dt
        if not self.particle.alive:
            self.obj.visible = False
            return False
        self.obj.pos = self.particle.pos
        self.obj.axis = vector(
            math.sin(self.age * 2.2),
            1,
            math.cos(self.age * 2.0),
        )
        self.obj.opacity = clamp(0.75 * (1 - self.age / self.ttl), 0, 0.75)
        if self.age >= self.ttl:
            self.obj.visible = False
            return False
        return True

class BurstEffect:
    def __init__(self, pos, color_value=ENERGY_COLOR, count=16, ttl=1.4):
        self.ttl = ttl
        self.age = 0.0
        self.bits = []
        for _ in range(count):
            obj = sphere(
                pos=pos,
                radius=randf(0.025, 0.055),
                color=color_value,
                emissive=True,
                opacity=0.7,
            )
            vel = random_unit_vector() * randf(0.5, 2.2)
            self.bits.append([obj, vel])

    def update(self, dt):
        self.age += dt
        for b in self.bits:
            b[0].pos += b[1] * dt
            b[1] *= 0.94
            b[0].opacity = clamp(0.7 * (1 - self.age / self.ttl), 0, 0.7)
        if self.age >= self.ttl:
            for b in self.bits:
                b[0].visible = False
            return False
        return True

# --------------------------
# Particle
# --------------------------

class FactoryParticle:
    _next_id = 0

    def __init__(self, sim, kind="raw", pos=vector(0, 0, 0), vel=vector(0, 0, 0), target=None):
        self.sim = sim
        self.id = FactoryParticle._next_id
        FactoryParticle._next_id += 1

        self.kind = kind
        self.pos = pos
        self.vel = vel
        self.target = target
        self.radius = KIND_RADII.get(kind, 0.15)
        self.alive = True
        self.age = 0.0
        self.processing_cooldown = 0.0
        self.attached = False
        self.attach_offset = vector(0, 0, 0)
        self.marked = False
        self.last_speed = 0.0

        self.obj = sphere(
            pos=pos,
            radius=self.radius,
            color=KIND_COLORS.get(kind, color.white),
            emissive=True,
            make_trail=True,
            retain=75,
            trail_radius=self.radius * 0.22,
            trail_color=KIND_COLORS.get(kind, color.white),
        )

    def set_kind(self, kind):
        self.kind = kind
        self.radius = KIND_RADII.get(kind, 0.15)
        self.obj.radius = self.radius
        self.obj.color = KIND_COLORS.get(kind, color.white)
        try:
            self.obj.trail_color = KIND_COLORS.get(kind, color.white)
        except Exception:
            pass

    def remove(self):
        self.alive = False
        self.obj.visible = False
        try:
            self.obj.clear_trail()
        except Exception:
            pass

    def desired_station(self):
        if self.kind == "raw":
            return self.sim.nucleus
        if self.kind == "blueprint":
            return self.sim.nearest_station(self.pos, "ribosome")
        if self.kind == "protein":
            return self.sim.nearest_station(self.pos, "mitochondrion")
        if self.kind == "product":
            return None
        return None

    def update_target_by_kind(self):
        if self.kind == "product":
            self.target = self.sim.exit_outside()
        else:
            st = self.desired_station()
            if st:
                self.target = st.pos + random_unit_vector() * st.radius * 0.35

    def update(self, dt):
        if not self.alive:
            return

        self.age += dt
        self.processing_cooldown = max(0, self.processing_cooldown - dt)

        if self.attached:
            self.pos = self.sim.drone_pos + self.attach_offset
            self.vel = self.sim.drone_vel
            self.obj.pos = self.pos
            self.last_speed = mag(self.vel)
            return

        if self.target is None or random.random() < 0.003:
            self.update_target_by_kind()

        if self.target is not None:
            to_target = self.target - self.pos
            desired = safe_norm(to_target) * (1.15 + 0.2 * random.random())
            steer = desired - self.vel
            self.vel += limit_vec(steer, 1.9) * dt

        swirl = cross(self.pos, vector(0, 1, 0))
        if mag(swirl) > 0.01:
            self.vel += safe_norm(swirl) * 0.06 * dt

        self.vel += random_unit_vector() * randf(0.0, 0.18) * dt
        self.vel = limit_vec(self.vel, 2.4)

        self.pos += self.vel * dt

        self.handle_membrane()
        self.handle_station_collisions()

        if self.kind == "product" and self.pos.x > self.sim.cell_radius + 0.6 and abs(self.pos.y) < 2.1 and abs(self.pos.z) < 2.1:
            self.sim.completed_products += 1
            self.sim.effects.append(BurstEffect(self.pos, PRODUCT_COLOR, 12, 1.1))
            self.remove()
            return

        self.obj.pos = self.pos
        self.last_speed = mag(self.vel)

    def handle_membrane(self):
        r = self.sim.cell_radius
        m = mag(self.pos)

        if self.kind == "product" and self.pos.x > r - 0.7 and abs(self.pos.y) < 1.6 and abs(self.pos.z) < 1.6:
            return

        if m > r - self.radius:
            n = safe_norm(self.pos)
            self.pos = n * (r - self.radius)
            vn = dot(self.vel, n)
            if vn > 0:
                self.vel -= 1.85 * vn * n
                self.vel += random_unit_vector() * 0.18

    def handle_station_collisions(self):
        if self.processing_cooldown > 0:
            return

        for st in self.sim.stations:
            d = self.pos - st.pos
            if mag(d) < st.radius + self.radius * 1.1:
                handled = self.sim.process_collision(self, st)
                if handled:
                    self.processing_cooldown = 0.45
                    return
                else:
                    self.vel += safe_norm(d) * 0.8
                    st.pulse(0.12)

# --------------------------
# AI Controller
# --------------------------

class AIController:
    MODES = [
        "FEED",
        "COLLECT",
        "ENERGIZE",
        "CLEANUP",
        "ARTISTIC",
        "PLAYFUL",
        "CAREFUL",
        "CHAOTIC",
        "CURIOUS",
        "CONSTRUCTIVE",
    ]

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "FEED"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 10.0
        self.action_timer = 0.0
        self.last_spawn_time = 0.0
        self.last_wrap_time = 0.0
        self.last_mark_time = 0.0
        self.last_metric = None
        self.stagnant_time = 0.0
        self.completion_time = 0.0
        self.reset_requested = False
        self.orbit_angle = 0.0
        self.random_target_time = 0.0
        self.random_target = random_inside_cell(sim.cell_radius)
        self.history = []

    def set_mode(self, mode):
        if mode not in self.MODES and mode != "RESETTING":
            return
        self.previous_mode = self.mode
        self.mode = mode
        self.mode_timer = 0.0
        self.mode_duration = randf(7.0, 15.0)
        self.history.append(mode)
        self.history = self.history[-8:]
        self.sim.message("AI mode: " + mode)

    def cycle_mode(self):
        i = self.MODES.index(self.mode) if self.mode in self.MODES else -1
        self.set_mode(self.MODES[(i + 1) % len(self.MODES)])

    def detect_stagnation_and_completion(self, dt):
        state = self.sim.get_state()
        metric = (
            state["active_count"] * 1.7
            + state["raw_count"] * 0.3
            + state["blueprint_count"] * 0.7
            + state["protein_count"] * 1.0
            + state["product_count"] * 1.4
            + state["completed_products"] * 4.0
            + state["avg_speed"] * 2.5
        )

        if self.last_metric is None:
            self.last_metric = metric

        if abs(metric - self.last_metric) < 0.08:
            self.stagnant_time += dt
        else:
            self.stagnant_time = max(0, self.stagnant_time - dt * 0.7)

        self.last_metric = metric

        complete = (
            state["completed_products"] >= self.sim.round_goal
            or (state["spawned_this_round"] >= self.sim.round_goal and state["active_count"] == 0)
        )

        empty = state["active_count"] == 0 and state["spawned_this_round"] >= 3
        halted = self.stagnant_time > 9.0

        if complete:
            self.completion_time += dt
            self.sim.message("Round complete. AI preparing new round...")
            if self.completion_time > 3.0:
                self.sim.reset_round()
                self.completion_time = 0.0
                self.stagnant_time = 0.0
                self.set_mode("FEED")
                return True
        else:
            self.completion_time = 0.0

        if halted:
            if empty:
                self.sim.reset_round()
                self.stagnant_time = 0.0
                self.set_mode("FEED")
                return True
            else:
                self.stagnant_time = 0.0
                self.set_mode(random.choice(["PLAYFUL", "CHAOTIC", "COLLECT", "ENERGIZE"]))
                self.sim.spill_from_drone(3)
                return True

        return False

    def choose_next_mode(self):
        state = self.sim.get_state()
        candidates = []

        if state["active_count"] < 4 and state["spawned_this_round"] < self.sim.round_goal:
            candidates += ["FEED", "FEED", "PLAYFUL"]
        if state["raw_count"] + state["blueprint_count"] + state["protein_count"] > 3:
            candidates += ["COLLECT", "CAREFUL", "CONSTRUCTIVE"]
        if state["protein_count"] > 1:
            candidates += ["ENERGIZE", "CONSTRUCTIVE"]
        if state["product_count"] > 0:
            candidates += ["CLEANUP", "CONSTRUCTIVE"]
        if state["avg_energy_charge"] < 0.6:
            candidates += ["ENERGIZE"]
        if len(self.history) >= 3 and len(set(self.history[-3:])) == 1:
            candidates += ["ARTISTIC", "CURIOUS", "PLAYFUL", "CHAOTIC"]
        candidates += ["CURIOUS", "ARTISTIC", "PLAYFUL"]

        mode = random.choice(candidates)
        tries = 0
        while mode == self.mode and tries < 6:
            mode = random.choice(candidates)
            tries += 1
        self.set_mode(mode)

    def update(self, dt):
        if not self.enabled:
            return

        if self.detect_stagnation_and_completion(dt):
            return

        self.mode_timer += dt
        self.action_timer += dt

        if self.mode_timer > self.mode_duration:
            self.choose_next_mode()

        if self.mode == "FEED":
            self.behavior_feed(dt)
        elif self.mode == "COLLECT":
            self.behavior_collect(dt)
        elif self.mode == "ENERGIZE":
            self.behavior_energize(dt)
        elif self.mode == "CLEANUP":
            self.behavior_cleanup(dt)
        elif self.mode == "ARTISTIC":
            self.behavior_artistic(dt)
        elif self.mode == "PLAYFUL":
            self.behavior_playful(dt)
        elif self.mode == "CAREFUL":
            self.behavior_careful(dt)
        elif self.mode == "CHAOTIC":
            self.behavior_chaotic(dt)
        elif self.mode == "CURIOUS":
            self.behavior_curious(dt)
        elif self.mode == "CONSTRUCTIVE":
            self.behavior_constructive(dt)

    def behavior_feed(self, dt):
        self.sim.set_drone_target(self.sim.entry_port + vector(-0.5, 0, 0))

        if self.sim.t - self.last_spawn_time > 0.75 and self.sim.spawned_this_round < self.sim.round_goal:
            self.sim.spawn_raw()
            self.last_spawn_time = self.sim.t

        if self.action_timer > 2.8:
            self.sim.spill_from_drone(1)
            self.action_timer = 0.0

    def behavior_collect(self, dt):
        if len(self.sim.attached_particles) < self.sim.max_attached:
            p = self.sim.nearest_particle(self.sim.drone_pos, kinds=["raw", "blueprint", "protein"])
            if p:
                self.sim.set_drone_target(p.pos)
                if mag(p.pos - self.sim.drone_pos) < 0.75:
                    self.sim.attach_particle(p)
        else:
            target = self.sim.target_for_attached()
            if target is not None:
                self.sim.set_drone_target(target)
                if mag(self.sim.drone_pos - target) < 0.95:
                    self.sim.detach_all(toward=target)

    def behavior_energize(self, dt):
        mito = self.sim.nearest_station(self.sim.drone_pos, "mitochondrion")
        if not mito:
            return

        self.orbit_angle += dt * 1.6
        orbit = mito.pos + vector(math.cos(self.orbit_angle) * 1.7, math.sin(self.orbit_angle * 0.7) * 0.8, math.sin(self.orbit_angle) * 1.7)
        self.sim.set_drone_target(orbit)

        if mag(self.sim.drone_pos - mito.pos) < 2.2:
            mito.pulse(dt * 1.8)

        if self.action_timer > 1.8:
            self.sim.effects.append(BurstEffect(mito.pos, ENERGY_COLOR, 20, 1.4))
            self.action_timer = 0.0

    def behavior_cleanup(self, dt):
        if len(self.sim.attached_particles) < self.sim.max_attached:
            p = self.sim.nearest_particle(self.sim.drone_pos, kinds=["product"])
            if p:
                self.sim.set_drone_target(p.pos)
                if mag(p.pos - self.sim.drone_pos) < 0.8:
                    self.sim.attach_particle(p)
            else:
                self.sim.set_drone_target(self.sim.exit_port + vector(-1.0, 0, 0))
        else:
            target = self.sim.exit_port + vector(1.8, 0, 0)
            self.sim.set_drone_target(target)
            if mag(self.sim.drone_pos - self.sim.exit_port) < 1.25:
                self.sim.detach_all(toward=target, outward=True)

    def behavior_artistic(self, dt):
        self.orbit_angle += dt * 0.9
        center = self.sim.nucleus.pos
        target = center + vector(math.cos(self.orbit_angle) * 3.2, math.sin(self.orbit_angle * 1.4) * 1.1, math.sin(self.orbit_angle) * 3.2)
        self.sim.set_drone_target(target)

        if self.sim.t - self.last_wrap_time > 4.5:
            st = random.choice(self.sim.stations)
            self.sim.effects.append(WrapEffect(st, ttl=8.0, color_value=random.choice([ENERGY_COLOR, PRODUCT_COLOR, BLUEPRINT_COLOR, vector(0.8, 0.5, 1.0)])))
            self.last_wrap_time = self.sim.t

        if self.sim.t - self.last_mark_time > 1.6:
            p = self.sim.nearest_particle(self.sim.drone_pos)
            if p:
                self.sim.mark_particle(p)
            self.last_mark_time = self.sim.t

    def behavior_playful(self, dt):
        self.random_target_time -= dt
        if self.random_target_time <= 0:
            self.random_target = random_inside_cell(self.sim.cell_radius)
            self.random_target_time = randf(1.2, 3.0)
        self.sim.set_drone_target(self.random_target)

        if self.action_timer > 2.0:
            if random.random() < 0.55:
                self.sim.spill_from_drone(random.randint(1, 3))
            else:
                self.sim.bounce_near_drone(radius=2.2, impulse=1.4)
            self.action_timer = 0.0

    def behavior_careful(self, dt):
        self.orbit_angle += dt * 0.5
        queue_base = self.sim.nucleus.pos + vector(-2.5, 0, 0)
        self.sim.set_drone_target(queue_base + vector(0, math.sin(self.orbit_angle) * 1.2, math.cos(self.orbit_angle) * 1.2))

        raw_index = 0
        for p in self.sim.particles:
            if p.alive and not p.attached:
                if p.kind == "raw":
                    p.target = queue_base + vector(0, (raw_index % 5 - 2) * 0.35, (raw_index // 5 - 1) * 0.35)
                    raw_index += 1
                elif p.kind == "product":
                    p.target = self.sim.exit_port + vector(-0.8, randf(-0.5, 0.5), randf(-0.5, 0.5))

        if len(self.sim.attached_particles) < self.sim.max_attached:
            p = self.sim.nearest_particle(self.sim.drone_pos, kinds=["raw", "blueprint"])
            if p and mag(p.pos - self.sim.drone_pos) < 0.9:
                self.sim.attach_particle(p)

        if self.sim.attached_particles:
            target = self.sim.target_for_attached()
            if target:
                self.sim.set_drone_target(target)
                if mag(self.sim.drone_pos - target) < 1.0:
                    self.sim.detach_all(toward=target)

    def behavior_chaotic(self, dt):
        self.random_target_time -= dt
        if self.random_target_time <= 0:
            st = random.choice(self.sim.stations)
            self.random_target = st.pos + random_unit_vector() * randf(0.4, 2.0)
            self.random_target_time = randf(0.4, 1.1)
        self.sim.set_drone_target(self.random_target)

        if self.action_timer > 1.1:
            self.sim.bounce_near_drone(radius=2.8, impulse=2.0)
            if random.random() < 0.45 and self.sim.spawned_this_round < self.sim.round_goal + 5:
                self.sim.spawn_raw(pos=self.sim.drone_pos + random_unit_vector() * 0.4)
            self.action_timer = 0.0

    def behavior_curious(self, dt):
        station = min(self.sim.stations, key=lambda s: s.last_touched)
        self.orbit_angle += dt * 1.0
        target = station.pos + vector(math.cos(self.orbit_angle) * (station.radius + 1.2), math.sin(self.orbit_angle * 0.8), math.sin(self.orbit_angle) * (station.radius + 1.2))
        self.sim.set_drone_target(target)

        if mag(self.sim.drone_pos - station.pos) < station.radius + 1.5:
            station.pulse(dt * 0.6)

        if self.action_timer > 3.2:
            self.sim.effects.append(WrapEffect(station, ttl=5.5, color_value=vector(0.65, 0.9, 1.0)))
            self.action_timer = 0.0

    def behavior_constructive(self, dt):
        priority = None
        for kinds in [["product"], ["protein"], ["blueprint"], ["raw"]]:
            priority = self.sim.nearest_particle(self.sim.drone_pos, kinds=kinds)
            if priority:
                break

        if len(self.sim.attached_particles) < self.sim.max_attached and priority:
            self.sim.set_drone_target(priority.pos)
            if mag(priority.pos - self.sim.drone_pos) < 0.85:
                self.sim.attach_particle(priority)

        if self.sim.attached_particles:
            target = self.sim.target_for_attached()
            if target is not None:
                self.sim.set_drone_target(target)
                if mag(self.sim.drone_pos - target) < 0.9:
                    self.sim.detach_all(toward=target, outward=True)

# --------------------------
# Main Simulation
# --------------------------

class CellFactorySimulation:
    def __init__(self):
        self.cell_radius = 8.0
        self.entry_port = vector(-self.cell_radius, 0, 0)
        self.exit_port = vector(self.cell_radius, 0, 0)

        self.t = 0.0
        self.paused = False
        self.round_number = 0
        self.round_goal = 12
        self.spawned_this_round = 0
        self.completed_products = 0

        self.particles = []
        self.effects = []
        self.stations = []
        self.ribosomes = []
        self.mitochondria = []
        self.energy_streams = []

        self.max_attached = 4
        self.attached_particles = []

        self.drone_pos = vector(-4, 0, 0)
        self.drone_vel = vector(0, 0, 0)
        self.drone_target = vector(-4, 0, 0)
        self.manual_override_timer = 0.0
        self.keys = {}

        self.build_static_scene()
        self.build_drone()
        self.ai = AIController(self)
        self.build_hud()
        self.bind_keys()
        self.reset_round(first=True)

    # --------------------------
    # Scene Construction
    # --------------------------

    def build_static_scene(self):
        self.membrane = sphere(
            pos=vector(0, 0, 0),
            radius=self.cell_radius,
            color=MEMBRANE_COLOR,
            opacity=0.16,
            shininess=0.25,
        )

        self.membrane_outline = ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=self.cell_radius,
            thickness=0.035,
            color=vector(0.45, 0.75, 1.0),
            opacity=0.5,
        )

        self.entry_ring = ring(
            pos=self.entry_port,
            axis=vector(1, 0, 0),
            radius=1.1,
            thickness=0.08,
            color=RAW_COLOR,
            emissive=True,
            opacity=0.75,
        )

        self.exit_ring = ring(
            pos=self.exit_port,
            axis=vector(1, 0, 0),
            radius=1.15,
            thickness=0.08,
            color=PRODUCT_COLOR,
            emissive=True,
            opacity=0.85,
        )

        label(pos=self.entry_port + vector(-0.7, 1.35, 0), text="raw input", height=12, color=vector(0.05, 0.15, 0.25), box=False, opacity=0)
        label(pos=self.exit_port + vector(0.8, 1.35, 0), text="product exit", height=12, color=vector(0.05, 0.15, 0.25), box=False, opacity=0)

        nucleus_obj = sphere(
            pos=vector(-2.0, 0.05, 0),
            radius=1.65,
            color=NUCLEUS_COLOR,
            opacity=0.82,
            shininess=0.6,
        )
        nucleus_core = sphere(
            pos=vector(-2.0, 0.05, 0),
            radius=0.62,
            color=vector(0.9, 0.78, 1.0),
            opacity=0.9,
            emissive=True,
        )
        self.nucleus = FactoryStation("Nucleus\nblueprint office", "nucleus", nucleus_obj.pos, 1.75, nucleus_obj, label_offset=vector(0, 2.2, 0))
        self.stations.append(self.nucleus)

        # ER-like paths
        self.er_curves = []
        for k in range(3):
            c = curve(color=ER_COLOR, radius=0.045, opacity=0.45)
            for i in range(80):
                u = i / 79
                a = u * 2 * math.pi
                r = 2.1 + 0.32 * k + 0.18 * math.sin(5 * a + k)
                p = self.nucleus.pos + vector(r * math.cos(a), 0.45 * math.sin(2 * a + k), r * math.sin(a))
                c.append(p)
            self.er_curves.append(c)

        mito_positions = [
            vector(2.8, 2.15, -0.25),
            vector(3.1, -2.25, 1.15),
            vector(0.35, 3.15, -2.15),
        ]

        for i, p in enumerate(mito_positions):
            obj = sphere(
                pos=p,
                size=vector(2.2, 1.0, 1.0),
                color=MITO_COLOR,
                opacity=0.88,
                shininess=0.5,
            )
            stripe = ring(
                pos=p,
                axis=vector(1, 0.2, 0.1),
                radius=0.62,
                thickness=0.025,
                color=vector(1.0, 0.85, 0.45),
                opacity=0.8,
            )
            st = FactoryStation("Mitochondrion\npower station", "mitochondrion", p, 1.05, obj, label_offset=vector(0, 1.45, 0))
            self.stations.append(st)
            self.mitochondria.append(st)

        ribo_positions = []
        for i in range(14):
            a = i * 2 * math.pi / 14
            r = randf(2.35, 3.35)
            p = self.nucleus.pos + vector(r * math.cos(a), randf(-0.65, 0.65), r * math.sin(a))
            ribo_positions.append(p)

        for i, p in enumerate(ribo_positions):
            obj = sphere(
                pos=p,
                radius=0.28,
                color=RIBO_COLOR,
                opacity=0.94,
                shininess=0.45,
            )
            st = FactoryStation("Ribosome", "ribosome", p, 0.45, obj, label_offset=vector(0, 0.55, 0))
            if i > 2:
                st.lbl.visible = False
            self.stations.append(st)
            self.ribosomes.append(st)

        # Energy flow network from mitochondria toward ribosomes/nucleus
        for mito in self.mitochondria:
            self.energy_streams.append(EnergyStream(mito, self.nucleus, ENERGY_COLOR, particles=7))
            for ribo in random.sample(self.ribosomes, 3):
                self.energy_streams.append(EnergyStream(mito, ribo, vector(0.35, 0.95, 1.0), particles=5))

    def build_drone(self):
        self.drone = sphere(
            pos=self.drone_pos,
            radius=0.36,
            color=DRONE_COLOR,
            emissive=True,
            shininess=0.8,
            make_trail=True,
            retain=100,
            trail_radius=0.035,
            trail_color=DRONE_COLOR,
        )
        self.drone_aura = ring(
            pos=self.drone_pos,
            axis=vector(0, 1, 0),
            radius=0.62,
            thickness=0.035,
            color=vector(0.0, 0.65, 1.0),
            opacity=0.8,
            emissive=True,
        )
        self.drone_arrow = arrow(
            pos=self.drone_pos,
            axis=vector(0.75, 0, 0),
            shaftwidth=0.09,
            headwidth=0.22,
            headlength=0.28,
            color=vector(0.05, 0.45, 0.65),
        )
        self.drone_label = label(
            pos=self.drone_pos + vector(0, 0.85, 0),
            text="AI enzyme drone",
            height=11,
            color=vector(0.05, 0.15, 0.25),
            box=False,
            opacity=0,
        )

    def build_hud(self):
        self.hud = label(
            pos=vector(0, self.cell_radius + 1.3, 0),
            text="",
            height=13,
            color=vector(0.05, 0.12, 0.2),
            box=False,
            opacity=0,
        )
        self.msg = label(
            pos=vector(0, -self.cell_radius - 1.1, 0),
            text="",
            height=12,
            color=vector(0.05, 0.12, 0.2),
            box=False,
            opacity=0,
        )
        self.msg_timer = 0.0

        self.help_label = label(
            pos=vector(0, -self.cell_radius - 1.8, 0),
            text="Keys: A toggle AI | Space pause | R reset | F feed | Z attach | X detach | M next AI mode | WASD/QE move drone",
            height=11,
            color=vector(0.12, 0.18, 0.25),
            box=False,
            opacity=0,
        )

    def bind_keys(self):
        scene.bind("keydown", self.keydown)
        scene.bind("keyup", self.keyup)

    # --------------------------
    # State / AI Interface
    # --------------------------

    def get_state(self):
        alive = [p for p in self.particles if p.alive]
        raw = [p for p in alive if p.kind == "raw"]
        blueprint = [p for p in alive if p.kind == "blueprint"]
        protein = [p for p in alive if p.kind == "protein"]
        product = [p for p in alive if p.kind == "product"]
        avg_speed = sum(p.last_speed for p in alive) / max(1, len(alive))
        avg_energy_charge = sum(st.charge for st in self.mitochondria) / max(1, len(self.mitochondria))
        return {
            "time": self.t,
            "round_number": self.round_number,
            "round_goal": self.round_goal,
            "spawned_this_round": self.spawned_this_round,
            "completed_products": self.completed_products,
            "active_count": len(alive),
            "raw_count": len(raw),
            "blueprint_count": len(blueprint),
            "protein_count": len(protein),
            "product_count": len(product),
            "avg_speed": avg_speed,
            "avg_energy_charge": avg_energy_charge,
            "drone_pos": self.drone_pos,
            "drone_vel": self.drone_vel,
            "attached_count": len(self.attached_particles),
            "ai_enabled": self.ai.enabled if hasattr(self, "ai") else True,
            "ai_mode": self.ai.mode if hasattr(self, "ai") else "FEED",
        }

    def set_drone_target(self, target):
        if mag(target) > self.cell_radius * 0.94:
            target = safe_norm(target) * self.cell_radius * 0.94
        self.drone_target = target

    # --------------------------
    # Round Management
    # --------------------------

    def reset_round(self, first=False, manual=False):
        for p in self.particles:
            p.remove()
        self.particles = []
        self.attached_particles = []

        for e in self.effects:
            if hasattr(e, "obj"):
                e.obj.visible = False
            if hasattr(e, "bits"):
                for b in e.bits:
                    b[0].visible = False
        self.effects = []

        self.round_number += 1
        self.round_goal = min(28, 10 + self.round_number * 2)
        self.spawned_this_round = 0
        self.completed_products = 0

        self.drone_pos = vector(-4.4, 0, 0)
        self.drone_vel = vector(0, 0, 0)
        self.drone_target = self.drone_pos
        self.drone.pos = self.drone_pos
        try:
            self.drone.clear_trail()
        except Exception:
            pass

        for st in self.stations:
            st.charge = 0.0

        for _ in range(5):
            self.spawn_raw()

        if not first:
            self.effects.append(BurstEffect(vector(0, 0, 0), vector(0.5, 0.9, 1.0), 36, 1.8))
        self.message("New factory round " + str(self.round_number))

    # --------------------------
    # Spawning and Actions
    # --------------------------

    def spawn_raw(self, pos=None):
        if pos is None:
            # Enter through left membrane input port.
            y = randf(-0.75, 0.75)
            z = randf(-0.75, 0.75)
            x = -math.sqrt(max(0, self.cell_radius ** 2 - y ** 2 - z ** 2)) + 0.1
            pos = vector(x, y, z)

        vel = safe_norm(self.nucleus.pos - pos) * randf(0.75, 1.45)
        p = FactoryParticle(self, "raw", pos, vel, target=self.nucleus.pos + random_unit_vector() * 0.4)
        self.particles.append(p)
        self.spawned_this_round += 1
        return p

    def spill_from_drone(self, count=3):
        for _ in range(count):
            if self.spawned_this_round >= self.round_goal + 8:
                return
            p = self.spawn_raw(pos=self.drone_pos + random_unit_vector() * randf(0.2, 0.6))
            p.vel = random_unit_vector() * randf(0.6, 1.9)
        self.effects.append(BurstEffect(self.drone_pos, RAW_COLOR, 10 + count * 3, 1.2))

    def attach_particle(self, p):
        if not p or not p.alive or p.attached:
            return False
        if len(self.attached_particles) >= self.max_attached:
            return False
        p.attached = True
        idx = len(self.attached_particles)
        angle = idx * 2 * math.pi / max(1, self.max_attached)
        p.attach_offset = vector(math.cos(angle) * 0.68, 0.25 * math.sin(angle * 2), math.sin(angle) * 0.68)
        self.attached_particles.append(p)
        self.mark_particle(p, color_value=vector(0.0, 0.95, 1.0))
        return True

    def detach_particle(self, p, toward=None, outward=False):
        if p not in self.attached_particles:
            return
        p.attached = False
        if toward is None:
            p.update_target_by_kind()
            toward = p.target if p.target is not None else p.pos + random_unit_vector()
        direction = safe_norm(toward - p.pos)
        if outward:
            direction = safe_norm(toward - self.drone_pos)
        p.vel = self.drone_vel + direction * randf(1.0, 2.0)
        p.target = toward
        self.attached_particles.remove(p)

    def detach_all(self, toward=None, outward=False):
        for p in list(self.attached_particles):
            self.detach_particle(p, toward=toward, outward=outward)

    def target_for_attached(self):
        if not self.attached_particles:
            return None
        kinds = [p.kind for p in self.attached_particles]
        if "product" in kinds:
            return self.exit_port + vector(1.6, 0, 0)
        if "protein" in kinds:
            st = self.nearest_station(self.drone_pos, "mitochondrion")
            return st.pos if st else None
        if "blueprint" in kinds:
            st = self.nearest_station(self.drone_pos, "ribosome")
            return st.pos if st else None
        if "raw" in kinds:
            return self.nucleus.pos
        return None

    def bounce_near_drone(self, radius=2.0, impulse=1.0):
        for p in self.particles:
            if p.alive and not p.attached:
                d = p.pos - self.drone_pos
                if mag(d) < radius:
                    p.vel += safe_norm(d + random_unit_vector() * 0.2) * impulse
                    self.mark_particle(p, color_value=vector(1.0, 0.45, 0.1))
        self.effects.append(BurstEffect(self.drone_pos, vector(1.0, 0.65, 0.25), 18, 1.0))

    def mark_particle(self, p, color_value=vector(1.0, 0.85, 0.12)):
        if p and p.alive:
            self.effects.append(MarkEffect(p, ttl=4.5, color_value=color_value))
            p.marked = True

    # --------------------------
    # Finders and Interactions
    # --------------------------

    def nearest_station(self, pos, stype=None):
        stations = [s for s in self.stations if stype is None or s.stype == stype]
        if not stations:
            return None
        return min(stations, key=lambda s: mag(s.pos - pos))

    def nearest_particle(self, pos, kinds=None):
        candidates = []
        for p in self.particles:
            if not p.alive or p.attached:
                continue
            if kinds is not None and p.kind not in kinds:
                continue
            candidates.append(p)
        if not candidates:
            return None
        return min(candidates, key=lambda p: mag(p.pos - pos))

    def exit_outside(self):
        return self.exit_port + vector(2.2, randf(-0.45, 0.45), randf(-0.45, 0.45))

    def process_collision(self, p, st):
        if p.kind == "raw" and st.stype == "nucleus":
            p.set_kind("blueprint")
            st.pulse(1.2)
            p.target = self.nearest_station(p.pos, "ribosome").pos
            p.vel += random_unit_vector() * 0.5
            self.effects.append(BurstEffect(st.pos, BLUEPRINT_COLOR, 16, 1.0))
            return True

        if p.kind == "blueprint" and st.stype == "ribosome":
            p.set_kind("protein")
            st.pulse(1.0)
            p.target = self.nearest_station(p.pos, "mitochondrion").pos
            p.vel += safe_norm(p.target - p.pos) * 0.7
            self.effects.append(BurstEffect(st.pos, PROTEIN_COLOR, 10, 0.9))
            return True

        if p.kind == "protein" and st.stype == "mitochondrion":
            p.set_kind("product")
            st.pulse(1.4)
            p.target = self.exit_outside()
            p.vel += safe_norm(self.exit_port - p.pos) * 1.1
            self.effects.append(BurstEffect(st.pos, PRODUCT_COLOR, 20, 1.1))
            return True

        if p.kind == "raw" and st.stype == "ribosome":
            p.vel += safe_norm(p.pos - st.pos) * 0.7
            st.pulse(0.08)
            return False

        if p.kind == "product" and st.stype != "mitochondrion":
            p.vel += safe_norm(self.exit_port - p.pos) * 0.35
            st.pulse(0.05)
            return False

        return False

    def particle_particle_collisions(self):
        alive = [p for p in self.particles if p.alive and not p.attached]
        max_checks = min(len(alive), 50)
        for i in range(max_checks):
            p = alive[i]
            for j in range(i + 1, min(len(alive), i + 7)):
                q = alive[j]
                d = q.pos - p.pos
                dist = mag(d)
                min_dist = p.radius + q.radius
                if dist < min_dist and dist > 1e-6:
                    n = d / dist
                    overlap = min_dist - dist
                    p.pos -= n * overlap * 0.5
                    q.pos += n * overlap * 0.5
                    vp = p.vel
                    p.vel = q.vel * 0.72 + random_unit_vector() * 0.08
                    q.vel = vp * 0.72 + random_unit_vector() * 0.08

                    if (p.kind == "protein" and q.kind == "product") or (q.kind == "protein" and p.kind == "product"):
                        self.mark_particle(p, vector(1.0, 0.95, 0.35))
                        self.mark_particle(q, vector(1.0, 0.95, 0.35))

    # --------------------------
    # Keyboard
    # --------------------------

    def keydown(self, evt):
        k = evt.key
        self.keys[k] = True

        if k in [" ", "space"]:
            self.paused = not self.paused
            self.message("Paused" if self.paused else "Resumed")
        elif k in ["a", "A"]:
            self.ai.enabled = not self.ai.enabled
            self.message("AI enabled" if self.ai.enabled else "AI disabled")
        elif k in ["r", "R"]:
            self.reset_round(manual=True)
        elif k in ["f", "F"]:
            self.spawn_raw()
            self.message("Human feed: raw material inserted")
        elif k in ["z", "Z"]:
            p = self.nearest_particle(self.drone_pos)
            if p and mag(p.pos - self.drone_pos) < 1.6:
                self.attach_particle(p)
                self.message("Human attach")
        elif k in ["x", "X"]:
            self.detach_all(toward=self.target_for_attached())
            self.message("Human detach")
        elif k in ["m", "M"]:
            self.ai.cycle_mode()
        elif k in ["o", "O"]:
            self.effects.append(WrapEffect(random.choice(self.stations)))
        elif k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            idx = int(k) - 1 if k != "0" else 9
            if idx < len(AIController.MODES):
                self.ai.set_mode(AIController.MODES[idx])

    def keyup(self, evt):
        self.keys[evt.key] = False

    def manual_drone_vector(self):
        v = vector(0, 0, 0)
        if self.keys.get("w") or self.keys.get("W"):
            v += vector(0, 1, 0)
        if self.keys.get("s") or self.keys.get("S"):
            v += vector(0, -1, 0)
        if self.keys.get("a") or self.keys.get("A"):
            pass
        if self.keys.get("d") or self.keys.get("D"):
            v += vector(1, 0, 0)
        if self.keys.get("q") or self.keys.get("Q"):
            v += vector(0, 0, 1)
        if self.keys.get("e") or self.keys.get("E"):
            v += vector(0, 0, -1)
        if self.keys.get("j") or self.keys.get("J"):
            v += vector(-1, 0, 0)
        if self.keys.get("l") or self.keys.get("L"):
            v += vector(1, 0, 0)
        if self.keys.get("i") or self.keys.get("I"):
            v += vector(0, 1, 0)
        if self.keys.get("k") or self.keys.get("K"):
            v += vector(0, -1, 0)
        return v

    # --------------------------
    # Visual Updates
    # --------------------------

    def message(self, txt):
        self.msg.text = txt
        self.msg_timer = 3.2

    def update_hud(self, dt):
        state = self.get_state()
        self.hud.text = (
            "Round {round_number} | Goal {round_goal} | Completed {completed_products} | "
            "Active {active_count} | raw {raw_count} blueprint {blueprint_count} protein {protein_count} product {product_count} | "
            "AI {ai_state}: {ai_mode}"
        ).format(
            round_number=state["round_number"],
            round_goal=state["round_goal"],
            completed_products=state["completed_products"],
            active_count=state["active_count"],
            raw_count=state["raw_count"],
            blueprint_count=state["blueprint_count"],
            protein_count=state["protein_count"],
            product_count=state["product_count"],
            ai_state="ON" if self.ai.enabled else "OFF",
            ai_mode=self.ai.mode,
        )

        if self.paused:
            self.hud.text += " | PAUSED"

        self.msg_timer -= dt
        if self.msg_timer <= 0:
            self.msg.text = ""

    def update_drone(self, dt):
        manual = self.manual_drone_vector()
        if mag(manual) > 0:
            self.manual_override_timer = 0.65
            desired_vel = safe_norm(manual) * 3.2
            self.drone_vel += (desired_vel - self.drone_vel) * min(1, dt * 8)
            self.drone_target = self.drone_pos + safe_norm(manual) * 1.5
        else:
            self.manual_override_timer = max(0, self.manual_override_timer - dt)
            if self.manual_override_timer <= 0:
                to_target = self.drone_target - self.drone_pos
                desired = safe_norm(to_target) * clamp(mag(to_target) * 1.4, 0, 3.1)
                self.drone_vel += (desired - self.drone_vel) * min(1, dt * 3.2)
            else:
                self.drone_vel *= 0.94

        self.drone_vel = limit_vec(self.drone_vel, 3.4)
        self.drone_pos += self.drone_vel * dt

        if mag(self.drone_pos) > self.cell_radius * 0.93:
            n = safe_norm(self.drone_pos)
            self.drone_pos = n * self.cell_radius * 0.93
            vn = dot(self.drone_vel, n)
            if vn > 0:
                self.drone_vel -= 1.4 * vn * n

        self.drone.pos = self.drone_pos
        self.drone_aura.pos = self.drone_pos
        self.drone_aura.axis = vector(math.sin(self.t * 1.3), 1, math.cos(self.t * 1.1))
        self.drone_aura.radius = 0.62 + 0.08 * math.sin(self.t * 5)

        axis = self.drone_vel
        if mag(axis) < 0.1:
            axis = self.drone_target - self.drone_pos
        self.drone_arrow.pos = self.drone_pos
        self.drone_arrow.axis = safe_norm(axis) * 0.8

        self.drone_label.pos = self.drone_pos + vector(0, 0.85, 0)

        for i, p in enumerate(self.attached_particles):
            a = self.t * 2.0 + i * 2 * math.pi / max(1, len(self.attached_particles))
            p.attach_offset = vector(math.cos(a) * 0.7, 0.18 * math.sin(a * 2), math.sin(a) * 0.7)

    # --------------------------
    # Main Update
    # --------------------------

    def update(self, dt):
        self.t += dt

        self.membrane_outline.rotate(angle=dt * 0.08, axis=vector(0, 1, 0), origin=vector(0, 0, 0))
        self.entry_ring.rotate(angle=dt * 0.8, axis=vector(1, 0, 0), origin=self.entry_port)
        self.exit_ring.rotate(angle=-dt * 0.9, axis=vector(1, 0, 0), origin=self.exit_port)

        for st in self.stations:
            st.update(self.t, dt)

        for stream in self.energy_streams:
            stream.update(self.t, dt)

        if not self.paused:
            self.ai.update(dt)
            self.update_drone(dt)

            for p in list(self.particles):
                p.update(dt)

            self.particle_particle_collisions()

            self.particles = [p for p in self.particles if p.alive]

        for e in list(self.effects):
            if not e.update(dt):
                self.effects.remove(e)

        self.update_hud(dt)

# --------------------------
# Run
# --------------------------

sim = CellFactorySimulation()


# --------------------------
# CSV snapshot helpers
# --------------------------
def _csv_base_row(csv_elapsed_seconds, frame, row_type, object_id="", object_kind=""):
    state = sim.get_state()
    row = {
        "csv_run_id": CSV_RUN_ID,
        "csv_elapsed_seconds": round(csv_elapsed_seconds, 4),
        "simulation_time": round(sim.t, 4),
        "frame": frame,
        "row_type": row_type,
        "object_id": object_id,
        "object_kind": object_kind,
        "round_number": state["round_number"],
        "round_goal": state["round_goal"],
        "spawned_this_round": state["spawned_this_round"],
        "completed_products": state["completed_products"],
        "active_count": state["active_count"],
        "raw_count": state["raw_count"],
        "blueprint_count": state["blueprint_count"],
        "protein_count": state["protein_count"],
        "product_count": state["product_count"],
        "avg_speed": state["avg_speed"],
        "avg_energy_charge": state["avg_energy_charge"],
        "ai_enabled": state["ai_enabled"],
        "ai_mode": state["ai_mode"],
        "ai_stagnant_time": getattr(sim.ai, "stagnant_time", ""),
        "ai_completion_time": getattr(sim.ai, "completion_time", ""),
        "paused": sim.paused,
        "attached_count": len(sim.attached_particles),
        "particle_count": len([p for p in sim.particles if p.alive]),
        "effect_count": len(sim.effects),
        "station_count": len(sim.stations),
        "energy_stream_count": len(sim.energy_streams),
    }
    row.update(_v_components(sim.drone_pos, "drone_"))
    row.update(_v_components(sim.drone_vel, "drone_v"))
    row.update(_v_components(sim.drone_target, "drone_target_"))
    return row


def write_csv_snapshot(csv_elapsed_seconds, frame):
    _csv_writer.writerow(_csv_base_row(csv_elapsed_seconds, frame, "summary", "cell_factory", "summary"))

    drone_row = _csv_base_row(csv_elapsed_seconds, frame, "drone", "ai_enzyme_drone", "drone")
    drone_row.update(_v_components(sim.drone_pos, ""))
    drone_row.update(_v_components(sim.drone_vel, "v"))
    drone_row.update(_v_components(sim.drone_target, "target_"))
    _csv_writer.writerow(drone_row)

    for i, p in enumerate(sim.particles):
        row = _csv_base_row(csv_elapsed_seconds, frame, "particle", f"particle_{p.id}", "particle")
        row.update({
            "particle_id": p.id,
            "kind": p.kind,
            "alive": p.alive,
            "attached": p.attached,
            "marked": p.marked,
            "age": p.age,
            "processing_cooldown": p.processing_cooldown,
            "radius": p.radius,
            "last_speed": p.last_speed,
        })
        row.update(_v_components(p.pos, ""))
        row.update(_v_components(p.vel, "v"))
        if p.target is not None:
            row.update(_v_components(p.target, "target_"))
        _csv_writer.writerow(row)

    for i, p in enumerate(sim.attached_particles):
        row = _csv_base_row(csv_elapsed_seconds, frame, "attached_particle", f"attached_particle_{p.id}", "attached_particle")
        row.update({
            "particle_id": p.id,
            "kind": p.kind,
            "alive": p.alive,
            "attached": p.attached,
            "marked": p.marked,
            "age": p.age,
            "radius": p.radius,
            "last_speed": p.last_speed,
        })
        row.update(_v_components(p.pos, ""))
        row.update(_v_components(p.vel, "v"))
        _csv_writer.writerow(row)

    for i, st in enumerate(sim.stations):
        row = _csv_base_row(csv_elapsed_seconds, frame, "station", f"station_{i}", "station")
        row.update({
            "station_name": st.name.replace("\n", " "),
            "station_type": st.stype,
            "station_charge": st.charge,
            "station_touch_count": st.touch_count,
            "station_last_touched": st.last_touched,
            "radius": st.radius,
        })
        row.update(_v_components(st.pos, ""))
        _csv_writer.writerow(row)

    for i, e in enumerate(sim.effects):
        row = _csv_base_row(csv_elapsed_seconds, frame, "effect", f"effect_{i}", "effect")
        row.update({
            "effect_type": type(e).__name__,
            "age": getattr(e, "age", ""),
            "radius": getattr(getattr(e, "obj", None), "radius", ""),
        })
        _csv_writer.writerow(row)

    _csv_file.flush()

last = time.time()
csv_elapsed_seconds = 0.0
csv_sample_timer = CSV_SAMPLE_INTERVAL
csv_frame = 0

try:
    while csv_elapsed_seconds < CSV_RUN_SECONDS:
        rate(60)
        now = time.time()
        dt = clamp(now - last, 0.001, 0.04)
        last = now

        csv_frame += 1
        csv_elapsed_seconds += dt
        csv_sample_timer += dt

        sim.update(dt)

        if csv_sample_timer >= CSV_SAMPLE_INTERVAL:
            csv_sample_timer = 0.0
            write_csv_snapshot(csv_elapsed_seconds, csv_frame)

    write_csv_snapshot(csv_elapsed_seconds, csv_frame)
    sim.message(f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}")
    sim.update_hud(0.0)
finally:
    _csv_file.flush()
    _csv_file.close()
