from vpython import *
import random
import math

# Never-Give-Up Climber
# A VPython simulation based on:
# INDOMITABLE — The Never-Give-Up Climber
# A figure climbs an impossible mountain where wind, ice, loose rocks, and fatigue
# push it backward, yet each fall teaches it a stronger route upward.

scene = canvas(
    title="The Never-Give-Up Climber",
    width=1180,
    height=720,
    background=vector(0.82, 0.91, 1.0),
    center=vector(0, 5, 0),
    range=16,
)
scene.forward = vector(-0.18, -0.18, -1)
scene.userspin = True
scene.userzoom = True

# ---------- helpers ----------
def lerp(a, b, u):
    return a + (b - a) * u

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def mountain_x_at_y(y):
    # jagged but continuous climbing path up the center of the mountain face
    return 1.25 * math.sin(0.55 * y) + 0.45 * math.sin(1.45 * y + 1.2)

def slope_width_at_y(y):
    return max(2.2, 8.5 - 0.25 * y)

def surface_pos(y, z=0):
    return vector(mountain_x_at_y(y), y, z)

def make_label(pos, text, height=13, color_value=vector(0.15,0.18,0.22), box=False):
    return label(pos=pos, text=text, height=height, color=color_value, box=box, opacity=0.0)

# ---------- world ----------
ground = box(pos=vector(0, -1.55, 0), size=vector(24, 0.25, 10), color=vector(0.70, 0.78, 0.68))
sky_band = box(pos=vector(0, 17.5, -4.6), size=vector(30, 6, 0.08), color=vector(0.77, 0.88, 1.0), opacity=0.45)

# mountain as layered ledges/face plates
mountain_parts = []
for i in range(22):
    y = -0.6 + i * 0.86
    w = slope_width_at_y(y)
    x = mountain_x_at_y(y) * 0.28
    shade = 0.62 + 0.012 * i
    ledge = box(
        pos=vector(x, y, -0.05),
        size=vector(w, 0.78, 0.38),
        axis=vector(1, 0.06 * math.sin(i), 0),
        color=vector(shade * 0.82, shade * 0.86, shade * 0.90),
    )
    mountain_parts.append(ledge)

# snow cap
for i in range(6):
    y = 16.3 + i * 0.45
    cap = box(
        pos=vector(mountain_x_at_y(y) * 0.18, y, -0.04),
        size=vector(max(0.9, 3.2 - i*0.4), 0.35, 0.42),
        color=vector(0.96, 0.98, 1.0),
    )
    mountain_parts.append(cap)

summit_flag_pole = cylinder(pos=surface_pos(18.75, 0.02), axis=vector(0, 1.25, 0), radius=0.035, color=vector(0.2,0.2,0.2))
summit_flag = box(pos=surface_pos(19.55, 0.04)+vector(0.45,0,0), size=vector(0.85,0.38,0.04), color=vector(1.0,0.72,0.25))
summit_glow = sphere(pos=surface_pos(19.0, 0.02), radius=0.42, color=vector(1.0,0.86,0.30), emissive=True, opacity=0.35)

# route memory markers: stronger learned route after each fall
route_markers = []
for i in range(30):
    y = -0.2 + i * 0.63
    marker = sphere(pos=surface_pos(y, 0.35), radius=0.055, color=vector(0.1, 0.45, 0.8), opacity=0.18)
    route_markers.append(marker)

# hazard zones
hazards = []
hazard_specs = [
    (2.1, "loose rocks", vector(0.55,0.39,0.25)),
    (4.6, "ice shelf", vector(0.65,0.90,1.0)),
    (7.3, "crosswind", vector(0.85,0.88,0.95)),
    (10.2, "fatigue wall", vector(0.9,0.75,0.60)),
    (13.4, "loose rocks", vector(0.55,0.39,0.25)),
    (15.5, "ice shelf", vector(0.65,0.90,1.0)),
]
for y, name, c in hazard_specs:
    p = surface_pos(y, -0.01)
    zone = box(pos=vector(p.x, y, 0.12), size=vector(3.2, 0.25, 0.10), color=c, opacity=0.55)
    txt = make_label(vector(p.x+2.6, y+0.22, 0.2), name, height=10, color_value=vector(0.24,0.26,0.28))
    hazards.append({"y": y, "name": name, "obj": zone, "label": txt})

# wind gust arrows
wind_arrows = []
for i in range(9):
    y = 1.0 + i * 1.65
    arr = arrow(
        pos=vector(-8.8, y, 0.55),
        axis=vector(1.25, 0, 0),
        shaftwidth=0.035,
        headwidth=0.16,
        color=vector(0.45,0.62,0.82),
        opacity=0.32,
    )
    wind_arrows.append(arr)

# falling rocks
rocks = []
for i in range(12):
    y = random.uniform(3.0, 16.0)
    p = surface_pos(y, 0.5)
    r = sphere(pos=vector(p.x + random.uniform(-1.0,1.2), y, 0.6), radius=random.uniform(0.07,0.15), color=vector(0.48,0.36,0.24))
    r.v = vector(random.uniform(-0.2,0.2), random.uniform(-0.4,-0.1), 0)
    rocks.append(r)

# climber body group
climber_y = -0.2
climber_x = mountain_x_at_y(climber_y)
body = sphere(pos=vector(climber_x, climber_y+0.25, 0.95), radius=0.26, color=vector(0.15,0.32,0.85))
head = sphere(pos=body.pos+vector(0,0.43,0), radius=0.17, color=vector(0.95,0.72,0.48))
pack = box(pos=body.pos+vector(0,-0.02,-0.25), size=vector(0.34,0.46,0.16), color=vector(0.9,0.25,0.16))
left_arm = cylinder(pos=body.pos+vector(-0.12,0.12,0), axis=vector(-0.28,0.30,0), radius=0.035, color=vector(0.12,0.18,0.28))
right_arm = cylinder(pos=body.pos+vector(0.12,0.12,0), axis=vector(0.28,0.30,0), radius=0.035, color=vector(0.12,0.18,0.28))
left_leg = cylinder(pos=body.pos+vector(-0.08,-0.18,0), axis=vector(-0.16,-0.36,0), radius=0.045, color=vector(0.08,0.12,0.20))
right_leg = cylinder(pos=body.pos+vector(0.08,-0.18,0), axis=vector(0.16,-0.36,0), radius=0.045, color=vector(0.08,0.12,0.20))
resolve_ring = ring(pos=body.pos, axis=vector(0,0,1), radius=0.48, thickness=0.025, color=vector(1.0,0.65,0.1), opacity=0.45)

# progress trail: never use curve.points in this VPython environment
trail = curve(color=vector(0.05,0.42,0.85), radius=0.025)
trail_tick = 0

# learned foothold memory as glowing small cylinders
footholds = []
for i in range(20):
    y = 0.4 + i*0.78
    p = surface_pos(y, 0.5)
    fh = cylinder(pos=vector(p.x - 0.25 + 0.5*(i%2), y, 0.72), axis=vector(0.4,0,0), radius=0.022, color=vector(0.2,0.42,0.72), opacity=0.12)
    footholds.append(fh)

# UI
status = label(
    pos=vector(-8.7, 18.4, 0),
    text="",
    height=14,
    color=vector(0.08,0.10,0.13),
    box=False,
    opacity=0,
)
lesson_label = label(
    pos=vector(4.5, 18.0, 0),
    text="Each fall teaches a stronger route.",
    height=13,
    color=vector(0.20,0.18,0.12),
    box=True,
    border=8,
    opacity=0.12,
)

# simulation state
attempt = 1
falls = 0
learned_strength = 0.0
fatigue = 0.0
mode = "CLIMB"
fall_timer = 0
fall_from_y = 0
current_goal = 19.0
best_height = -0.2
route_bias = random.uniform(-0.4,0.4)
phase_time = 0.0
catch_breath_timer = 0.0
last_lesson = "First route: uncertain grip."

# behavior patterns create varied climbs each round
round_styles = [
    {"name":"steady zigzag", "tempo":0.82, "risk":0.65, "rest":0.9},
    {"name":"fast burst climb", "tempo":1.18, "risk":1.05, "rest":0.55},
    {"name":"careful ice route", "tempo":0.70, "risk":0.38, "rest":1.30},
    {"name":"wind-reading traverse", "tempo":0.90, "risk":0.50, "rest":1.05},
    {"name":"learned direct ascent", "tempo":1.02, "risk":0.34, "rest":0.72},
]
style = round_styles[0]

# ---------- update functions ----------
def set_climber_position(y, sway, t):
    x = mountain_x_at_y(y) + sway
    base = vector(x, y, 0.95)
    body.pos = base + vector(0, 0.25, 0)
    head.pos = body.pos + vector(0, 0.43, 0)
    pack.pos = body.pos + vector(0, -0.02, -0.25)

    arm_wave = 0.18 * math.sin(6.0*t)
    leg_wave = 0.12 * math.sin(5.2*t + 1.0)
    left_arm.pos = body.pos + vector(-0.12,0.12,0)
    left_arm.axis = vector(-0.28, 0.30 + arm_wave, 0)
    right_arm.pos = body.pos + vector(0.12,0.12,0)
    right_arm.axis = vector(0.28, 0.30 - arm_wave, 0)
    left_leg.pos = body.pos + vector(-0.08,-0.18,0)
    left_leg.axis = vector(-0.16, -0.36 + leg_wave, 0)
    right_leg.pos = body.pos + vector(0.08,-0.18,0)
    right_leg.axis = vector(0.16, -0.36 - leg_wave, 0)

    resolve_ring.pos = body.pos
    resolve_ring.radius = 0.45 + 0.08 * math.sin(3*t)
    resolve_ring.opacity = 0.22 + 0.30 * learned_strength


def hazard_force(y, t):
    force = 0.0
    reason = "clear route"
    for h in hazards:
        d = abs(y - h["y"])
        if d < 0.65:
            pulse = 0.5 + 0.5 * math.sin(5*t + h["y"])
            if "ice" in h["name"]:
                force += 0.030 + 0.030*pulse
                reason = "ice slips underfoot"
            elif "loose" in h["name"]:
                force += 0.038 + 0.04*pulse
                reason = "loose rocks break away"
            elif "crosswind" in h["name"]:
                force += 0.025 + 0.050*pulse
                reason = "crosswind pushes sideways"
            elif "fatigue" in h["name"]:
                force += 0.045 + 0.035*pulse
                reason = "fatigue drains the ascent"
    return force, reason


def start_new_attempt(after_fall=True):
    global attempt, fatigue, mode, fall_timer, route_bias, phase_time, style, catch_breath_timer, last_lesson
    if after_fall:
        attempt += 1
    fatigue = max(0.05, fatigue * 0.28)
    mode = "CLIMB"
    fall_timer = 0
    phase_time = 0
    catch_breath_timer = random.uniform(0.5, 1.6)
    route_bias = random.uniform(-0.55,0.55) * max(0.15, 1.0 - learned_strength)
    # later attempts favor safer styles
    if learned_strength > 0.55:
        style = random.choice(round_styles[2:])
    else:
        style = random.choice(round_styles)
    last_lesson = random.choice([
        "Lesson kept: choose the firmer blue footholds.",
        "Lesson kept: slow down near ice shelves.",
        "Lesson kept: lean into wind before it hits.",
        "Lesson kept: rest before the fatigue wall.",
        "Lesson kept: avoid the loose-rock centerline.",
    ])


def trigger_fall(reason):
    global mode, fall_timer, fall_from_y, falls, learned_strength, last_lesson
    mode = "FALL"
    fall_timer = 0
    fall_from_y = climber_y
    falls += 1
    learned_strength = clamp(learned_strength + 0.11, 0.0, 0.92)
    last_lesson = "Fall reason: " + reason + " → route improves."


def update_route_memory():
    for i, m in enumerate(route_markers):
        y = -0.2 + i * 0.63
        if y < best_height + 0.8:
            m.opacity = 0.12 + 0.60 * learned_strength
            m.radius = 0.045 + 0.045 * learned_strength
            m.color = vector(0.05, 0.35 + 0.35*learned_strength, 0.85)
        else:
            m.opacity = 0.08
    for i, fh in enumerate(footholds):
        fh.opacity = 0.10 + 0.55 * learned_strength if fh.pos.y < best_height + 0.6 else 0.08
        fh.radius = 0.018 + 0.018 * learned_strength


def update_wind_and_rocks(t):
    for i, arr in enumerate(wind_arrows):
        strength = 0.55 + 0.55 * math.sin(t*1.4 + i*0.8)
        arr.axis = vector(0.8 + 1.3*strength, 0.05*math.sin(t+i), 0)
        arr.opacity = 0.20 + 0.25*strength
        arr.pos.x = -8.8 + 0.4*math.sin(t*0.7+i)

    for r in rocks:
        r.pos += r.v * 0.08
        r.v.y -= 0.005
        if r.pos.y < -0.5 or random.random() < 0.002:
            y = random.uniform(4.0, 17.0)
            p = surface_pos(y, 0.5)
            r.pos = vector(p.x + random.uniform(-1.4,1.4), y, 0.6)
            r.v = vector(random.uniform(-0.12,0.12), random.uniform(-0.55,-0.16), 0)


def update_hazard_visuals(t):
    for h in hazards:
        pulse = 0.5 + 0.5 * math.sin(4.3*t + h["y"])
        h["obj"].opacity = 0.30 + 0.32*pulse
        h["obj"].size.y = 0.18 + 0.12*pulse

# ---------- main loop ----------
t = 0.0
dt = 0.035
while True:
    rate(60)
    t += dt
    phase_time += dt
    update_wind_and_rocks(t)
    update_hazard_visuals(t)

    summit_glow.radius = 0.38 + 0.07*math.sin(2.5*t)
    summit_glow.opacity = 0.25 + 0.15*math.sin(2.5*t)**2
    summit_flag.pos.y = surface_pos(19.55, 0.04).y + 0.06*math.sin(3*t)

    if mode == "CLIMB":
        catch_breath_timer -= dt
        if catch_breath_timer > 0:
            climb_step = 0.006 * (0.65 + learned_strength)
            fatigue += 0.0007
        else:
            base_speed = 0.022 * style["tempo"]
            hazard, reason = hazard_force(climber_y, t)
            wind_drag = 0.006 * (0.5 + 0.5*math.sin(1.7*t + climber_y))
            fatigue += 0.0019 * style["risk"] * (1.0 + climber_y/20)
            learned_bonus = 0.016 * learned_strength
            grip_bonus = 0.006 * sum(1 for fh in footholds if abs(fh.pos.y-climber_y)<0.45) * learned_strength
            downward = hazard * style["risk"] + wind_drag + fatigue*0.020
            climb_step = base_speed + learned_bonus + grip_bonus - downward

            # fall chance when downward force overwhelms current skill
            danger = hazard + fatigue*0.09 - learned_strength*0.055
            if danger > 0.055 and random.random() < danger * 0.14:
                trigger_fall(reason)

            # planned rest after difficult zones
            if random.random() < 0.006 + fatigue*0.003:
                catch_breath_timer = style["rest"] * random.uniform(0.6, 1.4)

        # setbacks happen, but rarely after learning improves
        if mode == "CLIMB":
            climber_y += climb_step
            climber_y = clamp(climber_y, -0.25, 19.15)
            best_height = max(best_height, climber_y)

        sway = route_bias * math.exp(-0.10*climber_y) + 0.14*math.sin(2.0*t + attempt)
        set_climber_position(climber_y, sway, t)

        trail_tick += 1
        if trail_tick % 4 == 0:
            trail.append(pos=body.pos + vector(0, -0.2, -0.08))
            # Avoid trail.points; this environment supports npoints.
            if hasattr(trail, "npoints") and trail.npoints > 420:
                trail.clear()

        if climber_y >= 18.85:
            mode = "SUMMIT"
            phase_time = 0
            last_lesson = "The route holds. The climber reaches the summit."

    elif mode == "FALL":
        fall_timer += dt
        fall_u = clamp(fall_timer / 1.55, 0, 1)
        target_y = max(-0.2, fall_from_y - random.uniform(1.2, 3.5) * (1.0 - learned_strength*0.55))
        eased = 1 - (1 - fall_u)**2
        climber_y = lerp(fall_from_y, target_y, eased)
        sway = 0.55*math.sin(16*fall_u) * (1.0-fall_u)
        set_climber_position(climber_y, sway, t)
        resolve_ring.color = vector(1.0, 0.38, 0.14)
        resolve_ring.opacity = 0.55
        if fall_timer > 1.65:
            resolve_ring.color = vector(1.0,0.65,0.1)
            start_new_attempt(after_fall=True)

    elif mode == "SUMMIT":
        set_climber_position(18.85, 0.05*math.sin(3*t), t)
        resolve_ring.color = vector(1.0, 0.78, 0.12)
        resolve_ring.opacity = 0.75
        learned_strength = clamp(learned_strength + 0.0007, 0, 1.0)
        if phase_time > 5.2:
            # reset for another longer story round with a new style, keeping some learned strength
            climber_y = -0.2
            fatigue = 0.0
            learned_strength = clamp(learned_strength * 0.72, 0.0, 0.85)
            trail.clear()
            start_new_attempt(after_fall=True)

    update_route_memory()

    # readout
    progress_pct = int(clamp((climber_y + 0.2) / 19.05, 0, 1) * 100)
    status.text = (
        "THE NEVER-GIVE-UP CLIMBER\n"
        f"attempt: {attempt}    falls: {falls}    mode: {mode}\n"
        f"route style: {style['name']}\n"
        f"height progress: {progress_pct}%    best height: {best_height:0.1f}\n"
        f"fatigue: {fatigue:0.2f}    learned route strength: {learned_strength:0.2f}\n"
        f"{last_lesson}"
    )
    lesson_label.text = (
        "INDOMITABLE\n"
        "Wind, ice, rocks, and fatigue can push the climber back.\n"
        "Every fall brightens footholds and makes the next route stronger."
    )
