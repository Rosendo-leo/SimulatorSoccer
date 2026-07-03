# Design — Câmera simulada (B1)

> Status: proposta (não implementado). Pré-requisito para portar código real
> de Vision (Aperture Open, XLC, MegaHertz dependem de imagem de câmera).

## Objetivo

Expor `hal.read_camera_frame() -> np.ndarray (H, W, 3) uint8` para que o
código de decisão do time rode pipelines reais de detecção (blob por cor,
CNN leve) dentro do simulador — e o mesmo código funcione no robô físico.

## Requisito central: headless

O render NÃO pode depender do viewer Three.js: precisa funcionar em
`--headless`, no treino de RL (milhares de frames/s agregados) e no CI.
Logo: **rasterização própria em numpy no lado Python**, não WebGL.

Isso é viável porque a cena RCJ é geometricamente trivial: plano verde,
linhas brancas, bola laranja, gols coloridos, robôs pretos — cores chapadas,
sem texturas nem iluminação. Um rasterizador "flat" de ~200 linhas resolve.

## Modelos de câmera (3 perfis do YAML)

```yaml
sensors:
  camera:
    type: catadioptric      # pinhole | fisheye | catadioptric
    width: 160              # OpenMV QQVGA-ish; manter BAIXO por performance
    height: 120
    fov: 60                 # pinhole: FOV horizontal (graus)
    direction: 0            # pinhole: direção relativa ao heading
    height_m: 0.25          # altura da lente/espelho acima do chão
    noise_std: 4.0          # ruído gaussiano por canal (0-255)
```

1. **pinhole** — projeção perspectiva clássica; times usam ×4 (frente/trás/
   lados). Ray-cast por coluna de pixels contra o plano do chão + cilindros
   (robôs) + esfera (bola).
2. **fisheye** — equidistante (r = f·θ); mesma malha de raios, mapeamento
   diferente.
3. **catadioptric** — espelho cônico/hiperbólico apontado para baixo
   (Aperture): vista 360° anelar do chão. É o mais fácil de rasterizar:
   cada pixel (r, φ) da imagem anelar mapeia para um ponto do chão a
   distância d(r) — basta amostrar a "textura procedural" do campo.

## Rasterização (comum aos 3)

Para cada pixel, um raio → primeira interseção entre:
- chão (z=0): cor = função procedural `field_color(x, y)` (verde, linha
  branca se perto de FIELD_LINE_SEGMENTS/ARCS, preto no círculo central…);
- bola: esfera (centro, r=0.043) → laranja;
- robôs: cilindros (centro, raio, altura 0.22) → preto + faixa da cor do time;
- gols/paredes: caixas → azul/amarelo/preto.

Tudo vetorizável em numpy (grade de raios de uma vez, sem loop por pixel).
Sem sombras/iluminação na v1; `noise_std` + jitter de exposição dão o
realismo mínimo p/ threshold de cor não ficar trivial.

## Performance (estimativas a validar)

- 160×120 = 19,2k raios; numpy vetorizado ≈ 1–3 ms/frame → ~60 fps por robô.
- RL: câmera só em `obs_mode="camera"`; frame_skip=4 e resolução 80×60
  reduzem o custo. Treino em massa continua possível no perfil vector.
- Cache: geometria estática do chão pré-computada por tipo de câmera
  (lookup table pixel→(x,y) do chão para catadioptric/fisheye fixas).

## Integração

- `sim/camera.py` — rasterizador puro (testável sem engine).
- `CameraConfig` no config_loader + `compute_camera` nos percepts (caro:
  computar LAZY — só quando `read_camera_frame()` é chamado no tick, não
  em `compute_all_percepts`).
- HAL: `read_camera_frame()` opcional (NotImplementedError sem o bloco).
- Viewer: opcional PiP mostrando o frame da câmera do robô selecionado
  (enviar como JPEG base64 sob demanda via WS, nunca no stream de 60 Hz).
- RL: `obs_mode="camera"` → Box(0, 255, (H, W, 3), uint8) + CnnPolicy.

## Fases

1. `sim/camera.py` catadioptric + testes de cor/geometria (é o modo mais
   usado nos TDPs e o mais simples).
2. pinhole + fisheye reutilizando o mesmo sampler.
3. HAL + YAML + exemplo `examples/vision_strategy.py` (blob laranja → bola).
4. PiP no viewer; `obs_mode="camera"` no RL por último.

## Questões em aberto

- Ligação com a decisão PyBullet (spike pendente): se um dia a física for
  3D, robôs deixam de ser cilindros perfeitos — o rasterizador continua
  válido usando os convex hulls como cilindros equivalentes (aproximação).
- Liga Vision valida `ir_ring` hoje como stand-in da bola; quando a câmera
  existir, decidir se `league: vision` passa a EXIGIR camera e proibir
  ir_ring (breaking change nos YAMLs — avisar antes).
