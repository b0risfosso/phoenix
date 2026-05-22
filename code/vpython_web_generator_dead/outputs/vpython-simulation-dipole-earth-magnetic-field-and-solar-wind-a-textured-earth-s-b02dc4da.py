from vpython import *
import math
import random

# ============================================================
# Dipole Earth Magnetic Field + Solar Wind + Autonomous AI
# Self-contained VPython simulation
# ============================================================

scene.title = "Dipole Earth Magnetic Field and Solar Wind - AI Controlled VPython Simulation"
scene.width = 1180
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-1.8, -0.65, -1.25)
scene.up = vector(0, 1, 0)
scene.range = 6.8
scene.center = vector(0, 0, 0)

scene.append_to_caption(
    "\nControls: "
    "P pause | A AI on/off | R reset | B burst | M AI mode | "
    "Q/E tilt | Z/C azimuth | +/- spawn | [/ ] wind | X cleanup | H help\n\n"
)
status_text = wtext(text="Starting simulation...\n")

# -----------------------------
# Constants and global settings
# -----------------------------

EARTH_RADIUS = 1.0
MAGNETOPAUSE_RADIUS = 4.0
PARTICLE_LIMIT = 110
FLASH_LIMIT = 70

SOLAR_SOURCE_X = -8.4
SOLAR_EXIT_X = 8.5
SOLAR_WIND_RADIUS = 2.45

dt = 0.018
sim_time = 0.0
paused = False
show_help = False

dipole_tilt_deg = 23.5
dipole_azimuth = math.radians(20)
dipole_strength = 1.0
dipole_axis = vector(0, 0, 1)

solar_wind_speed = 2.6
spawn_rate = 10.0
spawn_accumulator = 0.0

ai_enabled = True
manual_override_until = 0.0

round_number = 1
impact_count = 0
escaped_count = 0
collision_count = 0
reset_count = 0

particles = []
flashes = []
field_lines = []
marks = []

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-9:
        return fallback
    return v / m

def random_disk(radius):
    a = random.random() * 2 * math.pi
    r = radius * math.sqrt(random.random())
    return r * math.cos(a), r * math.sin(a)

def basis_from_axis(axis):
    uz = safe_norm(axis, vector(0, 0, 1))
    ref = vector(0, 1, 0)
    if mag(cross(ref, uz)) < 0.02:
        ref = vector(1, 0, 0)
    ux = safe_norm(cross(ref, uz), vector(1, 0, 0))
    uy = safe_norm(cross(uz, ux), vector(0, 1, 0))
    return ux, uy, uz

def local_to_world(v, axis=None):
    if axis is None:
        axis = dipole_axis
    ux, uy, uz = basis_from_axis(axis)
    return ux * v.x + uy * v.y + uz * v.z

def local_spherical(r, theta, phi):
    return vector(
        r * math.sin(theta) * math.cos(phi),
        r * math.sin(theta) * math.sin(phi),
        r * math.cos(theta),
    )

def magnetic_latitude(pos):
    r = mag(pos)
    if r < 1e-9:
        return 0.0
    return math.asin(clamp(dot(pos / r, safe_norm(dipole_axis)), -1, 1))

def dipole_B(pos):
    r = mag(pos)
    if r < EARTH_RADIUS * 0.72:
        r = EARTH_RADIUS * 0.72
    rhat = safe_norm(pos, vector(1, 0, 0))
    mhat = safe_norm(dipole_axis)
    return dipole_strength * (3 * rhat * dot(mhat, rhat) - mhat) / (r ** 3)

def field_direction_toward_earth(pos):
    B = dipole_B(pos)
    b = safe_norm(B, vector(0, 0, 1))
    if dot(b, pos) > 0:
        b = -b
    return b

def hsv(h, s, v):
    return color.hsv_to_rgb(vector(h % 1.0, clamp(s, 0, 1), clamp(v, 0, 1)))

# -----------------------------
# Scene objects
# -----------------------------

sun = sphere(
    pos=vector(SOLAR_SOURCE_X - 1.55, 0, 0),
    radius=0.38,
    color=vector(1.0, 0.78, 0.20),
    emissive=True,
)
local_light(pos=sun.pos, color=vector(1.0, 0.92, 0.75))

earth = sphere(
    pos=vector(0, 0, 0),
    radius=EARTH_RADIUS,
    texture=textures.earth,
    shininess=0.25,
)

atmosphere = sphere(
    pos=vector(0, 0, 0),
    radius=EARTH_RADIUS * 1.018,
    color=vector(0.55, 0.78, 1.0),
    opacity=0.16,
    shininess=0.0,
)

magnetosphere = sphere(
    pos=vector(0.82, 0, 0),
    radius=1,
    scale=vector(4.9, 2.45, 2.45),
    color=vector(0.35, 0.74, 1.0),
    opacity=0.085,
    shininess=0.0,
)

bow_shock = sphere(
    pos=vector(-1.35, 0, 0),
    radius=1,
    scale=vector(3.75, 2.85, 2.85),
    color=vector(0.85, 0.96, 1.0),
    opacity=0.095,
    shininess=0.0,
)

tail_sheet = cylinder(
    pos=vector(1.3, 0, 0),
    axis=vector(5.2, 0, 0),
    radius=0.18,
    color=vector(0.58, 0.78, 1.0),
    opacity=0.16,
)

wind_arrows = []
for yy in [-1.55, -0.55, 0.55, 1.55]:
    arr = arrow(
        pos=vector(-7.15, yy, -2.85),
        axis=vector(1.15, 0, 0),
        shaftwidth=0.035,
        headwidth=0.13,
        headlength=0.20,
        color=vector(0.95, 0.72, 0.20),
        opacity=0.82,
    )
    wind_arrows.append(arr)

dipole_arrow = arrow(
    pos=vector(0, 0, 0),
    axis=vector(0, 0, 1.75),
    shaftwidth=0.045,
    headwidth=0.16,
    color=vector(0.20, 0.28, 1.0),
    opacity=0.9,
)
dipole_ring = ring(
    pos=vector(0, 0, 0),
    axis=vector(0, 0, 1),
    radius=1.16,
    thickness=0.012,
    color=vector(0.25, 0.40, 1.0),
    opacity=0.55,
)

north_label = label(
    pos=vector(0, 0, 1.35),
    text="magnetic N",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.10, 0.20, 0.95),
)
south_label = label(
    pos=vector(0, 0, -1.35),
    text="magnetic S",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.10, 0.20, 0.95),
)
earth_label = label(
    pos=vector(0, -1.55, 0),
    text="Earth + tilted magnetic dipole",
    height=12,
    box=False,
    opacity=0,
    color=vector(0.10, 0.18, 0.24),
)

# -----------------------------
# Aurora curtain system
# -----------------------------

class AuroraSystem:
    def __init__(self):
        self.strands = []
        self.oval_rings = []
        self.energy_north = 0.0
        self.energy_south = 0.0
        self.last_rebuild_axis = vector(0, 0, 1)
        self.rebuild()

    def hide_all(self):
        for s in self.strands:
            s.visible = False
        for r in self.oval_rings:
            r.visible = False
        self.strands = []
        self.oval_rings = []

    def rebuild(self):
        self.hide_all()
        self.last_rebuild_axis = vector(dipole_axis.x, dipole_axis.y, dipole_axis.z)

        for sign in [1, -1]:
            ring_points = []
            lat = math.radians(67.0) * sign
            theta = math.pi / 2 - lat
            for i in range(121):
                phi = 2 * math.pi * i / 120
                p = local_to_world(local_spherical(EARTH_RADIUS * 1.036, theta, phi))
                ring_points.append(p)
            ring_obj = curve(
                pos=ring_points,
                radius=0.012,
                color=vector(0.16, 1.0, 0.54) if sign > 0 else vector(0.10, 0.90, 1.0),
            )
            self.oval_rings.append(ring_obj)

            for k in range(24):
                phi = 2 * math.pi * k / 24
                local_lat = math.radians(63 + 9 * random.random()) * sign
                theta = math.pi / 2 - local_lat
                base = local_to_world(local_spherical(EARTH_RADIUS * 1.025, theta, phi))
                outward = safe_norm(base)
                pts = []
                height = random.uniform(0.30, 0.78)
                wiggle_dir = safe_norm(cross(outward, dipole_axis), vector(0, 1, 0))
                for j in range(9):
                    f = j / 8
                    wave = math.sin(f * math.pi * 2 + k * 0.8) * 0.025
                    pts.append(base + outward * (height * f) + wiggle_dir * wave)
                strand_color = vector(0.12, 1.0, 0.45) if sign > 0 else vector(0.12, 0.82, 1.0)
                self.strands.append({
                    "curve": curve(pos=pts, radius=0.009, color=strand_color),
                    "base": base,
                    "outward": outward,
                    "wiggle": wiggle_dir,
                    "height": height,
                    "phase": random.random() * 2 * math.pi,
                    "sign": sign,
                    "hue": 0.34 if sign > 0 else 0.52,
                })

    def pulse(self, sign, power=1.0):
        if sign >= 0:
            self.energy_north = clamp(self.energy_north + 0.34 * power, 0, 5.0)
        else:
            self.energy_south = clamp(self.energy_south + 0.34 * power, 0, 5.0)

    def total_energy(self):
        return self.energy_north + self.energy_south

    def update(self, t, step_dt):
        self.energy_north *= math.exp(-0.42 * step_dt)
        self.energy_south *= math.exp(-0.42 * step_dt)

        if mag(self.last_rebuild_axis - dipole_axis) > 0.04:
            self.rebuild()

        for item in self.strands:
            e = self.energy_north if item["sign"] > 0 else self.energy_south
            brightness = clamp(0.26 + 0.18 * e + 0.08 * math.sin(t * 4.0 + item["phase"]), 0.15, 1.0)
            item["curve"].color = hsv(item["hue"] + 0.035 * math.sin(t + item["phase"]), 0.78, brightness)
            item["curve"].radius = 0.006 + 0.0045 * clamp(e, 0, 4)

            pts = []
            base = item["base"]
            outward = item["outward"]
            wiggle = item["wiggle"]
            height = item["height"] * (1.0 + 0.16 * clamp(e, 0, 4))
            for j in range(9):
                f = j / 8
                wave = math.sin(t * 3.3 + item["phase"] + f * 5.5) * 0.022 * (1 + e * 0.14)
                pts.append(base + outward * (height * f) + wiggle * wave)
            item["curve"].clear()
            item["curve"].append(pts)

        for idx, ring_obj in enumerate(self.oval_rings):
            e = self.energy_north if idx == 0 else self.energy_south
            ring_obj.radius = 0.009 + 0.005 * clamp(e, 0, 4)
            ring_obj.color = hsv(0.34 if idx == 0 else 0.52, 0.72, clamp(0.35 + 0.14 * e, 0.2, 1.0))

aurora = AuroraSystem()

# -----------------------------
# Field line generation
# -----------------------------

def clear_field_lines():
    for ln in field_lines:
        ln.visible = False
    field_lines.clear()

def create_field_lines():
    clear_field_lines()

    shells = [1.35, 1.7, 2.15, 2.7, 3.35]
    phis = [2 * math.pi * i / 8 for i in range(8)]
    for L_i, L in enumerate(shells):
        theta_min = math.asin(math.sqrt(EARTH_RADIUS / L)) + 0.018
        theta_max = math.pi - theta_min
        for phi_i, phi in enumerate(phis):
            pts = []
            n = 92
            for j in range(n):
                theta = theta_min + (theta_max - theta_min) * j / (n - 1)
                r = L * (math.sin(theta) ** 2)
                p = local_to_world(local_spherical(r, theta, phi))
                pts.append(p)
            hue_value = 0.54 + 0.06 * (L_i / max(1, len(shells) - 1))
            line_color = hsv(hue_value, 0.55, 0.70)
            ln = curve(pos=pts, radius=0.0065, color=line_color)
            field_lines.append(ln)

    # Open cusp guide lines
    for sign in [1, -1]:
        for k in range(8):
            phi = 2 * math.pi * k / 8 + 0.15
            pts = []
            lat0 = math.radians(71) * sign
            theta0 = math.pi / 2 - lat0
            base = local_to_world(local_spherical(EARTH_RADIUS * 1.03, theta0, phi))
            outward = safe_norm(base)
            for j in range(38):
                f = j / 37
                p = base * (1 - f) + (outward * (1.3 + 2.9 * f) + vector(-1.25 * f * f, 0, 0)) * f
                pts.append(p)
            ln = curve(pos=pts, radius=0.0055, color=vector(0.36, 0.72, 1.0))
            field_lines.append(ln)

def set_dipole(tilt_deg=None, azimuth=None):
    global dipole_tilt_deg, dipole_azimuth, dipole_axis

    if tilt_deg is not None:
        dipole_tilt_deg = clamp(tilt_deg, 0, 65)
    if azimuth is not None:
        dipole_azimuth = azimuth

    tilt = math.radians(dipole_tilt_deg)
    dipole_axis = safe_norm(vector(
        math.sin(tilt) * math.cos(dipole_azimuth),
        math.sin(tilt) * math.sin(dipole_azimuth),
        math.cos(tilt),
    ), vector(0, 0, 1))

    dipole_arrow.axis = dipole_axis * 1.75
    dipole_ring.axis = dipole_axis
    north_label.pos = dipole_axis * 1.42
    south_label.pos = -dipole_axis * 1.42

    create_field_lines()
    aurora.rebuild()

set_dipole(dipole_tilt_deg, dipole_azimuth)

# -----------------------------
# Particle, flash, and mark systems
# -----------------------------

class Flash:
    def __init__(self, pos, col, radius=0.045, life=1.3):
        self.life = life
        self.age = 0.0
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=col,
            emissive=True,
            opacity=0.82,
            make_trail=False,
        )

    def update(self, step_dt):
        self.age += step_dt
        f = clamp(1 - self.age / self.life, 0, 1)
        self.obj.radius *= (1 + 0.85 * step_dt)
        self.obj.opacity = 0.82 * f
        self.obj.color = self.obj.color * (0.98 + 0.04 * f)
        if self.age >= self.life:
            self.obj.visible = False
            return False
        return True

class SceneMark:
    def __init__(self, pos, text, col=vector(1, 0.35, 0.7), life=2.2):
        self.age = 0
        self.life = life
        self.obj = label(
            pos=pos,
            text=text,
            color=col,
            box=False,
            opacity=0,
            height=11,
        )

    def update(self, step_dt):
        self.age += step_dt
        self.obj.pos = self.obj.pos + vector(0, 0.035 * step_dt, 0)
        self.obj.color = self.obj.color * 0.998
        if self.age > self.life:
            self.obj.visible = False
            return False
        return True

class SolarParticle:
    next_id = 0

    def __init__(self, storm=False):
        SolarParticle.next_id += 1
        self.id = SolarParticle.next_id
        y, z = random_disk(SOLAR_WIND_RADIUS * (1.25 if storm else 1.0))
        self.pos = vector(SOLAR_SOURCE_X, y, z)
        self.q = random.choice([-1, 1])
        spread = 0.20 if not storm else 0.38
        self.vel = vector(
            solar_wind_speed * random.uniform(0.88, 1.18 if storm else 1.08),
            random.uniform(-spread, spread),
            random.uniform(-spread, spread),
        )
        self.state = "wind"
        self.age = 0.0
        self.shell = random.uniform(1.6, 3.0)
        self.attached = False
        self.charge_color = vector(1.0, 0.78, 0.20) if self.q > 0 else vector(0.35, 0.55, 1.0)
        self.obj = sphere(
            pos=self.pos,
            radius=0.038 if not storm else 0.046,
            color=self.charge_color,
            emissive=True,
            make_trail=True,
            retain=34,
            trail_radius=0.010,
        )
        self.obj.trail_color = self.charge_color
        self.last_state_change = sim_time

    def set_state(self, new_state, col=None):
        if self.state != new_state:
            self.last_state_change = sim_time
        self.state = new_state
        if col is not None:
            self.obj.color = col
            self.obj.trail_color = col

    def attach_to_field(self):
        self.attached = True
        self.set_state("attached", vector(0.65, 0.28, 1.0))

    def detach(self):
        self.attached = False
        self.set_state("wind", self.charge_color)

    def cleanup(self):
        self.obj.visible = False
        self.obj.clear_trail()

    def update(self, step_dt):
        global impact_count, escaped_count, collision_count

        self.age += step_dt
        p = self.pos
        v = self.vel
        r = mag(p)
        lat = magnetic_latitude(p)
        a = vector(0, 0, 0)

        # Uniform solar wind pressure from Sun to Earth and onward
        a += vector(0.05, 0, 0)

        # Magnetic Lorentz-like deflection inside the visible magnetosphere
        inside_magnetosphere = r < MAGNETOPAUSE_RADIUS + 0.55
        if inside_magnetosphere:
            B = dipole_B(p)
            a += self.q * 0.68 * cross(v, B)

            # Front-side magnetopause: spill, wrap, and bounce around boundary
            if p.x < 0 and r < MAGNETOPAUSE_RADIUS:
                transverse = vector(0, p.y, p.z)
                if mag(transverse) < 0.08:
                    transverse = vector(0, random.choice([-1, 1]), random.choice([-1, 1]))
                boundary_strength = (MAGNETOPAUSE_RADIUS - r) / MAGNETOPAUSE_RADIUS
                a += safe_norm(transverse) * (2.25 * boundary_strength)
                a += vector(-0.22 * boundary_strength, 0, 0)
                if self.state == "wind":
                    self.set_state("deflected", vector(1.0, 0.56, 0.18))

            # Polar cusps funnel particles along field lines
            if r < 3.35 and abs(lat) > math.radians(38):
                if self.state not in ["funnel", "aurora"]:
                    self.attach_to_field()
                    self.set_state("funnel", vector(0.18, 1.0, 0.60))
                a += field_direction_toward_earth(p) * (1.8 + 0.35 * abs(lat))

            # Equatorial trapping: particles wrap/orbit/drift in the belt
            if r < 3.0 and abs(lat) < math.radians(42):
                if self.state in ["wind", "deflected"] and random.random() < 0.009:
                    self.attached = True
                    self.shell = clamp(r, 1.55, 3.05)
                    self.set_state("trapped", vector(0.75, 0.28, 1.0))

            if self.state == "trapped":
                drift = cross(dipole_axis, p)
                if mag(drift) > 0.02:
                    a += safe_norm(drift) * (0.62 + 0.10 * self.q)
                a += safe_norm(p) * ((self.shell - r) * 1.05)
                if abs(lat) > math.radians(55):
                    a += -safe_norm(dipole_axis) * (0.22 * (1 if lat > 0 else -1))
                if self.age - self.last_state_change > random.uniform(8.0, 15.0):
                    self.detach()

        # Tail stretching and spilling behind Earth
        if p.x > 1.3 and r < 3.5:
            a += vector(0.12, 0, 0)
            if self.state in ["deflected", "wind"]:
                a += vector(0, -0.05 * p.y, -0.05 * p.z)

        # Human/AI marked particles sparkle and obey their current state
        if self.state == "marked":
            a += field_direction_toward_earth(p) * 0.8

        self.vel = v + a * step_dt
        speed_cap = 5.2
        if mag(self.vel) > speed_cap:
            self.vel = safe_norm(self.vel) * speed_cap

        self.pos = p + self.vel * step_dt
        self.obj.pos = self.pos

        # Collision with Earth / atmosphere
        r = mag(self.pos)
        if r < EARTH_RADIUS * 1.026:
            n = safe_norm(self.pos)
            lat = magnetic_latitude(self.pos)

            if abs(lat) > math.radians(52) or self.state in ["funnel", "attached", "marked"]:
                sign = 1 if lat >= 0 else -1
                impact_pos = n * (EARTH_RADIUS * 1.045)
                aurora.pulse(sign, power=1.5 if self.state == "funnel" else 1.0)
                flashes.append(Flash(
                    impact_pos,
                    vector(0.25, 1.0, 0.48) if sign > 0 else vector(0.25, 0.82, 1.0),
                    radius=0.05,
                    life=1.1,
                ))
                impact_count += 1
                self.cleanup()
                return False
            else:
                collision_count += 1
                self.pos = n * EARTH_RADIUS * 1.07
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.72
                self.set_state("bounced", vector(1.0, 0.36, 0.18))

        # Escape / recycle
        if self.pos.x > SOLAR_EXIT_X or self.pos.x < SOLAR_SOURCE_X - 1.2 or mag(self.pos) > 9.5 or self.age > 28:
            escaped_count += 1
            self.cleanup()
            return False

        return True

def spawn_particle(storm=False):
    if len(particles) >= PARTICLE_LIMIT:
        return
    particles.append(SolarParticle(storm=storm))

def spawn_burst(n=18, storm=True):
    for _ in range(n):
        spawn_particle(storm=storm)
    marks.append(SceneMark(vector(SOLAR_SOURCE_X + 0.35, 1.95, 0), "solar wind burst", vector(1.0, 0.45, 0.05)))

def cleanup_particles(fraction=1.0):
    global particles
    keep = []
    for p in particles:
        remove = random.random() < fraction
        if remove:
            p.cleanup()
        else:
            keep.append(p)
    particles = keep
    marks.append(SceneMark(vector(1.2, 2.8, 0), "cleanup / detach", vector(0.60, 0.2, 1.0)))

def reset_simulation(reason="new round"):
    global particles, flashes, marks, spawn_accumulator, round_number
    global impact_count, escaped_count, collision_count, reset_count
    global solar_wind_speed, spawn_rate

    for p in particles:
        p.cleanup()
    particles = []

    for f in flashes:
        f.obj.visible = False
    flashes = []

    for m in marks:
        m.obj.visible = False
    marks = []

    spawn_accumulator = 0.0
    impact_count = 0
    escaped_count = 0
    collision_count = 0
    reset_count += 1
    round_number += 1

    solar_wind_speed = random.uniform(2.1, 3.1)
    spawn_rate = random.uniform(7.0, 13.0)

    aurora.energy_north = 0.0
    aurora.energy_south = 0.0

    set_dipole(random.uniform(16, 38), random.uniform(0, 2 * math.pi))
    marks.append(SceneMark(vector(-1.2, 3.15, 0), "AI loop reset: " + reason, vector(0.2, 0.38, 1.0), life=3.0))

# -----------------------------
# AI behavior system
# -----------------------------

class MagneticWindAI:
    MODES = [
        "OBSERVE",
        "QUIET",
        "STORM",
        "AURORA_PAINT",
        "DIPOLE_DANCE",
        "SHEPHERD",
        "ORGANIZE",
        "CHAOS",
        "CLEANUP",
        "RESET",
    ]

    def __init__(self):
        self.mode = "OBSERVE"
        self.mode_age = 0.0
        self.mode_duration = 6.0
        self.last_action = 0.0
        self.history = []
        self.history_timer = 0.0
        self.stagnant_time = 0.0
        self.completed_time = 0.0
        self.loop_delay = 0.0
        self.previous_signature = None
        self.round_seed = random.random()

    def read_state(self):
        counts = {}
        for p in particles:
            counts[p.state] = counts.get(p.state, 0) + 1

        avg_speed = 0.0
        if particles:
            avg_speed = sum(mag(p.vel) for p in particles) / len(particles)

        return {
            "time": sim_time,
            "particle_count": len(particles),
            "trapped": counts.get("trapped", 0),
            "funnel": counts.get("funnel", 0) + counts.get("attached", 0) + counts.get("marked", 0),
            "deflected": counts.get("deflected", 0) + counts.get("bounced", 0),
            "wind": counts.get("wind", 0),
            "aurora_energy": aurora.total_energy(),
            "north_energy": aurora.energy_north,
            "south_energy": aurora.energy_south,
            "impacts": impact_count,
            "escapes": escaped_count,
            "collisions": collision_count,
            "avg_speed": avg_speed,
            "spawn_rate": spawn_rate,
            "wind_speed": solar_wind_speed,
            "tilt": dipole_tilt_deg,
        }

    def choose_mode(self, st):
        if self.is_stagnant(st):
            return "RESET"

        if st["particle_count"] == 0 and self.mode_age > 2.0:
            return random.choice(["STORM", "AURORA_PAINT", "DIPOLE_DANCE"])

        if st["aurora_energy"] > 6.0:
            return random.choice(["QUIET", "ORGANIZE", "OBSERVE"])

        if st["trapped"] > 18 and random.random() < 0.7:
            return random.choice(["SHEPHERD", "AURORA_PAINT", "CLEANUP"])

        if st["particle_count"] < 12:
            return random.choice(["STORM", "CHAOS"])

        if self.mode_age >= self.mode_duration:
            options = list(self.MODES)
            options.remove("RESET")
            if self.mode in options and len(options) > 1:
                options.remove(self.mode)
            return random.choice(options)

        return self.mode

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode = mode
            self.mode_age = 0.0
            self.mode_duration = random.uniform(4.0, 9.5)
            if mode == "QUIET":
                self.mode_duration = random.uniform(5.0, 11.0)
            if mode == "STORM":
                self.mode_duration = random.uniform(3.4, 6.5)
            if mode == "RESET":
                self.mode_duration = 1.0
            marks.append(SceneMark(vector(-2.6, 3.25, 0), "AI mode: " + mode, vector(0.10, 0.22, 0.88), life=2.2))

    def is_stagnant(self, st):
        self.history_timer += dt
        if self.history_timer < 1.5:
            return False
        self.history_timer = 0.0

        signature = (
            round(st["particle_count"] / 4),
            round(st["trapped"] / 3),
            round(st["funnel"] / 2),
            round(st["aurora_energy"] * 1.5),
            st["impacts"],
            st["escapes"],
        )

        if self.previous_signature is not None:
            activity_delta = sum(abs(signature[i] - self.previous_signature[i]) for i in range(len(signature)))
            if activity_delta <= 1:
                self.stagnant_time += 1.5
            else:
                self.stagnant_time = max(0, self.stagnant_time - 1.0)

        self.previous_signature = signature

        if st["particle_count"] == 0 and st["aurora_energy"] < 0.14:
            self.completed_time += 1.5
        else:
            self.completed_time = 0.0

        return self.stagnant_time > 8.0 or self.completed_time > 4.0

    def act_observe(self, st):
        global spawn_rate
        spawn_rate = clamp(spawn_rate + random.uniform(-0.15, 0.10), 3.0, 14.0)

    def act_quiet(self, st):
        global spawn_rate, solar_wind_speed
        spawn_rate = clamp(spawn_rate - 0.08, 2.0, 8.0)
        solar_wind_speed = clamp(solar_wind_speed - 0.012, 1.6, 3.8)
        if random.random() < 0.025 and len(particles) > 20:
            cleanup_particles(0.08)

    def act_storm(self, st):
        global spawn_rate, solar_wind_speed
        spawn_rate = clamp(spawn_rate + 0.20, 9.0, 24.0)
        solar_wind_speed = clamp(solar_wind_speed + 0.018, 2.4, 4.6)
        if sim_time - self.last_action > random.uniform(1.2, 2.5):
            spawn_burst(random.randint(9, 22), storm=True)
            self.last_action = sim_time

    def act_aurora_paint(self, st):
        global spawn_rate
        spawn_rate = clamp(spawn_rate + 0.03, 7.0, 18.0)

        target_sign = 1 if st["north_energy"] < st["south_energy"] else -1

        candidates = [p for p in particles if mag(p.pos) < 3.8 and p.pos.x < 1.8]
        random.shuffle(candidates)
        for p in candidates[:4]:
            lat = magnetic_latitude(p.pos)
            if lat * target_sign < math.radians(35):
                guide = safe_norm(dipole_axis * target_sign + field_direction_toward_earth(p.pos) * 0.65)
                p.vel = p.vel * 0.82 + guide * mag(p.vel) * 0.48
                p.attached = True
                p.set_state("marked", vector(1.0, 0.18, 0.74))

        if sim_time - self.last_action > 1.6:
            marks.append(SceneMark(dipole_axis * target_sign * 1.7, "paint aurora", vector(0.95, 0.1, 0.65), life=1.6))
            self.last_action = sim_time

    def act_dipole_dance(self, st):
        wobble = math.sin(sim_time * 0.75 + self.round_seed * 6.28)
        new_tilt = clamp(25 + 16 * wobble + 6 * math.sin(sim_time * 0.22), 5, 58)
        new_az = dipole_azimuth + 0.006 * math.sin(sim_time * 0.9)
        if int(sim_time * 10) % 7 == 0:
            set_dipole(new_tilt, new_az)

    def act_shepherd(self, st):
        global spawn_rate
        spawn_rate = clamp(spawn_rate, 5.0, 14.0)

        for p in particles:
            if mag(p.pos) < 4.1:
                lat = magnetic_latitude(p.pos)
                if p.state in ["trapped", "deflected", "bounced", "wind"]:
                    direction = field_direction_toward_earth(p.pos)
                    p.vel = p.vel * 0.95 + direction * 0.12
                    if abs(lat) > math.radians(28):
                        p.attached = True
                        p.set_state("funnel", vector(0.18, 1.0, 0.58))

        if sim_time - self.last_action > 2.0:
            marks.append(SceneMark(vector(1.1, 2.75, 0), "shepherd along field lines", vector(0.2, 0.75, 1.0), life=1.7))
            self.last_action = sim_time

    def act_organize(self, st):
        # Organize charges into opposite drifts, making the radiation belts visibly structured.
        for p in particles:
            r = mag(p.pos)
            if 1.35 < r < 3.35:
                drift = cross(dipole_axis, p.pos)
                if mag(drift) > 0.01:
                    p.vel = p.vel * 0.96 + safe_norm(drift) * (0.09 * p.q)
                    p.shell = clamp(r, 1.4, 3.2)
                    if p.state not in ["funnel", "marked"]:
                        p.set_state("trapped", vector(0.74, 0.32, 1.0))

    def act_chaos(self, st):
        global spawn_rate, solar_wind_speed
        spawn_rate = clamp(spawn_rate + random.uniform(-0.15, 0.32), 5, 22)
        solar_wind_speed = clamp(solar_wind_speed + random.uniform(-0.035, 0.045), 1.8, 4.8)

        if random.random() < 0.03:
            set_dipole(
                clamp(dipole_tilt_deg + random.uniform(-7, 7), 0, 62),
                dipole_azimuth + random.uniform(-0.22, 0.22),
            )

        for p in random.sample(particles, min(5, len(particles))):
            p.vel += vector(random.uniform(-0.12, 0.12), random.uniform(-0.16, 0.16), random.uniform(-0.16, 0.16))
            if random.random() < 0.20:
                p.set_state("deflected", vector(1.0, 0.42, 0.12))

    def act_cleanup(self, st):
        global spawn_rate
        spawn_rate = clamp(spawn_rate - 0.16, 1.0, 7.0)
        if sim_time - self.last_action > 1.0:
            cleanup_particles(0.12)
            self.last_action = sim_time
        if len(particles) < 10:
            self.set_mode("QUIET")

    def update(self, step_dt):
        if not ai_enabled or paused:
            return

        if sim_time < manual_override_until:
            return

        self.mode_age += step_dt
        st = self.read_state()
        next_mode = self.choose_mode(st)
        self.set_mode(next_mode)

        if self.mode == "RESET":
            reset_simulation("stagnant or complete")
            self.stagnant_time = 0.0
            self.completed_time = 0.0
            self.previous_signature = None
            self.set_mode(random.choice(["OBSERVE", "STORM", "AURORA_PAINT"]))
            return

        if self.mode == "OBSERVE":
            self.act_observe(st)
        elif self.mode == "QUIET":
            self.act_quiet(st)
        elif self.mode == "STORM":
            self.act_storm(st)
        elif self.mode == "AURORA_PAINT":
            self.act_aurora_paint(st)
        elif self.mode == "DIPOLE_DANCE":
            self.act_dipole_dance(st)
        elif self.mode == "SHEPHERD":
            self.act_shepherd(st)
        elif self.mode == "ORGANIZE":
            self.act_organize(st)
        elif self.mode == "CHAOS":
            self.act_chaos(st)
        elif self.mode == "CLEANUP":
            self.act_cleanup(st)

ai = MagneticWindAI()

# -----------------------------
# Human keyboard controller
# -----------------------------

def human_override(seconds=3.0):
    global manual_override_until
    manual_override_until = max(manual_override_until, sim_time + seconds)

def cycle_ai_mode():
    idx = MagneticWindAI.MODES.index(ai.mode) if ai.mode in MagneticWindAI.MODES else 0
    next_mode = MagneticWindAI.MODES[(idx + 1) % len(MagneticWindAI.MODES)]
    if next_mode == "RESET":
        next_mode = MagneticWindAI.MODES[(idx + 2) % len(MagneticWindAI.MODES)]
    ai.set_mode(next_mode)

def keydown(evt):
    global paused, ai_enabled, spawn_rate, solar_wind_speed, show_help

    k = evt.key.lower()
    human_override(4.0)

    if k == "p":
        paused = not paused
    elif k == "a":
        ai_enabled = not ai_enabled
        marks.append(SceneMark(vector(-2.2, 3.0, 0), "AI " + ("ON" if ai_enabled else "OFF"), vector(0.0, 0.25, 1.0)))
    elif k == "r":
        reset_simulation("manual reset")
    elif k == "b":
        spawn_burst(24, storm=True)
    elif k == "m":
        cycle_ai_mode()
    elif k == "x":
        cleanup_particles(0.75)
    elif k == "q":
        set_dipole(dipole_tilt_deg - 3.0, dipole_azimuth)
    elif k == "e":
        set_dipole(dipole_tilt_deg + 3.0, dipole_azimuth)
    elif k == "z":
        set_dipole(dipole_tilt_deg, dipole_azimuth - math.radians(8))
    elif k == "c":
        set_dipole(dipole_tilt_deg, dipole_azimuth + math.radians(8))
    elif k in ["+", "="]:
        spawn_rate = clamp(spawn_rate + 1.2, 0.5, 30)
    elif k in ["-", "_"]:
        spawn_rate = clamp(spawn_rate - 1.2, 0.5, 30)
    elif k == "[":
        solar_wind_speed = clamp(solar_wind_speed - 0.25, 0.6, 6)
    elif k == "]":
        solar_wind_speed = clamp(solar_wind_speed + 0.25, 0.6, 6)
    elif k == "h":
        show_help = not show_help
    elif k == " ":
        spawn_particle(storm=False)

scene.bind("keydown", keydown)

# -----------------------------
# Main update functions
# -----------------------------

def update_status():
    counts = {}
    for p in particles:
        counts[p.state] = counts.get(p.state, 0) + 1

    help_line = ""
    if show_help:
        help_line = (
            "\nAI state variables: particles, trapped, funnel, aurora energy, impacts, speed, tilt."
            "\nAI actions: spawn, steer, attach, detach, mark, storm, cleanup, rotate dipole, reset."
            "\nAI modes: " + ", ".join(MagneticWindAI.MODES) + "\n"
        )

    status_text.text = (
        f"Round {round_number} | t={sim_time:5.1f}s | "
        f"{'PAUSED' if paused else 'running'} | AI={'ON' if ai_enabled else 'OFF'} mode={ai.mode} "
        f"| particles={len(particles)} wind={counts.get('wind',0)} deflected={counts.get('deflected',0)} "
        f"trapped={counts.get('trapped',0)} funnel={counts.get('funnel',0)+counts.get('attached',0)+counts.get('marked',0)}\n"
        f"wind speed={solar_wind_speed:3.2f} spawn={spawn_rate:3.1f}/s tilt={dipole_tilt_deg:3.1f}° "
        f"| aurora N={aurora.energy_north:3.1f} S={aurora.energy_south:3.1f} "
        f"| impacts={impact_count} escapes={escaped_count} collisions={collision_count} resets={reset_count}"
        f"{help_line}\n"
    )

def animate_wind_arrows(t):
    for i, arr in enumerate(wind_arrows):
        phase = (t * 0.75 + i * 0.21) % 1.0
        arr.pos.x = -7.55 + phase * 1.1
        arr.axis = vector(0.85 + 0.22 * clamp(solar_wind_speed / 4, 0, 1), 0, 0)
        arr.color = hsv(0.10, 0.78, 0.65 + 0.20 * math.sin(t * 2 + i))

def update_dynamic_objects(step_dt):
    global particles, flashes, marks

    new_particles = []
    for p in particles:
        if p.update(step_dt):
            new_particles.append(p)
    particles = new_particles

    new_flashes = []
    for f in flashes[-FLASH_LIMIT:]:
        if f.update(step_dt):
            new_flashes.append(f)
    for f in flashes[:-FLASH_LIMIT]:
        f.obj.visible = False
    flashes = new_flashes

    new_marks = []
    for m in marks:
        if m.update(step_dt):
            new_marks.append(m)
    marks = new_marks

def spawn_stream(step_dt):
    global spawn_accumulator
    spawn_accumulator += spawn_rate * step_dt
    while spawn_accumulator >= 1.0:
        spawn_particle(storm=(ai.mode in ["STORM", "CHAOS"]))
        spawn_accumulator -= 1.0

# -----------------------------
# Initial particles
# -----------------------------

spawn_burst(26, storm=False)
marks.append(SceneMark(vector(-2.6, 3.2, 0), "AI controller active", vector(0.1, 0.25, 1.0), life=3.0))

# -----------------------------
# Simulation loop
# -----------------------------

while True:
    rate(60)

    if not paused:
        sim_time += dt

        earth.rotate(angle=0.16 * dt, axis=vector(0, 0, 1), origin=vector(0, 0, 0))
        atmosphere.rotate(angle=0.11 * dt, axis=vector(0, 0, 1), origin=vector(0, 0, 0))

        spawn_stream(dt)
        update_dynamic_objects(dt)
        aurora.update(sim_time, dt)
        ai.update(dt)
        animate_wind_arrows(sim_time)

        if len(particles) > PARTICLE_LIMIT:
            cleanup_particles(0.12)

    update_status()
