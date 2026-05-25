from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# 3D Bacterial Colony Growth on a 3D Surface
# VPython self-contained simulation with rule-based + dynamic AI
# ------------------------------------------------------------

scene = canvas(
    title="3D Bacterial Colony Growth - Prevalent Chemical Signaling",
    width=1200,
    height=780,
    background=vector(0.985, 0.965, 1.0)
)
scene.forward = vector(-0.45, -0.52, -0.72)
scene.camera.pos = vector(8, 9, 12)
scene.camera.axis = vector(-8, -8, -12)
scene.ambient = vector(0.76, 0.70, 0.82)

distant_light(direction=vector(-0.4, -0.8, -0.5), color=vector(1.0, 0.88, 0.80))
distant_light(direction=vector(0.6, -0.4, 0.5), color=vector(0.62, 0.78, 0.95))

scene.caption = """
Controls:
  A: toggle AI    SPACE/P: pause/resume    R: reset    M: cycle AI mode    B: wrap/bounce boundary
  W/S/A/D or arrow keys: move controller cursor
  N: seed bacterium at cursor    F: spill nutrients    V: mark slime    X: scrape/clear
  C: attach nearby bacteria      U: detach nearby bacteria      O: orbit pulse
  G: release chemical signal     +/-: speed up / slow down
"""

# -----------------------------
# Simulation constants
# -----------------------------

PLANE_SIZE = 19.0
HALF = PLANE_SIZE / 2
GRID = 28
CELL = PLANE_SIZE / GRID

BACTERIA_Y = 0.16
MAX_BACTERIA = 145
START_BACTERIA = 10

BASE_SPEED = 0.62
BACTERIUM_LENGTH = 0.68
BACTERIUM_RADIUS = 0.095

NUTRIENT_DIFFUSION = 0.032
SLIME_DIFFUSION = 0.026
SLIME_DECAY = 0.0045
NUTRIENT_REGEN = 0.0016

CHEM_DIFFUSION = 0.092
CHEM_DECAY = 0.010
CHEM_SIGNAL_RADIUS = 2.45
SIGNAL_PULSE_LIMIT = 105
AUTO_SIGNAL_INTERVAL = 2.8
AUTO_SIGNAL_POP_THRESHOLD = 12
SIGNAL_SECRETION_RATE = 0.018

TRAIL_LIMIT = 520
PARTICLE_LIMIT = 250

SIM_SPEED = 1.0
paused = False
boundary_mode = "wrap"
sim_time = 0.0
frame_count = 0

# -----------------------------
# Visual base surface
# -----------------------------

base_plane = box(
    pos=vector(0, -0.025, 0),
    size=vector(PLANE_SIZE + 1.4, 0.05, PLANE_SIZE + 1.4),
    color=vector(0.94, 0.91, 0.98),
    shininess=0.15
)

border_objs = [
    box(pos=vector(0, 0.055, HALF + 0.33), size=vector(PLANE_SIZE + 0.7, 0.1, 0.12), color=vector(0.72, 0.66, 0.86)),
    box(pos=vector(0, 0.055, -HALF - 0.33), size=vector(PLANE_SIZE + 0.7, 0.1, 0.12), color=vector(0.72, 0.66, 0.86)),
    box(pos=vector(HALF + 0.33, 0.055, 0), size=vector(0.12, 0.1, PLANE_SIZE + 0.7), color=vector(0.72, 0.66, 0.86)),
    box(pos=vector(-HALF - 0.33, 0.055, 0), size=vector(0.12, 0.1, PLANE_SIZE + 0.7), color=vector(0.72, 0.66, 0.86)),
]

# -----------------------------
# Fields and global containers
# -----------------------------

N = [[0.0 for _ in range(GRID)] for _ in range(GRID)]  # nutrients
S = [[0.0 for _ in range(GRID)] for _ in range(GRID)]  # slime / secreted matrix
C = [[0.0 for _ in range(GRID)] for _ in range(GRID)]  # chemical signal field

chemical_behavior = "SLOW"
auto_signal_timer = 1.2

tiles = []
bacteria = []
trails = []
particles = []
signal_pulses = []

stats_label = label(
    pos=vector(-HALF - 0.35, 3.05, -HALF - 0.35),
    text="",
    height=12,
    color=vector(0.20, 0.14, 0.28),
    box=False,
    opacity=0,
    align="left"
)

mode_label = label(
    pos=vector(HALF + 0.25, 2.6, -HALF - 0.35),
    text="",
    height=12,
    color=vector(0.20, 0.14, 0.28),
    box=False,
    opacity=0,
    align="right"
)


# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def mix_color(a, b, t):
    t = clamp(t)
    return a * (1 - t) + b * t


def flat(v):
    return vector(v.x, 0, v.z)


def mag2(v):
    return v.x * v.x + v.y * v.y + v.z * v.z


def safe_norm(v):
    m = mag(v)
    if m < 1e-8:
        return vector(0, 0, 0)
    return v / m


def angle_wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def angle_diff(a, b):
    return angle_wrap(a - b)


def heading(theta):
    return vector(math.cos(theta), 0, math.sin(theta))


def perpendicular_xz(v):
    return vector(-v.z, 0, v.x)


def in_bounds_pos(p):
    return -HALF <= p.x <= HALF and -HALF <= p.z <= HALF


def grid_index_from_pos(pos):
    i = int((pos.x + HALF) / CELL)
    j = int((pos.z + HALF) / CELL)
    return max(0, min(GRID - 1, i)), max(0, min(GRID - 1, j))


def cell_center(i, j):
    return vector(-HALF + (i + 0.5) * CELL, 0.003, -HALF + (j + 0.5) * CELL)


def sample_field(field, pos):
    i, j = grid_index_from_pos(pos)
    return field[i][j]


def field_gradient(field, pos):
    eps = CELL * 0.9
    px = vector(eps, 0, 0)
    pz = vector(0, 0, eps)
    gx = sample_field(field, pos + px) - sample_field(field, pos - px)
    gz = sample_field(field, pos + pz) - sample_field(field, pos - pz)
    return vector(gx, 0, gz)


def add_to_field(field, pos, amount, radius=1.0, cap=1.4):
    cx, cz = grid_index_from_pos(pos)
    cr = max(1, int(radius / CELL) + 1)
    for i in range(max(0, cx - cr), min(GRID, cx + cr + 1)):
        for j in range(max(0, cz - cr), min(GRID, cz + cr + 1)):
            cp = cell_center(i, j)
            d = mag(vector(cp.x - pos.x, 0, cp.z - pos.z))
            if d <= radius:
                w = (1 - d / radius) ** 2
                field[i][j] = clamp(field[i][j] + amount * w, 0.0, cap)


def consume_nutrient(pos, amount, radius=0.52):
    cx, cz = grid_index_from_pos(pos)
    cr = max(1, int(radius / CELL) + 1)
    total = 0.0
    for i in range(max(0, cx - cr), min(GRID, cx + cr + 1)):
        for j in range(max(0, cz - cr), min(GRID, cz + cr + 1)):
            cp = cell_center(i, j)
            d = mag(vector(cp.x - pos.x, 0, cp.z - pos.z))
            if d <= radius:
                w = (1 - d / radius) ** 2
                take = min(N[i][j], amount * w)
                N[i][j] -= take
                total += take
    return total


def hide_object(obj):
    try:
        obj.visible = False
    except Exception:
        pass


# -----------------------------
# Environment initialization
# -----------------------------

def initialize_fields():
    global N, S, C
    rich_centers = []
    for _ in range(5):
        rich_centers.append(vector(random.uniform(-HALF * 0.75, HALF * 0.75), 0, random.uniform(-HALF * 0.75, HALF * 0.75)))

    for i in range(GRID):
        for j in range(GRID):
            cp = cell_center(i, j)
            n = 0.54 + random.random() * 0.12
            for c in rich_centers:
                d = mag(vector(cp.x - c.x, 0, cp.z - c.z))
                n += 0.34 * math.exp(-(d * d) / 9.5)
            center_d = mag(vector(cp.x, 0, cp.z))
            n += 0.16 * math.exp(-(center_d * center_d) / 20.0)
            N[i][j] = clamp(n, 0.0, 1.0)
            S[i][j] = 0.0
            C[i][j] = 0.0


def create_tiles():
    global tiles
    for i in range(GRID):
        row = []
        for j in range(GRID):
            cp = cell_center(i, j)
            tile = box(
                pos=vector(cp.x, 0.002, cp.z),
                size=vector(CELL * 0.965, 0.018, CELL * 0.965),
                color=vector(0.92, 0.86, 1.0),
                opacity=0.93,
                shininess=0.08
            )
            row.append(tile)
        tiles.append(row)


def update_tile_colors(force=False):
    if not force and frame_count % 4 != 0:
        return
    rich_col = vector(0.98, 0.76, 0.36)
    mid_col = vector(0.80, 0.86, 1.0)
    poor_col = vector(0.62, 0.50, 0.76)
    slime_col = vector(0.18, 0.88, 0.82)
    signal_col = chemical_behavior_color()

    for i in range(GRID):
        for j in range(GRID):
            n = clamp(N[i][j])
            s = clamp(S[i][j])
            chem = clamp(C[i][j])
            if n > 0.48:
                base = mix_color(mid_col, rich_col, (n - 0.48) / 0.52)
            else:
                base = mix_color(poor_col, mid_col, n / 0.48)

            slimed = mix_color(base, slime_col, clamp(s * 0.62))
            signaled = mix_color(slimed, signal_col, clamp(chem * 1.08))
            tiles[i][j].color = signaled
            tiles[i][j].opacity = 0.88 + 0.08 * clamp(n) + 0.06 * chem


def diffuse_fields(dt):
    global N, S, C
    newN = [[N[i][j] for j in range(GRID)] for i in range(GRID)]
    newS = [[S[i][j] for j in range(GRID)] for i in range(GRID)]
    newC = [[C[i][j] for j in range(GRID)] for i in range(GRID)]

    for i in range(GRID):
        for j in range(GRID):
            totalN = N[i][j]
            totalS = S[i][j]
            totalC = C[i][j]
            count = 1
            if i > 0:
                totalN += N[i - 1][j]
                totalS += S[i - 1][j]
                totalC += C[i - 1][j]
                count += 1
            if i < GRID - 1:
                totalN += N[i + 1][j]
                totalS += S[i + 1][j]
                totalC += C[i + 1][j]
                count += 1
            if j > 0:
                totalN += N[i][j - 1]
                totalS += S[i][j - 1]
                totalC += C[i][j - 1]
                count += 1
            if j < GRID - 1:
                totalN += N[i][j + 1]
                totalS += S[i][j + 1]
                totalC += C[i][j + 1]
                count += 1

            avgN = totalN / count
            avgS = totalS / count
            avgC = totalC / count
            newN[i][j] = clamp(N[i][j] + (avgN - N[i][j]) * NUTRIENT_DIFFUSION * dt * 8 + NUTRIENT_REGEN * dt, 0.0, 1.0)
            newS[i][j] = clamp(S[i][j] + (avgS - S[i][j]) * SLIME_DIFFUSION * dt * 8 - SLIME_DECAY * dt, 0.0, 1.35)
            newC[i][j] = clamp(C[i][j] + (avgC - C[i][j]) * CHEM_DIFFUSION * dt * 8 - CHEM_DECAY * dt, 0.0, 1.0)

    N = newN
    S = newS
    C = newC


# -----------------------------
# Particles and trails
# -----------------------------

def add_particle(pos, color_value, radius=0.045, life=1.0, vel=None, opacity=0.45):
    if len(particles) >= PARTICLE_LIMIT:
        old = particles.pop(0)
        hide_object(old["obj"])
    if vel is None:
        vel = vector(random.uniform(-0.06, 0.06), random.uniform(0.025, 0.15), random.uniform(-0.06, 0.06))
    obj = sphere(
        pos=pos,
        radius=radius,
        color=color_value,
        opacity=opacity,
        shininess=0.2
    )
    particles.append({"obj": obj, "vel": vel, "life": life, "maxlife": life})


def update_particles(dt):
    alive = []
    for p in particles:
        p["life"] -= dt
        if p["life"] <= 0:
            hide_object(p["obj"])
            continue
        p["obj"].pos += p["vel"] * dt
        p["vel"] += vector(0, -0.05, 0) * dt
        try:
            p["obj"].opacity = max(0, 0.55 * p["life"] / p["maxlife"])
        except Exception:
            pass
        alive.append(p)
    particles[:] = alive


def release_chemical_signal(pos, radius=CHEM_SIGNAL_RADIUS, amount=0.82, behavior=None, particles_on=True):
    """Add a visible chemical pulse that diffuses through slime and changes cell behavior."""
    global chemical_behavior
    if behavior is not None:
        chemical_behavior = behavior
    add_to_field(C, pos, amount, radius=radius, cap=1.0)

    if len(signal_pulses) >= SIGNAL_PULSE_LIMIT:
        old = signal_pulses.pop(0)
        hide_object(old["obj"])

    pulse_col = chemical_behavior_color()
    pulse = ring(
        pos=vector(pos.x, 0.065, pos.z),
        axis=vector(0, 1, 0),
        radius=0.18,
        thickness=0.018,
        color=pulse_col,
        opacity=0.52
    )
    signal_pulses.append({"obj": pulse, "life": 3.0, "maxlife": 3.0, "maxradius": radius * 1.72})

    if particles_on:
        for _ in range(18):
            a = random.uniform(0, math.tau)
            r = random.uniform(0.05, radius * 0.45)
            rp = pos + vector(math.cos(a) * r, 0.14, math.sin(a) * r)
            vel = vector(math.cos(a), 0.12, math.sin(a)) * random.uniform(0.06, 0.22)
            add_particle(rp, pulse_col, radius=random.uniform(0.022, 0.052), life=random.uniform(0.75, 1.65), vel=vel, opacity=0.50)


def update_signal_pulses(dt):
    alive = []
    for pulse in signal_pulses:
        pulse["life"] -= dt
        if pulse["life"] <= 0:
            hide_object(pulse["obj"])
            continue
        age = 1.0 - pulse["life"] / pulse["maxlife"]
        pulse["obj"].radius = 0.18 + pulse["maxradius"] * age
        try:
            pulse["obj"].opacity = max(0.03, 0.52 * pulse["life"] / pulse["maxlife"])
            pulse["obj"].thickness = max(0.006, 0.018 * pulse["life"] / pulse["maxlife"])
        except Exception:
            pass
        alive.append(pulse)
    signal_pulses[:] = alive


def chemical_behavior_color():
    if chemical_behavior == "CLUSTER":
        return vector(1.0, 0.46, 0.72)
    if chemical_behavior == "DISPERSE":
        return vector(0.44, 0.78, 1.0)
    return vector(0.92, 0.40, 1.0)


def add_slime_trail(start, end, strength=0.16):
    if mag(end - start) < 0.035:
        return
    if len(trails) >= TRAIL_LIMIT:
        old = trails.pop(0)
        hide_object(old["obj"])
    c = curve(
        pos=[vector(start.x, 0.034, start.z), vector(end.x, 0.034, end.z)],
        radius=0.012 + 0.008 * strength,
        color=vector(0.20, 0.86, 0.80)
    )
    try:
        c.opacity = 0.12 + 0.14 * strength
    except Exception:
        pass
    trails.append({"obj": c, "life": 20.0 + 18.0 * strength, "maxlife": 20.0 + 18.0 * strength})


def update_trails(dt):
    alive = []
    for tr in trails:
        tr["life"] -= dt
        if tr["life"] <= 0:
            hide_object(tr["obj"])
            continue
        try:
            tr["obj"].opacity = max(0.02, 0.22 * tr["life"] / tr["maxlife"])
        except Exception:
            pass
        alive.append(tr)
    trails[:] = alive


# -----------------------------
# Bacterium object
# -----------------------------

class Bacterium:
    _next_id = 0

    def __init__(self, pos=None, theta=None, energy=1.0, attached=False):
        self.id = Bacterium._next_id
        Bacterium._next_id += 1

        if pos is None:
            pos = vector(random.uniform(-1.3, 1.3), BACTERIA_Y, random.uniform(-1.3, 1.3))
        self.pos = vector(pos.x, BACTERIA_Y, pos.z)
        self.prev_pos = vector(self.pos.x, self.pos.y, self.pos.z)

        self.theta = theta if theta is not None else random.uniform(0, math.tau)
        self.vel = vector(0, 0, 0)
        self.omega = random.uniform(-0.2, 0.2)

        self.energy = energy
        self.age = 0.0
        self.attached = attached
        self.dead = False
        self.trail_clock = random.random()
        self.replicate_cooldown = random.uniform(2.0, 8.0)
        self.length = BACTERIUM_LENGTH * random.uniform(0.88, 1.12)
        self.radius = BACTERIUM_RADIUS * random.uniform(0.86, 1.12)
        self.lineage_color_bias = random.uniform(-0.06, 0.06)
        self.chemical_response = "NONE"
        self.signal_timer = random.uniform(0.0, 1.0)
        self.signal_strength = 0.0

        axis = heading(self.theta) * self.length
        self.body = cylinder(
            pos=self.pos - axis * 0.5,
            axis=axis,
            radius=self.radius,
            color=vector(1.0, 0.56, 0.72),
            shininess=0.38
        )
        self.cap1 = sphere(
            pos=self.pos - axis * 0.5,
            radius=self.radius,
            color=self.body.color,
            shininess=0.38
        )
        self.cap2 = sphere(
            pos=self.pos + axis * 0.5,
            radius=self.radius,
            color=self.body.color,
            shininess=0.38
        )
        self.halo = sphere(
            pos=self.pos,
            radius=self.radius * 1.8,
            color=vector(0.55, 0.38, 1.0),
            opacity=0.05,
            shininess=0.0
        )

    def forward(self):
        return heading(self.theta)

    def apply_force(self, f):
        self.vel += flat(f)

    def rotate_toward(self, target_theta, strength, dt):
        self.omega += angle_diff(target_theta, self.theta) * strength * dt

    def set_attached(self, value=True):
        self.attached = value
        if value:
            self.vel *= 0.18
            self.omega *= 0.25

    def kill(self):
        self.dead = True
        self.body.visible = False
        self.cap1.visible = False
        self.cap2.visible = False
        self.halo.visible = False

    def update_visual(self):
        axis = heading(self.theta) * self.length
        self.body.pos = self.pos - axis * 0.5
        self.body.axis = axis
        self.cap1.pos = self.pos - axis * 0.5
        self.cap2.pos = self.pos + axis * 0.5
        self.halo.pos = self.pos

        local_n = sample_field(N, self.pos)
        depleted_tint = mix_color(vector(0.44, 0.34, 0.70), vector(1.0, 0.62, 0.34), clamp(local_n))
        energy_tint = mix_color(vector(0.44, 0.78, 0.90), vector(1.0, 0.50, 0.74), clamp(self.energy / 1.8))
        c = mix_color(depleted_tint, energy_tint, 0.55)
        c += vector(self.lineage_color_bias, -self.lineage_color_bias * 0.4, self.lineage_color_bias * 0.6)
        if self.signal_strength > 0.06:
            c = mix_color(c, chemical_behavior_color(), clamp(self.signal_strength * 0.55))
            self.halo.opacity = max(self.halo.opacity, 0.07 + 0.12 * clamp(self.signal_strength))
            self.halo.color = chemical_behavior_color()
        else:
            self.halo.color = vector(0.55, 0.38, 1.0)
        if self.attached:
            c = mix_color(c, vector(0.18, 0.88, 0.82), 0.30)
            self.halo.opacity = 0.12
            self.halo.radius = self.radius * (2.15 + 0.25 * math.sin(sim_time * 2.0 + self.id))
        else:
            self.halo.opacity = 0.045
            self.halo.radius = self.radius * 1.75

        self.body.color = c
        self.cap1.color = c
        self.cap2.color = c

    def handle_boundary(self):
        global boundary_mode
        if boundary_mode == "wrap":
            if self.pos.x > HALF:
                self.pos.x = -HALF
            elif self.pos.x < -HALF:
                self.pos.x = HALF
            if self.pos.z > HALF:
                self.pos.z = -HALF
            elif self.pos.z < -HALF:
                self.pos.z = HALF
        else:
            bounced = False
            if self.pos.x > HALF:
                self.pos.x = HALF
                self.vel.x *= -0.65
                self.theta = math.pi - self.theta
                bounced = True
            elif self.pos.x < -HALF:
                self.pos.x = -HALF
                self.vel.x *= -0.65
                self.theta = math.pi - self.theta
                bounced = True
            if self.pos.z > HALF:
                self.pos.z = HALF
                self.vel.z *= -0.65
                self.theta = -self.theta
                bounced = True
            elif self.pos.z < -HALF:
                self.pos.z = -HALF
                self.vel.z *= -0.65
                self.theta = -self.theta
                bounced = True
            if bounced:
                self.omega += random.uniform(-0.7, 0.7)

    def update(self, dt):
        if self.dead:
            return

        self.age += dt
        self.replicate_cooldown -= dt
        self.prev_pos = vector(self.pos.x, self.pos.y, self.pos.z)

        local_n = sample_field(N, self.pos)
        local_s = sample_field(S, self.pos)
        local_c = sample_field(C, self.pos)
        self.signal_strength = local_c

        grad_n = field_gradient(N, self.pos)
        grad_s = field_gradient(S, self.pos)
        grad_c = field_gradient(C, self.pos)

        self.signal_timer -= dt
        if local_c > 0.045 and self.signal_timer <= 0:
            if chemical_behavior == "CLUSTER":
                self.chemical_response = "CLUSTER"
            elif chemical_behavior == "DISPERSE":
                self.chemical_response = "DISPERSE"
            else:
                self.chemical_response = random.choice(["SLOW", "CLUSTER", "DISPERSE"]) if local_c > 0.28 else random.choice(["SLOW", "CLUSTER"])
            self.signal_timer = random.uniform(0.55, 1.35)
        elif local_c <= 0.025 and self.signal_timer <= 0:
            self.chemical_response = "NONE"
            self.signal_timer = random.uniform(0.7, 1.4)

        desired = vector(0, 0, 0)
        if mag(grad_n) > 0.01:
            desired += safe_norm(grad_n) * (0.95 if local_n < 0.72 else 0.33)
        if mag(grad_s) > 0.01:
            desired += safe_norm(grad_s) * (0.20 + 0.60 * clamp(1.0 - local_n))

        if local_c > 0.035:
            center_vec = flat(colony_center() - self.pos)
            if self.chemical_response == "CLUSTER" and mag(center_vec) > 0.05:
                desired += safe_norm(center_vec) * (0.78 + 1.65 * local_c)
                add_to_field(S, self.pos, 0.018 * dt, radius=0.55, cap=1.35)
            elif self.chemical_response == "DISPERSE":
                away = -safe_norm(grad_c) if mag(grad_c) > 0.01 else safe_norm(flat(self.pos - colony_center()))
                desired += away * (0.92 + 1.85 * local_c)
                self.vel += away * 0.28 * local_c * dt
            elif self.chemical_response == "SLOW":
                self.vel *= max(0.0, 1.0 - 1.8 * local_c * dt)
                self.omega *= max(0.0, 1.0 - 1.2 * local_c * dt)

        if random.random() < 0.11:
            self.omega += random.uniform(-0.8, 0.8) * dt

        if mag(desired) > 0.001:
            target_theta = math.atan2(desired.z, desired.x)
            self.rotate_toward(target_theta, 2.8, dt)

        self.omega += random.uniform(-0.33, 0.33) * dt
        self.omega *= 0.965

        drag = 0.74 + 0.22 * clamp(local_s)
        self.vel *= max(0.0, 1.0 - drag * dt)

        if self.attached:
            chem_slow = 0.34 if (self.chemical_response == "SLOW" and local_c > 0.035) else 1.0
            chem_boost = 1.28 if (self.chemical_response == "DISPERSE" and local_c > 0.035) else 1.0
            crawl = BASE_SPEED * 0.045 * (0.6 + local_n) * chem_slow * chem_boost
            self.theta += self.omega * dt * 0.34
            self.pos += self.forward() * crawl * dt + self.vel * dt * 0.5
            slime_rate = 0.055
            consume_rate = 0.010
            if local_n > 0.70 and random.random() < 0.018 * dt:
                self.set_attached(False)
        else:
            chem_slow = 0.32 if (self.chemical_response == "SLOW" and local_c > 0.035) else 1.0
            chem_boost = 1.45 if (self.chemical_response == "DISPERSE" and local_c > 0.035) else 1.0
            cluster_slow = 0.72 if (self.chemical_response == "CLUSTER" and local_c > 0.12) else 1.0
            speed = BASE_SPEED * (0.25 + 0.92 * local_n) * (1.0 - 0.36 * clamp(local_s)) * chem_slow * chem_boost * cluster_slow
            self.theta += self.omega * dt
            self.pos += self.forward() * speed * dt + self.vel * dt
            slime_rate = 0.030 + 0.030 * clamp(1.0 - local_n)
            consume_rate = 0.020 + 0.030 * clamp(self.energy)

            if local_s > 0.72 and local_n < 0.47 and random.random() < 0.040 * dt:
                self.set_attached(True)
            if self.chemical_response == "CLUSTER" and local_c > 0.24 and random.random() < 0.028 * dt:
                self.set_attached(True)

        consumed = consume_nutrient(self.pos, consume_rate * dt, radius=0.58)
        add_to_field(S, self.pos, slime_rate * dt, radius=0.68, cap=1.35)

        self.energy += consumed * 14.0
        self.energy -= (0.010 + 0.009 * (0 if self.attached else 1)) * dt
        self.energy = clamp(self.energy, 0.05, 2.6)

        self.trail_clock -= dt
        moved = mag(self.pos - self.prev_pos)
        if self.trail_clock <= 0 and moved > 0.025:
            add_slime_trail(self.prev_pos, self.pos, strength=0.22 + local_s * 0.3)
            self.trail_clock = random.uniform(0.34, 0.80)

        self.pos.y = BACTERIA_Y
        self.handle_boundary()

        if self.energy > 1.55 and self.replicate_cooldown <= 0 and len(bacteria) < MAX_BACTERIA:
            if random.random() < (0.35 + 0.55 * local_n) * dt:
                self.replicate()

        if self.energy <= 0.06 and random.random() < 0.015 * dt:
            add_to_field(S, self.pos, 0.12, radius=0.62, cap=1.35)
            self.kill()

        self.update_visual()

    def replicate(self):
        self.replicate_cooldown = random.uniform(7.5, 14.0)
        child_theta = self.theta + random.uniform(-0.55, 0.55)
        side = perpendicular_xz(self.forward()) * random.choice([-1, 1])
        child_pos = self.pos + side * random.uniform(0.18, 0.28) + self.forward() * random.uniform(-0.12, 0.12)
        child_pos.y = BACTERIA_Y

        self.energy *= 0.54
        child = add_bacterium(pos=child_pos, theta=child_theta, energy=self.energy * random.uniform(0.9, 1.08), attached=self.attached and random.random() < 0.55)
        if child:
            child.vel = side * random.uniform(0.03, 0.14)
            child.omega = random.uniform(-0.35, 0.35)
            child.lineage_color_bias = self.lineage_color_bias + random.uniform(-0.015, 0.015)

        add_to_field(S, self.pos, 0.08, radius=0.78, cap=1.35)
        for _ in range(3):
            add_particle(
                self.pos + vector(random.uniform(-0.12, 0.12), 0.12, random.uniform(-0.12, 0.12)),
                vector(1.0, 0.72, 0.36),
                radius=0.035,
                life=random.uniform(0.5, 0.9),
                opacity=0.42
            )


def add_bacterium(pos=None, theta=None, energy=1.0, attached=False):
    if len(bacteria) >= MAX_BACTERIA:
        return None
    b = Bacterium(pos=pos, theta=theta, energy=energy, attached=attached)
    bacteria.append(b)
    return b


def remove_dead_bacteria():
    alive = []
    for b in bacteria:
        if b.dead:
            continue
        alive.append(b)
    bacteria[:] = alive


# -----------------------------
# Colony interactions
# -----------------------------

def process_bacterial_interactions(dt):
    n = len(bacteria)
    if n <= 1:
        return

    for i in range(n):
        a = bacteria[i]
        if a.dead:
            continue
        for j in range(i + 1, n):
            b = bacteria[j]
            if b.dead:
                continue

            d = flat(b.pos - a.pos)
            dist = mag(d)
            if dist < 1e-5:
                d = vector(random.uniform(-1, 1), 0, random.uniform(-1, 1))
                dist = mag(d)
            nd = d / dist

            neighbor_range = 1.18
            if dist < neighbor_range:
                local_s = max(sample_field(S, a.pos), sample_field(S, b.pos))
                closeness = 1.0 - dist / neighbor_range

                # Clustering/cohesion inside slime matrix
                if dist > 0.40:
                    cohesion = nd * (0.025 + 0.045 * local_s) * closeness * dt
                    a.apply_force(cohesion)
                    b.apply_force(-cohesion)

                # Alignment / organizing into patches
                diff = angle_diff(b.theta, a.theta)
                align_strength = (0.18 + 0.38 * local_s) * closeness * dt
                a.omega += diff * align_strength
                b.omega -= diff * align_strength

                # Contact collision
                min_dist = 0.28 + 0.09 * (a.radius + b.radius) / BACTERIUM_RADIUS
                if dist < min_dist:
                    push = nd * (min_dist - dist) * 2.1
                    a.apply_force(-push * dt)
                    b.apply_force(push * dt)
                    a.omega += random.uniform(-0.18, 0.18)
                    b.omega += random.uniform(-0.18, 0.18)

                    # Tiny transfer/equalization through close slime contact
                    if local_s > 0.35:
                        transfer = (a.energy - b.energy) * 0.006 * dt
                        a.energy -= transfer
                        b.energy += transfer


# -----------------------------
# Human/AI actions
# -----------------------------

def spill_nutrients(pos, radius=1.6, amount=0.55, particles_on=True):
    add_to_field(N, pos, amount, radius=radius, cap=1.0)
    if particles_on:
        for _ in range(12):
            rp = pos + vector(random.uniform(-radius * 0.45, radius * 0.45), 0.12, random.uniform(-radius * 0.45, radius * 0.45))
            add_particle(rp, vector(1.0, 0.70, 0.32), radius=random.uniform(0.025, 0.055), life=random.uniform(0.55, 1.25), opacity=0.46)


def spill_slime(pos, radius=1.25, amount=0.42, particles_on=True):
    add_to_field(S, pos, amount, radius=radius, cap=1.35)
    if particles_on:
        for _ in range(8):
            rp = pos + vector(random.uniform(-radius * 0.4, radius * 0.4), 0.08, random.uniform(-radius * 0.4, radius * 0.4))
            add_particle(rp, vector(0.20, 0.86, 0.80), radius=random.uniform(0.025, 0.05), life=random.uniform(0.65, 1.35), opacity=0.36)


def scrape_area(pos, radius=1.25, harshness=0.65):
    cx, cz = grid_index_from_pos(pos)
    cr = max(1, int(radius / CELL) + 1)
    for i in range(max(0, cx - cr), min(GRID, cx + cr + 1)):
        for j in range(max(0, cz - cr), min(GRID, cz + cr + 1)):
            cp = cell_center(i, j)
            d = mag(vector(cp.x - pos.x, 0, cp.z - pos.z))
            if d <= radius:
                w = (1 - d / radius) ** 1.2
                S[i][j] = max(0, S[i][j] - harshness * w)
                N[i][j] = clamp(N[i][j] + 0.08 * w, 0.0, 1.0)

    for b in list(bacteria):
        d = mag(flat(b.pos - pos))
        if d < radius:
            b.set_attached(False)
            b.vel += safe_norm(flat(b.pos - pos) + vector(random.uniform(-0.2, 0.2), 0, random.uniform(-0.2, 0.2))) * harshness * 0.5
            if d < radius * 0.42 and random.random() < 0.09 * harshness:
                b.kill()

    for _ in range(14):
        rp = pos + vector(random.uniform(-radius * 0.45, radius * 0.45), 0.09, random.uniform(-radius * 0.45, radius * 0.45))
        add_particle(rp, vector(0.96, 0.62, 0.48), radius=random.uniform(0.018, 0.04), life=random.uniform(0.35, 0.85), opacity=0.35)


def attach_near(pos, radius=1.4, attach=True):
    for b in bacteria:
        d = mag(flat(b.pos - pos))
        if d < radius:
            if attach:
                b.set_attached(True)
                add_to_field(S, b.pos, 0.05, radius=0.5, cap=1.35)
            else:
                b.set_attached(False)
                b.vel += safe_norm(flat(b.pos - pos)) * random.uniform(0.04, 0.15)


def chemical_signal_burst(pos, behavior=None, radius=2.0, amount=0.78):
    if behavior is None:
        behavior = random.choice(["SLOW", "CLUSTER", "DISPERSE"])
    release_chemical_signal(pos, radius=radius, amount=amount, behavior=behavior, particles_on=True)
    for b in bacteria:
        d = mag(flat(b.pos - pos))
        if d < radius * 1.35:
            w = (1 - d / (radius * 1.35)) ** 1.2
            if behavior == "SLOW":
                b.vel *= max(0.0, 1.0 - 0.55 * w)
                b.omega *= max(0.0, 1.0 - 0.45 * w)
            elif behavior == "CLUSTER":
                b.apply_force(safe_norm(flat(pos - b.pos)) * 0.20 * w)
            elif behavior == "DISPERSE":
                b.apply_force(safe_norm(flat(b.pos - pos)) * 0.30 * w)
                b.set_attached(False)


def auto_signal_from_colony(dt):
    """Make chemical signaling a regular colony behavior instead of a rare AI-only event."""
    global auto_signal_timer
    if not bacteria or len(bacteria) < AUTO_SIGNAL_POP_THRESHOLD:
        return

    # Crowded, slimed, or nutrient-poor cells leak weak signal continuously.
    sample_cells = bacteria if len(bacteria) <= 70 else random.sample(bacteria, 70)
    for b in sample_cells:
        if b.dead:
            continue
        local_n = sample_field(N, b.pos)
        local_s = sample_field(S, b.pos)
        local_c = sample_field(C, b.pos)
        crowd = 0
        for other in bacteria:
            if other is b or other.dead:
                continue
            if mag(flat(other.pos - b.pos)) < 1.05:
                crowd += 1
                if crowd >= 5:
                    break
        if crowd >= 3 or local_s > 0.42 or local_n < 0.36:
            add_to_field(C, b.pos, SIGNAL_SECRETION_RATE * dt * (1.0 + 0.22 * crowd), radius=0.75 + 0.10 * crowd, cap=1.0)
            if local_c > 0.18 and random.random() < 0.09 * dt:
                add_particle(b.pos + vector(0, 0.13, 0), chemical_behavior_color(), radius=0.024, life=0.65, opacity=0.34)

    # Periodic patch-wide broadcast from the densest or most depleted active region.
    auto_signal_timer -= dt
    if auto_signal_timer <= 0:
        c = colony_center()
        target = c
        best_score = -999.0
        for b in random.sample(bacteria, min(len(bacteria), 36)):
            local_n = sample_field(N, b.pos)
            local_s = sample_field(S, b.pos)
            nearby = 0
            for other in bacteria:
                if other is not b and not other.dead and mag(flat(other.pos - b.pos)) < 1.35:
                    nearby += 1
            score = nearby * 0.32 + local_s * 1.6 + (1.0 - local_n) * 1.25 + random.random() * 0.25
            if score > best_score:
                best_score = score
                target = b.pos

        if best_score > 1.2:
            if depleted_fraction() > 0.30:
                behavior = "DISPERSE"
            elif colony_spread(c) > 4.2 and random.random() < 0.55:
                behavior = "CLUSTER"
            else:
                behavior = random.choice(["SLOW", "CLUSTER", "DISPERSE"])
            chemical_signal_burst(target, behavior=behavior, radius=random.uniform(2.2, 3.6), amount=random.uniform(0.74, 1.0))
        auto_signal_timer = random.uniform(1.2, AUTO_SIGNAL_INTERVAL)


def apply_force_near(pos, radius=2.0, inward=0.0, tangent=0.0, randomize=0.0, align_theta=None, attach=None, detach=None):
    for b in bacteria:
        dvec = flat(pos - b.pos)
        d = mag(dvec)
        if d < radius and d > 1e-5:
            w = (1 - d / radius) ** 1.4
            radial = dvec / d
            tang = perpendicular_xz(radial)
            b.apply_force(radial * inward * w + tang * tangent * w)
            if randomize:
                b.apply_force(vector(random.uniform(-1, 1), 0, random.uniform(-1, 1)) * randomize * w)
                b.omega += random.uniform(-1, 1) * randomize * w
            if align_theta is not None:
                b.rotate_toward(align_theta, 5.0 * w, 1.0)
            if attach is True and random.random() < 0.12 * w:
                b.set_attached(True)
            if detach is True and random.random() < 0.12 * w:
                b.set_attached(False)


def orbit_pulse(pos, radius=2.3, strength=0.42):
    apply_force_near(pos, radius=radius, inward=0.03, tangent=strength, randomize=0.02)


# -----------------------------
# State measurements
# -----------------------------

def colony_center():
    if not bacteria:
        return vector(0, BACTERIA_Y, 0)
    c = vector(0, 0, 0)
    for b in bacteria:
        c += b.pos
    c /= len(bacteria)
    c.y = BACTERIA_Y
    return c


def colony_spread(center=None):
    if not bacteria:
        return 0.0
    if center is None:
        center = colony_center()
    total = 0.0
    for b in bacteria:
        total += mag(flat(b.pos - center))
    return total / len(bacteria)


def avg_field(field):
    total = 0.0
    for i in range(GRID):
        for j in range(GRID):
            total += field[i][j]
    return total / (GRID * GRID)


def total_field(field):
    total = 0.0
    for i in range(GRID):
        for j in range(GRID):
            total += field[i][j]
    return total


def active_signal_fraction():
    count = 0
    for i in range(GRID):
        for j in range(GRID):
            if C[i][j] > 0.12:
                count += 1
    return count / (GRID * GRID)


def depleted_fraction():
    count = 0
    for i in range(GRID):
        for j in range(GRID):
            if N[i][j] < 0.24:
                count += 1
    return count / (GRID * GRID)


def richest_cell_pos():
    best = -1
    bestij = (GRID // 2, GRID // 2)
    for i in range(GRID):
        for j in range(GRID):
            score = N[i][j] - 0.12 * S[i][j] + random.random() * 0.01
            if score > best:
                best = score
                bestij = (i, j)
    cp = cell_center(bestij[0], bestij[1])
    return vector(cp.x, BACTERIA_Y, cp.z)


def most_depleted_cell_pos():
    best = 999
    bestij = (GRID // 2, GRID // 2)
    for i in range(GRID):
        for j in range(GRID):
            score = N[i][j] + random.random() * 0.01
            if score < best:
                best = score
                bestij = (i, j)
    cp = cell_center(bestij[0], bestij[1])
    return vector(cp.x, BACTERIA_Y, cp.z)


# -----------------------------
# Expressive AI controller
# -----------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "SEED",
            "FEED",
            "HERD",
            "ORBIT",
            "MARK",
            "ORGANIZE",
            "STIR",
            "SIGNAL",
            "SIGNAL",
            "SCRAPE",
            "REST"
        ]
        self.mode = "SEED"
        self.previous_mode = None
        self.mode_time = 0.0
        self.switch_after = 4.5
        self.cursor_pos = vector(0, BACTERIA_Y, 0)
        self.cursor_target = vector(0, BACTERIA_Y, 0)
        self.phase = random.random() * math.tau
        self.action_timer = 0.0
        self.override_until = 0.0
        self.round = 1
        self.completion_timer = 0.0
        self.loop_delay = 4.0
        self.last_probe_time = 0.0
        self.last_metric = None
        self.stagnation_time = 0.0
        self.manual_note = ""

        self.ring = ring(
            pos=vector(0, 0.09, 0),
            axis=vector(0, 1, 0),
            radius=1.0,
            thickness=0.025,
            color=vector(0.58, 0.46, 1.0),
            opacity=0.65
        )
        self.core = sphere(
            pos=vector(0, 0.22, 0),
            radius=0.11,
            color=vector(0.58, 0.46, 1.0),
            opacity=0.72,
            shininess=0.45
        )
        self.beam = cylinder(
            pos=vector(0, 0.025, 0),
            axis=vector(0, 0.40, 0),
            radius=0.018,
            color=vector(0.58, 0.46, 1.0),
            opacity=0.25
        )

    def override(self, seconds=3.5):
        self.override_until = sim_time + seconds

    def next_mode(self):
        idx = self.modes.index(self.mode)
        self.set_mode(self.modes[(idx + 1) % len(self.modes)], immediate=True)

    def set_mode(self, mode, immediate=False):
        if mode not in self.modes:
            return
        if immediate or mode != self.mode:
            self.previous_mode = self.mode
            self.mode = mode
            self.mode_time = 0.0
            self.action_timer = 0.0
            self.switch_after = random.uniform(5.0, 12.5)
            self.cursor_target = self.choose_interesting_target()

    def mode_color(self):
        colors = {
            "SEED": vector(0.58, 0.46, 1.0),
            "FEED": vector(1.0, 0.70, 0.32),
            "HERD": vector(0.96, 0.44, 0.58),
            "ORBIT": vector(0.44, 0.36, 0.92),
            "MARK": vector(0.18, 0.88, 0.82),
            "ORGANIZE": vector(1.0, 0.42, 0.78),
            "STIR": vector(0.96, 0.52, 0.28),
            "SIGNAL": chemical_behavior_color(),
            "SCRAPE": vector(0.86, 0.28, 0.42),
            "REST": vector(0.74, 0.72, 0.86),
        }
        return colors.get(self.mode, vector(0.58, 0.46, 1.0))

    def read_state(self):
        c = colony_center()
        spread = colony_spread(c)
        pop = len(bacteria)
        avg_n = avg_field(N)
        avg_s = avg_field(S)
        dep = depleted_fraction()
        attached = 0
        responding = 0
        slowed = 0
        clustered = 0
        dispersed = 0
        avg_energy = 0.0
        for b in bacteria:
            avg_energy += b.energy
            if b.attached:
                attached += 1
            if b.chemical_response != "NONE" and b.signal_strength > 0.08:
                responding += 1
                if b.chemical_response == "SLOW":
                    slowed += 1
                elif b.chemical_response == "CLUSTER":
                    clustered += 1
                elif b.chemical_response == "DISPERSE":
                    dispersed += 1
        avg_energy = avg_energy / pop if pop else 0.0

        return {
            "population": pop,
            "max_population": MAX_BACTERIA,
            "center": c,
            "spread": spread,
            "avg_nutrient": avg_n,
            "avg_slime": avg_s,
            "total_slime": total_field(S),
            "avg_chemical": avg_field(C),
            "active_signal_fraction": active_signal_fraction(),
            "depleted_fraction": dep,
            "attached_fraction": attached / pop if pop else 0.0,
            "responding_fraction": responding / pop if pop else 0.0,
            "slowed_count": slowed,
            "clustered_count": clustered,
            "dispersed_count": dispersed,
            "avg_energy": avg_energy,
            "empty": pop == 0,
            "crowded": pop > MAX_BACTERIA * 0.82,
            "nutrient_poor": avg_n < 0.34 or dep > 0.35,
            "high_biofilm": avg_s > 0.34,
        }

    def detect_stagnation_or_completion(self, state, dt):
        if state["empty"]:
            self.stagnation_time += dt * 2.0
            return True

        if sim_time - self.last_probe_time > 4.0:
            metric = (
                state["population"],
                round(state["spread"], 2),
                round(state["avg_nutrient"], 3),
                round(state["avg_slime"], 3),
                round(state["attached_fraction"], 2)
            )
            if self.last_metric is not None:
                dp = abs(metric[0] - self.last_metric[0])
                ds = abs(metric[1] - self.last_metric[1])
                dn = abs(metric[2] - self.last_metric[2])
                dm = abs(metric[3] - self.last_metric[3])
                da = abs(metric[4] - self.last_metric[4])
                if dp < 2 and ds < 0.10 and dn < 0.010 and dm < 0.010 and da < 0.06:
                    self.stagnation_time += 4.0
                else:
                    self.stagnation_time = max(0.0, self.stagnation_time - 3.0)
            self.last_metric = metric
            self.last_probe_time = sim_time

        completed = (
            self.stagnation_time > 26.0 or
            (state["population"] >= MAX_BACTERIA * 0.95 and state["nutrient_poor"]) or
            (state["avg_nutrient"] < 0.20 and state["population"] < 8) or
            (state["spread"] > HALF * 0.86 and state["population"] > MAX_BACTERIA * 0.65)
        )
        return completed

    def choose_interesting_target(self):
        state = self.read_state()
        if state["empty"]:
            return richest_cell_pos()
        if self.mode == "FEED":
            if random.random() < 0.65:
                return most_depleted_cell_pos()
            return state["center"] + vector(random.uniform(-2, 2), 0, random.uniform(-2, 2))
        if self.mode == "SEED":
            return richest_cell_pos()
        if self.mode in ("HERD", "ORGANIZE"):
            return state["center"] + vector(random.uniform(-1.6, 1.6), 0, random.uniform(-1.6, 1.6))
        if self.mode == "SCRAPE":
            return state["center"] + vector(random.uniform(-state["spread"], state["spread"]), 0, random.uniform(-state["spread"], state["spread"]))
        if self.mode == "SIGNAL":
            return state["center"] + vector(random.uniform(-1.8, 1.8), 0, random.uniform(-1.8, 1.8))
        if self.mode in ("STIR", "ORBIT", "MARK"):
            r = max(1.1, state["spread"] + random.uniform(0.4, 2.0))
            a = random.uniform(0, math.tau)
            return state["center"] + vector(math.cos(a) * r, 0, math.sin(a) * r)
        return vector(random.uniform(-HALF * 0.7, HALF * 0.7), BACTERIA_Y, random.uniform(-HALF * 0.7, HALF * 0.7))

    def choose_mode(self, state):
        if state["empty"]:
            return "SEED"

        if self.mode_time < 1.4:
            return self.mode

        if state["nutrient_poor"] and self.mode not in ("FEED", "SEED", "SIGNAL"):
            if random.random() < 0.60:
                return random.choice(["FEED", "SIGNAL"])

        if state["population"] < 15 and self.mode != "SEED":
            if random.random() < 0.55:
                return "SEED"

        if state["crowded"] and self.mode not in ("SCRAPE", "ORGANIZE", "ORBIT"):
            return random.choice(["SCRAPE", "ORGANIZE", "ORBIT", "SIGNAL"])

        if state["spread"] < 2.2 and state["population"] > 22:
            return random.choice(["STIR", "ORBIT", "MARK", "HERD", "SIGNAL"])

        if state["attached_fraction"] > 0.72 and state["avg_nutrient"] > 0.45:
            return random.choice(["STIR", "FEED", "SCRAPE"])

        if self.mode_time > self.switch_after:
            options = [m for m in self.modes if m != self.mode and m != self.previous_mode]
            weights = []
            for m in options:
                w = 1.0
                if m == "FEED":
                    w += 2.2 if state["nutrient_poor"] else 0.2
                elif m == "SEED":
                    w += 2.5 if state["population"] < 25 else 0.0
                elif m == "SCRAPE":
                    w += 1.8 if state["crowded"] or state["high_biofilm"] else 0.1
                elif m == "MARK":
                    w += 1.1
                elif m == "SIGNAL":
                    w += 4.2 if state["population"] > 12 else 1.2
                elif m == "ORGANIZE":
                    w += 1.0 if state["population"] > 20 else 0.1
                elif m == "REST":
                    w += 0.35
                weights.append(w)
            total = sum(weights)
            r = random.random() * total
            acc = 0.0
            for m, w in zip(options, weights):
                acc += w
                if r <= acc:
                    return m
        return self.mode

    def move_cursor(self, dt):
        self.phase += dt
        self.cursor_target.x = clamp(self.cursor_target.x, -HALF + 0.4, HALF - 0.4)
        self.cursor_target.z = clamp(self.cursor_target.z, -HALF + 0.4, HALF - 0.4)
        self.cursor_target.y = BACTERIA_Y
        self.cursor_pos += (self.cursor_target - self.cursor_pos) * clamp(1.9 * dt, 0, 1)

        dip = 0.18 + 0.06 * math.sin(self.phase * 3.0)
        if self.mode in ("FEED", "MARK", "SCRAPE"):
            dip = 0.08 + 0.04 * math.sin(self.phase * 5.0)
        if sim_time < self.override_until:
            dip = 0.24 + 0.04 * math.sin(self.phase * 8.0)

        col = self.mode_color()
        self.ring.pos = vector(self.cursor_pos.x, 0.075, self.cursor_pos.z)
        self.ring.radius = 0.85 + 0.18 * math.sin(self.phase * 2.2)
        self.ring.color = col
        self.core.pos = vector(self.cursor_pos.x, dip + 0.08, self.cursor_pos.z)
        self.core.color = col
        self.beam.pos = vector(self.cursor_pos.x, 0.025, self.cursor_pos.z)
        self.beam.axis = vector(0, max(0.05, dip + 0.08), 0)
        self.beam.color = col

    def perform_mode_action(self, state, dt):
        self.action_timer -= dt

        if self.mode == "SEED":
            if self.action_timer <= 0:
                self.cursor_target = richest_cell_pos() + vector(random.uniform(-0.6, 0.6), 0, random.uniform(-0.6, 0.6))
                if len(bacteria) < MAX_BACTERIA:
                    add_bacterium(
                        pos=self.cursor_pos + vector(random.uniform(-0.35, 0.35), 0, random.uniform(-0.35, 0.35)),
                        theta=random.uniform(0, math.tau),
                        energy=random.uniform(0.85, 1.25),
                        attached=random.random() < 0.16
                    )
                    spill_slime(self.cursor_pos, radius=0.6, amount=0.05, particles_on=False)
                    add_particle(self.cursor_pos + vector(0, 0.18, 0), vector(0.58, 0.46, 1.0), radius=0.06, life=0.9, opacity=0.55)
                self.action_timer = random.uniform(0.8, 1.7)

        elif self.mode == "FEED":
            if self.action_timer <= 0:
                self.cursor_target = most_depleted_cell_pos() if random.random() < 0.72 else state["center"] + vector(random.uniform(-3, 3), 0, random.uniform(-3, 3))
                spill_nutrients(self.cursor_pos, radius=random.uniform(1.1, 2.0), amount=random.uniform(0.22, 0.48), particles_on=True)
                self.action_timer = random.uniform(0.9, 1.8)

        elif self.mode == "HERD":
            if self.action_timer <= 0:
                a = random.uniform(0, math.tau)
                edge = state["center"] + vector(math.cos(a), 0, math.sin(a)) * max(1.3, state["spread"] + 1.2)
                self.cursor_target = edge
                self.action_timer = random.uniform(1.5, 3.0)
            apply_force_near(self.cursor_pos, radius=2.6, inward=0.18, tangent=0.03, randomize=0.005)

        elif self.mode == "ORBIT":
            c = state["center"]
            radius = max(1.3, state["spread"] + 1.2)
            a = self.phase * 0.65
            self.cursor_target = c + vector(math.cos(a) * radius, 0, math.sin(a) * radius)
            apply_force_near(c, radius=max(2.2, state["spread"] + 2.2), inward=0.00, tangent=0.13, randomize=0.015)
            if self.action_timer <= 0:
                orbit_pulse(self.cursor_pos, radius=2.0, strength=0.22)
                spill_slime(self.cursor_pos, radius=0.8, amount=0.035, particles_on=False)
                self.action_timer = random.uniform(0.55, 1.25)

        elif self.mode == "MARK":
            c = state["center"]
            r = max(1.0, 1.0 + 0.17 * self.mode_time + 0.35 * math.sin(self.phase))
            a = self.phase * 1.25
            self.cursor_target = c + vector(math.cos(a) * r, 0, math.sin(a) * r)
            if self.action_timer <= 0:
                last = vector(self.cursor_pos.x - math.cos(a) * 0.15, BACTERIA_Y, self.cursor_pos.z - math.sin(a) * 0.15)
                add_slime_trail(last, self.cursor_pos, strength=0.55)
                spill_slime(self.cursor_pos, radius=0.72, amount=0.08, particles_on=True)
                self.action_timer = random.uniform(0.24, 0.48)

        elif self.mode == "ORGANIZE":
            if self.action_timer <= 0:
                self.cursor_target = state["center"] + vector(random.uniform(-1.3, 1.3), 0, random.uniform(-1.3, 1.3))
                self.action_timer = random.uniform(1.6, 3.0)
            align = math.atan2((self.cursor_pos - state["center"]).z, (self.cursor_pos - state["center"]).x) + math.pi * 0.5
            apply_force_near(self.cursor_pos, radius=2.4, inward=0.06, tangent=0.0, randomize=0.0, align_theta=align, attach=True)
            spill_slime(self.cursor_pos, radius=0.55, amount=0.012, particles_on=False)

        elif self.mode == "STIR":
            if self.action_timer <= 0:
                self.cursor_target = vector(random.uniform(-HALF * 0.82, HALF * 0.82), BACTERIA_Y, random.uniform(-HALF * 0.82, HALF * 0.82))
                self.action_timer = random.uniform(0.75, 1.6)
            apply_force_near(self.cursor_pos, radius=2.0, inward=random.uniform(-0.03, 0.08), tangent=0.18, randomize=0.075, detach=True)

        elif self.mode == "SIGNAL":
            if self.action_timer <= 0:
                self.cursor_target = state["center"] + vector(random.uniform(-max(1.2, state["spread"]), max(1.2, state["spread"])), 0, random.uniform(-max(1.2, state["spread"]), max(1.2, state["spread"])))
                if state["crowded"] or state["attached_fraction"] > 0.55:
                    behavior = random.choice(["DISPERSE", "SLOW", "CLUSTER"])
                elif state["spread"] > 4.0:
                    behavior = random.choice(["CLUSTER", "SLOW"])
                else:
                    behavior = random.choice(["SLOW", "CLUSTER", "DISPERSE"])
                chemical_signal_burst(self.cursor_pos, behavior=behavior, radius=random.uniform(2.4, 3.8), amount=random.uniform(0.78, 1.0))
                self.action_timer = random.uniform(0.45, 1.05)

        elif self.mode == "SCRAPE":
            if self.action_timer <= 0:
                self.cursor_target = state["center"] + vector(random.uniform(-max(1, state["spread"]), max(1, state["spread"])), 0, random.uniform(-max(1, state["spread"]), max(1, state["spread"])))
                scrape_area(self.cursor_pos, radius=random.uniform(0.9, 1.5), harshness=random.uniform(0.22, 0.55))
                self.action_timer = random.uniform(1.1, 2.6)

        elif self.mode == "REST":
            if self.action_timer <= 0:
                self.cursor_target = state["center"] + vector(random.uniform(-2.2, 2.2), 0, random.uniform(-2.2, 2.2))
                if random.random() < 0.25:
                    spill_slime(self.cursor_pos, radius=0.45, amount=0.025, particles_on=False)
                self.action_timer = random.uniform(2.0, 4.2)

    def update(self, dt):
        global boundary_mode
        self.move_cursor(dt)

        if not self.enabled:
            return

        state = self.read_state()
        completed = self.detect_stagnation_or_completion(state, dt)

        if completed:
            self.completion_timer += dt
            self.set_mode("REST")
            if self.completion_timer > self.loop_delay:
                reset_simulation(seed_count=random.randint(7, 13), from_ai=True)
                return
        else:
            self.completion_timer = 0.0

        if sim_time < self.override_until:
            return

        self.mode_time += dt
        desired_mode = self.choose_mode(state)
        if desired_mode != self.mode:
            self.set_mode(desired_mode)

        if random.random() < 0.0009:
            boundary_mode = "bounce" if boundary_mode == "wrap" else "wrap"

        self.perform_mode_action(state, dt)


# -----------------------------
# Reset and labels
# -----------------------------

def reset_simulation(seed_count=START_BACTERIA, from_ai=False):
    global bacteria, trails, particles, signal_pulses, sim_time, frame_count, chemical_behavior, auto_signal_timer

    for b in bacteria:
        b.kill()
    bacteria[:] = []

    for tr in trails:
        hide_object(tr["obj"])
    trails[:] = []

    for p in particles:
        hide_object(p["obj"])
    particles[:] = []

    for pulse in signal_pulses:
        hide_object(pulse["obj"])
    signal_pulses[:] = []
    chemical_behavior = "SLOW"
    auto_signal_timer = 0.8

    initialize_fields()
    update_tile_colors(force=True)

    for _ in range(seed_count):
        p = richest_cell_pos() + vector(random.uniform(-1.1, 1.1), 0, random.uniform(-1.1, 1.1))
        add_bacterium(pos=p, theta=random.uniform(0, math.tau), energy=random.uniform(0.95, 1.35), attached=random.random() < 0.12)

    if "ai" in globals():
        ai.round += 1 if from_ai else 0
        ai.mode = "SIGNAL"
        ai.mode_time = 0.0
        ai.action_timer = 0.0
        ai.completion_timer = 0.0
        ai.stagnation_time = 0.0
        ai.last_metric = None
        ai.cursor_target = richest_cell_pos()
        chemical_signal_burst(ai.cursor_target, behavior="SLOW", radius=2.6, amount=0.78)

    if not from_ai:
        sim_time = 0.0
        frame_count = 0


def update_labels():
    state = ai.read_state()
    stats_label.text = (
        f"Round {ai.round}\n"
        f"Population: {state['population']}/{MAX_BACTERIA}\n"
        f"Avg nutrient: {state['avg_nutrient']:.2f}\n"
        f"Depleted area: {state['depleted_fraction']*100:.0f}%\n"
        f"Avg slime: {state['avg_slime']:.2f}\n"
        f"Signal field: {state['active_signal_fraction']*100:.0f}%\n"
        f"Attached: {state['attached_fraction']*100:.0f}%\n"
        f"Spread: {state['spread']:.2f}\n"
        f"Boundary: {boundary_mode}\n"
        f"Speed: {SIM_SPEED:.2f}x"
    )

    override = max(0.0, ai.override_until - sim_time)
    mode_label.text = (
        f"AI: {'ON' if ai.enabled else 'OFF'}\n"
        f"Mode: {ai.mode}\n"
        f"Chemical: {chemical_behavior}\n"
        f"Responding: {state['responding_fraction']*100:.0f}%\n"
        f"Mode time: {ai.mode_time:.1f}s\n"
        f"Stagnation: {ai.stagnation_time:.0f}s\n"
        f"{'Manual override: %.1fs' % override if override > 0 else ''}\n"
        f"{'PAUSED' if paused else ''}"
    )


# -----------------------------
# Keyboard controls
# -----------------------------

def move_cursor_manual(dx, dz):
    ai.cursor_target += vector(dx, 0, dz)
    ai.cursor_target.x = clamp(ai.cursor_target.x, -HALF + 0.4, HALF - 0.4)
    ai.cursor_target.z = clamp(ai.cursor_target.z, -HALF + 0.4, HALF - 0.4)
    ai.cursor_pos += (ai.cursor_target - ai.cursor_pos) * 0.45
    ai.override(4.0)


def on_keydown(evt):
    global paused, SIM_SPEED, boundary_mode
    k = evt.key.lower()

    step = 0.75
    if k in ("w", "up"):
        move_cursor_manual(0, -step)
    elif k in ("s", "down"):
        move_cursor_manual(0, step)
    elif k in ("a", "left"):
        move_cursor_manual(-step, 0)
    elif k in ("d", "right"):
        move_cursor_manual(step, 0)
    elif k == " " or k == "p":
        paused = not paused
    elif k == "r":
        reset_simulation(seed_count=START_BACTERIA, from_ai=False)
        ai.override(2.0)
    elif k == "m":
        ai.next_mode()
        ai.override(1.5)
    elif k == "b":
        boundary_mode = "bounce" if boundary_mode == "wrap" else "wrap"
        ai.override(2.0)
    elif k == "n":
        add_bacterium(pos=ai.cursor_pos + vector(random.uniform(-0.3, 0.3), 0, random.uniform(-0.3, 0.3)), theta=random.uniform(0, math.tau), energy=1.2)
        spill_slime(ai.cursor_pos, radius=0.55, amount=0.06)
        ai.override(4.0)
    elif k == "f":
        spill_nutrients(ai.cursor_pos, radius=1.7, amount=0.55)
        ai.override(4.0)
    elif k == "v":
        spill_slime(ai.cursor_pos, radius=1.35, amount=0.45)
        ai.override(4.0)
    elif k == "x":
        scrape_area(ai.cursor_pos, radius=1.45, harshness=0.70)
        ai.override(4.0)
    elif k == "c":
        attach_near(ai.cursor_pos, radius=1.8, attach=True)
        ai.override(4.0)
    elif k == "u":
        attach_near(ai.cursor_pos, radius=1.8, attach=False)
        ai.override(4.0)
    elif k == "o":
        orbit_pulse(ai.cursor_pos, radius=2.8, strength=0.70)
        ai.override(4.0)
    elif k == "g":
        chemical_signal_burst(ai.cursor_pos, behavior=random.choice(["SLOW", "CLUSTER", "DISPERSE"]), radius=2.3, amount=0.85)
        ai.set_mode("SIGNAL", immediate=True)
        ai.override(4.0)
    elif k == "+" or k == "=":
        SIM_SPEED = clamp(SIM_SPEED + 0.15, 0.15, 3.0)
    elif k == "-" or k == "_":
        SIM_SPEED = clamp(SIM_SPEED - 0.15, 0.15, 3.0)
    elif k == "a":
        ai.enabled = not ai.enabled


def on_click(evt):
    loc = scene.mouse.pos
    ai.cursor_target = vector(clamp(loc.x, -HALF + 0.3, HALF - 0.3), BACTERIA_Y, clamp(loc.z, -HALF + 0.3, HALF - 0.3))
    ai.override(3.5)


scene.bind("keydown", on_keydown)
scene.bind("click", on_click)

# -----------------------------
# Initialization
# -----------------------------

initialize_fields()
create_tiles()
update_tile_colors(force=True)

ai = AIController()
reset_simulation(seed_count=START_BACTERIA, from_ai=False)

# -----------------------------
# Main simulation loop
# -----------------------------

last_clock = time.time()

while True:
    rate(45)
    now = time.time()
    real_dt = min(0.055, max(0.001, now - last_clock))
    last_clock = now

    if paused:
        ai.move_cursor(real_dt)
        if frame_count % 12 == 0:
            update_labels()
        continue

    dt = real_dt * SIM_SPEED
    sim_time += dt
    frame_count += 1

    auto_signal_from_colony(dt)
    ai.update(dt)

    for b in list(bacteria):
        b.update(dt)

    process_bacterial_interactions(dt)
    remove_dead_bacteria()

    if frame_count % 3 == 0:
        diffuse_fields(dt * 3.0)

    update_particles(dt)
    update_signal_pulses(dt)
    update_trails(dt)
    update_tile_colors(force=False)

    if frame_count % 10 == 0:
        update_labels()
