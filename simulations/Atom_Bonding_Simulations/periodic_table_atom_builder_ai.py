#!/usr/bin/env python3
"""
Periodic Table Atom Builder — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python periodic_table_atom_builder_ai.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset current element
    N       next element
    B       previous element
    M       cycle AI behavior mode
    C       clear temporary marks, sparks, and trails
    O       human override: spill bond probes and charge particles
    1-9     select element by preset index
    H       print controls

Concept:
    A user selects an element. The simulation builds a stylized atom:
    nucleus, protons, neutrons, electron shells, orbiting electrons, atomic-radius
    halo, charge field, valence shell, and possible bonding sites. The AI can
    read simulation state and choose actions: build, orbit, mark valence electrons,
    attempt bonds, detach bonds, spill probes, rotate the scene, or reset to a
    new element when the simulation is complete or stagnant.

Notes:
    This is an educational / visual model, not a quantum-mechanical simulation.
    Electron shell counts are simplified Bohr-style capacities for display.
    Uses VPython primitives only and avoids torus(), using ring(...) instead.
"""

from vpython import *
from math import sin, cos, pi, sqrt, atan2
import random
import time

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------

scene = canvas(
    title="Periodic Table Atom Builder — AI Controlled 3D Atom Builder",
    width=1200,
    height=780,
    background=vector(0.965, 0.975, 1.0),
    center=vector(0, 0, 0),
)

scene.forward = vector(-0.75, -0.40, -1.0)
scene.range = 9.2
scene.autoscale = False

# ------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)

def vlerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)

def rand_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m <= 1e-9:
        return fallback
    return v / m

def color_mix(a, b, t):
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))

def shell_capacity(n):
    # Simplified visible Bohr-shell display.
    return 2 * n * n

def shell_distribution(z):
    counts = []
    left = z
    n = 1
    while left > 0:
        cap = shell_capacity(n)
        take = min(left, cap)
        counts.append(take)
        left -= take
        n += 1
    return counts

def estimate_valence(counts):
    if not counts:
        return 0
    return counts[-1]

def possible_bonds_from_valence(v):
    # Rough visual heuristic for common main-group behavior.
    if v == 0:
        return 0
    if v <= 4:
        return v
    if v <= 7:
        return 8 - v
    return 0

# ------------------------------------------------------------
# Element data
# ------------------------------------------------------------

ELEMENTS = [
    {
        "symbol": "H", "name": "Hydrogen", "z": 1, "mass": 1, "charge": 0,
        "radius": 0.53, "group": "nonmetal", "color": vector(0.95, 0.95, 0.98),
        "bonds": 1
    },
    {
        "symbol": "He", "name": "Helium", "z": 2, "mass": 4, "charge": 0,
        "radius": 0.31, "group": "noble gas", "color": vector(0.85, 0.95, 1.0),
        "bonds": 0
    },
    {
        "symbol": "Li", "name": "Lithium", "z": 3, "mass": 7, "charge": 1,
        "radius": 1.67, "group": "alkali metal", "color": vector(0.84, 0.72, 1.0),
        "bonds": 1
    },
    {
        "symbol": "Be", "name": "Beryllium", "z": 4, "mass": 9, "charge": 2,
        "radius": 1.12, "group": "alkaline earth", "color": vector(0.70, 0.95, 0.68),
        "bonds": 2
    },
    {
        "symbol": "B", "name": "Boron", "z": 5, "mass": 11, "charge": 3,
        "radius": 0.87, "group": "metalloid", "color": vector(1.0, 0.78, 0.60),
        "bonds": 3
    },
    {
        "symbol": "C", "name": "Carbon", "z": 6, "mass": 12, "charge": 0,
        "radius": 0.67, "group": "nonmetal", "color": vector(0.54, 0.58, 0.62),
        "bonds": 4
    },
    {
        "symbol": "N", "name": "Nitrogen", "z": 7, "mass": 14, "charge": -3,
        "radius": 0.56, "group": "nonmetal", "color": vector(0.45, 0.62, 1.0),
        "bonds": 3
    },
    {
        "symbol": "O", "name": "Oxygen", "z": 8, "mass": 16, "charge": -2,
        "radius": 0.48, "group": "nonmetal", "color": vector(1.0, 0.32, 0.28),
        "bonds": 2
    },
    {
        "symbol": "F", "name": "Fluorine", "z": 9, "mass": 19, "charge": -1,
        "radius": 0.42, "group": "halogen", "color": vector(0.55, 1.0, 0.48),
        "bonds": 1
    },
    {
        "symbol": "Ne", "name": "Neon", "z": 10, "mass": 20, "charge": 0,
        "radius": 0.38, "group": "noble gas", "color": vector(0.72, 0.96, 1.0),
        "bonds": 0
    },
    {
        "symbol": "Na", "name": "Sodium", "z": 11, "mass": 23, "charge": 1,
        "radius": 1.90, "group": "alkali metal", "color": vector(0.76, 0.68, 1.0),
        "bonds": 1
    },
    {
        "symbol": "Mg", "name": "Magnesium", "z": 12, "mass": 24, "charge": 2,
        "radius": 1.45, "group": "alkaline earth", "color": vector(0.65, 0.95, 0.75),
        "bonds": 2
    },
    {
        "symbol": "Al", "name": "Aluminum", "z": 13, "mass": 27, "charge": 3,
        "radius": 1.18, "group": "post-transition metal", "color": vector(0.86, 0.88, 0.90),
        "bonds": 3
    },
    {
        "symbol": "Si", "name": "Silicon", "z": 14, "mass": 28, "charge": 4,
        "radius": 1.11, "group": "metalloid", "color": vector(0.96, 0.72, 0.50),
        "bonds": 4
    },
    {
        "symbol": "P", "name": "Phosphorus", "z": 15, "mass": 31, "charge": -3,
        "radius": 0.98, "group": "nonmetal", "color": vector(1.0, 0.70, 0.25),
        "bonds": 3
    },
    {
        "symbol": "S", "name": "Sulfur", "z": 16, "mass": 32, "charge": -2,
        "radius": 0.88, "group": "nonmetal", "color": vector(1.0, 0.93, 0.25),
        "bonds": 2
    },
    {
        "symbol": "Cl", "name": "Chlorine", "z": 17, "mass": 35, "charge": -1,
        "radius": 0.79, "group": "halogen", "color": vector(0.42, 0.95, 0.38),
        "bonds": 1
    },
    {
        "symbol": "Ar", "name": "Argon", "z": 18, "mass": 40, "charge": 0,
        "radius": 0.71, "group": "noble gas", "color": vector(0.75, 0.91, 1.0),
        "bonds": 0
    },
    {
        "symbol": "K", "name": "Potassium", "z": 19, "mass": 39, "charge": 1,
        "radius": 2.43, "group": "alkali metal", "color": vector(0.70, 0.60, 1.0),
        "bonds": 1
    },
    {
        "symbol": "Ca", "name": "Calcium", "z": 20, "mass": 40, "charge": 2,
        "radius": 1.94, "group": "alkaline earth", "color": vector(0.58, 0.90, 0.68),
        "bonds": 2
    },
]

element_index = 7

# ------------------------------------------------------------
# Global state
# ------------------------------------------------------------

paused = False
ai_enabled = True
sim_time = 0.0
round_id = 0
build_progress = 0.0
last_change_time = 0.0
last_state_signature = None

objects = []
nucleus_particles = []
shell_rings = []
shell_labels = []
electrons = []
bond_sites = []
bond_lines = []
bond_probes = []
charge_particles = []
sparks = []
temporary_marks = []
radius_halo = None
valence_halo = None
nucleus_core = None
info_label = None
ai_label = None
state_label = None
periodic_bar = []
ghost_atoms = []
selected_element = None

# ------------------------------------------------------------
# Materials / colors
# ------------------------------------------------------------

PROTON_COLOR = vector(1.0, 0.32, 0.32)
NEUTRON_COLOR = vector(0.72, 0.74, 0.78)
ELECTRON_COLOR = vector(0.22, 0.36, 1.0)
VALENCE_ELECTRON_COLOR = vector(0.10, 0.62, 1.0)
BOND_COLOR = vector(0.23, 0.50, 0.86)
POSITIVE_COLOR = vector(1.0, 0.48, 0.30)
NEGATIVE_COLOR = vector(0.24, 0.42, 1.0)
NEUTRAL_COLOR = vector(0.62, 0.68, 0.74)
MARK_COLOR = vector(1.0, 0.82, 0.20)

# ------------------------------------------------------------
# Entity classes
# ------------------------------------------------------------

class Electron:
    def __init__(self, shell_idx, shell_count, idx_in_shell, shell_radius, valence=False):
        self.shell_idx = shell_idx
        self.idx_in_shell = idx_in_shell
        self.shell_count = max(1, shell_count)
        self.shell_radius = shell_radius
        self.angle = 2 * pi * idx_in_shell / self.shell_count + random.uniform(-0.2, 0.2)
        self.speed = 0.55 + 0.13 * shell_idx + random.uniform(-0.05, 0.08)
        self.phase = random.uniform(0, 2 * pi)
        self.valence = valence
        self.attached_to_bond = False
        self.marked = False
        self.dip = 0.0
        self.trail = curve(color=VALENCE_ELECTRON_COLOR if valence else ELECTRON_COLOR, radius=0.012, opacity=0.35)
        self.body = sphere(
            pos=vector(0, 0, 0),
            radius=0.105 if valence else 0.085,
            color=VALENCE_ELECTRON_COLOR if valence else ELECTRON_COLOR,
            emissive=True,
            make_trail=False,
        )
        objects.extend([self.body, self.trail])

    def orbit_position(self, t):
        r = self.shell_radius + 0.10 * sin(0.7 * t + self.phase)
        a = self.angle + self.speed * t
        tilt = 0.26 * sin(self.shell_idx * 1.37 + self.idx_in_shell)
        wobble = 0.18 * sin(1.9 * t + self.phase)
        y = r * sin(a) * tilt + wobble + self.dip
        return vector(r * cos(a), y, r * sin(a))

    def update(self, t, dt):
        target = self.orbit_position(t)
        if self.attached_to_bond:
            target = vlerp(target, self.attached_to_bond.pos, 0.45)
        self.body.pos = vlerp(self.body.pos, target, min(1, 8 * dt))
        if self.marked:
            self.body.color = color_mix(self.body.color, MARK_COLOR, 0.09)
        else:
            base = VALENCE_ELECTRON_COLOR if self.valence else ELECTRON_COLOR
            self.body.color = color_mix(self.body.color, base, 0.05)
        self.dip *= 0.94
        if self.trail.npoints < 120:
            self.trail.append(pos=self.body.pos)
        else:
            self.trail.clear()
            self.trail.append(pos=self.body.pos)

    def clear_trail(self):
        self.trail.clear()

class BondSite:
    def __init__(self, idx, total, radius):
        self.idx = idx
        self.total = max(1, total)
        self.angle = 2 * pi * idx / self.total
        self.radius = radius
        self.occupied = False
        self.strength = 0.0
        self.pulse = random.uniform(0, 2 * pi)
        pos = self.position()
        self.body = sphere(
            pos=pos,
            radius=0.12,
            color=vector(1.0, 0.95, 0.45),
            opacity=0.72,
            emissive=True,
        )
        self.stem = cylinder(
            pos=pos * 0.75,
            axis=pos * 0.25,
            radius=0.025,
            color=BOND_COLOR,
            opacity=0.35,
        )
        self.label = label(
            pos=pos * 1.13,
            text=f"bond {idx + 1}",
            height=10,
            color=vector(0.15, 0.20, 0.25),
            opacity=0.0,
            box=False,
        )
        objects.extend([self.body, self.stem, self.label])

    def position(self):
        return vector(self.radius * cos(self.angle), 0.26 * sin(self.angle * 2.0), self.radius * sin(self.angle))

    def update(self, t, dt):
        self.pulse += dt * (2.5 + self.strength)
        pos = self.position()
        self.body.pos = pos + safe_norm(pos) * (0.05 * sin(self.pulse))
        self.body.radius = 0.12 + 0.05 * self.strength + 0.025 * sin(self.pulse)
        self.body.opacity = 0.35 + 0.45 * (0.4 + self.strength)
        self.body.color = color_mix(vector(1.0, 0.95, 0.45), BOND_COLOR, self.strength)
        self.stem.pos = pos * 0.72
        self.stem.axis = pos * 0.30
        self.stem.opacity = 0.25 + 0.45 * self.strength
        self.strength *= 0.985

    @property
    def pos(self):
        return self.body.pos

class BondProbe:
    def __init__(self, origin=None, target_site=None):
        self.target_site = target_site
        self.attached = False
        self.age = 0.0
        self.life = random.uniform(8.0, 15.0)
        if origin is None:
            origin = vector(random.uniform(-6, 6), random.uniform(-2.5, 2.5), random.uniform(-5, 5))
        self.vel = rand_vec(0.7)
        self.body = sphere(
            pos=origin,
            radius=random.uniform(0.08, 0.13),
            color=vector(0.20, 0.62, 0.95),
            opacity=0.76,
            emissive=True,
        )
        self.tail = curve(color=vector(0.20, 0.62, 0.95), radius=0.01, opacity=0.27)
        objects.extend([self.body, self.tail])

    def update(self, dt):
        self.age += dt
        if self.target_site is not None:
            direction = self.target_site.pos - self.body.pos
            self.vel += safe_norm(direction) * 0.18 * dt
            if mag(direction) < 0.35 and not self.target_site.occupied:
                self.attached = True
                self.target_site.occupied = True
                self.target_site.strength = 1.0
                self.body.color = vector(0.1, 0.75, 0.55)
                make_bond_line(self.target_site, self.body)
                make_spark(self.body.pos, vector(0.1, 0.75, 0.55), count=6)
        else:
            center_force = -self.body.pos * 0.015
            self.vel += center_force * dt

        self.vel *= 0.992
        self.body.pos += self.vel * dt
        if self.attached and self.target_site is not None:
            self.body.pos = vlerp(self.body.pos, self.target_site.pos * 1.16, min(1, 7 * dt))
            self.vel *= 0.6
        if self.tail.npoints < 80:
            self.tail.append(pos=self.body.pos)
        else:
            self.tail.clear()
            self.tail.append(pos=self.body.pos)

    def expired(self):
        return self.age > self.life and not self.attached

    def hide(self):
        self.body.visible = False
        self.tail.visible = False

class ChargeParticle:
    def __init__(self, charge_sign=0):
        self.charge_sign = charge_sign
        self.angle = random.uniform(0, 2 * pi)
        self.radius = random.uniform(3.0, 6.0)
        self.height = random.uniform(-2.3, 2.3)
        self.speed = random.uniform(0.22, 0.68) * (1 if charge_sign >= 0 else -1)
        self.age = 0.0
        self.life = random.uniform(7.0, 13.0)
        col = POSITIVE_COLOR if charge_sign > 0 else NEGATIVE_COLOR if charge_sign < 0 else NEUTRAL_COLOR
        self.body = sphere(
            pos=self.position(),
            radius=0.055,
            color=col,
            opacity=0.50,
            emissive=True,
        )
        objects.append(self.body)

    def position(self):
        return vector(self.radius * cos(self.angle), self.height + 0.2 * sin(self.angle * 2), self.radius * sin(self.angle))

    def update(self, dt):
        self.age += dt
        self.angle += self.speed * dt
        self.height += 0.10 * sin(self.angle * 0.7) * dt
        self.radius += 0.02 * sin(self.age * 2.0) * dt
        self.body.pos = self.position()
        self.body.opacity = max(0.0, 0.50 * (1 - self.age / self.life))

    def expired(self):
        return self.age > self.life

    def hide(self):
        self.body.visible = False

class Spark:
    def __init__(self, pos, col):
        self.age = 0.0
        self.life = random.uniform(0.45, 1.3)
        self.vel = rand_vec(random.uniform(0.35, 1.1))
        self.body = sphere(
            pos=pos,
            radius=random.uniform(0.035, 0.08),
            color=col,
            opacity=0.85,
            emissive=True,
        )
        objects.append(self.body)

    def update(self, dt):
        self.age += dt
        self.body.pos += self.vel * dt
        self.vel *= 0.94
        self.body.opacity = max(0.0, 0.85 * (1 - self.age / self.life))
        self.body.radius *= 0.992

    def expired(self):
        return self.age > self.life

    def hide(self):
        self.body.visible = False

# ------------------------------------------------------------
# Scene object management
# ------------------------------------------------------------

def register(obj):
    objects.append(obj)
    return obj

def hide_all_current():
    global objects, nucleus_particles, shell_rings, shell_labels, electrons
    global bond_sites, bond_lines, bond_probes, charge_particles, sparks
    global temporary_marks, radius_halo, valence_halo, nucleus_core
    global info_label, ai_label, state_label, periodic_bar, ghost_atoms

    for obj in objects:
        try:
            obj.visible = False
        except Exception:
            pass

    objects = []
    nucleus_particles = []
    shell_rings = []
    shell_labels = []
    electrons = []
    bond_sites = []
    bond_lines = []
    bond_probes = []
    charge_particles = []
    sparks = []
    temporary_marks = []
    radius_halo = None
    valence_halo = None
    nucleus_core = None
    info_label = None
    ai_label = None
    state_label = None
    periodic_bar = []
    ghost_atoms = []

def make_spark(pos, col=MARK_COLOR, count=8):
    for _ in range(count):
        sparks.append(Spark(pos + rand_vec(0.05), col))

def make_bond_line(site, probe_body):
    line = cylinder(
        pos=site.pos,
        axis=probe_body.pos - site.pos,
        radius=0.035,
        color=BOND_COLOR,
        opacity=0.62,
    )
    bond_lines.append((line, site, probe_body))
    objects.append(line)

def clear_marks():
    global temporary_marks
    for e in electrons:
        e.marked = False
        e.clear_trail()
    for obj in temporary_marks:
        try:
            obj.visible = False
        except Exception:
            pass
    temporary_marks = []
    for sp in sparks:
        sp.hide()
    sparks.clear()

def clear_probes_and_charge():
    for p in bond_probes:
        p.hide()
    bond_probes.clear()
    for c in charge_particles:
        c.hide()
    charge_particles.clear()
    for line, _, _ in bond_lines:
        line.visible = False
    bond_lines.clear()
    for site in bond_sites:
        site.occupied = False
        site.strength = 0.0

# ------------------------------------------------------------
# Atom building
# ------------------------------------------------------------

def create_periodic_selector():
    global periodic_bar
    x0 = -8.6
    y0 = -4.45
    spacing = 0.86
    for i, elem in enumerate(ELEMENTS[:20]):
        x = x0 + (i % 10) * spacing
        z = 0.0
        y = y0 + (i // 10) * 0.55
        marker = box(
            pos=vector(x, y, -5.4),
            size=vector(0.58, 0.32, 0.06),
            color=elem["color"],
            opacity=0.45,
        )
        txt = label(
            pos=marker.pos + vector(0, 0.03, 0.07),
            text=elem["symbol"],
            height=9,
            color=vector(0.12, 0.16, 0.20),
            opacity=0.0,
            box=False,
        )
        periodic_bar.append((marker, txt))
        objects.extend([marker, txt])

def update_periodic_selector():
    for i, (marker, txt) in enumerate(periodic_bar):
        if i == element_index:
            marker.opacity = 0.95
            marker.size = vector(0.70, 0.39, 0.08)
        else:
            marker.opacity = 0.38
            marker.size = vector(0.58, 0.32, 0.06)

def make_nucleus(elem):
    global nucleus_core
    z = elem["z"]
    neutrons = max(0, elem["mass"] - z)
    total = z + neutrons

    nucleus_core = sphere(
        pos=vector(0, 0, 0),
        radius=0.35 + 0.018 * sqrt(total),
        color=color_mix(elem["color"], vector(1, 1, 1), 0.20),
        opacity=0.22,
    )
    register(nucleus_core)

    # Keep the visual manageable for larger atoms.
    max_visible = min(total, 70)
    proton_visible = min(z, max_visible)
    neutron_visible = max_visible - proton_visible

    particles = [("p+", PROTON_COLOR)] * proton_visible + [("n", NEUTRON_COLOR)] * neutron_visible
    random.shuffle(particles)

    for i, (kind, col) in enumerate(particles):
        layer = int(i ** (1 / 3))
        r = 0.16 + 0.065 * layer + random.uniform(0.0, 0.18)
        theta = random.uniform(0, 2 * pi)
        phi = random.uniform(-pi / 2, pi / 2)
        pos = vector(r * cos(phi) * cos(theta), r * sin(phi), r * cos(phi) * sin(theta))
        part = sphere(
            pos=pos,
            radius=0.095,
            color=col,
            opacity=0.94,
            shininess=0.6,
        )
        nucleus_particles.append((part, pos, kind, random.uniform(0, 2 * pi)))
        register(part)

def make_shells_and_electrons(elem):
    global radius_halo, valence_halo
    counts = shell_distribution(elem["z"])
    display_radius = 1.55 + 0.30 * len(counts) + 0.15 * elem["radius"]

    radius_halo = sphere(
        pos=vector(0, 0, 0),
        radius=display_radius + 0.75,
        color=elem["color"],
        opacity=0.055,
    )
    register(radius_halo)

    valence_halo = sphere(
        pos=vector(0, 0, 0),
        radius=display_radius + 0.25,
        color=vector(0.45, 0.74, 1.0),
        opacity=0.035,
    )
    register(valence_halo)

    for s, count in enumerate(counts):
        r = 1.20 + 0.92 * s + 0.10 * elem["radius"]
        shell_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=r,
            thickness=0.018,
            color=vector(0.58, 0.68, 0.78),
            opacity=0.30,
        )
        shell_rings.append(shell_ring)
        register(shell_ring)

        shell_ring_2 = ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0.25, 0),
            radius=r,
            thickness=0.010,
            color=vector(0.70, 0.78, 0.86),
            opacity=0.20,
        )
        shell_rings.append(shell_ring_2)
        register(shell_ring_2)

        txt = label(
            pos=vector(r + 0.25, 0.18, 0),
            text=f"shell {s + 1}: {count}e⁻",
            height=11,
            color=vector(0.20, 0.25, 0.30),
            opacity=0.0,
            box=False,
        )
        shell_labels.append(txt)
        register(txt)

        for i in range(count):
            valence = (s == len(counts) - 1)
            electrons.append(Electron(s + 1, count, i, r, valence=valence))

    possible_bonds = elem.get("bonds", possible_bonds_from_valence(estimate_valence(counts)))
    possible_bonds = max(0, min(8, possible_bonds))
    for i in range(possible_bonds):
        bond_sites.append(BondSite(i, possible_bonds, display_radius + 0.75))

def make_charge_field(elem):
    q = elem["charge"]
    sign = 1 if q > 0 else -1 if q < 0 else 0
    count = 10 + min(20, abs(q) * 5)
    for _ in range(count):
        charge_particles.append(ChargeParticle(sign))

def make_labels(elem):
    global info_label, ai_label, state_label
    counts = shell_distribution(elem["z"])
    valence = estimate_valence(counts)
    bonds = elem.get("bonds", possible_bonds_from_valence(valence))
    q = elem["charge"]
    qtext = "neutral" if q == 0 else f"{q:+d} likely ion charge"
    info_label = label(
        pos=vector(-5.8, 3.95, 0),
        text=(
            f"{elem['name']} ({elem['symbol']})\n"
            f"Atomic number: {elem['z']} | Mass: {elem['mass']}\n"
            f"Protons: {elem['z']} | Neutrons: {max(0, elem['mass'] - elem['z'])} | Electrons: {elem['z']}\n"
            f"Shells: {counts} | Valence: {valence} | Possible bonds: {bonds}\n"
            f"Atomic radius model: {elem['radius']} Å | Charge field: {qtext}\n"
            f"Group: {elem['group']}"
        ),
        height=13,
        color=vector(0.12, 0.16, 0.20),
        opacity=0.72,
        border=8,
        background=vector(1.0, 1.0, 1.0),
        box=True,
        align="left",
    )
    ai_label = label(
        pos=vector(4.9, 3.95, 0),
        text="AI: initializing",
        height=12,
        color=vector(0.12, 0.16, 0.20),
        opacity=0.72,
        border=8,
        background=vector(1.0, 1.0, 1.0),
        box=True,
        align="left",
    )
    state_label = label(
        pos=vector(0, -3.85, 0),
        text="",
        height=12,
        color=vector(0.12, 0.16, 0.20),
        opacity=0.0,
        box=False,
    )
    objects.extend([info_label, ai_label, state_label])

def build_atom(index=None):
    global selected_element, element_index, build_progress, round_id, last_change_time, last_state_signature, sim_time
    if index is not None:
        element_index = index % len(ELEMENTS)
    hide_all_current()
    selected_element = ELEMENTS[element_index]
    build_progress = 0.0
    round_id += 1
    last_change_time = sim_time
    last_state_signature = None
    make_nucleus(selected_element)
    make_shells_and_electrons(selected_element)
    make_charge_field(selected_element)
    make_labels(selected_element)
    create_periodic_selector()
    update_periodic_selector()
    ai_controller.on_new_round()
    make_spark(vector(0, 0, 0), selected_element["color"], count=20)

def reset_current():
    build_atom(element_index)

def next_element():
    build_atom((element_index + 1) % len(ELEMENTS))

def previous_element():
    build_atom((element_index - 1) % len(ELEMENTS))

def select_element_by_key(n):
    if 1 <= n <= min(9, len(ELEMENTS)):
        build_atom(n - 1)

# ------------------------------------------------------------
# AI state machine
# ------------------------------------------------------------

class AtomBuilderAI:
    MODES = [
        "careful_builder",
        "valence_marker",
        "bond_seeker",
        "charge_weaver",
        "orbital_dancer",
        "chaotic_spill",
        "constructive_repair",
        "artistic_wrap",
        "curious_sampler",
        "reset_ritual",
    ]

    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.mode_duration = 7.0
        self.action_cooldown = 0.0
        self.last_signature = None
        self.stagnation_time = 0.0
        self.completion_time = 0.0
        self.round_wait = 0.0
        self.override_timer = 0.0
        self.mood = "careful"
        self.scene_spin = 0.0
        self.last_mode = None

    def on_new_round(self):
        self.mode_timer = 0.0
        self.action_cooldown = 0.3
        self.stagnation_time = 0.0
        self.completion_time = 0.0
        self.round_wait = 0.0
        self.override_timer = 0.0
        self.scene_spin = random.uniform(-0.12, 0.12)
        self.choose_mode(force=True)

    def read_state(self):
        attached = sum(1 for site in bond_sites if site.occupied)
        total_sites = len(bond_sites)
        marked = sum(1 for e in electrons if e.marked)
        valence_count = sum(1 for e in electrons if e.valence)
        active_probes = len(bond_probes)
        active_charge = len(charge_particles)
        complete = (total_sites == 0 and build_progress >= 0.98) or (total_sites > 0 and attached >= total_sites)
        empty_or_halted = (len(electrons) == 0 or build_progress < 0.02 and sim_time > 2)
        signature = (
            selected_element["symbol"] if selected_element else "?",
            round(build_progress, 2),
            attached,
            total_sites,
            marked,
            active_probes,
            active_charge,
        )
        return {
            "element": selected_element,
            "attached_bonds": attached,
            "total_bond_sites": total_sites,
            "marked_electrons": marked,
            "valence_count": valence_count,
            "active_probes": active_probes,
            "active_charge": active_charge,
            "complete": complete,
            "empty_or_halted": empty_or_halted,
            "signature": signature,
        }

    def detect_stagnation(self, state, dt):
        if state["signature"] == self.last_signature:
            self.stagnation_time += dt
        else:
            self.stagnation_time = 0.0
            self.last_signature = state["signature"]

        if state["complete"]:
            self.completion_time += dt
        else:
            self.completion_time = 0.0

        return self.stagnation_time > 6.5 or self.completion_time > 4.0 or state["empty_or_halted"]

    def choose_mode(self, force=False):
        if not force and self.mode_timer < self.mode_duration:
            return
        previous = self.mode
        choices = self.MODES[:]
        if previous in choices and len(choices) > 1:
            choices.remove(previous)

        # Weighted behavior based on element type and current state.
        elem = selected_element or ELEMENTS[element_index]
        if elem["group"] in ("noble gas",):
            weighted = ["charge_weaver", "orbital_dancer", "artistic_wrap", "curious_sampler", "reset_ritual"]
        elif elem.get("bonds", 0) >= 3:
            weighted = ["bond_seeker", "valence_marker", "constructive_repair", "artistic_wrap", "careful_builder"]
        elif elem["charge"] != 0:
            weighted = ["charge_weaver", "bond_seeker", "curious_sampler", "chaotic_spill", "constructive_repair"]
        else:
            weighted = choices

        self.mode = random.choice(weighted)
        if self.mode not in self.MODES:
            self.mode = random.choice(choices)
        self.mode_index = self.MODES.index(self.mode)
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(5.5, 11.0)
        self.action_cooldown = random.uniform(0.05, 0.55)
        self.mood = self.mode.split("_")[0]

    def cycle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.mode_timer = 0.0
        self.action_cooldown = 0.0

    def update(self, dt):
        if not self.enabled or self.override_timer > 0:
            self.override_timer = max(0.0, self.override_timer - dt)
            return

        state = self.read_state()
        stagnant = self.detect_stagnation(state, dt)
        self.mode_timer += dt
        self.action_cooldown -= dt

        if stagnant:
            self.mode = "reset_ritual"
            self.mode_index = self.MODES.index(self.mode)
            self.mode_timer = 0.0

        if self.action_cooldown <= 0:
            self.act(state)
            self.action_cooldown = random.uniform(0.35, 1.4)

        self.choose_mode(force=False)
        self.update_camera(dt)
        self.update_label(state, stagnant)

    def update_camera(self, dt):
        if self.mode in ("orbital_dancer", "artistic_wrap", "reset_ritual"):
            self.scene_spin += 0.025 * dt
            scene.forward = rotate(scene.forward, angle=0.015 * dt, axis=vector(0, 1, 0))
        elif self.mode == "chaotic_spill":
            scene.center = vlerp(scene.center, rand_vec(0.25), 0.015)
        else:
            scene.center = vlerp(scene.center, vector(0, 0, 0), 0.02)

    def act(self, state):
        if self.mode == "careful_builder":
            self.act_careful_builder(state)
        elif self.mode == "valence_marker":
            self.act_valence_marker(state)
        elif self.mode == "bond_seeker":
            self.act_bond_seeker(state)
        elif self.mode == "charge_weaver":
            self.act_charge_weaver(state)
        elif self.mode == "orbital_dancer":
            self.act_orbital_dancer(state)
        elif self.mode == "chaotic_spill":
            self.act_chaotic_spill(state)
        elif self.mode == "constructive_repair":
            self.act_constructive_repair(state)
        elif self.mode == "artistic_wrap":
            self.act_artistic_wrap(state)
        elif self.mode == "curious_sampler":
            self.act_curious_sampler(state)
        elif self.mode == "reset_ritual":
            self.act_reset_ritual(state)

    def act_careful_builder(self, state):
        global build_progress
        build_progress = min(1.0, build_progress + random.uniform(0.08, 0.16))
        if electrons:
            random.choice(electrons).dip += random.uniform(-0.25, 0.25)
        make_spark(vector(0, 0, 0), selected_element["color"], count=3)

    def act_valence_marker(self, state):
        valence = [e for e in electrons if e.valence]
        if valence:
            e = random.choice(valence)
            e.marked = not e.marked
            mark = ring(
                pos=e.body.pos,
                axis=vector(0, 1, 0),
                radius=0.22,
                thickness=0.012,
                color=MARK_COLOR,
                opacity=0.70,
            )
            temporary_marks.append(mark)
            objects.append(mark)
            make_spark(e.body.pos, MARK_COLOR, count=4)

    def act_bond_seeker(self, state):
        open_sites = [s for s in bond_sites if not s.occupied]
        if open_sites:
            site = random.choice(open_sites)
            origin = site.pos + rand_vec(1.9) + safe_norm(site.pos) * random.uniform(1.5, 2.8)
            bond_probes.append(BondProbe(origin=origin, target_site=site))
            site.strength = 0.7
        else:
            self.mode = "constructive_repair"
            self.mode_timer = 0.0

    def act_charge_weaver(self, state):
        q = selected_element["charge"]
        sign = 1 if q > 0 else -1 if q < 0 else random.choice([-1, 1])
        for _ in range(random.randint(2, 5)):
            charge_particles.append(ChargeParticle(sign))
        if radius_halo:
            radius_halo.opacity = min(0.12, radius_halo.opacity + 0.012)

    def act_orbital_dancer(self, state):
        for e in random.sample(electrons, min(len(electrons), random.randint(2, 6))):
            e.speed *= random.uniform(0.92, 1.12)
            e.dip += random.uniform(-0.18, 0.18)
        for ring_obj in shell_rings:
            ring_obj.opacity = clamp(ring_obj.opacity + random.uniform(-0.04, 0.05), 0.12, 0.55)

    def act_chaotic_spill(self, state):
        for _ in range(random.randint(3, 8)):
            bond_probes.append(BondProbe(origin=rand_vec(random.uniform(3.0, 6.0)), target_site=random.choice(bond_sites) if bond_sites and random.random() < 0.45 else None))
        for _ in range(random.randint(3, 7)):
            charge_particles.append(ChargeParticle(random.choice([-1, 0, 1])))
        make_spark(rand_vec(1.5), vector(1.0, 0.55, 0.25), count=10)

    def act_constructive_repair(self, state):
        if bond_sites:
            # Re-open one weak site sometimes, then rebuild it.
            if random.random() < 0.20:
                occupied = [s for s in bond_sites if s.occupied]
                if occupied:
                    site = random.choice(occupied)
                    site.occupied = False
                    site.strength = 0.1
            self.act_bond_seeker(state)
        else:
            self.act_charge_weaver(state)

    def act_artistic_wrap(self, state):
        r = radius_halo.radius if radius_halo else 4.0
        axis_choices = [vector(0, 1, 0), vector(1, 0.25, 0), vector(0.2, 0.2, 1)]
        wrap = ring(
            pos=vector(0, 0, 0),
            axis=random.choice(axis_choices),
            radius=random.uniform(0.75 * r, 1.05 * r),
            thickness=random.uniform(0.006, 0.018),
            color=color_mix(selected_element["color"], vector(0.3, 0.55, 1.0), random.random()),
            opacity=0.16,
        )
        temporary_marks.append(wrap)
        objects.append(wrap)
        make_spark(rand_vec(0.8), selected_element["color"], count=3)

    def act_curious_sampler(self, state):
        # Briefly preview nearby elements as ghost atoms.
        for g in ghost_atoms:
            try:
                g.visible = False
            except Exception:
                pass
        ghost_atoms.clear()
        for offset in [-1, 1]:
            elem = ELEMENTS[(element_index + offset) % len(ELEMENTS)]
            pos = vector(5.5 * offset, -1.6, 0)
            ghost = sphere(pos=pos, radius=0.45 + 0.08 * len(shell_distribution(elem["z"])), color=elem["color"], opacity=0.16)
            txt = label(pos=pos + vector(0, 0.85, 0), text=f"{elem['symbol']}\npreview", height=10, opacity=0.0, color=vector(0.15,0.2,0.25), box=False)
            ghost_atoms.extend([ghost, txt])
            objects.extend([ghost, txt])

    def act_reset_ritual(self, state):
        self.round_wait += 1.0
        make_spark(vector(0, 0, 0), vector(0.85, 0.65, 1.0), count=12)
        if self.round_wait >= 3.0:
            if random.random() < 0.60:
                build_atom((element_index + random.choice([1, 1, 1, 2, -1])) % len(ELEMENTS))
            else:
                reset_current()

    def update_label(self, state, stagnant):
        if ai_label:
            status = "ON" if ai_enabled else "OFF"
            ai_label.text = (
                f"AI controller: {status}\n"
                f"Mode: {self.mode}\n"
                f"Mood: {self.mood}\n"
                f"Build progress: {build_progress:.2f}\n"
                f"Bonds attached: {state['attached_bonds']}/{state['total_bond_sites']}\n"
                f"Marked valence e⁻: {state['marked_electrons']}/{state['valence_count']}\n"
                f"Stagnation: {self.stagnation_time:.1f}s | Complete: {state['complete']}\n"
                f"A/P/R/N/B/M/O controls active"
            )

ai_controller = AtomBuilderAI()

# ------------------------------------------------------------
# Human override actions
# ------------------------------------------------------------

def human_override_spill():
    ai_controller.override_timer = 1.5
    for site in bond_sites:
        if random.random() < 0.65:
            bond_probes.append(BondProbe(origin=site.pos + rand_vec(2.7), target_site=site))
            site.strength = 0.8
    for _ in range(12):
        charge_particles.append(ChargeParticle(random.choice([-1, 0, 1])))
    for e in random.sample(electrons, min(6, len(electrons))):
        e.dip += random.uniform(-0.55, 0.55)
        e.marked = True
    make_spark(vector(0, 0, 0), vector(1.0, 0.65, 0.15), count=20)

def print_controls():
    print(__doc__)

def keydown(evt):
    global paused, ai_enabled
    k = evt.key.lower()
    if k == "a":
        ai_enabled = not ai_enabled
        ai_controller.enabled = ai_enabled
    elif k == "p":
        paused = not paused
    elif k == "r":
        reset_current()
    elif k == "n":
        next_element()
    elif k == "b":
        previous_element()
    elif k == "m":
        ai_controller.cycle_mode()
    elif k == "c":
        clear_marks()
        clear_probes_and_charge()
    elif k == "o":
        human_override_spill()
    elif k == "h":
        print_controls()
    elif k in "123456789":
        select_element_by_key(int(k))

scene.bind("keydown", keydown)

# ------------------------------------------------------------
# Update loop helpers
# ------------------------------------------------------------

def update_build_visibility(dt):
    global build_progress

    # If no AI is active, still let the atom build slowly.
    if not ai_enabled:
        build_progress = min(1.0, build_progress + 0.035 * dt)

    for i, (part, base_pos, kind, phase) in enumerate(nucleus_particles):
        appear_limit = (i + 1) / max(1, len(nucleus_particles))
        visible_factor = 1.0 if build_progress >= appear_limit else 0.14
        part.opacity = lerp(part.opacity, 0.94 * visible_factor, 0.12)
        jitter = 0.018 * vector(sin(sim_time * 2.1 + phase), cos(sim_time * 1.7 + phase), sin(sim_time * 1.3 + phase))
        part.pos = base_pos + jitter

    for i, ring_obj in enumerate(shell_rings):
        shell_limit = 0.20 + 0.08 * i
        target_opacity = 0.30 if build_progress >= shell_limit else 0.04
        ring_obj.opacity = lerp(ring_obj.opacity, target_opacity, 0.06)
        ring_obj.rotate(angle=0.04 * dt * (1 if i % 2 == 0 else -1), axis=ring_obj.axis)

    for i, lab in enumerate(shell_labels):
        lab.opacity = 0.0

    for i, e in enumerate(electrons):
        electron_limit = 0.32 + 0.55 * ((i + 1) / max(1, len(electrons)))
        e.body.opacity = 1.0 if build_progress >= electron_limit else 0.12

    for site in bond_sites:
        site.body.visible = build_progress > 0.72
        site.stem.visible = build_progress > 0.72
        site.label.visible = build_progress > 0.72

    if radius_halo:
        radius_halo.opacity = lerp(radius_halo.opacity, 0.055 if build_progress > 0.25 else 0.01, 0.03)
    if valence_halo:
        valence_halo.opacity = lerp(valence_halo.opacity, 0.040 if build_progress > 0.65 else 0.005, 0.03)

    if state_label:
        state_label.text = "paused" if paused else f"{selected_element['name']} atom builder | AI {'on' if ai_enabled else 'off'} | round {round_id}"

def update_dynamic_entities(dt):
    for e in electrons:
        e.update(sim_time, dt)
    for site in bond_sites:
        site.update(sim_time, dt)

    for p in bond_probes[:]:
        p.update(dt)
        if p.expired():
            p.hide()
            bond_probes.remove(p)

    for c in charge_particles[:]:
        c.update(dt)
        if c.expired():
            c.hide()
            charge_particles.remove(c)

    for s in sparks[:]:
        s.update(dt)
        if s.expired():
            s.hide()
            sparks.remove(s)

    for line, site, probe_body in bond_lines[:]:
        if not line.visible:
            continue
        line.pos = site.pos
        line.axis = probe_body.pos - site.pos
        line.opacity = clamp(line.opacity * 0.999 + 0.001, 0.2, 0.78)

    # Temporary wrap marks slowly fade.
    for obj in temporary_marks[:]:
        try:
            if hasattr(obj, "opacity"):
                obj.opacity *= 0.997
                if obj.opacity < 0.025:
                    obj.visible = False
                    temporary_marks.remove(obj)
        except Exception:
            pass

def update_highlights():
    update_periodic_selector()
    # Glow selected valence shell if bonding is active.
    if valence_halo:
        occupied = sum(1 for s in bond_sites if s.occupied)
        total = max(1, len(bond_sites))
        valence_halo.opacity = clamp(0.025 + 0.055 * occupied / total + 0.015 * sin(sim_time * 2), 0.01, 0.12)

# ------------------------------------------------------------
# Initialize and run
# ------------------------------------------------------------

build_atom(element_index)
print_controls()

last = time.time()
while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last, 0.001, 0.05)
    last = now

    if paused:
        if ai_label:
            ai_label.text = (
                f"AI controller: {'ON' if ai_enabled else 'OFF'}\n"
                f"Mode: {ai_controller.mode}\n"
                f"PAUSED\n"
                f"Press P to resume"
            )
        continue

    sim_time += dt
    update_build_visibility(dt)
    update_dynamic_entities(dt)
    update_highlights()

    if ai_enabled:
        ai_controller.enabled = True
        ai_controller.update(dt)
    else:
        ai_controller.enabled = False
        state = ai_controller.read_state()
        ai_controller.update_label(state, stagnant=False)
