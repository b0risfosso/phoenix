from vpython import *
import random
import math

# ------------------------------------------------------------
# 3D MITOSIS SIMULATION WITH EXPRESSIVE AI CONTROLLER
# VPython self-contained source file
# Controls:
#   Space : pause / resume
#   A     : toggle AI on/off
#   M     : force AI to choose a new behavior mode
#   R     : reset simulation round
#   S     : spill vesicle/particle burst
#   D     : attach/detach a random spindle fiber
#   W     : create membrane wrapping rings
#   C     : toggle scripted camera orbit on/off (off allows mouse camera movement)
#   L     : toggle labels
#   X     : temporary human override of AI behavior
#   Up/Down : increase/decrease simulation speed bias
#   Left/Right : nudge camera around scene
#   F     : manually pulse the membrane contraction wave
# ------------------------------------------------------------

scene = canvas(
    title="Mitosis: Traveling Membrane Contraction Wave",
    width=1200,
    height=760,
    background=vector(0.94, 0.98, 1.0),
    center=vector(0, 0, 0),
    forward=vector(-0.15, -0.12, -1)
)

# Keep VPython's built-in mouse camera controls available.
# The original script overwrote scene.forward and scene.center every frame,
# which made mouse rotation/panning appear broken.
try:
    scene.userspin = True
    scene.userzoom = True
    scene.userpan = True
except Exception:
    pass

scene.lights = []
distant_light(direction=vector(0.4, -0.7, -0.3), color=vector(0.85, 0.88, 0.95))
distant_light(direction=vector(-0.6, 0.3, -0.6), color=vector(0.55, 0.60, 0.75))
local_light(pos=vector(0, 5, 7), color=vector(0.8, 0.82, 0.9))

random.seed()


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def smoothstep(edge0, edge1, x):
    if edge0 == edge1:
        return 0
    x = clamp((x - edge0) / (edge1 - edge0), 0, 1)
    return x * x * (3 - 2 * x)


def lerp(a, b, u):
    return a + (b - a) * u


def vlerp(a, b, u):
    return a + (b - a) * u


def safe_norm(v, fallback=vector(1, 0, 0)):
    m = mag(v)
    if m < 1e-8:
        return fallback
    return v / m


def dispose_vpython_object(obj):
    """Safely hide a VPython object without deleting it.

    This version intentionally avoids VPython's built-in trail cleanup calls.
    The simulation now uses manual trail dots, because built-in make_trail /
    clear_trail can stall some VPython builds when many moving objects begin
    drawing trails at the spindle-organization transition.
    """
    if obj is None:
        return
    try:
        obj.visible = False
    except Exception:
        pass


class ManualTrail:
    """Small fixed-size dot trail that is safe to reset.

    VPython's make_trail=True was the likely freeze source: at about 16%
    progress, chromosome movement and spindle visibility both increase, and
    many built-in trails begin updating at once. This class avoids that engine
    by preallocating a small ring buffer of translucent spheres.
    """
    def __init__(self, sim, color_value, radius=0.018, max_points=12, stride=3, opacity=0.34):
        self.sim = sim
        self.color_value = color_value
        self.radius = radius
        self.max_points = max_points
        self.stride = max(1, stride)
        self.opacity = opacity
        self.frame = 0
        self.index = 0
        self.active_count = 0
        self.points = []
        for _ in range(max_points):
            dot = sphere(
                pos=vector(0, 0, 0),
                radius=radius,
                color=color_value,
                opacity=0,
                shininess=0.1,
                emissive=False,
                visible=False
            )
            self.points.append(dot)
            sim.register(dot)

    def update(self, pos):
        self.frame += 1
        if self.frame % self.stride != 0:
            return
        dot = self.points[self.index]
        dot.pos = vector(pos.x, pos.y, pos.z)
        dot.visible = True
        dot.opacity = self.opacity
        dot.radius = self.radius
        self.index = (self.index + 1) % self.max_points
        self.active_count = min(self.max_points, self.active_count + 1)

        for age in range(self.active_count):
            i = (self.index - 1 - age) % self.max_points
            fade = 1.0 - age / max(1, self.max_points)
            self.points[i].opacity = self.opacity * fade
            self.points[i].radius = self.radius * (0.55 + 0.45 * fade)

    def clear(self):
        for dot in self.points:
            dispose_vpython_object(dot)
        self.active_count = 0
        self.index = 0
        self.frame = 0


class ChromosomePair:
    def __init__(self, sim, index, base_angle, radius_ring):
        self.sim = sim
        self.index = index
        self.base_angle = base_angle
        self.radius_ring = radius_ring
        self.phase_jitter = random.uniform(0, math.tau)
        self.color_left = vector(0.78, 0.16 + random.random() * 0.14, 0.78)
        self.color_right = vector(0.50, 0.20 + random.random() * 0.18, 0.92)

        y = math.cos(base_angle) * radius_ring
        z = math.sin(base_angle) * radius_ring
        self.central_pos = vector(random.uniform(-0.15, 0.15), y, z)

        self.left_final = vector(
            -1.45 - random.random() * 0.34,
            y * 0.82 + random.uniform(-0.12, 0.12),
            z * 0.82 + random.uniform(-0.12, 0.12)
        )
        self.right_final = vector(
            1.45 + random.random() * 0.34,
            y * 0.82 + random.uniform(-0.12, 0.12),
            z * 0.82 + random.uniform(-0.12, 0.12)
        )

        # Late-stage chromosome targets must move with the daughter-cell nuclei.
        # The earlier script used absolute world-space final positions. Once the
        # daughter cells drifted outward, those absolute targets remained near the
        # original center, so chromosomes appeared to hit an invisible boundary and
        # could not stay centered inside the new nuclei. These local offsets are
        # added to each daughter nucleus center during telophase/cytokinesis.
        self.left_nucleus_offset = vector(
            random.uniform(-0.14, 0.10),
            y * 0.38 + random.uniform(-0.08, 0.08),
            z * 0.38 + random.uniform(-0.08, 0.08)
        )
        self.right_nucleus_offset = vector(
            random.uniform(-0.10, 0.14),
            y * 0.38 + random.uniform(-0.08, 0.08),
            z * 0.38 + random.uniform(-0.08, 0.08)
        )

        self.left = sphere(
            pos=self.central_pos + vector(-0.08, 0, 0),
            radius=0.145,
            color=self.color_left,
            shininess=0.55
        )
        self.right = sphere(
            pos=self.central_pos + vector(0.08, 0, 0),
            radius=0.145,
            color=self.color_right,
            shininess=0.55
        )
        self.left_trail = ManualTrail(sim, vector(0.88, 0.45, 0.95), radius=0.020, max_points=14, stride=4, opacity=0.30)
        self.right_trail = ManualTrail(sim, vector(0.62, 0.50, 0.98), radius=0.020, max_points=14, stride=4, opacity=0.30)

        self.connector = cylinder(
            pos=self.left.pos,
            axis=self.right.pos - self.left.pos,
            radius=0.035,
            color=vector(0.58, 0.22, 0.76),
            opacity=0.65
        )
        self.left_fiber = cylinder(
            pos=vector(-0.7, 0, 0),
            axis=self.left.pos - vector(-0.7, 0, 0),
            radius=0.018,
            color=vector(1.0, 0.83, 0.34),
            opacity=0
        )
        self.right_fiber = cylinder(
            pos=vector(0.7, 0, 0),
            axis=self.right.pos - vector(0.7, 0, 0),
            radius=0.018,
            color=vector(1.0, 0.83, 0.34),
            opacity=0
        )
        self.left_attached = True
        self.right_attached = True
        self.selected = False

        sim.register(self.left)
        sim.register(self.right)
        sim.register(self.connector)
        sim.register(self.left_fiber)
        sim.register(self.right_fiber)

    def set_visible(self, value):
        self.left.visible = value
        self.right.visible = value
        self.connector.visible = value
        self.left_fiber.visible = value
        self.right_fiber.visible = value
        if not value:
            self.left_trail.clear()
            self.right_trail.clear()

    def update(self, t, time_seconds, left_pole, right_pole, left_nucleus_center, right_nucleus_center, ai_noise=0.0, pull_bias=1.0):
        congress = smoothstep(0.05, 0.27, t)
        separate = smoothstep(0.34, 0.58, t)
        telophase = smoothstep(0.60, 0.84, t)

        align_pos = vector(
            0,
            math.cos(self.base_angle) * self.radius_ring * 0.72,
            math.sin(self.base_angle) * self.radius_ring * 0.72
        )

        initial_left = self.central_pos + vector(-0.08, 0, 0)
        initial_right = self.central_pos + vector(0.08, 0, 0)

        paired_left = vlerp(initial_left, align_pos + vector(-0.11, 0, 0), congress)
        paired_right = vlerp(initial_right, align_pos + vector(0.11, 0, 0), congress)

        # First pull chromosomes outward, then gradually hand them off to
        # daughter-nucleus-local targets. This makes chromosomes travel with the
        # moving daughter cells instead of staying pinned to old world-space
        # coordinates near the original center.
        world_final_left = self.left_final + vector(-0.42 * telophase, 0, 0)
        world_final_right = self.right_final + vector(0.42 * telophase, 0, 0)
        nucleus_final_left = left_nucleus_center + self.left_nucleus_offset
        nucleus_final_right = right_nucleus_center + self.right_nucleus_offset
        nucleus_lock = smoothstep(0.58, 0.92, t)
        final_left = vlerp(world_final_left, nucleus_final_left, nucleus_lock)
        final_right = vlerp(world_final_right, nucleus_final_right, nucleus_lock)

        pull_u = clamp(separate * pull_bias, 0, 1)
        left_target = vlerp(paired_left, final_left, pull_u)
        right_target = vlerp(paired_right, final_right, pull_u)

        pulse = math.sin(time_seconds * 3.2 + self.phase_jitter)
        swirl = vector(
            0,
            math.sin(time_seconds * 2.4 + self.phase_jitter) * 0.045,
            math.cos(time_seconds * 2.1 + self.phase_jitter) * 0.045
        )
        noise_vec = swirl * ai_noise

        if not self.left_attached and separate > 0.1:
            left_target += vector(0.25 * math.sin(time_seconds * 4.0 + self.index), 0.18 * pulse, 0.12 * math.cos(time_seconds * 3.6))
        if not self.right_attached and separate > 0.1:
            right_target += vector(-0.25 * math.cos(time_seconds * 3.7 + self.index), -0.16 * pulse, 0.13 * math.sin(time_seconds * 3.2))

        self.left.pos = left_target + noise_vec
        self.right.pos = right_target - noise_vec
        self.left_trail.update(self.left.pos)
        self.right_trail.update(self.right.pos)

        self.left.radius = 0.145 + 0.016 * math.sin(time_seconds * 4.0 + self.index)
        self.right.radius = 0.145 + 0.016 * math.sin(time_seconds * 4.0 + self.index + 1.4)

        conn_visible = 1 - smoothstep(0.32, 0.46, t)
        self.connector.visible = conn_visible > 0.04
        self.connector.opacity = 0.65 * conn_visible
        self.connector.pos = self.left.pos
        self.connector.axis = self.right.pos - self.left.pos

        spindle_birth = smoothstep(0.16, 0.30, t)
        spindle_fade = 1 - smoothstep(0.82, 0.98, t)
        op_base = 0.68 * spindle_birth * spindle_fade

        self.left_fiber.pos = left_pole
        self.left_fiber.axis = self.left.pos - left_pole
        self.left_fiber.opacity = op_base if self.left_attached else op_base * 0.18
        self.left_fiber.radius = 0.018 if self.left_attached else 0.012
        self.left_fiber.color = vector(1.0, 0.84, 0.32) if self.left_attached else vector(0.90, 0.72, 0.60)

        self.right_fiber.pos = right_pole
        self.right_fiber.axis = self.right.pos - right_pole
        self.right_fiber.opacity = op_base if self.right_attached else op_base * 0.18
        self.right_fiber.radius = 0.018 if self.right_attached else 0.012
        self.right_fiber.color = vector(1.0, 0.84, 0.32) if self.right_attached else vector(0.90, 0.72, 0.60)

        highlight = 0.12 if self.selected else 0
        self.left.emissive = self.selected
        self.right.emissive = self.selected
        self.left.color = self.color_left + vector(highlight, highlight, highlight)
        self.right.color = self.color_right + vector(highlight, highlight, highlight)

    def attachment_fraction(self):
        return (1 if self.left_attached else 0) + (1 if self.right_attached else 0)

    def toggle_random_attachment(self):
        if random.random() < 0.5:
            self.left_attached = not self.left_attached
            return self.left_attached
        self.right_attached = not self.right_attached
        return self.right_attached

    def attach_all(self):
        self.left_attached = True
        self.right_attached = True

    def detach_one(self):
        if random.random() < 0.5:
            self.left_attached = False
        else:
            self.right_attached = False


class VesicleParticle:
    def __init__(self, sim, pos, vel, radius=0.045, color_value=None, life=8.0):
        self.sim = sim
        self.vel = vel
        self.life = life
        self.max_life = life
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=color_value if color_value is not None else vector(random.uniform(0.25, 0.75), 0.78, 1.0),
            opacity=0.72,
            shininess=0.35
        )
        sim.register(self.obj)
        self.trail = ManualTrail(sim, vector(0.70, 0.90, 1.0), radius=0.014, max_points=8, stride=5, opacity=0.22)

    def update(self, dt, t):
        self.life -= dt
        self.vel *= 0.995
        self.obj.pos += self.vel * dt
        self.trail.update(self.obj.pos)

        # Bounce against approximate cell boundary.
        if t < 0.68:
            rx = 2.25 + smoothstep(0.0, 0.45, t) * 0.7
            ry = 1.55
            rz = 1.55
            rel = self.obj.pos
            q = vector(rel.x / rx, rel.y / ry, rel.z / rz)
            if mag(q) > 0.98:
                n = safe_norm(vector(rel.x / (rx * rx), rel.y / (ry * ry), rel.z / (rz * rz)))
                self.obj.pos -= n * 0.04
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.72
        else:
            left_center = self.sim.left_daughter.pos
            right_center = self.sim.right_daughter.pos
            center = left_center if mag(self.obj.pos - left_center) < mag(self.obj.pos - right_center) else right_center
            r = 1.43
            rel = self.obj.pos - center
            if mag(rel) > r:
                n = safe_norm(rel)
                self.obj.pos = center + n * r
                self.vel = self.vel - 2 * dot(self.vel, n) * n
                self.vel *= 0.72

        self.obj.opacity = clamp(0.72 * self.life / self.max_life, 0, 0.72)
        self.obj.radius *= 0.999

    def dead(self):
        return self.life <= 0

    def destroy(self):
        dispose_vpython_object(self.obj)
        self.trail.clear()


class MarkerGlyph:
    def __init__(self, sim, pos, text, color_value=vector(0.2, 0.45, 0.9), life=5.0):
        self.sim = sim
        self.life = life
        self.max_life = life
        self.dot = sphere(pos=pos, radius=0.075, color=color_value, opacity=0.75, emissive=True)
        self.lbl = label(
            pos=pos + vector(0, 0.28, 0),
            text=text,
            color=color_value,
            box=False,
            opacity=0,
            height=12,
            border=0
        )
        sim.register(self.dot)
        sim.register(self.lbl)

    def update(self, dt):
        self.life -= dt
        self.dot.pos += vector(0, 0.018 * dt, 0)
        self.lbl.pos = self.dot.pos + vector(0, 0.28, 0)
        fade = clamp(self.life / self.max_life, 0, 1)
        self.dot.opacity = 0.75 * fade
        self.lbl.color = self.dot.color * fade

    def dead(self):
        return self.life <= 0

    def destroy(self):
        dispose_vpython_object(self.dot)
        dispose_vpython_object(self.lbl)


class MembraneWrapper:
    def __init__(self, sim, center, radius, color_value=vector(0.22, 0.62, 0.92), life=7.5):
        self.sim = sim
        self.center = center
        self.life = life
        self.max_life = life
        self.spin = random.choice([-1, 1]) * random.uniform(0.7, 1.5)
        self.phase = random.uniform(0, math.tau)
        self.obj = ring(
            pos=center,
            axis=vector(1, 0, 0),
            radius=radius,
            thickness=0.018,
            color=color_value,
            opacity=0.38
        )
        sim.register(self.obj)

    def update(self, dt, time_seconds):
        self.life -= dt
        self.phase += self.spin * dt
        self.obj.axis = norm(vector(1, math.sin(self.phase) * 0.55, math.cos(self.phase) * 0.55))
        self.obj.pos = self.center + vector(0, 0.06 * math.sin(time_seconds * 1.8 + self.phase), 0)
        self.obj.opacity = 0.38 * clamp(self.life / self.max_life, 0, 1)
        self.obj.radius *= 1.0 + 0.012 * math.sin(time_seconds * 2.0 + self.phase) * dt

    def dead(self):
        return self.life <= 0

    def destroy(self):
        dispose_vpython_object(self.obj)


class MembraneContractionWave:
    """Traveling surface wave that precedes and emphasizes cytokinesis.

    The wave is built from preallocated beads and faint rings, so it can be
    reset safely without VPython trail cleanup. It activates as cytokinesis
    begins, travels around the equator of the cell, and then collapses inward
    into the cleavage furrow.
    """
    def __init__(self, sim, bead_count=36):
        self.sim = sim
        self.bead_count = bead_count
        self.manual_pulse_timer = 0.0
        self.phase_offset = random.uniform(0, math.tau)
        self.beads = []
        for i in range(bead_count):
            bead = sphere(
                pos=vector(0, 0, 0),
                radius=0.035,
                color=vector(0.05, 0.85, 1.0),
                opacity=0,
                emissive=True,
                shininess=0.2,
                visible=False
            )
            self.beads.append(bead)
            sim.register(bead)

        self.leading_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=1.47,
            thickness=0.025,
            color=vector(0.05, 0.72, 1.0),
            opacity=0,
            emissive=True
        )
        self.trailing_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=1.54,
            thickness=0.012,
            color=vector(0.30, 0.92, 1.0),
            opacity=0,
            emissive=True
        )
        self.compression_shadow = ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=1.34,
            thickness=0.018,
            color=vector(0.04, 0.20, 0.32),
            opacity=0
        )
        sim.register(self.leading_ring)
        sim.register(self.trailing_ring)
        sim.register(self.compression_shadow)

    def pulse(self):
        self.manual_pulse_timer = 1.8

    def update(self, dt, t, time_seconds, pinch, cell_x):
        if self.manual_pulse_timer > 0:
            self.manual_pulse_timer = max(0, self.manual_pulse_timer - dt)

        cytokinesis_start = smoothstep(0.46, 0.60, t)
        cytokinesis_end_fade = 1 - smoothstep(0.84, 0.98, t)
        manual_boost = self.manual_pulse_timer / 1.8 if self.manual_pulse_timer > 0 else 0
        wave_strength = clamp(cytokinesis_start * cytokinesis_end_fade + 0.85 * manual_boost, 0, 1)

        # Radius follows the membrane at first, then contracts into the furrow.
        base_radius = lerp(1.52, 0.34, clamp(pinch, 0, 1))
        traveling_angle = (time_seconds * 3.15 + self.phase_offset) % math.tau
        band_width = lerp(0.75, 0.38, pinch)
        x_span = max(0.16, 0.22 + 0.22 * (1 - pinch))

        for i, bead in enumerate(self.beads):
            a = i * math.tau / self.bead_count
            angular_delta = abs(math.atan2(math.sin(a - traveling_angle), math.cos(a - traveling_angle)))
            traveling_front = math.exp(-(angular_delta * angular_delta) / max(0.04, band_width * band_width))
            secondary_front = math.exp(-((abs(math.atan2(math.sin(a - traveling_angle + 1.55), math.cos(a - traveling_angle + 1.55)))) ** 2) / 0.32)
            contraction = clamp(pinch + 0.22 * traveling_front * wave_strength, 0, 1)
            radius = base_radius - 0.12 * traveling_front * wave_strength
            x_ripple = math.sin(a * 2.0 + time_seconds * 5.0) * x_span * wave_strength * (0.25 + 0.75 * traveling_front)
            bead.pos = vector(x_ripple, math.cos(a) * radius, math.sin(a) * radius)
            bead.visible = wave_strength > 0.02
            bead.opacity = clamp(0.08 + 0.74 * traveling_front + 0.22 * secondary_front, 0, 0.86) * wave_strength
            bead.radius = 0.022 + 0.060 * traveling_front * wave_strength + 0.018 * contraction
            bead.color = vector(0.05 + 0.35 * traveling_front, 0.70 + 0.24 * traveling_front, 1.0)

        ripple = math.sin(time_seconds * 6.2) * 0.025 * wave_strength
        self.leading_ring.visible = wave_strength > 0.02
        self.trailing_ring.visible = wave_strength > 0.02
        self.compression_shadow.visible = wave_strength > 0.02
        self.leading_ring.radius = max(0.18, base_radius + ripple)
        self.trailing_ring.radius = max(0.18, base_radius + 0.11 + 0.05 * math.sin(time_seconds * 4.0))
        self.compression_shadow.radius = max(0.16, base_radius - 0.10)
        self.leading_ring.thickness = 0.020 + 0.030 * wave_strength + 0.016 * pinch
        self.trailing_ring.thickness = 0.010 + 0.012 * wave_strength
        self.compression_shadow.thickness = 0.014 + 0.030 * pinch
        self.leading_ring.opacity = 0.62 * wave_strength
        self.trailing_ring.opacity = 0.28 * wave_strength * (1 - 0.45 * pinch)
        self.compression_shadow.opacity = 0.24 * wave_strength * pinch
        wobble_axis = vector(1, 0.04 * math.sin(time_seconds * 3.4), 0.04 * math.cos(time_seconds * 3.4))
        self.leading_ring.axis = wobble_axis
        self.trailing_ring.axis = wobble_axis
        self.compression_shadow.axis = wobble_axis

    def activity(self, t):
        return smoothstep(0.46, 0.60, t) * (1 - smoothstep(0.84, 0.98, t))


class MitosisSimulation:
    def __init__(self):
        self.objects = []
        self.chromosomes = []
        self.particles = []
        self.markers = []
        self.wrappers = []

        self.paused = False
        self.show_labels = True
        self.camera_orbit = False  # default off so mouse drag/pan/rotate controls are not overwritten
        self.time_seconds = 0
        self.progress = 0
        self.round_index = 1
        self.base_progress_speed = 0.045
        self.speed_modifier = 1.0
        self.human_speed_bias = 1.0
        self.ai_noise = 0.0
        self.pull_bias = 1.0
        self.constriction_bias = 1.0
        self.drift_bias = 1.0
        self.human_override_timer = 0
        self.complete_timer = 0

        self.stage_label = label(
            pos=vector(0, 2.9, 0),
            text="",
            box=False,
            opacity=0,
            color=vector(0.10, 0.28, 0.46),
            height=18
        )
        self.ai_label = label(
            pos=vector(0, -2.85, 0),
            text="",
            box=False,
            opacity=0,
            color=vector(0.25, 0.36, 0.58),
            height=13
        )

        self.create_static_scene()
        self.reset_round(full=True)

    def register(self, obj):
        self.objects.append(obj)
        return obj

    def create_static_scene(self):
        self.floor = box(
            pos=vector(0, -2.25, 0),
            size=vector(7.6, 0.025, 4.6),
            color=vector(0.88, 0.94, 0.98),
            opacity=0.35
        )
        self.equator_plate = box(
            pos=vector(0, 0, 0),
            size=vector(0.018, 2.7, 2.7),
            color=vector(0.66, 0.82, 1.0),
            opacity=0.13
        )
        self.equator_plate.visible = True

    def cleanup_dynamic(self):
        # Clear live dynamic helpers first. Trails are manual preallocated dots,
        # so reset only needs to hide those dot primitives.
        for p in list(self.particles):
            p.destroy()
        for m in list(self.markers):
            m.destroy()
        for w in list(self.wrappers):
            w.destroy()

        # Clear every registered VPython object. Avoid delete(), make_trail,
        # and clear_trail to prevent VPython/WebVPython stalls.
        seen = set()
        for obj in list(self.objects):
            ident = id(obj)
            if ident in seen:
                continue
            seen.add(ident)
            dispose_vpython_object(obj)

        self.objects = []
        self.chromosomes = []
        self.particles = []
        self.markers = []
        self.wrappers = []

    def reset_round(self, full=False):
        self.cleanup_dynamic()
        self.time_seconds = 0
        self.progress = 0
        self.speed_modifier = 1.0
        self.ai_noise = 0.0
        self.pull_bias = 1.0
        self.constriction_bias = 1.0
        self.drift_bias = 1.0
        self.complete_timer = 0
        self.human_override_timer = 0
        if not full:
            self.round_index += 1

        self.single_cell = sphere(
            pos=vector(0, 0, 0),
            radius=1,
            size=vector(3.45, 3.05, 3.05),
            color=vector(0.49, 0.81, 0.96),
            opacity=0.24,
            shininess=0.4
        )
        self.register(self.single_cell)

        self.single_membrane = sphere(
            pos=vector(0, 0, 0),
            radius=1,
            size=vector(3.55, 3.15, 3.15),
            color=vector(0.18, 0.55, 0.90),
            opacity=0.12,
            shininess=0.8
        )
        self.register(self.single_membrane)

        self.left_daughter = sphere(
            pos=vector(-0.6, 0, 0),
            radius=1,
            size=vector(2.75, 2.75, 2.75),
            color=vector(0.50, 0.86, 0.98),
            opacity=0,
            shininess=0.45
        )
        self.right_daughter = sphere(
            pos=vector(0.6, 0, 0),
            radius=1,
            size=vector(2.75, 2.75, 2.75),
            color=vector(0.50, 0.86, 0.98),
            opacity=0,
            shininess=0.45
        )
        self.register(self.left_daughter)
        self.register(self.right_daughter)

        self.bridge = cylinder(
            pos=vector(-0.15, 0, 0),
            axis=vector(0.30, 0, 0),
            radius=1.25,
            color=vector(0.45, 0.82, 0.95),
            opacity=0
        )
        self.register(self.bridge)

        self.cleavage_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=1.48,
            thickness=0.035,
            color=vector(0.08, 0.50, 0.72),
            opacity=0
        )
        self.register(self.cleavage_ring)

        self.contraction_wave = MembraneContractionWave(self)

        self.left_nucleus = sphere(
            pos=vector(-1.3, 0, 0),
            radius=0.86,
            color=vector(0.73, 0.76, 1.0),
            opacity=0,
            shininess=0.35
        )
        self.right_nucleus = sphere(
            pos=vector(1.3, 0, 0),
            radius=0.86,
            color=vector(0.73, 0.76, 1.0),
            opacity=0,
            shininess=0.35
        )
        self.register(self.left_nucleus)
        self.register(self.right_nucleus)

        self.left_pole_obj = sphere(
            pos=vector(-0.55, 0, 0),
            radius=0.13,
            color=vector(1.0, 0.72, 0.18),
            emissive=True
        )
        self.right_pole_obj = sphere(
            pos=vector(0.55, 0, 0),
            radius=0.13,
            color=vector(1.0, 0.72, 0.18),
            emissive=True
        )
        self.register(self.left_pole_obj)
        self.register(self.right_pole_obj)

        self.pole_glow_left = sphere(
            pos=self.left_pole_obj.pos,
            radius=0.27,
            color=vector(1.0, 0.88, 0.42),
            opacity=0.17,
            emissive=True
        )
        self.pole_glow_right = sphere(
            pos=self.right_pole_obj.pos,
            radius=0.27,
            color=vector(1.0, 0.88, 0.42),
            opacity=0.17,
            emissive=True
        )
        self.register(self.pole_glow_left)
        self.register(self.pole_glow_right)

        count = 9
        for i in range(count):
            angle = i * math.tau / count + random.uniform(-0.12, 0.12)
            radius_ring = random.uniform(0.25, 0.78)
            self.chromosomes.append(ChromosomePair(self, i, angle, radius_ring))

        self.mark(vector(0, 0.95, 0), "duplicated chromosome cluster", vector(0.45, 0.25, 0.85), life=4.0)

    def stage_name(self):
        t = self.progress
        if t < 0.16:
            return "Prophase: duplicated chromosomes condense"
        if t < 0.34:
            return "Metaphase: spindle fibers attach and organize"
        if t < 0.58:
            return "Anaphase: chromosomes are pulled apart"
        if t < 0.82:
            return "Cytokinesis: contraction wave tightens membrane"
        if t < 0.98:
            return "Daughter cells detach and drift apart"
        return "Division complete"

    def get_state(self):
        left_positions = [c.left.pos for c in self.chromosomes]
        right_positions = [c.right.pos for c in self.chromosomes]
        sep = 0
        if self.chromosomes:
            sep = sum([abs(r.x - l.x) for l, r in zip(left_positions, right_positions)]) / len(self.chromosomes)
        attached = 0
        total = max(1, len(self.chromosomes) * 2)
        for c in self.chromosomes:
            attached += c.attachment_fraction()
        return {
            "progress": self.progress,
            "stage": self.stage_name(),
            "time_seconds": self.time_seconds,
            "chromosome_separation": sep,
            "attachment_ratio": attached / total,
            "particle_count": len(self.particles),
            "marker_count": len(self.markers),
            "wrapper_count": len(self.wrappers),
            "daughter_distance": mag(self.right_daughter.pos - self.left_daughter.pos),
            "is_complete": self.progress >= 0.999,
            "complete_timer": self.complete_timer,
            "paused": self.paused
        }

    def current_poles(self):
        t = self.progress
        pole_u = smoothstep(0.05, 0.33, t)
        left = vector(lerp(-0.55, -1.72, pole_u), 0, 0)
        right = vector(lerp(0.55, 1.72, pole_u), 0, 0)
        return left, right

    def update(self, dt):
        if self.paused:
            return

        self.time_seconds += dt
        if self.human_override_timer > 0:
            self.human_override_timer -= dt

        speed = self.base_progress_speed * self.speed_modifier * self.human_speed_bias
        if self.progress < 1:
            self.progress = clamp(self.progress + dt * speed, 0, 1)
        else:
            self.complete_timer += dt

        t = self.progress
        left_pole, right_pole = self.current_poles()

        stretch = smoothstep(0.0, 0.35, t)
        split = smoothstep(0.50, 0.78, t)
        detach = smoothstep(0.78, 1.0, t)
        pinch = clamp(smoothstep(0.52, 0.82, t) * self.constriction_bias, 0, 1)
        daughter_d = lerp(0.72, 2.25, split) + detach * 0.46 * self.drift_bias

        cell_x = lerp(3.45, 4.75, stretch)
        self.single_cell.size = vector(cell_x, 3.05 - 0.18 * stretch, 3.05 - 0.18 * stretch)
        self.single_membrane.size = vector(cell_x + 0.1, 3.15 - 0.18 * stretch, 3.15 - 0.18 * stretch)
        self.single_cell.opacity = 0.24 * (1 - 0.94 * split)
        self.single_membrane.opacity = 0.12 * (1 - 0.90 * split)

        daughter_radius = lerp(1.22, 1.42, smoothstep(0.55, 0.90, t))
        self.left_daughter.pos = vector(-daughter_d, 0, 0)
        self.right_daughter.pos = vector(daughter_d, 0, 0)
        self.left_daughter.size = vector(2 * daughter_radius, 2 * daughter_radius, 2 * daughter_radius)
        self.right_daughter.size = vector(2 * daughter_radius, 2 * daughter_radius, 2 * daughter_radius)
        self.left_daughter.opacity = 0.23 * split
        self.right_daughter.opacity = 0.23 * split

        bridge_op = smoothstep(0.48, 0.62, t) * (1 - smoothstep(0.80, 0.97, t))
        self.bridge.pos = vector(-0.16, 0, 0)
        self.bridge.axis = vector(0.32, 0, 0)
        self.bridge.radius = lerp(1.28, 0.14, pinch)
        self.bridge.opacity = 0.18 * bridge_op

        self.cleavage_ring.radius = lerp(1.47, 0.20, pinch)
        self.cleavage_ring.thickness = lerp(0.035, 0.058, pinch)
        self.cleavage_ring.opacity = 0.70 * bridge_op
        self.cleavage_ring.axis = vector(1, 0.05 * math.sin(self.time_seconds * 2.5), 0.05 * math.cos(self.time_seconds * 2.5))

        self.contraction_wave.update(dt, t, self.time_seconds, pinch, cell_x)

        nuc_op = smoothstep(0.64, 0.88, t)
        self.left_nucleus.pos = vector(-daughter_d, 0, 0)
        self.right_nucleus.pos = vector(daughter_d, 0, 0)
        self.left_nucleus.opacity = 0.14 * nuc_op
        self.right_nucleus.opacity = 0.14 * nuc_op

        self.left_pole_obj.pos = left_pole
        self.right_pole_obj.pos = right_pole
        self.left_pole_obj.radius = 0.13 + 0.025 * math.sin(self.time_seconds * 4.0)
        self.right_pole_obj.radius = 0.13 + 0.025 * math.sin(self.time_seconds * 4.0 + 1.7)
        self.pole_glow_left.pos = left_pole
        self.pole_glow_right.pos = right_pole

        for c in self.chromosomes:
            c.update(
                t,
                self.time_seconds,
                left_pole,
                right_pole,
                self.left_nucleus.pos,
                self.right_nucleus.pos,
                self.ai_noise,
                self.pull_bias
            )

        for p in list(self.particles):
            p.update(dt, t)
            if p.dead():
                p.destroy()
                self.particles.remove(p)

        for m in list(self.markers):
            m.update(dt)
            if m.dead():
                m.destroy()
                self.markers.remove(m)

        for w in list(self.wrappers):
            w.update(dt, self.time_seconds)
            if w.dead():
                w.destroy()
                self.wrappers.remove(w)

        self.stage_label.visible = self.show_labels
        self.ai_label.visible = self.show_labels
        wave_activity = int(self.contraction_wave.activity(t) * 100)
        furrow_depth = int(pinch * 100)
        self.stage_label.text = (
            f"Round {self.round_index} — {self.stage_name()}  |  "
            f"progress {int(self.progress * 100)}%  |  "
            f"contraction wave {wave_activity}%  |  furrow depth {furrow_depth}%"
        )
        self.stage_label.pos = vector(0, 2.82, 0)

        # Only run scripted camera orbit when the user explicitly toggles it on with C.
        # When this is off, VPython's normal mouse camera controls remain active.
        if self.camera_orbit:
            angle = self.time_seconds * 0.06
            scene.forward = norm(vector(-0.16 * math.sin(angle), -0.12, -1))
            scene.center = vector(0, 0, 0)

        self.equator_plate.visible = self.show_labels and t < 0.62
        self.equator_plate.opacity = 0.13 * (1 - smoothstep(0.48, 0.65, t))

    def spill_particles(self, count=16, source=None, mood="soft"):
        if source is None:
            if self.progress > 0.62:
                source = vector(0, 0, 0)
            else:
                source = vector(random.uniform(-0.35, 0.35), random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5))

        for _ in range(count):
            direction = safe_norm(vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
            if mood == "chaotic":
                speed = random.uniform(0.45, 1.25)
                col = vector(random.uniform(0.75, 1.0), random.uniform(0.35, 0.8), random.uniform(0.35, 1.0))
            elif mood == "ritual":
                speed = random.uniform(0.20, 0.55)
                col = vector(0.35 + random.random() * 0.15, 0.62 + random.random() * 0.2, 1.0)
            else:
                speed = random.uniform(0.18, 0.75)
                col = vector(random.uniform(0.30, 0.75), random.uniform(0.65, 0.95), 1.0)
            vel = direction * speed
            self.particles.append(VesicleParticle(self, source + direction * random.uniform(0.04, 0.20), vel, color_value=col))

    def mark(self, pos, text, color_value=vector(0.2, 0.45, 0.9), life=4.5):
        self.markers.append(MarkerGlyph(self, pos, text, color_value, life))

    def create_wrappers(self, target="both"):
        t = self.progress
        split = smoothstep(0.50, 0.78, t)
        if target in ("both", "left"):
            self.wrappers.append(MembraneWrapper(self, self.left_daughter.pos, 1.48 if split > 0.2 else 1.65, vector(0.22, 0.62, 0.92)))
        if target in ("both", "right"):
            self.wrappers.append(MembraneWrapper(self, self.right_daughter.pos, 1.48 if split > 0.2 else 1.65, vector(0.24, 0.70, 0.82)))

    def pulse_contraction_wave(self):
        if hasattr(self, "contraction_wave"):
            self.contraction_wave.pulse()
            self.mark(vector(0, 1.55, 0), "membrane contraction wave", vector(0.05, 0.72, 1.0), life=2.0)

    def toggle_random_spindle_attachment(self):
        if not self.chromosomes:
            return
        c = random.choice(self.chromosomes)
        for ch in self.chromosomes:
            ch.selected = False
        c.selected = True
        attached = c.toggle_random_attachment()
        self.mark(c.left.pos if random.random() < 0.5 else c.right.pos, "attached" if attached else "detached", vector(0.96, 0.45, 0.32), life=2.8)

    def attach_all_spindles(self):
        for c in self.chromosomes:
            c.attach_all()

    def detach_some_spindles(self, fraction=0.2):
        for c in self.chromosomes:
            if random.random() < fraction:
                c.detach_one()

    def nudge_camera(self, direction):
        scene.forward = rotate(scene.forward, angle=direction * 0.08, axis=vector(0, 1, 0))

    def pause_toggle(self):
        self.paused = not self.paused


class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.override = False
        self.mode = "OBSERVE"
        self.previous_modes = []
        self.mode_timer = 0
        self.mode_duration = 5.0
        self.action_timer = 0
        self.last_state_vector = None
        self.last_change_time = 0
        self.stagnation_time = 0
        self.reset_countdown = None
        self.playfulness = 0.55
        self.chaos = 0.25
        self.carefulness = 0.45
        self.artistry = 0.42
        self.behavior_modes = [
            "OBSERVE",
            "ORGANIZE",
            "PULL",
            "PINCH",
            "CELEBRATE",
            "CHAOTIC",
            "CAREFUL",
            "CURIOUS",
            "ARTISTIC",
            "RITUAL",
            "RESETTING"
        ]

    def read_state_vector(self):
        s = self.sim.get_state()
        return vector(
            s["progress"],
            s["chromosome_separation"] * 0.15,
            s["daughter_distance"] * 0.1
        )

    def detect_stagnation(self, dt):
        current = self.read_state_vector()
        if self.last_state_vector is None:
            self.last_state_vector = current
            self.stagnation_time = 0
            return False

        delta = mag(current - self.last_state_vector)
        self.last_state_vector = current
        if delta < 0.0009:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0, self.stagnation_time - dt * 1.5)
        return self.stagnation_time > 4.5

    def force_next_mode(self):
        self.mode_timer = self.mode_duration + 1.0

    def choose_mode(self, state, stagnating=False):
        t = state["progress"]

        if state["is_complete"] and state["complete_timer"] > 4.0:
            return "RESETTING"
        if state["is_complete"]:
            return random.choice(["CELEBRATE", "ARTISTIC", "RITUAL"])
        if stagnating:
            return random.choice(["CHAOTIC", "CURIOUS", "PULL", "ARTISTIC"])

        if t < 0.16:
            pool = ["OBSERVE", "CURIOUS", "RITUAL"]
        elif t < 0.34:
            pool = ["ORGANIZE", "CAREFUL", "CURIOUS", "ARTISTIC"]
        elif t < 0.58:
            pool = ["PULL", "CAREFUL", "CHAOTIC", "ORGANIZE"]
        elif t < 0.82:
            pool = ["PINCH", "RITUAL", "ARTISTIC", "CURIOUS"]
        else:
            pool = ["CELEBRATE", "ARTISTIC", "RITUAL", "OBSERVE"]

        if self.previous_modes:
            recent = set(self.previous_modes[-2:])
            filtered = [m for m in pool if m not in recent]
            if filtered:
                pool = filtered

        return random.choice(pool)

    def set_mode(self, mode):
        if mode not in self.behavior_modes:
            return
        self.previous_modes.append(self.mode)
        self.previous_modes = self.previous_modes[-5:]
        self.mode = mode
        self.mode_timer = 0
        self.mode_duration = random.uniform(3.2, 7.2)
        self.action_timer = 0

        colors = {
            "OBSERVE": vector(0.24, 0.50, 0.88),
            "ORGANIZE": vector(0.26, 0.72, 0.56),
            "PULL": vector(0.95, 0.56, 0.18),
            "PINCH": vector(0.10, 0.58, 0.72),
            "CELEBRATE": vector(0.90, 0.42, 0.88),
            "CHAOTIC": vector(1.00, 0.30, 0.28),
            "CAREFUL": vector(0.48, 0.62, 0.98),
            "CURIOUS": vector(0.66, 0.42, 0.94),
            "ARTISTIC": vector(0.18, 0.70, 0.95),
            "RITUAL": vector(0.42, 0.62, 1.00),
            "RESETTING": vector(0.30, 0.34, 0.45)
        }
        if mode != "RESETTING":
            self.sim.mark(vector(0, -1.72, 0), f"AI mode: {mode.lower()}", colors.get(mode, vector(0.2, 0.4, 0.8)), life=2.5)

    def update(self, dt):
        s = self.sim.get_state()

        if not self.enabled:
            self.sim.ai_noise *= 0.94
            self.sim.speed_modifier = lerp(self.sim.speed_modifier, 1.0, 0.03)
            self.sim.ai_label.text = "AI off — keyboard control active"
            return

        if self.sim.paused:
            self.sim.ai_label.text = f"AI paused in {self.mode.lower()} mode"
            return

        if self.override or self.sim.human_override_timer > 0:
            self.sim.ai_noise *= 0.92
            self.sim.speed_modifier = lerp(self.sim.speed_modifier, 1.0, 0.05)
            self.sim.ai_label.text = f"Human override — AI waiting ({self.mode.lower()})"
            return

        stagnating = self.detect_stagnation(dt)
        self.mode_timer += dt
        self.action_timer += dt

        if self.mode_timer > self.mode_duration or stagnating:
            self.set_mode(self.choose_mode(s, stagnating=stagnating))

        if s["is_complete"] and s["complete_timer"] > 7.0 and self.mode != "RESETTING":
            self.set_mode("RESETTING")

        self.apply_behavior(dt, s, stagnating)

        self.sim.ai_label.text = (
            f"AI on — mode: {self.mode.lower()} | "
            f"attachments {int(s['attachment_ratio'] * 100)}% | "
            f"particles {s['particle_count']} | "
            f"{'stagnation detected' if stagnating else 'adaptive loop'}"
        )

    def apply_behavior(self, dt, state, stagnating):
        mode = self.mode
        sim = self.sim

        sim.speed_modifier = lerp(sim.speed_modifier, 1.0, 0.025)
        sim.ai_noise = lerp(sim.ai_noise, 0.02, 0.04)
        sim.pull_bias = lerp(sim.pull_bias, 1.0, 0.04)
        sim.constriction_bias = lerp(sim.constriction_bias, 1.0, 0.04)
        sim.drift_bias = lerp(sim.drift_bias, 1.0, 0.04)

        if mode == "OBSERVE":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.82, 0.04)
            # Do not force camera orbit here; leave camera control to the user.
            sim.ai_noise = lerp(sim.ai_noise, 0.035, 0.03)
            if self.action_timer > 3.0:
                self.action_timer = 0
                sim.mark(vector(random.uniform(-0.7, 0.7), random.uniform(0.2, 1.0), random.uniform(-0.5, 0.5)), "observing", vector(0.24, 0.50, 0.88), life=3.0)

        elif mode == "ORGANIZE":
            sim.speed_modifier = lerp(sim.speed_modifier, 1.05, 0.05)
            sim.ai_noise = lerp(sim.ai_noise, 0.0, 0.09)
            sim.pull_bias = lerp(sim.pull_bias, 1.08, 0.05)
            if self.action_timer > 1.6:
                self.action_timer = 0
                sim.attach_all_spindles()
                sim.mark(vector(0, 1.25, 0), "spindles organized", vector(0.26, 0.72, 0.56), life=2.6)

        elif mode == "PULL":
            sim.speed_modifier = lerp(sim.speed_modifier, 1.32, 0.05)
            sim.pull_bias = lerp(sim.pull_bias, 1.28, 0.08)
            sim.ai_noise = lerp(sim.ai_noise, 0.055, 0.04)
            if self.action_timer > 2.2:
                self.action_timer = 0
                sim.attach_all_spindles()
                left_pole, right_pole = sim.current_poles()
                sim.spill_particles(5, source=random.choice([left_pole, right_pole]), mood="soft")

        elif mode == "PINCH":
            sim.speed_modifier = lerp(sim.speed_modifier, 1.20, 0.06)
            sim.constriction_bias = lerp(sim.constriction_bias, 1.35, 0.07)
            sim.ai_noise = lerp(sim.ai_noise, 0.025, 0.05)
            if self.action_timer > 1.9:
                self.action_timer = 0
                sim.spill_particles(8, source=vector(0, 0, 0), mood="ritual")
                sim.pulse_contraction_wave()
                sim.mark(vector(0, 0.95, 0), "cleavage furrow tightens", vector(0.10, 0.58, 0.72), life=2.6)

        elif mode == "CELEBRATE":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.88, 0.04)
            sim.drift_bias = lerp(sim.drift_bias, 1.35, 0.06)
            sim.ai_noise = lerp(sim.ai_noise, 0.065, 0.04)
            # Do not force camera orbit here; leave camera control to the user.
            if self.action_timer > 1.25:
                self.action_timer = 0
                src = random.choice([sim.left_daughter.pos, sim.right_daughter.pos, vector(0, 0, 0)])
                sim.spill_particles(10, source=src, mood="soft")
                if random.random() < 0.45:
                    sim.create_wrappers("both")

        elif mode == "CHAOTIC":
            sim.speed_modifier = lerp(sim.speed_modifier, 1.45, 0.06)
            sim.ai_noise = lerp(sim.ai_noise, 0.22, 0.08)
            sim.pull_bias = lerp(sim.pull_bias, random.uniform(0.85, 1.25), 0.08)
            if self.action_timer > 0.85:
                self.action_timer = 0
                if random.random() < 0.55:
                    sim.toggle_random_spindle_attachment()
                else:
                    sim.spill_particles(12, mood="chaotic")

        elif mode == "CAREFUL":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.62, 0.05)
            sim.ai_noise = lerp(sim.ai_noise, 0.0, 0.09)
            sim.pull_bias = lerp(sim.pull_bias, 0.96, 0.07)
            if self.action_timer > 2.4:
                self.action_timer = 0
                sim.attach_all_spindles()
                sim.mark(vector(0, -1.22, 0), "careful repair", vector(0.48, 0.62, 0.98), life=2.8)

        elif mode == "CURIOUS":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.98, 0.04)
            sim.ai_noise = lerp(sim.ai_noise, 0.10, 0.05)
            if self.action_timer > 1.7:
                self.action_timer = 0
                target = random.choice(sim.chromosomes)
                for c in sim.chromosomes:
                    c.selected = False
                target.selected = True
                sim.mark(target.left.pos, "inspect", vector(0.66, 0.42, 0.94), life=2.1)
                if random.random() < 0.25:
                    target.toggle_random_attachment()

        elif mode == "ARTISTIC":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.90, 0.04)
            sim.ai_noise = lerp(sim.ai_noise, 0.075, 0.04)
            # Do not force camera orbit here; leave camera control to the user.
            if self.action_timer > 1.35:
                self.action_timer = 0
                if random.random() < 0.60:
                    sim.create_wrappers(random.choice(["both", "left", "right"]))
                else:
                    sim.spill_particles(7, source=vector(random.uniform(-1.0, 1.0), random.uniform(-0.8, 0.8), random.uniform(-0.8, 0.8)), mood="ritual")

        elif mode == "RITUAL":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.76, 0.04)
            sim.ai_noise = lerp(sim.ai_noise, 0.035 + 0.035 * math.sin(sim.time_seconds * 1.7), 0.05)
            if self.action_timer > 2.0:
                self.action_timer = 0
                sim.create_wrappers("both")
                sim.spill_particles(6, source=vector(0, 0, 0), mood="ritual")
                sim.mark(vector(0, 1.55, 0), "loop ritual", vector(0.42, 0.62, 1.00), life=3.0)

        elif mode == "RESETTING":
            sim.speed_modifier = lerp(sim.speed_modifier, 0.0, 0.10)
            sim.ai_noise = lerp(sim.ai_noise, 0.0, 0.10)
            if self.reset_countdown is None:
                self.reset_countdown = 2.0
                sim.mark(vector(0, 0, 0), "resetting next round", vector(0.30, 0.34, 0.45), life=2.0)
            self.reset_countdown -= dt
            if self.reset_countdown <= 0:
                self.reset_countdown = None
                sim.reset_round()
                self.last_state_vector = None
                self.stagnation_time = 0
                self.set_mode("OBSERVE")


sim = MitosisSimulation()
ai = AIController(sim)


def keydown(evt):
    key = evt.key.lower()
    sim.human_override_timer = 1.8

    if key == " ":
        sim.pause_toggle()
    elif key == "a":
        ai.enabled = not ai.enabled
    elif key == "m":
        ai.force_next_mode()
    elif key == "r":
        sim.reset_round()
        ai.last_state_vector = None
        ai.stagnation_time = 0
        ai.set_mode("OBSERVE")
    elif key == "s":
        sim.spill_particles(18, mood="chaotic" if random.random() < 0.5 else "soft")
    elif key == "d":
        sim.toggle_random_spindle_attachment()
    elif key == "f":
        sim.pulse_contraction_wave()
    elif key == "w":
        sim.create_wrappers("both")
    elif key == "c":
        sim.camera_orbit = not sim.camera_orbit
        sim.mark(
            vector(0, -1.85, 0),
            "scripted camera orbit on" if sim.camera_orbit else "mouse camera control active",
            vector(0.2, 0.5, 0.9),
            life=2.2
        )
    elif key == "l":
        sim.show_labels = not sim.show_labels
    elif key == "x":
        ai.override = not ai.override
    elif key == "up":
        sim.human_speed_bias = clamp(sim.human_speed_bias + 0.12, 0.2, 2.2)
        sim.mark(vector(0, -1.55, 0), f"speed bias {sim.human_speed_bias:.2f}", vector(0.2, 0.5, 0.9), life=2.0)
    elif key == "down":
        sim.human_speed_bias = clamp(sim.human_speed_bias - 0.12, 0.2, 2.2)
        sim.mark(vector(0, -1.55, 0), f"speed bias {sim.human_speed_bias:.2f}", vector(0.2, 0.5, 0.9), life=2.0)
    elif key == "left":
        sim.nudge_camera(-1)
    elif key == "right":
        sim.nudge_camera(1)
    elif key in [str(i) for i in range(1, 10)]:
        index = int(key) - 1
        selectable = ai.behavior_modes[:-1]
        if index < len(selectable):
            ai.set_mode(selectable[index])


scene.bind("keydown", keydown)

controls = label(
    pos=vector(0, -3.18, 0),
    text="Space pause | A AI | M mode | R reset | S particles | D spindle | F furrow wave | W wrap | C camera | L labels | X override",
    box=False,
    opacity=0,
    color=vector(0.28, 0.34, 0.44),
    height=11
)

last_time = 0
dt = 1 / 60

while True:
    rate(60)
    ai.update(dt)
    sim.update(dt)
    controls.visible = sim.show_labels
    controls.pos = vector(0, -3.18, 0)
