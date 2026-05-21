#!/usr/bin/env python3
"""
Cell Organelle Ecosystem — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python cell_organelle_ecosystem_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    M       cycle AI behavior mode
    R       reset round
    O       human override: nutrient/protein burst
    V       release vesicles from Golgi
    L       send lysosomes toward waste
    C       clear marks and trails
    H       print controls
    + / =   increase AI intensity
    - / _   decrease AI intensity

Scene concept:
    A living cell interior is represented as a transparent cell boundary. The nucleus
    stays central and releases mRNA signals. Ribosomes attach to the rough ER or float
    freely and generate protein packets. ER membranes receive packets and pass them to
    vesicles. Vesicles travel to the Golgi body for processing, then deliver cargo to
    mitochondria, the membrane, or lysosomes. Lysosomes remove waste particles. The AI
    reads the state and changes behavior modes to organize, energize, repair, traffic,
    clean, orbit, disrupt, or reset the cellular ecosystem.

This file is self-contained and intentionally uses VPython primitives only.
"""

from vpython import *
import random
import math
import time

# -----------------------------------------------------------------------------
# Scene setup
# -----------------------------------------------------------------------------

scene.title = "Cell Organelle Ecosystem — AI Controlled VPython Simulation"
scene.width = 1280
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(-0.35, -0.25, -1)
scene.center = vector(0, 0, 0)
scene.range = 9.5
scene.autoscale = False
scene.userzoom = True
scene.userspin = True

CELL_RADIUS = 7.0
WORLD_LIMIT = CELL_RADIUS * 0.96
DT = 0.018
SOFTENING = 0.08

# Light palette
COLORS = {
    "membrane": vector(0.56, 0.78, 0.94),
    "cytoplasm": vector(0.78, 0.91, 1.00),
    "nucleus": vector(0.78, 0.62, 0.95),
    "nucleolus": vector(0.48, 0.28, 0.82),
    "mitochondria": vector(1.00, 0.62, 0.42),
    "mito_inner": vector(1.00, 0.86, 0.35),
    "ribosome": vector(0.28, 0.34, 0.44),
    "er": vector(0.39, 0.73, 0.93),
    "golgi": vector(0.98, 0.72, 0.36),
    "lysosome": vector(0.92, 0.38, 0.53),
    "vesicle": vector(0.56, 0.86, 0.72),
    "protein": vector(0.34, 0.76, 0.58),
    "mrna": vector(0.45, 0.30, 0.90),
    "waste": vector(0.45, 0.40, 0.36),
    "energy": vector(1.00, 0.90, 0.32),
    "mark": vector(1.00, 0.50, 0.30),
    "white": vector(1, 1, 1),
}

random.seed(8)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def vmag(v):
    return mag(v)

def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)).norm()
    return v / m

def rand_vec(scale=1.0):
    return vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)) * scale

def rand_inside(radius):
    while True:
        p = rand_vec(radius)
        if mag(p) <= radius:
            return p

def lerp_vec(a, b, t):
    return a * (1 - t) + b * t

def keep_inside(pos, vel, radius=WORLD_LIMIT, bounce=0.72):
    m = mag(pos)
    if m > radius:
        normal = safe_norm(pos)
        pos = normal * radius
        outward = dot(vel, normal)
        if outward > 0:
            vel = vel - (1 + bounce) * outward * normal
    return pos, vel

def spiral_position(base, radius, theta, height=0.0):
    return base + vector(radius * cos(theta), height, radius * sin(theta))

def make_label(text, pos, height=11, color_value=vector(0.20, 0.24, 0.30)):
    return label(
        text=text,
        pos=pos,
        height=height,
        border=4,
        box=False,
        opacity=0.0,
        color=color_value,
    )

def set_visible_group(items, visible=True):
    for item in items:
        try:
            item.visible = visible
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Static environment
# -----------------------------------------------------------------------------

cell_membrane = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS,
    color=COLORS["membrane"],
    opacity=0.12,
    shininess=0.2,
)

cell_glow = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS * 0.985,
    color=COLORS["cytoplasm"],
    opacity=0.055,
    shininess=0.0,
)

cytoplasm_dots = []
for i in range(110):
    p = rand_inside(CELL_RADIUS * 0.93)
    dot_obj = sphere(
        pos=p,
        radius=random.uniform(0.025, 0.055),
        color=vector(0.60, 0.78, 0.88),
        opacity=random.uniform(0.18, 0.42),
        shininess=0,
    )
    cytoplasm_dots.append(dot_obj)

title_label = make_label(
    "Cell organelle ecosystem\nA: AI  P: pause  M: mode  O: burst  R: reset  H: controls",
    vector(0, CELL_RADIUS + 1.15, 0),
    13,
)
status_label = make_label("", vector(-7.4, -7.65, 0), 11)
mode_label = make_label("", vector(5.0, 7.55, 0), 11)

# -----------------------------------------------------------------------------
# Core organelles
# -----------------------------------------------------------------------------

class Nucleus:
    def __init__(self):
        self.pos = vector(-0.75, 0.35, 0)
        self.radius = 1.45
        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=COLORS["nucleus"],
            opacity=0.58,
            shininess=0.35,
        )
        self.shell = sphere(
            pos=self.pos,
            radius=self.radius * 1.04,
            color=COLORS["white"],
            opacity=0.12,
            shininess=0.2,
        )
        self.nucleolus = sphere(
            pos=self.pos + vector(-0.25, 0.22, 0.18),
            radius=0.38,
            color=COLORS["nucleolus"],
            opacity=0.86,
        )
        self.rings = []
        for k in range(3):
            r = ring(
                pos=self.pos,
                axis=vector(0, 1, 0).rotate(angle=k * pi / 3, axis=vector(0, 0, 1)),
                radius=self.radius * (0.70 + 0.10 * k),
                thickness=0.018,
                color=vector(0.50, 0.36, 0.84),
                opacity=0.36,
            )
            self.rings.append(r)
        self.phase = 0.0

    def update(self, dt):
        self.phase += dt
        pulse = 1.0 + 0.035 * sin(self.phase * 1.7)
        self.body.radius = self.radius * pulse
        self.shell.radius = self.radius * 1.04 * pulse
        self.nucleolus.pos = self.pos + vector(
            -0.25 + 0.04 * sin(self.phase * 1.3),
            0.22 + 0.03 * cos(self.phase * 1.8),
            0.18,
        )
        for i, r in enumerate(self.rings):
            r.rotate(angle=0.004 + i * 0.0009, axis=vector(0, 1, 0), origin=self.pos)

class Mitochondrion:
    def __init__(self, idx, pos):
        self.idx = idx
        self.pos = pos
        self.vel = rand_vec(0.045)
        self.energy = random.uniform(0.4, 0.9)
        self.target = None
        self.phase = random.uniform(0, 2 * pi)
        self.body = ellipsoid(
            pos=self.pos,
            length=1.15,
            height=0.48,
            width=0.60,
            color=COLORS["mitochondria"],
            opacity=0.78,
            shininess=0.25,
        )
        self.cristae = []
        for j in range(4):
            offset = -0.34 + j * 0.22
            c = helix(
                pos=self.pos + vector(offset, -0.02, 0),
                axis=vector(0.15, 0, 0),
                radius=0.14,
                thickness=0.018,
                coils=1.2,
                color=COLORS["mito_inner"],
                opacity=0.85,
            )
            self.cristae.append(c)
        self.label = make_label("mitochondrion", self.pos + vector(0, 0.65, 0), 8)

    def apply_force(self, f):
        self.vel += f

    def update(self, dt):
        self.phase += dt
        if self.target is not None:
            self.vel += safe_norm(self.target - self.pos) * 0.008
        self.vel += rand_vec(0.002)
        self.vel *= 0.986
        self.pos += self.vel
        self.pos, self.vel = keep_inside(self.pos, self.vel, WORLD_LIMIT - 0.7)
        self.energy = clamp(self.energy + 0.0009 + 0.002 * sin(self.phase * 1.2), 0, 1.4)

        self.body.pos = self.pos
        self.body.rotate(angle=0.007, axis=vector(0, 1, 0), origin=self.pos)
        glow = 0.35 + 0.55 * clamp(self.energy, 0, 1)
        self.body.color = lerp_vec(vector(0.90, 0.52, 0.38), vector(1.0, 0.82, 0.24), glow)
        for j, c in enumerate(self.cristae):
            c.pos = self.pos + vector(-0.35 + j * 0.23, -0.02 + 0.03 * sin(self.phase * 3 + j), 0)
            c.axis = vector(0.15, 0.03 * sin(self.phase + j), 0.02 * cos(self.phase + j))
        self.label.pos = self.pos + vector(0, 0.68, 0)

class ERNetwork:
    def __init__(self):
        self.anchor = vector(-0.65, 0.20, 0)
        self.phase = 0.0
        self.segments = []
        self.rough_sites = []
        for i in range(7):
            theta0 = i * 0.58 - 1.8
            pts = []
            for j in range(34):
                t = j / 33.0
                radius = 1.85 + 0.24 * sin(j * 0.8 + i)
                theta = theta0 + t * 1.55
                y = -1.05 + i * 0.34 + 0.12 * sin(t * 7 + i)
                pts.append(vector(radius * cos(theta) - 0.3, y, radius * sin(theta) * 0.55))
            c = curve(pos=pts, radius=0.035, color=COLORS["er"], opacity=0.68)
            self.segments.append(c)
            if i % 2 == 0:
                for j in range(4, 29, 6):
                    site = sphere(pos=pts[j], radius=0.075, color=COLORS["ribosome"], opacity=0.82)
                    self.rough_sites.append(site)
        self.label = make_label("rough/smooth ER", vector(-2.6, -1.95, 1.2), 9)

    def update(self, dt):
        self.phase += dt
        for i, c in enumerate(self.segments):
            c.color = lerp_vec(COLORS["er"], vector(0.60, 0.88, 1.0), 0.5 + 0.5 * sin(self.phase * 1.7 + i))
        for j, site in enumerate(self.rough_sites):
            site.radius = 0.07 + 0.015 * sin(self.phase * 4 + j)

class GolgiBody:
    def __init__(self):
        self.pos = vector(2.55, -0.55, 0.15)
        self.phase = 0
        self.stacks = []
        for i in range(6):
            c = curve(
                pos=[
                    self.pos + vector(-0.85, -0.45 + i * 0.18, -0.10),
                    self.pos + vector(-0.42, -0.36 + i * 0.18, 0.18),
                    self.pos + vector(0.08, -0.32 + i * 0.18, 0.25),
                    self.pos + vector(0.58, -0.35 + i * 0.18, 0.12),
                    self.pos + vector(0.96, -0.43 + i * 0.18, -0.08),
                ],
                radius=0.055,
                color=COLORS["golgi"],
                opacity=0.78,
            )
            self.stacks.append(c)
        self.processing = 0.0
        self.label = make_label("Golgi body", self.pos + vector(0.1, 0.95, 0), 9)

    def update(self, dt):
        self.phase += dt
        for i, c in enumerate(self.stacks):
            c.radius = 0.052 + 0.012 * sin(self.phase * 2.2 + i)
            c.color = lerp_vec(vector(0.94, 0.64, 0.28), vector(1.0, 0.83, 0.42), clamp(self.processing, 0, 1))
        self.processing *= 0.985

class Lysosome:
    def __init__(self, idx, pos):
        self.idx = idx
        self.pos = pos
        self.vel = rand_vec(0.04)
        self.target = None
        self.digesting = 0.0
        self.phase = random.random() * 10
        self.body = sphere(
            pos=self.pos,
            radius=0.36,
            color=COLORS["lysosome"],
            opacity=0.75,
            shininess=0.4,
        )
        self.ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=0.40,
            thickness=0.015,
            color=vector(0.95, 0.60, 0.70),
            opacity=0.55,
        )
        self.label = make_label("lysosome", self.pos + vector(0, 0.48, 0), 7)

    def update(self, dt):
        self.phase += dt
        if self.target is not None:
            self.vel += safe_norm(self.target - self.pos) * 0.015
        else:
            self.vel += rand_vec(0.003)
        self.vel *= 0.982
        self.pos += self.vel
        self.pos, self.vel = keep_inside(self.pos, self.vel, WORLD_LIMIT - 0.45)
        self.digesting *= 0.97
        self.body.pos = self.pos
        self.body.radius = 0.34 + 0.06 * self.digesting + 0.02 * sin(self.phase * 3.5)
        self.ring.pos = self.pos
        self.ring.axis = vector(sin(self.phase), 1, cos(self.phase)).norm()
        self.ring.radius = self.body.radius * 1.15
        self.ring.rotate(angle=0.03, axis=vector(0, 1, 0), origin=self.pos)
        self.label.pos = self.pos + vector(0, 0.50, 0)

class Ribosome:
    def __init__(self, idx, pos, attached=False):
        self.idx = idx
        self.pos = pos
        self.vel = rand_vec(0.035)
        self.attached = attached
        self.attach_pos = pos if attached else None
        self.translation = random.random()
        self.phase = random.random() * 10
        self.body = sphere(
            pos=self.pos,
            radius=0.14,
            color=COLORS["ribosome"],
            opacity=0.88,
            shininess=0.15,
        )
        self.small = sphere(
            pos=self.pos + vector(0.08, 0.04, 0.02),
            radius=0.075,
            color=vector(0.42, 0.47, 0.58),
            opacity=0.88,
        )
        self.label = None

    def update(self, dt, er_sites):
        self.phase += dt
        self.translation += dt * (0.16 if self.attached else 0.06)
        if self.attached and self.attach_pos is not None:
            wiggle = vector(0.03 * sin(self.phase * 4), 0.02 * cos(self.phase * 5), 0.03 * sin(self.phase * 3.2))
            self.pos = self.attach_pos + wiggle
            if random.random() < 0.0008:
                self.attached = False
                self.attach_pos = None
                self.vel = rand_vec(0.08)
        else:
            self.vel += rand_vec(0.0035)
            self.vel += safe_norm(vector(0, 0, 0) - self.pos) * 0.0007
            self.vel *= 0.987
            self.pos += self.vel
            self.pos, self.vel = keep_inside(self.pos, self.vel, WORLD_LIMIT - 0.15)
            if er_sites and random.random() < 0.0018:
                site = random.choice(er_sites)
                if mag(site.pos - self.pos) < 1.2:
                    self.attached = True
                    self.attach_pos = vector(site.pos.x, site.pos.y, site.pos.z)
        self.body.pos = self.pos
        self.small.pos = self.pos + vector(0.08 * cos(self.phase), 0.04, 0.08 * sin(self.phase))
        self.body.radius = 0.13 + 0.018 * sin(self.translation * 2 * pi)

class Vesicle:
    def __init__(self, idx, pos, cargo="empty", target_name="golgi"):
        self.idx = idx
        self.pos = pos
        self.vel = rand_vec(0.035)
        self.cargo = cargo
        self.target_name = target_name
        self.target = None
        self.state = "travel"
        self.age = 0
        self.phase = random.random() * 10
        self.body = sphere(
            pos=self.pos,
            radius=0.24,
            color=COLORS["vesicle"],
            opacity=0.46,
            shininess=0.55,
        )
        self.inner = sphere(
            pos=self.pos,
            radius=0.09,
            color=self.cargo_color(),
            opacity=0.82,
        )
        self.trail = curve(pos=[self.pos], radius=0.012, color=self.cargo_color(), opacity=0.35)
        self.marked = False

    def cargo_color(self):
        if self.cargo == "protein":
            return COLORS["protein"]
        if self.cargo == "energy":
            return COLORS["energy"]
        if self.cargo == "waste":
            return COLORS["waste"]
        if self.cargo == "signal":
            return COLORS["mrna"]
        return COLORS["white"]

    def update_target(self, world):
        if self.target_name == "golgi":
            self.target = world.golgi.pos + rand_vec(0.16)
        elif self.target_name == "membrane":
            self.target = safe_norm(self.pos + rand_vec(0.8)) * (CELL_RADIUS * 0.84)
        elif self.target_name == "mitochondrion" and world.mitochondria:
            self.target = min(world.mitochondria, key=lambda m: mag(m.pos - self.pos)).pos
        elif self.target_name == "lysosome" and world.lysosomes:
            self.target = min(world.lysosomes, key=lambda l: mag(l.pos - self.pos)).pos
        elif self.target_name == "nucleus":
            self.target = world.nucleus.pos + rand_vec(0.4)
        else:
            self.target = rand_inside(CELL_RADIUS * 0.78)

    def update(self, dt, world):
        self.age += dt
        self.phase += dt
        self.update_target(world)
        if self.target is not None:
            self.vel += safe_norm(self.target - self.pos) * 0.012
        self.vel += rand_vec(0.002)
        self.vel *= 0.985
        self.pos += self.vel
        self.pos, self.vel = keep_inside(self.pos, self.vel, WORLD_LIMIT - 0.25)

        if self.target is not None and mag(self.target - self.pos) < 0.42:
            self.arrive(world)

        self.body.pos = self.pos
        self.body.radius = 0.22 + 0.035 * sin(self.phase * 4)
        self.body.color = lerp_vec(COLORS["vesicle"], self.cargo_color(), 0.25 if not self.marked else 0.72)
        self.inner.pos = self.pos + vector(0.04 * sin(self.phase * 2.5), 0.03 * cos(self.phase * 2), 0.02)
        self.inner.color = self.cargo_color()
        if int(self.age * 18) % 3 == 0:
            self.trail.append(pos=self.pos)
            if self.trail.npoints > 55:
                self.trail.pop(0)

    def arrive(self, world):
        if self.target_name == "golgi":
            world.golgi.processing = 1.0
            self.target_name = random.choice(["membrane", "mitochondrion", "lysosome"])
            self.marked = True
            world.add_mark(self.pos, "processed")
        elif self.target_name == "mitochondrion":
            for m in world.mitochondria:
                if mag(m.pos - self.pos) < 0.75:
                    m.energy = clamp(m.energy + 0.20, 0, 1.4)
            self.state = "delivered"
            world.add_energy_particle(self.pos)
        elif self.target_name == "lysosome":
            for l in world.lysosomes:
                if mag(l.pos - self.pos) < 0.75:
                    l.digesting = 1.0
            self.state = "delivered"
            world.add_mark(self.pos, "digest")
        elif self.target_name == "membrane":
            self.state = "delivered"
            world.add_mark(self.pos, "export")
        elif self.target_name == "nucleus":
            self.state = "delivered"
            world.add_mark(self.pos, "signal")

    def hide(self):
        set_visible_group([self.body, self.inner, self.trail], False)

class Packet:
    def __init__(self, idx, pos, kind="protein"):
        self.idx = idx
        self.kind = kind
        self.pos = pos
        self.vel = rand_vec(0.055)
        self.age = 0
        self.body = sphere(
            pos=self.pos,
            radius=0.085 if kind != "waste" else 0.11,
            color=self.color(),
            opacity=0.86,
            make_trail=False,
        )

    def color(self):
        if self.kind == "protein":
            return COLORS["protein"]
        if self.kind == "mrna":
            return COLORS["mrna"]
        if self.kind == "energy":
            return COLORS["energy"]
        if self.kind == "waste":
            return COLORS["waste"]
        return COLORS["white"]

    def update(self, dt):
        self.age += dt
        self.vel += rand_vec(0.004)
        self.vel += safe_norm(vector(0, 0, 0) - self.pos) * 0.0004
        self.vel *= 0.987
        self.pos += self.vel
        self.pos, self.vel = keep_inside(self.pos, self.vel, WORLD_LIMIT - 0.1)
        self.body.pos = self.pos
        self.body.radius = (0.08 if self.kind != "waste" else 0.11) * (1 + 0.18 * sin(self.age * 8))

    def hide(self):
        self.body.visible = False

class FloatingMark:
    def __init__(self, pos, text, color_value=COLORS["mark"]):
        self.pos = pos
        self.age = 0
        self.life = 2.2
        self.label = label(
            text=text,
            pos=pos,
            height=8,
            color=color_value,
            box=False,
            opacity=0,
            border=2,
        )
        self.ring = ring(pos=pos, axis=safe_norm(rand_vec(1)), radius=0.16, thickness=0.014, color=color_value, opacity=0.65)

    def update(self, dt):
        self.age += dt
        self.pos += vector(0, 0.012, 0)
        self.label.pos = self.pos + vector(0, 0.22, 0)
        self.ring.pos = self.pos
        self.ring.radius += 0.010
        self.ring.opacity = max(0, 0.65 * (1 - self.age / self.life))
        self.label.color = lerp_vec(COLORS["mark"], COLORS["white"], self.age / self.life)

    def expired(self):
        return self.age > self.life

    def hide(self):
        self.label.visible = False
        self.ring.visible = False

# -----------------------------------------------------------------------------
# World state
# -----------------------------------------------------------------------------

class CellWorld:
    def __init__(self):
        self.nucleus = Nucleus()
        self.er = ERNetwork()
        self.golgi = GolgiBody()
        self.mitochondria = []
        self.lysosomes = []
        self.ribosomes = []
        self.vesicles = []
        self.packets = []
        self.marks = []
        self.energy_particles = []
        self.round_id = 0
        self.spawn_counter = 0
        self.last_activity_score = 0
        self.reset()

    def clear_dynamic(self):
        for group in [self.mitochondria, self.lysosomes, self.ribosomes, self.vesicles, self.packets, self.marks, self.energy_particles]:
            for obj in group:
                if hasattr(obj, "hide"):
                    obj.hide()
                else:
                    try:
                        obj.visible = False
                    except Exception:
                        pass
        self.mitochondria = []
        self.lysosomes = []
        self.ribosomes = []
        self.vesicles = []
        self.packets = []
        self.marks = []
        self.energy_particles = []

    def reset(self):
        self.clear_dynamic()
        self.round_id += 1
        self.spawn_counter = 0

        mito_positions = [
            vector(-3.4, 2.1, 0.7),
            vector(3.6, 2.0, -0.8),
            vector(-3.5, -2.7, -0.6),
            vector(3.1, -2.9, 0.6),
        ]
        for i, p in enumerate(mito_positions):
            self.mitochondria.append(Mitochondrion(i, p + rand_vec(0.25)))

        for i in range(4):
            self.lysosomes.append(Lysosome(i, rand_inside(5.8)))

        er_sites = [s.pos for s in self.er.rough_sites]
        for i in range(36):
            if i < 18 and er_sites:
                self.ribosomes.append(Ribosome(i, vector(random.choice(er_sites)), attached=True))
            else:
                self.ribosomes.append(Ribosome(i, rand_inside(5.6), attached=False))

        for i in range(12):
            cargo = random.choice(["protein", "signal", "energy"])
            target = random.choice(["golgi", "membrane", "mitochondrion"])
            start = rand_inside(4.8)
            self.vesicles.append(Vesicle(i, start, cargo=cargo, target_name=target))

        for i in range(25):
            self.packets.append(Packet(i, rand_inside(4.5), kind=random.choice(["protein", "mrna", "waste"])))

        self.add_mark(vector(0, -5.7, 0), "new cell round")

    def add_mark(self, pos, text="mark"):
        self.marks.append(FloatingMark(pos, text))
        if len(self.marks) > 70:
            old = self.marks.pop(0)
            old.hide()

    def add_energy_particle(self, pos):
        p = sphere(pos=pos, radius=0.08, color=COLORS["energy"], opacity=0.85, make_trail=True, trail_radius=0.01, retain=20)
        p.vel = rand_vec(0.08)
        p.age = 0
        self.energy_particles.append(p)

    def burst_from_nucleus(self, n=8):
        for _ in range(n):
            p = self.nucleus.pos + safe_norm(rand_vec(1)) * (self.nucleus.radius + 0.1)
            self.packets.append(Packet(self.spawn_counter, p, "mrna"))
            self.spawn_counter += 1
        self.add_mark(self.nucleus.pos + vector(0, 1.6, 0), "mRNA spill")

    def protein_burst_from_er(self, n=10):
        for _ in range(n):
            site = random.choice(self.er.rough_sites)
            self.packets.append(Packet(self.spawn_counter, vector(site.pos), "protein"))
            self.spawn_counter += 1
        self.add_mark(vector(-2.5, -1.2, 0.7), "protein build")

    def golgi_release(self, n=6):
        for _ in range(n):
            cargo = random.choice(["protein", "protein", "energy", "signal"])
            target = random.choice(["membrane", "mitochondrion", "lysosome", "nucleus"])
            self.vesicles.append(Vesicle(len(self.vesicles) + self.spawn_counter, self.golgi.pos + rand_vec(0.35), cargo=cargo, target_name=target))
            self.spawn_counter += 1
        self.add_mark(self.golgi.pos + vector(0, 1.0, 0), "vesicle release")

    def create_waste(self, n=6):
        for _ in range(n):
            self.packets.append(Packet(self.spawn_counter, rand_inside(5.7), "waste"))
            self.spawn_counter += 1
        self.add_mark(rand_inside(4.5), "waste appears")

    def send_lysosomes_to_waste(self):
        wastes = [p for p in self.packets if p.kind == "waste"]
        if not wastes:
            self.create_waste(4)
            wastes = [p for p in self.packets if p.kind == "waste"]
        for lys in self.lysosomes:
            if wastes:
                target = min(wastes, key=lambda w: mag(w.pos - lys.pos))
                lys.target = target.pos
        self.add_mark(vector(0, -4.9, 0), "cleanup")

    def mark_random_vesicles(self, n=5):
        for v in random.sample(self.vesicles, min(n, len(self.vesicles))):
            v.marked = True
            v.target_name = random.choice(["golgi", "membrane", "mitochondrion", "lysosome"])
        self.add_mark(rand_inside(4.0), "traffic marked")

    def attach_more_ribosomes(self):
        free = [r for r in self.ribosomes if not r.attached]
        random.shuffle(free)
        for r in free[:8]:
            site = random.choice(self.er.rough_sites)
            r.attached = True
            r.attach_pos = vector(site.pos)
        self.add_mark(vector(-2.2, 1.7, 0), "ribosomes attach")

    def detach_some_ribosomes(self):
        attached = [r for r in self.ribosomes if r.attached]
        random.shuffle(attached)
        for r in attached[:8]:
            r.attached = False
            r.attach_pos = None
            r.vel = rand_vec(0.11)
        self.add_mark(vector(-1.0, 2.3, 0), "ribosomes detach")

    def stir_cytoplasm(self, strength=0.06):
        center = rand_inside(2.0)
        for collection in [self.mitochondria, self.lysosomes, self.ribosomes, self.vesicles, self.packets]:
            for obj in collection:
                tangent = cross(safe_norm(obj.pos - center), vector(0, 1, 0))
                if mag(tangent) < 0.01:
                    tangent = cross(safe_norm(obj.pos - center), vector(1, 0, 0))
                if hasattr(obj, "vel"):
                    obj.vel += safe_norm(tangent) * strength + rand_vec(strength * 0.25)
        self.add_mark(center, "cytoplasm swirl")

    def organize_orbit(self):
        for i, m in enumerate(self.mitochondria):
            theta = i * 2 * pi / max(1, len(self.mitochondria))
            m.target = vector(4.2 * cos(theta), 1.5 * sin(theta * 2), 4.2 * sin(theta))
        for i, l in enumerate(self.lysosomes):
            theta = i * 2 * pi / max(1, len(self.lysosomes)) + pi / 4
            l.target = vector(5.2 * cos(theta), -1.8, 5.2 * sin(theta))
        self.add_mark(vector(0, 0, 0), "organize orbit")

    def release_targets(self):
        for m in self.mitochondria:
            m.target = None
        for l in self.lysosomes:
            l.target = None

    def digest_waste_collisions(self):
        consumed = []
        for lys in self.lysosomes:
            for p in self.packets:
                if p.kind == "waste" and mag(lys.pos - p.pos) < 0.38:
                    lys.digesting = 1.0
                    consumed.append(p)
                    self.add_energy_particle(lys.pos)
        for p in consumed:
            if p in self.packets:
                p.hide()
                self.packets.remove(p)

    def packet_to_vesicle_collisions(self):
        converted = []
        for p in self.packets:
            if p.kind in ["protein", "mrna", "energy"] and p.age > 0.45:
                near_golgi = mag(p.pos - self.golgi.pos) < 1.2
                near_er = any(mag(p.pos - s.pos) < 0.42 for s in self.er.rough_sites[::3])
                if near_golgi or near_er or random.random() < 0.0008:
                    cargo = "protein" if p.kind == "protein" else "signal"
                    self.vesicles.append(Vesicle(len(self.vesicles) + self.spawn_counter, vector(p.pos), cargo=cargo, target_name="golgi"))
                    self.spawn_counter += 1
                    converted.append(p)
        for p in converted:
            if p in self.packets:
                p.hide()
                self.packets.remove(p)

    def remove_delivered_vesicles(self):
        delivered = [v for v in self.vesicles if v.state == "delivered" or v.age > 40]
        for v in delivered:
            v.hide()
            if v in self.vesicles:
                self.vesicles.remove(v)

    def update_energy_particles(self, dt):
        alive = []
        for p in self.energy_particles:
            p.age += dt
            p.vel += rand_vec(0.006)
            p.vel *= 0.96
            p.pos += p.vel
            p.pos, p.vel = keep_inside(p.pos, p.vel, WORLD_LIMIT - 0.1)
            p.opacity = max(0, 0.85 * (1 - p.age / 2.5))
            if p.age < 2.5:
                alive.append(p)
            else:
                p.visible = False
        self.energy_particles = alive

    def state_variables(self):
        attached = sum(1 for r in self.ribosomes if r.attached)
        free = len(self.ribosomes) - attached
        proteins = sum(1 for p in self.packets if p.kind == "protein")
        waste = sum(1 for p in self.packets if p.kind == "waste")
        mrna = sum(1 for p in self.packets if p.kind == "mrna")
        avg_energy = sum(m.energy for m in self.mitochondria) / max(1, len(self.mitochondria))
        processed = sum(1 for v in self.vesicles if v.marked)
        activity = (
            len(self.vesicles) * 1.7 +
            len(self.packets) * 0.9 +
            attached * 0.55 +
            free * 0.3 +
            waste * 1.2 +
            avg_energy * 8 +
            len(self.energy_particles) * 0.7
        )
        return {
            "round": self.round_id,
            "vesicles": len(self.vesicles),
            "packets": len(self.packets),
            "proteins": proteins,
            "waste": waste,
            "mrna": mrna,
            "ribosomes_attached": attached,
            "ribosomes_free": free,
            "avg_mito_energy": avg_energy,
            "processed_vesicles": processed,
            "energy_particles": len(self.energy_particles),
            "activity_score": activity,
        }

    def update(self, dt):
        self.nucleus.update(dt)
        self.er.update(dt)
        self.golgi.update(dt)

        # Molecular production by ribosomes.
        for r in self.ribosomes:
            prev = int(r.translation)
            r.update(dt, self.er.rough_sites)
            if r.attached and int(r.translation) > prev and random.random() < 0.48:
                self.packets.append(Packet(self.spawn_counter, vector(r.pos), "protein"))
                self.spawn_counter += 1

        for m in self.mitochondria:
            m.update(dt)
            if random.random() < 0.0035 and m.energy > 0.50:
                self.add_energy_particle(m.pos + rand_vec(0.15))
                m.energy *= 0.995

        for l in self.lysosomes:
            l.update(dt)

        for v in list(self.vesicles):
            v.update(dt, self)

        for p in list(self.packets):
            p.update(dt)

        self.digest_waste_collisions()
        self.packet_to_vesicle_collisions()
        self.remove_delivered_vesicles()
        self.update_energy_particles(dt)

        alive_marks = []
        for mark in self.marks:
            mark.update(dt)
            if mark.expired():
                mark.hide()
            else:
                alive_marks.append(mark)
        self.marks = alive_marks

        # Natural random events.
        if random.random() < 0.0025:
            self.burst_from_nucleus(random.randint(2, 5))
        if random.random() < 0.0022:
            self.create_waste(random.randint(1, 3))
        if random.random() < 0.0016:
            self.golgi_release(random.randint(1, 4))

# -----------------------------------------------------------------------------
# AI controller
# -----------------------------------------------------------------------------

class OrganelleAIController:
    """
    Rule-based expressive AI controller.

    The AI reads:
        vesicle count, packet count, waste count, mRNA count, attached/free ribosomes,
        average mitochondrial energy, processed vesicles, energy particles, and activity score.

    The AI can:
        burst mRNA, build proteins, release vesicles, mark traffic, move lysosomes,
        attach/detach ribosomes, stir cytoplasm, organize organelles into orbits,
        create waste, reset the world, or let the ecosystem breathe.

    Placement:
        This controller is placed after the world objects and before the main loop.
        The main loop calls ai.update(dt, world) whenever AI is enabled.
    """
    MODES = [
        "careful_homeostasis",
        "constructive_build",
        "traffic_director",
        "mitochondrial_festival",
        "lysosome_cleanup",
        "playful_orbit",
        "curious_probe",
        "chaotic_spill",
        "ritual_cycle",
        "artistic_marking",
        "destructive_stress_test",
        "quiet_observe",
    ]

    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.mode = self.MODES[self.mode_index]
        self.timer = 0.0
        self.action_timer = 0.0
        self.mode_duration = 9.0
        self.intensity = 1.0
        self.override_timer = 0.0
        self.stagnation_time = 0.0
        self.complete_time = 0.0
        self.last_activity = None
        self.last_counts = None
        self.round_pause = 0.0
        self.loop_after_completion = True
        self.ai_phase = 0.0

    def cycle_mode(self, world=None):
        self.mode_index = (self.mode_index + 1) % len(self.MODES)
        self.mode = self.MODES[self.mode_index]
        self.timer = 0
        self.action_timer = 0
        if world:
            world.add_mark(vector(0, 6.1, 0), "AI mode: " + self.mode)

    def choose_mode_from_state(self, s):
        # Completion/stagnation-driven mode selection.
        if s["waste"] > 9:
            return "lysosome_cleanup"
        if s["vesicles"] < 5 and s["proteins"] > 8:
            return "traffic_director"
        if s["avg_mito_energy"] < 0.50:
            return "mitochondrial_festival"
        if s["ribosomes_attached"] < 10:
            return "constructive_build"
        if s["packets"] > 55:
            return "careful_homeostasis"
        if self.stagnation_time > 7.0:
            return random.choice(["chaotic_spill", "playful_orbit", "artistic_marking", "curious_probe"])
        return random.choice(self.MODES)

    def set_mode(self, mode, world=None):
        if mode not in self.MODES:
            return
        self.mode = mode
        self.mode_index = self.MODES.index(mode)
        self.timer = 0.0
        self.action_timer = 0.0
        self.mode_duration = random.uniform(6.0, 14.0)
        if world:
            world.add_mark(vector(0, 6.1, 0), "AI: " + mode)

    def detect_stagnation_and_completion(self, dt, s):
        activity = s["activity_score"]
        counts = (s["vesicles"], s["packets"], s["waste"], s["ribosomes_attached"], s["energy_particles"])

        if self.last_activity is None:
            self.last_activity = activity
            self.last_counts = counts
            return False, False

        activity_delta = abs(activity - self.last_activity)
        count_delta = sum(abs(a - b) for a, b in zip(counts, self.last_counts))

        if activity_delta < 0.9 and count_delta <= 1:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0, self.stagnation_time - dt * 0.7)

        mostly_empty = s["vesicles"] < 3 and s["packets"] < 6 and s["energy_particles"] < 2
        too_stable = self.stagnation_time > 12.0
        too_crowded = s["packets"] > 90 or s["vesicles"] > 52

        complete = mostly_empty or too_stable or too_crowded
        if complete:
            self.complete_time += dt
        else:
            self.complete_time = 0

        self.last_activity = activity
        self.last_counts = counts
        return self.stagnation_time > 6.0, self.complete_time > 3.0

    def take_action(self, world, s):
        mode = self.mode
        strength = self.intensity

        if mode == "careful_homeostasis":
            if s["waste"] > 4:
                world.send_lysosomes_to_waste()
            elif s["vesicles"] < 10:
                world.golgi_release(max(2, int(3 * strength)))
            elif s["avg_mito_energy"] < 0.7:
                world.mark_random_vesicles(3)
                for v in world.vesicles[:5]:
                    v.target_name = "mitochondrion"
            else:
                world.protein_burst_from_er(max(2, int(4 * strength)))

        elif mode == "constructive_build":
            world.attach_more_ribosomes()
            if random.random() < 0.70:
                world.burst_from_nucleus(max(3, int(5 * strength)))
            if random.random() < 0.50:
                world.protein_burst_from_er(max(4, int(7 * strength)))

        elif mode == "traffic_director":
            world.mark_random_vesicles(max(4, int(7 * strength)))
            if s["vesicles"] < 16:
                world.golgi_release(max(4, int(7 * strength)))
            for i, v in enumerate(world.vesicles):
                if i % 4 == 0:
                    v.target_name = "golgi"
                elif i % 4 == 1:
                    v.target_name = "membrane"
                elif i % 4 == 2:
                    v.target_name = "mitochondrion"
                else:
                    v.target_name = "lysosome"

        elif mode == "mitochondrial_festival":
            for v in world.vesicles:
                if random.random() < 0.55:
                    v.target_name = "mitochondrion"
                    v.cargo = random.choice(["energy", "protein"])
                    v.marked = True
            world.golgi_release(max(3, int(5 * strength)))
            for m in world.mitochondria:
                m.energy = clamp(m.energy + 0.08, 0, 1.4)
                world.add_energy_particle(m.pos)

        elif mode == "lysosome_cleanup":
            if s["waste"] < 5:
                world.create_waste(max(3, int(5 * strength)))
            world.send_lysosomes_to_waste()
            for v in world.vesicles:
                if random.random() < 0.45:
                    v.target_name = "lysosome"
                    v.cargo = "waste"
                    v.marked = True

        elif mode == "playful_orbit":
            world.organize_orbit()
            world.stir_cytoplasm(0.025 * strength)
            for i, v in enumerate(world.vesicles):
                angle = self.ai_phase + i * 0.55
                v.target = vector(4.8 * cos(angle), 1.2 * sin(angle * 2), 4.8 * sin(angle))

        elif mode == "curious_probe":
            world.burst_from_nucleus(max(1, int(3 * strength)))
            world.mark_random_vesicles(max(2, int(4 * strength)))
            if random.random() < 0.4:
                world.detach_some_ribosomes()
            else:
                world.attach_more_ribosomes()

        elif mode == "chaotic_spill":
            world.stir_cytoplasm(0.095 * strength)
            if random.random() < 0.55:
                world.create_waste(max(3, int(7 * strength)))
            if random.random() < 0.55:
                world.golgi_release(max(2, int(6 * strength)))
            if random.random() < 0.35:
                world.detach_some_ribosomes()

        elif mode == "ritual_cycle":
            step = int((self.timer % 8.0) // 2.0)
            if step == 0:
                world.burst_from_nucleus(max(3, int(4 * strength)))
            elif step == 1:
                world.attach_more_ribosomes()
                world.protein_burst_from_er(max(3, int(5 * strength)))
            elif step == 2:
                world.golgi_release(max(4, int(6 * strength)))
            else:
                world.send_lysosomes_to_waste()
                world.organize_orbit()

        elif mode == "artistic_marking":
            world.mark_random_vesicles(max(4, int(8 * strength)))
            center = vector(0, 0, 0)
            for i in range(max(3, int(5 * strength))):
                angle = self.ai_phase + i * 2 * pi / 5
                p = vector(3.5 * cos(angle), 1.0 * sin(angle * 3), 3.5 * sin(angle))
                world.add_mark(p, random.choice(["trace", "sort", "signal", "fold", "ship"]))
            world.stir_cytoplasm(0.018 * strength)

        elif mode == "destructive_stress_test":
            world.create_waste(max(5, int(9 * strength)))
            world.detach_some_ribosomes()
            world.stir_cytoplasm(0.11 * strength)
            for v in world.vesicles:
                if random.random() < 0.30:
                    v.target_name = random.choice(["lysosome", "membrane"])
                    v.cargo = "waste"

        elif mode == "quiet_observe":
            world.release_targets()
            if random.random() < 0.25:
                world.add_mark(rand_inside(4.2), "observe")

    def update(self, dt, world):
        if not self.enabled:
            return

        self.ai_phase += dt
        self.timer += dt
        self.action_timer += dt
        if self.override_timer > 0:
            self.override_timer -= dt

        s = world.state_variables()
        stagnant, complete = self.detect_stagnation_and_completion(dt, s)

        # Reset/loop when the world is complete, halted, overcrowded, empty, or no longer changing.
        if self.loop_after_completion and complete:
            self.round_pause += dt
            if self.round_pause > 1.0:
                world.add_mark(vector(0, -6.1, 0), "AI loop reset")
                world.reset()
                self.round_pause = 0
                self.stagnation_time = 0
                self.complete_time = 0
                self.set_mode(random.choice(["constructive_build", "ritual_cycle", "traffic_director"]), world)
            return
        else:
            self.round_pause = 0

        # Switch modes over time or when a state condition demands it.
        if self.timer > self.mode_duration or stagnant:
            self.set_mode(self.choose_mode_from_state(s), world)

        # Take actions at irregular intervals to avoid repetitive behavior.
        interval = clamp(1.8 / max(0.3, self.intensity), 0.45, 2.4)
        jitter = 0.35 * sin(self.ai_phase * 1.7) + random.uniform(-0.10, 0.10)
        if self.action_timer > interval + jitter:
            self.take_action(world, s)
            self.action_timer = 0.0

# -----------------------------------------------------------------------------
# Controls
# -----------------------------------------------------------------------------

world = CellWorld()
ai = OrganelleAIController()
paused = False
show_help_until = 0

def print_controls():
    print(__doc__)

def keydown(evt):
    global paused, show_help_until
    key = evt.key.lower()

    if key == "a":
        ai.enabled = not ai.enabled
        world.add_mark(vector(0, 6.0, 0), "AI on" if ai.enabled else "AI off")
    elif key == "p":
        paused = not paused
        world.add_mark(vector(0, -6.0, 0), "paused" if paused else "running")
    elif key == "m":
        ai.cycle_mode(world)
    elif key == "r":
        world.reset()
        ai.stagnation_time = 0
        ai.complete_time = 0
    elif key == "o":
        ai.override_timer = 2.5
        world.burst_from_nucleus(8)
        world.protein_burst_from_er(10)
        world.golgi_release(6)
        world.add_mark(vector(0, 5.3, 0), "human override")
    elif key == "v":
        world.golgi_release(8)
    elif key == "l":
        world.send_lysosomes_to_waste()
    elif key == "c":
        for mark in world.marks:
            mark.hide()
        world.marks = []
        for v in world.vesicles:
            v.trail.clear()
        world.add_mark(vector(0, 0, 0), "marks cleared")
    elif key in ["+", "="]:
        ai.intensity = clamp(ai.intensity + 0.15, 0.25, 3.0)
        world.add_mark(vector(5.2, 5.2, 0), "AI intensity +")
    elif key in ["-", "_"]:
        ai.intensity = clamp(ai.intensity - 0.15, 0.25, 3.0)
        world.add_mark(vector(5.2, 5.2, 0), "AI intensity -")
    elif key == "h":
        print_controls()
        show_help_until = time.time() + 4

scene.bind("keydown", keydown)

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------

print_controls()

t = 0.0
frame = 0
while True:
    rate(60)
    if paused:
        status_label.text = "PAUSED | A toggle AI | P resume | R reset"
        continue

    t += DT
    frame += 1

    ai.update(DT, world)
    world.update(DT)

    if frame % 12 == 0:
        s = world.state_variables()
        status_label.text = (
            f"round {s['round']} | vesicles {s['vesicles']} | packets {s['packets']} "
            f"| waste {s['waste']} | attached ribosomes {s['ribosomes_attached']} "
            f"| mito energy {s['avg_mito_energy']:.2f} | AI {'on' if ai.enabled else 'off'}"
        )
        mode_label.text = (
            f"AI mode: {ai.mode}\n"
            f"intensity {ai.intensity:.2f} | stagnation {ai.stagnation_time:.1f}s"
        )

    # Soft breathing of the whole cell boundary.
    breath = 1.0 + 0.012 * sin(t * 0.75)
    cell_membrane.radius = CELL_RADIUS * breath
    cell_glow.radius = CELL_RADIUS * 0.985 * breath

    # Cytoplasm motes drift slowly and bounce inside the membrane.
    for i, d in enumerate(cytoplasm_dots):
        phase = t * 0.15 + i * 0.77
        d.pos += vector(0.002 * sin(phase), 0.0015 * cos(phase * 1.3), 0.002 * sin(phase * 0.7))
        if mag(d.pos) > CELL_RADIUS * 0.93:
            d.pos = safe_norm(d.pos) * CELL_RADIUS * 0.90
