import pygame
import tkinter as tk
import threading
from datetime import timedelta
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
pygame.display.set_caption("Campo Simulado - Aperture")
clock = pygame.time.Clock()

logo = pygame.image.load("Python/logo.png")
pygame.display.set_icon(logo)

robot_b = Robot(-30, 0, 0, 3.3, data.DIA_ROBOT/2, 40, data.AZUL)
robot_r = Robot(30, 0, 180, 3.3, data.DIA_ROBOT/2, 40, data.VERMELHO)
ball = Ball(0, 0, 3.5, data.DIA_BALL/2, 5, data.LARANJA)
field = Field()
# 52   27

thread.start()

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
    robot_b.move(vel_x, vel_y, vel_ang)

    if robot_b.check_collision(robot_r):
        robot_b.velocidade = 0
        robot_r.velocidade = 0

    ball.collision(robot_b)
    ball.collision(robot_r)
    ball.move()

    screen.fill(data.PRETO)
    field.draw(screen)
    robot_b.draw(screen)
    ball.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()