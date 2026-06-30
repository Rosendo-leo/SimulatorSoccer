"""Attacker strategy — port fiel do método Decisao::Attacker (C++).

Convenções do código original:
  vel.x  → strafe (positivo = direita do robô)
  vel.y  → frente/trás (positivo = frente)
  ball_angle em graus, 0 = bola à frente, + = esquerda, − = direita

Conversão para o HAL:
  hal.set_velocity(vx, vy, omega)
    vx  = frente  →  vel.y  × escala
    vy  = esquerda →  −vel.x × escala   (esquerda = −direita)
"""
from __future__ import annotations
import math
from sim.hal import HAL

# Potência máxima no código original → velocidade máxima do robô (m/s)
_MAX_POWER = 280.0
_MAX_SPEED = 1.5          # m/s (deve bater com body.max_speed do YAML)
_SCALE     = _MAX_SPEED / _MAX_POWER


def _map(value: float, in_min: float, in_max: float,
         out_min: float, out_max: float) -> int:
    """Equivalente ao map() do Arduino (sem clamp nos limites)."""
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def _ir_to_ball(ir_ring: list[float]) -> tuple[float, int]:
    """Converte leitura do anel IR em (ângulo_graus, dist).

    ângulo_graus : −180..180 em relação à frente do robô.
                   + = bola à esquerda (CCW), − = bola à direita (CW).
    dist         : 0 se bola não detectada, 1 se detectada.
    """
    if not ir_ring:
        return 0.0, 0
    n    = len(ir_ring)
    peak = max(range(n), key=lambda i: ir_ring[i])
    if ir_ring[peak] < 0.05:          # sem sinal confiável
        return 0.0, 0
    angle = (peak / n) * 360.0
    if angle > 180.0:
        angle -= 360.0                # normaliza para −180..180
    return angle, 1


def strategy(hal: HAL) -> None:
    ir    = hal.read_ir()
    lines = hal.read_line_sensors()

    ball_angle, dist = _ir_to_ball(ir)

    # Sensores de linha: posições do YAML [frente, trás, direita, esquerda]
    lf = bool(lines[0]) if len(lines) > 0 else False   # frente  (lf)
    lt = bool(lines[1]) if len(lines) > 1 else False   # trás    (lt)
    ld = bool(lines[2]) if len(lines) > 2 else False   # direita (ld)
    le = bool(lines[3]) if len(lines) > 3 else False   # esquerda(le)

    vel_x = 0   # strafe original (positivo = direita)
    vel_y = 0   # frente original (positivo = frente)

    if dist != 0 and not (ld or lf or le or lt):
        # ── Bola detectada e longe das linhas ──────────────────────────
        power     = 240
        mov_angle = abs(ball_angle)

        if mov_angle < 5:
            mov_angle = 0
            power     = 280
        elif mov_angle <= 20:
            power = 240                                          # ângulo sem mudança
        elif mov_angle <= 65:
            mov_angle = _map(mov_angle, 20,  65,  60,  95)
        elif mov_angle <= 95:
            mov_angle = _map(mov_angle, 60,  95,  65, 130)
        elif mov_angle <= 135:
            mov_angle = _map(mov_angle, 95, 135,  95, 180)
        elif mov_angle <= 185:
            mov_angle = _map(mov_angle, 135, 180, 135, 275)

        if ball_angle < 0:
            mov_angle = -mov_angle

        rad   = -(mov_angle * math.pi / 180.0)
        vel_x = int(math.sin(rad) * power)
        vel_y = int(math.cos(rad) * power)

    elif dist != 0:
        # ── Sensor de linha ativo → recuar da borda ───────────────────
        if lf: vel_y = -200
        if lt: vel_y =  200
        if ld: vel_x = -200
        if le: vel_x =  200

    # ── Sem bola detectada: para (vel_x=0, vel_y=0 por padrão) ───────

    # Converte para HAL: vx=frente, vy=esquerda
    hal.set_velocity(vel_y * _SCALE, -vel_x * _SCALE, 0.0)

    # Chuta quando a bola está bem na frente e perto
    if dist and ir and max(ir) > 0.75 and abs(ball_angle) < 20:
        hal.kick()
