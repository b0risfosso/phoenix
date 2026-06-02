"""
Black Hole Before Galaxy

Story:
    New data from NASA Webb suggests that some supermassive black holes in the
    early universe may have grown rapidly without needing a much larger host
    galaxy to feed them.

Simulation seed:
    A massive black hole appears first in the young universe, pulling gas inward
    while only a small, dim host galaxy begins forming around it.

Controls:
    Mouse       : drag / scroll to control camera
    Space       : pause / resume
    R           : reset formation
    G           : toggle gas inflow streams
    D           : toggle accretion disk
    S           : toggle seed-star/host galaxy particles
    C           : toggle camera follow
    Up / W      : speed up
    Down / S    : slow down

Run:
    python black_hole_before_galaxy.py

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
    title="Black Hole Before Galaxy",
    width=1200,
    height=780,
    background=vector(0.015, 0.012, 0.028),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.44, -0.28, -0.85)
scene.up = vector(0, 1, 0)
scene.range = 10.5

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
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def spiral_position(radius, angle, height_scale=0.18):
    return vector(
        radius * math.cos(angle),
        height_scale * math.sin(angle * 0.7),
        radius * math.sin(angle),
    )


# -----------------------------
# Colors
# -----------------------------
VOID = vector(0.015, 0.012, 0.028)
BH_BLACK = vector(0.0, 0.0, 0.0)
LENS_BLUE = vector(0.30, 0.55, 1.0)
DISK_INNER = vector(1.0, 0.82, 0.32)
DISK_OUTER = vector(1.0, 0.33, 0.10)
GAS_COLD = vector(0.20, 0.42, 0.90)
GAS_HOT = vector(1.0, 0.52, 0.18)
STAR_DIM = vector(0.62, 0.66, 0.78)
STAR_NEW = vector(0.98, 0.88, 0.56)
GALAXY_DUST = vector(0.36, 0.28, 0.42)
WEBB_GOLD = vector(1.0, 0.72, 0.26)

# -----------------------------
# Early universe background
# -----------------------------
background_stars = []
for i in range(180):
    pos = vector(
        random.uniform(-18, 18),
        random.uniform(-12, 12),
        random.uniform(-16, 12),
    )
    if mag(pos) < 3.0:
        continue
    star = sphere(
        pos=pos,
        radius=random.uniform(0.012, 0.045),
        color=mix_color(vector(0.50, 0.55, 0.72), vector(1.0, 0.90, 0.62), random.random()),
        emissive=True,
        opacity=random.uniform(0.25, 0.85),
    )
    background_stars.append({"obj": star, "phase": random.random() * math.tau})

cosmic_haze = []
for i in range(42):
    cloud = ellipsoid(
        pos=vector(random.uniform(-12, 12), random.uniform(-6, 6), random.uniform(-9, 7)),
        length=random.uniform(0.6, 2.5),
        height=random.uniform(0.08, 0.32),
        width=random.uniform(0.25, 0.9),
        color=mix_color(vector(0.16, 0.12, 0.30), vector(0.36, 0.18, 0.38), random.random()),
        opacity=random.uniform(0.05, 0.16),
    )
    cosmic_haze.append({"obj": cloud, "phase": random.random() * math.tau, "drift": random.uniform(0.002, 0.010)})

# -----------------------------
# Central black hole first
# -----------------------------
event_horizon = sphere(
    pos=vector(0, 0, 0),
    radius=0.62,
    color=BH_BLACK,
    opacity=1.0,
    shininess=0.0,
)

photon_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=0.78,
    thickness=0.035,
    color=WEBB_GOLD,
    emissive=True,
    opacity=0.82,
)

lensing_halo_1 = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 1, 0),
    radius=1.05,
    thickness=0.018,
    color=LENS_BLUE,
    emissive=True,
    opacity=0.26,
)
lensing_halo_2 = ring(
    pos=vector(0, 0, 0),
    axis=vector(0.3, 1, 0.1),
    radius=1.28,
    thickness=0.012,
    color=vector(0.55, 0.72, 1.0),
    emissive=True,
    opacity=0.18,
)

# -----------------------------
# Accretion disk particles
# -----------------------------
disk_particles = []
for i in range(140):
    r = random.uniform(0.95, 3.2)
    angle = random.uniform(0, math.tau)
    pos = spiral_position(r, angle, 0.08)
    particle = sphere(
        pos=pos,
        radius=random.uniform(0.025, 0.075),
        color=mix_color(DISK_INNER, DISK_OUTER, clamp((r - 0.95) / 2.25)),
        emissive=True,
        opacity=random.uniform(0.55, 0.92),
    )
    disk_particles.append({
        "obj": particle,
        "r": r,
        "angle": angle,
        "phase": random.random() * math.tau,
        "speed": random.uniform(0.42, 1.05) / (r ** 0.7),
        "base_radius": particle.radius,
    })

disk_plane = cylinder(
    pos=vector(0, -0.015, 0),
    axis=vector(0, 0.03, 0),
    radius=3.35,
    color=DISK_OUTER,
    opacity=0.075,
)

# -----------------------------
# Gas inflow streams: long filaments feeding the black hole
# -----------------------------
gas_streams = []
stream_origins = [
    vector(-8.5, 2.1, -4.4),
    vector(7.8, -1.5, 3.9),
    vector(-6.6, -3.0, 4.8),
    vector(6.8, 2.8, -4.2),
    vector(1.2, 5.3, 5.7),
    vector(-2.0, -5.4, -5.0),
]
for si, origin in enumerate(stream_origins):
    beads = []
    for j in range(30):
        f = j / 29.0
        bend = vector(
            math.sin(f * math.pi * 1.4 + si) * 0.55,
            math.sin(f * math.pi * 1.8 + si * 0.7) * 0.35,
            math.cos(f * math.pi * 1.1 + si) * 0.55,
        )
        pos = origin * (1.0 - f) + vector(0, 0, 0) * f + bend
        bead = sphere(
            pos=pos,
            radius=0.035 + 0.035 * (1.0 - f),
            color=mix_color(GAS_COLD, GAS_HOT, f),
            emissive=True,
            opacity=0.18 + 0.56 * f,
        )
        beads.append(bead)
    gas_streams.append({"origin": origin, "beads": beads, "phase": random.random() * math.tau, "index": si})

# -----------------------------
# Small, dim host galaxy assembling later
# -----------------------------
host_particles = []
for i in range(120):
    # Initially small and dim: host grows after the black hole already exists.
    arm = random.choice([-1, 1])
    birth_r = random.uniform(1.4, 5.8)
    angle = random.uniform(0, math.tau)
    height = random.gauss(0, 0.18)
    obj = sphere(
        pos=vector(0, 0, 0),
        radius=random.uniform(0.018, 0.055),
        color=STAR_DIM,
        emissive=True,
        opacity=0.0,
    )
    host_particles.append({
        "obj": obj,
        "r": birth_r,
        "angle": angle,
        "height": height,
        "arm": arm,
        "phase": random.random() * math.tau,
        "birth": random.uniform(0.16, 0.88),
        "spin": random.uniform(0.10, 0.22),
    })

dust_particles = []
for i in range(90):
    r = random.uniform(1.8, 6.8)
    angle = random.uniform(0, math.tau)
    obj = sphere(
        pos=vector(0, -10, 0),
        radius=random.uniform(0.025, 0.085),
        color=GALAXY_DUST,
        opacity=0.0,
    )
    dust_particles.append({
        "obj": obj,
        "r": r,
        "angle": angle,
        "phase": random.random() * math.tau,
        "birth": random.uniform(0.22, 0.92),
    })

# Growth metric columns beside scene.
metric_frame = box(
    pos=vector(-7.9, -3.1, 4.7),
    size=vector(1.35, 0.08, 0.08),
    color=vector(0.18, 0.20, 0.28),
    opacity=0.55,
)
bh_bar = box(
    pos=vector(-8.35, -2.45, 4.7),
    size=vector(0.18, 0.1, 0.18),
    color=WEBB_GOLD,
    emissive=True,
)
gal_bar = box(
    pos=vector(-7.55, -2.45, 4.7),
    size=vector(0.18, 0.1, 0.18),
    color=STAR_DIM,
    emissive=True,
)

bh_label = label(
    pos=vector(-8.35, -1.05, 4.7),
    text="black hole\nmass",
    height=10,
    box=False,
    color=vector(0.95, 0.82, 0.42),
)
gal_label = label(
    pos=vector(-7.55, -1.05, 4.7),
    text="host galaxy\nlight",
    height=10,
    box=False,
    color=vector(0.72, 0.74, 0.90),
)

# -----------------------------
# Observation markers
# -----------------------------
webb_beam = cylinder(
    pos=vector(7.6, 4.8, -6.0),
    axis=vector(-7.6, -4.8, 6.0),
    radius=0.025,
    color=WEBB_GOLD,
    opacity=0.16,
    emissive=True,
)
webb_node = sphere(
    pos=vector(7.6, 4.8, -6.0),
    radius=0.18,
    color=WEBB_GOLD,
    opacity=0.9,
    emissive=True,
)
observation_label = label(
    pos=vector(7.0, 5.25, -6.0),
    text="deep infrared observation",
    height=11,
    box=False,
    color=vector(1.0, 0.82, 0.34),
)

# -----------------------------
# Labels
# -----------------------------
title = label(
    pos=vector(0, 5.6, -5.5),
    text="Black Hole Before Galaxy",
    height=24,
    box=False,
    color=vector(0.95, 0.86, 0.62),
)
subtitle = label(
    pos=vector(0, 5.15, -5.5),
    text="A massive black hole dominates first while a small dim host galaxy assembles around it.",
    height=12,
    box=False,
    color=vector(0.72, 0.80, 1.0),
)
status = label(
    pos=vector(-7.7, 4.6, -5.3),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.88, 0.93, 1.0),
    background=vector(0.025, 0.025, 0.055),
    opacity=0.78,
)
legend = label(
    pos=vector(7.3, 4.5, -5.3),
    text="Gold ring: early massive black hole\nOrange disk: hot accretion flow\nBlue/orange streams: gas pulled inward\nDim points: small host galaxy forming late",
    height=12,
    box=True,
    border=8,
    color=vector(0.88, 0.93, 1.0),
    background=vector(0.025, 0.025, 0.055),
    opacity=0.78,
)

# -----------------------------
# State and controls
# -----------------------------
paused = False
show_gas = True
show_disk = True
show_stars = True
camera_follow = False
speed = 1.0
sim_t = 0.0


def reset_sim():
    global sim_t, speed
    sim_t = 0.0
    speed = 1.0
    for hp in host_particles:
        hp["obj"].opacity = 0.0
    for dp in dust_particles:
        dp["obj"].opacity = 0.0


def on_keydown(evt):
    global paused, show_gas, show_disk, show_stars, camera_follow, speed

    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_sim()
    elif key == "g":
        show_gas = not show_gas
        for stream in gas_streams:
            for bead in stream["beads"]:
                bead.visible = show_gas
    elif key == "d":
        show_disk = not show_disk
        disk_plane.visible = show_disk
        for dp in disk_particles:
            dp["obj"].visible = show_disk
    elif key == "s":
        show_stars = not show_stars
        for hp in host_particles:
            hp["obj"].visible = show_stars
        for dp in dust_particles:
            dp["obj"].visible = show_stars
    elif key == "c":
        camera_follow = not camera_follow
    elif key in ("up", "w"):
        speed = min(4.0, speed + 0.25)
    elif key in ("down",):
        speed = max(0.15, speed - 0.25)


scene.bind("keydown", on_keydown)

# -----------------------------
# Main animation loop
# -----------------------------
while True:
    rate(50)

    if paused:
        status.text = (
            "Paused\n"
            f"Speed: {speed:.2f}x\n"
            "Space resumes | R resets"
        )
        continue

    dt = 0.018 * speed
    sim_t += dt

    progress = (sim_t * 0.020) % 1.0

    # Black hole mass grows early and fast; host galaxy light grows later and slower.
    bh_growth = clamp(0.30 + 0.70 * (1.0 - math.exp(-progress * 7.0)))
    host_growth = clamp((progress - 0.18) / 0.82) ** 1.55
    accretion_power = clamp(0.25 + 0.75 * math.sin(progress * math.pi) ** 0.35)

    # Event horizon and lensing strengthen first.
    event_horizon.radius = 0.52 + 0.25 * bh_growth
    photon_ring.radius = 0.72 + 0.24 * bh_growth + 0.035 * math.sin(sim_t * 3.0)
    photon_ring.thickness = 0.025 + 0.035 * accretion_power
    photon_ring.opacity = 0.55 + 0.38 * accretion_power

    lensing_halo_1.radius = 1.00 + 0.35 * bh_growth + 0.04 * math.sin(sim_t * 1.4)
    lensing_halo_1.opacity = 0.12 + 0.22 * bh_growth
    lensing_halo_1.rotate(angle=dt * 0.55, axis=vector(0.2, 1, 0.1), origin=vector(0, 0, 0))

    lensing_halo_2.radius = 1.28 + 0.30 * bh_growth + 0.05 * math.sin(sim_t * 1.0 + 1.3)
    lensing_halo_2.opacity = 0.08 + 0.16 * bh_growth
    lensing_halo_2.rotate(angle=-dt * 0.42, axis=vector(0.3, 1, 0.1), origin=vector(0, 0, 0))

    # Accretion disk particles spiral inward, heat up, then recycle outward.
    for p in disk_particles:
        obj = p["obj"]
        p["angle"] += dt * p["speed"] * (1.0 + 1.5 * accretion_power)
        inward = 0.12 * math.sin(sim_t * 0.7 + p["phase"]) + 0.30 * progress
        r = p["r"] - inward
        if r < 0.84:
            r = random.uniform(2.3, 3.4)
            p["r"] = r
            p["angle"] = random.uniform(0, math.tau)
        heat = clamp((3.4 - r) / 2.5)
        obj.pos = spiral_position(r, p["angle"], 0.10 + 0.04 * math.sin(sim_t + p["phase"]))
        obj.radius = p["base_radius"] * (0.75 + 0.65 * heat * accretion_power)
        obj.color = mix_color(DISK_OUTER, DISK_INNER, heat)
        obj.opacity = (0.35 + 0.60 * accretion_power * heat) if show_disk else 0.0

    disk_plane.radius = 2.5 + 0.95 * accretion_power
    disk_plane.opacity = 0.035 + 0.095 * accretion_power if show_disk else 0.0
    disk_plane.rotate(angle=dt * 0.22, axis=vector(0, 1, 0), origin=vector(0, 0, 0))

    # Gas streams flow inward from the young universe.
    gas_rate = 0.35 + 0.65 * bh_growth
    for stream in gas_streams:
        origin = stream["origin"]
        phase = stream["phase"]
        for j, bead in enumerate(stream["beads"]):
            f0 = j / max(1, len(stream["beads"]) - 1)
            f = (f0 + sim_t * 0.060 * gas_rate + 0.08 * math.sin(sim_t * 0.35 + phase)) % 1.0

            # Flow goes from origin into center; near center it curves into disk.
            bend = vector(
                math.sin(f * math.pi * 2.2 + phase) * (0.75 * (1.0 - f)),
                math.sin(f * math.pi * 1.7 + phase) * (0.45 * (1.0 - f)),
                math.cos(f * math.pi * 2.0 + phase) * (0.75 * (1.0 - f)),
            )
            disk_swirl = vector(math.cos(f * 7 + phase), 0, math.sin(f * 7 + phase)) * (0.75 * f * (1.0 - f))
            pos = origin * (1.0 - f) + bend + disk_swirl
            bead.pos = pos
            heat = clamp(f)
            bead.color = mix_color(GAS_COLD, GAS_HOT, heat)
            bead.radius = 0.025 + 0.070 * heat * bh_growth
            bead.opacity = (0.12 + 0.70 * heat * gas_rate) if show_gas else 0.0

    # Host galaxy forms later: dim stars condense into a small spiral around the black hole.
    visible_stars = 0
    for hp in host_particles:
        obj = hp["obj"]
        birth_strength = clamp((host_growth - hp["birth"] * 0.65) / 0.35)
        angle = hp["angle"] + sim_t * hp["spin"]
        # Small host: spiral radius grows slowly and stays modest relative to black hole dominance.
        arm_twist = hp["arm"] * 0.65 * math.log(1 + hp["r"])
        r = hp["r"] * (0.22 + 0.78 * host_growth)
        pos = vector(
            r * math.cos(angle + arm_twist),
            hp["height"] * (0.35 + host_growth),
            r * math.sin(angle + arm_twist),
        )
        obj.pos = pos
        flicker = 0.5 + 0.5 * math.sin(sim_t * 2.1 + hp["phase"])
        obj.opacity = (0.05 + 0.64 * birth_strength * (0.65 + 0.35 * flicker)) if show_stars else 0.0
        obj.radius = 0.012 + 0.050 * birth_strength
        obj.color = mix_color(STAR_DIM, STAR_NEW, 0.35 * birth_strength * flicker)
        if birth_strength > 0.35:
            visible_stars += 1

    # Dust and gas glow fill in only after host starts to assemble.
    for dp in dust_particles:
        obj = dp["obj"]
        birth_strength = clamp((host_growth - dp["birth"] * 0.7) / 0.34)
        angle = dp["angle"] + sim_t * 0.07
        r = dp["r"] * (0.20 + 0.80 * host_growth)
        obj.pos = vector(
            r * math.cos(angle + 0.35 * math.sin(r)),
            0.22 * math.sin(angle * 0.7 + dp["phase"]),
            r * math.sin(angle + 0.35 * math.sin(r)),
        )
        obj.opacity = (0.02 + 0.18 * birth_strength) if show_stars else 0.0
        obj.color = mix_color(GALAXY_DUST, GAS_COLD, 0.20 * birth_strength)

    # Metric bars show black hole mass outpacing host galaxy light.
    bh_bar.size.y = 0.25 + 2.35 * bh_growth
    bh_bar.pos.y = -3.70 + bh_bar.size.y / 2
    gal_bar.size.y = 0.12 + 1.10 * host_growth
    gal_bar.pos.y = -3.70 + gal_bar.size.y / 2

    # Observation beam and node pulse.
    obs_pulse = 0.5 + 0.5 * math.sin(sim_t * 1.8)
    webb_beam.opacity = 0.08 + 0.14 * obs_pulse
    webb_node.radius = 0.16 + 0.05 * obs_pulse

    # Background twinkle and haze drift.
    for item in background_stars:
        item["obj"].opacity = 0.25 + 0.65 * math.sin(sim_t * 0.55 + item["phase"]) ** 2

    for item in cosmic_haze:
        cloud = item["obj"]
        cloud.pos.x += item["drift"] * math.sin(sim_t * 0.25 + item["phase"])
        cloud.opacity = 0.04 + 0.12 * math.sin(sim_t * 0.32 + item["phase"]) ** 2

    # Camera follow is optional; otherwise mouse controls remain active.
    if camera_follow:
        scene.center = vector(0, 0, 0)
        scene.forward = safe_norm(vector(0, 0, 0) - vector(5.8, 3.0, 8.2))
        scene.range = 8.0

    status.text = (
        f"Formation progress: {int(progress * 100)}%\n"
        f"Black hole growth: {int(bh_growth * 100)}%\n"
        f"Host galaxy light: {int(host_growth * 100)}%\n"
        f"Visible young stars: {visible_stars}\n"
        f"Accretion power: {int(accretion_power * 100)}%\n"
        f"Gas inflow: {'on' if show_gas else 'off'} | Disk: {'on' if show_disk else 'off'}\n"
        f"Host particles: {'on' if show_stars else 'off'} | Camera: {'follow' if camera_follow else 'mouse'}\n"
        f"Speed: {speed:.2f}x\n"
        "Mouse camera | Space pause | R reset | G gas | D disk | S stars | C follow"
    )
