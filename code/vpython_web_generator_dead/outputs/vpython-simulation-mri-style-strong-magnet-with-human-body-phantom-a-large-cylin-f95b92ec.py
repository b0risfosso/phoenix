from vpython import *
import random
import math
from collections import deque

# ------------------------------------------------------------
# MRI-Style Strong Magnet With Human-Body Phantom
# VPython 3D simulation with autonomous AI behavior controller.
# Keyboard:
#   SPACE pause/resume
#   A     toggle AI
#   I     pause/resume AI only
#   R     reset round
#   P     RF pulse
#   S     scramble/tip spins
#   UP/DOWN adjust magnetic field strength
#   LEFT/RIGHT move scan slice
#   M     force AI to switch mode
#   T     attach drone to nearest spin
#   D     detach drone
#   O     toggle drone orbit
#   C     clear markers
#   W     toggle RF wrap helix
# ------------------------------------------------------------

scene = canvas(
    title="MRI-Style Strong Magnet With Human-Body Phantom + AI Controller",
    width=1200,
    height=760,
    background=vector(0.94, 0.975, 1.0),
    center=vector(0, 0.35, 0),
    forward=vector(-1.2, -0.2, -1.4),
    range=6.6,
)
scene.userzoom = True
scene.userspin = True
scene.ambient = color.gray(0.62)

distant_light(direction=vector(-0.7, -1.0, -0.4), color=color.gray(0.68))
distant_light(direction=vector(0.4, -0.5, 0.8), color=color.gray(0.35))

# ------------------------------------------------------------
# Globals
# ------------------------------------------------------------

sim_time = 0.0
paused = False

field_strength = 1.0
target_field_strength = 1.0
B_AXIS = vector(1, 0, 0)

magnet_length = 9.0
magnet_radius = 2.75

spins = []
pulses = []
rf_waves = []
markers = []
field_tubes = []
field_arrows = []
manual_override_until = 0.0

scan_velocity = 0.0
scan_min_x = -3.85
scan_max_x = 3.85
rf_flash_timer = 0.0
wrap_visible_by_user = True

ROUND_SPIN_COUNT = 44

# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def lerp(a, b, t):
    return a + (b - a) * t

def color_lerp(c1, c2, t):
    t = clamp(t, 0, 1)
    return c1 * (1 - t) + c2 * t

def safe_norm(v):
    if mag(v) < 1e-8:
        return vector(1, 0, 0)
    return norm(v)

def random_body_point():
    # A simple probabilistic human phantom volume:
    # torso ellipsoid, head sphere, arms, legs.
    choice = random.random()

    if choice < 0.58:
        # Torso ellipsoid
        for _ in range(80):
            x = random.uniform(-0.42, 0.42)
            y = random.uniform(-0.30, 1.18)
            z = random.uniform(-0.31, 0.31)
            if (x / 0.45) ** 2 + ((y - 0.43) / 0.82) ** 2 + (z / 0.32) ** 2 <= 1:
                return vector(x, y, z)

    elif choice < 0.73:
        # Head sphere
        for _ in range(80):
            p = vector(
                random.uniform(-0.25, 0.25),
                random.uniform(1.32, 1.86),
                random.uniform(-0.25, 0.25),
            )
            if mag(p - vector(0, 1.58, 0)) <= 0.28:
                return p

    elif choice < 0.84:
        # Arms
        zc = random.choice([-0.52, 0.52])
        return vector(
            random.uniform(-0.12, 0.12),
            random.uniform(-0.18, 1.05),
            zc + random.uniform(-0.065, 0.065),
        )

    else:
        # Legs
        zc = random.choice([-0.16, 0.16])
        return vector(
            random.uniform(-0.11, 0.11),
            random.uniform(-1.15, -0.28),
            zc + random.uniform(-0.065, 0.065),
        )

    return vector(0, 0.4, 0)

# ------------------------------------------------------------
# Main stationary objects: MRI magnet, phantom, field tubes
# ------------------------------------------------------------

floor = box(
    pos=vector(0, -1.72, 0),
    size=vector(10.2, 0.035, 6.6),
    color=vector(0.88, 0.93, 0.96),
    opacity=0.55,
)

table = box(
    pos=vector(0, -1.31, 0),
    size=vector(7.8, 0.12, 1.05),
    color=vector(0.86, 0.88, 0.90),
    opacity=0.88,
)

magnet_shell = cylinder(
    pos=vector(-magnet_length / 2, 0, 0),
    axis=vector(magnet_length, 0, 0),
    radius=magnet_radius,
    color=vector(0.55, 0.75, 1.0),
    opacity=0.12,
)

bore_hint = cylinder(
    pos=vector(-magnet_length / 2 - 0.02, 0, 0),
    axis=vector(magnet_length + 0.04, 0, 0),
    radius=1.74,
    color=vector(1, 1, 1),
    opacity=0.06,
)

magnet_rings = []
for x in [-4.2, -3.45, -2.7, -1.95, -1.2, -0.45, 0.3, 1.05, 1.8, 2.55, 3.3, 4.05]:
    magnet_rings.append(
        ring(
            pos=vector(x, 0, 0),
            axis=vector(1, 0, 0),
            radius=magnet_radius,
            thickness=0.105,
            color=vector(0.34, 0.62, 0.95),
            opacity=0.74,
        )
    )

front_cap = ring(
    pos=vector(-4.55, 0, 0),
    axis=vector(1, 0, 0),
    radius=magnet_radius,
    thickness=0.18,
    color=vector(0.26, 0.56, 0.93),
    opacity=0.9,
)
rear_cap = ring(
    pos=vector(4.55, 0, 0),
    axis=vector(1, 0, 0),
    radius=magnet_radius,
    thickness=0.18,
    color=vector(0.26, 0.56, 0.93),
    opacity=0.9,
)

bore_label = label(
    pos=vector(-4.65, 2.82, 0),
    text="large superconducting magnet",
    height=13,
    box=False,
    color=vector(0.12, 0.26, 0.45),
)

field_label = label(
    pos=vector(3.2, 2.25, -1.15),
    text="B0: nearly uniform field",
    height=13,
    box=False,
    color=vector(0.05, 0.38, 0.48),
)

# Human-body phantom: translucent, simple, stationary.
phantom_color = vector(1.0, 0.70, 0.52)
torso = sphere(
    pos=vector(0, 0.42, 0),
    size=vector(0.88, 1.62, 0.62),
    color=phantom_color,
    opacity=0.34,
)
head = sphere(
    pos=vector(0, 1.58, 0),
    radius=0.30,
    color=phantom_color,
    opacity=0.38,
)
neck = cylinder(
    pos=vector(0, 1.14, 0),
    axis=vector(0, 0.22, 0),
    radius=0.12,
    color=phantom_color,
    opacity=0.30,
)
left_arm = cylinder(
    pos=vector(0, 1.02, -0.55),
    axis=vector(0, -1.24, 0),
    radius=0.085,
    color=phantom_color,
    opacity=0.30,
)
right_arm = cylinder(
    pos=vector(0, 1.02, 0.55),
    axis=vector(0, -1.24, 0),
    radius=0.085,
    color=phantom_color,
    opacity=0.30,
)
left_leg = cylinder(
    pos=vector(0, -0.28, -0.16),
    axis=vector(0, -0.88, 0),
    radius=0.09,
    color=phantom_color,
    opacity=0.30,
)
right_leg = cylinder(
    pos=vector(0, -0.28, 0.16),
    axis=vector(0, -0.88, 0),
    radius=0.09,
    color=phantom_color,
    opacity=0.30,
)

phantom_label = label(
    pos=vector(0.52, 1.82, 0.18),
    text="transparent body phantom",
    height=12,
    box=False,
    color=vector(0.48, 0.22, 0.10),
)

# Parallel field tubes through bore and phantom.
for y in [-1.2, -0.6, 0.0, 0.6, 1.2]:
    for z in [-1.15, -0.58, 0.0, 0.58, 1.15]:
        if y * y + z * z <= 1.75 ** 2:
            tube = cylinder(
                pos=vector(-4.85, y, z),
                axis=vector(9.7, 0, 0),
                radius=0.018,
                color=vector(0.0, 0.75, 0.92),
                opacity=0.24,
            )
            field_tubes.append(tube)
            if random.random() < 0.55:
                arr = arrow(
                    pos=vector(random.uniform(-3.7, 2.8), y, z),
                    axis=vector(0.38, 0, 0),
                    shaftwidth=0.035,
                    color=vector(0.0, 0.65, 0.82),
                    opacity=0.42,
                )
                field_arrows.append(arr)

# RF scan slice plane.
scan_slice = box(
    pos=vector(scan_min_x, 0.25, 0),
    size=vector(0.045, 3.55, 3.55),
    color=vector(0.25, 1.0, 0.55),
    opacity=0.14,
)

scan_label = label(
    pos=scan_slice.pos + vector(0, 2.0, 0),
    text="movable scan slice",
    height=11,
    box=False,
    color=vector(0.05, 0.44, 0.18),
)

rf_coil = ring(
    pos=vector(0, 0.34, 0),
    axis=vector(1, 0, 0),
    radius=1.02,
    thickness=0.035,
    color=vector(1.0, 0.56, 0.08),
    opacity=0.45,
)

rf_wrap = helix(
    pos=vector(-0.78, 0.34, 0),
    axis=vector(1.56, 0, 0),
    radius=1.04,
    coils=8,
    thickness=0.018,
    color=vector(1.0, 0.64, 0.12),
)
rf_wrap.visible = False

rf_label = label(
    pos=vector(0.0, -0.92, 1.2),
    text="RF coil / wrap",
    height=11,
    box=False,
    color=vector(0.72, 0.31, 0.02),
)

# ------------------------------------------------------------
# Dynamic objects
# ------------------------------------------------------------

class PulseParticle:
    def __init__(self, pos, c=vector(1.0, 0.26, 0.75), radius=0.06, ttl=0.85):
        self.age = 0.0
        self.ttl = ttl
        self.base_radius = radius
        self.obj = sphere(
            pos=vector(pos),
            radius=radius,
            color=c,
            opacity=0.56,
            emissive=True,
        )
        self.ring = ring(
            pos=vector(pos),
            axis=vector(1, 0, 0),
            radius=radius * 1.4,
            thickness=0.008,
            color=c,
            opacity=0.58,
        )

    def update(self, dt):
        self.age += dt
        t = self.age / self.ttl
        self.obj.radius = self.base_radius * (1 + 5.5 * t)
        self.ring.radius = self.base_radius * (1.4 + 9.0 * t)
        fade = clamp(1 - t, 0, 1)
        self.obj.opacity = 0.52 * fade
        self.ring.opacity = 0.60 * fade
        return self.age < self.ttl

    def destroy(self):
        self.obj.visible = False
        self.ring.visible = False

class RFWave:
    def __init__(self, center, start_radius=0.38, c=vector(1.0, 0.62, 0.05), ttl=1.1):
        self.age = 0.0
        self.ttl = ttl
        self.obj = ring(
            pos=vector(center),
            axis=vector(1, 0, 0),
            radius=start_radius,
            thickness=0.025,
            color=c,
            opacity=0.70,
        )

    def update(self, dt):
        self.age += dt
        t = self.age / self.ttl
        self.obj.radius = 0.38 + 1.42 * t
        self.obj.thickness = 0.025 * (1 - 0.45 * t)
        self.obj.opacity = 0.70 * clamp(1 - t, 0, 1)
        return self.age < self.ttl

    def destroy(self):
        self.obj.visible = False

class Marker:
    def __init__(self, spin=None, pos=None, c=vector(0.18, 0.75, 1.0), text="mark", attached=True, ttl=None):
        self.spin = spin
        self.attached = attached and spin is not None
        self.age = 0.0
        self.ttl = ttl
        p = vector(pos) if pos is not None else vector(spin.pos)
        self.ring = ring(
            pos=p,
            axis=vector(1, 0, 0),
            radius=0.16,
            thickness=0.012,
            color=c,
            opacity=0.74,
        )
        self.dot = sphere(pos=p, radius=0.026, color=c, opacity=0.92, emissive=True)
        self.label = label(
            pos=p + vector(0.05, 0.16, 0),
            text=text,
            height=8,
            box=False,
            color=c,
            opacity=0,
        )

    def update(self, dt):
        self.age += dt
        if self.attached and self.spin is not None:
            p = self.spin.pos
            self.ring.pos = p
            self.dot.pos = p
            self.label.pos = p + vector(0.05, 0.16, 0)
        self.ring.rotate(angle=1.8 * dt, axis=vector(1, 0, 0), origin=self.ring.pos)
        if self.ttl is not None:
            fade = clamp(1 - self.age / self.ttl, 0, 1)
            self.ring.opacity = 0.74 * fade
            self.dot.opacity = 0.92 * fade
            return self.age < self.ttl
        return True

    def destroy(self):
        self.ring.visible = False
        self.dot.visible = False
        self.label.visible = False

class Spin:
    def __init__(self, idx, pos):
        self.idx = idx
        self.pos = vector(pos)
        self.phase = random.uniform(0, 2 * math.pi)
        self.theta = random.uniform(0.55, 2.15)
        self.base_phase_speed = random.uniform(5.8, 8.4)
        self.relax = random.uniform(0.075, 0.15)
        self.pulse_timer = random.uniform(0.15, 1.2)
        self.marked = False
        self.locked = False
        self.body = sphere(
            pos=self.pos,
            radius=0.043,
            color=vector(1.0, 0.88, 0.15),
            opacity=0.88,
            emissive=False,
        )
        self.arrow = arrow(
            pos=self.pos,
            axis=vector(0.28, 0, 0),
            shaftwidth=0.026,
            color=vector(0.15, 0.35, 1.0),
        )
        self.label = None
        if idx < 8:
            self.label = label(
                pos=self.pos + vector(0.04, 0.12, 0),
                text="spin " + str(idx + 1),
                height=8,
                box=False,
                color=vector(0.18, 0.20, 0.30),
                opacity=0,
            )
        self.update_visual_only()

    def moment_vector(self):
        return vector(
            math.cos(self.theta),
            math.sin(self.theta) * math.cos(self.phase),
            math.sin(self.theta) * math.sin(self.phase),
        )

    def alignment(self):
        return clamp(math.cos(self.theta), -1, 1)

    def transverse(self):
        return clamp(math.sin(self.theta), 0, 1)

    def tip(self, amount):
        self.theta = clamp(self.theta + amount, 0.02, math.pi * 0.96)
        self.pulse_timer = min(self.pulse_timer, 0.08)

    def align_boost(self, amount):
        self.theta = clamp(self.theta - amount, 0.0, math.pi * 0.96)

    def scramble(self):
        self.theta = random.uniform(0.45, 2.55)
        self.phase = random.uniform(0, 2 * math.pi)
        self.pulse_timer = random.uniform(0.04, 0.42)

    def update_visual_only(self):
        m = self.moment_vector()
        self.arrow.axis = 0.34 * m
        align01 = clamp((self.alignment() + 1) / 2, 0, 1)
        self.arrow.color = color_lerp(vector(1.0, 0.18, 0.16), vector(0.1, 0.38, 1.0), align01)
        self.body.color = color_lerp(vector(1.0, 0.62, 0.12), vector(0.28, 0.9, 1.0), align01)
        if self.label:
            self.label.pos = self.pos + vector(0.04, 0.12, 0)

    def update(self, dt, B):
        if not self.locked:
            precession = self.base_phase_speed * max(0.05, B)
            self.phase += precession * dt

            # Longitudinal relaxation: spins gradually align with B0.
            self.theta *= math.exp(-self.relax * max(0.05, B) * dt)

            # Scan slice subtly "observes" spins near it and adds a visible flicker.
            dist_to_slice = abs(self.pos.x - scan_slice.pos.x)
            if dist_to_slice < 0.075:
                self.body.radius = 0.058
                if self.transverse() > 0.1:
                    self.pulse_timer = min(self.pulse_timer, 0.045)
            else:
                self.body.radius = 0.043

        self.update_visual_only()

        self.pulse_timer -= dt
        if self.pulse_timer <= 0:
            # Emission-like visible glow when transverse magnetization exists.
            if self.transverse() > 0.12:
                intensity = self.transverse()
                c = color_lerp(vector(0.35, 0.9, 1.0), vector(1.0, 0.20, 0.72), intensity)
                pulses.append(PulseParticle(self.pos, c=c, radius=0.035 + 0.025 * intensity, ttl=0.55 + 0.45 * intensity))
            self.pulse_timer = random.uniform(0.45, 1.35) / max(0.25, B)

    def destroy(self):
        self.body.visible = False
        self.arrow.visible = False
        if self.label:
            self.label.visible = False

class Drone:
    def __init__(self):
        self.obj = sphere(
            pos=vector(-1.6, 1.85, 1.2),
            radius=0.095,
            color=vector(0.58, 0.22, 1.0),
            opacity=0.95,
            emissive=True,
            make_trail=True,
            retain=90,
            trail_radius=0.012,
            trail_color=vector(0.55, 0.2, 1.0),
        )
        self.target_spin = None
        self.attached = False
        self.orbiting = True
        self.angle = 0.0
        self.free_velocity = vector(0.35, 0.08, -0.25)
        self.tether = cylinder(
            pos=self.obj.pos,
            axis=vector(0, 0, 0),
            radius=0.008,
            color=vector(0.6, 0.18, 1.0),
            opacity=0.0,
        )
        self.cooldown = 0.0

    def attach_to(self, spin):
        self.target_spin = spin
        self.attached = True
        self.orbiting = True
        self.cooldown = 0.3

    def detach(self):
        self.attached = False
        self.target_spin = None
        self.tether.opacity = 0.0

    def nearest_spin(self):
        if not spins:
            return None
        return min(spins, key=lambda s: mag(s.pos - self.obj.pos))

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        self.angle += dt * (1.1 + 0.45 * field_strength)

        if self.attached and self.target_spin is not None:
            radius = 0.34 if self.orbiting else 0.16
            bob = 0.08 * math.sin(2.3 * self.angle)
            offset = vector(
                0.18 * math.cos(0.7 * self.angle),
                radius * math.sin(self.angle) + bob,
                radius * math.cos(self.angle),
            )
            self.obj.pos = self.target_spin.pos + offset
            self.tether.pos = self.obj.pos
            self.tether.axis = self.target_spin.pos - self.obj.pos
            self.tether.opacity = 0.35
        else:
            self.obj.pos += self.free_velocity * dt
            # Bounce within the bore.
            if self.obj.pos.x < -4.0 or self.obj.pos.x > 4.0:
                self.free_velocity.x *= -1
            r_yz = math.sqrt(self.obj.pos.y ** 2 + self.obj.pos.z ** 2)
            if r_yz > 2.15:
                radial = safe_norm(vector(0, self.obj.pos.y, self.obj.pos.z))
                self.free_velocity -= 2 * dot(self.free_velocity, radial) * radial
                self.obj.pos.y = radial.y * 2.12
                self.obj.pos.z = radial.z * 2.12
            self.tether.opacity = 0.0

        # Drone collisions with spins: visible interaction, "collide and dip" tip.
        if self.cooldown <= 0:
            for s in spins:
                d = mag(s.pos - self.obj.pos)
                if d < 0.145:
                    s.tip(0.25)
                    pulses.append(PulseParticle(s.pos, c=vector(1.0, 0.2, 0.72), radius=0.055, ttl=0.8))
                    self.cooldown = 0.55
                    if not s.marked:
                        add_marker(s, c=vector(0.66, 0.28, 1.0), text="bump", ttl=4.5)
                    break

drone = Drone()

# ------------------------------------------------------------
# Labels/status display
# ------------------------------------------------------------

status_label = label(
    pos=vector(-4.95, 3.25, 0),
    text="",
    height=12,
    box=True,
    border=8,
    color=vector(0.06, 0.16, 0.25),
    background=vector(0.96, 0.99, 1.0),
    opacity=0.32,
)

help_label = label(
    pos=vector(0, -2.05, 0),
    text="SPACE pause | A toggle AI | P RF pulse | S scramble | R reset | arrows field/slice | M next AI mode",
    height=11,
    box=False,
    color=vector(0.20, 0.27, 0.33),
)

# ------------------------------------------------------------
# Simulation actions available to human and AI
# ------------------------------------------------------------

def create_pulse(pos, c=vector(1.0, 0.25, 0.75), radius=0.055, ttl=0.85):
    pulses.append(PulseParticle(pos, c=c, radius=radius, ttl=ttl))

def add_marker(spin=None, pos=None, c=vector(0.18, 0.75, 1.0), text="mark", attached=True, ttl=None):
    if len(markers) > 80:
        old = markers.pop(0)
        old.destroy()
    m = Marker(spin=spin, pos=pos, c=c, text=text, attached=attached, ttl=ttl)
    markers.append(m)
    if spin is not None:
        spin.marked = True
    return m

def clear_markers():
    for m in markers:
        m.destroy()
    markers[:] = []
    for s in spins:
        s.marked = False

def rf_pulse(angle=0.55, selective=False, center_x=None):
    global rf_flash_timer
    rf_flash_timer = 0.45
    center_x = scan_slice.pos.x if center_x is None else center_x

    rf_waves.append(RFWave(vector(center_x, 0.34, 0), start_radius=0.32, c=vector(1.0, 0.58, 0.08), ttl=1.0))
    rf_waves.append(RFWave(vector(center_x, 0.34, 0), start_radius=0.58, c=vector(1.0, 0.28, 0.68), ttl=0.82))

    for s in spins:
        if selective:
            dist = abs(s.pos.x - center_x)
            if dist > 0.38:
                continue
            strength = angle * (1 - dist / 0.38)
        else:
            strength = angle * random.uniform(0.72, 1.0)
        s.tip(strength)
        if random.random() < 0.42:
            create_pulse(s.pos, c=vector(1.0, 0.27, 0.75), radius=0.045, ttl=0.74)

def scramble_spins(fraction=1.0):
    selected = spins[:]
    random.shuffle(selected)
    count = int(len(selected) * fraction)
    for s in selected[:count]:
        s.scramble()
        if random.random() < 0.30:
            create_pulse(s.pos, c=vector(1.0, 0.33, 0.15), radius=0.04, ttl=0.75)

def organize_spins(amount=0.12):
    for s in spins:
        s.align_boost(amount * random.uniform(0.45, 1.0))

def move_scan_slice(dx):
    scan_slice.pos.x = clamp(scan_slice.pos.x + dx, scan_min_x, scan_max_x)

def attach_drone_to_nearest():
    s = drone.nearest_spin()
    if s:
        drone.attach_to(s)
        add_marker(s, c=vector(0.58, 0.22, 1.0), text="AI", ttl=5.5)

def detach_drone():
    drone.detach()

def set_field_strength(value):
    global target_field_strength
    target_field_strength = clamp(value, 0.15, 2.25)

def clear_pulses():
    for p in pulses:
        p.destroy()
    pulses[:] = []
    for w in rf_waves:
        w.destroy()
    rf_waves[:] = []

def destroy_spins():
    for s in spins:
        s.destroy()
    spins[:] = []

def reset_round():
    global sim_time, field_strength, target_field_strength, scan_velocity, rf_flash_timer
    destroy_spins()
    clear_pulses()
    clear_markers()

    for i in range(ROUND_SPIN_COUNT):
        spins.append(Spin(i, random_body_point()))

    field_strength = 1.0
    target_field_strength = 1.0
    scan_velocity = 0.0
    scan_slice.pos.x = scan_min_x
    rf_flash_timer = 0.0
    rf_wrap.visible = False
    drone.detach()
    drone.obj.pos = vector(-1.6, 1.85, 1.2)
    drone.free_velocity = vector(random.choice([-1, 1]) * 0.35, 0.08, random.choice([-1, 1]) * 0.25)
    if hasattr(drone.obj, "clear_trail"):
        drone.obj.clear_trail()

    for _ in range(5):
        s = random.choice(spins)
        add_marker(s, c=vector(0.12, 0.65, 1.0), text="seed", ttl=3.2)

# ------------------------------------------------------------
# AI Controller: state variables, actions, mode-switching,
# stagnation/completion detection, reset loop.
# ------------------------------------------------------------

class AIController:
    def __init__(self):
        self.enabled = True
        self.paused = False
        self.mode = "CAREFUL_ALIGN"
        self.last_modes = deque(maxlen=4)
        self.mode_time = 0.0
        self.mode_duration = random.uniform(5.5, 9.0)
        self.action_timer = 0.0
        self.metric_timer = 0.0
        self.metric_history = deque(maxlen=28)
        self.round_number = 1
        self.completion_timer = 0.0
        self.loop_delay = 2.8
        self.playfulness = 0.5
        self.chaos = 0.35
        self.care = 0.55
        self.artistry = 0.45
        self.modes = [
            "CAREFUL_ALIGN",
            "PLAYFUL_PULSE",
            "SCAN_MARK",
            "ORBIT_DIP",
            "ARTISTIC_WRAP",
            "CHAOTIC_SCRAMBLE",
            "CONSTRUCTIVE_ORGANIZE",
        ]

    def read_state(self):
        if len(spins) == 0:
            return {
                "empty": True,
                "avg_alignment": 0,
                "avg_transverse": 0,
                "marked_fraction": 0,
                "field_strength": field_strength,
                "scan_x": scan_slice.pos.x,
                "pulse_count": len(pulses),
                "drone_attached": drone.attached,
            }

        avg_alignment = sum((s.alignment() + 1) / 2 for s in spins) / len(spins)
        avg_transverse = sum(s.transverse() for s in spins) / len(spins)
        marked_fraction = sum(1 for s in spins if s.marked) / len(spins)
        least_aligned = min(spins, key=lambda s: s.alignment())
        most_transverse = max(spins, key=lambda s: s.transverse())
        near_slice = [s for s in spins if abs(s.pos.x - scan_slice.pos.x) < 0.20]

        return {
            "empty": False,
            "avg_alignment": avg_alignment,
            "avg_transverse": avg_transverse,
            "marked_fraction": marked_fraction,
            "field_strength": field_strength,
            "target_field_strength": target_field_strength,
            "scan_x": scan_slice.pos.x,
            "pulse_count": len(pulses),
            "wave_count": len(rf_waves),
            "marker_count": len(markers),
            "drone_attached": drone.attached,
            "least_aligned_spin": least_aligned,
            "most_transverse_spin": most_transverse,
            "near_slice_count": len(near_slice),
            "time": sim_time,
        }

    def detect_stagnation_or_completion(self, state, dt):
        self.metric_timer += dt
        if self.metric_timer >= 0.45:
            self.metric_timer = 0.0
            self.metric_history.append(
                (
                    sim_time,
                    state["avg_alignment"],
                    state["avg_transverse"],
                    state["pulse_count"],
                    state["marker_count"],
                    scan_slice.pos.x,
                )
            )

        complete = False
        stagnant = False
        empty = state.get("empty", False)

        if empty:
            complete = True

        if not empty:
            # Complete if spins have mostly aligned and scene is quiet.
            if state["avg_alignment"] > 0.94 and state["avg_transverse"] < 0.22 and len(pulses) < 3:
                self.completion_timer += dt
            else:
                self.completion_timer = max(0.0, self.completion_timer - 0.35 * dt)

            if self.completion_timer > 2.6:
                complete = True

        if len(self.metric_history) >= 15:
            oldest = self.metric_history[0]
            newest = self.metric_history[-1]
            time_span = newest[0] - oldest[0]
            dalign = abs(newest[1] - oldest[1])
            dtrans = abs(newest[2] - oldest[2])
            dpulse = abs(newest[3] - oldest[3])
            dscan = abs(newest[5] - oldest[5])
            if time_span > 6.0 and dalign < 0.012 and dtrans < 0.012 and dpulse < 2 and dscan < 0.08:
                stagnant = True

        return stagnant, complete, empty

    def choose_next_mode(self, reason="time"):
        state = self.read_state()

        if state.get("empty", False):
            self.switch_mode("RESET_LOOP")
            return

        candidates = self.modes[:]

        # Reactive weighting.
        if state["avg_alignment"] > 0.88:
            candidates += ["PLAYFUL_PULSE", "CHAOTIC_SCRAMBLE", "ARTISTIC_WRAP"]
        if state["avg_transverse"] > 0.72:
            candidates += ["CAREFUL_ALIGN", "CONSTRUCTIVE_ORGANIZE", "SCAN_MARK"]
        if state["marked_fraction"] < 0.30:
            candidates += ["SCAN_MARK", "ORBIT_DIP"]
        if state["pulse_count"] < 3:
            candidates += ["PLAYFUL_PULSE", "ARTISTIC_WRAP"]

        # Avoid repeating recent modes.
        candidates = [m for m in candidates if m not in self.last_modes]
        if not candidates:
            candidates = self.modes[:]

        if reason == "stagnant":
            candidates += ["CHAOTIC_SCRAMBLE", "PLAYFUL_PULSE", "ARTISTIC_WRAP"]
        elif reason == "complete":
            self.switch_mode("RESET_LOOP")
            return

        self.switch_mode(random.choice(candidates))

    def switch_mode(self, mode):
        if self.mode != mode:
            self.last_modes.append(self.mode)
        self.mode = mode
        self.mode_time = 0.0
        self.action_timer = 0.0
        self.mode_duration = random.uniform(5.0, 10.5)

        if mode == "CAREFUL_ALIGN":
            set_field_strength(random.uniform(1.08, 1.42))
            drone.orbiting = False
            rf_wrap.visible = False
        elif mode == "PLAYFUL_PULSE":
            set_field_strength(random.uniform(0.72, 1.05))
            drone.orbiting = True
        elif mode == "SCAN_MARK":
            set_field_strength(random.uniform(0.88, 1.18))
            drone.orbiting = True
        elif mode == "ORBIT_DIP":
            set_field_strength(random.uniform(0.8, 1.25))
            attach_drone_to_nearest()
            drone.orbiting = True
        elif mode == "ARTISTIC_WRAP":
            set_field_strength(random.uniform(0.65, 1.05))
            rf_wrap.visible = True and wrap_visible_by_user
        elif mode == "CHAOTIC_SCRAMBLE":
            set_field_strength(random.uniform(0.35, 0.9))
            rf_wrap.visible = True and wrap_visible_by_user
        elif mode == "CONSTRUCTIVE_ORGANIZE":
            set_field_strength(random.uniform(1.25, 1.75))
            rf_wrap.visible = False
        elif mode == "RESET_LOOP":
            self.completion_timer = 0.0
            rf_wrap.visible = False

    def update(self, dt):
        global scan_velocity

        if not self.enabled or self.paused:
            return

        state = self.read_state()
        stagnant, complete, empty = self.detect_stagnation_or_completion(state, dt)

        if complete or empty:
            if self.mode != "RESET_LOOP":
                self.switch_mode("RESET_LOOP")

        elif stagnant:
            self.choose_next_mode(reason="stagnant")

        self.mode_time += dt
        self.action_timer -= dt

        if self.mode != "RESET_LOOP" and self.mode_time > self.mode_duration:
            self.choose_next_mode(reason="time")

        if self.mode == "CAREFUL_ALIGN":
            self.behavior_careful_align(dt, state)
        elif self.mode == "PLAYFUL_PULSE":
            self.behavior_playful_pulse(dt, state)
        elif self.mode == "SCAN_MARK":
            self.behavior_scan_mark(dt, state)
        elif self.mode == "ORBIT_DIP":
            self.behavior_orbit_dip(dt, state)
        elif self.mode == "ARTISTIC_WRAP":
            self.behavior_artistic_wrap(dt, state)
        elif self.mode == "CHAOTIC_SCRAMBLE":
            self.behavior_chaotic_scramble(dt, state)
        elif self.mode == "CONSTRUCTIVE_ORGANIZE":
            self.behavior_constructive_organize(dt, state)
        elif self.mode == "RESET_LOOP":
            self.behavior_reset_loop(dt, state)

    def behavior_careful_align(self, dt, state):
        global scan_velocity
        scan_velocity = 0.18 * math.sin(sim_time * 0.55)
        set_field_strength(1.25 + 0.12 * math.sin(sim_time * 0.25))
        organize_spins(0.010 * dt)

        if self.action_timer <= 0 and not state.get("empty", False):
            s = state["least_aligned_spin"]
            add_marker(s, c=vector(0.12, 0.55, 1.0), text="align", ttl=4.2)
            drone.attach_to(s)
            self.action_timer = random.uniform(1.2, 2.4)

    def behavior_playful_pulse(self, dt, state):
        global scan_velocity
        scan_velocity = 0.45 * math.sin(sim_time * 0.95)
        rf_wrap.visible = False

        if self.action_timer <= 0:
            rf_pulse(angle=random.uniform(0.18, 0.42), selective=random.random() < 0.55)
            if spins:
                s = random.choice(spins)
                drone.attach_to(s)
            self.action_timer = random.uniform(0.85, 1.65)

    def behavior_scan_mark(self, dt, state):
        global scan_velocity
        scan_velocity = 0.74 * math.sin(sim_time * 0.42)

        if self.action_timer <= 0:
            near = [s for s in spins if abs(s.pos.x - scan_slice.pos.x) < 0.24 and not s.marked]
            if near:
                s = max(near, key=lambda q: q.transverse())
                add_marker(s, c=vector(0.02, 0.72, 0.38), text="slice", ttl=None)
                create_pulse(s.pos, c=vector(0.15, 1.0, 0.55), radius=0.045, ttl=0.85)
                drone.attach_to(s)
            else:
                rf_pulse(angle=0.16, selective=True)
            self.action_timer = random.uniform(0.55, 1.25)

    def behavior_orbit_dip(self, dt, state):
        global scan_velocity
        scan_velocity = 0.10 * math.sin(sim_time * 1.3)

        if not drone.attached and spins:
            drone.attach_to(random.choice(spins))

        if self.action_timer <= 0 and spins:
            s = random.choice(spins) if random.random() < 0.35 else state["most_transverse_spin"]
            drone.attach_to(s)
            if random.random() < 0.65:
                s.tip(random.uniform(0.10, 0.32))
                add_marker(s, c=vector(0.62, 0.22, 1.0), text="dip", ttl=3.8)
            self.action_timer = random.uniform(0.75, 1.7)

    def behavior_artistic_wrap(self, dt, state):
        global scan_velocity
        rf_wrap.visible = True and wrap_visible_by_user
        scan_velocity = 0.35 * math.sin(sim_time * 0.30)
        rf_wrap.pos.x = -0.78 + 0.08 * math.sin(sim_time * 0.7)
        rf_wrap.color = color_lerp(vector(1.0, 0.55, 0.05), vector(0.35, 0.75, 1.0), 0.5 + 0.5 * math.sin(sim_time * 1.1))

        if self.action_timer <= 0:
            ring_x = scan_slice.pos.x
            add_marker(
                spin=None,
                pos=vector(ring_x, random.uniform(-0.6, 1.25), random.uniform(-0.75, 0.75)),
                c=vector(random.uniform(0.2, 1.0), random.uniform(0.35, 1.0), 1.0),
                text="trace",
                attached=False,
                ttl=5.0,
            )
            rf_pulse(angle=random.uniform(0.10, 0.24), selective=True, center_x=ring_x)
            self.action_timer = random.uniform(0.55, 1.15)

    def behavior_chaotic_scramble(self, dt, state):
        global scan_velocity
        scan_velocity = random.uniform(-0.65, 0.65)
        rf_wrap.visible = True and wrap_visible_by_user

        set_field_strength(0.45 + 0.45 * (0.5 + 0.5 * math.sin(sim_time * 2.1)))

        if self.action_timer <= 0:
            if random.random() < 0.55:
                scramble_spins(fraction=random.uniform(0.12, 0.35))
            else:
                rf_pulse(angle=random.uniform(0.38, 0.85), selective=random.random() < 0.4)
            if spins:
                drone.attach_to(random.choice(spins))
            self.action_timer = random.uniform(0.45, 1.05)

    def behavior_constructive_organize(self, dt, state):
        global scan_velocity
        scan_velocity = -0.30 if scan_slice.pos.x > 0 else 0.30
        organize_spins(0.050 * dt)
        set_field_strength(1.48 + 0.08 * math.sin(sim_time * 0.32))

        if self.action_timer <= 0:
            if spins:
                candidates = sorted(spins, key=lambda s: s.alignment())
                for s in candidates[:3]:
                    add_marker(s, c=vector(0.05, 0.42, 1.0), text="order", ttl=3.8)
            self.action_timer = random.uniform(1.4, 2.5)

    def behavior_reset_loop(self, dt, state):
        global scan_velocity
        scan_velocity = 0.0
        set_field_strength(0.9)

        if self.mode_time < 0.25:
            rf_pulse(angle=0.10, selective=False)

        if self.mode_time > self.loop_delay:
            self.round_number += 1
            reset_round()
            self.metric_history.clear()
            self.completion_timer = 0.0
            self.choose_next_mode(reason="new_round")

ai = AIController()

# ------------------------------------------------------------
# Initial simulation state
# ------------------------------------------------------------

reset_round()

# ------------------------------------------------------------
# Keyboard controls
# ------------------------------------------------------------

def on_keydown(evt):
    global paused, manual_override_until, scan_velocity, wrap_visible_by_user

    k = evt.key
    manual_override_until = sim_time + 1.8

    if k == " ":
        paused = not paused

    elif k in ["a", "A"]:
        ai.enabled = not ai.enabled

    elif k in ["i", "I"]:
        ai.paused = not ai.paused

    elif k in ["r", "R"]:
        reset_round()
        ai.metric_history.clear()
        ai.completion_timer = 0.0

    elif k in ["p", "P"]:
        rf_pulse(angle=0.55, selective=False)

    elif k in ["s", "S"]:
        scramble_spins(fraction=1.0)

    elif k == "up":
        set_field_strength(target_field_strength + 0.15)

    elif k == "down":
        set_field_strength(target_field_strength - 0.15)

    elif k == "left":
        move_scan_slice(-0.22)

    elif k == "right":
        move_scan_slice(0.22)

    elif k in ["m", "M"]:
        ai.choose_next_mode(reason="manual")

    elif k in ["t", "T"]:
        attach_drone_to_nearest()

    elif k in ["d", "D"]:
        detach_drone()

    elif k in ["o", "O"]:
        drone.orbiting = not drone.orbiting

    elif k in ["c", "C"]:
        clear_markers()

    elif k in ["w", "W"]:
        wrap_visible_by_user = not wrap_visible_by_user
        rf_wrap.visible = wrap_visible_by_user and ai.mode in ["ARTISTIC_WRAP", "CHAOTIC_SCRAMBLE"]

scene.bind("keydown", on_keydown)

# ------------------------------------------------------------
# Main update helpers
# ------------------------------------------------------------

def update_field_visuals(dt):
    strength01 = clamp((field_strength - 0.15) / (2.25 - 0.15), 0, 1)
    tube_color = color_lerp(vector(0.15, 0.84, 1.0), vector(0.0, 0.36, 0.95), strength01)

    for i, tube in enumerate(field_tubes):
        tube.color = tube_color
        tube.opacity = 0.16 + 0.22 * strength01 + 0.035 * math.sin(sim_time * 2.0 + i)
        tube.radius = 0.014 + 0.010 * strength01

    for i, arr in enumerate(field_arrows):
        arr.color = tube_color
        arr.opacity = 0.32 + 0.25 * strength01
        arr.axis = vector(0.28 + 0.22 * strength01, 0, 0)
        arr.pos.x += dt * (0.22 + 0.22 * field_strength)
        if arr.pos.x > 4.25:
            arr.pos.x = -4.25

    magnet_shell.opacity = 0.09 + 0.06 * strength01
    for i, r in enumerate(magnet_rings):
        r.color = color_lerp(vector(0.42, 0.66, 0.95), vector(0.15, 0.38, 0.92), strength01)
        r.opacity = 0.60 + 0.28 * strength01

def update_scan_slice(dt):
    global scan_velocity

    if abs(scan_velocity) > 1e-5:
        scan_slice.pos.x += scan_velocity * dt
        if scan_slice.pos.x < scan_min_x:
            scan_slice.pos.x = scan_min_x
            scan_velocity = abs(scan_velocity)
        if scan_slice.pos.x > scan_max_x:
            scan_slice.pos.x = scan_max_x
            scan_velocity = -abs(scan_velocity)

    scan_label.pos = scan_slice.pos + vector(0, 2.0, 0)
    scan_label.text = "movable scan slice  x={:.2f}".format(scan_slice.pos.x)

def update_rf_visuals(dt):
    global rf_flash_timer

    rf_flash_timer = max(0, rf_flash_timer - dt)
    flash = clamp(rf_flash_timer / 0.45, 0, 1)
    rf_coil.opacity = 0.32 + 0.42 * flash
    rf_coil.thickness = 0.035 + 0.025 * flash
    rf_coil.color = color_lerp(vector(1.0, 0.52, 0.05), vector(1.0, 0.18, 0.72), flash)

    if rf_wrap.visible:
        rf_wrap.rotate(angle=0.55 * dt, axis=vector(1, 0, 0), origin=rf_wrap.pos)

def update_status():
    if len(spins) > 0:
        avg_alignment = sum((s.alignment() + 1) / 2 for s in spins) / len(spins)
        avg_transverse = sum(s.transverse() for s in spins) / len(spins)
    else:
        avg_alignment = 0
        avg_transverse = 0

    status_label.text = (
        "AI: {ai_state}  mode: {mode}  round: {round_no}\n"
        "B0 strength: {B:.2f}  scan x: {sx:.2f}  spins: {n}\n"
        "alignment: {al:.2f}  transverse: {tr:.2f}  pulses: {p}  markers: {m}\n"
        "paused: {paused}  manual override: {override}"
    ).format(
        ai_state=("ON" if ai.enabled and not ai.paused else "OFF/PAUSED"),
        mode=ai.mode,
        round_no=ai.round_number,
        B=field_strength,
        sx=scan_slice.pos.x,
        n=len(spins),
        al=avg_alignment,
        tr=avg_transverse,
        p=len(pulses),
        m=len(markers),
        paused=paused,
        override=("yes" if sim_time < manual_override_until else "no"),
    )

# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

last_dt = 1 / 60

while True:
    rate(60)

    dt = last_dt
    if paused:
        update_status()
        continue

    sim_time += dt

    # Human override lets keyboard input temporarily dominate but does not disable AI.
    if ai.enabled and not ai.paused and sim_time >= manual_override_until:
        ai.update(dt)

    # Smoothly move real field toward commanded target.
    field_strength += (target_field_strength - field_strength) * clamp(2.0 * dt, 0, 1)

    update_scan_slice(dt)
    update_field_visuals(dt)
    update_rf_visuals(dt)

    for s in spins:
        s.update(dt, field_strength)

    # Update pulses.
    alive_pulses = []
    for p in pulses:
        if p.update(dt):
            alive_pulses.append(p)
        else:
            p.destroy()
    pulses[:] = alive_pulses

    # Update RF waves.
    alive_waves = []
    for w in rf_waves:
        if w.update(dt):
            alive_waves.append(w)
        else:
            w.destroy()
    rf_waves[:] = alive_waves

    # Update markers.
    alive_markers = []
    for m in markers:
        if m.update(dt):
            alive_markers.append(m)
        else:
            m.destroy()
    markers[:] = alive_markers

    drone.update(dt)

    update_status()
