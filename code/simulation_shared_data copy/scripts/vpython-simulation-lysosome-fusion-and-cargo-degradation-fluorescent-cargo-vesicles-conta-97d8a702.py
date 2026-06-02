from vpython import *
import random
import math

# Lysosome Fusion and Cargo Degradation
# VPython self-contained simulation with an automatic expressive AI controller.
# Controls:
#   SPACE pause/resume
#   A     toggle AI
#   R     reset round
#   TAB   select next cargo vesicle
#   W/S/A/D or arrow keys move selected cargo
#   Q/E   move selected cargo down/up
#   O     attach selected cargo to AI orbit around nearest lysosome
#   X     spill selected cargo
#   F     force-fuse selected cargo with nearest lysosome
#   M     mark/recolor selected cargo
#   C     switch AI mode
#   P     pause/resume AI only


scene.title = "Lysosome Fusion and Cargo Degradation - AI Controlled 3D Simulation"
scene.background = vector(0.94, 0.97, 1.0)
scene.width = 1200
scene.height = 760
scene.forward = vector(-0.7, -0.45, -0.7)
scene.up = vector(0, 1, 0)
scene.userspin = True
scene.userzoom = True
scene.caption = (
    "\nLight 3D cell-space simulation. Fluorescent cargo vesicles wander, bounce, spill, orbit, "
    "and fuse with stationary acidic lysosomes. Internal cargo particles transfer into lysosomes, "
    "mix, shrink, fade, and disappear. An AI behavior system can herd, orbit, spill, mark, dip, "
    "chaotically stir, or artistically organize the scene.\n\n"
)


def randf(a, b):
    return random.uniform(a, b)


def random_unit():
    while True:
        v = vector(randf(-1, 1), randf(-1, 1), randf(-1, 1))
        if mag(v) > 0.0001:
            return norm(v)


def random_inside_sphere(radius):
    return random_unit() * (radius * (random.random() ** (1.0 / 3.0)))


def clamp_mag(v, max_m):
    m = mag(v)
    if m > max_m and m > 0:
        return norm(v) * max_m
    return v


def mix_color(a, b, t):
    t = max(0, min(1, t))
    return a * (1 - t) + b * t


def hsv(h, s, v):
    return color.hsv_to_rgb(vector(h % 1.0, s, v))


def bounce_in_box(obj, bounds, damping=0.83):
    p = obj.pos
    v = obj.vel
    r = getattr(obj, "radius", 0.2)

    if p.x > bounds - r:
        p.x = bounds - r
        v.x = -abs(v.x) * damping
    elif p.x < -bounds + r:
        p.x = -bounds + r
        v.x = abs(v.x) * damping

    if p.y > bounds - r:
        p.y = bounds - r
        v.y = -abs(v.y) * damping
    elif p.y < -bounds + r:
        p.y = -bounds + r
        v.y = abs(v.y) * damping

    if p.z > bounds - r:
        p.z = bounds - r
        v.z = -abs(v.z) * damping
    elif p.z < -bounds + r:
        p.z = -bounds + r
        v.z = abs(v.z) * damping

    obj.pos = p
    obj.vel = v


class TransientEffect:
    def __init__(self, sim, visual, ttl=1.0, expand=0.0, fade=True):
        self.sim = sim
        self.visual = visual
        self.ttl = ttl
        self.life = ttl
        self.expand = expand
        self.fade = fade
        self.start_opacity = getattr(visual, "opacity", 1.0)
        self.start_radius = getattr(visual, "radius", 1.0)
        sim.dynamic_visuals.append(visual)

    def update(self, dt):
        self.life -= dt
        t = max(0, self.life / max(0.001, self.ttl))
        if self.fade and hasattr(self.visual, "opacity"):
            self.visual.opacity = self.start_opacity * t
        if self.expand != 0 and hasattr(self.visual, "radius"):
            self.visual.radius = self.start_radius + self.expand * (1 - t)
        if self.life <= 0:
            self.visual.visible = False
            return False
        return True


class Lysosome:
    def __init__(self, sim, pos, radius, name, hue):
        self.sim = sim
        self.pos = vector(pos)
        self.radius = radius
        self.name = name
        self.hue = hue
        self.base_color = hsv(hue, 0.62, 0.95)
        self.acid_color = hsv(hue + 0.06, 0.82, 1.0)
        self.glow_timer = 0.0
        self.digest_count = 0

        self.halo = sphere(
            pos=self.pos,
            radius=radius * 1.45,
            color=self.acid_color,
            opacity=0.07,
            shininess=0,
            emissive=True,
        )
        self.shell = sphere(
            pos=self.pos,
            radius=radius,
            color=self.base_color,
            opacity=0.28,
            shininess=0.45,
        )
        self.core = sphere(
            pos=self.pos,
            radius=radius * 0.62,
            color=mix_color(self.base_color, color.white, 0.25),
            opacity=0.15,
            emissive=True,
            shininess=0,
        )
        self.label = label(
            pos=self.pos + vector(0, radius + 0.75, 0),
            text=name + "\nacidic lysosome",
            height=10,
            color=vector(0.22, 0.16, 0.30),
            box=False,
            opacity=0,
        )

        for v in [self.halo, self.shell, self.core, self.label]:
            sim.dynamic_visuals.append(v)

    def brighten(self, amount=1.0):
        self.glow_timer = max(self.glow_timer, 1.25 * amount)
        self.digest_count += 1

    def ingest_particle(self, particle):
        particle.start_degrading(self)
        self.brighten(1.0)

    def update(self, dt):
        self.glow_timer = max(0, self.glow_timer - dt)
        glow = min(1, self.glow_timer / 1.25)

        self.halo.radius = self.radius * (1.45 + 0.38 * glow)
        self.halo.opacity = 0.055 + 0.22 * glow
        self.halo.color = mix_color(self.base_color, color.white, glow * 0.58)

        self.shell.opacity = 0.25 + 0.17 * glow
        self.shell.color = mix_color(self.base_color, color.white, glow * 0.43)

        self.core.opacity = 0.13 + 0.24 * glow
        self.core.color = mix_color(self.acid_color, color.white, glow * 0.68)
        self.label.text = self.name + "\nacidic lysosome\ncargo degraded: " + str(self.digest_count)


class CargoParticle:
    def __init__(self, sim, cargo, local_pos, radius, col):
        self.sim = sim
        self.cargo = cargo
        self.local_pos = vector(local_pos)
        self.local_vel = random_unit() * randf(0.12, 0.42)
        self.pos = cargo.pos + self.local_pos
        self.vel = vector(0, 0, 0)
        self.radius0 = radius
        self.radius = radius
        self.color0 = col
        self.state = "in_cargo"
        self.lysosome = None
        self.dead = False
        self.age = 0

        self.visual = sphere(
            pos=self.pos,
            radius=self.radius,
            color=col,
            opacity=0.95,
            shininess=0.5,
            emissive=True,
        )
        sim.dynamic_visuals.append(self.visual)

    def update_inside_cargo(self, dt):
        if not self.cargo or not self.cargo.active:
            return

        self.age += dt
        self.local_vel += random_unit() * randf(0.02, 0.08)
        self.local_vel += cross(vector(0, 1, 0), self.local_pos) * self.cargo.spin * dt * 0.7
        self.local_vel *= 0.965

        self.local_pos += self.local_vel * dt
        limit = self.cargo.radius * 0.66
        if mag(self.local_pos) > limit:
            n = norm(self.local_pos)
            self.local_pos = n * limit
            self.local_vel -= 2 * dot(self.local_vel, n) * n
            self.local_vel *= 0.75

        pulse = 0.08 * math.sin(self.age * 4.5 + self.radius0 * 30)
        self.visual.radius = max(0.025, self.radius * (1 + pulse))
        self.pos = self.cargo.pos + self.local_pos
        self.visual.pos = self.pos

    def become_free(self, inherited_vel):
        self.state = "free"
        self.cargo = None
        self.vel = inherited_vel + random_unit() * randf(0.55, 1.55)
        self.visual.opacity = 0.9
        self.visual.make_trail = True
        self.visual.retain = 38
        self.visual.trail_color = self.visual.color

    def start_degrading(self, lysosome):
        self.state = "degrading"
        self.cargo = None
        self.lysosome = lysosome
        if mag(self.pos - lysosome.pos) > lysosome.radius * 0.83:
            self.pos = lysosome.pos + norm(self.pos - lysosome.pos) * lysosome.radius * randf(0.35, 0.78)
        self.vel = random_unit() * randf(0.35, 1.2) + cross(vector(0, 1, 0), self.pos - lysosome.pos) * 0.28
        self.visual.pos = self.pos
        self.visual.opacity = 0.95
        self.visual.emissive = True
        self.visual.make_trail = True
        self.visual.retain = 28
        self.visual.trail_color = mix_color(self.visual.color, color.white, 0.35)

    def update_free(self, dt):
        self.age += dt
        self.vel += random_unit() * 0.18 * dt
        self.vel *= 0.992
        self.pos += self.vel * dt

        holder = type("Holder", (), {})()
        holder.pos = self.pos
        holder.vel = self.vel
        holder.radius = self.radius
        bounce_in_box(holder, self.sim.bounds, damping=0.86)
        self.pos = holder.pos
        self.vel = holder.vel

        self.visual.pos = self.pos
        self.visual.radius = self.radius * (1 + 0.08 * math.sin(self.age * 8))

        for lys in self.sim.lysosomes:
            if mag(self.pos - lys.pos) < lys.radius * 0.92:
                lys.ingest_particle(self)
                break

    def update_degrading(self, dt):
        if not self.lysosome:
            return

        self.age += dt
        rvec = self.pos - self.lysosome.pos
        d = mag(rvec)
        if d < 0.001:
            rvec = random_unit() * 0.01
            d = mag(rvec)

        tangent = cross(vector(0, 1, 0), rvec)
        if mag(tangent) < 0.001:
            tangent = cross(vector(1, 0, 0), rvec)
        tangent = norm(tangent)

        # Mix, orbit, acid-dip, and shrink inside the lysosome.
        inward = -norm(rvec) * 0.20
        swirl = tangent * (0.92 / max(0.3, d))
        jitter = random_unit() * 0.12
        self.vel += (inward + swirl + jitter) * dt
        self.vel *= 0.982
        self.pos += self.vel * dt

        inner = self.lysosome.radius * 0.78
        if mag(self.pos - self.lysosome.pos) > inner:
            n = norm(self.pos - self.lysosome.pos)
            self.pos = self.lysosome.pos + n * inner
            self.vel -= 2 * dot(self.vel, n) * n
            self.vel *= 0.72

        acid_speed = 0.022 + 0.018 * (self.lysosome.glow_timer > 0)
        self.radius -= acid_speed * dt
        self.visual.radius = max(0.004, self.radius)
        self.visual.opacity = max(0, min(0.95, self.radius / self.radius0))
        self.visual.color = mix_color(self.color0, self.lysosome.acid_color, 0.45 + 0.35 * math.sin(self.age * 3) ** 2)
        self.visual.pos = self.pos

        if self.radius <= self.radius0 * 0.08:
            self.dead = True
            self.visual.visible = False
            try:
                self.visual.clear_trail()
            except Exception:
                pass

    def update(self, dt):
        if self.dead:
            return

        if self.state == "in_cargo":
            return
        elif self.state == "free":
            self.update_free(dt)
        elif self.state == "degrading":
            self.update_degrading(dt)


class CargoVesicle:
    def __init__(self, sim, pos, radius, hue, name):
        self.sim = sim
        self.name = name
        self.pos = vector(pos)
        self.vel = random_unit() * randf(0.35, 0.95)
        self.radius = radius
        self.hue = hue
        self.base_color = hsv(hue, 0.72, 1.0)
        self.active = True
        self.fused = False
        self.spilled = False
        self.marked = False
        self.ai_attached = False
        self.orbit_target = None
        self.orbit_phase = randf(0, 2 * math.pi)
        self.orbit_axis = random_unit()
        self.spin = randf(-0.6, 0.6)
        self.age = 0

        self.shell = sphere(
            pos=self.pos,
            radius=radius,
            color=self.base_color,
            opacity=0.23,
            shininess=0.65,
            make_trail=True,
            retain=90,
            trail_color=mix_color(self.base_color, color.white, 0.3),
        )
        self.mem = sphere(
            pos=self.pos,
            radius=radius * 1.04,
            color=mix_color(self.base_color, color.white, 0.32),
            opacity=0.075,
            shininess=0.2,
        )
        self.label = label(
            pos=self.pos + vector(0, radius + 0.34, 0),
            text=name,
            height=8,
            color=vector(0.16, 0.22, 0.28),
            box=False,
            opacity=0,
        )

        sim.dynamic_visuals += [self.shell, self.mem, self.label]
        self.particles = []

        particle_count = random.randint(6, 10)
        for i in range(particle_count):
            ph = (hue + randf(-0.15, 0.22)) % 1.0
            col = hsv(ph, randf(0.55, 0.95), randf(0.85, 1.0))
            p = CargoParticle(
                sim,
                self,
                random_inside_sphere(radius * 0.55),
                randf(0.055, 0.095),
                col,
            )
            self.particles.append(p)
            sim.particles.append(p)

    def alive_particles(self):
        return [p for p in self.particles if not p.dead]

    def apply_force(self, force, dt):
        if self.active:
            self.vel += force * dt

    def mark(self):
        self.marked = True
        self.base_color = hsv(randf(0, 1), 0.85, 1.0)
        self.shell.color = self.base_color
        self.shell.trail_color = mix_color(self.base_color, color.white, 0.4)
        self.mem.color = mix_color(self.base_color, color.white, 0.5)
        for p in self.particles:
            if p.state == "in_cargo":
                p.color0 = hsv(randf(0, 1), 0.9, 1.0)
                p.visual.color = p.color0

    def attach_orbit(self, lysosome):
        self.ai_attached = True
        self.orbit_target = lysosome
        self.orbit_phase = randf(0, 2 * math.pi)
        self.orbit_axis = random_unit()
        self.shell.trail_color = color.white

    def detach_orbit(self):
        self.ai_attached = False
        self.orbit_target = None
        self.vel += random_unit() * 0.7
        self.shell.trail_color = mix_color(self.base_color, color.white, 0.25)

    def spill(self):
        if not self.active:
            return

        self.active = False
        self.spilled = True
        self.shell.opacity = 0.03
        self.mem.opacity = 0.02
        self.label.visible = False

        burst = sphere(
            pos=self.pos,
            radius=self.radius * 0.75,
            color=mix_color(self.base_color, color.white, 0.55),
            opacity=0.22,
            emissive=True,
        )
        self.sim.effects.append(TransientEffect(self.sim, burst, ttl=0.85, expand=self.radius * 1.45, fade=True))

        for p in self.particles:
            if not p.dead and p.state == "in_cargo":
                p.become_free(self.vel)

    def fuse_with(self, lysosome):
        if not self.active:
            return

        self.active = False
        self.fused = True
        self.ai_attached = False

        direction = self.pos - lysosome.pos
        if mag(direction) < 0.001:
            direction = random_unit()
        n = norm(direction)
        contact = lysosome.pos + n * lysosome.radius * 0.94

        self.shell.visible = False
        self.mem.visible = False
        self.label.visible = False
        try:
            self.shell.clear_trail()
        except Exception:
            pass

        ring = torus(
            pos=contact,
            axis=n,
            radius=self.radius * 0.78,
            thickness=0.035,
            color=mix_color(self.base_color, color.white, 0.35),
            opacity=0.58,
            emissive=True,
        )
        wrap = sphere(
            pos=contact,
            radius=self.radius * 0.45,
            color=self.base_color,
            opacity=0.18,
            emissive=True,
        )
        self.sim.effects.append(TransientEffect(self.sim, ring, ttl=1.25, expand=0.22, fade=True))
        self.sim.effects.append(TransientEffect(self.sim, wrap, ttl=1.05, expand=0.65, fade=True))

        lysosome.brighten(1.35)

        for p in self.particles:
            if not p.dead and p.state == "in_cargo":
                # Transfer cargo into the lysosome volume.
                offset = p.local_pos
                p.pos = contact * 0.52 + (lysosome.pos + offset) * 0.48
                p.start_degrading(lysosome)

    def update(self, dt):
        if not self.active:
            return

        self.age += dt
        self.spin += randf(-0.35, 0.35) * dt
        self.spin = max(-2.5, min(2.5, self.spin))

        # Brownian vesicle motion unless AI/human steering dominates.
        self.vel += random_unit() * randf(0.06, 0.16) * dt
        self.vel *= 0.992
        self.vel = clamp_mag(self.vel, 3.2)
        self.pos += self.vel * dt

        holder = type("Holder", (), {})()
        holder.pos = self.pos
        holder.vel = self.vel
        holder.radius = self.radius
        bounce_in_box(holder, self.sim.bounds, damping=0.82)
        self.pos = holder.pos
        self.vel = holder.vel

        pulse = 1 + 0.025 * math.sin(self.age * 3.3 + self.hue * 10)
        self.shell.pos = self.pos
        self.mem.pos = self.pos
        self.shell.radius = self.radius * pulse
        self.mem.radius = self.radius * (1.04 + 0.02 * math.sin(self.age * 2.7))
        self.label.pos = self.pos + vector(0, self.radius + 0.34, 0)

        if self.marked:
            self.mem.opacity = 0.11 + 0.05 * math.sin(self.age * 5) ** 2

        for p in self.particles:
            if p.state == "in_cargo" and not p.dead:
                p.update_inside_cargo(dt)

        # Collision/fusion with stationary lysosomes.
        for lys in self.sim.lysosomes:
            if mag(self.pos - lys.pos) < lys.radius + self.radius * 0.78:
                self.fuse_with(lys)
                break


class AIController:
    def __init__(self, sim):
        self.sim = sim
        self.enabled = True
        self.paused = False

        self.modes = [
            "EXPLORE",
            "HERD_TO_ACID",
            "CAREFUL_ONE_BY_ONE",
            "ORBIT_RITUAL",
            "DIP_AND_PULL",
            "SPILL_AND_MIX",
            "MARK_AND_SORT",
            "CHAOTIC_STIR",
            "ARTISTIC_SPIRAL",
        ]

        self.mode = "EXPLORE"
        self.previous_mode = None
        self.mode_time = 0.0
        self.next_switch = randf(5.5, 10.0)
        self.last_signature = None
        self.stagnation_time = 0.0
        self.completion_time = 0.0
        self.loop_delay = 3.0
        self.action_cooldown = 0.0
        self.rounds_started_by_ai = 0

    def active_cargos(self):
        return [c for c in self.sim.cargos if c.active]

    def free_particles(self):
        return [p for p in self.sim.particles if (not p.dead and p.state == "free")]

    def degrading_particles(self):
        return [p for p in self.sim.particles if (not p.dead and p.state == "degrading")]

    def nearest_lysosome(self, pos):
        if not self.sim.lysosomes:
            return None
        return min(self.sim.lysosomes, key=lambda l: mag(l.pos - pos))

    def simulation_signature(self):
        active = len(self.active_cargos())
        free = len(self.free_particles())
        degrading = len(self.degrading_particles())
        in_cargo = len([p for p in self.sim.particles if (not p.dead and p.state == "in_cargo")])
        dead = len([p for p in self.sim.particles if p.dead])
        digestion = sum(l.digest_count for l in self.sim.lysosomes)
        return (active, free, degrading, in_cargo, dead, digestion)

    def state_summary(self):
        active = self.active_cargos()
        free = self.free_particles()
        degrading = self.degrading_particles()
        avg_speed = 0.0
        if active:
            avg_speed = sum(mag(c.vel) for c in active) / len(active)

        nearest_distance = None
        if active:
            distances = []
            for c in active:
                lys = self.nearest_lysosome(c.pos)
                if lys:
                    distances.append(max(0, mag(c.pos - lys.pos) - lys.radius - c.radius))
            if distances:
                nearest_distance = min(distances)

        return {
            "active_cargos": len(active),
            "free_particles": len(free),
            "degrading_particles": len(degrading),
            "avg_cargo_speed": avg_speed,
            "nearest_fusion_gap": nearest_distance,
            "total_alive_particles": len([p for p in self.sim.particles if not p.dead]),
        }

    def choose_new_mode(self, reason="time"):
        summary = self.state_summary()
        choices = list(self.modes)

        if summary["active_cargos"] <= 0:
            choices = ["CHAOTIC_STIR", "ARTISTIC_SPIRAL", "EXPLORE"]
        elif summary["active_cargos"] <= 2:
            choices = ["CAREFUL_ONE_BY_ONE", "HERD_TO_ACID", "DIP_AND_PULL", "MARK_AND_SORT"]
        elif summary["free_particles"] > 8:
            choices = ["HERD_TO_ACID", "CHAOTIC_STIR", "ARTISTIC_SPIRAL"]
        elif self.stagnation_time > 5:
            choices = ["CHAOTIC_STIR", "SPILL_AND_MIX", "HERD_TO_ACID"]
        elif reason == "play":
            choices = ["ORBIT_RITUAL", "MARK_AND_SORT", "ARTISTIC_SPIRAL", "DIP_AND_PULL"]

        if self.mode in choices and len(choices) > 1:
            choices.remove(self.mode)

        self.previous_mode = self.mode
        self.mode = random.choice(choices)
        self.mode_time = 0.0
        self.next_switch = randf(5.5, 12.0)
        self.action_cooldown = 0.0

        # Detach orbit when leaving ritual modes sometimes, to avoid permanent sameness.
        if self.previous_mode in ["ORBIT_RITUAL", "ARTISTIC_SPIRAL"] and self.mode not in ["ORBIT_RITUAL", "ARTISTIC_SPIRAL"]:
            for c in self.active_cargos():
                if random.random() < 0.55:
                    c.detach_orbit()

    def steer_cargo_to(self, cargo, target, dt, strength=1.8, max_speed=2.2):
        desired = target - cargo.pos
        if mag(desired) < 0.001:
            return
        desired_v = norm(desired) * max_speed
        steering = (desired_v - cargo.vel) * strength
        cargo.apply_force(steering, dt)

    def steer_particle_to(self, particle, target, dt, strength=1.2, max_speed=1.6):
        desired = target - particle.pos
        if mag(desired) < 0.001:
            return
        particle.vel += (norm(desired) * max_speed - particle.vel) * strength * dt

    def execute_explore(self, dt):
        for c in self.active_cargos():
            c.apply_force(random_unit() * 0.55, dt)
            if random.random() < 0.004:
                c.detach_orbit()

    def execute_herd(self, dt):
        for c in self.active_cargos():
            lys = self.nearest_lysosome(c.pos)
            if lys:
                target = lys.pos + norm(c.pos - lys.pos) * (lys.radius * 0.12)
                self.steer_cargo_to(c, target, dt, strength=2.4, max_speed=2.8)

        for p in self.free_particles():
            lys = self.nearest_lysosome(p.pos)
            if lys:
                self.steer_particle_to(p, lys.pos, dt, strength=1.4, max_speed=1.9)

    def execute_careful(self, dt):
        active = self.active_cargos()
        if not active:
            return

        target_cargo = min(active, key=lambda c: mag(c.pos - self.nearest_lysosome(c.pos).pos))
        lys = self.nearest_lysosome(target_cargo.pos)
        self.steer_cargo_to(target_cargo, lys.pos, dt, strength=1.6, max_speed=1.55)

        for c in active:
            if c is not target_cargo:
                c.vel *= 0.982
                safe = c.pos - lys.pos
                if mag(safe) < lys.radius + c.radius + 1.3:
                    self.steer_cargo_to(c, lys.pos + norm(safe) * (lys.radius + c.radius + 2.0), dt, strength=0.8, max_speed=1.0)

    def execute_orbit(self, dt):
        active = self.active_cargos()
        if not active:
            return

        for i, c in enumerate(active):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            if not c.ai_attached or c.orbit_target is not lys:
                c.attach_orbit(lys)

            c.orbit_phase += dt * (0.55 + 0.08 * i)
            radius = lys.radius + c.radius + 1.25 + 0.22 * (i % 3)
            y = 0.45 * math.sin(c.orbit_phase * 1.7 + i)

            target = lys.pos + vector(
                math.cos(c.orbit_phase) * radius,
                y,
                math.sin(c.orbit_phase) * radius,
            )
            self.steer_cargo_to(c, target, dt, strength=2.7, max_speed=2.25)

            if self.mode_time > 3.0 and random.random() < 0.0015:
                c.detach_orbit()

    def execute_dip_and_pull(self, dt):
        active = self.active_cargos()
        if not active:
            return

        for i, c in enumerate(active):
            lys = self.nearest_lysosome(c.pos)
            r = lys.radius + c.radius + 0.25 + 0.8 * (0.5 + 0.5 * math.sin(self.mode_time * 1.35 + i))
            direction = c.pos - lys.pos
            if mag(direction) < 0.001:
                direction = random_unit()

            # Alternate between almost-colliding dips and pulling back to a safe shell.
            target = lys.pos + norm(direction) * r
            self.steer_cargo_to(c, target, dt, strength=2.0, max_speed=2.0)

            # Occasionally commit the dip into a fusion.
            if random.random() < 0.0018 and mag(c.pos - lys.pos) < lys.radius + c.radius + 0.55:
                self.steer_cargo_to(c, lys.pos, dt, strength=5.0, max_speed=3.1)

    def execute_spill_and_mix(self, dt):
        active = self.active_cargos()

        self.action_cooldown -= dt
        if active and self.action_cooldown <= 0:
            candidate = random.choice(active)
            if random.random() < 0.55:
                candidate.spill()
            else:
                candidate.mark()
            self.action_cooldown = randf(1.8, 3.8)

        for p in self.free_particles():
            lys = self.nearest_lysosome(p.pos)
            if lys:
                swirl = cross(vector(0, 1, 0), p.pos - lys.pos)
                if mag(swirl) > 0.001:
                    p.vel += norm(swirl) * 0.55 * dt
                if random.random() < 0.35:
                    self.steer_particle_to(p, lys.pos, dt, strength=0.9, max_speed=1.8)

    def execute_mark_and_sort(self, dt):
        active = self.active_cargos()
        if not active:
            return

        self.action_cooldown -= dt
        if self.action_cooldown <= 0:
            random.choice(active).mark()
            self.action_cooldown = randf(1.0, 2.0)

        sorted_cargos = sorted(active, key=lambda c: c.hue)
        for i, c in enumerate(sorted_cargos):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            lane = lys.radius + c.radius + 1.7 + (i // len(self.sim.lysosomes)) * 0.42
            angle = i * 2.399963 + self.mode_time * 0.18
            target = lys.pos + vector(math.cos(angle) * lane, 1.0 + 0.18 * i, math.sin(angle) * lane)
            self.steer_cargo_to(c, target, dt, strength=1.8, max_speed=1.7)

    def execute_chaotic_stir(self, dt):
        for c in self.active_cargos():
            center_push = -norm(c.pos) * 0.25 if mag(c.pos) > 0.1 else random_unit()
            c.apply_force(random_unit() * 3.4 + center_push, dt)
            c.spin += randf(-4, 4) * dt
            if random.random() < 0.0025:
                c.mark()
            if random.random() < 0.0012:
                c.spill()

        for p in self.free_particles():
            p.vel += random_unit() * 1.8 * dt

    def execute_artistic_spiral(self, dt):
        active = self.active_cargos()
        center = vector(0, 0, 0)

        for i, c in enumerate(active):
            angle = self.mode_time * 0.38 + i * 1.618
            radius = 2.2 + 0.34 * i
            target = center + vector(math.cos(angle) * radius, math.sin(angle * 0.7) * 1.4, math.sin(angle) * radius)
            self.steer_cargo_to(c, target, dt, strength=2.1, max_speed=2.0)
            if random.random() < 0.002:
                c.mark()

        # Make a few free particles draw inward ribbons toward lysosomes.
        for i, p in enumerate(self.free_particles()):
            lys = self.sim.lysosomes[i % len(self.sim.lysosomes)]
            angle = self.mode_time + i
            target = lys.pos + vector(math.cos(angle), math.sin(angle * 0.3), math.sin(angle)) * (lys.radius * 0.55)
            self.steer_particle_to(p, target, dt, strength=0.9, max_speed=1.3)

    def reset_if_complete_or_stagnant(self, dt):
        sig = self.simulation_signature()

        if self.last_signature is None:
            self.last_signature = sig

        if sig == self.last_signature:
            self.stagnation_time += dt
        else:
            self.stagnation_time = max(0, self.stagnation_time - dt * 0.7)
            self.last_signature = sig

        summary = self.state_summary()
        complete = (
            summary["active_cargos"] == 0
            and summary["free_particles"] == 0
            and summary["degrading_particles"] == 0
        )
        empty_or_stable = (
            summary["total_alive_particles"] == 0
            or (summary["active_cargos"] == 0 and summary["degrading_particles"] == 0)
        )

        if complete or empty_or_stable:
            self.completion_time += dt
        else:
            self.completion_time = 0.0

        if self.completion_time > self.loop_delay:
            self.rounds_started_by_ai += 1
            self.sim.reset(reason="AI loop: completed degradation")
            self.last_signature = None
            self.completion_time = 0.0
            self.stagnation_time = 0.0
            self.choose_new_mode("play")
            return

        if self.stagnation_time > 11.0:
            # First try to break stagnation with a more disruptive behavior.
            if self.mode not in ["CHAOTIC_STIR", "SPILL_AND_MIX", "HERD_TO_ACID"]:
                self.choose_new_mode("stagnation")
            elif self.stagnation_time > 18.0:
                self.rounds_started_by_ai += 1
                self.sim.reset(reason="AI loop: stagnation reset")
                self.last_signature = None
                self.completion_time = 0.0
                self.stagnation_time = 0.0
                self.choose_new_mode("play")

    def update(self, dt):
        if not self.enabled or self.paused:
            return
        if self.sim.time < self.sim.manual_override_until:
            return

        self.mode_time += dt
        self.reset_if_complete_or_stagnant(dt)

        if self.mode_time > self.next_switch:
            self.choose_new_mode("time")

        if self.mode == "EXPLORE":
            self.execute_explore(dt)
        elif self.mode == "HERD_TO_ACID":
            self.execute_herd(dt)
        elif self.mode == "CAREFUL_ONE_BY_ONE":
            self.execute_careful(dt)
        elif self.mode == "ORBIT_RITUAL":
            self.execute_orbit(dt)
        elif self.mode == "DIP_AND_PULL":
            self.execute_dip_and_pull(dt)
        elif self.mode == "SPILL_AND_MIX":
            self.execute_spill_and_mix(dt)
        elif self.mode == "MARK_AND_SORT":
            self.execute_mark_and_sort(dt)
        elif self.mode == "CHAOTIC_STIR":
            self.execute_chaotic_stir(dt)
        elif self.mode == "ARTISTIC_SPIRAL":
            self.execute_artistic_spiral(dt)


class Simulation:
    def __init__(self):
        self.bounds = 7.2
        self.time = 0.0
        self.round_number = 0
        self.paused = False
        self.manual_override_until = -1
        self.dynamic_visuals = []
        self.lysosomes = []
        self.cargos = []
        self.particles = []
        self.effects = []
        self.ai = None
        self.selected_index = 0
        self.last_reset_reason = "initial"

        self.world_box = box(
            pos=vector(0, 0, 0),
            size=vector(self.bounds * 2, self.bounds * 2, self.bounds * 2),
            color=vector(0.55, 0.76, 0.92),
            opacity=0.035,
            shininess=0,
        )

        self.status = label(
            pos=vector(0, self.bounds + 1.75, 0),
            text="",
            height=11,
            color=vector(0.12, 0.17, 0.23),
            box=False,
            opacity=0,
        )

        self.selection_marker = sphere(
            pos=vector(0, 0, 0),
            radius=0.8,
            color=color.white,
            opacity=0.16,
            emissive=True,
            visible=False,
        )

        self.reset(reason="initial setup")

    def register_visual(self, obj):
        self.dynamic_visuals.append(obj)
        return obj

    def hide_dynamic_visuals(self):
        for v in self.dynamic_visuals:
            try:
                v.visible = False
            except Exception:
                pass
            try:
                v.clear_trail()
            except Exception:
                pass
        self.dynamic_visuals = []

    def reset(self, reason="manual reset"):
        self.hide_dynamic_visuals()

        self.round_number += 1
        self.time = 0.0
        self.manual_override_until = -1
        self.last_reset_reason = reason

        self.lysosomes = []
        self.cargos = []
        self.particles = []
        self.effects = []
        self.selected_index = 0
        self.selection_marker.visible = False

        # Stationary acidic lysosomes.
        lys_specs = [
            (vector(-3.6, -0.6, -2.4), 1.18, "Lysosome A", 0.82),
            (vector(3.5, 0.4, -1.2), 1.34, "Lysosome B", 0.76),
            (vector(0.1, 1.0, 3.2), 1.08, "Lysosome C", 0.88),
        ]
        for pos, rad, name, hue in lys_specs:
            self.lysosomes.append(Lysosome(self, pos, rad, name, hue))

        # Moving fluorescent cargo vesicles.
        cargo_count = random.randint(8, 11)
        for i in range(cargo_count):
            while True:
                p = vector(randf(-5.8, 5.8), randf(-4.6, 4.6), randf(-5.8, 5.8))
                if all(mag(p - l.pos) > l.radius + 1.9 for l in self.lysosomes):
                    break
            c = CargoVesicle(
                self,
                p,
                randf(0.42, 0.62),
                (i / max(1, cargo_count) + randf(-0.04, 0.04)) % 1.0,
                "cargo " + str(i + 1),
            )
            self.cargos.append(c)

        burst = sphere(
            pos=vector(0, 0, 0),
            radius=0.25,
            color=vector(0.75, 0.93, 1.0),
            opacity=0.24,
            emissive=True,
        )
        self.effects.append(TransientEffect(self, burst, ttl=1.1, expand=2.8, fade=True))

    def active_cargos(self):
        return [c for c in self.cargos if c.active]

    def selected_cargo(self):
        active = self.active_cargos()
        if not active:
            return None
        self.selected_index %= len(active)
        return active[self.selected_index]

    def select_next(self):
        active = self.active_cargos()
        if active:
            self.selected_index = (self.selected_index + 1) % len(active)

    def manual_override(self, seconds=4.0):
        self.manual_override_until = self.time + seconds

    def nearest_lysosome(self, pos):
        return min(self.lysosomes, key=lambda l: mag(l.pos - pos))

    def force_fuse_selected(self):
        c = self.selected_cargo()
        if c:
            lys = self.nearest_lysosome(c.pos)
            c.fuse_with(lys)

    def update_selection_marker(self):
        c = self.selected_cargo()
        if c and c.active:
            self.selection_marker.visible = True
            self.selection_marker.pos = c.pos
            self.selection_marker.radius = c.radius * 1.55 + 0.04 * math.sin(self.time * 7)
            self.selection_marker.color = mix_color(c.base_color, color.white, 0.65)
        else:
            self.selection_marker.visible = False

    def update_status(self):
        active = len([c for c in self.cargos if c.active])
        fused = len([c for c in self.cargos if c.fused])
        spilled = len([c for c in self.cargos if c.spilled])
        free = len([p for p in self.particles if not p.dead and p.state == "free"])
        degrading = len([p for p in self.particles if not p.dead and p.state == "degrading"])
        gone = len([p for p in self.particles if p.dead])
        total = len(self.particles)

        ai_text = "AI: unavailable"
        if self.ai:
            ai_text = (
                "AI: "
                + ("ON" if self.ai.enabled else "OFF")
                + (" / paused" if self.ai.paused else "")
                + " | mode: "
                + self.ai.mode
                + " | stagnant: "
                + format(self.ai.stagnation_time, ".1f")
                + "s"
            )

        manual = ""
        if self.time < self.manual_override_until:
            manual = " | HUMAN OVERRIDE " + format(self.manual_override_until - self.time, ".1f") + "s"

        self.status.text = (
            "Round "
            + str(self.round_number)
            + " | "
            + ai_text
            + manual
            + "\nactive vesicles: "
            + str(active)
            + " | fused: "
            + str(fused)
            + " | spilled: "
            + str(spilled)
            + " | free particles: "
            + str(free)
            + " | degrading: "
            + str(degrading)
            + " | disappeared: "
            + str(gone)
            + "/"
            + str(total)
            + "\nControls: SPACE pause, A AI, R reset, TAB select, WASD/arrows/QE move, O orbit attach/detach, X spill, F fuse, M mark, C change AI mode, P pause AI"
            + "\nLast reset: "
            + self.last_reset_reason
        )

    def update(self, dt):
        if self.paused:
            self.update_status()
            return

        self.time += dt

        if self.ai:
            self.ai.update(dt)

        for lys in self.lysosomes:
            lys.update(dt)

        for c in list(self.cargos):
            c.update(dt)

        for p in list(self.particles):
            p.update(dt)

        self.particles = [p for p in self.particles if not (p.dead and p.visual.visible is False)]

        alive_effects = []
        for e in self.effects:
            if e.update(dt):
                alive_effects.append(e)
        self.effects = alive_effects

        self.update_selection_marker()
        self.update_status()


sim = Simulation()
sim.ai = AIController(sim)


def keydown(evt):
    key = evt.key
    c = sim.selected_cargo()
    move_force = 4.8

    if key == " ":
        sim.paused = not sim.paused

    elif key in ["a", "A"]:
        sim.ai.enabled = not sim.ai.enabled

    elif key in ["p", "P"]:
        sim.ai.paused = not sim.ai.paused

    elif key in ["r", "R"]:
        sim.reset(reason="manual reset")
        if sim.ai:
            sim.ai.last_signature = None
            sim.ai.stagnation_time = 0
            sim.ai.completion_time = 0

    elif key == "tab":
        sim.select_next()

    elif key in ["c", "C"]:
        if sim.ai:
            sim.ai.choose_new_mode("play")

    elif key in ["m", "M"]:
        if c:
            c.mark()
            sim.manual_override()

    elif key in ["x", "X"]:
        if c:
            c.spill()
            sim.manual_override()

    elif key in ["f", "F"]:
        sim.force_fuse_selected()
        sim.manual_override()

    elif key in ["o", "O"]:
        if c:
            if c.ai_attached:
                c.detach_orbit()
            else:
                c.attach_orbit(sim.nearest_lysosome(c.pos))
            sim.manual_override()

    elif c:
        direction = vector(0, 0, 0)

        if key in ["left", "a"]:
            direction += vector(-1, 0, 0)
        if key in ["right", "d"]:
            direction += vector(1, 0, 0)
        if key in ["up", "w"]:
            direction += vector(0, 0, -1)
        if key in ["down", "s"]:
            direction += vector(0, 0, 1)
        if key in ["q", "Q"]:
            direction += vector(0, -1, 0)
        if key in ["e", "E"]:
            direction += vector(0, 1, 0)

        if mag(direction) > 0:
            c.detach_orbit()
            c.vel += norm(direction) * move_force * 0.12
            c.spin += randf(-1, 1)
            sim.manual_override()


scene.bind("keydown", keydown)

dt = 1.0 / 60.0
while True:
    rate(60)
    sim.update(dt)
