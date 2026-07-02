"""Typed data structures for simulation state and percepts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import numpy as np


@dataclass
class RobotPercepts:
    """Typed snapshot of one robot's sensor readings for a single tick."""
    ir_ring: list[float] = field(default_factory=list)
    compass: float = 0.0
    ultrasound: list[float] = field(default_factory=list)
    line_sensors: list[bool] = field(default_factory=list)
    camera_frame: Optional["np.ndarray"] = None
    timestamp: float = 0.0


@dataclass
class NoiseConfig:
    """Per-sensor noise parameters."""
    ir_noise_std: float = 0.05
    compass_noise_std_deg: float = 2.0
    ultrasound_noise_std: float = 0.03
    line_sensor_dropout_prob: float = 0.01
    motor_noise_std: float = 0.02


@dataclass
class DomainRandomization:
    """Re-samples physical parameters on each reset() when enabled."""
    enabled: bool = False
    friction_range: tuple = (0.3, 0.6)
    motor_speed_scale_range: tuple = (0.9, 1.1)
    noise_std_scale_range: tuple = (0.8, 1.3)
