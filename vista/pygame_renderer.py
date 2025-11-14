import os
import math
import random
import pygame

from vista.ball_animation import BallAnimation 


class PygameRenderer:
    def __init__(self, camera_width: int = 640, camera_height: int = 480, title: str = "Hand Detection Game",
                 enable_prep_screen: bool = True,
                 enable_auto_launch: bool = True,
                 auto_launch_delay_ms: int = 700,
                 countdown_seconds: int = 3):
        pygame.init()
        pygame.mixer.init()
        self.width = camera_width
        self.height = camera_height

        # Carga de la música de fondo
        try:
            music_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "audio", "showtime.ogg"))
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(0.5)  # Se ajusta el volumen (0.0 a 1.0)
        except pygame.error as e:
            print(f"Warning: No se pudo cargar el archivo de música en {music_path}: {e}")

        # Carga del sonido de game over
        try:
            game_over_sound_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "audio", "gameover.ogg"))
            self.game_over_sound = pygame.mixer.Sound(game_over_sound_path)
            self.game_over_sound.set_volume(1.0)
        except pygame.error as e:
            print(f"Warning: No se pudo cargar el sonido de game over en {game_over_sound_path}: {e}")
            self.game_over_sound = None

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
        
        # Crear y cachear una versión desenfocada del fondo
        try:
            blur_scale = 0.06
            sw = max(1, int(self.width * blur_scale))
            sh = max(1, int(self.height * blur_scale))
            small = pygame.transform.smoothscale(self.background, (sw, sh))
            self.background_blur = pygame.transform.smoothscale(small, (self.width, self.height))
        except Exception:
            # si algo falla, usar copia normal
            self.background_blur = self.background.copy()

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
        self.ball_y = self.height - self.ball_h - 210  # Posición del portero
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

        # --- NUEVAS VARIABLES PARA EL SISTEMA DE ARQUERÍA MEJORADO ---
        self.ball_moving = False
        self.ball_launching = False
        self.ball_target_x = 0
        self.ball_target_y = 0
        
        # Tiempo constante de viaje (2 segundos)
        self.ball_travel_time = 2000  # ms
        self.ball_launch_start_time = 0
        
        # Control de trayectoria curva
        self.curve_strength = 0.0
        self.curve_direction = 0
        self.control_point_x = 0
        self.control_point_y = 0
        
        # Sistema de puntuación
        self.score = 0
        self.misses = 0
        self.max_misses = 3

        # --- Configuración visual del marcador ---
        # Posición del número de goles (coordenada midleft en el canvas lógico)
        self.score_pos = (22.5 , 55)
        # Origen (x,y) para la primera X de derrotas; las siguientes se apilan verticalmente hacia abajo
        self.misses_icons_origin = (72, 32)
        # Tamaño y separación de cada icono X (en píxeles)
        self.miss_icon_size = 10
        self.miss_icon_spacing = 8
        # Color de las X
        self.miss_icon_color = (230, 40, 40)
        
        # Escalado progresivo - INICIA PEQUEÑA (0.2)
        self.ball_scale = 0.2  # CAMBIADO: ahora inicia pequeña
        self._move_start_x = self.ball_x + self.ball_w/2
        self._move_start_y = self.ball_y + self.ball_h/2
        
        # Definición de límites (sin cambio)
        self.ball_half_w = self.ball_w // 2
        self.ball_half_h = self.ball_h // 2
        
        self._move_target_left = self.ball_half_w
        self._move_target_right = self.width - self.ball_half_w
        self._move_target_top = self.ball_half_h
        self._move_target_bottom = self.height - self.ball_half_h

        # --- Game over: cargar imagen y fuentes ---
        self.game_over = False
        self.game_over_image = None
        self.game_over_instr_font = pygame.font.Font(None, 20)
        self.game_over_font = pygame.font.Font(None, 72)
        try:
            go_path = os.path.join(images_dir, "game_over.png")  # coloca la imagen guardada como Images/game_over.png
            img = pygame.image.load(go_path).convert_alpha()
            # Escalar para que encaje en la ventana manteniendo aspecto (95% del área disponible)
            iw, ih = img.get_size()
            if iw == 0 or ih == 0:
                raise Exception("invalid image size")
            fit_scale = min(self.width / iw, self.height / ih) * 0.95
            new_w = max(1, int(iw * fit_scale))
            new_h = max(1, int(ih * fit_scale))
            self.game_over_image = pygame.transform.smoothscale(img, (new_w, new_h))
            # guardar rect centrado para usar en render()
            self.game_over_image_rect = self.game_over_image.get_rect(center=(self.width // 2, self.height // 2))
        except Exception:
             # si no existe la imagen, se usará texto grande
            self.game_over_image = None
            self.game_over_image_rect = None

        # --- Menu inicial ---
        self.show_menu = True
        self.menu_image = None
        self.menu_image_rect = None
        self.menu_instr_font = pygame.font.Font(None, 28)
        try:
            menu_path = os.path.join(images_dir, "menu.png")
            mimg = pygame.image.load(menu_path).convert_alpha()
            mw, mh = mimg.get_size()
            if mw == 0 or mh == 0:
                raise Exception("invalid menu image")
            menu_scale = min(self.width / mw, self.height / mh) * 0.95
            mw2 = max(1, int(mw * menu_scale))
            mh2 = max(1, int(mh * menu_scale))
            self.menu_image = pygame.transform.smoothscale(mimg, (mw2, mh2))
            self.menu_image_rect = self.menu_image.get_rect(center=(self.width // 2, self.height // 2))
        except Exception:
            self.menu_image = None
            self.menu_image_rect = None

        # --- Imagen para pantalla de preparación ---
        self.prep_image = None
        self.prep_image_rect = None
        try:
            prep_path = os.path.join(images_dir, "prep_screen.png")  # Images/prep_screen.png
            pimg = pygame.image.load(prep_path).convert_alpha()
            iw, ih = pimg.get_size()
            if iw == 0 or ih == 0:
                raise Exception("invalid prep image")
            # Escalado "cover": cubrir toda la ventana, mantener aspect ratio (puede recortar)
            scale = max(self.width / iw, self.height / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            self.prep_image = pygame.transform.smoothscale(pimg, (new_w, new_h))
            # rect centrado; al cubrir la pantalla puede quedar mayor en una dimensión
            self.prep_image_rect = self.prep_image.get_rect(center=(self.width // 2, self.height // 2))
        except Exception:
            # si la imagen falta, dejamos None (fallback mostrará fondo desenfocado con texto)
            self.prep_image = None
            self.prep_image_rect = None

        # --- Pantalla de preparación / countdown ---
        self.waiting_start = False
        self.countdown_active = False
        self.countdown_start_time = 0
        # configurable
        self.countdown_seconds = countdown_seconds
        self.start_prompt_font = pygame.font.Font(None, 40)

        # Auto-launch tras el primer inicio: cuando True se lanza automáticamente después de cada reset
        # flags configurables (no rompen compatibilidad: valores por defecto mantienen comportamiento nuevo)
        self.enable_prep_screen = enable_prep_screen
        self.enable_auto_launch = enable_auto_launch
        self.auto_launch_enabled = False
        self.auto_launch_delay_ms = auto_launch_delay_ms
        self._last_reset_time = pygame.time.get_ticks()

    def _compute_fullscreen_scaler(self):
        # sin cambio
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
        # sin cambio
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        else:
            try:
                self.screen = pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF | pygame.SCALED)
            except Exception:
                self.screen = pygame.display.set_mode((self.width, self.height))
        self._compute_fullscreen_scaler()

    def _generate_target_position(self):
        """Genera posición objetivo con preferencia por esquinas y bordes"""
        # Áreas preferentes (esquinas y bordes)
        corner_weight = 0.6  # 60% de probabilidad para esquinas
        edge_weight = 0.3    # 30% para bordes
        center_weight = 0.1  # 10% para centro
        
        choice = random.random()
        
        if choice < corner_weight:
            # Esquina
            corner = random.choice([0, 1, 2, 3])  # 0: sup-izq, 1: sup-der, 2: inf-izq, 3: inf-der
            if corner == 0:  # Superior izquierda
                return (random.randint(50, self.width//4), random.randint(50, self.height//4))
            elif corner == 1:  # Superior derecha
                return (random.randint(self.width*3//4, self.width-50), random.randint(50, self.height//4))
            elif corner == 2:  # Inferior izquierda
                return (random.randint(50, self.width//4), random.randint(self.height*3//4, self.height-50))
            else:  # Inferior derecha
                return (random.randint(self.width*3//4, self.width-50), random.randint(self.height*3//4, self.height-50))
        
        elif choice < corner_weight + edge_weight:
            # Borde
            edge = random.choice([0, 1, 2, 3])  # 0: superior, 1: inferior, 2: izquierdo, 3: derecho
            if edge == 0:  # Superior
                return (random.randint(self.width//4, self.width*3//4), random.randint(30, self.height//6))
            elif edge == 1:  # Inferior
                return (random.randint(self.width//4, self.width*3//4), random.randint(self.height*5//6, self.height-30))
            elif edge == 2:  # Izquierdo
                return (random.randint(30, self.width//6), random.randint(self.height//4, self.height*3//4))
            else:  # Derecho
                return (random.randint(self.width*5//6, self.width-30), random.randint(self.height//4, self.height*3//4))
        
        else:
            # Centro (menos probable)
            return (random.randint(self.width//3, self.width*2//3), random.randint(self.height//3, self.height*2//3))

    def _calculate_bezier_point(self, t, start_x, start_y, control_x, control_y, end_x, end_y):
        """Calcula punto en curva Bézier cuadrática"""
        u = 1 - t
        tt = t * t
        uu = u * u
        
        x = uu * start_x + 2 * u * t * control_x + tt * end_x
        y = uu * start_y + 2 * u * t * control_y + tt * end_y
        
        return x, y

    def _generate_curve_parameters(self, start_x, start_y, end_x, end_y):
        """Genera parámetros para trayectoria curva"""
        # Determinar si habrá curva (70% de probabilidad)
        if random.random() < 0.7:
            curve_strength = random.uniform(0.2, 0.8)
            curve_direction = random.choice([-1, 1])
            
            # Punto de control para la curva Bézier
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            
            # Desplazamiento perpendicular
            dx = end_x - start_x
            dy = end_y - start_y
            length = max(1, math.sqrt(dx*dx + dy*dy))
            
            # Vector perpendicular normalizado
            perp_x = -dy / length
            perp_y = dx / length
            
            # Aplicar curva
            curve_distance = length * curve_strength * 0.5
            control_x = mid_x + perp_x * curve_distance * curve_direction
            control_y = mid_y + perp_y * curve_distance * curve_direction
            
            return curve_strength, curve_direction, control_x, control_y
        else:
            # Trayectoria recta
            return 0.0, 0, 0, 0

    def _launch_ball_to_random_target(self):
        """Lanza la pelota a una posición aleatoria con tiempo constante"""
        if self.ball_launching or self.ball_caught or self.game_over:
            return
        
        # Posición inicial
        self.ball_x = (self.width - self.ball_w) // 2
        self.ball_y = self.height - self.ball_h - 210 # Posición del que patea
        start_x = self.ball_x + self.ball_w/2
        start_y = self.ball_y + self.ball_h/2
        
        # Generar posición objetivo con preferencia por esquinas
        self.ball_target_x, self.ball_target_y = self._generate_target_position()
        
        # Generar parámetros de curva
        (self.curve_strength, self.curve_direction, 
         self.control_point_x, self.control_point_y) = self._generate_curve_parameters(
            start_x, start_y, self.ball_target_x, self.ball_target_y
        )
        
        # Configurar estado de lanzamiento
        self.ball_launching = True
        self.ball_moving = True
        self.ball_rotating = True
        self.ball_scale = 0.2  # Comienza pequeña (igual que al inicio)
        self.ball_launch_start_time = pygame.time.get_ticks()
        
        print(f"¡Pelota lanzada hacia ({self.ball_target_x}, {self.ball_target_y})!")
        if self.curve_strength > 0:
            print(f"Trayectoria curva: fuerza {self.curve_strength:.2f}")

    def _reset_ball_position(self):
        """Resetea la pelota a la posición inicial DEL PORTERO"""
        self.ball_launching = False
        self.ball_moving = False
        self.ball_x = (self.width - self.ball_w) // 2
        self.ball_y = self.height - self.ball_h - 210
        self.ball_scale = 0.2
        self.ball_caught = False
        self.caught_by = None
        self.curve_strength = 0.0
        # marcar tiempo del reset para posible auto-launch
        self._last_reset_time = pygame.time.get_ticks()

    def _check_ball_catch(self, hand_rect, ball_rect):
        """Verifica si se atrapó la pelota (solo cuando tiene escala 1.0)"""
        if self.ball_scale >= 0.95 and hand_rect.colliderect(ball_rect):
            return True
        return False

    # helpers de hitbox (sin cambio)
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
        # sin cambio
        now = pygame.time.get_ticks()
        self.last_collision_time = now
        self.collision_hand = hand_name

    def render(self, right_pos=None, left_pos=None) -> bool:
        # Eventos (MODIFICADO para nuevo sistema)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                # cuando estamos en menú, ENTER pasa a pantalla de preparación (configurable); ESC sale
                if self.show_menu:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        # Iniciar música al salir del menú
                        pygame.mixer.music.play(-1)
                        # comportamiento configurable: si está activada la pantalla de preparación,
                        # entrar en waiting_start para que el jugador coloque las manos; si no,
                        # iniciar el juego inmediatamente (y opcionalmente auto-lanzar si está configurado).
                        self.show_menu = False
                        # reiniciar estado base
                        self.score = 0
                        self.misses = 0
                        self.game_over = False
                        self._reset_ball_position()
                        if self.enable_prep_screen:
                            self.waiting_start = True
                            # mientras esperamos, no auto-launch
                            self.auto_launch_enabled = False
                            print("Ir a pantalla 'Pulsa ENTER para iniciar'.")
                        else:
                            # iniciar juego inmediatamente
                            self.waiting_start = False
                            # activar auto-launch sólo si la opción está habilitada
                            self.auto_launch_enabled = bool(self.enable_auto_launch)
                            print("Juego iniciado (inicio inmediato, sin pantalla de preparación).")
                            # si se desea auto-lanzar al empezar y está habilitado, lanzar ahora
                            if self.auto_launch_enabled and not self.ball_launching and not self.ball_moving:
                                self._launch_ball_to_random_target()
                    # ignorar el resto de teclas mientras esté el menú
                    continue
                
                # Si estamos en la pantalla de preparación ("Pulsa ENTER para iniciar")
                if self.waiting_start and not self.countdown_active:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        # iniciar la cuenta regresiva
                        self.countdown_active = True
                        self.countdown_start_time = pygame.time.get_ticks()
                        print("Cuenta regresiva iniciada.")
                    # ignorar otras teclas en este estado
                    continue

                # Si la cuenta regresiva está activa, sólo ESC puede salir
                if self.countdown_active:
                    if event.key == pygame.K_ESCAPE:
                        return False
                    # ignorar otras teclas durante countdown
                    continue
                
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_f:
                    self._toggle_fullscreen()
                if event.key == pygame.K_1 or event.key == pygame.K_KP1:
                    self.show_hitboxes = not self.show_hitboxes
                # Toggle con debounce para tecla '2' (sin cambio)
                if event.key == pygame.K_2 or event.key == pygame.K_KP2:
                    now = pygame.time.get_ticks()
                    if now - self._last_toggle_time >= self._toggle_cooldown_ms:
                        self.ball_rotating = not self.ball_rotating
                        self._last_toggle_time = now
                        print(f"[DEBUG] ball_rotating -> {self.ball_rotating}")
                
                # Tecla 'Enter' LANZA la pelota a objetivo aleatorio (MODIFICADO)
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # si estamos en game over -> reiniciar; si no, lanzar
                    if self.game_over:
                        # reiniciar todo el estado del juego
                        self.score = 0
                        self.misses = 0
                        self.game_over = False
                        self._reset_ball_position()
                        # Reiniciar música
                        pygame.mixer.music.play(-1)
                        print("Juego reiniciado (Enter).")
                    else:
                        if not self.ball_launching and not self.ball_moving:
                            self._launch_ball_to_random_target()

        # Si estamos en el menú, dibujar y devolver sin ejecutar la lógica del juego
        if self.show_menu:
            # dibujar fondo y menú centrado
            # usar la versión desenfocada si está disponible
            if getattr(self, "background_blur", None) is not None:
                self.canvas.blit(self.background_blur, (0, 0))
            else:
                self.canvas.blit(self.background, (0, 0))
            if self.menu_image is not None:
                self.canvas.blit(self.menu_image, self.menu_image_rect.topleft)
                instr = self.menu_instr_font.render("Pulsa ENTER para jugar  •  ESC para salir", True, (240, 240, 240))
                instr_rect = instr.get_rect(center=(self.width // 2, self.menu_image_rect.bottom + 24))
                self.canvas.blit(instr, instr_rect.topleft)
            else:
                # fallback textual
                title_font = pygame.font.Font(None, 96)
                title = title_font.render("FUTBOL CAMARA", True, (255, 255, 255))
                t_rect = title.get_rect(center=(self.width // 2, self.height // 2 - 40))
                self.canvas.blit(title, t_rect.topleft)
                instr = self.menu_instr_font.render("Pulsa ENTER para jugar  •  ESC para salir", True, (240, 240, 240))
                instr_rect = instr.get_rect(center=(self.width // 2, self.height // 2 + 40))
                self.canvas.blit(instr, instr_rect.topleft)

            # Presentación y retorno temprano
            if self.is_fullscreen:
                scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
                self.screen.fill((0, 0, 0))
                self.screen.blit(scaled, (self.offset_x, self.offset_y))
            else:
                self.screen.blit(self.canvas, (0, 0))
            pygame.display.flip()
            self.clock.tick(60)
            return True

        # Pantalla de preparación (esperando que el jugador coloque las manos)
        if self.waiting_start and not self.countdown_active:
            # Mostrar la imagen de preparación escalada para llenar la ventana.
            if self.prep_image is not None:
                # La imagen ya fue escalada en __init__ tipo "cover"; sólo blitearla centrada
                self.canvas.blit(self.prep_image, self.prep_image_rect.topleft)


            # Presentación y retorno temprano
            if self.is_fullscreen:
                scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
                self.screen.fill((0, 0, 0))
                self.screen.blit(scaled, (self.offset_x, self.offset_y))
            else:
                self.screen.blit(self.canvas, (0, 0))
            pygame.display.flip()
            self.clock.tick(60)
            return True

        # Pantalla de countdown (3..2..1)
        now = pygame.time.get_ticks()
        if self.countdown_active:
            # Dibujar fondo desenfocado
            if getattr(self, "background_blur", None) is not None:
                self.canvas.blit(self.background_blur, (0, 0))
            else:
                self.canvas.blit(self.background, (0, 0))
            elapsed = now - self.countdown_start_time
            idx = int(elapsed // 1000)
            remaining = self.countdown_seconds - idx
            if remaining > 0:
                txt = str(remaining)
            else:
                txt = "GO!"
            big_font = pygame.font.Font(None, 140)
            txt_surf = big_font.render(txt, True, (255, 220, 0))
            txt_rect = txt_surf.get_rect(center=(self.width // 2, self.height // 2))
            # fondo oscuro para el número
            box = pygame.Surface((txt_rect.width + 40, txt_rect.height + 24), pygame.SRCALPHA)
            box.fill((0, 0, 0, 160))
            box_rect = box.get_rect(center=txt_rect.center)
            self.canvas.blit(box, box_rect.topleft)
            self.canvas.blit(txt_surf, txt_rect.topleft)
            pygame.display.flip()

            # terminar countdown
            if elapsed >= (self.countdown_seconds * 1000):
                self.countdown_active = False
                self.waiting_start = False
                # activar auto-launch sólo si la opción está habilitada
                self.auto_launch_enabled = bool(self.enable_auto_launch)
                # lanzar la primera pelota automáticamente (si se habilitó auto-launch)
                if self.auto_launch_enabled and not self.ball_launching and not self.ball_moving:
                    self._launch_ball_to_random_target()
                # registrar tiempo del reset para controlar auto-launch posterior
                self._last_reset_time = pygame.time.get_ticks()
            self.clock.tick(60)
            return True

        # Actualizar movimiento con tiempo constante y trayectoria curva (COMPLETAMENTE MODIFICADO)
        if self.ball_moving and self.ball_launching:
            if not self.ball_rotating:
                # Si la pelota deja de rotar, detener desplazamiento
                self.ball_moving = False
                self.ball_launching = False
            else:
                current_time = pygame.time.get_ticks()
                elapsed_time = current_time - self.ball_launch_start_time
                progress = min(1.0, elapsed_time / self.ball_travel_time)
                
                start_x = self._move_start_x
                start_y = self._move_start_y
                
                if self.curve_strength > 0:
                    # Trayectoria curva (Bézier)
                    new_x, new_y = self._calculate_bezier_point(
                        progress, start_x, start_y, 
                        self.control_point_x, self.control_point_y,
                        self.ball_target_x, self.ball_target_y
                    )
                else:
                    # Trayectoria recta
                    new_x = start_x + (self.ball_target_x - start_x) * progress
                    new_y = start_y + (self.ball_target_y - start_y) * progress
                
                # Actualizar posición de la pelota (centro)
                self.ball_x = new_x - self.ball_w/2
                self.ball_y = new_y - self.ball_h/2
                
                # Escalar la pelota basado en el progreso
                start_scale = 0.2
                target_scale = 1.0
                self.ball_scale = start_scale + (target_scale - start_scale) * progress
                
                # Verificar si llegó al objetivo
                if progress >= 1.0:
                    self.ball_launching = False
                    self.ball_moving = False
                    self.misses += 1
                    print(f"¡Fallaste! Llevas {self.misses}/{self.max_misses} fallos")
                    self._reset_ball_position()  # Esto la reseteará a escala 0.2
                    
                    # Verificar si se perdió el juego -> activar game over
                    if self.misses >= self.max_misses:
                        self.game_over = True
                        pygame.mixer.music.stop()
                        if self.game_over_sound:
                            self.game_over_sound.play()
                        print("¡Juego terminado! Has perdido.")

        # Dibujar sobre el canvas lógico (sin cambio)
        self.canvas.blit(self.background, (0, 0))

        # Pelota animada (sin cambio)
        if self.ball_rotating:
            self.ball_animation.update()

        # Reutilizar superficie temporal para la pelota (sin cambio)
        self._ball_surface.fill((0, 0, 0, 0))
        self.ball_animation.draw(self._ball_surface, 0, 0)

        # Centro según tamaño base (sin cambio)
        cx = int(self.ball_x + self.ball_w / 2)
        cy = int(self.ball_y + self.ball_h / 2)

        # Dibujar pelota con rotación y escalado (sin cambio en la lógica de dibujo)
        if self.ball_rotating:
            self.ball_angle = (self.ball_angle + self.ball_rotation_speed) % 360
            if abs(self.ball_scale - 1.0) < 1e-6:
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
                scaled = pygame.transform.scale(self._ball_surface, (int(self.ball_w * self.ball_scale), int(self.ball_h * self.ball_scale)))
                rect = scaled.get_rect(center=(cx, cy))
                self.canvas.blit(scaled, rect.topleft)
            else:
                self.canvas.blit(self._ball_surface, (self.ball_x, self.ball_y))

        # Preparar hitboxes (sin cambio)
        right_rect = self._hand_rect_from_center(right_pos)
        left_rect = self._hand_rect_from_center(left_pos)
        ball_rect = self._ball_rect()

        # Manos (sin cambio)
        if right_rect is not None:
            self.canvas.blit(self.right_hand_img, right_rect.topleft)
        if left_rect is not None:
            self.canvas.blit(self.left_hand_img, left_rect.topleft)

        # Colisiones - SOLO cuando la pelota está en escala completa (MODIFICADO)
        collided = False
        if not self.game_over:
            if right_rect is not None and self._check_ball_catch(right_rect, ball_rect):
                self._handle_collision("Right", right_rect, ball_rect)
                collided = True
                self.score += 1
                print(f"¡Atrapado con mano derecha! Puntuación: {self.score}")
                self._reset_ball_position()  # Esto la reseteará a escala 0.2
                
            elif left_rect is not None and self._check_ball_catch(left_rect, ball_rect):
                self._handle_collision("Left", left_rect, ball_rect)
                collided = True
                self.score += 1
                print(f"¡Atrapado con mano izquierda! Puntuación: {self.score}")
                self._reset_ball_position()  # Esto la reseteará a escala 0.2

        # Mostrar hitboxes si corresponde (sin cambio)
        if self.show_hitboxes:
            now = pygame.time.get_ticks()
            recent_collision = (now - self.last_collision_time) <= self.collision_flash_ms
            box_color = (255, 0, 0) if recent_collision else (255, 255, 255)
            if right_rect is not None:
                pygame.draw.rect(self.canvas, box_color, right_rect, 2)
            if left_rect is not None:
                pygame.draw.rect(self.canvas, box_color, left_rect, 2)
            pygame.draw.rect(self.canvas, box_color, ball_rect, 2)

        # Mostrar información de puntuación
        font = pygame.font.Font(None, 36)
        # dibujar goles (número)
        score_text = font.render(str(self.score), True, (255, 255, 255))
        score_rect = score_text.get_rect(midleft=self.score_pos)
        self.canvas.blit(score_text, score_rect.topleft)

        # dibujar derrotas como X rojas verticales a la derecha del marcador
        icon_x, icon_y = self.misses_icons_origin
        size = self.miss_icon_size
        gap = self.miss_icon_spacing
        for i in range(self.max_misses):
            y = icon_y + i * (size + gap)
            rect = pygame.Rect(icon_x, y, size, size)
            # sólo dibujar X si ese índice corresponde a un fallo ya ocurrido
            if i < self.misses:
                c = self.miss_icon_color
                # dibujar X con 3px de grosor
                pygame.draw.line(self.canvas, c, rect.topleft, rect.bottomright, 3)
                pygame.draw.line(self.canvas, c, (rect.left, rect.bottom), (rect.right, rect.top), 3)
            # si no hay fallo todavía, no dibujamos nada (espacio oculto)

        # Mostrar indicador de trayectoria (DEBUG - opcional)
        if self.ball_launching and self.show_hitboxes:
            # Dibujar línea de trayectoria
            start_pos = (int(self._move_start_x), int(self._move_start_y))
            end_pos = (int(self.ball_target_x), int(self.ball_target_y))
            if self.curve_strength > 0:
                # Dibujar curva Bézier
                points = []
                for t in range(0, 101, 5):
                    progress = t / 100.0
                    x, y = self._calculate_bezier_point(
                        progress, self._move_start_x, self._move_start_y,
                        self.control_point_x, self.control_point_y,
                        self.ball_target_x, self.ball_target_y
                    )
                    points.append((int(x), int(y)))
                if len(points) > 1:
                    pygame.draw.lines(self.canvas, (0, 255, 0), False, points, 1)
            else:
                pygame.draw.line(self.canvas, (0, 255, 0), start_pos, end_pos, 1)

        # Presentación (sin cambio)
        if self.is_fullscreen:
            scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, (self.offset_x, self.offset_y))
        else:
            self.screen.blit(self.canvas, (0, 0))

        # Si estamos en estado de game over, dibujar overlay con la imagen y pedir ENTER para reiniciar
        if self.game_over:
            # Semitransparencia sobre el canvas
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.canvas.blit(overlay, (0, 0))

            if self.game_over_image is not None:
                iw, ih = self.game_over_image.get_size()
                go_x = (self.width - iw) // 2
                go_y = (self.height - ih) // 2
                self.canvas.blit(self.game_over_image, (go_x, go_y))
                instr = self.game_over_instr_font.render("Pulsa ENTER para reiniciar", True, (240, 240, 240))
                instr_rect = instr.get_rect(center=(self.width//2, go_y + ih + 24))
                self.canvas.blit(instr, instr_rect.topleft)
            else:
                # Texto grande centrado como fallback
                go_text = self.game_over_font.render("GAME OVER", True, (255, 40, 40))
                g_rect = go_text.get_rect(center=(self.width // 2, self.height // 2 - 20))
                self.canvas.blit(go_text, g_rect.topleft)
                instr = self.game_over_instr_font.render("Pulsa ENTER para reiniciar", True, (240, 240, 240))
                instr_rect = instr.get_rect(center=(self.width // 2, self.height // 2 + 40))
                self.canvas.blit(instr, instr_rect.topleft)

            # Re-blit final (para fullscreen se escala la canvas ya actualizada)
            if self.is_fullscreen:
                scaled = pygame.transform.smoothscale(self.canvas, self.scaled_size)
                self.screen.fill((0, 0, 0))
                self.screen.blit(scaled, (self.offset_x, self.offset_y))
            else:
                self.screen.blit(self.canvas, (0, 0))

            pygame.display.flip()
            self.clock.tick(30)
            return True

        # Auto-launch después de que la pelota se haya reseteado (si está habilitado)
        now = pygame.time.get_ticks()
        if self.auto_launch_enabled and not self.ball_launching and not self.ball_moving and not self.game_over:
            if now - self._last_reset_time >= self.auto_launch_delay_ms:
                self._launch_ball_to_random_target()

        pygame.display.flip()
        # Limitar FPS (sin cambio)
        self.clock.tick(60)  # Aumentado a 60 FPS para movimiento más suave
        return True

    def cleanup(self) -> None:
        # sin cambio
        pygame.quit()