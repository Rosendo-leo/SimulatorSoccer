"""Defender (goleiro) strategy — port fiel do método Decisao::Defender (C++).

Comportamento:
  vel.y = −90  → recua levemente em direção ao próprio gol
  vel.y = +260 → avança (ao tocar qualquer linha branca)
  vel.x        → rastreia a bola lateralmente quando no centro (±160 mm)
               → retorna ao centro quando fora da zona

'posx' do código original = posição lateral do robô em mm.
No sim usamos a coordenada Y do mundo × 1000 (eixo perpendicular ao gol).
"""
from __future__ import annotations
import math
from sim.hal import HAL

_MAX_POWER      = 280.0
_MAX_SPEED      = 1.5          # m/s
_SCALE          = _MAX_SPEED / _MAX_POWER
_CENTER_ZONE_MM = 160          # zona central ±160 mm (±0.16 m)


def _ir_to_ball(ir_ring: list[float]) -> tuple[float, int]:
    if not ir_ring:
        return 0.0, 0
    n    = len(ir_ring)
    peak = max(range(n), key=lambda i: ir_ring[i])
    if ir_ring[peak] < 0.05:
        return 0.0, 0
    angle = (peak / n) * 360.0
    if angle > 180.0:
        angle -= 360.0
    return angle, 1


def strategy(hal: HAL) -> None:
    ir    = hal.read_ir()
    lines = hal.read_line_sensors()
    _, py = hal.read_position()     # coordenada Y do mundo (metros)

    ball_angle, dist = _ir_to_ball(ir)

    lf = bool(lines[0]) if len(lines) > 0 else False
    lt = bool(lines[1]) if len(lines) > 1 else False
    ld = bool(lines[2]) if len(lines) > 2 else False
    le = bool(lines[3]) if len(lines) > 3 else False

    any_line = ld or lt or le or lf

    # Posição lateral em mm (equivale a 'posx' do código original)
    posx = int(py * 1000)

    vel_x = 0
    vel_y = 0

    # ── Movimento frente/trás (vel.y) ─────────────────────────────────
    if any_line:
        vel_y = 260     # sai da linha → avança
    else:
        vel_y = -90     # deriva suavemente para o próprio gol

    # ── Rastreio lateral (vel.x) ──────────────────────────────────────
    if dist != 0 and (-_CENTER_ZONE_MM <= posx <= _CENTER_ZONE_MM):
        power = 240
        vel_x = int(math.sin(-(ball_angle * math.pi / 180.0)) * power)
    elif dist != 0:
        # Fora da zona central: retorna ao centro
        vel_x = 120 if posx < 0 else -120
    else:
        # Sem bola: para tudo
        vel_x = 0
        vel_y = 0

    # Converte para HAL: vx=frente, vy=esquerda
    hal.set_velocity(vel_y * _SCALE, -vel_x * _SCALE, 0.0)
