#!/usr/bin/env python3
"""
Gene Expression Inside a Cell — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python gene_expression_inside_cell_ai_vpython.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation round
    M       cycle AI behavior mode
    O       human override: open gene + polymerase pulse
    T       force transcription burst
    E       force mRNA export from nucleus
    B       force ribosome/protein build burst
    S       spill free nucleotides / amino acids
    D       disturb/shake mobile molecules
    C       clear temporary marks/particles
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    A transparent cell contains a nucleus. Inside the nucleus, a chromosome carries
    a highlighted gene segment. The gene opens, RNA polymerase attaches and travels
    along the gene, free RNA nucleotides attach to form an mRNA strand, the mRNA
    exits through a nuclear pore, and ribosomes in the cytoplasm translate it into
    growing protein chains. The AI controller reads the simulation state and chooses
    behavior modes that open genes, recruit polymerase, spill molecules, export mRNA,
    build proteins, reset completed rounds, and create visible marks.

This file is self-contained and intentionally uses VPython primitives only.
It avoids torus() and uses ring(...) for pore/ribosome-like rings.
"""

from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def randf(lo, hi):
    return random.uniform(lo, hi)

def rand_vec(radius=1.0):
    return vector(randf(-radius, radius), randf(-radius, radius), randf(-radius, radius))

def unit_or_zero(v):
    mag_v = mag(v)
    if mag_v <= 1e-8:
        return vector(0, 0, 0)
    return v / mag_v

def lerp_vec(a, b, t):
    return a + (b - a) * t

def make_label(text, pos, height=12, color_value=color.black, box=False):
    return label(
        text=text,
        pos=pos,
        height=height,
        color=color_value,
        box=box,
        opacity=0.0,
        line=False,
    )

def safe_delete(obj):
    try:
        obj.visible = False
        del obj
    except Exception:
        pass

def set_obj_visible(obj, visible):
    try:
        obj.visible = visible
    except Exception:
        pass

def print_controls():
    print(__doc__)


# ------------------------------------------------------------
# Global visual setup
# ------------------------------------------------------------

scene.title = "Gene Expression Inside a Cell — VPython AI Simulation"
scene.width = 1250
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.58, -0.31, -0.75)
scene.range = 11.5
scene.center = vector(0, 0.4, 0)

# Soft lighting
distant_light(direction=vector(0.4, -0.6, -0.3), color=color.white)
local_light(pos=vector(-5, 6, 5), color=vector(0.55, 0.65, 0.85))

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

NUCLEUS_RADIUS = 3.05
CELL_RADIUS = 7.6
GENE_START_X = -2.15
GENE_END_X = 2.15
GENE_Y = 0.45
GENE_Z = 0.0
GENE_LENGTH = GENE_END_X - GENE_START_X

MAX_NUCLEOTIDES = 70
MAX_AMINO_ACIDS = 95
MAX_FREE_PARTICLES = 190
MAX_MARKS = 120
MAX_PROTEINS = 22
MAX_MRNA = 8

# ------------------------------------------------------------
# Simulation state containers
# ------------------------------------------------------------

objects = []
temporary_marks = []
free_nucleotides = []
free_amino_acids = []
mrnas = []
ribosomes = []
proteins = []

sim = {
    "time": 0.0,
    "dt": 0.018,
    "speed": 1.0,
    "paused": False,
    "round": 1,
    "gene_open": False,
    "gene_open_level": 0.0,
    "polymerase_attached": False,
    "polymerase_progress": 0.0,
    "transcription_complete": False,
    "nucleus_export_ready": False,
    "export_count": 0,
    "protein_count": 0,
    "last_change_time": 0.0,
    "activity_score": 0.0,
    "completion_hold": 0.0,
}

ai = {
    "enabled": True,
    "mode": "SCAN",
    "mode_timer": 0.0,
    "mode_duration": 4.0,
    "stagnation_timer": 0.0,
    "last_signature": None,
    "last_action_time": 0.0,
    "round_wait": 0.0,
    "curiosity_target": vector(0, 0, 0),
    "ritual_phase": 0.0,
    "mode_index": 0,
}

AI_MODES = [
    "SCAN",
    "OPEN_GENE",
    "RECRUIT_POLYMERASE",
    "TRANSCRIBE",
    "EXPORT_MRNA",
    "TRANSLATE",
    "ORGANIZE",
    "SPILL",
    "RITUAL",
    "CHAOS",
    "ARTIST",
    "RESET_LOOP",
]

MODE_COLORS = {
    "SCAN": vector(0.25, 0.35, 0.75),
    "OPEN_GENE": vector(0.1, 0.6, 0.95),
    "RECRUIT_POLYMERASE": vector(0.9, 0.62, 0.08),
    "TRANSCRIBE": vector(0.0, 0.55, 0.35),
    "EXPORT_MRNA": vector(0.55, 0.35, 0.95),
    "TRANSLATE": vector(0.9, 0.25, 0.25),
    "ORGANIZE": vector(0.1, 0.65, 0.65),
    "SPILL": vector(0.85, 0.45, 0.2),
    "RITUAL": vector(0.6, 0.25, 0.85),
    "CHAOS": vector(0.95, 0.2, 0.18),
    "ARTIST": vector(0.15, 0.55, 0.95),
    "RESET_LOOP": vector(0.4, 0.4, 0.4),
}

# ------------------------------------------------------------
# Scene objects
# ------------------------------------------------------------

cell = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS,
    color=vector(0.78, 0.91, 1.0),
    opacity=0.13,
    shininess=0.25,
)
objects.append(cell)

cell_boundary = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=CELL_RADIUS,
    thickness=0.025,
    color=vector(0.55, 0.72, 0.95),
    opacity=0.38,
)
objects.append(cell_boundary)

nucleus = sphere(
    pos=vector(0, 0.3, 0),
    radius=NUCLEUS_RADIUS,
    color=vector(0.72, 0.68, 1.0),
    opacity=0.22,
    shininess=0.4,
)
objects.append(nucleus)

nucleus_boundary = ring(
    pos=nucleus.pos,
    axis=vector(0, 1, 0),
    radius=NUCLEUS_RADIUS,
    thickness=0.035,
    color=vector(0.48, 0.42, 0.95),
    opacity=0.52,
)
objects.append(nucleus_boundary)

nucleus_label = make_label("nucleus", nucleus.pos + vector(0, 3.55, 0), 13, vector(0.25, 0.22, 0.55))
cell_label = make_label("cell boundary", vector(-5.6, -6.0, 0), 12, vector(0.22, 0.38, 0.55))
objects.extend([nucleus_label, cell_label])

# Nuclear pores as rings on the nucleus boundary.
pore_positions = [
    vector(2.95, 0.65, 0),
    vector(-2.75, -0.55, 0.6),
    vector(0.65, 0.15, 2.85),
    vector(-0.75, 0.15, -2.85),
]
pores = []
for i, pp in enumerate(pore_positions):
    pore = ring(
        pos=pp,
        axis=unit_or_zero(pp - nucleus.pos),
        radius=0.36,
        thickness=0.035,
        color=vector(0.25, 0.55, 0.95),
        opacity=0.75,
    )
    pores.append(pore)
    objects.append(pore)

# Chromosome backbone and gene segment
chromosome_points = []
for i in range(56):
    x = -2.65 + i * (5.3 / 55.0)
    y = GENE_Y + 0.22 * math.sin(i * 0.75)
    z = 0.20 * math.cos(i * 0.62)
    chromosome_points.append(vector(x, y, z))

chromosome = curve(
    pos=chromosome_points,
    radius=0.055,
    color=vector(0.42, 0.35, 0.82),
)
objects.append(chromosome)

gene_top = curve(
    radius=0.06,
    color=vector(0.15, 0.45, 0.95),
)
gene_bottom = curve(
    radius=0.06,
    color=vector(0.15, 0.45, 0.95),
)
objects.extend([gene_top, gene_bottom])

base_pairs = []
for i in range(28):
    x = GENE_START_X + i * (GENE_LENGTH / 27.0)
    top = vector(x, GENE_Y + 0.10, 0.16 * math.sin(i * 0.8))
    bottom = vector(x, GENE_Y - 0.10, -0.16 * math.sin(i * 0.8))
    bp = cylinder(
        pos=top,
        axis=bottom - top,
        radius=0.018,
        color=vector(0.85, 0.75, 0.25),
        opacity=0.85,
    )
    base_pairs.append(bp)
    objects.append(bp)

gene_label = make_label("gene opens here", vector(0, GENE_Y + 0.78, 0), 12, vector(0.05, 0.25, 0.55))
objects.append(gene_label)

polymerase = sphere(
    pos=vector(GENE_START_X - 0.45, GENE_Y + 0.42, 0),
    radius=0.32,
    color=vector(1.0, 0.68, 0.12),
    opacity=0.95,
    shininess=0.6,
)
polymerase_label = make_label("RNA polymerase", polymerase.pos + vector(0, 0.55, 0), 10, vector(0.45, 0.26, 0.02))
objects.extend([polymerase, polymerase_label])

# mRNA preview inside the nucleus while transcription occurs
nascent_mrna_curve = curve(radius=0.045, color=vector(0.0, 0.62, 0.32))
objects.append(nascent_mrna_curve)

# Ribosomes in cytoplasm
class Ribosome:
    def __init__(self, pos):
        self.pos = pos
        self.phase = randf(0, math.tau)
        self.busy = False
        self.current_mrna = None
        self.translation_progress = 0.0
        self.body = sphere(
            pos=pos,
            radius=0.38,
            color=vector(0.95, 0.40, 0.35),
            opacity=0.88,
            shininess=0.4,
        )
        self.groove = ring(
            pos=pos + vector(0, 0.02, 0),
            axis=vector(0, 1, 0),
            radius=0.43,
            thickness=0.025,
            color=vector(0.68, 0.12, 0.12),
            opacity=0.85,
        )
        self.label = make_label("ribosome", pos + vector(0, 0.62, 0), 9, vector(0.45, 0.06, 0.04))
        objects.extend([self.body, self.groove, self.label])

    def update_visuals(self, dt):
        self.phase += dt * 1.7
        wobble = vector(0, math.sin(self.phase) * 0.018, math.cos(self.phase * 0.8) * 0.018)
        self.body.pos = self.pos + wobble
        self.groove.pos = self.body.pos + vector(0, 0.02, 0)
        self.label.pos = self.body.pos + vector(0, 0.62, 0)
        self.groove.axis = rotate(vector(0, 1, 0), angle=0.35 * math.sin(self.phase), axis=vector(1, 0, 0))

for rp in [
    vector(4.7, 1.0, 1.2),
    vector(4.0, -1.6, -1.4),
    vector(-4.8, 1.2, -1.1),
    vector(-3.8, -2.2, 1.5),
    vector(1.0, -4.9, 0.6),
]:
    ribosomes.append(Ribosome(rp))

# Free molecules
def note_change(amount=1.0):
    """Record that the simulation changed; used by AI stagnation/completion logic."""
    sim["activity_score"] += amount
    sim["last_change_time"] = sim["time"]

class FreeParticle:
    def __init__(self, kind, pos=None):
        self.kind = kind
        self.pos = pos if pos is not None else rand_vec(CELL_RADIUS * 0.75)
        self.vel = rand_vec(0.6)
        self.orbit_phase = randf(0, math.tau)
        if kind == "nucleotide":
            self.radius = 0.085
            self.color = vector(0.1, 0.7, 0.35)
        else:
            self.radius = 0.075
            self.color = vector(0.95, 0.35, 0.52)
        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.color,
            opacity=0.86,
            shininess=0.35,
        )
        objects.append(self.obj)

    def update(self, dt):
        self.orbit_phase += dt
        self.vel += rand_vec(0.035) * dt * 30.0

        # Keep nucleotides mostly in nucleus; amino acids mostly in cytoplasm.
        if self.kind == "nucleotide":
            center = nucleus.pos
            boundary = NUCLEUS_RADIUS * 0.92
        else:
            center = vector(0, 0, 0)
            boundary = CELL_RADIUS * 0.92

        toward_center = center - self.pos
        if mag(toward_center) > boundary:
            self.vel += unit_or_zero(toward_center) * 0.05

        # Amino acids avoid deep nucleus to suggest nuclear membrane separation.
        if self.kind == "amino" and mag(self.pos - nucleus.pos) < NUCLEUS_RADIUS * 1.05:
            self.vel += unit_or_zero(self.pos - nucleus.pos) * 0.05

        self.vel *= 0.985
        self.pos += self.vel * dt
        self.obj.pos = self.pos

    def delete(self):
        safe_delete(self.obj)

def spawn_nucleotide(pos=None, count=1):
    added = 0
    for _ in range(count):
        if len(free_nucleotides) >= MAX_NUCLEOTIDES:
            break
        p = pos + rand_vec(0.45) if pos is not None else nucleus.pos + rand_vec(NUCLEUS_RADIUS * 0.65)
        free_nucleotides.append(FreeParticle("nucleotide", p))
        added += 1
    if added:
        note_change(0.08 * added)
    return added

def spawn_amino(pos=None, count=1):
    added = 0
    for _ in range(count):
        if len(free_amino_acids) >= MAX_AMINO_ACIDS:
            break
        if pos is None:
            p = rand_vec(CELL_RADIUS * 0.72)
            if mag(p - nucleus.pos) < NUCLEUS_RADIUS + 0.6:
                p += unit_or_zero(p - nucleus.pos) * (NUCLEUS_RADIUS + 1.2)
        else:
            p = pos + rand_vec(0.55)
        free_amino_acids.append(FreeParticle("amino", p))
        added += 1
    if added:
        note_change(0.06 * added)
    return added

# Seed initial particles
spawn_nucleotide(count=34)
spawn_amino(count=52)

# Proteins and mRNA classes
class MessengerRNA:
    def __init__(self, points, exported=False):
        self.points = [vector(p.x, p.y, p.z) for p in points]
        self.exported = exported
        self.export_progress = 0.0
        self.translation_progress = 0.0
        self.bound_ribosome = None
        self.complete = False
        self.target_pore = random.choice(pores)
        self.target_cytoplasm = vector(randf(3.8, 5.4), randf(-1.8, 2.0), randf(-1.8, 2.0))
        self.curve = curve(pos=self.points, radius=0.05, color=vector(0.0, 0.62, 0.32), opacity=0.95)
        self.cap = sphere(pos=self.points[-1], radius=0.12, color=vector(0.0, 0.48, 0.25), opacity=0.95)
        self.label = make_label("mRNA", self.points[-1] + vector(0, 0.32, 0), 9, vector(0.0, 0.36, 0.2))
        objects.extend([self.curve, self.cap, self.label])

    def center(self):
        if not self.points:
            return vector(0, 0, 0)
        total = vector(0, 0, 0)
        for p in self.points:
            total += p
        return total / len(self.points)

    def shift(self, delta):
        self.points = [p + delta for p in self.points]
        self.curve.clear()
        for p in self.points:
            self.curve.append(p)
        self.cap.pos = self.points[-1]
        self.label.pos = self.points[-1] + vector(0, 0.32, 0)

    def update_export(self, dt):
        if self.complete:
            return
        if not self.exported:
            self.export_progress += dt * 0.22 * sim["speed"]
            path_a = self.center()
            if self.export_progress < 0.55:
                target = self.target_pore.pos
            else:
                t2 = (self.export_progress - 0.55) / 0.45
                target = lerp_vec(self.target_pore.pos, self.target_cytoplasm, clamp(t2, 0, 1))
            delta = (target - path_a) * dt * 0.95
            self.shift(delta)
            if self.export_progress >= 1.0:
                self.exported = True
                sim["export_count"] += 1
                note_change(1.0)
                add_mark(self.center(), "export", vector(0.25, 0.45, 1.0))
        else:
            # drift gently in cytoplasm
            drift = vector(0, 0.018 * math.sin(sim["time"] * 1.3 + self.center().x), 0.012 * math.cos(sim["time"] * 1.1))
            self.shift(drift * dt * 18.0)
            # keep outside nucleus
            c = self.center()
            if mag(c - nucleus.pos) < NUCLEUS_RADIUS + 0.6:
                self.shift(unit_or_zero(c - nucleus.pos) * 0.03)

    def delete(self):
        safe_delete(self.curve)
        safe_delete(self.cap)
        safe_delete(self.label)

class ProteinChain:
    def __init__(self, origin):
        self.origin = origin
        self.points = [origin]
        self.age = 0.0
        self.done = False
        self.color = vector(randf(0.25, 0.95), randf(0.25, 0.75), randf(0.35, 0.95))
        self.curve = curve(pos=self.points, radius=0.07, color=self.color, opacity=0.95)
        self.beads = []
        objects.append(self.curve)

    def grow(self, point):
        if len(self.points) > 34:
            self.done = True
            return
        self.points.append(point)
        self.curve.append(point)
        bead = sphere(pos=point, radius=0.105, color=self.color, opacity=0.92)
        self.beads.append(bead)
        objects.append(bead)

    def update(self, dt):
        self.age += dt
        if self.done:
            float_dir = vector(0.018 * math.sin(self.age), 0.028, 0.012 * math.cos(self.age * 1.7))
            new_points = []
            for i, p in enumerate(self.points):
                q = p + float_dir * dt * 20.0 + rand_vec(0.003)
                new_points.append(q)
                if i < len(self.beads):
                    self.beads[i].pos = q
            self.points = new_points
            self.curve.clear()
            for p in self.points:
                self.curve.append(p)

    def delete(self):
        safe_delete(self.curve)
        for b in self.beads:
            safe_delete(b)

# Temporary particles / marks
class Mark:
    def __init__(self, pos, text, color_value):
        self.age = 0.0
        self.life = randf(1.4, 3.4)
        self.pos = pos
        self.obj = sphere(pos=pos, radius=0.07, color=color_value, opacity=0.65)
        self.ring_obj = ring(pos=pos, axis=vector(0, 1, 0), radius=0.16, thickness=0.01, color=color_value, opacity=0.45)
        self.label = None
        if text:
            self.label = make_label(text, pos + vector(0, 0.25, 0), 8, color_value)
            objects.append(self.label)
        objects.extend([self.obj, self.ring_obj])

    def update(self, dt):
        self.age += dt
        self.obj.pos += vector(0, 0.015, 0) * dt * 18.0
        self.ring_obj.pos = self.obj.pos
        self.ring_obj.radius = 0.16 + self.age * 0.15
        alpha = clamp(1.0 - self.age / self.life, 0, 1)
        self.obj.opacity = 0.65 * alpha
        self.ring_obj.opacity = 0.45 * alpha
        if self.label:
            self.label.pos = self.obj.pos + vector(0, 0.25, 0)
            self.label.opacity = 0.0

    def expired(self):
        return self.age >= self.life

    def delete(self):
        safe_delete(self.obj)
        safe_delete(self.ring_obj)
        if self.label:
            safe_delete(self.label)

def add_mark(pos, text="", color_value=vector(0.2, 0.4, 1.0)):
    if len(temporary_marks) > MAX_MARKS:
        old = temporary_marks.pop(0)
        old.delete()
    temporary_marks.append(Mark(pos, text, color_value))

def clear_marks():
    while temporary_marks:
        m = temporary_marks.pop()
        m.delete()

# ------------------------------------------------------------
# Visual status panel
# ------------------------------------------------------------

status = label(
    pos=vector(-7.7, 7.2, 0),
    text="",
    height=12,
    color=color.black,
    box=True,
    border=10,
    background=vector(0.96, 0.98, 1.0),
    opacity=0.78,
    line=False,
)

mode_beacon = sphere(
    pos=vector(-6.8, 5.95, 0),
    radius=0.16,
    color=MODE_COLORS[ai["mode"]],
    opacity=0.9,
)
objects.extend([status, mode_beacon])

# ------------------------------------------------------------
# Gene visual update and core processes
# ------------------------------------------------------------

def gene_point(progress, offset_y=0.0, offset_z=0.0):
    x = GENE_START_X + clamp(progress, 0, 1) * GENE_LENGTH
    return vector(x, GENE_Y + offset_y, offset_z + 0.12 * math.sin(progress * math.tau * 2.0))

def update_gene_visuals():
    open_level = sim["gene_open_level"]
    gene_top.clear()
    gene_bottom.clear()

    for i in range(34):
        t = i / 33.0
        separation = 0.10 + 0.42 * open_level * math.sin(math.pi * t)
        wiggle = 0.08 * math.sin(t * math.tau * 2.0 + sim["time"] * 1.7)
        gene_top.append(gene_point(t, separation + wiggle * 0.2, 0.08))
        gene_bottom.append(gene_point(t, -separation - wiggle * 0.2, -0.08))

    for i, bp in enumerate(base_pairs):
        t = i / max(1, len(base_pairs) - 1)
        separation = 0.10 + 0.42 * open_level * math.sin(math.pi * t)
        top = gene_point(t, separation, 0.08)
        bottom = gene_point(t, -separation, -0.08)
        bp.pos = top
        bp.axis = bottom - top
        bp.opacity = 0.75 * (1.0 - 0.65 * open_level * math.sin(math.pi * t))

    if sim["gene_open"]:
        sim["gene_open_level"] = clamp(sim["gene_open_level"] + sim["dt"] * 2.4 * sim["speed"], 0, 1)
    else:
        sim["gene_open_level"] = clamp(sim["gene_open_level"] - sim["dt"] * 1.4 * sim["speed"], 0, 1)

def open_gene():
    if not sim["gene_open"]:
        sim["gene_open"] = True
        note_change(1.0)
        add_mark(vector(0, GENE_Y + 0.65, 0), "open", vector(0.1, 0.55, 1.0))

def close_gene():
    if sim["gene_open"] and not sim["polymerase_attached"]:
        sim["gene_open"] = False
        note_change(0.4)

def attach_polymerase():
    if sim["gene_open"] and not sim["polymerase_attached"] and not sim["transcription_complete"]:
        sim["polymerase_attached"] = True
        sim["polymerase_progress"] = 0.0
        polymerase.color = vector(1.0, 0.63, 0.04)
        note_change(1.0)
        add_mark(polymerase.pos, "attach", vector(1.0, 0.55, 0.05))

def detach_polymerase():
    if sim["polymerase_attached"]:
        sim["polymerase_attached"] = False
        polymerase.color = vector(1.0, 0.68, 0.12)
        add_mark(polymerase.pos, "detach", vector(0.85, 0.45, 0.0))
        note_change(0.7)

def update_polymerase(dt):
    if sim["polymerase_attached"]:
        speed = 0.055 * sim["speed"]
        sim["polymerase_progress"] += dt * speed
        progress = clamp(sim["polymerase_progress"], 0, 1)
        target = gene_point(progress, 0.47, 0.0)
        polymerase.pos = lerp_vec(polymerase.pos, target, 0.18)
        polymerase_label.pos = polymerase.pos + vector(0, 0.55, 0)

        # Consume nearby nucleotides and draw nascent mRNA.
        if random.random() < 0.45 and free_nucleotides:
            nearest = min(free_nucleotides, key=lambda p: mag(p.pos - polymerase.pos))
            if mag(nearest.pos - polymerase.pos) < 1.1 or random.random() < 0.2:
                free_nucleotides.remove(nearest)
                nearest.delete()
                add_mark(polymerase.pos + rand_vec(0.12), "", vector(0.0, 0.65, 0.35))
                note_change(0.25)

        nascent_mrna_curve.clear()
        n_points = max(3, int(4 + 42 * progress))
        for i in range(n_points):
            t = i / max(1, n_points - 1)
            p = gene_point(t * progress, -0.48 - 0.10 * math.sin(i * 0.45 + sim["time"]), 0.22 * math.sin(i * 0.55))
            nascent_mrna_curve.append(p)

        if progress >= 1.0:
            finish_transcription()
    else:
        home = vector(GENE_START_X - 0.55, GENE_Y + 0.58 + 0.08 * math.sin(sim["time"]), 0.25 * math.cos(sim["time"] * 0.8))
        polymerase.pos = lerp_vec(polymerase.pos, home, 0.045)
        polymerase_label.pos = polymerase.pos + vector(0, 0.55, 0)

def finish_transcription():
    if sim["transcription_complete"]:
        return
    sim["transcription_complete"] = True
    sim["polymerase_attached"] = False
    sim["nucleus_export_ready"] = True
    note_change(2.0)

    points = []
    n = 44
    for i in range(n):
        t = i / (n - 1)
        points.append(gene_point(t, -0.48 - 0.08 * math.sin(i * 0.5), 0.24 * math.sin(i * 0.55)))

    nascent_mrna_curve.clear()
    if len(mrnas) < MAX_MRNA:
        mrnas.append(MessengerRNA(points, exported=False))
    add_mark(vector(GENE_END_X, GENE_Y + 0.55, 0), "mRNA made", vector(0.0, 0.55, 0.25))

def force_transcription_burst():
    open_gene()
    attach_polymerase()
    spawn_nucleotide(polymerase.pos, 10)
    sim["polymerase_progress"] = clamp(sim["polymerase_progress"] + 0.12, 0, 1)
    add_mark(polymerase.pos, "burst", vector(0.0, 0.65, 0.3))
    note_change(1.5)

def force_export():
    for m in mrnas:
        if not m.exported:
            m.export_progress = max(m.export_progress, 0.72)
            add_mark(m.center(), "export push", vector(0.2, 0.45, 1.0))
            note_change(1.0)
            return
    # If no mRNA exists, make a completed one so export can be demonstrated.
    points = [gene_point(i / 36.0, -0.5, 0.18 * math.sin(i)) for i in range(37)]
    if len(mrnas) < MAX_MRNA:
        m = MessengerRNA(points, exported=False)
        m.export_progress = 0.68
        mrnas.append(m)
        note_change(1.0)

def nearest_available_mrna(pos):
    candidates = [m for m in mrnas if m.exported and not m.complete and m.bound_ribosome is None]
    if not candidates:
        return None
    return min(candidates, key=lambda m: mag(m.center() - pos))

def start_translation(ribo):
    if ribo.busy:
        return
    m = nearest_available_mrna(ribo.pos)
    if m:
        ribo.busy = True
        ribo.current_mrna = m
        ribo.translation_progress = 0.0
        m.bound_ribosome = ribo
        add_mark(ribo.pos, "bind mRNA", vector(0.95, 0.25, 0.25))
        note_change(1.0)

def force_translation_burst():
    spawn_amino(count=14)
    for r in ribosomes:
        if not r.busy:
            start_translation(r)
            break
    # If no exported mRNA, force export first.
    if not any(m.exported and not m.complete for m in mrnas):
        force_export()

def update_translation(dt):
    for r in ribosomes:
        r.update_visuals(dt)
        if not r.busy:
            # idle ribosomes slowly attract toward exported mRNA
            m = nearest_available_mrna(r.pos)
            if m:
                r.pos += unit_or_zero(m.center() - r.pos) * dt * 0.18 * sim["speed"]
            continue

        m = r.current_mrna
        if m is None or m.complete:
            r.busy = False
            r.current_mrna = None
            continue

        target = m.center()
        r.pos = lerp_vec(r.pos, target + vector(0, 0.24, 0), 0.05)
        r.translation_progress += dt * 0.12 * sim["speed"]
        m.translation_progress = r.translation_progress

        # Create or grow protein.
        if not proteins or proteins[-1].done or mag(proteins[-1].origin - r.pos) > 1.2:
            if len(proteins) < MAX_PROTEINS:
                proteins.append(ProteinChain(r.pos + vector(0.2, -0.35, 0)))
        if proteins:
            chain = proteins[-1]
            if random.random() < 0.26:
                if free_amino_acids:
                    nearest = min(free_amino_acids, key=lambda p: mag(p.pos - r.pos))
                    free_amino_acids.remove(nearest)
                    nearest.delete()
                p = r.pos + vector(0.16 * math.sin(r.translation_progress * 30), -0.38 - 0.06 * len(chain.points), 0.16 * math.cos(r.translation_progress * 25))
                chain.grow(p)
                note_change(0.35)

        if r.translation_progress >= 1.0 or (proteins and proteins[-1].done):
            m.complete = True
            r.busy = False
            r.current_mrna = None
            sim["protein_count"] += 1
            if proteins:
                proteins[-1].done = True
            add_mark(r.pos, "protein", vector(0.9, 0.2, 0.28))
            note_change(2.0)

    for p in proteins:
        p.update(dt)

# ------------------------------------------------------------
# AI controller
# ------------------------------------------------------------

def state_signature():
    return (
        int(sim["gene_open"]),
        int(sim["polymerase_attached"]),
        int(sim["polymerase_progress"] * 10),
        len(mrnas),
        sum(1 for m in mrnas if m.exported),
        sim["protein_count"],
        len(free_nucleotides) // 5,
        len(free_amino_acids) // 8,
    )

def is_complete():
    enough_protein = sim["protein_count"] >= 3
    finished_mrna = mrnas and all(m.complete or m.translation_progress >= 0.95 for m in mrnas)
    return enough_protein and finished_mrna

def is_empty_or_stalled():
    no_inputs = len(free_nucleotides) < 5 and len(free_amino_acids) < 8
    no_process = not sim["polymerase_attached"] and not any(r.busy for r in ribosomes)
    return no_inputs and no_process

def update_stagnation_detector(dt):
    sig = state_signature()
    if sig == ai["last_signature"]:
        ai["stagnation_timer"] += dt
    else:
        ai["last_signature"] = sig
        ai["stagnation_timer"] = 0.0

    if sim["activity_score"] > 0:
        sim["activity_score"] *= 0.985

def choose_ai_mode():
    if is_complete():
        return "RESET_LOOP"
    if is_empty_or_stalled():
        return "SPILL"
    if ai["stagnation_timer"] > 8.0:
        return random.choice(["CHAOS", "SPILL", "ARTIST", "RESET_LOOP"])
    if not sim["gene_open"]:
        return "OPEN_GENE"
    if sim["gene_open"] and not sim["polymerase_attached"] and not sim["transcription_complete"]:
        return "RECRUIT_POLYMERASE"
    if sim["polymerase_attached"]:
        return "TRANSCRIBE"
    if sim["transcription_complete"] and any(not m.exported for m in mrnas):
        return "EXPORT_MRNA"
    if any(m.exported and not m.complete for m in mrnas):
        return "TRANSLATE"
    return random.choice(["SCAN", "ORGANIZE", "RITUAL", "ARTIST"])

def set_ai_mode(mode):
    if mode not in AI_MODES:
        return
    ai["mode"] = mode
    ai["mode_timer"] = 0.0
    ai["mode_duration"] = randf(2.8, 6.2)
    ai["curiosity_target"] = rand_vec(CELL_RADIUS * 0.55)
    mode_beacon.color = MODE_COLORS.get(mode, color.white)
    add_mark(vector(-6.8, 5.95, 0), mode.lower(), MODE_COLORS.get(mode, vector(0.2, 0.2, 0.2)))

def cycle_ai_mode():
    ai["mode_index"] = (AI_MODES.index(ai["mode"]) + 1) % len(AI_MODES)
    set_ai_mode(AI_MODES[ai["mode_index"]])

def ai_scan(dt):
    if random.random() < 0.04:
        pos = nucleus.pos + rand_vec(NUCLEUS_RADIUS * 0.75)
        add_mark(pos, "scan", MODE_COLORS["SCAN"])

def ai_open_gene(dt):
    open_gene()
    if random.random() < 0.07:
        add_mark(gene_point(randf(0, 1), 0.62, 0), "mark gene", MODE_COLORS["OPEN_GENE"])

def ai_recruit_polymerase(dt):
    open_gene()
    polymerase.pos = lerp_vec(polymerase.pos, vector(GENE_START_X - 0.18, GENE_Y + 0.5, 0), 0.05)
    if mag(polymerase.pos - vector(GENE_START_X, GENE_Y + 0.47, 0)) < 0.55 or ai["mode_timer"] > 1.2:
        attach_polymerase()

def ai_transcribe(dt):
    open_gene()
    if not sim["polymerase_attached"]:
        attach_polymerase()
    if len(free_nucleotides) < 12:
        spawn_nucleotide(polymerase.pos, 6)
    if random.random() < 0.05:
        add_mark(polymerase.pos, "copy", MODE_COLORS["TRANSCRIBE"])

def ai_export_mrna(dt):
    for m in mrnas:
        if not m.exported:
            m.export_progress += dt * 0.45
            if random.random() < 0.05:
                add_mark(m.center(), "to pore", MODE_COLORS["EXPORT_MRNA"])
            return
    force_export()

def ai_translate(dt):
    if len(free_amino_acids) < 18:
        spawn_amino(count=10)
    for r in ribosomes:
        if not r.busy:
            start_translation(r)
            break
    if random.random() < 0.05:
        add_mark(random.choice(ribosomes).pos, "build", MODE_COLORS["TRANSLATE"])

def ai_organize(dt):
    # Move free molecules into useful neighborhoods.
    for p in free_nucleotides[:20]:
        p.vel += unit_or_zero(polymerase.pos - p.pos) * 0.025
    exported = [m for m in mrnas if m.exported and not m.complete]
    if exported:
        target = exported[0].center()
        for p in free_amino_acids[:28]:
            p.vel += unit_or_zero(target - p.pos) * 0.02
    if random.random() < 0.04:
        add_mark(ai["curiosity_target"], "organize", MODE_COLORS["ORGANIZE"])

def ai_spill(dt):
    if random.random() < 0.14:
        spawn_nucleotide(nucleus.pos + rand_vec(1.4), 4)
    if random.random() < 0.16:
        spawn_amino(rand_vec(CELL_RADIUS * 0.55), 5)
    if random.random() < 0.035:
        add_mark(rand_vec(CELL_RADIUS * 0.6), "spill", MODE_COLORS["SPILL"])

def ai_ritual(dt):
    ai["ritual_phase"] += dt * 1.8
    r = 1.3 + 0.45 * math.sin(ai["ritual_phase"] * 0.7)
    pos = vector(r * math.cos(ai["ritual_phase"]), GENE_Y + 0.85, r * math.sin(ai["ritual_phase"]))
    add_mark(pos, "", MODE_COLORS["RITUAL"])
    if int(ai["ritual_phase"] * 2) % 4 == 0:
        open_gene()
    if random.random() < 0.018:
        attach_polymerase()

def ai_chaos(dt):
    for p in random.sample(free_nucleotides, min(10, len(free_nucleotides))):
        p.vel += rand_vec(0.25)
    for p in random.sample(free_amino_acids, min(14, len(free_amino_acids))):
        p.vel += rand_vec(0.25)
    for r in ribosomes:
        r.pos += rand_vec(0.018)
    if random.random() < 0.08:
        add_mark(rand_vec(CELL_RADIUS * 0.65), "chaos", MODE_COLORS["CHAOS"])
    if random.random() < 0.03:
        force_transcription_burst()

def ai_artist(dt):
    t = sim["time"] * 1.4
    pos = vector(2.4 * math.cos(t), -2.2 + 0.9 * math.sin(t * 0.7), 2.0 * math.sin(t))
    add_mark(pos, "", MODE_COLORS["ARTIST"])
    if random.random() < 0.03:
        spawn_amino(pos, 2)

def ai_reset_loop(dt):
    ai["round_wait"] += dt
    if ai["round_wait"] > 2.4:
        reset_simulation()
        ai["round_wait"] = 0.0
        set_ai_mode("SCAN")

def update_ai(dt):
    if not ai["enabled"] or sim["paused"]:
        return

    update_stagnation_detector(dt)
    ai["mode_timer"] += dt

    if ai["mode_timer"] > ai["mode_duration"]:
        set_ai_mode(choose_ai_mode())

    # Reactive override when obvious stage transition is needed.
    desired = choose_ai_mode()
    if desired in ["OPEN_GENE", "RECRUIT_POLYMERASE", "TRANSCRIBE", "EXPORT_MRNA", "TRANSLATE", "RESET_LOOP"]:
        if desired != ai["mode"] and ai["mode_timer"] > 0.9:
            set_ai_mode(desired)

    mode = ai["mode"]
    if mode == "SCAN":
        ai_scan(dt)
    elif mode == "OPEN_GENE":
        ai_open_gene(dt)
    elif mode == "RECRUIT_POLYMERASE":
        ai_recruit_polymerase(dt)
    elif mode == "TRANSCRIBE":
        ai_transcribe(dt)
    elif mode == "EXPORT_MRNA":
        ai_export_mrna(dt)
    elif mode == "TRANSLATE":
        ai_translate(dt)
    elif mode == "ORGANIZE":
        ai_organize(dt)
    elif mode == "SPILL":
        ai_spill(dt)
    elif mode == "RITUAL":
        ai_ritual(dt)
    elif mode == "CHAOS":
        ai_chaos(dt)
    elif mode == "ARTIST":
        ai_artist(dt)
    elif mode == "RESET_LOOP":
        ai_reset_loop(dt)

# ------------------------------------------------------------
# Reset and cleanup
# ------------------------------------------------------------

def reset_simulation():
    sim["round"] += 1
    sim["time"] = 0.0
    sim["gene_open"] = False
    sim["gene_open_level"] = 0.0
    sim["polymerase_attached"] = False
    sim["polymerase_progress"] = 0.0
    sim["transcription_complete"] = False
    sim["nucleus_export_ready"] = False
    sim["export_count"] = 0
    sim["protein_count"] = 0
    sim["activity_score"] = 0.0
    sim["last_change_time"] = 0.0
    sim["completion_hold"] = 0.0

    ai["stagnation_timer"] = 0.0
    ai["last_signature"] = None
    ai["round_wait"] = 0.0

    nascent_mrna_curve.clear()
    polymerase.pos = vector(GENE_START_X - 0.45, GENE_Y + 0.42, 0)
    polymerase.color = vector(1.0, 0.68, 0.12)

    while mrnas:
        m = mrnas.pop()
        m.delete()
    while proteins:
        p = proteins.pop()
        p.delete()
    while free_nucleotides:
        p = free_nucleotides.pop()
        p.delete()
    while free_amino_acids:
        p = free_amino_acids.pop()
        p.delete()
    clear_marks()

    for r in ribosomes:
        r.busy = False
        r.current_mrna = None
        r.translation_progress = 0.0

    spawn_nucleotide(count=34)
    spawn_amino(count=52)
    add_mark(vector(0, 0.8, 0), "new round", vector(0.2, 0.5, 0.9))
    note_change(1.0)

# ------------------------------------------------------------
# Human keyboard controls
# ------------------------------------------------------------

def human_override():
    open_gene()
    attach_polymerase()
    spawn_nucleotide(polymerase.pos, 8)
    add_mark(polymerase.pos, "override", vector(0.1, 0.4, 1.0))
    note_change(2.0)

def disturb():
    for p in free_nucleotides:
        p.vel += rand_vec(0.45)
    for p in free_amino_acids:
        p.vel += rand_vec(0.45)
    for r in ribosomes:
        r.pos += rand_vec(0.16)
    add_mark(vector(0, 0.8, 0), "disturb", vector(0.9, 0.2, 0.1))
    note_change(1.0)

def spill_all():
    spawn_nucleotide(nucleus.pos, 14)
    spawn_amino(rand_vec(CELL_RADIUS * 0.4), 18)
    add_mark(vector(0, 0.8, 0), "spill", vector(0.85, 0.42, 0.1))

def on_keydown(evt):
    key = evt.key.lower()
    if key == "a":
        ai["enabled"] = not ai["enabled"]
        add_mark(vector(-6.8, 5.95, 0), "AI on" if ai["enabled"] else "AI off", vector(0.1, 0.5, 0.95))
    elif key == "p":
        sim["paused"] = not sim["paused"]
    elif key == "r":
        reset_simulation()
    elif key == "m":
        cycle_ai_mode()
    elif key == "o":
        human_override()
    elif key == "t":
        force_transcription_burst()
    elif key == "e":
        force_export()
    elif key == "b":
        force_translation_burst()
    elif key == "s":
        spill_all()
    elif key == "d":
        disturb()
    elif key == "c":
        clear_marks()
    elif key in ["+", "="]:
        sim["speed"] = clamp(sim["speed"] * 1.18, 0.25, 5.0)
    elif key in ["-", "_"]:
        sim["speed"] = clamp(sim["speed"] / 1.18, 0.25, 5.0)
    elif key == "h":
        print_controls()

scene.bind("keydown", on_keydown)

# ------------------------------------------------------------
# Main update loop
# ------------------------------------------------------------

def update_particles(dt):
    for p in free_nucleotides:
        p.update(dt)
    for p in free_amino_acids:
        p.update(dt)

    # Cap total particle count if the user/AI spills too much.
    while len(free_nucleotides) + len(free_amino_acids) > MAX_FREE_PARTICLES:
        if len(free_amino_acids) > len(free_nucleotides) and free_amino_acids:
            old = free_amino_acids.pop(0)
        elif free_nucleotides:
            old = free_nucleotides.pop(0)
        else:
            break
        old.delete()

def update_mrnas(dt):
    for m in list(mrnas):
        m.update_export(dt)
        # remove old completed mRNA after translation
        if m.complete and m.translation_progress >= 1.0 and random.random() < 0.003:
            m.delete()
            mrnas.remove(m)

def update_marks(dt):
    for m in list(temporary_marks):
        m.update(dt)
        if m.expired():
            m.delete()
            temporary_marks.remove(m)

def update_status():
    status.text = (
        f"Gene Expression Inside a Cell\n"
        f"Round: {sim['round']} | Speed: {sim['speed']:.2f} | Paused: {sim['paused']}\n"
        f"AI: {'ON' if ai['enabled'] else 'OFF'} | Mode: {ai['mode']} | Stagnation: {ai['stagnation_timer']:.1f}s\n"
        f"Gene open: {sim['gene_open_level']:.2f} | Polymerase: {'attached' if sim['polymerase_attached'] else 'free'} | Progress: {sim['polymerase_progress']:.2f}\n"
        f"mRNA: {len(mrnas)} | Exported: {sum(1 for m in mrnas if m.exported)} | Proteins: {sim['protein_count']}\n"
        f"Nucleotides: {len(free_nucleotides)} | Amino acids: {len(free_amino_acids)}\n"
        f"Keys: A AI, P pause, R reset, M mode, O override, T transcribe, E export, B build, S spill, D disturb, H help"
    )
    mode_beacon.color = MODE_COLORS.get(ai["mode"], vector(0.5, 0.5, 0.5))
    mode_beacon.radius = 0.16 + 0.035 * math.sin(sim["time"] * 4.0)

def idle_stage_helpers(dt):
    # Natural tendency to start if AI is off: keeps the scene alive.
    if not ai["enabled"]:
        if sim["time"] > 1.0 and not sim["gene_open"] and random.random() < 0.003:
            open_gene()

    # Slowly close gene after all transcription/export work is done.
    if sim["transcription_complete"] and not sim["polymerase_attached"] and all(m.exported for m in mrnas):
        if random.random() < 0.01:
            close_gene()

print_controls()
set_ai_mode("SCAN")

while True:
    rate(60)
    if sim["paused"]:
        update_status()
        continue

    dt = sim["dt"] * sim["speed"]
    sim["time"] += dt

    update_ai(dt)
    idle_stage_helpers(dt)
    update_gene_visuals()
    update_polymerase(dt)
    update_particles(dt)
    update_mrnas(dt)
    update_translation(dt)
    update_marks(dt)
    update_status()
