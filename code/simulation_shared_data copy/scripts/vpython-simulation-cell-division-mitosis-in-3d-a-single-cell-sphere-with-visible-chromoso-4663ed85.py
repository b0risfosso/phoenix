from vpython import *
import csv
import os
import time
import math
import random as pyrandom
from datetime import datetime

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

CSV_LOGGING_ACTIVE = True


def clamp(x, a, b):
    return max(a, min(b, x))


def smoothstep(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)


def lerp_vec(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1.0 - t) + b * t


def rand_vec_in_sphere(radius):
    while True:
        v = vector(pyrandom.uniform(-1, 1), pyrandom.uniform(-1, 1), pyrandom.uniform(-1, 1))
        if mag(v) <= 1 and mag(v) > 0.001:
            return v * radius


def safe_norm(v, fallback=vector(0, 1, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def stage_name(progress):
    if progress < 0.14:
        return "Interphase: loose chromatin drifts"
    if progress < 0.28:
        return "Prophase: chromosomes condense"
    if progress < 0.46:
        return "Metaphase: chromosomes align at equator"
    if progress < 0.68:
        return "Anaphase: spindle fibers pull chromatids apart"
    if progress < 0.84:
        return "Telophase: two nuclei reform"
    if progress < 0.995:
        return "Cytokinesis: membrane pinches inward"
    return "Complete: two daughter cells"


scene = canvas(
    title="AI-Controlled 3D Mitosis Simulation",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0)
)
scene.forward = vector(-0.75, -0.35, -0.85)
scene.range = 6.2
scene.userzoom = True
scene.userspin = True
scene.ambient = color.gray(0.78)
distant_light(direction=vector(-0.3, -0.6, -0.4), color=color.white)
distant_light(direction=vector(0.7, 0.4, 0.2), color=vector(0.55, 0.62, 0.75))

CELL_RADIUS = 3.0
POLE_X = 3.55
CHROMOSOME_COUNT = 8
BASE_CYCLE_SECONDS = 42.0
BASE_PHASE_SPEED = 1.0 / BASE_CYCLE_SECONDS

palette = [
    vector(0.85, 0.22, 0.28),
    vector(0.24, 0.42, 0.95),
    vector(0.95, 0.55, 0.18),
    vector(0.48, 0.26, 0.78),
    vector(0.12, 0.62, 0.52),
    vector(0.92, 0.35, 0.70),
    vector(0.36, 0.68, 0.20),
    vector(0.92, 0.78, 0.16),
]

title_label = label(
    pos=vector(0, 3.95, 0),
    text="Mitosis: AI-controlled chromosome organization and cell division",
    height=18,
    color=vector(0.12, 0.16, 0.22),
    box=False,
    opacity=0
)

stage_label = label(
    pos=vector(0, -3.95, 0),
    text="",
    height=15,
    color=vector(0.10, 0.18, 0.25),
    box=False,
    opacity=0
)

help_label = label(
    pos=vector(0, 4.35, 0),
    text="Keys: A AI | P pause | R reset | M mode | C chaos | T attach | D detach | X spill | N next | arrows/W/S nudge selected",
    height=10,
    color=vector(0.25, 0.30, 0.38),
    box=False,
    opacity=0
)

main_membrane = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS,
    color=vector(0.50, 0.78, 1.0),
    opacity=0.17,
    shininess=0.25
)

outer_glow = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS * 1.015,
    color=vector(0.72, 0.88, 1.0),
    opacity=0.055,
    shininess=0.1
)

nucleus = sphere(
    pos=vector(0, 0, 0),
    radius=1.68,
    color=vector(0.73, 0.62, 0.93),
    opacity=0.20,
    shininess=0.08
)

left_nucleus = sphere(
    pos=vector(-1.85, 0, 0),
    radius=0.2,
    color=vector(0.73, 0.62, 0.93),
    opacity=0.0,
    visible=False
)
right_nucleus = sphere(
    pos=vector(1.85, 0, 0),
    radius=0.2,
    color=vector(0.73, 0.62, 0.93),
    opacity=0.0,
    visible=False
)

left_daughter_membrane = sphere(
    pos=vector(-1.55, 0, 0),
    radius=0.1,
    color=vector(0.54, 0.82, 1.0),
    opacity=0.0,
    visible=False,
    shininess=0.25
)
right_daughter_membrane = sphere(
    pos=vector(1.55, 0, 0),
    radius=0.1,
    color=vector(0.54, 0.82, 1.0),
    opacity=0.0,
    visible=False,
    shininess=0.25
)

cleavage_band = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=CELL_RADIUS * 0.98,
    thickness=0.055,
    color=vector(0.18, 0.55, 0.95),
    opacity=0.0,
    visible=False
)

metaphase_plane = box(
    pos=vector(0, 0, 0),
    size=vector(0.018, 5.15, 5.15),
    color=vector(0.12, 0.75, 0.95),
    opacity=0.0,
    visible=False
)

left_pole = sphere(pos=vector(-0.25, 0, 0), radius=0.15, color=vector(1.0, 0.56, 0.10), emissive=True)
right_pole = sphere(pos=vector(0.25, 0, 0), radius=0.15, color=vector(1.0, 0.56, 0.10), emissive=True)

left_aster = []
right_aster = []
for k in range(12):
    angle = 2 * math.pi * k / 12
    direction = vector(0, math.cos(angle), math.sin(angle))
    left_aster.append(cylinder(pos=left_pole.pos, axis=direction * 0.46, radius=0.012, color=vector(1.0, 0.73, 0.22), opacity=0.55))
    right_aster.append(cylinder(pos=right_pole.pos, axis=direction * 0.46, radius=0.012, color=vector(1.0, 0.73, 0.22), opacity=0.55))

daughter_label_left = label(
    pos=vector(-2.25, -2.95, 0),
    text="Daughter Cell A",
    height=15,
    color=vector(0.07, 0.22, 0.34),
    box=False,
    opacity=0,
    visible=False
)
daughter_label_right = label(
    pos=vector(2.25, -2.95, 0),
    text="Daughter Cell B",
    height=15,
    color=vector(0.07, 0.22, 0.34),
    box=False,
    opacity=0,
    visible=False
)


class Chromosome:
    def __init__(self, index, chrom_color):
        self.index = index
        self.color = chrom_color
        self.initial_center = vector(0, 0, 0)
        self.target_yz = vector(0, 0, 0)
        self.manual_offset = vector(0, 0, 0)
        self.ai_offset = vector(0, 0, 0)
        self.left_attached = False
        self.right_attached = False
        self.left_detach_timer = 0.0
        self.right_detach_timer = 0.0
        self.last_center = vector(0, 0, 0)
        self.velocity = vector(0, 0, 0)
        self.left_pos = vector(0, 0, 0)
        self.right_pos = vector(0, 0, 0)
        self.last_left_pos = vector(0, 0, 0)
        self.last_right_pos = vector(0, 0, 0)

        self.left_rod = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0.5, 0), radius=0.055, color=self.color, opacity=0.85)
        self.right_rod = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0.5, 0), radius=0.055, color=self.color, opacity=0.85)
        self.centromere = sphere(pos=vector(0, 0, 0), radius=0.105, color=vector(0.98, 0.96, 0.55), opacity=0.95, emissive=True)
        self.left_fiber = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0, 0), radius=0.011, color=vector(0.35, 0.62, 0.95), opacity=0.15, visible=False)
        self.right_fiber = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0, 0), radius=0.011, color=vector(0.35, 0.62, 0.95), opacity=0.15, visible=False)
        self.marker = sphere(pos=vector(0, 0, 0), radius=0.34, color=vector(1.0, 0.95, 0.25), opacity=0.0, visible=False)
        self.trail_curve = curve(radius=0.013, color=self.color, visible=False)
        self.set_new_round()

    def set_new_round(self):
        self.initial_center = rand_vec_in_sphere(1.15)
        slot_angle = 2 * math.pi * self.index / CHROMOSOME_COUNT
        slot_radius = 1.55 if self.index % 2 == 0 else 0.85
        self.target_yz = vector(0, math.cos(slot_angle) * slot_radius, math.sin(slot_angle) * slot_radius)
        self.manual_offset = vector(0, 0, 0)
        self.ai_offset = vector(0, 0, 0)
        self.left_attached = False
        self.right_attached = False
        self.left_detach_timer = 0.0
        self.right_detach_timer = 0.0
        self.last_center = self.initial_center
        self.velocity = vector(0, 0, 0)
        self.marker.visible = False
        self.marker.opacity = 0.0
        self.trail_curve.visible = False
        self.trail_curve = curve(radius=0.013, color=self.color, visible=False)

    def attach_all(self):
        self.left_attached = True
        self.right_attached = True
        self.left_detach_timer = 0.0
        self.right_detach_timer = 0.0

    def detach_random_side(self, duration=1.0):
        if pyrandom.random() < 0.5:
            self.left_attached = False
            self.left_detach_timer = duration
        else:
            self.right_attached = False
            self.right_detach_timer = duration

    def add_jitter(self, amount):
        self.ai_offset += rand_vec_in_sphere(amount)

    def nudge(self, delta):
        self.manual_offset += delta

    def update(self, progress, sim_time, dt, alignment_boost, selected=False, artistic=False):
        self.left_detach_timer = max(0.0, self.left_detach_timer - dt)
        self.right_detach_timer = max(0.0, self.right_detach_timer - dt)

        if progress > 0.28 and self.left_detach_timer <= 0:
            self.left_attached = True
        if progress > 0.28 and self.right_detach_timer <= 0:
            self.right_attached = True

        wander = vector(
            math.sin(sim_time * 0.9 + self.index * 2.1),
            math.sin(sim_time * 0.7 + self.index * 1.3),
            math.cos(sim_time * 0.8 + self.index * 1.9)
        ) * 0.12

        condense = smoothstep(0.10, 0.28, progress) * (1.0 - 0.55 * smoothstep(0.72, 0.92, progress))
        metaphase = smoothstep(0.28, 0.46, progress)
        anaphase = smoothstep(0.46, 0.68, progress)
        telophase = smoothstep(0.68, 0.84, progress)

        center_pre = self.initial_center + wander * (1.0 - metaphase)
        target_center = self.target_yz
        align_t = clamp(metaphase * (1.0 + alignment_boost), 0.0, 1.0)
        center = lerp_vec(center_pre, target_center, align_t)

        left_goal = vector(-2.05, self.target_yz.y * 0.50, self.target_yz.z * 0.50)
        right_goal = vector(2.05, self.target_yz.y * 0.50, self.target_yz.z * 0.50)

        sister_sep = lerp(0.055, 0.16, condense)
        pre_left = center + vector(-sister_sep, 0, 0)
        pre_right = center + vector(sister_sep, 0, 0)

        left_pos = lerp_vec(pre_left, left_goal, anaphase)
        right_pos = lerp_vec(pre_right, right_goal, anaphase)

        if telophase > 0:
            left_pos = lerp_vec(left_pos, vector(-2.05, self.target_yz.y * 0.28, self.target_yz.z * 0.28), telophase)
            right_pos = lerp_vec(right_pos, vector(2.05, self.target_yz.y * 0.28, self.target_yz.z * 0.28), telophase)

        self.ai_offset *= max(0.0, 1.0 - dt * 1.8)
        self.manual_offset *= max(0.0, 1.0 - dt * 0.65)

        left_pos += self.ai_offset + self.manual_offset
        right_pos += self.ai_offset + self.manual_offset

        self.last_left_pos = self.left_pos
        self.last_right_pos = self.right_pos
        self.left_pos = left_pos
        self.right_pos = right_pos

        current_center = (left_pos + right_pos) * 0.5
        self.velocity = (current_center - self.last_center) / max(dt, 1e-6)
        self.last_center = current_center

        rod_len = lerp(0.35, 0.92, condense)
        rod_len *= lerp(1.0, 0.48, smoothstep(0.70, 0.93, progress))
        rod_rad = lerp(0.035, 0.072, condense)
        rod_opacity = lerp(0.35, 0.96, condense)
        rod_opacity *= lerp(1.0, 0.55, smoothstep(0.78, 0.98, progress))

        tilt_amount = 0.42 * (1.0 - 0.55 * anaphase)
        left_axis_dir = safe_norm(vector(0, 1, tilt_amount))
        right_axis_dir = safe_norm(vector(0, 1, -tilt_amount))

        if progress < 0.18:
            left_axis_dir = safe_norm(vector(math.sin(sim_time + self.index), 1, math.cos(sim_time * 0.6 + self.index)) * 0.35 + vector(0, 1, 0))
            right_axis_dir = safe_norm(vector(math.cos(sim_time * 0.8 + self.index), 1, -math.sin(sim_time + self.index)) * 0.35 + vector(0, 1, 0))

        self.left_rod.pos = left_pos - left_axis_dir * rod_len * 0.5
        self.left_rod.axis = left_axis_dir * rod_len
        self.left_rod.radius = rod_rad
        self.left_rod.opacity = rod_opacity
        self.left_rod.color = self.color

        self.right_rod.pos = right_pos - right_axis_dir * rod_len * 0.5
        self.right_rod.axis = right_axis_dir * rod_len
        self.right_rod.radius = rod_rad
        self.right_rod.opacity = rod_opacity
        self.right_rod.color = self.color

        self.centromere.pos = current_center
        self.centromere.radius = lerp(0.055, 0.115, condense)
        self.centromere.opacity = lerp(0.35, 0.98, condense)

        fiber_visible = progress > 0.24 and progress < 0.78
        self.left_fiber.visible = fiber_visible
        self.right_fiber.visible = fiber_visible

        if fiber_visible:
            self.left_fiber.pos = left_pole.pos
            self.left_fiber.axis = left_pos - left_pole.pos
            self.left_fiber.opacity = 0.62 if self.left_attached else 0.13
            self.left_fiber.color = vector(0.26, 0.56, 0.92) if self.left_attached else vector(0.72, 0.74, 0.78)
            self.right_fiber.pos = right_pole.pos
            self.right_fiber.axis = right_pos - right_pole.pos
            self.right_fiber.opacity = 0.62 if self.right_attached else 0.13
            self.right_fiber.color = vector(0.26, 0.56, 0.92) if self.right_attached else vector(0.72, 0.74, 0.78)

        self.marker.pos = current_center
        self.marker.visible = selected
        self.marker.opacity = 0.24 + 0.12 * math.sin(sim_time * 6.0) if selected else 0.0

        if artistic:
            self.trail_curve.visible = True
            if pyrandom.random() < 0.35:
                self.trail_curve.append(pos=current_center)
        else:
            self.trail_curve.visible = False

    def center(self):
        return (self.left_pos + self.right_pos) * 0.5

    def separation(self):
        return abs(self.right_pos.x - self.left_pos.x)


class Particle:
    def __init__(self, index):
        self.index = index
        self.body = sphere(
            pos=rand_vec_in_sphere(CELL_RADIUS * 0.65),
            radius=pyrandom.uniform(0.035, 0.07),
            color=vector(0.22 + pyrandom.random() * 0.35, 0.75 + pyrandom.random() * 0.20, 0.92 + pyrandom.random() * 0.08),
            opacity=0.58,
            shininess=0.1
        )
        self.vel = rand_vec_in_sphere(0.32)
        self.spill_timer = 0.0
        self.orbit_phase = pyrandom.random() * 2 * math.pi

    def reset(self):
        self.body.pos = rand_vec_in_sphere(CELL_RADIUS * 0.65)
        self.vel = rand_vec_in_sphere(0.32)
        self.body.opacity = 0.58
        self.body.color = vector(0.22 + pyrandom.random() * 0.35, 0.75 + pyrandom.random() * 0.20, 0.92 + pyrandom.random() * 0.08)
        self.spill_timer = 0.0

    def spill(self, strength=1.8):
        direction = safe_norm(self.body.pos, rand_vec_in_sphere(1))
        self.vel += direction * strength + rand_vec_in_sphere(0.35)
        self.spill_timer = 2.4
        self.body.color = vector(1.0, 0.58, 0.25)
        self.body.opacity = 0.78

    def update(self, dt, progress, ritual_orbit=False):
        self.spill_timer = max(0.0, self.spill_timer - dt)
        if ritual_orbit:
            axis_dir = vector(1, 0, 0)
            rel = self.body.pos
            swirl = cross(axis_dir, rel) * 0.11
            self.vel += swirl * dt

        self.body.pos += self.vel * dt
        self.vel *= max(0.0, 1.0 - dt * 0.22)

        if self.spill_timer <= 0.0:
            limit = CELL_RADIUS * 0.92
            if mag(self.body.pos) > limit:
                outward = safe_norm(self.body.pos)
                self.body.pos = outward * limit
                self.vel = self.vel - 2 * dot(self.vel, outward) * outward
                self.vel *= 0.72
                return 1
        else:
            if mag(self.body.pos) > CELL_RADIUS * 1.35:
                self.vel += -safe_norm(self.body.pos) * 0.9 * dt

        if progress > 0.90 and self.spill_timer <= 0.0:
            side = -1 if self.body.pos.x < 0 else 1
            target = vector(side * 1.95, self.body.pos.y * 0.7, self.body.pos.z * 0.7)
            self.vel += (target - self.body.pos) * dt * 0.22
        return 0


class MitosisSimulation:
    def __init__(self):
        self.phase_progress = 0.0
        self.sim_time = 0.0
        self.frame = 0
        self.paused = False
        self.selected_index = 0
        self.loop_count = 0
        self.reset_count = 0
        self.completion_timer = 0.0
        self.mark_count = 0
        self.particle_bounce_count = 0
        self.manual_phase_boost = 0.0
        self.alignment_boost = 0.0
        self.ai_jitter_amount = 0.0
        self.last_reset_reason = "initial"
        self.chromosomes = [Chromosome(i, palette[i % len(palette)]) for i in range(CHROMOSOME_COUNT)]
        self.particles = [Particle(i) for i in range(36)]
        self.left_daughter_pos = vector(-1.70, 0, 0)
        self.right_daughter_pos = vector(1.70, 0, 0)
        self.last_progress_for_stagnation = 0.0
        self.last_alignment_for_stagnation = 999.0
        self.stagnation_seconds = 0.0

    def reset(self, reason="reset"):
        self.phase_progress = 0.0
        self.completion_timer = 0.0
        self.loop_count += 1
        self.reset_count += 1
        self.last_reset_reason = reason
        self.selected_index = self.loop_count % CHROMOSOME_COUNT
        self.manual_phase_boost = 0.0
        self.alignment_boost = 0.0
        self.ai_jitter_amount = 0.0
        for c in self.chromosomes:
            c.set_new_round()
        for p in self.particles:
            p.reset()
        daughter_label_left.visible = False
        daughter_label_right.visible = False
        self.particle_bounce_count = 0

    def attach_all_spindles(self):
        for c in self.chromosomes:
            c.attach_all()

    def detach_random_spindle(self, duration=1.2):
        c = pyrandom.choice(self.chromosomes)
        c.detach_random_side(duration)

    def mark_chromosome(self, index=None):
        if index is None:
            self.selected_index = (self.selected_index + 1) % len(self.chromosomes)
        else:
            self.selected_index = index % len(self.chromosomes)
        self.mark_count += 1

    def spill_particles(self, count=8, strength=1.6):
        for p in pyrandom.sample(self.particles, min(count, len(self.particles))):
            p.spill(strength)

    def add_chromosome_jitter(self, amount=0.12):
        for c in self.chromosomes:
            if pyrandom.random() < 0.55:
                c.add_jitter(amount)

    def nudge_selected(self, delta):
        self.chromosomes[self.selected_index].nudge(delta)

    def current_alignment_error(self):
        if not self.chromosomes:
            return 0.0
        total = 0.0
        for c in self.chromosomes:
            cen = c.center()
            total += abs(cen.x) + 0.35 * mag(vector(0, cen.y, cen.z) - c.target_yz)
        return total / len(self.chromosomes)

    def average_separation(self):
        if not self.chromosomes:
            return 0.0
        return sum(c.separation() for c in self.chromosomes) / len(self.chromosomes)

    def attached_count(self):
        return sum((1 if c.left_attached else 0) + (1 if c.right_attached else 0) for c in self.chromosomes)

    def update_static_objects(self, dt, ai_membrane_pulse=0.0):
        p = self.phase_progress

        pole_move = smoothstep(0.08, 0.28, p)
        left_pole.pos = lerp_vec(vector(-0.25, 0, 0), vector(-POLE_X, 0, 0), pole_move)
        right_pole.pos = lerp_vec(vector(0.25, 0, 0), vector(POLE_X, 0, 0), pole_move)

        for k, ray in enumerate(left_aster):
            angle = 2 * math.pi * k / len(left_aster) + self.sim_time * 0.25
            direction = safe_norm(vector(0.12, math.cos(angle), math.sin(angle)))
            ray.pos = left_pole.pos
            ray.axis = direction * lerp(0.18, 0.58, pole_move)
            ray.opacity = 0.28 + 0.35 * pole_move

        for k, ray in enumerate(right_aster):
            angle = 2 * math.pi * k / len(right_aster) - self.sim_time * 0.25
            direction = safe_norm(vector(-0.12, math.cos(angle), math.sin(angle)))
            ray.pos = right_pole.pos
            ray.axis = direction * lerp(0.18, 0.58, pole_move)
            ray.opacity = 0.28 + 0.35 * pole_move

        nucleus.opacity = 0.20 * (1.0 - smoothstep(0.18, 0.34, p)) + 0.02 * smoothstep(0.80, 0.95, p)
        nucleus.visible = nucleus.opacity > 0.015

        reform = smoothstep(0.66, 0.84, p)
        left_nucleus.visible = reform > 0.02
        right_nucleus.visible = reform > 0.02
        left_nucleus.pos = vector(-2.05, 0, 0)
        right_nucleus.pos = vector(2.05, 0, 0)
        left_nucleus.radius = lerp(0.15, 0.95, reform)
        right_nucleus.radius = lerp(0.15, 0.95, reform)
        left_nucleus.opacity = 0.22 * reform
        right_nucleus.opacity = 0.22 * reform

        align_alpha = smoothstep(0.29, 0.39, p) * (1.0 - smoothstep(0.48, 0.56, p))
        metaphase_plane.visible = align_alpha > 0.01
        metaphase_plane.opacity = 0.12 * align_alpha

        pinch = smoothstep(0.76, 0.995, p)
        cleavage_band.visible = p > 0.72
        cleavage_band.opacity = 0.04 + 0.40 * pinch if p > 0.72 else 0.0
        cleavage_band.radius = max(0.18, CELL_RADIUS * (1.0 - 0.88 * pinch))
        cleavage_band.thickness = 0.045 + 0.035 * pinch
        cleavage_band.color = vector(0.16, 0.48 + 0.18 * math.sin(self.sim_time * 4.0), 0.95)

        daughter_alpha = smoothstep(0.72, 0.98, p)
        sep = lerp(0.0, 1.78, daughter_alpha)
        daughter_radius = lerp(0.2, 2.12, daughter_alpha)

        left_daughter_membrane.visible = daughter_alpha > 0.02
        right_daughter_membrane.visible = daughter_alpha > 0.02
        left_daughter_membrane.pos = vector(-sep, 0, 0)
        right_daughter_membrane.pos = vector(sep, 0, 0)
        left_daughter_membrane.radius = daughter_radius
        right_daughter_membrane.radius = daughter_radius
        left_daughter_membrane.opacity = 0.17 * daughter_alpha
        right_daughter_membrane.opacity = 0.17 * daughter_alpha

        main_membrane.opacity = max(0.02, 0.17 * (1.0 - 0.78 * daughter_alpha)) + ai_membrane_pulse
        main_membrane.color = vector(0.50 + ai_membrane_pulse * 2.2, 0.78, 1.0)
        outer_glow.opacity = max(0.015, 0.055 * (1.0 - 0.45 * daughter_alpha)) + ai_membrane_pulse * 0.5

        daughter_label_left.visible = p > 0.94
        daughter_label_right.visible = p > 0.94
        daughter_label_left.pos = vector(-2.05, -2.92, 0)
        daughter_label_right.pos = vector(2.05, -2.92, 0)

    def update(self, dt, ai_controller):
        if self.paused:
            return

        self.frame += 1
        self.sim_time += dt

        speed_multiplier = ai_controller.speed_multiplier if ai_controller.enabled else 1.0
        self.phase_progress += dt * BASE_PHASE_SPEED * speed_multiplier
        self.phase_progress += self.manual_phase_boost
        self.manual_phase_boost *= 0.0
        self.phase_progress = clamp(self.phase_progress, 0.0, 1.0)

        if self.phase_progress >= 0.995:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

        self.alignment_boost *= max(0.0, 1.0 - dt * 1.4)
        self.ai_jitter_amount *= max(0.0, 1.0 - dt * 2.2)

        artistic = ai_controller.enabled and ai_controller.mode == "artistic"
        for i, c in enumerate(self.chromosomes):
            if self.ai_jitter_amount > 0 and pyrandom.random() < 0.09:
                c.add_jitter(self.ai_jitter_amount)
            c.update(
                self.phase_progress,
                self.sim_time,
                dt,
                self.alignment_boost,
                selected=(i == self.selected_index),
                artistic=artistic
            )

        ritual_orbit = ai_controller.enabled and ai_controller.mode in ("ritual", "orbit")
        for particle in self.particles:
            self.particle_bounce_count += particle.update(dt, self.phase_progress, ritual_orbit)

        ai_pulse = ai_controller.membrane_pulse if ai_controller.enabled else 0.0
        self.update_static_objects(dt, ai_pulse)

        if self.phase_progress >= 1.0 and self.completion_timer > 7.0:
            self.reset("automatic loop after completion")

        align_now = self.current_alignment_error()
        progress_change = abs(self.phase_progress - self.last_progress_for_stagnation)
        align_change = abs(align_now - self.last_alignment_for_stagnation)
        if progress_change < 0.0002 and align_change < 0.002 and not self.paused:
            self.stagnation_seconds += dt
        else:
            self.stagnation_seconds = max(0.0, self.stagnation_seconds - dt * 0.4)
        self.last_progress_for_stagnation = self.phase_progress
        self.last_alignment_for_stagnation = align_now

        stage_label.text = (
            f"{stage_name(self.phase_progress)}\n"
            f"AI: {'ON' if ai_controller.enabled else 'OFF'} | Mode: {ai_controller.mode} | "
            f"Loop: {self.loop_count} | Attached spindle ends: {self.attached_count()}/{CHROMOSOME_COUNT * 2}"
        )


class AIController:
    def __init__(self, simulation):
        self.sim = simulation
        self.enabled = True
        self.behavior_modes = [
            "careful",
            "constructive",
            "ritual",
            "curious",
            "chaotic",
            "destructive",
            "artistic",
            "orbit"
        ]
        self.mode = "constructive"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.next_switch = 7.0
        self.speed_multiplier = 1.0
        self.membrane_pulse = 0.0
        self.action_cooldown = 0.0
        self.override_until_time = 0.0
        self.stagnation_memory = 0.0
        self.completion_seen = False
        self.last_mode_switch_frame = 0

    def toggle(self):
        self.enabled = not self.enabled

    def set_mode(self, mode_name):
        if mode_name in self.behavior_modes:
            self.previous_mode = self.mode
            self.mode = mode_name
            self.mode_timer = 0.0
            self.next_switch = pyrandom.uniform(6.0, 12.0)

    def cycle_mode(self):
        idx = self.behavior_modes.index(self.mode)
        self.set_mode(self.behavior_modes[(idx + 1) % len(self.behavior_modes)])

    def human_override(self, seconds=8.0):
        self.override_until_time = self.sim.sim_time + seconds

    def read_state(self):
        return {
            "progress": self.sim.phase_progress,
            "stage": stage_name(self.sim.phase_progress),
            "alignment_error": self.sim.current_alignment_error(),
            "separation": self.sim.average_separation(),
            "attached_count": self.sim.attached_count(),
            "completion_timer": self.sim.completion_timer,
            "stagnation_seconds": self.sim.stagnation_seconds,
            "selected_index": self.sim.selected_index,
            "loop_count": self.sim.loop_count,
            "particle_bounces": self.sim.particle_bounce_count
        }

    def choose_mode(self, state):
        p = state["progress"]
        candidates = []

        if state["stagnation_seconds"] > 5.5:
            candidates = ["chaotic", "destructive", "constructive"]
        elif p >= 0.995:
            candidates = ["ritual", "artistic", "orbit"]
        elif p < 0.20:
            candidates = ["curious", "ritual", "constructive"]
        elif p < 0.46 and state["alignment_error"] > 0.45:
            candidates = ["constructive", "careful", "curious"]
        elif p < 0.68:
            candidates = ["careful", "chaotic", "artistic", "orbit"]
        elif p < 0.90:
            candidates = ["ritual", "artistic", "constructive"]
        else:
            candidates = ["ritual", "orbit", "curious"]

        if self.mode in candidates and pyrandom.random() < 0.35:
            candidates = [m for m in candidates if m != self.mode] or candidates

        new_mode = pyrandom.choice(candidates)
        if new_mode == self.previous_mode and len(candidates) > 1:
            alternatives = [m for m in candidates if m != self.previous_mode]
            new_mode = pyrandom.choice(alternatives)
        self.set_mode(new_mode)

    def update(self, dt):
        self.membrane_pulse = 0.0
        if not self.enabled:
            self.speed_multiplier = 1.0
            return

        state = self.read_state()
        self.mode_timer += dt
        self.action_cooldown = max(0.0, self.action_cooldown - dt)

        if state["completion_timer"] > 5.0:
            self.sim.reset("AI loop after complete daughter cells")
            self.set_mode("constructive")
            return

        if state["stagnation_seconds"] > 8.0:
            self.sim.reset("AI reset after stagnation")
            self.set_mode("curious")
            return

        if self.mode_timer > self.next_switch:
            self.choose_mode(state)

        if self.sim.sim_time < self.override_until_time:
            self.speed_multiplier = 1.0
            self.membrane_pulse = 0.01 * (0.5 + 0.5 * math.sin(self.sim.sim_time * 8.0))
            return

        self.apply_behavior(state, dt)

    def apply_behavior(self, state, dt):
        p = state["progress"]
        self.speed_multiplier = 1.0

        if self.mode == "careful":
            self.speed_multiplier = 0.68 if 0.26 < p < 0.72 else 0.82
            self.sim.alignment_boost += 0.25 * dt
            if p > 0.25:
                self.sim.attach_all_spindles()
            if self.action_cooldown <= 0:
                self.sim.mark_chromosome((self.sim.selected_index + 1) % CHROMOSOME_COUNT)
                self.action_cooldown = 2.4
            self.membrane_pulse = 0.006 * (0.5 + 0.5 * math.sin(self.sim.sim_time * 3.0))

        elif self.mode == "constructive":
            self.speed_multiplier = 1.12
            self.sim.alignment_boost += 0.75 * dt
            if p > 0.22:
                self.sim.attach_all_spindles()
            if state["alignment_error"] > 0.35 and self.action_cooldown <= 0:
                target = max(range(len(self.sim.chromosomes)), key=lambda i: abs(self.sim.chromosomes[i].center().x))
                self.sim.mark_chromosome(target)
                self.sim.chromosomes[target].add_jitter(0.035)
                self.action_cooldown = 1.5

        elif self.mode == "ritual":
            self.speed_multiplier = 0.74
            self.membrane_pulse = 0.018 * (0.5 + 0.5 * math.sin(self.sim.sim_time * 5.5))
            if self.action_cooldown <= 0:
                self.sim.mark_chromosome()
                self.action_cooldown = 1.15
            self.orbit_camera(dt, speed=0.20)
            for c in self.sim.chromosomes:
                c.ai_offset += safe_norm(c.center() + vector(0.001, 0, 0)) * 0.002 * math.sin(self.sim.sim_time * 4.0 + c.index)

        elif self.mode == "curious":
            self.speed_multiplier = 0.88
            if self.action_cooldown <= 0:
                self.sim.mark_chromosome()
                self.action_cooldown = 1.8
            selected = self.sim.chromosomes[self.sim.selected_index]
            scene.center = lerp_vec(scene.center, selected.center() * 0.22, 0.025)
            selected.marker.color = vector(1.0, 0.92, 0.18)
            selected.add_jitter(0.012)

        elif self.mode == "chaotic":
            self.speed_multiplier = 1.34
            self.sim.ai_jitter_amount = max(self.sim.ai_jitter_amount, 0.070)
            self.membrane_pulse = 0.012 * pyrandom.random()
            if self.action_cooldown <= 0:
                self.sim.detach_random_spindle(duration=pyrandom.uniform(0.45, 1.15))
                if pyrandom.random() < 0.38:
                    self.sim.spill_particles(count=4, strength=1.25)
                self.action_cooldown = pyrandom.uniform(0.35, 0.85)
            self.orbit_camera(dt, speed=-0.12)

        elif self.mode == "destructive":
            self.speed_multiplier = 0.96
            self.sim.ai_jitter_amount = max(self.sim.ai_jitter_amount, 0.105)
            if self.action_cooldown <= 0:
                for _ in range(2):
                    self.sim.detach_random_spindle(duration=pyrandom.uniform(0.8, 1.7))
                self.sim.spill_particles(count=7, strength=2.0)
                self.action_cooldown = 2.2
            self.membrane_pulse = 0.020 * (0.5 + 0.5 * math.sin(self.sim.sim_time * 9.0))

        elif self.mode == "artistic":
            self.speed_multiplier = 0.98
            self.membrane_pulse = 0.010 * (0.5 + 0.5 * math.sin(self.sim.sim_time * 2.0))
            if self.action_cooldown <= 0:
                self.sim.mark_chromosome()
                self.sim.spill_particles(count=3, strength=0.95)
                self.action_cooldown = 2.8
            self.orbit_camera(dt, speed=0.10)

        elif self.mode == "orbit":
            self.speed_multiplier = 1.02
            self.orbit_camera(dt, speed=0.34)
            if self.action_cooldown <= 0:
                self.sim.mark_chromosome()
                self.action_cooldown = 2.0
            self.membrane_pulse = 0.006

    def orbit_camera(self, dt, speed=0.18):
        angle = speed * dt
        f = scene.forward
        ca = math.cos(angle)
        sa = math.sin(angle)
        new_forward = vector(f.x * ca - f.z * sa, f.y, f.x * sa + f.z * ca)
        scene.forward = safe_norm(new_forward, vector(-0.75, -0.35, -0.85))


simulation = MitosisSimulation()
ai_controller = AIController(simulation)


def on_keydown(evt):
    key = evt.key.lower()
    if key == "a":
        ai_controller.toggle()
    elif key == "p":
        simulation.paused = not simulation.paused
    elif key == "r":
        simulation.reset("human reset")
        ai_controller.human_override(2.0)
    elif key == "m":
        ai_controller.cycle_mode()
    elif key == "c":
        simulation.add_chromosome_jitter(0.18)
        simulation.spill_particles(count=10, strength=2.0)
        ai_controller.set_mode("chaotic")
    elif key == "t":
        simulation.attach_all_spindles()
        ai_controller.human_override()
    elif key == "d":
        simulation.detach_random_spindle(duration=2.0)
        ai_controller.human_override()
    elif key == "x":
        simulation.spill_particles(count=12, strength=2.2)
        ai_controller.human_override()
    elif key == "n":
        simulation.manual_phase_boost = 0.08
        ai_controller.human_override(3.0)
    elif key in ("left", "right", "up", "down", "w", "s"):
        step = 0.18
        if key == "left":
            simulation.nudge_selected(vector(0, -step, 0))
        elif key == "right":
            simulation.nudge_selected(vector(0, step, 0))
        elif key == "up":
            simulation.nudge_selected(vector(0, 0, -step))
        elif key == "down":
            simulation.nudge_selected(vector(0, 0, step))
        elif key == "w":
            simulation.nudge_selected(vector(-step, 0, 0))
        elif key == "s":
            simulation.nudge_selected(vector(step, 0, 0))
        ai_controller.human_override()
    elif key.isdigit():
        idx = int(key)
        if 0 <= idx < len(ai_controller.behavior_modes):
            ai_controller.set_mode(ai_controller.behavior_modes[idx])
            ai_controller.enabled = True


scene.bind("keydown", on_keydown)

_csv_file = None
_csv_writer = None

try:
    parent_dir = os.path.dirname(os.path.abspath(CSV_OUTPUT_PATH))
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    _csv_file = open(CSV_OUTPUT_PATH, "w", newline="")
    _csv_writer = csv.writer(_csv_file)
    _csv_writer.writerow([
        "run_id",
        "frame",
        "elapsed_seconds",
        "sim_time",
        "phase_progress",
        "stage",
        "ai_enabled",
        "ai_mode",
        "paused",
        "loop_count",
        "reset_count",
        "last_reset_reason",
        "selected_chromosome",
        "selected_x",
        "selected_y",
        "selected_z",
        "selected_vx",
        "selected_vy",
        "selected_vz",
        "left_pole_x",
        "left_pole_y",
        "left_pole_z",
        "right_pole_x",
        "right_pole_y",
        "right_pole_z",
        "left_daughter_membrane_x",
        "right_daughter_membrane_x",
        "cleavage_band_radius",
        "alignment_error",
        "average_chromatid_separation",
        "attached_spindle_ends",
        "particle_bounce_count",
        "mark_count",
        "stagnation_seconds",
        "completion_timer",
        "membrane_opacity",
        "nucleus_opacity"
    ])
    _csv_file.flush()

    last_time = time.time()
    start_time = last_time
    csv_snapshot_interval_frames = 6
    csv_flush_interval_frames = 60

    while True:
        rate(60)
        now = time.time()
        dt = clamp(now - last_time, 0.001, 0.05)
        last_time = now
        elapsed = now - start_time

        ai_controller.update(dt)
        simulation.update(dt, ai_controller)

        if simulation.frame % csv_snapshot_interval_frames == 0:
            selected = simulation.chromosomes[simulation.selected_index]
            selected_center = selected.center()
            _csv_writer.writerow([
                _csv_run_id,
                simulation.frame,
                f"{elapsed:.4f}",
                f"{simulation.sim_time:.4f}",
                f"{simulation.phase_progress:.5f}",
                stage_name(simulation.phase_progress),
                int(ai_controller.enabled),
                ai_controller.mode,
                int(simulation.paused),
                simulation.loop_count,
                simulation.reset_count,
                simulation.last_reset_reason,
                simulation.selected_index,
                f"{selected_center.x:.5f}",
                f"{selected_center.y:.5f}",
                f"{selected_center.z:.5f}",
                f"{selected.velocity.x:.5f}",
                f"{selected.velocity.y:.5f}",
                f"{selected.velocity.z:.5f}",
                f"{left_pole.pos.x:.5f}",
                f"{left_pole.pos.y:.5f}",
                f"{left_pole.pos.z:.5f}",
                f"{right_pole.pos.x:.5f}",
                f"{right_pole.pos.y:.5f}",
                f"{right_pole.pos.z:.5f}",
                f"{left_daughter_membrane.pos.x:.5f}",
                f"{right_daughter_membrane.pos.x:.5f}",
                f"{cleavage_band.radius:.5f}",
                f"{simulation.current_alignment_error():.5f}",
                f"{simulation.average_separation():.5f}",
                simulation.attached_count(),
                simulation.particle_bounce_count,
                simulation.mark_count,
                f"{simulation.stagnation_seconds:.5f}",
                f"{simulation.completion_timer:.5f}",
                f"{main_membrane.opacity:.5f}",
                f"{nucleus.opacity:.5f}"
            ])

        if simulation.frame % csv_flush_interval_frames == 0:
            _csv_file.flush()

        if CSV_LOGGING_ACTIVE and elapsed >= CSV_RUN_SECONDS:
            stage_label.text = (
                f"CSV recording complete — saved run data\n"
                f"{CSV_OUTPUT_PATH}\n"
                f"Final AI mode: {ai_controller.mode} | Loops: {simulation.loop_count}"
            )
            _csv_file.flush()
            break

finally:
    if _csv_file is not None:
        _csv_file.flush()
        _csv_file.close()
