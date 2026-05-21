#!/usr/bin/env python3
"""
Cell Membrane Self-Assembly — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python cell_membrane_self_assembly_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    O       human override: spill new lipids + perturb the system
    B       encourage bilayer assembly
    V       encourage vesicle wrapping
    D       detach/randomize some lipid bonds
    C       clear temporary AI marks/trails
    + / =   increase AI intensity
    - / _   decrease AI intensity
    H       print controls

Scene concept:
    Lipid molecules move through a light water volume. Each lipid has a hydrophilic
    head and two hydrophobic tails. Lipids cluster, collide, attach, detach, rotate,
    organize into micelles, bilayer sheets, and vesicle-like shells. A simple
    protective cell boundary emerges as lipids wrap around a central protected region.

The file is self-contained and uses VPython primitives only.
"""

from vpython import *
from random import random, uniform, choice, sample
from math import sin, cos, pi, sqrt, atan2, acos

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Cell membrane self-assembly — lipids, micelles, bilayers, vesicles, AI controller",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
)

scene.center = vector(0, 0, 0)
scene.range = 15
scene.forward = vector(-0.55, -0.35, -0.75)
scene.up = vector(0, 1, 0)
scene.lights = []
distant_light(direction=vector(0.4, -0.7, -0.5), color=color.white)
distant_light(direction=vector(-0.6, -0.4, 0.7), color=vector(0.75, 0.82, 1.0))

# Soft colors
WATER_BLUE = vector(0.72, 0.88, 1.0)
HEAD_COLOR = vector(0.18, 0.48, 0.95)
TAIL_COLOR = vector(0.96, 0.76, 0.22)
TAIL_DARK = vector(0.82, 0.58, 0.18)
BOND_COLOR = vector(0.55, 0.68, 0.95)
VESICLE_COLOR = vector(0.60, 0.78, 1.0)
MICELLE_COLOR = vector(0.95, 0.75, 0.40)
BILAYER_COLOR = vector(0.62, 0.82, 0.64)
AI_MARK_COLOR = vector(0.88, 0.42, 0.95)
CELL_CORE_COLOR = vector(0.98, 0.86, 0.70)
TEXT_COLOR = vector(0.18, 0.22, 0.28)

BOX_LIMIT = 11.5
WATER_SIZE = vector(23.5, 17.0, 23.5)
LIPID_COUNT = 72
MAX_LIPIDS = 105
TAIL_LENGTH = 0.76
HEAD_RADIUS = 0.23
TAIL_RADIUS = 0.07
LIPID_SPEED_LIMIT = 2.0
DT = 0.018

AI_MODES = [
    "curious_scan",
    "micelle_seed",
    "bilayer_weave",
    "vesicle_wrap",
    "repair_boundary",
    "chaotic_stir",
    "careful_sort",
    "artistic_orbit",
    "destructive_detach",
    "constructive_seal",
]

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def rand_vec(scale=1.0):
    return vector(uniform(-scale, scale), uniform(-scale, scale), uniform(-scale, scale))

def random_unit():
    v = rand_vec(1.0)
    if mag(v) < 1e-6:
        return vector(1, 0, 0)
    return norm(v)

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def project_to_box(pos, margin=0.0):
    return vector(
        clamp(pos.x, -BOX_LIMIT + margin, BOX_LIMIT - margin),
        clamp(pos.y, -BOX_LIMIT * 0.72 + margin, BOX_LIMIT * 0.72 - margin),
        clamp(pos.z, -BOX_LIMIT + margin, BOX_LIMIT - margin),
    )

def distance(a, b):
    return mag(a - b)

def mix_color(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1 - t) + b * t

def angle_between(a, b):
    if mag(a) < 1e-8 or mag(b) < 1e-8:
        return 0
    return acos(clamp(dot(norm(a), norm(b)), -1, 1))

def rotate_vec_y(v, theta):
    c, s = cos(theta), sin(theta)
    return vector(v.x * c + v.z * s, v.y, -v.x * s + v.z * c)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

water_box = box(
    pos=vector(0, 0, 0),
    size=WATER_SIZE,
    color=WATER_BLUE,
    opacity=0.12,
    shininess=0.1,
)

floor_grid = []
for i in range(-10, 11, 2):
    floor_grid.append(
        curve(
            pos=[vector(i, -8.55, -11.5), vector(i, -8.55, 11.5)],
            color=vector(0.80, 0.88, 0.95),
            radius=0.012,
        )
    )
    floor_grid.append(
        curve(
            pos=[vector(-11.5, -8.55, i), vector(11.5, -8.55, i)],
            color=vector(0.80, 0.88, 0.95),
            radius=0.012,
        )
    )

cell_core = sphere(
    pos=vector(0, 0, 0),
    radius=2.0,
    color=CELL_CORE_COLOR,
    opacity=0.22,
    shininess=0.8,
)
core_label = label(
    pos=vector(0, 2.65, 0),
    text="protected interior",
    color=TEXT_COLOR,
    height=13,
    box=False,
    opacity=0,
)

vesicle_hint = sphere(
    pos=vector(0, 0, 0),
    radius=4.4,
    color=VESICLE_COLOR,
    opacity=0.055,
    shininess=0.3,
)

axis_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=4.4,
    thickness=0.018,
    color=vector(0.55, 0.72, 0.93),
    opacity=0.45,
)

bilayer_plane = box(
    pos=vector(0, -5.7, 0),
    size=vector(12.5, 0.05, 5.2),
    color=BILAYER_COLOR,
    opacity=0.12,
)

bilayer_label = label(
    pos=vector(-5.8, -5.0, -2.6),
    text="bilayer staging plane",
    color=TEXT_COLOR,
    height=12,
    box=False,
    opacity=0,
)

water_particles = []
for i in range(150):
    p = sphere(
        pos=vector(uniform(-BOX_LIMIT, BOX_LIMIT), uniform(-7.6, 7.6), uniform(-BOX_LIMIT, BOX_LIMIT)),
        radius=uniform(0.025, 0.065),
        color=vector(0.48, 0.72, 1.0),
        opacity=uniform(0.12, 0.33),
    )
    p.vel = rand_vec(0.08)
    p.phase = uniform(0, 2 * pi)
    water_particles.append(p)

# ---------------------------------------------------------------------------
# Visual status panels
# ---------------------------------------------------------------------------

title_label = label(
    pos=vector(-11.2, 8.2, 0),
    text="Cell membrane self-assembly",
    height=18,
    color=TEXT_COLOR,
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-11.2, 7.45, 0),
    text="",
    height=12,
    color=TEXT_COLOR,
    box=False,
    opacity=0,
    align="left",
)

mode_label = label(
    pos=vector(7.0, 8.2, 0),
    text="",
    height=13,
    color=TEXT_COLOR,
    box=False,
    opacity=0,
    align="left",
)

help_label = label(
    pos=vector(-11.2, -8.0, 0),
    text="A AI  P pause  R reset  M mode  O spill  B bilayer  V vesicle  D detach  +/- intensity  H controls",
    height=11,
    color=TEXT_COLOR,
    box=False,
    opacity=0,
    align="left",
)

# ---------------------------------------------------------------------------
# Lipid object
# ---------------------------------------------------------------------------

class Lipid:
    def __init__(self, idx, pos=None, mode="free"):
        self.idx = idx
        self.pos = pos if pos is not None else vector(uniform(-9.5, 9.5), uniform(-6.2, 6.2), uniform(-9.5, 9.5))
        self.vel = rand_vec(0.52)
        self.forward = random_unit()
        self.spin_axis = random_unit()
        self.angular = uniform(-1.0, 1.0)
        self.phase = uniform(0, 2 * pi)
        self.mode = mode
        self.cluster_id = -1
        self.bound_to = set()
        self.age = uniform(0, 5)
        self.energy = uniform(0.35, 1.0)
        self.mark_timer = 0
        self.attached_strength = 0.0
        self.target = None
        self.recent_collision = 0.0

        self.head = sphere(
            pos=self.pos,
            radius=HEAD_RADIUS,
            color=HEAD_COLOR,
            opacity=0.96,
            shininess=0.7,
        )
        self.tail1 = cylinder(
            pos=self.pos,
            axis=vector(0, -TAIL_LENGTH, 0),
            radius=TAIL_RADIUS,
            color=TAIL_COLOR,
            opacity=0.88,
        )
        self.tail2 = cylinder(
            pos=self.pos,
            axis=vector(0, -TAIL_LENGTH, 0),
            radius=TAIL_RADIUS,
            color=TAIL_DARK,
            opacity=0.88,
        )
        self.bridge = cylinder(
            pos=self.pos,
            axis=vector(0, -0.2, 0),
            radius=0.05,
            color=vector(0.68, 0.77, 0.92),
            opacity=0.75,
        )
        self.trail = curve(color=vector(0.45, 0.66, 0.95), radius=0.016, opacity=0.28)
        self.trail_counter = 0
        self.update_visuals()

    def tail_center(self):
        return self.pos - self.forward * (TAIL_LENGTH * 0.88)

    def hydrophobic_tip(self):
        return self.pos - self.forward * (TAIL_LENGTH * 1.35)

    def set_visible(self, visible=True):
        self.head.visible = visible
        self.tail1.visible = visible
        self.tail2.visible = visible
        self.bridge.visible = visible
        self.trail.visible = visible

    def mark(self, duration=0.7):
        self.mark_timer = max(self.mark_timer, duration)

    def apply_force(self, f, dt):
        self.vel += f * dt
        if mag(self.vel) > LIPID_SPEED_LIMIT:
            self.vel = norm(self.vel) * LIPID_SPEED_LIMIT

    def steer_to(self, target_pos, strength, dt, arrival=0.0):
        to_target = target_pos - self.pos
        d = mag(to_target)
        if d < 1e-6:
            return
        desired_speed = LIPID_SPEED_LIMIT * clamp(d / max(arrival, 0.6), 0.2, 1.0)
        desired = norm(to_target) * desired_speed
        self.vel += (desired - self.vel) * strength * dt

    def rotate_toward(self, direction, strength, dt):
        desired = safe_norm(direction, self.forward)
        self.forward = safe_norm(self.forward * (1 - strength * dt) + desired * (strength * dt), self.forward)

    def jitter(self, amount):
        self.vel += rand_vec(amount)

    def update_physics(self, dt):
        self.age += dt
        self.phase += dt * (1.0 + self.energy)

        # Brownian water movement
        self.vel += rand_vec(0.18) * dt
        self.vel *= (0.986 - 0.004 * self.attached_strength)

        # Slight float and water swirl
        self.vel.y += 0.02 * sin(self.phase * 0.7) * dt
        swirl = vector(-self.pos.z, 0, self.pos.x)
        if mag(swirl) > 0.1:
            self.vel += norm(swirl) * 0.015 * dt

        # Hydrophilic heads prefer water/outside; hydrophobic tails prefer inward clusters.
        if self.mode == "vesicle":
            radial = safe_norm(self.pos - vector(0, 0, 0), self.forward)
            shell_target = radial * 4.4
            self.steer_to(shell_target, 1.8, dt, arrival=2.3)
            self.rotate_toward(radial, 2.5, dt)
        elif self.mode == "bilayer_top":
            target = vector(clamp(self.pos.x, -5.8, 5.8), -4.95, clamp(self.pos.z, -2.3, 2.3))
            self.steer_to(target, 1.2, dt, arrival=2.6)
            self.rotate_toward(vector(0, 1, 0), 2.2, dt)
        elif self.mode == "bilayer_bottom":
            target = vector(clamp(self.pos.x, -5.8, 5.8), -6.45, clamp(self.pos.z, -2.3, 2.3))
            self.steer_to(target, 1.2, dt, arrival=2.6)
            self.rotate_toward(vector(0, -1, 0), 2.2, dt)
        elif self.mode == "micelle":
            center = self.target if self.target is not None else vector(5.7, 0.2, 3.6)
            radial = safe_norm(self.pos - center, self.forward)
            self.steer_to(center + radial * 1.45, 1.25, dt, arrival=2.1)
            self.rotate_toward(radial, 2.1, dt)
        elif self.mode == "orbit":
            center = vector(0, 0, 0)
            radial = self.pos - center
            tangent = vector(-radial.z, 0.25 * sin(self.phase), radial.x)
            if mag(radial) > 0.1 and mag(tangent) > 0.1:
                self.vel += norm(tangent) * 0.32 * dt
                self.steer_to(center + safe_norm(radial) * 6.5, 0.45, dt, arrival=3.0)
                self.rotate_toward(safe_norm(radial), 1.4, dt)

        self.pos += self.vel * dt

        # Bounce / wrap inside water container
        if abs(self.pos.x) > BOX_LIMIT:
            self.pos.x = clamp(self.pos.x, -BOX_LIMIT, BOX_LIMIT)
            self.vel.x *= -0.75
            self.recent_collision = 0.3
        if abs(self.pos.y) > BOX_LIMIT * 0.72:
            self.pos.y = clamp(self.pos.y, -BOX_LIMIT * 0.72, BOX_LIMIT * 0.72)
            self.vel.y *= -0.75
            self.recent_collision = 0.3
        if abs(self.pos.z) > BOX_LIMIT:
            self.pos.z = clamp(self.pos.z, -BOX_LIMIT, BOX_LIMIT)
            self.vel.z *= -0.75
            self.recent_collision = 0.3

        # Orientation drift
        self.forward = safe_norm(self.forward + cross(self.spin_axis, self.forward) * self.angular * dt * 0.12 + rand_vec(0.025) * dt)
        self.angular *= 0.995
        self.recent_collision = max(0, self.recent_collision - dt)
        self.mark_timer = max(0, self.mark_timer - dt)

    def update_visuals(self):
        f = safe_norm(self.forward, vector(0, 1, 0))
        side = safe_norm(cross(f, vector(0, 1, 0)), vector(1, 0, 0))
        if mag(side) < 0.1:
            side = vector(1, 0, 0)
        fork_base = self.pos - f * 0.28
        tail1_dir = safe_norm(-f * TAIL_LENGTH + side * 0.18)
        tail2_dir = safe_norm(-f * TAIL_LENGTH - side * 0.18)

        self.head.pos = self.pos
        self.bridge.pos = self.pos - f * 0.08
        self.bridge.axis = -f * 0.35

        self.tail1.pos = fork_base
        self.tail1.axis = tail1_dir * TAIL_LENGTH
        self.tail2.pos = fork_base
        self.tail2.axis = tail2_dir * TAIL_LENGTH

        if self.mark_timer > 0:
            self.head.color = mix_color(HEAD_COLOR, AI_MARK_COLOR, 0.65)
            self.tail1.color = mix_color(TAIL_COLOR, AI_MARK_COLOR, 0.45)
            self.tail2.color = mix_color(TAIL_DARK, AI_MARK_COLOR, 0.45)
            self.head.radius = HEAD_RADIUS * 1.15
        elif self.recent_collision > 0:
            self.head.color = vector(0.95, 0.52, 0.42)
            self.tail1.color = vector(1.0, 0.84, 0.25)
            self.tail2.color = vector(0.92, 0.68, 0.25)
            self.head.radius = HEAD_RADIUS
        else:
            if self.mode.startswith("bilayer"):
                tint = 0.42
                self.head.color = mix_color(HEAD_COLOR, BILAYER_COLOR, tint)
            elif self.mode == "vesicle":
                self.head.color = mix_color(HEAD_COLOR, VESICLE_COLOR, 0.35)
            elif self.mode == "micelle":
                self.head.color = mix_color(HEAD_COLOR, MICELLE_COLOR, 0.28)
            elif self.mode == "orbit":
                self.head.color = mix_color(HEAD_COLOR, AI_MARK_COLOR, 0.25)
            else:
                self.head.color = HEAD_COLOR
            self.tail1.color = TAIL_COLOR
            self.tail2.color = TAIL_DARK
            self.head.radius = HEAD_RADIUS

        self.trail_counter += 1
        if self.trail_counter % 8 == 0:
            self.trail.append(pos=self.pos)
            if self.trail.npoints > 32:
                self.trail.pop(0)

# ---------------------------------------------------------------------------
# Bonds, clusters, marks
# ---------------------------------------------------------------------------

lipids = []
bond_visuals = {}
ai_marks = []
micelle_centers = [
    vector(5.6, 0.2, 3.8),
    vector(-6.0, 1.1, 3.4),
    vector(4.9, 2.4, -4.9),
]

for mpos in micelle_centers:
    sphere(pos=mpos, radius=0.12, color=MICELLE_COLOR, opacity=0.42)

def bond_key(i, j):
    return tuple(sorted((i, j)))

def create_lipids(n=LIPID_COUNT, arrangement="mixed"):
    global lipids
    lipids = []
    for i in range(n):
        if arrangement == "seeded":
            if i < n * 0.34:
                center = choice(micelle_centers)
                pos = center + random_unit() * uniform(1.3, 4.0)
            elif i < n * 0.68:
                pos = vector(uniform(-5.8, 5.8), uniform(-6.7, -4.8), uniform(-2.6, 2.6))
            else:
                pos = random_unit() * uniform(3.6, 7.2)
        else:
            pos = vector(uniform(-9.5, 9.5), uniform(-6.4, 6.4), uniform(-9.5, 9.5))
        lipids.append(Lipid(i, pos))

def clear_bonds():
    global bond_visuals
    for c in bond_visuals.values():
        c.visible = False
    bond_visuals = {}
    for l in lipids:
        l.bound_to.clear()
        l.attached_strength = 0.0

def clear_marks():
    global ai_marks
    for obj in ai_marks:
        obj.visible = False
    ai_marks = []
    for l in lipids:
        l.mark_timer = 0
        l.trail.clear()

def attach_lipids(a, b, strength=1.0):
    if a.idx == b.idx:
        return
    k = bond_key(a.idx, b.idx)
    a.bound_to.add(b.idx)
    b.bound_to.add(a.idx)
    a.attached_strength = clamp(a.attached_strength + 0.08 * strength, 0, 1)
    b.attached_strength = clamp(b.attached_strength + 0.08 * strength, 0, 1)
    if k not in bond_visuals:
        bond_visuals[k] = curve(pos=[a.tail_center(), b.tail_center()], color=BOND_COLOR, radius=0.023, opacity=0.38)
    else:
        bond_visuals[k].visible = True

def detach_lipids(a, b):
    k = bond_key(a.idx, b.idx)
    a.bound_to.discard(b.idx)
    b.bound_to.discard(a.idx)
    a.attached_strength = max(0, a.attached_strength - 0.18)
    b.attached_strength = max(0, b.attached_strength - 0.18)
    if k in bond_visuals:
        bond_visuals[k].visible = False
        del bond_visuals[k]

def update_bond_visuals():
    stale = []
    for k, c in bond_visuals.items():
        i, j = k
        if i >= len(lipids) or j >= len(lipids):
            stale.append(k)
            continue
        a, b = lipids[i], lipids[j]
        if j not in a.bound_to or i not in b.bound_to:
            stale.append(k)
            continue
        c.modify(0, pos=a.tail_center())
        c.modify(1, pos=b.tail_center())
        d = distance(a.pos, b.pos)
        c.opacity = clamp(0.58 - d * 0.06, 0.08, 0.45)
    for k in stale:
        if k in bond_visuals:
            bond_visuals[k].visible = False
            del bond_visuals[k]

def add_ai_mark(pos, radius=0.25, lifetime=2.0, color_value=AI_MARK_COLOR):
    s = sphere(pos=pos, radius=radius, color=color_value, opacity=0.35, shininess=0.6)
    s.life = lifetime
    s.max_life = lifetime
    ai_marks.append(s)
    return s

def update_ai_marks(dt):
    remaining = []
    for obj in ai_marks:
        obj.life -= dt
        if obj.life <= 0:
            obj.visible = False
        else:
            obj.opacity = 0.35 * clamp(obj.life / obj.max_life, 0, 1)
            obj.radius *= 1.003
            remaining.append(obj)
    ai_marks[:] = remaining

# ---------------------------------------------------------------------------
# Lipid interactions
# ---------------------------------------------------------------------------

def interaction_step(dt):
    # Pairwise hydrophobic attraction, head repulsion, collision, attachment, detachment.
    n = len(lipids)
    for i in range(n):
        a = lipids[i]
        for j in range(i + 1, n):
            b = lipids[j]
            delta = b.pos - a.pos
            d = mag(delta)
            if d < 1e-6 or d > 2.9:
                continue
            u = delta / d

            tail_d = distance(a.hydrophobic_tip(), b.hydrophobic_tip())
            head_d = distance(a.pos, b.pos)
            facing = dot(a.forward, b.forward)

            if d < 0.48:
                push = u * (0.48 - d) * 4.2
                a.apply_force(-push, dt)
                b.apply_force(push, dt)
                a.recent_collision = b.recent_collision = 0.18

            if tail_d < 1.08:
                # Hydrophobic tails cluster together.
                pull = u * (1.08 - tail_d) * 1.9
                a.apply_force(pull, dt)
                b.apply_force(-pull, dt)

                # Lipids prefer aligned or paired orientations depending on structure.
                if a.mode.startswith("bilayer") and b.mode.startswith("bilayer") and a.mode != b.mode:
                    a.rotate_toward(-b.forward, 0.55, dt)
                    b.rotate_toward(-a.forward, 0.55, dt)
                else:
                    a.rotate_toward(a.forward + b.forward, 0.25, dt)
                    b.rotate_toward(a.forward + b.forward, 0.25, dt)

                if tail_d < 0.82 and random() < 0.012:
                    attach_lipids(a, b, 1.0)

            if head_d < 0.70:
                # Heads are hydrated and resist occupying the same point.
                a.apply_force(-u * 1.5, dt)
                b.apply_force(u * 1.5, dt)

            if j in a.bound_to:
                target_d = 0.95 if (a.mode == "vesicle" or b.mode == "vesicle") else 0.78
                spring = (d - target_d) * 1.35
                a.apply_force(u * spring, dt)
                b.apply_force(-u * spring, dt)

                # Occasional thermal detach, more likely in chaotic states.
                detach_chance = 0.0008
                if a.mode == "free" or b.mode == "free":
                    detach_chance += 0.001
                if d > 1.85 or random() < detach_chance:
                    detach_lipids(a, b)

def update_clusters():
    # Connected components using current bonds.
    for l in lipids:
        l.cluster_id = -1
    cid = 0
    for l in lipids:
        if l.cluster_id != -1:
            continue
        stack = [l.idx]
        l.cluster_id = cid
        while stack:
            i = stack.pop()
            for j in lipids[i].bound_to:
                if 0 <= j < len(lipids) and lipids[j].cluster_id == -1:
                    lipids[j].cluster_id = cid
                    stack.append(j)
        cid += 1

def cluster_stats():
    groups = {}
    for l in lipids:
        groups.setdefault(l.cluster_id, []).append(l)
    sizes = sorted([len(v) for v in groups.values()], reverse=True)
    largest = sizes[0] if sizes else 0
    avg_bonds = sum(len(l.bound_to) for l in lipids) / max(1, len(lipids))
    vesicle_count = sum(1 for l in lipids if l.mode == "vesicle")
    bilayer_count = sum(1 for l in lipids if l.mode.startswith("bilayer"))
    micelle_count = sum(1 for l in lipids if l.mode == "micelle")
    free_count = sum(1 for l in lipids if l.mode == "free")
    speed_avg = sum(mag(l.vel) for l in lipids) / max(1, len(lipids))
    shell_error = 0.0
    shell_members = 0
    for l in lipids:
        if l.mode == "vesicle":
            shell_error += abs(mag(l.pos) - 4.4)
            shell_members += 1
    shell_error = shell_error / max(1, shell_members)
    return {
        "clusters": len(groups),
        "largest_cluster": largest,
        "avg_bonds": avg_bonds,
        "vesicle_count": vesicle_count,
        "bilayer_count": bilayer_count,
        "micelle_count": micelle_count,
        "free_count": free_count,
        "speed_avg": speed_avg,
        "shell_error": shell_error,
        "total": len(lipids),
    }

# ---------------------------------------------------------------------------
# Assembly pattern helpers
# ---------------------------------------------------------------------------

def assign_micelle(target_fraction=0.32):
    count = int(len(lipids) * target_fraction)
    candidates = sorted(lipids, key=lambda l: min(distance(l.pos, c) for c in micelle_centers))
    for l in candidates[:count]:
        center = min(micelle_centers, key=lambda c: distance(l.pos, c))
        l.mode = "micelle"
        l.target = center
        l.mark(0.5)

def assign_bilayer(target_fraction=0.48):
    count = int(len(lipids) * target_fraction)
    chosen = sorted(lipids, key=lambda l: distance(l.pos, vector(0, -5.7, 0)))[:count]
    chosen = sorted(chosen, key=lambda l: l.pos.x)
    for idx, l in enumerate(chosen):
        l.mode = "bilayer_top" if idx % 2 == 0 else "bilayer_bottom"
        row = idx // 2
        x = -5.8 + (row % 12) * 1.05
        z = -2.1 + ((row // 12) % 5) * 1.0
        y = -4.95 if l.mode == "bilayer_top" else -6.45
        l.target = vector(x, y, z)
        l.mark(0.5)

def assign_vesicle(target_fraction=0.62):
    count = int(len(lipids) * target_fraction)
    chosen = sorted(lipids, key=lambda l: abs(mag(l.pos) - 4.4))[:count]
    golden = pi * (3 - sqrt(5))
    for idx, l in enumerate(chosen):
        y = 1 - (idx / max(1, count - 1)) * 2
        r = sqrt(max(0, 1 - y * y))
        theta = idx * golden
        pos = vector(cos(theta) * r, y, sin(theta) * r) * 4.4
        l.mode = "vesicle"
        l.target = pos
        l.mark(0.65)

def assign_orbit(target_fraction=0.35):
    count = int(len(lipids) * target_fraction)
    chosen = sample(lipids, min(count, len(lipids)))
    for l in chosen:
        l.mode = "orbit"
        l.target = None
        l.mark(0.55)

def free_some_lipids(fraction=0.20, impulse=0.55):
    count = int(len(lipids) * fraction)
    if count <= 0:
        return
    chosen = sample(lipids, min(count, len(lipids)))
    for l in chosen:
        for j in list(l.bound_to):
            if 0 <= j < len(lipids):
                detach_lipids(l, lipids[j])
        l.mode = "free"
        l.target = None
        l.vel += random_unit() * impulse
        l.mark(0.7)

def spill_lipids(n=12):
    start = len(lipids)
    for i in range(n):
        if len(lipids) >= MAX_LIPIDS:
            break
        side = choice(["x+", "x-", "z+", "z-", "top"])
        if side == "x+":
            pos = vector(BOX_LIMIT - 0.3, uniform(-6, 6), uniform(-9, 9))
            vel = vector(-1.0, uniform(-0.2, 0.2), uniform(-0.2, 0.2))
        elif side == "x-":
            pos = vector(-BOX_LIMIT + 0.3, uniform(-6, 6), uniform(-9, 9))
            vel = vector(1.0, uniform(-0.2, 0.2), uniform(-0.2, 0.2))
        elif side == "z+":
            pos = vector(uniform(-9, 9), uniform(-6, 6), BOX_LIMIT - 0.3)
            vel = vector(uniform(-0.2, 0.2), uniform(-0.2, 0.2), -1.0)
        elif side == "z-":
            pos = vector(uniform(-9, 9), uniform(-6, 6), -BOX_LIMIT + 0.3)
            vel = vector(uniform(-0.2, 0.2), uniform(-0.2, 0.2), 1.0)
        else:
            pos = vector(uniform(-8, 8), 7.6, uniform(-8, 8))
            vel = vector(uniform(-0.2, 0.2), -1.0, uniform(-0.2, 0.2))
        new_lipid = Lipid(start + i, pos)
        new_lipid.vel = vel
        new_lipid.mark(1.0)
        lipids.append(new_lipid)
        add_ai_mark(pos, radius=0.18, lifetime=1.2, color_value=vector(0.35, 0.72, 1.0))

def set_all_free():
    for l in lipids:
        l.mode = "free"
        l.target = None

def remove_extra_lipids(target=LIPID_COUNT):
    while len(lipids) > target:
        l = lipids.pop()
        for j in list(l.bound_to):
            if 0 <= j < len(lipids):
                lipids[j].bound_to.discard(l.idx)
        l.set_visible(False)

# ---------------------------------------------------------------------------
# AI controller
# ---------------------------------------------------------------------------

class MembraneAI:
    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = AI_MODES[self.mode_index]
        self.timer = 0
        self.mode_duration = 7.5
        self.intensity = 1.0
        self.paused = False
        self.round_id = 1
        self.completed = False
        self.completion_timer = 0
        self.stagnation_timer = 0
        self.prev_metric = None
        self.last_action = ""
        self.loop_delay = 0
        self.personality = "constructive"
        self.scan_angle = 0
        self.ritual_phase = 0
        self.human_override_timer = 0

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(AI_MODES)
        self.mode = AI_MODES[self.mode_index]
        self.timer = 0
        self.last_action = "manual mode cycle"
        self.flash_mode_marker()

    def set_mode(self, mode_name):
        if mode_name in AI_MODES:
            self.mode_index = AI_MODES.index(mode_name)
            self.mode = mode_name
            self.timer = 0
            self.flash_mode_marker()

    def flash_mode_marker(self):
        radius = {
            "curious_scan": 5.8,
            "micelle_seed": 1.8,
            "bilayer_weave": 3.0,
            "vesicle_wrap": 4.4,
            "repair_boundary": 4.4,
            "chaotic_stir": 7.0,
            "careful_sort": 5.2,
            "artistic_orbit": 6.4,
            "destructive_detach": 3.5,
            "constructive_seal": 4.25,
        }.get(self.mode, 4.5)
        add_ai_mark(vector(radius * 0.55, 0.2, radius * 0.15), radius=0.35, lifetime=1.2)

    def read_state(self):
        stats = cluster_stats()
        stats["time_in_mode"] = self.timer
        stats["round_id"] = self.round_id
        stats["ai_mode"] = self.mode
        stats["lipid_count"] = len(lipids)
        stats["boundary_score"] = self.boundary_score()
        stats["bilayer_score"] = stats["bilayer_count"] / max(1, stats["total"])
        stats["micelle_score"] = stats["micelle_count"] / max(1, stats["total"])
        return stats

    def boundary_score(self):
        if not lipids:
            return 0
        shell_members = [l for l in lipids if 3.55 <= mag(l.pos) <= 5.35 and dot(safe_norm(l.pos), l.forward) > 0.35]
        return len(shell_members) / max(1, len(lipids))

    def detect_stagnation_or_completion(self, state, dt):
        metric = (
            state["largest_cluster"] * 0.030
            + state["avg_bonds"] * 0.38
            + state["boundary_score"] * 1.8
            + state["bilayer_score"] * 0.65
            + state["micelle_score"] * 0.45
        )

        if self.prev_metric is not None and abs(metric - self.prev_metric) < 0.006 and state["speed_avg"] < 0.16:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 1.4)

        self.prev_metric = metric

        complete = (
            state["boundary_score"] > 0.48
            and state["avg_bonds"] > 1.15
            and state["vesicle_count"] > state["total"] * 0.48
        )

        bilayer_complete = (
            state["bilayer_score"] > 0.42
            and state["avg_bonds"] > 0.95
            and state["speed_avg"] < 0.24
        )

        micelle_complete = (
            state["micelle_score"] > 0.28
            and state["largest_cluster"] > 12
            and state["avg_bonds"] > 0.85
        )

        if complete or bilayer_complete or micelle_complete:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0, self.completion_timer - dt)

        self.completed = self.completion_timer > 4.5
        return self.stagnation_timer > 7.0 or self.completed or len(lipids) < 18

    def choose_next_mode(self, state):
        # State-reactive transitions, not just a fixed loop.
        if state["lipid_count"] < 55:
            return "constructive_seal"
        if self.stagnation_timer > 5.5:
            return choice(["chaotic_stir", "destructive_detach", "artistic_orbit"])
        if state["avg_bonds"] < 0.45:
            return choice(["micelle_seed", "careful_sort"])
        if state["bilayer_score"] < 0.25 and random() < 0.45:
            return "bilayer_weave"
        if state["boundary_score"] < 0.38 and random() < 0.55:
            return "vesicle_wrap"
        if state["boundary_score"] > 0.40 and state["avg_bonds"] < 1.3:
            return "repair_boundary"
        return choice(AI_MODES)

    def apply_action(self, action, state, dt):
        self.last_action = action

        if action == "scan":
            self.scan_angle += dt * (0.9 + 0.3 * self.intensity)
            p = vector(6.2 * cos(self.scan_angle), 1.7 * sin(self.scan_angle * 0.6), 6.2 * sin(self.scan_angle))
            add_ai_mark(p, radius=0.10, lifetime=0.55, color_value=AI_MARK_COLOR)
            for l in lipids:
                if random() < 0.012:
                    l.mark(0.25)
                if distance(l.pos, p) < 3.0:
                    l.vel += safe_norm(p - l.pos) * 0.08 * self.intensity

        elif action == "seed_micelle":
            assign_micelle(0.22 + 0.16 * random())
            for c in micelle_centers:
                add_ai_mark(c, radius=0.35, lifetime=1.1, color_value=MICELLE_COLOR)

        elif action == "weave_bilayer":
            assign_bilayer(0.36 + 0.18 * random())
            add_ai_mark(vector(0, -5.7, 0), radius=0.5, lifetime=1.4, color_value=BILAYER_COLOR)

        elif action == "wrap_vesicle":
            assign_vesicle(0.46 + 0.20 * random())
            add_ai_mark(vector(0, 0, 0), radius=0.65, lifetime=1.5, color_value=VESICLE_COLOR)

        elif action == "repair":
            # Pull near-shell lipids into gaps and point heads outward.
            for l in lipids:
                r = mag(l.pos)
                if 3.0 < r < 5.9:
                    l.mode = "vesicle"
                    l.rotate_toward(safe_norm(l.pos), 3.0, dt)
                    l.steer_to(safe_norm(l.pos) * 4.4, 2.0 * self.intensity, dt, arrival=1.4)
                    if random() < 0.05:
                        l.mark(0.35)
            add_ai_mark(random_unit() * 4.4, radius=0.25, lifetime=0.9, color_value=VESICLE_COLOR)

        elif action == "stir":
            center = vector(0, 0, 0)
            for l in lipids:
                radial = l.pos - center
                tangent = vector(-radial.z, uniform(-0.35, 0.35), radial.x)
                if mag(tangent) > 0.1:
                    l.vel += norm(tangent) * uniform(0.02, 0.13) * self.intensity
                if random() < 0.08:
                    l.mark(0.25)
            add_ai_mark(rand_vec(4.5), radius=0.35, lifetime=0.9, color_value=vector(1.0, 0.55, 0.38))

        elif action == "sort":
            # Free lipids are nudged toward nearest useful pattern.
            for l in lipids:
                if l.mode == "free":
                    if l.pos.y < -3.3:
                        l.mode = "bilayer_top" if random() < 0.5 else "bilayer_bottom"
                    elif mag(l.pos) < 6.2:
                        l.mode = "vesicle"
                    else:
                        l.mode = "micelle"
                        l.target = min(micelle_centers, key=lambda c: distance(l.pos, c))
                    l.mark(0.4)
            add_ai_mark(vector(-4.7, 2.3, -3.8), radius=0.28, lifetime=1.0, color_value=vector(0.65, 0.92, 0.62))

        elif action == "orbit":
            assign_orbit(0.28 + 0.12 * random())
            theta = uniform(0, 2 * pi)
            add_ai_mark(vector(6.5 * cos(theta), 0.3, 6.5 * sin(theta)), radius=0.30, lifetime=1.2, color_value=AI_MARK_COLOR)

        elif action == "detach":
            free_some_lipids(0.10 + 0.08 * random(), impulse=0.7 * self.intensity)
            add_ai_mark(rand_vec(3.8), radius=0.42, lifetime=1.0, color_value=vector(1.0, 0.45, 0.35))

        elif action == "seal":
            if len(lipids) < LIPID_COUNT:
                spill_lipids(LIPID_COUNT - len(lipids))
            else:
                spill_lipids(5)
            assign_vesicle(0.55)
            add_ai_mark(vector(0, 0, 0), radius=0.52, lifetime=1.3, color_value=vector(0.40, 0.86, 0.75))

    def update(self, dt):
        if not self.enabled or self.paused:
            return

        self.timer += dt
        state = self.read_state()

        reset_needed = self.detect_stagnation_or_completion(state, dt)
        if reset_needed:
            self.loop_delay += dt
            if self.loop_delay > 2.6:
                reset_round(seed_mode="seeded")
                self.loop_delay = 0
                self.round_id += 1
                self.completion_timer = 0
                self.stagnation_timer = 0
                self.prev_metric = None
                self.set_mode(choice(["curious_scan", "micelle_seed", "bilayer_weave", "vesicle_wrap"]))
                self.last_action = "loop reset"
            return
        else:
            self.loop_delay = 0

        if self.timer > self.mode_duration:
            new_mode = self.choose_next_mode(state)
            self.set_mode(new_mode)
            self.mode_duration = uniform(5.5, 10.5)

        # Mode-specific action rhythm.
        chance = clamp(0.018 * self.intensity, 0.005, 0.065)

        if self.mode == "curious_scan":
            self.apply_action("scan", state, dt)
            if random() < chance * 0.20:
                self.apply_action(choice(["sort", "seed_micelle"]), state, dt)

        elif self.mode == "micelle_seed":
            if random() < chance:
                self.apply_action("seed_micelle", state, dt)
            if random() < chance * 0.25:
                self.apply_action("scan", state, dt)

        elif self.mode == "bilayer_weave":
            if random() < chance:
                self.apply_action("weave_bilayer", state, dt)
            if random() < chance * 0.15:
                self.apply_action("repair", state, dt)

        elif self.mode == "vesicle_wrap":
            if random() < chance:
                self.apply_action("wrap_vesicle", state, dt)
            if random() < chance * 0.25:
                self.apply_action("repair", state, dt)

        elif self.mode == "repair_boundary":
            self.apply_action("repair", state, dt)

        elif self.mode == "chaotic_stir":
            self.apply_action("stir", state, dt)
            if random() < chance * 0.18:
                self.apply_action("detach", state, dt)

        elif self.mode == "careful_sort":
            if random() < chance * 0.75:
                self.apply_action("sort", state, dt)
            self.apply_action("scan", state, dt)

        elif self.mode == "artistic_orbit":
            if random() < chance * 0.55:
                self.apply_action("orbit", state, dt)
            self.apply_action("scan", state, dt)

        elif self.mode == "destructive_detach":
            if random() < chance:
                self.apply_action("detach", state, dt)
            if random() < chance * 0.45:
                self.apply_action("stir", state, dt)

        elif self.mode == "constructive_seal":
            if random() < chance:
                self.apply_action("seal", state, dt)
            self.apply_action("repair", state, dt)

# ---------------------------------------------------------------------------
# Reset and keyboard control
# ---------------------------------------------------------------------------

ai = MembraneAI()
running = True

def reset_round(seed_mode="mixed"):
    global bond_visuals
    clear_marks()
    clear_bonds()
    for l in lipids:
        l.set_visible(False)
    lipids[:] = []
    create_lipids(LIPID_COUNT, arrangement=seed_mode)
    bond_visuals = {}
    ai.completed = False
    ai.completion_timer = 0
    ai.stagnation_timer = 0
    ai.prev_metric = None
    ai.timer = 0
    ai.last_action = "reset"
    if seed_mode == "seeded":
        assign_micelle(0.18)
        assign_bilayer(0.22)
    add_ai_mark(vector(0, 0, 0), radius=0.65, lifetime=1.4, color_value=vector(0.38, 0.78, 0.95))

def print_controls():
    print(__doc__)

def keydown(evt):
    global running
    k = evt.key.lower()
    if k == "a":
        ai.enabled = not ai.enabled
        ai.last_action = "AI on" if ai.enabled else "AI off"
    elif k == "p":
        running = not running
        ai.paused = not running
    elif k == "r":
        reset_round(seed_mode="mixed")
    elif k == "m":
        ai.cycle_mode()
    elif k == "o":
        spill_lipids(12)
        free_some_lipids(0.12, impulse=1.1)
        ai.human_override_timer = 2.0
        ai.last_action = "human spill override"
    elif k == "b":
        assign_bilayer(0.58)
        ai.set_mode("bilayer_weave")
        ai.human_override_timer = 2.0
    elif k == "v":
        assign_vesicle(0.68)
        ai.set_mode("vesicle_wrap")
        ai.human_override_timer = 2.0
    elif k == "d":
        free_some_lipids(0.22, impulse=0.9)
        ai.set_mode("destructive_detach")
        ai.human_override_timer = 2.0
    elif k == "c":
        clear_marks()
    elif k in ["+", "="]:
        ai.intensity = clamp(ai.intensity + 0.15, 0.2, 3.0)
    elif k in ["-", "_"]:
        ai.intensity = clamp(ai.intensity - 0.15, 0.2, 3.0)
    elif k == "h":
        print_controls()

scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Main animation update
# ---------------------------------------------------------------------------

def update_water(dt, t):
    for i, p in enumerate(water_particles):
        p.phase += dt * uniform(0.4, 1.1)
        p.pos += p.vel * dt + vector(0, 0.008 * sin(t * 0.5 + p.phase), 0)
        if p.pos.x > BOX_LIMIT or p.pos.x < -BOX_LIMIT:
            p.vel.x *= -1
        if p.pos.y > 7.9 or p.pos.y < -7.9:
            p.vel.y *= -1
        if p.pos.z > BOX_LIMIT or p.pos.z < -BOX_LIMIT:
            p.vel.z *= -1
        p.pos = vector(clamp(p.pos.x, -BOX_LIMIT, BOX_LIMIT), clamp(p.pos.y, -7.9, 7.9), clamp(p.pos.z, -BOX_LIMIT, BOX_LIMIT))

def update_environment(dt, t):
    cell_core.radius = 2.0 + 0.05 * sin(t * 1.3)
    vesicle_hint.opacity = 0.045 + 0.025 * (0.5 + 0.5 * sin(t * 0.8))
    axis_ring.rotate(angle=dt * 0.10, axis=vector(0, 1, 0), origin=vector(0, 0, 0))
    bilayer_plane.opacity = 0.10 + 0.03 * (0.5 + 0.5 * sin(t * 0.7))

def update_status(t):
    state = ai.read_state()
    status_label.text = (
        f"lipids {state['total']} | clusters {state['clusters']} | largest {state['largest_cluster']} | "
        f"avg bonds {state['avg_bonds']:.2f}\n"
        f"vesicle {state['vesicle_count']} | bilayer {state['bilayer_count']} | micelle {state['micelle_count']} | "
        f"boundary {state['boundary_score']:.2f} | speed {state['speed_avg']:.2f}"
    )
    mode_label.text = (
        f"AI {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode}\n"
        f"intensity {ai.intensity:.2f} | round {ai.round_id} | action: {ai.last_action}\n"
        f"stagnation {ai.stagnation_timer:.1f}s | completion {ai.completion_timer:.1f}s"
    )

def simulation_step(dt, t):
    update_water(dt, t)
    update_environment(dt, t)

    if running:
        if ai.human_override_timer > 0:
            ai.human_override_timer -= dt

        ai.update(dt)

        for l in lipids:
            l.update_physics(dt)

        interaction_step(dt)
        update_clusters()

        for l in lipids:
            l.update_visuals()

        update_bond_visuals()
        update_ai_marks(dt)

    update_status(t)

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

create_lipids(LIPID_COUNT, arrangement="seeded")
assign_micelle(0.16)
assign_bilayer(0.18)
print_controls()

t = 0.0
while True:
    rate(60)
    t += DT
    simulation_step(DT, t)
