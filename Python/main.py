import pygame
import tkinter as tk
import threading
from control import Control
from ball import Ball
from robot import Robot
from field import Field
import data
import math

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
ball.setGoal(collisionGoal)

#thread.start()

running = True
while running:
    last_W, last_H = data.screen_W, data.screen_H
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen_W, screen_H = event.size
            screen = pygame.display.set_mode((data.screen_W, data.screen_H), pygame.RESIZABLE)

    teclas = pygame.key.get_pressed()
    vel_x = 0
    vel_y = 0
    vel_ang = 0
    
    if teclas[pygame.K_w]:
        vel_y = 0.1
    if teclas[pygame.K_s]:
        vel_y = -0.1
    if teclas[pygame.K_a]:
        vel_x = -0.1
    if teclas[pygame.K_d]:
        vel_x = 0.1
    if teclas[pygame.K_q]:
        vel_ang = -0.1
    if teclas[pygame.K_e]:
        vel_ang = 0.1

    robot_b.sensor(ball, aux_layer)
    robot_b.move(vel_x, vel_y, vel_ang)

    ball.collision(robot)
    ball.move()
    ball.rule()
    if ball.goal(goals):
        ball.reset()
        for r in robot: r.reset()

    screen.fill(data.PRETO)
    field.draw(screen)
    
    for r in robot: r.draw(screen)
    ball.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()