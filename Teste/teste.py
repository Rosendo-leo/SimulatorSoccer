import gym
from gym import spaces
import numpy as np

class RoboSoccerEnv(gym.Env):
    def __init__(self):
        super(RoboSoccerEnv, self).__init__()
        # Espaço de observação (ex.: posição e velocidade da bola e do robô)
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(8,), dtype=np.float32)
        
        # Espaço de ação (ex.: controle de velocidade e direção)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        self.reset()

    def reset(self):
        # Reinicia o estado do ambiente
        self.state = np.random.uniform(-1, 1, size=(8,))
        return self.state

    def step(self, action):
        # Aplica a ação e calcula o próximo estado
        reward = self._compute_reward(action)
        done = self._is_done()
        self.state = np.random.uniform(-1, 1, size=(8,))
        return self.state, reward, done, {}

    def _compute_reward(self, action):
        # Define a recompensa (exemplo simples)
        return 1.0 if action[0] > 0 else -1.0

    def _is_done(self):
        # Define a condição de término
        return False  # Modifique conforme o problema

    def render(self, mode="human"):
        pass  # Opcional: visualize o ambiente

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

# Crie o ambiente
env = RoboSoccerEnv()

# Crie um ambiente vetorizado (melhora eficiência do treinamento)
vec_env = make_vec_env(lambda: env, n_envs=4)

# Inicialize o modelo PPO
model = PPO("MlpPolicy", vec_env, verbose=1, learning_rate=0.001, gamma=0.99)

# Treine o modelo
model.learn(total_timesteps=100000)

# Salve o modelo
model.save("ppo_robo_soccer")

# Teste o modelo
obs = env.reset()
for _ in range(1000):
    action, _ = model.predict(obs)
    obs, reward, done, info = env.step(action)
    env.render()
