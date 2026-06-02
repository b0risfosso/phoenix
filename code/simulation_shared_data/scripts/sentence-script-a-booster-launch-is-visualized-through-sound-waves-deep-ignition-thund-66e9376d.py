from vpython import *
import math
import random

# Sound-On Ascent Chamber
# A booster launch visualized through sound waves: deep ignition thunder,
# rising vibration bands, aerodynamic roar, and sudden quiet after separation.
#
# Controls:
#   SPACE  pause / resume
#   R      reset
#   W/S    increase/decrease ascent speed
#   A/D    rotate camera around chamber
#   Q/E    zoom camera out/in
#   H      show/hide help panel

scene.title = "Sound-On Ascent Chamber"
scene.width = 1200
scene.height = 760
scene.background = vector(0.93, 0.96, 1.0)
scene.forward = vector(-0.65, -0.32, -0.70)
scene.center = vector(0, 16, 0)
scene.range = 38
scene.autoscale = False

# ---------- Helpers ----------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = clamp(t, 0, 1)
    return vector(lerp(c1.x, c2.x, t), lerp(c1.y, c2.y, t), lerp(c1.z, c2.z, t))


def make_label(text, pos, height=14, color_value=vector(0.15, 0.18, 0.25), box=False):
    return label(
        text=text,
        pos=pos,
        height=height,
        color=color_value,
        box=box,
        opacity=0.0,
        line=False,
        font="sans",
    )

# ---------- Scene structure ----------

floor = box(
    pos=vector(0, -0.28, 0),
    size=vector(42, 0.18, 42),
    color=vector(0.82, 0.88, 0.92),
    opacity=0.55,
)
launch_pad = cylinder(
    pos=vector(0, 0, 0),
    axis=vector(0, 0.25, 0),
    radius=4.4,
    color=vector(0.55, 0.57, 0.60),
    opacity=0.85,
)

# Chamber reference rings: a vertical acoustic tunnel around the ascent path.
chamber_rings = []
for y in range(0, 58, 6):
    r = ring(
        pos=vector(0, y, 0),
        axis=vector(0, 1, 0),
        radius=12.0,
        thickness=0.035,
        color=vector(0.62, 0.74, 0.88),
        opacity=0.32,
    )
    chamber_rings.append(r)

# faint vertical guide struts
for i in range(8):
    ang = 2 * math.pi * i / 8
    x = 12 * math.cos(ang)
    z = 12 * math.sin(ang)
    cylinder(
        pos=vector(x, 0, z),
        axis=vector(0, 58, 0),
        radius=0.035,
        color=vector(0.70, 0.78, 0.85),
        opacity=0.26,
    )

# Cloud layers
clouds = []
for i in range(44):
    y = random.uniform(17, 36)
    radius = random.uniform(0.7, 1.7)
    theta = random.uniform(0, 2 * math.pi)
    dist = random.uniform(4.6, 12.4)
    p = vector(dist * math.cos(theta), y, dist * math.sin(theta))
    clouds.append(
        sphere(
            pos=p,
            radius=radius,
            color=vector(1, 1, 1),
            opacity=random.uniform(0.23, 0.48),
        )
    )

# Booster stack group
booster = compound([
    cylinder(pos=vector(0, 0, 0), axis=vector(0, 5.6, 0), radius=0.72, color=vector(0.96, 0.97, 0.96)),
    cone(pos=vector(0, 5.6, 0), axis=vector(0, 1.25, 0), radius=0.72, color=vector(0.92, 0.38, 0.22)),
    cylinder(pos=vector(0.96, 0.6, 0), axis=vector(0, 4.6, 0), radius=0.22, color=vector(0.88, 0.27, 0.18)),
    cylinder(pos=vector(-0.96, 0.6, 0), axis=vector(0, 4.6, 0), radius=0.22, color=vector(0.88, 0.27, 0.18)),
    box(pos=vector(0, 2.2, -0.78), size=vector(1.35, 2.4, 0.18), color=vector(0.48, 0.58, 0.68)),
])
booster.pos = vector(0, 0, 0)

# Exhaust and flame objects
flames = []
for i in range(14):
    flames.append(
        cone(
            pos=vector(0, -0.08 - i * 0.18, 0),
            axis=vector(0, -1.0, 0),
            radius=0.55 + i * 0.055,
            color=mix(vector(1.0, 0.93, 0.35), vector(1.0, 0.32, 0.10), i / 13),
            opacity=0.68,
            visible=True,
        )
    )

smoke_puffs = []
for i in range(90):
    theta = random.uniform(0, 2 * math.pi)
    smoke_puffs.append({
        "obj": sphere(
            pos=vector(random.uniform(-2, 2), random.uniform(-1.8, 0.4), random.uniform(-2, 2)),
            radius=random.uniform(0.22, 0.72),
            color=vector(0.78, 0.79, 0.78),
            opacity=0.0,
        ),
        "vel": vector(random.uniform(-0.04, 0.04), random.uniform(-0.015, 0.035), random.uniform(-0.04, 0.04)),
        "phase": random.uniform(0, 2 * math.pi),
        "spin": random.uniform(-0.08, 0.08),
        "base_radius": random.uniform(0.22, 0.72),
        "theta": theta,
    })

# Sound rings expanding from the nozzle and from chamber bands.
sound_rings = []
for i in range(34):
    sound_rings.append({
        "obj": ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=1.0,
            thickness=0.055,
            color=vector(0.18, 0.35, 0.78),
            opacity=0.0,
        ),
        "age": random.uniform(0, 6.0),
        "kind": "thunder" if i < 14 else "roar",
        "offset": random.uniform(-0.4, 0.7),
    })

vibration_bands = []
for i in range(18):
    vibration_bands.append({
        "obj": ring(
            pos=vector(0, 0.8 + i * 2.7, 0),
            axis=vector(0, 1, 0),
            radius=2.1 + 0.12 * i,
            thickness=0.045,
            color=vector(0.95, 0.64, 0.20),
            opacity=0.0,
        ),
        "phase": random.uniform(0, 2 * math.pi),
    })

# Roar stream: tilted translucent sheets moving along the sides.
roar_streams = []
for i in range(24):
    side = -1 if i % 2 == 0 else 1
    roar_streams.append({
        "obj": box(
            pos=vector(side * random.uniform(2.2, 6.2), random.uniform(4, 44), random.uniform(-0.25, 0.25)),
            size=vector(random.uniform(0.05, 0.12), random.uniform(1.7, 4.6), random.uniform(0.08, 0.18)),
            color=vector(0.55, 0.68, 0.92),
            opacity=0.0,
        ),
        "side": side,
        "speed": random.uniform(5.0, 9.0),
        "phase": random.uniform(0, 2 * math.pi),
    })

# Separation components
separation_ring = ring(
    pos=vector(0, 44, 0),
    axis=vector(0, 1, 0),
    radius=1.6,
    thickness=0.09,
    color=vector(0.35, 0.45, 0.65),
    opacity=0.0,
)
quiet_dome = sphere(
    pos=vector(0, 46, 0),
    radius=1.0,
    color=vector(0.86, 0.94, 1.0),
    opacity=0.0,
)
quiet_dome.visible = True

# Sound meter bars
meter_back = box(pos=vector(-15.5, 6, 0), size=vector(0.28, 12, 0.28), color=vector(0.78, 0.82, 0.86), opacity=0.5)
meter_fill = box(pos=vector(-15.5, 0.2, 0), size=vector(0.5, 0.2, 0.5), color=vector(0.98, 0.45, 0.18), opacity=0.9)
make_label("SOUND", vector(-15.5, 13.1, 0), 12, vector(0.20, 0.24, 0.30))

stage_label = make_label("IGNITION THUNDER", vector(0, 62, 0), 22, vector(0.18, 0.22, 0.34))
status_label = make_label("", vector(0, -3.0, 0), 12, vector(0.22, 0.26, 0.34))
help_label = label(
    pos=vector(15, 16, 0),
    text="SPACE pause | R reset\nW/S ascent speed\nA/D orbit camera | Q/E zoom\nH hide help",
    height=11,
    color=vector(0.12, 0.15, 0.22),
    box=True,
    border=8,
    opacity=0.72,
    line=False,
)

# ---------- Simulation state ----------

t = 0.0
paused = False
speed_scale = 1.0
camera_angle = -0.75
camera_dist = 52
show_help = True

separation_started = False
separation_time = 0.0
booster_shell = None
upper_stage = None

# Use mutable dictionary to make reset simple without global rebinding problems.
state = {
    "altitude": 0.0,
    "velocity": 0.0,
    "separated": False,
}


def create_separation_parts(current_pos):
    global booster_shell, upper_stage
    if booster_shell is not None:
        booster_shell.visible = False
    if upper_stage is not None:
        upper_stage.visible = False

    booster.visible = False
    booster_shell = compound([
        cylinder(pos=vector(0, -2.8, 0), axis=vector(0, 4.8, 0), radius=0.72, color=vector(0.93, 0.93, 0.90)),
        cone(pos=vector(0, 2.0, 0), axis=vector(0, 0.8, 0), radius=0.72, color=vector(0.85, 0.32, 0.22)),
        cylinder(pos=vector(0.96, -2.3, 0), axis=vector(0, 3.5, 0), radius=0.22, color=vector(0.86, 0.27, 0.18)),
        cylinder(pos=vector(-0.96, -2.3, 0), axis=vector(0, 3.5, 0), radius=0.22, color=vector(0.86, 0.27, 0.18)),
    ])
    booster_shell.pos = current_pos + vector(0, 0.3, 0)

    upper_stage = compound([
        cylinder(pos=vector(0, 0, 0), axis=vector(0, 2.4, 0), radius=0.50, color=vector(0.96, 0.97, 0.98)),
        cone(pos=vector(0, 2.4, 0), axis=vector(0, 0.9, 0), radius=0.50, color=vector(0.60, 0.70, 0.85)),
        box(pos=vector(0, 1.1, -0.52), size=vector(1.2, 1.5, 0.13), color=vector(0.44, 0.58, 0.72)),
    ])
    upper_stage.pos = current_pos + vector(0, 4.8, 0)


def reset_scene():
    global t, separation_started, separation_time
    t = 0.0
    separation_started = False
    separation_time = 0.0
    state["altitude"] = 0.0
    state["velocity"] = 0.0
    state["separated"] = False
    booster.visible = True
    booster.pos = vector(0, 0, 0)
    booster.axis = vector(0, 1, 0)
    if booster_shell is not None:
        booster_shell.visible = False
    if upper_stage is not None:
        upper_stage.visible = False
    separation_ring.opacity = 0.0
    quiet_dome.opacity = 0.0
    quiet_dome.radius = 1.0
    stage_label.text = "IGNITION THUNDER"


def keydown(evt):
    global paused, speed_scale, camera_angle, camera_dist, show_help
    k = evt.key.lower()
    if k == " ":
        paused = not paused
    elif k == "r":
        reset_scene()
    elif k == "w":
        speed_scale = clamp(speed_scale + 0.15, 0.35, 2.2)
    elif k == "s":
        speed_scale = clamp(speed_scale - 0.15, 0.35, 2.2)
    elif k == "a":
        camera_angle -= 0.12
    elif k == "d":
        camera_angle += 0.12
    elif k == "q":
        camera_dist = clamp(camera_dist + 3, 32, 82)
    elif k == "e":
        camera_dist = clamp(camera_dist - 3, 32, 82)
    elif k == "h":
        show_help = not show_help
        help_label.visible = show_help

scene.bind("keydown", keydown)

# ---------- Main loop ----------

dt = 0.016
while True:
    rate(60)
    if paused:
        status_label.text = "PAUSED"
        continue

    t += dt * speed_scale

    altitude = state["altitude"]
    separated = state["separated"]

    # Flight phases and intensity envelopes.
    ignition = clamp(t / 5.0, 0, 1)
    ascent = clamp((t - 3.0) / 20.0, 0, 1)
    thinning_air = clamp((altitude - 28.0) / 14.0, 0, 1)

    if not separated:
        accel = 0.072 + 0.036 * ignition + 0.018 * math.sin(t * 0.9)
        state["velocity"] = clamp(state["velocity"] + accel * dt * 10.0, 0, 2.35)
        state["altitude"] += state["velocity"] * dt * 5.2
        altitude = state["altitude"]

        if altitude > 43.0:
            state["separated"] = True
            separated = True
            separation_started = True
            separation_time = t
            create_separation_parts(vector(0, altitude, 0))

    time_since_sep = max(0, t - separation_time) if separated else 0

    thunder_intensity = (1.0 - clamp(t / 12.0, 0, 1)) * ignition
    vibration_intensity = clamp(math.sin(t * 0.45) * 0.15 + 0.85, 0, 1) * clamp((t - 1.3) / 8.5, 0, 1) * (1 - 0.65 * thinning_air)
    roar_intensity = clamp((altitude - 8.0) / 24.0, 0, 1) * (1 - 0.85 * thinning_air)
    quiet_intensity = clamp(time_since_sep / 3.0, 0, 1) if separated else 0
    sound_level = clamp(0.48 * thunder_intensity + 0.52 * vibration_intensity + 0.68 * roar_intensity, 0, 1) * (1 - quiet_intensity)

    # Stage labels.
    if separated:
        stage_label.text = "SEPARATION: SUDDEN QUIET"
    elif altitude < 9:
        stage_label.text = "DEEP IGNITION THUNDER"
    elif altitude < 25:
        stage_label.text = "RISING VIBRATION BANDS"
    else:
        stage_label.text = "AERODYNAMIC ROAR"

    status_label.text = "altitude %.1f   sound %.0f%%   speed %.2fx" % (altitude, sound_level * 100, speed_scale)

    # Camera rides beside the booster.
    target_y = altitude + 10 if not separated else altitude + 10 + time_since_sep * 0.7
    scene.center = vector(0, clamp(target_y, 10, 55), 0)
    scene.forward = vector(-0.65 * math.cos(camera_angle), -0.28, -0.65 * math.sin(camera_angle))
    scene.range = camera_dist * 0.68

    # Booster shake and movement.
    shake_amp = 0.09 + 0.22 * sound_level
    shake = vector(
        math.sin(t * 42.0) * shake_amp + random.uniform(-0.035, 0.035) * sound_level,
        0,
        math.cos(t * 37.0) * shake_amp + random.uniform(-0.035, 0.035) * sound_level,
    )

    if not separated:
        booster.pos = vector(0, altitude, 0) + shake
        booster.rotate(angle=0.003 * math.sin(t * 18) * vibration_intensity, axis=vector(0, 0, 1), origin=booster.pos)
    else:
        # Booster falls away; upper stage continues upward into quiet.
        if booster_shell is not None:
            booster_shell.pos += vector(0.018 * math.sin(t), -0.055 - 0.010 * time_since_sep, 0.014 * math.cos(t * 0.8))
            booster_shell.rotate(angle=0.01, axis=vector(0, 0, 1), origin=booster_shell.pos)
        if upper_stage is not None:
            upper_stage.pos += vector(0, 0.12, 0)

    # Flame plume dims after separation.
    flame_strength = (0.25 + 0.75 * sound_level) * (1 - quiet_intensity)
    nozzle_pos = vector(0, altitude - 0.05, 0) if not separated else (booster_shell.pos + vector(0, -2.9, 0) if booster_shell else vector(0, altitude, 0))
    for i, f in enumerate(flames):
        phase = t * (9.0 + i * 0.22) + i
        flare = 0.65 + 0.35 * math.sin(phase)
        f.visible = flame_strength > 0.04
        f.pos = nozzle_pos + vector(0.08 * math.sin(phase), -0.22 - i * 0.17, 0.08 * math.cos(phase * 1.1))
        f.radius = (0.34 + 0.055 * i) * (0.75 + flame_strength * flare)
        f.opacity = clamp(0.12 + 0.76 * flame_strength * (1 - i / 18), 0, 0.86)
        f.axis = vector(0.08 * math.sin(phase * 0.7), -0.72 - 0.06 * i, 0.08 * math.cos(phase * 0.6))

    # Smoke pulses mostly at lower altitude.
    smoke_strength = clamp((9.0 - altitude) / 9.0, 0, 1) * ignition
    for idx, puff in enumerate(smoke_puffs):
        obj = puff["obj"]
        puff["theta"] += puff["spin"] * dt * 8
        spread = 1.5 + (t * 0.32 + idx * 0.05) % 5.2
        if obj.opacity <= 0.01 or random.random() < 0.006 * smoke_strength:
            obj.pos = vector(
                1.1 * math.cos(puff["theta"]) + random.uniform(-0.3, 0.3),
                random.uniform(-1.5, 0.5),
                1.1 * math.sin(puff["theta"]) + random.uniform(-0.3, 0.3),
            )
            obj.opacity = 0.22 * smoke_strength
            obj.radius = puff["base_radius"]
        obj.pos += puff["vel"] * (1 + 3 * smoke_strength)
        obj.radius = min(2.1, obj.radius + 0.003 + 0.010 * smoke_strength)
        obj.opacity = max(0, obj.opacity - 0.0018 - 0.003 * (1 - smoke_strength))

    # Expanding acoustic rings.
    for i, sr in enumerate(sound_rings):
        obj = sr["obj"]
        sr["age"] += dt * (1.0 + 1.8 * sound_level)
        limit = 4.5 if sr["kind"] == "thunder" else 2.2
        if sr["age"] > limit:
            sr["age"] = random.uniform(0, 0.22)
            sr["offset"] = random.uniform(-0.4, 0.7)
        if sr["kind"] == "thunder":
            local = 1 - clamp(sr["age"] / 4.5, 0, 1)
            obj.pos = vector(0, max(0.04, altitude * 0.18 + sr["offset"]), 0)
            obj.radius = 1.4 + sr["age"] * (3.7 + 4.5 * thunder_intensity)
            obj.thickness = 0.045 + 0.09 * thunder_intensity * local
            obj.color = mix(vector(0.15, 0.30, 0.70), vector(0.98, 0.50, 0.16), thunder_intensity)
            obj.opacity = 0.42 * thunder_intensity * local * (1 - quiet_intensity)
        else:
            local = 1 - clamp(sr["age"] / 2.2, 0, 1)
            obj.pos = vector(0, altitude + sr["offset"], 0)
            obj.radius = 0.9 + sr["age"] * (2.4 + 3.0 * roar_intensity)
            obj.thickness = 0.035 + 0.06 * roar_intensity * local
            obj.color = mix(vector(0.34, 0.55, 0.95), vector(0.95, 0.78, 0.28), roar_intensity)
            obj.opacity = 0.35 * (0.25 + roar_intensity) * local * (1 - quiet_intensity)

    # Vibration bands climbing through the chamber.
    for i, vb in enumerate(vibration_bands):
        obj = vb["obj"]
        y_base = ((i * 3.2 + t * (2.4 + 6.5 * vibration_intensity)) % 52.0) + 1.0
        wave = math.sin(t * 8.0 + vb["phase"]) * (0.55 + 0.7 * vibration_intensity)
        obj.pos = vector(wave * 0.12, y_base, -wave * 0.10)
        obj.radius = 2.4 + 0.14 * y_base + 0.45 * math.sin(t * 7 + i)
        obj.thickness = 0.03 + 0.08 * vibration_intensity * (0.5 + 0.5 * math.sin(t * 12 + i))
        obj.opacity = clamp(0.03 + 0.52 * vibration_intensity * (1 - abs(y_base - altitude) / 34.0), 0, 0.54) * (1 - quiet_intensity)
        obj.color = mix(vector(0.98, 0.78, 0.25), vector(0.25, 0.45, 0.90), thinning_air)

    # Aerodynamic roar streams sliding past the stack.
    for rs in roar_streams:
        obj = rs["obj"]
        obj.pos.y += rs["speed"] * dt * (0.55 + roar_intensity)
        if obj.pos.y > altitude + 18:
            obj.pos.y = altitude - random.uniform(6, 16)
            obj.pos.x = rs["side"] * random.uniform(2.0, 7.0)
            obj.pos.z = random.uniform(-0.35, 0.35)
        drift = math.sin(t * 5.0 + rs["phase"]) * (0.2 + 0.5 * roar_intensity)
        obj.pos.x = rs["side"] * (3.0 + 3.5 * roar_intensity + drift)
        obj.size.y = 1.6 + 4.8 * roar_intensity * (0.4 + 0.6 * math.sin(t * 2 + rs["phase"]) ** 2)
        obj.opacity = 0.38 * roar_intensity * (1 - quiet_intensity)

    # Chamber rings respond to noise then settle into quiet.
    for i, cr in enumerate(chamber_rings):
        pulse = 0.5 + 0.5 * math.sin(t * 5.2 + i * 0.9)
        cr.radius = 12.0 + sound_level * (0.25 + 0.55 * pulse)
        cr.thickness = 0.032 + 0.055 * sound_level * pulse
        cr.opacity = 0.18 + 0.25 * sound_level * pulse
        cr.color = mix(vector(0.62, 0.74, 0.88), vector(0.98, 0.62, 0.22), sound_level * pulse)

    # Quiet shock: visible silence bubble after separation.
    if separated:
        separation_ring.pos = vector(0, altitude + 0.8, 0)
        separation_ring.radius = 1.7 + 4.0 * clamp(time_since_sep / 2.0, 0, 1)
        separation_ring.opacity = max(0, 0.65 - 0.18 * time_since_sep)
        quiet_dome.pos = vector(0, altitude + 2.5 + time_since_sep * 0.6, 0)
        quiet_dome.radius = 2.0 + 8.5 * quiet_intensity
        quiet_dome.opacity = 0.08 + 0.24 * quiet_intensity
    else:
        separation_ring.opacity = 0.0
        quiet_dome.opacity = 0.0

    # Sound meter.
    meter_height = 0.2 + 11.6 * sound_level
    meter_fill.size = vector(0.55, meter_height, 0.55)
    meter_fill.pos = vector(-15.5, -0.1 + meter_height / 2, 0)
    meter_fill.color = mix(vector(0.30, 0.58, 0.96), vector(1.0, 0.35, 0.12), sound_level)

    # Fade clouds as booster tears through them.
    for i, c in enumerate(clouds):
        distance_to_stack = mag(vector(c.pos.x, c.pos.y - altitude, c.pos.z))
        wake = clamp(1 - distance_to_stack / 6.5, 0, 1)
        c.opacity = clamp(c.opacity + 0.0004 - 0.018 * wake * sound_level, 0.05, 0.52)
        c.pos.x += 0.002 * math.sin(t + i) + 0.015 * wake * math.sin(t * 8 + i)
        c.pos.z += 0.002 * math.cos(t * 0.8 + i) + 0.015 * wake * math.cos(t * 7 + i)
