import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import data

reward = 0
best_reward = 0
mod=None

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
    advantages = torch.zeros(len(rewards))
    gae = 0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma * values[t + 1] - values[t]
        gae = delta + gamma * lam * gae
        advantages[t] = gae
    return advantages

def compute_ppo_loss(policy, old_policy, actions, advantages, epsilon=0.2):
    # Certificar-se de que as ações estão normalizadas
    actions = ((actions + 1) / 2 * (policy.size(1) - 1)).long().view(-1, 1)

    # Validar as dimensões
    if actions.size(0) != policy.size(0):
        actions = actions[:policy.size(0)]

    # Garantir que os índices estão no intervalo válido
    if actions.min() < 0 or actions.max() >= policy.size(1):
        raise ValueError(f"Invalid action index: {actions.min().item()} to {actions.max().item()}, "
                         f"but policy supports indices in [0, {policy.size(1) - 1}]")

    # Cálculo da razão de probabilidade
    ratio = (policy / old_policy).gather(1, actions)
    clipped_ratio = torch.clamp(ratio, 1 - epsilon, 1 + epsilon)
    loss_clip = torch.min(ratio * advantages, clipped_ratio * advantages).mean()
    return -loss_clip

def compute_returns(rewards, gamma=0.99):
    returns = torch.zeros(len(rewards))
    G = 0
    for t in reversed(range(len(rewards))):
        G = rewards[t] + gamma * G
        returns[t] = G
    return returns

def update_policy(model, optimizer, trajectory, epsilon=0.2):
    states, actions, old_policies, advantages = trajectory
    optimizer.zero_grad()
    policy_logits, _ = model(states)

    # Converter logits em probabilidades
    if policy_logits.dim() == 1:
        policy = torch.softmax(policy_logits, dim=0)
    else:
        policy = torch.softmax(policy_logits, dim=1)

    loss = compute_ppo_loss(policy, old_policies, actions, advantages, epsilon)
    loss.backward()
    optimizer.step()

def calculate(robot, ball, action, aux):
    global reward

    #bx_y=(ball.x,ball.y)
    robot.move(action[0], action[1], action[2])
    #if (ball.x,ball.y)==bx_y:reward-=20
    robot.sensor(ball, aux)
    
    if abs(robot.x) >= 193 * data.SCALE / 2 or abs(robot.y) >= 132 * data.SCALE / 2:
        reward -= 10
    if ball.goal():
        done = True
        reward += 200_000_000
    else:
        done = False
    now = robot.value

    reward += 30//now[3]
    return now, reward, done

def train(robot, ball, aux, model, num_steps=800, gamma=0.99):
    global reward
    global best_reward
    global mod

    reward=0
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    robot.sensor(ball, aux)
    state = robot.value
    trajectory = {"states": [], "actions": [], "old_policies": [], "rewards": [], "values": []}

    for t in range(num_steps):
        policy_logits, value = model(torch.FloatTensor(state))

        # Garantir formato correto das probabilidades
        if policy_logits.dim() == 1:
            policy = torch.softmax(policy_logits, dim=0)
        else:
            policy = torch.softmax(policy_logits, dim=1)

        dist = Normal(policy, torch.ones_like(policy) * 0.1)
        action = dist.sample()

        next_state, reward, done = calculate(robot, ball, action, aux)

        trajectory["states"].append(state)
        trajectory["actions"].append(action)
        trajectory["old_policies"].append(policy.detach())
        trajectory["rewards"].append(reward)
        trajectory["values"].append(value.item())

        state = next_state
        if done:
            break
    
    rew=sum(trajectory["rewards"])

    if rew>best_reward or mod==None:
        best_reward=rew
        mod=model

    # Calcular retornos e vantagens
    trajectory["values"].append(0)  # Valor do estado terminal
    returns = compute_returns(trajectory["rewards"], gamma)
    advantages = compute_advantages(trajectory["rewards"], trajectory["values"], gamma)

    # Transformar os dados para tensores
    states = torch.FloatTensor(trajectory["states"])
    actions = torch.stack(trajectory["actions"])
    old_policies = torch.stack(trajectory["old_policies"])

    # Atualizar a rede neural
    update_policy(model, optimizer, (states, actions, old_policies, advantages))

    return rew, mod, best_reward

def run(robot, ball, aux, model):
    robot.sensor(ball, aux)
    state = robot.value

    policy_logits, _ = model(torch.FloatTensor(state))

    # Garantir formato correto das probabilidades
    if policy_logits.dim() == 1:
        policy = torch.softmax(policy_logits, dim=0)
    else:
        policy = torch.softmax(policy_logits, dim=1)

    dist = Normal(policy, torch.ones_like(policy) * 0.1)
    action = dist.sample()

    return action