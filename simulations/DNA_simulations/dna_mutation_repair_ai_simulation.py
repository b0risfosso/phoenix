"""
DNA Mutation and Repair System — 3D VPython Simulation
======================================================

A self-contained VPython simulation of DNA mismatch detection and repair.

Run:
    pip install vpython
    python dna_mutation_repair_ai_simulation.py

Keyboard controls:
    H       print controls
    A       toggle expressive AI on/off
    P       pause/resume simulation
    O       one human override repair pulse
    M       introduce a new mismatch
    R       reset the whole simulation
    1       AI mode: scan
    2       AI mode: inspect
    3       AI mode: excise
    4       AI mode: replace
    5       AI mode: verify
    6       AI mode: playful orbit
    7       AI mode: chaotic mutation
    8       AI mode: artistic marking

The simulation includes:
- DNA double helix backbones and paired bases.
- Correct and mismatched base pairs.
- Repair enzymes that scan, mark, attach, detach, excise, replace, collide, orbit, spill particles,
  wrap around the helix, verify repaired sites, and loop into new rounds.
- A simple rule-based controller and a more expressive AI behavior system.
- Human keyboard override while AI is running.

This is a conceptual educational simulation, not a biochemical model.
"""

from vpython import *
from math import sin, cos, pi, atan2
from random import random, uniform, choice, randint

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="DNA Mutation and Repair System — AI Controlled VPython Simulation",
    width=1280,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, -13.5, 7.6)
scene.camera.axis = vector(0, 13.5, -7.0)
scene.forward = vector(0, 1, -0.35)

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

COLORS = {
    "A": vector(0.28, 0.58, 1.00),   # adenine blue
    "T": vector(1.00, 0.58, 0.25),   # thymine orange
    "G": vector(0.32, 0.78, 0.40),   # guanine green
    "C": vector(0.84, 0.38, 0.85),   # cytosine purple
    "damaged": vector(1.0, 0.20, 0.18),
    "repair": vector(0.10, 0.72, 0.80),
    "enzyme": vector(0.20, 0.65, 0.95),
    "mark": vector(1.0, 0.88, 0.15),
    "backbone": vector(0.70, 0.73, 0.80),
    "shadow": vector(0.80, 0.84, 0.90),
    "rna": vector(0.9, 0.55, 0.1),
    "white": vector(1, 1, 1),
    "black": vector(0.15, 0.16, 0.18),
    "gray": vector(0.58, 0.62, 0.70),
}

BASE_COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G"}
BASES = ["A", "T", "G", "C"]

# ------------------------------------------------------------
# Global settings and state
# ------------------------------------------------------------

NUM_PAIRS = 34
HELIX_RADIUS = 1.55
HELIX_TWIST = 0.58
PAIR_SPACING = 0.34
HELIX_LENGTH = (NUM_PAIRS - 1) * PAIR_SPACING
Z_OFFSET = -HELIX_LENGTH / 2

running = True
ai_enabled = True
human_override_timer = 0.0
sim_time = 0.0
round_index = 1
last_change_time = 0.0
completion_hold = 0.0
status_message = None

objects_to_clear = []
dna_pairs = []
enzymes = []
free_nucleotides = []
particles = []
repair_marks = []
status_labels = []
floating_notes = []
sensors = []


# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def clamp(x, low, high):
    return max(low, min(high, x))


def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)


def smoothstep(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def random_base_except(base):
    choices = [b for b in BASES if b != base]
    return choice(choices)


def helix_center_for_index(i):
    z = Z_OFFSET + i * PAIR_SPACING
    return vector(0, 0, z)


def helix_angle_for_index(i):
    return i * HELIX_TWIST


def helix_positions(i):
    angle = helix_angle_for_index(i)
    z = Z_OFFSET + i * PAIR_SPACING
    p1 = vector(HELIX_RADIUS * cos(angle), HELIX_RADIUS * sin(angle), z)
    p2 = vector(-HELIX_RADIUS * cos(angle), -HELIX_RADIUS * sin(angle), z)
    return p1, p2


def add_obj(obj):
    objects_to_clear.append(obj)
    return obj


def clear_scene_objects():
    global objects_to_clear, dna_pairs, enzymes, free_nucleotides, particles, repair_marks, status_labels, floating_notes, sensors

    for obj in objects_to_clear:
        try:
            obj.visible = False
        except Exception:
            pass

    objects_to_clear = []
    dna_pairs = []
    enzymes = []
    free_nucleotides = []
    particles = []
    repair_marks = []
    status_labels = []
    floating_notes = []
    sensors = []


def make_label(text, pos, height=12, color_value=None, box=False, opacity=0.0):
    if color_value is None:
        color_value = COLORS["black"]
    lbl = label(
        pos=pos,
        text=text,
        height=height,
        color=color_value,
        box=box,
        opacity=opacity,
        border=4,
        font="sans",
    )
    return add_obj(lbl)


def set_status(text):
    global status_message
    if status_message is not None:
        status_message.text = text


# ------------------------------------------------------------
# Visual classes
# ------------------------------------------------------------

class DNApair:
    def __init__(self, index, left_base, right_base, mismatch=False):
        self.index = index
        self.correct_left = left_base
        self.correct_right = BASE_COMPLEMENT[left_base]
        self.left_base = left_base
        self.right_base = right_base
        self.mismatch = mismatch
        self.damaged_side = "right" if mismatch else None
        self.state = "damaged" if mismatch else "healthy"
        self.marked = False
        self.excised = False
        self.repaired = False
        self.scan_score = 0.0
        self.repair_progress = 0.0
        self.last_touched = 0.0

        p1, p2 = helix_positions(index)
        self.left_pos = p1
        self.right_pos = p2
        self.center = (p1 + p2) * 0.5
        axis = p2 - p1

        # backbone nodes
        self.left_backbone = add_obj(sphere(
            pos=p1,
            radius=0.115,
            color=COLORS["backbone"],
            opacity=0.82,
        ))
        self.right_backbone = add_obj(sphere(
            pos=p2,
            radius=0.115,
            color=COLORS["backbone"],
            opacity=0.82,
        ))

        # base rungs
        self.rung = add_obj(cylinder(
            pos=p1,
            axis=axis,
            radius=0.028,
            color=COLORS["shadow"],
            opacity=0.55,
        ))

        # base spheres
        self.left_sphere = add_obj(sphere(
            pos=p1 * 0.70 + p2 * 0.30,
            radius=0.145,
            color=COLORS[left_base],
            opacity=0.95,
            shininess=0.65,
        ))
        self.right_sphere = add_obj(sphere(
            pos=p1 * 0.30 + p2 * 0.70,
            radius=0.145,
            color=COLORS[right_base] if not mismatch else COLORS["damaged"],
            opacity=0.95,
            shininess=0.65,
        ))

        self.left_label = make_label(left_base, self.left_sphere.pos + vector(0, 0, 0.18), 8, COLORS["black"])
        self.right_label = make_label(right_base, self.right_sphere.pos + vector(0, 0, 0.18), 8, COLORS["black"])

        # mismatch visual marker
        self.damage_ring = add_obj(ring(
            pos=self.right_sphere.pos,
            axis=norm(axis),
            radius=0.22,
            thickness=0.018,
            color=COLORS["damaged"],
            opacity=0.0 if not mismatch else 0.80,
        ))

        self.glow = add_obj(sphere(
            pos=self.center,
            radius=0.23,
            color=COLORS["mark"],
            opacity=0.0,
        ))

    def expected_right(self):
        return BASE_COMPLEMENT[self.left_base]

    def target_pos_for_side(self, side):
        if side == "left":
            return self.left_sphere.pos
        return self.right_sphere.pos

    def is_mismatched(self):
        return self.right_base != BASE_COMPLEMENT[self.left_base] or self.state in ["damaged", "marked", "excised"]

    def mark(self):
        global last_change_time
        if not self.marked:
            self.marked = True
            self.state = "marked"
            self.glow.opacity = 0.35
            self.damage_ring.opacity = 0.95
            last_change_time = sim_time
            make_repair_mark(self.index, "Mismatch marked")

    def excise(self):
        global last_change_time
        if self.state in ["damaged", "marked"] and not self.excised:
            self.excised = True
            self.state = "excised"
            self.right_sphere.opacity = 0.18
            self.right_label.text = "?"
            self.rung.opacity = 0.22
            self.damage_ring.opacity = 0.65
            last_change_time = sim_time
            spill_particles(self.right_sphere.pos, COLORS["damaged"], count=8, speed=0.8)
            make_repair_mark(self.index, "Damaged base removed")

    def replace(self):
        global last_change_time
        if self.excised:
            self.right_base = self.expected_right()
            self.right_sphere.color = COLORS[self.right_base]
            self.right_sphere.opacity = 0.97
            self.right_label.text = self.right_base
            self.rung.opacity = 0.62
            self.excised = False
            self.repaired = True
            self.mismatch = False
            self.state = "repaired"
            self.damage_ring.opacity = 0.12
            self.glow.color = COLORS["repair"]
            self.glow.opacity = 0.32
            last_change_time = sim_time
            spill_particles(self.right_sphere.pos, COLORS["repair"], count=14, speed=0.55)
            make_repair_mark(self.index, "Correct base inserted")

    def verify(self):
        global last_change_time
        if self.state == "repaired":
            self.state = "healthy"
            self.marked = False
            self.repaired = False
            self.glow.opacity = 0.0
            self.damage_ring.opacity = 0.0
            self.rung.opacity = 0.55
            last_change_time = sim_time
            make_repair_mark(self.index, "Repair verified")

    def mutate(self):
        global last_change_time
        new_base = random_base_except(self.expected_right())
        self.right_base = new_base
        self.right_sphere.color = COLORS["damaged"]
        self.right_sphere.opacity = 1.0
        self.right_label.text = new_base
        self.mismatch = True
        self.damaged_side = "right"
        self.state = "damaged"
        self.marked = False
        self.excised = False
        self.repaired = False
        self.damage_ring.opacity = 0.80
        self.glow.color = COLORS["damaged"]
        self.glow.opacity = 0.24
        self.rung.opacity = 0.45
        last_change_time = sim_time
        spill_particles(self.right_sphere.pos, COLORS["damaged"], count=10, speed=0.9)
        make_repair_mark(self.index, "New mutation formed")

    def update(self, t):
        # Subtle breathing and mismatch flashing
        phase = t * 2.2 + self.index * 0.2
        breathe = 1.0 + 0.035 * sin(phase)
        self.left_sphere.radius = 0.145 * breathe
        self.right_sphere.radius = 0.145 * breathe

        if self.state in ["damaged", "marked", "excised"]:
            pulse = 0.55 + 0.45 * sin(t * 5.2 + self.index)
            self.damage_ring.opacity = 0.45 + 0.45 * max(0, pulse)
            self.glow.opacity = 0.12 + 0.28 * max(0, pulse)
        elif self.state == "repaired":
            self.glow.opacity = max(0.0, self.glow.opacity - 0.004)
            self.damage_ring.opacity = max(0.0, self.damage_ring.opacity - 0.004)


class FreeNucleotide:
    def __init__(self, base, pos=None):
        self.base = base
        self.bound = False
        self.target_pair = None
        self.timer = uniform(0, 100)
        if pos is None:
            pos = vector(uniform(-4.0, 4.0), uniform(-3.2, 3.2), uniform(Z_OFFSET - 1, -Z_OFFSET + 1))
        self.body = add_obj(sphere(
            pos=pos,
            radius=0.125,
            color=COLORS[base],
            opacity=0.78,
            shininess=0.6,
            make_trail=True,
            retain=18,
            trail_radius=0.008,
        ))
        self.lbl = make_label(base, pos + vector(0, 0, 0.19), 7, COLORS["black"])

    @property
    def pos(self):
        return self.body.pos

    @pos.setter
    def pos(self, value):
        self.body.pos = value
        self.lbl.pos = value + vector(0, 0, 0.19)

    def move_to(self, target, dt, speed=1.0):
        self.pos = self.pos + (target - self.pos) * clamp(dt * speed, 0.0, 0.2)

    def update(self, dt, t):
        if self.bound:
            return
        self.timer += dt
        # Gentle Brownian/orbital motion around the helix volume
        drift = vector(
            0.025 * sin(t * 1.3 + self.timer * 0.7),
            0.025 * cos(t * 1.7 + self.timer * 0.5),
            0.020 * sin(t * 0.9 + self.timer),
        )
        self.pos = self.pos + drift

        # Wrap in a loose tube around DNA
        if self.pos.z > -Z_OFFSET + 1.2:
            self.pos = vector(self.pos.x, self.pos.y, Z_OFFSET - 1.2)
        if self.pos.z < Z_OFFSET - 1.2:
            self.pos = vector(self.pos.x, self.pos.y, -Z_OFFSET + 1.2)

        r = mag(vector(self.pos.x, self.pos.y, 0))
        if r > 5.2:
            self.pos = vector(self.pos.x * 0.86, self.pos.y * 0.86, self.pos.z)


class Particle:
    def __init__(self, pos, color_value, vel=None, radius=0.035, life=1.8):
        self.life = life
        self.age = 0.0
        if vel is None:
            vel = vector(uniform(-1, 1), uniform(-1, 1), uniform(-1, 1)) * uniform(0.2, 0.9)
        self.vel = vel
        self.body = add_obj(sphere(
            pos=pos,
            radius=radius,
            color=color_value,
            opacity=0.7,
            make_trail=True,
            retain=8,
            trail_radius=0.004,
        ))

    def update(self, dt):
        self.age += dt
        self.vel *= 0.985
        self.body.pos += self.vel * dt
        self.body.opacity = max(0.0, 0.7 * (1 - self.age / self.life))
        if self.age >= self.life:
            self.body.visible = False
            return False
        return True


class RepairMark:
    def __init__(self, pair_index, text):
        p = dna_pairs[pair_index].center + vector(0, -2.05, 0.0)
        self.age = 0.0
        self.life = 5.0
        self.body = add_obj(sphere(pos=p, radius=0.055, color=COLORS["mark"], opacity=0.85))
        self.lbl = make_label(text, p + vector(0, -0.1, 0.16), 7, COLORS["black"])

    def update(self, dt):
        self.age += dt
        self.body.radius = 0.055 + 0.012 * sin(self.age * 5)
        self.body.opacity = max(0.0, 0.85 * (1 - self.age / self.life))
        self.lbl.opacity = max(0.0, 1 - self.age / self.life)
        if self.age >= self.life:
            self.body.visible = False
            self.lbl.visible = False
            return False
        return True


class FloatingNote:
    def __init__(self, text, pos, color_value=None):
        if color_value is None:
            color_value = COLORS["black"]
        self.age = 0.0
        self.life = 2.8
        self.lbl = make_label(text, pos, 10, color_value, box=True, opacity=0.12)

    def update(self, dt):
        self.age += dt
        self.lbl.pos += vector(0, 0.015, 0.018)
        fade = max(0.0, 1 - self.age / self.life)
        self.lbl.opacity = 0.12 * fade
        if self.age >= self.life:
            self.lbl.visible = False
            return False
        return True


def spill_particles(pos, color_value, count=8, speed=0.6):
    for _ in range(count):
        vel = vector(uniform(-1, 1), uniform(-1, 1), uniform(-0.6, 0.6))
        if mag(vel) < 0.01:
            vel = vector(1, 0, 0)
        particles.append(Particle(pos, color_value, norm(vel) * uniform(0.15, speed), radius=uniform(0.018, 0.045), life=uniform(0.9, 2.2)))


def make_repair_mark(pair_index, text):
    repair_marks.append(RepairMark(pair_index, text))


def make_note(text, pos, color_value=None):
    floating_notes.append(FloatingNote(text, pos, color_value))


# ------------------------------------------------------------
# Enzyme and AI classes
# ------------------------------------------------------------

class RepairEnzyme:
    def __init__(self, name, color_value, offset_angle=0.0):
        self.name = name
        self.offset_angle = offset_angle
        self.index_pos = uniform(0, NUM_PAIRS - 1)
        self.target_index = None
        self.mode = "scan"
        self.attached_pair = None
        self.action_timer = 0.0
        self.speed = uniform(4.5, 7.5)
        self.orbit_radius = HELIX_RADIUS + 0.72
        self.body = add_obj(sphere(
            pos=self.position_from_index(self.index_pos, 0),
            radius=0.24,
            color=color_value,
            opacity=0.92,
            shininess=0.7,
            make_trail=True,
            retain=42,
            trail_radius=0.014,
        ))
        self.core = add_obj(sphere(
            pos=self.body.pos,
            radius=0.10,
            color=COLORS["white"],
            opacity=0.7,
        ))
        self.sensor = add_obj(ring(
            pos=self.body.pos,
            axis=vector(0, 0, 1),
            radius=0.36,
            thickness=0.016,
            color=color_value,
            opacity=0.45,
        ))
        self.lbl = make_label(name, self.body.pos + vector(0, 0, 0.38), 8, COLORS["black"])

    def position_from_index(self, idx, t):
        i = clamp(idx, 0, NUM_PAIRS - 1)
        z = Z_OFFSET + i * PAIR_SPACING
        angle = i * HELIX_TWIST + self.offset_angle + 0.22 * sin(t * 1.4 + self.offset_angle)
        return vector(
            self.orbit_radius * cos(angle),
            self.orbit_radius * sin(angle),
            z,
        )

    def set_mode(self, mode):
        self.mode = mode
        self.action_timer = 0.0

    def move_to_index(self, target_index, dt, t):
        target_index = clamp(target_index, 0, NUM_PAIRS - 1)
        delta = target_index - self.index_pos
        step = clamp(delta, -self.speed * dt, self.speed * dt)
        self.index_pos += step
        self.body.pos = self.position_from_index(self.index_pos, t)
        self.update_parts(t)
        return abs(delta) < 0.12

    def update_parts(self, t):
        self.core.pos = self.body.pos + vector(0, 0, 0.015 * sin(t * 8))
        self.sensor.pos = self.body.pos
        self.sensor.axis = norm(vector(self.body.pos.x, self.body.pos.y, 0.15))
        self.sensor.radius = 0.34 + 0.04 * sin(t * 4 + self.offset_angle)
        self.lbl.pos = self.body.pos + vector(0, 0, 0.38)

    def scan_step(self, dt, t):
        self.index_pos += self.speed * 0.22 * dt
        if self.index_pos >= NUM_PAIRS:
            self.index_pos = 0
        self.body.pos = self.position_from_index(self.index_pos, t)
        self.update_parts(t)

        nearest = int(round(self.index_pos))
        if 0 <= nearest < NUM_PAIRS:
            pair = dna_pairs[nearest]
            pair.scan_score = min(1.0, pair.scan_score + dt * 0.8)
            if pair.is_mismatched() and pair.state == "damaged":
                pair.mark()
                self.target_index = nearest
                self.set_mode("inspect")
                make_note(f"{self.name}: anomaly found", pair.center + vector(0, -2.8, 0.7), COLORS["damaged"])

    def attach_to_pair(self, pair_index, dt, t):
        pair = dna_pairs[pair_index]
        target = pair.center + norm(self.position_from_index(pair_index, t) - pair.center) * 0.88
        self.body.pos = self.body.pos + (target - self.body.pos) * clamp(dt * 5.0, 0.0, 0.22)
        self.index_pos += (pair_index - self.index_pos) * clamp(dt * 5.0, 0.0, 0.18)
        self.update_parts(t)
        return mag(self.body.pos - target) < 0.08

    def orbit_pair(self, pair_index, dt, t, radius=1.05, vertical=0.18):
        pair = dna_pairs[pair_index]
        self.action_timer += dt
        angle = t * 2.6 + self.offset_angle
        target = pair.center + vector(radius * cos(angle), radius * sin(angle), vertical * sin(angle * 2))
        self.body.pos = self.body.pos + (target - self.body.pos) * clamp(dt * 4.5, 0.0, 0.25)
        self.index_pos += (pair_index - self.index_pos) * clamp(dt * 4.5, 0.0, 0.20)
        self.update_parts(t)

    def perform_repair_sequence(self, dt, t):
        if self.target_index is None:
            self.set_mode("scan")
            return

        pair = dna_pairs[self.target_index]
        self.action_timer += dt

        if self.mode == "inspect":
            arrived = self.attach_to_pair(self.target_index, dt, t)
            if arrived and self.action_timer > 0.8:
                pair.mark()
                self.set_mode("excise")
                self.action_timer = 0.0

        elif self.mode == "excise":
            self.orbit_pair(self.target_index, dt, t, radius=0.95)
            if self.action_timer > 1.05:
                pair.excise()
                self.set_mode("replace")
                self.action_timer = 0.0

        elif self.mode == "replace":
            self.orbit_pair(self.target_index, dt, t, radius=1.12)
            target_base = pair.expected_right()
            matching = find_free_nucleotide(target_base, pair.right_sphere.pos)
            if matching is not None:
                matching.bound = True
                matching.move_to(pair.right_sphere.pos + vector(0, 0, 0.05), dt, speed=3.0)
                if mag(matching.pos - pair.right_sphere.pos) < 0.12 or self.action_timer > 2.0:
                    matching.body.visible = False
                    matching.lbl.visible = False
                    pair.replace()
                    self.set_mode("verify")
                    self.action_timer = 0.0
                    spawn_free_nucleotide()
            elif self.action_timer > 1.0:
                pair.replace()
                self.set_mode("verify")
                self.action_timer = 0.0

        elif self.mode == "verify":
            self.orbit_pair(self.target_index, dt, t, radius=1.28)
            if self.action_timer > 1.1:
                pair.verify()
                self.target_index = None
                self.set_mode("scan")
                self.action_timer = 0.0

    def update(self, dt, t):
        if self.mode == "scan":
            self.scan_step(dt, t)
        elif self.mode in ["inspect", "excise", "replace", "verify"]:
            self.perform_repair_sequence(dt, t)
        elif self.mode == "playful_orbit":
            target = self.target_index if self.target_index is not None else int((NUM_PAIRS - 1) * (0.5 + 0.5 * sin(t * 0.17)))
            self.orbit_pair(target, dt, t, radius=1.45 + 0.2 * sin(t))
        elif self.mode == "artistic_mark":
            self.scan_step(dt * 0.6, t)
            if random() < 0.025:
                idx = randint(0, NUM_PAIRS - 1)
                make_repair_mark(idx, "AI trace pattern")
        elif self.mode == "chaotic_mutation":
            self.scan_step(dt * 1.7, t)


class ExpressiveAIController:
    """
    A simple state-machine AI that can:
    - Read simulation state.
    - Choose actions.
    - Control one or more repair enzymes.
    - Switch modes over time.
    - Detect completion/stagnation.
    - Reset and start new rounds.
    """

    def __init__(self):
        self.enabled = True
        self.mode = "scan"
        self.mode_timer = 0.0
        self.last_mode_switch = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.previous_signature = None
        self.round_cooldown = 0.0
        self.override_timer = 0.0
        self.modes = [
            "scan",
            "inspect",
            "excise",
            "replace",
            "verify",
            "playful_orbit",
            "chaotic_mutation",
            "artistic_mark",
            "careful_patrol",
            "curious_probe",
        ]

    def read_state(self):
        damaged = [p for p in dna_pairs if p.state == "damaged"]
        marked = [p for p in dna_pairs if p.state == "marked"]
        excised = [p for p in dna_pairs if p.state == "excised"]
        repaired = [p for p in dna_pairs if p.state == "repaired"]
        healthy = [p for p in dna_pairs if not p.is_mismatched() and p.state == "healthy"]
        signature = (
            len(damaged),
            len(marked),
            len(excised),
            len(repaired),
            len(healthy),
            sum(1 for n in free_nucleotides if not n.bound),
        )
        return {
            "damaged": damaged,
            "marked": marked,
            "excised": excised,
            "repaired": repaired,
            "healthy": healthy,
            "signature": signature,
            "all_complete": len(damaged) + len(marked) + len(excised) + len(repaired) == 0,
            "active_repairs": len(marked) + len(excised) + len(repaired),
        }

    def choose_mode(self, state, dt, t):
        self.mode_timer += dt

        if self.previous_signature == state["signature"]:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = 0.0
            self.previous_signature = state["signature"]

        if state["all_complete"]:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

        # Completion: celebrate, then loop into a new mutation round.
        if self.completion_timer > 5.5:
            self.mode = "playful_orbit"
            self.round_cooldown += dt
            if self.round_cooldown > 2.0:
                introduce_mutation_burst(count=randint(2, 5))
                self.round_cooldown = 0.0
                self.completion_timer = 0.0
                self.mode = "scan"
                make_note("New repair round begins", vector(0, -3.8, -Z_OFFSET + 0.6), COLORS["repair"])
            return self.mode

        # Stagnation: shake the scene by spawning bases or adding a small mutation.
        if self.stagnation_timer > 7.5:
            self.mode = choice(["curious_probe", "artistic_mark", "chaotic_mutation"])
            if random() < 0.45:
                spawn_free_nucleotide()
            if random() < 0.25 and state["all_complete"]:
                introduce_mutation_burst(count=1)
            self.stagnation_timer = 0.0
            return self.mode

        # React to current repair phase.
        if state["excised"]:
            self.mode = "replace"
        elif state["marked"]:
            self.mode = "excise"
        elif state["damaged"]:
            self.mode = "inspect"
        elif state["repaired"]:
            self.mode = "verify"
        elif self.mode_timer > uniform(3.5, 7.0):
            self.mode = choice(["scan", "careful_patrol", "playful_orbit", "artistic_mark"])
            self.mode_timer = 0.0

        return self.mode

    def assign_actions(self, state, dt, t):
        if not enzymes:
            return

        # Prioritize concrete repair tasks first.
        targets = []
        if state["excised"]:
            targets = [p.index for p in state["excised"]]
            desired = "replace"
        elif state["marked"]:
            targets = [p.index for p in state["marked"]]
            desired = "excise"
        elif state["damaged"]:
            targets = [p.index for p in state["damaged"]]
            desired = "inspect"
        elif state["repaired"]:
            targets = [p.index for p in state["repaired"]]
            desired = "verify"
        else:
            targets = []
            desired = self.mode

        for e_i, enzyme in enumerate(enzymes):
            if targets:
                enzyme.target_index = targets[e_i % len(targets)]
                enzyme.set_mode(desired)
            else:
                if self.mode == "careful_patrol":
                    enzyme.target_index = int((NUM_PAIRS - 1) * ((e_i + 1) / (len(enzymes) + 1)))
                    enzyme.set_mode("playful_orbit")
                    enzyme.speed = 3.2
                elif self.mode == "curious_probe":
                    enzyme.target_index = randint(0, NUM_PAIRS - 1)
                    enzyme.set_mode("playful_orbit")
                    if random() < 0.015:
                        make_note("AI probe", dna_pairs[enzyme.target_index].center + vector(0, -2.6, 0.6), COLORS["enzyme"])
                elif self.mode == "playful_orbit":
                    enzyme.target_index = int((NUM_PAIRS - 1) * (0.5 + 0.5 * sin(t * 0.25 + e_i)))
                    enzyme.set_mode("playful_orbit")
                elif self.mode == "artistic_mark":
                    enzyme.set_mode("artistic_mark")
                elif self.mode == "chaotic_mutation":
                    enzyme.set_mode("chaotic_mutation")
                    if random() < 0.012:
                        introduce_single_mutation()
                else:
                    enzyme.set_mode("scan")
                    enzyme.speed = 5.5 + e_i * 0.7

    def update(self, dt, t):
        if not self.enabled:
            return
        state = self.read_state()
        self.choose_mode(state, dt, t)
        self.assign_actions(state, dt, t)
        set_status(status_text(state, self.mode))


ai_controller = ExpressiveAIController()


# ------------------------------------------------------------
# DNA and scene construction
# ------------------------------------------------------------

def build_backbone_curves():
    left_points = []
    right_points = []
    for i in range(NUM_PAIRS):
        p1, p2 = helix_positions(i)
        left_points.append(p1)
        right_points.append(p2)

    c1 = curve(pos=left_points, radius=0.035, color=COLORS["backbone"], opacity=0.78)
    c2 = curve(pos=right_points, radius=0.035, color=COLORS["backbone"], opacity=0.78)
    add_obj(c1)
    add_obj(c2)


def build_dna(initial_mutations=None):
    if initial_mutations is None:
        initial_mutations = [6, 13, 22, 29]

    build_backbone_curves()

    seq = []
    for i in range(NUM_PAIRS):
        seq.append(choice(BASES))

    for i, left in enumerate(seq):
        right = BASE_COMPLEMENT[left]
        mismatch = i in initial_mutations
        if mismatch:
            right = random_base_except(BASE_COMPLEMENT[left])
        pair = DNApair(i, left, right, mismatch=mismatch)
        dna_pairs.append(pair)

    # Stationary reference rails and labels
    add_obj(box(pos=vector(0, 0, Z_OFFSET - 0.45), size=vector(4.5, 0.025, 0.025), color=COLORS["gray"], opacity=0.18))
    add_obj(box(pos=vector(0, 0, -Z_OFFSET + 0.45), size=vector(4.5, 0.025, 0.025), color=COLORS["gray"], opacity=0.18))
    make_label("mismatched bases glow red/yellow", vector(-4.8, -3.4, -Z_OFFSET + 0.8), 11, COLORS["black"], box=True, opacity=0.08)
    make_label("repair enzymes scan, attach, excise, replace, verify", vector(-4.8, -3.4, -Z_OFFSET + 0.35), 11, COLORS["black"], box=True, opacity=0.08)


def build_enzyme_team():
    enzymes.append(RepairEnzyme("MutS scanner", COLORS["enzyme"], offset_angle=0.0))
    enzymes.append(RepairEnzyme("Excision enzyme", vector(0.15, 0.78, 0.55), offset_angle=2.1))
    enzymes.append(RepairEnzyme("Polymerase patcher", vector(0.70, 0.55, 1.0), offset_angle=4.2))


def spawn_free_nucleotide(base=None, pos=None):
    if base is None:
        base = choice(BASES)
    free_nucleotides.append(FreeNucleotide(base, pos))


def build_free_nucleotide_pool(count=34):
    for _ in range(count):
        spawn_free_nucleotide()


def find_free_nucleotide(base, near_pos):
    candidates = [n for n in free_nucleotides if (not n.bound) and n.base == base and n.body.visible]
    if not candidates:
        spawn_free_nucleotide(base)
        candidates = [free_nucleotides[-1]]
    return min(candidates, key=lambda n: mag(n.pos - near_pos))


def make_status_panel():
    global status_message
    add_obj(box(pos=vector(0, -4.25, -Z_OFFSET + 1.35), size=vector(9.5, 0.08, 0.58), color=vector(0.90, 0.94, 1.0), opacity=0.55))
    status_message = make_label(
        "AI mode: scan | mutations active",
        vector(0, -4.32, -Z_OFFSET + 1.42),
        12,
        COLORS["black"],
        box=False,
        opacity=0,
    )


def build_scene():
    global last_change_time
    clear_scene_objects()
    build_dna()
    build_enzyme_team()
    build_free_nucleotide_pool()
    make_status_panel()
    last_change_time = sim_time
    set_status("AI mode: scan | DNA repair round ready")


# ------------------------------------------------------------
# Mutation, reset, loop, and state helpers
# ------------------------------------------------------------

def unresolved_pairs():
    return [p for p in dna_pairs if p.is_mismatched() or p.state in ["damaged", "marked", "excised", "repaired"]]


def introduce_single_mutation():
    healthy = [p for p in dna_pairs if not p.is_mismatched() and p.state == "healthy"]
    if not healthy:
        return
    pair = choice(healthy)
    pair.mutate()
    make_note("mutation introduced", pair.center + vector(0, -2.8, 0.55), COLORS["damaged"])


def introduce_mutation_burst(count=3):
    for _ in range(count):
        introduce_single_mutation()


def status_text(state=None, mode=None):
    if state is None:
        state = ai_controller.read_state()
    if mode is None:
        mode = ai_controller.mode
    return (
        f"Round {round_index} | AI {'on' if ai_controller.enabled else 'off'} | "
        f"mode: {mode} | damaged:{len(state['damaged'])} marked:{len(state['marked'])} "
        f"excised:{len(state['excised'])} repaired:{len(state['repaired'])} | "
        f"free bases:{sum(1 for n in free_nucleotides if not n.bound)}"
    )


def reset_simulation(new_round=True):
    global round_index, sim_time, last_change_time
    if new_round:
        round_index += 1
    build_scene()
    ai_controller.mode = "scan"
    ai_controller.mode_timer = 0.0
    ai_controller.stagnation_timer = 0.0
    ai_controller.completion_timer = 0.0
    ai_controller.round_cooldown = 0.0
    make_note("reset / new DNA repair round", vector(0, -3.8, -Z_OFFSET + 0.7), COLORS["repair"])
    last_change_time = sim_time


def human_override_repair_pulse():
    global human_override_timer
    human_override_timer = 2.0
    targets = unresolved_pairs()
    if not targets:
        introduce_mutation_burst(count=2)
        return

    target = targets[0]
    target.mark()
    if target.state == "marked":
        target.excise()
    elif target.state == "excised":
        target.replace()
    elif target.state == "repaired":
        target.verify()

    for e in enzymes:
        e.target_index = target.index
        e.set_mode("playful_orbit")
    make_note("human override pulse", target.center + vector(0, -2.9, 0.75), COLORS["mark"])


# ------------------------------------------------------------
# Keyboard controls
# ------------------------------------------------------------

def print_controls():
    print(__doc__)


def keydown(evt):
    global running, ai_enabled
    k = evt.key.lower()

    if k == "h":
        print_controls()
    elif k == "p":
        running = not running
        make_note("paused" if not running else "resumed", vector(0, -3.7, -ZOFFSET_SAFE(), 0) if False else vector(0, -3.7, -Z_OFFSET + 0.7), COLORS["black"])
    elif k == "a":
        ai_controller.enabled = not ai_controller.enabled
        make_note(f"AI {'enabled' if ai_controller.enabled else 'disabled'}", vector(0, -3.7, -Z_OFFSET + 0.7), COLORS["enzyme"])
    elif k == "o":
        human_override_repair_pulse()
    elif k == "m":
        introduce_single_mutation()
    elif k == "r":
        reset_simulation(new_round=True)
    elif k in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        modes = {
            "1": "scan",
            "2": "inspect",
            "3": "excise",
            "4": "replace",
            "5": "verify",
            "6": "playful_orbit",
            "7": "chaotic_mutation",
            "8": "artistic_mark",
        }
        selected = modes[k]
        ai_controller.mode = selected
        ai_controller.mode_timer = 0.0
        if selected in ["playful_orbit", "chaotic_mutation", "artistic_mark"]:
            for e in enzymes:
                e.set_mode(selected)
        make_note(f"AI mode set: {selected}", vector(0, -3.7, -Z_OFFSET + 0.7), COLORS["enzyme"])


scene.bind("keydown", keydown)


# ------------------------------------------------------------
# Main update functions
# ------------------------------------------------------------

def update_free_nucleotides(dt, t):
    for n in list(free_nucleotides):
        n.update(dt, t)


def update_particles(dt):
    global particles
    particles = [p for p in particles if p.update(dt)]


def update_marks(dt):
    global repair_marks, floating_notes
    repair_marks = [m for m in repair_marks if m.update(dt)]
    floating_notes = [n for n in floating_notes if n.update(dt)]


def update_dna(t):
    for pair in dna_pairs:
        pair.update(t)


def update_human_override(dt):
    global human_override_timer
    if human_override_timer > 0:
        human_override_timer -= dt


def update_enzymes(dt, t):
    for enzyme in enzymes:
        enzyme.update(dt, t)


def keep_nucleotide_pool_alive():
    visible_free = [n for n in free_nucleotides if n.body.visible and not n.bound]
    if len(visible_free) < 18:
        for _ in range(8):
            spawn_free_nucleotide()


def auto_reset_if_empty_or_halted(dt):
    # Secondary safeguard: if the scene has become completely stable for a long time,
    # begin another round instead of freezing forever.
    if not ai_controller.enabled:
        return
    if len(unresolved_pairs()) == 0 and ai_controller.completion_timer > 9.0:
        reset_simulation(new_round=True)
    elif sim_time - last_change_time > 28.0:
        introduce_mutation_burst(count=3)


# ------------------------------------------------------------
# Build and run
# ------------------------------------------------------------

def main():
    global sim_time

    print("DNA Mutation and Repair System simulation loaded.")
    print("Press H in the VPython window for controls.")

    build_scene()

    dt = 1 / 60.0

    while True:
        rate(60)
        if not running:
            update_marks(dt)
            continue

        sim_time += dt

        ai_controller.update(dt, sim_time)
        update_enzymes(dt, sim_time)
        update_free_nucleotides(dt, sim_time)
        update_particles(dt)
        update_marks(dt)
        update_dna(sim_time)
        update_human_override(dt)
        keep_nucleotide_pool_alive()
        auto_reset_if_empty_or_halted(dt)


if __name__ == "__main__":
    main()
