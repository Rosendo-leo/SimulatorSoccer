from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import yaml


@dataclass
class BodyConfig:
    shape: str = "circle"
    radius: float = 0.11
    width: float = 0.22
    height: float = 0.22
    mass: float = 1.0
    max_speed: float = 1.5


@dataclass
class WheelsConfig:
    type: str = "omnidirectional"
    count: int = 4
    positions: List[float] = field(default_factory=lambda: [45, 135, 225, 315])


@dataclass
class IRRingConfig:
    count: int = 16
    range: float = 1.5
    noise_std: float = 0.05


@dataclass
class CompassConfig:
    noise_std: float = 2.0


@dataclass
class UltrasoundConfig:
    count: int = 4
    directions: List[float] = field(default_factory=lambda: [0, 90, 180, 270])
    range: float = 2.0
    noise_std: float = 0.03


@dataclass
class LineSensorsConfig:
    count: int = 4
    positions: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class SensorsConfig:
    ir_ring: Optional[IRRingConfig] = None
    compass: Optional[CompassConfig] = None
    ultrasound: Optional[UltrasoundConfig] = None
    line_sensors: Optional[LineSensorsConfig] = None


@dataclass
class KickerConfig:
    force: float = 5.0
    cooldown: float = 2.0


@dataclass
class RobotConfig:
    name: str = "Robot"
    body: BodyConfig = field(default_factory=BodyConfig)
    wheels: WheelsConfig = field(default_factory=WheelsConfig)
    sensors: SensorsConfig = field(default_factory=SensorsConfig)
    kicker: Optional[KickerConfig] = None


def load_robot_config(path: str) -> RobotConfig:
    with open(path) as f:
        data = yaml.safe_load(f)

    r = data["robot"]

    bd = r.get("body", {})
    body = BodyConfig(
        shape=bd.get("shape", "circle"),
        radius=bd.get("radius", 0.11),
        width=bd.get("width", 0.22),
        height=bd.get("height", 0.22),
        mass=bd.get("mass", 1.0),
        max_speed=bd.get("max_speed", 1.5),
    )

    wd = r.get("wheels", {})
    wheels = WheelsConfig(
        type=wd.get("type", "omnidirectional"),
        count=wd.get("count", 4),
        positions=wd.get("positions", [45, 135, 225, 315]),
    )

    sd = r.get("sensors", {})
    sensors = SensorsConfig()

    if "ir_ring" in sd:
        d = sd["ir_ring"]
        sensors.ir_ring = IRRingConfig(
            count=d.get("count", 16),
            range=d.get("range", 1.5),
            noise_std=d.get("noise_std", 0.05),
        )

    if "compass" in sd:
        d = sd["compass"]
        sensors.compass = CompassConfig(noise_std=d.get("noise_std", 2.0))

    if "ultrasound" in sd:
        d = sd["ultrasound"]
        sensors.ultrasound = UltrasoundConfig(
            count=d.get("count", 4),
            directions=d.get("directions", [0, 90, 180, 270]),
            range=d.get("range", 2.0),
            noise_std=d.get("noise_std", 0.03),
        )

    if "line_sensors" in sd:
        d = sd["line_sensors"]
        sensors.line_sensors = LineSensorsConfig(
            count=d.get("count", 4),
            positions=[tuple(p) for p in d.get("positions", [])],
        )

    kicker = None
    if "kicker" in r:
        d = r["kicker"]
        kicker = KickerConfig(
            force=d.get("force", 5.0),
            cooldown=d.get("cooldown", 2.0),
        )

    return RobotConfig(
        name=r.get("name", "Robot"),
        body=body,
        wheels=wheels,
        sensors=sensors,
        kicker=kicker,
    )
