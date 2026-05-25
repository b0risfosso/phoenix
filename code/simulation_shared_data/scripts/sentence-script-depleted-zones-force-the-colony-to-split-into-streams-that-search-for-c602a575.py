from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# 3D Bacterial Colony Growth on a 3D Surface
# VPython self-contained simulation with rule-based + dynamic AI
# ------------------------------------------------------------

scene = canvas(
    title="3D Bacterial Colony Growth - Splitting Depleted Streams",
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
  T: force stream search burst    C: attach nearby bacteria      U: detach nearby bacteria
  +/-: speed up / slow down
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

# Depleted-zone stream behavior: when nutrients are exhausted locally,
# cells split into visible outbound streams seeking richer territory.
STREAM_DIFFUSION = 0.024
STREAM_DECAY = 0.006
STREAM_REINFORCE = 0.18
DEPLETION_STREAM_THRESHOLD = 0.46
STREAM_VISUAL_LIMIT = 620
STREAM_SCOUT_FRACTION = 0.42
STREAM_FOLLOW_THRESHOLD = 0.055

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
ST = [[0.0 for _ in range(GRID)] for _ in range(GRID)]  # reinforced outbound stream paths

tiles = []
bacteria = []
trails = []
particles = []
stream_visuals = []

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
    global N, S, ST
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
            ST[i][j] = 0.0


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
    stream_col = vector(1.0, 0.88, 0.24)

    for i in range(GRID):
        for j in range(GRID):
            n = clamp(N[i][j])
            s = clamp(S[i][j])
            st = clamp(ST[i][j])
            if n > 0.48:
                base = mix_color(mid_col, rich_col, (n - 0.48) / 0.52)
            else:
                base = mix_color(poor_col, mid_col, n / 0.48)

            slimed = mix_color(base, slime_col, clamp(s * 0.62))
            streamed = mix_color(slimed, stream_col, clamp(st * 0.52))
            tiles[i][j].color = streamed
            tiles[i][j].opacity = 0.88 + 0.08 * clamp(n)


def diffuse_fields(dt):
    global N, S, ST
    newN = [[N[i][j] for j in range(GRID)] for i in range(GRID)]
    newS = [[S[i][j] for j in range(GRID)] for i in range(GRID)]
    newST = [[ST[i][j] for j in range(GRID)] for i in range(GRID)]

    for i in range(GRID):
        for j in range(GRID):
            totalN = N[i][j]
            totalS = S[i][j]
            totalST = ST[i][j]
            count = 1
            if i > 0:
                totalN += N[i - 1][j]
                totalS += S[i - 1][j]
                totalST += ST[i - 1][j]
                count += 1
            if i < GRID - 1:
                totalN += N[i + 1][j]
                totalS += S[i + 1][j]
                totalST += ST[i + 1][j]
                count += 1
            if j > 0:
                totalN += N[i][j - 1]
                totalS += S[i][j - 1]
                totalST += ST[i][j - 1]
                count += 1
            if j < GRID - 1:
                totalN += N[i][j + 1]
                totalS += S[i][j + 1]
                totalST += ST[i][j + 1]
                count += 1

            avgN = totalN / count
            avgS = totalS / count
            avgST = totalST / count
            newN[i][j] = clamp(N[i][j] + (avgN - N[i][j]) * NUTRIENT_DIFFUSION * dt * 8 + NUTRIENT_REGEN * dt, 0.0, 1.0)
            newS[i][j] = clamp(S[i][j] + (avgS - S[i][j]) * SLIME_DIFFUSION * dt * 8 - SLIME_DECAY * dt, 0.0, 1.35)
            newST[i][j] = clamp(ST[i][j] + (avgST - ST[i][j]) * STREAM_DIFFUSION * dt * 8 - STREAM_DECAY * dt, 0.0, 1.25)

    N = newN
    S = newS
    ST = newST


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


def stream_lane_color(lane):
    palette = [
        vector(1.0, 0.86, 0.20),
        vector(0.48, 0.92, 1.0),
        vector(1.0, 0.50, 0.74),
        vector(0.64, 1.0, 0.50),
        vector(0.92, 0.62, 1.0),
    ]
    return palette[lane % len(palette)]


def strongest_stream_count():
    count = 0
    for b in bacteria:
        if getattr(b, "streaming", False):
            count += 1
    return count


def stream_candidate_score(b):
    local_n = sample_field(N, b.pos)
    local_s = sample_field(S, b.pos)
    center = colony_center()
    outward = clamp(mag(flat(b.pos - center)) / max(0.01, HALF))
    perimeter_bonus = 0.35 if outward > 0.28 else 0.0
    low_food = clamp((0.62 - local_n) / 0.62)
    slime_pressure = clamp(local_s * 0.60)
    return low_food + slime_pressure + perimeter_bonus + random.random() * 0.25


def activate_streamers(center=None, radius=4.0, fraction=STREAM_SCOUT_FRACTION, heat=0.95):
    """Push a larger portion of the colony into visible search-stream behavior."""
    if not bacteria:
        return 0
    candidates = []
    for b in bacteria:
        if b.dead or b.attached:
            continue
        if center is not None and mag(flat(b.pos - center)) > radius:
            continue
        candidates.append((stream_candidate_score(b), b))
    candidates.sort(key=lambda item: item[0], reverse=True)
    target_count = max(1, int(len(candidates) * fraction))
    activated = 0
    for _, b in candidates[:target_count]:
        b.force_stream_time = max(getattr(b, "force_stream_time", 0.0), random.uniform(2.4, 5.2))
        b.stream_heat = max(getattr(b, "stream_heat", 0.0), heat)
        b.set_attached(False)
        direction = choose_fresh_stream_direction(b.pos, b.stream_lane)
        b.vel += direction * random.uniform(0.10, 0.28)
        activated += 1
    return activated


def choose_fresh_stream_direction(pos, lane):
    center = colony_center() if bacteria else vector(0, BACTERIA_Y, 0)
    outward = safe_norm(flat(pos - center))
    if mag(outward) < 0.01:
        outward = heading((lane / 5.0) * math.tau + random.uniform(-0.3, 0.3))

    base_angle = math.atan2(outward.z, outward.x) + (lane - 2) * 0.44
    best_dir = outward
    best_score = -999.0
    for offset in (-1.0, -0.55, -0.22, 0.0, 0.22, 0.55, 1.0):
        direction = heading(base_angle + offset + random.uniform(-0.06, 0.06))
        probe = pos + direction * 3.4
        probe.x = clamp(probe.x, -HALF + 0.2, HALF - 0.2)
        probe.z = clamp(probe.z, -HALF + 0.2, HALF - 0.2)
        nutrient_score = sample_field(N, probe)
        slime_penalty = sample_field(S, probe) * 0.18
        distance_bonus = 0.10 * clamp(mag(flat(probe - center)) / HALF)
        same_stream_bonus = 0.32 * sample_field(ST, probe)
        branch_bias = 0.10 * math.cos(offset * 1.7 + lane)
        score = nutrient_score - slime_penalty + distance_bonus + same_stream_bonus + branch_bias + random.random() * 0.035
        if score > best_score:
            best_score = score
            best_dir = direction
    return safe_norm(best_dir)


def reinforce_stream_path(start, end, lane, strength=1.0):
    moved = mag(flat(end - start))
    if moved < 0.02:
        return

    steps = max(2, int(moved / 0.20))
    for k in range(steps + 1):
        t = k / steps
        p = start * (1 - t) + end * t
        p.y = BACTERIA_Y
        add_to_field(ST, p, STREAM_REINFORCE * strength / steps, radius=0.72, cap=1.45)
        # Searching streams consume and visibly deplete what they leave behind.
        add_to_field(N, p, -0.026 * strength / steps, radius=0.52, cap=1.0)

    if len(stream_visuals) >= STREAM_VISUAL_LIMIT:
        old = stream_visuals.pop(0)
        hide_object(old["obj"])

    c = curve(
        pos=[vector(start.x, 0.052, start.z), vector(end.x, 0.052, end.z)],
        radius=0.023 + 0.012 * clamp(strength),
        color=stream_lane_color(lane)
    )
    try:
        c.opacity = 0.26 + 0.34 * clamp(strength)
    except Exception:
        pass
    stream_visuals.append({"obj": c, "life": 26.0 + 28.0 * clamp(strength), "maxlife": 26.0 + 28.0 * clamp(strength)})


def update_stream_visuals(dt):
    alive = []
    for sv in stream_visuals:
        sv["life"] -= dt
        if sv["life"] <= 0:
            hide_object(sv["obj"])
            continue
        try:
            sv["obj"].opacity = max(0.03, 0.34 * sv["life"] / sv["maxlife"])
        except Exception:
            pass
        alive.append(sv)
    stream_visuals[:] = alive


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
        self.stream_lane = self.id % 5
        self.streaming = False
        self.stream_heat = 0.0
        self.force_stream_time = random.uniform(0.0, 1.2) if random.random() < 0.18 else 0.0
        self.stream_clock = random.uniform(0.05, 0.22)

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
        if self.streaming or self.stream_heat > 0.08:
            c = mix_color(c, stream_lane_color(self.stream_lane), 0.34 + 0.28 * clamp(self.stream_heat))
            self.halo.opacity = 0.12 + 0.12 * clamp(self.stream_heat)
            self.halo.radius = self.radius * (2.0 + 0.85 * clamp(self.stream_heat) + 0.18 * math.sin(sim_time * 5.0 + self.id))
            self.halo.color = stream_lane_color(self.stream_lane)
        elif self.attached:
            c = mix_color(c, vector(0.18, 0.88, 0.82), 0.30)
            self.halo.opacity = 0.12
            self.halo.radius = self.radius * (2.15 + 0.25 * math.sin(sim_time * 2.0 + self.id))
            self.halo.color = vector(0.55, 0.38, 1.0)
        else:
            self.halo.opacity = 0.045
            self.halo.radius = self.radius * 1.75
            self.halo.color = vector(0.55, 0.38, 1.0)

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

        grad_n = field_gradient(N, self.pos)
        grad_s = field_gradient(S, self.pos)

        desired = vector(0, 0, 0)
        if mag(grad_n) > 0.01:
            desired += safe_norm(grad_n) * (0.95 if local_n < 0.72 else 0.33)
        if mag(grad_s) > 0.01:
            desired += safe_norm(grad_s) * (0.20 + 0.60 * clamp(1.0 - local_n))

        stream_level = sample_field(ST, self.pos)
        grad_stream = field_gradient(ST, self.pos)
        self.force_stream_time = max(0.0, self.force_stream_time - dt)
        crowd_depletion_pressure = (local_n < 0.58 and local_s > 0.32)
        early_scout_pressure = (len(bacteria) > 18 and local_n < 0.66 and random.random() < 0.020 * dt)
        depleted_push = local_n < DEPLETION_STREAM_THRESHOLD or crowd_depletion_pressure or self.force_stream_time > 0.0 or early_scout_pressure
        self.streaming = False
        if depleted_push and not self.attached:
            stream_dir = choose_fresh_stream_direction(self.pos, self.stream_lane)
            urgency = clamp((0.72 - local_n) / 0.72)
            desired += stream_dir * (1.65 + 1.25 * urgency + 0.42 * clamp(local_s))
            self.streaming = True
            self.stream_heat = clamp(self.stream_heat + dt * 2.7, 0.0, 1.0)
        elif stream_level > STREAM_FOLLOW_THRESHOLD and mag(grad_stream) > 0.0025 and not self.attached:
            desired += safe_norm(grad_stream) * (0.58 + 0.72 * clamp(stream_level))
            if random.random() < 0.035 * dt:
                self.force_stream_time = random.uniform(1.4, 3.4)
            self.stream_heat = clamp(self.stream_heat + dt * 0.65, 0.0, 0.85)
        else:
            self.stream_heat = max(0.0, self.stream_heat - dt * 0.32)

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
            crawl = BASE_SPEED * 0.045 * (0.6 + local_n)
            self.theta += self.omega * dt * 0.34
            self.pos += self.forward() * crawl * dt + self.vel * dt * 0.5
            slime_rate = 0.055
            consume_rate = 0.010
            if local_n > 0.70 and random.random() < 0.018 * dt:
                self.set_attached(False)
        else:
            speed = BASE_SPEED * (0.25 + 0.92 * local_n) * (1.0 - 0.36 * clamp(local_s))
            if self.streaming:
                speed *= 1.75 + 0.72 * clamp(self.stream_heat)
            elif self.stream_heat > 0.05:
                speed *= 1.0 + 0.38 * clamp(self.stream_heat)
            self.theta += self.omega * dt
            self.pos += self.forward() * speed * dt + self.vel * dt
            slime_rate = 0.030 + 0.030 * clamp(1.0 - local_n)
            consume_rate = 0.020 + 0.030 * clamp(self.energy)

            if local_s > 0.72 and local_n < 0.47 and random.random() < 0.040 * dt:
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

        self.stream_clock -= dt
        if self.streaming and moved > 0.014 and self.stream_clock <= 0:
            reinforce_stream_path(self.prev_pos, self.pos, self.stream_lane, strength=0.85 + self.stream_heat * 0.85)
            self.stream_clock = random.uniform(0.07, 0.20)

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
            "STREAM",
            "MARK",
            "ORGANIZE",
            "STIR",
            "SCRAPE",
            "REST"
        ]
        self.mode = "SEED"
        self.previous_mode = None
        self.mode_time = 0.0
        self.switch_after = 7.0
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
            "STREAM": vector(1.0, 0.88, 0.18),
            "MARK": vector(0.18, 0.88, 0.82),
            "ORGANIZE": vector(1.0, 0.42, 0.78),
            "STIR": vector(0.96, 0.52, 0.28),
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
        avg_energy = 0.0
        for b in bacteria:
            avg_energy += b.energy
            if b.attached:
                attached += 1
        avg_energy = avg_energy / pop if pop else 0.0

        return {
            "population": pop,
            "max_population": MAX_BACTERIA,
            "center": c,
            "spread": spread,
            "avg_nutrient": avg_n,
            "avg_slime": avg_s,
            "total_slime": total_field(S),
            "depleted_fraction": dep,
            "attached_fraction": attached / pop if pop else 0.0,
            "avg_energy": avg_energy,
            "empty": pop == 0,
            "crowded": pop > MAX_BACTERIA * 0.82,
            "nutrient_poor": avg_n < 0.34 or dep > 0.35,
            "high_biofilm": avg_s > 0.34,
            "active_streams": strongest_stream_count(),
            "stream_pressure": dep > 0.18 or avg_n < 0.48 or avg_s > 0.24,
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
        if self.mode == "STREAM":
            return most_depleted_cell_pos() if random.random() < 0.55 else state["center"] + heading(random.uniform(0, math.tau)) * max(2.0, state["spread"] + 2.2)
        if self.mode in ("HERD", "ORGANIZE"):
            return state["center"] + vector(random.uniform(-1.6, 1.6), 0, random.uniform(-1.6, 1.6))
        if self.mode == "SCRAPE":
            return state["center"] + vector(random.uniform(-state["spread"], state["spread"]), 0, random.uniform(-state["spread"], state["spread"]))
        if self.mode in ("STIR", "MARK"):
            r = max(1.1, state["spread"] + random.uniform(0.4, 2.0))
            a = random.uniform(0, math.tau)
            return state["center"] + vector(math.cos(a) * r, 0, math.sin(a) * r)
        return vector(random.uniform(-HALF * 0.7, HALF * 0.7), BACTERIA_Y, random.uniform(-HALF * 0.7, HALF * 0.7))

    def choose_mode(self, state):
        if state["empty"]:
            return "SEED"

        if self.mode_time < 2.2:
            return self.mode

        if state["stream_pressure"] and self.mode not in ("STREAM", "SEED"):
            if random.random() < 0.72:
                return "STREAM"

        if state["nutrient_poor"] and self.mode not in ("FEED", "SEED", "STREAM"):
            if random.random() < 0.45:
                return "FEED"

        if state["population"] < 15 and self.mode != "SEED":
            if random.random() < 0.55:
                return "SEED"

        if state["crowded"] and self.mode not in ("SCRAPE", "ORGANIZE", "STIR"):
            return random.choice(["SCRAPE", "ORGANIZE", "STIR"])

        if state["spread"] < 3.0 and state["population"] > 16:
            return random.choice(["STREAM", "STIR", "MARK", "HERD"])

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
                elif m == "STREAM":
                    w += 3.6 if state["stream_pressure"] else 1.2
                elif m == "MARK":
                    w += 1.1
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
        if self.mode in ("FEED", "STREAM", "MARK", "SCRAPE"):
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

        elif self.mode == "STREAM":
            if self.action_timer <= 0:
                origin = most_depleted_cell_pos() if random.random() < 0.60 else state["center"]
                lane_angle = random.uniform(0, math.tau)
                self.cursor_target = origin + vector(math.cos(lane_angle), 0, math.sin(lane_angle)) * random.uniform(1.4, max(2.2, state["spread"] + 3.0))
                activate_streamers(center=self.cursor_pos, radius=4.8, fraction=random.uniform(0.38, 0.62), heat=1.0)
                spill_slime(self.cursor_pos, radius=0.68, amount=0.045, particles_on=False)
                self.action_timer = random.uniform(0.45, 0.95)
            apply_force_near(self.cursor_pos, radius=3.2, inward=-0.10, tangent=0.05, randomize=0.025, detach=True)

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
    global bacteria, trails, particles, stream_visuals, sim_time, frame_count

    for b in bacteria:
        b.kill()
    bacteria[:] = []

    for tr in trails:
        hide_object(tr["obj"])
    trails[:] = []

    for p in particles:
        hide_object(p["obj"])
    particles[:] = []

    for sv in stream_visuals:
        hide_object(sv["obj"])
    stream_visuals[:] = []

    initialize_fields()
    update_tile_colors(force=True)

    for _ in range(seed_count):
        p = richest_cell_pos() + vector(random.uniform(-1.1, 1.1), 0, random.uniform(-1.1, 1.1))
        add_bacterium(pos=p, theta=random.uniform(0, math.tau), energy=random.uniform(0.95, 1.35), attached=random.random() < 0.12)

    if "ai" in globals():
        ai.round += 1 if from_ai else 0
        ai.mode = "STREAM"
        ai.mode_time = 0.0
        ai.action_timer = 0.0
        ai.completion_timer = 0.0
        ai.stagnation_time = 0.0
        ai.last_metric = None
        ai.cursor_target = richest_cell_pos()

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
        f"Attached: {state['attached_fraction']*100:.0f}%\n"
        f"Streaming: {strongest_stream_count()}\n"
        f"Stream paths: {len(stream_visuals)}\n"
        f"Spread: {state['spread']:.2f}\n"
        f"Boundary: {boundary_mode}\n"
        f"Speed: {SIM_SPEED:.2f}x"
    )

    override = max(0.0, ai.override_until - sim_time)
    mode_label.text = (
        f"AI: {'ON' if ai.enabled else 'OFF'}\n"
        f"Mode: {ai.mode}\n"
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
    elif k == "t":
        activate_streamers(center=ai.cursor_pos, radius=5.2, fraction=0.72, heat=1.0)
        spill_slime(ai.cursor_pos, radius=0.9, amount=0.08, particles_on=True)
        ai.set_mode("STREAM", immediate=True)
        ai.override(2.0)
    elif k == "c":
        attach_near(ai.cursor_pos, radius=1.8, attach=True)
        ai.override(4.0)
    elif k == "u":
        attach_near(ai.cursor_pos, radius=1.8, attach=False)
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

    ai.update(dt)

    for b in list(bacteria):
        b.update(dt)

    process_bacterial_interactions(dt)
    remove_dead_bacteria()

    if frame_count % 3 == 0:
        diffuse_fields(dt * 3.0)

    update_particles(dt)
    update_trails(dt)
    update_stream_visuals(dt)
    update_tile_colors(force=False)

    if frame_count % 10 == 0:
        update_labels()
