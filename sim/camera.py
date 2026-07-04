"""Câmera simulada (B1) — rasterizador numpy headless.

Renderiza um frame RGB (H, W, 3) uint8 do ponto de vista do robô, sem
depender do viewer Three.js — funciona em --headless, no RL e no CI.

Três modelos (ver docs/design_camera_sim.md):
  pinhole      — perspectiva clássica (OpenMV etc.), FOV configurável
  fisheye      — equidistante (r = f·θ), FOV padrão 180°
  catadioptric — espelho cônico p/ baixo (Aperture): vista 360° do chão

Todos compartilham o mesmo núcleo: geração de raios + ray-cast vetorizado
contra (1) o chão com cor procedural do campo, (2) a bola (esfera),
(3) robôs (cilindros) e (4) as paredes externas. Cores chapadas, sem
iluminação — o suficiente para blob por cor / CNN leve.
"""
from __future__ import annotations

import math

import numpy as np

from sim.ball import BALL_RADIUS
from sim.field import (
    FIELD_LINE_ARCS,
    FIELD_LINE_SEGMENTS,
    CENTER_CIRCLE_RADIUS,
    GOAL_DEPTH,
    HALF_G,
    HALF_L,
    HALF_TOTAL_L,
    HALF_TOTAL_W,
    LINE_HALF_THICKNESS,
    NEUTRAL_SPOTS,
)

# ── Paleta (RGB uint8) ────────────────────────────────────────────────────────
COLOR_GRASS      = np.array([30, 120, 40],   dtype=np.float32)
COLOR_LINE       = np.array([240, 240, 240], dtype=np.float32)
COLOR_BLACK_LINE = np.array([25, 25, 25],    dtype=np.float32)
COLOR_GOAL_BLUE  = np.array([50, 110, 240],  dtype=np.float32)
COLOR_GOAL_YEL   = np.array([230, 185, 20],  dtype=np.float32)
COLOR_WALL       = np.array([45, 45, 48],    dtype=np.float32)
COLOR_VOID       = np.array([12, 12, 16],    dtype=np.float32)
COLOR_BALL       = np.array([255, 90, 10],   dtype=np.float32)
COLOR_ROBOT      = np.array([28, 28, 30],    dtype=np.float32)
COLOR_TEAM = {
    "blue":   np.array([59, 130, 246], dtype=np.float32),
    "yellow": np.array([234, 179, 8],  dtype=np.float32),
}

ROBOT_HEIGHT      = 0.22   # altura do cilindro do robô (m)
TEAM_BAND_MIN_Z   = 0.15   # acima disso o cilindro tem a cor do time
WALL_HEIGHT       = 0.15
_BLACK_HALF_THICK = 0.010  # meia-espessura do círculo central / pontos neutros


# ── Cor procedural do chão ────────────────────────────────────────────────────

def field_color(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Cor do chão em cada (x, y) — vetorizado. Retorna (N, 3) float32."""
    n   = x.shape[0]
    out = np.tile(COLOR_GRASS, (n, 1))

    # Fora do carpete total → vazio (chão escuro)
    inside = (np.abs(x) <= HALF_TOTAL_L + 1e-9) & (np.abs(y) <= HALF_TOTAL_W + 1e-9)
    out[~inside] = COLOR_VOID

    # Bocas dos gols (chão pintado): azul em −X, amarelo em +X
    in_goal_y = np.abs(y) < HALF_G
    out[(x < -HALF_L) & (x >= -HALF_L - GOAL_DEPTH - 0.02) & in_goal_y] = COLOR_GOAL_BLUE
    out[(x >  HALF_L) & (x <=  HALF_L + GOAL_DEPTH + 0.02) & in_goal_y] = COLOR_GOAL_YEL

    # Círculo central (linha PRETA) + pontos neutros
    r_c   = np.sqrt(x * x + y * y)
    black = np.abs(r_c - CENTER_CIRCLE_RADIUS) < _BLACK_HALF_THICK
    for sx, sy in NEUTRAL_SPOTS:
        black |= ((x - sx) ** 2 + (y - sy) ** 2) < 0.008 ** 2
    out[black & inside] = COLOR_BLACK_LINE

    # Linhas brancas (borda + áreas de pênalti) — segmentos
    white = np.zeros(n, dtype=bool)
    for (x1, y1), (x2, y2) in FIELD_LINE_SEGMENTS:
        dx, dy = x2 - x1, y2 - y1
        len_sq = dx * dx + dy * dy
        t = np.clip(((x - x1) * dx + (y - y1) * dy) / len_sq, 0.0, 1.0)
        d_sq = (x - (x1 + t * dx)) ** 2 + (y - (y1 + t * dy)) ** 2
        white |= d_sq < LINE_HALF_THICKNESS ** 2
    # Arcos das áreas de pênalti
    for cx, cy, r, a0, a1 in FIELD_LINE_ARCS:
        d   = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        ang = np.arctan2(y - cy, x - cx) % (2 * math.pi)
        s, e = a0 % (2 * math.pi), a1 % (2 * math.pi)
        in_arc = (ang >= s) & (ang <= e) if s < e else (ang >= s) | (ang <= e)
        white |= (np.abs(d - r) < LINE_HALF_THICKNESS) & in_arc
    out[white & inside] = COLOR_LINE

    return out


# ── Ray-cast ──────────────────────────────────────────────────────────────────

def _raycast(origin: np.ndarray, dirs: np.ndarray,
             ball_pos, robots) -> np.ndarray:
    """Cor do primeiro hit de cada raio. origin (3,), dirs (N, 3) norm."""
    n      = dirs.shape[0]
    colors = np.tile(COLOR_VOID, (n, 1))
    t_best = np.full(n, np.inf, dtype=np.float32)

    ox, oy, oz = origin
    dx, dy, dz = dirs[:, 0], dirs[:, 1], dirs[:, 2]

    # 1. Chão (z = 0)
    down = dz < -1e-6
    t_g  = np.where(down, -oz / np.where(down, dz, 1.0), np.inf)
    hit  = t_g < t_best
    if hit.any():
        gx, gy = ox + t_g[hit] * dx[hit], oy + t_g[hit] * dy[hit]
        colors[hit] = field_color(gx, gy)
        t_best[hit] = t_g[hit]

    # 2. Paredes externas (4 planos verticais, altura WALL_HEIGHT)
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
        bound = (HALF_TOTAL_L if axis == 0 else HALF_TOTAL_W) * sign
        o_a   = ox if axis == 0 else oy
        d_a   = dx if axis == 0 else dy
        ok    = np.abs(d_a) > 1e-6
        t_w   = np.where(ok, (bound - o_a) / np.where(ok, d_a, 1.0), np.inf)
        t_w   = np.where(t_w > 1e-6, t_w, np.inf)
        wz    = oz + t_w * dz
        w_o   = (ox + t_w * dx) if axis == 1 else (oy + t_w * dy)
        w_lim = HALF_TOTAL_L if axis == 1 else HALF_TOTAL_W
        valid = (t_w < t_best) & (wz >= 0) & (wz <= WALL_HEIGHT) \
                & (np.abs(w_o) <= w_lim)
        colors[valid] = COLOR_WALL
        t_best[valid] = t_w[valid]

    # 3. Robôs (cilindros verticais)
    for rx, ry, rr, team in robots:
        fx, fy = ox - rx, oy - ry
        a = dx * dx + dy * dy
        b = 2.0 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - rr * rr
        disc = b * b - 4 * a * c
        ok   = (disc > 0) & (a > 1e-9)
        sq   = np.sqrt(np.where(ok, disc, 0.0))
        t_c  = np.where(ok, (-b - sq) / np.where(ok, 2 * a, 1.0), np.inf)
        t_c  = np.where(t_c > 1e-6, t_c, np.inf)
        cz   = oz + t_c * dz
        valid = (t_c < t_best) & (cz >= 0) & (cz <= ROBOT_HEIGHT)
        band  = valid & (cz >= TEAM_BAND_MIN_Z)
        colors[valid] = COLOR_ROBOT
        colors[band]  = COLOR_TEAM.get(team, COLOR_ROBOT)
        t_best[valid] = t_c[valid]

    # 4. Bola (esfera de raio BALL_RADIUS com centro a BALL_RADIUS do chão)
    bx, by = ball_pos
    fx, fy, fz = ox - bx, oy - by, oz - BALL_RADIUS
    b = 2.0 * (fx * dx + fy * dy + fz * dz)
    c = fx * fx + fy * fy + fz * fz - BALL_RADIUS ** 2
    disc = b * b - 4 * c                      # a = 1 (dirs normalizados)
    ok   = disc > 0
    sq   = np.sqrt(np.where(ok, disc, 0.0))
    t_b  = np.where(ok, (-b - sq) / 2.0, np.inf)
    t_b  = np.where(t_b > 1e-6, t_b, np.inf)
    valid = t_b < t_best
    colors[valid] = COLOR_BALL

    return colors


# ── Geradores de raios ────────────────────────────────────────────────────────

def _pinhole_dirs(w, h, fov_deg, yaw) -> np.ndarray:
    half   = math.tan(math.radians(fov_deg) / 2)
    xs     = np.linspace(-half, half, w, dtype=np.float32)
    zs     = np.linspace(half * h / w, -half * h / w, h, dtype=np.float32)
    u, v   = np.meshgrid(xs, zs)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    fwd    = np.array([cos_y, sin_y, 0.0], dtype=np.float32)
    right  = np.array([sin_y, -cos_y, 0.0], dtype=np.float32)
    up     = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    dirs   = (fwd[None, None] + u[..., None] * right[None, None]
              + v[..., None] * up[None, None]).reshape(-1, 3)
    return dirs / np.linalg.norm(dirs, axis=1, keepdims=True)


def _fisheye_dirs(w, h, fov_deg, yaw) -> np.ndarray:
    ys = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    zs = np.linspace(1.0 * h / w, -1.0 * h / w, h, dtype=np.float32)
    u, v = np.meshgrid(ys, zs)
    r    = np.sqrt(u * u + v * v)
    r    = np.where(r < 1e-9, 1e-9, r)
    theta = r * math.radians(fov_deg) / 2          # equidistante: r ∝ θ
    psi   = np.arctan2(v, u)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    fwd    = np.array([cos_y, sin_y, 0.0], dtype=np.float32)
    right  = np.array([sin_y, -cos_y, 0.0], dtype=np.float32)
    up     = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    lateral = (np.cos(psi)[..., None] * right[None, None]
               + np.sin(psi)[..., None] * up[None, None])
    dirs = (np.cos(theta)[..., None] * fwd[None, None]
            + np.sin(theta)[..., None] * lateral).reshape(-1, 3)
    return dirs


def _catadioptric_dirs(w, h, range_m, height_m, yaw) -> np.ndarray:
    """Espelho p/ baixo: anel 360°. Centro da imagem = reto p/ baixo;
    borda = chão a range_m. Topo da imagem = frente do robô."""
    ys = np.linspace(-1.0, 1.0, w, dtype=np.float32)
    zs = np.linspace(1.0, -1.0, h, dtype=np.float32)
    u, v = np.meshgrid(ys, zs)
    r    = np.sqrt(u * u + v * v)
    r    = np.clip(r, 1e-6, 1.0)
    theta_max = math.atan2(range_m, height_m)
    theta = r * theta_max                          # do vertical (0 = p/ baixo)
    # v+ (topo) = frente; u− (esquerda da imagem) = esquerda do robô (CCW+)
    phi   = np.arctan2(-u, v) + yaw
    sin_t = np.sin(theta)
    dirs  = np.stack([sin_t * np.cos(phi),
                      sin_t * np.sin(phi),
                      -np.cos(theta)], axis=-1).reshape(-1, 3)
    return dirs


# ── API principal ─────────────────────────────────────────────────────────────

def render_camera(cfg, robot_x: float, robot_y: float, heading: float,
                  ball_pos: tuple[float, float],
                  robots: list[tuple[float, float, float, str]],
                  rng: np.random.Generator | None = None) -> np.ndarray:
    """Renderiza o frame da câmera. Retorna (H, W, 3) uint8.

    cfg     — CameraConfig (type/width/height/fov/direction/height_m/range/noise_std)
    robots  — [(x, y, raio, team)] dos OUTROS robôs (o próprio fica fora)
    """
    w, h = cfg.width, cfg.height
    yaw  = heading + math.radians(cfg.direction)

    if cfg.type == "pinhole":
        dirs = _pinhole_dirs(w, h, cfg.fov, yaw)
    elif cfg.type == "fisheye":
        dirs = _fisheye_dirs(w, h, cfg.fov, yaw)
    else:  # catadioptric
        dirs = _catadioptric_dirs(w, h, cfg.range, cfg.height_m, heading)

    origin = np.array([robot_x, robot_y, cfg.height_m], dtype=np.float32)
    colors = _raycast(origin, dirs, ball_pos, robots)

    if cfg.noise_std > 0:
        rng = rng or np.random.default_rng()
        colors = colors + rng.normal(0, cfg.noise_std, colors.shape)

    return np.clip(colors, 0, 255).astype(np.uint8).reshape(h, w, 3)
