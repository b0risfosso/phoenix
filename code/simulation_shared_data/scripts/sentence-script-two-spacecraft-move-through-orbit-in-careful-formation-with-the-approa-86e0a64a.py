from vpython import *
import math
import random

# Orbital Rendezvous Ballet
# Two spacecraft move through orbit in careful formation, with the approaching
# craft slowly matching the ISS speed until both drift together above Earth.

scene = canvas(
    title="Orbital Rendezvous Ballet — ISS rendezvous above Earth",
    width=1200,
    height=760,
    background=vector(0.86, 0.92, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-1.2, -0.55, -1.0)
scene.range = 18
scene.autoscale = False
scene.userspin = True
scene.userzoom = True

# ---------- Colors ----------
EARTH_BLUE = vector(0.18, 0.45, 0.86)
EARTH_GREEN = vector(0.14, 0.55, 0.26)
EARTH_WHITE = vector(0.95, 0.97, 1.0)
ORBIT_LINE = vector(0.46, 0.58, 0.78)
ISS_WHITE = vector(0.92, 0.95, 0.97)
ISS_DARK = vector(0.34, 0.38, 0.43)
SOLAR_BLUE = vector(0.18, 0.32, 0.72)
CRAFT_BODY = vector(0.88, 0.88, 0.82)
CRAFT_ACCENT = vector(0.95, 0.48, 0.18)
THRUST = vector(0.3, 0.72, 1.0)
MATCHED = vector(0.1, 0.65, 0.38)
AMBER = vector(1.0, 0.68, 0.18)

# ---------- Scene objects ----------
earth_radius = 6.2
orbit_radius = 11.0
altitude_y = 0.0

earth = sphere(
    pos=vector(0, -7.0, 0),
    radius=earth_radius,
    color=EARTH_BLUE,
    shininess=0.25,
)

# Cloud shell and soft atmosphere
atmosphere = sphere(
    pos=earth.pos,
    radius=earth_radius * 1.035,
    color=vector(0.55, 0.78, 1.0),
    opacity=0.18,
    shininess=0.0,
)

# Abstract continents visible from orbit
continents = []
continent_specs = [
    (-2.8, 0.35, 2.2, 1.1, 0.22),
    (1.6, -0.55, 2.8, 1.0, -0.34),
    (0.4, 1.1, 1.6, 0.7, 0.44),
    (-0.6, -1.8, 1.1, 0.5, 0.02),
    (3.0, 0.85, 1.25, 0.55, -0.1),
]
for x, z, sx, sz, rot in continent_specs:
    patch = ellipsoid(
        pos=earth.pos + vector(x, earth_radius * 0.98, z),
        length=sx,
        height=0.05,
        width=sz,
        axis=vector(math.cos(rot), 0, math.sin(rot)),
        color=EARTH_GREEN,
        opacity=0.76,
    )
    continents.append(patch)

# Orbit guide rings. Use ring, not torus, for this VPython environment.
orbit_ring = ring(
    pos=vector(0, altitude_y, 0),
    axis=vector(0, 1, 0),
    radius=orbit_radius,
    thickness=0.018,
    color=ORBIT_LINE,
    opacity=0.38,
)
inner_orbit = ring(
    pos=vector(0, altitude_y, 0),
    axis=vector(0, 1, 0),
    radius=orbit_radius - 1.1,
    thickness=0.01,
    color=ORBIT_LINE,
    opacity=0.18,
)

# Soft sun and orbital lighting
local_light(pos=vector(-8, 12, 8), color=vector(1.0, 0.96, 0.82))
distant_light(direction=vector(-0.4, -0.7, -0.5), color=vector(0.9, 0.95, 1.0))
sun = sphere(pos=vector(-16, 12, 10), radius=0.65, color=vector(1, 0.86, 0.34), emissive=True)

# ---------- Helpers ----------
managed_objects = []

def add_obj(obj):
    managed_objects.append(obj)
    return obj


def tangent_at(theta):
    return vector(-math.sin(theta), 0, math.cos(theta))


def radial_at(theta):
    return vector(math.cos(theta), 0, math.sin(theta))


def orbit_pos(theta, radius=orbit_radius, y=altitude_y):
    return vector(radius * math.cos(theta), y, radius * math.sin(theta))


def set_part_visibility(parts, visible):
    for p in parts:
        p.visible = visible

# ---------- ISS model ----------
class ISSModel:
    def __init__(self):
        self.parts = []
        self.theta = 0.52
        self.speed = 0.165
        self.pos = orbit_pos(self.theta)
        self.forward = tangent_at(self.theta)
        self.right = radial_at(self.theta)
        self.up = vector(0, 1, 0)

        self.core = add_obj(box(pos=self.pos, size=vector(1.15, 0.28, 0.34), color=ISS_WHITE, shininess=0.5))
        self.parts.append(self.core)
        self.truss = add_obj(box(pos=self.pos, size=vector(2.9, 0.08, 0.08), color=ISS_DARK))
        self.parts.append(self.truss)

        self.modules = []
        for offset in [-0.54, -0.18, 0.18, 0.54]:
            m = add_obj(cylinder(pos=self.pos, axis=self.forward * 0.33, radius=0.12, color=ISS_WHITE))
            self.modules.append((m, offset))
            self.parts.append(m)

        self.panels = []
        for side in [-1, 1]:
            for segment in [-1.12, -0.5, 0.5, 1.12]:
                panel = add_obj(box(pos=self.pos, size=vector(0.52, 0.035, 0.82), color=SOLAR_BLUE, opacity=0.88))
                self.panels.append((panel, side, segment))
                self.parts.append(panel)

        self.docking_port = add_obj(cylinder(pos=self.pos, axis=self.forward * 0.28, radius=0.13, color=vector(0.75, 0.79, 0.82)))
        self.parts.append(self.docking_port)
        self.trail = add_obj(curve(pos=[self.pos, self.pos + vector(0.01, 0, 0)], radius=0.018, color=MATCHED, opacity=0.45))
        self.parts.append(self.trail)

    def update(self, dt):
        self.theta += self.speed * dt
        self.pos = orbit_pos(self.theta)
        self.forward = tangent_at(self.theta)
        self.right = radial_at(self.theta)
        self.up = vector(0, 1, 0)

        self.core.pos = self.pos
        self.core.axis = self.forward
        self.core.up = self.up
        self.truss.pos = self.pos + self.up * 0.05
        self.truss.axis = self.right
        self.truss.up = self.up

        for m, offset in self.modules:
            m.pos = self.pos + self.right * offset - self.forward * 0.12
            m.axis = self.forward * 0.42

        for panel, side, segment in self.panels:
            panel.pos = self.pos + self.right * segment + self.up * side * 0.52
            panel.axis = self.right
            panel.up = self.up

        self.docking_port.pos = self.pos - self.forward * 0.78
        self.docking_port.axis = -self.forward * 0.34

        if self.trail.npoints < 170:
            self.trail.append(pos=self.pos)
        else:
            self.trail.clear()
            self.trail.append(pos=self.pos - self.forward * 0.01)
            self.trail.append(pos=self.pos)

# ---------- Approaching spacecraft ----------
class ApproachCraft:
    def __init__(self, iss):
        self.parts = []
        self.iss = iss
        self.theta = iss.theta - 1.85
        self.radius = orbit_radius - 1.35
        self.speed = iss.speed * 0.72
        self.match = 0.0
        self.phase = 0.0
        self.pos = orbit_pos(self.theta, self.radius, altitude_y - 0.12)
        self.forward = tangent_at(self.theta)
        self.right = radial_at(self.theta)
        self.up = vector(0, 1, 0)

        self.body = add_obj(cylinder(pos=self.pos, axis=self.forward * 0.72, radius=0.23, color=CRAFT_BODY, shininess=0.45))
        self.parts.append(self.body)
        self.nose = add_obj(cone(pos=self.pos + self.forward * 0.72, axis=self.forward * 0.3, radius=0.23, color=CRAFT_ACCENT))
        self.parts.append(self.nose)
        self.cabin = add_obj(sphere(pos=self.pos + self.forward * 0.26 + self.up * 0.18, radius=0.17, color=vector(0.65, 0.84, 1.0), opacity=0.78))
        self.parts.append(self.cabin)

        self.wings = []
        for side in [-1, 1]:
            wing = add_obj(box(pos=self.pos, size=vector(0.72, 0.035, 0.22), color=vector(0.7, 0.74, 0.78)))
            self.wings.append((wing, side))
            self.parts.append(wing)

        self.thrusters = []
        for side in [-1, 1]:
            thr = add_obj(cone(pos=self.pos, axis=-self.forward * 0.36, radius=0.09, color=THRUST, opacity=0.48, emissive=True))
            self.thrusters.append((thr, side))
            self.parts.append(thr)

        self.trail = add_obj(curve(pos=[self.pos, self.pos + vector(0.01, 0, 0)], radius=0.02, color=AMBER, opacity=0.56))
        self.parts.append(self.trail)

    def update(self, dt):
        # Speed and orbital radius gradually converge with ISS: the rendezvous ballet.
        self.phase += dt
        target_theta = self.iss.theta - 0.34
        angle_error = math.atan2(math.sin(target_theta - self.theta), math.cos(target_theta - self.theta))
        speed_target = self.iss.speed + 0.045 * angle_error
        self.speed += (speed_target - self.speed) * min(1, 0.42 * dt)
        self.theta += self.speed * dt

        desired_radius = orbit_radius - 0.14 * max(0.0, min(1.0, abs(angle_error) * 2.2))
        self.radius += (desired_radius - self.radius) * min(1, 0.21 * dt)
        self.match = max(0.0, min(1.0, 1.0 - abs(angle_error) / 1.5 - abs(self.radius - orbit_radius) / 1.6))

        vertical_bob = 0.16 * math.sin(self.phase * 2.4) * (1 - self.match)
        self.pos = orbit_pos(self.theta, self.radius, altitude_y - 0.14 + vertical_bob)
        self.forward = norm(tangent_at(self.theta) + radial_at(self.theta) * 0.035 * math.sin(self.phase * 3.1))
        self.right = radial_at(self.theta)

        self.body.pos = self.pos - self.forward * 0.36
        self.body.axis = self.forward * 0.72
        self.nose.pos = self.pos + self.forward * 0.34
        self.nose.axis = self.forward * 0.3
        self.cabin.pos = self.pos + self.forward * 0.08 + self.up * 0.22

        for wing, side in self.wings:
            wing.pos = self.pos - self.forward * 0.18 + self.right * side * 0.42
            wing.axis = self.right * side
            wing.up = self.up

        pulse = 0.55 + 0.45 * abs(math.sin(self.phase * 7.0))
        thrust_len = 0.15 + 0.36 * (1 - self.match) * pulse
        for thr, side in self.thrusters:
            thr.pos = self.pos - self.forward * 0.82 + self.right * side * 0.16
            thr.axis = -self.forward * thrust_len
            thr.opacity = 0.18 + 0.48 * (1 - self.match) * pulse

        trail_color = AMBER * (1 - self.match) + MATCHED * self.match
        self.trail.color = trail_color
        if self.trail.npoints < 180:
            self.trail.append(pos=self.pos)
        else:
            self.trail.clear()
            self.trail.append(pos=self.pos - self.forward * 0.01)
            self.trail.append(pos=self.pos)

# ---------- Visual overlays ----------
iss = ISSModel()
craft = ApproachCraft(iss)

line_of_approach = curve(pos=[craft.pos, iss.pos], radius=0.018, color=AMBER, opacity=0.45)
docking_corridor = curve(pos=[iss.pos, iss.pos - iss.forward], radius=0.025, color=MATCHED, opacity=0.38)
range_marker = label(
    pos=vector(-8.5, 5.8, 0),
    text="Rendezvous initializing",
    color=vector(0.1, 0.16, 0.24),
    height=18,
    border=8,
    box=False,
    opacity=0,
)
status_panel = label(
    pos=vector(7.5, 5.8, 0),
    text="",
    color=vector(0.1, 0.16, 0.24),
    height=13,
    border=8,
    box=True,
    background=vector(0.95, 0.97, 1.0),
    opacity=0.45,
)

# Approach dots in the docking corridor
corridor_dots = []
for i in range(12):
    dot = sphere(pos=iss.pos, radius=0.045, color=MATCHED, opacity=0.22, emissive=True)
    corridor_dots.append(dot)

# Stars / distant orbital reference points on a light sky
stars = []
for _ in range(80):
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(17, 32)
    y = random.uniform(-5, 12)
    star = sphere(pos=vector(r * math.cos(angle), y, r * math.sin(angle)), radius=random.uniform(0.018, 0.04), color=vector(1, 1, 1), opacity=random.uniform(0.45, 0.9), emissive=True)
    stars.append(star)

# Velocity arrows
iss_velocity = arrow(pos=iss.pos, axis=iss.forward * 1.15, shaftwidth=0.035, color=MATCHED, opacity=0.75)
craft_velocity = arrow(pos=craft.pos, axis=craft.forward * 1.15, shaftwidth=0.035, color=AMBER, opacity=0.75)

# ---------- Controls ----------
paused = False
camera_follow = True
show_guides = True

def keydown(evt):
    global paused, camera_follow, show_guides
    key = evt.key
    if key == ' ':
        paused = not paused
    elif key in ['f', 'F']:
        camera_follow = not camera_follow
    elif key in ['g', 'G']:
        show_guides = not show_guides
        line_of_approach.visible = show_guides
        docking_corridor.visible = show_guides
        iss_velocity.visible = show_guides
        craft_velocity.visible = show_guides
        for d in corridor_dots:
            d.visible = show_guides
    elif key in ['r', 'R']:
        craft.theta = iss.theta - 1.85
        craft.radius = orbit_radius - 1.35
        craft.speed = iss.speed * 0.72
        craft.trail.clear()
        craft.trail.append(pos=craft.pos)
        craft.trail.append(pos=craft.pos + vector(0.01, 0, 0))

scene.bind('keydown', keydown)

help_text = label(
    pos=vector(0, -13.3, 0),
    text="Space: pause/resume   F: camera follow   G: guides   R: reset approach   Mouse: move camera",
    color=vector(0.12, 0.18, 0.26),
    height=12,
    box=False,
    opacity=0,
)

# ---------- Main loop ----------
t = 0.0
dt = 0.018
while True:
    rate(60)
    if paused:
        continue

    t += dt
    iss.update(dt)
    craft.update(dt)

    # Rotate Earth slowly and keep abstract surface features locked to it by moving in a lazy drift.
    earth.rotate(angle=0.003, axis=vector(0, 1, 0), origin=earth.pos)
    atmosphere.rotate(angle=0.0022, axis=vector(0, 1, 0), origin=earth.pos)
    for idx, patch in enumerate(continents):
        patch.rotate(angle=0.003, axis=vector(0, 1, 0), origin=earth.pos)
        patch.opacity = 0.62 + 0.12 * math.sin(t * 0.6 + idx)

    # Guide lines update. Always provide existing points; avoid empty curve initialization.
    line_of_approach.clear()
    line_of_approach.append(pos=craft.pos)
    line_of_approach.append(pos=iss.docking_port.pos)
    line_of_approach.opacity = 0.16 + 0.38 * (1 - craft.match)
    line_of_approach.color = AMBER * (1 - craft.match) + MATCHED * craft.match

    corridor_start = iss.docking_port.pos
    corridor_end = iss.docking_port.pos - iss.forward * 2.1
    docking_corridor.clear()
    docking_corridor.append(pos=corridor_start)
    docking_corridor.append(pos=corridor_end)
    docking_corridor.opacity = 0.22 + 0.28 * craft.match

    for i, dot in enumerate(corridor_dots):
        phase = ((i / len(corridor_dots)) + t * 0.18) % 1.0
        dot.pos = corridor_start * (1 - phase) + corridor_end * phase
        dot.opacity = (0.12 + 0.36 * craft.match) * (0.5 + 0.5 * math.sin(t * 4 + i))
        dot.radius = 0.035 + 0.03 * craft.match

    rel = iss.docking_port.pos - craft.pos
    range_value = mag(rel)
    speed_delta = abs(craft.speed - iss.speed)
    if craft.match < 0.45:
        stage = "phasing orbit"
    elif craft.match < 0.78:
        stage = "closing and matching speed"
    else:
        stage = "formation drift"

    range_marker.text = "Orbital Rendezvous Ballet\napproach range: {:.2f}\nspeed delta: {:.3f}\nstage: {}".format(range_value, speed_delta, stage)
    range_marker.pos = vector(-8.7, 5.8, 0)

    status_panel.text = "ISS velocity  >>>\nChaser velocity >>>\nmatch quality: {:>3.0f}%\n{}".format(craft.match * 100, "docked rhythm" if craft.match > 0.86 else "controlled approach")
    status_panel.pos = vector(7.6, 5.8, 0)

    iss_velocity.pos = iss.pos + vector(0, 0.6, 0)
    iss_velocity.axis = iss.forward * (0.9 + 0.7 * iss.speed / 0.2)
    craft_velocity.pos = craft.pos + vector(0, 0.45, 0)
    craft_velocity.axis = craft.forward * (0.9 + 0.7 * craft.speed / 0.2)
    craft_velocity.color = AMBER * (1 - craft.match) + MATCHED * craft.match

    # Slight coordinated drift once matched.
    if craft.match > 0.86:
        craft.body.color = CRAFT_BODY * 0.88 + MATCHED * 0.12
        range_marker.color = MATCHED
    else:
        craft.body.color = CRAFT_BODY
        range_marker.color = vector(0.1, 0.16, 0.24)

    if camera_follow:
        mid = (iss.pos + craft.pos) * 0.5
        scene.center = scene.center * 0.94 + mid * 0.06
