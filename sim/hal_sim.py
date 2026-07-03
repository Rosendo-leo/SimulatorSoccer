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
        self._kick_angle_deg: float = 0.0
        self._kicker_cooldown: float = 0.0
        self._dribbler_on: bool = False

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

    def read_ball_velocity(self) -> tuple[float, float]:
        if "ball_velocity" not in self._percepts:
            raise NotImplementedError("sensors.ball_velocity not configured")
        return tuple(self._percepts["ball_velocity"])

    def read_opponent_lidar(self) -> list[float]:
        if "opponent_lidar" not in self._percepts:
            raise NotImplementedError("sensors.opponent_lidar not configured")
        return list(self._percepts["opponent_lidar"])

    # ------------------------------------------------------------------
    # HAL actuator interface
    # ------------------------------------------------------------------

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        self._cmd_vx = float(vx)
        self._cmd_vy = float(vy)
        self._cmd_omega = float(omega)

    def kick(self, angle_deg: float = 0.0) -> None:
        if self._kicker_cooldown <= 0.0:
            self._kick_requested = True
            self._kick_angle_deg = float(angle_deg)

    def set_dribbler(self, on: bool) -> None:
        if not self._config.dribbler:
            raise NotImplementedError("dribbler not configured")
        self._dribbler_on = bool(on)

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

        # Dribbler: força de captura contínua enquanto ativo
        if self._dribbler_on and self._config.dribbler:
            self._apply_dribbler(dt)

        # Kicker cooldown
        if self._kicker_cooldown > 0.0:
            self._kicker_cooldown -= dt

        if self._kick_requested:
            self._try_kick()
            self._kick_requested = False
            if self._config.kicker:
                self._kicker_cooldown = self._config.kicker.cooldown

    def _apply_dribbler(self, dt: float) -> None:
        """Modelo 2D do backspin: mola puxando a bola para a boca do
        dribbler + amortecimento da velocidade relativa bola-robô."""
        d     = self._config.dribbler
        body  = self._robot.body
        angle = body.angle + (0.0 if d.position == "front" else math.pi)

        mouth_dist = self._config.body.radius + BALL_RADIUS_APPROX + 0.004
        mx = body.position.x + math.cos(angle) * mouth_dist
        my = body.position.y + math.sin(angle) * mouth_dist

        ball  = self._ball.body
        ex    = ball.position.x - mx
        ey    = ball.position.y - my
        if math.hypot(ex, ey) > d.capture_radius:
            return                                    # fora da zona de captura

        # Aceleração desejada da bola: mola (K, 1/s²) + amortecimento da
        # velocidade relativa (C, 1/s), com teto — segura sem lançar.
        K = 120.0 * d.strength
        C = 15.0 * d.strength
        MAX_ACC = 25.0 * d.strength      # m/s²
        rvx = ball.velocity.x - body.velocity.x
        rvy = ball.velocity.y - body.velocity.y
        ax  = -K * ex - C * rvx
        ay  = -K * ey - C * rvy
        acc = math.hypot(ax, ay)
        if acc > MAX_ACC:
            ax, ay = ax * MAX_ACC / acc, ay * MAX_ACC / acc
        m_ball = ball.mass
        ball.apply_impulse_at_world_point(
            (m_ball * ax * dt, m_ball * ay * dt), ball.position)

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
            # Direção do chute (B4): comandada por kick(angle_deg), limitada
            # ao setor aim_range do YAML (0 = sempre reto à frente)
            half_range = self._config.kicker.aim_range / 2.0
            angle_cmd  = max(-half_range,
                             min(half_range, self._kick_angle_deg))
            kick_dir   = self._robot.body.angle + math.radians(angle_cmd)
            nx, ny = math.cos(kick_dir), math.sin(kick_dir)
            # A bola precisa estar aproximadamente na boca do kicker
            ball_dir = math.atan2(dy, dx)
            diff = (ball_dir - kick_dir + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) > math.radians(60):
                return
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
