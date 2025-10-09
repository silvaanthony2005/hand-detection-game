# Detección de Manos y Reproducción de Sonidos

Este proyecto utiliza la cámara web para detectar las manos en todo momento para así poder detener los penales y ganar puntos. Está desarrollado en Python utilizando las librerías OpenCV, MediaPipe y Pygame.

## Requisitos
- Python 3.10 o 3.12
- OpenCV (`pip install opencv-python`)
- MediaPipe (`pip install mediapipe`)
- Pygame (`pip install pygame`)

## Funcionamiento

1. **Detección de Manos**:
   - Utiliza MediaPipe para detectar las manos a través de la cámara web.
   - Dibuja los puntos de referencia y las conexiones entre ellos en la imagen capturada.

2. **Serán agregadas mediante se vaya realizando el proyecto**

3. **Control de la Aplicación**:
   - Presiona la tecla `ESC` para salir del programa.

## Ejecución

1. Ejecuta el script principal:
   ```bash
   python final_count.py
   ```
2. Coloca tus manos frente a la cámara y empieza a moverla para evitar un gol.

## Notas
- Asegúrate de que la cámara web esté conectada y funcione correctamente.
- El programa está configurado para detectar hasta dos manos simultáneamente.
