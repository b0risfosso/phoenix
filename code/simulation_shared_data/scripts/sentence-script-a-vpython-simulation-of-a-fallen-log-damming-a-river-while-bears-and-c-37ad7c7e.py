"""
Log Dam River Crossing
A VPython simulation of a fallen log damming a river while bears and cats walk
across it from one bank to the other.

Run with:
    python log_dam_river_bears_cats.py

Requires:
    pip install vpython
"""

from vpython import *
import random
import math

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Log Dam River Crossing",
    width=1200,
    height=720,
    background=vector(0.86, 0.93, 1.0),
    center=vector(0, 0.8, 0),
)
scene.forward = vector(-0.55, -0.28, -0.78)
scene.range = 13

# Light styling
sun = distant_light(direction=vector(-0.5, -1.0, -0.4), color=vector(1.0, 0.97, 0.88))
ambient = local_light(pos=vector(0, 8, 5), color=vector(0.35, 0.35, 0.35))

# -----------------------------
# Constants / colors
# -----------------------------
RIVER_LENGTH = 24.0
RIVER_WIDTH = 7.2
GROUND_Y = -0.15
WATER_Y = 0.02
LOG_Y = 0.55
LOG_RADIUS = 0.38
LOG_LENGTH = 9.3

bank_color = vector(0.55, 0.78, 0.43)
soil_color = vector(0.48, 0.36, 0.23)
water_color = vector(0.20, 0.58, 0.90)
foam_color = vector(0.96, 0.99, 1.0)
log_color = vector(0.52, 0.31, 0.16)
bark_dark = vector(0.30, 0.18, 0.09)

# -----------------------------
# Terrain: banks and river
# -----------------------------
left_bank = box(pos=vector(-6.6, GROUND_Y - 0.05, 0), size=vector(8.7, 0.28, RIVER_LENGTH), color=bank_color)
right_bank = box(pos=vector(6.6, GROUND_Y - 0.05, 0), size=vector(8.7, 0.28, RIVER_LENGTH), color=bank_color)
riverbed = box(pos=vector(0, GROUND_Y - 0.16, 0), size=vector(RIVER_WIDTH, 0.18, RIVER_LENGTH), color=vector(0.36, 0.30, 0.22))

# Main water split into upstream and downstream sheets so the log visibly dams the river.
upstream_water = box(
    pos=vector(0, WATER_Y + 0.10, -3.35),
    size=vector(RIVER_WIDTH - 0.25, 0.24, RIVER_LENGTH / 2 - 1.3),
    color=water_color,
    opacity=0.62,
)
downstream_water = box(
    pos=vector(0, WATER_Y - 0.04, 4.0),
    size=vector(RIVER_WIDTH - 0.25, 0.13, RIVER_LENGTH / 2 - 2.2),
    color=vector(0.13, 0.48, 0.78),
    opacity=0.55,
)

# Bank slopes / muddy edges
for x in [-3.95, 3.95]:
    box(pos=vector(x, -0.08, 0), size=vector(0.22, 0.08, RIVER_LENGTH), color=soil_color)
    for z in range(-10, 11, 2):
        sphere(pos=vector(x + random.uniform(-0.08, 0.08), -0.005, z + random.uniform(-0.35, 0.35)), radius=random.uniform(0.05, 0.11), color=soil_color)

# -----------------------------
# Fallen log dam / crossing
# -----------------------------
# Main log spans left-to-right across the river, blocking the current.
main_log = cylinder(
    pos=vector(-LOG_LENGTH / 2, LOG_Y, 0),
    axis=vector(LOG_LENGTH, 0.18, 0),
    radius=LOG_RADIUS,
    color=log_color,
)

# Dark end rings
cylinder(pos=vector(-LOG_LENGTH / 2 - 0.015, LOG_Y, 0), axis=vector(0.05, 0.001, 0), radius=LOG_RADIUS * 1.02, color=bark_dark)
cylinder(pos=vector(LOG_LENGTH / 2 - 0.035, LOG_Y + 0.18, 0), axis=vector(0.05, 0.001, 0), radius=LOG_RADIUS * 1.02, color=bark_dark)

# Bark strips along the top make the cylinder read as a log.
for i in range(12):
    zoff = random.uniform(-0.23, 0.23)
    yoff = random.uniform(0.18, 0.35)
    curve(
        pos=[
            vector(-4.1, LOG_Y + yoff, zoff),
            vector(-1.6, LOG_Y + yoff + random.uniform(-0.04, 0.04), zoff + random.uniform(-0.03, 0.03)),
            vector(1.3, LOG_Y + yoff + random.uniform(-0.05, 0.05), zoff + random.uniform(-0.03, 0.03)),
            vector(4.1, LOG_Y + yoff + random.uniform(-0.04, 0.04), zoff + random.uniform(-0.03, 0.03)),
        ],
        radius=0.022,
        color=bark_dark,
    )

# Branch stubs and lodged debris show that the log is damming the current.
for sx in [-2.7, -1.1, 1.4, 3.0]:
    angle = random.choice([-1, 1]) * random.uniform(0.5, 0.9)
    cylinder(
        pos=vector(sx, LOG_Y + 0.15, -0.05),
        axis=vector(0.15, 0.4, angle),
        radius=0.07,
        color=log_color,
    )

jam_debris = []
for i in range(18):
    x = random.uniform(-3.25, 3.25)
    z = random.uniform(-0.72, -0.28)
    twig = cylinder(
        pos=vector(x, 0.26 + random.uniform(-0.03, 0.05), z),
        axis=vector(random.uniform(-0.55, 0.55), random.uniform(-0.02, 0.04), random.uniform(-0.08, 0.17)),
        radius=random.uniform(0.018, 0.035),
        color=vector(0.36, 0.22, 0.11),
    )
    jam_debris.append(twig)

# Foam banked against the upstream side of the log.
foam_patches = []
for i in range(30):
    foam_patches.append(
        sphere(
            pos=vector(random.uniform(-3.45, 3.45), 0.24 + random.uniform(-0.02, 0.07), random.uniform(-0.95, -0.42)),
            radius=random.uniform(0.035, 0.09),
            color=foam_color,
            opacity=random.uniform(0.55, 0.9),
        )
    )

# Small spill streams where water leaks around/over the log.
spill_streams = []
for x in [-3.2, -1.1, 1.25, 3.25]:
    spill_streams.append(
        curve(
            pos=[vector(x, 0.31, -0.45), vector(x + 0.12, 0.19, 0.12), vector(x + 0.02, 0.10, 0.72)],
            radius=0.035,
            color=foam_color,
        )
    )

# -----------------------------
# Water motion particles
# -----------------------------
flow_particles = []
for i in range(70):
    z = random.uniform(-11.5, 11.0)
    x = random.uniform(-3.15, 3.15)
    p = sphere(
        pos=vector(x, 0.19 if z < -0.65 else 0.08, z),
        radius=random.uniform(0.025, 0.055),
        color=vector(0.78, 0.94, 1.0),
        opacity=0.50,
    )
    p.speed = random.uniform(0.045, 0.09)
    flow_particles.append(p)

# Ripples upstream of the jam and downstream of the leakage points.
ripples = []
for i in range(18):
    r = ring(
        pos=vector(random.uniform(-3.1, 3.1), 0.255, random.uniform(-5.5, -1.0)),
        axis=vector(0, 1, 0),
        radius=random.uniform(0.15, 0.55),
        thickness=0.012,
        color=vector(0.75, 0.93, 1.0),
        opacity=0.35,
    )
    r.grow = random.uniform(0.004, 0.012)
    ripples.append(r)

# -----------------------------
# Animals
# -----------------------------
class Animal:
    def __init__(self, kind, direction, delay):
        self.kind = kind
        self.direction = direction
        self.delay = delay
        self.phase = random.uniform(0, math.tau)
        self.cross_progress = 0.0 if direction > 0 else 1.0
        self.speed = random.uniform(0.0017, 0.0026) if kind == "bear" else random.uniform(0.0028, 0.0041)
        self.waiting = True
        self.rest_timer = random.uniform(0, 180)
        self.z_lane = random.uniform(-0.19, 0.19)
        self.group = []
        self.make_body()
        self.place_at_start()

    def make_body(self):
        if self.kind == "bear":
            body_color = vector(0.25, 0.16, 0.09)
            muzzle_color = vector(0.42, 0.29, 0.17)
            scale = 1.0
            self.body = ellipsoid(size=vector(0.92, 0.48, 0.42), color=body_color)
            self.head = sphere(radius=0.26, color=body_color)
            self.muzzle = sphere(radius=0.13, color=muzzle_color)
            self.ears = [sphere(radius=0.075, color=body_color), sphere(radius=0.075, color=body_color)]
            self.legs = [cylinder(radius=0.07, color=body_color) for _ in range(4)]
            self.tail = sphere(radius=0.06, color=body_color)
        else:
            body_color = random.choice([vector(0.85, 0.58, 0.23), vector(0.18, 0.18, 0.18), vector(0.92, 0.88, 0.76), vector(0.50, 0.50, 0.48)])
            muzzle_color = vector(0.95, 0.86, 0.70)
            scale = 0.55
            self.body = ellipsoid(size=vector(0.62, 0.25, 0.23), color=body_color)
            self.head = sphere(radius=0.17, color=body_color)
            self.muzzle = sphere(radius=0.07, color=muzzle_color)
            self.ears = [cone(radius=0.07, axis=vector(0, 0.14, 0), color=body_color), cone(radius=0.07, axis=vector(0, 0.14, 0), color=body_color)]
            self.legs = [cylinder(radius=0.035, color=body_color) for _ in range(4)]
            self.tail = cylinder(radius=0.035, color=body_color)
        self.scale = scale
        self.group = [self.body, self.head, self.muzzle, self.tail] + self.ears + self.legs

    def place_at_start(self):
        self.cross_progress = 0.0 if self.direction > 0 else 1.0
        self.waiting = True
        self.rest_timer = random.uniform(80, 220)
        self.z_lane = random.uniform(-0.2, 0.2)
        self.delay = random.uniform(0, 160)

    def hide_offstage(self):
        for part in self.group:
            part.visible = False

    def show(self):
        for part in self.group:
            part.visible = True

    def update(self, t):
        if self.delay > 0:
            self.delay -= 1
            self.hide_offstage()
            return
        self.show()

        if self.waiting:
            self.rest_timer -= 1
            if self.rest_timer <= 0:
                self.waiting = False
            # Waiting on the bank, facing the log.
            x = -5.25 if self.direction > 0 else 5.25
            z = self.z_lane + 0.7 * math.sin(t * 0.015 + self.phase)
        else:
            self.cross_progress += self.speed * self.direction
            if self.cross_progress > 1.08 or self.cross_progress < -0.08:
                self.direction *= -1
                self.place_at_start()
            progress = max(0.0, min(1.0, self.cross_progress))
            x = -4.8 + progress * 9.6
            z = self.z_lane + 0.05 * math.sin(progress * math.pi * 3 + self.phase)

        gait = math.sin(t * (0.12 if self.kind == "bear" else 0.19) + self.phase)
        bob = 0.035 * abs(gait) if self.kind == "bear" else 0.055 * abs(gait)
        y = LOG_Y + LOG_RADIUS + 0.16 + bob if not self.waiting else 0.18 + bob

        facing = self.direction
        if self.waiting:
            facing = 1 if x < 0 else -1

        body_len = 0.92 if self.kind == "bear" else 0.62
        body_height = 0.48 if self.kind == "bear" else 0.25
        self.body.pos = vector(x, y, z)
        self.body.axis = vector(body_len * facing, 0, 0)
        self.head.pos = vector(x + facing * body_len * 0.48, y + body_height * 0.12, z)
        self.muzzle.pos = vector(x + facing * (body_len * 0.65), y + body_height * 0.09, z)
        self.tail.pos = vector(x - facing * body_len * 0.52, y + body_height * 0.04, z)
        if self.kind == "cat":
            self.tail.axis = vector(-facing * 0.34, 0.22 + 0.05 * math.sin(t * 0.13 + self.phase), 0)
        self.ears[0].pos = self.head.pos + vector(-facing * 0.03, 0.17 if self.kind == "cat" else 0.17, 0.10)
        self.ears[1].pos = self.head.pos + vector(-facing * 0.03, 0.17 if self.kind == "cat" else 0.17, -0.10)

        leg_spacing_x = body_len * 0.28
        leg_spacing_z = 0.13 if self.kind == "bear" else 0.08
        leg_len = 0.30 if self.kind == "bear" else 0.20
        for idx, leg in enumerate(self.legs):
            lx = x + (leg_spacing_x if idx < 2 else -leg_spacing_x) * facing
            lz = z + (leg_spacing_z if idx % 2 == 0 else -leg_spacing_z)
            step = 0.055 * math.sin(t * (0.12 if self.kind == "bear" else 0.19) + self.phase + idx * math.pi)
            leg.pos = vector(lx + step * facing, y - body_height * 0.28, lz)
            leg.axis = vector(-step * 0.35 * facing, -leg_len, 0)

# Create a crossing population.
animals = []
for i in range(4):
    animals.append(Animal("bear", 1 if i % 2 == 0 else -1, delay=i * 120))
for i in range(8):
    animals.append(Animal("cat", 1 if i % 2 == 1 else -1, delay=50 + i * 70))

# -----------------------------
# Labels / controls
# -----------------------------
info = label(
    pos=vector(0, 3.6, -6.5),
    text="Fallen log dam: upstream water rises, debris collects, and animals use the log as a bridge",
    height=15,
    box=False,
    color=vector(0.12, 0.16, 0.20),
)
status = label(pos=vector(-7.2, 2.5, 7.8), text="", height=13, box=False, align="left", color=vector(0.12, 0.16, 0.20))

paused = False
show_labels = True
flow_strength = 1.0


def keydown(evt):
    global paused, show_labels, flow_strength
    k = evt.key.lower()
    if k == " ":
        paused = not paused
    elif k == "l":
        show_labels = not show_labels
        info.visible = show_labels
        status.visible = show_labels
    elif k == "up":
        flow_strength = min(2.0, flow_strength + 0.15)
    elif k == "down":
        flow_strength = max(0.25, flow_strength - 0.15)
    elif k == "r":
        flow_strength = 1.0

scene.bind("keydown", keydown)

# -----------------------------
# Animation loop
# -----------------------------
t = 0
while True:
    rate(60)
    if paused:
        status.text = "Paused | Space: resume | Up/Down: river flow | L: labels"
        continue

    t += 1

    # Damming effect: upstream water breathes higher than downstream water.
    dam_pressure = 0.5 + 0.5 * math.sin(t * 0.018)
    upstream_water.size.y = 0.22 + 0.10 * dam_pressure * flow_strength
    upstream_water.pos.y = WATER_Y + 0.08 + upstream_water.size.y * 0.20
    downstream_water.size.y = 0.11 + 0.035 * math.sin(t * 0.025 + 1.2)
    downstream_water.pos.y = WATER_Y - 0.04 + downstream_water.size.y * 0.10

    # Moving water particles slow and pile up before the log, then leak through gaps.
    for p in flow_particles:
        local_speed = p.speed * flow_strength
        if p.pos.z < -0.55:
            # Upstream current moving toward the log.
            p.pos.z += local_speed
            p.pos.x += 0.012 * math.sin(t * 0.04 + p.pos.z * 1.4)
            p.pos.y = upstream_water.pos.y + upstream_water.size.y * 0.52 + 0.01 * math.sin(t * 0.09 + p.pos.x)
            if p.pos.z > -0.62:
                # Most particles circulate against the dam; some leak over/around it.
                if random.random() < 0.78:
                    p.pos.z = random.uniform(-5.7, -2.0)
                    p.pos.x = random.uniform(-3.15, 3.15)
                else:
                    p.pos.z = random.uniform(0.35, 0.9)
                    p.pos.x += random.uniform(-0.25, 0.25)
        else:
            # Downstream leaked current.
            p.pos.z += local_speed * 1.55
            p.pos.y = downstream_water.pos.y + downstream_water.size.y * 0.55
            p.opacity = 0.35 + 0.2 * math.sin(t * 0.05 + p.pos.x)
            if p.pos.z > 11.4:
                p.pos.z = random.uniform(-10.7, -6.0)
                p.pos.x = random.uniform(-3.15, 3.15)
                p.opacity = 0.5

    # Foam pulses and twigs tremble along the jammed side of the log.
    for i, f in enumerate(foam_patches):
        f.pos.x += 0.01 * math.sin(t * 0.05 + i)
        f.pos.y = upstream_water.pos.y + upstream_water.size.y * 0.52 + 0.02 * math.sin(t * 0.07 + i)
        f.opacity = 0.45 + 0.38 * (0.5 + 0.5 * math.sin(t * 0.04 + i * 0.7))
    for i, twig in enumerate(jam_debris):
        twig.rotate(angle=0.002 * math.sin(t * 0.03 + i), axis=vector(0, 1, 0), origin=twig.pos)

    # Ripple expansion near the backed-up water.
    for r in ripples:
        r.radius += r.grow * flow_strength
        r.opacity *= 0.992
        if r.radius > 0.95 or r.opacity < 0.08:
            r.pos = vector(random.uniform(-3.1, 3.1), upstream_water.pos.y + upstream_water.size.y * 0.56, random.uniform(-5.3, -1.05))
            r.radius = random.uniform(0.12, 0.26)
            r.opacity = random.uniform(0.25, 0.42)

    # Spill streams flicker brighter as the upstream water pressure rises.
    for i, s in enumerate(spill_streams):
        s.radius = 0.025 + 0.028 * dam_pressure * flow_strength + 0.006 * math.sin(t * 0.07 + i)
        s.color = vector(0.83 + 0.12 * dam_pressure, 0.95, 1.0)

    # Animals cross the log.
    for a in animals:
        a.update(t)

    crossing_count = sum(1 for a in animals if not a.waiting and a.delay <= 0)
    status.text = (
        f"Animals crossing: {crossing_count}\n"
        f"River flow: {flow_strength:.2f}  (Up/Down keys)\n"
        f"Space: pause | L: labels | R: reset flow"
    )
