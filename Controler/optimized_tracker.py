import time
from collections import deque
import cv2
import mediapipe as mp
import numpy as np

class HandSmoother:
    """Media móvil optimizada."""
    def __init__(self, buffer_size=3):  # Buffer reducido
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
        # Promedio simple sin pesos para menor overhead
        sx = sum(p[0] for p in buf) / len(buf)
        sy = sum(p[1] for p in buf) / len(buf)
        return (sx, sy)


class ExponentialSmoother:
    """Suavizado exponencial optimizado."""
    def __init__(self, alpha=0.6):  # Alpha más alto para respuesta más rápida
        self.alpha = alpha
        self.prev = {'Right': None, 'Left': None}

    def update(self, label, current):
        if current is None:
            return self.prev[label]
        prev = self.prev[label]
        if prev is None:
            smoothed = current
        else:
            # Cálculo optimizado
            ax = self.alpha * current[0] + (1 - self.alpha) * prev[0]
            ay = self.alpha * current[1] + (1 - self.alpha) * prev[1]
            smoothed = (ax, ay)
        self.prev[label] = smoothed
        return smoothed

class HandTracker:
    def __init__(self, max_missed=5):  # Reducido para respuesta más rápida
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
                 camera_width=640,  # Valores por defecto reducidos
                 camera_height=480,
                 max_num_hands=2,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 buffer_size=3,      # Buffer reducido
                 smoothing='ema',    # EMA por defecto (más rápido)
                 ema_alpha=0.6,      # Respuesta más rápida
                 max_delta_px=35,    # Permitir movimientos más rápidos
                 model_complexity=0, # Modelo más simple
                 static_image_mode=False):
        
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity  # Modelo más simple
        )
        
        self.smoother = HandSmoother(buffer_size=buffer_size)
        self.ema = ExponentialSmoother(alpha=ema_alpha)
        self.tracker = HandTracker()
        self.smoothing_mode = smoothing
        self.max_delta_px = max_delta_px
        self._last_right = None
        self._last_left = None
        
        # Optimizaciones de OpenCV
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(4)  # Usar 4 threads para procesamiento
        except Exception:
            pass

    def _palm_center_fast(self, landmarks):
        """Centro de palma optimizado usando menos puntos."""
        # Usar solo wrist, MCP índice y MCP meñique para mayor velocidad
        idxs = [0, 5, 17]  # wrist, MCP índice, MCP meñique
        xs = [landmarks[i].x for i in idxs]
        ys = [landmarks[i].y for i in idxs]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    @staticmethod
    def _clamp_delta_fast(prev, curr, max_d):
        """Versión optimizada de clamp delta."""
        if prev is None or curr is None:
            return curr
        
        dx = curr[0] - prev[0]
        dy = curr[1] - prev[1]
        
        # Usar distancia Manhattan para mayor velocidad
        if abs(dx) > max_d or abs(dy) > max_d:
            dx = max(-max_d, min(max_d, dx))
            dy = max(-max_d, min(max_d, dy))
            return (int(prev[0] + dx), int(prev[1] + dy))
        return curr

    def process_frame(self, frame):
        """Procesamiento de frame optimizado."""
        # Redimensionar frame para procesamiento más rápido
        if frame.shape[1] != self.camera_width or frame.shape[0] != self.camera_height:
            frame = cv2.resize(frame, (self.camera_width, self.camera_height))
        
        # Convertir a RGB (más eficiente que procesar BGR directamente)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Procesar con MediaPipe
        results = self.hands.process(rgb)

        detected = {'Right': None, 'Left': None}

        if results.multi_hand_landmarks and results.multi_handedness:
            for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                
                # Centro de palma optimizado
                x_norm, y_norm = self._palm_center_fast(lm.landmark)
                
                # Suavizado temporal
                if self.smoothing_mode == 'mean':
                    self.smoother.add(label, (x_norm, y_norm))
                    s = self.smoother.get(label)
                else:  # 'ema' (más rápido)
                    s = self.ema.update(label, (x_norm, y_norm))
                
                if s is not None:
                    # Convertir a píxeles
                    px = int(s[0] * self.camera_width)
                    py = int(s[1] * self.camera_height)
                    
                    # Limitar dentro del canvas (más rápido que min/max individual)
                    px = max(0, min(px, self.camera_width - 1))
                    py = max(0, min(py, self.camera_height - 1))
                    
                    detected[label] = (px, py)

        # Actualizar trackers
        right_raw = self.tracker.update('Right', detected.get('Right'))
        left_raw = self.tracker.update('Left', detected.get('Left'))

        # Limitar saltos por frame
        right = self._clamp_delta_fast(self._last_right, right_raw, self.max_delta_px)
        left = self._clamp_delta_fast(self._last_left, left_raw, self.max_delta_px)
        
        self._last_right = right
        self._last_left = left

        return right, left

    def release(self):
        """Liberación de recursos optimizada."""
        try:
            if hasattr(self, 'hands') and self.hands is not None:
                self.hands.close()
        except Exception:
            pass
        
        # Limpieza agresiva
        try:
            self.smoother.buffers.clear()
            self.hands = None
            self.mp_hands = None
            self.smoother = None
            self.tracker = None
        except Exception:
            pass
        
        # Forzar recolección de basura
        try:
            import gc
            gc.collect()
        except Exception:
            pass