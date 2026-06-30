# CLAUDE.md — Contexto do projeto para Claude Code

## O que é este projeto

Simulador para **RoboCup Junior Soccer** (modalidade autônoma, cada robô tem seu próprio código de decisão). O objetivo é permitir que o time desenvolva e teste estratégias sem precisar do hardware físico.

Não é um fork do grSim (feito para SSL com visão global). É um simulador construído do zero para refletir a arquitetura autônoma do Junior.

---

## Stack técnica

| Componente | Tecnologia |
|---|---|
| Motor de física | Python + PyMunk (Chipmunk2D 2D top-down) |
| Visualizador atual | Pygame (top-down 2D, dev/debug) |
| Visualizador futuro | React + Three.js (3D, Fase 4) |
| Config de robôs | YAML → parser Python |
| HAL interface | Python ABC |
| Bridge C++ (futuro) | pybind11 → `.so`/`.pyd` |
| Shell desktop (futuro) | Tauri 2.0 → `.exe` / `.AppImage` |
| Comunicação (futuro) | WebSocket JSON (FastAPI + uvicorn) |
| RL (futuro) | Gymnasium + Stable-Baselines3 + PettingZoo |

---

## Arquitetura atual (Fase 1 + 2)

```
python -m sim
    └── SimEngine (engine.py)
          ├── PyMunk Space
          │     ├── Field walls + goals (field.py)
          │     ├── Ball body (ball.py)
          │     └── Robot bodies (robot.py)
          ├── Per-robot SimHAL (hal_sim.py)
          │     ├── Percepts: compute_all_percepts() (percepts.py)
          │     └── Actuators: set_velocity(), kick()
          ├── Strategy functions (examples/)
          ├── Penalty system
          └── Recorder (recorder.py)
    └── PygameViewer (viewer/pygame_viewer.py)
```

---

## Dimensões do campo (oficiais RCJ Junior Soccer)

```
Área de jogo:    219 × 158 cm   (FIELD_LENGTH=2.19, FIELD_WIDTH=1.58 em metros)
Com out-area:    243 × 182 cm   (TOTAL_LENGTH=2.43, TOTAL_WIDTH=1.82)
Gol:             60 cm wide × 74 mm deep
Postes:          na linha branca (x = ±HALF_L = ±1.095)
Goal back wall:  x = ±(HALF_L + GOAL_DEPTH) = ±1.169
Outer walls:     x = ±HALF_TOTAL_L = ±1.215, y = ±HALF_TOTAL_W = ±0.91
```

Eixo X = comprimento do campo (gol azul em -X, gol amarelo em +X).  
Eixo Y = largura do campo.

---

## Linhas brancas (ativam line sensors)

- Retângulo da borda da área de jogo (x=±1.095, y=±0.79)
- Áreas de pênalti: 25 cm × 80 cm com cantos r=15 cm, à frente de cada gol

**NÃO são linhas brancas** (linha preta, não ativa sensores):
- Círculo central (raio 0.30 m)
- 5 pontos neutros

---

## Sensores — convenções

| Sensor | Retorno | Convenção |
|---|---|---|
| `read_ir()` | `[float]` 0–1 por setor | Setor 0 = frente, CCW positivo |
| `read_compass()` | `float` rad | 0 = +X world, CCW positivo |
| `read_ultrasound()` | `[float]` metros | Direções do YAML em graus relativos ao heading |
| `read_line_sensors()` | `[bool]` | `[frente, trás, direita, esquerda]` por padrão |
| `read_position()` | `(float, float)` metros | Posição world (x, y) — sim usa PyMunk diretamente |

**Frame local do robô:**
- `vx` positivo = frente
- `vy` positivo = esquerda (strafe)
- `omega` positivo = anti-horário (CCW)

---

## HAL interface

```python
# sim/hal.py — ABC que tanto SimHAL quanto HardwareHAL implementam
class HAL(ABC):
    def read_ir(self) -> List[float]: ...
    def read_compass(self) -> float: ...
    def read_ultrasound(self) -> List[float]: ...
    def read_line_sensors(self) -> List[bool]: ...
    def read_position(self) -> tuple[float, float]: ...  # odometria no hardware
    def set_velocity(self, vx, vy, omega) -> None: ...
    def kick(self) -> None: ...
    def stop(self) -> None: ...  # atalho set_velocity(0,0,0)
```

---

## Como as estratégias funcionam

Cada estratégia é um módulo Python com uma função `strategy(hal: HAL) -> None`.

```python
# examples/attacker_strategy.py — port fiel do Decisao::Attacker (C++ original)
def strategy(hal: HAL) -> None:
    ir    = hal.read_ir()
    lines = hal.read_line_sensors()
    ball_angle, dist = _ir_to_ball(ir)   # graus, 0=frente, +=esq, −=dir
    # ... lógica de mapeamento de ângulo igual ao código C++ ...
    hal.set_velocity(vel_y * SCALE, -vel_x * SCALE, 0.0)
```

**Conversão de coordenadas C++ → HAL:**
```
C++  vel.y (frente)  → HAL  vx = vel_y × escala
C++  vel.x (direita) → HAL  vy = −vel_x × escala  (vy=esquerda = −direita)
```

---

## Problemas conhecidos e soluções aplicadas

### Bola sumindo (tunneling)
**Causa:** Impulso do kicker (`force=5 N·s` na bola de 65g) = 76.9 m/s → percorre 1.28m por frame, atravessando paredes.  
**Solução:** Velocidade máxima da bola capped em 4 m/s após kick (`hal_sim.py:MAX_BALL_SPEED`) + 4 substeps por frame (`engine.py:PHYSICS_SUBSTEPS=4`) + safety net que reseta bola se escapar.

### Robôs passando um pelo outro
**Causa:** Controle por `body.velocity = ...` sobrescreve impulsos de colisão do PyMunk no tick seguinte.  
**Solução:** `_resolve_robot_overlaps()` no engine — após cada step, separa pares de robôs sobrepostos e cancela a componente de velocidade de aproximação.

### Line sensors ativando no círculo central
**Causa:** O círculo central era branco no código original, disparando falsos positivos de linha de borda.  
**Solução:** Círculo central é linha **preta** (só visual), removido de `FIELD_LINE_SEGMENTS`. Sensores de linha só detectam borda + áreas de pênalti.

### Estratégia travando no círculo central
**Causa:** A `simple_strategy` usava sensores de linha para evitar paredes — linha do círculo central disparava avoidance e o robô ficava preso.  
**Solução:** Avoidance de paredes migrado para ultrassom (que não detecta linhas pintadas), sensores de linha usados apenas para informação.

---

## Fluxo do engine por tick

```
1. Refresh percepts de cada robô não-penalizado
2. Executa strategy(hal) → armazena comandos em hal._cmd_*
3. _apply_action(dt) → converte vel local→world, seta body.velocity
4. Aplica damping da bola (×0.992 por frame)
5. space.step(dt/4) × 4  (4 substeps)
6. _resolve_robot_overlaps()  (correção posicional de colisão robô-robô)
7. Detecção de gol → atualiza score + estado
8. Safety net: bola fora dos limites → reset ao centro
9. Detecção out-of-bounds → _penalize(entry)
10. Contagem regressiva de penalidades → _return_from_penalty()
11. get_state() → serializa + grava frame se recorder ativo
```

---

## Configurações importantes

```python
# engine.py
PHYSICS_DT       = 1/60     # timestep fixo
PHYSICS_SUBSTEPS = 4        # substeps por frame
PENALTY_DURATION_S = 60.0   # 1 minuto de penalidade
BALL_DAMPING     = 0.992    # atrito da bola por frame

# hal_sim.py
MAX_BALL_SPEED = 4.0        # m/s máximo após kick

# field.py
LINE_HALF_THICKNESS = 0.010 # 10 mm — tolerância de detecção de linha
```

---

## Próximas fases

### Fase 3 — Robot builder + C++ bridge
- pybind11: código C++ do Arduino compilado como `.so` e chamado pelo engine
- Suporte a 2v2
- Parser YAML avançado com validação

### Fase 4 — Frontend 3D + Tauri
- React + Three.js: campo 3D, robôs com modelo geométrico, bola
- WebSocket server (FastAPI) publicando frames a cada tick
- Empacotamento Tauri → `.exe` Windows + `.AppImage` Linux
- Frontend idêntico na versão web (Vercel + sim no Oracle Cloud VPS)

### Fase 5 — Replay + editor de cenários
- Recorder já implementado (JSON Lines); precisa de player no frontend
- Timeline com seek, play/pause, velocidade variável
- Drag-and-drop para posicionar robôs/bola

### Fase 6 — RL headless
- Wrapper Gymnasium sobre o SimEngine
- Treino com Stable-Baselines3 (PPO)
- PettingZoo para self-play 2v2

---

## Comandos úteis

```bash
# Rodar simulação
python -m sim
python -m sim --blue robots/striker_v3.yaml --yellow robots/goalkeeper_v2.yaml
python -m sim --headless --steps 3600 --seed 42

# Estratégias
python -m sim --strategy examples.attacker_strategy
python -m sim --strategy examples.defender_strategy

# Testes
python -m pytest tests/ -v

# Instalar dependências
pip install pymunk pygame pyyaml numpy pytest
```
