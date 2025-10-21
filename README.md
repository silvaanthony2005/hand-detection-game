# Detección de Manos y Reproducción de Sonidos

Este proyecto utiliza la cámara web para detectar las manos y jugar atajando penales. Está desarrollado en Python usando OpenCV/MediaPipe para la detección y Pygame para el renderizado del juego (fondo, manos y animación de la pelota).

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

## ¿Qué se integró?

- Se reemplazó la ventana de OpenCV por un renderer de Pygame.
- Se agregó la animación de la pelota desde un spritesheet.
- El pipeline de cámara/detección sigue siendo con OpenCV/MediaPipe.

Archivos nuevos/claves:
- `vista/ball_animation.py`: clase `BallAnimation` que carga y reproduce la animación del spritesheet.
- `vista/pygame_renderer.py`: clase `PygameRenderer` que dibuja fondo, manos y pelota animada.
- `Controler/hand_detection.py`: ahora usa `PygameRenderer` en lugar de `GameRenderer`.

## Cómo ejecutar

1) Conecta tu cámara y asegúrate de que no esté siendo usada por otra app.

2) Desde PowerShell, en la raíz del proyecto:

```powershell
python run_game.py
```

3) Controles:
- Mueve tus manos frente a la cámara para ver los overlays de mano.
- La pelota se anima automáticamente al centro de la pantalla.
- Presiona `F` para alternar pantalla completa/ventana.
- Presiona `ESC` o cierra la ventana para salir.

## Notas
- Ejecutar `run_game.py` desde la raíz evita problemas de imports y rutas.
- Los assets se cargan desde la carpeta `Images` usando rutas relativas robustas.
- El programa está configurado para detectar hasta dos manos simultáneamente.
- Si alguna imagen no carga, revisa que existan:
  - `Images/background.jpg`
  - `Images/right_hand.png`
  - `Images/left_hand.png`
  - `Images/spritesheet_pelota.png`

## Rendimiento y uso de memoria

- La resolución de la cámara se fija a 640x480 para reducir carga y RAM.
- En Windows se usa el backend `CAP_DSHOW` para mejorar estabilidad.
- Al cerrar el juego se liberan recursos de MediaPipe y se limpian buffers para bajar el uso de RAM.

## Próximos pasos
- Física de la pelota: Agregar movimiento y trayectoria.
- Detección de colisión: Entre manos y pelota.
- Sistema de puntuación: Contador de penales atajados.
- Sonidos: Usar `pygame.mixer` para efectos de audio.
- Estados del juego: jugando, pausa, game over.

