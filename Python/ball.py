import math
import pygame
import data

class Ball:
    def __init__(self, x, y, vel_max, raid, mass, color):
        self.x = x * data.SCALE
        self.y = y * data.SCALE
        self.x_i = self.x
        self.y_i = self.y

        self.raid = raid * data.SCALE
        self.vel_max = vel_max
        self.mass = mass
        self.color = color

        self.vel_x = 0
        self.vel_y = 0

    def resize(self, k):
        self.raid *= k

    def reset(self):
        self.x = self.x_i
        self.y = self.y_i

        self.vel_x = 0
        self.vel_y = 0

    def goal(self):
        if(self.x >= 1539 - data.CENTER_W and self.y >= 320 - data.CENTER_H - 2 * data.SCALE and self.x <= 1539 + 60 - data.CENTER_W and self.y <= 320 + 360 - data.CENTER_H - 4 * data.SCALE):
            return 1
        else:
            return 0

    def move(self):
        if abs(self.x + self.vel_x) <= 220 * data.SCALE/2: self.x += self.vel_x
        else: self.vel_x *= -data.COL_W

        if (abs(self.x + self.vel_x) <= 195 * data.SCALE/2) and not(abs(self.y + self.vel_y) >= 30 * data.SCALE/2) and not(abs(self.y + self.vel_y) <= 28 * data.SCALE/2): self.vel_x *= -data.COL_W

        if abs(self.y + self.vel_y) <= 160 * data.SCALE/2: self.y += self.vel_y
        else: self.vel_y *= -data.COL_W
    
    def collision(self, other):
        dist = math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
        if dist < (self.raid + other.raid):
            if self.vel_max >= self.vel_x: self.vel_x += other.vel_x * math.cos(math.radians(other.ang)) - other.vel_y * math.sin(math.radians(other.ang))
            if self.vel_max >= self.vel_y: self.vel_y += other.vel_x * math.sin(math.radians(other.ang)) + other.vel_y * math.cos(math.radians(other.ang))
        if abs(self.vel_x) >= 0.01: self.vel_x -= data.FAT * math.copysign(1, self.vel_x) * self.mass
        if abs(self.vel_y) >= 0.01: self.vel_y -= data.FAT * math.copysign(1, self.vel_y) * self.mass

    def draw(self, screen):
        x = self.x + data.CENTER_W
        y = self.y + data.CENTER_H
        pygame.draw.circle(screen, self.color, (int(x), int(y)), self.raid)
