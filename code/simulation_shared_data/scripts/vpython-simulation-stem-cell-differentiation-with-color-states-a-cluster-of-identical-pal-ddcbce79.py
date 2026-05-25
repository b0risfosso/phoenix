from vpython import *
import random
import math
import time

# Stem Cell Differentiation with Color States
# VPython self-contained simulation with an automatic expressive AI controller.
# Controls:
#   SPACE: pause/resume
#   A: toggle AI
#   R: reset round
#   S: manual signal burst near the cluster
#   F: feed frontier cells with signals
#   D: detach attached signals
#   C: chaos kick
#   M: next AI behavior mode
#   1-8: force AI behavior mode
#   H: temporary human override / AI quiet period

scene.title = "3D Stem Cell Differentiation: Signals, Branches, and AI Controller"
scene.width = 1200
scene.height = 780
scene.background = vector(0.93, 0.97, 1.0)
scene.forward = vector(-0.55, -0.35, -0.75)
scene.up = vector(0, 1, 0)
scene.camera.pos = vector(0, 3.5, 8.5)
scene.camera.axis = vector(0, -2.4, -8.5)
scene.autoscale = False
scene.range = 5.7
scene.ambient = color.gray(0.72)
distant_light(direction=vector(0.4, -0.7, -0.5), color=color.gray(0.55))
distant_light(direction=vector(-0.8, 0.35, 0.4), color=color.gray(0.35))

PALE = vector(0.96, 0.90, 0.78)
PALE_EDGE = vector(0.82, 0.76, 0.65)
TYPE_COLORS = {
    0: PALE,
    1: vector(0.22, 0.55, 1.00),   # blue neural-like
    2: vector(1.00, 0.34, 0.39),   # rose muscle-like
    3: vector(0.24, 0.82, 0.47),   # green epithelial-like
    4: vector(1.00, 0.72, 0.18),   # amber blood-like
}
TYPE_NAMES = {
    0: "stem",
    1: "neural-blue",
    2: "muscle-rose",
    3: "epithelial-green",
    4: "blood-amber",
}

AI_MODE_NAMES = [
    "SCOUT",
    "SEED",
    "AMPLIFY",
    "WEAVE",
    "WRAP",
    "CURATE",
    "CHAOS",
    "REST",
    "RESETTING",
]

CELL_COUNT = 105
CLUSTER_RADIUS = 3.05
BOUND_RADIUS = 4.15
CELL_RADIUS = 0.255
NEIGHBOR_DISTANCE = 0.92
MAX_SIGNALS = 190

cells = []
signals = []
branches = []
decorations = []
boundary = None
ai = None
paused = False
sim_time = 0.0
round_number = 1
frame_count = 0
last_caption_update = 0.0


def rand_unit():
    while True:
        v = vector(random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        if mag(v) > 1e-6:
            return norm(v)


def random_in_sphere(radius):
    while True:
        v = vector(random.uniform(-radius, radius), random.uniform(-radius, radius), random.uniform(-radius, radius))
        if mag(v) <= radius:
            return v


def random_shell(radius, thickness=0.12):
    return rand_unit() * random.uniform(radius - thickness, radius + thickness)


def clamp_mag(v, maximum):
    m = mag(v)
    if m > maximum and m > 1e-9:
        return norm(v) * maximum
    return v


def soft_mix(a, b, f):
    return a * (1 - f) + b * f


def make_basis(axis):
    axis = norm(axis)
    ref = vector(0, 1, 0)
    if abs(dot(axis, ref)) > 0.9:
        ref = vector(1, 0, 0)
    u = norm(cross(axis, ref))
    v = norm(cross(axis, u))
    return u, v


def safe_visible_false(obj):
    try:
        obj.visible = False
    except Exception:
        pass


class Transient:
    def __init__(self, obj, ttl=2.0, fade=True, spin=0.0):
        self.obj = obj
        self.ttl = ttl
        self.max_ttl = max(ttl, 0.01)
        self.fade = fade
        self.spin = spin
        self.dead = False

    def update(self, dt):
        self.ttl -= dt
        if self.spin != 0:
            try:
                self.obj.rotate(angle=self.spin * dt, axis=vector(0, 1, 0), origin=self.obj.pos)
            except Exception:
                pass
        if self.fade:
            try:
                self.obj.opacity = max(0.0, min(1.0, self.ttl / self.max_ttl)) * 0.55
            except Exception:
                pass
        if self.ttl <= 0:
            safe_visible_false(self.obj)
            self.dead = True


class Cell:
    def __init__(self, index, pos):
        self.index = index
        self.pos = pos
        self.radius = CELL_RADIUS * random.uniform(0.92, 1.12)
        self.state = 0
        self.birth_t = sim_time
        self.changed_t = None
        self.neighbors = []
        self.exposure = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.threshold = random.uniform(1.15, 1.55)
        self.axis = rand_unit()
        self.spin_axis = rand_unit()
        self.source_index = None
        self.kind_memory = 0

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=PALE,
            opacity=0.58,
            shininess=0.18,
        )
        self.body.emissive = False
        self.alt = None
        self.marker = None
        self.small_orbiters = []
        self.pulse_phase = random.uniform(0, 2 * math.pi)

    def visual_radius(self):
        if self.state == 0:
            return self.radius * 1.15
        if self.state == 1:
            return self.radius * 1.65
        if self.state == 2:
            return self.radius * 1.45
        if self.state == 3:
            return self.radius * 1.35
        return self.radius * 1.35

    def delete_extra_visuals(self):
        if self.alt is not None:
            safe_visible_false(self.alt)
            self.alt = None
        if self.marker is not None:
            safe_visible_false(self.marker)
            self.marker = None
        for o in self.small_orbiters:
            safe_visible_false(o)
        self.small_orbiters = []

    def destroy(self):
        safe_visible_false(self.body)
        self.delete_extra_visuals()

    def receive_signal(self, kind, amount):
        if kind < 1 or kind > 4:
            return
        if self.state == 0:
            self.exposure[kind] += amount
            if self.exposure[kind] >= self.threshold:
                src = nearest_changed_cell(self.pos, max_distance=1.25)
                self.differentiate(kind, source_cell=src)
        else:
            self.kind_memory = kind

    def dominant_neighbor_kind(self):
        weights = [0, 0, 0, 0, 0]
        strongest = None
        strongest_score = -1
        for n in self.neighbors:
            if n.state != 0:
                d = max(0.08, mag(n.pos - self.pos))
                score = 1.0 / (d * d)
                weights[n.state] += score
                if score > strongest_score:
                    strongest_score = score
                    strongest = n
        best_kind = 0
        best_weight = 0
        for k in range(1, 5):
            if weights[k] > best_weight:
                best_weight = weights[k]
                best_kind = k
        return best_kind, best_weight, strongest

    def differentiate(self, kind=None, source_cell=None):
        if self.state != 0:
            return False

        if kind is None or kind == 0:
            best_kind, _, source = self.dominant_neighbor_kind()
            if best_kind != 0:
                kind = best_kind
                source_cell = source
            else:
                kind = random.randint(1, 4)

        self.state = kind
        self.changed_t = sim_time
        self.source_index = source_cell.index if source_cell is not None else None
        self.delete_extra_visuals()

        c = TYPE_COLORS[kind]
        self.body.visible = True
        self.body.color = c
        self.body.opacity = 0.86
        self.body.shininess = 0.55
        self.body.radius = self.radius

        if kind == 1:
            self.axis = rand_unit()
            self.body.size = vector(self.radius * 3.4, self.radius * 1.25, self.radius * 1.25)
            self.body.axis = self.axis * self.radius * 3.4
            self.marker = cylinder(
                pos=self.pos - self.axis * self.radius * 2.0,
                axis=self.axis * self.radius * 4.0,
                radius=self.radius * 0.115,
                color=soft_mix(c, color.white, 0.33),
                opacity=0.38,
            )
        elif kind == 2:
            self.axis = rand_unit()
            self.body.size = vector(self.radius * 1.55, self.radius * 2.8, self.radius * 1.55)
            self.body.axis = self.axis * self.radius * 1.55
            self.marker = torus(
                pos=self.pos,
                axis=self.axis,
                radius=self.radius * 1.25,
                thickness=self.radius * 0.09,
                color=soft_mix(c, color.white, 0.22),
                opacity=0.67,
            )
        elif kind == 3:
            self.body.visible = False
            self.axis = rand_unit()
            self.alt = box(
                pos=self.pos,
                axis=self.axis,
                size=vector(self.radius * 2.15, self.radius * 2.15, self.radius * 0.95),
                color=c,
                opacity=0.84,
                shininess=0.4,
            )
            self.marker = torus(
                pos=self.pos,
                axis=self.axis,
                radius=self.radius * 1.25,
                thickness=self.radius * 0.045,
                color=soft_mix(c, color.white, 0.30),
                opacity=0.44,
            )
        elif kind == 4:
            self.body.size = vector(self.radius * 1.85, self.radius * 1.85, self.radius * 1.85)
            self.marker = torus(
                pos=self.pos,
                axis=rand_unit(),
                radius=self.radius * 1.13,
                thickness=self.radius * 0.075,
                color=soft_mix(c, color.white, 0.18),
                opacity=0.66,
            )
            for i in range(3):
                orb = sphere(
                    pos=self.pos + rand_unit() * self.radius * 1.4,
                    radius=self.radius * 0.16,
                    color=soft_mix(c, color.white, 0.35),
                    opacity=0.75,
                    emissive=True,
                )
                self.small_orbiters.append(orb)

        if source_cell is not None:
            line = curve(
                pos=[source_cell.pos, self.pos],
                color=soft_mix(TYPE_COLORS[kind], color.white, 0.18),
                radius=0.014,
            )
            branches.append(line)

        halo = sphere(
            pos=self.pos,
            radius=self.radius * 2.15,
            color=soft_mix(TYPE_COLORS[kind], color.white, 0.38),
            opacity=0.22,
            shininess=0,
        )
        decorations.append(Transient(halo, ttl=1.2, fade=True))

        spill_signals(self.pos, kind, count=random.randint(3, 6), speed=0.38, inherited=True)
        return True

    def update(self, dt):
        if self.state == 0:
            self.exposure = [x * (1.0 - 0.12 * dt) for x in self.exposure]
            best_kind, influence, source = self.dominant_neighbor_kind()
            if best_kind != 0:
                probability = dt * min(0.32, 0.008 + influence * 0.018)
                probability *= 0.7 + 0.7 * random.random()
                if random.random() < probability:
                    self.differentiate(best_kind, source_cell=source)

            p = 0.035 * math.sin(sim_time * 1.8 + self.pulse_phase)
            self.body.radius = self.radius * (1.0 + p)
            self.body.opacity = 0.50 + 0.08 * math.sin(sim_time * 1.3 + self.pulse_phase)
        else:
            if self.marker is not None:
                try:
                    self.marker.rotate(angle=dt * (0.35 + 0.10 * self.state), axis=self.spin_axis, origin=self.pos)
                except Exception:
                    pass
            if self.alt is not None:
                try:
                    self.alt.rotate(angle=dt * 0.18, axis=self.axis, origin=self.pos)
                except Exception:
                    pass
            if self.small_orbiters:
                for i, orb in enumerate(self.small_orbiters):
                    a = sim_time * (1.2 + 0.25 * i) + i * 2.1
                    u, v = make_basis(self.axis)
                    orb.pos = self.pos + (math.cos(a) * u + math.sin(a) * v) * self.radius * (1.35 + 0.12 * i)

            if random.random() < dt * 0.012:
                spill_signals(self.pos, self.state, count=1, speed=0.26, inherited=True)


class Signal:
    def __init__(self, pos, kind=None, vel=None, radius=0.067, parent=None):
        self.pos = vector(pos)
        self.kind = kind if kind is not None else random.randint(1, 4)
        self.vel = vector(vel) if vel is not None else rand_unit() * random.uniform(0.22, 0.65)
        self.radius = radius
        self.attached = None
        self.attach_time = 0.0
        self.attach_limit = random.uniform(1.1, 2.8)
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.orbit_speed = random.choice([-1, 1]) * random.uniform(2.0, 4.8)
        self.orbit_axis = rand_unit()
        self.orbit_u, self.orbit_v = make_basis(self.orbit_axis)
        self.parent = parent
        self.age = 0.0
        self.dead = False
        self.visual = sphere(
            pos=self.pos,
            radius=self.radius,
            color=TYPE_COLORS[self.kind],
            emissive=True,
            opacity=0.88,
            make_trail=True,
            retain=55,
            trail_radius=self.radius * 0.28,
            trail_color=soft_mix(TYPE_COLORS[self.kind], color.white, 0.18),
        )

    def destroy(self):
        self.dead = True
        try:
            self.visual.clear_trail()
        except Exception:
            pass
        safe_visible_false(self.visual)

    def attach_to(self, cell):
        self.attached = cell
        self.attach_time = 0.0
        self.attach_limit = random.uniform(0.7, 2.2)
        self.orbit_axis = rand_unit()
        self.orbit_u, self.orbit_v = make_basis(self.orbit_axis)
        self.orbit_angle = random.uniform(0, 2 * math.pi)
        self.visual.radius = self.radius * 0.92

    def detach(self, kick=None):
        if self.attached is None:
            return
        tangent = -math.sin(self.orbit_angle) * self.orbit_u + math.cos(self.orbit_angle) * self.orbit_v
        self.vel = tangent * random.uniform(0.28, 0.78) + rand_unit() * random.uniform(0.05, 0.22)
        if kick is not None:
            self.vel += kick
        self.attached = None
        self.attach_time = 0.0
        self.visual.radius = self.radius

    def update(self, dt):
        self.age += dt
        self.visual.color = TYPE_COLORS[self.kind]

        if self.age > 55 and random.random() < dt * 0.2:
            self.destroy()
            return

        if self.attached is not None:
            cell = self.attached
            self.attach_time += dt
            self.orbit_angle += self.orbit_speed * dt
            r = cell.visual_radius() + self.radius * 2.1
            self.pos = cell.pos + (math.cos(self.orbit_angle) * self.orbit_u + math.sin(self.orbit_angle) * self.orbit_v) * r
            self.visual.pos = self.pos
            cell.receive_signal(self.kind, dt * 0.84)

            if cell.state != 0 and random.random() < dt * 0.08:
                self.kind = cell.state

            if self.attach_time > self.attach_limit or random.random() < dt * 0.035:
                self.detach()
            return

        turbulence = vector(
            math.sin(sim_time * 1.7 + self.pos.y * 2.1),
            math.cos(sim_time * 1.3 + self.pos.z * 2.3),
            math.sin(sim_time * 1.1 + self.pos.x * 2.4),
        ) * 0.035

        if ai is not None and ai.enabled and not ai.is_quiet():
            to_cursor = ai.cursor_pos - self.pos
            d = mag(to_cursor)
            if d > 0.08:
                self.vel += norm(to_cursor) * ai.attractor_strength * dt / max(0.6, d)

        self.vel += turbulence * dt
        self.vel = clamp_mag(self.vel, 1.65)
        self.pos += self.vel * dt

        dcenter = mag(self.pos)
        if dcenter > BOUND_RADIUS:
            n = norm(self.pos)
            self.pos = n * BOUND_RADIUS
            self.vel = self.vel - 2 * dot(self.vel, n) * n
            self.vel *= 0.78

        self.visual.pos = self.pos

        if random.random() < 0.92:
            nearest = None
            nearest_d = 999
            for cell in cells:
                d = mag(cell.pos - self.pos)
                if d < nearest_d:
                    nearest_d = d
                    nearest = cell
            if nearest is not None and nearest_d < nearest.visual_radius() + self.radius * 1.8:
                if nearest.state == 0:
                    if random.random() < 0.72:
                        self.attach_to(nearest)
                    else:
                        n = norm(self.pos - nearest.pos) if mag(self.pos - nearest.pos) > 0.001 else rand_unit()
                        self.vel = self.vel - 2 * dot(self.vel, n) * n
                        self.vel *= 0.65
                        nearest.receive_signal(self.kind, 0.20)
                else:
                    if random.random() < 0.35:
                        self.kind = nearest.state
                    n = norm(self.pos - nearest.pos) if mag(self.pos - nearest.pos) > 0.001 else rand_unit()
                    self.vel = self.vel - 2 * dot(self.vel, n) * n + n * 0.12


def nearest_changed_cell(pos, max_distance=1.2):
    best = None
    best_d = max_distance
    for c in cells:
        if c.state != 0:
            d = mag(c.pos - pos)
            if d < best_d:
                best_d = d
                best = c
    return best


def frontier_cells():
    f = []
    for c in cells:
        if c.state == 0:
            for n in c.neighbors:
                if n.state != 0:
                    f.append(c)
                    break
    return f


def undifferentiated_cells():
    return [c for c in cells if c.state == 0]


def differentiated_cells():
    return [c for c in cells if c.state != 0]


def spill_signals(pos, kind, count=5, speed=0.45, inherited=False):
    if len(signals) >= MAX_SIGNALS:
        trim_signals(len(signals) - MAX_SIGNALS + count)
    for i in range(count):
        k = kind if inherited or random.random() < 0.7 else random.randint(1, 4)
        p = pos + rand_unit() * random.uniform(0.05, 0.28)
        v = rand_unit() * random.uniform(speed * 0.45, speed * 1.35)
        signals.append(Signal(p, kind=k, vel=v, radius=random.uniform(0.045, 0.075)))


def spawn_signal_burst(center=None, count=12, kind=None, radius=0.45, inward_target=None, speed=0.72):
    if center is None:
        center = random_shell(BOUND_RADIUS * 0.72)
    if len(signals) + count > MAX_SIGNALS:
        trim_signals(len(signals) + count - MAX_SIGNALS)

    for i in range(count):
        p = center + random_in_sphere(radius)
        k = kind if kind is not None else random.randint(1, 4)
        if inward_target is not None:
            direction = norm(inward_target - p) if mag(inward_target - p) > 0.01 else rand_unit()
            v = direction * random.uniform(speed * 0.65, speed * 1.25) + rand_unit() * random.uniform(0, speed * 0.25)
        else:
            v = rand_unit() * random.uniform(speed * 0.35, speed * 1.05)
        signals.append(Signal(p, kind=k, vel=v))


def trim_signals(count):
    count = max(0, min(count, len(signals)))
    for i in range(count):
        s = signals.pop(0)
        s.destroy()


def detach_all_signals(kick_strength=0.22):
    for s in signals:
        if s.attached is not None:
            s.detach(rand_unit() * kick_strength)


def chaos_kick():
    for s in signals:
        s.detach(rand_unit() * 0.35)
        s.vel += rand_unit() * random.uniform(0.45, 1.05)
    for i in range(4):
        spawn_signal_burst(
            center=random_shell(BOUND_RADIUS * 0.95),
            count=5,
            kind=random.randint(1, 4),
            radius=0.18,
            inward_target=random_in_sphere(1.7),
            speed=1.1,
        )


def mark_cell(cell, col=None, ttl=1.4):
    if cell is None:
        return
    col = col if col is not None else color.white
    ring = torus(
        pos=cell.pos,
        axis=rand_unit(),
        radius=cell.visual_radius() * 1.35,
        thickness=0.013,
        color=col,
        opacity=0.48,
    )
    decorations.append(Transient(ring, ttl=ttl, fade=True, spin=random.choice([-1, 1]) * random.uniform(0.5, 1.8)))


def update_decorations(dt):
    for d in decorations[:]:
        d.update(dt)
        if d.dead:
            decorations.remove(d)


def mix_and_collide_signals():
    limit = min(len(signals), 120)
    for i in range(limit):
        a = signals[i]
        if a.dead or a.attached is not None:
            continue
        for j in range(i + 1, limit):
            b = signals[j]
            if b.dead or b.attached is not None:
                continue
            delta = a.pos - b.pos
            d = mag(delta)
            if d < (a.radius + b.radius) * 1.65 and d > 1e-5:
                n = norm(delta)
                av = dot(a.vel, n)
                bv = dot(b.vel, n)
                a.vel += (bv - av) * n * 0.62
                b.vel += (av - bv) * n * 0.62
                if random.random() < 0.08:
                    if random.random() < 0.5:
                        a.kind = b.kind
                    else:
                        b.kind = a.kind


def generate_cluster_positions(n, radius):
    pts = []
    min_d = CELL_RADIUS * 2.05
    attempts = 0
    while len(pts) < n and attempts < 70000:
        attempts += 1
        p = random_in_sphere(radius)
        p.y *= 0.88
        ok = True
        for q in pts:
            if mag(p - q) < min_d:
                ok = False
                break
        if ok:
            pts.append(p)
        if attempts == 35000 and len(pts) < n * 0.75:
            min_d *= 0.94
    while len(pts) < n:
        pts.append(random_in_sphere(radius * 0.96))
    return pts


def build_neighbor_graph():
    for c in cells:
        c.neighbors = []
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            if mag(cells[i].pos - cells[j].pos) < NEIGHBOR_DISTANCE:
                cells[i].neighbors.append(cells[j])
                cells[j].neighbors.append(cells[i])


def clear_world_objects():
    global cells, signals, branches, decorations, boundary

    for s in signals:
        s.destroy()
    signals = []

    for c in cells:
        c.destroy()
    cells = []

    for b in branches:
        safe_visible_false(b)
    branches = []

    for d in decorations:
        safe_visible_false(d.obj)
    decorations = []

    if boundary is not None:
        safe_visible_false(boundary)
        boundary = None


def reset_world(loop_round=True):
    global cells, signals, branches, decorations, boundary, sim_time, round_number

    clear_world_objects()
    if loop_round:
        round_number += 1
    sim_time = 0.0

    boundary = sphere(
        pos=vector(0, 0, 0),
        radius=BOUND_RADIUS,
        color=vector(0.70, 0.88, 1.0),
        opacity=0.055,
        shininess=0.0,
    )

    shell1 = torus(
        pos=vector(0, 0, 0),
        axis=vector(0, 1, 0),
        radius=BOUND_RADIUS,
        thickness=0.006,
        color=vector(0.60, 0.82, 1.0),
        opacity=0.25,
    )
    shell2 = torus(
        pos=vector(0, 0, 0),
        axis=vector(1, 0, 0),
        radius=BOUND_RADIUS,
        thickness=0.006,
        color=vector(0.60, 0.82, 1.0),
        opacity=0.19,
    )
    decorations.append(Transient(shell1, ttl=999999, fade=False, spin=0.018))
    decorations.append(Transient(shell2, ttl=999999, fade=False, spin=-0.014))

    pts = generate_cluster_positions(CELL_COUNT, CLUSTER_RADIUS)
    for i, p in enumerate(pts):
        cells.append(Cell(i, p))
    build_neighbor_graph()

    for i in range(10):
        spawn_signal_burst(
            center=random_shell(BOUND_RADIUS * random.uniform(0.55, 0.86)),
            count=1,
            kind=random.randint(1, 4),
            radius=0.05,
            inward_target=random_in_sphere(1.8),
            speed=random.uniform(0.45, 0.9),
        )

    if ai is not None:
        ai.on_world_reset()


class AIController:
    def __init__(self):
        self.enabled = True
        self.mode = "SEED"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.mode_duration = 7.0
        self.action_timer = 0.0
        self.round_timer = 0.0
        self.quiet_timer = 0.0
        self.stable_timer = 0.0
        self.last_changed_count = 0
        self.last_branch_count = 0
        self.completion_delay = 0.0
        self.attractor_strength = 0.16
        self.cursor_pos = vector(0, 0, 0)
        self.cursor_phase = random.uniform(0, 10)
        self.history = []
        self.loop_pause = 2.8

        self.cursor = sphere(
            pos=self.cursor_pos,
            radius=0.13,
            color=vector(0.38, 0.62, 1.0),
            opacity=0.28,
            emissive=True,
        )
        self.cursor_ring = torus(
            pos=self.cursor_pos,
            axis=vector(0, 1, 0),
            radius=0.32,
            thickness=0.012,
            color=vector(0.38, 0.62, 1.0),
            opacity=0.35,
        )

    def is_quiet(self):
        return self.quiet_timer > 0

    def human_override(self, seconds=4.0):
        self.quiet_timer = max(self.quiet_timer, seconds)

    def on_world_reset(self):
        self.mode = "SEED"
        self.previous_mode = None
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.round_timer = 0.0
        self.quiet_timer = 0.5
        self.stable_timer = 0.0
        self.last_changed_count = 0
        self.last_branch_count = 0
        self.completion_delay = 0.0
        self.cursor_phase = random.uniform(0, 10)
        self.set_mode("SEED", duration=5.5)

    def force_next_mode(self):
        modes = ["SCOUT", "SEED", "AMPLIFY", "WEAVE", "WRAP", "CURATE", "CHAOS", "REST"]
        idx = modes.index(self.mode) if self.mode in modes else -1
        self.set_mode(modes[(idx + 1) % len(modes)], duration=random.uniform(5.0, 8.5))

    def set_mode(self, mode, duration=None):
        if mode == self.mode and mode != "RESETTING":
            return
        self.previous_mode = self.mode
        self.mode = mode
        self.mode_timer = 0.0
        self.action_timer = 0.0
        self.mode_duration = duration if duration is not None else random.uniform(5.5, 10.5)
        self.history.append(mode)
        if len(self.history) > 8:
            self.history.pop(0)

        mode_col = {
            "SCOUT": vector(0.30, 0.55, 1.00),
            "SEED": vector(1.00, 0.78, 0.22),
            "AMPLIFY": vector(0.32, 0.94, 0.48),
            "WEAVE": vector(0.72, 0.42, 1.00),
            "WRAP": vector(0.25, 0.85, 1.00),
            "CURATE": vector(1.00, 0.52, 0.62),
            "CHAOS": vector(1.00, 0.25, 0.18),
            "REST": vector(0.70, 0.78, 0.82),
            "RESETTING": vector(1.00, 1.00, 1.00),
        }.get(mode, color.white)
        self.cursor.color = mode_col
        self.cursor_ring.color = mode_col

    def read_state(self):
        counts = [0, 0, 0, 0, 0]
        for c in cells:
            counts[c.state] += 1
        free_count = sum(1 for s in signals if s.attached is None)
        attached_count = len(signals) - free_count
        f = frontier_cells()
        diff = CELL_COUNT - counts[0]
        completion = diff / max(1, CELL_COUNT)
        return {
            "counts": counts,
            "undiff": counts[0],
            "diff": diff,
            "completion": completion,
            "frontier": f,
            "frontier_count": len(f),
            "free_signals": free_count,
            "attached_signals": attached_count,
            "signal_count": len(signals),
            "branch_count": len(branches),
        }

    def detect_stagnation_or_completion(self, st, dt):
        changed_now = st["diff"]
        branch_now = st["branch_count"]

        if changed_now == self.last_changed_count and branch_now == self.last_branch_count:
            self.stable_timer += dt
        else:
            self.stable_timer = 0.0
            self.last_changed_count = changed_now
            self.last_branch_count = branch_now

        complete = st["completion"] >= 0.985 or st["undiff"] <= 1
        empty_or_stable = self.stable_timer > 15.5 and st["diff"] > 4
        no_start = self.stable_timer > 10.0 and st["diff"] == 0 and st["signal_count"] < 6
        too_empty = st["signal_count"] == 0 and self.stable_timer > 7.0

        return complete or empty_or_stable or no_start or too_empty

    def choose_next_mode(self, st):
        if st["diff"] == 0:
            return "SEED"
        if st["signal_count"] > MAX_SIGNALS * 0.72:
            return random.choice(["CURATE", "REST", "WEAVE"])
        if st["frontier_count"] > 18 and st["completion"] < 0.78:
            return random.choice(["AMPLIFY", "WEAVE", "CURATE"])
        if st["completion"] > 0.82:
            return random.choice(["CURATE", "WRAP", "REST"])
        if self.mode == "REST":
            return random.choice(["SCOUT", "WRAP", "AMPLIFY"])
        choices = ["SCOUT", "SEED", "AMPLIFY", "WEAVE", "WRAP", "CURATE", "CHAOS", "REST"]
        weights = {
            "SCOUT": 1.2,
            "SEED": 0.85,
            "AMPLIFY": 1.4,
            "WEAVE": 1.1,
            "WRAP": 0.95,
            "CURATE": 1.1,
            "CHAOS": 0.38,
            "REST": 0.55,
        }
        if self.previous_mode in weights:
            weights[self.previous_mode] *= 0.35
        if self.mode in weights:
            weights[self.mode] *= 0.15
        total = sum(weights[m] for m in choices)
        r = random.random() * total
        accum = 0
        for m in choices:
            accum += weights[m]
            if r <= accum:
                return m
        return "SCOUT"

    def update_cursor(self, dt, st):
        self.cursor_phase += dt
        t = self.cursor_phase

        if self.mode == "SCOUT":
            self.cursor_pos = vector(
                math.cos(t * 0.72) * 2.5,
                math.sin(t * 1.1) * 1.35,
                math.sin(t * 0.72) * 2.5,
            )
            self.attractor_strength = 0.10
        elif self.mode == "SEED":
            pale = undifferentiated_cells()
            if pale and int(t * 2.0) % 2 == 0:
                target = random.choice(pale).pos
                self.cursor_pos = soft_mix(self.cursor_pos, target, min(1, dt * 1.7))
            else:
                self.cursor_pos = vector(math.cos(t) * 0.8, math.sin(t * 0.7) * 0.5, math.sin(t) * 0.8)
            self.attractor_strength = 0.20
        elif self.mode == "AMPLIFY":
            f = st["frontier"]
            if f:
                target = random.choice(f).pos
                self.cursor_pos = soft_mix(self.cursor_pos, target, min(1, dt * 2.4))
            self.attractor_strength = 0.30
        elif self.mode == "WEAVE":
            self.cursor_pos = vector(
                math.cos(t * 1.3) * (1.2 + 0.9 * math.sin(t * 0.21)),
                math.sin(t * 1.7) * 1.05,
                math.sin(t * 1.3) * (1.2 + 0.9 * math.cos(t * 0.24)),
            )
            self.attractor_strength = 0.22
        elif self.mode == "WRAP":
            self.cursor_pos = vector(math.cos(t * 0.9) * 3.4, math.sin(t * 0.55) * 1.3, math.sin(t * 0.9) * 3.4)
            self.attractor_strength = 0.08
        elif self.mode == "CURATE":
            under = self.underrepresented_kind(st)
            candidates = [c for c in st["frontier"] if c.dominant_neighbor_kind()[0] != under]
            if not candidates:
                candidates = st["frontier"] or undifferentiated_cells()
            if candidates:
                self.cursor_pos = soft_mix(self.cursor_pos, random.choice(candidates).pos, min(1, dt * 1.8))
            self.attractor_strength = 0.24
        elif self.mode == "CHAOS":
            self.cursor_pos = random_in_sphere(2.8) if random.random() < dt * 5 else self.cursor_pos
            self.attractor_strength = -0.05
        elif self.mode == "REST":
            self.cursor_pos = vector(math.cos(t * 0.2) * 1.1, 1.8 + 0.2 * math.sin(t), math.sin(t * 0.2) * 1.1)
            self.attractor_strength = 0.02
        elif self.mode == "RESETTING":
            self.cursor_pos = vector(0, 0, 0)
            self.attractor_strength = 0.0

        self.cursor.pos = self.cursor_pos
        self.cursor_ring.pos = self.cursor_pos
        try:
            self.cursor_ring.rotate(angle=dt * 1.5, axis=vector(0, 1, 0), origin=self.cursor_pos)
        except Exception:
            pass

    def underrepresented_kind(self, st):
        counts = st["counts"]
        best = 1
        best_count = counts[1]
        for k in range(2, 5):
            if counts[k] < best_count:
                best_count = counts[k]
                best = k
        return best

    def action_seed(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.35, 0.78)

        pale = undifferentiated_cells()
        if not pale:
            return
        target = random.choice(pale)
        kind = random.randint(1, 4)
        if random.random() < 0.5:
            under = self.underrepresented_kind(st)
            kind = under
        start = target.pos + rand_unit() * random.uniform(0.55, 1.3)
        spawn_signal_burst(center=start, count=random.randint(2, 5), kind=kind, radius=0.13, inward_target=target.pos, speed=0.75)
        mark_cell(target, TYPE_COLORS[kind], ttl=1.0)

    def action_scout(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.55, 1.1)
        if random.random() < 0.65:
            spawn_signal_burst(
                center=self.cursor_pos + rand_unit() * 0.18,
                count=random.randint(1, 3),
                kind=random.randint(1, 4),
                radius=0.08,
                inward_target=random_in_sphere(1.4),
                speed=0.55,
            )
        if st["frontier"]:
            mark_cell(random.choice(st["frontier"]), vector(0.55, 0.75, 1.0), ttl=0.9)

    def action_amplify(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.18, 0.42)
        f = st["frontier"]
        if not f:
            self.action_seed(st, dt)
            return
        target = random.choice(f)
        kind, _, src = target.dominant_neighbor_kind()
        if kind == 0:
            kind = random.randint(1, 4)
        start = target.pos + rand_unit() * random.uniform(0.45, 0.95)
        spawn_signal_burst(center=start, count=random.randint(1, 3), kind=kind, radius=0.08, inward_target=target.pos, speed=0.82)
        if src is not None and random.random() < 0.45:
            mark_cell(src, TYPE_COLORS[kind], ttl=0.7)
            mark_cell(target, soft_mix(TYPE_COLORS[kind], color.white, 0.3), ttl=0.9)

    def action_weave(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.35, 0.72)
        changed = differentiated_cells()
        f = st["frontier"]
        if not changed or not f:
            self.action_seed(st, dt)
            return
        src = random.choice(changed)
        target = min(f, key=lambda c: mag(c.pos - src.pos) + random.random() * 0.6)
        kind = src.state
        mid = (src.pos + target.pos) * 0.5 + rand_unit() * 0.12
        ribbon = curve(
            pos=[src.pos, mid, target.pos],
            color=soft_mix(TYPE_COLORS[kind], color.white, 0.38),
            radius=0.008,
        )
        decorations.append(Transient(ribbon, ttl=2.0, fade=False))
        spawn_signal_burst(center=mid, count=random.randint(2, 4), kind=kind, radius=0.12, inward_target=target.pos, speed=0.67)
        mark_cell(target, TYPE_COLORS[kind], ttl=1.1)

    def action_wrap(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.25, 0.55)
        kind = random.randint(1, 4)
        if st["frontier"]:
            tcell = random.choice(st["frontier"])
            nk, _, _ = tcell.dominant_neighbor_kind()
            if nk:
                kind = nk
            target = tcell.pos
        else:
            target = random_in_sphere(1.5)
        p = random_shell(BOUND_RADIUS * 0.95, thickness=0.04)
        tangent = norm(cross(norm(p), vector(0, 1, 0))) if mag(cross(norm(p), vector(0, 1, 0))) > 0.02 else rand_unit()
        inward = norm(target - p)
        vel = tangent * random.uniform(0.45, 0.75) + inward * random.uniform(0.30, 0.60)
        signals.append(Signal(p, kind=kind, vel=vel, radius=random.uniform(0.048, 0.07)))

    def action_curate(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.42, 0.88)

        under = self.underrepresented_kind(st)
        f = st["frontier"] or undifferentiated_cells()
        if f:
            target = random.choice(f)
            spawn_signal_burst(
                center=target.pos + rand_unit() * random.uniform(0.5, 1.0),
                count=random.randint(1, 3),
                kind=under,
                radius=0.10,
                inward_target=target.pos,
                speed=0.55,
            )
            mark_cell(target, TYPE_COLORS[under], ttl=1.0)

        if len(signals) > MAX_SIGNALS * 0.78:
            trim_signals(random.randint(4, 9))

        if random.random() < 0.3:
            detach_all_signals(kick_strength=0.08)

    def action_chaos(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(0.55, 1.4)
        chaos_kick()
        if st["frontier"] and random.random() < 0.7:
            random.choice(st["frontier"]).receive_signal(random.randint(1, 4), random.uniform(0.25, 0.55))

    def action_rest(self, st, dt):
        self.action_timer -= dt
        if self.action_timer > 0:
            return
        self.action_timer = random.uniform(1.2, 2.6)
        if st["signal_count"] < 8 and st["undiff"] > 0:
            self.action_seed(st, dt)
        elif st["frontier"] and random.random() < 0.35:
            mark_cell(random.choice(st["frontier"]), vector(0.8, 0.9, 1.0), ttl=1.1)

    def update(self, dt):
        if not self.enabled:
            self.cursor.opacity = 0.08
            self.cursor_ring.opacity = 0.08
            return

        self.cursor.opacity = 0.28
        self.cursor_ring.opacity = 0.35

        self.round_timer += dt
        self.mode_timer += dt
        if self.quiet_timer > 0:
            self.quiet_timer -= dt

        st = self.read_state()
        self.update_cursor(dt, st)

        halted = self.detect_stagnation_or_completion(st, dt)
        if halted and self.mode != "RESETTING":
            self.set_mode("RESETTING", duration=self.loop_pause)
            self.completion_delay = 0.0

        if self.mode == "RESETTING":
            self.completion_delay += dt
            if self.completion_delay < 0.15:
                label(
                    pos=vector(0, 3.95, 0),
                    text="pattern complete — reseeding new round",
                    color=vector(0.33, 0.50, 0.70),
                    box=False,
                    opacity=0,
                    height=14,
                )
            if self.completion_delay >= self.loop_pause:
                reset_world(loop_round=True)
            return

        if self.mode_timer > self.mode_duration:
            self.set_mode(self.choose_next_mode(st), duration=random.uniform(5.0, 10.5))

        if self.is_quiet():
            return

        if self.mode == "SCOUT":
            self.action_scout(st, dt)
        elif self.mode == "SEED":
            self.action_seed(st, dt)
        elif self.mode == "AMPLIFY":
            self.action_amplify(st, dt)
        elif self.mode == "WEAVE":
            self.action_weave(st, dt)
        elif self.mode == "WRAP":
            self.action_wrap(st, dt)
        elif self.mode == "CURATE":
            self.action_curate(st, dt)
        elif self.mode == "CHAOS":
            self.action_chaos(st, dt)
        elif self.mode == "REST":
            self.action_rest(st, dt)


def manual_feed_frontier():
    f = frontier_cells()
    if not f:
        f = undifferentiated_cells()
    if not f:
        return
    for i in range(7):
        target = random.choice(f)
        k, _, _ = target.dominant_neighbor_kind()
        if k == 0:
            k = random.randint(1, 4)
        spawn_signal_burst(
            center=target.pos + rand_unit() * random.uniform(0.45, 1.0),
            count=2,
            kind=k,
            radius=0.09,
            inward_target=target.pos,
            speed=0.80,
        )
        mark_cell(target, TYPE_COLORS[k], ttl=1.1)


def keydown(evt):
    global paused
    key = evt.key.lower()

    if key == " ":
        paused = not paused
    elif key == "a":
        ai.enabled = not ai.enabled
    elif key == "r":
        reset_world(loop_round=True)
    elif key == "s":
        spawn_signal_burst(
            center=random_shell(BOUND_RADIUS * 0.75),
            count=16,
            kind=None,
            radius=0.32,
            inward_target=random_in_sphere(1.0),
            speed=0.9,
        )
        ai.human_override(2.0)
    elif key == "f":
        manual_feed_frontier()
        ai.human_override(2.5)
    elif key == "d":
        detach_all_signals(kick_strength=0.35)
        ai.human_override(2.0)
    elif key == "c":
        chaos_kick()
        ai.set_mode("CHAOS", duration=5.0)
        ai.human_override(0.7)
    elif key == "m":
        ai.force_next_mode()
    elif key == "h":
        ai.human_override(6.0)
    elif key in ["1", "2", "3", "4", "5", "6", "7", "8"]:
        modes = ["SCOUT", "SEED", "AMPLIFY", "WEAVE", "WRAP", "CURATE", "CHAOS", "REST"]
        ai.set_mode(modes[int(key) - 1], duration=8.0)


scene.bind("keydown", keydown)


def update_status_caption(force=False):
    global last_caption_update
    if not force and sim_time - last_caption_update < 0.25:
        return
    last_caption_update = sim_time
    counts = [0, 0, 0, 0, 0]
    for c in cells:
        counts[c.state] += 1
    attached = sum(1 for s in signals if s.attached is not None)
    ai_state = "ON" if ai.enabled else "OFF"
    quiet = " human override" if ai.quiet_timer > 0 else ""
    pause_text = "PAUSED" if paused else "running"

    scene.caption = (
        "\n"
        "Controls: SPACE pause | A AI on/off | R reset | S signal burst | F feed frontier | "
        "D detach | C chaos | M next AI mode | 1-8 force mode | H quiet AI\n"
        f"Round {round_number} | {pause_text} | AI {ai_state}: {ai.mode}{quiet} | "
        f"Signals {len(signals)} ({attached} attached) | Branches {len(branches)}\n"
        f"Cells: stem {counts[0]}  "
        f"<span style='color:rgb(40,100,230)'>blue {counts[1]}</span>  "
        f"<span style='color:rgb(230,60,80)'>rose {counts[2]}</span>  "
        f"<span style='color:rgb(40,170,90)'>green {counts[3]}</span>  "
        f"<span style='color:rgb(220,150,20)'>amber {counts[4]}</span>\n"
    )


reset_world(loop_round=False)
ai = AIController()
ai.on_world_reset()
update_status_caption(force=True)

dt = 1.0 / 60.0

while True:
    rate(60)
    frame_count += 1

    if paused:
        update_status_caption(force=False)
        continue

    sim_time += dt

    if ai is not None:
        ai.update(dt)

    for c in cells:
        c.update(dt)

    for s in signals[:]:
        s.update(dt)
        if s.dead:
            if s in signals:
                signals.remove(s)

    if frame_count % 8 == 0:
        mix_and_collide_signals()

    update_decorations(dt)

    if len(signals) > MAX_SIGNALS:
        trim_signals(len(signals) - MAX_SIGNALS)

    update_status_caption(force=False)
