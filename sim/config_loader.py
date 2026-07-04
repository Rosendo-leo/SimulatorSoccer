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
class BallVelocityConfig:
    """Sensor de velocidade absoluta da bola (estilo Leopard: sensor óptico
    de movimento). Retorna (vx, vy) em m/s no frame do MUNDO, com ruído."""
    noise_std: float = 0.05


@dataclass
class OpponentLidarConfig:
    """Feixe de sensores de distância que detecta apenas ROBÔS (estilo
    Leopard: 5 ToF a 20°). Ignora paredes e bola; detecta qualquer robô,
    inclusive o parceiro — como um ToF real faria."""
    directions: List[float] = field(default_factory=lambda: [-40, -20, 0, 20, 40])
    range: float = 1.0
    noise_std: float = 0.02


@dataclass
class CameraConfig:
    """Câmera simulada (B1) — frame RGB via hal.read_camera_frame().

    Renderização lazy (só quando chamada), rasterizador numpy headless
    (sim/camera.py). Mantenha a resolução BAIXA (ex. 160×120) — o custo
    é proporcional a width×height.
    """
    type: str = "catadioptric"      # pinhole | fisheye | catadioptric
    width: int = 160
    height: int = 120
    fov: float = 60.0               # pinhole/fisheye: FOV horizontal (graus)
    direction: float = 0.0          # pinhole/fisheye: direção rel. ao heading
    height_m: float = 0.25          # altura da lente/espelho (m)
    range: float = 2.5              # catadioptric: alcance máx no chão (m)
    noise_std: float = 4.0          # ruído gaussiano por canal (0–255)


@dataclass
class SensorsConfig:
    ir_ring: Optional[IRRingConfig] = None
    compass: Optional[CompassConfig] = None
    ultrasound: Optional[UltrasoundConfig] = None
    line_sensors: Optional[LineSensorsConfig] = None
    ball_velocity: Optional[BallVelocityConfig] = None
    opponent_lidar: Optional[OpponentLidarConfig] = None
    camera: Optional[CameraConfig] = None


@dataclass
class KickerConfig:
    force: float = 5.0
    cooldown: float = 2.0
    # Setor de chute dirigível, em graus centrado na frente (B4, estilo
    # Leopard com 2 solenoides): 0 = só frontal (default), 90 = ±45°,
    # 360 = chuta em qualquer direção. Use hal.kick(angle_deg).
    aim_range: float = 0.0


@dataclass
class DribblerConfig:
    """Dribbler (B3): rolete que mantém a bola presa por backspin.

    Modelo 2D: força-mola puxando a bola para a 'boca' do dribbler +
    amortecimento da velocidade relativa (efeito do backspin). Robôs com
    dribbler ATIVO ficam isentos da violação de holding (Rule 2.5.2);
    a boca fica fora do corpo, respeitando a zona de captura ≤ 1,5 cm.
    """
    position: str = "front"         # front | back
    strength: float = 1.0           # multiplicador da força de captura
    capture_radius: float = 0.05    # alcance da captura a partir da boca (m)


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
    dribbler: Optional[DribblerConfig] = None
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
    if s.ball_velocity:
        _require(s.ball_velocity.noise_std >= 0,
                 f"sensors.ball_velocity.noise_std must be >= 0, "
                 f"got {s.ball_velocity.noise_std}")
    if s.opponent_lidar:
        _require(len(s.opponent_lidar.directions) >= 1,
                 "sensors.opponent_lidar.directions must not be empty")
        _require(s.opponent_lidar.range > 0,
                 f"sensors.opponent_lidar.range must be positive, "
                 f"got {s.opponent_lidar.range}")
        _require(s.opponent_lidar.noise_std >= 0,
                 f"sensors.opponent_lidar.noise_std must be >= 0, "
                 f"got {s.opponent_lidar.noise_std}")
        for d in s.opponent_lidar.directions:
            _num(d, "sensors.opponent_lidar.directions[]")
    if s.camera:
        c = s.camera
        _require(c.type in ("pinhole", "fisheye", "catadioptric"),
                 f"sensors.camera.type must be pinhole/fisheye/catadioptric, "
                 f"got {c.type!r}")
        _require(16 <= c.width <= 320 and 16 <= c.height <= 320,
                 f"sensors.camera width/height must be in [16, 320] px, "
                 f"got {c.width}x{c.height}")
        _require(10 <= c.fov <= 200,
                 f"sensors.camera.fov must be in [10, 200] degrees, got {c.fov}")
        _require(c.height_m > 0,
                 f"sensors.camera.height_m must be positive, got {c.height_m}")
        _require(c.range > 0,
                 f"sensors.camera.range must be positive, got {c.range}")
        _require(c.noise_std >= 0,
                 f"sensors.camera.noise_std must be >= 0, got {c.noise_std}")
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
        _require(0 <= cfg.kicker.aim_range <= 360,
                 f"kicker.aim_range must be in [0, 360] degrees, "
                 f"got {cfg.kicker.aim_range}")

    if cfg.dribbler:
        d = cfg.dribbler
        _require(d.position in ("front", "back"),
                 f"dribbler.position must be 'front' or 'back', "
                 f"got {d.position!r}")
        _require(d.strength > 0,
                 f"dribbler.strength must be positive, got {d.strength}")
        _require(0 < d.capture_radius <= 0.08,
                 f"dribbler.capture_radius must be in (0, 0.08] m, "
                 f"got {d.capture_radius}")

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

    d = sd.get("ir_ring")
    if d is not None:
        sensors.ir_ring = IRRingConfig(
            count=d.get("count", 16),
            range=d.get("range", 1.5),
            noise_std=d.get("noise_std", 0.05),
        )

    d = sd.get("compass")
    if d is not None:
        sensors.compass = CompassConfig(noise_std=d.get("noise_std", 2.0))

    d = sd.get("ultrasound")
    if d is not None:
        sensors.ultrasound = UltrasoundConfig(
            count=d.get("count", 4),
            directions=d.get("directions", [0, 90, 180, 270]),
            range=d.get("range", 2.0),
            noise_std=d.get("noise_std", 0.03),
        )

    d = sd.get("line_sensors")
    if d is not None:
        sensors.line_sensors = LineSensorsConfig(
            count=d.get("count", 4),
            positions=[tuple(p) for p in d.get("positions", [])],
        )

    d = sd.get("ball_velocity")
    if d is not None:
        sensors.ball_velocity = BallVelocityConfig(
            noise_std=d.get("noise_std", 0.05),
        )

    d = sd.get("opponent_lidar")
    if d is not None:
        sensors.opponent_lidar = OpponentLidarConfig(
            directions=d.get("directions", [-40, -20, 0, 20, 40]),
            range=d.get("range", 1.0),
            noise_std=d.get("noise_std", 0.02),
        )

    d = sd.get("camera")
    if d is not None:
        sensors.camera = CameraConfig(
            type=d.get("type", "catadioptric"),
            width=int(d.get("width", 160)),
            height=int(d.get("height", 120)),
            fov=d.get("fov", 60.0),
            direction=d.get("direction", 0.0),
            height_m=d.get("height_m", 0.25),
            range=d.get("range", 2.5),
            noise_std=d.get("noise_std", 4.0),
        )

    # `bloco: null` no YAML (ex.: toggle desligado no Builder) = ausente
    kicker = None
    if r.get("kicker"):
        d = r["kicker"]
        kicker = KickerConfig(
            force=d.get("force", 5.0),
            cooldown=d.get("cooldown", 2.0),
            aim_range=d.get("aim_range", 0.0),
        )

    dribbler = None
    if "dribbler" in r and r["dribbler"]:
        d = r["dribbler"]
        dribbler = DribblerConfig(
            position=d.get("position", "front"),
            strength=d.get("strength", 1.0),
            capture_radius=d.get("capture_radius", 0.05),
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
        dribbler=dribbler,
        visual=visual,
    )
    _validate(cfg)
    return cfg
