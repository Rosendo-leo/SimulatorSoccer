import math
import pygame
import random
import data

NEUTRAL = [(52, 27),(-52, -27),(-52, 27),(52, -27)]

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

        self.robots = None
        self.goalWall = None
        self.t = 0

    def resize(self, k):
        self.raid *= k

    def reset(self):
        self.x = self.x_i
        self.y = self.y_i

        self.vel_x = 0
        self.vel_y = 0

    def setRobots(self, robots):
        self.robots = robots

    def setGoal(self, goalWall):
        self.goalWall = goalWall

    def goal(self, goals):
        ans = False
        cx = self.x + data.CENTER_W
        cy = self.y + data.CENTER_H
        for rect in goals:
            point_x = max(rect.left, min(cx, rect.right))
            point_y = max(rect.top, min(cy, rect.bottom))
        
            dist = math.sqrt((point_x - cx)**2 + (point_y - cy)**2)
            if dist <= self.raid: ans = True
        return ans

    def isFree(self, x, y):
        ans = True
        for r in self.robots:
            if r.x != self.x and r.y != self.y:
                dist = math.sqrt((x - r.x) ** 2 + (y - r.y) ** 2)
                if dist <= self.raid + r.raid: ans = False

        cx = self.x + data.CENTER_W
        cy = self.y + data.CENTER_H
        for rect in self.goalWall:
            point_x = max(rect.left, min(cx, rect.right))
            point_y = max(rect.top, min(cy, rect.bottom))
        
            dist = math.sqrt((point_x - cx)**2 + (point_y - cy)**2)
            if dist <= self.raid: ans = False
        return ans
    
    def setNeutral(self):
         i = random.randrange(0,3)
         self.x = NEUTRAL[i][0] * data.SCALE
         self.y = NEUTRAL[i][1] * data.SCALE
         self.vel_x = 0
         self.vel_y = 0
    
    def rule(self):
        if(abs(self.x) >= 193 * data.SCALE/2 or abs(self.y) >= 132 * data.SCALE/2):
            self.t += 1
            if(self.t >= 5 * 60):
                self.t = 0
                self.setNeutral()
        else:
            self.t = 0

    def move(self):
        if abs(self.x + self.vel_x) <= 220 * data.SCALE/2 and self.isFree(self.x + self.vel_x, self.y + self.vel_y): self.x += self.vel_x
        else: self.vel_x *= -data.COL_W

        if abs(self.y + self.vel_y) <= 160 * data.SCALE/2 and self.isFree(self.x + self.vel_x, self.y + self.vel_y): self.y += self.vel_y
        else: self.vel_y *= -data.COL_W
    
    def collision(self, robot):
        for other in robot:
            if other.x != self.x and other.y != self.y:
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
