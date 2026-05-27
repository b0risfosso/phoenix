from vpython import *

scene = canvas(title='Sample main simulation', background=color.white)
ball = sphere(pos=vector(-2,0,0), radius=0.35, color=color.blue, make_trail=True)
v = vector(0.04,0,0)
while True:
    rate(60)
    ball.pos += v
    if abs(ball.pos.x) > 2:
        v.x *= -1
