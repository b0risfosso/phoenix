#!/usr/bin/env python3
"""
Origin of Life Chemical Soup — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python origin_of_life_chemical_soup_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    O       human override: energy pulse + molecule spill
    C       clear trails/marks
    B       force a lipid bubble event
    S       force a self-copying molecule seed
    + / =   increase simulation speed
    - / _   decrease simulation speed
    H       print controls

Scene concept:
    A warm shallow-water chemical soup contains simple molecules drifting in a transparent
    chamber. Molecules collide, bond, detach, cluster, form amino acids, nucleotides,
    lipid bubbles, and early self-copying chain molecules. An AI controller reads the
    scene state, chooses actions, switches behavior modes, avoids stagnation, resets
    completed or halted rounds, and creates visible changes in the environment.

This file is self-contained and uses VPython primitives only.
"""

from vpython import *
import random
import math
import time

# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="Origin of Life Chemical Soup — AI Controlled 3D VPython Simulation",
    width=1280,
    height=780,
    background=vector(0.92, 0.97, 1.0),
    center=vector(0, 0, 0),
)

scene.camera.pos = vector(0, 8.2, 15.0)
scene.camera.axis = vector(0, -5.0, -15.0)
scene.forward = vector(0, -0.32, -1)

random.seed()

WORLD_HALF = vector(6.2, 3.2, 4.4)
GROUND_Y = -WORLD_HALF.y
MAX_MOLECULES = 120
MAX_PRODUCTS = 50
MAX_MARKS = 160
MAX_TRAILS = 90

paused = False
ai_enabled = True
show_labels = True
sim_speed = 1.0
round_index = 1

# -----------------------------
# Colors and molecule definitions
# -----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def randf(a, b):
    return random.uniform(a, b)

def random_vec(scale=1.0):
    return vector(randf(-scale, scale), randf(-scale, scale), randf(-scale, scale))

def mag2(v):
    return v.x * v.x + v.y * v.y + v.z * v.z

def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(1, 0, 0)
    return v / m

def mix_color(c1, c2, amount):
    return c1 * (1 - amount) + c2 * amount

COLORS = {
    "H2O": vector(0.70, 0.92, 1.00),
    "CH4": vector(0.58, 0.76, 0.58),
    "NH3": vector(0.78, 0.72, 0.95),
    "CO2": vector(0.68, 0.68, 0.68),
    "HCN": vector(0.82, 0.78, 0.50),
    "H2S": vector(0.84, 0.78, 0.40),
    "PO4": vector(1.00, 0.67, 0.32),
    "SUGAR": vector(1.00, 0.76, 0.86),
    "BASE": vector(0.65, 0.82, 1.00),
    "LIPID": vector(0.95, 0.82, 0.38),
    "AMINO": vector(0.64, 0.95, 0.68),
    "NUCLEOTIDE": vector(0.72, 0.72, 1.00),
    "CHAIN": vector(1.00, 0.54, 0.70),
    "CATALYST": vector(1.00, 0.93, 0.45),
    "WASTE": vector(0.70, 0.70, 0.76),
}

RADII = {
    "H2O": 0.12,
    "CH4": 0.18,
    "NH3": 0.16,
    "CO2": 0.17,
    "HCN": 0.15,
    "H2S": 0.18,
    "PO4": 0.20,
    "SUGAR": 0.20,
    "BASE": 0.18,
    "LIPID": 0.19,
    "AMINO": 0.22,
    "NUCLEOTIDE": 0.23,
    "CHAIN": 0.24,
    "CATALYST": 0.23,
    "WASTE": 0.14,
}

FORMABLE = ["AMINO", "NUCLEOTIDE", "CHAIN"]

RECIPE_PAIRS = {
    tuple(sorted(("CH4", "NH3"))): ("AMINO", 0.43),
    tuple(sorted(("HCN", "NH3"))): ("AMINO", 0.36),
    tuple(sorted(("CO2", "NH3"))): ("AMINO", 0.30),
    tuple(sorted(("BASE", "SUGAR"))): ("NUCLEOTIDE", 0.36),
    tuple(sorted(("PO4", "SUGAR"))): ("NUCLEOTIDE", 0.32),
    tuple(sorted(("BASE", "PO4"))): ("NUCLEOTIDE", 0.24),
    tuple(sorted(("NUCLEOTIDE", "NUCLEOTIDE"))): ("CHAIN", 0.38),
    tuple(sorted(("AMINO", "AMINO"))): ("CATALYST", 0.25),
    tuple(sorted(("CHAIN", "NUCLEOTIDE"))): ("CHAIN", 0.44),
    tuple(sorted(("CHAIN", "CHAIN"))): ("CHAIN", 0.30),
}

SIMPLE_TYPES = ["CH4", "NH3", "CO2", "HCN", "H2S", "PO4", "SUGAR", "BASE", "LIPID"]

# -----------------------------
# Static environment
# -----------------------------

water_box = box(
    pos=vector(0, -0.05, 0),
    size=vector(WORLD_HALF.x * 2, WORLD_HALF.y * 2, WORLD_HALF.z * 2),
    color=vector(0.65, 0.88, 1.0),
    opacity=0.12,
)

floor = box(
    pos=vector(0, GROUND_Y - 0.04, 0),
    size=vector(WORLD_HALF.x * 2 + 0.2, 0.08, WORLD_HALF.z * 2 + 0.2),
    color=vector(0.78, 0.74, 0.62),
    opacity=0.65,
)

vent = cylinder(
    pos=vector(-4.8, GROUND_Y - 0.02, -2.7),
    axis=vector(0, 0.18, 0),
    radius=0.48,
    color=vector(0.50, 0.48, 0.45),
    opacity=0.8,
)

vent_glow = sphere(
    pos=vent.pos + vector(0, 0.22, 0),
    radius=0.60,
    color=vector(1.0, 0.72, 0.34),
    opacity=0.22,
    emissive=True,
)

shore_plate = box(
    pos=vector(3.3, GROUND_Y + 0.08, 2.7),
    size=vector(3.8, 0.13, 2.3),
    color=vector(0.82, 0.78, 0.62),
    opacity=0.58,
)

sun_lamp = sphere(
    pos=vector(4.8, WORLD_HALF.y + 1.2, -3.1),
    radius=0.38,
    color=vector(1.0, 0.92, 0.45),
    emissive=True,
)
local_light(pos=sun_lamp.pos, color=vector(1.0, 0.92, 0.70))

# Visual tank edges
edges = []
edge_color = vector(0.48, 0.62, 0.74)
for sx in [-1, 1]:
    for sy in [-1, 1]:
        edges.append(curve(pos=[vector(sx * WORLD_HALF.x, sy * WORLD_HALF.y, -WORLD_HALF.z),
                                vector(sx * WORLD_HALF.x, sy * WORLD_HALF.y, WORLD_HALF.z)],
                           radius=0.012, color=edge_color))
for sx in [-1, 1]:
    for sz in [-1, 1]:
        edges.append(curve(pos=[vector(sx * WORLD_HALF.x, -WORLD_HALF.y, sz * WORLD_HALF.z),
                                vector(sx * WORLD_HALF.x, WORLD_HALF.y, sz * WORLD_HALF.z)],
                           radius=0.012, color=edge_color))
for sy in [-1, 1]:
    for sz in [-1, 1]:
        edges.append(curve(pos=[vector(-WORLD_HALF.x, sy * WORLD_HALF.y, sz * WORLD_HALF.z),
                                vector(WORLD_HALF.x, sy * WORLD_HALF.y, sz * WORLD_HALF.z)],
                           radius=0.012, color=edge_color))

# -----------------------------
# Dynamic visual registries
# -----------------------------

molecules = []
bond_cylinders = []
bubble_objects = []
chain_links = []
marks = []
sparks = []
trail_curves = []

message = label(
    pos=vector(-5.95, 3.65, 0),
    text="",
    xoffset=0,
    yoffset=0,
    height=12,
    color=vector(0.10, 0.16, 0.22),
    box=False,
    opacity=0,
)

hud = label(
    pos=vector(0, 3.85, 0),
    text="",
    height=14,
    color=vector(0.08, 0.12, 0.18),
    box=True,
    border=8,
    opacity=0.68,
    background=vector(0.96, 0.99, 1.0),
)

# -----------------------------
# Classes
# -----------------------------

class FloatingLabel:
    def __init__(self, obj, text):
        self.obj = obj
        self.label = label(
            pos=obj.pos + vector(0, obj.radius + 0.18, 0),
            text=text,
            height=8,
            box=False,
            opacity=0,
            color=vector(0.16, 0.16, 0.20),
            visible=show_labels,
        )

    def update(self):
        self.label.pos = self.obj.pos + vector(0, self.obj.radius + 0.18, 0)
        self.label.visible = show_labels and self.obj.visible

    def destroy(self):
        self.label.visible = False
        self.label.text = ""

class Molecule:
    next_id = 1

    def __init__(self, kind, pos=None, vel=None, energy=0.35, parent=None):
        self.id = Molecule.next_id
        Molecule.next_id += 1
        self.kind = kind
        self.radius = RADII.get(kind, 0.17)
        self.pos = pos if pos is not None else vector(randf(-4.7, 4.7), randf(-2.0, 2.5), randf(-3.2, 3.2))
        self.vel = vel if vel is not None else random_vec(0.45)
        self.vel.y *= 0.55
        self.energy = energy
        self.age = 0.0
        self.charge = randf(-0.8, 0.8) if kind not in ["LIPID", "CHAIN"] else randf(-0.25, 0.25)
        self.bonded = set()
        self.orbit_target = None
        self.marked = False
        self.alive = True
        self.parent = parent
        self.copy_stage = 0.0
        self.replication_cooldown = randf(3.0, 8.0)
        self.trail_timer = randf(0, 1)
        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=COLORS.get(kind, vector(0.8, 0.8, 0.8)),
            opacity=0.88 if kind != "H2O" else 0.36,
            shininess=0.35,
            make_trail=False,
        )
        self.glow = None
        self.label = FloatingLabel(self.obj, kind)
        if kind in ["CHAIN", "CATALYST"]:
            self.glow = sphere(
                pos=self.pos,
                radius=self.radius * 1.55,
                color=COLORS.get(kind, vector(1, 1, 1)),
                opacity=0.16,
                emissive=True,
            )

    def update_visual(self):
        self.obj.pos = self.pos
        self.obj.radius = self.radius * (1.0 + 0.05 * math.sin(self.age * 5.0 + self.id))
        if self.marked:
            self.obj.color = mix_color(COLORS.get(self.kind, vector(0.8, 0.8, 0.8)), vector(1, 1, 1), 0.25)
        else:
            self.obj.color = COLORS.get(self.kind, vector(0.8, 0.8, 0.8))
        if self.glow:
            self.glow.pos = self.pos
            self.glow.radius = self.radius * (1.55 + 0.14 * math.sin(self.age * 4.0))
        self.label.update()

    def destroy(self):
        self.alive = False
        self.obj.visible = False
        if self.glow:
            self.glow.visible = False
        self.label.destroy()

class Bubble:
    next_id = 1

    def __init__(self, center, lipids):
        self.id = Bubble.next_id
        Bubble.next_id += 1
        self.center = center
        self.vel = random_vec(0.13)
        self.age = 0.0
        self.life = randf(24, 42)
        self.radius = clamp(0.55 + 0.045 * len(lipids), 0.75, 1.45)
        self.lipids = list(lipids)
        self.contents = []
        self.shell = sphere(
            pos=self.center,
            radius=self.radius,
            color=vector(1.0, 0.86, 0.38),
            opacity=0.18,
            shininess=0.5,
        )
        self.edge = ring(
            pos=self.center,
            axis=vector(0, 1, 0),
            radius=self.radius,
            thickness=0.025,
            color=vector(0.90, 0.70, 0.26),
            opacity=0.65,
        )
        self.label = label(
            pos=self.center + vector(0, self.radius + 0.16, 0),
            text="lipid bubble",
            height=9,
            box=False,
            opacity=0,
            color=vector(0.20, 0.18, 0.08),
            visible=show_labels,
        )
        for i, lipid in enumerate(self.lipids):
            angle = 2 * math.pi * i / max(1, len(self.lipids))
            lipid.orbit_target = self
            lipid.pos = self.center + vector(math.cos(angle) * self.radius, 0.1 * math.sin(angle * 2), math.sin(angle) * self.radius)
            lipid.vel *= 0.1
            lipid.marked = True

    def update(self, dt):
        self.age += dt
        self.center += self.vel * dt
        if self.center.x < -WORLD_HALF.x + self.radius or self.center.x > WORLD_HALF.x - self.radius:
            self.vel.x *= -0.9
        if self.center.y < GROUND_Y + self.radius or self.center.y > WORLD_HALF.y - self.radius:
            self.vel.y *= -0.9
        if self.center.z < -WORLD_HALF.z + self.radius or self.center.z > WORLD_HALF.z - self.radius:
            self.vel.z *= -0.9
        self.center.x = clamp(self.center.x, -WORLD_HALF.x + self.radius, WORLD_HALF.x - self.radius)
        self.center.y = clamp(self.center.y, GROUND_Y + self.radius, WORLD_HALF.y - self.radius)
        self.center.z = clamp(self.center.z, -WORLD_HALF.z + self.radius, WORLD_HALF.z - self.radius)

        pulse = 1.0 + 0.04 * math.sin(self.age * 2.4 + self.id)
        self.shell.pos = self.center
        self.shell.radius = self.radius * pulse
        self.edge.pos = self.center
        self.edge.axis = vector(math.sin(self.age * 0.4), 1, math.cos(self.age * 0.35))
        self.edge.radius = self.radius * pulse
        self.label.pos = self.center + vector(0, self.radius + 0.20, 0)
        self.label.visible = show_labels

        for i, lipid in enumerate(self.lipids):
            if not lipid.alive:
                continue
            angle = self.age * 0.75 + 2 * math.pi * i / max(1, len(self.lipids))
            tilt = 0.12 * math.sin(angle * 2.7)
            target = self.center + vector(math.cos(angle) * self.radius, tilt, math.sin(angle) * self.radius)
            lipid.vel += (target - lipid.pos) * 0.9 * dt
            lipid.vel *= 0.92

    def destroy(self):
        self.shell.visible = False
        self.edge.visible = False
        self.label.visible = False
        for lipid in self.lipids:
            if lipid.alive:
                lipid.orbit_target = None
                lipid.marked = False
                lipid.vel += random_vec(0.7)

class Spark:
    def __init__(self, pos, color=None, life=1.2, radius=0.045):
        self.pos = vector(pos)
        self.vel = random_vec(randf(0.3, 1.0))
        self.life = life
        self.age = 0.0
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=color if color is not None else vector(1.0, 0.86, 0.30),
            opacity=0.75,
            emissive=True,
        )

    def update(self, dt):
        self.age += dt
        self.vel *= 0.98
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0, 0.75 * (1 - self.age / self.life))
        self.obj.radius *= 0.995
        return self.age < self.life

    def destroy(self):
        self.obj.visible = False

# -----------------------------
# Creation and destruction helpers
# -----------------------------

def print_controls():
    print(__doc__)

def show_message(text):
    message.text = text

def add_mark(pos, color=None, radius=0.07, life_note=False):
    if len(marks) >= MAX_MARKS:
        old = marks.pop(0)
        old.visible = False
    mark_obj = sphere(
        pos=pos,
        radius=radius,
        color=color if color is not None else vector(1.0, 0.75, 0.30),
        opacity=0.28,
        emissive=True,
    )
    marks.append(mark_obj)
    return mark_obj

def add_sparks(pos, n=8, color=None, force=1.0):
    for _ in range(n):
        sparks.append(Spark(pos + random_vec(0.07), color=color, life=randf(0.5, 1.8), radius=randf(0.025, 0.065)))
    while len(sparks) > 220:
        old = sparks.pop(0)
        old.destroy()

def add_trail_segment(p1, p2, col=None):
    if len(trail_curves) >= MAX_TRAILS:
        old = trail_curves.pop(0)
        old.visible = False
    tr = curve(
        pos=[p1, p2],
        radius=0.008,
        color=col if col is not None else vector(0.48, 0.64, 0.78),
        opacity=0.42,
    )
    trail_curves.append(tr)

def spawn_molecule(kind=None, pos=None, vel=None, energy=None):
    if len(molecules) >= MAX_MOLECULES:
        simple = [m for m in molecules if m.kind in SIMPLE_TYPES and m.alive]
        if simple:
            destroy_molecule(random.choice(simple))
        else:
            return None
    if kind is None:
        kind = random.choice(SIMPLE_TYPES)
    if pos is None:
        pos = vector(randf(-5.2, 5.2), randf(-2.4, 2.6), randf(-3.7, 3.7))
    if vel is None:
        vel = random_vec(randf(0.2, 0.8))
    if energy is None:
        energy = randf(0.18, 0.55)
    m = Molecule(kind, pos=pos, vel=vel, energy=energy)
    molecules.append(m)
    return m

def destroy_molecule(m):
    for other in molecules:
        if m.id in other.bonded:
            other.bonded.discard(m.id)
    m.destroy()
    if m in molecules:
        molecules.remove(m)

def clear_bonds():
    for b in bond_cylinders:
        b.visible = False
    bond_cylinders[:] = []

def clear_chain_links():
    for c in chain_links:
        c.visible = False
    chain_links[:] = []

def clear_marks_and_trails():
    for mk in marks:
        mk.visible = False
    marks[:] = []
    for sp in sparks:
        sp.destroy()
    sparks[:] = []
    for tr in trail_curves:
        tr.visible = False
    trail_curves[:] = []
    show_message("cleared temporary marks and trails")

def clear_all_dynamic():
    clear_bonds()
    clear_chain_links()
    clear_marks_and_trails()
    for b in bubble_objects:
        b.destroy()
    bubble_objects[:] = []
    for m in list(molecules):
        destroy_molecule(m)

def initial_soup():
    clear_all_dynamic()
    Molecule.next_id = 1
    for _ in range(14):
        spawn_molecule("H2O", energy=0.12)
    for kind, count in [
        ("CH4", 8), ("NH3", 8), ("CO2", 7), ("HCN", 7), ("H2S", 5),
        ("PO4", 5), ("SUGAR", 7), ("BASE", 7), ("LIPID", 12)
    ]:
        for _ in range(count):
            spawn_molecule(kind)
    show_message("round %d: primordial soup seeded" % round_index)

# -----------------------------
# Chemistry interactions
# -----------------------------

def try_react(a, b, impulse=1.0):
    if not a.alive or not b.alive:
        return None
    key = tuple(sorted((a.kind, b.kind)))
    if key not in RECIPE_PAIRS:
        return None

    product_kind, base_prob = RECIPE_PAIRS[key]
    energy_factor = clamp((a.energy + b.energy) * 0.65, 0.0, 0.9)
    catalyst_bonus = 0.0
    nearby_catalysts = 0
    for c in molecules:
        if c.alive and c.kind in ["CATALYST", "CHAIN"] and mag(c.pos - (a.pos + b.pos) * 0.5) < 1.2:
            nearby_catalysts += 1
    catalyst_bonus = min(0.20, nearby_catalysts * 0.04)
    prob = clamp(base_prob + energy_factor + catalyst_bonus, 0.02, 0.86)

    if random.random() > prob:
        if random.random() < 0.18:
            add_sparks((a.pos + b.pos) * 0.5, n=2, color=vector(0.9, 0.9, 1.0))
        return None

    center = (a.pos + b.pos) * 0.5
    vel = (a.vel + b.vel) * 0.35 + random_vec(0.16)
    new_energy = clamp((a.energy + b.energy) * 0.55 + 0.18, 0.18, 0.95)

    destroy_molecule(a)
    destroy_molecule(b)
    p = spawn_molecule(product_kind, center, vel, new_energy)
    if p:
        p.marked = True
        add_sparks(center, n=13 if product_kind in ["CHAIN", "CATALYST"] else 8, color=COLORS.get(product_kind, vector(1, 1, 1)))
        add_mark(center, COLORS.get(product_kind, vector(1, 1, 1)), radius=0.16 if product_kind == "CHAIN" else 0.10)
        show_message("reaction formed %s" % product_kind)
    return p

def form_lipid_bubble(force=False):
    lipids = [m for m in molecules if m.alive and m.kind == "LIPID" and m.orbit_target is None]
    if len(lipids) < 6:
        return None

    best_group = None
    for _ in range(16):
        seed = random.choice(lipids)
        group = sorted(lipids, key=lambda m: mag(m.pos - seed.pos))[:8]
        density = sum(1 for g in group if mag(g.pos - seed.pos) < 1.7)
        if density >= 5 or force:
            best_group = group[:random.randint(6, min(10, len(group)))]
            break

    if not best_group:
        return None

    center = vector(0, 0, 0)
    for m in best_group:
        center += m.pos
    center /= len(best_group)

    b = Bubble(center, best_group)
    bubble_objects.append(b)
    add_sparks(center, n=18, color=vector(1.0, 0.82, 0.30))
    add_mark(center, vector(1.0, 0.82, 0.30), radius=0.25)
    show_message("lipids wrapped into a bubble")
    return b

def seed_self_copying_chain(force=False):
    nucs = [m for m in molecules if m.alive and m.kind == "NUCLEOTIDE"]
    if len(nucs) >= 2:
        group = nucs[:min(4, len(nucs))]
        center = sum((m.pos for m in group), vector(0, 0, 0)) / len(group)
        for m in group:
            destroy_molecule(m)
        chain = spawn_molecule("CHAIN", center, random_vec(0.2), 0.82)
    elif force:
        center = vector(randf(-2.5, 2.5), randf(-1.2, 1.6), randf(-2.4, 2.4))
        chain = spawn_molecule("CHAIN", center, random_vec(0.2), 0.82)
    else:
        return None
    if chain:
        chain.radius = 0.28
        chain.copy_stage = 0.2
        add_sparks(chain.pos, n=24, color=COLORS["CHAIN"])
        show_message("self-copying chain seeded")
    return chain

def replicate_chain(chain):
    if len(molecules) >= MAX_MOLECULES - 2:
        return None

    nearby = [m for m in molecules if m.alive and m.kind in ["NUCLEOTIDE", "BASE", "SUGAR", "PO4"] and mag(m.pos - chain.pos) < 1.65]
    if len(nearby) < 2 and random.random() > 0.18:
        return None

    chain.replication_cooldown = randf(6.0, 11.0)
    chain.copy_stage = 0.0

    if nearby:
        for m in nearby[:min(2, len(nearby))]:
            destroy_molecule(m)

    offset = random_vec(0.55)
    copy = spawn_molecule("CHAIN", chain.pos + offset, chain.vel * 0.2 + random_vec(0.15), 0.76)
    if copy:
        copy.radius = clamp(chain.radius * randf(0.95, 1.08), 0.22, 0.36)
        copy.parent = chain.id
        copy.marked = True
        chain.bonded.add(copy.id)
        copy.bonded.add(chain.id)
        add_sparks((chain.pos + copy.pos) * 0.5, n=26, color=COLORS["CHAIN"])
        add_mark(copy.pos, COLORS["CHAIN"], radius=0.20)
        show_message("chain copied itself")
    return copy

def update_bond_visuals():
    clear_bonds()
    mol_by_id = {m.id: m for m in molecules if m.alive}
    drawn = set()
    for m in molecules:
        if not m.alive:
            continue
        for bid in list(m.bonded):
            if bid not in mol_by_id:
                m.bonded.discard(bid)
                continue
            pair = tuple(sorted((m.id, bid)))
            if pair in drawn:
                continue
            drawn.add(pair)
            other = mol_by_id[bid]
            axis = other.pos - m.pos
            if mag(axis) > 0.01:
                bond_cylinders.append(cylinder(
                    pos=m.pos,
                    axis=axis,
                    radius=0.025,
                    color=mix_color(COLORS.get(m.kind, vector(1,1,1)), COLORS.get(other.kind, vector(1,1,1)), 0.5),
                    opacity=0.55,
                ))

def update_chain_links():
    clear_chain_links()
    chains = [m for m in molecules if m.alive and m.kind == "CHAIN"]
    if len(chains) < 2:
        return
    chains_sorted = sorted(chains, key=lambda m: (m.parent if m.parent is not None else m.id, m.id))
    for i in range(len(chains_sorted) - 1):
        a = chains_sorted[i]
        b = chains_sorted[i + 1]
        if mag(a.pos - b.pos) < 2.3:
            chain_links.append(curve(
                pos=[a.pos, b.pos],
                radius=0.018,
                color=vector(1.0, 0.54, 0.70),
                opacity=0.48,
            ))

# -----------------------------
# Physics
# -----------------------------

def boundary_bounce(m):
    r = m.radius
    if m.pos.x < -WORLD_HALF.x + r:
        m.pos.x = -WORLD_HALF.x + r
        m.vel.x = abs(m.vel.x) * 0.78
    if m.pos.x > WORLD_HALF.x - r:
        m.pos.x = WORLD_HALF.x - r
        m.vel.x = -abs(m.vel.x) * 0.78
    if m.pos.y < -WORLD_HALF.y + r:
        m.pos.y = -WORLD_HALF.y + r
        m.vel.y = abs(m.vel.y) * 0.74
    if m.pos.y > WORLD_HALF.y - r:
        m.pos.y = WORLD_HALF.y - r
        m.vel.y = -abs(m.vel.y) * 0.74
    if m.pos.z < -WORLD_HALF.z + r:
        m.pos.z = -WORLD_HALF.z + r
        m.vel.z = abs(m.vel.z) * 0.78
    if m.pos.z > WORLD_HALF.z - r:
        m.pos.z = WORLD_HALF.z - r
        m.vel.z = -abs(m.vel.z) * 0.78

def environmental_forces(m, dt):
    # Hydrothermal vent lift and heat
    to_vent = m.pos - vent.pos
    horizontal_dist = math.sqrt(to_vent.x * to_vent.x + to_vent.z * to_vent.z)
    if horizontal_dist < 1.55 and m.pos.y < -0.2:
        lift = (1.55 - horizontal_dist) / 1.55
        m.vel.y += 0.42 * lift * dt
        m.energy = clamp(m.energy + 0.28 * lift * dt, 0, 1.2)

    # Shore surface concentration
    if m.pos.x > 2.0 and m.pos.z > 1.5 and m.pos.y < -2.0:
        m.vel += (shore_plate.pos - m.pos) * 0.045 * dt
        m.energy = clamp(m.energy + 0.04 * dt, 0, 1.1)

    # Sunlight agitation
    sun_dir = safe_norm(sun_lamp.pos - m.pos)
    sunlight = max(0, dot(sun_dir, vector(0, 1, 0))) * 0.012
    m.vel += random_vec(sunlight) * dt * 18
    if m.kind in ["HCN", "BASE", "SUGAR", "PO4"]:
        m.energy = clamp(m.energy + sunlight * dt * 2.0, 0, 1.2)

    # Brownian stirring
    m.vel += random_vec(0.09 + m.energy * 0.06) * dt

    # Water drag
    drag = 0.992 - clamp(m.energy, 0, 1) * 0.004
    m.vel *= drag

def update_molecule_physics(dt):
    living = [m for m in molecules if m.alive]

    for m in living:
        m.age += dt
        environmental_forces(m, dt)

        # Bubble orbiting or containment
        if isinstance(m.orbit_target, Bubble):
            toward = m.orbit_target.center - m.pos
            tangential = cross(safe_norm(toward), vector(0, 1, 0))
            if mag(tangential) < 0.01:
                tangential = vector(1, 0, 0)
            desired_dist = m.orbit_target.radius
            radial_error = mag(toward) - desired_dist
            m.vel += safe_norm(toward) * radial_error * 0.7 * dt
            m.vel += safe_norm(tangential) * 0.18 * dt

        # Chain attracts nucleotide-like materials
        if m.kind == "CHAIN":
            for other in living:
                if other is m or other.kind not in ["NUCLEOTIDE", "BASE", "SUGAR", "PO4"]:
                    continue
                d = other.pos - m.pos
                dsq = mag2(d)
                if 0.08 < dsq < 4.2:
                    other.vel += -safe_norm(d) * 0.16 * dt
                    m.vel += safe_norm(d) * 0.035 * dt

        # Mild charge interactions
        for other in living:
            if other.id <= m.id:
                continue
            d = other.pos - m.pos
            dsq = mag2(d)
            if 0.05 < dsq < 1.25:
                direction = safe_norm(d)
                charge_force = -m.charge * other.charge * 0.006 / max(dsq, 0.08)
                m.vel += -direction * charge_force * dt
                other.vel += direction * charge_force * dt

        m.pos += m.vel * dt
        boundary_bounce(m)

        if random.random() < 0.008 and m.kind != "H2O":
            m.marked = False

        m.trail_timer -= dt
        if m.trail_timer <= 0 and m.kind in ["CHAIN", "CATALYST", "NUCLEOTIDE"]:
            m.trail_timer = randf(0.45, 1.0)
            add_trail_segment(m.pos - m.vel * 0.25, m.pos, COLORS.get(m.kind, vector(0.6, 0.6, 0.8)))

        # Chain replication timer
        if m.kind == "CHAIN":
            m.replication_cooldown -= dt
            m.copy_stage += dt * 0.08
            if m.replication_cooldown <= 0:
                replicate_chain(m)

    # Pair collisions and reactions
    living = [m for m in molecules if m.alive]
    random.shuffle(living)
    checked = 0
    for i, a in enumerate(living):
        for b in living[i + 1:]:
            checked += 1
            if checked > 620:
                break
            d = b.pos - a.pos
            dist = mag(d)
            min_dist = a.radius + b.radius + 0.035
            if dist < min_dist and dist > 1e-6:
                n = d / dist
                overlap = min_dist - dist
                a.pos -= n * overlap * 0.5
                b.pos += n * overlap * 0.5

                rel = dot(b.vel - a.vel, n)
                impulse = max(0.05, abs(rel))
                a.vel -= n * impulse * 0.28
                b.vel += n * impulse * 0.28

                if a.kind != "H2O" and b.kind != "H2O":
                    if random.random() < 0.34:
                        a.bonded.add(b.id)
                        b.bonded.add(a.id)
                    try_react(a, b, impulse=impulse)
                    break
        if checked > 620:
            break

    if random.random() < 0.012:
        form_lipid_bubble(force=False)

    for b in list(bubble_objects):
        b.update(dt)
        if b.age > b.life:
            b.destroy()
            bubble_objects.remove(b)
            show_message("old lipid bubble opened and released its lipids")

    for sp in list(sparks):
        if not sp.update(dt):
            sp.destroy()
            sparks.remove(sp)

    for m in list(molecules):
        if m.alive:
            m.update_visual()

# -----------------------------
# AI Controller
# -----------------------------

class ChemicalSoupAI:
    MODES = [
        "observe",
        "stir",
        "feed",
        "concentrate",
        "spark",
        "wrap",
        "copy",
        "prune",
        "chaos",
        "ritual",
        "artist",
        "reset_watch",
    ]

    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.mode_duration = 6.0
        self.action_timer = 0.0
        self.round_timer = 0.0
        self.last_score = 0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_change_time = 0.0
        self.preferred_center = vector(0, 0, 0)
        self.curiosity = 0.4
        self.carefulness = 0.5
        self.chaos = 0.25
        self.ritual_phase = 0.0

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0
        show_message("AI mode: %s" % self.mode)

    def set_mode(self, mode):
        if mode in self.MODES:
            self.mode_index = self.MODES.index(mode)
            self.mode = mode
            self.mode_timer = 0
            show_message("AI mode: %s" % self.mode)

    def read_state(self):
        counts = {}
        total_energy = 0.0
        avg_speed = 0.0
        living = [m for m in molecules if m.alive]
        for m in living:
            counts[m.kind] = counts.get(m.kind, 0) + 1
            total_energy += m.energy
            avg_speed += mag(m.vel)
        n = max(1, len(living))
        chain_count = counts.get("CHAIN", 0)
        nucleotide_count = counts.get("NUCLEOTIDE", 0)
        amino_count = counts.get("AMINO", 0)
        lipid_count = counts.get("LIPID", 0)
        catalyst_count = counts.get("CATALYST", 0)
        product_score = chain_count * 7 + nucleotide_count * 3 + amino_count * 2 + catalyst_count * 4 + len(bubble_objects) * 5
        state = {
            "counts": counts,
            "molecule_count": len(living),
            "bubble_count": len(bubble_objects),
            "chain_count": chain_count,
            "nucleotide_count": nucleotide_count,
            "amino_count": amino_count,
            "lipid_count": lipid_count,
            "catalyst_count": catalyst_count,
            "avg_energy": total_energy / n,
            "avg_speed": avg_speed / n,
            "product_score": product_score,
            "simple_count": sum(counts.get(k, 0) for k in SIMPLE_TYPES),
            "empty": len(living) < 12,
            "stable": avg_speed / n < 0.035,
            "complete": chain_count >= 8 or (chain_count >= 4 and len(bubble_objects) >= 2 and catalyst_count >= 2),
        }
        return state

    def choose_mode(self, state):
        # Dynamic state machine: different goals depending on what the soup lacks.
        if state["empty"]:
            return "feed"
        if state["complete"]:
            return "reset_watch"
        if self.stagnation_timer > 12.0:
            return random.choice(["chaos", "spark", "feed", "reset_watch"])
        if state["lipid_count"] >= 8 and state["bubble_count"] < 2:
            return "wrap"
        if state["nucleotide_count"] >= 3 and state["chain_count"] < 2:
            return "copy"
        if state["avg_energy"] < 0.26:
            return "spark"
        if state["molecule_count"] > 105:
            return "prune"
        if random.random() < 0.18:
            return random.choice(["artist", "ritual", "concentrate", "stir"])
        return random.choice(["observe", "stir", "concentrate", "feed"])

    def update_stagnation(self, state, dt):
        score = state["product_score"] + int(state["avg_energy"] * 12) + state["molecule_count"] // 8
        if abs(score - self.last_score) <= 1:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0, self.stagnation_timer - dt * 2.0)
            self.last_change_time = self.round_timer
        self.last_score = score
        if state["complete"]:
            self.completion_timer += dt
        else:
            self.completion_timer = 0.0

    def update(self, dt):
        if not self.enabled:
            return

        self.round_timer += dt
        self.mode_timer += dt
        self.action_timer -= dt
        self.ritual_phase += dt

        state = self.read_state()
        self.update_stagnation(state, dt)

        if self.mode_timer > self.mode_duration:
            new_mode = self.choose_mode(state)
            self.set_mode(new_mode)
            self.mode_duration = randf(4.0, 9.5) if new_mode != "reset_watch" else 3.0
            self.curiosity = clamp(self.curiosity + randf(-0.14, 0.16), 0.05, 1.0)
            self.carefulness = clamp(self.carefulness + randf(-0.12, 0.12), 0.05, 1.0)
            self.chaos = clamp(self.chaos + randf(-0.12, 0.18), 0.05, 1.0)

        # If the scene has halted or completed, loop into a new round.
        if state["empty"] or self.completion_timer > 5.5 or self.stagnation_timer > 22.0:
            self.reset_round(reason="AI loop reset: halted, complete, or stagnant")
            return

        if self.action_timer <= 0:
            self.perform_action(state)
            self.action_timer = randf(0.22, 1.35)

    def reset_round(self, reason="AI reset"):
        global round_index
        round_index += 1
        self.round_timer = 0.0
        self.mode_timer = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_score = 0
        initial_soup()
        add_sparks(vector(0, 0, 0), n=40, color=vector(1.0, 0.85, 0.35))
        show_message("%s — round %d" % (reason, round_index))

    def perform_action(self, state):
        mode = self.mode

        if mode == "observe":
            self.action_observe(state)
        elif mode == "stir":
            self.action_stir(strength=0.35)
        elif mode == "feed":
            self.action_feed(state)
        elif mode == "concentrate":
            self.action_concentrate(state)
        elif mode == "spark":
            self.action_spark(state)
        elif mode == "wrap":
            self.action_wrap(state)
        elif mode == "copy":
            self.action_copy(state)
        elif mode == "prune":
            self.action_prune(state)
        elif mode == "chaos":
            self.action_chaos(state)
        elif mode == "ritual":
            self.action_ritual(state)
        elif mode == "artist":
            self.action_artist(state)
        elif mode == "reset_watch":
            if random.random() < 0.35:
                self.reset_round(reason="AI began a new origin round")
            else:
                self.action_stir(strength=0.12)

    def pick(self, kinds=None):
        pool = [m for m in molecules if m.alive and (kinds is None or m.kind in kinds)]
        if not pool:
            return None
        return random.choice(pool)

    def action_observe(self, state):
        target = self.pick(["CHAIN", "NUCLEOTIDE", "AMINO", "CATALYST"]) or self.pick()
        if target:
            target.marked = True
            add_mark(target.pos, vector(1.0, 1.0, 1.0), radius=0.11)
            # Gentle attention: slow target so collisions gather around it.
            target.vel *= 0.74

    def action_stir(self, strength=0.35):
        center = vector(randf(-1.5, 1.5), randf(-0.6, 0.9), randf(-1.5, 1.5))
        for m in molecules:
            if not m.alive:
                continue
            d = m.pos - center
            swirl = cross(vector(0, 1, 0), d)
            if mag(swirl) > 0.01:
                m.vel += safe_norm(swirl) * strength * randf(0.3, 1.0)
            m.vel += random_vec(strength * 0.12)
        add_sparks(center, n=8, color=vector(0.62, 0.82, 1.0))
        add_mark(center, vector(0.62, 0.82, 1.0), radius=0.16)
        show_message("AI stirred the chemical soup")

    def action_feed(self, state):
        needed = []
        if state["counts"].get("BASE", 0) < 4:
            needed.append("BASE")
        if state["counts"].get("SUGAR", 0) < 4:
            needed.append("SUGAR")
        if state["counts"].get("PO4", 0) < 3:
            needed.append("PO4")
        if state["counts"].get("LIPID", 0) < 8:
            needed.append("LIPID")
        if state["counts"].get("NH3", 0) < 4:
            needed.append("NH3")
        if not needed:
            needed = SIMPLE_TYPES

        pos = vector(randf(-5.0, 5.0), WORLD_HALF.y - 0.25, randf(-3.5, 3.5))
        for _ in range(random.randint(2, 6)):
            kind = random.choice(needed)
            spawn_molecule(kind, pos + random_vec(0.4), vector(randf(-0.2, 0.2), randf(-0.55, -0.15), randf(-0.2, 0.2)), energy=randf(0.35, 0.8))
        add_sparks(pos, n=12, color=vector(0.95, 0.95, 1.0))
        show_message("AI spilled new feedstock molecules")

    def action_concentrate(self, state):
        center = random.choice([vent.pos + vector(0, 0.9, 0), shore_plate.pos + vector(0, 0.7, 0), vector(0, 0, 0)])
        target_kinds = ["BASE", "SUGAR", "PO4", "NUCLEOTIDE", "LIPID", "CHAIN"]
        for m in molecules:
            if m.alive and m.kind in target_kinds:
                m.vel += (center - m.pos) * 0.16
                m.marked = True
        add_mark(center, vector(1.0, 0.78, 0.35), radius=0.20)
        show_message("AI concentrated reactive molecules")

    def action_spark(self, state):
        center = self.pick(["HCN", "NH3", "BASE", "SUGAR", "PO4", "NUCLEOTIDE"])
        pos = center.pos if center else vector(randf(-3, 3), randf(-1, 2), randf(-3, 3))
        for m in molecules:
            if m.alive and mag(m.pos - pos) < 1.8:
                m.energy = clamp(m.energy + randf(0.18, 0.42), 0, 1.25)
                m.vel += safe_norm(m.pos - pos + random_vec(0.1)) * randf(0.05, 0.45)
                m.marked = True
        add_sparks(pos, n=28, color=vector(1.0, 0.82, 0.25))
        add_mark(pos, vector(1.0, 0.82, 0.25), radius=0.28)
        show_message("AI added an energy spark")

    def action_wrap(self, state):
        bubble = form_lipid_bubble(force=True)
        if not bubble:
            self.action_concentrate(state)

    def action_copy(self, state):
        chain = self.pick(["CHAIN"])
        if chain:
            chain.replication_cooldown = min(chain.replication_cooldown, 0.2)
            chain.marked = True
            for m in molecules:
                if m.alive and m.kind in ["NUCLEOTIDE", "BASE", "SUGAR", "PO4"] and mag(m.pos - chain.pos) < 2.8:
                    m.vel += (chain.pos - m.pos) * 0.17
            add_mark(chain.pos, COLORS["CHAIN"], radius=0.22)
            show_message("AI encouraged self-copying")
        else:
            seed_self_copying_chain(force=state["nucleotide_count"] >= 2)

    def action_prune(self, state):
        low_value = [m for m in molecules if m.alive and m.kind in ["H2O", "WASTE", "CH4", "H2S"]]
        random.shuffle(low_value)
        for m in low_value[:random.randint(2, 5)]:
            add_sparks(m.pos, n=3, color=vector(0.75, 0.75, 0.85))
            destroy_molecule(m)
        show_message("AI cleared crowded material")

    def action_chaos(self, state):
        center = vector(randf(-3, 3), randf(-1.5, 1.8), randf(-3, 3))
        for m in molecules:
            if not m.alive:
                continue
            d = m.pos - center
            if mag(d) < 3.2:
                m.vel += safe_norm(d + random_vec(0.4)) * randf(0.35, 1.0)
                m.energy = clamp(m.energy + randf(0.04, 0.25), 0, 1.25)
                if random.random() < 0.18:
                    m.bonded.clear()
        if random.random() < 0.4:
            self.action_feed(state)
        add_sparks(center, n=34, color=vector(1.0, 0.58, 0.40))
        add_mark(center, vector(1.0, 0.58, 0.40), radius=0.35)
        show_message("AI performed chaotic mixing")

    def action_ritual(self, state):
        # Arrange selected molecules in a circular procession.
        center = vector(0, 0.15 * math.sin(self.ritual_phase), 0)
        candidates = [m for m in molecules if m.alive and m.kind != "H2O"]
        random.shuffle(candidates)
        group = candidates[:min(18, len(candidates))]
        if not group:
            return
        radius = 1.4 + 0.35 * math.sin(self.ritual_phase * 0.6)
        for i, m in enumerate(group):
            angle = self.ritual_phase * 0.7 + 2 * math.pi * i / len(group)
            target = center + vector(math.cos(angle) * radius, 0.55 * math.sin(angle * 2), math.sin(angle) * radius)
            m.vel += (target - m.pos) * 0.22
            m.marked = True
        if random.random() < 0.4:
            add_mark(center, vector(0.78, 0.65, 1.0), radius=0.18)
        show_message("AI arranged a molecular ritual")

    def action_artist(self, state):
        # Paint a visible path using marks and gently move molecules through it.
        t = self.ritual_phase
        points = []
        for i in range(5):
            a = t * 0.8 + i * 1.256
            points.append(vector(math.cos(a) * (1.0 + 0.24 * i), 0.55 * math.sin(a * 1.7), math.sin(a) * (1.0 + 0.24 * i)))
        for p in points:
            add_mark(p, vector(0.80, 0.92, 1.0), radius=0.075)
        for m in molecules:
            if m.alive and random.random() < 0.24:
                target = random.choice(points)
                m.vel += (target - m.pos) * 0.12
                m.marked = True
        show_message("AI painted molecular paths")

ai = ChemicalSoupAI()

# -----------------------------
# Human controls
# -----------------------------

def human_override():
    ai.action_spark(ai.read_state())
    ai.action_feed(ai.read_state())
    show_message("human override: pulse and spill")

def keydown(evt):
    global paused, ai_enabled, sim_speed, show_labels
    key = evt.key.lower()

    if key == "a":
        ai.enabled = not ai.enabled
        show_message("AI enabled" if ai.enabled else "AI disabled")
    elif key == "p":
        paused = not paused
        show_message("paused" if paused else "resumed")
    elif key == "r":
        ai.reset_round(reason="manual reset")
    elif key == "m":
        ai.cycle_mode()
    elif key == "o":
        human_override()
    elif key == "c":
        clear_marks_and_trails()
    elif key == "b":
        form_lipid_bubble(force=True)
    elif key == "s":
        seed_self_copying_chain(force=True)
    elif key in ["+", "="]:
        sim_speed = clamp(sim_speed + 0.15, 0.25, 3.0)
        show_message("speed %.2fx" % sim_speed)
    elif key in ["-", "_"]:
        sim_speed = clamp(sim_speed - 0.15, 0.25, 3.0)
        show_message("speed %.2fx" % sim_speed)
    elif key == "l":
        show_labels = not show_labels
        show_message("labels on" if show_labels else "labels off")
    elif key == "h":
        print_controls()
        show_message("controls printed to terminal")

scene.bind("keydown", keydown)

# -----------------------------
# HUD
# -----------------------------

def update_hud():
    state = ai.read_state()
    counts = state["counts"]
    hud.text = (
        "Origin of Life Chemical Soup | round %d | AI %s | mode: %s | speed %.2fx\n"
        "molecules %d | amino %d | nucleotides %d | chains %d | catalysts %d | bubbles %d | avg energy %.2f | stagnation %.1fs\n"
        "A AI  P pause  R reset  M mode  O override  B bubble  S seed chain  C clear  +/- speed  H help"
        % (
            round_index,
            "on" if ai.enabled else "off",
            ai.mode,
            sim_speed,
            state["molecule_count"],
            counts.get("AMINO", 0),
            counts.get("NUCLEOTIDE", 0),
            counts.get("CHAIN", 0),
            counts.get("CATALYST", 0),
            state["bubble_count"],
            state["avg_energy"],
            ai.stagnation_timer,
        )
    )

# -----------------------------
# Main loop
# -----------------------------

initial_soup()
print_controls()
last_t = time.time()
hud_timer = 0.0
bond_timer = 0.0
chain_timer = 0.0

while True:
    rate(60)
    now = time.time()
    real_dt = clamp(now - last_t, 0.001, 0.05)
    last_t = now

    if paused:
        update_hud()
        continue

    dt = real_dt * sim_speed

    # Ambient water shimmer
    vent_glow.opacity = 0.18 + 0.08 * (0.5 + 0.5 * math.sin(now * 3.0))
    water_box.opacity = 0.10 + 0.025 * (0.5 + 0.5 * math.sin(now * 0.7))

    ai.update(dt)
    update_molecule_physics(dt)

    bond_timer -= dt
    chain_timer -= dt
    hud_timer -= dt

    if bond_timer <= 0:
        update_bond_visuals()
        bond_timer = 0.16

    if chain_timer <= 0:
        update_chain_links()
        chain_timer = 0.35

    if hud_timer <= 0:
        update_hud()
        hud_timer = 0.20
