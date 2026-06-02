from vpython import *
import random
import math

# 3D Neuron Network with Firing Signals, Growth, Synapses, Labels, Activity Meter,
# pathway brightening, unused-branch fading, Human Controls, and an Expressive AI Controller.
#
# Controls:
#   SPACE pause/resume
#   A     toggle AI
#   R     reset round
#   N     force AI to choose a new behavior mode
#   TAB   select next neuron
#   1-9   select neuron
#   Arrow keys / W/S  move selected neuron
#   Q/E   rotate selected neuron's arbor
#   G     grow a branch on selected neuron
#   P     fire selected neuron / spawn signals
#   C     attach closest branch tips
#   D     detach a random synapse
#   X     prune a leaf branch on selected neuron
#   M     mark selected neuron
#   V     spill particles from selected neuron
#   B     wrap halo particles around selected neuron
#   O     orbit all neurons around center
#   I     dip selected neuron downward/upward

scene.title = "3D Neuron Network with Strengthening Pathways + Fading Branches"
scene.background = vector(0.94, 0.97, 1.0)
scene.width = 1280
scene.height = 760
scene.forward = vector(-0.55, -0.28, -0.78)
scene.up = vector(0, 1, 0)
scene.range = 10.5
scene.caption = (
    "\nLight 3D neural network simulation. "
    "Toggle AI with A, pause with SPACE, reset with R. "
    "Repeated pulses brighten pathways; quiet branches slowly fade. "
    "Use TAB/1-9 to select neurons; G/P/C/D/X/M/V/B/O manipulate the system.\n"
)

WORLD_RADIUS = 7.2
MAX_NEURONS = 7
INITIAL_NEURONS = 6
MAX_BRANCHES = 88
MAX_SYNAPSES = 28
AUTO_RESET_AFTER_STAGNATION = True

# Pathway memory controls. Synapses and branch segments keep a visual memory of
# recent traffic: repeated pulses brighten/thicken active pathways, while quiet
# branches slowly fade toward pale, transparent threads.
PATHWAY_REINFORCE_AMOUNT = 0.16
PATHWAY_DECAY_RATE = 0.055
BRANCH_USE_DECAY_RATE = 0.040
BRANCH_REINFORCE_AMOUNT = 0.18



def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_vec(a, b, t):
    return vector(lerp(a.x, b.x, t), lerp(a.y, b.y, t), lerp(a.z, b.z, t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return vector(fallback.x, fallback.y, fallback.z)
    return norm(v)


def random_unit():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) > 0.05:
            return norm(v)


def random_pastel():
    return vector(
        random.uniform(0.38, 0.82),
        random.uniform(0.50, 0.92),
        random.uniform(0.72, 1.00),
    )


def hide_obj(o):
    """Hide a VPython object and clear any retained trail geometry.

    VPython trails created with make_trail=True are not removed just by setting
    the parent object invisible. reset_round() hides old signal/free-particle
    spheres, but their trails can remain in the scene unless clear_trail() is
    called first.
    """
    if o is None:
        return
    try:
        if hasattr(o, "clear_trail"):
            o.clear_trail()
    except Exception:
        pass
    try:
        o.visible = False
    except Exception:
        pass


class BranchSegment:
    def __init__(self, neuron, parent=None, kind="dendrite", direction=None, max_len=None):
        self.neuron = neuron
        self.parent = parent
        self.kind = kind
        self.children = []
        self.alive = True
        self.age = 0.0
        self.phase = random.uniform(0, 2 * math.pi)

        if direction is None:
            if parent is None:
                direction = random_unit()
            else:
                direction = safe_norm(parent.direction + 0.65 * random_unit())
        self.direction = safe_norm(direction)

        if kind == "axon":
            self.max_len = max_len if max_len is not None else random.uniform(1.1, 2.2)
            self.radius = random.uniform(0.025, 0.045)
            self.base_color = vector(1.0, 0.63, 0.20)
            self.tip_color = vector(1.0, 0.82, 0.30)
            self.grow_rate = random.uniform(0.30, 0.62)
        else:
            self.max_len = max_len if max_len is not None else random.uniform(0.65, 1.55)
            self.radius = random.uniform(0.035, 0.065)
            self.base_color = vector(0.34, 0.70, 1.0)
            self.tip_color = vector(0.55, 0.95, 1.0)
            self.grow_rate = random.uniform(0.22, 0.50)

        self.length = random.uniform(0.05, 0.18)
        self.glow = random.uniform(0.0, 0.3)
        self.use_level = random.uniform(0.32, 0.58)
        self.unused_time = 0.0

        b = self.base_pos()
        axis = self.current_tip() - b
        self.cyl = cylinder(
            pos=b,
            axis=axis,
            radius=self.radius,
            color=self.base_color,
            opacity=0.78,
            shininess=0.35,
        )
        self.tip_sphere = sphere(
            pos=self.current_tip(),
            radius=self.radius * 2.35,
            color=self.tip_color,
            opacity=0.88,
            emissive=True,
        )

        if parent is not None:
            parent.children.append(self)

    def base_pos(self):
        if self.parent is None or not self.parent.alive:
            return self.neuron.pos
        return self.parent.current_tip()

    def curled_direction(self):
        sway = 0.055 * vector(
            math.sin(self.neuron.sim_time * 0.75 + self.phase),
            math.sin(self.neuron.sim_time * 0.52 + self.phase * 1.7),
            math.cos(self.neuron.sim_time * 0.61 + self.phase),
        )
        return safe_norm(self.direction + sway, self.direction)

    def current_tip(self):
        return self.base_pos() + self.curled_direction() * self.length

    def update(self, dt):
        if not self.alive:
            return

        self.age += dt
        if self.length < self.max_len:
            self.length = min(self.max_len, self.length + self.grow_rate * dt)

        self.glow *= (0.91 ** (dt * 60.0))
        self.use_level = clamp(self.use_level - BRANCH_USE_DECAY_RATE * dt, 0.0, 1.0)
        if self.use_level < 0.18:
            self.unused_time += dt
        else:
            self.unused_time = max(0.0, self.unused_time - dt * 1.8)

        activity_mix = clamp(self.neuron.activity * 0.55 + self.glow + self.use_level * 0.35)
        active_color = lerp_vec(self.base_color, vector(1.0, 0.96, 0.30), activity_mix)
        faded_color = vector(0.66, 0.75, 0.82)
        use_mix = clamp(0.12 + 0.88 * self.use_level)
        c = lerp_vec(faded_color, active_color, use_mix)

        b = self.base_pos()
        t = self.current_tip()
        self.cyl.pos = b
        self.cyl.axis = t - b
        self.cyl.radius = self.radius * (0.62 + 0.48 * use_mix + 0.44 * activity_mix)
        self.cyl.color = c
        self.cyl.opacity = 0.16 + 0.46 * use_mix + 0.32 * activity_mix

        self.tip_sphere.pos = t
        self.tip_sphere.color = lerp_vec(vector(0.70, 0.78, 0.84), lerp_vec(self.tip_color, vector(1.0, 0.98, 0.25), activity_mix), use_mix)
        self.tip_sphere.radius = self.radius * (1.25 + 1.05 * use_mix + 1.20 * activity_mix)
        self.tip_sphere.opacity = 0.20 + 0.42 * use_mix + 0.30 * activity_mix

    def rotate(self, angle, axis):
        self.direction = self.direction.rotate(angle=angle, axis=axis)

    def reinforce(self, amount=BRANCH_REINFORCE_AMOUNT):
        self.use_level = clamp(self.use_level + amount, 0.0, 1.0)
        self.unused_time = 0.0
        self.glow = clamp(self.glow + amount * 0.75, 0.0, 1.0)

    def pulse(self, amount=1.0):
        self.glow = clamp(self.glow + amount, 0, 1)
        self.reinforce(amount * 0.22)

    def hide(self):
        self.alive = False
        hide_obj(self.cyl)
        hide_obj(self.tip_sphere)

    def is_leaf(self):
        return self.alive and len([c for c in self.children if c.alive]) == 0


class Neuron:
    def __init__(self, sim, index, pos, base_color=None):
        self.sim = sim
        self.index = index
        self.name = f"N{index + 1}"
        self.pos = vector(pos.x, pos.y, pos.z)
        self.vel = vector(0, 0, 0)
        self.base_color = base_color if base_color is not None else random_pastel()
        self.activity = random.uniform(0.05, 0.25)
        self.energy = random.uniform(0.4, 0.8)
        self.sim_time = 0.0
        self.selected = False
        self.branches = []
        self.marks = []

        self.soma = sphere(
            pos=self.pos,
            radius=0.36,
            color=self.base_color,
            opacity=0.88,
            shininess=0.65,
        )
        self.aura = sphere(
            pos=self.pos,
            radius=0.52,
            color=lerp_vec(self.base_color, vector(1, 1, 1), 0.45),
            opacity=0.13,
            emissive=True,
        )
        self.label = label(
            pos=self.pos + vector(0, 0.72, 0),
            text=self.name,
            xoffset=0,
            yoffset=0,
            height=13,
            border=7,
            font="sans",
            color=vector(0.1, 0.18, 0.25),
            background=vector(0.92, 0.96, 1.0),
            opacity=0.48,
            box=True,
        )
        self.selection_ring = ring(
            pos=self.pos,
            axis=vector(0, 1, 0),
            radius=0.58,
            thickness=0.018,
            color=vector(1.0, 0.62, 0.15),
            opacity=0.0,
        )

        for _ in range(random.randint(4, 6)):
            self.grow_branch(parent=None, kind=random.choice(["dendrite", "dendrite", "axon"]))

    def leaf_segments(self):
        return [b for b in self.branches if b.is_leaf()]

    def live_branches(self):
        return [b for b in self.branches if b.alive]

    def grow_branch(self, parent=None, kind=None):
        if len(self.live_branches()) >= 28:
            return None
        if kind is None:
            kind = random.choice(["dendrite", "dendrite", "dendrite", "axon"])

        if parent is None:
            leaves = self.leaf_segments()
            if leaves and random.random() < 0.68:
                parent = random.choice(leaves)

        if parent is None:
            direction = safe_norm(random_unit() + 0.25 * safe_norm(self.pos, random_unit()))
        else:
            branch_angle = random.uniform(-0.95, 0.95)
            axis = random_unit()
            direction = safe_norm(parent.curled_direction().rotate(angle=branch_angle, axis=axis) + 0.28 * random_unit())

        seg = BranchSegment(self, parent=parent, kind=kind, direction=direction)
        self.branches.append(seg)
        self.energy = clamp(self.energy - 0.025, 0, 1)
        return seg

    def prune_leaf(self):
        leaves = self.leaf_segments()
        if not leaves:
            return None
        seg = random.choice(leaves)
        self.sim.detach_synapses_involving_segment(seg)
        if seg.parent is not None and seg in seg.parent.children:
            seg.parent.children.remove(seg)
        seg.hide()
        self.energy = clamp(self.energy + 0.05, 0, 1)
        return seg

    def rotate_arbor(self, angle=0.25, axis=vector(0, 1, 0)):
        for b in self.live_branches():
            b.rotate(angle, axis)

    def fire(self, amount=0.75):
        self.activity = clamp(self.activity + amount, 0, 1)
        for b in random.sample(self.live_branches(), min(len(self.live_branches()), random.randint(2, 7))):
            b.pulse(random.uniform(0.35, 1.0))
        self.sim.spawn_signals_from_neuron(self, burst=True)

    def receive_signal(self, amount=0.16):
        self.activity = clamp(self.activity + amount, 0, 1)
        self.energy = clamp(self.energy + amount * 0.18, 0, 1)
        if random.random() < 0.38:
            leaves = self.leaf_segments()
            if leaves:
                random.choice(leaves).pulse(amount * 2.5)

    def mark(self, color=None):
        if color is None:
            color = vector(random.uniform(0.7, 1.0), random.uniform(0.25, 0.8), random.uniform(0.2, 0.9))
        r = ring(
            pos=self.pos + vector(0, 0.06 * len(self.marks), 0),
            axis=random_unit(),
            radius=0.70 + 0.035 * len(self.marks),
            thickness=0.016,
            color=color,
            opacity=0.58,
            emissive=True,
        )
        self.marks.append(r)
        if len(self.marks) > 8:
            old = self.marks.pop(0)
            hide_obj(old)

    def update(self, dt):
        self.sim_time += dt
        self.vel *= (0.985 ** (dt * 60.0))
        self.pos += self.vel * dt

        if mag(self.pos) > WORLD_RADIUS:
            outward = norm(self.pos)
            self.pos = outward * WORLD_RADIUS
            self.vel -= 2.0 * dot(self.vel, outward) * outward
            self.vel *= 0.72

        self.activity *= (0.972 ** (dt * 60.0))
        self.energy = clamp(self.energy + 0.012 * dt, 0, 1)

        active_color = lerp_vec(self.base_color, vector(1.0, 0.93, 0.18), clamp(self.activity))
        self.soma.pos = self.pos
        self.soma.color = active_color
        self.soma.radius = 0.36 + 0.10 * clamp(self.activity)
        self.soma.opacity = 0.76 + 0.20 * clamp(self.activity)

        self.aura.pos = self.pos
        self.aura.radius = 0.54 + 0.42 * clamp(self.activity)
        self.aura.color = lerp_vec(lerp_vec(self.base_color, vector(1, 1, 1), 0.28), vector(1.0, 0.9, 0.1), clamp(self.activity))
        self.aura.opacity = 0.08 + 0.21 * clamp(self.activity)

        self.label.pos = self.pos + vector(0, 0.76, 0)
        self.label.text = f"{self.name}  A:{self.activity:.2f}"
        self.selection_ring.pos = self.pos
        self.selection_ring.opacity = 0.72 if self.selected else 0.0

        for i, m in enumerate(self.marks):
            m.pos = self.pos + vector(0, 0.07 * i, 0)
            m.axis = m.axis.rotate(angle=0.35 * dt * (1 + i * 0.2), axis=vector(0, 1, 0))

        for b in self.live_branches():
            b.update(dt)

    def hide(self):
        hide_obj(self.soma)
        hide_obj(self.aura)
        hide_obj(self.label)
        hide_obj(self.selection_ring)
        for m in self.marks:
            hide_obj(m)
        for b in self.branches:
            b.hide()


class Synapse:
    def __init__(self, sim, seg_a, seg_b):
        self.sim = sim
        self.seg_a = seg_a
        self.seg_b = seg_b
        self.neuron_a = seg_a.neuron
        self.neuron_b = seg_b.neuron
        self.alive = True
        self.age = 0.0
        self.strength = random.uniform(0.34, 0.94)
        self.pathway_strength = random.uniform(0.10, 0.28)
        self.repeated_pulse_memory = 0.0
        self.pulse_count = 0
        self.signal_timer = random.uniform(0.1, 1.2)
        self.detaching = False

        p1 = self.p1()
        p2 = self.p2()
        self.cyl = cylinder(
            pos=p1,
            axis=p2 - p1,
            radius=0.022 + 0.018 * self.strength,
            color=vector(0.68, 0.49, 1.0),
            opacity=0.28 + 0.24 * self.strength,
            shininess=0.25,
        )
        self.mid_glow = sphere(
            pos=(p1 + p2) / 2,
            radius=0.07,
            color=vector(0.88, 0.72, 1.0),
            opacity=0.34,
            emissive=True,
        )

    def p1(self):
        return self.seg_a.current_tip()

    def p2(self):
        return self.seg_b.current_tip()

    def involves_segment(self, seg):
        return self.seg_a is seg or self.seg_b is seg

    def other_neuron(self, neuron):
        if neuron is self.neuron_a:
            return self.neuron_b
        if neuron is self.neuron_b:
            return self.neuron_a
        return None

    def update(self, dt):
        if not self.alive:
            return
        if not self.seg_a.alive or not self.seg_b.alive:
            self.detach()
            return

        self.age += dt
        p1 = self.p1()
        p2 = self.p2()
        dist = mag(p2 - p1)

        if dist > 4.2 + self.strength and random.random() < 0.018:
            self.detach()
            return

        self.pathway_strength = clamp(self.pathway_strength - PATHWAY_DECAY_RATE * dt, 0.02, 1.0)
        self.repeated_pulse_memory = clamp(self.repeated_pulse_memory - PATHWAY_DECAY_RATE * 1.6 * dt, 0.0, 1.0)

        combined_activity = clamp((self.neuron_a.activity + self.neuron_b.activity) * 0.45)
        pathway_mix = clamp(self.pathway_strength + self.repeated_pulse_memory * 0.45 + combined_activity * 0.30)
        quiet_color = vector(0.55, 0.60, 0.70)
        base_path_color = lerp_vec(vector(0.58, 0.46, 1.0), vector(0.52, 0.82, 1.0), self.strength)
        hot_color = vector(1.0, 0.92, 0.22)
        c = lerp_vec(quiet_color, lerp_vec(base_path_color, hot_color, pathway_mix), clamp(0.22 + pathway_mix))

        self.cyl.pos = p1
        self.cyl.axis = p2 - p1
        self.cyl.radius = 0.012 + 0.018 * self.strength + 0.044 * pathway_mix
        self.cyl.color = c
        self.cyl.opacity = 0.14 + 0.14 * self.strength + 0.58 * pathway_mix

        self.mid_glow.pos = (p1 + p2) / 2
        self.mid_glow.color = lerp_vec(vector(0.68, 0.62, 0.90), hot_color, pathway_mix)
        self.mid_glow.radius = 0.040 + 0.045 * self.strength + 0.105 * pathway_mix
        self.mid_glow.opacity = 0.12 + 0.56 * pathway_mix

        self.signal_timer -= dt
        base_rate = 1.5 - self.strength
        if self.signal_timer <= 0:
            if random.random() < 0.22 + combined_activity * 0.75:
                source = self.neuron_a if self.neuron_a.activity >= self.neuron_b.activity else self.neuron_b
                self.sim.spawn_signal_on_synapse(self, source=source)
            self.signal_timer = random.uniform(0.22, base_rate + 0.75)

    def reinforce(self, amount=PATHWAY_REINFORCE_AMOUNT):
        self.pathway_strength = clamp(self.pathway_strength + amount, 0.0, 1.0)
        self.repeated_pulse_memory = clamp(self.repeated_pulse_memory + amount * 1.35, 0.0, 1.0)
        self.pulse_count += 1
        self.strength = clamp(self.strength + amount * 0.020, 0.10, 1.0)
        self.seg_a.reinforce(amount * 1.05)
        self.seg_b.reinforce(amount * 1.05)
        if self.seg_a.parent is not None:
            self.seg_a.parent.reinforce(amount * 0.42)
        if self.seg_b.parent is not None:
            self.seg_b.parent.reinforce(amount * 0.42)

    def detach(self):
        if not self.alive:
            return
        self.alive = False
        hide_obj(self.cyl)
        hide_obj(self.mid_glow)


class SignalParticle:
    def __init__(self, synapse, source=None):
        self.synapse = synapse
        self.alive = True
        self.speed = random.uniform(0.55, 1.15) * (0.75 + synapse.strength)
        self.t = 0.0
        if source is synapse.neuron_b:
            self.forward = False
            self.target = synapse.neuron_a
        else:
            self.forward = True
            self.target = synapse.neuron_b
        synapse.reinforce(PATHWAY_REINFORCE_AMOUNT)
        start = self.position()
        self.sphere = sphere(
            pos=start,
            radius=0.065 + 0.035 * synapse.strength,
            color=vector(1.0, 0.88, 0.20),
            opacity=0.92,
            emissive=True,
            make_trail=True,
            retain=12,
            trail_radius=0.012,
            trail_color=vector(1.0, 0.74, 0.16),
        )

    def position(self):
        if not self.synapse.alive:
            return vector(0, 0, 0)
        p1 = self.synapse.p1()
        p2 = self.synapse.p2()
        if not self.forward:
            p1, p2 = p2, p1
        wave = 0.08 * math.sin(self.t * math.pi * 3.0 + self.synapse.age * 2.0)
        axis = safe_norm(p2 - p1)
        side = safe_norm(cross(axis, vector(0, 1, 0)), random_unit())
        return lerp_vec(p1, p2, self.t) + side * wave

    def update(self, dt):
        if not self.alive:
            return
        if not self.synapse.alive:
            self.hide()
            return
        dist = max(0.25, mag(self.synapse.p2() - self.synapse.p1()))
        self.t += dt * self.speed / dist
        if self.t >= 1.0:
            self.target.receive_signal(0.10 + 0.20 * self.synapse.strength)
            self.hide()
            return
        self.synapse.seg_a.reinforce(0.010)
        self.synapse.seg_b.reinforce(0.010)
        self.sphere.pos = self.position()
        pulse = 0.5 + 0.5 * math.sin(self.t * math.pi * 8.0)
        self.sphere.radius = 0.055 + 0.055 * pulse
        self.sphere.color = lerp_vec(vector(1.0, 0.62, 0.16), vector(1.0, 1.0, 0.28), pulse)

    def hide(self):
        self.alive = False
        hide_obj(self.sphere)


class FreeParticle:
    def __init__(self, sim, pos, vel=None, mode="spill", neuron=None, color=None):
        self.sim = sim
        self.mode = mode
        self.neuron = neuron
        self.alive = True
        self.life = random.uniform(1.8, 4.8)
        self.max_life = self.life
        self.phase = random.uniform(0, 2 * math.pi)
        self.radius = random.uniform(0.035, 0.075)
        self.orbit_radius = random.uniform(0.55, 1.35)
        self.height = random.uniform(-0.6, 0.6)
        self.spin = random.choice([-1, 1]) * random.uniform(1.0, 3.0)
        self.vel = vel if vel is not None else random_unit() * random.uniform(0.3, 1.5)
        self.color = color if color is not None else vector(1.0, random.uniform(0.58, 0.95), random.uniform(0.18, 0.55))
        self.s = sphere(
            pos=pos,
            radius=self.radius,
            color=self.color,
            opacity=0.72,
            emissive=True,
            make_trail=True,
            retain=10,
            trail_radius=self.radius * 0.22,
            trail_color=self.color,
        )

    def update(self, dt):
        if not self.alive:
            return
        self.life -= dt
        if self.life <= 0:
            self.hide()
            return

        fade = clamp(self.life / self.max_life)
        if self.mode == "wrap" and self.neuron is not None:
            self.phase += self.spin * dt
            y = self.height + 0.42 * math.sin(self.phase * 0.9)
            x = math.cos(self.phase) * self.orbit_radius
            z = math.sin(self.phase) * self.orbit_radius
            self.s.pos = self.neuron.pos + vector(x, y, z)
        else:
            self.vel += vector(0, -0.06, 0) * dt
            self.s.pos += self.vel * dt
            if mag(self.s.pos) > WORLD_RADIUS + 1.2:
                n = norm(self.s.pos)
                self.s.pos = n * (WORLD_RADIUS + 1.2)
                self.vel -= 2 * dot(self.vel, n) * n
                self.vel *= 0.62

        self.s.opacity = 0.12 + 0.62 * fade
        self.s.radius = self.radius * (0.75 + 0.75 * fade)

    def hide(self):
        self.alive = False
        hide_obj(self.s)


class NetworkSimulation:
    def __init__(self):
        self.neurons = []
        self.synapses = []
        self.signals = []
        self.free_particles = []
        self.round_number = 0
        self.selected_index = 0
        self.paused = False
        self.ai_enabled = True
        self.ai_mode_text = "AI booting"
        self.time = 0.0
        self.natural_clock = 0.0
        self.orbit_impulse_timer = 0.0

        self.floor = cylinder(
            pos=vector(0, -3.25, 0),
            axis=vector(0, 0.02, 0),
            radius=WORLD_RADIUS + 0.7,
            color=vector(0.86, 0.93, 0.98),
            opacity=0.18,
        )
        self.boundary = ring(
            pos=vector(0, -3.18, 0),
            axis=vector(0, 1, 0),
            radius=WORLD_RADIUS,
            thickness=0.025,
            color=vector(0.55, 0.74, 0.92),
            opacity=0.32,
        )

        self.meter_back = box(
            pos=vector(-6.5, 5.2, -1.0),
            size=vector(3.4, 0.22, 0.12),
            color=vector(0.80, 0.88, 0.95),
            opacity=0.48,
        )
        self.meter_bar = box(
            pos=vector(-8.18, 5.2, -0.93),
            size=vector(0.05, 0.24, 0.16),
            color=vector(0.25, 0.88, 0.45),
            opacity=0.82,
            emissive=True,
        )
        self.meter_label = label(
            pos=vector(-6.5, 5.55, -1.0),
            text="Network Activity",
            height=14,
            border=6,
            color=vector(0.10, 0.18, 0.25),
            background=vector(0.94, 0.97, 1.0),
            opacity=0.45,
            box=True,
        )
        self.status_label = label(
            pos=vector(2.7, 5.55, -1.0),
            text="",
            height=13,
            border=6,
            color=vector(0.11, 0.16, 0.20),
            background=vector(0.94, 0.97, 1.0),
            opacity=0.45,
            box=True,
        )

        self.reset_round()

    def clear_dynamic(self):
        for n in self.neurons:
            n.hide()
        for s in self.synapses:
            s.detach()
        for p in self.signals:
            p.hide()
        for fp in self.free_particles:
            fp.hide()
        self.neurons = []
        self.synapses = []
        self.signals = []
        self.free_particles = []

    def reset_round(self):
        self.clear_dynamic()
        self.round_number += 1
        self.time = 0.0
        self.natural_clock = 0.0
        self.selected_index = 0

        count = INITIAL_NEURONS
        for i in range(count):
            angle = 2 * math.pi * i / count
            pos = vector(
                math.cos(angle) * random.uniform(2.2, 3.9),
                random.uniform(-1.2, 1.2),
                math.sin(angle) * random.uniform(2.2, 3.9),
            )
            n = Neuron(self, i, pos, base_color=random_pastel())
            n.vel = cross(vector(0, 1, 0), safe_norm(n.pos, random_unit())) * random.uniform(0.05, 0.18)
            self.neurons.append(n)

        for _ in range(5):
            self.attach_closest(max_dist=3.25, force=False)

        self.select_neuron(0)
        self.update_meter()

    def select_neuron(self, idx):
        if not self.neurons:
            return
        self.selected_index = idx % len(self.neurons)
        for i, n in enumerate(self.neurons):
            n.selected = (i == self.selected_index)

    def selected_neuron(self):
        if not self.neurons:
            return None
        return self.neurons[self.selected_index % len(self.neurons)]

    def total_branch_count(self):
        return sum(len(n.live_branches()) for n in self.neurons)

    def live_synapses(self):
        return [s for s in self.synapses if s.alive]

    def detach_synapses_involving_segment(self, seg):
        for s in self.synapses:
            if s.alive and s.involves_segment(seg):
                s.detach()

    def synapse_exists(self, seg_a, seg_b):
        for s in self.synapses:
            if not s.alive:
                continue
            if (s.seg_a is seg_a and s.seg_b is seg_b) or (s.seg_a is seg_b and s.seg_b is seg_a):
                return True
        return False

    def attach_segments(self, seg_a, seg_b):
        if seg_a is None or seg_b is None:
            return None
        if seg_a.neuron is seg_b.neuron:
            return None
        if self.synapse_exists(seg_a, seg_b):
            return None
        if len(self.live_synapses()) >= MAX_SYNAPSES:
            return None

        syn = Synapse(self, seg_a, seg_b)
        self.synapses.append(syn)
        seg_a.pulse(0.9)
        seg_b.pulse(0.9)
        seg_a.neuron.activity = clamp(seg_a.neuron.activity + 0.08)
        seg_b.neuron.activity = clamp(seg_b.neuron.activity + 0.08)
        return syn

    def attach_closest(self, max_dist=2.1, force=True):
        leaves = []
        for n in self.neurons:
            leaves.extend(n.leaf_segments())
        if len(leaves) < 2:
            return None

        best = None
        best_d = 999
        sample = leaves if len(leaves) < 80 else random.sample(leaves, 80)
        for i, a in enumerate(sample):
            for b in sample[i + 1:]:
                if a.neuron is b.neuron or self.synapse_exists(a, b):
                    continue
                d = mag(a.current_tip() - b.current_tip())
                if d < best_d:
                    best_d = d
                    best = (a, b)
        if best is not None and (best_d <= max_dist or force):
            return self.attach_segments(best[0], best[1])
        return None

    def detach_random_synapse(self):
        live = self.live_synapses()
        if not live:
            return None
        s = random.choice(live)
        s.detach()
        self.spill_particles(pos=(s.p1() + s.p2()) / 2, count=8, color=vector(0.82, 0.58, 1.0))
        return s

    def detach_weakest_synapse(self):
        live = self.live_synapses()
        if not live:
            return None
        s = min(live, key=lambda x: x.strength)
        s.detach()
        return s

    def spawn_signal_on_synapse(self, synapse, source=None):
        if not synapse.alive:
            return
        self.signals.append(SignalParticle(synapse, source=source))

    def spawn_signals_from_neuron(self, neuron, burst=False):
        related = [s for s in self.live_synapses() if s.neuron_a is neuron or s.neuron_b is neuron]
        if not related:
            return
        count = min(len(related), random.randint(2, 5) if burst else 1)
        for syn in random.sample(related, count):
            self.spawn_signal_on_synapse(syn, source=neuron)

    def spill_particles(self, neuron=None, pos=None, count=16, color=None):
        if neuron is not None:
            pos = neuron.pos
        if pos is None:
            pos = vector(0, 0, 0)
        for _ in range(count):
            vel = random_unit() * random.uniform(0.25, 1.8)
            vel.y += random.uniform(0.1, 0.8)
            self.free_particles.append(FreeParticle(self, pos + random_unit() * 0.18, vel=vel, mode="spill", color=color))

    def wrap_particles(self, neuron=None, count=18):
        if neuron is None:
            neuron = self.selected_neuron()
        if neuron is None:
            return
        for _ in range(count):
            col = lerp_vec(neuron.base_color, vector(1.0, 0.9, 0.18), random.uniform(0.2, 0.8))
            self.free_particles.append(FreeParticle(self, neuron.pos, mode="wrap", neuron=neuron, color=col))

    def mark_neuron(self, neuron=None):
        if neuron is None:
            neuron = self.selected_neuron()
        if neuron is not None:
            neuron.mark()

    def apply_orbit(self, strength=0.45):
        for n in self.neurons:
            tangent = cross(vector(0, 1, 0), safe_norm(n.pos, random_unit()))
            n.vel += tangent * strength * random.uniform(0.7, 1.2)
            n.vel += vector(0, math.sin(self.time + n.index) * 0.08, 0)

    def organize_circle(self, dt, radius=3.9):
        count = max(1, len(self.neurons))
        for i, n in enumerate(self.neurons):
            a = 2 * math.pi * i / count + 0.14 * math.sin(self.time * 0.2)
            target = vector(math.cos(a) * radius, 0.35 * math.sin(a * 2.0), math.sin(a) * radius)
            n.vel += (target - n.pos) * (0.38 * dt)

    def dip_neuron(self, neuron=None):
        if neuron is None:
            neuron = self.selected_neuron()
        if neuron:
            neuron.vel += vector(0, -1.25 if neuron.pos.y > -1.3 else 1.45, 0)

    def collide_neurons(self):
        for i in range(len(self.neurons)):
            for j in range(i + 1, len(self.neurons)):
                a = self.neurons[i]
                b = self.neurons[j]
                delta = b.pos - a.pos
                d = mag(delta)
                min_d = 0.92
                if d < min_d and d > 1e-5:
                    n = delta / d
                    push = (min_d - d) * 0.65
                    a.pos -= n * push
                    b.pos += n * push
                    va = dot(a.vel, n)
                    vb = dot(b.vel, n)
                    a.vel += (vb - va) * n * 0.75
                    b.vel += (va - vb) * n * 0.75
                    a.activity = clamp(a.activity + 0.08)
                    b.activity = clamp(b.activity + 0.08)

    def natural_events(self, dt):
        self.natural_clock += dt
        if self.natural_clock < 0.32:
            return
        self.natural_clock = 0.0

        if not self.ai_enabled:
            if random.random() < 0.22 and self.total_branch_count() < MAX_BRANCHES:
                random.choice(self.neurons).grow_branch()
            if random.random() < 0.16:
                self.attach_closest(max_dist=1.65, force=False)
            if random.random() < 0.05:
                self.detach_random_synapse()
            if random.random() < 0.12:
                random.choice(self.neurons).fire(0.22)
        else:
            if random.random() < 0.045 and self.total_branch_count() < MAX_BRANCHES:
                random.choice(self.neurons).grow_branch()
            if random.random() < 0.06:
                self.attach_closest(max_dist=1.35, force=False)

    def network_activity(self):
        if not self.neurons:
            return 0.0
        soma_a = sum(n.activity for n in self.neurons) / len(self.neurons)
        signal_a = clamp(len([p for p in self.signals if p.alive]) / 18.0)
        syn_a = clamp(len(self.live_synapses()) / float(MAX_SYNAPSES))
        particle_a = clamp(len([p for p in self.free_particles if p.alive]) / 90.0) * 0.35
        return clamp(0.58 * soma_a + 0.27 * signal_a + 0.12 * syn_a + particle_a)

    def update_meter(self):
        activity = self.network_activity()
        width = 3.35 * activity
        self.meter_bar.size = vector(max(0.05, width), 0.24, 0.16)
        left = -6.5 - 3.35 / 2
        self.meter_bar.pos = vector(left + max(0.05, width) / 2, 5.2, -0.93)
        self.meter_bar.color = lerp_vec(vector(0.24, 0.72, 0.92), vector(1.0, 0.70, 0.18), activity)
        self.meter_label.text = f"Network Activity: {activity:.2f}"
        self.status_label.text = (
            f"Round {self.round_number} | Branches {self.total_branch_count()} | "
            f"Synapses {len(self.live_synapses())} | Signals {len([p for p in self.signals if p.alive])} | "
            f"Strong paths {len([s for s in self.live_synapses() if s.pathway_strength > 0.62])} | "
            f"{'AI ON' if self.ai_enabled else 'AI OFF'}: {self.ai_mode_text}"
        )

    def state_snapshot(self):
        return {
            "time": self.time,
            "round": self.round_number,
            "neuron_count": len(self.neurons),
            "branch_count": self.total_branch_count(),
            "synapse_count": len(self.live_synapses()),
            "signal_count": len([s for s in self.signals if s.alive]),
            "free_particle_count": len([p for p in self.free_particles if p.alive]),
            "activity": self.network_activity(),
            "avg_pathway_strength": sum(s.pathway_strength for s in self.live_synapses()) / max(1, len(self.live_synapses())),
            "avg_neuron_activity": sum(n.activity for n in self.neurons) / max(1, len(self.neurons)),
            "max_activity": max([n.activity for n in self.neurons] + [0]),
            "selected_index": self.selected_index,
        }

    def update(self, dt):
        self.time += dt

        self.natural_events(dt)

        for n in self.neurons:
            n.update(dt)

        self.collide_neurons()

        for s in self.synapses:
            s.update(dt)
        self.synapses = [s for s in self.synapses if s.alive]

        for p in self.signals:
            p.update(dt)
        self.signals = [p for p in self.signals if p.alive]

        for fp in self.free_particles:
            fp.update(dt)
        self.free_particles = [fp for fp in self.free_particles if fp.alive]

        self.update_meter()


class ExpressiveAIController:
    """
    AI behavior modes implemented in this file:
      construct, connect, pulse, prune, orbit, organize, careful, chaotic,
      curious, ritual, destructive, artistic, reset_loop

    The controller reads sim.state_snapshot(), chooses an action mode, and
    applies visible actions automatically while keyboard control remains active.
    """

    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.mode = "construct"
        self.mode_timer = 0.0
        self.mode_duration = 5.0
        self.action_timer = 0.0
        self.history_timer = 0.0
        self.history = []
        self.stagnant_for = 0.0
        self.loop_cooldown = 0.0
        self.recent_modes = []
        self.modes = [
            "construct",
            "connect",
            "pulse",
            "prune",
            "orbit",
            "organize",
            "careful",
            "chaotic",
            "curious",
            "ritual",
            "destructive",
            "artistic",
        ]
        self.set_mode("construct")

    def set_mode(self, mode=None):
        if mode is None:
            mode = self.choose_next_mode(self.sim.state_snapshot())
        self.mode = mode
        self.sim.ai_mode_text = mode
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.mode_duration = random.uniform(3.8, 8.5)
        self.recent_modes.append(mode)
        self.recent_modes = self.recent_modes[-5:]

    def force_next_mode(self):
        self.set_mode(self.choose_next_mode(self.sim.state_snapshot(), force_variety=True))

    def choose_next_mode(self, state, force_variety=False):
        candidates = list(self.modes)

        if force_variety:
            candidates = [m for m in candidates if m not in self.recent_modes[-3:]] or candidates

        if state["branch_count"] < 34:
            weighted = ["construct", "construct", "curious", "organize", "connect"]
        elif state["synapse_count"] < 7:
            weighted = ["connect", "connect", "construct", "careful", "ritual"]
        elif state["activity"] < 0.22:
            weighted = ["pulse", "curious", "ritual", "artistic", "orbit"]
        elif state["synapse_count"] > MAX_SYNAPSES * 0.78:
            weighted = ["prune", "careful", "destructive", "organize", "pulse"]
        elif self.stagnant_for > 7.0:
            weighted = ["chaotic", "destructive", "orbit", "artistic", "reset_loop"]
        else:
            weighted = [
                "construct", "connect", "pulse", "orbit", "organize", "careful",
                "chaotic", "curious", "ritual", "artistic"
            ]

        if force_variety:
            weighted = [m for m in weighted if m not in self.recent_modes[-2:]] or weighted

        return random.choice(weighted)

    def update_stagnation_detector(self, dt, state):
        self.history_timer += dt
        if self.history_timer < 0.55:
            return
        self.history_timer = 0.0

        signature = (
            state["branch_count"],
            state["synapse_count"],
            round(state["activity"], 2),
            state["signal_count"],
        )
        self.history.append(signature)
        self.history = self.history[-10:]

        if len(self.history) >= 6:
            oldest = self.history[0]
            newest = self.history[-1]
            branch_delta = abs(newest[0] - oldest[0])
            syn_delta = abs(newest[1] - oldest[1])
            activity_delta = abs(newest[2] - oldest[2])
            signal_delta = abs(newest[3] - oldest[3])
            stable = branch_delta <= 1 and syn_delta <= 1 and activity_delta < 0.06 and signal_delta <= 2
            empty = newest[0] < 6 or state["neuron_count"] == 0
            complete = newest[0] >= MAX_BRANCHES and newest[1] >= MAX_SYNAPSES * 0.75 and state["activity"] < 0.25
            if stable or empty or complete:
                self.stagnant_for += 0.55
            else:
                self.stagnant_for = max(0.0, self.stagnant_for - 0.75)

    def should_reset_loop(self, state):
        if not AUTO_RESET_AFTER_STAGNATION:
            return False
        if self.loop_cooldown > 0:
            return False
        if state["neuron_count"] == 0:
            return True
        if state["branch_count"] < 4:
            return True
        if self.stagnant_for > 13.0:
            return True
        if state["branch_count"] >= MAX_BRANCHES and state["synapse_count"] >= MAX_SYNAPSES * 0.82 and state["activity"] < 0.18:
            return True
        if self.mode == "reset_loop" and self.mode_timer > 2.0:
            return True
        return False

    def tick(self, dt):
        self.enabled = self.sim.ai_enabled
        if not self.enabled:
            return

        state = self.sim.state_snapshot()
        self.update_stagnation_detector(dt, state)

        if self.loop_cooldown > 0:
            self.loop_cooldown -= dt

        if self.should_reset_loop(state):
            self.sim.spill_particles(pos=vector(0, 0, 0), count=45, color=vector(0.95, 0.75, 1.0))
            self.sim.reset_round()
            self.stagnant_for = 0.0
            self.history = []
            self.loop_cooldown = 8.0
            self.set_mode("construct")
            return

        self.mode_timer += dt
        self.action_timer += dt

        if self.mode_timer > self.mode_duration:
            self.set_mode(self.choose_next_mode(state, force_variety=True))
            return

        self.execute_mode(dt, state)

    def execute_mode(self, dt, state):
        sim = self.sim

        if self.mode == "construct":
            if self.action_timer > 0.34:
                self.action_timer = 0.0
                if state["branch_count"] < MAX_BRANCHES:
                    n = random.choice(sim.neurons)
                    n.grow_branch(kind=random.choice(["dendrite", "dendrite", "axon"]))
                    n.activity = clamp(n.activity + 0.04)
                if random.random() < 0.28:
                    sim.attach_closest(max_dist=2.4, force=False)

        elif self.mode == "connect":
            if self.action_timer > 0.26:
                self.action_timer = 0.0
                syn = sim.attach_closest(max_dist=2.7, force=random.random() < 0.34)
                if syn and random.random() < 0.65:
                    sim.spawn_signal_on_synapse(syn, source=random.choice([syn.neuron_a, syn.neuron_b]))
                sim.organize_circle(dt, radius=3.4)

        elif self.mode == "pulse":
            if self.action_timer > 0.38:
                self.action_timer = 0.0
                n = random.choice(sim.neurons)
                n.fire(random.uniform(0.20, 0.55))
                if random.random() < 0.25:
                    sim.wrap_particles(n, count=4)

        elif self.mode == "prune":
            if self.action_timer > 0.60:
                self.action_timer = 0.0
                if random.random() < 0.55:
                    n = max(sim.neurons, key=lambda x: len(x.live_branches()))
                    n.prune_leaf()
                    sim.spill_particles(neuron=n, count=5, color=vector(0.64, 0.76, 1.0))
                else:
                    sim.detach_weakest_synapse()

        elif self.mode == "orbit":
            sim.apply_orbit(strength=0.030)
            if self.action_timer > 1.05:
                self.action_timer = 0.0
                random.choice(sim.neurons).fire(0.18)

        elif self.mode == "organize":
            sim.organize_circle(dt, radius=3.6 + 0.8 * math.sin(sim.time * 0.25))
            if self.action_timer > 0.75:
                self.action_timer = 0.0
                sim.attach_closest(max_dist=2.15, force=False)
                if random.random() < 0.25:
                    random.choice(sim.neurons).mark(vector(0.35, 0.72, 1.0))

        elif self.mode == "careful":
            sim.organize_circle(dt, radius=4.2)
            if self.action_timer > 0.72:
                self.action_timer = 0.0
                if state["synapse_count"] > 12 and random.random() < 0.45:
                    sim.detach_weakest_synapse()
                elif state["branch_count"] < MAX_BRANCHES:
                    random.choice(sim.neurons).grow_branch(kind="dendrite")
                sim.attach_closest(max_dist=1.8, force=False)

        elif self.mode == "chaotic":
            if self.action_timer > 0.28:
                self.action_timer = 0.0
                n = random.choice(sim.neurons)
                n.vel += random_unit() * random.uniform(0.35, 1.15)
                n.rotate_arbor(angle=random.uniform(-0.35, 0.35), axis=random_unit())
                if random.random() < 0.35:
                    n.fire(0.30)
                if random.random() < 0.35:
                    sim.detach_random_synapse()
                if random.random() < 0.45:
                    sim.spill_particles(neuron=n, count=5)

        elif self.mode == "curious":
            if self.action_timer > 0.48:
                self.action_timer = 0.0
                n = random.choice(sim.neurons)
                target = random.choice([x for x in sim.neurons if x is not n] or [n])
                direction = safe_norm(target.pos - n.pos, random_unit())
                n.vel += direction * 0.26 + random_unit() * 0.08
                if random.random() < 0.50:
                    n.grow_branch(kind=random.choice(["axon", "dendrite"]))
                if random.random() < 0.25:
                    sim.attach_closest(max_dist=2.2, force=False)

        elif self.mode == "ritual":
            sim.organize_circle(dt, radius=3.25 + 0.45 * math.sin(sim.time * 0.65))
            if self.action_timer > 0.90:
                self.action_timer = 0.0
                idx = int((sim.time * 0.8) % max(1, len(sim.neurons)))
                n = sim.neurons[idx]
                n.fire(0.45)
                n.mark(vector(1.0, 0.72, 0.25))
                sim.wrap_particles(n, count=7)

        elif self.mode == "destructive":
            if self.action_timer > 0.44:
                self.action_timer = 0.0
                if random.random() < 0.58:
                    sim.detach_random_synapse()
                else:
                    n = random.choice(sim.neurons)
                    n.prune_leaf()
                    n.vel += random_unit() * 0.5
                sim.spill_particles(pos=random_unit() * random.uniform(0.4, 3.0), count=7, color=vector(1.0, 0.46, 0.28))

        elif self.mode == "artistic":
            if self.action_timer > 0.62:
                self.action_timer = 0.0
                n = random.choice(sim.neurons)
                palette = random.choice([
                    vector(1.0, 0.50, 0.85),
                    vector(0.35, 0.88, 1.0),
                    vector(1.0, 0.88, 0.22),
                    vector(0.60, 1.0, 0.56),
                ])
                n.mark(palette)
                sim.wrap_particles(n, count=6)
                if random.random() < 0.45:
                    n.fire(0.22)
                if random.random() < 0.35:
                    sim.attach_closest(max_dist=2.0, force=False)

        elif self.mode == "reset_loop":
            if self.action_timer > 0.22:
                self.action_timer = 0.0
                sim.spill_particles(pos=random_unit() * random.uniform(0.2, 3.0), count=6, color=vector(0.95, 0.68, 1.0))


sim = NetworkSimulation()
ai = ExpressiveAIController(sim)


def keydown(evt):
    key = evt.key
    n = sim.selected_neuron()

    if key == " ":
        sim.paused = not sim.paused

    elif key.lower() == "a":
        sim.ai_enabled = not sim.ai_enabled
        sim.ai_mode_text = ai.mode if sim.ai_enabled else "manual"

    elif key.lower() == "r":
        sim.reset_round()
        ai.stagnant_for = 0.0
        ai.history = []
        ai.set_mode("construct")

    elif key.lower() == "n":
        ai.force_next_mode()

    elif key == "tab":
        sim.select_neuron(sim.selected_index + 1)

    elif key in [str(i) for i in range(1, 10)]:
        idx = int(key) - 1
        if idx < len(sim.neurons):
            sim.select_neuron(idx)

    elif n is not None:
        impulse = 0.70

        if key == "left":
            n.vel += vector(-impulse, 0, 0)
        elif key == "right":
            n.vel += vector(impulse, 0, 0)
        elif key == "up":
            n.vel += vector(0, impulse, 0)
        elif key == "down":
            n.vel += vector(0, -impulse, 0)
        elif key.lower() == "w":
            n.vel += vector(0, 0, -impulse)
        elif key.lower() == "s":
            n.vel += vector(0, 0, impulse)
        elif key.lower() == "q":
            n.rotate_arbor(angle=0.24, axis=vector(0, 1, 0))
        elif key.lower() == "e":
            n.rotate_arbor(angle=-0.24, axis=vector(0, 1, 0))
        elif key.lower() == "g":
            n.grow_branch()
        elif key.lower() == "p":
            n.fire(0.65)
        elif key.lower() == "c":
            sim.attach_closest(max_dist=3.2, force=True)
        elif key.lower() == "d":
            sim.detach_random_synapse()
        elif key.lower() == "x":
            n.prune_leaf()
        elif key.lower() == "m":
            sim.mark_neuron(n)
        elif key.lower() == "v":
            sim.spill_particles(neuron=n, count=22)
        elif key.lower() == "b":
            sim.wrap_particles(n, count=20)
        elif key.lower() == "o":
            sim.apply_orbit(strength=0.75)
        elif key.lower() == "i":
            sim.dip_neuron(n)


scene.bind("keydown", keydown)

dt = 1.0 / 60.0
while True:
    rate(60)

    if not sim.paused:
        ai.tick(dt)
        sim.update(dt)
    else:
        sim.status_label.text = (
            f"PAUSED | Round {sim.round_number} | Branches {sim.total_branch_count()} | "
            f"Synapses {len(sim.live_synapses())} | {'AI ON' if sim.ai_enabled else 'AI OFF'}: {sim.ai_mode_text}"
        )
