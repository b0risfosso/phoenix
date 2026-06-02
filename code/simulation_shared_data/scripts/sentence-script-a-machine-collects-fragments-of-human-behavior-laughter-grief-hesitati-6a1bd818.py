from vpython import *
import math
import random

# ------------------------------------------------------------
# A machine collects fragments of human behavior: laughter,
# grief, hesitation, prayer, silence, and stores them as glowing
# particles inside its chest.
# ------------------------------------------------------------

scene.title = "Machine Collecting Human Behavior Fragments - Open Floor"
scene.width = 1200
scene.height = 760
scene.background = vector(0.93, 0.91, 0.86)
scene.center = vector(0, 1.7, 0)
scene.forward = vector(-0.55, -0.25, -0.9)
scene.range = 8.2

# -----------------------------
# Materials / colors
# -----------------------------
brass = vector(0.78, 0.55, 0.22)
dark_brass = vector(0.45, 0.30, 0.12)
glass_color = vector(0.75, 0.95, 1.0)
wood = vector(0.55, 0.42, 0.30)
shadow = vector(0.34, 0.32, 0.28)
soft_black = vector(0.08, 0.075, 0.065)

fragment_specs = {
    "laughter": {
        "color": vector(1.0, 0.84, 0.20),
        "shape": "spark",
        "orbit": 1.0,
        "pulse": 3.4,
        "meaning": "bright quick rhythm",
    },
    "grief": {
        "color": vector(0.22, 0.38, 0.95),
        "shape": "drop",
        "orbit": 1.25,
        "pulse": 1.15,
        "meaning": "heavy downward memory",
    },
    "hesitation": {
        "color": vector(0.72, 0.62, 0.95),
        "shape": "small",
        "orbit": 0.70,
        "pulse": 4.6,
        "meaning": "stutter before motion",
    },
    "prayer": {
        "color": vector(0.96, 0.92, 0.74),
        "shape": "halo",
        "orbit": 1.55,
        "pulse": 0.85,
        "meaning": "upward quiet request",
    },
    "silence": {
        "color": vector(0.58, 0.88, 0.82),
        "shape": "still",
        "orbit": 0.45,
        "pulse": 0.35,
        "meaning": "nearly motionless center",
    },
}

# -----------------------------
# Open workshop environment without walls
# -----------------------------
floor = box(pos=vector(0, -0.08, 0), size=vector(16, 0.16, 12), color=wood)

# Workbench and shelves
bench = box(pos=vector(4.5, 0.8, -4.8), size=vector(5.2, 0.35, 1.2), color=vector(0.45, 0.29, 0.16))
for x in [2.5, 6.5]:
    cylinder(pos=vector(x, -0.05, -5.25), axis=vector(0, 0.85, 0), radius=0.08, color=dark_brass)
    cylinder(pos=vector(x, -0.05, -4.35), axis=vector(0, 0.85, 0), radius=0.08, color=dark_brass)

for i, y in enumerate([2.3, 3.25, 4.2]):
    box(pos=vector(-5.7, y, -5.85), size=vector(3.0, 0.12, 0.28), color=vector(0.41, 0.29, 0.19))
    for j in range(5):
        cylinder(pos=vector(-6.9 + j * 0.55, y + 0.1, -5.75), axis=vector(0, 0.38, 0), radius=0.08,
                 color=glass_color, opacity=0.35)

# Hanging lamp
lamp_cord = cylinder(pos=vector(0, 6.2, -2.5), axis=vector(0, -1.3, 0), radius=0.025, color=soft_black)
lamp_shade = cone(pos=vector(0, 4.7, -2.5), axis=vector(0, -0.45, 0), radius=0.65, color=vector(0.22, 0.20, 0.18))
lamp_glow = sphere(pos=vector(0, 4.28, -2.5), radius=0.22, color=vector(1.0, 0.82, 0.44), emissive=True)
local_light(pos=lamp_glow.pos, color=vector(0.75, 0.60, 0.35))

# -----------------------------
# Machine body
# -----------------------------
machine_parts = []

base = cylinder(pos=vector(0, 0.0, 0), axis=vector(0, 0.22, 0), radius=1.15, color=dark_brass)
machine_parts.append(base)

pelvis = box(pos=vector(0, 0.55, 0), size=vector(1.4, 0.5, 0.8), color=brass)
machine_parts.append(pelvis)

torso = box(pos=vector(0, 1.55, 0), size=vector(1.55, 1.65, 0.65), color=brass)
machine_parts.append(torso)

neck = cylinder(pos=vector(0, 2.42, 0), axis=vector(0, 0.35, 0), radius=0.18, color=dark_brass)
head = box(pos=vector(0, 2.98, 0), size=vector(1.0, 0.68, 0.62), color=brass)
machine_parts.extend([neck, head])

eye_l = sphere(pos=vector(-0.22, 3.04, -0.33), radius=0.075, color=vector(0.55, 0.9, 1.0), emissive=True)
eye_r = sphere(pos=vector(0.22, 3.04, -0.33), radius=0.075, color=vector(0.55, 0.9, 1.0), emissive=True)
machine_parts.extend([eye_l, eye_r])

# Glass chest chamber
chest_glass = sphere(pos=vector(0, 1.6, -0.39), radius=0.52, color=glass_color, opacity=0.23)
chest_core = sphere(pos=chest_glass.pos, radius=0.10, color=vector(0.35, 0.92, 1.0), emissive=True)
chest_ring_1 = ring(pos=chest_glass.pos, axis=vector(0, 0, 1), radius=0.56, thickness=0.025, color=dark_brass)
chest_ring_2 = ring(pos=chest_glass.pos, axis=vector(0, 1, 0), radius=0.56, thickness=0.018, color=dark_brass)
machine_parts.extend([chest_glass, chest_core, chest_ring_1, chest_ring_2])
local_light(pos=chest_core.pos, color=vector(0.35, 0.75, 1.0))

# Brass gears on shoulders/chest
gears = []
def make_gear(pos, radius, teeth, axis=vector(0, 0, 1)):
    hub = cylinder(pos=pos - axis.norm() * 0.035, axis=axis.norm() * 0.07, radius=radius * 0.55, color=dark_brass)
    outer = ring(pos=pos, axis=axis, radius=radius, thickness=0.04, color=brass)
    tooth_objs = []
    for k in range(teeth):
        ang = 2 * math.pi * k / teeth
        tooth_pos = pos + vector(math.cos(ang) * radius, math.sin(ang) * radius, 0)
        tooth = box(pos=tooth_pos, size=vector(0.13, 0.05, 0.08), color=brass)
        tooth.rotate(angle=ang, axis=axis, origin=tooth.pos)
        tooth_objs.append(tooth)
    gear = {"hub": hub, "outer": outer, "teeth": tooth_objs, "pos": pos, "axis": axis, "speed": random.choice([-1, 1]) * random.uniform(0.5, 1.3)}
    gears.append(gear)
    machine_parts.extend([hub, outer] + tooth_objs)
    return gear

make_gear(vector(-0.62, 1.87, -0.38), 0.27, 12)
make_gear(vector(0.62, 1.87, -0.38), 0.27, 12)
make_gear(vector(0, 1.05, -0.38), 0.22, 10)

# Arms and legs
left_upper_arm = cylinder(pos=vector(-0.86, 2.05, 0), axis=vector(-0.55, -0.55, 0), radius=0.09, color=dark_brass)
left_forearm = cylinder(pos=vector(-1.41, 1.50, 0), axis=vector(-0.25, -0.55, -0.08), radius=0.08, color=brass)
left_hand = sphere(pos=vector(-1.68, 0.88, -0.08), radius=0.15, color=dark_brass)

right_upper_arm = cylinder(pos=vector(0.86, 2.05, 0), axis=vector(0.55, -0.55, 0), radius=0.09, color=dark_brass)
right_forearm = cylinder(pos=vector(1.41, 1.50, 0), axis=vector(0.25, -0.55, -0.08), radius=0.08, color=brass)
right_hand = sphere(pos=vector(1.68, 0.88, -0.08), radius=0.15, color=dark_brass)

left_leg = cylinder(pos=vector(-0.42, 0.35, 0), axis=vector(0, -0.55, 0.15), radius=0.11, color=dark_brass)
right_leg = cylinder(pos=vector(0.42, 0.35, 0), axis=vector(0, -0.55, 0.15), radius=0.11, color=dark_brass)
left_foot = box(pos=vector(-0.42, -0.25, 0.2), size=vector(0.55, 0.12, 0.8), color=brass)
right_foot = box(pos=vector(0.42, -0.25, 0.2), size=vector(0.55, 0.12, 0.8), color=brass)
machine_parts.extend([
    left_upper_arm, left_forearm, left_hand, right_upper_arm, right_forearm, right_hand,
    left_leg, right_leg, left_foot, right_foot
])

# Glass tubes feeding into chest
tube_objs = []
tube_starts = [vector(-2.8, 0.75, -1.2), vector(2.8, 0.85, -1.4), vector(-2.4, 2.7, -1.0), vector(2.4, 2.7, -1.0), vector(0, 3.8, -1.25)]
for start in tube_starts:
    direction = chest_glass.pos - start
    tube = cylinder(pos=start, axis=direction, radius=0.045, color=glass_color, opacity=0.28)
    bead = sphere(pos=start, radius=0.11, color=glass_color, opacity=0.38)
    tube_objs.extend([tube, bead])

# -----------------------------
# Behavior fragments
# -----------------------------
fragment_labels = []
fragments = []
stored_particles = []
collection_trails = []

spawn_positions = {
    "laughter": vector(-4.5, 2.8, -1.4),
    "grief": vector(-4.0, 0.7, 0.8),
    "hesitation": vector(0.0, 3.7, -1.8),
    "prayer": vector(4.0, 2.6, -1.2),
    "silence": vector(4.5, 0.75, 0.9),
}

for name, pos in spawn_positions.items():
    spec = fragment_specs[name]
    color = spec["color"]
    if spec["shape"] == "drop":
        obj = sphere(pos=pos, radius=0.18, color=color, emissive=True)
        tail = cone(pos=pos + vector(0, 0.32, 0), axis=vector(0, -0.36, 0), radius=0.12, color=color, opacity=0.75)
        parts = [obj, tail]
    elif spec["shape"] == "halo":
        obj = sphere(pos=pos, radius=0.14, color=color, emissive=True)
        halo = ring(pos=pos, axis=vector(0, 1, 0), radius=0.27, thickness=0.018, color=color, opacity=0.8)
        parts = [obj, halo]
    elif spec["shape"] == "still":
        obj = sphere(pos=pos, radius=0.20, color=color, emissive=True, opacity=0.7)
        halo = ring(pos=pos, axis=vector(0, 0, 1), radius=0.34, thickness=0.012, color=color, opacity=0.25)
        parts = [obj, halo]
    else:
        obj = sphere(pos=pos, radius=0.16, color=color, emissive=True)
        parts = [obj]
        for n in range(6):
            ang = 2 * math.pi * n / 6
            spark = cylinder(pos=pos + vector(math.cos(ang)*0.18, math.sin(ang)*0.18, 0),
                             axis=vector(math.cos(ang)*0.18, math.sin(ang)*0.18, 0),
                             radius=0.015, color=color, emissive=True)
            parts.append(spark)
    local_light(pos=pos, color=color * 0.45)
    label_obj = label(pos=pos + vector(0, 0.45, 0), text=name, height=13, box=False, color=color, opacity=0)
    fragment_labels.append(label_obj)
    fragments.append({
        "name": name,
        "parts": parts,
        "origin": vector(pos.x, pos.y, pos.z),
        "pos": vector(pos.x, pos.y, pos.z),
        "collected": False,
        "t": random.uniform(0, 10),
        "phase": random.uniform(0, 2 * math.pi),
        "color": color,
        "label": label_obj,
        "pulse": spec["pulse"],
    })

# Each behavior has a faint source object in the workshop.
source_objects = []
source_objects.append(ring(pos=vector(-4.5, 0.04, -1.4), axis=vector(0, 1, 0), radius=0.55, thickness=0.02, color=fragment_specs["laughter"]["color"], opacity=0.45))
source_objects.append(cone(pos=vector(-4.0, 0.04, 0.8), axis=vector(0, 0.45, 0), radius=0.23, color=fragment_specs["grief"]["color"], opacity=0.38))
source_objects.append(box(pos=vector(0.0, 0.06, -1.8), size=vector(0.7, 0.08, 0.7), color=fragment_specs["hesitation"]["color"], opacity=0.35))
source_objects.append(cylinder(pos=vector(4.0, 0.04, -1.2), axis=vector(0, 0.55, 0), radius=0.09, color=fragment_specs["prayer"]["color"], opacity=0.45))
source_objects.append(sphere(pos=vector(4.5, 0.12, 0.9), radius=0.18, color=fragment_specs["silence"]["color"], opacity=0.35))

# Chest memory display
memory_panel = label(
    pos=vector(0, 4.25, 1.3),
    text="CHEST MEMORY: empty",
    height=15,
    box=True,
    border=8,
    color=vector(0.1, 0.1, 0.08),
    background=vector(0.92, 0.86, 0.68),
    opacity=0.72,
)
current_action_label = label(
    pos=vector(0, 3.75, 1.3),
    text="seeking first human fragment",
    height=13,
    box=False,
    color=vector(0.18, 0.14, 0.09),
    opacity=0,
)

# -----------------------------
# Helpers
# -----------------------------
def move_parts(parts, delta):
    for p in parts:
        p.pos += delta


def set_parts_pos(fragment, new_pos):
    delta = new_pos - fragment["pos"]
    fragment["pos"] = vector(new_pos.x, new_pos.y, new_pos.z)
    move_parts(fragment["parts"], delta)
    fragment["label"].pos += delta


def make_collection_trail(start, end, color):
    trail = curve(color=color, radius=0.018)
    steps = 12
    for i in range(steps + 1):
        f = i / steps
        lift = math.sin(math.pi * f) * 0.75
        p = start * (1 - f) + end * f + vector(0, lift, 0)
        trail.append(pos=p)
    collection_trails.append({"curve": trail, "life": 2.0})


def store_particle(name, color):
    angle = random.uniform(0, 2 * math.pi)
    radius = random.uniform(0.05, 0.34)
    height = random.uniform(-0.23, 0.25)
    pos = chest_glass.pos + vector(math.cos(angle) * radius, height, math.sin(angle) * radius * 0.45)
    p = sphere(pos=pos, radius=0.075, color=color, emissive=True)
    orbit = random.choice([-1, 1]) * random.uniform(0.6, 1.3)
    stored_particles.append({
        "name": name,
        "obj": p,
        "angle": angle,
        "radius": radius,
        "height": height,
        "orbit": orbit,
        "color": color,
        "pulse": fragment_specs[name]["pulse"],
    })


def update_memory_panel():
    names = [p["name"] for p in stored_particles]
    if not names:
        memory_panel.text = "CHEST MEMORY: empty"
        return
    unique = []
    for name in names:
        if name not in unique:
            unique.append(name)
    memory_panel.text = "CHEST MEMORY: " + "  |  ".join(unique)


# Gentle dust motes for workshop stillness
dust = []
for _ in range(65):
    dust.append(sphere(
        pos=vector(random.uniform(-7, 7), random.uniform(0.15, 5.5), random.uniform(-5.5, 4.5)),
        radius=random.uniform(0.008, 0.022),
        color=vector(0.95, 0.88, 0.68),
        opacity=random.uniform(0.12, 0.35),
    ))

# -----------------------------
# Main simulation loop
# -----------------------------
time = 0.0
fragment_index = 0
collection_timer = 0.0
pause_between_fragments = 1.2
machine_breath = 0.0
last_collected_name = None

while True:
    rate(60)
    dt = 1 / 60
    time += dt
    collection_timer += dt
    machine_breath += dt

    # Dust drift
    for d in dust:
        d.pos += vector(0.004 * math.sin(time * 0.7 + d.pos.y), 0.002 * math.sin(time + d.pos.x), 0)
        if d.pos.x > 7.4:
            d.pos.x = -7.4

    # Moving gears
    gear_intensity = 0.75 + 0.35 * len(stored_particles)
    for gear in gears:
        angle = gear["speed"] * gear_intensity * dt
        gear["hub"].rotate(angle=angle, axis=gear["axis"], origin=gear["pos"])
        gear["outer"].rotate(angle=angle, axis=gear["axis"], origin=gear["pos"])
        for tooth in gear["teeth"]:
            tooth.rotate(angle=angle, axis=gear["axis"], origin=gear["pos"])

    # Machine slight awakening movement.
    sway = math.sin(machine_breath * (0.9 + 0.08 * len(stored_particles))) * 0.018
    head.pos.x = sway
    neck.pos.x = sway * 0.5
    eye_l.pos.x = -0.22 + sway
    eye_r.pos.x = 0.22 + sway
    eye_brightness = 0.35 + min(0.6, len(stored_particles) * 0.12) + 0.12 * math.sin(time * 3.0)
    eye_l.color = vector(0.35, 0.65 + eye_brightness * 0.25, 1.0)
    eye_r.color = eye_l.color

    # Arms lift toward active fragment.
    active_fragment = fragments[fragment_index % len(fragments)]
    active_pos = active_fragment["pos"]
    target_left_axis = vector(-0.55, -0.45 + 0.09 * math.sin(time * 1.7), -0.04)
    target_right_axis = vector(0.55, -0.45 + 0.09 * math.cos(time * 1.5), -0.04)
    if not active_fragment["collected"]:
        if active_pos.x < 0:
            target_left_axis = vector(-0.62, -0.25 + 0.06 * math.sin(time * 4), -0.16)
        else:
            target_right_axis = vector(0.62, -0.25 + 0.06 * math.sin(time * 4), -0.16)
    left_upper_arm.axis = target_left_axis
    left_forearm.pos = left_upper_arm.pos + left_upper_arm.axis
    left_forearm.axis = vector(-0.25, -0.52, -0.08)
    left_hand.pos = left_forearm.pos + left_forearm.axis
    right_upper_arm.axis = target_right_axis
    right_forearm.pos = right_upper_arm.pos + right_upper_arm.axis
    right_forearm.axis = vector(0.25, -0.52, -0.08)
    right_hand.pos = right_forearm.pos + right_forearm.axis

    # Float behavior fragments before collection.
    for frag in fragments:
        if not frag["collected"]:
            frag["t"] += dt
            pos = frag["origin"] + vector(
                0.12 * math.sin(frag["t"] * frag["pulse"] + frag["phase"]),
                0.14 * math.sin(frag["t"] * 1.2 + frag["phase"]),
                0.06 * math.cos(frag["t"] * 0.9 + frag["phase"]),
            )
            set_parts_pos(frag, pos)
            # Pulse opacity/size for visible personality.
            pulse_scale = 1.0 + 0.18 * math.sin(time * frag["pulse"] + frag["phase"])
            for p in frag["parts"]:
                if hasattr(p, "radius"):
                    # Preserve rough shape without accumulating growth.
                    if p.__class__.__name__ == "sphere":
                        p.radius = max(0.045, min(0.28, p.radius * 0.97 + (0.15 * pulse_scale) * 0.03))
        else:
            # Hide collected source fragments after they become memory.
            for p in frag["parts"]:
                p.visible = False
            frag["label"].visible = False

    # Pull one fragment at a time into the chest.
    active_fragment = fragments[fragment_index % len(fragments)]
    if not active_fragment["collected"] and collection_timer > pause_between_fragments:
        current_action_label.text = "collecting " + active_fragment["name"] + ": " + fragment_specs[active_fragment["name"]]["meaning"]
        direction = chest_glass.pos - active_fragment["pos"]
        distance = mag(direction)
        if distance > 0.08:
            speed = 0.032 + 0.010 * len(stored_particles)
            new_pos = active_fragment["pos"] + norm(direction) * speed
            # Add a slight spiral intake path.
            spiral = vector(math.sin(time * 5.0) * 0.012, math.cos(time * 4.3) * 0.01, math.sin(time * 3.1) * 0.012)
            set_parts_pos(active_fragment, new_pos + spiral)
            if random.random() < 0.06:
                make_collection_trail(active_fragment["pos"], chest_glass.pos, active_fragment["color"])
        else:
            active_fragment["collected"] = True
            store_particle(active_fragment["name"], active_fragment["color"])
            last_collected_name = active_fragment["name"]
            update_memory_panel()
            collection_timer = 0.0
            fragment_index += 1
            current_action_label.text = "stored " + last_collected_name + " inside the chest"

            # If all are collected, respawn weaker echoes outside so the machine can keep searching.
            if all(f["collected"] for f in fragments):
                collection_timer = -2.0
                for f in fragments:
                    f["collected"] = False
                    f["origin"] = spawn_positions[f["name"]] + vector(random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.2), random.uniform(-0.18, 0.18))
                    set_parts_pos(f, f["origin"])
                    for p in f["parts"]:
                        p.visible = True
                    f["label"].visible = True
                current_action_label.text = "all fragments stored; searching for deeper echoes"

    # Stored particles orbit inside chest as the machine's inner life signal.
    aggregate = vector(0, 0, 0)
    for idx, particle in enumerate(stored_particles):
        particle["angle"] += dt * particle["orbit"]
        pulse = 1.0 + 0.24 * math.sin(time * particle["pulse"] + idx)
        r = particle["radius"] * pulse
        particle["obj"].pos = chest_glass.pos + vector(
            math.cos(particle["angle"]) * r,
            particle["height"] + 0.035 * math.sin(time * particle["pulse"] + idx),
            math.sin(particle["angle"]) * r * 0.55,
        )
        particle["obj"].radius = 0.055 + 0.028 * pulse
        aggregate += particle["color"]

    if stored_particles:
        aggregate = aggregate / len(stored_particles)
        core_pulse = 1.0 + 0.2 * math.sin(time * (1.0 + len(stored_particles) * 0.13))
        chest_core.color = aggregate * 0.85 + vector(0.12, 0.12, 0.12)
        chest_core.radius = 0.12 + 0.018 * len(stored_particles) + 0.025 * core_pulse
        chest_ring_1.rotate(angle=dt * (0.7 + 0.05 * len(stored_particles)), axis=vector(0, 0, 1), origin=chest_glass.pos)
        chest_ring_2.rotate(angle=-dt * (0.45 + 0.03 * len(stored_particles)), axis=vector(0, 1, 0), origin=chest_glass.pos)
    else:
        chest_core.radius = 0.10 + 0.01 * math.sin(time * 1.5)

    # Trails fade and disappear.
    for tr in collection_trails[:]:
        tr["life"] -= dt
        tr["curve"].opacity = max(0.0, min(1.0, tr["life"] / 2.0))
        if tr["life"] <= 0:
            tr["curve"].visible = False
            collection_trails.remove(tr)

    # Soft source object pulse.
    for i, obj in enumerate(source_objects):
        obj.opacity = 0.25 + 0.18 * (0.5 + 0.5 * math.sin(time * 1.2 + i))
