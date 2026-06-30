"""Ball physics body."""
from __future__ import annotations
import pymunk

BALL_RADIUS = 0.043      # 43 mm — foam ball size 3
BALL_MASS = 0.065        # 65 g
BALL_ELASTICITY = 0.75
BALL_FRICTION = 0.4

CATEGORY_BALL = 0b100


class Ball:
    def __init__(self, space: pymunk.Space, x: float = 0.0, y: float = 0.0) -> None:
        moment = pymunk.moment_for_circle(BALL_MASS, 0, BALL_RADIUS)
        self.body = pymunk.Body(BALL_MASS, moment)
        self.body.position = (x, y)

        self.shape = pymunk.Circle(self.body, BALL_RADIUS)
        self.shape.elasticity = BALL_ELASTICITY
        self.shape.friction = BALL_FRICTION
        self.shape.filter = pymunk.ShapeFilter(categories=CATEGORY_BALL)

        space.add(self.body, self.shape)

    def reset(self, x: float = 0.0, y: float = 0.0) -> None:
        self.body.position = (x, y)
        self.body.velocity = (0.0, 0.0)
        self.body.angular_velocity = 0.0
