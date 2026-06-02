from vpython import *
import random
import math

# Night Blossom Shrine
# A Kyoto shrine garden glows after dark as cherry trees bloom under lantern light,
# drawing slow-moving crowds through paths of falling petals.

scene = canvas(
    title="Night Blossom Shrine - VPython Sakura Garden",
    width=1200,
    height=760,
    background=vector(0.92, 0.94, 0.98),
    center=vector(0, 1.6, 0),
)
scene.camera.pos = vector(0, 10, 22)
scene.camera.axis = vector(0, -6, -22)
scene.forward = vector(0, -0.23, -0.97)
scene.up = vector(0, 1, 0)

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def rand_vec_xz(radius):
    a = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius)
    return vector(math.cos(a) * r, 0, math.sin(a) * r)


def make_glow_sphere(pos, radius, col, opacity=0.18):
    return sphere(pos=pos, radius=radius, color=col, opacity=opacity, emissive=True)

# -----------------------------
# Ground, walkway, shrine
# -----------------------------

grass = box(pos=vector(0, -0.06, 0), size=vector(28, 0.12, 22), color=vector(0.78, 0.86, 0.72))
path = box(pos=vector(0, 0.01, 0), size=vector(4.2, 0.06, 21), color=vector(0.72, 0.68, 0.59))
path_edge_l = box(pos=vector(-2.25, 0.05, 0), size=vector(0.12, 0.08, 21), color=vector(0.50, 0.43, 0.35))
path_edge_r = box(pos=vector(2.25, 0.05, 0), size=vector(0.12, 0.08, 21), color=vector(0.50, 0.43, 0.35))

# Torii-style gate at front
red = vector(0.78, 0.16, 0.11)
dark_red = vector(0.55, 0.08, 0.06)
box(pos=vector(-2.9, 2.0, 8.4), size=vector(0.35, 4.0, 0.35), color=red)
box(pos=vector(2.9, 2.0, 8.4), size=vector(0.35, 4.0, 0.35), color=red)
box(pos=vector(0, 4.0, 8.4), size=vector(6.6, 0.35, 0.45), color=red)
box(pos=vector(0, 4.45, 8.4), size=vector(7.3, 0.25, 0.55), color=dark_red)
box(pos=vector(0, 3.35, 8.4), size=vector(5.2, 0.18, 0.35), color=dark_red)

# Shrine building in the back
shrine_base = box(pos=vector(0, 0.45, -8.6), size=vector(7.4, 0.9, 3.2), color=vector(0.56, 0.34, 0.22))
shrine_body = box(pos=vector(0, 1.45, -8.6), size=vector(6.4, 1.7, 2.6), color=vector(0.83, 0.74, 0.61))
roof1 = box(pos=vector(0, 2.65, -8.6), size=vector(7.7, 0.35, 3.8), color=vector(0.24, 0.20, 0.18))
roof2 = box(pos=vector(0, 2.95, -8.6), size=vector(6.8, 0.24, 3.2), color=vector(0.30, 0.25, 0.21))
for x in [-2.3, 0, 2.3]:
    cylinder(pos=vector(x, 0.95, -7.0), axis=vector(0, 1.3, 0), radius=0.10, color=red)

# Label panel
counter_label = label(
    pos=vector(-9.2, 5.7, 8),
    text="Night viewing begins\nLanterns: 0% | Bloom: 0% | Visitors: 0",
    color=vector(0.12, 0.10, 0.12),
    box=True,
    background=vector(1.0, 0.96, 0.90),
    opacity=0.65,
    height=14,
)

# -----------------------------
# Lanterns
# -----------------------------

lanterns = []
lantern_positions = []
for z in [-7.0, -4.8, -2.6, -0.4, 1.8, 4.0, 6.2]:
    for x in [-3.4, 3.4]:
        lantern_positions.append(vector(x, 0, z))

for i, p in enumerate(lantern_positions):
    post = cylinder(pos=p + vector(0, 0.0, 0), axis=vector(0, 1.7, 0), radius=0.06, color=vector(0.18, 0.13, 0.10))
    cap = box(pos=p + vector(0, 1.85, 0), size=vector(0.65, 0.10, 0.65), color=vector(0.20, 0.15, 0.12))
    lamp = sphere(pos=p + vector(0, 1.55, 0), radius=0.28, color=vector(1.0, 0.72, 0.31), opacity=0.45, emissive=True)
    glow = make_glow_sphere(p + vector(0, 1.55, 0), 1.10, vector(1.0, 0.62, 0.22), opacity=0.04)
    lanterns.append({"lamp": lamp, "glow": glow, "phase": random.uniform(0, 6.28), "index": i})

# -----------------------------
# Cherry trees
# -----------------------------

class CherryTree:
    def __init__(self, base, height, spread, seed):
        random.seed(seed)
        self.base = base
        self.height = height
        self.spread = spread
        self.phase = random.uniform(0, 2 * math.pi)
        self.trunk = cylinder(pos=base, axis=vector(0, height * 0.62, 0), radius=0.18, color=vector(0.36, 0.22, 0.14))
        self.branches = []
        trunk_top = base + vector(0, height * 0.58, 0)
        for j in range(8):
            ang = j * 2 * math.pi / 8 + random.uniform(-0.20, 0.20)
            length = random.uniform(1.1, 1.9) * spread
            up = random.uniform(0.35, 0.85)
            axis = vector(math.cos(ang) * length, up, math.sin(ang) * length)
            b = cylinder(pos=trunk_top, axis=axis, radius=random.uniform(0.045, 0.085), color=vector(0.33, 0.19, 0.12))
            self.branches.append(b)
        self.blossoms = []
        for k in range(28):
            offset = rand_vec_xz(spread * random.uniform(0.35, 1.25))
            pos = trunk_top + offset + vector(0, random.uniform(0.3, 1.5), 0)
            r = random.uniform(0.20, 0.34)
            c = vector(1.0, random.uniform(0.63, 0.82), random.uniform(0.78, 0.96))
            bl = sphere(pos=pos, radius=r, color=c, opacity=0.80, emissive=True)
            self.blossoms.append({"obj": bl, "base": vector(pos.x, pos.y, pos.z), "r": r, "phase": random.uniform(0, 6.28)})
        self.glow = sphere(pos=trunk_top + vector(0, 0.7, 0), radius=spread * 1.55, color=vector(1.0, 0.64, 0.82), opacity=0.035, emissive=True)

    def update(self, t, bloom, lantern_power):
        sway = 0.055 * math.sin(t * 1.4 + self.phase)
        glow_strength = clamp(0.025 + 0.055 * bloom + 0.035 * lantern_power, 0.02, 0.15)
        self.glow.opacity = glow_strength
        self.glow.radius = self.spread * (1.28 + 0.38 * bloom + 0.06 * math.sin(t + self.phase))
        for data in self.blossoms:
            obj = data["obj"]
            obj.visible = bloom > 0.04
            pulse = 0.82 + 0.22 * math.sin(t * 2.0 + data["phase"])
            obj.radius = data["r"] * (0.35 + bloom * 0.85) * pulse
            obj.opacity = clamp(0.25 + 0.70 * bloom, 0.20, 0.95)
            base = data["base"]
            obj.pos = base + vector(sway * (base.y - self.base.y), 0.025 * math.sin(t * 1.7 + data["phase"]), 0)


tree_specs = [
    (vector(-6.7, 0.02, -6.7), 3.4, 1.45),
    (vector(6.5, 0.02, -6.0), 3.6, 1.50),
    (vector(-6.1, 0.02, -2.5), 3.1, 1.30),
    (vector(6.2, 0.02, -1.8), 3.3, 1.40),
    (vector(-6.8, 0.02, 2.0), 3.5, 1.55),
    (vector(6.7, 0.02, 2.6), 3.2, 1.35),
    (vector(-5.7, 0.02, 6.1), 3.0, 1.25),
    (vector(5.7, 0.02, 6.1), 3.0, 1.25),
]

trees = [CherryTree(base, h, s, 100 + i) for i, (base, h, s) in enumerate(tree_specs)]

# -----------------------------
# Visitors
# -----------------------------

class Visitor:
    def __init__(self, z, side_offset, col):
        self.base_x = side_offset
        self.speed = random.uniform(0.012, 0.028)
        self.phase = random.uniform(0, 6.28)
        self.body = sphere(pos=vector(side_offset, 0.55, z), radius=0.22, color=col)
        self.head = sphere(pos=vector(side_offset, 0.92, z), radius=0.13, color=vector(0.82, 0.64, 0.48))
        self.aura = sphere(pos=vector(side_offset, 0.63, z), radius=0.50, color=vector(1.0, 0.78, 0.48), opacity=0.02, emissive=True)
        self.pause_timer = random.uniform(0, 1)

    def update(self, t):
        # Slow procession: visitors pause briefly near trees, then continue.
        z = self.body.pos.z
        attraction = 0.5 + 0.5 * math.sin(0.9 * t + self.phase)
        near_view = abs(z - random.choice([-5.0, -1.5, 2.5, 6.0])) < 0.35
        pause_factor = 0.25 if near_view and attraction > 0.55 else 1.0
        z -= self.speed * pause_factor
        if z < -8.4:
            z = 8.2 + random.uniform(0, 1.5)
        x = self.base_x + 0.10 * math.sin(t * 1.8 + self.phase)
        bob = 0.035 * math.sin(t * 5.0 + self.phase)
        self.body.pos = vector(x, 0.55 + bob, z)
        self.head.pos = vector(x, 0.92 + bob, z)
        self.aura.pos = vector(x, 0.63 + bob, z)
        self.aura.opacity = 0.012 + 0.014 * attraction

visitors = []
visitor_cols = [vector(0.20, 0.25, 0.42), vector(0.36, 0.22, 0.36), vector(0.16, 0.35, 0.32), vector(0.45, 0.32, 0.21)]
for i in range(18):
    x = random.uniform(-1.5, 1.5)
    z = random.uniform(-8.0, 8.2)
    visitors.append(Visitor(z, x, random.choice(visitor_cols)))

# -----------------------------
# Falling petals and ground drifts
# -----------------------------

petals = []
for i in range(160):
    tree = random.choice(trees)
    pos = tree.base + vector(random.uniform(-2.2, 2.2), random.uniform(2.4, 5.2), random.uniform(-1.7, 1.7))
    petal = sphere(pos=pos, radius=random.uniform(0.035, 0.065), color=vector(1.0, random.uniform(0.65, 0.85), random.uniform(0.82, 0.98)), opacity=0.78, emissive=True)
    petals.append({
        "obj": petal,
        "origin": tree.base,
        "fall": random.uniform(0.008, 0.027),
        "phase": random.uniform(0, 6.28),
        "grounded": False,
    })

petal_drifts = []
for z in [-6.5, -4.5, -2.5, -0.5, 1.5, 3.5, 5.5, 7.0]:
    drift = ellipsoid(pos=vector(random.uniform(-1.8, 1.8), 0.09, z), length=random.uniform(0.5, 1.1), height=0.025, width=random.uniform(0.18, 0.35), color=vector(1.0, 0.73, 0.88), opacity=0.38)
    petal_drifts.append(drift)

# -----------------------------
# Moon and atmosphere
# -----------------------------

moon = sphere(pos=vector(8.8, 8.5, -7.5), radius=0.75, color=vector(1.0, 0.96, 0.82), emissive=True)
moon_glow = sphere(pos=moon.pos, radius=2.3, color=vector(1.0, 0.95, 0.72), opacity=0.045, emissive=True)
soft_fog = []
for i in range(18):
    soft_fog.append(sphere(pos=vector(random.uniform(-10, 10), random.uniform(0.05, 0.5), random.uniform(-8.5, 8.5)), radius=random.uniform(0.5, 1.4), color=vector(0.95, 0.89, 0.96), opacity=0.018))

# -----------------------------
# Animation loop
# -----------------------------

t = 0.0
while True:
    rate(60)
    t += 0.016

    # Scene phases: lanterns wake first, blossoms reach full glow, crowd continues.
    lantern_power = clamp(t / 8.0, 0.0, 1.0)
    bloom = clamp((t - 2.5) / 10.0, 0.0, 1.0)
    wind = vector(0.018 * math.sin(t * 0.8), 0, 0.012 * math.cos(t * 0.6))

    # Lantern pulsing
    for l in lanterns:
        local_on = clamp((t - l["index"] * 0.32) / 2.0, 0.0, 1.0)
        flicker = 0.85 + 0.15 * math.sin(t * 4.0 + l["phase"])
        l["lamp"].opacity = 0.18 + 0.55 * local_on * flicker
        l["lamp"].radius = 0.22 + 0.075 * local_on * flicker
        l["glow"].opacity = 0.012 + 0.08 * local_on * flicker
        l["glow"].radius = 0.75 + 0.85 * local_on * flicker

    # Blossoming trees
    for tree in trees:
        tree.update(t, bloom, lantern_power)

    # Visitors
    for v in visitors:
        v.update(t)

    # Petals fall only strongly once bloom starts.
    active_fall = clamp((bloom - 0.18) / 0.82, 0.0, 1.0)
    for data in petals:
        p = data["obj"]
        if active_fall <= 0.01:
            p.opacity = 0.20
            continue
        data["grounded"] = p.pos.y < 0.13
        if not data["grounded"]:
            sway = vector(0.025 * math.sin(t * 1.9 + data["phase"]), 0, 0.020 * math.cos(t * 1.5 + data["phase"]))
            p.pos = p.pos + wind + sway - vector(0, data["fall"] * active_fall, 0)
            p.opacity = 0.35 + 0.45 * active_fall
        else:
            # On the path, petals slide lightly and join the visible pink drifts.
            p.pos.y = 0.10
            p.pos.x += 0.002 * math.sin(t + data["phase"])
            p.opacity = 0.28
            if random.random() < 0.015:
                origin = data["origin"]
                p.pos = origin + vector(random.uniform(-2.2, 2.2), random.uniform(3.4, 5.4), random.uniform(-1.7, 1.7))
                data["phase"] = random.uniform(0, 6.28)
        # Recycle petals if blown too far away.
        if abs(p.pos.x) > 10 or abs(p.pos.z) > 10:
            origin = data["origin"]
            p.pos = origin + vector(random.uniform(-2.2, 2.2), random.uniform(3.2, 5.2), random.uniform(-1.7, 1.7))

    # Petal drifts brighten as the ground collects blossoms.
    for i, d in enumerate(petal_drifts):
        d.opacity = 0.18 + 0.28 * active_fall + 0.07 * math.sin(t * 0.7 + i)
        d.length = 0.55 + 0.55 * active_fall + 0.04 * math.sin(t + i)

    # Soft fog moves slowly through the shrine garden.
    for i, f in enumerate(soft_fog):
        f.pos.x += 0.006 * math.sin(t * 0.25 + i)
        f.pos.z += 0.005 * math.cos(t * 0.21 + i)
        f.opacity = 0.010 + 0.014 * math.sin(t * 0.4 + i) ** 2

    # Subtle moon glow
    moon_glow.opacity = 0.035 + 0.012 * math.sin(t * 0.5) ** 2

    counter_label.text = (
        "Night viewing at Hirano-style shrine\n"
        f"Lanterns: {int(lantern_power * 100):3d}% | "
        f"Bloom: {int(bloom * 100):3d}% | "
        f"Visitors: {len(visitors)}\n"
        "Falling petals collect along the lantern path"
    )
