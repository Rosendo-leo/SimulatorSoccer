"""State Machine strategy — template didático (estilo Aperture Open TDP).

Máquina de estados explícita, como o striker do Aperture Open:

    SEARCH ──bola vista──► CHASE ──bola perto──► ALIGN ──alinhado──► SHOOT
       ▲                     │                     │                   │
       └────bola sumiu───────┴─────────────────────┴───────────────────┘

- SEARCH: gira no lugar procurando sinal no anel IR.
- CHASE:  anda na direção da bola (ângulo do IR).
- ALIGN:  orbita a bola até ficar atrás dela olhando o gol adversário
          (usa a bússola: ataque é sempre no sentido +X do campo).
- SHOOT:  avança reto e chuta.
- Guarda global: sensor de linha ativo → recua (prioridade máxima).

O estado é guardado por robô (keyed pelo id do HAL) porque strategy(hal)
é uma função chamada a cada tick, sem instância própria.
"""
from __future__ import annotations

import math

from sim.hal import HAL

_SPEED       = 1.2     # m/s de cruzeiro
_ORBIT_SPEED = 0.9
_NEAR        = 0.60    # intensidade IR que define "bola perto" (0-1)
_ALIGN_TOL   = math.radians(25)   # tolerância p/ considerar "olhando o gol"

# Estado por robô: id(hal) → dict
_mem: dict[int, dict] = {}


def _ball_from_ir(ir: list[float]) -> tuple[float, float]:
    """(ângulo_rad local, intensidade 0-1). Ângulo 0 = frente, + = esquerda."""
    if not ir:
        return 0.0, 0.0
    n    = len(ir)
    peak = max(range(n), key=lambda i: ir[i])
    if ir[peak] < 0.05:
        return 0.0, 0.0
    angle = (peak / n) * 2 * math.pi
    if angle > math.pi:
        angle -= 2 * math.pi
    return angle, ir[peak]


def strategy(hal: HAL) -> None:
    mem = _mem.setdefault(id(hal), {"state": "SEARCH"})
    state = mem["state"]

    ir      = hal.read_ir()
    lines   = hal.read_line_sensors()
    heading = hal.read_compass()

    ball_angle, intensity = _ball_from_ir(ir)
    seen = intensity > 0.0

    # ── Guarda global: linha branca → recua e volta a procurar ──────────────
    if any(lines):
        lf = lines[0] if len(lines) > 0 else False
        lt = lines[1] if len(lines) > 1 else False
        ld = lines[2] if len(lines) > 2 else False
        le = lines[3] if len(lines) > 3 else False
        vx = -_SPEED if lf else (_SPEED if lt else 0.0)
        vy =  _SPEED if ld else (-_SPEED if le else 0.0)
        hal.set_velocity(vx, vy, 0.0)
        mem["state"] = "SEARCH"
        return

    # ── Transições ───────────────────────────────────────────────────────────
    if not seen:
        state = "SEARCH"
    elif state == "SEARCH":
        state = "CHASE"
    elif state == "CHASE" and intensity >= _NEAR:
        state = "ALIGN"
    elif state == "ALIGN":
        # Alinhado = bola à frente E robô apontando para o gol adversário (+X)
        if abs(ball_angle) < math.radians(15) and abs(heading) < _ALIGN_TOL:
            state = "SHOOT"
        elif intensity < _NEAR * 0.5:      # bola escapou → persegue de novo
            state = "CHASE"
    elif state == "SHOOT" and (intensity < _NEAR * 0.5
                               or abs(ball_angle) > math.radians(45)):
        state = "CHASE"
    mem["state"] = state

    # ── Ações por estado ─────────────────────────────────────────────────────
    if state == "SEARCH":
        hal.set_velocity(0.0, 0.0, 2.0)            # gira procurando

    elif state == "CHASE":
        hal.set_velocity(math.cos(ball_angle) * _SPEED,
                         math.sin(ball_angle) * _SPEED, 0.0)

    elif state == "ALIGN":
        # Orbita: componente tangencial à bola + correção de heading p/ o gol.
        # Lado da órbita = lado que aproxima o heading de 0 (gol em +X).
        side  = 1.0 if heading > 0 else -1.0
        hal.set_velocity(math.cos(ball_angle) * 0.35 * _SPEED,   # mantém perto
                         side * _ORBIT_SPEED,                     # orbita
                         -heading * 2.0)                          # vira p/ o gol

    elif state == "SHOOT":
        hal.set_velocity(_SPEED, math.sin(ball_angle) * 0.5, -heading * 1.5)
        if intensity > 0.75 and abs(ball_angle) < math.radians(20):
            hal.kick()
