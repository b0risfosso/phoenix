#!/usr/bin/env python3
"""
Covalent Bond Formation — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python covalent_bond_formation_ai_simulation.py

Keyboard controls:
    H       print controls
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset round
    M       cycle AI behavior mode
    N       spawn a free atom
    B       request bond-building pulse
    D       detach the most strained or newest bond
    S       spill electron particles
    O       human override: attraction/organization pulse
    C       clear temporary marks/sparks
    1-6     select target molecule template:
            1 H2, 2 O2, 3 H2O, 4 CO2, 5 CH4, 6 NH3
    + / =   increase AI speed
    - / _   decrease AI speed

Simulation concept:
    Atoms drift through a light 3D space. Valence electrons orbit their atoms. When atoms
    approach with available valence capacity, the simulation creates shared electron pairs,
    draws covalent bonds, shows bond labels, stabilizes geometry, and displays lone pairs,
    molecular geometry, and bond angles. The AI controller reads simulation state and can
    organize, collide, attach, detach, orbit, mark, spill, wrap, reset, and loop the scene.

Notes:
    This is an educational, stylized model rather than a quantum-chemical solver.
    It uses VPython primitives only and avoids torus() for compatibility.
"""

from vpython import *
from math import sin, cos, pi, sqrt, atan2, acos
from random import random, uniform, choice, shuffle

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Covalent Bond Formation — AI Controlled 3D VPython Simulation",
    width=1280,
    height=760,
    background=vector(0.96, 0.985, 1.0),
    center=vector(0, 0, 0),
)
scene.range = 9.5
scene.forward = vector(-0.45, -0.28, -1.0)
scene.up = vector(0, 1, 0)

# Light styling.
scene.ambient = color.gray(0.78)
distant_light(direction=vector(-1, -1, -1), color=color.white)
distant_light(direction=vector(1, 0.7, 0.5), color=vector(0.75, 0.8, 1.0))

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-9:
        return fallback
    return norm(v)


def rand_vec(scale=1.0):
    return vector(uniform(-scale, scale), uniform(-scale, scale), uniform(-scale, scale))


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def angle_between(a, b):
    ma = mag(a)
    mb = mag(b)
    if ma < 1e-9 or mb < 1e-9:
        return 0.0
    c = clamp(dot(a, b) / (ma * mb), -1.0, 1.0)
    return acos(c) * 180.0 / pi


def rotate_y(v, ang):
    return vector(v.x * cos(ang) + v.z * sin(ang), v.y, -v.x * sin(ang) + v.z * cos(ang))


def set_visible(obj, visible=True):
    try:
        obj.visible = visible
    except Exception:
        pass


def make_label(text, pos, height=11, color_value=vector(0.15, 0.16, 0.20), box=False, opacity=0.0):
    return label(
        pos=pos,
        text=text,
        height=height,
        color=color_value,
        box=box,
        opacity=opacity,
        border=4,
    )


def delete_visual(obj):
    if obj is None:
        return
    if isinstance(obj, (list, tuple)):
        for item in obj:
            delete_visual(item)
        return
    try:
        obj.visible = False
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Chemical metadata: valence capacity and rough visual style
# ---------------------------------------------------------------------------

ELEMENTS = {
    "H": {
        "name": "Hydrogen",
        "valence": 1,
        "radius": 0.30,
        "atomic_radius": 0.65,
        "color": vector(0.96, 0.97, 1.0),
        "edge": vector(0.42, 0.48, 0.58),
        "electrons": 1,
        "mass": 1.0,
    },
    "C": {
        "name": "Carbon",
        "valence": 4,
        "radius": 0.46,
        "atomic_radius": 0.88,
        "color": vector(0.18, 0.23, 0.28),
        "edge": vector(0.08, 0.10, 0.12),
        "electrons": 4,
        "mass": 12.0,
    },
    "N": {
        "name": "Nitrogen",
        "valence": 3,
        "radius": 0.43,
        "atomic_radius": 0.82,
        "color": vector(0.30, 0.45, 0.96),
        "edge": vector(0.12, 0.18, 0.45),
        "electrons": 5,
        "mass": 14.0,
    },
    "O": {
        "name": "Oxygen",
        "valence": 2,
        "radius": 0.44,
        "atomic_radius": 0.80,
        "color": vector(1.0, 0.28, 0.24),
        "edge": vector(0.50, 0.10, 0.10),
        "electrons": 6,
        "mass": 16.0,
    },
    "F": {
        "name": "Fluorine",
        "valence": 1,
        "radius": 0.40,
        "atomic_radius": 0.74,
        "color": vector(0.60, 0.96, 0.42),
        "edge": vector(0.18, 0.42, 0.12),
        "electrons": 7,
        "mass": 19.0,
    },
    "Cl": {
        "name": "Chlorine",
        "valence": 1,
        "radius": 0.50,
        "atomic_radius": 0.98,
        "color": vector(0.48, 0.86, 0.28),
        "edge": vector(0.18, 0.38, 0.08),
        "electrons": 7,
        "mass": 35.0,
    },
}

TEMPLATES = {
    "H2": ["H", "H"],
    "O2": ["O", "O"],
    "H2O": ["O", "H", "H"],
    "CO2": ["C", "O", "O"],
    "CH4": ["C", "H", "H", "H", "H"],
    "NH3": ["N", "H", "H", "H"],
}

TEMPLATE_ORDER = ["H2", "O2", "H2O", "CO2", "CH4", "NH3"]

# Idealized local geometries for central atoms. Directions are normalized.
GEOMETRY_DIRECTIONS = {
    "linear": [
        vector(1, 0, 0),
        vector(-1, 0, 0),
    ],
    "bent": [
        safe_norm(vector(0.94, 0.32, 0.0)),
        safe_norm(vector(-0.38, 0.92, 0.0)),
    ],
    "trigonal_pyramidal": [
        safe_norm(vector(0.92, -0.18, 0.0)),
        safe_norm(vector(-0.46, -0.18, 0.80)),
        safe_norm(vector(-0.46, -0.18, -0.80)),
    ],
    "tetrahedral": [
        safe_norm(vector(1, 1, 1)),
        safe_norm(vector(1, -1, -1)),
        safe_norm(vector(-1, 1, -1)),
        safe_norm(vector(-1, -1, 1)),
    ],
}

# ---------------------------------------------------------------------------
# Visual structures
# ---------------------------------------------------------------------------

class Spark:
    def __init__(self, pos, vel, color_value, radius=0.045, life=1.2, trail=False):
        self.life = life
        self.max_life = life
        self.vel = vel
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=color_value,
            emissive=True,
            opacity=0.78,
            make_trail=trail,
            retain=18,
            trail_radius=0.008,
        )

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.obj.pos += self.vel * dt
        self.obj.opacity = clamp(self.life / self.max_life, 0, 1) * 0.78
        self.obj.radius *= 0.997
        if self.life <= 0:
            delete_visual(self.obj)
            return False
        return True


class Marker:
    def __init__(self, pos, text, color_value=vector(0.2, 0.25, 0.35), life=2.0):
        self.life = life
        self.max_life = life
        self.label = make_label(text, pos, height=10, color_value=color_value, box=True, opacity=0.12)

    def update(self, dt):
        self.life -= dt
        self.label.pos.y += 0.17 * dt
        self.label.opacity = clamp(self.life / self.max_life, 0, 1) * 0.12
        if self.life <= 0:
            delete_visual(self.label)
            return False
        return True


class BondAngleVisual:
    def __init__(self, central_atom, atom_a, atom_b):
        self.central = central_atom
        self.a = atom_a
        self.b = atom_b
        self.curve = curve(radius=0.018, color=vector(0.24, 0.48, 0.82), opacity=0.55)
        self.label = make_label("", vector(0, 0, 0), height=9, color_value=vector(0.18, 0.26, 0.38), box=False)
        self.update()

    def update(self):
        c = self.central.pos
        va = safe_norm(self.a.pos - c)
        vb = safe_norm(self.b.pos - c)
        deg = angle_between(va, vb)
        # Use simple interpolation along normalized vectors for arc-like guide.
        pts = []
        for i in range(18):
            t = i / 17.0
            d = safe_norm(lerp_vec(va, vb, t), va)
            pts.append(c + d * 0.85)
        self.curve.clear()
        for p in pts:
            self.curve.append(p)
        self.label.pos = c + safe_norm(va + vb, vector(0, 1, 0)) * 1.05 + vector(0, 0.12, 0)
        self.label.text = f"{deg:0.0f}°"

    def delete(self):
        delete_visual(self.curve)
        delete_visual(self.label)


class LonePair:
    def __init__(self, atom, index, direction):
        self.atom = atom
        self.index = index
        self.direction = safe_norm(direction)
        self.phase = uniform(0, 2 * pi)
        self.orbital = ellipsoid(
            pos=atom.pos + self.direction * (atom.radius + 0.48),
            length=0.42,
            height=0.19,
            width=0.19,
            axis=self.direction,
            color=vector(0.65, 0.70, 1.0),
            opacity=0.30,
        )
        self.e1 = sphere(
            pos=self.orbital.pos + vector(0.02, 0.02, 0),
            radius=0.055,
            color=vector(0.36, 0.44, 1.0),
            emissive=True,
        )
        self.e2 = sphere(
            pos=self.orbital.pos - vector(0.02, 0.02, 0),
            radius=0.055,
            color=vector(0.36, 0.44, 1.0),
            emissive=True,
        )

    def update(self, dt):
        self.phase += 3.4 * dt
        spin = vector(0.05 * cos(self.phase), 0.04 * sin(self.phase), 0.04 * cos(self.phase * 0.7))
        center = self.atom.pos + self.direction * (self.atom.radius + 0.50)
        self.orbital.pos = center
        self.orbital.axis = self.direction
        self.e1.pos = center + spin
        self.e2.pos = center - spin

    def delete(self):
        delete_visual([self.orbital, self.e1, self.e2])


class ValenceElectron:
    def __init__(self, atom, index):
        self.atom = atom
        self.index = index
        self.phase = 2 * pi * index / max(1, atom.visible_electron_count)
        self.free = True
        self.shared_bond = None
        self.obj = sphere(
            pos=atom.pos,
            radius=0.055,
            color=vector(0.28, 0.34, 1.0),
            emissive=True,
            make_trail=False,
        )

    def update(self, dt):
        if self.shared_bond:
            return
        a = self.atom
        self.phase += (1.9 + 0.05 * self.index) * dt
        orbit_r = a.radius + 0.40 + 0.06 * (self.index % 2)
        tilt = 0.55 + 0.2 * sin(self.index)
        local = vector(
            orbit_r * cos(self.phase),
            orbit_r * sin(self.phase) * tilt,
            orbit_r * sin(self.phase + self.index * 0.7) * 0.32,
        )
        self.obj.pos = a.pos + local

    def attach_to_bond(self, bond):
        self.free = False
        self.shared_bond = bond
        self.obj.color = vector(0.08, 0.28, 1.0)
        self.obj.radius = 0.065

    def detach_from_bond(self):
        self.free = True
        self.shared_bond = None
        self.obj.color = vector(0.28, 0.34, 1.0)
        self.obj.radius = 0.055

    def delete(self):
        delete_visual(self.obj)


class Atom:
    next_id = 1

    def __init__(self, symbol, pos, vel=None, fixed=False):
        self.id = Atom.next_id
        Atom.next_id += 1
        self.symbol = symbol
        self.meta = ELEMENTS[symbol]
        self.name = self.meta["name"]
        self.radius = self.meta["radius"]
        self.atomic_radius = self.meta["atomic_radius"]
        self.valence_capacity = self.meta["valence"]
        self.visible_electron_count = max(1, min(8, self.meta["electrons"]))
        self.mass = self.meta["mass"]
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vel if vel is not None else rand_vec(0.6)
        self.force = vector(0, 0, 0)
        self.fixed = fixed
        self.selected = False
        self.spin = uniform(0, 2 * pi)
        self.bonds = []
        self.target_slot = None
        self.marked = False

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.meta["color"],
            opacity=0.94,
            shininess=0.62,
            make_trail=True,
            retain=45,
            trail_radius=0.012,
            trail_color=self.meta["edge"],
        )
        self.shell = sphere(
            pos=self.pos,
            radius=self.atomic_radius,
            color=self.meta["color"],
            opacity=0.085,
        )
        self.outer = sphere(
            pos=self.pos,
            radius=self.radius * 1.05,
            color=self.meta["edge"],
            opacity=0.18,
        )
        self.label = make_label(symbol, self.pos + vector(0, self.radius + 0.32, 0), height=12, color_value=vector(0.06, 0.08, 0.10), box=False)
        self.electrons = [ValenceElectron(self, i) for i in range(self.visible_electron_count)]
        self.lone_pairs = []

    @property
    def open_slots(self):
        return max(0, self.valence_capacity - len(self.bonds))

    @property
    def bond_count(self):
        return len(self.bonds)

    def can_bond(self):
        return self.open_slots > 0

    def shared_electron_for_new_bond(self):
        for e in self.electrons:
            if e.free:
                return e
        return None

    def update(self, dt):
        if not self.fixed:
            self.vel += (self.force / max(1, self.mass)) * dt
            self.vel *= 0.992
            # Keep scene bounded with gentle bounce.
            bound = 7.2
            for axis_name in ("x", "y", "z"):
                val = getattr(self.pos, axis_name)
                vel = getattr(self.vel, axis_name)
                if val > bound:
                    setattr(self.pos, axis_name, bound)
                    setattr(self.vel, axis_name, -abs(vel) * 0.7)
                elif val < -bound:
                    setattr(self.pos, axis_name, -bound)
                    setattr(self.vel, axis_name, abs(vel) * 0.7)
            self.pos += self.vel * dt

        self.body.pos = self.pos
        self.shell.pos = self.pos
        self.outer.pos = self.pos
        self.label.pos = self.pos + vector(0, self.radius + 0.32, 0)
        self.force = vector(0, 0, 0)
        for e in self.electrons:
            e.update(dt)
        for lp in self.lone_pairs:
            lp.update(dt)

    def refresh_lone_pairs(self):
        for lp in self.lone_pairs:
            lp.delete()
        self.lone_pairs = []

        # Stylized lone pair count for common atoms:
        # O: 2 when two bonds, N: 1 when three bonds, halogens: 3 when one bond.
        lp_count = 0
        if self.symbol == "O":
            lp_count = max(0, 2 - max(0, self.bond_count - 2))
        elif self.symbol == "N":
            lp_count = 1 if self.bond_count >= 1 else 1
        elif self.symbol in ("F", "Cl"):
            lp_count = 3
        elif self.symbol == "C":
            lp_count = 0
        elif self.symbol == "H":
            lp_count = 0

        if lp_count <= 0:
            return

        bonded_dirs = [safe_norm(other_atom_from_bond(b, self).pos - self.pos) for b in self.bonds]
        base_dirs = [
            vector(0, 1, 0),
            vector(0, -1, 0),
            vector(0, 0, 1),
            vector(0, 0, -1),
            vector(1, 0, 0),
            vector(-1, 0, 0),
        ]

        candidates = []
        for d in base_dirs:
            score = 0
            for bd in bonded_dirs:
                score -= dot(d, bd)
            candidates.append((score, d))
        candidates.sort(reverse=True, key=lambda item: item[0])

        for i in range(lp_count):
            d = candidates[i % len(candidates)][1]
            if i > 0:
                d = safe_norm(rotate_y(d, i * 0.65) + vector(0, 0.15 * sin(i), 0))
            self.lone_pairs.append(LonePair(self, i, d))

    def delete(self):
        for e in self.electrons:
            e.delete()
        for lp in self.lone_pairs:
            lp.delete()
        delete_visual([self.body, self.shell, self.outer, self.label])


def other_atom_from_bond(bond, atom):
    return bond.b if bond.a == atom else bond.a


class Bond:
    next_id = 1

    def __init__(self, a, b, order=1, source="collision"):
        self.id = Bond.next_id
        Bond.next_id += 1
        self.a = a
        self.b = b
        self.order = order
        self.source = source
        self.age = 0.0
        self.ideal_length = a.radius + b.radius + 0.62
        self.strength = 1.0
        self.electron_phase = uniform(0, 2 * pi)
        self.visuals = []
        self.label = None
        self.shared_electrons = []
        self.create_visuals()
        self.assign_electrons()

        a.bonds.append(self)
        b.bonds.append(self)
        a.refresh_lone_pairs()
        b.refresh_lone_pairs()

    def create_visuals(self):
        self.visuals = []
        for i in range(self.order):
            cyl = cylinder(
                pos=self.a.pos,
                axis=self.b.pos - self.a.pos,
                radius=0.045,
                color=vector(0.42, 0.50, 0.62),
                opacity=0.60,
                shininess=0.25,
            )
            self.visuals.append(cyl)
        self.label = make_label(
            f"{self.a.symbol}—{self.b.symbol}",
            (self.a.pos + self.b.pos) * 0.5 + vector(0, 0.18, 0),
            height=9,
            color_value=vector(0.18, 0.22, 0.30),
            box=False,
        )

    def assign_electrons(self):
        ea = self.a.shared_electron_for_new_bond()
        eb = self.b.shared_electron_for_new_bond()
        for e in (ea, eb):
            if e is not None:
                e.attach_to_bond(self)
                self.shared_electrons.append(e)

    def update(self, dt):
        self.age += dt
        self.electron_phase += 4.4 * dt
        axis_vec = self.b.pos - self.a.pos
        mid = (self.a.pos + self.b.pos) * 0.5
        side = safe_norm(cross(axis_vec, vector(0, 1, 0)), vector(0, 0, 1))
        if mag(side) < 0.1:
            side = vector(0, 0, 1)

        offsets = [0]
        if self.order == 2:
            offsets = [-0.07, 0.07]
        elif self.order == 3:
            offsets = [-0.10, 0.0, 0.10]

        for i, cyl in enumerate(self.visuals):
            off = side * offsets[min(i, len(offsets) - 1)]
            cyl.pos = self.a.pos + off
            cyl.axis = axis_vec
            cyl.radius = 0.045 + 0.008 * sin(self.age * 5.0 + i)
            if self.source == "ai":
                cyl.color = vector(0.28, 0.54, 0.90)
            else:
                cyl.color = vector(0.42, 0.50, 0.62)

        if self.label:
            self.label.pos = mid + vector(0, 0.25, 0)
            stretch = mag(axis_vec) / max(0.01, self.ideal_length)
            if stretch > 1.55:
                self.label.text = f"{self.a.symbol}—{self.b.symbol} strain"
                self.label.color = vector(0.82, 0.20, 0.18)
            else:
                self.label.text = f"{self.a.symbol}—{self.b.symbol}"

        # Move two shared electrons as an animated pair between atoms.
        for i, e in enumerate(self.shared_electrons):
            phase = self.electron_phase + i * pi
            offset = side * (0.12 * cos(phase)) + vector(0, 0.08 * sin(phase), 0)
            e.obj.pos = mid + offset

    def apply_force(self):
        axis_vec = self.b.pos - self.a.pos
        d = mag(axis_vec)
        if d < 1e-6:
            return
        direction = axis_vec / d
        stretch = d - self.ideal_length
        f = direction * (3.2 * stretch)
        if not self.a.fixed:
            self.a.force += f
        if not self.b.fixed:
            self.b.force -= f

    def delete(self):
        for e in self.shared_electrons:
            e.detach_from_bond()
        if self in self.a.bonds:
            self.a.bonds.remove(self)
        if self in self.b.bonds:
            self.b.bonds.remove(self)
        self.a.refresh_lone_pairs()
        self.b.refresh_lone_pairs()
        delete_visual(self.visuals)
        delete_visual(self.label)


# ---------------------------------------------------------------------------
# Molecule template and geometry helpers
# ---------------------------------------------------------------------------

def molecule_formula():
    counts = {}
    for atom in atoms:
        counts[atom.symbol] = counts.get(atom.symbol, 0) + 1
    parts = []
    for sym in ["C", "H", "N", "O", "F", "Cl"]:
        if sym in counts:
            n = counts[sym]
            parts.append(sym if n == 1 else f"{sym}{n}")
    return "".join(parts) if parts else "empty"


def infer_geometry(atom):
    if atom.symbol == "C" and atom.bond_count == 4:
        return "tetrahedral"
    if atom.symbol == "C" and atom.bond_count == 2:
        return "linear"
    if atom.symbol == "O" and atom.bond_count == 2:
        return "bent"
    if atom.symbol == "N" and atom.bond_count == 3:
        return "trigonal pyramidal"
    if atom.bond_count == 2:
        return "linear"
    if atom.bond_count == 1:
        return "diatomic / terminal"
    if atom.bond_count == 0:
        return "free atom"
    return "cluster"


def desired_template_edges(template_name):
    if template_name == "H2":
        return [(0, 1)]
    if template_name == "O2":
        return [(0, 1)]
    if template_name == "H2O":
        return [(0, 1), (0, 2)]          # O-H, O-H
    if template_name == "CO2":
        return [(0, 1), (0, 2)]          # C-O, C-O
    if template_name == "CH4":
        return [(0, 1), (0, 2), (0, 3), (0, 4)]
    if template_name == "NH3":
        return [(0, 1), (0, 2), (0, 3)]
    return []


def target_positions_for_template(template_name, center=vector(0, 0, 0)):
    symbols = TEMPLATES[template_name]
    positions = [center]
    if template_name == "H2":
        return [center + vector(-0.65, 0, 0), center + vector(0.65, 0, 0)]
    if template_name == "O2":
        return [center + vector(-0.78, 0, 0), center + vector(0.78, 0, 0)]
    if template_name == "CO2":
        return [center, center + vector(1.55, 0, 0), center + vector(-1.55, 0, 0)]
    if template_name == "H2O":
        return [center, center + vector(1.12, 0.22, 0), center + vector(-0.43, 1.07, 0)]
    if template_name == "NH3":
        dirs = GEOMETRY_DIRECTIONS["trigonal_pyramidal"]
        return [center] + [center + d * 1.35 for d in dirs]
    if template_name == "CH4":
        dirs = GEOMETRY_DIRECTIONS["tetrahedral"]
        return [center] + [center + d * 1.42 for d in dirs]
    return [center + rand_vec(1.5) for _ in symbols]


def find_atom_pair(a, b):
    for bond in bonds:
        if (bond.a == a and bond.b == b) or (bond.a == b and bond.b == a):
            return bond
    return None


def find_existing_bond(a, b):
    return find_atom_pair(a, b) is not None


def compatible_for_bond(a, b):
    if a == b:
        return False
    if find_existing_bond(a, b):
        return False
    if not a.can_bond() or not b.can_bond():
        return False
    # Avoid H becoming central with many bonds; open_slots already prevents.
    return True


# ---------------------------------------------------------------------------
# Global simulation state
# ---------------------------------------------------------------------------

atoms = []
bonds = []
sparks = []
markers = []
angle_visuals = []
molecule_label = None
geometry_label = None
status_label = None
ai_label = None
legend_label = None

paused = False
human_override_timer = 0.0
bond_pulse_timer = 0.0
selected_template = "H2O"
round_index = 0

# AI globals.
ai_enabled = True
ai_speed = 1.0
ai_mode_index = 0
ai_mode = "careful_builder"
ai_mode_timer = 0.0
ai_mode_duration = 6.5
ai_last_progress_value = 0
ai_stagnation_timer = 0.0
ai_completion_timer = 0.0
ai_reset_countdown = -1.0
ai_memory = {
    "last_pair": None,
    "curiosity_target": None,
    "ritual_angle": 0.0,
    "chaos_cooldown": 0.0,
}

AI_MODES = [
    "careful_builder",
    "curious_orbits",
    "collision_play",
    "geometry_teacher",
    "lone_pair_artist",
    "constructive_spill",
    "destructive_repair",
    "ritual_loop",
]


# ---------------------------------------------------------------------------
# Persistent UI
# ---------------------------------------------------------------------------

def create_static_ui():
    global molecule_label, geometry_label, status_label, ai_label, legend_label
    molecule_label = make_label("Molecule: --", vector(-7.8, 5.2, 0), height=14, color_value=vector(0.05, 0.08, 0.12), box=True, opacity=0.12)
    geometry_label = make_label("Geometry: --", vector(-7.8, 4.65, 0), height=12, color_value=vector(0.05, 0.08, 0.12), box=True, opacity=0.10)
    status_label = make_label("Status: --", vector(-7.8, 4.15, 0), height=12, color_value=vector(0.05, 0.08, 0.12), box=True, opacity=0.10)
    ai_label = make_label("AI: --", vector(-7.8, 3.65, 0), height=12, color_value=vector(0.05, 0.08, 0.12), box=True, opacity=0.10)
    legend_label = make_label(
        "A AI  |  P pause  |  R reset  |  M mode  |  N atom  |  B bond  |  D detach  |  S spill  |  1-6 template",
        vector(0, -5.45, 0),
        height=11,
        color_value=vector(0.16, 0.18, 0.22),
        box=True,
        opacity=0.08,
    )


# ---------------------------------------------------------------------------
# Simulation reset, spawn, cleanup
# ---------------------------------------------------------------------------

def clear_scene_objects():
    global atoms, bonds, sparks, markers, angle_visuals
    for av in angle_visuals:
        av.delete()
    angle_visuals = []
    for b in list(bonds):
        b.delete()
    bonds = []
    for a in atoms:
        a.delete()
    atoms = []
    for s in sparks:
        delete_visual(s.obj)
    sparks = []
    for m in markers:
        delete_visual(m.label)
    markers = []


def spawn_atom(symbol=None, pos=None, vel=None, fixed=False):
    if symbol is None:
        symbol = choice(["H", "H", "H", "O", "C", "N", "F", "Cl"])
    if pos is None:
        pos = rand_vec(3.5) + vector(uniform(-1, 1), uniform(-0.4, 0.4), uniform(-1, 1))
    if vel is None:
        vel = rand_vec(0.6)
    atom = Atom(symbol, pos, vel, fixed=fixed)
    atoms.append(atom)
    return atom


def reset_round(template_name=None, scatter=True):
    global selected_template, round_index, ai_mode_timer, ai_completion_timer, ai_stagnation_timer
    global ai_reset_countdown, ai_last_progress_value, human_override_timer, bond_pulse_timer

    if template_name is not None:
        selected_template = template_name

    clear_scene_objects()
    round_index += 1
    ai_mode_timer = 0.0
    ai_completion_timer = 0.0
    ai_stagnation_timer = 0.0
    ai_reset_countdown = -1.0
    ai_last_progress_value = 0
    human_override_timer = 0.0
    bond_pulse_timer = 0.0

    symbols = TEMPLATES[selected_template]
    target_positions = target_positions_for_template(selected_template, center=vector(0, 0, 0))
    for i, sym in enumerate(symbols):
        if scatter:
            p = target_positions[i] + rand_vec(3.2) + vector(uniform(-2, 2), uniform(-1.0, 1.0), uniform(-1.0, 1.0))
        else:
            p = target_positions[i] + rand_vec(0.2)
        a = spawn_atom(sym, p, rand_vec(0.45))
        a.target_slot = i

    spill_electrons(10, center=vector(0, 0, 0), burst=1.2)
    add_marker(vector(0, 2.6, 0), f"Round {round_index}: build {selected_template}", vector(0.16, 0.28, 0.48), life=2.3)


def add_marker(pos, text, color_value=vector(0.2, 0.25, 0.35), life=2.0):
    markers.append(Marker(pos, text, color_value, life))


def add_spark(pos, color_value=vector(0.28, 0.45, 1.0), count=1, burst=1.0):
    for _ in range(count):
        sparks.append(Spark(pos, rand_vec(burst), color_value, radius=uniform(0.025, 0.065), life=uniform(0.6, 1.8), trail=random() < 0.18))


def spill_electrons(count=18, center=vector(0, 0, 0), burst=1.8):
    for _ in range(count):
        p = center + rand_vec(0.7)
        v = rand_vec(burst)
        sparks.append(Spark(p, v, vector(0.18, 0.34, 1.0), radius=0.04, life=uniform(0.8, 2.3), trail=True))


def clear_temporary_visuals():
    global sparks, markers
    for s in sparks:
        delete_visual(s.obj)
    sparks = []
    for m in markers:
        delete_visual(m.label)
    markers = []


# ---------------------------------------------------------------------------
# Physics, bonding, geometry
# ---------------------------------------------------------------------------

def apply_nonbonded_forces(dt):
    # Mild central containment.
    for atom in atoms:
        atom.force += -0.18 * atom.pos
        if human_override_timer > 0:
            atom.force += -1.2 * atom.pos

    # Atom-atom interaction: soft repulsion, reactive attraction when compatible.
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a = atoms[i]
            b = atoms[j]
            r = b.pos - a.pos
            d = mag(r)
            if d < 0.05:
                r = rand_vec(0.1)
                d = mag(r)
            direction = r / d

            # Soft repulsion for overlap.
            min_d = a.radius + b.radius + 0.25
            if d < min_d:
                f = direction * (-10.0 * (min_d - d))
                a.force += f
                b.force -= f

            # Reactive attraction for atoms that can share electron pairs.
            if compatible_for_bond(a, b) and d < 3.2:
                attract = direction * (0.45 / max(0.18, d))
                a.force += attract
                b.force -= attract

            # Weak charge/electron-cloud repulsion for stable spacing.
            repulse = direction * (-0.06 / max(0.25, d * d))
            a.force += repulse
            b.force -= repulse


def update_bonds(dt):
    for b in list(bonds):
        b.apply_force()
        b.update(dt)


def form_bond(a, b, source="collision"):
    if not compatible_for_bond(a, b):
        return None
    order = 1
    # Stylized O2 can show a double bond if both oxygens have spare capacity.
    if a.symbol == "O" and b.symbol == "O" and a.open_slots >= 2 and b.open_slots >= 2:
        order = 2
    # CO2 can be visually shown as double bonds when carbon and oxygen meet.
    if set([a.symbol, b.symbol]) == set(["C", "O"]) and selected_template == "CO2":
        if a.open_slots >= 1 and b.open_slots >= 1:
            order = 1  # keep capacity simple; label/geometry still shows linear CO2
    new_bond = Bond(a, b, order=order, source=source)
    bonds.append(new_bond)
    add_spark((a.pos + b.pos) * 0.5, vector(0.10, 0.35, 1.0), count=14, burst=1.3)
    add_marker((a.pos + b.pos) * 0.5 + vector(0, 0.45, 0), "shared pair", vector(0.08, 0.22, 0.55), life=1.6)
    return new_bond


def collision_bonding():
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a = atoms[i]
            b = atoms[j]
            if not compatible_for_bond(a, b):
                continue
            d = mag(a.pos - b.pos)
            threshold = a.radius + b.radius + 0.88
            should_bond = d < threshold
            if bond_pulse_timer > 0 and d < threshold + 0.8:
                should_bond = True
            if should_bond:
                form_bond(a, b, source="ai" if ai_enabled else "collision")


def enforce_molecular_geometry(dt):
    # Geometry shaping is strongest for atoms with several bonds.
    for atom in atoms:
        if atom.bond_count < 2:
            continue

        bonded_atoms = [other_atom_from_bond(b, atom) for b in atom.bonds]

        geometry = infer_geometry(atom)
        if atom.symbol == "C" and atom.bond_count >= 4:
            dirs = GEOMETRY_DIRECTIONS["tetrahedral"]
            ideal = 1.42
        elif atom.symbol == "N" and atom.bond_count >= 3:
            dirs = GEOMETRY_DIRECTIONS["trigonal_pyramidal"]
            ideal = 1.35
        elif atom.symbol == "O" and atom.bond_count >= 2:
            dirs = GEOMETRY_DIRECTIONS["bent"]
            ideal = 1.18
        elif atom.bond_count == 2:
            dirs = GEOMETRY_DIRECTIONS["linear"]
            ideal = 1.48
        else:
            continue

        # Rotate desired directions slowly around y-axis for living 3D motion.
        base_ang = 0.15 * sin(round_index + len(bonds) + atom.id)
        dirs_rot = [rotate_y(d, base_ang) for d in dirs]

        for k, neighbor in enumerate(bonded_atoms):
            target = atom.pos + dirs_rot[k % len(dirs_rot)] * ideal
            correction = target - neighbor.pos
            if not neighbor.fixed:
                neighbor.force += correction * 1.6
            if not atom.fixed:
                atom.force -= correction * 0.16


def update_angle_visuals():
    global angle_visuals

    # Delete and rebuild periodically enough for simplicity and correctness.
    for av in angle_visuals:
        av.delete()
    angle_visuals = []

    for atom in atoms:
        if atom.bond_count >= 2:
            bonded_atoms = [other_atom_from_bond(b, atom) for b in atom.bonds]
            # Show a few angle arcs, not every possible pair in crowded molecules.
            for i in range(len(bonded_atoms)):
                for j in range(i + 1, len(bonded_atoms)):
                    if len(angle_visuals) < 8:
                        angle_visuals.append(BondAngleVisual(atom, bonded_atoms[i], bonded_atoms[j]))


def detach_bond(bond=None, reason="detached"):
    global bonds
    if not bonds:
        return
    if bond is None:
        # Prefer strained or newest.
        bond = max(bonds, key=lambda x: (mag(x.a.pos - x.b.pos) / max(0.1, x.ideal_length), x.age))
    pos = (bond.a.pos + bond.b.pos) * 0.5
    add_marker(pos + vector(0, 0.5, 0), reason, vector(0.70, 0.18, 0.12), life=1.7)
    add_spark(pos, vector(1.0, 0.32, 0.20), count=10, burst=1.2)
    if bond in bonds:
        bonds.remove(bond)
    bond.delete()


def update_atoms(dt):
    for atom in atoms:
        atom.update(dt)


def update_transient_visuals(dt):
    global sparks, markers
    sparks = [s for s in sparks if s.update(dt)]
    markers = [m for m in markers if m.update(dt)]


# ---------------------------------------------------------------------------
# Simulation state snapshot for AI
# ---------------------------------------------------------------------------

def simulation_state():
    total_open_slots = sum(a.open_slots for a in atoms)
    bond_count = len(bonds)
    free_atoms = sum(1 for a in atoms if a.bond_count == 0)
    avg_speed = sum(mag(a.vel) for a in atoms) / max(1, len(atoms))
    formula = molecule_formula()
    center = vector(0, 0, 0)
    if atoms:
        for a in atoms:
            center += a.pos
        center /= len(atoms)

    possible_pairs = []
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a = atoms[i]
            b = atoms[j]
            if compatible_for_bond(a, b):
                possible_pairs.append((mag(a.pos - b.pos), a, b))

    progress = bond_count * 10 + (len(atoms) - free_atoms) * 2 - int(total_open_slots)
    template_edges = desired_template_edges(selected_template)
    expected_bonds = len(template_edges)
    complete = bond_count >= expected_bonds and expected_bonds > 0 and free_atoms == 0
    stable = complete and avg_speed < 0.08

    return {
        "atom_count": len(atoms),
        "bond_count": bond_count,
        "free_atoms": free_atoms,
        "avg_speed": avg_speed,
        "formula": formula,
        "center": center,
        "possible_pairs": sorted(possible_pairs, key=lambda x: x[0]),
        "open_slots": total_open_slots,
        "complete": complete,
        "stable": stable,
        "expected_bonds": expected_bonds,
        "progress": progress,
    }


# ---------------------------------------------------------------------------
# AI controller
# ---------------------------------------------------------------------------

def set_ai_mode(mode_name):
    global ai_mode, ai_mode_index, ai_mode_timer
    if mode_name in AI_MODES:
        ai_mode = mode_name
        ai_mode_index = AI_MODES.index(mode_name)
        ai_mode_timer = 0.0
        add_marker(vector(0, 3.0, 0), f"AI mode: {ai_mode}", vector(0.15, 0.22, 0.48), life=1.5)


def cycle_ai_mode():
    global ai_mode_index
    ai_mode_index = (ai_mode_index + 1) % len(AI_MODES)
    set_ai_mode(AI_MODES[ai_mode_index])


def ai_choose_next_mode(state):
    # State-reactive mode selection avoids repeating forever.
    if state["atom_count"] == 0:
        return "constructive_spill"
    if state["complete"] and ai_completion_timer > 1.0:
        return "ritual_loop"
    if ai_stagnation_timer > 4.0:
        return choice(["collision_play", "constructive_spill", "destructive_repair"])
    if state["free_atoms"] > 0 and state["possible_pairs"]:
        return choice(["careful_builder", "collision_play", "curious_orbits"])
    if state["bond_count"] >= 2:
        return choice(["geometry_teacher", "lone_pair_artist", "ritual_loop"])
    return choice(["careful_builder", "curious_orbits"])


def ai_apply_attraction_pair(a, b, strength=1.0):
    r = b.pos - a.pos
    d = max(0.1, mag(r))
    direction = r / d
    f = direction * strength
    a.force += f
    b.force -= f


def ai_organize_to_template(state, dt, strength=1.0):
    target_positions = target_positions_for_template(selected_template, center=vector(0, 0, 0))
    for atom in atoms:
        slot = atom.target_slot if atom.target_slot is not None else 0
        target = target_positions[slot % len(target_positions)]
        atom.force += (target - atom.pos) * strength
        atom.vel *= 0.995


def ai_find_template_pair():
    edges = desired_template_edges(selected_template)
    by_slot = {a.target_slot: a for a in atoms if a.target_slot is not None}
    for i, j in edges:
        if i in by_slot and j in by_slot:
            a = by_slot[i]
            b = by_slot[j]
            if compatible_for_bond(a, b):
                return a, b
    return None, None


def ai_careful_builder(state, dt):
    ai_organize_to_template(state, dt, strength=0.75)
    a, b = ai_find_template_pair()
    if a is None or b is None:
        if state["possible_pairs"]:
            _, a, b = state["possible_pairs"][0]
    if a is not None and b is not None:
        ai_apply_attraction_pair(a, b, strength=2.0 * ai_speed)
        if mag(a.pos - b.pos) < a.radius + b.radius + 1.05:
            form_bond(a, b, source="ai")


def ai_curious_orbits(state, dt):
    if not atoms:
        return
    center = state["center"]
    ai_memory["ritual_angle"] += dt * (0.8 + ai_speed * 0.5)
    for idx, atom in enumerate(atoms):
        radial = atom.pos - center
        tangent = cross(vector(0, 1, 0), radial)
        atom.force += safe_norm(tangent, rand_vec(1)) * (0.35 + 0.15 * idx) * ai_speed
        atom.force += -0.10 * radial
    if state["possible_pairs"] and random() < 0.035 * ai_speed:
        _, a, b = choice(state["possible_pairs"][: min(3, len(state["possible_pairs"]))])
        ai_apply_attraction_pair(a, b, strength=1.5)


def ai_collision_play(state, dt):
    if state["possible_pairs"]:
        _, a, b = choice(state["possible_pairs"][: min(4, len(state["possible_pairs"]))])
        midpoint = (a.pos + b.pos) * 0.5
        a.vel += safe_norm(midpoint - a.pos, rand_vec(1)) * 0.12 * ai_speed
        b.vel += safe_norm(midpoint - b.pos, rand_vec(1)) * 0.12 * ai_speed
        ai_apply_attraction_pair(a, b, strength=2.5 * ai_speed)
        if random() < 0.04 * ai_speed:
            add_marker(midpoint + vector(0, 0.5, 0), "collision test", vector(0.45, 0.22, 0.10), life=1.0)


def ai_geometry_teacher(state, dt):
    ai_organize_to_template(state, dt, strength=0.32)
    for atom in atoms:
        if atom.bond_count >= 2 and random() < 0.015 * ai_speed:
            add_marker(atom.pos + vector(0, 0.8, 0), infer_geometry(atom), vector(0.10, 0.30, 0.42), life=2.0)
    # Add gentle movement so the geometry remains visibly alive.
    for atom in atoms:
        atom.force += vector(0, 0.10 * sin(ai_mode_timer * 2 + atom.id), 0)


def ai_lone_pair_artist(state, dt):
    for atom in atoms:
        if atom.symbol in ("O", "N", "F", "Cl"):
            atom.shell.opacity = 0.13 + 0.04 * sin(ai_mode_timer * 4 + atom.id)
            if random() < 0.012 * ai_speed:
                add_spark(atom.pos + rand_vec(0.5), vector(0.48, 0.56, 1.0), count=3, burst=0.45)
                add_marker(atom.pos + vector(0, 0.85, 0), "lone pairs shape bonds", vector(0.24, 0.25, 0.60), life=1.6)
    ai_organize_to_template(state, dt, strength=0.18)


def ai_constructive_spill(state, dt):
    if random() < 0.05 * ai_speed:
        spill_electrons(4, center=state["center"], burst=1.0)
    if state["atom_count"] < len(TEMPLATES[selected_template]) and random() < 0.02 * ai_speed:
        needed = TEMPLATES[selected_template][state["atom_count"] % len(TEMPLATES[selected_template])]
        spawn_atom(needed, pos=rand_vec(4.0), vel=rand_vec(0.35))
    ai_careful_builder(state, dt)


def ai_destructive_repair(state, dt):
    # Occasionally detach one bond, then repair through builder mode.
    ai_memory["chaos_cooldown"] = max(0.0, ai_memory.get("chaos_cooldown", 0.0) - dt)
    if bonds and ai_memory["chaos_cooldown"] <= 0 and random() < 0.012 * ai_speed:
        detach_bond(reason="AI breaks / repairs")
        ai_memory["chaos_cooldown"] = 3.0
    else:
        ai_careful_builder(state, dt)
    for atom in atoms:
        atom.vel += rand_vec(0.015 * ai_speed)


def ai_ritual_loop(state, dt):
    center = state["center"]
    ai_memory["ritual_angle"] += dt * 1.1
    radius = 2.5
    for i, atom in enumerate(atoms):
        theta = ai_memory["ritual_angle"] + 2 * pi * i / max(1, len(atoms))
        target = vector(radius * cos(theta), 0.45 * sin(theta * 2), radius * sin(theta))
        atom.force += (target - atom.pos) * 0.35
    if random() < 0.025 * ai_speed:
        add_spark(center + rand_vec(0.5), vector(0.90, 0.68, 0.18), count=6, burst=0.8)
    if state["complete"]:
        add_marker(center + vector(0, 1.4, 0), "stable molecule loop", vector(0.42, 0.24, 0.08), life=1.3)


def update_ai_controller(dt):
    global ai_mode_timer, ai_mode_duration, ai_stagnation_timer, ai_completion_timer
    global ai_last_progress_value, ai_reset_countdown

    if not ai_enabled:
        return

    dt_ai = dt * ai_speed
    state = simulation_state()
    ai_mode_timer += dt_ai

    # Progress/stagnation detector.
    if state["progress"] != ai_last_progress_value:
        ai_last_progress_value = state["progress"]
        ai_stagnation_timer = 0.0
    else:
        ai_stagnation_timer += dt_ai

    # Completion detector and loop reset countdown.
    if state["complete"] or state["stable"]:
        ai_completion_timer += dt_ai
    else:
        ai_completion_timer = 0.0

    if ai_reset_countdown > 0:
        ai_reset_countdown -= dt_ai
        if ai_reset_countdown <= 0:
            next_template = choice(TEMPLATE_ORDER)
            reset_round(next_template, scatter=True)
            return

    if state["complete"] and ai_completion_timer > 5.0 and ai_reset_countdown < 0:
        add_marker(state["center"] + vector(0, 1.8, 0), "complete → new round soon", vector(0.20, 0.35, 0.16), life=2.2)
        ai_reset_countdown = 2.2

    if ai_stagnation_timer > 7.0 and ai_reset_countdown < 0:
        add_marker(vector(0, 2.2, 0), "stagnation reset", vector(0.50, 0.20, 0.12), life=1.8)
        ai_reset_countdown = 1.2

    # Mode switching.
    if ai_mode_timer > ai_mode_duration:
        next_mode = ai_choose_next_mode(state)
        set_ai_mode(next_mode)
        ai_mode_duration = uniform(4.0, 8.0)

    # Run selected behavior.
    if ai_mode == "careful_builder":
        ai_careful_builder(state, dt_ai)
    elif ai_mode == "curious_orbits":
        ai_curious_orbits(state, dt_ai)
    elif ai_mode == "collision_play":
        ai_collision_play(state, dt_ai)
    elif ai_mode == "geometry_teacher":
        ai_geometry_teacher(state, dt_ai)
    elif ai_mode == "lone_pair_artist":
        ai_lone_pair_artist(state, dt_ai)
    elif ai_mode == "constructive_spill":
        ai_constructive_spill(state, dt_ai)
    elif ai_mode == "destructive_repair":
        ai_destructive_repair(state, dt_ai)
    elif ai_mode == "ritual_loop":
        ai_ritual_loop(state, dt_ai)


# ---------------------------------------------------------------------------
# UI state update
# ---------------------------------------------------------------------------

def update_labels():
    state = simulation_state()
    molecule_label.text = f"Molecule: {state['formula']}  | target {selected_template}"
    central = None
    if atoms:
        central = max(atoms, key=lambda a: a.bond_count)
    geometry = infer_geometry(central) if central else "--"
    geometry_label.text = f"Geometry: {geometry}  | bonds {state['bond_count']}/{state['expected_bonds']}"
    status = "complete" if state["complete"] else "stable" if state["stable"] else "forming"
    if paused:
        status = "paused"
    status_label.text = f"Status: {status}  | free atoms {state['free_atoms']}  | avg speed {state['avg_speed']:.2f}"
    ai_state = "on" if ai_enabled else "off"
    ai_label.text = f"AI: {ai_state}  | mode {ai_mode}  | speed {ai_speed:.1f}  | stagnant {ai_stagnation_timer:.1f}s"


# ---------------------------------------------------------------------------
# Keyboard controls
# ---------------------------------------------------------------------------

def print_controls():
    print(__doc__)


def keydown(evt):
    global paused, ai_enabled, human_override_timer, bond_pulse_timer, ai_speed, selected_template
    key = evt.key.lower()

    if key == "h":
        print_controls()

    elif key == "a":
        ai_enabled = not ai_enabled
        add_marker(vector(0, 3.0, 0), f"AI {'on' if ai_enabled else 'off'}", vector(0.15, 0.22, 0.48), life=1.5)

    elif key == "p":
        paused = not paused
        add_marker(vector(0, 3.0, 0), "paused" if paused else "resumed", vector(0.16, 0.20, 0.28), life=1.2)

    elif key == "r":
        reset_round(selected_template, scatter=True)

    elif key == "m":
        cycle_ai_mode()

    elif key == "n":
        spawn_atom()
        add_marker(vector(0, 2.6, 0), "spawned atom", vector(0.16, 0.24, 0.38), life=1.2)

    elif key == "b":
        bond_pulse_timer = 1.2
        add_marker(vector(0, 2.6, 0), "bond pulse", vector(0.08, 0.28, 0.50), life=1.2)

    elif key == "d":
        detach_bond(reason="human detach")

    elif key == "s":
        spill_electrons(24, center=vector(0, 0, 0), burst=2.0)

    elif key == "o":
        human_override_timer = 2.0
        bond_pulse_timer = 0.8
        add_marker(vector(0, 2.6, 0), "human override", vector(0.32, 0.18, 0.48), life=1.3)

    elif key == "c":
        clear_temporary_visuals()

    elif key in ["+", "="]:
        ai_speed = clamp(ai_speed + 0.2, 0.2, 3.0)
        add_marker(vector(0, 2.6, 0), f"AI speed {ai_speed:.1f}", vector(0.16, 0.24, 0.38), life=1.0)

    elif key in ["-", "_"]:
        ai_speed = clamp(ai_speed - 0.2, 0.2, 3.0)
        add_marker(vector(0, 2.6, 0), f"AI speed {ai_speed:.1f}", vector(0.16, 0.24, 0.38), life=1.0)

    elif key in ["1", "2", "3", "4", "5", "6"]:
        idx = int(key) - 1
        if 0 <= idx < len(TEMPLATE_ORDER):
            selected_template = TEMPLATE_ORDER[idx]
            reset_round(selected_template, scatter=True)


scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Background guide objects
# ---------------------------------------------------------------------------

def create_environment():
    # Light floor grid.
    for x in range(-7, 8):
        curve(
            pos=[vector(x, -3.0, -7), vector(x, -3.0, 7)],
            radius=0.006,
            color=vector(0.78, 0.84, 0.90),
            opacity=0.35,
        )
    for z in range(-7, 8):
        curve(
            pos=[vector(-7, -3.0, z), vector(7, -3.0, z)],
            radius=0.006,
            color=vector(0.78, 0.84, 0.90),
            opacity=0.35,
        )
    box(
        pos=vector(0, -3.05, 0),
        size=vector(14.0, 0.02, 14.0),
        color=vector(0.94, 0.96, 0.98),
        opacity=0.32,
    )
    make_label(
        "Covalent bonds: shared electron pairs stabilize geometry",
        vector(0, 5.7, 0),
        height=16,
        color_value=vector(0.06, 0.08, 0.12),
        box=False,
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    global human_override_timer, bond_pulse_timer

    create_environment()
    create_static_ui()
    reset_round(selected_template, scatter=True)
    print_controls()

    t = 0.0
    angle_timer = 0.0

    while True:
        rate(60)
        dt = 1 / 60.0
        if paused:
            update_transient_visuals(dt)
            update_labels()
            continue

        t += dt
        angle_timer += dt
        human_override_timer = max(0.0, human_override_timer - dt)
        bond_pulse_timer = max(0.0, bond_pulse_timer - dt)

        update_ai_controller(dt)
        apply_nonbonded_forces(dt)
        update_bonds(dt)
        enforce_molecular_geometry(dt)
        update_atoms(dt)
        collision_bonding()
        update_transient_visuals(dt)

        if angle_timer > 0.55:
            angle_timer = 0.0
            update_angle_visuals()

        update_labels()


if __name__ == "__main__":
    main()
