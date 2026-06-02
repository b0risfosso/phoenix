from vpython import *
import math
import random

# Strapped to the SRB with keyboard controls - aligned booster version
# VPython simulation: viewer/camera rides beside a solid rocket booster during ascent.
# Alignment fix: avoids forcing compound.axis vertical after construction.
# Uses ring(...) instead of torus(...). No external assets required.
# Controls:
#   C  toggle SRB side camera / free camera
#   P  pause or resume
#   R  full simulation reset
#   S  toggle vibration shake
#   F  toggle flame and smoke plume
#   H  toggle HUD/control text
#   B  toggle booster-body visibility for a cleaner side-camera view
#   UP/DOWN    increase/decrease ascent speed
#   RIGHT/LEFT increase/decrease thrust strength
#   +/-        increase/decrease camera shake intensity
#   [/]        decrease/increase cloud visibility

scene = canvas(
    title="Strapped to the SRB - side-mounted booster ride",
    width=1200,
    height=760,
    background=vector(0.78, 0.90, 1.0),
    center=vector(0, 32, 0),
)
scene.forward = vector(-0.55, -0.18, -0.82)
scene.range = 55
scene.userspin = True
scene.userzoom = True

# ---------- Helpers ----------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, f):
    return a + (b - a) * clamp(f, 0, 1)


def color_lerp(c1, c2, f):
    f = clamp(f, 0, 1)
    return vector(lerp(c1.x, c2.x, f), lerp(c1.y, c2.y, f), lerp(c1.z, c2.z, f))


# ---------- World ----------

# High-altitude Earth arc below the ascent path.
earth_radius_visual = 520
earth = sphere(
    pos=vector(0, -earth_radius_visual - 8, 0),
    radius=earth_radius_visual,
    color=vector(0.38, 0.70, 0.95),
    shininess=0.25,
    opacity=0.96,
)

# Horizon haze rings showing curvature.
horizon_rings = []
for i, rad in enumerate([235, 280, 330, 390]):
    r = ring(
        pos=vector(0, -12 - i * 4, 0),
        axis=vector(0, 1, 0),
        radius=rad,
        thickness=0.35,
        color=vector(0.70, 0.86, 1.0),
        opacity=0.25 - i * 0.035,
    )
    horizon_rings.append(r)

# Launch pad and tower.
pad = box(pos=vector(0, 0, 0), size=vector(42, 2, 42), color=vector(0.55, 0.56, 0.55))
flame_trench = box(pos=vector(0, 0.25, 0), size=vector(12, 1.3, 28), color=vector(0.25, 0.25, 0.25))
tower_parts = []
for y in range(4, 62, 8):
    tower_parts.append(box(pos=vector(-19, y, 0), size=vector(3.0, 6.5, 3.0), color=vector(0.80, 0.36, 0.20)))
    tower_parts.append(box(pos=vector(-13, y, 0), size=vector(2.0, 6.5, 2.0), color=vector(0.72, 0.30, 0.16)))
    tower_parts.append(box(pos=vector(-16, y + 3.1, 0), size=vector(9.5, 0.7, 3.0), color=vector(0.78, 0.34, 0.18)))
for y in [13, 27, 41, 55]:
    tower_parts.append(box(pos=vector(-9, y, 0), size=vector(13, 0.7, 2.5), color=vector(0.76, 0.34, 0.18)))

# Painted reference lines that fall away as the booster climbs.
pad_markers = []
for x in [-28, -18, -8, 8, 18, 28]:
    pad_markers.append(box(pos=vector(x, 0.55, -24), size=vector(4, 0.12, 1.0), color=color.white))

# Clouds as soft clusters.
clouds = []
for layer_y, spread, count in [(85, 80, 36), (145, 115, 42), (220, 150, 36)]:
    for _ in range(count):
        p = vector(random.uniform(-spread, spread), layer_y + random.uniform(-8, 8), random.uniform(-spread, spread))
        s = random.uniform(5, 14)
        clouds.append(sphere(pos=p, radius=s, color=vector(1, 1, 1), opacity=random.uniform(0.18, 0.36), shininess=0))

# ---------- Shuttle stack / booster ----------

# SRB body: long white cylinder with black nose cap and bands.
srb_body = cylinder(pos=vector(0, 8, 0), axis=vector(0, 72, 0), radius=3.1, color=vector(0.94, 0.94, 0.90), shininess=0.55)
srb_nose = cone(pos=vector(0, 80, 0), axis=vector(0, 9, 0), radius=3.1, color=vector(0.12, 0.12, 0.12))
srb_nozzle = cone(pos=vector(0, 7.5, 0), axis=vector(0, -5.5, 0), radius=2.5, color=vector(0.16, 0.16, 0.16))
booster_bands = []
for y in [16, 31, 48, 65]:
    booster_bands.append(ring(pos=vector(0, y, 0), axis=vector(0, 1, 0), radius=3.17, thickness=0.18, color=vector(0.08, 0.08, 0.08)))

# A partial shuttle stack beside the SRB gives context.
external_tank = cylinder(pos=vector(7.5, 13, 0), axis=vector(0, 66, 0), radius=5.0, color=vector(0.95, 0.47, 0.18), shininess=0.35)
orbiter_body = cylinder(pos=vector(13.0, 24, 0), axis=vector(0, 34, 0), radius=2.6, color=vector(0.88, 0.90, 0.91), shininess=0.45)
orbiter_nose = cone(pos=vector(13.0, 58, 0), axis=vector(0, 6, 0), radius=2.6, color=vector(0.80, 0.82, 0.84))
left_wing = box(pos=vector(13, 37, -5.3), size=vector(6.5, 1.0, 8.5), color=vector(0.80, 0.82, 0.84))
right_wing = box(pos=vector(13, 37, 5.3), size=vector(6.5, 1.0, 8.5), color=vector(0.80, 0.82, 0.84))
connectors = []
for y in [24, 47, 66]:
    connectors.append(cylinder(pos=vector(3.0, y, 0), axis=vector(4.6, 0, 0), radius=0.35, color=vector(0.26, 0.26, 0.26)))

stack_parts = [srb_body, srb_nose, srb_nozzle, external_tank, orbiter_body, orbiter_nose, left_wing, right_wing] + booster_bands + connectors
# VPython compound objects must be built from a non-empty object list.
stack = compound(stack_parts, pos=vector(0, 0, 0))

# Viewer mounting bracket and small camera node attached to side of SRB.
bracket = box(pos=vector(-3.6, 47, 0), size=vector(1.0, 5.0, 2.2), color=vector(0.18, 0.20, 0.22), shininess=0.4)
camera_node = sphere(pos=vector(-4.3, 47, 0), radius=0.8, color=vector(0.05, 0.06, 0.07), shininess=0.8)
lens = cylinder(pos=vector(-4.9, 47, 0), axis=vector(-1.0, 0, 0), radius=0.42, color=vector(0.02, 0.03, 0.05), shininess=0.9)
mount = compound([bracket, camera_node, lens])

# Exhaust flame and plume elements. These stay relative to the SRB base.
flame_core = cone(pos=vector(0, 8, 0), axis=vector(0, -16, 0), radius=2.5, color=vector(1.0, 0.78, 0.18), opacity=0.78, shininess=0.2)
flame_outer = cone(pos=vector(0, 7, 0), axis=vector(0, -28, 0), radius=5.5, color=vector(1.0, 0.34, 0.06), opacity=0.32, shininess=0.1)
plume_balls = []
for i in range(34):
    plume_balls.append(
        sphere(
            pos=vector(random.uniform(-3, 3), 2 - i * 3.5, random.uniform(-3, 3)),
            radius=random.uniform(2.5, 6.5),
            color=vector(0.92, 0.87, 0.78),
            opacity=random.uniform(0.12, 0.26),
            shininess=0,
        )
    )
shock_rings = []
for i in range(10):
    shock_rings.append(
        ring(
            pos=vector(0, -5 - i * 8, 0),
            axis=vector(0, 1, 0),
            radius=3 + i * 1.6,
            thickness=0.18,
            color=vector(1.0, 0.72, 0.24),
            opacity=0.22,
        )
    )

# Speed streaks make ascent readable in the camera view.
streaks = []
for i in range(28):
    z = random.uniform(-35, 35)
    x = random.uniform(-34, 34)
    y = random.uniform(30, 250)
    streaks.append(cylinder(pos=vector(x, y, z), axis=vector(0, -10, 0), radius=0.08, color=vector(0.76, 0.85, 0.92), opacity=0.36))

# HUD labels.
hud = label(
    pos=vector(-27, 76, 8),
    text="T+0s | SRB CAMERA | ignition hold",
    height=13,
    box=False,
    color=vector(0.05, 0.08, 0.10),
    opacity=0,
)
stage_label = label(
    pos=vector(0, 96, 0),
    text="viewer strapped to booster side",
    height=15,
    box=False,
    color=vector(0.08, 0.10, 0.12),
    opacity=0,
)

# ---------- Controls ----------

follow_camera = True
shake_enabled = True
paused = False
plume_visible = True
hud_visible = True
booster_visible = True
thrust_scale = 1.0
time_scale = 1.0
shake_scale = 1.0
cloud_visibility = 1.0
reset_requested = False


def set_stack_visibility(flag):
    for obj in stack_parts:
        obj.visible = flag
    mount.visible = True


def keydown(evt):
    global follow_camera, shake_enabled, paused, plume_visible, hud_visible, booster_visible
    global thrust_scale, time_scale, shake_scale, cloud_visibility, reset_requested
    k = evt.key.lower()
    if k == 'c':
        follow_camera = not follow_camera
    elif k == 's':
        shake_enabled = not shake_enabled
    elif k == 'p':
        paused = not paused
    elif k == 'r':
        reset_requested = True
    elif k == 'f':
        plume_visible = not plume_visible
    elif k == 'h':
        hud_visible = not hud_visible
    elif k == 'b':
        booster_visible = not booster_visible
        set_stack_visibility(booster_visible)
    elif k == 'up':
        time_scale = clamp(time_scale + 0.15, 0.25, 2.5)
    elif k == 'down':
        time_scale = clamp(time_scale - 0.15, 0.25, 2.5)
    elif k == 'right':
        thrust_scale = clamp(thrust_scale + 0.10, 0.35, 2.2)
    elif k == 'left':
        thrust_scale = clamp(thrust_scale - 0.10, 0.35, 2.2)
    elif k in ['+', '=']:
        shake_scale = clamp(shake_scale + 0.15, 0.0, 3.0)
    elif k in ['-', '_']:
        shake_scale = clamp(shake_scale - 0.15, 0.0, 3.0)
    elif k == ']':
        cloud_visibility = clamp(cloud_visibility + 0.15, 0.0, 1.5)
    elif k == '[':
        cloud_visibility = clamp(cloud_visibility - 0.15, 0.0, 1.5)

scene.bind('keydown', keydown)
controls = label(
    pos=vector(30, 16, 28),
    text="",
    height=11,
    box=False,
    color=vector(0.08, 0.08, 0.08),
    opacity=0,
)

# ---------- Simulation state ----------

t = 0.0
dt = 0.025
altitude = 0.0
velocity = 0.0
max_time = 92.0
separated = False
sep_time = None

initial_stack_pos = vector(0, 0, 0)


def reset_simulation():
    global t, altitude, velocity, separated, sep_time, reset_requested
    t = 0.0
    altitude = 0.0
    velocity = 0.0
    separated = False
    sep_time = None
    reset_requested = False
    stack.pos = initial_stack_pos
    # Do not set stack.axis here. A VPython compound has its own internal
    # orientation axis; forcing it to vector(0, 1, 0) rotates the already
    # vertical rocket stack and makes the booster look off-angle.
    mount.pos = vector(0, 0, 0)
    flame_core.visible = plume_visible
    flame_outer.visible = plume_visible
    flame_core.opacity = 0.78
    flame_outer.opacity = 0.32
    stage_label.text = "viewer strapped to booster side"
    scene.range = 55
    scene.background = vector(0.78, 0.90, 1.0)


while True:
    rate(40)
    if reset_requested or t > max_time:
        reset_simulation()
    if paused:
        hud.text = "PAUSED | press P to resume | R reset"
        continue

    scaled_dt = dt * time_scale
    t += scaled_dt

    # Acceleration profile: heavy shake at ignition, then increasing climb, then separation.
    if t < 5:
        thrust = 0.12 + 0.03 * t
        phase_text = "ignition thunder"
    elif t < 42:
        thrust = 0.33 + 0.010 * t
        phase_text = "launch pad falling away"
    elif t < 68:
        thrust = 0.78 - 0.004 * (t - 42)
        phase_text = "cloud punch-through"
    elif t < 76:
        thrust = 0.36
        phase_text = "thin air / Earth curve visible"
    else:
        thrust = 0.03
        phase_text = "SRB separation drift"
        if not separated:
            separated = True
            sep_time = t

    if not separated:
        velocity = velocity * 0.992 + thrust * thrust_scale
        altitude += velocity * scaled_dt * 7.2
    else:
        # After separation the booster tumbles gently away while the flame dies.
        velocity = velocity * 0.985 - 0.018
        altitude += velocity * scaled_dt * 5.2

    # Scale altitude into visual height and slight downrange curve.
    visual_y = altitude
    visual_x = 0.045 * altitude + 5 * math.sin(t * 0.05)
    visual_z = 0.018 * altitude * math.sin(t * 0.035)

    shake_amp = 0.0
    if shake_enabled:
        if t < 10:
            shake_amp = lerp(1.15, 0.70, t / 10) * shake_scale
        elif not separated:
            shake_amp = (0.55 + 0.20 * math.sin(t * 3.0)) * shake_scale
        else:
            shake_amp = 0.16 * shake_scale
    shake = vector(
        random.uniform(-shake_amp, shake_amp),
        random.uniform(-shake_amp * 0.42, shake_amp * 0.42),
        random.uniform(-shake_amp, shake_amp),
    )

    stack.pos = vector(visual_x, visual_y, visual_z) + shake * 0.18

    if separated:
        since_sep = t - sep_time
        # Keep the compound orientation unchanged so the SRB remains visually aligned.
        # Separation is shown by drifting away, fading flame, and quieter camera motion
        # instead of rotating the compound axis.
        stack.pos += vector(-since_sep * 1.2, -0.18 * since_sep * since_sep, 0.6 * since_sep)
        flame_core.opacity = max(0, 0.60 - since_sep * 0.08)
        flame_outer.opacity = max(0, 0.22 - since_sep * 0.035)
        if since_sep > 8:
            flame_core.visible = False
            flame_outer.visible = False
            stage_label.text = "separation: sudden quiet, booster drifting away"

    # Mount follows the SRB side; intentionally separate from compound so it can visibly shake more.
    mount.pos = stack.pos + vector(-0.05 * altitude / 100, 0, 0) + shake * 0.28

    # Flame tracks booster nozzle.
    nozzle_world = stack.pos + vector(0, 7.5, 0)
    flame_core.pos = nozzle_world + vector(0, -0.5, 0)
    flame_outer.pos = nozzle_world + vector(0, -2.0, 0)
    flame_len = 16 + 12 * clamp(velocity / 28, 0, 1)
    if separated:
        flame_len = max(0.5, flame_len * max(0, 1 - (t - sep_time) / 7))
    flame_core.axis = vector(0, -flame_len * 0.65, 0)
    flame_outer.axis = vector(0, -flame_len * 1.15, 0)
    flame_core.radius = 2.2 + 0.7 * math.sin(t * 19)
    flame_outer.radius = 5.0 + 1.4 * math.sin(t * 11)
    flame_core.color = color_lerp(vector(1.0, 0.95, 0.55), vector(1.0, 0.35, 0.05), 0.5 + 0.5 * math.sin(t * 23))

    flame_core.visible = plume_visible and (not separated or flame_core.opacity > 0.01)
    flame_outer.visible = plume_visible and (not separated or flame_outer.opacity > 0.01)

    # Plume stretches from booster toward pad/sky behind it.
    for i, p in enumerate(plume_balls):
        age = i / len(plume_balls)
        trail_len = 3.5 + 5.5 * clamp(velocity / 26, 0, 1)
        swirl = vector(
            math.sin(t * (1.5 + age) + i) * (2 + 22 * age),
            -i * trail_len,
            math.cos(t * (1.7 + age) + i * 0.7) * (2 + 22 * age),
        )
        p.pos = nozzle_world + vector(0, -6, 0) + swirl
        p.radius = 2.0 + age * 10 + 0.7 * math.sin(t * 6 + i)
        p.opacity = max(0.0, (0.25 - age * 0.17) * (0.2 if separated else 1.0)) if plume_visible else 0
        if p.pos.y < 8:
            p.color = vector(0.82, 0.79, 0.72)
        else:
            p.color = vector(0.94, 0.90, 0.82)

    # Mach/shock rings in the exhaust column.
    for i, r in enumerate(shock_rings):
        age = i / len(shock_rings)
        r.pos = nozzle_world + vector(0, -10 - i * (5.5 + 4.5 * clamp(velocity / 24, 0, 1)), 0)
        r.radius = 4 + i * 1.25 + 1.1 * math.sin(t * 7 + i)
        r.opacity = max(0, (0.23 - i * 0.016) * (0.15 if separated else 1.0)) if plume_visible else 0

    # Pad/tower shrink visually by being far below; keep physical objects where they are.
    pad.opacity = clamp(1 - altitude / 900, 0.08, 1)
    flame_trench.opacity = clamp(1 - altitude / 650, 0.04, 1)
    for obj in tower_parts + pad_markers:
        obj.opacity = clamp(1 - altitude / 600, 0.05, 1)

    # Clouds drift past the camera and thin out above the atmosphere.
    for idx, c in enumerate(clouds):
        c.pos.x += 0.012 * math.sin(t * 0.7 + idx)
        c.pos.z += 0.015 * math.cos(t * 0.5 + idx)
        vertical_distance = abs(c.pos.y - visual_y)
        c.opacity = clamp(0.30 - vertical_distance / 180, 0.02, 0.34) * cloud_visibility
        if vertical_distance < 25:
            c.radius = c.radius * 0.997 + 13 * 0.003

    # Speed streaks fall past the viewer, reinforcing motion.
    for s in streaks:
        s.pos.y -= 1.5 + velocity * 0.55
        if s.pos.y < visual_y - 120:
            s.pos = vector(visual_x + random.uniform(-45, 45), visual_y + random.uniform(60, 180), visual_z + random.uniform(-45, 45))
        s.opacity = 0.20 + 0.22 * clamp(velocity / 22, 0, 1)
        s.axis = vector(0, -8 - velocity * 0.28, 0)

    # Earth curvature becomes more obvious with altitude; sky darkens gently above atmosphere.
    sky_blend = clamp((altitude - 260) / 420, 0, 1)
    scene.background = color_lerp(vector(0.78, 0.90, 1.0), vector(0.04, 0.07, 0.14), sky_blend)
    earth.color = color_lerp(vector(0.40, 0.72, 0.95), vector(0.18, 0.42, 0.78), sky_blend)
    earth.pos = vector(visual_x * 0.25, -earth_radius_visual - 8 - altitude * 0.08, visual_z * 0.25)
    for i, r in enumerate(horizon_rings):
        r.pos = vector(visual_x * 0.18, -12 - i * 4 - altitude * 0.10, visual_z * 0.18)
        r.radius = 235 + i * 58 + altitude * 0.25
        r.opacity = clamp(0.28 - i * 0.04 + sky_blend * 0.18, 0.02, 0.42)

    # Follow-camera places viewer just off the SRB side, looking down and backward along flame.
    if follow_camera:
        camera_mount = stack.pos + vector(-17, 45, 15) + shake * 0.75
        look_target = stack.pos + vector(2, 22, -18)
        if separated:
            look_target = stack.pos + vector(0, 26, 0)
            camera_mount = stack.pos + vector(-34, 48, 26) + shake * 0.25
        scene.camera.pos = camera_mount
        scene.camera.axis = look_target - camera_mount
        scene.center = look_target
        scene.range = lerp(scene.range, 42 + 0.015 * altitude, 0.025)

    # Labels follow the camera region.
    hud.pos = stack.pos + vector(-28, 78, 10)
    stage_label.pos = stack.pos + vector(3, 95, 0)
    controls.pos = stack.pos + vector(30, 18, 28)
    hud.visible = hud_visible
    stage_label.visible = hud_visible
    controls.visible = hud_visible
    controls.text = ("Keys: C camera | P pause | R reset | S shake | F plume | B booster | H HUD\n"
                     "Up/Down speed %.2fx | Left/Right thrust %.2fx | +/- shake %.2fx | [/] clouds %.2fx"
                     % (time_scale, thrust_scale, shake_scale, cloud_visibility))
    hud.text = "T+%02ds | altitude %.0f | speed %.1f | %s" % (int(t), altitude, velocity, phase_text)

    # Stage label changes at major visual beats.
    if 10 < t < 22:
        stage_label.text = "the launch pad drops away beneath the booster"
    elif 35 < t < 55:
        stage_label.text = "white cloud layers whip past the side camera"
    elif 58 < t < 75:
        stage_label.text = "Earth bends into a blue arc below the plume"
