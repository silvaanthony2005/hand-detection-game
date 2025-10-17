import cv2
import mediapipe as mp
from vista.game_render import GameRenderer

# Inicialización de MediaPipe
mp_hands = mp.solutions.hands

# Tamaño de cámara (también usado por el renderizador)
camera_width, camera_height = 640, 480

# Parámetros de MediaPipe
min_detection_confidence = 0.7
min_tracking_confidence = 0.7

# Configuración de la UI (manejada por GameRenderer)
window_name = 'Hand Detection Game'
renderer = GameRenderer(camera_width=camera_width, camera_height=camera_height, window_name=window_name)

# Captura de cámara
cap = cv2.VideoCapture(0)

# Variables para almacenar las últimas posiciones conocidas
last_right_hand_position = None
last_left_hand_position = None

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

        # Variables temporales para las posiciones actuales
        current_right_hand_position = None
        current_left_hand_position = None

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                # Muñeca (landmark 0)
                wrist = hand_landmarks.landmark[0]
                wrist_x = int(wrist.x * camera_width)
                wrist_y = int(wrist.y * camera_height)

                # Limitar al área visible (tamaño de guante 120x120)
                wrist_x = max(0, min(wrist_x, camera_width - 120))
                wrist_y = max(0, min(wrist_y, camera_height - 120))

                if handedness.classification[0].label == "Right":
                    current_right_hand_position = (wrist_x, wrist_y)
                else:
                    current_left_hand_position = (wrist_x, wrist_y)

        # Actualizar posiciones persistentes
        if current_right_hand_position:
            last_right_hand_position = current_right_hand_position
        if current_left_hand_position:
            last_left_hand_position = current_left_hand_position

        # Renderizar (UI y eventos dentro del renderer)
        if not renderer.render(last_right_hand_position, last_left_hand_position):
            break

cap.release()
renderer.cleanup()