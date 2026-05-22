from vpython import *
from random import uniform, randint, choice, random
from math import sin, cos, pi, atan2

scene.title = "Dragon Breathing Fire at Moving Targets - VPython Simulation"
scene.width = 1200
scene.height = 720
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.45, -0.18, -0.88)
scene.center = vector(0, 2.1, 0)
scene.range = 7.8
scene.autoscale = False
scene.ambient = color.gray(0.72)

sun = distant_light(direction=vector(-0.4, -0.8, -0.2), color=vector(0.95, 0.92, 0.82))

ARENA_X_MIN = -7.5
ARENA_X_MAX = 6.8
ARENA_Y_MIN = 0.85
ARENA_Y_MAX = 4.8
ARENA_Z_MIN = -3.8
ARENA_Z_MAX = 3.8

UP = vector(0, 1, 0)


def clamp(x, a, b):
    return max(a, min(b, x))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-7:
        return fallback
    return norm(v)


def lerp(a, b, t):
    return a * (1 - t) + b * t


def color_lerp(a, b, t):
    return vector(a.x * (1 - t) + b.x * t, a.y * (1 - t) + b.y * t, a.z * (1 - t) + b.z * t)


def heat_color(h):
    h = clamp(h, 0, 1)
    cold = vector(0.18, 0.64, 1.0)
    warm = vector(1.0, 0.55, 0.08)
    hot = vector(1.0, 0.08, 0.02)
    whitehot = vector(1.0, 0.95, 0.45)
    if h < 0.45:
        return color_lerp(cold, warm, h / 0.45)
    elif h < 0.82:
        return color_lerp(warm, hot, (h - 0.45) / 0.37)
    else:
        return color_lerp(hot, whitehot, (h - 0.82) / 0.18)


def random_target_pos():
    return vector(uniform(-0.4, 5.9), uniform(1.45, 4.2), uniform(-3.0, 3.0))


def random_target_vel():
    return vector(uniform(-0.85, 0.85), uniform(-0.35, 0.35), uniform(-0.75, 0.75))


floor = box(pos=vector(0, -0.035, 0), size=vector(15.8, 0.05, 8.6), color=vector(0.88, 0.93, 0.85))
back_wall = box(pos=vector(0, 2.2, ARENA_Z_MIN - 0.08), size=vector(15.8, 4.4, 0.035), color=vector(0.86, 0.93, 0.98), opacity=0.18)
front_wall = box(pos=vector(0, 2.2, ARENA_Z_MAX + 0.08), size=vector(15.8, 4.4, 0.035), color=vector(0.86, 0.93, 0.98), opacity=0.18)
ceiling_hint = curve(
    pos=[
        vector(ARENA_X_MIN, ARENA_Y_MAX, ARENA_Z_MIN),
        vector(ARENA_X_MAX, ARENA_Y_MAX, ARENA_Z_MIN),
        vector(ARENA_X_MAX, ARENA_Y_MAX, ARENA_Z_MAX),
        vector(ARENA_X_MIN, ARENA_Y_MAX, ARENA_Z_MAX),
        vector(ARENA_X_MIN, ARENA_Y_MAX, ARENA_Z_MIN),
    ],
    radius=0.02,
    color=vector(0.55, 0.66, 0.82),
    opacity=0.35,
)

status_label = label(
    pos=vector(-1.0, 5.35, 0),
    text="",
    height=13,
    color=vector(0.1, 0.13, 0.16),
    box=False,
    opacity=0,
)

orbit_marker = curve(radius=0.018, color=vector(0.55, 0.35, 1.0), opacity=0.55)
for i in range(121):
    a = 2 * pi * i / 120
    orbit_marker.append(pos=vector(2.1 + cos(a) * 2.1, 2.55, sin(a) * 2.1))
orbit_marker.visible = False


class Droplet:
    def __init__(self, pos, vel, heat=1.0):
        self.pos = vector(pos)
        self.vel = vector(vel)
        self.age = 0
        self.max_age = uniform(2.0, 4.2)
        self.radius = uniform(0.035, 0.075)
        self.heat = heat
        self.stuck = False
        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=vector(1.0, 0.33, 0.03),
            emissive=True,
            opacity=0.92,
        )
        self.trail = curve(radius=self.radius * 0.28, color=vector(1, 0.42, 0.08), retain=12)

    def update(self, dt, scorch_marks):
        self.age += dt
        if not self.stuck:
            self.vel += vector(0, -4.8, 0) * dt
            self.pos += self.vel * dt
            if self.pos.y <= self.radius + 0.02:
                self.pos.y = self.radius + 0.02
                self.vel = vector(self.vel.x * 0.45, abs(self.vel.y) * 0.16, self.vel.z * 0.45)
                if mag(self.vel) < 0.35:
                    self.stuck = True
                    mark = cylinder(
                        pos=vector(self.pos.x, 0.006, self.pos.z),
                        axis=vector(0, 0.012, 0),
                        radius=self.radius * uniform(1.4, 2.7),
                        color=vector(1.0, 0.31, 0.04),
                        emissive=True,
                        opacity=0.38,
                    )
                    scorch_marks.append(mark)
        else:
            self.heat *= 0.986
            self.radius *= 1.004

        fade = clamp(1 - self.age / self.max_age, 0, 1)
        flicker = uniform(-0.08, 0.08)
        self.obj.pos = self.pos
        self.obj.radius = self.radius
        self.obj.color = vector(1.0, clamp(0.28 + self.heat * 0.35 + flicker, 0, 1), 0.03)
        self.obj.opacity = 0.85 * fade
        self.trail.append(pos=self.pos)
        return self.age < self.max_age and self.obj.opacity > 0.02

    def destroy(self):
        self.obj.visible = False
        self.trail.visible = False


class FireParticle:
    def __init__(self, pos, direction, speed, radius, intensity=1.0):
        self.pos = vector(pos)
        self.vel = safe_norm(direction) * speed
        self.age = 0
        self.max_age = uniform(0.42, 0.9)
        self.intensity = intensity
        self.expansion = uniform(0.13, 0.33)
        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=vector(1.0, uniform(0.45, 0.88), 0.03),
            emissive=True,
            opacity=0.82,
        )

    def update(self, dt):
        self.age += dt
        self.pos += self.vel * dt
        self.vel *= 0.985
        self.vel += vector(0, uniform(-0.08, 0.16), 0) * dt
        life_t = clamp(self.age / self.max_age, 0, 1)

        self.obj.pos = self.pos
        self.obj.radius += self.expansion * dt
        flicker = uniform(-0.12, 0.12)
        if life_t < 0.38:
            self.obj.color = vector(1.0, clamp(0.82 + flicker, 0, 1), 0.06)
        elif life_t < 0.72:
            self.obj.color = vector(1.0, clamp(0.42 + flicker, 0, 1), 0.02)
        else:
            self.obj.color = vector(clamp(0.75 + flicker, 0, 1), 0.11, 0.04)
        self.obj.opacity = 0.78 * (1 - life_t)
        return self.age < self.max_age and self.obj.opacity > 0.025

    def destroy(self):
        self.obj.visible = False


class Target:
    next_id = 1

    def __init__(self, pos=None, vel=None, radius=None):
        self.id = Target.next_id
        Target.next_id += 1
        self.pos = vector(pos) if pos is not None else random_target_pos()
        self.vel = vector(vel) if vel is not None else random_target_vel()
        self.radius = radius if radius is not None else uniform(0.20, 0.34)
        self.base_radius = self.radius
        self.heat = 0.0
        self.melted = False
        self.mode = "free"
        self.orbit_center = vector(2.1, 2.55, 0)
        self.orbit_radius = uniform(1.25, 2.55)
        self.orbit_phase = uniform(0, 2 * pi)
        self.orbit_speed = choice([-1, 1]) * uniform(0.55, 1.25)
        self.wobble = uniform(0, 2 * pi)
        self.last_heated_time = -999

        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=heat_color(0),
            shininess=0.72,
            opacity=0.92,
        )
        self.trail = curve(radius=0.012, color=vector(0.35, 0.65, 1.0), retain=40, opacity=0.5)
        self.label = label(
            pos=self.pos + vector(0, self.radius + 0.22, 0),
            text="",
            height=8,
            color=vector(0.12, 0.15, 0.18),
            box=False,
            opacity=0,
        )

    def attach_orbit(self, center=vector(2.1, 2.55, 0), radius=None):
        self.mode = "orbit"
        self.orbit_center = vector(center)
        if radius is not None:
            self.orbit_radius = radius
        rel = self.pos - self.orbit_center
        self.orbit_phase = atan2(rel.z, rel.x)

    def detach(self):
        self.mode = "free"
        tangent = vector(-sin(self.orbit_phase), uniform(-0.18, 0.18), cos(self.orbit_phase))
        self.vel = safe_norm(tangent) * uniform(0.65, 1.25)

    def add_heat(self, amount, now):
        if self.melted:
            return
        self.heat = clamp(self.heat + amount, 0, 1.15)
        self.last_heated_time = now

    def melt(self, droplets, scorch_marks):
        if self.melted:
            return
        self.melted = True
        self.obj.visible = False
        self.trail.visible = False
        self.label.visible = False

        mark = cylinder(
            pos=vector(self.pos.x, 0.004, self.pos.z),
            axis=vector(0, 0.01, 0),
            radius=self.base_radius * 1.65,
            color=vector(0.23, 0.13, 0.07),
            opacity=0.58,
        )
        scorch_marks.append(mark)

        for _ in range(randint(7, 14)):
            v = vector(uniform(-0.65, 0.65), uniform(-0.25, 0.25), uniform(-0.65, 0.65))
            v += vector(0, -uniform(0.15, 1.05), 0)
            droplets.append(Droplet(self.pos + vector(uniform(-0.12, 0.12), 0, uniform(-0.12, 0.12)), v))

    def update(self, dt, now, droplets, scorch_marks):
        if self.melted:
            return

        self.wobble += dt * uniform(0.85, 1.18)

        if self.mode == "orbit":
            self.orbit_phase += self.orbit_speed * dt
            ybob = sin(self.orbit_phase * 1.7 + self.id) * 0.38
            desired = self.orbit_center + vector(cos(self.orbit_phase) * self.orbit_radius, ybob, sin(self.orbit_phase) * self.orbit_radius)
            desired.y = clamp(desired.y, ARENA_Y_MIN + 0.3, ARENA_Y_MAX - 0.25)
            self.vel = (desired - self.pos) * 2.8
            self.pos += self.vel * dt
        else:
            drift = vector(sin(self.wobble * 1.1 + self.id) * 0.12, sin(self.wobble * 1.7) * 0.09, cos(self.wobble * 1.3) * 0.12)
            self.vel += drift * dt
            if mag(self.vel) > 1.45:
                self.vel = norm(self.vel) * 1.45
            self.pos += self.vel * dt

            if self.pos.x < -0.7:
                self.pos.x = -0.7
                self.vel.x = abs(self.vel.x) * uniform(0.7, 1.05)
            if self.pos.x > ARENA_X_MAX - 0.4:
                self.pos.x = ARENA_X_MAX - 0.4
                self.vel.x = -abs(self.vel.x) * uniform(0.7, 1.05)
            if self.pos.y < ARENA_Y_MIN:
                self.pos.y = ARENA_Y_MIN
                self.vel.y = abs(self.vel.y) * uniform(0.7, 1.1)
            if self.pos.y > ARENA_Y_MAX:
                self.pos.y = ARENA_Y_MAX
                self.vel.y = -abs(self.vel.y) * uniform(0.7, 1.1)
            if self.pos.z < ARENA_Z_MIN + 0.3:
                self.pos.z = ARENA_Z_MIN + 0.3
                self.vel.z = abs(self.vel.z) * uniform(0.7, 1.1)
            if self.pos.z > ARENA_Z_MAX - 0.3:
                self.pos.z = ARENA_Z_MAX - 0.3
                self.vel.z = -abs(self.vel.z) * uniform(0.7, 1.1)

        if now - self.last_heated_time > 1.25:
            self.heat = max(0, self.heat - 0.012 * dt)

        if self.heat >= 1.0:
            self.melt(droplets, scorch_marks)
            return

        melt_softening = 1 - max(0, self.heat - 0.72) * 0.48
        self.radius = self.base_radius * melt_softening
        self.obj.pos = self.pos
        self.obj.radius = self.radius
        self.obj.color = heat_color(self.heat)
        self.obj.emissive = self.heat > 0.62
        self.obj.opacity = clamp(0.95 - self.heat * 0.18, 0.66, 0.95)
        self.trail.color = color_lerp(vector(0.35, 0.65, 1.0), vector(1.0, 0.28, 0.03), self.heat)
        self.trail.append(pos=self.pos)
        self.label.pos = self.pos + vector(0, self.radius + 0.22, 0)
        self.label.text = str(int(self.heat * 100)) + "%"

    def destroy(self):
        self.obj.visible = False
        self.trail.visible = False
        self.label.visible = False


class Dragon:
    def __init__(self):
        self.root = vector(-5.85, 1.55, 0)
        self.aim_dir = vector(1, 0.05, 0)
        self.desired_dir = vector(1, 0.05, 0)
        self.neck_len = 2.05
        self.turn_rate = 3.8
        self.fire_accumulator = 0
        self.fire_rate = 96
        self.fire_active = False

        self.body = sphere(pos=vector(-6.75, 0.92, 0), size=vector(2.1, 1.12, 1.28), color=vector(0.22, 0.56, 0.29), shininess=0.45)
        self.belly = sphere(pos=vector(-6.35, 0.76, 0), size=vector(1.25, 0.56, 0.86), color=vector(0.58, 0.78, 0.38), shininess=0.35)
        self.tail = cone(pos=vector(-7.62, 0.95, 0), axis=vector(-1.25, -0.22, 0), radius=0.34, color=vector(0.19, 0.47, 0.25))
        self.left_leg = cylinder(pos=vector(-6.6, 0.33, -0.38), axis=vector(0.4, -0.1, -0.25), radius=0.14, color=vector(0.18, 0.45, 0.24))
        self.right_leg = cylinder(pos=vector(-6.6, 0.33, 0.38), axis=vector(0.4, -0.1, 0.25), radius=0.14, color=vector(0.18, 0.45, 0.24))
        self.wing_l = pyramid(pos=vector(-6.85, 1.28, -0.56), size=vector(1.1, 0.08, 1.2), color=vector(0.34, 0.68, 0.42), opacity=0.45)
        self.wing_r = pyramid(pos=vector(-6.85, 1.28, 0.56), size=vector(1.1, 0.08, 1.2), color=vector(0.34, 0.68, 0.42), opacity=0.45)

        self.neck_segments = []
        for i in range(5):
            self.neck_segments.append(cylinder(pos=self.root, axis=vector(0.2, 0, 0), radius=0.22 - i * 0.018, color=vector(0.2, 0.52, 0.28)))
        self.head = sphere(pos=self.root + self.aim_dir * self.neck_len, size=vector(0.82, 0.58, 0.66), color=vector(0.2, 0.55, 0.28), shininess=0.5)
        self.snout = cone(pos=self.head.pos + self.aim_dir * 0.22, axis=self.aim_dir * 0.72, radius=0.25, color=vector(0.17, 0.47, 0.24))
        self.eye_l = sphere(radius=0.055, color=vector(1, 0.92, 0.18), emissive=True)
        self.eye_r = sphere(radius=0.055, color=vector(1, 0.92, 0.18), emissive=True)
        self.horn_l = cone(radius=0.045, color=vector(0.9, 0.84, 0.58))
        self.horn_r = cone(radius=0.045, color=vector(0.9, 0.84, 0.58))
        self.mouth_glow = local_light(pos=self.mouth_pos(), color=vector(0, 0, 0))

    def mouth_pos(self):
        head_center = self.root + self.aim_dir * self.neck_len + vector(0, 0.15, 0)
        return head_center + self.aim_dir * 0.95 - vector(0, 0.03, 0)

    def set_desired_toward(self, point):
        self.desired_dir = safe_norm(point - self.root, self.aim_dir)

    def update(self, dt):
        k = clamp(self.turn_rate * dt, 0, 1)
        self.aim_dir = safe_norm(self.aim_dir * (1 - k) + self.desired_dir * k, self.aim_dir)

        head_center = self.root + self.aim_dir * self.neck_len + vector(0, 0.15, 0)
        side = safe_norm(cross(UP, self.aim_dir), vector(0, 0, 1))
        top = safe_norm(cross(self.aim_dir, side), UP)

        points = []
        for i in range(6):
            t = i / 5
            arch = sin(pi * t) * 0.25
            points.append(self.root + self.aim_dir * (self.neck_len * t) + vector(0, arch + 0.10 * t, 0))

        for i, seg in enumerate(self.neck_segments):
            p1 = points[i]
            p2 = points[i + 1]
            seg.pos = p1
            seg.axis = p2 - p1
            seg.radius = 0.23 - 0.02 * i

        self.head.pos = head_center
        self.snout.pos = head_center + self.aim_dir * 0.18
        self.snout.axis = self.aim_dir * 0.72
        self.eye_l.pos = head_center + self.aim_dir * 0.36 + side * 0.18 + top * 0.17
        self.eye_r.pos = head_center + self.aim_dir * 0.36 - side * 0.18 + top * 0.17
        self.horn_l.pos = head_center - self.aim_dir * 0.13 + side * 0.17 + top * 0.24
        self.horn_r.pos = head_center - self.aim_dir * 0.13 - side * 0.17 + top * 0.24
        self.horn_l.axis = top * 0.35 - self.aim_dir * 0.08
        self.horn_r.axis = top * 0.35 - self.aim_dir * 0.08
        self.mouth_glow.pos = self.mouth_pos()
        self.mouth_glow.color = vector(1.0, 0.42, 0.05) if self.fire_active else vector(0, 0, 0)

    def emit_fire(self, dt, particles):
        self.fire_accumulator += self.fire_rate * dt
        count = int(self.fire_accumulator)
        self.fire_accumulator -= count
        mouth = self.mouth_pos()
        side = safe_norm(cross(UP, self.aim_dir), vector(0, 0, 1))
        top = safe_norm(cross(self.aim_dir, side), UP)

        for _ in range(count):
            spread = uniform(0.02, 0.18)
            d = self.aim_dir + side * uniform(-spread, spread) + top * uniform(-spread * 0.8, spread * 0.8)
            speed = uniform(4.8, 7.4)
            particles.append(FireParticle(mouth + self.aim_dir * uniform(0.02, 0.20), d, speed, uniform(0.055, 0.105), intensity=uniform(0.7, 1.25)))


class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.override = False
        self.mode = "HUNT"
        self.modes = ["HUNT", "CAREFUL", "SWEEP", "ORBIT_RITUAL", "CHAOTIC", "ARTISTIC"]
        self.mode_time = 0
        self.next_switch = uniform(5.5, 9.0)
        self.last_switch_reason = "start"
        self.stagnation_time = 0
        self.complete_time = 0
        self.sample_timer = 0
        self.last_alive = 0
        self.last_heat = 0
        self.last_particle_count = 0
        self.chaos_timer = 0
        self.spawn_timer = 0
        self.round_delay = 0

    def read_state(self):
        alive = [t for t in self.sim.targets if not t.melted]
        avg_heat = sum(t.heat for t in alive) / len(alive) if alive else 0
        hottest = max(alive, key=lambda t: t.heat, default=None)
        coldest = min(alive, key=lambda t: t.heat, default=None)
        closest = min(alive, key=lambda t: mag(t.pos - self.sim.dragon.mouth_pos()), default=None)
        return {
            "time": self.sim.t,
            "round": self.sim.round_number,
            "alive_count": len(alive),
            "avg_heat": avg_heat,
            "hottest": hottest,
            "coldest": coldest,
            "closest": closest,
            "particles": len(self.sim.particles),
            "droplets": len(self.sim.droplets),
            "dragon_aim": self.sim.dragon.aim_dir,
            "mouth": self.sim.dragon.mouth_pos(),
        }

    def switch_mode(self, reason="timer"):
        old = self.mode
        options = [m for m in self.modes if m != old]
        state = self.read_state()
        if state["alive_count"] <= 1:
            weighted = ["SPAWN_FEAST", "CHAOTIC", "ORBIT_RITUAL"]
        elif state["avg_heat"] > 0.7:
            weighted = ["CAREFUL", "ARTISTIC", "HUNT"]
        else:
            weighted = options

        new_mode = choice(weighted)
        if new_mode == "SPAWN_FEAST":
            new_mode = "CHAOTIC"
            self.sim.spawn_targets(randint(2, 4))
        self.mode = new_mode
        self.mode_time = 0
        self.next_switch = uniform(5.0, 10.0)
        self.last_switch_reason = reason

        if self.mode != "ORBIT_RITUAL":
            orbit_marker.visible = False

    def detect_stagnation_or_completion(self, dt):
        self.sample_timer += dt
        if self.sample_timer < 1.0:
            return

        state = self.read_state()
        heat_total = sum(t.heat for t in self.sim.targets if not t.melted)
        change = abs(heat_total - self.last_heat) + abs(state["alive_count"] - self.last_alive) * 2.0 + abs(state["particles"] - self.last_particle_count) * 0.01

        if state["alive_count"] == 0:
            self.complete_time += self.sample_timer
        else:
            self.complete_time = 0

        if change < 0.025 and state["alive_count"] > 0 and state["particles"] < 3:
            self.stagnation_time += self.sample_timer
        else:
            self.stagnation_time = 0

        self.last_alive = state["alive_count"]
        self.last_heat = heat_total
        self.last_particle_count = state["particles"]
        self.sample_timer = 0

        if self.complete_time > 2.8:
            self.sim.reset_round("completed")
            self.complete_time = 0
            self.stagnation_time = 0

        if self.stagnation_time > 8.0:
            self.sim.reset_round("stagnant")
            self.complete_time = 0
            self.stagnation_time = 0

    def update(self, dt):
        if not self.enabled or self.sim.manual_control:
            return

        self.detect_stagnation_or_completion(dt)
        self.mode_time += dt
        self.chaos_timer += dt
        self.spawn_timer += dt

        state = self.read_state()
        alive = [t for t in self.sim.targets if not t.melted]

        if len(alive) == 0:
            self.sim.ai_fire_permission = False
            return

        if self.mode_time > self.next_switch:
            self.switch_mode("timer")

        if state["alive_count"] <= 2 and self.spawn_timer > 4.0:
            self.sim.spawn_targets(randint(1, 3))
            self.spawn_timer = 0

        target = None
        fire = True

        if self.mode == "HUNT":
            target = state["closest"]
            fire = True

        elif self.mode == "CAREFUL":
            target = state["coldest"] if state["avg_heat"] < 0.75 else state["hottest"]
            fire = sin(self.sim.t * 3.4) > -0.15
            for t in alive:
                if t.heat > 0.93 and random() < 0.015:
                    t.detach()

        elif self.mode == "SWEEP":
            sweep_point = vector(2.8, 2.7 + sin(self.sim.t * 0.7) * 0.85, sin(self.sim.t * 1.05) * 3.0)
            target = min(alive, key=lambda t: mag(t.pos - sweep_point))
            fire = True

        elif self.mode == "ORBIT_RITUAL":
            orbit_marker.visible = True
            center = vector(2.1, 2.55, 0)
            for i, t in enumerate(alive):
                t.attach_orbit(center=center, radius=1.25 + (i % 4) * 0.38)
                t.orbit_speed = (0.55 + 0.16 * (i % 3)) * (1 if i % 2 == 0 else -1)
            target = min(alive, key=lambda t: (t.heat, mag(t.pos - state["mouth"])))
            fire = sin(self.sim.t * 2.1) > -0.55

        elif self.mode == "CHAOTIC":
            target = choice(alive)
            fire = True
            if self.chaos_timer > uniform(1.0, 2.0):
                self.chaos_timer = 0
                for t in alive:
                    if random() < 0.55:
                        t.detach()
                        t.vel += vector(uniform(-1.4, 1.4), uniform(-0.45, 0.55), uniform(-1.3, 1.3))
                if random() < 0.35 and len(alive) < 9:
                    self.sim.spawn_targets(1)

        elif self.mode == "ARTISTIC":
            target = min(alive, key=lambda t: abs(t.pos.z - sin(self.sim.t * 0.8) * 2.5) + t.heat * 0.4)
            fire = sin(self.sim.t * 4.2) > -0.35

        self.sim.selected_target = target
        self.sim.ai_fire_permission = fire


class Simulation:
    def __init__(self):
        self.dragon = Dragon()
        self.targets = []
        self.particles = []
        self.droplets = []
        self.scorch_marks = []
        self.t = 0
        self.round_number = 0
        self.paused = False
        self.manual_control = False
        self.manual_fire = False
        self.ai_fire_permission = True
        self.selected_target = None
        self.user_selected_index = 0
        self.keys = set()
        self.ai = AIController(self)
        self.reset_round("initial")

    def clear_dynamic_objects(self):
        for p in self.particles:
            p.destroy()
        for d in self.droplets:
            d.destroy()
        for t in self.targets:
            t.destroy()
        for m in self.scorch_marks:
            m.visible = False
        self.particles = []
        self.droplets = []
        self.targets = []
        self.scorch_marks = []
        orbit_marker.visible = False

    def reset_round(self, reason="reset"):
        self.clear_dynamic_objects()
        self.round_number += 1
        self.selected_target = None
        self.user_selected_index = 0
        self.ai_fire_permission = True
        self.manual_fire = False
        self.dragon.aim_dir = vector(1, 0.05, 0)
        self.dragon.desired_dir = vector(1, 0.05, 0)
        self.spawn_targets(randint(5, 7))
        self.ai.mode = choice(["HUNT", "ORBIT_RITUAL", "SWEEP"])
        self.ai.mode_time = 0
        self.ai.next_switch = uniform(6.0, 9.5)
        self.ai.last_switch_reason = reason
        self.ai.stagnation_time = 0
        self.ai.complete_time = 0

    def spawn_targets(self, n=1):
        for _ in range(n):
            if len([t for t in self.targets if not t.melted]) >= 11:
                return
            self.targets.append(Target())

    def alive_targets(self):
        return [t for t in self.targets if not t.melted]

    def cycle_target(self):
        alive = self.alive_targets()
        if not alive:
            self.selected_target = None
            return
        self.user_selected_index = (self.user_selected_index + 1) % len(alive)
        self.selected_target = alive[self.user_selected_index]

    def nearest_target_to_aim(self):
        alive = self.alive_targets()
        if not alive:
            return None
        mouth = self.dragon.mouth_pos()

        def score(t):
            direction = safe_norm(t.pos - mouth)
            return diff_angle(direction, self.dragon.aim_dir) + mag(t.pos - mouth) * 0.015

        return min(alive, key=score)

    def target_collisions(self):
        alive = self.alive_targets()
        for i in range(len(alive)):
            a = alive[i]
            for j in range(i + 1, len(alive)):
                b = alive[j]
                delta = b.pos - a.pos
                dist = mag(delta)
                min_dist = a.radius + b.radius
                if dist < min_dist and dist > 1e-6:
                    n = delta / dist
                    overlap = min_dist - dist
                    a.pos -= n * overlap * 0.5
                    b.pos += n * overlap * 0.5
                    if a.mode == "free":
                        a.vel -= n * dot(a.vel, n) * 1.4
                    if b.mode == "free":
                        b.vel -= n * dot(b.vel, -n) * 1.4
                    mixed_heat = (a.heat + b.heat) * 0.5
                    if abs(a.heat - b.heat) > 0.18:
                        a.heat = lerp(a.heat, mixed_heat, 0.08)
                        b.heat = lerp(b.heat, mixed_heat, 0.08)

    def update_manual_controls(self, dt):
        if not self.manual_control:
            return
        d = self.dragon.desired_dir
        yaw_speed = 1.45
        pitch_speed = 1.1
        if "left" in self.keys or "a" in self.keys:
            d = rotate(d, angle=yaw_speed * dt, axis=UP)
        if "right" in self.keys or "d" in self.keys:
            d = rotate(d, angle=-yaw_speed * dt, axis=UP)
        side = safe_norm(cross(UP, d), vector(0, 0, 1))
        if "up" in self.keys or "w" in self.keys:
            d = rotate(d, angle=pitch_speed * dt, axis=side)
        if "down" in self.keys or "s" in self.keys:
            d = rotate(d, angle=-pitch_speed * dt, axis=side)
        if d.y < -0.35:
            d.y = -0.35
        if d.y > 0.72:
            d.y = 0.72
        self.dragon.desired_dir = safe_norm(d, vector(1, 0, 0))

    def update_dragon_targeting(self):
        alive = self.alive_targets()

        if self.manual_control:
            return

        if self.ai.enabled:
            self.ai.update(0)
            if self.selected_target is None or self.selected_target.melted:
                self.selected_target = self.nearest_target_to_aim()
        else:
            if self.selected_target is None or self.selected_target.melted:
                self.selected_target = self.nearest_target_to_aim()

        if self.selected_target is not None and not self.selected_target.melted:
            self.dragon.set_desired_toward(self.selected_target.pos)

    def update_fire_collisions(self, dt):
        for p in self.particles:
            for t in self.targets:
                if t.melted:
                    continue
                dist = mag(t.pos - p.pos)
                if dist < t.radius + p.obj.radius * 1.25:
                    hit_power = 0.028 * p.intensity * (1 - clamp(p.age / p.max_age, 0, 1) * 0.55)
                    t.add_heat(hit_power, self.t)
                    p.vel *= 0.91
                    p.obj.radius *= 0.98
                    if random() < 0.03:
                        self.droplets.append(
                            Droplet(
                                t.pos + vector(uniform(-t.radius, t.radius), -t.radius * 0.2, uniform(-t.radius, t.radius)),
                                vector(uniform(-0.25, 0.25), -uniform(0.1, 0.55), uniform(-0.25, 0.25)),
                                heat=t.heat,
                            )
                        )

    def should_fire(self):
        if self.manual_control:
            return self.manual_fire

        if self.selected_target is None or self.selected_target.melted:
            return False

        mouth = self.dragon.mouth_pos()
        target_dir = safe_norm(self.selected_target.pos - mouth, self.dragon.aim_dir)
        aligned = diff_angle(self.dragon.aim_dir, target_dir) < 0.105
        permission = self.ai_fire_permission if self.ai.enabled else self.manual_fire
        return aligned and permission

    def update(self, dt):
        if self.paused:
            return

        self.t += dt

        if self.ai.enabled and not self.manual_control:
            self.ai.update(dt)

        self.update_manual_controls(dt)
        self.update_dragon_targeting()
        self.dragon.update(dt)

        for target in list(self.targets):
            target.update(dt, self.t, self.droplets, self.scorch_marks)

        self.target_collisions()

        firing = self.should_fire()
        self.dragon.fire_active = firing
        if firing:
            self.dragon.emit_fire(dt, self.particles)

        next_particles = []
        for p in self.particles:
            if p.update(dt):
                next_particles.append(p)
            else:
                p.destroy()
        self.particles = next_particles

        self.update_fire_collisions(dt)

        next_droplets = []
        for d in self.droplets:
            if d.update(dt, self.scorch_marks):
                next_droplets.append(d)
            else:
                d.destroy()
        self.droplets = next_droplets

        self.update_status()

    def update_status(self):
        alive = self.alive_targets()
        target_text = "none"
        if self.selected_target is not None and not self.selected_target.melted:
            target_text = "#" + str(self.selected_target.id) + " heat " + str(int(self.selected_target.heat * 100)) + "%"

        status_label.text = (
            "Round " + str(self.round_number)
            + " | Targets " + str(len(alive))
            + " | AI " + ("ON" if self.ai.enabled else "OFF")
            + " | Mode " + self.ai.mode
            + " | Manual " + ("ON" if self.manual_control else "OFF")
            + " | Fire " + ("ON" if self.dragon.fire_active else "OFF")
            + " | Target " + target_text
            + "\nKeys: A toggle AI | M manual aim | F fire/hold fire | P pause | R reset | N next target | O orbit attach | D detach | C chaos | T spawn"
        )


sim = Simulation()


def keydown(evt):
    k = evt.key
    sim.keys.add(k)

    if k == "p":
        sim.paused = not sim.paused
    elif k == "r":
        sim.reset_round("human")
    elif k == "m":
        sim.manual_control = not sim.manual_control
        sim.manual_fire = False
    elif k == "f" or k == " ":
        sim.manual_fire = not sim.manual_fire
    elif k == "a":
        if not sim.manual_control:
            sim.ai.enabled = not sim.ai.enabled
    elif k == "n":
        sim.cycle_target()
    elif k == "t":
        sim.spawn_targets(1)
    elif k == "o":
        alive = sim.alive_targets()
        if sim.selected_target is None and alive:
            sim.selected_target = alive[0]
        if sim.selected_target is not None and not sim.selected_target.melted:
            sim.selected_target.attach_orbit()
            orbit_marker.visible = True
    elif k == "d":
        if sim.selected_target is not None and not sim.selected_target.melted:
            sim.selected_target.detach()
    elif k == "c":
        for t in sim.alive_targets():
            t.detach()
            t.vel += vector(uniform(-1.6, 1.6), uniform(-0.5, 0.5), uniform(-1.6, 1.6))
        sim.ai.switch_mode("human chaos")


def keyup(evt):
    if evt.key in sim.keys:
        sim.keys.remove(evt.key)


scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

dt = 1 / 60

while True:
    rate(60)
    sim.update(dt)
