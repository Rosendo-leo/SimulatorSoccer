"""Teste de força do kicker — Rules 2026 §6.2.C.2 / Anexo A.

Procedimento oficial replicado: robô encostado na parede do próprio gol,
bola à frente, um chute. O kick é REPROVADO se a bola, depois de rebater
no gol adversário, voltar e bater na parede de trás do próprio gol.

Uso: python -m sim --kicker-test --blue robots/striker_v3.yaml
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.ball import BALL_RADIUS
from sim.engine import SimEngine, PHYSICS_DT, PHYSICS_SUBSTEPS, BALL_DAMPING
from sim.field import HALF_L, HALF_G

_TIMEOUT_TICKS = 1200    # 20 s de simulação no máximo
_STOP_SPEED    = 0.02    # bola considerada parada (m/s)


@dataclass
class KickerTestResult:
    passed: bool
    kicked: bool                    # o kick chegou a acelerar a bola?
    reached_opponent_goal: bool     # bola rebateu no gol adversário
    returned_to_own_goal: bool      # bola voltou até o próprio gol (reprova)
    max_x: float                    # alcance máximo (m; gol adversário ≈ +1.095)
    final_x: float                  # posição final da bola
    ticks: int

    def report(self) -> str:
        lines = [
            "Kicker test (Rules 2026 §6.2.C.2 / Anexo A)",
            f"  chute executado:        {'sim' if self.kicked else 'NÃO'}",
            f"  alcance máximo:         {self.max_x:+.3f} m "
            f"(gol adversário em {HALF_L:+.3f})",
            f"  rebateu no gol rival:   {'sim' if self.reached_opponent_goal else 'não'}",
            f"  voltou ao próprio gol:  {'SIM' if self.returned_to_own_goal else 'não'}",
            f"  duração:                {self.ticks * PHYSICS_DT:.1f} s",
            f"  resultado:              {'APROVADO' if self.passed else 'REPROVADO'}",
        ]
        if not self.kicked:
            lines.append("  (bola fora do alcance do kicker ou robô sem kicker)")
        return "\n".join(lines)


def run_kicker_test(yaml_path: str, seed: int | None = 0) -> KickerTestResult:
    engine = SimEngine(seed=seed, referee=False)

    # Robô azul encostado na parede de trás do próprio gol, olhando o adversário
    robot, hal = engine.add_robot(yaml_path, team="blue", heading=0.0,
                                  position=(0.0, 0.0))
    radius = robot.config.body.radius
    x0 = -HALF_L + radius            # encostado na linha do gol
    engine.set_robot_pose("blue_1", x0, 0.0, 0.0)

    # Bola imediatamente à frente, dentro do alcance do kicker
    ball_x = x0 + radius + BALL_RADIUS + 0.005
    engine.set_ball_pose(ball_x, 0.0)

    # Um único chute
    hal._refresh_percepts()
    hal.kick()
    hal._apply_action(PHYSICS_DT)

    body   = engine.ball.body
    kicked = body.velocity.length > 0.1

    # Loop de física puro (sem engine.step: a detecção de gol pausaria/resetaria
    # a bola durante o rebote, o que invalidaria o procedimento do Anexo A)
    space  = engine._space
    sub_dt = PHYSICS_DT / PHYSICS_SUBSTEPS
    max_x  = body.position.x
    reached = returned = False
    tick = 0
    for tick in range(1, _TIMEOUT_TICKS + 1):
        vx, vy = body.velocity
        body.velocity = (vx * BALL_DAMPING, vy * BALL_DAMPING)
        for _ in range(PHYSICS_SUBSTEPS):
            space.step(sub_dt)
        bx, by = body.position
        max_x = max(max_x, bx)
        if bx > HALF_L and abs(by) < HALF_G:
            reached = True
        if reached and bx < -HALF_L and abs(by) < HALF_G:
            returned = True
            break
        if body.velocity.length < _STOP_SPEED and tick > 30:
            break

    return KickerTestResult(
        passed=kicked and not returned,
        kicked=kicked,
        reached_opponent_goal=reached,
        returned_to_own_goal=returned,
        max_x=round(max_x, 4),
        final_x=round(body.position.x, 4),
        ticks=tick,
    )
