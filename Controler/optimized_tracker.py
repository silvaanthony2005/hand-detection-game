import time
from collections import deque
import cv2
import mediapipe as mp

class HandSmoother:
    """Media móvil simple (promedio ventana)."""
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


class ExponentialSmoother:
    """Suavizado exponencial simple por mano."""
    def __init__(self, alpha=0.4):
        self.alpha = alpha
        self.prev = {'Right': None, 'Left': None}

    def update(self, label, current):
        if current is None:
            return self.prev[label]
        prev = self.prev[label]
        if prev is None:
            smoothed = current
        else:
            ax = self.alpha * current[0] + (1 - self.alpha) * prev[0]
            ay = self.alpha * current[1] + (1 - self.alpha) * prev[1]
            smoothed = (ax, ay)
        self.prev[label] = smoothed
        return smoothed

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
                 buffer_size=5,
                 smoothing='ema',
                 ema_alpha=0.4,
                 max_delta_px=25,
                 model_complexity=1):
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity
        )
        self.smoother = HandSmoother(buffer_size=buffer_size)
        self.ema = ExponentialSmoother(alpha=ema_alpha)
        self.tracker = HandTracker()
        self.smoothing_mode = smoothing  # 'ema' o 'mean'
        self.max_delta_px = max_delta_px
        self._last_right = None
        self._last_left = None
        try:
            cv2.setUseOptimized(True)
        except Exception:
            pass

    def _palm_center_norm(self, landmarks):
        """Centro de la palma normalizado promediando wrist+MCPs para mayor estabilidad."""
        idxs = [0, 5, 9, 13, 17]
        xs = [landmarks[i].x for i in idxs]
        ys = [landmarks[i].y for i in idxs]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    @staticmethod
    def _clamp_delta(prev, curr, max_d):
        if prev is None or curr is None:
            return curr
        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        if abs(dx) > max_d or abs(dy) > max_d:
            # limitar delta por componente
            from math import copysign
            dx = copysign(min(abs(dx), max_d), dx)
            dy = copysign(min(abs(dy), max_d), dy)
            return (int(prev[0] + dx), int(prev[1] + dy))
        return curr

    def process_frame(self, frame):
        # Resize to target camera size for consistent coordinates + speed
        small = cv2.resize(frame, (self.camera_width, self.camera_height))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        detected = {'Right': None, 'Left': None}

        if results.multi_hand_landmarks and results.multi_handedness:
            for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label  # "Right" / "Left"
                # Centro de la palma (más estable que sólo wrist)
                x_norm, y_norm = self._palm_center_norm(lm.landmark)
                # Suavizado temporal
                if self.smoothing_mode == 'mean':
                    self.smoother.add(label, (x_norm, y_norm))
                    s = self.smoother.get(label)
                else:  # 'ema'
                    s = self.ema.update(label, (x_norm, y_norm))
                if s is not None:
                    px = int(s[0] * self.camera_width)
                    py = int(s[1] * self.camera_height)
                    # Limitar dentro del canvas
                    px = max(0, min(px, self.camera_width - 1))
                    py = max(0, min(py, self.camera_height - 1))
                    detected[label] = (px, py)

        # Actualizar trackers individuales y devolver posiciones finales
        right_raw = self.tracker.update('Right', detected.get('Right'))
        left_raw = self.tracker.update('Left', detected.get('Left'))

        # Limitar saltos por frame (clamp de velocidad)
        right = self._clamp_delta(getattr(self, '_last_right', None), right_raw, self.max_delta_px)
        left = self._clamp_delta(getattr(self, '_last_left', None), left_raw, self.max_delta_px)
        self._last_right = right
        self._last_left = left

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