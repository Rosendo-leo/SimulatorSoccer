import math
import pygame
import data

def maps(x, in_min, in_max, out_min, out_max):
	return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;

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

        self.value = None
        self.robots = None
        self.goal = None

    def resize(self, k):
        self.vel_max *= k
        self.raid *= k

    def sensor(self, ball):
        delta_x = ball.x - self.x
        delta_y = ball.y - self.y
        angBall = math.degrees(math.atan2(delta_y, delta_x))

        self.value = [self.y/data.SCALE, self.x/data.SCALE, math.sqrt((self.x - ball.x) ** 2 + (self.y - ball.y) ** 2), angBall]

    def reset(self):
        self.x = self.x_i
        self.y = self.y_i
        self.ang = 0
        self.ang_rel = self.ang_i

        self.vel_x = 0
        self.vel_y = 0

    def setRobots(self, robots):
        self.robots = robots

    def setGoal(self, goal):
        self.goal = goal

    def attack(self):
        dist = 1
        ball_angle = self.value[3]
        angle = self.ang
        power = 100
        Mov_Angle = abs(ball_angle)
        if Mov_Angle < 10:
            Mov_Angle = 0
        elif Mov_Angle <= 60:
            Mov_Angle = maps(Mov_Angle, 40, 80, 50, 90)
        elif Mov_Angle <= 90:
            Mov_Angle = maps(Mov_Angle, 70, 100, 80, 130)
        elif Mov_Angle <= 130:
            Mov_Angle = maps(Mov_Angle, 95, 140, 120, 160)
        elif Mov_Angle <= 180:
            Mov_Angle = maps(Mov_Angle, 130, 180, 155, 270)
        if angle <= 0: Mov_Angle *= -1
        x = -int(math.sin((Mov_Angle * math.pi / 180.0))  * power * dist)
        y = -int(math.cos((Mov_Angle * math.pi / 180.0))  * power * dist)
        x = maps(x, -100, 100, -self.vel_max, self.vel_max)
        y = maps(y, -100, 100, -self.vel_max, self.vel_max)
        self.move(y ,x ,0)

    def isFree(self, x, y):
        ans = True
        for r in self.robots:
            if r.x != self.x and r.y != self.y:
                dist = math.sqrt((x - r.x) ** 2 + (y - r.y) ** 2)
                if dist + 2 <= self.raid + r.raid: ans = False
        cx = x + data.CENTER_W
        cy = y + data.CENTER_H
        for rect in self.goal:
            point_x = max(rect.left, min(cx, rect.right))
            point_y = max(rect.top, min(cy, rect.bottom))
        
            dist = math.sqrt((point_x - cx)**2 + (point_y - cy)**2)
            if dist <= self.raid: ans = False
        return ans

    def move(self, vel_y, vel_x, vel_ang):
        if(self.vel_max >= abs(self.vel_x + vel_x * data.ACC_P)): self.vel_x += vel_x * data.ACC_P
        if(self.vel_max >= abs(self.vel_y + vel_y * data.ACC_P)): self.vel_y += vel_y * data.ACC_P
        if(self.vel_max >= abs(self.vel_ang + vel_ang * data.ACC_A)): self.vel_ang += vel_ang * data.ACC_A

        self.ang += self.vel_ang
        self.ang_rel += self.vel_ang
        x = self.vel_x * math.cos(math.radians(self.ang)) - self.vel_y * math.sin(math.radians(self.ang)) + self.x
        y = self.vel_x * math.sin(math.radians(self.ang)) + self.vel_y * math.cos(math.radians(self.ang)) + self.y
        if max(abs(x + self.raid), abs(x - self.raid)) <= 223 * data.SCALE/2 and self.isFree(x,y): self.x = x
        if max(abs(y + self.raid), abs(y - self.raid)) <= 162 * data.SCALE/2 and self.isFree(x,y): self.y = y

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