from vpython import *
import random
import math
import csv
import os
from datetime import datetime
import time

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

try:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
except Exception:
    _script_dir = os.getcwd()

if _csv_output_dir:
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-simulation-state.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(_script_dir, f"{_csv_run_id}-simulation-state.csv")
    )

AUTO_STOP_AFTER_CSV = bool(
    os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
    or os.environ.get("SIM_STATE_CSV_PATH")
    or os.environ.get("SIMULATION_CSV_RUN_SECONDS")
)

scene = canvas(
    title="AI-Controlled 3D Root System Branching Through Soil Layers",
    width=1180,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0, 0),
    forward=vector(-0.45, -0.25, -0.85),
    range=8.3
)

scene.caption = (
    "\nControls: SPACE/P pause  |  A toggle AI  |  M next AI mode  |  R reset round  |  "
    "F force branch  |  N add water  |  C chaotic pulse\n"
    "Manual root nudge while AI runs: W/S/A/D horizontal, Q/E vertical, release key to stop override.\n"
)

random.seed()

TOP_Y = 5.35
BOTTOM_Y = -5.35
WORLD_RADIUS = 4.25
MAX_TIPS = 42
MAX_SEGMENTS = 1250
BASE_STEP = 0.105

soil_layers = [
    {"name": "sandy topsoil", "y": 4.15, "thick": 2.35, "col": vector(0.91, 0.76, 0.48), "opacity": 0.22},
    {"name": "dark loam", "y": 1.65, "thick": 2.25, "col": vector(0.47, 0.32, 0.20), "opacity": 0.20},
    {"name": "red clay seam", "y": -0.65, "thick": 2.15, "col": vector(0.72, 0.38, 0.25), "opacity": 0.22},
    {"name": "pale silt", "y": -2.75, "thick": 1.65, "col": vector(0.72, 0.64, 0.49), "opacity": 0.18},
    {"name": "gravel bed", "y": -4.45, "thick": 1.75, "col": vector(0.48, 0.50, 0.48), "opacity": 0.22},
]

soil_objects = []
soil_label_objects = []

for layer in soil_layers:
    slab = box(
        pos=vector(0, layer["y"], 0),
        size=vector(9.2, layer["thick"], 9.2),
        color=layer["col"],
        opacity=layer["opacity"]
    )
    soil_objects.append(slab)
    layer_text = label(
        pos=vector(-5.1, layer["y"], 4.65),
        text=layer["name"],
        height=12,
        box=False,
        opacity=0,
        color=layer["col"] * 0.65
    )
    soil_label_objects.append(layer_text)

top_plane = box(pos=vector(0, TOP_Y + 0.03, 0), size=vector(9.2, 0.035, 9.2), color=vector(0.75, 0.68, 0.50), opacity=0.16)
bottom_plane = box(pos=vector(0, BOTTOM_Y - 0.03, 0), size=vector(9.2, 0.04, 9.2), color=vector(0.40, 0.36, 0.31), opacity=0.18)

status_text = label(
    pos=vector(0, 6.25, 0),
    text="",
    height=14,
    box=True,
    border=8,
    opacity=0.45,
    color=vector(0.18, 0.22, 0.18),
    background=vector(1, 1, 0.92)
)

legend_text = label(
    pos=vector(4.65, 5.65, 0),
    text="cyan glow = water pocket\nsilver stones = rocks\nthick amber nodes = absorption swelling\ncolored disks = AI ritual marks",
    height=11,
    box=False,
    opacity=0,
    color=vector(0.22, 0.28, 0.30)
)

dynamic_objects = []
root_tips = []
root_segments = []
rocks = []
water_pockets = []
droplets = []
detached_fragments = []
soil_marks = []
absorption_bulges = []

frame = 0
sim_time = 0.0
round_number = 0
paused = False
ai_enabled = True
manual_override = False
manual_vector = vector(0, 0, 0)
force_branch_request = False
chaotic_pulse_timer = 0.0

branch_count = 0
collision_count = 0
wrap_count = 0
attachment_count = 0
detach_count = 0
mark_count = 0
spill_count = 0
transfer_count = 0
absorption_events = 0
total_absorbed = 0.0
last_absorption_time = -999.0


def add_dynamic(obj):
    dynamic_objects.append(obj)
    return obj


def safe_norm(v, fallback=vector(0, -1, 0)):
    if mag(v) < 1e-8:
        return vector(fallback.x, fallback.y, fallback.z)
    return norm(v)


def clamp(x, a, b):
    return max(a, min(b, x))


def rand_unit():
    z = random.uniform(-1, 1)
    t = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), z, r * math.sin(t))


def rand_horizontal():
    a = random.uniform(0, 2 * math.pi)
    return vector(math.cos(a), 0, math.sin(a))


def layer_at_y(y):
    for layer in soil_layers:
        if abs(y - layer["y"]) <= layer["thick"] * 0.5:
            return layer
    return soil_layers[-1]


def root_color_for_y(y, thickening=0.0):
    layer = layer_at_y(y)
    base = vector(0.54, 0.34, 0.16)
    if "clay" in layer["name"]:
        base = vector(0.60, 0.30, 0.16)
    elif "loam" in layer["name"]:
        base = vector(0.43, 0.27, 0.13)
    elif "gravel" in layer["name"]:
        base = vector(0.50, 0.38, 0.24)
    if thickening > 0:
        return base * (1 - 0.35 * thickening) + vector(1.0, 0.68, 0.26) * (0.35 * thickening)
    return base


class Rock:
    def __init__(self, pos, radius):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.radius = radius
        self.obj = add_dynamic(sphere(
            pos=self.pos,
            radius=radius,
            color=vector(0.56, 0.57, 0.56),
            opacity=0.72,
            shininess=0.35
        ))
        self.shadow = add_dynamic(sphere(
            pos=self.pos + vector(0, -0.015, 0),
            radius=radius * 1.08,
            color=vector(0.35, 0.35, 0.34),
            opacity=0.12
        ))
        self.wrap_score = 0


class WaterPocket:
    def __init__(self, pos, amount, radius):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.max_amount = amount
        self.amount = amount
        self.base_radius = radius
        self.depleted = False
        self.absorbers = 0
        self.obj = add_dynamic(sphere(
            pos=self.pos,
            radius=radius,
            color=vector(0.05, 0.78, 1.0),
            opacity=0.62,
            emissive=True,
            shininess=0.85
        ))
        self.halo = add_dynamic(ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=radius * 1.72,
            thickness=0.026,
            color=vector(0.25, 0.86, 1.0),
            opacity=0.35
        ))
        self.pulse = random.uniform(0, 2 * math.pi)
        self.text_obj = add_dynamic(label(
            pos=self.pos + vector(0, radius + 0.32, 0),
            text="water",
            height=9,
            box=False,
            opacity=0,
            color=vector(0.0, 0.45, 0.72)
        ))

    def update_visual(self, t):
        if self.amount <= 0.01:
            self.depleted = True
            self.obj.visible = False
            self.halo.visible = False
            self.text_obj.visible = False
            return
        frac = clamp(self.amount / self.max_amount, 0.03, 1.0)
        r = self.base_radius * (0.28 + 0.72 * (frac ** (1 / 3)))
        self.obj.radius = r
        self.obj.opacity = 0.28 + 0.36 * frac
        pulse_scale = 1.0 + 0.12 * math.sin(t * 3.2 + self.pulse)
        self.halo.radius = r * 1.72 * pulse_scale
        self.halo.thickness = 0.018 + 0.014 * frac
        self.halo.opacity = 0.12 + 0.30 * frac
        self.text_obj.pos = self.pos + vector(0, r + 0.32, 0)
        self.text_obj.text = "water " + str(int(frac * 100)) + "%"


class RootTip:
    next_id = 0

    def __init__(self, pos, direction, radius=0.075, parent_id=-1, generation=0, mode="primary"):
        self.id = RootTip.next_id
        RootTip.next_id += 1
        self.pos = vector(pos.x, pos.y, pos.z)
        self.prev_pos = vector(pos.x, pos.y, pos.z)
        self.dir = safe_norm(direction)
        self.radius = radius
        self.parent_id = parent_id
        self.generation = generation
        self.active = True
        self.age = 0.0
        self.mode = mode
        self.energy = 1.0
        self.wrap_target = None
        self.orbit_phase = random.uniform(0, 2 * math.pi)
        self.last_branch_time = 0
        self.absorbed_local = 0.0
        self.recent_collision = False
        self.indicator = add_dynamic(sphere(
            pos=self.pos,
            radius=max(0.045, radius * 1.55),
            color=vector(0.82, 0.50, 0.25),
            opacity=0.85
        ))

    def update_indicator(self):
        self.indicator.pos = self.pos
        self.indicator.radius = max(0.035, self.radius * 1.48)
        self.indicator.color = vector(0.82, 0.50, 0.25) if self.active else vector(0.50, 0.38, 0.28)
        self.indicator.opacity = 0.85 if self.active else 0.32


class Droplet:
    def __init__(self, pos, vel, amount=0.12):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(vel.x, vel.y, vel.z)
        self.amount = amount
        self.age = 0.0
        self.obj = add_dynamic(sphere(
            pos=self.pos,
            radius=0.045 + amount * 0.06,
            color=vector(0.05, 0.78, 1.0),
            opacity=0.72,
            emissive=True
        ))


class Fragment:
    def __init__(self, pos, axis, vel):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(vel.x, vel.y, vel.z)
        self.age = 0.0
        self.obj = add_dynamic(cylinder(
            pos=self.pos,
            axis=axis,
            radius=0.035,
            color=vector(0.42, 0.25, 0.12),
            opacity=0.72
        ))


AI_MODES = [
    "careful_seek",
    "curious_branch",
    "ritual_wrap",
    "chaotic_probe",
    "constructive_thicken",
    "artistic_mark",
    "destructive_split",
    "quiet_listen"
]


class RootAIController:
    def __init__(self):
        self.enabled = True
        self.mode = "careful_seek"
        self.mode_timer = 0.0
        self.mode_duration = 8.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_water_remaining = None
        self.last_segment_count = 0
        self.last_check_time = 0.0
        self.reset_requested = False
        self.mode_index_override = 0
        self.last_action = "initialize"
        self.mark_phase = 0.0

    def params(self):
        p = {
            "speed": 1.0,
            "noise": 0.16,
            "branch_boost": 1.0,
            "water_attraction": 1.0,
            "wrap_strength": 1.0,
            "thicken_rate": 1.0,
            "mark_rate": 0.04,
            "spill_rate": 0.0,
            "detach_rate": 0.0,
            "spiral": 0.0
        }
        if self.mode == "careful_seek":
            p.update(speed=0.92, noise=0.07, branch_boost=0.75, water_attraction=1.75, wrap_strength=1.05, mark_rate=0.025)
        elif self.mode == "curious_branch":
            p.update(speed=1.05, noise=0.18, branch_boost=2.6, water_attraction=1.05, wrap_strength=0.85, mark_rate=0.05)
        elif self.mode == "ritual_wrap":
            p.update(speed=0.88, noise=0.10, branch_boost=1.25, water_attraction=0.80, wrap_strength=2.6, spiral=1.5, mark_rate=0.12)
        elif self.mode == "chaotic_probe":
            p.update(speed=1.34, noise=0.62, branch_boost=3.2, water_attraction=0.72, wrap_strength=1.25, spill_rate=0.10, mark_rate=0.10)
        elif self.mode == "constructive_thicken":
            p.update(speed=0.74, noise=0.05, branch_boost=0.55, water_attraction=1.25, thicken_rate=2.7, wrap_strength=0.75, mark_rate=0.035)
        elif self.mode == "artistic_mark":
            p.update(speed=0.82, noise=0.24, branch_boost=1.25, water_attraction=0.95, spiral=0.65, mark_rate=0.28)
        elif self.mode == "destructive_split":
            p.update(speed=1.12, noise=0.42, branch_boost=2.1, water_attraction=0.72, detach_rate=0.018, spill_rate=0.05, mark_rate=0.055)
        elif self.mode == "quiet_listen":
            p.update(speed=0.44, noise=0.025, branch_boost=0.22, water_attraction=1.42, wrap_strength=0.45, mark_rate=0.012)
        return p

    def read_state(self):
        active = [t for t in root_tips if t.active]
        water_remaining = sum(w.amount for w in water_pockets if not w.depleted)
        depleted = sum(1 for w in water_pockets if w.depleted)
        nearest_water_dist = 999
        nearest_water_pos = vector(0, 0, 0)
        if active:
            for w in water_pockets:
                if not w.depleted:
                    d = mag(active[0].pos - w.pos)
                    if d < nearest_water_dist:
                        nearest_water_dist = d
                        nearest_water_pos = w.pos
        near_rock_count = 0
        for t in active:
            for r in rocks:
                if mag(t.pos - r.pos) < r.radius + 0.65:
                    near_rock_count += 1
        return {
            "active_tips": len(active),
            "tip_count": len(root_tips),
            "segment_count": len(root_segments),
            "water_remaining": water_remaining,
            "depleted": depleted,
            "nearest_water_dist": nearest_water_dist,
            "nearest_water_pos": nearest_water_pos,
            "near_rock_count": near_rock_count
        }

    def detect_stagnation(self, t, state):
        if self.last_water_remaining is None:
            self.last_water_remaining = state["water_remaining"]
            self.last_segment_count = state["segment_count"]
            self.last_check_time = t
            return

        if t - self.last_check_time >= 1.0:
            water_delta = abs(self.last_water_remaining - state["water_remaining"])
            seg_delta = abs(self.last_segment_count - state["segment_count"])
            if water_delta < 0.015 and seg_delta < 2:
                self.stagnation_timer += t - self.last_check_time
            else:
                self.stagnation_timer = max(0.0, self.stagnation_timer - 0.5)
            self.last_water_remaining = state["water_remaining"]
            self.last_segment_count = state["segment_count"]
            self.last_check_time = t

    def choose_mode(self, state):
        if state["active_tips"] == 0:
            return "curious_branch"
        if state["water_remaining"] <= 0.06:
            return "artistic_mark"
        if self.stagnation_timer > 9.5:
            return random.choice(["chaotic_probe", "destructive_split", "curious_branch"])
        if state["near_rock_count"] >= 2 and random.random() < 0.55:
            return "ritual_wrap"
        if sim_time - last_absorption_time < 3.0 and random.random() < 0.50:
            return "constructive_thicken"
        if state["active_tips"] < 4:
            return "curious_branch"
        if len(soil_marks) < 8 and random.random() < 0.32:
            return "artistic_mark"
        return random.choice(["careful_seek", "curious_branch", "quiet_listen", "artistic_mark"])

    def update(self, dt):
        if not self.enabled:
            self.last_action = "human_override"
            return self.params()

        state = self.read_state()
        self.detect_stagnation(sim_time, state)

        complete = (
            state["water_remaining"] <= 0.04
            or state["active_tips"] == 0
            or (state["segment_count"] >= MAX_SEGMENTS and state["water_remaining"] < 0.45)
        )
        if complete:
            self.completion_timer += dt
            if self.completion_timer > 4.5:
                self.reset_requested = True
                self.last_action = "reset_round"
        else:
            self.completion_timer = 0.0

        self.mode_timer += dt
        if self.mode_timer >= self.mode_duration:
            self.mode = self.choose_mode(state)
            self.mode_timer = 0.0
            self.mode_duration = random.uniform(5.5, 12.5)
            self.last_action = "switch_to_" + self.mode

        if self.stagnation_timer > 16.0:
            self.reset_requested = True
            self.last_action = "reset_stagnant"

        self.mark_phase += dt
        return self.params()

    def next_mode(self):
        idx = AI_MODES.index(self.mode) if self.mode in AI_MODES else 0
        self.mode = AI_MODES[(idx + 1) % len(AI_MODES)]
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(6.0, 10.0)
        self.last_action = "manual_mode_" + self.mode

    def reset_memory(self):
        self.mode = random.choice(["careful_seek", "curious_branch", "artistic_mark"])
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(6.0, 11.0)
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_water_remaining = None
        self.last_segment_count = 0
        self.last_check_time = sim_time
        self.reset_requested = False
        self.last_action = "new_round"


ai = RootAIController()


def spawn_soil_mark(pos, col=None, radius=None):
    global mark_count
    if len(soil_marks) > 180:
        old = soil_marks.pop(0)
        old.visible = False
    if col is None:
        hue = 0.5 + 0.5 * math.sin(sim_time * 0.8 + mark_count)
        col = vector(0.9, 0.35 + 0.35 * hue, 0.18 + 0.55 * (1 - hue))
    if radius is None:
        radius = random.uniform(0.08, 0.18)
    disk = add_dynamic(cylinder(
        pos=pos,
        axis=vector(0, 0.012, 0),
        radius=radius,
        color=col,
        opacity=0.35
    ))
    soil_marks.append(disk)
    mark_count += 1


def spawn_bulge(pos, radius, intensity=1.0):
    bulge = add_dynamic(sphere(
        pos=pos,
        radius=radius,
        color=vector(1.0, 0.58, 0.18),
        opacity=0.45,
        shininess=0.6
    ))
    absorption_bulges.append(bulge)
    if len(absorption_bulges) > 120:
        old = absorption_bulges.pop(0)
        old.visible = False


def spawn_droplet(pos, vel=None, amount=0.10):
    global spill_count
    if vel is None:
        vel = rand_unit() * random.uniform(0.45, 1.25) + vector(0, random.uniform(-0.35, 0.25), 0)
    droplets.append(Droplet(pos, vel, amount))
    spill_count += 1


def spawn_tip(pos, direction, radius=0.075, parent_id=-1, generation=0, mode="branch"):
    tip = RootTip(pos, direction, radius, parent_id, generation, mode)
    root_tips.append(tip)
    return tip


def create_branch_from_tip(tip, strength=1.0):
    global branch_count, attachment_count
    if len(root_tips) >= MAX_TIPS:
        return None
    side = rand_horizontal() * random.uniform(0.7, 1.25)
    downward = vector(0, random.uniform(-0.70, -0.18), 0)
    inherited = tip.dir * random.uniform(0.15, 0.55)
    new_dir = safe_norm(side + downward + inherited)
    new_radius = max(0.028, tip.radius * random.uniform(0.58, 0.83))
    child = spawn_tip(tip.pos, new_dir, new_radius, tip.id, tip.generation + 1, "lateral")
    attach_node = add_dynamic(sphere(
        pos=tip.pos,
        radius=tip.radius * 1.65,
        color=vector(0.74, 0.42, 0.18),
        opacity=0.72
    ))
    branch_count += 1
    attachment_count += 1
    return child


def nearest_water(pos):
    best = None
    best_d = 999
    for w in water_pockets:
        if not w.depleted and w.amount > 0.01:
            d = mag(pos - w.pos)
            if d < best_d:
                best = w
                best_d = d
    return best, best_d


def nearest_rock(pos):
    best = None
    best_d = 999
    for r in rocks:
        d = mag(pos - r.pos) - r.radius
        if d < best_d:
            best = r
            best_d = d
    return best, best_d


def add_random_water():
    y = random.uniform(BOTTOM_Y + 0.65, TOP_Y - 1.05)
    p = vector(random.uniform(-3.3, 3.3), y, random.uniform(-3.3, 3.3))
    for r in rocks:
        if mag(p - r.pos) < r.radius + 0.75:
            p += safe_norm(p - r.pos, rand_horizontal()) * (r.radius + 0.85)
    water_pockets.append(WaterPocket(p, random.uniform(0.85, 1.65), random.uniform(0.25, 0.42)))


def clear_dynamic_objects():
    for obj in dynamic_objects:
        try:
            obj.visible = False
        except Exception:
            pass
    dynamic_objects[:] = []
    root_tips[:] = []
    root_segments[:] = []
    rocks[:] = []
    water_pockets[:] = []
    droplets[:] = []
    detached_fragments[:] = []
    soil_marks[:] = []
    absorption_bulges[:] = []


def reset_simulation():
    global round_number, branch_count, collision_count, wrap_count, attachment_count, detach_count
    global mark_count, spill_count, transfer_count, absorption_events, total_absorbed, last_absorption_time
    global force_branch_request, chaotic_pulse_timer

    clear_dynamic_objects()
    round_number += 1
    RootTip.next_id = 0
    branch_count = 0
    collision_count = 0
    wrap_count = 0
    attachment_count = 0
    detach_count = 0
    mark_count = 0
    spill_count = 0
    transfer_count = 0
    absorption_events = 0
    total_absorbed = 0.0
    last_absorption_time = -999.0
    force_branch_request = False
    chaotic_pulse_timer = 0.0

    root_start = vector(0, TOP_Y + 0.34, 0)
    trunk = add_dynamic(cylinder(
        pos=root_start + vector(0, 0.40, 0),
        axis=vector(0, -0.46, 0),
        radius=0.135,
        color=vector(0.44, 0.25, 0.11),
        opacity=0.96
    ))
    crown = add_dynamic(sphere(
        pos=root_start + vector(0, 0.42, 0),
        radius=0.19,
        color=vector(0.56, 0.34, 0.15),
        opacity=0.95
    ))

    spawn_tip(root_start, vector(0.02, -1, 0.01), 0.118, -1, 0, "primary")

    rock_count = random.randint(7, 10)
    for i in range(rock_count):
        p = vector(random.uniform(-3.45, 3.45), random.uniform(BOTTOM_Y + 0.55, TOP_Y - 0.95), random.uniform(-3.45, 3.45))
        if mag(vector(p.x, 0, p.z)) < 0.38:
            p.x += random.choice([-1, 1]) * random.uniform(0.55, 1.1)
        rad = random.uniform(0.32, 0.72)
        rocks.append(Rock(p, rad))

    water_count = random.randint(5, 7)
    for i in range(water_count):
        add_random_water()

    for i in range(8):
        p = vector(random.uniform(-3.9, 3.9), random.uniform(BOTTOM_Y + 0.35, TOP_Y - 0.45), random.uniform(-3.9, 3.9))
        spawn_soil_mark(p, col=vector(0.58, 0.43, 0.25), radius=random.uniform(0.035, 0.075))

    ai.reset_memory()


reset_simulation()


def grow_tip(tip, dt, params):
    global collision_count, wrap_count, absorption_events, total_absorbed, transfer_count, last_absorption_time

    if not tip.active:
        tip.update_indicator()
        return

    if len(root_segments) >= MAX_SEGMENTS:
        tip.active = False
        tip.update_indicator()
        return

    tip.age += dt
    tip.recent_collision = False

    desired = vector(0, -0.45, 0) + tip.dir * 0.92

    w, wd = nearest_water(tip.pos)
    if w is not None:
        water_vec = safe_norm(w.pos - tip.pos)
        attraction = params["water_attraction"] * clamp(1.0 / max(0.4, wd), 0.10, 1.65)
        desired += water_vec * attraction

    r, rd = nearest_rock(tip.pos)
    if r is not None and rd < 1.15:
        away = safe_norm(tip.pos - r.pos, rand_horizontal())
        tangent = cross(vector(0, 1, 0), away)
        if mag(tangent) < 0.03:
            tangent = cross(vector(1, 0, 0), away)
        tangent = safe_norm(tangent)
        orbit_sign = 1 if math.sin(tip.orbit_phase + sim_time * 1.4 + tip.id) >= 0 else -1
        desired += tangent * orbit_sign * params["wrap_strength"] * clamp(1.35 - rd, 0.0, 1.35)
        desired += away * clamp(0.58 - rd, 0.0, 0.85)
        if rd < 0.22:
            r.wrap_score += dt
            wrap_count += 1
            tip.wrap_target = r
            if random.random() < 0.06:
                spawn_soil_mark(tip.pos + away * 0.06, col=vector(0.83, 0.50, 0.22), radius=0.055)

    if params["spiral"] > 0:
        spiral_vec = vector(math.cos(sim_time * 2.2 + tip.id), 0, math.sin(sim_time * 2.2 + tip.id))
        desired += spiral_vec * params["spiral"] * 0.28

    desired += rand_unit() * params["noise"]

    if manual_override:
        desired += manual_vector * 1.25

    if chaotic_pulse_timer > 0:
        desired += rand_unit() * 1.2

    desired.y += -0.08
    tip.dir = safe_norm(desired, tip.dir)

    speed_variation = 0.84 + 0.28 * random.random()
    step = BASE_STEP * params["speed"] * speed_variation
    new_pos = tip.pos + tip.dir * step

    radial = vector(new_pos.x, 0, new_pos.z)
    if mag(radial) > WORLD_RADIUS:
        normal = safe_norm(radial)
        new_pos.x = normal.x * WORLD_RADIUS
        new_pos.z = normal.z * WORLD_RADIUS
        tip.dir = safe_norm(tip.dir - normal * 0.75 + vector(0, -0.15, 0))
        collision_count += 1
        tip.recent_collision = True

    if new_pos.y < BOTTOM_Y:
        tip.active = False
        tip.update_indicator()
        spawn_soil_mark(tip.pos, col=vector(0.38, 0.30, 0.22), radius=0.12)
        return

    for rock_obj in rocks:
        d = mag(new_pos - rock_obj.pos)
        min_d = rock_obj.radius + tip.radius * 0.85
        if d < min_d:
            away = safe_norm(new_pos - rock_obj.pos, rand_horizontal())
            tangent = safe_norm(cross(vector(0, 1, 0), away), rand_horizontal())
            if random.random() < 0.5:
                tangent = -tangent
            new_pos = rock_obj.pos + away * min_d
            tip.dir = safe_norm(tangent * 0.82 + away * 0.34 + vector(0, -0.22, 0))
            collision_count += 1
            tip.recent_collision = True
            rock_obj.wrap_score += 0.25
            if random.random() < 0.12:
                spawn_soil_mark(new_pos, col=vector(0.66, 0.45, 0.28), radius=0.065)

    axis = new_pos - tip.pos
    if mag(axis) < 1e-5:
        tip.update_indicator()
        return

    thickening = clamp(tip.absorbed_local * 0.55, 0, 1)
    seg = add_dynamic(cylinder(
        pos=tip.pos,
        axis=axis,
        radius=tip.radius,
        color=root_color_for_y(new_pos.y, thickening),
        opacity=0.96
    ))
    root_segments.append(seg)

    if random.random() < 0.045 and tip.generation <= 4:
        side = safe_norm(cross(tip.dir, rand_unit()), rand_horizontal())
        hair_len = random.uniform(0.08, 0.21)
        hair = add_dynamic(cylinder(
            pos=tip.pos + axis * random.uniform(0.25, 0.85),
            axis=side * hair_len,
            radius=max(0.008, tip.radius * 0.18),
            color=vector(0.63, 0.44, 0.25),
            opacity=0.50
        ))

    tip.prev_pos = tip.pos
    tip.pos = new_pos

    for water in water_pockets:
        if water.depleted:
            continue
        d = mag(tip.pos - water.pos)
        if d < water.obj.radius + tip.radius + 0.16:
            rate = (0.23 + 0.12 * random.random()) * dt * params["thicken_rate"]
            absorbed = min(water.amount, rate)
            if absorbed > 0:
                water.amount -= absorbed
                tip.absorbed_local += absorbed
                tip.radius = clamp(tip.radius + absorbed * 0.045, 0.022, 0.22)
                total_absorbed += absorbed
                transfer_count += 1
                absorption_events += 1
                last_absorption_time = sim_time
                water.absorbers += 1
                if random.random() < 0.34:
                    spawn_bulge(tip.pos, tip.radius * random.uniform(1.45, 2.15), absorbed)
                if random.random() < 0.18:
                    spawn_soil_mark(tip.pos, col=vector(0.13, 0.73, 0.86), radius=0.09)
                if water.amount <= 0.02:
                    water.depleted = True
                    spawn_soil_mark(water.pos, col=vector(0.88, 0.72, 0.28), radius=0.22)
            if params["spill_rate"] > 0 and random.random() < params["spill_rate"]:
                water.amount = max(0, water.amount - 0.018)
                spawn_droplet(water.pos + rand_unit() * water.obj.radius, amount=0.08)

    if random.random() < params["mark_rate"] * dt * 5.0:
        spawn_soil_mark(tip.pos, radius=random.uniform(0.045, 0.13))

    base_branch_prob = 0.018
    if tip.mode == "primary":
        base_branch_prob *= 1.35
    if tip.age - tip.last_branch_time > 1.0:
        if random.random() < base_branch_prob * params["branch_boost"]:
            create_branch_from_tip(tip)
            tip.last_branch_time = tip.age

    if force_branch_request and tip.mode == "primary":
        create_branch_from_tip(tip, strength=2.0)

    if params["detach_rate"] > 0 and tip.generation > 0 and random.random() < params["detach_rate"] * dt:
        detach_tip(tip)

    tip.energy -= dt * 0.004
    if tip.energy < -1 or tip.radius < 0.015:
        tip.active = False

    tip.update_indicator()


def detach_tip(tip):
    global detach_count
    if not tip.active:
        return
    tip.active = False
    axis = tip.dir * random.uniform(0.14, 0.26)
    vel = rand_unit() * random.uniform(0.15, 0.55) + vector(0, -0.25, 0)
    detached_fragments.append(Fragment(tip.pos, axis, vel))
    detach_count += 1
    spawn_soil_mark(tip.pos, col=vector(0.46, 0.19, 0.12), radius=0.09)


def update_droplets(dt):
    for d in list(droplets):
        d.age += dt
        d.vel += vector(0, -0.75, 0) * dt
        d.pos += d.vel * dt

        for r in rocks:
            to_drop = d.pos - r.pos
            if mag(to_drop) < r.radius + d.obj.radius:
                n = safe_norm(to_drop, rand_horizontal())
                d.pos = r.pos + n * (r.radius + d.obj.radius)
                d.vel = d.vel - 1.65 * dot(d.vel, n) * n
                d.vel *= 0.62

        if d.pos.y < BOTTOM_Y:
            d.pos.y = BOTTOM_Y
            d.vel.y = abs(d.vel.y) * 0.32
            d.vel.x *= 0.72
            d.vel.z *= 0.72

        for tip in root_tips:
            if tip.active and mag(tip.pos - d.pos) < tip.radius + d.obj.radius + 0.09:
                tip.radius = clamp(tip.radius + d.amount * 0.016, 0.022, 0.22)
                d.amount = 0
                d.obj.visible = False
                if d in droplets:
                    droplets.remove(d)
                break

        if d.amount <= 0:
            continue

        d.obj.pos = d.pos
        d.obj.opacity = max(0, 0.72 - d.age * 0.10)
        if d.age > 8.0 or d.obj.opacity <= 0.02:
            d.obj.visible = False
            if d in droplets:
                droplets.remove(d)


def update_fragments(dt):
    for f in list(detached_fragments):
        f.age += dt
        f.vel += vector(0, -0.58, 0) * dt
        f.pos += f.vel * dt
        if f.pos.y < BOTTOM_Y:
            f.pos.y = BOTTOM_Y
            f.vel.y = abs(f.vel.y) * 0.24
            f.vel.x *= 0.65
            f.vel.z *= 0.65
        f.obj.pos = f.pos
        f.obj.rotate(angle=dt * 1.7, axis=vector(0.3, 1, 0.2))
        f.obj.opacity = max(0, 0.72 - f.age * 0.08)
        if f.age > 8.5 or f.obj.opacity <= 0.03:
            f.obj.visible = False
            if f in detached_fragments:
                detached_fragments.remove(f)


def update_water_visuals():
    for w in water_pockets:
        w.update_visual(sim_time)


def handle_keydown(evt):
    global paused, ai_enabled, manual_override, manual_vector, force_branch_request, chaotic_pulse_timer
    k = evt.key.lower()
    if k in [" ", "p"]:
        paused = not paused
    elif k == "a":
        ai_enabled = not ai_enabled
        ai.enabled = ai_enabled
    elif k == "m":
        ai.next_mode()
    elif k == "r":
        reset_simulation()
    elif k == "f":
        force_branch_request = True
    elif k == "n":
        add_random_water()
    elif k == "c":
        chaotic_pulse_timer = 2.8
        ai.mode = "chaotic_probe"
        ai.mode_timer = 0
    elif k in ["w", "s", "a", "d", "q", "e", "up", "down", "left", "right"]:
        manual_override = True
        if k in ["w", "up"]:
            manual_vector += vector(0, 0, -1)
        elif k in ["s", "down"]:
            manual_vector += vector(0, 0, 1)
        elif k in ["a", "left"]:
            manual_vector += vector(-1, 0, 0)
        elif k in ["d", "right"]:
            manual_vector += vector(1, 0, 0)
        elif k == "q":
            manual_vector += vector(0, 0.55, 0)
        elif k == "e":
            manual_vector += vector(0, -0.75, 0)
        manual_vector = safe_norm(manual_vector, vector(0, -1, 0))


def handle_keyup(evt):
    global manual_override, manual_vector, force_branch_request
    k = evt.key.lower()
    if k in ["w", "s", "a", "d", "q", "e", "up", "down", "left", "right"]:
        manual_override = False
        manual_vector = vector(0, 0, 0)
    if k == "f":
        force_branch_request = False


scene.bind("keydown", handle_keydown)
scene.bind("keyup", handle_keyup)


csv_file = None
csv_writer = None
csv_enabled = True
csv_closed = False
last_csv_write = 0.0
last_csv_flush = 0.0
csv_error = ""

try:
    os.makedirs(os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH)), exist_ok=True)
    csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "run_id",
        "frame",
        "elapsed_seconds",
        "simulation_time",
        "round_number",
        "paused",
        "ai_enabled",
        "ai_mode",
        "ai_last_action",
        "manual_override",
        "root_tip_count",
        "active_tip_count",
        "root_segment_count",
        "branch_count",
        "attachment_count",
        "detach_count",
        "collision_count",
        "wrap_count",
        "mark_count",
        "spill_count",
        "transfer_count",
        "absorption_events",
        "total_absorbed",
        "water_remaining",
        "depleted_water_pockets",
        "droplet_count",
        "fragment_count",
        "nearest_water_x",
        "nearest_water_y",
        "nearest_water_z",
        "lead_tip_x",
        "lead_tip_y",
        "lead_tip_z",
        "lead_tip_dir_x",
        "lead_tip_dir_y",
        "lead_tip_dir_z",
        "lead_tip_radius",
        "active_rock_wrap_scores",
        "stagnation_seconds",
        "completion_seconds"
    ])
    csv_file.flush()
except Exception as e:
    csv_enabled = False
    csv_error = str(e)


def write_csv_snapshot(elapsed):
    global last_csv_write, last_csv_flush
    if not csv_enabled or csv_closed or csv_writer is None:
        return
    if elapsed - last_csv_write < 0.25:
        return

    active = [t for t in root_tips if t.active]
    lead = active[0] if active else (root_tips[0] if root_tips else None)
    nw, nd = nearest_water(lead.pos if lead else vector(0, 0, 0))
    water_remaining = sum(w.amount for w in water_pockets if not w.depleted)
    depleted_count = sum(1 for w in water_pockets if w.depleted)
    rock_wrap_sum = sum(r.wrap_score for r in rocks)

    if nw is None:
        nwp = vector(0, 0, 0)
    else:
        nwp = nw.pos

    if lead is None:
        lpos = vector(0, 0, 0)
        ldir = vector(0, 0, 0)
        lr = 0
    else:
        lpos = lead.pos
        ldir = lead.dir
        lr = lead.radius

    csv_writer.writerow([
        _csv_run_id,
        frame,
        f"{elapsed:.3f}",
        f"{sim_time:.3f}",
        round_number,
        int(paused),
        int(ai_enabled),
        ai.mode,
        ai.last_action,
        int(manual_override),
        len(root_tips),
        len(active),
        len(root_segments),
        branch_count,
        attachment_count,
        detach_count,
        collision_count,
        wrap_count,
        mark_count,
        spill_count,
        transfer_count,
        absorption_events,
        f"{total_absorbed:.5f}",
        f"{water_remaining:.5f}",
        depleted_count,
        len(droplets),
        len(detached_fragments),
        f"{nwp.x:.4f}",
        f"{nwp.y:.4f}",
        f"{nwp.z:.4f}",
        f"{lpos.x:.4f}",
        f"{lpos.y:.4f}",
        f"{lpos.z:.4f}",
        f"{ldir.x:.4f}",
        f"{ldir.y:.4f}",
        f"{ldir.z:.4f}",
        f"{lr:.5f}",
        f"{rock_wrap_sum:.5f}",
        f"{ai.stagnation_timer:.3f}",
        f"{ai.completion_timer:.3f}"
    ])

    last_csv_write = elapsed
    if elapsed - last_csv_flush >= 2.0:
        csv_file.flush()
        last_csv_flush = elapsed


def close_csv():
    global csv_closed
    if csv_enabled and not csv_closed and csv_file is not None:
        try:
            csv_file.flush()
            csv_file.close()
        except Exception:
            pass
    csv_closed = True


start_wall_time = time.time()
dt = 1.0 / 30.0

while True:
    rate(30)
    frame += 1
    elapsed_wall = time.time() - start_wall_time

    if not paused:
        sim_time += dt
        if chaotic_pulse_timer > 0:
            chaotic_pulse_timer = max(0.0, chaotic_pulse_timer - dt)

        ai.enabled = ai_enabled
        ai_params = ai.update(dt)

        if ai.reset_requested:
            reset_simulation()

        if force_branch_request:
            for t in list(root_tips):
                if t.active and (t.mode == "primary" or random.random() < 0.15):
                    create_branch_from_tip(t)
            force_branch_request = False

        tips_snapshot = list(root_tips)
        random.shuffle(tips_snapshot)
        for tip in tips_snapshot:
            grow_tip(tip, dt, ai_params)

        if ai_params["spill_rate"] > 0:
            for w in water_pockets:
                if not w.depleted and random.random() < ai_params["spill_rate"] * dt:
                    w.amount = max(0.0, w.amount - 0.006)
                    spawn_droplet(w.pos + rand_unit() * max(0.1, w.obj.radius), amount=0.065)

        if len([t for t in root_tips if t.active]) == 0 and len(water_pockets) > 0 and ai_enabled:
            if random.random() < 0.05:
                spawn_tip(vector(0, TOP_Y + 0.30, 0), vector(random.uniform(-0.1, 0.1), -1, random.uniform(-0.1, 0.1)), 0.105, -1, 0, "primary")

        update_droplets(dt)
        update_fragments(dt)
        update_water_visuals()
    else:
        update_water_visuals()

    active_count = len([t for t in root_tips if t.active])
    water_remaining = sum(w.amount for w in water_pockets if not w.depleted)
    depleted_count = sum(1 for w in water_pockets if w.depleted)

    csv_line = ""
    if csv_enabled and not csv_closed:
        csv_line = "\nCSV: recording saved run data"
    elif csv_enabled and csv_closed:
        csv_line = "\nCSV recording complete"
    elif csv_error:
        csv_line = "\nCSV unavailable: " + csv_error[:60]

    status_text.text = (
        f"Round {round_number} | AI {'ON' if ai_enabled else 'OFF'} | Mode: {ai.mode}"
        f" | {'PAUSED' if paused else 'growing'}\n"
        f"tips {active_count}/{len(root_tips)}  segments {len(root_segments)}  branches {branch_count}  "
        f"wraps {wrap_count}  collisions {collision_count}\n"
        f"water {water_remaining:.2f}  depleted {depleted_count}/{len(water_pockets)}  "
        f"absorbed {total_absorbed:.2f}  marks {mark_count}  spills {spill_count}  "
        f"stagnation {ai.stagnation_timer:.1f}s"
        f"{csv_line}"
    )

    write_csv_snapshot(elapsed_wall)

    if csv_enabled and not csv_closed and elapsed_wall >= CSV_RUN_SECONDS:
        close_csv()
        if AUTO_STOP_AFTER_CSV:
            status_text.text += "\nCSV recording complete"
            break

close_csv()
while AUTO_STOP_AFTER_CSV:
    rate(10)
