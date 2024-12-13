import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import data

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

def compute_advantages(rewards, values, gamma=0.99, lam=0.95):
    # GAE (Generalized Advantage Estimation)
    advantages = []
    gae = 0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * values[t + 1] - values[t]
        gae = delta + gamma * lam * gae
        advantages.insert(0, gae)
    return advantages

def compute_ppo_loss(policy, old_policy, action, advantage, epsilon=0.2):
    ratio = (policy / old_policy).gather(1, action)
    clipped_ratio = torch.clamp(ratio, 1 - epsilon, 1 + epsilon)
    loss_clip = torch.min(ratio * advantage, clipped_ratio * advantage).mean()
    return -loss_clip

def compute_returns(rewards, gamma=0.99):
    returns = []
    G = 0
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)
    return torch.FloatTensor(returns)

def update_policy(model, optimizer, trajectory, epsilon=0.2):
    states, actions, old_policies, advantages = trajectory
    optimizer.zero_grad()
    policy, value = model(torch.FloatTensor(states))
    loss = compute_ppo_loss(policy, old_policies, actions, advantages, epsilon)
    loss.backward()
    optimizer.step()

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

def calculate(robot, ball, action, aux):
    last = robot.value
    robot.move(action[0], action[1], action[2])
    robot.sensor(ball, aux)
    reward = -0.1
    if abs(robot.x) >= 193 * data.SCALE/2 or abs(robot.y) >= 132 * data.SCALE/2:
        reward -= 10
    if ball.goal():
        done = True
        reward += 100
    else:
        done = False
    now = robot.value
    if last[3] > now[3]: reward += 1
    return  now, reward, done

def run(robot, ball, aux, num_steps=200, gamma=0.99):
    state_dim = 10  # Ex.: x, y, θ, dx, dy, ω
    action_dim = 3  # Velocidades x, y, angular
    model = ActorCritic(state_dim, action_dim)
    optimizer = optim.Adam(model.parameters(), lr=0.0003)
    robot.sensor(ball, aux)
    state = robot.value
    trajectory = {"states": [], "actions": [], "old_policies": [], "rewards": [], "values": []}
    for t in range(num_steps):
        policy, value = model(torch.FloatTensor(state))
        dist = Normal(policy, torch.ones_like(policy) * 0.1)
        action = dist.sample()

        next_state, reward, done = calculate(robot, ball, action, aux)

        trajectory["states"].append(state)
        trajectory["actions"].append(action)
        trajectory["old_policies"].append(policy.detach().numpy())
        trajectory["rewards"].append(reward)
        trajectory["values"].append(value.item())

        state = next_state
        if done: 
            break
        
     # Calcular retornos e vantagens
    trajectory["values"].append(0)  # Valor do estado terminal
    returns = compute_returns(trajectory["rewards"], gamma)
    advantages = compute_advantages(trajectory["rewards"], trajectory["values"], gamma)

    # Transformar os dados para tensores
    states = torch.FloatTensor(trajectory["states"])
    actions = torch.cat(trajectory["actions"])
    actions = actions.long()
    old_policies = torch.FloatTensor(trajectory["old_policies"])
    
    # Atualizar a rede neural
    update_policy(model, optimizer, (states, actions, old_policies, advantages))

    return model