from vpython import *
import random
import math

# Virus Entry into a Host Cell - VPython simulation with autonomous AI controller
# Controls:
#   P pause/resume     I AI on/off          R reset round
#   V select virus     W/A/S/D/Q/E move selected virus
#   B bind selected    F force injection    G force endocytosis
#   X detach selected  O orbit impulse      M mark nearest receptor
#   H toggle this help

scene = canvas(
    title="Virus Entry into a Host Cell - AI Controlled 3D Simulation",
    width=1180,
    height=760,
    background=vector(0.96, 0.985, 1.0),
    center=vector(0, 0, 0),
)
scene.forward = vector(-0.82, -0.34, -1.05)
scene.up = vector(0, 1, 0)
scene.camera.pos = vector(8, 7, 12)
scene.camera.axis = vector(-8, -7, -12)
scene.autoscale = False
scene.range = 9.5
scene.append_to_caption("\n")
status_text = wtext(text="")

# -----------------------------
# Global visual/simulation setup
# -----------------------------

HOST_R = 4.0
NUCLEUS_R = 1.05
VIRUS_R = 0.34
SPIKE_LEN = 0.27
RECEPTOR_COUNT = 22
VIRUS_COUNT = 10
MAX_PARTICLES = 180
DT = 0.030

PALE_BLUE = vector(0.55, 0.82, 1.00)
MEMBRANE_BLUE = vector(0.45, 0.72, 1.00)
NUCLEUS_COLOR = vector(0.67, 0.58, 0.95)
RECEPTOR_OPEN = vector(0.96, 0.58, 1.00)
RECEPTOR_OCCUPIED = vector(1.0, 0.70, 0.28)
RECEPTOR_USED = vector(0.55, 0.80, 0.55)
RECEPTOR_MARKED = vector(1.0, 0.92, 0.35)
VIRUS_COLORS = [
    vector(1.00, 0.42, 0.42),
    vector(1.00, 0.54, 0.70),
    vector(0.90, 0.48, 1.00),
    vector(1.00, 0.62, 0.38),
    vector(0.65, 0.62, 1.00),
]
SPIKE_COLOR = vector(1.00, 0.92, 0.28)
GENOME_COLORS = [
    vector(0.05, 1.00, 0.55),
    vector(0.00, 0.90, 1.00),
    vector(0.65, 1.00, 0.18),
    vector(1.00, 0.78, 0.12),
]
AI_MARK_COLOR = vector(1.0, 0.45, 0.1)

host_cell = None
nucleus = None
host_label = None
receptors = []
viruses = []
particles = []
loose_genomes = []
decorations = []
selected_index = 0
selection_marker = None
paused = False
show_help = True
sim_time = 0.0
event_count = 0
round_number = 1
keys_down = set()
human_override_until = 0.0
ai = None


# -----------------------------
# Utility functions
# -----------------------------

def randf(a, b):
    return a + random.random() * (b - a)


def random_unit():
    z = randf(-1, 1)
    t = randf(0, 2 * math.pi)
    r = math.sqrt(max(0, 1 - z * z))
    return vector(r * math.cos(t), z, r * math.sin(t))


def safe_norm(v, fallback=vector(1, 0, 0)):
    if mag(v) < 1e-8:
        return fallback
    return norm(v)


def limit_vec(v, m):
    if mag(v) > m:
        return safe_norm(v) * m
    return v


def reflect(v, n):
    n = safe_norm(n)
    return v - 2 * dot(v, n) * n


def fibonacci_sphere_points(n):
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / float(n - 1)) * 2 if n > 1 else 0
        radius = math.sqrt(max(0, 1 - y * y))
        theta = golden * i
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        pts.append(vector(x, y, z))
    return pts


def erase_obj(obj):
    if obj is not None:
        try:
            obj.visible = False
        except Exception:
            pass


def add_event():
    global event_count
    event_count += 1


# -----------------------------
# Simulation objects
# -----------------------------

class Receptor:
    def __init__(self, idx, normal_vec):
        self.idx = idx
        self.normal = safe_norm(normal_vec)
        self.pos = self.normal * (HOST_R * 1.012)
        self.docking_pos = self.normal * (HOST_R + VIRUS_R + 0.045)
        self.state = "open"
        self.marked = False
        self.occupied_by = None
        self.use_count = 0

        self.spot = sphere(
            pos=self.pos,
            radius=0.145,
            color=RECEPTOR_OPEN,
            shininess=0.8,
            emissive=False,
        )
        self.ring = ring(
            pos=self.pos + self.normal * 0.018,
            axis=self.normal,
            radius=0.255,
            thickness=0.018,
            color=vector(0.82, 0.38, 1.0),
            opacity=0.72,
        )
        self.marker = sphere(
            pos=self.pos + self.normal * 0.08,
            radius=0.055,
            color=RECEPTOR_MARKED,
            emissive=True,
            visible=False,
        )

    def set_state(self, state):
        self.state = state
        if state == "open":
            self.spot.color = RECEPTOR_MARKED if self.marked else RECEPTOR_OPEN
            self.ring.color = vector(0.82, 0.38, 1.0)
            self.ring.opacity = 0.72
        elif state == "occupied":
            self.spot.color = RECEPTOR_OCCUPIED
            self.ring.color = vector(1.0, 0.62, 0.18)
            self.ring.opacity = 0.95
        elif state == "used":
            self.spot.color = RECEPTOR_USED
            self.ring.color = vector(0.35, 0.76, 0.35)
            self.ring.opacity = 0.42

    def mark(self, playful=False):
        self.marked = True
        self.marker.visible = True
        self.marker.color = AI_MARK_COLOR if playful else RECEPTOR_MARKED
        if self.state == "open":
            self.spot.color = self.marker.color
        add_event()

    def unmark(self):
        self.marked = False
        self.marker.visible = False
        if self.state == "open":
            self.spot.color = RECEPTOR_OPEN

    def erase(self):
        erase_obj(self.spot)
        erase_obj(self.ring)
        erase_obj(self.marker)


class Particle:
    def __init__(self, pos, vel, col, radius=0.035, life=1.6):
        self.obj = sphere(
            pos=pos,
            radius=radius,
            color=col,
            opacity=0.78,
            emissive=True,
        )
        self.vel = vel
        self.life = life
        self.life0 = life

    def update(self, dt):
        self.life -= dt
        self.obj.pos += self.vel * dt
        self.vel *= 0.985
        self.obj.opacity = max(0, 0.78 * self.life / self.life0)
        return self.life > 0

    def erase(self):
        erase_obj(self.obj)


class GenomeFilament:
    def __init__(self, start_pos, direction, col=None, max_len=None, source_name="genome"):
        self.col = col if col is not None else random.choice(GENOME_COLORS)
        self.curve = curve(
            pos=[start_pos],
            radius=0.035,
            color=self.col,
            emissive=True,
        )
        self.tip = vector(start_pos)
        self.direction = safe_norm(direction, random_unit())
        self.max_len = max_len if max_len is not None else randf(1.8, 4.7)
        self.length = 0.0
        self.active = True
        self.source_name = source_name
        self.timer = 0.0
        self.branch_done = False
        self.pulse = sphere(
            pos=start_pos,
            radius=0.07,
            color=self.col,
            emissive=True,
            opacity=0.6,
        )

    def update(self, dt):
        if not self.active:
            self.pulse.opacity *= 0.985
            if self.pulse.opacity < 0.02:
                self.pulse.visible = False
            return False

        self.timer += dt
        self.pulse.radius = 0.065 + 0.025 * math.sin(10 * sim_time + self.length)
        self.pulse.pos = self.tip

        if self.timer >= 0.055:
            self.timer = 0.0
            inward_bias = safe_norm(-self.tip, random_unit())
            wandering = random_unit() * 0.65
            step_dir = safe_norm(self.direction * 0.75 + inward_bias * 0.35 + wandering)
            step_len = randf(0.055, 0.125)
            new_tip = self.tip + step_dir * step_len

            if mag(new_tip) > HOST_R - 0.28:
                new_tip = safe_norm(new_tip) * (HOST_R - 0.28)
                step_dir = safe_norm(-new_tip + random_unit() * 0.5)

            self.direction = safe_norm(step_dir * 0.8 + random_unit() * 0.2)
            self.curve.append(pos=new_tip)
            self.tip = new_tip
            self.length += step_len

            if self.length > self.max_len * 0.48 and not self.branch_done and random.random() < 0.28:
                self.branch_done = True
                loose_genomes.append(
                    GenomeFilament(
                        self.tip,
                        safe_norm(random_unit() + safe_norm(-self.tip) * 0.45),
                        col=self.col * 0.8 + vector(0.2, 0.2, 0.2),
                        max_len=self.max_len * randf(0.25, 0.45),
                        source_name="branch",
                    )
                )

            if self.length >= self.max_len:
                self.active = False
                add_event()

        return self.active

    def erase(self):
        erase_obj(self.curve)
        erase_obj(self.pulse)


class Virus:
    def __init__(self, idx):
        self.idx = idx
        self.color = VIRUS_COLORS[idx % len(VIRUS_COLORS)]
        self.state = "free"
        self.radius = VIRUS_R
        self.pos = random_unit() * randf(HOST_R + 5.8, HOST_R + 8.0)
        self.vel = safe_norm(-self.pos + random_unit() * 1.2) * randf(0.38, 0.78)
        self.target_receptor = None
        self.bound_receptor = None
        self.bound_time = 0.0
        self.decision_time = randf(1.7, 4.5)
        self.genomes = []
        self.vesicle = None
        self.wrap_ring = None
        self.tether = None
        self.orbiting = False
        self.injection_started = False
        self.endocytosis_started = False
        self.release_started = False
        self.spin_axis = random_unit()
        self.spin_rate = randf(-1.1, 1.1)
        self.spin_angle = randf(0, 2 * math.pi)

        self.body = sphere(
            pos=self.pos,
            radius=self.radius,
            color=self.color,
            opacity=0.92,
            shininess=0.75,
        )

        self.spike_dirs = fibonacci_sphere_points(14)
        self.spikes = []
        for d in self.spike_dirs:
            c = cone(
                pos=self.pos + d * (self.radius * 0.86),
                axis=d * SPIKE_LEN,
                radius=0.065,
                color=SPIKE_COLOR,
                shininess=0.55,
            )
            self.spikes.append(c)

        self.trail = curve(
            pos=[self.pos],
            radius=0.012,
            color=self.color * 0.65 + vector(0.25, 0.25, 0.25),
            opacity=0.38,
        )
        self.trail_timer = 0.0
        self.name_label = label(
            pos=self.pos + vector(0, 0.55, 0),
            text="V" + str(idx + 1),
            height=9,
            box=False,
            opacity=0,
            color=vector(0.25, 0.25, 0.35),
        )

    def set_pos(self, p):
        self.pos = vector(p)
        self.body.pos = self.pos
        self.name_label.pos = self.pos + vector(0, 0.55, 0)
        self.update_spikes(0)

    def set_visible_shell(self, visible=True):
        self.body.visible = visible
        self.name_label.visible = visible
        for s in self.spikes:
            s.visible = visible

    def update_spikes(self, dt):
        self.spin_angle += self.spin_rate * dt
        for i, d in enumerate(self.spike_dirs):
            rd = rotate(d, angle=self.spin_angle, axis=self.spin_axis)
            self.spikes[i].pos = self.pos + rd * (self.radius * 0.86)
            self.spikes[i].axis = rd * SPIKE_LEN

    def choose_target(self):
        open_recs = [r for r in receptors if r.state == "open"]
        if not open_recs:
            self.target_receptor = None
            return None
        open_recs.sort(key=lambda r: mag(self.pos - r.docking_pos) + r.use_count * 0.9 + (0.25 if r.marked else 0))
        self.target_receptor = random.choice(open_recs[:min(4, len(open_recs))])
        return self.target_receptor

    def bind_to(self, receptor):
        if self.state != "free" or receptor.state != "open":
            return False
        self.state = "bound"
        self.bound_receptor = receptor
        self.target_receptor = receptor
        receptor.occupied_by = self
        receptor.set_state("occupied")
        self.bound_time = 0.0
        self.decision_time = randf(1.3, 3.8)
        self.vel = vector(0, 0, 0)
        self.set_pos(receptor.docking_pos)
        self.tether = curve(
            pos=[self.pos - receptor.normal * self.radius * 0.65, receptor.pos],
            radius=0.018,
            color=vector(1.0, 0.74, 0.32),
            emissive=True,
        )
        create_particle_burst(receptor.pos, vector(1.0, 0.72, 0.18), count=12, speed=0.65)
        add_event()
        return True

    def detach(self, impulse=1.0):
        if self.state != "bound":
            return
        r = self.bound_receptor
        if r is not None:
            r.occupied_by = None
            r.set_state("open")
        erase_obj(self.tether)
        self.tether = None
        self.bound_receptor = None
        self.state = "free"
        outward = safe_norm(self.pos)
        self.vel = outward * randf(0.45, 0.75) * impulse + random_unit() * 0.25
        self.set_pos(outward * (HOST_R + VIRUS_R + 0.28))
        create_particle_burst(self.pos, vector(0.7, 0.8, 1.0), count=8, speed=0.55)
        add_event()

    def start_injection(self):
        if self.state != "bound" or self.injection_started:
            return False
        r = self.bound_receptor
        if r is None:
            return False
        self.state = "injecting"
        self.injection_started = True
        r.occupied_by = None
        r.use_count += 1
        r.set_state("used")
        erase_obj(self.tether)
        self.tether = None

        start = r.pos - r.normal * 0.16
        direction = -r.normal + random_unit() * 0.25
        self.genomes.append(
            GenomeFilament(
                start,
                direction,
                col=random.choice(GENOME_COLORS),
                max_len=randf(3.0, 5.2),
                source_name="injected genome",
            )
        )
        self.body.opacity = 0.62
        create_particle_burst(start, vector(0.05, 1.0, 0.45), count=18, speed=0.72)
        add_event()
        return True

    def start_endocytosis(self):
        if self.state != "bound" or self.endocytosis_started:
            return False
        r = self.bound_receptor
        if r is None:
            return False
        self.state = "endocytosed"
        self.endocytosis_started = True
        r.occupied_by = None
        r.use_count += 1
        r.set_state("used")
        erase_obj(self.tether)
        self.tether = None

        inside = r.normal * (HOST_R - 0.38)
        self.vesicle = sphere(
            pos=inside,
            radius=self.radius * 1.55,
            color=vector(0.62, 0.86, 1.0),
            opacity=0.30,
            shininess=0.85,
        )
        self.wrap_ring = ring(
            pos=r.pos - r.normal * 0.10,
            axis=r.normal,
            radius=0.38,
            thickness=0.045,
            color=vector(0.45, 0.75, 1.0),
            opacity=0.55,
        )
        self.body.opacity = 0.74
        self.set_pos(inside)
        create_particle_burst(r.pos, vector(0.35, 0.75, 1.0), count=20, speed=0.48)
        add_event()
        return True

    def release_from_vesicle(self):
        if self.release_started:
            return
        self.release_started = True
        self.state = "released"
        release_pos = self.pos
        for _ in range(random.randint(2, 3)):
            self.genomes.append(
                GenomeFilament(
                    release_pos + random_unit() * 0.1,
                    random_unit() + safe_norm(-release_pos) * 0.35,
                    col=random.choice(GENOME_COLORS),
                    max_len=randf(2.2, 4.5),
                    source_name="vesicle release",
                )
            )
        create_particle_burst(release_pos, vector(0.0, 0.92, 1.0), count=30, speed=0.8)
        self.body.opacity = 0.18
        for s in self.spikes:
            s.opacity = 0.20
        erase_obj(self.vesicle)
        erase_obj(self.wrap_ring)
        self.vesicle = None
        self.wrap_ring = None
        add_event()

    def force_orbit(self):
        radial = safe_norm(self.pos, random_unit())
        axis = vector(0, 1, 0)
        if abs(dot(radial, axis)) > 0.9:
            axis = vector(1, 0, 0)
        tangent = safe_norm(cross(axis, radial), random_unit())
        self.vel += tangent * 0.85
        self.orbiting = True
        add_event()

    def update_free(self, dt):
        if self.target_receptor is None or self.target_receptor.state != "open" or random.random() < 0.004:
            self.choose_target()

        accel = vector(0, 0, 0)
        if self.target_receptor is not None:
            target = self.target_receptor.docking_pos
            accel += safe_norm(target - self.pos) * 0.18
        else:
            desired_r = HOST_R + 2.8
            radial = safe_norm(self.pos, random_unit())
            accel += radial * ((desired_r - mag(self.pos)) * 0.035)

        accel += random_unit() * 0.027

        if self.orbiting:
            radial = safe_norm(self.pos, random_unit())
            tangent = safe_norm(cross(vector(0, 1, 0), radial), random_unit())
            accel += tangent * 0.19
            accel += radial * ((HOST_R + 2.2 - mag(self.pos)) * 0.055)

        self.vel += accel * dt * 12.0
        self.vel = limit_vec(self.vel, 1.35)
        self.set_pos(self.pos + self.vel * dt)

        for r in receptors:
            if r.state == "open" and mag(self.pos - r.docking_pos) < 0.30:
                self.bind_to(r)
                return

        dist = mag(self.pos)
        if dist < HOST_R + self.radius:
            n = safe_norm(self.pos, random_unit())
            nearest_open = None
            nearest_dist = 999
            for r in receptors:
                d = mag(self.pos - r.docking_pos)
                if r.state == "open" and d < nearest_dist:
                    nearest_dist = d
                    nearest_open = r
            if nearest_open is not None and nearest_dist < 0.62:
                self.bind_to(nearest_open)
                return
            self.set_pos(n * (HOST_R + self.radius + 0.03))
            self.vel = reflect(self.vel, n) * 0.62 + n * 0.12
            create_particle_burst(self.pos, vector(0.62, 0.86, 1.0), count=5, speed=0.25)

    def update_bound(self, dt):
        self.bound_time += dt
        if self.bound_receptor is not None:
            self.set_pos(self.bound_receptor.docking_pos)
        if self.bound_time > self.decision_time:
            if random.random() < 0.54:
                self.start_injection()
            else:
                self.start_endocytosis()

    def update_injecting(self, dt):
        still_active = False
        for g in self.genomes:
            if g.update(dt):
                still_active = True
        if not still_active and self.genomes:
            self.state = "released"
            self.body.opacity = 0.28
            add_event()

    def update_endocytosed(self, dt):
        if self.vesicle is None:
            return
        inward = safe_norm(-self.vesicle.pos, random_unit())
        wobble = random_unit() * 0.12
        speed = 0.46 + 0.11 * math.sin(sim_time * 1.8 + self.idx)
        newp = self.vesicle.pos + (inward * speed + wobble) * dt
        if mag(newp) < NUCLEUS_R + 0.55:
            newp = safe_norm(newp, random_unit()) * (NUCLEUS_R + 0.55)
        self.vesicle.pos = newp
        if self.wrap_ring is not None:
            self.wrap_ring.opacity *= 0.982
            if self.wrap_ring.opacity < 0.03:
                self.wrap_ring.visible = False
        self.set_pos(newp)
        if mag(newp) <= NUCLEUS_R + 0.72 or random.random() < 0.001:
            self.release_from_vesicle()

    def update_released(self, dt):
        for g in self.genomes:
            g.update(dt)
        self.spin_rate *= 0.995

    def update(self, dt):
        self.update_spikes(dt)

        if self.state == "free":
            self.update_free(dt)
        elif self.state == "bound":
            self.update_bound(dt)
        elif self.state == "injecting":
            self.update_injecting(dt)
        elif self.state == "endocytosed":
            self.update_endocytosed(dt)
        elif self.state == "released":
            self.update_released(dt)

        self.trail_timer += dt
        if self.trail_timer > 0.18 and self.state in ("free", "endocytosed"):
            self.trail_timer = 0.0
            self.trail.append(pos=self.pos)

    def erase(self):
        erase_obj(self.body)
        for s in self.spikes:
            erase_obj(s)
        erase_obj(self.trail)
        erase_obj(self.name_label)
        erase_obj(self.tether)
        erase_obj(self.vesicle)
        erase_obj(self.wrap_ring)
        for g in self.genomes:
            g.erase()


# -----------------------------
# Scene effects
# -----------------------------

def create_particle_burst(pos, col, count=12, speed=0.5):
    global particles
    for _ in range(count):
        if len(particles) >= MAX_PARTICLES:
            old = particles.pop(0)
            old.erase()
        particles.append(
            Particle(
                pos=pos + random_unit() * 0.045,
                vel=random_unit() * randf(0.08, speed),
                col=col * randf(0.72, 1.0) + vector(0.04, 0.04, 0.04),
                radius=randf(0.018, 0.05),
                life=randf(0.7, 1.9),
            )
        )


def create_loose_spill(pos=None, count=1, artistic=False):
    if pos is None:
        pos = random_unit() * randf(0.5, HOST_R - 0.7)
    for _ in range(count):
        col = random.choice(GENOME_COLORS)
        if artistic:
            col = vector(randf(0.0, 1.0), randf(0.65, 1.0), randf(0.25, 1.0))
        loose_genomes.append(
            GenomeFilament(
                pos + random_unit() * 0.15,
                random_unit() + safe_norm(-pos) * 0.25,
                col=col,
                max_len=randf(1.4, 3.2),
                source_name="AI spill",
            )
        )
    create_particle_burst(pos, random.choice(GENOME_COLORS), count=10 + 5 * count, speed=0.55)
    add_event()


def update_collisions():
    for i in range(len(viruses)):
        a = viruses[i]
        if a.state != "free":
            continue
        for j in range(i + 1, len(viruses)):
            b = viruses[j]
            if b.state != "free":
                continue
            delta = a.pos - b.pos
            d = mag(delta)
            min_d = (a.radius + b.radius) * 1.25
            if 0.001 < d < min_d:
                n = delta / d
                overlap = min_d - d
                a.set_pos(a.pos + n * overlap * 0.5)
                b.set_pos(b.pos - n * overlap * 0.5)
                rel = dot(a.vel - b.vel, n)
                if rel < 0:
                    impulse = -rel * 0.58
                    a.vel += n * impulse
                    b.vel -= n * impulse
                create_particle_burst((a.pos + b.pos) * 0.5, vector(1.0, 0.9, 0.3), count=3, speed=0.25)


# -----------------------------
# Expressive AI controller
# -----------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.mode_names = [
            "curious_probe",
            "careful_bind",
            "orbital_dance",
            "chaotic_stir",
            "injection_ritual",
            "endocytosis_wave",
            "artistic_spill",
            "cleanup_reset",
        ]
        self.mode = "curious_probe"
        self.mode_timer = 0.0
        self.mode_duration = 8.0
        self.history = []
        self.last_event_count = event_count
        self.last_signature = None
        self.last_change_time = 0.0
        self.completion_time = None
        self.reset_countdown = None
        self.playfulness = 0.45
        self.ritual_phase = 0.0
        self.last_spill_time = -99
        self.last_mark_time = -99

    def read_state(self):
        counts = {
            "free": 0,
            "bound": 0,
            "injecting": 0,
            "endocytosed": 0,
            "released": 0,
            "open_receptors": 0,
            "used_receptors": 0,
            "marked_receptors": 0,
            "active_genomes": 0,
        }
        for v in viruses:
            counts[v.state] = counts.get(v.state, 0) + 1
            for g in v.genomes:
                if g.active:
                    counts["active_genomes"] += 1
        for r in receptors:
            if r.state == "open":
                counts["open_receptors"] += 1
            if r.state == "used":
                counts["used_receptors"] += 1
            if r.marked:
                counts["marked_receptors"] += 1
        for g in loose_genomes:
            if g.active:
                counts["active_genomes"] += 1
        counts["event_count"] = event_count
        return counts

    def is_complete(self, state):
        if len(viruses) == 0:
            return True
        active_viruses = state["free"] + state["bound"] + state["injecting"] + state["endocytosed"]
        no_receptors = state["open_receptors"] == 0 and state["bound"] == 0
        all_released = state["released"] >= len(viruses)
        genomes_done = state["active_genomes"] == 0
        return (all_released and genomes_done) or (no_receptors and active_viruses == 0)

    def is_stagnant(self, state):
        signature = (
            state["free"],
            state["bound"],
            state["injecting"],
            state["endocytosed"],
            state["released"],
            state["open_receptors"],
            state["active_genomes"],
            state["event_count"],
        )
        if signature != self.last_signature:
            self.last_signature = signature
            self.last_change_time = sim_time
            return False
        return sim_time - self.last_change_time > 12.0

    def choose_mode(self, state):
        if self.is_complete(state) or self.is_stagnant(state):
            self.set_mode("cleanup_reset", duration=3.5)
            return

        possible = ["curious_probe", "careful_bind", "orbital_dance", "chaotic_stir"]
        if state["bound"] > 0:
            possible += ["injection_ritual", "endocytosis_wave"]
        if state["released"] > 0 or state["active_genomes"] > 1:
            possible += ["artistic_spill"]
        if state["open_receptors"] <= 2 and state["bound"] == 0:
            possible += ["artistic_spill"]

        recent = set(self.history[-2:])
        filtered = [m for m in possible if m not in recent]
        if not filtered:
            filtered = possible

        weights = []
        for m in filtered:
            w = 1.0
            if m == "careful_bind" and state["free"] > 0 and state["open_receptors"] > 0:
                w += 1.2
            if m == "injection_ritual" and state["bound"] > 0:
                w += 1.0
            if m == "endocytosis_wave" and state["bound"] > 1:
                w += 0.9
            if m == "chaotic_stir":
                w += self.playfulness
            if m == "artistic_spill":
                w += 0.8 if state["released"] > 0 else 0.1
            weights.append(w)

        total = sum(weights)
        pick = randf(0, total)
        acc = 0
        for m, w in zip(filtered, weights):
            acc += w
            if pick <= acc:
                self.set_mode(m, duration=randf(5.5, 11.5))
                return
        self.set_mode(random.choice(filtered), duration=randf(5.5, 11.5))

    def set_mode(self, mode, duration=None):
        if mode != self.mode:
            self.history.append(mode)
            if len(self.history) > 8:
                self.history.pop(0)
            create_particle_burst(vector(0, HOST_R + 0.75, 0), vector(1.0, 0.75, 0.25), count=10, speed=0.38)
        self.mode = mode
        self.mode_timer = 0.0
        self.mode_duration = duration if duration is not None else randf(6.0, 12.0)
        self.ritual_phase = randf(0, 2 * math.pi)

    def nudge(self, virus, target, strength=0.16, max_speed=1.15):
        if virus.state != "free":
            return
        desired = safe_norm(target - virus.pos) * max_speed
        virus.vel += (desired - virus.vel) * strength * DT * 4.0
        virus.vel = limit_vec(virus.vel, max_speed)

    def nearest_open_receptor(self, virus, prefer_marked=False):
        candidates = [r for r in receptors if r.state == "open"]
        if not candidates:
            return None
        candidates.sort(key=lambda r: mag(virus.pos - r.docking_pos) - (0.9 if prefer_marked and r.marked else 0))
        return candidates[0]

    def behavior_curious_probe(self, state):
        for v in viruses:
            if v.state == "free":
                r = self.nearest_open_receptor(v, prefer_marked=True)
                if r is not None:
                    v.target_receptor = r
                    offset = r.normal * (0.22 * math.sin(sim_time * 1.7 + v.idx))
                    self.nudge(v, r.docking_pos + offset, strength=0.10, max_speed=0.92)
        if sim_time - self.last_mark_time > 2.2 and state["open_receptors"] > 0:
            open_recs = [r for r in receptors if r.state == "open"]
            r = random.choice(open_recs)
            r.mark(playful=True)
            self.last_mark_time = sim_time

    def behavior_careful_bind(self, state):
        for v in viruses:
            if v.state == "free":
                r = self.nearest_open_receptor(v, prefer_marked=True)
                if r is not None:
                    v.target_receptor = r
                    self.nudge(v, r.docking_pos, strength=0.24, max_speed=0.75)
                    if mag(v.pos - r.docking_pos) < 0.42:
                        v.bind_to(r)

    def behavior_orbital_dance(self, state):
        for k, v in enumerate(viruses):
            if v.state == "free":
                radial = safe_norm(v.pos, random_unit())
                axis = vector(0, 1, 0)
                tangent = safe_norm(cross(axis, radial), random_unit())
                desired_r = HOST_R + 2.15 + 0.45 * math.sin(sim_time + k)
                correction = radial * ((desired_r - mag(v.pos)) * 0.18)
                v.vel += (tangent * 0.19 + correction) * DT * 8.0
                v.vel = limit_vec(v.vel, 1.2)
                v.orbiting = True
        if random.random() < 0.012:
            create_particle_burst(random_unit() * (HOST_R + 2.1), vector(0.65, 0.75, 1.0), count=5, speed=0.35)

    def behavior_chaotic_stir(self, state):
        for v in viruses:
            if v.state == "free":
                v.vel += random_unit() * randf(0.01, 0.065)
                v.vel = limit_vec(v.vel, 1.85)
            elif v.state == "bound" and random.random() < 0.004:
                v.detach(impulse=1.5)
        if random.random() < 0.028:
            create_particle_burst(random_unit() * randf(1.0, HOST_R - 0.5), vector(1.0, 0.55, 0.18), count=8, speed=0.8)

    def behavior_injection_ritual(self, state):
        self.ritual_phase += DT * 1.7
        bound = [v for v in viruses if v.state == "bound"]
        for v in bound:
            if v.bound_time > 0.45 or random.random() < 0.012:
                v.start_injection()

        free = [v for v in viruses if v.state == "free"]
        n = max(1, len(free))
        for i, v in enumerate(free):
            angle = 2 * math.pi * i / n + self.ritual_phase
            target = vector(
                math.cos(angle) * (HOST_R + 1.65),
                0.70 * math.sin(self.ritual_phase * 0.75 + i),
                math.sin(angle) * (HOST_R + 1.65),
            )
            self.nudge(v, target, strength=0.16, max_speed=1.05)

        if random.random() < 0.025:
            create_loose_spill(random_unit() * randf(0.7, HOST_R - 1.0), count=1, artistic=False)

    def behavior_endocytosis_wave(self, state):
        bound = [v for v in viruses if v.state == "bound"]
        for v in bound:
            if v.bound_time > 0.35 or random.random() < 0.015:
                v.start_endocytosis()

        for v in viruses:
            if v.state == "free":
                candidates = [r for r in receptors if r.state == "open" and r.normal.y < 0.55]
                if candidates:
                    r = min(candidates, key=lambda rr: mag(v.pos - rr.docking_pos))
                    v.target_receptor = r
                    self.nudge(v, r.docking_pos, strength=0.18, max_speed=0.95)
            elif v.state == "endocytosed" and v.vesicle is not None:
                v.vesicle.color = vector(0.50 + 0.18 * math.sin(sim_time * 4), 0.86, 1.0)

    def behavior_artistic_spill(self, state):
        if sim_time - self.last_spill_time > randf(1.0, 2.4):
            points = []
            released = [v for v in viruses if v.state in ("released", "injecting", "endocytosed")]
            if released:
                points.append(random.choice(released).pos)
            points.append(random_unit() * randf(0.5, HOST_R - 0.65))
            create_loose_spill(random.choice(points), count=random.randint(1, 2), artistic=True)
            self.last_spill_time = sim_time

        for r in receptors:
            if r.state == "open" and random.random() < 0.006:
                r.mark(playful=True)

        for v in viruses:
            if v.state == "free":
                angle = sim_time * 0.7 + v.idx
                target = vector(math.cos(angle), math.sin(angle * 0.7), math.sin(angle)) * (HOST_R + 2.8)
                self.nudge(v, target, strength=0.06, max_speed=0.8)

    def behavior_cleanup_reset(self, state):
        if self.reset_countdown is None:
            self.reset_countdown = 2.7
            create_particle_burst(vector(0, 0, 0), vector(1.0, 0.88, 0.24), count=40, speed=1.15)
        self.reset_countdown -= DT
        if self.reset_countdown <= 0:
            reset_simulation(keep_ai=True)
            self.reset_countdown = None
            self.set_mode("curious_probe", duration=randf(5.0, 9.0))

    def update(self, dt):
        if not self.enabled:
            return

        state = self.read_state()

        if event_count != self.last_event_count:
            self.last_event_count = event_count
            self.last_change_time = sim_time

        self.mode_timer += dt
        if self.mode != "cleanup_reset" and self.mode_timer >= self.mode_duration:
            self.choose_mode(state)
        elif self.mode != "cleanup_reset" and (self.is_complete(state) or self.is_stagnant(state)):
            self.set_mode("cleanup_reset", duration=3.5)

        if sim_time < human_override_until:
            return

        if self.mode == "curious_probe":
            self.behavior_curious_probe(state)
        elif self.mode == "careful_bind":
            self.behavior_careful_bind(state)
        elif self.mode == "orbital_dance":
            self.behavior_orbital_dance(state)
        elif self.mode == "chaotic_stir":
            self.behavior_chaotic_stir(state)
        elif self.mode == "injection_ritual":
            self.behavior_injection_ritual(state)
        elif self.mode == "endocytosis_wave":
            self.behavior_endocytosis_wave(state)
        elif self.mode == "artistic_spill":
            self.behavior_artistic_spill(state)
        elif self.mode == "cleanup_reset":
            self.behavior_cleanup_reset(state)


# -----------------------------
# Reset and setup
# -----------------------------

def reset_simulation(keep_ai=False):
    global host_cell, nucleus, host_label, receptors, viruses, particles, loose_genomes, decorations
    global selected_index, selection_marker, sim_time, event_count, round_number, human_override_until

    for v in viruses:
        v.erase()
    for r in receptors:
        r.erase()
    for p in particles:
        p.erase()
    for g in loose_genomes:
        g.erase()
    for d in decorations:
        erase_obj(d)
    erase_obj(host_cell)
    erase_obj(nucleus)
    erase_obj(host_label)
    erase_obj(selection_marker)

    receptors = []
    viruses = []
    particles = []
    loose_genomes = []
    decorations = []
    selected_index = 0
    human_override_until = 0.0

    host_cell = sphere(
        pos=vector(0, 0, 0),
        radius=HOST_R,
        color=MEMBRANE_BLUE,
        opacity=0.22,
        shininess=0.55,
    )
    decorations.append(
        sphere(
            pos=vector(0, 0, 0),
            radius=HOST_R * 0.985,
            color=vector(0.82, 0.94, 1.0),
            opacity=0.055,
            shininess=0.2,
        )
    )
    nucleus = sphere(
        pos=vector(0, 0, 0),
        radius=NUCLEUS_R,
        color=NUCLEUS_COLOR,
        opacity=0.34,
        shininess=0.62,
    )
    decorations.append(
        ring(
            pos=vector(0, 0, 0),
            axis=vector(0, 1, 0),
            radius=HOST_R,
            thickness=0.012,
            color=vector(0.68, 0.86, 1.0),
            opacity=0.35,
        )
    )
    decorations.append(
        ring(
            pos=vector(0, 0, 0),
            axis=vector(1, 0, 0),
            radius=HOST_R,
            thickness=0.012,
            color=vector(0.68, 0.86, 1.0),
            opacity=0.25,
        )
    )
    host_label = label(
        pos=vector(0, HOST_R + 0.72, 0),
        text="HOST CELL MEMBRANE",
        height=13,
        box=False,
        opacity=0,
        color=vector(0.25, 0.37, 0.55),
    )

    pts = fibonacci_sphere_points(RECEPTOR_COUNT)
    random.shuffle(pts)
    for i, p in enumerate(pts):
        receptors.append(Receptor(i, p))

    for i in range(VIRUS_COUNT):
        viruses.append(Virus(i))

    selection_marker = ring(
        pos=viruses[0].pos if viruses else vector(0, 0, 0),
        axis=vector(0, 1, 0),
        radius=0.58,
        thickness=0.025,
        color=vector(1.0, 0.72, 0.1),
        opacity=0.8,
        visible=True,
    )

    round_number += 1
    add_event()
    create_particle_burst(vector(0, HOST_R + 0.7, 0), vector(1.0, 0.82, 0.22), count=24, speed=0.75)

    if keep_ai and ai is not None:
        ai.last_signature = None
        ai.last_change_time = sim_time
        ai.completion_time = None
        ai.reset_countdown = None


# -----------------------------
# Human controls
# -----------------------------

def selected_virus():
    if not viruses:
        return None
    return viruses[selected_index % len(viruses)]


def nearest_receptor_to_virus(v, open_only=True):
    candidates = [r for r in receptors if (r.state == "open" or not open_only)]
    if not candidates:
        return None
    return min(candidates, key=lambda r: mag(v.pos - r.docking_pos))


def register_human_override(seconds=3.0):
    global human_override_until
    human_override_until = sim_time + seconds


def keydown(evt):
    global paused, selected_index, show_help
    k = evt.key
    keys_down.add(k)
    register_human_override(3.0)

    if k in ("p", "P"):
        paused = not paused
    elif k in ("i", "I"):
        if ai is not None:
            ai.enabled = not ai.enabled
    elif k in ("r", "R"):
        reset_simulation(keep_ai=True)
    elif k in ("v", "V", "tab"):
        if viruses:
            selected_index = (selected_index + 1) % len(viruses)
    elif k in ("h", "H"):
        show_help = not show_help
    elif k in ("b", "B"):
        v = selected_virus()
        if v is not None and v.state == "free":
            r = nearest_receptor_to_virus(v, open_only=True)
            if r is not None:
                v.bind_to(r)
    elif k in ("f", "F"):
        v = selected_virus()
        if v is not None and v.state == "bound":
            v.start_injection()
    elif k in ("g", "G"):
        v = selected_virus()
        if v is not None and v.state == "bound":
            v.start_endocytosis()
    elif k in ("x", "X"):
        v = selected_virus()
        if v is not None and v.state == "bound":
            v.detach(impulse=1.3)
    elif k in ("o", "O"):
        v = selected_virus()
        if v is not None and v.state == "free":
            v.force_orbit()
    elif k in ("m", "M"):
        v = selected_virus()
        if v is not None:
            r = nearest_receptor_to_virus(v, open_only=False)
            if r is not None:
                r.mark(playful=True)


def keyup(evt):
    k = evt.key
    if k in keys_down:
        keys_down.remove(k)


def apply_keyboard_motion(dt):
    v = selected_virus()
    if v is None:
        return

    move = vector(0, 0, 0)
    if "w" in keys_down or "W" in keys_down:
        move += vector(0, 0, -1)
    if "s" in keys_down or "S" in keys_down:
        move += vector(0, 0, 1)
    if "a" in keys_down or "A" in keys_down:
        move += vector(-1, 0, 0)
    if "d" in keys_down or "D" in keys_down:
        move += vector(1, 0, 0)
    if "q" in keys_down or "Q" in keys_down:
        move += vector(0, 1, 0)
    if "e" in keys_down or "E" in keys_down:
        move += vector(0, -1, 0)

    if mag(move) > 0:
        register_human_override(2.0)
        if v.state == "bound":
            v.detach(impulse=1.0)
        if v.state == "free":
            v.vel += safe_norm(move) * 1.15 * dt * 4.0
            v.vel = limit_vec(v.vel, 1.75)


scene.bind("keydown", keydown)
scene.bind("keyup", keyup)


# -----------------------------
# Status display
# -----------------------------

def update_selection_marker():
    if selection_marker is None or not viruses:
        return
    v = selected_virus()
    if v is None:
        selection_marker.visible = False
        return
    selection_marker.visible = True
    selection_marker.pos = v.pos
    selection_marker.axis = scene.up
    selection_marker.radius = 0.59 + 0.05 * math.sin(sim_time * 6)


def update_status():
    state_counts = {"free": 0, "bound": 0, "injecting": 0, "endocytosed": 0, "released": 0}
    for v in viruses:
        state_counts[v.state] = state_counts.get(v.state, 0) + 1
    open_count = len([r for r in receptors if r.state == "open"])
    used_count = len([r for r in receptors if r.state == "used"])
    v = selected_virus()
    selected = "none"
    if v is not None:
        selected = "V{} ({})".format(v.idx + 1, v.state)
    ai_status = "ON" if ai is not None and ai.enabled else "OFF"
    pause_status = "PAUSED" if paused else "RUNNING"
    override = "human override" if sim_time < human_override_until else "auto"
    mode = ai.mode if ai is not None else "none"

    help_line = ""
    if show_help:
        help_line = (
            "\nControls: P pause | I AI | R reset | V select | WASDQE move | "
            "B bind | F inject | G endocytose | X detach | O orbit | M mark | H hide help"
        )

    status_text.text = (
        "\nRound {} | {} | AI {} / {} / mode: {} | selected: {}"
        "\nViruses free:{} bound:{} injecting:{} vesicles:{} released:{} | receptors open:{} used:{} | events:{}{}"
    ).format(
        round_number,
        pause_status,
        ai_status,
        override,
        mode,
        selected,
        state_counts.get("free", 0),
        state_counts.get("bound", 0),
        state_counts.get("injecting", 0),
        state_counts.get("endocytosed", 0),
        state_counts.get("released", 0),
        open_count,
        used_count,
        event_count,
        help_line,
    )


# -----------------------------
# Main loop
# -----------------------------

reset_simulation(keep_ai=False)
round_number = 1
ai = AIController()

while True:
    rate(50)

    if not paused:
        sim_time += DT

        apply_keyboard_motion(DT)

        if ai is not None:
            ai.update(DT)

        for v in list(viruses):
            v.update(DT)

        update_collisions()

        alive_particles = []
        for p in particles:
            if p.update(DT):
                alive_particles.append(p)
            else:
                p.erase()
        particles = alive_particles

        for g in list(loose_genomes):
            g.update(DT)

        if nucleus is not None:
            nucleus.radius = NUCLEUS_R + 0.035 * math.sin(sim_time * 2.0)
            nucleus.opacity = 0.30 + 0.04 * math.sin(sim_time * 1.3)

        if host_cell is not None:
            host_cell.opacity = 0.20 + 0.025 * math.sin(sim_time * 0.9)

    update_selection_marker()
    update_status()
