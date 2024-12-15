import pygame
import tkinter as tk
import threading
from control import Control
from ball import Ball
from robot import Robot
from field import Field
import data
import math

import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import neural

import matplotlib.pyplot as plt

state_simulator = 0

def open_control():
    root = tk.Tk()
    control = Control(root)
    root.mainloop()

thread = threading.Thread(target=open_control)

pygame.init()
screen = pygame.display.set_mode((data.screen_W, data.screen_H), pygame.RESIZABLE)
aux_layer = pygame.Surface((data.screen_W, data.screen_H))
pygame.display.set_caption("Campo Simulado - Aperture")
clock = pygame.time.Clock()
logo = pygame.image.load("Python/logo.png")
pygame.display.set_icon(logo)

robot = []
robot_b = Robot(-30, 0, 0, 3.3, data.DIA_ROBOT/2, 40, data.ROXO)
robot.append(robot_b)

ball = Ball(0, 0, 3.5, data.DIA_BALL/2, 5, data.LARANJA)
robot.append(ball)

robot_b.setRobots(robot)
ball.setRobots(robot)

field = Field()
field.draw(aux_layer)
goals = [field.goalBlue(), field.goalYellow()]
collisionGoal = [field.goalBlueWall(), field.goalYellowWall()]

robot_b.setGoal(collisionGoal)
ball.setGoalWall(collisionGoal)
ball.setGoal(goals)

#thread.start()

state_dim = 10  # Ex.: x, y, θ, dx, dy, ω
action_dim = 3  # Velocidades x, y, angular
model = neural.ActorCritic(state_dim, action_dim)

running = True
running_neural = True
n = 0
a = []
while running:
    last_W, last_H = data.screen_W, data.screen_H
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen_W, screen_H = event.size
            screen = pygame.display.set_mode((data.screen_W, data.screen_H), pygame.RESIZABLE)

    if not(running_neural):
        teclas = pygame.key.get_pressed()
        vel_x = 0
        vel_y = 0
        vel_ang = 0

        vel = neural.run(robot_b, ball, aux_layer, model)
        robot_b.move(vel[0], vel[1], vel[2])

        ball.move()
        ball.collision(robot)
        ball.rule()
        if ball.goal():
            ball.reset()
            for r in robot: r.reset()

        screen.fill(data.PRETO)
        field.draw(screen)
        
        for r in robot: r.draw(screen)

        pygame.display.flip()
        
    else:
        n += 1
        for r in robot: r.reset()
        result = neural.train(robot_b, ball, aux_layer, model)
        print(n, round(result, 3))
        a.append(result)
        for r in robot: r.reset()
        if n >= 500: 
            running_neural = False
            torch.save(model.state_dict(), "modelo.pth")
            plt.plot(result)
            plt.show()

    clock.tick(60)

pygame.quit()