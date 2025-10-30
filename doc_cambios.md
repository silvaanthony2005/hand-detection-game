 el archivo vista/game_render.py ya no sirve después de implementar la integración con Pygame. game_render.py:5

Por qué ya no es necesario
El archivo GameRenderer fue diseñado para usar OpenCV (cv2.imshow(), cv2.waitKey()) para el renderizado game_render.py:76-86 , pero ahora has reemplazado completamente ese sistema con PygameRenderer que usa Pygame para todo el renderizado y manejo de eventos.

| Funcionalidad en `GameRenderer` | Reemplazo en `PygameRenderer` |
| :------------------------------ | :----------------------------- |
| `cv2.imread()` para cargar imágenes | `pygame.image.load()` |
| `cv2.imshow()` para mostrar ventana | `pygame.display.flip()` |
| `cv2.waitKey()` para eventos | `pygame.event.get()` |
| `overlay_image()` con alpha blending manual | `surface.blit()` con transparencia nativa |
| Pelota estática (`pelota.png`) | `BallAnimation` con spritesheet animado |


El archivo test.py tampoco es necesario ya que su funcionalidad de animación de spritesheet ahora está integrada en BallAnimation dentro del sistema principal

## 26-10-2025 — Cambios recientes en jugabilidad y renderizado

- Controles de movimiento: ahora la tecla Enter lanza la pelota en dirección aleatoria (izquierda/derecha) únicamente si la pelota está rotando y no se está moviendo.
- Efecto de aproximación: al iniciar el movimiento, la pelota comienza con escala 0.6 y aumenta linealmente hasta 1.0 conforme se acerca a la portería.
- Colisión con manos: si cualquier mano toca la pelota, se cancela el desplazamiento y la pelota vuelve al centro. La rotación no se detiene (si estaba activa, continúa).
- Optimización segura: se reutiliza la superficie temporal de la pelota para no crear una nueva cada frame; se usa rotate cuando no hay escala y scale en lugar de smoothscale cuando solo hay escalado. Se mantuvo el límite fijo de 30 FPS.

Optimización de rendimiento adicional:

- Ventana y fullscreen con flags de rendimiento:
	- Ventana: `pygame.DOUBLEBUF | pygame.SCALED` (con fallback seguro si no está disponible).
	- Pantalla completa: `pygame.FULLSCREEN | pygame.DOUBLEBUF`.
- Caché de rotaciones cuando la escala es 1.0:
	- Cuantización en pasos de 5° para reutilizar superficies rotadas y reducir el uso de CPU sin perder calidad perceptible.
- I/O de consola reducido: se removió el `print` en cada colisión para evitar microcortes.
- Sensación de juego más rápida sin subir FPS: `_move_speed` aumentó de 6 a 8 px/frame.
- Se mantiene el límite fijo de 30 FPS.

Archivos impactados:
- `vista/pygame_renderer.py`: ajustes de flags de ventana, caché de rotación, eliminación de prints de colisión, incremento de velocidad.

(Es decir:
Doble Búfer (DOUBLEBUF): Se activó para la ventana y pantalla completa. Esto permite dibujar la siguiente imagen "detrás" de la actual, eliminando el "tearing" (imagen cortada) y asegurando animaciones fluidas.

Escalado (SCALED): Garantiza que si la ventana se redimensiona, el contenido se escale de forma limpia.

Caché de Rotaciones: En lugar de calcular una rotación nueva para cada grado, solo se calculan en pasos de 5° y se reutilizan (caché). Esto reduce significativamente la carga de la CPU sin un impacto visual perceptible.

I/O Reducido: Se eliminó el print que ocurría en cada colisión. Esta operación de Entrada/Salida (I/O) causaba microcortes o pausas en el juego, interrumpiendo la fluidez.

)