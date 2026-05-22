from vpython import *
from random import random, uniform, choice
from math import sin, cos, sqrt, pi

# ------------------------------------------------------------
# Orbiting Water Comet Near a Planet
# VPython self-contained simulation with human controls and AI.
# ------------------------------------------------------------

scene = canvas(
    title="Orbiting Water Comet Near a Planet - AI Controlled Water-Ice Tail",
    width=1200,
    height=760,
    background=vector(0.88, 0.95, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.75, -0.35, -0.85)
scene.range = 8.5
scene.autoscale = False
scene.caption = """
Controls:
SPACE pause/resume | A toggle AI | O human override AI thrust | R reset round | N next AI mode
W/S prograde/retrograde thrust | UP/DOWN radial out/in | LEFT/RIGHT orbit-normal thrust
Z spill/detach ice | X attach/collect nearby ice | [ / ] decrease/increase shedding
"""

# -----------------------------
# Constants / simulation tuning
# -----------------------------

DT = 0.018
MAX_PARTICLES = 260
MAX_MARKS = 80

PLANET_RADIUS = 1.48
ATM_RADIUS = 1.93
COMET_RADIUS = 0.18
MU = 16.5

SUN_POS = vector(-7.8, 4.3, 3.2)
SUN_COLOR = vector(1.0, 0.92, 0.58)
ICE_BLUE = vector(0.45, 0.82, 1.0)
DEEP_ICE = vector(0.18, 0.55, 0.95)
ATM_COLOR = vector(0.55, 0.88, 1.0)
PLANET_COLOR = vector(0.58, 0.76, 0.95)

paused = False
round_time = 0.0
round_id = 0
global_collision_count = 0
global_shed_multiplier = 1.0
human_override_ai = False
keys_down = set()

particles = []
marks = []
attached_shards = []

# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-9:
        return fallback
    return v / m

def rand_unit():
    z = uniform(-1, 1)
    t = uniform(0, 2 * pi)
    r = sqrt(max(0, 1 - z * z))
    return vector(r * cos(t), z, r * sin(t))

def rand_perp(axis):
    axis = safe_norm(axis)
    v = rand_unit()
    p = v - dot(v, axis) * axis
    if mag(p) < 1e-6:
        p = cross(axis, vector(0, 1, 0))
    return safe_norm(p)

def mix_color(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t

def tangential_direction(pos, orbit_normal=vector(0, 1, 0)):
    radial = safe_norm(pos)
    t = cross(orbit_normal, radial)
    if mag(t) < 1e-5:
        t = cross(vector(0, 0, 1), radial)
    return safe_norm(t)

# -----------------------------
# Scene objects
# -----------------------------

sun = sphere(
    pos=SUN_POS,
    radius=0.45,
    color=SUN_COLOR,
    emissive=True,
    shininess=0.4,
)
local_light(pos=SUN_POS, color=vector(1.0, 0.94, 0.82))
distant_light(direction=safe_norm(-SUN_POS), color=vector(0.55, 0.58, 0.62))

sun_label = label(
    pos=SUN_POS + vector(0, 0.65, 0),
    text="light source",
    height=12,
    color=vector(0.55, 0.42, 0.05),
    box=False,
    opacity=0,
)

planet = sphere(
    pos=vector(0, 0, 0),
    radius=PLANET_RADIUS,
    color=PLANET_COLOR,
    shininess=0.25,
)
planet_label = label(
    pos=vector(0, -2.25, 0),
    text="central planet",
    height=12,
    color=vector(0.15, 0.32, 0.55),
    box=False,
    opacity=0,
)

atmosphere = sphere(
    pos=vector(0, 0, 0),
    radius=ATM_RADIUS,
    color=ATM_COLOR,
    opacity=0.18,
    shininess=0.1,
)

inner_atmosphere = sphere(
    pos=vector(0, 0, 0),
    radius=(PLANET_RADIUS + ATM_RADIUS) * 0.5,
    color=vector(0.75, 0.95, 1.0),
    opacity=0.055,
    shininess=0.1,
)

# Orbit guide rings
for rr, op in [(ATM_RADIUS, 0.18), (3.5, 0.11), (5.3, 0.10), (6.4, 0.07)]:
    pts = []
    for i in range(145):
        a = 2 * pi * i / 144
        pts.append(vector(rr * cos(a), 0, rr * sin(a)))
    curve(pos=pts, color=vector(0.55, 0.65, 0.75), radius=0.006, opacity=op)

light_arrow = arrow(
    pos=SUN_POS * 0.68,
    axis=safe_norm(-SUN_POS) * 1.2,
    shaftwidth=0.045,
    color=vector(1.0, 0.80, 0.22),
    opacity=0.65,
)

comet = sphere(
    pos=vector(5.2, 0, 0),
    radius=COMET_RADIUS,
    color=ICE_BLUE,
    emissive=True,
    shininess=0.8,
    make_trail=True,
    trail_color=vector(0.40, 0.70, 1.0),
    retain=700,
)
comet.vel = vector(0, 0, 1.75)
comet_spin = 0.0
comet_spin_axis = safe_norm(vector(0.3, 1.0, 0.2))
comet_label = label(
    pos=comet.pos + vector(0, 0.42, 0),
    text="icy-blue nucleus",
    height=11,
    color=vector(0.05, 0.35, 0.85),
    box=False,
    opacity=0,
)

tail_axis_arrow = arrow(
    pos=comet.pos,
    axis=vector(0.8, 0, 0),
    shaftwidth=0.025,
    color=vector(0.38, 0.74, 1.0),
    opacity=0.35,
)

dashboard = label(
    pos=vector(-5.6, 4.05, 0),
    text="",
    height=11,
    color=vector(0.05, 0.16, 0.28),
    box=True,
    border=8,
    background=vector(0.93, 0.98, 1.0),
    opacity=0.48,
)

mode_marker = sphere(
    pos=vector(0, 2.45, 0),
    radius=0.08,
    color=vector(0.2, 0.55, 1.0),
    emissive=True,
    opacity=0.75,
)

# -----------------------------
# Particle / mark classes
# -----------------------------

class IceParticle:
    def __init__(self, pos, vel, radius, life, colorv, attached_origin=False):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.radius0 = radius
        self.radius = radius
        self.life = life
        self.max_life = life
        self.mass = radius * radius * radius * 12.0
        self.was_in_atm = False
        self.collisions = 0
        self.attached_origin = attached_origin
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=colorv,
            emissive=True,
            opacity=0.62,
            shininess=0.5,
        )
        self.trail = curve(
            pos=[self.pos],
            radius=max(0.0025, radius * 0.12),
            color=colorv,
            opacity=0.20,
        )

    def destroy(self):
        self.obj.visible = False
        self.trail.visible = False

    def update(self, dt, controls):
        global global_collision_count

        r = mag(self.pos)
        radial = safe_norm(self.pos)
        sun_away = safe_norm(self.pos - SUN_POS)

        gravity = -MU * self.pos / max(r ** 3, 0.03)
        radiation_push = sun_away * (0.16 + 0.22 * (1.0 - clamp(self.radius / 0.05, 0, 1)))
        random_dispersion = rand_unit() * 0.018

        swirl = vector(0, 0, 0)
        if controls["swirl_strength"] > 0:
            swirl_dir = safe_norm(cross(vector(0, 1, 0), radial), rand_perp(radial))
            swirl = swirl_dir * controls["swirl_strength"] / max(1.2, r)

        accel = gravity + radiation_push + random_dispersion + swirl
        self.vel += accel * dt

        in_atm = PLANET_RADIUS < r < ATM_RADIUS
        hit_planet = r <= PLANET_RADIUS

        if in_atm:
            depth = clamp((ATM_RADIUS - r) / (ATM_RADIUS - PLANET_RADIUS), 0, 1)
            drag = 1.0 - clamp(0.16 * depth * dt * 60, 0, 0.35)
            self.vel *= drag
            self.vel += radial * 0.015 * depth
            self.life -= dt * (0.4 + 1.8 * depth)

            if not self.was_in_atm or random() < 0.006 + 0.055 * depth:
                self.collisions += 1
                global_collision_count += 1
                create_atmosphere_mark(self.pos, self.vel, depth)
            self.was_in_atm = True
        else:
            self.was_in_atm = False

        if hit_planet:
            create_surface_mark(self.pos, self.vel)
            global_collision_count += 1
            return False

        self.life -= dt * (0.17 + 0.08 * mag(self.pos - SUN_POS) / 8.0)
        self.pos += self.vel * dt

        age = 1.0 - self.life / max(self.max_life, 1e-6)
        sublimate = clamp(age, 0, 1)
        self.radius = self.radius0 * (1.0 - 0.82 * sublimate)
        self.obj.radius = max(0.002, self.radius)
        self.obj.opacity = clamp(0.68 * (1.0 - sublimate), 0.02, 0.68)
        self.obj.color = mix_color(ICE_BLUE, color.white, sublimate * 0.65)
        self.obj.pos = self.pos

        if len(self.trail.pos) < 24:
            self.trail.append(pos=self.pos)
        else:
            self.trail.append(pos=self.pos, retain=24)

        self.trail.opacity = clamp(0.22 * (1.0 - sublimate), 0.015, 0.22)

        if self.life <= 0 or self.radius < 0.003 or mag(self.pos) > 14.0:
            return False
        return True

def create_atmosphere_mark(pos, vel, depth=0.5):
    if len(marks) >= MAX_MARKS:
        old = marks.pop(0)
        old["obj"].visible = False

    radial = safe_norm(pos)
    ring_radius = uniform(0.045, 0.12) * (1.0 + depth)
    obj = ring(
        pos=radial * (ATM_RADIUS * 0.998),
        axis=radial,
        radius=ring_radius,
        thickness=0.008,
        color=mix_color(vector(0.55, 0.9, 1.0), color.white, random() * 0.5),
        opacity=0.52,
    )
    marks.append({
        "obj": obj,
        "age": 0.0,
        "life": uniform(1.5, 3.6),
        "kind": "atmosphere",
    })

def create_surface_mark(pos, vel):
    if len(marks) >= MAX_MARKS:
        old = marks.pop(0)
        old["obj"].visible = False

    radial = safe_norm(pos)
    obj = sphere(
        pos=radial * (PLANET_RADIUS + 0.012),
        radius=uniform(0.035, 0.075),
        color=vector(0.80, 0.97, 1.0),
        emissive=True,
        opacity=0.68,
    )
    marks.append({
        "obj": obj,
        "age": 0.0,
        "life": uniform(2.0, 5.0),
        "kind": "surface",
    })

def update_marks(dt):
    alive = []
    for m in marks:
        m["age"] += dt
        t = clamp(m["age"] / m["life"], 0, 1)
        m["obj"].opacity = max(0, (1 - t) * 0.58)
        if hasattr(m["obj"], "radius"):
            m["obj"].radius *= (1.0 + 0.018 * dt * 60)
        if m["age"] < m["life"]:
            alive.append(m)
        else:
            m["obj"].visible = False
    marks[:] = alive

# -----------------------------
# Attached ice chunks on nucleus
# -----------------------------

def create_attached_shard(offset=None, size=None):
    if offset is None:
        offset = rand_unit() * uniform(COMET_RADIUS * 0.85, COMET_RADIUS * 1.25)
    if size is None:
        size = uniform(0.025, 0.055)
    obj = sphere(
        pos=comet.pos + offset,
        radius=size,
        color=mix_color(ICE_BLUE, color.white, random() * 0.55),
        emissive=True,
        opacity=0.78,
        shininess=0.7,
    )
    attached_shards.append({
        "obj": obj,
        "offset": offset,
        "size": size,
        "phase": uniform(0, 2 * pi),
    })

def update_attached_shards(dt):
    global comet_spin
    comet_spin += dt * 1.45
    for shard in attached_shards:
        off = rotate(shard["offset"], angle=comet_spin + shard["phase"] * 0.10, axis=comet_spin_axis)
        shard["obj"].pos = comet.pos + off
        shard["obj"].radius = shard["size"] * (1.0 + 0.08 * sin(comet_spin * 2 + shard["phase"]))
        shard["obj"].opacity = 0.70 + 0.18 * sin(comet_spin + shard["phase"])

def detach_one_shard(extra_vel=vector(0, 0, 0)):
    if not attached_shards:
        return None
    shard = attached_shards.pop(0)
    shard["obj"].visible = False
    away_from_sun = safe_norm(comet.pos - SUN_POS)
    lateral = rand_perp(away_from_sun)
    ppos = shard["obj"].pos
    pvel = comet.vel + away_from_sun * uniform(0.45, 1.25) + lateral * uniform(-0.25, 0.25) + extra_vel
    particle = IceParticle(
        ppos,
        pvel,
        shard["size"] * uniform(0.7, 1.1),
        uniform(8, 18),
        mix_color(ICE_BLUE, color.white, random() * 0.5),
        attached_origin=True,
    )
    particles.append(particle)
    return particle

def collect_nearby_ice(radius=0.55, max_collect=2):
    collected = 0
    remaining = []
    for p in particles:
        if collected < max_collect and mag(p.pos - comet.pos) < radius:
            create_attached_shard(offset=safe_norm(p.pos - comet.pos, rand_unit()) * uniform(COMET_RADIUS * 0.9, COMET_RADIUS * 1.35),
                                  size=clamp(p.radius, 0.018, 0.055))
            p.destroy()
            collected += 1
        else:
            remaining.append(p)
    particles[:] = remaining
    return collected

# -----------------------------
# Comet shedding
# -----------------------------

emit_accumulator = 0.0

def emit_ice_particles(dt, controls, manual_spill=False):
    global emit_accumulator

    base_rate = 8.5
    rate_now = base_rate * global_shed_multiplier * controls["shed_multiplier"]
    if manual_spill:
        rate_now += 38.0

    emit_accumulator += rate_now * dt
    n_emit = int(emit_accumulator)
    emit_accumulator -= n_emit

    for _ in range(n_emit):
        if len(particles) >= MAX_PARTICLES:
            old = particles.pop(0)
            old.destroy()

        detach_chance = controls["detach_probability"] + (0.25 if manual_spill else 0.0)
        if attached_shards and random() < detach_chance:
            detach_one_shard(extra_vel=rand_unit() * 0.08)
            continue

        away_from_sun = safe_norm(comet.pos - SUN_POS)
        side1 = rand_perp(away_from_sun)
        side2 = safe_norm(cross(away_from_sun, side1), rand_perp(away_from_sun))
        spread = side1 * uniform(-0.13, 0.13) + side2 * uniform(-0.13, 0.13)
        ppos = comet.pos + away_from_sun * (COMET_RADIUS * 1.05) + spread
        pvel = comet.vel * uniform(0.75, 1.0) + away_from_sun * uniform(0.75, 1.95) + spread * uniform(0.4, 1.8)
        radius = uniform(0.018, 0.052)
        life = uniform(5.5, 16.0)
        pcolor = mix_color(ICE_BLUE, color.white, random() * 0.55)
        particles.append(IceParticle(ppos, pvel, radius, life, pcolor))

# -----------------------------
# Simulation state / AI
# -----------------------------

class AIController:
    MODES = [
        "CURIOUS_ORBIT",
        "FLARE_TAIL",
        "ATMOSPHERE_DIP",
        "WRAP_TAIL",
        "MARK_ATMOSPHERE",
        "ORGANIZE_ICE",
        "CHAOTIC_SPILL",
        "ARTISTIC_SPIRAL",
        "CAREFUL_EVADE",
    ]

    MODE_COLORS = {
        "CURIOUS_ORBIT": vector(0.25, 0.55, 1.0),
        "FLARE_TAIL": vector(0.20, 0.85, 1.0),
        "ATMOSPHERE_DIP": vector(0.70, 0.40, 1.0),
        "WRAP_TAIL": vector(0.10, 0.75, 0.80),
        "MARK_ATMOSPHERE": vector(0.95, 0.60, 0.20),
        "ORGANIZE_ICE": vector(0.38, 0.80, 0.46),
        "CHAOTIC_SPILL": vector(1.0, 0.35, 0.50),
        "ARTISTIC_SPIRAL": vector(0.80, 0.50, 1.0),
        "CAREFUL_EVADE": vector(1.0, 0.72, 0.15),
    }

    def __init__(self):
        self.enabled = True
        self.mode = "CURIOUS_ORBIT"
        self.last_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 9.0
        self.round_pause = 0.0
        self.random_impulse_timer = 0.0
        self.stagnation_timer = 0.0
        self.metric_timer = 0.0
        self.last_metric = None
        self.complete = False
        self.reset_delay = 0.0
        self.controls = self.default_controls()
        self.human_override_timer = 0.0

    def default_controls(self):
        return {
            "thrust": vector(0, 0, 0),
            "shed_multiplier": 1.0,
            "detach_probability": 0.06,
            "swirl_strength": 0.0,
            "collect_radius": 0.0,
            "marker_pulse": False,
            "name": self.mode,
        }

    def next_mode(self, forced=None):
        self.last_mode = self.mode
        if forced:
            self.mode = forced
        else:
            choices = [m for m in self.MODES if m != self.mode and m != self.last_mode]
            self.mode = choice(choices)
        self.mode_timer = 0.0
        self.mode_duration = uniform(7.0, 15.0)
        self.random_impulse_timer = 0.0

    def get_state(self):
        r = mag(comet.pos)
        radial = safe_norm(comet.pos)
        speed = mag(comet.vel)
        altitude = r - PLANET_RADIUS
        sun_away = safe_norm(comet.pos - SUN_POS)
        prograde = safe_norm(comet.vel, tangential_direction(comet.pos))
        normal = safe_norm(cross(radial, prograde), vector(0, 1, 0))

        avg_tail_dist = 0.0
        if particles:
            avg_tail_dist = sum(mag(p.pos - comet.pos) for p in particles) / len(particles)

        in_atm = r < ATM_RADIUS
        danger = r < PLANET_RADIUS + 0.42 or (in_atm and dot(comet.vel, radial) < -0.2)

        return {
            "r": r,
            "altitude": altitude,
            "speed": speed,
            "radial": radial,
            "prograde": prograde,
            "normal": normal,
            "sun_away": sun_away,
            "particle_count": len(particles),
            "shard_count": len(attached_shards),
            "mark_count": len(marks),
            "collision_count": global_collision_count,
            "avg_tail_dist": avg_tail_dist,
            "in_atmosphere": in_atm,
            "danger": danger,
            "round_time": round_time,
        }

    def update_stagnation(self, dt, state):
        self.metric_timer += dt
        complete_reason = None

        if self.metric_timer >= 1.0:
            metric = (
                state["particle_count"],
                state["shard_count"],
                state["collision_count"],
                round(state["avg_tail_dist"], 2),
                round(state["r"], 2),
            )
            if self.last_metric is not None:
                dp = abs(metric[0] - self.last_metric[0])
                ds = abs(metric[1] - self.last_metric[1])
                dc = abs(metric[2] - self.last_metric[2])
                dd = abs(metric[3] - self.last_metric[3])
                dr = abs(metric[4] - self.last_metric[4])
                if dp + ds + dc < 2 and dd < 0.05 and dr < 0.03:
                    self.stagnation_timer += 1.0
                else:
                    self.stagnation_timer = max(0, self.stagnation_timer - 1.5)
            self.last_metric = metric
            self.metric_timer = 0.0

        if state["collision_count"] >= 45:
            complete_reason = "atmosphere marked"
        elif round_time > 105:
            complete_reason = "round aged"
        elif state["particle_count"] == 0 and state["shard_count"] == 0 and round_time > 18:
            complete_reason = "empty"
        elif self.stagnation_timer > 13:
            complete_reason = "stable"
        elif state["r"] < PLANET_RADIUS + COMET_RADIUS * 0.5:
            complete_reason = "impact"

        self.complete = complete_reason is not None
        return complete_reason

    def update(self, dt):
        if not self.enabled:
            self.controls = self.default_controls()
            return self.controls

        state = self.get_state()
        reason = self.update_stagnation(dt, state)

        if reason:
            self.reset_delay += dt
            self.controls = self.default_controls()
            self.controls["shed_multiplier"] = 0.25
            if self.reset_delay > 2.2:
                reset_simulation(randomize=True)
                self.reset_delay = 0.0
                self.complete = False
                self.stagnation_timer = 0.0
                self.next_mode("CURIOUS_ORBIT")
            return self.controls
        else:
            self.reset_delay = 0.0

        if state["danger"] and self.mode != "CAREFUL_EVADE":
            self.next_mode("CAREFUL_EVADE")

        self.mode_timer += dt
        if self.mode_timer > self.mode_duration:
            self.next_mode()

        c = self.default_controls()
        r = state["r"]
        radial = state["radial"]
        prograde = state["prograde"]
        normal = state["normal"]
        sun_away = state["sun_away"]

        desired_orbit = 5.1
        altitude_error = r - desired_orbit

        if self.mode == "CURIOUS_ORBIT":
            c["shed_multiplier"] = 0.85 + 0.35 * sin(round_time * 0.7)
            c["detach_probability"] = 0.05
            c["thrust"] = -radial * altitude_error * 0.035 + prograde * 0.014 * sin(round_time)
            if state["particle_count"] < 35:
                c["shed_multiplier"] += 0.55

        elif self.mode == "FLARE_TAIL":
            c["shed_multiplier"] = 2.7 + 0.8 * max(0, sin(round_time * 2.2))
            c["detach_probability"] = 0.16
            c["thrust"] = sun_away * 0.045 + prograde * 0.018
            if random() < 0.015:
                c["marker_pulse"] = True

        elif self.mode == "ATMOSPHERE_DIP":
            target = ATM_RADIUS + 0.18
            c["shed_multiplier"] = 1.35
            c["detach_probability"] = 0.09
            c["thrust"] = -radial * clamp((r - target) * 0.045, -0.025, 0.075) + prograde * 0.016
            if r < ATM_RADIUS + 0.05:
                c["thrust"] += radial * 0.12 + prograde * 0.04

        elif self.mode == "WRAP_TAIL":
            c["shed_multiplier"] = 2.0
            c["detach_probability"] = 0.12
            c["swirl_strength"] = 0.9 + 0.45 * sin(round_time * 1.6)
            c["thrust"] = prograde * 0.035 - radial * clamp((r - 4.2) * 0.025, -0.03, 0.04)

        elif self.mode == "MARK_ATMOSPHERE":
            c["shed_multiplier"] = 1.7
            c["detach_probability"] = 0.18
            target = ATM_RADIUS + 0.02
            c["thrust"] = -radial * clamp((r - target) * 0.055, -0.02, 0.09) + prograde * 0.018
            if r < ATM_RADIUS:
                c["marker_pulse"] = True
                c["thrust"] += radial * 0.08

        elif self.mode == "ORGANIZE_ICE":
            c["shed_multiplier"] = 0.45
            c["detach_probability"] = 0.01
            c["collect_radius"] = 0.75
            c["thrust"] = -radial * altitude_error * 0.04 + prograde * 0.022
            if len(attached_shards) < 20 and random() < 0.025:
                collect_nearby_ice(radius=0.9, max_collect=2)

        elif self.mode == "CHAOTIC_SPILL":
            c["shed_multiplier"] = 3.25
            c["detach_probability"] = 0.35
            self.random_impulse_timer -= dt
            if self.random_impulse_timer <= 0:
                self.random_impulse = rand_unit() * uniform(0.04, 0.13)
                self.random_impulse_timer = uniform(0.35, 1.2)
            c["thrust"] = self.random_impulse + sun_away * 0.03
            c["swirl_strength"] = uniform(0.2, 0.75)

        elif self.mode == "ARTISTIC_SPIRAL":
            c["shed_multiplier"] = 1.25 + 1.15 * (0.5 + 0.5 * sin(round_time * 1.8))
            c["detach_probability"] = 0.10
            spiral = normal * 0.045 * sin(round_time * 0.9) + prograde * 0.02
            c["thrust"] = spiral - radial * clamp((r - 5.6) * 0.022, -0.025, 0.035)
            c["swirl_strength"] = 0.35 + 0.25 * sin(round_time * 0.5)

        elif self.mode == "CAREFUL_EVADE":
            c["shed_multiplier"] = 0.75
            c["detach_probability"] = 0.05
            c["thrust"] = radial * 0.18 + prograde * 0.06
            if r > ATM_RADIUS + 0.85:
                self.next_mode("CURIOUS_ORBIT")

        if human_override_ai or self.human_override_timer > 0:
            c["thrust"] *= 0.15

        c["name"] = self.mode
        self.controls = c
        return c

ai = AIController()

# -----------------------------
# Human controls
# -----------------------------

def keydown(evt):
    global paused, global_shed_multiplier, human_override_ai
    k = evt.key
    keys_down.add(k)

    if k == " ":
        paused = not paused
    elif k.lower() == "a":
        ai.enabled = not ai.enabled
    elif k.lower() == "o":
        human_override_ai = not human_override_ai
    elif k.lower() == "r":
        reset_simulation(randomize=True)
    elif k.lower() == "n":
        ai.next_mode()
    elif k == "[":
        global_shed_multiplier = clamp(global_shed_multiplier * 0.82, 0.08, 5.0)
    elif k == "]":
        global_shed_multiplier = clamp(global_shed_multiplier * 1.22, 0.08, 5.0)

def keyup(evt):
    k = evt.key
    if k in keys_down:
        keys_down.remove(k)

scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

def human_thrust(dt):
    thrust = vector(0, 0, 0)
    manual_active = False
    radial = safe_norm(comet.pos)
    prograde = safe_norm(comet.vel, tangential_direction(comet.pos))
    normal = safe_norm(cross(radial, prograde), vector(0, 1, 0))

    strength = 0.18

    def down(name):
        return name in keys_down or name.upper() in keys_down

    if down("w"):
        thrust += prograde * strength
        manual_active = True
    if down("s"):
        thrust -= prograde * strength
        manual_active = True
    if "up" in keys_down:
        thrust += radial * strength
        manual_active = True
    if "down" in keys_down:
        thrust -= radial * strength
        manual_active = True
    if "left" in keys_down:
        thrust += normal * strength
        manual_active = True
    if "right" in keys_down:
        thrust -= normal * strength
        manual_active = True
    if down("x"):
        collect_nearby_ice(radius=0.95, max_collect=3)
        manual_active = True

    if manual_active:
        ai.human_override_timer = 1.4
    else:
        ai.human_override_timer = max(0, ai.human_override_timer - dt)

    return thrust, down("z")

# -----------------------------
# Reset / round loop
# -----------------------------

def reset_simulation(randomize=True):
    global particles, marks, attached_shards
    global round_time, round_id, global_collision_count, emit_accumulator, comet_spin

    for p in particles:
        p.destroy()
    for m in marks:
        m["obj"].visible = False
    for s in attached_shards:
        s["obj"].visible = False

    particles = []
    marks = []
    attached_shards = []

    round_id += 1
    round_time = 0.0
    global_collision_count = 0
    emit_accumulator = 0.0
    comet_spin = 0.0

    if randomize:
        rr = uniform(4.4, 6.2)
        theta = uniform(0, 2 * pi)
        orbit_normal = safe_norm(vector(uniform(-0.25, 0.25), 1.0, uniform(-0.25, 0.25)))
        rough_radial = safe_norm(vector(cos(theta), uniform(-0.08, 0.08), sin(theta)))
        radial = safe_norm(cross(orbit_normal, cross(rough_radial, orbit_normal)), rough_radial)
        tangent = safe_norm(cross(orbit_normal, radial))
        comet.pos = radial * rr
        comet.vel = tangent * sqrt(MU / rr) * uniform(0.88, 1.08) + radial * uniform(-0.15, 0.12)
    else:
        comet.pos = vector(5.2, 0, 0)
        comet.vel = vector(0, 0, sqrt(MU / 5.2))

    comet.clear_trail()
    comet.radius = COMET_RADIUS
    comet.color = ICE_BLUE
    comet.opacity = 1.0

    for _ in range(16):
        create_attached_shard()

    ai.last_metric = None
    ai.stagnation_timer = 0.0
    ai.metric_timer = 0.0
    ai.reset_delay = 0.0
    ai.complete = False

# Initial ice crystals
for _ in range(16):
    create_attached_shard()

# -----------------------------
# Physics update
# -----------------------------

def update_comet(dt, controls, manual_accel):
    r = mag(comet.pos)
    radial = safe_norm(comet.pos)

    gravity = -MU * comet.pos / max(r ** 3, 0.04)
    accel = gravity + controls["thrust"] + manual_accel

    if PLANET_RADIUS < r < ATM_RADIUS:
        depth = clamp((ATM_RADIUS - r) / (ATM_RADIUS - PLANET_RADIUS), 0, 1)
        comet.vel *= (1.0 - clamp(0.012 * depth * dt * 60, 0, 0.08))
        if random() < 0.025 * depth:
            create_atmosphere_mark(comet.pos + rand_perp(radial) * 0.05, comet.vel, depth)

    comet.vel += accel * dt
    comet.pos += comet.vel * dt

    # Bounce if the comet nucleus grazes the planet surface.
    r2 = mag(comet.pos)
    if r2 < PLANET_RADIUS + COMET_RADIUS:
        radial2 = safe_norm(comet.pos)
        comet.pos = radial2 * (PLANET_RADIUS + COMET_RADIUS + 0.02)
        vn = dot(comet.vel, radial2)
        comet.vel = comet.vel - 1.65 * vn * radial2
        comet.vel *= 0.76
        create_surface_mark(comet.pos, comet.vel)

def update_particles(dt, controls):
    alive = []
    for p in particles:
        if p.update(dt, controls):
            alive.append(p)
        else:
            p.destroy()
    particles[:] = alive

# -----------------------------
# Visual update
# -----------------------------

def update_visuals(controls):
    away_from_sun = safe_norm(comet.pos - SUN_POS)
    comet_label.pos = comet.pos + vector(0, 0.42, 0)
    tail_axis_arrow.pos = comet.pos
    tail_axis_arrow.axis = away_from_sun * 0.85
    tail_axis_arrow.opacity = 0.25 + 0.10 * clamp(controls["shed_multiplier"] / 3.0, 0, 1)

    atmosphere.opacity = 0.14 + 0.045 * sin(round_time * 0.7)
    inner_atmosphere.opacity = 0.045 + 0.025 * max(0, sin(round_time * 1.1))

    mode_marker.pos = safe_norm(comet.pos, vector(0, 1, 0)) * 2.42
    mode_marker.color = ai.MODE_COLORS.get(ai.mode, vector(0.2, 0.55, 1.0))
    mode_marker.radius = 0.075 + 0.025 * sin(round_time * 3.0)

    state = ai.get_state()
    dashboard.text = (
        f"Round {round_id}   Time {round_time:5.1f}s\n"
        f"AI: {'ON' if ai.enabled else 'OFF'}   Mode: {ai.mode}\n"
        f"Paused: {'YES' if paused else 'NO'}   Human override: {'ON' if human_override_ai else 'OFF'}\n"
        f"Particles: {len(particles):3d}/{MAX_PARTICLES}   Attached ice: {len(attached_shards):2d}\n"
        f"Atmosphere collisions/marks: {global_collision_count:3d}\n"
        f"Comet distance: {state['r']:.2f}   speed: {state['speed']:.2f}\n"
        f"Shedding x{global_shed_multiplier * controls['shed_multiplier']:.2f}   swirl {controls['swirl_strength']:.2f}"
    )

# -----------------------------
# Main loop
# -----------------------------

while True:
    rate(60)

    if paused:
        update_visuals(ai.controls)
        continue

    round_time += DT

    manual_accel, manual_spill = human_thrust(DT)
    controls = ai.update(DT)

    update_comet(DT, controls, manual_accel)
    update_attached_shards(DT)
    emit_ice_particles(DT, controls, manual_spill=manual_spill or controls["marker_pulse"])
    update_particles(DT, controls)
    update_marks(DT)

    if controls["collect_radius"] > 0 and random() < 0.04:
        collect_nearby_ice(radius=controls["collect_radius"], max_collect=1)

    if len(attached_shards) < 8 and random() < 0.015:
        create_attached_shard()

    update_visuals(controls)
