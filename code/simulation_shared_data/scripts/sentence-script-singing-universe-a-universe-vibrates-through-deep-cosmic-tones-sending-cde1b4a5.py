"""
Singing Universe — VPython simulation

A universe vibrates through deep cosmic tones, sending waves of music across
the void that cause nearby empty regions to bloom into new space.

Run:
    python singing_universe.py

Requires:
    pip install vpython

Notes:
- Uses ring(...) instead of torus(...).
- Light background / light styling.
- No CSV logging.
"""

from vpython import *
import math
import random

# ------------------------------------------------------------
# Scene setup
# ------------------------------------------------------------
scene = canvas(
    title="Singing Universe — cosmic tones bloom new space",
    width=1200,
    height=760,
    background=vector(0.94, 0.97, 1.0),
    center=vector(0, 0, 0),
)
scene.range = 34
scene.forward = vector(-0.45, -0.28, -0.84)
scene.up = vector(0, 1, 0)

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
random.seed(7)

UNIVERSE_RADIUS = 8.0
MAX_WAVES = 16
MAX_BLOOMS = 70
MAX_STARS = 260
MAX_NOTE_PARTICLES = 120

DEEP_TONES = [
    {"name": "Dawn Bass", "freq": 0.18, "color": vector(0.45, 0.58, 1.00), "speed": 4.2},
    {"name": "Grav Hymn", "freq": 0.27, "color": vector(0.62, 0.50, 1.00), "speed": 4.8},
    {"name": "Void Cello", "freq": 0.36, "color": vector(0.30, 0.75, 0.95), "speed": 5.4},
    {"name": "Creation Chord", "freq": 0.44, "color": vector(0.90, 0.62, 1.00), "speed": 5.9},
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def random_unit_vector():
    z = random.uniform(-1, 1)
    theta = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))


def random_shell_point(radius_min, radius_max):
    return random_unit_vector() * random.uniform(radius_min, radius_max)


def make_label_text(tone_name, wave_count, bloom_count, active_regions):
    return (
        f"Singing Universe\n"
        f"tone: {tone_name}\n"
        f"traveling music waves: {wave_count}\n"
        f"space blooms: {bloom_count}\n"
        f"empty regions listening: {active_regions}\n\n"
        f"Behavior:\n"
        f"• deep tones pulse from the central universe\n"
        f"• musical waves cross the void\n"
        f"• empty regions bloom when struck by strong sound\n"
        f"• mature blooms seed small star-fields"
    )


# ------------------------------------------------------------
# Central singing universe
# ------------------------------------------------------------
core = sphere(
    pos=vector(0, 0, 0),
    radius=UNIVERSE_RADIUS,
    color=vector(0.74, 0.84, 1.0),
    opacity=0.36,
    shininess=0.9,
    emissive=True,
)

inner_core = sphere(
    pos=vector(0, 0, 0),
    radius=2.2,
    color=vector(0.45, 0.58, 1.0),
    opacity=0.82,
    shininess=0.8,
    emissive=True,
)

core_shells = []
for i, rad in enumerate([3.2, 4.8, 6.4, 8.0]):
    shell = ring(
        pos=vector(0, 0, 0),
        axis=vector(0, 1, 0),
        radius=rad,
        thickness=0.035 + i * 0.01,
        color=DEEP_TONES[i % len(DEEP_TONES)]["color"],
        opacity=0.42,
        emissive=True,
    )
    core_shells.append(shell)

equator = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=UNIVERSE_RADIUS * 1.03,
    thickness=0.06,
    color=vector(0.56, 0.68, 1.0),
    opacity=0.5,
    emissive=True,
)

vertical_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(1, 0, 0),
    radius=UNIVERSE_RADIUS * 0.98,
    thickness=0.035,
    color=vector(0.85, 0.67, 1.0),
    opacity=0.34,
    emissive=True,
)

# Soft reference plane
plane = box(
    pos=vector(0, -9.8, 0),
    size=vector(58, 0.05, 58),
    color=vector(0.90, 0.94, 0.98),
    opacity=0.22,
)

# ------------------------------------------------------------
# Empty regions that can bloom into new space
# ------------------------------------------------------------
empty_regions = []
for i in range(30):
    pos = random_shell_point(14, 30)
    marker = sphere(
        pos=pos,
        radius=random.uniform(0.26, 0.48),
        color=vector(0.74, 0.78, 0.86),
        opacity=0.22,
        shininess=0.25,
    )
    halo = ring(
        pos=pos,
        axis=random_unit_vector(),
        radius=marker.radius * 2.2,
        thickness=0.025,
        color=vector(0.70, 0.74, 0.82),
        opacity=0.13,
    )
    empty_regions.append(
        {
            "marker": marker,
            "halo": halo,
            "base_pos": vector(pos.x, pos.y, pos.z),
            "sensitivity": random.uniform(0.72, 1.25),
            "charge": 0.0,
            "bloomed": False,
            "cooldown": random.uniform(0, 4),
        }
    )

# ------------------------------------------------------------
# Dynamic entities
# ------------------------------------------------------------
waves = []
blooms = []
stars = []
note_particles = []

status = label(
    pos=vector(-31, 20, 0),
    text="",
    height=13,
    color=vector(0.14, 0.18, 0.28),
    box=False,
    opacity=0,
    align="left",
)

title_label = label(
    pos=vector(0, 13, 0),
    text="deep tones cause emptiness to unfold into space",
    height=16,
    color=vector(0.18, 0.22, 0.36),
    box=False,
    opacity=0,
)

# ------------------------------------------------------------
# Keyboard controls
# ------------------------------------------------------------
paused = False
sim_speed = 1.0
manual_bloom_requested = False
manual_wave_requested = False
reset_requested = False
tone_bias = 0

control_help = label(
    pos=vector(20, -17, 0),
    text=(
        "Keyboard controls\n"
        "space: pause/resume\n"
        "w: send tone wave\n"
        "b: force nearest empty bloom\n"
        "1-4: select tone family\n"
        "up/down: simulation speed\n"
        "r: reset run"
    ),
    height=11,
    color=vector(0.16, 0.20, 0.30),
    box=False,
    opacity=0,
    align="left",
)


def on_keydown(evt):
    global paused, sim_speed, manual_bloom_requested, manual_wave_requested
    global reset_requested, tone_bias

    key = evt.key

    if key == " ":
        paused = not paused
    elif key in ("w", "W"):
        manual_wave_requested = True
    elif key in ("b", "B"):
        manual_bloom_requested = True
    elif key in ("r", "R"):
        reset_requested = True
    elif key in ("up", "up arrow"):
        sim_speed = clamp(sim_speed + 0.25, 0.25, 3.0)
    elif key in ("down", "down arrow"):
        sim_speed = clamp(sim_speed - 0.25, 0.25, 3.0)
    elif key in ("1", "2", "3", "4"):
        tone_bias = int(key) - 1


scene.bind("keydown", on_keydown)


def current_control_text(tone_name):
    state = "paused" if paused else "running"
    return (
        "Keyboard controls\n"
        "space: pause/resume\n"
        "w: send tone wave\n"
        "b: force nearest empty bloom\n"
        "1-4: select tone family\n"
        "up/down: simulation speed\n"
        "r: reset run\n\n"
        f"state: {state}\n"
        f"speed: {sim_speed:.2f}x\n"
        f"selected tone: {tone_name}"
    )


def force_nearest_empty_bloom(tone_color):
    candidates = [r for r in empty_regions if not r["bloomed"]]
    if not candidates:
        return

    # Prefer a region near the viewer-facing side so the effect is easy to see.
    chosen = min(candidates, key=lambda r: mag(r["marker"].pos - vector(11, 4, 12)))
    chosen["bloomed"] = True
    chosen["marker"].visible = False
    chosen["halo"].visible = False
    spawn_bloom(chosen["marker"].pos, tone_color, 1.65)


def clear_dynamic_objects():
    for wave in waves:
        wave["ring"].visible = False
        wave["companion"].visible = False
    waves.clear()

    for bloom in blooms:
        bloom["sphere"].visible = False
        bloom["ring1"].visible = False
        bloom["ring2"].visible = False
        bloom["stem"].visible = False
    blooms.clear()

    for star in stars:
        star["obj"].visible = False
    stars.clear()

    for particle in note_particles:
        particle["obj"].visible = False
        particle["obj"].clear_trail()
    note_particles.clear()


def reset_empty_regions():
    for region in empty_regions:
        region["bloomed"] = False
        region["charge"] = 0.0
        region["marker"].visible = True
        region["halo"].visible = True
        region["marker"].pos = vector(region["base_pos"].x, region["base_pos"].y, region["base_pos"].z)
        region["marker"].radius = random.uniform(0.26, 0.48)
        region["marker"].color = vector(0.74, 0.78, 0.86)
        region["marker"].opacity = 0.20
        region["halo"].pos = region["marker"].pos
        region["halo"].radius = region["marker"].radius * 2.2
        region["halo"].color = vector(0.70, 0.74, 0.82)
        region["halo"].opacity = 0.13

# ------------------------------------------------------------
# Entity creation
# ------------------------------------------------------------
def spawn_wave(t, tone_index):
    tone = DEEP_TONES[tone_index]
    axis = random_unit_vector()

    wave = ring(
        pos=vector(0, 0, 0),
        axis=axis,
        radius=UNIVERSE_RADIUS * 1.05,
        thickness=0.09,
        color=tone["color"],
        opacity=0.68,
        emissive=True,
    )

    # Secondary perpendicular ring makes the wave read as a musical shell.
    companion = ring(
        pos=vector(0, 0, 0),
        axis=random_unit_vector(),
        radius=UNIVERSE_RADIUS * 0.95,
        thickness=0.035,
        color=lerp_vec(tone["color"], vector(1, 1, 1), 0.22),
        opacity=0.38,
        emissive=True,
    )

    waves.append(
        {
            "ring": wave,
            "companion": companion,
            "age": 0.0,
            "speed": tone["speed"],
            "strength": 1.0,
            "tone": tone,
            "axis": axis,
            "hit_regions": set(),
        }
    )

    # Musical particles ride the front of each pulse.
    for _ in range(8):
        direction = random_unit_vector()
        p = sphere(
            pos=direction * (UNIVERSE_RADIUS + random.uniform(0.4, 1.2)),
            radius=random.uniform(0.08, 0.16),
            color=tone["color"],
            opacity=0.72,
            emissive=True,
            make_trail=True,
            retain=8,
            trail_radius=0.018,
        )
        note_particles.append(
            {
                "obj": p,
                "dir": direction,
                "speed": tone["speed"] * random.uniform(0.95, 1.35),
                "age": 0.0,
                "life": random.uniform(4.2, 6.8),
                "color": tone["color"],
            }
        )

    if len(waves) > MAX_WAVES:
        old = waves.pop(0)
        old["ring"].visible = False
        old["companion"].visible = False


def spawn_bloom(pos, tone_color, strength):
    if len(blooms) >= MAX_BLOOMS:
        old = blooms.pop(0)
        old["sphere"].visible = False
        old["ring1"].visible = False
        old["ring2"].visible = False
        old["stem"].visible = False

    bloom_color = lerp_vec(tone_color, vector(1.0, 0.88, 0.58), 0.28)
    bloom_sphere = sphere(
        pos=pos,
        radius=0.35,
        color=bloom_color,
        opacity=0.26,
        shininess=0.8,
        emissive=True,
    )
    ring1 = ring(
        pos=pos,
        axis=random_unit_vector(),
        radius=0.55,
        thickness=0.035,
        color=bloom_color,
        opacity=0.58,
        emissive=True,
    )
    ring2 = ring(
        pos=pos,
        axis=random_unit_vector(),
        radius=0.82,
        thickness=0.025,
        color=lerp_vec(bloom_color, vector(0.65, 0.85, 1.0), 0.35),
        opacity=0.38,
        emissive=True,
    )
    stem = cylinder(
        pos=pos * 0.96,
        axis=pos * 0.04,
        radius=0.035,
        color=bloom_color,
        opacity=0.28,
        emissive=True,
    )

    blooms.append(
        {
            "sphere": bloom_sphere,
            "ring1": ring1,
            "ring2": ring2,
            "stem": stem,
            "age": 0.0,
            "growth": 0.0,
            "target": random.uniform(2.1, 4.8) * strength,
            "spin": random.uniform(0.008, 0.025),
            "seeded": False,
            "color": bloom_color,
        }
    )


def spawn_star_cluster(center, bloom_color):
    global stars
    new_stars = random.randint(5, 9)
    for _ in range(new_stars):
        if len(stars) >= MAX_STARS:
            old = stars.pop(0)
            old["obj"].visible = False

        offset = random_unit_vector() * random.uniform(0.25, 2.4)
        star = sphere(
            pos=center + offset,
            radius=random.uniform(0.045, 0.12),
            color=lerp_vec(bloom_color, vector(1, 1, 1), random.uniform(0.2, 0.55)),
            opacity=random.uniform(0.58, 0.95),
            emissive=True,
        )
        stars.append(
            {
                "obj": star,
                "base": vector(star.pos.x, star.pos.y, star.pos.z),
                "twinkle": random.uniform(0, 2 * math.pi),
                "amp": random.uniform(0.02, 0.09),
            }
        )


# ------------------------------------------------------------
# Main animation loop
# ------------------------------------------------------------
t = 0.0
dt = 1 / 60
tone_index = 0
last_wave_time = -10.0

while True:
    rate(60)

    active_tone = DEEP_TONES[(tone_index + tone_bias) % len(DEEP_TONES)]
    control_help.text = current_control_text(active_tone["name"])

    if reset_requested:
        clear_dynamic_objects()
        reset_empty_regions()
        t = 0.0
        tone_index = tone_bias
        last_wave_time = -10.0
        reset_requested = False
        paused = False

    if paused:
        continue

    step = dt * sim_speed
    t += step

    # Deep cosmic chord drives the visible breathing of the central universe.
    active_tone = DEEP_TONES[(tone_index + tone_bias) % len(DEEP_TONES)]
    chord = (
        0.55 * math.sin(2 * math.pi * DEEP_TONES[0]["freq"] * t)
        + 0.32 * math.sin(2 * math.pi * DEEP_TONES[1]["freq"] * t + 1.2)
        + 0.22 * math.sin(2 * math.pi * DEEP_TONES[2]["freq"] * t + 2.1)
    )
    pulse = 1.0 + 0.045 * chord

    core.radius = UNIVERSE_RADIUS * pulse
    inner_core.radius = 2.15 + 0.32 * abs(chord)
    inner_core.color = lerp_vec(vector(0.45, 0.58, 1.0), active_tone["color"], 0.45 + 0.25 * abs(math.sin(t)))

    equator.rotate(angle=0.006 + 0.002 * abs(chord), axis=vector(0, 1, 0), origin=vector(0, 0, 0))
    vertical_ring.rotate(angle=-0.0045, axis=vector(1, 0.2, 0), origin=vector(0, 0, 0))

    for i, shell in enumerate(core_shells):
        shell.radius = (3.2 + i * 1.6) * (1 + 0.04 * math.sin(t * (0.8 + i * 0.13) + i))
        shell.rotate(angle=0.004 * (i + 1), axis=random_unit_vector() * 0.02 + vector(0, 1, 0), origin=vector(0, 0, 0))
        shell.opacity = 0.30 + 0.22 * abs(math.sin(t * DEEP_TONES[i]["freq"] * 2.4 + i))

    # Spawn new tone wave at chord intervals.
    if manual_wave_requested or t - last_wave_time > 2.15:
        spawn_wave(t, (tone_index + tone_bias) % len(DEEP_TONES))
        last_wave_time = t
        tone_index += 1
        manual_wave_requested = False

    if manual_bloom_requested:
        force_nearest_empty_bloom(active_tone["color"])
        manual_bloom_requested = False

    # Update music waves.
    for wave in list(waves):
        wave["age"] += step
        radius = UNIVERSE_RADIUS + wave["age"] * wave["speed"]
        fade = clamp(1.0 - wave["age"] / 7.2, 0, 1)
        strength = fade * (0.75 + 0.25 * math.sin(t * 2.0 + wave["age"]))

        wave["ring"].radius = radius
        wave["ring"].thickness = 0.035 + 0.11 * strength
        wave["ring"].opacity = 0.62 * fade
        wave["ring"].rotate(angle=0.008, axis=wave["axis"], origin=vector(0, 0, 0))

        wave["companion"].radius = radius * 0.78
        wave["companion"].opacity = 0.34 * fade
        wave["companion"].rotate(angle=-0.006, axis=wave["axis"], origin=vector(0, 0, 0))

        # Regions bloom when the musical shell reaches them.
        for idx, region in enumerate(empty_regions):
            if region["bloomed"]:
                continue

            dist = mag(region["marker"].pos)
            near_front = abs(dist - radius) < 0.38 + 0.22 * strength
            if near_front and idx not in wave["hit_regions"]:
                wave["hit_regions"].add(idx)
                region["charge"] += strength * region["sensitivity"]

                region["marker"].radius *= 1.18
                region["marker"].color = lerp_vec(region["marker"].color, wave["tone"]["color"], 0.45)
                region["marker"].opacity = clamp(region["marker"].opacity + 0.23, 0.08, 0.9)
                region["halo"].color = wave["tone"]["color"]
                region["halo"].opacity = clamp(region["halo"].opacity + 0.20, 0.05, 0.85)
                region["halo"].radius *= 1.12

                if region["charge"] > 1.28:
                    region["bloomed"] = True
                    spawn_bloom(region["marker"].pos, wave["tone"]["color"], region["charge"])
                    region["marker"].visible = False
                    region["halo"].visible = False

        if wave["age"] > 7.6:
            wave["ring"].visible = False
            wave["companion"].visible = False
            waves.remove(wave)

    # Update empty listening regions.
    for region in empty_regions:
        if region["bloomed"]:
            continue
        wobble = 0.08 * math.sin(t * 1.2 + region["cooldown"])
        outward = norm(region["base_pos"]) if mag(region["base_pos"]) > 0 else vector(0, 1, 0)
        region["marker"].pos = region["base_pos"] + outward * wobble
        region["halo"].pos = region["marker"].pos
        region["halo"].rotate(angle=0.006, axis=outward, origin=region["marker"].pos)
        region["charge"] *= 0.997

    # Update musical particles.
    for particle in list(note_particles):
        particle["age"] += step
        obj = particle["obj"]
        obj.pos += particle["dir"] * particle["speed"] * step
        obj.pos += vector(
            0.04 * math.sin(t * 3 + obj.pos.z),
            0.03 * math.cos(t * 2.3 + obj.pos.x),
            0.04 * math.sin(t * 2.7 + obj.pos.y),
        )
        life_fade = clamp(1 - particle["age"] / particle["life"], 0, 1)
        obj.opacity = 0.78 * life_fade
        obj.radius = 0.06 + 0.09 * life_fade

        if particle["age"] > particle["life"] or len(note_particles) > MAX_NOTE_PARTICLES:
            obj.visible = False
            obj.clear_trail()
            note_particles.remove(particle)

    # Update blooms.
    for bloom in blooms:
        bloom["age"] += step
        bloom["growth"] = min(bloom["target"], bloom["growth"] + step * (0.88 + 0.08 * bloom["target"]))
        breathing = 1 + 0.08 * math.sin(t * 1.8 + bloom["target"])

        bloom["sphere"].radius = 0.42 + bloom["growth"] * 0.45 * breathing
        bloom["sphere"].opacity = 0.20 + 0.18 * abs(math.sin(t * 1.1 + bloom["target"]))

        bloom["ring1"].radius = 0.7 + bloom["growth"] * 0.72
        bloom["ring2"].radius = 1.1 + bloom["growth"] * 1.05
        bloom["ring1"].rotate(angle=bloom["spin"], axis=bloom["ring1"].axis, origin=bloom["sphere"].pos)
        bloom["ring2"].rotate(angle=-bloom["spin"] * 0.8, axis=bloom["ring2"].axis, origin=bloom["sphere"].pos)
        bloom["ring1"].opacity = clamp(0.65 - bloom["age"] * 0.015, 0.22, 0.65)
        bloom["ring2"].opacity = clamp(0.48 - bloom["age"] * 0.012, 0.18, 0.48)

        bloom["stem"].axis = bloom["sphere"].pos * 0.04 * (1 + 0.2 * math.sin(t + bloom["target"]))
        bloom["stem"].radius = 0.025 + bloom["growth"] * 0.012

        if not bloom["seeded"] and bloom["growth"] > bloom["target"] * 0.56:
            bloom["seeded"] = True
            spawn_star_cluster(bloom["sphere"].pos, bloom["color"])

    # Update stars inside bloomed regions.
    for s in stars:
        s["twinkle"] += step * 2.5
        s["obj"].radius = 0.055 + s["amp"] * (0.5 + 0.5 * math.sin(s["twinkle"]))
        s["obj"].opacity = 0.55 + 0.38 * abs(math.sin(s["twinkle"]))

    # If every initial empty region has bloomed, seed a few new distant empty regions.
    unbloomed = [r for r in empty_regions if not r["bloomed"]]
    if len(unbloomed) < 6 and len(empty_regions) < 50:
        for _ in range(4):
            pos = random_shell_point(22, 33)
            marker = sphere(
                pos=pos,
                radius=random.uniform(0.24, 0.42),
                color=vector(0.74, 0.78, 0.86),
                opacity=0.18,
                shininess=0.25,
            )
            halo = ring(
                pos=pos,
                axis=random_unit_vector(),
                radius=marker.radius * 2.1,
                thickness=0.022,
                color=vector(0.70, 0.74, 0.82),
                opacity=0.11,
            )
            empty_regions.append(
                {
                    "marker": marker,
                    "halo": halo,
                    "base_pos": vector(pos.x, pos.y, pos.z),
                    "sensitivity": random.uniform(0.8, 1.35),
                    "charge": 0.0,
                    "bloomed": False,
                    "cooldown": random.uniform(0, 4),
                }
            )

    status.text = make_label_text(
        active_tone["name"],
        len(waves),
        len(blooms),
        len([r for r in empty_regions if not r["bloomed"]]),
    )
