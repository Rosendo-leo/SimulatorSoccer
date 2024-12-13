import torch
import torch.nn as nn
import torch.optim as optim

class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(ActorCritic, self).__init__()
        # Camadas compartilhadas
        self.shared = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
        )
        # Rede de política (ação)
        self.policy = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),
            nn.Tanh()
        )
        self.value = nn.Sequential(
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

    def forward(self, state):
        x = self.shared(state)
        return self.policy(x), self.value(x)
    
from torch.distributions import Normal

def compute_advantages(rewards, values, gamma=0.99, lam=0.95):
    # GAE (Generalized Advantage Estimation)
    advantages = []
    gae = 0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * values[t + 1] - values[t]
        gae = delta + gamma * lam * gae
        advantages.insert(0, gae)
    return advantages

def ppo_update(trajectory, model, optimizer, clip_param=0.2, epochs=10):
    states, actions, rewards, old_probs, values = trajectory

    for _ in range(epochs):
        policy, new_values = model(states)
        dist = Normal(policy, torch.ones_like(policy) * 0.1)
        new_probs = dist.log_prob(actions).sum(dim=1)

        # Razão de probabilidades
        ratio = torch.exp(new_probs - old_probs)

        # Loss de PPO
        advantages = torch.tensor(compute_advantages(rewards, values))
        surr1 = ratio * advantages
        surr2 = torch.clamp(ratio, 1 - clip_param, 1 + clip_param) * advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        # Loss de valor
        value_loss = nn.MSELoss()(new_values, torch.tensor(rewards))

        # Loss total
        loss = policy_loss + 0.5 * value_loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

state_dim = 6  # Ex.: x, y, θ, dx, dy, ω
action_dim = 3  # Velocidades x, y, angular

model = ActorCritic(state_dim, action_dim)
optimizer = optim.Adam(model.parameters(), lr=0.0003)
