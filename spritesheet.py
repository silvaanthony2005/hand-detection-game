import pygame

class Spritesheet():
    def __init__(self, image):
        self.sheet = image

# Funcion para separar el spritesheet en frames individuales
    def get_img(self, frame, width, height, scale, color):
        image = pygame.Surface((width, height)).convert_alpha()
        image.blit(self.sheet, (0, 0), ((frame*width), 0, width, height))
        image = pygame.transform.scale(image, (width*scale, height*scale))
        image.set_colorkey(color)
        return image