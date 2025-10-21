import time
from collections import deque
import cv2
import mediapipe as mp

class HandSmoother:
    def __init__(self, buffer_size=5):
        self.buffer_size = buffer_size
        self.buffers = {}  # label -> deque of (x,y)

    def add(self, label, pos):
        if pos is None:
            return
        if label not in self.buffers:
            self.buffers[label] = deque(maxlen=self.buffer_size)
        self.buffers[label].append(pos)

    def get(self, label):
        buf = self.buffers.get(label)
        if not buf:
            return None
        sx = sum(p[0] for p in buf) / len(buf)
        sy = sum(p[1] for p in buf) / len(buf)
        return (sx, sy)

class HandTracker:
    def __init__(self, max_missed=8):
        self.last = {'Right': None, 'Left': None}
        self.missed = {'Right': 0, 'Left': 0}
        self.max_missed = max_missed

    def update(self, label, pos):
        if pos is None:
            self.missed[label] += 1
            if self.missed[label] > self.max_missed:
                self.last[label] = None
            return self.last[label]
        # new detection
        self.last[label] = pos
        self.missed[label] = 0
        return pos

class OptimizedHandTracker:
    def __init__(self,
                 camera_width=640,
                 camera_height=480,
                 max_num_hands=2,
                 min_detection_confidence=0.4,
                 min_tracking_confidence=0.4,
                 buffer_size=5):
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=0
        )
        self.smoother = HandSmoother(buffer_size=buffer_size)
        self.tracker = HandTracker()

    def process_frame(self, frame):
        # Resize to target camera size for consistent coordinates + speed
        small = cv2.resize(frame, (self.camera_width, self.camera_height))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        detected = {'Right': None, 'Left': None}

        if results.multi_hand_landmarks and results.multi_handedness:
            for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label  # "Right" / "Left"
                wrist = lm.landmark[0]
                # Normalized coords -> pixeles usando el tamaño objetivo
                x_norm = wrist.x
                y_norm = wrist.y
                # Guardar normalizado para suavizar
                self.smoother.add(label, (x_norm, y_norm))
                smoothed = self.smoother.get(label)
                if smoothed is not None:
                    px = int(smoothed[0] * self.camera_width)
                    py = int(smoothed[1] * self.camera_height)
                    # Limitar dentro del canvas
                    px = max(0, min(px, self.camera_width - 1))
                    py = max(0, min(py, self.camera_height - 1))
                    detected[label] = (px, py)

        # Actualizar trackers individuales y devolver posiciones finales
        right = self.tracker.update('Right', detected.get('Right'))
        left = self.tracker.update('Left', detected.get('Left'))

        return right, left

    def release(self):
        # Liberar recursos de MediaPipe y limpiar buffers para reducir uso de RAM
        try:
            if hasattr(self, 'hands') and self.hands is not None:
                self.hands.close()
        except Exception:
            pass
        # Vaciar buffers y referencias
        try:
            self.smoother.buffers.clear()
        except Exception:
            pass
        try:
            self.hands = None
            self.mp_hands = None
            self.smoother = None
            self.tracker = None
        except Exception:
            pass
        # Forzar recolección de basura como última medida (útil en equipos con poca RAM)
        try:
            import gc
            gc.collect()
        except Exception:
            pass