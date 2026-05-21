"""
DNA Packaging into Chromosomes — VPython 3D Simulation with Expressive AI

Run:
    pip install vpython
    python dna_packaging_chromosome_ai_simulation.py

Controls:
    H        print controls
    Space    pause / resume
    A        toggle AI on/off
    R        reset round
    1        AI mode: scan
    2        AI mode: wrap
    3        AI mode: coil
    4        AI mode: condense
    5        AI mode: playful
    6        AI mode: repair
    7        AI mode: ritual
    O        human override pulse
    D        detach a wrapped DNA segment
    M        mark closest unfinished histone
    C        clear particles / marks

Simulation idea:
    DNA starts as a loose strand of base-pair beads. Histone proteins attract nearby DNA,
    DNA wraps around histones to form nucleosomes, nucleosomes coil into chromatin fibers,
    and the fiber condenses into a chromosome-like X form.

AI controller:
    A rule-based and expressive state machine reads packaging progress, velocity/stagnation,
    and completion. It switches behavior modes, applies forces, marks objects, causes wrapping,
    coils fibers, condenses the final chromosome, and resets the scene when a completed or stagnant
    round has stopped changing.
"""

from vpython import *
import math
import random
from collections import deque

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="DNA Packaging into Chromosomes — AI Controlled VPython Simulation",
    width=1250,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 5.5, 18)
scene.camera.axis = vector(0, -4.0, -18)
scene.forward = vector(0, -0.18, -1)
scene.up = vector(0, 1, 0)
scene.autoscale = False
scene.range = 8.2

# ------------------------------------------------------------
# Visual constants
# ------------------------------------------------------------

DNA_A = vector(0.28, 0.44, 1.0)
DNA_T = vector(1.0, 0.48, 0.36)
DNA_C = vector(0.20, 0.70, 0.48)
DNA_G = vector(0.90, 0.64, 0.24)
DNA_BACKBONE = vector(0.36, 0.46, 0.88)
DNA_BACKBONE_2 = vector(0.90, 0.50, 0.82)

HISTONE_COLOR = vector(0.88, 0.72, 1.0)
HISTONE_CORE = vector(0.64, 0.46, 0.92)
CHROMATIN_COLOR = vector(0.68, 0.54, 0.92)
CHROMOSOME_COLOR = vector(0.56, 0.40, 0.84)
ENZYME_COLOR = vector(0.22, 0.70, 0.95)
AI_COLOR = vector(0.25, 0.62, 0.90)
MARK_COLOR = vector(1.0, 0.72, 0.22)
SPARK_COLOR = vector(0.42, 0.80, 1.0)
FIELD_COLOR = vector(0.73, 0.86, 1.0)

# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp_vec(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def rotate_y(v, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return vector(c * v.x + s * v.z, v.y, -s * v.x + c * v.z)

def rotate_z(v, angle):
    c = math.cos(angle)
    s = math.sin(angle)
    return vector(c * v.x - s * v.y, s * v.x + c * v.y, v.z)

def random_unit():
    a = random.uniform(0, 2 * math.pi)
    z = random.uniform(-0.45, 0.45)
    r = math.sqrt(max(0.0, 1 - z * z))
    return vector(r * math.cos(a), z, r * math.sin(a))

def color_by_base(base):
    return {"A": DNA_A, "T": DNA_T, "C": DNA_C, "G": DNA_G}.get(base, color.white)

# ------------------------------------------------------------
# Ground and labels
# ------------------------------------------------------------

floor = box(
    pos=vector(0, -3.05, 0),
    size=vector(16, 0.05, 10.5),
    color=vector(0.93, 0.96, 0.98),
    opacity=0.55,
)

title_label = label(
    pos=vector(0, 3.85, 0),
    text="DNA packaging: loose DNA → nucleosomes → chromatin fiber → chromosome",
    height=18,
    color=vector(0.15, 0.22, 0.32),
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-7.6, 3.25, 0),
    text="",
    height=12,
    color=vector(0.12, 0.16, 0.22),
    box=False,
    opacity=0,
    align="left",
)

legend_label = label(
    pos=vector(5.3, 3.25, 0),
    text="",
    height=11,
    color=vector(0.16, 0.20, 0.26),
    box=False,
    opacity=0,
    align="left",
)

# ------------------------------------------------------------
# Data objects
# ------------------------------------------------------------

class DNABead:
    def __init__(self, index, base, pos, strand_side):
        self.index = index
        self.base = base
        self.strand_side = strand_side
        self.pos = vector(pos)
        self.prev_pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.force = vector(0, 0, 0)
        self.radius = 0.075
        self.target = vector(pos)
        self.attached_histone = None
        self.wrap_slot = None
        self.is_wrapped = False
        self.is_condensed = False
        self.marker_timer = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=color_by_base(base),
            shininess=0.35,
            opacity=0.95,
            make_trail=False,
        )

    def reset(self, pos):
        self.pos = vector(pos)
        self.prev_pos = vector(pos)
        self.vel = vector(random.uniform(-0.05, 0.05), random.uniform(-0.02, 0.02), random.uniform(-0.03, 0.03))
        self.force = vector(0, 0, 0)
        self.target = vector(pos)
        self.attached_histone = None
        self.wrap_slot = None
        self.is_wrapped = False
        self.is_condensed = False
        self.marker_timer = 0.0
        self.body.visible = True
        self.body.radius = self.radius
        self.body.opacity = 0.95
        self.body.color = color_by_base(self.base)
        self.body.pos = self.pos

    def apply_force(self, f):
        self.force += f

    def integrate(self, dt, time_value):
        self.prev_pos = vector(self.pos)

        if self.is_condensed:
            spring = (self.target - self.pos) * 8.0
            damping = -self.vel * 2.3
            self.force += spring + damping
        elif self.is_wrapped:
            spring = (self.target - self.pos) * 13.0
            damping = -self.vel * 2.7
            self.force += spring + damping
        else:
            drift = vector(0, 0.025 * math.sin(time_value * 1.2 + self.phase), 0.0)
            spring = (self.target - self.pos) * 1.6
            damping = -self.vel * 0.82
            self.force += spring + damping + drift

        self.vel += self.force * dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.force = vector(0, 0, 0)

        # Soft table boundary.
        if self.pos.y < -2.72:
            self.pos.y = -2.72
            self.vel.y = abs(self.vel.y) * 0.35
        for axis in ("x", "z"):
            val = getattr(self.pos, axis)
            if abs(val) > 7.2:
                setattr(self.pos, axis, 7.2 if val > 0 else -7.2)
                setattr(self.vel, axis, -getattr(self.vel, axis) * 0.45)

        if self.marker_timer > 0:
            self.marker_timer -= dt
            pulse = 0.5 + 0.5 * math.sin(time_value * 10)
            self.body.color = lerp_vec(color_by_base(self.base), MARK_COLOR, pulse)
            self.body.radius = self.radius * (1.0 + 0.25 * pulse)
        else:
            self.body.color = color_by_base(self.base)
            self.body.radius = self.radius

        self.body.pos = self.pos


class StrandSegment:
    def __init__(self, b1, b2, radius, col):
        self.b1 = b1
        self.b2 = b2
        self.obj = cylinder(
            pos=b1.pos,
            axis=b2.pos - b1.pos,
            radius=radius,
            color=col,
            opacity=0.70,
        )

    def update(self):
        self.obj.pos = self.b1.pos
        self.obj.axis = self.b2.pos - self.b1.pos


class BasePairRung:
    def __init__(self, b1, b2):
        self.b1 = b1
        self.b2 = b2
        self.obj = cylinder(
            pos=b1.pos,
            axis=b2.pos - b1.pos,
            radius=0.018,
            color=vector(0.72, 0.78, 0.86),
            opacity=0.58,
        )

    def update(self):
        self.obj.pos = self.b1.pos
        self.obj.axis = self.b2.pos - self.b1.pos


class Histone:
    def __init__(self, index, pos):
        self.index = index
        self.pos = vector(pos)
        self.base_pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.radius = 0.48
        self.wrap_progress = 0.0
        self.target_wrap_progress = 0.0
        self.is_complete = False
        self.marked = False
        self.mark_timer = 0.0
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.coil_target = vector(pos)
        self.condense_target = vector(pos)
        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=HISTONE_COLOR,
            opacity=0.74,
            shininess=0.55,
        )
        self.core = sphere(
            pos=self.pos,
            radius=self.radius * 0.62,
            color=HISTONE_CORE,
            opacity=0.85,
            shininess=0.7,
        )
        self.field = sphere(
            pos=self.pos,
            radius=self.radius * 1.55,
            color=FIELD_COLOR,
            opacity=0.10,
        )
        self.wrap_ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=self.radius * 0.98,
            thickness=0.025,
            color=CHROMATIN_COLOR,
            opacity=0.25,
        )
        self.label = label(
            pos=self.pos + vector(0, 0.76, 0),
            text=f"H{index+1}",
            height=9,
            color=vector(0.32, 0.24, 0.50),
            box=False,
            opacity=0,
        )

    def reset(self, pos):
        self.pos = vector(pos)
        self.base_pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.wrap_progress = 0.0
        self.target_wrap_progress = 0.0
        self.is_complete = False
        self.marked = False
        self.mark_timer = 0.0
        self.coil_target = vector(pos)
        self.condense_target = vector(pos)
        self.body.visible = True
        self.core.visible = True
        self.field.visible = True
        self.wrap_ring.visible = True
        self.label.visible = True
        self.update_visuals(0)

    def apply_force(self, f):
        self.vel += f

    def update(self, dt, time_value):
        self.wrap_progress = lerp_vec(vector(self.wrap_progress, 0, 0), vector(self.target_wrap_progress, 0, 0), dt * 2.2).x
        if self.wrap_progress >= 0.985:
            self.is_complete = True

        target = self.base_pos
        if global_stage >= 2:
            target = self.coil_target
        if global_stage >= 3:
            target = self.condense_target

        self.vel += (target - self.pos) * 0.55 * dt
        self.vel *= 0.94
        self.pos += self.vel * dt

        self.mark_timer = max(0, self.mark_timer - dt)
        self.update_visuals(time_value)

    def update_visuals(self, time_value):
        pulse = 0.5 + 0.5 * math.sin(time_value * 4 + self.index)
        mark_mix = 1.0 if self.marked or self.mark_timer > 0 else 0.0
        self.body.pos = self.pos
        self.core.pos = self.pos
        self.field.pos = self.pos
        self.wrap_ring.pos = self.pos
        self.label.pos = self.pos + vector(0, 0.78, 0)
        self.label.text = f"H{self.index+1}\n{int(self.wrap_progress*100)}%"

        self.body.color = lerp_vec(HISTONE_COLOR, MARK_COLOR, mark_mix * (0.4 + 0.35 * pulse))
        self.field.opacity = 0.04 + 0.12 * self.wrap_progress + (0.13 * pulse if self.mark_timer > 0 else 0)
        self.wrap_ring.opacity = 0.18 + 0.55 * self.wrap_progress
        self.wrap_ring.radius = self.radius * (0.82 + 0.22 * self.wrap_progress + 0.04 * pulse)
        self.wrap_ring.axis = vector(math.sin(time_value * 0.4 + self.index), 1.0, math.cos(time_value * 0.4 + self.index)) * 0.8


class EnzymeAgent:
    def __init__(self, name, pos, color_value):
        self.name = name
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.target = vector(pos)
        self.mode = "scan"
        self.attached_to = None
        self.phase = random.uniform(0, 2 * math.pi)
        self.body = sphere(pos=self.pos, radius=0.18, color=color_value, shininess=0.65, make_trail=True, retain=90)
        self.halo = ring(pos=self.pos, axis=vector(0, 1, 0), radius=0.28, thickness=0.018, color=color_value, opacity=0.35)
        self.label = label(
            pos=self.pos + vector(0, 0.35, 0),
            text=name,
            height=9,
            color=vector(0.10, 0.20, 0.30),
            box=False,
            opacity=0,
        )

    def reset(self, pos):
        self.pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.target = vector(pos)
        self.mode = "scan"
        self.attached_to = None
        self.body.clear_trail()
        self.update(0.01, 0)

    def update(self, dt, time_value):
        wobble = vector(
            0.06 * math.sin(time_value * 2.5 + self.phase),
            0.05 * math.cos(time_value * 1.8 + self.phase),
            0.05 * math.sin(time_value * 2.2 + self.phase * 0.5),
        )
        self.vel += (self.target + wobble - self.pos) * 2.0 * dt
        self.vel *= 0.90
        self.pos += self.vel * dt
        self.body.pos = self.pos
        self.halo.pos = self.pos
        self.halo.axis = vector(math.sin(time_value * 2), 1, math.cos(time_value * 1.6))
        self.label.pos = self.pos + vector(0, 0.35, 0)
        self.label.text = f"{self.name}\n{self.mode}"


class Spark:
    def __init__(self, pos, vel, col, radius=0.035, life=2.0):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.life = life
        self.max_life = life
        self.obj = sphere(pos=self.pos, radius=radius, color=col, opacity=0.75)

    def update(self, dt):
        self.life -= dt
        self.vel += vector(0, -0.06, 0) * dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0, 0.75 * self.life / self.max_life)
        return self.life > 0

    def hide(self):
        self.obj.visible = False


class MarkDisk:
    def __init__(self, pos, col=MARK_COLOR, life=4.5):
        self.life = life
        self.max_life = life
        self.obj = ring(pos=pos, axis=vector(0, 1, 0), radius=0.22, thickness=0.015, color=col, opacity=0.75)

    def update(self, dt, time_value):
        self.life -= dt
        self.obj.radius += 0.08 * dt
        self.obj.opacity = max(0, 0.75 * self.life / self.max_life)
        self.obj.axis = vector(math.sin(time_value), 1, math.cos(time_value * 0.8))
        return self.life > 0

    def hide(self):
        self.obj.visible = False


# ------------------------------------------------------------
# Global simulation containers
# ------------------------------------------------------------

N_BASE_PAIRS = 72
N_HISTONES = 8
dna_left = []
dna_right = []
all_beads = []
backbone_segments = []
rungs = []
histones = []
enzymes = []
sparks = []
marks = []
nucleosome_links = []

time_value = 0.0
paused = False
ai_enabled = True
human_override_timer = 0.0
round_number = 1
global_stage = 0  # 0 loose, 1 wrapping, 2 coiling, 3 condensing, 4 complete

# ------------------------------------------------------------
# Build/reset scene
# ------------------------------------------------------------

def initial_dna_position(i, side):
    span = 13.0
    x = -span / 2 + span * i / (N_BASE_PAIRS - 1)
    angle = i * 0.55
    helix_r = 0.28
    y = 0.38 * math.sin(i * 0.20) + side * helix_r * math.cos(angle)
    z = side * helix_r * math.sin(angle) - 0.55
    return vector(x, y, z)

def histone_initial_position(j):
    x = -5.7 + j * (11.4 / (N_HISTONES - 1))
    y = -1.35 + 0.24 * math.sin(j * 1.7)
    z = 0.85 + 0.20 * math.cos(j * 1.2)
    return vector(x, y, z)

def coil_position(j):
    t = j / max(1, N_HISTONES - 1)
    angle = t * 2.0 * math.pi * 1.25
    r = 2.25 - 0.45 * t
    return vector(r * math.cos(angle), -0.55 + 0.22 * math.sin(angle * 1.7), r * math.sin(angle) * 0.55)

def chromosome_position_for_histone(j):
    # Two chromatids crossing into an X-like chromosome.
    t = j / max(1, N_HISTONES - 1)
    if j < N_HISTONES / 2:
        u = j / max(1, (N_HISTONES / 2 - 1))
        x = -1.0 + 2.0 * u
        y = 1.35 - 2.7 * u
        z = 0.15 * math.sin(u * math.pi)
    else:
        u = (j - N_HISTONES / 2) / max(1, (N_HISTONES / 2 - 1))
        x = 1.0 - 2.0 * u
        y = 1.35 - 2.7 * u
        z = -0.15 * math.sin(u * math.pi)
    return vector(x, y, z)

def hide_and_clear_objects(collection):
    while collection:
        obj = collection.pop()
        if hasattr(obj, "hide"):
            obj.hide()
        elif hasattr(obj, "visible"):
            obj.visible = False

def build_simulation():
    global dna_left, dna_right, all_beads, backbone_segments, rungs, histones, enzymes
    global nucleosome_links, sparks, marks

    dna_left = []
    dna_right = []
    all_beads = []
    backbone_segments = []
    rungs = []
    histones = []
    enzymes = []
    sparks = []
    marks = []
    nucleosome_links = []

    bases = []
    base_names = ["A", "T", "C", "G"]
    complement = {"A": "T", "T": "A", "C": "G", "G": "C"}

    for i in range(N_BASE_PAIRS):
        base = random.choice(base_names)
        bases.append(base)
        b_left = DNABead(i, base, initial_dna_position(i, -1), -1)
        b_right = DNABead(i, complement[base], initial_dna_position(i, 1), 1)
        dna_left.append(b_left)
        dna_right.append(b_right)
        all_beads.extend([b_left, b_right])
        rungs.append(BasePairRung(b_left, b_right))

    for i in range(N_BASE_PAIRS - 1):
        backbone_segments.append(StrandSegment(dna_left[i], dna_left[i + 1], 0.027, DNA_BACKBONE))
        backbone_segments.append(StrandSegment(dna_right[i], dna_right[i + 1], 0.027, DNA_BACKBONE_2))

    for j in range(N_HISTONES):
        h = Histone(j, histone_initial_position(j))
        h.coil_target = coil_position(j)
        h.condense_target = chromosome_position_for_histone(j)
        histones.append(h)

    enzymes.append(EnzymeAgent("remodeler", vector(-6.5, 2.2, 0.2), ENZYME_COLOR))
    enzymes.append(EnzymeAgent("condensin", vector(6.4, 2.0, -0.2), vector(0.80, 0.42, 0.95)))

build_simulation()

def reset_round(full_randomize=True):
    global time_value, global_stage, human_override_timer, round_number
    global sparks, marks

    round_number += 1
    global_stage = 0
    human_override_timer = 0.0

    for s in sparks:
        s.hide()
    for m in marks:
        m.hide()
    sparks = []
    marks = []

    for i in range(N_BASE_PAIRS):
        offset = vector(0, random.uniform(-0.08, 0.08), random.uniform(-0.06, 0.06)) if full_randomize else vector(0, 0, 0)
        dna_left[i].reset(initial_dna_position(i, -1) + offset)
        dna_right[i].reset(initial_dna_position(i, 1) + offset)

    for j, h in enumerate(histones):
        jitter = random_unit() * random.uniform(0.0, 0.15) if full_randomize else vector(0, 0, 0)
        h.reset(histone_initial_position(j) + jitter)
        h.coil_target = coil_position(j)
        h.condense_target = chromosome_position_for_histone(j)

    enzymes[0].reset(vector(-6.5, 2.2, 0.2))
    enzymes[1].reset(vector(6.4, 2.0, -0.2))
    ai_controller.reset_soft()

# ------------------------------------------------------------
# Packaging geometry
# ------------------------------------------------------------

def histone_base_range(histone):
    segment = N_BASE_PAIRS / N_HISTONES
    center = int((histone.index + 0.5) * segment)
    half = int(segment * 0.62)
    lo = max(0, center - half)
    hi = min(N_BASE_PAIRS - 1, center + half)
    return lo, hi

def wrap_position(histone, bead, side, time_value):
    lo, hi = histone_base_range(histone)
    if hi == lo:
        local_t = 0.0
    else:
        local_t = (bead.index - lo) / (hi - lo)
    turns = 1.72
    angle = local_t * turns * 2 * math.pi + side * 0.32
    radius = histone.radius * (1.24 + 0.05 * math.sin(time_value * 1.2 + bead.index))
    pitch = (local_t - 0.5) * 0.70
    base_vector = vector(radius * math.cos(angle), pitch, radius * math.sin(angle))
    # Tilt wrap plane so nucleosomes feel 3D rather than flat rings.
    tilted = rotate_z(base_vector, 0.28 * math.sin(histone.index * 0.7))
    return histone.pos + tilted

def update_dna_targets(time_value):
    global global_stage

    complete_count = sum(1 for h in histones if h.is_complete)
    wrap_fraction = sum(h.wrap_progress for h in histones) / len(histones)

    if wrap_fraction > 0.15:
        global_stage = max(global_stage, 1)
    if complete_count >= max(3, int(0.62 * N_HISTONES)):
        global_stage = max(global_stage, 2)
    if complete_count >= N_HISTONES and ai_controller.condense_drive > 0.35:
        global_stage = max(global_stage, 3)
    if global_stage >= 3 and ai_controller.condense_drive > 0.92:
        global_stage = 4

    for h in histones:
        lo, hi = histone_base_range(h)
        for i in range(lo, hi + 1):
            progress_gate = clamp((h.wrap_progress * (hi - lo + 1) - (i - lo)) / 2.0, 0, 1)
            for bead in (dna_left[i], dna_right[i]):
                free_pos = initial_dna_position(i, bead.strand_side)
                wrap_pos = wrap_position(h, bead, bead.strand_side, time_value)
                target = lerp_vec(free_pos, wrap_pos, progress_gate)
                if global_stage >= 2:
                    local_offset = target - h.pos
                    target = lerp_vec(target, h.coil_target + local_offset * 0.74, clamp((global_stage - 1) * 0.55, 0, 1))
                if global_stage >= 3:
                    local_offset = target - h.pos
                    compact = h.condense_target + local_offset * 0.40
                    target = lerp_vec(target, compact, ai_controller.condense_drive)
                    bead.is_condensed = ai_controller.condense_drive > 0.55

                bead.target = target
                if progress_gate > 0.2:
                    bead.attached_histone = h
                    bead.wrap_slot = i - lo
                    bead.is_wrapped = progress_gate > 0.72
                else:
                    bead.attached_histone = None
                    bead.wrap_slot = None
                    bead.is_wrapped = False

def apply_dna_physics(dt, time_value):
    # Keep strands coherent.
    for strand in (dna_left, dna_right):
        for i in range(N_BASE_PAIRS - 1):
            a = strand[i]
            b = strand[i + 1]
            desired = 0.20 if global_stage >= 3 else 0.24
            delta = b.pos - a.pos
            d = mag(delta)
            if d > 1e-5:
                f = safe_norm(delta) * (d - desired) * 1.35
                a.apply_force(f)
                b.apply_force(-f)

    # Keep base-pair rungs near each other while still flexible.
    for i in range(N_BASE_PAIRS):
        a = dna_left[i]
        b = dna_right[i]
        desired = 0.36 if not a.is_wrapped else 0.24
        delta = b.pos - a.pos
        d = mag(delta)
        if d > 1e-5:
            f = safe_norm(delta) * (d - desired) * 0.60
            a.apply_force(f)
            b.apply_force(-f)

    # Collision/soft repulsion between histones and loose DNA.
    for h in histones:
        for bead in all_beads[::2]:
            dvec = bead.pos - h.pos
            d = mag(dvec)
            if 0.05 < d < h.radius * 1.2 and not bead.is_wrapped:
                bead.apply_force(safe_norm(dvec) * (h.radius * 1.2 - d) * 2.5)

    # Integrate.
    for bead in all_beads:
        bead.integrate(dt, time_value)

def update_connectors():
    for seg in backbone_segments:
        seg.update()
    for rung in rungs:
        rung.update()

def update_histone_links():
    # Links between nucleosomes, shown only when chromatin fiber starts forming.
    global nucleosome_links
    if not nucleosome_links:
        for i in range(N_HISTONES - 1):
            link = cylinder(
                pos=histones[i].pos,
                axis=histones[i + 1].pos - histones[i].pos,
                radius=0.035,
                color=CHROMATIN_COLOR,
                opacity=0.0,
            )
            nucleosome_links.append(link)

    alpha = 0.0
    if global_stage >= 2:
        alpha = 0.25 + 0.45 * clamp(ai_controller.coil_drive, 0, 1)
    if global_stage >= 3:
        alpha = 0.55 + 0.25 * ai_controller.condense_drive

    for i, link in enumerate(nucleosome_links):
        link.visible = True
        link.pos = histones[i].pos
        link.axis = histones[i + 1].pos - histones[i].pos
        link.opacity = alpha
        link.radius = 0.025 + 0.045 * clamp(ai_controller.condense_drive, 0, 1)

def spawn_sparks(pos, count=8, col=SPARK_COLOR, strength=0.5):
    for _ in range(count):
        vel = random_unit() * random.uniform(0.12, strength)
        sparks.append(Spark(pos + random_unit() * 0.05, vel, col, radius=random.uniform(0.018, 0.04), life=random.uniform(1.0, 2.4)))

def update_particles(dt, time_value):
    global sparks, marks
    live_sparks = []
    for s in sparks:
        if s.update(dt):
            live_sparks.append(s)
        else:
            s.hide()
    sparks = live_sparks[-240:]

    live_marks = []
    for m in marks:
        if m.update(dt, time_value):
            live_marks.append(m)
        else:
            m.hide()
    marks = live_marks[-80:]

def mark_histone(h, strong=False):
    h.marked = True
    h.mark_timer = 2.2 if strong else 1.1
    marks.append(MarkDisk(h.pos + vector(0, -0.58, 0)))
    spawn_sparks(h.pos + vector(0, 0.6, 0), count=5 if not strong else 12, col=MARK_COLOR, strength=0.35)

def detach_random_segment():
    wrapped = [h for h in histones if h.wrap_progress > 0.28]
    if not wrapped:
        return
    h = random.choice(wrapped)
    h.target_wrap_progress = max(0, h.target_wrap_progress - random.uniform(0.12, 0.28))
    h.wrap_progress = min(h.wrap_progress, h.target_wrap_progress + 0.05)
    h.is_complete = False
    h.marked = False
    spawn_sparks(h.pos, count=16, col=vector(1.0, 0.55, 0.36), strength=0.55)

def clear_marks_and_particles():
    global sparks, marks
    for s in sparks:
        s.hide()
    for m in marks:
        m.hide()
    sparks = []
    marks = []
    for h in histones:
        h.marked = False
        h.mark_timer = 0

# ------------------------------------------------------------
# AI Controller
# ------------------------------------------------------------

class ExpressiveAIController:
    """
    Rule-based expressive AI controller.

    It reads state variables:
        - wrap fraction
        - number of complete histones
        - average DNA speed
        - coil drive
        - condense drive
        - recent progress / stagnation
        - current stage

    It takes actions:
        - move enzyme agents
        - mark histones
        - increase/decrease wrapping
        - apply orbit/coil/condense drives
        - detach or spill particles
        - reset and start new rounds

    Modes:
        scan, careful_wrap, coil, condense, playful, repair, ritual, disrupt, complete_pause
    """
    def __init__(self):
        self.mode = "scan"
        self.mode_timer = 0.0
        self.decision_timer = 0.0
        self.target_histone_index = 0
        self.wrap_drive = 0.0
        self.coil_drive = 0.0
        self.condense_drive = 0.0
        self.playfulness = 0.25
        self.chaos = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_progress = 0.0
        self.progress_history = deque(maxlen=120)
        self.round_cooldown = 0.0
        self.override = False

    def reset_soft(self):
        self.mode = "scan"
        self.mode_timer = 0.0
        self.decision_timer = 0.0
        self.target_histone_index = 0
        self.wrap_drive = 0.0
        self.coil_drive = 0.0
        self.condense_drive = 0.0
        self.chaos = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_progress = 0.0
        self.progress_history.clear()
        self.round_cooldown = 0.0

    def read_state(self):
        wrap_fraction = sum(h.wrap_progress for h in histones) / len(histones)
        complete_count = sum(1 for h in histones if h.is_complete)
        marked_count = sum(1 for h in histones if h.marked)
        avg_speed = sum(mag(b.vel) for b in all_beads) / len(all_beads)
        histone_speed = sum(mag(h.vel) for h in histones) / len(histones)
        progress = 0.52 * wrap_fraction + 0.25 * self.coil_drive + 0.23 * self.condense_drive
        return {
            "wrap_fraction": wrap_fraction,
            "complete_count": complete_count,
            "marked_count": marked_count,
            "avg_speed": avg_speed,
            "histone_speed": histone_speed,
            "progress": progress,
            "stage": global_stage,
            "spark_count": len(sparks),
            "all_complete": complete_count == len(histones),
        }

    def select_mode(self, state):
        if self.round_cooldown > 0:
            return "complete_pause"
        if state["all_complete"] and self.condense_drive > 0.95:
            return "complete_pause"
        if self.stagnation_timer > 6.0 and state["wrap_fraction"] < 0.95:
            return random.choice(["repair", "playful", "ritual"])
        if state["wrap_fraction"] < 0.12:
            return "scan"
        if state["wrap_fraction"] < 0.78:
            return random.choice(["careful_wrap", "careful_wrap", "playful", "ritual"])
        if self.coil_drive < 0.90:
            return random.choice(["coil", "coil", "ritual"])
        if self.condense_drive < 0.96:
            return random.choice(["condense", "condense", "playful"])
        return "complete_pause"

    def choose_target_histone(self, state):
        incomplete = [h for h in histones if h.wrap_progress < 0.96]
        if not incomplete:
            return histones[-1]
        if self.mode == "repair":
            return min(incomplete, key=lambda h: h.wrap_progress)
        if self.mode == "playful":
            return random.choice(incomplete)
        # Default: orderly left-to-right packaging.
        return min(incomplete, key=lambda h: (h.wrap_progress > 0.03, h.index))

    def update(self, dt, time_value):
        global human_override_timer

        state = self.read_state()
        self.progress_history.append(state["progress"])

        # Stagnation detector: low progress change and low movement.
        if len(self.progress_history) >= self.progress_history.maxlen:
            recent_change = max(self.progress_history) - min(self.progress_history)
            if recent_change < 0.018 and state["avg_speed"] < 0.035 and state["histone_speed"] < 0.025:
                self.stagnation_timer += dt
            else:
                self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 1.8)

        if state["all_complete"] and self.condense_drive > 0.96:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

        self.mode_timer += dt
        self.decision_timer -= dt
        self.round_cooldown = max(0.0, self.round_cooldown - dt)

        if self.decision_timer <= 0:
            old = self.mode
            self.mode = self.select_mode(state)
            self.decision_timer = random.uniform(2.2, 4.8)
            if self.mode != old:
                self.mode_timer = 0.0
                spawn_sparks(enzymes[0].pos, count=7, col=AI_COLOR, strength=0.35)

        if self.completion_timer > 5.0 or (self.stagnation_timer > 13.0 and state["progress"] > 0.2):
            reset_round(full_randomize=True)
            return

        target_histone = self.choose_target_histone(state)
        self.target_histone_index = target_histone.index

        # Human override temporarily amplifies motion and visible changes.
        override_boost = 1.0 + 1.7 * clamp(human_override_timer, 0, 1)

        if self.mode == "scan":
            self.action_scan(dt, time_value, target_histone, override_boost)
        elif self.mode == "careful_wrap":
            self.action_wrap(dt, time_value, target_histone, override_boost)
        elif self.mode == "coil":
            self.action_coil(dt, time_value, override_boost)
        elif self.mode == "condense":
            self.action_condense(dt, time_value, override_boost)
        elif self.mode == "playful":
            self.action_playful(dt, time_value, target_histone, override_boost)
        elif self.mode == "repair":
            self.action_repair(dt, time_value, target_histone, override_boost)
        elif self.mode == "ritual":
            self.action_ritual(dt, time_value, target_histone, override_boost)
        elif self.mode == "disrupt":
            self.action_disrupt(dt, time_value, override_boost)
        elif self.mode == "complete_pause":
            self.action_complete_pause(dt, time_value, state)

        # Keep drives bounded.
        self.wrap_drive = clamp(self.wrap_drive, 0, 1)
        self.coil_drive = clamp(self.coil_drive, 0, 1)
        self.condense_drive = clamp(self.condense_drive, 0, 1)
        self.chaos = clamp(self.chaos * 0.994, 0, 1)

    def action_scan(self, dt, time_value, target, boost):
        path_x = -6.2 + 12.4 * (0.5 + 0.5 * math.sin(time_value * 0.32))
        enzymes[0].mode = "scan"
        enzymes[0].target = vector(path_x, 1.7 + 0.2 * math.sin(time_value), 0.4 * math.cos(time_value * 0.7))
        enzymes[1].mode = "wait"
        enzymes[1].target = target.pos + vector(0, 1.3, -0.4)

        if self.mode_timer > 1.0:
            target.mark_timer = max(target.mark_timer, 0.25)
            target.marked = True
        target.target_wrap_progress = max(target.target_wrap_progress, 0.08 * boost)
        self.wrap_drive += dt * 0.04 * boost

    def action_wrap(self, dt, time_value, target, boost):
        enzymes[0].mode = "wrap"
        enzymes[1].mode = "guide"
        orbit = vector(0.65 * math.cos(time_value * 2.2), 0.7 + 0.12 * math.sin(time_value * 3.1), 0.65 * math.sin(time_value * 2.2))
        enzymes[0].target = target.pos + orbit
        enzymes[1].target = target.pos - orbit * 0.65 + vector(0, 0.35, 0)

        if self.mode_timer < 0.2 or random.random() < dt * 0.55:
            mark_histone(target, strong=False)

        target.target_wrap_progress += dt * random.uniform(0.12, 0.20) * boost
        self.wrap_drive += dt * 0.08 * boost

        # Pull nearby loose beads toward the active nucleosome.
        lo, hi = histone_base_range(target)
        for i in range(lo, hi + 1):
            for bead in (dna_left[i], dna_right[i]):
                bead.apply_force((target.pos - bead.pos) * 0.06 * boost)

    def action_coil(self, dt, time_value, boost):
        self.coil_drive += dt * 0.13 * boost
        enzymes[0].mode = "coil"
        enzymes[1].mode = "compact"
        center = vector(0, 0, 0)
        enzymes[0].target = vector(2.7 * math.cos(time_value * 0.9), 1.2, 1.2 * math.sin(time_value * 0.9))
        enzymes[1].target = vector(2.7 * math.cos(time_value * 0.9 + math.pi), 1.0, 1.2 * math.sin(time_value * 0.9 + math.pi))

        for h in histones:
            h.target_wrap_progress = max(h.target_wrap_progress, 1.0)
            radial = h.pos - center
            swirl = vector(-radial.z, 0, radial.x)
            h.apply_force(safe_norm(swirl) * dt * 0.35 * boost)
            h.mark_timer = max(h.mark_timer, 0.1)

        if random.random() < dt * 1.5:
            spawn_sparks(random.choice(histones).pos, count=2, col=CHROMATIN_COLOR, strength=0.22)

    def action_condense(self, dt, time_value, boost):
        self.coil_drive = max(self.coil_drive, 1.0)
        self.condense_drive += dt * 0.12 * boost
        enzymes[0].mode = "condense"
        enzymes[1].mode = "condense"
        enzymes[0].target = vector(-1.2, 1.7 + 0.2 * math.sin(time_value), 0.3)
        enzymes[1].target = vector(1.2, 1.7 + 0.2 * math.cos(time_value), -0.3)

        for h in histones:
            h.target_wrap_progress = 1.0
            h.apply_force((h.condense_target - h.pos) * dt * 0.85 * boost)
            if random.random() < dt * 0.7:
                h.mark_timer = max(h.mark_timer, 0.25)

        if random.random() < dt * 2.2:
            spawn_sparks(vector(0, 0, 0), count=3, col=CHROMOSOME_COLOR, strength=0.42)

    def action_playful(self, dt, time_value, target, boost):
        enzymes[0].mode = "play"
        enzymes[1].mode = "tease"
        self.playfulness = clamp(self.playfulness + dt * 0.08, 0, 1)
        self.chaos += dt * 0.06

        circle = vector(1.1 * math.cos(time_value * 3.2), 0.9 + 0.4 * math.sin(time_value * 2.4), 1.1 * math.sin(time_value * 3.2))
        enzymes[0].target = target.pos + circle
        enzymes[1].target = target.pos - circle * 0.8

        target.target_wrap_progress += dt * 0.09 * boost
        if random.random() < dt * 0.75:
            h = random.choice(histones)
            h.apply_force(random_unit() * 0.12)
            mark_histone(h, strong=random.random() < 0.22)
        if random.random() < dt * 0.65:
            spawn_sparks(target.pos, count=6, col=random.choice([SPARK_COLOR, MARK_COLOR, CHROMATIN_COLOR]), strength=0.65)

    def action_repair(self, dt, time_value, target, boost):
        enzymes[0].mode = "repair"
        enzymes[1].mode = "stabilize"
        enzymes[0].target = target.pos + vector(0, 0.85, 0.2 * math.sin(time_value * 2))
        enzymes[1].target = target.pos + vector(0.35 * math.cos(time_value * 1.6), 0.55, 0.35 * math.sin(time_value * 1.6))
        mark_histone(target, strong=False)
        target.target_wrap_progress += dt * 0.22 * boost
        self.stagnation_timer = max(0, self.stagnation_timer - dt * 2.0)

        # Repair means damping excess chaos and pulling loose segments back into the intended package.
        for bead in all_beads:
            bead.vel *= 0.985
            if bead.attached_histone == target:
                bead.apply_force((target.pos - bead.pos) * 0.025)

    def action_ritual(self, dt, time_value, target, boost):
        enzymes[0].mode = "ritual"
        enzymes[1].mode = "orbit"
        ritual_radius = 3.2
        enzymes[0].target = vector(ritual_radius * math.cos(time_value * 0.75), 1.55, ritual_radius * math.sin(time_value * 0.75) * 0.45)
        enzymes[1].target = vector(ritual_radius * math.cos(time_value * 0.75 + math.pi), 1.55, ritual_radius * math.sin(time_value * 0.75 + math.pi) * 0.45)

        wave = 0.5 + 0.5 * math.sin(time_value * 2.1)
        for h in histones:
            if h.index <= target.index or random.random() < dt * 0.08:
                h.target_wrap_progress += dt * (0.045 + 0.045 * wave) * boost
                h.mark_timer = max(h.mark_timer, 0.15 * wave)

        if random.random() < dt * 1.1:
            h = histones[int((time_value * 1.3) % len(histones))]
            marks.append(MarkDisk(h.pos + vector(0, -0.58, 0), col=vector(0.84, 0.68, 1.0), life=3.0))

    def action_disrupt(self, dt, time_value, boost):
        enzymes[0].mode = "disrupt"
        enzymes[1].mode = "scatter"
        self.chaos += dt * 0.18
        enzymes[0].target = vector(random.uniform(-4, 4), random.uniform(0.4, 2.3), random.uniform(-2, 2))
        enzymes[1].target = vector(random.uniform(-4, 4), random.uniform(0.4, 2.3), random.uniform(-2, 2))
        if random.random() < dt * 1.2:
            detach_random_segment()

    def action_complete_pause(self, dt, time_value, state):
        enzymes[0].mode = "complete"
        enzymes[1].mode = "complete"
        enzymes[0].target = vector(-1.5, 2.3, 0.3)
        enzymes[1].target = vector(1.5, 2.3, -0.3)
        self.condense_drive = max(self.condense_drive, 1.0)
        for h in histones:
            h.target_wrap_progress = 1.0
            h.mark_timer = max(h.mark_timer, 0.05)
        if random.random() < dt * 1.4:
            spawn_sparks(vector(0, 0.2, 0), count=3, col=CHROMOSOME_COLOR, strength=0.35)

ai_controller = ExpressiveAIController()

# ------------------------------------------------------------
# Human controls
# ------------------------------------------------------------

def print_controls():
    print(__doc__)

def set_mode(mode):
    ai_controller.mode = mode
    ai_controller.mode_timer = 0
    ai_controller.decision_timer = 3.0

def keydown(evt):
    global paused, ai_enabled, human_override_timer

    key = evt.key.lower()
    if key == "h":
        print_controls()
    elif key == " ":
        paused = not paused
    elif key == "a":
        ai_enabled = not ai_enabled
    elif key == "r":
        reset_round(full_randomize=True)
    elif key == "1":
        set_mode("scan")
    elif key == "2":
        set_mode("careful_wrap")
    elif key == "3":
        set_mode("coil")
    elif key == "4":
        set_mode("condense")
    elif key == "5":
        set_mode("playful")
    elif key == "6":
        set_mode("repair")
    elif key == "7":
        set_mode("ritual")
    elif key == "o":
        human_override_timer = 1.0
        spawn_sparks(vector(0, 1.1, 0), count=35, col=AI_COLOR, strength=0.9)
    elif key == "d":
        detach_random_segment()
    elif key == "m":
        h = ai_controller.choose_target_histone(ai_controller.read_state())
        mark_histone(h, strong=True)
    elif key == "c":
        clear_marks_and_particles()

scene.bind("keydown", keydown)

# ------------------------------------------------------------
# UI/status updates
# ------------------------------------------------------------

def update_status():
    state = ai_controller.read_state()
    status_label.text = (
        f"Round: {round_number}\n"
        f"AI: {'ON' if ai_enabled else 'OFF'} | Mode: {ai_controller.mode}\n"
        f"Stage: {global_stage}  "
        f"Wrap: {state['wrap_fraction']*100:5.1f}%  "
        f"Complete histones: {state['complete_count']}/{N_HISTONES}\n"
        f"Coil drive: {ai_controller.coil_drive:4.2f}  "
        f"Condense drive: {ai_controller.condense_drive:4.2f}\n"
        f"Avg DNA speed: {state['avg_speed']:5.3f}  "
        f"Stagnation: {ai_controller.stagnation_timer:4.1f}s\n"
        f"Space pause | A AI | R reset | 1-7 modes | O override"
    )

    legend_label.text = (
        "Objects / interactions\n"
        "• colored base beads = DNA bases\n"
        "• lavender spheres = histone proteins\n"
        "• rings/links = nucleosomes and chromatin fiber\n"
        "• blue/purple agents = AI remodeler + condensin\n"
        "• marks/sparks = AI decisions, attachment, repair, reset signals\n"
        "• final X shape = condensed chromosome"
    )

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

print("DNA Packaging into Chromosomes simulation loaded.")
print("Press H in the VPython window to print controls.")

dt = 1 / 60.0
status_timer = 0.0

while True:
    rate(60)
    if paused:
        update_status()
        continue

    time_value += dt
    human_override_timer = max(0.0, human_override_timer - dt)

    if ai_enabled:
        ai_controller.update(dt, time_value)

    # Minimal non-AI automatic progression so the simulation still runs if AI is off.
    if not ai_enabled:
        for h in histones:
            if h.marked:
                h.target_wrap_progress += dt * 0.025

    update_dna_targets(time_value)
    apply_dna_physics(dt, time_value)

    for h in histones:
        h.update(dt, time_value)

    for e in enzymes:
        e.update(dt, time_value)

    update_connectors()
    update_histone_links()
    update_particles(dt, time_value)

    # Visual condensation chromosome body: two translucent arms appear late.
    # Created lazily to keep reset logic simple.
    if "chromosome_arms" not in globals():
        chromosome_arms = [
            cylinder(pos=vector(-1.05, 1.35, 0), axis=vector(2.1, -2.7, 0), radius=0.13, color=CHROMOSOME_COLOR, opacity=0),
            cylinder(pos=vector(1.05, 1.35, 0), axis=vector(-2.1, -2.7, 0), radius=0.13, color=CHROMOSOME_COLOR, opacity=0),
            sphere(pos=vector(0, 0, 0), radius=0.26, color=CHROMOSOME_COLOR, opacity=0),
        ]

    arm_alpha = 0.0
    if global_stage >= 3:
        arm_alpha = 0.18 + 0.44 * ai_controller.condense_drive
    for arm in chromosome_arms:
        arm.opacity = arm_alpha

    status_timer += dt
    if status_timer > 0.18:
        status_timer = 0.0
        update_status()
