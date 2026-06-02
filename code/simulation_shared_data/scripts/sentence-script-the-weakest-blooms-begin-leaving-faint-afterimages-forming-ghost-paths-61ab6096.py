"""
Vacuum Bloom Reactor
A VPython simulation where empty space flowers into pulses of usable energy.
Small quantum blooms appear, collapse, and reseed across a pale luminous field.
Weak blooms leave faint afterimages that become ghost paths, biasing future bloom formation.

Run with:
    python vacuum_bloom_reactor.py

Controls:
    SPACE  pause / resume
    R      reset blooms
    UP     increase reactor demand
    DOWN   decrease reactor demand

New behavior:
    Weak blooms deposit fading ghost traces. Future blooms are more likely to appear
    along these afterimage paths, so the vacuum slowly remembers where fragile
    energy flowers passed before.
"""

from vpython import *
import random
import math
import time

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Vacuum Bloom Reactor — quantum blooms reseed usable energy",
    width=1200,
    height=760,
    background=vector(0.86, 0.91, 0.96),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 18, 35)
scene.camera.axis = vector(0, -14, -34)
scene.range = 22

# -----------------------------
# Parameters
# -----------------------------
FIELD_RADIUS = 16.0
MAX_BLOOMS = 42
INITIAL_BLOOMS = 18
MAX_PULSES = 85
MAX_SPORES = 160
MAX_GHOST_PATHS = 90
WEAK_BLOOM_THRESHOLD = 0.92
DEMAND_MIN = 0.25
DEMAND_MAX = 2.5

paused = False
reactor_demand = 1.0
usable_energy = 0.0
harvested_total = 0.0
cycle_count = 0

# -----------------------------
# Materials / colors
# -----------------------------
C_FIELD = vector(0.78, 0.86, 0.92)
C_FIELD_GRID = vector(0.40, 0.56, 0.68)
C_BLOOM_BIRTH = vector(0.05, 0.48, 0.95)
C_BLOOM_GROW = vector(0.00, 0.70, 0.88)
C_BLOOM_PEAK = vector(1.0, 0.62, 0.10)
C_COLLAPSE = vector(0.92, 0.18, 0.08)
C_SPORE = vector(0.55, 0.20, 0.92)
C_HARVEST = vector(0.00, 0.66, 0.38)
C_GHOST_PATH = vector(0.58, 0.68, 0.86)
C_GHOST_SEED = vector(0.36, 0.47, 0.78)

# -----------------------------
# Utility functions
# -----------------------------
def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def rand_field_pos(radius=FIELD_RADIUS):
    # More mass near the center, but still allows edge reseeding.
    angle = random.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(random.uniform(0.02, 1.0))
    y = random.uniform(-2.6, 2.6)
    return vector(r * math.cos(angle), y, r * math.sin(angle))


def ghost_biased_field_pos(radius=FIELD_RADIUS):
    """Return a new bloom position, often biased toward a living ghost path."""
    if ghost_paths and random.random() < 0.62:
        active = [g for g in ghost_paths if g.strength > 0.05]
        if active:
            total = sum(g.strength for g in active)
            pick = random.uniform(0, total)
            running = 0.0
            chosen = active[-1]
            for g in active:
                running += g.strength
                if running >= pick:
                    chosen = g
                    break
            base = chosen.sample_position()
            jitter = vector(random.uniform(-1.4, 1.4), random.uniform(-0.35, 0.35), random.uniform(-1.4, 1.4))
            pos = base + jitter
            if mag(vector(pos.x, 0, pos.z)) < radius:
                return pos
    return rand_field_pos(radius)


def color_lerp(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a * (1 - t) + b * t


def safe_unit(v):
    magv = mag(v)
    if magv < 1e-6:
        return vector(1, 0, 0)
    return v / magv

# -----------------------------
# Field: light vacuum bed with soft grid
# -----------------------------
field_disk = cylinder(
    pos=vector(0, -3.3, 0),
    axis=vector(0, 0.04, 0),
    radius=FIELD_RADIUS + 1.5,
    color=C_FIELD,
    opacity=0.42,
)

outer_ring = ring(
    pos=vector(0, -3.25, 0),
    axis=vector(0, 1, 0),
    radius=FIELD_RADIUS + 1.5,
    thickness=0.045,
    color=vector(0.25, 0.42, 0.55),
    opacity=0.50,
)

inner_rings = []
for rr in [4, 8, 12, 16]:
    inner_rings.append(
        ring(
            pos=vector(0, -3.22, 0),
            axis=vector(0, 1, 0),
            radius=rr,
            thickness=0.018,
            color=C_FIELD_GRID,
            opacity=0.34,
        )
    )

radial_lines = []
for i in range(18):
    ang = 2 * math.pi * i / 18
    end = vector((FIELD_RADIUS + 1.0) * math.cos(ang), -3.18, (FIELD_RADIUS + 1.0) * math.sin(ang))
    radial_lines.append(
        curve(
            pos=[vector(0, -3.18, 0), end],
            color=C_FIELD_GRID,
            radius=0.01,
            opacity=0.30,
        )
    )

# Central reactor collector
collector_core = sphere(pos=vector(0, 0, 0), radius=0.72, color=C_HARVEST, emissive=True, opacity=0.85)
collector_shell = sphere(pos=vector(0, 0, 0), radius=1.1, color=C_HARVEST, opacity=0.11)
collector_ring_a = ring(pos=vector(0, 0, 0), axis=vector(0, 1, 0), radius=2.1, thickness=0.035, color=C_HARVEST, opacity=0.6)
collector_ring_b = ring(pos=vector(0, 0, 0), axis=vector(1, 0, 0), radius=1.55, thickness=0.025, color=vector(0.04, 0.48, 0.85), opacity=0.5)
collector_ring_c = ring(pos=vector(0, 0, 0), axis=vector(0, 0, 1), radius=1.75, thickness=0.025, color=vector(0.48, 0.28, 0.82), opacity=0.45)

energy_bar_back = box(pos=vector(-18, 9, 0), size=vector(0.35, 8.5, 0.35), color=vector(0.70, 0.75, 0.80), opacity=0.45)
energy_bar = box(pos=vector(-18, 5.0, 0), size=vector(0.5, 0.25, 0.5), color=C_HARVEST, emissive=True)
demand_bar_back = box(pos=vector(-17.1, 9, 0), size=vector(0.25, 8.5, 0.25), color=vector(0.70, 0.75, 0.80), opacity=0.45)
demand_bar = box(pos=vector(-17.1, 5.0, 0), size=vector(0.38, 0.25, 0.38), color=vector(0.95, 0.40, 0.08), emissive=True)

status = label(
    pos=vector(0, 12.4, 0),
    text="",
    height=16,
    box=False,
    color=vector(0.12, 0.24, 0.34),
    opacity=0,
)
legend = label(
    pos=vector(0, -11.5, 0),
    text="SPACE pause/resume   R reset   UP/DOWN demand",
    height=12,
    box=False,
    color=vector(0.20, 0.35, 0.48),
    opacity=0,
)

# -----------------------------
# Simulation objects
# -----------------------------
class GhostPath:
    def __init__(self, points, strength=1.0):
        self.points = [vector(pt) for pt in points]
        self.age = 0.0
        self.life = random.uniform(12.0, 20.0)
        self.strength = clamp(strength, 0.15, 1.0)
        self.initial_strength = self.strength
        self.line = curve(pos=self.points, radius=0.014 + 0.012 * self.strength, color=C_GHOST_PATH, opacity=0.22 * self.strength)
        self.nodes = []
        for pt in self.points[::max(1, len(self.points)//4)]:
            self.nodes.append(sphere(pos=pt, radius=0.055 + 0.035 * self.strength, color=C_GHOST_SEED, opacity=0.18 * self.strength, emissive=True))

    def sample_position(self):
        if not self.points:
            return rand_field_pos()
        idx = random.randrange(len(self.points))
        return vector(self.points[idx])

    def update(self, dt):
        self.age += dt
        fade = clamp(1.0 - self.age / self.life, 0.0, 1.0)
        self.strength = self.initial_strength * fade
        self.line.opacity = 0.22 * self.strength
        self.line.radius = max(0.004, 0.014 * (0.4 + self.strength))
        for n in self.nodes:
            n.opacity = 0.18 * self.strength
            n.radius = max(0.018, (0.055 + 0.035 * self.initial_strength) * (0.45 + 0.55 * fade))
        return fade <= 0.0

    def remove(self):
        self.line.visible = False
        for n in self.nodes:
            n.visible = False


class EnergyPulse:
    def __init__(self, start_pos, energy, color=C_HARVEST):
        self.energy = energy
        self.age = 0.0
        self.life = random.uniform(1.1, 1.9)
        self.start = vector(start_pos)
        self.end = vector(0, 0, 0)
        self.body = sphere(pos=start_pos, radius=0.10 + 0.025 * energy, color=color, emissive=True, opacity=0.9)
        self.tail = curve(pos=[start_pos, start_pos], radius=0.018, color=color, opacity=0.55)

    def update(self, dt):
        self.age += dt
        t = clamp(self.age / self.life, 0.0, 1.0)
        eased = 1 - (1 - t) ** 2
        swirl = vector(math.sin(self.age * 8.0), math.cos(self.age * 5.0), math.sin(self.age * 6.0 + 1.2)) * (1.2 * (1 - t))
        self.body.pos = self.start * (1 - eased) + self.end * eased + swirl
        self.body.radius = max(0.035, (0.12 + 0.025 * self.energy) * (1 - 0.55 * t))
        self.body.opacity = max(0.0, 0.9 * (1 - 0.2 * t))
        self.tail.modify(0, pos=self.start)
        self.tail.modify(1, pos=self.body.pos)
        self.tail.opacity = max(0.0, 0.55 * (1 - t))
        return t >= 1.0

    def remove(self):
        self.body.visible = False
        self.tail.visible = False


class VacuumSpore:
    def __init__(self, pos, velocity, potency=1.0):
        self.pos = vector(pos)
        self.velocity = vector(velocity)
        self.potency = potency
        self.age = 0.0
        self.life = random.uniform(2.0, 4.8)
        self.body = sphere(pos=self.pos, radius=0.055 + 0.035 * potency, color=C_SPORE, emissive=True, opacity=0.78)

    def update(self, dt):
        self.age += dt
        center_pull = safe_unit(-self.pos) * 0.10
        self.velocity += center_pull * dt
        self.velocity *= 0.995
        self.pos += self.velocity * dt
        self.body.pos = self.pos
        fade = clamp(1 - self.age / self.life, 0.0, 1.0)
        self.body.opacity = 0.78 * fade
        self.body.radius = (0.055 + 0.035 * self.potency) * (0.55 + 0.45 * fade)
        return self.age >= self.life or mag(self.pos) > FIELD_RADIUS + 4

    def remove(self):
        self.body.visible = False


class QuantumBloom:
    def __init__(self, pos=None, seed_strength=None):
        self.pos = ghost_biased_field_pos() if pos is None else vector(pos)
        self.seed_strength = random.uniform(0.7, 1.45) if seed_strength is None else seed_strength
        self.age = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.stage = "seed"
        self.life = random.uniform(4.2, 7.8) / clamp(reactor_demand, 0.6, 1.8)
        self.peak_time = self.life * random.uniform(0.48, 0.65)
        self.collapse_time = self.life * random.uniform(0.82, 0.94)
        self.energy_yield = 0.0
        self.radius = 0.08
        self.spin = random.choice([-1, 1]) * random.uniform(0.7, 1.8)
        self.petals = []
        self.lines = []
        self.weak_trace_points = []
        self.last_trace_age = -1.0

        self.core = sphere(pos=self.pos, radius=0.08, color=C_BLOOM_BIRTH, emissive=True, opacity=0.88)
        self.halo = sphere(pos=self.pos, radius=0.20, color=C_BLOOM_GROW, opacity=0.10)
        for i in range(6):
            ang = 2 * math.pi * i / 6
            p = sphere(
                pos=self.pos + vector(math.cos(ang), 0, math.sin(ang)) * 0.16,
                radius=0.035,
                color=C_BLOOM_GROW,
                emissive=True,
                opacity=0.7,
            )
            self.petals.append(p)
            self.lines.append(curve(pos=[self.pos, p.pos], radius=0.006, color=C_BLOOM_GROW, opacity=0.45))

    def update(self, dt):
        self.age += dt
        cycle = self.age / self.life
        pulse_wave = 0.5 + 0.5 * math.sin(self.phase + self.age * (7.0 + reactor_demand * 2.0))

        if self.age < self.peak_time:
            self.stage = "blooming"
            t = clamp(self.age / max(0.001, self.peak_time), 0.0, 1.0)
            self.radius = 0.15 + (1.0 + 0.65 * self.seed_strength) * math.sin(t * math.pi / 2)
            bloom_color = color_lerp(C_BLOOM_BIRTH, C_BLOOM_GROW, t)
            self.energy_yield = self.seed_strength * (0.25 + 1.9 * t) * (0.8 + 0.25 * pulse_wave)
        elif self.age < self.collapse_time:
            self.stage = "peak"
            t = clamp((self.age - self.peak_time) / max(0.001, self.collapse_time - self.peak_time), 0.0, 1.0)
            self.radius = (1.05 + 0.7 * self.seed_strength) * (1.0 + 0.15 * math.sin(t * math.pi * 4))
            bloom_color = color_lerp(C_BLOOM_GROW, C_BLOOM_PEAK, t)
            self.energy_yield = self.seed_strength * (2.0 + 1.1 * (1 - abs(0.5 - t))) * reactor_demand
        else:
            self.stage = "collapsing"
            t = clamp((self.age - self.collapse_time) / max(0.001, self.life - self.collapse_time), 0.0, 1.0)
            collapse_fraction = max(0.0, 1.0 - t)
            self.radius = max(0.06, (1.1 + 0.55 * self.seed_strength) * collapse_fraction ** 1.5)
            bloom_color = color_lerp(C_BLOOM_PEAK, C_COLLAPSE, t)
            self.energy_yield = self.seed_strength * collapse_fraction * 1.3

        # Slight vacuum drift keeps blooms from appearing static.
        drift = vector(
            math.sin(self.age * 0.9 + self.phase),
            math.sin(self.age * 1.4 + self.phase * 0.7) * 0.15,
            math.cos(self.age * 0.8 + self.phase),
        ) * 0.0035
        self.pos += drift

        # Weak blooms leave faint afterimages. These traces later bias new bloom seeding.
        if self.seed_strength <= WEAK_BLOOM_THRESHOLD and self.stage != "collapsing":
            if self.last_trace_age < 0 or self.age - self.last_trace_age > 0.22:
                self.weak_trace_points.append(vector(self.pos))
                self.last_trace_age = self.age
                if len(self.weak_trace_points) > 14:
                    self.weak_trace_points.pop(0)

        self.core.pos = self.pos
        self.core.radius = self.radius * (0.16 + 0.035 * pulse_wave)
        self.core.color = bloom_color
        self.core.opacity = 0.9

        self.halo.pos = self.pos
        self.halo.radius = self.radius * (1.0 + 0.24 * pulse_wave)
        self.halo.color = bloom_color
        self.halo.opacity = 0.08 + 0.10 * pulse_wave

        petal_count = len(self.petals)
        for i, p in enumerate(self.petals):
            ang = self.phase + self.age * self.spin + 2 * math.pi * i / petal_count
            tilt = math.sin(self.age * 2.1 + i) * 0.28
            petal_radius = self.radius * (0.72 + 0.22 * math.sin(self.age * 4.0 + i))
            offset = vector(math.cos(ang) * petal_radius, tilt, math.sin(ang) * petal_radius)
            p.pos = self.pos + offset
            p.radius = max(0.012, self.radius * 0.055 * (0.65 + pulse_wave))
            p.color = bloom_color
            p.opacity = 0.68 if self.stage != "collapsing" else 0.38
            self.lines[i].modify(0, pos=self.pos)
            self.lines[i].modify(1, pos=p.pos)
            self.lines[i].color = bloom_color
            self.lines[i].opacity = 0.35 if self.stage != "collapsing" else 0.18

        return self.age >= self.life

    def collapse_products(self):
        # Usable harvest pulse plus several spores that reseed future blooms.
        products = []
        if self.seed_strength <= WEAK_BLOOM_THRESHOLD and len(self.weak_trace_points) >= 3:
            ghost_strength = clamp((WEAK_BLOOM_THRESHOLD - self.seed_strength + 0.22) / 0.55, 0.20, 0.95)
            products.append(("ghost", list(self.weak_trace_points), ghost_strength))
        energy = max(0.4, self.seed_strength * random.uniform(1.4, 3.2) * reactor_demand)
        products.append(("pulse", self.pos, energy))
        spore_count = random.randint(3, 7)
        if reactor_demand > 1.45:
            spore_count += random.randint(1, 3)
        for _ in range(spore_count):
            direction = safe_unit(vector(random.uniform(-1, 1), random.uniform(-0.25, 0.25), random.uniform(-1, 1)))
            velocity = direction * random.uniform(1.2, 3.8)
            potency = clamp(self.seed_strength * random.uniform(0.55, 1.10), 0.35, 1.7)
            products.append(("spore", self.pos + direction * random.uniform(0.3, 0.8), velocity, potency))
        return products

    def remove(self):
        self.core.visible = False
        self.halo.visible = False
        for p in self.petals:
            p.visible = False
        for ln in self.lines:
            ln.visible = False

# -----------------------------
# Simulation state
# -----------------------------
blooms = []
pulses = []
spores = []
ghost_paths = []


def reset_simulation():
    global blooms, pulses, spores, ghost_paths, usable_energy, harvested_total, cycle_count
    for obj in blooms:
        obj.remove()
    for obj in pulses:
        obj.remove()
    for obj in spores:
        obj.remove()
    for obj in ghost_paths:
        obj.remove()
    blooms = []
    pulses = []
    spores = []
    ghost_paths = []
    usable_energy = 0.0
    harvested_total = 0.0
    cycle_count = 0
    for _ in range(INITIAL_BLOOMS):
        blooms.append(QuantumBloom())


def keydown(evt):
    global paused, reactor_demand
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ("r", "R"):
        reset_simulation()
    elif key == "up":
        reactor_demand = clamp(reactor_demand + 0.15, DEMAND_MIN, DEMAND_MAX)
    elif key == "down":
        reactor_demand = clamp(reactor_demand - 0.15, DEMAND_MIN, DEMAND_MAX)


scene.bind("keydown", keydown)
reset_simulation()

# -----------------------------
# Main loop
# -----------------------------
last = time.time()
while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last, 0.001, 0.05)
    last = now

    if paused:
        status.text = "VACUUM BLOOM REACTOR  |  PAUSED\n" + status.text.split("\n", 1)[-1] if "\n" in status.text else "PAUSED"
        continue

    cycle_count += 1

    # Reactor collector animation
    collector_ring_a.rotate(angle=0.010 * reactor_demand, axis=vector(0, 1, 0), origin=vector(0, 0, 0))
    collector_ring_b.rotate(angle=-0.014 * reactor_demand, axis=vector(1, 0, 0), origin=vector(0, 0, 0))
    collector_ring_c.rotate(angle=0.011 * reactor_demand, axis=vector(0, 0, 1), origin=vector(0, 0, 0))
    collector_core.radius = 0.68 + 0.16 * math.sin(cycle_count * 0.06) + 0.025 * min(usable_energy, 8)
    collector_shell.radius = 1.05 + 0.13 * math.sin(cycle_count * 0.04 + 1.3) + 0.025 * min(usable_energy, 8)
    collector_shell.opacity = clamp(0.08 + usable_energy * 0.012, 0.08, 0.28)

    # Demand consumes stored usable energy, forcing blooms to reseed faster.
    usable_energy = max(0.0, usable_energy - dt * reactor_demand * 0.55)

    # Update blooms
    expired_blooms = []
    instantaneous_energy = 0.0
    for b in blooms:
        done = b.update(dt)
        instantaneous_energy += b.energy_yield
        if done:
            expired_blooms.append(b)

    for b in expired_blooms:
        products = b.collapse_products()
        b.remove()
        if b in blooms:
            blooms.remove(b)
        for product in products:
            if product[0] == "ghost":
                if len(ghost_paths) < MAX_GHOST_PATHS:
                    ghost_paths.append(GhostPath(product[1], product[2]))
                else:
                    old = ghost_paths.pop(0)
                    old.remove()
                    ghost_paths.append(GhostPath(product[1], product[2]))
            elif product[0] == "pulse" and len(pulses) < MAX_PULSES:
                pulses.append(EnergyPulse(product[1], product[2]))
            elif product[0] == "spore" and len(spores) < MAX_SPORES:
                spores.append(VacuumSpore(product[1], product[2], product[3]))

    # Update ghost paths before seeding decisions; fading paths gradually lose influence.
    expired_ghost_paths = []
    for g in ghost_paths:
        if g.update(dt):
            expired_ghost_paths.append(g)
    for g in expired_ghost_paths:
        g.remove()
        if g in ghost_paths:
            ghost_paths.remove(g)

    # Update pulses and harvest energy
    expired_pulses = []
    for p in pulses:
        arrived = p.update(dt)
        if arrived:
            usable_energy += p.energy
            harvested_total += p.energy
            expired_pulses.append(p)
    for p in expired_pulses:
        p.remove()
        if p in pulses:
            pulses.remove(p)

    # Update spores; mature spores can reseed new blooms
    expired_spores = []
    for s in spores:
        done = s.update(dt)
        mature_probability = 0.008 * reactor_demand + 0.003 * max(0, MAX_BLOOMS - len(blooms))
        near_field = mag(s.pos) < FIELD_RADIUS
        if near_field and random.random() < mature_probability and len(blooms) < MAX_BLOOMS:
            blooms.append(QuantumBloom(pos=s.pos, seed_strength=s.potency))
            expired_spores.append(s)
        elif done:
            expired_spores.append(s)
    for s in expired_spores:
        s.remove()
        if s in spores:
            spores.remove(s)

    # Vacuum occasionally births spontaneous fluctuations when energy is low or demand rises.
    ghost_memory = clamp(sum(g.strength for g in ghost_paths) / 18.0, 0.0, 0.05)
    vacuum_pressure = clamp(reactor_demand * 0.015 + max(0, 3.0 - usable_energy) * 0.003 + ghost_memory, 0.004, 0.070)
    if len(blooms) < MAX_BLOOMS and random.random() < vacuum_pressure:
        # Ghost paths favor fragile blooms, making afterimage channels self-reinforcing.
        if ghost_paths and random.random() < 0.55:
            strength = random.uniform(0.55, 0.94)
        else:
            strength = random.uniform(0.55, 1.25 + reactor_demand * 0.2)
        blooms.append(QuantumBloom(seed_strength=strength))

    # Keep minimum activity alive.
    if len(blooms) < 6 and random.random() < 0.08:
        blooms.append(QuantumBloom(seed_strength=random.uniform(0.62, 1.35)))

    while len(ghost_paths) > MAX_GHOST_PATHS:
        old = ghost_paths.pop(0)
        old.remove()

    # Reduce oldest particles if caps are exceeded.
    while len(pulses) > MAX_PULSES:
        old = pulses.pop(0)
        old.remove()
    while len(spores) > MAX_SPORES:
        old = spores.pop(0)
        old.remove()

    # Field and UI updates
    outer_ring.rotate(angle=0.0015 * reactor_demand, axis=vector(0, 1, 0), origin=vector(0, -3.25, 0))
    for i, rr in enumerate(inner_rings):
        rr.opacity = 0.18 + 0.07 * math.sin(cycle_count * 0.025 + i)

    energy_fill = clamp(usable_energy / 18.0, 0.02, 1.0)
    energy_bar.size.y = 8.5 * energy_fill
    energy_bar.pos.y = 4.75 + energy_bar.size.y / 2
    energy_bar.color = color_lerp(vector(0.05, 0.42, 0.70), C_HARVEST, energy_fill)

    demand_fill = clamp((reactor_demand - DEMAND_MIN) / (DEMAND_MAX - DEMAND_MIN), 0.02, 1.0)
    demand_bar.size.y = 8.5 * demand_fill
    demand_bar.pos.y = 4.75 + demand_bar.size.y / 2
    demand_bar.color = color_lerp(vector(0.75, 0.26, 0.10), vector(1.0, 0.58, 0.05), demand_fill)

    status.text = (
        "VACUUM BLOOM REACTOR\n"
        f"Blooms: {len(blooms):02d}   Spores: {len(spores):03d}   Pulses: {len(pulses):02d}   Ghost Paths: {len(ghost_paths):02d}\n"
        f"Usable Energy: {usable_energy:05.2f}   Harvested Total: {harvested_total:07.2f}   Demand: {reactor_demand:04.2f}x"
    )
