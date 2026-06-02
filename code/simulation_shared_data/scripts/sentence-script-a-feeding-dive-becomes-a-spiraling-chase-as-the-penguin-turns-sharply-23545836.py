from vpython import *
import math
import random

# Penguin Hunt Spiral
# A feeding dive becomes a spiraling chase as the penguin turns sharply through cold water,
# following scattered fish that flash and split apart.
#
# Controls:
#   Space : pause / resume
#   R     : reset the simulation
#   F     : spawn a new fish split burst
#   T     : toggle trail visibility
#   Up    : increase penguin chase speed
#   Down  : decrease penguin chase speed

scene = canvas(
    title="Penguin Hunt Spiral - Yellow-eyed Penguin Feeding Dive",
    width=1280,
    height=760,
    background=vector(0.78, 0.91, 0.97),
    center=vector(0, -2, 0),
)
scene.forward = vector(-0.55, -0.28, -0.78)
scene.range = 18
scene.userspin = True
scene.userzoom = True

# Palette: light cold-water styling
WATER = vector(0.52, 0.78, 0.92)
DEEP_WATER = vector(0.24, 0.56, 0.74)
SEAFLOOR = vector(0.72, 0.67, 0.55)
KELP = vector(0.26, 0.55, 0.32)
PENGUIN_DARK = vector(0.06, 0.09, 0.12)
PENGUIN_WHITE = vector(0.94, 0.96, 0.94)
YELLOW_EYE = vector(1.0, 0.78, 0.12)
ORANGE_BEAK = vector(1.0, 0.45, 0.12)
FISH = vector(0.68, 0.88, 1.0)
FISH_FLASH = vector(1.0, 0.98, 0.62)
PULSE = vector(0.35, 0.75, 1.0)
TRAIL = vector(0.20, 0.45, 0.72)
TEXT = vector(0.08, 0.20, 0.28)

objects = []
fish_school = []
bubbles = []
kelp_stalks = []
trail_marks = []
current_arrows = []

paused = False
show_trails = True
chase_speed = 1.0
sim_time = 0.0
spiral_phase = 0.0
split_timer = 0.0
capture_count = 0


def add_obj(obj):
    objects.append(obj)
    return obj


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp_vec(a, b, f):
    return a * (1 - f) + b * f


def clear_scene_objects():
    global objects, fish_school, bubbles, kelp_stalks, trail_marks, current_arrows
    for obj in objects:
        try:
            obj.visible = False
        except Exception:
            pass
    objects = []
    fish_school = []
    bubbles = []
    kelp_stalks = []
    trail_marks = []
    current_arrows = []


# ---------- Environment ----------

def make_environment():
    add_obj(box(pos=vector(0, -8.5, 0), size=vector(42, 0.35, 32), color=SEAFLOOR, opacity=0.95))
    add_obj(box(pos=vector(0, 3.0, 0), size=vector(42, 18, 32), color=WATER, opacity=0.18))

    # Soft depth bands
    for i in range(6):
        y = 1.5 - i * 2.2
        add_obj(box(pos=vector(0, y, -0.2), size=vector(40, 0.04, 30), color=lerp_vec(WATER, DEEP_WATER, i / 6), opacity=0.09))

    # Otago-like rocky bottom and kelp hints
    for _ in range(34):
        x = random.uniform(-19, 19)
        z = random.uniform(-14, 14)
        r = random.uniform(0.25, 0.75)
        add_obj(sphere(pos=vector(x, -8.1 + random.uniform(-0.05, 0.15), z), radius=r,
                       color=vector(0.48 + random.random()*0.12, 0.45 + random.random()*0.09, 0.38), opacity=0.9))

    for _ in range(22):
        base = vector(random.uniform(-18, 18), -8.2, random.uniform(-13, 13))
        height = random.uniform(2.0, 5.3)
        stalk = add_obj(cylinder(pos=base, axis=vector(0.25 * random.uniform(-1, 1), height, 0.25 * random.uniform(-1, 1)),
                               radius=0.035, color=KELP, opacity=0.72))
        kelp_stalks.append(stalk)
        for j in range(3):
            leaf_y = base.y + height * (0.35 + j * 0.18)
            leaf = add_obj(ellipsoid(pos=vector(base.x + random.uniform(-0.4, 0.4), leaf_y, base.z + random.uniform(-0.4, 0.4)),
                                     length=random.uniform(0.8, 1.4), height=0.08, width=0.22,
                                     color=KELP, opacity=0.55))
            leaf.rotate(angle=random.uniform(0, math.pi), axis=vector(0, 1, 0))

    # Current arrows
    for i in range(9):
        y = random.uniform(-5.5, 1.8)
        z = random.uniform(-11, 11)
        x = -18 + i * 4.5
        arr = add_obj(arrow(pos=vector(x, y, z), axis=vector(1.0, 0, 0.18 * math.sin(i)),
                            shaftwidth=0.05, color=vector(0.35, 0.65, 0.82), opacity=0.36))
        current_arrows.append(arr)

    # Labels
    add_obj(label(pos=vector(-17.8, 5.7, 0), text="Penguin Hunt Spiral", height=24,
                  color=TEXT, box=False, opacity=0))
    add_obj(label(pos=vector(-17.8, 4.8, 0), text="spiral chase  |  flashing fish split apart  |  rootless cold-water dive path",
                  height=12, color=TEXT, box=False, opacity=0))


# ---------- Penguin model ----------
class Penguin:
    def __init__(self):
        self.pos = vector(-9, -1.2, 0)
        self.prev_pos = vector(self.pos.x, self.pos.y, self.pos.z)
        self.velocity = vector(0, 0, 0)
        self.heading = vector(1, -0.15, 0)
        self.roll = 0.0
        self.flap_phase = 0.0
        self.group = []
        self.make_body()

    def make_body(self):
        # Body aligned primarily along x-axis; rotations are applied by axis changes.
        self.body = add_obj(ellipsoid(pos=self.pos, length=2.0, height=0.78, width=0.62, color=PENGUIN_DARK))
        self.belly = add_obj(ellipsoid(pos=self.pos + vector(0.08, -0.06, 0), length=1.45, height=0.58, width=0.50, color=PENGUIN_WHITE))
        self.head = add_obj(sphere(pos=self.pos + vector(0.95, 0.20, 0), radius=0.38, color=PENGUIN_DARK))
        self.throat = add_obj(sphere(pos=self.pos + vector(0.88, 0.05, 0), radius=0.24, color=PENGUIN_WHITE))
        self.beak = add_obj(cone(pos=self.pos + vector(1.32, 0.18, 0), axis=vector(0.55, -0.04, 0), radius=0.11, color=ORANGE_BEAK))
        self.eye_l = add_obj(sphere(pos=self.pos + vector(1.08, 0.35, 0.18), radius=0.055, color=YELLOW_EYE, emissive=True))
        self.eye_r = add_obj(sphere(pos=self.pos + vector(1.08, 0.35, -0.18), radius=0.055, color=YELLOW_EYE, emissive=True))
        self.yellow_band_l = add_obj(curve(pos=[self.pos + vector(0.78, 0.40, 0.22), self.pos + vector(1.20, 0.38, 0.18)],
                                          radius=0.025, color=YELLOW_EYE, emissive=True))
        self.yellow_band_r = add_obj(curve(pos=[self.pos + vector(0.78, 0.40, -0.22), self.pos + vector(1.20, 0.38, -0.18)],
                                          radius=0.025, color=YELLOW_EYE, emissive=True))
        self.left_flipper = add_obj(cone(pos=self.pos + vector(0.0, 0.0, 0.40), axis=vector(-0.45, -0.08, 0.85), radius=0.18, color=PENGUIN_DARK))
        self.right_flipper = add_obj(cone(pos=self.pos + vector(0.0, 0.0, -0.40), axis=vector(-0.45, -0.08, -0.85), radius=0.18, color=PENGUIN_DARK))
        self.wake = add_obj(curve(pos=[self.pos - vector(0.5, 0, 0), self.pos - vector(0.55, 0, 0)], radius=0.035, color=PULSE, opacity=0.5))
        self.group = [self.body, self.belly, self.head, self.throat, self.beak, self.eye_l, self.eye_r,
                      self.left_flipper, self.right_flipper]

    def target_spiral_position(self, t):
        # The hunt path spirals inward and downward, then loops back through the fish field.
        radius = 7.5 - 3.1 * (0.5 + 0.5 * math.sin(t * 0.17))
        angle = t * 0.92
        x = radius * math.cos(angle)
        z = radius * math.sin(angle)
        y = -1.8 - 2.4 * math.sin(t * 0.31 + 0.7)
        return vector(x, y, z)

    def nearest_fish_pull(self):
        if not fish_school:
            return vector(0, 0, 0)
        nearest = min(fish_school, key=lambda f: mag(f.pos - self.pos))
        d = nearest.pos - self.pos
        if mag(d) < 0.01:
            return vector(0, 0, 0)
        return norm(d) * clamp(6.0 / (mag(d) + 0.5), 0, 1.6)

    def update(self, dt, t):
        global capture_count
        self.prev_pos = vector(self.pos.x, self.pos.y, self.pos.z)
        spiral_target = self.target_spiral_position(t)
        fish_pull = self.nearest_fish_pull()
        desired = (spiral_target - self.pos) * 0.17 + fish_pull * 0.62
        if mag(desired) > 0:
            desired = norm(desired) * (3.0 * chase_speed)
        # Smooth turning to suggest sharp but controlled underwater maneuvering.
        self.velocity = lerp_vec(self.velocity, desired, 0.055)
        self.pos += self.velocity * dt
        self.pos.y = clamp(self.pos.y, -7.0, 2.2)
        if mag(self.velocity) > 0.02:
            self.heading = norm(self.velocity)

        self.flap_phase += dt * (8.0 + 2.0 * mag(self.velocity))
        flap = math.sin(self.flap_phase) * 0.35
        bob = math.sin(t * 5.0) * 0.025

        # Visual position updates. VPython ellipsoid has fixed axis behavior across versions,
        # so the model translates and uses flippers/wake to emphasize direction and chase.
        for obj in self.group:
            obj.pos += self.pos - self.prev_pos
        self.yellow_band_l.modify(0, pos=self.pos + vector(0.78, 0.40 + bob, 0.22))
        self.yellow_band_l.modify(1, pos=self.pos + vector(1.20, 0.38 + bob, 0.18))
        self.yellow_band_r.modify(0, pos=self.pos + vector(0.78, 0.40 + bob, -0.22))
        self.yellow_band_r.modify(1, pos=self.pos + vector(1.20, 0.38 + bob, -0.18))

        self.body.pos = self.pos + vector(0, bob, 0)
        self.belly.pos = self.pos + vector(0.08, -0.06 + bob, 0)
        self.head.pos = self.pos + vector(0.95, 0.20 + bob, 0)
        self.throat.pos = self.pos + vector(0.88, 0.05 + bob, 0)
        self.beak.pos = self.pos + vector(1.32, 0.18 + bob, 0)
        self.eye_l.pos = self.pos + vector(1.08, 0.35 + bob, 0.18)
        self.eye_r.pos = self.pos + vector(1.08, 0.35 + bob, -0.18)
        self.left_flipper.pos = self.pos + vector(0.0, 0.0, 0.40)
        self.right_flipper.pos = self.pos + vector(0.0, 0.0, -0.40)
        self.left_flipper.axis = vector(-0.45, -0.10 + flap, 0.85)
        self.right_flipper.axis = vector(-0.45, -0.10 - flap, -0.85)
        self.beak.axis = vector(0.52, -0.04 + 0.025 * math.sin(t * 4.0), 0)

        # Wake line behind penguin
        behind = self.pos - self.heading * 0.8
        farther = self.pos - self.heading * 3.0 + vector(0, 0.15 * math.sin(t * 3.2), 0)
        self.wake.modify(0, pos=behind)
        self.wake.modify(1, pos=farther)
        self.wake.opacity = 0.20 + 0.25 * clamp(mag(self.velocity) / 4.0, 0, 1)

        # Captures: fish vanish into a little bubble flash if the penguin reaches them.
        for f in list(fish_school):
            if mag(f.pos - self.pos) < 0.42:
                capture_count += 1
                f.hide()
                fish_school.remove(f)
                make_bubble_burst(f.pos, count=8, flash=True)

        if show_trails and random.random() < 0.22:
            mark = add_obj(sphere(pos=self.pos - self.heading * 0.75, radius=0.055, color=TRAIL, opacity=0.28))
            trail_marks.append({"obj": mark, "age": 0.0, "life": 4.0})


# ---------- Fish ----------
class Fish:
    def __init__(self, pos, velocity=None, split_level=0):
        self.pos = vector(pos.x, pos.y, pos.z)
        self.velocity = velocity if velocity is not None else vector(random.uniform(-0.8, 0.8), random.uniform(-0.2, 0.2), random.uniform(-0.8, 0.8))
        self.split_level = split_level
        self.phase = random.uniform(0, math.tau)
        self.flash_phase = random.uniform(0, math.tau)
        self.body = add_obj(ellipsoid(pos=self.pos, length=0.48, height=0.16, width=0.12, color=FISH, emissive=False))
        self.tail = add_obj(cone(pos=self.pos - vector(0.24, 0, 0), axis=vector(-0.22, 0, 0), radius=0.09, color=FISH, opacity=0.8))
        self.flash = add_obj(sphere(pos=self.pos + vector(0.03, 0.03, 0), radius=0.075, color=FISH_FLASH, opacity=0.15, emissive=True))
        self.alive = True

    def hide(self):
        self.alive = False
        self.body.visible = False
        self.tail.visible = False
        self.flash.visible = False

    def update(self, dt, t, penguin_pos):
        if not self.alive:
            return
        self.phase += dt * 8.0
        self.flash_phase += dt * (5.0 + 0.8 * self.split_level)
        away = self.pos - penguin_pos
        d = mag(away)
        if d < 4.4 and d > 0.01:
            self.velocity += norm(away) * dt * (4.5 / (d + 0.35))
            self.velocity += vector(random.uniform(-1, 1), random.uniform(-0.3, 0.3), random.uniform(-1, 1)) * dt * 0.55
        # schooling swirl and current
        swirl = vector(-self.pos.z, 0.05 * math.sin(t + self.phase), self.pos.x)
        if mag(swirl) > 0:
            self.velocity += norm(swirl) * dt * 0.18
        self.velocity += vector(0.10, 0.02 * math.sin(t * 0.7 + self.phase), 0.03 * math.cos(t * 0.5)) * dt
        speed_limit = 2.4 + self.split_level * 0.45
        if mag(self.velocity) > speed_limit:
            self.velocity = norm(self.velocity) * speed_limit
        self.pos += self.velocity * dt

        # Keep fish within cold-water scene.
        if abs(self.pos.x) > 17:
            self.velocity.x *= -0.8
            self.pos.x = clamp(self.pos.x, -17, 17)
        if abs(self.pos.z) > 12:
            self.velocity.z *= -0.8
            self.pos.z = clamp(self.pos.z, -12, 12)
        if self.pos.y > 2 or self.pos.y < -7.2:
            self.velocity.y *= -0.8
            self.pos.y = clamp(self.pos.y, -7.2, 2)

        wiggle = vector(0, 0.025 * math.sin(self.phase), 0)
        self.body.pos = self.pos + wiggle
        self.tail.pos = self.pos - vector(0.24, 0, 0) + wiggle
        self.flash.pos = self.pos + vector(0.06, 0.04, 0)
        flash_strength = 0.10 + 0.40 * max(0, math.sin(self.flash_phase))
        if d < 4.4:
            flash_strength += 0.30
        self.flash.opacity = clamp(flash_strength, 0.08, 0.85)
        self.body.color = lerp_vec(FISH, FISH_FLASH, clamp(flash_strength * 0.7, 0, 1))
        self.tail.axis = vector(-0.22, 0.03 * math.sin(self.phase * 1.7), 0.06 * math.sin(self.phase))


def spawn_fish_school(center=None, count=24, spread=3.0, split_level=0):
    if center is None:
        center = vector(random.uniform(-5, 7), random.uniform(-4.5, -1.0), random.uniform(-5, 5))
    for _ in range(count):
        offset = vector(random.uniform(-spread, spread), random.uniform(-spread * 0.32, spread * 0.32), random.uniform(-spread, spread))
        vel = vector(random.uniform(-0.9, 0.9), random.uniform(-0.15, 0.15), random.uniform(-0.9, 0.9))
        fish_school.append(Fish(center + offset, vel, split_level=split_level))


def split_fish_burst(center=None):
    if not fish_school:
        spawn_fish_school(count=18)
        return
    if center is None:
        center = random.choice(fish_school).pos
    # Existing fish near center scatter.
    for f in fish_school:
        d = f.pos - center
        if mag(d) < 4.5 and mag(d) > 0.01:
            f.velocity += norm(d) * random.uniform(1.0, 2.6)
            f.split_level = min(f.split_level + 1, 4)
    # New small flashes split outward.
    for i in range(12):
        angle = math.tau * i / 12.0 + random.uniform(-0.25, 0.25)
        vel = vector(math.cos(angle), random.uniform(-0.18, 0.18), math.sin(angle)) * random.uniform(1.0, 2.2)
        fish_school.append(Fish(center + vel * 0.28, vel, split_level=2))
    make_bubble_burst(center, count=14, flash=True)


# ---------- Bubbles, trails, and visual effects ----------
def make_bubble_burst(origin, count=10, flash=False):
    for _ in range(count):
        r = random.uniform(0.035, 0.11)
        color = FISH_FLASH if flash and random.random() < 0.45 else vector(0.85, 0.96, 1.0)
        obj = add_obj(sphere(pos=origin + vector(random.uniform(-0.25, 0.25), random.uniform(-0.1, 0.25), random.uniform(-0.25, 0.25)),
                             radius=r, color=color, opacity=random.uniform(0.22, 0.55), emissive=flash))
        bubbles.append({
            "obj": obj,
            "vel": vector(random.uniform(-0.12, 0.12), random.uniform(0.18, 0.52), random.uniform(-0.12, 0.12)),
            "age": 0.0,
            "life": random.uniform(2.0, 4.5),
        })


def update_bubbles(dt):
    for b in list(bubbles):
        obj = b["obj"]
        b["age"] += dt
        obj.pos += b["vel"] * dt
        obj.radius *= 1.0 + 0.10 * dt
        obj.opacity = max(0, obj.opacity * (1 - 0.45 * dt))
        if b["age"] > b["life"] or obj.pos.y > 3.0:
            obj.visible = False
            bubbles.remove(b)


def update_trails(dt):
    for mark in list(trail_marks):
        mark["age"] += dt
        obj = mark["obj"]
        obj.opacity = max(0, 0.28 * (1 - mark["age"] / mark["life"]))
        obj.radius *= 1.0 + 0.04 * dt
        if mark["age"] > mark["life"]:
            obj.visible = False
            trail_marks.remove(mark)


def update_currents(t):
    for i, arr in enumerate(current_arrows):
        arr.axis = vector(0.9 + 0.25 * math.sin(t * 0.7 + i), 0.02 * math.sin(t + i), 0.18 * math.sin(t * 0.4 + i))
        arr.opacity = 0.22 + 0.14 * (0.5 + 0.5 * math.sin(t * 0.8 + i))


def update_kelp(t):
    for i, stalk in enumerate(kelp_stalks):
        h = mag(stalk.axis)
        stalk.axis.x = 0.22 * math.sin(t * 0.7 + i * 0.4)
        stalk.axis.z = 0.18 * math.cos(t * 0.52 + i * 0.3)
        stalk.axis.y = h


# ---------- HUD ----------
hud = None


def update_hud():
    global hud
    if hud is None:
        hud = add_obj(label(pos=vector(10.2, 5.6, 0), height=13, color=TEXT, box=True,
                            background=vector(0.88, 0.96, 1.0), opacity=0.45))
    hud.text = (
        "Space pause | R reset | F split fish | T trails\n"
        f"fish: {len(fish_school)}   captures: {capture_count}   chase speed: {chase_speed:.1f}x"
    )


# ---------- Controls ----------
def on_keydown(evt):
    global paused, show_trails, chase_speed
    key = evt.key.lower()
    if key == " ":
        paused = not paused
    elif key == "r":
        reset_simulation()
    elif key == "f":
        split_fish_burst(penguin.pos + vector(random.uniform(-2, 3), random.uniform(-1, 1), random.uniform(-2, 2)))
    elif key == "t":
        show_trails = not show_trails
        if not show_trails:
            for mark in trail_marks:
                mark["obj"].visible = False
            trail_marks.clear()
    elif key == "up":
        chase_speed = clamp(chase_speed + 0.1, 0.4, 2.4)
    elif key == "down":
        chase_speed = clamp(chase_speed - 0.1, 0.4, 2.4)


scene.bind("keydown", on_keydown)


# ---------- Reset and main loop ----------
penguin = None


def reset_simulation():
    global penguin, paused, sim_time, split_timer, capture_count, chase_speed, show_trails
    clear_scene_objects()
    paused = False
    sim_time = 0.0
    split_timer = 1.5
    capture_count = 0
    chase_speed = 1.0
    show_trails = True
    make_environment()
    penguin = Penguin()
    spawn_fish_school(center=vector(4.5, -2.5, 2.2), count=26, spread=2.4)
    spawn_fish_school(center=vector(-1.0, -4.0, -3.5), count=18, spread=1.8)
    make_bubble_burst(vector(-8.5, -1.3, 0), count=18)
    update_hud()


reset_simulation()

while True:
    rate(60)
    dt = 1.0 / 60.0
    if paused:
        update_hud()
        continue

    sim_time += dt
    split_timer -= dt

    penguin.update(dt, sim_time)

    for f in list(fish_school):
        f.update(dt, sim_time, penguin.pos)

    # Fish split periodically when the penguin presses into the school.
    if split_timer <= 0:
        if fish_school:
            nearest = min(fish_school, key=lambda ff: mag(ff.pos - penguin.pos))
            split_fish_burst(nearest.pos)
        split_timer = random.uniform(4.0, 6.8)

    # Replenish scattered fish so the chase keeps evolving.
    if len(fish_school) < 24:
        spawn_fish_school(center=vector(random.uniform(-5, 7), random.uniform(-5.5, -1.5), random.uniform(-5, 5)), count=12, spread=1.6)

    if random.random() < 0.04:
        make_bubble_burst(penguin.pos - penguin.heading * 0.9, count=1)

    update_bubbles(dt)
    update_trails(dt)
    update_currents(sim_time)
    update_kelp(sim_time)
    update_hud()
