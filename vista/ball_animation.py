import os
import pygame
from spritesheet import Spritesheet


class BallAnimation:
    """
    Maneja la animación de la pelota a partir de un spritesheet.

    - spritesheet_path: ruta al archivo de spritesheet
    - frame_width/height: tamaño de cada frame en el spritesheet
    - num_frames: cantidad de frames en el spritesheet (horizontal)
    - animation_speed: tiempo en ms entre frames
    """

    def __init__(
        self,
        spritesheet_path: str,
        frame_width: int = 132,
        frame_height: int = 125,
        num_frames: int = 15,
        animation_speed: int = 75,
        colorkey=(0, 0, 0),
    ) -> None:
        # Cargar spritesheet
        spritesheet_img = pygame.image.load(spritesheet_path).convert_alpha()
        self.spritesheet = Spritesheet(spritesheet_img)

        # Armar lista de frames
        self.frames: list[pygame.Surface] = []
        for frame in range(num_frames):
            self.frames.append(
                self.spritesheet.get_img(frame, frame_width, frame_height, 1, colorkey)
            )

        self.current_frame = 0
        self.last_update = pygame.time.get_ticks()
        self.animation_speed = animation_speed

    def update(self) -> None:
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update >= self.animation_speed:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.last_update = current_time

    def draw(self, surface: pygame.Surface, x: int, y: int) -> None:
        surface.blit(self.frames[self.current_frame], (x, y))
