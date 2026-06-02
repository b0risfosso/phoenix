"""
Quiet Boom Threshold

Story:
    NASA's X-59 prepares for supersonic flight testing. The aircraft accelerates
    toward the sound barrier, but instead of releasing a violent sonic boom, it
    shapes shockwaves into a soft pressure ripple across the sky.

Simulation seed:
    NASA's X-59 accelerates toward the sound barrier, but instead of releasing a
    violent sonic boom, it shapes shockwaves into a soft pressure ripple across
    the sky.

Controls:
    Mouse       : drag / scroll to control camera
    Space       : pause / resume
    R           : reset acceleration run
    C           : toggle camera follow
    S           : toggle shockwave/ripple field
    T           : toggle telemetry markers
    Up / W      : increase simulation speed
    Down / S    : decrease simulation speed

Run:
    python quiet_boom_threshold_x59.py

Requires:
    pip install vpython
"""

from vpython import *
import math
import random

# -----------------------------
# Scene setup
# -----------------------------
scene = canvas(
    title="Quiet Boom Threshold - X-59",
    width=1200,
    height=780,
    background=vector(0.82, 0.92, 1.0),
    center=vector(0, 1.4, 0),
)
scene.forward = vector(-0.62, -0.20, -0.76)
scene.up = vector(0, 1, 0)
scene.range = 15.0

scene.userspin = True
scene.userzoom = True
scene.userpan = True

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return vector(
        lerp(a.x, b.x, t),
        lerp(a.y, b.y, t),
        lerp(a.z, b.z, t),
    )


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


# -----------------------------
# Colors
# -----------------------------
SKY_TOP = vector(0.72, 0.88, 1.0)
SKY_LOW = vector(0.90, 0.96, 1.0)
AIR_BLUE = vector(0.48, 0.76, 1.0)
SOFT_RIPPLE = vector(0.50, 0.95, 1.0)
PRESSURE_GOLD = vector(1.0, 0.78, 0.28)
PRESSURE_RED = vector(1.0, 0.32, 0.22)
X59_WHITE = vector(0.88, 0.90, 0.88)
X59_BLUE = vector(0.05, 0.15, 0.42)
X59_RED = vector(0.88, 0.10, 0.10)
X59_DARK = vector(0.12, 0.14, 0.16)
GROUND = vector(0.56, 0.72, 0.45)

# -----------------------------
# Environment
# -----------------------------
ground = box(
    pos=vector(0, -2.25, 0),
    size=vector(34, 0.08, 18),
    color=GROUND,
    opacity=0.48,
)

horizon = box(
    pos=vector(0, -1.85, 4.8),
    size=vector(34, 0.05, 0.08),
    color=vector(0.48, 0.62, 0.42),
    opacity=0.55,
)

# Light cloud streaks.
clouds = []
for i in range(28):
    x = random.uniform(-16, 16)
    y = random.uniform(2.8, 7.4)
    z = random.uniform(-6.0, 6.0)
    cloud = ellipsoid(
        pos=vector(x, y, z),
        length=random.uniform(0.8, 2.8),
        height=random.uniform(0.05, 0.18),
        width=random.uniform(0.25, 0.7),
        color=vector(1.0, 1.0, 1.0),
        opacity=random.uniform(0.28, 0.62),
    )
    clouds.append({"obj": cloud, "speed": random.uniform(0.004, 0.014), "phase": random.random() * math.tau})

# Altitude lane and speed guide.
flight_lane = cylinder(
    pos=vector(-14, 2.1, 0),
    axis=vector(28, 0, 0),
    radius=0.018,
    color=vector(0.20, 0.48, 0.70),
    opacity=0.28,
)

mach_one_marker = ring(
    pos=vector(1.2, 2.1, 0),
    axis=vector(1, 0, 0),
    radius=1.25,
    thickness=0.025,
    color=PRESSURE_GOLD,
    opacity=0.55,
    emissive=True,
)

threshold_label = label(
    pos=vector(1.2, 3.65, 0),
    text="Mach 1 threshold",
    height=12,
    box=False,
    color=vector(0.26, 0.22, 0.08),
)

# -----------------------------
# X-59 model
# -----------------------------
plane_root_start = vector(-12.0, 2.1, 0.0)
plane_parts = []

# Long slender nose.
nose = cone(
    pos=plane_root_start + vector(0.98, 0, 0),
    axis=vector(2.15, 0, 0),
    radius=0.105,
    color=X59_WHITE,
)
plane_parts.append(nose)

# Main fuselage.
fuselage = cylinder(
    pos=plane_root_start + vector(-1.05, 0, 0),
    axis=vector(2.10, 0, 0),
    radius=0.18,
    color=X59_WHITE,
)
plane_parts.append(fuselage)

rear = cone(
    pos=plane_root_start + vector(-1.78, 0, 0),
    axis=vector(0.76, 0, 0),
    radius=0.20,
    color=X59_WHITE,
)
plane_parts.append(rear)

# Cockpit / canopy set high and aft relative to long nose.
canopy = ellipsoid(
    pos=plane_root_start + vector(0.20, 0.20, 0),
    length=0.52,
    height=0.16,
    width=0.22,
    color=vector(0.06, 0.24, 0.44),
    opacity=0.90,
    emissive=True,
)
plane_parts.append(canopy)

# Wings.
left_wing = box(
    pos=plane_root_start + vector(-0.42, -0.02, -0.55),
    size=vector(0.95, 0.055, 1.10),
    color=X59_BLUE,
    opacity=0.95,
)
right_wing = box(
    pos=plane_root_start + vector(-0.42, -0.02, 0.55),
    size=vector(0.95, 0.055, 1.10),
    color=X59_BLUE,
    opacity=0.95,
)
plane_parts.extend([left_wing, right_wing])

# Tail surfaces.
tail_fin = box(
    pos=plane_root_start + vector(-1.55, 0.36, 0),
    size=vector(0.40, 0.72, 0.06),
    color=X59_RED,
    opacity=0.95,
)
tail_l = box(
    pos=plane_root_start + vector(-1.64, 0.02, -0.34),
    size=vector(0.44, 0.045, 0.62),
    color=X59_BLUE,
    opacity=0.95,
)
tail_r = box(
    pos=plane_root_start + vector(-1.64, 0.02, 0.34),
    size=vector(0.44, 0.045, 0.62),
    color=X59_BLUE,
    opacity=0.95,
)
plane_parts.extend([tail_fin, tail_l, tail_r])

# Engine outlet and soft exhaust.
engine = cylinder(
    pos=plane_root_start + vector(-1.96, 0, 0),
    axis=vector(-0.25, 0, 0),
    radius=0.13,
    color=X59_DARK,
)
exhaust = cone(
    pos=plane_root_start + vector(-2.20, 0, 0),
    axis=vector(-0.78, 0, 0),
    radius=0.18,
    color=vector(0.45, 0.70, 1.0),
    opacity=0.28,
    emissive=True,
)
plane_parts.extend([engine, exhaust])

# NASA-like stripe without logos/text.
stripe = cylinder(
    pos=plane_root_start + vector(-0.92, 0.185, 0),
    axis=vector(1.62, 0, 0),
    radius=0.024,
    color=X59_RED,
)
plane_parts.append(stripe)

plane_offsets = {obj: obj.pos - plane_root_start for obj in plane_parts}

# -----------------------------
# Shockwave and quiet-ripple field
# -----------------------------
shock_rings = []
for i in range(26):
    ring_obj = ring(
        pos=plane_root_start + vector(-0.2 - i * 0.40, 0, 0),
        axis=vector(1, 0, 0),
        radius=0.15 + i * 0.06,
        thickness=0.012,
        color=AIR_BLUE,
        opacity=0.0,
        emissive=True,
    )
    shock_rings.append({"obj": ring_obj, "phase": i * 0.22, "index": i})

nose_pressure_lines = []
for i in range(18):
    angle = i * math.tau / 18
    line = cylinder(
        pos=plane_root_start + vector(3.05, 0, 0),
        axis=vector(-0.35, math.cos(angle) * 0.18, math.sin(angle) * 0.18),
        radius=0.008,
        color=SOFT_RIPPLE,
        opacity=0.0,
        emissive=True,
    )
    nose_pressure_lines.append({"obj": line, "angle": angle, "phase": random.random() * math.tau})

soft_ground_ripples = []
for i in range(18):
    ripple = ring(
        pos=vector(-10 + i * 1.15, -2.16, 0),
        axis=vector(0, 1, 0),
        radius=0.10,
        thickness=0.012,
        color=SOFT_RIPPLE,
        opacity=0.0,
        emissive=True,
    )
    soft_ground_ripples.append({"obj": ripple, "phase": random.random() * math.tau, "x": -10 + i * 1.15})

# Sharp boom warning wave, kept faint because this simulation is about avoiding it.
sharp_boom = ring(
    pos=vector(0, 2.1, 0),
    axis=vector(1, 0, 0),
    radius=0.5,
    thickness=0.030,
    color=PRESSURE_RED,
    opacity=0.0,
    emissive=True,
)

# Telemetry markers.
telemetry_markers = []
for i in range(12):
    marker = sphere(
        pos=vector(-12 + i * 2.1, 2.1, 1.75),
        radius=0.055,
        color=PRESSURE_GOLD,
        opacity=0.62,
        emissive=True,
    )
    telemetry_markers.append({"obj": marker, "phase": random.random() * math.tau})

# Soft pressure samples as floating dots around the aircraft.
pressure_dots = []
for i in range(65):
    p = sphere(
        pos=plane_root_start + vector(random.uniform(-4, 3), random.uniform(-1.2, 1.2), random.uniform(-1.8, 1.8)),
        radius=random.uniform(0.018, 0.055),
        color=SOFT_RIPPLE,
        opacity=0.0,
        emissive=True,
    )
    pressure_dots.append({
        "obj": p,
        "offset": vector(random.uniform(-4, 3), random.uniform(-1.2, 1.2), random.uniform(-1.8, 1.8)),
        "phase": random.random() * math.tau,
    })

# -----------------------------
# Labels
# -----------------------------
title = label(
    pos=vector(0, 6.1, -4.9),
    text="Quiet Boom Threshold",
    height=24,
    box=False,
    color=vector(0.08, 0.16, 0.28),
)
subtitle = label(
    pos=vector(0, 5.65, -4.9),
    text="The X-59 approaches Mach 1 and reshapes shockwaves into soft pressure ripples.",
    height=12,
    box=False,
    color=vector(0.12, 0.25, 0.38),
)
status = label(
    pos=vector(-8.9, 5.05, -4.9),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.05, 0.13, 0.22),
    background=vector(0.92, 0.97, 1.0),
    opacity=0.78,
)
legend = label(
    pos=vector(8.4, 5.0, -4.9),
    text="Blue rings: shaped shockwave field\nCyan ground rings: soft pressure ripple\nGold marker: Mach 1 threshold\nRed flash: suppressed sharp boom",
    height=12,
    box=True,
    border=8,
    color=vector(0.05, 0.13, 0.22),
    background=vector(0.92, 0.97, 1.0),
    opacity=0.78,
)

# -----------------------------
# State and controls
# -----------------------------
paused = False
camera_follow = False
show_shock_field = True
show_telemetry = True
speed = 1.0
sim_t = 0.0
run_progress = 0.0
plane_root = vector(plane_root_start.x, plane_root_start.y, plane_root_start.z)


def reset_sim():
    global sim_t, run_progress, speed, plane_root
    sim_t = 0.0
    run_progress = 0.0
    speed = 1.0
    plane_root = vector(plane_root_start.x, plane_root_start.y, plane_root_start.z)


def on_keydown(evt):
    global paused, camera_follow, show_shock_field, show_telemetry, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_sim()
    elif key == "c":
        camera_follow = not camera_follow
    elif key == "t":
        show_telemetry = not show_telemetry
        for item in telemetry_markers:
            item["obj"].visible = show_telemetry
    elif key == "s":
        show_shock_field = not show_shock_field
        for item in shock_rings:
            item["obj"].visible = show_shock_field
        for item in nose_pressure_lines:
            item["obj"].visible = show_shock_field
        for item in pressure_dots:
            item["obj"].visible = show_shock_field
        for item in soft_ground_ripples:
            item["obj"].visible = show_shock_field
        sharp_boom.visible = show_shock_field
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down",):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)


# -----------------------------
# Plane transform
# -----------------------------
def update_plane(root, pitch, roll):
    global plane_root
    plane_root = root

    cp = math.cos(pitch)
    sp = math.sin(pitch)
    cr = math.cos(roll)
    sr = math.sin(roll)

    def transform_offset(v):
        # Plane local x is forward; y vertical; z lateral.
        y1 = v.y * cp - v.x * sp
        x1 = v.y * sp + v.x * cp
        z1 = v.z

        y2 = y1 * cr - z1 * sr
        z2 = y1 * sr + z1 * cr
        return vector(x1, y2, z2)

    for obj, offset in plane_offsets.items():
        new_offset = transform_offset(offset)
        obj.pos = root + new_offset

        if hasattr(obj, "axis"):
            base_axis = obj.axis
            # Use original part type axes from geometric placement.
            if obj is nose:
                obj.axis = transform_offset(vector(2.15, 0, 0))
            elif obj is fuselage:
                obj.axis = transform_offset(vector(2.10, 0, 0))
            elif obj is rear:
                obj.axis = transform_offset(vector(0.76, 0, 0))
            elif obj is engine:
                obj.axis = transform_offset(vector(-0.25, 0, 0))
            elif obj is exhaust:
                obj.axis = transform_offset(vector(-0.78, 0, 0))
            elif obj is stripe:
                obj.axis = transform_offset(vector(1.62, 0, 0))


# -----------------------------
# Main animation loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Mach estimate: {lerp(0.65, 1.18, run_progress):.2f}\n"
            f"Speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.018 * speed
    sim_t += dt

    # Progress repeats. The plane accelerates from subsonic, crosses Mach 1,
    # then sustains a gentle supersonic regime before looping.
    run_progress = (sim_t * 0.028) % 1.0
    accel_curve = 1.0 - (1.0 - run_progress) ** 2.2
    mach = lerp(0.65, 1.18, accel_curve)

    # X position moves across the sky; altitude gently rises through test corridor.
    x = lerp(-12.0, 12.5, accel_curve)
    y = 2.1 + 0.25 * math.sin(sim_t * 0.55) + 0.45 * clamp((mach - 0.95) / 0.25)
    z = 0.20 * math.sin(sim_t * 0.38)
    pitch = 0.035 * math.sin(sim_t * 0.7) - 0.04 * clamp((mach - 1.0) / 0.18)
    roll = 0.055 * math.sin(sim_t * 1.3) * (1.0 - clamp((mach - 1.0) / 0.3))
    update_plane(vector(x, y, z), pitch, roll)

    # Mach threshold intensity.
    near_mach_one = math.exp(-((mach - 1.0) ** 2) / 0.0045)
    supersonic = clamp((mach - 0.98) / 0.18)
    quiet_shaping = clamp((mach - 0.88) / 0.30)

    # Exhaust changes with acceleration.
    flame = 0.5 + 0.5 * math.sin(sim_t * 18.0)
    exhaust.radius = 0.16 + 0.10 * flame * quiet_shaping
    exhaust.opacity = 0.18 + 0.34 * quiet_shaping * flame
    exhaust.color = mix_color(vector(0.42, 0.70, 1.0), PRESSURE_GOLD, 0.30 * near_mach_one)

    # Mach one marker pulse.
    mach_one_marker.radius = 1.18 + 0.18 * near_mach_one * math.sin(sim_t * 7.0) ** 2
    mach_one_marker.opacity = 0.28 + 0.45 * near_mach_one
    threshold_label.opacity = 0.45 + 0.55 * near_mach_one

    # Nose pressure lines: shockwaves form and are stretched into a smooth wavefront.
    nose_tip = plane_root + vector(3.08, 0, 0)
    for item in nose_pressure_lines:
        obj = item["obj"]
        ang = item["angle"]
        pulse = 0.5 + 0.5 * math.sin(sim_t * 5.0 + item["phase"])
        spread = 0.25 + 0.60 * quiet_shaping + 0.25 * near_mach_one * pulse
        obj.pos = nose_tip + vector(-0.05, 0, 0)
        obj.axis = vector(
            -0.70 - 0.55 * supersonic,
            math.cos(ang) * spread,
            math.sin(ang) * spread,
        )
        obj.opacity = (0.10 + 0.48 * quiet_shaping * pulse) if show_shock_field else 0.0
        obj.radius = 0.006 + 0.010 * quiet_shaping
        obj.color = mix_color(AIR_BLUE, SOFT_RIPPLE, 0.75 * quiet_shaping)

    # Shock rings travel aft. Near Mach 1 they would sharpen, but the X-59
    # shaping splits them into smoother, separated pulses.
    for item in shock_rings:
        idx = item["index"]
        obj = item["obj"]

        aft = 0.35 + idx * (0.24 + 0.11 * supersonic)
        wave_phase = (sim_t * 2.0 - idx * 0.37) % math.tau
        softness = 0.5 + 0.5 * math.sin(wave_phase)

        obj.pos = plane_root + vector(-aft, 0, 0)
        obj.axis = vector(1, 0, 0)
        obj.radius = 0.18 + idx * 0.044 + 0.45 * supersonic + 0.10 * softness
        obj.thickness = 0.006 + 0.018 * (1.0 - near_mach_one * 0.55) + 0.010 * quiet_shaping
        obj.color = mix_color(AIR_BLUE, SOFT_RIPPLE, 0.68 * quiet_shaping)
        obj.opacity = (0.03 + 0.30 * quiet_shaping * softness * (1.0 - idx / 34.0)) if show_shock_field else 0.0

    # A sharp boom flash appears faintly and is immediately suppressed into soft ripples.
    sharp_boom.pos = plane_root + vector(-0.9, 0, 0)
    sharp_boom.radius = 0.55 + 1.35 * near_mach_one
    sharp_boom.thickness = 0.020 + 0.030 * near_mach_one
    sharp_boom.opacity = 0.10 * near_mach_one * (1.0 - 0.80 * quiet_shaping)
    sharp_boom.color = mix_color(PRESSURE_RED, SOFT_RIPPLE, quiet_shaping)

    # Soft pressure ripples reach the ground as low-amplitude cyan rings.
    ground_hit_x = plane_root.x - 1.5
    for item in soft_ground_ripples:
        obj = item["obj"]
        delay = abs(item["x"] - ground_hit_x) / 12.0
        phase = (sim_t * 1.4 - delay * 4.0 + item["phase"]) % math.tau
        local_wave = max(0.0, math.sin(phase))
        strength = quiet_shaping * local_wave * clamp(1.0 - abs(item["x"] - ground_hit_x) / 8.5)
        obj.pos = vector(item["x"], -2.16, 0)
        obj.radius = 0.10 + 1.05 * strength
        obj.opacity = 0.30 * strength if show_shock_field else 0.0
        obj.thickness = 0.008 + 0.014 * strength

    # Floating pressure dots visualize the shaped wave as a soft distributed field.
    for item in pressure_dots:
        obj = item["obj"]
        offset = item["offset"]
        drift = vector(
            -0.55 * quiet_shaping * math.sin(sim_t * 0.9 + item["phase"]),
            0.10 * math.sin(sim_t * 1.4 + item["phase"]),
            0.14 * math.cos(sim_t * 1.1 + item["phase"]),
        )
        obj.pos = plane_root + offset + drift
        pulse = 0.5 + 0.5 * math.sin(sim_t * 3.4 + item["phase"] - offset.x)
        obj.opacity = (0.04 + 0.38 * quiet_shaping * pulse) if show_shock_field else 0.0
        obj.radius = 0.014 + 0.045 * pulse * quiet_shaping
        obj.color = mix_color(AIR_BLUE, SOFT_RIPPLE, 0.65 + 0.35 * pulse)

    # Telemetry markers brighten as aircraft passes each sample point.
    for item in telemetry_markers:
        obj = item["obj"]
        distance = abs(obj.pos.x - plane_root.x)
        active = clamp(1.0 - distance / 2.8)
        obj.radius = 0.045 + 0.08 * active
        obj.opacity = 0.22 + 0.62 * active if show_telemetry else 0.0
        obj.color = mix_color(PRESSURE_GOLD, SOFT_RIPPLE, 0.45 * active)

    # Clouds drift slowly.
    for item in clouds:
        obj = item["obj"]
        obj.pos.x -= item["speed"] * speed
        obj.opacity = 0.25 + 0.35 * math.sin(sim_t * 0.4 + item["phase"]) ** 2
        if obj.pos.x < -17:
            obj.pos.x = 17
            obj.pos.y = random.uniform(2.8, 7.4)
            obj.pos.z = random.uniform(-6.0, 6.0)

    # Camera follow is optional; otherwise mouse camera remains fully user-controlled.
    if camera_follow:
        scene.center = plane_root + vector(0.2, 0.2, 0)
        scene.forward = safe_norm(plane_root + vector(2.5, 0.2, 0) - (plane_root + vector(-4.2, 1.3, -5.2)))
        scene.range = 8.0

    pressure_label = "subsonic"
    if mach >= 1.0:
        pressure_label = "soft supersonic ripple"
    elif mach > 0.92:
        pressure_label = "near sound barrier"

    status.text = (
        f"Acceleration run: {int(run_progress * 100)}%\n"
        f"Mach estimate: {mach:.2f}\n"
        f"Flight condition: {pressure_label}\n"
        f"Shock shaping: {int(quiet_shaping * 100)}%\n"
        f"Sharp boom suppression: {int(quiet_shaping * 92)}%\n"
        f"Shock field: {'on' if show_shock_field else 'off'}\n"
        f"Telemetry: {'on' if show_telemetry else 'off'} | Camera follow: {'on' if camera_follow else 'off'}\n"
        f"Speed: {speed:.2f}x\n"
        "Mouse camera | Space pause | R reset | C follow | S shock field | T telemetry"
    )
