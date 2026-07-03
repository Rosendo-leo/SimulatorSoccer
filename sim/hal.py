"""Hardware Abstraction Layer — abstract interface.

The same decision code calls these methods whether it runs in the simulator
or on the physical robot. The backend is swapped transparently.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List


class HAL(ABC):
    """Unified sensor/actuator interface for one robot."""

    # ------------------------------------------------------------------
    # Sensors
    # ------------------------------------------------------------------

    @abstractmethod
    def read_ir(self) -> List[float]:
        """Return IR ring intensities [0..1] per sector (sector 0 = forward)."""

    @abstractmethod
    def read_compass(self) -> float:
        """Return absolute heading in radians (0 = +X, CCW positive)."""

    @abstractmethod
    def read_ultrasound(self) -> List[float]:
        """Return distances in metres for each ultrasound emitter."""

    @abstractmethod
    def read_line_sensors(self) -> List[bool]:
        """Return True for each sensor currently over a white line."""

    @abstractmethod
    def read_position(self) -> tuple[float, float]:
        """Return estimated world position (x, y) in metres.

        In the simulator this reads directly from the physics engine.
        In hardware, implement via encoder odometry or dead-reckoning.
        """

    # ------------------------------------------------------------------
    # Optional sensors — not abstract: only robots whose YAML declares
    # them get real readings; backends without them raise.
    # ------------------------------------------------------------------

    def read_ball_velocity(self) -> tuple[float, float]:
        """Return absolute ball velocity (vx, vy) in m/s, world frame.

        Requires `sensors.ball_velocity` in the robot YAML (models an
        optical motion sensor / camera-based estimate). Essential for
        intercepting a moving ball instead of chasing its position.
        """
        raise NotImplementedError("sensors.ball_velocity not configured")

    def read_opponent_lidar(self) -> List[float]:
        """Return distance (m) to the nearest ROBOT along each configured
        direction; sensor range when nothing is hit.

        Requires `sensors.opponent_lidar` in the robot YAML. Detects any
        robot (teammates included) and ignores walls and the ball —
        like a real ToF array would.
        """
        raise NotImplementedError("sensors.opponent_lidar not configured")

    # ------------------------------------------------------------------
    # Actuators
    # ------------------------------------------------------------------

    @abstractmethod
    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        """Set desired velocity in robot-local frame.

        vx    — forward speed (m/s), positive = forward
        vy    — lateral speed (m/s), positive = left (for omni robots)
        omega — angular velocity (rad/s), positive = CCW
        For differential robots use vx as forward, vy=0, omega for turning.
        """

    @abstractmethod
    def kick(self, angle_deg: float = 0.0) -> None:
        """Trigger the kicker (subject to cooldown).

        angle_deg — kick direction relative to the robot heading, in degrees
        (0 = straight ahead, + = left/CCW). Clamped to the sector allowed by
        `kicker.aim_range` in the YAML; with the default aim_range of 0 the
        kick is always straight ahead.
        """

    def set_dribbler(self, on: bool) -> None:
        """Turn the dribbler on/off.

        Requires a `dribbler` block in the robot YAML. While active, the
        ball is held against the dribbler mouth (backspin grip) and the
        robot is exempt from the holding rule (2.5.2).
        """
        raise NotImplementedError("dribbler not configured")

    # ------------------------------------------------------------------
    # Optional convenience: stop all motors
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self.set_velocity(0.0, 0.0, 0.0)
