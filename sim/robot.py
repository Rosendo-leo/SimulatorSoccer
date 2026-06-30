"""Robot physics body generated from RobotConfig."""
from __future__ import annotations
import math
import pymunk
from sim.config_loader import RobotConfig

CATEGORY_ROBOT = 0b010
ROBOT_ELASTICITY = 0.2
ROBOT_FRICTION = 0.6

# Robots don't collide with each other in the same group, but do collide with walls/ball.
# Each robot gets its own pymunk group id to avoid self-collision with its own shapes.
_next_group = 1


class Robot:
    def __init__(
        self,
        space: pymunk.Space,
        config: RobotConfig,
        team: str,
        x: float = 0.0,
        y: float = 0.0,
        heading: float = 0.0,
    ) -> None:
        global _next_group
        self.config = config
        self.team = team

        mass = config.body.mass
        radius = config.body.radius
        moment = pymunk.moment_for_circle(mass, 0, radius)

        self.body = pymunk.Body(mass, moment)
        self.body.position = (x, y)
        self.body.angle = heading

        self.shape = pymunk.Circle(self.body, radius)
        self.shape.elasticity = ROBOT_ELASTICITY
        self.shape.friction = ROBOT_FRICTION
        self.shape.filter = pymunk.ShapeFilter(
            group=_next_group,
            categories=CATEGORY_ROBOT,
        )
        _next_group += 1

        space.add(self.body, self.shape)

    def reset(self, x: float, y: float, heading: float = 0.0) -> None:
        self.body.position = (x, y)
        self.body.angle = heading
        self.body.velocity = (0.0, 0.0)
        self.body.angular_velocity = 0.0
