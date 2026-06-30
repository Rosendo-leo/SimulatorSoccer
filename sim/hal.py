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
    def kick(self) -> None:
        """Trigger the kicker (subject to cooldown)."""

    # ------------------------------------------------------------------
    # Optional convenience: stop all motors
    # ------------------------------------------------------------------

    def stop(self) -> None:
        self.set_velocity(0.0, 0.0, 0.0)
