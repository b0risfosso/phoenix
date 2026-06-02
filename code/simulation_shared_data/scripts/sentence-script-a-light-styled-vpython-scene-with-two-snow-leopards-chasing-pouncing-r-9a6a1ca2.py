"""
Snow Leopards Playing in Snow - VPython Simulation

A light-styled VPython scene with two snow leopards chasing, pouncing,
rolling, and leaving paw prints in soft snow.

Controls:
  Space : pause / resume
  R     : reset the leopards
  F     : toggle falling snow
  P     : toggle paw prints
  C     : cycle camera mode
  Up    : increase play speed
  Down  : decrease play speed

Run with:
  python snow_leopards_playing_in_snow.py
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup: light snow style
# -----------------------------
scene = canvas(
    title="Two Snow Leopards Playing in Snow",
    width=1100,
    height=720,
    background=vector(0.86, 0.92, 1.0),
    center=vector(0, 1.2, 0),
)
scene.forward = vector(-0.55, -0.28, -0.78)
scene.range = 19
scene.userspin = True
scene.userzoom = True

# Soft daylight
local_light(pos=vector(-8, 9, 5), color=vector(0.72, 0.78, 0.86))
local_light(pos=vector(8, 7, -8), color=vector(0.35, 0.42, 0.50))

SNOW = vector(0.94, 0.97, 1.0)
SNOW_BLUE = vector(0.75, 0.86, 0.96)
ICE_BLUE = vector(0.55, 0.72, 0.86)
ROCK = vector(0.45, 0.49, 0.52)
DARK = vector(0.10, 0.12, 0.14)
TAIL_TIP = vector(0.16, 0.18, 0.20)
LEOPARD_A = vector(0.82, 0.84, 0.79)
LEOPARD_B = vector(0.74, 0.79, 0.77)
SPOT = vector(0.12, 0.13, 0.13)

# Ground and snowbanks
ground = box(pos=vector(0, -0.08, 0), size=vector(42, 0.12, 30), color=SNOW)
under_shadow = box(pos=vector(0, -0.16, 0), size=vector(42, 0.04, 30), color=vector(0.72, 0.82, 0.90))

# Gentle snow mounds
mounds = []
for i in range(16):
    x = random.uniform(-19, 19)
    z = random.uniform(-13, 13)
    if abs(x) < 5 and abs(z) < 5:
        x += random.choice([-8, 8])
    mounds.append(ellipsoid(
        pos=vector(x, 0.02, z),
        size=vector(random.uniform(2.4, 6.2), random.uniform(0.22, 0.52), random.uniform(1.5, 4.6)),
        color=vector(0.90, 0.95, 1.0),
        opacity=0.72,
    ))

# Distant rocks and pine trunks for scale
for i in range(8):
    x = random.choice([-1, 1]) * random.uniform(12, 20)
    z = random.uniform(-13, 13)
    rock = ellipsoid(pos=vector(x, 0.28, z), size=vector(1.1, 0.8, 1.0), color=ROCK, opacity=0.85)
    cap = ellipsoid(pos=vector(x, 0.78, z), size=vector(1.25, 0.24, 1.1), color=SNOW, opacity=0.9)

for i in range(9):
    x = random.uniform(-20, 20)
    z = random.choice([-1, 1]) * random.uniform(11, 14.5)
    trunk = cylinder(pos=vector(x, 0, z), axis=vector(0, 2.5, 0), radius=0.12, color=vector(0.45, 0.34, 0.25))
    foliage1 = cone(pos=vector(x, 1.1, z), axis=vector(0, 2.0, 0), radius=0.95, color=vector(0.30, 0.48, 0.43))
    foliage2 = cone(pos=vector(x, 2.0, z), axis=vector(0, 1.75, 0), radius=0.72, color=vector(0.25, 0.43, 0.39))
    snowcap = cone(pos=vector(x, 2.15, z), axis=vector(0, 1.0, 0), radius=0.58, color=SNOW, opacity=0.78)

# Labels
status = label(
    pos=vector(-19.0, 6.7, -13.0),
    text="Space pause | R reset | F snow | P paw prints | C camera | ↑/↓ speed",
    height=13,
    color=vector(0.1, 0.15, 0.20),
    box=False,
    line=False,
    opacity=0,
)

# -----------------------------
# Utility functions
# -----------------------------
def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-6:
        return fallback
    return norm(v)


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def rotate_y(local, yaw):
    c = math.cos(yaw)
    s = math.sin(yaw)
    return vector(local.x * c - local.z * s, local.y, local.x * s + local.z * c)


def oval_track(t, radius_x=9.5, radius_z=6.0):
    return vector(radius_x * math.cos(t), 0, radius_z * math.sin(t))

# -----------------------------
# Snow leopard model
# -----------------------------
class SnowLeopard:
    def __init__(self, name, start_pos, body_color, accent_color, phase=0.0, scale=1.0):
        self.name = name
        self.scale = scale
        self.body_color = body_color
        self.accent_color = accent_color
        self.phase = phase
        self.pos = vector(start_pos.x, start_pos.y, start_pos.z)
        self.vel = vector(0.8, 0, 0.2)
        self.yaw = 0.0
        self.speed = 1.0
        self.state = "chase"
        self.state_timer = random.uniform(1.0, 2.0)
        self.pounce_power = 0.0
        self.roll_angle = 0.0
        self.last_print_time = -10.0
        self.parts = []
        self.local_parts = []
        self.legs = []
        self.paws = []
        self.spots = []
        self.tail_segments = []
        self.shadow = ellipsoid(pos=self.pos + vector(0, 0.025, 0), size=vector(2.4, 0.035, 1.05) * scale,
                                color=vector(0.58, 0.68, 0.76), opacity=0.30)
        self.make_body()

    def add(self, obj, local_pos, kind="part"):
        self.parts.append(obj)
        self.local_parts.append((obj, vector(local_pos.x, local_pos.y, local_pos.z), kind))
        return obj

    def make_body(self):
        s = self.scale
        # Main body and chest
        self.body = self.add(ellipsoid(size=vector(2.1, 0.78, 0.74) * s, color=self.body_color), vector(0, 0.92 * s, 0), "body")
        self.chest = self.add(ellipsoid(size=vector(0.85, 0.86, 0.78) * s, color=self.body_color * 1.04), vector(0.88 * s, 0.98 * s, 0), "body")
        self.neck = self.add(ellipsoid(size=vector(0.58, 0.48, 0.48) * s, color=self.body_color), vector(1.38 * s, 1.12 * s, 0), "body")
        self.head = self.add(ellipsoid(size=vector(0.78, 0.56, 0.54) * s, color=self.body_color), vector(1.76 * s, 1.18 * s, 0), "head")
        self.muzzle = self.add(ellipsoid(size=vector(0.35, 0.23, 0.28) * s, color=vector(0.92, 0.93, 0.88)), vector(2.16 * s, 1.12 * s, 0), "head")
        self.nose = self.add(sphere(radius=0.07 * s, color=DARK), vector(2.35 * s, 1.13 * s, 0), "head")
        self.left_eye = self.add(sphere(radius=0.04 * s, color=vector(0.03, 0.04, 0.04)), vector(2.02 * s, 1.27 * s, 0.21 * s), "head")
        self.right_eye = self.add(sphere(radius=0.04 * s, color=vector(0.03, 0.04, 0.04)), vector(2.02 * s, 1.27 * s, -0.21 * s), "head")
        self.left_ear = self.add(cone(axis=vector(0, 0.28 * s, 0), radius=0.13 * s, color=self.body_color * 0.95), vector(1.72 * s, 1.48 * s, 0.23 * s), "head")
        self.right_ear = self.add(cone(axis=vector(0, 0.28 * s, 0), radius=0.13 * s, color=self.body_color * 0.95), vector(1.72 * s, 1.48 * s, -0.23 * s), "head")

        # Legs and paws, animated independently
        for x in [-0.72, 0.70]:
            for z in [-0.30, 0.30]:
                upper = cylinder(radius=0.105 * s, color=self.body_color * 0.92)
                lower = cylinder(radius=0.085 * s, color=self.body_color * 0.96)
                paw = ellipsoid(size=vector(0.28, 0.12, 0.17) * s, color=vector(0.90, 0.92, 0.88))
                self.legs.append({"x": x * s, "z": z * s, "upper": upper, "lower": lower, "paw": paw})
                self.parts.extend([upper, lower, paw])
                self.paws.append(paw)

        # Thick curved tail segments
        for k in range(8):
            seg = sphere(radius=(0.18 - k * 0.010) * s, color=self.body_color if k < 6 else TAIL_TIP)
            self.tail_segments.append(seg)
            self.parts.append(seg)

        # Rosette-like spots on body and head
        spot_locals = []
        for k in range(34):
            x = random.uniform(-0.95, 0.95) * s
            side = random.choice([-1, 1])
            z = side * random.uniform(0.32, 0.41) * s
            y = random.uniform(0.82, 1.25) * s
            spot_locals.append(vector(x, y, z))
        for k in range(10):
            x = random.uniform(1.45, 1.95) * s
            side = random.choice([-1, 1])
            z = side * random.uniform(0.22, 0.31) * s
            y = random.uniform(1.12, 1.38) * s
            spot_locals.append(vector(x, y, z))
        for loc in spot_locals:
            spot = ellipsoid(size=vector(0.18, 0.035, 0.10) * s, color=SPOT, opacity=0.88)
            self.spots.append((spot, loc))
            self.parts.append(spot)

    def choose_state(self):
        # Friendly play states
        r = random.random()
        if r < 0.50:
            self.state = "chase"
            self.state_timer = random.uniform(1.5, 3.2)
        elif r < 0.74:
            self.state = "pounce"
            self.state_timer = random.uniform(0.65, 1.1)
            self.pounce_power = 1.0
        elif r < 0.90:
            self.state = "circle"
            self.state_timer = random.uniform(1.2, 2.2)
        else:
            self.state = "roll"
            self.state_timer = random.uniform(0.9, 1.5)
            self.roll_angle = 0.0

    def update_motion(self, dt, t, other, global_speed):
        self.state_timer -= dt
        if self.state_timer <= 0:
            self.choose_state()

        to_other = other.pos - self.pos
        flat_to_other = vector(to_other.x, 0, to_other.z)
        dist = mag(flat_to_other)
        dir_to_other = safe_norm(flat_to_other, vector(math.cos(self.yaw), 0, math.sin(self.yaw)))
        tangent = vector(-dir_to_other.z, 0, dir_to_other.x)

        # Moving play center keeps the pair roaming across the snowfield
        play_center = oval_track(0.17 * t + self.phase * 0.2, 8.2, 5.2)
        to_center = play_center - self.pos
        center_dir = safe_norm(vector(to_center.x, 0, to_center.z), dir_to_other)

        desired = vector(0, 0, 0)
        desired_speed = 1.0

        if self.state == "chase":
            # One follows while keeping space; the other veers away
            follow_bias = 1 if self.name == "A" else -1
            if follow_bias > 0:
                desired = dir_to_other * 1.2 + tangent * 0.28 + center_dir * 0.22
            else:
                desired = -dir_to_other * 0.55 + tangent * 0.85 + center_dir * 0.38
            desired_speed = 1.8 if dist > 2.2 else 1.25
        elif self.state == "pounce":
            # Short leap toward the other, then slide away
            desired = dir_to_other * 1.1 + center_dir * 0.2
            desired_speed = 2.25
        elif self.state == "circle":
            desired = tangent * 1.2 + center_dir * 0.25
            desired_speed = 1.45
        elif self.state == "roll":
            desired = tangent * 0.35 + center_dir * 0.2
            desired_speed = 0.50
            self.roll_angle += dt * 8.0

        # Avoid crowding and boundaries
        if dist < 1.45:
            desired += -dir_to_other * 1.5
        margin_push = vector(0, 0, 0)
        if self.pos.x > 18:
            margin_push.x -= 1
        if self.pos.x < -18:
            margin_push.x += 1
        if self.pos.z > 12.5:
            margin_push.z -= 1
        if self.pos.z < -12.5:
            margin_push.z += 1
        desired += margin_push * 1.6

        desired = safe_norm(desired, vector(math.cos(self.yaw), 0, math.sin(self.yaw)))
        target_vel = desired * desired_speed * global_speed
        self.vel = lerp_vec(self.vel, target_vel, clamp(dt * 2.8, 0, 1))
        self.pos += self.vel * dt
        self.pos.x = clamp(self.pos.x, -19.0, 19.0)
        self.pos.z = clamp(self.pos.z, -13.0, 13.0)

        # Snow terrain bob and pounce arc
        speed_now = mag(self.vel)
        run_bob = 0.07 * math.sin(t * 8.5 + self.phase) * clamp(speed_now / 1.8, 0, 1)
        leap = 0.0
        if self.state == "pounce":
            p = 1.0 - clamp(self.state_timer / 1.1, 0, 1)
            leap = 0.65 * math.sin(math.pi * p)
        elif self.state == "roll":
            leap = -0.12 + 0.06 * math.sin(self.roll_angle)
        self.pos.y = max(0, run_bob + leap)

        if speed_now > 0.05:
            target_yaw = math.atan2(self.vel.z, self.vel.x)
            # Smooth yaw interpolation with wrap handling
            delta = (target_yaw - self.yaw + math.pi) % (2 * math.pi) - math.pi
            self.yaw += delta * clamp(dt * 5.0, 0, 1)

    def update_parts(self, t):
        s = self.scale
        speed_factor = clamp(mag(self.vel) / 2.2, 0.25, 1.6)
        gait = t * (8.5 + 2.2 * speed_factor) + self.phase
        body_roll = 0.0
        body_dip = 0.0
        if self.state == "roll":
            body_roll = 0.32 * math.sin(self.roll_angle)
            body_dip = -0.23 * s
        elif self.state == "pounce":
            body_roll = 0.08 * math.sin(gait)
        else:
            body_roll = 0.04 * math.sin(gait)

        # Update local objects
        for obj, local, kind in self.local_parts:
            loc = vector(local.x, local.y + body_dip, local.z)
            if kind == "head":
                loc.y += 0.05 * math.sin(gait * 0.5)
                loc.z += 0.04 * math.sin(gait * 0.7 + self.phase)
            obj.pos = self.pos + rotate_y(loc, self.yaw)
            if hasattr(obj, "axis"):
                if kind == "head" and obj in [self.left_ear, self.right_ear]:
                    obj.axis = rotate_y(vector(0, 0.28 * s, 0), self.yaw)
            if isinstance(obj, ellipsoid):
                obj.axis = rotate_y(vector(obj.size.x, 0, 0), self.yaw)
                obj.up = rotate_y(vector(0, math.cos(body_roll), math.sin(body_roll)), self.yaw)

        # Legs: diagonal gait, paws kick up snow
        for idx, leg in enumerate(self.legs):
            diagonal = 0 if (idx % 2 == 0) else math.pi
            stride = math.sin(gait + diagonal)
            lift = max(0, math.sin(gait + diagonal + math.pi / 2))
            xbase = leg["x"]
            zbase = leg["z"]
            shoulder = self.pos + rotate_y(vector(xbase, 0.78 * s + body_dip, zbase), self.yaw)
            foot_local = vector(xbase + 0.26 * stride * s * speed_factor, 0.08 * s + lift * 0.22 * s, zbase)
            if self.state == "roll":
                foot_local.y = 0.45 * s + 0.18 * math.sin(gait + idx)
                foot_local.z += 0.35 * math.sin(gait + idx)
            foot = self.pos + rotate_y(foot_local, self.yaw)
            knee = (shoulder + foot) * 0.5 + rotate_y(vector(0.05 * stride * s, 0.16 * s, 0), self.yaw)
            leg["upper"].pos = shoulder
            leg["upper"].axis = knee - shoulder
            leg["lower"].pos = knee
            leg["lower"].axis = foot - knee
            leg["paw"].pos = foot + rotate_y(vector(0.02, 0, 0), self.yaw)
            leg["paw"].axis = rotate_y(vector(0.28 * s, 0, 0), self.yaw)
            leg["paw"].up = vector(0, 1, 0)

        # Tail waves like a thick balance rope
        base = vector(-1.08 * s, 1.0 * s + body_dip, 0)
        for k, seg in enumerate(self.tail_segments):
            back = -0.28 * k * s
            wave = 0.34 * math.sin(gait * 0.55 - k * 0.55 + self.phase)
            lift = 0.16 * math.sin(gait * 0.35 - k * 0.25)
            local = base + vector(back, 0.05 * k * s + lift * s, wave * s)
            seg.pos = self.pos + rotate_y(local, self.yaw)

        # Spots track sides of body/head
        for spot, loc in self.spots:
            spot.pos = self.pos + rotate_y(vector(loc.x, loc.y + body_dip, loc.z), self.yaw)
            spot.axis = rotate_y(vector(0.18 * s, 0, 0), self.yaw)
            spot.up = vector(0, 1, 0)

        self.shadow.pos = vector(self.pos.x, 0.018, self.pos.z)
        self.shadow.size = vector(2.6, 0.035, 1.05) * s * (1.0 + 0.08 * clamp(mag(self.vel), 0, 2))
        self.shadow.axis = rotate_y(vector(self.shadow.size.x, 0, 0), self.yaw)

    def leave_paw_prints(self, t, prints_enabled, paw_prints):
        if not prints_enabled:
            return
        if t - self.last_print_time < 0.22:
            return
        if mag(self.vel) < 0.35 or self.state == "roll":
            return
        self.last_print_time = t
        s = self.scale
        for side in [-1, 1]:
            forward_back = random.choice([-0.45, 0.45]) * s
            local = vector(forward_back, 0.013, side * 0.34 * s)
            p = self.pos + rotate_y(local, self.yaw)
            print_obj = ellipsoid(pos=vector(p.x, 0.016, p.z), size=vector(0.24, 0.012, 0.14) * s,
                                  color=vector(0.70, 0.80, 0.89), opacity=0.55)
            print_obj.axis = rotate_y(vector(0.24 * s, 0, 0), self.yaw)
            paw_prints.append({"obj": print_obj, "age": 0.0})

# -----------------------------
# Snow particles and puffs
# -----------------------------
snowflakes = []
for i in range(170):
    flake = sphere(
        pos=vector(random.uniform(-21, 21), random.uniform(2.0, 10.5), random.uniform(-15, 15)),
        radius=random.uniform(0.018, 0.045),
        color=SNOW,
        opacity=random.uniform(0.35, 0.75),
    )
    snowflakes.append(flake)

snow_puffs = []
paw_prints = []

def spawn_snow_puff(pos, strength=1.0):
    for _ in range(5):
        puff = sphere(
            pos=vector(pos.x, 0.08, pos.z),
            radius=random.uniform(0.035, 0.07) * strength,
            color=SNOW,
            opacity=0.65,
        )
        vel = vector(random.uniform(-0.45, 0.45), random.uniform(0.18, 0.65), random.uniform(-0.45, 0.45)) * strength
        snow_puffs.append({"obj": puff, "vel": vel, "age": 0.0, "life": random.uniform(0.45, 0.85)})

# -----------------------------
# Create the two snow leopards
# -----------------------------
leopard_a = SnowLeopard("A", vector(-3.5, 0, -1.5), LEOPARD_A, ICE_BLUE, phase=0.0, scale=1.0)
leopard_b = SnowLeopard("B", vector(3.4, 0, 1.8), LEOPARD_B, SNOW_BLUE, phase=math.pi * 0.7, scale=0.94)
leopards = [leopard_a, leopard_b]

# Play ribbons show recent paths
path_a = curve(color=vector(0.55, 0.70, 0.85), radius=0.018)
path_b = curve(color=vector(0.68, 0.76, 0.82), radius=0.018)
path_points_a = []
path_points_b = []

# -----------------------------
# Controls
# -----------------------------
paused = False
snow_enabled = True
prints_enabled = True
camera_mode = 0
play_speed = 1.0

def reset_simulation():
    global play_speed
    leopard_a.pos = vector(-3.5, 0, -1.5)
    leopard_a.vel = vector(1.2, 0, 0.2)
    leopard_a.state = "chase"
    leopard_a.state_timer = 2.0
    leopard_b.pos = vector(3.4, 0, 1.8)
    leopard_b.vel = vector(-0.8, 0, -0.2)
    leopard_b.state = "circle"
    leopard_b.state_timer = 2.0
    path_points_a.clear()
    path_points_b.clear()
    path_a.clear()
    path_b.clear()
    for item in paw_prints:
        item["obj"].visible = False
    paw_prints.clear()
    play_speed = 1.0


def keydown(evt):
    global paused, snow_enabled, prints_enabled, camera_mode, play_speed
    key = evt.key
    if key == " ":
        paused = not paused
    elif key in ["r", "R"]:
        reset_simulation()
    elif key in ["f", "F"]:
        snow_enabled = not snow_enabled
    elif key in ["p", "P"]:
        prints_enabled = not prints_enabled
    elif key in ["c", "C"]:
        camera_mode = (camera_mode + 1) % 3
    elif key == "up":
        play_speed = clamp(play_speed + 0.15, 0.3, 2.5)
    elif key == "down":
        play_speed = clamp(play_speed - 0.15, 0.3, 2.5)

scene.bind("keydown", keydown)

# -----------------------------
# Main animation loop
# -----------------------------
t = 0.0
last_puff_a = 0.0
last_puff_b = 0.0

while True:
    rate(60)
    dt = 1.0 / 60.0
    if paused:
        status.text = "PAUSED | Space resume | R reset | F snow | P paw prints | C camera | ↑/↓ speed"
        continue

    t += dt * play_speed

    # Motion and body animation
    leopard_a.update_motion(dt, t, leopard_b, play_speed)
    leopard_b.update_motion(dt, t, leopard_a, play_speed)
    for leo in leopards:
        leo.update_parts(t)
        leo.leave_paw_prints(t, prints_enabled, paw_prints)

    # Snow puffs from pounces and fast turns
    if leopard_a.state == "pounce" and t - last_puff_a > 0.16:
        spawn_snow_puff(leopard_a.pos, 1.1)
        last_puff_a = t
    if leopard_b.state == "pounce" and t - last_puff_b > 0.16:
        spawn_snow_puff(leopard_b.pos, 1.0)
        last_puff_b = t

    # Falling snow
    if snow_enabled:
        wind = vector(0.18 * math.sin(t * 0.23), 0, 0.10 * math.cos(t * 0.18))
        for flake in snowflakes:
            flake.visible = True
            flake.pos += vector(wind.x, -0.035 - flake.radius * 0.18, wind.z) * play_speed
            if flake.pos.y < 0.05:
                flake.pos = vector(random.uniform(-21, 21), random.uniform(7.0, 11.0), random.uniform(-15, 15))
    else:
        for flake in snowflakes:
            flake.visible = False

    # Snow puffs fade out
    for puff in list(snow_puffs):
        puff["age"] += dt * play_speed
        puff["vel"].y -= 0.9 * dt * play_speed
        puff["obj"].pos += puff["vel"] * dt * play_speed
        puff["obj"].opacity = max(0, 0.65 * (1 - puff["age"] / puff["life"]))
        puff["obj"].radius *= 1.012
        if puff["age"] >= puff["life"]:
            puff["obj"].visible = False
            snow_puffs.remove(puff)

    # Paw prints slowly soften into the snow
    for item in list(paw_prints):
        item["age"] += dt * play_speed
        item["obj"].opacity = max(0, 0.55 * (1 - item["age"] / 14.0))
        if item["age"] > 14.0 or len(paw_prints) > 140:
            item["obj"].visible = False
            paw_prints.remove(item)

    # Path ribbons, limited length
    path_points_a.append(vector(leopard_a.pos.x, 0.05, leopard_a.pos.z))
    path_points_b.append(vector(leopard_b.pos.x, 0.05, leopard_b.pos.z))
    if len(path_points_a) > 95:
        path_points_a.pop(0)
    if len(path_points_b) > 95:
        path_points_b.pop(0)
    path_a.clear()
    path_b.clear()
    for p in path_points_a:
        path_a.append(pos=p)
    for p in path_points_b:
        path_b.append(pos=p)

    # Camera modes
    midpoint = (leopard_a.pos + leopard_b.pos) * 0.5
    if camera_mode == 0:
        scene.center = lerp_vec(scene.center, midpoint + vector(0, 1.4, 0), 0.04)
    elif camera_mode == 1:
        scene.center = lerp_vec(scene.center, leopard_a.pos + vector(0, 1.15, 0), 0.05)
    else:
        scene.center = lerp_vec(scene.center, vector(0, 1.1, 0), 0.03)

    # Status text
    status.pos = scene.center + vector(-18.2, 5.5, -11.8)
    status.text = (
        f"Two snow leopards playing | A: {leopard_a.state} | B: {leopard_b.state} | "
        f"speed {play_speed:.2f} | snow {'on' if snow_enabled else 'off'} | prints {'on' if prints_enabled else 'off'}"
    )
