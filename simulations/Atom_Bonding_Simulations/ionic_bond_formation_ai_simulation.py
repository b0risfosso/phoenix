"""
Ionic Bond Formation — 3D VPython Simulation with Expressive AI Controller

Run:
    pip install vpython
    python ionic_bond_formation_ai_simulation.py

Keyboard controls:
    A       toggle AI controller on/off
    P       pause/resume
    R       reset round
    M       cycle AI behavior mode
    T       force electron transfer
    L       force lattice construction
    D       detach lattice / disperse ions
    O       human override: stir ions and spill charge sparks
    C       clear temporary marks/sparks/trails
    + / =   increase AI speed
    - / _   decrease AI speed
    H       print controls

Scene concept:
    A sodium atom and chlorine atom move through space. Sodium's outer electron can
    transfer to chlorine. After transfer, sodium becomes Na+ and chlorine becomes Cl-.
    Opposite charges attract, the ion pair forms, then more ions organize into a
    NaCl crystal lattice. The AI controller can guide, stir, mark, spill sparks,
    reset, and start new rounds while keyboard controls remain available.
"""

from vpython import *
from math import sin, cos, pi, sqrt
import random
import time

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

scene = canvas(
    title="Ionic Bond Formation: Sodium + Chlorine -> NaCl Crystal Lattice",
    width=1180,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.35, -0.22, -1)
scene.range = 9.2
scene.userspin = True
scene.userzoom = True

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def random_vec(scale=1.0):
    return vector(
        random.uniform(-1, 1),
        random.uniform(-1, 1),
        random.uniform(-1, 1),
    ) * scale


def random_unit():
    v = random_vec(1)
    if mag(v) < 1e-6:
        return vector(1, 0, 0)
    return norm(v)


def soft_color(c, amount=0.35):
    return c * (1 - amount) + vector(1, 1, 1) * amount


def make_text(pos, text, height=0.22, col=vector(0.22, 0.24, 0.28), box=False):
    return label(
        pos=pos,
        text=text,
        height=height * 50,
        color=col,
        box=box,
        opacity=0.08 if box else 0,
        border=4,
        font="sans",
    )


# ---------------------------------------------------------------------------
# Global style
# ---------------------------------------------------------------------------

COLORS = {
    "sodium": vector(0.38, 0.60, 1.00),
    "chlorine": vector(0.38, 0.86, 0.46),
    "electron": vector(0.18, 0.28, 0.42),
    "electron_glow": vector(0.72, 0.82, 1.0),
    "positive": vector(0.95, 0.45, 0.24),
    "negative": vector(0.18, 0.43, 0.95),
    "bond": vector(0.55, 0.65, 0.78),
    "lattice_line": vector(0.65, 0.72, 0.82),
    "trail": vector(0.45, 0.55, 0.72),
    "spark": vector(1.0, 0.76, 0.25),
    "mark": vector(0.99, 0.88, 0.34),
    "floor": vector(0.88, 0.92, 0.96),
    "grid": vector(0.72, 0.78, 0.84),
}

# Ground plane and reference grid
floor = box(
    pos=vector(0, -3.2, 0),
    size=vector(16, 0.04, 11),
    color=COLORS["floor"],
    opacity=0.42,
)
grid_lines = []
for x in range(-8, 9, 2):
    grid_lines.append(curve(pos=[vector(x, -3.15, -5.5), vector(x, -3.15, 5.5)],
                            color=COLORS["grid"], radius=0.006, opacity=0.35))
for z in range(-5, 6, 2):
    grid_lines.append(curve(pos=[vector(-8, -3.145, z), vector(8, -3.145, z)],
                            color=COLORS["grid"], radius=0.006, opacity=0.35))

title_label = make_text(vector(0, 3.95, 0), "Ionic Bond Formation: Na transfers e⁻ to Cl → Na⁺ + Cl⁻ → NaCl lattice", 0.20)
status_label = make_text(vector(-6.6, 3.45, 0), "", 0.15, col=vector(0.12, 0.15, 0.19), box=True)
ai_label = make_text(vector(4.6, 3.45, 0), "", 0.15, col=vector(0.12, 0.15, 0.19), box=True)
help_label = make_text(
    vector(0, -3.75, 0),
    "A AI | P pause | R reset | M mode | T transfer | L lattice | D detach | O override | C clear | +/- AI speed",
    0.13,
    col=vector(0.25, 0.28, 0.34),
    box=True,
)

# ---------------------------------------------------------------------------
# Visual effect systems
# ---------------------------------------------------------------------------

class Spark:
    def __init__(self, pos, vel, col=None, radius=0.045, life=1.0, trail=False):
        self.life = life
        self.max_life = life
        self.vel = vel
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=col if col is not None else COLORS["spark"],
            emissive=True,
            opacity=0.85,
            make_trail=trail,
            retain=16,
            trail_radius=0.01,
            trail_color=COLORS["spark"],
        )

    def update(self, dt):
        self.life -= dt
        self.vel *= 0.985
        self.vel += vector(0, -0.05, 0) * dt
        self.obj.pos += self.vel * dt
        self.obj.opacity = clamp(0.9 * self.life / self.max_life, 0, 0.9)
        self.obj.radius *= 0.996
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


class PulseRing:
    def __init__(self, pos, col, radius=0.2, axis=vector(0, 1, 0), speed=1.8, life=1.1):
        self.life = life
        self.max_life = life
        self.speed = speed
        self.obj = ring(
            pos=pos,
            axis=axis,
            radius=radius,
            thickness=0.018,
            color=col,
            opacity=0.55,
        )

    def update(self, dt):
        self.life -= dt
        self.obj.radius += self.speed * dt
        self.obj.thickness = max(0.004, self.obj.thickness * 0.985)
        self.obj.opacity = clamp(0.55 * self.life / self.max_life, 0, 0.55)
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


class Mark:
    def __init__(self, pos, text, col=COLORS["mark"], life=1.8):
        self.life = life
        self.max_life = life
        self.obj = label(
            pos=pos,
            text=text,
            height=18,
            color=col,
            box=True,
            opacity=0.12,
            border=4,
            font="sans",
        )

    def update(self, dt):
        self.life -= dt
        self.obj.pos.y += 0.12 * dt
        self.obj.opacity = clamp(0.12 * self.life / self.max_life, 0, 0.12)
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


sparks = []
pulses = []
marks = []

def add_sparks(pos, count=10, col=None, power=1.0):
    for _ in range(count):
        sparks.append(Spark(pos, random_unit() * random.uniform(0.35, 1.1) * power,
                            col=col, radius=random.uniform(0.025, 0.06), life=random.uniform(0.55, 1.3),
                            trail=random.random() < 0.35))


def add_pulse(pos, col, radius=0.2, axis=vector(0, 1, 0), speed=1.8, life=1.0):
    pulses.append(PulseRing(pos, col, radius, axis, speed, life))


def add_mark(pos, text, col=COLORS["mark"], life=1.8):
    marks.append(Mark(pos, text, col, life))


def clear_effects():
    global sparks, pulses, marks
    for group in (sparks, pulses, marks):
        for obj in group:
            if hasattr(obj, "obj"):
                obj.obj.visible = False
    sparks = []
    pulses = []
    marks = []


# ---------------------------------------------------------------------------
# Atomic and ionic structures
# ---------------------------------------------------------------------------

class Electron:
    def __init__(self, owner, shell_radius, phase, name="e⁻"):
        self.owner = owner
        self.shell_radius = shell_radius
        self.phase = phase
        self.name = name
        self.angular_speed = random.uniform(1.0, 1.7)
        self.in_transfer = False
        self.transfer_t = 0.0
        self.transfer_start = vector(0, 0, 0)
        self.transfer_end = vector(0, 0, 0)
        self.detached = False
        self.obj = sphere(
            pos=owner.pos + vector(shell_radius, 0, 0),
            radius=0.10,
            color=COLORS["electron"],
            emissive=True,
            make_trail=True,
            retain=28,
            trail_radius=0.012,
            trail_color=COLORS["electron_glow"],
        )

    def update_orbit(self, dt, index=0):
        if self.in_transfer:
            self.transfer_t += dt * 0.55
            t = clamp(self.transfer_t, 0, 1)
            arc_height = sin(t * pi) * 1.35
            side = vector(0, arc_height, 0)
            self.obj.pos = lerp_vec(self.transfer_start, self.transfer_end, t) + side
            self.obj.color = lerp_vec(COLORS["electron"], COLORS["negative"], t)
            if t >= 1.0:
                self.in_transfer = False
                self.detached = False
                return "arrived"
            return "transfer"

        if self.detached:
            self.obj.pos += random_vec(0.025)
            return "detached"

        self.phase += self.angular_speed * dt
        # Different orbital planes by index for visible shell geometry.
        if index % 3 == 0:
            offset = vector(cos(self.phase), sin(self.phase), 0) * self.shell_radius
        elif index % 3 == 1:
            offset = vector(cos(self.phase), 0, sin(self.phase)) * self.shell_radius
        else:
            offset = vector(0, cos(self.phase), sin(self.phase)) * self.shell_radius
        self.obj.pos = self.owner.pos + offset
        return "orbit"

    def start_transfer(self, target_atom):
        self.in_transfer = True
        self.detached = True
        self.transfer_t = 0.0
        self.transfer_start = self.obj.pos
        self.transfer_end = target_atom.pos + vector(-0.45, 0.3, 0.2)
        self.owner = target_atom


class AtomIon:
    def __init__(self, name, symbol, pos, radius, col, shell_radii, charge=0):
        self.name = name
        self.symbol = symbol
        self.pos = pos
        self.vel = vector(0, 0, 0)
        self.radius = radius
        self.base_color = col
        self.charge = charge
        self.target_pos = pos
        self.locked = False
        self.shell_radii = shell_radii[:]
        self.electrons = []
        self.shell_objs = []
        self.force = vector(0, 0, 0)

        self.core = sphere(
            pos=pos,
            radius=radius,
            color=col,
            opacity=0.92,
            shininess=0.7,
        )
        self.glow = sphere(
            pos=pos,
            radius=radius * 1.22,
            color=soft_color(col, 0.62),
            opacity=0.15,
            emissive=True,
        )
        self.charge_ring = ring(
            pos=pos,
            axis=vector(0, 1, 0),
            radius=radius * 1.55,
            thickness=0.022,
            color=COLORS["bond"],
            opacity=0.22,
        )
        for r in shell_radii:
            self.shell_objs.append(ring(pos=pos, axis=vector(0, 1, 0), radius=r, thickness=0.006,
                                        color=vector(0.58, 0.66, 0.76), opacity=0.22))
            self.shell_objs.append(ring(pos=pos, axis=vector(1, 0, 0), radius=r, thickness=0.006,
                                        color=vector(0.58, 0.66, 0.76), opacity=0.16))

        self.label = label(
            pos=pos + vector(0, radius + 0.55, 0),
            text=symbol,
            height=22,
            color=vector(0.1, 0.12, 0.16),
            box=True,
            opacity=0.08,
            border=4,
            font="sans",
        )

    def add_electron(self, shell_radius, phase=None):
        if phase is None:
            phase = random.uniform(0, 2 * pi)
        e = Electron(self, shell_radius, phase)
        self.electrons.append(e)
        return e

    def set_charge(self, charge):
        self.charge = charge
        if charge > 0:
            self.core.color = lerp_vec(self.base_color, COLORS["positive"], 0.45)
            self.glow.color = COLORS["positive"]
            self.charge_ring.color = COLORS["positive"]
            self.label.text = f"{self.symbol}⁺"
        elif charge < 0:
            self.core.color = lerp_vec(self.base_color, COLORS["negative"], 0.33)
            self.glow.color = COLORS["negative"]
            self.charge_ring.color = COLORS["negative"]
            self.label.text = f"{self.symbol}⁻"
        else:
            self.core.color = self.base_color
            self.glow.color = soft_color(self.base_color, 0.62)
            self.charge_ring.color = COLORS["bond"]
            self.label.text = self.symbol

    def apply_force(self, f):
        if not self.locked:
            self.force += f

    def move_toward(self, target, strength=1.0):
        self.apply_force((target - self.pos) * strength)

    def update(self, dt, damping=0.94):
        if not self.locked:
            self.vel += self.force * dt
            self.vel *= damping
            self.pos += self.vel * dt
        else:
            self.vel = vector(0, 0, 0)
            self.pos = lerp_vec(self.pos, self.target_pos, clamp(dt * 3.4, 0, 1))

        self.force = vector(0, 0, 0)
        self.core.pos = self.pos
        self.glow.pos = self.pos
        self.glow.radius = self.radius * (1.23 + 0.035 * sin(time.time() * 3.1))
        self.charge_ring.pos = self.pos
        self.charge_ring.axis = vector(sin(time.time() * 0.9), 1, cos(time.time() * 0.9))
        self.charge_ring.opacity = 0.16 + 0.20 * min(abs(self.charge), 1)

        for i, s in enumerate(self.shell_objs):
            s.pos = self.pos
            if i % 2 == 0:
                s.axis = vector(0, 1, 0)
            else:
                s.axis = vector(cos(time.time() * 0.35), 0, sin(time.time() * 0.35))

        self.label.pos = self.pos + vector(0, self.radius + 0.55, 0)

        arrived = False
        for i, e in enumerate(self.electrons):
            state = e.update_orbit(dt, i)
            if state == "arrived":
                arrived = True
        return arrived

    def visible(self, val):
        self.core.visible = val
        self.glow.visible = val
        self.charge_ring.visible = val
        self.label.visible = val
        for s in self.shell_objs:
            s.visible = val
        for e in self.electrons:
            e.obj.visible = val


class LatticeIon:
    def __init__(self, symbol, charge, pos, target, col):
        self.symbol = symbol
        self.charge = charge
        self.pos = pos
        self.target = target
        self.vel = random_vec(0.4)
        self.locked = False
        self.radius = 0.34 if charge > 0 else 0.42
        self.obj = sphere(pos=pos, radius=self.radius, color=col, opacity=0.9, shininess=0.65)
        self.glow = sphere(pos=pos, radius=self.radius * 1.25, color=col, opacity=0.08, emissive=True)
        self.label = label(
            pos=pos + vector(0, self.radius + 0.18, 0),
            text=symbol,
            height=12,
            color=vector(0.15, 0.16, 0.20),
            box=False,
            opacity=0,
        )

    def update(self, dt, mode_strength=1.0):
        direction = self.target - self.pos
        dist = mag(direction)
        if dist > 0.04:
            self.vel += safe_norm(direction) * min(dist, 3) * 1.8 * mode_strength * dt
            self.vel *= 0.90
            self.pos += self.vel * dt
        else:
            self.locked = True
            self.vel *= 0.2
            self.pos = lerp_vec(self.pos, self.target, 0.18)

        self.obj.pos = self.pos
        self.glow.pos = self.pos
        self.label.pos = self.pos + vector(0, self.radius + 0.18, 0)

    def disperse(self):
        self.locked = False
        self.target = self.pos + random_unit() * random.uniform(2.5, 5.5)
        self.vel += random_unit() * random.uniform(1.5, 3.2)

    def hide(self):
        self.obj.visible = False
        self.glow.visible = False
        self.label.visible = False


# ---------------------------------------------------------------------------
# Simulation state
# ---------------------------------------------------------------------------

sodium = None
chlorine = None
transfer_electron = None
bond_curve = None
attraction_arrow = None
lattice_ions = []
lattice_bonds = []
floating_ions = []

stage = "approach"
round_number = 1
round_time = 0.0
stage_time = 0.0
completed_time = 0.0
stagnation_time = 0.0
last_motion_score = 999
electron_transfer_started = False
electron_transfer_finished = False
lattice_started = False
paused = False

AI_ENABLED = True
AI_SPEED = 1.0

# ---------------------------------------------------------------------------
# AI controller
# ---------------------------------------------------------------------------

class IonicAIController:
    def __init__(self):
        self.enabled = True
        self.mode_index = 0
        self.modes = [
            "careful_pairing",
            "curious_orbit",
            "ritual_transfer",
            "construct_lattice",
            "chaotic_stir",
            "artistic_marking",
            "destructive_detach",
            "constructive_heal",
        ]
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.mode_duration = 5.0
        self.action_cooldown = 0.0
        self.no_change_time = 0.0
        self.last_stage = None
        self.last_lattice_locked = 0
        self.auto_loop = True
        self.round_delay = 3.0
        self.completion_hold = 0.0
        self.personality = "balanced"

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.timer = 0.0
        self.mode_duration = random.uniform(3.5, 7.5)
        add_mark(vector(3.8, 2.55, 0), f"AI: {self.mode}", COLORS["negative"], 1.4)

    def choose_reactive_mode(self, state):
        if state["stage"] == "approach" and state["ion_distance"] > 4.2:
            return "careful_pairing"
        if state["stage"] == "transfer":
            return random.choice(["ritual_transfer", "curious_orbit", "artistic_marking"])
        if state["stage"] == "ion_pair" and not state["lattice_started"]:
            return "construct_lattice"
        if state["stage"] == "lattice":
            if state["lattice_locked_fraction"] > 0.92:
                return random.choice(["artistic_marking", "constructive_heal", "destructive_detach"])
            return "construct_lattice"
        if state["stage"] == "complete":
            return random.choice(["artistic_marking", "destructive_detach", "constructive_heal"])
        return random.choice(self.modes)

    def maybe_switch_mode(self, dt, state):
        self.timer += dt * AI_SPEED
        if state["stage"] != self.last_stage:
            self.mode = self.choose_reactive_mode(state)
            self.timer = 0.0
            self.mode_duration = random.uniform(4.0, 7.5)
            self.last_stage = state["stage"]
            add_mark(vector(3.8, 2.55, 0), f"AI reacts: {self.mode}", COLORS["negative"], 1.5)

        if self.timer > self.mode_duration:
            if random.random() < 0.70:
                self.mode = self.choose_reactive_mode(state)
            else:
                self.next_mode()
                return
            self.timer = 0.0
            self.mode_duration = random.uniform(4.0, 8.0)
            add_mark(vector(3.8, 2.55, 0), f"AI shifts: {self.mode}", COLORS["negative"], 1.3)

    def detect_stagnation(self, dt, state):
        locked = state["locked_lattice_count"]
        stable_stage = state["stage"] in ("complete", "lattice")
        low_motion = state["motion_score"] < 0.035

        if locked == self.last_lattice_locked and low_motion:
            self.no_change_time += dt
        else:
            self.no_change_time = max(0, self.no_change_time - dt * 0.7)

        self.last_lattice_locked = locked

        if state["complete"]:
            self.completion_hold += dt
        else:
            self.completion_hold = 0.0

        return (stable_stage and self.no_change_time > 6.0) or self.completion_hold > self.round_delay

    def update(self, dt, state):
        if not self.enabled:
            return

        self.maybe_switch_mode(dt, state)
        self.action_cooldown -= dt * AI_SPEED

        if self.detect_stagnation(dt, state):
            if self.auto_loop:
                reset_round(reason="AI loop reset")
                return

        if self.mode == "careful_pairing":
            self.act_careful_pairing(dt, state)
        elif self.mode == "curious_orbit":
            self.act_curious_orbit(dt, state)
        elif self.mode == "ritual_transfer":
            self.act_ritual_transfer(dt, state)
        elif self.mode == "construct_lattice":
            self.act_construct_lattice(dt, state)
        elif self.mode == "chaotic_stir":
            self.act_chaotic_stir(dt, state)
        elif self.mode == "artistic_marking":
            self.act_artistic_marking(dt, state)
        elif self.mode == "destructive_detach":
            self.act_destructive_detach(dt, state)
        elif self.mode == "constructive_heal":
            self.act_constructive_heal(dt, state)

    def act_careful_pairing(self, dt, state):
        if sodium and chlorine and state["stage"] == "approach":
            sodium.move_toward(vector(-1.0, 0.0, 0), 0.75 * AI_SPEED)
            chlorine.move_toward(vector(1.0, 0.0, 0), 0.75 * AI_SPEED)
            if state["ion_distance"] < 2.8 and self.action_cooldown <= 0:
                add_pulse((sodium.pos + chlorine.pos) / 2, COLORS["bond"], 0.15, axis=vector(0, 1, 0), speed=1.1)
                self.action_cooldown = 1.3

    def act_curious_orbit(self, dt, state):
        if sodium and chlorine and state["stage"] in ("approach", "transfer", "ion_pair"):
            center = (sodium.pos + chlorine.pos) / 2
            t = time.time() * 0.9
            sodium.move_toward(center + vector(cos(t), 0.28 * sin(t * 2), sin(t)) * 1.3, 0.65 * AI_SPEED)
            chlorine.move_toward(center - vector(cos(t), 0.28 * sin(t * 2), sin(t)) * 1.3, 0.65 * AI_SPEED)
            if self.action_cooldown <= 0:
                add_sparks(center, 4, col=COLORS["electron_glow"], power=0.45)
                self.action_cooldown = 0.8

    def act_ritual_transfer(self, dt, state):
        if state["stage"] == "approach" and state["ion_distance"] < 3.2 and self.action_cooldown <= 0:
            force_transfer()
            self.action_cooldown = 2.0
        elif state["stage"] == "transfer" and self.action_cooldown <= 0:
            center = (sodium.pos + chlorine.pos) / 2 if sodium and chlorine else vector(0, 0, 0)
            add_pulse(center, COLORS["spark"], 0.25, axis=random_unit(), speed=1.5, life=1.1)
            add_mark(center + vector(0, 0.8, 0), "electron offering", COLORS["spark"], 1.1)
            self.action_cooldown = 0.9

    def act_construct_lattice(self, dt, state):
        if state["stage"] in ("ion_pair", "complete") and not state["lattice_started"]:
            start_lattice()
        if state["stage"] == "lattice" and self.action_cooldown <= 0:
            for ion in lattice_ions:
                ion.target += random_vec(0.012)
            add_pulse(vector(0, 0, 0), COLORS["lattice_line"], 0.6, axis=vector(0, 1, 0), speed=2.0, life=0.9)
            self.action_cooldown = 1.4

    def act_chaotic_stir(self, dt, state):
        objects = []
        if sodium:
            objects.append(sodium)
        if chlorine:
            objects.append(chlorine)
        for obj in objects:
            obj.apply_force(random_vec(1.0) * 1.4 * AI_SPEED)
        for ion in lattice_ions:
            if random.random() < 0.04:
                ion.vel += random_unit() * random.uniform(0.4, 1.1) * AI_SPEED
        if self.action_cooldown <= 0:
            add_sparks(random_vec(1.7), 13, col=COLORS["spark"], power=1.15)
            self.action_cooldown = 1.1

    def act_artistic_marking(self, dt, state):
        if self.action_cooldown <= 0:
            if state["stage"] in ("lattice", "complete") and lattice_ions:
                ion = random.choice(lattice_ions)
                add_mark(ion.pos + vector(0, 0.7, 0), random.choice(["Na⁺", "Cl⁻", "attract", "order", "crystal"]), COLORS["mark"], 1.7)
                add_pulse(ion.pos, COLORS["mark"], 0.1, axis=random_unit(), speed=1.0, life=1.1)
            elif sodium and chlorine:
                center = (sodium.pos + chlorine.pos) / 2
                add_mark(center + random_vec(0.7), random.choice(["transfer", "charge", "pull", "pair"]), COLORS["mark"], 1.5)
            self.action_cooldown = random.uniform(0.8, 1.7)

    def act_destructive_detach(self, dt, state):
        if state["stage"] in ("lattice", "complete") and self.action_cooldown <= 0:
            detach_lattice(soft=True)
            self.action_cooldown = 5.0
        elif sodium and chlorine and state["stage"] == "ion_pair":
            sodium.apply_force(vector(-1, 0.25, 0) * 0.5 * AI_SPEED)
            chlorine.apply_force(vector(1, -0.15, 0) * 0.5 * AI_SPEED)

    def act_constructive_heal(self, dt, state):
        if state["stage"] == "lattice":
            for ion in lattice_ions:
                ion.vel *= 0.92
        elif state["stage"] == "complete" and self.action_cooldown <= 0:
            add_pulse(vector(0, 0, 0), COLORS["chlorine"], 0.75, axis=vector(0, 1, 0), speed=1.2, life=1.2)
            add_mark(vector(0, 2.0, 0), "stable lattice", COLORS["chlorine"], 1.8)
            self.action_cooldown = 1.7


ai = IonicAIController()

# ---------------------------------------------------------------------------
# Scene construction and reset
# ---------------------------------------------------------------------------

def destroy_scene_objects():
    global sodium, chlorine, transfer_electron, bond_curve, attraction_arrow
    global lattice_ions, lattice_bonds, floating_ions

    if sodium:
        sodium.visible(False)
    if chlorine:
        chlorine.visible(False)
    if bond_curve:
        bond_curve.visible = False
    if attraction_arrow:
        attraction_arrow.visible = False

    for ion in lattice_ions:
        ion.hide()
    for b in lattice_bonds:
        b.visible = False

    lattice_ions = []
    lattice_bonds = []
    floating_ions = []
    sodium = None
    chlorine = None
    transfer_electron = None
    bond_curve = None
    attraction_arrow = None
    clear_effects()


def make_atoms():
    global sodium, chlorine, transfer_electron, bond_curve, attraction_arrow

    sodium = AtomIon(
        name="Sodium",
        symbol="Na",
        pos=vector(-4.6, 0.0, 0.0),
        radius=0.52,
        col=COLORS["sodium"],
        shell_radii=[0.9, 1.25, 1.6],
        charge=0,
    )
    chlorine = AtomIon(
        name="Chlorine",
        symbol="Cl",
        pos=vector(4.6, 0.0, 0.0),
        radius=0.68,
        col=COLORS["chlorine"],
        shell_radii=[1.0, 1.38, 1.8],
        charge=0,
    )

    # Sodium simplified shell model: 2 inner, 8 middle, 1 valence.
    for i in range(2):
        sodium.add_electron(0.9, phase=i * pi)
    for i in range(8):
        sodium.add_electron(1.25, phase=i * 2 * pi / 8)
    transfer_electron = sodium.add_electron(1.6, phase=0.35)

    # Chlorine simplified shell model: 2 inner, 8 middle, 7 valence.
    for i in range(2):
        chlorine.add_electron(1.0, phase=i * pi)
    for i in range(8):
        chlorine.add_electron(1.38, phase=i * 2 * pi / 8)
    for i in range(7):
        chlorine.add_electron(1.8, phase=i * 2 * pi / 7 + 0.15)

    bond_curve = curve(
        pos=[sodium.pos, chlorine.pos],
        color=COLORS["bond"],
        radius=0.028,
        opacity=0.0,
    )
    attraction_arrow = arrow(
        pos=vector(0, -1.25, 0),
        axis=vector(0.01, 0, 0),
        shaftwidth=0.06,
        color=COLORS["positive"],
        opacity=0.0,
    )


def reset_round(reason="new round"):
    global stage, round_number, round_time, stage_time, completed_time, stagnation_time
    global last_motion_score, electron_transfer_started, electron_transfer_finished, lattice_started
    global AI_ENABLED

    destroy_scene_objects()
    make_atoms()

    stage = "approach"
    round_number += 1
    round_time = 0.0
    stage_time = 0.0
    completed_time = 0.0
    stagnation_time = 0.0
    last_motion_score = 999
    electron_transfer_started = False
    electron_transfer_finished = False
    lattice_started = False

    ai.no_change_time = 0.0
    ai.completion_hold = 0.0
    ai.last_stage = None
    ai.last_lattice_locked = 0

    add_mark(vector(0, 2.5, 0), reason, COLORS["negative"], 1.7)
    add_pulse(vector(0, 0, 0), COLORS["negative"], 0.25, axis=vector(0, 1, 0), speed=2.1, life=1.0)


def force_transfer():
    global stage, electron_transfer_started
    if transfer_electron and not electron_transfer_started and sodium and chlorine:
        electron_transfer_started = True
        stage = "transfer"
        transfer_electron.start_transfer(chlorine)
        sodium.electrons = [e for e in sodium.electrons if e is not transfer_electron]
        chlorine.electrons.append(transfer_electron)
        add_sparks(sodium.pos + vector(0.9, 0.2, 0), 16, col=COLORS["electron_glow"], power=0.8)
        add_mark((sodium.pos + chlorine.pos) / 2 + vector(0, 1.1, 0), "Na gives e⁻ to Cl", COLORS["spark"], 1.8)
        add_pulse(sodium.pos, COLORS["positive"], 0.35, axis=vector(0, 1, 0), speed=1.8)
        add_pulse(chlorine.pos, COLORS["negative"], 0.35, axis=vector(0, 1, 0), speed=1.8)


def finish_transfer():
    global stage, electron_transfer_finished
    if electron_transfer_finished:
        return
    electron_transfer_finished = True
    stage = "ion_pair"
    sodium.set_charge(+1)
    chlorine.set_charge(-1)
    add_sparks(chlorine.pos, 22, col=COLORS["negative"], power=0.85)
    add_sparks(sodium.pos, 14, col=COLORS["positive"], power=0.75)
    add_mark(vector(0, 1.7, 0), "Na⁺ and Cl⁻ attract", COLORS["mark"], 2.0)
    add_pulse(vector(0, 0, 0), COLORS["bond"], 0.5, axis=vector(0, 1, 0), speed=1.7, life=1.1)


def start_lattice():
    global lattice_started, stage, lattice_ions, lattice_bonds
    if lattice_started:
        return
    lattice_started = True
    stage = "lattice"

    # Hide the large atom pair after it seeds the lattice.
    sodium.visible(False)
    chlorine.visible(False)

    lattice_ions = []
    spacing = 1.05
    coords = []
    for ix in range(-2, 3):
        for iy in range(-1, 2):
            for iz in range(-2, 3):
                if abs(ix) + abs(iy) + abs(iz) <= 4:
                    coords.append((ix, iy, iz))

    for ix, iy, iz in coords:
        target = vector(ix * spacing, iy * spacing * 0.9, iz * spacing)
        charge = +1 if (ix + iy + iz) % 2 == 0 else -1
        symbol = "Na⁺" if charge > 0 else "Cl⁻"
        col = COLORS["positive"] if charge > 0 else COLORS["negative"]
        start = vector(random.uniform(-6, 6), random.uniform(-2.2, 2.7), random.uniform(-4.4, 4.4))
        lattice_ions.append(LatticeIon(symbol, charge, start, target, col))

    # Neighbor lines in the lattice.
    lattice_bonds = []
    for i, a in enumerate(lattice_ions):
        for j in range(i + 1, len(lattice_ions)):
            b = lattice_ions[j]
            if mag(a.target - b.target) < spacing * 1.08 and a.charge != b.charge:
                lattice_bonds.append(curve(pos=[a.pos, b.pos], color=COLORS["lattice_line"], radius=0.012, opacity=0.17))

    add_mark(vector(0, 2.5, 0), "crystal lattice begins", COLORS["chlorine"], 2.0)
    add_pulse(vector(0, 0, 0), COLORS["chlorine"], 0.45, axis=vector(0, 1, 0), speed=2.3)


def detach_lattice(soft=False):
    global stage
    if not lattice_ions:
        return
    for ion in lattice_ions:
        ion.disperse()
    add_sparks(vector(0, 0, 0), 28 if not soft else 14, col=COLORS["spark"], power=1.25 if not soft else 0.75)
    add_mark(vector(0, 2.35, 0), "lattice disturbed", COLORS["spark"], 1.7)
    if soft:
        for ion in lattice_ions:
            ion.target += random_vec(0.24)
    else:
        stage = "lattice"


make_atoms()

# ---------------------------------------------------------------------------
# Physics and state reading
# ---------------------------------------------------------------------------

def read_simulation_state():
    ion_distance = mag(chlorine.pos - sodium.pos) if sodium and chlorine else 0.0
    locked = sum(1 for ion in lattice_ions if ion.locked)
    total = max(1, len(lattice_ions))
    motion_score = 0.0
    if sodium and chlorine and sodium.core.visible:
        motion_score += mag(sodium.vel) + mag(chlorine.vel)
    for ion in lattice_ions:
        motion_score += mag(ion.vel)
    motion_score /= max(1, len(lattice_ions) + 2)

    complete = False
    if stage == "lattice" and lattice_ions:
        complete = locked / total > 0.92 and motion_score < 0.06

    return {
        "stage": stage,
        "round": round_number,
        "round_time": round_time,
        "stage_time": stage_time,
        "ion_distance": ion_distance,
        "sodium_charge": sodium.charge if sodium else 0,
        "chlorine_charge": chlorine.charge if chlorine else 0,
        "electron_transfer_started": electron_transfer_started,
        "electron_transfer_finished": electron_transfer_finished,
        "lattice_started": lattice_started,
        "locked_lattice_count": locked,
        "lattice_total": len(lattice_ions),
        "lattice_locked_fraction": locked / total,
        "motion_score": motion_score,
        "complete": complete,
        "ai_enabled": ai.enabled,
        "ai_mode": ai.mode,
    }


def update_pair_physics(dt):
    global stage

    if not sodium or not chlorine or not sodium.core.visible:
        return

    dist_vec = chlorine.pos - sodium.pos
    dist = mag(dist_vec)
    direction = safe_norm(dist_vec, vector(1, 0, 0))

    # Soft boundaries.
    for atom_obj in (sodium, chlorine):
        if abs(atom_obj.pos.x) > 6.4:
            atom_obj.apply_force(vector(-atom_obj.pos.x, 0, 0) * 0.7)
        if abs(atom_obj.pos.y) > 2.6:
            atom_obj.apply_force(vector(0, -atom_obj.pos.y, 0) * 0.7)
        if abs(atom_obj.pos.z) > 3.6:
            atom_obj.apply_force(vector(0, 0, -atom_obj.pos.z) * 0.7)

    if stage == "approach":
        sodium.move_toward(vector(-1.35, 0, 0), 0.38)
        chlorine.move_toward(vector(1.35, 0, 0), 0.38)

        # Mild collision bounce if they approach too close before transfer.
        if dist < 2.25:
            sodium.apply_force(-direction * 0.8)
            chlorine.apply_force(direction * 0.8)

        if dist < 2.95 and round_time > 2.2:
            force_transfer()

    elif stage == "transfer":
        # Atoms hold near each other while electron moves.
        sodium.move_toward(vector(-1.25, 0, 0), 0.55)
        chlorine.move_toward(vector(1.25, 0, 0), 0.55)

    elif stage == "ion_pair":
        # Coulomb-like attraction after transfer.
        q = sodium.charge * chlorine.charge
        if q != 0 and dist > 1.15:
            fmag = 2.2 * abs(q) / max(0.75, dist * dist)
            sodium.apply_force(direction * fmag)
            chlorine.apply_force(-direction * fmag)

        # Pair equilibrium.
        desired = 1.65
        if dist < desired:
            sodium.apply_force(-direction * (desired - dist) * 1.6)
            chlorine.apply_force(direction * (desired - dist) * 1.6)

        if stage_time > 4.0 or (dist < 1.9 and stage_time > 1.7):
            start_lattice()

    sodium_arrived = sodium.update(dt)
    chlorine_arrived = chlorine.update(dt)

    if sodium_arrived or chlorine_arrived:
        finish_transfer()

    # Visual bond/attraction line.
    bond_curve.clear()
    bond_curve.append(pos=sodium.pos)
    bond_curve.append(pos=chlorine.pos)
    if stage == "ion_pair":
        bond_curve.opacity = 0.42
        bond_curve.radius = 0.035 + 0.006 * sin(time.time() * 5)
        attraction_arrow.pos = sodium.pos + vector(0, -1.05, 0)
        attraction_arrow.axis = (chlorine.pos - sodium.pos) * 0.82
        attraction_arrow.opacity = 0.38
    elif stage == "transfer":
        bond_curve.opacity = 0.18
        attraction_arrow.opacity = 0.0
    else:
        bond_curve.opacity = 0.06
        attraction_arrow.opacity = 0.0


def update_lattice(dt):
    global stage, completed_time

    if not lattice_ions:
        return

    mode_strength = 1.0
    if ai.mode == "constructive_heal":
        mode_strength = 1.45
    elif ai.mode == "chaotic_stir":
        mode_strength = 0.65

    for ion in lattice_ions:
        ion.update(dt, mode_strength=mode_strength)

    # Update lattice bond line endpoints and visibility.
    for b in lattice_bonds:
        # Store no custom endpoint refs, so reconstruct via nearest target each frame.
        # This keeps the code simple and visible, but uses target lookup.
        b.opacity = 0.10

    # More accurate bond line update using matching target neighbors.
    idx = 0
    spacing = 1.05
    for i, a in enumerate(lattice_ions):
        for j in range(i + 1, len(lattice_ions)):
            c = lattice_ions[j]
            if mag(a.target - c.target) < spacing * 1.08 and a.charge != c.charge:
                if idx < len(lattice_bonds):
                    lattice_bonds[idx].clear()
                    lattice_bonds[idx].append(pos=a.pos)
                    lattice_bonds[idx].append(pos=c.pos)
                    lattice_bonds[idx].opacity = 0.10 + 0.20 * min(a.locked + c.locked, 2) / 2
                idx += 1

    locked = sum(1 for ion in lattice_ions if ion.locked)
    if locked == len(lattice_ions) and stage == "lattice":
        if completed_time == 0:
            add_mark(vector(0, 2.7, 0), "NaCl crystal stable", COLORS["chlorine"], 2.2)
            add_pulse(vector(0, 0, 0), COLORS["chlorine"], 0.85, axis=vector(0, 1, 0), speed=1.2, life=1.4)
            add_sparks(vector(0, 1.3, 0), 24, col=COLORS["chlorine"], power=0.9)
        stage = "complete"


def update_effects(dt):
    global sparks, pulses, marks
    sparks = [s for s in sparks if s.update(dt)]
    pulses = [p for p in pulses if p.update(dt)]
    marks = [m for m in marks if m.update(dt)]


def update_labels(state):
    charge_text = f"Na charge: {state['sodium_charge']:+d}     Cl charge: {state['chlorine_charge']:+d}"
    lattice_text = ""
    if state["lattice_total"]:
        lattice_text = f"     lattice locked: {state['locked_lattice_count']}/{state['lattice_total']}"
    status_label.text = (
        f"Round {state['round']} | stage: {state['stage']} | {charge_text}{lattice_text}\n"
        f"distance: {state['ion_distance']:.2f} | motion: {state['motion_score']:.3f}"
    )
    ai_label.text = (
        f"AI: {'ON' if ai.enabled else 'OFF'} | mode: {ai.mode} | speed: {AI_SPEED:.1f}x\n"
        f"auto-loop: {'ON' if ai.auto_loop else 'OFF'} | pause: {'YES' if paused else 'NO'}"
    )


# ---------------------------------------------------------------------------
# Human controls
# ---------------------------------------------------------------------------

def print_controls():
    print(__doc__)


def human_override():
    if sodium and chlorine and sodium.core.visible:
        sodium.vel += random_unit() * 1.4
        chlorine.vel += random_unit() * 1.4
        add_sparks((sodium.pos + chlorine.pos) / 2, 22, col=COLORS["spark"], power=1.2)
        add_mark(vector(0, 2.2, 0), "human override", COLORS["spark"], 1.4)
    elif lattice_ions:
        for ion in lattice_ions:
            if random.random() < 0.35:
                ion.vel += random_unit() * random.uniform(0.7, 1.8)
        add_sparks(vector(0, 0, 0), 24, col=COLORS["spark"], power=1.25)
        add_mark(vector(0, 2.2, 0), "human override", COLORS["spark"], 1.4)


def keydown(evt):
    global paused, AI_SPEED
    key = evt.key.lower()

    if key == "a":
        ai.enabled = not ai.enabled
        add_mark(vector(4.3, 2.6, 0), f"AI {'ON' if ai.enabled else 'OFF'}", COLORS["negative"], 1.3)
    elif key == "p":
        paused = not paused
        add_mark(vector(0, 2.45, 0), "paused" if paused else "resumed", COLORS["mark"], 1.2)
    elif key == "r":
        reset_round(reason="human reset")
    elif key == "m":
        ai.next_mode()
    elif key == "t":
        force_transfer()
    elif key == "l":
        start_lattice()
    elif key == "d":
        detach_lattice(soft=False)
    elif key == "o":
        human_override()
    elif key == "c":
        clear_effects()
    elif key in ["+", "="]:
        AI_SPEED = clamp(AI_SPEED + 0.2, 0.2, 3.0)
    elif key in ["-", "_"]:
        AI_SPEED = clamp(AI_SPEED - 0.2, 0.2, 3.0)
    elif key == "h":
        print_controls()


scene.bind("keydown", keydown)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

print_controls()

last_t = time.time()

while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last_t, 0.001, 0.045)
    last_t = now

    state = read_simulation_state()
    update_labels(state)

    if paused:
        update_effects(dt)
        continue

    round_time += dt
    stage_time += dt
    if state["stage"] != stage:
        stage_time = 0.0

    # AI reads current state and chooses actions automatically.
    state = read_simulation_state()
    ai.update(dt, state)

    # Physics and visuals.
    old_stage = stage
    update_pair_physics(dt)
    update_lattice(dt)
    if stage != old_stage:
        stage_time = 0.0

    if stage == "complete":
        completed_time += dt
    else:
        completed_time = 0.0

    update_effects(dt)
