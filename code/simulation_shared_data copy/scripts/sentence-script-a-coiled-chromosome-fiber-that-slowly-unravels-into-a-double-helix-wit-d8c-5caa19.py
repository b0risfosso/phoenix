from vpython import *
import csv
import os
import time
from datetime import datetime
import random
import math

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

os.makedirs(os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH)), exist_ok=True)

scene = canvas(
    title="AI-Controlled DNA Replication and Chromosome Unfolding",
    width=1280,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
    range=16
)
scene.forward = vector(-0.65, -0.35, -1)
scene.up = vector(0, 1, 0)
scene.ambient = color.gray(0.72)

distant_light(direction=vector(-0.4, -0.9, -0.3), color=vector(0.8, 0.82, 0.9))
distant_light(direction=vector(0.5, 0.7, 0.2), color=vector(0.65, 0.72, 0.8))

random.seed(7)

N = 82
DNA_LENGTH = 24.0
HALF_LENGTH = DNA_LENGTH / 2.0
HELIX_RADIUS = 0.58
HELIX_TWIST = 0.82
DT = 1.0 / 60.0

strand_a_color = vector(0.12, 0.36, 0.93)
strand_b_color = vector(0.58, 0.24, 0.88)
new_top_color = vector(0.0, 0.72, 0.95)
new_bottom_color = vector(0.0, 0.82, 0.45)
rung_color = vector(0.95, 0.74, 0.18)
coil_color = vector(0.78, 0.58, 0.34)
enzyme_color = vector(1.0, 0.48, 0.12)
enzyme_attached_color = vector(1.0, 0.2, 0.08)
fork_color = vector(1.0, 0.86, 0.12)

title_label = label(
    pos=vector(0, 8.7, 0),
    text="Chromosome fiber unfolding into a replicating DNA double helix",
    height=20,
    box=False,
    opacity=0,
    color=vector(0.1, 0.16, 0.28)
)

status_label = label(
    pos=vector(-11.8, 7.6, 0),
    text="",
    height=13,
    box=False,
    opacity=0,
    align="left",
    color=vector(0.12, 0.18, 0.25)
)

key_label = label(
    pos=vector(6.0, -8.2, 0),
    text="Keys: SPACE pause/resume | A AI on/off | R reset | +/- speed | E attach | D detach | C chaos | M mark | O orbit",
    height=11,
    box=False,
    opacity=0,
    color=vector(0.25, 0.28, 0.34)
)

# New label to explain the mesh behavior
mesh_label = label(
    pos=vector(0, 7.0, 0),
    text="Daughter helices mesh active",
    height=13,
    box=False,
    opacity=0.0,
    color=vector(0.9, 0.4, 0.1),
    align="center"
)

guide_axis = cylinder(
    pos=vector(-HALF_LENGTH, 0, 0),
    axis=vector(DNA_LENGTH, 0, 0),
    radius=0.018,
    color=vector(0.55, 0.62, 0.7),
    opacity=0.35
)

origin_marker_band = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.15,
    thickness=0.035,
    color=vector(1.0, 0.68, 0.22),
    opacity=0.55
)

left_boundary_band = ring(
    pos=vector(-HALF_LENGTH, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.0,
    thickness=0.025,
    color=vector(0.65, 0.75, 0.9),
    opacity=0.35
)

right_boundary_band = ring(
    pos=vector(HALF_LENGTH, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.0,
    thickness=0.025,
    color=vector(0.65, 0.75, 0.9),
    opacity=0.35
)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

def safe_norm(v):
    if mag(v) < 1e-8:
        return vector(0, 0, 0)
    return norm(v)

def set_cylinder_between(obj, a, b):
    obj.pos = a
    axis_vec = b - a
    if mag(axis_vec) < 1e-5:
        axis_vec = vector(0.0001, 0, 0)
    obj.axis = axis_vec

x_positions = []
helix_a_positions = []
helix_b_positions = []
daughter_top_a_positions = []
daughter_top_b_positions = []
daughter_bottom_a_positions = []
daughter_bottom_b_positions = []
coil_start_positions = []
coil_unfold_positions = []

for i in range(N):
    f = i / (N - 1)
    x = -HALF_LENGTH + DNA_LENGTH * f
    theta = i * HELIX_TWIST
    x_positions.append(x)

    a_pos = vector(x, HELIX_RADIUS * math.cos(theta), HELIX_RADIUS * math.sin(theta))
    b_pos = vector(x, -HELIX_RADIUS * math.cos(theta), -HELIX_RADIUS * math.sin(theta))
    helix_a_positions.append(a_pos)
    helix_b_positions.append(b_pos)

    daughter_top_a_positions.append(vector(x, 2.45 + HELIX_RADIUS * 0.8 * math.cos(theta), HELIX_RADIUS * 0.8 * math.sin(theta)))
    daughter_top_b_positions.append(vector(x, 2.45 - HELIX_RADIUS * 0.8 * math.cos(theta), -HELIX_RADIUS * 0.8 * math.sin(theta)))
    daughter_bottom_a_positions.append(vector(x, -2.45 + HELIX_RADIUS * 0.8 * math.cos(theta), HELIX_RADIUS * 0.8 * math.sin(theta)))
    daughter_bottom_b_positions.append(vector(x, -2.45 - HELIX_RADIUS * 0.8 * math.cos(theta), -HELIX_RADIUS * 0.8 * math.sin(theta)))

    coil_t = i * 0.46
    coil_rad = 3.4 + 0.55 * math.sin(i * 0.17)
    coil_pos = vector(
        coil_rad * math.cos(coil_t),
        -4.2 + 8.4 * f,
        coil_rad * math.sin(coil_t) + 0.45 * math.sin(i * 0.9)
    )
    coil_start_positions.append(coil_pos)
    coil_unfold_positions.append(vector(x, 0.0, 0.0))

parent_a_beads = []
parent_b_beads = []
parent_rungs = []
parent_a_backbone = []
parent_b_backbone = []

for i in range(N):
    parent_a_beads.append(sphere(pos=helix_a_positions[i], radius=0.12, color=strand_a_color, opacity=0.05))
    parent_b_beads.append(sphere(pos=helix_b_positions[i], radius=0.12, color=strand_b_color, opacity=0.05))
    parent_rungs.append(cylinder(
        pos=helix_a_positions[i],
        axis=helix_b_positions[i] - helix_a_positions[i],
        radius=0.025,
        color=rung_color,
        opacity=0.04
    ))

for i in range(N - 1):
    parent_a_backbone.append(cylinder(
        pos=helix_a_positions[i],
        axis=helix_a_positions[i + 1] - helix_a_positions[i],
        radius=0.036,
        color=strand_a_color,
        opacity=0.04
    ))
    parent_b_backbone.append(cylinder(
        pos=helix_b_positions[i],
        axis=helix_b_positions[i + 1] - helix_b_positions[i],
        radius=0.036,
        color=strand_b_color,
        opacity=0.04
    ))

coil_beads = []
coil_links = []
for i in range(N):
    coil_beads.append(sphere(
        pos=coil_start_positions[i],
        radius=0.16,
        color=coil_color,
        opacity=0.72
    ))
for i in range(N - 1):
    coil_links.append(cylinder(
        pos=coil_start_positions[i],
        axis=coil_start_positions[i + 1] - coil_start_positions[i],
        radius=0.07,
        color=coil_color,
        opacity=0.58
    ))

daughter_objects = []
daughter_top_a_beads = []
daughter_top_b_beads = []
daughter_bottom_a_beads = []
daughter_bottom_b_beads = []
daughter_top_rungs = []
daughter_bottom_rungs = []
daughter_backbones = []

for i in range(N):
    s1 = sphere(pos=daughter_top_a_positions[i], radius=0.105, color=strand_a_color, opacity=0.0)
    s2 = sphere(pos=daughter_top_b_positions[i], radius=0.105, color=new_top_color, opacity=0.0, emissive=True)
    s3 = sphere(pos=daughter_bottom_a_positions[i], radius=0.105, color=new_bottom_color, opacity=0.0, emissive=True)
    s4 = sphere(pos=daughter_bottom_b_positions[i], radius=0.105, color=strand_b_color, opacity=0.0)
    daughter_top_a_beads.append(s1)
    daughter_top_b_beads.append(s2)
    daughter_bottom_a_beads.append(s3)
    daughter_bottom_b_beads.append(s4)
    daughter_objects += [s1, s2, s3, s4]

    tr = cylinder(
        pos=daughter_top_a_positions[i],
        axis=daughter_top_b_positions[i] - daughter_top_a_positions[i],
        radius=0.018,
        color=vector(0.87, 0.89, 0.45),
        opacity=0.0
    )
    br = cylinder(
        pos=daughter_bottom_a_positions[i],
        axis=daughter_bottom_b_positions[i] - daughter_bottom_a_positions[i],
        radius=0.018,
        color=vector(0.87, 0.89, 0.45),
        opacity=0.0
    )
    daughter_top_rungs.append(tr)
    daughter_bottom_rungs.append(br)
    daughter_objects += [tr, br]

for i in range(N - 1):
    for pos_list, col in [
        (daughter_top_a_positions, strand_a_color),
        (daughter_top_b_positions, new_top_color),
        (daughter_bottom_a_positions, new_bottom_color),
        (daughter_bottom_b_positions, strand_b_color)
    ]:
        bb = cylinder(
            pos=pos_list[i],
            axis=pos_list[i + 1] - pos_list[i],
            radius=0.026,
            color=col,
            opacity=0.0
        )
        daughter_backbones.append((bb, pos_list, i))
        daughter_objects.append(bb)

right_fork_cone = cone(
    pos=vector(0.25, 0, 0),
    axis=vector(0.72, 0, 0),
    radius=0.42,
    color=fork_color,
    emissive=True,
    opacity=0.95
)

left_fork_cone = cone(
    pos=vector(-0.25, 0, 0),
    axis=vector(-0.72, 0, 0),
    radius=0.42,
    color=fork_color,
    emissive=True,
    opacity=0.95
)

right_fork_glow = sphere(pos=vector(0, 0, 0), radius=0.72, color=vector(1.0, 0.88, 0.2), opacity=0.18, emissive=True)
left_fork_glow = sphere(pos=vector(0, 0, 0), radius=0.72, color=vector(1.0, 0.88, 0.2), opacity=0.18, emissive=True)

replication_bubble_band = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=1.42,
    thickness=0.035,
    color=vector(1.0, 0.78, 0.16),
    opacity=0.28
)

class EnzymeMachine:
    def __init__(self, idx, kind):
        self.idx = idx
        self.kind = kind
        self.attached = False
        self.side = random.choice([-1, 1])
        self.orbiting = True
        self.angle = random.random() * 2 * math.pi
        self.orbit_radius = random.uniform(0.7, 1.25)
        self.phase_speed = random.uniform(1.4, 2.6)
        self.wander = vector(random.uniform(-7, 7), random.uniform(-5, 5), random.uniform(-5, 5))
        self.vel = vector(0, 0, 0)
        base_col = vector(1.0, 0.45, 0.13) if kind == "polymerase" else vector(0.93, 0.18, 0.15)
        if kind == "ligase":
            base_col = vector(0.2, 0.72, 1.0)
        self.body = sphere(pos=self.wander, radius=0.27, color=base_col, emissive=True, opacity=0.96, make_trail=True, retain=42, trail_radius=0.016)
        self.clamp_band = ring(pos=self.wander, axis=vector(1, 0, 0), radius=0.38, thickness=0.035, color=vector(1, 0.88, 0.25), opacity=0.72)
        self.tag = label(pos=self.wander + vector(0, 0.55, 0), text=kind[0].upper(), height=8, box=False, opacity=0, color=vector(0.16, 0.17, 0.22))

    def attach(self, side=None):
        global attachment_count
        if side is not None:
            self.side = side
        if not self.attached:
            attachment_count += 1
        self.attached = True
        self.orbiting = True
        self.body.color = enzyme_attached_color if self.kind != "ligase" else vector(0.0, 0.62, 1.0)

    def detach(self):
        global detachment_count
        if self.attached:
            detachment_count += 1
        self.attached = False
        self.vel = vector(random.uniform(-0.8, 0.8), random.uniform(-0.7, 0.7), random.uniform(-0.7, 0.7))
        self.body.color = enzyme_color if self.kind != "ligase" else vector(0.2, 0.72, 1.0)

    def update(self, dt, left_x, right_x, global_t, chaos=0.0):
        target_x = right_x if self.side > 0 else left_x
        target = vector(target_x, 0, 0)

        if self.attached:
            self.angle += dt * self.phase_speed * (1.0 + 0.5 * chaos)
            if self.kind == "polymerase":
                behind = -0.48 * self.side
                offset_y = 0.78 * math.cos(self.angle)
                offset_z = 0.78 * math.sin(self.angle)
            elif self.kind == "helicase":
                behind = 0.08 * self.side
                offset_y = 0.56 * math.cos(self.angle * 1.35)
                offset_z = 0.56 * math.sin(self.angle * 1.35)
            else:
                behind = -0.92 * self.side
                offset_y = 1.05 * math.cos(self.angle * 0.7)
                offset_z = 1.05 * math.sin(self.angle * 0.7)

            desired = target + vector(behind, offset_y, offset_z)
            desired += chaos * vector(
                0.16 * math.sin(global_t * 7 + self.idx),
                0.12 * math.cos(global_t * 6.1 + self.idx),
                0.12 * math.sin(global_t * 5.3 + self.idx * 0.3)
            )
            self.body.pos = self.body.pos + (desired - self.body.pos) * clamp(dt * 8.0, 0, 1)
        else:
            self.angle += dt * (0.8 + self.phase_speed * 0.25)
            anchor = vector(0, 0, 0)
            lazy_orbit = vector(
                7.2 * math.cos(self.angle * 0.35 + self.idx),
                4.6 * math.sin(self.angle * 0.21 + self.idx * 0.6),
                5.3 * math.sin(self.angle * 0.29 + self.idx)
            )
            desired = anchor + lazy_orbit
            self.vel += (desired - self.body.pos) * dt * 0.18
            self.vel *= 0.985
            self.body.pos += self.vel * dt * 7.5

        self.clamp_band.pos = self.body.pos
        self.clamp_band.axis = vector(1, 0.25 * math.sin(self.angle), 0.25 * math.cos(self.angle))
        self.tag.pos = self.body.pos + vector(0, 0.55, 0)

enzymes = []
for k in range(10):
    kind = "polymerase"
    if k in [0, 1]:
        kind = "helicase"
    elif k in [8, 9]:
        kind = "ligase"
    enzymes.append(EnzymeMachine(k, kind))

class ParticleUnit:
    def __init__(self, idx):
        self.idx = idx
        self.body = sphere(pos=vector(0, 0, 0), radius=0.055, color=color.white, opacity=0.0, emissive=True)
        self.active = False
        self.vel = vector(0, 0, 0)
        self.life = 0.0
        self.target = vector(0, 0, 0)

    def spawn(self, source, target, col):
        self.active = True
        self.body.opacity = 0.95
        self.body.color = col
        self.body.pos = source + vector(random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25))
        self.target = target
        self.vel = vector(random.uniform(-0.5, 0.5), random.uniform(-0.6, 0.6), random.uniform(-0.6, 0.6))
        self.life = random.uniform(1.1, 2.4)

    def update(self, dt):
        global transfer_count, collision_count
        if not self.active:
            return
        toward = self.target - self.body.pos
        self.vel += safe_norm(toward) * dt * 4.5
        self.vel *= 0.965
        self.body.pos += self.vel * dt * 4.2
        self.life -= dt

        for enz in enzymes:
            if mag(self.body.pos - enz.body.pos) < 0.33:
                collision_count += 1
                self.vel = self.vel + safe_norm(self.body.pos - enz.body.pos) * 0.7

        if mag(toward) < 0.18 or self.life <= 0:
            if mag(toward) < 0.25:
                transfer_count += 1
            self.active = False
            self.body.opacity = 0.0
            return

        self.body.opacity = clamp(self.life / 1.3, 0.0, 0.95)

particles = [ParticleUnit(i) for i in range(90)]

marker_bands = []
for i in range(18):
    marker_bands.append(ring(
        pos=vector(0, 0, 0),
        axis=vector(1, 0, 0),
        radius=1.55,
        thickness=0.033,
        color=vector(1.0, 0.36, 0.16),
        opacity=0.0
    ))

# --- New behavior: Daughter helices mesh ---

# Mesh connection objects between daughter helices to create dense mesh
# We'll create a set of thin cylinders connecting daughter top and bottom beads across strands and between strands
mesh_connections = []

# Parameters controlling the mesh density and appearance
MESH_MAX_DISTANCE = 1.2  # max distance to connect beads
MESH_OPACITY_BASE = 0.12
MESH_OPACITY_MAX = 0.35
MESH_RADIUS = 0.009

# We'll precompute possible pairs for mesh connections to avoid runtime overhead
# Connections will be between daughter_top_a <-> daughter_top_b, daughter_bottom_a <-> daughter_bottom_b,
# and cross connections daughter_top_a <-> daughter_bottom_a, daughter_top_b <-> daughter_bottom_b
# Also some cross-strand connections daughter_top_a <-> daughter_bottom_b and daughter_top_b <-> daughter_bottom_a
# but limited to close indices to avoid clutter.

# To keep it performant and visually meaningful, only connect beads within +/- 3 indices

def create_mesh_connection(pos1, pos2, col):
    c = cylinder(pos=pos1, axis=pos2 - pos1, radius=MESH_RADIUS, color=col, opacity=0.0)
    return c

# Store tuples: (cylinder_obj, index1, index2, strand_type)
# strand_type: 'top_a_b', 'bottom_a_b', 'top_a_bottom_a', 'top_b_bottom_b', 'top_a_bottom_b', 'top_b_bottom_a'
mesh_connection_data = []

# Colors for mesh connections (slightly transparent yellow-greenish)
mesh_color = vector(0.65, 0.85, 0.45)

for i in range(N):
    for j in range(max(0, i - 3), min(N, i + 4)):
        # top_a <-> top_b
        c1 = create_mesh_connection(daughter_top_a_positions[i], daughter_top_b_positions[j], mesh_color)
        mesh_connection_data.append((c1, i, j, 'top_a_b'))
        # bottom_a <-> bottom_b
        c2 = create_mesh_connection(daughter_bottom_a_positions[i], daughter_bottom_b_positions[j], mesh_color)
        mesh_connection_data.append((c2, i, j, 'bottom_a_b'))
        # top_a <-> bottom_a
        c3 = create_mesh_connection(daughter_top_a_positions[i], daughter_bottom_a_positions[j], mesh_color)
        mesh_connection_data.append((c3, i, j, 'top_a_bottom_a'))
        # top_b <-> bottom_b
        c4 = create_mesh_connection(daughter_top_b_positions[i], daughter_bottom_b_positions[j], mesh_color)
        mesh_connection_data.append((c4, i, j, 'top_b_bottom_b'))
        # top_a <-> bottom_b (cross strand)
        c5 = create_mesh_connection(daughter_top_a_positions[i], daughter_bottom_b_positions[j], mesh_color)
        mesh_connection_data.append((c5, i, j, 'top_a_bottom_b'))
        # top_b <-> bottom_a (cross strand)
        c6 = create_mesh_connection(daughter_top_b_positions[i], daughter_bottom_a_positions[j], mesh_color)
        mesh_connection_data.append((c6, i, j, 'top_b_bottom_a'))

# New state variables for mesh dynamic behavior
mesh_dynamic_phase = 0.0
mesh_dynamic_speed = 1.5  # speed of mesh dynamic shifting
mesh_dynamic_amplitude = 0.18  # max positional oscillation amplitude for mesh connections

# --- End new behavior ---

paused = False
human_override_until = 0.0
unfold_progress = 0.015
fork_distance = 0.0
target_replication_speed = 0.72
replication_speed = 0.72
target_unfold_speed = 0.115
unfold_speed = 0.115
chaos_level = 0.0
orbit_emphasis = 1.0
attachment_count = 0
detachment_count = 0
collision_count = 0
mark_count = 0
spill_count = 0
transfer_count = 0
round_count = 1
completion_hold = 0.0
last_progress_value = 0.0
stagnation_clock = 0.0
simulation_mode_note = "initializing"
last_particle_spawn = 0.0
last_marker_time = 0.0

def get_fork_positions():
    left_x = -fork_distance
    right_x = fork_distance
    return left_x, right_x

def source_to_target_for_particle(side=None):
    if side is None:
        side = random.choice([-1, 1])
    x = side * fork_distance
    source = vector(x, 0, 0)
    if random.random() < 0.5:
        target = vector(x - side * random.uniform(0.15, 1.25), 2.45 + random.uniform(-0.55, 0.55), random.uniform(-0.55, 0.55))
        col = new_top_color
    else:
        target = vector(x - side * random.uniform(0.15, 1.25), -2.45 + random.uniform(-0.55, 0.55), random.uniform(-0.55, 0.55))
        col = new_bottom_color
    return source, target, col

def spawn_particle_burst(count=6, side=None):
    global spill_count
    spill_count += count
    for _ in range(count):
        for p in particles:
            if not p.active:
                source, target, col = source_to_target_for_particle(side)
                p.spawn(source, target, col)
                break

def activate_marker(x=None, col=None):
    global mark_count
    if x is None:
        x = random.uniform(-fork_distance, fork_distance) if fork_distance > 0.1 else 0
    if col is None:
        col = vector(1.0, random.uniform(0.25, 0.75), random.uniform(0.12, 0.35))
    band = marker_bands[mark_count % len(marker_bands)]
    band.pos = vector(x, 0, 0)
    band.radius = random.uniform(1.1, 1.9)
    band.color = col
    band.opacity = 0.65
    mark_count += 1

def attach_one(side=None):
    free = [e for e in enzymes if not e.attached]
    if not free:
        return
    random.choice(free).attach(side if side is not None else random.choice([-1, 1]))

def detach_one():
    attached = [e for e in enzymes if e.attached]
    if not attached:
        return
    random.choice(attached).detach()

def attach_balanced_pair():
    left_candidates = [e for e in enzymes if not e.attached]
    if left_candidates:
        left_candidates[0].attach(-1)
    right_candidates = [e for e in enzymes if not e.attached]
    if right_candidates:
        right_candidates[0].attach(1)

def reset_simulation(ritual=False):
    global unfold_progress, fork_distance, replication_speed, unfold_speed
    global target_replication_speed, target_unfold_speed, chaos_level, orbit_emphasis
    global completion_hold, stagnation_clock, last_progress_value, round_count
    global simulation_mode_note, mesh_dynamic_phase

    unfold_progress = 0.015
    fork_distance = 0.0
    target_replication_speed = 0.68 + random.uniform(-0.08, 0.18)
    target_unfold_speed = 0.105 + random.uniform(-0.018, 0.028)
    replication_speed = target_replication_speed
    unfold_speed = target_unfold_speed
    chaos_level = 0.0
    orbit_emphasis = 1.0
    completion_hold = 0.0
    stagnation_clock = 0.0
    last_progress_value = 0.0
    round_count += 1
    simulation_mode_note = "new round"
    mesh_dynamic_phase = 0.0  # reset mesh dynamic phase

    for obj in daughter_objects:
        obj.opacity = 0.0

    for p in particles:
        p.active = False
        p.body.opacity = 0.0

    for i, band in enumerate(marker_bands):
        band.opacity = 0.0

    for e in enzymes:
        e.detach()
        e.body.clear_trail()
        e.body.pos = vector(random.uniform(-7, 7), random.uniform(-5, 5), random.uniform(-5, 5))
        e.side = random.choice([-1, 1])
        if ritual and random.random() < 0.65:
            e.attach(e.side)

    for _ in range(2):
        attach_balanced_pair()

    # Reset mesh connections opacity to zero on reset
    for c, _, _, _ in mesh_connection_data:
        c.opacity = 0.0

class AIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "careful",
            "constructive",
            "curious",
            "ritual",
            "artistic",
            "chaotic",
            "destructive",
            "repair"
        ]
        self.mode = "careful"
        self.mode_timer = 0.0
        self.next_switch = 7.0
        self.action_timer = 0.0
        self.last_progress = 0.0
        self.local_stagnation = 0.0
        self.reset_cooldown = 0.0

    def read_state(self):
        active_particles = sum(1 for p in particles if p.active)
        attached = sum(1 for e in enzymes if e.attached)
        complete = fork_distance >= HALF_LENGTH - 0.04 and unfold_progress >= 0.98
        progress = 0.5 * unfold_progress + 0.5 * (fork_distance / HALF_LENGTH)
        return {
            "unfold": unfold_progress,
            "fork_distance": fork_distance,
            "progress": progress,
            "attached": attached,
            "active_particles": active_particles,
            "complete": complete,
            "paused": paused,
            "chaos": chaos_level
        }

    def choose_new_mode(self, state, forced=None):
        if forced:
            self.mode = forced
        elif state["complete"]:
            self.mode = "ritual"
        elif self.local_stagnation > 5.0:
            self.mode = "repair"
        elif state["attached"] < 2:
            self.mode = "constructive"
        else:
            options = list(self.modes)
            if self.mode in options and len(options) > 1:
                options.remove(self.mode)
            if state["active_particles"] > 55 and "chaotic" in options:
                options.remove("chaotic")
            if state["fork_distance"] < 1.5 and "destructive" in options:
                options.remove("destructive")
            self.mode = random.choice(options)
        self.mode_timer = 0.0
        self.next_switch = random.uniform(5.5, 12.5)

    def step(self, dt, now):
        global target_replication_speed, target_unfold_speed, chaos_level, orbit_emphasis
        global paused, completion_hold, simulation_mode_note

        if not self.enabled:
            simulation_mode_note = "human/manual"
            chaos_level *= 0.97
            return

        state = self.read_state()
        progress_delta = abs(state["progress"] - self.last_progress)
        if progress_delta < 0.00035 and not paused:
            self.local_stagnation += dt
        else:
            self.local_stagnation = max(0.0, self.local_stagnation - dt * 0.75)
        self.last_progress = state["progress"]

        if now < human_override_until:
            simulation_mode_note = "human override"
            chaos_level *= 0.985
            return

        self.mode_timer += dt
        self.action_timer += dt
        self.reset_cooldown = max(0.0, self.reset_cooldown - dt)

        if state["complete"]:
            completion_hold += dt
            if completion_hold > 4.2 and self.reset_cooldown <= 0:
                self.choose_new_mode(state, forced=random.choice(["constructive", "artistic", "careful"]))
                reset_simulation(ritual=True)
                self.reset_cooldown = 6.0
                completion_hold = 0.0
                return
        else:
            completion_hold = 0.0

        if self.mode_timer > self.next_switch or self.local_stagnation > 6.5:
            self.choose_new_mode(state)

        simulation_mode_note = self.mode

        if self.mode == "careful":
            target_replication_speed = 0.48 + 0.12 * math.sin(now * 0.6)
            target_unfold_speed = 0.075
            chaos_level *= 0.94
            orbit_emphasis = 0.75
            if self.action_timer > 1.55:
                attach_one(random.choice([-1, 1]))
                if random.random() < 0.5:
                    spawn_particle_burst(2, random.choice([-1, 1]))
                self.action_timer = 0.0

        elif self.mode == "constructive":
            target_replication_speed = 0.86
            target_unfold_speed = 0.135
            chaos_level *= 0.96
            orbit_emphasis = 1.1
            if self.action_timer > 0.85:
                attach_one(random.choice([-1, 1]))
                spawn_particle_burst(4, random.choice([-1, 1]))
                self.action_timer = 0.0

        elif self.mode == "curious":
            target_replication_speed = 0.62 + 0.28 * abs(math.sin(now * 0.47))
            target_unfold_speed = 0.105 + 0.05 * math.sin(now * 0.31)
            chaos_level = chaos_level * 0.96 + 0.08
            orbit_emphasis = 1.75
            if self.action_timer > 1.15:
                side = 1 if math.sin(now * 1.1) > 0 else -1
                attach_one(side)
                spawn_particle_burst(3, side)
                self.action_timer = 0.0

        elif self.mode == "ritual":
            target_replication_speed = 0.38 + 0.16 * math.sin(now * 0.9) ** 2
            target_unfold_speed = 0.075
            chaos_level *= 0.9
            orbit_emphasis = 2.35
            if self.action_timer > 1.0:
                if fork_distance > 0.2:
                    x = math.sin(now * 1.2) * fork_distance
                    activate_marker(x, vector(1.0, 0.58, 0.14))
                attach_balanced_pair()
                spawn_particle_burst(2, None)
                self.action_timer = 0.0

        elif self.mode == "artistic":
            target_replication_speed = 0.66
            target_unfold_speed = 0.12
            chaos_level = chaos_level * 0.95 + 0.12
            orbit_emphasis = 1.6
            if self.action_timer > 0.62:
                spawn_particle_burst(6, random.choice([-1, 1]))
                if random.random() < 0.55:
                    activate_marker(None, vector(random.uniform(0.4, 1.0), random.uniform(0.2, 0.8), random.uniform(0.5, 1.0)))
                self.action_timer = 0.0

        elif self.mode == "chaotic":
            target_replication_speed = 0.95 + 0.45 * math.sin(now * 2.7)
            target_unfold_speed = 0.16 + 0.05 * math.sin(now * 3.1)
            chaos_level = chaos_level * 0.88 + 0.45
            orbit_emphasis = 2.0
            if self.action_timer > 0.42:
                if random.random() < 0.38:
                    detach_one()
                else:
                    attach_one(random.choice([-1, 1]))
                spawn_particle_burst(random.randint(5, 10), random.choice([-1, 1]))
                self.action_timer = 0.0

        elif self.mode == "destructive":
            target_replication_speed = 0.24
            target_unfold_speed = 0.04
            chaos_level = chaos_level * 0.9 + 0.32
            orbit_emphasis = 2.75
            if self.action_timer > 0.75:
                detach_one()
                spawn_particle_burst(5, None)
                self.action_timer = 0.0
            if self.mode_timer > 4.2:
                self.choose_new_mode(state, forced="repair")

        elif self.mode == "repair":
            target_replication_speed = 0.72
            target_unfold_speed = 0.13
            chaos_level *= 0.86
            orbit_emphasis = 0.9
            if self.action_timer > 0.65:
                attach_balanced_pair()
                spawn_particle_burst(5, random.choice([-1, 1]))
                self.action_timer = 0.0
            if self.local_stagnation > 9.0 and self.reset_cooldown <= 0:
                reset_simulation(ritual=True)
                self.local_stagnation = 0.0
                self.reset_cooldown = 6.0

ai = AIController()

def keyboard_control(evt):
    global paused, human_override_until, target_replication_speed, target_unfold_speed, chaos_level
    key = evt.key.lower()
    human_override_until = time.monotonic() + 5.0

    if key == " ":
        paused = not paused
    elif key == "a":
        ai.enabled = not ai.enabled
    elif key == "r":
        reset_simulation(ritual=True)
    elif key in ["+", "="]:
        target_replication_speed = min(2.1, target_replication_speed + 0.18)
        target_unfold_speed = min(0.34, target_unfold_speed + 0.03)
    elif key in ["-", "_"]:
        target_replication_speed = max(0.05, target_replication_speed - 0.18)
        target_unfold_speed = max(0.01, target_unfold_speed - 0.03)
    elif key == "e":
        attach_one(random.choice([-1, 1]))
    elif key == "d":
        detach_one()
    elif key == "c":
        chaos_level = min(1.0, chaos_level + 0.35)
        spawn_particle_burst(16, None)
    elif key == "m":
        activate_marker(None)
    elif key == "o":
        for e in enzymes:
            e.orbiting = not e.orbiting
        chaos_level = min(1.0, chaos_level + 0.12)

scene.bind("keydown", keyboard_control)

def update_parent_and_coil(dt, now):
    reveal_softness = 0.08
    for i in range(N):
        x = x_positions[i]
        loc = abs(x) / HALF_LENGTH
        reveal = smoothstep((unfold_progress - loc + reveal_softness) / (2 * reveal_softness))
        parent_op = 0.025 + 0.87 * reveal

        parent_a_beads[i].opacity = parent_op
        parent_b_beads[i].opacity = parent_op
        parent_rungs[i].opacity = 0.02 + 0.52 * reveal

        separation = smoothstep((fork_distance - abs(x) + 0.22) / 0.55) * 0.36
        wobble = chaos_level * 0.035 * vector(0, math.sin(now * 5 + i), math.cos(now * 4.6 + i * 0.2))
        parent_a_beads[i].pos = helix_a_positions[i] + vector(0, separation, 0) + wobble
        parent_b_beads[i].pos = helix_b_positions[i] + vector(0, -separation, 0) - wobble
        set_cylinder_between(parent_rungs[i], parent_a_beads[i].pos, parent_b_beads[i].pos)

        uncoil_amount = smoothstep((unfold_progress - loc + 0.18) / 0.36)
        coil_pos = coil_start_positions[i] * (1 - uncoil_amount) + coil_unfold_positions[i] * uncoil_amount
        coil_pos += chaos_level * 0.11 * vector(math.sin(now * 4.2 + i), math.cos(now * 3.8 + i * 0.5), math.sin(now * 3.2 + i * 0.25))
        coil_beads[i].pos = coil_pos
        coil_beads[i].opacity = clamp(0.72 * (1 - uncoil_amount) + 0.08 * (1 - unfold_progress), 0.0, 0.72)
        coil_beads[i].radius = 0.12 + 0.06 * (1 - uncoil_amount)

    for i in range(N - 1):
        parent_a_backbone[i].opacity = min(parent_a_beads[i].opacity, parent_a_beads[i + 1].opacity) * 0.82
        parent_b_backbone[i].opacity = min(parent_b_beads[i].opacity, parent_b_beads[i + 1].opacity) * 0.82
        set_cylinder_between(parent_a_backbone[i], parent_a_beads[i].pos, parent_a_beads[i + 1].pos)
        set_cylinder_between(parent_b_backbone[i], parent_b_beads[i].pos, parent_b_beads[i + 1].pos)

        set_cylinder_between(coil_links[i], coil_beads[i].pos, coil_beads[i + 1].pos)
        coil_links[i].opacity = min(coil_beads[i].opacity, coil_beads[i + 1].opacity) * 0.88

def update_daughters(now):
    shimmer = 0.07 + 0.05 * math.sin(now * 4.0)
    for i in range(N):
        x = x_positions[i]
        copied = smoothstep((fork_distance - abs(x) + 0.18) / 0.55)
        glow = copied * (0.76 + shimmer)

        daughter_top_a_beads[i].opacity = glow * 0.76
        daughter_top_b_beads[i].opacity = glow
        daughter_bottom_a_beads[i].opacity = glow
        daughter_bottom_b_beads[i].opacity = glow * 0.76
        daughter_top_rungs[i].opacity = glow * 0.45
        daughter_bottom_rungs[i].opacity = glow * 0.45

        wave = chaos_level * 0.045 * vector(0, math.sin(now * 3.6 + i), math.cos(now * 3.4 + i))
        daughter_top_a_beads[i].pos = daughter_top_a_positions[i] + wave
        daughter_top_b_beads[i].pos = daughter_top_b_positions[i] - wave
        daughter_bottom_a_beads[i].pos = daughter_bottom_a_positions[i] + vector(wave.x, -wave.y, wave.z)
        daughter_bottom_b_beads[i].pos = daughter_bottom_b_positions[i] - vector(wave.x, -wave.y, wave.z)

        set_cylinder_between(daughter_top_rungs[i], daughter_top_a_beads[i].pos, daughter_top_b_beads[i].pos)
        set_cylinder_between(daughter_bottom_rungs[i], daughter_bottom_a_beads[i].pos, daughter_bottom_b_beads[i].pos)

    for bb, pos_list, i in daughter_backbones:
        x1 = x_positions[i]
        x2 = x_positions[i + 1]
        copied = min(
            smoothstep((fork_distance - abs(x1) + 0.18) / 0.55),
            smoothstep((fork_distance - abs(x2) + 0.18) / 0.55)
        )
        bb.opacity = copied * 0.72
        set_cylinder_between(bb, pos_list[i], pos_list[i + 1])

def update_mesh_connections(dt, now):
    global mesh_dynamic_phase
    # Update the dynamic phase for oscillation
    mesh_dynamic_phase += dt * mesh_dynamic_speed
    mesh_dynamic_phase %= 2 * math.pi

    # Update the opacity and positions of mesh connections to simulate branching and overlapping mesh
    for c, i1, i2, stype in mesh_connection_data:
        # Compute distance between the two beads (current positions)
        if stype == 'top_a_b':
            pos1 = daughter_top_a_beads[i1].pos
            pos2 = daughter_top_b_beads[i2].pos
        elif stype == 'bottom_a_b':
            pos1 = daughter_bottom_a_beads[i1].pos
            pos2 = daughter_bottom_b_beads[i2].pos
        elif stype == 'top_a_bottom_a':
            pos1 = daughter_top_a_beads[i1].pos
            pos2 = daughter_bottom_a_beads[i2].pos
        elif stype == 'top_b_bottom_b':
            pos1 = daughter_top_b_beads[i1].pos
            pos2 = daughter_bottom_b_beads[i2].pos
        elif stype == 'top_a_bottom_b':
            pos1 = daughter_top_a_beads[i1].pos
            pos2 = daughter_bottom_b_beads[i2].pos
        elif stype == 'top_b_bottom_a':
            pos1 = daughter_top_b_beads[i1].pos
            pos2 = daughter_bottom_a_beads[i2].pos
        else:
            # Unknown type, skip
            continue

        dist = mag(pos2 - pos1)
        if dist > MESH_MAX_DISTANCE:
            # Too far, hide connection
            c.opacity = 0.0
            continue

        # Opacity depends on distance and fork_distance progress (mesh grows as fork advances)
        base_opacity = MESH_OPACITY_BASE + (MESH_OPACITY_MAX - MESH_OPACITY_BASE) * (1 - dist / MESH_MAX_DISTANCE)
        # Also modulate opacity with unfold_progress and fork_distance for progressive mesh appearance
        progress_factor = clamp((fork_distance / HALF_LENGTH) * 1.5, 0.0, 1.0)
        opacity = base_opacity * progress_factor

        # Add dynamic flickering to opacity for lively effect
        flicker = 0.15 * math.sin(mesh_dynamic_phase * 3 + (i1 + i2) * 0.7)
        opacity = clamp(opacity + flicker, 0.0, MESH_OPACITY_MAX)

        c.opacity = opacity

        # Dynamic oscillation of the connection axis to simulate shifting mesh shape
        midpoint = (pos1 + pos2) * 0.5
        axis_vec = pos2 - pos1
        # Perpendicular vector for oscillation (arbitrary but consistent)
        perp = vector(-axis_vec.y, axis_vec.x, 0)
        if mag(perp) < 1e-5:
            perp = vector(0, 0, 1)
        perp = norm(perp)
        oscillation = perp * math.sin(mesh_dynamic_phase * 4 + (i1 - i2) * 1.3) * mesh_dynamic_amplitude * (1 - dist / MESH_MAX_DISTANCE)

        # Update cylinder position and axis with oscillation
        c.pos = pos1 + oscillation
        c.axis = (pos2 + oscillation) - c.pos
        c.radius = MESH_RADIUS * (0.7 + 0.6 * (opacity / MESH_OPACITY_MAX))  # radius modulated by opacity for depth effect

# --- End mesh update ---

def update_forks(now):
    left_x, right_x = get_fork_positions()
    right_fork_cone.pos = vector(right_x - 0.36, 0, 0)
    right_fork_cone.axis = vector(0.72, 0, 0)
    left_fork_cone.pos = vector(left_x + 0.36, 0, 0)
    left_fork_cone.axis = vector(-0.72, 0, 0)

    pulse = 0.18 + 0.08 * math.sin(now * 7.0)
    right_fork_glow.pos = vector(right_x, 0, 0)
    left_fork_glow.pos = vector(left_x, 0, 0)
    right_fork_glow.opacity = pulse
    left_fork_glow.opacity = pulse

    replication_bubble_band.pos = vector(0, 0, 0)
    replication_bubble_band.radius = 1.18 + 0.65 * smoothstep(fork_distance / HALF_LENGTH)
    replication_bubble_band.opacity = 0.18 + 0.22 * math.sin(now * 2.3) ** 2
    replication_bubble_band.thickness = 0.025 + 0.018 * smoothstep(fork_distance / HALF_LENGTH)

def update_markers(dt, now):
    for i, band in enumerate(marker_bands):
        if band.opacity > 0:
            band.opacity = max(0.0, band.opacity - dt * 0.045)
            band.radius += dt * 0.025 * math.sin(now + i)
            band.axis = vector(1, 0.08 * math.sin(now * 0.5 + i), 0.08 * math.cos(now * 0.45 + i))

def update_status(elapsed):
    status_label.text = (
        f"Round: {round_count}\n"
        f"AI: {'ON' if ai.enabled else 'OFF'} | mode: {simulation_mode_note}\n"
        f"Paused: {paused}\n"
        f"Unfolded: {100 * unfold_progress:5.1f}%\n"
        f"Fork distance: {fork_distance:4.2f} / {HALF_LENGTH:4.2f}\n"
        f"Replication speed: {replication_speed:4.2f}\n"
        f"Attached enzymes: {sum(1 for e in enzymes if e.attached)} / {len(enzymes)}\n"
        f"Particles active: {sum(1 for p in particles if p.active)}\n"
        f"Attach/detach: {attachment_count}/{detachment_count}\n"
        f"Collisions/transfers/marks/spills: {collision_count}/{transfer_count}/{mark_count}/{spill_count}\n"
        f"Daughter mesh connections active: {sum(1 for c, _, _, _ in mesh_connection_data if c.opacity > 0):d}\n"
        f"CSV elapsed: {elapsed:5.1f}s"
    )
    # Update mesh label opacity to show when mesh is visible
    mesh_label.opacity = clamp((fork_distance / HALF_LENGTH) * 1.5, 0.0, 1.0)

csv_file = None
csv_writer = None
CSV_ACTIVE = False

try:
    csv_file = open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "run_id",
        "frame",
        "elapsed_seconds",
        "round",
        "paused",
        "ai_enabled",
        "ai_mode",
        "simulation_mode_note",
        "unfold_progress",
        "fork_distance",
        "left_fork_x",
        "left_fork_y",
        "left_fork_z",
        "right_fork_x",
        "right_fork_y",
        "right_fork_z",
        "replication_speed",
        "unfold_speed",
        "target_replication_speed",
        "target_unfold_speed",
        "chaos_level",
        "attached_enzyme_count",
        "active_particle_count",
        "attachment_count",
        "detachment_count",
        "collision_count",
        "transfer_count",
        "mark_count",
        "spill_count",
        "enzyme0_x",
        "enzyme0_y",
        "enzyme0_z",
        "enzyme0_attached",
        "enzyme1_x",
        "enzyme1_y",
        "enzyme1_z",
        "enzyme1_attached",
        "completion_hold",
        "ai_stagnation_seconds"
    ])
    csv_file.flush()
    CSV_ACTIVE = True
except Exception as exc:
    CSV_ACTIVE = False
    print("CSV logging disabled:", exc)

reset_simulation(ritual=True)
round_count = 1

frame = 0
start_time = time.monotonic()
last_csv_log = 0.0
last_csv_flush = 0.0

try:
    while True:
        rate(60)
        now = time.monotonic()
        elapsed = now - start_time
        frame += 1

        ai.step(DT, now)

        if not paused:
            replication_speed += (target_replication_speed - replication_speed) * 0.045
            unfold_speed += (target_unfold_speed - unfold_speed) * 0.045

            unfold_progress = clamp(unfold_progress + unfold_speed * DT, 0.0, 1.0)
            allowed_fork = unfold_progress * HALF_LENGTH
            if unfold_progress > 0.04:
                fork_distance = clamp(fork_distance + max(0.0, replication_speed) * DT, 0.0, allowed_fork)
            fork_distance = clamp(fork_distance, 0.0, HALF_LENGTH)
            chaos_level = clamp(chaos_level * 0.995, 0.0, 1.0)

            if now - last_particle_spawn > max(0.12, 0.55 - chaos_level * 0.38):
                if fork_distance > 0.1 and random.random() < (0.45 + chaos_level * 0.42):
                    spawn_particle_burst(1 + int(chaos_level * 4), random.choice([-1, 1]))
                last_particle_spawn = now

            if fork_distance >= HALF_LENGTH - 0.05:
                unfold_progress = min(1.0, unfold_progress + DT * 0.08)

        left_x, right_x = get_fork_positions()

        update_parent_and_coil(DT, now)
        update_daughters(now)
        update_forks(now)
        update_markers(DT, now)

        # Update the new mesh connections to simulate branching and overlapping mesh
        if not paused:
            update_mesh_connections(DT, now)

        for e in enzymes:
            e.phase_speed *= 0.995
            e.phase_speed += 0.005 * (1.4 + orbit_emphasis * random.uniform(0.4, 1.4))
            e.update(DT, left_x, right_x, now, chaos_level)

        for p in particles:
            p.update(DT)

        progress_value = 0.5 * unfold_progress + 0.5 * (fork_distance / HALF_LENGTH)
        if abs(progress_value - last_progress_value) < 0.0002 and not paused:
            stagnation_clock += DT
        else:
            stagnation_clock = max(0.0, stagnation_clock - DT)
        last_progress_value = progress_value

        update_status(elapsed)

        if CSV_ACTIVE and elapsed - last_csv_log >= 0.25:
            e0 = enzymes[0]
            e1 = enzymes[1]
            csv_writer.writerow([
                _csv_run_id,
                frame,
                f"{elapsed:.3f}",
                round_count,
                int(paused),
                int(ai.enabled),
                ai.mode,
                simulation_mode_note,
                f"{unfold_progress:.5f}",
                f"{fork_distance:.5f}",
                f"{left_x:.5f}",
                "0.00000",
                "0.00000",
                f"{right_x:.5f}",
                "0.00000",
                "0.00000",
                f"{replication_speed:.5f}",
                f"{unfold_speed:.5f}",
                f"{target_replication_speed:.5f}",
                f"{target_unfold_speed:.5f}",
                f"{chaos_level:.5f}",
                sum(1 for e in enzymes if e.attached),
                sum(1 for p in particles if p.active),
                attachment_count,
                detachment_count,
                collision_count,
                transfer_count,
                mark_count,
                spill_count,
                f"{e0.body.pos.x:.5f}",
                f"{e0.body.pos.y:.5f}",
                f"{e0.body.pos.z:.5f}",
                int(e0.attached),
                f"{e1.body.pos.x:.5f}",
                f"{e1.body.pos.y:.5f}",
                f"{e1.body.pos.z:.5f}",
                int(e1.attached),
                f"{completion_hold:.5f}",
                f"{ai.local_stagnation:.5f}"
            ])
            last_csv_log = elapsed

        if CSV_ACTIVE and elapsed - last_csv_flush >= 2.0:
            csv_file.flush()
            last_csv_flush = elapsed

        if CSV_ACTIVE and elapsed >= CSV_RUN_SECONDS:
            break

finally:
    if csv_file:
        csv_file.flush()
        csv_file.close()

status_label.text += "\nCSV recording complete | saved run data"
completion_label = label(
    pos=vector(0, -7.25, 0),
    text=f"CSV recording complete: {os.path.basename(CSV_OUTPUT_PATH)}",
    height=13,
    box=False,
    opacity=0,
    color=vector(0.1, 0.36, 0.18)
)

while True:
    rate(10)
