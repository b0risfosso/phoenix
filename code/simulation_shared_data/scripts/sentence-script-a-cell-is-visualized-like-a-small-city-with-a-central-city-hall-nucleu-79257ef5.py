from vpython import *
import random
import math
from collections import deque

# ============================================================
# Cell as a City: Metaphorical Traffic Map
# VPython 3D simulation with expressive AI controller
# ============================================================

# -----------------------------
# Scene setup
# -----------------------------
scene.title = "Cell as a City: Metaphorical Traffic Map"
scene.width = 1200
scene.height = 760
scene.background = vector(0.94, 0.98, 1.0)
scene.forward = vector(-0.55, -0.45, -0.7)
scene.up = vector(0, 0, 1)
scene.range = 9.5
scene.autoscale = False

distant_light(direction=vector(-1, -1, -1), color=color.white)
local_light(pos=vector(0, 0, 6), color=vector(0.9, 0.95, 1.0))

# -----------------------------
# Global simulation parameters
# -----------------------------
DT = 1.0 / 60.0
CELL_RADIUS = 7.5
sim_time = 0.0
paused = False
activity_score = 0
selected_index = 0

vesicles = []
tracks = []
stations = []
mitochondria = []
particles = []
wraps = []
marks = []

# -----------------------------
# Utility functions
# -----------------------------
def clamp(x, a, b):
    return max(a, min(b, x))

def rand_vec_xy(radius_min=0.0, radius_max=1.0, z=0.0):
    r = random.uniform(radius_min, radius_max)
    a = random.uniform(0, 2 * math.pi)
    return vector(r * math.cos(a), r * math.sin(a), z)

def random_bright_color():
    return color.hsv_to_rgb(vector(random.random(), random.uniform(0.45, 0.8), random.uniform(0.75, 1.0)))

def mix_colors(c1, c2, blend=0.5):
    return c1 * (1 - blend) + c2 * blend

def safe_norm(v):
    if mag(v) < 1e-7:
        return vector(1, 0, 0)
    return norm(v)

def distance_xy(a, b):
    return mag(vector(a.x - b.x, a.y - b.y, 0))

def add_activity(amount=1):
    global activity_score
    activity_score += amount

# -----------------------------
# Background cell city
# -----------------------------
cell_membrane = sphere(
    pos=vector(0, 0, 0),
    radius=CELL_RADIUS,
    color=vector(0.45, 0.85, 1.0),
    opacity=0.10,
    shininess=0.2
)
cell_membrane_label = label(
    pos=vector(0, -CELL_RADIUS - 0.5, 1.2),
    text="transparent cell membrane / city boundary",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.2, 0.45, 0.55)
)

# City hall nucleus
nucleus = sphere(
    pos=vector(0, 0, 0.15),
    radius=1.35,
    color=vector(0.48, 0.62, 1.0),
    opacity=0.62,
    shininess=0.5
)
nucleus_core = sphere(
    pos=vector(0, 0, 0.25),
    radius=0.45,
    color=vector(0.18, 0.28, 0.72),
    opacity=0.8
)
nucleus_roof = cone(
    pos=vector(0, 0, 1.15),
    axis=vector(0, 0, 0.75),
    radius=0.95,
    color=vector(0.35, 0.48, 0.95),
    opacity=0.55
)
nucleus_label = label(
    pos=vector(0, 0, 2.35),
    text="CITY HALL\nNucleus",
    height=13,
    box=False,
    opacity=0,
    color=vector(0.1, 0.15, 0.45)
)

# Light city floor
floor_disk = cylinder(
    pos=vector(0, 0, -0.95),
    axis=vector(0, 0, 0.035),
    radius=CELL_RADIUS * 0.96,
    color=vector(0.9, 0.98, 0.94),
    opacity=0.22
)

# -----------------------------
# Data classes
# -----------------------------
class Track:
    def __init__(self, name, points, col, radius=0.035, is_loop=True):
        self.name = name
        self.points = points[:]
        self.color = col
        self.radius = radius
        self.is_loop = is_loop
        self.curve = curve(pos=self.points, color=self.color, radius=self.radius)
        self.seg_lengths = []
        self.total_length = 0.0
        for i in range(len(self.points) - 1):
            L = mag(self.points[i + 1] - self.points[i])
            self.seg_lengths.append(L)
            self.total_length += L
        if self.total_length <= 0:
            self.total_length = 1.0
        self.label = None

    def point_at(self, t):
        if self.is_loop:
            t = t % 1.0
        else:
            t = clamp(t, 0.0, 1.0)

        target = t * self.total_length
        acc = 0.0
        for i, L in enumerate(self.seg_lengths):
            if acc + L >= target:
                f = 0 if L == 0 else (target - acc) / L
                return self.points[i] * (1 - f) + self.points[i + 1] * f
            acc += L
        return self.points[-1]

    def tangent_at(self, t):
        eps = 0.002
        p1 = self.point_at(t)
        p2 = self.point_at(t + eps)
        return safe_norm(p2 - p1)

    def nearest_t(self, p, samples=150):
        best_t = 0.0
        best_d = 1e9
        for i in range(samples):
            t = i / float(samples)
            d = mag(self.point_at(t) - p)
            if d < best_d:
                best_d = d
                best_t = t
        return best_t

class Station:
    def __init__(self, name, kind, track, t, col, cargo=4, capacity=10):
        self.name = name
        self.kind = kind
        self.track = track
        self.t = t
        self.pos = track.point_at(t)
        self.color = col
        self.cargo = cargo
        self.capacity = capacity
        self.cooldown = 0.0

        self.base = cylinder(
            pos=self.pos + vector(0, 0, -0.22),
            axis=vector(0, 0, 0.42),
            radius=0.38,
            color=self.color,
            opacity=0.82
        )
        self.sign = box(
            pos=self.pos + vector(0, 0, 0.32),
            size=vector(0.78, 0.10, 0.28),
            color=self.color * 0.85 + vector(0.15, 0.15, 0.15)
        )
        self.marker = sphere(
            pos=self.pos + vector(0, 0, 0.62),
            radius=0.17,
            color=color.white,
            emissive=True,
            opacity=0.92
        )
        self.label = label(
            pos=self.pos + vector(0, 0, 0.95),
            text=f"{self.name}\n{self.kind}",
            height=10,
            box=False,
            opacity=0,
            color=vector(0.2, 0.25, 0.3)
        )

    def update(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        pulse = 0.5 + 0.5 * math.sin(sim_time * 2.0 + self.t * 20)
        self.marker.radius = 0.12 + 0.08 * pulse
        fullness = self.cargo / max(1, self.capacity)
        self.base.opacity = 0.45 + 0.45 * fullness
        self.sign.size = vector(0.55 + 0.5 * fullness, 0.10, 0.28)

class Particle:
    def __init__(self, pos, vel, col, life=4.0, radius=0.065, kind="cargo"):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.life = life
        self.max_life = life
        self.kind = kind
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=col,
            opacity=0.75,
            emissive=(kind == "spark")
        )

    def update(self, dt):
        self.life -= dt
        self.vel += vector(0, 0, -0.03) * dt
        self.vel *= 0.992
        self.pos += self.vel * dt
        if mag(self.pos) > CELL_RADIUS * 0.98:
            self.vel = -0.65 * self.vel
            self.pos = safe_norm(self.pos) * CELL_RADIUS * 0.94
        self.obj.pos = self.pos
        self.obj.opacity = max(0.0, 0.75 * self.life / self.max_life)
        if self.kind == "cargo":
            self.obj.radius = 0.045 + 0.02 * math.sin(sim_time * 7 + self.pos.x)
        return self.life > 0

class Mark:
    def __init__(self, pos, col, life=3.5, radius=0.75, text=""):
        self.life = life
        self.max_life = life
        self.obj = sphere(pos=pos, radius=radius, color=col, opacity=0.22)
        self.text = None
        if text:
            self.text = label(
                pos=pos + vector(0, 0, radius + 0.25),
                text=text,
                height=10,
                color=col,
                box=False,
                opacity=0
            )

    def update(self, dt):
        self.life -= dt
        f = max(0.0, self.life / self.max_life)
        self.obj.opacity = 0.22 * f
        self.obj.radius *= 1.0025
        if self.text:
            self.text.opacity = 0
            self.text.pos = self.obj.pos + vector(0, 0, self.obj.radius + 0.18)
        return self.life > 0

    def hide(self):
        self.obj.visible = False
        if self.text:
            self.text.visible = False

class Wrap:
    def __init__(self, center, radius, height, col, turns=2.5, life=8.0, name="wrap"):
        self.life = life
        self.max_life = life
        self.name = name
        pts = []
        n = 120
        for i in range(n):
            u = i / (n - 1)
            a = turns * 2 * math.pi * u
            z = -height / 2 + height * u
            pts.append(center + vector(radius * math.cos(a), radius * math.sin(a), z))
        self.obj = curve(pos=pts, color=col, radius=0.028)

    def update(self, dt):
        self.life -= dt
        f = max(0.0, self.life / self.max_life)
        self.obj.radius = 0.012 + 0.025 * f
        return self.life > 0

    def hide(self):
        self.obj.visible = False

class Mitochondrion:
    def __init__(self, pos, name):
        self.pos = pos
        self.name = name
        self.phase = random.random() * 10
        self.body = sphere(
            pos=pos,
            size=vector(1.15, 0.58, 0.58),
            color=vector(1.0, 0.63, 0.18),
            opacity=0.84,
            shininess=0.6
        )
        self.inner = []
        for k in range(3):
            stripe = sphere(
                pos=pos + vector(-0.32 + k * 0.32, 0, 0.02),
                size=vector(0.08, 0.52, 0.35),
                color=vector(1.0, 0.88, 0.32),
                opacity=0.65
            )
            self.inner.append(stripe)
        self.label = label(
            pos=pos + vector(0, 0, 0.7),
            text=f"{name}\nPower Plant",
            height=9,
            box=False,
            opacity=0,
            color=vector(0.45, 0.23, 0.0)
        )

    def update(self, dt):
        pulse = 0.5 + 0.5 * math.sin(sim_time * 3.2 + self.phase)
        self.body.opacity = 0.65 + 0.23 * pulse
        if random.random() < 0.015:
            vel = rand_vec_xy(0.15, 0.9, random.uniform(0.0, 0.6))
            particles.append(Particle(self.pos + rand_vec_xy(0, 0.35, 0.1), vel, vector(1.0, 0.82, 0.18), life=1.0, radius=0.035, kind="spark"))

class Vesicle:
    def __init__(self, name, track, t, col):
        self.name = name
        self.track = track
        self.t = t
        self.direction = random.choice([-1, 1])
        self.speed = random.uniform(0.75, 1.25)
        self.base_speed = self.speed
        self.color = col
        self.cargo_color = random_bright_color()
        self.cargo = random.randint(0, 3)
        self.capacity = 5
        self.stop_timer = random.uniform(0, 1)
        self.collision_cooldown = 0.0
        self.station_cooldown = 0.0
        self.ai_goal = "wander"
        self.target_station = None
        self.dip_timer = 0.0
        self.dip_phase = random.random() * math.pi * 2
        self.orbit_timer = 0.0
        self.orbit_radius = 3.0
        self.orbit_angle = random.random() * math.pi * 2
        self.orbit_speed = random.choice([-1, 1]) * random.uniform(0.4, 0.9)
        self.last_pos = self.track.point_at(self.t)
        self.pos = self.last_pos

        self.body = sphere(
            pos=self.pos,
            radius=0.26,
            color=self.color,
            opacity=0.95,
            shininess=0.7
        )
        self.nose = cone(
            pos=self.pos,
            axis=vector(0.42, 0, 0),
            radius=0.15,
            color=self.color * 0.85,
            opacity=0.92
        )
        self.cargo_obj = sphere(
            pos=self.pos + vector(0, 0, 0.32),
            radius=0.115,
            color=self.cargo_color,
            emissive=True,
            visible=(self.cargo > 0)
        )
        self.trail = curve(radius=0.018, color=self.color * 0.72 + vector(0.16, 0.16, 0.16))
        self.label = label(
            pos=self.pos + vector(0, 0, 0.55),
            text=self.name,
            height=8,
            box=False,
            opacity=0,
            color=vector(0.15, 0.15, 0.2)
        )

    def set_track(self, new_track):
        self.track = new_track
        self.t = new_track.nearest_t(self.pos)
        self.direction = random.choice([-1, 1])
        self.ai_goal = "rerouted"

    def attach_cargo(self, count=1, col=None):
        if self.cargo < self.capacity:
            self.cargo += count
            if col is not None:
                self.cargo_color = mix_colors(self.cargo_color, col, 0.35)
                self.cargo_obj.color = self.cargo_color
            add_activity(2)

    def detach_cargo(self, spill=True):
        if self.cargo <= 0:
            return
        self.cargo -= 1
        if spill:
            self.spill(count=3)
        add_activity(2)

    def spill(self, count=None):
        global particles
        if count is None:
            count = max(2, self.cargo + 1)
        for _ in range(count):
            vel = rand_vec_xy(0.4, 1.5, random.uniform(0.05, 0.65))
            particles.append(Particle(self.pos + rand_vec_xy(0, 0.18, 0.1), vel, self.cargo_color, life=random.uniform(2.4, 5.2), radius=0.055, kind="cargo"))
        add_activity(4)

    def mark(self, text="marked"):
        marks.append(Mark(self.pos, self.color, life=3.3, radius=0.55, text=text))
        add_activity(1)

    def wrap(self):
        wraps.append(Wrap(self.pos, 0.45, 0.9, self.color, turns=2.0, life=5.0, name=f"wrap {self.name}"))
        add_activity(1)

    def orbit_nucleus(self, duration=4.0, radius=None):
        self.orbit_timer = duration
        if radius is None:
            radius = clamp(distance_xy(self.pos, vector(0, 0, 0)), 2.2, 5.8)
        self.orbit_radius = radius
        self.orbit_angle = math.atan2(self.pos.y, self.pos.x)
        self.ai_goal = "orbit"

    def dip(self, duration=2.5):
        self.dip_timer = max(self.dip_timer, duration)
        self.ai_goal = "dip"

    def transfer_with_station(self, st):
        if st.cooldown > 0 or self.station_cooldown > 0:
            return

        changed = False

        if self.cargo > 0 and st.cargo < st.capacity:
            self.cargo -= 1
            st.cargo += 1
            changed = True
            particles.append(Particle(st.pos + vector(0, 0, 0.55), vector(0, 0, 0.4), self.cargo_color, life=0.9, radius=0.05, kind="spark"))

        elif self.cargo < self.capacity and st.cargo > 0:
            self.cargo += 1
            st.cargo -= 1
            self.cargo_color = mix_colors(self.cargo_color, st.color, 0.45)
            self.cargo_obj.color = self.cargo_color
            changed = True
            particles.append(Particle(self.pos + vector(0, 0, 0.35), vector(0, 0, 0.5), st.color, life=0.8, radius=0.05, kind="spark"))

        if changed:
            self.stop_timer = random.uniform(0.45, 1.25)
            st.cooldown = 0.7
            self.station_cooldown = 0.9
            self.mark("transfer")
            add_activity(5)

    def update(self, dt):
        self.collision_cooldown = max(0.0, self.collision_cooldown - dt)
        self.station_cooldown = max(0.0, self.station_cooldown - dt)

        if self.orbit_timer > 0:
            self.orbit_timer -= dt
            self.orbit_angle += self.orbit_speed * dt
            z = 0.28 + 0.25 * math.sin(sim_time * 2.1 + self.orbit_angle)
            self.pos = vector(self.orbit_radius * math.cos(self.orbit_angle), self.orbit_radius * math.sin(self.orbit_angle), z)
            if self.orbit_timer <= 0:
                self.t = self.track.nearest_t(self.pos)
        else:
            if self.stop_timer > 0:
                self.stop_timer -= dt
            else:
                self.t += self.direction * self.speed * dt / self.track.total_length
                if not self.track.is_loop:
                    if self.t <= 0 or self.t >= 1:
                        self.direction *= -1
                        self.t = clamp(self.t, 0.0, 1.0)
                p = self.track.point_at(self.t)
                if self.dip_timer > 0:
                    self.dip_timer -= dt
                    p.z += 0.25 * math.sin((self.dip_timer * 8.0) + self.dip_phase)
                self.pos = p

                for st in stations:
                    if st.track == self.track and abs(((self.t - st.t + 0.5) % 1.0) - 0.5) < 0.015:
                        self.transfer_with_station(st)

        heading = safe_norm(self.pos - self.last_pos)
        if mag(self.pos - self.last_pos) < 1e-5:
            heading = self.track.tangent_at(self.t) * self.direction

        self.body.pos = self.pos
        self.nose.axis = heading * 0.42
        self.nose.pos = self.pos + heading * 0.19
        self.cargo_obj.visible = self.cargo > 0
        self.cargo_obj.pos = self.pos + vector(0, 0, 0.34 + 0.025 * math.sin(sim_time * 7))
        self.cargo_obj.radius = 0.075 + 0.026 * min(self.cargo, self.capacity)
        self.label.pos = self.pos + vector(0, 0, 0.58)
        self.label.text = f"{self.name} {self.cargo}"

        if int(sim_time * 12) % 2 == 0:
            self.trail.append(pos=self.pos, retain=85)

        self.last_pos = vector(self.pos)

    def hide(self):
        self.body.visible = False
        self.nose.visible = False
        self.cargo_obj.visible = False
        self.trail.visible = False
        self.label.visible = False

# -----------------------------
# Build tracks
# -----------------------------
def make_circle_track(name, radius, z, col, wobble=0.0):
    pts = []
    n = 160
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        zz = z + wobble * math.sin(3 * a)
        pts.append(vector(radius * math.cos(a), radius * math.sin(a), zz))
    return Track(name, pts, col, radius=0.035, is_loop=True)

def make_radial_track(name, angle, col):
    pts = []
    n = 90
    for i in range(n + 1):
        u = i / n
        r = 1.75 + u * 5.35
        z = -0.55 + 0.12 * math.sin(u * math.pi * 2)
        pts.append(vector(r * math.cos(angle), r * math.sin(angle), z))
    return Track(name, pts, col, radius=0.032, is_loop=False)

tracks.append(make_circle_track("inner cytoskeletal loop", 2.45, -0.25, vector(0.36, 0.72, 0.94), wobble=0.05))
tracks.append(make_circle_track("midtown microtubule belt", 4.15, -0.42, vector(0.42, 0.82, 0.55), wobble=0.08))
tracks.append(make_circle_track("outer actin ring road", 6.05, -0.60, vector(0.92, 0.62, 0.28), wobble=0.06))

for k in range(6):
    tracks.append(make_radial_track(f"radial cargo avenue {k+1}", k * math.pi / 3 + math.pi / 12, vector(0.76, 0.70, 0.95)))

for tr in tracks:
    tr.label = label(
        pos=tr.point_at(0.11) + vector(0, 0, 0.18),
        text=tr.name,
        height=7,
        box=False,
        opacity=0,
        color=tr.color * 0.55
    )

# -----------------------------
# Stations
# -----------------------------
station_specs = [
    ("Golgi Hub", "sorting station", tracks[1], 0.08, vector(1.0, 0.72, 0.25), 7),
    ("ER Depot", "factory district", tracks[0], 0.31, vector(0.55, 0.78, 1.0), 8),
    ("Membrane Dock", "export gate", tracks[2], 0.18, vector(0.25, 0.86, 0.95), 2),
    ("Ribosome Row", "build site", tracks[1], 0.57, vector(0.78, 0.58, 1.0), 5),
    ("Lysosome Yard", "recycling", tracks[2], 0.68, vector(0.92, 0.42, 0.48), 3),
    ("Signal Plaza", "message stop", tracks[0], 0.77, vector(0.52, 0.95, 0.58), 6),
]

for spec in station_specs:
    stations.append(Station(*spec))

# Add tiny station roads from station to nucleus as visual footpaths
for st in stations:
    curve(
        pos=[st.pos, st.pos * 0.42 + vector(0, 0, -0.25)],
        radius=0.012,
        color=vector(0.72, 0.75, 0.76)
    )

# -----------------------------
# Mitochondria / power plants
# -----------------------------
mito_positions = [
    vector(-4.9, 2.15, -0.15),
    vector(4.9, -2.35, -0.10),
    vector(-2.8, -4.75, -0.20),
    vector(3.2, 4.35, -0.15)
]
for i, p in enumerate(mito_positions):
    mitochondria.append(Mitochondrion(p, f"Mito {i+1}"))

# -----------------------------
# Vesicles / vehicles
# -----------------------------
vehicle_colors = [
    vector(0.95, 0.34, 0.34),
    vector(0.32, 0.63, 1.0),
    vector(0.35, 0.85, 0.50),
    vector(1.0, 0.78, 0.22),
    vector(0.75, 0.50, 1.0),
    vector(1.0, 0.50, 0.78),
    vector(0.28, 0.86, 0.88),
    vector(0.95, 0.58, 0.25),
    vector(0.58, 0.88, 0.38),
    vector(0.56, 0.58, 1.0)
]

for i in range(10):
    tr = random.choice(tracks[:3])
    vesicles.append(Vesicle(f"V{i+1}", tr, random.random(), vehicle_colors[i % len(vehicle_colors)]))

# -----------------------------
# Interactions
# -----------------------------
def handle_collisions():
    for i in range(len(vesicles)):
        for j in range(i + 1, len(vesicles)):
            a = vesicles[i]
            b = vesicles[j]
            if a.collision_cooldown > 0 or b.collision_cooldown > 0:
                continue
            d = mag(a.pos - b.pos)
            if d < 0.50:
                a.collision_cooldown = 1.1
                b.collision_cooldown = 1.1

                # Bounce
                a.direction *= -1
                b.direction *= -1
                a.stop_timer = random.uniform(0.12, 0.35)
                b.stop_timer = random.uniform(0.12, 0.35)

                # Mix visual identity and cargo colors
                mixed = mix_colors(a.color, b.color, 0.5)
                a.color = mix_colors(a.color, mixed, 0.35)
                b.color = mix_colors(b.color, mixed, 0.35)
                a.body.color = a.color
                b.body.color = b.color
                a.nose.color = a.color * 0.85
                b.nose.color = b.color * 0.85

                c_mix = mix_colors(a.cargo_color, b.cargo_color, 0.5)
                a.cargo_color = mix_colors(a.cargo_color, c_mix, 0.5)
                b.cargo_color = mix_colors(b.cargo_color, c_mix, 0.5)
                a.cargo_obj.color = a.cargo_color
                b.cargo_obj.color = b.cargo_color

                # Transfer or spill cargo
                if a.cargo > 0 and b.cargo < b.capacity and random.random() < 0.55:
                    a.cargo -= 1
                    b.cargo += 1
                elif b.cargo > 0 and a.cargo < a.capacity and random.random() < 0.55:
                    b.cargo -= 1
                    a.cargo += 1
                else:
                    if a.cargo > 0 and random.random() < 0.5:
                        a.detach_cargo(spill=True)
                    if b.cargo > 0 and random.random() < 0.5:
                        b.detach_cargo(spill=True)

                # Reroute sometimes
                if random.random() < 0.5:
                    a.set_track(random.choice(tracks))
                if random.random() < 0.5:
                    b.set_track(random.choice(tracks))

                marks.append(Mark((a.pos + b.pos) / 2, vector(1.0, 0.35, 0.25), life=2.0, radius=0.42, text="collision"))
                add_activity(8)

def gather_spilled_cargo():
    # Vesicles can collect nearby cargo particles.
    for v in vesicles:
        if v.cargo >= v.capacity:
            continue
        for p in particles:
            if p.kind != "cargo":
                continue
            if p.life <= 0:
                continue
            if mag(v.pos - p.pos) < 0.32:
                p.life = 0
                v.attach_cargo(1, p.obj.color)
                v.mark("picked up")
                break

# -----------------------------
# AI Controller
# -----------------------------
class ExpressiveAIController:
    def __init__(self):
        self.enabled = True
        self.mode = "traffic"
        self.modes = [
            "traffic",
            "careful",
            "curious",
            "constructive",
            "chaotic",
            "ritual",
            "artistic",
            "cleanup"
        ]
        self.mode_timer = 0.0
        self.mode_duration = 8.0
        self.override_until = 0.0
        self.last_activity_score = 0
        self.stagnation_timer = 0.0
        self.completion_timer = 0.0
        self.round_number = 1
        self.reset_pending_timer = -1.0
        self.last_signature = None
        self.signature_timer = 0.0
        self.last_positions = deque(maxlen=120)
        self.next_minor_action = 0.0

        self.status = label(
            pos=vector(-7.4, 7.0, 2.3),
            text="",
            height=12,
            box=False,
            opacity=0,
            color=vector(0.12, 0.25, 0.38)
        )

    def read_state(self):
        total_vehicle_cargo = sum(v.cargo for v in vesicles)
        total_station_cargo = sum(s.cargo for s in stations)
        total_spilled = sum(1 for p in particles if p.kind == "cargo" and p.life > 0)
        avg_speed = sum(v.speed for v in vesicles) / max(1, len(vesicles))
        closest_pair = 999
        for i in range(len(vesicles)):
            for j in range(i + 1, len(vesicles)):
                closest_pair = min(closest_pair, mag(vesicles[i].pos - vesicles[j].pos))
        station_fullness = [s.cargo / max(1, s.capacity) for s in stations]
        moving_amount = 0.0
        if len(self.last_positions) > 1:
            old = self.last_positions[0]
            new = [(round(v.pos.x, 2), round(v.pos.y, 2), round(v.pos.z, 2)) for v in vesicles]
            for a, b in zip(old, new):
                moving_amount += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])

        return {
            "total_vehicle_cargo": total_vehicle_cargo,
            "total_station_cargo": total_station_cargo,
            "total_spilled": total_spilled,
            "avg_speed": avg_speed,
            "closest_pair": closest_pair,
            "station_fullness": station_fullness,
            "activity_score": activity_score,
            "moving_amount": moving_amount,
            "round": self.round_number
        }

    def detect_stagnation_or_completion(self, state, dt):
        if activity_score == self.last_activity_score:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = 0.0
            self.last_activity_score = activity_score

        snapshot = tuple(
            (round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1), v.cargo, v.track.name)
            for v in vesicles
        ) + tuple((s.name, s.cargo) for s in stations)

        self.signature_timer += dt
        if self.signature_timer > 2.0:
            if snapshot == self.last_signature:
                self.stagnation_timer += 2.0
            self.last_signature = snapshot
            self.signature_timer = 0.0

        balanced = all(0.18 <= f <= 0.92 for f in state["station_fullness"])
        little_spill = state["total_spilled"] < 3
        low_motion = state["moving_amount"] < 0.06 and sim_time > 8

        if balanced and little_spill and state["total_vehicle_cargo"] < 8:
            self.completion_timer += dt
        elif low_motion:
            self.completion_timer += dt * 0.5
        else:
            self.completion_timer = max(0.0, self.completion_timer - dt * 0.8)

        stagnant = self.stagnation_timer > 13.0
        complete = self.completion_timer > 7.0
        empty = len(vesicles) == 0
        return stagnant or complete or empty

    def choose_mode(self, state):
        # Reactive state-machine transitions
        if state["total_spilled"] > 20:
            return "cleanup"
        if state["closest_pair"] < 0.72 and self.mode != "chaotic":
            return random.choice(["careful", "chaotic"])
        if state["total_vehicle_cargo"] == 0 and state["total_spilled"] < 3:
            return "constructive"
        if max(state["station_fullness"]) > 0.95:
            return "traffic"
        if self.mode_timer > self.mode_duration:
            choices = [m for m in self.modes if m != self.mode]
            return random.choice(choices)
        return self.mode

    def switch_mode(self, new_mode):
        if new_mode == self.mode:
            return
        self.mode = new_mode
        self.mode_timer = 0.0
        self.mode_duration = random.uniform(6.0, 13.0)
        col = {
            "traffic": vector(0.25, 0.6, 1.0),
            "careful": vector(0.35, 0.85, 0.65),
            "curious": vector(0.8, 0.55, 1.0),
            "constructive": vector(0.45, 0.9, 0.42),
            "chaotic": vector(1.0, 0.35, 0.22),
            "ritual": vector(0.45, 0.5, 1.0),
            "artistic": vector(1.0, 0.55, 0.85),
            "cleanup": vector(0.42, 0.85, 0.95)
        }.get(new_mode, color.white)
        marks.append(Mark(vector(0, 0, 1.25), col, life=2.4, radius=1.65, text=f"AI: {new_mode}"))
        add_activity(1)

    def run_traffic(self, state):
        # Balance cargo among stations and keep traffic flowing.
        fullest = max(stations, key=lambda s: s.cargo / s.capacity)
        emptiest = min(stations, key=lambda s: s.cargo / s.capacity)

        for v in vesicles:
            v.speed = 0.92 * v.speed + 0.08 * random.uniform(0.8, 1.35)
            if v.cargo == 0:
                v.target_station = fullest
            else:
                v.target_station = emptiest

            if v.target_station and v.track != v.target_station.track and random.random() < 0.012:
                v.set_track(v.target_station.track)

            if random.random() < 0.004:
                v.dip(1.5)

    def run_careful(self, state):
        # Slow down, increase spacing, avoid collisions.
        for v in vesicles:
            v.speed = 0.94 * v.speed + 0.06 * 0.65

        for i in range(len(vesicles)):
            for j in range(i + 1, len(vesicles)):
                a = vesicles[i]
                b = vesicles[j]
                if mag(a.pos - b.pos) < 0.85:
                    if random.random() < 0.55:
                        b.set_track(random.choice(tracks))
                    else:
                        b.direction *= -1
                    b.mark("yield")
                    add_activity(1)

        if random.random() < 0.02:
            random.choice(vesicles).mark("inspection")

    def run_curious(self, state):
        # Explore mitochondria, dip, orbit, and inspect stations.
        if sim_time > self.next_minor_action:
            v = random.choice(vesicles)
            target = random.choice(mitochondria).pos
            closest_track = min(tracks, key=lambda tr: mag(tr.point_at(tr.nearest_t(target)) - target))
            v.set_track(closest_track)
            v.dip(random.uniform(1.5, 3.5))
            if random.random() < 0.35:
                v.orbit_nucleus(duration=random.uniform(2.0, 4.0), radius=random.uniform(2.2, 5.7))
            v.mark("curious")
            self.next_minor_action = sim_time + random.uniform(1.0, 2.5)

    def run_constructive(self, state):
        # Gather spilled cargo and deliver it to the emptiest station.
        emptiest = min(stations, key=lambda s: s.cargo / s.capacity)
        for v in vesicles:
            v.speed = 0.93 * v.speed + 0.07 * 1.05
            if v.cargo == 0 and state["total_spilled"] > 0:
                if random.random() < 0.02:
                    v.mark("search")
            else:
                if v.track != emptiest.track and random.random() < 0.025:
                    v.set_track(emptiest.track)

        if sim_time > self.next_minor_action:
            wraps.append(Wrap(nucleus.pos, 1.55, 2.3, vector(0.52, 0.9, 0.62), turns=2.0, life=4.0, name="repair spiral"))
            self.next_minor_action = sim_time + random.uniform(3.0, 5.0)

    def run_chaotic(self, state):
        # Increase speed, cause reroutes, collisions, spills, bounces.
        for v in vesicles:
            v.speed = 0.92 * v.speed + 0.08 * random.uniform(1.35, 2.4)
            if random.random() < 0.012:
                v.direction *= -1
            if random.random() < 0.012:
                v.set_track(random.choice(tracks))
            if random.random() < 0.006 and v.cargo > 0:
                v.detach_cargo(spill=True)

        if sim_time > self.next_minor_action:
            v = random.choice(vesicles)
            v.wrap()
            v.mark("swerve")
            self.next_minor_action = sim_time + random.uniform(0.6, 1.3)

    def run_ritual(self, state):
        # Orderly orbit around the nucleus, visible spiral wrapping.
        for idx, v in enumerate(vesicles):
            v.speed = 0.9
            if v.orbit_timer <= 0 and random.random() < 0.04:
                v.orbit_nucleus(duration=random.uniform(3.0, 6.5), radius=2.2 + (idx % 5) * 0.65)

        if sim_time > self.next_minor_action:
            wraps.append(Wrap(nucleus.pos, random.uniform(1.65, 2.05), 2.6, random_bright_color(), turns=random.uniform(2.5, 4.2), life=6.5, name="nucleus ritual wrap"))
            self.next_minor_action = sim_time + random.uniform(2.2, 3.8)

    def run_artistic(self, state):
        # Paint with trails, marks, and color mixing.
        for v in vesicles:
            v.speed = 0.96 * v.speed + 0.04 * random.uniform(0.7, 1.75)
            if random.random() < 0.008:
                v.color = mix_colors(v.color, random_bright_color(), 0.16)
                v.body.color = v.color
                v.nose.color = v.color * 0.85
                v.trail.color = v.color * 0.72 + vector(0.16, 0.16, 0.16)
            if random.random() < 0.006:
                v.mark("paint")

        if sim_time > self.next_minor_action:
            center = rand_vec_xy(1.8, 5.7, random.uniform(-0.3, 0.45))
            wraps.append(Wrap(center, random.uniform(0.25, 0.75), random.uniform(0.5, 1.4), random_bright_color(), turns=random.uniform(1.2, 3.2), life=random.uniform(3.5, 7.0), name="art spiral"))
            self.next_minor_action = sim_time + random.uniform(0.8, 1.8)

    def run_cleanup(self, state):
        # Collect spills, slow scene, stabilize traffic.
        for v in vesicles:
            v.speed = 0.93 * v.speed + 0.07 * 0.82
            if state["total_spilled"] > 0:
                v.ai_goal = "cleanup"
            if random.random() < 0.006:
                v.mark("clean")

        # Expire oldest cargo particles gently if scene is crowded.
        cargo_particles = [p for p in particles if p.kind == "cargo" and p.life > 0]
        if len(cargo_particles) > 12:
            for p in cargo_particles[:3]:
                p.life *= 0.8

        if state["total_spilled"] < 4 and self.mode_timer > 3:
            self.switch_mode("traffic")

    def request_reset_loop(self):
        if self.reset_pending_timer < 0:
            self.reset_pending_timer = 3.0
            marks.append(Mark(vector(0, 0, 1.1), vector(0.25, 0.7, 1.0), life=3.0, radius=2.0, text="round complete\nreset soon"))

    def update(self, dt):
        if not self.enabled:
            self.status.text = "AI OFF | keys: A toggle AI, Space pause, R reset, T/C/O modes"
            return

        if sim_time < self.override_until:
            self.status.text = f"AI OVERRIDDEN by human ({self.override_until - sim_time:0.1f}s)"
            return

        self.mode_timer += dt
        state = self.read_state()

        current_positions = [(round(v.pos.x, 2), round(v.pos.y, 2), round(v.pos.z, 2)) for v in vesicles]
        self.last_positions.append(current_positions)

        if self.detect_stagnation_or_completion(state, dt):
            self.request_reset_loop()

        if self.reset_pending_timer >= 0:
            self.reset_pending_timer -= dt
            if self.reset_pending_timer <= 0:
                reset_simulation(ai_round=True)
                return

        desired = self.choose_mode(state)
        self.switch_mode(desired)

        if self.mode == "traffic":
            self.run_traffic(state)
        elif self.mode == "careful":
            self.run_careful(state)
        elif self.mode == "curious":
            self.run_curious(state)
        elif self.mode == "constructive":
            self.run_constructive(state)
        elif self.mode == "chaotic":
            self.run_chaotic(state)
        elif self.mode == "ritual":
            self.run_ritual(state)
        elif self.mode == "artistic":
            self.run_artistic(state)
        elif self.mode == "cleanup":
            self.run_cleanup(state)

        self.status.text = (
            f"AI ON | mode: {self.mode} | round {self.round_number}\n"
            f"cargo vehicles:{state['total_vehicle_cargo']} stations:{state['total_station_cargo']} "
            f"spilled:{state['total_spilled']} | selected: {vesicles[selected_index].name}"
        )

ai = ExpressiveAIController()

# -----------------------------
# Reset / loop system
# -----------------------------
def reset_simulation(ai_round=False):
    global activity_score, selected_index

    for p in particles:
        p.obj.visible = False
    particles.clear()

    for w in wraps:
        w.hide()
    wraps.clear()

    for m in marks:
        m.hide()
    marks.clear()

    for st in stations:
        st.cargo = random.randint(2, 8)
        st.cooldown = 0

    for i, v in enumerate(vesicles):
        v.track = random.choice(tracks[:3])
        v.t = random.random()
        v.direction = random.choice([-1, 1])
        v.speed = random.uniform(0.75, 1.35)
        v.base_speed = v.speed
        v.cargo = random.randint(0, 3)
        v.cargo_color = random_bright_color()
        v.cargo_obj.color = v.cargo_color
        v.stop_timer = random.uniform(0, 1.0)
        v.collision_cooldown = 0
        v.station_cooldown = 0
        v.orbit_timer = 0
        v.dip_timer = 0
        v.pos = v.track.point_at(v.t)
        v.last_pos = vector(v.pos)
        try:
            v.trail.clear()
        except Exception:
            v.trail.visible = False
            v.trail = curve(radius=0.018, color=v.color * 0.72 + vector(0.16, 0.16, 0.16))

    selected_index = 0
    activity_score += 10

    ai.stagnation_timer = 0
    ai.completion_timer = 0
    ai.reset_pending_timer = -1
    ai.mode_timer = 0
    ai.last_signature = None
    ai.last_activity_score = activity_score
    ai.round_number += 1 if ai_round else 0
    ai.switch_mode(random.choice(["traffic", "curious", "constructive", "artistic"]))

    marks.append(Mark(vector(0, 0, 1.4), vector(0.25, 0.75, 1.0), life=3.0, radius=2.1, text=f"new round {ai.round_number}"))

# -----------------------------
# Human controls
# -----------------------------
help_label = label(
    pos=vector(-7.5, -7.2, 2.2),
    text=(
        "Controls: Space pause | A AI on/off | R reset | N select vehicle\n"
        "T traffic AI | C chaos AI | O ritual orbit | P artistic | D detach/spill | W wrap | M mark\n"
        "Up/Down speed selected | Left/Right reverse/reroute | H human override"
    ),
    height=10,
    box=False,
    opacity=0,
    color=vector(0.18, 0.25, 0.32)
)

def select_vehicle_visual():
    for i, v in enumerate(vesicles):
        v.body.opacity = 1.0 if i == selected_index else 0.86
        v.body.radius = 0.31 if i == selected_index else 0.26

def human_override(seconds=5.0):
    ai.override_until = max(ai.override_until, sim_time + seconds)

def keydown(evt):
    global paused, selected_index

    k = evt.key.lower()

    if k == " ":
        paused = not paused
    elif k == "a":
        ai.enabled = not ai.enabled
    elif k == "r":
        reset_simulation(ai_round=False)
    elif k == "n":
        selected_index = (selected_index + 1) % len(vesicles)
        select_vehicle_visual()
    elif k == "t":
        ai.enabled = True
        ai.switch_mode("traffic")
    elif k == "c":
        ai.enabled = True
        ai.switch_mode("chaotic")
    elif k == "o":
        ai.enabled = True
        ai.switch_mode("ritual")
        for idx, v in enumerate(vesicles):
            v.orbit_nucleus(duration=4.5, radius=2.2 + (idx % 5) * 0.65)
    elif k == "p":
        ai.enabled = True
        ai.switch_mode("artistic")
    elif k == "h":
        human_override(7.0)
    elif k == "d":
        human_override()
        vesicles[selected_index].detach_cargo(spill=True)
    elif k == "w":
        human_override()
        vesicles[selected_index].wrap()
    elif k == "m":
        human_override()
        vesicles[selected_index].mark("human mark")
    elif k == "up":
        human_override()
        vesicles[selected_index].speed = clamp(vesicles[selected_index].speed + 0.25, 0.15, 3.0)
    elif k == "down":
        human_override()
        vesicles[selected_index].speed = clamp(vesicles[selected_index].speed - 0.25, 0.15, 3.0)
    elif k == "left":
        human_override()
        vesicles[selected_index].direction *= -1
        vesicles[selected_index].mark("reverse")
    elif k == "right":
        human_override()
        vesicles[selected_index].set_track(random.choice(tracks))
        vesicles[selected_index].mark("reroute")

scene.bind("keydown", keydown)
select_vehicle_visual()

# -----------------------------
# Main loop
# -----------------------------
while True:
    rate(60)

    if paused:
        ai.status.text = "PAUSED | Space resumes"
        continue

    sim_time += DT

    # Update stationary-but-alive systems
    for st in stations:
        st.update(DT)

    for mto in mitochondria:
        mto.update(DT)

    # Update AI before vehicles, so actions affect this frame
    ai.update(DT)

    # Update vehicles and interactions
    for v in vesicles:
        v.update(DT)

    handle_collisions()
    gather_spilled_cargo()

    # Update particles
    alive_particles = []
    for p in particles:
        if p.update(DT):
            alive_particles.append(p)
        else:
            p.obj.visible = False
    particles[:] = alive_particles

    # Update wraps
    alive_wraps = []
    for w in wraps:
        if w.update(DT):
            alive_wraps.append(w)
        else:
            w.hide()
    wraps[:] = alive_wraps

    # Update marks
    alive_marks = []
    for m in marks:
        if m.update(DT):
            alive_marks.append(m)
        else:
            m.hide()
    marks[:] = alive_marks

    # Light automatic city shimmer
    nucleus.opacity = 0.55 + 0.08 * math.sin(sim_time * 1.8)
    nucleus_core.radius = 0.43 + 0.035 * math.sin(sim_time * 2.7)

    # Keep selected vehicle visually highlighted
    if int(sim_time * 3) % 2 == 0:
        select_vehicle_visual()
