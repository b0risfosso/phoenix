"""
Spore-Bearing Universe

A VPython simulation of a universe expanding like a living membrane,
growing bright cosmic sacs along its outer edge. Sacs swell, pulse, burst,
and release glowing spores into the surrounding void.

Run with:
    python spore_bearing_universe.py

Requires:
    pip install vpython
"""

from vpython import (
    canvas, vector, color, sphere, curve, label, rate, mag, norm,
    random, sin, cos, pi, wtext, button
)
import math
import random as pyrandom

# -----------------------------
# Scene setup: light styling
# -----------------------------
scene = canvas(
    title="Spore-Bearing Universe — expanding membrane, cosmic sacs, drifting spores",
    width=1100,
    height=760,
    background=vector(0.94, 0.96, 1.0),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 0, 35)
scene.camera.axis = vector(0, 0, -35)
scene.range = 18

running = True

# Keyboard-adjustable controls.
expansion_speed = 1.0
spore_speed = 1.0
keyboard_wind = vector(0, 0, 0)
membrane_wave_boost = 1.0
auto_burst_requested = False

wtext(text="\n")
status = wtext(text="")


def toggle_pause():
    global running
    running = not running


def clear_all_spores():
    global spores
    for spore in spores:
        spore.hide()
    spores = []


def request_burst():
    global auto_burst_requested
    auto_burst_requested = True


def reset_simulation():
    global t, radius, expansion_complete, expansion_speed, spore_speed, keyboard_wind, membrane_wave_boost
    clear_all_spores()
    t = 0.0
    radius = INITIAL_RADIUS
    expansion_complete = False
    expansion_speed = 1.0
    spore_speed = 1.0
    keyboard_wind = vector(0, 0, 0)
    membrane_wave_boost = 1.0
    for sac in sacs:
        sac.growth = pyrandom.uniform(0.05, 0.35)
        sac.burst_cooldown = pyrandom.uniform(0.0, 2.0)
        sac.last_burst_flash = 0.0
        sac.burst_count = 0


def handle_keydown(evt):
    global running, expansion_speed, spore_speed, keyboard_wind, membrane_wave_boost
    key = evt.key.lower() if hasattr(evt, "key") else ""

    if key in (" ", "space"):
        running = not running
    elif key == "r":
        reset_simulation()
    elif key == "c":
        clear_all_spores()
    elif key == "b":
        request_burst()
    elif key in ("+", "="):
        expansion_speed = min(4.0, expansion_speed + 0.25)
    elif key in ("-", "_"):
        expansion_speed = max(0.0, expansion_speed - 0.25)
    elif key == "s":
        spore_speed = min(3.0, spore_speed + 0.25)
    elif key == "x":
        spore_speed = max(0.25, spore_speed - 0.25)
    elif key == "w":
        membrane_wave_boost = min(2.5, membrane_wave_boost + 0.25)
    elif key == "q":
        membrane_wave_boost = max(0.25, membrane_wave_boost - 0.25)
    elif key in ("left", "a"):
        keyboard_wind += vector(-0.0025, 0, 0)
    elif key in ("right", "d"):
        keyboard_wind += vector(0.0025, 0, 0)
    elif key == "up":
        keyboard_wind += vector(0, 0.0025, 0)
    elif key == "down":
        keyboard_wind += vector(0, -0.0025, 0)
    elif key == "z":
        keyboard_wind = vector(0, 0, 0)


scene.bind("keydown", handle_keydown)

button(text="Pause / Resume", bind=toggle_pause)
wtext(text="   Drag to rotate. Scroll to zoom.\n")
wtext(text="Keyboard: Space pause | R reset | B burst sacs | C clear spores | +/- expansion | S/X spore speed | W/Q membrane waves | Arrows/A/D wind | Z clear wind\n\n")

# -----------------------------
# Simulation constants
# -----------------------------
INITIAL_RADIUS = 4.2
MAX_RADIUS = 11.5
EXPANSION_RATE = 0.010
MEMBRANE_POINTS = 96
EDGE_SAC_COUNT = 14
SPORE_LIMIT = 260

# Colors are intentionally bright and readable against a light background.
MEMBRANE_COLOR = vector(0.45, 0.56, 0.95)
MEMBRANE_GLOW = vector(0.64, 0.78, 1.0)
SAC_COLOR = vector(1.0, 0.68, 0.22)
SAC_RIPE_COLOR = vector(1.0, 0.90, 0.34)
SPORE_COLORS = [
    vector(0.96, 0.72, 1.0),
    vector(0.62, 0.92, 1.0),
    vector(1.0, 0.84, 0.46),
    vector(0.76, 1.0, 0.72),
]

# -----------------------------
# Core universe membrane
# -----------------------------
universe_core = sphere(
    pos=vector(0, 0, 0),
    radius=INITIAL_RADIUS * 0.96,
    color=vector(0.72, 0.82, 1.0),
    opacity=0.17,
    shininess=0.15,
)

inner_glow = sphere(
    pos=vector(0, 0, 0),
    radius=INITIAL_RADIUS * 0.35,
    color=vector(0.98, 0.95, 0.65),
    opacity=0.35,
    shininess=0.4,
)

# A scalloped ring of points shows the membrane edge without using torus().
membrane_edge = curve(color=MEMBRANE_COLOR, radius=0.045)
membrane_ripples = []
for i in range(4):
    membrane_ripples.append(curve(color=MEMBRANE_GLOW, radius=0.018 + i * 0.004))

# Background void markers: faint static stars outside the universe.
stars = []
for _ in range(90):
    angle = pyrandom.uniform(0, 2 * pi)
    distance = pyrandom.uniform(13.5, 24.0)
    z = pyrandom.uniform(-3.5, 3.5)
    stars.append(
        sphere(
            pos=vector(distance * cos(angle), distance * sin(angle), z),
            radius=pyrandom.uniform(0.025, 0.07),
            color=vector(0.68, 0.72, 0.82),
            opacity=pyrandom.uniform(0.20, 0.45),
            emissive=False,
        )
    )

# -----------------------------
# Sacs and spores
# -----------------------------
class CosmicSac:
    def __init__(self, index, base_angle):
        self.index = index
        self.base_angle = base_angle
        self.angle_offset = pyrandom.uniform(-0.08, 0.08)
        self.phase = pyrandom.uniform(0, 2 * pi)
        self.age = pyrandom.uniform(0, 6.0)
        self.growth = pyrandom.uniform(0.05, 0.35)
        self.burst_cooldown = pyrandom.uniform(0.0, 2.0)
        self.last_burst_flash = 0.0
        self.burst_count = 0
        self.body = sphere(
            pos=vector(0, 0, 0),
            radius=0.25,
            color=SAC_COLOR,
            opacity=0.72,
            shininess=0.6,
            emissive=True,
        )
        self.halo = sphere(
            pos=vector(0, 0, 0),
            radius=0.45,
            color=vector(1.0, 0.82, 0.36),
            opacity=0.13,
            shininess=0.1,
            emissive=True,
        )
        self.stem = curve(color=vector(0.54, 0.63, 0.95), radius=0.025)

    def direction(self, t):
        slow_drift = 0.08 * sin(t * 0.17 + self.phase)
        angle = self.base_angle + self.angle_offset + slow_drift
        return vector(cos(angle), sin(angle), 0)

    def update(self, t, radius):
        self.age += 0.018
        self.burst_cooldown = max(0.0, self.burst_cooldown - 0.018)
        self.last_burst_flash = max(0.0, self.last_burst_flash - 0.035)

        # Sacs grow faster as the membrane grows larger, then reset after bursting.
        maturity_push = 0.0013 + 0.0008 * (radius / MAX_RADIUS)
        self.growth += maturity_push * (1.0 + 0.45 * sin(t * 0.8 + self.phase))
        self.growth = min(self.growth, 1.18)

        d = self.direction(t)
        root_pos = d * (radius * 0.93)
        sac_pos = d * (radius + 0.48 + self.growth * 1.05) + vector(0, 0, 0.35 * sin(t * 0.5 + self.phase))

        pulse = 0.08 * sin(t * 3.3 + self.phase)
        sac_radius = 0.26 + 0.62 * self.growth + pulse
        ripe = self.growth > 0.82
        flash = self.last_burst_flash

        self.body.pos = sac_pos
        self.body.radius = max(0.18, sac_radius)
        self.body.color = SAC_RIPE_COLOR if ripe else SAC_COLOR
        self.body.opacity = 0.62 + 0.22 * self.growth + 0.12 * flash

        self.halo.pos = sac_pos
        self.halo.radius = self.body.radius * (1.75 + 0.45 * sin(t * 2.5 + self.phase))
        self.halo.opacity = 0.08 + 0.08 * self.growth + 0.22 * flash

        self.stem.clear()
        self.stem.append(root_pos)
        self.stem.append((root_pos + sac_pos) * 0.5 + vector(0, 0, 0.12 * sin(t + self.phase)))
        self.stem.append(sac_pos)

        if self.growth >= 1.0 and self.burst_cooldown <= 0.0:
            self.burst(radius, sac_pos, d)

    def burst(self, radius, sac_pos, direction):
        global spores
        self.burst_count += 1
        self.last_burst_flash = 1.0
        self.burst_cooldown = pyrandom.uniform(5.0, 9.0)

        # Burst releases a fan of spores outward, with some sideways drift.
        spore_count = pyrandom.randint(10, 18)
        for _ in range(spore_count):
            if len(spores) >= SPORE_LIMIT:
                oldest = spores.pop(0)
                oldest.hide()
            side = vector(-direction.y, direction.x, 0)
            spread = side * pyrandom.uniform(-0.55, 0.55) + vector(0, 0, pyrandom.uniform(-0.18, 0.18))
            velocity = norm(direction + spread) * pyrandom.uniform(0.045, 0.105)
            velocity += direction * (0.04 + radius * 0.002)
            spores.append(Spore(sac_pos + direction * 0.3, velocity))

        # Sac collapses into a small bud that can regrow.
        self.growth = pyrandom.uniform(0.03, 0.18)


class Spore:
    def __init__(self, pos, velocity):
        self.velocity = velocity
        self.age = 0.0
        self.life = pyrandom.uniform(10.0, 18.0)
        self.phase = pyrandom.uniform(0, 2 * pi)
        self.color = pyrandom.choice(SPORE_COLORS)
        self.body = sphere(
            pos=pos,
            radius=pyrandom.uniform(0.08, 0.16),
            color=self.color,
            opacity=0.88,
            shininess=0.6,
            emissive=True,
        )
        self.halo = sphere(
            pos=pos,
            radius=self.body.radius * 2.3,
            color=self.color,
            opacity=0.12,
            emissive=True,
        )
        self.trail = curve(color=self.color, radius=0.012)
        self.trail_positions = [vector(pos.x, pos.y, pos.z)]
        self.trail.append(pos)

    def update(self, t):
        self.age += 0.035
        curl = vector(
            0.004 * sin(t * 1.7 + self.phase),
            0.004 * cos(t * 1.3 + self.phase),
            0.002 * sin(t * 0.9 + self.phase),
        )
        self.velocity += curl + keyboard_wind
        max_speed = 0.18 * spore_speed
        if mag(self.velocity) > max_speed:
            self.velocity = norm(self.velocity) * max_speed
        self.body.pos += self.velocity * spore_speed
        self.halo.pos = self.body.pos

        pulse = 1.0 + 0.22 * sin(t * 4.0 + self.phase)
        fade = max(0.0, 1.0 - self.age / self.life)
        self.body.radius = max(0.025, self.body.radius * 0.998 + 0.003 * pulse)
        self.body.opacity = 0.18 + 0.70 * fade
        self.halo.radius = self.body.radius * (2.0 + 0.7 * pulse)
        self.halo.opacity = 0.04 + 0.12 * fade

        # Keep trails short for performance.
        # Some VPython builds expose curve.npoints but not curve.points,
        # so this script stores its own list of recent trail positions.
        self.trail_positions.append(vector(self.body.pos.x, self.body.pos.y, self.body.pos.z))
        if len(self.trail_positions) > 18:
            self.trail_positions = self.trail_positions[-18:]
            self.trail.clear()
            for p in self.trail_positions:
                self.trail.append(p)
        else:
            self.trail.append(self.body.pos)

        return self.age < self.life

    def hide(self):
        self.body.visible = False
        self.halo.visible = False
        self.trail.visible = False


sacs = []
for i in range(EDGE_SAC_COUNT):
    sacs.append(CosmicSac(i, 2 * pi * i / EDGE_SAC_COUNT))

spores = []

# -----------------------------
# Membrane geometry helpers
# -----------------------------
def membrane_point(angle, radius, t, ripple_index=0):
    living_wave = membrane_wave_boost * 0.28 * sin(5 * angle + t * 1.15)
    smaller_wave = membrane_wave_boost * 0.12 * sin(11 * angle - t * 0.75 + ripple_index)
    breathing = membrane_wave_boost * 0.08 * sin(t * 0.65 + ripple_index)
    r = radius + living_wave + smaller_wave + breathing
    z = 0.35 * sin(3 * angle + t * 0.45 + ripple_index)
    return vector(r * cos(angle), r * sin(angle), z)


def rebuild_membrane(radius, t):
    membrane_edge.clear()
    for i in range(MEMBRANE_POINTS + 1):
        a = 2 * pi * i / MEMBRANE_POINTS
        membrane_edge.append(membrane_point(a, radius, t))

    for j, ripple in enumerate(membrane_ripples):
        ripple.clear()
        scale = 0.58 + j * 0.105
        for i in range(MEMBRANE_POINTS + 1):
            a = 2 * pi * i / MEMBRANE_POINTS
            ripple.append(membrane_point(a, radius * scale, t, j + 1))


# -----------------------------
# Informational labels
# -----------------------------
title_label = label(
    pos=vector(0, -14.5, 0),
    text="Spore-Bearing Universe",
    height=18,
    color=vector(0.16, 0.18, 0.26),
    box=False,
    opacity=0,
)

burst_label = label(
    pos=vector(0, 13.2, 0),
    text="Cosmic sacs grow along the membrane edge and burst into drifting spores.",
    height=12,
    color=vector(0.22, 0.24, 0.33),
    box=False,
    opacity=0,
)

# -----------------------------
# Main loop
# -----------------------------
t = 0.0
radius = INITIAL_RADIUS
expansion_complete = False

while True:
    rate(60)
    if not running:
        status.text = "Paused.   "
        continue

    t += 0.035

    # Expansion slows as the membrane approaches its mature size.
    if radius < MAX_RADIUS:
        radius += EXPANSION_RATE * expansion_speed * (1.0 - (radius / (MAX_RADIUS * 1.15)))
    else:
        expansion_complete = True
        radius = MAX_RADIUS + 0.18 * sin(t * 0.22)

    universe_core.radius = radius * 0.96
    universe_core.opacity = 0.12 + 0.05 * sin(t * 0.55) ** 2
    inner_glow.radius = radius * (0.22 + 0.03 * sin(t * 0.8))
    inner_glow.opacity = 0.25 + 0.12 * sin(t * 0.7) ** 2

    rebuild_membrane(radius, t)

    total_bursts = 0
    ripe_count = 0
    if auto_burst_requested:
        for sac in sacs:
            sac.growth = max(sac.growth, 1.03)
            sac.burst_cooldown = 0.0
        auto_burst_requested = False

    for sac in sacs:
        sac.update(t, radius)
        total_bursts += sac.burst_count
        if sac.growth > 0.82:
            ripe_count += 1

    live_spores = []
    for spore in spores:
        if spore.update(t):
            live_spores.append(spore)
        else:
            spore.hide()
    spores = live_spores

    status.text = (
        f"Membrane radius: {radius:0.2f}   "
        f"ripe sacs: {ripe_count}/{EDGE_SAC_COUNT}   "
        f"spores in void: {len(spores)}   "
        f"total bursts: {total_bursts}   "
        f"expansion x{expansion_speed:0.2f}   "
        f"spore speed x{spore_speed:0.2f}   "
        f"wind ({keyboard_wind.x:0.3f}, {keyboard_wind.y:0.3f})   "
    )
