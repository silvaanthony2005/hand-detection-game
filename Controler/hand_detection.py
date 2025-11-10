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

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        right_pos, left_pos = tracker.process_frame(frame)

        # SIEMPRE mostrar ambos guantes juntos
        if right_pos or left_pos:
            # Usar la mano detectada (cualquiera que sea)
            hand_pos = right_pos if right_pos else left_pos
            x, y = hand_pos
            
            # Ambos guantes separados por 120 píxeles
            right_pos = (min(camera_width, x + 60), y)
            left_pos = (max(0, x - 60), y)

        if not renderer.render(right_pos, left_pos):
            break

except Exception as e:
    print(f"Error: {e}")
finally:
    cap.release()
    tracker.release()
    renderer.cleanup()