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

        # tamaño de las imágenes (se usan para hitboxes y para centrar)
        self.hand_w, self.hand_h = 120, 120
        self.right_hand_img = pygame.transform.smoothscale(self.right_hand_img, (self.hand_w, self.hand_h))
        self.left_hand_img = pygame.transform.smoothscale(self.left_hand_img, (self.hand_w, self.hand_h))

        # Animación de pelota
        sprite_path = os.path.join(images_dir, "spritesheet_pelota.png")
        self.ball_animation = BallAnimation(sprite_path)
        self.ball_w, self.ball_h = 132, 125
        self.ball_x = (self.width - self.ball_w) // 2
        self.ball_y = (self.height - self.ball_h) // 2

        # hitboxes: mano = caja basada en tamaño de la imagen; pelota = cuadrado inscrito en la circunferencia
        # mano: tamaño igual al mayor lado de la imagen de la mano (ajustable cambiando hand_hitbox_size)
        self.hand_hitbox_size = max(1, int(max(self.hand_w, self.hand_h)))

        # pelota: asignación manual del tamaño de la hitbox (en píxeles)
        # Este valor se puede ajustar (el rect se centra automáticamente en la pelota).
        self.ball_hitbox_size = 65

        # Debug: mostrar hitboxes
        self.show_hitboxes = False

        # Colisiones detectadas (marcador temporal)
        self.last_collision_time = 0
        self.collision_flash_ms = 400
        self.collision_hand = None

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

    # helpers de hitbox
    def _hand_rect_from_center(self, center_pos):
        #Devuelve un pygame.Rect cuadrado centrado en center_pos según self.hand_hitbox_size.
        if center_pos is None:
            return None
        cx, cy = int(center_pos[0]), int(center_pos[1])
        size = int(self.hand_hitbox_size)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        return rect

    def _ball_rect(self):
        #Rect cuadrado centrado en la pelota (usa ball_hitbox_size).
        size = int(self.ball_hitbox_size)
        cx = int(self.ball_x + self.ball_w / 2)
        cy = int(self.ball_y + self.ball_h / 2)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        return rect

    def _handle_collision(self, hand_name, hand_rect, ball_rect):
        #Marcar la colisión.
        now = pygame.time.get_ticks()
        self.last_collision_time = now
        self.collision_hand = hand_name
        print(f"COLISIÓN detectada: {hand_name}")

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
                # aceptar tecla '1' y tec numpad '1'
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    self.show_hitboxes = not self.show_hitboxes

        # Dibujar sobre el canvas lógico
        self.canvas.blit(self.background, (0, 0))

        # Pelota animada
        self.ball_animation.update()
        self.ball_animation.draw(self.canvas, self.ball_x, self.ball_y)

        # Preparar hitboxes
        right_rect = self._hand_rect_from_center(right_pos)
        left_rect = self._hand_rect_from_center(left_pos)
        ball_rect = self._ball_rect()

        # Manos (si existen) - dibujadas centradas en la posición detectada
        if right_rect is not None:
            self.canvas.blit(self.right_hand_img, right_rect.topleft)
        if left_rect is not None:
            self.canvas.blit(self.left_hand_img, left_rect.topleft)

        # Detección de colisiones simple (rect vs rect) -> marcar colisión
        # Solo registrar la primera colisión si ocurre en este frame
        if right_rect is not None and right_rect.colliderect(ball_rect):
            self._handle_collision("Right", right_rect, ball_rect)
        elif left_rect is not None and left_rect.colliderect(ball_rect):
            self._handle_collision("Left", left_rect, ball_rect)

        # Si se solicita, dibujar hitboxes (debug) como cuadrados
        if self.show_hitboxes:
            # color: rojo si colisión reciente, blanco por defecto.
            now = pygame.time.get_ticks()
            recent_collision = (now - self.last_collision_time) <= self.collision_flash_ms
            box_color = (255, 0, 0) if recent_collision else (255, 255, 255)

            # mano derecha
            if right_rect is not None:
                pygame.draw.rect(self.canvas, box_color, right_rect, 2)
            # mano izquierda
            if left_rect is not None:
                pygame.draw.rect(self.canvas, box_color, left_rect, 2)
            # pelota
            pygame.draw.rect(self.canvas, box_color, ball_rect, 2)

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
