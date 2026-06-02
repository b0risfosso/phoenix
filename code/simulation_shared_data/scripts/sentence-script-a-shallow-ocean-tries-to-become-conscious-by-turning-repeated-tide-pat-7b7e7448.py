"""
Tide Memory Ocean - Initial Simulation

A shallow ocean tries to become conscious by turning repeated tide paths into memory.

Start state:
    A shallow ocean surface with simple wave particles moving in repeated tide cycles.
    Each wave leaves a faint trace of where it has traveled.

End goal:
    The ocean begins recognizing repeated wave paths as memory. Tides stop being
    random motion and become stored patterns that influence future movement.

Controls:
    Q / Esc : quit
    R       : reset simulation
    Space   : pause / resume
    M       : toggle memory influence
    T       : toggle trace visibility
"""

from vpython import *
import math
import random
import time

# -----------------------------
# Scene setup
# -----------------------------
scene.title = "Tide Memory Ocean - Initial Simulation"
scene.width = 1200
scene.height = 760
scene.background = vector(0.78, 0.90, 0.98)
scene.forward = vector(-0.35, -0.55, -1.0)
scene.center = vector(0, 0, 0)
scene.range = 30
scene.autoscale = False

# -----------------------------
# Configuration
# -----------------------------
OCEAN_HALF_SIZE = 24
GRID_SPACING = 3
MEMORY_GRID_N = 33
MEMORY_CELL_SIZE = (OCEAN_HALF_SIZE * 2) / MEMORY_GRID_N
NUM_WAVES = 70
NUM_SURFACE_POINTS = 17
TRACE_SAMPLE_INTERVAL = 0.16
MAX_TRACE_POINTS_PER_WAVE = 75
DT = 0.025

running = True
paused = False
memory_enabled = True
traces_visible = True
reset_requested = False

# -----------------------------
# Utility helpers
# -----------------------------

def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, amount):
    return a + (b - a) * amount


def smoothstep(edge0, edge1, x):
    x = clamp((x - edge0) / max(edge1 - edge0, 1e-9), 0.0, 1.0)
    return x * x * (3 - 2 * x)


def cell_from_pos(pos):
    gx = int((pos.x + OCEAN_HALF_SIZE) / (OCEAN_HALF_SIZE * 2) * MEMORY_GRID_N)
    gz = int((pos.z + OCEAN_HALF_SIZE) / (OCEAN_HALF_SIZE * 2) * MEMORY_GRID_N)
    gx = clamp(gx, 0, MEMORY_GRID_N - 1)
    gz = clamp(gz, 0, MEMORY_GRID_N - 1)
    return gx, gz


def pos_from_cell(gx, gz):
    x = -OCEAN_HALF_SIZE + (gx + 0.5) * MEMORY_CELL_SIZE
    z = -OCEAN_HALF_SIZE + (gz + 0.5) * MEMORY_CELL_SIZE
    return vector(x, 0.025, z)


def color_mix(c1, c2, amount):
    amount = clamp(amount, 0, 1)
    return vector(
        lerp(c1.x, c2.x, amount),
        lerp(c1.y, c2.y, amount),
        lerp(c1.z, c2.z, amount),
    )

# -----------------------------
# Visual base objects
# -----------------------------

ocean_floor = box(
    pos=vector(0, -0.18, 0),
    size=vector(OCEAN_HALF_SIZE * 2.1, 0.08, OCEAN_HALF_SIZE * 2.1),
    color=vector(0.48, 0.76, 0.88),
    opacity=0.55,
)

surface_sheet = box(
    pos=vector(0, 0, 0),
    size=vector(OCEAN_HALF_SIZE * 2, 0.025, OCEAN_HALF_SIZE * 2),
    color=vector(0.56, 0.84, 0.96),
    opacity=0.35,
)

boundary = curve(color=vector(0.18, 0.48, 0.62), radius=0.035)
boundary.append(vector(-OCEAN_HALF_SIZE, 0.04, -OCEAN_HALF_SIZE))
boundary.append(vector(OCEAN_HALF_SIZE, 0.04, -OCEAN_HALF_SIZE))
boundary.append(vector(OCEAN_HALF_SIZE, 0.04, OCEAN_HALF_SIZE))
boundary.append(vector(-OCEAN_HALF_SIZE, 0.04, OCEAN_HALF_SIZE))
boundary.append(vector(-OCEAN_HALF_SIZE, 0.04, -OCEAN_HALF_SIZE))

# Gentle coordinate grid beneath the water
floor_lines = []
for i in range(-OCEAN_HALF_SIZE, OCEAN_HALF_SIZE + 1, GRID_SPACING):
    c1 = curve(color=vector(0.72, 0.86, 0.92), radius=0.008)
    c1.append(vector(i, -0.12, -OCEAN_HALF_SIZE))
    c1.append(vector(i, -0.12, OCEAN_HALF_SIZE))
    floor_lines.append(c1)

    c2 = curve(color=vector(0.72, 0.86, 0.92), radius=0.008)
    c2.append(vector(-OCEAN_HALF_SIZE, -0.12, i))
    c2.append(vector(OCEAN_HALF_SIZE, -0.12, i))
    floor_lines.append(c2)

# Surface beads that rise/fall with the tide, giving the plane a living pulse
surface_points = []
for ix in range(NUM_SURFACE_POINTS):
    for iz in range(NUM_SURFACE_POINTS):
        x = lerp(-OCEAN_HALF_SIZE, OCEAN_HALF_SIZE, ix / (NUM_SURFACE_POINTS - 1))
        z = lerp(-OCEAN_HALF_SIZE, OCEAN_HALF_SIZE, iz / (NUM_SURFACE_POINTS - 1))
        bead = sphere(
            pos=vector(x, 0.03, z),
            radius=0.055,
            color=vector(0.86, 0.97, 1.0),
            opacity=0.28,
        )
        bead.base_x = x
        bead.base_z = z
        surface_points.append(bead)

# -----------------------------
# Memory field
# -----------------------------

memory_strength = [[0.0 for _ in range(MEMORY_GRID_N)] for _ in range(MEMORY_GRID_N)]
memory_marks = []
for gx in range(MEMORY_GRID_N):
    row = []
    for gz in range(MEMORY_GRID_N):
        mark = box(
            pos=pos_from_cell(gx, gz),
            size=vector(MEMORY_CELL_SIZE * 0.88, 0.018, MEMORY_CELL_SIZE * 0.88),
            color=vector(0.20, 0.58, 0.78),
            opacity=0.0,
        )
        row.append(mark)
    memory_marks.append(row)

# -----------------------------
# Wave particles
# -----------------------------

class WaveParticle:
    def __init__(self, idx):
        self.idx = idx
        self.reset(randomize_phase=True)

    def reset(self, randomize_phase=False):
        self.angle = random.uniform(0, math.tau)
        self.radial_band = random.uniform(6.0, OCEAN_HALF_SIZE * 0.94)
        self.phase = random.uniform(0, math.tau) if randomize_phase else 0
        self.speed = random.uniform(0.42, 0.92)
        self.tide_bias = random.uniform(-0.35, 0.35)
        self.memory_pull = vector(0, 0, 0)
        self.last_trace_time = 0
        self.trace_points = []
        self.body = sphere(
            pos=vector(0, 0.2, 0),
            radius=random.uniform(0.13, 0.22),
            color=vector(0.78, 0.96, 1.0),
            emissive=True,
            opacity=0.88,
        )
        self.glow = sphere(
            pos=vector(0, 0.2, 0),
            radius=self.body.radius * 2.2,
            color=vector(0.70, 0.92, 1.0),
            opacity=0.10,
        )
        self.path = curve(color=vector(0.84, 0.98, 1.0), radius=0.018)
        self.update_position(0, 0)

    def update_position(self, t, tide_phase):
        # Repeated tide cycle: waves travel in slow loops, but the whole ocean breathes in/out.
        cycle_radius = self.radial_band + 3.8 * math.sin(tide_phase + self.tide_bias)
        wobble = 1.3 * math.sin(t * 0.65 + self.phase + self.idx * 0.21)
        local_angle = self.angle + t * self.speed * 0.16 + 0.14 * math.sin(t * 0.23 + self.phase)

        base = vector(
            (cycle_radius + wobble) * math.cos(local_angle),
            0,
            (cycle_radius * 0.55 + wobble) * math.sin(local_angle),
        )

        # Stronger tide sweep from left to right and back.
        sweep = vector(6.0 * math.sin(tide_phase + self.phase * 0.18), 0, 2.0 * math.sin(tide_phase * 0.5 + self.phase))
        target = base + sweep

        # Memory influence: nearby strengthened path cells gently pull new waves toward stored lanes.
        if memory_enabled:
            gx, gz = cell_from_pos(target)
            pull = vector(0, 0, 0)
            total = 0.0
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    nx = gx + dx
                    nz = gz + dz
                    if 0 <= nx < MEMORY_GRID_N and 0 <= nz < MEMORY_GRID_N:
                        s = memory_strength[nx][nz]
                        if s > 0.02:
                            p = pos_from_cell(nx, nz)
                            direction = vector(p.x - target.x, 0, p.z - target.z)
                            dist = max(mag(direction), 0.001)
                            pull += norm(direction) * s / (1.0 + dist)
                            total += s
            if total > 0:
                self.memory_pull = self.memory_pull * 0.90 + pull * 0.10
                target += self.memory_pull * 2.6

        # Keep waves within the ocean boundary.
        target.x = clamp(target.x, -OCEAN_HALF_SIZE + 0.6, OCEAN_HALF_SIZE - 0.6)
        target.z = clamp(target.z, -OCEAN_HALF_SIZE + 0.6, OCEAN_HALF_SIZE - 0.6)
        target.y = 0.24 + 0.22 * math.sin(tide_phase + self.phase) + 0.06 * math.sin(t * 3.0 + self.idx)

        self.body.pos = target
        self.glow.pos = target

    def leave_trace_and_memory(self, t):
        if t - self.last_trace_time < TRACE_SAMPLE_INTERVAL:
            return
        self.last_trace_time = t

        pos = vector(self.body.pos.x, 0.075, self.body.pos.z)
        gx, gz = cell_from_pos(pos)
        memory_strength[gx][gz] = clamp(memory_strength[gx][gz] + 0.055, 0.0, 1.0)

        if traces_visible:
            self.path.append(pos)
            self.trace_points.append(pos)
            while len(self.trace_points) > MAX_TRACE_POINTS_PER_WAVE:
                self.trace_points.pop(0)
                if self.path.npoints > MAX_TRACE_POINTS_PER_WAVE:
                    self.path.pop(0)
        else:
            self.path.clear()
            self.trace_points.clear()

    def clear_trace(self):
        self.path.clear()
        self.trace_points.clear()

waves = [WaveParticle(i) for i in range(NUM_WAVES)]

# -----------------------------
# Labels and status objects
# -----------------------------

title_label = label(
    pos=vector(0, 5.2, -OCEAN_HALF_SIZE - 2.2),
    text="Tide Memory Ocean",
    height=20,
    box=False,
    color=vector(0.05, 0.24, 0.34),
)

status_label = label(
    pos=vector(-OCEAN_HALF_SIZE, 3.9, -OCEAN_HALF_SIZE - 2.2),
    text="",
    height=12,
    box=False,
    align="left",
    color=vector(0.05, 0.24, 0.34),
)

memory_core = sphere(
    pos=vector(0, 1.6, 0),
    radius=0.45,
    color=vector(0.22, 0.72, 0.95),
    opacity=0.22,
    emissive=True,
)

memory_ring = ring(
    pos=vector(0, 1.6, 0),
    axis=vector(0, 1, 0),
    radius=1.05,
    thickness=0.035,
    color=vector(0.22, 0.72, 0.95),
    opacity=0.24,
)

# -----------------------------
# Event handling
# -----------------------------

def handle_keydown(evt):
    global running, paused, reset_requested, memory_enabled, traces_visible
    key = evt.key.lower()
    if key in ("q", "esc"):
        running = False
    elif key == " ":
        paused = not paused
    elif key == "r":
        reset_requested = True
    elif key == "m":
        memory_enabled = not memory_enabled
    elif key == "t":
        traces_visible = not traces_visible
        if not traces_visible:
            for wave in waves:
                wave.clear_trace()

scene.bind("keydown", handle_keydown)

# -----------------------------
# Reset and update functions
# -----------------------------

def reset_simulation():
    global memory_strength
    memory_strength = [[0.0 for _ in range(MEMORY_GRID_N)] for _ in range(MEMORY_GRID_N)]
    for gx in range(MEMORY_GRID_N):
        for gz in range(MEMORY_GRID_N):
            memory_marks[gx][gz].opacity = 0.0
    for wave in waves:
        wave.body.visible = False
        wave.glow.visible = False
        wave.path.visible = False
        wave.reset(randomize_phase=True)
    for wave in waves:
        wave.body.visible = True
        wave.glow.visible = True
        wave.path.visible = traces_visible


def update_surface_points(t, tide_phase):
    for bead in surface_points:
        wave_height = (
            0.18 * math.sin(0.36 * bead.base_x + tide_phase)
            + 0.14 * math.sin(0.29 * bead.base_z - tide_phase * 1.2)
            + 0.06 * math.sin(0.25 * (bead.base_x + bead.base_z) + t)
        )
        bead.pos.y = 0.04 + wave_height
        shimmer = 0.45 + 0.35 * smoothstep(-0.25, 0.25, wave_height)
        bead.opacity = 0.10 + 0.22 * shimmer


def update_memory_field():
    total_memory = 0.0
    active_cells = 0
    peak_memory = 0.0

    for gx in range(MEMORY_GRID_N):
        for gz in range(MEMORY_GRID_N):
            s = memory_strength[gx][gz]
            # Memory slowly fades unless reinforced by repeated tide paths.
            s *= 0.9978
            memory_strength[gx][gz] = s
            total_memory += s
            if s > 0.035:
                active_cells += 1
            peak_memory = max(peak_memory, s)

            mark = memory_marks[gx][gz]
            if s < 0.015:
                mark.opacity = 0.0
            else:
                mark.opacity = clamp(0.05 + s * 0.58, 0.0, 0.66)
                mark.size.y = 0.018 + 0.11 * s
                mark.color = color_mix(vector(0.18, 0.58, 0.78), vector(0.95, 0.92, 0.55), s)

    return total_memory, active_cells, peak_memory


def update_memory_symbol(t, total_memory, active_cells, peak_memory):
    awareness = clamp((total_memory / 85.0) * 0.55 + (active_cells / 420.0) * 0.35 + peak_memory * 0.10, 0, 1)
    memory_core.radius = 0.35 + awareness * 1.0 + 0.05 * math.sin(t * 3.0)
    memory_core.opacity = 0.10 + awareness * 0.38
    memory_core.color = color_mix(vector(0.22, 0.72, 0.95), vector(1.0, 0.86, 0.28), awareness)
    memory_ring.radius = 0.85 + awareness * 2.4
    memory_ring.opacity = 0.12 + awareness * 0.32
    memory_ring.rotate(angle=0.006 + awareness * 0.012, axis=vector(0, 1, 0))
    return awareness

# -----------------------------
# Main loop
# -----------------------------

t = 0.0
frame_count = 0
last_status = time.time()

while running:
    rate(45)

    if reset_requested:
        reset_simulation()
        t = 0.0
        reset_requested = False

    if paused:
        status_label.text = (
            "PAUSED | Space: resume | R: reset | M: memory influence | T: traces | Q: quit"
        )
        continue

    tide_phase = t * 0.72

    update_surface_points(t, tide_phase)

    for wave in waves:
        wave.update_position(t, tide_phase)
        wave.leave_trace_and_memory(t)
        wave.path.visible = traces_visible

    total_memory, active_cells, peak_memory = update_memory_field()
    awareness = update_memory_symbol(t, total_memory, active_cells, peak_memory)

    # The ocean surface becomes more golden as memory strengthens.
    surface_sheet.color = color_mix(vector(0.56, 0.84, 0.96), vector(0.80, 0.93, 0.72), awareness * 0.55)
    ocean_floor.opacity = 0.48 + awareness * 0.15

    now = time.time()
    if now - last_status > 0.25:
        last_status = now
        status_label.text = (
            f"memory cells: {active_cells:3d} | memory strength: {total_memory:5.1f} | "
            f"awareness: {awareness:0.2f}\n"
            f"memory influence: {'on' if memory_enabled else 'off'} | traces: {'on' if traces_visible else 'off'} | "
            "Space pause | R reset | M memory | T traces | Q quit"
        )

    t += DT
    frame_count += 1
