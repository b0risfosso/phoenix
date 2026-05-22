from vpython import *
import random as pyrandom
import math

# Rising Hot Air Balloon Fleet
# Self-contained VPython simulation with built-in human controls and expressive AI controller.

scene = canvas(
    title="Rising Hot Air Balloon Fleet - AI Controlled 3D Simulation",
    width=1100,
    height=720,
    background=vector(0.82, 0.93, 1.0),
)
scene.autoscale = False
scene.range = 24
scene.center = vector(0, 9, 0)
scene.forward = vector(-0.35, -0.25, -1)

scene.caption = """
Controls:
  P / Space : pause or resume
  I         : toggle AI controller
  M         : switch AI behavior mode
  R         : reset round
  Tab       : select next balloon
  Arrow keys: push selected balloon left/right/up/down
  W / S     : push selected balloon forward/back
  C         : attach selected balloon to nearest, or detach if already tethered
  X         : detach selected balloon from all tethers
  B         : vent warm-air particles / mark path
  G         : create a gust
  O         : toggle horizontal world wrapping
  H         : hide/show help caption
"""

# ---------------------------------------------------------------------
# World constants
# ---------------------------------------------------------------------

WORLD_X = 18.0
WORLD_Z = 12.0
FLOOR_Y = -3.0
CEILING_Y = 25.0
DT = 0.02
MAX_BALLOONS = 10
MAX_TETHERS = 14

paused = False
show_caption = True
wrap_enabled = False
sim_time = 0.0
frame_count = 0
selected_index = 0

balloons = []
tethers = []
particles = []
wind_arrows = []
clouds = []

base_wind = vector(0.8, 0, 0.15)
target_wind = vector(0.8, 0, 0.15)

# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v):
    if mag(v) < 1e-7:
        return vector(0, 0, 0)
    return norm(v)

def lerp(a, b, t):
    return a * (1 - t) + b * t

def random_color():
    h = pyrandom.random()
    return color.hsv_to_rgb(vector(h, 0.62, 0.95))

def horizontal(v):
    return vector(v.x, 0, v.z)

def distance(a, b):
    return mag(a - b)

def invisible(obj):
    try:
        obj.visible = False
    except Exception:
        pass

# ---------------------------------------------------------------------
# Stationary scene objects
# ---------------------------------------------------------------------

floor = box(
    pos=vector(0, FLOOR_Y - 0.05, 0),
    size=vector(WORLD_X * 2.25, 0.1, WORLD_Z * 2.25),
    color=vector(0.72, 0.88, 0.72),
    opacity=0.35,
)

floor_grid = []
for x in range(-18, 19, 3):
    floor_grid.append(curve(
        pos=[vector(x, FLOOR_Y + 0.015, -WORLD_Z), vector(x, FLOOR_Y + 0.015, WORLD_Z)],
        radius=0.01,
        color=vector(0.55, 0.72, 0.62),
    ))
for z in range(-12, 13, 3):
    floor_grid.append(curve(
        pos=[vector(-WORLD_X, FLOOR_Y + 0.018, z), vector(WORLD_X, FLOOR_Y + 0.018, z)],
        radius=0.01,
        color=vector(0.55, 0.72, 0.62),
    ))

boundary_color = vector(0.75, 0.85, 1.0)
for x in [-WORLD_X, WORLD_X]:
    curve(pos=[vector(x, FLOOR_Y, -WORLD_Z), vector(x, CEILING_Y, -WORLD_Z)], radius=0.025, color=boundary_color)
    curve(pos=[vector(x, FLOOR_Y, WORLD_Z), vector(x, CEILING_Y, WORLD_Z)], radius=0.025, color=boundary_color)
for z in [-WORLD_Z, WORLD_Z]:
    curve(pos=[vector(-WORLD_X, FLOOR_Y, z), vector(-WORLD_X, CEILING_Y, z)], radius=0.025, color=boundary_color)
    curve(pos=[vector(WORLD_X, FLOOR_Y, z), vector(WORLD_X, CEILING_Y, z)], radius=0.025, color=boundary_color)

maypole = cylinder(
    pos=vector(0, FLOOR_Y, 0),
    axis=vector(0, CEILING_Y - FLOOR_Y, 0),
    radius=0.04,
    color=vector(1.0, 0.85, 0.35),
    opacity=0.45,
)

sun = sphere(
    pos=vector(-13, 23, -10),
    radius=1.3,
    color=vector(1.0, 0.86, 0.32),
    emissive=True,
    opacity=0.75,
)

for i in range(9):
    c = sphere(
        pos=vector(
            pyrandom.uniform(-16, 16),
            pyrandom.uniform(17, 26),
            pyrandom.uniform(-11, 8),
        ),
        radius=pyrandom.uniform(1.0, 2.4),
        color=color.white,
        opacity=0.18,
    )
    clouds.append(c)

hud = label(
    pos=vector(-WORLD_X - 0.7, CEILING_Y + 1.2, -WORLD_Z),
    text="",
    height=13,
    color=vector(0.08, 0.16, 0.22),
    box=False,
    line=False,
    align="left",
)

mode_label = label(
    pos=vector(0, CEILING_Y + 1.4, 0),
    text="",
    height=18,
    color=vector(0.15, 0.22, 0.28),
    box=False,
    line=False,
)

# ---------------------------------------------------------------------
# Wind field
# ---------------------------------------------------------------------

def wind_at(pos, t=None):
    if t is None:
        t = sim_time

    shear = vector(
        0.45 * math.sin(0.18 * pos.y + 0.8 * math.sin(t * 0.37)),
        0,
        0.32 * math.cos(0.14 * pos.y + 0.21 * pos.x + t * 0.45),
    )

    swirl_center = vector(0, pos.y, 0)
    radial = pos - swirl_center
    tangent = vector(-radial.z, 0, radial.x)
    swirl = safe_norm(tangent) * (0.34 * math.sin(t * 0.25 + pos.y * 0.1))

    thermal = vector(0, 0.0, 0)
    return base_wind + shear + swirl + thermal

def make_wind_arrows():
    global wind_arrows
    for a in wind_arrows:
        invisible(a)
    wind_arrows = []

    for y in [2.0, 7.5, 13.0, 18.5]:
        for x in [-13, -5, 3, 11]:
            for z in [-8, 0, 8]:
                p = vector(x, y, z)
                a = arrow(
                    pos=p,
                    axis=vector(1.1, 0, 0),
                    shaftwidth=0.065,
                    headwidth=0.26,
                    headlength=0.38,
                    color=vector(0.22, 0.55, 1.0),
                    opacity=0.44,
                )
                wind_arrows.append(a)

def update_wind_arrows():
    for a in wind_arrows:
        w = wind_at(a.pos)
        h = horizontal(w)
        if mag(h) < 0.08:
            h = vector(0.08, 0, 0)
        a.axis = h * 0.9
        strength = clamp(mag(h) / 3.0, 0.0, 1.0)
        a.color = lerp(vector(0.35, 0.68, 1.0), vector(1.0, 0.55, 0.22), strength)

make_wind_arrows()

# ---------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------

class Particle:
    def __init__(self, pos, vel, col, radius=0.08, ttl=2.0, opacity=0.6):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.ttl = ttl
        self.max_ttl = ttl
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=col,
            opacity=opacity,
            emissive=True,
        )

    def update(self, dt):
        self.ttl -= dt
        self.vel += vector(0, 0.06, 0) * dt
        self.vel *= 0.992
        self.pos += self.vel * dt
        self.obj.pos = self.pos
        self.obj.opacity = clamp(0.65 * self.ttl / self.max_ttl, 0, 0.65)
        if self.ttl <= 0:
            invisible(self.obj)
            return False
        return True

# ---------------------------------------------------------------------
# Balloon class
# ---------------------------------------------------------------------

class Balloon:
    def __init__(self, ident, pos, radius, col):
        self.ident = ident
        self.pos = vector(pos)
        self.radius = radius
        self.color = vector(col)
        self.mass = radius ** 3 * 0.55
        self.vel = vector(
            pyrandom.uniform(-0.5, 0.5),
            pyrandom.uniform(0.15, 0.8),
            pyrandom.uniform(-0.35, 0.35),
        )
        self.force = vector(0, 0, 0)
        self.warmth = pyrandom.uniform(0.88, 1.18)
        self.spin = pyrandom.uniform(0, 6.283)
        self.trail_timer = pyrandom.random() * 0.2
        self.last_mark = 0.0
        self.completed_once = False

        self.shell = sphere(
            pos=self.pos,
            radius=radius,
            color=self.color,
            opacity=0.38,
            shininess=0.75,
        )
        self.inner = sphere(
            pos=self.pos,
            radius=radius * 0.58,
            color=vector(1.0, 0.55, 0.18),
            opacity=0.22,
            emissive=True,
        )
        self.seam = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=radius * 1.012,
            thickness=0.025,
            color=self.color,
            opacity=0.62,
        )
        self.top_patch = sphere(
            pos=self.pos + vector(0, radius * 0.92, 0),
            radius=radius * 0.17,
            color=lerp(self.color, color.white, 0.45),
            opacity=0.5,
        )

        basket_y = -radius - 0.82
        self.basket = box(
            pos=self.pos + vector(0, basket_y, 0),
            size=vector(radius * 0.72, radius * 0.45, radius * 0.55),
            color=vector(0.58, 0.35, 0.18),
            opacity=0.92,
        )

        self.ropes = []
        rope_color = vector(0.72, 0.56, 0.36)
        for sx in [-1, 1]:
            for sz in [-1, 1]:
                r = cylinder(
                    pos=self.pos,
                    axis=vector(0, -1, 0),
                    radius=0.018,
                    color=rope_color,
                    opacity=0.85,
                )
                self.ropes.append((r, sx, sz))

        self.trail = curve(color=lerp(self.color, color.white, 0.1), radius=0.028)
        self.name = label(
            pos=self.pos + vector(0, radius + 0.55, 0),
            text=f"B{ident}",
            height=10,
            color=vector(0.06, 0.1, 0.14),
            box=False,
            line=False,
            opacity=0,
        )

        self.selection_ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=radius * 1.22,
            thickness=0.035,
            color=vector(1.0, 0.95, 0.25),
            opacity=0.0,
        )

    def hide(self):
        for obj in [self.shell, self.inner, self.seam, self.top_patch, self.basket,
                    self.trail, self.name, self.selection_ring]:
            invisible(obj)
        for r, _, _ in self.ropes:
            invisible(r)

    def add_force(self, f):
        self.force += f

    def basket_pos(self):
        return self.pos + vector(0, -self.radius - 0.82, 0)

    def vent(self, amount=7, hot=True):
        global particles
        self.warmth = clamp(self.warmth - 0.006 * amount, 0.72, 1.28)
        for _ in range(amount):
            angle = pyrandom.uniform(0, 6.283)
            spread = pyrandom.uniform(0.0, self.radius * 0.5)
            p = self.pos + vector(
                math.cos(angle) * spread,
                -self.radius * 0.35,
                math.sin(angle) * spread,
            )
            v = self.vel * 0.35 + vector(
                pyrandom.uniform(-0.45, 0.45),
                pyrandom.uniform(-0.2, 0.8),
                pyrandom.uniform(-0.45, 0.45),
            )
            col = vector(1.0, pyrandom.uniform(0.42, 0.78), 0.16) if hot else self.color
            particles.append(Particle(p, v, col, radius=pyrandom.uniform(0.035, 0.09), ttl=pyrandom.uniform(1.1, 2.7)))

    def integrate(self, dt):
        local_wind = wind_at(self.pos)

        lift = vector(0, 0.56 * self.warmth, 0)
        drag = -0.18 * self.vel
        wind_drag = (horizontal(local_wind) - horizontal(self.vel)) * 0.34

        # Warm thermals lift balloons more near the center and above the floor.
        thermal_strength = 0.23 * math.exp(-(self.pos.x ** 2 + self.pos.z ** 2) / 160.0)
        thermal = vector(0, thermal_strength, 0)

        accel = lift + wind_drag + drag + thermal + self.force / max(self.mass, 0.1)
        self.vel += accel * dt

        max_speed = 6.2
        if mag(self.vel) > max_speed:
            self.vel = norm(self.vel) * max_speed

        self.pos += self.vel * dt

        # Heat slowly breathes: rising hot air spheres pulse visibly.
        self.warmth += 0.012 * math.sin(sim_time * 0.8 + self.ident) * dt
        self.warmth = clamp(self.warmth, 0.68, 1.35)

        self.spin += (0.45 + 0.15 * mag(horizontal(self.vel))) * dt

    def enforce_world(self):
        global particles

        if wrap_enabled:
            wrapped = False
            if self.pos.x > WORLD_X:
                self.pos.x = -WORLD_X
                wrapped = True
            elif self.pos.x < -WORLD_X:
                self.pos.x = WORLD_X
                wrapped = True
            if self.pos.z > WORLD_Z:
                self.pos.z = -WORLD_Z
                wrapped = True
            elif self.pos.z < -WORLD_Z:
                self.pos.z = WORLD_Z
                wrapped = True
            if wrapped:
                self.vent(5, hot=False)
                self.trail.append(pos=self.pos)
        else:
            if self.pos.x > WORLD_X - self.radius:
                self.pos.x = WORLD_X - self.radius
                self.vel.x = -abs(self.vel.x) * 0.72
                self.vent(2, hot=False)
            elif self.pos.x < -WORLD_X + self.radius:
                self.pos.x = -WORLD_X + self.radius
                self.vel.x = abs(self.vel.x) * 0.72
                self.vent(2, hot=False)

            if self.pos.z > WORLD_Z - self.radius:
                self.pos.z = WORLD_Z - self.radius
                self.vel.z = -abs(self.vel.z) * 0.72
                self.vent(2, hot=False)
            elif self.pos.z < -WORLD_Z + self.radius:
                self.pos.z = -WORLD_Z + self.radius
                self.vel.z = abs(self.vel.z) * 0.72
                self.vent(2, hot=False)

        if self.pos.y < FLOOR_Y + self.radius:
            self.pos.y = FLOOR_Y + self.radius
            self.vel.y = abs(self.vel.y) * 0.62 + 0.18
            self.vent(3, hot=True)

        if self.pos.y > CEILING_Y - 0.7 and not self.completed_once:
            self.completed_once = True
            self.vent(10, hot=True)

    def update_graphics(self, selected=False):
        self.shell.pos = self.pos
        self.inner.pos = self.pos
        self.inner.radius = self.radius * (0.48 + 0.14 * self.warmth)
        self.inner.opacity = clamp(0.12 + 0.13 * self.warmth, 0.12, 0.34)
        self.inner.color = lerp(vector(1.0, 0.35, 0.08), vector(1.0, 0.86, 0.2), clamp(self.warmth - 0.7, 0, 0.7))

        self.seam.pos = self.pos
        self.seam.axis = safe_norm(vector(math.cos(self.spin), 0.38, math.sin(self.spin)))
        self.top_patch.pos = self.pos + vector(0, self.radius * 0.92, 0)

        bpos = self.basket_pos()
        self.basket.pos = bpos
        horizontal_axis = horizontal(self.vel)
        if mag(horizontal_axis) > 0.05:
            self.basket.axis = safe_norm(vector(1, 0, 0) + horizontal_axis * 0.08)

        for r, sx, sz in self.ropes:
            top = self.pos + vector(sx * self.radius * 0.38, -self.radius * 0.62, sz * self.radius * 0.28)
            bottom = bpos + vector(sx * self.radius * 0.34, self.radius * 0.22, sz * self.radius * 0.25)
            r.pos = top
            r.axis = bottom - top

        self.name.pos = self.pos + vector(0, self.radius + 0.56, 0)
        self.selection_ring.pos = self.pos
        self.selection_ring.opacity = 0.78 if selected else 0.0

        self.trail_timer += DT
        if self.trail_timer >= 0.12:
            self.trail.append(pos=self.pos)
            self.trail_timer = 0.0

# ---------------------------------------------------------------------
# Tethers: attach, detach, transfer warmth, pull balloons together
# ---------------------------------------------------------------------

class Tether:
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.rest = clamp(distance(a.basket_pos(), b.basket_pos()), 2.5, 7.0)
        self.k = 0.52
        self.damping = 0.08
        self.line = cylinder(
            pos=a.basket_pos(),
            axis=b.basket_pos() - a.basket_pos(),
            radius=0.028,
            color=vector(0.50, 0.38, 0.24),
            opacity=0.72,
        )

    def involves(self, balloon):
        return self.a is balloon or self.b is balloon

    def other(self, balloon):
        if self.a is balloon:
            return self.b
        if self.b is balloon:
            return self.a
        return None

    def apply(self):
        pa = self.a.basket_pos()
        pb = self.b.basket_pos()
        dvec = pb - pa
        d = mag(dvec)
        if d < 1e-6:
            return
        n = dvec / d
        ext = d - self.rest
        rel = dot(self.b.vel - self.a.vel, n)
        f = (self.k * ext + self.damping * rel) * n
        self.a.add_force(f)
        self.b.add_force(-f)

        # Attached balloons mix and transfer warm air gradually.
        heat_delta = (self.b.warmth - self.a.warmth) * 0.008
        self.a.warmth += heat_delta
        self.b.warmth -= heat_delta

    def update_graphics(self):
        pa = self.a.basket_pos()
        pb = self.b.basket_pos()
        self.line.pos = pa
        self.line.axis = pb - pa

    def hide(self):
        invisible(self.line)

def tether_between(a, b):
    for t in tethers:
        if (t.a is a and t.b is b) or (t.a is b and t.b is a):
            return t
    return None

def attach_pair(a, b):
    if a is b:
        return None
    existing = tether_between(a, b)
    if existing:
        return existing
    if len(tethers) >= MAX_TETHERS:
        return None
    t = Tether(a, b)
    tethers.append(t)
    return t

def detach_tether(t):
    if t in tethers:
        t.hide()
        tethers.remove(t)

def detach_balloon(balloon):
    for t in list(tethers):
        if t.involves(balloon):
            detach_tether(t)

def nearest_balloon(balloon):
    best = None
    best_d = 99999
    for other in balloons:
        if other is balloon:
            continue
        d = distance(balloon.pos, other.pos)
        if d < best_d:
            best = other
            best_d = d
    return best, best_d

# ---------------------------------------------------------------------
# Physics interactions
# ---------------------------------------------------------------------

def handle_collisions():
    for i in range(len(balloons)):
        for j in range(i + 1, len(balloons)):
            a = balloons[i]
            b = balloons[j]
            delta = b.pos - a.pos
            d = mag(delta)
            min_d = a.radius + b.radius
            if d <= 1e-7:
                n = vector(1, 0, 0)
                d = 1e-7
            else:
                n = delta / d

            if d < min_d:
                overlap = min_d - d
                total_mass = a.mass + b.mass
                a.pos -= n * overlap * (b.mass / total_mass) * 0.92
                b.pos += n * overlap * (a.mass / total_mass) * 0.92

                rel = b.vel - a.vel
                rel_n = dot(rel, n)
                if rel_n < 0:
                    restitution = 0.74
                    impulse = -(1 + restitution) * rel_n / (1 / a.mass + 1 / b.mass)
                    a.vel -= impulse * n / a.mass
                    b.vel += impulse * n / b.mass

                    mix_heat = (a.warmth + b.warmth) * 0.5
                    a.warmth = lerp(a.warmth, mix_heat, 0.04)
                    b.warmth = lerp(b.warmth, mix_heat, 0.04)

                    if pyrandom.random() < 0.18:
                        p = (a.pos + b.pos) * 0.5
                        particles.append(Particle(
                            p,
                            n * pyrandom.uniform(0.4, 1.2) + vector(0, 0.25, 0),
                            lerp(a.color, b.color, 0.5),
                            radius=0.055,
                            ttl=1.2,
                            opacity=0.5,
                        ))

# ---------------------------------------------------------------------
# Reset / round setup
# ---------------------------------------------------------------------

def clear_dynamic_objects():
    for b in balloons:
        b.hide()
    for t in tethers:
        t.hide()
    for p in particles:
        invisible(p.obj)
    balloons.clear()
    tethers.clear()
    particles.clear()

def spawn_balloons(count=MAX_BALLOONS):
    attempts = 0
    while len(balloons) < count and attempts < 600:
        attempts += 1
        r = pyrandom.uniform(1.0, 1.55)
        p = vector(
            pyrandom.uniform(-WORLD_X + 3, WORLD_X - 3),
            pyrandom.uniform(FLOOR_Y + r + 0.2, FLOOR_Y + r + 5.0),
            pyrandom.uniform(-WORLD_Z + 2.5, WORLD_Z - 2.5),
        )
        ok = True
        for b in balloons:
            if distance(p, b.pos) < r + b.radius + 0.8:
                ok = False
                break
        if ok:
            balloons.append(Balloon(len(balloons) + 1, p, r, random_color()))

def reset_world(reason="new round"):
    global base_wind, target_wind, selected_index, wrap_enabled
    clear_dynamic_objects()
    selected_index = 0
    wrap_enabled = False
    base_wind = vector(pyrandom.uniform(-0.6, 0.9), 0, pyrandom.uniform(-0.25, 0.25))
    target_wind = vector(pyrandom.uniform(-0.8, 1.2), 0, pyrandom.uniform(-0.35, 0.35))
    spawn_balloons(MAX_BALLOONS)
    if ai is not None:
        ai.on_reset(reason)

# ---------------------------------------------------------------------
# Expressive AI Controller
# ---------------------------------------------------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.modes = [
            "GENTLE_ASCENT",
            "SIDEWAYS_PARADE",
            "ORBIT_MAYPOLE",
            "ORGANIZE_CLUSTER",
            "CHAOTIC_GUSTS",
            "ARTIST_SPIRAL",
            "DIP_AND_RECOVER",
            "WRAP_DANCE",
        ]
        self.mode = "GENTLE_ASCENT"
        self.mode_index = 0
        self.mode_elapsed = 0.0
        self.mode_duration = 8.0
        self.round = 1
        self.override_until = 0.0
        self.last_random_gust = 0.0
        self.recent_modes = []
        self.prev_avg_y = None
        self.prev_state_check = 0.0
        self.stagnant_time = 0.0
        self.completion_time = 0.0
        self.completed = False
        self.ritual_angle = 0.0

    def on_reset(self, reason=""):
        self.round += 1
        self.mode_elapsed = 0.0
        self.mode_duration = pyrandom.uniform(6.0, 10.0)
        self.prev_avg_y = None
        self.prev_state_check = sim_time
        self.stagnant_time = 0.0
        self.completion_time = 0.0
        self.completed = False
        self.pick_mode(force=True)

    def human_override(self, seconds=2.0):
        self.override_until = max(self.override_until, sim_time + seconds)

    def read_state(self):
        if not balloons:
            return {
                "count": 0,
                "avg_pos": vector(0, 0, 0),
                "avg_y": 0,
                "avg_speed": 0,
                "spread": 0,
                "max_y": 0,
                "min_y": 0,
                "tether_count": len(tethers),
                "near_collision_pairs": 0,
            }

        avg_pos = vector(0, 0, 0)
        avg_speed = 0.0
        max_y = -999
        min_y = 999
        for b in balloons:
            avg_pos += b.pos
            avg_speed += mag(b.vel)
            max_y = max(max_y, b.pos.y)
            min_y = min(min_y, b.pos.y)
        avg_pos /= len(balloons)
        avg_speed /= len(balloons)

        spread = 0.0
        for b in balloons:
            spread += mag(horizontal(b.pos - avg_pos))
        spread /= len(balloons)

        near_pairs = 0
        for i in range(len(balloons)):
            for j in range(i + 1, len(balloons)):
                if distance(balloons[i].pos, balloons[j].pos) < balloons[i].radius + balloons[j].radius + 0.75:
                    near_pairs += 1

        return {
            "count": len(balloons),
            "avg_pos": avg_pos,
            "avg_y": avg_pos.y,
            "avg_speed": avg_speed,
            "spread": spread,
            "max_y": max_y,
            "min_y": min_y,
            "tether_count": len(tethers),
            "near_collision_pairs": near_pairs,
        }

    def detect_stagnation_or_completion(self, state, dt):
        if state["count"] == 0:
            self.completed = True
            self.completion_time += dt
            return

        complete_by_height = state["avg_y"] > CEILING_Y - 4.0 or state["min_y"] > CEILING_Y - 6.0

        if sim_time - self.prev_state_check >= 1.0:
            if self.prev_avg_y is not None:
                progress = abs(state["avg_y"] - self.prev_avg_y)
                if progress < 0.035 and state["avg_speed"] < 0.16:
                    self.stagnant_time += sim_time - self.prev_state_check
                else:
                    self.stagnant_time = max(0.0, self.stagnant_time - 0.5)
            self.prev_avg_y = state["avg_y"]
            self.prev_state_check = sim_time

        stable_or_stuck = self.stagnant_time > 5.0
        too_high_and_done = complete_by_height

        if stable_or_stuck or too_high_and_done:
            self.completed = True
            self.completion_time += dt
        else:
            self.completed = False
            self.completion_time = 0.0

    def pick_mode(self, force=False):
        state = self.read_state()
        if state["count"] == 0:
            return

        candidates = list(self.modes)

        if state["spread"] > 10:
            preferred = ["ORGANIZE_CLUSTER", "ORBIT_MAYPOLE", "GENTLE_ASCENT"]
        elif state["tether_count"] > 8:
            preferred = ["CHAOTIC_GUSTS", "ARTIST_SPIRAL", "SIDEWAYS_PARADE"]
        elif state["near_collision_pairs"] > 2:
            preferred = ["GENTLE_ASCENT", "ORBIT_MAYPOLE", "WRAP_DANCE"]
        elif state["avg_y"] > CEILING_Y * 0.62:
            preferred = ["ARTIST_SPIRAL", "DIP_AND_RECOVER", "WRAP_DANCE"]
        else:
            preferred = candidates

        pool = [m for m in preferred if m not in self.recent_modes[-2:]]
        if not pool:
            pool = candidates

        if force:
            new_mode = pyrandom.choice(pool)
        else:
            new_mode = pyrandom.choice([m for m in pool if m != self.mode] or pool)

        self.mode = new_mode
        self.mode_index = self.modes.index(new_mode)
        self.mode_elapsed = 0.0
        self.mode_duration = pyrandom.uniform(6.5, 11.5)
        self.recent_modes.append(new_mode)
        if len(self.recent_modes) > 5:
            self.recent_modes.pop(0)

    def next_mode(self):
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.mode = self.modes[self.mode_index]
        self.mode_elapsed = 0.0
        self.mode_duration = pyrandom.uniform(6.0, 10.0)
        self.recent_modes.append(self.mode)

    def apply_wind_target(self, v, strength=0.025):
        global target_wind
        target_wind = lerp(target_wind, v, strength)

    def nudge_to(self, b, target, gain=0.35, damping=0.18, max_force=2.7):
        desired = target - b.pos
        f = desired * gain - b.vel * damping
        if mag(f) > max_force:
            f = norm(f) * max_force
        b.add_force(f)

    def behavior_gentle_ascent(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        self.apply_wind_target(vector(0.65 * math.sin(sim_time * 0.32), 0, 0.35 * math.cos(sim_time * 0.21)), 0.035)
        for b in balloons:
            center_pull = vector(-b.pos.x * 0.025, 0.25, -b.pos.z * 0.025)
            b.add_force(center_pull * influence)
            b.warmth = lerp(b.warmth, 1.05, 0.002)

    def behavior_sideways_parade(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        direction = 1 if math.sin(sim_time * 0.18) >= 0 else -1
        self.apply_wind_target(vector(1.8 * direction, 0, 0.35 * math.sin(sim_time * 0.44)), 0.045)

        n = max(1, len(balloons))
        for i, b in enumerate(balloons):
            lane_z = (i - (n - 1) * 0.5) * 1.55
            target = vector(
                -WORLD_X * 0.55 * direction + math.sin(sim_time * 0.25 + i) * 1.5,
                FLOOR_Y + 6.5 + i * 0.65,
                lane_z,
            )
            self.nudge_to(b, target, gain=0.11 * influence, damping=0.08, max_force=1.8)

    def behavior_orbit_maypole(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        self.apply_wind_target(vector(0.25 * math.sin(sim_time), 0, 0.25 * math.cos(sim_time * 0.7)), 0.025)

        self.ritual_angle += dt * 0.45
        for i, b in enumerate(balloons):
            radial = horizontal(b.pos)
            r = mag(radial)
            if r < 0.5:
                radial = vector(1, 0, 0)
                r = 1.0
            tangent = safe_norm(vector(-radial.z, 0, radial.x))
            desired_r = 6.0 + 1.5 * math.sin(self.ritual_angle + i)
            radial_force = safe_norm(radial) * (desired_r - r) * 0.22
            swirl_force = tangent * 1.2
            lift = vector(0, 0.16 * math.sin(sim_time * 0.8 + i), 0)
            b.add_force((radial_force + swirl_force + lift) * influence)

    def behavior_organize_cluster(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        self.apply_wind_target(vector(0.25 * math.sin(sim_time * 0.2), 0, -0.15), 0.03)

        n = max(1, len(balloons))
        ring_r = 5.4
        center_y = clamp(state["avg_y"] + 0.15, FLOOR_Y + 6.0, CEILING_Y - 5.0)
        for i, b in enumerate(balloons):
            ang = 2 * math.pi * i / n + 0.12 * math.sin(sim_time * 0.2)
            target = vector(math.cos(ang) * ring_r, center_y + 1.2 * math.sin(ang * 2), math.sin(ang) * ring_r * 0.72)
            self.nudge_to(b, target, gain=0.17 * influence, damping=0.10, max_force=2.2)

        if len(tethers) < min(MAX_TETHERS, len(balloons)):
            for i, b in enumerate(balloons):
                other = balloons[(i + 1) % len(balloons)]
                if tether_between(b, other) is None and pyrandom.random() < 0.015:
                    attach_pair(b, other)

    def behavior_chaotic_gusts(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False

        if sim_time - self.last_random_gust > 0.9:
            self.last_random_gust = sim_time
            self.apply_wind_target(vector(
                pyrandom.uniform(-3.2, 3.2),
                0,
                pyrandom.uniform(-1.8, 1.8),
            ), 0.45)

            for b in balloons:
                if pyrandom.random() < 0.32:
                    b.vel += vector(
                        pyrandom.uniform(-1.0, 1.0),
                        pyrandom.uniform(-0.25, 0.85),
                        pyrandom.uniform(-1.0, 1.0),
                    ) * influence
                    b.vent(2, hot=pyrandom.random() < 0.5)

            if tethers and pyrandom.random() < 0.35:
                detach_tether(pyrandom.choice(tethers))

        for b in balloons:
            jitter = vector(
                pyrandom.uniform(-0.6, 0.6),
                pyrandom.uniform(-0.25, 0.55),
                pyrandom.uniform(-0.6, 0.6),
            )
            b.add_force(jitter * influence)

    def behavior_artist_spiral(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        self.apply_wind_target(vector(0.9 * math.sin(sim_time * 0.55), 0, 0.9 * math.cos(sim_time * 0.47)), 0.04)

        for i, b in enumerate(balloons):
            phase = sim_time * 0.65 + i * 0.77
            target = vector(
                math.cos(phase) * (3.5 + 0.28 * i),
                FLOOR_Y + 6.0 + (phase * 0.65 + i * 0.5) % 13.0,
                math.sin(phase) * (2.5 + 0.22 * i),
            )
            self.nudge_to(b, target, gain=0.13 * influence, damping=0.06, max_force=2.2)
            if pyrandom.random() < 0.018:
                b.vent(3, hot=True)

    def behavior_dip_and_recover(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = False
        self.apply_wind_target(vector(0.45 * math.cos(sim_time * 0.4), 0, 0.55 * math.sin(sim_time * 0.31)), 0.03)

        phase = (self.mode_elapsed % 5.0) / 5.0
        dipping = phase < 0.45
        for i, b in enumerate(balloons):
            if dipping:
                b.add_force(vector(0, -1.15 - 0.18 * math.sin(i), 0) * influence)
                b.warmth = lerp(b.warmth, 0.82, 0.006)
            else:
                b.add_force(vector(0, 1.65 + 0.2 * math.cos(i), 0) * influence)
                b.warmth = lerp(b.warmth, 1.22, 0.006)

    def behavior_wrap_dance(self, state, dt, influence):
        global wrap_enabled
        wrap_enabled = True
        self.apply_wind_target(vector(2.3 * math.sin(sim_time * 0.33), 0, 1.45 * math.cos(sim_time * 0.27)), 0.045)

        for i, b in enumerate(balloons):
            push = vector(
                0.5 * math.sin(sim_time * 0.8 + i),
                0.2,
                0.5 * math.cos(sim_time * 0.75 + i),
            )
            b.add_force(push * influence)
            if abs(b.pos.x) > WORLD_X - 2.5 or abs(b.pos.z) > WORLD_Z - 2.5:
                if pyrandom.random() < 0.03:
                    b.vent(4, hot=False)

    def update(self, dt):
        if not self.enabled:
            return

        state = self.read_state()
        self.detect_stagnation_or_completion(state, dt)

        if self.completed and self.completion_time > 2.8:
            reset_world("AI loop reset after completion/stagnation")
            return

        self.mode_elapsed += dt
        if self.mode_elapsed > self.mode_duration:
            self.pick_mode()

        influence = 1.0
        if sim_time < self.override_until:
            influence = 0.32

        if self.mode == "GENTLE_ASCENT":
            self.behavior_gentle_ascent(state, dt, influence)
        elif self.mode == "SIDEWAYS_PARADE":
            self.behavior_sideways_parade(state, dt, influence)
        elif self.mode == "ORBIT_MAYPOLE":
            self.behavior_orbit_maypole(state, dt, influence)
        elif self.mode == "ORGANIZE_CLUSTER":
            self.behavior_organize_cluster(state, dt, influence)
        elif self.mode == "CHAOTIC_GUSTS":
            self.behavior_chaotic_gusts(state, dt, influence)
        elif self.mode == "ARTIST_SPIRAL":
            self.behavior_artist_spiral(state, dt, influence)
        elif self.mode == "DIP_AND_RECOVER":
            self.behavior_dip_and_recover(state, dt, influence)
        elif self.mode == "WRAP_DANCE":
            self.behavior_wrap_dance(state, dt, influence)

# ---------------------------------------------------------------------
# Keyboard / human control
# ---------------------------------------------------------------------

ai = None

def selected_balloon():
    if not balloons:
        return None
    idx = selected_index % len(balloons)
    return balloons[idx]

def keydown(evt):
    global paused, selected_index, show_caption, wrap_enabled, target_wind

    k = evt.key

    if k in ["p", "P", " "]:
        paused = not paused
        return

    if k in ["h", "H"]:
        show_caption = not show_caption
        scene.caption = scene.caption if show_caption else ""
        return

    if k in ["i", "I"]:
        ai.enabled = not ai.enabled
        return

    if k in ["m", "M"]:
        ai.next_mode()
        ai.human_override(1.5)
        return

    if k in ["r", "R"]:
        reset_world("human reset")
        ai.human_override(1.0)
        return

    if k == "tab":
        if balloons:
            selected_index = (selected_index + 1) % len(balloons)
        return

    if k in ["o", "O"]:
        wrap_enabled = not wrap_enabled
        ai.human_override(2.0)
        return

    if k in ["g", "G"]:
        target_wind = vector(pyrandom.uniform(-3.2, 3.2), 0, pyrandom.uniform(-1.8, 1.8))
        for b in balloons:
            b.vel += vector(pyrandom.uniform(-0.5, 0.5), pyrandom.uniform(0.0, 0.55), pyrandom.uniform(-0.5, 0.5))
        ai.human_override(2.0)
        return

    b = selected_balloon()
    if b is None:
        return

    impulse = 0.78

    if k == "left":
        b.vel += vector(-impulse, 0, 0)
        ai.human_override(2.5)
    elif k == "right":
        b.vel += vector(impulse, 0, 0)
        ai.human_override(2.5)
    elif k == "up":
        b.vel += vector(0, impulse, 0)
        b.warmth = clamp(b.warmth + 0.04, 0.7, 1.35)
        ai.human_override(2.5)
    elif k == "down":
        b.vel += vector(0, -impulse, 0)
        b.warmth = clamp(b.warmth - 0.04, 0.65, 1.35)
        ai.human_override(2.5)
    elif k in ["w", "W"]:
        b.vel += vector(0, 0, -impulse)
        ai.human_override(2.5)
    elif k in ["s", "S"]:
        b.vel += vector(0, 0, impulse)
        ai.human_override(2.5)
    elif k in ["b", "B"]:
        b.vent(10, hot=True)
        ai.human_override(2.0)
    elif k in ["x", "X"]:
        detach_balloon(b)
        ai.human_override(2.0)
    elif k in ["c", "C"]:
        other, d = nearest_balloon(b)
        if other is not None:
            existing = tether_between(b, other)
            if existing:
                detach_tether(existing)
            else:
                attach_pair(b, other)
        ai.human_override(2.0)

scene.bind("keydown", keydown)

# ---------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------

def update_hud():
    state = ai.read_state()
    selected = selected_balloon()
    selected_text = f"B{selected.ident}" if selected else "none"

    ai_text = "ON" if ai.enabled else "OFF"
    pause_text = "PAUSED" if paused else "RUNNING"
    wrap_text = "ON" if wrap_enabled else "OFF"

    hud.text = (
        f"Round {ai.round} | {pause_text}\n"
        f"AI: {ai_text} | Mode: {ai.mode} | Wrap: {wrap_text}\n"
        f"Selected: {selected_text} | Balloons: {state['count']} | Tethers: {state['tether_count']}\n"
        f"Avg altitude: {state['avg_y']:.1f} | Spread: {state['spread']:.1f} | Avg speed: {state['avg_speed']:.2f}\n"
        f"Completion/stagnation timer: {ai.completion_time:.1f}s"
    )

    mode_label.text = f"AI behavior: {ai.mode}" if ai.enabled else "AI disabled - human control"

# ---------------------------------------------------------------------
# Initialize dynamic simulation
# ---------------------------------------------------------------------

ai = AIController()
reset_world("initial")

# ---------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------

while True:
    rate(60)

    if not paused:
        sim_time += DT
        frame_count += 1

        # Smoothly move current wind toward the AI/human target.
        base_wind = lerp(base_wind, target_wind, 0.018)

        for b in balloons:
            b.force = vector(0, 0, 0)

        ai.update(DT)

        for t in list(tethers):
            t.apply()

        for b in balloons:
            b.integrate(DT)

        handle_collisions()

        for b in balloons:
            b.enforce_world()

        for i, b in enumerate(balloons):
            b.update_graphics(selected=(i == selected_index % max(1, len(balloons))))

        for t in list(tethers):
            t.update_graphics()

        alive_particles = []
        for p in particles:
            if p.update(DT):
                alive_particles.append(p)
        particles[:] = alive_particles

        update_wind_arrows()

    update_hud()
