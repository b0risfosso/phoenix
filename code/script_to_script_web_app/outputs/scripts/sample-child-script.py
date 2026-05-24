from vpython import *

scene = canvas(title='Sample child script', background=color.white)
ball = sphere(pos=vector(-2,0,0), radius=0.35, color=color.green, make_trail=True)
marker = ring(pos=vector(0,0,0), axis=vector(0,1,0), radius=1.2, thickness=0.04, color=color.orange)
v = vector(0.04,0,0)
while True:
    rate(60)
    ball.pos += v
    marker.rotate(angle=0.01, axis=vector(0,1,0))
    if abs(ball.pos.x) > 2:
        v.x *= -1
