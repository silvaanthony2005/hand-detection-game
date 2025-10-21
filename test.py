import pygame
import spritesheet
pygame.init()
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 500

#Define la ventana
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Spritesheets')

#Carga el spritesheet de la pelota
spritesheet_img = pygame.image.load('Images/spritesheet_pelota.png').convert_alpha()
spritesheet_pelota = spritesheet.Spritesheet(spritesheet_img)


BG = (50, 50, 50)
BLACK = (0, 0, 0)

#Definiendo animation list (va a contener los frames individuales del spritesheet)
animation_list = []
animation_steps = 15 #Cantidad de frames a utilizar

#Definiendo tiempos de la animacion
last_update = pygame.time.get_ticks()
animation_cooldown = 75
current_frame = 0

#Vaciado de los frames individuales del spritesheet en la lista
for frame in range(animation_steps):
    animation_list.append(spritesheet_pelota.get_img(frame, 132, 125, 1, BLACK))

#Ejecuta el juego
run = True
while run:

    #Update BG
    screen.fill(BG)

    #update animation
    current_time=pygame.time.get_ticks()
    if current_time - last_update >= animation_cooldown: #Cada vez que pase el tiempo estipulado (ms) de cooldown, pasa al siguiente frame
        current_frame += 1
        last_update = current_time
        if current_frame >= len(animation_list): #Reinicia los frames en la animacion
            current_frame = 0

    #show animation   
    screen.blit(animation_list[current_frame], (0,0))

    #Event Handler (cierra el juego en la x de la ventana)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
    
    pygame.display.update()

pygame.quit()