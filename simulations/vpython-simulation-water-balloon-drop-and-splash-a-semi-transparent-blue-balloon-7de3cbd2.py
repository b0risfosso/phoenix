from vpython import *
import random
import math

# ------------------------------------------------------------
# Water Balloon Drop and Splash - VPython Simulation
# Includes an automatic expressive AI controller plus keyboard control.
# ------------------------------------------------------------

scene = canvas(
    title="Water Balloon Drop and Splash - AI Controlled VPython Simulation",
    width=1100,
    height=720,
    background=vector(0.88, 0.95, 1.0)
)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.center = vector(0, 2.2, 0)
scene.range = 8.0

# -----------------------------
# General helpers
# -----------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0, 1)

def rand_range(a, b):
    return random.uniform(a, b)

def v_xz(v):
    return vector(v.x, 0, v.z)

def safe_norm(v):
    m = mag(v)
    if m <= 1e-9:
        return vector(0, 0, 0)
    return v / m

def random_xz_unit():
    a = rand_range(0, 2 * math.pi)
    return vector(math.cos(a), 0, math.sin(a))

def random_point_in_disc(radius):
    a = rand_range(0, 2 * math.pi)
    r = radius * math.sqrt(random.random())
    return vector(math.cos(a) * r, 0, math.sin(a) * r)

# -----------------------------
# Constants
# -----------------------------

GROUND_Y = 0.0
GROUND_HALF = 6.5
BALLOON_R = 0.55
GUIDE_Y = 8.15
BALLOON_READY_OFFSET = vector(0, -0.88, 0)
GRAVITY = vector(0, -9.8, 0)
DT = 1 / 60

PHASE_READY = "READY / ATTACHED"
PHASE_FALLING = "FALLING / DETACHED"
PHASE_IMPACT = "IMPACT STRETCH"
PHASE_SPLASH = "BURST SPLASH"
PHASE_COMPLETE = "COMPLETE / WET PATCH"

# -----------------------------
# Static scene objects
# -----------------------------

ground = box(
    pos=vector(0, -0.035, 0),
    size=vector(GROUND_HALF * 2.2, 0.07, GROUND_HALF * 2.2),
    color=vector(0.93, 0.91, 0.86)
)

# Light grid on floor
grid_lines = []
for i in range(-6, 7):
    grid_lines.append(curve(
        pos=[vector(i, 0.006, -GROUND_HALF), vector(i, 0.006, GROUND_HALF)],
        radius=0.006,
        color=vector(0.78, 0.82, 0.82)
    ))
    grid_lines.append(curve(
        pos=[vector(-GROUND_HALF, 0.006, i), vector(GROUND_HALF, 0.006, i)],
        radius=0.006,
        color=vector(0.78, 0.82, 0.82)
    ))

drop_zone_ring = ring(
    pos=vector(0, 0.018, 0),
    axis=vector(0, 1, 0),
    radius=1.1,
    thickness=0.015,
    color=vector(0.45, 0.72, 0.92),
    opacity=0.28
)

# Wet patch: thin circular stain that spreads after burst.
wet_patch = cylinder(
    pos=vector(0, 0.012, 0),
    axis=vector(0, 0.006, 0),
    radius=0.02,
    color=vector(0.1, 0.55, 1.0),
    opacity=0.0
)

# Visual AI / human guide drone.
guide = sphere(
    pos=vector(0, GUIDE_Y, 0),
    radius=0.13,
    color=vector(1.0, 0.62, 0.18),
    emissive=True
)
guide_ring = ring(
    pos=guide.pos,
    axis=vector(0, 1, 0),
    radius=0.28,
    thickness=0.025,
    color=vector(1.0, 0.75, 0.25)
)
guide_orbit_ring = ring(
    pos=guide.pos,
    axis=vector(1, 0, 0),
    radius=0.19,
    thickness=0.015,
    color=vector(1.0, 0.88, 0.4)
)

# Tether showing attached state before release.
tether = cylinder(
    pos=guide.pos,
    axis=vector(0, -0.8, 0),
    radius=0.012,
    color=vector(0.55, 0.68, 0.9),
    opacity=0.55
)

# Balloon shell and knot.
balloon = sphere(
    pos=guide.pos + BALLOON_READY_OFFSET,
    radius=BALLOON_R,
    size=vector(2 * BALLOON_R, 2 * BALLOON_R, 2 * BALLOON_R),
    color=vector(0.05, 0.45, 1.0),
    opacity=0.42
)
balloon_knot = cone(
    pos=balloon.pos + vector(0, -BALLOON_R - 0.09, 0),
    axis=vector(0, -0.21, 0),
    radius=0.12,
    color=vector(0.05, 0.28, 0.85),
    opacity=0.55
)

# Wind arrow and labels.
wind_arrow = arrow(
    pos=vector(-5.4, 0.25, -5.35),
    axis=vector(0.001, 0, 0),
    shaftwidth=0.05,
    color=vector(0.1, 0.65, 0.95)
)
wind_label = label(
    pos=wind_arrow.pos + vector(0, 0.42, 0),
    text="wind",
    height=12,
    border=4,
    box=False,
    color=vector(0.1, 0.38, 0.58)
)

status_label = label(
    pos=vector(0, 5.35, 0),
    text="",
    height=13,
    box=False,
    color=vector(0.12, 0.2, 0.28)
)

mode_label = label(
    pos=vector(0, 6.0, 0),
    text="",
    height=15,
    box=False,
    color=vector(0.15, 0.25, 0.38)
)

# -----------------------------
# Simulation state
# -----------------------------

phase = PHASE_READY
paused = False
sim_time = 0.0
round_number = 1

balloon_velocity = vector(0, 0, 0)
impact_elapsed = 0.0
impact_duration = 0.24
impact_point = vector(0, 0, 0)
burst_time = -999.0

droplets = []
wet_marks = []
splash_rings = []

wet_center = vector(0, 0, 0)
wet_radius = 0.02
wet_target_radius = 0.02
wet_opacity = 0.0
total_droplets_created = 0

wind = vector(0, 0, 0)

human_override_until = 0.0
last_caption_update = 0.0

# -----------------------------
# Particle and splash objects
# -----------------------------

class Droplet:
    def __init__(self, pos, velocity, radius, ttl, shade, trail=False):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.velocity = vector(velocity.x, velocity.y, velocity.z)
        self.radius0 = radius
        self.radius = radius
        self.ttl = ttl
        self.age = 0.0
        self.ground_contacts = 0
        self.dead = False
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=shade,
            opacity=0.76,
            make_trail=trail,
            retain=16,
            trail_radius=max(0.006, radius * 0.18),
            interval=2
        )

    def update(self, dt):
        global wet_target_radius

        if self.dead:
            return False

        self.age += dt

        # Air physics: gravity, wind, simple drag.
        self.velocity += GRAVITY * dt
        self.velocity += wind * 0.95 * dt
        self.velocity += -self.velocity * 0.19 * dt

        self.pos += self.velocity * dt

        hit_floor = False

        if self.pos.y - self.radius <= GROUND_Y:
            self.pos.y = GROUND_Y + self.radius
            if self.velocity.y < 0:
                hit_floor = True
                self.ground_contacts += 1

                bounce = rand_range(0.22, 0.52)
                if self.radius < 0.035 or self.ground_contacts > 3:
                    bounce *= 0.35

                self.velocity.y = abs(self.velocity.y) * bounce
                self.velocity.x *= rand_range(0.58, 0.82)
                self.velocity.z *= rand_range(0.58, 0.82)

                if random.random() < 0.80:
                    add_wet_mark(vector(self.pos.x, GROUND_Y, self.pos.z), self.radius)

                dist_from_center = mag(v_xz(self.pos - wet_center))
                wet_target_radius = max(wet_target_radius, dist_from_center + rand_range(0.08, 0.25))

        # Soft invisible boundary so droplets remain visible.
        if abs(self.pos.x) > GROUND_HALF:
            self.pos.x = clamp(self.pos.x, -GROUND_HALF, GROUND_HALF)
            self.velocity.x *= -0.45
        if abs(self.pos.z) > GROUND_HALF:
            self.pos.z = clamp(self.pos.z, -GROUND_HALF, GROUND_HALF)
            self.velocity.z *= -0.45

        # Evaporation/shrink.
        shrink_age = self.age / self.ttl
        floor_bonus = 0.12 * self.ground_contacts
        shrink = clamp(shrink_age + floor_bonus, 0, 1)
        self.radius = self.radius0 * ((1 - shrink) ** 0.82)

        if hit_floor and self.radius > 0.02:
            # Tiny rebound glint caused by collision.
            self.obj.opacity = min(0.82, self.obj.opacity + 0.08)

        self.obj.pos = self.pos
        self.obj.radius = max(self.radius, 0.001)
        self.obj.opacity = clamp(0.78 * (1 - shrink), 0.0, 0.78)

        if self.age >= self.ttl or self.radius < 0.012:
            self.dead = True
            self.obj.visible = False
            try:
                self.obj.clear_trail()
            except Exception:
                pass
            return False

        return True


class SplashRing:
    def __init__(self, pos, radius, speed, lifetime, shade):
        self.age = 0.0
        self.radius = radius
        self.speed = speed
        self.lifetime = lifetime
        self.obj = ring(
            pos=vector(pos.x, 0.025, pos.z),
            axis=vector(0, 1, 0),
            radius=radius,
            thickness=0.025,
            color=shade,
            opacity=0.42
        )

    def update(self, dt):
        self.age += dt
        self.radius += self.speed * dt
        self.obj.radius = self.radius
        self.obj.thickness = max(0.006, 0.03 * (1 - self.age / self.lifetime))
        self.obj.opacity = max(0.0, 0.42 * (1 - self.age / self.lifetime))
        if self.age >= self.lifetime:
            self.obj.visible = False
            return False
        return True

# -----------------------------
# Wet floor mark system
# -----------------------------

def add_wet_mark(pos, droplet_radius):
    if len(wet_marks) > 110:
        old = wet_marks.pop(0)
        old.visible = False

    mark_r = clamp(droplet_radius * rand_range(1.8, 4.5), 0.035, 0.22)
    mark = cylinder(
        pos=vector(pos.x, 0.018 + random.random() * 0.002, pos.z),
        axis=vector(0, 0.004, 0),
        radius=mark_r,
        color=vector(0.08, 0.48, 0.95),
        opacity=rand_range(0.09, 0.22)
    )
    wet_marks.append(mark)

def update_wet_marks(dt):
    # Small marks dry slowly; the main patch remains as the dominant final trace.
    for m in wet_marks:
        if m.visible:
            m.opacity = max(0.0, m.opacity - 0.008 * dt)
            if m.opacity <= 0.004:
                m.visible = False

# -----------------------------
# Visual updates
# -----------------------------

def set_balloon_position(pos):
    balloon.pos = pos
    balloon_knot.pos = pos + vector(0, -balloon.size.y / 2 - 0.09, 0)
    balloon_knot.axis = vector(0, -0.21, 0)

def update_guide_visual(dt):
    guide_ring.pos = guide.pos
    guide_orbit_ring.pos = guide.pos
    guide_orbit_ring.rotate(angle=2.1 * dt, axis=vector(0, 1, 0), origin=guide.pos)
    guide_ring.rotate(angle=1.2 * dt, axis=vector(0, 1, 0), origin=guide.pos)

    if phase == PHASE_READY:
        tether.visible = True
        tether.pos = guide.pos
        tether.axis = balloon.pos - guide.pos
    else:
        tether.visible = False

def update_wind_visual():
    global wind
    horizontal = vector(wind.x, 0, wind.z)
    if mag(horizontal) < 0.02:
        wind_arrow.axis = vector(0.001, 0, 0)
    else:
        wind_arrow.axis = horizontal * 0.62
    wind_label.text = "wind ({:+.1f}, {:+.1f})".format(wind.x, wind.z)

def update_wet_patch(dt):
    global wet_radius, wet_opacity

    wet_radius = lerp(wet_radius, wet_target_radius, 3.2 * dt)
    wet_opacity = lerp(wet_opacity, 0.22 if wet_target_radius > 0.08 else 0.0, 2.0 * dt)

    wet_patch.pos = vector(wet_center.x, 0.013, wet_center.z)
    wet_patch.radius = max(0.01, wet_radius)
    wet_patch.opacity = wet_opacity

    drop_zone_ring.pos = vector(guide.pos.x, 0.02, guide.pos.z)
    drop_zone_ring.radius = 0.85 + 0.18 * math.sin(sim_time * 1.6)

def update_labels():
    active = len(droplets)
    status_label.text = (
        "Round {} | {} | droplets: {} | patch radius: {:.2f} | AI: {} | paused: {}\n"
        "Keys: Space drop/reset, R reset, P pause, G toggle AI, B burst, arrows move guide, Z/X/C/V wind, 0 calm wind"
    ).format(
        round_number,
        phase,
        active,
        wet_radius,
        "ON" if ai.enabled else "OFF",
        "YES" if paused else "NO"
    )

    mode_label.text = "AI behavior mode: {}{}".format(
        ai.mode,
        "  (human override)" if sim_time < human_override_until else ""
    )

# -----------------------------
# Simulation actions
# -----------------------------

def reset_round(choose_ai_mode=True):
    global phase, balloon_velocity, impact_elapsed, impact_point, burst_time
    global droplets, wet_marks, splash_rings
    global wet_center, wet_radius, wet_target_radius, wet_opacity, wind
    global round_number, total_droplets_created

    for d in droplets:
        d.obj.visible = False
        try:
            d.obj.clear_trail()
        except Exception:
            pass
    droplets = []

    for m in wet_marks:
        m.visible = False
    wet_marks = []

    for r in splash_rings:
        r.obj.visible = False
    splash_rings = []

    phase = PHASE_READY
    balloon_velocity = vector(0, 0, 0)
    impact_elapsed = 0.0
    burst_time = -999.0
    total_droplets_created = 0

    wet_center = vector(guide.pos.x, 0, guide.pos.z)
    wet_radius = 0.02
    wet_target_radius = 0.02
    wet_opacity = 0.0
    wet_patch.radius = wet_radius
    wet_patch.opacity = 0.0
    wet_patch.pos = vector(wet_center.x, 0.013, wet_center.z)

    balloon.visible = True
    balloon_knot.visible = True
    balloon.opacity = 0.42
    balloon.color = vector(0.05, 0.45, 1.0)
    balloon.size = vector(2 * BALLOON_R, 2 * BALLOON_R, 2 * BALLOON_R)
    set_balloon_position(guide.pos + BALLOON_READY_OFFSET)

    wind = vector(0, 0, 0)

    if choose_ai_mode:
        ai.start_new_round()

def start_drop():
    global phase, balloon_velocity
    if phase == PHASE_READY:
        phase = PHASE_FALLING
        balloon_velocity = vector(wind.x * 0.18, 0.0, wind.z * 0.18)

def start_impact():
    global phase, impact_elapsed, impact_point, balloon_velocity
    phase = PHASE_IMPACT
    impact_elapsed = 0.0
    impact_point = vector(balloon.pos.x, GROUND_Y, balloon.pos.z)
    balloon_velocity = vector(0, 0, 0)

def burst_balloon():
    global phase, burst_time, wet_center, wet_target_radius, total_droplets_created
    global droplets, splash_rings

    if phase not in [PHASE_FALLING, PHASE_IMPACT, PHASE_READY]:
        return

    phase = PHASE_SPLASH
    burst_time = sim_time

    wet_center = vector(balloon.pos.x, GROUND_Y, balloon.pos.z)
    wet_target_radius = max(wet_target_radius, 0.68)

    balloon.visible = False
    balloon_knot.visible = False

    base = vector(wet_center.x, GROUND_Y + 0.14, wet_center.z)

    # Main splash droplets.
    count = 132
    for i in range(count):
        radial = random_xz_unit()
        speed = rand_range(1.3, 5.9)
        upward = rand_range(0.6, 4.2)
        if random.random() < 0.22:
            speed *= rand_range(1.2, 1.9)
            upward *= rand_range(0.4, 0.8)

        pos = base + random_point_in_disc(0.25) + vector(0, rand_range(0.0, 0.25), 0)
        vel = radial * speed + vector(0, upward, 0) + wind * rand_range(0.12, 0.34)

        radius = rand_range(0.028, 0.084)
        ttl = rand_range(1.4, 4.4)
        shade = vector(
            rand_range(0.03, 0.12),
            rand_range(0.38, 0.72),
            rand_range(0.88, 1.0)
        )
        trail = random.random() < 0.22
        droplets.append(Droplet(pos, vel, radius, ttl, shade, trail))

    # Fine mist droplets.
    for i in range(55):
        radial = random_xz_unit()
        pos = base + random_point_in_disc(0.15) + vector(0, rand_range(0.1, 0.45), 0)
        vel = radial * rand_range(2.0, 7.5) + vector(0, rand_range(1.2, 5.5), 0) + wind * 0.22
        radius = rand_range(0.014, 0.034)
        ttl = rand_range(0.8, 2.3)
        shade = vector(0.35, rand_range(0.72, 0.9), 1.0)
        droplets.append(Droplet(pos, vel, radius, ttl, shade, False))

    total_droplets_created = len(droplets)

    splash_rings.append(SplashRing(wet_center, 0.18, 2.9, 1.05, vector(0.12, 0.58, 1.0)))
    splash_rings.append(SplashRing(wet_center, 0.08, 4.5, 0.75, vector(0.36, 0.78, 1.0)))

    for _ in range(20):
        add_wet_mark(wet_center + random_point_in_disc(rand_range(0.05, 0.6)), rand_range(0.035, 0.08))

def mark_complete():
    global phase
    if phase == PHASE_SPLASH:
        phase = PHASE_COMPLETE

def move_guide_by(dx, dz):
    guide.pos.x = clamp(guide.pos.x + dx, -4.8, 4.8)
    guide.pos.z = clamp(guide.pos.z + dz, -4.8, 4.8)
    if phase == PHASE_READY:
        set_balloon_position(guide.pos + BALLOON_READY_OFFSET)

def set_guide_target_pos(target, speed, dt):
    delta = vector(target.x, GUIDE_Y, target.z) - guide.pos
    step = speed * dt
    if mag(delta) <= step:
        guide.pos = vector(target.x, GUIDE_Y, target.z)
    else:
        guide.pos += safe_norm(delta) * step

    guide.pos.x = clamp(guide.pos.x, -4.8, 4.8)
    guide.pos.z = clamp(guide.pos.z, -4.8, 4.8)

    if phase == PHASE_READY:
        set_balloon_position(guide.pos + BALLOON_READY_OFFSET)

# -----------------------------
# Expressive AI controller
# -----------------------------

class AIController:
    def __init__(self):
        self.enabled = True

        self.behavior_modes = [
            "CAREFUL_CENTER_DROP",
            "PLAYFUL_ORBIT_DROP",
            "WIND_PAINTER",
            "CHAOTIC_GUST",
            "RITUAL_STILLNESS",
            "EDGE_SWEEPER",
            "CURIOUS_NEAR_PATCH",
            "ARTISTIC_SPIRAL"
        ]

        self.mode = "CAREFUL_CENTER_DROP"
        self.previous_mode = None
        self.mode_started = 0.0
        self.target = vector(0, GUIDE_Y, 0)
        self.drop_after = 1.5
        self.watch_started = 0.0
        self.complete_started = 0.0
        self.loop_delay = 2.4
        self.last_action_time = 0.0

        # Stagnation/completion detector.
        self.last_check_time = 0.0
        self.last_count = 0
        self.last_patch_radius = 0.0
        self.last_motion_score = 999.0
        self.stagnant_time = 0.0

        self.phase_memory = phase

    def start_new_round(self):
        global round_number

        choices = [m for m in self.behavior_modes if m != self.mode]
        if not choices:
            choices = self.behavior_modes[:]

        self.previous_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_started = sim_time
        self.last_action_time = sim_time
        self.watch_started = 0.0
        self.complete_started = 0.0
        self.stagnant_time = 0.0
        self.last_check_time = sim_time
        self.last_count = 0
        self.last_patch_radius = 0.0
        self.last_motion_score = 999.0

        self.loop_delay = rand_range(1.4, 3.6)
        self.drop_after = rand_range(0.9, 2.6)

        if self.mode == "CAREFUL_CENTER_DROP":
            self.target = vector(rand_range(-0.35, 0.35), GUIDE_Y, rand_range(-0.35, 0.35))
            guide.color = vector(1.0, 0.62, 0.18)

        elif self.mode == "PLAYFUL_ORBIT_DROP":
            a = rand_range(0, 2 * math.pi)
            self.target = vector(math.cos(a) * 1.8, GUIDE_Y, math.sin(a) * 1.8)
            guide.color = vector(1.0, 0.74, 0.18)

        elif self.mode == "WIND_PAINTER":
            self.target = vector(rand_range(-2.5, 2.5), GUIDE_Y, rand_range(-2.5, 2.5))
            guide.color = vector(0.2, 0.75, 1.0)

        elif self.mode == "CHAOTIC_GUST":
            self.target = vector(rand_range(-4.0, 4.0), GUIDE_Y, rand_range(-4.0, 4.0))
            guide.color = vector(1.0, 0.35, 0.22)

        elif self.mode == "RITUAL_STILLNESS":
            self.target = vector(0, GUIDE_Y, 0)
            self.drop_after = rand_range(2.0, 3.8)
            guide.color = vector(0.82, 0.65, 1.0)

        elif self.mode == "EDGE_SWEEPER":
            a = rand_range(0, 2 * math.pi)
            self.target = vector(math.cos(a) * 3.8, GUIDE_Y, math.sin(a) * 3.8)
            guide.color = vector(0.4, 1.0, 0.6)

        elif self.mode == "CURIOUS_NEAR_PATCH":
            self.target = vector(rand_range(-1.2, 1.2), GUIDE_Y, rand_range(-1.2, 1.2))
            guide.color = vector(1.0, 0.95, 0.35)

        elif self.mode == "ARTISTIC_SPIRAL":
            self.target = vector(rand_range(-1.0, 1.0), GUIDE_Y, rand_range(-1.0, 1.0))
            guide.color = vector(0.95, 0.45, 1.0)

    def state_snapshot(self):
        avg_speed = 0.0
        if droplets:
            avg_speed = sum(mag(d.velocity) for d in droplets) / len(droplets)

        return {
            "time": sim_time,
            "phase": phase,
            "round": round_number,
            "balloon_pos": vector(balloon.pos.x, balloon.pos.y, balloon.pos.z),
            "balloon_velocity": vector(balloon_velocity.x, balloon_velocity.y, balloon_velocity.z),
            "guide_pos": vector(guide.pos.x, guide.pos.y, guide.pos.z),
            "droplet_count": len(droplets),
            "average_droplet_speed": avg_speed,
            "wet_center": vector(wet_center.x, wet_center.y, wet_center.z),
            "wet_radius": wet_radius,
            "wet_target_radius": wet_target_radius,
            "wind": vector(wind.x, wind.y, wind.z)
        }

    def choose_wind(self, dt):
        global wind

        t = sim_time - self.mode_started

        if self.mode == "CAREFUL_CENTER_DROP":
            desired = vector(0.15 * math.sin(t * 0.9), 0, 0.15 * math.cos(t * 0.7))

        elif self.mode == "PLAYFUL_ORBIT_DROP":
            desired = vector(0.7 * math.cos(t * 1.4), 0, 0.7 * math.sin(t * 1.4))

        elif self.mode == "WIND_PAINTER":
            desired = vector(1.35 * math.sin(t * 1.1), 0, 1.35 * math.cos(t * 0.83))

        elif self.mode == "CHAOTIC_GUST":
            if random.random() < 0.045:
                desired = vector(rand_range(-2.8, 2.8), 0, rand_range(-2.8, 2.8))
            else:
                desired = wind

        elif self.mode == "RITUAL_STILLNESS":
            desired = vector(0, 0, 0)

        elif self.mode == "EDGE_SWEEPER":
            # Blow toward the center from whichever edge the guide occupies.
            desired = -safe_norm(v_xz(guide.pos)) * 1.2

        elif self.mode == "CURIOUS_NEAR_PATCH":
            # Gentle reversing breeze around the latest wet mark.
            tangent = vector(-wet_center.z, 0, wet_center.x)
            if mag(tangent) < 0.1:
                tangent = vector(math.cos(t), 0, math.sin(t))
            desired = safe_norm(tangent) * (0.75 + 0.35 * math.sin(t * 2.0))

        elif self.mode == "ARTISTIC_SPIRAL":
            desired = vector(math.cos(t * 1.8), 0, math.sin(t * 1.8)) * (0.4 + 1.1 * abs(math.sin(t * 0.45)))

        else:
            desired = vector(0, 0, 0)

        max_wind = 3.0
        desired.x = clamp(desired.x, -max_wind, max_wind)
        desired.z = clamp(desired.z, -max_wind, max_wind)
        wind = wind + (desired - wind) * clamp(1.9 * dt, 0, 1)

    def choose_ready_motion(self, dt):
        elapsed = sim_time - self.mode_started
        t = elapsed

        if self.mode == "PLAYFUL_ORBIT_DROP":
            r = 1.7 + 0.5 * math.sin(t * 0.7)
            self.target = vector(math.cos(t * 1.25) * r, GUIDE_Y, math.sin(t * 1.25) * r)

        elif self.mode == "CHAOTIC_GUST":
            if sim_time - self.last_action_time > rand_range(0.35, 0.9):
                self.target = vector(rand_range(-4.2, 4.2), GUIDE_Y, rand_range(-4.2, 4.2))
                self.last_action_time = sim_time

        elif self.mode == "EDGE_SWEEPER":
            r = 4.0
            self.target = vector(math.cos(t * 0.9) * r, GUIDE_Y, math.sin(t * 0.9) * r)

        elif self.mode == "RITUAL_STILLNESS":
            pulse = 0.15 * math.sin(t * 2.7)
            self.target = vector(pulse, GUIDE_Y, pulse * math.cos(t * 0.5))

        elif self.mode == "ARTISTIC_SPIRAL":
            r = clamp(0.18 + t * 0.5, 0.2, 3.2)
            self.target = vector(math.cos(t * 2.4) * r, GUIDE_Y, math.sin(t * 2.4) * r)

        elif self.mode == "CURIOUS_NEAR_PATCH":
            self.target = vector(
                0.9 * math.sin(t * 1.1),
                GUIDE_Y,
                0.9 * math.sin(t * 1.7 + 1.1)
            )

        set_guide_target_pos(self.target, speed=2.4 if self.mode != "CHAOTIC_GUST" else 4.1, dt=dt)

        distance_to_target = mag(v_xz(guide.pos - self.target))

        if elapsed > self.drop_after and distance_to_target < 0.22:
            start_drop()

        if elapsed > 5.5:
            start_drop()

    def choose_splash_motion(self, dt):
        # Drone visibly studies/orbits the splash while wind continues to sculpt droplets.
        t = sim_time - burst_time

        if self.mode in ["PLAYFUL_ORBIT_DROP", "ARTISTIC_SPIRAL", "CURIOUS_NEAR_PATCH"]:
            r = 1.0 + wet_radius * 0.55 + 0.25 * math.sin(t * 1.4)
            target = wet_center + vector(math.cos(t * 1.15) * r, GUIDE_Y, math.sin(t * 1.15) * r)
            set_guide_target_pos(target, 2.5, dt)

        elif self.mode == "CHAOTIC_GUST":
            if random.random() < 0.03:
                target = wet_center + vector(rand_range(-3.8, 3.8), GUIDE_Y, rand_range(-3.8, 3.8))
                set_guide_target_pos(target, 5.0, dt)

        elif self.mode == "RITUAL_STILLNESS":
            target = vector(wet_center.x, GUIDE_Y, wet_center.z)
            set_guide_target_pos(target, 1.1, dt)

        elif self.mode == "EDGE_SWEEPER":
            target = vector(-guide.pos.x, GUIDE_Y, -guide.pos.z)
            if sim_time - self.last_action_time > 1.2:
                self.last_action_time = sim_time
            set_guide_target_pos(target, 1.6, dt)

        else:
            target = wet_center + vector(math.cos(t * 0.6), GUIDE_Y, math.sin(t * 0.6))
            set_guide_target_pos(target, 1.8, dt)

    def completion_detector(self, dt):
        if phase != PHASE_SPLASH:
            self.stagnant_time = 0.0
            return False

        if sim_time - self.last_check_time < 0.45:
            return False

        interval = sim_time - self.last_check_time
        self.last_check_time = sim_time

        count = len(droplets)
        avg_speed = 0.0
        if droplets:
            avg_speed = sum(mag(d.velocity) for d in droplets) / len(droplets)

        count_change = abs(count - self.last_count)
        radius_change = abs(wet_radius - self.last_patch_radius)

        stable = (
            count <= 2 or
            (count_change <= 2 and radius_change < 0.018 and avg_speed < 0.16) or
            (sim_time - burst_time > 8.5)
        )

        if stable:
            self.stagnant_time += interval
        else:
            self.stagnant_time = 0.0

        self.last_count = count
        self.last_patch_radius = wet_radius
        self.last_motion_score = avg_speed

        return self.stagnant_time > 1.0 or count == 0

    def update(self, dt):
        global round_number

        if not self.enabled:
            return

        self.choose_wind(dt)

        if sim_time < human_override_until:
            # Keyboard control temporarily overrides motion/drop decisions,
            # but AI wind and completion loop continue to keep the system alive.
            if self.completion_detector(dt):
                mark_complete()
            if phase == PHASE_COMPLETE:
                if self.complete_started <= 0:
                    self.complete_started = sim_time
                if sim_time - self.complete_started > self.loop_delay:
                    round_number += 1
                    reset_round(choose_ai_mode=True)
            return

        if phase == PHASE_READY:
            self.choose_ready_motion(dt)

        elif phase in [PHASE_FALLING, PHASE_IMPACT]:
            # While detached, the drone hovers above and reacts.
            if self.mode == "CHAOTIC_GUST" and phase == PHASE_FALLING:
                if balloon.pos.y < 2.4 and random.random() < 0.025:
                    burst_balloon()

            hover = vector(balloon.pos.x, GUIDE_Y, balloon.pos.z)
            if self.mode == "PLAYFUL_ORBIT_DROP":
                t = sim_time - self.mode_started
                hover += vector(math.cos(t * 2.3), 0, math.sin(t * 2.3)) * 0.9
            set_guide_target_pos(hover, 2.8, dt)

        elif phase == PHASE_SPLASH:
            self.choose_splash_motion(dt)
            if self.completion_detector(dt):
                mark_complete()

        elif phase == PHASE_COMPLETE:
            if self.complete_started <= 0:
                self.complete_started = sim_time

            # AI "observes" the final wet patch, then starts the next round.
            t = sim_time - self.complete_started
            observe_radius = max(0.7, wet_radius * 0.38)
            observe_target = wet_center + vector(
                math.cos(t * 1.3) * observe_radius,
                GUIDE_Y,
                math.sin(t * 1.3) * observe_radius
            )
            set_guide_target_pos(observe_target, 1.9, dt)

            if sim_time - self.complete_started > self.loop_delay:
                round_number += 1
                reset_round(choose_ai_mode=True)

    def next_mode_now(self):
        self.start_new_round()

ai = AIController()
ai.start_new_round()

# -----------------------------
# Keyboard control
# -----------------------------

def human_override(seconds=3.0):
    global human_override_until
    human_override_until = sim_time + seconds

def keydown(evt):
    global paused, wind, round_number

    k = evt.key

    if k == "p":
        paused = not paused
        return

    if k == "g":
        ai.enabled = not ai.enabled
        human_override(0.5)
        return

    if k == "r":
        round_number += 1
        reset_round(choose_ai_mode=True)
        human_override(1.0)
        return

    if k == "m":
        ai.next_mode_now()
        human_override(0.5)
        return

    if k == " ":
        if phase == PHASE_READY:
            start_drop()
        elif phase == PHASE_COMPLETE:
            round_number += 1
            reset_round(choose_ai_mode=True)
        human_override(2.2)
        return

    if k == "b":
        if phase in [PHASE_READY, PHASE_FALLING, PHASE_IMPACT]:
            burst_balloon()
        human_override(2.0)
        return

    step = 0.32
    if k == "left":
        move_guide_by(-step, 0)
        human_override()
    elif k == "right":
        move_guide_by(step, 0)
        human_override()
    elif k == "up":
        move_guide_by(0, -step)
        human_override()
    elif k == "down":
        move_guide_by(0, step)
        human_override()

    # Human wind steering.
    elif k == "z":
        wind.x -= 0.35
        wind.x = clamp(wind.x, -3.0, 3.0)
        human_override()
    elif k == "x":
        wind.x += 0.35
        wind.x = clamp(wind.x, -3.0, 3.0)
        human_override()
    elif k == "c":
        wind.z += 0.35
        wind.z = clamp(wind.z, -3.0, 3.0)
        human_override()
    elif k == "v":
        wind.z -= 0.35
        wind.z = clamp(wind.z, -3.0, 3.0)
        human_override()
    elif k == "0":
        wind = vector(0, 0, 0)
        human_override()

scene.bind("keydown", keydown)

# -----------------------------
# Main physics update
# -----------------------------

def update_balloon(dt):
    global balloon_velocity, impact_elapsed, wet_center, wet_target_radius

    if phase == PHASE_READY:
        set_balloon_position(guide.pos + BALLOON_READY_OFFSET)

    elif phase == PHASE_FALLING:
        balloon_velocity += GRAVITY * dt
        balloon_velocity += wind * 0.16 * dt
        balloon_velocity += -balloon_velocity * 0.025 * dt

        set_balloon_position(balloon.pos + balloon_velocity * dt)

        if balloon.pos.y - balloon.size.y / 2 <= GROUND_Y:
            start_impact()

    elif phase == PHASE_IMPACT:
        impact_elapsed += dt
        f = clamp(impact_elapsed / impact_duration, 0, 1)
        pulse = math.sin(math.pi * f)

        sx = 2 * BALLOON_R * (1.0 + 0.42 * pulse)
        sy = 2 * BALLOON_R * (1.0 - 0.50 * pulse)
        sz = 2 * BALLOON_R * (1.0 + 0.36 * pulse)

        balloon.size = vector(sx, sy, sz)
        balloon.opacity = 0.42 + 0.12 * pulse
        balloon.color = vector(0.04 + 0.08 * pulse, 0.48 + 0.06 * pulse, 1.0)

        set_balloon_position(vector(impact_point.x, GROUND_Y + sy / 2, impact_point.z))

        wet_center = vector(impact_point.x, GROUND_Y, impact_point.z)
        wet_target_radius = max(wet_target_radius, 0.28 + 0.15 * pulse)

        if impact_elapsed >= impact_duration:
            burst_balloon()

def update_particles(dt):
    global droplets, splash_rings

    new_droplets = []
    for d in droplets:
        if d.update(dt):
            new_droplets.append(d)
    droplets = new_droplets

    new_rings = []
    for r in splash_rings:
        if r.update(dt):
            new_rings.append(r)
    splash_rings = new_rings

def update_caption_if_needed():
    global last_caption_update
    if sim_time - last_caption_update < 0.25:
        return
    last_caption_update = sim_time

    scene.caption = (
        "\n"
        "Water Balloon Drop and Splash | Semi-transparent balloon, impact stretch, burst droplets, bouncing evaporation, spreading wet patch.\n"
        "AI reads state, chooses guide/wind/drop/reset actions, changes behavior modes, detects completion, and loops new rounds.\n"
        "Keyboard remains active: Space drop/reset | R reset | P pause | G AI on/off | B burst | M new AI mode | Arrows move guide | Z/X/C/V wind | 0 calm wind\n"
    )

# -----------------------------
# Main loop
# -----------------------------

while True:
    rate(60)

    if paused:
        update_guide_visual(DT)
        update_wind_visual()
        update_labels()
        update_caption_if_needed()
        continue

    sim_time += DT

    ai.update(DT)

    update_balloon(DT)
    update_particles(DT)
    update_wet_patch(DT)
    update_wet_marks(DT)

    update_guide_visual(DT)
    update_wind_visual()
    update_labels()
    update_caption_if_needed()

    # If AI is off, still mark completion when the physical action has ended.
    if not ai.enabled and phase == PHASE_SPLASH:
        if len(droplets) == 0 or sim_time - burst_time > 9.0:
            mark_complete()
