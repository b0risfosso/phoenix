"""
DNA Transcription into RNA — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python dna_transcription_rna_ai_vpython.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    O       human override: polymerase pulse + nucleotide spill
    C       clear temporary marks/spark particles
    + / =   increase AI transcription speed
    - / _   decrease AI transcription speed
    H       print controls

Scene concept:
    A DNA segment opens at a moving transcription bubble. RNA polymerase travels along
    the template strand. Free RNA nucleotides orbit, collide near the active site,
    attach by base-pair rules, then become part of a growing mRNA strand. The mRNA
    detaches from the DNA path and floats away as a transcript tail.

This file is self-contained and intentionally uses VPython primitives only.
"""

from vpython import *
from math import sin, cos, pi
import random

# -----------------------------------------------------------------------------
# Scene setup
# -----------------------------------------------------------------------------
scene = canvas(
    title="DNA Transcription into RNA — AI Controlled VPython Simulation",
    width=1280,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0.2, 0),
)
scene.forward = vector(-0.45, -0.25, -1.0)
scene.range = 12
scene.lights = []
distant_light(direction=vector(0.2, -0.5, -0.8), color=vector(0.9, 0.95, 1.0))
distant_light(direction=vector(-0.7, -0.4, 0.4), color=vector(1.0, 0.95, 0.85))

# -----------------------------------------------------------------------------
# Colors and constants
# -----------------------------------------------------------------------------
DNA_A = vector(0.98, 0.72, 0.32)
DNA_T = vector(0.35, 0.66, 0.96)
DNA_C = vector(0.62, 0.80, 0.44)
DNA_G = vector(0.88, 0.50, 0.73)
BACKBONE_1 = vector(0.38, 0.50, 0.86)
BACKBONE_2 = vector(0.48, 0.70, 0.88)
RNA_BACKBONE = vector(0.95, 0.45, 0.20)
POLYMERASE = vector(1.0, 0.82, 0.28)
POLYMERASE_DARK = vector(0.90, 0.58, 0.10)
BUBBLE_COLOR = vector(1.0, 0.94, 0.65)
GRID_COLOR = vector(0.72, 0.78, 0.84)
MARK_COLOR = vector(0.15, 0.52, 0.95)

DNA_BASE_COLORS = {"A": DNA_A, "T": DNA_T, "C": DNA_C, "G": DNA_G}
RNA_BASE_COLORS = {"A": DNA_T, "U": vector(0.85, 0.65, 1.0), "C": DNA_C, "G": DNA_G}
RNA_PAIR_FOR_TEMPLATE = {"A": "U", "T": "A", "C": "G", "G": "C"}
DNA_PAIR = {"A": "T", "T": "A", "C": "G", "G": "C"}

N_BASES = 34
BASE_SPACING = 0.52
HELIX_RADIUS = 1.15
HELIX_TWIST = 0.72
BUBBLE_HALF_WIDTH = 3.2
ATTACH_DISTANCE = 0.55
WORLD_BOUNDARY = 9.8

random.seed(7)

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def helix_center(index):
    x = (index - (N_BASES - 1) / 2.0) * BASE_SPACING
    return vector(x, 0, 0)


def strand_positions(index, open_amount):
    theta = index * HELIX_TWIST
    center = helix_center(index)
    radial = vector(0, cos(theta), sin(theta))
    p1_closed = center + radial * HELIX_RADIUS
    p2_closed = center - radial * HELIX_RADIUS
    # Open bubble pulls the strands apart and slightly upward/downward.
    open_dir = safe_norm(radial + vector(0, 0.18, 0.08))
    p1 = p1_closed + open_dir * open_amount
    p2 = p2_closed - open_dir * open_amount
    return p1, p2


def make_text_label(text, pos, height=0.22, color_value=vector(0.12, 0.16, 0.23), box=False):
    return label(
        text=text,
        pos=pos,
        height=height,
        color=color_value,
        box=box,
        opacity=0.0 if not box else 0.12,
        line=False,
    )

# -----------------------------------------------------------------------------
# Ground and explanatory labels
# -----------------------------------------------------------------------------
ground = box(pos=vector(0, -2.35, 0), size=vector(20, 0.04, 7.5), color=vector(0.91, 0.94, 0.96), opacity=0.85)
for gx in range(-10, 11):
    curve(pos=[vector(gx, -2.32, -3.7), vector(gx, -2.32, 3.7)], color=GRID_COLOR, radius=0.008, opacity=0.45)
for gz in range(-4, 5):
    curve(pos=[vector(-10, -2.31, gz), vector(10, -2.31, gz)], color=GRID_COLOR, radius=0.008, opacity=0.45)

main_title = make_text_label("DNA transcription: DNA opens → RNA polymerase moves → mRNA grows and detaches", vector(0, 3.65, 0), 0.26)
status_label = make_text_label("", vector(-8.9, 3.15, 0), 0.18)
mode_label = make_text_label("", vector(6.2, 3.15, 0), 0.18)
controls_label = make_text_label("A AI  |  P pause  |  R reset  |  M mode  |  O override  |  +/- speed  |  H help", vector(0, -2.8, 0), 0.17)

# -----------------------------------------------------------------------------
# Simulation object classes
# -----------------------------------------------------------------------------
class DNAUnit:
    def __init__(self, index, base_template):
        self.index = index
        self.template_base = base_template
        self.coding_base = DNA_PAIR[base_template]
        self.open_amount = 0.0
        self.transcribed = False
        self.marked = False
        p1, p2 = strand_positions(index, 0)
        self.template_sugar = sphere(pos=p1, radius=0.13, color=BACKBONE_1, opacity=0.92)
        self.coding_sugar = sphere(pos=p2, radius=0.13, color=BACKBONE_2, opacity=0.92)
        self.template_base_obj = box(pos=lerp(p1, p2, 0.37), size=vector(0.34, 0.12, 0.12), color=DNA_BASE_COLORS[base_template], opacity=0.95)
        self.coding_base_obj = box(pos=lerp(p1, p2, 0.63), size=vector(0.34, 0.12, 0.12), color=DNA_BASE_COLORS[self.coding_base], opacity=0.95)
        self.rung = cylinder(pos=p1, axis=p2 - p1, radius=0.035, color=vector(0.78, 0.82, 0.86), opacity=0.7)
        self.template_label = make_text_label(base_template, p1 + vector(0, 0.20, 0), 0.11, color.white, box=True)
        self.coding_label = make_text_label(self.coding_base, p2 - vector(0, 0.20, 0), 0.11, color.white, box=True)
        self.mark = sphere(pos=vector(0, 0, 0), radius=0.07, color=MARK_COLOR, opacity=0.0, emissive=True)

    def update(self, bubble_center_index, bubble_width, dt):
        dist = abs(self.index - bubble_center_index)
        target_open = 0.0
        if dist < bubble_width:
            target_open = (1.0 - dist / bubble_width) ** 0.55 * 1.25
        self.open_amount += (target_open - self.open_amount) * min(1.0, dt * 6.5)
        p1, p2 = strand_positions(self.index, self.open_amount)
        self.template_sugar.pos = p1
        self.coding_sugar.pos = p2
        self.template_base_obj.pos = lerp(p1, p2, 0.35)
        self.coding_base_obj.pos = lerp(p1, p2, 0.65)
        self.rung.pos = p1
        self.rung.axis = p2 - p1
        self.rung.opacity = 0.25 + 0.55 * (1.0 - clamp(self.open_amount / 1.25, 0, 1))
        self.template_label.pos = p1 + vector(0, 0.20, 0)
        self.coding_label.pos = p2 - vector(0, 0.20, 0)
        self.template_base_obj.opacity = 0.95
        self.coding_base_obj.opacity = 0.95
        if self.transcribed:
            self.mark.opacity = 0.85
            self.mark.pos = p1 + vector(0, 0.38, 0)
        else:
            self.mark.opacity *= 0.95

    def template_site(self):
        p1, _ = strand_positions(self.index, self.open_amount)
        return p1

    def expected_rna(self):
        return RNA_PAIR_FOR_TEMPLATE[self.template_base]

    def hide(self):
        for obj in [self.template_sugar, self.coding_sugar, self.template_base_obj, self.coding_base_obj, self.rung, self.template_label, self.coding_label, self.mark]:
            obj.visible = False


class RNANucleotide:
    def __init__(self, nucleotide_id, base=None):
        self.id = nucleotide_id
        self.base = base or random.choice(list(RNA_BASE_COLORS.keys()))
        self.attached = False
        self.used = False
        self.target_index = None
        self.angle = random.random() * 2 * pi
        self.speed = random.uniform(0.8, 1.45)
        self.radius = random.uniform(1.1, 2.8)
        self.vel = vector(random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.1), random.uniform(-0.25, 0.25))
        self.obj = sphere(pos=self.random_free_position(), radius=0.13, color=RNA_BASE_COLORS[self.base], opacity=0.92, emissive=False, make_trail=True, retain=12, trail_radius=0.012)
        self.label = make_text_label(self.base, self.obj.pos + vector(0, 0.22, 0), 0.10, color.white, box=True)
        self.glow = sphere(pos=self.obj.pos, radius=0.20, color=RNA_BASE_COLORS[self.base], opacity=0.10, emissive=True)

    def random_free_position(self):
        x = random.uniform(-8.5, 8.5)
        y = random.uniform(-0.9, 2.4)
        z = random.choice([-1, 1]) * random.uniform(2.3, 4.3)
        return vector(x, y, z)

    def reset_free(self, base=None):
        self.base = base or random.choice(list(RNA_BASE_COLORS.keys()))
        self.attached = False
        self.used = False
        self.target_index = None
        self.angle = random.random() * 2 * pi
        self.radius = random.uniform(1.2, 3.1)
        self.vel = vector(random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.1), random.uniform(-0.25, 0.25))
        self.obj.clear_trail()
        self.obj.pos = self.random_free_position()
        self.obj.color = RNA_BASE_COLORS[self.base]
        self.obj.opacity = 0.92
        self.obj.visible = True
        self.label.visible = True
        self.label.text = self.base
        self.glow.visible = True
        self.glow.color = RNA_BASE_COLORS[self.base]
        self.glow.opacity = 0.10

    def update_free(self, dt, polymerase_pos, attract_strength, chaos, orbit_bias):
        if self.attached or self.used:
            return
        to_poly = polymerase_pos - self.obj.pos
        d = mag(to_poly)
        if d < 6.0:
            self.vel += safe_norm(to_poly) * attract_strength * dt / max(0.7, d)
        self.angle += dt * self.speed * (0.7 + orbit_bias)
        orbit_center = polymerase_pos + vector(0, -0.15, 0)
        desired = orbit_center + vector(cos(self.angle) * self.radius * 0.2, sin(self.angle * 0.7) * 0.4, sin(self.angle) * self.radius)
        self.vel += (desired - self.obj.pos) * 0.08 * orbit_bias * dt
        self.vel += vector(random.uniform(-chaos, chaos), random.uniform(-chaos, chaos), random.uniform(-chaos, chaos)) * dt
        self.vel *= 0.992
        self.obj.pos += self.vel * dt
        if abs(self.obj.pos.x) > WORLD_BOUNDARY:
            self.obj.pos.x = clamp(self.obj.pos.x, -WORLD_BOUNDARY, WORLD_BOUNDARY)
            self.vel.x *= -0.7
        if self.obj.pos.y < -2.0 or self.obj.pos.y > 3.3:
            self.obj.pos.y = clamp(self.obj.pos.y, -2.0, 3.3)
            self.vel.y *= -0.7
        if abs(self.obj.pos.z) > 4.8:
            self.obj.pos.z = clamp(self.obj.pos.z, -4.8, 4.8)
            self.vel.z *= -0.7
        self.label.pos = self.obj.pos + vector(0, 0.22, 0)
        self.glow.pos = self.obj.pos
        self.glow.opacity = 0.08 + 0.08 * sin(self.angle) ** 2

    def attach_to(self, pos, target_index):
        self.attached = True
        self.used = True
        self.target_index = target_index
        self.obj.clear_trail()
        self.obj.pos = pos
        self.vel = vector(0, 0, 0)
        self.glow.opacity = 0.32
        self.label.pos = self.obj.pos + vector(0, 0.22, 0)
        self.glow.pos = self.obj.pos

    def follow(self, pos, detached=False):
        if not self.used:
            return
        self.obj.pos = pos
        self.label.pos = pos + vector(0, 0.22, 0)
        self.glow.pos = pos
        self.glow.opacity = 0.16 if detached else 0.30

    def hide(self):
        self.obj.visible = False
        self.label.visible = False
        self.glow.visible = False


class MessengerRNA:
    def __init__(self):
        self.nucleotides = []
        self.backbone_segments = []
        self.detached_lift = 0.0
        self.complete = False
        self.drift_phase = 0.0

    def reset(self):
        for seg in self.backbone_segments:
            seg.visible = False
        self.backbone_segments = []
        self.nucleotides = []
        self.detached_lift = 0.0
        self.complete = False
        self.drift_phase = 0.0

    def add(self, nucleotide):
        self.nucleotides.append(nucleotide)
        if len(self.nucleotides) >= 2:
            seg = cylinder(pos=self.nucleotides[-2].obj.pos, axis=self.nucleotides[-1].obj.pos - self.nucleotides[-2].obj.pos, radius=0.04, color=RNA_BACKBONE, opacity=0.85)
            self.backbone_segments.append(seg)

    def base_position_for_index(self, dna_index, polymerase_index, detached_lift):
        site = dna_units[dna_index].template_site()
        lag = max(0, polymerase_index - dna_index) * 0.06
        detach = clamp((polymerase_index - dna_index) / 7.0, 0, 1)
        curl = sin(dna_index * 0.85 + self.drift_phase) * 0.25
        return site + vector(0, 0.43 + detached_lift * detach + lag, 0.42 + curl + 1.2 * detach)

    def update(self, dt, polymerase_index):
        self.drift_phase += dt * 1.7
        if self.complete:
            self.detached_lift += dt * 0.28
        for i, nt in enumerate(self.nucleotides):
            dna_index = nt.target_index
            lift = self.detached_lift + max(0, polymerase_index - dna_index) * 0.10
            pos = self.base_position_for_index(dna_index, polymerase_index, lift)
            if self.complete:
                pos += vector(sin(self.drift_phase + i * 0.4) * 0.18, self.detached_lift * 0.40, 0.65 + cos(self.drift_phase * 0.5 + i) * 0.13)
            nt.follow(pos, detached=(polymerase_index - dna_index > 4 or self.complete))
        for j, seg in enumerate(self.backbone_segments):
            a = self.nucleotides[j].obj.pos
            b = self.nucleotides[j + 1].obj.pos
            seg.pos = a
            seg.axis = b - a
            seg.opacity = 0.82 if not self.complete else 0.70


class Polymerase:
    def __init__(self):
        self.index_float = 0.0
        self.speed = 0.85
        self.target_speed = 0.85
        self.active_index = 0
        self.pulse_phase = 0.0
        self.obj = ellipsoid(pos=vector(0, 0, 0), length=1.25, height=1.05, width=1.15, color=POLYMERASE, opacity=0.86)
        self.core = sphere(pos=vector(0, 0, 0), radius=0.34, color=POLYMERASE_DARK, opacity=0.70, emissive=True)
        self.active_site = sphere(pos=vector(0, 0, 0), radius=0.14, color=vector(1.0, 0.35, 0.08), opacity=0.75, emissive=True)
        self.label = make_text_label("RNA polymerase", vector(0, 0, 0), 0.15, vector(0.17, 0.12, 0.03), box=True)
        self.wake = curve(color=POLYMERASE_DARK, radius=0.025, retain=35)

    def reset(self):
        self.index_float = 0.0
        self.target_speed = 0.85
        self.speed = 0.85
        self.active_index = 0
        self.pulse_phase = 0.0
        self.wake.clear()

    def update(self, dt, paused=False):
        if not paused:
            self.speed += (self.target_speed - self.speed) * min(1.0, dt * 3.0)
            self.index_float += self.speed * dt
            self.index_float = clamp(self.index_float, 0, N_BASES - 1)
        self.active_index = int(clamp(round(self.index_float), 0, N_BASES - 1))
        site = dna_units[self.active_index].template_site()
        self.pulse_phase += dt * (4.0 + self.speed)
        self.obj.pos = site + vector(0, 0.18 + 0.05 * sin(self.pulse_phase), 0.36)
        self.obj.length = 1.25 + 0.08 * sin(self.pulse_phase)
        self.core.pos = self.obj.pos + vector(0.22, 0.05, 0.02)
        self.core.radius = 0.31 + 0.05 * sin(self.pulse_phase * 1.7) ** 2
        self.active_site.pos = site + vector(0, 0.48, 0.52)
        self.active_site.radius = 0.13 + 0.045 * sin(self.pulse_phase * 2.1) ** 2
        self.label.pos = self.obj.pos + vector(0, 0.82, 0)
        self.wake.append(self.obj.pos - vector(0.12, 0.0, 0.2))

    def complete(self):
        return self.index_float >= N_BASES - 1.1


class TranscriptionAI:
    MODES = ["careful", "fast", "recruit", "playful", "ritual", "chaotic", "repair", "artist"]

    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.timer = 0.0
        self.mode_duration = 7.0
        self.last_progress = 0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.round_count = 1
        self.override_timer = 0.0
        self.human_override_timer = 0.0
        self.base_speed_bonus = 0.0
        self.message = "AI active"

    def reset(self):
        self.timer = 0.0
        self.mode_duration = random.uniform(5.5, 9.5)
        self.last_progress = 0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.override_timer = 0.0
        self.human_override_timer = 0.0
        self.message = "new transcription round"

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.timer = 0.0
        self.mode_duration = random.uniform(5.0, 8.5)
        self.message = "mode changed"

    def set_mode(self, mode):
        if mode in self.MODES:
            self.mode_index = self.MODES.index(mode)
            self.mode = mode
            self.timer = 0.0
            self.mode_duration = random.uniform(5.0, 9.0)
            self.message = "state reaction"

    def state(self):
        return {
            "polymerase_index": polymerase.index_float,
            "active_index": polymerase.active_index,
            "mrna_length": len(mrna.nucleotides),
            "free_nucleotides": sum(1 for n in rna_pool if not n.used),
            "complete": mrna.complete,
            "paused": paused,
            "round": self.round_count,
            "mode": self.mode,
        }

    def detect_stagnation_or_completion(self, dt):
        progress = len(mrna.nucleotides)
        if progress <= self.last_progress:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = 0.0
            self.last_progress = progress
        if progress >= N_BASES or polymerase.complete():
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0
        no_free = sum(1 for n in rna_pool if not n.used) < 4
        return self.stagnation_timer > 7.5 or self.completion_timer > 5.0 or no_free

    def choose_mode_from_state(self):
        free_count = sum(1 for n in rna_pool if not n.used)
        attached_count = len(mrna.nucleotides)
        if mrna.complete:
            return "artist"
        if self.stagnation_timer > 4.5:
            return "repair"
        if free_count < 8:
            return "recruit"
        if attached_count > N_BASES * 0.72 and self.mode not in ["artist", "fast"]:
            return "fast"
        return None

    def update(self, dt):
        global paused
        if not self.enabled:
            polymerase.target_speed = 0.75 + self.base_speed_bonus
            return
        self.timer += dt
        if self.human_override_timer > 0:
            self.human_override_timer -= dt
        if self.timer > self.mode_duration:
            self.cycle_mode()
        reaction_mode = self.choose_mode_from_state()
        if reaction_mode and reaction_mode != self.mode:
            self.set_mode(reaction_mode)
        if self.detect_stagnation_or_completion(dt):
            self.completion_timer += dt
            if self.completion_timer > 2.0:
                reset_simulation(new_round=True)
                return
        # Behavior parameters. These change visible simulation movement.
        if self.mode == "careful":
            polymerase.target_speed = 0.55 + self.base_speed_bonus
            self.organize_correct_nucleotides(strength=0.42, scatter_wrong=True)
            self.message = "carefully matching bases"
        elif self.mode == "fast":
            polymerase.target_speed = 1.35 + self.base_speed_bonus
            self.organize_correct_nucleotides(strength=0.34, scatter_wrong=False)
            self.message = "accelerating transcription"
        elif self.mode == "recruit":
            polymerase.target_speed = 0.75 + self.base_speed_bonus
            self.recruit_nucleotides()
            self.message = "recruiting loose RNA nucleotides"
        elif self.mode == "playful":
            polymerase.target_speed = 0.82 + self.base_speed_bonus
            self.make_orbits(playful=True)
            self.message = "playful nucleotide orbit patterns"
        elif self.mode == "ritual":
            polymerase.target_speed = 0.68 + self.base_speed_bonus
            self.ritual_pulses()
            self.message = "ritual pulse at active site"
        elif self.mode == "chaotic":
            polymerase.target_speed = 1.05 + self.base_speed_bonus
            self.chaotic_spill()
            self.message = "controlled chaos and collisions"
        elif self.mode == "repair":
            polymerase.target_speed = 0.35 + self.base_speed_bonus
            self.repair_missing_match()
            self.message = "repairing stalled active site"
        elif self.mode == "artist":
            polymerase.target_speed = 0.12 + self.base_speed_bonus
            self.artistic_marks()
            self.message = "drawing completion marks"

    def expected_base(self):
        return dna_units[polymerase.active_index].expected_rna()

    def organize_correct_nucleotides(self, strength=0.35, scatter_wrong=False):
        expected = self.expected_base()
        target = polymerase.active_site.pos
        for nt in rna_pool:
            if nt.used:
                continue
            if nt.base == expected:
                nt.vel += safe_norm(target - nt.obj.pos) * strength * 0.035
            elif scatter_wrong:
                nt.vel += safe_norm(nt.obj.pos - target) * 0.006

    def recruit_nucleotides(self):
        expected = self.expected_base()
        target = polymerase.active_site.pos + vector(0, 0.1, 0)
        matching = [nt for nt in rna_pool if not nt.used and nt.base == expected]
        if len(matching) < 3:
            for nt in rna_pool:
                if not nt.used and random.random() < 0.02:
                    nt.base = expected
                    nt.obj.color = RNA_BASE_COLORS[expected]
                    nt.glow.color = RNA_BASE_COLORS[expected]
                    nt.label.text = expected
        for nt in rna_pool:
            if not nt.used:
                nt.vel += safe_norm(target - nt.obj.pos) * 0.018

    def make_orbits(self, playful=False):
        center = polymerase.obj.pos
        for k, nt in enumerate(rna_pool):
            if nt.used:
                continue
            phase = scene_time * (1.0 + 0.04 * k) + k * 0.7
            desired = center + vector(cos(phase) * 1.1, sin(phase * 1.3) * 0.55, sin(phase) * 1.8)
            nt.vel += (desired - nt.obj.pos) * (0.018 if playful else 0.012)

    def ritual_pulses(self):
        if int(scene_time * 2) % 2 == 0:
            self.organize_correct_nucleotides(strength=0.55, scatter_wrong=False)
        for nt in rna_pool:
            if not nt.used:
                nt.glow.opacity = 0.18 + 0.16 * sin(scene_time * 5 + nt.id) ** 2

    def chaotic_spill(self):
        if random.random() < 0.035:
            make_spark(polymerase.obj.pos + vector(random.uniform(-0.4, 0.4), 0.4, random.uniform(-0.4, 0.4)), vector(1.0, 0.55, 0.18), life=1.2)
        for nt in rna_pool:
            if not nt.used and random.random() < 0.035:
                nt.vel += vector(random.uniform(-0.45, 0.45), random.uniform(-0.2, 0.35), random.uniform(-0.45, 0.45))

    def repair_missing_match(self):
        expected = self.expected_base()
        target = polymerase.active_site.pos
        best = None
        best_dist = 999
        for nt in rna_pool:
            if nt.used:
                continue
            if nt.base != expected:
                continue
            d = mag(nt.obj.pos - target)
            if d < best_dist:
                best = nt
                best_dist = d
        if best is None:
            for nt in rna_pool:
                if not nt.used:
                    nt.base = expected
                    nt.obj.color = RNA_BASE_COLORS[expected]
                    nt.glow.color = RNA_BASE_COLORS[expected]
                    nt.label.text = expected
                    best = nt
                    break
        if best:
            best.vel += safe_norm(target - best.obj.pos) * 0.09

    def artistic_marks(self):
        for i, unit in enumerate(dna_units):
            if unit.transcribed and random.random() < 0.015:
                make_spark(unit.template_site() + vector(0, 0.55, 0.35), RNA_BACKBONE, life=1.8)


# -----------------------------------------------------------------------------
# World state containers
# -----------------------------------------------------------------------------
dna_units = []
rna_pool = []
mrna = MessengerRNA()
polymerase = None
ai = None
sparks = []
scene_time = 0.0
paused = False

# Backbone curves; recreated on reset.
backbone_curve_1 = None
backbone_curve_2 = None
bubble_shell = None
progress_bar = None
progress_fill = None

# -----------------------------------------------------------------------------
# Spark / mark particles
# -----------------------------------------------------------------------------
class Spark:
    def __init__(self, pos, color_value, life=1.0):
        self.life = life
        self.max_life = life
        self.vel = vector(random.uniform(-0.15, 0.15), random.uniform(0.05, 0.35), random.uniform(-0.15, 0.15))
        self.obj = sphere(pos=pos, radius=random.uniform(0.035, 0.075), color=color_value, opacity=0.75, emissive=True, make_trail=True, retain=8, trail_radius=0.006)

    def update(self, dt):
        self.life -= dt
        self.obj.pos += self.vel * dt
        self.vel *= 0.985
        self.obj.opacity = max(0, self.life / self.max_life) * 0.75
        self.obj.radius *= 0.997
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


def make_spark(pos, color_value, life=1.0):
    sparks.append(Spark(pos, color_value, life))


def clear_sparks():
    for sp in sparks:
        sp.obj.visible = False
    sparks.clear()

# -----------------------------------------------------------------------------
# Build and reset functions
# -----------------------------------------------------------------------------
def generate_template_sequence():
    motif = "TACGGCATTAACCGTACGATTCGGCATAGCTAAG"
    seq = []
    for i in range(N_BASES):
        if i < len(motif):
            seq.append(motif[i])
        else:
            seq.append(random.choice("ATCG"))
    return seq


def build_world():
    global dna_units, rna_pool, polymerase, ai, backbone_curve_1, backbone_curve_2, bubble_shell, progress_bar, progress_fill
    template_seq = generate_template_sequence()
    dna_units = [DNAUnit(i, template_seq[i]) for i in range(N_BASES)]
    backbone_curve_1 = curve(color=BACKBONE_1, radius=0.045, opacity=0.62)
    backbone_curve_2 = curve(color=BACKBONE_2, radius=0.045, opacity=0.62)
    for unit in dna_units:
        p1, p2 = strand_positions(unit.index, 0)
        backbone_curve_1.append(p1)
        backbone_curve_2.append(p2)
    rna_pool = [RNANucleotide(i) for i in range(86)]
    polymerase = Polymerase()
    ai = TranscriptionAI()
    bubble_shell = ellipsoid(pos=vector(0, 0, 0), length=2.4, height=2.2, width=2.0, color=BUBBLE_COLOR, opacity=0.14)
    progress_bar = box(pos=vector(0, -2.05, -3.25), size=vector(17.0, 0.08, 0.08), color=vector(0.78, 0.83, 0.88), opacity=0.7)
    progress_fill = box(pos=vector(-8.5, -1.92, -3.25), size=vector(0.05, 0.10, 0.12), color=RNA_BACKBONE, opacity=0.88)


def reset_simulation(new_round=False):
    global scene_time
    mrna.complete = False
    mrna.reset()
    polymerase.reset()
    for unit in dna_units:
        unit.transcribed = False
        unit.marked = False
        unit.open_amount = 0.0
    for i, nt in enumerate(rna_pool):
        nt.reset_free()
    clear_sparks()
    if new_round:
        ai.round_count += 1
    ai.reset()
    scene_time = 0.0

# -----------------------------------------------------------------------------
# Transcription mechanics
# -----------------------------------------------------------------------------
def find_candidate_nucleotide(expected_base):
    target = polymerase.active_site.pos
    candidates = []
    for nt in rna_pool:
        if nt.used:
            continue
        d = mag(nt.obj.pos - target)
        if nt.base == expected_base:
            candidates.append((d, nt))
    candidates.sort(key=lambda item: item[0])
    if candidates and candidates[0][0] < ATTACH_DISTANCE:
        return candidates[0][1]
    return None


def try_attach_current_base(dt):
    idx = polymerase.active_index
    if dna_units[idx].transcribed:
        return
    # Only attach when the transcription bubble is open enough.
    if dna_units[idx].open_amount < 0.55:
        return
    expected = dna_units[idx].expected_rna()
    candidate = find_candidate_nucleotide(expected)
    if candidate is not None:
        attach_pos = mrna.base_position_for_index(idx, polymerase.index_float, 0.0)
        candidate.attach_to(attach_pos, idx)
        mrna.add(candidate)
        dna_units[idx].transcribed = True
        dna_units[idx].marked = True
        make_spark(attach_pos, RNA_BASE_COLORS[expected], life=1.1)
    else:
        # A gentle visible signal when no matching base has arrived.
        if random.random() < 0.025:
            make_spark(polymerase.active_site.pos, vector(0.95, 0.35, 0.20), life=0.7)


def update_backbone_curves():
    # VPython curve point mutation support differs by version, so rebuild with clear+append.
    backbone_curve_1.clear()
    backbone_curve_2.clear()
    for unit in dna_units:
        p1, p2 = strand_positions(unit.index, unit.open_amount)
        backbone_curve_1.append(p1)
        backbone_curve_2.append(p2)


def update_progress_visual():
    progress = clamp(len(mrna.nucleotides) / float(N_BASES), 0, 1)
    progress_fill.size = vector(17.0 * progress, 0.10, 0.12)
    progress_fill.pos = vector(-8.5 + 8.5 * progress, -1.92, -3.25)


def update_status_labels():
    s = ai.state()
    status_label.text = (
        f"round {s['round']} | mRNA {s['mrna_length']}/{N_BASES} | "
        f"polymerase index {s['active_index']} | free RNA {s['free_nucleotides']}"
    )
    mode_label.text = (
        f"AI {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode} | {ai.message}\n"
        f"speed {polymerase.speed:.2f} | paused {'YES' if paused else 'NO'}"
    )


def update_bubble_visual():
    site = dna_units[polymerase.active_index].template_site()
    bubble_shell.pos = site + vector(0, 0.04, 0.0)
    pulse = 0.12 * sin(scene_time * 4.0) ** 2
    bubble_shell.length = 2.6 + pulse
    bubble_shell.height = 2.0 + pulse
    bubble_shell.width = 2.1 + pulse

# -----------------------------------------------------------------------------
# Human keyboard controls
# -----------------------------------------------------------------------------
def print_controls():
    print(__doc__)


def human_override_burst():
    ai.human_override_timer = 2.2
    ai.message = "human override burst"
    polymerase.target_speed = min(2.4, polymerase.target_speed + 0.35)
    expected = dna_units[polymerase.active_index].expected_rna()
    for nt in rna_pool:
        if nt.used:
            continue
        if random.random() < 0.35:
            nt.base = expected if random.random() < 0.65 else nt.base
            nt.obj.color = RNA_BASE_COLORS[nt.base]
            nt.glow.color = RNA_BASE_COLORS[nt.base]
            nt.label.text = nt.base
            nt.vel += safe_norm(polymerase.active_site.pos - nt.obj.pos) * random.uniform(0.25, 0.60)
    for _ in range(12):
        make_spark(polymerase.active_site.pos + vector(random.uniform(-0.3, 0.3), random.uniform(-0.1, 0.3), random.uniform(-0.3, 0.3)), vector(1.0, 0.62, 0.20), life=random.uniform(0.6, 1.2))


def keydown(evt):
    global paused
    k = evt.key.lower()
    if k == "a":
        ai.enabled = not ai.enabled
        ai.message = "manual AI toggle"
    elif k == "p":
        paused = not paused
    elif k == "r":
        reset_simulation(new_round=True)
    elif k == "m":
        ai.cycle_mode()
    elif k == "o":
        human_override_burst()
    elif k == "c":
        clear_sparks()
    elif k in ["+", "="]:
        ai.base_speed_bonus = clamp(ai.base_speed_bonus + 0.15, -0.5, 1.2)
    elif k in ["-", "_"]:
        ai.base_speed_bonus = clamp(ai.base_speed_bonus - 0.15, -0.5, 1.2)
    elif k == "h":
        print_controls()

scene.bind("keydown", keydown)

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
build_world()
print_controls()

while True:
    rate(60)
    dt = 1.0 / 60.0
    if not paused:
        scene_time += dt

    ai.update(dt)
    polymerase.update(dt, paused=paused)

    for unit in dna_units:
        unit.update(polymerase.index_float, BUBBLE_HALF_WIDTH, dt)

    update_backbone_curves()
    update_bubble_visual()

    # AI parameters also influence loose nucleotide motion.
    if ai.mode == "chaotic":
        attract_strength, chaos, orbit_bias = 1.25, 0.95, 0.35
    elif ai.mode == "playful":
        attract_strength, chaos, orbit_bias = 0.85, 0.25, 1.05
    elif ai.mode == "ritual":
        attract_strength, chaos, orbit_bias = 1.10, 0.10, 0.75
    elif ai.mode == "careful":
        attract_strength, chaos, orbit_bias = 1.45, 0.05, 0.50
    else:
        attract_strength, chaos, orbit_bias = 1.05, 0.13, 0.55

    for nt in rna_pool:
        nt.update_free(dt, polymerase.active_site.pos, attract_strength, chaos, orbit_bias)

    if not paused:
        try_attach_current_base(dt)

    # Complete mRNA when polymerase reaches the end or all bases are transcribed.
    if not mrna.complete and (polymerase.complete() or len(mrna.nucleotides) >= N_BASES):
        mrna.complete = True
        ai.set_mode("artist")
        for _ in range(24):
            make_spark(polymerase.obj.pos + vector(random.uniform(-0.9, 0.9), random.uniform(0.0, 0.8), random.uniform(-0.9, 0.9)), RNA_BACKBONE, life=random.uniform(1.0, 2.0))

    mrna.update(dt, polymerase.index_float)

    # Update sparks and remove dead ones.
    for sp in sparks[:]:
        if not sp.update(dt):
            sparks.remove(sp)

    update_progress_visual()
    update_status_labels()
