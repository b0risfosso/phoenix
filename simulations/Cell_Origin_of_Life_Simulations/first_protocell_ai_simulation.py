#!/usr/bin/env python3
"""
First Protocell Simulation — 3D VPython Simulation with Expressive AI Controller (vector-limit fixed)

Run:
    pip install vpython
    python first_protocell_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset simulation
    M       cycle AI behavior mode
    L       force lipid spill
    N       force nutrient/molecule spill
    S       force split on largest protocell
    D       disturb/shake protocells
    C       clear temporary markers
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    A translucent membrane bubble traps molecules inside. Free lipids drift through
    the environment, collide with protocells, and attach to their membranes. When a
    protocell grows past its division threshold, it pinches into two daughter cells
    that inherit internal molecules. The AI controller reads the state, chooses
    behavior modes, spills material, nudges protocells, marks targets, triggers
    splits, detects stagnation/completion, and loops into new rounds.

This file is self-contained and intentionally uses VPython primitives only.
"""

from vpython import *
import random
import math
from collections import deque

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="First Protocell Simulation — Membrane Growth, Molecule Trapping, Division, AI",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
)

scene.camera.pos = vector(0, 0, 16)
scene.camera.axis = vector(0, 0, -16)
scene.forward = vector(0, 0, -1)
scene.up = vector(0, 1, 0)

WORLD_RADIUS = 7.8
BASE_DT = 0.016
sim_speed = 1.0
paused = False
ai_enabled = True
round_number = 1
global_time = 0.0
split_count = 0

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COLORS = {
    "membrane": vector(0.42, 0.72, 1.0),
    "membrane_edge": vector(0.16, 0.46, 0.95),
    "membrane_divide": vector(0.84, 0.54, 1.0),
    "lipid": vector(1.0, 0.72, 0.25),
    "lipid_tail": vector(0.95, 0.55, 0.18),
    "nutrient": vector(0.25, 0.78, 0.52),
    "catalyst": vector(0.95, 0.35, 0.45),
    "marker": vector(1.0, 0.45, 0.75),
    "trail": vector(0.70, 0.78, 0.90),
    "field": vector(0.74, 0.86, 1.0),
    "text": vector(0.18, 0.22, 0.30),
    "warning": vector(1.0, 0.35, 0.28),
    "ai": vector(0.55, 0.45, 1.0),
    "inherit": vector(0.35, 0.95, 0.85),
}

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def rand_unit_vector():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        m = mag(v)
        if m > 0.001:
            return v / m

def rand_in_sphere(radius):
    return rand_unit_vector() * (radius * (random.random() ** (1.0 / 3.0)))

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m

def limit_vec(v, max_mag):
    """VPython vector-compatible replacement for v.limit(max_mag)."""
    m = mag(v)
    if m > max_mag and m > 1e-8:
        return v * (max_mag / m)
    return v

def mix_vec(a, b, t):
    return a * (1 - t) + b * t

def pair_key(a, b):
    return tuple(sorted((a, b)))

# ---------------------------------------------------------------------------
# Visual boundary and labels
# ---------------------------------------------------------------------------

world_shell = sphere(
    pos=vector(0, 0, 0),
    radius=WORLD_RADIUS,
    color=COLORS["field"],
    opacity=0.045,
    shininess=0.2,
)
world_ring_1 = ring(pos=vector(0, 0, 0), axis=vector(0, 0, 1), radius=WORLD_RADIUS, thickness=0.012, color=vector(0.66, 0.78, 0.95), opacity=0.25)
world_ring_2 = ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=WORLD_RADIUS, thickness=0.012, color=vector(0.66, 0.78, 0.95), opacity=0.18)
world_ring_3 = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=WORLD_RADIUS, thickness=0.012, color=vector(0.66, 0.78, 0.95), opacity=0.18)

status_label = label(
    pos=vector(-7.8, 7.0, 0),
    text="",
    align="left",
    height=13,
    border=8,
    box=True,
    color=COLORS["text"],
    background=vector(1, 1, 1),
    opacity=0.72,
)

legend_label = label(
    pos=vector(5.6, -6.9, 0),
    text="Lipids attach to membranes • Internal molecules are inherited • AI can spill, nudge, mark, split, and reset",
    align="center",
    height=11,
    border=6,
    box=True,
    color=COLORS["text"],
    background=vector(1, 1, 1),
    opacity=0.62,
)

# ---------------------------------------------------------------------------
# Ephemeral visual marks
# ---------------------------------------------------------------------------

spark_marks = []
ai_markers = []

class Spark:
    def __init__(self, pos, color, radius=0.06, life=1.0, velocity=None):
        self.life = life
        self.max_life = life
        self.vel = velocity if velocity is not None else rand_unit_vector() * random.uniform(0.25, 1.0)
        self.obj = sphere(pos=pos, radius=radius, color=color, opacity=0.75, emissive=True)

    def update(self, dt):
        self.life -= dt
        self.obj.pos += self.vel * dt
        self.obj.radius *= (1.0 + 0.4 * dt)
        self.obj.opacity = max(0.0, 0.75 * self.life / self.max_life)
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True

class AIMarker:
    def __init__(self, pos, label_text, color=COLORS["ai"], life=2.2):
        self.life = life
        self.max_life = life
        self.ring = ring(pos=pos, axis=vector(0, 0, 1), radius=0.55, thickness=0.035, color=color, opacity=0.8)
        self.label = label(
            pos=pos + vector(0, 0.55, 0),
            text=label_text,
            height=10,
            border=4,
            box=False,
            color=color,
            opacity=0.0,
        )

    def update(self, dt):
        self.life -= dt
        self.ring.radius += 0.25 * dt
        self.ring.rotate(angle=1.7 * dt, axis=vector(0, 0, 1), origin=self.ring.pos)
        opacity = max(0.0, min(0.8, 0.8 * self.life / self.max_life))
        self.ring.opacity = opacity
        self.label.opacity = 0.0
        if self.life <= 0:
            self.ring.visible = False
            self.label.visible = False
            return False
        return True

def spawn_sparks(pos, count, color, speed=1.0, radius=0.045, life=0.9):
    for _ in range(count):
        spark_marks.append(Spark(pos, color, radius=radius, life=life * random.uniform(0.7, 1.35), velocity=rand_unit_vector() * random.uniform(0.2, speed)))

def clear_marks():
    for s in spark_marks:
        s.obj.visible = False
    spark_marks.clear()
    for m in ai_markers:
        m.ring.visible = False
        m.label.visible = False
    ai_markers.clear()

# ---------------------------------------------------------------------------
# Free molecules and lipids
# ---------------------------------------------------------------------------

class FreeParticle:
    next_id = 1

    def __init__(self, kind="lipid", pos=None, vel=None):
        self.id = FreeParticle.next_id
        FreeParticle.next_id += 1
        self.kind = kind
        self.pos = pos if pos is not None else rand_in_sphere(WORLD_RADIUS * 0.82)
        self.vel = vel if vel is not None else rand_unit_vector() * random.uniform(0.08, 0.55)
        self.age = 0.0
        self.marked = False

        if kind == "lipid":
            self.radius = 0.105
            self.body = sphere(pos=self.pos, radius=self.radius, color=COLORS["lipid"], opacity=0.92)
            self.tail = cylinder(pos=self.pos, axis=rand_unit_vector() * 0.22, radius=0.026, color=COLORS["lipid_tail"], opacity=0.7)
        elif kind == "nutrient":
            self.radius = 0.08
            self.body = sphere(pos=self.pos, radius=self.radius, color=COLORS["nutrient"], opacity=0.88)
            self.tail = None
        elif kind == "catalyst":
            self.radius = 0.09
            self.body = sphere(pos=self.pos, radius=self.radius, color=COLORS["catalyst"], opacity=0.9)
            self.tail = None
        else:
            self.radius = 0.075
            self.body = sphere(pos=self.pos, radius=self.radius, color=vector(0.7, 0.7, 0.9), opacity=0.85)
            self.tail = None

        self.trail = curve(color=COLORS["trail"], radius=0.008, opacity=0.18)
        self.trail.append(self.pos)
        self.trail_limit = 16

    def set_visible(self, flag):
        self.body.visible = flag
        if self.tail:
            self.tail.visible = flag
        self.trail.visible = flag

    def remove(self):
        self.set_visible(False)

    def update_visual(self):
        self.body.pos = self.pos
        if self.kind == "lipid" and self.tail:
            self.tail.pos = self.pos - safe_norm(self.vel, rand_unit_vector()) * 0.08
            self.tail.axis = safe_norm(self.vel, rand_unit_vector()) * 0.25
        if self.marked:
            self.body.emissive = True
        else:
            self.body.emissive = False

    def drift(self, dt):
        self.age += dt
        swirl = vector(-self.pos.y, self.pos.x, 0) * 0.006
        random_force = rand_unit_vector() * 0.025
        self.vel += (swirl + random_force) * dt
        self.vel *= 0.994
        self.vel = limit_vec(self.vel, 1.15)
        self.pos += self.vel * dt

        distance = mag(self.pos)
        if distance > WORLD_RADIUS - 0.25:
            outward = safe_norm(self.pos)
            self.pos = outward * (WORLD_RADIUS - 0.25)
            self.vel = self.vel - 2 * dot(self.vel, outward) * outward
            self.vel *= 0.72
            spawn_sparks(self.pos, 1, vector(0.7, 0.85, 1.0), speed=0.25, radius=0.025, life=0.4)

        self.update_visual()
        # Store trail positions ourselves because VPython curve APIs differ by version.
        if not hasattr(self, "_trail_positions"):
            self._trail_positions = []
        self._trail_positions.append(vector(self.pos.x, self.pos.y, self.pos.z))
        if len(self._trail_positions) > self.trail_limit:
            self._trail_positions.pop(0)
        try:
            self.trail.clear()
            for tp in self._trail_positions:
                self.trail.append(tp)
        except Exception:
            pass

class InternalMolecule:
    next_id = 1

    def __init__(self, kind="nutrient", local_pos=None):
        self.id = InternalMolecule.next_id
        InternalMolecule.next_id += 1
        self.kind = kind
        self.local_pos = local_pos if local_pos is not None else rand_unit_vector() * random.uniform(0.05, 0.75)
        self.local_vel = rand_unit_vector() * random.uniform(0.05, 0.35)
        self.radius = 0.075 if kind == "nutrient" else 0.09
        c = COLORS["nutrient"] if kind == "nutrient" else COLORS["catalyst"]
        self.obj = sphere(pos=vector(0, 0, 0), radius=self.radius, color=c, opacity=0.92, emissive=False)
        self.phase = random.uniform(0, 2 * math.pi)

    def remove(self):
        self.obj.visible = False

    def clone_for_daughter(self, offset, shrink=0.86):
        nm = InternalMolecule(self.kind, (self.local_pos - offset) * shrink)
        nm.local_vel = self.local_vel + rand_unit_vector() * 0.05
        return nm

# ---------------------------------------------------------------------------
# Protocell model
# ---------------------------------------------------------------------------

class Protocell:
    next_id = 1

    def __init__(self, pos=None, radius=1.1, vel=None, lipids=28, molecules=None, generation=0):
        self.id = Protocell.next_id
        Protocell.next_id += 1
        self.pos = pos if pos is not None else rand_in_sphere(WORLD_RADIUS * 0.25)
        self.vel = vel if vel is not None else rand_unit_vector() * random.uniform(0.02, 0.16)
        self.radius = radius
        self.target_radius = radius
        self.lipids = lipids
        self.max_lipids_before_split = 70
        self.generation = generation
        self.age = 0.0
        self.split_charge = 0.0
        self.pinching = False
        self.pinching_axis = rand_unit_vector()
        self.marked_by_ai = False
        self.dead = False

        self.molecules = molecules if molecules is not None else []
        if not self.molecules:
            for _ in range(random.randint(7, 13)):
                self.molecules.append(InternalMolecule("nutrient"))
            if random.random() < 0.65:
                self.molecules.append(InternalMolecule("catalyst"))

        base_color = COLORS["membrane"] if generation % 2 == 0 else mix_vec(COLORS["membrane"], COLORS["membrane_divide"], 0.28)
        self.shell = sphere(pos=self.pos, radius=self.radius, color=base_color, opacity=0.24, shininess=0.55)
        self.outline = ring(pos=self.pos, axis=vector(0, 0, 1), radius=self.radius * 1.01, thickness=0.025, color=COLORS["membrane_edge"], opacity=0.55)
        self.outline2 = ring(pos=self.pos, axis=vector(1, 0, 0), radius=self.radius * 0.98, thickness=0.016, color=COLORS["membrane_edge"], opacity=0.26)
        self.neck = cylinder(pos=self.pos, axis=vector(0, 0.001, 0), radius=0.025, color=COLORS["membrane_divide"], opacity=0.0)

        self.label = label(
            pos=self.pos + vector(0, self.radius + 0.3, 0),
            text="",
            height=9,
            box=False,
            color=COLORS["text"],
            opacity=0.0,
        )

        for m in self.molecules:
            m.obj.pos = self.pos + m.local_pos

    def remove(self):
        self.dead = True
        self.shell.visible = False
        self.outline.visible = False
        self.outline2.visible = False
        self.neck.visible = False
        self.label.visible = False
        for m in self.molecules:
            m.remove()

    def contains_world_pos(self, p):
        return mag(p - self.pos) < self.radius * 0.92

    def absorb_lipid(self, lipid):
        self.lipids += 1
        self.target_radius += 0.017
        self.split_charge += 0.75
        spawn_sparks(lipid.pos, 4, COLORS["lipid"], speed=0.55, radius=0.035, life=0.6)
        # Ripple ring marking membrane absorption.
        ai_markers.append(AIMarker(lipid.pos, "+lipid", color=COLORS["lipid"], life=0.7))

    def import_molecule(self, particle):
        if len(self.molecules) > 52:
            return
        local = particle.pos - self.pos
        if mag(local) > self.radius * 0.7:
            local = safe_norm(local, rand_unit_vector()) * self.radius * 0.45
        im = InternalMolecule(particle.kind, local)
        self.molecules.append(im)
        spawn_sparks(particle.pos, 3, im.obj.color, speed=0.45, radius=0.03, life=0.7)

    def density(self):
        volume_scale = max(0.1, self.radius ** 3)
        return len(self.molecules) / volume_scale

    def ready_to_split(self):
        return self.lipids >= self.max_lipids_before_split or self.radius >= 1.95 or self.split_charge > 32

    def force_split(self):
        self.lipids = max(self.lipids, self.max_lipids_before_split)
        self.split_charge = max(self.split_charge, 36)

    def update_molecules(self, dt):
        for m in self.molecules:
            m.phase += dt * random.uniform(0.2, 0.7)
            swirl = vector(-m.local_pos.y, m.local_pos.x, 0) * 0.11
            center_pull = -m.local_pos * 0.18
            jitter = rand_unit_vector() * 0.11
            m.local_vel += (swirl + center_pull + jitter) * dt
            m.local_vel *= 0.985
            m.local_vel = limit_vec(m.local_vel, 0.8)
            m.local_pos += m.local_vel * dt

            wall = mag(m.local_pos)
            max_wall = self.radius * 0.78
            if wall > max_wall:
                n = safe_norm(m.local_pos)
                m.local_pos = n * max_wall
                m.local_vel = m.local_vel - 2 * dot(m.local_vel, n) * n
                m.local_vel *= 0.62

            wobble = vector(0.025 * math.sin(m.phase), 0.02 * math.cos(m.phase * 1.4), 0.018 * math.sin(m.phase * 0.7))
            m.obj.pos = self.pos + m.local_pos + wobble
            m.obj.radius = m.radius * (1.0 + 0.06 * math.sin(m.phase * 2.0))

    def update_visuals(self, dt):
        self.shell.pos = self.pos
        self.radius += (self.target_radius - self.radius) * min(1.0, 4.0 * dt)
        self.shell.radius = self.radius
        divide_t = clamp((self.lipids - 54) / 26.0, 0.0, 1.0)
        self.shell.color = mix_vec(COLORS["membrane"], COLORS["membrane_divide"], divide_t * 0.55)
        self.shell.opacity = 0.19 + 0.08 * math.sin(self.age * 2.0) ** 2 + 0.06 * divide_t

        self.outline.pos = self.pos
        self.outline.radius = self.radius * (1.01 + 0.018 * math.sin(self.age * 4.5))
        self.outline.axis = vector(math.sin(self.age * 0.6) * 0.25, math.cos(self.age * 0.4) * 0.25, 1)
        self.outline.opacity = 0.46 + 0.24 * divide_t

        self.outline2.pos = self.pos
        self.outline2.radius = self.radius * (0.95 + 0.025 * math.cos(self.age * 3.7))
        self.outline2.axis = vector(1, math.sin(self.age * 0.8) * 0.2, math.cos(self.age * 0.5) * 0.2)

        if self.ready_to_split():
            self.pinching = True

        if self.pinching:
            self.neck.opacity = min(0.75, self.neck.opacity + 1.2 * dt)
            self.neck.pos = self.pos - self.pinching_axis * self.radius * 0.65
            self.neck.axis = self.pinching_axis * self.radius * 1.3
            self.neck.radius = max(0.035, self.radius * (0.28 - 0.12 * math.sin(self.age * 9.0) ** 2))
            self.neck.color = COLORS["membrane_divide"]
        else:
            self.neck.opacity = max(0.0, self.neck.opacity - dt * 1.4)

        self.label.pos = self.pos + vector(0, self.radius + 0.35, 0)
        self.label.text = f"P{self.id}  lipids:{self.lipids}  mol:{len(self.molecules)}  gen:{self.generation}"
        self.label.visible = self.marked_by_ai or self.ready_to_split()
        self.label.opacity = 0.0

    def drift(self, dt):
        self.age += dt
        swirl = vector(-self.pos.y, self.pos.x, 0) * 0.003
        self.vel += (swirl + rand_unit_vector() * 0.018) * dt
        self.vel *= 0.992
        self.vel = limit_vec(self.vel, 0.55)
        self.pos += self.vel * dt

        dist = mag(self.pos)
        if dist + self.radius > WORLD_RADIUS - 0.1:
            n = safe_norm(self.pos)
            self.pos = n * (WORLD_RADIUS - self.radius - 0.1)
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.65

        self.update_molecules(dt)
        self.update_visuals(dt)

    def split(self):
        global split_count
        if len(self.molecules) < 2 and self.lipids < 25:
            self.pinching = False
            return []

        axis = safe_norm(self.pinching_axis, rand_unit_vector())
        offset = axis * self.radius * 0.52
        r1 = max(0.72, self.radius * random.uniform(0.68, 0.76))
        r2 = max(0.72, self.radius * random.uniform(0.68, 0.76))
        l1 = max(12, int(self.lipids * random.uniform(0.45, 0.55)))
        l2 = max(12, self.lipids - l1)

        mols1 = []
        mols2 = []
        for m in self.molecules:
            if dot(m.local_pos, axis) >= 0:
                mols1.append(m.clone_for_daughter(offset))
            else:
                mols2.append(m.clone_for_daughter(-offset))
            m.remove()

        if not mols1 and mols2:
            mols1.append(mols2.pop())
        if not mols2 and mols1:
            mols2.append(mols1.pop())

        daughter1 = Protocell(
            pos=self.pos + offset,
            radius=r1,
            vel=self.vel + axis * random.uniform(0.13, 0.28),
            lipids=l1,
            molecules=mols1,
            generation=self.generation + 1,
        )
        daughter2 = Protocell(
            pos=self.pos - offset,
            radius=r2,
            vel=self.vel - axis * random.uniform(0.13, 0.28),
            lipids=l2,
            molecules=mols2,
            generation=self.generation + 1,
        )
        daughter1.target_radius = r1
        daughter2.target_radius = r2
        daughter1.max_lipids_before_split = max(58, int(self.max_lipids_before_split * 1.05))
        daughter2.max_lipids_before_split = max(58, int(self.max_lipids_before_split * 1.05))

        spawn_sparks(self.pos, 30, COLORS["inherit"], speed=1.25, radius=0.045, life=1.2)
        ai_markers.append(AIMarker(self.pos, "division", color=COLORS["inherit"], life=1.5))
        split_count += 1
        self.remove()
        return [daughter1, daughter2]

# ---------------------------------------------------------------------------
# Global simulation containers
# ---------------------------------------------------------------------------

protocells = []
free_particles = []

def spawn_lipid_cloud(center=None, count=22, radius=2.2, inward_target=None):
    center = center if center is not None else rand_in_sphere(WORLD_RADIUS * 0.65)
    for _ in range(count):
        pos = center + rand_in_sphere(radius)
        if mag(pos) > WORLD_RADIUS - 0.5:
            pos = safe_norm(pos) * (WORLD_RADIUS - 0.5)
        if inward_target is not None:
            vel = safe_norm(inward_target - pos, rand_unit_vector()) * random.uniform(0.25, 0.85)
        else:
            vel = rand_unit_vector() * random.uniform(0.15, 0.7)
        free_particles.append(FreeParticle("lipid", pos, vel))

def spawn_molecule_cloud(center=None, count=14, radius=2.4, kind=None, inward_target=None):
    center = center if center is not None else rand_in_sphere(WORLD_RADIUS * 0.7)
    for _ in range(count):
        k = kind if kind is not None else ("catalyst" if random.random() < 0.22 else "nutrient")
        pos = center + rand_in_sphere(radius)
        if mag(pos) > WORLD_RADIUS - 0.5:
            pos = safe_norm(pos) * (WORLD_RADIUS - 0.5)
        if inward_target is not None:
            vel = safe_norm(inward_target - pos, rand_unit_vector()) * random.uniform(0.18, 0.65)
        else:
            vel = rand_unit_vector() * random.uniform(0.12, 0.5)
        free_particles.append(FreeParticle(k, pos, vel))

def seed_initial_world():
    protocells.clear()
    free_particles.clear()
    clear_marks()
    Protocell.next_id = 1
    FreeParticle.next_id = 1
    InternalMolecule.next_id = 1

    root = Protocell(pos=vector(-1.0, 0.1, 0.0), radius=1.12, vel=vector(0.04, 0.02, 0.0), lipids=32, generation=0)
    protocells.append(root)

    spawn_lipid_cloud(center=vector(2.4, 1.5, 0), count=38, radius=2.5, inward_target=root.pos)
    spawn_molecule_cloud(center=vector(-2.6, -1.8, 0.4), count=20, radius=2.0, inward_target=root.pos)

def hard_reset(new_round=True):
    global round_number, split_count, global_time
    for c in protocells:
        c.remove()
    for p in free_particles:
        p.remove()
    protocells.clear()
    free_particles.clear()
    clear_marks()
    if new_round:
        round_number += 1
    split_count = 0
    global_time = 0.0
    seed_initial_world()
    ai_controller.reset_brain()
    ai_markers.append(AIMarker(vector(0, 0, 0), f"round {round_number}", color=COLORS["ai"], life=1.8))

# ---------------------------------------------------------------------------
# AI Controller
# ---------------------------------------------------------------------------

class AIController:
    """
    Expressive rule-based controller.

    It reads compact simulation state, switches modes over time, performs visible
    actions, detects stagnation/completion, and starts new rounds when needed.
    """

    MODES = [
        "careful_feed",
        "curious_probe",
        "constructive_grow",
        "ritual_orbit",
        "chaotic_spill",
        "artistic_mark",
        "destructive_split",
        "reset_loop",
    ]

    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.reset_timer = 0.0
        self.state_history = deque(maxlen=150)
        self.last_progress = 0.0
        self.stagnation_time = 0.0
        self.override_message_timer = 0.0
        self.playfulness = 0.5
        self.chaos = 0.35
        self.care = 0.55
        self.curiosity = 0.6
        self.round_complete = False

    def reset_brain(self):
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.action_timer = 0.2
        self.reset_timer = 0.0
        self.state_history.clear()
        self.last_progress = 0.0
        self.stagnation_time = 0.0
        self.override_message_timer = 0.0
        self.round_complete = False

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        ai_markers.append(AIMarker(vector(0, 0, 0), f"AI: {self.mode}", color=COLORS["ai"], life=1.4))

    def read_state(self):
        largest = None
        if protocells:
            largest = max(protocells, key=lambda c: c.radius + 0.025 * c.lipids)
        total_lipids = sum(c.lipids for c in protocells)
        total_internal = sum(len(c.molecules) for c in protocells)
        free_lipids = sum(1 for p in free_particles if p.kind == "lipid")
        free_molecules = len(free_particles) - free_lipids
        ready = sum(1 for c in protocells if c.ready_to_split())
        avg_radius = sum(c.radius for c in protocells) / max(1, len(protocells))
        max_radius = max((c.radius for c in protocells), default=0.0)
        progress = len(protocells) * 4.0 + total_lipids * 0.05 + total_internal * 0.08 + split_count * 8.0 + max_radius
        state = {
            "time": global_time,
            "cells": len(protocells),
            "free_particles": len(free_particles),
            "free_lipids": free_lipids,
            "free_molecules": free_molecules,
            "total_lipids": total_lipids,
            "total_internal": total_internal,
            "ready_to_split": ready,
            "avg_radius": avg_radius,
            "max_radius": max_radius,
            "split_count": split_count,
            "largest": largest,
            "progress": progress,
        }
        return state

    def update_stagnation(self, state, dt):
        self.state_history.append(state)
        progress = state["progress"]
        if abs(progress - self.last_progress) < 0.035:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0.0, self.stagnation_time - 0.8 * dt)
        self.last_progress = progress

        empty = state["cells"] <= 0
        starved = state["free_lipids"] <= 2 and state["cells"] > 0 and state["ready_to_split"] == 0
        many_cells = state["cells"] >= 9
        complete = split_count >= 4 or many_cells
        stalled = self.stagnation_time > 10.0
        self.round_complete = empty or complete or stalled

        if empty:
            return "empty"
        if complete:
            return "complete"
        if stalled:
            return "stalled"
        if starved:
            return "starved"
        return "active"

    def choose_mode(self, state, condition):
        # Hard mode choices from state.
        if condition in ("empty", "complete", "stalled"):
            self.mode = "reset_loop"
            return
        if state["ready_to_split"] > 0:
            self.mode = "destructive_split"
            return
        if state["free_lipids"] < 6:
            self.mode = "constructive_grow"
            return
        if state["free_molecules"] < 4 and state["cells"] < 5:
            self.mode = "careful_feed"
            return

        # Timed expressive switching to avoid repeating the same thing forever.
        self.mode_timer += BASE_DT * sim_speed
        switch_after = 4.0 + random.random() * 5.0
        if self.mode_timer > switch_after:
            choices = ["careful_feed", "curious_probe", "constructive_grow", "ritual_orbit", "chaotic_spill", "artistic_mark"]
            weights = {
                "careful_feed": 1.4 if state["free_molecules"] < 12 else 0.8,
                "curious_probe": 1.2,
                "constructive_grow": 1.7 if state["free_lipids"] < 18 else 0.9,
                "ritual_orbit": 1.0 + self.playfulness,
                "chaotic_spill": 0.6 + self.chaos,
                "artistic_mark": 0.8 + self.curiosity,
            }
            total = sum(weights[c] for c in choices)
            r = random.random() * total
            acc = 0
            for c in choices:
                acc += weights[c]
                if r <= acc:
                    self.mode = c
                    break
            self.mode_timer = 0.0
            ai_markers.append(AIMarker(vector(0, 0, 0), f"AI: {self.mode}", color=COLORS["ai"], life=1.0))

    def target_cell(self):
        if not protocells:
            return None
        # Prefer large, lipid-rich cells, but occasionally inspect small daughters.
        if random.random() < 0.25:
            return min(protocells, key=lambda c: c.radius + 0.02 * len(c.molecules))
        return max(protocells, key=lambda c: c.lipids + c.radius * 18 + len(c.molecules) * 0.5)

    def nudge_cell(self, cell, toward=None, strength=0.18):
        if cell is None:
            return
        if toward is None:
            impulse = rand_unit_vector() * strength
        else:
            impulse = safe_norm(toward - cell.pos, rand_unit_vector()) * strength
        cell.vel += impulse
        cell.marked_by_ai = True
        ai_markers.append(AIMarker(cell.pos, "nudge", color=COLORS["ai"], life=0.8))

    def spill_lipids_to_cell(self, cell, count=10):
        if cell is None:
            return
        source = cell.pos + rand_unit_vector() * random.uniform(2.3, 4.8)
        spawn_lipid_cloud(center=source, count=count, radius=0.85, inward_target=cell.pos)
        ai_markers.append(AIMarker(source, "lipid spill", color=COLORS["lipid"], life=1.1))

    def spill_molecules_to_cell(self, cell, count=7):
        if cell is None:
            return
        source = cell.pos + rand_unit_vector() * random.uniform(1.8, 4.2)
        spawn_molecule_cloud(center=source, count=count, radius=0.75, inward_target=cell.pos)
        ai_markers.append(AIMarker(source, "molecule spill", color=COLORS["nutrient"], life=1.1))

    def organize_orbit(self, cell):
        if cell is None:
            return
        around = [p for p in free_particles if mag(p.pos - cell.pos) < 4.8]
        random.shuffle(around)
        around = around[:18]
        for i, p in enumerate(around):
            tangent = vector(-(p.pos - cell.pos).y, (p.pos - cell.pos).x, 0)
            tangent = safe_norm(tangent, rand_unit_vector())
            radial = safe_norm(cell.pos - p.pos, rand_unit_vector())
            p.vel += tangent * 0.12 + radial * 0.05
            p.marked = True
        ai_markers.append(AIMarker(cell.pos, "orbit organize", color=COLORS["ai"], life=1.0))

    def mark_target(self, cell, text="target"):
        if cell is None:
            return
        cell.marked_by_ai = True
        ai_markers.append(AIMarker(cell.pos, text, color=COLORS["marker"], life=1.4))
        spawn_sparks(cell.pos, 8, COLORS["marker"], speed=0.65, radius=0.035, life=0.8)

    def force_split_if_ready(self, cell):
        if cell is None:
            return
        if not cell.ready_to_split():
            cell.split_charge += 8.0
            cell.target_radius += 0.05
            cell.lipids += 4
        else:
            cell.force_split()
        ai_markers.append(AIMarker(cell.pos, "pinch", color=COLORS["membrane_divide"], life=1.0))

    def perform_mode_action(self, state, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return

        cell = self.target_cell()

        if self.mode == "careful_feed":
            self.spill_molecules_to_cell(cell, count=random.randint(5, 9))
            self.nudge_cell(cell, toward=vector(0, 0, 0), strength=0.05)
            self.action_timer = random.uniform(1.2, 2.2)

        elif self.mode == "curious_probe":
            self.mark_target(cell, "inspect")
            self.nudge_cell(cell, strength=random.uniform(0.05, 0.16))
            if random.random() < 0.35:
                self.spill_molecules_to_cell(cell, count=4)
            self.action_timer = random.uniform(1.0, 1.8)

        elif self.mode == "constructive_grow":
            self.spill_lipids_to_cell(cell, count=random.randint(8, 16))
            if random.random() < 0.45:
                self.organize_orbit(cell)
            self.action_timer = random.uniform(1.3, 2.4)

        elif self.mode == "ritual_orbit":
            self.organize_orbit(cell)
            if random.random() < 0.28:
                self.spill_lipids_to_cell(cell, count=6)
            self.action_timer = random.uniform(0.8, 1.45)

        elif self.mode == "chaotic_spill":
            center = rand_in_sphere(WORLD_RADIUS * 0.55)
            spawn_lipid_cloud(center=center, count=random.randint(8, 18), radius=random.uniform(0.6, 1.8), inward_target=(cell.pos if cell else None))
            spawn_molecule_cloud(center=center + rand_unit_vector(), count=random.randint(4, 10), radius=random.uniform(0.5, 1.4), inward_target=(cell.pos if cell else None))
            for c in protocells:
                if random.random() < 0.55:
                    self.nudge_cell(c, strength=random.uniform(0.04, 0.18))
            ai_markers.append(AIMarker(center, "chaos spill", color=COLORS["warning"], life=1.0))
            self.action_timer = random.uniform(1.5, 2.7)

        elif self.mode == "artistic_mark":
            self.mark_target(cell, "trace")
            if cell:
                for angle in [0, 1.57, 3.14, 4.71]:
                    pos = cell.pos + vector(math.cos(angle), math.sin(angle), 0) * (cell.radius + 0.4)
                    spawn_sparks(pos, 5, COLORS["marker"], speed=0.35, radius=0.025, life=1.1)
            self.action_timer = random.uniform(1.1, 1.9)

        elif self.mode == "destructive_split":
            if cell:
                self.force_split_if_ready(cell)
            self.action_timer = random.uniform(0.7, 1.2)

        elif self.mode == "reset_loop":
            self.reset_timer += dt
            if self.reset_timer > 2.0:
                hard_reset(new_round=True)
            self.action_timer = 0.25

    def update(self, dt):
        if not self.enabled:
            return
        for c in protocells:
            c.marked_by_ai = False
        for p in free_particles:
            p.marked = False

        state = self.read_state()
        condition = self.update_stagnation(state, dt)
        self.choose_mode(state, condition)
        self.perform_mode_action(state, dt)

ai_controller = AIController()

# ---------------------------------------------------------------------------
# Physics / interactions
# ---------------------------------------------------------------------------

def update_free_particles(dt):
    # Attraction of lipids to membranes and weak attraction of molecules to membrane pores.
    for p in list(free_particles):
        nearest = None
        nearest_d = 999
        for c in protocells:
            d = mag(p.pos - c.pos)
            if d < nearest_d:
                nearest = c
                nearest_d = d

        if nearest:
            direction_to_cell = safe_norm(nearest.pos - p.pos, rand_unit_vector())
            if p.kind == "lipid":
                # Lipids are amphiphilic: strong tendency toward membrane surface.
                surface_target = nearest.pos - direction_to_cell * nearest.radius
                p.vel += safe_norm(surface_target - p.pos, direction_to_cell) * (0.22 / max(0.8, nearest_d)) * dt
            else:
                # Nutrients/catalysts occasionally pass through permeable membrane.
                if nearest_d < nearest.radius + 1.15:
                    p.vel += direction_to_cell * 0.10 * dt

        p.drift(dt)

def handle_absorptions_and_imports():
    to_remove = []
    for p in free_particles:
        for c in protocells:
            d = mag(p.pos - c.pos)
            if p.kind == "lipid" and abs(d - c.radius) < 0.13:
                c.absorb_lipid(p)
                p.remove()
                to_remove.append(p)
                break
            elif p.kind != "lipid" and d < c.radius * 0.78:
                # Molecule gets trapped inside membrane bubble.
                c.import_molecule(p)
                p.remove()
                to_remove.append(p)
                break
    if to_remove:
        dead = set(to_remove)
        free_particles[:] = [p for p in free_particles if p not in dead]

def handle_cell_collisions(dt):
    for i in range(len(protocells)):
        for j in range(i + 1, len(protocells)):
            a = protocells[i]
            b = protocells[j]
            diff = b.pos - a.pos
            d = mag(diff)
            min_d = (a.radius + b.radius) * 0.78
            if d < min_d and d > 0.001:
                n = diff / d
                overlap = min_d - d
                a.pos -= n * overlap * 0.5
                b.pos += n * overlap * 0.5
                va = dot(a.vel, n)
                vb = dot(b.vel, n)
                a.vel += n * (vb - va) * 0.35
                b.vel += n * (va - vb) * 0.35
                spawn_sparks((a.pos + b.pos) * 0.5, 2, vector(0.76, 0.85, 1.0), speed=0.28, radius=0.025, life=0.4)

def update_protocells(dt):
    new_cells = []
    for c in list(protocells):
        c.drift(dt)
        if c.ready_to_split() and c.age > 3.0:
            c.split_charge += dt * 2.0
            if c.split_charge > 38 or c.radius > 2.05:
                daughters = c.split()
                new_cells.extend(daughters)

    if new_cells:
        protocells[:] = [c for c in protocells if not c.dead]
        protocells.extend(new_cells)

def control_free_particle_population():
    # Keep the scene alive without flooding it.
    lipids = sum(1 for p in free_particles if p.kind == "lipid")
    molecules = len(free_particles) - lipids
    if lipids < 4 and len(protocells) > 0:
        target = random.choice(protocells).pos
        spawn_lipid_cloud(center=rand_in_sphere(WORLD_RADIUS * 0.65), count=8, radius=1.2, inward_target=target)
    if molecules < 3 and len(protocells) > 0:
        target = random.choice(protocells).pos
        spawn_molecule_cloud(center=rand_in_sphere(WORLD_RADIUS * 0.65), count=5, radius=1.0, inward_target=target)
    if len(free_particles) > 185:
        for p in free_particles[:len(free_particles) - 185]:
            p.remove()
        del free_particles[:len(free_particles) - 185]

def update_sparks(dt):
    spark_marks[:] = [s for s in spark_marks if s.update(dt)]
    ai_markers[:] = [m for m in ai_markers if m.update(dt)]

def update_status():
    state = ai_controller.read_state()
    status_label.text = (
        f"First protocell simulation\n"
        f"Round: {round_number}   Time: {global_time:5.1f}s   Speed: {sim_speed:.2f}x\n"
        f"AI: {'ON' if ai_controller.enabled else 'OFF'}   Mode: {ai_controller.mode}\n"
        f"Cells: {state['cells']}   Splits: {split_count}   Ready: {state['ready_to_split']}\n"
        f"Free lipids: {state['free_lipids']}   Free molecules: {state['free_molecules']}\n"
        f"Internal molecules: {state['total_internal']}   Max radius: {state['max_radius']:.2f}\n"
        f"Paused: {'YES' if paused else 'NO'}   Stagnation: {ai_controller.stagnation_time:.1f}s\n"
        f"Keys: A AI | P pause | R reset | M mode | L lipids | N molecules | S split | D disturb | H help"
    )

# ---------------------------------------------------------------------------
# Human controls
# ---------------------------------------------------------------------------

def print_controls():
    print(__doc__)

def disturb_scene():
    for c in protocells:
        c.vel += rand_unit_vector() * random.uniform(0.16, 0.38)
        c.split_charge += random.uniform(0.0, 2.5)
        spawn_sparks(c.pos, 8, COLORS["ai"], speed=0.85, radius=0.035, life=0.8)
    for p in free_particles:
        if random.random() < 0.45:
            p.vel += rand_unit_vector() * random.uniform(0.15, 0.45)
    ai_markers.append(AIMarker(vector(0, 0, 0), "human disturb", color=COLORS["ai"], life=1.1))

def force_largest_split():
    if protocells:
        c = max(protocells, key=lambda x: x.radius + x.lipids * 0.02)
        c.force_split()
        ai_markers.append(AIMarker(c.pos, "human split", color=COLORS["membrane_divide"], life=1.0))

def keydown(evt):
    global paused, ai_enabled, sim_speed
    key = evt.key.lower()

    if key == "a":
        ai_controller.enabled = not ai_controller.enabled
        ai_markers.append(AIMarker(vector(0, 0, 0), f"AI {'ON' if ai_controller.enabled else 'OFF'}", color=COLORS["ai"], life=1.0))
    elif key == "p":
        paused = not paused
    elif key == "r":
        hard_reset(new_round=True)
    elif key == "m":
        ai_controller.cycle_mode()
    elif key == "l":
        target = ai_controller.target_cell()
        ai_controller.spill_lipids_to_cell(target, count=18)
    elif key == "n":
        target = ai_controller.target_cell()
        ai_controller.spill_molecules_to_cell(target, count=12)
    elif key == "s":
        force_largest_split()
    elif key == "d":
        disturb_scene()
    elif key == "c":
        clear_marks()
    elif key in ["+", "="]:
        sim_speed = min(3.0, sim_speed + 0.15)
    elif key in ["-", "_"]:
        sim_speed = max(0.25, sim_speed - 0.15)
    elif key == "h":
        print_controls()

scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

seed_initial_world()
print_controls()

while True:
    rate(60)
    if paused:
        update_status()
        continue

    dt = BASE_DT * sim_speed
    global_time += dt

    ai_controller.update(dt)
    update_free_particles(dt)
    handle_absorptions_and_imports()
    handle_cell_collisions(dt)
    update_protocells(dt)
    control_free_particle_population()
    update_sparks(dt)
    update_status()
