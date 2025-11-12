import cv2
from Controler.optimized_tracker import OptimizedHandTracker
from vista.pygame_renderer import PygameRenderer

# Configuración básica

camera_width, camera_height = 640, 480
renderer = PygameRenderer(camera_width=camera_width, camera_height=camera_height, title='Hand Detection Game')

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)

tracker = OptimizedHandTracker(
    camera_width=camera_width,
    camera_height=camera_height,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    smoothness_level=0.92,  # ¡Ultra-suave!
    model_complexity=0
)

print("Modo simple: Una mano controla ambos guantes")

# Variable para recordar la última posición de la mano y evitar que los guantes desaparezcan
last_known_hand_pos = None

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        right_pos, left_pos = tracker.process_frame(frame)

        # Determinar la posición de la mano detectada
        current_hand_pos = None
        if right_pos or left_pos:
            # Priorizar la mano izquierda para un control más consistente
            current_hand_pos = left_pos if left_pos else right_pos
            last_known_hand_pos = current_hand_pos  # Actualizar la última posición conocida

        # Usar la última posición conocida si no se detecta ninguna mano en este frame
        final_hand_pos = current_hand_pos if current_hand_pos else last_known_hand_pos

        if final_hand_pos:
            x, y = final_hand_pos
            # Calcular la posición de ambos guantes a partir de la posición de la mano
            right_pos = (min(camera_width - renderer.hand_w // 2, x + 60), y)
            left_pos = (max(renderer.hand_w // 2, x - 60), y)

        if not renderer.render(right_pos, left_pos):
            break

except Exception as e:
    print(f"Error: {e}")
finally:
    cap.release()
    tracker.release()
    renderer.cleanup()