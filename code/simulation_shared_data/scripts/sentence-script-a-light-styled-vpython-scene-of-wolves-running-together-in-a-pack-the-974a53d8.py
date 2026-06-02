"""
Wolf Pack Running Simulation - VPython

Light-styled VPython scene of wolves running together in a pack.
This version avoids VPython compound.origin and keeps every wolf part as a
separate primitive so legs, paws, tails, heads, and bodies animate reliably.

Keyboard controls:
    SPACE  pause/resume
    W      increase pack speed
    S      decrease pack speed
    A      steer pack left
    D      steer pack right
    F      toggle formation tight/loose
    T      toggle trails
    R      reset pack
    H      show/hide help

Run with:
    python wolf_pack_vpython_fixed.py
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Wolf Pack Running - Fixed",
    width=1200,
    height=760,
    background=vector(0.86, 0.92, 1.0),
    center=vector(0, 2, 0),
)
scene.forward = vector(-0.55, -0.25, -0.8)
scene.range = 48
scene.userspin = True
scene.userzoom = True

GROUND_Y = -0.18
WORLD_HALF = 58

terrain = box(
    pos=vector(0, GROUND_Y - 0.05, 0),
    size=vector(WORLD_HALF * 2.4, 0.1, WORLD_HALF * 2.4),
    color=vector(0.74, 0.84, 0.66),
)

for i, z in enumerate([-54, -48, -42]):
    box(
        pos=vector(0, 1.1 + i * 0.25, z),
        size=vector(WORLD_HALF * 2.2, 0.08, 0.45),
        color=vector(0.78 + i * 0.02, 0.87 + i * 0.015, 0.95),
        opacity=0.5,
    )

for _ in range(170):
    x = random.uniform(-WORLD_HALF, WORLD_HALF)
    z = random.uniform(-WORLD_HALF, WORLD_HALF)
    if random.random() < 0.72:
        cylinder(
            pos=vector(x, GROUND_Y, z),
            axis=vector(0, random.uniform(0.25, 0.9), 0),
            radius=random.uniform(0.012, 0.025),
            color=vector(0.34, 0.54 + random.random() * 0.16, 0.25),
            opacity=0.65,
        )
    else:
        sphere(
            pos=vector(x, GROUND_Y + 0.03, z),
            radius=random.uniform(0.09, 0.2),
            color=vector(0.55, 0.55, 0.50),
            opacity=0.75,
        )

local_light(pos=vector(-30, 35, 15), color=vector(1.0, 0.97, 0.88))
distant_light(direction=vector(0.25, -0.45, 0.4), color=vector(0.75, 0.78, 0.82))

# -----------------------------
# Helpers
# -----------------------------
def clamp(value, low, high):
    return max(low, min(high, value))


def norm_or(v, fallback):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def horizontal_angle(direction):
    return math.atan2(direction.x, direction.z)


def forward_from_yaw(angle):
    return vector(math.sin(angle), 0, math.cos(angle))


def right_from_yaw(angle):
    return vector(math.cos(angle), 0, -math.sin(angle))


def rotate_y(local_v, yaw):
    ca = math.cos(yaw)
    sa = math.sin(yaw)
    return vector(local_v.x * ca + local_v.z * sa, local_v.y, -local_v.x * sa + local_v.z * ca)


def world_point(base_pos, yaw, local_v):
    return base_pos + rotate_y(local_v, yaw)


def world_axis(yaw, local_v):
    return rotate_y(local_v, yaw)

# -----------------------------
# Wolf model
# -----------------------------
class Wolf:
    def __init__(self, index, start_pos, body_color, accent_color, scale=1.0):
        self.index = index
        self.pos = vector(start_pos.x, 0, start_pos.z)
        self.vel = vector(0, 0, 1)
        self.yaw = 0.0
        self.target_yaw = 0.0
        self.phase = random.uniform(0, math.tau)
        self.scale = scale
        self.rank_offset = random.uniform(-0.3, 0.3)
        self.body_color = body_color
        self.accent_color = accent_color
        self.trail_enabled = True
        self.trail_points = []
        self.max_trail_points = 34
        self.parts = []
        self.legs = []

        s = self.scale

        # Body forms. These are intentionally simple primitive clusters instead of a compound.
        self.body = ellipsoid(pos=self.pos, length=1.85 * s, height=0.64 * s, width=0.55 * s, color=body_color)
        self.chest = sphere(radius=0.34 * s, color=body_color)
        self.haunch = sphere(radius=0.35 * s, color=body_color)
        self.neck = cylinder(radius=0.16 * s, color=body_color)
        self.head = ellipsoid(length=0.55 * s, height=0.36 * s, width=0.34 * s, color=body_color)
        self.muzzle = cone(radius=0.16 * s, color=accent_color)
        self.left_ear = cone(radius=0.08 * s, color=body_color)
        self.right_ear = cone(radius=0.08 * s, color=body_color)
        self.left_eye = sphere(radius=0.027 * s, color=vector(0.04, 0.04, 0.04))
        self.right_eye = sphere(radius=0.027 * s, color=vector(0.04, 0.04, 0.04))
        self.tail = cylinder(radius=0.07 * s, color=body_color)

        self.parts.extend([
            self.body, self.chest, self.haunch, self.neck, self.head, self.muzzle,
            self.left_ear, self.right_ear, self.left_eye, self.right_eye, self.tail,
        ])

        leg_specs = [
            (-0.20, 0.50, 0.0),
            (0.20, 0.50, math.pi),
            (-0.20, -0.55, math.pi),
            (0.20, -0.55, 0.0),
        ]
        for x, z, phase in leg_specs:
            upper = cylinder(radius=0.055 * s, color=accent_color)
            lower = cylinder(radius=0.045 * s, color=accent_color)
            paw = ellipsoid(length=0.22 * s, height=0.06 * s, width=0.10 * s, color=vector(0.12, 0.12, 0.12))
            self.parts.extend([upper, lower, paw])
            self.legs.append({
                "x": x * s,
                "z": z * s,
                "phase": phase,
                "upper": upper,
                "lower": lower,
                "paw": paw,
            })

        self.trail = curve(color=vector(0.35, 0.40, 0.42), radius=0.025, opacity=0.35)
        self.animate(0.0, 1 / 60)

    def hide(self):
        for part in self.parts:
            part.visible = False
        self.trail.visible = False

    def desired_velocity(self, leader_pos, leader_dir, formation_offset, pack, tightness):
        right = vector(leader_dir.z, 0, -leader_dir.x)
        desired = leader_pos - leader_dir * formation_offset.z + right * formation_offset.x
        to_target = desired - self.pos
        follow = norm_or(to_target, leader_dir) * clamp(mag(to_target) * 0.75, 0.0, 7.5)

        separation = vector(0, 0, 0)
        for other in pack:
            if other is self:
                continue
            diff = self.pos - other.pos
            d = mag(diff)
            min_d = 1.05 * tightness
            if 0.001 < d < min_d:
                separation += norm(diff) * (min_d - d) * 6.0

        forward_pull = leader_dir * (4.3 + self.rank_offset)
        return follow + separation + forward_pull

    def update_motion(self, dt, target_vel, base_speed):
        desired_speed = clamp(mag(target_vel), 3.0, base_speed + 4.5)
        desired_dir = norm_or(target_vel, forward_from_yaw(self.yaw))
        self.vel = self.vel * 0.88 + desired_dir * desired_speed * 0.12
        self.pos += self.vel * dt

        if self.pos.x > WORLD_HALF:
            self.pos.x = -WORLD_HALF
            self.clear_trail()
        if self.pos.x < -WORLD_HALF:
            self.pos.x = WORLD_HALF
            self.clear_trail()
        if self.pos.z > WORLD_HALF:
            self.pos.z = -WORLD_HALF
            self.clear_trail()
        if self.pos.z < -WORLD_HALF:
            self.pos.z = WORLD_HALF
            self.clear_trail()

        self.target_yaw = horizontal_angle(norm_or(self.vel, vector(0, 0, 1)))
        delta = (self.target_yaw - self.yaw + math.pi) % math.tau - math.pi
        self.yaw += delta * clamp(dt * 6.0, 0, 1)

    def orient_ellipsoid(self, obj, center, yaw, forward_length, up_y=1.0):
        obj.pos = center
        obj.axis = world_axis(yaw, vector(0, 0, forward_length))
        obj.up = vector(0, up_y, 0)

    def animate(self, t, dt):
        s = self.scale
        speed_factor = clamp(mag(self.vel) / 8.0, 0.35, 1.45)
        gait = t * (7.0 + speed_factor * 5.0) + self.phase
        bob = math.sin(gait * 2.0) * 0.045 * s * speed_factor
        base = vector(self.pos.x, GROUND_Y + bob, self.pos.z)

        # Main body and head cluster.
        self.orient_ellipsoid(self.body, world_point(base, self.yaw, vector(0, 0.78 * s, 0)), self.yaw, 1.85 * s)
        self.chest.pos = world_point(base, self.yaw, vector(0, 0.82 * s, 0.53 * s))
        self.haunch.pos = world_point(base, self.yaw, vector(0, 0.78 * s, -0.58 * s))
        self.neck.pos = world_point(base, self.yaw, vector(0, 0.98 * s, 0.62 * s))
        self.neck.axis = world_axis(self.yaw, vector(0, 0.25 * s, 0.38 * s))
        self.orient_ellipsoid(self.head, world_point(base, self.yaw, vector(0, 1.28 * s, 1.03 * s)), self.yaw, 0.55 * s)
        self.muzzle.pos = world_point(base, self.yaw, vector(0, 1.23 * s, 1.24 * s))
        self.muzzle.axis = world_axis(self.yaw, vector(0, -0.02 * s, 0.36 * s))
        self.left_ear.pos = world_point(base, self.yaw, vector(-0.14 * s, 1.42 * s, 0.94 * s))
        self.left_ear.axis = world_axis(self.yaw, vector(-0.08 * s, 0.28 * s, 0.03 * s))
        self.right_ear.pos = world_point(base, self.yaw, vector(0.14 * s, 1.42 * s, 0.94 * s))
        self.right_ear.axis = world_axis(self.yaw, vector(0.08 * s, 0.28 * s, 0.03 * s))
        self.left_eye.pos = world_point(base, self.yaw, vector(-0.11 * s, 1.30 * s, 1.26 * s))
        self.right_eye.pos = world_point(base, self.yaw, vector(0.11 * s, 1.30 * s, 1.26 * s))

        tail_swing = math.sin(gait * 0.75 + self.phase) * 0.16 * s
        self.tail.pos = world_point(base, self.yaw, vector(0, 0.82 * s, -0.92 * s))
        self.tail.axis = world_axis(self.yaw, vector(tail_swing, 0.10 * s, -0.76 * s))

        # Running legs.
        for leg in self.legs:
            stride = math.sin(gait + leg["phase"]) * 0.26 * s * speed_factor
            lift = max(0.0, math.cos(gait + leg["phase"])) * 0.13 * s * speed_factor
            x = leg["x"]
            z = leg["z"]
            knee_z = z - stride * 0.28
            paw_z = z + stride

            upper_local_pos = vector(x, 0.58 * s, z)
            upper_local_axis = vector(0.025 * s, -0.34 * s, knee_z - z)
            lower_local_pos = vector(x + 0.02 * s, 0.26 * s, knee_z)
            lower_local_axis = vector(-0.02 * s, -0.30 * s + lift, paw_z - knee_z)
            paw_local_pos = vector(x, 0.02 * s + lift * 0.45, paw_z)

            leg["upper"].pos = world_point(base, self.yaw, upper_local_pos)
            leg["upper"].axis = world_axis(self.yaw, upper_local_axis)
            leg["lower"].pos = world_point(base, self.yaw, lower_local_pos)
            leg["lower"].axis = world_axis(self.yaw, lower_local_axis)
            self.orient_ellipsoid(leg["paw"], world_point(base, self.yaw, paw_local_pos), self.yaw, 0.22 * s)

        if self.trail_enabled:
            if len(self.trail_points) == 0 or mag(self.pos - self.trail_points[-1]) > 0.35:
                self.trail_points.append(vector(self.pos.x, GROUND_Y + 0.02, self.pos.z))
                if len(self.trail_points) > self.max_trail_points:
                    self.trail_points.pop(0)
                self.trail.clear()
                for p in self.trail_points:
                    self.trail.append(pos=p)
        else:
            self.clear_trail()

    def clear_trail(self):
        self.trail.clear()
        self.trail_points = []

    def set_trail_enabled(self, enabled):
        self.trail_enabled = enabled
        if not enabled:
            self.clear_trail()

# -----------------------------
# Pack setup
# -----------------------------
base_wolf_colors = [
    (vector(0.42, 0.43, 0.41), vector(0.28, 0.29, 0.28)),
    (vector(0.50, 0.49, 0.45), vector(0.31, 0.30, 0.28)),
    (vector(0.36, 0.37, 0.36), vector(0.22, 0.23, 0.23)),
    (vector(0.58, 0.56, 0.51), vector(0.38, 0.36, 0.32)),
    (vector(0.47, 0.46, 0.43), vector(0.29, 0.28, 0.26)),
    (vector(0.31, 0.32, 0.32), vector(0.19, 0.20, 0.20)),
    (vector(0.54, 0.53, 0.49), vector(0.34, 0.33, 0.30)),
]

formation_slots = [
    vector(0, 0, 0),
    vector(-1.8, 0, 2.2),
    vector(1.8, 0, 2.5),
    vector(-3.2, 0, 4.8),
    vector(3.2, 0, 5.0),
    vector(-1.1, 0, 6.9),
    vector(1.3, 0, 7.4),
]

wolves = []
leader_pos = vector(-18, 0, -20)
leader_yaw = math.radians(38)
leader_dir = forward_from_yaw(leader_yaw)
trails_enabled = True


def create_pack():
    global wolves, leader_pos, leader_yaw, leader_dir
    for w in wolves:
        w.hide()
    wolves = []
    leader_pos = vector(-18, 0, -20)
    leader_yaw = math.radians(38)
    leader_dir = forward_from_yaw(leader_yaw)
    for i in range(len(formation_slots)):
        body, accent = base_wolf_colors[i % len(base_wolf_colors)]
        slot = formation_slots[i]
        start = leader_pos - leader_dir * slot.z + vector(slot.x, 0, 0)
        wolf = Wolf(i, start, body, accent, scale=random.uniform(0.88, 1.04))
        wolf.vel = leader_dir * random.uniform(5.5, 7.0)
        wolf.set_trail_enabled(trails_enabled)
        wolves.append(wolf)

create_pack()

lead_marker = ring(pos=leader_pos + vector(0, 0.02, 0), axis=vector(0, 1, 0), radius=0.75, thickness=0.035, color=vector(0.25, 0.44, 0.70), opacity=0.40)
direction_arrow = arrow(pos=leader_pos + vector(0, 0.2, 0), axis=leader_dir * 2.0, shaftwidth=0.08, color=vector(0.25, 0.44, 0.70), opacity=0.55)

help_text = label(
    pos=vector(-42, 8.5, -36),
    text="W/S speed  A/D steer  F formation  T trails  SPACE pause  R reset  H help",
    height=14,
    color=vector(0.08, 0.10, 0.12),
    box=False,
    opacity=0,
    align="left",
)
status_text = label(
    pos=vector(-42, 6.8, -36),
    text="",
    height=13,
    color=vector(0.12, 0.14, 0.16),
    box=False,
    opacity=0,
    align="left",
)

# -----------------------------
# Controls
# -----------------------------
paused = False
base_speed = 7.2
steer_input = 0.0
formation_tight = True
show_help = True


def on_keydown(evt):
    global paused, base_speed, steer_input, formation_tight, trails_enabled, show_help
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "w":
        base_speed = clamp(base_speed + 0.8, 3.0, 14.0)
    elif key == "s":
        base_speed = clamp(base_speed - 0.8, 3.0, 14.0)
    elif key == "a":
        steer_input -= 0.18
    elif key == "d":
        steer_input += 0.18
    elif key == "f":
        formation_tight = not formation_tight
    elif key == "t":
        trails_enabled = not trails_enabled
        for w in wolves:
            w.set_trail_enabled(trails_enabled)
    elif key == "r":
        create_pack()
    elif key == "h":
        show_help = not show_help
        help_text.visible = show_help

scene.bind("keydown", on_keydown)

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
dt = 1 / 60

while True:
    rate(60)
    if paused:
        status_text.text = f"Paused | speed {base_speed:.1f} | formation {'tight' if formation_tight else 'loose'} | trails {'on' if trails_enabled else 'off'}"
        continue

    t += dt

    wander = 0.42 * math.sin(t * 0.33) + 0.16 * math.sin(t * 0.91)
    leader_yaw += (wander * 0.010 + steer_input * 0.035) * clamp(base_speed / 7.0, 0.6, 1.7)
    steer_input *= 0.84
    leader_dir = forward_from_yaw(leader_yaw)
    leader_pos += leader_dir * base_speed * dt

    wrapped = False
    if leader_pos.x > WORLD_HALF:
        leader_pos.x = -WORLD_HALF
        wrapped = True
    if leader_pos.x < -WORLD_HALF:
        leader_pos.x = WORLD_HALF
        wrapped = True
    if leader_pos.z > WORLD_HALF:
        leader_pos.z = -WORLD_HALF
        wrapped = True
    if leader_pos.z < -WORLD_HALF:
        leader_pos.z = WORLD_HALF
        wrapped = True
    if wrapped:
        for w in wolves:
            w.clear_trail()

    tightness = 1.0 if formation_tight else 1.75
    formation_scale = 1.0 if formation_tight else 1.65

    for i, wolf in enumerate(wolves):
        slot = formation_slots[i] * formation_scale
        desired = wolf.desired_velocity(leader_pos, leader_dir, slot, wolves, tightness)
        wolf.update_motion(dt, desired, base_speed)

    for wolf in wolves:
        wolf.animate(t, dt)

    lead_marker.pos = leader_pos + vector(0, 0.025, 0)
    direction_arrow.pos = leader_pos + vector(0, 0.2, 0)
    direction_arrow.axis = leader_dir * 2.2

    pack_center = vector(0, 0, 0)
    for wolf in wolves:
        pack_center += wolf.pos
    pack_center /= len(wolves)

    scene.center = scene.center * 0.985 + vector(pack_center.x, 1.7, pack_center.z) * 0.015

    status_text.text = (
        f"Pack speed {base_speed:.1f} | formation {'tight' if formation_tight else 'loose'} | "
        f"trails {'on' if trails_enabled else 'off'} | wolves {len(wolves)}"
    )
