"""
DNA Double Helix Replication — VPython 3D Simulation with Expressive AI Controller

Run:
    pip install vpython
    python dna_double_helix_replication_ai_simulation.py

Controls:
    H       print controls
    A       toggle AI on/off
    P       pause/resume simulation
    R       reset current round
    O       human override burst: add extra nucleotides near replication forks
    1       AI mode: careful
    2       AI mode: curious
    3       AI mode: chaotic
    4       AI mode: ritual
    5       AI mode: artistic
    6       AI mode: repair
    Left/Right arrows   move forks manually
    Up arrow            increase replication speed
    Down arrow          decrease replication speed
    Space               spawn a cloud of free nucleotides

What this simulation shows:
    - A stylized DNA double helix made of paired bases.
    - Helicase enzymes unzip the original strands.
    - Polymerase enzymes build matching daughter strands.
    - Free nucleotides drift, orbit, collide, attach, detach, spill, wrap, and mark.
    - Two replication forks move outward from an origin.
    - A rule-based AI controller reads simulation state and changes behavior modes.
    - The AI can alter speed, spawn nucleotides, organize free bases, repair gaps,
      reset stalled rounds, and start a new loop when replication completes.

Notes:
    This is an educational/stylized simulation, not a chemically exact molecular dynamics model.
"""

from vpython import *
from math import sin, cos, pi, sqrt
from random import random, uniform, choice, randint

# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="DNA Double Helix Replication — AI Controlled VPython Simulation",
    width=1240,
    height=760,
    background=vector(0.96, 0.985, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.35, -0.2, -1)
scene.range = 12

# Light style, no dark background.
distant_light(direction=vector(0.5, 1, 0.7), color=vector(0.85, 0.88, 0.95))
local_light(pos=vector(0, 8, 8), color=vector(0.75, 0.80, 0.90))

# -----------------------------
# Constants and visual settings
# -----------------------------

BASE_COLORS = {
    "A": vector(0.20, 0.55, 1.00),  # blue
    "T": vector(1.00, 0.38, 0.34),  # red/coral
    "C": vector(0.18, 0.75, 0.42),  # green
    "G": vector(0.96, 0.74, 0.18),  # gold
}

PAIR_MATCH = {"A": "T", "T": "A", "C": "G", "G": "C"}
PAIR_LABEL = {"A": "Adenine", "T": "Thymine", "C": "Cytosine", "G": "Guanine"}

HELIX_LENGTH = 36
HELIX_SPACING = 0.42
HELIX_RADIUS = 2.05
HELIX_TWIST = 0.58
BASE_RADIUS = 0.18
BACKBONE_RADIUS = 0.075
ATTACH_DISTANCE = 0.38

BASE_SEQUENCE = "ATGCCGTAATCGGCTTACGATCGTACGGCATTAACG"
BASE_SEQUENCE = BASE_SEQUENCE[:HELIX_LENGTH]

WORLD_X_LIMIT = HELIX_LENGTH * HELIX_SPACING * 0.55 + 2.8
WORLD_Y_LIMIT = 6.2
WORLD_Z_LIMIT = 5.3

LEFT = -1
RIGHT = 1

# -----------------------------
# Global state variables
# -----------------------------

paused = False
ai_enabled = True
human_override_timer = 0.0
round_number = 1
sim_time = 0.0

all_objects = []
template_pairs = []
free_nucleotides = []
attached_nucleotides = []
event_marks = []
floating_particles = []

left_fork_index = HELIX_LENGTH // 2 - 1
right_fork_index = HELIX_LENGTH // 2
fork_speed = 1.05
fork_progress = 0.0

status_label = None
control_label = None
mode_label = None
progress_bar = None
progress_fill = None
origin_marker = None
left_helicase = None
right_helicase = None
left_polymerase_top = None
left_polymerase_bottom = None
right_polymerase_top = None
right_polymerase_bottom = None

# -----------------------------
# Utility functions
# -----------------------------

def clamp(value, low, high):
    return max(low, min(high, value))


def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(0, 0, 0)
    return v / m


def rand_vec(scale=1.0):
    return vector(uniform(-scale, scale), uniform(-scale, scale), uniform(-scale, scale))


def x_for_index(i):
    return (i - (HELIX_LENGTH - 1) / 2.0) * HELIX_SPACING


def helix_angle(i):
    return i * HELIX_TWIST


def template_positions(i):
    x = x_for_index(i)
    theta = helix_angle(i)
    p1 = vector(x, HELIX_RADIUS * cos(theta), HELIX_RADIUS * sin(theta))
    p2 = vector(x, -HELIX_RADIUS * cos(theta), -HELIX_RADIUS * sin(theta))
    return p1, p2


def daughter_position(template_pos, side_factor):
    """
    Position a newly built complementary base slightly outside the template strand.
    The side factor separates upper/lower geometry and creates a readable Y-fork.
    """
    radial = safe_norm(vector(0, template_pos.y, template_pos.z))
    outward = radial * 0.72
    fan = vector(0, side_factor * 0.55, 0)
    return template_pos + outward + fan


def register(obj):
    all_objects.append(obj)
    return obj


def delete_all_visuals():
    global all_objects
    for obj in all_objects:
        try:
            obj.visible = False
        except Exception:
            pass
    all_objects = []


def make_text(pos, text, height=0.18, color_value=vector(0.12, 0.18, 0.28), box=False, opacity=0.0):
    return register(label(
        pos=pos,
        text=text,
        height=height,
        color=color_value,
        box=box,
        opacity=opacity,
        border=8,
        font="sans"
    ))


def draw_connection(pos_a, pos_b, color_value, radius=0.035, opacity=0.55):
    mid = (pos_a + pos_b) * 0.5
    axis = pos_b - pos_a
    if mag(axis) < 1e-6:
        axis = vector(0.01, 0, 0)
    return register(cylinder(pos=mid - axis * 0.5, axis=axis, radius=radius, color=color_value, opacity=opacity))


def wrap_position(pos):
    if pos.x > WORLD_X_LIMIT:
        pos.x = -WORLD_X_LIMIT
    elif pos.x < -WORLD_X_LIMIT:
        pos.x = WORLD_X_LIMIT
    if pos.y > WORLD_Y_LIMIT:
        pos.y = -WORLD_Y_LIMIT
    elif pos.y < -WORLD_Y_LIMIT:
        pos.y = WORLD_Y_LIMIT
    if pos.z > WORLD_Z_LIMIT:
        pos.z = -WORLD_Z_LIMIT
    elif pos.z < -WORLD_Z_LIMIT:
        pos.z = WORLD_Z_LIMIT
    return pos


# -----------------------------
# Biological scene objects
# -----------------------------

class BasePair:
    def __init__(self, index, base_top):
        self.index = index
        self.base_top = base_top
        self.base_bottom = PAIR_MATCH[base_top]
        self.top_pos_closed, self.bottom_pos_closed = template_positions(index)

        self.top_pos = vector(self.top_pos_closed)
        self.bottom_pos = vector(self.bottom_pos_closed)

        self.unzipped = False
        self.copied_top = False
        self.copied_bottom = False
        self.copy_top_obj = None
        self.copy_bottom_obj = None
        self.copy_top_link = None
        self.copy_bottom_link = None

        self.top_sphere = register(sphere(
            pos=self.top_pos,
            radius=BASE_RADIUS,
            color=BASE_COLORS[self.base_top],
            opacity=0.95,
            shininess=0.7
        ))
        self.bottom_sphere = register(sphere(
            pos=self.bottom_pos,
            radius=BASE_RADIUS,
            color=BASE_COLORS[self.base_bottom],
            opacity=0.95,
            shininess=0.7
        ))

        self.hbond = draw_connection(self.top_pos, self.bottom_pos, vector(0.65, 0.67, 0.72), 0.023, 0.48)

        self.top_label = make_text(self.top_pos + vector(0, 0.26, 0), self.base_top, 0.11, vector(0.05, 0.06, 0.09))
        self.bottom_label = make_text(self.bottom_pos - vector(0, 0.26, 0), self.base_bottom, 0.11, vector(0.05, 0.06, 0.09))

        self.top_backbone = None
        self.bottom_backbone = None
        self.copy_top_backbone = None
        self.copy_bottom_backbone = None

    def set_backbone_links(self, next_pair):
        self.top_backbone = draw_connection(self.top_pos, next_pair.top_pos, vector(0.78, 0.58, 0.92), BACKBONE_RADIUS, 0.65)
        self.bottom_backbone = draw_connection(self.bottom_pos, next_pair.bottom_pos, vector(0.40, 0.76, 0.90), BACKBONE_RADIUS, 0.65)

    def unzip(self, fork_direction):
        if self.unzipped:
            return
        self.unzipped = True
        self.hbond.visible = False

        # Fork direction bends the two original template strands outward.
        fan = 1.05
        spread_z = 0.32 * fork_direction
        self.top_pos = self.top_pos_closed + vector(0, fan, spread_z)
        self.bottom_pos = self.bottom_pos_closed + vector(0, -fan, -spread_z)

        self.top_sphere.pos = self.top_pos
        self.bottom_sphere.pos = self.bottom_pos
        self.top_label.pos = self.top_pos + vector(0, 0.26, 0)
        self.bottom_label.pos = self.bottom_pos - vector(0, 0.26, 0)

        if self.top_backbone:
            self.top_backbone.color = vector(0.84, 0.63, 0.96)
            self.top_backbone.opacity = 0.72
        if self.bottom_backbone:
            self.bottom_backbone.color = vector(0.48, 0.80, 0.95)
            self.bottom_backbone.opacity = 0.72

        make_mark(self.top_pos, vector(1.0, 0.78, 0.25), "unzip")
        make_mark(self.bottom_pos, vector(1.0, 0.78, 0.25), "unzip")

    def rebuild_closed_position(self):
        if not self.unzipped:
            self.top_pos = vector(self.top_pos_closed)
            self.bottom_pos = vector(self.bottom_pos_closed)
            self.top_sphere.pos = self.top_pos
            self.bottom_sphere.pos = self.bottom_pos
            self.top_label.pos = self.top_pos + vector(0, 0.26, 0)
            self.bottom_label.pos = self.bottom_pos - vector(0, 0.26, 0)

    def attach_copy(self, strand_name, nucleotide):
        if strand_name == "top":
            if self.copied_top:
                return False
            self.copied_top = True
            self.copy_top_obj = nucleotide
            attach_pos = daughter_position(self.top_pos, 1)
            nucleotide.attach_to(attach_pos, PAIR_MATCH[self.base_top], self)
            self.copy_top_link = draw_connection(self.top_pos, attach_pos, vector(0.40, 0.62, 0.95), 0.03, 0.68)
            make_mark(attach_pos, vector(0.25, 0.65, 1.0), "attach")
            return True

        if strand_name == "bottom":
            if self.copied_bottom:
                return False
            self.copied_bottom = True
            self.copy_bottom_obj = nucleotide
            attach_pos = daughter_position(self.bottom_pos, -1)
            nucleotide.attach_to(attach_pos, PAIR_MATCH[self.base_bottom], self)
            self.copy_bottom_link = draw_connection(self.bottom_pos, attach_pos, vector(0.34, 0.82, 0.48), 0.03, 0.68)
            make_mark(attach_pos, vector(0.26, 0.78, 0.36), "attach")
            return True

        return False

    def detach_copy(self, strand_name):
        if strand_name == "top" and self.copied_top and self.copy_top_obj:
            self.copy_top_obj.detach()
            self.copy_top_obj = None
            self.copied_top = False
            if self.copy_top_link:
                self.copy_top_link.visible = False
                self.copy_top_link = None
            return True

        if strand_name == "bottom" and self.copied_bottom and self.copy_bottom_obj:
            self.copy_bottom_obj.detach()
            self.copy_bottom_obj = None
            self.copied_bottom = False
            if self.copy_bottom_link:
                self.copy_bottom_link.visible = False
                self.copy_bottom_link = None
            return True

        return False

    def update(self, dt):
        # Gently wiggle unzipped strands and copied bases.
        if self.unzipped:
            phase = sim_time * 2.0 + self.index * 0.2
            top_offset = vector(0, 0.04 * sin(phase), 0.035 * cos(phase))
            bottom_offset = vector(0, -0.04 * sin(phase + 0.8), -0.035 * cos(phase))
            self.top_sphere.pos = self.top_pos + top_offset
            self.bottom_sphere.pos = self.bottom_pos + bottom_offset
            self.top_label.pos = self.top_sphere.pos + vector(0, 0.26, 0)
            self.bottom_label.pos = self.bottom_sphere.pos - vector(0, 0.26, 0)
        else:
            self.rebuild_closed_position()

        if self.copy_top_obj:
            self.copy_top_obj.obj.pos = self.copy_top_obj.target_pos + vector(0, 0.02 * sin(sim_time * 3 + self.index), 0)
            self.copy_top_obj.label.pos = self.copy_top_obj.obj.pos + vector(0, 0.22, 0)
        if self.copy_bottom_obj:
            self.copy_bottom_obj.obj.pos = self.copy_bottom_obj.target_pos + vector(0, 0.02 * cos(sim_time * 3 + self.index), 0)
            self.copy_bottom_obj.label.pos = self.copy_bottom_obj.obj.pos - vector(0, 0.22, 0)


class FreeNucleotide:
    def __init__(self, base=None, pos=None, vel=None):
        self.base = base if base else choice(["A", "T", "C", "G"])
        self.attached = False
        self.template_pair = None
        self.target_pos = None
        self.age = 0.0
        self.orbit_phase = uniform(0, 2 * pi)
        self.orbit_radius = uniform(0.05, 0.22)

        self.pos = pos if pos is not None else vector(uniform(-5, 5), uniform(-4.8, 4.8), uniform(-3.8, 3.8))
        self.vel = vel if vel is not None else rand_vec(0.45)
        self.obj = register(sphere(
            pos=self.pos,
            radius=0.135,
            color=BASE_COLORS[self.base],
            opacity=0.86,
            shininess=0.75,
            make_trail=True,
            retain=18,
            trail_radius=0.015
        ))
        self.label = make_text(self.obj.pos + vector(0, 0.22, 0), self.base, 0.10, vector(0.04, 0.04, 0.06))

    def attach_to(self, pos, required_base, pair):
        self.base = required_base
        self.attached = True
        self.template_pair = pair
        self.target_pos = vector(pos)
        self.vel = vector(0, 0, 0)
        self.obj.clear_trail()
        self.obj.color = BASE_COLORS[self.base]
        self.obj.opacity = 0.97
        self.obj.radius = 0.155
        self.obj.pos = self.target_pos
        self.label.text = self.base
        self.label.pos = self.target_pos + vector(0, 0.22, 0)
        if self in free_nucleotides:
            free_nucleotides.remove(self)
        if self not in attached_nucleotides:
            attached_nucleotides.append(self)

    def detach(self):
        self.attached = False
        self.template_pair = None
        self.target_pos = None
        self.obj.opacity = 0.80
        self.obj.radius = 0.135
        self.vel = rand_vec(0.8)
        if self in attached_nucleotides:
            attached_nucleotides.remove(self)
        if self not in free_nucleotides:
            free_nucleotides.append(self)

    def update_free(self, dt, attract_targets):
        if self.attached:
            return

        self.age += dt

        # Brownian drift with mild attraction toward open unmatched template targets.
        force = rand_vec(0.08)
        nearest = None
        nearest_d = 999

        for target_pos, needed_base in attract_targets:
            d = mag(target_pos - self.obj.pos)
            if needed_base == self.base and d < nearest_d:
                nearest = target_pos
                nearest_d = d

        if nearest is not None:
            direction = safe_norm(nearest - self.obj.pos)
            force += direction * clamp(1.6 / max(nearest_d * nearest_d, 0.25), 0.0, 1.15)

            # If very near a target, orbit briefly before attachment can happen.
            if nearest_d < 1.1:
                tangent = vector(-direction.y, direction.x, 0)
                if mag(tangent) < 0.01:
                    tangent = vector(0, -direction.z, direction.y)
                force += safe_norm(tangent) * 0.18

        # Gentle central containment.
        if mag(self.obj.pos) > 7.8:
            force += -safe_norm(self.obj.pos) * 0.45

        self.vel += force * dt
        self.vel *= 0.987

        # Bounce off invisible soft bounds.
        next_pos = self.obj.pos + self.vel * dt
        bounced = False
        if abs(next_pos.x) > WORLD_X_LIMIT:
            self.vel.x *= -0.8
            bounced = True
        if abs(next_pos.y) > WORLD_Y_LIMIT:
            self.vel.y *= -0.8
            bounced = True
        if abs(next_pos.z) > WORLD_Z_LIMIT:
            self.vel.z *= -0.8
            bounced = True
        if bounced:
            make_mark(self.obj.pos, vector(0.72, 0.72, 0.72), "bounce")

        self.obj.pos += self.vel * dt
        wrap_position(self.obj.pos)
        self.label.pos = self.obj.pos + vector(0, 0.22, 0)

    def try_attach(self, open_targets):
        if self.attached:
            return False

        for pair, strand_name, target_pos, needed_base in open_targets:
            if self.base != needed_base:
                continue
            d = mag(self.obj.pos - target_pos)
            if d <= ATTACH_DISTANCE:
                return pair.attach_copy(strand_name, self)

        return False


class ReplicationEnzyme:
    def __init__(self, name, color_value, radius, pos, label_offset):
        self.name = name
        self.body = register(sphere(pos=pos, radius=radius, color=color_value, opacity=0.82, shininess=0.85))
        self.ring_obj = register(ring(
            pos=pos,
            axis=vector(1, 0, 0),
            radius=radius * 1.25,
            thickness=0.045,
            color=color_value,
            opacity=0.55
        ))
        self.pointer = register(cone(
            pos=pos + vector(0.24, 0, 0),
            axis=vector(0.34, 0, 0),
            radius=radius * 0.38,
            color=color_value,
            opacity=0.72
        ))
        self.label_offset = label_offset
        self.label = make_text(pos + label_offset, name, 0.14, vector(0.10, 0.14, 0.20))

    def move_to(self, pos, direction=RIGHT):
        self.body.pos = pos
        self.ring_obj.pos = pos
        self.pointer.pos = pos + vector(0.20 * direction, 0, 0)
        self.pointer.axis = vector(0.36 * direction, 0, 0)
        self.ring_obj.axis = vector(1, 0.08 * sin(sim_time * 3), 0.08 * cos(sim_time * 3))
        self.label.pos = pos + self.label_offset

    def pulse(self, amount=1.0):
        self.body.radius = self.body.radius * (0.995 + 0.01 * amount)


class EventMark:
    def __init__(self, pos, color_value, text_value):
        self.age = 0.0
        self.max_age = 1.6
        self.obj = register(sphere(pos=pos, radius=0.06, color=color_value, opacity=0.55))
        self.ripple = register(ring(pos=pos, axis=vector(1, 0, 0), radius=0.12, thickness=0.012, color=color_value, opacity=0.42))
        self.label = make_text(pos + vector(0, 0.18, 0), text_value, 0.075, color_value)

    def update(self, dt):
        self.age += dt
        k = self.age / self.max_age
        self.obj.radius = 0.06 + 0.10 * k
        self.obj.opacity = max(0, 0.55 * (1 - k))
        self.ripple.radius = 0.12 + 0.55 * k
        self.ripple.opacity = max(0, 0.42 * (1 - k))
        self.label.opacity = max(0, 1 - k)
        if self.age >= self.max_age:
            self.obj.visible = False
            self.ripple.visible = False
            self.label.visible = False
            return False
        return True


class FloatingParticle:
    def __init__(self, pos, color_value, vel=None):
        self.age = 0.0
        self.max_age = uniform(1.2, 3.0)
        self.vel = vel if vel is not None else rand_vec(0.8)
        self.obj = register(sphere(pos=pos, radius=0.04, color=color_value, opacity=0.45))

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.vel * dt
        self.vel *= 0.98
        k = self.age / self.max_age
        self.obj.opacity = max(0, 0.45 * (1 - k))
        if self.age >= self.max_age:
            self.obj.visible = False
            return False
        return True


def make_mark(pos, color_value, text_value="mark"):
    mark = EventMark(vector(pos), color_value, text_value)
    event_marks.append(mark)
    return mark


def emit_particles(pos, color_value, count=8, strength=1.0):
    for _ in range(count):
        floating_particles.append(FloatingParticle(
            vector(pos),
            color_value,
            rand_vec(strength)
        ))


# -----------------------------
# AI controller
# -----------------------------

class DNAReplicationAI:
    """
    Expressive rule-based AI controller.

    The AI reads:
        - fork positions and replication progress
        - number of free nucleotides
        - number of missing complementary bases
        - attachment rate / recent change
        - whether replication is complete or stagnant
        - current mode and time in mode

    The AI can:
        - change replication speed
        - choose behavior modes
        - spawn, organize, spill, or orbit nucleotides
        - detach a few incorrect/stale-looking bases in repair mode
        - mark regions of interest
        - reset and start new rounds
    """
    def __init__(self):
        self.mode = "careful"
        self.available_modes = ["careful", "curious", "chaotic", "ritual", "artistic", "repair"]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.completion_timer = 0.0
        self.stagnation_timer = 0.0
        self.last_copied_count = 0
        self.last_progress_value = -1
        self.round_wait_timer = 0.0
        self.override_intensity = 0.0

    def set_mode(self, mode):
        if mode not in self.available_modes:
            return
        self.mode = mode
        self.mode_timer = 0.0
        self.action_timer = 0.0
        make_mark(vector(0, 3.25, 0), vector(0.60, 0.40, 1.0), "AI " + mode)
        emit_particles(vector(0, 3.1, 0), vector(0.60, 0.40, 1.0), 16, 1.2)

    def read_state(self):
        total_slots = HELIX_LENGTH * 2
        copied = sum(1 for p in template_pairs if p.copied_top) + sum(1 for p in template_pairs if p.copied_bottom)
        unzipped = sum(1 for p in template_pairs if p.unzipped)
        missing = total_slots - copied
        open_targets = get_open_targets()
        progress_value = copied + unzipped * 0.25 + (left_fork_index + (HELIX_LENGTH - 1 - right_fork_index)) * 0.5
        complete = copied >= total_slots
        sparse = len(free_nucleotides) < 18
        crowded = len(free_nucleotides) > 95

        return {
            "total_slots": total_slots,
            "copied": copied,
            "missing": missing,
            "unzipped": unzipped,
            "open_targets_count": len(open_targets),
            "free_count": len(free_nucleotides),
            "complete": complete,
            "sparse": sparse,
            "crowded": crowded,
            "progress_value": progress_value,
        }

    def update_stagnation(self, dt, state):
        copied_changed = state["copied"] != self.last_copied_count
        progress_changed = abs(state["progress_value"] - self.last_progress_value) > 0.1

        if copied_changed or progress_changed:
            self.stagnation_timer = 0.0
            self.last_copied_count = state["copied"]
            self.last_progress_value = state["progress_value"]
        else:
            self.stagnation_timer += dt

    def choose_mode(self, state):
        # React to real state first.
        if state["complete"]:
            return "artistic"
        if self.stagnation_timer > 6.0:
            return "repair"
        if state["sparse"]:
            return "curious"
        if state["crowded"]:
            return "careful"

        # Avoid doing the same thing forever.
        if self.mode_timer > uniform(9.0, 15.0):
            return choice(self.available_modes)

        # Occasional expressive shift.
        if random() < 0.003:
            return choice(self.available_modes)

        return self.mode

    def act(self, dt, state):
        global fork_speed

        if not ai_enabled:
            return

        self.mode_timer += dt
        self.action_timer += dt
        self.update_stagnation(dt, state)

        chosen = self.choose_mode(state)
        if chosen != self.mode:
            self.set_mode(chosen)

        # Completion loop: pause briefly, make visible celebration, then reset.
        if state["complete"]:
            self.completion_timer += dt
            if self.action_timer > 0.22:
                self.action_timer = 0.0
                emit_particles(vector(uniform(-5, 5), uniform(-2, 2), uniform(-2, 2)), vector(0.35, 0.62, 1.0), 4, 1.0)
            if self.completion_timer > 4.0:
                reset_simulation(new_round=True)
                self.completion_timer = 0.0
            return
        else:
            self.completion_timer = 0.0

        if self.mode == "careful":
            fork_speed = clamp(fork_speed + 0.12 * dt, 0.55, 1.45)
            if state["sparse"] and self.action_timer > 1.2:
                self.action_timer = 0.0
                spawn_nucleotide_cloud(count=12, near_forks=True)
            if self.action_timer > 1.7:
                self.action_timer = 0.0
                organize_nucleotides_toward_targets(max_items=14, strength=0.55)

        elif self.mode == "curious":
            fork_speed = clamp(fork_speed + 0.25 * dt, 0.75, 2.15)
            if self.action_timer > 0.9:
                self.action_timer = 0.0
                spawn_nucleotide_cloud(count=16, near_forks=random() < 0.65)
                mark_open_target()

        elif self.mode == "chaotic":
            fork_speed = clamp(fork_speed + uniform(-0.08, 0.12), 0.7, 2.55)
            if self.action_timer > 0.45:
                self.action_timer = 0.0
                spill_nucleotides()
                if random() < 0.25:
                    detach_one_recent_copy()

        elif self.mode == "ritual":
            fork_speed = clamp(1.0 + 0.45 * sin(sim_time * 0.9), 0.55, 1.65)
            if self.action_timer > 0.7:
                self.action_timer = 0.0
                arrange_nucleotides_in_orbit()
                emit_particles(vector(0, 0, 0), vector(0.95, 0.72, 0.20), 5, 0.7)

        elif self.mode == "artistic":
            fork_speed = clamp(fork_speed * 0.998 + 0.002 * 1.2, 0.65, 1.55)
            if self.action_timer > 0.55:
                self.action_timer = 0.0
                paint_replication_wave()
                organize_nucleotides_toward_targets(max_items=8, strength=0.25)

        elif self.mode == "repair":
            fork_speed = clamp(1.35, 0.7, 1.7)
            if self.action_timer > 0.8:
                self.action_timer = 0.0
                spawn_needed_nucleotides(count=18)
                organize_nucleotides_toward_targets(max_items=30, strength=0.9)
                if self.stagnation_timer > 10.0:
                    force_attach_one_missing()
                    self.stagnation_timer = 0.0


ai_controller = DNAReplicationAI()

# -----------------------------
# AI action helpers
# -----------------------------

def get_open_targets():
    targets = []
    for pair in template_pairs:
        if not pair.unzipped:
            continue
        if not pair.copied_top:
            targets.append((pair, "top", daughter_position(pair.top_pos, 1), PAIR_MATCH[pair.base_top]))
        if not pair.copied_bottom:
            targets.append((pair, "bottom", daughter_position(pair.bottom_pos, -1), PAIR_MATCH[pair.base_bottom]))
    return targets


def get_target_points_for_motion():
    return [(pos, needed) for _, _, pos, needed in get_open_targets()]


def spawn_nucleotide(base=None, pos=None, vel=None):
    n = FreeNucleotide(base=base, pos=pos, vel=vel)
    free_nucleotides.append(n)
    return n


def spawn_nucleotide_cloud(count=20, near_forks=False):
    for _ in range(count):
        base = choice(["A", "T", "C", "G"])
        if near_forks:
            side = choice([LEFT, RIGHT])
            fork_x = x_for_index(left_fork_index if side == LEFT else right_fork_index)
            pos = vector(
                fork_x + uniform(-1.0, 1.0),
                uniform(-3.8, 3.8),
                uniform(-2.8, 2.8)
            )
        else:
            pos = vector(uniform(-WORLD_X_LIMIT * 0.75, WORLD_X_LIMIT * 0.75), uniform(-4.6, 4.6), uniform(-3.2, 3.2))
        spawn_nucleotide(base=base, pos=pos, vel=rand_vec(0.9))
    make_mark(vector(0, -3.2, 0), vector(0.30, 0.70, 1.0), "spawn")


def spawn_needed_nucleotides(count=12):
    targets = get_open_targets()
    if not targets:
        spawn_nucleotide_cloud(count=count, near_forks=True)
        return
    for _ in range(count):
        pair, strand, pos, needed = choice(targets)
        npos = pos + rand_vec(1.1)
        spawn_nucleotide(base=needed, pos=npos, vel=safe_norm(pos - npos) * uniform(0.4, 1.0))
    make_mark(vector(0, -3.55, 0), vector(0.34, 0.88, 0.44), "needed")


def organize_nucleotides_toward_targets(max_items=12, strength=0.5):
    targets = get_open_targets()
    if not targets:
        return
    moved = 0
    for n in list(free_nucleotides):
        if moved >= max_items:
            break
        compatible = [(pos, needed) for _, _, pos, needed in targets if needed == n.base]
        if not compatible:
            continue
        pos, needed = min(compatible, key=lambda item: mag(item[0] - n.obj.pos))
        n.vel += safe_norm(pos - n.obj.pos) * strength
        moved += 1


def arrange_nucleotides_in_orbit():
    if not free_nucleotides:
        return
    center = vector(0, 0, 0)
    for i, n in enumerate(free_nucleotides[:50]):
        angle = sim_time * 1.6 + i * 0.38
        radius = 3.2 + 0.3 * sin(i)
        target = center + vector(radius * cos(angle), 2.2 * sin(angle * 0.7), radius * sin(angle))
        n.vel += safe_norm(target - n.obj.pos) * 0.32


def spill_nucleotides():
    if len(free_nucleotides) < 120:
        spawn_nucleotide_cloud(count=8, near_forks=random() < 0.4)
    for n in free_nucleotides[:30]:
        n.vel += rand_vec(1.2)
    make_mark(vector(uniform(-3, 3), uniform(-2, 2), uniform(-1, 1)), vector(1.0, 0.45, 0.35), "spill")


def detach_one_recent_copy():
    copied_pairs = [p for p in template_pairs if p.copied_top or p.copied_bottom]
    if not copied_pairs:
        return
    p = choice(copied_pairs)
    if p.copied_top and p.copied_bottom:
        strand = choice(["top", "bottom"])
    elif p.copied_top:
        strand = "top"
    else:
        strand = "bottom"

    if p.detach_copy(strand):
        make_mark(template_positions(p.index)[0], vector(1.0, 0.38, 0.30), "detach")


def force_attach_one_missing():
    targets = get_open_targets()
    if not targets:
        return
    pair, strand, pos, needed = choice(targets)
    n = spawn_nucleotide(base=needed, pos=pos + rand_vec(0.3), vel=vector(0, 0, 0))
    pair.attach_copy(strand, n)
    make_mark(pos, vector(0.25, 0.95, 0.50), "repair")


def mark_open_target():
    targets = get_open_targets()
    if not targets:
        return
    pair, strand, pos, needed = choice(targets)
    make_mark(pos, BASE_COLORS[needed], "seek " + needed)


def paint_replication_wave():
    # A visible wave following copied/unzipped areas.
    copied = [p for p in template_pairs if p.copied_top or p.copied_bottom]
    if not copied:
        return
    p = choice(copied)
    pos = (p.top_pos + p.bottom_pos) * 0.5
    emit_particles(pos, vector(0.58, 0.40, 1.0), 7, 0.9)
    make_mark(pos, vector(0.58, 0.40, 1.0), "wave")


# -----------------------------
# World creation
# -----------------------------

def create_background_guides():
    global progress_bar, progress_fill, origin_marker

    # Soft floor grid.
    for x in range(-9, 10, 2):
        register(curve(pos=[vector(x, -5.35, -4.6), vector(x, -5.35, 4.6)], color=vector(0.82, 0.88, 0.94), radius=0.008))
    for z in range(-4, 5, 2):
        register(curve(pos=[vector(-9.4, -5.35, z), vector(9.4, -5.35, z)], color=vector(0.82, 0.88, 0.94), radius=0.008))

    origin_marker = register(ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=2.75, thickness=0.018, color=vector(0.95, 0.70, 0.20), opacity=0.25))
    make_text(vector(0, 4.55, 0), "DNA replication origin: forks move outward", 0.18, vector(0.15, 0.20, 0.30))

    # Legend.
    lx = -9.2
    ly = 4.75
    make_text(vector(lx + 1.3, ly, 0), "Base colors", 0.15, vector(0.15, 0.18, 0.24))
    for j, base in enumerate(["A", "T", "C", "G"]):
        register(sphere(pos=vector(lx + j * 0.55, ly - 0.48, 0), radius=0.14, color=BASE_COLORS[base], opacity=0.95))
        make_text(vector(lx + j * 0.55, ly - 0.78, 0), base, 0.11, vector(0.08, 0.10, 0.14))

    # Progress bar.
    progress_bar = register(box(pos=vector(0, -5.88, 0), size=vector(8.2, 0.10, 0.10), color=vector(0.78, 0.84, 0.90), opacity=0.50))
    progress_fill = register(box(pos=vector(-4.1, -5.88, 0), size=vector(0.01, 0.16, 0.16), color=vector(0.30, 0.68, 1.0), opacity=0.82))


def create_dna():
    global template_pairs

    template_pairs = []
    for i, base in enumerate(BASE_SEQUENCE):
        p = BasePair(i, base)
        template_pairs.append(p)

    for i in range(len(template_pairs) - 1):
        template_pairs[i].set_backbone_links(template_pairs[i + 1])

    # Highlight initial origin.
    for i in [HELIX_LENGTH // 2 - 1, HELIX_LENGTH // 2]:
        make_mark((template_pairs[i].top_pos + template_pairs[i].bottom_pos) * 0.5, vector(0.95, 0.72, 0.20), "origin")


def create_enzymes():
    global left_helicase, right_helicase
    global left_polymerase_top, left_polymerase_bottom, right_polymerase_top, right_polymerase_bottom

    left_helicase = ReplicationEnzyme("helicase L", vector(1.0, 0.62, 0.18), 0.36, vector(-0.4, 0, 0), vector(0, 0.55, 0))
    right_helicase = ReplicationEnzyme("helicase R", vector(1.0, 0.62, 0.18), 0.36, vector(0.4, 0, 0), vector(0, 0.55, 0))

    left_polymerase_top = ReplicationEnzyme("polymerase", vector(0.35, 0.68, 1.0), 0.25, vector(-0.6, 2.9, 0), vector(0, 0.42, 0))
    left_polymerase_bottom = ReplicationEnzyme("polymerase", vector(0.30, 0.82, 0.48), 0.25, vector(-0.6, -2.9, 0), vector(0, -0.42, 0))

    right_polymerase_top = ReplicationEnzyme("polymerase", vector(0.35, 0.68, 1.0), 0.25, vector(0.6, 2.9, 0), vector(0, 0.42, 0))
    right_polymerase_bottom = ReplicationEnzyme("polymerase", vector(0.30, 0.82, 0.48), 0.25, vector(0.6, -2.9, 0), vector(0, -0.42, 0))


def create_labels():
    global status_label, control_label, mode_label
    status_label = make_text(vector(0, 5.55, 0), "", 0.16, vector(0.10, 0.14, 0.20), box=False)
    mode_label = make_text(vector(7.2, 5.1, 0), "", 0.15, vector(0.10, 0.14, 0.20), box=False)
    control_label = make_text(
        vector(0, -6.35, 0),
        "Controls: A AI | P pause | R reset | O override | Space spawn | 1-6 AI modes | arrows speed/forks | H help",
        0.13,
        vector(0.10, 0.14, 0.20),
        box=False
    )


def initialize_world():
    create_background_guides()
    create_dna()
    create_enzymes()
    create_labels()
    spawn_nucleotide_cloud(count=70, near_forks=False)
    spawn_needed_nucleotides(count=24)


# -----------------------------
# Simulation mechanics
# -----------------------------

def reset_simulation(new_round=False):
    global left_fork_index, right_fork_index, fork_progress, fork_speed
    global sim_time, round_number, paused, human_override_timer
    global free_nucleotides, attached_nucleotides, event_marks, floating_particles
    global ai_controller

    delete_all_visuals()

    if new_round:
        round_number += 1

    free_nucleotides = []
    attached_nucleotides = []
    event_marks = []
    floating_particles = []

    left_fork_index = HELIX_LENGTH // 2 - 1
    right_fork_index = HELIX_LENGTH // 2
    fork_progress = 0.0
    fork_speed = 1.05
    human_override_timer = 0.0
    paused = False

    ai_controller.mode_timer = 0.0
    ai_controller.action_timer = 0.0
    ai_controller.stagnation_timer = 0.0
    ai_controller.completion_timer = 0.0
    ai_controller.last_copied_count = 0
    ai_controller.last_progress_value = -1

    initialize_world()
    make_mark(vector(0, 0, 0), vector(0.60, 0.40, 1.0), "round " + str(round_number))


def unzip_step():
    global left_fork_index, right_fork_index

    if left_fork_index >= 0:
        template_pairs[left_fork_index].unzip(LEFT)
        emit_particles((template_pairs[left_fork_index].top_pos + template_pairs[left_fork_index].bottom_pos) * 0.5, vector(1.0, 0.70, 0.22), 5, 0.6)
        left_fork_index -= 1

    if right_fork_index < HELIX_LENGTH:
        template_pairs[right_fork_index].unzip(RIGHT)
        emit_particles((template_pairs[right_fork_index].top_pos + template_pairs[right_fork_index].bottom_pos) * 0.5, vector(1.0, 0.70, 0.22), 5, 0.6)
        right_fork_index += 1


def update_forks(dt):
    global fork_progress

    fork_progress += dt * fork_speed
    if fork_progress >= 1.0:
        fork_progress -= 1.0
        unzip_step()


def try_attach_free_nucleotides():
    open_targets = get_open_targets()
    if not open_targets:
        return
    for n in list(free_nucleotides):
        if n.try_attach(open_targets):
            continue


def update_enzymes():
    # Move enzymes to fork positions, or keep them at the completed ends.
    left_i = clamp(left_fork_index + 1, 0, HELIX_LENGTH - 1)
    right_i = clamp(right_fork_index - 1, 0, HELIX_LENGTH - 1)

    left_pos = vector(x_for_index(left_i), 0, 0)
    right_pos = vector(x_for_index(right_i), 0, 0)

    left_helicase.move_to(left_pos + vector(-0.28, 0, 0), LEFT)
    right_helicase.move_to(right_pos + vector(0.28, 0, 0), RIGHT)

    left_polymerase_top.move_to(left_pos + vector(-0.55, 2.75, 0.2 * sin(sim_time * 2)), LEFT)
    left_polymerase_bottom.move_to(left_pos + vector(-0.55, -2.75, 0.2 * cos(sim_time * 2)), LEFT)
    right_polymerase_top.move_to(right_pos + vector(0.55, 2.75, 0.2 * cos(sim_time * 2)), RIGHT)
    right_polymerase_bottom.move_to(right_pos + vector(0.55, -2.75, 0.2 * sin(sim_time * 2)), RIGHT)


def update_visual_objects(dt):
    targets = get_target_points_for_motion()

    for pair in template_pairs:
        pair.update(dt)

    for n in list(free_nucleotides):
        n.update_free(dt, targets)

    try_attach_free_nucleotides()

    for mark in list(event_marks):
        if not mark.update(dt):
            event_marks.remove(mark)

    for p in list(floating_particles):
        if not p.update(dt):
            floating_particles.remove(p)

    update_enzymes()


def update_ui():
    copied = sum(1 for p in template_pairs if p.copied_top) + sum(1 for p in template_pairs if p.copied_bottom)
    total = HELIX_LENGTH * 2
    unzipped = sum(1 for p in template_pairs if p.unzipped)
    pct = copied / total if total else 0

    status_label.text = (
        "Round {round_no} | copied {copied}/{total} | unzipped {unzipped}/{helix} | "
        "free nucleotides {free_count} | speed {speed:.2f} | {pause}"
    ).format(
        round_no=round_number,
        copied=copied,
        total=total,
        unzipped=unzipped,
        helix=HELIX_LENGTH,
        free_count=len(free_nucleotides),
        speed=fork_speed,
        pause="PAUSED" if paused else "running"
    )

    mode_label.text = "AI: {state}\nmode: {mode}\nstagnation: {stag:.1f}s".format(
        state="on" if ai_enabled else "off",
        mode=ai_controller.mode,
        stag=ai_controller.stagnation_timer
    )

    fill_width = 8.2 * pct
    progress_fill.size = vector(max(0.01, fill_width), 0.16, 0.16)
    progress_fill.pos = vector(-4.1 + fill_width * 0.5, -5.88, 0)


def manual_move_forks(direction):
    global left_fork_index, right_fork_index
    if direction == LEFT and left_fork_index >= 0:
        template_pairs[left_fork_index].unzip(LEFT)
        left_fork_index -= 1
    elif direction == RIGHT and right_fork_index < HELIX_LENGTH:
        template_pairs[right_fork_index].unzip(RIGHT)
        right_fork_index += 1


def print_controls():
    print(__doc__)


def keydown(evt):
    global paused, ai_enabled, fork_speed, human_override_timer

    key = evt.key.lower()

    if key == "h":
        print_controls()
    elif key == "a":
        ai_enabled = not ai_enabled
        make_mark(vector(0, 3.6, 0), vector(0.6, 0.4, 1.0), "AI " + ("on" if ai_enabled else "off"))
    elif key == "p":
        paused = not paused
        make_mark(vector(0, 3.8, 0), vector(0.3, 0.5, 1.0), "pause" if paused else "resume")
    elif key == "r":
        reset_simulation(new_round=False)
    elif key == "o":
        human_override_timer = 2.2
        spawn_needed_nucleotides(count=32)
        organize_nucleotides_toward_targets(max_items=45, strength=1.1)
        make_mark(vector(0, -3.9, 0), vector(1.0, 0.35, 0.25), "override")
    elif key == " ":
        spawn_nucleotide_cloud(count=26, near_forks=True)
    elif key == "1":
        ai_controller.set_mode("careful")
    elif key == "2":
        ai_controller.set_mode("curious")
    elif key == "3":
        ai_controller.set_mode("chaotic")
    elif key == "4":
        ai_controller.set_mode("ritual")
    elif key == "5":
        ai_controller.set_mode("artistic")
    elif key == "6":
        ai_controller.set_mode("repair")
    elif key == "up":
        fork_speed = clamp(fork_speed + 0.2, 0.25, 3.2)
    elif key == "down":
        fork_speed = clamp(fork_speed - 0.2, 0.25, 3.2)
    elif key == "left":
        manual_move_forks(LEFT)
    elif key == "right":
        manual_move_forks(RIGHT)


scene.bind("keydown", keydown)

# -----------------------------
# Main loop
# -----------------------------

initialize_world()
print_controls()

dt = 1 / 60.0

while True:
    rate(60)
    if paused:
        update_ui()
        continue

    sim_time += dt

    if human_override_timer > 0:
        human_override_timer -= dt

    state = ai_controller.read_state()
    ai_controller.act(dt, state)

    # Human override temporarily boosts constructive behavior but still allows AI.
    if human_override_timer > 0:
        organize_nucleotides_toward_targets(max_items=16, strength=0.35)

    update_forks(dt)
    update_visual_objects(dt)
    update_ui()
