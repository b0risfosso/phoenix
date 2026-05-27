from vpython import *
import random
import math
import time
import csv
import os
from datetime import datetime

# ============================================================
# Cellular Conveyor Belt: Golgi Apparatus
# Web-app-compatible CSV storage version
# ============================================================

scene = canvas(
    title="Cellular Conveyor Belt: Golgi Apparatus - CSV Storage Version",
    width=1280,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0.2, 0),
)
scene.forward = vector(-7.5, -3.0, -6.5)
scene.up = vector(0, 1, 0)
scene.range = 7.3
scene.ambient = color.gray(0.72)

scene.append_to_caption(
    "\nCSV storage version. Controls: SPACE pause/resume | A toggle AI | R reset | "
    "S spawn | B burst | N select | D detach selected | Arrow keys/IJKL nudge selected.\n"
)

# ----------------------------
# CSV storage configuration
# ----------------------------

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10
CSV_STATIC_SAMPLE_INTERVAL = 1.00

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-golgi-conveyor-state-log.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "golgi_conveyor_state_log.csv"),
    )

csv_run_id = _csv_run_id

CSV_FIELDS = [
    "run_id", "time", "round", "row_type", "object_id", "object_name", "state",
    "ai_enabled", "ai_mode", "paused", "flow_speed", "delivered_round",
    "total_delivered", "active_vesicles", "incoming_count", "attached_count",
    "transfer_count", "outgoing_count", "particle_count", "membrane_mark_count",
    "selected_vesicle_id", "x", "y", "z", "vx", "vy", "vz", "radius",
    "progress", "cis_index", "s", "age", "stall_time", "target_x", "target_y",
    "target_z", "cargo_x", "cargo_y", "cargo_z", "color_r", "color_g",
    "color_b", "opacity", "life", "max_life", "cisterna_index", "cisterna_y",
    "receptor_index", "membrane_x", "drone_x", "drone_y", "drone_z",
    "stagnation_time", "completion_time",
]

# ----------------------------
# Simulation constants/state
# ----------------------------

NUM_CISTERNAE = 6
MEMBRANE_X = 5.55
VESICLE_LIMIT = 42
ROUND_GOAL = 22

vesicles = []
particles = []
membrane_marks = []
cisternae = []
receptors = []

paused = False
sim_time = 0.0
round_number = 1
delivered_round = 0
total_delivered = 0
manual_selected_index = 0
flow_speed = 1.0
last_spawn_time = 0.0

# ----------------------------
# Utility functions
# ----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def safe_norm(v, fallback=vector(0, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def lerp(a, b, t):
    return a * (1 - t) + b * t

def color_lerp(c1, c2, t):
    return vector(c1.x * (1 - t) + c2.x * t, c1.y * (1 - t) + c2.y * t, c1.z * (1 - t) + c2.z * t)

def random_unit_vector():
    theta = random.uniform(0, 2 * math.pi)
    z = random.uniform(-0.7, 0.7)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))

def mature_color(progress):
    palette = [
        vector(0.25, 0.65, 1.00),
        vector(0.20, 0.92, 0.75),
        vector(0.40, 0.92, 0.35),
        vector(1.00, 0.84, 0.25),
        vector(1.00, 0.50, 0.20),
        vector(1.00, 0.28, 0.55),
        vector(0.72, 0.38, 1.00),
    ]
    progress = clamp(progress, 0, 1)
    scaled = progress * (len(palette) - 1)
    i = int(math.floor(scaled))
    if i >= len(palette) - 1:
        return palette[-1]
    return color_lerp(palette[i], palette[i + 1], scaled - i)

def hue_color(h):
    return color.hsv_to_rgb(vector(h % 1.0, 0.72, 1.0))

# ----------------------------
# Static scene
# ----------------------------

floor = box(pos=vector(0, -3.55, 0), size=vector(12.5, 0.035, 7.6), color=vector(0.88, 0.93, 0.96), opacity=0.38)
membrane = box(pos=vector(MEMBRANE_X, 0, 0), size=vector(0.12, 7.2, 5.4), color=vector(0.52, 0.78, 1.0), opacity=0.20)
status_label = label(pos=vector(0, 4.05, 0), text="", height=14, box=True, border=7, color=vector(0.12, 0.18, 0.22), background=vector(0.96, 0.99, 1.0), opacity=0.72)
selector_ring = ring(pos=vector(0, -20, 0), axis=vector(0, 1, 0), radius=0.34, thickness=0.018, color=vector(0.1, 0.2, 0.3), opacity=0.85)

label(pos=vector(MEMBRANE_X + 0.13, 3.75, 0), text="Cell membrane / delivery zone", height=14, box=False, color=vector(0.22, 0.36, 0.45))
label(pos=vector(-3.65, -2.95, 0.25), text="cis face: vesicles attach", height=13, box=False, color=vector(0.15, 0.35, 0.55))
label(pos=vector(3.25, 2.95, 0.25), text="trans face: mature vesicles detach", height=13, box=False, color=vector(0.55, 0.2, 0.38))

for i in range(18):
    y = random.uniform(-2.8, 2.8)
    z = random.uniform(-2.15, 2.15)
    receptors.append(ring(pos=vector(MEMBRANE_X - 0.09, y, z), axis=vector(1, 0, 0), radius=random.uniform(0.11, 0.18), thickness=0.015, color=vector(0.25, 0.58, 0.9), opacity=0.50))

# ----------------------------
# Golgi objects
# ----------------------------

class Cisterna:
    def __init__(self, index, y, base_color):
        self.index = index
        self.y = y
        self.base_color = base_color
        self.objects = []
        self.width = 0.95 + 0.08 * math.sin(index)
        self.thickness = 0.065
        self.a = 2.75 - 0.08 * index
        self.b = 0.72 + 0.035 * index
        self.xoff = -0.18 + 0.06 * math.sin(index * 0.8)
        self.zoff = 0.04 * math.cos(index)

        for j in range(36):
            s = (j + 0.5) / 36
            p = self.path(s)
            tangent = self.tangent(s)
            self.objects.append(box(pos=p, axis=tangent, size=vector(0.26, self.thickness, self.width), color=base_color, opacity=0.28))

        for side in [-1, 1]:
            pts = []
            for j in range(60):
                s = j / 59
                tangent = self.tangent(s)
                normal_xz = safe_norm(cross(vector(0, 1, 0), tangent), vector(1, 0, 0))
                pts.append(self.path(s) + normal_xz * side * self.width * 0.53)
            self.objects.append(curve(pos=pts, radius=0.018, color=color_lerp(base_color, vector(1, 1, 1), 0.22), opacity=0.52))

        self.cis_port = sphere(pos=self.surface_point(0.0) + vector(-0.13, 0, 0), radius=0.085, color=vector(0.34, 0.68, 1.0), opacity=0.75)
        self.trans_port = sphere(pos=self.surface_point(1.0) + vector(0.13, 0, 0), radius=0.085, color=vector(1.0, 0.45, 0.62), opacity=0.75)
        self.objects.extend([self.cis_port, self.trans_port])

    def path(self, s):
        s = clamp(s, 0, 1)
        theta = math.pi * (1 - s)
        x = self.xoff + self.a * math.cos(theta)
        z = self.zoff + self.b * math.sin(theta) + 0.10 * math.sin(2 * theta + self.index * 0.35)
        return vector(x, self.y, z)

    def tangent(self, s):
        s = clamp(s, 0, 1)
        theta = math.pi * (1 - s)
        dx = self.a * math.pi * math.sin(theta)
        dz = -self.b * math.pi * math.cos(theta) - 0.20 * math.pi * math.cos(2 * theta + self.index * 0.35)
        return safe_norm(vector(dx, 0, dz), vector(1, 0, 0))

    def surface_point(self, s, lift=0.22, side_wobble=0.0):
        tangent = self.tangent(s)
        normal_xz = safe_norm(cross(vector(0, 1, 0), tangent), vector(1, 0, 0))
        return self.path(s) + vector(0, lift, 0) + normal_xz * side_wobble

    def pulse(self, amount):
        for obj in self.objects:
            if hasattr(obj, "opacity"):
                obj.opacity = clamp(0.22 + amount, 0.15, 0.55)

    def restore_opacity(self):
        for obj in self.objects:
            if hasattr(obj, "opacity"):
                obj.opacity = 0.28 if isinstance(obj, box) else 0.52

class Particle:
    def __init__(self, pos, vel, col, radius=0.035, life=1.2, opacity=0.75):
        self.life = life
        self.max_life = life
        self.vel = vel
        self.obj = sphere(pos=pos, radius=radius, color=col, opacity=opacity)

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.obj.pos += self.vel * dt
        self.obj.opacity = clamp(0.75 * self.life / self.max_life, 0, 0.75)
        self.obj.radius *= 0.997
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True

def spill_particles(pos, col, count=10, speed=0.8, life=1.1):
    for _ in range(count):
        if len(particles) > 280:
            break
        particles.append(Particle(pos, random_unit_vector() * random.uniform(0.15, speed), col, radius=random.uniform(0.018, 0.045), life=random.uniform(0.55, life)))

def create_membrane_mark(pos, col):
    if len(membrane_marks) > 90:
        old = membrane_marks.pop(0)
        old.visible = False
    membrane_marks.append(ring(pos=vector(MEMBRANE_X - 0.13, pos.y, pos.z), axis=vector(1, 0, 0), radius=random.uniform(0.12, 0.25), thickness=0.018, color=col, opacity=0.72))

class Vesicle:
    next_id = 0

    def __init__(self, pos=None, artistic_hue=None):
        self.id = Vesicle.next_id
        Vesicle.next_id += 1
        if pos is None:
            pos = vector(-5.2 + random.uniform(-0.35, 0.15), cisternae[0].y + random.uniform(-0.24, 0.24), random.uniform(-0.75, 0.75))
        self.radius = random.uniform(0.115, 0.165)
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(random.uniform(0.15, 0.45), random.uniform(-0.05, 0.05), random.uniform(-0.08, 0.08))
        self.state = "incoming"
        self.cis_index = 0
        self.s = 0.0
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.age = 0.0
        self.stall_time = 0.0
        self.artistic_hue = artistic_hue
        self.target = cisternae[0].surface_point(0.0, lift=0.26) + vector(-0.25, random.uniform(-0.08, 0.12), random.uniform(-0.18, 0.18))
        self.mem_target = None
        self.just_changed = True

        col = mature_color(0) if artistic_hue is None else hue_color(artistic_hue)
        self.body = sphere(pos=self.pos, radius=self.radius, color=col, opacity=0.88, shininess=0.7, make_trail=True, retain=85, trail_radius=0.014, trail_color=col)
        self.cargo = sphere(pos=self.pos + vector(self.radius * 0.38, self.radius * 0.20, 0), radius=self.radius * 0.28, color=color_lerp(col, vector(1, 1, 1), 0.50), opacity=0.92)
        self.halo = ring(pos=self.pos, axis=vector(0, 1, 0), radius=self.radius * 1.45, thickness=0.012, color=vector(1, 1, 1), opacity=0.0, visible=True)
        self.marker = sphere(pos=self.pos, radius=self.radius * 0.18, color=vector(1, 1, 1), opacity=0.0)

    def progress(self):
        if self.state == "delivered":
            return NUM_CISTERNAE + 1
        if self.state == "outgoing":
            return NUM_CISTERNAE + 0.5
        return self.cis_index + clamp(self.s, 0, 1)

    def set_state(self, state):
        if self.state != state:
            self.just_changed = True
            self.stall_time = 0
            self.state = state

    def current_color(self):
        p = clamp((self.cis_index + self.s) / max(1, NUM_CISTERNAE - 1), 0, 1)
        col = mature_color(p)
        if self.artistic_hue is not None:
            col = color_lerp(col, hue_color(self.artistic_hue + 0.23 * p), 0.42)
        return col

    def attach_to_current(self):
        self.set_state("attached")
        self.s = 0.0
        self.vel = vector(0, 0, 0)
        self.halo.opacity = 0.62
        self.halo.color = color_lerp(self.current_color(), vector(1, 1, 1), 0.45)
        spill_particles(self.pos, self.current_color(), count=5, speed=0.25, life=0.65)

    def force_detach(self, strength=1.0):
        if self.state == "attached":
            self.set_state("transfer")
            self.halo.opacity = 0.0
            self.vel = (cisternae[self.cis_index].tangent(self.s) + random_unit_vector() * 0.45) * strength
        elif self.state in ["incoming", "transfer"]:
            self.vel += random_unit_vector() * strength
        elif self.state == "outgoing":
            self.vel += vector(1, 0, 0) * strength + random_unit_vector() * strength * 0.35
        spill_particles(self.pos, vector(1, 0.6, 0.3), count=6, speed=0.5, life=0.8)

    def choose_membrane_target(self):
        rec = random.choice(receptors)
        self.mem_target = rec.pos + vector(-0.05, random.uniform(-0.08, 0.08), random.uniform(-0.08, 0.08))

    def update_visuals(self):
        col = self.current_color()
        self.body.color = col
        self.cargo.color = color_lerp(col, vector(1, 1, 1), 0.52)
        self.cargo.pos = self.body.pos + vector(self.radius * 0.34 * math.cos(self.age * 3.0), self.radius * 0.28 * math.sin(self.age * 2.3), self.radius * 0.31 * math.sin(self.age * 2.0))
        self.halo.pos = self.body.pos
        self.halo.axis = vector(0.2 * math.sin(self.age * 1.7), 1, 0.2 * math.cos(self.age * 1.5))
        self.marker.pos = self.body.pos + vector(0, self.radius * 1.2, 0)

    def seek(self, target, speed, dt, agility=4.0):
        to_target = target - self.pos
        dist = mag(to_target)
        if dist > 1e-5:
            self.vel = lerp(self.vel, norm(to_target) * speed, clamp(agility * dt, 0, 1))
        self.pos += self.vel * dt
        return dist

    def update(self, dt):
        self.age += dt
        old_progress = self.progress()
        self.orbit_phase += dt * (4.5 + self.cis_index * 0.5)

        if self.state == "incoming":
            self.halo.opacity = 0.0
            d = self.seek(self.target, speed=1.10 * flow_speed, dt=dt, agility=3.2)
            self.pos += vector(0, math.sin(self.age * 4.0 + self.id) * 0.004, math.cos(self.age * 3.2) * 0.004)
            if d < 0.18:
                self.attach_to_current()

        elif self.state == "attached":
            c = cisternae[self.cis_index]
            self.s += dt * (0.135 + 0.025 * self.cis_index) * flow_speed
            wobble = 0.16 * math.sin(self.orbit_phase)
            lift = 0.25 + 0.055 * math.cos(self.orbit_phase * 1.2)
            self.pos = c.surface_point(self.s, lift=lift, side_wobble=wobble)
            self.halo.opacity = 0.60 + 0.18 * math.sin(self.age * 8.0)
            self.halo.radius = self.radius * (1.45 + 0.12 * math.sin(self.age * 7.0))
            if random.random() < 0.012 * flow_speed:
                spill_particles(self.pos, self.current_color(), count=1, speed=0.18, life=0.55)
            if self.s >= 1.0:
                self.halo.opacity = 0.0
                if self.cis_index < NUM_CISTERNAE - 1:
                    self.cis_index += 1
                    self.s = 0.0
                    self.target = cisternae[self.cis_index].surface_point(0.0, lift=0.27) + vector(-0.20, random.uniform(-0.05, 0.08), random.uniform(-0.16, 0.16))
                    self.vel = vector(0.50, 0.30, random.uniform(-0.10, 0.10))
                    self.set_state("transfer")
                    spill_particles(self.pos, self.current_color(), count=7, speed=0.35, life=0.75)
                else:
                    self.choose_membrane_target()
                    self.vel = vector(1.8, random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
                    self.set_state("outgoing")
                    spill_particles(self.pos, self.current_color(), count=9, speed=0.50, life=0.85)

        elif self.state == "transfer":
            self.halo.opacity = 0.0
            d = self.seek(self.target, speed=1.28 * flow_speed, dt=dt, agility=3.6)
            self.pos += random_unit_vector() * 0.006
            if d < 0.18:
                self.attach_to_current()

        elif self.state == "outgoing":
            self.halo.opacity = 0.0
            if self.mem_target is None:
                self.choose_membrane_target()
            d = self.seek(self.mem_target, speed=2.15 * flow_speed, dt=dt, agility=4.8)
            if random.random() < 0.020:
                spill_particles(self.pos, self.current_color(), count=1, speed=0.22, life=0.45)
            if self.pos.x >= MEMBRANE_X - 0.22 or d < 0.16:
                self.deliver()
                return False

        self.body.pos = self.pos
        self.update_visuals()
        self.stall_time = self.stall_time + dt if abs(self.progress() - old_progress) < 0.0003 else 0
        return True

    def deliver(self):
        global delivered_round, total_delivered
        self.set_state("delivered")
        delivered_round += 1
        total_delivered += 1
        col = self.current_color()
        create_membrane_mark(self.pos, col)
        spill_particles(self.pos, col, count=18, speed=0.95, life=1.35)
        self.visible_off()

    def visible_off(self):
        for obj in [self.body, self.cargo, self.halo, self.marker]:
            obj.visible = False
        try:
            self.body.clear_trail()
        except Exception:
            pass

# ----------------------------
# Spawning/reset
# ----------------------------

def spawn_vesicle(pos=None, artistic_hue=None):
    global last_spawn_time
    if len(vesicles) >= VESICLE_LIMIT:
        return None
    v = Vesicle(pos=pos, artistic_hue=artistic_hue)
    vesicles.append(v)
    last_spawn_time = sim_time
    return v

def spawn_burst(count=5, artistic=False):
    for i in range(count):
        hue = (sim_time * 0.055 + i / max(1, count)) % 1.0 if artistic else None
        pos = vector(-5.4 + random.uniform(-0.28, 0.18), cisternae[0].y + random.uniform(-0.38, 0.38), random.uniform(-1.0, 1.0))
        spawn_vesicle(pos=pos, artistic_hue=hue)

def clear_dynamic_objects():
    global vesicles, particles, membrane_marks
    for v in vesicles:
        v.visible_off()
    vesicles = []
    for p in particles:
        p.obj.visible = False
    particles = []
    for m in membrane_marks:
        m.visible = False
    membrane_marks = []

def reset_simulation(spawn_initial=True, new_round=True):
    global delivered_round, round_number, flow_speed, manual_selected_index
    clear_dynamic_objects()
    delivered_round = 0
    manual_selected_index = 0
    flow_speed = 1.0
    if new_round:
        round_number += 1
    for c in cisternae:
        c.restore_opacity()
    if spawn_initial:
        spawn_burst(5, artistic=False)

# ----------------------------
# AI
# ----------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode_names = ["careful", "constructive", "organize", "curious", "ritual", "artistic", "chaotic", "destructive"]
        self.mode = "constructive"
        self.previous_mode = None
        self.mode_started = 0.0
        self.next_switch = 10.0
        self.last_metric = 0.0
        self.last_change_time = 0.0
        self.completion_time = None
        self.stagnation_time = 0.0
        self.pulse_timer = 0.0
        self.action_timer = 0.0
        self.override_until = 0.0
        self.loop_delay = 2.5
        self.drone = sphere(pos=vector(-4.6, 3.35, 0), radius=0.15, color=vector(0.84, 0.38, 1.0), emissive=True, make_trail=True, retain=140, trail_radius=0.012, trail_color=vector(0.7, 0.4, 1.0))
        self.drone_ring = ring(pos=self.drone.pos, axis=vector(0, 1, 0), radius=0.27, thickness=0.015, color=self.drone.color, opacity=0.75)
        self.mode_label = label(pos=self.drone.pos + vector(0, 0.45, 0), text="AI: constructive", height=12, box=False, color=vector(0.35, 0.18, 0.45))

    def read_state(self):
        active = [v for v in vesicles if v.state != "delivered"]
        attached = [v for v in active if v.state == "attached"]
        free = [v for v in active if v.state in ["incoming", "transfer", "outgoing"]]
        outgoing = [v for v in active if v.state == "outgoing"]
        stalled = [v for v in active if v.stall_time > 5.0]
        progress_metric = sum(v.progress() for v in active) + delivered_round * (NUM_CISTERNAE + 2)
        avg_progress = sum(v.progress() for v in active) / max(1, len(active))
        return {
            "active": active, "attached": attached, "free": free, "outgoing": outgoing,
            "stalled": stalled, "count": len(active), "attached_count": len(attached),
            "free_count": len(free), "outgoing_count": len(outgoing),
            "delivered_round": delivered_round, "progress_metric": progress_metric,
            "avg_progress": avg_progress,
        }

    def detect_stagnation_or_completion(self, state, dt):
        metric = state["progress_metric"]
        if abs(metric - self.last_metric) > 0.03:
            self.last_change_time = sim_time
            self.last_metric = metric
        no_active = state["count"] == 0
        complete = delivered_round >= ROUND_GOAL and no_active
        empty = no_active and sim_time - last_spawn_time > 2.5
        if complete or empty:
            if self.completion_time is None:
                self.completion_time = sim_time
            return "complete" if complete else "empty"
        self.completion_time = None
        if sim_time - self.last_change_time > 13.0 and sim_time > 5.0:
            self.stagnation_time += dt
            if self.stagnation_time > 2.0:
                return "stagnant"
        else:
            self.stagnation_time = 0.0
        return "moving"

    def choose_new_mode(self, reason="timer"):
        choices = [m for m in self.mode_names if m != self.mode]
        if reason == "empty":
            preferred = [m for m in ["constructive", "ritual", "artistic"] if m != self.mode]
            choices = preferred or choices
        elif reason == "stagnant":
            preferred = [m for m in ["chaotic", "curious", "destructive", "constructive"] if m != self.mode]
            choices = preferred or choices
        self.previous_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_started = sim_time
        self.next_switch = random.uniform(8.0, 18.0)
        self.pulse_timer = 0
        self.action_timer = 0
        self.mode_label.text = "AI: " + self.mode

    def next_mode_manual(self):
        idx = self.mode_names.index(self.mode)
        self.mode = self.mode_names[(idx + 1) % len(self.mode_names)]
        self.mode_started = sim_time
        self.mode_label.text = "AI: " + self.mode

    def update_drone(self, dt, state):
        if not self.enabled:
            target = vector(-5.0, 3.35, -1.7)
            self.drone.color = vector(0.55, 0.55, 0.60)
        elif self.mode == "curious" and state["active"]:
            target = min(state["active"], key=lambda v: v.progress()).pos + vector(0, 0.55, 0)
            self.drone.color = vector(0.80, 0.45, 1.0)
        elif self.mode == "organize" and state["active"]:
            avg = vector(0, 0, 0)
            for v in state["active"]:
                avg += v.pos
            target = avg / len(state["active"]) + vector(0, 0.85, 0)
            self.drone.color = vector(0.45, 0.72, 1.0)
        elif self.mode == "artistic":
            angle = sim_time * 1.25
            target = vector(-0.4 + 3.9 * math.cos(angle), 2.7 + 0.45 * math.sin(angle * 0.7), 2.2 * math.sin(angle))
            self.drone.color = vector(1.0, 0.32, 0.72)
        elif self.mode == "chaotic":
            target = vector(random.uniform(-4.2, 4.8), random.uniform(-2.2, 3.4), random.uniform(-2.2, 2.2))
            self.drone.color = vector(1.0, 0.58, 0.15)
        else:
            angle = sim_time * 0.45
            target = vector(-2.6 + math.cos(angle), 3.25 + 0.15 * math.sin(angle), 1.5 * math.sin(angle))
            self.drone.color = vector(0.25, 0.95, 0.55) if self.mode == "constructive" else vector(0.28, 0.65, 1.0)
        self.drone.pos = lerp(self.drone.pos, target, clamp(dt * 2.4, 0, 1))
        self.drone_ring.pos = self.drone.pos
        self.drone_ring.color = self.drone.color
        self.drone_ring.axis = vector(math.sin(sim_time * 2.2), 1, math.cos(sim_time * 2.0))
        self.mode_label.pos = self.drone.pos + vector(0, 0.42, 0)
        self.mode_label.text = "AI: " + ("off" if not self.enabled else self.mode)

    def organize_spacing(self, state, dt):
        for v in state["active"]:
            if v.state == "attached":
                v.pos.z = lerp(v.pos.z, 0.14 * math.sin(v.cis_index * 1.3 + v.id), dt * 0.5)
            elif v.state in ["incoming", "transfer"]:
                v.vel.z += (((v.id % 5) - 2) * 0.22 - v.pos.z) * dt * 0.8

    def nudge_stalled(self, state, strength=0.65):
        targets = state["stalled"] if state["stalled"] else state["active"]
        if targets:
            v = random.choice(targets)
            v.force_detach(strength)
            spill_particles(v.pos, self.drone.color, count=7, speed=0.55, life=0.9)

    def update(self, dt):
        global flow_speed
        state = self.read_state()
        self.update_drone(dt, state)
        if not self.enabled:
            return
        detector = self.detect_stagnation_or_completion(state, dt)
        if detector in ["complete", "empty"] and self.completion_time is not None and sim_time - self.completion_time > self.loop_delay:
            reset_simulation(spawn_initial=True, new_round=True)
            self.completion_time = None
            self.last_change_time = sim_time
            self.choose_new_mode(detector)
            return
        if detector == "stagnant":
            self.choose_new_mode("stagnant")
            if state["count"] == 0:
                spawn_burst(5, artistic=True)
            else:
                self.nudge_stalled(state, 1.2)
            self.last_change_time = sim_time
        if sim_time - self.mode_started > self.next_switch:
            self.choose_new_mode("timer")
        if state["count"] == 0 and delivered_round < ROUND_GOAL:
            self.choose_new_mode("empty")
            spawn_burst(4, artistic=self.mode in ["artistic", "chaotic"])

        self.action_timer += dt
        self.pulse_timer += dt
        if self.mode == "careful":
            flow_speed = lerp(flow_speed, 0.75, dt * 0.8)
            if state["count"] < 5 and self.action_timer > 1.8:
                spawn_vesicle()
                self.action_timer = 0
            self.organize_spacing(state, dt)
        elif self.mode == "constructive":
            flow_speed = lerp(flow_speed, 1.15, dt * 0.9)
            if state["count"] < 14 and self.action_timer > random.uniform(0.45, 1.05):
                spawn_vesicle()
                self.action_timer = 0
            if state["count"] < 4:
                spawn_burst(3)
        elif self.mode == "organize":
            flow_speed = lerp(flow_speed, 0.95, dt)
            self.organize_spacing(state, dt)
            if state["count"] < 7:
                spawn_vesicle()
        elif self.mode == "artistic":
            flow_speed = lerp(flow_speed, 1.22, dt * 0.8)
            if self.action_timer > 0.95 and state["count"] < 20:
                spawn_vesicle(artistic_hue=(sim_time * 0.072 + random.random() * 0.14) % 1.0)
                self.action_timer = 0
        elif self.mode == "chaotic":
            flow_speed = lerp(flow_speed, 1.78, dt * 1.8)
            if self.action_timer > random.uniform(0.55, 1.3):
                if random.random() < 0.58:
                    spawn_burst(random.randint(2, 5), artistic=random.random() < 0.45)
                self.nudge_stalled(state, random.uniform(0.7, 1.4))
                for v in random.sample(state["active"], min(len(state["active"]), random.randint(1, 4))):
                    v.vel += random_unit_vector() * random.uniform(0.35, 1.0)
                self.action_timer = 0
        elif self.mode == "destructive":
            flow_speed = lerp(flow_speed, 1.55, dt * 1.3)
            if self.action_timer > 1.25:
                targets = state["attached"] if state["attached"] else state["active"]
                for v in random.sample(targets, min(len(targets), 3)):
                    v.force_detach(random.uniform(0.8, 1.5))
                self.action_timer = 0

# ----------------------------
# Setup
# ----------------------------

cisterna_colors = [
    vector(0.62, 0.85, 1.0),
    vector(0.57, 0.92, 0.92),
    vector(0.66, 0.95, 0.72),
    vector(1.00, 0.92, 0.58),
    vector(1.00, 0.74, 0.55),
    vector(1.00, 0.62, 0.78),
]
for i in range(NUM_CISTERNAE):
    cisternae.append(Cisterna(i, -2.35 + i * 0.88, cisterna_colors[i]))

ai = AIController()

# ----------------------------
# CSV helpers
# ----------------------------

csv_file = None
csv_writer = None

def color_fields(c):
    return {"color_r": getattr(c, "x", ""), "color_g": getattr(c, "y", ""), "color_b": getattr(c, "z", "")}

def active_vesicles():
    return [v for v in vesicles if v.state != "delivered"]

def state_counts(active):
    counts = {"incoming": 0, "attached": 0, "transfer": 0, "outgoing": 0}
    for v in active:
        if v.state in counts:
            counts[v.state] += 1
    return counts

def selected_vesicle():
    active = active_vesicles()
    if not active:
        return None
    global manual_selected_index
    manual_selected_index %= len(active)
    return active[manual_selected_index]

def open_csv_storage():
    global csv_file, csv_writer
    os.makedirs(os.path.dirname(CSV_OUTPUT_PATH) or ".", exist_ok=True)
    csv_file = open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS, extrasaction="ignore")
    csv_writer.writeheader()
    csv_file.flush()

def close_csv_storage():
    global csv_file
    if csv_file is not None:
        csv_file.flush()
        csv_file.close()
        csv_file = None

def write_csv_row(row):
    if csv_writer is None:
        return
    active = active_vesicles()
    counts = state_counts(active)
    selected = selected_vesicle()
    base = {
        "run_id": csv_run_id,
        "time": round(sim_time, 4),
        "round": round_number,
        "ai_enabled": ai.enabled,
        "ai_mode": ai.mode,
        "paused": paused,
        "flow_speed": round(flow_speed, 5),
        "delivered_round": delivered_round,
        "total_delivered": total_delivered,
        "active_vesicles": len(active),
        "incoming_count": counts["incoming"],
        "attached_count": counts["attached"],
        "transfer_count": counts["transfer"],
        "outgoing_count": counts["outgoing"],
        "particle_count": len(particles),
        "membrane_mark_count": len(membrane_marks),
        "selected_vesicle_id": "" if selected is None else selected.id,
    }
    base.update(row)
    csv_writer.writerow(base)

def record_csv_snapshot(include_static=False):
    write_csv_row({
        "row_type": "summary",
        "object_id": "summary",
        "state": "running" if not paused else "paused",
        "drone_x": ai.drone.pos.x,
        "drone_y": ai.drone.pos.y,
        "drone_z": ai.drone.pos.z,
        "stagnation_time": ai.stagnation_time,
        "completion_time": "" if ai.completion_time is None else ai.completion_time,
        "membrane_x": MEMBRANE_X,
    })

    write_csv_row({
        "row_type": "ai_controller",
        "object_id": "ai",
        "object_name": f"AI_{ai.mode}",
        "state": "enabled" if ai.enabled else "disabled",
        "x": ai.drone.pos.x,
        "y": ai.drone.pos.y,
        "z": ai.drone.pos.z,
        "radius": ai.drone.radius,
        "stagnation_time": ai.stagnation_time,
        "completion_time": "" if ai.completion_time is None else ai.completion_time,
        **color_fields(ai.drone.color),
    })

    for v in active_vesicles():
        col = v.current_color()
        write_csv_row({
            "row_type": "vesicle",
            "object_id": v.id,
            "object_name": f"vesicle_{v.id}",
            "state": v.state,
            "x": v.pos.x, "y": v.pos.y, "z": v.pos.z,
            "vx": v.vel.x, "vy": v.vel.y, "vz": v.vel.z,
            "radius": v.radius,
            "progress": v.progress(),
            "cis_index": v.cis_index,
            "s": v.s,
            "age": v.age,
            "stall_time": v.stall_time,
            "target_x": getattr(v.target, "x", ""),
            "target_y": getattr(v.target, "y", ""),
            "target_z": getattr(v.target, "z", ""),
            "cargo_x": v.cargo.pos.x,
            "cargo_y": v.cargo.pos.y,
            "cargo_z": v.cargo.pos.z,
            "opacity": v.body.opacity,
            **color_fields(col),
        })

    for i, p in enumerate(particles):
        write_csv_row({
            "row_type": "particle",
            "object_id": i,
            "object_name": f"particle_{i}",
            "state": "active",
            "x": p.obj.pos.x, "y": p.obj.pos.y, "z": p.obj.pos.z,
            "vx": p.vel.x, "vy": p.vel.y, "vz": p.vel.z,
            "radius": p.obj.radius,
            "life": p.life,
            "max_life": p.max_life,
            "opacity": p.obj.opacity,
            **color_fields(p.obj.color),
        })

    for i, mark in enumerate(membrane_marks):
        write_csv_row({
            "row_type": "membrane_mark",
            "object_id": i,
            "object_name": f"membrane_mark_{i}",
            "state": "visible" if getattr(mark, "visible", True) else "hidden",
            "x": mark.pos.x, "y": mark.pos.y, "z": mark.pos.z,
            "radius": mark.radius,
            "opacity": mark.opacity,
            "membrane_x": MEMBRANE_X,
            **color_fields(mark.color),
        })

    if include_static:
        write_csv_row({
            "row_type": "membrane",
            "object_id": "membrane",
            "object_name": "delivery_zone",
            "state": "static",
            "x": membrane.pos.x, "y": membrane.pos.y, "z": membrane.pos.z,
            "membrane_x": MEMBRANE_X,
            "opacity": membrane.opacity,
            **color_fields(membrane.color),
        })
        for c in cisternae:
            write_csv_row({
                "row_type": "cisterna",
                "object_id": c.index,
                "object_name": f"cisterna_{c.index}",
                "state": "static",
                "cisterna_index": c.index,
                "cisterna_y": c.y,
                "x": c.xoff,
                "y": c.y,
                "z": c.zoff,
                "radius": c.width,
                **color_fields(c.base_color),
            })
        for i, rec in enumerate(receptors):
            write_csv_row({
                "row_type": "receptor",
                "object_id": i,
                "object_name": f"receptor_{i}",
                "state": "static",
                "receptor_index": i,
                "x": rec.pos.x, "y": rec.pos.y, "z": rec.pos.z,
                "radius": rec.radius,
                "opacity": rec.opacity,
                "membrane_x": MEMBRANE_X,
                **color_fields(rec.color),
            })

# ----------------------------
# Runtime helpers
# ----------------------------

def handle_collisions(dt):
    active = [v for v in vesicles if v.state not in ["delivered", "attached"]]
    for i in range(len(active)):
        a = active[i]
        for j in range(i + 1, len(active)):
            b = active[j]
            delta = b.pos - a.pos
            d = mag(delta)
            min_d = a.radius + b.radius
            if 1e-5 < d < min_d:
                push = norm(delta) * (min_d - d) * 0.52
                a.pos -= push
                b.pos += push
                col = color_lerp(a.body.color, b.body.color, 0.5)
                if random.random() < 0.40:
                    spill_particles((a.pos + b.pos) * 0.5, col, count=2, speed=0.32, life=0.55)

def nudge_selected(vec):
    v = selected_vesicle()
    if v is not None:
        v.vel += vec
        v.pos += vec * 0.05
        spill_particles(v.pos, vector(0.15, 0.25, 0.35), count=4, speed=0.3, life=0.6)
        ai.override_until = sim_time + 4.0

def keydown(evt):
    global paused, manual_selected_index
    k = evt.key
    if k == " ":
        paused = not paused
    elif k in ["a", "A"]:
        ai.enabled = not ai.enabled
    elif k in ["m", "M"]:
        ai.next_mode_manual()
    elif k in ["r", "R"]:
        reset_simulation(spawn_initial=True, new_round=True)
        ai.last_change_time = sim_time
    elif k in ["s", "S"]:
        spawn_vesicle()
        ai.override_until = sim_time + 2.5
    elif k in ["b", "B"]:
        spawn_burst(7, artistic=False)
        ai.override_until = sim_time + 2.5
    elif k in ["n", "N"]:
        manual_selected_index += 1
    elif k in ["d", "D"]:
        v = selected_vesicle()
        if v is not None:
            v.force_detach(1.4)
            ai.override_until = sim_time + 4.0
    elif k == "up" or k in ["i", "I"]:
        nudge_selected(vector(0, 0.55, 0))
    elif k == "down" or k in ["k", "K"]:
        nudge_selected(vector(0, -0.55, 0))
    elif k == "left" or k in ["j", "J"]:
        nudge_selected(vector(-0.55, 0, 0))
    elif k == "right" or k in ["l", "L"]:
        nudge_selected(vector(0.55, 0, 0))
    elif k in ["u", "U"]:
        nudge_selected(vector(0, 0, -0.55))
    elif k in ["o", "O"]:
        nudge_selected(vector(0, 0, 0.55))

scene.bind("keydown", keydown)

def update_selector():
    v = selected_vesicle()
    if v is None:
        selector_ring.visible = False
        return
    selector_ring.visible = True
    selector_ring.pos = v.pos
    selector_ring.radius = v.radius * 1.95
    selector_ring.axis = vector(0, 1, 0)

def update_status():
    active = active_vesicles()
    counts = state_counts(active)
    status_label.text = (
        f"Round {round_number} | delivered {delivered_round}/{ROUND_GOAL} | total {total_delivered} "
        f"| active {len(active)} | AI {'ON' if ai.enabled else 'OFF'}:{ai.mode} "
        f"{'| PAUSED' if paused else ''}\n"
        f"incoming {counts['incoming']}  attached {counts['attached']}  transfer {counts['transfer']}  "
        f"outgoing {counts['outgoing']}  flow {flow_speed:.2f}"
    )

# ----------------------------
# Initial round and main loop
# ----------------------------

spawn_burst(6, artistic=False)
ai.last_change_time = 0.0

open_csv_storage()
record_csv_snapshot(include_static=True)

last_real = time.time()
last_status_update = 0.0
csv_next_sample_time = 0.0
csv_next_static_sample_time = 0.0

try:
    while True:
        rate(60)
        now = time.time()
        dt = min(0.035, max(0.001, now - last_real))
        last_real = now

        if paused:
            ai.update_drone(dt, ai.read_state())
            update_selector()
            update_status()
        else:
            sim_time += dt

            ai.update(dt)

            survivors = []
            for v in vesicles:
                alive = v.update(dt)
                if alive and v.state != "delivered":
                    survivors.append(v)
            vesicles = survivors

            handle_collisions(dt)

            particle_survivors = []
            for p in particles:
                if p.update(dt):
                    particle_survivors.append(p)
            particles = particle_survivors

            for v in vesicles:
                if v.marker.opacity > 0:
                    v.marker.opacity = max(0, v.marker.opacity - dt * 0.35)

            for i, rec in enumerate(receptors):
                rec.opacity = 0.42 + 0.18 * (0.5 + 0.5 * math.sin(sim_time * 1.4 + i * 0.7))
                rec.radius = 0.145 + 0.025 * math.sin(sim_time * 1.1 + i)

            if ai.mode not in ["ritual", "chaotic"] or not ai.enabled:
                for c in cisternae:
                    c.restore_opacity()

            update_selector()
            if sim_time - last_status_update > 0.15:
                update_status()
                last_status_update = sim_time

        if sim_time >= csv_next_sample_time:
            include_static = sim_time >= csv_next_static_sample_time
            record_csv_snapshot(include_static=include_static)
            csv_next_sample_time += CSV_SAMPLE_INTERVAL
            if include_static:
                csv_next_static_sample_time += CSV_STATIC_SAMPLE_INTERVAL
            if csv_file is not None:
                csv_file.flush()

        if sim_time >= CSV_RUN_SECONDS:
            record_csv_snapshot(include_static=True)
            close_csv_storage()
            status_label.text = (
                f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to "
                f"{os.path.basename(CSV_OUTPUT_PATH)}"
            )
            break
finally:
    close_csv_storage()
