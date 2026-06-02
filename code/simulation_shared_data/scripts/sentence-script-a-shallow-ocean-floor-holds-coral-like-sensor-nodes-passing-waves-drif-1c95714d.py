"""
Listening Reef Network - Initial Simulation

A shallow ocean floor holds coral-like sensor nodes. Passing waves, drifting fish,
storm sparks, and sunlight bands stimulate the reef. Each node pulses when touched,
and nearby nodes strengthen their connection when they fire close together.

Controls:
    Space  - pause/resume
    R      - reset simulation
    H      - hide/show help text

Requires:
    pip install vpython
"""

from vpython import *
import random
import math
import time

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Listening Reef Network",
    width=1200,
    height=760,
    background=vector(0.78, 0.91, 0.96),
)
scene.forward = vector(-0.35, -0.52, -0.78)
scene.up = vector(0, 1, 0)
scene.camera.pos = vector(0, 32, 42)
scene.camera.axis = vector(0, -22, -42)
scene.autoscale = False
scene.range = 28

random.seed(12)

# -----------------------------
# Visual constants
# -----------------------------
OCEAN_BLUE = vector(0.38, 0.72, 0.88)
SEA_FLOOR = vector(0.72, 0.62, 0.45)
REEF_REST = vector(0.45, 0.56, 0.42)
REEF_ACTIVE = vector(1.0, 0.62, 0.20)
REEF_MEMORY = vector(0.72, 0.38, 0.92)
SIGNAL_BLUE = vector(0.18, 0.50, 1.0)
FISH_GREEN = vector(0.10, 0.75, 0.48)
SUN_GOLD = vector(1.0, 0.88, 0.28)
STORM_WHITE = vector(0.94, 0.98, 1.0)
CONNECTION_COLOR = vector(0.22, 0.45, 0.72)

# -----------------------------
# World objects
# -----------------------------
floor = box(
    pos=vector(0, -1.05, 0),
    size=vector(54, 0.25, 38),
    color=SEA_FLOOR,
    opacity=0.72,
)
water_sheet = box(
    pos=vector(0, 0.9, 0),
    size=vector(54, 3.5, 38),
    color=OCEAN_BLUE,
    opacity=0.16,
)

# Gentle surface wave lines
surface_lines = []
for i in range(7):
    z = -16 + i * 5.2
    line_points = []
    line = curve(color=vector(0.65, 0.88, 0.98), radius=0.035, opacity=0.42)
    for x in range(-26, 27, 2):
        pt = vector(x, 2.78, z)
        line_points.append(pt)
        line.append(pt)
    surface_lines.append({"curve": line, "points": line_points, "base_z": z, "phase": random.random() * math.tau})

# -----------------------------
# Classes
# -----------------------------
class ReefNode:
    def __init__(self, x, z, idx):
        self.idx = idx
        self.pos = vector(x, -0.45, z)
        self.energy = random.uniform(0.0, 0.25)
        self.memory = 0.0
        self.last_fire = -999.0
        self.refractory = 0.0
        self.height = random.uniform(0.55, 1.05)
        self.base_radius = random.uniform(0.18, 0.28)
        self.body = cone(
            pos=self.pos,
            axis=vector(0, self.height, 0),
            radius=self.base_radius,
            color=REEF_REST,
            opacity=0.92,
        )
        self.tip = sphere(
            pos=self.pos + vector(0, self.height + 0.08, 0),
            radius=self.base_radius * 0.62,
            color=REEF_REST,
            emissive=False,
            opacity=0.95,
        )
        self.ripple = ring(
            pos=self.tip.pos,
            axis=vector(0, 1, 0),
            radius=0.18,
            thickness=0.018,
            color=REEF_ACTIVE,
            opacity=0.0,
        )
        self.label = None

    def stimulate(self, amount, now):
        if self.refractory <= 0.0:
            self.energy += amount
        else:
            self.energy += amount * 0.25
        self.energy = min(self.energy, 1.6)

    def update(self, dt, now):
        self.refractory = max(0.0, self.refractory - dt)
        fired = False
        threshold = 0.72 - min(0.26, self.memory * 0.17)
        if self.energy > threshold and self.refractory <= 0.0:
            fired = True
            self.last_fire = now
            self.refractory = 0.58
            self.energy *= 0.28
            self.memory = min(3.0, self.memory + 0.08)
        else:
            self.energy *= 0.992
            self.memory *= 0.9995

        pulse = max(0.0, 1.0 - (now - self.last_fire) * 2.6)
        mem_blend = min(1.0, self.memory / 2.3)
        active_color = REEF_ACTIVE * pulse + REEF_MEMORY * mem_blend * (1 - pulse) + REEF_REST * max(0.0, 1 - pulse - 0.42 * mem_blend)
        self.body.color = active_color
        self.tip.color = active_color
        self.tip.emissive = pulse > 0.25
        self.tip.radius = self.base_radius * (0.62 + 0.55 * pulse + 0.12 * mem_blend)
        self.ripple.opacity = 0.42 * pulse
        self.ripple.radius = 0.22 + 1.25 * (1 - pulse)
        self.ripple.pos = self.tip.pos
        return fired


class MovingSignal:
    def __init__(self, kind):
        self.kind = kind
        self.reset()

    def reset(self):
        self.age = 0.0
        self.life = random.uniform(8.0, 13.0)
        side = random.choice(["left", "right", "front", "back"])
        if side == "left":
            self.pos = vector(-27, random.uniform(0.05, 2.5), random.uniform(-17, 17))
            self.vel = vector(random.uniform(2.2, 4.3), 0, random.uniform(-0.35, 0.35))
        elif side == "right":
            self.pos = vector(27, random.uniform(0.05, 2.5), random.uniform(-17, 17))
            self.vel = vector(random.uniform(-4.3, -2.2), 0, random.uniform(-0.35, 0.35))
        elif side == "front":
            self.pos = vector(random.uniform(-24, 24), random.uniform(0.05, 2.5), -18)
            self.vel = vector(random.uniform(-0.35, 0.35), 0, random.uniform(2.1, 4.2))
        else:
            self.pos = vector(random.uniform(-24, 24), random.uniform(0.05, 2.5), 18)
            self.vel = vector(random.uniform(-0.35, 0.35), 0, random.uniform(-4.2, -2.1))

        if self.kind == "wave":
            self.radius = random.uniform(1.8, 2.8)
            self.strength = random.uniform(0.16, 0.30)
            self.obj = ring(pos=self.pos, axis=vector(0, 1, 0), radius=self.radius, thickness=0.045, color=SIGNAL_BLUE, opacity=0.30)
        elif self.kind == "fish":
            self.radius = random.uniform(1.0, 1.7)
            self.strength = random.uniform(0.26, 0.42)
            self.obj = sphere(pos=self.pos, radius=0.36, color=FISH_GREEN, emissive=True, opacity=0.92)
            self.trail_points = []
            self.trail = curve(color=FISH_GREEN, radius=0.035, opacity=0.25)
        elif self.kind == "sun":
            self.radius = random.uniform(2.4, 4.0)
            self.strength = random.uniform(0.12, 0.22)
            self.obj = box(pos=self.pos, size=vector(3.2, 0.08, 0.38), color=SUN_GOLD, opacity=0.38)
        else:  # storm
            self.radius = random.uniform(1.3, 2.2)
            self.strength = random.uniform(0.38, 0.62)
            self.obj = sphere(pos=self.pos, radius=0.24, color=STORM_WHITE, emissive=True, opacity=0.95)
            self.flash = ring(pos=self.pos, axis=vector(0, 1, 0), radius=0.5, thickness=0.03, color=STORM_WHITE, opacity=0.55)

    def delete(self):
        self.obj.visible = False
        if hasattr(self, "trail"):
            self.trail.visible = False
        if hasattr(self, "flash"):
            self.flash.visible = False

    def update(self, dt, now):
        self.age += dt
        wobble = math.sin(now * 1.8 + self.pos.x * 0.09) * 0.018
        self.pos += self.vel * dt + vector(0, wobble, 0)
        self.obj.pos = self.pos

        if self.kind == "wave":
            self.obj.radius = self.radius + 0.35 * math.sin(now * 1.6 + self.age)
            self.obj.opacity = 0.22 + 0.10 * math.sin(now * 2.1)
        elif self.kind == "fish":
            self.obj.pos = self.pos
            self.obj.radius = 0.31 + 0.06 * math.sin(now * 7.0)
            self.trail_points.append(vector(self.pos.x, self.pos.y, self.pos.z))
            if len(self.trail_points) > 32:
                self.trail_points.pop(0)
            self.trail.clear()
            for pt in self.trail_points:
                self.trail.append(pt)
        elif self.kind == "sun":
            self.obj.pos = self.pos
            self.obj.axis = norm(self.vel) * 3.2
            self.obj.opacity = 0.24 + 0.12 * math.sin(now * 1.2)
        else:
            self.flash.pos = self.pos
            self.flash.radius = 0.35 + 1.4 * ((self.age * 2.0) % 1.0)
            self.flash.opacity = 0.44 * (1.0 - ((self.age * 2.0) % 1.0))

        out = abs(self.pos.x) > 31 or abs(self.pos.z) > 22 or self.age > self.life
        if out:
            self.delete()
            return False
        return True

# -----------------------------
# Build reef network
# -----------------------------
reef_nodes = []
rows = 6
cols = 9
idx = 0
for rz in range(rows):
    for cx in range(cols):
        x = -22 + cx * 5.5 + random.uniform(-0.8, 0.8)
        z = -13 + rz * 5.1 + random.uniform(-0.7, 0.7)
        if random.random() < 0.93:
            reef_nodes.append(ReefNode(x, z, idx))
            idx += 1

# Nearby connection curves with strength values
connections = []
for i, a in enumerate(reef_nodes):
    for j in range(i + 1, len(reef_nodes)):
        b = reef_nodes[j]
        d = mag(a.pos - b.pos)
        if d < 6.6 and random.random() < 0.78:
            c = curve(
                pos=[a.tip.pos, b.tip.pos],
                color=CONNECTION_COLOR,
                radius=0.018,
                opacity=0.10,
            )
            connections.append({"a": a, "b": b, "curve": c, "strength": 0.02})

# Floating status text
status = label(
    pos=vector(-25, 7.5, -18),
    text="Listening Reef Network\nreef sensation: 0\nnetwork memory: 0\nmode: sensing",
    height=14,
    box=False,
    line=False,
    color=vector(0.10, 0.16, 0.20),
    opacity=0,
)
help_label = label(
    pos=vector(0, 7.8, 18),
    text="Space: pause   R: reset   H: help\nNodes pulse when waves, fish, sun, or storm signals pass over them.\nRepeated co-firing strengthens blue connection paths.",
    height=12,
    box=False,
    line=False,
    color=vector(0.10, 0.16, 0.20),
    opacity=0,
)

# -----------------------------
# Simulation state
# -----------------------------
signals = []
time_now = 0.0
paused = False
show_help = True
spawn_timer = 0.0
sensation_total = 0
recent_fires = []


def reset_simulation():
    global signals, time_now, spawn_timer, sensation_total, recent_fires
    for s in signals:
        s.delete()
    signals = []
    time_now = 0.0
    spawn_timer = 0.0
    sensation_total = 0
    recent_fires = []
    for node in reef_nodes:
        node.energy = random.uniform(0.0, 0.18)
        node.memory = 0.0
        node.last_fire = -999.0
        node.refractory = 0.0
        node.body.color = REEF_REST
        node.tip.color = REEF_REST
        node.tip.emissive = False
        node.ripple.opacity = 0.0
    for link in connections:
        link["strength"] = 0.02
        link["curve"].opacity = 0.10
        link["curve"].radius = 0.018


def keydown(evt):
    global paused, show_help
    k = evt.key.lower()
    if k == " ":
        paused = not paused
    elif k == "r":
        reset_simulation()
    elif k == "h":
        show_help = not show_help
        help_label.visible = show_help

scene.bind("keydown", keydown)


def spawn_signal():
    roll = random.random()
    if roll < 0.46:
        kind = "wave"
    elif roll < 0.72:
        kind = "fish"
    elif roll < 0.90:
        kind = "sun"
    else:
        kind = "storm"
    signals.append(MovingSignal(kind))

# Preload a few events
for _ in range(6):
    spawn_signal()

# -----------------------------
# Main loop
# -----------------------------
last = time.time()
while True:
    rate(60)
    now_real = time.time()
    dt = min(0.04, now_real - last)
    last = now_real

    if paused:
        status.text = f"Listening Reef Network\nreef sensation: {sensation_total}\nnetwork memory: {sum(l['strength'] for l in connections):.1f}\nmode: paused"
        continue

    time_now += dt
    spawn_timer -= dt

    # Animate surface lines
    for surface in surface_lines:
        line = surface["curve"]
        phase = surface["phase"]
        base_z = surface["base_z"]
        for p_index, _ in enumerate(surface["points"]):
            x = -26 + p_index * 2
            y = 2.78 + 0.14 * math.sin(time_now * 1.4 + x * 0.26 + phase)
            z = base_z + 0.22 * math.sin(time_now * 0.8 + x * 0.13 + phase)
            new_pos = vector(x, y, z)
            surface["points"][p_index] = new_pos
            line.modify(p_index, pos=new_pos)

    if spawn_timer <= 0:
        spawn_signal()
        spawn_timer = random.uniform(0.65, 1.25)

    # Update moving signals and stimulate nodes
    active_signals = []
    for sig in signals:
        if sig.update(dt, time_now):
            active_signals.append(sig)
            for node in reef_nodes:
                dxz = vector(sig.pos.x - node.pos.x, 0, sig.pos.z - node.pos.z)
                d = mag(dxz)
                if d < sig.radius:
                    closeness = 1.0 - d / max(0.01, sig.radius)
                    node.stimulate(sig.strength * closeness, time_now)
                    # Visual contact glimmer
                    if random.random() < 0.012 + 0.04 * closeness:
                        spark = sphere(pos=node.tip.pos + vector(random.uniform(-0.2, 0.2), 0.12, random.uniform(-0.2, 0.2)), radius=0.055, color=REEF_ACTIVE, emissive=True, opacity=0.8)
                        spark.visible = False
        else:
            pass
    signals = active_signals

    # Update nodes and collect firing events
    fired_nodes = []
    for node in reef_nodes:
        if node.update(dt, time_now):
            fired_nodes.append(node)
            sensation_total += 1

    # Co-firing strengthens local links
    for link in connections:
        a = link["a"]
        b = link["b"]
        recent_a = time_now - a.last_fire < 0.45
        recent_b = time_now - b.last_fire < 0.45
        if recent_a and recent_b:
            link["strength"] = min(1.0, link["strength"] + 0.018)
        else:
            link["strength"] *= 0.9997
        st = link["strength"]
        link["curve"].modify(0, pos=a.tip.pos)
        link["curve"].modify(1, pos=b.tip.pos)
        link["curve"].opacity = 0.08 + 0.55 * st
        link["curve"].radius = 0.012 + 0.045 * st
        link["curve"].color = CONNECTION_COLOR * (1 - st * 0.4) + REEF_MEMORY * (st * 0.4)

    # Neighbor propagation: an early nervous-system behavior
    for node in fired_nodes:
        for link in connections:
            other = None
            if link["a"] is node:
                other = link["b"]
            elif link["b"] is node:
                other = link["a"]
            if other is not None:
                other.stimulate(0.035 + 0.10 * link["strength"], time_now)

    network_memory = sum(l["strength"] for l in connections)
    avg_node_memory = sum(n.memory for n in reef_nodes) / max(1, len(reef_nodes))
    if avg_node_memory > 1.2 and network_memory > 16:
        mode = "distributed listening"
    elif network_memory > 9:
        mode = "forming pathways"
    else:
        mode = "sensing"

    status.text = (
        "Listening Reef Network\n"
        f"reef sensation: {sensation_total}\n"
        f"network memory: {network_memory:.1f}\n"
        f"active signals: {len(signals)}\n"
        f"mode: {mode}"
    )
