import pygame
import tkinter as tk
import threading
import math

def open_control():
    root = tk.Tk()
    root.title("Controle Simulador")

    icone = tk.PhotoImage(file="Python/logo.png")
    root.iconphoto(True, icone)

    label = tk.Label(root, text="Sim")
    label.pack(pady=10)

    button = tk.Button(root, text="Fechar", command=root.destroy)
    button.pack(pady=10)

    root.mainloop()

thread = threading.Thread(target=open_control)

COL_P = 0.8

class Ball:
    def __init__(self, x, y, vel_max, raid, mass, color):
        self.x = x
        self.y = y
        self.raid = raid
        self.vel_max = vel_max
        self.mass = mass
        self.color = color

        self.vel_x = 0
        self.vel_y = 0

    def resize(self, k):
        self.raid *= k

    def move(self):
        self.x += self.vel_x
        self.y += self.vel_y
    
    def collision(self, other):
        dist = math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        if dist < (self.raid + other.raid):
            if self.vel_max >= self.vel_x: self.vel_x += other.vel_x * math.cos(math.radians(other.ang)) - other.vel_y * math.sin(math.radians(other.ang))
            if self.vel_max >= self.vel_y: self.vel_y += other.vel_x * math.sin(math.radians(other.ang)) + other.vel_y * math.cos(math.radians(other.ang))
        if abs(self.vel_x) >= 0.01: self.vel_x -= FAT * math.copysign(1, self.vel_x) * self.mass
        if abs(self.vel_y) >= 0.01: self.vel_y -= FAT * math.copysign(1, self.vel_y) * self.mass

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.raid)

ACC_P = 0.7
ACC_A = 0.8
FAT = 0.001

class Robot:
    def __init__(self, x, y, ang, vel_max, raid, mass, color):
        self.x = x
        self.y = y
        self.ang_rel = ang
        self.vel_max = vel_max
        self.raid = raid
        self.mass = mass
        self.color = color

        self.ang = 0
        self.vel_x = 0
        self.vel_y = 0
        self.vel_ang = 0

    def resize(self, k):
        self.vel_max *= k
        self.raid *= k

    def move(self, vel_x, vel_y, vel_ang):
        if(self.vel_max >= abs(self.vel_x + vel_x * ACC_P)): self.vel_x += vel_x * ACC_P
        if(self.vel_max >= abs(self.vel_y + vel_y * ACC_P)): self.vel_y += vel_y * ACC_P
        if(self.vel_max >= abs(self.vel_ang + vel_ang * ACC_P)): self.vel_ang += vel_ang * ACC_A

        self.ang += self.vel_ang
        self.ang_rel += self.vel_ang
        self.x += self.vel_x * math.cos(math.radians(self.ang)) - self.vel_y * math.sin(math.radians(self.ang))
        self.y += self.vel_x * math.sin(math.radians(self.ang)) + self.vel_y * math.cos(math.radians(self.ang))

        if abs(self.vel_x) >= 0.01: self.vel_x -=  FAT * math.copysign(1, self.vel_x) * self.mass
        if abs(self.vel_y) >= 0.01: self.vel_y -= FAT * math.copysign(1, self.vel_y) * self.mass
        if abs(self.vel_ang) >= 0.01: self.vel_ang -= FAT * math.copysign(1, self.vel_ang) * self.mass
    
    def check_collision(self, other):
        dist = math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        return dist < (self.raid + other.raid)
    
    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.raid)
        ponta_x = self.x + self.raid * math.cos(math.radians(self.ang_rel))
        ponta_y = self.y + self.raid * math.sin(math.radians(self.ang_rel))
        pygame.draw.line(screen, BRANCO, (self.x, self.y), (ponta_x, ponta_y), 2)

VERDE = (0, 128, 0)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
AZUL = (0, 0, 255)
VERMELHO = (255, 0, 0)
LARANJA = (255, 127, 0)
CINZA = (50, 50, 50)
AMARELO = (255, 255, 0)

SCALE = 6

DIA_ROBOT = 18
DIA_BALL =  4.3

screen_W = 1920
screen_H = 1000

CENTER_H = screen_H/2
CENTER_W = screen_W/2

PLAY_FIELD_WIDTH = 193 * SCALE
PLAY_FIELD_HEIGHT = 132 * SCALE
TOTAL_FIELD_WIDTH = 223 * SCALE
TOTAL_FIELD_HEIGHT = 162 * SCALE 
OUTER_AREA_WIDTH = 15 * SCALE + (CENTER_W - TOTAL_FIELD_WIDTH/2)
OUTER_AREA_HEIGHT = 15 * SCALE + (CENTER_H - TOTAL_FIELD_HEIGHT/2)
WALL_HEIGHT = 22 * SCALE
GOAL_WIDTH = 60 * SCALE 
GOAL_DEPTH = 10 * SCALE
GOAL_ARC_RADIUS = 23 * SCALE
CENTER_CIRCLE_RADIUS = 30 * SCALE
NEUTRAL_SPOT_RADIUS = 1 * SCALE // 2

def draw_field(screen, scale):
    pygame.draw.rect(screen, VERDE, (
            (CENTER_W - TOTAL_FIELD_WIDTH/2),
            (CENTER_H - TOTAL_FIELD_HEIGHT/2),
            TOTAL_FIELD_WIDTH,
            TOTAL_FIELD_HEIGHT
        ))
    
    pygame.draw.rect(screen, BRANCO, (
            OUTER_AREA_WIDTH,
            OUTER_AREA_HEIGHT,
            PLAY_FIELD_WIDTH,
            PLAY_FIELD_HEIGHT
        ), 1 * SCALE)
    
    pygame.draw.circle(screen, PRETO, (
            OUTER_AREA_WIDTH + PLAY_FIELD_WIDTH // 2,
            OUTER_AREA_HEIGHT + PLAY_FIELD_HEIGHT // 2
        ), CENTER_CIRCLE_RADIUS, 1 * SCALE)
    
    pygame.draw.rect(screen, AZUL, (
            OUTER_AREA_WIDTH + PLAY_FIELD_WIDTH,
            OUTER_AREA_HEIGHT + (PLAY_FIELD_HEIGHT - GOAL_WIDTH) // 2,
            GOAL_DEPTH,
            GOAL_WIDTH
        ))
    
    pygame.draw.rect(screen, AMARELO, (
            OUTER_AREA_WIDTH - GOAL_DEPTH,
            OUTER_AREA_HEIGHT + (PLAY_FIELD_HEIGHT - GOAL_WIDTH) // 2,
            GOAL_DEPTH,
            GOAL_WIDTH
        ))

    # Pontos neutros
    neutral_spots = [
        (
            OUTER_AREA_WIDTH + PLAY_FIELD_WIDTH // 2,
            OUTER_AREA_HEIGHT + PLAY_FIELD_HEIGHT // 2
        ),  # Centro
        (
            OUTER_AREA_WIDTH + 45 * SCALE,
            OUTER_AREA_HEIGHT + 45 * SCALE
        ),  # Canto superior esquerdo
        (
            OUTER_AREA_WIDTH + PLAY_FIELD_WIDTH - 45 * SCALE,
            OUTER_AREA_HEIGHT + 45 * SCALE
        ),  # Canto superior direito
        (
            OUTER_AREA_WIDTH + 45 * SCALE,
            OUTER_AREA_HEIGHT + PLAY_FIELD_HEIGHT - 45 * SCALE
        ),  # Canto inferior esquerdo
        (
            OUTER_AREA_WIDTH + PLAY_FIELD_WIDTH - 45 * SCALE,
            OUTER_AREA_HEIGHT + PLAY_FIELD_HEIGHT - 45 * SCALE
        )  # Canto inferior direito
    ]

    for spot in neutral_spots:
        pygame.draw.circle(screen, PRETO, spot, NEUTRAL_SPOT_RADIUS)

proporcao_raio_robo = 0.02
proporcao_velocidade = 0.005

pygame.init()
screen = pygame.display.set_mode((screen_W, screen_H), pygame.RESIZABLE)
pygame.display.set_caption("Simulador Soccer RoboCup Junior - Aperture")
clock = pygame.time.Clock()

logo = pygame.image.load("Python/logo.png")
pygame.display.set_icon(logo)

robot_b = Robot(200, 300, 0, 3, DIA_ROBOT/2 * SCALE, 40, AZUL)
robot_r = Robot(600, 300, 180, 3, DIA_ROBOT/2 * SCALE, 40, VERMELHO)
ball = Ball(400, 300, 3.5, DIA_BALL/2 * SCALE, 5, LARANJA)

#thread.start()

running = True
while running:
    last_W, last_H = screen_W, screen_H
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen_W, screen_H = event.size
            screen = pygame.display.set_mode((screen_W, screen_H), pygame.RESIZABLE)

    teclas = pygame.key.get_pressed()
    vel_x = 0
    vel_y = 0
    vel_ang = 0
    if teclas[pygame.K_w]:
        vel_x = 0.1
    if teclas[pygame.K_s]:
        vel_x = -0.1
    if teclas[pygame.K_a]:
        vel_y = -0.1
    if teclas[pygame.K_d]:
        vel_y = 0.1
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

    screen.fill(PRETO)
    draw_field(screen, 0)
    robot_b.draw(screen)
    robot_r.draw(screen)
    ball.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()