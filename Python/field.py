import data
import pygame

class Field:
    def __init__(self):
        self.col = 0
    
    def draw(self, screen):
        pygame.draw.rect(screen, data.VERDE, (
                (data.CENTER_W - data.TOTAL_FIELD_WIDTH/2),
                (data.CENTER_H - data.TOTAL_FIELD_HEIGHT/2),
                data.TOTAL_FIELD_WIDTH,
                data.TOTAL_FIELD_HEIGHT
            ))
        
        pygame.draw.rect(screen, data.BRANCO, (
                data.OUTER_AREA_WIDTH,
                data.OUTER_AREA_HEIGHT,
                data.PLAY_FIELD_WIDTH,
                data.PLAY_FIELD_HEIGHT
            ), data.LINE_WIDTH)
        
        pygame.draw.circle(screen, data.PRETO, (
                data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH // 2,
                data.OUTER_AREA_HEIGHT + data.PLAY_FIELD_HEIGHT // 2
            ), data.CENTER_CIRCLE_RADIUS, data.LINE_WIDTH)
        
        pygame.draw.rect(screen, data.AZUL, (
                data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH,
                data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2,
                data.GOAL_DEPTH,
                data.GOAL_WIDTH
            ))
        
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH , data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5 * data.SCALE), (data.OUTER_AREA_WIDTH - data.GOAL_DEPTH + 20 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH , data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH + 5 * data.SCALE), (data.OUTER_AREA_WIDTH - data.GOAL_DEPTH + 20 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH + 5 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH + 25 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + 10 * data.SCALE), (data.OUTER_AREA_WIDTH + 25 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + 50 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.arc(screen, data.BRANCO, (
            data.OUTER_AREA_WIDTH - data.GOAL_DEPTH + 3.9 * data.SCALE, 
            data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5.2 * data.SCALE,
            16 * data.SCALE * 2,
            16 * data.SCALE * 2
        ), 2 * 3.14, 2.5 * 3.14, width= data.LINE_WIDTH)
        pygame.draw.arc(screen, data.BRANCO, (
            data.OUTER_AREA_WIDTH - data.GOAL_DEPTH + 3.9 * data.SCALE, 
            data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH - 26.3 * data.SCALE,
            16 * data.SCALE * 2,
            16 * data.SCALE * 2
        ), 1.5 * 3.14, 2 * 3.14, width= data.LINE_WIDTH)
        
        pygame.draw.rect(screen, data.AMARELO, (
                data.OUTER_AREA_WIDTH - data.GOAL_DEPTH,
                data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2,
                data.GOAL_DEPTH,
                data.GOAL_WIDTH
            ))
        
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 11 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5 * data.SCALE), (data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 1 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 11 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH + 5 * data.SCALE), (data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 1 * data.SCALE, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH + 5 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.line(screen, data.BRANCO, (data.OUTER_AREA_WIDTH - 25 * data.SCALE + data.PLAY_FIELD_WIDTH, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + 10 * data.SCALE), (data.OUTER_AREA_WIDTH - 25 * data.SCALE + data.PLAY_FIELD_WIDTH, data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + 50 * data.SCALE), width= data.LINE_WIDTH)
        pygame.draw.arc(screen, data.BRANCO, (
            data.OUTER_AREA_WIDTH - data.GOAL_DEPTH - 0.3 * data.SCALE + data.PLAY_FIELD_WIDTH - 15 * data.SCALE, 
            data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 - 5.2 * data.SCALE,
            16 * data.SCALE * 2,
            16 * data.SCALE * 2
        ), 0.5 * 3.14, 1 * 3.14, width= data.LINE_WIDTH)
        pygame.draw.arc(screen, data.BRANCO, (
            data.OUTER_AREA_WIDTH - data.GOAL_DEPTH - 0.3 * data.SCALE + data.PLAY_FIELD_WIDTH - 15 * data.SCALE, 
            data.OUTER_AREA_HEIGHT + (data.PLAY_FIELD_HEIGHT - data.GOAL_WIDTH) // 2 + data.GOAL_WIDTH - 26.3 * data.SCALE,
            16 * data.SCALE * 2,
            16 * data.SCALE * 2
        ), 1 * 3.14, 1.5 * 3.14, width= data.LINE_WIDTH)

        # Pontos neutros
        neutral_spots = [
            (
                data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH // 2,
                data.OUTER_AREA_HEIGHT + data.PLAY_FIELD_HEIGHT // 2
            ),  # Centro
            (
                data.OUTER_AREA_WIDTH + 45 * data.SCALE,
                data.OUTER_AREA_HEIGHT + 40 * data.SCALE
            ),  # Canto superior esquerdo
            (
                data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 45 * data.SCALE,
                data.OUTER_AREA_HEIGHT + 40 * data.SCALE
            ),  # Canto superior direito
            (
                data.OUTER_AREA_WIDTH + 45 * data.SCALE,
                data.OUTER_AREA_HEIGHT + data.PLAY_FIELD_HEIGHT - 40 * data.SCALE
            ),  # Canto inferior esquerdo
            (
                data.OUTER_AREA_WIDTH + data.PLAY_FIELD_WIDTH - 45 * data.SCALE,
                data.OUTER_AREA_HEIGHT + data.PLAY_FIELD_HEIGHT - 40 * data.SCALE
            )  # Canto inferior direito
        ]

        for spot in neutral_spots:
            pygame.draw.circle(screen, data.PRETO, spot, data.NEUTRAL_SPOT_RADIUS)