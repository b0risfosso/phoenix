"""
Human Genome Mutation Simulation — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python human_genome_mutation_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    1       create substitution mutation
    2       create deletion mutation
    3       create insertion mutation
    4       create duplication mutation
    5       create random mutation
    E       spawn repair enzyme
    C       clear repaired/faded markers
    Space   force repair burst
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    Chromosome pairs float inside a transparent nucleus. Random mutations appear
    across chromosome regions: substitutions, deletions, insertions, and duplications.
    Repair enzymes patrol the nucleus, attach to damaged sites, mark them, repair
    them, then detach. A rule-based expressive AI controller reads simulation state,
    switches behavior modes, creates mutation pressure, organizes repair responses,
    marks chromosomes, and resets the round when the scene becomes complete or stable.
"""

from vpython import *
import random
import math
from dataclasses import dataclass, field

scene = canvas(
    title="Human Genome Mutation Simulation — VPython + Expressive AI Controller",
    width=1280,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.35, -0.25, -1)
scene.range = 18
scene.userspin = True
scene.userzoom = True

LIGHT_BLUE = vector(0.76, 0.88, 1.0)
NUCLEUS_BLUE = vector(0.62, 0.78, 1.0)
DNA_BLUE = vector(0.25, 0.42, 0.95)
DNA_PURPLE = vector(0.56, 0.35, 0.95)
GENE_GREEN = vector(0.28, 0.72, 0.38)
REPAIR_GOLD = vector(1.0, 0.74, 0.20)
SUB_RED = vector(1.0, 0.25, 0.18)
DEL_ORANGE = vector(1.0, 0.50, 0.16)
INS_CYAN = vector(0.0, 0.72, 0.90)
DUP_MAGENTA = vector(0.95, 0.25, 0.82)
REPAIRED_GREEN = vector(0.25, 0.82, 0.46)
GRAY = vector(0.68, 0.70, 0.75)
DARK_TEXT = vector(0.12, 0.15, 0.18)

objects_to_clear = []
chromosomes = []
mutations = []
repair_enzymes = []
particles = []
ai_marks = []
round_number = 1
tick_count = 0
sim_time = 0.0
dt = 0.016
speed = 1.0
paused = False
ai_enabled = True
manual_override_timer = 0.0
repair_burst_timer = 0.0

MUTATION_TYPES = ["substitution", "deletion", "insertion", "duplication"]
mutation_colors = {
    "substitution": SUB_RED,
    "deletion": DEL_ORANGE,
    "insertion": INS_CYAN,
    "duplication": DUP_MAGENTA,
}
mutation_symbols = {
    "substitution": "S",
    "deletion": "DEL",
    "insertion": "INS",
    "duplication": "DUP",
}


def add_obj(obj):
    objects_to_clear.append(obj)
    return obj


def random_unit_vector():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) > 0.001:
            return norm(v)


def safe_norm(v):
    if mag(v) < 1e-6:
        return vector(0, 0, 0)
    return norm(v)


def make_label(text, pos, height=10, color_value=DARK_TEXT, opacity=0, box=False):
    return add_obj(label(text=text, pos=pos, height=height, color=color_value, opacity=opacity, box=box, border=3, font="sans"))


def show_controls():
    print(__doc__)


@dataclass
class Chromosome:
    index: int
    pair_id: int
    center: vector
    angle: float
    length: float
    radius: float
    color_a: vector
    color_b: vector
    damage_load: float = 0.0
    repaired_count: int = 0
    parts: list = field(default_factory=list)
    base_positions: list = field(default_factory=list)
    gene_regions: list = field(default_factory=list)
    label_obj: object = None
    halo: object = None

    def mark_damage(self):
        self.damage_load = min(1.0, self.damage_load + 0.12)
        if self.halo:
            self.halo.opacity = 0.08 + self.damage_load * 0.25
            self.halo.color = vector(1.0, 0.55 + 0.25 * (1 - self.damage_load), 0.35)

    def mark_repaired(self):
        self.damage_load = max(0.0, self.damage_load - 0.18)
        self.repaired_count += 1
        if self.halo:
            self.halo.opacity = 0.04 + self.damage_load * 0.18
            self.halo.color = REPAIRED_GREEN if self.damage_load < 0.08 else vector(1.0, 0.65, 0.30)


@dataclass
class Mutation:
    mtype: str
    chromosome: Chromosome
    base_index: int
    pos: vector
    severity: float
    age: float = 0.0
    repaired: bool = False
    attached_enzyme: object = None
    marker: object = None
    glow: object = None
    label_obj: object = None
    extra_parts: list = field(default_factory=list)

    def update_visual(self):
        pulse = 0.5 + 0.5 * math.sin(self.age * 7.0)
        if self.marker:
            self.marker.radius = 0.20 + 0.06 * pulse + 0.06 * self.severity
            self.marker.color = REPAIRED_GREEN if self.repaired else mutation_colors[self.mtype]
            self.marker.opacity = 0.32 if self.repaired else 0.85
        if self.glow:
            self.glow.opacity = 0.025 if self.repaired else 0.08 + 0.10 * pulse
            self.glow.radius = 0.42 + 0.10 * pulse
        if self.label_obj:
            self.label_obj.pos = self.pos + vector(0, 0.55 + 0.08 * pulse, 0)


@dataclass
class RepairEnzyme:
    pos: vector
    vel: vector
    mode: str = "patrol"
    target: Mutation = None
    attach_timer: float = 0.0
    repair_progress: float = 0.0
    body: object = None
    ring_obj: object = None
    label_obj: object = None

    def update_visual(self):
        if self.body:
            self.body.pos = self.pos
        if self.ring_obj:
            self.ring_obj.pos = self.pos
            self.ring_obj.axis = vector(0, 1, 0)
        if self.label_obj:
            self.label_obj.pos = self.pos + vector(0, 0.45, 0)


@dataclass
class SparkParticle:
    pos: vector
    vel: vector
    age: float
    life: float
    obj: object
    fade: bool = True


@dataclass
class GenomeAI:
    enabled: bool = True
    mode: str = "survey"
    mode_timer: float = 0.0
    decision_timer: float = 0.0
    stagnation_timer: float = 0.0
    loop_timer: float = 0.0
    last_mutation_count: int = 0
    last_repaired_count: int = 0
    selected_chromosome: Chromosome = None
    ritual_phase: float = 0.0
    mutation_pressure: float = 0.0
    repair_pressure: float = 0.0
    history: list = field(default_factory=list)
    modes: list = field(default_factory=lambda: [
        "survey", "seed_mutations", "repair_focus", "chaos_burst",
        "careful_cleanup", "duplication_wave", "artistic_marking", "reset_round"
    ])

    def read_state(self):
        total = len(mutations)
        unresolved = sum(1 for m in mutations if not m.repaired)
        repaired = sum(1 for m in mutations if m.repaired)
        damage = sum(c.damage_load for c in chromosomes)
        return {
            "total_mutations": total,
            "unresolved": unresolved,
            "repaired": repaired,
            "enzymes": len(repair_enzymes),
            "damage": damage,
            "stable_for_reset": False,
        }

    def update_stagnation(self, state, step_dt):
        changed = state["total_mutations"] != self.last_mutation_count or state["repaired"] != self.last_repaired_count
        if changed:
            self.stagnation_timer = 0.0
            self.last_mutation_count = state["total_mutations"]
            self.last_repaired_count = state["repaired"]
        else:
            self.stagnation_timer += step_dt
        complete = state["total_mutations"] >= 10 and state["unresolved"] == 0
        too_empty = state["total_mutations"] == 0 and self.mode_timer > 6.0
        too_stable = self.stagnation_timer > 15.0
        state["stable_for_reset"] = complete or too_empty or too_stable
        return state

    def choose_next_mode(self, state):
        previous = self.mode
        unresolved = state["unresolved"]
        total = state["total_mutations"]
        repaired = state["repaired"]
        enzymes = state["enzymes"]
        if state["stable_for_reset"]:
            self.mode = "reset_round"
        elif unresolved == 0 and total < 5:
            self.mode = random.choice(["seed_mutations", "duplication_wave", "artistic_marking"])
        elif unresolved > 12 and enzymes < 7:
            self.mode = random.choice(["repair_focus", "careful_cleanup"])
        elif unresolved > 18:
            self.mode = "chaos_burst" if random.random() < 0.35 else "repair_focus"
        elif repaired > 10 and random.random() < 0.35:
            self.mode = random.choice(["seed_mutations", "artistic_marking"])
        else:
            options = [m for m in self.modes if m != previous and m != "reset_round"]
            self.mode = random.choice(options)
        self.mode_timer = 0.0
        self.history.append(self.mode)
        if len(self.history) > 12:
            self.history.pop(0)

    def update(self, step_dt):
        if not self.enabled:
            return
        self.mode_timer += step_dt
        self.decision_timer -= step_dt
        self.ritual_phase += step_dt
        state = self.update_stagnation(self.read_state(), step_dt)
        if self.decision_timer <= 0.0 or self.mode_timer > random.uniform(5.0, 9.0):
            self.choose_next_mode(state)
            self.decision_timer = random.uniform(2.2, 4.5)
        if chromosomes and (self.selected_chromosome is None or random.random() < 0.02):
            self.selected_chromosome = pick_chromosome_by_damage(prefer_damage=self.mode in ["repair_focus", "careful_cleanup"])
        if self.mode == "survey":
            self.action_survey(step_dt, state)
        elif self.mode == "seed_mutations":
            self.action_seed_mutations(step_dt, state)
        elif self.mode == "repair_focus":
            self.action_repair_focus(step_dt, state)
        elif self.mode == "chaos_burst":
            self.action_chaos_burst(step_dt, state)
        elif self.mode == "careful_cleanup":
            self.action_careful_cleanup(step_dt, state)
        elif self.mode == "duplication_wave":
            self.action_duplication_wave(step_dt, state)
        elif self.mode == "artistic_marking":
            self.action_artistic_marking(step_dt, state)
        elif self.mode == "reset_round":
            self.action_reset_round(step_dt, state)

    def action_survey(self, step_dt, state):
        self.mutation_pressure = max(0.0, self.mutation_pressure - step_dt * 0.2)
        self.repair_pressure = max(0.0, self.repair_pressure - step_dt * 0.15)
        if random.random() < 0.012:
            c = pick_chromosome_by_damage(prefer_damage=False)
            create_ai_mark(c.center + random_unit_vector() * 0.8, "survey", LIGHT_BLUE, life=3.0)

    def action_seed_mutations(self, step_dt, state):
        self.mutation_pressure += step_dt
        if random.random() < 0.055 + self.mutation_pressure * 0.005:
            create_mutation(random.choice(["substitution", "insertion", "deletion"]))
            self.mutation_pressure = 0.0
        if random.random() < 0.01:
            spawn_repair_enzyme()

    def action_repair_focus(self, step_dt, state):
        self.repair_pressure += step_dt
        if state["enzymes"] < 8 and random.random() < 0.045:
            spawn_repair_enzyme()
        if random.random() < 0.04:
            target = find_oldest_unrepaired_mutation()
            if target:
                create_ai_mark(target.pos, "repair target", REPAIR_GOLD, life=4.0)

    def action_chaos_burst(self, step_dt, state):
        if random.random() < 0.08:
            create_mutation(random.choice(MUTATION_TYPES))
        if random.random() < 0.025:
            c = random.choice(chromosomes)
            spill_mutation_particles(c.center, random.choice(list(mutation_colors.values())), amount=10)
        if state["enzymes"] < 4 and random.random() < 0.03:
            spawn_repair_enzyme()

    def action_careful_cleanup(self, step_dt, state):
        if state["enzymes"] < 10 and state["unresolved"] > state["enzymes"] and random.random() < 0.07:
            spawn_repair_enzyme()
        if random.random() < 0.03:
            target = find_nearest_unrepaired_to_origin()
            if target:
                target.severity = max(0.15, target.severity - 0.03)
                create_ai_mark(target.pos, "soft repair", REPAIRED_GREEN, life=2.5)

    def action_duplication_wave(self, step_dt, state):
        wave = 0.5 + 0.5 * math.sin(self.ritual_phase * 2.4)
        if random.random() < 0.035 + 0.025 * wave:
            create_mutation("duplication")
        if random.random() < 0.02:
            create_orbiting_marker(random.choice(chromosomes))

    def action_artistic_marking(self, step_dt, state):
        if random.random() < 0.055:
            c = random.choice(chromosomes)
            create_ai_mark(c.center + random_unit_vector() * random.uniform(0.4, 1.3), "pattern", random.choice([INS_CYAN, DUP_MAGENTA, REPAIR_GOLD]), life=4.5)
        if random.random() < 0.025:
            create_mutation(random.choice(["substitution", "insertion"]))

    def action_reset_round(self, step_dt, state):
        self.loop_timer += step_dt
        if self.loop_timer < 2.0:
            create_ai_mark(random_unit_vector() * random.uniform(1.0, 5.0), "round complete", REPAIRED_GREEN, life=2.0)
        else:
            reset_simulation(new_round=True)
            self.loop_timer = 0.0
            self.mode = "survey"
            self.mode_timer = 0.0
            self.stagnation_timer = 0.0


ai = GenomeAI()


def create_chromosome(index, pair_id, center, angle, length=4.0):
    axis_dir = vector(math.cos(angle), math.sin(angle) * 0.15, math.sin(angle))
    perp_a = cross(axis_dir, vector(0, 1, 0))
    if mag(perp_a) < 0.01:
        perp_a = vector(1, 0, 0)
    else:
        perp_a = norm(perp_a)
    perp_b = norm(cross(axis_dir, perp_a))
    chrom = Chromosome(index=index, pair_id=pair_id, center=center, angle=angle, length=length, radius=0.22, color_a=DNA_BLUE, color_b=DNA_PURPLE)
    chrom.halo = add_obj(sphere(pos=center, radius=0.95, color=LIGHT_BLUE, opacity=0.04, shininess=0.2))
    steps = 18
    last_a = None
    last_b = None
    for i in range(steps):
        t = (i / (steps - 1) - 0.5) * length
        twist = i * 0.85
        base_center = center + axis_dir * t
        helix_offset = perp_a * math.cos(twist) * chrom.radius + perp_b * math.sin(twist) * chrom.radius
        p1 = base_center + helix_offset
        p2 = base_center - helix_offset
        chrom.base_positions.append(base_center)
        s1 = add_obj(sphere(pos=p1, radius=0.065, color=chrom.color_a, shininess=0.5))
        s2 = add_obj(sphere(pos=p2, radius=0.065, color=chrom.color_b, shininess=0.5))
        rung = add_obj(cylinder(pos=p1, axis=p2 - p1, radius=0.018, color=GRAY, opacity=0.72))
        chrom.parts.extend([s1, s2, rung])
        if last_a is not None:
            c1 = add_obj(cylinder(pos=last_a, axis=p1 - last_a, radius=0.026, color=chrom.color_a, opacity=0.9))
            c2 = add_obj(cylinder(pos=last_b, axis=p2 - last_b, radius=0.026, color=chrom.color_b, opacity=0.9))
            chrom.parts.extend([c1, c2])
        last_a = p1
        last_b = p2
    for g in range(3):
        idx = 3 + g * 5 + random.randint(0, 1)
        if idx < len(chrom.base_positions):
            gp = chrom.base_positions[idx]
            gene = add_obj(sphere(pos=gp + perp_b * 0.38, radius=0.12, color=GENE_GREEN, opacity=0.78))
            gene_label = make_label("gene", gp + perp_b * 0.7, height=7, color_value=GENE_GREEN)
            chrom.gene_regions.append(gene)
            chrom.parts.extend([gene, gene_label])
    chrom.label_obj = make_label(f"Chr {pair_id}{'A' if index % 2 == 0 else 'B'}", center + vector(0, 0.75, 0), height=8)
    chromosomes.append(chrom)
    return chrom


def build_scene():
    global nucleus, nucleus_shell, cytoplasm_boundary, title_label, status_label, ai_label, round_label
    nucleus = add_obj(sphere(pos=vector(0, 0, 0), radius=10.2, color=NUCLEUS_BLUE, opacity=0.11, shininess=0.25))
    nucleus_shell = add_obj(sphere(pos=vector(0, 0, 0), radius=10.35, color=vector(0.72, 0.84, 1.0), opacity=0.045, shininess=0.15))
    cytoplasm_boundary = add_obj(ring(pos=vector(0, -0.05, 0), axis=vector(0, 1, 0), radius=10.35, thickness=0.018, color=vector(0.48, 0.62, 0.95), opacity=0.35))
    title_label = make_label("Human genome mutation simulation", vector(0, 11.5, 0), height=16)
    round_label = make_label("", vector(-9.8, 10.2, 0), height=10)
    status_label = make_label("", vector(-9.8, 9.4, 0), height=9)
    ai_label = make_label("", vector(-9.8, 8.7, 0), height=9, color_value=vector(0.22, 0.28, 0.44))
    pair_count = 12
    for pair_id in range(1, pair_count + 1):
        theta = 2 * math.pi * pair_id / pair_count
        ring_radius = 5.4 + 0.8 * math.sin(pair_id * 1.7)
        base_center = vector(math.cos(theta) * ring_radius, random.uniform(-2.8, 2.8), math.sin(theta) * ring_radius)
        pair_offset = random_unit_vector() * 0.45
        length = random.uniform(3.1, 4.7)
        create_chromosome(pair_id * 2, pair_id, base_center - pair_offset, theta + 0.6, length)
        create_chromosome(pair_id * 2 + 1, pair_id, base_center + pair_offset, theta - 0.6, length * random.uniform(0.92, 1.06))
    make_label("Visible model: chromosome-pair regions inside a transparent nucleus\nMutations: S, DEL, INS, DUP | Repair enzymes attach, mark, repair, detach", vector(0, -11.2, 0), height=9, color_value=vector(0.20, 0.25, 0.33))
    for _ in range(5):
        spawn_repair_enzyme()


def destroy_all():
    for obj in objects_to_clear:
        try:
            obj.visible = False
            if hasattr(obj, "clear"):
                obj.clear()
        except Exception:
            pass
    objects_to_clear.clear()
    chromosomes.clear()
    mutations.clear()
    repair_enzymes.clear()
    particles.clear()
    ai_marks.clear()


def reset_simulation(new_round=False):
    global round_number, tick_count, sim_time, manual_override_timer, repair_burst_timer
    if new_round:
        round_number += 1
    tick_count = 0
    sim_time = 0.0
    manual_override_timer = 0.0
    repair_burst_timer = 0.0
    destroy_all()
    build_scene()
    ai.last_mutation_count = 0
    ai.last_repaired_count = 0
    ai.mode_timer = 0.0
    ai.decision_timer = 1.0
    ai.stagnation_timer = 0.0
    ai.loop_timer = 0.0
    ai.selected_chromosome = None


def pick_chromosome_by_damage(prefer_damage=True):
    if not chromosomes:
        return None
    if prefer_damage:
        total = sum(c.damage_load + 0.05 for c in chromosomes)
        r = random.uniform(0, total)
        acc = 0
        for c in chromosomes:
            acc += c.damage_load + 0.05
            if acc >= r:
                return c
    return random.choice(chromosomes)


def create_mutation(mtype=None, chrom=None):
    if not chromosomes:
        return None
    if mtype is None:
        mtype = random.choice(MUTATION_TYPES)
    if chrom is None:
        chrom = random.choice(chromosomes)
    base_index = random.randrange(len(chrom.base_positions))
    base_pos = chrom.base_positions[base_index]
    pos = base_pos + random_unit_vector() * random.uniform(0.24, 0.55)
    severity = random.uniform(0.35, 1.0)
    col = mutation_colors[mtype]
    marker = add_obj(sphere(pos=pos, radius=0.24, color=col, opacity=0.88, emissive=True))
    glow = add_obj(sphere(pos=pos, radius=0.52, color=col, opacity=0.12))
    label_obj = make_label(mutation_symbols[mtype], pos + vector(0, 0.55, 0), height=8, color_value=col)
    extra_parts = []
    if mtype == "deletion":
        extra_parts.append(add_obj(cylinder(pos=pos + vector(-0.20, -0.20, 0), axis=vector(0.40, 0.40, 0), radius=0.035, color=col)))
    elif mtype == "insertion":
        extra_parts.append(add_obj(sphere(pos=pos + vector(0, 0.28, 0), radius=0.13, color=col, opacity=0.95)))
        extra_parts.append(add_obj(cylinder(pos=pos, axis=vector(0, 0.28, 0), radius=0.025, color=col)))
    elif mtype == "duplication":
        extra_parts.append(add_obj(sphere(pos=pos + vector(0.25, 0.12, 0.0), radius=0.20, color=col, opacity=0.72)))
        extra_parts.append(add_obj(cylinder(pos=pos, axis=vector(0.25, 0.12, 0.0), radius=0.025, color=col, opacity=0.7)))
    elif mtype == "substitution":
        extra_parts.append(add_obj(sphere(pos=pos + vector(0.0, 0.30, 0.0), radius=0.09, color=vector(1, 1, 1), opacity=0.9)))
    mut = Mutation(mtype=mtype, chromosome=chrom, base_index=base_index, pos=pos, severity=severity, marker=marker, glow=glow, label_obj=label_obj, extra_parts=extra_parts)
    mutations.append(mut)
    chrom.mark_damage()
    spill_mutation_particles(pos, col, amount=8)
    return mut


def repair_mutation(mut, enzyme=None):
    if mut.repaired:
        return
    mut.repaired = True
    mut.chromosome.mark_repaired()
    if mut.label_obj:
        mut.label_obj.text = "fixed"
        mut.label_obj.color = REPAIRED_GREEN
    for part in mut.extra_parts:
        try:
            part.opacity = 0.18
            part.color = REPAIRED_GREEN
        except Exception:
            pass
    spill_mutation_particles(mut.pos, REPAIRED_GREEN, amount=12)
    create_ai_mark(mut.pos, "repair scar", REPAIRED_GREEN, life=3.5)
    mut.attached_enzyme = enzyme


def find_oldest_unrepaired_mutation():
    targets = [m for m in mutations if not m.repaired]
    return max(targets, key=lambda m: m.age) if targets else None


def find_nearest_unrepaired_to_origin():
    targets = [m for m in mutations if not m.repaired]
    return min(targets, key=lambda m: mag(m.pos)) if targets else None


def nearest_unrepaired_mutation(pos):
    targets = [m for m in mutations if not m.repaired and m.attached_enzyme is None]
    if not targets:
        targets = [m for m in mutations if not m.repaired]
    return min(targets, key=lambda m: mag(m.pos - pos)) if targets else None


def spawn_repair_enzyme(pos=None):
    if pos is None:
        pos = random_unit_vector() * random.uniform(1.0, 7.5)
    vel = random_unit_vector() * random.uniform(0.15, 0.45)
    body = add_obj(sphere(pos=pos, radius=0.20, color=REPAIR_GOLD, emissive=True, opacity=0.95))
    ring_obj = add_obj(ring(pos=pos, axis=vector(0, 1, 0), radius=0.32, thickness=0.022, color=REPAIR_GOLD, opacity=0.82))
    label_obj = make_label("repair", pos + vector(0, 0.42, 0), height=7, color_value=vector(0.55, 0.36, 0.02))
    enz = RepairEnzyme(pos=pos, vel=vel, body=body, ring_obj=ring_obj, label_obj=label_obj)
    repair_enzymes.append(enz)
    return enz


def update_repair_enzyme(enz, step_dt):
    if enz.target and enz.target.repaired:
        enz.target = None
        enz.mode = "patrol"
        enz.repair_progress = 0.0
    if enz.target is None:
        enz.target = nearest_unrepaired_mutation(enz.pos)
        if enz.target:
            enz.mode = "seek"
            enz.target.attached_enzyme = enz
    if enz.mode == "seek" and enz.target:
        direction = enz.target.pos - enz.pos
        dist = mag(direction)
        enz.vel += safe_norm(direction) * step_dt * 3.0
        enz.vel *= 0.94
        if mag(enz.vel) > 2.0:
            enz.vel = norm(enz.vel) * 2.0
        enz.pos += enz.vel * step_dt
        if dist < 0.45:
            enz.mode = "attached"
            enz.attach_timer = 0.0
            enz.repair_progress = 0.0
            create_ai_mark(enz.target.pos, "enzyme attached", REPAIR_GOLD, life=1.5)
    elif enz.mode == "attached" and enz.target:
        enz.attach_timer += step_dt
        enz.repair_progress += step_dt * (0.55 + 0.55 * (1.0 - enz.target.severity))
        enz.pos = enz.target.pos + vector(0, 0.24 + 0.06 * math.sin(sim_time * 18.0), 0)
        if enz.ring_obj:
            enz.ring_obj.radius = 0.32 + 0.08 * math.sin(sim_time * 12.0)
        if enz.repair_progress > 1.0:
            repair_mutation(enz.target, enz)
            enz.target.attached_enzyme = None
            enz.target = None
            enz.mode = "detach"
            enz.vel = random_unit_vector() * 0.8
    elif enz.mode == "detach":
        enz.pos += enz.vel * step_dt
        enz.vel *= 0.97
        if mag(enz.pos) > 8.5:
            enz.vel += safe_norm(-enz.pos) * step_dt * 2.0
        if mag(enz.vel) < 0.08:
            enz.mode = "patrol"
    else:
        enz.vel += random_unit_vector() * 0.08 * step_dt
        if mag(enz.pos) > 8.4:
            enz.vel += safe_norm(-enz.pos) * step_dt * 1.6
        enz.vel *= 0.985
        if mag(enz.vel) > 0.75:
            enz.vel = norm(enz.vel) * 0.75
        enz.pos += enz.vel * step_dt
    enz.update_visual()


def spill_mutation_particles(pos, col, amount=10):
    for _ in range(amount):
        p = pos + random_unit_vector() * random.uniform(0.02, 0.18)
        obj = add_obj(sphere(pos=p, radius=random.uniform(0.025, 0.055), color=col, opacity=0.75, emissive=True))
        particles.append(SparkParticle(pos=p, vel=random_unit_vector() * random.uniform(0.25, 1.3), age=0.0, life=random.uniform(0.8, 2.0), obj=obj))


def update_particles(step_dt):
    for p in list(particles):
        p.age += step_dt
        p.pos += p.vel * step_dt
        p.vel *= 0.96
        p.obj.pos = p.pos
        if p.fade:
            p.obj.opacity = max(0.0, 0.75 * (1.0 - p.age / p.life))
        if p.age >= p.life:
            p.obj.visible = False
            particles.remove(p)


def create_ai_mark(pos, text, col, life=3.0):
    ring_obj = add_obj(ring(pos=pos, axis=random_unit_vector(), radius=0.35, thickness=0.018, color=col, opacity=0.65))
    lab = make_label(text, pos + vector(0, 0.42, 0), height=7, color_value=col)
    mark = {"pos": pos, "ring": ring_obj, "label": lab, "age": 0.0, "life": life, "spin": random_unit_vector()}
    ai_marks.append(mark)
    return mark


def create_orbiting_marker(chrom):
    if not chrom:
        return
    for i in range(6):
        angle = i * math.pi / 3.0
        pos = chrom.center + vector(math.cos(angle), 0.2 * math.sin(angle * 2), math.sin(angle)) * 1.15
        create_ai_mark(pos, "copy wave", DUP_MAGENTA, life=3.5)


def update_ai_marks(step_dt):
    for mark in list(ai_marks):
        mark["age"] += step_dt
        pulse = 0.5 + 0.5 * math.sin(mark["age"] * 8.0)
        mark["ring"].radius = 0.25 + 0.25 * pulse + 0.08 * mark["age"]
        mark["ring"].opacity = max(0.0, 0.65 * (1.0 - mark["age"] / mark["life"]))
        mark["ring"].axis = rotate(mark["ring"].axis, angle=step_dt * 1.7, axis=mark["spin"])
        mark["label"].pos = mark["pos"] + vector(0, 0.42 + 0.04 * pulse, 0)
        if mark["age"] >= mark["life"]:
            mark["ring"].visible = False
            mark["label"].visible = False
            ai_marks.remove(mark)


def clear_faded_markers():
    for m in list(mutations):
        if m.repaired and m.age > 4.0:
            for obj in [m.marker, m.glow, m.label_obj] + m.extra_parts:
                try:
                    obj.visible = False
                except Exception:
                    pass
            mutations.remove(m)
    for mark in list(ai_marks):
        mark["ring"].visible = False
        mark["label"].visible = False
        ai_marks.remove(mark)


def handle_keydown(evt):
    global paused, ai_enabled, speed, manual_override_timer, repair_burst_timer
    key = evt.key.lower()
    manual_override_timer = 2.5
    if key == "a":
        ai.enabled = not ai.enabled
        ai_enabled = ai.enabled
    elif key == "p":
        paused = not paused
    elif key == "r":
        reset_simulation(new_round=False)
    elif key == "m":
        idx = ai.modes.index(ai.mode) if ai.mode in ai.modes else 0
        ai.mode = ai.modes[(idx + 1) % len(ai.modes)]
        ai.mode_timer = 0.0
    elif key == "1":
        create_mutation("substitution")
    elif key == "2":
        create_mutation("deletion")
    elif key == "3":
        create_mutation("insertion")
    elif key == "4":
        create_mutation("duplication")
    elif key == "5":
        create_mutation()
    elif key == "e":
        spawn_repair_enzyme()
    elif key == "c":
        clear_faded_markers()
    elif key == " ":
        repair_burst_timer = 3.0
        for _ in range(3):
            spawn_repair_enzyme()
    elif key in ["+", "="]:
        speed = min(4.0, speed + 0.25)
    elif key in ["-", "_"]:
        speed = max(0.25, speed - 0.25)
    elif key == "h":
        show_controls()


scene.bind("keydown", handle_keydown)


def update_status_labels():
    unresolved = sum(1 for m in mutations if not m.repaired)
    repaired = sum(1 for m in mutations if m.repaired)
    damage = sum(c.damage_load for c in chromosomes)
    round_label.text = f"Round {round_number} | genome regions: {len(chromosomes)} | speed {speed:.2f}x"
    status_label.text = f"mutations {len(mutations)} | unresolved {unresolved} | repaired {repaired} | enzymes {len(repair_enzymes)} | damage {damage:.1f}"
    ai_label.text = f"AI {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode} | {'PAUSED' if paused else 'running'}"


def update_chromosome_motion(step_dt):
    for c in chromosomes:
        bob = 0.018 * math.sin(sim_time * 0.9 + c.index * 0.4)
        sway = 0.014 * math.cos(sim_time * 0.7 + c.index)
        delta = vector(sway, bob, -sway * 0.6)
        c.center += delta * step_dt
        if c.halo:
            c.halo.pos = c.center
        if c.label_obj:
            c.label_obj.pos += delta * step_dt
        for part in c.parts:
            try:
                part.pos += delta * step_dt
            except Exception:
                pass
        for i in range(len(c.base_positions)):
            c.base_positions[i] += delta * step_dt


def update_mutations(step_dt):
    for m in list(mutations):
        m.age += step_dt
        if not m.repaired and random.random() < 0.00035:
            repair_mutation(m)
        m.update_visual()


def update_repair_burst(step_dt):
    global repair_burst_timer
    if repair_burst_timer > 0:
        repair_burst_timer -= step_dt
        target = find_oldest_unrepaired_mutation()
        if target and random.random() < 0.10:
            spawn_repair_enzyme(pos=target.pos + random_unit_vector() * 1.2)
            create_ai_mark(target.pos, "burst", REPAIR_GOLD, life=1.2)


def natural_mutation_background(step_dt):
    if random.random() < 0.0035 * speed:
        create_mutation(random.choice(MUTATION_TYPES))


build_scene()
show_controls()

while True:
    rate(60)
    if paused:
        update_status_labels()
        continue
    step_dt = dt * speed
    sim_time += step_dt
    tick_count += 1
    if manual_override_timer > 0:
        manual_override_timer -= step_dt
    update_chromosome_motion(step_dt)
    natural_mutation_background(step_dt)
    if ai.enabled and manual_override_timer <= 0:
        ai.update(step_dt)
    update_repair_burst(step_dt)
    for enz in list(repair_enzymes):
        update_repair_enzyme(enz, step_dt)
    update_mutations(step_dt)
    update_particles(step_dt)
    update_ai_marks(step_dt)
    if len(mutations) > 42:
        repaired_old = [m for m in mutations if m.repaired]
        for m in repaired_old[:max(0, len(mutations) - 34)]:
            for obj in [m.marker, m.glow, m.label_obj] + m.extra_parts:
                try:
                    obj.visible = False
                except Exception:
                    pass
            mutations.remove(m)
    update_status_labels()
