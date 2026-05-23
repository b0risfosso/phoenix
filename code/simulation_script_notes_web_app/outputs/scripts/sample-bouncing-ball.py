from vpython import *

scene = canvas(title="Sample VPython Script", background=color.white)
ball = sphere(pos=vector(-3, 0, 0), radius=0.4, color=color.blue, make_trail=True)
floor = box(pos=vector(0, -0.5, 0), size=vector(8, 0.1, 3), color=vector(0.9, 0.9, 0.9))

v = vector(0.04, 0, 0)

while True:
    rate(60)
    ball.pos += v
    if ball.pos.x > 3 or ball.pos.x < -3:
        v.x *= -1
