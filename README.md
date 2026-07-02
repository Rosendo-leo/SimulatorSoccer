# RCJ Soccer Simulator

Simulador desktop para times de **RoboCup Junior Soccer** desenvolverem, testarem e analisarem seus robôs em ambiente virtual. Permite montar um robô via arquivo YAML, importar o código real do time (Python e C++), assistir partidas em 2D top-down e analisar percepts em tempo real.

Desenvolvido por **Leonardo Rosendo**.

---

## Fase atual: Fases 1–3 completas + Fase 4 parcial

Motor de física, percepts, HAL, 2v2, validação de YAML, bridge C++ (pybind11), Robot Builder web e viewer 3D já funcionam. Falta: empacotamento Tauri, replay player e RL.

---

## Pré-requisitos

- Python 3.10+
- Node.js 18+ (só para o frontend web)

```bash
pip install pymunk pygame pyyaml numpy pytest

# Servidor web (builder + viewer 3D)
pip install "fastapi>=0.110" "uvicorn[standard]>=0.29"

# Bridge C++ (opcional — requer MSVC Build Tools no Windows ou g++ no Linux)
pip install pybind11
```

---

## Como rodar

```bash
# Janela pygame — robô azul vs goleiro amarelo
python -m sim --blue robots/striker_v3.yaml --yellow robots/goalkeeper_v2.yaml

# Só o atacante (estratégia padrão)
python -m sim

# Headless — sem janela, para testes rápidos
python -m sim --headless --steps 3600

# Gravar replay
python -m sim --headless --steps 3600 --record replays/partida.jsonl

# Seed fixo para reprodutibilidade
python -m sim --seed 42

# Estratégia customizada
python -m sim --strategy examples.defender_strategy

# 2v2 — dois YAMLs por time (slot 0 = atacante, slot 1 = goleiro)
python -m sim --blue robots/striker_v3.yaml robots/goalkeeper_v2.yaml \
              --yellow robots/striker_omni.yaml robots/goalkeeper_diff.yaml \
              --yellow-strategy examples.defender_strategy

# Estratégia C++ compilada (ver bridge/README.md)
python -m sim --strategy bridge.cpp_attacker
```

### Interface web (builder + viewer 3D)

```bash
# Terminal 1 — servidor (WebSocket + API de robôs)
uvicorn server.main:app --reload --port 8000

# Terminal 2 — frontend React
cd frontend && npm install && npm run dev
# → http://localhost:5173  (abas: Builder | Simulation)
```

### Controles da janela pygame

| Tecla | Ação |
|-------|------|
| `Space` | Pausar / retomar |
| `R` | Reset para kickoff |
| `Q` / `Esc` | Sair |

---

## Estrutura do projeto

```
rcj-soccer-sim/
├── pyproject.toml            # dependências e entry points
│
├── sim/                      # motor de simulação
│   ├── engine.py             # loop principal, física, penalidades, placar
│   ├── field.py              # campo oficial (219×158 cm), paredes, gols, linhas
│   ├── ball.py               # bola PyMunk (raio 43 mm, massa 65 g)
│   ├── robot.py              # corpo PyMunk gerado do YAML
│   ├── percepts.py           # cálculo de sensores com ruído gaussiano
│   ├── hal.py                # interface HAL abstrata (ABC)
│   ├── hal_sim.py            # backend HAL do simulador
│   ├── hal_hardware.py       # stub para hardware real
│   ├── config_loader.py      # parser + validação de YAML (ConfigError)
│   ├── types.py              # dataclasses (RobotPercepts, NoiseConfig, ...)
│   ├── constants.py          # collision categories
│   ├── recorder.py           # gravação de frames para replay (JSON Lines)
│   └── __main__.py           # entry point `python -m sim`
│
├── server/
│   └── main.py               # FastAPI: WebSocket do sim + CRUD de robôs
│
├── frontend/                 # React + Vite
│   └── src/
│       ├── App.jsx           # Robot Builder (formulário + preview SVG)
│       └── components/
│           ├── RobotPreview.jsx
│           └── SimViewer.jsx # viewer 3D (Three.js) via WebSocket
│
├── bridge/                   # estratégias C++ compiladas (pybind11)
│   ├── cpp/hal.hpp           # wrapper C++ do HAL
│   ├── cpp/attacker.cpp      # Decisao::Attacker original em C++
│   └── setup.py              # build: python setup.py build_ext --inplace
│
├── robots/                   # configurações YAML dos robôs
│   ├── example.yaml
│   ├── striker_v3.yaml
│   ├── striker_omni.yaml
│   ├── goalkeeper_v2.yaml
│   └── goalkeeper_diff.yaml
│
├── viewer/
│   └── pygame_viewer.py      # visualizador top-down 2D (debug)
│
├── examples/                 # estratégias de exemplo
│   ├── attacker_strategy.py  # port do Decisao::Attacker (C++)
│   ├── defender_strategy.py  # port do Decisao::Defender (C++)
│   └── simple_strategy.py    # alias para attacker_strategy
│
└── tests/
    ├── test_percepts.py      # sensores: pose conhecida → saída esperada
    ├── test_config_loader.py # parsing dos YAMLs
    ├── test_validation.py    # validação (ConfigError) + 2v2
    ├── test_physics.py       # bola, kicker, engine
    └── test_cpp_bridge.py    # paridade C++ ↔ Python (pulado se não compilado)
```

---

## Campo oficial RoboCup Junior Soccer

| Dimensão | Valor |
|----------|-------|
| Área de jogo | 219 × 158 cm |
| Total com out-area (12 cm) | 243 × 182 cm |
| Largura do gol | 60 cm |
| Profundidade do gol | 74 mm |
| Linha branca | 20 mm |
| Áreas de pênalti | 25 cm × 80 cm (cantos r=15 cm) |
| Círculo central | 60 cm diâmetro — linha **preta** (não ativa sensores) |
| Pontos neutros | 5 pontos pretos (centro + 4 cantos) |

---

## Configuração de robô (YAML)

```yaml
robot:
  name: "Striker v3"
  body:
    shape: circle
    radius: 0.11        # metros
    mass: 1.1           # kg
    max_speed: 1.5      # m/s

  wheels:
    type: omnidirectional
    count: 4
    positions: [45, 135, 225, 315]   # graus

  sensors:
    ir_ring:
      count: 16         # setores
      range: 1.5        # metros
      noise_std: 0.05

    compass:
      noise_std: 2.0    # graus

    ultrassom:
      count: 4
      directions: [0, 90, 180, 270]
      range: 2.0
      noise_std: 0.03

    line_sensors:
      count: 4
      positions:
        - [0.10,  0.0]
        - [-0.10, 0.0]
        - [0.0,   0.10]
        - [0.0,  -0.10]

  kicker:
    force: 5.0          # N·s de impulso (limitado a 4 m/s internamente)
    cooldown: 2.0       # segundos
```

---

## HAL — Hardware Abstraction Layer

O mesmo código de decisão roda no simulador e no robô físico sem modificação:

```python
from sim.hal import HAL

def strategy(hal: HAL) -> None:
    ir    = hal.read_ir()           # [float] × N setores, 0–1
    comp  = hal.read_compass()      # float, radianos
    us    = hal.read_ultrasound()   # [float] × N direções, metros
    lines = hal.read_line_sensors() # [bool] × N sensores
    px, py = hal.read_position()    # (float, float), metros — odometria no hardware

    hal.set_velocity(vx, vy, omega) # m/s local; omega rad/s
    hal.kick()                      # dispara kicker (respeita cooldown)
    hal.stop()                      # atalho: set_velocity(0, 0, 0)
```

**Convenção de eixos (frame local do robô):**
- `vx` positivo → frente
- `vy` positivo → esquerda (strafe)
- `omega` positivo → anti-horário

**Sensores de linha detectam apenas linhas brancas** (borda do campo + áreas de pênalti). O círculo central e os pontos neutros são pretos e **não** ativam os sensores.

---

## Estratégias de exemplo

As estratégias são ports do código C++ original dos robôs físicos do time:

### `examples/attacker_strategy.py`
Port do método `Decisao::Attacker`. Move em direção à bola usando o anel IR com mapeamento de ângulo progressivo; recua ao detectar linha branca via ultrassom.

### `examples/defender_strategy.py`
Port do método `Decisao::Defender`. Goleiro que deriva suavemente para o próprio gol, reverte ao tocar linha branca, e rastreia a bola lateralmente quando dentro da zona central (±16 cm).

---

## Sistema de penalidade

Quando um robô cruza a **linha branca de borda** (sai da área de jogo):

1. É removido do campo por **60 segundos** (configurável em `engine.py` via `PENALTY_DURATION_S`)
2. Ao retornar, é posicionado no **ponto neutro mais distante da bola**
3. A frente do robô fica voltada para o **próprio gol**
4. Gol marcado cancela penalidades pendentes (todos voltam ao kickoff)

---

## Rodando os testes

```bash
python -m pytest tests/ -v
```

65 testes cobrem percepts, parsing e validação de YAML, física (bola/kicker/engine), 2v2 e a paridade da estratégia C++ com o port Python (mesma seed → trajetória idêntica).

---

## Roadmap

| Fase | Status | Descrição |
|------|--------|-----------|
| 1 — Física + percepts + pygame | ✅ Completo | Motor PyMunk, todos os sensores, viewer top-down |
| 2 — HAL layer | ✅ Completo | Interface unificada sim↔hardware, `read_position()` |
| 3 — Robot builder + C++ bridge | ✅ Completo | pybind11, 2v2, validação de YAML, builder web |
| 4 — Frontend 3D + Tauri | ⚠️ Parcial | Viewer 3D + WebSocket ✅ · falta Tauri `.exe` e seleção de robôs na UI |
| 5 — Replay + editor de cenários | 🔲 Pendente | Timeline, drag-and-drop (recorder já grava) |
| 6 — RL headless + versão web | 🔲 Pendente | Gymnasium, SB3, deploy VPS |
