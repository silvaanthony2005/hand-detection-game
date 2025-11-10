import cv2
from Controler.optimized_tracker import OptimizedHandTracker
from vista.pygame_renderer import PygameRenderer

# Tamaño de cámara reducido para mejor rendimiento
camera_width, camera_height = 640, 480

# Parámetros de MediaPipe optimizados
min_detection_confidence = 0.5  # Aumentado para menos falsos positivos
min_tracking_confidence = 0.5   # Aumentado para tracking más estable

# Configuración de la UI
renderer = PygameRenderer(camera_width=camera_width, camera_height=camera_height, title='Hand Detection Game')

# Captura de cámara optimizada
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
cap.set(cv2.CAP_PROP_FPS, 60)  # Limitar FPS de cámara
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# Reducir buffer al mínimo
try:
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
except Exception:
    pass

# Tracker optimizado con parámetros mejorados
tracker = OptimizedHandTracker(
    camera_width=camera_width,
    camera_height=camera_height,
    max_num_hands=2,
    min_detection_confidence=min_detection_confidence,
    min_tracking_confidence=min_tracking_confidence,
    buffer_size=3,  # Reducido para menor latencia
    smoothing='ema',  # Usar EMA para respuesta más rápida
    ema_alpha=0.6,   # Alpha más alto para respuesta más rápida
    max_delta_px=35, # Aumentado para movimientos más rápidos
    model_complexity=0  # Modelo más simple para mejor rendimiento
)

# Variables para almacenar las últimas posiciones conocidas
last_right_hand_position = None
last_left_hand_position = None

print("Iniciando detección de manos...")
print("Presiona 'q' para salir, '1' para mostrar hitboxes")

try:
    while cap.isOpened():
        # Leer frame sin procesar primero
        ret = cap.grab()
        if not ret:
            break
            
        # Recuperar frame
        ret, frame = cap.retrieve()
        if not ret:
            break

        # Espejar frame horizontalmente
        frame = cv2.flip(frame, 1)

        # Procesar frame con el tracker
        right_pos, left_pos = tracker.process_frame(frame)

        # Actualizar posiciones persistentes
        if right_pos:
            last_right_hand_position = right_pos
        if left_pos:
            last_left_hand_position = left_pos

        # Renderizar (UI y eventos dentro del renderer)
        if not renderer.render(last_right_hand_position, last_left_hand_position):
            break

except KeyboardInterrupt:
    print("Interrupción por teclado")
finally:
    # Limpieza garantizada
    print("Liberando recursos...")
    cap.release()
    tracker.release()
    renderer.cleanup()
    
    # Limpieza de memoria
    try:
        import gc
        gc.collect()
    except Exception:
        pass
    
    print("Recursos liberados correctamente")