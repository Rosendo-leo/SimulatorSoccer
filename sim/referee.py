"""Árbitro automático — RCJ Soccer Rules 2026 (2.5–2.9).

As checagens são funções puras sobre snapshots simples (sem PyMunk), para
serem testáveis isoladamente e fáceis de atualizar quando as regras mudarem.
O `Referee` mantém apenas o estado temporal (contadores de bola travada e
de posse) e devolve `Violation`s; quem aplica os efeitos é o engine.

Regras cobertas:
- Pushing (2.6): contato entre adversários dentro de uma área de pênalti com
  um deles tocando a bola → bola vai ao ponto neutro livre mais distante.
- Multiple defense (2.7): 2+ robôs do mesmo time na própria área → o mais
  distante da bola é movido a um ponto neutro.
- Lack of progress (2.8): bola parada na mesma região por N s → bola vai ao
  ponto neutro livre mais próximo.
- Holding (2.5): bola imobilizada junto a um robô por N s (sem dribbler
  regulamentar — exceção de backspin entra com o bloco `dribbler`, backlog B3)
  → tratado como lack of progress + violação atribuída ao robô.
- Damaged robot (2.9): a critério do árbitro — exposto via
  `SimEngine.mark_damaged(robot_id)`, sem detecção automática aqui.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from sim.field import HALF_L, PENALTY_DEPTH, PENALTY_HALF_Y

# ── Parâmetros (ticks a 60 Hz) ───────────────────────────────────────────────
LACK_OF_PROGRESS_TICKS = 600    # 10 s com a bola na mesma região
LACK_OF_PROGRESS_EPS   = 0.05   # raio (m) que define "mesma região"
HOLDING_TICKS          = 180    # 3 s de bola presa junto ao mesmo robô
HOLDING_GAP            = 0.03   # bola a menos de 3 cm do corpo = "presa"
HOLDING_REL_SPEED      = 0.15   # m/s — bola parada relativa ao robô
CONTACT_MARGIN         = 0.01   # 1 cm de folga para considerar contato


@dataclass(frozen=True)
class RobotSnapshot:
    robot_id: str
    team: str            # "blue" | "yellow"
    x: float
    y: float
    radius: float
    vx: float = 0.0
    vy: float = 0.0
    # Dribbler regulamentar ativo → isento da regra de holding (2.5.2)
    dribbler_active: bool = False


@dataclass(frozen=True)
class Violation:
    kind: str                       # "pushing" | "multiple_defense" | ...
    robot_id: Optional[str] = None  # robô a mover/punir (se aplicável)
    detail: str = ""


# ── Geometria ─────────────────────────────────────────────────────────────────

def in_penalty_area(x: float, y: float, side: str) -> bool:
    """Centro (x, y) dentro da área de pênalti do lado dado.

    'blue' = área na frente do gol azul (x negativo). Aproximação retangular
    (ignora os cantos arredondados de 15 cm — diferença desprezível aqui).
    """
    if abs(y) > PENALTY_HALF_Y:
        return False
    front = HALF_L - PENALTY_DEPTH
    return x <= -front if side == "blue" else x >= front


def _touching_ball(r: RobotSnapshot, ball: Tuple[float, float],
                   ball_radius: float) -> bool:
    return (math.hypot(r.x - ball[0], r.y - ball[1])
            <= r.radius + ball_radius + CONTACT_MARGIN)


# ── Checagens puras ───────────────────────────────────────────────────────────

def check_pushing(robots: Sequence[RobotSnapshot],
                  ball: Tuple[float, float],
                  ball_radius: float) -> Optional[Violation]:
    """Contato atacante × defensor dentro de uma área, com bola em disputa."""
    for i in range(len(robots)):
        for j in range(i + 1, len(robots)):
            a, b = robots[i], robots[j]
            if a.team == b.team:
                continue
            dist = math.hypot(a.x - b.x, a.y - b.y)
            if dist > a.radius + b.radius + CONTACT_MARGIN:
                continue
            for side in ("blue", "yellow"):
                if (in_penalty_area(a.x, a.y, side)
                        or in_penalty_area(b.x, b.y, side)):
                    if (_touching_ball(a, ball, ball_radius)
                            or _touching_ball(b, ball, ball_radius)):
                        return Violation(
                            "pushing", None,
                            f"{a.robot_id} × {b.robot_id} na área {side}")
    return None


def check_multiple_defense(robots: Sequence[RobotSnapshot],
                           ball: Tuple[float, float]) -> Optional[Violation]:
    """2+ robôs do mesmo time na própria área → move o mais longe da bola."""
    for team in ("blue", "yellow"):
        inside = [r for r in robots
                  if r.team == team and in_penalty_area(r.x, r.y, team)]
        if len(inside) >= 2:
            worst = max(inside,
                        key=lambda r: math.hypot(r.x - ball[0], r.y - ball[1]))
            return Violation("multiple_defense", worst.robot_id,
                             f"{len(inside)} robôs {team} na própria área")
    return None


# ── Árbitro com estado temporal ───────────────────────────────────────────────

class Referee:
    """Acumula estado entre ticks (bola travada / posse prolongada)."""

    def __init__(self) -> None:
        self._stuck_anchor: Optional[Tuple[float, float]] = None
        self._stuck_ticks = 0
        self._hold_robot: Optional[str] = None
        self._hold_ticks = 0

    def reset(self) -> None:
        """Zera contadores (chamar em kickoff / reposição da bola)."""
        self._stuck_anchor = None
        self._stuck_ticks = 0
        self._hold_robot = None
        self._hold_ticks = 0

    def _update_lack_of_progress(
            self, ball: Tuple[float, float]) -> Optional[Violation]:
        if (self._stuck_anchor is None
                or math.hypot(ball[0] - self._stuck_anchor[0],
                              ball[1] - self._stuck_anchor[1])
                > LACK_OF_PROGRESS_EPS):
            self._stuck_anchor = ball
            self._stuck_ticks = 0
            return None
        self._stuck_ticks += 1
        if self._stuck_ticks >= LACK_OF_PROGRESS_TICKS:
            self._stuck_ticks = 0
            self._stuck_anchor = None
            return Violation("lack_of_progress", None,
                             f"bola parada por {LACK_OF_PROGRESS_TICKS} ticks")
        return None

    def _update_holding(self, robots: Sequence[RobotSnapshot],
                        ball: Tuple[float, float],
                        ball_vel: Tuple[float, float],
                        ball_radius: float) -> Optional[Violation]:
        holder = None
        for r in robots:
            if r.dribbler_active:        # exceção do backspin (Rule 2.5.2)
                continue
            gap = (math.hypot(r.x - ball[0], r.y - ball[1])
                   - r.radius - ball_radius)
            rel_speed = math.hypot(ball_vel[0] - r.vx, ball_vel[1] - r.vy)
            if gap <= HOLDING_GAP and rel_speed <= HOLDING_REL_SPEED:
                holder = r.robot_id
                break
        if holder is None or holder != self._hold_robot:
            self._hold_robot = holder
            self._hold_ticks = 0
            return None
        self._hold_ticks += 1
        if self._hold_ticks >= HOLDING_TICKS:
            self._hold_ticks = 0
            self._hold_robot = None
            return Violation("holding", holder,
                             f"bola presa por {HOLDING_TICKS} ticks")
        return None

    def step(self, robots: Sequence[RobotSnapshot],
             ball: Tuple[float, float],
             ball_vel: Tuple[float, float],
             ball_radius: float) -> List[Violation]:
        """Roda todas as checagens para um tick. No máx. 1 violação por tipo."""
        violations: List[Violation] = []
        v = check_pushing(robots, ball, ball_radius)
        if v:
            violations.append(v)
        v = check_multiple_defense(robots, ball)
        if v:
            violations.append(v)
        v = self._update_holding(robots, ball, ball_vel, ball_radius)
        if v:
            violations.append(v)
        # Holding já reposiciona a bola; evita disparo duplo no mesmo tick
        if not any(x.kind == "holding" for x in violations):
            v = self._update_lack_of_progress(ball)
            if v:
                violations.append(v)
        return violations
