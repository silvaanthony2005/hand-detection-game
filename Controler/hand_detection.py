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

# --- Sistema de detección robusto con memoria ---
last_known_hand_pos = None  # Última posición válida conocida
last_active_hand_label = None # 'Right' o 'Left', para dar prioridad

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        right_pos, left_pos = tracker.process_frame(frame)

        # --- Lógica de selección de mano activa ---
        active_hand_pos = None

        # Caso 1: Ambas manos detectadas. Priorizar la última que estuvo activa.
        if right_pos and left_pos:
            if last_active_hand_label == 'Left':
                active_hand_pos = left_pos
            else: # Si es 'Right' o None, se prefiere la derecha por defecto
                active_hand_pos = right_pos
                last_active_hand_label = 'Right'
        # Caso 2: Solo se detecta la mano izquierda.
        elif left_pos:
            active_hand_pos = left_pos
            last_active_hand_label = 'Left'
        # Caso 3: Solo se detecta la mano derecha.
        elif right_pos:
            active_hand_pos = right_pos
            last_active_hand_label = 'Right'

        # Actualizar la última posición conocida si tenemos una mano activa
        if active_hand_pos:
            last_known_hand_pos = active_hand_pos

        # Si hay una posición final (ya sea de este frame o una recordada), calcular la posición de los guantes
        if last_known_hand_pos:
            x, y = last_known_hand_pos
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