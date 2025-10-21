import os
import pygame

from vista.ball_animation import BallAnimation


class PygameRenderer:
    def __init__(self, camera_width: int = 640, camera_height: int = 480, title: str = "Hand Detection Game"):
        pygame.init()
        self.width = camera_width
        self.height = camera_height

        # Ventana inicial en modo ventana
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(title)
        self._compute_fullscreen_scaler()

        # Superficie lógica (canvas) con tamaño de cámara; mantiene coordenadas del tracker
        self.canvas = pygame.Surface((self.width, self.height)).convert_alpha()

        # Clock para limitar FPS
        self.clock = pygame.time.Clock()

        # Rutas de recursos desde la carpeta Images
        images_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Images"))

        # Fondo
        bg_path = os.path.join(images_dir, "background.jpg")
        self.background = pygame.image.load(bg_path).convert()
        self.background = pygame.transform.scale(self.background, (self.width, self.height))

        # Manos
        rh_path = os.path.join(images_dir, "right_hand.png")
        lh_path = os.path.join(images_dir, "left_hand.png")
        self.right_hand_img = pygame.image.load(rh_path).convert_alpha()
        self.left_hand_img = pygame.image.load(lh_path).convert_alpha()
        self.right_hand_img = pygame.transform.smoothscale(self.right_hand_img, (120, 120))
        self.left_hand_img = pygame.transform.smoothscale(self.left_hand_img, (120, 120))

        # Animación de pelota
        sprite_path = os.path.join(images_dir, "spritesheet_pelota.png")
        self.ball_animation = BallAnimation(sprite_path)
        self.ball_w, self.ball_h = 132, 125
        self.ball_x = (self.width - self.ball_w) // 2
        self.ball_y = (self.height - self.ball_h) // 2

    def _compute_fullscreen_scaler(self):
        # Calcula parámetros de escalado/centrado para fullscreen
        display_surf = pygame.display.get_surface()
        if display_surf is None:
            self.screen_w, self.screen_h = self.width, self.height
        else:
            self.screen_w, self.screen_h = display_surf.get_size()
        sx = self.screen_w / self.width
        sy = self.screen_h / self.height
        self.scale = min(sx, sy)
        scaled_w = int(self.width * self.scale)
        scaled_h = int(self.height * self.scale)
        self.offset_x = (self.screen_w - scaled_w) // 2
        self.offset_y = (self.screen_h - scaled_h) // 2
        self.scaled_size = (scaled_w, scaled_h)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            # Resolución nativa del monitor
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.width, self.height))
        self._compute_fullscreen_scaler()

    def render(self, right_pos=None, left_pos=None) -> bool:
        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_f:
                    self._toggle_fullscreen()

        # Dibujar sobre el canvas lógico
        self.canvas.blit(self.background, (0, 0))

        # Pelota animada
        self.ball_animation.update()
        self.ball_animation.draw(self.canvas, self.ball_x, self.ball_y)

        # Manos (si existen)
        if right_pos is not None:
            self.canvas.blit(self.right_hand_img, right_pos)
        if left_pos is not None:
            self.canvas.blit(self.left_hand_img, left_pos)

        # Presentación: escalar si fullscreen, si no blitear 1:1
        if self.is_fullscreen:
            scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
            # Limpiar pantalla (por si hay letterboxing)
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, (self.offset_x, self.offset_y))
        else:
            self.screen.blit(self.canvas, (0, 0))

        pygame.display.flip()
        self.clock.tick(30)  # 30 FPS
        return True

    def cleanup(self) -> None:
        pygame.quit()
