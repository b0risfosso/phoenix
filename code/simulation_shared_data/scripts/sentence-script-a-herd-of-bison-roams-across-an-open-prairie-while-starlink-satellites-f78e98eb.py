from vpython import *
import math
import random

# ------------------------------------------------------------
# Bison Starlink Prairie
# A herd of bison roams across an open prairie while satellites
# pass overhead, sending broadband beams down to a remote station.
# ------------------------------------------------------------

scene = canvas(
    title="Bison Starlink Prairie — Broadband on the Open Range",
    width=1200,
    height=760,
    background=vector(0.78, 0.90, 1.0),
    center=vector(0, 2, 0),
)
scene.forward = vector(-0.35, -0.28, -0.88)
scene.range = 38

random.seed(8)

# -----------------------------
# Utility helpers
# -----------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, u):
    return a + (b - a) * u


def soft_color(c1, c2, u):
    return vector(lerp(c1.x, c2.x, u), lerp(c1.y, c2.y, u), lerp(c1.z, c2.z, u))


# -----------------------------
# Environment
# -----------------------------
prairie = box(
    pos=vector(0, -0.08, 0),
    size=vector(86, 0.12, 64),
    color=vector(0.72, 0.86, 0.45),
)

# Soft rolling prairie bands
for i in range(14):
    z = -29 + i * 4.4
    band = box(
        pos=vector(0, 0.015 + 0.02 * math.sin(i), z),
        size=vector(88, 0.035, 1.35),
        color=vector(0.64 + 0.05 * (i % 2), 0.79, 0.39),
        opacity=0.55,
    )

# Horizon and distant hills
horizon = box(pos=vector(0, 2.1, -33), size=vector(90, 0.18, 0.55), color=vector(0.50, 0.70, 0.42), opacity=0.8)
for i in range(9):
    pyramid(
        pos=vector(-38 + i * 9.5, 0.0, -32.5 + 0.4 * math.sin(i)),
        size=vector(8.5, 2.4 + 0.5 * math.sin(i * 0.7), 2.4),
        color=vector(0.48, 0.68, 0.40),
        opacity=0.55,
    )

sun = sphere(pos=vector(-35, 27, -26), radius=2.0, color=vector(1.0, 0.88, 0.36), emissive=True)
sun_glow = sphere(pos=sun.pos, radius=3.2, color=vector(1.0, 0.90, 0.45), opacity=0.18, emissive=True)

# Prairie grass tufts
for i in range(90):
    x = random.uniform(-40, 40)
    z = random.uniform(-28, 28)
    h = random.uniform(0.25, 0.75)
    blade = cylinder(
        pos=vector(x, 0.02, z),
        axis=vector(random.uniform(-0.08, 0.08), h, random.uniform(-0.08, 0.08)),
        radius=0.025,
        color=vector(0.35 + random.random() * 0.14, 0.56 + random.random() * 0.18, 0.23),
        opacity=0.75,
    )

# -----------------------------
# Field station
# -----------------------------
station_base = box(pos=vector(20, 0.55, 9), size=vector(4.8, 1.1, 3.2), color=vector(0.86, 0.88, 0.82))
station_roof = pyramid(pos=vector(20, 1.35, 9), size=vector(5.2, 1.25, 3.6), color=vector(0.70, 0.22, 0.16))
door = box(pos=vector(20, 0.35, 7.37), size=vector(0.95, 0.85, 0.08), color=vector(0.34, 0.22, 0.14))
window1 = box(pos=vector(18.55, 0.75, 7.35), size=vector(0.85, 0.55, 0.07), color=vector(0.55, 0.80, 1.0), emissive=True, opacity=0.85)
window2 = box(pos=vector(21.45, 0.75, 7.35), size=vector(0.85, 0.55, 0.07), color=vector(0.55, 0.80, 1.0), emissive=True, opacity=0.85)

mast = cylinder(pos=vector(23.6, 0.0, 10.5), axis=vector(0, 5.2, 0), radius=0.08, color=vector(0.48, 0.48, 0.48))
dish_arm = cylinder(pos=vector(23.6, 4.75, 10.5), axis=vector(0.9, 0.55, -0.25), radius=0.05, color=vector(0.42, 0.42, 0.42))
dish = ellipsoid(pos=vector(24.55, 5.35, 10.22), length=1.4, height=0.22, width=1.0, color=vector(0.93, 0.94, 0.90), opacity=0.95)
dish_ring = ring(pos=dish.pos, axis=vector(0.55, 0.75, -0.2), radius=0.68, thickness=0.035, color=vector(0.55, 0.58, 0.60))

signal_bar_back = box(pos=vector(20, 3.3, 6.6), size=vector(5.2, 0.28, 0.18), color=vector(0.72, 0.72, 0.72), opacity=0.55)
signal_bar = box(pos=vector(17.4, 3.3, 6.48), size=vector(0.2, 0.32, 0.22), color=vector(0.15, 0.70, 0.95), emissive=True)

station_label = label(
    pos=vector(20, 4.3, 6.3),
    text="Remote Field Station\nSignal: searching",
    height=13,
    color=vector(0.10, 0.16, 0.18),
    box=False,
)

# -----------------------------
# Bison herd
# -----------------------------
class Bison:
    def __init__(self, idx, pos, scale=1.0):
        self.idx = idx
        self.base_scale = scale
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(random.uniform(0.18, 0.38), 0, random.uniform(-0.10, 0.10))
        self.phase = random.uniform(0, 2 * math.pi)
        self.wander = random.uniform(0.3, 0.8)
        self.body = ellipsoid(pos=self.pos + vector(0, 1.0 * scale, 0), length=2.2 * scale, height=1.2 * scale, width=1.05 * scale, color=vector(0.29, 0.17, 0.09))
        self.shoulder = ellipsoid(pos=self.pos + vector(-0.55 * scale, 1.35 * scale, 0), length=1.25 * scale, height=1.35 * scale, width=1.12 * scale, color=vector(0.22, 0.12, 0.07))
        self.head = ellipsoid(pos=self.pos + vector(1.35 * scale, 1.1 * scale, 0), length=0.82 * scale, height=0.68 * scale, width=0.70 * scale, color=vector(0.20, 0.11, 0.06))
        self.beard = cone(pos=self.pos + vector(1.62 * scale, 0.92 * scale, 0), axis=vector(0.15 * scale, -0.42 * scale, 0), radius=0.18 * scale, color=vector(0.10, 0.06, 0.035))
        self.horn_l = cone(pos=self.pos + vector(1.42 * scale, 1.36 * scale, 0.31 * scale), axis=vector(0.18 * scale, 0.11 * scale, 0.28 * scale), radius=0.07 * scale, color=vector(0.86, 0.78, 0.58))
        self.horn_r = cone(pos=self.pos + vector(1.42 * scale, 1.36 * scale, -0.31 * scale), axis=vector(0.18 * scale, 0.11 * scale, -0.28 * scale), radius=0.07 * scale, color=vector(0.86, 0.78, 0.58))
        self.legs = []
        for lx in [-0.75, -0.25, 0.35, 0.85]:
            for lz in [-0.32, 0.32]:
                if len(self.legs) < 4:
                    self.legs.append(cylinder(pos=self.pos + vector(lx * scale, 0.1, lz * scale), axis=vector(0, 0.75 * scale, 0), radius=0.08 * scale, color=vector(0.16, 0.09, 0.05)))

    def update(self, t, herd_center):
        # Gentle herd migration with individual wandering
        drift = vector(0.015, 0, 0.010 * math.sin(t * 0.12 + self.idx))
        cohesion = (herd_center - self.pos) * 0.006
        noise = vector(0.018 * math.sin(t * self.wander + self.phase), 0, 0.020 * math.cos(t * 0.73 + self.phase))
        self.vel += drift + cohesion + noise
        speed = mag(self.vel)
        if speed > 0.42:
            self.vel = norm(self.vel) * 0.42
        if speed < 0.12:
            self.vel += vector(0.03, 0, random.uniform(-0.02, 0.02))

        self.pos += self.vel * 0.12

        # Wrap herd gently across prairie
        if self.pos.x > 39:
            self.pos.x = -39
        if self.pos.z > 27:
            self.pos.z = -27
        if self.pos.z < -27:
            self.pos.z = 27

        s = self.base_scale
        bob = 0.05 * math.sin(t * 3.2 + self.phase)
        body_center = self.pos + vector(0, 1.0 * s + bob, 0)
        self.body.pos = body_center
        self.shoulder.pos = self.pos + vector(-0.55 * s, 1.35 * s + bob, 0)
        self.head.pos = self.pos + vector(1.35 * s, 1.1 * s + bob, 0)
        self.beard.pos = self.pos + vector(1.62 * s, 0.92 * s + bob, 0)
        self.horn_l.pos = self.pos + vector(1.42 * s, 1.36 * s + bob, 0.31 * s)
        self.horn_r.pos = self.pos + vector(1.42 * s, 1.36 * s + bob, -0.31 * s)
        for j, leg in enumerate(self.legs):
            lx = [-0.75, -0.25, 0.35, 0.85][j] * s
            lz = [-0.32, 0.32, -0.32, 0.32][j] * s
            stride = 0.09 * math.sin(t * 4.2 + self.phase + j * 1.7)
            leg.pos = self.pos + vector(lx + stride, 0.1, lz)
            leg.axis = vector(-stride * 0.7, 0.75 * s, 0)


bison = []
for i in range(13):
    x = random.uniform(-28, -7)
    z = random.uniform(-12, 17)
    bison.append(Bison(i, vector(x, 0, z), scale=random.uniform(0.72, 1.05)))

# -----------------------------
# Satellites and beams
# -----------------------------
class Satellite:
    def __init__(self, idx, phase, lane_z, altitude, speed):
        self.idx = idx
        self.phase = phase
        self.lane_z = lane_z
        self.altitude = altitude
        self.speed = speed
        self.body = box(pos=vector(0, altitude, lane_z), size=vector(1.1, 0.34, 0.52), color=vector(0.83, 0.86, 0.90), emissive=True)
        self.panel_l = box(pos=vector(0, altitude, lane_z), size=vector(1.5, 0.06, 0.65), color=vector(0.08, 0.18, 0.55), emissive=True)
        self.panel_r = box(pos=vector(0, altitude, lane_z), size=vector(1.5, 0.06, 0.65), color=vector(0.08, 0.18, 0.55), emissive=True)
        self.beam = cone(pos=vector(0, altitude - 0.15, lane_z), axis=vector(0, -1, 0), radius=0.2, color=vector(0.20, 0.70, 1.0), opacity=0.10)
        self.pulse = ring(pos=vector(24.55, 5.36, 10.22), axis=vector(0, 1, 0), radius=0.2, thickness=0.025, color=vector(0.1, 0.65, 1.0), emissive=True, opacity=0.0)
        self.active = False

    def update(self, t, station_pos):
        # Smooth overhead pass from west to east, slightly arcing across the scene.
        x = ((t * self.speed + self.phase) % 96) - 48
        z = self.lane_z + 2.8 * math.sin(t * 0.11 + self.phase * 0.07)
        y = self.altitude + 1.1 * math.sin(t * 0.16 + self.idx)
        sat_pos = vector(x, y, z)
        self.body.pos = sat_pos
        self.panel_l.pos = sat_pos + vector(-1.35, 0, 0)
        self.panel_r.pos = sat_pos + vector(1.35, 0, 0)
        self.panel_l.size = vector(1.55 + 0.20 * math.sin(t * 1.7 + self.idx), 0.06, 0.65)
        self.panel_r.size = vector(1.55 + 0.20 * math.sin(t * 1.7 + self.idx), 0.06, 0.65)

        target = station_pos + vector(0, 1.0, 0)
        dist_horizontal = mag(vector(sat_pos.x - target.x, 0, sat_pos.z - target.z))
        alignment = clamp(1 - dist_horizontal / 30.0, 0, 1)
        self.active = alignment > 0.18

        axis = target - sat_pos
        self.beam.pos = sat_pos + vector(0, -0.1, 0)
        self.beam.axis = axis
        self.beam.radius = 0.35 + 2.5 * alignment
        self.beam.opacity = 0.03 + 0.23 * alignment
        self.beam.color = soft_color(vector(0.5, 0.85, 1.0), vector(0.0, 0.42, 1.0), alignment)

        self.pulse.pos = target + vector(0, 0.1, 0)
        self.pulse.radius = 0.6 + 1.6 * ((t * 1.7 + self.idx * 0.2) % 1.0)
        self.pulse.opacity = alignment * (0.65 - 0.40 * ((t * 1.7 + self.idx * 0.2) % 1.0))
        return alignment


satellites = [
    Satellite(0, 0, -8, 21.0, 5.6),
    Satellite(1, 21, 3, 23.0, 5.0),
    Satellite(2, 43, 13, 20.5, 6.2),
    Satellite(3, 66, -18, 24.0, 5.3),
]

# Broadband packets travelling down best beam
packets = []
for i in range(16):
    packets.append(sphere(pos=vector(0, 20, 0), radius=0.11, color=vector(0.0, 0.55, 1.0), emissive=True, opacity=0.0))

# Station connection waves on ground
waves = []
for i in range(5):
    waves.append(ring(pos=vector(23.6, 0.05, 10.5), axis=vector(0, 1, 0), radius=1.0 + i * 1.7, thickness=0.035, color=vector(0.18, 0.55, 1.0), opacity=0.15, emissive=True))

# Signal path label
main_label = label(
    pos=vector(-12, 18, 20),
    text="Starlink-style satellite passes overhead\nBroadband beams lock onto the prairie station",
    height=14,
    color=vector(0.08, 0.12, 0.15),
    box=False,
)

# -----------------------------
# Main animation loop
# -----------------------------
t = 0.0
packet_phase = [random.random() for _ in packets]

while True:
    rate(60)
    t += 0.032

    # Bison herd movement
    center = vector(0, 0, 0)
    for b in bison:
        center += b.pos
    center = center / len(bison)
    for b in bison:
        b.update(t, center)

    # Satellite links
    station_target = vector(24.55, 5.35, 10.22)
    alignments = []
    for sat in satellites:
        alignments.append(sat.update(t, station_target))

    best_index = max(range(len(alignments)), key=lambda k: alignments[k])
    best_signal = alignments[best_index]
    best_sat = satellites[best_index]

    # Dish and ring point toward strongest pass by moving/pulsing visually
    dish.color = soft_color(vector(0.93, 0.94, 0.90), vector(0.55, 0.86, 1.0), best_signal)
    dish_ring.color = soft_color(vector(0.55, 0.58, 0.60), vector(0.05, 0.55, 1.0), best_signal)
    dish_ring.radius = 0.66 + 0.16 * best_signal * (0.5 + 0.5 * math.sin(t * 5.0))

    # Signal bar expands from left to right
    signal_strength = clamp(0.18 + 0.82 * best_signal, 0, 1)
    bar_width = 5.0 * signal_strength
    signal_bar.size = vector(bar_width, 0.32, 0.22)
    signal_bar.pos = vector(17.4 + bar_width / 2.0, 3.3, 6.48)
    signal_bar.color = soft_color(vector(0.95, 0.72, 0.18), vector(0.0, 0.55, 1.0), signal_strength)

    status = "locked" if best_signal > 0.62 else "handoff" if best_signal > 0.32 else "searching"
    station_label.text = "Remote Field Station\nSignal: %s  %d%%" % (status, int(signal_strength * 100))

    # Packets travel down the best beam when signal is active
    start = best_sat.body.pos
    end = station_target
    for i, p in enumerate(packets):
        phase = (packet_phase[i] + t * (0.22 + 0.22 * best_signal)) % 1.0
        p.pos = start * (1 - phase) + end * phase
        p.radius = 0.07 + 0.10 * best_signal
        p.opacity = 0.08 + 0.82 * best_signal
        p.color = soft_color(vector(0.65, 0.88, 1.0), vector(0.0, 0.45, 1.0), phase)

    # Ground waves show the connection spreading around station
    for i, w in enumerate(waves):
        phase = (t * 0.27 + i * 0.18) % 1.0
        w.radius = 1.0 + phase * 9.0
        w.opacity = best_signal * (0.30 * (1 - phase))
        w.thickness = 0.025 + 0.02 * best_signal

    # Subtle sun glow pulse
    sun_glow.radius = 3.1 + 0.16 * math.sin(t * 0.8)
