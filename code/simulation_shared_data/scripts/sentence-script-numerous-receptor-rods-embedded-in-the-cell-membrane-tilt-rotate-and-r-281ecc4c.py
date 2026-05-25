from vpython import *
import random
import math
import time

# ------------------------------------------------------------
# Signal Receptor Scanning and Activation on Membrane
# VPython self-contained 3D simulation with rule-based / dynamic AI
# ------------------------------------------------------------

# -----------------------------
# Utility functions
# -----------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)

def randf(a, b):
    return random.uniform(a, b)

def random_xy(radius):
    a = randf(0, 2 * math.pi)
    r = radius * math.sqrt(random.random())
    return vector(r * math.cos(a), r * math.sin(a), 0)

def random_unit_vector():
    z = randf(-1, 1)
    a = randf(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(a), r * math.sin(a), z)

def random_outside_position(bounds=5.4, zmin=1.1, zmax=6.2):
    return vector(randf(-bounds, bounds), randf(-bounds, bounds), randf(zmin, zmax))

def random_inside_position(bounds=5.0, zmin=-5.5, zmax=-0.5):
    return vector(randf(-bounds, bounds), randf(-bounds, bounds), randf(zmin, zmax))

def tint(c, amount=0.2):
    return vector(
        clamp(c.x + amount, 0, 1),
        clamp(c.y + amount, 0, 1),
        clamp(c.z + amount, 0, 1)
    )

def dim(c, amount=0.2):
    return vector(
        clamp(c.x - amount, 0, 1),
        clamp(c.y - amount, 0, 1),
        clamp(c.z - amount, 0, 1)
    )


# -----------------------------
# Scene setup
# -----------------------------

scene = canvas(
    title="Signal Receptor Scanning and Activation on Membrane",
    width=1200,
    height=780,
    background=vector(0.93, 0.97, 1.0),
    center=vector(0, 0, -1.5)
)

scene.forward = vector(-0.55, -0.58, -0.62)
scene.up = vector(0, 0, 1)
scene.range = 9.5
scene.autoscale = False
scene.ambient = color.gray(0.72)

distant_light(direction=vector(-0.3, -0.4, -0.9), color=vector(0.95, 0.95, 0.9))
distant_light(direction=vector(0.4, 0.3, 0.6), color=vector(0.55, 0.65, 0.9))

# -----------------------------
# Global constants
# -----------------------------

MEMBRANE_Z = 0.0
OUTSIDE_Z_MIN = 0.42
OUTSIDE_Z_MAX = 6.7
INSIDE_Z_MAX = -0.18
INSIDE_Z_MIN = -7.4
WORLD_BOUND = 6.0

SPECIFIC_COLOR = vector(0.10, 0.72, 0.40)
NONSPECIFIC_COLOR = vector(0.72, 0.75, 0.78)
RECEPTOR_IDLE_COLOR = vector(0.38, 0.58, 0.92)
RECEPTOR_ACTIVE_COLOR = vector(1.0, 0.48, 0.13)
RECEPTOR_BOUND_COLOR = vector(1.0, 0.70, 0.18)
SIGNAL_COLOR = vector(1.0, 0.88, 0.10)
MESSENGER_COLOR = vector(0.10, 0.88, 1.0)
NUCLEUS_COLOR = vector(0.58, 0.42, 0.92)

AI_MODES = [
    "OBSERVE",
    "CURIOUS_GUIDE",
    "CAREFUL_BIND",
    "PLAYFUL_STIR",
    "RITUAL_ORBIT",
    "CONSTRUCTIVE_ACTIVATE",
    "ARTISTIC_MARK",
    "CHAOTIC_SPILL",
    "RESET_LOOP"
]


# -----------------------------
# Simulation object classes
# -----------------------------

class Receptor:
    def __init__(self, sim, base, index):
        self.sim = sim
        self.index = index
        self.base = vector(base.x, base.y, MEMBRANE_Z + 0.03)
        self.length = randf(1.45, 1.85)
        self.radius = 0.055
        self.scan_phase = randf(0, 2 * math.pi)
        self.scan_speed = randf(0.75, 1.55) * random.choice([-1, 1])
        self.tilt_base = randf(0.20, 0.47)
        self.tilt_wobble = randf(0.08, 0.20)
        self.wobble_speed = randf(1.2, 2.6)
        self.bound_ligand = None
        self.activated = False
        self.activation_timer = 0.0
        self.cooldown_timer = randf(0, 2)
        self.scan_boost_timer = 0.0
        self.mark_intensity = 0.0
        self.force_wrap_timer = 0.0

        self.direction = vector(0, 0, 1)

        self.socket = cylinder(
            pos=self.base - vector(0, 0, 0.10),
            axis=vector(0, 0, 0.22),
            radius=0.17,
            color=vector(0.26, 0.38, 0.72),
            opacity=0.58
        )

        self.rod = cylinder(
            pos=self.base,
            axis=self.direction * self.length,
            radius=self.radius,
            color=RECEPTOR_IDLE_COLOR
        )

        self.tip_sphere = sphere(
            pos=self.base + self.direction * self.length,
            radius=0.14,
            color=tint(RECEPTOR_IDLE_COLOR, 0.12),
            shininess=0.75
        )

        self.scan_whisker = cylinder(
            pos=self.tip_sphere.pos,
            axis=vector(0.15, 0, 0.03),
            radius=0.014,
            color=vector(0.72, 0.83, 1.0),
            opacity=0.50
        )

        self.ring = ring(
            pos=self.base + vector(0, 0, 0.015),
            axis=vector(0, 0, 1),
            radius=0.26,
            thickness=0.018,
            color=vector(0.52, 0.70, 0.94),
            opacity=0.38
        )

        self.halo = sphere(
            pos=self.tip_sphere.pos,
            radius=0.42,
            color=vector(1.0, 0.72, 0.20),
            opacity=0.0,
            visible=True
        )

        self.inside_tail = cylinder(
            pos=self.base - vector(0, 0, 0.08),
            axis=vector(0, 0, -0.34),
            radius=0.04,
            color=vector(0.36, 0.50, 0.85),
            opacity=0.55
        )

    @property
    def tip(self):
        return self.base + self.direction * self.length

    def update(self, dt):
        if self.scan_boost_timer > 0:
            self.scan_boost_timer -= dt
        if self.force_wrap_timer > 0:
            self.force_wrap_timer -= dt

        boost = 3.0 if self.scan_boost_timer > 0 else 1.0

        if self.activated:
            self.activation_timer -= dt
            self.mark_intensity = clamp(self.mark_intensity + dt * 2.0, 0, 1)

            pulse = 0.5 + 0.5 * math.sin(self.sim.t * 8.5 + self.index)
            self.length = 1.42 + 0.08 * pulse

            self.scan_phase += self.scan_speed * 0.20 * dt
            tilt = 0.28 + 0.05 * math.sin(self.sim.t * 5.0 + self.index)
            az = self.scan_phase
            self.direction = safe_norm(vector(
                math.sin(tilt) * math.cos(az),
                math.sin(tilt) * math.sin(az),
                math.cos(tilt)
            ), vector(0, 0, 1))

            self.rod.color = RECEPTOR_ACTIVE_COLOR
            self.tip_sphere.color = RECEPTOR_BOUND_COLOR
            self.socket.color = vector(0.95, 0.48, 0.18)
            self.inside_tail.color = vector(1.0, 0.70, 0.18)
            self.inside_tail.radius = 0.055 + 0.025 * pulse
            self.halo.opacity = 0.14 + 0.12 * pulse
            self.halo.radius = 0.40 + 0.12 * pulse
            self.ring.color = vector(1.0, 0.62, 0.16)
            self.ring.opacity = 0.40 + 0.28 * pulse
            self.ring.thickness = 0.020 + 0.012 * pulse

            if self.activation_timer <= 0:
                self.detach_ligand(kick=True)
                self.activated = False
                self.cooldown_timer = 2.2
        else:
            if self.cooldown_timer > 0:
                self.cooldown_timer -= dt

            self.mark_intensity = clamp(self.mark_intensity - dt * 0.12, 0, 1)

            self.scan_phase += self.scan_speed * boost * dt
            tilt = self.tilt_base + self.tilt_wobble * math.sin(self.sim.t * self.wobble_speed + self.index * 0.91)
            tilt += 0.05 * math.sin(self.sim.t * 3.7 + self.index * 1.77)
            tilt = clamp(tilt, 0.08, 0.78)
            az = self.scan_phase

            self.direction = safe_norm(vector(
                math.sin(tilt) * math.cos(az),
                math.sin(tilt) * math.sin(az),
                math.cos(tilt)
            ), vector(0, 0, 1))

            idle_mix = 0.5 + 0.5 * math.sin(self.sim.t * 1.8 + self.index)
            self.rod.color = RECEPTOR_IDLE_COLOR
            self.tip_sphere.color = tint(RECEPTOR_IDLE_COLOR, 0.05 + 0.10 * idle_mix)
            self.socket.color = vector(0.26, 0.38, 0.72)
            self.inside_tail.color = vector(0.36, 0.50, 0.85)
            self.inside_tail.radius = 0.04
            self.halo.opacity = 0.0
            self.ring.color = vector(0.52 + 0.42 * self.mark_intensity, 0.70 - 0.08 * self.mark_intensity, 0.94 - 0.64 * self.mark_intensity)
            self.ring.opacity = 0.24 + 0.22 * self.mark_intensity
            self.ring.thickness = 0.018

        self.rod.axis = self.direction * self.length
        self.tip_sphere.pos = self.tip
        self.scan_whisker.pos = self.tip
        tangent = vector(-math.sin(self.scan_phase), math.cos(self.scan_phase), 0)
        self.scan_whisker.axis = safe_norm(tangent + vector(0, 0, 0.15), vector(1, 0, 0)) * 0.22
        self.halo.pos = self.tip

    def can_bind(self):
        return (not self.activated) and self.bound_ligand is None and self.cooldown_timer <= 0

    def bind_ligand(self, ligand):
        if not self.can_bind():
            return False
        self.bound_ligand = ligand
        ligand.attached_to = self
        ligand.attach_angle = randf(0, 2 * math.pi)
        ligand.vel = vector(0, 0, 0)
        self.activate()
        return True

    def activate(self):
        self.activated = True
        self.activation_timer = randf(6.5, 9.0)
        self.mark_intensity = 1.0
        self.sim.spawn_signal_chain(self, count=random.randint(6, 10))
        self.sim.spill_messengers(self.base - vector(0, 0, 0.18), count=random.randint(10, 18))
        self.sim.flash_membrane_mark(self.base, vector(1.0, 0.62, 0.12))

    def detach_ligand(self, kick=True):
        if self.bound_ligand is not None:
            lig = self.bound_ligand
            lig.attached_to = None
            lig.bound_age = 0.0
            if kick:
                lig.vel = safe_norm(self.direction + 0.5 * random_unit_vector(), vector(0, 0, 1)) * randf(0.8, 1.7)
                lig.pos = self.tip + self.direction * 0.32
            self.bound_ligand = None

    def force_signal_spill(self):
        self.mark_intensity = 1.0
        self.scan_boost_timer = 1.4
        self.sim.spawn_signal_chain(self, count=random.randint(3, 6))
        self.sim.spill_messengers(self.base - vector(0, 0, 0.18), count=random.randint(6, 14))
        self.sim.flash_membrane_mark(self.base, vector(0.15, 0.82, 1.0))

    def hide(self):
        for obj in [self.socket, self.rod, self.tip_sphere, self.scan_whisker, self.ring, self.halo, self.inside_tail]:
            obj.visible = False


class Ligand:
    def __init__(self, sim, pos=None, specific=True, vel=None, artistic=False):
        self.sim = sim
        self.specific = specific
        self.pos = pos if pos is not None else random_outside_position()
        self.vel = vel if vel is not None else vector(randf(-0.45, 0.45), randf(-0.45, 0.45), randf(-0.25, 0.25))
        self.radius = 0.105 if specific else 0.095
        self.attached_to = None
        self.attach_angle = randf(0, 2 * math.pi)
        self.bound_age = 0.0
        self.life = randf(80, 140)
        self.ai_mark = False
        self.artistic = artistic
        self.collision_flash = 0.0

        if specific:
            base_color = SPECIFIC_COLOR if not artistic else vector(randf(0.15, 0.45), randf(0.65, 1.0), randf(0.40, 0.95))
            trail_color = vector(0.40, 0.95, 0.60)
            make_trail_flag = True
        else:
            base_color = NONSPECIFIC_COLOR
            trail_color = vector(0.72, 0.76, 0.82)
            make_trail_flag = False

        self.obj = sphere(
            pos=self.pos,
            radius=self.radius,
            color=base_color,
            make_trail=make_trail_flag,
            retain=35,
            trail_color=trail_color,
            trail_radius=0.015,
            shininess=0.75
        )

        self.core = sphere(
            pos=self.pos,
            radius=self.radius * 0.38,
            color=vector(1, 1, 1),
            opacity=0.28 if specific else 0.18
        )

        self.label_obj = None

    def update(self, dt):
        self.life -= dt

        if self.attached_to is not None:
            self.bound_age += dt
            receptor = self.attached_to
            self.attach_angle += dt * (2.8 + 1.5 * math.sin(self.sim.t + receptor.index))
            r = 0.24 + 0.04 * math.sin(self.attach_angle * 2.0)
            orbit = vector(math.cos(self.attach_angle), math.sin(self.attach_angle), 0)
            up_offset = receptor.direction * 0.17
            self.pos = receptor.tip + orbit * r + up_offset
            self.vel = vector(0, 0, 0)
            self.obj.color = vector(0.12, 0.95, 0.38)
            self.obj.radius = self.radius * (1.08 + 0.14 * math.sin(self.sim.t * 7.0))
        else:
            brownian = vector(randf(-0.55, 0.55), randf(-0.55, 0.55), randf(-0.35, 0.35)) * dt
            self.vel += brownian

            drag = 0.985 if self.specific else 0.978
            self.vel *= drag

            if mag(self.vel) > 2.4:
                self.vel = norm(self.vel) * 2.4

            self.pos += self.vel * dt

            # Boundaries / bounce
            if self.pos.x < -WORLD_BOUND:
                self.pos.x = -WORLD_BOUND
                self.vel.x = abs(self.vel.x) * 0.8
            if self.pos.x > WORLD_BOUND:
                self.pos.x = WORLD_BOUND
                self.vel.x = -abs(self.vel.x) * 0.8
            if self.pos.y < -WORLD_BOUND:
                self.pos.y = -WORLD_BOUND
                self.vel.y = abs(self.vel.y) * 0.8
            if self.pos.y > WORLD_BOUND:
                self.pos.y = WORLD_BOUND
                self.vel.y = -abs(self.vel.y) * 0.8
            if self.pos.z < OUTSIDE_Z_MIN:
                self.pos.z = OUTSIDE_Z_MIN
                self.vel.z = abs(self.vel.z) * randf(0.55, 0.95)
            if self.pos.z > OUTSIDE_Z_MAX:
                self.pos.z = OUTSIDE_Z_MAX
                self.vel.z = -abs(self.vel.z) * randf(0.55, 0.95)

            if self.collision_flash > 0:
                self.collision_flash -= dt
                self.obj.color = vector(1.0, 0.85, 0.28)
                self.obj.radius = self.radius * 1.18
            else:
                self.obj.color = SPECIFIC_COLOR if self.specific else NONSPECIFIC_COLOR
                if self.artistic and self.specific:
                    self.obj.color = vector(0.20 + 0.20 * math.sin(self.sim.t + self.pos.x), 0.78, 0.55 + 0.25 * math.sin(self.sim.t * 0.7))
                self.obj.radius = self.radius

        self.obj.pos = self.pos
        self.core.pos = self.pos

    def bounce_from(self, point, strength=1.0):
        direction = safe_norm(self.pos - point, random_unit_vector())
        self.vel += direction * strength
        self.collision_flash = 0.25

    def hide(self):
        self.obj.visible = False
        self.core.visible = False
        try:
            self.obj.clear_trail()
        except Exception:
            pass
        if self.label_obj:
            self.label_obj.visible = False


class SignalParticle:
    def __init__(self, sim, start, target, delay=0.0, color_value=SIGNAL_COLOR):
        self.sim = sim
        self.pos = vector(start.x, start.y, start.z)
        self.start = vector(start.x, start.y, start.z)
        self.target = vector(target.x, target.y, target.z)
        self.delay = delay
        self.age = 0.0
        self.dead = False
        self.speed = randf(1.35, 2.25)
        self.phase = randf(0, 2 * math.pi)
        self.color_value = color_value

        self.obj = sphere(
            pos=self.pos,
            radius=0.075,
            color=color_value,
            emissive=True,
            make_trail=True,
            retain=45,
            trail_color=color_value,
            trail_radius=0.026
        )
        self.obj.visible = False

        self.glow = sphere(
            pos=self.pos,
            radius=0.20,
            color=color_value,
            opacity=0.12,
            emissive=True
        )
        self.glow.visible = False

    def update(self, dt):
        if self.dead:
            return

        if self.delay > 0:
            self.delay -= dt
            if self.delay > 0:
                return
            self.obj.visible = True
            self.glow.visible = True

        self.age += dt

        to_target = self.target - self.pos
        dist = mag(to_target)
        if dist < 0.22:
            self.dead = True
            self.sim.deliver_signal(self.pos)
            self.hide()
            return

        direction = safe_norm(to_target, vector(0, 0, -1))
        side = cross(direction, vector(0, 0, 1))
        if mag(side) < 0.05:
            side = cross(direction, vector(1, 0, 0))
        side = safe_norm(side, vector(1, 0, 0))
        side2 = safe_norm(cross(direction, side), vector(0, 1, 0))
        spiral = side * math.sin(self.age * 9.5 + self.phase) + side2 * math.cos(self.age * 8.0 + self.phase)
        self.pos += direction * self.speed * dt + spiral * 0.11 * dt

        pulse = 0.5 + 0.5 * math.sin(self.age * 13.0 + self.phase)
        self.obj.pos = self.pos
        self.obj.radius = 0.065 + 0.035 * pulse
        self.glow.pos = self.pos
        self.glow.radius = 0.16 + 0.16 * pulse
        self.glow.opacity = 0.08 + 0.10 * pulse

    def hide(self):
        self.obj.visible = False
        self.glow.visible = False
        try:
            self.obj.clear_trail()
        except Exception:
            pass


class Messenger:
    def __init__(self, sim, pos, vel=None, color_value=MESSENGER_COLOR):
        self.sim = sim
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vel if vel is not None else vector(randf(-0.9, 0.9), randf(-0.9, 0.9), randf(-1.5, -0.1))
        self.life = randf(2.8, 6.2)
        self.max_life = self.life
        self.dead = False
        self.color_value = color_value

        self.obj = sphere(
            pos=self.pos,
            radius=randf(0.035, 0.065),
            color=color_value,
            emissive=True,
            make_trail=True,
            retain=18,
            trail_color=color_value,
            trail_radius=0.010
        )

    def update(self, dt):
        if self.dead:
            return

        self.life -= dt
        if self.life <= 0:
            self.dead = True
            self.hide()
            return

        self.vel += vector(randf(-0.35, 0.35), randf(-0.35, 0.35), randf(-0.18, 0.22)) * dt
        self.vel *= 0.992
        self.pos += self.vel * dt

        if self.pos.z > INSIDE_Z_MAX:
            self.pos.z = INSIDE_Z_MAX
            self.vel.z = -abs(self.vel.z) * 0.65
        if self.pos.z < INSIDE_Z_MIN:
            self.pos.z = INSIDE_Z_MIN
            self.vel.z = abs(self.vel.z) * 0.65

        for axis in ["x", "y"]:
            val = getattr(self.pos, axis)
            if val < -WORLD_BOUND:
                setattr(self.pos, axis, -WORLD_BOUND)
                setattr(self.vel, axis, abs(getattr(self.vel, axis)) * 0.75)
            elif val > WORLD_BOUND:
                setattr(self.pos, axis, WORLD_BOUND)
                setattr(self.vel, axis, -abs(getattr(self.vel, axis)) * 0.75)

        alpha = clamp(self.life / self.max_life, 0, 1)
        pulse = 0.5 + 0.5 * math.sin(self.sim.t * 10 + self.pos.x)
        self.obj.pos = self.pos
        self.obj.opacity = 0.25 + 0.75 * alpha
        self.obj.radius = 0.028 + 0.045 * alpha + 0.012 * pulse

    def hide(self):
        self.obj.visible = False
        try:
            self.obj.clear_trail()
        except Exception:
            pass


class MembraneMark:
    def __init__(self, pos, color_value):
        self.pos = vector(pos.x, pos.y, MEMBRANE_Z + 0.075)
        self.life = 2.4
        self.max_life = self.life
        self.dead = False
        self.obj = ring(
            pos=self.pos,
            axis=vector(0, 0, 1),
            radius=0.18,
            thickness=0.014,
            color=color_value,
            opacity=0.55
        )

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            self.dead = True
            self.obj.visible = False
            return
        p = 1 - self.life / self.max_life
        self.obj.radius = 0.18 + 0.55 * p
        self.obj.opacity = 0.55 * (1 - p)

    def hide(self):
        self.obj.visible = False


# -----------------------------
# AI Controller
# -----------------------------

class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "OBSERVE"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 5.0
        self.action_timer = 0.0
        self.reset_timer = 0.0
        self.manual_override_timer = 0.0
        self.last_metric = None
        self.stagnant_time = 0.0
        self.round_completed_time = 0.0
        self.preferred_receptor = None
        self.last_switch_time = 0.0
        self.personality_bias = random.choice(["playful", "curious", "careful", "chaotic", "ritual", "artistic", "constructive"])
        self.choose_new_mode(force=True)

    def notify_manual_override(self):
        self.manual_override_timer = 2.5

    def get_state(self):
        receptors = self.sim.receptors
        ligands = self.sim.ligands
        free_ligands = [l for l in ligands if l.attached_to is None]
        free_specific = [l for l in free_ligands if l.specific]
        free_nonspecific = [l for l in free_ligands if not l.specific]
        active = [r for r in receptors if r.activated]
        bound = [r for r in receptors if r.bound_ligand is not None]
        inactive_ready = [r for r in receptors if r.can_bind()]
        avg_speed = 0.0
        if free_ligands:
            avg_speed = sum(mag(l.vel) for l in free_ligands) / len(free_ligands)

        return {
            "time": self.sim.t,
            "round": self.sim.round_index,
            "ligand_count": len(ligands),
            "free_ligand_count": len(free_ligands),
            "free_specific_count": len(free_specific),
            "free_nonspecific_count": len(free_nonspecific),
            "active_count": len(active),
            "bound_count": len(bound),
            "inactive_ready_count": len(inactive_ready),
            "signal_count": len(self.sim.signals),
            "messenger_count": len(self.sim.messengers),
            "delivered_count": self.sim.delivered_count,
            "goal": self.sim.round_goal,
            "avg_ligand_speed": avg_speed,
        }

    def update_stagnation(self, dt, state):
        metric = (
            state["free_specific_count"],
            state["active_count"],
            state["bound_count"],
            state["signal_count"],
            state["delivered_count"]
        )

        if self.last_metric is None:
            self.last_metric = metric
            self.stagnant_time = 0.0
            return

        if metric == self.last_metric and state["avg_ligand_speed"] < 0.16 and state["signal_count"] == 0:
            self.stagnant_time += dt
        elif metric == self.last_metric and state["free_specific_count"] == 0 and state["signal_count"] == 0 and state["active_count"] == 0:
            self.stagnant_time += dt
        else:
            self.stagnant_time = max(0.0, self.stagnant_time - dt * 0.75)

        self.last_metric = metric

    def is_complete_or_empty(self, state):
        complete = state["delivered_count"] >= state["goal"] and state["signal_count"] == 0 and state["active_count"] == 0
        empty = state["free_specific_count"] == 0 and state["active_count"] == 0 and state["signal_count"] == 0
        stable = self.stagnant_time > 8.0
        too_crowded_done = state["delivered_count"] >= state["goal"] * 1.4
        return complete or empty or stable or too_crowded_done

    def choose_new_mode(self, force=False):
        state = self.get_state() if hasattr(self, "sim") else None

        if state is not None and self.is_complete_or_empty(state):
            new_mode = "RESET_LOOP"
        else:
            if self.personality_bias == "playful":
                candidates = ["PLAYFUL_STIR", "CURIOUS_GUIDE", "RITUAL_ORBIT", "ARTISTIC_MARK", "CONSTRUCTIVE_ACTIVATE"]
            elif self.personality_bias == "curious":
                candidates = ["CURIOUS_GUIDE", "CAREFUL_BIND", "OBSERVE", "CONSTRUCTIVE_ACTIVATE", "RITUAL_ORBIT"]
            elif self.personality_bias == "careful":
                candidates = ["CAREFUL_BIND", "OBSERVE", "CURIOUS_GUIDE", "CONSTRUCTIVE_ACTIVATE"]
            elif self.personality_bias == "chaotic":
                candidates = ["CHAOTIC_SPILL", "PLAYFUL_STIR", "ARTISTIC_MARK", "CONSTRUCTIVE_ACTIVATE"]
            elif self.personality_bias == "ritual":
                candidates = ["RITUAL_ORBIT", "CAREFUL_BIND", "ARTISTIC_MARK", "CURIOUS_GUIDE"]
            elif self.personality_bias == "artistic":
                candidates = ["ARTISTIC_MARK", "RITUAL_ORBIT", "PLAYFUL_STIR", "CURIOUS_GUIDE"]
            else:
                candidates = ["CONSTRUCTIVE_ACTIVATE", "CURIOUS_GUIDE", "CAREFUL_BIND", "PLAYFUL_STIR"]

            if state:
                if state["free_specific_count"] < 4:
                    candidates += ["CONSTRUCTIVE_ACTIVATE", "ARTISTIC_MARK"]
                if state["active_count"] == 0 and state["free_specific_count"] > 0:
                    candidates += ["CURIOUS_GUIDE", "CAREFUL_BIND"]
                if state["signal_count"] > 12:
                    candidates += ["OBSERVE", "RITUAL_ORBIT"]
                if state["ligand_count"] > 75:
                    candidates = [m for m in candidates if m not in ["CHAOTIC_SPILL"]] + ["CAREFUL_BIND"]

            candidates = [m for m in candidates if m != self.mode]
            if not candidates:
                candidates = [m for m in AI_MODES if m not in ["RESET_LOOP", self.mode]]

            new_mode = random.choice(candidates)

        self.previous_mode = self.mode
        self.mode = new_mode
        self.mode_timer = 0.0
        self.mode_duration = randf(5.5, 13.0)
        self.action_timer = 0.0
        self.last_switch_time = self.sim.t if hasattr(self, "sim") else 0.0

        if self.mode == "RESET_LOOP":
            self.reset_timer = 2.8

        self.preferred_receptor = random.choice(self.sim.receptors) if self.sim.receptors else None

    def step(self, dt):
        if not self.enabled:
            return

        if self.manual_override_timer > 0:
            self.manual_override_timer -= dt
            # During override, AI watches but does not push objects strongly.
            state = self.get_state()
            self.update_stagnation(dt, state)
            return

        state = self.get_state()
        self.update_stagnation(dt, state)

        self.mode_timer += dt
        self.action_timer -= dt

        if self.is_complete_or_empty(state) and self.mode != "RESET_LOOP":
            self.choose_new_mode(force=True)

        if self.mode_timer > self.mode_duration and self.mode != "RESET_LOOP":
            self.choose_new_mode()

        if self.mode == "OBSERVE":
            self.behavior_observe(dt, state)
        elif self.mode == "CURIOUS_GUIDE":
            self.behavior_curious_guide(dt, state)
        elif self.mode == "CAREFUL_BIND":
            self.behavior_careful_bind(dt, state)
        elif self.mode == "PLAYFUL_STIR":
            self.behavior_playful_stir(dt, state)
        elif self.mode == "RITUAL_ORBIT":
            self.behavior_ritual_orbit(dt, state)
        elif self.mode == "CONSTRUCTIVE_ACTIVATE":
            self.behavior_constructive_activate(dt, state)
        elif self.mode == "ARTISTIC_MARK":
            self.behavior_artistic_mark(dt, state)
        elif self.mode == "CHAOTIC_SPILL":
            self.behavior_chaotic_spill(dt, state)
        elif self.mode == "RESET_LOOP":
            self.behavior_reset_loop(dt, state)

    def choose_free_specific(self):
        choices = [l for l in self.sim.ligands if l.specific and l.attached_to is None]
        return random.choice(choices) if choices else None

    def choose_free_ligand(self):
        choices = [l for l in self.sim.ligands if l.attached_to is None]
        return random.choice(choices) if choices else None

    def choose_ready_receptor(self):
        choices = [r for r in self.sim.receptors if r.can_bind()]
        if not choices:
            return random.choice(self.sim.receptors) if self.sim.receptors else None
        return random.choice(choices)

    def guide_ligand_to_receptor(self, ligand, receptor, speed=1.25, softness=0.55):
        if ligand is None or receptor is None or ligand.attached_to is not None:
            return
        target = receptor.tip + receptor.direction * 0.08
        desired = safe_norm(target - ligand.pos, vector(0, 0, -1)) * speed
        ligand.vel = ligand.vel * softness + desired * (1 - softness)
        ligand.ai_mark = True
        receptor.scan_boost_timer = max(receptor.scan_boost_timer, 0.6)

    def spawn_specific_near_receptor(self, receptor=None, count=1, artistic=False):
        if receptor is None:
            receptor = self.choose_ready_receptor()
        if receptor is None:
            return
        for _ in range(count):
            offset = vector(randf(-0.8, 0.8), randf(-0.8, 0.8), randf(1.6, 3.8))
            pos = receptor.base + offset
            pos.x = clamp(pos.x, -WORLD_BOUND, WORLD_BOUND)
            pos.y = clamp(pos.y, -WORLD_BOUND, WORLD_BOUND)
            pos.z = clamp(pos.z, OUTSIDE_Z_MIN + 0.5, OUTSIDE_Z_MAX - 0.2)
            vel = safe_norm(receptor.tip - pos, vector(0, 0, -1)) * randf(0.4, 1.0)
            self.sim.spawn_ligand(pos=pos, specific=True, vel=vel, artistic=artistic)

    def behavior_observe(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = randf(1.5, 3.5)
            if state["free_specific_count"] < 5:
                self.spawn_specific_near_receptor(count=1)
            for r in random.sample(self.sim.receptors, min(3, len(self.sim.receptors))):
                r.scan_boost_timer = max(r.scan_boost_timer, 0.4)

    def behavior_curious_guide(self, dt, state):
        if state["free_specific_count"] < 3 and self.action_timer <= 0:
            self.action_timer = 1.0
            self.spawn_specific_near_receptor(count=2)

        if self.action_timer <= 0:
            self.action_timer = 0.22
            ready = [r for r in self.sim.receptors if r.can_bind()]
            free = [l for l in self.sim.ligands if l.specific and l.attached_to is None]
            if ready and free:
                receptor = random.choice(ready)
                ligand = min(free, key=lambda l: mag(l.pos - receptor.tip))
                self.guide_ligand_to_receptor(ligand, receptor, speed=1.55, softness=0.50)

    def behavior_careful_bind(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = 0.35
            if state["free_specific_count"] < 2:
                self.spawn_specific_near_receptor(count=1)

            ready = [r for r in self.sim.receptors if r.can_bind()]
            free = [l for l in self.sim.ligands if l.specific and l.attached_to is None]
            if ready and free:
                receptor = min(ready, key=lambda r: abs(r.base.x) + abs(r.base.y))
                ligand = min(free, key=lambda l: mag(l.pos - receptor.tip))
                self.guide_ligand_to_receptor(ligand, receptor, speed=0.95, softness=0.72)

            for l in self.sim.ligands:
                if l.attached_to is None:
                    l.vel *= 0.985

    def behavior_playful_stir(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = randf(0.55, 1.2)

            center = vector(randf(-1.2, 1.2), randf(-1.2, 1.2), randf(2.0, 4.2))
            for l in self.sim.ligands:
                if l.attached_to is None:
                    around = cross(vector(0, 0, 1), l.pos - center)
                    if mag(around) > 0.01:
                        l.vel += safe_norm(around) * randf(0.15, 0.7)
                    l.vel += random_unit_vector() * randf(0.0, 0.25)

            for r in random.sample(self.sim.receptors, min(5, len(self.sim.receptors))):
                r.scan_boost_timer = max(r.scan_boost_timer, randf(0.7, 1.7))

            if random.random() < 0.45 and state["ligand_count"] < 80:
                self.sim.spawn_ligand(specific=random.random() < 0.70)

    def behavior_ritual_orbit(self, dt, state):
        if self.preferred_receptor is None or random.random() < 0.002:
            self.preferred_receptor = self.choose_ready_receptor()

        receptor = self.preferred_receptor
        if receptor is None:
            return

        receptor.scan_boost_timer = max(receptor.scan_boost_timer, 0.4)
        receptor.force_wrap_timer = max(receptor.force_wrap_timer, 0.4)

        if state["free_specific_count"] < 5 and self.action_timer <= 0:
            self.spawn_specific_near_receptor(receptor, count=3, artistic=True)
            self.action_timer = 1.2

        free = [l for l in self.sim.ligands if l.attached_to is None]
        if not free:
            return

        ring_count = min(14, len(free))
        selected = sorted(free, key=lambda l: mag(l.pos - receptor.base))[:ring_count]
        radius = 1.25 + 0.25 * math.sin(self.sim.t * 0.7)
        height = 1.6 + 0.45 * math.sin(self.sim.t * 0.5)

        for i, l in enumerate(selected):
            angle = self.sim.t * 0.7 + i * 2 * math.pi / max(1, ring_count)
            desired = receptor.base + vector(math.cos(angle) * radius, math.sin(angle) * radius, height)
            to_desired = desired - l.pos
            l.vel = l.vel * 0.82 + safe_norm(to_desired, vector(0, 0, 1)) * min(1.35, mag(to_desired) * 0.55) * 0.18

        if self.action_timer <= 0:
            self.action_timer = randf(1.4, 2.2)
            self.sim.flash_membrane_mark(receptor.base, vector(0.48, 0.25, 1.0))
            if random.random() < 0.35:
                receptor.force_signal_spill()

    def behavior_constructive_activate(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = 0.42

            if state["free_specific_count"] < max(4, state["inactive_ready_count"] // 3):
                self.spawn_specific_near_receptor(count=2)

            ready = [r for r in self.sim.receptors if r.can_bind()]
            free = [l for l in self.sim.ligands if l.specific and l.attached_to is None]

            if ready and free:
                random.shuffle(ready)
                for receptor in ready[:min(4, len(ready))]:
                    if not free:
                        break
                    ligand = min(free, key=lambda l: mag(l.pos - receptor.tip))
                    self.guide_ligand_to_receptor(ligand, receptor, speed=1.65, softness=0.45)
                    if ligand in free:
                        free.remove(ligand)

            for r in random.sample(self.sim.receptors, min(4, len(self.sim.receptors))):
                r.scan_boost_timer = max(r.scan_boost_timer, 0.9)

    def behavior_artistic_mark(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = randf(0.65, 1.4)
            receptor = self.choose_ready_receptor()
            if receptor:
                self.sim.flash_membrane_mark(
                    receptor.base + vector(randf(-0.15, 0.15), randf(-0.15, 0.15), 0),
                    vector(randf(0.25, 1.0), randf(0.35, 0.95), randf(0.45, 1.0))
                )
                receptor.scan_boost_timer = max(receptor.scan_boost_timer, 1.0)
                if random.random() < 0.45:
                    receptor.force_signal_spill()
                if random.random() < 0.65 and state["ligand_count"] < 85:
                    self.spawn_specific_near_receptor(receptor, count=1, artistic=True)

        # Draw slow spirals with free ligands
        center = vector(0, 0, 3.2)
        free = [l for l in self.sim.ligands if l.attached_to is None]
        selected = free[:min(18, len(free))]
        for i, l in enumerate(selected):
            angle = self.sim.t * 0.42 + i * 0.55
            spiral_radius = 1.0 + 0.08 * i
            desired = center + vector(math.cos(angle) * spiral_radius, math.sin(angle) * spiral_radius, 0.35 * math.sin(angle * 2 + i))
            l.vel = l.vel * 0.90 + safe_norm(desired - l.pos) * 0.10

    def behavior_chaotic_spill(self, dt, state):
        if self.action_timer <= 0:
            self.action_timer = randf(0.30, 0.85)

            if state["ligand_count"] < 95:
                for _ in range(random.randint(1, 4)):
                    self.sim.spawn_ligand(
                        pos=random_outside_position(zmin=2.5, zmax=6.5),
                        specific=random.random() < 0.55,
                        vel=random_unit_vector() * randf(0.5, 1.8)
                    )

            blast_center = random_outside_position(zmin=1.0, zmax=4.0)
            for l in self.sim.ligands:
                if l.attached_to is None:
                    outward = safe_norm(l.pos - blast_center, random_unit_vector())
                    l.vel += outward * randf(0.15, 1.1)

            if random.random() < 0.55 and self.sim.receptors:
                random.choice(self.sim.receptors).force_signal_spill()

            if random.random() < 0.20:
                self.sim.detach_random_ligand()

    def behavior_reset_loop(self, dt, state):
        self.reset_timer -= dt

        if self.action_timer <= 0:
            self.action_timer = 0.45
            for r in random.sample(self.sim.receptors, min(6, len(self.sim.receptors))):
                self.sim.flash_membrane_mark(r.base, vector(1.0, 0.72, 0.22))
                r.scan_boost_timer = max(r.scan_boost_timer, 0.7)

        if self.reset_timer <= 0:
            self.sim.reset_round()
            self.stagnant_time = 0.0
            self.last_metric = None
            self.personality_bias = random.choice(["playful", "curious", "careful", "chaotic", "ritual", "artistic", "constructive"])
            self.choose_new_mode(force=True)


# -----------------------------
# Main Simulation
# -----------------------------

class Simulation:
    def __init__(self):
        self.t = 0.0
        self.round_index = 0
        self.round_goal = 32
        self.delivered_count = 0

        self.receptors = []
        self.ligands = []
        self.signals = []
        self.messengers = []
        self.marks = []

        self.paused = False
        self.show_help = True
        self.human_override_note = ""

        self.create_stationary_scene()

        self.status_label = label(
            pos=vector(-6.25, -6.05, 4.15),
            text="",
            height=12,
            color=vector(0.12, 0.18, 0.26),
            box=True,
            border=7,
            opacity=0.72,
            background=vector(0.98, 1.0, 1.0),
            line=False
        )

        self.mode_label = label(
            pos=vector(4.0, -6.1, 3.75),
            text="",
            height=14,
            color=vector(0.10, 0.18, 0.30),
            box=True,
            border=8,
            opacity=0.65,
            background=vector(0.96, 0.99, 1.0),
            line=False
        )

        self.help_label = label(
            pos=vector(0, 6.25, 4.25),
            text="",
            height=11,
            color=vector(0.16, 0.20, 0.28),
            box=True,
            border=8,
            opacity=0.76,
            background=vector(1.0, 1.0, 0.96),
            line=False
        )

        self.ai = AIController(self)

        scene.bind("keydown", self.on_keydown)

        self.reset_round(initial=True)

    def create_stationary_scene(self):
        self.membrane = box(
            pos=vector(0, 0, MEMBRANE_Z),
            size=vector(12.5, 12.5, 0.075),
            color=vector(0.70, 0.86, 1.0),
            opacity=0.38
        )

        self.membrane_core = box(
            pos=vector(0, 0, MEMBRANE_Z - 0.035),
            size=vector(12.5, 12.5, 0.018),
            color=vector(0.47, 0.68, 0.96),
            opacity=0.28
        )

        self.outer_label = label(
            pos=vector(-5.9, 5.75, 3.1),
            text="outside: ligand space",
            height=12,
            color=vector(0.20, 0.32, 0.48),
            box=False,
            opacity=0
        )

        self.inner_label = label(
            pos=vector(-5.8, 5.75, -4.4),
            text="inside: cytosol → nucleus",
            height=12,
            color=vector(0.34, 0.22, 0.58),
            box=False,
            opacity=0
        )

        # Membrane grid and lipid-like dots
        self.grid_lines = []
        for v in [i * 1.0 for i in range(-6, 7)]:
            self.grid_lines.append(curve(
                pos=[vector(-6.2, v, MEMBRANE_Z + 0.06), vector(6.2, v, MEMBRANE_Z + 0.06)],
                radius=0.006,
                color=vector(0.50, 0.67, 0.88)
            ))
            self.grid_lines.append(curve(
                pos=[vector(v, -6.2, MEMBRANE_Z + 0.061), vector(v, 6.2, MEMBRANE_Z + 0.061)],
                radius=0.006,
                color=vector(0.50, 0.67, 0.88)
            ))

        self.lipid_dots = []
        for _ in range(150):
            p = random_xy(6.1)
            p.z = MEMBRANE_Z + 0.075
            self.lipid_dots.append(sphere(
                pos=p,
                radius=randf(0.018, 0.032),
                color=random.choice([
                    vector(0.58, 0.78, 1.0),
                    vector(0.74, 0.88, 1.0),
                    vector(0.90, 0.96, 1.0)
                ]),
                opacity=0.50
            ))

        self.nucleus = sphere(
            pos=vector(0, 0, -6.45),
            radius=1.18,
            color=NUCLEUS_COLOR,
            opacity=0.50,
            shininess=0.9
        )

        self.nucleus_core = sphere(
            pos=vector(0, 0, -6.45),
            radius=0.65,
            color=vector(0.75, 0.58, 1.0),
            opacity=0.35,
            emissive=True
        )

        self.nucleus_ring = ring(
            pos=vector(0, 0, -6.45),
            axis=vector(0, 0, 1),
            radius=1.32,
            thickness=0.025,
            color=vector(0.72, 0.58, 1.0),
            opacity=0.36
        )

        self.nuclear_light = local_light(
            pos=vector(0, 0, -6.45),
            color=vector(0.35, 0.25, 0.55)
        )

        self.cytosol_haze = sphere(
            pos=vector(0, 0, -3.1),
            radius=6.1,
            color=vector(0.88, 0.94, 1.0),
            opacity=0.055
        )

    def generate_receptor_positions(self, count):
        positions = []
        attempts = 0
        while len(positions) < count and attempts < 2000:
            attempts += 1
            p = random_xy(5.35)
            if all(mag(p - q) > 0.85 for q in positions):
                positions.append(p)
        return positions

    def setup_receptors(self):
        positions = self.generate_receptor_positions(30)
        self.receptors = [Receptor(self, p, i) for i, p in enumerate(positions)]

    def setup_ligands(self):
        self.ligands = []
        for _ in range(32):
            self.spawn_ligand(specific=True)
        for _ in range(18):
            self.spawn_ligand(specific=False)

    def reset_round(self, initial=False):
        for r in self.receptors:
            r.hide()
        for l in self.ligands:
            l.hide()
        for s in self.signals:
            s.hide()
        for m in self.messengers:
            m.hide()
        for mark in self.marks:
            mark.hide()

        self.receptors = []
        self.ligands = []
        self.signals = []
        self.messengers = []
        self.marks = []

        self.round_index += 1
        self.t = 0.0
        self.delivered_count = 0
        self.round_goal = random.randint(24, 44)

        self.nucleus.color = NUCLEUS_COLOR
        self.nucleus.opacity = 0.50
        self.nucleus_core.radius = 0.65
        self.nucleus_core.opacity = 0.35
        self.nuclear_light.color = vector(0.35, 0.25, 0.55)

        self.setup_receptors()
        self.setup_ligands()

        if hasattr(self, "ai") and not initial:
            self.ai.last_metric = None
            self.ai.stagnant_time = 0.0
            self.ai.reset_timer = 0.0
            self.ai.choose_new_mode(force=True)

    def spawn_ligand(self, pos=None, specific=True, vel=None, artistic=False):
        if pos is None:
            pos = random_outside_position()
        if vel is None:
            vel = vector(randf(-0.55, 0.55), randf(-0.55, 0.55), randf(-0.25, 0.25))
        ligand = Ligand(self, pos=pos, specific=specific, vel=vel, artistic=artistic)
        self.ligands.append(ligand)
        return ligand

    def spawn_signal_chain(self, receptor, count=7):
        base = receptor.base - vector(0, 0, 0.22)
        target_base = self.nucleus.pos + vector(randf(-0.38, 0.38), randf(-0.38, 0.38), randf(-0.22, 0.22))
        for i in range(count):
            offset = vector(randf(-0.12, 0.12), randf(-0.12, 0.12), -0.06 * i)
            delay = i * randf(0.08, 0.16)
            sig = SignalParticle(self, base + offset, target_base, delay=delay, color_value=SIGNAL_COLOR)
            self.signals.append(sig)

    def spill_messengers(self, pos, count=10):
        for _ in range(count):
            vel = vector(randf(-1.2, 1.2), randf(-1.2, 1.2), randf(-1.8, -0.1))
            if random.random() < 0.25:
                vel += safe_norm(self.nucleus.pos - pos) * randf(0.4, 1.1)
            messenger = Messenger(self, pos + vector(randf(-0.12, 0.12), randf(-0.12, 0.12), randf(-0.05, 0.05)), vel=vel)
            self.messengers.append(messenger)

    def flash_membrane_mark(self, pos, color_value):
        mark = MembraneMark(pos, color_value)
        self.marks.append(mark)

    def deliver_signal(self, pos):
        self.delivered_count += 1
        pulse = min(1.0, self.delivered_count / max(1, self.round_goal))
        self.nucleus.opacity = 0.50 + 0.24 * pulse
        self.nucleus.color = vector(0.58 + 0.22 * pulse, 0.42 + 0.08 * pulse, 0.92)
        self.nucleus_core.opacity = 0.35 + 0.34 * pulse
        self.nucleus_core.radius = 0.65 + 0.28 * pulse
        self.nuclear_light.color = vector(0.35 + 0.55 * pulse, 0.25 + 0.38 * pulse, 0.55 + 0.35 * pulse)

        for _ in range(4):
            self.messengers.append(Messenger(
                self,
                self.nucleus.pos + random_unit_vector() * randf(0.4, 1.0),
                vel=random_unit_vector() * randf(0.15, 0.55),
                color_value=vector(0.92, 0.72, 1.0)
            ))

    def detach_all(self):
        for r in self.receptors:
            r.detach_ligand(kick=True)

    def detach_random_ligand(self):
        bound = [r for r in self.receptors if r.bound_ligand is not None]
        if bound:
            random.choice(bound).detach_ligand(kick=True)

    def stir_ligands(self, strength=1.0):
        center = vector(0, 0, 3.0)
        for l in self.ligands:
            if l.attached_to is None:
                swirl = cross(vector(0, 0, 1), l.pos - center)
                l.vel += safe_norm(swirl, random_unit_vector()) * randf(0.2, 0.9) * strength
                l.vel += random_unit_vector() * randf(0.0, 0.35) * strength

    def organize_ligands_ring(self):
        if not self.receptors:
            return
        receptor = random.choice(self.receptors)
        free = [l for l in self.ligands if l.attached_to is None]
        for i, l in enumerate(free):
            angle = i * 2 * math.pi / max(1, len(free))
            desired = receptor.base + vector(math.cos(angle) * 2.2, math.sin(angle) * 2.2, 2.4 + 0.4 * math.sin(angle * 3))
            l.vel += safe_norm(desired - l.pos) * 0.9
        self.flash_membrane_mark(receptor.base, vector(0.36, 0.30, 1.0))

    def handle_collisions(self):
        for ligand in self.ligands:
            if ligand.attached_to is not None:
                continue

            # Ligand-to-ligand soft bouncing / mixing
            if random.random() < 0.16:
                other = random.choice(self.ligands) if self.ligands else None
                if other is not None and other is not ligand and other.attached_to is None:
                    d = ligand.pos - other.pos
                    dist = mag(d)
                    min_dist = ligand.radius + other.radius + 0.02
                    if 0 < dist < min_dist:
                        push = safe_norm(d) * (min_dist - dist) * 0.9
                        ligand.vel += push
                        other.vel -= push

            # Ligand-to-receptor tip collision / binding
            for receptor in self.receptors:
                tip = receptor.tip
                d = mag(ligand.pos - tip)
                bind_radius = 0.25 + ligand.radius
                collide_radius = 0.34 + ligand.radius

                if ligand.specific and receptor.can_bind() and d < bind_radius:
                    receptor.bind_ligand(ligand)
                    break
                elif d < collide_radius:
                    if ligand.specific and receptor.can_bind() and random.random() < 0.18:
                        receptor.bind_ligand(ligand)
                        break
                    else:
                        ligand.bounce_from(tip, strength=randf(0.25, 0.75))

    def cleanup_dead(self):
        self.signals = [s for s in self.signals if not s.dead]
        self.messengers = [m for m in self.messengers if not m.dead]
        self.marks = [m for m in self.marks if not m.dead]

        # Keep ligand count bounded. Remove oldest far nonspecific ligands first.
        if len(self.ligands) > 105:
            removable = [l for l in self.ligands if l.attached_to is None and not l.specific]
            if not removable:
                removable = [l for l in self.ligands if l.attached_to is None]
            for lig in removable[:len(self.ligands) - 105]:
                lig.hide()
                if lig in self.ligands:
                    self.ligands.remove(lig)

    def update_labels(self):
        active_count = sum(1 for r in self.receptors if r.activated)
        bound_count = sum(1 for r in self.receptors if r.bound_ligand is not None)
        free_specific = sum(1 for l in self.ligands if l.specific and l.attached_to is None)

        paused_text = "PAUSED" if self.paused else "running"
        ai_text = "ON" if self.ai.enabled else "OFF"
        override_text = " | human override" if self.ai.manual_override_timer > 0 else ""

        self.status_label.text = (
            f"Round {self.round_index} | {paused_text}\n"
            f"receptors: {len(self.receptors)}   active: {active_count}   bound: {bound_count}\n"
            f"ligands: {len(self.ligands)}   free specific: {free_specific}\n"
            f"signals in transit: {len(self.signals)}   delivered: {self.delivered_count}/{self.round_goal}\n"
            f"AI: {ai_text}{override_text}"
        )

        self.mode_label.text = (
            f"AI mode: {self.ai.mode}\n"
            f"personality: {self.ai.personality_bias}\n"
            f"stagnation: {self.ai.stagnant_time:0.1f}s\n"
            f"next switch: {max(0, self.ai.mode_duration - self.ai.mode_timer):0.1f}s"
        )

        if self.show_help:
            self.help_label.text = (
                "Keys: Space pause/resume | A toggle AI | R reset | L spawn specific | N spawn nonspecific\n"
                "S stir/mix | O organize orbit | D detach | C spill random signal | M change AI mode | H hide help"
            )
            self.help_label.visible = True
        else:
            self.help_label.visible = False

    def update_stationary_effects(self, dt):
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.6)
        delivered_pulse = min(1.0, self.delivered_count / max(1, self.round_goal))
        self.nucleus_core.radius = (0.65 + 0.28 * delivered_pulse) + 0.035 * pulse
        self.nucleus_ring.radius = 1.32 + 0.08 * math.sin(self.t * 1.4)
        self.nucleus_ring.opacity = 0.30 + 0.20 * delivered_pulse + 0.04 * pulse

        # Gentle membrane shimmer through lipid dots
        if int(self.t * 10) % 7 == 0 and self.lipid_dots:
            for dot in random.sample(self.lipid_dots, min(3, len(self.lipid_dots))):
                dot.color = random.choice([
                    vector(0.58, 0.78, 1.0),
                    vector(0.74, 0.88, 1.0),
                    vector(0.90, 0.96, 1.0),
                    vector(0.82, 0.95, 1.0)
                ])

    def update(self, dt):
        if self.paused:
            self.update_labels()
            return

        self.t += dt

        if self.ai.enabled:
            self.ai.step(dt)

        for receptor in self.receptors:
            receptor.update(dt)

        for ligand in list(self.ligands):
            ligand.update(dt)

        self.handle_collisions()

        for signal in list(self.signals):
            signal.update(dt)

        for messenger in list(self.messengers):
            messenger.update(dt)

        for mark in list(self.marks):
            mark.update(dt)

        self.update_stationary_effects(dt)
        self.cleanup_dead()
        self.update_labels()

    def on_keydown(self, evt):
        key = evt.key.lower()
        self.ai.notify_manual_override()

        if key in [" ", "space"]:
            self.paused = not self.paused
        elif key == "a":
            self.ai.enabled = not self.ai.enabled
        elif key == "r":
            self.reset_round()
        elif key == "l":
            receptor = random.choice(self.receptors) if self.receptors else None
            if receptor:
                pos = receptor.base + vector(randf(-1.4, 1.4), randf(-1.4, 1.4), randf(2.0, 4.8))
                self.spawn_ligand(pos=pos, specific=True, vel=safe_norm(receptor.tip - pos) * 1.1)
            else:
                self.spawn_ligand(specific=True)
        elif key == "n":
            self.spawn_ligand(specific=False, vel=random_unit_vector() * randf(0.4, 1.2))
        elif key == "s":
            self.stir_ligands(strength=1.6)
        elif key == "o":
            self.organize_ligands_ring()
        elif key == "d":
            self.detach_all()
        elif key == "c":
            if self.receptors:
                random.choice(self.receptors).force_signal_spill()
        elif key == "m":
            self.ai.choose_new_mode(force=True)
        elif key == "h":
            self.show_help = not self.show_help
        elif key == "x":
            self.ai.mode = "CHAOTIC_SPILL"
            self.ai.mode_timer = 0
            self.ai.mode_duration = 8.0
        elif key == "q":
            self.ai.mode = "CAREFUL_BIND"
            self.ai.mode_timer = 0
            self.ai.mode_duration = 8.0


# -----------------------------
# Run simulation
# -----------------------------

sim = Simulation()

last_time = time.time()
while True:
    rate(60)
    now = time.time()
    dt = clamp(now - last_time, 0.001, 0.05)
    last_time = now
    sim.update(dt)
