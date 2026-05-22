from vpython import *
import random as pyrandom
import math

# ----------------------------- VPython scene -----------------------------

scene.title = "Meteor Shower on a Metal Shield Plate - AI Controlled"
scene.width = 1180
scene.height = 760
scene.background = vector(0.94, 0.97, 1.0)
scene.forward = vector(0, 0, -1)
scene.center = vector(0, 0, 0)
scene.range = 10.5
scene.autoscale = False
scene.ambient = color.gray(0.72)

distant_light(direction=vector(0.4, 0.5, -1), color=color.gray(0.75))
distant_light(direction=vector(-0.6, -0.2, -0.5), color=vector(0.55, 0.62, 0.72))

# ----------------------------- constants -----------------------------

SHIELD_W = 10.0
SHIELD_H = 6.0
SHIELD_T = 0.36

MAX_METEORS = 52
MAX_SPARKS = 520
MAX_DENTS = 72
MAX_FORCE_MARKS = 40

BASE_SPAWN_RATE = 0.55
DT = 1.0 / 60.0

# ----------------------------- global runtime state -----------------------------

meteors = []
sparks = []
dents = []
force_marks = []

keys_down = set()

sim_time = 0.0
round_start_time = 0.0
round_number = 1
last_impact_time = 0.0
impacts_total = 0

paused = False
human_override_ai_motion = False

current_spawn_rate = BASE_SPAWN_RATE
spawn_accumulator = 0.0

artist_color_phase = 0.0


# ----------------------------- utility functions -----------------------------

def clamp(x, a, b):
    return max(a, min(b, x))


def randf(a, b):
    return pyrandom.uniform(a, b)


def random_unit_vector():
    z = randf(-1, 1)
    t = randf(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), r * math.sin(t), z)


def safe_norm(v, fallback=vector(0, 0, 1)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)


def metallic_color(base=0.55, jitter=0.12):
    c = clamp(base + randf(-jitter, jitter), 0.25, 0.9)
    return vector(c * 0.95, c, c * 1.04)


# ----------------------------- shield and attached visual details -----------------------------

class ShieldPlate:
    def __init__(self):
        self.pos = vector(0, 0, 0)
        self.yaw = 0.0
        self.pitch = 0.0
        self.right = vector(1, 0, 0)
        self.up = vector(0, 1, 0)
        self.normal = vector(0, 0, 1)

        self.body = box(
            pos=self.pos,
            size=vector(SHIELD_W, SHIELD_H, SHIELD_T),
            color=vector(0.62, 0.66, 0.68),
            opacity=0.93,
            shininess=0.75
        )

        self.front_glow = box(
            pos=self.local_to_world(0, 0, SHIELD_T / 2 + 0.012),
            size=vector(SHIELD_W * 0.985, SHIELD_H * 0.985, 0.012),
            color=vector(0.78, 0.88, 1.0),
            opacity=0.13,
            shininess=0.5
        )

        self.grid_lines = []
        for x in [-4, -2, 0, 2, 4]:
            c = curve(
                pos=[
                    self.local_to_world(x, -SHIELD_H / 2, SHIELD_T / 2 + 0.025),
                    self.local_to_world(x, SHIELD_H / 2, SHIELD_T / 2 + 0.025)
                ],
                radius=0.012,
                color=vector(0.40, 0.45, 0.48)
            )
            self.grid_lines.append(("v", x, c))

        for y in [-2, 0, 2]:
            c = curve(
                pos=[
                    self.local_to_world(-SHIELD_W / 2, y, SHIELD_T / 2 + 0.026),
                    self.local_to_world(SHIELD_W / 2, y, SHIELD_T / 2 + 0.026)
                ],
                radius=0.012,
                color=vector(0.40, 0.45, 0.48)
            )
            self.grid_lines.append(("h", y, c))

        self.rivets = []
        for x in [-4.55, -2.25, 0, 2.25, 4.55]:
            for y in [-2.65, 2.65]:
                s = sphere(
                    pos=self.local_to_world(x, y, SHIELD_T / 2 + 0.06),
                    radius=0.105,
                    color=vector(0.48, 0.51, 0.52),
                    shininess=0.9
                )
                self.rivets.append((x, y, s))

        for x in [-4.75, 4.75]:
            for y in [-2.5, -1.25, 0, 1.25, 2.5]:
                s = sphere(
                    pos=self.local_to_world(x, y, SHIELD_T / 2 + 0.06),
                    radius=0.085,
                    color=vector(0.50, 0.53, 0.54),
                    shininess=0.9
                )
                self.rivets.append((x, y, s))

        self.update_basis()
        self.update_visuals()

    def update_basis(self):
        yaw = self.yaw
        pitch = self.pitch

        n = vector(
            math.sin(yaw) * math.cos(pitch),
            math.sin(pitch),
            math.cos(yaw) * math.cos(pitch)
        )
        self.normal = safe_norm(n, vector(0, 0, 1))

        world_up = vector(0, 1, 0)
        if abs(dot(world_up, self.normal)) > 0.96:
            world_up = vector(1, 0, 0)

        self.right = safe_norm(cross(world_up, self.normal), vector(1, 0, 0))
        self.up = safe_norm(cross(self.normal, self.right), vector(0, 1, 0))

    def update_visuals(self):
        self.update_basis()

        self.body.pos = self.pos
        self.body.axis = self.right * SHIELD_W
        self.body.up = self.up
        self.body.size = vector(SHIELD_W, SHIELD_H, SHIELD_T)

        self.front_glow.pos = self.local_to_world(0, 0, SHIELD_T / 2 + 0.012)
        self.front_glow.axis = self.right * (SHIELD_W * 0.985)
        self.front_glow.up = self.up
        self.front_glow.size = vector(SHIELD_W * 0.985, SHIELD_H * 0.985, 0.012)

        for kind, value, c in self.grid_lines:
            if kind == "v":
                p0 = self.local_to_world(value, -SHIELD_H / 2, SHIELD_T / 2 + 0.028)
                p1 = self.local_to_world(value, SHIELD_H / 2, SHIELD_T / 2 + 0.028)
            else:
                p0 = self.local_to_world(-SHIELD_W / 2, value, SHIELD_T / 2 + 0.028)
                p1 = self.local_to_world(SHIELD_W / 2, value, SHIELD_T / 2 + 0.028)
            c.modify(0, pos=p0)
            c.modify(1, pos=p1)

        for x, y, s in self.rivets:
            s.pos = self.local_to_world(x, y, SHIELD_T / 2 + 0.06)

    def local_to_world(self, x, y, z):
        return self.pos + self.right * x + self.up * y + self.normal * z

    def world_to_local(self, p):
        r = p - self.pos
        return vector(dot(r, self.right), dot(r, self.up), dot(r, self.normal))

    def move_world(self, delta):
        self.pos += delta
        self.pos.x = clamp(self.pos.x, -4.5, 4.5)
        self.pos.y = clamp(self.pos.y, -3.0, 3.0)
        self.pos.z = clamp(self.pos.z, -0.75, 1.25)
        self.update_visuals()

    def move_toward_world(self, target, rate_value, dt):
        target = vector(
            clamp(target.x, -4.5, 4.5),
            clamp(target.y, -3.0, 3.0),
            clamp(target.z, -0.75, 1.25)
        )
        self.pos += (target - self.pos) * clamp(rate_value * dt, 0, 1)
        self.update_visuals()

    def tilt(self, dyaw, dpitch):
        self.yaw = clamp(self.yaw + dyaw, -0.52, 0.52)
        self.pitch = clamp(self.pitch + dpitch, -0.38, 0.38)
        self.update_visuals()

    def tilt_toward(self, target_yaw, target_pitch, rate_value, dt):
        self.yaw += clamp(target_yaw - self.yaw, -rate_value * dt, rate_value * dt)
        self.pitch += clamp(target_pitch - self.pitch, -rate_value * dt, rate_value * dt)
        self.yaw = clamp(self.yaw, -0.52, 0.52)
        self.pitch = clamp(self.pitch, -0.38, 0.38)
        self.update_visuals()

    def reset_pose(self):
        self.pos = vector(0, 0, 0)
        self.yaw = 0.0
        self.pitch = 0.0
        self.update_visuals()


shield = ShieldPlate()


# ----------------------------- dents, impacts, sparks -----------------------------

class Dent:
    def __init__(self, local_x, local_y, force_kn, tint=None):
        self.local_x = local_x
        self.local_y = local_y
        self.force_kn = force_kn
        self.radius = clamp(0.16 + force_kn * 0.012, 0.18, 0.72)
        self.depth = clamp(force_kn * 0.002, 0.02, 0.11)
        self.age = 0.0
        self.repair = 0.0

        if tint is None:
            disk_color = vector(0.20, 0.22, 0.23)
            ring_color = vector(0.95, 0.76, 0.34)
        else:
            disk_color = tint * 0.42
            ring_color = tint

        self.disk = cylinder(
            pos=shield.local_to_world(local_x, local_y, SHIELD_T / 2 + 0.035),
            axis=shield.normal * 0.028,
            radius=self.radius,
            color=disk_color,
            opacity=0.62,
            shininess=0.15
        )

        self.ring = ring(
            pos=shield.local_to_world(local_x, local_y, SHIELD_T / 2 + 0.05),
            axis=shield.normal * 0.035,
            radius=self.radius * 1.05,
            thickness=0.025,
            color=ring_color,
            opacity=0.70
        )

        self.label = label(
            pos=shield.local_to_world(local_x, local_y + self.radius + 0.35, SHIELD_T / 2 + 0.52),
            text=f"{force_kn:4.1f} kN",
            height=10,
            color=vector(0.42, 0.17, 0.03),
            box=False,
            opacity=0
        )

    def update(self, dt):
        self.age += dt
        repaired_factor = clamp(1 - self.repair, 0, 1)
        self.disk.radius = max(0.025, self.radius * repaired_factor)
        self.ring.radius = max(0.035, self.radius * 1.05 * repaired_factor)
        self.disk.opacity = 0.62 * repaired_factor
        self.ring.opacity = 0.70 * repaired_factor

        self.disk.pos = shield.local_to_world(self.local_x, self.local_y, SHIELD_T / 2 + 0.035)
        self.disk.axis = shield.normal * 0.028

        self.ring.pos = shield.local_to_world(self.local_x, self.local_y, SHIELD_T / 2 + 0.052)
        self.ring.axis = shield.normal * 0.035

        self.label.pos = shield.local_to_world(
            self.local_x,
            self.local_y + self.radius + 0.35,
            SHIELD_T / 2 + 0.55
        )
        self.label.opacity = 0
        self.label.color = vector(0.42, 0.17, 0.03) * repaired_factor + vector(0.25, 0.45, 0.75) * self.repair

    def visible(self, value):
        self.disk.visible = value
        self.ring.visible = value
        self.label.visible = value


class Spark:
    def __init__(self, pos, vel, radius, col):
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=col,
            emissive=True,
            opacity=1.0,
            shininess=0
        )
        self.vel = vel
        self.life = randf(0.35, 1.15)
        self.max_life = self.life

    def update(self, dt):
        self.vel += vector(0, -1.4, 0) * dt
        self.vel *= 0.985
        self.obj.pos += self.vel * dt
        self.life -= dt
        a = clamp(self.life / self.max_life, 0, 1)
        self.obj.opacity = a
        self.obj.radius *= 0.995
        return self.life > 0

    def remove(self):
        self.obj.visible = False


def create_force_arrow(pos, force_kn):
    axis_len = clamp(force_kn * 0.025, 0.35, 1.6)
    a = arrow(
        pos=pos + shield.normal * (0.5 + axis_len),
        axis=-shield.normal * axis_len,
        shaftwidth=0.05,
        headwidth=0.18,
        headlength=0.25,
        color=vector(1.0, 0.20, 0.07),
        opacity=0.88
    )
    force_marks.append({"obj": a, "life": 1.3, "max_life": 1.3})


def remove_dent(d):
    if d in dents:
        dents.remove(d)
    d.visible(False)


def create_sparks(impact_pos, meteor_vel, force_kn):
    count = int(clamp(10 + force_kn * 0.55, 12, 38))

    for _ in range(count):
        if len(sparks) >= MAX_SPARKS:
            old = sparks.pop(0)
            old.remove()

        tangential = shield.right * randf(-1, 1) + shield.up * randf(-1, 1)
        outgoing = shield.normal * randf(2.0, 7.0) + safe_norm(tangential, shield.right) * randf(0.7, 5.0)
        reflected_hint = meteor_vel - 2 * dot(meteor_vel, shield.normal) * shield.normal
        vel = outgoing + safe_norm(reflected_hint, shield.normal) * randf(0.2, 1.4)

        col = pyrandom.choice([
            vector(1.0, 0.78, 0.15),
            vector(1.0, 0.48, 0.05),
            vector(1.0, 0.95, 0.50),
            vector(0.75, 0.90, 1.00)
        ])

        sparks.append(Spark(
            impact_pos + shield.normal * randf(0.08, 0.24),
            vel,
            randf(0.025, 0.065),
            col
        ))


# ----------------------------- meteors -----------------------------

class Meteor:
    def __init__(self, spawn_pos, target_pos, speed, radius):
        self.pos = spawn_pos
        self.prev_pos = spawn_pos
        self.vel = safe_norm(target_pos - spawn_pos, -shield.normal) * speed
        self.radius = radius
        self.mass = 1.0 + radius * radius * radius * 850
        self.age = 0.0

        core_color = pyrandom.choice([
            vector(0.92, 0.72, 0.45),
            vector(0.78, 0.80, 0.83),
            vector(0.95, 0.62, 0.30),
            vector(0.72, 0.88, 1.0)
        ])

        self.obj = sphere(
            pos=self.pos,
            radius=radius,
            color=core_color,
            emissive=True,
            shininess=0.85,
            make_trail=True,
            trail_type="curve",
            retain=32,
            trail_radius=radius * 0.45,
            trail_color=vector(1.0, 0.68, 0.18)
        )

        self.shell = sphere(
            pos=self.pos,
            radius=radius * 1.55,
            color=vector(1.0, 0.70, 0.22),
            opacity=0.18,
            emissive=True
        )

    def update(self, dt):
        self.prev_pos = vector(self.pos)
        self.age += dt

        flutter = random_unit_vector() * 0.05
        self.vel += flutter * dt
        self.pos += self.vel * dt

        self.obj.pos = self.pos
        self.shell.pos = self.pos

    def remove(self):
        self.obj.visible = False
        self.shell.visible = False
        try:
            self.obj.clear_trail()
        except Exception:
            pass


def spawn_meteor(focused=False, target_local=None, speed_multiplier=1.0):
    if len(meteors) >= MAX_METEORS:
        return

    if target_local is None:
        if focused:
            tx = randf(-SHIELD_W * 0.36, SHIELD_W * 0.36)
            ty = randf(-SHIELD_H * 0.36, SHIELD_H * 0.36)
        else:
            tx = randf(-SHIELD_W * 0.68, SHIELD_W * 0.68)
            ty = randf(-SHIELD_H * 0.70, SHIELD_H * 0.70)
    else:
        tx = target_local.x
        ty = target_local.y

    target = shield.local_to_world(tx, ty, SHIELD_T / 2 + 0.03)

    side_jitter = shield.right * randf(-8.5, 8.5) + shield.up * randf(-5.5, 5.5)
    distance = randf(17.0, 31.0)
    spawn_pos = target + shield.normal * distance + side_jitter

    if not focused:
        target += shield.right * randf(-1.2, 1.2) + shield.up * randf(-0.8, 0.8)

    speed = randf(8.0, 15.0) * speed_multiplier
    radius = randf(0.075, 0.19)

    meteors.append(Meteor(spawn_pos, target, speed, radius))


def meteor_shield_collision(m):
    front = SHIELD_T / 2 + m.radius * 0.18

    lp = shield.world_to_local(m.prev_pos)
    lc = shield.world_to_local(m.pos)

    crossed_front = lp.z > front and lc.z <= front
    if not crossed_front:
        return None

    denom = lp.z - lc.z
    if abs(denom) < 1e-7:
        t = 0
    else:
        t = clamp((lp.z - front) / denom, 0, 1)

    local_hit = lp + (lc - lp) * t

    if abs(local_hit.x) <= SHIELD_W / 2 and abs(local_hit.y) <= SHIELD_H / 2:
        hit_pos = shield.local_to_world(local_hit.x, local_hit.y, SHIELD_T / 2 + 0.05)
        force_kn = 0.5 * m.mass * mag(m.vel) * mag(m.vel) / 35.0
        return local_hit.x, local_hit.y, hit_pos, force_kn

    return None


def handle_impact(m, hit):
    global last_impact_time, impacts_total, artist_color_phase

    local_x, local_y, hit_pos, force_kn = hit

    tint = None
    if ai_controller.mode == "ARTIST":
        artist_color_phase += 0.17
        tint = vector(
            0.55 + 0.45 * math.sin(artist_color_phase),
            0.55 + 0.45 * math.sin(artist_color_phase + 2.1),
            0.55 + 0.45 * math.sin(artist_color_phase + 4.2)
        )

    d = Dent(local_x, local_y, force_kn, tint)
    dents.append(d)

    while len(dents) > MAX_DENTS:
        remove_dent(dents[0])

    create_sparks(hit_pos, m.vel, force_kn)
    create_force_arrow(hit_pos, force_kn)

    last_impact_time = sim_time
    impacts_total += 1


# ----------------------------- AI repair/orbit drone -----------------------------

class RepairDrone:
    def __init__(self):
        self.angle = 0.0
        self.mode = "ORBIT"
        self.attached_dent = None
        self.attach_time = 0.0

        self.body = sphere(
            pos=shield.local_to_world(0, 0, 2.8),
            radius=0.22,
            color=vector(0.18, 0.55, 1.0),
            emissive=True,
            shininess=0.6
        )

        self.aura = ring(
            pos=self.body.pos,
            axis=vector(0, 0, 1),
            radius=0.38,
            thickness=0.025,
            color=vector(0.35, 0.78, 1.0),
            opacity=0.65
        )

        self.beam = curve(
            pos=[self.body.pos, self.body.pos],
            radius=0.018,
            color=vector(0.20, 0.78, 1.0),
            visible=False
        )

    def attach_to(self, dent):
        if dent is None:
            self.detach()
            return
        self.mode = "ATTACHED"
        self.attached_dent = dent
        self.attach_time = 0.0
        self.beam.visible = True

    def detach(self):
        self.mode = "ORBIT"
        self.attached_dent = None
        self.attach_time = 0.0
        self.beam.visible = False

    def update(self, dt, preferred_mode="ORBIT"):
        self.angle += dt * (1.3 if preferred_mode != "RITUAL" else 2.4)

        if self.mode == "ATTACHED" and self.attached_dent not in dents:
            self.detach()

        if self.mode == "ATTACHED" and self.attached_dent is not None:
            d = self.attached_dent
            self.attach_time += dt

            target = shield.local_to_world(d.local_x, d.local_y, SHIELD_T / 2 + 0.78)
            self.body.pos += (target - self.body.pos) * clamp(7.0 * dt, 0, 1)

            d.repair += dt * 0.22
            if d.repair >= 1.0:
                remove_dent(d)
                self.detach()

            base = shield.local_to_world(d.local_x, d.local_y, SHIELD_T / 2 + 0.06)
            self.beam.modify(0, pos=self.body.pos)
            self.beam.modify(1, pos=base)
            self.beam.visible = True

        else:
            self.mode = "ORBIT"
            self.beam.visible = False

            if preferred_mode == "PLAY":
                rx = 4.1 + 0.8 * math.sin(sim_time * 0.7)
                ry = 2.6 + 0.4 * math.cos(sim_time * 0.9)
                z = 1.15 + 0.35 * math.sin(sim_time * 1.8)
            elif preferred_mode == "RITUAL":
                rx = 5.2
                ry = 3.25
                z = 1.45 + 0.16 * math.sin(sim_time * 3.0)
            else:
                rx = 4.25
                ry = 2.55
                z = 1.25

            target = shield.local_to_world(
                math.cos(self.angle) * rx,
                math.sin(self.angle * 1.15) * ry,
                SHIELD_T / 2 + z
            )
            self.body.pos += (target - self.body.pos) * clamp(3.8 * dt, 0, 1)

        self.aura.pos = self.body.pos
        self.aura.axis = shield.normal
        self.aura.radius = 0.36 + 0.05 * math.sin(sim_time * 7.0)


drone = RepairDrone()


# ----------------------------- AI state machine -----------------------------

class MeteorShieldAI:
    def __init__(self):
        self.enabled = True
        self.mode = "GUARD"
        self.previous_modes = []
        self.mode_timer = 0.0
        self.mode_duration = 9.0
        self.completion_timer = 0.0
        self.stagnation_timer = 0.0
        self.last_state_signature = None
        self.auto_loop_delay = 2.5
        self.last_mode_switch_time = 0.0

        self.behavior_modes = [
            "GUARD",
            "ATTRACT",
            "EVADE",
            "REPAIR",
            "CHAOS",
            "ARTIST",
            "RITUAL"
        ]

    def read_state(self):
        predictions = []
        earliest = None

        for m in meteors:
            local = shield.world_to_local(m.pos)
            vx = dot(m.vel, shield.right)
            vy = dot(m.vel, shield.up)
            vz = dot(m.vel, shield.normal)

            if local.z > SHIELD_T / 2 and vz < -0.02:
                t = (local.z - SHIELD_T / 2) / (-vz)
                if 0 < t < 5.5:
                    px = local.x + vx * t
                    py = local.y + vy * t
                    pred = vector(px, py, t)
                    predictions.append(pred)
                    if earliest is None or t < earliest.z:
                        earliest = pred

        if predictions:
            avg = vector(
                sum(p.x for p in predictions) / len(predictions),
                sum(p.y for p in predictions) / len(predictions),
                sum(p.z for p in predictions) / len(predictions)
            )
        else:
            avg = vector(0, 0, 99)

        return {
            "time": sim_time,
            "round_time": sim_time - round_start_time,
            "meteors": len(meteors),
            "sparks": len(sparks),
            "dents": len(dents),
            "impacts": impacts_total,
            "since_impact": sim_time - last_impact_time,
            "predictions": predictions,
            "avg_prediction": avg,
            "earliest_prediction": earliest,
            "shield_pos": vector(shield.pos),
            "shield_yaw": shield.yaw,
            "shield_pitch": shield.pitch,
        }

    def choose_new_mode(self, state=None, forced=None):
        if forced is not None:
            new_mode = forced
        else:
            if state is None:
                state = self.read_state()

            if state["dents"] > 35:
                candidates = ["REPAIR", "GUARD", "RITUAL"]
            elif state["meteors"] > 30:
                candidates = ["GUARD", "EVADE", "CHAOS"]
            elif state["dents"] < 5 and state["round_time"] > 8:
                candidates = ["ATTRACT", "ARTIST", "CHAOS"]
            elif state["since_impact"] > 12 and state["round_time"] > 15:
                candidates = ["ATTRACT", "CHAOS", "ARTIST"]
            else:
                candidates = list(self.behavior_modes)

            for old in self.previous_modes[-2:]:
                if old in candidates and len(candidates) > 1:
                    candidates.remove(old)

            if self.mode in candidates and len(candidates) > 1:
                candidates.remove(self.mode)

            new_mode = pyrandom.choice(candidates)

        self.previous_modes.append(self.mode)
        self.previous_modes = self.previous_modes[-4:]
        self.mode = new_mode
        self.mode_timer = 0.0
        self.mode_duration = randf(7.5, 14.5)
        self.last_mode_switch_time = sim_time

        if self.mode != "REPAIR":
            drone.detach()

    def detect_completion_or_stagnation(self, state, dt):
        signature = (
            state["meteors"],
            state["dents"],
            state["impacts"],
            int(state["sparks"] / 8)
        )

        if self.last_state_signature == signature:
            self.stagnation_timer += dt
        else:
            self.stagnation_timer = max(0.0, self.stagnation_timer - dt * 0.5)
            self.last_state_signature = signature

        too_many_dents = state["dents"] >= MAX_DENTS - 2
        very_long_round = state["round_time"] > 85
        empty_and_still = state["meteors"] == 0 and state["sparks"] < 5 and state["since_impact"] > 8
        stagnant = self.stagnation_timer > 13 and state["round_time"] > 20
        quiet_failure = state["since_impact"] > 22 and state["round_time"] > 25

        return too_many_dents or very_long_round or empty_and_still or stagnant or quiet_failure

    def update(self, dt):
        global current_spawn_rate

        if not self.enabled:
            current_spawn_rate = BASE_SPAWN_RATE
            drone.update(dt, "ORBIT")
            return

        state = self.read_state()
        self.mode_timer += dt

        if self.detect_completion_or_stagnation(state, dt):
            self.completion_timer += dt
            current_spawn_rate = 0.0
            if self.completion_timer > self.auto_loop_delay:
                reset_simulation(auto=True)
                self.completion_timer = 0.0
                self.choose_new_mode(self.read_state(), forced=pyrandom.choice(["ATTRACT", "ARTIST", "GUARD"]))
                return
        else:
            self.completion_timer = 0.0

        if self.mode_timer > self.mode_duration:
            self.choose_new_mode(state)

        if self.mode == "GUARD":
            self.behavior_guard(state, dt)
        elif self.mode == "ATTRACT":
            self.behavior_attract(state, dt)
        elif self.mode == "EVADE":
            self.behavior_evade(state, dt)
        elif self.mode == "REPAIR":
            self.behavior_repair(state, dt)
        elif self.mode == "CHAOS":
            self.behavior_chaos(state, dt)
        elif self.mode == "ARTIST":
            self.behavior_artist(state, dt)
        elif self.mode == "RITUAL":
            self.behavior_ritual(state, dt)

    def apply_shield_target(self, target_pos, target_yaw, target_pitch, move_rate, tilt_rate, dt):
        if not human_override_ai_motion:
            shield.move_toward_world(target_pos, move_rate, dt)
            shield.tilt_toward(target_yaw, target_pitch, tilt_rate, dt)

    def behavior_guard(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 0.62

        pred = state["earliest_prediction"] or state["avg_prediction"]
        target = shield.pos

        if pred.z < 50:
            target = shield.pos + shield.right * pred.x * 0.42 + shield.up * pred.y * 0.42
            target.z = 0

        target_yaw = clamp(-pred.x * 0.035, -0.28, 0.28) if pred.z < 50 else 0
        target_pitch = clamp(-pred.y * 0.035, -0.22, 0.22) if pred.z < 50 else 0

        self.apply_shield_target(target, target_yaw, target_pitch, 1.9, 0.75, dt)
        drone.update(dt, "ORBIT")

    def behavior_attract(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 1.05

        target = vector(0, 0, 0)
        target_yaw = 0.12 * math.sin(sim_time * 0.55)
        target_pitch = 0.10 * math.cos(sim_time * 0.48)

        self.apply_shield_target(target, target_yaw, target_pitch, 0.9, 0.45, dt)
        drone.update(dt, "PLAY")

    def behavior_evade(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 0.72

        pred = state["earliest_prediction"] or state["avg_prediction"]
        target = shield.pos

        if pred.z < 50:
            dodge_x = -math.copysign(2.2, pred.x if abs(pred.x) > 0.25 else math.sin(sim_time))
            dodge_y = -math.copysign(1.35, pred.y if abs(pred.y) > 0.15 else math.cos(sim_time * 0.8))
            target = vector(dodge_x, dodge_y, 0)
        else:
            target = vector(2.6 * math.sin(sim_time * 0.7), 1.5 * math.cos(sim_time * 0.9), 0)

        self.apply_shield_target(target, 0.25 * math.sin(sim_time), 0.18 * math.cos(sim_time * 1.2), 2.35, 1.05, dt)
        drone.update(dt, "PLAY")

    def behavior_repair(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 0.12

        if not dents:
            self.choose_new_mode(state, forced=pyrandom.choice(["ATTRACT", "ARTIST", "GUARD"]))
            drone.detach()
            return

        if drone.mode != "ATTACHED":
            target_dent = max(dents, key=lambda d: d.force_kn * (1.0 - d.repair))
            drone.attach_to(target_dent)

        self.apply_shield_target(vector(0, 0, 0), 0, 0, 0.65, 0.55, dt)
        drone.update(dt, "ORBIT")

    def behavior_chaos(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 1.65

        target = vector(
            3.3 * math.sin(sim_time * 1.55) + randf(-0.03, 0.03),
            2.2 * math.sin(sim_time * 2.15 + 1.7) + randf(-0.03, 0.03),
            0.18 * math.sin(sim_time * 3.1)
        )
        target_yaw = 0.46 * math.sin(sim_time * 1.9)
        target_pitch = 0.31 * math.cos(sim_time * 2.25)

        self.apply_shield_target(target, target_yaw, target_pitch, 3.2, 1.8, dt)
        drone.update(dt, "PLAY")

    def behavior_artist(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 0.78

        target = vector(
            2.7 * math.sin(sim_time * 0.72),
            1.85 * math.sin(sim_time * 1.31 + 0.8),
            0
        )
        target_yaw = 0.20 * math.sin(sim_time * 0.42)
        target_pitch = 0.16 * math.sin(sim_time * 0.61 + 1.4)

        self.apply_shield_target(target, target_yaw, target_pitch, 1.15, 0.55, dt)
        drone.update(dt, "PLAY")

    def behavior_ritual(self, state, dt):
        global current_spawn_rate
        current_spawn_rate = 0.28

        orbit_yaw = 0.34 * math.sin(sim_time * 0.42)
        orbit_pitch = 0.24 * math.sin(sim_time * 0.37 + math.pi / 3)

        target = vector(
            1.2 * math.sin(sim_time * 0.32),
            0.75 * math.cos(sim_time * 0.32),
            0
        )

        self.apply_shield_target(target, orbit_yaw, orbit_pitch, 0.65, 0.38, dt)
        drone.update(dt, "RITUAL")


ai_controller = MeteorShieldAI()


# ----------------------------- labels and static scenery -----------------------------

title_label = label(
    pos=vector(0, 4.65, 0.7),
    text="Meteor Shower on Metal Shield",
    height=20,
    color=vector(0.08, 0.12, 0.18),
    box=False,
    opacity=0
)

status_label = label(
    pos=vector(-6.8, -4.55, 1.0),
    text="",
    height=11,
    color=vector(0.05, 0.08, 0.12),
    box=False,
    opacity=0,
    align="left"
)

legend_label = label(
    pos=vector(5.5, -4.7, 0.5),
    text="Keys: arrows move | W/S pitch | A/D yaw | I AI | H human override | P pause | R reset | N next AI | M meteor",
    height=9,
    color=vector(0.15, 0.18, 0.21),
    box=False,
    opacity=0,
    align="right"
)

# Light reference frame behind the scene.
for x in [-5, 0, 5]:
    curve(pos=[vector(x, -3.2, -0.55), vector(x, 3.2, -0.55)], radius=0.006, color=vector(0.82, 0.87, 0.92))
for y in [-3, 0, 3]:
    curve(pos=[vector(-5.2, y, -0.55), vector(5.2, y, -0.55)], radius=0.006, color=vector(0.82, 0.87, 0.92))


# ----------------------------- reset and control -----------------------------

def clear_meteors():
    for m in list(meteors):
        m.remove()
    meteors.clear()


def clear_sparks():
    for s in list(sparks):
        s.remove()
    sparks.clear()


def clear_force_marks():
    for fm in list(force_marks):
        fm["obj"].visible = False
    force_marks.clear()


def clear_dents():
    for d in list(dents):
        d.visible(False)
    dents.clear()


def reset_simulation(auto=False):
    global round_number, round_start_time, last_impact_time, impacts_total, spawn_accumulator

    clear_meteors()
    clear_sparks()
    clear_force_marks()
    clear_dents()

    shield.reset_pose()
    drone.detach()
    drone.body.pos = shield.local_to_world(0, 0, 2.8)

    if auto:
        round_number += 1

    round_start_time = sim_time
    last_impact_time = sim_time
    impacts_total = 0
    spawn_accumulator = 0.0

    for _ in range(7):
        spawn_meteor(focused=True, speed_multiplier=randf(0.85, 1.15))


def on_keydown(evt):
    global paused, human_override_ai_motion

    k = evt.key.lower()
    keys_down.add(k)

    if k == "p" or k == " ":
        paused = not paused
    elif k == "i":
        ai_controller.enabled = not ai_controller.enabled
    elif k == "h":
        human_override_ai_motion = not human_override_ai_motion
    elif k == "r":
        reset_simulation(auto=False)
    elif k == "n":
        ai_controller.choose_new_mode(ai_controller.read_state())
    elif k == "m":
        spawn_meteor(focused=True, speed_multiplier=1.05)


def on_keyup(evt):
    k = evt.key.lower()
    if k in keys_down:
        keys_down.remove(k)


scene.bind("keydown", on_keydown)
scene.bind("keyup", on_keyup)


def apply_human_controls(dt):
    move_speed = 4.7
    tilt_speed = 0.88

    delta = vector(0, 0, 0)

    if "left" in keys_down:
        delta += vector(-move_speed * dt, 0, 0)
    if "right" in keys_down:
        delta += vector(move_speed * dt, 0, 0)
    if "up" in keys_down:
        delta += vector(0, move_speed * dt, 0)
    if "down" in keys_down:
        delta += vector(0, -move_speed * dt, 0)

    if "q" in keys_down:
        delta += vector(0, 0, move_speed * 0.35 * dt)
    if "e" in keys_down:
        delta += vector(0, 0, -move_speed * 0.35 * dt)

    if mag(delta) > 0:
        shield.move_world(delta)

    dyaw = 0.0
    dpitch = 0.0

    if "a" in keys_down:
        dyaw -= tilt_speed * dt
    if "d" in keys_down:
        dyaw += tilt_speed * dt
    if "w" in keys_down:
        dpitch += tilt_speed * dt
    if "s" in keys_down:
        dpitch -= tilt_speed * dt

    if dyaw != 0 or dpitch != 0:
        shield.tilt(dyaw, dpitch)


# ----------------------------- physics/update loop -----------------------------

def update_meteors(dt):
    for m in list(meteors):
        m.update(dt)
        hit = meteor_shield_collision(m)

        if hit is not None:
            handle_impact(m, hit)
            m.remove()
            meteors.remove(m)
            continue

        local_now = shield.world_to_local(m.pos)
        if m.age > 12 or local_now.z < -8 or mag(m.pos - shield.pos) > 48:
            m.remove()
            meteors.remove(m)


def update_sparks(dt):
    for s in list(sparks):
        alive = s.update(dt)
        if not alive:
            s.remove()
            sparks.remove(s)


def update_dents(dt):
    for d in list(dents):
        d.update(dt)


def update_force_marks(dt):
    for fm in list(force_marks):
        fm["life"] -= dt
        a = clamp(fm["life"] / fm["max_life"], 0, 1)
        fm["obj"].opacity = a * 0.88
        if fm["life"] <= 0:
            fm["obj"].visible = False
            force_marks.remove(fm)


def update_spawning(dt):
    global spawn_accumulator

    spawn_accumulator += current_spawn_rate * dt

    while spawn_accumulator >= 1.0:
        spawn_accumulator -= 1.0

        focused = ai_controller.enabled and ai_controller.mode in ["ATTRACT", "ARTIST", "CHAOS"]
        speed_mult = 1.0

        if ai_controller.mode == "CHAOS":
            speed_mult = randf(1.05, 1.45)
        elif ai_controller.mode == "RITUAL":
            speed_mult = randf(0.72, 0.95)
        elif ai_controller.mode == "ARTIST":
            speed_mult = randf(0.82, 1.08)

            t = sim_time * 0.85
            target_local = vector(
                math.sin(t * 1.7) * SHIELD_W * 0.38,
                math.sin(t * 2.3 + 1.2) * SHIELD_H * 0.36,
                0
            )
            spawn_meteor(focused=True, target_local=target_local, speed_multiplier=speed_mult)
            continue

        spawn_meteor(focused=focused, speed_multiplier=speed_mult)


def update_status_label():
    ai_state = "ON" if ai_controller.enabled else "OFF"
    override_state = "ON" if human_override_ai_motion else "OFF"
    pause_state = "PAUSED" if paused else "RUNNING"
    status_label.text = (
        f"{pause_state} | Round {round_number}\n"
        f"AI: {ai_state} | Mode: {ai_controller.mode} | Human override: {override_state}\n"
        f"Meteors: {len(meteors)} | Dents: {len(dents)} | Sparks: {len(sparks)} | Impacts this round: {impacts_total}\n"
        f"Spawn rate: {current_spawn_rate:.2f}/s | Next mode in: {max(0, ai_controller.mode_duration - ai_controller.mode_timer):.1f}s"
    )

    if paused:
        title_label.text = "Meteor Shower on Metal Shield - PAUSED"
    else:
        title_label.text = "Meteor Shower on Metal Shield"


# Initial wave
reset_simulation(auto=False)

# ----------------------------- main loop -----------------------------

while True:
    rate(60)

    if paused:
        apply_human_controls(DT)
        drone.update(DT, "ORBIT")
        update_status_label()
        continue

    sim_time += DT

    apply_human_controls(DT)

    ai_controller.update(DT)

    shield.update_visuals()
    update_dents(DT)

    update_spawning(DT)
    update_meteors(DT)
    update_sparks(DT)
    update_force_marks(DT)

    update_status_label()
