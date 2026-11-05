import pygame

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Wilderness Survival AI")

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((100, 160, 100))  # Fill the screen with a green color
    pygame.display.flip()  # Update the display

pygame.quit()