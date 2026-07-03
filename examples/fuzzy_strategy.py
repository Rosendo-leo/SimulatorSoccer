"""Fuzzy strategy — template didático (estilo MegaHertz TDP).

Em vez de estados discretos, combina evidências contínuas em um valor de
confiança 0–1 e mistura dois comportamentos proporcionalmente:

    atk (0–1) = quão seguro estou para ATACAR agora?
              = min(bola_perto, bola_à_frente, campo_livre)
    def (0–1) = 1 − atk

    velocidade final = atk × vetor_ataque + def × vetor_defesa

- vetor_ataque : ir na direção da bola (e chutar quando colada à frente)
- vetor_defesa : recuar para a frente do próprio gol (x ≈ −0.8, y ≈ y_bola)

As funções de pertinência são trapézios/triângulos simples — o objetivo do
template é mostrar a estrutura (fuzzificação → regras → defuzzificação),
não afinar constantes.
"""
from __future__ import annotations

import math

from sim.hal import HAL

_SPEED    = 1.3
_HOME_X   = -0.80    # posto defensivo (frente da própria área, gol azul em −X)


def _tri(x: float, lo: float, peak: float, hi: float) -> float:
    """Pertinência triangular: 0 fora de [lo, hi], 1 em peak."""
    if x <= lo or x >= hi:
        return 0.0
    return (x - lo) / (peak - lo) if x < peak else (hi - x) / (hi - peak)


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
    ir      = hal.read_ir()
    lines   = hal.read_line_sensors()
    heading = hal.read_compass()
    px, py  = hal.read_position()

    ball_angle, intensity = _ball_from_ir(ir)

    # ── Guarda: linha branca → recua (fora da lógica fuzzy) ─────────────────
    if any(lines):
        lf = lines[0] if len(lines) > 0 else False
        lt = lines[1] if len(lines) > 1 else False
        ld = lines[2] if len(lines) > 2 else False
        le = lines[3] if len(lines) > 3 else False
        hal.set_velocity(-_SPEED if lf else (_SPEED if lt else 0.0),
                         _SPEED if ld else (-_SPEED if le else 0.0), 0.0)
        return

    # ── Fuzzificação ─────────────────────────────────────────────────────────
    # bola_perto: intensidade IR alta ⇒ 1
    ball_near  = _tri(intensity, 0.10, 1.00, 1.01)
    # bola_à_frente: |ângulo| pequeno ⇒ 1 (some além de 100°)
    ball_ahead = _tri(-abs(ball_angle), -math.radians(100), 0.0, 0.01)
    # campo_livre: ultrassom frontal longe de obstáculo ⇒ 1
    us = hal.read_ultrasound()
    front_clear = _tri(us[0], 0.15, 0.80, 99.0) if us else 1.0
    # Com opponent_lidar no YAML, use-o no lugar do ultrassom:
    #   front_clear = _tri(min(hal.read_opponent_lidar()), 0.15, 0.8, 99.0)

    # ── Regras (t-norm = min, como no MegaHertz) ─────────────────────────────
    atk = min(max(ball_near, 0.15),      # nunca zera de vez: persegue fraco
              max(ball_ahead, 0.30),
              max(front_clear, 0.40))
    dfn = 1.0 - atk

    # ── Defuzzificação: mistura dos dois vetores ─────────────────────────────
    # Vetor de ataque (frame local): direção da bola
    atk_vx = math.cos(ball_angle)
    atk_vy = math.sin(ball_angle)

    # Vetor de defesa (frame do mundo → local): voltar ao posto (−0.8, y_bola)
    tgt_y   = max(-0.55, min(0.55, py))     # mantém o y atual, limitado ao gol
    wdx, wdy = _HOME_X - px, tgt_y - py
    norm = math.hypot(wdx, wdy)
    if norm > 0.05:
        wdx, wdy = wdx / norm, wdy / norm
    else:
        wdx = wdy = 0.0
    cos_h, sin_h = math.cos(-heading), math.sin(-heading)
    def_vx = cos_h * wdx - sin_h * wdy
    def_vy = sin_h * wdx + cos_h * wdy

    vx = (atk * atk_vx + dfn * def_vx) * _SPEED
    vy = (atk * atk_vy + dfn * def_vy) * _SPEED
    omega = -heading * 1.5          # sempre tende a olhar o gol adversário

    hal.set_velocity(vx, vy, omega)

    # Chute: só com confiança de ataque alta e bola colada à frente
    if atk > 0.7 and intensity > 0.75 and abs(ball_angle) < math.radians(20):
        hal.kick()
