import os
import math
import random
import pygame

from vista.ball_animation import BallAnimation 


class PygameRenderer:
    def __init__(self, camera_width: int = 640, camera_height: int = 480, title: str = "Hand Detection Game"):
        pygame.init()
        self.width = camera_width
        self.height = camera_height

        # Ventana inicial en modo ventana
        self.is_fullscreen = False
        try:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.SCALED)
        except Exception:
            self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(title)
        self._compute_fullscreen_scaler()

        self.canvas = pygame.Surface((self.width, self.height)).convert_alpha()
        self.clock = pygame.time.Clock()

        # Rutas de recursos (asumiendo que la estructura de directorios funciona)
        # Nota: La clase BallAnimation se asume importada y funcional.
        images_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Images"))

        # --- Carga de recursos (omitiendo la carga real si faltan archivos) ---
        # Se asume que estos archivos existen en la ruta relativa.
        # Fondo
        bg_path = os.path.join(images_dir, "background.jpg")
        self.background = pygame.Surface((self.width, self.height))
        self.background.fill((10, 50, 80)) # Color de fondo temporal si no existe la imagen
        try:
             self.background = pygame.image.load(bg_path).convert()
             self.background = pygame.transform.scale(self.background, (self.width, self.height))
        except pygame.error:
            print(f"Warning: Background image not found at {bg_path}")
        
        # Manos (usamos un rectángulo gris como fallback si faltan las imágenes)
        self.hand_w, self.hand_h = 120, 120
        hand_fallback = pygame.Surface((self.hand_w, self.hand_h), pygame.SRCALPHA)
        hand_fallback.fill((128, 128, 128, 150))
        self.right_hand_img = hand_fallback
        self.left_hand_img = hand_fallback
        try:
            rh_path = os.path.join(images_dir, "right_hand.png")
            lh_path = os.path.join(images_dir, "left_hand.png")
            self.right_hand_img = pygame.image.load(rh_path).convert_alpha()
            self.left_hand_img = pygame.image.load(lh_path).convert_alpha()
            self.right_hand_img = pygame.transform.smoothscale(self.right_hand_img, (self.hand_w, self.hand_h))
            self.left_hand_img = pygame.transform.smoothscale(self.left_hand_img, (self.hand_w, self.hand_h))
        except pygame.error:
            print("Warning: Hand images not found, using fallback.")

        # Animación de pelota
        sprite_path = os.path.join(images_dir, "spritesheet_pelota.png")
        # Usamos un dummy si BallAnimation no está disponible
        try:
             self.ball_animation = BallAnimation(sprite_path)
        except NameError:
             print("Error: BallAnimation class not found. Using dummy surface.")
             class DummyBallAnimation:
                def update(self): pass
                def draw(self, surf, x, y): 
                    surf.fill((255, 100, 0)) # Pelota naranja de fallback
             self.ball_animation = DummyBallAnimation()
        
        self.ball_w, self.ball_h = 132, 125
        self.ball_x = (self.width - self.ball_w) // 2
        self.ball_y = (self.height - self.ball_h) // 2
        self._ball_surface = pygame.Surface((self.ball_w, self.ball_h), pygame.SRCALPHA)

        # hitboxes
        self.hand_hitbox_size = max(1, int(max(self.hand_w, self.hand_h)))
        self.ball_hitbox_size = 65

        self.show_hitboxes = False
        self.last_collision_time = 0
        self.collision_flash_ms = 400
        self.collision_hand = None
        self.ball_rotating = False
        self.ball_angle = 0.0
        self.ball_rotation_speed = 6.0
        self._rotation_cache = {}
        self._rotation_cache_step = 5

        # Compatibilidad de estado de atrapado
        self.ball_caught = False
        self.caught_by = None
        self._last_toggle_time = 0
        self._toggle_cooldown_ms = 200

        # --- MODIFICACIONES CLAVE PARA EL MOVIMIENTO 2D ---
        self.ball_moving = False
        self._move_speed_mag = 40 # 
        self._move_speed_x = 0.0 # Componente X de la velocidad
        self._move_speed_y = 0.0  # Componente Y de la velocidad
        
        # Definición de límites de rebote (usando la mitad del tamaño de la pelota)
        self.ball_half_w = self.ball_w // 2
        self.ball_half_h = self.ball_h // 2
        
        self._move_target_left = self.ball_half_w# X Mínimo (Centro)
        self._move_target_right = self.width - self.ball_half_w # X Máximo (Centro)
        self._move_target_top = self.ball_half_h # Y Mínimo (Centro)
        self._move_target_bottom = self.height - self.ball_half_h # Y Máximo (Centro)

        # Variables de escala mantenidas por compatibilidad, aunque la lógica de "aproximación"
        # deja de tener sentido con movimiento de rebote continuo.
        self.ball_scale = 1.0
        self._move_scale_start = 0.6
        self._move_start_x = self.ball_x
        # -------------------------------------------------------------------

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
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            try:
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.SCALED)
            except Exception:
                self.screen = pygame.display.set_mode((self.width, self.height))
        self._compute_fullscreen_scaler()

    # helpers de hitbox
    def _hand_rect_from_center(self, center_pos):
        if center_pos is None:
            return None
        cx, cy = int(center_pos[0]), int(center_pos[1])
        size = int(self.hand_hitbox_size)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        return rect

    def _ball_rect(self):
        size = int(self.ball_hitbox_size)
        cx = int(self.ball_x + self.ball_w / 2)
        cy = int(self.ball_y + self.ball_h / 2)
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (cx, cy)
        return rect

    def _handle_collision(self, hand_name, hand_rect, ball_rect):
        now = pygame.time.get_ticks()
        self.last_collision_time = now
        self.collision_hand = hand_name
        # Mensajes de debug desactivados para ahorrar I/O

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
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    self.show_hitboxes = not self.show_hitboxes
                # Toggle con debounce para tecla '2'
                if event.key == pygame.K_2 or event.key == pygame.K_KP2:
                    now = pygame.time.get_ticks()
                    if now - self._last_toggle_time >= self._toggle_cooldown_ms:
                        self.ball_rotating = not self.ball_rotating
                        self._last_toggle_time = now
                        print(f"[DEBUG] ball_rotating -> {self.ball_rotating}")
                
                # Tecla 'Enter' INICIA desplazamiento en dirección aleatoria 2D
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    if self.ball_rotating and not self.ball_moving:
                        # si está atrapada, soltar antes de iniciar
                        if self.ball_caught:
                            self.ball_caught = False
                            self.caught_by = None
                        self.ball_moving = True
                        
                        # 1. Elegir un ángulo de movimiento aleatorio (en radianes)
                        # Usamos 360 grados (2*pi) para movimiento completamente aleatorio en 2D
                        angle_radians = random.uniform(0, 2 * math.pi)
                        
                        # 2. Descomponer la velocidad total (magnitud) en componentes X e Y
                        self._move_speed_x = self._move_speed_mag * math.cos(angle_radians)
                        self._move_speed_y = self._move_speed_mag * math.sin(angle_radians)
                        
                        # Opcional: Asegurarse de que no sea demasiado lento en un eje (evitar ángulos muy cercanos a 0, 90, 180, 270)
                        min_speed_component = 0.5 
                        if abs(self._move_speed_x) < min_speed_component:
                            self._move_speed_x = min_speed_component if self._move_speed_x >= 0 else -min_speed_component
                        if abs(self._move_speed_y) < min_speed_component:
                            self._move_speed_y = min_speed_component if self._move_speed_y >= 0 else -min_speed_component


                        # El efecto de escala de aproximación ya no es útil para rebote continuo, pero mantenemos las variables
                        self.ball_scale = 1.0
                        self._move_start_x = self.ball_x

        # Actualizar movimiento si corresponde
        if self.ball_moving:
            if not self.ball_rotating:
                # Si la pelota deja de rotar, detener desplazamiento
                self.ball_moving = False
                self._move_speed_x = 0.0
                self._move_speed_y = 0.0
            else:
                # 1. Aplicar movimiento 2D
                self.ball_x += self._move_speed_x
                self.ball_y += self._move_speed_y

                # 2. Lógica de Rebote (Horizontal X)
                center_x = self.ball_x + self.ball_half_w
                if center_x > self._move_target_right:
                    self.ball_x = self._move_target_right - self.ball_half_w
                    self._move_speed_x *= -1 # Invierte dirección X (rebote)
                elif center_x < self._move_target_left:
                    self.ball_x = self._move_target_left - self.ball_half_w
                    self._move_speed_x *= -1 # Invierte dirección X (rebote)

                # 3. Lógica de Rebote (Vertical Y)
                center_y = self.ball_y + self.ball_half_h
                if center_y > self._move_target_bottom:
                    self.ball_y = self._move_target_bottom - self.ball_half_h
                    self._move_speed_y *= -1 # Invierte dirección Y (rebote)
                elif center_y < self._move_target_top:
                    self.ball_y = self._move_target_top - self.ball_half_h
                    self._move_speed_y *= -1 # Invierte dirección Y (rebote)
                
                # Para movimiento de rebote continuo, la escala se mantiene en 1.0
                self.ball_scale = 1.0

        # Dibujar sobre el canvas lógico
        self.canvas.blit(self.background, (0, 0))

        # Pelota animada
        if self.ball_rotating:
            self.ball_animation.update()

        # Reutilizar superficie temporal para la pelota
        self._ball_surface.fill((0, 0, 0, 0))
        self.ball_animation.draw(self._ball_surface, 0, 0)

        # Centro según tamaño base
        cx = int(self.ball_x + self.ball_w / 2)
        cy = int(self.ball_y + self.ball_h / 2)

        if self.ball_rotating:
            # velocidad de rotación estándar
            self.ball_angle = (self.ball_angle + self.ball_rotation_speed) % 360
            # Si no hay escala, usar rotate (más ligero); si hay escala != 1.0, usar rotozoom
            if abs(self.ball_scale - 1.0) < 1e-6:
                # Usar cache de rotaciones para reducir costo CPU
                step = self._rotation_cache_step
                angle_q = int(round(self.ball_angle / step)) * step
                rotated = self._rotation_cache.get(angle_q)
                if rotated is None:
                    rotated = pygame.transform.rotate(self._ball_surface, angle_q)
                    self._rotation_cache[angle_q] = rotated
            else:
                rotated = pygame.transform.rotozoom(self._ball_surface, self.ball_angle, self.ball_scale)
            rect = rotated.get_rect(center=(cx, cy))
            self.canvas.blit(rotated, rect.topleft)
        else:
            if self.ball_scale != 1.0:
                # usar scale (más rápido que smoothscale)
                scaled = pygame.transform.scale(self._ball_surface, (int(self.ball_w * self.ball_scale), int(self.ball_h * self.ball_scale)))
                rect = scaled.get_rect(center=(cx, cy))
                self.canvas.blit(scaled, rect.topleft)
            else:
                self.canvas.blit(self._ball_surface, (self.ball_x, self.ball_y))

        # Preparar hitboxes
        right_rect = self._hand_rect_from_center(right_pos)
        left_rect = self._hand_rect_from_center(left_pos)
        ball_rect = self._ball_rect()

        # Manos
        if right_rect is not None:
            self.canvas.blit(self.right_hand_img, right_rect.topleft)
        if left_rect is not None:
            self.canvas.blit(self.left_hand_img, left_rect.topleft)

        # Colisiones
        collided = False
        if right_rect is not None and right_rect.colliderect(ball_rect):
            self._handle_collision("Right", right_rect, ball_rect)
            collided = True
        elif left_rect is not None and left_rect.colliderect(ball_rect):
            self._handle_collision("Left", left_rect, ball_rect)
            collided = True

        # Si alguna mano toca la pelota, resetear al centro y detener el movimiento
        if collided:
            self.ball_moving = False
            self.ball_scale = 1.0
            self._move_speed_x = 0.0
            self._move_speed_y = 0.0
            # volver al centro inicial
            self.ball_x = (self.width - self.ball_w) // 2
            self.ball_y = (self.height - self.ball_h) // 2

        # Mostrar hitboxes si corresponde
        if self.show_hitboxes:
            now = pygame.time.get_ticks()
            recent_collision = (now - self.last_collision_time) <= self.collision_flash_ms
            box_color = (255, 0, 0) if recent_collision else (255, 255, 255)
            if right_rect is not None:
                pygame.draw.rect(self.canvas, box_color, right_rect, 2)
            if left_rect is not None:
                pygame.draw.rect(self.canvas, box_color, left_rect, 2)
            pygame.draw.rect(self.canvas, box_color, ball_rect, 2)

        # Presentación
        if self.is_fullscreen:
            scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, (self.offset_x, self.offset_y))
        else:
            self.screen.blit(self.canvas, (0, 0))

        pygame.display.flip()
        # Limitar FPS
        self.clock.tick(30)
        return True

    def cleanup(self) -> None:
        pygame.quit()
