from vpython import *
from math import sin, cos, atan2, sqrt, pi
from random import random, uniform, choice, randint
import time

# ============================================================
# Current-Carrying Wire and Circular Magnetic Field Lines
# VPython simulation with rule-based + expressive AI controller
# ============================================================

scene = canvas(
    title="Current-Carrying Wire: Circular Magnetic Field Lines with AI Controller",
    width=1180,
    height=760,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0, 0),
    forward=vector(-1.25, -0.65, -1.2),
)
scene.userspin = True
scene.userzoom = True
scene.range = 6.2
scene.ambient = color.gray(0.72)

scene.caption = """
Controls:
  SPACE: pause/resume simulation      I: toggle AI controller      P: pause/resume AI only
  R: reset round                      M: switch AI behavior mode   C: manual chaos spill
  A: add test charge                  TAB: select next charge
  O: attach selected charge to nearest field ring
  F: detach selected charge
  + / -: increase/decrease current
  Arrow keys: nudge selected charge or rotate it while attached
  H: hide/show in-scene help
"""

# -----------------------------
# Constants and global variables
# -----------------------------

Y_AXIS = vector(0, 1, 0)

WIRE_HEIGHT = 8.4
WIRE_RADIUS = 0.075
WORLD_RADIUS = 4.85
Y_LIMIT = WIRE_HEIGHT / 2
CHARGE_RADIUS = 0.13

RING_RADII = [0.75, 1.25, 1.85, 2.55, 3.35, 4.15]
RING_LEVELS = [-3.2, -1.6, 0.0, 1.6, 3.2]

current_strength = 1.05
paused = False
ai_paused = False
show_help = True
sim_time = 0.0
round_number = 1
selected_index = 0

charges = []
field_rings = []
current_arrows = []
sparks = []
background_marks = []

# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def vec_lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def radial_radius(pos):
    return sqrt(pos.x * pos.x + pos.z * pos.z)

def radial_theta(pos):
    return atan2(pos.z, pos.x)

def radial_unit(pos):
    r = radial_radius(pos)
    if r < 1e-6:
        return vector(1, 0, 0)
    return vector(pos.x / r, 0, pos.z / r)

def tangent_unit_from_theta(theta, direction=1):
    return direction * vector(-sin(theta), 0, cos(theta))

def current_sign():
    return 1 if current_strength >= 0 else -1

def soft_color_for_charge(sign, index=0):
    if sign >= 0:
        palette = [
            vector(1.0, 0.45, 0.35),
            vector(1.0, 0.62, 0.35),
            vector(1.0, 0.36, 0.50),
        ]
    else:
        palette = [
            vector(0.25, 0.55, 1.0),
            vector(0.35, 0.82, 1.0),
            vector(0.45, 0.48, 1.0),
        ]
    return palette[index % len(palette)]

def field_color():
    if current_strength >= 0:
        return vector(0.18, 0.68, 0.92)
    return vector(0.58, 0.45, 1.0)

def nearest_ring_to_position(pos):
    rr = radial_radius(pos)
    best = None
    best_score = 1e9
    for ring_obj in field_rings:
        score = abs(ring_obj.radius - rr) + 0.17 * abs(ring_obj.y - pos.y)
        if score < best_score:
            best_score = score
            best = ring_obj
    return best

def nearest_field_radius(rr):
    return min(RING_RADII, key=lambda r: abs(r - rr))

# -----------------------------
# Stationary scene objects
# -----------------------------

floor = box(
    pos=vector(0, -Y_LIMIT - 0.05, 0),
    size=vector(10.0, 0.035, 10.0),
    color=vector(0.88, 0.92, 0.94),
    opacity=0.35,
)

wire = cylinder(
    pos=vector(0, -Y_LIMIT, 0),
    axis=vector(0, WIRE_HEIGHT, 0),
    radius=WIRE_RADIUS,
    color=vector(0.62, 0.62, 0.66),
    shininess=0.8,
)

wire_glow = cylinder(
    pos=vector(0, -Y_LIMIT, 0),
    axis=vector(0, WIRE_HEIGHT, 0),
    radius=0.145,
    color=vector(1.0, 0.72, 0.32),
    opacity=0.13,
)

axis_tip = cone(
    pos=vector(0, Y_LIMIT + 0.22, 0),
    axis=vector(0, 0.44, 0),
    radius=0.16,
    color=vector(1.0, 0.57, 0.18),
    opacity=0.9,
)

wire_label = label(
    pos=vector(0.32, Y_LIMIT + 0.75, 0),
    text="current I",
    height=14,
    color=vector(0.55, 0.26, 0.05),
    box=False,
    line=False,
)

field_label = label(
    pos=vector(3.4, 3.85, 0),
    text="concentric magnetic field lines B",
    height=13,
    color=vector(0.05, 0.38, 0.52),
    box=False,
    line=False,
)

status_label = label(
    pos=vector(-5.2, 4.75, 0),
    text="",
    height=12,
    color=vector(0.08, 0.12, 0.16),
    box=False,
    line=False,
    align="left",
)

help_label = label(
    pos=vector(-5.2, -4.65, 0),
    text="",
    height=10,
    color=vector(0.14, 0.18, 0.22),
    box=False,
    line=False,
    align="left",
)

selection_indicator = sphere(
    pos=vector(0, 0, 0),
    radius=0.22,
    color=vector(0.1, 0.7, 0.25),
    opacity=0.19,
    visible=False,
)

# -----------------------------
# Visual effect classes
# -----------------------------

class Spark:
    def __init__(self, pos, col=vector(1, 0.85, 0.25), radius=0.06, lifetime=0.9, marker=False):
        self.age = 0.0
        self.lifetime = lifetime
        self.base_radius = radius
        self.marker = marker
        self.body = sphere(
            pos=pos,
            radius=radius,
            color=col,
            opacity=0.75 if not marker else 0.42,
            emissive=True,
        )
        self.vel = vector(uniform(-0.15, 0.15), uniform(-0.08, 0.18), uniform(-0.15, 0.15))

    def update(self, dt):
        self.age += dt
        if self.age >= self.lifetime:
            self.body.visible = False
            return False

        fade = 1.0 - self.age / self.lifetime
        if not self.marker:
            self.body.pos += self.vel * dt
            self.body.radius = self.base_radius * (0.7 + 0.9 * fade)
        self.body.opacity = (0.75 if not self.marker else 0.42) * fade
        return True

class FadingTrail:
    def __init__(self, col, max_points=90, interval=0.055, lifetime=3.3):
        self.col = col
        self.max_points = max_points
        self.interval = interval
        self.lifetime = lifetime
        self.timer = 0.0
        self.points = []

    def add(self, pos, dt, radius=0.032):
        self.timer += dt
        if self.timer < self.interval:
            return
        self.timer = 0.0
        dot = sphere(
            pos=pos,
            radius=radius,
            color=self.col,
            opacity=0.36,
            emissive=True,
        )
        self.points.append([dot, 0.0])
        while len(self.points) > self.max_points:
            old, _ = self.points.pop(0)
            old.visible = False

    def update(self, dt):
        alive = []
        for obj, age in self.points:
            age += dt
            if age < self.lifetime:
                fade = 1.0 - age / self.lifetime
                obj.opacity = 0.36 * fade
                obj.radius = max(0.008, obj.radius * (0.997 + 0.003 * fade))
                alive.append([obj, age])
            else:
                obj.visible = False
        self.points = alive

    def set_color(self, col):
        self.col = col

    def clear(self):
        for obj, _ in self.points:
            obj.visible = False
        self.points = []

# -----------------------------
# Magnetic field ring objects
# -----------------------------

class FieldRing:
    def __init__(self, radius, y, level_index=0):
        self.radius = radius
        self.y = y
        self.theta_offset = uniform(0, 2 * pi)
        opacity = 0.13 + 0.035 * (level_index % 2)
        self.ring = ring(
            pos=vector(0, y, 0),
            axis=Y_AXIS,
            radius=radius,
            thickness=0.012 + 0.003 * (radius < 1.0),
            color=field_color(),
            opacity=opacity,
        )
        self.markers = []
        marker_count = 2 if radius < 3.0 else 3
        for k in range(marker_count):
            theta = self.theta_offset + 2 * pi * k / marker_count
            p = vector(radius * cos(theta), y, radius * sin(theta))
            c = cone(
                pos=p,
                axis=tangent_unit_from_theta(theta, current_sign()) * 0.20,
                radius=0.055,
                color=field_color(),
                opacity=0.62,
            )
            self.markers.append([c, theta])

    def update(self, dt):
        col = field_color()
        self.ring.color = vec_lerp(self.ring.color, col, 0.06)
        self.ring.opacity = 0.09 + 0.045 * clamp(abs(current_strength) / 2.4, 0, 1)
        angular_speed = 0.38 * current_strength / (0.25 + self.radius)
        for item in self.markers:
            marker, theta = item
            theta += angular_speed * dt
            item[1] = theta
            marker.pos = vector(self.radius * cos(theta), self.y, self.radius * sin(theta))
            marker.axis = tangent_unit_from_theta(theta, current_sign()) * (0.18 + 0.08 * clamp(abs(current_strength), 0, 2))
            marker.color = vec_lerp(marker.color, col, 0.09)
            marker.opacity = 0.36 + 0.30 * clamp(abs(current_strength) / 2.0, 0, 1)

# -----------------------------
# Animated current arrows
# -----------------------------

class CurrentArrow:
    def __init__(self, y, phase=0):
        self.phase = phase
        self.obj = arrow(
            pos=vector(-0.18, y, 0),
            axis=vector(0, 0.56, 0),
            shaftwidth=0.07,
            headwidth=0.18,
            headlength=0.20,
            color=vector(1.0, 0.55, 0.16),
            opacity=0.88,
        )

    def update(self, dt):
        sgn = current_sign()
        speed = 0.25 + 1.15 * abs(current_strength)
        self.obj.pos.y += sgn * speed * dt
        if self.obj.pos.y > Y_LIMIT:
            self.obj.pos.y = -Y_LIMIT
        if self.obj.pos.y < -Y_LIMIT:
            self.obj.pos.y = Y_LIMIT
        self.obj.axis = vector(0, 0.56 * sgn, 0)
        target_col = vector(1.0, 0.55, 0.16) if sgn > 0 else vector(0.50, 0.37, 1.0)
        self.obj.color = vec_lerp(self.obj.color, target_col, 0.08)
        self.obj.opacity = 0.45 + 0.45 * clamp(abs(current_strength) / 2.0, 0, 1)

# -----------------------------
# Test charge class
# -----------------------------

class TestCharge:
    next_id = 1

    def __init__(self, pos, sign=1, attached=True, ring_radius=1.0, theta=0.0, y_drift=0.0):
        self.id = TestCharge.next_id
        TestCharge.next_id += 1

        self.charge_sign = sign
        self.attached = attached
        self.ring_radius = ring_radius
        self.theta = theta
        self.y = pos.y
        self.y_drift = y_drift
        self.base_omega = uniform(0.75, 1.25)
        self.velocity = vector(0, 0, 0)
        self.collision_cooldown = 0.0
        self.trail_life_bonus = 0.0

        col = soft_color_for_charge(sign, self.id)
        self.body = sphere(
            pos=pos,
            radius=CHARGE_RADIUS,
            color=col,
            opacity=0.96,
            shininess=0.55,
            emissive=False,
        )

        self.halo = sphere(
            pos=pos,
            radius=CHARGE_RADIUS * 1.58,
            color=vector(1, 1, 1),
            opacity=0.14 if attached else 0.04,
            visible=True,
        )

        self.trail = FadingTrail(col, max_points=105, interval=0.045, lifetime=3.3)

    def attach_to_ring(self, ring_obj=None, theta=None, snap_y=True, spiral=False):
        if ring_obj is None:
            ring_obj = nearest_ring_to_position(self.body.pos)
        self.attached = True
        self.ring_radius = ring_obj.radius
        if theta is None:
            theta = radial_theta(self.body.pos)
        self.theta = theta
        if snap_y:
            self.y = ring_obj.y
        else:
            self.y = clamp(self.body.pos.y, -Y_LIMIT, Y_LIMIT)
        self.y_drift = uniform(-0.28, 0.28) if spiral else 0.0
        self.halo.opacity = 0.16
        self.collision_cooldown = 0.25

    def detach(self, kick=None, speed_scale=1.0):
        if not self.attached:
            return
        self.attached = False
        theta = radial_theta(self.body.pos)
        tangent = tangent_unit_from_theta(theta, self.charge_sign * current_sign())
        if kick is None:
            kick = tangent * (0.75 + 0.65 * random()) + radial_unit(self.body.pos) * uniform(-0.35, 0.55)
        self.velocity = kick * speed_scale + vector(0, uniform(-0.22, 0.22), 0)
        self.halo.opacity = 0.045
        self.collision_cooldown = 0.25

    def mark(self, col=None):
        if col is None:
            col = self.body.color
        sparks.append(Spark(self.body.pos, col=col, radius=0.042, lifetime=1.6, marker=True))

    def update_attached(self, dt):
        previous = vector(self.body.pos.x, self.body.pos.y, self.body.pos.z)
        omega = self.charge_sign * current_strength * self.base_omega / (0.25 + self.ring_radius)
        self.theta += omega * dt
        self.y += self.y_drift * dt

        wrapped = False
        if self.y > Y_LIMIT:
            self.y = -Y_LIMIT
            wrapped = True
        elif self.y < -Y_LIMIT:
            self.y = Y_LIMIT
            wrapped = True

        if wrapped:
            self.trail.clear()
            sparks.append(Spark(vector(self.ring_radius * cos(self.theta), self.y, self.ring_radius * sin(self.theta)),
                                col=vector(0.2, 0.9, 1.0), radius=0.08, lifetime=0.8))

        self.body.pos = vector(self.ring_radius * cos(self.theta), self.y, self.ring_radius * sin(self.theta))
        if dt > 0:
            self.velocity = (self.body.pos - previous) / dt

    def update_free(self, dt):
        pos = self.body.pos
        rr = max(radial_radius(pos), 0.08)
        ru = radial_unit(pos)
        theta = radial_theta(pos)
        tangent = tangent_unit_from_theta(theta, current_sign())

        b_strength = current_strength / (0.35 + rr)
        magnetic_acc = self.charge_sign * cross(self.velocity, tangent * b_strength) * 0.43

        target_r = nearest_field_radius(rr)
        radial_acc = ru * ((target_r - rr) * 0.34)

        damping = -0.055 * self.velocity
        self.velocity += (magnetic_acc + radial_acc + damping) * dt
        self.body.pos += self.velocity * dt

        self.apply_boundaries()

    def apply_boundaries(self):
        pos = self.body.pos

        if pos.y > Y_LIMIT:
            self.body.pos.y = Y_LIMIT
            self.velocity.y *= -0.78
            sparks.append(Spark(self.body.pos, col=vector(0.75, 0.9, 1.0), radius=0.05, lifetime=0.7))
        elif pos.y < -Y_LIMIT:
            self.body.pos.y = -Y_LIMIT
            self.velocity.y *= -0.78
            sparks.append(Spark(self.body.pos, col=vector(0.75, 0.9, 1.0), radius=0.05, lifetime=0.7))

        rr = radial_radius(self.body.pos)
        if rr > WORLD_RADIUS:
            ru = radial_unit(self.body.pos)
            self.body.pos = vector(ru.x * WORLD_RADIUS, self.body.pos.y, ru.z * WORLD_RADIUS)
            vn = dot(self.velocity, ru)
            if vn > 0:
                self.velocity -= 1.72 * vn * ru
            sparks.append(Spark(self.body.pos, col=vector(0.35, 0.8, 1.0), radius=0.055, lifetime=0.75))

        rr = radial_radius(self.body.pos)
        min_r = WIRE_RADIUS + CHARGE_RADIUS + 0.04
        if rr < min_r:
            ru = radial_unit(self.body.pos)
            self.body.pos = vector(ru.x * min_r, self.body.pos.y, ru.z * min_r)
            vn = dot(self.velocity, ru)
            if vn < 0:
                self.velocity -= 1.9 * vn * ru
            self.velocity += ru * 0.45
            sparks.append(Spark(self.body.pos, col=vector(1.0, 0.63, 0.18), radius=0.075, lifetime=0.75))

    def update(self, dt):
        if self.collision_cooldown > 0:
            self.collision_cooldown -= dt

        if self.attached:
            self.update_attached(dt)
        else:
            self.update_free(dt)

        pulse = 0.5 + 0.5 * sin(sim_time * 4.0 + self.id)
        self.body.radius = CHARGE_RADIUS * (0.92 + 0.08 * pulse)
        self.halo.pos = self.body.pos
        self.halo.visible = True
        self.halo.opacity = lerp(self.halo.opacity, 0.16 if self.attached else 0.045, 0.05)

        self.trail.lifetime = 3.3 + self.trail_life_bonus
        self.trail.add(self.body.pos, dt, radius=0.027 if self.attached else 0.033)
        self.trail.update(dt)

    def destroy(self):
        self.body.visible = False
        self.halo.visible = False
        self.trail.clear()

# -----------------------------
# Build field rings and arrows
# -----------------------------

for yi, y in enumerate(RING_LEVELS):
    for r in RING_RADII:
        field_rings.append(FieldRing(r, y, yi))

for k in range(9):
    y = -Y_LIMIT + k * WIRE_HEIGHT / 8.0
    current_arrows.append(CurrentArrow(y, k))

# -----------------------------
# Charge creation and interactions
# -----------------------------

def add_charge(attached=True, sign=None, ring_obj=None, spiral=False):
    if sign is None:
        sign = 1 if random() < 0.56 else -1

    if ring_obj is None:
        ring_obj = choice(field_rings)

    theta = uniform(0, 2 * pi)
    if attached:
        pos = vector(ring_obj.radius * cos(theta), ring_obj.y, ring_obj.radius * sin(theta))
        ch = TestCharge(
            pos=pos,
            sign=sign,
            attached=True,
            ring_radius=ring_obj.radius,
            theta=theta,
            y_drift=uniform(-0.22, 0.22) if spiral else 0.0,
        )
    else:
        r = uniform(0.8, WORLD_RADIUS * 0.85)
        y = uniform(-Y_LIMIT * 0.85, Y_LIMIT * 0.85)
        pos = vector(r * cos(theta), y, r * sin(theta))
        ch = TestCharge(pos=pos, sign=sign, attached=False, ring_radius=r, theta=theta)
        tangent = tangent_unit_from_theta(theta, current_sign() * sign)
        ch.velocity = tangent * uniform(0.3, 1.2) + vector(uniform(-0.25, 0.25), uniform(-0.2, 0.2), uniform(-0.25, 0.25))
    charges.append(ch)
    return ch

def handle_charge_collisions():
    n = len(charges)
    for i in range(n):
        a = charges[i]
        for j in range(i + 1, n):
            b = charges[j]
            delta = b.body.pos - a.body.pos
            d = mag(delta)
            min_d = CHARGE_RADIUS * 2.05
            if d > 1e-5 and d < min_d:
                normal = delta / d
                overlap = min_d - d

                if a.attached:
                    a.detach(kick=-normal * 0.7 + a.velocity * 0.16)
                if b.attached:
                    b.detach(kick=normal * 0.7 + b.velocity * 0.16)

                a.body.pos -= normal * overlap * 0.5
                b.body.pos += normal * overlap * 0.5

                va_n = dot(a.velocity, normal)
                vb_n = dot(b.velocity, normal)
                a.velocity += (vb_n - va_n) * normal * 0.85
                b.velocity += (va_n - vb_n) * normal * 0.85

                if a.collision_cooldown <= 0 and b.collision_cooldown <= 0:
                    col = (a.body.color + b.body.color) * 0.5
                    sparks.append(Spark((a.body.pos + b.body.pos) * 0.5, col=col, radius=0.075, lifetime=0.8))
                    a.collision_cooldown = 0.35
                    b.collision_cooldown = 0.35

def chaos_spill(amount=1.0):
    global current_strength
    current_strength = choice([-1, 1]) * uniform(1.35, 2.45)
    for ch in charges:
        if random() < 0.58 * amount:
            theta = radial_theta(ch.body.pos)
            ru = radial_unit(ch.body.pos)
            tangent = tangent_unit_from_theta(theta, current_sign() * ch.charge_sign)
            ch.detach(kick=ru * uniform(0.2, 1.0) + tangent * uniform(0.4, 1.5), speed_scale=1.0 + 0.6 * amount)
            ch.mark(vector(1.0, 0.42, 0.22))

def organize_charges_evenly():
    if not charges:
        return
    sorted_rings = [ring_obj for ring_obj in field_rings if abs(ring_obj.y) < 0.1 or ring_obj.y in [-1.6, 1.6]]
    for i, ch in enumerate(charges):
        ring_obj = sorted_rings[i % len(sorted_rings)]
        theta = 2 * pi * (i / max(1, len(charges))) + (i % 3) * 0.35
        ch.attach_to_ring(ring_obj, theta=theta, snap_y=True, spiral=False)
        ch.base_omega = 0.85 + 0.1 * (i % 4)
        ch.trail_life_bonus = 0.4

def create_background_mark(pos, col):
    background_marks.append(Spark(pos, col=col, radius=0.035, lifetime=5.0, marker=True))

# -----------------------------
# Reset and loop system
# -----------------------------

def reset_simulation():
    global charges, sparks, background_marks, selected_index, current_strength, round_number

    for ch in charges:
        ch.destroy()
    charges = []

    for sp in sparks:
        sp.body.visible = False
    sparks = []

    for m in background_marks:
        m.body.visible = False
    background_marks = []

    selected_index = 0
    round_number += 1
    current_strength = choice([-1, 1]) * uniform(0.75, 1.25)

    for k in range(9):
        ring_obj = choice(field_rings)
        add_charge(
            attached=True,
            sign=1 if k % 2 == 0 else -1,
            ring_obj=ring_obj,
            spiral=(k % 3 == 0),
        )

    for k in range(3):
        add_charge(attached=False, sign=choice([-1, 1]))

    sparks.append(Spark(vector(0, 0, 0), col=vector(1.0, 0.8, 0.2), radius=0.14, lifetime=1.2))
    if "ai" in globals():
        ai.note_reset()

# Initial charges
for k in range(10):
    add_charge(attached=True, sign=1 if k % 2 == 0 else -1, ring_obj=choice(field_rings), spiral=(k % 3 == 0))
for k in range(2):
    add_charge(attached=False, sign=choice([-1, 1]))

# -----------------------------
# Expressive AI behavior system
# -----------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode = "SPIRAL_DANCE"
        self.modes = [
            "CAREFUL_ORBIT",
            "ORGANIZE",
            "SPIRAL_DANCE",
            "CURIOUS_SCAN",
            "ARTIST_MARK",
            "CHAOS_SPILL",
            "RESET_RITUAL",
        ]
        self.mode_elapsed = 0.0
        self.mode_duration = 13.0
        self.action_timer = 0.0
        self.history = []
        self.human_override_until = 0.0
        self.stagnant_time = 0.0
        self.last_positions = {}
        self.round_elapsed = 0.0
        self.completion_hold = 0.0

    def note_reset(self):
        self.mode_elapsed = 0.0
        self.action_timer = 0.0
        self.stagnant_time = 0.0
        self.last_positions = {}
        self.round_elapsed = 0.0

    def read_state(self):
        if not charges:
            return {
                "count": 0,
                "attached": 0,
                "free": 0,
                "avg_radius": 0,
                "avg_speed": 0,
                "avg_y": 0,
                "current": current_strength,
            }

        attached_count = sum(1 for c in charges if c.attached)
        avg_radius = sum(radial_radius(c.body.pos) for c in charges) / len(charges)
        avg_speed = sum(mag(c.velocity) for c in charges) / len(charges)
        avg_y = sum(c.body.pos.y for c in charges) / len(charges)
        return {
            "count": len(charges),
            "attached": attached_count,
            "free": len(charges) - attached_count,
            "avg_radius": avg_radius,
            "avg_speed": avg_speed,
            "avg_y": avg_y,
            "current": current_strength,
        }

    def detect_stagnation_or_completion(self, dt):
        if not charges:
            self.stagnant_time += dt
            return True

        motion = 0.0
        tracked = 0
        new_positions = {}

        for ch in charges:
            p = ch.body.pos
            new_positions[ch.id] = vector(p.x, p.y, p.z)
            if ch.id in self.last_positions:
                motion += mag(p - self.last_positions[ch.id])
                tracked += 1

        self.last_positions = new_positions

        if tracked > 0:
            avg_motion = motion / tracked
            if avg_motion < 0.0035 and abs(current_strength) < 0.12:
                self.stagnant_time += dt
            else:
                self.stagnant_time = max(0.0, self.stagnant_time - 0.7 * dt)

        stable_orbit_complete = (
            self.mode == "ORGANIZE"
            and self.mode_elapsed > 10.0
            and all(ch.attached for ch in charges)
        )

        if stable_orbit_complete:
            self.completion_hold += dt
        else:
            self.completion_hold = max(0.0, self.completion_hold - dt)

        return self.stagnant_time > 5.5 or self.completion_hold > 4.5 or self.round_elapsed > 95.0

    def choose_next_mode(self, forced=None):
        if forced is not None:
            new_mode = forced
        else:
            recent = set(self.history[-2:])
            candidates = [m for m in self.modes if m != self.mode and m not in recent]
            if not candidates:
                candidates = [m for m in self.modes if m != self.mode]
            new_mode = choice(candidates)

        self.history.append(self.mode)
        self.mode = new_mode
        self.mode_elapsed = 0.0
        self.action_timer = 0.0
        self.mode_duration = {
            "CAREFUL_ORBIT": uniform(10, 15),
            "ORGANIZE": uniform(11, 16),
            "SPIRAL_DANCE": uniform(13, 20),
            "CURIOUS_SCAN": uniform(12, 18),
            "ARTIST_MARK": uniform(12, 18),
            "CHAOS_SPILL": uniform(7, 12),
            "RESET_RITUAL": uniform(2.5, 4.0),
        }[self.mode]

    def nudge_current_toward(self, target, dt, strength=0.8):
        global current_strength
        current_strength = lerp(current_strength, target, dt * strength)
        current_strength = clamp(current_strength, -2.8, 2.8)

    def update(self, dt):
        global current_strength

        if not self.enabled or ai_paused:
            return

        self.round_elapsed += dt
        self.mode_elapsed += dt
        self.action_timer += dt

        state = self.read_state()
        halted = self.detect_stagnation_or_completion(dt)

        if halted and self.mode != "RESET_RITUAL":
            self.choose_next_mode("RESET_RITUAL")

        if self.mode_elapsed > self.mode_duration and self.mode != "RESET_RITUAL":
            self.choose_next_mode()

        # Human input override: AI keeps observing, but temporarily stops commanding objects.
        if sim_time < self.human_override_until:
            return

        if self.mode == "RESET_RITUAL":
            self.nudge_current_toward(0.0, dt, strength=1.5)
            if self.action_timer > 0.25:
                self.action_timer = 0
                r = choice(RING_RADII)
                th = uniform(0, 2 * pi)
                y = choice(RING_LEVELS)
                sparks.append(Spark(vector(r * cos(th), y, r * sin(th)), col=vector(1.0, 0.85, 0.25), radius=0.08, lifetime=0.9))
            if self.mode_elapsed > 2.3:
                reset_simulation()
                self.choose_next_mode(choice(["CAREFUL_ORBIT", "SPIRAL_DANCE", "CURIOUS_SCAN", "ARTIST_MARK"]))
            return

        if state["count"] < 5:
            if self.action_timer > 0.6:
                add_charge(attached=random() < 0.75, sign=choice([-1, 1]), ring_obj=choice(field_rings), spiral=random() < 0.35)
                self.action_timer = 0

        if self.mode == "CAREFUL_ORBIT":
            self.nudge_current_toward(0.78 * current_sign(), dt, strength=0.7)
            if self.action_timer > 0.8:
                self.action_timer = 0
                for ch in charges:
                    ch.trail_life_bonus = 0.1
                    if not ch.attached and random() < 0.7:
                        ch.attach_to_ring(nearest_ring_to_position(ch.body.pos), snap_y=False, spiral=False)
                    if ch.attached:
                        ch.y_drift = lerp(ch.y_drift, 0.0, 0.2)

        elif self.mode == "ORGANIZE":
            self.nudge_current_toward(0.64, dt, strength=0.9)
            if self.action_timer > 1.7:
                self.action_timer = 0
                organize_charges_evenly()
                for ch in charges:
                    if random() < 0.25:
                        ch.mark(vector(0.35, 0.9, 0.75))

        elif self.mode == "SPIRAL_DANCE":
            target = 1.12 * sin(self.mode_elapsed * 0.62) + 0.86 * current_sign()
            self.nudge_current_toward(target, dt, strength=0.55)
            if self.action_timer > 0.75:
                self.action_timer = 0
                for ch in charges:
                    if not ch.attached and random() < 0.45:
                        ch.attach_to_ring(nearest_ring_to_position(ch.body.pos), snap_y=False, spiral=True)
                    if ch.attached:
                        ch.y_drift = 0.20 * sin(self.mode_elapsed * 0.9 + ch.id * 0.75)
                        ch.trail_life_bonus = 0.6
                if random() < 0.35 and len(charges) < 15:
                    add_charge(attached=True, sign=choice([-1, 1]), ring_obj=choice(field_rings), spiral=True)

        elif self.mode == "CURIOUS_SCAN":
            target = 1.55 * sin(self.mode_elapsed * 0.45)
            self.nudge_current_toward(target, dt, strength=0.65)
            if self.action_timer > 1.15:
                self.action_timer = 0
                if charges:
                    ch = choice(charges)
                    if ch.attached:
                        if random() < 0.42:
                            ch.detach(speed_scale=0.85)
                        else:
                            ch.y_drift = uniform(-0.34, 0.34)
                    else:
                        ch.attach_to_ring(nearest_ring_to_position(ch.body.pos), snap_y=random() < 0.5, spiral=random() < 0.5)
                    ch.mark(vector(0.15, 0.75, 1.0))

        elif self.mode == "ARTIST_MARK":
            self.nudge_current_toward(1.25 * sin(self.mode_elapsed * 0.35) + 0.35, dt, strength=0.5)
            if self.action_timer > 0.28:
                self.action_timer = 0
                if charges:
                    ch = choice(charges)
                    hue_col = vector(
                        0.55 + 0.45 * sin(sim_time * 1.3 + ch.id),
                        0.55 + 0.45 * sin(sim_time * 1.7 + ch.id + 2.1),
                        0.55 + 0.45 * sin(sim_time * 1.1 + ch.id + 4.2),
                    )
                    ch.trail_life_bonus = 2.0
                    ch.mark(hue_col)
                    create_background_mark(ch.body.pos, hue_col)
                    if not ch.attached and random() < 0.3:
                        ch.attach_to_ring(nearest_ring_to_position(ch.body.pos), snap_y=False, spiral=True)

        elif self.mode == "CHAOS_SPILL":
            target = choice([-1, 1]) * (1.65 + 0.85 * sin(self.mode_elapsed * 2.4))
            self.nudge_current_toward(target, dt, strength=1.25)
            if self.action_timer > 0.52:
                self.action_timer = 0
                if charges:
                    ch = choice(charges)
                    theta = radial_theta(ch.body.pos)
                    ru = radial_unit(ch.body.pos)
                    tangent = tangent_unit_from_theta(theta, current_sign() * ch.charge_sign)
                    ch.detach(kick=ru * uniform(0.4, 1.35) + tangent * uniform(-1.4, 1.8), speed_scale=1.15)
                    ch.mark(vector(1.0, 0.35, 0.14))
                if random() < 0.28 and len(charges) < 18:
                    add_charge(attached=False, sign=choice([-1, 1]))

ai = AIController()

# -----------------------------
# Keyboard control
# -----------------------------

def select_next_charge():
    global selected_index
    if charges:
        selected_index = (selected_index + 1) % len(charges)

def get_selected_charge():
    if not charges:
        return None
    return charges[selected_index % len(charges)]

def mark_human_override(seconds=5.0):
    if "ai" in globals():
        ai.human_override_until = sim_time + seconds

def keydown(evt):
    global paused, ai_paused, current_strength, selected_index, show_help

    k = evt.key

    if k in [" ", "space"]:
        paused = not paused
        return

    if k.lower() == "i":
        ai.enabled = not ai.enabled
        return

    if k.lower() == "p":
        ai_paused = not ai_paused
        return

    if k.lower() == "h":
        show_help = not show_help
        help_label.visible = show_help
        return

    mark_human_override()

    if k.lower() == "r":
        reset_simulation()

    elif k.lower() == "m":
        ai.choose_next_mode()

    elif k.lower() == "c":
        chaos_spill(1.0)

    elif k.lower() == "a":
        add_charge(attached=random() < 0.7, sign=choice([-1, 1]), ring_obj=choice(field_rings), spiral=random() < 0.45)
        selected_index = len(charges) - 1

    elif k == "tab":
        select_next_charge()

    elif k.lower() == "o":
        ch = get_selected_charge()
        if ch:
            ch.attach_to_ring(nearest_ring_to_position(ch.body.pos), snap_y=False, spiral=True)
            ch.mark(vector(0.2, 0.9, 0.8))

    elif k.lower() == "f":
        ch = get_selected_charge()
        if ch:
            ch.detach(speed_scale=1.1)
            ch.mark(vector(1.0, 0.45, 0.2))

    elif k in ["+", "="]:
        current_strength = clamp(current_strength + 0.18, -2.8, 2.8)

    elif k in ["-", "_"]:
        current_strength = clamp(current_strength - 0.18, -2.8, 2.8)

    elif k in ["left", "right", "up", "down"]:
        ch = get_selected_charge()
        if ch:
            if ch.attached:
                if k == "left":
                    ch.theta -= 0.22
                elif k == "right":
                    ch.theta += 0.22
                elif k == "up":
                    ch.y = clamp(ch.y + 0.22, -Y_LIMIT, Y_LIMIT)
                elif k == "down":
                    ch.y = clamp(ch.y - 0.22, -Y_LIMIT, Y_LIMIT)
            else:
                if k == "left":
                    ch.body.pos.x -= 0.18
                    ch.velocity.x -= 0.12
                elif k == "right":
                    ch.body.pos.x += 0.18
                    ch.velocity.x += 0.12
                elif k == "up":
                    ch.body.pos.y += 0.18
                    ch.velocity.y += 0.12
                elif k == "down":
                    ch.body.pos.y -= 0.18
                    ch.velocity.y -= 0.12
            ch.mark(vector(0.25, 0.95, 0.35))

scene.bind("keydown", keydown)

# -----------------------------
# UI update
# -----------------------------

def update_labels():
    state = ai.read_state()
    ai_state = "ON" if ai.enabled else "OFF"
    if ai_paused:
        ai_state += " / paused"
    if sim_time < ai.human_override_until and ai.enabled and not ai_paused:
        ai_state += " / human override"

    status_label.text = (
        f"Round {round_number}\n"
        f"Current I: {current_strength:+.2f}\n"
        f"Charges: {state['count']}   attached/orbiting: {state['attached']}   free: {state['free']}\n"
        f"AI: {ai_state}\n"
        f"AI mode: {ai.mode}\n"
        f"Selected: #{get_selected_charge().id if get_selected_charge() else '-'}\n"
        f"{'SIM PAUSED' if paused else ''}"
    )

    if show_help:
        help_label.text = (
            "Objects: stationary vertical wire, current arrows, magnetic field rings, movable test charges.\n"
            "Charges can attach to rings, detach, orbit, spiral, wrap vertically, collide, bounce, and mark trails.\n"
            "AI modes: careful orbit, organize, spiral dance, curious scan, artist mark, chaos spill, reset ritual."
        )
    else:
        help_label.text = ""

def update_selection_indicator():
    ch = get_selected_charge()
    if ch:
        selection_indicator.visible = True
        selection_indicator.pos = ch.body.pos
        selection_indicator.radius = CHARGE_RADIUS * (1.95 + 0.2 * sin(sim_time * 6))
    else:
        selection_indicator.visible = False

# -----------------------------
# Main simulation loop
# -----------------------------

last_time = time.time()

while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last_time, 0.001, 0.04)
    last_time = now

    if paused:
        update_labels()
        continue

    sim_time += dt

    ai.update(dt)

    wire_glow.color = vec_lerp(
        wire_glow.color,
        vector(1.0, 0.68, 0.26) if current_strength >= 0 else vector(0.50, 0.42, 1.0),
        0.05,
    )
    wire_glow.opacity = 0.08 + 0.12 * clamp(abs(current_strength) / 2.2, 0, 1)
    axis_tip.axis = vector(0, 0.44 * current_sign(), 0)
    axis_tip.pos = vector(0, Y_LIMIT + 0.22 if current_sign() > 0 else -Y_LIMIT - 0.22, 0)
    axis_tip.color = vector(1.0, 0.57, 0.18) if current_sign() > 0 else vector(0.50, 0.37, 1.0)

    for arr in current_arrows:
        arr.update(dt)

    for fr in field_rings:
        fr.update(dt)

    for ch in charges:
        ch.update(dt)

    handle_charge_collisions()

    alive_sparks = []
    for sp in sparks:
        if sp.update(dt):
            alive_sparks.append(sp)
    sparks = alive_sparks

    alive_marks = []
    for m in background_marks:
        if m.update(dt):
            alive_marks.append(m)
    background_marks = alive_marks

    update_selection_indicator()
    update_labels()
