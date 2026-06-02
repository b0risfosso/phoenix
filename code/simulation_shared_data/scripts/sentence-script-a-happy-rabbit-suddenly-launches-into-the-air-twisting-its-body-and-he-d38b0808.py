"""
Binky Joy Leap

Story:
    A rabbit will binky when it feels really happy or excited. The behavior
    involves a high jump into the air while twisting its body and head at the
    same time.

Simulation seed:
    A happy rabbit suddenly launches into the air, twisting its body and head
    mid-jump as visible joy pulses ripple outward through the meadow.

Controls:
    Mouse       : drag / scroll to control camera
    Space       : pause / resume
    B           : trigger an extra binky
    R           : reset simulation
    C           : toggle camera follow
    J           : toggle joy ripples
    F           : toggle flowers/butterflies
    Up / W      : increase energy/speed
    Down / S    : decrease energy/speed

Run:
    python binky_joy_leap.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

scene = canvas(
    title="Binky Joy Leap",
    width=1200,
    height=780,
    background=vector(0.86, 0.94, 1.0),
    center=vector(0, 1.2, 0),
)
scene.forward = vector(-0.52, -0.30, -0.80)
scene.up = vector(0, 1, 0)
scene.range = 9.2
scene.userspin = True
scene.userzoom = True
scene.userpan = True


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def rotate_y(v, angle):
    ca = math.cos(angle)
    sa = math.sin(angle)
    return vector(v.x * ca - v.z * sa, v.y, v.x * sa + v.z * ca)


MEADOW = vector(0.48, 0.74, 0.36)
MEADOW_LIGHT = vector(0.68, 0.86, 0.44)
DIRT = vector(0.55, 0.43, 0.28)
RABBIT_FUR = vector(0.72, 0.72, 0.68)
RABBIT_LIGHT = vector(0.90, 0.90, 0.84)
RABBIT_SHADOW = vector(0.48, 0.48, 0.46)
EAR_INNER = vector(0.95, 0.58, 0.62)
JOY_YELLOW = vector(1.0, 0.86, 0.25)
JOY_PINK = vector(1.0, 0.48, 0.74)
JOY_BLUE = vector(0.44, 0.88, 1.0)
JOY_GREEN = vector(0.44, 1.0, 0.48)

# Meadow
ground = box(pos=vector(0, -0.06, 0), size=vector(18, 0.10, 13), color=MEADOW, opacity=0.95)

meadow_patches = []
for _ in range(70):
    patch = ellipsoid(
        pos=vector(random.uniform(-8.5, 8.5), 0.015, random.uniform(-6.0, 6.0)),
        length=random.uniform(0.35, 1.25),
        height=0.025,
        width=random.uniform(0.10, 0.38),
        color=mix_color(MEADOW, MEADOW_LIGHT, random.random()),
        opacity=random.uniform(0.28, 0.65),
    )
    patch.rotate(angle=random.random() * math.tau, axis=vector(0, 1, 0), origin=patch.pos)
    meadow_patches.append({"obj": patch, "phase": random.random() * math.tau})

path_tiles = []
for i in range(18):
    x = -7.5 + i * 0.9
    z = 0.65 * math.sin(i * 0.55)
    tile = ellipsoid(
        pos=vector(x, 0.018, z),
        length=0.70,
        height=0.018,
        width=0.38,
        color=mix_color(DIRT, MEADOW, 0.25),
        opacity=0.28,
    )
    tile.rotate(angle=random.uniform(-0.5, 0.5), axis=vector(0, 1, 0), origin=tile.pos)
    path_tiles.append(tile)

flowers = []
flower_colors = [JOY_YELLOW, JOY_PINK, JOY_BLUE, vector(0.86, 0.52, 1.0), vector(1.0, 0.64, 0.30)]
for _ in range(58):
    root = vector(random.uniform(-8.0, 8.0), 0.03, random.uniform(-5.6, 5.6))
    stem = cylinder(pos=root, axis=vector(0, random.uniform(0.12, 0.28), 0), radius=0.008, color=vector(0.20, 0.50, 0.18), opacity=0.86)
    blossom = sphere(pos=root + stem.axis, radius=random.uniform(0.035, 0.075), color=random.choice(flower_colors), emissive=True, opacity=0.88)
    flowers.append({"stem": stem, "blossom": blossom, "phase": random.random() * math.tau})

butterflies = []
for _ in range(12):
    center = vector(random.uniform(-7, 7), random.uniform(0.6, 1.8), random.uniform(-5, 5))
    col = random.choice([JOY_PINK, JOY_YELLOW, JOY_BLUE])
    wing_l = ellipsoid(pos=center + vector(-0.04, 0, 0), length=0.05, height=0.14, width=0.08, color=col, opacity=0.70, emissive=True)
    wing_r = ellipsoid(pos=center + vector(0.04, 0, 0), length=0.05, height=0.14, width=0.08, color=col, opacity=0.70, emissive=True)
    butterflies.append({"left": wing_l, "right": wing_r, "center": center, "phase": random.random() * math.tau, "radius": random.uniform(0.8, 2.2), "speed": random.uniform(0.35, 0.9)})

# Rabbit
rabbit_root = vector(-2.8, 0.55, 0)
rabbit_parts = []
body = ellipsoid(pos=rabbit_root, length=1.05, height=0.58, width=0.62, color=RABBIT_FUR)
chest = ellipsoid(pos=rabbit_root + vector(0.28, 0.05, -0.02), length=0.48, height=0.44, width=0.50, color=RABBIT_LIGHT, opacity=0.95)
head = ellipsoid(pos=rabbit_root + vector(0.66, 0.30, 0), length=0.45, height=0.38, width=0.36, color=RABBIT_FUR)
muzzle = ellipsoid(pos=rabbit_root + vector(0.92, 0.25, 0), length=0.20, height=0.15, width=0.20, color=RABBIT_LIGHT)
nose = sphere(pos=rabbit_root + vector(1.035, 0.28, 0), radius=0.040, color=vector(0.40, 0.18, 0.20))
eye_l = sphere(pos=rabbit_root + vector(0.81, 0.39, -0.14), radius=0.040, color=vector(0.03, 0.025, 0.02), emissive=True)
eye_r = sphere(pos=rabbit_root + vector(0.81, 0.39, 0.14), radius=0.040, color=vector(0.03, 0.025, 0.02), emissive=True)
tail = sphere(pos=rabbit_root + vector(-0.56, 0.12, 0), radius=0.18, color=RABBIT_LIGHT)
rabbit_parts.extend([body, chest, head, muzzle, nose, eye_l, eye_r, tail])

ear_l = ellipsoid(pos=rabbit_root + vector(0.52, 0.86, -0.13), length=0.14, height=0.72, width=0.10, color=RABBIT_FUR)
ear_r = ellipsoid(pos=rabbit_root + vector(0.52, 0.86, 0.13), length=0.14, height=0.72, width=0.10, color=RABBIT_FUR)
ear_inner_l = ellipsoid(pos=rabbit_root + vector(0.545, 0.86, -0.145), length=0.055, height=0.52, width=0.030, color=EAR_INNER, opacity=0.86)
ear_inner_r = ellipsoid(pos=rabbit_root + vector(0.545, 0.86, 0.145), length=0.055, height=0.52, width=0.030, color=EAR_INNER, opacity=0.86)
rabbit_parts.extend([ear_l, ear_r, ear_inner_l, ear_inner_r])

leg_parts = []
for z in [-0.22, 0.22]:
    rear_leg = ellipsoid(pos=rabbit_root + vector(-0.26, -0.25, z), length=0.44, height=0.18, width=0.20, color=RABBIT_SHADOW)
    rear_foot = ellipsoid(pos=rabbit_root + vector(-0.48, -0.42, z), length=0.46, height=0.10, width=0.20, color=RABBIT_LIGHT)
    front_leg = cylinder(pos=rabbit_root + vector(0.38, -0.04, z * 0.72), axis=vector(0.08, -0.42, 0), radius=0.045, color=RABBIT_FUR)
    front_foot = ellipsoid(pos=rabbit_root + vector(0.46, -0.45, z * 0.72), length=0.24, height=0.08, width=0.13, color=RABBIT_LIGHT)
    leg_parts.extend([rear_leg, rear_foot, front_leg, front_foot])
rabbit_parts.extend(leg_parts)

whiskers = []
for side in [-1, 1]:
    for yoff in [-0.03, 0.03, 0.09]:
        start = rabbit_root + vector(0.98, 0.27 + yoff, side * 0.09)
        axis = vector(0.36, 0.03 * (1 if yoff > 0 else -1), side * 0.22)
        w = cylinder(pos=start, axis=axis, radius=0.006, color=vector(0.96, 0.96, 0.92), opacity=0.72)
        whiskers.append(w)
        rabbit_parts.append(w)

base_data = {}
for obj in rabbit_parts:
    base_data[obj] = {
        "offset": obj.pos - rabbit_root,
        "axis": vector(obj.axis.x, obj.axis.y, obj.axis.z) if hasattr(obj, "axis") else None,
    }

sparkles = []
for _ in range(36):
    sp = sphere(pos=rabbit_root, radius=random.uniform(0.018, 0.052), color=random.choice([JOY_YELLOW, JOY_PINK, JOY_BLUE, JOY_GREEN]), emissive=True, opacity=0.0)
    sparkles.append({"obj": sp, "angle": random.random() * math.tau, "r": random.uniform(0.6, 1.8), "height": random.uniform(0.0, 1.4), "phase": random.random() * math.tau, "speed": random.uniform(0.6, 1.6)})

joy_ripples = []
for _ in range(12):
    ripple = ring(pos=vector(0, 0.04, 0), axis=vector(0, 1, 0), radius=0.2, thickness=0.018, color=random.choice([JOY_YELLOW, JOY_PINK, JOY_BLUE, JOY_GREEN]), opacity=0.0, emissive=True)
    joy_ripples.append({"obj": ripple, "life": 0.0, "max_radius": random.uniform(1.6, 3.2)})

arc_markers = []
for i in range(18):
    marker = sphere(pos=vector(-2.8 + i * 0.18, 0.08, 0), radius=0.025, color=JOY_YELLOW, opacity=0.18, emissive=True)
    arc_markers.append(marker)

title = label(pos=vector(0, 5.2, -4.8), text="Binky Joy Leap", height=24, box=False, color=vector(0.12, 0.20, 0.11))
subtitle = label(pos=vector(0, 4.78, -4.8), text="A happy rabbit launches into the air, twisting body and head as joy ripples through the meadow.", height=12, box=False, color=vector(0.18, 0.32, 0.16))
status = label(pos=vector(-6.7, 4.08, -4.8), text="", height=12, box=True, border=8, color=vector(0.12, 0.20, 0.11), background=vector(0.94, 0.98, 0.88), opacity=0.82)
legend = label(pos=vector(6.2, 4.00, -4.8), text="Binky = high happy jump + twist\nGold/pink/cyan rings = joy pulses\nSparkles intensify during midair twist\nFlowers respond to each landing", height=12, box=True, border=8, color=vector(0.12, 0.20, 0.11), background=vector(0.94, 0.98, 0.88), opacity=0.82)

paused = False
camera_follow = False
show_ripples = True
show_flowers = True
speed = 1.0
sim_t = 0.0
binky_phase = 0.0
binky_active = True
binky_count = 0
joy_energy = 0.45
landing_point = vector(rabbit_root.x, 0.04, rabbit_root.z)


def spawn_joy_ripple(pos, strength=1.0):
    for r in joy_ripples:
        if r["life"] <= 0.02:
            r["life"] = 1.0
            r["obj"].pos = vector(pos.x, 0.055, pos.z)
            r["obj"].radius = 0.15
            r["obj"].opacity = 0.70 if show_ripples else 0.0
            r["obj"].color = random.choice([JOY_YELLOW, JOY_PINK, JOY_BLUE, JOY_GREEN])
            r["max_radius"] = random.uniform(1.8, 3.8) * strength
            return


def trigger_binky():
    global binky_phase, binky_active, binky_count, joy_energy
    if binky_phase > 0.78 or not binky_active:
        binky_phase = 0.0
        binky_active = True
        binky_count += 1
        joy_energy = clamp(joy_energy + 0.18)


def reset_sim():
    global sim_t, binky_phase, binky_active, binky_count, joy_energy, speed
    sim_t = 0.0
    binky_phase = 0.0
    binky_active = True
    binky_count = 0
    joy_energy = 0.45
    speed = 1.0
    for r in joy_ripples:
        r["life"] = 0.0
        r["obj"].opacity = 0.0


def on_keydown(evt):
    global paused, camera_follow, show_ripples, show_flowers, speed
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "b":
        trigger_binky()
    elif key == "r":
        reset_sim()
    elif key == "c":
        camera_follow = not camera_follow
    elif key == "j":
        show_ripples = not show_ripples
        for r in joy_ripples:
            r["obj"].visible = show_ripples
    elif key == "f":
        show_flowers = not show_flowers
        for fl in flowers:
            fl["stem"].visible = show_flowers
            fl["blossom"].visible = show_flowers
        for bf in butterflies:
            bf["left"].visible = show_flowers
            bf["right"].visible = show_flowers
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down", "s"):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)


def update_rabbit(root, body_twist, head_twist, squash, stretch, hop_phase):
    for obj, data in base_data.items():
        off = vector(data["offset"].x, data["offset"].y, data["offset"].z)
        local_twist = body_twist
        if obj in [head, muzzle, nose, eye_l, eye_r, ear_l, ear_r, ear_inner_l, ear_inner_r] or obj in whiskers:
            local_twist += head_twist
        if obj in leg_parts:
            off.y *= squash
            off.x += -0.12 * math.sin(math.pi * hop_phase)
        off.y *= stretch
        off = rotate_y(off, local_twist)
        side_flick = vector(0, 0, 0.10 * math.sin(math.pi * hop_phase) * math.sin(body_twist))
        obj.pos = root + off + side_flick
        if data["axis"] is not None:
            axis = rotate_y(data["axis"], local_twist)
            if obj in leg_parts:
                axis = axis + vector(0.03 * math.sin(math.pi * hop_phase), 0.10 * math.sin(math.pi * hop_phase), 0)
            obj.axis = axis
    ear_l.pos += vector(-0.05 * math.sin(head_twist), 0.05 * math.sin(math.pi * hop_phase), -0.05)
    ear_r.pos += vector(-0.05 * math.sin(head_twist), 0.05 * math.sin(math.pi * hop_phase), 0.05)
    ear_inner_l.pos = ear_l.pos + vector(0.03, -0.01, -0.015)
    ear_inner_r.pos = ear_r.pos + vector(0.03, -0.01, 0.015)


while True:
    rate(50)
    if paused:
        status.text = f"Paused\nBinkies: {binky_count}\nJoy energy: {int(joy_energy * 100)}%\nSpace resumes | R resets"
        continue

    dt = 0.018 * speed
    sim_t += dt

    if binky_active:
        binky_phase += dt * (0.42 + 0.28 * joy_energy)
        if binky_phase >= 1.0:
            binky_phase = 1.0
            binky_active = False
            binky_count += 1
            joy_energy = clamp(joy_energy + 0.06, 0, 1)
            spawn_joy_ripple(landing_point, 1.0 + joy_energy)
    else:
        if math.sin(sim_t * (0.75 + 0.45 * joy_energy)) > 0.92:
            binky_phase = 0.0
            binky_active = True

    p = binky_phase
    jump_height = 0.12 + 2.25 * math.sin(math.pi * p) ** 1.05
    forward_motion = 2.2 * p
    side_wiggle = 0.30 * math.sin(math.pi * p) * math.sin(2.0 * math.pi * p)
    root = rabbit_root + vector(forward_motion, jump_height, side_wiggle)
    if p >= 0.98:
        landing_point = vector(root.x, 0.04, root.z)

    body_twist = 1.35 * math.sin(math.pi * p) * math.sin(2.0 * math.pi * p + 0.45)
    head_twist = 0.85 * math.sin(math.pi * p) * math.sin(3.0 * math.pi * p + 1.15)
    squash = 0.82 + 0.26 * math.sin(math.pi * p)
    stretch = 0.92 + 0.22 * math.sin(math.pi * p)
    if p < 0.12:
        crouch = (0.12 - p) / 0.12
        root.y -= 0.22 * crouch
        stretch -= 0.18 * crouch
        squash += 0.12 * crouch

    update_rabbit(root, body_twist, head_twist, squash, stretch, p)

    midair = math.sin(math.pi * p)
    twist_strength = abs(body_twist) + abs(head_twist)
    for sp in sparkles:
        sp["angle"] += dt * sp["speed"] * (0.8 + 2.0 * midair)
        radius = sp["r"] * (0.65 + 0.45 * midair)
        y = root.y + sp["height"] * (0.55 + 0.45 * midair) + 0.10 * math.sin(sim_t * 3 + sp["phase"])
        sp["obj"].pos = vector(root.x + math.cos(sp["angle"]) * radius, y, root.z + math.sin(sp["angle"]) * radius)
        sparkle_pulse = 0.5 + 0.5 * math.sin(sim_t * 5.0 + sp["phase"])
        sp["obj"].opacity = 0.08 + 0.75 * midair * sparkle_pulse
        sp["obj"].radius = 0.012 + 0.060 * midair * sparkle_pulse

    for r in joy_ripples:
        if r["life"] > 0.0:
            r["life"] *= 0.935
            expansion = 1.0 - r["life"]
            r["obj"].radius = 0.20 + r["max_radius"] * expansion
            r["obj"].thickness = 0.012 + 0.026 * r["life"]
            r["obj"].opacity = (0.62 * r["life"]) if show_ripples else 0.0
        else:
            r["obj"].opacity = 0.0

    for i, marker in enumerate(arc_markers):
        q = i / max(1, len(arc_markers) - 1)
        arc_y = 0.14 + 2.10 * math.sin(math.pi * q) ** 1.05
        marker.pos = rabbit_root + vector(2.2 * q, arc_y, 0.22 * math.sin(2 * math.pi * q))
        marker.opacity = 0.08 + 0.32 * math.sin(math.pi * q) * (0.4 + 0.6 * midair)
        marker.radius = 0.018 + 0.025 * math.sin(math.pi * q)

    for fl in flowers:
        dist = mag(vector(fl["blossom"].pos.x, 0, fl["blossom"].pos.z) - vector(landing_point.x, 0, landing_point.z))
        wave = max(0.0, math.sin(sim_t * 2.4 - dist * 1.5))
        joy_response = joy_energy * wave * 0.22
        fl["blossom"].radius = 0.040 + 0.050 * joy_response + 0.015 * math.sin(sim_t * 1.6 + fl["phase"]) ** 2
        fl["blossom"].opacity = 0.68 + 0.30 * joy_response

    for patch in meadow_patches:
        patch["obj"].opacity = 0.25 + 0.38 * math.sin(sim_t * 0.9 + patch["phase"]) ** 2

    for bf in butterflies:
        bf["phase"] += dt * bf["speed"] * (0.8 + joy_energy + midair)
        c = bf["center"] + vector(math.cos(bf["phase"]) * bf["radius"], 0.22 * math.sin(bf["phase"] * 1.7), math.sin(bf["phase"]) * bf["radius"] * 0.65)
        flap = 0.5 + 0.5 * math.sin(sim_t * 12.0 + bf["phase"])
        bf["left"].pos = c + vector(-0.045 - 0.04 * flap, 0, 0)
        bf["right"].pos = c + vector(0.045 + 0.04 * flap, 0, 0)
        bf["left"].height = 0.10 + 0.08 * flap
        bf["right"].height = 0.10 + 0.08 * flap
        bf["left"].opacity = 0.50 + 0.35 * flap
        bf["right"].opacity = 0.50 + 0.35 * flap

    if camera_follow:
        scene.center = root + vector(0.2, 0.75, 0)
        scene.forward = safe_norm(root - vector(5.4, 3.4, 6.8))
        scene.range = 6.0

    leap_state = "launching"
    if 0.25 < p < 0.78:
        leap_state = "twisting midair"
    elif p >= 0.78:
        leap_state = "landing joy ripple"
    if not binky_active:
        leap_state = "happy reset bounce"

    status.text = (
        f"Binky state: {leap_state}\n"
        f"Binky phase: {int(p * 100)}%\n"
        f"Binkies completed: {binky_count}\n"
        f"Joy energy: {int(joy_energy * 100)}%\n"
        f"Twist strength: {int(clamp(twist_strength / 2.0) * 100)}%\n"
        f"Joy ripples: {'on' if show_ripples else 'off'} | Meadow life: {'on' if show_flowers else 'off'}\n"
        f"Camera: {'follow' if camera_follow else 'mouse'} | Speed: {speed:.2f}x\n"
        "Mouse camera | Space pause | B binky | R reset | C follow | J ripples | F flowers"
    )
