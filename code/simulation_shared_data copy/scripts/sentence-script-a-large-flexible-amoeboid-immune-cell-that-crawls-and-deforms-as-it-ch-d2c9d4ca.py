from vpython import *
import csv
import os
import time
from datetime import datetime
import math
import random

CSV_RUN_SECONDS = float(os.environ.get("SIMULATION_CSV_RUN_SECONDS", "60"))
_csv_output_dir = os.environ.get("SIMULATION_CSV_OUTPUT_DIR")
_csv_run_id = os.environ.get("SIMULATION_CSV_RUN_ID", datetime.now().strftime("%Y%m%d_%H%M%S"))

if _csv_output_dir:
    CSV_OUTPUT_PATH = os.path.join(_csv_output_dir, f"{_csv_run_id}-simulation-state.csv")
else:
    CSV_OUTPUT_PATH = os.environ.get(
        "SIM_STATE_CSV_PATH",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{_csv_run_id}-simulation-state.csv")
    )

os.makedirs(os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH)), exist_ok=True)

scene.title = "AI Immune Cell Chasing a Pathogen"
scene.width = 1180
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.45, -0.35, -0.82)
scene.up = vector(0, 1, 0)
scene.range = 18
scene.center = vector(0, 1.1, 0)

random.seed()

WHITE_BLUE = vector(0.82, 0.93, 1.0)
CELL_BLUE = vector(0.22, 0.74, 0.95)
CELL_EDGE = vector(0.08, 0.55, 0.82)
BACTERIA_GREEN = vector(0.25, 0.82, 0.36)
TRAIL_GREEN = vector(0.18, 0.92, 0.40)
ENZYME_YELLOW = vector(1.0, 0.78, 0.18)
ENZYME_ORANGE = vector(1.0, 0.45, 0.12)
PURPLE = vector(0.75, 0.42, 1.0)
RED = vector(1.0, 0.25, 0.25)

DISH_RADIUS = 17.5
CELL_BASE_RADIUS = 2.25
CELL_Y = 1.05
PATHOGEN_Y = 0.86

dish_floor = cylinder(
    pos=vector(0, -0.08, 0),
    axis=vector(0, 0.08, 0),
    radius=DISH_RADIUS,
    color=vector(0.90, 0.96, 1.0),
    opacity=0.35
)

dish_rim = ring(
    pos=vector(0, 0.02, 0),
    axis=vector(0, 1, 0),
    radius=DISH_RADIUS,
    thickness=0.16,
    color=vector(0.70, 0.86, 1.0),
    opacity=0.55
)

grid_lines = []
for g in range(-15, 16, 3):
    grid_lines.append(curve(
        pos=[vector(g, 0.005, -15), vector(g, 0.005, 15)],
        radius=0.012,
        color=vector(0.72, 0.84, 0.92),
        opacity=0.22
    ))
    grid_lines.append(curve(
        pos=[vector(-15, 0.005, g), vector(15, 0.005, g)],
        radius=0.012,
        color=vector(0.72, 0.84, 0.92),
        opacity=0.22
    ))

cell_pos = vector(-9.0, CELL_Y, -5.0)
cell_vel = vector(0, 0, 0)
pathogen_pos = vector(8.2, PATHOGEN_Y, 5.4)
pathogen_vel = vector(-0.35, 0, -0.15)
bac_dir = norm(vector(1, 0, 0.18))

attached = False
engulfed = False
digest_complete = False
digestion_progress = 0.0
wrap_progress = 0.0
completion_pause = 0.0
current_bac_scale = 1.0

frame = 0
round_index = 1
collision_count = 0
attach_count = 0
detach_count = 0
engulf_count = 0
mark_count = 0
spill_count = 0
reset_count = 0
orbit_count = 0
wrap_count = 0

paused = False
force_human_override = False
keys_down = set()

cell_core = sphere(
    pos=cell_pos,
    radius=CELL_BASE_RADIUS * 0.96,
    color=CELL_BLUE,
    opacity=0.34,
    shininess=0.15
)

n_nodes = 32
membrane_nodes = []
membrane_points = []
for i in range(n_nodes):
    a = 2 * math.pi * i / n_nodes
    p = cell_pos + vector(math.cos(a) * CELL_BASE_RADIUS, 0.05 * math.sin(a * 3), math.sin(a) * CELL_BASE_RADIUS)
    membrane_points.append(p)
    membrane_nodes.append(sphere(
        pos=p,
        radius=0.33 + 0.04 * random.random(),
        color=CELL_EDGE,
        opacity=0.55,
        shininess=0.2
    ))
membrane_points.append(membrane_points[0])
membrane_curve = curve(pos=membrane_points, radius=0.055, color=CELL_EDGE, opacity=0.55)

pseudopods = []
for i in range(7):
    pseudopods.append(sphere(
        pos=cell_pos,
        radius=0.35,
        color=CELL_BLUE,
        opacity=0.23,
        shininess=0.1,
        visible=True
    ))

wrap_curve_left = curve(pos=[cell_pos for _ in range(11)], radius=0.09, color=vector(0.15, 0.70, 0.95), opacity=0.58, visible=False)
wrap_curve_right = curve(pos=[cell_pos for _ in range(11)], radius=0.09, color=vector(0.15, 0.70, 0.95), opacity=0.58, visible=False)

bacterium_length = 1.35
bacterium_radius = 0.36
bac_body = cylinder(
    pos=pathogen_pos - bac_dir * bacterium_length * 0.5,
    axis=bac_dir * bacterium_length,
    radius=bacterium_radius,
    color=BACTERIA_GREEN,
    opacity=1.0,
    shininess=0.35
)
bac_cap_a = sphere(pos=pathogen_pos - bac_dir * bacterium_length * 0.5, radius=bacterium_radius, color=BACTERIA_GREEN, opacity=1.0)
bac_cap_b = sphere(pos=pathogen_pos + bac_dir * bacterium_length * 0.5, radius=bacterium_radius, color=BACTERIA_GREEN, opacity=1.0)
bac_stripes = []
for offset in [-0.42, 0.0, 0.42]:
    bac_stripes.append(cylinder(
        pos=pathogen_pos + bac_dir * offset - vector(0, bacterium_radius * 1.02, 0),
        axis=vector(0, bacterium_radius * 2.04, 0),
        radius=0.035,
        color=vector(0.12, 0.50, 0.18),
        opacity=0.85
    ))
flagellum_points = [pathogen_pos for _ in range(9)]
flagellum = curve(pos=flagellum_points, radius=0.035, color=vector(0.16, 0.48, 0.16), opacity=0.72)

cell_label = label(
    pos=cell_pos + vector(0, 3.3, 0),
    text="AI immune cell",
    color=vector(0.05, 0.30, 0.46),
    box=False,
    opacity=0,
    height=13
)
pathogen_label = label(
    pos=pathogen_pos + vector(0, 1.3, 0),
    text="pathogen",
    color=vector(0.10, 0.38, 0.10),
    box=False,
    opacity=0,
    height=12
)
status_label = label(
    pos=vector(-15.5, 8.0, 0),
    text="",
    color=vector(0.12, 0.18, 0.26),
    box=False,
    opacity=0,
    height=13
)
controls_label = label(
    pos=vector(0, -1.0, -17.5),
    text="Controls: A toggle AI | O human override | Space/P pause | R reset | E force engulf | WASD move immune | IJKL move pathogen",
    color=vector(0.20, 0.26, 0.32),
    box=False,
    opacity=0,
    height=11
)

chem_trail = []
enzyme_particles = []
digest_particles = []


def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(1, 0, 0)
    return v / m


def xz(v):
    return vector(v.x, 0, v.z)


def clamp_to_dish(pos, vel, margin):
    flat = vector(pos.x, 0, pos.z)
    d = mag(flat)
    limit = DISH_RADIUS - margin
    if d > limit:
        inward = -safe_norm(flat)
        pos = vector(flat.x, pos.y, flat.z)
        pos.x = safe_norm(flat).x * limit
        pos.z = safe_norm(flat).z * limit
        normal = safe_norm(flat)
        vel = vel - 1.75 * dot(vel, normal) * normal
        vel += inward * 0.15
    return pos, vel


def update_bacterium_visual(t):
    global bac_dir
    scale = max(0.03, current_bac_scale)
    visible_now = current_bac_scale > 0.045
    for obj in [bac_body, bac_cap_a, bac_cap_b, flagellum] + bac_stripes:
        obj.visible = visible_now

    if mag(pathogen_vel) > 0.03 and not engulfed:
        desired = safe_norm(xz(pathogen_vel))
        bac_dir = safe_norm(bac_dir * 0.92 + desired * 0.08)
    elif engulfed:
        bac_dir = safe_norm(vector(math.cos(t * 1.7), 0.08 * math.sin(t * 2.1), math.sin(t * 1.7)))

    opacity = max(0.04, min(1.0, 1.0 - digestion_progress * 1.05))
    bac_body.opacity = opacity
    bac_cap_a.opacity = opacity
    bac_cap_b.opacity = opacity

    bac_body.radius = bacterium_radius * scale
    bac_body.axis = bac_dir * bacterium_length * scale
    bac_body.pos = pathogen_pos - bac_dir * bacterium_length * scale * 0.5
    bac_cap_a.radius = bacterium_radius * scale
    bac_cap_b.radius = bacterium_radius * scale
    bac_cap_a.pos = pathogen_pos - bac_dir * bacterium_length * scale * 0.5
    bac_cap_b.pos = pathogen_pos + bac_dir * bacterium_length * scale * 0.5

    for n, stripe_obj in enumerate(bac_stripes):
        offset = (-0.42 + n * 0.42) * scale
        stripe_obj.pos = pathogen_pos + bac_dir * offset - vector(0, bacterium_radius * scale * 1.04, 0)
        stripe_obj.axis = vector(0, bacterium_radius * scale * 2.08, 0)
        stripe_obj.radius = 0.035 * scale
        stripe_obj.opacity = opacity * 0.75

    tail_base = pathogen_pos - bac_dir * bacterium_length * scale * 0.72
    side = safe_norm(vector(-bac_dir.z, 0, bac_dir.x))
    for i in range(9):
        u = i / 8.0
        wiggle = side * math.sin(t * 9.0 - u * 7.0) * 0.18 * scale * (1.0 - u * 0.3)
        p = tail_base - bac_dir * (0.20 + u * 1.05) * scale + wiggle
        flagellum.modify(i, pos=p)
    flagellum.opacity = opacity * 0.65


def add_chem_mark(pos, strong=False):
    global mark_count
    mark_count += 1
    chem_trail.append({
        "obj": sphere(
            pos=vector(pos.x, 0.07, pos.z),
            radius=random.uniform(0.10, 0.22) * (1.55 if strong else 1.0),
            color=TRAIL_GREEN,
            opacity=0.18 if not strong else 0.26,
            shininess=0
        ),
        "age": 0.0,
        "life": random.uniform(7.0, 12.0) * (1.25 if strong else 1.0),
        "strong": strong
    })


def update_chem_trail(dt):
    alive = []
    for item in chem_trail:
        item["age"] += dt
        f = max(0.0, 1.0 - item["age"] / item["life"])
        item["obj"].opacity = (0.20 if item["strong"] else 0.14) * f
        item["obj"].radius *= (1.0 + 0.018 * dt)
        if f > 0.02:
            alive.append(item)
        else:
            item["obj"].visible = False
    chem_trail[:] = alive[-240:]


def spill_enzyme(pos, count=3, outward=None):
    global spill_count
    spill_count += count
    if outward is None:
        outward = vector(random.uniform(-1, 1), 0, random.uniform(-1, 1))
    outward = safe_norm(xz(outward))
    for _ in range(count):
        vel = outward * random.uniform(0.35, 1.1) + vector(random.uniform(-0.18, 0.18), random.uniform(0.05, 0.35), random.uniform(-0.18, 0.18))
        enzyme_particles.append({
            "obj": sphere(
                pos=pos + vector(random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.35), random.uniform(-0.25, 0.25)),
                radius=random.uniform(0.055, 0.13),
                color=ENZYME_YELLOW if random.random() < 0.65 else PURPLE,
                opacity=0.72,
                emissive=False
            ),
            "vel": vel,
            "age": 0.0,
            "life": random.uniform(1.8, 4.4)
        })


def update_enzyme_particles(dt):
    alive = []
    for item in enzyme_particles:
        item["age"] += dt
        item["vel"] += vector(0, -0.12, 0) * dt
        item["obj"].pos += item["vel"] * dt
        if item["obj"].pos.y < 0.08:
            item["obj"].pos.y = 0.08
            item["vel"].y *= -0.35
            item["vel"].x *= 0.88
            item["vel"].z *= 0.88
        f = max(0, 1 - item["age"] / item["life"])
        item["obj"].opacity = 0.72 * f
        item["obj"].radius *= (1.0 - 0.09 * dt)
        if f > 0.03:
            alive.append(item)
        else:
            item["obj"].visible = False
    enzyme_particles[:] = alive[-180:]


def create_digest_particles():
    digest_particles.clear()
    for i in range(34):
        rel = vector(random.uniform(-0.8, 0.8), random.uniform(-0.45, 0.55), random.uniform(-0.8, 0.8))
        if mag(rel) > 0.95:
            rel = safe_norm(rel) * random.uniform(0.25, 0.95)
        digest_particles.append({
            "obj": sphere(
                pos=cell_pos + rel,
                radius=random.uniform(0.045, 0.13),
                color=ENZYME_YELLOW if i % 3 else ENZYME_ORANGE,
                opacity=0.82
            ),
            "vel": vector(random.uniform(-0.75, 0.75), random.uniform(-0.25, 0.25), random.uniform(-0.75, 0.75)),
            "phase": random.random() * 10.0
        })


def update_digest_particles(dt, t):
    if not engulfed:
        return
    inner_radius = CELL_BASE_RADIUS * 0.83
    for item in digest_particles:
        rel_to_cell = item["obj"].pos - cell_pos
        to_pathogen = pathogen_pos - item["obj"].pos
        tangent = cross(vector(0, 1, 0), rel_to_cell)
        item["vel"] += safe_norm(to_pathogen) * (0.46 + 0.75 * digestion_progress) * dt
        item["vel"] += safe_norm(tangent) * (0.58 + 0.4 * math.sin(t + item["phase"])) * dt
        item["vel"] *= (1.0 - 0.55 * dt)
        item["obj"].pos += item["vel"] * dt
        rel = item["obj"].pos - cell_pos
        if mag(rel) > inner_radius:
            normal = safe_norm(rel)
            item["obj"].pos = cell_pos + normal * inner_radius
            item["vel"] -= 1.9 * dot(item["vel"], normal) * normal
        pulse = 0.72 + 0.28 * math.sin(t * 8 + item["phase"])
        item["obj"].opacity = max(0.05, (0.85 - digestion_progress * 0.35) * pulse)
        item["obj"].color = ENZYME_YELLOW * (1 - digestion_progress) + ENZYME_ORANGE * digestion_progress


def update_cell_visual(t, action):
    target_vec = pathogen_pos - cell_pos
    target_vec.y = 0
    d = safe_norm(target_vec)
    dist = max(0.1, mag(target_vec))
    speed_stretch = min(1.0, mag(cell_vel) / 3.2)
    mode = action.get("mode", "idle")
    wrap_intensity = action.get("wrap_intensity", 0.0)
    artistic = 1.0 if mode == "artistic_mark" else 0.0
    chaotic = 1.0 if mode == "chaotic_zigzag" else 0.0

    core_pulse = 0.035 * math.sin(t * 3.0) + 0.025 * math.sin(t * 7.1)
    cell_core.pos = cell_pos
    cell_core.radius = CELL_BASE_RADIUS * (0.96 + core_pulse + 0.04 * wrap_progress)
    cell_core.opacity = 0.34 + 0.12 * min(1.0, digestion_progress)

    max_forward_stretch = 1.75 * (1.0 - min(1.0, dist / 12.0)) + 0.5 * speed_stretch + 1.3 * wrap_intensity
    if engulfed:
        max_forward_stretch = 0.32 + 0.18 * math.sin(t * 2.2)

    outline = []
    for i in range(n_nodes):
        a = 2 * math.pi * i / n_nodes
        radial = vector(math.cos(a), 0, math.sin(a))
        forward = max(0, dot(radial, d))
        rear = max(0, -dot(radial, d))
        side_wave = math.sin(a * 4 + t * 2.4) * 0.12
        chaos_wave = chaotic * math.sin(t * 7.0 + i * 1.7) * 0.23
        art_wave = artistic * math.sin(a * 7 - t * 2.0) * 0.22
        stretch = max_forward_stretch * (forward ** 3.1) - 0.30 * rear * speed_stretch
        if attached and not engulfed:
            stretch += 0.55 * (forward ** 5)
        if engulfed:
            stretch += 0.15 * math.sin(t * 5 + i)

        r = CELL_BASE_RADIUS + stretch + side_wave + chaos_wave + art_wave
        ywiggle = 0.10 * math.sin(t * 3.5 + i * 0.8) + 0.08 * math.sin(a * 2 + t)
        p = cell_pos + radial * r + vector(0, ywiggle, 0)
        membrane_nodes[i].pos = p
        membrane_nodes[i].radius = 0.31 + 0.05 * math.sin(t * 4.0 + i) + 0.05 * forward * wrap_intensity
        membrane_nodes[i].opacity = 0.55 + 0.12 * wrap_progress
        membrane_curve.modify(i, pos=p)
        outline.append(p)
    membrane_curve.modify(n_nodes, pos=outline[0])

    for i, pod in enumerate(pseudopods):
        u = (i + 1) / len(pseudopods)
        wobble_side = safe_norm(vector(-d.z, 0, d.x)) * math.sin(t * 3.0 + i * 1.3) * (0.12 + 0.22 * chaotic)
        reach = CELL_BASE_RADIUS + max_forward_stretch * (0.55 + u * 0.68) + 0.25 * math.sin(t * 4 + i)
        if attached and not engulfed:
            reach = CELL_BASE_RADIUS + dist * min(0.94, 0.38 + u * 0.14)
        if engulfed:
            reach = CELL_BASE_RADIUS * (0.45 + 0.25 * math.sin(t + i))
        pod.pos = cell_pos + d * reach + wobble_side + vector(0, 0.02 * i, 0)
        pod.radius = 0.30 + 0.42 * (1 - u) + 0.18 * wrap_intensity + 0.08 * math.sin(t * 3.5 + i)
        pod.opacity = 0.18 + 0.20 * min(1.0, wrap_progress + wrap_intensity)
        pod.visible = True

    close_enough = (dist < 5.0 and not engulfed) or attached
    wrap_curve_left.visible = close_enough
    wrap_curve_right.visible = close_enough

    if close_enough:
        perp = safe_norm(vector(-d.z, 0, d.x))
        for side, curve_obj in [(-1, wrap_curve_left), (1, wrap_curve_right)]:
            for j in range(11):
                u = j / 10.0
                arc_height = math.sin(math.pi * u)
                reach = min(dist + 0.5, CELL_BASE_RADIUS + 3.2) * u
                side_span = side * perp * arc_height * (0.55 + 1.05 * wrap_progress + 0.15 * math.sin(t * 3 + j))
                p = cell_pos + d * (CELL_BASE_RADIUS * 0.55 + reach) + side_span + vector(0, 0.24 * arc_height, 0)
                curve_obj.modify(j, pos=p)


def get_human_action():
    immune = vector(0, 0, 0)
    pathogen = vector(0, 0, 0)
    if "w" in keys_down or "up" in keys_down:
        immune += vector(0, 0, -1)
    if "s" in keys_down or "down" in keys_down:
        immune += vector(0, 0, 1)
    if "a" in keys_down or "left" in keys_down:
        immune += vector(-1, 0, 0)
    if "d" in keys_down or "right" in keys_down:
        immune += vector(1, 0, 0)

    if "i" in keys_down:
        pathogen += vector(0, 0, -1)
    if "k" in keys_down:
        pathogen += vector(0, 0, 1)
    if "j" in keys_down:
        pathogen += vector(-1, 0, 0)
    if "l" in keys_down:
        pathogen += vector(1, 0, 0)

    return immune, pathogen


def reset_simulation(reason="loop"):
    global cell_pos, cell_vel, pathogen_pos, pathogen_vel, bac_dir
    global attached, engulfed, digest_complete, digestion_progress, wrap_progress, completion_pause, current_bac_scale
    global round_index, reset_count

    reset_count += 1
    round_index += 1
    angle_a = random.uniform(0, 2 * math.pi)
    angle_b = angle_a + math.pi + random.uniform(-0.55, 0.55)
    cell_pos = vector(math.cos(angle_a) * random.uniform(5.5, 9.0), CELL_Y, math.sin(angle_a) * random.uniform(5.5, 9.0))
    pathogen_pos = vector(math.cos(angle_b) * random.uniform(6.0, 10.0), PATHOGEN_Y, math.sin(angle_b) * random.uniform(6.0, 10.0))
    cell_vel = vector(0, 0, 0)
    pathogen_vel = vector(random.uniform(-0.25, 0.25), 0, random.uniform(-0.25, 0.25))
    bac_dir = safe_norm(vector(random.uniform(-1, 1), 0, random.uniform(-1, 1)))

    attached = False
    engulfed = False
    digest_complete = False
    digestion_progress = 0.0
    wrap_progress = 0.0
    completion_pause = 0.0
    current_bac_scale = 1.0

    for item in chem_trail:
        item["obj"].visible = False
    chem_trail.clear()

    for item in enzyme_particles:
        item["obj"].visible = False
    enzyme_particles.clear()

    for item in digest_particles:
        item["obj"].visible = False
    digest_particles.clear()

    for obj in [bac_body, bac_cap_a, bac_cap_b, flagellum] + bac_stripes:
        obj.visible = True
        obj.opacity = 1.0

    if hasattr(ai_controller, "set_mode"):
        ai_controller.set_mode(random.choice(["seek", "careful_stalk", "ritual_orbit", "artistic_mark"]), "reset")


class AIController:
    def __init__(self):
        self.enabled = True
        self.behavior_modes = [
            "seek",
            "careful_stalk",
            "chaotic_zigzag",
            "ritual_orbit",
            "artistic_mark",
            "curious_dip",
            "wrap",
            "digest",
            "reset_pause"
        ]
        self.mode = "seek"
        self.previous_mode = "seek"
        self.time_in_mode = 0.0
        self.mode_duration = random.uniform(4.0, 8.0)
        self.last_distance = None
        self.stagnation_timer = 0.0
        self.complete_timer = 0.0
        self.random_bias = vector(random.uniform(-1, 1), 0, random.uniform(-1, 1))
        self.last_action_name = "boot"

    def set_mode(self, mode, reason=""):
        if mode not in self.behavior_modes:
            mode = "seek"
        self.previous_mode = self.mode
        self.mode = mode
        self.time_in_mode = 0.0
        self.mode_duration = random.uniform(3.5, 8.5)
        self.random_bias = safe_norm(vector(random.uniform(-1, 1), 0, random.uniform(-1, 1)))
        self.last_action_name = f"{mode}:{reason}"

    def read_state(self):
        distance = mag(xz(pathogen_pos - cell_pos))
        rel = pathogen_pos - cell_pos
        return {
            "cell_pos": cell_pos,
            "cell_vel": cell_vel,
            "pathogen_pos": pathogen_pos,
            "pathogen_vel": pathogen_vel,
            "distance": distance,
            "direction": safe_norm(xz(rel)),
            "attached": attached,
            "engulfed": engulfed,
            "digest_complete": digest_complete,
            "digestion_progress": digestion_progress,
            "wrap_progress": wrap_progress,
            "round_index": round_index
        }

    def update_stagnation(self, state, dt):
        if self.last_distance is None:
            self.last_distance = state["distance"]
            return
        if state["engulfed"]:
            if state["digestion_progress"] > 0.985:
                self.complete_timer += dt
            else:
                self.complete_timer = 0.0
            self.stagnation_timer = 0.0
        else:
            improvement = self.last_distance - state["distance"]
            if abs(improvement) < 0.015 and mag(cell_vel) < 0.17 and mag(pathogen_vel) < 0.17:
                self.stagnation_timer += dt
            elif improvement < -0.05:
                self.stagnation_timer += dt * 0.25
            else:
                self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 0.7)
        self.last_distance = state["distance"]

    def choose_next_wandering_mode(self):
        choices = ["seek", "careful_stalk", "chaotic_zigzag", "ritual_orbit", "artistic_mark", "curious_dip"]
        if self.mode in choices and len(choices) > 1:
            choices.remove(self.mode)
        return random.choice(choices)

    def choose_action(self, dt):
        state = self.read_state()
        self.update_stagnation(state, dt)
        self.time_in_mode += dt

        if state["digest_complete"] or self.complete_timer > 2.5:
            if self.mode != "reset_pause":
                self.set_mode("reset_pause", "completion")
        elif state["engulfed"]:
            if self.mode != "digest":
                self.set_mode("digest", "inside")
        elif state["distance"] < CELL_BASE_RADIUS + 1.05:
            if self.mode != "wrap":
                self.set_mode("wrap", "contact")
        elif self.stagnation_timer > 8.0:
            self.set_mode(random.choice(["chaotic_zigzag", "artistic_mark", "ritual_orbit"]), "stagnation")
            self.stagnation_timer = 0.0
        elif self.time_in_mode > self.mode_duration:
            self.set_mode(self.choose_next_wandering_mode(), "timer")

        d = state["direction"]
        tangent = safe_norm(vector(-d.z, 0, d.x))
        wobble = math.sin(time.time() * 2.1 + self.time_in_mode)
        immune_accel = vector(0, 0, 0)
        pathogen_accel = vector(0, 0, 0)
        action = {
            "mode": self.mode,
            "immune_accel": immune_accel,
            "pathogen_accel": pathogen_accel,
            "attach": False,
            "detach": False,
            "mark": False,
            "spill": False,
            "wrap_intensity": 0.0,
            "orbit_strength": 0.0,
            "reset": False
        }

        if self.mode == "seek":
            immune_accel = d * 5.2
            pathogen_accel = d * 2.1 + tangent * 0.45 * wobble
            action["wrap_intensity"] = 0.2

        elif self.mode == "careful_stalk":
            immune_accel = d * 2.8 + tangent * 0.75 * math.sin(self.time_in_mode * 1.2)
            pathogen_accel = d * 1.45 + tangent * 0.25 * math.cos(self.time_in_mode * 2.0)
            action["mark"] = random.random() < 0.03
            action["wrap_intensity"] = 0.1

        elif self.mode == "chaotic_zigzag":
            if random.random() < 0.045:
                self.random_bias = safe_norm(vector(random.uniform(-1, 1), 0, random.uniform(-1, 1)))
            immune_accel = d * 3.0 + tangent * random.uniform(-3.5, 3.5) + self.random_bias * 1.8
            pathogen_accel = d * 3.0 + tangent * random.uniform(-2.2, 2.2)
            action["mark"] = random.random() < 0.09
            action["spill"] = random.random() < 0.04
            action["detach"] = attached and random.random() < 0.006

        elif self.mode == "ritual_orbit":
            orbit_sign = 1 if math.sin(self.time_in_mode * 0.55) >= 0 else -1
            immune_accel = d * 2.0 + tangent * orbit_sign * 3.7
            pathogen_accel = d * 1.25 - tangent * orbit_sign * 0.7
            action["orbit_strength"] = orbit_sign * 1.0
            action["mark"] = random.random() < 0.12
            action["wrap_intensity"] = 0.28

        elif self.mode == "artistic_mark":
            immune_accel = d * 1.85 + tangent * (2.8 * math.sin(self.time_in_mode * 1.45))
            pathogen_accel = d * 1.2 + tangent * (1.7 * math.cos(self.time_in_mode * 1.8))
            action["mark"] = True
            action["spill"] = random.random() < 0.08
            action["wrap_intensity"] = 0.15 + 0.15 * math.sin(self.time_in_mode * 3.0)

        elif self.mode == "curious_dip":
            pulse = math.sin(self.time_in_mode * 2.8)
            immune_accel = d * (2.2 + 1.8 * max(0, pulse)) - d * 1.0 * max(0, -pulse) + tangent * 0.9 * wobble
            pathogen_accel = d * (1.0 + 0.5 * max(0, pulse))
            action["spill"] = random.random() < 0.06
            action["mark"] = random.random() < 0.05
            action["wrap_intensity"] = 0.45 * max(0, pulse)

        elif self.mode == "wrap":
            immune_accel = d * 6.0 + tangent * 0.4 * math.sin(self.time_in_mode * 5)
            pathogen_accel = d * (0.65 if attached else 1.2)
            action["attach"] = True
            action["wrap_intensity"] = 1.3
            action["mark"] = random.random() < 0.05
            action["spill"] = random.random() < 0.08

        elif self.mode == "digest":
            swirl = safe_norm(vector(math.cos(self.time_in_mode * 2.2), 0, math.sin(self.time_in_mode * 2.2)))
            immune_accel = swirl * 0.55
            pathogen_accel = vector(0, 0, 0)
            action["spill"] = random.random() < 0.10
            action["wrap_intensity"] = 0.8

        elif self.mode == "reset_pause":
            immune_accel = vector(0, 0, 0)
            pathogen_accel = vector(0, 0, 0)
            if self.time_in_mode > 2.2:
                action["reset"] = True

        action["immune_accel"] = immune_accel
        action["pathogen_accel"] = pathogen_accel
        return action


ai_controller = AIController()


def on_keydown(evt):
    global paused, force_human_override, engulfed, attached, wrap_progress
    k = evt.key.lower()
    keys_down.add(k)
    if k in [" ", "space", "p"]:
        paused = not paused
    elif k == "a":
        ai_controller.enabled = not ai_controller.enabled
    elif k == "o":
        force_human_override = not force_human_override
    elif k == "r":
        reset_simulation("human")
    elif k == "e":
        if not engulfed:
            attached = True
            wrap_progress = 1.0


def on_keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)


scene.bind("keydown", on_keydown)
scene.bind("keyup", on_keyup)


def csv_vector(v):
    return (round(v.x, 5), round(v.y, 5), round(v.z, 5))


csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow([
    "run_id",
    "frame",
    "elapsed_seconds",
    "simulation_seconds",
    "round_index",
    "ai_enabled",
    "human_override",
    "paused",
    "ai_mode",
    "ai_action",
    "cell_x",
    "cell_y",
    "cell_z",
    "cell_vx",
    "cell_vy",
    "cell_vz",
    "pathogen_x",
    "pathogen_y",
    "pathogen_z",
    "pathogen_vx",
    "pathogen_vy",
    "pathogen_vz",
    "distance",
    "attached",
    "engulfed",
    "digest_complete",
    "wrap_progress",
    "digestion_progress",
    "bacterium_scale",
    "collision_count",
    "attach_count",
    "detach_count",
    "engulf_count",
    "orbit_count",
    "mark_count",
    "spill_count",
    "reset_count",
    "trail_count",
    "enzyme_particle_count",
    "digest_particle_count",
    "stagnation_timer"
])
csv_file.flush()

start_real = time.time()
last_real = start_real
last_csv = start_real
last_flush = start_real
sim_time = 0.0
trail_timer = 0.0
last_action = {"mode": "boot", "immune_accel": vector(0, 0, 0), "pathogen_accel": vector(0, 0, 0)}

try:
    while True:
        rate(60)
        now = time.time()
        dt = min(0.05, max(0.001, now - last_real))
        last_real = now
        elapsed_real = now - start_real

        if not paused:
            frame += 1
            sim_time += dt
            t = sim_time

            if ai_controller.enabled and not force_human_override:
                action = ai_controller.choose_action(dt)
            else:
                action = {
                    "mode": "human_override" if force_human_override else "ai_off",
                    "immune_accel": vector(0, 0, 0),
                    "pathogen_accel": vector(0, 0, 0),
                    "attach": False,
                    "detach": False,
                    "mark": False,
                    "spill": False,
                    "wrap_intensity": 0.0,
                    "orbit_strength": 0.0,
                    "reset": False
                }

            human_immune, human_pathogen = get_human_action()
            if mag(human_immune) > 0:
                action["immune_accel"] += safe_norm(human_immune) * 7.0
                action["mode"] += "+human_cell"
            if mag(human_pathogen) > 0:
                action["pathogen_accel"] += safe_norm(human_pathogen) * 5.5
                action["mode"] += "+human_pathogen"

            if action.get("reset", False):
                reset_simulation("ai_loop")
                action = ai_controller.choose_action(dt)

            last_action = action

            to_pathogen = xz(pathogen_pos - cell_pos)
            distance = mag(to_pathogen)
            direction = safe_norm(to_pathogen)

            if action.get("mark", False):
                add_chem_mark(pathogen_pos, strong=(action["mode"].startswith("artistic")))
            trail_timer += dt
            if not engulfed and trail_timer > 0.18:
                trail_timer = 0
                add_chem_mark(pathogen_pos, strong=False)

            if action.get("spill", False):
                spill_enzyme(cell_pos + direction * CELL_BASE_RADIUS * 0.9, count=random.randint(1, 4), outward=direction)

            if not engulfed:
                cell_vel += action["immune_accel"] * dt
                cell_vel *= (1.0 - 0.84 * dt)
                if mag(cell_vel) > 3.2:
                    cell_vel = safe_norm(cell_vel) * 3.2
                cell_pos += cell_vel * dt
                cell_pos.y = CELL_Y

                if attached:
                    anchor = cell_pos + direction * (CELL_BASE_RADIUS * 0.78)
                    pathogen_pos = pathogen_pos * 0.86 + anchor * 0.14
                    pathogen_vel *= 0.55
                    wrap_progress += dt * (0.28 + 0.5 * action.get("wrap_intensity", 0.0))
                    wrap_count += 1
                else:
                    pathogen_vel += action["pathogen_accel"] * dt
                    pathogen_vel += vector(random.uniform(-0.35, 0.35), 0, random.uniform(-0.35, 0.35)) * dt
                    pathogen_vel *= (1.0 - 0.58 * dt)
                    if mag(pathogen_vel) > 2.55:
                        pathogen_vel = safe_norm(pathogen_vel) * 2.55
                    pathogen_pos += pathogen_vel * dt
                    pathogen_pos.y = PATHOGEN_Y

                cell_pos, cell_vel = clamp_to_dish(cell_pos, cell_vel, CELL_BASE_RADIUS + 0.4)
                pathogen_pos, pathogen_vel = clamp_to_dish(pathogen_pos, pathogen_vel, 1.0)

                if distance < CELL_BASE_RADIUS + 0.82:
                    collision_count += 1
                    wrap_progress += dt * (0.35 + action.get("wrap_intensity", 0.0) * 0.55)
                    if not attached and (action.get("attach", False) or wrap_progress > 0.34):
                        attached = True
                        attach_count += 1

                if attached and action.get("detach", False) and wrap_progress < 0.72:
                    attached = False
                    detach_count += 1
                    pathogen_vel += direction * 1.7

                if attached and wrap_progress > 1.0:
                    engulfed = True
                    attached = False
                    engulf_count += 1
                    pathogen_pos = cell_pos + vector(0.22, 0.03, -0.18)
                    pathogen_vel = vector(0, 0, 0)
                    create_digest_particles()
                    spill_enzyme(cell_pos + direction * CELL_BASE_RADIUS * 0.7, count=12, outward=direction)

                if abs(action.get("orbit_strength", 0.0)) > 0.1:
                    orbit_count += 1

            else:
                cell_vel += action["immune_accel"] * dt
                cell_vel *= (1.0 - 1.05 * dt)
                if mag(cell_vel) > 1.35:
                    cell_vel = safe_norm(cell_vel) * 1.35
                cell_pos += cell_vel * dt
                cell_pos.y = CELL_Y
                cell_pos, cell_vel = clamp_to_dish(cell_pos, cell_vel, CELL_BASE_RADIUS + 0.3)

                internal_offset = vector(
                    0.42 * math.sin(t * 1.4),
                    -0.10 + 0.08 * math.sin(t * 2.1),
                    0.42 * math.cos(t * 1.3)
                ) * (1.0 - min(1.0, digestion_progress) * 0.55)
                pathogen_pos = cell_pos + internal_offset
                pathogen_vel = vector(0, 0, 0)
                wrap_progress = min(1.25, wrap_progress + dt * 0.10)
                digestion_progress = min(1.0, digestion_progress + dt * (0.045 + 0.055 * min(1.0, len(digest_particles) / 34.0)))
                current_bac_scale = max(0.03, 1.0 - digestion_progress * 0.96)

                if digestion_progress >= 0.995:
                    digest_complete = True
                    completion_pause += dt
                    if completion_pause > 4.0:
                        reset_simulation("natural_loop")

            update_cell_visual(sim_time, action)
            update_bacterium_visual(sim_time)
            update_chem_trail(dt)
            update_enzyme_particles(dt)
            update_digest_particles(dt, sim_time)

            cell_label.pos = cell_pos + vector(0, 3.3, 0)
            pathogen_label.pos = pathogen_pos + vector(0, 1.1, 0)
            pathogen_label.visible = not digest_complete

        dist_now = mag(xz(pathogen_pos - cell_pos))
        status_label.text = (
            f"Round {round_index} | AI: {'ON' if ai_controller.enabled else 'OFF'} | "
            f"Mode: {ai_controller.mode} | Override: {'YES' if force_human_override else 'NO'} | "
            f"Paused: {'YES' if paused else 'NO'}\n"
            f"Distance: {dist_now:0.2f} | Attached: {attached} | Engulfed: {engulfed} | "
            f"Digesting: {digestion_progress * 100:0.0f}% | Trail marks: {mark_count} | Spills: {spill_count}"
        )

        if now - last_csv >= 0.25:
            last_csv = now
            cx, cy, cz = csv_vector(cell_pos)
            cvx, cvy, cvz = csv_vector(cell_vel)
            px, py, pz = csv_vector(pathogen_pos)
            pvx, pvy, pvz = csv_vector(pathogen_vel)
            csv_writer.writerow([
                _csv_run_id,
                frame,
                round(elapsed_real, 5),
                round(sim_time, 5),
                round_index,
                int(ai_controller.enabled),
                int(force_human_override),
                int(paused),
                ai_controller.mode,
                ai_controller.last_action_name,
                cx, cy, cz,
                cvx, cvy, cvz,
                px, py, pz,
                pvx, pvy, pvz,
                round(mag(xz(pathogen_pos - cell_pos)), 5),
                int(attached),
                int(engulfed),
                int(digest_complete),
                round(wrap_progress, 5),
                round(digestion_progress, 5),
                round(current_bac_scale, 5),
                collision_count,
                attach_count,
                detach_count,
                engulf_count,
                orbit_count,
                mark_count,
                spill_count,
                reset_count,
                len(chem_trail),
                len(enzyme_particles),
                len(digest_particles),
                round(ai_controller.stagnation_timer, 5)
            ])

        if now - last_flush >= 2.0:
            last_flush = now
            csv_file.flush()

        if elapsed_real >= CSV_RUN_SECONDS:
            status_label.text += f"\nCSV recording complete: saved run data"
            csv_file.flush()
            break

finally:
    csv_file.flush()
    csv_file.close()
    print(f"CSV recording complete: {CSV_OUTPUT_PATH}")
