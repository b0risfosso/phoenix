from vpython import *
import math
import random
import time

# ============================================================
# Two Moving Bar Magnets With Dynamic 3D Field Lines
# VPython self-contained simulation with mouse dragging and AI
# ============================================================

scene = canvas(
    title="Two Moving Bar Magnets With Dynamic 3D Field Lines",
    width=1200,
    height=760,
    background=vector(0.93, 0.96, 1.0),
    center=vector(0, 0, 0.45),
)
scene.forward = vector(-0.45, -0.72, -0.52)
scene.up = vector(0, 0, 1)
scene.range = 5.0
scene.lights = []
distant_light(direction=vector(-0.3, -0.5, -0.8), color=color.white)
distant_light(direction=vector(0.7, 0.2, -0.4), color=vector(0.55, 0.62, 0.75))

# ----------------------------
# Global simulation parameters
# ----------------------------

TRACK_Y_1 = 0.48
TRACK_Y_2 = -0.48
TRACK_Z = 0.22
X_LIMIT = 3.85

MAGNET_LENGTH = 1.55
MAGNET_WIDTH = 0.34
MAGNET_HEIGHT = 0.28
POLE_CHARGE = 1.0

MAG_FORCE_K = 0.40
MAG_TORQUE_K = 0.22
LINE_COUNT_PER_MAGNET = 18
FIELD_POINTS = 72
FIELD_STEP = 0.105
FIELD_RECALC_INTERVAL = 0.22
FIELD_MORPH_SPEED = 5.5

AI_DEFAULT_ENABLED = True

selected_magnet = None
dragging_magnet = None
drag_offset_x = 0.0
physics_paused = False
human_override_until = 0.0
sim_time = 0.0

attached = False
attach_pair = None

random.seed(7)

# ----------------------------
# Utility functions
# ----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m

def lerp_vec(a, b, t):
    return a * (1 - t) + b * t

def lerp_color(a, b, t):
    return vector(a.x * (1 - t) + b.x * t, a.y * (1 - t) + b.y * t, a.z * (1 - t) + b.z * t)

def heat_color(strength):
    s = clamp(math.log(1 + strength * 2.2) / math.log(18), 0, 1)
    c0 = vector(0.18, 0.34, 1.00)
    c1 = vector(0.08, 0.83, 1.00)
    c2 = vector(0.25, 0.95, 0.45)
    c3 = vector(1.00, 0.86, 0.18)
    c4 = vector(1.00, 0.22, 0.16)

    if s < 0.25:
        return lerp_color(c0, c1, s / 0.25)
    elif s < 0.50:
        return lerp_color(c1, c2, (s - 0.25) / 0.25)
    elif s < 0.76:
        return lerp_color(c2, c3, (s - 0.50) / 0.26)
    else:
        return lerp_color(c3, c4, (s - 0.76) / 0.24)

def angle_wrap(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a

def angle_lerp(current, target, gain):
    return current + angle_wrap(target - current) * gain

def fibonacci_sphere(n):
    dirs = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2 if n > 1 else 0
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        dirs.append(vector(x, y, z))
    return dirs

seed_dirs = fibonacci_sphere(LINE_COUNT_PER_MAGNET)

# ----------------------------
# Stationary scenery: rails, floor, guide marks
# ----------------------------

floor = box(
    pos=vector(0, 0, -0.045),
    size=vector(9.0, 3.3, 0.035),
    color=vector(0.86, 0.91, 0.96),
    opacity=0.78,
)

track_objs = []
for yy in (TRACK_Y_1, TRACK_Y_2):
    track_objs.append(box(pos=vector(0, yy - 0.27, 0.02), size=vector(8.2, 0.035, 0.04), color=vector(0.67, 0.72, 0.78)))
    track_objs.append(box(pos=vector(0, yy + 0.27, 0.02), size=vector(8.2, 0.035, 0.04), color=vector(0.67, 0.72, 0.78)))
    track_objs.append(box(pos=vector(-4.08, yy, 0.08), size=vector(0.06, 0.72, 0.16), color=vector(0.92, 0.47, 0.38)))
    track_objs.append(box(pos=vector(4.08, yy, 0.08), size=vector(0.06, 0.72, 0.16), color=vector(0.92, 0.47, 0.38)))

grid_lines = []
for x in [i * 0.5 for i in range(-8, 9)]:
    grid_lines.append(curve(pos=[vector(x, -1.7, -0.018), vector(x, 1.7, -0.018)], radius=0.003, color=vector(0.75, 0.82, 0.88)))
for y in [i * 0.25 for i in range(-6, 7)]:
    grid_lines.append(curve(pos=[vector(-4.2, y, -0.017), vector(4.2, y, -0.017)], radius=0.003, color=vector(0.77, 0.84, 0.90)))

title_label = label(
    pos=vector(0, 1.86, 0.32),
    text="Dynamic 3D magnetic field lines: drag magnets, rotate them, or let the AI play",
    height=13,
    color=vector(0.12, 0.18, 0.24),
    box=False,
    opacity=0,
)

# ----------------------------
# Magnet class
# ----------------------------

class BarMagnet:
    def __init__(self, name, pos, theta, track_y, north_color, south_color):
        self.name = name
        self.pos = vector(pos.x, track_y, TRACK_Z)
        self.theta = theta
        self.track_y = track_y
        self.vel = vector(0, 0, 0)
        self.omega = 0.0
        self.dragged = False

        self.north_color = north_color
        self.south_color = south_color

        self.north_box = box(size=vector(MAGNET_LENGTH / 2, MAGNET_WIDTH, MAGNET_HEIGHT), color=self.north_color)
        self.south_box = box(size=vector(MAGNET_LENGTH / 2, MAGNET_WIDTH, MAGNET_HEIGHT), color=self.south_color)
        self.core = cylinder(radius=MAGNET_WIDTH * 0.57, length=MAGNET_LENGTH * 1.02, color=vector(0.96, 0.96, 0.91), opacity=0.16)
        self.halo = ring(radius=0.46, thickness=0.018, color=vector(1.0, 0.76, 0.18), opacity=0.0)

        self.north_box.owner = self
        self.south_box.owner = self
        self.core.owner = self
        self.halo.owner = self

        self.label_N = label(text="N", height=12, color=vector(0.95, 0.05, 0.05), box=False, opacity=0)
        self.label_S = label(text="S", height=12, color=vector(0.05, 0.18, 0.95), box=False, opacity=0)
        self.name_label = label(text=self.name, height=10, color=vector(0.17, 0.22, 0.28), box=False, opacity=0)

        self.trail = curve(radius=0.012, color=vector(0.18, 0.36, 0.88), opacity=0.34)
        self.trail_timer = 0.0

        self.update_visuals()

    @property
    def axis(self):
        return vector(math.cos(self.theta), math.sin(self.theta), 0)

    @property
    def perp(self):
        a = self.axis
        return vector(-a.y, a.x, 0)

    def pole_position(self, pole_name):
        if pole_name == "N":
            return self.pos + self.axis * (MAGNET_LENGTH / 2)
        return self.pos - self.axis * (MAGNET_LENGTH / 2)

    def poles(self):
        return [
            ("N", self.pole_position("N"), POLE_CHARGE),
            ("S", self.pole_position("S"), -POLE_CHARGE),
        ]

    def set_x(self, x):
        self.pos.x = clamp(x, -X_LIMIT, X_LIMIT)
        self.pos.y = self.track_y
        self.pos.z = TRACK_Z

    def set_theta(self, theta):
        self.theta = angle_wrap(theta)

    def update_visuals(self):
        a = self.axis
        self.pos.y = self.track_y
        self.pos.z = TRACK_Z

        self.north_box.pos = self.pos + a * (MAGNET_LENGTH / 4)
        self.south_box.pos = self.pos - a * (MAGNET_LENGTH / 4)
        self.north_box.axis = a
        self.south_box.axis = a

        self.core.pos = self.pos
        self.core.axis = a * MAGNET_LENGTH

        self.halo.pos = self.pos + vector(0, 0, 0.02)
        self.halo.axis = vector(0, 0, 1)
        self.halo.opacity = 0.42 if selected_magnet is self else 0.0

        npos = self.pole_position("N")
        spos = self.pole_position("S")
        self.label_N.pos = npos + vector(0, 0, 0.31)
        self.label_S.pos = spos + vector(0, 0, 0.31)
        self.name_label.pos = self.pos + vector(0, 0, 0.52)

    def integrate(self, dt):
        if self.dragged:
            self.vel = vector(0, 0, 0)
            self.omega *= 0.6
            return

        self.pos.x += self.vel.x * dt
        self.theta = angle_wrap(self.theta + self.omega * dt)

        if self.pos.x < -X_LIMIT:
            self.pos.x = -X_LIMIT
            self.vel.x = abs(self.vel.x) * 0.76
        elif self.pos.x > X_LIMIT:
            self.pos.x = X_LIMIT
            self.vel.x = -abs(self.vel.x) * 0.76

        self.vel.x *= 0.997
        self.omega *= 0.993
        self.pos.y = self.track_y
        self.pos.z = TRACK_Z

    def update_trail(self, dt):
        self.trail_timer += dt
        if self.trail_timer > 0.06:
            self.trail_timer = 0
            self.trail.append(pos=self.pos + vector(0, 0, 0.07))
            if self.trail.npoints > 420:
                self.trail.pop(0)

    def clear_trail(self):
        self.trail.clear()

m1 = BarMagnet("Magnet A", vector(-1.35, TRACK_Y_1, TRACK_Z), 0.05, TRACK_Y_1, vector(0.95, 0.12, 0.10), vector(0.10, 0.22, 0.95))
m2 = BarMagnet("Magnet B", vector(1.35, TRACK_Y_2, TRACK_Z), math.pi + 0.05, TRACK_Y_2, vector(0.95, 0.12, 0.10), vector(0.10, 0.22, 0.95))
magnets = [m1, m2]
selected_magnet = m1

# ----------------------------
# Field calculation
# ----------------------------

def all_poles():
    poles = []
    for m in magnets:
        for pname, ppos, q in m.poles():
            poles.append((m, pname, ppos, q))
    return poles

def field_at(p):
    B = vector(0, 0, 0)
    for m, pname, ppos, q in all_poles():
        r = p - ppos
        d2 = mag2(r) + 0.018
        B += q * r / (d2 * math.sqrt(d2))
    return B

def nearest_south_distance(p):
    dmin = 999
    for m in magnets:
        dmin = min(dmin, mag(p - m.pole_position("S")))
    return dmin

def generate_field_lines():
    lines = []
    strengths = []
    for m in magnets:
        source = m.pole_position("N")
        for local_dir in seed_dirs:
            start_dir = safe_norm(local_dir)
            p = source + start_dir * 0.175
            line = []
            line_strengths = []

            for i in range(FIELD_POINTS):
                if abs(p.x) > 5.2 or abs(p.y) > 3.2 or p.z < -0.45 or p.z > 3.4:
                    line.append(p)
                    line_strengths.append(0.0)
                    continue

                B = field_at(p)
                strength = mag(B)
                line.append(p)
                line_strengths.append(strength)

                if i > 8 and nearest_south_distance(p) < 0.18:
                    for _ in range(i + 1, FIELD_POINTS):
                        line.append(p)
                        line_strengths.append(strength)
                    break

                p = p + safe_norm(B, start_dir) * FIELD_STEP

            while len(line) < FIELD_POINTS:
                line.append(line[-1])
                line_strengths.append(line_strengths[-1])

            lines.append(line)
            strengths.append(line_strengths)
    return lines, strengths

current_lines, current_strengths = generate_field_lines()
target_lines = [[vector(p.x, p.y, p.z) for p in line] for line in current_lines]
target_strengths = [[s for s in st] for st in current_strengths]

field_curves = []
for line, strengths in zip(current_lines, current_strengths):
    c = curve(radius=0.0095, opacity=0.82)
    for p, s in zip(line, strengths):
        c.append(pos=p, color=heat_color(s))
    field_curves.append(c)

# ----------------------------
# Compass needles / iron-filings style indicators
# ----------------------------

compasses = []
for ix in range(-6, 7, 2):
    for iy in range(-2, 3):
        if abs(iy) == 0 and abs(ix) < 2:
            continue
        p = vector(ix * 0.52, iy * 0.34, 0.08)
        compasses.append(
            arrow(
                pos=p,
                axis=vector(0.20, 0, 0),
                shaftwidth=0.018,
                headwidth=0.055,
                headlength=0.075,
                color=vector(0.32, 0.39, 0.46),
                opacity=0.72,
            )
        )

def update_compasses():
    for ar in compasses:
        B = field_at(ar.pos + vector(0, 0, 0.08))
        s = mag(B)
        ar.axis = safe_norm(B, vector(1, 0, 0)) * clamp(0.10 + 0.06 * math.log(1 + s), 0.10, 0.28)
        ar.color = lerp_color(vector(0.35, 0.40, 0.45), heat_color(s), 0.56)

# ----------------------------
# Attachment bridge and marker particles
# ----------------------------

attach_bridge = curve(radius=0.035, color=vector(0.18, 0.88, 0.55), opacity=0.0)
marker_particles = []

def closest_opposite_poles():
    pairs = []
    for pa_name, pa_pos, qa in m1.poles():
        for pb_name, pb_pos, qb in m2.poles():
            if qa * qb < 0:
                pairs.append((mag(pa_pos - pb_pos), pa_name, pb_name, pa_pos, pb_pos))
    return min(pairs, key=lambda x: x[0])

def try_attach(force=False):
    global attached, attach_pair
    d, a_name, b_name, pa, pb = closest_opposite_poles()
    if force or d < 1.08:
        attached = True
        attach_pair = (a_name, b_name)
        return True
    return False

def detach():
    global attached, attach_pair
    attached = False
    attach_pair = None
    attach_bridge.opacity = 0.0

def update_attach_bridge():
    if not attached or attach_pair is None:
        attach_bridge.opacity = 0.0
        return

    pa = m1.pole_position(attach_pair[0])
    pb = m2.pole_position(attach_pair[1])
    mid = (pa + pb) * 0.5 + vector(0, 0, 0.24 + 0.08 * math.sin(sim_time * 5))
    attach_bridge.clear()
    attach_bridge.append(pos=pa, color=vector(0.10, 0.72, 0.52))
    attach_bridge.append(pos=mid, color=vector(1.00, 0.86, 0.20))
    attach_bridge.append(pos=pb, color=vector(0.10, 0.72, 0.52))
    attach_bridge.opacity = 0.58

def add_marker(p, col=None, radius=0.035, life=5.5):
    if col is None:
        col = heat_color(mag(field_at(p)))
    sph = sphere(pos=p, radius=radius, color=col, opacity=0.62)
    marker_particles.append([sph, life, life])

def update_markers(dt):
    for rec in marker_particles[:]:
        sph, life, maxlife = rec
        life -= dt
        rec[1] = life
        sph.opacity = clamp(0.62 * life / maxlife, 0, 0.62)
        sph.radius *= 0.999
        if life <= 0:
            sph.visible = False
            marker_particles.remove(rec)

    while len(marker_particles) > 120:
        sph, _, _ = marker_particles.pop(0)
        sph.visible = False

def clear_markers():
    for sph, _, _ in marker_particles:
        sph.visible = False
    marker_particles[:] = []

# ----------------------------
# Physics
# ----------------------------

def apply_magnetic_forces(dt):
    F1 = vector(0, 0, 0)
    F2 = vector(0, 0, 0)
    tau1 = 0.0
    tau2 = 0.0

    for name1, p1, q1 in m1.poles():
        for name2, p2, q2 in m2.poles():
            r = p1 - p2
            d2 = mag2(r) + 0.045
            f = MAG_FORCE_K * q1 * q2 * r / (d2 * math.sqrt(d2))
            F1 += f
            F2 -= f
            tau1 += cross(p1 - m1.pos, f).z * MAG_TORQUE_K
            tau2 += cross(p2 - m2.pos, -f).z * MAG_TORQUE_K

    if attached and attach_pair is not None:
        pa = m1.pole_position(attach_pair[0])
        pb = m2.pole_position(attach_pair[1])
        dx = pb.x - pa.x
        relv = m2.vel.x - m1.vel.x
        spring = 2.8 * dx + 0.55 * relv
        F1.x += spring
        F2.x -= spring

        d = mag(pa - pb)
        if d > 1.85:
            detach()

    if not m1.dragged:
        m1.vel.x += F1.x * dt
        m1.omega += tau1 * dt
    if not m2.dragged:
        m2.vel.x += F2.x * dt
        m2.omega += tau2 * dt

    m1.vel.x = clamp(m1.vel.x, -2.2, 2.2)
    m2.vel.x = clamp(m2.vel.x, -2.2, 2.2)
    m1.omega = clamp(m1.omega, -3.0, 3.0)
    m2.omega = clamp(m2.omega, -3.0, 3.0)

def projected_carriage_collision():
    dx = m1.pos.x - m2.pos.x
    if abs(dx) < 0.46 and abs(m1.track_y - m2.track_y) < 1.05:
        push = 0.46 - abs(dx)
        sign = 1 if dx >= 0 else -1
        if not m1.dragged:
            m1.pos.x += sign * push * 0.5
            m1.vel.x = abs(m1.vel.x) * sign + 0.16 * sign
        if not m2.dragged:
            m2.pos.x -= sign * push * 0.5
            m2.vel.x = -abs(m2.vel.x) * sign - 0.16 * sign

def clear_trails():
    for m in magnets:
        m.clear_trail()

# ----------------------------
# Expressive AI controller
# ----------------------------

class AIController:
    def __init__(self):
        self.enabled = AI_DEFAULT_ENABLED
        self.mode = "seek_attract"
        self.modes = [
            "seek_attract",
            "repel_align",
            "pinch_middle",
            "orbit_dance",
            "careful_scan",
            "attach_hold",
            "field_art",
            "chaos",
            "ritual_reset",
        ]
        self.mode_index = 0
        self.mode_time = 0.0
        self.switch_after = 9.0
        self.round = 1
        self.last_signature = None
        self.stagnant_time = 0.0
        self.completion_time = 0.0
        self.marker_timer = 0.0
        self.target_x1 = m1.pos.x
        self.target_x2 = m2.pos.x
        self.target_t1 = m1.theta
        self.target_t2 = m2.theta
        self.chaos_timer = 0.0
        self.scan_dir = 1
        self.loop_wait = 0.0
        self.paused = False

    def read_state(self):
        d_opp, a_name, b_name, pa, pb = closest_opposite_poles()
        sep = abs(m2.pos.x - m1.pos.x)
        same_facing = abs(angle_wrap(m1.theta - m2.theta)) < 0.5
        energy = abs(m1.vel.x) + abs(m2.vel.x) + abs(m1.omega) * 0.25 + abs(m2.omega) * 0.25
        return {
            "x1": m1.pos.x,
            "x2": m2.pos.x,
            "theta1": m1.theta,
            "theta2": m2.theta,
            "v1": m1.vel.x,
            "v2": m2.vel.x,
            "opp_pole_distance": d_opp,
            "closest_pair": (a_name, b_name),
            "separation": sep,
            "same_facing": same_facing,
            "attached": attached,
            "energy": energy,
            "time": sim_time,
        }

    def signature(self):
        return (
            round(m1.pos.x, 2),
            round(m2.pos.x, 2),
            round(angle_wrap(m1.theta), 2),
            round(angle_wrap(m2.theta), 2),
            attached,
        )

    def detect_stagnation_or_completion(self, dt, st):
        sig = self.signature()
        if self.last_signature == sig:
            self.stagnant_time += dt
        else:
            self.stagnant_time = max(0, self.stagnant_time - dt * 1.8)
        self.last_signature = sig

        complete = False
        if attached and st["energy"] < 0.08:
            self.completion_time += dt
            complete = self.completion_time > 4.0
        elif st["energy"] < 0.025 and self.stagnant_time > 6.0:
            complete = True
        elif self.mode_time > 18.0:
            complete = True
        else:
            self.completion_time = max(0, self.completion_time - dt)

        return complete

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.mode_time = 0.0
        self.switch_after = random.uniform(7.0, 13.0)
        self.chaos_timer = 0.0
        self.marker_timer = 0.0

    def set_mode(self, mode):
        if mode in self.modes:
            self.mode = mode
            self.mode_index = self.modes.index(mode)
            self.mode_time = 0.0

    def reset_round(self):
        global attached, attach_pair
        detach()
        clear_markers()
        clear_trails()

        m1.set_x(random.uniform(-2.6, -1.1))
        m2.set_x(random.uniform(1.1, 2.6))
        m1.set_theta(random.choice([0, math.pi, math.pi / 2, -math.pi / 2]) + random.uniform(-0.18, 0.18))
        m2.set_theta(random.choice([0, math.pi, math.pi / 2, -math.pi / 2]) + random.uniform(-0.18, 0.18))

        m1.vel = vector(random.uniform(-0.16, 0.16), 0, 0)
        m2.vel = vector(random.uniform(-0.16, 0.16), 0, 0)
        m1.omega = random.uniform(-0.35, 0.35)
        m2.omega = random.uniform(-0.35, 0.35)

        self.round += 1
        self.stagnant_time = 0
        self.completion_time = 0
        self.mode_index = random.randrange(0, len(self.modes) - 1)
        self.mode = self.modes[self.mode_index]
        self.mode_time = 0
        self.loop_wait = 0

        for _ in range(10):
            add_marker(vector(random.uniform(-2, 2), random.uniform(-0.8, 0.8), random.uniform(0.15, 0.65)),
                       col=vector(0.95, 0.72, 0.25), radius=random.uniform(0.018, 0.035), life=random.uniform(2, 5))

    def choose_actions(self, st, dt):
        t = sim_time
        self.target_x1 = m1.pos.x
        self.target_x2 = m2.pos.x
        self.target_t1 = m1.theta
        self.target_t2 = m2.theta

        if self.mode == "seek_attract":
            self.target_x1 = -0.62 + 0.10 * math.sin(t * 0.9)
            self.target_x2 = 0.62 + 0.10 * math.sin(t * 0.9 + math.pi)
            self.target_t1 = 0.0
            self.target_t2 = 0.0
            if st["opp_pole_distance"] < 0.72:
                try_attach()

        elif self.mode == "repel_align":
            detach()
            self.target_x1 = -0.45 + 0.06 * math.sin(t * 1.7)
            self.target_x2 = 0.45 - 0.06 * math.sin(t * 1.7)
            self.target_t1 = 0.0
            self.target_t2 = math.pi
            if st["separation"] < 0.9:
                m1.vel.x -= 0.22 * dt
                m2.vel.x += 0.22 * dt

        elif self.mode == "pinch_middle":
            detach()
            self.target_x1 = -0.24 + 0.20 * math.sin(t * 0.8)
            self.target_x2 = 0.24 + 0.20 * math.sin(t * 0.8 + math.pi)
            self.target_t1 = math.pi / 2 + 0.45 * math.sin(t * 1.1)
            self.target_t2 = -math.pi / 2 + 0.45 * math.sin(t * 1.1 + math.pi)
            self.marker_timer += dt
            if self.marker_timer > 0.22:
                self.marker_timer = 0
                add_marker(vector(0, 0, 0.35 + 0.15 * math.sin(t * 3)), radius=0.024, life=3.8)

        elif self.mode == "orbit_dance":
            detach()
            phase = t * 0.85
            self.target_x1 = -1.25 + 1.0 * math.sin(phase)
            self.target_x2 = 1.25 + 1.0 * math.sin(phase + math.pi)
            self.target_t1 = phase + math.pi / 2
            self.target_t2 = -phase + math.pi / 2
            self.marker_timer += dt
            if self.marker_timer > 0.30:
                self.marker_timer = 0
                add_marker(m1.pos + vector(0, 0, 0.27), col=vector(0.45, 0.62, 1.0), radius=0.022, life=4.2)
                add_marker(m2.pos + vector(0, 0, 0.27), col=vector(1.0, 0.42, 0.38), radius=0.022, life=4.2)

        elif self.mode == "careful_scan":
            detach()
            self.target_x1 = -2.25
            self.target_t1 = 0.0
            self.target_x2 = 2.35 * math.sin(t * 0.36)
            self.target_t2 = t * 0.78
            if abs(m2.pos.x) > 2.22:
                self.scan_dir *= -1

        elif self.mode == "attach_hold":
            self.target_x1 = -0.52
            self.target_x2 = 0.52
            self.target_t1 = 0.0
            self.target_t2 = 0.0
            if st["opp_pole_distance"] < 1.15 or self.mode_time > 2.5:
                try_attach(force=True)
            if attached:
                sway = 0.72 * math.sin(t * 0.55)
                self.target_x1 = -0.25 + sway
                self.target_x2 = 0.25 + sway
                self.target_t1 = 0.25 * math.sin(t * 1.2)
                self.target_t2 = 0.25 * math.sin(t * 1.2)

        elif self.mode == "field_art":
            detach()
            self.target_x1 = -1.55 + 0.85 * math.sin(t * 0.73)
            self.target_x2 = 1.55 + 0.85 * math.sin(t * 0.51 + 1.2)
            self.target_t1 = 1.8 * math.sin(t * 0.62)
            self.target_t2 = 1.8 * math.cos(t * 0.57)
            self.marker_timer += dt
            if self.marker_timer > 0.10:
                self.marker_timer = 0
                p = vector(
                    0.5 * (m1.pos.x + m2.pos.x) + random.uniform(-0.12, 0.12),
                    random.uniform(-0.62, 0.62),
                    random.uniform(0.25, 1.1),
                )
                add_marker(p, radius=random.uniform(0.014, 0.028), life=random.uniform(2.5, 6.0))

        elif self.mode == "chaos":
            detach()
            self.chaos_timer -= dt
            if self.chaos_timer <= 0:
                self.chaos_timer = random.uniform(0.45, 1.15)
                self.target_x1 = random.uniform(-3.2, 3.2)
                self.target_x2 = random.uniform(-3.2, 3.2)
                self.target_t1 = random.uniform(-math.pi, math.pi)
                self.target_t2 = random.uniform(-math.pi, math.pi)
                m1.vel.x += random.uniform(-0.55, 0.55)
                m2.vel.x += random.uniform(-0.55, 0.55)
                m1.omega += random.uniform(-1.2, 1.2)
                m2.omega += random.uniform(-1.2, 1.2)
                for _ in range(4):
                    add_marker(vector(random.uniform(-3, 3), random.uniform(-0.9, 0.9), random.uniform(0.15, 1.0)),
                               col=random.choice([vector(1, 0.35, 0.25), vector(0.25, 0.75, 1), vector(1, 0.84, 0.18)]),
                               radius=random.uniform(0.014, 0.03), life=random.uniform(1.8, 4.5))
            else:
                self.target_x1 = m1.pos.x
                self.target_x2 = m2.pos.x
                self.target_t1 = m1.theta
                self.target_t2 = m2.theta

        elif self.mode == "ritual_reset":
            detach()
            self.target_x1 = -2.1 + 0.22 * math.sin(t * 2.0)
            self.target_x2 = 2.1 + 0.22 * math.sin(t * 2.0 + math.pi)
            self.target_t1 = t * 1.5
            self.target_t2 = -t * 1.5
            if self.mode_time > 4.0:
                self.reset_round()

    def apply_actions(self, dt):
        if time.perf_counter() < human_override_until or dragging_magnet is not None:
            return

        kx = 4.2
        kv = 1.15
        kt = 4.5
        ko = 1.25

        if not m1.dragged:
            ax1 = (self.target_x1 - m1.pos.x) * kx - m1.vel.x * kv
            m1.vel.x += clamp(ax1, -5.0, 5.0) * dt
            ao1 = angle_wrap(self.target_t1 - m1.theta) * kt - m1.omega * ko
            m1.omega += clamp(ao1, -6.0, 6.0) * dt

        if not m2.dragged:
            ax2 = (self.target_x2 - m2.pos.x) * kx - m2.vel.x * kv
            m2.vel.x += clamp(ax2, -5.0, 5.0) * dt
            ao2 = angle_wrap(self.target_t2 - m2.theta) * kt - m2.omega * ko
            m2.omega += clamp(ao2, -6.0, 6.0) * dt

    def update(self, dt):
        if not self.enabled or self.paused:
            return

        self.mode_time += dt
        st = self.read_state()
        complete = self.detect_stagnation_or_completion(dt, st)

        if complete:
            self.loop_wait += dt
            if self.loop_wait > 1.25:
                self.next_mode()
                if random.random() < 0.36 or self.stagnant_time > 7.5:
                    self.reset_round()
                self.loop_wait = 0
        elif self.mode_time > self.switch_after:
            self.next_mode()

        self.choose_actions(st, dt)
        self.apply_actions(dt)

ai = AIController()

# ----------------------------
# Mouse and keyboard control
# ----------------------------

def human_override(seconds=2.5):
    global human_override_until
    human_override_until = time.perf_counter() + seconds

def on_mouse_down(evt):
    global dragging_magnet, selected_magnet, drag_offset_x
    obj = scene.mouse.pick
    if obj is not None and hasattr(obj, "owner"):
        dragging_magnet = obj.owner
        selected_magnet = dragging_magnet
        dragging_magnet.dragged = True
        p = scene.mouse.project(normal=vector(0, 0, 1), d=TRACK_Z)
        if p is not None:
            drag_offset_x = dragging_magnet.pos.x - p.x
        else:
            drag_offset_x = 0
        human_override(3.0)

def on_mouse_move(evt):
    global dragging_magnet
    if dragging_magnet is not None:
        p = scene.mouse.project(normal=vector(0, 0, 1), d=TRACK_Z)
        if p is not None:
            dragging_magnet.set_x(p.x + drag_offset_x)
            dragging_magnet.vel = vector(0, 0, 0)
            human_override(1.0)

def on_mouse_up(evt):
    global dragging_magnet
    if dragging_magnet is not None:
        dragging_magnet.dragged = False
    dragging_magnet = None

def on_key_down(evt):
    global selected_magnet, physics_paused
    key = evt.key.lower()
    human_override(2.6)

    if key == "1":
        selected_magnet = m1
    elif key == "2":
        selected_magnet = m2
    elif key == "left":
        selected_magnet.vel.x -= 0.55
    elif key == "right":
        selected_magnet.vel.x += 0.55
    elif key == "q":
        selected_magnet.omega += 0.75
    elif key == "e":
        selected_magnet.omega -= 0.75
    elif key == "f":
        selected_magnet.set_theta(selected_magnet.theta + math.pi)
    elif key == "d":
        if attached:
            detach()
        else:
            try_attach(force=True)
    elif key == "a":
        ai.enabled = not ai.enabled
    elif key == "p":
        physics_paused = not physics_paused
    elif key == "i":
        ai.paused = not ai.paused
    elif key == "m":
        ai.next_mode()
    elif key == "r":
        ai.reset_round()
    elif key == "c":
        clear_trails()
        clear_markers()
    elif key == "s":
        m1.vel = vector(0, 0, 0)
        m2.vel = vector(0, 0, 0)
        m1.omega = 0
        m2.omega = 0

scene.bind("mousedown", on_mouse_down)
scene.bind("mousemove", on_mouse_move)
scene.bind("mouseup", on_mouse_up)
scene.bind("keydown", on_key_down)

# ----------------------------
# Reset and status
# ----------------------------

def update_status_caption():
    ai_state = "ON" if ai.enabled else "OFF"
    ai_pause = "paused" if ai.paused else "running"
    sim_pause = "PAUSED" if physics_paused else "live"
    attach_state = "attached" if attached else "free"
    selected = selected_magnet.name if selected_magnet else "none"
    override_left = max(0, human_override_until - time.perf_counter())

    scene.caption = (
        "\n"
        "Controls: drag a magnet with mouse | 1/2 select | Left/Right push | Q/E rotate | F flip | D attach/detach\n"
        "A toggle AI | I pause AI only | M next AI behavior | P pause simulation | R reset round | C clear trails/marks | S stop motion\n"
        f"Status: simulation {sim_pause} | AI {ai_state} ({ai_pause}) | mode '{ai.mode}' | round {ai.round} | magnets {attach_state} | selected {selected}"
        + (f" | human override {override_left:0.1f}s" if override_left > 0 else "")
        + "\n"
    )

# ----------------------------
# Main loop
# ----------------------------

last_time = time.perf_counter()
field_timer = 0.0
caption_timer = 0.0

while True:
    rate(60)
    now = time.perf_counter()
    dt = clamp(now - last_time, 0.001, 0.045)
    last_time = now
    sim_time += dt

    if dragging_magnet is not None:
        p = scene.mouse.project(normal=vector(0, 0, 1), d=TRACK_Z)
        if p is not None:
            dragging_magnet.set_x(p.x + drag_offset_x)
            dragging_magnet.vel = vector(0, 0, 0)

    if not physics_paused:
        ai.update(dt)
        apply_magnetic_forces(dt)

        for m in magnets:
            m.integrate(dt)

        projected_carriage_collision()

    for m in magnets:
        m.update_visuals()
        if not physics_paused:
            m.update_trail(dt)

    update_attach_bridge()
    update_markers(dt)

    field_timer += dt
    if field_timer >= FIELD_RECALC_INTERVAL:
        field_timer = 0.0
        target_lines, target_strengths = generate_field_lines()

    morph = clamp(FIELD_MORPH_SPEED * dt, 0, 1)
    for li, c in enumerate(field_curves):
        line = current_lines[li]
        target = target_lines[li]
        strengths = target_strengths[li]
        for pi in range(FIELD_POINTS):
            line[pi] = lerp_vec(line[pi], target[pi], morph)
            c.modify(pi, pos=line[pi], color=heat_color(strengths[pi]))

    if int(sim_time * 15) % 2 == 0:
        update_compasses()

    caption_timer += dt
    if caption_timer > 0.25:
        caption_timer = 0
        update_status_caption()
