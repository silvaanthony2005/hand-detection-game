import cv2
import numpy as np
import os

class GameRenderer:
    def __init__(self, camera_width=640, camera_height=480, window_name='Hand Detection Game'):
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.window_name = window_name
        self.is_fullscreen = False

        # Cargar imágenes desde la carpeta Images
        image_folder = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Images"))
        self.background = cv2.imread(os.path.join(image_folder, "background.jpg"))
        self.right_hand_image = cv2.imread(os.path.join(image_folder, "right_hand.png"), cv2.IMREAD_UNCHANGED)
        self.left_hand_image = cv2.imread(os.path.join(image_folder, "left_hand.png"), cv2.IMREAD_UNCHANGED)
        self.pelota = cv2.imread(os.path.join(image_folder, "pelota.png"), cv2.IMREAD_UNCHANGED)

        # Redimensionar fondo
        if self.background is None:
            self.background = np.zeros((self.camera_height, self.camera_width, 3), dtype=np.uint8)
        else:
            self.background = cv2.resize(self.background, (self.camera_width, self.camera_height))

        # Redimensionar overlays si existen
        def resize_if(img, size):
            return cv2.resize(img, size) if img is not None else None

        self.right_hand_image = resize_if(self.right_hand_image, (120, 120))
        self.left_hand_image = resize_if(self.left_hand_image, (120, 120))
        self.pelota = resize_if(self.pelota, (120, 120))

        if self.pelota is None:
            print("ERROR: No se pudo cargar la pelota")
        else:
            print(f"Pelota cargada - Shape: {self.pelota.shape}")

        # Ventana
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    @staticmethod
    def overlay_image(background, overlay, x, y):
        if overlay is None:
            return
        h, w = overlay.shape[:2]

        # Recortar si se sale del lienzo
        if x < 0 or y < 0 or x + w > background.shape[1] or y + h > background.shape[0]:
            x0 = max(0, x); y0 = max(0, y)
            x1 = min(background.shape[1], x + w); y1 = min(background.shape[0], y + h)
            if x0 >= x1 or y0 >= y1:
                return
            overlay = overlay[y0 - y:y1 - y, x0 - x:x1 - x]
            x = x0; y = y0; h, w = overlay.shape[:2]

        if overlay.shape[2] == 4:
            overlay_image = overlay[:, :, :3]
            mask = overlay[:, :, 3:] / 255.0
            roi = background[y:y+h, x:x+w]
            background[y:y+h, x:x+w] = (1.0 - mask) * roi + mask * overlay_image
        else:
            background[y:y+h, x:x+w] = overlay

    def render(self, right_pos=None, left_pos=None):
        # Componer el frame
        game_frame = self.background.copy()

        # Pelota centrada
        if self.pelota is not None:
            px = (self.camera_width - self.pelota.shape[1]) // 2
            py = (self.camera_height - self.pelota.shape[0]) // 2
            self.overlay_image(game_frame, self.pelota, px, py)

        # Manos encima
        if right_pos:
            self.overlay_image(game_frame, self.right_hand_image, right_pos[0], right_pos[1])
        if left_pos:
            self.overlay_image(game_frame, self.left_hand_image, left_pos[0], left_pos[1])

        # Mostrar y manejar eventos
        cv2.imshow(self.window_name, game_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return False
        if key == ord('f'):
            self.is_fullscreen = not self.is_fullscreen
            if self.is_fullscreen:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        return True

    def cleanup(self):
        cv2.destroyWindow(self.window_name)