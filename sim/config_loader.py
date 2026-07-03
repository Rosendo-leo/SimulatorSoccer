from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import yaml

# RCJ Soccer 2026 — limites por sub-liga.
# Soccer Infrared: cilindro de 22 cm, até 1500 g, bola IR.
# Soccer Vision:   cilindro de 18 cm, sem limite de peso, bola passiva (câmera).
# Nota: enquanto a câmera simulada não existe (backlog B1), o ir_ring funciona
# como detector abstrato de bola também na liga Vision.
LEAGUE_LIMITS = {
    "infrared": {"max_diameter": 0.22, "max_mass": 1.5},
    "vision":   {"max_diameter": 0.18, "max_mass": None},   # sem limite de peso
}
DEFAULT_LEAGUE = "infrared"

# Aliases legados (limites da liga Infrared) — mantidos por compatibilidade
MAX_ROBOT_DIAMETER = LEAGUE_LIMITS["infrared"]["max_diameter"]
MAX_ROBOT_RADIUS   = MAX_ROBOT_DIAMETER / 2
MAX_ROBOT_MASS     = LEAGUE_LIMITS["infrared"]["max_mass"]


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
class VisualConfig:
    """Malha 3D do viewer (só cosmética — a física continua no shape do body).

    `mesh` é o nome de um arquivo .glb em robots/meshes/ (exportar o CAD em
    METROS; use `scale` só para ajustes finos). `offset` em metros nos eixos
    do Three.js (x = comprimento do campo, y = altura, z = -y do sim);
    `rotation` em graus (x, y, z) para corrigir a orientação do CAD.
    """
    mesh: str = ""
    scale: float = 1.0
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class RobotConfig:
    name: str = "Robot"
    league: str = DEFAULT_LEAGUE          # "infrared" | "vision"
    body: BodyConfig = field(default_factory=BodyConfig)
    wheels: WheelsConfig = field(default_factory=WheelsConfig)
    sensors: SensorsConfig = field(default_factory=SensorsConfig)
    kicker: Optional[KickerConfig] = None
    visual: Optional[VisualConfig] = None


class ConfigError(ValueError):
    """Raised when a robot YAML fails validation. Message names the bad field."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ConfigError(msg)


def _num(value, name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool),
             f"{name} must be a number, got {value!r}")
    return float(value)


def _validate(cfg: RobotConfig) -> None:
    _require(cfg.league in LEAGUE_LIMITS,
             f"league must be one of {sorted(LEAGUE_LIMITS)}, got {cfg.league!r}")
    limits       = LEAGUE_LIMITS[cfg.league]
    max_diameter = limits["max_diameter"]
    max_radius   = max_diameter / 2
    max_mass     = limits["max_mass"]

    b = cfg.body
    _require(b.shape in ("circle", "rectangle"),
             f"body.shape must be 'circle' or 'rectangle', got {b.shape!r}")
    if b.shape == "circle":
        _require(0 < b.radius <= max_radius,
                 f"body.radius must be in (0, {max_radius}] m "
                 f"(RCJ {cfg.league} league: {max_diameter * 100:.0f} cm "
                 f"diameter limit), got {b.radius}")
        reach = b.radius
    else:
        _require(0 < b.width <= max_diameter,
                 f"body.width must be in (0, {max_diameter}] m "
                 f"({cfg.league} league), got {b.width}")
        _require(0 < b.height <= max_diameter,
                 f"body.height must be in (0, {max_diameter}] m "
                 f"({cfg.league} league), got {b.height}")
        reach = math.hypot(b.width / 2, b.height / 2)
    if max_mass is not None:
        _require(0 < b.mass <= max_mass,
                 f"body.mass must be in (0, {max_mass}] kg "
                 f"(RCJ {cfg.league} league limit), got {b.mass}")
    else:
        _require(b.mass > 0, f"body.mass must be positive, got {b.mass}")
    _require(b.max_speed > 0,
             f"body.max_speed must be positive, got {b.max_speed}")

    w = cfg.wheels
    _require(w.type in ("omnidirectional", "differential"),
             f"wheels.type must be 'omnidirectional' or 'differential', got {w.type!r}")
    if w.type == "omnidirectional":
        _require(len(w.positions) >= 3,
                 f"omnidirectional drive needs >= 3 wheels, got {len(w.positions)}")

    s = cfg.sensors
    if s.ir_ring:
        _require(s.ir_ring.count >= 1,
                 f"sensors.ir_ring.count must be >= 1, got {s.ir_ring.count}")
        _require(s.ir_ring.range > 0,
                 f"sensors.ir_ring.range must be positive, got {s.ir_ring.range}")
        _require(s.ir_ring.noise_std >= 0,
                 f"sensors.ir_ring.noise_std must be >= 0, got {s.ir_ring.noise_std}")
    if s.compass:
        _require(s.compass.noise_std >= 0,
                 f"sensors.compass.noise_std must be >= 0, got {s.compass.noise_std}")
    if s.ultrasound:
        _require(len(s.ultrasound.directions) >= 1,
                 "sensors.ultrasound.directions must not be empty")
        _require(s.ultrasound.range > 0,
                 f"sensors.ultrasound.range must be positive, got {s.ultrasound.range}")
        _require(s.ultrasound.noise_std >= 0,
                 f"sensors.ultrasound.noise_std must be >= 0, got {s.ultrasound.noise_std}")
        for d in s.ultrasound.directions:
            _num(d, "sensors.ultrasound.directions[]")
    if s.line_sensors:
        for i, pos in enumerate(s.line_sensors.positions):
            _require(len(pos) == 2,
                     f"sensors.line_sensors.positions[{i}] must be [x, y], got {pos!r}")
            lx = _num(pos[0], f"sensors.line_sensors.positions[{i}].x")
            ly = _num(pos[1], f"sensors.line_sensors.positions[{i}].y")
            _require(math.hypot(lx, ly) <= reach + 1e-9,
                     f"sensors.line_sensors.positions[{i}] = ({lx}, {ly}) lies "
                     f"outside the robot body (reach {reach:.3f} m)")

    if cfg.kicker:
        _require(cfg.kicker.force > 0,
                 f"kicker.force must be positive, got {cfg.kicker.force}")
        _require(cfg.kicker.cooldown >= 0,
                 f"kicker.cooldown must be >= 0, got {cfg.kicker.cooldown}")

    if cfg.visual:
        v = cfg.visual
        _require(bool(v.mesh) and isinstance(v.mesh, str),
                 f"visual.mesh must be a .glb filename, got {v.mesh!r}")
        _require(not any(c in v.mesh for c in ("/", "\\")) and ".." not in v.mesh,
                 f"visual.mesh must be a plain filename inside robots/meshes/ "
                 f"(no paths), got {v.mesh!r}")
        _require(v.mesh.lower().endswith(".glb"),
                 f"visual.mesh must end in .glb, got {v.mesh!r}")
        _require(v.scale > 0, f"visual.scale must be positive, got {v.scale}")
        for label, triple in (("offset", v.offset), ("rotation", v.rotation)):
            _require(len(triple) == 3,
                     f"visual.{label} must be [x, y, z], got {triple!r}")
            for val in triple:
                _num(val, f"visual.{label}[]")


def load_robot_config(path: str) -> RobotConfig:
    with open(path) as f:
        data = yaml.safe_load(f)

    _require(isinstance(data, dict) and "robot" in data,
             f"{path}: top-level 'robot:' key missing")
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

    visual = None
    if "visual" in r and r["visual"]:
        d = r["visual"]
        visual = VisualConfig(
            mesh=d.get("mesh", ""),
            scale=d.get("scale", 1.0),
            offset=tuple(d.get("offset", (0.0, 0.0, 0.0))),
            rotation=tuple(d.get("rotation", (0.0, 0.0, 0.0))),
        )

    cfg = RobotConfig(
        name=r.get("name", "Robot"),
        league=r.get("league", DEFAULT_LEAGUE),
        body=body,
        wheels=wheels,
        sensors=sensors,
        kicker=kicker,
        visual=visual,
    )
    _validate(cfg)
    return cfg
