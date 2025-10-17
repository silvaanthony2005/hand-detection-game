import cv2
import mediapipe as mp
import numpy as np
import os

# Inicialización de MediaPipe
mp_hands = mp.solutions.hands

# Cargar imágenes
image_folder = "../images"
background = cv2.imread(os.path.join(image_folder, "background.jpg"))
right_hand_image = cv2.imread(os.path.join(image_folder, "right_hand.png"), cv2.IMREAD_UNCHANGED)
left_hand_image = cv2.imread(os.path.join(image_folder, "left_hand.png"), cv2.IMREAD_UNCHANGED)
pelota = cv2.imread(os.path.join(image_folder, "pelota.png"), cv2.IMREAD_UNCHANGED)

# Redimensionar el fondo y las imágenes de los guantes
camera_width, camera_height = 640, 480
background = cv2.resize(background, (camera_width, camera_height))
right_hand_image = cv2.resize(right_hand_image, (120, 120))  # Ajustar tamaño del guante derecho
left_hand_image = cv2.resize(left_hand_image, (120, 120))  # Ajustar tamaño del guante izquierdo
pelota = cv2.resize(pelota, (120, 120))  # Ajustar tamaño de la pelota
if pelota is None:
    print("ERROR: No se pudo cargar la pelota")
else:
    print(f"Pelota cargada - Shape: {pelota.shape}")

# Función para superponer imágenes con canal alfa
def overlay_image(background, overlay, x, y):
    h, w, _ = overlay.shape
    overlay_image = overlay[:, :, :3]
    mask = overlay[:, :, 3:] / 255.0
    try:
        background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image
    except ValueError:
        pass  # Evitar errores si las coordenadas están fuera de los límites

# Variables para almacenar las últimas posiciones conocidas
last_right_hand_position = None
last_left_hand_position = None

# Parámetros de MediaPipe
min_detection_confidence = 0.8
min_tracking_confidence = 0.8

# Configuración inicial de la ventana
window_name = 'Hand Detection Game'
is_fullscreen = False  # Inicia en modo ventana

cap = cv2.VideoCapture(0)

cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)  # Permitir redimensionar la ventana

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=min_detection_confidence,
    min_tracking_confidence=min_tracking_confidence
) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Procesar el cuadro para detectar manos
        results = hands.process(rgb_frame)

        # Usar la imagen de fondo
        game_frame = background.copy()

        # Variables temporales para las posiciones actuales
        current_right_hand_position = None
        current_left_hand_position = None

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # Obtener la posición de la muñeca (landmark 0)
                wrist = hand_landmarks.landmark[0]
                wrist_x = int(wrist.x * camera_width)
                wrist_y = int(wrist.y * camera_height)

                # Ajustar las coordenadas para que no salgan del área visible
                wrist_x = max(0, min(wrist_x, camera_width - 120))  # Ajustar al tamaño del guante
                wrist_y = max(0, min(wrist_y, camera_height - 120))

                # Determinar si es la mano derecha o izquierda
                if handedness.classification[0].label == "Right":
                    current_right_hand_position = (wrist_x, wrist_y)
                else:
                    current_left_hand_position = (wrist_x, wrist_y)

        # Actualizar las posiciones persistentes solo si hay detección
        if current_right_hand_position:
            last_right_hand_position = current_right_hand_position
        if current_left_hand_position:
            last_left_hand_position = current_left_hand_position

        # Dibujar los guantes en las últimas posiciones conocidas
        if last_right_hand_position:
            overlay_image(game_frame, right_hand_image, last_right_hand_position[0], last_right_hand_position[1])
        if last_left_hand_position:
            overlay_image(game_frame, left_hand_image, last_left_hand_position[0], last_left_hand_position[1])

        # Mostrar el cuadro con las imágenes superpuestas
        cv2.imshow(window_name, game_frame)

        # Manejar eventos de teclado
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # Presiona ESC para salir
            break
        elif key == ord('f'):  # Presiona 'f' para alternar entre ventana y pantalla completa
            is_fullscreen = not is_fullscreen
            if is_fullscreen:
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

cap.release()
cv2.destroyAllWindows()