"""
Hydrogen Bonding Network — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python hydrogen_bonding_network_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume simulation
    R       reset the liquid network
    M       cycle AI behavior mode
    O       human override: stir/pulse the liquid
    D       detach several hydrogen bonds
    C       clear marks and temporary particles
    + / =   increase AI intensity
    - / _   decrease AI intensity
    H       print controls

Scene:
    Water molecules drift, rotate, collide softly, attract by hydrogen bonding,
    detach, reconnect, and form a moving liquid-like network. Oxygen atoms act as
    hydrogen-bond acceptors. Hydrogens act as donors. Dashed blue links appear
    when a hydrogen on one molecule is near and oriented toward the oxygen of another.

AI:
    The AI reads the simulation state, chooses behavior modes, applies forces,
    rotates molecules, creates network patterns, breaks bonds, marks molecules,
    spills new molecules, and resets the scene when it becomes stagnant or complete.

This file is self-contained and intentionally uses VPython primitives only.
"""

from vpython import *
from math import sin, cos, pi, sqrt, atan2
import random
import time

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Hydrogen Bonding Network — Water Molecules + Expressive AI",
    width=1250,
    height=780,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 9, 15)
scene.camera.axis = vector(0, -7, -14)
scene.forward = vector(0, -0.25, -1)
scene.up = vector(0, 1, 0)
scene.range = 8.8
scene.autoscale = False

# Light visual style
scene.append_to_caption("""
Controls:
[A] AI on/off    [P] pause    [R] reset    [M] AI mode    [O] override stir
[D] detach bonds [C] clear marks    [+/-] AI intensity    [H] print controls

Hydrogen bonds are shown as pale dashed blue links.
Oxygen = red, hydrogen = white, dipole arrow = blue/cyan.
""")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOX_R = 6.2
WALL_Y = 3.4
INITIAL_MOLECULES = 28
MAX_MOLECULES = 42
DT = 0.016

O_RADIUS = 0.22
H_RADIUS = 0.105
OH_DIST = 0.50
HOH_ANGLE = 104.5 * pi / 180.0
HALF_HOH = HOH_ANGLE / 2.0

HBOND_DISTANCE = 1.08
HBOND_BREAK_DISTANCE = 1.52
HBOND_ALIGN_MIN = 0.33
MAX_BONDS_PER_MOLECULE = 4

DAMPING = 0.987
ANGULAR_DAMPING = 0.975
CENTER_PULL = 0.010
COLLISION_RADIUS = 0.72
COLLISION_K = 0.035
THERMAL_NOISE = 0.010

AI_DEFAULT_INTENSITY = 1.0

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def clamp(x, a, b):
    return max(a, min(b, x))


def mag_safe(v):
    m = mag(v)
    if m < 1e-9:
        return 1e-9
    return m


def norm_safe(v):
    m = mag(v)
    if m < 1e-9:
        return vector(1, 0, 0)
    return v / m


def random_vec(scale=1.0):
    return vector(
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
        random.uniform(-scale, scale),
    )


def random_unit():
    v = random_vec(1.0)
    while mag(v) < 0.001:
        v = random_vec(1.0)
    return norm(v)


def rotate_vec(v, axis_v, angle):
    return rotate(v, angle=angle, axis=axis_v)


def soft_color(c, factor=0.5):
    return vector(
        clamp(c.x * factor + (1 - factor), 0, 1),
        clamp(c.y * factor + (1 - factor), 0, 1),
        clamp(c.z * factor + (1 - factor), 0, 1),
    )


def clear_curve(crv):
    try:
        crv.clear()
    except Exception:
        crv.visible = False


# ---------------------------------------------------------------------------
# Static environment
# ---------------------------------------------------------------------------

boundary = box(
    pos=vector(0, 0, 0),
    size=vector(BOX_R * 2, WALL_Y * 2, BOX_R * 2),
    opacity=0.055,
    color=vector(0.62, 0.75, 0.95),
)

floor = box(
    pos=vector(0, -WALL_Y - 0.035, 0),
    size=vector(BOX_R * 2.05, 0.04, BOX_R * 2.05),
    color=vector(0.86, 0.91, 0.98),
    opacity=0.35,
)

center_marker = sphere(
    pos=vector(0, 0, 0),
    radius=0.06,
    color=vector(0.35, 0.52, 0.9),
    opacity=0.35,
)

mode_label = label(
    pos=vector(-6.4, 4.1, 0),
    text="AI: on | mode: organize",
    height=13,
    color=vector(0.12, 0.18, 0.25),
    box=False,
    opacity=0,
)

state_label = label(
    pos=vector(3.0, 4.1, 0),
    text="",
    height=12,
    color=vector(0.12, 0.18, 0.25),
    box=False,
    opacity=0,
)

caption_label = label(
    pos=vector(0, -4.15, 0),
    text="moving hydrogen-bond network",
    height=11,
    color=vector(0.20, 0.28, 0.36),
    box=False,
    opacity=0,
)

# ---------------------------------------------------------------------------
# Visual particle effects
# ---------------------------------------------------------------------------

class Spark:
    def __init__(self, pos, vel, color_v, radius=0.035, life=1.0):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.life = life
        self.age = 0.0
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=color_v,
            opacity=0.7,
            emissive=False,
        )

    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt
        self.vel *= 0.985
        self.obj.pos = self.pos
        self.obj.opacity = max(0.0, 0.7 * (1.0 - self.age / self.life))
        if self.age >= self.life:
            self.obj.visible = False
            return False
        return True


class RippleRing:
    def __init__(self, pos, axis_v, color_v, life=1.2):
        self.pos = vector(pos)
        self.life = life
        self.age = 0.0
        self.base_radius = 0.08
        self.obj = ring(
            pos=self.pos,
            axis=norm_safe(axis_v),
            radius=self.base_radius,
            thickness=0.012,
            color=color_v,
            opacity=0.45,
        )

    def update(self, dt):
        self.age += dt
        k = self.age / self.life
        self.obj.radius = self.base_radius + 1.0 * k
        self.obj.thickness = max(0.003, 0.012 * (1 - k))
        self.obj.opacity = max(0.0, 0.45 * (1 - k))
        if self.age >= self.life:
            self.obj.visible = False
            return False
        return True


sparks = []
ripples = []


def add_sparks(pos, count=8, color_v=vector(0.45, 0.70, 1.0), speed=0.7):
    for _ in range(count):
        sparks.append(Spark(pos, random_unit() * random.uniform(0.05, speed), color_v, life=random.uniform(0.45, 1.1)))


def add_ripple(pos, axis_v=vector(0, 1, 0), color_v=vector(0.45, 0.68, 1.0)):
    ripples.append(RippleRing(pos, axis_v, color_v))


# ---------------------------------------------------------------------------
# Water molecule
# ---------------------------------------------------------------------------

class WaterMolecule:
    def __init__(self, idx, pos=None):
        self.idx = idx
        self.pos = vector(pos) if pos is not None else random_vec(BOX_R * 0.72)
        self.pos.y = clamp(self.pos.y, -WALL_Y * 0.65, WALL_Y * 0.65)

        self.vel = random_vec(0.28)
        self.angle = random.uniform(0, 2 * pi)
        self.tilt = random.uniform(-0.8, 0.8)
        self.spin = random.uniform(-1.5, 1.5)
        self.tilt_spin = random.uniform(-0.8, 0.8)
        self.mark_timer = 0.0
        self.ai_tag = ""
        self.selected = False

        self.oxygen_color = vector(0.86, 0.18, 0.15)
        self.hydrogen_color = vector(1.0, 1.0, 1.0)

        self.o = sphere(pos=self.pos, radius=O_RADIUS, color=self.oxygen_color, shininess=0.65)
        self.h1 = sphere(pos=self.pos, radius=H_RADIUS, color=self.hydrogen_color, shininess=0.8)
        self.h2 = sphere(pos=self.pos, radius=H_RADIUS, color=self.hydrogen_color, shininess=0.8)

        self.oh1 = cylinder(pos=self.pos, axis=vector(0, 0, 0), radius=0.035, color=vector(0.93, 0.77, 0.77))
        self.oh2 = cylinder(pos=self.pos, axis=vector(0, 0, 0), radius=0.035, color=vector(0.93, 0.77, 0.77))

        self.dipole = arrow(
            pos=self.pos,
            axis=vector(0, 0.4, 0),
            shaftwidth=0.035,
            headwidth=0.10,
            headlength=0.15,
            color=vector(0.23, 0.52, 0.93),
            opacity=0.55,
        )

        self.mark = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=0.46,
            thickness=0.012,
            color=vector(0.25, 0.63, 1.0),
            opacity=0.0,
        )

        self.trail = curve(color=vector(0.55, 0.73, 1.0), radius=0.008)
        self.trail_timer = 0.0

        self.update_geometry()

    def local_axes(self):
        yaw_axis = vector(0, 1, 0)
        forward = rotate(vector(1, 0, 0), axis=yaw_axis, angle=self.angle)
        side = rotate(vector(0, 0, 1), axis=yaw_axis, angle=self.angle)
        up = rotate(vector(0, 1, 0), axis=side, angle=self.tilt)
        forward = norm_safe(rotate(forward, axis=side, angle=self.tilt * 0.35))
        return forward, up, side

    def hydrogen_offsets(self):
        forward, up, side = self.local_axes()
        h1_dir = norm_safe(rotate_vec(forward, up, HALF_HOH))
        h2_dir = norm_safe(rotate_vec(forward, up, -HALF_HOH))
        return h1_dir * OH_DIST, h2_dir * OH_DIST

    def donor_positions(self):
        a, b = self.hydrogen_offsets()
        return [self.pos + a, self.pos + b]

    def donor_dirs(self):
        a, b = self.hydrogen_offsets()
        return [norm_safe(a), norm_safe(b)]

    def acceptor_pos(self):
        return self.pos

    def dipole_dir(self):
        a, b = self.hydrogen_offsets()
        return norm_safe((a + b) * 0.55 - vector(0, 0.18, 0))

    def update_geometry(self):
        h1_off, h2_off = self.hydrogen_offsets()
        h1_pos = self.pos + h1_off
        h2_pos = self.pos + h2_off

        self.o.pos = self.pos
        self.h1.pos = h1_pos
        self.h2.pos = h2_pos

        self.oh1.pos = self.pos
        self.oh1.axis = h1_off
        self.oh2.pos = self.pos
        self.oh2.axis = h2_off

        dip = self.dipole_dir()
        self.dipole.pos = self.pos - dip * 0.24
        self.dipole.axis = dip * 0.52

        self.mark.pos = self.pos
        self.mark.axis = vector(0, 1, 0)
        self.mark.opacity = 0.55 if self.mark_timer > 0 else 0.0
        self.mark.radius = 0.42 + 0.05 * sin(global_time * 9 + self.idx)

        if self.mark_timer > 0:
            self.o.color = vector(0.98, 0.34, 0.25)
            self.h1.color = vector(0.92, 0.97, 1.0)
            self.h2.color = vector(0.92, 0.97, 1.0)
        else:
            self.o.color = self.oxygen_color
            self.h1.color = self.hydrogen_color
            self.h2.color = self.hydrogen_color

    def add_force(self, force):
        self.vel += force

    def add_spin(self, amount, tilt_amount=0.0):
        self.spin += amount
        self.tilt_spin += tilt_amount

    def update(self, dt):
        self.vel += -self.pos * CENTER_PULL * dt
        self.vel += random_vec(THERMAL_NOISE)

        self.pos += self.vel * dt
        self.vel *= DAMPING

        self.angle += self.spin * dt
        self.tilt += self.tilt_spin * dt
        self.spin *= ANGULAR_DAMPING
        self.tilt_spin *= ANGULAR_DAMPING
        self.tilt = clamp(self.tilt, -1.15, 1.15)

        # Soft wall bounce.
        if abs(self.pos.x) > BOX_R:
            self.pos.x = clamp(self.pos.x, -BOX_R, BOX_R)
            self.vel.x *= -0.72
            add_ripple(self.pos, vector(1, 0, 0), vector(0.70, 0.82, 1.0))
        if abs(self.pos.z) > BOX_R:
            self.pos.z = clamp(self.pos.z, -BOX_R, BOX_R)
            self.vel.z *= -0.72
            add_ripple(self.pos, vector(0, 0, 1), vector(0.70, 0.82, 1.0))
        if abs(self.pos.y) > WALL_Y:
            self.pos.y = clamp(self.pos.y, -WALL_Y, WALL_Y)
            self.vel.y *= -0.72
            add_ripple(self.pos, vector(0, 1, 0), vector(0.70, 0.82, 1.0))

        if self.mark_timer > 0:
            self.mark_timer -= dt

        self.trail_timer += dt
        if self.trail_timer > 0.09:
            self.trail_timer = 0.0
            try:
                self.trail.append(pos=self.pos)
                if self.trail.npoints > 24:
                    self.trail.pop(0)
            except Exception:
                pass

        self.update_geometry()

    def hide(self):
        for obj in [self.o, self.h1, self.h2, self.oh1, self.oh2, self.dipole, self.mark, self.trail]:
            obj.visible = False


# ---------------------------------------------------------------------------
# Hydrogen bond visual
# ---------------------------------------------------------------------------

class HydrogenBond:
    def __init__(self, donor_idx, donor_slot, acceptor_idx):
        self.donor_idx = donor_idx
        self.donor_slot = donor_slot
        self.acceptor_idx = acceptor_idx
        self.age = 0.0
        self.strength = 0.0
        self.line = curve(color=vector(0.25, 0.62, 1.0), radius=0.014)
        self.dots = []
        for _ in range(5):
            self.dots.append(sphere(pos=vector(0, 0, 0), radius=0.026, color=vector(0.35, 0.72, 1.0), opacity=0.5))

    def key(self):
        return (self.donor_idx, self.donor_slot, self.acceptor_idx)

    def update_visual(self, molecules, dt):
        self.age += dt
        donor = molecules[self.donor_idx]
        acceptor = molecules[self.acceptor_idx]
        p1 = donor.donor_positions()[self.donor_slot]
        p2 = acceptor.acceptor_pos()
        d = mag_safe(p2 - p1)
        self.strength = clamp(1.0 - (d - 0.55) / (HBOND_BREAK_DISTANCE - 0.55), 0.0, 1.0)

        self.line.clear()
        segments = 9
        for i in range(segments + 1):
            k = i / segments
            wave = vector(0, 0.035 * sin(global_time * 10 + i + self.donor_idx), 0)
            self.line.append(pos=p1 * (1 - k) + p2 * k + wave)

        self.line.color = vector(0.22, 0.55 + 0.25 * self.strength, 1.0)
        self.line.radius = 0.008 + 0.011 * self.strength

        for i, dot in enumerate(self.dots):
            k = (i + 1) / (len(self.dots) + 1)
            pulse = 0.5 + 0.5 * sin(global_time * 8 + i * 1.2 + self.age)
            dot.pos = p1 * (1 - k) + p2 * k
            dot.radius = 0.016 + 0.018 * self.strength * pulse
            dot.opacity = 0.14 + 0.46 * self.strength * pulse

    def hide(self):
        self.line.visible = False
        for d in self.dots:
            d.visible = False


# ---------------------------------------------------------------------------
# Simulation data
# ---------------------------------------------------------------------------

molecules = []
bonds = {}
global_time = 0.0
paused = False

round_number = 1
last_state_signature = None


def create_molecules(n=INITIAL_MOLECULES):
    created = []
    for i in range(n):
        radius = random.uniform(1.0, BOX_R * 0.80)
        theta = random.uniform(0, 2 * pi)
        y = random.uniform(-WALL_Y * 0.55, WALL_Y * 0.55)
        pos = vector(radius * cos(theta), y, radius * sin(theta))
        created.append(WaterMolecule(i, pos))
    return created


def remove_all_visuals():
    global molecules, bonds, sparks, ripples
    for m in molecules:
        m.hide()
    for b in bonds.values():
        b.hide()
    for s in sparks:
        s.obj.visible = False
    for r in ripples:
        r.obj.visible = False
    molecules = []
    bonds = {}
    sparks = []
    ripples = []


def reset_simulation(reason="new round"):
    global molecules, bonds, round_number, last_state_signature
    remove_all_visuals()
    molecules = create_molecules(INITIAL_MOLECULES)
    bonds = {}
    last_state_signature = None
    round_number += 1
    for _ in range(24):
        add_sparks(random_vec(2.5), 1, vector(0.45, 0.70, 1.0), speed=1.1)
    caption_label.text = "reset: " + reason


def molecule_bond_count(idx):
    count = 0
    for k in bonds:
        if k[0] == idx or k[2] == idx:
            count += 1
    return count


def donor_bonded(donor_idx, donor_slot):
    for k in bonds:
        if k[0] == donor_idx and k[1] == donor_slot:
            return True
    return False


def acceptor_bond_count(acceptor_idx):
    count = 0
    for k in bonds:
        if k[2] == acceptor_idx:
            count += 1
    return count


def detach_bond(key, spark=True):
    if key in bonds:
        b = bonds[key]
        if spark:
            donor = molecules[b.donor_idx]
            acceptor = molecules[b.acceptor_idx]
            p = (donor.pos + acceptor.pos) * 0.5
            add_sparks(p, 5, vector(0.35, 0.65, 1.0), speed=0.45)
        b.hide()
        del bonds[key]


def detach_random_bonds(count=5):
    keys = list(bonds.keys())
    random.shuffle(keys)
    for key in keys[:count]:
        detach_bond(key, True)


def clear_marks_and_particles():
    global sparks, ripples
    for m in molecules:
        m.mark_timer = 0
        clear_curve(m.trail)
    for s in sparks:
        s.obj.visible = False
    for r in ripples:
        r.obj.visible = False
    sparks = []
    ripples = []


# ---------------------------------------------------------------------------
# Physics and hydrogen-bond network rules
# ---------------------------------------------------------------------------

def update_collisions():
    for i in range(len(molecules)):
        a = molecules[i]
        for j in range(i + 1, len(molecules)):
            b = molecules[j]
            delta = b.pos - a.pos
            d = mag_safe(delta)
            if d < COLLISION_RADIUS:
                n = delta / d
                overlap = COLLISION_RADIUS - d
                force = n * overlap * COLLISION_K
                a.add_force(-force)
                b.add_force(force)
                a.add_spin(random.uniform(-0.035, 0.035), random.uniform(-0.02, 0.02))
                b.add_spin(random.uniform(-0.035, 0.035), random.uniform(-0.02, 0.02))


def try_form_bonds():
    candidate_events = []
    for i, donor in enumerate(molecules):
        if molecule_bond_count(i) >= MAX_BONDS_PER_MOLECULE:
            continue

        donor_positions = donor.donor_positions()
        donor_dirs = donor.donor_dirs()

        for slot in [0, 1]:
            if donor_bonded(i, slot):
                continue

            hp = donor_positions[slot]
            hdir = donor_dirs[slot]

            best = None
            best_score = 0.0

            for j, acceptor in enumerate(molecules):
                if i == j:
                    continue
                if acceptor_bond_count(j) >= 2:
                    continue
                if molecule_bond_count(j) >= MAX_BONDS_PER_MOLECULE:
                    continue

                target = acceptor.acceptor_pos()
                vec_to_o = target - hp
                d = mag_safe(vec_to_o)
                if d > HBOND_DISTANCE:
                    continue

                align = dot(hdir, norm_safe(vec_to_o))
                dipole_complement = 0.5 + 0.5 * dot(donor.dipole_dir(), -acceptor.dipole_dir())
                score = (1.0 - d / HBOND_DISTANCE) * 0.75 + align * 0.35 + dipole_complement * 0.18

                if align > HBOND_ALIGN_MIN and score > best_score:
                    best_score = score
                    best = j

            if best is not None and random.random() < clamp(best_score * 0.45, 0.05, 0.85):
                key = (i, slot, best)
                if key not in bonds:
                    bonds[key] = HydrogenBond(i, slot, best)
                    candidate_events.append((i, best))

    for i, j in candidate_events[:5]:
        add_sparks((molecules[i].pos + molecules[j].pos) * 0.5, 4, vector(0.45, 0.72, 1.0), speed=0.28)


def update_bonds(dt):
    keys_to_detach = []

    for key, hb in list(bonds.items()):
        donor = molecules[hb.donor_idx]
        acceptor = molecules[hb.acceptor_idx]
        hp = donor.donor_positions()[hb.donor_slot]
        hdir = donor.donor_dirs()[hb.donor_slot]
        target = acceptor.acceptor_pos()

        delta = target - hp
        d = mag_safe(delta)
        align = dot(hdir, norm_safe(delta))

        if d > HBOND_BREAK_DISTANCE or align < -0.18:
            keys_to_detach.append(key)
            continue

        # Attraction through hydrogen bond.
        n = norm_safe(delta)
        ideal = 0.78
        stretch = d - ideal
        force = n * clamp(stretch * 0.020, -0.025, 0.035)
        donor.add_force(force)
        acceptor.add_force(-force * 0.82)

        # Mild rotational alignment: donor hydrogen points to acceptor oxygen.
        donor.add_spin(0.008 * align, 0.003 * random.uniform(-1, 1))
        acceptor.add_spin(-0.005 * align, 0.003 * random.uniform(-1, 1))

        # Occasional thermal detach.
        if random.random() < 0.0006 + 0.0016 * mag(donor.vel - acceptor.vel):
            keys_to_detach.append(key)
            continue

        hb.update_visual(molecules, dt)

    for key in keys_to_detach:
        detach_bond(key, True)

    if random.random() < 0.42:
        try_form_bonds()


def update_molecules(dt):
    for m in molecules:
        m.update(dt)


def update_effects(dt):
    global sparks, ripples
    sparks = [s for s in sparks if s.update(dt)]
    ripples = [r for r in ripples if r.update(dt)]


def update_network_physics(dt):
    update_collisions()
    update_bonds(dt)
    update_molecules(dt)
    update_effects(dt)


# ---------------------------------------------------------------------------
# AI state reader
# ---------------------------------------------------------------------------

class SimulationState:
    def __init__(self):
        self.n_molecules = len(molecules)
        self.n_bonds = len(bonds)
        self.avg_speed = 0.0
        self.avg_distance_from_center = 0.0
        self.network_density = 0.0
        self.free_donors = 0
        self.is_stable = False
        self.is_sparse = False
        self.is_crowded = False
        self.signature = 0.0

    def read(self):
        self.n_molecules = len(molecules)
        self.n_bonds = len(bonds)

        if self.n_molecules:
            self.avg_speed = sum(mag(m.vel) for m in molecules) / self.n_molecules
            self.avg_distance_from_center = sum(mag(m.pos) for m in molecules) / self.n_molecules
        else:
            self.avg_speed = 0
            self.avg_distance_from_center = 0

        possible = max(1, self.n_molecules * 2)
        self.network_density = self.n_bonds / possible

        free = 0
        for i in range(len(molecules)):
            for slot in [0, 1]:
                if not donor_bonded(i, slot):
                    free += 1
        self.free_donors = free

        self.is_stable = self.avg_speed < 0.075 and self.n_bonds > self.n_molecules * 0.65
        self.is_sparse = self.n_bonds < max(3, self.n_molecules * 0.22)
        self.is_crowded = self.avg_distance_from_center < 2.0

        # Signature used by stagnation detector.
        self.signature = (
            self.n_bonds * 3.7
            + self.avg_speed * 80
            + self.avg_distance_from_center * 8
            + self.free_donors * 0.21
        )
        return self


sim_state = SimulationState()


# ---------------------------------------------------------------------------
# Expressive AI controller
# ---------------------------------------------------------------------------

class HydrogenBondAI:
    def __init__(self):
        self.enabled = True
        self.mode = "organize"
        self.modes = [
            "organize",
            "stir",
            "careful",
            "playful",
            "chaotic",
            "constructive",
            "destructive",
            "orbit",
            "artistic",
            "ritual",
            "spill",
        ]

        self.intensity = AI_DEFAULT_INTENSITY
        self.mode_timer = 0.0
        self.mode_duration = 7.0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.last_signature = None
        self.loop_delay = 0.0
        self.override_timer = 0.0

        self.target_center = vector(0, 0, 0)
        self.last_switch_reason = "start"

    def set_mode(self, mode, reason="manual"):
        if mode not in self.modes:
            return
        self.mode = mode
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(5.5, 11.5)
        self.last_switch_reason = reason
        add_ripple(vector(0, 0, 0), vector(0, 1, 0), vector(0.35, 0.62, 1.0))

    def cycle_mode(self):
        idx = self.modes.index(self.mode)
        self.set_mode(self.modes[(idx + 1) % len(self.modes)], "manual cycle")

    def read_state(self):
        return sim_state.read()

    def choose_mode(self, state, dt):
        self.mode_timer += dt

        # Stagnation detector.
        if self.last_signature is None:
            self.last_signature = state.signature

        if abs(state.signature - self.last_signature) < 0.055:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 1.5)

        self.last_signature = state.signature

        # Completion detector: dense network plus low motion.
        if state.is_stable or state.n_bonds > state.n_molecules * 1.25:
            self.completion_timer += dt
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 2.0)

        # Loop/reset if too still or over-complete.
        if self.completion_timer > 8.0:
            reset_simulation("network completed and settled")
            self.completion_timer = 0.0
            self.stagnation_timer = 0.0
            self.set_mode("spill", "new round")
            return

        if self.stagnation_timer > 9.5:
            self.set_mode(random.choice(["stir", "chaotic", "destructive", "spill"]), "stagnation")
            self.stagnation_timer = 0.0
            return

        # State-reactive mode switching.
        if self.mode_timer > self.mode_duration:
            if state.is_sparse:
                options = ["organize", "constructive", "careful", "spill"]
            elif state.is_crowded:
                options = ["stir", "orbit", "artistic", "destructive"]
            elif state.avg_speed > 0.55:
                options = ["careful", "organize", "ritual"]
            elif state.network_density > 0.72:
                options = ["artistic", "ritual", "destructive", "orbit"]
            else:
                options = self.modes[:]

            # Avoid immediate repetition.
            if self.mode in options and len(options) > 1:
                options.remove(self.mode)

            self.set_mode(random.choice(options), "timed/state switch")

    def apply(self, dt):
        if not self.enabled or paused:
            return

        state = self.read_state()
        self.choose_mode(state, dt)

        if self.override_timer > 0:
            self.override_timer -= dt
            self.action_stir(dt, strength=2.2)
            return

        if self.mode == "organize":
            self.action_organize(dt)
        elif self.mode == "stir":
            self.action_stir(dt, strength=1.0)
        elif self.mode == "careful":
            self.action_careful(dt)
        elif self.mode == "playful":
            self.action_playful(dt)
        elif self.mode == "chaotic":
            self.action_chaotic(dt)
        elif self.mode == "constructive":
            self.action_constructive(dt)
        elif self.mode == "destructive":
            self.action_destructive(dt)
        elif self.mode == "orbit":
            self.action_orbit(dt)
        elif self.mode == "artistic":
            self.action_artistic(dt)
        elif self.mode == "ritual":
            self.action_ritual(dt)
        elif self.mode == "spill":
            self.action_spill(dt)

    def nearest_pair_without_bond(self):
        best = None
        best_d = 1e9
        for i in range(len(molecules)):
            for j in range(i + 1, len(molecules)):
                if molecule_bond_count(i) >= MAX_BONDS_PER_MOLECULE or molecule_bond_count(j) >= MAX_BONDS_PER_MOLECULE:
                    continue
                d = mag(molecules[j].pos - molecules[i].pos)
                if d < best_d:
                    best_d = d
                    best = (i, j)
        return best

    def mark(self, idx, color_v=vector(0.22, 0.62, 1.0), duration=0.8):
        if 0 <= idx < len(molecules):
            molecules[idx].mark_timer = duration
            molecules[idx].mark.color = color_v

    def action_organize(self, dt):
        # Pull sparse molecules toward nearby partners and align dipoles.
        pair = self.nearest_pair_without_bond()
        if pair:
            i, j = pair
            a = molecules[i]
            b = molecules[j]
            mid = (a.pos + b.pos) * 0.5
            a.add_force((mid - a.pos) * 0.012 * self.intensity)
            b.add_force((mid - b.pos) * 0.012 * self.intensity)
            a.add_spin(0.018 * self.intensity, 0.006)
            b.add_spin(-0.018 * self.intensity, -0.006)
            self.mark(i, vector(0.28, 0.62, 1.0), 0.3)
            self.mark(j, vector(0.28, 0.62, 1.0), 0.3)

        for m in molecules:
            m.add_force(-m.pos * 0.0008 * self.intensity)

    def action_stir(self, dt, strength=1.0):
        # Swirl the fluid around the y-axis.
        for m in molecules:
            tangential = vector(-m.pos.z, 0, m.pos.x)
            if mag(tangential) > 0.001:
                m.add_force(norm(tangential) * 0.018 * strength * self.intensity)
            m.add_spin(0.06 * strength * self.intensity, 0.014 * sin(global_time + m.idx))
        if random.random() < 0.03:
            add_ripple(vector(0, 0, 0), vector(0, 1, 0), vector(0.45, 0.70, 1.0))

    def action_careful(self, dt):
        # Slow the system, preserve bonds, gently nudge unbonded donors.
        for m in molecules:
            m.vel *= 0.995
            m.spin *= 0.990
            if molecule_bond_count(m.idx) == 0:
                m.add_force(-m.pos * 0.0025 * self.intensity)
                self.mark(m.idx, vector(0.25, 0.78, 0.75), 0.25)

    def action_playful(self, dt):
        # Pick random molecules and make them hop/dip.
        if random.random() < 0.12:
            m = random.choice(molecules)
            m.add_force(vector(random.uniform(-0.04, 0.04), random.uniform(-0.015, 0.06), random.uniform(-0.04, 0.04)) * self.intensity)
            m.add_spin(random.uniform(-0.12, 0.12) * self.intensity, random.uniform(-0.08, 0.08) * self.intensity)
            self.mark(m.idx, vector(0.85, 0.55, 1.0), 0.55)
            add_sparks(m.pos, 2, vector(0.80, 0.65, 1.0), speed=0.36)

    def action_chaotic(self, dt):
        # Increase motion and break some bonds.
        for m in molecules:
            if random.random() < 0.35:
                m.add_force(random_unit() * random.uniform(0.006, 0.040) * self.intensity)
                m.add_spin(random.uniform(-0.12, 0.12) * self.intensity, random.uniform(-0.08, 0.08))
        if random.random() < 0.035:
            detach_random_bonds(random.randint(1, 3))

    def action_constructive(self, dt):
        # Find isolated molecules and bring them into the network.
        if not molecules:
            return

        center = vector(0, 0, 0)
        bonded = [m for m in molecules if molecule_bond_count(m.idx) > 0]
        if bonded:
            center = sum((m.pos for m in bonded), vector(0, 0, 0)) / len(bonded)

        isolated = [m for m in molecules if molecule_bond_count(m.idx) == 0]
        if isolated:
            for m in isolated[:6]:
                m.add_force(norm_safe(center - m.pos) * 0.020 * self.intensity)
                m.add_spin(0.035 * self.intensity, 0.012)
                self.mark(m.idx, vector(0.35, 0.88, 0.55), 0.35)
        else:
            self.action_organize(dt)

    def action_destructive(self, dt):
        # Tear open part of the network, then allow it to reform later.
        if random.random() < 0.08:
            detach_random_bonds(random.randint(2, 6))
        for m in molecules:
            if random.random() < 0.13:
                m.add_force(norm_safe(m.pos + random_vec(0.5)) * 0.025 * self.intensity)
                self.mark(m.idx, vector(1.0, 0.55, 0.35), 0.3)

    def action_orbit(self, dt):
        # Make the liquid rotate around a temporary invisible center.
        self.target_center = vector(
            1.8 * sin(global_time * 0.35),
            0.5 * sin(global_time * 0.21),
            1.8 * cos(global_time * 0.35),
        )
        center_marker.pos = self.target_center

        for m in molecules:
            rel = m.pos - self.target_center
            tangent = vector(-rel.z, 0.15 * sin(global_time + m.idx), rel.x)
            m.add_force(norm_safe(tangent) * 0.016 * self.intensity)
            m.add_force(norm_safe(self.target_center - m.pos) * 0.004 * self.intensity)

    def action_artistic(self, dt):
        # Create a wave/ribbon: marks molecules by phase and moves them in a pattern.
        for m in molecules:
            phase = atan2(m.pos.z, m.pos.x) + global_time * 0.8
            desired_y = 1.1 * sin(phase * 2.0)
            m.add_force(vector(0, (desired_y - m.pos.y) * 0.004, 0) * self.intensity)
            if random.random() < 0.04:
                m.mark_timer = 0.4
                m.mark.color = vector(0.35 + 0.25 * sin(phase), 0.70, 1.0)

    def action_ritual(self, dt):
        # Slow pulses: expand, contract, mark, repeat.
        pulse = sin(global_time * 1.15)
        for m in molecules:
            radial = norm_safe(m.pos)
            m.add_force(radial * pulse * 0.009 * self.intensity)
            m.add_spin(0.018 * sin(global_time + m.idx) * self.intensity, 0.004)
            if abs(pulse) > 0.94 and random.random() < 0.06:
                self.mark(m.idx, vector(0.45, 0.55, 1.0), 0.45)
        if abs(pulse) > 0.985 and random.random() < 0.06:
            add_ripple(vector(0, 0, 0), vector(0, 1, 0), vector(0.45, 0.62, 1.0))

    def action_spill(self, dt):
        # Add a few new water molecules from the top edge if there is room.
        if len(molecules) < MAX_MOLECULES and random.random() < 0.045:
            idx = len(molecules)
            angle = random.uniform(0, 2 * pi)
            pos = vector(BOX_R * 0.72 * cos(angle), WALL_Y * 0.9, BOX_R * 0.72 * sin(angle))
            m = WaterMolecule(idx, pos)
            m.vel = vector(random.uniform(-0.2, 0.2), random.uniform(-0.55, -0.20), random.uniform(-0.2, 0.2))
            molecules.append(m)
            add_sparks(pos, 8, vector(0.45, 0.72, 1.0), speed=0.8)
            caption_label.text = "AI spilled a new water molecule into the liquid"
        else:
            self.action_constructive(dt)

    def human_override(self):
        self.override_timer = 1.7
        for _ in range(8):
            add_ripple(random_vec(2.5), random_unit(), vector(0.45, 0.72, 1.0))
        caption_label.text = "human override: stir pulse"


ai = HydrogenBondAI()

# ---------------------------------------------------------------------------
# Keyboard controls
# ---------------------------------------------------------------------------

def print_controls():
    print("""
Hydrogen Bonding Network Controls
---------------------------------
A       toggle AI controller
P       pause/resume
R       reset liquid network
M       cycle AI behavior mode
O       human override stir/pulse
D       detach several hydrogen bonds
C       clear marks/trails/sparks
+ / =   increase AI intensity
- / _   decrease AI intensity
H       print this help

AI modes:
    organize, stir, careful, playful, chaotic, constructive,
    destructive, orbit, artistic, ritual, spill
""")


def keydown(evt):
    global paused
    k = evt.key.lower()

    if k == "a":
        ai.enabled = not ai.enabled
        caption_label.text = "AI " + ("enabled" if ai.enabled else "disabled")

    elif k == "p":
        paused = not paused
        caption_label.text = "paused" if paused else "resumed"

    elif k == "r":
        reset_simulation("manual reset")

    elif k == "m":
        ai.cycle_mode()
        caption_label.text = "AI mode: " + ai.mode

    elif k == "o":
        ai.human_override()

    elif k == "d":
        detach_random_bonds(8)
        caption_label.text = "detached several hydrogen bonds"

    elif k == "c":
        clear_marks_and_particles()
        caption_label.text = "cleared marks and temporary particles"

    elif k in ["+", "="]:
        ai.intensity = clamp(ai.intensity + 0.15, 0.2, 3.0)
        caption_label.text = "AI intensity: %.2f" % ai.intensity

    elif k in ["-", "_"]:
        ai.intensity = clamp(ai.intensity - 0.15, 0.2, 3.0)
        caption_label.text = "AI intensity: %.2f" % ai.intensity

    elif k == "h":
        print_controls()


scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Initialize and main loop
# ---------------------------------------------------------------------------

molecules = create_molecules(INITIAL_MOLECULES)
print_controls()

last_caption_update = 0.0

while True:
    rate(60)
    global_time += DT

    if not paused:
        ai.apply(DT)
        update_network_physics(DT)
    else:
        update_effects(DT)

    state = sim_state.read()

    mode_label.text = (
        "AI: %s | mode: %s | intensity: %.2f\n"
        "switch: %s"
        % ("on" if ai.enabled else "off", ai.mode, ai.intensity, ai.last_switch_reason)
    )

    state_label.text = (
        "round: %d | molecules: %d | H-bonds: %d\n"
        "density: %.2f | avg speed: %.2f | stagnant: %.1fs"
        % (round_number, state.n_molecules, state.n_bonds, state.network_density, state.avg_speed, ai.stagnation_timer)
    )

    if global_time - last_caption_update > 2.5:
        last_caption_update = global_time
        if paused:
            caption_label.text = "paused"
        elif ai.enabled:
            caption_label.text = "AI is reading molecular state and acting through: " + ai.mode
        else:
            caption_label.text = "AI disabled: liquid network moves by local hydrogen-bond rules"
