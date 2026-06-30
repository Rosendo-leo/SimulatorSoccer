"""Simulator backend for the HAL interface."""
from __future__ import annotations
import math
import numpy as np
import pymunk

from sim.hal import HAL
from sim.config_loader import RobotConfig
from sim.percepts import compute_all_percepts


class SimHAL(HAL):
    def __init__(
        self,
        robot,          # sim.robot.Robot
        ball,           # sim.ball.Ball
        space: pymunk.Space,
        config: RobotConfig,
        rng: np.random.Generator | None = None,
    ) -> None:
        self._robot = robot
        self._ball = ball
        self._space = space
        self._config = config
        self._rng = rng or np.random.default_rng()

        # Command registers (written by strategy, applied each tick)
        self._cmd_vx: float = 0.0
        self._cmd_vy: float = 0.0
        self._cmd_omega: float = 0.0
        self._kick_requested: bool = False
        self._kicker_cooldown: float = 0.0

        # Cache percepts computed at start of each tick
        self._percepts: dict = {}

    # ------------------------------------------------------------------
    # Refresh percepts (called by engine before strategy runs)
    # ------------------------------------------------------------------

    def _refresh_percepts(self) -> None:
        self._percepts = compute_all_percepts(
            self._robot.body,
            self._config,
            self._ball.body,
            self._space,
            self._rng,
        )

    # ------------------------------------------------------------------
    # HAL sensor interface
    # ------------------------------------------------------------------

    def read_ir(self) -> list[float]:
        return list(self._percepts.get("ir_ring", []))

    def read_compass(self) -> float:
        return float(self._percepts.get("compass", self._robot.body.angle))

    def read_ultrasound(self) -> list[float]:
        return list(self._percepts.get("ultrasound", []))

    def read_line_sensors(self) -> list[bool]:
        return list(self._percepts.get("line_sensors", []))

    def read_position(self) -> tuple[float, float]:
        pos = self._robot.body.position
        return (float(pos.x), float(pos.y))

    # ------------------------------------------------------------------
    # HAL actuator interface
    # ------------------------------------------------------------------

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        self._cmd_vx = float(vx)
        self._cmd_vy = float(vy)
        self._cmd_omega = float(omega)

    def kick(self) -> None:
        if self._kicker_cooldown <= 0.0:
            self._kick_requested = True

    # ------------------------------------------------------------------
    # Engine calls these
    # ------------------------------------------------------------------

    def _apply_action(self, dt: float) -> None:
        """Convert local-frame command to world-frame velocity and apply."""
        angle = self._robot.body.angle
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Rotate from robot-local to world frame
        world_vx = cos_a * self._cmd_vx - sin_a * self._cmd_vy
        world_vy = sin_a * self._cmd_vx + cos_a * self._cmd_vy

        # Clamp to max speed
        speed = math.sqrt(world_vx ** 2 + world_vy ** 2)
        max_speed = self._config.body.max_speed
        if speed > max_speed and speed > 0:
            scale = max_speed / speed
            world_vx *= scale
            world_vy *= scale

        self._robot.body.velocity = (world_vx, world_vy)
        self._robot.body.angular_velocity = self._cmd_omega

        # Kicker cooldown
        if self._kicker_cooldown > 0.0:
            self._kicker_cooldown -= dt

        if self._kick_requested:
            self._try_kick()
            self._kick_requested = False
            if self._config.kicker:
                self._kicker_cooldown = self._config.kicker.cooldown

    def _try_kick(self) -> None:
        if not self._config.kicker:
            return
        robot_pos = self._robot.body.position
        ball_pos  = self._ball.body.position
        dx = ball_pos.x - robot_pos.x
        dy = ball_pos.y - robot_pos.y
        dist = math.sqrt(dx ** 2 + dy ** 2)

        kick_reach = self._config.body.radius + BALL_RADIUS_APPROX + 0.02
        if dist < kick_reach and dist > 1e-4:
            nx, ny = dx / dist, dy / dist
            self._ball.body.apply_impulse_at_world_point(
                (self._config.kicker.force * nx,
                 self._config.kicker.force * ny),
                ball_pos,
            )
            # Clamp ball speed so it never tunnels through walls.
            # At MAX_BALL_SPEED m/s with PHYSICS_SUBSTEPS substeps the ball
            # travels MAX_BALL_SPEED/(60*SUBSTEPS) m per sub-step, well below
            # the wall+ball collision distance (~5 cm).
            vx, vy = self._ball.body.velocity
            speed  = math.sqrt(vx ** 2 + vy ** 2)
            if speed > MAX_BALL_SPEED:
                scale = MAX_BALL_SPEED / speed
                self._ball.body.velocity = (vx * scale, vy * scale)


# Approximate ball radius — avoid circular import by hardcoding here
BALL_RADIUS_APPROX = 0.043

# Maximum speed the ball can reach after a kick (m/s).
# Keeps per-substep displacement below wall+ball collision distance.
MAX_BALL_SPEED = 4.0
