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
        # Sugerencia de rendimiento: DOUBLEBUF y SCALED pueden ayudar en Windows
        try:
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.SCALED)
        except Exception:
            # Fallback seguro
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
        # Superficie temporal reutilizable para dibujar la pelota (evita crear cada frame)
        self._ball_surface = pygame.Surface((self.ball_w, self.ball_h), pygame.SRCALPHA)

        # hitboxes: mano = caja basada en tamaño de la imagen; pelota = cuadrado inscrito en la circunferencia
        self.hand_hitbox_size = max(1, int(max(self.hand_w, self.hand_h)))

        # pelota: asignación manual del tamaño de la hitbox (en píxeles)
        self.ball_hitbox_size = 65

        # Debug: mostrar hitboxes
        self.show_hitboxes = False

        # Colisiones detectadas (marcador temporal)
        self.last_collision_time = 0
        self.collision_flash_ms = 400
        self.collision_hand = None

        # Estado de rotación de la pelota (inactivo al inicio)
        self.ball_rotating = False
        self.ball_angle = 0.0
        self.ball_rotation_speed = 6.0
        # Cache de rotaciones (solo cuando escala==1.0) para reducir CPU
        self._rotation_cache = {}
        self._rotation_cache_step = 5  # grados por paso (72 entradas máx)

        # Compatibilidad: variables de "atrapado" que fueron usadas antes
        # No se usa lógica de atrapado actualmente, pero estas banderas evitan errores
        # cuando se presiona Enter (se consultan y se resetean si existieran)
        self.ball_caught = False
        self.caught_by = None

        # Toggle debounce para evitar reversiones por key-repeat
        self._last_toggle_time = 0
        self._toggle_cooldown_ms = 200  # 200 ms de protección

        # Movimiento iniciado con tecla Enter (dirección aleatoria)
        self.ball_moving = False
        self._move_direction = 1               # +1 derecha, -1 izquierda
        self._move_speed = 8                   # px por frame (un poco más rápido sin subir FPS)
        self._move_amplitude = 36              # amplitud vertical de la oscilación
        self._move_phase = 0.0
        self._move_phase_speed = 0.24          # incremento de fase por frame
        self._move_origin_y = self.ball_y
        self._move_target_right = self.width - 40
        self._move_target_left = 40

        # Escala visual: efecto de aproximación durante el desplazamiento
        self.ball_scale = 1.0                 # 1.0 tamaño normal
        self._move_scale_start = 0.6          # escala inicial al iniciar desplazamiento
        self._move_start_x = self.ball_x      # para calcular progreso hacia el objetivo

    # (Limpieza) Sin estado de atrapado: la colisión con cualquier mano resetea al centro

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
                
                # Tecla 'Enter' INICIA desplazamiento en dirección aleatoria
                # (solo si la pelota está rotando y no se está moviendo)
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    if self.ball_rotating and not self.ball_moving:
                        # si está atrapada, soltar antes de iniciar
                        if self.ball_caught:
                            self.ball_caught = False
                            self.caught_by = None
                        self.ball_moving = True
                        self._move_direction = random.choice([-1, 1])
                        self._move_origin_y = self.ball_y
                        self._move_phase = 0.0
                        # efecto de aproximación: iniciar pequeño
                        self.ball_scale = self._move_scale_start
                        self._move_start_x = self.ball_x

        # Actualizar movimiento si corresponde (antes de dibujar la pelota)
        if self.ball_moving:
            if not self.ball_rotating:
                # si la pelota deja de rotar (pasa a estática), detener desplazamiento
                self.ball_moving = False
            else:
                self.ball_x += self._move_speed * self._move_direction
                self._move_phase += self._move_phase_speed
                # oscilación vertical tipo seno alrededor del origen fijado
                self.ball_y = int(self._move_origin_y + self._move_amplitude * math.sin(self._move_phase))
                # actualizar escala en función de la proximidad al objetivo
                target_x = self._move_target_right if self._move_direction > 0 else self._move_target_left
                dist_total = abs(target_x - self._move_start_x)
                if dist_total <= 0:
                    self.ball_scale = 1.0
                else:
                    dist_rest = abs(target_x - self.ball_x)
                    progress = max(0.0, min(1.0, 1.0 - (dist_rest / dist_total)))
                    self.ball_scale = self._move_scale_start + (1.0 - self._move_scale_start) * progress
                # detener al llegar al objetivo según dirección
                if self._move_direction > 0:
                    if self.ball_x >= self._move_target_right:
                        self.ball_x = self._move_target_right
                        self.ball_moving = False
                        self.ball_scale = 1.0
                else:
                    if self.ball_x <= self._move_target_left:
                        self.ball_x = self._move_target_left
                        self.ball_moving = False
                        self.ball_scale = 1.0

        # Dibujar sobre el canvas lógico
        self.canvas.blit(self.background, (0, 0))

        # Pelota animada
        # Solo avanzamos animación y aplicamos rotación si está activada
        if self.ball_rotating:
            self.ball_animation.update()

        # Reutilizar superficie temporal para la pelota
        self._ball_surface.fill((0, 0, 0, 0))
        self.ball_animation.draw(self._ball_surface, 0, 0)

        # Centro según tamaño base; el escalado se compensa centrando al dibujar
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

        # Si alguna mano toca la pelota, resetear al centro sin quedar estática (no alteramos rotación)
        if collided:
            self.ball_moving = False
            self.ball_scale = 1.0
            self._move_phase = 0.0
            # volver al centro inicial
            self.ball_x = (self.width - self.ball_w) // 2
            self.ball_y = (self.height - self.ball_h) // 2
            # (Limpieza) Sin estado de atrapado adicional

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
