# Bridge C++ (pybind11)

Roda o código C++ do robô (firmware Arduino) **sem modificação de lógica** dentro do simulador. A mesma função de decisão que roda no hardware é compilada como extensão Python (`.pyd`/`.so`) e chamada pelo engine a cada tick.

## Pré-requisitos

- **Windows:** Visual Studio Build Tools 2022 (workload "Desktop development with C++")
- **Linux:** `g++` >= 9
- `pip install pybind11`

## Compilar

```bash
cd bridge
python setup.py build_ext --inplace
```

Gera `cpp_attacker.<abi>.pyd` nesta pasta, importável como `bridge.cpp_attacker`.

## Usar

```bash
# C++ attacker (azul) vs Python defender (amarelo)
python -m sim --blue robots/striker_v3.yaml --yellow robots/goalkeeper_v2.yaml \
    --strategy bridge.cpp_attacker --yellow-strategy examples.defender_strategy
```

## Portar seu próprio código

1. Copie a lógica de decisão do firmware para um novo `.cpp` em `cpp/`
2. Troque as chamadas de hardware pelos métodos de `rcj::HAL` (`hal.hpp`):

| Firmware (exemplo) | Bridge |
|---|---|
| ler ADC dos fototransistores | `hal.read_ir()` → `vector<double>` 0–1 |
| ler magnetômetro I2C | `hal.read_compass()` → rad |
| ler HC-SR04 | `hal.read_ultrasound()` → metros |
| ler sensores de linha | `hal.read_line_sensors()` → `vector<bool>` |
| PWM dos motores | `hal.set_velocity(vx, vy, omega)` |
| solenoide do kicker | `hal.kick()` |

3. Exponha a função no final do arquivo:

```cpp
PYBIND11_MODULE(minha_estrategia, m) {
    m.def("strategy", [](py::object py_hal) {
        rcj::HAL hal(std::move(py_hal));
        minha_funcao_de_decisao(hal);
    });
}
```

4. Adicione o módulo em `setup.py` (`ext_modules`) e recompile.

## Convenções (iguais ao HAL Python)

- `vx` positivo = frente, `vy` positivo = esquerda, `omega` positivo = anti-horário
- Ângulos em radianos, 0 = +X do mundo
- IR: setor 0 = frente, CCW positivo

## Teste de paridade

`tests/test_cpp_bridge.py` verifica que `bridge.cpp_attacker` produz trajetória **idêntica** à do port Python (`examples/attacker_strategy.py`) com o mesmo seed — qualquer divergência entre os dois ports falha o teste. O teste é pulado automaticamente se a extensão não estiver compilada.
