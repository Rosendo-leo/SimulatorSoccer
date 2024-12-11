import math
import pygame
import data

class Robot():
    def __init__(self, x, y, ang, vel_max, raid, mass, color):
        self.x = x * data.SCALE
        self.y = y * data.SCALE
        self.x_i = self.x
        self.y_i = self.y

        self.ang_rel = ang
        self.ang_i = self.ang_rel
        self.vel_max = vel_max
        self.raid = raid * data.SCALE
        self.mass = mass
        self.color = color

        self.ang = 0
        self.vel_x = 0
        self.vel_y = 0
        self.vel_ang = 0

    def resize(self, k):
        self.vel_max *= k
        self.raid *= k

    def reset(self):
        self.x = self.x_i
        self.y = self.y_i
        self.ang = 0
        self.ang_rel = self.ang_i

        self.vel_x = 0
        self.vel_y = 0

    def move(self, vel_y, vel_x, vel_ang):
        if(self.vel_max >= abs(self.vel_x + vel_x * data.ACC_P)): self.vel_x += vel_x * data.ACC_P
        if(self.vel_max >= abs(self.vel_y + vel_y * data.ACC_P)): self.vel_y += vel_y * data.ACC_P
        if(self.vel_max >= abs(self.vel_ang + vel_ang * data.ACC_A)): self.vel_ang += vel_ang * data.ACC_A

        self.ang += self.vel_ang
        self.ang_rel += self.vel_ang
        x = self.vel_x * math.cos(math.radians(self.ang)) - self.vel_y * math.sin(math.radians(self.ang))
        y = self.vel_x * math.sin(math.radians(self.ang)) + self.vel_y * math.cos(math.radians(self.ang))
        if max(abs(x + self.raid + self.x), abs(x - self.raid + self.x)) <= 223 * data.SCALE/2: self.x += self.vel_x * math.cos(math.radians(self.ang)) - self.vel_y * math.sin(math.radians(self.ang))
        if max(abs(y + self.raid + self.y), abs(y - self.raid + self.y)) <= 162 * data.SCALE/2: self.y += self.vel_x * math.sin(math.radians(self.ang)) + self.vel_y * math.cos(math.radians(self.ang))

        if abs(self.vel_x) >= 0.01: self.vel_x -=  data.FAT * math.copysign(1, self.vel_x) * self.mass
        if abs(self.vel_y) >= 0.01: self.vel_y -= data.FAT * math.copysign(1, self.vel_y) * self.mass
        if abs(self.vel_ang) >= 0.01: self.vel_ang -= data.FAT * math.copysign(1, self.vel_ang) * self.mass
    
    def check_collision(self, other):
        dist = math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        return dist < (self.raid + other.raid)
    
    def draw(self, screen):
        x = self.x + data.CENTER_W
        y = self.y + data.CENTER_H
        pygame.draw.circle(screen, self.color, (int(x), int(y)), self.raid)
        ponta_x = x + self.raid * math.cos(math.radians(self.ang_rel))
        ponta_y = y + self.raid * math.sin(math.radians(self.ang_rel))
        pygame.draw.line(screen, data.BRANCO, (x, y), (ponta_x, ponta_y), 2)