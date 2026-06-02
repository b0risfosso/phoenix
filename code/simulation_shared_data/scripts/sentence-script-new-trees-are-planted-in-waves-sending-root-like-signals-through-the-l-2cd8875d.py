"""
Reforestation Pulse Network

A VPython simulation where new trees are planted in expanding waves. Each new grove
sends root-like signal pulses through the soil, gradually linking separated forest
islands into one living system.

Run:
    python reforestation_pulse_network.py

Controls:
    SPACE  pause / resume
    W      trigger an extra planting wave
    S      trigger an extra soil signal burst
    R      reset simulation
    F      toggle forest-link visibility
    UP     increase simulation speed
    DOWN   decrease simulation speed
    H      show / hide help
"""

from vpython import *
import math
import random
# -----------------------------------------------------------------------------
# Scene setup: light styling
# -----------------------------------------------------------------------------
scene = canvas(
    title="Reforestation Pulse Network",
    width=1200,
    height=760,
    background=vector(0.86, 0.93, 1.0),
    center=vector(0, 0.7, 0),
)
scene.camera.pos = vector(0, 35, 42)
scene.camera.axis = vector(0, -29, -39)
scene.forward = vector(0, -0.55, -0.83)
scene.up = vector(0, 1, 0)
scene.range = 24

random.seed(13)

GROUND_Y = 0
LAND_SIZE = 42
HALF = LAND_SIZE / 2

# Colors
SOIL = vector(0.70, 0.55, 0.38)
SOIL_GRID = vector(0.78, 0.66, 0.50)
WATER = vector(0.50, 0.74, 0.91)
HILL = vector(0.66, 0.78, 0.48)
TRUNK = vector(0.48, 0.29, 0.12)
SAPLING = vector(0.35, 0.75, 0.28)
TREE_GREEN = vector(0.15, 0.55, 0.22)
TREE_DARK = vector(0.07, 0.38, 0.18)
PULSE = vector(0.12, 0.72, 0.42)
PULSE_BRIGHT = vector(0.46, 0.95, 0.55)
LINK_COLOR = vector(0.20, 0.68, 0.28)
GHOST_LINK = vector(0.72, 0.84, 0.66)
DAMAGE = vector(0.80, 0.68, 0.48)

# Global state containers
all_objects = []
trees = []
pulses = []
root_links = []
islands = []
plant_waves = []
wave_count = 0
network_strength = 0.0
show_links = True
paused = False
show_help = True
sim_speed = 1.0
t = 0.0

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def add_obj(obj):
    all_objects.append(obj)
    return obj


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_vec(a, b, f):
    return a * (1 - f) + b * f


def terrain_height(x, z):
    return 0.12 * math.sin(x * 0.22) * math.cos(z * 0.18)


def ground_pos(x, z, lift=0.03):
    return vector(x, terrain_height(x, z) + lift, z)


def dist_xz(a, b):
    dx = a.x - b.x
    dz = a.z - b.z
    return math.sqrt(dx * dx + dz * dz)


def make_label(pos, text, height=14, color_value=vector(0.15, 0.23, 0.16), box=False):
    return add_obj(label(
        pos=pos,
        text=text,
        height=height,
        color=color_value,
        box=box,
        opacity=0.0,
        line=False,
    ))


def clear_scene_objects():
    global all_objects, trees, pulses, root_links, islands, plant_waves
    for obj in all_objects:
        try:
            obj.visible = False
        except Exception:
            pass
    all_objects = []
    trees = []
    pulses = []
    root_links = []
    islands = []
    plant_waves = []

# -----------------------------------------------------------------------------
# Landscape
# -----------------------------------------------------------------------------
def build_landscape():
    add_obj(box(
        pos=vector(0, -0.08, 0),
        size=vector(LAND_SIZE, 0.16, LAND_SIZE),
        color=SOIL,
    ))

    # Soft terrain grid lines, like mapped conservation zones.
    for x in range(-20, 21, 4):
        add_obj(curve(
            pos=[ground_pos(x, -HALF), ground_pos(x, HALF)],
            radius=0.018,
            color=SOIL_GRID,
            opacity=0.45,
        ))
    for z in range(-20, 21, 4):
        add_obj(curve(
            pos=[ground_pos(-HALF, z), ground_pos(HALF, z)],
            radius=0.018,
            color=SOIL_GRID,
            opacity=0.45,
        ))

    # River / coastline-like divider.
    river_points = []
    for i in range(64):
        z = -20 + i * (40 / 63)
        x = -2.4 + 1.2 * math.sin(z * 0.28) + 0.5 * math.sin(z * 0.73)
        river_points.append(vector(x, 0.035, z))
    add_obj(curve(pos=river_points, radius=0.19, color=WATER, opacity=0.65))
    add_obj(label(
        pos=vector(-14.8, 0.6, 18.5),
        text="forest islands reconnect as waves of new planting spread",
        height=14,
        color=vector(0.16, 0.23, 0.17),
        box=False,
        opacity=0,
    ))

    # Damaged open patches that gradually fill in.
    for x, z, sx, sz in [(-9, -8, 6, 4), (10, -4, 5, 5), (7, 11, 7, 4), (-13, 9, 5, 5)]:
        add_obj(ellipsoid(
            pos=vector(x, 0.018, z),
            length=sx,
            height=0.03,
            width=sz,
            color=DAMAGE,
            opacity=0.55,
        ))

# -----------------------------------------------------------------------------
# Tree, island, pulse, and link classes
# -----------------------------------------------------------------------------
class Tree:
    def __init__(self, x, z, age=1.0, island_id=None, planted=False):
        self.pos = ground_pos(x, z, 0.10)
        self.age = age
        self.target_age = 1.0 if age >= 1 else random.uniform(0.72, 1.18)
        self.island_id = island_id
        self.planted = planted
        self.signal_phase = random.uniform(0, math.tau)
        self.height = 0.55 + 1.15 * self.age
        self.trunk = add_obj(cylinder(
            pos=self.pos,
            axis=vector(0, self.height * 0.62, 0),
            radius=0.055 + 0.035 * self.age,
            color=TRUNK,
        ))
        crown_color = lerp_vec(SAPLING, TREE_GREEN, self.age)
        self.crown = add_obj(sphere(
            pos=self.pos + vector(0, self.height * 0.82, 0),
            radius=0.32 + 0.37 * self.age,
            color=crown_color,
            opacity=0.94,
        ))
        self.glow = add_obj(sphere(
            pos=self.pos + vector(0, 0.07, 0),
            radius=0.15 + 0.12 * self.age,
            color=PULSE_BRIGHT,
            opacity=0.0,
            emissive=True,
        ))

    def update(self, dt, time_value):
        if self.age < self.target_age:
            self.age = min(self.target_age, self.age + dt * 0.10)
            self.height = 0.55 + 1.15 * self.age
            self.trunk.axis = vector(0, self.height * 0.62, 0)
            self.trunk.radius = 0.055 + 0.035 * self.age
            self.crown.pos = self.pos + vector(0, self.height * 0.82, 0)
            self.crown.radius = 0.32 + 0.37 * self.age
            self.crown.color = lerp_vec(SAPLING, TREE_GREEN, self.age)
            self.glow.radius = 0.15 + 0.12 * self.age
        pulse_alpha = 0.10 + 0.08 * math.sin(time_value * 2.0 + self.signal_phase)
        if self.planted:
            pulse_alpha += 0.05
        self.glow.opacity = clamp(pulse_alpha, 0.04, 0.26)


class ForestIsland:
    def __init__(self, center, radius, count, island_id):
        self.center = center
        self.radius = radius
        self.island_id = island_id
        self.members = []
        self.connected = set()
        self.halo = add_obj(ring(
            pos=ground_pos(center.x, center.z, 0.06),
            axis=vector(0, 1, 0),
            radius=radius,
            thickness=0.035,
            color=GHOST_LINK,
            opacity=0.28,
        ))
        self.label = make_label(
            vector(center.x, 0.55, center.z - radius - 1.1),
            f"forest island {island_id + 1}",
            height=10,
            color_value=vector(0.14, 0.32, 0.16),
        )
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            r = radius * math.sqrt(random.uniform(0.05, 0.95))
            x = center.x + math.cos(ang) * r
            z = center.z + math.sin(ang) * r
            self.members.append(Tree(x, z, age=random.uniform(0.7, 1.0), island_id=island_id))
        trees.extend(self.members)

    def update(self, time_value):
        linked_factor = min(1, len(self.connected) / 2.0)
        self.halo.color = lerp_vec(GHOST_LINK, LINK_COLOR, linked_factor)
        self.halo.opacity = 0.20 + 0.18 * linked_factor + 0.04 * math.sin(time_value * 1.3 + self.island_id)
        self.halo.radius = self.radius + 0.18 * math.sin(time_value * 0.7 + self.island_id)


class PlantingWave:
    def __init__(self, origin, target_island=None):
        global wave_count
        wave_count += 1
        self.origin = vector(origin.x, 0.09, origin.z)
        self.radius = 0.25
        self.max_radius = random.uniform(7.0, 10.5)
        self.speed = random.uniform(1.7, 2.4)
        self.timer = 0.0
        self.spawned = []
        self.target_island = target_island
        self.ring = add_obj(ring(
            pos=ground_pos(origin.x, origin.z, 0.09),
            axis=vector(0, 1, 0),
            radius=self.radius,
            thickness=0.06,
            color=PULSE_BRIGHT,
            opacity=0.72,
            emissive=True,
        ))

    def update(self, dt):
        self.timer += dt
        self.radius += self.speed * dt
        self.ring.radius = self.radius
        self.ring.opacity = clamp(0.78 * (1 - self.radius / self.max_radius), 0.0, 0.78)
        self.ring.thickness = 0.05 + 0.02 * math.sin(self.timer * 5.0)

        # Plant saplings along the moving edge.
        if self.radius < self.max_radius and random.random() < 0.55:
            for _ in range(random.randint(1, 2)):
                ang = random.uniform(0, math.tau)
                r = self.radius + random.uniform(-0.35, 0.35)
                x = self.origin.x + math.cos(ang) * r
                z = self.origin.z + math.sin(ang) * r
                if -HALF + 1 < x < HALF - 1 and -HALF + 1 < z < HALF - 1:
                    too_close = any(dist_xz(vector(x, 0, z), tree.pos) < 0.75 for tree in trees[-140:])
                    if not too_close:
                        new_tree = Tree(x, z, age=0.08, island_id=None, planted=True)
                        trees.append(new_tree)
                        self.spawned.append(new_tree)
                        if random.random() < 0.50:
                            pulses.append(RootPulse(new_tree.pos, self.origin, strength=random.uniform(0.55, 0.95)))

        if self.radius >= self.max_radius:
            self.ring.visible = False
            return False
        return True


class RootPulse:
    def __init__(self, start, end=None, strength=1.0):
        self.start = vector(start.x, 0.13, start.z)
        if end is None:
            if islands:
                target = min(islands, key=lambda isl: dist_xz(self.start, isl.center)).center
                end = vector(target.x, 0.13, target.z)
            else:
                end = self.start + vector(random.uniform(-4, 4), 0, random.uniform(-4, 4))
        self.end = vector(end.x, 0.13, end.z)
        self.strength = strength
        self.age = 0.0
        self.life = random.uniform(1.2, 2.3)
        self.wiggle = random.uniform(0.2, 0.65)
        self.body = add_obj(curve(pos=[self.start, self.start + vector(0.001, 0, 0)], radius=0.035 * strength, color=PULSE, opacity=0.72, emissive=True))
        self.head = add_obj(sphere(pos=self.start, radius=0.13 * strength, color=PULSE_BRIGHT, opacity=0.85, emissive=True))

    def update(self, dt):
        self.age += dt
        f = clamp(self.age / self.life, 0, 1)
        points = []
        segments = 16
        direction = self.end - self.start
        perp = vector(-direction.z, 0, direction.x)
        if mag(perp) > 0:
            perp = norm(perp)
        for i in range(segments + 1):
            u = i / segments
            visible_u = min(u, f)
            base = self.start + direction * visible_u
            wobble = math.sin(u * math.pi * 3.0 + self.age * 6.0) * self.wiggle * (1 - abs(0.5 - u))
            points.append(base + perp * wobble)
        self.body.clear()
        for p in points:
            self.body.append(p)
        self.head.pos = self.start + direction * f
        alpha = clamp(0.78 * (1 - f) + 0.08, 0.0, 0.78)
        self.body.opacity = alpha
        self.head.opacity = alpha
        return self.age < self.life


class RootLink:
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.strength = 0.0
        self.active = False
        initial_points = self.make_points()
        self.curve = add_obj(curve(pos=initial_points, radius=0.045, color=GHOST_LINK, opacity=0.20))
        self.travelers = []
        for i in range(3):
            self.travelers.append(add_obj(sphere(
                pos=initial_points[0],
                radius=0.12,
                color=PULSE_BRIGHT,
                opacity=0.0,
                emissive=True,
            )))

    def make_points(self):
        points = []
        ca = self.a.center
        cb = self.b.center
        direction = cb - ca
        perp = vector(-direction.z, 0, direction.x)
        if mag(perp) > 0:
            perp = norm(perp)
        for i in range(30):
            u = i / 29
            wiggle = math.sin(u * math.pi * 2.0) * 0.8
            p = lerp_vec(ground_pos(ca.x, ca.z, 0.15), ground_pos(cb.x, cb.z, 0.15), u) + perp * wiggle
            points.append(p)
        return points

    def update(self, dt, time_value):
        global network_strength
        target_strength = 1.0 if self.active else 0.12
        self.strength += (target_strength - self.strength) * dt * 0.55
        self.curve.visible = show_links
        self.curve.radius = 0.025 + 0.055 * self.strength
        self.curve.color = lerp_vec(GHOST_LINK, LINK_COLOR, self.strength)
        self.curve.opacity = 0.12 + 0.58 * self.strength

        pts = self.make_points()
        self.curve.clear()
        for p in pts:
            self.curve.append(p)

        if self.active and show_links:
            for i, traveler in enumerate(self.travelers):
                phase = (time_value * (0.13 + 0.03 * i) + i / len(self.travelers)) % 1.0
                idx = int(phase * (len(pts) - 1))
                traveler.pos = pts[idx] + vector(0, 0.08 + 0.10 * math.sin(time_value * 3 + i), 0)
                traveler.opacity = 0.45 + 0.35 * self.strength
                traveler.visible = True
        else:
            for traveler in self.travelers:
                traveler.opacity = 0.0
                traveler.visible = False

# -----------------------------------------------------------------------------
# Simulation construction
# -----------------------------------------------------------------------------
def create_initial_forest():
    centers = [
        vector(-14, 0, -12),
        vector(12, 0, -11),
        vector(-12, 0, 10),
        vector(12, 0, 10),
    ]
    for i, c in enumerate(centers):
        islands.append(ForestIsland(c, radius=random.uniform(2.2, 3.3), count=14, island_id=i))

    for i in range(len(islands)):
        for j in range(i + 1, len(islands)):
            if dist_xz(islands[i].center, islands[j].center) < 29:
                root_links.append(RootLink(islands[i], islands[j]))


def trigger_wave(origin=None):
    if origin is None:
        # Favor gaps between islands so new groves build corridors.
        candidates = [
            vector(0, 0, -11),
            vector(0, 0, 10),
            vector(-12, 0, 0),
            vector(12, 0, 0),
            vector(random.uniform(-8, 8), 0, random.uniform(-8, 8)),
        ]
        origin = random.choice(candidates)
        origin.x += random.uniform(-1.8, 1.8)
        origin.z += random.uniform(-1.8, 1.8)
    plant_waves.append(PlantingWave(origin))
    # Immediate signal pulse toward nearest islands.
    ordered = sorted(islands, key=lambda isl: dist_xz(origin, isl.center))[:2]
    for isl in ordered:
        pulses.append(RootPulse(origin, isl.center, strength=1.0))


def trigger_signal_burst():
    if not trees:
        return
    for _ in range(10):
        source = random.choice(trees).pos
        target_island = random.choice(islands).center
        pulses.append(RootPulse(source, target_island, strength=random.uniform(0.6, 1.0)))


def update_connectivity(dt):
    global network_strength
    # Link pairs strengthen when enough planted trees fill the corridor between islands.
    linked_pairs = 0
    for link in root_links:
        a = link.a.center
        b = link.b.center
        corridor_count = 0
        ab = b - a
        ab_len2 = ab.x * ab.x + ab.z * ab.z
        for tree in trees:
            if tree.planted:
                ap = tree.pos - a
                u = 0.0 if ab_len2 == 0 else clamp((ap.x * ab.x + ap.z * ab.z) / ab_len2, 0, 1)
                closest = a + ab * u
                if dist_xz(tree.pos, closest) < 3.2:
                    corridor_count += 1
        link.active = corridor_count >= 9 or link.strength > 0.68
        if link.active:
            link.a.connected.add(link.b.island_id)
            link.b.connected.add(link.a.island_id)
            linked_pairs += 1
    max_links = max(1, len(root_links))
    target_network = linked_pairs / max_links
    network_strength += (target_network - network_strength) * dt * 0.5


def reset_simulation():
    global wave_count, network_strength, t, paused, sim_speed
    clear_scene_objects()
    wave_count = 0
    network_strength = 0.0
    t = 0.0
    paused = False
    sim_speed = 1.0
    build_landscape()
    create_initial_forest()
    trigger_wave(vector(0, 0, -1))

# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------
status_label = None
help_label = None


def make_ui_labels():
    global status_label, help_label
    status_label = label(
        pos=vector(-20, 4.8, -20),
        text="",
        height=13,
        color=vector(0.09, 0.18, 0.10),
        box=True,
        border=8,
        opacity=0.18,
        line=False,
    )
    help_label = label(
        pos=vector(0, 6.0, 21.5),
        text="",
        height=11,
        color=vector(0.10, 0.17, 0.11),
        box=True,
        border=6,
        opacity=0.16,
        line=False,
    )


def update_ui():
    linked_pairs = sum(1 for link in root_links if link.active or link.strength > 0.55)
    status_label.text = (
        f"Reforestation Pulse Network\\n"
        f"trees: {len(trees)}   waves: {wave_count}   active signals: {len(pulses)}\\n"
        f"linked corridors: {linked_pairs}/{len(root_links)}   network strength: {network_strength:.2f}\\n"
        f"speed: {sim_speed:.1f}x   {'paused' if paused else 'running'}"
    )
    help_label.visible = show_help
    if show_help:
        help_label.text = (
            "SPACE pause/resume   W planting wave   S signal burst   R reset\\n"
            "F toggle links   UP/DOWN speed   H help"
        )


def handle_key(evt):
    global paused, show_links, show_help, sim_speed
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ("w", "W"):
        trigger_wave()
    elif key in ("s", "S"):
        trigger_signal_burst()
    elif key in ("r", "R"):
        reset_simulation()
    elif key in ("f", "F"):
        show_links = not show_links
    elif key in ("h", "H"):
        show_help = not show_help
    elif key == "up":
        sim_speed = min(4.0, sim_speed + 0.25)
    elif key == "down":
        sim_speed = max(0.25, sim_speed - 0.25)


scene.bind("keydown", handle_key)

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
make_ui_labels()
reset_simulation()

while True:
    rate(60)
    dt = 1 / 60 * sim_speed

    if not paused:
        t += dt

        # Periodic planting waves make reforestation arrive in visible waves.
        if int(t) > 0 and int(t) % 9 == 0 and (not plant_waves or plant_waves[-1].timer > 2.5):
            trigger_wave()

        # Occasional system-wide soil signal bursts.
        if random.random() < 0.018:
            trigger_signal_burst()

        for tree in trees:
            tree.update(dt, t)

        for island in islands:
            island.update(t)

        for wave in list(plant_waves):
            if not wave.update(dt):
                plant_waves.remove(wave)

        for pulse in list(pulses):
            if not pulse.update(dt):
                pulses.remove(pulse)

        update_connectivity(dt)

        for link in root_links:
            link.update(dt, t)

    update_ui()
