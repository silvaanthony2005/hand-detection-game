import cv2
import mediapipe as mp
import pygame 

# Inicialización de MediaPipe y utilidades de dibujo
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

pygame.mixer.init()

cap = cv2.VideoCapture(0) # trabajar con la camara conectada a la pc

with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, 
                    max_num_hands=2) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Dibujar los landmarks de la mano
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        cv2.imshow('Hand Detection for Game', frame) # Título actualizado
        if cv2.waitKey(1) & 0xFF == 27: # Presiona ESC para salir
            break

cap.release()
cv2.destroyAllWindows()