"""Testes da câmera simulada (B1) — sim/camera.py."""
import math

import numpy as np
import pytest

from sim.camera import (
    COLOR_BALL, field_color, render_camera,
)
from sim.config_loader import CameraConfig, ConfigError, load_robot_config
from sim.engine import SimEngine
from sim.field import HALF_L, HALF_TOTAL_L


def _is_orange(px) -> bool:
    r, g, b = int(px[0]), int(px[1]), int(px[2])
    return r > 150 and g < 160 and b < 90


def _orange_mask(frame):
    r = frame[:, :, 0].astype(int)
    g = frame[:, :, 1].astype(int)
    b = frame[:, :, 2].astype(int)
    return (r > 150) & (g > 30) & (g < 160) & (b < 90)


# ── field_color ───────────────────────────────────────────────────────────────

def test_field_color_regions():
    pts = np.array([
        [0.5, 0.5],                  # gramado
        [HALF_L, 0.0],               # linha branca (borda direita)
        [0.30, 0.0],                 # círculo central (linha preta)
        [-HALF_L - 0.03, 0.0],       # boca do gol azul
        [HALF_L + 0.03, 0.0],        # boca do gol amarelo
        [HALF_TOTAL_L + 0.5, 0.0],   # fora do carpete
    ])
    c = field_color(pts[:, 0], pts[:, 1])
    assert c[0][1] > c[0][0]                       # verde: G > R
    assert c[1].min() > 200                        # branco
    assert c[2].max() < 60                         # preto
    assert c[3][2] > 150 and c[3][0] < 100         # azul
    assert c[4][0] > 180 and c[4][1] > 120         # amarelo
    assert c[5].max() < 40                         # vazio


# ── Catadioptric ──────────────────────────────────────────────────────────────

def _cfg(**kw):
    base = dict(type="catadioptric", width=80, height=80, noise_std=0.0)
    base.update(kw)
    return CameraConfig(**base)


def test_catadioptric_sees_ball_ahead():
    frame = render_camera(_cfg(), 0.0, 0.0, 0.0, (0.4, 0.0), [])
    mask = _orange_mask(frame)
    assert mask.sum() > 0
    ys, xs = np.nonzero(mask)
    # bola à FRENTE → topo da imagem (y < centro)
    assert ys.mean() < frame.shape[0] / 2
    assert abs(xs.mean() - frame.shape[1] / 2) < 6


def test_catadioptric_ball_left_appears_left():
    # bola à esquerda (y+ do sim) → lado esquerdo da imagem
    frame = render_camera(_cfg(), 0.0, 0.0, 0.0, (0.0, 0.4), [])
    ys, xs = np.nonzero(_orange_mask(frame))
    assert xs.mean() < frame.shape[1] / 2


def test_catadioptric_heading_compensated():
    # robô virado 90° CCW: bola em +Y do mundo fica À FRENTE dele
    frame = render_camera(_cfg(), 0.0, 0.0, math.pi / 2, (0.0, 0.4), [])
    ys, xs = np.nonzero(_orange_mask(frame))
    assert ys.mean() < frame.shape[0] / 2


def test_catadioptric_sees_opponent():
    frame = render_camera(_cfg(), 0.0, 0.0, 0.0, (2.0, 2.0),
                          [(0.35, 0.0, 0.11, "yellow")])
    # cilindro escuro do robô à frente (acima do centro da imagem)
    top = frame[:frame.shape[0] // 2]
    dark = (top.astype(int).sum(axis=2) < 120).sum()
    assert dark > 4


# ── Pinhole / fisheye ─────────────────────────────────────────────────────────

def test_pinhole_ball_centered():
    cfg = _cfg(type="pinhole", fov=60, height_m=0.10)
    frame = render_camera(cfg, 0.0, 0.0, 0.0, (0.5, 0.0), [])
    mask = _orange_mask(frame)
    assert mask.sum() > 0
    ys, xs = np.nonzero(mask)
    assert abs(xs.mean() - frame.shape[1] / 2) < 8   # centrado em X


def test_pinhole_ball_behind_invisible():
    cfg = _cfg(type="pinhole", fov=60, height_m=0.10)
    frame = render_camera(cfg, 0.0, 0.0, 0.0, (-0.5, 0.0), [])
    assert _orange_mask(frame).sum() == 0


def test_fisheye_renders():
    cfg = _cfg(type="fisheye", fov=180, height_m=0.15)
    frame = render_camera(cfg, 0.0, 0.0, 0.0, (0.4, 0.0), [])
    assert frame.shape == (80, 80, 3)
    assert _orange_mask(frame).sum() > 0


def test_noise_reproducible():
    cfg = _cfg(noise_std=5.0)
    f1 = render_camera(cfg, 0, 0, 0, (0.4, 0), [], np.random.default_rng(7))
    f2 = render_camera(cfg, 0, 0, 0, (0.4, 0), [], np.random.default_rng(7))
    assert np.array_equal(f1, f2)


# ── Config / HAL ──────────────────────────────────────────────────────────────

def _yaml(tmp_path, sensors):
    p = tmp_path / "r.yaml"
    p.write_text(f"""
robot:
  name: T
  body: {{ radius: 0.09 }}
  sensors:
{sensors}
""")
    return str(p)


def test_camera_config_validated(tmp_path):
    with pytest.raises(ConfigError, match="camera.type"):
        load_robot_config(_yaml(tmp_path, "    camera: { type: telescope }"))
    with pytest.raises(ConfigError, match="width/height"):
        load_robot_config(_yaml(tmp_path, "    camera: { width: 4000 }"))


def test_hal_raises_without_camera():
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot("robots/striker_v3.yaml", team="blue")
    with pytest.raises(NotImplementedError):
        hal.read_camera_frame()


def test_hal_camera_frame_shape_and_content(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, """
    camera: { type: catadioptric, width: 64, height: 48, noise_std: 0 }
"""), team="blue")
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    engine.set_ball_pose(0.4, 0.0)
    frame = hal.read_camera_frame()
    assert frame.shape == (48, 64, 3) and frame.dtype == np.uint8
    assert _orange_mask(frame).sum() > 0


def test_hal_camera_sees_other_robot(tmp_path):
    engine = SimEngine(seed=0, referee=False)
    _, hal = engine.add_robot(_yaml(tmp_path, """
    camera: { type: catadioptric, width: 64, height: 64, noise_std: 0 }
"""), team="blue")
    engine.add_robot("robots/striker_v3.yaml", team="yellow")
    engine.set_robot_pose("blue_1", 0.0, 0.0, 0.0)
    engine.set_robot_pose("yellow_1", 0.35, 0.0)
    engine.set_ball_pose(2.0, 2.0)
    frame = hal.read_camera_frame()
    dark = (frame[:32].astype(int).sum(axis=2) < 120).sum()
    assert dark > 4


# ── Estratégia de visão fecha o ciclo ────────────────────────────────────────

def test_vision_strategy_scores(tmp_path):
    from examples.vision_strategy import strategy
    engine = SimEngine(seed=3, referee=False)
    engine.add_robot("robots/example.yaml", team="blue", strategy_fn=strategy)
    for _ in range(3600):
        engine.step()
        if engine.score["blue"] > 0:
            break
    assert engine.score["blue"] > 0


# ── encode_png ────────────────────────────────────────────────────────────────

def test_encode_png_valid():
    from sim.camera import encode_png
    frame = render_camera(_cfg(width=32, height=24), 0, 0, 0, (0.4, 0), [])
    png = encode_png(frame)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert b"IHDR" in png[:30] and png[-8:-4] == b"IEND"
