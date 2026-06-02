from vpython import *
import random
import math
import os
import csv
from datetime import datetime

# ============================================================
# 3D Cell with Organelles + Vesicle AI Controller
# CSV-storage version, compatible with CSV storage web app
# ============================================================
# Web-app environment variables supported:
#   SIMULATION_CSV_OUTPUT_DIR
#   SIMULATION_CSV_RUN_ID
#   SIMULATION_CSV_RUN_SECONDS
# Fallback:
#   SIM_STATE_CSV_PATH
# ============================================================

# -----------------------------
# CSV run configuration
# -----------------------------
CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10
CSV_FLUSH_INTERVAL = 1.0

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    os.makedirs(_csv_output_dir, exist_ok=True)
    CSV_OUTPUT_PATH = os.path.join(
        _csv_output_dir,
        f"{_csv_run_id}-cell-organelles-vesicles-state-log.csv"
    )
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cell_organelles_vesicles_state_log.csv")
    )

csv_run_id = _csv_run_id

# -----------------------------
# Scene styling
# -----------------------------
scene.title = "3D Cell with Organelles, Vesicles, Flow, AI Controller, and CSV Storage"
scene.width = 1200
scene.height = 760
scene.background = vector(0.96, 0.985, 1.0)
scene.forward = vector(-0.45, -0.25, -1)
scene.up = vector(0, 1, 0)
scene.range = 8.2
scene.autoscale = False
scene.caption = """
Controls:
SPACE pause/resume | A toggle AI | M next AI mode | 1-9 choose AI mode | R reset round
V select vesicle | Arrow keys / U / J nudge selected vesicle | O attach/detach selected | B spill selected
K mark nearest organelle | W wrap nucleus | X short human override of selected vesicle

CSV recording runs for the configured run seconds and writes repeated state snapshots.
"""

# -----------------------------
# Constants and globals
# -----------------------------
CELL_RADIUS = 6.0
VESICLE_COUNT = 16
RIBOSOME_COUNT = 90
FLOW_PARTICLE_COUNT = 55
DT = 1.0 / 60.0

sim_time = 0.0
paused = False
selected_index = 0
human_override_until = 0.0
frame_count = 0

random.seed()

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(1, 0, 0)
    return v / m

def random_unit():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) > 0.001:
            return norm(v)

def random_in_cell(margin=0.4):
    r = (CELL_RADIUS - margin) * (random.random() ** (1.0 / 3.0))
    return random_unit() * r

def outside_any_large_organelle(p, extra=0.0):
    for o in organelles:
        if mag(p - o["obj"].pos) < o["radius"] + extra:
            return False
    return True

def random_free_position(margin=0.55):
    for _ in range(200):
        p = random_in_cell(margin)
        if outside_any_large_organelle(p, margin):
            return p
    return random_in_cell(margin)

def flow_field(p, t):
    radial = mag(p) / CELL_RADIUS
    swirl = vector(-p.z, 0.0, p.x) * (0.055 + 0.025 * math.sin(t * 0.35))
    vertical = vector(0, 0.10 * math.sin(1.35 * t + p.x * 0.65 + p.z * 0.25), 0)
    eddy = vector(
        0.045 * math.sin(t * 0.9 + p.y * 1.4),
        0.035 * math.cos(t * 1.1 + p.z * 1.2),
        0.045 * math.sin(t * 0.75 - p.x * 1.1)
    )
    inward = -safe_norm(p) * max(0, radial - 0.75) * 0.07
    return swirl + vertical + eddy + inward

def vector_tuple(v):
    return (v.x, v.y, v.z)

def attached_name(target):
    if target is None:
        return ""
    return target.get("name", target.get("kind", "target"))

# -----------------------------
# Lighting and cell shell
# -----------------------------
distant_light(direction=vector(-1, -1, -0.5), color=vector(0.75, 0.78, 0.82))
local_light(pos=vector(0, 5, 6), color=vector(0.7, 0.85, 1.0))

cell_shell = sphere(pos=vector(0, 0, 0), radius=CELL_RADIUS, color=vector(0.66, 0.93, 1.0), opacity=0.18, shininess=0.6)
cell_membrane = sphere(pos=vector(0, 0, 0), radius=CELL_RADIUS * 1.006, color=vector(0.35, 0.75, 0.95), opacity=0.055, shininess=0.8)

# -----------------------------
# Organelles
# -----------------------------
organelles = []

nucleus_obj = sphere(pos=vector(-1.15, 0.25, 0.15), radius=1.55, color=vector(0.58, 0.48, 0.92), opacity=0.58, shininess=0.9)
nucleolus = sphere(pos=nucleus_obj.pos + vector(-0.25, 0.15, 0.18), radius=0.48, color=vector(0.42, 0.28, 0.72), opacity=0.82)
nucleus_wrap_hint = sphere(pos=nucleus_obj.pos, radius=1.75, color=vector(0.82, 0.76, 1.0), opacity=0.06)
organelles.append({
    "name": "Nucleus", "kind": "nucleus", "obj": nucleus_obj, "radius": 1.68, "marks": 0,
    "label": label(pos=nucleus_obj.pos + vector(0, 1.95, 0), text="Nucleus", color=vector(0.16, 0.10, 0.32), box=False, opacity=0, height=13)
})

mito_positions = [vector(2.6, 1.4, -0.95), vector(2.25, -1.55, 1.15), vector(-3.15, -1.05, -1.3), vector(0.45, 2.8, 1.85), vector(-2.55, 1.95, 1.2)]
mito_axes = [vector(1, 0.25, 0.35), vector(0.7, -0.25, 1), vector(1, -0.1, -0.5), vector(-0.5, 0.2, 1), vector(1, 0.1, -0.8)]

for i, p in enumerate(mito_positions):
    m = sphere(pos=p, size=vector(1.55, 0.58, 0.58), color=vector(1.0, 0.58, 0.25), opacity=0.88, shininess=0.7)
    try:
        m.axis = safe_norm(mito_axes[i])
    except Exception:
        pass
    cristae_points = []
    for k in range(28):
        a = -0.63 + 1.26 * k / 27.0
        cristae_points.append(p + vector(a, 0.14 * math.sin(k * 1.45), 0.09 * math.cos(k * 1.45)))
    c = curve(pos=cristae_points, radius=0.025, color=vector(1.0, 0.86, 0.38), opacity=0.65)
    organelles.append({
        "name": "Mitochondrion " + str(i + 1), "kind": "mitochondrion", "obj": m, "radius": 0.88,
        "marks": 0, "spin": random.choice([-1, 1]) * random.uniform(0.25, 0.65), "cristae": c,
        "label": label(pos=p + vector(0, 0.82, 0), text="Mitochondrion", color=vector(0.38, 0.18, 0.02), box=False, opacity=0, height=10)
    })

# -----------------------------
# Ribosomes, flow particles, dynamic lists
# -----------------------------
ribosomes = []
ribosome_label = label(pos=vector(2.4, -3.65, 0), text="Ribosomes", color=vector(0.32, 0.10, 0.37), box=False, opacity=0, height=12)
for i in range(RIBOSOME_COUNT):
    p = random_free_position(0.3)
    r = sphere(pos=p, radius=random.uniform(0.045, 0.075), color=vector(0.78, 0.36, 0.88), opacity=random.uniform(0.48, 0.86), shininess=0.25)
    ribosomes.append({"obj": r, "anchor": p, "phase": random.uniform(0, 2 * math.pi), "amp": random.uniform(0.012, 0.04)})

flow_particles = []
for i in range(FLOW_PARTICLE_COUNT):
    p = random_free_position(0.25)
    fp = sphere(pos=p, radius=random.uniform(0.035, 0.06), color=vector(0.24, 0.68, 1.0), opacity=random.uniform(0.18, 0.36), shininess=0.2)
    flow_particles.append({"obj": fp, "age": random.random() * 4.0})

flow_arrows = []
for i in range(14):
    p = random_free_position(0.9)
    arr = arrow(pos=p, axis=flow_field(p, 0) * 2.0, shaftwidth=0.025, headwidth=0.09, headlength=0.13, color=vector(0.42, 0.78, 1.0), opacity=0.26)
    flow_arrows.append({"obj": arr, "anchor": p, "phase": random.uniform(0, 2 * math.pi)})

markers = []
spill_particles = []
wraps = []

# -----------------------------
# Vesicles
# -----------------------------
class Vesicle:
    def __init__(self, idx):
        self.idx = idx
        self.r = random.uniform(0.19, 0.31)
        self.base_color = random.choice([
            vector(0.98, 0.78, 0.28), vector(0.98, 0.54, 0.72), vector(0.36, 0.86, 0.62), vector(0.56, 0.78, 1.0)
        ])
        self.obj = sphere(pos=random_free_position(self.r + 0.25), radius=self.r, color=self.base_color, opacity=0.72, shininess=0.85)
        self.vel = random_unit() * random.uniform(0.25, 0.65)
        self.trail = curve(color=self.obj.color, radius=0.018, opacity=0.22)
        self.label = label(pos=self.obj.pos + vector(0, self.r + 0.24, 0), text="V" + str(idx + 1), height=8, color=vector(0.16, 0.20, 0.26), box=False, opacity=0)
        self.ai_force = vector(0, 0, 0)
        self.attached_to = None
        self.attach_timer = 0.0
        self.orbit_angle = random.random() * 2 * math.pi
        self.orbit_speed = random.choice([-1, 1]) * random.uniform(0.6, 1.4)
        self.orbit_radius = 1.0
        self.orbit_axis = random_unit()
        self.orbit_seed = random_unit()
        self.cargo = False
        self.cargo_from = None
        self.cargo_to = None
        self.human_touched = False

    def reset(self):
        self.obj.pos = random_free_position(self.r + 0.25)
        self.vel = random_unit() * random.uniform(0.25, 0.65)
        self.obj.color = self.base_color
        self.obj.opacity = 0.72
        self.attached_to = None
        self.attach_timer = 0
        self.cargo = False
        self.cargo_from = None
        self.cargo_to = None
        self.ai_force = vector(0, 0, 0)
        self.trail.visible = False
        self.trail = curve(color=self.obj.color, radius=0.018, opacity=0.22)
        self.label.text = "V" + str(self.idx + 1)
        self.human_touched = False

    def attach(self, target, duration=None):
        self.attached_to = target
        self.attach_timer = duration if duration is not None else random.uniform(2.0, 5.0)
        self.orbit_axis = random_unit()
        self.orbit_seed = random_unit()
        self.orbit_radius = target["radius"] + self.r + random.uniform(0.16, 0.42)
        self.orbit_speed = random.choice([-1, 1]) * random.uniform(0.55, 1.55)
        self.orbit_angle = random.random() * 2 * math.pi
        self.label.text = "V" + str(self.idx + 1) + " attached"

    def detach(self):
        if self.attached_to is not None:
            tangent = safe_norm(cross(self.orbit_axis, safe_norm(self.obj.pos - self.attached_to["obj"].pos)))
            self.vel = tangent * random.uniform(0.55, 1.05) + random_unit() * 0.18
        self.attached_to = None
        self.attach_timer = 0.0
        self.label.text = "V" + str(self.idx + 1)

    def collide_with_cell_wall(self):
        d = mag(self.obj.pos)
        if d + self.r > CELL_RADIUS:
            n = safe_norm(self.obj.pos)
            self.obj.pos = n * (CELL_RADIUS - self.r - 0.015)
            if dot(self.vel, n) > 0:
                self.vel = self.vel - 1.72 * dot(self.vel, n) * n
                self.vel *= 0.86

    def collide_with_organelles(self):
        for o in organelles:
            delta = self.obj.pos - o["obj"].pos
            d = mag(delta)
            min_dist = self.r + o["radius"]
            if d < min_dist:
                n = safe_norm(delta)
                self.obj.pos = o["obj"].pos + n * (min_dist + 0.012)
                if dot(self.vel, n) < 0:
                    self.vel = self.vel - 1.58 * dot(self.vel, n) * n
                    self.vel += n * 0.04
                if random.random() < 0.018:
                    create_tiny_collision_flash(self.obj.pos, n)

    def update(self, dt, t):
        old_pos = vector(self.obj.pos.x, self.obj.pos.y, self.obj.pos.z)
        if self.attached_to is not None:
            center = self.attached_to["obj"].pos
            self.attach_timer -= dt
            self.orbit_angle += self.orbit_speed * dt
            radial = rotate(self.orbit_seed, angle=self.orbit_angle, axis=self.orbit_axis)
            radial = safe_norm(radial)
            bob = 0.07 * math.sin(t * 2.0 + self.idx)
            desired = center + radial * (self.orbit_radius + bob)
            self.obj.pos = self.obj.pos * 0.22 + desired * 0.78
            self.vel = (self.obj.pos - old_pos) / max(dt, 1e-5)
            if self.attach_timer <= 0:
                self.detach()
        else:
            noise = random_unit() * random.uniform(0.0, 0.025)
            self.vel += (flow_field(self.obj.pos, t) + self.ai_force + noise) * dt
            self.vel *= 0.992
            spd = mag(self.vel)
            if spd > 1.55:
                self.vel = self.vel / spd * 1.55
            self.obj.pos += self.vel * dt
            self.collide_with_cell_wall()
            self.collide_with_organelles()
        self.trail.append(pos=self.obj.pos, retain=95)
        self.label.pos = self.obj.pos + vector(0, self.r + 0.28, 0)
        if self.cargo:
            self.obj.color = vector(1.0, 0.86, 0.16)
            self.obj.opacity = 0.86

vesicles = [Vesicle(i) for i in range(VESICLE_COUNT)]

selector = ring(pos=vesicles[selected_index].obj.pos, axis=vector(0, 1, 0), radius=0.48, thickness=0.018, color=vector(0.18, 0.38, 1.0), opacity=0.6)
hud = label(pos=vector(0, CELL_RADIUS + 0.55, 0), text="", height=12, color=vector(0.08, 0.14, 0.20), box=False, opacity=0)

# -----------------------------
# Interaction helpers
# -----------------------------
def create_tiny_collision_flash(p, n):
    flash = sphere(pos=p + n * 0.03, radius=0.045, color=vector(1.0, 1.0, 0.58), opacity=0.55)
    spill_particles.append({"obj": flash, "vel": n * random.uniform(0.15, 0.4) + random_unit() * 0.08, "age": 0.0, "life": random.uniform(0.3, 0.65), "kind": "flash"})

def create_mark(target, source_pos=None, mark_color=None):
    if source_pos is None:
        n = random_unit()
    else:
        n = safe_norm(source_pos - target["obj"].pos)
    p = target["obj"].pos + n * (target["radius"] + 0.045)
    col = mark_color if mark_color is not None else vector(0.18, 0.95, 0.92)
    mk = sphere(pos=p, radius=0.085 if target["kind"] == "nucleus" else 0.065, color=col, opacity=0.88, shininess=0.4)
    markers.append({"obj": mk, "target": target, "normal": n, "age": 0.0})
    target["marks"] += 1
    return mk

def spill_from_vesicle(v, count=7, color_override=None):
    col = color_override if color_override is not None else vector(1.0, 0.72, 0.26)
    for _ in range(count):
        d = random_unit()
        p = v.obj.pos + d * (v.r + 0.04)
        particle = sphere(pos=p, radius=random.uniform(0.035, 0.065), color=col + random_unit() * 0.03, opacity=random.uniform(0.42, 0.78), shininess=0.2)
        spill_particles.append({"obj": particle, "vel": v.vel * 0.35 + d * random.uniform(0.25, 0.85), "age": 0.0, "life": random.uniform(2.0, 5.0), "kind": "cargo"})

def wrap_target(target, color_override=None, life=6.0):
    col = color_override if color_override is not None else vector(0.74, 0.95, 1.0)
    shell = sphere(pos=target["obj"].pos, radius=target["radius"] + random.uniform(0.16, 0.32), color=col, opacity=0.15, shininess=0.9)
    wraps.append({"obj": shell, "target": target, "age": 0.0, "life": life})
    return shell

def nearest_organelle_to(p):
    return min(organelles, key=lambda o: mag(p - o["obj"].pos))

def handle_vesicle_vesicle_collisions():
    for i in range(len(vesicles)):
        a = vesicles[i]
        if a.attached_to is not None:
            continue
        for j in range(i + 1, len(vesicles)):
            b = vesicles[j]
            if b.attached_to is not None:
                continue
            delta = a.obj.pos - b.obj.pos
            d = mag(delta)
            min_d = a.r + b.r
            if d < min_d and d > 1e-6:
                n = delta / d
                overlap = min_d - d
                a.obj.pos += n * overlap * 0.52
                b.obj.pos -= n * overlap * 0.52
                va = dot(a.vel, n)
                vb = dot(b.vel, n)
                if va - vb < 0:
                    a.vel += (vb - va) * n * 0.82
                    b.vel += (va - vb) * n * 0.82
                if random.random() < 0.08:
                    create_tiny_collision_flash((a.obj.pos + b.obj.pos) * 0.5, n)

def reset_round():
    global sim_time
    for v in vesicles:
        v.reset()
    for mk in markers:
        mk["obj"].visible = False
    markers.clear()
    for sp in spill_particles:
        sp["obj"].visible = False
    spill_particles.clear()
    for wr in wraps:
        wr["obj"].visible = False
    wraps.clear()
    for o in organelles:
        o["marks"] = 0
    for r in ribosomes:
        p = random_free_position(0.25)
        r["anchor"] = p
        r["obj"].pos = p
        r["phase"] = random.uniform(0, 2 * math.pi)
    for fp in flow_particles:
        fp["obj"].pos = random_free_position(0.25)
        fp["age"] = random.random() * 4
    for fa in flow_arrows:
        fa["anchor"] = random_free_position(0.9)
        fa["obj"].pos = fa["anchor"]
    if "ai" in globals():
        ai.reset_state()
    sim_time = 0.0

# -----------------------------
# AI controller
# -----------------------------
class CellAIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "PLAYFUL_FLOW", "ORBIT_NUCLEUS", "ORGANIZE_RING", "MARK_ORGANELLES", "SPILL_BURSTS",
            "WRAP_AND_DIP", "CAREFUL_TRANSFER", "CHAOTIC_MIX", "ARTISTIC_TRAILS"
        ]
        self.mode = "PLAYFUL_FLOW"
        self.mode_timer = 0.0
        self.mode_duration = 10.0
        self.round = 1
        self.history = []
        self.last_centroid = vector(0, 0, 0)
        self.last_mark_count = 0
        self.sample_timer = 0.0
        self.stable_time = 0.0
        self.reset_countdown = 0.0
        self.last_action_time = 0.0
        self.behavior_seed = random.random() * 100
        self.target_organelle = organelles[0]
        self.transfer_stage = "choose"
        self.transfer_carrier = None
        self.transfer_source = None
        self.transfer_target = organelles[0]

    def reset_state(self):
        self.mode_timer = 0.0
        self.sample_timer = 0.0
        self.stable_time = 0.0
        self.reset_countdown = 0.0
        self.last_mark_count = 0
        self.last_centroid = self.get_centroid()
        self.transfer_stage = "choose"
        self.transfer_carrier = None
        self.behavior_seed = random.random() * 100

    def get_centroid(self):
        if not vesicles:
            return vector(0, 0, 0)
        c = vector(0, 0, 0)
        for v in vesicles:
            c += v.obj.pos
        return c / len(vesicles)

    def read_state(self):
        speeds = [mag(v.vel) for v in vesicles]
        centroid = self.get_centroid()
        attached = sum(1 for v in vesicles if v.attached_to is not None)
        cargo = sum(1 for v in vesicles if v.cargo)
        mark_count = sum(o["marks"] for o in organelles)
        marked_organelle_count = sum(1 for o in organelles if o["marks"] > 0)
        avg_speed = sum(speeds) / max(1, len(speeds))
        return {
            "time": sim_time, "round": self.round, "mode": self.mode, "vesicle_count": len(vesicles),
            "avg_speed": avg_speed, "max_speed": max(speeds) if speeds else 0,
            "centroid": centroid, "attached_count": attached, "cargo_count": cargo,
            "mark_count": mark_count, "marked_organelle_count": marked_organelle_count,
            "spill_count": len(spill_particles), "wrap_count": len(wraps),
            "completion": marked_organelle_count >= len(organelles) and mark_count >= len(organelles),
            "empty": len(vesicles) == 0
        }

    def set_mode(self, mode):
        self.mode = mode
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(7.5, 15.0)
        self.behavior_seed = random.random() * 100
        self.history.append(mode)
        if len(self.history) > 5:
            self.history.pop(0)
        if mode == "MARK_ORGANELLES":
            unmarked = [o for o in organelles if o["marks"] == 0]
            self.target_organelle = random.choice(unmarked if unmarked else organelles)
        elif mode == "CAREFUL_TRANSFER":
            self.transfer_stage = "choose"
            self.transfer_carrier = None
        elif mode == "CHAOTIC_MIX":
            for v in vesicles:
                if v.attached_to is not None and random.random() < 0.75:
                    v.detach()

    def pick_next_mode(self, state=None):
        if state is None:
            state = self.read_state()
        if state["completion"] or state["empty"] or self.stable_time > 7.0 or sim_time > max(125.0, CSV_RUN_SECONDS * 0.85):
            self.set_mode("RESET_LOOP")
            self.reset_countdown = 2.6
            wrap_target(organelles[0], vector(0.95, 0.95, 1.0), life=2.4)
            return
        choices = list(self.modes)
        if state["marked_organelle_count"] < len(organelles) and random.random() < 0.35:
            choices += ["MARK_ORGANELLES", "CAREFUL_TRANSFER"]
        if state["attached_count"] < 4:
            choices += ["ORBIT_NUCLEUS", "WRAP_AND_DIP"]
        if len(spill_particles) < 20:
            choices += ["SPILL_BURSTS"]
        if self.history:
            choices = [c for c in choices if c != self.history[-1]] or self.modes
        if len(self.history) >= 2:
            choices = [c for c in choices if c not in self.history[-2:]] or self.modes
        self.set_mode(random.choice(choices))

    def detect_stagnation_or_completion(self, dt, state):
        self.sample_timer += dt
        if self.sample_timer < 1.0:
            return
        centroid_shift = mag(state["centroid"] - self.last_centroid)
        mark_changed = state["mark_count"] != self.last_mark_count
        low_motion = state["avg_speed"] < 0.105 and state["attached_count"] < 3
        no_scene_change = centroid_shift < 0.075 and not mark_changed and len(spill_particles) < 5
        if low_motion or no_scene_change:
            self.stable_time += self.sample_timer
        else:
            self.stable_time = max(0.0, self.stable_time - self.sample_timer * 0.7)
        self.last_centroid = state["centroid"]
        self.last_mark_count = state["mark_count"]
        self.sample_timer = 0.0

    def force_toward(self, v, target_pos, strength=0.45, damping=0.16):
        return (target_pos - v.obj.pos) * strength - v.vel * damping

    def choose_actions(self, dt, t, state):
        for v in vesicles:
            v.ai_force = vector(0, 0, 0)

        if self.mode == "RESET_LOOP":
            for v in vesicles:
                v.ai_force = -v.obj.pos * 0.35 - v.vel * 0.2
            self.reset_countdown -= dt
            if self.reset_countdown <= 0:
                self.round += 1
                reset_round()
                self.pick_next_mode()
            return

        if self.mode == "PLAYFUL_FLOW":
            for i, v in enumerate(vesicles):
                swirl = safe_norm(vector(-v.obj.pos.z, 0.25 * math.sin(t + i), v.obj.pos.x))
                pulse = 0.20 + 0.10 * math.sin(t * 1.2 + i)
                v.ai_force = swirl * pulse + flow_field(v.obj.pos, t) * 0.8
                if random.random() < 0.0009:
                    v.obj.color = color.hsv_to_rgb(vector((t * 0.05 + i * 0.07) % 1.0, 0.46, 1.0))

        elif self.mode == "ORBIT_NUCLEUS":
            center = nucleus_obj.pos
            for i, v in enumerate(vesicles):
                delta = v.obj.pos - center
                tangent = safe_norm(cross(vector(0, 1, 0), delta))
                desired_r = 2.45 + 0.35 * math.sin(i * 1.7)
                radial_force = (desired_r - mag(delta)) * safe_norm(delta) * 0.45
                v.ai_force = tangent * 0.42 + radial_force - v.vel * 0.10
                if v.attached_to is None and mag(delta) < 2.3 and random.random() < 0.004:
                    v.attach(organelles[0], random.uniform(2.2, 5.2))

        elif self.mode == "ORGANIZE_RING":
            center = nucleus_obj.pos
            n = len(vesicles)
            for i, v in enumerate(vesicles):
                angle = 2 * math.pi * i / n + 0.28 * math.sin(t * 0.35)
                target = center + vector(3.45 * math.cos(angle), 0.65 * math.sin(t * 0.7 + i), 3.45 * math.sin(angle))
                v.ai_force = self.force_toward(v, target, strength=0.38, damping=0.22)
                if v.attached_to is not None and random.random() < 0.004:
                    v.detach()

        elif self.mode == "MARK_ORGANELLES":
            if self.target_organelle["marks"] > 0 and random.random() < 0.03:
                unmarked = [o for o in organelles if o["marks"] == 0]
                self.target_organelle = random.choice(unmarked if unmarked else organelles)
            target = self.target_organelle
            for i, v in enumerate(vesicles):
                n = safe_norm(v.obj.pos - target["obj"].pos)
                desired = target["obj"].pos + n * (target["radius"] + v.r + 0.05)
                if i % 3 == 0:
                    v.ai_force = self.force_toward(v, desired, 0.58, 0.20)
                else:
                    tangent = safe_norm(cross(vector(0, 1, 0), v.obj.pos - target["obj"].pos))
                    v.ai_force = tangent * 0.20 + self.force_toward(v, desired + tangent * 0.3, 0.22, 0.12)
                if mag(v.obj.pos - target["obj"].pos) < target["radius"] + v.r + 0.13:
                    if target["marks"] < 3 or random.random() < 0.15:
                        create_mark(target, v.obj.pos, vector(0.15, 0.95, 0.86))
                        v.vel += safe_norm(v.obj.pos - target["obj"].pos) * 0.55
                        if random.random() < 0.35:
                            spill_from_vesicle(v, count=3, color_override=vector(0.30, 1.0, 0.86))

        elif self.mode == "SPILL_BURSTS":
            for i, v in enumerate(vesicles):
                v.ai_force = flow_field(v.obj.pos, t) * 1.2 + vector(0, -0.25 * math.sin(t * 1.4 + i), 0)
            if t - self.last_action_time > random.uniform(0.7, 1.4):
                self.last_action_time = t
                for v in random.sample(vesicles, k=min(3, len(vesicles))):
                    spill_from_vesicle(v, count=random.randint(5, 11), color_override=random.choice([vector(1.0, 0.72, 0.28), vector(0.54, 0.95, 1.0), vector(0.94, 0.62, 1.0)]))

        elif self.mode == "WRAP_AND_DIP":
            for i, v in enumerate(vesicles):
                lower = vector(v.obj.pos.x, -2.3 + 0.25 * math.sin(i + t), v.obj.pos.z)
                rise = nucleus_obj.pos + safe_norm(v.obj.pos - nucleus_obj.pos) * 2.25
                target = lower if math.sin(t * 0.45 + i * 0.4) > 0 else rise
                v.ai_force = self.force_toward(v, target, 0.34, 0.12)
            if t - self.last_action_time > 3.4:
                self.last_action_time = t
                wrap_target(random.choice(organelles), vector(0.72, 0.92, 1.0), life=random.uniform(4.5, 7.5))

        elif self.mode == "CAREFUL_TRANSFER":
            if self.transfer_stage == "choose" or self.transfer_carrier is None:
                self.transfer_source = random.choice([o for o in organelles if o["kind"] == "mitochondrion"])
                self.transfer_target = organelles[0]
                self.transfer_carrier = random.choice(vesicles)
                self.transfer_carrier.cargo = True
                self.transfer_carrier.cargo_from = self.transfer_source
                self.transfer_carrier.cargo_to = self.transfer_target
                self.transfer_stage = "to_source"
            carrier = self.transfer_carrier
            for v in vesicles:
                if v is carrier:
                    if self.transfer_stage == "to_source":
                        target_pos = self.transfer_source["obj"].pos
                        v.ai_force = self.force_toward(v, target_pos, 0.72, 0.25)
                        if mag(v.obj.pos - target_pos) < self.transfer_source["radius"] + v.r + 0.15:
                            v.attach(self.transfer_source, 1.1)
                            self.transfer_stage = "to_target"
                    elif self.transfer_stage == "to_target":
                        target_pos = self.transfer_target["obj"].pos
                        if v.attached_to is not None and v.attach_timer < 0.15:
                            v.detach()
                        v.ai_force = self.force_toward(v, target_pos, 0.70, 0.23)
                        if mag(v.obj.pos - target_pos) < self.transfer_target["radius"] + v.r + 0.18:
                            create_mark(self.transfer_target, v.obj.pos, vector(1.0, 0.86, 0.18))
                            spill_from_vesicle(v, count=8, color_override=vector(1.0, 0.86, 0.18))
                            v.cargo = False
                            v.obj.color = v.base_color
                            self.transfer_stage = "choose"
                            self.transfer_carrier = None
                else:
                    tangent = safe_norm(cross(vector(0, 1, 0), v.obj.pos - nucleus_obj.pos))
                    v.ai_force = tangent * 0.12 + flow_field(v.obj.pos, t) * 0.55

        elif self.mode == "CHAOTIC_MIX":
            for i, v in enumerate(vesicles):
                random_kick = vector(math.sin(t * 4.1 + i * 2.3), math.cos(t * 3.7 + i * 1.9), math.sin(t * 4.5 - i * 1.3))
                v.ai_force = random_kick * 0.42 + flow_field(v.obj.pos, t) * 1.4
                if v.attached_to is not None and random.random() < 0.018:
                    v.detach()
                if random.random() < 0.0018:
                    v.vel += random_unit() * random.uniform(0.4, 0.9)
            if t - self.last_action_time > 2.2:
                self.last_action_time = t
                spill_from_vesicle(random.choice(vesicles), count=10, color_override=vector(1.0, 0.45, 0.35))

        elif self.mode == "ARTISTIC_TRAILS":
            for i, v in enumerate(vesicles):
                a = t * 0.65 + i * 2 * math.pi / len(vesicles)
                target = vector(3.3 * math.sin(a * 1.1), 2.1 * math.sin(a * 1.7 + i), 3.3 * math.cos(a * 1.1))
                v.ai_force = self.force_toward(v, target, 0.42, 0.18)
                hue = (0.56 + 0.34 * math.sin(t * 0.15 + i * 0.4)) % 1
                v.trail.color = color.hsv_to_rgb(vector(hue, 0.45, 1.0))
                v.obj.color = v.obj.color * 0.96 + color.hsv_to_rgb(vector(hue, 0.35, 1.0)) * 0.04

    def update(self, dt, t):
        state = self.read_state()
        self.detect_stagnation_or_completion(dt, state)
        self.mode_timer += dt
        if self.mode != "RESET_LOOP" and (self.mode_timer > self.mode_duration or state["completion"] or state["empty"] or self.stable_time > 7.0):
            self.pick_next_mode(state)
        self.choose_actions(dt, t, state)

ai = CellAIController()

# -----------------------------
# Updates
# -----------------------------
def update_particles(dt, t):
    for fp in flow_particles:
        p = fp["obj"].pos
        fp["obj"].pos += flow_field(p, t) * dt * 1.8
        fp["age"] += dt
        if mag(fp["obj"].pos) > CELL_RADIUS - 0.2 or fp["age"] > 12 or not outside_any_large_organelle(fp["obj"].pos, 0.05):
            fp["obj"].pos = random_free_position(0.25)
            fp["age"] = 0.0
    for fa in flow_arrows:
        drift = vector(0.16 * math.sin(t * 0.18 + fa["phase"]), 0.10 * math.sin(t * 0.22 + fa["phase"] * 0.7), 0.16 * math.cos(t * 0.18 + fa["phase"]))
        fa["obj"].pos = fa["anchor"] + drift
        fa["obj"].axis = flow_field(fa["obj"].pos, t) * 2.3

def update_spills_and_wraps(dt, t):
    dead = []
    for sp in spill_particles:
        sp["age"] += dt
        sp["obj"].pos += sp["vel"] * dt
        sp["vel"] += flow_field(sp["obj"].pos, t) * dt * 0.85
        sp["vel"] *= 0.986
        if mag(sp["obj"].pos) > CELL_RADIUS - 0.1:
            n = safe_norm(sp["obj"].pos)
            sp["obj"].pos = n * (CELL_RADIUS - 0.13)
            sp["vel"] -= 1.4 * dot(sp["vel"], n) * n
        fade = max(0.0, 1.0 - sp["age"] / sp["life"])
        sp["obj"].opacity = 0.65 * fade if sp["kind"] != "flash" else 0.55 * fade
        if sp["age"] > sp["life"]:
            sp["obj"].visible = False
            dead.append(sp)
    for sp in dead:
        if sp in spill_particles:
            spill_particles.remove(sp)

    dead_wraps = []
    for wr in wraps:
        wr["age"] += dt
        wr["obj"].pos = wr["target"]["obj"].pos
        wr["obj"].radius += 0.01 * math.sin(t * 2.0 + wr["age"])
        wr["obj"].opacity = 0.15 * max(0.0, 1.0 - wr["age"] / wr["life"])
        if wr["age"] > wr["life"]:
            wr["obj"].visible = False
            dead_wraps.append(wr)
    for wr in dead_wraps:
        if wr in wraps:
            wraps.remove(wr)

    for mk in markers:
        mk["age"] += dt
        pulse = 0.80 + 0.20 * math.sin(t * 2.2 + mk["age"])
        mk["obj"].opacity = 0.70 + 0.18 * pulse
        mk["obj"].pos = mk["target"]["obj"].pos + mk["normal"] * (mk["target"]["radius"] + 0.045)

def update_ribosomes_and_organelles(dt, t):
    for r in ribosomes:
        r["phase"] += dt * 0.8
        bob = vector(r["amp"] * math.sin(r["phase"] * 1.7), r["amp"] * math.cos(r["phase"] * 1.2), r["amp"] * math.sin(r["phase"] * 1.1 + 1.3))
        r["obj"].pos = r["anchor"] + bob
    nucleus_wrap_hint.radius = 1.75 + 0.04 * math.sin(t * 0.65)
    nucleus_wrap_hint.opacity = 0.055 + 0.018 * math.sin(t * 0.7 + 1.0)
    nucleolus.pos = nucleus_obj.pos + vector(-0.25 + 0.03 * math.sin(t * 0.5), 0.15 + 0.025 * math.cos(t * 0.6), 0.18)
    for o in organelles:
        if o["kind"] == "mitochondrion":
            try:
                o["obj"].rotate(angle=o["spin"] * dt * 0.35, axis=vector(0.25, 1, 0.12), origin=o["obj"].pos)
            except Exception:
                pass

def update_labels():
    for o in organelles:
        offset = vector(0, 2.0 if o["kind"] == "nucleus" else 0.82, 0)
        if o["kind"] == "mitochondrion":
            offset = vector(0, 0.92 + 0.06 * math.sin(sim_time + o["obj"].pos.x), 0)
        o["label"].pos = o["obj"].pos + offset
        o["label"].text = o["name"] + ("  marks:" + str(o["marks"]) if o["marks"] > 0 else "")
    ribosome_label.pos = vector(2.3, -3.7 + 0.1 * math.sin(sim_time), 0.2)
    selected = vesicles[selected_index]
    selector.pos = selected.obj.pos
    selector.axis = scene.camera.pos - selector.pos
    selector.radius = selected.r + 0.18 + 0.04 * math.sin(sim_time * 3.0)
    state = ai.read_state()
    hud.text = (
        "AI: " + ("ON" if ai.enabled else "OFF") +
        " | Mode: " + ai.mode +
        " | Round: " + str(ai.round) +
        " | Time: " + str(round(sim_time, 1)) + "/" + str(round(CSV_RUN_SECONDS, 1)) +
        " | Avg vesicle speed: " + str(round(state["avg_speed"], 2)) +
        " | Attached: " + str(state["attached_count"]) +
        " | Marks: " + str(state["mark_count"]) +
        " | Stable: " + str(round(ai.stable_time, 1)) +
        " | Selected: V" + str(selected_index + 1) +
        (" | PAUSED" if paused else "")
    )
    hud.pos = vector(0, CELL_RADIUS + 0.62, 0)

# -----------------------------
# Keyboard controls
# -----------------------------
def detach_or_attach_selected():
    v = vesicles[selected_index]
    if v.attached_to is not None:
        v.detach()
    else:
        target = nearest_organelle_to(v.obj.pos)
        v.attach(target, random.uniform(2.0, 5.0))

def keydown(evt):
    global paused, selected_index, human_override_until
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ["a", "A"]:
        ai.enabled = not ai.enabled
    elif key in ["r", "R"]:
        reset_round()
    elif key in ["m", "M"]:
        ai.pick_next_mode()
    elif key in ["v", "V"]:
        selected_index = (selected_index + 1) % len(vesicles)
    elif key in ["o", "O"]:
        detach_or_attach_selected()
    elif key in ["b", "B"]:
        spill_from_vesicle(vesicles[selected_index], count=12, color_override=vector(1.0, 0.75, 0.25))
    elif key in ["k", "K"]:
        v = vesicles[selected_index]
        create_mark(nearest_organelle_to(v.obj.pos), v.obj.pos, vector(0.12, 1.0, 0.82))
    elif key in ["w", "W"]:
        wrap_target(organelles[0], vector(0.75, 0.88, 1.0), life=6.5)
    elif key in ["x", "X"]:
        human_override_until = sim_time + 4.0
    elif key in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        idx = int(key) - 1
        if 0 <= idx < len(ai.modes):
            ai.set_mode(ai.modes[idx])

    v = vesicles[selected_index]
    impulse = vector(0, 0, 0)
    if key == "left":
        impulse = vector(-0.55, 0, 0)
    elif key == "right":
        impulse = vector(0.55, 0, 0)
    elif key == "up":
        impulse = vector(0, 0.55, 0)
    elif key == "down":
        impulse = vector(0, -0.55, 0)
    elif key in ["u", "U"]:
        impulse = vector(0, 0, -0.55)
    elif key in ["j", "J"]:
        impulse = vector(0, 0, 0.55)
    if mag(impulse) > 0:
        if v.attached_to is not None:
            v.detach()
        v.vel += impulse
        v.human_touched = True
        human_override_until = sim_time + 1.5

scene.bind("keydown", keydown)

# -----------------------------
# Initial visible interactions
# -----------------------------
for v in random.sample(vesicles, 4):
    v.attach(random.choice(organelles), random.uniform(2.0, 5.5))
for o in random.sample(organelles, 2):
    create_mark(o, o["obj"].pos + random_unit() * (o["radius"] + 0.2), vector(0.22, 0.94, 0.86))
wrap_target(organelles[0], vector(0.80, 0.87, 1.0), life=5.0)

# -----------------------------
# CSV recording helpers
# -----------------------------
CSV_FIELDNAMES = [
    "run_id", "time_seconds", "frame", "row_type", "entity_id", "entity_name", "entity_kind",
    "ai_enabled", "ai_mode", "ai_round", "ai_mode_timer", "ai_mode_duration", "ai_stable_time",
    "selected_index", "paused", "human_override_active", "vesicle_count", "attached_count", "cargo_count",
    "mark_count", "marked_organelle_count", "spill_count", "wrap_count", "avg_speed", "max_speed",
    "completion", "empty", "x", "y", "z", "vx", "vy", "vz", "radius", "age", "life",
    "attached_to", "attach_timer", "cargo", "cargo_from", "cargo_to", "marks", "visible", "extra"
]

_csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
_csv_writer = csv.DictWriter(_csv_file, fieldnames=CSV_FIELDNAMES)
_csv_writer.writeheader()
_csv_last_sample_time = -CSV_SAMPLE_INTERVAL
_csv_last_flush_time = 0.0
_csv_closed = False

def base_csv_row(row_type, entity_id="", entity_name="", entity_kind=""):
    state = ai.read_state()
    c = state["centroid"]
    return {
        "run_id": csv_run_id,
        "time_seconds": round(sim_time, 4),
        "frame": frame_count,
        "row_type": row_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "entity_kind": entity_kind,
        "ai_enabled": ai.enabled,
        "ai_mode": ai.mode,
        "ai_round": ai.round,
        "ai_mode_timer": round(ai.mode_timer, 4),
        "ai_mode_duration": round(ai.mode_duration, 4),
        "ai_stable_time": round(ai.stable_time, 4),
        "selected_index": selected_index,
        "paused": paused,
        "human_override_active": sim_time < human_override_until,
        "vesicle_count": state["vesicle_count"],
        "attached_count": state["attached_count"],
        "cargo_count": state["cargo_count"],
        "mark_count": state["mark_count"],
        "marked_organelle_count": state["marked_organelle_count"],
        "spill_count": state["spill_count"],
        "wrap_count": state["wrap_count"],
        "avg_speed": round(state["avg_speed"], 6),
        "max_speed": round(state["max_speed"], 6),
        "completion": state["completion"],
        "empty": state["empty"],
        "x": "", "y": "", "z": "", "vx": "", "vy": "", "vz": "", "radius": "", "age": "", "life": "",
        "attached_to": "", "attach_timer": "", "cargo": "", "cargo_from": "", "cargo_to": "", "marks": "", "visible": "", "extra": f"centroid=({c.x:.4f},{c.y:.4f},{c.z:.4f})"
    }

def write_csv_snapshot():
    if _csv_closed:
        return
    # Summary row
    _csv_writer.writerow(base_csv_row("summary", "scene", "cell_scene", "summary"))

    # Main cell objects
    for entity_id, name, obj, radius in [
        ("cell_shell", "Cell shell", cell_shell, CELL_RADIUS),
        ("cell_membrane", "Cell membrane", cell_membrane, CELL_RADIUS * 1.006),
        ("nucleolus", "Nucleolus", nucleolus, nucleolus.radius),
        ("nucleus_wrap_hint", "Nucleus wrap hint", nucleus_wrap_hint, nucleus_wrap_hint.radius),
    ]:
        row = base_csv_row("cell_object", entity_id, name, "cell_object")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": radius, "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

    # Organelles
    for i, o in enumerate(organelles):
        obj = o["obj"]
        row = base_csv_row("organelle", i, o["name"], o["kind"])
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": o["radius"], "marks": o["marks"], "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

    # Vesicles
    for v in vesicles:
        cargo_from = attached_name(v.cargo_from)
        cargo_to = attached_name(v.cargo_to)
        row = base_csv_row("vesicle", v.idx, "V" + str(v.idx + 1), "vesicle")
        row.update({
            "x": v.obj.pos.x, "y": v.obj.pos.y, "z": v.obj.pos.z,
            "vx": v.vel.x, "vy": v.vel.y, "vz": v.vel.z,
            "radius": v.r, "attached_to": attached_name(v.attached_to), "attach_timer": round(v.attach_timer, 4),
            "cargo": v.cargo, "cargo_from": cargo_from, "cargo_to": cargo_to, "visible": getattr(v.obj, "visible", True),
            "extra": f"ai_force=({v.ai_force.x:.4f},{v.ai_force.y:.4f},{v.ai_force.z:.4f});human_touched={v.human_touched}"
        })
        _csv_writer.writerow(row)

    # Ribosomes
    for i, r in enumerate(ribosomes):
        obj = r["obj"]
        row = base_csv_row("ribosome", i, "Ribosome " + str(i + 1), "ribosome")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": obj.radius, "visible": getattr(obj, "visible", True), "extra": f"anchor=({r['anchor'].x:.4f},{r['anchor'].y:.4f},{r['anchor'].z:.4f})"})
        _csv_writer.writerow(row)

    # Flow particles
    for i, fp in enumerate(flow_particles):
        obj = fp["obj"]
        row = base_csv_row("flow_particle", i, "Flow particle " + str(i + 1), "flow_particle")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": obj.radius, "age": round(fp["age"], 4), "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

    # Spill particles
    for i, sp in enumerate(spill_particles):
        obj = sp["obj"]
        row = base_csv_row("spill_particle", i, "Spill particle " + str(i + 1), sp.get("kind", "spill"))
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "vx": sp["vel"].x, "vy": sp["vel"].y, "vz": sp["vel"].z, "radius": obj.radius, "age": round(sp["age"], 4), "life": round(sp["life"], 4), "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

    # Markers and wraps
    for i, mk in enumerate(markers):
        obj = mk["obj"]
        row = base_csv_row("marker", i, "Marker " + str(i + 1), "marker")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": obj.radius, "age": round(mk["age"], 4), "attached_to": attached_name(mk["target"]), "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)
    for i, wr in enumerate(wraps):
        obj = wr["obj"]
        row = base_csv_row("wrap", i, "Wrap " + str(i + 1), "wrap")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "radius": obj.radius, "age": round(wr["age"], 4), "life": round(wr["life"], 4), "attached_to": attached_name(wr["target"]), "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

    # Flow arrows are useful for reconstructing field direction.
    for i, fa in enumerate(flow_arrows):
        obj = fa["obj"]
        row = base_csv_row("flow_arrow", i, "Flow arrow " + str(i + 1), "flow_arrow")
        row.update({"x": obj.pos.x, "y": obj.pos.y, "z": obj.pos.z, "vx": obj.axis.x, "vy": obj.axis.y, "vz": obj.axis.z, "visible": getattr(obj, "visible", True)})
        _csv_writer.writerow(row)

def close_csv_file():
    global _csv_closed
    if not _csv_closed:
        _csv_file.flush()
        _csv_file.close()
        _csv_closed = True

# -----------------------------
# Main simulation loop with CSV storage
# -----------------------------
try:
    while sim_time < CSV_RUN_SECONDS:
        rate(60)
        frame_count += 1

        if paused:
            update_labels()
        else:
            sim_time += DT
            if ai.enabled:
                ai.update(DT, sim_time)
            else:
                for v in vesicles:
                    v.ai_force = vector(0, 0, 0)

            if sim_time < human_override_until and 0 <= selected_index < len(vesicles):
                vesicles[selected_index].ai_force = vector(0, 0, 0)

            for v in vesicles:
                v.update(DT, sim_time)

            handle_vesicle_vesicle_collisions()
            update_particles(DT, sim_time)
            update_spills_and_wraps(DT, sim_time)
            update_ribosomes_and_organelles(DT, sim_time)
            update_labels()

        if sim_time - _csv_last_sample_time >= CSV_SAMPLE_INTERVAL - 1e-9:
            write_csv_snapshot()
            _csv_last_sample_time = sim_time

        if sim_time - _csv_last_flush_time >= CSV_FLUSH_INTERVAL:
            _csv_file.flush()
            _csv_last_flush_time = sim_time

    close_csv_file()
    hud.text = f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}"
    print(f"CSV recording complete: {CSV_OUTPUT_PATH}")
except Exception:
    close_csv_file()
    raise
