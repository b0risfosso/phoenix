#!/usr/bin/env python3
"""
Human Genome Replication — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python human_genome_replication_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    F       force active fork burst
    N       spill nucleotides
    E       add extra repair enzymes
    D       disturb chromosome lanes
    C       clear temporary particles/markers
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    A simplified human genome is shown as 23 chromosome-pair lanes inside a nucleus.
    Each pair duplicates before division. Helicase opens glowing replication forks,
    polymerases follow behind, free nucleotides attach to growing daughter strands,
    repair enzymes patrol mismatches, and duplicated chromosome copies separate
    toward left/right daughter-cell zones.

This file is self-contained and intentionally uses VPython primitives only.

Note:
    The biology is stylized for an interactive simulation. It represents the process
    conceptually rather than using real chromosome lengths, timing, or molecular scale.
"""

from vpython import *
import random
import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene.title = "Human Genome Replication — VPython Simulation with Expressive AI"
scene.width = 1280
scene.height = 780
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1.0)
scene.center = vector(0, 0, 0)
scene.range = 18

scene.caption = """
Controls:
A toggle AI | P pause | R reset | M cycle AI mode | F fork burst | N nucleotide spill
E repair enzymes | D disturb | C clear particles | +/- speed | H print controls

Mouse drag rotates camera. Scroll zooms.
"""

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def rand_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m <= 1e-8:
        return fallback
    return v / m

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def color_mix(a, b, t):
    t = clamp(t, 0, 1)
    return vector(
        a.x + (b.x - a.x) * t,
        a.y + (b.y - a.y) * t,
        a.z + (b.z - a.z) * t,
    )

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

CHROMOSOME_PAIRS = 23
LANES_PER_ROW = 8
LANE_SPACING_X = 4.1
LANE_SPACING_Y = 2.15
LANE_LENGTH = 2.55
BASE_RADIUS = 0.045
MAX_NUCLEOTIDES = 260
MAX_SPARKS = 180
MAX_MARKERS = 120
MAX_REPAIR_ENZYMES = 18

BASE_COLORS = {
    "A": vector(0.20, 0.56, 1.00),
    "T": vector(1.00, 0.56, 0.20),
    "C": vector(0.22, 0.78, 0.45),
    "G": vector(0.72, 0.42, 1.00),
}

ENZYME_COLORS = {
    "helicase": vector(1.00, 0.77, 0.18),
    "polymerase": vector(0.14, 0.66, 0.94),
    "repair": vector(1.00, 0.28, 0.42),
}

AI_MODES = [
    "survey",
    "ignite_origins",
    "feed_forks",
    "repair_watch",
    "speed_run",
    "careful_copy",
    "chaotic_spill",
    "ritual_sync",
    "artistic_trace",
    "separate_duplicates",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Nucleotide:
    base: str
    obj: object
    vel: vector
    target_pair: int = -1
    age: float = 0.0
    attached: bool = False

@dataclass
class Particle:
    obj: object
    vel: vector
    age: float
    life: float

@dataclass
class ReplicationFork:
    side: int
    progress: float
    speed: float
    glow_phase: float
    helicase: object
    polymerase: object
    glow: object
    daughter_line: object
    active: bool = True

@dataclass
class ChromosomePair:
    pair_id: int
    origin: vector
    length: float
    row: int
    col: int
    base_color: vector
    lane_axis: vector
    strand_a: object
    strand_b: object
    original_bases: list = field(default_factory=list)
    daughter_bases: list = field(default_factory=list)
    base_objs: list = field(default_factory=list)
    forks: list = field(default_factory=list)
    duplicated: bool = False
    duplicate_left: object = None
    duplicate_right: object = None
    label_obj: object = None
    completion_marker: object = None
    disturbance: vector = field(default_factory=lambda: vector(0, 0, 0))

@dataclass
class RepairEnzyme:
    obj: object
    target_pair: int
    phase: float
    fixing: bool = False

@dataclass
class AIController:
    enabled: bool = True
    mode_index: int = 0
    mode_timer: float = 0.0
    action_timer: float = 0.0
    loop_timer: float = 0.0
    previous_completion: float = 0.0
    stable_timer: float = 0.0
    complete_timer: float = 0.0
    round_number: int = 1
    mood: float = 0.5
    last_action: str = "none"

    @property
    def mode(self):
        return AI_MODES[self.mode_index % len(AI_MODES)]

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(AI_MODES)
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.last_action = "mode switch"

# ---------------------------------------------------------------------------
# Global simulation state
# ---------------------------------------------------------------------------

chromosomes = []
nucleotides = []
sparks = []
markers = []
repair_enzymes = []
ai = AIController()

paused = False
sim_speed = 1.0
global_time = 0.0
selected_pair = 0

status_label = None
title_label = None
nucleus_shell = None
daughter_left_shell = None
daughter_right_shell = None
axis_ring_1 = None
axis_ring_2 = None

# ---------------------------------------------------------------------------
# Object cleanup
# ---------------------------------------------------------------------------

def hide_obj(obj):
    if obj is None:
        return
    try:
        obj.visible = False
    except Exception:
        pass

def clear_list_objects(items, attr_name=None):
    for item in items:
        if attr_name:
            hide_obj(getattr(item, attr_name, None))
        else:
            hide_obj(item)
    items.clear()

def clear_scene_objects():
    global chromosomes, nucleotides, sparks, markers, repair_enzymes
    for cp in chromosomes:
        hide_obj(cp.strand_a)
        hide_obj(cp.strand_b)
        hide_obj(cp.duplicate_left)
        hide_obj(cp.duplicate_right)
        hide_obj(cp.label_obj)
        hide_obj(cp.completion_marker)
        for obj in cp.base_objs:
            hide_obj(obj)
        for fork in cp.forks:
            hide_obj(fork.helicase)
            hide_obj(fork.polymerase)
            hide_obj(fork.glow)
            hide_obj(fork.daughter_line)
    chromosomes.clear()

    for n in nucleotides:
        hide_obj(n.obj)
    nucleotides.clear()

    for p in sparks:
        hide_obj(p.obj)
    sparks.clear()

    for m in markers:
        hide_obj(m)
    markers.clear()

    for r in repair_enzymes:
        hide_obj(r.obj)
    repair_enzymes.clear()

# ---------------------------------------------------------------------------
# Visual setup
# ---------------------------------------------------------------------------

def make_environment():
    global status_label, title_label, nucleus_shell, daughter_left_shell, daughter_right_shell
    global axis_ring_1, axis_ring_2

    hide_obj(status_label)
    hide_obj(title_label)
    hide_obj(nucleus_shell)
    hide_obj(daughter_left_shell)
    hide_obj(daughter_right_shell)
    hide_obj(axis_ring_1)
    hide_obj(axis_ring_2)

    nucleus_shell = sphere(
        pos=vector(0, 0, 0),
        radius=13.5,
        color=vector(0.78, 0.88, 1.0),
        opacity=0.13,
        shininess=0.25,
    )

    daughter_left_shell = sphere(
        pos=vector(-11.2, -7.7, -0.3),
        radius=3.1,
        color=vector(0.75, 1.0, 0.82),
        opacity=0.10,
    )
    daughter_right_shell = sphere(
        pos=vector(11.2, -7.7, -0.3),
        radius=3.1,
        color=vector(0.75, 1.0, 0.82),
        opacity=0.10,
    )

    axis_ring_1 = ring(
        pos=vector(0, 0, -0.08),
        axis=vector(0, 0, 1),
        radius=13.7,
        thickness=0.025,
        color=vector(0.62, 0.75, 1.0),
        opacity=0.45,
    )
    axis_ring_2 = ring(
        pos=vector(0, 0, 0.08),
        axis=vector(0, 1, 0),
        radius=13.7,
        thickness=0.018,
        color=vector(0.75, 0.85, 1.0),
        opacity=0.23,
    )

    title_label = label(
        pos=vector(0, 11.0, 0),
        text="Human Genome Replication: 23 chromosome pairs duplicate before division",
        height=18,
        color=vector(0.08, 0.12, 0.18),
        box=False,
        opacity=0,
    )

    status_label = label(
        pos=vector(-13.4, 12.0, 0),
        text="starting...",
        height=12,
        color=vector(0.05, 0.08, 0.12),
        box=False,
        opacity=0,
        align="left",
    )

# ---------------------------------------------------------------------------
# Chromosome construction
# ---------------------------------------------------------------------------

def make_base_tick(pos, base, radius=BASE_RADIUS):
    return sphere(
        pos=pos,
        radius=radius,
        color=BASE_COLORS.get(base, vector(0.7, 0.7, 0.7)),
        opacity=0.85,
        shininess=0.1,
    )

def make_chromosome_pair(pair_id, origin, row, col):
    color_factor = pair_id / max(1, CHROMOSOME_PAIRS - 1)
    base_color = color_mix(vector(0.35, 0.43, 0.85), vector(0.95, 0.48, 0.75), color_factor)
    lane_axis = vector(1, 0, 0)

    strand_offset = vector(0, 0.14, 0)
    strand_a = cylinder(
        pos=origin - lane_axis * LANE_LENGTH - strand_offset,
        axis=lane_axis * (LANE_LENGTH * 2),
        radius=0.033,
        color=base_color,
        opacity=0.82,
    )
    strand_b = cylinder(
        pos=origin - lane_axis * LANE_LENGTH + strand_offset,
        axis=lane_axis * (LANE_LENGTH * 2),
        radius=0.033,
        color=color_mix(base_color, vector(1, 1, 1), 0.35),
        opacity=0.82,
    )

    cp = ChromosomePair(
        pair_id=pair_id,
        origin=origin,
        length=LANE_LENGTH,
        row=row,
        col=col,
        base_color=base_color,
        lane_axis=lane_axis,
        strand_a=strand_a,
        strand_b=strand_b,
    )

    bases = ["A", "T", "C", "G"]
    for i in range(10):
        t = i / 9.0
        x = -LANE_LENGTH + t * (LANE_LENGTH * 2)
        base = random.choice(bases)
        pos_a = origin + vector(x, -0.14, 0.02)
        pos_b = origin + vector(x, 0.14, -0.02)
        cp.original_bases.append(base)
        cp.base_objs.append(make_base_tick(pos_a, base, 0.043))
        cp.base_objs.append(make_base_tick(pos_b, random.choice(bases), 0.038))
        # rung between strands
        rung = cylinder(
            pos=pos_a,
            axis=pos_b - pos_a,
            radius=0.012,
            color=vector(0.64, 0.70, 0.83),
            opacity=0.42,
        )
        cp.base_objs.append(rung)

    cp.label_obj = label(
        pos=origin + vector(0, 0.48, 0),
        text=f"{pair_id + 1}",
        height=8,
        color=vector(0.12, 0.12, 0.15),
        box=False,
        opacity=0,
    )

    for side in [-1, 1]:
        fork_pos = origin + lane_axis * (side * 0.10)
        helicase = sphere(
            pos=fork_pos + vector(0, 0, 0.11),
            radius=0.105,
            color=ENZYME_COLORS["helicase"],
            emissive=True,
            make_trail=True,
            retain=22,
            trail_radius=0.012,
        )
        polymerase = box(
            pos=fork_pos - lane_axis * side * 0.22 + vector(0, -0.34, 0.02),
            size=vector(0.21, 0.15, 0.15),
            color=ENZYME_COLORS["polymerase"],
            opacity=0.93,
        )
        glow = sphere(
            pos=fork_pos,
            radius=0.20,
            color=vector(1.0, 0.9, 0.25),
            opacity=0.32,
            emissive=True,
        )
        daughter_line = cylinder(
            pos=origin,
            axis=vector(0.001, 0, 0),
            radius=0.021,
            color=vector(0.27, 0.78, 0.94),
            opacity=0.58,
        )
        cp.forks.append(
            ReplicationFork(
                side=side,
                progress=0.02,
                speed=random.uniform(0.020, 0.036),
                glow_phase=random.uniform(0, math.tau),
                helicase=helicase,
                polymerase=polymerase,
                glow=glow,
                daughter_line=daughter_line,
            )
        )

    return cp

def build_genome():
    chromosomes.clear()
    start_x = -((LANES_PER_ROW - 1) * LANE_SPACING_X) / 2
    start_y = 6.5
    for pair_id in range(CHROMOSOME_PAIRS):
        row = pair_id // LANES_PER_ROW
        col = pair_id % LANES_PER_ROW
        y = start_y - row * LANE_SPACING_Y
        x = start_x + col * LANE_SPACING_X
        if row == 2:
            x += 2.0
        z = random.uniform(-0.35, 0.35)
        cp = make_chromosome_pair(pair_id, vector(x, y, z), row, col)
        chromosomes.append(cp)

# ---------------------------------------------------------------------------
# Particles and enzymes
# ---------------------------------------------------------------------------

def spawn_spark(pos, color_value=vector(1, 0.88, 0.26), count=1, spread=0.35, life=1.0):
    for _ in range(count):
        if len(sparks) >= MAX_SPARKS:
            old = sparks.pop(0)
            hide_obj(old.obj)
        obj = sphere(
            pos=pos + rand_vec(spread * 0.25),
            radius=random.uniform(0.025, 0.07),
            color=color_value,
            opacity=0.75,
            emissive=True,
        )
        vel = rand_vec(spread)
        sparks.append(Particle(obj=obj, vel=vel, age=0.0, life=random.uniform(life * 0.6, life * 1.3)))

def add_marker(pos, color_value=vector(1, 0.25, 0.35), radius=0.16, text=None):
    if len(markers) >= MAX_MARKERS:
        old = markers.pop(0)
        hide_obj(old)
    marker_obj = sphere(
        pos=pos,
        radius=radius,
        color=color_value,
        opacity=0.32,
        emissive=True,
    )
    markers.append(marker_obj)
    if text:
        if len(markers) >= MAX_MARKERS:
            old = markers.pop(0)
            hide_obj(old)
        markers.append(label(
            pos=pos + vector(0, 0.34, 0),
            text=text,
            height=8,
            color=vector(0.15, 0.1, 0.12),
            box=False,
            opacity=0,
        ))

def spawn_nucleotides(count=28, target_pair=-1, near_pos=None, energetic=False):
    bases = list(BASE_COLORS.keys())
    for _ in range(count):
        if len(nucleotides) >= MAX_NUCLEOTIDES:
            old = nucleotides.pop(0)
            hide_obj(old.obj)
        base = random.choice(bases)
        if near_pos is None:
            pos = vector(
                random.uniform(-10.5, 10.5),
                random.uniform(-8.5, 8.5),
                random.uniform(-1.7, 1.7),
            )
        else:
            pos = near_pos + rand_vec(0.95 if energetic else 0.55)
        obj = sphere(
            pos=pos,
            radius=0.075,
            color=BASE_COLORS[base],
            opacity=0.82,
            shininess=0.15,
            make_trail=energetic,
            retain=10,
            trail_radius=0.008,
        )
        vel = rand_vec(0.45 if energetic else 0.20)
        nucleotides.append(Nucleotide(base=base, obj=obj, vel=vel, target_pair=target_pair))

def add_repair_enzyme(target_pair=-1):
    if len(repair_enzymes) >= MAX_REPAIR_ENZYMES:
        old = repair_enzymes.pop(0)
        hide_obj(old.obj)
    if target_pair < 0:
        target_pair = random.randrange(len(chromosomes))
    cp = chromosomes[target_pair]
    obj = sphere(
        pos=cp.origin + rand_vec(0.6) + vector(0, 0, 0.28),
        radius=0.13,
        color=ENZYME_COLORS["repair"],
        opacity=0.94,
        make_trail=True,
        retain=18,
        trail_radius=0.01,
    )
    repair_enzymes.append(RepairEnzyme(obj=obj, target_pair=target_pair, phase=random.random() * math.tau))

def seed_environment():
    spawn_nucleotides(90, energetic=False)
    for _ in range(8):
        add_repair_enzyme()

# ---------------------------------------------------------------------------
# Simulation state helpers
# ---------------------------------------------------------------------------

def chromosome_completion(cp):
    if not cp.forks:
        return 0
    return clamp(sum(f.progress for f in cp.forks) / len(cp.forks), 0, 1)

def total_completion():
    if not chromosomes:
        return 0
    return sum(chromosome_completion(cp) for cp in chromosomes) / len(chromosomes)

def active_fork_count():
    return sum(1 for cp in chromosomes for f in cp.forks if f.active)

def least_complete_pair():
    if not chromosomes:
        return 0
    return min(range(len(chromosomes)), key=lambda i: chromosome_completion(chromosomes[i]))

def most_complete_pair():
    if not chromosomes:
        return 0
    return max(range(len(chromosomes)), key=lambda i: chromosome_completion(chromosomes[i]))

def random_active_pair():
    active = [i for i, cp in enumerate(chromosomes) if chromosome_completion(cp) < 0.99]
    if not active:
        return random.randrange(len(chromosomes))
    return random.choice(active)

# ---------------------------------------------------------------------------
# Replication mechanics
# ---------------------------------------------------------------------------

def fork_position(cp, fork):
    return cp.origin + cp.lane_axis * (fork.side * fork.progress * cp.length)

def update_fork_visual(cp, fork, dt):
    pos = fork_position(cp, fork)
    fork.glow_phase += dt * 6.0
    pulse = 0.5 + 0.5 * math.sin(fork.glow_phase)

    fork.helicase.pos = pos + vector(0, 0, 0.16 + 0.04 * pulse)
    fork.polymerase.pos = pos - cp.lane_axis * fork.side * 0.30 + vector(0, -0.33, 0.03)
    fork.glow.pos = pos
    fork.glow.radius = 0.18 + 0.10 * pulse
    fork.glow.opacity = 0.20 + 0.23 * pulse

    copied_len = fork.progress * cp.length
    if fork.side < 0:
        fork.daughter_line.pos = cp.origin - cp.lane_axis * copied_len + vector(0, -0.28, 0.05)
        fork.daughter_line.axis = cp.lane_axis * copied_len
    else:
        fork.daughter_line.pos = cp.origin + vector(0, -0.28, 0.05)
        fork.daughter_line.axis = cp.lane_axis * copied_len

def complete_chromosome(cp):
    if cp.duplicated:
        return

    cp.duplicated = True
    offset = vector(0, -0.58, 0.15)

    cp.duplicate_left = cylinder(
        pos=cp.origin - cp.lane_axis * cp.length + offset + vector(-0.16, 0, 0),
        axis=cp.lane_axis * (cp.length * 2),
        radius=0.048,
        color=vector(0.32, 0.72, 0.96),
        opacity=0.76,
    )
    cp.duplicate_right = cylinder(
        pos=cp.origin - cp.lane_axis * cp.length + offset + vector(0.16, 0, 0),
        axis=cp.lane_axis * (cp.length * 2),
        radius=0.048,
        color=vector(0.70, 0.38, 0.95),
        opacity=0.76,
    )
    cp.completion_marker = sphere(
        pos=cp.origin + vector(0, -0.58, 0.38),
        radius=0.18,
        color=vector(0.18, 0.92, 0.38),
        opacity=0.45,
        emissive=True,
    )
    spawn_spark(cp.origin + vector(0, -0.5, 0.4), vector(0.25, 0.95, 0.45), count=7, spread=0.5, life=1.2)

def update_chromosomes(dt):
    for cp in chromosomes:
        completion = chromosome_completion(cp)

        # mild organic motion
        cp.disturbance *= 0.94
        wobble = vector(
            math.sin(global_time * 0.9 + cp.pair_id) * 0.018,
            math.cos(global_time * 0.7 + cp.pair_id * 0.4) * 0.012,
            math.sin(global_time * 0.5 + cp.pair_id) * 0.012,
        ) + cp.disturbance * 0.018

        cp.strand_a.pos += wobble * dt
        cp.strand_b.pos += wobble * dt

        for fork in cp.forks:
            if fork.active:
                fork.progress += dt * fork.speed * sim_speed
                if fork.progress >= 1.0:
                    fork.progress = 1.0
                    fork.active = False
                    spawn_spark(fork_position(cp, fork), vector(0.22, 0.92, 0.40), count=5, spread=0.35, life=0.9)
            update_fork_visual(cp, fork, dt)

            if random.random() < dt * 1.15 * sim_speed and fork.active:
                spawn_spark(fork_position(cp, fork), vector(1.0, 0.88, 0.25), count=1, spread=0.22, life=0.75)

        if completion >= 0.995:
            complete_chromosome(cp)

        # move completed duplicates toward daughter-cell zones during late completion
        if cp.duplicated and cp.duplicate_left and cp.duplicate_right:
            t = clamp((total_completion() - 0.65) / 0.35, 0, 1)
            left_target = vector(-11.2, -7.7, 0) + vector(random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), 0)
            right_target = vector(11.2, -7.7, 0) + vector(random.uniform(-0.03, 0.03), random.uniform(-0.03, 0.03), 0)
            cp.duplicate_left.pos = lerp(cp.duplicate_left.pos, left_target + vector(-0.5, cp.row * 0.08, 0), dt * 0.55 * t)
            cp.duplicate_right.pos = lerp(cp.duplicate_right.pos, right_target + vector(0.5, cp.row * 0.08, 0), dt * 0.55 * t)

def update_nucleotides(dt):
    for n in list(nucleotides):
        n.age += dt
        if n.attached:
            continue

        # Target the nearest active fork if assigned, otherwise wander.
        attraction = vector(0, 0, 0)
        if chromosomes:
            if 0 <= n.target_pair < len(chromosomes):
                cp = chromosomes[n.target_pair]
            else:
                cp = chromosomes[random_active_pair()]
                if random.random() < 0.01:
                    n.target_pair = cp.pair_id

            live_forks = [f for f in cp.forks if f.active]
            if live_forks:
                nearest = min(live_forks, key=lambda f: mag(fork_position(cp, f) - n.obj.pos))
                target = fork_position(cp, nearest)
                to_target = target - n.obj.pos
                attraction = safe_norm(to_target, rand_vec(1)) * (0.24 + 0.18 * sim_speed)
                if mag(to_target) < 0.32:
                    n.attached = True
                    n.obj.pos = target + vector(0, -0.18, 0.05)
                    n.obj.opacity = 0.42
                    n.obj.radius *= 0.82
                    spawn_spark(target, BASE_COLORS[n.base], count=2, spread=0.18, life=0.55)
                    continue

        n.vel += attraction * dt + rand_vec(0.035) * dt
        if mag(n.vel) > 1.25:
            n.vel = safe_norm(n.vel) * 1.25
        n.obj.pos += n.vel * dt * sim_speed

        # soft nuclear boundary
        if mag(n.obj.pos) > 12.8:
            n.vel += safe_norm(-n.obj.pos) * 0.55 * dt

        # old free nucleotides recycle
        if n.age > 38 and random.random() < dt * 0.1:
            hide_obj(n.obj)
            nucleotides.remove(n)

def update_repair_enzymes(dt):
    for r in repair_enzymes:
        if not chromosomes:
            continue
        if r.target_pair >= len(chromosomes) or chromosome_completion(chromosomes[r.target_pair]) > 0.99:
            r.target_pair = random_active_pair()

        cp = chromosomes[r.target_pair]
        r.phase += dt * (1.4 + 0.25 * sim_speed)

        # Patrol around the active fork, then flash as if correcting mismatches.
        live_forks = [f for f in cp.forks if f.active]
        if live_forks:
            fork = random.choice(live_forks)
            target = fork_position(cp, fork) + vector(0, 0.34 * math.sin(r.phase), 0.28 * math.cos(r.phase))
        else:
            target = cp.origin + vector(0, 0.25 * math.sin(r.phase), 0.25)

        r.obj.pos = lerp(r.obj.pos, target, dt * 1.6)
        if random.random() < dt * 0.15:
            r.fixing = not r.fixing
        r.obj.color = vector(1.0, 0.20, 0.36) if r.fixing else ENZYME_COLORS["repair"]
        if r.fixing and random.random() < dt * 1.1:
            spawn_spark(r.obj.pos, vector(1.0, 0.28, 0.42), count=1, spread=0.15, life=0.45)

def update_particles(dt):
    for p in list(sparks):
        p.age += dt
        p.obj.pos += p.vel * dt
        p.vel *= 0.96
        p.obj.opacity = max(0, 0.75 * (1 - p.age / p.life))
        if p.age >= p.life:
            hide_obj(p.obj)
            sparks.remove(p)

    # marker fade
    for m in list(markers):
        try:
            if hasattr(m, "opacity"):
                m.opacity *= 0.995
                if m.opacity < 0.035:
                    hide_obj(m)
                    markers.remove(m)
        except Exception:
            pass

# ---------------------------------------------------------------------------
# AI behavior
# ---------------------------------------------------------------------------

def get_ai_state():
    return {
        "completion": total_completion(),
        "active_forks": active_fork_count(),
        "free_nucleotides": sum(1 for n in nucleotides if not n.attached),
        "repair_count": len(repair_enzymes),
        "least_pair": least_complete_pair(),
        "most_pair": most_complete_pair(),
        "stable_timer": ai.stable_timer,
        "complete_timer": ai.complete_timer,
        "mode": ai.mode,
        "round": ai.round_number,
    }

def ai_mark_pair(pair_id, color_value=vector(1, 0.25, 0.38), text=None):
    if not chromosomes:
        return
    cp = chromosomes[pair_id % len(chromosomes)]
    add_marker(cp.origin + vector(0, 0, 0.55), color_value, radius=0.22, text=text)

def ai_force_fork_burst(pair_id=None):
    if not chromosomes:
        return
    if pair_id is None:
        pair_id = random_active_pair()
    cp = chromosomes[pair_id]
    for f in cp.forks:
        if f.active:
            f.speed = clamp(f.speed * random.uniform(1.20, 1.55), 0.015, 0.13)
            spawn_spark(fork_position(cp, f), vector(1.0, 0.83, 0.18), count=5, spread=0.42, life=0.85)
    ai_mark_pair(pair_id, vector(1.0, 0.78, 0.18), "fork burst")
    ai.last_action = "fork burst"

def ai_feed_pair(pair_id=None, count=24, energetic=True):
    if not chromosomes:
        return
    if pair_id is None:
        pair_id = least_complete_pair()
    cp = chromosomes[pair_id]
    spawn_nucleotides(count, target_pair=pair_id, near_pos=cp.origin, energetic=energetic)
    ai_mark_pair(pair_id, vector(0.20, 0.75, 1.0), "feed")
    ai.last_action = "nucleotide spill"

def ai_repair_pair(pair_id=None):
    if not chromosomes:
        return
    if pair_id is None:
        pair_id = random_active_pair()
    for _ in range(2):
        add_repair_enzyme(pair_id)
    ai_mark_pair(pair_id, vector(1.0, 0.25, 0.40), "repair")
    ai.last_action = "repair patrol"

def ai_disturb_pair(pair_id=None, amount=0.8):
    if not chromosomes:
        return
    if pair_id is None:
        pair_id = random_active_pair()
    cp = chromosomes[pair_id]
    cp.disturbance += rand_vec(amount)
    for f in cp.forks:
        f.speed = clamp(f.speed * random.uniform(0.85, 1.35), 0.014, 0.11)
    spawn_spark(cp.origin, vector(0.85, 0.52, 1.0), count=6, spread=0.65, life=0.95)
    ai_mark_pair(pair_id, vector(0.82, 0.48, 1.0), "disturb")
    ai.last_action = "disturbance"

def ai_ritual_sync():
    for i, cp in enumerate(chromosomes):
        phase = (i / max(1, len(chromosomes))) * math.tau + global_time
        if math.sin(phase) > 0.92 and chromosome_completion(cp) < 0.98:
            spawn_spark(cp.origin + vector(0, 0, 0.35), vector(1.0, 0.88, 0.22), count=1, spread=0.22, life=0.65)
        for f in cp.forks:
            if f.active:
                f.speed = clamp(0.028 + 0.018 * (0.5 + 0.5 * math.sin(phase)), 0.015, 0.07)
    ai.last_action = "synchronized fork rhythm"

def ai_artistic_trace():
    pair_id = int((global_time * 2.2) % max(1, len(chromosomes)))
    cp = chromosomes[pair_id]
    angle = global_time * 2.1 + pair_id
    pos = cp.origin + vector(math.cos(angle) * 0.4, math.sin(angle) * 0.4, 0.45)
    add_marker(pos, vector(0.35, 0.80, 1.0), radius=0.065, text=None)
    if random.random() < 0.18:
        ai_feed_pair(pair_id, count=3, energetic=True)
    ai.last_action = "artistic trace"

def ai_separate_duplicates():
    completion = total_completion()
    if completion < 0.75:
        ai_feed_pair(least_complete_pair(), count=14, energetic=True)
        return
    for cp in chromosomes:
        if cp.duplicated:
            spawn_spark(cp.origin + vector(0, -0.6, 0.32), vector(0.24, 0.95, 0.42), count=1, spread=0.12, life=0.55)
    ai.last_action = "duplicate separation"

def ai_detect_stagnation(dt):
    completion = total_completion()
    delta = abs(completion - ai.previous_completion)

    if delta < 0.00035:
        ai.stable_timer += dt
    else:
        ai.stable_timer = 0.0

    if completion >= 0.995:
        ai.complete_timer += dt
    else:
        ai.complete_timer = 0.0

    ai.previous_completion = completion

def ai_choose_mode(state):
    # Completion and stagnation override random mode choice.
    if state["completion"] > 0.86:
        return "separate_duplicates"
    if state["stable_timer"] > 7.0:
        return random.choice(["chaotic_spill", "ignite_origins", "feed_forks"])
    if state["free_nucleotides"] < 30:
        return "feed_forks"
    if state["repair_count"] < 5:
        return "repair_watch"
    if random.random() < 0.22:
        return random.choice(AI_MODES)
    return ai.mode

def ai_set_mode_by_name(mode_name):
    if mode_name in AI_MODES:
        ai.mode_index = AI_MODES.index(mode_name)
        ai.mode_timer = 0.0
        ai.action_timer = 0.0

def update_ai(dt):
    global sim_speed

    if not ai.enabled:
        return

    state = get_ai_state()
    ai_detect_stagnation(dt)
    ai.mode_timer += dt
    ai.action_timer += dt

    # Start a new round after visible completion.
    if ai.complete_timer > 7.0:
        ai.loop_timer += dt
        if ai.loop_timer > 1.8:
            reset_simulation(new_round=True)
            return
    else:
        ai.loop_timer = 0.0

    # Switch modes over time and when state demands it.
    if ai.mode_timer > random.uniform(5.0, 9.0):
        new_mode = ai_choose_mode(state)
        ai_set_mode_by_name(new_mode)

    mode = ai.mode
    act_every = 1.2
    if mode in ["speed_run", "chaotic_spill", "artistic_trace"]:
        act_every = 0.55
    elif mode in ["careful_copy", "repair_watch"]:
        act_every = 1.55
    elif mode == "ritual_sync":
        act_every = 0.18

    if ai.action_timer < act_every:
        if mode == "ritual_sync":
            ai_ritual_sync()
        elif mode == "artistic_trace":
            ai_artistic_trace()
        return

    ai.action_timer = 0.0

    if mode == "survey":
        pair_id = least_complete_pair()
        ai_mark_pair(pair_id, vector(0.70, 0.78, 1.0), "survey")
        if random.random() < 0.38:
            ai_feed_pair(pair_id, count=10, energetic=False)

    elif mode == "ignite_origins":
        pair_id = random_active_pair()
        ai_force_fork_burst(pair_id)
        if random.random() < 0.45:
            ai_feed_pair(pair_id, count=10, energetic=True)

    elif mode == "feed_forks":
        ai_feed_pair(least_complete_pair(), count=random.randint(18, 34), energetic=True)

    elif mode == "repair_watch":
        pair_id = random_active_pair()
        ai_repair_pair(pair_id)
        for cp in chromosomes:
            for f in cp.forks:
                f.speed = clamp(f.speed * 0.98, 0.016, 0.07)

    elif mode == "speed_run":
        sim_speed = clamp(sim_speed * 1.01, 0.35, 3.5)
        ai_force_fork_burst(least_complete_pair())
        ai_feed_pair(least_complete_pair(), count=10, energetic=True)

    elif mode == "careful_copy":
        pair_id = least_complete_pair()
        ai_feed_pair(pair_id, count=8, energetic=False)
        ai_repair_pair(pair_id)
        for cp in chromosomes:
            for f in cp.forks:
                f.speed = clamp(f.speed * 0.96, 0.012, 0.045)

    elif mode == "chaotic_spill":
        pair_id = random_active_pair()
        ai_disturb_pair(pair_id, amount=1.4)
        ai_feed_pair(pair_id, count=random.randint(16, 36), energetic=True)

    elif mode == "ritual_sync":
        ai_ritual_sync()

    elif mode == "artistic_trace":
        ai_artistic_trace()

    elif mode == "separate_duplicates":
        ai_separate_duplicates()

# ---------------------------------------------------------------------------
# Human controls
# ---------------------------------------------------------------------------

def print_controls():
    print(__doc__)

def keydown(evt):
    global paused, sim_speed, selected_pair

    key = evt.key.lower()

    if key == "a":
        ai.enabled = not ai.enabled
        ai.last_action = "AI on" if ai.enabled else "AI off"

    elif key == "p":
        paused = not paused

    elif key == "r":
        reset_simulation(new_round=True)

    elif key == "m":
        ai.next_mode()

    elif key == "f":
        selected_pair = random_active_pair()
        ai_force_fork_burst(selected_pair)

    elif key == "n":
        selected_pair = random_active_pair()
        ai_feed_pair(selected_pair, count=36, energetic=True)

    elif key == "e":
        selected_pair = random_active_pair()
        ai_repair_pair(selected_pair)

    elif key == "d":
        selected_pair = random_active_pair()
        ai_disturb_pair(selected_pair, amount=1.5)

    elif key == "c":
        clear_list_objects(sparks, "obj")
        for m in markers:
            hide_obj(m)
        markers.clear()

    elif key in ["+", "="]:
        sim_speed = clamp(sim_speed * 1.18, 0.2, 5.0)

    elif key in ["-", "_"]:
        sim_speed = clamp(sim_speed / 1.18, 0.2, 5.0)

    elif key == "h":
        print_controls()

scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Reset and status
# ---------------------------------------------------------------------------

def reset_simulation(new_round=False):
    global global_time, sim_speed, paused, ai

    if new_round:
        ai.round_number += 1

    clear_scene_objects()
    make_environment()
    build_genome()
    seed_environment()

    global_time = 0.0
    paused = False
    sim_speed = 1.0

    ai.mode_timer = 0.0
    ai.action_timer = 0.0
    ai.loop_timer = 0.0
    ai.previous_completion = 0.0
    ai.stable_timer = 0.0
    ai.complete_timer = 0.0
    ai.last_action = "new round"
    ai.mode_index = 0

def update_status():
    state = get_ai_state()
    completion_pct = state["completion"] * 100.0
    txt = (
        f"Round: {ai.round_number}\n"
        f"AI: {'ON' if ai.enabled else 'OFF'} | Mode: {ai.mode}\n"
        f"Paused: {'YES' if paused else 'NO'} | Speed: {sim_speed:.2f}x\n"
        f"Genome duplicated: {completion_pct:5.1f}%\n"
        f"Active forks: {state['active_forks']} | Free nucleotides: {state['free_nucleotides']}\n"
        f"Repair enzymes: {state['repair_count']} | Stable: {ai.stable_timer:4.1f}s\n"
        f"Last action: {ai.last_action}"
    )
    status_label.text = txt

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

make_environment()
build_genome()
seed_environment()
print_controls()

while True:
    rate(60)
    dt = 1.0 / 60.0

    if paused:
        update_status()
        continue

    global_time += dt * sim_speed

    update_ai(dt)
    update_chromosomes(dt)
    update_nucleotides(dt)
    update_repair_enzymes(dt)
    update_particles(dt)
    update_status()
