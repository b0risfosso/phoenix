from vpython import *
import random as pyrandom
import math
import csv
import os
from datetime import datetime
import time

# ============================================================
# AI Cell Membrane Transport and Vesicle Traffic
# Web-app-compatible CSV storage version
# ============================================================

# -----------------------------
# CSV output configuration
# -----------------------------
CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
CSV_SAMPLE_INTERVAL = 0.10
CSV_STATIC_INTERVAL = 1.00

_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

try:
    _default_script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _default_script_dir = os.getcwd()

if _csv_output_dir:
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-cell-membrane-vesicle-traffic-state-log.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(_default_script_dir, f"{_csv_run_id}-cell-membrane-vesicle-traffic-state-log.csv"),
    )

_csv_parent = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
if _csv_parent:
    os.makedirs(_csv_parent, exist_ok=True)

# -----------------------------
# Scene setup
# -----------------------------
scene.title = "AI Cell Membrane Transport and Vesicle Traffic - CSV Storage Version"
scene.width = 1250
scene.height = 760
scene.background = vector(0.94, 0.98, 1.0)
scene.forward = vector(-0.78, -0.28, -0.56)
scene.up = vector(0, 1, 0)
scene.range = 9.2
scene.caption = (
    "\nKeyboard: I toggle AI | P pause | R reset | Space wrap vesicle | "
    "O pulse nearest channel | M mark | X spill | Arrows/WASD/QE move director\n"
)

distant_light(direction=vector(-0.4, -0.8, -0.3), color=color.white)
local_light(pos=vector(4, 7, 5), color=vector(0.85, 0.92, 1.0))

# -----------------------------
# Constants and global state
# -----------------------------
CELL_R = 6.0
OUTER_R = 8.2
MOLECULE_R = 0.115
DT = 0.022
MAX_MOLECULES = 58
MAX_VESICLES = 10

molecules = []
vesicles = []
channels = []
microtubules = []
organelle_list = []
decorations = []

sim_time = 0.0
frame = 0
paused = False
ai_enabled = True
manual_override_until = 0.0
round_number = 1
last_info_update = 0.0

counts = {
    "passes": 0,
    "bounces": 0,
    "collisions": 0,
    "buds": 0,
    "fusions": 0,
    "transfers": 0,
    "marks": 0,
    "wraps": 0,
    "spills": 0,
    "detaches": 0,
    "resets": 0,
    "round_completions": 0,
}

# -----------------------------
# Utility helpers
# -----------------------------
def randf(a, b):
    return pyrandom.uniform(a, b)


def random_unit():
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        if mag(v) > 0.001:
            return norm(v)


def random_inside(radius=CELL_R - 0.45):
    return random_unit() * (radius * (pyrandom.random() ** (1.0 / 3.0)))


def color_mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return a * (1 - t) + b * t


def clamp_to_director_bounds(pos):
    if mag(pos) > CELL_R + 1.25:
        return norm(pos) * (CELL_R + 1.25)
    return pos


def set_visible(obj, is_visible):
    try:
        obj.visible = is_visible
    except Exception:
        pass


def vector_tuple(v):
    return round(v.x, 5), round(v.y, 5), round(v.z, 5)

# -----------------------------
# Static scene objects
# -----------------------------
cell_shell = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_R,
    color=vector(0.55, 0.82, 1.0),
    opacity=0.13,
    shininess=0.35,
)
inner_glow = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_R * 0.985,
    color=vector(0.86, 0.96, 1.0),
    opacity=0.035,
)
membrane_label = label(
    pos=vector(-4.9, 6.65, 0),
    text="semi-permeable membrane",
    height=13,
    color=vector(0.12, 0.28, 0.44),
    box=False,
    opacity=0,
)

mtoc_pos = vector(-0.55, -0.35, 0.25)
mtoc = sphere(pos=mtoc_pos, radius=0.22, color=vector(0.1, 0.45, 0.95), emissive=True)
mtoc_label = label(
    pos=mtoc_pos + vector(0, 0.55, 0),
    text="MTOC",
    height=10,
    color=vector(0.1, 0.25, 0.6),
    box=False,
    opacity=0,
)

director = sphere(
    pos=vector(CELL_R - 0.85, 0.25, 0.0),
    radius=0.19,
    color=vector(0.15, 0.95, 0.65),
    emissive=True,
    make_trail=True,
    trail_color=vector(0.25, 0.75, 0.7),
    retain=70,
)
director_arrow = arrow(
    pos=director.pos,
    axis=vector(0.6, 0, 0),
    shaftwidth=0.055,
    color=vector(0.05, 0.55, 0.55),
    opacity=0.72,
)
director_label = label(
    pos=director.pos + vector(0, 0.45, 0),
    text="AI transport director",
    height=10,
    color=vector(0.05, 0.36, 0.34),
    box=False,
    opacity=0,
)
info_label = label(
    pos=vector(-7.3, 7.55, 0),
    text="",
    height=12,
    color=vector(0.08, 0.14, 0.22),
    box=False,
    opacity=0,
    align="left",
)
csv_label = label(
    pos=vector(3.8, -7.45, 0),
    text="CSV recording active",
    height=10,
    color=vector(0.22, 0.28, 0.36),
    box=False,
    opacity=0,
)

# -----------------------------
# Organelle and channel classes
# -----------------------------
class Organelle:
    def __init__(self, name, pos, radius, base_color, opacity=0.42):
        self.name = name
        self.pos = pos
        self.radius = radius
        self.base_color = base_color
        self.absorbed = 0
        self.obj = sphere(pos=pos, radius=radius, color=base_color, opacity=opacity, shininess=0.5)
        self.halo = sphere(pos=pos, radius=radius * 1.08, color=base_color, opacity=0.075)
        self.marker = ring(pos=pos, axis=vector(0, 1, 0), radius=radius * 1.28, thickness=0.025, color=base_color, opacity=0.48)
        self.label = label(pos=pos + vector(0, radius + 0.35, 0), text=name, height=10, color=base_color * 0.75, box=False, opacity=0)

    def pulse(self, amount=1.0):
        self.absorbed += amount
        self.halo.radius = self.radius * (1.08 + min(0.35, self.absorbed * 0.008))
        self.halo.opacity = min(0.18, 0.075 + self.absorbed * 0.002)

    def reset_visual(self):
        self.absorbed = 0
        self.halo.radius = self.radius * 1.08
        self.halo.opacity = 0.075


class MembraneChannel:
    def __init__(self, index, direction, channel_color):
        self.index = index
        self.dir = norm(direction)
        self.radius = 0.34
        self.open = False
        self.open_timer = randf(0.5, 3.0)
        self.activity = 0
        self.pos = self.dir * CELL_R
        self.tube = cylinder(pos=self.dir * (CELL_R - 0.52), axis=self.dir * 1.04, radius=self.radius, color=vector(0.55, 0.58, 0.62), opacity=0.27)
        self.gate = sphere(pos=self.pos, radius=self.radius * 0.55, color=channel_color, opacity=0.64, emissive=False)
        self.rim_obj = ring(pos=self.pos, axis=self.dir, radius=self.radius * 1.42, thickness=0.035, color=channel_color, opacity=0.72)

    def set_open(self, value=True, duration=2.5):
        self.open = bool(value)
        self.open_timer = max(self.open_timer, duration)
        if self.open:
            self.tube.opacity = 0.48
            self.gate.color = vector(0.22, 1.0, 0.45)
            self.gate.opacity = 0.82
            self.rim_obj.color = vector(0.08, 0.82, 0.32)
            self.rim_obj.opacity = 0.95
        else:
            self.tube.opacity = 0.22
            self.gate.color = vector(0.58, 0.60, 0.65)
            self.gate.opacity = 0.44
            self.rim_obj.color = vector(0.42, 0.48, 0.55)
            self.rim_obj.opacity = 0.45

    def pulse(self, duration=3.5):
        self.activity += 1
        self.set_open(True, duration)

    def update(self, dt):
        self.open_timer -= dt
        if self.open_timer <= 0:
            if self.open:
                self.set_open(False, randf(1.0, 3.0))
            elif pyrandom.random() < 0.008:
                self.set_open(True, randf(1.2, 4.0))

# -----------------------------
# Build static organelles/channels
# -----------------------------
organelle_list.append(Organelle("nucleus", vector(-1.55, 0.05, -0.25), 1.35, vector(0.55, 0.64, 1.0), 0.34))
organelle_list.append(Organelle("Golgi", vector(2.05, 1.0, 0.45), 0.76, vector(1.0, 0.62, 0.22), 0.48))
organelle_list.append(Organelle("lysosome", vector(1.65, -1.68, -0.35), 0.68, vector(0.95, 0.28, 0.76), 0.46))
organelle_list.append(Organelle("ER", vector(-2.65, 1.42, 0.72), 0.64, vector(0.25, 0.82, 0.52), 0.42))

for i, offset in enumerate([-0.28, 0, 0.28]):
    decorations.append(cylinder(pos=organelle_list[1].pos + vector(-0.55, offset, -0.18), axis=vector(1.1, 0.12 * math.sin(i), 0.22), radius=0.045, color=vector(1.0, 0.52, 0.15), opacity=0.75))

channel_dirs = [
    vector(1, 0.08, 0.12), vector(-0.94, -0.12, 0.3), vector(0.15, 0.98, -0.1),
    vector(-0.22, -0.95, 0.18), vector(0.55, 0.43, 0.72), vector(-0.42, 0.55, -0.72),
    vector(0.62, -0.55, -0.5), vector(-0.64, -0.28, 0.71),
]
channel_colors = [
    vector(0.18, 0.85, 0.95), vector(1.0, 0.62, 0.2), vector(0.58, 0.42, 1.0),
    vector(0.2, 0.9, 0.45), vector(1.0, 0.35, 0.45), vector(0.55, 0.75, 1.0),
    vector(0.92, 0.8, 0.18), vector(0.8, 0.35, 1.0),
]
for idx, (d, c) in enumerate(zip(channel_dirs, channel_colors)):
    ch = MembraneChannel(idx, d, c)
    channels.append(ch)
    microtubules.append(curve(pos=[mtoc_pos, ch.dir * (CELL_R - 0.65)], radius=0.023, color=vector(0.12, 0.43, 0.92), opacity=0.44))

for org in organelle_list:
    microtubules.append(curve(pos=[mtoc_pos, (mtoc_pos + org.pos) * 0.5 + vector(0.18, 0.08, -0.1), org.pos], radius=0.032, color=vector(0.1, 0.38, 0.9), opacity=0.56))

# -----------------------------
# Molecules and vesicles
# -----------------------------
molecule_kinds = [
    ("nutrient", vector(0.12, 0.78, 1.0)),
    ("ion", vector(1.0, 0.86, 0.15)),
    ("protein", vector(0.65, 0.32, 1.0)),
    ("waste", vector(1.0, 0.24, 0.2)),
    ("signal", vector(0.25, 0.95, 0.36)),
]


class Molecule:
    _next_id = 0

    def __init__(self, pos, vel, kind, base_color, inside=True):
        self.id = Molecule._next_id
        Molecule._next_id += 1
        self.pos = pos
        self.vel = vel
        self.kind = kind
        self.base_color = base_color
        self.inside = inside
        self.state = "free"
        self.vesicle = None
        self.offset = vector(0, 0, 0)
        self.marked_until = 0
        self.orbit_org = None
        self.orbit_until = 0
        self.orbit_phase = randf(0, 2 * math.pi)
        self.obj = sphere(pos=pos, radius=MOLECULE_R * randf(0.86, 1.24), color=base_color, opacity=0.93, shininess=0.7)

    def mark(self, duration=8.0):
        self.marked_until = sim_time + duration
        self.obj.color = color_mix(self.base_color, color.white, 0.42)
        self.obj.emissive = True
        counts["marks"] += 1

    def attach_to(self, vesicle, offset):
        self.state = "attached"
        self.vesicle = vesicle
        self.offset = offset
        self.obj.opacity = 0.88

    def detach(self, new_vel=None):
        self.state = "free"
        self.vesicle = None
        if new_vel is not None:
            self.vel = new_vel
        self.obj.opacity = 0.93

    def update_visual(self):
        self.obj.pos = self.pos
        if sim_time > self.marked_until and self.obj.emissive:
            self.obj.emissive = False
            self.obj.color = self.base_color

    def apply_brownian(self, dt):
        self.vel += random_unit() * randf(0.0, 0.18) * math.sqrt(dt)
        if mag(self.vel) > 2.2:
            self.vel = norm(self.vel) * 2.2

    def channel_nearby(self):
        surface_point = norm(self.pos) * CELL_R if mag(self.pos) > 0.001 else vector(CELL_R, 0, 0)
        best = min(channels, key=lambda ch: mag(ch.pos - surface_point))
        return best, mag(best.pos - surface_point)

    def update_orbit(self, dt):
        if self.orbit_org is None or sim_time > self.orbit_until:
            self.orbit_org = None
            return False
        org = self.orbit_org
        self.orbit_phase += dt * 2.1
        radial = vector(math.cos(self.orbit_phase), 0.35 * math.sin(self.orbit_phase * 0.7), math.sin(self.orbit_phase))
        self.pos = org.pos + norm(radial) * (org.radius + 0.38 + 0.15 * math.sin(self.orbit_phase * 2.0))
        self.vel = cross(vector(0, 1, 0), norm(radial)) * 0.6
        self.update_visual()
        return True

    def update(self, dt):
        if self.state != "free":
            if self.vesicle:
                self.pos = self.vesicle.pos + self.offset
                self.update_visual()
            return
        if self.update_orbit(dt):
            return
        self.apply_brownian(dt)
        self.pos += self.vel * dt
        r = mag(self.pos)
        if self.inside:
            for org in organelle_list:
                delta = self.pos - org.pos
                d = mag(delta)
                if d < org.radius + self.obj.radius:
                    n = norm(delta) if d > 0.001 else random_unit()
                    self.pos = org.pos + n * (org.radius + self.obj.radius + 0.01)
                    self.vel = self.vel - 2 * dot(self.vel, n) * n
                    counts["bounces"] += 1
            if r > CELL_R - self.obj.radius:
                n = norm(self.pos)
                ch, dch = self.channel_nearby()
                if ch.open and dch < ch.radius * 1.7 and dot(self.vel, n) > 0:
                    self.inside = False
                    self.pos = n * (CELL_R + self.obj.radius + 0.08)
                    self.vel = self.vel * 0.82 + n * 0.32
                    ch.activity += 1
                    counts["passes"] += 1
                else:
                    self.pos = n * (CELL_R - self.obj.radius - 0.012)
                    self.vel = self.vel - 2 * dot(self.vel, n) * n
                    self.vel *= 0.94
                    counts["bounces"] += 1
        else:
            if r < CELL_R + self.obj.radius:
                n = norm(self.pos)
                ch, dch = self.channel_nearby()
                if ch.open and dch < ch.radius * 1.7 and dot(self.vel, n) < 0:
                    self.inside = True
                    self.pos = n * (CELL_R - self.obj.radius - 0.08)
                    self.vel = self.vel * 0.82 - n * 0.25
                    ch.activity += 1
                    counts["passes"] += 1
                else:
                    self.pos = n * (CELL_R + self.obj.radius + 0.02)
                    self.vel = self.vel - 2 * dot(self.vel, n) * n
                    self.vel *= 0.94
                    counts["bounces"] += 1
            elif r > OUTER_R:
                n = norm(self.pos)
                self.pos = n * OUTER_R
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.86
        self.update_visual()


class Vesicle:
    _next_id = 0

    def __init__(self, start_pos, cargo, target, export_dir=None):
        self.id = Vesicle._next_id
        Vesicle._next_id += 1
        self.start_pos = start_pos
        self.pos = start_pos
        self.cargo = cargo[:]
        self.target = target
        self.export_dir = export_dir
        self.state = "budding"
        self.age = 0
        self.progress = 0
        self.speed = randf(0.35, 0.72)
        self.radius = 0.34 + 0.045 * len(cargo)
        self.fuse_timer = 0
        self.mode_note = "organelle_delivery" if isinstance(target, Organelle) else "membrane_export"
        self.obj = sphere(pos=self.pos, radius=self.radius, color=vector(0.25, 0.84, 1.0) if isinstance(target, Organelle) else vector(1.0, 0.55, 0.25), opacity=0.27, shininess=0.8, make_trail=True, trail_color=vector(0.32, 0.74, 0.95), retain=95)
        self.rim_obj = ring(pos=self.pos, axis=random_unit(), radius=self.radius * 1.05, thickness=0.018, color=self.obj.color, opacity=0.46)
        self.path_curve = None
        for mol in self.cargo:
            offset = mol.pos - self.pos
            if mag(offset) > self.radius * 0.75:
                offset = norm(offset) * self.radius * randf(0.25, 0.72)
            mol.attach_to(self, offset)
        if isinstance(target, Organelle):
            self.target_pos = target.pos + random_unit() * (target.radius * 0.72)
            mid = mtoc_pos + vector(0, randf(-0.2, 0.35), randf(-0.2, 0.2))
            self.path_curve = curve(pos=[self.pos, mid, self.target_pos], radius=0.018, color=vector(0.3, 0.62, 1.0), opacity=0.28)
        else:
            self.target_pos = norm(export_dir if export_dir is not None else self.pos) * (CELL_R + 0.55)
            self.path_curve = curve(pos=[self.pos, self.target_pos], radius=0.018, color=vector(1.0, 0.55, 0.18), opacity=0.26)

    def bezier_pos(self, p):
        if isinstance(self.target, Organelle):
            a = self.start_pos
            b = mtoc_pos
            c = self.target_pos
            return (1 - p) * (1 - p) * a + 2 * (1 - p) * p * b + p * p * c
        return self.start_pos * (1 - p) + self.target_pos * p

    def update_rim(self):
        self.obj.pos = self.pos
        self.rim_obj.pos = self.pos
        self.rim_obj.axis = norm(vector(math.sin(self.age * 1.7) + 0.1, math.cos(self.age * 1.1), 0.55))

    def detach_all(self, violent=False):
        for mol in self.cargo:
            mol.detach(random_unit() * randf(0.8, 1.7) if violent else random_unit() * randf(0.2, 0.7))
        self.cargo = []

    def fuse(self):
        counts["fusions"] += 1
        if isinstance(self.target, Organelle):
            self.target.pulse(len(self.cargo))
            counts["transfers"] += len(self.cargo)
            for mol in self.cargo:
                mol.detach(random_unit() * randf(0.18, 0.62))
                mol.inside = True
                mol.pos = self.target.pos + random_unit() * (self.target.radius + 0.22)
                mol.orbit_org = self.target
                mol.orbit_until = sim_time + randf(2.5, 5.0)
                mol.mark(2.6)
        else:
            counts["spills"] += len(self.cargo)
            n = norm(self.target_pos)
            for mol in self.cargo:
                mol.detach(n * randf(0.55, 1.25) + random_unit() * 0.25)
                mol.inside = False
                mol.pos = n * (CELL_R + randf(0.25, 0.8)) + random_unit() * 0.12
        self.cargo = []
        set_visible(self.obj, False)
        set_visible(self.rim_obj, False)
        if self.path_curve:
            set_visible(self.path_curve, False)
        self.state = "dead"

    def update(self, dt):
        self.age += dt
        if self.state == "budding":
            inward = -norm(self.start_pos)
            self.pos += inward * dt * 0.52
            self.obj.radius = self.radius * (0.72 + 0.28 * min(1.0, self.age / 1.0))
            self.rim_obj.radius = self.obj.radius * 1.05
            if self.age > 1.1 or mag(self.pos) < CELL_R - 1.32:
                self.state = "travel"
                self.start_pos = self.pos
                self.progress = 0
        elif self.state == "travel":
            self.progress += dt * self.speed
            if self.progress > 1:
                self.progress = 1
                self.state = "fusing"
                self.fuse_timer = 0
            self.pos = self.bezier_pos(self.progress)
            if self.progress < 0.98:
                tangent = self.bezier_pos(min(1, self.progress + 0.02)) - self.pos
                if mag(tangent) > 0.001:
                    self.pos += norm(tangent) * 0.018 * math.sin(self.age * 10)
        elif self.state == "fusing":
            self.fuse_timer += dt
            self.obj.opacity = max(0.04, 0.27 * (1 - self.fuse_timer / 0.7))
            self.obj.radius = max(0.04, self.radius * (1 - 0.55 * self.fuse_timer / 0.7))
            self.rim_obj.radius = self.obj.radius * 1.1
            if self.fuse_timer > 0.7:
                self.fuse()
                return
        for mol in self.cargo:
            mol.pos = self.pos + mol.offset
            mol.update_visual()
        self.update_rim()

# -----------------------------
# Simulation operations
# -----------------------------
def create_molecule(inside=True, near=None, kind_name=None):
    if kind_name:
        choices = [item for item in molecule_kinds if item[0] == kind_name]
        kind, c = choices[0] if choices else pyrandom.choice(molecule_kinds)
    else:
        kind, c = pyrandom.choice(molecule_kinds)
    if near is not None:
        pos = near + random_unit() * randf(0.05, 0.65)
    else:
        if inside:
            pos = random_inside(CELL_R - 0.7)
        else:
            d = random_unit()
            pos = d * randf(CELL_R + 0.35, OUTER_R - 0.35)
    vel = random_unit() * randf(0.25, 1.2)
    if not inside:
        vel += -norm(pos) * randf(0.15, 0.55)
    return Molecule(pos, vel, kind, c, inside)


def nearest_channel_to(pos):
    if mag(pos) < 0.001:
        return channels[0]
    surf = norm(pos) * CELL_R
    return min(channels, key=lambda ch: mag(ch.pos - surf))


def richest_membrane_direction(prefer_kind=None):
    best_dir = channels[0].dir
    best_score = -1
    for ch in channels:
        score = 0
        patch = ch.dir * (CELL_R - 0.78)
        for mol in molecules:
            if mol.state == "free" and mol.inside and mag(mol.pos - patch) < 2.0:
                score += 2 if prefer_kind is None or mol.kind == prefer_kind else 1
        score += pyrandom.random() * 0.3
        if score > best_score:
            best_score = score
            best_dir = ch.dir
    return best_dir


def select_target_organelle(mode="constructive"):
    if mode == "careful_import":
        return min(organelle_list, key=lambda org: org.absorbed + pyrandom.random() * 4)
    if mode in ["destructive_flush", "export_spill"]:
        return None
    if mode == "ritual_orbit":
        return organelle_list[int(sim_time / 7) % len(organelle_list)]
    if mode == "artistic_mark":
        return organelle_list[1]
    if mode == "curious_sample":
        return pyrandom.choice(organelle_list)
    return pyrandom.choice([organelle_list[1], organelle_list[2], organelle_list[3], organelle_list[0]])


def make_vesicle_at(direction=None, target=None, prefer_kind=None, max_cargo=7):
    if len(vesicles) >= MAX_VESICLES:
        return None
    if direction is None:
        direction = norm(director.pos) if mag(director.pos) > 0.01 else richest_membrane_direction(prefer_kind)
    direction = norm(direction)
    start = direction * (CELL_R - 0.66)
    candidates = [mol for mol in molecules if mol.state == "free" and mol.inside and mag(mol.pos - start) < 1.75 and (prefer_kind is None or mol.kind == prefer_kind)]
    if len(candidates) < 2:
        all_near = [mol for mol in molecules if mol.state == "free" and mol.inside]
        all_near.sort(key=lambda m: mag(m.pos - start))
        candidates += [m for m in all_near if m not in candidates][: max(0, 3 - len(candidates))]
    if not candidates:
        return None
    pyrandom.shuffle(candidates)
    cargo = candidates[: pyrandom.randint(2, max(2, min(max_cargo, len(candidates))))]
    for mol in cargo:
        mol.pos = start + random_unit() * randf(0.08, 0.42)
        mol.vel *= 0.2
    ves = Vesicle(start, cargo, target if target is not None else "membrane", export_dir=direction if target is None else None)
    vesicles.append(ves)
    counts["buds"] += 1
    counts["wraps"] += 1
    return ves


def mark_near_director(radius=1.4):
    marked = 0
    for mol in molecules:
        if mol.state == "free" and mag(mol.pos - director.pos) < radius:
            mol.mark(randf(4.0, 9.0))
            marked += 1
            if marked >= 8:
                break
    return marked


def spill_near_director():
    did = 0
    for ves in vesicles:
        if ves.state != "dead" and mag(ves.pos - director.pos) < 1.8 and len(ves.cargo) > 0:
            ves.detach_all(violent=True)
            ves.obj.color = vector(1.0, 0.28, 0.15)
            ves.obj.opacity = 0.12
            ves.state = "fusing"
            ves.fuse_timer = 0.55
            counts["detaches"] += 1
            did += 1
    if did == 0:
        for mol in molecules:
            if mol.state == "free" and mag(mol.pos - director.pos) < 1.4:
                mol.vel += norm(mol.pos if mag(mol.pos) > 0.01 else random_unit()) * randf(0.5, 1.2)
                did += 1
    counts["spills"] += did
    return did


def apply_director_force(strength=0.35, radius=1.7, inward=False):
    for mol in molecules:
        if mol.state != "free":
            continue
        d = mag(mol.pos - director.pos)
        if 0.001 < d < radius:
            direction = norm(director.pos - mol.pos)
            if inward:
                direction = -norm(mol.pos)
            mol.vel += direction * strength * (1 - d / radius)


def molecule_collisions():
    for i in range(len(molecules)):
        a = molecules[i]
        if a.state != "free":
            continue
        for j in range(i + 1, len(molecules)):
            b = molecules[j]
            if b.state != "free" or a.inside != b.inside:
                continue
            delta = b.pos - a.pos
            d = mag(delta)
            min_d = a.obj.radius + b.obj.radius
            if 0.001 < d < min_d:
                n = delta / d
                overlap = min_d - d
                a.pos -= n * overlap * 0.5
                b.pos += n * overlap * 0.5
                av = dot(a.vel, n)
                bv = dot(b.vel, n)
                a.vel += (bv - av) * n * 0.96
                b.vel += (av - bv) * n * 0.96
                if pyrandom.random() < 0.18:
                    a.mark(1.2)
                    b.mark(1.2)
                counts["collisions"] += 1


class AIController:
    def __init__(self):
        self.behavior_modes = ["careful_import", "constructive_delivery", "ritual_orbit", "chaotic_mix", "curious_sample", "artistic_mark", "destructive_flush", "export_spill"]
        self.mode = "constructive_delivery"
        self.next_switch = 8.0
        self.cooldown = 0.0
        self.orbit_target = organelle_list[0]
        self.orbit_phase = 0.0
        self.last_metric = -1
        self.stagnant_for = 0.0
        self.round_started = 0.0
        self.completion_pause = 0.0
        self.target_channel = channels[0]
        self.mode_label = label(pos=vector(0, -7.3, 0), text="AI mode: constructive_delivery", height=12, color=vector(0.1, 0.22, 0.38), box=False, opacity=0)

    def read_state(self):
        free_inside = sum(1 for m in molecules if m.state == "free" and m.inside)
        free_outside = sum(1 for m in molecules if m.state == "free" and not m.inside)
        attached = sum(1 for m in molecules if m.state == "attached")
        active_channels = sum(1 for ch in channels if ch.open)
        living_vesicles = sum(1 for v in vesicles if v.state != "dead")
        return {
            "free_inside": free_inside,
            "free_outside": free_outside,
            "attached": attached,
            "active_channels": active_channels,
            "living_vesicles": living_vesicles,
            "total_metric": counts["passes"] + counts["buds"] + counts["fusions"] + counts["transfers"] + counts["spills"] + counts["marks"] // 4,
        }

    def choose_new_mode(self, reason="time"):
        state = self.read_state()
        old = self.mode
        if state["free_inside"] < 7:
            self.mode = "careful_import"
        elif state["living_vesicles"] > 6:
            self.mode = pyrandom.choice(["ritual_orbit", "artistic_mark", "constructive_delivery"])
        elif reason == "stagnation":
            self.mode = pyrandom.choice(["chaotic_mix", "destructive_flush", "curious_sample"])
        elif counts["transfers"] > 0 and counts["transfers"] % 20 < 4:
            self.mode = pyrandom.choice(["export_spill", "artistic_mark", "ritual_orbit"])
        else:
            self.mode = pyrandom.choice([m for m in self.behavior_modes if m != old])
        self.next_switch = sim_time + randf(6.5, 13.5)
        self.cooldown = min(self.cooldown, 0.7)
        self.orbit_target = pyrandom.choice(organelle_list)
        self.target_channel = pyrandom.choice(channels)

    def detect_stagnation_or_completion(self, dt):
        state = self.read_state()
        metric = state["total_metric"]
        if metric == self.last_metric:
            self.stagnant_for += dt
        else:
            self.stagnant_for = 0.0
            self.last_metric = metric
        if self.stagnant_for > 11.0:
            self.choose_new_mode("stagnation")
            self.stagnant_for = 0.0
            for ch in channels:
                if pyrandom.random() < 0.6:
                    ch.pulse(randf(2.0, 4.5))
        empty_or_stable = state["free_inside"] + state["attached"] < 4
        old_round = sim_time - self.round_started > 45.0
        complete_transfer = counts["transfers"] >= 24 * round_number
        if empty_or_stable or old_round or complete_transfer:
            self.completion_pause += dt
            if self.completion_pause > 2.2:
                reset_simulation(looping=True)
                self.round_started = sim_time
                self.completion_pause = 0.0
                self.choose_new_mode("completion")
        else:
            self.completion_pause = 0.0

    def move_director_toward(self, target_pos, dt, speed=1.4):
        delta = target_pos - director.pos
        if mag(delta) > 0.03:
            director.pos += norm(delta) * min(mag(delta), speed * dt)
            director.pos = clamp_to_director_bounds(director.pos)

    def update_director_arrow(self):
        director_arrow.pos = director.pos
        director_label.pos = director.pos + vector(0, 0.45, 0)

    def update(self, dt):
        if not ai_enabled or sim_time < manual_override_until:
            self.update_director_arrow()
            return
        self.detect_stagnation_or_completion(dt)
        if sim_time > self.next_switch:
            self.choose_new_mode("time")
        self.cooldown = max(0.0, self.cooldown - dt)
        state = self.read_state()

        if self.mode == "careful_import":
            for ch in channels:
                ch.set_open(False, ch.open_timer)
            self.target_channel = min(channels, key=lambda ch: mag(ch.pos - director.pos) + 0.05 * ch.activity)
            self.target_channel.pulse(0.28)
            self.move_director_toward(self.target_channel.dir * (CELL_R - 0.45), dt, 1.25)
            apply_director_force(0.12, 2.0, inward=True)
            if self.cooldown <= 0 and state["free_inside"] > 2:
                make_vesicle_at(self.target_channel.dir, select_target_organelle("careful_import"), max_cargo=4)
                self.cooldown = randf(2.8, 4.6)

        elif self.mode == "constructive_delivery":
            d = richest_membrane_direction()
            self.move_director_toward(d * (CELL_R - 0.72), dt, 1.55)
            nearest_channel_to(director.pos).pulse(0.5)
            apply_director_force(0.18, 1.7)
            if self.cooldown <= 0:
                make_vesicle_at(d, select_target_organelle("constructive_delivery"), max_cargo=7)
                self.cooldown = randf(2.2, 3.7)

        elif self.mode == "ritual_orbit":
            self.orbit_phase += dt * 0.82
            org = self.orbit_target
            orbit_radius = org.radius + 1.05 + 0.2 * math.sin(sim_time * 0.7)
            target_pos = org.pos + vector(math.cos(self.orbit_phase), 0.35 * math.sin(self.orbit_phase * 1.7), math.sin(self.orbit_phase)) * orbit_radius
            self.move_director_toward(target_pos, dt, 1.8)
            if int(sim_time * 2) % 3 == 0:
                mark_near_director(1.25)
            if self.cooldown <= 0 and state["free_inside"] > 3:
                make_vesicle_at(richest_membrane_direction(), org, max_cargo=5)
                self.cooldown = randf(3.0, 5.0)

        elif self.mode == "chaotic_mix":
            swirl = vector(math.sin(sim_time * 2.7), math.cos(sim_time * 1.9), math.sin(sim_time * 1.3 + 1.0))
            self.move_director_toward(norm(swirl) * randf(2.3, CELL_R - 0.8), dt, 2.9)
            for ch in channels:
                if pyrandom.random() < 0.025:
                    ch.pulse(randf(1.0, 3.0))
            for mol in molecules:
                if mol.state == "free" and mag(mol.pos) > 0.01:
                    mol.vel += cross(norm(mol.pos), norm(swirl)) * 0.035
            apply_director_force(-0.23, 1.9)
            if self.cooldown <= 0:
                if pyrandom.random() < 0.5:
                    make_vesicle_at(richest_membrane_direction(), pyrandom.choice(organelle_list), max_cargo=4)
                else:
                    spill_near_director()
                self.cooldown = randf(1.6, 2.8)

        elif self.mode == "curious_sample":
            if mag(director.pos - self.target_channel.pos) < 0.5 or self.cooldown <= 0.15:
                self.target_channel = pyrandom.choice(channels)
            self.move_director_toward(self.target_channel.dir * (CELL_R - 0.3), dt, 1.45)
            self.target_channel.pulse(0.4)
            if self.cooldown <= 0:
                mark_near_director(1.1)
                make_vesicle_at(self.target_channel.dir, select_target_organelle("curious_sample"), max_cargo=3)
                self.cooldown = randf(2.4, 4.0)

        elif self.mode == "artistic_mark":
            self.orbit_phase += dt * 1.15
            flower = vector(math.cos(self.orbit_phase) * (3.6 + 0.5 * math.sin(4 * self.orbit_phase)), math.sin(self.orbit_phase * 2.0) * 1.8, math.sin(self.orbit_phase) * (3.6 + 0.5 * math.cos(3 * self.orbit_phase)))
            self.move_director_toward(flower, dt, 2.15)
            mark_near_director(1.55)
            for mol in molecules:
                if mol.state == "free" and mol.inside and sim_time < mol.marked_until:
                    mol.vel += norm(flower - mol.pos) * 0.015
            if self.cooldown <= 0:
                make_vesicle_at(richest_membrane_direction(), organelle_list[1], max_cargo=5)
                self.cooldown = randf(3.5, 5.2)

        elif self.mode == "destructive_flush":
            d = norm(director.pos) if mag(director.pos) > 0.1 else random_unit()
            self.move_director_toward(d * (CELL_R - 0.15), dt, 2.25)
            for ch in channels:
                ch.pulse(0.32)
            for mol in molecules:
                if mol.state == "free" and mol.inside and mag(mol.pos) > 0.01:
                    mol.vel += norm(mol.pos) * 0.026
            if self.cooldown <= 0:
                spill_near_director()
                if pyrandom.random() < 0.45:
                    make_vesicle_at(d, None, prefer_kind="waste", max_cargo=8)
                self.cooldown = randf(1.5, 2.7)

        elif self.mode == "export_spill":
            d = richest_membrane_direction("waste")
            self.move_director_toward(d * (CELL_R - 0.55), dt, 1.75)
            nearest_channel_to(director.pos).pulse(0.65)
            if self.cooldown <= 0:
                make_vesicle_at(d, None, prefer_kind="waste", max_cargo=7)
                self.cooldown = randf(2.1, 3.2)

        director.color = vector(0.15, 0.95, 0.65) if self.mode not in ["destructive_flush", "chaotic_mix"] else vector(1.0, 0.36, 0.18)
        self.mode_label.text = f"AI mode: {self.mode}   round {round_number}"
        self.update_director_arrow()


ai = AIController()


def reset_simulation(looping=False):
    global molecules, vesicles, round_number
    for mol in molecules:
        set_visible(mol.obj, False)
    for ves in vesicles:
        set_visible(ves.obj, False)
        set_visible(ves.rim_obj, False)
        if ves.path_curve:
            set_visible(ves.path_curve, False)
    molecules = []
    vesicles = []
    for org in organelle_list:
        org.reset_visual()
    for ch in channels:
        ch.set_open(False, randf(0.5, 3.0))
    for _ in range(38):
        molecules.append(create_molecule(True))
    for _ in range(20):
        molecules.append(create_molecule(False))
    for ch in pyrandom.sample(channels, 3):
        ch.pulse(randf(2.0, 4.0))
    if looping:
        counts["round_completions"] += 1
        round_number += 1
    counts["resets"] += 1
    director.pos = richest_membrane_direction() * (CELL_R - 0.8)
    try:
        director.clear_trail()
    except Exception:
        pass
    ai.round_started = sim_time
    ai.stagnant_for = 0.0
    ai.last_metric = -1


reset_simulation(looping=False)

# -----------------------------
# Display and keyboard controls
# -----------------------------
def update_info():
    active_channels = sum(1 for ch in channels if ch.open)
    living_vesicles = sum(1 for v in vesicles if v.state != "dead")
    inside = sum(1 for m in molecules if m.state == "free" and m.inside)
    outside = sum(1 for m in molecules if m.state == "free" and not m.inside)
    attached = sum(1 for m in molecules if m.state == "attached")
    info_label.text = (
        f"AI {'ON' if ai_enabled else 'OFF'} | {'PAUSED' if paused else 'running'}\n"
        f"mode: {ai.mode}\n"
        f"molecules inside/outside/vesicle: {inside}/{outside}/{attached}\n"
        f"vesicles: {living_vesicles}   open channels: {active_channels}\n"
        f"passes {counts['passes']}  buds {counts['buds']}  fusions {counts['fusions']}  transfers {counts['transfers']}\n"
        f"collisions {counts['collisions']}  marks {counts['marks']}  spills {counts['spills']}  round {round_number}"
    )


def keydown(evt):
    global paused, ai_enabled, manual_override_until
    k = evt.key.lower()
    step = 0.42
    moved = False
    if k == "p":
        paused = not paused
    elif k == "i":
        ai_enabled = not ai_enabled
    elif k == "r":
        reset_simulation(looping=True)
    elif k == " ":
        make_vesicle_at(norm(director.pos) if mag(director.pos) > 0.01 else richest_membrane_direction(), select_target_organelle(ai.mode), max_cargo=7)
        manual_override_until = sim_time + 4.0
    elif k == "o":
        nearest_channel_to(director.pos).pulse(4.0)
        manual_override_until = sim_time + 4.0
    elif k == "m":
        mark_near_director(1.7)
        manual_override_until = sim_time + 4.0
    elif k == "x":
        spill_near_director()
        manual_override_until = sim_time + 4.0
    elif k in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        ai.mode = ai.behavior_modes[int(k) - 1]
        ai.next_switch = sim_time + 10.0
        manual_override_until = sim_time + 2.0
    elif k in ["left", "a"]:
        director.pos += vector(-step, 0, 0)
        moved = True
    elif k in ["right", "d"]:
        director.pos += vector(step, 0, 0)
        moved = True
    elif k in ["up", "w"]:
        director.pos += vector(0, step, 0)
        moved = True
    elif k in ["down", "s"]:
        director.pos += vector(0, -step, 0)
        moved = True
    elif k == "q":
        director.pos += vector(0, 0, step)
        moved = True
    elif k == "e":
        director.pos += vector(0, 0, -step)
        moved = True
    if moved:
        director.pos = clamp_to_director_bounds(director.pos)
        manual_override_until = sim_time + 5.0
        apply_director_force(0.18, 1.5)


scene.bind("keydown", keydown)

# -----------------------------
# CSV recording helpers
# -----------------------------
CSV_COLUMNS = [
    "run_id", "row_type", "object_id", "frame", "elapsed_seconds", "sim_time", "round_number",
    "ai_enabled", "ai_mode", "paused", "manual_override_active",
    "object_state", "kind", "inside", "attached_to", "target", "cargo_count",
    "x", "y", "z", "vx", "vy", "vz", "radius", "progress", "age",
    "director_x", "director_y", "director_z",
    "active_channels", "molecules_free_inside", "molecules_free_outside", "molecules_attached", "vesicles_alive",
    "passes", "bounces", "collisions", "buds", "fusions", "transfers", "marks", "wraps", "spills", "detaches", "resets", "round_completions",
    "open", "open_timer", "activity", "absorbed", "marked", "orbiting", "marked_until", "notes",
]


def csv_base(row_type, object_id, elapsed_seconds):
    free_inside = sum(1 for m in molecules if m.state == "free" and m.inside)
    free_outside = sum(1 for m in molecules if m.state == "free" and not m.inside)
    attached = sum(1 for m in molecules if m.state == "attached")
    active_channels = sum(1 for ch in channels if ch.open)
    living_vesicles = sum(1 for v in vesicles if v.state != "dead")
    return {
        "run_id": _csv_run_id,
        "row_type": row_type,
        "object_id": object_id,
        "frame": frame,
        "elapsed_seconds": round(elapsed_seconds, 5),
        "sim_time": round(sim_time, 5),
        "round_number": round_number,
        "ai_enabled": int(ai_enabled),
        "ai_mode": ai.mode,
        "paused": int(paused),
        "manual_override_active": int(sim_time < manual_override_until),
        "director_x": round(director.pos.x, 5),
        "director_y": round(director.pos.y, 5),
        "director_z": round(director.pos.z, 5),
        "active_channels": active_channels,
        "molecules_free_inside": free_inside,
        "molecules_free_outside": free_outside,
        "molecules_attached": attached,
        "vesicles_alive": living_vesicles,
        "passes": counts["passes"],
        "bounces": counts["bounces"],
        "collisions": counts["collisions"],
        "buds": counts["buds"],
        "fusions": counts["fusions"],
        "transfers": counts["transfers"],
        "marks": counts["marks"],
        "wraps": counts["wraps"],
        "spills": counts["spills"],
        "detaches": counts["detaches"],
        "resets": counts["resets"],
        "round_completions": counts["round_completions"],
    }


def emit(writer, data):
    writer.writerow([data.get(col, "") for col in CSV_COLUMNS])


def log_csv_snapshot(writer, elapsed_seconds, include_static=False):
    emit(writer, csv_base("summary", "simulation", elapsed_seconds))

    director_row = csv_base("director", "director", elapsed_seconds)
    director_row.update({"x": round(director.pos.x, 5), "y": round(director.pos.y, 5), "z": round(director.pos.z, 5), "object_state": "manual_override" if sim_time < manual_override_until else "auto"})
    emit(writer, director_row)

    for idx, ch in enumerate(channels):
        row = csv_base("channel", f"channel_{idx}", elapsed_seconds)
        row.update({"x": round(ch.pos.x, 5), "y": round(ch.pos.y, 5), "z": round(ch.pos.z, 5), "radius": ch.radius, "open": int(ch.open), "open_timer": round(ch.open_timer, 5), "activity": ch.activity, "object_state": "open" if ch.open else "closed"})
        emit(writer, row)

    for mol in molecules:
        row = csv_base("molecule", f"molecule_{mol.id}", elapsed_seconds)
        row.update({
            "object_state": mol.state,
            "kind": mol.kind,
            "inside": int(mol.inside),
            "attached_to": f"vesicle_{mol.vesicle.id}" if mol.vesicle else "",
            "x": round(mol.pos.x, 5), "y": round(mol.pos.y, 5), "z": round(mol.pos.z, 5),
            "vx": round(mol.vel.x, 5), "vy": round(mol.vel.y, 5), "vz": round(mol.vel.z, 5),
            "radius": round(mol.obj.radius, 5),
            "marked": int(sim_time < mol.marked_until),
            "orbiting": int(mol.orbit_org is not None),
            "marked_until": round(mol.marked_until, 5),
        })
        emit(writer, row)

    for ves in vesicles:
        if ves.state == "dead":
            continue
        row = csv_base("vesicle", f"vesicle_{ves.id}", elapsed_seconds)
        target_name = ves.target.name if isinstance(ves.target, Organelle) else str(ves.target)
        row.update({
            "object_state": ves.state,
            "target": target_name,
            "cargo_count": len(ves.cargo),
            "x": round(ves.pos.x, 5), "y": round(ves.pos.y, 5), "z": round(ves.pos.z, 5),
            "radius": round(ves.obj.radius, 5),
            "progress": round(ves.progress, 5),
            "age": round(ves.age, 5),
            "notes": ves.mode_note,
        })
        emit(writer, row)

    for idx, org in enumerate(organelle_list):
        row = csv_base("organelle", f"organelle_{idx}_{org.name}", elapsed_seconds)
        row.update({"kind": org.name, "x": round(org.pos.x, 5), "y": round(org.pos.y, 5), "z": round(org.pos.z, 5), "radius": org.radius, "absorbed": org.absorbed})
        emit(writer, row)

    if include_static:
        for idx, mt in enumerate(microtubules):
            row = csv_base("microtubule", f"microtubule_{idx}", elapsed_seconds)
            row.update({"object_state": "static", "notes": "microtubule path visualization"})
            emit(writer, row)

# -----------------------------
# Main simulation loop with CSV recording
# -----------------------------
csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(CSV_COLUMNS)
csv_file.flush()

real_start = time.time()
last_csv_log = -1.0
last_static_log = -1.0
csv_rows_since_flush = 0

try:
    while True:
        rate(60)
        elapsed = time.time() - real_start

        if not paused:
            sim_time += DT
            frame += 1
            for ch in channels:
                ch.update(DT)
            ai.update(DT)
            for mol in molecules:
                mol.update(DT)
            molecule_collisions()
            for ves in vesicles[:]:
                ves.update(DT)
            vesicles = [v for v in vesicles if v.state != "dead"]
            if len(molecules) < MAX_MOLECULES and pyrandom.random() < 0.012:
                molecules.append(create_molecule(False))

        if sim_time - last_info_update > 0.25:
            update_info()
            last_info_update = sim_time

        if mag(director.pos) > 0.001:
            director_arrow.pos = director.pos
            if vesicles:
                target_axis = vesicles[0].pos - director.pos
            else:
                target_axis = norm(director.pos) * 0.65
            if mag(target_axis) > 0.01:
                director_arrow.axis = norm(target_axis) * 0.62
            director_label.pos = director.pos + vector(0, 0.45, 0)

        if sim_time - last_csv_log >= CSV_SAMPLE_INTERVAL or frame == 1:
            include_static = (sim_time - last_static_log >= CSV_STATIC_INTERVAL) or frame == 1
            log_csv_snapshot(csv_writer, elapsed, include_static=include_static)
            last_csv_log = sim_time
            if include_static:
                last_static_log = sim_time
            csv_rows_since_flush += 1
            if csv_rows_since_flush >= 8:
                csv_file.flush()
                csv_rows_since_flush = 0

        if elapsed >= CSV_RUN_SECONDS:
            csv_file.flush()
            csv_label.text = f"CSV recording complete: {CSV_RUN_SECONDS:0.0f}s saved to {os.path.basename(CSV_OUTPUT_PATH)}"
            break
finally:
    try:
        csv_file.flush()
        csv_file.close()
    except Exception:
        pass
