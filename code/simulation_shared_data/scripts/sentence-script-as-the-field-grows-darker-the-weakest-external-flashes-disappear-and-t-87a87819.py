from vpython import *
import random
import math

# Sleeping Signal Garden
# Initial simulation seed:
# A few disconnected neuron bodies sit in a quiet space. Their signals are short,
# unstable, and mostly random. As the environment darkens, internal pulses begin
# looping and repeated paths become early glowing dream paths.

scene = canvas(
    title="Sleeping Signal Garden - Initial Simulation",
    width=1100,
    height=720,
    background=vector(0.88, 0.92, 0.96),
    center=vector(0, 0, 0),
)
scene.camera.pos = vector(0, 21, 26)
scene.camera.axis = vector(0, -17, -25)
scene.range = 15
scene.forward = vector(0, -0.55, -1)
scene.caption = """
Sleeping Signal Garden\n
Bright phase: weak outside flashes disturb disconnected neurons.\nDark phase: the weakest outside flashes vanish first; internal echoes take over and repeated signal paths thicken into dream paths.\n
Visible states:\n  pale neurons = quiet\n  cyan pulses = short unstable firing\n  yellow outside sparks = waking input, disappearing as sleep deepens\n  violet echo motes = internal replay replacing outside input\n  violet/gold paths = early dream traces\n  central mist = accumulating sleep chemistry\n"""

# ---------- Helpers ----------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_vec(a, b, t):
    return a * (1 - t) + b * t


def random_disk(radius):
    r = radius * math.sqrt(random.random())
    th = random.uniform(0, 2 * math.pi)
    return vector(r * math.cos(th), random.uniform(-0.35, 0.35), r * math.sin(th))


def make_text(pos, text, height=0.45):
    return label(
        pos=pos,
        text=text,
        height=height,
        box=False,
        opacity=0,
        color=vector(0.15, 0.18, 0.23),
    )

# ---------- Ground / sleep field ----------

ground = box(
    pos=vector(0, -0.48, 0),
    size=vector(31, 0.08, 31),
    color=vector(0.82, 0.86, 0.90),
    opacity=0.42,
)

sleep_mist = sphere(
    pos=vector(0, -0.12, 0),
    radius=1.6,
    color=vector(0.45, 0.34, 0.82),
    opacity=0.08,
)

sleep_wave = ring(
    pos=vector(0, -0.2, 0),
    axis=vector(0, 1, 0),
    radius=2.0,
    thickness=0.025,
    color=vector(0.35, 0.30, 0.80),
    opacity=0.18,
)

status_label = make_text(vector(-14.5, 7.5, 0), "mode: waking noise", 0.5)
cycle_label = make_text(vector(-14.5, 6.7, 0), "sleep depth: 0.00", 0.42)
input_label = make_text(vector(-14.5, 5.95, 0), "input source: outside flashes", 0.38)

# ---------- Neurons ----------

class Neuron:
    def __init__(self, idx, pos):
        self.idx = idx
        self.pos = pos
        self.phase = random.uniform(0, 2 * math.pi)
        self.freq = random.uniform(0.45, 0.95)
        self.charge = random.uniform(0.0, 0.25)
        self.memory = 0.0
        self.echo_charge = 0.0
        self.last_fire = -100.0
        self.refractory = random.uniform(0.35, 0.7)
        self.dream_bias = random.uniform(0.0, 0.15)
        self.soma = sphere(
            pos=pos,
            radius=random.uniform(0.35, 0.50),
            color=vector(0.72, 0.78, 0.84),
            opacity=0.92,
            shininess=0.25,
        )
        self.halo = ring(
            pos=pos,
            axis=vector(0, 1, 0),
            radius=self.soma.radius * 1.7,
            thickness=0.018,
            color=vector(0.50, 0.82, 1.00),
            opacity=0.05,
        )
        self.core = sphere(
            pos=pos + vector(0, 0.02, 0),
            radius=self.soma.radius * 0.34,
            color=vector(0.30, 0.70, 1.00),
            opacity=0.16,
        )
        self.tendrils = []
        for _ in range(4):
            th = random.uniform(0, 2 * math.pi)
            length = random.uniform(0.8, 1.45)
            end = pos + vector(math.cos(th) * length, random.uniform(-0.05, 0.14), math.sin(th) * length)
            tendril = cylinder(
                pos=pos,
                axis=end - pos,
                radius=0.025,
                color=vector(0.67, 0.73, 0.80),
                opacity=0.30,
            )
            self.tendrils.append(tendril)

    def disturb(self, amount, now):
        if now - self.last_fire > self.refractory:
            self.charge += amount

    def update(self, dt, now, sleep_depth, external_light, echo_pressure):
        # Waking input is noisy. As sleep deepens, outside input collapses and
        # stored echoes become the main energy source.
        noisy_gain = (1.0 - sleep_depth) * random.uniform(0.0, 0.020)
        echo_wave = max(0.0, math.sin(now * self.freq + self.phase))
        dream_gain = sleep_depth * (0.010 + self.dream_bias * 0.020) * echo_wave
        self.echo_charge *= 0.988
        self.echo_charge += echo_pressure * self.memory * (0.004 + 0.018 * sleep_depth)
        self.charge += noisy_gain + max(0.0, dream_gain) + self.echo_charge
        self.charge *= 0.965 - 0.018 * sleep_depth
        self.memory *= 0.996

        threshold = 0.50 - 0.13 * sleep_depth
        fired = False
        if self.charge > threshold and now - self.last_fire > self.refractory:
            fired = True
            self.last_fire = now
            self.memory = clamp(self.memory + 0.10 + 0.06 * sleep_depth, 0, 1)
            self.charge = 0.10 + random.uniform(0, 0.05)

        active = clamp(self.charge * 1.5 + self.memory * 0.7 + self.echo_charge * 3.5, 0, 1)
        quiet_color = vector(0.62, 0.68, 0.75) * (0.8 + 0.2 * external_light)
        active_color = lerp_vec(vector(0.35, 0.75, 1.00), vector(0.86, 0.68, 1.00), sleep_depth)
        self.soma.color = lerp_vec(quiet_color, active_color, active)
        self.soma.radius = self.soma.radius * 0.985 + (0.38 + 0.10 * active) * 0.015
        self.core.opacity = 0.12 + 0.45 * active
        self.core.color = active_color
        self.halo.opacity = 0.04 + 0.55 * active
        self.halo.radius = self.soma.radius * (1.6 + 0.65 * active + 0.18 * math.sin(now * 5 + self.idx))
        self.halo.color = lerp_vec(vector(0.38, 0.80, 1.00), vector(0.78, 0.45, 1.00), sleep_depth)
        for t in self.tendrils:
            t.opacity = 0.18 + 0.25 * active
            t.color = lerp_vec(vector(0.64, 0.70, 0.78), active_color, active * 0.75)
        return fired

class Edge:
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.strength = random.uniform(0.04, 0.10)
        self.replay = 0.0
        self.loop_score = 0.0
        self.obj = cylinder(
            pos=a.pos,
            axis=b.pos - a.pos,
            radius=0.025,
            color=vector(0.56, 0.62, 0.72),
            opacity=0.05,
        )

    def update(self, sleep_depth, now):
        self.replay *= 0.985
        self.strength *= 0.9992
        dream = clamp(self.loop_score * sleep_depth + self.replay, 0, 1)
        self.obj.pos = self.a.pos
        self.obj.axis = self.b.pos - self.a.pos
        self.obj.radius = 0.018 + 0.055 * clamp(self.strength + dream, 0, 1)
        waking_color = vector(0.50, 0.62, 0.75)
        dream_color = lerp_vec(vector(0.58, 0.32, 1.00), vector(1.00, 0.74, 0.22), clamp(self.loop_score, 0, 1))
        self.obj.color = lerp_vec(waking_color, dream_color, sleep_depth)
        self.obj.opacity = clamp(0.04 + self.strength * 0.45 + dream * 0.55, 0.03, 0.88)

    def reinforce(self, amount):
        self.strength = clamp(self.strength + amount, 0, 1)
        self.replay = clamp(self.replay + amount * 2.4, 0, 1)
        self.loop_score = clamp(self.loop_score + amount * 0.65, 0, 1)

class Pulse:
    def __init__(self, edge, direction=1, dream=False):
        self.edge = edge
        self.t = 0.0 if direction == 1 else 1.0
        self.direction = direction
        self.speed = random.uniform(0.010, 0.023) * (1.0 + 0.5 * edge.strength)
        self.dream = dream
        self.obj = sphere(
            pos=edge.a.pos,
            radius=0.105 if not dream else 0.135,
            color=vector(0.30, 0.82, 1.00) if not dream else vector(0.90, 0.55, 1.00),
            opacity=0.78 if not dream else 0.92,
            emissive=True,
        )

    def update(self):
        self.t += self.speed * self.direction
        a = self.edge.a.pos
        b = self.edge.b.pos
        self.obj.pos = a * (1 - self.t) + b * self.t + vector(0, 0.08 * math.sin(self.t * math.pi), 0)
        self.obj.opacity *= 0.996
        finished = self.t > 1.03 or self.t < -0.03 or self.obj.opacity < 0.05
        return not finished

    def destroy(self):
        self.obj.visible = False

# Place neurons in separated islands; no stable paths at first.
neurons = []
for i in range(22):
    pos = random_disk(11.5)
    # Keep a loose open center so the sleep mist can be seen.
    if mag(pos) < 2.3:
        pos = norm(pos + vector(0.1, 0, 0.1)) * random.uniform(3.0, 5.0)
    neurons.append(Neuron(i, pos))

# Candidate edges are invisible/very faint until repeated co-firing strengthens them.
edges = []
for i, a in enumerate(neurons):
    distances = []
    for j, b in enumerate(neurons):
        if i < j:
            distances.append((mag(a.pos - b.pos), a, b))
    distances.sort(key=lambda x: x[0])
    for d, a, b in distances[:3]:
        if d < 7.0 and random.random() < 0.38:
            edges.append(Edge(a, b))

# Avoid duplicate edge objects.
unique = {}
for e in edges:
    key = tuple(sorted([e.a.idx, e.b.idx]))
    if key not in unique:
        unique[key] = e
    else:
        e.obj.visible = False
edges = list(unique.values())

pulses = []
external_flashes = []
fired_recent = []

# Small drifting outside stimuli. Each has a strength; the weakest ones
# disappear first as the field darkens.
for _ in range(15):
    strength = random.uniform(0.12, 1.0)
    p = sphere(
        pos=random_disk(14.5) + vector(0, random.uniform(0.4, 1.4), 0),
        radius=0.035 + 0.105 * strength,
        color=lerp_vec(vector(0.85, 0.90, 1.0), vector(1.0, 0.92, 0.45), strength),
        opacity=random.uniform(0.16, 0.42) * strength,
        emissive=True,
    )
    p.vel = vector(random.uniform(-0.018, 0.018), 0, random.uniform(-0.018, 0.018))
    p.strength = strength
    p.base_radius = p.radius
    p.extinct = False
    external_flashes.append(p)

# Violet echo motes are internal traces. They are almost invisible while awake,
# then brighten as the colony stops listening to the outside field.
echo_motes = []
for _ in range(18):
    carrier = random.choice(neurons)
    mote = sphere(
        pos=carrier.pos + vector(random.uniform(-0.6, 0.6), random.uniform(0.15, 0.85), random.uniform(-0.6, 0.6)),
        radius=random.uniform(0.045, 0.09),
        color=vector(0.76, 0.48, 1.0),
        opacity=0.0,
        emissive=True,
    )
    mote.carrier = carrier
    mote.phase = random.uniform(0, 2 * math.pi)
    mote.orbit = random.uniform(0.25, 0.85)
    echo_motes.append(mote)

# ---------- Main loop ----------

now = 0.0
dt = 1.0 / 60.0
sleep_cycle_seconds = 38.0

while True:
    rate(60)
    now += dt

    # Gradual transition from waking noise into sleep, with a long soft cycle.
    cycle = (math.sin((now / sleep_cycle_seconds) * 2 * math.pi - math.pi / 2) + 1) / 2
    sleep_depth = clamp(cycle ** 1.55, 0, 1)
    external_light = 1.0 - sleep_depth

    # Background dims and cools.
    scene.background = lerp_vec(vector(0.88, 0.92, 0.96), vector(0.055, 0.065, 0.115), sleep_depth)
    ground.color = lerp_vec(vector(0.82, 0.86, 0.90), vector(0.12, 0.13, 0.22), sleep_depth)
    ground.opacity = 0.42 - 0.12 * sleep_depth

    sleep_mist.radius = 1.7 + 6.8 * sleep_depth + 0.35 * math.sin(now * 1.2)
    sleep_mist.opacity = 0.06 + 0.16 * sleep_depth
    sleep_mist.color = lerp_vec(vector(0.45, 0.34, 0.82), vector(0.67, 0.46, 1.0), sleep_depth)
    sleep_wave.radius = 2.2 + 8.0 * ((now * 0.11) % 1.0)
    sleep_wave.opacity = (0.06 + 0.24 * sleep_depth) * (1.0 - ((now * 0.11) % 1.0))
    sleep_wave.color = lerp_vec(vector(0.35, 0.30, 0.80), vector(0.95, 0.65, 1.0), sleep_depth)

    status_label.text = "mode: waking noise" if sleep_depth < 0.35 else ("mode: outside fading" if sleep_depth < 0.72 else "mode: internal echo reliance")
    status_label.color = lerp_vec(vector(0.12, 0.15, 0.20), vector(0.80, 0.72, 1.00), sleep_depth)
    cycle_label.text = "sleep depth: %.2f" % sleep_depth
    cycle_label.color = status_label.color
    outside_strength = 0.0
    echo_pressure = clamp((sleep_depth - 0.30) / 0.70, 0, 1)
    input_label.text = "input source: outside flashes" if echo_pressure < 0.35 else ("input source: fading outside + echoes" if echo_pressure < 0.75 else "input source: internal echoes")
    input_label.color = status_label.color

    # External flashes wander, then wink out by strength. Weak flashes vanish
    # early; only strong flashes survive shallow sleep, and none dominate deep sleep.
    for p in external_flashes:
        p.pos += p.vel
        if mag(vector(p.pos.x, 0, p.pos.z)) > 15.0:
            p.pos = random_disk(13.5) + vector(0, random.uniform(0.4, 1.4), 0)
        survival_gate = clamp((external_light - (0.08 + 0.58 * (1.0 - p.strength))) / 0.35, 0, 1)
        flicker = 0.55 + 0.45 * math.sin(now * (2.5 + p.strength * 4.0) + p.strength * 9.0)
        visible_input = survival_gate * flicker
        p.opacity = clamp(0.04 + 0.40 * visible_input * p.strength, 0, 0.48)
        p.radius = p.base_radius * (0.65 + 0.55 * visible_input)
        p.color = lerp_vec(vector(0.55, 0.62, 0.78), vector(1.0, 0.92, 0.45), visible_input)
        outside_strength += visible_input * p.strength
        if visible_input > 0.15 and random.random() < 0.020 + 0.030 * visible_input:
            target = min(neurons, key=lambda n: mag(n.pos - p.pos))
            if mag(target.pos - p.pos) < 4.0:
                target.disturb(random.uniform(0.08, 0.20) * visible_input, now)

    outside_strength = clamp(outside_strength / max(1, len(external_flashes)), 0, 1)
    echo_pressure = clamp(max(echo_pressure, sleep_depth * (1.0 - outside_strength) * 1.18), 0, 1)

    # Internal echo motes visibly replace the missing outside sparks.
    for mote in echo_motes:
        n = mote.carrier
        mote.phase += 0.020 + 0.030 * sleep_depth
        mote.pos = n.pos + vector(
            math.cos(mote.phase) * mote.orbit,
            0.28 + 0.45 * math.sin(mote.phase * 0.7 + n.idx),
            math.sin(mote.phase) * mote.orbit,
        )
        echo_brightness = clamp(echo_pressure * (0.25 + n.memory + n.echo_charge * 8.0), 0, 1)
        mote.opacity = 0.02 + 0.55 * echo_brightness
        mote.radius = 0.045 + 0.075 * echo_brightness
        if echo_brightness > 0.20 and random.random() < 0.006 + 0.020 * echo_brightness:
            n.disturb(0.035 + 0.12 * echo_brightness, now)

    fired_now = []
    for n in neurons:
        if n.update(dt, now, sleep_depth, external_light, echo_pressure):
            fired_now.append(n)
            fired_recent.append((now, n))

    # Keep recent co-fire events only.
    fired_recent = [(t, n) for (t, n) in fired_recent if now - t < 1.1]

    # Repeated near co-firing strengthens faint edges into dream traces.
    for e in edges:
        a_times = [t for (t, n) in fired_recent if n is e.a]
        b_times = [t for (t, n) in fired_recent if n is e.b]
        reinforced = False
        for ta in a_times:
            for tb in b_times:
                if abs(ta - tb) < (0.42 + 0.40 * sleep_depth):
                    e.reinforce(0.006 + 0.020 * sleep_depth)
                    reinforced = True
                    break
            if reinforced:
                break
        # Dream replay can reinforce without outside stimulus; this becomes
        # more common as outside flashes disappear.
        if sleep_depth > 0.55 and e.loop_score > 0.15 and random.random() < 0.010 + e.loop_score * 0.018 + echo_pressure * 0.012:
            e.reinforce(0.010)
            pulses.append(Pulse(e, direction=random.choice([1, -1]), dream=True))
        e.update(sleep_depth, now)

    # Fire short unstable pulses on available edges.
    for n in fired_now:
        connected = [e for e in edges if e.a is n or e.b is n]
        random.shuffle(connected)
        for e in connected[:2]:
            if random.random() < 0.45 + sleep_depth * 0.35:
                direction = 1 if e.a is n else -1
                pulses.append(Pulse(e, direction=direction, dream=sleep_depth > 0.72))
                e.reinforce(0.004 + 0.010 * sleep_depth)

    # Occasionally add pure internal dream pulses through the strongest traces.
    if sleep_depth > 0.78 and random.random() < 0.035 and edges:
        e = max(edges, key=lambda ed: ed.loop_score + random.random() * 0.18)
        pulses.append(Pulse(e, direction=random.choice([1, -1]), dream=True))
        e.reinforce(0.008)

    # Limit pulse count for stable long-running display.
    if len(pulses) > 110:
        for old in pulses[:20]:
            old.destroy()
        pulses = pulses[20:]

    new_pulses = []
    for p in pulses:
        if p.update():
            new_pulses.append(p)
        else:
            p.destroy()
    pulses = new_pulses
