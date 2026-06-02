from vpython import *
import math
import random

# ------------------------------------------------------------
# Otago Underwater Descent - longer hunting rounds
# A yellow-eyed penguin descends through kelp shadows, pressure
# layers, bubbles, drifting plankton, and an evasive prey field.
# ------------------------------------------------------------

scene.title = "Otago Underwater Descent - Longer Feeding Rounds"
scene.width = 1200
scene.height = 760
scene.background = vector(0.82, 0.94, 0.98)
scene.forward = vector(-0.22, -0.18, -1)
scene.center = vector(0, -8, 0)
scene.range = 18

local_light(pos=vector(-8, 8, 10), color=vector(0.75, 0.9, 1.0))
local_light(pos=vector(10, -16, -8), color=vector(0.25, 0.55, 0.75))

SEA_TOP = 5.5
SEA_BOTTOM = -24.0
DEPTH_SPAN = SEA_TOP - SEA_BOTTOM
FIELD_X_LIMIT = 17
FIELD_Z_LIMIT = 8.5
random.seed(31)

# ----------------------------
# World
# ----------------------------
surface = box(pos=vector(0, SEA_TOP, 0), size=vector(38, 0.08, 20), color=vector(0.72, 0.90, 0.98), opacity=0.45)
label(pos=vector(-15.5, SEA_TOP + 0.8, 0), text="surface", box=False, color=vector(0.15, 0.35, 0.45), height=13)
seafloor = box(pos=vector(0, SEA_BOTTOM - 0.35, 0), size=vector(40, 0.7, 22), color=vector(0.60, 0.72, 0.55), opacity=0.62)

pressure_layers = []
for i in range(7):
    y = SEA_TOP - (i + 1) * (DEPTH_SPAN / 8.0)
    pressure_layers.append(box(pos=vector(0, y, 0), size=vector(38, 0.18, 20),
                               color=vector(0.38, 0.66 - i * 0.035, 0.84 - i * 0.055),
                               opacity=0.10 + i * 0.025))

ruler = cylinder(pos=vector(-17, SEA_BOTTOM, -8.5), axis=vector(0, DEPTH_SPAN, 0), radius=0.025, color=vector(0.2, 0.45, 0.55))
for mark in range(0, 31, 5):
    y = SEA_TOP - (mark / 30.0) * DEPTH_SPAN
    cylinder(pos=vector(-17.35, y, -8.5), axis=vector(0.7, 0, 0), radius=0.018, color=vector(0.2, 0.45, 0.55))
    label(pos=vector(-18.4, y, -8.5), text=f"{mark} m", box=False, height=9, color=vector(0.16, 0.34, 0.42))

# Kelp forest and shadows
kelp_stems = []
kelp_leaves = []
for i in range(30):
    x = random.uniform(-15, 15)
    z = random.uniform(-8, 8)
    base_y = SEA_BOTTOM + random.uniform(0.0, 1.0)
    h = random.uniform(10, 21)
    stem = curve(color=vector(0.16, 0.45, 0.25), radius=random.uniform(0.035, 0.06))
    stem.phase = random.uniform(0, math.tau)
    stem.base_x = x
    stem.base_z = z
    stem.base_y = base_y
    stem.height = h
    stem.points_count = 9
    for k in range(stem.points_count):
        u = k / (stem.points_count - 1)
        stem.append(vector(x, base_y + u * h, z))
    kelp_stems.append(stem)

    for j in range(3):
        side = random.choice([-1, 1])
        leaf_y = base_y + random.uniform(0.30, 0.90) * h
        leaf = ellipsoid(pos=vector(x + side * random.uniform(0.25, 0.55), leaf_y, z),
                         size=vector(0.14, random.uniform(0.7, 1.3), 0.38),
                         color=vector(0.12, 0.38, 0.19), opacity=0.55)
        leaf.phase = stem.phase + random.uniform(-0.5, 0.5)
        leaf.base = vector(leaf.pos.x, leaf_y, z)
        kelp_leaves.append(leaf)

shadow_curtains = []
for i in range(10):
    curtain = box(pos=vector(random.uniform(-14, 14), random.uniform(-14, 2), random.uniform(-8, 8)),
                  size=vector(random.uniform(1.2, 2.4), random.uniform(9, 17), 0.06),
                  color=vector(0.05, 0.18, 0.21), opacity=0.075)
    curtain.phase = random.uniform(0, math.tau)
    shadow_curtains.append(curtain)

# ----------------------------
# Penguin model
# ----------------------------
penguin = compound([
    ellipsoid(pos=vector(0, 0, 0), size=vector(1.0, 1.9, 0.78), color=vector(0.08, 0.10, 0.12)),
    ellipsoid(pos=vector(0, -0.03, -0.04), size=vector(0.62, 1.45, 0.42), color=vector(0.94, 0.93, 0.82)),
    sphere(pos=vector(0, 1.02, 0), radius=0.38, color=vector(0.08, 0.10, 0.12)),
    cone(pos=vector(0, 1.03, -0.38), axis=vector(0, 0, -0.46), radius=0.12, color=vector(0.88, 0.52, 0.18)),
    ellipsoid(pos=vector(-0.32, 1.12, -0.26), size=vector(0.13, 0.05, 0.05), color=vector(0.92, 0.82, 0.12)),
    ellipsoid(pos=vector(0.32, 1.12, -0.26), size=vector(0.13, 0.05, 0.05), color=vector(0.92, 0.82, 0.12)),
    sphere(pos=vector(-0.16, 1.08, -0.32), radius=0.035, color=color.black),
    sphere(pos=vector(0.16, 1.08, -0.32), radius=0.035, color=color.black),
    ellipsoid(pos=vector(-0.68, -0.05, 0), size=vector(0.26, 1.25, 0.16), color=vector(0.06, 0.09, 0.11)),
    ellipsoid(pos=vector(0.68, -0.05, 0), size=vector(0.26, 1.25, 0.16), color=vector(0.06, 0.09, 0.11)),
    cone(pos=vector(-0.23, -0.98, 0), axis=vector(-0.32, -0.22, 0), radius=0.10, color=vector(0.95, 0.62, 0.20)),
    cone(pos=vector(0.23, -0.98, 0), axis=vector(0.32, -0.22, 0), radius=0.10, color=vector(0.95, 0.62, 0.20)),
])
penguin.pos = vector(-12, SEA_TOP - 0.8, 0)
penguin.axis = vector(0.8, -1.0, 0)
penguin.scale = vector(1.05, 1.05, 1.05)
left_flipper = ellipsoid(pos=penguin.pos + vector(-0.7, -0.05, 0), size=vector(0.22, 1.18, 0.13), color=vector(0.05, 0.08, 0.10))
right_flipper = ellipsoid(pos=penguin.pos + vector(0.7, -0.05, 0), size=vector(0.22, 1.18, 0.13), color=vector(0.05, 0.08, 0.10))
trail = curve(color=vector(0.25, 0.55, 0.75), radius=0.035)

# ----------------------------
# Particles and prey
# ----------------------------
bubbles = []
for i in range(70):
    b = sphere(pos=vector(random.uniform(-13, 15), random.uniform(SEA_BOTTOM + 2, SEA_TOP - 0.5), random.uniform(-8, 8)),
               radius=random.uniform(0.04, 0.15), color=vector(0.88, 0.97, 1.0), opacity=random.uniform(0.25, 0.55))
    b.speed = random.uniform(0.025, 0.085)
    b.drift = random.uniform(-0.014, 0.014)
    bubbles.append(b)

plankton = []
for i in range(140):
    p = sphere(pos=vector(random.uniform(-16, 16), random.uniform(SEA_BOTTOM + 2, SEA_TOP - 1), random.uniform(-8.5, 8.5)),
               radius=random.uniform(0.025, 0.055), color=vector(0.78, 0.92, 0.50), opacity=random.uniform(0.35, 0.72))
    p.phase = random.uniform(0, math.tau)
    p.speed = random.uniform(0.005, 0.02)
    plankton.append(p)

prey = []
for i in range(46):
    fish = ellipsoid(pos=vector(random.uniform(7.5, 14.5), random.uniform(-19.5, -10.5), random.uniform(-6.0, 6.0)),
                     size=vector(0.36, 0.085, 0.13), color=vector(0.70, 0.82, 0.88), opacity=0.95)
    fish.phase = random.uniform(0, math.tau)
    fish.speed = random.uniform(0.65, 1.25)
    fish.vel = vector(random.uniform(-0.025, 0.025), random.uniform(-0.012, 0.012), random.uniform(-0.025, 0.025))
    fish.alive = True
    fish.respawn_timer = 0.0
    fish.flash_timer = 0.0
    prey.append(fish)

prey_field_ring = ring(pos=vector(10.8, -15.5, 0), axis=vector(0, 1, 0), radius=4.2, thickness=0.025,
                       color=vector(0.45, 0.72, 0.84), opacity=0.35)

catch_bursts = []
for i in range(12):
    s = sphere(pos=vector(0, -40, 0), radius=0.06, color=vector(1.0, 0.86, 0.34), opacity=0.0)
    s.vel = vector(0, 0, 0)
    s.life = 0.0
    catch_bursts.append(s)

# ----------------------------
# Labels and dashboard
# ----------------------------
status = label(pos=vector(0, 7.5, 0), text="Otago underwater descent", box=False, height=18, color=vector(0.08, 0.23, 0.30))
mode_label = label(pos=vector(7.5, 6.4, 0), text="Mode: surface slip", box=True, border=6, height=12,
                   color=vector(0.05, 0.20, 0.25), background=vector(0.88, 0.96, 0.98))
round_label = label(pos=vector(-7.5, 6.4, 0), text="Round 1", box=True, border=6, height=12,
                    color=vector(0.05, 0.20, 0.25), background=vector(0.88, 0.96, 0.98))

box(pos=vector(15.8, -9.2, -8.5), size=vector(0.20, 27.5, 0.20), color=vector(0.80, 0.88, 0.90), opacity=0.65)
depth_bar = box(pos=vector(15.8, SEA_TOP, -8.5), size=vector(0.32, 0.1, 0.32), color=vector(0.10, 0.55, 0.80), opacity=0.9)
depth_label = label(pos=vector(14.1, 5.6, -8.5), text="depth 0 m", box=False, height=11, color=vector(0.05, 0.25, 0.35))
pressure_label = label(pos=vector(13.8, 4.5, -8.5), text="pressure 1.0 atm", box=False, height=11, color=vector(0.05, 0.25, 0.35))
catch_label = label(pos=vector(0, -25.8, 0), text="caught fish: 0", box=False, height=12, color=vector(0.08, 0.25, 0.30))
controls_label = label(pos=vector(0, -27.2, 0), text="Keys: space pause | f follow camera | t trail | r new round | 1 slow | 2 normal | 3 fast", box=False, height=11, color=vector(0.08, 0.25, 0.30))

# ----------------------------
# Round controller
# ----------------------------
DIVE_STYLES = [
    {"name": "deep kelp glide", "target_depth": -19.0, "hunt_x": 9.0, "weave": 1.0, "speed": 0.80, "linger": 23.0},
    {"name": "zigzag chase", "target_depth": -15.5, "hunt_x": 8.0, "weave": 2.2, "speed": 1.03, "linger": 28.0},
    {"name": "steep feeding plunge", "target_depth": -21.2, "hunt_x": 10.0, "weave": 1.5, "speed": 1.18, "linger": 19.0},
    {"name": "slow shadow stalk", "target_depth": -13.8, "hunt_x": 6.5, "weave": 0.75, "speed": 0.68, "linger": 32.0},
    {"name": "looping pursuit", "target_depth": -17.6, "hunt_x": 7.2, "weave": 2.6, "speed": 0.92, "linger": 30.0},
]

round_number = 0
round_time = 0.0
round_duration = 72.0
current_style = None
catch_count = 0
last_penguin_pos = vector(-12, SEA_TOP - 0.8, 0)
penguin_vel = vector(0.1, -0.1, 0)
active_target = None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-6:
        return fallback
    return norm(v)


def reset_fish(fish, near_field=True):
    if near_field:
        fish.pos = current_style["prey_center"] + vector(random.uniform(-4.0, 4.0), random.uniform(-2.2, 2.2), random.uniform(-3.8, 3.8))
    else:
        fish.pos = vector(random.uniform(6.5, 14.8), random.uniform(-20.5, -10.0), random.uniform(-6.8, 6.8))
    fish.vel = vector(random.uniform(-0.035, 0.035), random.uniform(-0.014, 0.014), random.uniform(-0.035, 0.035))
    fish.alive = True
    fish.visible = True
    fish.opacity = 0.95
    fish.color = vector(0.70, 0.82, 0.88)
    fish.flash_timer = 0.0


def start_new_round():
    global round_number, round_time, round_duration, current_style, catch_count, last_penguin_pos, penguin_vel, active_target
    round_number += 1
    round_time = 0.0
    style = dict(random.choice(DIVE_STYLES))
    style["phase"] = random.uniform(0, math.tau)
    style["prey_center"] = vector(random.uniform(7.7, 11.8), style["target_depth"] + random.uniform(-1.0, 1.2), random.uniform(-1.2, 1.2))
    style["entry_z"] = random.uniform(-2.2, 2.2)
    style["exit_z"] = random.uniform(-2.5, 2.5)
    current_style = style
    round_duration = 18.0 + style["linger"] + 22.0 + random.uniform(6.0, 12.0)  # longer full dive cycles
    catch_count = 0
    active_target = None
    last_penguin_pos = vector(-12.8, SEA_TOP - 0.7, style["entry_z"])
    penguin_vel = vector(0.08, -0.08, 0)
    penguin.pos = last_penguin_pos
    trail.clear()
    for fish in prey:
        reset_fish(fish, near_field=True)
    round_label.text = f"Round {round_number}: {style['name']}"


start_new_round()


def phase_name(u):
    if u < 0.22:
        return "surface slip"
    if u < 0.43:
        return "varied descent"
    if u < 0.77:
        return "linger-and-chase"
    if u < 0.91:
        return "return arc"
    return "surface recovery"


def scripted_target_position(rt):
    u = rt / round_duration
    style = current_style
    descent_end = 0.43 * round_duration
    hunt_end = 0.77 * round_duration
    return_end = round_duration

    if rt < descent_end:
        q = rt / descent_end
        ease = 0.5 - 0.5 * math.cos(math.pi * q)
        x = -12.8 + (style["hunt_x"] + 12.8) * ease
        y = SEA_TOP - 0.7 + (style["target_depth"] - (SEA_TOP - 0.7)) * ease
        z = style["entry_z"] + style["weave"] * math.sin(q * math.tau * (1.1 + 0.25 * style["speed"]) + style["phase"])
        z += 0.45 * math.sin(q * math.tau * 3.0 + style["phase"] * 0.5)
        return vector(x, y, z)

    if rt < hunt_end:
        q = (rt - descent_end) / max(0.01, (hunt_end - descent_end))
        center = style["prey_center"] + vector(0.7 * math.sin(rt * 0.18), 0.45 * math.sin(rt * 0.23), 0.6 * math.cos(rt * 0.17))
        # If a fish is being pursued, the penguin lingers around the fish instead of following a fixed path.
        target = choose_target_fish()
        if target is not None:
            lead = target.pos + target.vel * 11.0
            loop = vector(0.55 * math.sin(rt * 1.1 + style["phase"]), 0.25 * math.sin(rt * 0.7), 0.55 * math.cos(rt * 1.0))
            return lead + loop
        loop_radius = 2.2 + 0.7 * math.sin(q * math.tau * 2)
        return center + vector(loop_radius * math.cos(rt * 0.55 * style["speed"] + style["phase"]),
                               0.9 * math.sin(rt * 0.42 + style["phase"]),
                               loop_radius * math.sin(rt * 0.70 * style["speed"]))

    q = (rt - hunt_end) / max(0.01, (return_end - hunt_end))
    ease = 0.5 - 0.5 * math.cos(math.pi * q)
    start = style["prey_center"] + vector(1.5, 0.2, 0)
    x = start.x + (-11.5 - start.x) * ease
    y = style["target_depth"] + ((SEA_TOP - 0.9) - style["target_depth"]) * ease
    z = style["exit_z"] + 1.2 * math.sin(q * math.tau * 1.6 + style["phase"])
    return vector(x, y, z)


def choose_target_fish():
    global active_target
    if active_target is not None and active_target.alive and mag(active_target.pos - penguin.pos) < 6.5:
        return active_target
    best = None
    best_dist = 999
    for fish in prey:
        if not fish.alive:
            continue
        d = mag(fish.pos - penguin.pos)
        if d < best_dist:
            best = fish
            best_dist = d
    if best is not None and best_dist < 7.0:
        active_target = best
    elif random.random() < 0.015:
        active_target = best
    return active_target


def trigger_catch_burst(pos):
    for s in catch_bursts:
        s.life = random.uniform(0.5, 1.0)
        s.pos = pos + vector(random.uniform(-0.18, 0.18), random.uniform(-0.12, 0.12), random.uniform(-0.18, 0.18))
        s.vel = vector(random.uniform(-0.07, 0.07), random.uniform(0.02, 0.12), random.uniform(-0.07, 0.07))
        s.opacity = 0.85
        s.radius = random.uniform(0.045, 0.095)


def update_penguin(dt):
    global last_penguin_pos, penguin_vel, active_target, catch_count
    target = scripted_target_position(round_time)
    to_target = target - penguin.pos
    desired_speed = 0.10 * current_style["speed"]
    if phase_name(round_time / round_duration) == "linger-and-chase":
        desired_speed = 0.145 * current_style["speed"]
        if active_target is not None and active_target.alive and mag(active_target.pos - penguin.pos) < 2.9:
            desired_speed = 0.20 * current_style["speed"]
    desired_vel = safe_norm(to_target, penguin_vel) * desired_speed
    penguin_vel = penguin_vel * 0.84 + desired_vel * 0.16
    last_penguin_pos = vector(penguin.pos.x, penguin.pos.y, penguin.pos.z)
    penguin.pos += penguin_vel * (dt / 0.05)
    penguin.pos.x = clamp(penguin.pos.x, -14.5, 14.5)
    penguin.pos.y = clamp(penguin.pos.y, SEA_BOTTOM + 1.8, SEA_TOP - 0.25)
    penguin.pos.z = clamp(penguin.pos.z, -7.5, 7.5)
    direction = safe_norm(penguin.pos - last_penguin_pos, vector(1, -0.4, 0))
    penguin.axis = direction

    side_vec = cross(direction, vector(0, 1, 0))
    if mag(side_vec) < 0.1:
        side_vec = vector(1, 0, 0)
    else:
        side_vec = norm(side_vec)
    beat_rate = 7.0 if phase_name(round_time / round_duration) != "linger-and-chase" else 11.5
    beat_amp = 0.28 if phase_name(round_time / round_duration) != "linger-and-chase" else 0.52
    beat = math.sin(round_time * beat_rate) * beat_amp
    left_flipper.pos = penguin.pos - side_vec * 0.70 + vector(0, -0.03, 0)
    right_flipper.pos = penguin.pos + side_vec * 0.70 + vector(0, -0.03, 0)
    left_flipper.axis = vector(-0.1, -1, beat)
    right_flipper.axis = vector(0.1, -1, -beat)

    if getattr(trail, "npoints", 0) > 230:
        try:
            trail.pop(0)
        except Exception:
            pass
    trail.append(penguin.pos)

    # Catch fish when close enough during hunting. Catch probability increases during burst pursuit.
    for fish in prey:
        if not fish.alive:
            continue
        dist = mag(fish.pos - penguin.pos)
        if dist < 0.63 and phase_name(round_time / round_duration) == "linger-and-chase":
            if random.random() < 0.60:
                fish.alive = False
                fish.visible = False
                fish.respawn_timer = random.uniform(6.0, 12.0)
                catch_count += 1
                active_target = None
                trigger_catch_burst(fish.pos)
                break

    return direction


def update_kelp(t):
    for stem in kelp_stems:
        stem.clear()
        for k in range(stem.points_count):
            u = k / (stem.points_count - 1)
            sway = math.sin(t * 0.75 + stem.phase + u * 2.2) * 0.18 * u
            stem.append(vector(stem.base_x + sway, stem.base_y + u * stem.height, stem.base_z + 0.06 * math.sin(t + u)))
    for leaf in kelp_leaves:
        leaf.pos = leaf.base + vector(0.20 * math.sin(t * 0.9 + leaf.phase), 0, 0.07 * math.cos(t * 0.7 + leaf.phase))
    for curtain in shadow_curtains:
        curtain.pos.x += 0.010 * math.sin(t * 0.5 + curtain.phase)
        curtain.opacity = 0.055 + 0.035 * (0.5 + 0.5 * math.sin(t * 0.8 + curtain.phase))


def update_particles(t):
    for b in bubbles:
        b.pos.y += b.speed
        b.pos.x += b.drift + 0.009 * math.sin(t + b.pos.z)
        if mag(b.pos - penguin.pos) < 1.8:
            b.pos.y += 0.15
            b.opacity = min(0.72, b.opacity + 0.012)
        if b.pos.y > SEA_TOP + 0.3:
            b.pos.y = random.uniform(SEA_BOTTOM + 1, SEA_BOTTOM + 6)
            b.pos.x = random.uniform(-15, 15)
            b.pos.z = random.uniform(-8, 8)
            b.opacity = random.uniform(0.25, 0.55)

    for p in plankton:
        p.pos.x += p.speed * math.sin(t * 0.6 + p.phase)
        p.pos.z += p.speed * math.cos(t * 0.5 + p.phase)
        p.pos.y += 0.004 * math.sin(t * 0.8 + p.phase)
        if p.pos.x > FIELD_X_LIMIT:
            p.pos.x = -FIELD_X_LIMIT
        if p.pos.x < -FIELD_X_LIMIT:
            p.pos.x = FIELD_X_LIMIT
        if mag(p.pos - penguin.pos) < 1.4:
            p.color = vector(0.95, 0.96, 0.65)
            p.opacity = 0.85
        else:
            p.color = vector(0.78, 0.92, 0.50)
            p.opacity = max(0.35, p.opacity * 0.995)


def update_prey(dt):
    center = current_style["prey_center"] + vector(0.9 * math.sin(round_time * 0.22), 0.45 * math.sin(round_time * 0.27), 0.8 * math.cos(round_time * 0.19))
    prey_field_ring.pos = center
    prey_field_ring.radius = 3.7 + 0.35 * math.sin(round_time * 0.9)

    for i, fish in enumerate(prey):
        if not fish.alive:
            fish.respawn_timer -= dt
            if fish.respawn_timer <= 0:
                reset_fish(fish, near_field=True)
            continue

        # Schooling target around the field.
        phase = fish.phase + round_time * 0.45 * fish.speed
        school_target = center + vector(3.2 * math.cos(phase + i * 0.21),
                                        1.2 * math.sin(phase * 0.8),
                                        2.8 * math.sin(phase + i * 0.13))
        desired = (school_target - fish.pos) * 0.012

        # Evasion: fish turn away from the penguin, juke sideways, and brighten.
        away = fish.pos - penguin.pos
        d = mag(away)
        if d < 5.5:
            flee = safe_norm(away, vector(1, 0, 0)) * (0.040 * (1.0 - d / 5.5) + 0.012)
            lateral = cross(safe_norm(away, vector(1, 0, 0)), vector(0, 1, 0))
            if mag(lateral) < 0.1:
                lateral = vector(0, 0, 1)
            else:
                lateral = norm(lateral)
            juke = lateral * (0.022 * math.sin(round_time * 7.0 + fish.phase))
            desired += flee + juke
            fish.color = vector(0.95, 0.72, 0.44)
            fish.flash_timer = 0.35
        elif fish.flash_timer > 0:
            fish.flash_timer -= dt
            fish.color = vector(0.88, 0.79, 0.58)
        else:
            fish.color = vector(0.70, 0.82, 0.88)

        fish.vel = fish.vel * 0.91 + desired * 0.09
        # Keep movement alive but bounded.
        if mag(fish.vel) > 0.105:
            fish.vel = norm(fish.vel) * 0.105
        fish.pos += fish.vel * (dt / 0.05)

        if fish.pos.x > FIELD_X_LIMIT or fish.pos.x < -FIELD_X_LIMIT:
            fish.vel.x *= -0.8
            fish.pos.x = clamp(fish.pos.x, -FIELD_X_LIMIT, FIELD_X_LIMIT)
        if fish.pos.z > FIELD_Z_LIMIT or fish.pos.z < -FIELD_Z_LIMIT:
            fish.vel.z *= -0.8
            fish.pos.z = clamp(fish.pos.z, -FIELD_Z_LIMIT, FIELD_Z_LIMIT)
        if fish.pos.y > SEA_TOP - 1.0 or fish.pos.y < SEA_BOTTOM + 1.5:
            fish.vel.y *= -0.8
            fish.pos.y = clamp(fish.pos.y, SEA_BOTTOM + 1.5, SEA_TOP - 1.0)

        fish.axis = safe_norm(fish.vel, vector(1, 0, 0))


def update_catch_bursts(dt):
    for s in catch_bursts:
        if s.life > 0:
            s.life -= dt
            s.pos += s.vel * (dt / 0.05)
            s.opacity = max(0.0, s.life)
            s.radius *= 0.992
        else:
            s.opacity = 0.0
            s.pos.y = -40


def update_dashboard():
    depth_m = int(round(clamp((SEA_TOP - penguin.pos.y) / DEPTH_SPAN, 0, 1) * 30))
    pressure_atm = 1.0 + depth_m / 10.0
    depth_fraction = clamp((SEA_TOP - penguin.pos.y) / DEPTH_SPAN, 0, 1)
    depth_bar.pos.y = SEA_TOP - depth_fraction * DEPTH_SPAN
    depth_bar.size.y = 0.2 + depth_fraction * DEPTH_SPAN
    depth_label.text = f"depth {depth_m} m"
    pressure_label.text = f"pressure {pressure_atm:.1f} atm"
    mode_label.text = "Mode: " + phase_name(round_time / round_duration)
    catch_label.text = f"caught fish: {catch_count} | remaining prey: {sum(1 for f in prey if f.alive)} | round length: {int(round_duration)}s"


# Keyboard controls
paused = False
follow_camera = True
show_trail = True
speed_multiplier = 1.0


def keydown(evt):
    global paused, follow_camera, show_trail, speed_multiplier
    key = evt.key
    if key == " ":
        paused = not paused
    elif key == "f":
        follow_camera = not follow_camera
    elif key == "t":
        show_trail = not show_trail
        trail.visible = show_trail
    elif key == "r":
        start_new_round()
    elif key == "1":
        speed_multiplier = 0.55
    elif key == "2":
        speed_multiplier = 1.0
    elif key == "3":
        speed_multiplier = 1.75

scene.bind("keydown", keydown)

# ----------------------------
# Main loop
# ----------------------------
t = 0.0
while True:
    rate(60)
    if paused:
        continue

    dt = 0.05 * speed_multiplier
    t += dt
    round_time += dt
    if round_time >= round_duration:
        start_new_round()

    update_penguin(dt)
    update_kelp(t)
    update_particles(t)
    update_prey(dt)
    update_catch_bursts(dt)
    update_dashboard()

    for idx, layer in enumerate(pressure_layers):
        distance = abs(layer.pos.y - penguin.pos.y)
        layer.opacity = 0.08 + idx * 0.018 + max(0, 0.10 * (1.0 - distance / 2.5))

    if follow_camera:
        scene.center = vector(penguin.pos.x * 0.25, penguin.pos.y - 1.0, 0)
