"""Top-down 2D pygame viewer for the sim engine."""
from __future__ import annotations
import math
import pygame

from sim.field import (
    FIELD_LENGTH, FIELD_WIDTH,
    TOTAL_LENGTH, TOTAL_WIDTH,
    GOAL_WIDTH, GOAL_DEPTH,
    HALF_L, HALF_W, HALF_G,
    HALF_TOTAL_L, HALF_TOTAL_W,
    CENTER_CIRCLE_RADIUS,
    PENALTY_DEPTH, PENALTY_HALF_Y, PENALTY_CORNER_R,
    NEUTRAL_SPOTS,
)
from sim.ball import BALL_RADIUS
from sim.engine import SimEngine, PENALTY_TICKS, PHYSICS_DT

# ── Colours ──────────────────────────────────────────────────────────────────
C_BG            = ( 20,  20,  20)
C_OUT_AREA      = ( 28,  75,  28)
C_FIELD         = ( 38,  98,  38)
C_LINE_WHITE    = (255, 255, 255)
C_LINE_BLACK    = ( 10,  10,  10)
C_GOAL_BLUE     = ( 50, 100, 220)
C_GOAL_YELLOW   = (220, 190,  30)
C_BALL          = (240,  90,  20)
C_ROBOT_BLUE    = ( 80, 140, 255)
C_ROBOT_YELLOW  = (240, 210,  50)
C_HEADING       = (255, 255, 255)
C_IR_DOT        = (255,  60,  60)
C_TEXT          = (210, 210, 210)
C_SCORE_BG      = ( 15,  15,  15)
C_PAUSED        = (200, 200,  50)
C_PENALTY       = (220,  60,  60)

SCALE  = 290    # pixels per metre
MARGIN =  55    # border around total field


class PygameViewer:
    def __init__(self) -> None:
        pygame.init()
        self._w = int(TOTAL_LENGTH * SCALE) + 2 * MARGIN
        self._h = int(TOTAL_WIDTH  * SCALE) + 2 * MARGIN
        self._screen = pygame.display.set_mode((self._w, self._h))
        pygame.display.set_caption("RCJ Soccer Simulator")
        self._clock   = pygame.time.Clock()
        self._font_sm = pygame.font.SysFont("monospace", 13)
        self._font_md = pygame.font.SysFont("monospace", 20, bold=True)
        self._font_lg = pygame.font.SysFont("monospace", 34, bold=True)

    # ── coordinate helpers ────────────────────────────────────────────────────

    def _p(self, x: float, y: float) -> tuple[int, int]:
        """World metres → screen pixels (Y flipped)."""
        return (
            self._w // 2 + int(x * SCALE),
            self._h // 2 - int(y * SCALE),
        )

    def _r(self, metres: float) -> int:
        return max(1, int(metres * SCALE))

    def _arc_pts(self, cx: float, cy: float, r: float,
                 start: float, end: float, n: int = 24) -> list[tuple[int, int]]:
        """Return screen-pixel polyline approximating a world-coord arc.
        Angles in standard math convention (0=+X, CCW positive, Y-up)."""
        pts = []
        for i in range(n + 1):
            a  = start + (end - start) * i / n
            pts.append(self._p(cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw_field(self) -> None:
        cx, cy = self._w // 2, self._h // 2
        lw     = max(2, self._r(0.020))   # 20 mm white line width

        # Out-area + playing carpet
        tl, tw = self._r(TOTAL_LENGTH), self._r(TOTAL_WIDTH)
        fl, fw = self._r(FIELD_LENGTH),  self._r(FIELD_WIDTH)
        pygame.draw.rect(self._screen, C_OUT_AREA,
                         (cx - tl // 2, cy - tw // 2, tl, tw))
        pygame.draw.rect(self._screen, C_FIELD,
                         (cx - fl // 2, cy - fw // 2, fl, fw))

        # Goal boxes (coloured fill, inside out-area)
        gd = self._r(GOAL_DEPTH)
        gw = self._r(GOAL_WIDTH)
        pygame.draw.rect(self._screen, C_GOAL_BLUE,
                         (cx - fl // 2 - gd, cy - gw // 2, gd, gw))
        pygame.draw.rect(self._screen, C_GOAL_YELLOW,
                         (cx + fl // 2,      cy - gw // 2, gd, gw))

        # White boundary rectangle
        pygame.draw.rect(self._screen, C_LINE_WHITE,
                         (cx - fl // 2, cy - fw // 2, fl, fw), lw)

        # Penalty areas
        self._draw_penalty_area( HALF_L, lw)
        self._draw_penalty_area(-HALF_L, lw)

        # Centre circle — BLACK (referee guide only, not detected by sensors)
        pygame.draw.circle(self._screen, C_LINE_BLACK,
                           self._p(0, 0), self._r(CENTER_CIRCLE_RADIUS), 1)
        pygame.draw.circle(self._screen, C_LINE_BLACK, self._p(0, 0), 3)

        # 5 neutral spots — BLACK 1 cm dots
        for sx, sy in NEUTRAL_SPOTS:
            pygame.draw.circle(self._screen, C_LINE_BLACK,
                               self._p(sx, sy), max(3, self._r(0.005)))

    def _draw_penalty_area(self, goal_x: float, lw: int) -> None:
        """Draw the white penalty area for the goal at goal_x.

        Shape: U opening toward the goal, with two 90° arc corners on the
        front edge (the edge farther from the goal line).

        Geometry for RIGHT goal (goal_x = +HALF_L = +1.095):
          front_x   = goal_x − PENALTY_DEPTH          = +0.845
          arc_cx    = front_x + PENALTY_CORNER_R       = +0.995
          arc_top   = (arc_cx,  ARC_Y) where ARC_Y = PENALTY_HALF_Y − R = 0.25
          arc_bot   = (arc_cx, −ARC_Y)

          top-side  segment : (goal_x, +HALF_Y) → (arc_cx, +HALF_Y)
          top arc   (90°→180°): centre arc_top, radius R
          front seg : (front_x, +ARC_Y) → (front_x, −ARC_Y)
          bot arc   (180°→270°): centre arc_bot, radius R
          bot-side  segment : (arc_cx, −HALF_Y) → (goal_x, −HALF_Y)

        For LEFT goal mirror on X.
        """
        sign     = 1 if goal_x > 0 else -1
        front_x  = goal_x - sign * PENALTY_DEPTH        # ±0.845
        arc_cx   = front_x + sign * PENALTY_CORNER_R    # ±0.995
        arc_y    = PENALTY_HALF_Y - PENALTY_CORNER_R    # 0.25

        # top-side straight segment
        pygame.draw.line(self._screen, C_LINE_WHITE,
                         self._p(goal_x,  PENALTY_HALF_Y),
                         self._p(arc_cx,  PENALTY_HALF_Y), lw)

        # top arc: from top of circle (cy = arc_y, angle 90°) to left/right of circle
        if sign > 0:
            # right goal: 90° → 180° (goes from top → left in math coords)
            pts = self._arc_pts(arc_cx,  arc_y, PENALTY_CORNER_R, math.pi / 2, math.pi)
        else:
            # left goal:  0° → 90°  (goes from right → top in math coords)
            pts = self._arc_pts(arc_cx,  arc_y, PENALTY_CORNER_R, 0, math.pi / 2)
        if len(pts) >= 2:
            pygame.draw.lines(self._screen, C_LINE_WHITE, False, pts, lw)

        # front straight segment
        pygame.draw.line(self._screen, C_LINE_WHITE,
                         self._p(front_x,  arc_y),
                         self._p(front_x, -arc_y), lw)

        # bottom arc
        if sign > 0:
            # right goal: 180° → 270°
            pts = self._arc_pts(arc_cx, -arc_y, PENALTY_CORNER_R, math.pi, 3 * math.pi / 2)
        else:
            # left goal:  270° → 360°
            pts = self._arc_pts(arc_cx, -arc_y, PENALTY_CORNER_R, 3 * math.pi / 2, 2 * math.pi)
        if len(pts) >= 2:
            pygame.draw.lines(self._screen, C_LINE_WHITE, False, pts, lw)

        # bottom-side straight segment
        pygame.draw.line(self._screen, C_LINE_WHITE,
                         self._p(arc_cx, -PENALTY_HALF_Y),
                         self._p(goal_x, -PENALTY_HALF_Y), lw)

    def _draw_ball(self, bx: float, by: float) -> None:
        pygame.draw.circle(self._screen, C_BALL,
                           self._p(bx, by), max(4, self._r(BALL_RADIUS)))

    def _draw_robot(self, rx: float, ry: float, heading: float,
                    radius: float, colour: tuple,
                    ir_ring: list[float] | None) -> None:
        pr     = self._r(radius)
        centre = self._p(rx, ry)

        pygame.draw.circle(self._screen, colour, centre, pr)
        pygame.draw.circle(self._screen, (0, 0, 0), centre, pr, 2)

        # Heading indicator (white line to front)
        hx = rx + math.cos(heading) * radius
        hy = ry + math.sin(heading) * radius
        pygame.draw.line(self._screen, C_HEADING, centre, self._p(hx, hy), 3)

        # IR: show a single orange line toward ball only when signal is strong
        if ir_ring:
            n           = len(ir_ring)
            max_i       = max(range(n), key=lambda i: ir_ring[i])
            max_val     = ir_ring[max_i]
            if max_val > 0.20:   # threshold high enough to ignore noise
                ball_angle = heading + (max_i / n) * 2 * math.pi
                tip_r      = radius + 0.06
                bx2 = rx + math.cos(ball_angle) * tip_r
                by2 = ry + math.sin(ball_angle) * tip_r
                pygame.draw.line(self._screen, C_IR_DOT,
                                 centre, self._p(bx2, by2), 2)

    def _draw_hud(self, state: dict) -> None:
        w, h = self._w, self._h

        # Score bar
        pygame.draw.rect(self._screen, C_SCORE_BG, (0, 0, w, 34))
        blue_t = self._font_md.render(
            f"BLUE  {state['score']['blue']}", True, C_ROBOT_BLUE)
        yel_t  = self._font_md.render(
            f"{state['score']['yellow']}  YELLOW", True, C_ROBOT_YELLOW)
        tick_t = self._font_sm.render(
            f"tick {state['tick']}  t={state['timestamp']:.1f}s", True, C_TEXT)
        self._screen.blit(blue_t, (8, 6))
        self._screen.blit(yel_t,  (w - yel_t.get_width() - 8, 6))
        self._screen.blit(tick_t, (w // 2 - tick_t.get_width() // 2, 9))

        # Pause overlay
        if state.get("_paused"):
            p = self._font_lg.render("PAUSED", True, C_PAUSED)
            self._screen.blit(p, (w // 2 - p.get_width() // 2,
                                  h // 2 - p.get_height() // 2))

        # Goal flash
        gs = state["state"]
        if gs in ("goal_blue", "goal_yellow"):
            col   = C_ROBOT_BLUE if gs == "goal_blue" else C_ROBOT_YELLOW
            label = "GOAL  BLUE!" if gs == "goal_blue" else "GOAL  YELLOW!"
            g = self._font_lg.render(label, True, col)
            self._screen.blit(g, (w // 2 - g.get_width() // 2,
                                  h // 2 - g.get_height() // 2))

        # Per-robot strip (bottom)
        y_base = h - 56
        for i, robot in enumerate(state["robots"]):
            col   = C_ROBOT_BLUE if robot["team"] == "blue" else C_ROBOT_YELLOW
            x_off = 8 + i * 300

            if robot.get("penalized"):
                secs = robot.get("penalty_remaining", 0)
                pen_t = self._font_sm.render(
                    f"{robot['id']}  PENALIZADO  {secs:.0f}s restantes",
                    True, C_PENALTY)
                self._screen.blit(pen_t, (x_off, y_base))
            else:
                hdr = self._font_sm.render(
                    f"{robot['id']}  ({robot['x']:.2f},{robot['y']:.2f})"
                    f"  hdg={math.degrees(robot['heading']):.0f}°",
                    True, col)
                self._screen.blit(hdr, (x_off, y_base))
                us = robot["percepts"].get("ultrasound", [])
                if us:
                    us_t = self._font_sm.render(
                        "US:" + " ".join(f"{v:.2f}" for v in us), True, C_TEXT)
                    self._screen.blit(us_t, (x_off, y_base + 17))

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self, engine: SimEngine, max_steps: int | None = None) -> None:
        running    = True
        steps_done = 0

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif event.key == pygame.K_SPACE:
                        engine.toggle_pause()
                    elif event.key == pygame.K_r:
                        engine._kickoff_reset()

            if not engine.paused:
                state = engine.step()
                steps_done += 1
            else:
                state = engine.get_state()
                state["_paused"] = True

            self._screen.fill(C_BG)
            self._draw_field()

            for robot in state["robots"]:
                if robot.get("penalized"):
                    continue    # robot is off-field; don't render
                col = C_ROBOT_BLUE if robot["team"] == "blue" else C_ROBOT_YELLOW
                self._draw_robot(
                    robot["x"], robot["y"], robot["heading"],
                    radius=0.11,
                    colour=col,
                    ir_ring=robot["percepts"].get("ir_ring"),
                )

            self._draw_ball(state["ball"]["x"], state["ball"]["y"])
            self._draw_hud(state)
            pygame.display.flip()
            self._clock.tick(60)

            if max_steps and steps_done >= max_steps:
                running = False

        pygame.quit()
