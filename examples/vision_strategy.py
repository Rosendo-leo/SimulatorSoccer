"""Vision strategy — template didático de pipeline por câmera (liga Vision).

Usa SÓ a câmera simulada (`hal.read_camera_frame()`) para achar a bola:
threshold de cor laranja → centróide do blob → ângulo/distância → dirige.
É a mesma estrutura de um pipeline OpenMV/blob real (Aperture, XLC):

    frame RGB → máscara de cor → centróide → controle

Requer um robô com bloco `sensors.camera` (default: catadioptric — o
espelho 360° do Aperture; o mapeamento pixel→direção assume esse modo).
Ex.: examples/vision_robot.yaml ou o robots/example.yaml.
"""
from __future__ import annotations

import math

import numpy as np

from sim.hal import HAL

_SPEED = 1.2


def _find_ball(frame: np.ndarray) -> tuple[float, float] | None:
    """Acha o blob laranja. Retorna (ângulo_rad local, r_norm 0-1) ou None.

    Na imagem catadióptrica: centro = robô, topo = frente. O ângulo do
    centróide em torno do centro é a direção da bola no frame do robô;
    o raio normalizado cresce com a distância.
    """
    r = frame[:, :, 0].astype(np.int16)
    g = frame[:, :, 1].astype(np.int16)
    b = frame[:, :, 2].astype(np.int16)
    mask = (r > 150) & (g > 30) & (g < 160) & (b < 90)   # laranja
    if mask.sum() < 4:                                    # blob mínimo
        return None
    ys, xs = np.nonzero(mask)
    h, w  = mask.shape
    cx, cy = xs.mean() - w / 2, ys.mean() - h / 2         # rel. ao centro
    # topo da imagem (cy negativo) = frente; ângulo CCW positivo p/ esquerda
    angle  = math.atan2(-cx, -cy)
    r_norm = math.hypot(cx / (w / 2), cy / (h / 2))
    return angle, min(1.0, r_norm)


def strategy(hal: HAL) -> None:
    frame = hal.read_camera_frame()
    found = _find_ball(frame)

    if found is None:
        hal.set_velocity(0.0, 0.0, 2.0)      # gira procurando a bola
        return

    angle, r_norm = found
    # Perto (blob perto do centro) e à frente → chuta
    if r_norm < 0.18 and abs(angle) < math.radians(25):
        hal.set_velocity(_SPEED, 0.0, 0.0)
        hal.kick()
        return

    hal.set_velocity(math.cos(angle) * _SPEED,
                     math.sin(angle) * _SPEED,
                     angle * 1.5)             # vira enquanto anda
