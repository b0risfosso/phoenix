from vpython import *
import math
import random

# Little Red Dot Engine
# A stylized VPython simulation inspired by JWST observations of compact red early-universe objects
# where a supermassive black hole can outweigh its small surrounding host galaxy.

scene = canvas(
    title="Little Red Dot Engine - Hidden Monster Black Hole",
    width=1200,
    height=760,
    background=vector(0.92, 0.95, 1.0),
    center=vector(0, 0, 0),
    range=20,
)
scene.caption = "A tiny red dusty host reveals an oversized central black hole. Dust dims and reddens the object while the hidden engine pulses through the galaxy.\n"

# ---------- Utility ----------

def clamp(x, a, b):
    return max(a, min(b, x))


def lerp_vec(a, b, f):
    return a * (1 - f) + b * f


def rand_unit():
    theta = random.uniform(0, 2 * math.pi)
    z = random.uniform(-1, 1)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))


def make_ring_segment(pos, radius, color_value, thickness=0.035, opacity=0.45, axis=vector(0, 1, 0)):
    return ring(pos=pos, radius=radius, thickness=thickness, axis=axis, color=color_value, opacity=opacity)

# ---------- Scene objects ----------

# Deep-space reference stars on a pale background
stars = []
for _ in range(150):
    d = random.uniform(25, 42)
    p = rand_unit() * d
    s = sphere(
        pos=p,
        radius=random.uniform(0.025, 0.07),
        color=vector(1, 1, 1),
        emissive=True,
        opacity=random.uniform(0.35, 0.85),
    )
    stars.append(s)

# Tiny red host galaxy / little red dot
host_core = sphere(
    pos=vector(0, 0, 0),
    radius=1.55,
    color=vector(0.85, 0.18, 0.10),
    opacity=0.23,
    emissive=True,
)
host_glow = sphere(
    pos=vector(0, 0, 0),
    radius=2.6,
    color=vector(1.0, 0.35, 0.18),
    opacity=0.08,
    emissive=True,
)
outer_dust_haze = sphere(
    pos=vector(0, 0, 0),
    radius=4.6,
    color=vector(0.80, 0.34, 0.16),
    opacity=0.06,
    emissive=True,
)

# Hidden monster black hole: deliberately larger influence than host scale
black_hole = sphere(
    pos=vector(0, 0, 0),
    radius=0.72,
    color=vector(0.002, 0.002, 0.004),
    opacity=1.0,
)
event_horizon_rim = ring(
    pos=black_hole.pos,
    radius=0.92,
    thickness=0.045,
    axis=vector(0.18, 1, 0.08),
    color=vector(1.0, 0.45, 0.10),
    emissive=True,
    opacity=0.95,
)
photon_rim = ring(
    pos=black_hole.pos,
    radius=1.16,
    thickness=0.025,
    axis=vector(0.18, 1, 0.08),
    color=vector(1.0, 0.90, 0.35),
    emissive=True,
    opacity=0.7,
)

# Accretion disk layers using rings, not torus
accretion_rings = []
for i in range(8):
    r = 1.25 + i * 0.25
    ring_obj = ring(
        pos=vector(0, 0, 0),
        radius=r,
        thickness=0.025 + 0.005 * (8 - i),
        axis=vector(0.12, 1, 0.18),
        color=vector(1.0, 0.62 - 0.035 * i, 0.18),
        opacity=0.52 - 0.035 * i,
        emissive=True,
    )
    accretion_rings.append(ring_obj)

# Obscuring dust shells and streaks
obscuring_dust = []
for i in range(44):
    angle = random.uniform(0, 2 * math.pi)
    rr = random.uniform(2.0, 4.3)
    y = random.uniform(-1.1, 1.1)
    p = vector(rr * math.cos(angle), y, rr * math.sin(angle))
    dust = sphere(
        pos=p,
        radius=random.uniform(0.06, 0.18),
        color=vector(0.55 + random.random() * 0.25, 0.18 + random.random() * 0.10, 0.08),
        opacity=random.uniform(0.22, 0.50),
        emissive=True,
    )
    dust._angle = angle
    dust._rr = rr
    dust._speed = random.uniform(0.12, 0.30) * random.choice([-1, 1])
    dust._height = y
    dust._phase = random.uniform(0, 2 * math.pi)
    obscuring_dust.append(dust)

# Small host star particles, intentionally sparse compared with central engine
host_stars = []
for i in range(90):
    angle = random.uniform(0, 2 * math.pi)
    rr = random.uniform(0.7, 3.8)
    y = random.uniform(-0.45, 0.45)
    p = vector(rr * math.cos(angle), y, rr * math.sin(angle))
    star = sphere(
        pos=p,
        radius=random.uniform(0.025, 0.065),
        color=vector(1.0, random.uniform(0.55, 0.85), random.uniform(0.35, 0.60)),
        emissive=True,
        opacity=random.uniform(0.35, 0.80),
    )
    star._angle = angle
    star._rr = rr
    star._speed = random.uniform(0.08, 0.22)
    star._height = y
    host_stars.append(star)

# Energy leaks through dust as red/gold beams
beams = []
for i in range(14):
    theta = 2 * math.pi * i / 14
    length = random.uniform(3.8, 7.0)
    axis_vec = vector(math.cos(theta), random.uniform(-0.12, 0.12), math.sin(theta))
    cyl = cylinder(
        pos=vector(0, 0, 0),
        axis=axis_vec * length,
        radius=random.uniform(0.018, 0.045),
        color=vector(1.0, 0.28 + random.random() * 0.25, 0.08),
        opacity=0.12,
        emissive=True,
    )
    cyl._theta = theta
    cyl._length = length
    cyl._speed = random.uniform(0.05, 0.16)
    beams.append(cyl)

# Infalling gas packets show the black hole being fed by compact surroundings
infall_packets = []
for i in range(36):
    angle = random.uniform(0, 2 * math.pi)
    rr = random.uniform(3.0, 8.5)
    y = random.uniform(-1.4, 1.4)
    pkt = sphere(
        pos=vector(rr * math.cos(angle), y, rr * math.sin(angle)),
        radius=random.uniform(0.055, 0.11),
        color=vector(1.0, 0.36, 0.12),
        opacity=0.72,
        emissive=True,
    )
    pkt._angle = angle
    pkt._rr = rr
    pkt._height = y
    pkt._spiral = random.uniform(0.08, 0.18)
    pkt._speed = random.uniform(0.08, 0.22)
    infall_packets.append(pkt)

# Mass comparison columns: host galaxy vs black hole
base_y = -7.3
mass_panel = box(pos=vector(-11.7, base_y + 1.8, 0), size=vector(4.8, 4.2, 0.12), color=vector(0.96, 0.98, 1.0), opacity=0.55)
host_bar = box(pos=vector(-12.7, base_y + 0.8, 0.08), size=vector(0.72, 1.6, 0.18), color=vector(0.85, 0.28, 0.12), opacity=0.85)
bh_bar = box(pos=vector(-10.7, base_y + 1.8, 0.08), size=vector(0.72, 3.6, 0.18), color=vector(0.02, 0.02, 0.04), opacity=0.93)
bh_bar_glow = box(pos=vector(-10.7, base_y + 1.8, 0.18), size=vector(0.86, 3.75, 0.05), color=vector(1.0, 0.55, 0.16), opacity=0.35, emissive=True)

# Envelope grid: dust opacity and engine dominance
zone_grid = []
for row in range(3):
    for col in range(6):
        z = -10.8 + col * 1.05
        y = 5.8 - row * 0.55
        cell = box(
            pos=vector(9.7, y, z),
            size=vector(0.06, 0.35, 0.72),
            color=vector(0.74, 0.79, 0.86),
            opacity=0.22,
            emissive=True,
        )
        cell._row = row
        cell._col = col
        zone_grid.append(cell)

# Labels
label(
    pos=vector(0, 6.7, 0),
    text="Little Red Dot Engine",
    height=24,
    color=vector(0.18, 0.20, 0.25),
    box=False,
)
label(
    pos=vector(0, 5.9, 0),
    text="small dusty host • oversized hidden black hole • red glow through obscuring gas",
    height=12,
    color=vector(0.32, 0.34, 0.39),
    box=False,
)

status = label(
    pos=vector(0, -8.0, 0),
    text="",
    height=13,
    color=vector(0.10, 0.12, 0.16),
    box=False,
)
label(pos=vector(-12.7, base_y - 0.25, 0), text="host\ngalaxy", height=10, color=vector(0.25, 0.25, 0.30), box=False)
label(pos=vector(-10.7, base_y - 0.25, 0), text="black\nhole", height=10, color=vector(0.25, 0.25, 0.30), box=False)
label(pos=vector(-11.7, base_y + 4.15, 0), text="mass balance", height=11, color=vector(0.18, 0.20, 0.25), box=False)
label(pos=vector(9.7, 6.55, -8.3), text="revealed test zones", height=10, color=vector(0.18, 0.20, 0.25), box=False)

# Camera controls remain free; set a useful opening view
scene.camera.pos = vector(0, 7.5, 20)
scene.camera.axis = vector(0, -5.5, -20)
scene.userspin = True
scene.userzoom = True
scene.userpan = True

# ---------- Simulation loop ----------

round_timer = 0.0
phase_duration = 15.0
phase_names = [
    "camouflaged red dot",
    "dust-obscured engine",
    "central monster revealed",
    "overmassive black hole confirmed",
]
phase_index = 0

# Model values for display
host_mass = 1.0
bh_mass = 4.8
accretion_power = 0.0
dust_opacity_signal = 0.0
revealed_fraction = 0.0

clock = 0.0
while True:
    rate(60)
    dt = 1 / 60
    clock += dt
    round_timer += dt

    if round_timer > phase_duration:
        round_timer = 0
        phase_index = (phase_index + 1) % len(phase_names)

    phase_progress = round_timer / phase_duration
    pulse = 0.5 + 0.5 * math.sin(clock * 2.1)
    deep_pulse = 0.5 + 0.5 * math.sin(clock * 0.55 + phase_index)

    # Phase behavior
    if phase_index == 0:
        target_reveal = 0.18 + 0.10 * pulse
        target_dust = 0.88
        target_power = 0.25 + 0.12 * pulse
    elif phase_index == 1:
        target_reveal = 0.35 + 0.15 * phase_progress
        target_dust = 0.72 - 0.16 * phase_progress
        target_power = 0.48 + 0.18 * pulse
    elif phase_index == 2:
        target_reveal = 0.62 + 0.22 * phase_progress
        target_dust = 0.52 - 0.22 * phase_progress
        target_power = 0.72 + 0.22 * pulse
    else:
        target_reveal = 0.88 + 0.10 * pulse
        target_dust = 0.28 + 0.08 * deep_pulse
        target_power = 0.94 + 0.06 * pulse

    revealed_fraction += (target_reveal - revealed_fraction) * 0.025
    dust_opacity_signal += (target_dust - dust_opacity_signal) * 0.025
    accretion_power += (target_power - accretion_power) * 0.025

    # Host/dust/engine size and opacity pulse
    host_core.radius = 1.45 + 0.15 * pulse + 0.15 * dust_opacity_signal
    host_core.opacity = 0.18 + 0.18 * dust_opacity_signal
    host_glow.radius = 2.25 + 0.42 * pulse + 0.75 * revealed_fraction
    host_glow.opacity = 0.05 + 0.10 * revealed_fraction
    outer_dust_haze.radius = 4.25 + 0.4 * math.sin(clock * 0.37)
    outer_dust_haze.opacity = 0.035 + 0.09 * dust_opacity_signal

    black_hole.radius = 0.60 + 0.20 * revealed_fraction + 0.04 * pulse
    event_horizon_rim.radius = 0.88 + 0.18 * revealed_fraction + 0.06 * pulse
    event_horizon_rim.opacity = 0.35 + 0.55 * revealed_fraction
    photon_rim.radius = 1.08 + 0.24 * revealed_fraction + 0.07 * math.sin(clock * 3.4)
    photon_rim.opacity = 0.25 + 0.55 * revealed_fraction

    # Accretion disk rotation and brightening
    disk_axis = vector(0.12 + 0.05 * math.sin(clock * 0.31), 1, 0.18 + 0.06 * math.cos(clock * 0.27))
    for i, ring_obj in enumerate(accretion_rings):
        spin = clock * (0.55 + i * 0.08)
        ring_obj.axis = vector(
            disk_axis.x + 0.08 * math.sin(spin),
            1,
            disk_axis.z + 0.08 * math.cos(spin),
        )
        ring_obj.radius = 1.18 + i * 0.25 + 0.05 * math.sin(clock * 2.0 + i)
        ring_obj.opacity = clamp((0.12 + 0.48 * accretion_power) - i * 0.035, 0.06, 0.68)
        ring_obj.color = vector(1.0, 0.36 + 0.35 * accretion_power - i * 0.02, 0.10 + 0.16 * pulse)

    # Dust motion around object
    for dust in obscuring_dust:
        dust._angle += dust._speed * dt
        bob = 0.22 * math.sin(clock * 0.8 + dust._phase)
        dust.pos = vector(dust._rr * math.cos(dust._angle), dust._height + bob, dust._rr * math.sin(dust._angle))
        dust.opacity = clamp(0.10 + 0.42 * dust_opacity_signal + 0.08 * math.sin(clock * 1.7 + dust._phase), 0.05, 0.62)
        dust.radius = dust.radius * 0.995 + (0.05 + 0.12 * dust_opacity_signal) * 0.005

    # Sparse host stars orbit slowly, dimmed by dust
    for st in host_stars:
        st._angle += st._speed * dt
        st.pos = vector(st._rr * math.cos(st._angle), st._height + 0.05 * math.sin(clock + st._rr), st._rr * math.sin(st._angle))
        st.opacity = clamp(0.18 + 0.55 * (1 - dust_opacity_signal) + 0.10 * pulse, 0.12, 0.82)

    # Energy beams become more visible as dust clears / engine revealed
    for beam in beams:
        beam._theta += beam._speed * dt
        beam_axis = vector(math.cos(beam._theta), 0.08 * math.sin(clock + beam._theta), math.sin(beam._theta))
        beam.axis = beam_axis * (beam._length + 1.3 * accretion_power * pulse)
        beam.radius = 0.012 + 0.04 * accretion_power * (0.4 + 0.6 * pulse)
        beam.opacity = clamp(0.04 + 0.35 * accretion_power * revealed_fraction, 0.03, 0.45)
        beam.color = vector(1.0, 0.20 + 0.45 * accretion_power, 0.06)

    # Gas packets spiral inward; when swallowed, reset to outer dusty host
    for pkt in infall_packets:
        pkt._rr -= pkt._spiral * dt * (0.8 + 1.5 * accretion_power)
        pkt._angle += pkt._speed * dt * (1.5 + 2.5 / max(0.6, pkt._rr))
        pkt._height *= 0.999
        pkt.pos = vector(pkt._rr * math.cos(pkt._angle), pkt._height, pkt._rr * math.sin(pkt._angle))
        pkt.opacity = clamp(0.25 + 0.60 * accretion_power, 0.18, 0.95)
        pkt.radius = clamp(0.035 + 0.035 * pkt._rr / 6.0, 0.03, 0.11)
        if pkt._rr < 0.92:
            pkt._rr = random.uniform(5.2, 8.8)
            pkt._angle = random.uniform(0, 2 * math.pi)
            pkt._height = random.uniform(-1.6, 1.6)

    # Mass panel: black hole outweighs host, with pulsing glow
    bh_scale = 3.55 + 0.30 * revealed_fraction + 0.08 * pulse
    host_scale = 1.15 + 0.28 * (1 - dust_opacity_signal)
    host_bar.size.y = host_scale
    host_bar.pos.y = base_y + host_scale / 2
    bh_bar.size.y = bh_scale
    bh_bar.pos.y = base_y + bh_scale / 2
    bh_bar_glow.size.y = bh_scale + 0.15
    bh_bar_glow.pos.y = base_y + (bh_scale + 0.15) / 2
    bh_bar_glow.opacity = 0.18 + 0.28 * revealed_fraction * pulse

    # Reveal grid cells as simulated observing confirmations
    confirm_level = int(revealed_fraction * len(zone_grid))
    for idx, cell in enumerate(zone_grid):
        if idx <= confirm_level:
            cell.color = vector(1.0, 0.36 + 0.35 * pulse, 0.12)
            cell.opacity = 0.42 + 0.28 * pulse
        else:
            cell.color = vector(0.74, 0.79, 0.86)
            cell.opacity = 0.18

    # Occasional central flare through the dust
    flare = 0.0
    if math.sin(clock * 0.83) > 0.965:
        flare = (math.sin(clock * 0.83) - 0.965) / 0.035
    photon_rim.thickness = 0.025 + 0.05 * flare
    event_horizon_rim.thickness = 0.04 + 0.04 * flare
    host_glow.opacity = clamp(host_glow.opacity + 0.05 * flare, 0.04, 0.28)

    # Star field shimmer
    for i, s in enumerate(stars):
        if i % 7 == 0:
            s.opacity = clamp(0.25 + 0.35 * math.sin(clock * 0.6 + i) ** 2, 0.18, 0.88)

    # Status dashboard
    displayed_bh_mass = bh_mass + 0.25 * revealed_fraction * math.sin(clock * 0.5)
    displayed_host_mass = host_mass + 0.05 * math.sin(clock * 0.4)
    ratio = displayed_bh_mass / displayed_host_mass
    status.text = (
        f"mode: {phase_names[phase_index]}   |   "
        f"dust opacity: {dust_opacity_signal:0.2f}   |   "
        f"engine reveal: {revealed_fraction:0.2f}   |   "
        f"BH / host mass ratio: {ratio:0.1f}x   |   "
        f"accretion glow: {accretion_power:0.2f}"
    )
