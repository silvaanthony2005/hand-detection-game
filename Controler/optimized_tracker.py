import time
from collections import deque
import cv2
import mediapipe as mp
import numpy as np
import math

class UltraSmoothFilter:
    """Filtro ultra-suave que elimina tirones y movimientos bruscos"""
    def __init__(self, smoothness=0.85, max_prediction=0.3):
        self.smoothness = smoothness  # 0-1: más alto = más suave
        self.max_prediction = max_prediction
        self.position_history = deque(maxlen=8)  # Historial más largo
        self.velocity_history = deque(maxlen=5)
        self.acceleration_history = deque(maxlen=3)
        self.last_raw_position = None
        self.last_time = time.time()
        
    def update(self, new_position):
        current_time = time.time()
        
        if new_position is None:
            # Predicción avanzada cuando no hay detección
            return self._predict_position()
        
        # Detectar y filtrar tirones (movimientos físicamente imposibles)
        if self.last_raw_position and len(self.position_history) > 1:
            if self._is_jerk_movement(new_position):
                # Ignorar movimiento brusco y usar predicción
                print("Movimiento brusco detectado - aplicando filtro")
                return self._predict_position()
        
        self.last_raw_position = new_position
        
        # Calcular derivadas (velocidad y aceleración)
        dt = max(0.001, current_time - self.last_time)
        velocity = self._calculate_velocity(new_position, dt)
        acceleration = self._calculate_acceleration(velocity, dt)
        
        # Suavizado multi-nivel
        smoothed_position = self._multi_level_smoothing(new_position, velocity, acceleration)
        
        self.last_time = current_time
        return smoothed_position
    
    def _is_jerk_movement(self, new_position):
        """Detectar movimientos físicamente imposibles (tirones)"""
        if len(self.position_history) < 2:
            return False
            
        # Calcular distancia y velocidad instantánea
        last_pos = self.position_history[-1]
        dx = new_position[0] - last_pos[0]
        dy = new_position[1] - last_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Velocidad máxima razonable (píxeles por segundo)
        max_reasonable_speed = 800  # Ajustado para movimientos rápidos pero realistas
        
        current_time = time.time()
        dt = current_time - self.last_time
        speed = distance / max(0.001, dt)
        
        # Si la velocidad es físicamente imposible, es un tirón
        return speed > max_reasonable_speed
    
    def _calculate_velocity(self, new_position, dt):
        """Calcular velocidad suavizada"""
        if not self.position_history:
            return (0, 0)
            
        last_pos = self.position_history[-1]
        instant_velocity = (
            (new_position[0] - last_pos[0]) / dt,
            (new_position[1] - last_pos[1]) / dt
        )
        
        # Suavizar velocidad
        self.velocity_history.append(instant_velocity)
        avg_velocity = np.mean(self.velocity_history, axis=0)
        
        return (float(avg_velocity[0]), float(avg_velocity[1]))
    
    def _calculate_acceleration(self, velocity, dt):
        """Calcular aceleración suavizada"""
        if len(self.velocity_history) < 2:
            return (0, 0)
            
        last_velocity = self.velocity_history[-2] if len(self.velocity_history) > 1 else (0, 0)
        instant_acceleration = (
            (velocity[0] - last_velocity[0]) / dt,
            (velocity[1] - last_velocity[1]) / dt
        )
        
        # Suavizar aceleración
        self.acceleration_history.append(instant_acceleration)
        avg_acceleration = np.mean(self.acceleration_history, axis=0)
        
        return (float(avg_acceleration[0]), float(avg_acceleration[1]))
    
    def _multi_level_smoothing(self, new_position, velocity, acceleration):
        """Suavizado multi-nivel para máxima fluidez"""
        # 1. Suavizado básico por posición
        if not self.position_history:
            smoothed = new_position
        else:
            last_smooth = self.position_history[-1]
            smoothed = (
                last_smooth[0] * (1 - self.smoothness) + new_position[0] * self.smoothness,
                last_smooth[1] * (1 - self.smoothness) + new_position[1] * self.smoothness
            )
        
        # 2. Aplicar corrección por inercia
        dt = time.time() - self.last_time
        inertia_corrected = (
            smoothed[0] + velocity[0] * dt * 0.1,  # Factor de inercia pequeño
            smoothed[1] + velocity[1] * dt * 0.1
        )
        
        # 3. Aplicar tendencia (predicción suave)
        trend_strength = min(self.max_prediction, abs(velocity[0] + velocity[1]) * 0.001)
        trend_corrected = (
            inertia_corrected[0] + velocity[0] * dt * trend_strength,
            inertia_corrected[1] + velocity[1] * dt * trend_strength
        )
        
        self.position_history.append(trend_corrected)
        return trend_corrected
    
    def _predict_position(self):
        """Predicción avanzada cuando no hay detección"""
        if len(self.position_history) < 2:
            return self.last_raw_position
            
        # Usar las últimas 2 posiciones para predecir
        pos1 = self.position_history[-1]
        pos2 = self.position_history[-2] if len(self.position_history) > 1 else pos1
        
        # Calcular velocidad de predicción
        dt = time.time() - self.last_time
        pred_velocity = (
            (pos1[0] - pos2[0]) / max(0.001, dt),
            (pos1[1] - pos2[1]) / max(0.001, dt)
        )
        
        # Aplicar predicción con decaimiento
        decay_factor = 0.7  # La predicción pierde fuerza con el tiempo
        predicted = (
            pos1[0] + pred_velocity[0] * dt * decay_factor,
            pos1[1] + pred_velocity[1] * dt * decay_factor
        )
        
        return predicted


class DoubleExponentialSmoother:
    """Suavizado exponencial doble para tendencias"""
    def __init__(self, alpha=0.8, beta=0.1):
        self.alpha = alpha  # Suavizado de posición
        self.beta = beta    # Suavizado de tendencia
        self.level = None
        self.trend = (0, 0)
        self.last_time = time.time()
        
    def update(self, new_position):
        if new_position is None:
            # Predicción basada en nivel + tendencia
            if self.level is None:
                return None
            dt = time.time() - self.last_time
            return (
                self.level[0] + self.trend[0] * dt,
                self.level[1] + self.trend[1] * dt
            )
        
        current_time = time.time()
        dt = max(0.001, current_time - self.last_time)
        
        if self.level is None:
            self.level = new_position
            self.trend = (0, 0)
        else:
            # Actualizar nivel
            new_level = (
                self.alpha * new_position[0] + (1 - self.alpha) * (self.level[0] + self.trend[0] * dt),
                self.alpha * new_position[1] + (1 - self.alpha) * (self.level[1] + self.trend[1] * dt)
            )
            
            # Actualizar tendencia
            new_trend = (
                self.beta * (new_level[0] - self.level[0]) / dt + (1 - self.beta) * self.trend[0],
                self.beta * (new_level[1] - self.level[1]) / dt + (1 - self.beta) * self.trend[1]
            )
            
            self.level = new_level
            self.trend = new_trend
        
        self.last_time = current_time
        return self.level


class OptimizedHandTracker:
    def __init__(self,
                 camera_width=480,
                 camera_height=360,
                 max_num_hands=1,
                 min_detection_confidence=0.5,
                 min_tracking_confidence=0.5,
                 smoothness_level=0.9,  # Nuevo: control de suavidad (0-1)
                 model_complexity=0,
                 static_image_mode=False):
        
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
            model_complexity=model_complexity
        )
        
        # Filtros ultra-suaves
        self.ultra_smooth_filters = {
            'Right': UltraSmoothFilter(smoothness=smoothness_level),
            'Left': UltraSmoothFilter(smoothness=smoothness_level)
        }
        
        self.double_smoothers = {
            'Right': DoubleExponentialSmoother(alpha=0.85, beta=0.05),
            'Left': DoubleExponentialSmoother(alpha=0.85, beta=0.05)
        }
        
        self.smoothness_level = smoothness_level
        self._last_positions = {'Right': None, 'Left': None}
        self._stability_counters = {'Right': 0, 'Left': 0}
        
        # Estadísticas para debug
        self.jerk_detections = 0
        self.total_frames = 0
        
        try:
            cv2.setUseOptimized(True)
            cv2.setNumThreads(4)
        except Exception:
            pass

    def _palm_center_fast(self, landmarks):
        """Centro de palma optimizado"""
        idxs = [0, 5, 17]
        xs = [landmarks[i].x for i in idxs]
        ys = [landmarks[i].y for i in idxs]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _apply_comfort_zone(self, label, position):
        """Crear zona de confort alrededor de la última posición estable"""
        if position is None or self._last_positions[label] is None:
            return position
            
        last_pos = self._last_positions[label]
        dx = position[0] - last_pos[0]
        dy = position[1] - last_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Si el movimiento es pequeño, aumentar estabilidad
        if distance < 10:  # Zona de alta estabilidad
            self._stability_counters[label] += 1
            comfort_factor = min(0.95, 0.8 + self._stability_counters[label] * 0.01)
        else:
            self._stability_counters[label] = max(0, self._stability_counters[label] - 1)
            comfort_factor = 0.8
        
        # Aplicar zona de confort (más suavizado en posiciones estables)
        comfortable_position = (
            last_pos[0] * (1 - comfort_factor) + position[0] * comfort_factor,
            last_pos[1] * (1 - comfort_factor) + position[1] * comfort_factor
        )
        
        return comfortable_position

    def process_frame(self, frame):
        """Procesamiento con suavizado ultra-fluido"""
        self.total_frames += 1
        
        # Redimensionar
        if frame.shape[1] != self.camera_width or frame.shape[0] != self.camera_height:
            frame = cv2.resize(frame, (self.camera_width, self.camera_height))
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        raw_detected = {'Right': None, 'Left': None}
        final_positions = {'Right': None, 'Left': None}

        if results.multi_hand_landmarks and results.multi_handedness:
            for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                label = handedness.classification[0].label
                
                # Centro de palma
                x_norm, y_norm = self._palm_center_fast(lm.landmark)
                
                # Convertir a píxeles
                px = int(x_norm * self.camera_width)
                py = int(y_norm * self.camera_height)
                
                px = max(0, min(px, self.camera_width - 1))
                py = max(0, min(py, self.camera_height - 1))
                
                raw_detected[label] = (px, py)

        # Aplicar suavizado ultra-fluido
        for label in ['Right', 'Left']:
            raw_position = raw_detected.get(label)
            
            # Primera etapa: filtro ultra-suave
            ultra_smooth = self.ultra_smooth_filters[label].update(raw_position)
            
            # Segunda etapa: suavizado exponencial doble
            double_smooth = self.double_smoothers[label].update(ultra_smooth)
            
            # Tercera etapa: zona de confort
            final_position = self._apply_comfort_zone(label, double_smooth)
            
            final_positions[label] = final_position
            
            # Actualizar última posición estable
            if final_position:
                self._last_positions[label] = final_position

        # Debug opcional
        if self.total_frames % 60 == 0:  # Cada segundo aproximadamente
            print(f"Frames: {self.total_frames}, Tirones detectados: {self.jerk_detections}")

        return final_positions['Right'], final_positions['Left']

    def release(self):
        """Liberación de recursos"""
        try:
            if hasattr(self, 'hands') and self.hands is not None:
                self.hands.close()
        except Exception:
            pass
        
        try:
            self.hands = None
            self.mp_hands = None
        except Exception:
            pass

# Versión simplificada para máxima fluidez
class SimpleUltraSmoothTracker:
    """Tracker ultra-simple pero ultra-fluido"""
    def __init__(self, camera_width=480, camera_height=360, smoothness=0.92):
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.smoothness = smoothness
        
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=0
        )
        
        self.last_position = None
        self.velocity = (0, 0)
        
    def process_frame(self, frame):
        frame = cv2.resize(frame, (self.camera_width, self.camera_height))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        if results.multi_hand_landmarks:
            landmarks = results.multi_hand_landmarks[0].landmark
            x_norm = sum(landmarks[i].x for i in [0, 5, 17]) / 3
            y_norm = sum(landmarks[i].y for i in [0, 5, 17]) / 3
            
            new_position = (
                int(x_norm * self.camera_width),
                int(y_norm * self.camera_height)
            )
            
            # Suavizado extremadamente simple pero efectivo
            if self.last_position:
                smoothed = (
                    self.last_position[0] * self.smoothness + new_position[0] * (1 - self.smoothness),
                    self.last_position[1] * self.smoothness + new_position[1] * (1 - self.smoothness)
                )
                self.last_position = smoothed
                return smoothed, smoothed  # Ambas manos iguales
            else:
                self.last_position = new_position
                return new_position, new_position
        else:
            # Mantener última posición cuando no hay detección
            return self.last_position, self.last_position
    
    def release(self):
        if self.hands:
            self.hands.close()