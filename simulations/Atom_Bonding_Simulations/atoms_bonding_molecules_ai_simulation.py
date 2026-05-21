#!/usr/bin/env python3
"""
Atoms Bonding into Molecules — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python atoms_bonding_molecules_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    O       human override: spawn/spill free electrons and push atoms
    D       detach weakest/free molecule bonds
    C       clear marks and temporary particles
    + / =   increase AI action speed
    - / _   decrease AI action speed
    H       print controls

Scene concept:
    Protons, neutrons, and electrons assemble into simplified atoms. Atoms drift,
    collide, share electrons, and attach into simple molecules: H2O, CO2, O2, CH4.

Notes:
    This is a visual/educational simulation, not a quantum chemistry solver.
    It uses simplified bonding rules and readable 3D motion.
    The file is self-contained and uses VPython primitives only.

AI behavior modes:
    - CURIOUS: scan atoms, nudge likely bond partners together
    - CAREFUL: build molecule templates in a clean, deliberate order
    - CHAOTIC: stir atoms, spill electrons, create collisions
    - RITUAL: orbit atoms around a molecule altar, then assemble
    - CONSTRUCTIVE: prioritize completing H2O, CO2, O2, CH4
    - DESTRUCTIVE: detach bonds and scatter atoms
    - ARTISTIC: arrange completed molecules into a rotating gallery

The AI reads simulation state, chooses actions, runs automatically, and can be paused
or overridden by keyboard control.
"""

from vpython import *
from math import sin, cos, pi, sqrt, atan2
from random import random, uniform, choice, randint

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="Atoms Bonding into Molecules — AI Controlled VPython Simulation",
    width=1280,
    height=760,
    background=vector(0.96, 0.98, 1.0),
    center=vector(0, 0, 0),
)

scene.forward = vector(-0.25, -0.28, -1.0)
scene.up = vector(0, 1, 0)
scene.range = 12

# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def clamp(value, low, high):
    return max(low, min(high, value))

def safe_norm(v, fallback=vector(1, 0, 0)):
    mag_v = mag(v)
    if mag_v < 1e-8:
        return fallback
    return v / mag_v

def rand_vec(scale=1.0):
    return vector(uniform(-scale, scale), uniform(-scale, scale), uniform(-scale, scale))

def lerp_vec(a, b, t):
    return a * (1 - t) + b * t

def distance(a, b):
    return mag(a - b)

def color_mix(a, b, t):
    return a * (1 - t) + b * t

# ------------------------------------------------------------
# Visual constants
# ------------------------------------------------------------

COLORS = {
    "proton": vector(1.0, 0.38, 0.34),
    "neutron": vector(0.78, 0.78, 0.80),
    "electron": vector(0.20, 0.45, 1.0),
    "H": vector(0.98, 0.98, 1.0),
    "O": vector(0.98, 0.25, 0.22),
    "C": vector(0.18, 0.18, 0.20),
    "bond": vector(0.35, 0.45, 0.55),
    "shared": vector(0.18, 0.42, 1.0),
    "mark": vector(1.0, 0.78, 0.20),
    "field": vector(0.50, 0.80, 1.0),
    "altar": vector(0.88, 0.90, 1.0),
    "success": vector(0.25, 0.78, 0.45),
    "warning": vector(1.0, 0.45, 0.28),
}

ELEMENT_DATA = {
    "H": {
        "name": "Hydrogen",
        "protons": 1,
        "neutrons": 0,
        "electrons": 1,
        "valence": 1,
        "desired_bonds": 1,
        "radius": 0.34,
        "nucleus_radius": 0.16,
        "mass": 1.0,
        "color": COLORS["H"],
    },
    "O": {
        "name": "Oxygen",
        "protons": 8,
        "neutrons": 8,
        "electrons": 8,
        "valence": 6,
        "desired_bonds": 2,
        "radius": 0.58,
        "nucleus_radius": 0.30,
        "mass": 16.0,
        "color": COLORS["O"],
    },
    "C": {
        "name": "Carbon",
        "protons": 6,
        "neutrons": 6,
        "electrons": 6,
        "valence": 4,
        "desired_bonds": 4,
        "radius": 0.52,
        "nucleus_radius": 0.28,
        "mass": 12.0,
        "color": COLORS["C"],
    },
}

MOLECULE_TEMPLATES = {
    "H2O": ["O", "H", "H"],
    "CO2": ["C", "O", "O"],
    "O2": ["O", "O"],
    "CH4": ["C", "H", "H", "H", "H"],
}

AI_MODES = [
    "CURIOUS",
    "CAREFUL",
    "CONSTRUCTIVE",
    "CHAOTIC",
    "RITUAL",
    "ARTISTIC",
    "DESTRUCTIVE",
]

# ------------------------------------------------------------
# Global simulation state containers
# ------------------------------------------------------------

atoms = []
bonds = []
free_electrons = []
marks = []
spark_particles = []
molecule_labels = []
round_number = 0

paused = False
show_help = True

# ------------------------------------------------------------
# Lightweight object classes
# ------------------------------------------------------------

class SparkParticle:
    def __init__(self, pos, vel=None, color=vector(1, 0.85, 0.25), radius=0.035, life=1.5):
        self.pos = vector(pos)
        self.vel = vector(vel) if vel is not None else rand_vec(1.0)
        self.life = life
        self.max_life = life
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=color,
            emissive=True,
            opacity=0.75,
        )

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = max(0.0, 0.75 * self.life / self.max_life)
        return self.life > 0

    def delete(self):
        self.obj.visible = False
        del self.obj

class FreeElectron:
    def __init__(self, pos, vel=None, owner=None):
        self.pos = vector(pos)
        self.vel = vector(vel) if vel is not None else rand_vec(2.5)
        self.owner = owner
        self.life = 12.0
        self.obj = sphere(
            pos=self.pos,
            radius=0.075,
            color=COLORS["electron"],
            emissive=True,
            make_trail=True,
            trail_radius=0.012,
            retain=36,
        )

    def update(self, dt):
        self.life -= dt
        attraction = vector(0, 0, 0)
        nearest = None
        nearest_d = 999
        for atom in atoms:
            d = distance(self.pos, atom.pos)
            if d < nearest_d:
                nearest_d = d
                nearest = atom
        if nearest is not None and nearest_d < 4.0:
            attraction += safe_norm(nearest.pos - self.pos) * (0.9 / max(0.3, nearest_d))
        self.vel += attraction * dt
        self.vel *= 0.992
        self.pos += self.vel * dt
        if mag(self.pos) > 13:
            self.vel += safe_norm(-self.pos) * 3.0 * dt
        self.obj.pos = self.pos
        self.obj.opacity = clamp(self.life / 2.0, 0, 1)
        return self.life > 0

    def delete(self):
        self.obj.visible = False
        self.obj.clear_trail()
        del self.obj

class Atom:
    _next_id = 1

    def __init__(self, element, pos, vel=None):
        self.id = Atom._next_id
        Atom._next_id += 1
        self.element = element
        self.data = ELEMENT_DATA[element]
        self.pos = vector(pos)
        self.vel = vector(vel) if vel is not None else rand_vec(0.7)
        self.force = vector(0, 0, 0)
        self.angle = uniform(0, 2 * pi)
        self.spin = uniform(0.5, 1.8)
        self.marked = False
        self.selected = False
        self.attach_cooldown = uniform(0.0, 1.5)
        self.molecule_name = ""
        self.molecule_group = None

        self.radius = self.data["radius"]
        self.desired_bonds = self.data["desired_bonds"]

        self.nucleus = sphere(
            pos=self.pos,
            radius=self.data["nucleus_radius"],
            color=self.data["color"],
            opacity=0.95,
            shininess=0.5,
        )

        self.shell = sphere(
            pos=self.pos,
            radius=self.radius,
            color=color_mix(self.data["color"], vector(0.75, 0.9, 1.0), 0.35),
            opacity=0.16,
        )

        self.label = label(
            pos=self.pos + vector(0, self.radius + 0.32, 0),
            text=element,
            color=vector(0.08, 0.10, 0.12),
            height=15,
            box=False,
            opacity=0,
        )

        self.nucleons = []
        self.electrons = []

        self._make_nucleus_particles()
        self._make_electrons()

    def _make_nucleus_particles(self):
        total = min(self.data["protons"] + self.data["neutrons"], 16)
        protons = min(self.data["protons"], total)
        for i in range(total):
            a = i * 2.399
            r = 0.11 + 0.028 * (i % 4)
            z = ((i % 5) - 2) * 0.035
            offset = vector(r * cos(a), r * sin(a), z)
            c = COLORS["proton"] if i < protons else COLORS["neutron"]
            obj = sphere(
                pos=self.pos + offset,
                radius=0.045 if self.element == "H" else 0.040,
                color=c,
                opacity=0.96,
            )
            self.nucleons.append((obj, offset))

    def _make_electrons(self):
        count = min(self.data["electrons"], 8)
        for i in range(count):
            orbital_radius = self.radius * (0.95 + 0.08 * (i % 2))
            phase = (2 * pi * i / max(1, count)) + uniform(-0.2, 0.2)
            tilt = (i % 3) * pi / 3.0
            obj = sphere(
                pos=self.pos,
                radius=0.052 if self.element == "H" else 0.045,
                color=COLORS["electron"],
                emissive=True,
                opacity=0.95,
            )
            self.electrons.append({
                "obj": obj,
                "phase": phase,
                "orbital_radius": orbital_radius,
                "tilt": tilt,
                "shared_with": None,
            })

    @property
    def bond_count(self):
        count = 0
        for b in bonds:
            if b.a is self or b.b is self:
                count += b.order
        return count

    @property
    def free_slots(self):
        return max(0, self.desired_bonds - self.bond_count)

    def can_bond_with(self, other):
        if other is self:
            return False
        if self.free_slots <= 0 or other.free_slots <= 0:
            return False
        if get_bond(self, other) is not None:
            return False

        pair = "".join(sorted([self.element, other.element]))
        valid_pairs = {"HO", "CO", "OO", "CH", "HH"}
        if pair not in valid_pairs:
            return False

        # H-H allowed only when both are isolated, to form H2-like temporary pair.
        if pair == "HH":
            return self.bond_count == 0 and other.bond_count == 0

        return True

    def apply_force(self, force):
        self.force += force

    def nudge_toward(self, target, strength=1.0):
        self.apply_force(safe_norm(target - self.pos) * strength)

    def update_physics(self, dt):
        self.attach_cooldown = max(0.0, self.attach_cooldown - dt)
        accel = self.force / max(1.0, self.data["mass"] * 0.25)
        self.vel += accel * dt
        self.vel *= 0.985
        self.pos += self.vel * dt
        self.force = vector(0, 0, 0)

        # Soft wall/boundary.
        boundary = 10.0
        if mag(self.pos) > boundary:
            inward = safe_norm(-self.pos)
            self.vel += inward * 2.6 * dt
            self.pos = safe_norm(self.pos) * min(mag(self.pos), boundary + 0.2)

    def update_visuals(self, t):
        self.angle += self.spin * 0.035
        self.nucleus.pos = self.pos
        self.shell.pos = self.pos
        self.label.pos = self.pos + vector(0, self.radius + 0.32, 0)

        if self.selected:
            self.shell.opacity = 0.30 + 0.08 * sin(t * 8)
            self.shell.color = COLORS["mark"]
        elif self.marked:
            self.shell.opacity = 0.25 + 0.05 * sin(t * 5)
            self.shell.color = color_mix(self.data["color"], COLORS["mark"], 0.45)
        else:
            self.shell.opacity = 0.16
            self.shell.color = color_mix(self.data["color"], vector(0.75, 0.9, 1.0), 0.35)

        for i, (obj, offset) in enumerate(self.nucleons):
            rot = vector(
                offset.x * cos(self.angle * 0.3) - offset.z * sin(self.angle * 0.3),
                offset.y,
                offset.x * sin(self.angle * 0.3) + offset.z * cos(self.angle * 0.3),
            )
            obj.pos = self.pos + rot

        for i, e in enumerate(self.electrons):
            if e["shared_with"] is not None and get_bond(self, e["shared_with"]) is not None:
                other = e["shared_with"]
                mid = (self.pos + other.pos) * 0.5
                dir_ab = safe_norm(other.pos - self.pos)
                side = vector(-dir_ab.y, dir_ab.x, 0)
                if mag(side) < 0.1:
                    side = vector(0, 1, 0)
                pulse = 0.08 * sin(t * 7 + e["phase"])
                e["obj"].pos = mid + side * pulse
                e["obj"].radius = 0.060
                e["obj"].opacity = 1.0
            else:
                phase = e["phase"] + self.angle + t * (0.8 + 0.1 * i)
                rr = e["orbital_radius"]
                tilt = e["tilt"]
                x = rr * cos(phase)
                y = 0.18 * sin(phase * 0.5 + tilt)
                z = rr * sin(phase) * cos(tilt)
                e["obj"].pos = self.pos + vector(x, y, z)
                e["obj"].radius = 0.045 if self.element != "H" else 0.052
                e["obj"].opacity = 0.95

    def set_some_electrons_shared(self, other, count=1):
        available = [e for e in self.electrons if e["shared_with"] is None]
        for e in available[:count]:
            e["shared_with"] = other

    def clear_shared_with(self, other):
        for e in self.electrons:
            if e["shared_with"] is other:
                e["shared_with"] = None

    def delete(self):
        self.nucleus.visible = False
        self.shell.visible = False
        self.label.visible = False
        del self.nucleus
        del self.shell
        del self.label
        for obj, offset in self.nucleons:
            obj.visible = False
            del obj
        for e in self.electrons:
            e["obj"].visible = False
            del e["obj"]

class Bond:
    def __init__(self, a, b, order=1, molecule_name=""):
        self.a = a
        self.b = b
        self.order = order
        self.molecule_name = molecule_name
        self.age = 0.0
        self.stress = 0.0
        self.obj = cylinder(
            pos=a.pos,
            axis=b.pos - a.pos,
            radius=0.055 + 0.018 * (order - 1),
            color=COLORS["bond"],
            opacity=0.62,
        )
        self.halo = cylinder(
            pos=a.pos,
            axis=b.pos - a.pos,
            radius=0.11 + 0.02 * (order - 1),
            color=COLORS["shared"],
            opacity=0.12,
        )

    def update(self, dt, t):
        self.age += dt
        target_dist = desired_bond_distance(self.a, self.b)
        delta = self.b.pos - self.a.pos
        d = max(0.1, mag(delta))
        direction = delta / d

        # Spring-like bond force.
        stretch = d - target_dist
        force = direction * stretch * 7.0
        self.a.apply_force(force)
        self.b.apply_force(-force)
        self.stress = abs(stretch)

        # Mild orbital rotation for molecules.
        side = vector(-direction.y, direction.x, 0)
        if mag(side) > 0.01:
            side = norm(side)
            self.a.apply_force(side * 0.08 * sin(t + self.age))
            self.b.apply_force(-side * 0.08 * sin(t + self.age))

        self.obj.pos = self.a.pos
        self.obj.axis = self.b.pos - self.a.pos
        self.halo.pos = self.a.pos
        self.halo.axis = self.b.pos - self.a.pos
        pulse = 0.5 + 0.5 * sin(t * 5 + self.age)
        self.halo.opacity = 0.08 + 0.09 * pulse
        self.obj.color = color_mix(COLORS["bond"], COLORS["success"], clamp(self.age / 2.0, 0, 1) * 0.35)

    def delete(self):
        self.a.clear_shared_with(self.b)
        self.b.clear_shared_with(self.a)
        self.obj.visible = False
        self.halo.visible = False
        del self.obj
        del self.halo

# ------------------------------------------------------------
# Display panels
# ------------------------------------------------------------

title_label = label(
    pos=vector(0, 7.2, 0),
    text="Atoms bonding into molecules",
    height=22,
    color=vector(0.05, 0.08, 0.12),
    box=False,
    opacity=0,
)

status_label = label(
    pos=vector(-9.6, 6.2, 0),
    text="",
    height=12,
    color=vector(0.05, 0.08, 0.12),
    box=True,
    border=8,
    opacity=0.18,
    background=vector(1, 1, 1),
)

help_label = label(
    pos=vector(6.2, 5.9, 0),
    text="",
    height=10,
    color=vector(0.08, 0.08, 0.08),
    box=True,
    border=8,
    opacity=0.18,
    background=vector(1, 1, 1),
)

# ------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------

def desired_bond_distance(a, b):
    pair = "".join(sorted([a.element, b.element]))
    if pair == "HO":
        return 1.05
    if pair == "CO":
        return 1.25
    if pair == "OO":
        return 1.18
    if pair == "CH":
        return 1.08
    if pair == "HH":
        return 0.82
    return a.radius + b.radius + 0.25

def get_bond(a, b):
    for bond in bonds:
        if (bond.a is a and bond.b is b) or (bond.a is b and bond.b is a):
            return bond
    return None

def add_spark(pos, count=8, color=COLORS["mark"], strength=1.0):
    for _ in range(count):
        spark_particles.append(
            SparkParticle(
                pos=pos + rand_vec(0.05),
                vel=rand_vec(strength),
                color=color,
                radius=uniform(0.02, 0.05),
                life=uniform(0.5, 1.6),
            )
        )

def add_mark(pos, radius=0.38, color=COLORS["mark"], life=2.2):
    obj = sphere(pos=pos, radius=radius, color=color, opacity=0.18)
    marks.append({"obj": obj, "life": life, "max_life": life})

def clear_marks_and_sparks():
    for m in marks:
        m["obj"].visible = False
        del m["obj"]
    marks.clear()
    for s in spark_particles:
        s.delete()
    spark_particles.clear()

def clear_free_electrons():
    for e in free_electrons:
        e.delete()
    free_electrons.clear()

def clear_molecule_labels():
    for lb in molecule_labels:
        lb.visible = False
        del lb
    molecule_labels.clear()

# ------------------------------------------------------------
# Bonding and molecule recognition
# ------------------------------------------------------------

def create_bond(a, b, order=1):
    if get_bond(a, b) is not None:
        return None
    if not a.can_bond_with(b):
        return None

    # Special case: CO2 needs C=O style double bonds in simplified form.
    if {a.element, b.element} == {"C", "O"}:
        c_atom = a if a.element == "C" else b
        o_atom = b if a.element == "C" else a
        if c_atom.free_slots >= 2 and o_atom.free_slots >= 2:
            order = 2
        else:
            order = 1

    # But CH and OH should remain single.
    if "H" in (a.element, b.element):
        order = 1

    if a.free_slots < order or b.free_slots < order:
        order = min(a.free_slots, b.free_slots)
    if order <= 0:
        return None

    bond = Bond(a, b, order=order)
    bonds.append(bond)

    a.set_some_electrons_shared(b, order)
    b.set_some_electrons_shared(a, order)

    mid = (a.pos + b.pos) * 0.5
    add_spark(mid, count=10 + 5 * order, color=COLORS["shared"], strength=1.6)
    add_mark(mid, radius=0.35 + 0.06 * order, color=COLORS["success"], life=1.6)
    return bond

def detach_bond(bond, scatter=True):
    if bond not in bonds:
        return
    mid = (bond.a.pos + bond.b.pos) * 0.5
    add_spark(mid, count=16, color=COLORS["warning"], strength=2.6)
    add_mark(mid, radius=0.48, color=COLORS["warning"], life=1.5)
    if scatter:
        direction = safe_norm(bond.b.pos - bond.a.pos)
        bond.a.vel -= direction * uniform(0.5, 1.4)
        bond.b.vel += direction * uniform(0.5, 1.4)
    bond.delete()
    bonds.remove(bond)

def detach_random_bond():
    if not bonds:
        return False
    bond = choice(bonds)
    detach_bond(bond, scatter=True)
    return True

def component_for_atom(start):
    seen = set()
    stack = [start]
    while stack:
        atom = stack.pop()
        if atom in seen:
            continue
        seen.add(atom)
        for bond in bonds:
            if bond.a is atom and bond.b not in seen:
                stack.append(bond.b)
            if bond.b is atom and bond.a not in seen:
                stack.append(bond.a)
    return list(seen)

def all_components():
    comps = []
    seen = set()
    for atom in atoms:
        if atom in seen:
            continue
        comp = component_for_atom(atom)
        for a in comp:
            seen.add(a)
        comps.append(comp)
    return comps

def formula_for_component(comp):
    counts = {}
    for atom in comp:
        counts[atom.element] = counts.get(atom.element, 0) + 1
    # Common chemical ordering for this simplified scene.
    if counts == {"H": 2, "O": 1}:
        return "H2O"
    if counts == {"C": 1, "O": 2}:
        return "CO2"
    if counts == {"O": 2}:
        return "O2"
    if counts == {"C": 1, "H": 4}:
        return "CH4"
    if counts == {"H": 2}:
        return "H2"
    text = ""
    for key in ["C", "H", "O"]:
        if key in counts:
            text += key + (str(counts[key]) if counts[key] > 1 else "")
    return text or "atom"

def update_molecule_labels():
    clear_molecule_labels()
    for comp in all_components():
        if len(comp) < 2:
            continue
        formula = formula_for_component(comp)
        center = sum((a.pos for a in comp), vector(0, 0, 0)) / len(comp)
        is_target = formula in MOLECULE_TEMPLATES
        lb = label(
            pos=center + vector(0, 0.95, 0),
            text=formula,
            height=13 if is_target else 11,
            color=vector(0.03, 0.08, 0.10),
            box=True,
            border=5,
            opacity=0.15,
            background=COLORS["success"] if is_target else vector(1, 1, 1),
        )
        molecule_labels.append(lb)
        for atom in comp:
            atom.molecule_name = formula

def completed_target_molecules():
    completed = []
    for comp in all_components():
        formula = formula_for_component(comp)
        if formula in MOLECULE_TEMPLATES:
            # Require all atoms in this component to have enough bonds for their simple model.
            stable = True
            for atom in comp:
                if atom.element == "H" and atom.bond_count < 1:
                    stable = False
                if atom.element == "O" and formula != "O2" and atom.bond_count < 2:
                    stable = False
                if atom.element == "C" and formula == "CH4" and atom.bond_count < 4:
                    stable = False
                if atom.element == "C" and formula == "CO2" and atom.bond_count < 4:
                    stable = False
                if atom.element == "O" and formula == "O2" and atom.bond_count < 1:
                    stable = False
            if stable:
                completed.append(formula)
    return completed

# ------------------------------------------------------------
# Atom creation and reset
# ------------------------------------------------------------

def create_atom(element, pos, vel=None):
    atom = Atom(element, pos, vel)
    atoms.append(atom)
    return atom

def spawn_cloud():
    # Enough atoms to permit multiple molecules.
    recipe = ["O", "O", "O", "O", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H"]
    positions = []
    for i, element in enumerate(recipe):
        angle = 2 * pi * i / len(recipe)
        rad = 4.3 + uniform(-1.0, 1.0)
        pos = vector(rad * cos(angle), uniform(-1.2, 1.2), rad * sin(angle))
        positions.append(pos)
        vel = vector(-0.20 * cos(angle), uniform(-0.2, 0.2), -0.20 * sin(angle)) + rand_vec(0.35)
        create_atom(element, pos, vel)

def delete_all():
    global atoms, bonds
    for bond in list(bonds):
        bond.delete()
    bonds.clear()

    for atom in list(atoms):
        atom.delete()
    atoms.clear()

    clear_free_electrons()
    clear_marks_and_sparks()
    clear_molecule_labels()

def reset_round():
    global round_number
    round_number += 1
    delete_all()
    Atom._next_id = 1
    spawn_cloud()
    ai.reset_for_new_round()
    add_mark(vector(0, 0, 0), radius=0.8, color=COLORS["altar"], life=2.0)

# ------------------------------------------------------------
# AI controller
# ------------------------------------------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = AI_MODES[self.mode_index]
        self.mode_timer = 0.0
        self.mode_duration = 7.0
        self.action_timer = 0.0
        self.action_interval = 0.42
        self.speed = 1.0
        self.target_template = "H2O"
        self.last_signature = None
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.loop_delay = 4.0
        self.round_phase = "explore"
        self.ritual_angle = 0.0
        self.selected_atoms = []
        self.mood = "curious"
        self.state_changed_flash = 0.0

    def reset_for_new_round(self):
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.round_phase = "explore"
        self.target_template = choice(list(MOLECULE_TEMPLATES.keys()))
        self.selected_atoms = []
        self.clear_selection()
        self.last_signature = None
        self.mode = choice(["CURIOUS", "CAREFUL", "CONSTRUCTIVE", "RITUAL"])
        self.mode_index = AI_MODES.index(self.mode)
        self.mode_duration = uniform(5.5, 9.5)

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(AI_MODES)
        self.mode = AI_MODES[self.mode_index]
        self.mode_timer = 0.0
        self.state_changed_flash = 1.0
        add_mark(vector(0, 0, 0), radius=0.65, color=COLORS["mark"], life=1.5)

    def clear_selection(self):
        for atom in atoms:
            atom.selected = False
        self.selected_atoms = []

    def choose_mode_from_state(self, state):
        completed_count = len(state["completed"])
        free_slots = state["free_slots"]
        avg_speed = state["avg_speed"]
        bond_count = state["bond_count"]

        if self.stagnation_timer > 5.5 and bond_count > 0:
            return "DESTRUCTIVE"
        if self.stagnation_timer > 4.0 and bond_count == 0:
            return "CHAOTIC"
        if completed_count >= 3:
            return "ARTISTIC"
        if free_slots > 10 and avg_speed < 0.22:
            return "CHAOTIC"
        if completed_count == 0 and bond_count < 2:
            return choice(["CURIOUS", "CAREFUL", "RITUAL"])
        if bond_count >= 2:
            return choice(["CONSTRUCTIVE", "CAREFUL", "ARTISTIC"])
        return choice(["CURIOUS", "CONSTRUCTIVE", "RITUAL"])

    def read_state(self):
        total_free_slots = sum(atom.free_slots for atom in atoms)
        avg_speed = sum(mag(atom.vel) for atom in atoms) / max(1, len(atoms))
        completed = completed_target_molecules()
        comps = all_components()
        signature = (
            len(atoms),
            len(bonds),
            tuple(sorted(completed)),
            round(avg_speed, 2),
            total_free_slots,
        )
        return {
            "atom_count": len(atoms),
            "bond_count": len(bonds),
            "free_slots": total_free_slots,
            "avg_speed": avg_speed,
            "completed": completed,
            "components": comps,
            "signature": signature,
        }

    def update_stagnation(self, dt, state):
        changing = state["signature"] != self.last_signature
        moving = state["avg_speed"] > 0.08
        if changing or moving:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 0.5)
        else:
            self.stagnation_timer += dt

        self.last_signature = state["signature"]

        if len(state["completed"]) >= 3:
            self.completion_timer += dt
        elif len(state["completed"]) >= 2 and state["free_slots"] <= 3:
            self.completion_timer += dt * 0.6
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt)

    def update(self, dt, t):
        if not self.enabled or paused:
            return

        state = self.read_state()
        self.update_stagnation(dt, state)

        # Automatic loop when complete or halted.
        if self.completion_timer > self.loop_delay:
            reset_round()
            return

        if self.stagnation_timer > 9.5:
            reset_round()
            return

        self.mode_timer += dt
        self.action_timer -= dt * self.speed
        self.state_changed_flash = max(0.0, self.state_changed_flash - dt)

        if self.mode_timer > self.mode_duration:
            self.mode = self.choose_mode_from_state(state)
            self.mode_index = AI_MODES.index(self.mode)
            self.mode_timer = 0.0
            self.mode_duration = uniform(5.5, 11.0)
            self.state_changed_flash = 1.0
            self.clear_selection()
            add_mark(vector(0, 0, 0), radius=0.52, color=COLORS["mark"], life=1.2)

        # Continuous behavior.
        self.apply_continuous_forces(dt, t, state)

        # Discrete actions.
        if self.action_timer <= 0:
            self.action_timer = self.action_interval
            self.take_action(state, t)

    def apply_continuous_forces(self, dt, t, state):
        if self.mode == "RITUAL":
            self.ritual_angle += dt * 0.7
            for i, atom in enumerate(atoms):
                target_angle = self.ritual_angle + i * 2 * pi / max(1, len(atoms))
                radius = 3.2 + 0.5 * sin(t * 0.5 + i)
                target = vector(radius * cos(target_angle), 0.7 * sin(t + i), radius * sin(target_angle))
                atom.nudge_toward(target, 0.55)

        elif self.mode == "ARTISTIC":
            comps = [c for c in state["components"] if len(c) >= 2]
            if comps:
                for ci, comp in enumerate(comps):
                    angle = t * 0.18 + ci * 2 * pi / max(1, len(comps))
                    center_target = vector(4.0 * cos(angle), 1.2 * sin(angle * 2), 4.0 * sin(angle))
                    center = sum((a.pos for a in comp), vector(0, 0, 0)) / len(comp)
                    for atom in comp:
                        atom.nudge_toward(atom.pos + (center_target - center), 0.42)
            for atom in atoms:
                if atom.bond_count == 0:
                    atom.nudge_toward(vector(0, -1.5, 0), 0.16)

        elif self.mode == "CHAOTIC":
            for atom in atoms:
                swirl = vector(-atom.pos.z, 0.3 * sin(t + atom.id), atom.pos.x)
                if mag(swirl) > 0.01:
                    atom.apply_force(norm(swirl) * 0.16)

        elif self.mode in ("CAREFUL", "CONSTRUCTIVE"):
            self.pull_target_partners(dt)

    def take_action(self, state, t):
        if not atoms:
            return

        if self.mode == "CURIOUS":
            self.action_curious()
        elif self.mode == "CAREFUL":
            self.action_careful()
        elif self.mode == "CONSTRUCTIVE":
            self.action_constructive()
        elif self.mode == "CHAOTIC":
            self.action_chaotic()
        elif self.mode == "RITUAL":
            self.action_ritual()
        elif self.mode == "ARTISTIC":
            self.action_artistic()
        elif self.mode == "DESTRUCTIVE":
            self.action_destructive()

    def find_best_pair(self):
        candidates = []
        for i, a in enumerate(atoms):
            for b in atoms[i + 1:]:
                if a.can_bond_with(b):
                    pair_score = 0.0
                    pair = "".join(sorted([a.element, b.element]))
                    if pair in ("HO", "CO", "CH", "OO"):
                        pair_score += 3.0
                    pair_score += 2.0 / max(0.35, distance(a.pos, b.pos))
                    pair_score += 0.4 * (a.free_slots + b.free_slots)
                    candidates.append((pair_score, a, b))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], candidates[0][2]

    def try_bond_nearby(self, max_distance=1.55):
        best = self.find_best_pair()
        if best is None:
            return False
        a, b = best
        d = distance(a.pos, b.pos)
        if d < max_distance:
            create_bond(a, b)
            return True
        midpoint = (a.pos + b.pos) * 0.5
        a.nudge_toward(midpoint, 5.0)
        b.nudge_toward(midpoint, 5.0)
        a.selected = True
        b.selected = True
        self.selected_atoms = [a, b]
        add_mark(midpoint, radius=0.22, color=COLORS["field"], life=0.8)
        return False

    def pull_target_partners(self, dt):
        best = self.find_best_pair()
        if best is None:
            return
        a, b = best
        midpoint = (a.pos + b.pos) * 0.5
        a.nudge_toward(midpoint, 0.65)
        b.nudge_toward(midpoint, 0.65)

    def action_curious(self):
        self.clear_selection()
        self.try_bond_nearby(max_distance=1.65)
        if random() < 0.25:
            atom = choice(atoms)
            atom.marked = not atom.marked
            add_mark(atom.pos, radius=atom.radius * 1.1, color=COLORS["mark"], life=1.0)

    def action_careful(self):
        self.clear_selection()

        # Select a molecule template and assemble atoms toward geometric positions.
        if random() < 0.18 or self.target_template not in MOLECULE_TEMPLATES:
            self.target_template = choice(list(MOLECULE_TEMPLATES.keys()))

        self.arrange_template(self.target_template)
        self.try_bond_nearby(max_distance=1.45)

    def action_constructive(self):
        self.clear_selection()
        # Prefer completing common molecules.
        for target in ["H2O", "CO2", "CH4", "O2"]:
            if self.has_available_atoms_for(target):
                self.target_template = target
                self.arrange_template(target)
                self.try_bond_nearby(max_distance=1.58)
                return
        self.try_bond_nearby(max_distance=1.75)

    def action_chaotic(self):
        self.clear_selection()
        for atom in atoms:
            atom.vel += rand_vec(0.7)
        if random() < 0.55:
            self.spill_electrons(count=randint(3, 8))
        if random() < 0.35:
            self.try_bond_nearby(max_distance=1.9)
        add_mark(rand_vec(2.5), radius=0.35, color=COLORS["warning"], life=0.9)

    def action_ritual(self):
        self.clear_selection()
        center = vector(0, 0, 0)
        for atom in atoms:
            atom.nudge_toward(center, 0.38)
        if random() < 0.7:
            self.try_bond_nearby(max_distance=1.7)
        add_mark(center, radius=0.42 + random() * 0.3, color=COLORS["altar"], life=1.1)

    def action_artistic(self):
        # Highlight complete molecules and leave soft marks.
        comps = all_components()
        complete_comps = [c for c in comps if formula_for_component(c) in MOLECULE_TEMPLATES]
        if complete_comps:
            comp = choice(complete_comps)
            center = sum((a.pos for a in comp), vector(0, 0, 0)) / len(comp)
            add_mark(center, radius=0.60, color=COLORS["success"], life=1.4)
            for atom in comp:
                atom.marked = True
        else:
            self.try_bond_nearby(max_distance=1.6)

    def action_destructive(self):
        self.clear_selection()
        if random() < 0.75:
            if not detach_random_bond():
                for atom in atoms:
                    atom.vel += rand_vec(0.6)
        if random() < 0.45:
            self.spill_electrons(count=randint(2, 6))

    def has_available_atoms_for(self, formula):
        required = {}
        for el in MOLECULE_TEMPLATES[formula]:
            required[el] = required.get(el, 0) + 1
        available = {}
        for atom in atoms:
            if atom.free_slots > 0 or atom.bond_count == 0:
                available[atom.element] = available.get(atom.element, 0) + 1
        return all(available.get(el, 0) >= count for el, count in required.items())

    def choose_atoms_for_template(self, formula):
        needed = MOLECULE_TEMPLATES[formula]
        chosen = []
        used = set()
        for el in needed:
            candidates = [a for a in atoms if a.element == el and a not in used and (a.free_slots > 0 or a.bond_count == 0)]
            if not candidates:
                return []
            # Choose candidates nearest origin for stable assembly.
            candidates.sort(key=lambda a: mag(a.pos))
            selected = candidates[0]
            chosen.append(selected)
            used.add(selected)
        return chosen

    def arrange_template(self, formula):
        chosen = self.choose_atoms_for_template(formula)
        if not chosen:
            return

        center = vector(0, 0, 0)
        offsets = []
        if formula == "H2O":
            # O in center, H atoms at bent water shape.
            offsets = [vector(0, 0, 0), vector(-1.0, 0.55, 0), vector(1.0, 0.55, 0)]
        elif formula == "CO2":
            offsets = [vector(0, 0, 0), vector(-1.35, 0, 0), vector(1.35, 0, 0)]
        elif formula == "O2":
            offsets = [vector(-0.65, 0, 0), vector(0.65, 0, 0)]
        elif formula == "CH4":
            offsets = [
                vector(0, 0, 0),
                vector(1.05, 0.80, 0.80),
                vector(-1.05, 0.80, -0.80),
                vector(0.80, -0.95, -0.80),
                vector(-0.80, -0.95, 0.80),
            ]
        else:
            for i in range(len(chosen)):
                offsets.append(vector(cos(i), sin(i), 0))

        # Put the target assembly slightly different per round to avoid visual sameness.
        round_offset = vector(0.8 * sin(round_number), 0, 0.8 * cos(round_number * 0.7))
        for atom, offset in zip(chosen, offsets):
            target = center + round_offset + offset
            atom.nudge_toward(target, 2.1)
            atom.selected = True
        self.selected_atoms = chosen
        add_mark(center + round_offset, radius=0.45, color=COLORS["field"], life=0.8)

    def spill_electrons(self, count=5):
        for _ in range(count):
            owner = choice(atoms) if atoms else None
            if owner is not None:
                pos = owner.pos + rand_vec(owner.radius * 1.4)
                vel = rand_vec(2.0) + owner.vel
            else:
                pos = rand_vec(3.0)
                vel = rand_vec(2.0)
            free_electrons.append(FreeElectron(pos=pos, vel=vel, owner=owner))

# AI created before reset_round so reset can call it.
ai = AIController()

# ------------------------------------------------------------
# Simulation physics
# ------------------------------------------------------------

def apply_atom_interactions(dt):
    # Collision, repulsion, and possible bonding.
    for i, a in enumerate(atoms):
        for b in atoms[i + 1:]:
            delta = b.pos - a.pos
            d = max(0.05, mag(delta))
            direction = delta / d
            min_dist = a.radius + b.radius + 0.12

            # Soft collision repulsion.
            if d < min_dist:
                overlap = min_dist - d
                push = direction * overlap * 5.5
                a.apply_force(-push)
                b.apply_force(push)

                # Visual collision mark.
                if random() < 0.025:
                    add_spark((a.pos + b.pos) * 0.5, count=3, color=COLORS["field"], strength=0.6)

            # Bonding opportunity after collision/near collision.
            if d < desired_bond_distance(a, b) + 0.28 and a.attach_cooldown <= 0 and b.attach_cooldown <= 0:
                if a.can_bond_with(b):
                    # Probability increased when moving slowly enough to "settle".
                    relative_speed = mag(a.vel - b.vel)
                    chance = clamp(0.18 + (0.35 - relative_speed) * 0.25, 0.05, 0.45)
                    if random() < chance:
                        create_bond(a, b)
                        a.attach_cooldown = 0.8
                        b.attach_cooldown = 0.8

            # Weak attraction between compatible atoms.
            if a.can_bond_with(b) and d < 3.0:
                attraction = direction * (0.08 / max(0.35, d))
                a.apply_force(attraction)
                b.apply_force(-attraction)

def update_marks(dt):
    for m in list(marks):
        m["life"] -= dt
        frac = max(0.0, m["life"] / m["max_life"])
        m["obj"].opacity = 0.18 * frac
        m["obj"].radius *= 1.0 + 0.10 * dt
        if m["life"] <= 0:
            m["obj"].visible = False
            del m["obj"]
            marks.remove(m)

def update_free_electrons(dt):
    for e in list(free_electrons):
        if not e.update(dt):
            e.delete()
            free_electrons.remove(e)

def update_sparks(dt):
    for s in list(spark_particles):
        if not s.update(dt):
            s.delete()
            spark_particles.remove(s)

def stabilize_molecules(dt):
    # Dampen bonded components so completed molecules can settle without freezing.
    for comp in all_components():
        if len(comp) < 2:
            continue
        formula = formula_for_component(comp)
        center = sum((a.pos for a in comp), vector(0, 0, 0)) / len(comp)
        avg_vel = sum((a.vel for a in comp), vector(0, 0, 0)) / len(comp)

        if formula in MOLECULE_TEMPLATES:
            for atom in comp:
                atom.vel = lerp_vec(atom.vel, avg_vel, 0.018)
                atom.apply_force((center - atom.pos) * 0.012)

def update_status():
    completed = completed_target_molecules()
    help_text = (
        "Controls\\n"
        "A AI on/off   P pause   R reset\\n"
        "M mode        O override spill\\n"
        "D detach      C clear marks\\n"
        "+/- AI speed  H help"
    )
    help_label.text = help_text if show_help else "H show controls"

    mode_text = ai.mode
    status_label.text = (
        f"Round: {round_number}\\n"
        f"AI: {'ON' if ai.enabled else 'OFF'} | Mode: {mode_text} | Speed: {ai.speed:.1f}x\\n"
        f"Atoms: {len(atoms)} | Bonds: {len(bonds)} | Free e⁻: {len(free_electrons)}\\n"
        f"Completed: {', '.join(completed) if completed else 'none'}\\n"
        f"Stagnation: {ai.stagnation_timer:.1f}s | Loop: {ai.completion_timer:.1f}s"
    )

# ------------------------------------------------------------
# Human keyboard control
# ------------------------------------------------------------

def human_override():
    for atom in atoms:
        atom.vel += rand_vec(0.35)
    ai.spill_electrons(count=10)
    add_mark(vector(0, 0, 0), radius=0.7, color=COLORS["warning"], life=1.2)

def print_controls():
    print(__doc__)

def keydown(evt):
    global paused, show_help
    key = evt.key.lower()

    if key == "a":
        ai.enabled = not ai.enabled
        add_mark(vector(0, 0, 0), radius=0.6, color=COLORS["mark"], life=1.0)
    elif key == "p":
        paused = not paused
    elif key == "r":
        reset_round()
    elif key == "m":
        ai.cycle_mode()
    elif key == "o":
        human_override()
    elif key == "d":
        detach_random_bond()
    elif key == "c":
        clear_marks_and_sparks()
    elif key in ["+", "="]:
        ai.speed = clamp(ai.speed + 0.2, 0.2, 4.0)
    elif key in ["-", "_"]:
        ai.speed = clamp(ai.speed - 0.2, 0.2, 4.0)
    elif key == "h":
        show_help = not show_help
        print_controls()

scene.bind("keydown", keydown)

# ------------------------------------------------------------
# Ground/reference objects
# ------------------------------------------------------------

ground = box(
    pos=vector(0, -2.15, 0),
    size=vector(18, 0.04, 18),
    color=vector(0.91, 0.94, 0.97),
    opacity=0.45,
)

altar_ring_outer = ring(
    pos=vector(0, -2.08, 0),
    axis=vector(0, 1, 0),
    radius=2.8,
    thickness=0.025,
    color=COLORS["altar"],
    opacity=0.55,
)

altar_ring_inner = ring(
    pos=vector(0, -2.06, 0),
    axis=vector(0, 1, 0),
    radius=1.35,
    thickness=0.018,
    color=vector(0.76, 0.84, 1.0),
    opacity=0.45,
)

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

def main():
    global paused
    print("Atoms Bonding into Molecules simulation loaded.")
    print("Press H in the VPython window for controls.")
    reset_round()

    t = 0.0
    molecule_label_timer = 0.0

    while True:
        rate(60)
        dt = 1.0 / 60.0
        t += dt

        if not paused:
            # AI may call reset_round internally.
            ai.update(dt, t)

            for bond in list(bonds):
                bond.update(dt, t)

            apply_atom_interactions(dt)
            stabilize_molecules(dt)

            for atom in atoms:
                atom.update_physics(dt)

            update_free_electrons(dt)
            update_sparks(dt)
            update_marks(dt)

        # Visuals always update, even when paused.
        for atom in atoms:
            atom.update_visuals(t)

        altar_ring_outer.rotate(angle=0.0025, axis=vector(0, 1, 0))
        altar_ring_inner.rotate(angle=-0.0035, axis=vector(0, 1, 0))

        molecule_label_timer += dt
        if molecule_label_timer > 0.45:
            molecule_label_timer = 0.0
            update_molecule_labels()

        update_status()

if __name__ == "__main__":
    main()
