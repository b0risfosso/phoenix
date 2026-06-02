from vpython import *
import random
import math
from collections import deque

# ============================================================
# 3D VPython Neuronal Cell Body Simulation with Expressive AI
# ============================================================

scene.title = "Neuronal Cell Body with Branching Dendrites, Axon Pulse, and AI Controller"
scene.width = 1180
scene.height = 760
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.75, -0.18, -0.62)
scene.up = vector(0, 1, 0)
scene.range = 12.5
scene.center = vector(3, 0, 0)

random.seed(8)

SOFT_GREEN = vector(0.52, 0.82, 0.62)
DENDRITE_GREEN = vector(0.46, 0.74, 0.56)
SOMA_COLOR = vector(0.93, 0.64, 0.76)
SOMA_FLASH = vector(1.0, 0.96, 0.35)
AXON_COLOR = vector(0.56, 0.72, 0.98)
SYNAPSE_COLOR = vector(0.96, 0.48, 0.95)
SIGNAL_COLOR = vector(1.0, 0.86, 0.18)
PULSE_COLOR = vector(1.0, 0.98, 0.20)
AI_BLUE = vector(0.25, 0.58, 1.0)
AI_PURPLE = vector(0.70, 0.40, 1.0)
AI_RED = vector(1.0, 0.32, 0.24)
AI_GREEN = vector(0.20, 0.86, 0.52)
AI_GOLD = vector(1.0, 0.68, 0.16)
AI_CYAN = vector(0.15, 0.9, 1.0)


def clamp(x, a, b):
    return max(a, min(b, x))


def mix(a, b, t):
    t = clamp(t, 0, 1)
    return a * (1 - t) + b * t


def safe_norm(v):
    if mag(v) < 1e-8:
        return vector(1, 0, 0)
    return norm(v)


def random_unit():
    z = random.uniform(-1, 1)
    theta = random.uniform(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(theta), z, r * math.sin(theta))


def path_length(points):
    total = 0
    for i in range(len(points) - 1):
        total += mag(points[i + 1] - points[i])
    return total


def point_on_path(points, distance):
    if len(points) < 2:
        return points[0] if points else vector(0, 0, 0)
    d = max(0, distance)
    for i in range(len(points) - 1):
        a = points[i]
        b = points[i + 1]
        seg_len = mag(b - a)
        if seg_len <= 1e-8:
            continue
        if d <= seg_len:
            return a + (b - a) * (d / seg_len)
        d -= seg_len
    return points[-1]


class SignalParticle:
    def __init__(self, sim, synapse_index, color_value=SIGNAL_COLOR):
        self.sim = sim
        self.synapse_index = synapse_index
        self.path = list(sim.synapses[synapse_index]["path"])
        self.total_length = max(0.001, path_length(self.path))
        self.distance = 0.0
        self.speed = random.uniform(2.0, 3.5)
        self.radius = random.uniform(0.075, 0.12)
        self.finished = False
        self.transfer_flash = 0.0
        start_pos = self.path[0]
        self.obj = sphere(
            pos=start_pos,
            radius=self.radius,
            color=color_value,
            emissive=True,
            shininess=0.8,
            make_trail=True,
            retain=18,
            trail_radius=self.radius * 0.35,
            trail_color=color_value,
        )

    def update(self, dt):
        if self.finished:
            return False

        self.distance += self.speed * dt
        self.obj.pos = point_on_path(self.path, self.distance)

        syn = self.sim.synapses[self.synapse_index]
        syn["signal_glow"] = max(syn["signal_glow"], 0.55)

        if self.distance >= self.total_length:
            self.finished = True
            self.obj.visible = False
            self.obj.clear_trail()
            self.sim.receive_dendrite_signal(self.synapse_index)
            return False
        return True


class AxonPulse:
    def __init__(self, sim):
        self.sim = sim
        self.path = sim.axon_path
        self.total_length = max(0.001, path_length(self.path))
        self.distance = 0.0
        self.speed = 6.2
        self.finished = False
        self.trail_timer = 0.0
        self.obj = sphere(
            pos=self.path[0],
            radius=0.24,
            color=PULSE_COLOR,
            emissive=True,
            shininess=1.0,
        )
        self.halo = sphere(
            pos=self.path[0],
            radius=0.43,
            color=vector(1.0, 0.95, 0.25),
            opacity=0.22,
            emissive=True,
        )

    def update(self, dt):
        if self.finished:
            return False

        self.distance += self.speed * dt
        p = point_on_path(self.path, self.distance)
        self.obj.pos = p
        self.halo.pos = p
        self.halo.radius = 0.42 + 0.07 * math.sin(self.sim.t * 25)

        self.trail_timer -= dt
        if self.trail_timer <= 0:
            self.trail_timer = 0.045
            self.sim.add_fading_trail(p, PULSE_COLOR, 0.23, 1.15)

        if self.distance >= self.total_length:
            self.finished = True
            self.obj.visible = False
            self.halo.visible = False
            self.sim.axon_terminal_flash = 1.0
            self.sim.last_activity_time = self.sim.t
            return False
        return True


class FadingTrail:
    def __init__(self, pos, color_value, radius, life):
        self.life = life
        self.max_life = life
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=color_value,
            opacity=0.48,
            emissive=True,
        )

    def update(self, dt):
        self.life -= dt
        f = max(0, self.life / self.max_life)
        self.obj.opacity = 0.48 * f
        self.obj.radius *= 0.992
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


class SpillParticle:
    def __init__(self, pos, color_value):
        self.vel = random_unit() * random.uniform(0.25, 1.1) + vector(0, random.uniform(0.1, 0.6), 0)
        self.life = random.uniform(3.0, 6.0)
        self.max_life = self.life
        self.obj = sphere(
            pos=pos + random_unit() * random.uniform(0.05, 0.32),
            radius=random.uniform(0.035, 0.075),
            color=color_value,
            opacity=0.42,
            emissive=True,
        )

    def update(self, dt):
        self.life -= dt
        self.vel += vector(0, -0.22, 0) * dt
        self.obj.pos += self.vel * dt

        floor_y = -4.8
        if self.obj.pos.y < floor_y:
            self.obj.pos.y = floor_y
            self.vel.y = abs(self.vel.y) * 0.55
            self.vel.x *= 0.82
            self.vel.z *= 0.82

        f = max(0, self.life / self.max_life)
        self.obj.opacity = 0.42 * f
        self.obj.radius *= 0.998
        if self.life <= 0:
            self.obj.visible = False
            return False
        return True


class AttachedMarker:
    def __init__(self, segment, color_value, text=None):
        self.segment = segment
        self.life = random.uniform(9.0, 18.0)
        self.max_life = self.life
        mid = (segment["start"] + segment["end"]) * 0.5
        tangent = safe_norm(segment["end"] - segment["start"])
        self.obj = sphere(
            pos=mid + random_unit() * 0.08,
            radius=segment["radius"] * 1.9 + 0.035,
            color=color_value,
            opacity=0.70,
            emissive=True,
        )
        self.ring = ring(
            pos=mid,
            axis=tangent,
            radius=segment["radius"] * 3.2 + 0.08,
            thickness=0.012,
            color=color_value,
            opacity=0.45,
            emissive=True,
        )
        self.label = None
        if text:
            self.label = label(
                pos=mid + vector(0, 0.28, 0),
                text=text,
                height=8,
                color=color_value,
                box=False,
                opacity=0,
            )

    def detach_now(self):
        self.life = min(self.life, 0.5)

    def update(self, dt):
        self.life -= dt
        f = max(0, self.life / self.max_life)
        self.obj.opacity = 0.70 * f
        self.ring.opacity = 0.45 * f
        self.ring.rotate(angle=dt * 1.8, axis=self.ring.axis, origin=self.ring.pos)
        if self.label:
            self.label.opacity = 0
            self.label.color = self.obj.color * f + vector(0.4, 0.4, 0.4) * (1 - f)
        if self.life <= 0:
            self.obj.visible = False
            self.ring.visible = False
            if self.label:
                self.label.visible = False
            return False
        return True


class AxonWrap:
    def __init__(self, sim, color_value):
        self.sim = sim
        self.life = random.uniform(9.0, 15.0)
        self.max_life = self.life
        self.points = []
        self.objs = []
        steps = 80
        total = path_length(sim.axon_path)
        phase = random.uniform(0, 2 * math.pi)
        for i in range(steps):
            d = total * i / (steps - 1)
            center = point_on_path(sim.axon_path, d)
            angle = phase + i * 0.55
            offset = vector(0, math.cos(angle), math.sin(angle)) * 0.38
            self.points.append(center + offset)
        self.curve = curve(
            pos=self.points,
            radius=0.025,
            color=color_value,
            opacity=0.52,
            emissive=True,
        )

    def update(self, dt):
        self.life -= dt
        f = max(0, self.life / self.max_life)
        self.curve.opacity = 0.52 * f
        if self.life <= 0:
            self.curve.visible = False
            return False
        return True


class NeuronSimulation:
    def __init__(self):
        self.t = 0.0
        self.paused = False
        self.round_index = 1
        self.last_activity_time = 0.0

        self.soma_radius = 1.25
        self.soma_flash = 0.0
        self.soma_charge = 0
        self.charge_threshold = 3
        self.axon_terminal_flash = 0.0

        self.segments = []
        self.synapses = []
        self.particles = []
        self.pulses = []
        self.trails = []
        self.spills = []
        self.markers = []
        self.wraps = []

        self.create_static_scene()
        self.ai = None

    def create_static_scene(self):
        distant_light(direction=vector(-0.3, -0.6, -0.8), color=vector(0.75, 0.75, 0.78))
        local_light(pos=vector(0, 5, 7), color=vector(0.55, 0.62, 0.75))

        self.floor = box(
            pos=vector(4, -4.86, 0),
            size=vector(28, 0.03, 16),
            color=vector(0.88, 0.94, 0.98),
            opacity=0.35,
        )

        self.soma = sphere(
            pos=vector(0, 0, 0),
            radius=self.soma_radius,
            color=SOMA_COLOR,
            opacity=0.93,
            shininess=0.78,
        )
        self.soma_nucleus = sphere(
            pos=vector(-0.16, 0.08, 0.05),
            radius=0.46,
            color=vector(0.72, 0.44, 0.82),
            opacity=0.38,
            shininess=0.9,
        )
        self.soma_membrane_ring = ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=self.soma_radius * 1.03,
            thickness=0.018,
            color=vector(1.0, 0.8, 0.92),
            opacity=0.45,
        )

        self.create_dendrites()
        self.create_axon()

        self.title_label = label(
            pos=vector(3.0, 4.25, 0),
            text="Neuron: dendrite signals trigger axon pulses",
            height=13,
            color=vector(0.25, 0.32, 0.42),
            box=False,
            opacity=0,
        )
        self.status_label = label(
            pos=vector(3.0, 3.72, 0),
            text="",
            height=10,
            color=vector(0.23, 0.28, 0.35),
            box=False,
            opacity=0,
        )

        scene.append_to_caption("\n")
        scene.append_to_caption("Keyboard: SPACE pause | A toggle AI | R reset | S stimulate | W wave | P pulse | M mark | X spill | O override AI | C next AI mode | 1-8 set AI mode\n")
        scene.append_to_caption("Manual probe: I/K/J/L/U/D move AI probe while override is active. Mouse can orbit/zoom the camera.\n\n")

    def add_segment(self, start, end, radius, parent_index, depth):
        seg = {
            "start": start,
            "end": end,
            "radius": radius,
            "parent": parent_index,
            "children": [],
            "depth": depth,
            "glow": 0.0,
        }
        axis = end - start
        obj = cylinder(
            pos=start,
            axis=axis,
            radius=radius,
            color=mix(DENDRITE_GREEN, vector(0.75, 0.94, 0.74), 0.12 * depth),
            opacity=0.84,
            shininess=0.7,
        )
        seg["obj"] = obj
        idx = len(self.segments)
        self.segments.append(seg)
        if parent_index is not None:
            self.segments[parent_index]["children"].append(idx)
        return idx

    def create_dendrites(self):
        root_dirs = [
            vector(-1.0, 0.58, 0.18),
            vector(-1.0, -0.55, 0.36),
            vector(-0.95, 0.10, -0.72),
            vector(-0.62, 0.84, -0.20),
            vector(-0.88, -0.18, -0.62),
            vector(-0.76, 0.28, 0.78),
        ]

        def grow(parent_idx, start, direction, depth, length, radius):
            direction = safe_norm(direction)
            wiggle = random_unit() * random.uniform(0.05, 0.22)
            end = start + safe_norm(direction + wiggle) * length
            idx = self.add_segment(start, end, radius, parent_idx, depth)

            if depth <= 0:
                self.add_synapse(idx)
                return

            branch_count = 2 if depth >= 2 else random.choice([1, 2])
            for _ in range(branch_count):
                perturb = random_unit() * random.uniform(0.38, 0.78)
                outward_bias = vector(-0.16, random.uniform(-0.05, 0.12), random.uniform(-0.08, 0.08))
                new_dir = safe_norm(direction * random.uniform(0.65, 0.9) + perturb + outward_bias)
                new_len = length * random.uniform(0.63, 0.82)
                new_rad = radius * random.uniform(0.62, 0.76)
                grow(idx, end, new_dir, depth - 1, new_len, new_rad)

        for d in root_dirs:
            d = safe_norm(d)
            start = d * self.soma_radius * 0.96
            grow(None, start, d, 3, random.uniform(1.55, 2.15), 0.105)

    def add_synapse(self, terminal_segment_index):
        seg = self.segments[terminal_segment_index]
        path = [seg["end"]]
        cursor = terminal_segment_index
        while cursor is not None:
            s = self.segments[cursor]
            path.append(s["start"])
            cursor = s["parent"]
        path.append(vector(0, 0, 0))

        syn_obj = sphere(
            pos=seg["end"],
            radius=0.18,
            color=SYNAPSE_COLOR,
            opacity=0.92,
            emissive=False,
            shininess=0.85,
        )
        halo = sphere(
            pos=seg["end"],
            radius=0.27,
            color=SYNAPSE_COLOR,
            opacity=0.10,
            emissive=True,
        )
        self.synapses.append({
            "obj": syn_obj,
            "halo": halo,
            "path": path,
            "terminal_segment": terminal_segment_index,
            "cooldown": 0.0,
            "signal_glow": 0.0,
            "last_fire": -999.0,
            "ai_mark": 0.0,
        })

    def create_axon(self):
        self.axon_path = []
        start = vector(self.soma_radius * 0.95, 0, 0)
        self.axon_path.append(start)
        for i in range(1, 23):
            x = self.soma_radius + i * 0.68
            y = 0.28 * math.sin(i * 0.55)
            z = 0.22 * math.sin(i * 0.37 + 0.6)
            self.axon_path.append(vector(x, y, z))

        self.axon_segments = []
        for i in range(len(self.axon_path) - 1):
            a = self.axon_path[i]
            b = self.axon_path[i + 1]
            c = cylinder(
                pos=a,
                axis=b - a,
                radius=0.155,
                color=AXON_COLOR,
                opacity=0.84,
                shininess=0.72,
            )
            self.axon_segments.append(c)

        self.axon_hillock = cone(
            pos=vector(0.72, 0, 0),
            axis=vector(0.92, 0, 0),
            radius=0.44,
            color=mix(SOMA_COLOR, AXON_COLOR, 0.38),
            opacity=0.78,
        )

        self.axon_terminal_bulbs = []
        tip = self.axon_path[-1]
        terminal_offsets = [vector(0.35, 0.28, 0.18), vector(0.45, -0.12, -0.32), vector(0.38, -0.35, 0.18)]
        for off in terminal_offsets:
            cyl = cylinder(
                pos=tip,
                axis=off,
                radius=0.07,
                color=AXON_COLOR,
                opacity=0.72,
            )
            bulb = sphere(
                pos=tip + off,
                radius=0.18,
                color=vector(0.68, 0.82, 1.0),
                opacity=0.86,
                shininess=0.8,
            )
            self.axon_terminal_bulbs.append((cyl, bulb))

    def stimulate_synapse(self, index=None, burst=1, color_value=SIGNAL_COLOR, source="manual"):
        if not self.synapses:
            return
        if index is None:
            index = random.randrange(len(self.synapses))
        index %= len(self.synapses)
        syn = self.synapses[index]

        for _ in range(burst):
            if len(self.particles) < 180:
                self.particles.append(SignalParticle(self, index, color_value=color_value))

        syn["cooldown"] = max(syn["cooldown"], 0.72)
        syn["signal_glow"] = 1.0
        syn["last_fire"] = self.t
        self.last_activity_time = self.t

    def stimulate_wave(self, count=None):
        if count is None:
            count = min(8, len(self.synapses))
        if not self.synapses:
            return
        start = random.randrange(len(self.synapses))
        step = random.choice([1, 2, 3, 5])
        for i in range(count):
            idx = (start + i * step) % len(self.synapses)
            self.stimulate_synapse(idx, burst=1, color_value=mix(SIGNAL_COLOR, AI_CYAN, i / max(1, count - 1)), source="wave")

    def receive_dendrite_signal(self, synapse_index):
        self.soma_charge += 1
        self.soma_flash = 1.0
        self.last_activity_time = self.t

        terminal = self.synapses[synapse_index]["terminal_segment"]
        cursor = terminal
        while cursor is not None:
            self.segments[cursor]["glow"] = max(self.segments[cursor]["glow"], 0.75)
            cursor = self.segments[cursor]["parent"]

        if self.soma_charge >= self.charge_threshold:
            self.soma_charge = 0
            self.trigger_axon_pulse()

    def trigger_axon_pulse(self):
        if len(self.pulses) < 12:
            self.pulses.append(AxonPulse(self))
            self.soma_flash = 1.0
            self.last_activity_time = self.t

    def add_fading_trail(self, pos, color_value, radius, life):
        if len(self.trails) < 420:
            self.trails.append(FadingTrail(pos, color_value, radius, life))

    def spill_at_synapse(self, index=None, amount=18, palette=None):
        if not self.synapses:
            return
        if index is None:
            index = random.randrange(len(self.synapses))
        syn = self.synapses[index]
        if palette is None:
            palette = [AI_CYAN, AI_PURPLE, SIGNAL_COLOR, SYNAPSE_COLOR]
        for _ in range(amount):
            if len(self.spills) < 350:
                self.spills.append(SpillParticle(syn["obj"].pos, random.choice(palette)))
        syn["signal_glow"] = 1.0
        self.last_activity_time = self.t

    def mark_branch(self, index=None, color_value=AI_CYAN, text=None):
        if not self.segments:
            return
        if index is None:
            index = random.randrange(len(self.segments))
        seg = self.segments[index % len(self.segments)]
        if len(self.markers) < 80:
            self.markers.append(AttachedMarker(seg, color_value, text=text))
        seg["glow"] = max(seg["glow"], 0.9)
        self.last_activity_time = self.t

    def detach_marker(self):
        if self.markers:
            random.choice(self.markers).detach_now()
            self.last_activity_time = self.t

    def wrap_axon(self, color_value=AI_GOLD):
        if len(self.wraps) < 10:
            self.wraps.append(AxonWrap(self, color_value))
            self.last_activity_time = self.t

    def reset_round(self, announce=True):
        for collection in [self.particles, self.pulses, self.trails, self.spills, self.markers, self.wraps]:
            for item in collection:
                for attr in ("obj", "halo", "ring", "curve", "label"):
                    if hasattr(item, attr):
                        o = getattr(item, attr)
                        if o:
                            o.visible = False
            collection.clear()

        self.soma_charge = 0
        self.soma_flash = 0.0
        self.axon_terminal_flash = 0.0
        self.round_index += 1
        self.last_activity_time = self.t

        for s in self.synapses:
            s["cooldown"] = 0
            s["signal_glow"] = 0
            s["ai_mark"] = 0
            s["obj"].color = SYNAPSE_COLOR
            s["halo"].opacity = 0.10

        for seg in self.segments:
            seg["glow"] = 0.0
            seg["obj"].color = DENDRITE_GREEN

        for c in self.axon_segments:
            c.color = AXON_COLOR

        for _, bulb in self.axon_terminal_bulbs:
            bulb.color = vector(0.68, 0.82, 1.0)
            bulb.radius = 0.18

        if announce:
            self.spill_at_synapse(random.randrange(len(self.synapses)), amount=12, palette=[AI_GREEN, AI_CYAN, AI_GOLD])

    def get_state(self):
        active_synapses = sum(1 for s in self.synapses if self.t - s["last_fire"] < 2.0)
        recently_marked = len(self.markers)
        moving = len(self.particles) + len(self.pulses)
        return {
            "time": self.t,
            "round": self.round_index,
            "particle_count": len(self.particles),
            "pulse_count": len(self.pulses),
            "trail_count": len(self.trails),
            "spill_count": len(self.spills),
            "marker_count": len(self.markers),
            "wrap_count": len(self.wraps),
            "soma_charge": self.soma_charge,
            "charge_threshold": self.charge_threshold,
            "active_synapses": active_synapses,
            "moving_count": moving,
            "synapse_count": len(self.synapses),
            "segment_count": len(self.segments),
            "time_since_activity": self.t - self.last_activity_time,
            "paused": self.paused,
        }

    def update_visual_state(self, dt):
        self.soma_flash = max(0, self.soma_flash - dt * 1.6)
        soma_pulse = self.soma_flash
        charge_glow = self.soma_charge / max(1, self.charge_threshold)
        self.soma.color = mix(SOMA_COLOR, SOMA_FLASH, max(soma_pulse, charge_glow * 0.45))
        self.soma.radius = self.soma_radius * (1 + 0.035 * soma_pulse * math.sin(self.t * 42))
        self.soma_nucleus.opacity = 0.35 + 0.16 * charge_glow
        self.soma_membrane_ring.rotate(angle=dt * (0.3 + 1.2 * charge_glow), axis=vector(0, 1, 0), origin=vector(0, 0, 0))

        self.axon_terminal_flash = max(0, self.axon_terminal_flash - dt * 1.2)
        for _, bulb in self.axon_terminal_bulbs:
            bulb.color = mix(vector(0.68, 0.82, 1.0), PULSE_COLOR, self.axon_terminal_flash)
            bulb.radius = 0.18 + 0.11 * self.axon_terminal_flash

        for syn in self.synapses:
            syn["cooldown"] = max(0, syn["cooldown"] - dt)
            syn["signal_glow"] = max(0, syn["signal_glow"] - dt * 1.65)
            glow = max(syn["cooldown"], syn["signal_glow"], syn["ai_mark"])
            syn["ai_mark"] = max(0, syn["ai_mark"] - dt * 0.25)
            syn["obj"].color = mix(SYNAPSE_COLOR, SIGNAL_COLOR, min(1, glow))
            syn["obj"].radius = 0.18 + 0.055 * glow
            syn["halo"].opacity = 0.10 + 0.28 * glow
            syn["halo"].radius = 0.27 + 0.13 * glow

        for seg in self.segments:
            seg["glow"] = max(0, seg["glow"] - dt * 1.3)
            seg["obj"].color = mix(DENDRITE_GREEN, SIGNAL_COLOR, min(1, seg["glow"]))
            seg["obj"].opacity = 0.80 + 0.12 * min(1, seg["glow"])

    def update_status_label(self):
        ai_text = "AI: none"
        if self.ai:
            ai_text = f"AI: {'ON' if self.ai.enabled else 'OFF'} | mode {self.ai.mode}"
            if self.ai.human_override_active():
                ai_text += " | HUMAN OVERRIDE"
        state = self.get_state()
        self.status_label.text = (
            f"Round {state['round']} | charge {state['soma_charge']}/{state['charge_threshold']} | "
            f"signals {state['particle_count']} | pulses {state['pulse_count']} | marks {state['marker_count']} | {ai_text}"
        )

    def update(self, dt):
        if self.paused:
            self.update_status_label()
            return

        self.t += dt

        if self.ai:
            self.ai.update(dt)

        self.particles[:] = [p for p in self.particles if p.update(dt)]
        self.pulses[:] = [p for p in self.pulses if p.update(dt)]
        self.trails[:] = [tr for tr in self.trails if tr.update(dt)]
        self.spills[:] = [sp for sp in self.spills if sp.update(dt)]
        self.markers[:] = [m for m in self.markers if m.update(dt)]
        self.wraps[:] = [w for w in self.wraps if w.update(dt)]

        self.update_visual_state(dt)
        self.update_status_label()


class AIController:
    MODES = [
        "OBSERVE",
        "CAREFUL",
        "CURIOUS",
        "RITUAL",
        "CHAOTIC",
        "ARTISTIC",
        "CONSTRUCTIVE",
        "RESETTING",
    ]

    MODE_COLORS = {
        "OBSERVE": AI_BLUE,
        "CAREFUL": AI_GREEN,
        "CURIOUS": AI_CYAN,
        "RITUAL": AI_GOLD,
        "CHAOTIC": AI_RED,
        "ARTISTIC": AI_PURPLE,
        "CONSTRUCTIVE": vector(0.24, 0.82, 0.42),
        "RESETTING": vector(1.0, 0.55, 0.2),
    }

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "OBSERVE"
        self.mode_age = 0.0
        self.next_mode_switch = 5.0
        self.action_timer = 0.0
        self.wave_cursor = 0
        self.history = deque(maxlen=4)
        self.override_until = -1.0

        self.last_signature = None
        self.signature_timer = 0.0
        self.stagnation_seconds = 0.0
        self.completion_seconds = 0.0
        self.round_loop_delay = 0.0

        self.probe_target = vector(0, 0, 0)
        self.probe_phase = random.uniform(0, 2 * math.pi)
        self.attached_synapse = None
        self.manual_probe_velocity = vector(0, 0, 0)

        self.probe = sphere(
            pos=vector(0, 2.4, 2.3),
            radius=0.18,
            color=AI_BLUE,
            emissive=True,
            shininess=1.0,
            make_trail=True,
            retain=38,
            trail_radius=0.025,
            trail_color=AI_BLUE,
        )
        self.probe_ring = ring(
            pos=self.probe.pos,
            axis=vector(0, 1, 0),
            radius=0.34,
            thickness=0.015,
            color=AI_BLUE,
            opacity=0.65,
            emissive=True,
        )
        self.mode_label = label(
            pos=self.probe.pos + vector(0, 0.45, 0),
            text="AI",
            height=9,
            color=AI_BLUE,
            box=False,
            opacity=0,
        )

    def human_override_active(self):
        return self.sim.t < self.override_until

    def set_override(self, seconds=8.0):
        self.override_until = max(self.override_until, self.sim.t + seconds)
        self.attached_synapse = None

    def set_mode(self, mode):
        if mode in self.MODES:
            self.history.append(self.mode)
            self.mode = mode
            self.mode_age = 0.0
            self.next_mode_switch = self.sim.t + random.uniform(7.5, 14.0)

    def next_mode(self):
        current = self.MODES.index(self.mode)
        for i in range(1, len(self.MODES)):
            candidate = self.MODES[(current + i) % len(self.MODES)]
            if candidate != "RESETTING":
                self.set_mode(candidate)
                break

    def read_state(self):
        return self.sim.get_state()

    def detect_stagnation_and_completion(self, dt):
        s = self.read_state()
        signature = (
            s["particle_count"],
            s["pulse_count"],
            s["soma_charge"],
            s["active_synapses"],
            s["marker_count"] // 3,
            s["wrap_count"],
        )

        self.signature_timer += dt
        if self.signature_timer >= 0.65:
            self.signature_timer = 0.0
            if signature == self.last_signature:
                self.stagnation_seconds += 0.65
            else:
                self.stagnation_seconds = max(0, self.stagnation_seconds - 0.9)
            self.last_signature = signature

        if s["moving_count"] == 0 and s["time_since_activity"] > 5.8:
            self.completion_seconds += dt
        else:
            self.completion_seconds = max(0, self.completion_seconds - dt * 2)

        return self.stagnation_seconds, self.completion_seconds

    def choose_new_mode(self, state):
        if self.completion_seconds > 4.5 or self.stagnation_seconds > 8.0:
            return "RESETTING"

        candidates = ["OBSERVE", "CAREFUL", "CURIOUS", "RITUAL", "CHAOTIC", "ARTISTIC", "CONSTRUCTIVE"]

        if state["particle_count"] == 0 and state["pulse_count"] == 0:
            weighted = ["CURIOUS", "RITUAL", "CONSTRUCTIVE", "ARTISTIC", "CAREFUL"]
        elif state["particle_count"] > 35:
            weighted = ["OBSERVE", "CAREFUL", "ARTISTIC"]
        elif state["soma_charge"] == state["charge_threshold"] - 1:
            weighted = ["CAREFUL", "RITUAL", "CURIOUS"]
        elif state["marker_count"] > 28:
            weighted = ["CHAOTIC", "OBSERVE", "CAREFUL"]
        else:
            weighted = candidates[:]

        for old in self.history:
            if old in weighted and len(weighted) > 2:
                weighted.remove(old)

        return random.choice(weighted)

    def move_probe(self, dt):
        color_value = self.MODE_COLORS.get(self.mode, AI_BLUE)
        self.probe.color = color_value
        self.probe.trail_color = color_value
        self.probe_ring.color = color_value
        self.mode_label.color = color_value

        if self.human_override_active() and mag(self.manual_probe_velocity) > 0.001:
            self.probe.pos += self.manual_probe_velocity * dt * 2.6
        else:
            self.probe_phase += dt * (0.65 if self.mode != "CHAOTIC" else 1.85)

            if self.attached_synapse is not None and self.sim.synapses:
                syn = self.sim.synapses[self.attached_synapse % len(self.sim.synapses)]
                self.probe_target = syn["obj"].pos + vector(0, 0.36, 0)
            elif self.mode == "OBSERVE":
                self.probe_target = vector(
                    0.5 + 2.4 * math.cos(self.probe_phase * 0.75),
                    2.0 + 0.28 * math.sin(self.probe_phase * 1.4),
                    2.4 * math.sin(self.probe_phase * 0.75),
                )
            elif self.mode == "RITUAL":
                self.probe_target = vector(
                    0.0 + 2.0 * math.cos(self.probe_phase),
                    0.7 + 1.2 * math.sin(self.probe_phase * 2.0),
                    2.0 * math.sin(self.probe_phase),
                )
            elif self.mode == "CHAOTIC":
                if random.random() < dt * 1.4:
                    self.probe_target = random_unit() * random.uniform(1.5, 5.0) + vector(1.5, 0, 0)
            elif self.mode == "ARTISTIC":
                d = (self.probe_phase * 0.9) % (2 * math.pi)
                self.probe_target = vector(
                    4.5 + 3.8 * math.cos(d),
                    1.3 + 0.8 * math.sin(d * 3),
                    2.1 * math.sin(d),
                )
            elif self.mode == "CONSTRUCTIVE":
                self.probe_target = vector(-2.0, 1.2 + 0.6 * math.sin(self.probe_phase * 2), 1.8 * math.cos(self.probe_phase))
            else:
                self.probe_target = vector(-1.2, 1.6 + 0.4 * math.sin(self.probe_phase * 1.7), 1.6 * math.cos(self.probe_phase))

            self.probe.pos += (self.probe_target - self.probe.pos) * clamp(dt * 2.2, 0, 1)

        self.probe_ring.pos = self.probe.pos
        self.probe_ring.axis = vector(math.sin(self.sim.t * 1.2), 1.0, math.cos(self.sim.t * 1.2))
        self.probe_ring.rotate(angle=dt * 4.0, axis=self.probe_ring.axis, origin=self.probe_ring.pos)
        self.mode_label.pos = self.probe.pos + vector(0, 0.45, 0)
        self.mode_label.text = self.mode

    def least_recent_synapse(self):
        if not self.sim.synapses:
            return 0
        return min(range(len(self.sim.synapses)), key=lambda i: self.sim.synapses[i]["last_fire"])

    def choose_visible_synapse(self):
        if not self.sim.synapses:
            return 0
        if self.mode in ["CAREFUL", "CONSTRUCTIVE"]:
            return self.least_recent_synapse()
        if self.mode == "RITUAL":
            self.wave_cursor = (self.wave_cursor + 1) % len(self.sim.synapses)
            return self.wave_cursor
        return random.randrange(len(self.sim.synapses))

    def act_observe(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(2.0, 3.8)
            if random.random() < 0.45:
                self.sim.mark_branch(color_value=mix(AI_BLUE, AI_CYAN, random.random()), text="watch")
            if state["moving_count"] == 0 and random.random() < 0.5:
                self.sim.stimulate_synapse(self.choose_visible_synapse(), color_value=mix(SIGNAL_COLOR, AI_BLUE, 0.25), source="ai_observe")

    def act_careful(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(1.1, 1.9)
            idx = self.least_recent_synapse()
            self.attached_synapse = idx
            self.sim.synapses[idx]["ai_mark"] = 1.0
            self.sim.stimulate_synapse(idx, burst=1, color_value=mix(SIGNAL_COLOR, AI_GREEN, 0.22), source="ai_careful")
            if random.random() < 0.25:
                self.sim.mark_branch(self.sim.synapses[idx]["terminal_segment"], color_value=AI_GREEN, text="safe")

    def act_curious(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.65, 1.35)
            idx = self.choose_visible_synapse()
            self.attached_synapse = idx if random.random() < 0.45 else None
            self.sim.synapses[idx]["ai_mark"] = 1.0
            self.sim.stimulate_synapse(idx, burst=random.choice([1, 1, 2]), color_value=mix(SIGNAL_COLOR, AI_CYAN, 0.35), source="ai_curious")
            if random.random() < 0.25:
                self.sim.spill_at_synapse(idx, amount=5, palette=[AI_CYAN, SIGNAL_COLOR, SYNAPSE_COLOR])

    def act_ritual(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = 0.42
            idx = self.choose_visible_synapse()
            self.attached_synapse = idx
            self.sim.stimulate_synapse(idx, burst=1, color_value=mix(SIGNAL_COLOR, AI_GOLD, 0.45), source="ai_ritual")
            if self.wave_cursor % 5 == 0:
                self.sim.wrap_axon(color_value=AI_GOLD)
            if self.wave_cursor % 4 == 0:
                self.sim.mark_branch(self.sim.synapses[idx]["terminal_segment"], color_value=AI_GOLD, text="loop")

    def act_chaotic(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.25, 0.8)
            actions = random.randint(2, 5)
            for _ in range(actions):
                idx = random.randrange(len(self.sim.synapses))
                self.sim.stimulate_synapse(idx, burst=random.choice([1, 2, 3]), color_value=mix(SIGNAL_COLOR, AI_RED, 0.4), source="ai_chaotic")
                if random.random() < 0.28:
                    self.sim.spill_at_synapse(idx, amount=random.randint(5, 12), palette=[AI_RED, AI_PURPLE, AI_GOLD, SIGNAL_COLOR])
            if random.random() < 0.24:
                self.sim.trigger_axon_pulse()
            if random.random() < 0.36:
                self.sim.detach_marker()

    def act_artistic(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.75, 1.4)
            color_value = random.choice([AI_PURPLE, AI_CYAN, AI_GOLD, SYNAPSE_COLOR, vector(0.45, 0.95, 0.72)])
            if random.random() < 0.55:
                self.sim.mark_branch(color_value=color_value, text=random.choice(["mark", "arc", "trace", "bloom"]))
            if random.random() < 0.32:
                self.sim.wrap_axon(color_value=color_value)
            if random.random() < 0.35:
                idx = self.choose_visible_synapse()
                self.sim.spill_at_synapse(idx, amount=8, palette=[color_value, AI_CYAN, AI_PURPLE])
            if state["moving_count"] < 18 and random.random() < 0.45:
                self.sim.stimulate_synapse(self.choose_visible_synapse(), color_value=mix(SIGNAL_COLOR, color_value, 0.35), source="ai_artistic")

    def act_constructive(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.9, 1.65)
            idx = self.least_recent_synapse()
            self.attached_synapse = idx
            terminal = self.sim.synapses[idx]["terminal_segment"]
            self.sim.mark_branch(terminal, color_value=AI_GREEN, text="build")
            self.sim.stimulate_synapse(idx, burst=1, color_value=mix(SIGNAL_COLOR, AI_GREEN, 0.33), source="ai_constructive")
            if state["wrap_count"] < 3 and random.random() < 0.2:
                self.sim.wrap_axon(color_value=AI_GREEN)

    def act_resetting(self, dt, state):
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.action_timer = 2.2
            self.sim.reset_round(announce=True)
            self.stagnation_seconds = 0
            self.completion_seconds = 0
            self.round_loop_delay = random.uniform(0.8, 2.0)
            self.set_mode(random.choice(["CURIOUS", "RITUAL", "CONSTRUCTIVE", "ARTISTIC"]))

    def update(self, dt):
        self.move_probe(dt)

        if not self.enabled:
            return

        state = self.read_state()
        self.detect_stagnation_and_completion(dt)

        if self.human_override_active():
            return

        self.mode_age += dt

        if self.completion_seconds > 4.5 or self.stagnation_seconds > 8.0:
            if self.mode != "RESETTING":
                self.set_mode("RESETTING")
                self.action_timer = 0.0

        if self.sim.t >= self.next_mode_switch and self.mode != "RESETTING":
            new_mode = self.choose_new_mode(state)
            self.set_mode(new_mode)

        if self.round_loop_delay > 0:
            self.round_loop_delay -= dt
            return

        if self.mode == "OBSERVE":
            self.act_observe(dt, state)
        elif self.mode == "CAREFUL":
            self.act_careful(dt, state)
        elif self.mode == "CURIOUS":
            self.act_curious(dt, state)
        elif self.mode == "RITUAL":
            self.act_ritual(dt, state)
        elif self.mode == "CHAOTIC":
            self.act_chaotic(dt, state)
        elif self.mode == "ARTISTIC":
            self.act_artistic(dt, state)
        elif self.mode == "CONSTRUCTIVE":
            self.act_constructive(dt, state)
        elif self.mode == "RESETTING":
            self.act_resetting(dt, state)


sim = NeuronSimulation()
ai = AIController(sim)
sim.ai = ai


def keydown(evt):
    k = evt.key
    low = k.lower() if isinstance(k, str) else k

    if k == " ":
        sim.paused = not sim.paused

    elif low == "a":
        ai.enabled = not ai.enabled

    elif low == "r":
        sim.reset_round(announce=True)
        ai.set_override(2.0)

    elif low == "s":
        sim.stimulate_synapse(None, burst=1, source="manual")
        ai.set_override(2.2)

    elif low == "w":
        sim.stimulate_wave()
        ai.set_override(2.5)

    elif low == "p":
        sim.trigger_axon_pulse()
        ai.set_override(2.0)

    elif low == "m":
        sim.mark_branch(color_value=random.choice([AI_CYAN, AI_PURPLE, AI_GOLD, AI_GREEN]), text="human")
        ai.set_override(2.0)

    elif low == "x":
        sim.spill_at_synapse(None, amount=20)
        ai.set_override(2.0)

    elif low == "o":
        ai.set_override(8.0)

    elif low == "c":
        ai.next_mode()
        ai.set_override(1.5)

    elif low in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        idx = int(low) - 1
        if 0 <= idx < len(AIController.MODES):
            ai.set_mode(AIController.MODES[idx])
            ai.set_override(1.2)

    elif low in ["i", "k", "j", "l", "u", "d"]:
        ai.set_override(5.0)
        v = vector(0, 0, 0)
        if low == "i":
            v += vector(0, 1, 0)
        elif low == "k":
            v += vector(0, -1, 0)
        elif low == "j":
            v += vector(0, 0, 1)
        elif low == "l":
            v += vector(0, 0, -1)
        elif low == "u":
            v += vector(-1, 0, 0)
        elif low == "d":
            v += vector(1, 0, 0)
        ai.manual_probe_velocity = v


def keyup(evt):
    k = evt.key
    low = k.lower() if isinstance(k, str) else k
    if low in ["i", "k", "j", "l", "u", "d"]:
        ai.manual_probe_velocity = vector(0, 0, 0)


scene.bind("keydown", keydown)
scene.bind("keyup", keyup)

sim.stimulate_wave(count=5)
sim.wrap_axon(color_value=AI_CYAN)

dt = 1 / 60
while True:
    rate(60)
    sim.update(dt)
