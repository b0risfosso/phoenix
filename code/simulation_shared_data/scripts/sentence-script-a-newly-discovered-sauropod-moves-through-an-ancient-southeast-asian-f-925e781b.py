"""
Nagatitan Giant Walk
VPython simulation based on the seed:

A newly discovered sauropod moves through an ancient Southeast Asian floodplain,
its 88-foot body reshaping trees, mud, and riverbanks with every step.

Controls:
- Space: pause/resume
- R: reset
- Up/Down: change walking speed
- T: toggle tree recovery
- C: cycle camera

Light styling. No CSV logging.
"""

from vpython import *
import math
import random

scene = canvas(
    title="Nagatitan Giant Walk",
    width=1200,
    height=760,
    background=vector(0.86, 0.93, 1.0),
    center=vector(0, 0.8, 0),
    forward=vector(-0.54, -0.28, -0.79),
    range=30,
)

scene.caption = """
Nagatitan Giant Walk
A giant sauropod crosses an ancient floodplain, reshaping mud, trees, and riverbanks.
Space pause/resume | R reset | Up/Down speed | T tree recovery | C camera
"""

MUD = vector(0.50, 0.39, 0.28)
WET_MUD = vector(0.36, 0.29, 0.22)
GRASS = vector(0.45, 0.65, 0.36)
WATER = vector(0.32, 0.62, 0.82)
WATER_LIGHT = vector(0.54, 0.82, 0.92)
TREE_TRUNK = vector(0.40, 0.25, 0.12)
TREE_LEAF = vector(0.23, 0.55, 0.26)
TREE_LEAF_LIGHT = vector(0.38, 0.70, 0.33)
DINO_BODY = vector(0.55, 0.62, 0.50)
DINO_DARK = vector(0.38, 0.45, 0.36)
DINO_BELLY = vector(0.68, 0.70, 0.58)
DINO_SPOT = vector(0.30, 0.36, 0.29)
TEXT = vector(0.10, 0.12, 0.16)
GUIDE = vector(0.72, 0.78, 0.84)
SPLASH = vector(0.70, 0.90, 1.0)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return a + (b - a) * t


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-7:
        return fallback
    return v / m


def ground_y_at(x, z):
    return -2.2 + 0.08 * math.sin(x * 0.22) + 0.05 * math.cos(z * 0.5)


def reset_curve(c, pts):
    c.clear()
    for p in pts:
        c.append(pos=p)

# ---------------------------------------------------------------------
# Floodplain
# ---------------------------------------------------------------------

ground = box(pos=vector(0, -2.45, 0), size=vector(76, 0.32, 42), color=MUD)

for i in range(48):
    x = random.uniform(-35, 35)
    z = random.uniform(-18, 18)
    if -5.8 < z < -3.2:
        continue
    ellipsoid(
        pos=vector(x, ground_y_at(x, z) + 0.05, z),
        length=random.uniform(1.0, 3.4),
        height=0.035,
        width=random.uniform(0.45, 1.45),
        color=lerp(GRASS, TREE_LEAF_LIGHT, random.random() * 0.35),
        opacity=random.uniform(0.35, 0.68),
    )

river = box(pos=vector(0, -2.16, -8.5), size=vector(78, 0.08, 5.4), color=WATER, opacity=0.72)
river_highlight = curve(pos=[vector(-38, -2.07, -7.0), vector(38, -2.07, -7.0)], radius=0.035, color=WATER_LIGHT, opacity=0.45)
riverbank_front = curve(pos=[vector(-38, -2.02, -5.6), vector(38, -2.02, -5.6)], radius=0.05, color=WET_MUD, opacity=0.85)
riverbank_back = curve(pos=[vector(-38, -2.02, -11.2), vector(38, -2.02, -11.2)], radius=0.05, color=WET_MUD, opacity=0.72)

puddles = []
for i in range(20):
    x = random.uniform(-34, 34)
    z = random.uniform(-3.0, 16.0)
    puddles.append(ellipsoid(
        pos=vector(x, ground_y_at(x, z) + 0.055, z),
        length=random.uniform(1.2, 3.2),
        height=0.025,
        width=random.uniform(0.5, 1.7),
        color=lerp(WATER, WET_MUD, 0.25),
        opacity=random.uniform(0.28, 0.46),
    ))

# Scale guide for 88 feet / 27 meters.
scale_line = curve(pos=[vector(-28, -1.98, 15.8), vector(-1.2, -1.98, 15.8)], radius=0.035, color=GUIDE, opacity=0.75)
for sx in [-28, -1.2]:
    cylinder(pos=vector(sx, -2.1, 15.8), axis=vector(0, 0.6, 0), radius=0.045, color=GUIDE, opacity=0.85)
label(pos=vector(-14.6, -1.1, 15.8), text="88 ft / 27 m body length scale", height=12, color=TEXT, box=False, opacity=0)

for i in range(10):
    ellipsoid(
        pos=vector(random.uniform(-34, 34), random.uniform(5.0, 9.0), random.uniform(-18, 14)),
        length=random.uniform(5.0, 12.0),
        height=random.uniform(0.18, 0.45),
        width=random.uniform(1.2, 3.2),
        color=vector(1, 1, 1),
        opacity=0.22,
    )

# ---------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------

trees = []
tree_recovery = False

class FloodplainTree:
    def __init__(self, x, z, height, radius, index):
        self.index = index
        self.base = vector(x, ground_y_at(x, z) + 0.05, z)
        self.height = height
        self.radius = radius
        self.lean = vector(0, 0, 0)
        self.lean_vel = vector(0, 0, 0)
        self.fallen = False
        self.fall_dir = vector(1, 0, 0)
        self.fall_angle = 0.0
        self.trunk = cylinder(pos=self.base, axis=vector(0, self.height, 0), radius=self.radius, color=TREE_TRUNK)
        self.crown = ellipsoid(
            pos=self.base + vector(0, self.height + 0.5, 0),
            length=self.height * 0.85,
            height=self.height * 0.62,
            width=self.height * 0.75,
            color=lerp(TREE_LEAF, TREE_LEAF_LIGHT, random.random() * 0.4),
            opacity=0.86,
        )
        self.shadow = ellipsoid(
            pos=self.base + vector(0.3, 0.02, 0.2),
            length=self.height * 0.65,
            height=0.018,
            width=self.height * 0.42,
            color=vector(0.25, 0.28, 0.20),
            opacity=0.16,
        )

    def disturb(self, source_pos, strength):
        if self.fallen:
            return
        away = self.base - source_pos
        away.y = 0
        away = safe_norm(away, vector(0, 0, 1))
        self.lean_vel += away * (0.025 * strength / max(0.7, self.height))
        if strength > 3.2 and random.random() < 0.12:
            self.fallen = True
            self.fall_dir = away

    def update(self, dt, t):
        if self.fallen:
            self.fall_angle = clamp(self.fall_angle + dt * 1.05, 0, math.radians(78))
            trunk_axis = vector(
                self.fall_dir.x * math.sin(self.fall_angle) * self.height,
                math.cos(self.fall_angle) * self.height,
                self.fall_dir.z * math.sin(self.fall_angle) * self.height,
            )
            self.trunk.axis = trunk_axis
            self.crown.pos = self.base + trunk_axis + self.fall_dir * 0.35
            self.crown.height = self.height * 0.50
            self.shadow.opacity = 0.22
            return

        if tree_recovery:
            self.lean_vel += -self.lean * 0.025
        self.lean_vel *= 0.94
        self.lean += self.lean_vel
        if mag(self.lean) > 1.25:
            self.lean = safe_norm(self.lean) * 1.25
        wind = vector(0.12 * math.sin(t * 0.8 + self.index), 0, 0.10 * math.cos(t * 0.7 + self.index))
        top_offset = self.lean + wind * 0.25
        self.trunk.axis = vector(top_offset.x, self.height, top_offset.z)
        self.crown.pos = self.base + self.trunk.axis + vector(0, 0.5, 0)
        self.shadow.pos = self.base + vector(0.4 + top_offset.x * 0.3, 0.02, 0.2 + top_offset.z * 0.3)

for i in range(38):
    x = random.uniform(-32, 34)
    z = random.choice([random.uniform(-17, -11.8), random.uniform(-5.0, -1.2), random.uniform(4.0, 17.5)])
    trees.append(FloodplainTree(x, z, random.uniform(1.5, 3.7), random.uniform(0.06, 0.15), i))

# ---------------------------------------------------------------------
# Footfall effects
# ---------------------------------------------------------------------

footprints = []
mud_ripples = []
river_slumps = []
splashes = []

class Footprint:
    def __init__(self, pos):
        self.age = 0.0
        self.pos = vector(pos.x, ground_y_at(pos.x, pos.z) + 0.07, pos.z)
        self.depression = ellipsoid(pos=self.pos, length=1.25, height=0.035, width=0.70, color=WET_MUD, opacity=0.78)
        self.rim = ring(pos=self.pos + vector(0, 0.025, 0), axis=vector(0, 1, 0), radius=0.55, thickness=0.025, color=lerp(MUD, WET_MUD, 0.5), opacity=0.45)

    def update(self, dt):
        self.age += dt
        self.depression.opacity = max(0.18, 0.78 - self.age * 0.018)
        self.rim.opacity = max(0.08, 0.45 - self.age * 0.020)
        return self.age < 55

    def hide(self):
        self.depression.visible = False
        self.rim.visible = False

class MudRipple:
    def __init__(self, pos, strength=1.0):
        self.age = 0.0
        self.strength = strength
        self.obj = ring(pos=vector(pos.x, ground_y_at(pos.x, pos.z) + 0.09, pos.z), axis=vector(0, 1, 0), radius=0.25, thickness=0.025, color=WET_MUD, opacity=0.44)

    def update(self, dt):
        self.age += dt
        fade = clamp(1 - self.age / 2.2, 0, 1)
        self.obj.radius = 0.25 + self.age * (1.5 + self.strength)
        self.obj.opacity = 0.38 * fade
        self.obj.thickness = 0.016 + 0.015 * fade
        return self.age < 2.2

    def hide(self):
        self.obj.visible = False

class RiverSlump:
    def __init__(self, x, z):
        self.age = 0.0
        self.obj = ellipsoid(pos=vector(x, -2.03, z), length=random.uniform(1.2, 2.4), height=0.06, width=random.uniform(0.4, 1.0), color=WET_MUD, opacity=0.58)
        self.slide = vector(random.uniform(-0.02, 0.02), -0.002, -0.020)

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.slide
        self.obj.opacity = clamp(0.58 - self.age * 0.06, 0, 0.58)
        self.obj.length *= 1.003
        return self.age < 8.0

    def hide(self):
        self.obj.visible = False

class Splash:
    def __init__(self, origin):
        self.age = 0.0
        self.vel = vector(random.uniform(-0.04, 0.04), random.uniform(0.04, 0.12), random.uniform(-0.04, 0.02))
        self.obj = sphere(pos=origin, radius=random.uniform(0.035, 0.075), color=SPLASH, opacity=0.74, emissive=True)

    def update(self, dt):
        self.age += dt
        self.obj.pos += self.vel
        self.vel += vector(0, -0.004, 0)
        self.vel *= 0.965
        self.obj.opacity = 0.74 * clamp(1 - self.age / 1.4, 0, 1)
        return self.age < 1.4

    def hide(self):
        self.obj.visible = False

def create_footfall(pos):
    footprints.append(Footprint(pos))
    mud_ripples.append(MudRipple(pos, strength=1.2))
    for tr in trees:
        d = mag(tr.base - pos)
        if d < 3.1:
            tr.disturb(pos, (3.1 - d) * 1.5)
    if -6.9 < pos.z < -3.5:
        river_slumps.append(RiverSlump(pos.x, -5.7))
        for _ in range(8):
            splashes.append(Splash(vector(pos.x + random.uniform(-0.8, 0.8), -1.95, -6.3 + random.uniform(-0.5, 0.4))))

# ---------------------------------------------------------------------
# Dinosaur
# ---------------------------------------------------------------------

class Nagatitan:
    def __init__(self):
        self.pos = vector(-30, 0.2, 0.4)
        self.walk_speed = 0.82
        self.phase = 0.0
        self.body = ellipsoid(pos=self.pos, length=7.6, height=2.25, width=2.45, color=DINO_BODY)
        self.belly = ellipsoid(pos=self.pos + vector(0.2, -0.28, 0), length=6.7, height=1.45, width=2.15, color=DINO_BELLY, opacity=0.68)
        self.neck_segments = [cylinder(pos=self.pos, axis=vector(0.8, 0.25, 0), radius=0.38 - i * 0.018, color=DINO_BODY) for i in range(7)]
        self.head = ellipsoid(pos=self.pos + vector(5.8, 2.4, 0), length=1.2, height=0.55, width=0.55, color=DINO_DARK)
        self.snout = ellipsoid(pos=self.pos + vector(6.45, 2.35, 0), length=0.7, height=0.32, width=0.36, color=DINO_DARK)
        self.eye_l = sphere(pos=self.pos + vector(6.15, 2.55, -0.22), radius=0.055, color=vector(0.02, 0.02, 0.02))
        self.eye_r = sphere(pos=self.pos + vector(6.15, 2.55, 0.22), radius=0.055, color=vector(0.02, 0.02, 0.02))
        self.tail_segments = [cylinder(pos=self.pos, axis=vector(-0.75, 0, 0), radius=0.58 - i * 0.055, color=DINO_BODY) for i in range(8)]
        self.legs = []
        for name, local, offset in [
            ("front_l", vector(2.2, -0.85, -0.72), 0.0),
            ("front_r", vector(2.2, -0.85, 0.72), math.pi),
            ("back_l", vector(-2.2, -0.85, -0.78), math.pi),
            ("back_r", vector(-2.2, -0.85, 0.78), 0.0),
        ]:
            self.legs.append({
                "local": local,
                "offset": offset,
                "upper": cylinder(pos=self.pos, axis=vector(0, -1.25, 0), radius=0.38, color=DINO_DARK),
                "lower": cylinder(pos=self.pos, axis=vector(0, -1.0, 0), radius=0.31, color=DINO_DARK),
                "foot": ellipsoid(pos=self.pos, length=1.15, height=0.22, width=0.58, color=DINO_DARK),
                "last_grounded": False,
            })
        self.spots = []
        for i in range(18):
            lx = random.uniform(-3.2, 2.8)
            ly = random.uniform(0.3, 1.1)
            lz = random.choice([-1, 1]) * random.uniform(1.05, 1.28)
            self.spots.append({"local": vector(lx, ly, lz), "obj": sphere(pos=self.pos + vector(lx, ly, lz), radius=random.uniform(0.08, 0.18), color=DINO_SPOT, opacity=0.55)})

    def local_to_world(self, local):
        return self.pos + local

    def update(self, dt, t):
        self.phase += dt * self.walk_speed * 1.65
        self.pos.x += dt * self.walk_speed * 1.55
        self.pos.y = 0.16 + 0.10 * math.sin(self.phase * 2.0)
        if self.pos.x > 36:
            self.pos.x = -36
        body_bob = 0.08 * math.sin(self.phase * 2.0)
        self.body.pos = self.local_to_world(vector(0, body_bob, 0))
        self.belly.pos = self.local_to_world(vector(0.2, -0.30 + body_bob, 0))
        neck_base = self.local_to_world(vector(3.05, 0.72 + body_bob, 0))
        prev = neck_base
        for i, seg in enumerate(self.neck_segments):
            u = (i + 1) / len(self.neck_segments)
            sway = 0.18 * math.sin(self.phase * 0.8 + i * 0.55)
            target = self.local_to_world(vector(3.05 + u * 3.1, 0.72 + body_bob + 1.65 * math.sin(u * math.pi / 2), sway))
            seg.pos = prev
            seg.axis = target - prev
            seg.radius = max(0.22, 0.42 - i * 0.028)
            prev = target
        self.head.pos = prev + vector(0.52, 0.02, 0.05 * math.sin(self.phase))
        self.snout.pos = self.head.pos + vector(0.62, -0.04, 0)
        self.eye_l.pos = self.head.pos + vector(0.18, 0.17, -0.24)
        self.eye_r.pos = self.head.pos + vector(0.18, 0.17, 0.24)
        tail_base = self.local_to_world(vector(-3.75, 0.34 + body_bob, 0))
        prev = tail_base
        for i, seg in enumerate(self.tail_segments):
            u = (i + 1) / len(self.tail_segments)
            sway = 0.45 * math.sin(self.phase * 0.65 + i * 0.45)
            target = self.local_to_world(vector(-3.75 - u * 5.2, 0.34 + body_bob - 0.20 * u, sway * u))
            seg.pos = prev
            seg.axis = target - prev
            seg.radius = max(0.10, 0.55 - i * 0.055)
            prev = target
        for leg in self.legs:
            leg_phase = self.phase + leg["offset"]
            step = math.sin(leg_phase)
            lift = max(0, step) * 0.60
            swing = 0.48 * math.cos(leg_phase)
            hip = self.local_to_world(leg["local"] + vector(0, body_bob, 0))
            knee = hip + vector(swing * 0.28, -1.25 + lift * 0.28, 0)
            foot = hip + vector(swing, -2.26 + lift, 0)
            ground_level = ground_y_at(foot.x, foot.z) + 0.16
            grounded = foot.y <= ground_level + 0.09 and step < -0.72
            if grounded:
                foot.y = ground_level
            leg["upper"].pos = hip
            leg["upper"].axis = knee - hip
            leg["lower"].pos = knee
            leg["lower"].axis = foot - knee
            leg["foot"].pos = foot + vector(0.15, -0.04, 0)
            leg["foot"].length = 1.1 + 0.15 * abs(math.cos(leg_phase))
            if grounded and not leg["last_grounded"]:
                create_footfall(foot)
            leg["last_grounded"] = grounded
        for spot in self.spots:
            spot["obj"].pos = self.local_to_world(spot["local"] + vector(0, 0.04 * math.sin(self.phase * 2 + spot["local"].x), 0))

    def disturb_environment(self):
        points = [self.body.pos, self.head.pos, self.tail_segments[-1].pos + self.tail_segments[-1].axis]
        for tr in trees:
            for p in points:
                d = mag(tr.base - p)
                if d < 3.7:
                    tr.disturb(p, (3.7 - d) * 0.8)

dino = Nagatitan()

# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

title_label = label(pos=vector(-22, 10.4, -8.8), text="Nagatitan Giant Walk", height=17, color=TEXT, box=False, opacity=0)
status_label = label(pos=vector(-22, 9.1, -8.8), text="", height=12, color=TEXT, box=False, opacity=0)
impact_label = label(pos=vector(18, 9.5, -8.8), text="", height=13, color=TEXT, box=False, opacity=0)
impact_back = box(pos=vector(18, 8.55, -8.8), size=vector(7.0, 0.20, 0.12), color=GUIDE, opacity=0.58)
impact_fill = box(pos=vector(14.6, 8.55, -8.72), size=vector(0.1, 0.34, 0.16), color=vector(0.80, 0.45, 0.20), opacity=0.86)

legend_body = ellipsoid(pos=vector(-22.2, 7.35, -8.8), length=0.45, height=0.18, width=0.25, color=DINO_BODY)
legend_mud = ellipsoid(pos=vector(-22.2, 6.75, -8.8), length=0.45, height=0.05, width=0.25, color=WET_MUD)
legend_tree = cylinder(pos=vector(-22.2, 6.0, -8.8), axis=vector(0, 0.42, 0), radius=0.04, color=TREE_TRUNK)
label(pos=vector(-21.35, 7.35, -8.8), text="88-foot sauropod body", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-21.35, 6.75, -8.8), text="mud compression", height=10, color=TEXT, box=False, opacity=0)
label(pos=vector(-21.35, 6.05, -8.8), text="trees and banks reshaped", height=10, color=TEXT, box=False, opacity=0)

paused = False
camera_mode = 0
sim_time = 0.0


def reset_simulation():
    global sim_time
    sim_time = 0.0
    dino.pos = vector(-30, 0.2, 0.4)
    dino.phase = 0.0
    dino.walk_speed = 0.82
    for collection in [footprints, mud_ripples, river_slumps, splashes]:
        for item in collection:
            item.hide()
        collection.clear()
    for tr in trees:
        tr.lean = vector(0, 0, 0)
        tr.lean_vel = vector(0, 0, 0)
        tr.fallen = False
        tr.fall_angle = 0.0
        tr.trunk.axis = vector(0, tr.height, 0)
        tr.crown.pos = tr.base + vector(0, tr.height + 0.5, 0)
        tr.crown.height = tr.height * 0.62
        tr.shadow.opacity = 0.16


def on_keydown(evt):
    global paused, camera_mode, tree_recovery
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_simulation()
    elif key == "up":
        dino.walk_speed = clamp(dino.walk_speed + 0.10, 0.20, 2.20)
    elif key == "down":
        dino.walk_speed = clamp(dino.walk_speed - 0.10, 0.20, 2.20)
    elif key in ["t", "T"]:
        tree_recovery = not tree_recovery
    elif key in ["c", "C"]:
        camera_mode = (camera_mode + 1) % 3

scene.bind("keydown", on_keydown)

while True:
    rate(60)
    if paused:
        continue

    dt = 1.0 / 60.0
    sim_time += dt

    dino.update(dt, sim_time)
    dino.disturb_environment()

    for tr in trees:
        tr.update(dt, sim_time)

    live = []
    for fp in footprints:
        if fp.update(dt):
            live.append(fp)
        else:
            fp.hide()
    footprints[:] = live

    live = []
    for mr in mud_ripples:
        if mr.update(dt):
            live.append(mr)
        else:
            mr.hide()
    mud_ripples[:] = live

    live = []
    for rs in river_slumps:
        if rs.update(dt):
            live.append(rs)
        else:
            rs.hide()
    river_slumps[:] = live

    live = []
    for sp in splashes:
        if sp.update(dt):
            live.append(sp)
        else:
            sp.hide()
    splashes[:] = live

    river.opacity = 0.66 + 0.08 * math.sin(sim_time * 1.7)
    wave_pts = []
    for i in range(28):
        u = i / 27
        x = -38 + u * 76
        y = -2.05 + 0.03 * math.sin(sim_time * 2.2 + u * 10)
        z = -7.0 + 0.12 * math.sin(sim_time * 1.4 + u * 16)
        wave_pts.append(vector(x, y, z))
    reset_curve(river_highlight, wave_pts)

    for i, p in enumerate(puddles):
        d = abs(p.pos.x - dino.pos.x) + abs(p.pos.z - dino.pos.z) * 0.3
        shake = clamp(1.0 - d / 10.0, 0, 1)
        p.height = 0.025 + 0.035 * shake * (0.5 + 0.5 * math.sin(sim_time * 10 + i))
        p.opacity = 0.28 + 0.24 * shake

    step_impact = clamp(dino.walk_speed / 2.2 + len(mud_ripples) * 0.03, 0, 1)
    impact_fill.size.x = 6.8 * step_impact
    impact_fill.pos.x = 14.65 + impact_fill.size.x / 2.0

    fallen_count = sum(1 for tr in trees if tr.fallen)
    status_label.text = "ancient Southeast Asian floodplain\nnewly discovered giant sauropod\neach step changes the ground"
    impact_label.text = f"walking speed: {dino.walk_speed:.2f}\nfresh footprints: {len(footprints)}\nfallen trees: {fallen_count}"

    if camera_mode == 0:
        scene.center = dino.pos + vector(0, 0.6, 0)
        scene.forward = vector(-0.54, -0.28, -0.79)
        scene.range = 26
    elif camera_mode == 1:
        scene.center = dino.pos + vector(1.6, 1.0, 0)
        scene.forward = vector(-0.22, -0.10, -0.97)
        scene.range = 12
    else:
        scene.center = vector(dino.pos.x, -1.0, 0)
        scene.forward = vector(-0.05, -0.92, -0.38)
        scene.range = 25
