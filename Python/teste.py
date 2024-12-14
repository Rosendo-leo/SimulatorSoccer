import torch

# Lista de tensores
actions = [
    torch.tensor([0.9945, 0.9119, -0.9573]),
    torch.tensor([1.0094, 0.8423, -1.0376]),
    torch.tensor([0.8353, 0.7423, -0.9171])
]

# Concatenar os tensores em um único tensor 1D
action_tensor = torch.cat(actions).long()

print(action_tensor)