import cv2
from Controler.optimized_tracker import OptimizedHandTracker
from vista.game_render import GameRenderer

# Tamaño de cámara (también usado por el renderizador)
camera_width, camera_height = 640, 480

# Parámetros de MediaPipe (se pasan al tracker)
min_detection_confidence = 0.4
min_tracking_confidence = 0.4

# Configuración de la UI (manejada por GameRenderer)
window_name = 'Hand Detection Game'
renderer = GameRenderer(camera_width=camera_width, camera_height=camera_height, window_name=window_name)

# Captura de cámara
cap = cv2.VideoCapture(0)

# Optimized tracker
tracker = OptimizedHandTracker(
    camera_width=camera_width,
    camera_height=camera_height,
    max_num_hands=2,
    min_detection_confidence=min_detection_confidence,
    min_tracking_confidence=min_tracking_confidence,
    buffer_size=5
)

# Variables para almacenar las últimas posiciones conocidas
last_right_hand_position = None
last_left_hand_position = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    # Usar el tracker optimizado (devuelve en pixeles ya ajustados)
    right_pos, left_pos = tracker.process_frame(frame)

    # Actualizar posiciones persistentes
    if right_pos:
        last_right_hand_position = right_pos
    if left_pos:
        last_left_hand_position = left_pos

    # Renderizar (UI y eventos dentro del renderer)
    if not renderer.render(last_right_hand_position, last_left_hand_position):
        break

cap.release()
tracker.release()
renderer.cleanup()